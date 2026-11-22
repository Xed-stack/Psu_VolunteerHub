"""Posting essentials retain proposal capture, draft content and publication rules."""
import json
import pytest
from app.models import db
from app.models.event import Event
from app.models.workspace import ActivityProposal
from app.services.proposal_record import validate_posting_record, validate_record, capture_proposal, normalize_record
from tests.test_app import app, client
from tests.test_workspace_overhaul import actors
from tests.test_proposal_record import seed_draft, filled_docx


def test_posting_ignores_incomplete_detailed_proposal_and_retains_it(client, actors):
    record={'partnership_status':'none','rationale':'Saved authored rationale',
            'budget':[{'item':'Saved budget item','unit_cost':'invalid'}]}
    draft=seed_draft(client,actors,record)
    before=normalize_record(draft.payload['proposal_record'][0])
    assert validate_record(before) and not validate_posting_record(before)
    for step in (2,3,4):
        html=client.get(f'/workspace/create/{step}').text
        assert 'name="pr.budget' not in html and 'name="pr.rationale"' not in html
        assert 'value="budget" required' not in html
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes'})
    assert response.status_code==302,response.text
    proposal=ActivityProposal.query.one()
    assert {key:value for key,value in proposal.content.items() if key!='_form_profile'}==before
    html=client.get(f'/workspace/activities/{proposal.event_id}/proposal-record').text
    assert 'Public description only' in html
    assert 'Total Requested' not in html and 'Budget Applies' not in html


@pytest.mark.parametrize('key,value,message',[
    ('title','','Complete Activity Title'),
    ('description','','Complete Public Activity Description'),
    ('date','invalid','start'),
    ('end_date','','end'),
    ('category','Unavailable','Category'),
    ('sdg_ids',[],'Sustainable Development Goal'),
    ('slots','0','Volunteer Registration Slots'),
    ('target_participants','0','Total Participant Target'),
    ('cancellation_days','366','Withdrawal'),
    ('expected_partner_participants','5','primary partner'),
    ('departments',['Other campus department'],'campus'),
])
def test_direct_publication_still_checks_posting_fields(client,actors,key,value,message):
    draft=seed_draft(client,actors,{'partnership_status':'none'})
    draft.payload=dict(draft.payload,**{key:value if isinstance(value,list) else [value]})
    db.session.commit()
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes'})
    assert response.status_code==200 and message.lower() in response.text.lower()
    assert ActivityProposal.query.count()==0


def test_posting_steps_and_autosave_preserve_hidden_proposal_details(client,actors):
    draft=seed_draft(client,actors)
    before=json.loads(draft.payload['proposal_record'][0])
    assert client.post('/workspace/create/2',data={'description':'Edited summary','sdg_ids':draft.payload['sdg_ids'],'save_step':'3'}).status_code==302
    assert client.post('/workspace/create/3',data={'pr.partnership_status':'none','slots':'12','save_step':'4'}).status_code==302
    assert client.put('/workspace/drafts/activity:new',json={'title':['Saved title']}).status_code==200
    db.session.refresh(draft)
    saved=json.loads(draft.payload['proposal_record'][0])
    assert {key:saved[key] for key in before}==before
    assert saved['agency_id']==''
    assert draft.payload['description']==['Edited summary'] and draft.payload['title']==['Saved title']
    assert client.post('/workspace/create/4',data={'proposal_reviewed':'yes'}).status_code==302
    assert Event.query.filter_by(title='Saved title').one().slots==12


def test_only_posting_capture_requires_confirmation(client,actors):
    draft=seed_draft(client,actors,{'partnership_status':'none'})
    draft.payload=dict(draft.payload,_capture={
        'budget':{'state':'Needs Review','source':'Budget','excerpt':'Detailed rows'},
        'title':{'state':'Needs Review','source':'Retained','excerpt':'Saved title'}})
    db.session.commit()
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes'})
    assert response.status_code==200 and 'Confirm the captured posting details' in response.text
    assert 'value="title" required' in response.text and 'value="budget" required' not in response.text
    assert client.post('/workspace/create/4',data={'proposal_reviewed':'yes','capture_confirmed':['title']}).status_code==302


def test_explicit_public_description_is_captured_without_promoting_private_rationale():
    from io import BytesIO
    from zipfile import ZipFile
    source=filled_docx()
    output=BytesIO()
    with ZipFile(source) as original, ZipFile(output,'w') as replacement:
        xml=original.read('word/document.xml').decode()
        xml=xml.replace('</w:body>','<w:p><w:r><w:t>Public Activity Description: Help with a community workshop.</w:t></w:r></w:p></w:body>')
        replacement.writestr('word/document.xml',xml)
    _,operational,_,_=capture_proposal(output.getvalue(),'proposal.docx')
    assert operational['description']=='Help with a community workshop.'
    _,operational,_,_=capture_proposal(filled_docx().getvalue(),'proposal.docx')
    assert 'description' not in operational
