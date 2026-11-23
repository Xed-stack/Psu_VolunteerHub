"""Headless browser checks against disposable, synthetic in-memory AOP data."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event
from app.models.user import User
from app.models.annual_plan import AnnualTarget, AnnualGoalProposal, AnnualActivityMapping
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out = Path('.qa-overhaul-temp/aop-commitments').resolve()
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True, PRIVATE_UPLOAD_FOLDER=str(out/'private'))
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    cookies, checks, errors = {}, [], []
    year = local_now().year
    with app.app_context():
        for role in ('director', 'coordinator'):
            user = User(name='Synthetic AOP '+role, email=role+'@aop.invalid', role=role,
                        campus_id=1, password_hash='unused', sex='prefer_not_to_say',
                        first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user)
            db.session.flush()
            cookies[role] = app.session_interface.get_signing_serializer(app).dumps(dict(
                _user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        event = Event(title='Synthetic Completed Community Activity', description='Synthetic browser evidence',
            date=datetime(year, 7, 1, 8), end_date=datetime(year, 7, 1, 10), campus_id=1,
            lifecycle_status='approved', slots=20)
        db.session.add(event)
        db.session.commit()
        event_id = event.id
        for name in app.jinja_env.list_templates():
            app.jinja_env.get_template(name)
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session', value=cookies['director'], url=base)])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            response = page.goto(base+'/annual-goals/workspace')
            assert response.status == 200
            page.wait_for_load_state('networkidle')
            expect(page.get_by_role('heading', name=f'No AOP Goals for {year}')).to_be_visible()
            checks.append('Empty goal list')
            page.get_by_role('link', name='Post AOP Goal').click()
            page.get_by_label('Goal Title').fill('Synthetic Community Learning Goal')
            page.get_by_label('Director Target').fill('1')
            page.get_by_label('Description', exact=True).fill('Synthetic goal for browser verification only.')
            for label, value in [('Start Date', f'{year}-06-01'), ('End Date', f'{year}-12-31')]:
                page.locator('[data-moa-picker='+('start_date' if label=='Start Date' else 'end_date')+']').click()
                expect(page.get_by_role('dialog')).to_be_visible()
                page.get_by_label('Date', exact=True).fill(value)
                page.get_by_role('button', name='Confirm', exact=True).click()
                expect(page.get_by_role('dialog')).not_to_be_visible()
            page.get_by_role('button', name='Publish AOP Goal', exact=True).click()
            page.wait_for_load_state('networkidle')
            expect(page.get_by_role('heading', name='University Progress')).to_be_visible()
            goal_id = int(page.url.rsplit('/', 1)[1])
            checks.append('Director publishes with shared date dialog and CSRF')
            context.add_cookies([dict(name='session', value=cookies['coordinator'], url=base)])
            page.goto(base+'/notifications')
            page.wait_for_load_state('networkidle')
            expect(page.get_by_text('AOP Goal Published or Updated', exact=True)).to_be_visible()
            page.goto(base+f'/annual-goals/targets/{goal_id}')
            page.get_by_role('link', name='Submit Commitment', exact=True).click()
            page.get_by_label('Campus Goal', exact=False).fill('2')
            page.get_by_label('Explanation (Optional)').fill('Synthetic campus commitment.')
            page.get_by_role('button', name='Submit Commitment', exact=True).click()
            page.wait_for_load_state('networkidle')
            expect(page.get_by_role('heading', name='Your Campus')).to_be_visible()
            expect(page.get_by_role('link', name='Link Activities', exact=True)).to_be_visible()
            checks.append('Immediate commitment greater than Director target')
            page.get_by_role('link', name='Link Activities', exact=True).click()
            page.get_by_role('checkbox', name='Synthetic Completed Community Activity', exact=False).check()
            page.get_by_role('button', name='Save Activity Links').click()
            page.wait_for_load_state('networkidle')
            expect(page.get_by_text('Completed', exact=True)).to_be_visible()
            with app.app_context():
                assert AnnualActivityMapping.query.count() == 1
                child = AnnualTarget.query.filter_by(workflow_kind='campus_commitment').one()
                assert int(child.target_value) == 2
            checks.append('Ended activity earns credit without attendance')
            for role in ('director', 'coordinator'):
                context.add_cookies([dict(name='session', value=cookies[role], url=base)])
                routes = ['/annual-goals/workspace', f'/annual-goals/targets/{goal_id}',
                          f'/annual-goals/proposals/new?target_id={goal_id}'] if role == 'director' else [
                              '/annual-goals/workspace', f'/annual-goals/targets/{goal_id}',
                              f'/annual-goals/targets/{goal_id}/commitment',
                              f'/annual-goals/targets/{goal_id}/link-activities', '/workspace/create/2']
                for width in (1440, 1024, 768, 390, 320):
                    page.set_viewport_size(dict(width=width, height=900))
                    for index, route in enumerate(routes):
                        assert page.goto(base+route).status == 200
                        page.wait_for_load_state('networkidle')
                        assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (role,width,route)
                        for control in page.locator('.aop-page a, .aop-page button, .aop-page summary, .aop-page .aop-check').all():
                            if control.is_visible():
                                box=control.bounding_box()
                                assert box['height'] >= 44 and box['width'] >= 44, (width,route,control.text_content(),box)
                        assert not page.get_by_role('button', name='Approve', exact=True).count()
                        assert not page.get_by_text('ASP', exact=True).count()
                        if index < 3:
                            page.screenshot(path=str(out/f'{role}-{width}-{index}.png'), full_page=True)
                    checks.append([role, width, 'Layouts, no overflow, no approval, no ASP'])
            context.add_cookies([dict(name='session', value=cookies['director'], url=base)])
            page.goto(base+f'/annual-goals/proposals/new?target_id={goal_id}')
            page.locator('[data-moa-picker=start_date]').click()
            page.get_by_label('Date', exact=True).fill(f'{year}-08-01')
            page.get_by_role('button', name='Confirm', exact=True).click()
            page.get_by_role('button', name='Publish Revision', exact=True).click()
            expect(page.get_by_role('heading', name='Review Period Change')).to_be_visible()
            expect(page.get_by_text('Completed activities: 1 before', exact=False)).to_be_visible()
            page.get_by_role('checkbox', name='I confirm this period change', exact=False).check()
            page.get_by_role('button', name='Publish Revision', exact=True).click()
            page.wait_for_load_state('networkidle')
            expect(page.get_by_text('Outside Goal Period', exact=True)).to_be_visible()
            checks.append('Period revision preview and retained ineligible link')
            page.goto(base+'/annual-goals/proposals/new')
            page.keyboard.press('Tab')
            page.keyboard.press('Tab')
            assert page.evaluate('document.activeElement.tagName') in ('A','BUTTON','INPUT')
            page.evaluate("document.documentElement.style.fontSize='24px'")
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            checks.append('Keyboard focus and enlarged text')
            nojs = browser.new_context(java_script_enabled=False, viewport=dict(width=320,height=900))
            nojs.add_cookies([dict(name='session', value=cookies['director'], url=base)])
            native = nojs.new_page()
            native.goto(base+'/annual-goals/proposals/new')
            expect(native.locator('input[name=start_date]')).to_be_visible()
            expect(native.locator('[data-moa-picker=start_date]')).not_to_be_visible()
            checks.append('Native date inputs without JavaScript')
            nojs.close()
            context.close()
            browser.close()
        assert not errors, errors
        (out/'results.json').write_text(json.dumps(dict(checks=checks, errors=errors), indent=2), encoding='utf-8')
        print(f'{len(checks)} AOP browser groups passed; evidence: {out}')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
