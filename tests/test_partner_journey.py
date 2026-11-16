"""Connected partner records and explicit activity-draft agreement selection."""
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import pytest
from app.models import db
from app.models.workspace import PartnerAgency, PartnerAgreement, FormDraft
from app.services.activity_workflow import save_document
from tests.test_app import app, client
from tests.test_workspace_overhaul import actors, sign_in, docx


@pytest.fixture
def records(app, actors):
    agency=PartnerAgency(name='Authored Agency 100%_',contact_name='Authored Contact',campus_id=1,email='contact@example.org')
    other=PartnerAgency(name='Other campus',contact_name='Other Contact',campus_id=2)
    db.session.add_all([agency,other]);db.session.flush()
    from werkzeug.datastructures import FileStorage
    document,_=save_document(FileStorage(docx(),filename='signed.docx'))
    agreement=PartnerAgreement(agency_id=agency.id,reference='MOA-BOUNDARY',valid_from=date(2027,1,1),valid_until=date(2027,12,31),document=document)
    foreign=PartnerAgreement(agency_id=other.id,reference='FOREIGN',valid_from=date(2027,1,1),valid_until=date(2027,12,31),document=document)
    db.session.add_all([agreement,foreign]);db.session.commit()
    return agency.id,other.id,agreement.id,foreign.id


def new_draft(actors, date_value='2027-05-01T09:00'):
    payload={'_proposal':{'name':'proposal.docx','path':'saved.docx'},'_files':{'cover_image':{'name':'cover.png','path':'cover.png'}},
        'date':[date_value],'end_date':['2027-05-01T12:00'],'title':['Authored Activity'], 'departments':['Authored Department'],
        'participant_type':['Community'],'agreement_id':['old']}
    draft=FormDraft(user_id=actors['coordinator'],campus_id=1,key='activity:new',payload=payload)
    db.session.add(draft);db.session.commit();return draft


def test_agency_list_search_counts_context_and_separate_forms(client, actors, records):
    sign_in(client,actors)
    aid,_,mid,_=records
    response=client.get('/workspace/partners?q=%25_&activity_context=create')
    assert response.status_code==200 and b'Authored Agency' in response.data
    assert b'name="contact_name"' not in response.data and b'Add Agency' in response.data
    assert b'Other campus' not in response.data and b'Back to Activity Draft' in response.data
    assert b'Back to Activity Draft' not in client.get('/workspace/partners').data
    record=client.get(f'/workspace/partners/{aid}?return_to='+quote('/workspace/partners?q=%25_&page=2',safe=''))
    assert b'Edit Agency Details' in record.data and b'name="document"' not in record.data
    assert b'/workspace/partners?q=%25_&amp;page=2' in record.data
    assert b'MOA-BOUNDARY' in record.data
    detail=client.get(f'/workspace/partners/{aid}/agreements/{mid}')
    assert b'Use This MOA' not in detail.data and b'Download Document' in detail.data


def test_agency_create_edit_errors_and_legacy_post(client, actors, records):
    sign_in(client,actors);aid=records[0]
    url=f'/workspace/partners/{aid}/edit'
    failed=client.post(url,data={'name':'Retained Name','contact_name':'','email':'retained@example.org'})
    assert failed.status_code==200 and b'Retained Name' in failed.data and b'aria-invalid="true"' in failed.data
    assert db.session.get(PartnerAgency,aid).name=='Authored Agency 100%_'
    response=client.post(url,data=dict(name='Updated Authored Name',contact_name='Updated Contact',email='new@example.org',phone='123'))
    assert response.status_code==302 and response.location.endswith(f'/workspace/partners/{aid}')
    assert db.session.get(PartnerAgency,aid).email=='new@example.org'
    response=client.post('/workspace/partners',data=dict(name='Legacy created',contact_name='Legacy Contact',campus_id='2'))
    assert response.status_code==302
    assert PartnerAgency.query.filter_by(name='Legacy created').one().campus_id==1


