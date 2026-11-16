"""Disposable roster fixtures and bounded layout/behavior captures."""
import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event, Registration, Attendance, ExternalParticipant
from app.models.workspace import ExternalGroup
from app.services.activity_workflow import local_now
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/attendance-rosters')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        coord=User(name='QA Coordinator',email='coordinator@roster.test',role='coordinator',campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow());coord.set_password('StrongPassword1!');db.session.add(coord)
        now=local_now();event=Event(title='Community Literacy and Digital Skills Outreach',date=now-timedelta(hours=1),end_date=now+timedelta(hours=3),campus_id=1,slots=100,lifecycle_status='approved',description='QA only')
        db.session.add(event);db.session.flush();eid=event.id
        for i in range(18):
            user=User(name=f'Volunteer {i:02} — Community Service',email=f'person{i}@roster.test',role='volunteer',campus_id=1,sex='prefer_not_to_say');user.set_password('StrongPassword1!');db.session.add(user);db.session.flush()
            reg=Registration(event_id=eid,user_id=user.id,status='confirmed');db.session.add(reg);db.session.flush()
            if i%3:db.session.add(Attendance(event_id=eid,registration_id=reg.id,user_id=user.id,status='present' if i%2 else 'excused'))
        group=ExternalGroup(event_id=eid,name='Community Learning Group');db.session.add(group);db.session.flush()
        for i in range(4):
            person=ExternalParticipant(name=f'Community Participant {i+1}',id_number=f'EXT-QA-{i}',email=f'external{i}@example.org',group_id=group.id);db.session.add(person);db.session.flush()
            reg=Registration(event_id=eid,external_participant_id=person.id,status='confirmed');db.session.add(reg)
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(base+'/auth/login');page.locator('#identifier').fill('coordinator@roster.test');page.locator('#password').fill('StrongPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
            routes=[(f'/attendance?event_id={eid}','internal'),(f'/workspace/activities/{eid}/external','external'),(f'/workspace/activities/{eid}/registrations','registrations')]
            if args.stage=='after':routes.append((f'/workspace/activities/{eid}/external/new','add-external'))
            for route,name in routes:
                for w,h in ([(1440,1000),(390,844)] if args.stage=='before' else [(1440,1000),(1024,768),(768,900),(390,844),(320,800),(844,390)]):
                    page.set_viewport_size(dict(width=w,height=h));page.goto(base+route);page.wait_for_load_state('networkidle')
                    page.screenshot(path=str(out/f'{name}-{w}.png'))
                    if args.stage=='after':assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,w)
                    checks.append([name,w,h])
            if args.stage=='after':exercise(page,context,app,base,eid,out,checks)
            context.close();browser.close()
        assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} browser groups passed: {out}')


