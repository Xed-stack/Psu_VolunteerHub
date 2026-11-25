"""Director activity cards and conditional entry with disposable browser data."""
import json
import logging
import sys
from datetime import datetime,timedelta
from pathlib import Path
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event,Registration,Campus,SdgGoal
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app('testing')
    app.config.update(FINDING_REVIEWS_ENABLED=True,ATTENDANCE_DEFAULTS_EFFECTIVE_FROM=None)
    out=Path('.qa-director-activities-temp/browser');out.mkdir(parents=True,exist_ok=True)
    with app.app_context():
        now=local_now()
        director=User.query.filter_by(role='director').first()
        director.first_use_guide_dismissed_at=datetime.utcnow()
        volunteer=User.query.filter_by(role='volunteer').first()
        campus=db.session.get(Campus,1)
        campus.name='Lingayen Campus with a Long Institutional Campus Name'
        events={}
        specs=[('Ready',2,3,'approved',1),('Schedule Issue',1,None,'approved',1),
               ('Ongoing',-1/24,1/24,'approved',1),('Ended',-3,-2,'approved',1),
               ('Other Campus',4,5,'approved',2),('Cancelled',3,4,'cancelled',1)]
        specs += [(f'Extra {i}',6+i,7+i,'approved',1) for i in range(6)]
        for name,start,end,status,campus_id in specs:
            event=Event(title='Director Browser '+name,description='Synthetic browser fixture',
                date=now+timedelta(days=start),end_date=now+timedelta(days=end) if end is not None else None,
                campus_id=campus_id,lifecycle_status=status,target_participants=10,category='Environment',
                conducting_department='Extension',location='Campus Community Center')
            db.session.add(event);db.session.flush();events[name]=event
        events['Ready'].sdgs=SdgGoal.query.order_by(SdgGoal.number).limit(2).all()
        for name in ('Ready','Ongoing','Ended'):
            db.session.add(Registration(event_id=events[name].id,user_id=volunteer.id,status='confirmed'))
        db.session.commit()
        ready_id,flag_id=events['Ready'].id,events['Schedule Issue'].id
        cookie=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(director.id),_fresh=True,auth_version=director.auth_version))
        for template in app.jinja_env.list_templates():app.jinja_env.get_template(template)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    path='/workspace/activities?q=Director+Browser'
    checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(base_url=base)
            context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in (1440,1280,1024):
                page.set_viewport_size(dict(width=width,height=1000))
                assert page.goto(path).status==200
                page.wait_for_load_state('networkidle')
                desk=page.locator('.director-activities-desktop')
                expect(desk).to_be_visible()
                expect(page.locator('.director-activities-original')).to_be_hidden()
                assert desk.locator('.activities-card').count()==5
                expect(desk).not_to_contain_text('Create Activity')
                expect(desk.locator('.activities-tabs')).not_to_contain_text('Cancelled')
                expect(desk).to_contain_text('SDG 1')
                expect(desk).to_contain_text('Needs Attention')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                desk.screenshot(path=str(out/f'director-{width}.png'))
            checks.append('1440/1280/1024px: Coordinator-based cards, long campus names, five rows, SDGs and no overflow')
            desk.get_by_label('Campus',exact=True).select_option('2')
            desk.get_by_role('button',name='Apply Filters').click()
            expect(desk).to_contain_text('Director Browser Other Campus')
            assert desk.locator('.activities-card').count()==1
            desk.get_by_role('link',name='All Activities',exact=False).click()
            assert 'campus_id=2' in page.url
            checks.append('Campus/search filters, counts and schedule tabs preserve scope')
            for enabled in (True,False):
                app.config['FINDING_REVIEWS_ENABLED']=enabled
                page.goto(path+'+Schedule+Issue')
                desk.get_by_role('link',name='Review Findings',exact=False).click()
                page.wait_for_url(lambda url:'/workspace/follow-up?' in url)
                assert f'event_id={flag_id}' in page.url and 'period=all' in page.url
                expect(page.get_by_role('heading',name='Needs Attention',exact=True)).to_be_visible()
                if enabled:
                    page.locator('.needs-back').click()
                    page.wait_for_url(lambda url:'/workspace/activities?' in url)
                page.goto(path+'+Ready')
                desk.get_by_role('link',name='View Activity',exact=False).focus()
                page.keyboard.press('Enter')
                page.wait_for_url(lambda url:f'/workspace/activities/{ready_id}?' in url)
                expect(page.get_by_role('heading',name='Director Browser Ready',exact=True)).to_be_visible()
            checks.append('Active finding opens event-scoped Needs Attention; clean activity opens details with keyboard; both workflow modes')
            page.goto(path)
            page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            desk.screenshot(path=str(out/'director-enlarged.png'))
            page.evaluate('document.documentElement.style.fontSize=""')
            page.set_viewport_size(dict(width=390,height=844))
            expect(desk).to_be_hidden()
            expect(page.locator('.director-activities-original')).to_be_visible()
            checks.append('200% root text sizing; existing narrow presentation retained')
            context.close()
            context=browser.new_context(base_url=base,java_script_enabled=False,viewport=dict(width=1440,height=1000))
            context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.goto(path+'+Schedule+Issue')
            page.locator('.director-activities-desktop').get_by_role('link',name='Review Findings',exact=False).click()
            assert '/workspace/follow-up?' in page.url
            checks.append('JavaScript-disabled entry routing works')
            browser.close()
        assert not errors,errors
        result=dict(checks=checks,errors=errors)
        (out/'results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:server.shutdown()


if __name__=='__main__':main()
