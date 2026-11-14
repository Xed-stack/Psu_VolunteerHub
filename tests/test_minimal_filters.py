"""Primary/More presentation must not change authorized filter semantics."""
from urllib.parse import parse_qs,urlsplit
from app.models import db
from app.models.event import Event
from tests.test_workspace_overhaul import app,client,actors,sign_in
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html,form_with_control,form_values


def test_reports_primary_more_count_and_inactive_period_fields(client,app,actors):
    sign_in(client,actors,'director')
    response,_=screen(client,app,'/workspace/reports/results?year=2026&period=annual&category=No+such+category&sex=female&campus=1&campus=2')
    page=parse_html(response.get_data(as_text=True));form=form_with_control(page,'period')
    more=form.one('details',**{'class':'filter-more'})
    assert 'open' not in more.attrs
    assert '3 Active' in more.text
    assert not more.all('details')
    assert {i.attrs['name'] for i in more.all('select')} >= {'department','event_id','category','attention','sdg_id','sex','affiliation','campus_mode'}
    assert not more.all('input',name='activity_name')
    assert 'data-period-inactive' in next(label for label in form.all('label') if 'data-period-segment' in label.attrs).attrs
    assert form_values(form)['campus'] == ['1','2']
    assert form_values(form)['category'] == ['No such category']
    assert len(form.all('button')) == 1


def test_aop_has_only_relevant_scope_controls(client,actors):
    sign_in(client,actors,'director')
    page=parse_html(client.get('/workspace/reports/aop').get_data(as_text=True))
    form=form_with_control(page,'year')
    assert {control.attrs['name'] for tag in ('input','select') for control in form.all(tag)} == {'year','campus_id'}
    assert not form.all('details')
    sign_in(client,actors)
    form=form_with_control(parse_html(client.get('/workspace/reports/aop?campus_id=2').get_data(as_text=True)),'year')
    assert not form.all('select',name='campus_id')


def test_specialist_alias_clear_and_reset_preserve_other_filters(client,actors):
    sign_in(client,actors,'director')
    path='/workspace/reports/results?period=all&q=100%25_&college_affiliation=Mixed+Affiliation&sex=female&campus=1&campus=2&page=1'
    page=parse_html(client.get(path).get_data(as_text=True))
    form=form_with_control(page,'period');values=form_values(form)
    assert values['activity_name']==['100%_'] and values['affiliation']==['Mixed Affiliation']
    assert 'q' not in values and 'college_affiliation' not in values
    assert values['campus']==['1','2'] and 'page' not in values
    assert '3 Active' in form.text
    chip=next(a for a in page.all('a') if a.attrs.get('aria-label','').startswith('Remove Search:'))
    query=parse_qs(urlsplit(chip.attrs['href']).query)
    assert 'q' not in query and 'activity_name' not in query
    assert query['sex']==['female'] and query['campus']==['1','2'] and 'page' not in query
    reset=next(a for a in form.all('a') if a.text=='Reset Filters')
    assert not parse_qs(urlsplit(reset.attrs['href']).query)


def test_coordinator_scope_and_authored_case_stay_unchanged(client,app,actors):
    event=Event.query.first();event.title='aUTHORED title in PSU 100%_';event.conducting_department='MiXeD department';db.session.commit()
    sign_in(client,actors)
    response,data=screen(client,app,'/workspace/reports/results?period=all&campus_id=2&campus=2&activity_name=100%25_')
    assert data['campus_id']==1 and b'aUTHORED title in PSU 100%_' in response.data
    form=form_with_control(parse_html(response.get_data(as_text=True)),'period')
    assert not form.all('select',name='campus_id') and not form.all('input',name='campus')
    assert b'MiXeD department' in response.data
    assert Event.query.first().title=='aUTHORED title in PSU 100%_'


def test_other_more_forms_and_historical_year_range_preservation(client,actors):
    sign_in(client,actors,'director')
    for path,primary,secondary in [('/workspace/activities','q','category'),('/admin_dash','search','role'),
            ('/workspace/reports/historical?year=2025&start_year=2020&end_year=2026','year','start_year'),
            ('/annual-goals','year','program')]:
        response=client.get(path);assert response.status_code==200
        form=form_with_control(parse_html(response.get_data(as_text=True)),primary)
        more=form.one('details',**{'class':'filter-more'})
        assert more.all('input',name=secondary) or more.all('select',name=secondary)
        if 'historical' in path:
            values=form_values(form)
            assert values['year']==['2025'] and values['start_year']==['2020'] and values['end_year']==['2026']
    sign_in(client,actors,'volunteer')
    for path,primary,secondary in [('/workspace/registrations','q','start_date'),('/opportunities','search','category')]:
        form=form_with_control(parse_html(client.get(path).get_data(as_text=True)),primary)
        assert 'More Filters' in form.text
        assert len(form.all('details'))==1


def test_newspaper_case_and_sentence_copy(client,actors):
    sign_in(client,actors,'director')
    text=client.get('/workspace/reports/results').get_data(as_text=True)
    for label in ['Report Filters','More Filters','Reporting Year','Conducting Department','Apply Filters','Reset Filters']:
        assert label in text
    assert 'Reporting Year scopes annual plans' in text
    from flask import g
    g.pop('_login_user',None)
    with client.session_transaction() as session:session.clear()
    public=client.get('/auth/login').get_data(as_text=True)
    assert '>Sign In</button>' in public and 'Registered Email' not in public