@pytest.mark.parametrize('path', ['','/edit','/agreements/new','/agreements/{mid}','/moa/{mid}','/agreements/{mid}/use'])
def test_other_campus_records_inaccessible(client,actors,records,path):
    sign_in(client,actors);_,aid,_,mid=records
    url=f'/workspace/partners/{aid}'+path.format(mid=mid)
    response=client.post(url+'?activity_context=create') if path.endswith('/use') else client.get(url)
    assert response.status_code==404


@pytest.mark.parametrize('role',['director','volunteer'])
def test_other_roles_cannot_manage_partners(client,actors,records,role):
    sign_in(client,actors,role);aid,_,mid,_=records
    for path in ['/workspace/partners/new',f'/workspace/partners/{aid}/edit',f'/workspace/partners/{aid}/agreements/new',f'/workspace/partners/{aid}/agreements/{mid}']:
        assert client.get(path).status_code==403
        assert client.post(path).status_code in (403,405)
    assert client.post(f'/workspace/partners/{aid}/agreements/{mid}/use?activity_context=create').status_code==403


@pytest.mark.parametrize('start,allowed',[('2027-01-01T00:00',True),('2027-12-31T23:59',True),('2026-12-31T23:59',False),('2028-01-01T00:00',False)])
def test_use_moa_checks_start_inclusively_and_preserves_draft(client,actors,records,start,allowed):
    sign_in(client,actors);aid,_,mid,_=records;draft=new_draft(actors,start);before=deepcopy(draft.payload)
    response=client.post(f'/workspace/partners/{aid}/agreements/{mid}/use?activity_context=create')
    assert response.status_code==302
    if allowed:
        assert response.location.endswith('/workspace/create/3')
        assert draft.payload==dict(before,agreement_id=[str(mid)])
    else:
        assert '/agreements/' in response.location and draft.payload==before
    assert FormDraft.query.filter_by(key='activity:new').count()==1


def test_use_requires_existing_draft_and_context_and_matching_agreement(client,actors,records):
    sign_in(client,actors);aid,_,mid,foreign=records
    url=f'/workspace/partners/{aid}/agreements/{mid}/use'
    assert client.post(url).status_code==400
    assert client.post(url+'?activity_context=create').status_code==302
    assert FormDraft.query.filter_by(key='activity:new').count()==0
    assert client.get(f'/workspace/partners/{aid}/agreements/{foreign}').status_code==404
    assert client.get(f'/workspace/partners/{aid}/moa/{foreign}').status_code==404
    draft=new_draft(actors,'bad-date');before=deepcopy(draft.payload)
    page=client.get(f'/workspace/partners/{aid}/agreements/{mid}?activity_context=create')
    assert b'Use This MOA' not in page.data and b'Complete the approved proposal' in page.data
    client.post(url+'?activity_context=create');assert draft.payload==before


def test_private_download_and_missing_file(client,app,actors,records):
    sign_in(client,actors);aid,_,mid,_=records
    url=f'/workspace/partners/{aid}/moa/{mid}'
    response=client.get(url);assert response.status_code==200 and 'attachment' in response.headers['Content-Disposition']
    response.close()
    agreement=db.session.get(PartnerAgreement,mid)
    (Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'proposals'/agreement.document['path']).unlink()
    assert client.get(url).status_code==404


def test_legacy_draft_resume_upload_and_cleanup(client,app,actors,records):
    sign_in(client,actors);aid=records[0];key=f'form:/workspace/partners/{aid}?q=old'
    client.put('/workspace/drafts/'+quote(key,safe=''),json={'reference':['LEGACY-MOA'],'valid_from':['2027-01-01'],'valid_until':['2027-12-31']})
    assert client.post('/workspace/draft-uploads/'+quote(key,safe=''),data={'field':'document','upload':(docx(),'retained.docx')}).status_code==200
    listing=client.get('/workspace/drafts');assert b'/agreements/new?resume=' in listing.data
    form=client.get(f'/workspace/partners/{aid}/agreements/new?resume='+quote(key,safe=''))
    assert key.encode() in form.data
    response=client.post(f'/workspace/partners/{aid}',data={'_draft_key':key,'reference':'LEGACY-MOA','valid_from':'2027-01-01','valid_until':'2027-12-31'})
    assert response.status_code==302
    assert PartnerAgreement.query.filter_by(reference='LEGACY-MOA').one().document['name']=='retained.docx'
    assert FormDraft.query.filter_by(key=key).count()==0


