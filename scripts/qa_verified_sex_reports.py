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
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/verified-sex');out.mkdir(parents=True,exist_ok=True)
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
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for role in ['director','coordinator']:
                context=browser.new_context(reduced_motion='reduce',has_touch=True)
                context.add_cookies([dict(name='session',value=cookies[role],url=base)])
                def long_labels(route):
                    if route.request.resource_type!='document':
                        route.continue_();return
                    response=route.fetch()
                    route.fulfill(response=response,body=response.text().replace('Urdaneta','Urdaneta Community Extension and Volunteer Services Campus'))
                context.route('**/workspace/**',long_labels)
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                paths=[('overview','/workspace/overview?period=all'),
                       ('summary','/workspace/reports/results?period=all'),
                       ('participation','/workspace/reports/results?period=all&view=participation')]
                for width in [1440,1024,768,390,320]:
                    page.set_viewport_size(dict(width=width,height=950))
                    for name,path in paths:
                        assert page.goto(base+path).status==200;page.wait_for_load_state('networkidle')
                        chart=page.locator('[data-sex-chart]');chart.wait_for(state='visible')
                        assert chart.evaluate('el=>el.data[0].type')=='pie'
                        assert chart.evaluate('el=>el.data[0].hole')==.62
                        assert chart.evaluate("el=>el.data[0].text.every((text,i)=>text===JSON.parse(el.dataset.chartValues)[i].share.toFixed(1)+'%')")
                        assert chart.evaluate('el=>el.data[0].values.reduce((a,b)=>a+b,0)')==(96 if role=='director' else 48)
                        assert page.locator('.sex-breakdown-table tbody tr').count()==4
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,name,width)
                        assert page.locator('[data-chart-status]:visible').count()==0
                        if name=='summary' and role=='director':
                            controls=page.locator('#campus-comparison .comparison-filters')
                            assert controls.locator('[name=campus]').count()==9
                            box=controls.locator('.comparison-campus-list')
                            assert box.evaluate('el=>el.scrollHeight>el.clientHeight')
                            assert box.evaluate('el=>el.children[3].getBoundingClientRect().bottom<=el.getBoundingClientRect().bottom+1')
                            assert box.locator('label').first.bounding_box()['height']>=44
                            box.locator('input').last.focus()
                            assert box.evaluate('el=>el.scrollTop>0')
                            box.evaluate('el=>el.scrollTop=0')
                        if name=='overview' and role=='director':
                            details=page.locator('.campus-details');assert not details.evaluate('el=>el.open')
                            assert not page.locator('.staff-campus-table').is_visible()
                            summary=details.locator('summary');summary.focus();summary.press('Enter')
                            assert page.locator('.staff-campus-table').is_visible()
                            assert summary.evaluate('el=>getComputedStyle(el).outlineStyle')!='none'
                            assert summary.bounding_box()['height']>=44
                            summary.press('Enter');assert not details.evaluate('el=>el.open')
                        if width in [1440,390,320]:
                            page.wait_for_function("[...document.querySelectorAll('[data-campus-chart],[data-month-chart],[data-sex-chart]')].every(el=>el.hidden || Math.abs(el._fullLayout.width-el.getBoundingClientRect().width)<2)")
                            page.locator('main').click(position=dict(x=2,y=2),force=True)
                            page.evaluate('window.scrollTo(0,0)')
                            page.screenshot(path=str(out/f'{role}-{name}-{width}.png'),full_page=True)
                            if name=='summary':
                                page.locator('[data-sex-chart]').scroll_into_view_if_needed();page.wait_for_timeout(300)
                                page.screenshot(path=str(out/f'{role}-donut-viewport-{width}.png'))
                                page.locator('#campus-comparison').scroll_into_view_if_needed();page.wait_for_timeout(300)
                                page.screenshot(path=str(out/f'{role}-comparison-viewport-{width}.png'))
                        checks.append([role,name,width,'plots, totals, disclosure, overflow'])
                page.goto(base+paths[1][1]);page.wait_for_load_state('networkidle')
                page.set_viewport_size(dict(width=1440,height=950));page.set_viewport_size(dict(width=320,height=950));page.wait_for_timeout(400)
                assert page.locator('[data-sex-chart]').evaluate('el=>el._fullLayout.width')<=page.locator('[data-sex-chart]').bounding_box()['width']+1
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                checks.append([role,'live chart resize'])
                page.evaluate("document.documentElement.style.fontSize='200%'");page.wait_for_timeout(400)
                page.screenshot(path=str(out/f'{role}-text200.png'),full_page=True)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),page.evaluate("[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>({tag:el.tagName,cls:String(el.className),width:el.getBoundingClientRect().width,text:el.textContent.slice(0,50)}))")
                checks.append([role,'200% text'])
                if role=='director':
                    page.goto(base+'/workspace/overview?year=2025&period=quarterly&segment=2&campus_id=1');page.wait_for_load_state('networkidle')
                    page.get_by_role('link',name='Compare Campuses',exact=True).click();page.wait_for_load_state('networkidle')
                    args=parse_qs(urlsplit(page.url).query)
                    assert args['year']==['2025'] and args['period']==['quarterly'] and args['segment']==['2']
                    assert 'campus_id' not in args and page.url.endswith('#campus-comparison')
                    title=page.locator('#campus-comparison-title')
                    assert title.evaluate('el=>el===document.activeElement')
                    assert title.bounding_box()['y']>0 and title.bounding_box()['y']<400
                    form=page.locator('.comparison-filters')
                    form.locator('[name=campus][value="1"]').check()
                    form.locator('[name=campus][value="2"]').check()
                    form.get_by_role('button',name='Apply Comparison').click();page.wait_for_load_state('networkidle')
                    args=parse_qs(urlsplit(page.url).query)
                    assert args['campus']==['1','2'] and args['page']==['1'] and page.url.endswith('#campus-comparison')
                    assert page.locator('#campus-comparison-title').bounding_box()['y']<400
                    form=page.locator('.comparison-filters');form.locator('[name=campus_mode]').select_option('exclude')
                    form.get_by_role('button',name='Apply Comparison').click();page.wait_for_load_state('networkidle')
                    assert parse_qs(urlsplit(page.url).query)['campus_mode']==['exclude']
                    page.get_by_role('link',name='Participation Records',exact=True).click();page.wait_for_load_state('networkidle')
                    assert page.locator('.comparison-filters').count()==0
                    page.get_by_role('link',name='Adjust Campus Comparison').click();page.wait_for_load_state('networkidle')
                    assert page.locator('.comparison-filters [name=campus]:checked').count()==2
                    page.get_by_role('link',name='Reset Comparison').click();page.wait_for_load_state('networkidle')
                    assert 'campus' not in parse_qs(urlsplit(page.url).query)
                    assert page.locator('#campus-comparison-title').bounding_box()['y']<400
                    checks.append([role,'dashboard link, anchored apply/include/exclude/reset, report tabs'])
                for suffix in ['&sex=female','&activity_name=NoMatchingSyntheticActivity']:
                    page.goto(base+'/workspace/reports/results?period=all'+suffix);page.wait_for_load_state('networkidle')
                    if 'sex=' in suffix:
                        assert page.locator('[data-sex-chart]').evaluate('el=>el.data[0].values.filter(n=>n>0).length')==1
                    else:
                        assert page.locator('[data-sex-chart]').count()==0
                        assert 'No verified attendance' in page.locator('.sex-attendance').inner_text()
                    checks.append([role,suffix,'filtered/empty state'])
                page.set_viewport_size(dict(width=1440,height=950))
                page.goto(base+f'/workspace/reports/activities/{event_id}?period=all');page.wait_for_load_state('networkidle')
                assert page.locator('.attendance-total strong').inner_text()=='8'
                checks.append([role,'combined activity report'])
                page.goto(base+'/workspace/overview?period=all');page.wait_for_load_state('networkidle')
                page.pdf(path=str(out/f'{role}-print.pdf'),format='A4')
                if role=='director':
                    assert not page.locator('.campus-details').evaluate('el=>el.open')
                    print_text=' '.join(p.extract_text() for p in PdfReader(out/f'{role}-print.pdf').pages)
                    assert 'Urdaneta' in print_text and 'Sex-Disaggregated' in print_text
                checks.append([role,'print and disclosure restoration'])
                for fmt in ['pdf','xlsx','csv']:
                    response=context.request.get(base+'/workspace/reports/export/'+fmt+'?period=all')
                    assert response.status==200
                    (out/f'{role}-report.{fmt}').write_bytes(response.body())
                    checks.append([role,fmt,'download'])
                context.close()
                for blocked in ['plotly','all-js']:
                    fallback=browser.new_context(java_script_enabled=blocked!='all-js',viewport=dict(width=390,height=844))
                    fallback.add_cookies([dict(name='session',value=cookies[role],url=base)])
                    if blocked=='plotly':fallback.route('**/plotly-5.24.1.min.js',lambda route:route.abort())
                    fallback_page=fallback.new_page();fallback_page.goto(base+paths[1][1]);fallback_page.wait_for_load_state('networkidle')
                    assert fallback_page.locator('.sex-breakdown-table').is_visible()
                    assert fallback_page.locator('[data-chart-status]:visible').count()>=1
                    fallback_page.get_by_text('View Campus Values and Details',exact=True).click()
                    assert fallback_page.locator('[data-tour-id="campus-comparison"] details').evaluate('el=>el.open')
                    if role=='director':
                        form=fallback_page.locator('.comparison-filters');form.locator('[name=campus][value="2"]').check()
                        form.get_by_role('button',name='Apply Comparison').click();fallback_page.wait_for_load_state('networkidle')
                        assert fallback_page.url.endswith('#campus-comparison')
                        assert fallback_page.locator('#campus-comparison').bounding_box()['y']>=0
                        assert fallback_page.locator('#campus-comparison').bounding_box()['y']<400
                        assert parse_qs(urlsplit(fallback_page.url).query)['campus']==['2']
                    fallback.close();checks.append([role,blocked,'text fallback'])
            browser.close()
        assert not errors,errors
        print(f'{len(checks)} verified-attendance browser groups passed.')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
        server.shutdown()


if __name__=='__main__':main()
