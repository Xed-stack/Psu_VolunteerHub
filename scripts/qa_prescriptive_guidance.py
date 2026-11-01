"""Browser QA against an isolated in-memory database, never the running app."""
import json
import logging
import sys
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from werkzeug.serving import make_server

from app import create_app
from app.models import db
from app.models.event import Campus
from tests.test_app import _seed_campuses, _seed_events, _create_user
from tests.test_annual_goals import target
from tests.test_dashboard_followups import pending_activities


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app('testing')
    app.config.update(SERVER_NAME=None, WTF_CSRF_ENABLED=True)
    with app.app_context():
        db._app_engines[app][None] = create_engine('sqlite://', poolclass=StaticPool,
            connect_args={'check_same_thread': False})
        db.create_all()
        _seed_campuses()
        _seed_events()
        coordinator = _create_user(app, role='coordinator', campus_id=1)
        director = _create_user(app, email='director-qa@test.com', role='director')
        admin = _create_user(app, email='admin-qa@test.com', role='admin')
        target(campus=1, actual=0)
        pending_activities(6)
        db.session.get(Campus, 1).name = 'Lingayen Campus With a Long Name for Layout Verification'
        db.session.commit()
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    results, errors = [], []
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            for role, uid, paths in [
                ('director', director, ['/director_dash?period=all', '/analytics?period=all']),
                ('coordinator', coordinator, ['/coordinator_dash?period=all', '/coordinator_analytics?period=all']),
                ('admin', admin, ['/analytics?period=all'])]:
                context = browser.new_context()
                cookie = app.session_interface.get_signing_serializer(app).dumps(
                    {'_user_id': str(uid), '_fresh': True, 'auth_version': 1})
                context.add_cookies([dict(name=app.config['SESSION_COOKIE_NAME'], value=cookie, url=base)])
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                for path in paths:
                    for width in (1440, 768, 720, 390):
                        page.set_viewport_size(dict(width=width, height=1000))
                        response = page.goto(base + path)
                        assert response.status == 200, (role, path, response.status)
                        skip = page.get_by_role('button', name='Skip Guide', exact=True)
                        if skip.is_visible():
                            skip.click()
                        page.locator('details').evaluate_all('(items) => items.forEach(item => item.open = true)')
                        page.wait_for_timeout(300)
                        overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                        assert not overflow, (role, path, width, 'page overflow')
                        for control in page.locator('[data-guidance] .btn').all():
                            if control.is_visible():
                                box = control.bounding_box()
                                assert box['height'] >= 44 and box['width'] >= 44, box
                        if role == 'coordinator' and path.startswith('/coordinator_dash') and width == 1440:
                            panels = page.locator('.coordinator-briefing > *')
                            left, right = panels.nth(0).bounding_box(), panels.nth(1).bounding_box()
                            assert abs(left['width'] - right['width']) < 1 and abs(left['height'] - right['height']) < 1
                        if role == 'admin':
                            assert page.locator('[data-guidance]').count() == 0
                        results.append(dict(role=role, path=path, width=width, overflow=False))
                if role == 'director':
                    page.set_viewport_size(dict(width=1440, height=1000))
                    page.goto(base + '/director_dash?period=all')
                    summary = page.locator('#campus-guidance > summary')
                    summary.focus()
                    initial_open = page.locator('#campus-guidance').get_attribute('open') is not None
                    page.keyboard.press('Enter')
                    page.wait_for_timeout(100)
                    assert (page.locator('#campus-guidance').get_attribute('open') is not None) != initial_open
                    if initial_open:
                        summary.press('Enter')
                    notify = page.locator('#campus-guidance [data-guidance="pending_attendance"] button').first
                    notify.focus()
                    assert notify.evaluate('(el) => el.matches(":focus-visible")')
                    with page.expect_navigation():
                        notify.press('Enter')
                    assert 'Follow-up sent to' in page.locator('body').inner_text()
                    assert page.locator('#campus-guidance').get_attribute('open') is not None
                    with page.expect_navigation():
                        page.locator('#campus-guidance [data-guidance="pending_attendance"] button').first.click()
                    assert 'equivalent unread reminder' in page.locator('body').inner_text()
                    page.screenshot(path=str(Path(__file__).resolve().parents[1] / '.qa-prescriptive-director.png'), full_page=True)
                    results.append(dict(action='Director send, duplicate feedback, keyboard expansion and focus', passed=True))
                if role == 'coordinator':
                    page.goto(base + '/notifications')
                    link = page.get_by_role('link', name='Review Campus Records').first
                    link.click()
                    page.wait_for_load_state()
                    assert '/coordinator_analytics' in page.url
                    assert page.locator('#detailed-report').get_attribute('open') is not None
                    page.goto(base + '/coordinator_dash?period=all')
                    page.get_by_role('link', name='Next Page', exact=True).click()
                    page.wait_for_load_state()
                    assert page.locator('[aria-current="page"]').inner_text() == '2'
                    page.get_by_role('link', name='Previous Page', exact=True).click()
                    page.wait_for_load_state()
                    assert page.locator('[aria-current="page"]').inner_text() == '1'
                    page.screenshot(path=str(Path(__file__).resolve().parents[1] / '.qa-prescriptive-coordinator.png'), full_page=True)
                    results.append(dict(action='Inbox destination and follow-up pagination', passed=True))
                context.close()
            context = browser.new_context(java_script_enabled=False, viewport=dict(width=390, height=1000))
            cookie = app.session_interface.get_signing_serializer(app).dumps(
                {'_user_id': str(director), '_fresh': True, 'auth_version': 1})
            context.add_cookies([dict(name=app.config['SESSION_COOKIE_NAME'], value=cookie, url=base)])
            page = context.new_page()
            page.goto(base + '/director_dash?period=all')
            page.locator('#campus-guidance > summary').click()
            page.locator('#campus-guidance [data-guidance="pending_attendance"] button').first.click()
            page.wait_for_load_state()
            assert 'equivalent unread reminder' in page.locator('body').inner_text()
            results.append(dict(action='Native disclosure and form work without JavaScript', passed=True))
            context.close()
            browser.close()
        assert not errors, errors
        print(json.dumps(dict(checks=results, page_errors=errors), indent=2))
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
