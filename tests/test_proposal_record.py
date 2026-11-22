"""Full proposal capture, draft preservation, isolation and publication acceptance."""
import io
import json
import zipfile
from datetime import timedelta, date
from xml.sax.saxutils import escape
import pytest
from sqlalchemy import create_engine, inspect
from app.models import db
from app.models.workspace import ActivityProposal, FormDraft, PartnerAgency, PartnerAgreement
from app.models.event import Event, SdgGoal
from app.services.activity_workflow import local_now
from app.services.proposal_record import (capture_proposal,normalize_record,validate_record,budget_totals,
    REQUIRED, CHOICES, TABLES)
from app.proposal_migration import migrate_proposals
from tests.test_app import app, client
from tests.test_workspace_overhaul import actors, sign_in, docx


def complete_record():
    result={key:'Authored '+key for key in REQUIRED}
    result.update(beneficiary_count='80',volunteer_count='12',budget_na='no',partnership_status='none',
                  partnership_reason='Delivered by the campus without an external partner.')
    result.update({key:[values[0]] for key,values in CHOICES.items()})
    result['team']=[dict(name='Maria Reyes',designation='Faculty',campus='Lingayen',role='Leader')]
    result['implementation']=[dict(activity='Workshop',people='Project team',timeline='Activity date',output='Completed training')]
    result['budget']=[dict(item='Training kits',unit='kit',quantity='2.5',unit_cost='12.35',classification='Supplies',source='Unit resources')]
    result['risks']=[dict(risk='Heavy rain',impact='Possible / Moderate',mitigation='Indoor venue')]
    return result


def filled_docx(title='Community learning day'):
    paragraphs=[f'I. Title of the Outreach / Volunteer Activity: {title}',
        'II. Campus / Implementing Unit / Degree Program: Lingayen / Education',
        'III. Proponent / Project Leader and Members',
        'IV. Rationale','A documented community need guides this activity.',
        'V. Objectives','General Objectives: Improve learning access.','Specific Objectives: Deliver a workshop.',
        'VI. Methodology','Run a facilitated learning workshop.',
        'VII. Target Beneficiaries','Estimated Number of Beneficiaries: 80','[x] Farmers','[ ] Women',
        'VIII. Volunteer Participation','Estimated Number of Volunteers: 12','[x] Teaching Staff','[x] Health & Well-being',
        'IX. Activity Details','Location / Community: Lingayen community hall','[x] Volunteerism',
        'X. Implementation Plan','XI. Budget Requested','XII. Expected Outcomes','[x] Increased Access to Services',
        'XIII. Monitoring and Evaluation','Use the approved evaluation form.',
        'XIV. Sustainability / Replicability Plan','Repeat workshops with the unit.',
        'XV. Conclusion','Support community learning.',
        'XVI. Partnership & Linkages','Role and Responsibilities of PSU: Provide trainers.',
        'XVII. Risk Management and Contingency Plan','XVIII. Detailed Budget Breakdown']
    def paragraph(text):return '<w:p><w:r><w:t>'+escape(text)+'</w:t></w:r></w:p>'
    tables=[]
    record=complete_record()
    for key,(_,columns) in TABLES.items():
        rows=[[label for _,label in columns]]+[[row[column] for column,_ in columns] for row in record[key]]
        tables.append('<w:tbl>'+''.join('<w:tr>'+''.join('<w:tc>'+paragraph(cell)+'</w:tc>' for cell in row)+'</w:tr>' for row in rows)+'</w:tbl>')
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w') as archive:
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join(map(paragraph,paragraphs))+''.join(tables)+'</w:body></w:document>')
    output.seek(0)
    return output


