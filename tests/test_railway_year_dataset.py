"""The Railway year is exercised only against disposable SQLite databases."""
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

from app import create_app
from app.models import db
from app.models.annual_plan import AnnualGoalProposal, AnnualTarget
from app.models.event import Attendance, Event, ExternalParticipant, Registration
from app.models.finding_review import FindingReview, FindingReviewEvent
from app.models.user import SystemSetting, User
from app.railway_year_dataset import DEFAULT_EMAILS, MARKER

NOW = datetime(2026, 11, 24, 10)


@pytest.fixture
def seed_app(tmp_path, monkeypatch):
    app=create_app('testing')
    app.config.update(PRIVATE_UPLOAD_FOLDER=str(tmp_path/'private'), MAIL_SUPPRESS_SEND=True)
    app.static_folder=str(tmp_path/'static')
    monkeypatch.setattr('app.railway_year_dataset.local_now', lambda: NOW)
    monkeypatch.setattr('app.services.aop_goals.local_now', lambda: NOW)
    monkeypatch.setattr('app.services.activity_workflow.local_now', lambda: NOW)
    monkeypatch.setattr('app.services.finding_reviews.local_now', lambda: NOW)
    monkeypatch.setattr('app.services.workspace_reports.local_now', lambda: NOW, raising=False)
    monkeypatch.setattr('app.annual_goals.local_now', lambda: NOW)
    source=tmp_path/'source.sqlite'
    with app.app_context():
        original=db.engine.raw_connection()
        with sqlite3.connect(source) as target:
            original.driver_connection.backup(target)
        original.close()
        db.drop_all()
    monkeypatch.setenv('RAILWAY_SEED_SOURCE_DATABASE_URL', 'sqlite:///'+source.as_posix())
    app.config['SEED_TEST_SOURCE']=str(source)
    yield app
    with app.app_context():
        db.session.remove()
        db.engine.dispose()


def invoke(app, *extra, answer='SEED 2026 local/:memory:\n'):
    return app.test_cli_runner().invoke(args=['seed-railway-year','--database',':memory:',*extra], input=answer)


def test_dry_run_is_read_only_and_confirmation_is_required(seed_app):
    source=Path(seed_app.config['SEED_TEST_SOURCE'])
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    result=invoke(seed_app, '--dry-run')
    assert result.exit_code==0, result.output
    assert '90 activities' in result.output
    with seed_app.app_context():
        assert inspect(db.engine).get_table_names()==[]
    assert not Path(seed_app.config['PRIVATE_UPLOAD_FOLDER']).exists()
    result=invoke(seed_app, answer='wrong\n')
    assert result.exit_code!=0
    with seed_app.app_context():
        assert inspect(db.engine).get_table_names()==[]
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before


