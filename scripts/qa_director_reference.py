"""Browser acceptance for the reference Overview using disposable SQLite data."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event, Campus
from app.report_demo import seed_aop_commitments
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out = Path('.qa-overhaul-temp/director-reference').resolve()
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True, PRIVATE_UPLOAD_FOLDER=str(out / 'private'))
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    checks, errors, cookies = [], [], {}
    with app.app_context():
        for role in ('director', 'coordinator'):
            user = User.query.filter_by(role=role).first()
            user.first_use_guide_dismissed_at = datetime.utcnow()
            cookies[role] = app.session_interface.get_signing_serializer(app).dumps(dict(
                _user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        events = []
        for index in range(13):
            event = Event(title=f'Synthetic Completed AOP {index}', description='Synthetic', campus_id=1,
                          date=datetime(2025, 6, 1, 8), end_date=datetime(2025, 6, 1, 9),
                          lifecycle_status='approved')
            db.session.add(event)
            events.append(event)
        db.session.flush()
        seed_aop_commitments(2025, Campus.query.order_by(Campus.id).all(), events)
        db.session.commit()
        templates = app.jinja_env.list_templates()
        for name in templates:
            app.jinja_env.get_template(name)
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    path = '/workspace/overview?year=2025&period=annual'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session', value=cookies['director'], url=base)])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for enabled in (False, True):
                app.config['FINDING_REVIEWS_ENABLED'] = enabled
                for width in (1440, 1280, 1024, 768, 390, 320):
                    page.set_viewport_size(dict(width=width, height=1000))
                    assert page.goto(base + path).status == 200
                    page.wait_for_load_state('networkidle')
                    expect(page.locator('.director-achievement-label strong')).to_have_text('130% AOP Goal Achievement Rate')
                    expect(page.locator('.director-achievement-label strong')).to_have_css('color', 'rgb(0, 43, 96)')
                    assert 'by 3.' in page.locator('.director-achievement-top').inner_text()
                    assert page.locator('.director-achievement-metric').count() == 3
                    assert page.locator('[data-campus-chart],[data-sex-chart],[data-month-chart],.director-secondary-summary,.staff-footer-links').count() == 0
                    expect(page.locator('[data-review-chart] .main-svg').first).to_be_visible()
                    assert page.locator('.director-commitments-table tbody tr').count() == 9
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (enabled, width)
                    review = page.locator('.review-card').bounding_box()
                    campus = page.locator('.director-commitments').bounding_box()
                    if width >= 1280:
                        assert abs(review['y'] - campus['y']) < 2
                        assert campus['width'] > review['width']
                    else:
                        assert campus['y'] >= review['y'] + review['height']
                    for link in page.locator('.review-card a,.director-commitments a').all():
                        assert link.bounding_box()['height'] >= 44
                    tiles = page.locator('.director-achievement-metric').evaluate_all('els=>els.map(el=>({y:el.offsetTop,w:el.offsetWidth}))')
                    if width >= 1024:
                        assert len({tile['y'] for tile in tiles}) == 1
                    elif width >= 480:
                        assert tiles[0]['y'] == tiles[1]['y'] and tiles[2]['w'] > tiles[0]['w']
                    else:
                        assert len({tile['y'] for tile in tiles}) == 3
                    page.screenshot(path=str(out / f'overview-{enabled}-{width}.png'), full_page=True)
                    checks.append([enabled, width, '130%, one chart, nine campuses, layout and targets'])

            page.set_viewport_size(dict(width=1440, height=1000))
            page.goto(base + path + '&campus_id=1')
            expect(page.locator('.review-empty')).to_be_visible()
            assert 'No active reviews' in page.locator('.director-review-next').inner_text()
            checks.append('No-review state retains queue access and a factual next action')
            page.goto(base + path + '&campus_id=2&sex=female')
            page.wait_for_load_state('networkidle')
            expect(page.locator('.director-commitments-table tbody tr')).to_have_count(1)
            assert 'denominator remains' in page.locator('.director-achievement-scope').inner_text()
            page.locator('.review-card-groups a').first.focus()
            assert page.locator('.review-card-groups a').first.evaluate('el=>getComputedStyle(el).outlineStyle') != 'none'
            page.keyboard.press('Enter')
            page.wait_for_url('**/workspace/follow-up**')
            assert 'campus_id=2' in page.url and 'sex=female' in page.url
            checks.append('Filtered scope and keyboard queue navigation')

            for period, segment in (('annual', 1), ('semiannual', 2), ('quarterly', 2), ('custom', 1), ('all', 1)):
                page.goto(base + path)
                page.select_option('[name=period]', period)
                if period in ('semiannual', 'quarterly'):
                    page.select_option('[name=segment]', str(segment))
                if period == 'custom':
                    page.fill('[name=start_date]', '2025-01-01')
                    page.fill('[name=end_date]', '2025-12-31')
                page.get_by_role('button', name='Apply Scope', exact=True).click()
                page.wait_for_load_state('networkidle')
                expect(page.locator('.director-achievement-label strong')).to_have_text('130% AOP Goal Achievement Rate')
            checks.append('All five evaluation periods submit without changing annual achievement')

            page.goto(base + path)
            links = page.locator('.staff-overview a:not([data-guide-replay])').evaluate_all('els=>els.map(el=>el.getAttribute("href"))')
            for href in dict.fromkeys(links):
                assert page.goto(base + href).status == 200, href
                page.wait_for_load_state('networkidle')
            checks.append(f'{len(set(links))} distinct Overview navigation destinations opened')
            page.goto(base + path + '&tour=1')
            expect(page.locator('#tourTitle')).to_have_text('Choose the Overview Scope')
            while page.get_by_role('button', name='Next', exact=True).is_visible():
                page.get_by_role('button', name='Next', exact=True).click()
            page.get_by_role('button', name='Finish', exact=True).click()
            expect(page.locator('.first-use-tour')).not_to_be_visible()
            checks.append('Director guide completed with updated targets')

            with app.app_context():
                campus = db.session.get(Campus, 1)
                campus.name = 'Synthetic Long Campus Name ' * 8
                db.session.commit()
            page.set_viewport_size(dict(width=320, height=1000))
            page.goto(base + path)
            page.evaluate("document.documentElement.style.fontSize='32px'")
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            page.screenshot(path=str(out / 'enlarged-text.png'), full_page=True)
            page.evaluate("document.documentElement.style.fontSize=''")
            page.goto(base + '/workspace/overview?year=1900')
            expect(page.locator('.director-achievement-label strong')).to_have_text('AOP Target Not Set')
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            checks.append('Long campus name, doubled root text and no-target state')

            for javascript in (True, False):
                fallback = browser.new_context(java_script_enabled=javascript, viewport=dict(width=390, height=1000))
                fallback.add_cookies([dict(name='session', value=cookies['director'], url=base)])
                view = fallback.new_page()
                if javascript:
                    view.route('**/plotly-5.24.1.min.js', lambda route: route.abort())
                assert view.goto(base + path).status == 200
                view.wait_for_load_state('networkidle')
                expect(view.locator('.director-commitments-table')).to_be_visible()
                assert view.locator('.review-card-groups a').count() == 4
                assert not view.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                fallback.close()
            checks.append('Blocked chart library and no-JavaScript exact values and actions')
            context.add_cookies([dict(name='session', value=cookies['coordinator'], url=base)])
            page.goto(base + path)
            assert page.locator('.director-achievement-metric').count() == 3
            assert page.locator('.coordinator-primary-grid').count() == 1
            assert page.locator('.director-overview').count() == 0
            checks.append('Coordinator uses its approved three-metric reference layout')
            browser.close()
        assert not errors, errors
        print(f'{len(checks)} browser groups passed; {len(templates)} templates parsed; {out}')
    finally:
        (out / 'results.json').write_text(json.dumps(dict(checks=checks, errors=errors), indent=2), encoding='utf-8')
        server.shutdown()


if __name__ == '__main__':
    main()