def exercise(page,context,app,base,eid,out,checks):
    page.set_viewport_size(dict(width=1440,height=1000))
    internal=f'/attendance?event_id={eid}'
    external=f'/workspace/activities/{eid}/external'
    entry=external+'/new'
    page.goto(base+internal);page.wait_for_load_state('networkidle')
    assert page.locator('.draft-status').count()==0
    control=page.locator('[data-attendance-status]').first
    control.select_option('present')
    expect(page.locator('[data-attendance-change-status]')).to_contain_text('1 unsaved attendance change')
    page.once('dialog',lambda d:d.dismiss())
    page.get_by_role('link',name='External Volunteers',exact=True).click()
    assert '/attendance?' in page.url
    page.get_by_role('button',name='Save Attendance',exact=True).click();page.wait_for_load_state('networkidle')
    expect(page.locator('[data-attendance-change-status]')).to_have_text('No unsaved changes.')
    assert page.locator('[data-attendance-status]').first.input_value()=='present'
    # The saved-record select must not suggest clearing existing evidence.
    assert page.locator('[data-attendance-status]').first.locator('option[value=""]').count()==0
    checks.append('Explicit save, unsaved warning, persisted presence and no misleading clear')
    page.goto(base+internal+'&page=2&volunteer_search=Volunteer')
    page.get_by_role('button',name='Save Attendance',exact=True).click();page.wait_for_load_state('networkidle')
    assert 'page=2' in page.url and 'volunteer_search=Volunteer' in page.url
    page.get_by_role('link',name='Report',exact=True).click();page.wait_for_load_state('networkidle')
    assert '/report' in page.url and 'return_to=' in page.url
    checks.append('Page/search retained after save and connected report')

    page.goto(base+external+'?q=Community&attendance_status=unmarked&page=1');page.wait_for_load_state('networkidle')
    assert page.locator('textarea[name=roster]').count()==0
    page.get_by_role('link',name='Add External Participants',exact=True).click();page.wait_for_load_state('networkidle')
    assert page.url.startswith(base+entry) and 'q=Community' in page.url
    page.locator('#group_name').fill('Preserved Community Group')
    page.get_by_role('button',name='Save Named Roster',exact=True).click();page.wait_for_load_state('networkidle')
    expect(page.locator('#group_name')).to_have_value('Preserved Community Group')
    expect(page.locator('[data-form-errors]')).to_be_focused()
    assert page.locator('a[href="#roster"]').is_visible()
    page.once('dialog',lambda d:d.dismiss())
    page.get_by_role('link',name='Back to External Attendance',exact=True).click()
    assert '/external/new' in page.url
    page.locator('#roster').fill('Community Added,added@example.org')
    assert page.locator('.draft-status').count()==0
    expect(page.locator('[data-attendance-change-status]')).to_contain_text('Unsaved input')
    page.get_by_role('button',name='Save Named Roster',exact=True).click();page.wait_for_load_state('networkidle')
    assert page.url.startswith(base+external+'?') and 'attendance_status=unmarked' in page.url
    expect(page.get_by_text('Community Added',exact=True)).to_be_visible()
    page.screenshot(path=str(out/'external-after-add.png'))
    checks.append('Dedicated entry, retained filters, linked validation and saved group')

    for route,name in [(internal,'internal'),(external,'external'),(entry,'add-external'),(f'/workspace/activities/{eid}/registrations','registrations')]:
        page.goto(base+route);page.wait_for_load_state('networkidle')
        for target in page.locator('main a,main button,main input:not([type=hidden]),main select,main summary').all():
            if target.is_visible() and target.get_attribute('type') not in ('checkbox',):
                assert target.bounding_box()['height']>=43,(name,target.inner_text())
        page.set_viewport_size(dict(width=320,height=800));page.evaluate('document.documentElement.style.fontSize="200%"')
        if name!='add-external':
            page.locator('.roster-table strong').first.evaluate('(el)=>el.textContent="LongParticipantName".repeat(12)')
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,'200%')
        target=page.locator('main input:not([type=hidden]), main select, main textarea').first
        target.focus()
        page.wait_for_function('''() => {
            const box=document.activeElement.getBoundingClientRect();
            const header=document.querySelector('.role-topbar').getBoundingClientRect();
            const nav=document.querySelector('.mobile-nav').getBoundingClientRect();
            return box.top >= header.bottom-1 && box.bottom <= nav.top+1;
        }''',timeout=3000)
        page.screenshot(path=str(out/f'{name}-200.png'))
        page.evaluate('document.documentElement.style.fontSize=""')
        page.set_viewport_size(dict(width=1440,height=1000))
        page.emulate_media(media='print')
        assert not page.locator('.role-topbar').is_visible()
        if name in ('internal','external'):
            assert page.locator('.roster-table').is_visible()
            assert page.locator('.roster-print-status').first.is_visible()
        page.emulate_media(media='screen')
        checks.append([name,'touch targets, 200% text and print'])

    nojs=context.browser.new_context(java_script_enabled=False,storage_state=context.storage_state())
    np=nojs.new_page();np.goto(base+internal);np.locator('[data-attendance-status]').first.select_option('excused');np.get_by_role('button',name='Save Attendance',exact=True).click();np.wait_for_load_state('networkidle')
    assert np.locator('[data-attendance-status]').first.input_value()=='excused'
    np.goto(base+entry);np.locator('#roster').fill('No JS Person');np.get_by_role('button',name='Save Named Roster',exact=True).click();np.wait_for_load_state('networkidle')
    assert np.url.startswith(base+external) and 'new' not in np.url
    nojs.close();checks.append('Native no-JavaScript attendance and external-entry saves')

    for state in ['upcoming','ended','cancelled','missing']:
        with app.app_context():
            event=db.session.get(Event,eid);now=local_now();event.date=now-timedelta(hours=1);event.end_date=now+timedelta(hours=1);event.lifecycle_status='approved'
            if state=='upcoming':event.date=now+timedelta(hours=1);event.end_date=now+timedelta(hours=2)
            elif state=='ended':event.end_date=now-timedelta(minutes=1)
            elif state=='cancelled':event.lifecycle_status='cancelled'
            else:event.end_date=None
            db.session.commit()
        for route,name in [(internal,'internal'),(external,'external')]:
            page.goto(base+route);page.wait_for_load_state('networkidle')
            assert page.locator('select[name=status]').count()==0
            assert page.get_by_role('button',name='Save Attendance',exact=True).count()==0
            page.screenshot(path=str(out/f'{name}-{state}.png'))
        checks.append([state,'read-only status and visible schedule guidance'])

    # Reaching the end after opening a form must not commit any named people.
    with app.app_context():
        event=db.session.get(Event,eid);event.date=local_now()-timedelta(hours=1);event.end_date=local_now()+timedelta(hours=1);db.session.commit()
    page.goto(base+entry);page.locator('#roster').fill('Not Saved Person')
    with app.app_context():
        event=db.session.get(Event,eid);event.end_date=local_now()-timedelta(seconds=1);db.session.commit()
    page.get_by_role('button',name='Save Named Roster',exact=True).click();page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='Unsubmitted Participants',exact=True)).to_be_visible()
    expect(page.locator('#roster')).to_have_value('Not Saved Person')
    checks.append('Expiry after form load rejects save and retains entered names')


if __name__=='__main__':main()
