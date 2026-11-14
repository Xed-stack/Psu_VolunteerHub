"""Bounded Chromium checks for activity journeys, using disposable data only."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event, Registration
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app('testing')
    out=Path('.qa-overhaul-temp/activity-journeys/browser');out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];cookies={};events={}
    with app.app_context():
        for role in ['volunteer','coordinator','director']:
            user=User.query.filter_by(role=role).first()
            if not user:
                user=User(name=role.title(),email=role+'@example.org',role=role,campus_id=1,password_hash='unused');db.session.add(user)
            user.sex='prefer_not_to_say';user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
            if role=='volunteer':volunteer_id=user.id
        now=local_now()
        empty_user=User(name='No interests selected',email='empty-journey@example.org',role='volunteer',campus_id=1,password_hash='unused',sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
        db.session.add(empty_user);db.session.flush()
        cookies['empty']=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(empty_user.id),_fresh=True,auth_version=empty_user.auth_version))
        for kind,offset in [('upcoming',10),('ongoing',0),('ended',-2),('legacy',-3),('cancelled',12),('unlimited',15),('join',18)]:
            date=now+timedelta(days=offset) if offset else now-timedelta(minutes=30)
            event=Event(title=('Community Learning and Coastal Conservation with Campus Volunteers ' * 2 if kind=='upcoming' else 'Journey '+kind),description='Authored activity description.\nKeep schedule and requirements readable.',date=date,end_date=None if kind=='legacy' else date+timedelta(hours=2),campus_id=1,category='Environment',slots=0 if kind=='unlimited' else 30,location='PSU community learning centre',lifecycle_status='cancelled' if kind=='cancelled' else 'approved',cancellation_deadline=date-timedelta(days=1),nda_required=kind=='join',nda_text='Authored NDA for this activity.',nda_version='internal-nda-version')
            if kind=='unlimited':event.cover_image_path='assets/FB_IMG_1788789005999.jpg'
            db.session.add(event);db.session.flush();events[kind]=event.id
            if kind=='upcoming':
                reg=Registration(event_id=event.id,user_id=volunteer_id,status='confirmed');db.session.add(reg);db.session.flush();registration_id=reg.id
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            scenarios={
                'volunteer':['/volunteer_dash?view=recommended','/volunteer_dash?view=calendar','/opportunities',f'/opportunities/{events["upcoming"]}',f'/opportunities/register/{events["join"]}',f'/workspace/registrations/{registration_id}',f'/registrations/{registration_id}/cancel'],
                'coordinator':[f'/workspace/activities/{events[k]}' for k in ['upcoming','ongoing','ended','legacy','cancelled']],
                'public':['/opportunities',f'/opportunities/{events["join"]}',f'/opportunities/{events["unlimited"]}'],
                'empty':['/volunteer_dash','/opportunities?search=NoSuchJourneyActivity'],
                'director':['/workspace/overview']}
            for role,paths in scenarios.items():
                context=browser.new_context(has_touch=True,reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                if role!='public':context.add_cookies([dict(name='session',value=cookies[role],url=base)])
                for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    for index,path in enumerate(paths):
                        response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(role,path,response.status)
                        if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                            page.screenshot(path=str(out/'overflow.png'),full_page=True)
                            raise AssertionError((role,path,width,'overflow',page.evaluate("[...document.querySelectorAll('main *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(e=>[e.tagName,e.className])")))
                        if width in (1440,390):page.screenshot(path=str(out/f'{role}-{index}-{width}.png'),full_page=True)
                        checks.append([role,path,width,height])
                for path in paths:
                    page.set_viewport_size(dict(width=320,height=800));page.goto(base+path);page.evaluate("document.documentElement.style.fontSize='200%'")
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,path,'200% text')
                    checks.append([role,path,'200% text'])
                context.close()
            context=browser.new_context(viewport=dict(width=390,height=844));context.add_cookies([dict(name='session',value=cookies['volunteer'],url=base)])
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+f'/opportunities/{events["upcoming"]}')
            page.get_by_role('link',name='View Your Registration',exact=True).click();assert urlsplit(page.url).path==f'/workspace/registrations/{registration_id}'
            page.get_by_role('link',name='Withdraw',exact=True).click();page.get_by_role('link',name='Keep Registration',exact=True).click()
            assert urlsplit(page.url).path==f'/workspace/registrations/{registration_id}'
            checks.append(['registered destination and withdrawal Back'])
            page.goto(base+f'/opportunities/{events["cancelled"]}');assert 'This activity has started.' not in page.locator('main').inner_text()
            page.goto(base+f'/opportunities/{events["unlimited"]}');assert 'No capacity limit' in page.locator('main').inner_text()
            checks.append(['cancelled and unlimited states'])
            origin='/opportunities?search=Journey&campus=1&campus=2'
            page.goto(base+origin);page.locator(f'.journey-activity-row a[href^="/opportunities/{events["join"]}?"]').first.click()
            page.get_by_role('link',name='Review and Join',exact=True).click()
            page.locator('#accept_agreement').check();page.reload();assert not page.locator('#accept_agreement').is_checked()
            assert page.locator('.draft-status').count()==0
            page.locator('#accept_agreement').check();page.locator('#accept_nda').check();page.get_by_role('button',name='Agree and Join',exact=True).click();page.wait_for_load_state('networkidle')
            assert '/workspace/registrations/' in urlsplit(page.url).path
            assert parse_qs(urlsplit(page.url).query)['return_to']==[origin]
            page.get_by_role('link',name='Withdraw',exact=True).click();page.get_by_role('button',name='Confirm Withdrawal',exact=True).click();page.wait_for_load_state('networkidle')
            assert '/workspace/registrations/' in urlsplit(page.url).path
            assert parse_qs(urlsplit(page.url).query)['return_to']==[origin]
            checks.append(['discovery → detail → consent refresh → join → withdrawal retains origin'])
            page.goto(base+'/volunteer_dash?tour=1');page.wait_for_selector('.first-use-tour[open]');page.keyboard.press('Escape');page.wait_for_selector('.first-use-tour[open]',state='hidden')
            assert page.locator('[data-guide-replay]').evaluate('e=>e===document.activeElement')
            page.goto(base+'/volunteer_dash?view=calendar');assert page.locator('.volunteer-month-agenda').is_visible() and not page.locator('.volunteer-month-grid').is_visible()
            page.set_viewport_size(dict(width=1440,height=1000));assert page.locator('.volunteer-month-grid').is_visible() and not page.locator('.volunteer-month-agenda').is_visible()
            checks.append(['guide Escape focus and mobile calendar equivalent'])
            page.goto(base+f'/workspace/registrations/{registration_id}');page.emulate_media(media='print');page.pdf(path=str(out/'registration-print.pdf'),format='A4');page.emulate_media(media='screen')
            checks.append(['registration print'])
            browser.close()
            assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8')
    print(f'{len(checks)} journey browser checks passed; no page script errors. Artifacts: {out}')


if __name__=='__main__':main()
