"""Coordinator Overview browser acceptance with disposable synthetic SQLite."""
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event, Campus, Registration, Attendance
from app.models.annual_plan import AnnualTarget
from app.report_demo import seed_aop_commitments
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out = Path('.qa-overhaul-temp/coordinator-reference').resolve()
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True, PRIVATE_UPLOAD_FOLDER=str(out / 'private'))
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    checks, errors = [], []
    with app.app_context():
        user = User.query.filter_by(role='coordinator', campus_id=1).first()
        user.first_use_guide_dismissed_at = datetime.utcnow()
        cookie = app.session_interface.get_signing_serializer(app).dumps(dict(
            _user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        for event in Event.query.all():
            event.date = datetime(2020, 6, 1)
            event.end_date = datetime(2020, 6, 2)
        ended = []
        for year, count in ((2025, 13), (2024, 10), (2023, 0)):
            events = []
            for index in range(count):
                event = Event(title=f'Synthetic Campus AOP {year}-{index}', description='Synthetic', campus_id=1,
                              date=datetime(year, 6, 1, 8), end_date=datetime(year, 6, 1, 9),
                              lifecycle_status='approved', target_participants=10)
                db.session.add(event)
                events.append(event)
            db.session.flush()
            seed_aop_commitments(year, Campus.query.order_by(Campus.id).all(), events)
            AnnualTarget.query.filter_by(workflow_kind='campus_commitment', campus_id=1).update(
                dict(target_value=10), synchronize_session=False)
            ended.extend(events)
        volunteer = User.query.filter_by(role='volunteer').first()
        registration = Registration(user_id=volunteer.id, event_id=ended[0].id, status='confirmed')
        db.session.add(registration)
        db.session.flush()
        db.session.add(Attendance(user_id=volunteer.id, event_id=ended[0].id,
                                  registration_id=registration.id, status='present'))
        now = local_now()
        ongoing = Event(title='Synthetic Ongoing Campus Activity', description='Synthetic', campus_id=1,
                        date=now - timedelta(hours=1), end_date=now + timedelta(hours=2), lifecycle_status='approved')
        db.session.add(ongoing)
        db.session.flush()
        db.session.add(Registration(user_id=volunteer.id, event_id=ongoing.id, status='confirmed'))
        for index in range(6):
            db.session.add(Event(title=f'Synthetic Upcoming Campus Activity {index}', description='Synthetic', campus_id=1,
                date=now + timedelta(days=index+1), end_date=now + timedelta(days=index+1, hours=2), lifecycle_status='approved'))
        db.session.add(Event(title='Synthetic Incomplete Schedule', description='Synthetic', campus_id=1,
                            date=now + timedelta(days=10), lifecycle_status='approved'))
        db.session.add(Event(title='Other Campus Must Stay Hidden', description='Synthetic', campus_id=2,
                            date=now + timedelta(minutes=1), end_date=now + timedelta(hours=3), lifecycle_status='approved'))
        db.session.commit()
        templates = app.jinja_env.list_templates()
        for name in templates:
            app.jinja_env.get_template(name)
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    path = '/workspace/overview?year=2025&period=all'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session', value=cookie, url=base)])
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for enabled in (False, True):
                app.config['FINDING_REVIEWS_ENABLED'] = enabled
                for width in (1440, 1280, 1024, 768, 390, 320):
                    page.set_viewport_size(dict(width=width, height=1000))
                    assert page.goto(base + path).status == 200
                    page.wait_for_load_state('networkidle')
                    assert '130%' in page.locator('.director-achievement-label strong').inner_text()
                    assert 'by 3' in page.locator('.director-achievement-top').inner_text()
                    assert page.locator('.director-achievement-metric h3').all_text_contents() == [
                        'Conducted Activities', 'Verified Attendees', 'Campus Commitments']
                    assert page.locator('.metric-tile,.staff-annual,.staff-footer-links,[data-month-chart],[data-sex-chart],[data-campus-chart]').count() == 0
                    assert page.locator('.review-card').get_attribute('data-review-persisted') == 'false'
                    expect(page.locator('[data-review-chart] .main-svg').first).to_be_visible()
                    assert page.locator('.review-card-groups li').count() == 4
                    values = json.loads(page.locator('[data-review-chart]').get_attribute('data-chart-values'))
                    assert sum(group['total'] for group in values) == sum(int(v) for v in page.locator('.review-card-groups strong').all_text_contents())
                    assert 'Reviewed History' not in page.locator('.review-card').inner_text()
                    assert page.locator('.staff-agenda > li').count() == 5
                    assert 'Other Campus Must Stay Hidden' not in page.locator('.staff-overview').inner_text()
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (enabled, width)
                    schedule = page.locator('[data-tour-id=activity-workspace]').bounding_box()
                    review = page.locator('.review-card').bounding_box()
                    if width >= 1280:
                        assert abs(schedule['y'] - review['y']) < 2
                        assert schedule['width'] > review['width']
                    else:
                        assert review['y'] >= schedule['y'] + schedule['height']
                    for link in page.locator('.review-card a,.staff-agenda a').all():
                        assert link.bounding_box()['height'] >= 44, link.inner_text()
                    tiles = page.locator('.director-achievement-metric').evaluate_all('els=>els.map(el=>({y:el.offsetTop,w:el.offsetWidth}))')
                    if width >= 1024:
                        assert len({tile['y'] for tile in tiles}) == 1
                    elif width >= 480:
                        assert tiles[0]['y'] == tiles[1]['y'] and tiles[2]['w'] > tiles[0]['w']
                    else:
                        assert len({tile['y'] for tile in tiles}) == 3
                    page.screenshot(path=str(out / f'overview-{enabled}-{width}.png'), full_page=True)
                    checks.append([enabled, width, '130%, four generated categories, five schedule entries, responsive layout'])

            page.set_viewport_size(dict(width=1440, height=1000))
            for year, rate in ((2023, '0%'), (2024, '100%'), (2025, '130%')):
                page.goto(base + f'/workspace/overview?year={year}&period=all')
                assert rate in page.locator('.director-achievement-label strong').inner_text()
            page.goto(base + '/workspace/overview?year=1900')
            assert '%' not in page.locator('.director-achievement-label strong').inner_text()
            checks.append('Zero, met, exceeded and no-commitment achievement states')

            for period, segment in (('annual', 1), ('semiannual', 2), ('quarterly', 2), ('custom', 1), ('all', 1)):
                page.goto(base + path)
                page.select_option('[name=period]', period)
                if period in ('semiannual', 'quarterly'):
                    page.select_option('[name=segment]', str(segment))
                if period == 'custom':
                    page.fill('[name=start_date]', '2025-01-01')
                    page.fill('[name=end_date]', '2025-12-31')
                page.locator('[data-overview-scope] button').click()
                page.wait_for_load_state('networkidle')
                assert '130%' in page.locator('.director-achievement-label strong').inner_text()
                assert page.locator('.staff-agenda > li').count() == 5
            checks.append('Five native period submissions preserve annual achievement and agenda')

            page.goto(base + path + '&campus_id=2&campus=2&sex=female')
            assert '130%' in page.locator('.director-achievement-label strong').inner_text()
            assert 'Other Campus Must Stay Hidden' not in page.locator('.staff-overview').inner_text()
            page.locator('.review-card-groups a').first.focus()
            assert page.locator('.review-card-groups a').first.evaluate('el=>getComputedStyle(el).outlineStyle') != 'none'
            page.keyboard.press('Enter')
            page.wait_for_url('**/workspace/follow-up**')
            checks.append('Forged campus scope cannot change campus achievement; keyboard queue navigation')

            page.goto(base + path + '&activity_name=NoMatch')
            expect(page.locator('.review-empty')).to_be_visible()
            assert 'No generated findings' in page.locator('.director-review-next').inner_text()
            assert '130%' in page.locator('.director-achievement-label strong').inner_text()
            checks.append('No-findings state retains annual achievement and factual next action')

            page.goto(base + path)
            categories = page.locator('.review-card-groups li').evaluate_all('els=>els.map(el=>({href:el.querySelector("a").getAttribute("href"),count:el.querySelector("strong").textContent}))')
            for category in categories:
                assert page.goto(base + category['href']).status == 200
                expect(page.locator('.section-top h2')).to_have_text(category['count'] + ' Follow-up Findings')
            checks.append('Every category count matches its filtered Coordinator queue')

            page.goto(base + path)
            links = page.locator('.staff-overview a:not([data-guide-replay])').evaluate_all('els=>els.map(el=>el.getAttribute("href"))')
            for href in dict.fromkeys(links):
                assert page.goto(base + href).status == 200, href
                page.wait_for_load_state('networkidle')
            checks.append(f'{len(set(links))} distinct Overview destinations opened')
            page.goto(base + path + '&tour=1')
            expect(page.locator('.first-use-tour')).to_be_visible()
            guide_titles = []
            while page.get_by_role('button', name='Next', exact=True).is_visible():
                guide_titles.append(page.locator('#tourTitle').inner_text())
                page.get_by_role('button', name='Next', exact=True).click()
            guide_titles.append(page.locator('#tourTitle').inner_text())
            assert guide_titles == ['Choose Your Reporting Scope', 'Track Campus AOP Achievement',
                'Review Delivery and Commitments', 'Start with an Approved Proposal',
                'Follow Your Campus Schedule', 'Review Campus Findings']
            page.get_by_role('button', name='Finish', exact=True).click()
            expect(page.locator('.first-use-tour')).not_to_be_visible()
            checks.append('Coordinator guide completed')

            with app.app_context():
                db.session.get(Campus, 1).name = 'Synthetic Long Campus Name ' * 8
                for event in Event.query.filter_by(campus_id=1).all():
                    if event.date.year == local_now().year:
                        event.date = datetime(2020, 6, 1)
                        event.end_date = datetime(2020, 6, 2)
                db.session.commit()
            page.set_viewport_size(dict(width=320, height=1000))
            page.goto(base + path)
            page.evaluate("document.documentElement.style.fontSize='32px'")
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
            page.screenshot(path=str(out / 'enlarged-text.png'), full_page=True)
            page.evaluate("document.documentElement.style.fontSize=''")
            assert page.locator('.staff-agenda > li').count() == 1
            assert 'No upcoming approved activities' in page.locator('.staff-agenda').inner_text()
            checks.append('Long campus name, doubled root text and empty agenda')

            for javascript in (True, False):
                fallback = browser.new_context(java_script_enabled=javascript, viewport=dict(width=390, height=1000))
                fallback.add_cookies([dict(name='session', value=cookie, url=base)])
                view = fallback.new_page()
                if javascript:
                    view.route('**/plotly-5.24.1.min.js', lambda route: route.abort())
                assert view.goto(base + path).status == 200
                view.wait_for_load_state('networkidle')
                assert '130%' in view.locator('.director-achievement-label strong').inner_text()
                assert view.locator('.review-card-groups a').count() == 4
                assert not view.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                fallback.close()
            checks.append('Blocked chart library and JavaScript-disabled exact values and actions')
            browser.close()
        assert not errors, errors
        print(f'{len(checks)} Coordinator browser groups passed; {len(templates)} templates parsed; {out}')
    finally:
        (out / 'results.json').write_text(json.dumps(dict(checks=checks, errors=errors), indent=2), encoding='utf-8')
        server.shutdown()


if __name__ == '__main__':
    main()
