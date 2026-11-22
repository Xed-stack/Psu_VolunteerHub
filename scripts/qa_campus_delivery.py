"""Read/render checks on a disposable, synthetic in-memory app only."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs,urlsplit
from pypdf import PdfReader

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Attendance, Event, ExternalParticipant, Registration
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/campus-delivery');out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config['WTF_CSRF_ENABLED']=True
    cookies={};checks=[];errors=[]
    with app.app_context():
        now=local_now()
        for role in ['director','coordinator']:
            user=User.query.filter_by(role=role).first()
            if user is None:
                user=User(name=role.title(),email=role+'@synthetic.invalid',role=role,campus_id=1,password_hash='unused')
                db.session.add(user)
            user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        events=[]
        for index in range(12):
            start=now.replace(month=index+1,day=1,hour=9,minute=0,second=0,microsecond=0)-timedelta(days=365)
            event=Event(title=f'Synthetic outreach {index+1}',description='Synthetic browser fixture only',
                date=start,end_date=start+timedelta(hours=2),campus_id=1 if index%2==0 else 2,
                lifecycle_status='approved',slots=30,category='Environment')
            db.session.add(event);db.session.flush();events.append(event)
            for i,sex in enumerate(['female','male','prefer_not_to_say',None]):
                user=User(name=f'Synthetic participant {index}-{i}',email=f'person-{index}-{i}@synthetic.invalid',
                    role='volunteer',campus_id=event.campus_id,sex=sex,password_hash='unused')
                outsider=ExternalParticipant(id_number=f'synthetic-{index}-{i}',name=f'Community participant {index}-{i}',sex=sex)
                db.session.add_all([user,outsider]);db.session.flush()
                for person in [user,outsider]:
                    reg=Registration(event_id=event.id,status='confirmed',**({'user_id':person.id} if person is user else {'external_participant_id':person.id}))
                    db.session.add(reg);db.session.flush()
                    db.session.add(Attendance(event_id=event.id,registration_id=reg.id,status='present'))
        db.session.commit();event_id=events[0].id
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    path='/workspace/reports/results?period=all&activity_name=Synthetic+outreach&campus=1&campus=2'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in [1440,1024,768,390,320]:
                page.set_viewport_size(dict(width=width,height=950))
                assert page.goto(base+path).status==200;page.wait_for_load_state('networkidle')
                chart=page.locator('[data-month-chart]');expect(chart).to_be_visible()
                assert chart.evaluate('el=>el.data.length')==2
                assert chart.evaluate('el=>el.data.map(t=>t.name)')==['Lingayen','Urdaneta']
                assert chart.evaluate('el=>el.data.every((t,i)=>JSON.stringify(t.y)===JSON.stringify(JSON.parse(el.dataset.chartSeries)[i].values))')
                assert chart.evaluate('el=>el.data[0].marker.symbol!==el.data[1].marker.symbol')
                dropdown=page.locator('[data-comparison-dropdown]');trigger=dropdown.locator('summary');panel=dropdown.locator('form')
                assert not dropdown.evaluate('el=>el.open')
                trigger.scroll_into_view_if_needed()
                before=chart.evaluate('el=>el.getBoundingClientRect().top+scrollY')
                trigger.click();expect(panel).to_be_visible();page.wait_for_function("document.querySelector('.comparison-filters').style.top.endsWith('px')")
                assert abs(chart.evaluate('el=>el.getBoundingClientRect().top+scrollY')-before)<2
                box=panel.bounding_box()
                assert box['x']>=0 and box['x']+box['width']<=width+1
                assert box['y']>=0 and box['y']+box['height']<=951,(width,box,panel.get_attribute('style'))
                assert panel.evaluate('el=>el.contains(document.elementFromPoint(el.getBoundingClientRect().x+20,el.getBoundingClientRect().y+20))')
                choices=panel.locator('.comparison-campus-list')
                assert choices.evaluate('el=>el.scrollHeight>el.clientHeight')
                assert choices.locator('label').first.bounding_box()['height']>=44
                choices.locator('input').last.focus();assert choices.evaluate('el=>el.scrollTop>0')
                choices.locator('input').last.press('Escape');expect(panel).to_be_hidden();expect(trigger).to_be_focused()
                assert trigger.evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
                trigger.press('Enter');expect(panel).to_be_visible()
                page.locator('#campus-comparison-title').click();expect(panel).to_be_hidden()
                page.locator('.staff-trend summary').click()
                assert page.locator('.delivery-values tbody tr').count()>=12
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                trigger.scroll_into_view_if_needed();trigger.click()
                page.screenshot(path=str(out/f'comparison-open-{width}.png'))
                trigger.press('Escape')
                chart.scroll_into_view_if_needed();page.screenshot(path=str(out/f'delivery-{width}.png'))
                checks.append(['layout, two traces, dropdown overlay, focus and text table',width])
            # Top filters always clear comparison and preserve unrelated filters.
            for campus in ['1','']:
                page.goto(base+path);page.wait_for_load_state('networkidle')
                top=page.locator('form.filter-form');top.locator('[name=campus_id]').select_option(campus)
                top.get_by_role('button',name='Apply Filters',exact=True).click();page.wait_for_load_state('networkidle')
                args=parse_qs(urlsplit(page.url).query)
                assert 'campus' not in args and 'campus_mode' not in args
                assert args.get('campus_id',[''])[0]==campus and args['activity_name']==['Synthetic outreach']
                assert page.locator('[data-month-chart]').evaluate('el=>el.data.length')==1
                checks.append(['top filter precedence',campus or 'all'])
            page.goto(base+'/workspace/reports/results?period=all&campus_id=1&activity_name=Synthetic+outreach');page.wait_for_load_state('networkidle')
            page.locator('[data-comparison-dropdown] > summary').click()
            form=page.locator('.comparison-filters')
            for campus in ['1','2']:form.locator(f'[name=campus][value="{campus}"]').check()
            form.get_by_role('button',name='Apply Comparison').click();page.wait_for_load_state('networkidle')
            args=parse_qs(urlsplit(page.url).query)
            assert 'campus_id' not in args and args['campus']==['1','2'] and args['page']==['1']
            assert page.url.endswith('#campus-comparison')
            assert 0<page.locator('#campus-comparison-title').bounding_box()['y']<400
            expect(page.locator('.comparison-dropdown')).not_to_have_attribute('open','')
            assert page.locator('[data-month-chart]').evaluate('el=>el.data.length')==2
            checks.append(['comparison replaces top campus, closes and returns to chart'])
            page.locator('[data-comparison-dropdown] > summary').click()
            page.locator('[name=campus_mode]').select_option('exclude')
            page.get_by_role('button',name='Apply Comparison').click();page.wait_for_load_state('networkidle')
            assert page.locator('[data-month-chart]').evaluate('el=>el.data.length')==7
            checks.append(['exclude plots remaining campuses including zeros'])
            page.get_by_role('link',name='Participation Records',exact=True).click();page.wait_for_load_state('networkidle')
            assert parse_qs(urlsplit(page.url).query)['campus_mode']==['exclude']
            page.get_by_role('link',name='Adjust Campus Comparison').click();page.wait_for_load_state('networkidle')
            page.locator('[data-comparison-dropdown] > summary').click()
            page.get_by_role('link',name='Reset Comparison').click();page.wait_for_load_state('networkidle')
            assert 'campus' not in parse_qs(urlsplit(page.url).query)
            checks.append(['tabs and comparison reset'])
            page.goto(base+path+'&category=NoMatch');page.wait_for_load_state('networkidle')
            assert page.locator('[data-month-chart]').evaluate('el=>el.data.every(t=>t.y.every(v=>v===0))')
            expect(page.locator('.staff-trend')).to_contain_text('No conducted activities match this scope')
            checks.append(['zero-line empty state'])
            page.goto(base+path);page.wait_for_load_state('networkidle')
            page.evaluate("document.documentElement.style.fontSize='200%'")
            page.locator('[data-comparison-dropdown] > summary').click()
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            box=page.locator('.comparison-filters').bounding_box();assert box['y']>=0 and box['y']+box['height']<=950
            assert page.locator('.comparison-filters').evaluate('el=>el.scrollWidth<=el.clientWidth+1')
            page.screenshot(path=str(out/'comparison-text200.png'))
            page.keyboard.press('Escape')
            page.evaluate("document.documentElement.style.fontSize=''")
            page.evaluate("window.dispatchEvent(new Event('beforeprint'))")
            expect(page.locator('.delivery-values')).to_be_visible()
            page.emulate_media(media='print');page.screenshot(path=str(out/'print.png'),full_page=True)
            page.emulate_media(media='screen');page.evaluate("window.dispatchEvent(new Event('afterprint'))")
            checks.append(['200 percent text and print values'])
            def long_labels(route):
                response=route.fetch()
                route.fulfill(response=response,body=response.text().replace('Urdaneta','Urdaneta Community Extension and Volunteer Services Campus'))
            context.route('**/workspace/reports/results?**',long_labels)
            page.goto(base+path);page.wait_for_load_state('networkidle')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.set_viewport_size(dict(width=1440,height=950))
            page.set_viewport_size(dict(width=320,height=950))
            page.wait_for_function("document.querySelector('[data-month-chart]')._fullLayout.width<=document.querySelector('[data-month-chart]').getBoundingClientRect().width+1")
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.locator('[data-month-chart]').scroll_into_view_if_needed()
            page.screenshot(path=str(out/'long-label-resize.png'))
            checks.append(['long campus labels and live resize'])
            for javascript in [False,True]:
                fallback=browser.new_context(java_script_enabled=javascript,viewport=dict(width=390,height=950))
                fallback.add_cookies([dict(name='session',value=cookies['director'],url=base)])
                if javascript:fallback.route('**/plotly-*.js',lambda route:route.abort())
                basic=fallback.new_page();basic.goto(base+path);basic.wait_for_load_state('networkidle')
                basic.locator('[data-comparison-dropdown] > summary').click()
                basic.locator('[name=campus][value="2"]').uncheck()
                basic.get_by_role('button',name='Apply Comparison').click();basic.wait_for_load_state('networkidle')
                assert parse_qs(urlsplit(basic.url).query)['campus']==['1']
                basic.locator('.staff-trend summary').click();expect(basic.locator('.delivery-values')).to_be_visible()
                checks.append(['no JavaScript / Plotly failure fallback',javascript]);fallback.close()
            coordinator=browser.new_context();coordinator.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            other=coordinator.new_page();other.goto(base+path);other.wait_for_load_state('networkidle')
            assert other.locator('[data-comparison-dropdown]').count()==0
            assert other.locator('[data-month-chart]').evaluate('el=>el.data.length')==1
            checks.append(['coordinator scope and aggregate unchanged'])
            assert not errors,errors
            browser.close()
        print(f'{len(checks)} campus-delivery browser groups passed; evidence: {out}')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
        server.shutdown()


if __name__=='__main__':main()
