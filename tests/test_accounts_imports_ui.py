"""Account actions and resumable imports, using only disposable databases/files."""
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import pytest
from app.models import db
from app.models.user import User, PasswordResetToken, SystemSetting
from app.models.event import HistoricalActivity
from app.models.annual_plan import AnnualTarget
from app.routes.admin import USER_IMPORT_COLUMNS
from tests.test_workspace_overhaul import actors, sign_in
from tests.test_app import app, client


def csv_bytes(rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def upload_users(client, count=1, prefix='new'):
    rows = [dict.fromkeys(USER_IMPORT_COLUMNS, '') for _ in range(count)]
    for index, row in enumerate(rows):
        row.update(name=f'Authored Name {index}', email=f'{prefix}{index}@example.org',
                   password='StrongPassword1!', role='volunteer', campus_code='LINGAYEN')
    return client.post('/admin/users/import', data={'file': (io.BytesIO(csv_bytes(rows)), 'users.csv')})


def stage(client, slot='user_import_preview'):
    with client.session_transaction() as session:
        return dict(session[slot])


def test_user_review_refresh_paging_full_confirm_and_export(client, app, actors):
    sign_in(client, actors, 'director')
    response = upload_users(client, 26)
    assert response.status_code == 302
    assert response.location.endswith('?stage=review')
    staged = stage(client)
    path = Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'import-previews'/staged['file']
    for page in (1, 2, 2):
        response = client.get(f'/admin/users/import?stage=review&page={page}')
        text = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'StrongPassword1!' not in text and 'scrypt:' not in text
        assert staged['file'] not in text and str(path) not in text
        assert f'Page {page} of 2' in text
        assert 'new25@example.org' in text if page == 2 else 'new25@example.org' not in text
    assert b'Resume Preview' in client.get('/admin/users/import').data
    assert User.query.filter(User.email.like('new%@example.org')).count() == 0
    response = client.post('/admin/users/import', data={'action':'confirm','token':staged['token']})
    assert response.status_code == 302
    assert User.query.filter(User.email.like('new%@example.org')).count() == 26
    assert not path.exists()
    assert client.post('/admin/users/import',data={'action':'confirm','token':staged['token']}).status_code == 400
    exported = client.get('/admin/users/export.csv?search=nothing').data
    assert b'new25@example.org' in exported and b'password_hash' not in exported


def test_user_replacement_discard_and_failed_replacement(client, app, actors):
    sign_in(client, actors, 'director')
    upload_users(client)
    first = stage(client)
    base = Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'import-previews'
    assert client.post('/admin/users/import',data={'file':(io.BytesIO(b'bad'), 'bad.csv')}).status_code == 302
    assert stage(client) == first
    upload_users(client, prefix='replacement')
    second = stage(client)
    assert second['file'] != first['file'] and not (base/first['file']).exists()
    assert client.post('/admin/users/import',data={'action':'discard','token':second['token']}).status_code == 302
    assert not (base/second['file']).exists()
    assert User.query.filter_by(email='replacement0@example.org').first() is None


@pytest.mark.parametrize('failure',['wrong-token','missing-file','tampered-file','different-client','changed-account'])
def test_user_stage_failure_is_atomic(client, app, actors, failure):
    sign_in(client, actors, 'director')
    upload_users(client, count=2)
    staged = stage(client)
    path = Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'import-previews'/staged['file']
    token = staged['token']
    acting = client
    if failure == 'wrong-token': token = 'wrong'
    if failure == 'missing-file': path.unlink()
    if failure == 'tampered-file': path.write_text('[]')
    if failure == 'different-client':
        acting = app.test_client(); sign_in(acting, actors, 'director')
    if failure == 'changed-account':
        db.session.add(User(name='Late conflict',email='new1@example.org',role='volunteer',password_hash='unused'))
        db.session.commit()
    response = acting.post('/admin/users/import',data={'action':'confirm','token':token})
    assert response.status_code in (400,302)
    assert User.query.filter_by(email='new0@example.org').count() == 0


def dataset(kind, count=1):
    if kind == 'annual':
        return [dict(plan_key='aop-ui',year='2026',plan_type='AOP',plan_title='Annual plan',
            source_document='Approved plan',indicator_key=f'ui-{n}',indicator_code=f'UI-{n}',
            program='Extension',indicator_name=f'Authored indicator {n}',unit='activities',
            responsible_office='Extension Office',target_key=f'ui-target-{n}',campus_code='LINGAYEN',
            target_value='4',approval_reference='Board reference',approval_date='2026-01-01',
            evidence_basis='approved_aggregate') for n in range(count)]
    return [dict(source_key=f'history-ui-{n}',source_document='Archived report',source_page='1',source_row=str(n+1),
        unit_name='Lingayen',title=f'Authored historical title {n}',activity_type='Extension',partners='',
        participant_categories='',volunteer_count='10',year_conducted='2025') for n in range(count)]


@pytest.mark.parametrize('kind',['annual','historical'])
def test_dataset_review_resume_pagination_confirm_all(client, app, actors, kind):
    sign_in(client, actors, 'director')
    url = '/workspace/imports/'+kind
    response = client.post(url,data={'dataset':(io.BytesIO(csv_bytes(dataset(kind,26))),'input.csv')})
    assert response.status_code == 302
    staged = stage(client,'import_preview_'+kind)
    review = client.get(url+'?stage=review&page=2')
    assert review.status_code == 200 and b'Page 2 of 2' in review.data
    assert staged['file'].encode() not in review.data
    assert b'Resume Preview' in client.get(url).data
    model = AnnualTarget if kind == 'annual' else HistoricalActivity
    assert model.query.count() == 0
    result = client.post(url+'?stage=review&page=2',data={'action':'confirm','token':staged['token']},follow_redirects=True)
    assert result.status_code == 200 and b'Import completed' in result.data
    assert model.query.count() == 26
    assert client.post(url,data={'action':'confirm','token':staged['token']}).status_code == 400


@pytest.mark.parametrize('kind',['annual','historical'])
def test_dataset_revalidation_rolls_back_late_row_failure(client, app, actors, kind):
    sign_in(client, actors, 'director')
    from unittest.mock import patch
    from app.routes.workspace import run_import
    url='/workspace/imports/'+kind
    client.post(url,data={'dataset':(io.BytesIO(csv_bytes(dataset(kind,2))),'input.csv')})
    staged=stage(client,'import_preview_'+kind)
    def fail_after_validation(kind,path,dry_run):
        if not dry_run:
            # Exercise the route's rollback wrapper after an importer flush.
            db.session.add(User(name='Uncommitted',email='rollback@example.org',role='volunteer',password_hash='unused'))
            db.session.flush()
            raise ValueError('Late validation failure. Upload a corrected file.')
        return run_import(kind,path,dry_run)
    with patch('app.routes.workspace.run_import',side_effect=fail_after_validation):
        response=client.post(url+'?stage=review',data={'action':'confirm','token':staged['token']})
    assert response.status_code==200 and b'Late validation failure' in response.data
    assert User.query.filter_by(email='rollback@example.org').count()==0
    assert stage(client,'import_preview_'+kind)==staged


@pytest.mark.parametrize('role',['coordinator','volunteer'])
@pytest.mark.parametrize('path',['/admin/users/1','/admin/users/1/reset-password','/admin/users/import','/workspace/imports/annual','/workspace/imports/historical'])
def test_director_only_accounts_and_imports(client, actors, role, path):
    sign_in(client,actors,role)
    assert client.get(path).status_code==403
    assert client.post(path,data={'action':'confirm','token':'wrong'}).status_code in (403,405)


def test_account_details_context_validation_and_secrets(client, app, actors):
    sign_in(client,actors,'director')
    target=actors['volunteer'];url=f'/admin/users/{target}'
    context='/admin_dash?search=volunteer&campus_id=1&page=2'
    record=client.get(url+'?return_to='+quote(context,safe=''))
    assert b'View Record' not in record.data and b'Reset Password' in record.data
    assert b'/admin_dash?search=volunteer&amp;campus_id=1&amp;page=2' in record.data
    submitted=dict(name='Submitted Authored Name',email='director@example.org',role='coordinator',campus_id='2',volunteer_type='staff',college_affiliation='Authored college')
    response=client.post(url+'/edit',data=submitted)
    assert b'Email already exists' in response.data and b'Submitted Authored Name' in response.data
    assert b'value="2" selected' in response.data and b'value="staff" selected' in response.data
    assert db.session.get(User,target).name=='volunteer'
    assert client.get(url+'/edit').data.count(b'name="new_password"')==0
    rejected=client.post(url+'/reset-password',data={'new_password':'StrongPassword1!','confirm_password':'different'})
    assert b'does not match' in rejected.data and b'value="StrongPassword1!' not in rejected.data
    assert b'data-no-draft' in rejected.data
    external=client.get(url+'?return_to=https://example.org')
    assert b'href="/admin_dash"' in external.data


def test_account_guards_reset_and_eligible_delete(client, app, actors):
    sign_in(client,actors,'director');target=actors['volunteer'];director=actors['director']
    client.post(f'/admin/users/deactivate/{director}')
    assert db.session.get(User,director).is_active
    client.post(f'/admin/users/{director}/edit',data=dict(name='Director',email='director@example.org',role='volunteer',campus_id=1))
    assert db.session.get(User,director).role=='director'
    assert client.post(f'/admin/users/{target}/delete').status_code==403
    user=db.session.get(User,target);old_version=user.auth_version
    recovery=PasswordResetToken(user_id=target,token_hash='1'*64,expires_at=datetime.utcnow()+timedelta(hours=1))
    other_recovery=PasswordResetToken(user_id=director,token_hash='2'*64,expires_at=datetime.utcnow()+timedelta(hours=1))
    db.session.add_all([recovery,other_recovery]);db.session.commit()
    response=client.post(f'/admin/users/{target}/reset-password',data={'new_password':'StrongPassword1!'})
    assert response.status_code==302
    assert user.auth_version==old_version+1 and user.check_password('StrongPassword1!')
    assert recovery.used_at is not None and other_recovery.used_at is None
    client.post(f'/admin/users/deactivate/{target}')
    assert not user.is_active and client.post(f'/admin/users/{target}/delete').status_code==403
    user.deactivated_at=datetime.utcnow()-timedelta(days=31);db.session.commit()
    assert b'Delete Account' in client.get(f'/admin/users/{target}').data
    response=client.post(f'/admin/users/{target}/delete?return_to=%2Fadmin_dash%3Ftab%3Ddeactivated')
    assert response.location.endswith('/admin_dash?tab=deactivated')
    assert db.session.get(User,target) is None


def test_create_errors_and_draft_cleanup(client, app, actors):
    sign_in(client,actors,'director')
    response=client.post('/admin/users/create',data=dict(name='Authored retained name',email='director@example.org',
        password='weak',role='coordinator',campus_id=2,volunteer_type='staff'))
    assert response.status_code==200 and b'Email already exists' in response.data
    assert b'value="2" selected' in response.data and b'value="staff" selected' in response.data
    assert b'value="weak"' not in response.data
    key='form:/admin/users/create'
    client.put('/workspace/drafts/'+key,json={'name':['Draft account'],'role':['coordinator'],'campus_id':['2'],'password':['NeverStoreThis1!']})
    draft=client.get('/workspace/drafts/'+key).json['payload']
    assert draft['role']==['coordinator'] and 'password' not in draft
    response=client.post('/admin/users/create',data=dict(name='New authored account',email='created@example.org',
        password='StrongPassword1!',role='coordinator',campus_id=2,_draft_key=key))
    assert response.status_code==302 and '/admin/users/' in response.location
    assert client.get('/workspace/drafts/'+key).json['payload']=={}


def test_changed_password_policy_requires_new_upload(client, app, actors):
    sign_in(client,actors,'director');upload_users(client)
    staged=stage(client)
    db.session.add(SystemSetting(key='default_password_length',value='24'));db.session.commit()
    response=client.post('/admin/users/import',data={'action':'confirm','token':staged['token']},follow_redirects=True)
    assert b'password policy changed' in response.data
    assert User.query.filter_by(email='new0@example.org').count()==0
