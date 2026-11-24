"""Synthetic browser checks for the Coordinator Needs Attention desktop queue."""
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event, ExternalParticipant, Registration
from app.models.user import User
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True, FINDING_REVIEWS_ENABLED=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out = Path('.qa-overhaul-temp/coordinator-needs-desktop')
    out.mkdir(parents=True, exist_ok=True)
    checks, errors, cookies = [], [], {}
    with app.app_context():
        for role in ('director', 'coordinator'):
            user = User(name='Synthetic ' + role, email=role + '@coord-needs.invalid', role=role,
                        campus_id=1, password_hash='unused', sex='prefer_not_to_say',
                        first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user)
            db.session.flush()
            cookies[role] = app.session_interface.get_signing_serializer(app).dumps(
                dict(_user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        now = local_now()
        for index in range(7):
            event = Event(title=f'Synthetic Campus Finding {index}', description='Synthetic browser fixture',
                          campus_id=1, date=now - timedelta(days=2, minutes=index),
                          end_date=now - timedelta(days=1), lifecycle_status='approved')
            person = ExternalParticipant(name=f'Synthetic Participant {index}', id_number=f'COORD-NEEDS-{index}')
            db.session.add_all([event, person])
            db.session.flush()
            db.session.add(Registration(event_id=event.id, external_participant_id=person.id, status='confirmed'))
        db.session.commit()
    for name in app.jinja_env.list_templates():
        app.jinja_env.get_template(name)
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            director = browser.new_context(reduced_motion='reduce')
            director.add_cookies([dict(name='session', value=cookies['director'], url=base)])
            dpage = director.new_page()
            dpage.on('pageerror', lambda error: errors.append(str(error)))
            assert dpage.goto(base + '/workspace/follow-up?period=all').status == 200
            dpage.get_by_role('link', name='Review', exact=True).first.click()
            dpage.wait_for_load_state('networkidle')
            dpage.locator('textarea[name=assessment]').fill('Synthetic browser assessment for review closure.')
            dpage.locator('select[name=closure_reason]').select_option(index=1)
            dpage.on('dialog', lambda dialog: dialog.accept())
            dpage.get_by_role('button', name='Mark Reviewed and Close').click()
            dpage.wait_for_load_state('networkidle')
            checks.append('director closed one synthetic review')

            coord = browser.new_context(reduced_motion='reduce')
            coord.add_cookies([dict(name='session', value=cookies['coordinator'], url=base)])
            page = coord.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            queue = '/workspace/follow-up?period=all'
            for width in (1440, 1280, 1024, 768, 390, 320):
                page.set_viewport_size(dict(width=width, height=900))
                assert page.goto(base + queue).status == 200
                page.wait_for_load_state('networkidle')
                desktop = page.locator('.needs-desktop')
                original = page.locator('.needs-original')
                assert (desktop.is_visible(), original.is_visible()) == ((True, False) if width >= 1024 else (False, True))
                assert page.locator('.needs-queue > li').count() <= 5
                assert 'Remind Coordinator' not in (desktop.inner_text() if width >= 1024 else original.inner_text())
                if width >= 1024:
                    def size(selector):
                        return page.locator(selector).first.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)")
                    for selector, minimum in [('.needs-heading h1', 32), ('.needs-evidence h2', 18),
                                              ('.needs-meta', 14), ('.needs-categories a', 14),
                                              ('.needs-row-actions .btn', 15)]:
                        assert size(selector) >= minimum, (width, selector, size(selector))
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out / f'generated-{width}.png'), full_page=True)
                checks.append(['generated queue', width])
            page.set_viewport_size(dict(width=1440, height=900))
            page.goto(base + queue)
            page.wait_for_load_state('networkidle')
            chip = page.locator('.needs-categories a').nth(1)
            group = chip.get_attribute('href').split('review_group=')[1].split('&')[0]
            chip.focus()
            assert page.evaluate("document.activeElement===document.querySelectorAll('.needs-categories a')[1]")
            chip.press('Enter')
            page.wait_for_load_state('networkidle')
            assert f'review_group={group}' in page.url
            summary = page.locator('.needs-evidence-details summary').first
            summary.click()
            assert page.locator('.needs-evidence-details').first.get_attribute('open') is not None
            checks.append('category chip keyboard and evidence disclosure')
            page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out / 'generated-text200.png'), full_page=True)
            page.evaluate('document.documentElement.style.fontSize=""')
            checks.append('generated queue 200% text')
            for width in (1440, 390):
                page.set_viewport_size(dict(width=width, height=900))
                assert page.goto(base + '/workspace/follow-up?period=all&review_tab=reviewed').status == 200
                page.wait_for_load_state('networkidle')
                visible = page.locator('.needs-desktop' if width >= 1024 else '.needs-original')
                assert visible.is_visible()
                assert visible.get_by_role('link', name='View Assessment').count() >= 1
                assert 'Remind Coordinator' not in visible.inner_text() and 'Export CSV' not in visible.inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out / f'reviewed-{width}.png'), full_page=True)
                checks.append(['reviewed queue', width])
            dpage.set_viewport_size(dict(width=1440, height=900))
            assert dpage.goto(base + '/workspace/follow-up?period=all').status == 200
            dpage.wait_for_load_state('networkidle')
            assert dpage.get_by_role('navigation', name='Director Review Views').count() == 1
            assert 'Export CSV' in dpage.locator('.needs-desktop').inner_text()
            for selector, minimum in [('.needs-heading h1', 32), ('.needs-evidence h2', 18),
                                      ('.needs-meta', 14), ('.needs-categories a', 14),
                                      ('.needs-row-actions .btn', 15)]:
                actual = dpage.locator(selector).first.evaluate("el=>parseFloat(getComputedStyle(el).fontSize)")
                assert actual >= minimum, (selector, actual)
            checks.append('director queue regression and type scale')
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
    print(f'{len(checks)} browser checks passed; console errors: {len(errors)}')


if __name__ == '__main__':
    main()
