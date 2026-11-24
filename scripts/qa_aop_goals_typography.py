"""Synthetic browser checks for Director AOP Goals desktop typography."""
import logging
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from flask_login import login_user
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    out = Path('.qa-overhaul-temp/aop-goals-typography')
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    checks, errors = [], []
    with app.app_context(), app.test_request_context():
        user = User.query.filter_by(role='director').first()
        user.first_use_guide_dismissed_at = datetime.utcnow()
        login_user(user)
        cookie = app.session_interface.get_signing_serializer(app).dumps(
            dict(_user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        for name in app.jinja_env.list_templates():
            app.jinja_env.get_template(name)
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    path = '/annual-goals/workspace?year=2025'
    sizes = [('.aop-desktop-context', 14), ('.aop-director .journey-heading p', 16),
             ('.aop-director-summary > header h2', 18), ('.aop-director-summary > header p', 14),
             ('.aop-director-totals dt', 14), ('.aop-director-totals dd > span', 14),
             ('.aop-director-totals strong', 36), ('.aop-director-note p', 14),
             ('.aop-campus-tiles a', 14), ('.aop-campus-tiles small', 13)]
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session', value=cookie, url=base)])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for width in (1440, 1280, 1024):
                page.set_viewport_size(dict(width=width, height=1000))
                assert page.goto(base + path).status == 200
                page.wait_for_load_state('networkidle')
                for selector, minimum in sizes:
                    actual = page.locator(selector).first.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)")
                    assert actual >= minimum, (width, selector, actual)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'), width
                assert not page.locator('.aop-director-deliverables').is_visible()
                for tile in page.locator('.aop-campus-tiles a').all():
                    assert tile.evaluate('el=>el.scrollWidth<=el.clientWidth+1')
                    assert tile.bounding_box()['width'] >= 104
                page.screenshot(path=str(out / f'goals-{width}.png'), full_page=True)
                checks.append([width, 'type scale, contained tiles, hidden table and overflow'])
            page.set_viewport_size(dict(width=1440, height=1000))
            page.goto(base + path)
            page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out / 'goals-text200.png'), full_page=True)
            page.evaluate('document.documentElement.style.fontSize=""')
            checks.append('200% root-font text')
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
    print(f'{len(checks)} browser checks passed; console errors: {len(errors)}')


if __name__ == '__main__':
    main()
