"""Advance external registration and locked attendance in a disposable app."""
import json
import logging
import sys
from datetime import datetime,timedelta
from pathlib import Path
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event,Registration,Attendance
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app('testing');app.config['WTF_CSRF_ENABLED']=True
    out=Path('.qa-external-advance-temp');out.mkdir(exist_ok=True)
    with app.app_context():
        now=local_now();user=User.query.filter_by(role='coordinator').first()
        user.first_use_guide_dismissed_at=datetime.utcnow()
        event=Event(title='Synthetic Advance External Registration',description='Synthetic browser fixture',
            campus_id=user.campus_id,lifecycle_status='approved',date=now+timedelta(hours=2),end_date=None)
        db.session.add(event);db.session.commit();event_id=event.id
        cookie=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    roster=f'/workspace/activities/{event_id}/external'
    errors=[];checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(base_url=base)
            context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in (1440,1280,1024):
                page.set_viewport_size(dict(width=width,height=1000))
                assert page.goto(f'/attendance?event_id={event_id}').status==200
                expect(page.get_by_role('link',name='Edit Activity Schedule',exact=True)).to_be_visible()
                page.get_by_role('link',name='Add External Participants',exact=True).click()
                expect(page.locator('[name=mark_present]')).to_have_count(0)
                expect(page.get_by_role('button',name='Save Named Roster')).to_be_visible()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.locator('.roster-page').screenshot(path=str(out/f'entry-{width}.png'))
            checks.append('Three desktop widths: direct Attendance entry, missing-end guidance, no early attendance checkbox, no overflow')
            page.get_by_label('Group Name (Optional)',exact=True).fill('Advance Group')
            page.get_by_label('Named Participants',exact=True).fill('Early Person,early@example.invalid\nSecond Person')
            page.get_by_role('button',name='Save Named Roster',exact=True).focus()
            page.keyboard.press('Enter')
            page.wait_for_function('location.pathname.endsWith("/external")')
            expect(page.locator('.roster-table')).to_contain_text('Early Person')
            expect(page.locator('.roster-table')).to_contain_text('Unrecorded')
            assert page.locator('select[name=status]').count()==0
            with app.app_context():
                assert Registration.query.filter_by(event_id=event_id).count()==2
                assert Attendance.query.filter_by(event_id=event_id).count()==0
                event=db.session.get(Event,event_id);event.date=local_now()-timedelta(hours=1);event.end_date=local_now()+timedelta(hours=1);db.session.commit()
            checks.append('Keyboard save with CSRF: advance roster creates registrations and zero attendance rows')
            page.goto(roster)
            page.locator('select[name=status]').first.select_option('present')
            page.get_by_role('button',name='Save External Attendance',exact=True).click()
            expect(page.locator('select[name=status]').first).to_have_value('present')
            with app.app_context():
                assert Attendance.query.filter_by(event_id=event_id,status='present').count()==1
                event=db.session.get(Event,event_id);event.end_date=local_now()-timedelta(minutes=1);db.session.commit()
            page.goto(roster)
            expect(page.get_by_role('link',name='Add External Participants',exact=True)).to_have_count(0)
            expect(page.get_by_role('button',name='Save External Attendance',exact=True)).to_have_count(0)
            expect(page.locator('.roster-table')).to_contain_text('Attended')
            checks.append('Ongoing attendance saved; ended roster and attendance remain locked with existing evidence visible')
            with app.app_context():
                event=db.session.get(Event,event_id);event.date=local_now()+timedelta(hours=2);event.end_date=local_now()+timedelta(hours=3);db.session.commit()
            page.goto(roster+'/new')
            page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            context.close()
            context=browser.new_context(base_url=base,java_script_enabled=False,viewport=dict(width=1440,height=1000))
            context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.goto(roster+'/new')
            page.get_by_label('Named Participants',exact=True).fill('No Script Person')
            page.get_by_role('button',name='Save Named Roster',exact=True).click()
            expect(page.locator('.roster-table')).to_contain_text('No Script Person')
            checks.append('200% text sizing and JavaScript-disabled advance registration')
            browser.close()
        assert not errors,errors
        result=dict(checks=checks,errors=errors)
        (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    finally:server.shutdown()


if __name__=='__main__':main()
