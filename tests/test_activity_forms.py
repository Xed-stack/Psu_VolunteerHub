"""Simplified activity forms preserve drafts, campus scope and legacy consent."""
import io
from datetime import datetime,timedelta
from pathlib import Path
from PIL import Image

from app.models import db
from app.models.event import Event,Registration,SdgGoal
from app.models.user import Skill,User
from app.models.workspace import FormDraft
from app.models.notification import Notification
from app.services.activity_workflow import local_now
from tests.test_workspace_overhaul import app,client,actors,sign_in,docx
from tests.html_helpers import parse_html


def choices():
    if not SdgGoal.query.first():
        db.session.add_all([SdgGoal(number=n,name=f'Goal {n}') for n in range(1,4)])
    if Skill.query.count()<2:
        db.session.add_all([Skill(name='Analysis Skill A'),Skill(name='Analysis Skill B')])
    db.session.commit()
    return Skill.query.order_by(Skill.id).limit(2).all(),SdgGoal.query.order_by(SdgGoal.number).limit(2).all()


def details(event,sdgs):
    future=local_now()+timedelta(days=12)
    return dict(title='Simplified activity',description='Approved activity description',date=future.isoformat(timespec='minutes'),
                end_date=(future+timedelta(hours=2)).isoformat(timespec='minutes'),cancellation_days='2',category=event.category,slots='20',sdg_ids=[str(s.id) for s in sdgs])


def image_file():
    image=io.BytesIO();Image.new('RGB',(10,10),'blue').save(image,format='PNG');image.seek(0);return image


def test_create_ignores_removed_fields_and_cover_is_saved_in_details(client,app,actors,tmp_path):
    sign_in(client,actors);app.static_folder=str(tmp_path/'public')
    skills,sdgs=choices();event=Event.query.first()
    client.post('/workspace/create/1',data={'proposal':(docx(),'approved.docx')})
    draft=FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').one()
    draft.payload=dict(draft.payload,nda_required=['on'],nda_text=['Obsolete NDA'],participation_agreement_text=['Obsolete policy'],volunteer_ids=[str(actors['volunteer'])]);db.session.commit()
    html=client.get('/workspace/create/2').text
    assert all(name not in draft.payload for name in ['nda_required','nda_text','participation_agreement_text','volunteer_ids'])
    assert 'name="cover_image"' in html and '<select name="required_skills"' not in html
    form=dict(details(event,sdgs),required_skills=[str(s.id) for s in skills],cover_image=(image_file(),'cover.png'))
    assert client.post('/workspace/create/2',data=form).status_code==302
    staged=Path(app.config['PRIVATE_UPLOAD_FOLDER'])/'draft-uploads'/draft.payload['_files']['cover_image']['path']
    assert staged.exists() and b'cover.png' in client.get('/workspace/create/2').data
    assert 'name="cover_image"' not in client.get('/workspace/create/3').text
    client.post('/workspace/create/3',data={'nda_required':'on','nda_text':'Forged NDA','participation_agreement_text':'Forged policy','volunteer_ids':str(actors['volunteer'])})
    assert client.post('/workspace/create/4').status_code==302
    published=Event.query.filter_by(title='Simplified activity').one()
    assert not published.nda_required and published.nda_text is None and published.nda_version is None
    assert published.participation_agreement_text is None and published.participation_agreement_version is None
    assert not published.audience.get('volunteer_ids') and published.cover_image_path
    assert (Path(app.static_folder)/published.cover_image_path).exists() and not staged.exists()
    assert FormDraft.query.filter_by(user_id=actors['coordinator'],key='activity:new').count()==0
    sign_in(client,actors,'volunteer')
    assert client.post(f'/opportunities/register/{published.id}').status_code==400
    assert client.post(f'/opportunities/register/{published.id}',data={'accept_agreement':'yes'}).status_code==302
    reg=Registration.query.filter_by(event_id=published.id,user_id=actors['volunteer']).one()
    assert reg.policy_accepted_at and reg.policy_version and reg.nda_accepted_at is None


