"""Reference-card, optional partner-list and date-only MOA regressions."""
from datetime import date
import json
import pytest
from werkzeug.datastructures import MultiDict
from app.models import db
from app.models.workspace import PartnerAgency,PartnerAgreement,ActivityProposal
from app.services.proposal_record import normalize_record,record_from_form
from tests.test_workspace_overhaul import app,client,actors,sign_in,docx
from tests.test_proposal_record import seed_draft
from tests.test_partner_journey import records
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html


@pytest.fixture
def agencies(actors):
    rows=[PartnerAgency(name=name,contact_name='Synthetic Contact',campus_id=campus)
          for name,campus in [('Primary',1),('Additional A',1),('Additional B',1),('Foreign',2)]]
    db.session.add_all(rows);db.session.commit()
    return [str(row.id) for row in rows]


def test_partner_list_normalizes_deduplicates_and_removes_primary():
    assert normalize_record({'agency_id':'2','additional_agency_ids':['2','3','03','4']})==dict(agency_id='2',additional_agency_ids=['3','4'])
    assert 'additional_agency_ids' not in normalize_record({'agency_id':'2'})
    assert normalize_record({'agency_id':'02','additional_agency_ids':['2','3']})['additional_agency_ids']==['3']
    assert normalize_record({'partnership_status':'none','additional_agency_ids':['3']})['additional_agency_ids']==[]
    assert record_from_form(MultiDict([('pr.present.additional_agency_ids','1')]),{'additional_agency_ids':['3']})['additional_agency_ids']==[]


@pytest.mark.parametrize('value',['1',[1],['bad'],['0'],['1'*30],{},[None]])
def test_invalid_partner_lists_are_refused(value):
    with pytest.raises(ValueError):normalize_record({'additional_agency_ids':value})


def test_multiple_partners_survive_native_save_and_publication(client,actors,agencies):
    primary,a,b,_=agencies
    draft=seed_draft(client,actors,{'partnership_status':'new','agency_id':primary})
    data=MultiDict([('pr.partnership_status','new'),('pr.agency_id',primary),('pr.present.additional_agency_ids','1'),
                    ('pr.additional_agency_ids',a),('pr.additional_agency_ids',b),('slots','20'),('save_draft','yes')])
    assert client.post('/workspace/create/3',data=data).status_code==302
    db.session.refresh(draft);assert json.loads(draft.payload['proposal_record'][0])['additional_agency_ids']==[a,b]
    html=client.get('/workspace/create/4').text
    assert 'Additional A' in html and 'Additional B' in html
    assert client.post('/workspace/create/4',data={'proposal_reviewed':'yes'}).status_code==302
    proposal=ActivityProposal.query.one()
    assert proposal.content['additional_agency_ids']==[a,b] and str(proposal.agency_id)==primary
    assert proposal.publishing_snapshot['Additional Partner Agencies']==['Additional A','Additional B']
    db.session.get(PartnerAgency,int(a)).name='Renamed later';db.session.commit()
    assert 'Additional A' in client.get(f'/workspace/activities/{proposal.event_id}/proposal-record').text


def test_autosave_preserves_and_rejects_foreign_additional_agencies(client,actors,agencies):
    primary,a,b,foreign=agencies
    draft=seed_draft(client,actors,{'partnership_status':'new','agency_id':primary})
    record={'partnership_status':'new','agency_id':primary,'additional_agency_ids':[a,b]}
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps(record)]}).status_code==200
    assert client.put('/workspace/drafts/activity:new',json={'proposal_record':[json.dumps(dict(record,additional_agency_ids=[foreign]))]}).status_code==400
    db.session.refresh(draft);assert json.loads(draft.payload['proposal_record'][0])['additional_agency_ids']==[a,b]


def test_foreign_partner_cannot_publish_and_none_clears_partners(client,actors,agencies):
    primary,a,b,foreign=agencies
    draft=seed_draft(client,actors,{'partnership_status':'new','agency_id':primary,'additional_agency_ids':[foreign]})
    response=client.post('/workspace/create/4',data={'proposal_reviewed':'yes'})
    assert response.status_code==200 and 'belonging to your campus' in response.text
    assert ActivityProposal.query.count()==0
    assert client.post('/workspace/create/3',data={'pr.partnership_status':'none','save_draft':'yes'}).status_code==302
    db.session.refresh(draft);record=json.loads(draft.payload['proposal_record'][0])
    assert record['additional_agency_ids']==[] and record['agency_id']=='' and draft.payload['agreement_id']==[]


def test_agency_and_moa_context_selection_preserves_additional_agencies(client,actors,agencies,records):
    primary,a,b,_=agencies;aid,_,mid,_=records
    draft=seed_draft(client,actors,{'partnership_status':'new','agency_id':primary,'additional_agency_ids':[a,b,str(aid)]})
    assert client.post(f'/workspace/partners/{aid}/use?activity_context=create').status_code==302
    db.session.refresh(draft);record=json.loads(draft.payload['proposal_record'][0])
    assert record['agency_id']==str(aid) and record['additional_agency_ids']==[a,b]
    draft.payload=dict(draft.payload,date=['2027-05-01T09:00'],end_date=['2027-05-01T12:00']);db.session.commit()
    assert client.post(f'/workspace/partners/{aid}/agreements/{mid}/use?activity_context=create').status_code==302
    db.session.refresh(draft);assert json.loads(draft.payload['proposal_record'][0])['additional_agency_ids']==[a,b]


@pytest.mark.parametrize('enabled',[False,True])
def test_reference_card_counts_and_queue_links(client,app,actors,enabled):
    app.config['FINDING_REVIEWS_ENABLED']=enabled;sign_in(client,actors,'director')
    response,context=screen(client,app,'/workspace/overview?period=all')
    summary=context['attention_summary']
    assert sum(row['total'] for row in summary['groups'])==summary['total']
    page=parse_html(response.text)
    section=next(s for s in page.all('section') if 'review-card' in s.attrs.get('class','').split())
    assert 'review-card-warning' in response.text
    assert ('Active reviews requiring your action.' if enabled else 'Generated findings in the selected scope.') in section.text
    if summary['total']:
        links=[a for a in section.all('a') if 'review_group=' in a.attrs.get('href','')]
        assert len(links)==4
        assert all('review_group=' in link.attrs['href'] for link in links)
    if not enabled:assert context['review_summary'] is None and 'Reviewed History' not in section.text


def test_moa_dates_stay_date_only_and_historical_same_day_allowed(client,actors,records):
    sign_in(client,actors);aid=records[0]
    path=f'/workspace/partners/{aid}/agreements/new'
    html=client.get(path).text
    assert 'moa-date-picker' in html and 'data-moa-picker="valid_from"' in html
    assert 'schedule-picker-hour' not in html and 'type="date"' in html
    assert client.post(path,data={'reference':'Historical same day','valid_from':'2020-02-20','valid_until':'2020-02-20','document':(docx(),'historical.docx')}).status_code==302
    agreement=PartnerAgreement.query.filter_by(reference='Historical same day').one()
    assert agreement.valid_from==agreement.valid_until==date(2020,2,20)
