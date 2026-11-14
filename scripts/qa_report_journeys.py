"""Exercise reports and annual evidence in Chromium with disposable data."""
import json
import logging
import sys
from datetime import datetime,timedelta
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit,parse_qs

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event,Registration,Attendance,ExternalParticipant
from app.models.annual_plan import AnnualGoalProposal
from app.services.activity_workflow import local_now
from tests.test_annual_goals import target,definition
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app('testing');cookies={};checks=[];errors=[]
    out=Path('.qa-overhaul-temp/report-journeys/browser');out.mkdir(parents=True,exist_ok=True)
    with app.app_context():
        for role in ['director','coordinator','volunteer']:
            user=User.query.filter_by(role=role).first()
            if not user:
                user=User(name=role.title(),email=role+'@example.org',role=role,campus_id=1,password_hash='unused');db.session.add(user)
            user.sex='prefer_not_to_say';user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
            if role=='volunteer':volunteer_id=user.id
            if role=='director':director_id=user.id
        event=Event.query.first();event.title='ReportJourney 100%_ literal: community learning and coastal conservation with volunteers';event.date=local_now()-timedelta(days=3);event.end_date=event.date+timedelta(hours=2);event_id=event.id
        reg=Registration(event_id=event.id,user_id=volunteer_id,status='confirmed');db.session.add(reg);db.session.flush();db.session.add(Attendance(event_id=event.id,registration_id=reg.id,status='present'))
        for i in range(27):
            person=ExternalParticipant(id_number=f'QA-REPORT-{i:02}',name=f'External fixture {i:02}');db.session.add(person);db.session.flush();db.session.add(Registration(event_id=event.id,external_participant_id=person.id,status='confirmed'))
        university=target(actual=4);campus=target(campus=1,actual=4,shared='campus-shared');target(campus=1,kind='ASP',actual=4,shared='campus-shared');target(campus=2)
        other=target(actual=2);other.indicator.unit='activities';target()
        proposal=AnnualGoalProposal(campus_id=1,payload=definition(),status='submitted',proposed_by_id=director_id,history=[dict(action='submitted',at=datetime.utcnow().isoformat(),actor=director_id)])
        db.session.add(proposal);db.session.commit();target_id=university.id;campus_target_id=campus.id;proposal_id=proposal.id
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            scenarios={
                'director':['/workspace/reports','/workspace/reports/results?period=all','/workspace/reports/results?period=all&view=activities','/workspace/reports/results?period=all&view=participation',f'/workspace/reports/activities/{event_id}','/workspace/reports/aop','/workspace/reports/aop?campus_id=1','/annual-goals','/annual-goals?view=campuses',f'/annual-goals/targets/{target_id}',f'/annual-goals/targets/{target_id}/evidence','/annual-goals/workspace',f'/annual-goals/proposals/{proposal_id}','/annual-goals?sample=1','/workspace/reports/historical','/workspace/reports/people'],
                'coordinator':['/workspace/reports/results?period=all',f'/workspace/reports/activities/{event_id}','/workspace/reports/aop','/annual-goals',f'/annual-goals/targets/{campus_target_id}','/annual-goals/proposals/new'],
                'volunteer':['/volunteer_dash']}
            for role,paths in scenarios.items():
                context=browser.new_context(has_touch=True,reduced_motion='reduce');context.add_cookies([dict(name='session',value=cookies[role],url=base)])
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    for index,path in enumerate(paths):
                        response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(role,path,response.status)
                        if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                            page.screenshot(path=str(out/'overflow.png'),full_page=True)
                            raise AssertionError((role,path,width,'overflow',page.evaluate("[...document.querySelectorAll('main *')].filter(e=>{if(e.getBoundingClientRect().right<=innerWidth+1)return false;return !e.closest('.table-wrap,.table-scroll');}).slice(0,10).map(e=>[e.tagName,e.className])")))
                        if width in (1440,390):page.screenshot(path=str(out/f'{role}-{index}-{width}.png'),full_page=True)
                        checks.append([role,path,width,height])
                for path in paths:
                    page.set_viewport_size(dict(width=320,height=800));page.goto(base+path);page.evaluate("document.documentElement.style.fontSize='200%'");page.wait_for_timeout(100)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,path,'200% text')
                    checks.append([role,path,'200% text'])
                context.close()
            context=browser.new_context(viewport=dict(width=390,height=844));context.add_cookies([dict(name='session',value=cookies['director'],url=base)]);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            origin='/workspace/reports/results?period=all&activity_name=100%25_&campus=1&campus=2'
            page.goto(base+origin);tabs=page.get_by_role('navigation',name='Report Views',exact=True)
            assert page.locator('.activity-report-table').count()==0 and page.locator('.participation-report-table').count()==0
            page.wait_for_function("document.querySelector('[data-month-chart]')._fullLayout !== undefined")
            assert page.locator('[data-month-chart]').evaluate('e=>e._fullLayout.yaxis.range[0] < e._fullLayout.yaxis.range[1]')
            tabs.get_by_role('link',name='Activity Records',exact=True).focus();page.keyboard.press('Enter');page.wait_for_load_state('networkidle')
            assert parse_qs(urlsplit(page.url).query)['campus']==['1','2'] and page.locator('.activity-report-table mark').count()==1
            record_origin=page.url.removeprefix(base)
            page.locator('.activity-report-table th a,.activity-report-table td a').first.click();page.wait_for_load_state('networkidle')
            assert urlsplit(page.url).path==f'/workspace/reports/activities/{event_id}'
            assert '25 of 28' in page.locator('main').inner_text()
            page.get_by_role('navigation',name='Roster Pages').get_by_role('link',name='Next',exact=True).click();assert '3 of 28' in page.locator('main').inner_text()
            assert context.request.get(base+page.get_by_role('link',name='Export CSV',exact=True).get_attribute('href')).status==200
            page.get_by_role('link',name='Back to Report Results',exact=True).click();page.wait_for_load_state('networkidle');assert page.url.removeprefix(base)==record_origin
            checks.append(['tabs, literal highlight, repeated campus, combined report, roster pagination, export and Back'])
            page.goto(base+'/workspace/reports/aop');assert page.locator('[data-target-group]').count()==2
            page.locator('.annual-indicator-table a').first.click();page.wait_for_load_state('networkidle');assert '/annual-goals/targets/' in urlsplit(page.url).path
            original=page.url.removeprefix(base);page.get_by_role('link',name='Manage AOP Evidence',exact=True).click();page.wait_for_load_state('networkidle')
            page.get_by_role('link',name='Back to Indicator',exact=True).click();page.wait_for_load_state('networkidle');assert page.url.removeprefix(base)==original
            checks.append(['unit-group charts, exact indicator and evidence Back'])
            page.goto(base+'/annual-goals?sample=1');assert page.locator('a[href*="/annual-goals/targets/"]').count()==0
            page.goto(base+'/workspace/reports/results?activity_name=NoMatchingReportJourney');assert '0 matching activities' in page.locator('main').inner_text()
            checks.append(['sample isolation and empty scope'])
            page.goto(base+f'/workspace/reports/activities/{event_id}');page.emulate_media(media='print');page.pdf(path=str(out/'activity-print.pdf'),format='A4',landscape=True)
            page.goto(base+'/workspace/reports/aop');page.pdf(path=str(out/'annual-print.pdf'),format='A4',landscape=True);page.emulate_media(media='screen')
            checks.append(['activity and annual print PDFs'])
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8');print(f'{len(checks)} report browser checks passed; no page script errors. Artifacts: {out}')


if __name__=='__main__':main()
