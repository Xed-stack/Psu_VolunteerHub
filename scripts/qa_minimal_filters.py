"""Inspect and exercise active filter screens using disposable local fixtures."""
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
from app.models.event import Event
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/minimal-filters/after');out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');cookies={};checks=[];errors=[]
    with app.app_context():
        for role in ['director','coordinator','volunteer']:
            user=User.query.filter_by(role=role).first()
            if not user:
                user=User(name=role.title(),email=role+'@example.org',role=role,campus_id=1,password_hash='unused');db.session.add(user)
            user.sex='prefer_not_to_say';user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        event=Event.query.first();event.title='aUTHORED activity in PSU 100%_';event.date=local_now()-timedelta(hours=1);event.end_date=local_now()+timedelta(hours=2);event_id=event.id
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            scenarios={
                'director':['/workspace/reports/results','/workspace/reports/aop','/workspace/reports/historical','/annual-goals','/admin_dash','/workspace/overview','/workspace/volunteers','/workspace/reports/people','/workspace/recognition'],
                'coordinator':['/workspace/reports/results','/workspace/activities',f'/attendance?event_id={event_id}',f'/workspace/activities/{event_id}/registrations',f'/workspace/activities/{event_id}/external','/workspace/partners'],
                'volunteer':['/opportunities','/workspace/registrations','/profile','/volunteer_dash'],
                'public':['/','/auth/login','/auth/interests','/workspace/about','/help']}
            if '--diagnose' in sys.argv:scenarios={'director':['/annual-goals']}
            if '--text-only' in sys.argv:scenarios={}
            for role,paths in scenarios.items():
                c=browser.new_context(has_touch=True,reduced_motion='reduce');page=c.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                if role!='public':c.add_cookies([dict(name='session',value=cookies[role],url=base)])
                for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    for path in paths:
                        response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(role,path,response.status)
                        if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                            page.screenshot(path=str(out/'overflow.png'),full_page=True)
                            raise AssertionError((role,path,width,'overflow',page.evaluate("[...document.querySelectorAll('body *')].filter(el=>{if(el.getBoundingClientRect().right<=innerWidth+1)return false;for(let p=el.parentElement;p;p=p.parentElement){if(['auto','scroll','hidden'].includes(getComputedStyle(p).overflowX))return false;}return true;}).slice(0,10).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,text:el.textContent.slice(0,55)}))")))
                        for more in page.locator('[data-more-filters]').all():
                            assert not more.evaluate('el=>el.open')
                            assert more.locator('details').count()==0
                        checks.append([role,path,width,height])
                        if width in (1440,390) and path in ['/workspace/reports/results','/workspace/reports/aop','/workspace/reports/historical','/opportunities','/workspace/registrations','/admin_dash','/annual-goals','/auth/login']:
                            page.screenshot(path=str(out/f'{role}-{width}-{path.strip("/").replace("/","-")}.png'),full_page=True)
                c.close()
            if '--diagnose' in sys.argv:
                browser.close();print('Diagnostic layouts passed.');return
            c=browser.new_context(viewport=dict(width=390,height=844),has_touch=True);c.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=c.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            if '--text-only' not in sys.argv:
                page.goto(base+'/workspace/reports/results');form=page.locator('[data-period-controls]');more=form.locator('[data-more-filters]')
                assert form.locator('[name=year]').is_visible() and not form.locator('[name=department]').is_visible()
                assert not form.locator('[name=segment]').is_visible() and not form.locator('[name=start_date]').is_visible()
                for mode,maximum,label in [('quarterly',4,'Quarter'),('semiannual',2,'Half-Year')]:
                    form.locator('[name=period]').select_option(mode)
                    assert form.locator('[data-segment-label]').inner_text()==label
                    form.locator('[name=segment]').select_option(str(maximum));form.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
                    assert parse_qs(urlsplit(page.url).query)['segment']==[str(maximum)]
                    assert not more.evaluate('el=>el.open')
                form.locator('[name=period]').select_option('custom');assert form.locator('[name=start_date]').is_visible()
                year=local_now().year
                form.locator('[name=start_date]').fill(f'{year}-01-01');form.locator('[name=end_date]').fill(f'{year}-12-31')
                form.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
                assert parse_qs(urlsplit(page.url).query)['start_date']==[f'{year}-01-01']
                form.locator('[name=period]').select_option('all');form.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
                assert not form.locator('[name=start_date]').is_visible() and not form.locator('[name=segment]').is_visible()
                checks.append(['reports','quarter, half, custom, all conditional controls'])
                page.goto(base+'/workspace/reports/results?period=this_month');assert form.locator('[name=period]').input_value()=='custom';assert len(form.locator('[name=start_date]').input_value())==10
                checks.append(['reports','legacy normalized month dates'])
                page.goto(base+'/workspace/reports/results?period=all&department=MiXeD+office&affiliation=MiXeD+affiliation&sex=female&campus=1&campus=2')
                assert '4 Active' in more.locator('summary').inner_text()
                form.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
                query=parse_qs(urlsplit(page.url).query)
                assert query['campus']==['1','2'] and query['department']==['MiXeD office'] and query['affiliation']==['MiXeD affiliation']
                assert not more.evaluate('el=>el.open')
                page.get_by_role('link',name='Remove Affiliation: MiXeD affiliation',exact=True).click();page.wait_for_load_state('networkidle')
                query=parse_qs(urlsplit(page.url).query);assert 'affiliation' not in query and query['sex']==['female'] and query['campus']==['1','2']
                export=page.get_by_role('link',name='Export CSV',exact=True).get_attribute('href');assert parse_qs(urlsplit(export).query)['campus']==['1','2']
                assert c.request.get(base+export).status==200
                more.locator('summary').focus();page.keyboard.press('Enter');assert more.evaluate('el=>el.open');page.keyboard.press('Enter');assert not more.evaluate('el=>el.open')
                page.screenshot(path=str(out/'director-390-active-more.png'),full_page=True)
                checks.append(['reports','closed selections, active count, keyboard, remove-one and CSV scope'])
                page.get_by_role('link',name='Reset Filters',exact=True).click();page.wait_for_load_state('networkidle');assert not parse_qs(urlsplit(page.url).query)
                page.locator('[name=department]').evaluate('el=>el.required=true')
                form.get_by_role('button',name='Apply Filters',exact=True).click();assert more.evaluate('el=>el.open')
                assert page.locator('[name=department]').get_attribute('aria-invalid')=='true'
                checks.append(['reports','reset and invalid field reveals More Filters'])
            for path in ['/workspace/reports/results','/workspace/reports/aop','/annual-goals','/workspace/registrations']:
                page.goto(base+path) if 'registrations' not in path else None
                if 'registrations' in path:continue
                page.set_viewport_size(dict(width=320,height=800));page.evaluate("document.documentElement.style.fontSize='200%'");page.wait_for_timeout(200)
                if path == '/workspace/reports/results':
                    page.locator('[data-more-filters] > summary').click()
                if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                    page.screenshot(path=str(out/'text200-overflow.png'),full_page=True)
                    raise AssertionError((path,'200% overflow',page.evaluate("[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1 && !el.closest('.table-scroll,.table-wrap')).slice(0,8).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,text:el.textContent.slice(0,50)}))")))
                page.screenshot(path=str(out/(path.rsplit('/',1)[-1]+'-320-text200.png')),full_page=True)
                checks.append([path,'200% text'])
            page.set_viewport_size(dict(width=1440,height=1000));page.goto(base+'/workspace/reports/results');page.emulate_media(media='print');page.pdf(path=str(out/'report-print.pdf'),format='A4');page.emulate_media(media='screen')
            page.goto(base+'/workspace/reports/results?period=all&view=activities&activity_name=100%25_');assert 'aUTHORED activity in PSU 100%_' in page.locator('main').inner_text()
            checks.append(['reports','authored title preserved and print'])
            c.close()
            nojs=browser.new_context(java_script_enabled=False,viewport=dict(width=390,height=844))
            nojs.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=nojs.new_page();page.goto(base+'/workspace/reports/results')
            nojs_form=page.locator('[data-period-controls]');nojs_form.locator('[name=period]').select_option('quarterly');nojs_form.locator('[name=segment]').select_option('3')
            nojs_form.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
            assert parse_qs(urlsplit(page.url).query)['segment']==['3']
            assert page.locator('[data-segment-label]').inner_text()=='Quarter'
            checks.append(['reports','native no-JavaScript quarter submission'])
            nojs.close();browser.close()
        assert not errors,errors
        print(f'{len(checks)} filter/browser checks passed.')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));server.shutdown()


if __name__=='__main__':main()