def test_edit_preserves_legacy_policies_acceptances_and_cleared_skills(client,actors):
    sign_in(client,actors);skills,sdgs=choices();event=Event.query.first();form=details(event,sdgs)
    event.date=local_now()+timedelta(days=10);event.end_date=event.date+timedelta(hours=2);event.lifecycle_status='approved'
    event.participation_agreement_text='Authored policy';event.participation_agreement_version='authored-policy-v1'
    event.nda_required=True;event.nda_text='Authored NDA';event.nda_version='authored-nda-v1';event.required_skills_rel=skills;event.sdgs=sdgs
    event.audience={'departments':['Historical department'],'volunteer_ids':[actors['volunteer']]}
    accepted=datetime.utcnow();reg=Registration(event_id=event.id,user_id=actors['volunteer'],status='confirmed',policy_accepted_at=accepted,policy_version='authored-policy-v1',nda_accepted_at=accepted,nda_version='authored-nda-v1');db.session.add(reg);db.session.commit()
    path=f'/coordinator/events/{event.id}/edit'
    response=client.post(path,data=dict(form,required_skills=[],participation_agreement_text='Overwrite',nda_required='',nda_text='Overwrite NDA'))
    assert response.status_code==302
    assert event.participation_agreement_text=='Authored policy' and event.participation_agreement_version=='authored-policy-v1'
    assert event.nda_required and event.nda_text=='Authored NDA' and event.nda_version=='authored-nda-v1'
    assert reg.policy_accepted_at==accepted and reg.nda_version=='authored-nda-v1'
    assert event.audience['volunteer_ids']==[actors['volunteer']] and not event.required_skills_rel
    event.sdgs=sdgs;db.session.commit()
    response=client.post(path,data=dict(form,sdg_ids=[],required_skills=[]))
    assert b'Select at least one Sustainable Development Goal.' in response.data
    page=parse_html(response.text)
    assert all('checked' not in node.attrs for node in page.all('input') if node.attrs.get('name') in ('required_skills','sdg_ids'))
    assert len([node for node in page.all('input') if node.attrs.get('name')=='required_skills'])>=2
    assert 'name="nda_required"' not in response.text and 'name="participation_agreement_text"' not in response.text
    punctuation=Skill(name='Community Planning, Research');db.session.add(punctuation);db.session.commit()
    assert client.post(path,data=dict(form,required_skills=[punctuation.name])).status_code==302
    assert event.required_skills_rel==[punctuation]


def test_activity_draft_cleanup_is_scoped_and_preserves_upload_metadata(client,actors):
    sign_in(client,actors)
    keys=['activity:new','form:/coordinator/events/1/edit?return_to=/workspace/activities','form:/unrelated-settings']
    for key in keys:
        db.session.add(FormDraft(user_id=actors['coordinator'],campus_id=1,key=key,payload={'title':['Keep me'],'nda_text':['Old draft text'],'volunteer_ids':['99'],'_files':{'cover_image':{'name':'saved.png','path':'saved.png'}}}))
    db.session.commit()
    for key in keys[:2]:
        response=client.get('/workspace/drafts/'+key.replace('?','%3F'))
        assert response.json['payload']=={'title':['Keep me'],'_files':{'cover_image':{'name':'saved.png','path':'saved.png'}}}
        response=client.put('/workspace/drafts/'+key.replace('?','%3F'),json={'required_skills':[],'sdg_ids':[],'nda_required':['on'],'nda_text':['Forged'],'volunteer_ids':['99']})
        assert response.json['payload']['required_skills']==[] and 'nda_text' not in response.json['payload']
    assert client.get('/workspace/drafts/'+keys[2]).json['payload']['nda_text']==['Old draft text']


def test_departments_are_campus_scoped_and_drive_notifications(client,actors):
    sign_in(client,actors);_,sdgs=choices();event=Event.query.first()
    db.session.get(User,actors['volunteer']).college_affiliation='Local fixture department'
    outsider=User(name='Other campus',email='other-campus@example.org',role='volunteer',campus_id=2,college_affiliation='Other campus only',sex='prefer_not_to_say',password_hash='unused');db.session.add(outsider);db.session.commit()
    client.post('/workspace/create/1',data={'proposal':(docx(),'approved.docx')});client.post('/workspace/create/2',data=details(event,sdgs))
    client.post('/workspace/create/3',data={'departments':['Other campus only']})
    assert b'Choose audience departments from the campus list.' in client.post('/workspace/create/4').data
    client.post('/workspace/create/3',data={'departments':['Local fixture department']})
    assert client.post('/workspace/create/4').status_code==302
    assert Notification.query.filter_by(user_id=actors['volunteer'],notification_type='activity_invitation').count()==1
    assert Notification.query.filter_by(user_id=outsider.id,notification_type='activity_invitation').count()==0
