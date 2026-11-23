"""Synthetic in-memory checks for Director reminders and editable bulk attendance."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event, Registration, Attendance, ExternalParticipant
from app.models.user import User
from app.models.notification import Notification
from app.models.finding_review import FindingReview, FindingReviewEvent
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    app=create_app('testing');app.config.update(WTF_CSRF_ENABLED=True,FINDING_REVIEWS_ENABLED=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/attention-attendance-refinements');out.mkdir(parents=True,exist_ok=True)
    checks=[];errors=[];cookies={}
    with app.app_context():
        for role,campus in [('director',1),('coordinator',1),('other',2)]:
            user=User(name='Synthetic '+role,email=role+'@refinement.invalid',role='coordinator' if role=='other' else role,
                      campus_id=campus,password_hash='unused',sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user);db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        now=local_now()
        event=Event(title='Synthetic Ongoing Attendance Outreach',description='Synthetic browser fixture',campus_id=1,
                    date=now-timedelta(hours=1),end_date=now+timedelta(hours=3),lifecycle_status='approved',slots=100)
        ended=Event(title='Synthetic Completed Review',description='Synthetic browser fixture',campus_id=1,
                    date=now-timedelta(days=2),end_date=now-timedelta(days=1),lifecycle_status='approved',slots=100)
        missing=Event(title='Synthetic Missing End',description='Synthetic browser fixture',campus_id=1,
                    date=now-timedelta(days=3),lifecycle_status='approved',slots=100)
        db.session.add_all([event,ended,missing]);db.session.flush();eid=event.id
        for i in range(18):
            user=User(name=f'Synthetic Volunteer {i:02}',email=f'volunteer-{i}@refinement.invalid',role='volunteer',campus_id=1,sex='prefer_not_to_say',password_hash='unused')
            db.session.add(user);db.session.flush()
            reg=Registration(event_id=eid,user_id=user.id,status='confirmed');db.session.add(reg);db.session.flush()
            if i==0:db.session.add(Attendance(registration_id=reg.id,event_id=eid,user_id=user.id,status='excused'))
            if i==0:db.session.add(Registration(event_id=ended.id,user_id=user.id,status='confirmed'))
        for i in range(3):
            person=ExternalParticipant(name=f'Synthetic Community {i}',id_number=f'EXT-REFINE-{i}')
            db.session.add(person);db.session.flush();db.session.add(Registration(event_id=eid,external_participant_id=person.id,status='confirmed'))
        db.session.commit()
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            director=browser.new_context(reduced_motion='reduce');director.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=director.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('dialog',lambda d:d.accept())
            queue='/workspace/follow-up?period=all&review_group=attendance'
            for enabled in [True,False]:
                app.config['FINDING_REVIEWS_ENABLED']=enabled
                for width in [1440,1024,768,390,320]:
                    page.set_viewport_size(dict(width=width,height=900));assert page.goto(base+queue).status==200;page.wait_for_load_state('networkidle')
                    expect(page.locator('select[name=review_group]')).to_be_visible()
                    assert page.locator('select[name=finding_type]').count()==0
                    assert page.get_by_role('link',name='Advanced Filters in Reports').count()==0
                    row=page.locator('li').filter(has=page.get_by_text('Synthetic Ongoing Attendance Outreach',exact=True)).last
                    assert 'Start:' in row.inner_text() and 'End:' in row.inner_text()
                    assert row.get_by_role('button',name='Remind Coordinator',exact=True).count()==1
                    assert row.get_by_role('link',name='Review',exact=True).count()==0
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    page.screenshot(path=str(out/f'queue-{enabled}-{width}.png'),full_page=True)
                    checks.append(['queue',enabled,width])
                button=page.get_by_role('button',name='Remind Coordinator',exact=True)
                button.focus();assert button.evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
                button.click();page.wait_for_load_state('networkidle');assert page.url==base+queue
                expect(page.locator('.flash-stack')).to_contain_text('Reminder sent' if enabled else 'Follow-up sent')
                page.get_by_role('button',name='Remind Coordinator',exact=True).click();page.wait_for_load_state('networkidle')
                assert 'equivalent unread reminder already exists' in page.locator('main').inner_text().lower() or 'equivalent unread reminder already exists' in page.locator('body').inner_text().lower()
                checks.append(['native reminder and deduplication',enabled])
            app.config['FINDING_REVIEWS_ENABLED']=True
            page.goto(base+queue);page.wait_for_load_state('networkidle')
            page.get_by_role('link',name='Reviewed',exact=True).focus();page.keyboard.press('Enter');page.wait_for_load_state('networkidle')
            expect(page.get_by_role('link',name='Reviewed',exact=True)).to_have_attribute('aria-current','page')
            page.get_by_role('link',name='Active',exact=True).focus();page.keyboard.press('Enter');page.wait_for_load_state('networkidle')
            page.locator('select[name=review_group]').select_option('participation')
            page.get_by_role('button',name='Apply Review Filters',exact=True).click();page.wait_for_load_state('networkidle')
            assert 'review_group=participation' in page.url and 'finding_type' not in page.url
            page.goto(base+queue);page.wait_for_load_state('networkidle');checks.append('keyboard review tabs and category submission')
            page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1');page.screenshot(path=str(out/'queue-text200.png'),full_page=True)
            page.evaluate('document.documentElement.style.fontSize=""');checks.append('queue 200% text')
            page.goto(base+'/workspace/reports');page.wait_for_load_state('networkidle')
            card=page.get_by_role('navigation',name='Annual Recognition Reports').get_by_role('link')
            page.screenshot(path=str(out/'reports-recognition-320.png'),full_page=True)
            expect(card).to_contain_text('Outstanding Recognition');card.click();page.wait_for_load_state('networkidle')
            assert '/workspace/recognition' in page.url;checks.append('recognition report card')

            coord=browser.new_context(reduced_motion='reduce');coord.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            roster=coord.new_page();roster.on('pageerror',lambda e:errors.append(str(e)));roster.on('dialog',lambda d:d.accept())
            for route,name in [(f'/attendance?event_id={eid}','internal'),(f'/workspace/activities/{eid}/external','external')]:
                for width in [1440,1024,768,390,320]:
                    roster.set_viewport_size(dict(width=width,height=900));assert roster.goto(base+route).status==200;roster.wait_for_load_state('networkidle')
                    expect(roster.get_by_role('button',name='All Attended',exact=True)).to_be_visible()
                    assert roster.locator('select[name=status] option[value=excused]').count()==0
                    assert not roster.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    roster.screenshot(path=str(out/f'{name}-{width}.png'),full_page=True);checks.append([name,width])
                with app.app_context():before=Attendance.query.count()
                roster.get_by_role('button',name='All Attended',exact=True).focus();roster.keyboard.press('Space')
                selects=roster.locator('[data-attendance-status]');assert all(s.input_value()=='present' for s in selects.all())
                selects.last.select_option('absent')
                with app.app_context():assert Attendance.query.count()==before
                roster.get_by_role('button',name='Save External Attendance' if name=='external' else 'Save Attendance',exact=True).click();roster.wait_for_load_state('networkidle')
                assert roster.locator('[data-attendance-status]').last.input_value()=='absent'
                with app.app_context():
                    if name=='internal':
                        offpage=Registration.query.filter(Registration.event_id==eid,Registration.user_id.isnot(None)).order_by(Registration.id).all()[15:]
                        assert all(r.attendance_record is None for r in offpage)
                roster.evaluate('document.documentElement.style.fontSize="200%"');assert not roster.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                roster.screenshot(path=str(out/f'{name}-text200.png'),full_page=True);roster.evaluate('document.documentElement.style.fontSize=""')
                checks.append([name,'bulk, exception, explicit save, enlarged text'])
            nojs=browser.new_context(java_script_enabled=False,storage_state=coord.storage_state())
            native=nojs.new_page();native.goto(base+f'/attendance?event_id={eid}');expect(native.get_by_role('button',name='All Attended')).to_be_hidden()
            native.locator('[data-attendance-status]').first.select_option('absent');native.get_by_role('button',name='Save Attendance',exact=True).click();native.wait_for_load_state('networkidle')
            assert native.locator('[data-attendance-status]').first.input_value()=='absent';checks.append('no JavaScript individual save')
            with app.app_context():db.session.get(Event,eid).end_date=local_now()-timedelta(minutes=1);db.session.commit()
            roster.goto(base+f'/attendance?event_id={eid}');assert roster.locator('[data-attendance-status]').count()==0
            assert roster.get_by_role('button',name='All Attended').count()==0;checks.append('ended attendance locked')
            page.goto(base+'/workspace/follow-up?period=all&review_group=attendance');assert page.get_by_role('button',name='Remind Coordinator').count()==0
            page.goto(base+'/workspace/follow-up?period=all&review_group=planning');expect(page.locator('.finding-schedule').filter(has_text='End time not recorded').first).to_be_visible()
            page.goto(base+'/workspace/follow-up?period=all&review_tab=reviewed');expect(page.get_by_text('No completed assessments match this scope.',exact=True)).to_be_visible();checks.append('missing-end and reviewed empty states')
            nojs.close();coord.close();director.close();browser.close()
        assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} browser groups passed: {out}')


if __name__=='__main__':main()