def seed_draft(client,actors,record=None):
    sign_in(client,actors)
    client.get('/workspace/create/1')
    assert client.post('/workspace/create/1',data={'proposal':(filled_docx(),'approved.docx')}).status_code==302
    draft=FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one()
    if not SdgGoal.query.first():
        db.session.add(SdgGoal(number=4,name='Quality Education'));db.session.commit()
    start=local_now()+timedelta(days=14)
    payload=dict(draft.payload,title=['Published proposal'],description=['Public description only'],
        date=[start.isoformat(timespec='minutes')],end_date=[(start+timedelta(hours=2)).isoformat(timespec='minutes')],
        category=['General'],slots=['20'],cancellation_days=['2'],sdg_ids=[str(SdgGoal.query.first().id)],
        proposal_record=[json.dumps(record or complete_record())])
    draft.payload=payload;db.session.commit()
    return draft


def test_template_capture_values_tables_and_checkbox_states():
    record,values,capture,readable=capture_proposal(filled_docx().getvalue(),'approved.docx')
    assert readable and values['title']=='Community learning day'
    assert values['location']=='Lingayen community hall'
    assert record['beneficiary_count']=='80' and record['volunteer_count']=='12'
    assert record['beneficiary_groups']==['Farmers']
    assert record['team'][0]['name']=='Maria Reyes'
    assert record['risks'][0]['mitigation']=='Indoor venue'
    assert capture['budget']['state']=='Needs Review'
    assert 'documented community' in record['rationale']


def test_blank_template_instructions_are_not_authored_data():
    paragraphs=['I. Title of the Outreach / Volunteer Activity: ______',
        'II. Campus / Implementing Unit / Degree Program: ______',
        'IV. Rationale','(Describe the identified community need or issue.)',
        'V. Objectives','(Cite the general objectives and specific objectives.)',
        'VI. Methodology','(Describe the activities, strategies, and approaches.)',
        'VII. Target Beneficiaries','Estimated Number of Beneficiaries: ______','[ ] Farmers',
        'Prepared By           Noted By            Recommending Approval            Approved By']
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'+''.join('<w:p><w:r><w:t>'+escape(v)+'</w:t></w:r></w:p>' for v in paragraphs)+'</w:document>')
    record,values,_,_=capture_proposal(buffer.getvalue(),'blank.docx')
    assert not record and not values


def test_pdf_capture_and_unreadable_fallback():
    from reportlab.pdfgen.canvas import Canvas
    buffer=io.BytesIO();canvas=Canvas(buffer)
    for index,line in enumerate(['I. Title of the Outreach / Volunteer Activity: PDF learning day',
        'II. Campus / Implementing Unit / Degree Program: Education',
        'IV. Rationale','Authored rationale from a readable PDF.',
        'V. Objectives','General Objectives: Learn together.']):
        canvas.drawString(45,800-index*24,line)
    canvas.save()
    record,values,_,readable=capture_proposal(buffer.getvalue(),'proposal.pdf')
    assert readable and values['title']=='PDF learning day'
    assert 'Authored rationale' in record['rationale']
    assert capture_proposal(b'%PDF-invalid','scan.pdf')==({}, {}, {}, False)


def test_docx_checkbox_control_and_three_column_team_capture():
    xml='''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"><w:body>
    <w:p><w:r><w:t>VII. Target Beneficiaries</w:t></w:r></w:p>
    <w:p><w:sdt><w:sdtPr><w14:checkbox><w14:checked w14:val="1"/></w14:checkbox></w:sdtPr><w:sdtContent><w:r><w:t>☐</w:t></w:r></w:sdtContent></w:sdt><w:r><w:t> Farmers</w:t></w:r></w:p>
    <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Name</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Designation</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Campus</w:t></w:r></w:p></w:tc></w:tr>
    <w:tr><w:tc><w:p><w:r><w:t>Authored Leader</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Faculty</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Lingayen</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
    </w:body></w:document>'''
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:archive.writestr('word/document.xml',xml)
    record,_,capture,_=capture_proposal(buffer.getvalue(),'checkbox.docx')
    assert record['beneficiary_groups']==['Farmers']
    assert record['team'][0]['name']=='Authored Leader' and record['team'][0]['role']==''
    assert capture['team']['state']=='Needs Review'


