"""Check the campus/university summary using an isolated presentation database."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app
from app.models import db
from app.models.user import User
import app.presentation_dataset as dataset


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app('testing')
    with app.app_context():
        db.session.remove()
        with db.engine.connect() as connection:
            connection.exec_driver_sql('PRAGMA foreign_keys=ON')
    dataset._now = lambda: datetime(2026, 11, 1, 12)
    original = User.set_password
    User.set_password = lambda self, password: setattr(self, 'password_hash', 'unusable-qa')
    try:
        result = app.test_cli_runner().invoke(
            args=['reset-and-seed-presentation', '--database', ':memory:'],
            input='RESET PRESENTATION local/:memory:\n')
        assert result.exit_code == 0, result.output
    finally:
        User.set_password = original
    with app.app_context():
        user = User.query.filter_by(email='director@psu.edu').one()
        cookie = app.session_interface.get_signing_serializer(app).dumps(
            {'_user_id': str(user.id), '_fresh': True, 'auth_version': user.auth_version})
    server = make_server('127.0.0.1', 0, app)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    try:
        with sync_playwright() as runtime:
            browser = runtime.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies([dict(name=app.config['SESSION_COOKIE_NAME'], value=cookie, url=base)])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for width in (1440, 900, 768, 390, 320):
                page.set_viewport_size(dict(width=width, height=1000))
                assert page.goto(base + '/director_dash?goal_year=2026').status == 200
                skip = page.get_by_role('button', name='Skip Guide', exact=True)
                if skip.is_visible():
                    skip.click()
                overview = page.locator('.goal-overview')
                assert '14 of 27 Approved Goals' in overview.inner_text()
                assert '3 awaiting evidence' in page.locator('.goal-university').inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                link = page.get_by_role('link', name='View University Targets', exact=True)
                box = link.bounding_box()
                assert box['height'] >= 44 and box['width'] >= 44
                page.keyboard.press('Tab')
                link.focus()
                assert link.evaluate('(element) => element.matches(":focus-visible")')
                if width in (1440, 390):
                    page.screenshot(path=str(Path(__file__).resolve().parents[1] /
                                             f'.qa-campus-summary-{width}.png'), full_page=True)
                with page.expect_navigation():
                    link.press('Enter')
                assert 'University goal evidence' in page.locator('h1').inner_text()
                checks.append(dict(width=width, overflow=False, keyboard_link=True))
            browser.close()
        assert not errors, errors
        print(json.dumps(dict(checks=checks, page_errors=errors), indent=2))
    finally:
        server.shutdown()
        thread.join(timeout=5)


if __name__ == '__main__':
    main()
