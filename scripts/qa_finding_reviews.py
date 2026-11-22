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
    out=Path('.qa-overhaul-temp/finding-reviews');out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config.update(WTF_CSRF_ENABLED=True,FINDING_REVIEWS_ENABLED=True)
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
    from app.models.finding_review import FindingReview,FindingReviewEvent
    with app.app_context():
        now=local_now()
        student=User.query.filter_by(role='volunteer').first()
        for title,start,end in [('Review Browser Outcome',now-timedelta(days=2),now-timedelta(days=1)),('Review Browser Ongoing',now-timedelta(hours=1),now+timedelta(hours=2))]:
            event=Event(title=title,description='Synthetic review fixture',campus_id=1,date=start,end_date=end,lifecycle_status='approved',slots=30)
            db.session.add(event);db.session.flush()
            db.session.add(Registration(event_id=event.id,user_id=student.id,status='confirmed'))
            if title.endswith('Outcome'):review_event_id=event.id
        Event.query.filter_by(id=events[0].id).update({'target_participants':50})
        for role,campus in [('other',2)]:
            user=User(name='Synthetic '+role,email=role+'@review.invalid',role='coordinator' if role=='other' else role,campus_id=campus,sex='prefer_not_to_say',password_hash='unused',first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user);db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        db.session.commit()
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)));page.on('dialog',lambda dialog:dialog.accept())
            detail_url=None
            for width in [1440,1024,768,390,320]:
                page.set_viewport_size(dict(width=width,height=900))
                for name,path in [('overview','/workspace/overview?period=all'),('active','/workspace/follow-up?period=all')]:
                    assert page.goto(base+path).status==200;page.wait_for_load_state('networkidle')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,width)
                    if name=='overview':
                        chart=page.locator('[data-review-chart]');expect(chart).to_be_visible()
                        assert chart.evaluate('el=>el.data[0].values.length')==4
                        total=chart.evaluate('el=>el.data[0].values.reduce((a,b)=>a+b,0)')
                        assert int(page.locator('.metric-tile > a').last.locator('strong').inner_text())==total
                        assert page.locator('.review-card-groups li').count()==4
                        chart.scroll_into_view_if_needed();page.screenshot(path=str(out/f'card-{width}.png'))
                    else:
                        row=page.locator('.review-queue li').filter(has_text='Review Browser Outcome')
                        row.get_by_role('link',name='Review',exact=True).click();page.wait_for_load_state('networkidle')
                        detail_url=page.url
                        assert page.locator('[name=assessment]').is_visible()
                        assert page.get_by_role('button',name='Notify Coordinator').count()==0
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                        page.screenshot(path=str(out/f'detail-{width}.png'),full_page=True)
                    checks.append([name,width,'layout, data and contextual actions'])
            page.locator('[name=assessment]').focus();assert page.locator('[name=assessment]').evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
            page.locator('form.finding-review-form').evaluate('el=>el.noValidate=true')
            page.get_by_role('button',name='Save Assessment',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('[data-form-errors]')).to_be_focused()
            page.locator('[name=assessment]').fill('Historical evidence reviewed. Improve attendance verification in future activities.')
            page.get_by_role('button',name='Save Assessment',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('.review-history')).to_contain_text('Assessed')
            checks.append(['server validation, focus and save assessment'])
            page.locator('[name=closure_reason]').select_option('historical_outcome_reviewed')
            page.get_by_role('button',name='Mark Reviewed and Close',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('.review-status')).to_contain_text('Reviewed and Closed')
            with app.app_context():
                closed=FindingReviewEvent.query.filter_by(action='closed').first()
                review=db.session.get(FindingReview,closed.review_id)
                occurrence_url=base+f'/workspace/finding-reviews/{review.finding_key}?occurrence={closed.id}'
            page.goto(base+'/workspace/follow-up?period=all&review_tab=reviewed');page.wait_for_load_state('networkidle')
            expect(page.locator('.review-queue')).to_contain_text('Review Browser Outcome')
            page.get_by_role('link',name='View Assessment',exact=True).first.click();page.wait_for_load_state('networkidle')
            expect(page.locator('main')).to_contain_text('Historical evidence reviewed.')
            page.emulate_media(media='print');page.screenshot(path=str(out/'completed-print.png'),full_page=True);page.emulate_media(media='screen')
            checks.append(['close, Reviewed history and print assessment'])
            for role,status in [('coordinator',200),('other',404)]:
                staff=browser.new_context();staff.add_cookies([dict(name='session',value=cookies[role],url=base)])
                viewer=staff.new_page();response=viewer.goto(occurrence_url);viewer.wait_for_load_state('networkidle')
                assert response.status==status,(role,response.status)
                assert viewer.locator('form.finding-review-form').count()==0
                staff.close();checks.append([role,'completed assessment access'])
            with app.app_context():
                someone=User.query.filter_by(role='coordinator',campus_id=1).first()
                db.session.add(Registration(event_id=review_event_id,user_id=someone.id,status='confirmed'));db.session.commit()
            page.goto(base+'/workspace/follow-up?period=all&finding_type=pending_attendance');page.wait_for_load_state('networkidle')
            expect(page.locator('.review-queue')).to_contain_text('Evidence Changed')
            page.locator('.review-queue li').filter(has_text='Review Browser Outcome').get_by_role('link',name='Review',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('[name=assessment]')).to_have_value('')
            expect(page.locator('summary')).to_contain_text('Previously Assessed Evidence')
            page.set_viewport_size(dict(width=390,height=900));page.evaluate("document.documentElement.style.fontSize='200%'")
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out/'detail-text200.png'),full_page=True)
            checks.append(['changed evidence, preserved previous decision and enlarged text'])
            page.goto(base+'/workspace/follow-up?period=all&finding_type=record_attendance');page.wait_for_load_state('networkidle')
            page.locator('.review-queue li').filter(has_text='Review Browser Ongoing').get_by_role('link',name='Review',exact=True).click();page.wait_for_load_state('networkidle')
            page.get_by_role('button',name='Notify Coordinator',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('.review-status')).to_contain_text('Follow-up Sent')
            checks.append(['actionable notification and follow-up status'])
            for javascript in [False,True]:
                fallback=browser.new_context(java_script_enabled=javascript,viewport=dict(width=390,height=900))
                fallback.add_cookies([dict(name='session',value=cookies['director'],url=base)])
                if javascript:fallback.route('**/plotly-*.js',lambda route:route.abort())
                basic=fallback.new_page();basic.goto(base+'/workspace/overview?period=all');basic.wait_for_load_state('networkidle')
                assert basic.locator('.review-card-groups li').count()==4
                assert basic.locator('[data-review-chart]:visible').count()==0
                if not javascript:
                    basic.goto(page.url);basic.wait_for_load_state('networkidle')
                    basic.locator('[name=assessment]').fill('Native form assessment saved without JavaScript.')
                    basic.get_by_role('button',name='Save Assessment',exact=True).click()
                    basic.wait_for_load_state('networkidle')
                    expect(basic.locator('[name=assessment]')).to_have_value('Native form assessment saved without JavaScript.')
                    checks.append(['native assessment form without JavaScript'])
                fallback.close();checks.append(['chart fallback',javascript])
            page.goto(base+'/workspace/overview?period=all&activity_name=NoMatchingFixture');page.wait_for_load_state('networkidle')
            expect(page.locator('.review-empty')).to_contain_text('0 Active Reviews')
            checks.append(['empty review card'])
            assert not errors,errors
            browser.close()
        print(f'{len(checks)} finding-review browser groups passed; evidence: {out}')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));server.shutdown()


if __name__=='__main__':main()
