"""Director AOP reference acceptance with disposable synthetic SQLite."""
import csv
import io
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
from app.models.annual_plan import AnnualGoalProposal, AnnualTarget
from app.report_demo import seed_aop_commitments
from app.services.aop_goals import publish
from flask_login import login_user
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    out = Path('.qa-overhaul-temp/director-aop-list').resolve()
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    app.config.update(WTF_CSRF_ENABLED=True, PRIVATE_UPLOAD_FOLDER=str(out/'private'))
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    checks, errors = [], []
    with app.app_context(), app.test_request_context():
        user = User.query.filter_by(role='director').first()
        user.first_use_guide_dismissed_at = datetime.utcnow()
        login_user(user)
        cookie = app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        events = [Event(title=f'Synthetic AOP {i}', description='Synthetic', campus_id=1,
            date=datetime(2025,6,1),end_date=datetime(2025,6,2),lifecycle_status='approved') for i in range(13)]
        db.session.add_all(events); db.session.flush()
        seed_aop_commitments(2025,Campus.query.all(),events)
        for index in range(11):
            payload = dict(year=2025,title=f'Synthetic Learning {index}',description='Literacy extension',
                target_value=2,start_date='2025-01-01',end_date='2025-12-31')
            proposal = AnnualGoalProposal(workflow_kind='director_goal', proposed_by_id=user.id,payload=payload)
            db.session.add(proposal);db.session.flush()
            publish(proposal,payload)
        db.session.add(AnnualGoalProposal(workflow_kind='director_goal',proposed_by_id=user.id,
            payload=dict(title='Synthetic Saved Draft',year=2025)))
        db.session.commit()
        templates = app.jinja_env.list_templates()
        for name in templates: app.jinja_env.get_template(name)
    server = make_server('127.0.0.1',0,app)
    Thread(target=server.serve_forever,daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    path = '/annual-goals?year=2025'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session',value=cookie,url=base)])
            page = context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width in (1440,1280,1024,768,390,320):
                page.set_viewport_size(dict(width=width,height=1000))
                assert page.goto(base+path).status==200
                page.wait_for_load_state('networkidle')
                assert page.locator('.aop-director-totals strong').all_text_contents()==['32','13','22','2']
                assert page.locator('.aop-deliverables-table tbody tr').count()==10
                assert page.locator('.aop-deliverables-table thead th').all_text_contents()==[
                    'Activity Title','Category','Campus Commitments','Director Baseline','Progress / Status']
                assert page.locator('.aop-category-unset').first.inner_text()=='Not Assigned'
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'), width
                page.get_by_text('View Campus Breakdown',exact=True).click()
                expect(page.locator('.aop-breakdown')).to_be_visible()
                for link in page.locator('.aop-director a:visible').all():
                    assert link.bounding_box()['height']>=44,link.inner_text()
                page.evaluate('document.activeElement.blur();window.scrollTo(0,0)')
                page.wait_for_function('scrollY === 0')
                page.screenshot(path=str(out/f'goals-{width}.png'),full_page=True)
                checks.append(f'{width}px: summary, ten rows, breakdown, targets and overflow')
            page.set_viewport_size(dict(width=1440,height=1000))
            page.goto(base+path)
            page.get_by_role('link',name='Next',exact=True).click()
            assert page.locator('.aop-deliverables-table tbody tr').count()==2
            page.fill('.aop-director-search [name=q]', 'Literacy')
            page.get_by_role('button',name='Apply Filters',exact=True).click()
            assert 'q=Literacy' in page.url and 'page=2' not in page.url
            page.get_by_role('link',name='Next',exact=True).click()
            assert page.locator('.aop-deliverables-table tbody tr').count()==1 and 'q=Literacy' in page.url
            checks.append('Search before pagination, query retention and page reset')
            page.goto(base+path)
            page.select_option('.aop-director-search [name=progress_status]','above')
            page.get_by_role('button',name='Apply Filters',exact=True).click()
            assert page.locator('.aop-deliverables-table tbody tr').count()==1
            assert '130%' in page.locator('.aop-deliverables-table').inner_text()
            page.locator('.aop-deliverables-table details summary').click()
            expect(page.locator('.aop-deliverables-table details ul')).to_be_visible()
            summary = page.locator('.aop-director-totals').inner_text()
            page.fill('.aop-director-search [name=q]','NoMatch')
            page.get_by_role('button',name='Apply Filters',exact=True).click()
            assert 'No goals match' in page.locator('.aop-list-empty').inner_text()
            assert page.locator('.aop-director-totals').inner_text()==summary
            page.get_by_role('link',name='Clear Table Filters',exact=True).click()
            checks.append('Above-target status, full campus disclosure, no results and stable summary')
            page.select_option('[name=campus]','2')
            page.get_by_role('button',name='Apply Scope',exact=True).click()
            assert page.locator('.aop-director-totals strong').all_text_contents()[:3]==['32','0','32']
            assert '0 / 10' in page.locator('.aop-deliverables-table').inner_text()
            response = context.request.get(base+path+'&q=Learning&export=csv')
            assert response.status==200 and len(list(csv.reader(io.StringIO(response.text()))))==13
            assert context.request.get(base+path+'&q=Learning&export=pdf').body().startswith(b'%PDF')
            checks.append('Campus contributions retain Director baseline; full filtered CSV/PDF')
            page.goto(base+path)
            hrefs=page.locator('.aop-director a:visible').evaluate_all('els=>els.map(el=>el.getAttribute("href"))')
            for href in dict.fromkeys(hrefs):
                if 'export=' not in href:
                    assert page.goto(base+href).status==200, href
            checks.append('Visible goal, creation, draft, history and pagination destinations')
            page.goto(base+path)
            page.get_by_role('link',name='Create Goal',exact=True).focus()
            assert page.get_by_role('link',name='Create Goal',exact=True).evaluate('el=>getComputedStyle(el).outlineStyle')!='none'
            page.keyboard.press('Enter');page.wait_for_url('**/annual-goals/proposals/new')
            page.goto(base+'/annual-goals?year=1900')
            assert page.locator('.aop-director-totals strong').all_text_contents()==['0','0','0','0']
            checks.append('Keyboard focus/creation and empty year')
            page.set_viewport_size(dict(width=320,height=1000))
            with app.app_context():
                goal=AnnualTarget.query.filter_by(workflow_kind='director_goal').order_by(AnnualTarget.id).first()
                goal.indicator.name=('Synthetic Long Coastal Rehabilitation Goal ' * 6)[:250]
                db.session.get(Campus,1).name=('Synthetic Long Campus Name ' * 4)[:95]
                db.session.commit()
            page.goto(base+path+'&progress_status=above')
            page.evaluate("document.documentElement.style.fontSize='32px'")
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out/'enlarged-text.png'),full_page=True)
            checks.append('Long authored goal/campus names and doubled text at 320px')
            native=browser.new_context(java_script_enabled=False,viewport=dict(width=390,height=1000))
            native.add_cookies([dict(name='session',value=cookie,url=base)])
            view=native.new_page();assert view.goto(base+path).status==200
            view.get_by_text('View Campus Breakdown',exact=True).click()
            expect(view.locator('.aop-breakdown')).to_be_visible()
            view.fill('.aop-director-search [name=q]','Learning');view.get_by_role('button',name='Apply Filters',exact=True).click()
            assert 'q=Learning' in view.url
            checks.append('JavaScript-disabled scope, search and native disclosure')
            browser.close()
        assert not errors,errors
        print(f'{len(checks)} Director AOP browser groups passed; {len(templates)} templates parsed; {out}')
    finally:
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8')
        server.shutdown()


if __name__=='__main__':main()
