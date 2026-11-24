"""Desktop report filtering and final outcomes against disposable synthetic data."""
import csv
import io
import json
import logging
import sys
from datetime import datetime,timedelta
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event,Registration,Attendance,ExternalParticipant,SdgGoal
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright,expect
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app=create_app('testing')
    app.config['ATTENDANCE_DEFAULTS_EFFECTIVE_FROM']=None
    out=Path('.qa-overhaul-temp/report-filter-outcomes')
    out.mkdir(parents=True,exist_ok=True)
    cookies,checks,errors={ },[],[]
    with app.app_context():
        now=local_now()
        for role in ('director','coordinator'):
            user=User.query.filter_by(role=role).first()
            user.first_use_guide_dismissed_at=datetime.utcnow()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        volunteer=User.query.filter_by(role='volunteer').first()
        volunteer.sex='female'
        female=ExternalParticipant(name='Synthetic Female Report',id_number='synthetic-report-female',sex='female')
        male=ExternalParticipant(name='Synthetic Male Report',id_number='synthetic-report-male',sex='male')
        sdgs=SdgGoal.query.filter(SdgGoal.number.in_([1,2])).order_by(SdgGoal.number).all()
        db.session.add_all([female,male]);db.session.flush()
        events={}
        for name,start,end in [('Primary',now-timedelta(days=2),now-timedelta(days=1)),
            ('Unrecorded',now-timedelta(days=2),now-timedelta(days=1)),
            ('Upcoming',now+timedelta(days=1),now+timedelta(days=2)),
            ('Ongoing',now-timedelta(hours=1),now+timedelta(hours=1)),
            ('Missing End',now-timedelta(days=1),None)]:
            event=Event(title='Synthetic Report Fix '+name,description='Synthetic browser fixture',date=start,end_date=end,
                campus_id=1,lifecycle_status='approved',category='Environment',conducting_department='Extension',target_participants=2)
            db.session.add(event);db.session.flush();events[name]=event
        events['Primary'].sdgs=sdgs
        for person,attendance in [(volunteer,'present'),(male,'present'),(female,None)]:
            reg=Registration(event_id=events['Primary'].id,status='confirmed',**({'user_id':person.id} if isinstance(person,User) else {'external_participant_id':person.id}))
            db.session.add(reg);db.session.flush()
            if attendance:db.session.add(Attendance(event_id=events['Primary'].id,registration_id=reg.id,status=attendance))
        db.session.add(Registration(event_id=events['Unrecorded'].id,user_id=volunteer.id,status='confirmed'))
        db.session.commit()
        primary_id=events['Primary'].id
        for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    server=make_server('127.0.0.1',0,app)
    Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    path='/workspace/reports/results?period=all&activity_name=Synthetic+Report+Fix'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for role,cookie in cookies.items():
                context=browser.new_context()
                context.add_cookies([dict(name='session',value=cookie,url=base)])
                page=context.new_page()
                page.on('pageerror',lambda error:errors.append(str(error)))
                for width in (1440,1280,1024):
                    page.set_viewport_size(dict(width=width,height=1000))
                    assert page.goto(base+path+'&view=activities').status==200
                    page.wait_for_load_state('networkidle')
                    expect(page.locator('.activity-report-table')).to_contain_text('SDG 1: No Poverty')
                    expect(page.locator('.activity-report-table')).to_contain_text('SDG 2: Zero Hunger')
                    expect(page.locator('.activity-report-table')).to_contain_text('No SDGs Assigned')
                    page.select_option('.report-filters [name=delivery]','approved')
                    page.locator('.report-filters').get_by_role('button',name='Apply Filters',exact=True).click()
                    assert page.locator('.activity-report-table tbody tr').count()==3
                    expect(page.locator('.activity-report-table')).not_to_contain_text('Synthetic Report Fix Primary')
                    page.select_option('.report-filters [name=delivery]','conducted')
                    page.locator('.report-filters').get_by_role('button',name='Apply Filters',exact=True).click()
                    assert page.locator('.activity-report-table tbody tr').count()==2
                    page.get_by_role('link',name='Participation Records',exact=True).click()
                    assert 'delivery=conducted' in page.url
                    page.wait_for_selector('[data-sdg-chart].js-plotly-plot')
                    expect(page.locator('.sdg-alignment-table')).to_contain_text('SDG 1: No Poverty')
                    expect(page.locator('.report-sdg-alignment .attendance-total')).to_contain_text('2 activity-to-SDG links')
                    sex=page.locator('.sex-attendance').bounding_box()
                    sdg=page.locator('.report-sdg-alignment').bounding_box()
                    assert abs(sex['y']-sdg['y'])<2 and sdg['x']>=sex['x']+sex['width']
                    row=page.locator('.participation-report-table tbody tr').filter(has_text='Synthetic Report Fix Unrecorded')
                    expect(row).to_contain_text('0.0%')
                    expect(row).to_contain_text('Target Not Met')
                    expect(row).to_contain_text('Ended · 1 Unrecorded')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
                checks.append(f'{role}: three desktop widths, SDG donut beside attendance, exact values, delivery separation, tabs and ended outcomes')
                page.goto(base+path+'&view=summary&delivery=approved')
                expect(page.locator('.report-sdg-alignment')).to_contain_text('No SDGs are assigned')
                page.goto(base+path+'&view=participation&delivery=conducted&sex=female')
                row=page.locator('.participation-report-table tbody tr').filter(has_text='Synthetic Report Fix Primary')
                expect(row).to_contain_text('50.0%')
                expect(row).to_contain_text('Target Met')
                expect(row).to_contain_text('Whole-Activity Target')
                page.evaluate('document.documentElement.style.fontSize="200%";window.dispatchEvent(new Event("resize"))')
                page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=str(out/f'{role}-sdg-enlarged.png'),full_page=True)
                page.evaluate('document.documentElement.style.fontSize="";window.dispatchEvent(new Event("resize"))')
                exported=context.request.get(base+'/workspace/reports/export/csv?period=all&activity_name=Synthetic+Report+Fix&delivery=conducted&sex=female')
                rows=list(csv.DictReader(io.StringIO(exported.body().decode('utf-8-sig'))))
                assert len(rows)==2 and any(row['Target outcome']=='Target Not Met' for row in rows)
                assert page.goto(base+f'/workspace/reports/activities/{primary_id}?period=all&sex=female').status==200
                expect(page.locator('[aria-label="Named Attendance Roster"]')).not_to_contain_text('Synthetic Male Report')
                page.keyboard.press('Tab')
                assert page.evaluate('document.activeElement.tagName') in ('A','BUTTON','INPUT','SELECT','SUMMARY')
                page.evaluate('document.documentElement.style.fontSize="200%";window.dispatchEvent(new Event("resize"))')
                page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                checks.append(f'{role}: filtered rate, whole-event target, CSV, scoped roster, keyboard and enlarged text')
                context.close()
            context=browser.new_context(java_script_enabled=False,viewport=dict(width=1440,height=1000))
            context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=context.new_page()
            assert page.goto(base+path+'&view=participation&delivery=conducted').status==200
            expect(page.locator('.participation-report-table')).to_contain_text('Target Not Met')
            expect(page.locator('.sdg-alignment-table')).to_contain_text('SDG 1: No Poverty')
            page.get_by_role('link',name='Activity Records',exact=True).click()
            expect(page.locator('.activity-report-table')).to_contain_text('SDG 1: No Poverty')
            checks.append('JavaScript-disabled report outcomes and scoped tab navigation')
            context.close()
            context=browser.new_context(viewport=dict(width=1440,height=1000))
            context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            context.route('**/plotly-5.24.1.min.js',lambda route:route.abort())
            page=context.new_page()
            page.goto(base+path+'&view=summary&delivery=conducted')
            expect(page.locator('.sdg-alignment-table')).to_contain_text('50.0%')
            expect(page.locator('.report-sdg-alignment [data-chart-status]')).to_be_visible()
            page.set_viewport_size(dict(width=390,height=844))
            expect(page.locator('.report-sdg-alignment')).to_be_hidden()
            assert page.locator('.report-attendance-sdg').evaluate('el=>getComputedStyle(el).display')=='block'
            checks.append('Unavailable chart library retains exact SDG values; narrow layout remains unchanged')
            browser.close()
        assert not errors,errors
        result=dict(checks=checks,errors=errors)
        (out/'results.json').write_text(json.dumps(result,indent=2))
        print(json.dumps(result,indent=2))
    finally:
        server.shutdown()


if __name__=='__main__':main()