def test_validation_decimal_totals_and_limits():
    record=complete_record()
    assert validate_record(record)=={}
    assert budget_totals(record)==(['30.88'],'30.88')
    for value in ['-1','NaN','Infinity','0.001','10000000000000']:
        record['budget'][0]['unit_cost']=value
        assert 'budget' in validate_record(record)
    with pytest.raises(ValueError):normalize_record({'rationale':'x'*10001})
    with pytest.raises(ValueError):normalize_record({'team':[{}]*51})
    with pytest.raises(ValueError):normalize_record({'unexpected':[]})
    with pytest.raises(ValueError):normalize_record({'outcomes':['invented option']})


def test_full_draft_capture_render_refresh_and_tables(client,actors):
    sign_in(client,actors)
    assert client.get('/workspace/create/1').status_code==200
    assert client.post('/workspace/create/1',data={'proposal':(filled_docx(),'approved.docx')}).status_code==302
    for step in (2,3,4):
        response=client.get('/workspace/create/'+str(step))
        assert response.status_code==200,response.data[:500]
    assert b'Maria Reyes' in client.get('/workspace/create/2').data
    record=complete_record();record['team'].append(dict(name='Second member',designation='Staff',campus='Lingayen',role='Member'))
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps(record)]}).status_code==200
    assert b'Second member' in client.get('/workspace/create/2').data
    record['team'].pop();record['beneficiary_groups']=[]
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps(record)]}).status_code==200
    draft=FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one()
    assert json.loads(draft.payload['proposal_record'][0])['beneficiary_groups']==[]
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps({'team':[{}]*51})]}).status_code==400


def test_large_record_autosave_is_activity_scoped(client,actors):
    sign_in(client,actors);client.get('/workspace/create/1')
    record={k:'x'*9000 for k in REQUIRED if not k.endswith('_count')}
    assert len(json.dumps(record))>60000
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps(record)]}).status_code==200
    assert client.put('/workspace/drafts/form:/settings',json={'name':['x'*11000]}).status_code==400


def test_publish_review_record_visibility_and_historical_fallback(client,actors):
    seed_draft(client,actors)
    assert client.post('/workspace/create/4').status_code==200
    assert not ActivityProposal.query.count()
    assert client.post('/workspace/create/4',data={'save_step':'2'}).status_code==302
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':list(TABLES)})
    assert response.status_code==302,response.data[:1000]
    event=Event.query.filter_by(title='Published proposal').one()
    assert event.target_participants is None and event.slots==20
    assert db.session.get(ActivityProposal,event.id).content['beneficiary_count']=='80'
    assert FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').first() is None
    url=f'/workspace/activities/{event.id}/proposal-record'
    assert b'Public description only' in client.get(url).data
    proposal=db.session.get(ActivityProposal,event.id)
    assert proposal.content['_form_profile']=='posting_essentials_v1'
    # Previously published full records retain their detailed presentation.
    proposal.content={key:value for key,value in proposal.content.items() if key!='_form_profile'}
    db.session.commit()
    assert b'Authored rationale' in client.get(url).data
    sign_in(client,actors,'director');assert client.get(url).status_code==200
    sign_in(client,actors,'other');assert client.get(url).status_code==404
    sign_in(client,actors,'volunteer');assert client.get(url).status_code==403
    sign_in(client,actors)
    historical=Event.query.filter(Event.id!=event.id).first()
    assert b'Digital Proposal Details Not Recorded' in client.get(f'/workspace/activities/{historical.id}/proposal-record').data


def test_no_javascript_rows_save_and_validation_retention(client,actors):
    seed_draft(client,actors)
    response=client.post('/workspace/create/2',data={'pr.rationale':'Changed rationale','pr.present.team':'1',
        'pr.team.name':['Maria Reyes','Ben Santos'],'pr.team.designation':['Faculty','Staff'],
        'pr.team.campus':['Lingayen','Lingayen'],'pr.team.role':['Leader','Member'],'row_action':'add:team:0'})
    assert response.status_code==302
    response=client.get('/workspace/create/2')
    assert b'Ben Santos' in response.data and b'Changed rationale' in response.data
    assert b'name="pr.team.name"' not in response.data
    draft=FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one()
    assert len(json.loads(draft.payload['proposal_record'][0])['team'])==2