@pytest.mark.parametrize('admin_role', ['director', 'admin'])
def test_complete_year_and_rerun(seed_app, admin_role):
    source=Path(seed_app.config['SEED_TEST_SOURCE'])
    with sqlite3.connect(source) as conn:
        conn.execute("UPDATE users SET role=? WHERE email='admin@psu.edu'", (admin_role,))
    before=hashlib.sha256(source.read_bytes()).hexdigest()
    result=invoke(seed_app)
    assert result.exit_code==0, result.output
    with seed_app.app_context():
        manifest=json.loads(SystemSetting.query.filter_by(key=MARKER).one().value)
        assert manifest['lifecycle']==dict(ended=65,ongoing=2,future=15,draft=4,cancelled=4)
        assert Counter(row['status'] for row in manifest['goals'])==dict(not_started=5,in_progress=10,met=7,above=3)
        assert sorted(Counter(row['campus'] for row in manifest['goals']).values())==[2,2,3,3,3,3,3,3,3]
        assert User.query.count()==191
        assert ExternalParticipant.query.count()==90
        assert AnnualGoalProposal.query.filter_by(status='submitted').count()==25
        assert Registration.query.count()>1800
        assert Attendance.query.count()>900
        assert not db.session.query(Attendance).join(Event).filter(Event.date>NOW).count()
        assert not db.session.query(Registration).join(Event).filter(Event.end_date>NOW, Registration.status=='completed').count()
        assert {'female','male','prefer_not_to_say'} <= set(manifest['sex'])
        breakdown=manifest['sex_participation']
        assert {r['key'] for r in breakdown['groups']}=={'female','male','prefer_not_to_say','unrecorded'}
        assert sum(r['total'] for r in breakdown['groups'])==breakdown['total']>0
        assert all(r['total']==r['psu']+r['external'] for r in breakdown['groups'])
        assert {'remaining_goals','low_attendance','missed_targets'} <= set(manifest['findings'])
        assert FindingReview.query.count()>0
        assert FindingReviewEvent.query.count()>=FindingReview.query.count()
        with sqlite3.connect(source) as conn:
            conn.row_factory=sqlite3.Row
            for row in conn.execute('SELECT * FROM users WHERE email IN (?,?,?,?)',DEFAULT_EMAILS):
                user=User.query.filter_by(email=row['email']).one()
                expected_role = 'director' if row['email'] == 'admin@psu.edu' else row['role']
                assert (user.id,user.password_hash,user.role,user.name)==(row['id'],row['password_hash'],expected_role,row['name'])
                assert user.campus.code==conn.execute('SELECT code FROM campuses WHERE id=?',(row['campus_id'],)).fetchone()[0] if row['campus_id'] else user.campus_id is None
        assert all(not any(word in e.title.lower() for word in ('demo','test','sample','synthetic')) for e in Event.query.all())
        from app.railway_year_dataset import _dest_file
        from pypdf import PdfReader
        for relative in manifest['files']:
            path=_dest_file(relative)
            assert path.is_file()
            if path.suffix=='.pdf':
                reader=PdfReader(path)
                assert reader.pages[0].extract_text().strip()
        expected_tables=manifest['tables']
    result=invoke(seed_app)
    assert result.exit_code==0, result.output
    assert 'no changes made' in result.output
    assert hashlib.sha256(source.read_bytes()).hexdigest()==before
    with seed_app.app_context():
        from app.railway_year_dataset import _fingerprint
        assert _fingerprint()==expected_tables
        User.query.filter_by(email='student@psu.edu').one().name='Changed after seed'
        db.session.commit()
    result=invoke(seed_app)
    assert result.exit_code!=0
    assert 'has changed' in result.output


@pytest.mark.parametrize('problem',['mail','populated','missing_account','role','wrong_database','same_source','late','source_error'])
def test_preflight_refuses_unsafe_inputs(seed_app, monkeypatch, problem):
    extra=[]
    if problem=='mail':
        seed_app.config['MAIL_SUPPRESS_SEND']=False
    elif problem=='populated':
        with seed_app.app_context():
            db.create_all()
    elif problem in ('missing_account','role'):
        with sqlite3.connect(seed_app.config['SEED_TEST_SOURCE']) as conn:
            conn.execute("UPDATE users SET email='other@people.invalid' WHERE email='student@psu.edu'" if problem=='missing_account'
                         else "UPDATE users SET role='volunteer' WHERE email='director@psu.edu'")
    elif problem=='wrong_database':
        extra=['--database','other']
    elif problem=='same_source':
        monkeypatch.setenv('RAILWAY_SEED_SOURCE_DATABASE_URL','sqlite:///:memory:')
    elif problem=='late':
        monkeypatch.setattr('app.railway_year_dataset.local_now',lambda:datetime(2027,1,1))
    elif problem=='source_error':
        monkeypatch.setenv('RAILWAY_SEED_SOURCE_DATABASE_URL','sqlite:///unreadable-folder/private-password.sqlite')
    result=invoke(seed_app,'--dry-run',*extra)
    assert result.exit_code!=0
    assert 'private-password' not in result.output
    if problem!='populated':
        with seed_app.app_context():
            assert inspect(db.engine).get_table_names()==[]