def test_new_agreement_validation_values_and_upload(client,actors,records):
    sign_in(client,actors);aid=records[0];url=f'/workspace/partners/{aid}/agreements/new'
    response=client.post(url,data=dict(reference='Authored reference',valid_from='2027-12-31',valid_until='2027-01-01'))
    assert response.status_code==200 and b'value="Authored reference"' in response.data
    assert b'value="2027-12-31"' in response.data and b'data-form-errors' in response.data
    response=client.post(url,data={'reference':'New MOA','valid_from':'2027-01-01','valid_until':'2027-12-31','document':(docx(),'new.docx')})
    assert response.status_code==302 and '/agreements/' in response.location
    assert PartnerAgreement.query.filter_by(reference='New MOA').count()==1


def test_agency_and_agreement_pagination(client,actors,records):
    sign_in(client,actors);aid=records[0]
    for n in range(26):
        db.session.add(PartnerAgency(name=f'Agency {n:02}',contact_name='Contact',campus_id=1))
        db.session.add(PartnerAgreement(agency_id=aid,reference=f'MOA-{n:02}',valid_from=date(2026,1,1),valid_until=date(2030,1,1),document={'name':'file.pdf','path':'missing.pdf'}))
    db.session.commit()
    assert b'Page 2 of 2' in client.get('/workspace/partners?page=2').data
    assert b'Page 2 of 2' in client.get(f'/workspace/partners/{aid}?page=2').data


def test_current_status_is_separate_from_activity_applicability(client,actors,records):
    from unittest.mock import patch
    sign_in(client,actors);aid,_,mid,_=records;new_draft(actors)
    with patch('app.routes.workspace.local_now',return_value=datetime(2028,1,1)):
        page=client.get(f'/workspace/partners/{aid}/agreements/{mid}?activity_context=create')
    assert b'Expired' in page.data and b'Covers Activity Date' in page.data and b'Use This MOA' in page.data
    with patch('app.routes.workspace.local_now',return_value=datetime(2026,1,1)):
        assert b'Upcoming' in client.get(f'/workspace/partners/{aid}/agreements/{mid}').data


def test_use_moa_csrf_and_draft_isolation(client,app,actors,records):
    sign_in(client,actors);aid,_,mid,_=records;draft=new_draft(actors);before=deepcopy(draft.payload)
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post(f'/workspace/partners/{aid}/agreements/{mid}/use?activity_context=create').status_code==400
    assert draft.payload==before
    app.config['WTF_CSRF_ENABLED']=False
    draft.campus_id=2;db.session.commit()
    assert client.post(f'/workspace/partners/{aid}/agreements/{mid}/use?activity_context=create').status_code==403
    assert draft.payload==before


def test_legacy_agency_draft_resume_stays_private(client,actors):
    sign_in(client,actors)
    key='form:/workspace/partners?q=Authored'
    client.put('/workspace/drafts/'+quote(key,safe=''),json={'name':['Authored saved agency'],'contact_name':['Saved contact']})
    assert b'/workspace/partners/new?resume=' in client.get('/workspace/drafts').data
    assert client.get('/workspace/partners/new?resume='+quote(key,safe='')).status_code==200
    sign_in(client,actors,'other')
    assert client.get('/workspace/partners/new?resume='+quote(key,safe='')).status_code==404


def test_agency_list_query_count_stays_bounded(client,app,actors,records):
    from sqlalchemy import event
    sign_in(client,actors);queries=[]
    def capture(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT') and 'partner_' in statement:
            queries.append(statement)
    event.listen(db.engine,'before_cursor_execute',capture)
    try:
        assert client.get('/workspace/partners').status_code==200
        baseline=len(queries)
        db.session.add_all([PartnerAgency(name=f'Budget Agency {n}',contact_name='Contact',campus_id=1) for n in range(25)])
        db.session.commit();queries.clear()
        assert client.get('/workspace/partners').status_code==200
        assert len(queries)<=baseline+1
    finally:
        event.remove(db.engine,'before_cursor_execute',capture)