def test_replacement_compares_and_preserves_authored_values(client,actors):
    draft=seed_draft(client,actors);previous=draft.payload['_proposal']['path']
    response=client.post('/workspace/create/1',data={'proposal':(filled_docx('Replacement title'),'replacement.docx')})
    assert response.status_code==302
    db.session.refresh(draft)
    assert draft.payload['_proposal']['path']==previous
    assert b'Review Replacement Proposal' in client.get('/workspace/create/1').data
    client.post('/workspace/create/1',data={'apply_replacement':'yes','replace_fields':['title']})
    db.session.refresh(draft)
    assert draft.payload['title']==['Replacement title']
    assert json.loads(draft.payload['proposal_record'][0])['rationale']=='Authored rationale'
    assert draft.payload['_proposal']['path']!=previous


def test_agency_selection_and_wrong_agreement_rejected(client,actors):
    draft=seed_draft(client,actors)
    agencies=[PartnerAgency(name=name,contact_name='Contact',campus_id=campus) for name,campus in [('Agency One',1),('Agency Two',1),('Foreign',2)]]
    db.session.add_all(agencies);db.session.commit()
    response=client.post(f'/workspace/partners/{agencies[0].id}/use?activity_context=create')
    assert response.status_code==302
    db.session.refresh(draft);record=json.loads(draft.payload['proposal_record'][0])
    assert record['agency_id']==str(agencies[0].id) and record['partnership_status']=='new'
    assert draft.payload['_proposal']
    assert client.post(f'/workspace/partners/{agencies[2].id}/use?activity_context=create').status_code==404
    assert b'Use This Agency' in client.get(f'/workspace/partners/{agencies[0].id}?activity_context=create').data
    agreement=PartnerAgreement(agency_id=agencies[1].id,reference='WRONG',valid_from=date(2020,1,1),valid_until=date(2099,1,1),document=draft.payload['_proposal'])
    db.session.add(agreement);db.session.flush()
    record.update(psu_roles='Trainers',partner_roles='Venue',partnership_duration='One day',partnership_status='existing')
    draft.payload=dict(draft.payload,proposal_record=[json.dumps(record)],agreement_id=[str(agreement.id)]);db.session.commit()
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':list(TABLES)})
    assert response.status_code==200 and b'belong to the selected agency' in response.data
    assert not ActivityProposal.query.count()


def test_legacy_draft_remains_legacy_until_explicit_upgrade(client,actors):
    sign_in(client,actors)
    draft=FormDraft(user_id=actors['coordinator'],campus_id=1,key='activity:new',payload={'title':['Preserved legacy title'],'_proposal':{'name':'old.docx','path':'old.docx'}})
    db.session.add(draft);db.session.commit()
    assert b'Use the Shorter Posting Form' in client.get('/workspace/create/1').data
    assert b'Preserved legacy title' in client.get('/workspace/create/2').data
    assert client.post('/workspace/create/1',data={'upgrade_proposal':'yes'}).status_code==302
    db.session.refresh(draft)
    assert draft.payload['_full_proposal']==1 and draft.payload['title']==['Preserved legacy title']


def test_publication_failure_rolls_back_activity_and_keeps_draft(client,actors,monkeypatch):
    from sqlalchemy.exc import SQLAlchemyError
    import app.routes.workspace as workspace
    seed_draft(client,actors)
    before=Event.query.count()
    def fail(event):raise SQLAlchemyError('Simulated transaction failure')
    monkeypatch.setattr(workspace,'notify_audience',fail)
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':list(TABLES)})
    assert response.status_code==200 and b'saved draft is retained' in response.data
    assert Event.query.count()==before and not ActivityProposal.query.count()
    assert FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one().payload['_proposal']


