"""Bounded staff Overview visual/interaction checks on disposable data only."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from tests.test_annual_goals import target


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/staff-overview/after');out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing')
    cookies={}
    with app.app_context():
        for role in ['director','coordinator','volunteer']:
            user=User.query.filter_by(role=role).first()
            if not user:
                user=User(name=role.title(),email=role+'@example.org',role=role,campus_id=1,password_hash='unused')
                db.session.add(user)
            user.sex='prefer_not_to_say';user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        now=local_now()
        for row in Event.query.all():
            row.date=now-timedelta(days=10);row.end_date=now-timedelta(days=9)
        for i in range(6):
            start=now-timedelta(hours=1) if i==0 else now+timedelta(days=i)
            db.session.add(Event(title=['Coastal community partnership and outreach','Campus volunteer orientation','Community learning workshop','Health and wellbeing outreach','Environmental action day','Service preparation workshop'][i],
                description='Disposable browser QA fixture',campus_id=1,date=start,end_date=start+timedelta(hours=3),slots=20,location='PSU campus',lifecycle_status='approved'))
        db.session.commit()
        target(campus=1,actual=4,shared='shared');target(campus=1,actual=4,shared='shared',kind='ASP')
        target(campus=2,actual=0);target(campus=2);target(actual=4)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for role in ['director','coordinator']:
                context=browser.new_context(has_touch=True,reduced_motion='reduce')
                context.add_cookies([dict(name='session',value=cookies[role],url=base)])
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                for width,height in [(1440,900),(1024,900),(768,1000),(390,844),(320,740),(844,390)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    response=page.goto(base+'/workspace/overview');page.wait_for_load_state('networkidle')
                    assert response.status==200
                    assert page.locator('.metric-tile').count()==(4 if role=='director' else 5)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,width,'overflow')
                    assert page.locator('.workspace-hero').count()==0
                    if role=='director':
                        assert page.locator('.staff-campus-table tbody tr').count()==9
                        assert page.locator('.metric-title').all_text_contents()==['Conducted Activities','Verified Attendees','Campus Annual Achievement','Findings to Review']
                        primary=page.locator('.director-primary-grid')
                        assert primary.locator('.staff-attention').count()==1 and primary.locator('[data-campus-chart]').count()==1
                        assert primary.locator('[data-month-chart],[data-sex-chart],.staff-annual').count()==0
                        assert page.locator('.director-secondary-summary').inner_text().find('Volunteer Accounts')>=0
                        if width==1440:
                            assert len(set(page.locator('.metric-tile').evaluate_all('els=>els.map(el=>Math.round(el.getBoundingClientRect().y))')))==1
                            assert page.locator('.metric-tile').first.bounding_box()['width']>page.locator('.kpi-strip').bounding_box()['width']/4-2
                        assert page.locator('.metric-tile').first.bounding_box()['width']>=page.locator('.metric-tile').last.bounding_box()['width']-2
                        assert primary.evaluate("el=>el.getBoundingClientRect().top<document.querySelector('.director-details').getBoundingClientRect().top")
                        assert page.locator('.staff-annual-result').inner_text().startswith('1 / 3')
                        assert page.locator('.staff-university-targets').is_visible()
                        assert page.locator('[data-month-chart]').count()==1
                    else:
                        assert page.locator('.staff-agenda li').count()==5
                        assert page.get_by_role('link',name='Record Attendance',exact=True).count()==1
                    if width in (1440,390):page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
                    checks.append([role,width,height,'layout and visible data'])
                page.set_viewport_size(dict(width=1440,height=900))
                page.evaluate("document.documentElement.style.fontSize='125%'")
                page.wait_for_timeout(250)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out/f'{role}-text125.png'))
                checks.append([role,'125% text'])
                page.set_viewport_size(dict(width=320,height=800))
                page.evaluate("document.documentElement.style.fontSize='200%'")
                page.wait_for_timeout(250)
                page.screenshot(path=str(out/f'{role}-320-text200.png'),full_page=True)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,'200% overflow',page.evaluate("[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(el=>({tag:el.tagName,cls:el.className,width:el.getBoundingClientRect().width,text:el.textContent.slice(0,60)}))"))
                page.screenshot(path=str(out/f'{role}-320-text200.png'),full_page=True)
                checks.append([role,'200% text'])
                page.reload();page.set_viewport_size(dict(width=390,height=844))
                form=page.locator('[data-overview-scope]')
                form.locator('[name=period]').select_option('quarterly')
                assert form.locator('[data-period-segment]').is_visible()
                form.locator('[name=segment]').select_option('2')
                form.get_by_role('button',name='Apply',exact=True).click();page.wait_for_load_state('networkidle')
                assert parse_qs(urlsplit(page.url).query)['segment']==['2']
                form.locator('[name=period]').select_option('custom')
                assert form.locator('[name=start_date]').is_visible()
                form.locator('[name=start_date]').fill(f'{now.year}-01-01')
                form.locator('[name=end_date]').fill(f'{now.year}-12-31')
                form.get_by_role('button',name='Apply',exact=True).click();page.wait_for_load_state('networkidle')
                assert parse_qs(urlsplit(page.url).query)['period']==['custom']
                checks.append([role,'quarter/custom scope submission'])
                tip=page.locator('.metric-tile .info-tip summary').last
                tip.focus();tip.press('Enter')
                content=page.locator('.metric-tile .info-tip[open] .info-tip__content');assert content.is_visible()
                rect=content.bounding_box();assert rect['x']>=0 and rect['x']+rect['width']<=391
                tip.press('Escape');assert tip.evaluate('el=>el===document.activeElement')
                checks.append([role,'information tip keyboard, viewport and focus'])
                page.goto(base+'/workspace/overview?tour=1');guide=page.locator('dialog.first-use-tour');guide.wait_for(state='visible')
                while page.locator('[data-tour-next]').inner_text()!='Finish':page.locator('[data-tour-next]').click()
                page.locator('[data-tour-next]').click();guide.wait_for(state='hidden')
                assert page.locator('[data-guide-replay]').evaluate('el=>el===document.activeElement')
                checks.append([role,'complete retargeted guide and focus return'])
                if role=='director':
                    page.goto(base+'/workspace/overview?period=all');page.wait_for_load_state('networkidle')
                    page.locator('.metric-tile > a[href="#annual-title"]').click()
                    assert 0<page.locator('#annual-title').bounding_box()['y']<400
                    checks.append([role,'annual headline reaches visible detailed scope'])
                    page.goto(base+'/workspace/overview?period=all&campus_id=2');page.wait_for_load_state('networkidle')
                    review=page.get_by_role('link',name='Review These Findings',exact=True).first
                    review.focus();assert review.evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
                    review.press('Enter');page.wait_for_load_state('networkidle')
                    args=parse_qs(urlsplit(page.url).query)
                    assert args['campus_id']==['2'] and 'finding_type' in args
                    assert page.locator('.finding-type-scope').is_visible()
                    page.get_by_role('link',name='View All Findings',exact=True).click();page.wait_for_load_state('networkidle')
                    args=parse_qs(urlsplit(page.url).query);assert args['campus_id']==['2'] and 'finding_type' not in args
                    checks.append([role,'grouped queue, focus, scope and clear type'])
                    page.goto(base+'/workspace/overview?period=all&activity_name=NoMatchingActivity');page.wait_for_load_state('networkidle')
                    assert page.locator('.director-finding-total strong').inner_text()=='0'
                    assert 'No follow-up findings' in page.locator('.staff-attention').inner_text()
                    checks.append([role,'zero findings empty state'])
                    page.goto(base+'/workspace/overview?period=all&campus=1&campus=2&category=Environment')
                    form=page.locator('[data-overview-scope]');form.get_by_role('button',name='Apply',exact=True).click();page.wait_for_load_state('networkidle')
                    assert parse_qs(urlsplit(page.url).query)['campus']==['1','2']
                    assert parse_qs(urlsplit(page.url).query)['category']==['Environment']
                    original=page.url
                    page.get_by_text('Expand Campus Details',exact=True).click()
                    page.locator('.staff-campus-table a[href*="/workspace/campuses/"]').first.click();page.wait_for_load_state('networkidle')
                    page.get_by_role('link',name='Back to Overview',exact=True).click();page.wait_for_load_state('networkidle')
                    assert page.url==original
                    checks.append([role,'repeated filters, campus detail and return'])
                page.set_viewport_size(dict(width=1440,height=1000));page.goto(base+'/workspace/overview?year=1900');page.wait_for_load_state('networkidle')
                assert 'Not set' in page.locator('.staff-annual-result').inner_text()
                page.screenshot(path=str(out/f'{role}-empty-annual.png'),full_page=True)
                page.emulate_media(media='print');page.pdf(path=str(out/f'{role}-print.pdf'),format='A4');page.emulate_media(media='screen')
                checks.append([role,'missing annual evidence and print'])
                if role=='coordinator':
                    with app.app_context():
                        Event.query.update({'date':now-timedelta(days=10),'end_date':now-timedelta(days=9)})
                        db.session.commit()
                    page.goto(base+'/workspace/overview');page.wait_for_load_state('networkidle')
                    assert 'No upcoming approved activities' in page.locator('.staff-agenda').inner_text()
                    page.screenshot(path=str(out/'coordinator-empty-agenda.png'),full_page=True)
                    checks.append([role,'empty agenda with recovery action'])
                context.close()
            c=browser.new_context(viewport=dict(width=390,height=844));c.add_cookies([dict(name='session',value=cookies['volunteer'],url=base)])
            page=c.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for path in ['/volunteer_dash','/profile','/workspace/registrations']:
                response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200
                assert page.locator('.staff-overview').count()==0
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                checks.append(['volunteer',path,'unaffected shared layout'])
            page.screenshot(path=str(out/'volunteer-390.png'),full_page=True);c.close();browser.close()
        assert not errors,errors
        print(f'{len(checks)} staff browser checks passed.')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
        server.shutdown()


if __name__=='__main__':main()