def test_failure_rolls_back_rows_and_created_files(seed_app,monkeypatch):
    from app import railway_year_dataset as seed
    def fail():
        raise RuntimeError('secret SQL password must never be displayed')
    monkeypatch.setattr(seed,'_fingerprint',fail)
    result=invoke(seed_app)
    assert result.exit_code!=0
    assert 'secret SQL' not in result.output
    with seed_app.app_context():
        assert Event.query.count()==0
        assert User.query.count()==0
    assert not list(Path(seed_app.config['PRIVATE_UPLOAD_FOLDER']).rglob('*.pdf'))


def test_file_collision_preserves_existing_upload(seed_app):
    root=Path(seed_app.config['PRIVATE_UPLOAD_FOLDER'])/'proposals'
    root.mkdir(parents=True)
    path=root/'moa-2026-01.pdf'
    path.write_bytes(b'existing unrelated file')
    result=invoke(seed_app)
    assert result.exit_code!=0
    assert path.read_bytes()==b'existing unrelated file'
    with seed_app.app_context():
        assert Event.query.count()==0


def test_retains_profile_photos_and_policy_acceptances_without_reset_tokens(seed_app, tmp_path, monkeypatch):
    uploads=tmp_path/'source-uploads'
    (uploads/'profiles').mkdir(parents=True)
    (uploads/'profiles'/'retained.png').write_bytes(b'preserved profile image bytes')
    monkeypatch.setenv('RAILWAY_SEED_SOURCE_UPLOAD_FOLDER',str(uploads))
    with sqlite3.connect(seed_app.config['SEED_TEST_SOURCE']) as conn:
        student=conn.execute("SELECT id FROM users WHERE email='student@psu.edu'").fetchone()[0]
        publisher=conn.execute("SELECT id FROM users WHERE email='faculty@psu.edu'").fetchone()[0]
        conn.execute("UPDATE users SET profile_image_path='uploads/profiles/retained.png',profile_image_name='Portrait.png' WHERE id=?",(student,))
        conn.execute("UPDATE volunteer_profiles SET past_participation=? WHERE user_id=?",(json.dumps([{'title':'Prior participation record'}]),student))
        conn.execute("INSERT INTO terms_revisions (id,title,body,version,is_active,published_by_id,published_at) VALUES (1,'Terms','Existing policy text','v1',1,?,'2026-01-01 00:00:00')",(publisher,))
        conn.execute("INSERT INTO terms_acceptances (user_id,revision_id,accepted_at) VALUES (?,1,'2026-01-02 00:00:00')",(student,))
        conn.execute("INSERT INTO password_reset_tokens (user_id,token_hash,expires_at,created_at) VALUES (?,'private-token','2026-12-01 00:00:00','2026-11-24 00:00:00')",(student,))
    result=invoke(seed_app)
    assert result.exit_code==0,result.output
    with seed_app.app_context():
        from app.models.policy import TermsRevision, TermsAcceptance
        from app.models.user import PasswordResetToken
        student=User.query.filter_by(email='student@psu.edu').one()
        assert student.profile.past_participation==[{'title':'Prior participation record'}]
        assert student.profile_image_name=='Portrait.png'
        assert TermsRevision.query.one().published_by_id is None
        assert TermsAcceptance.query.one().user_id==student.id
        assert PasswordResetToken.query.count()==0
        assert (Path(seed_app.static_folder)/'uploads/profiles/retained.png').read_bytes()==b'preserved profile image bytes'


def test_missing_profile_photo_stops_before_schema(seed_app):
    with sqlite3.connect(seed_app.config['SEED_TEST_SOURCE']) as conn:
        conn.execute("UPDATE users SET profile_image_path='uploads/profiles/missing.png' WHERE email='student@psu.edu'")
    result=invoke(seed_app,'--dry-run')
    assert result.exit_code!=0
    with seed_app.app_context():
        assert inspect(db.engine).get_table_names()==[]