def test_draft_discard_cleans_only_its_private_files(client,actors):
    from pathlib import Path
    from flask import current_app
    draft=seed_draft(client,actors)
    saved=Path(current_app.config['PRIVATE_UPLOAD_FOLDER'])/'proposals'/draft.payload['_proposal']['path']
    untouched=saved.with_name('unrelated.pdf');untouched.write_bytes(b'keep')
    assert saved.is_file()
    assert client.delete('/workspace/drafts/activity:new').status_code==204
    assert not saved.exists() and untouched.read_bytes()==b'keep'


@pytest.mark.parametrize('status',['existing','renewal','new'])
def test_full_partnership_publication_documents_and_snapshot(client,actors,status):
    from datetime import datetime
    draft=seed_draft(client,actors)
    agency=PartnerAgency(name='Campus partner',contact_name='Contact',campus_id=1)
    db.session.add(agency);db.session.flush()
    content=complete_record();content.update(partnership_status=status,agency_id=str(agency.id),
        psu_roles='Provide staff',partner_roles='Provide venue',partnership_duration='One activity day')
    payload=dict(draft.payload,proposal_record=[json.dumps(content)])
    if status=='existing':
        start=datetime.fromisoformat(payload['date'][0]).date()
        agreement=PartnerAgreement(agency_id=agency.id,reference='SIGNED',valid_from=start,
            valid_until=start+timedelta(days=30),document=payload['_proposal'])
        db.session.add(agreement);db.session.flush();payload['agreement_id']=[str(agreement.id)]
    draft.payload=payload;db.session.commit()
    if status!='existing':
        assert client.post('/workspace/create/3',data={'partnership_document':(docx(),'draft-agreement.docx')}).status_code==302
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':list(TABLES)})
    assert response.status_code==302,response.text[:500]
    event=Event.query.filter_by(title='Published proposal').one()
    proposal=db.session.get(ActivityProposal,event.id)
    assert proposal.agency_id==agency.id
    assert bool(event.agreement_id)==(status=='existing')
    assert b'Authored rationale' not in client.get(f'/opportunities/{event.id}').data
    event.description='Later operational description';db.session.commit()
    record=client.get(f'/workspace/activities/{event.id}/proposal-record')
    assert b'Public description only' in record.data
    if status!='existing':
        url=f'/workspace/activities/{event.id}/partnership-draft'
        assert client.get(url).status_code==200
        sign_in(client,actors,'director');assert client.get(url).status_code==200
        sign_in(client,actors,'volunteer');assert client.get(url).status_code==403


def test_migration_dry_run_exact_target_and_repeatability():
    engine=create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.exec_driver_sql('CREATE TABLE events (id INTEGER PRIMARY KEY)')
        connection.exec_driver_sql('CREATE TABLE partner_agencies (id INTEGER PRIMARY KEY)')
    with pytest.raises(ValueError):migrate_proposals(engine,'wrong',True)
    assert migrate_proposals(engine,':memory:',True)
    assert 'activity_proposals' not in inspect(engine).get_table_names()
    assert migrate_proposals(engine,':memory:')
    assert migrate_proposals(engine,':memory:')==[]


def test_development_startup_requires_explicit_proposal_migration(tmp_path,monkeypatch):
    from app import create_app
    from config import DevelopmentConfig
    target=tmp_path/'migration-only.sqlite'
    monkeypatch.setattr(DevelopmentConfig,'SQLALCHEMY_DATABASE_URI','sqlite:///'+target.as_posix())
    app=create_app('development')
    with app.app_context():
        assert not inspect(db.engine).has_table('activity_proposals')
        database_name=db.engine.url.database
    result=app.test_cli_runner().invoke(args=['migrate-proposals','--database',database_name,'--dry-run'])
    assert result.exit_code==0,result.output
    with app.app_context():assert not inspect(db.engine).has_table('activity_proposals')
    result=app.test_cli_runner().invoke(args=['migrate-proposals','--database',database_name])
    assert result.exit_code==0,result.output
    with app.app_context():assert inspect(db.engine).has_table('activity_proposals')
