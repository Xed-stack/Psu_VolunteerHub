"""Exercise the overhaul in Chromium against a disposable in-memory app."""
import json
import logging
import sys
from pathlib import Path
from threading import Thread
from datetime import datetime, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = create_app('testing')
    artifact = Path('.qa-overhaul-temp/browser')
    artifact.mkdir(parents=True, exist_ok=True)
    app.config['PRIVATE_UPLOAD_FOLDER'] = str((artifact / 'uploads').resolve())
    with app.app_context():
        actors = {}
        for role in ('director', 'coordinator', 'volunteer'):
            user = User.query.filter_by(role=role).first()
            if not user:
                user = User(name=role.title(), email=role+'@example.org', role=role, campus_id=1, password_hash='unused')
                db.session.add(user)
            user.sex = 'prefer_not_to_say'
            user.first_use_guide_dismissed_at = datetime.utcnow()
            db.session.flush()
            actors[role] = app.session_interface.get_signing_serializer(app).dumps(
                dict(_user_id=str(user.id), _fresh=True, auth_version=user.auth_version))
        event = Event.query.first()
        event.date = local_now() - timedelta(hours=1)
        event.end_date = local_now() + timedelta(hours=2)
        event_id = event.id
        from app.models.workspace import FormDraft
        coordinator = User.query.filter_by(role='coordinator').first()
        proposal_folder = Path(app.config['PRIVATE_UPLOAD_FOLDER']) / 'proposals'
        proposal_folder.mkdir(parents=True, exist_ok=True)
        (proposal_folder / 'qa.pdf').write_bytes(b'%PDF-1.4\n% QA placeholder document')
        db.session.add(FormDraft(user_id=coordinator.id, campus_id=coordinator.campus_id, key='activity:new',
            payload={'_proposal': {'path':'qa.pdf','name':'QA approved proposal.pdf','readable':False}}))
        for index, historical in enumerate(Event.query.filter(Event.id != event_id).all()):
            historical.date = local_now() - timedelta(days=14 + index * 7)
            historical.end_date = historical.date + timedelta(hours=2)
        from app.models.annual_plan import AnnualPlan, AnnualIndicator, AnnualTarget, AnnualResult
        plan = AnnualPlan(source_key='qa-plan', year=local_now().year, plan_type='AOP', title='QA example plan',
                          source_document='Disposable browser fixture; not institutional evidence')
        indicator = AnnualIndicator(source_key='qa-indicator', plan=plan, code='QA-1', program='QA example',
            name='QA example target', unit='activities', responsible_office='QA only', evidence_basis='approved_aggregate')
        target = AnnualTarget(source_key='qa-target', indicator=indicator, campus_id=1, target_value=4)
        result = AnnualResult(source_key='qa-result', target=target, actual_value=5, evidence_status='verified',
            result_type='approved_aggregate', source_document='Disposable QA fixture', coverage_note='QA only',
            coverage_end=local_now().date()-timedelta(days=1))
        db.session.add_all([plan, indicator, target, result])
        db.session.commit()
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            scenarios = {
                'public': ['/', '/auth/login', '/auth/interests', '/workspace/about', '/help', '/opportunities'],
                'director': ['/workspace/overview', '/workspace/reports', '/workspace/reports/results', '/workspace/reports/aop', '/workspace/reports/historical', '/workspace/imports', '/admin_dash', '/settings', '/workspace/management', '/workspace/volunteers', '/director/calendar', '/workspace/follow-up', '/workspace/campuses/1', '/workspace/recognition', '/workspace/reports/people'],
                'coordinator': ['/workspace/overview', '/workspace/activities', f'/workspace/activities/{event_id}', '/workspace/create/1', '/workspace/create/2', '/workspace/create/3', '/workspace/create/4', '/workspace/partners', '/workspace/reports/historical', f'/workspace/activities/{event_id}/registrations', f'/attendance?event_id={event_id}', f'/workspace/activities/{event_id}/external', f'/workspace/activities/{event_id}/documents', '/coordinator/calendar', '/workspace/follow-up', '/workspace/reports/people'],
                'volunteer': ['/volunteer_dash', '/workspace/registrations', '/profile', '/profile?section=preferences', '/profile?section=impact', '/opportunities']
            }
            if '--draft-only' in sys.argv:
                scenarios = {'coordinator': ['/workspace/partners']}
            if '--guidance-only' in sys.argv or '--polish-only' in sys.argv:
                scenarios = {}
            if '--showcase-only' in sys.argv:
                scenarios={'public':['/','/auth/login'],'director':['/workspace/overview','/workspace/reports/results','/workspace/recognition'],
                    'coordinator':['/workspace/overview','/workspace/activities','/workspace/create/3','/annual-goals/workspace'],
                    'volunteer':['/volunteer_dash','/profile','/workspace/registrations']}
            for role, paths in scenarios.items():
                context = browser.new_context()
                if role != 'public':
                    context.add_cookies([dict(name='session', value=actors[role], url=base)])
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                for width in ((1440,390) if '--showcase-only' in sys.argv else (1440,1024,768,390,320)):
                    page.set_viewport_size(dict(width=width, height=1000))
                    for path in paths:
                        result = page.goto(base+path)
                        page.wait_for_timeout(100)
                        assert result.status == 200, (role, width, path, result.status)
                        overflow = page.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                        if overflow:
                            offenders = page.evaluate('''[...document.querySelectorAll('body *')].filter(el => {
                              const r=el.getBoundingClientRect(); return r.width && r.right>innerWidth+1 && !el.closest('.overflow-x-auto,.table-scroll,.calendar-grid');
                            }).slice(0,8).map(el=>({tag:el.tagName,cls:el.className,right:el.getBoundingClientRect().right}))''')
                            raise AssertionError((role,width,path,'overflow',offenders))
                        checks.append([role,width,path])
                        if width in (1440,390) and ('--showcase-only' in sys.argv or path in ('/','/workspace/overview','/auth/login','/workspace/create/1','/profile','/volunteer_dash')):
                            page.screenshot(path=str(artifact / f'{role}-{width}-{path.strip("/").replace("/","-") or "home"}.png'), full_page=True)
                if role == 'coordinator':
                    page.goto(base+'/workspace/partners')
                    page.locator('input[name=name]').fill('Refresh retained agency')
                    page.wait_for_function("document.body.textContent.includes('Draft saved')")
                    page.reload()
                    page.wait_for_function("document.querySelector('input[name=name]').value === 'Refresh retained agency'")
                    checks.append(['draft','refresh restored'])
                    page.locator('input[name=contact_name]').fill('QA contact')
                    draft_key = page.locator('form').filter(has=page.locator('input[name=contact_name]')).locator('input[name=_draft_key]').input_value()
                    page.get_by_role('button', name='Save Agency', exact=True).click()
                    page.wait_for_url('**/workspace/partners/*')
                    page.wait_for_timeout(800)
                    from urllib.parse import quote
                    draft = page.request.get(base+'/workspace/drafts/'+quote(draft_key, safe='')).json()
                    assert draft['payload'] == {}, draft
                    checks.append(['draft','submission cleared without recreation'])
                if role != 'public':
                    page.set_viewport_size(dict(width=390,height=900))
                    page.goto(base+paths[0])
                    toggle = page.locator('[data-sidebar-toggle]').first
                    toggle.focus()
                    assert toggle.evaluate('el=>el.matches(":focus-visible")')
                    toggle.press('Enter')
                    assert page.locator('#roleSidebar').evaluate('el=>!el.inert')
                    page.keyboard.press('Escape')
                    assert page.locator('#roleSidebar').evaluate('el=>el.inert')
                    checks.append([role,'keyboard drawer'])
                if role == 'director':
                    page.set_viewport_size(dict(width=1440,height=1000))
                    page.goto(base+'/workspace/reports/results')
                    page.emulate_media(media='print')
                    assert not page.locator('.role-sidebar').is_visible()
                    page.pdf(path=str(artifact/'activity-print.pdf'),format='A4',landscape=True,print_background=True)
                    page.emulate_media(media='screen')
                    for report in ('activity','aop'):
                        response = page.request.get(base+'/workspace/reports/export/pdf'+('?report=aop' if report == 'aop' else ''))
                        assert response.status == 200
                        content = response.body()
                        from pypdf import PdfReader
                        import io
                        document = PdfReader(io.BytesIO(content))
                        assert document.pages and 'PSU' in document.pages[0].extract_text()
                        (artifact/(report+'-export.pdf')).write_bytes(content)
                        checks.append([report,'PDF contents and print output'])
                page.set_viewport_size(dict(width=1440,height=1000))
                page.goto(base+paths[0])
                page.add_style_tag(content='html { font-size: 200%; }')
                page.wait_for_timeout(400)
                offenders = page.evaluate('''[...document.querySelectorAll('body *')].filter(el=>{
                  const r=el.getBoundingClientRect();return r.width && r.right>innerWidth+1 && !el.closest('.overflow-x-auto,.table-scroll');
                }).slice(0,8).map(el=>({tag:el.tagName,cls:el.getAttribute('class'),right:el.getBoundingClientRect().right}))''')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (role,'200% text size',offenders)
                checks.append([role,'200% text size'])
                context.close()
            if '--draft-only' not in sys.argv and '--showcase-only' not in sys.argv:
                with app.app_context():
                    for index in range(21):
                        db.session.add(Event(title=f'QA search 100%_activity {index:02}',description='Disposable search fixture',
                            date=local_now()+timedelta(days=3+index),end_date=local_now()+timedelta(days=3+index,hours=2),
                            campus_id=1,category='Education & Literacy',slots=20,lifecycle_status='approved'))
                    db.session.commit()
                context = browser.new_context(viewport=dict(width=390,height=844))
                context.add_cookies([dict(name='session',value=actors['coordinator'],url=base)])
                page = context.new_page()
                page.on('pageerror',lambda error: errors.append(str(error)))
                page.goto(base+'/workspace/activities')
                page.locator('input[name=q]').fill('100%_activity')
                page.locator('input[name=q]').press('Enter')
                assert page.locator('mark').count() == 15
                page.locator('a[rel=next]').click()
                assert 'page=2' in page.url and page.locator('mark').count() == 6
                page.locator('.activity-list h2 a').first.click()
                page.get_by_role('navigation',name='Activity Workspace',exact=True).get_by_role('link',name='Attendance',exact=True).click()
                assert page.locator('input[name=volunteer_search]').count() == 0
                page.get_by_role('link',name='Back to Activity',exact=True).click()
                page.get_by_role('link',name='Back to Activities',exact=True).click()
                assert 'page=2' in page.url and page.locator('input[name=q]').input_value() == '100%_activity'
                page.get_by_role('link',name='Remove Search:',exact=False).click()
                assert 'page=' not in page.url and 'q=' not in page.url
                page.locator('[data-more-filters] > summary').click()
                page.locator('select[name=category]').select_option('Education & Literacy')
                page.locator('input[name=q]').fill('100%_activity')
                page.get_by_role('button',name='Apply Filters',exact=True).click()
                page.get_by_role('link',name='Remove Category:',exact=False).click()
                assert page.locator('input[name=q]').input_value() == '100%_activity'
                page.screenshot(path=str(artifact/'coordinator-390-filtered-search.png'),full_page=True)
                page.get_by_role('link',name='Clear All Filters',exact=True).click()
                page.locator('input[name=q]').fill('<unfindable>')
                page.locator('input[name=q]').press('Enter')
                assert page.get_by_role('heading',name='No Matching Activities').is_visible()
                assert '“<unfindable>”' in page.locator('.search-empty').inner_text()
                page.get_by_role('link',name='Clear Search and Filters',exact=True).click()
                checks.append(['search','Enter, literal highlights, pagination, nested Back context, chips, reset, empty recovery'])
                page.goto(base+'/workspace/partners')
                page.get_by_role('button',name='Save Agency',exact=True).click()
                assert page.locator('[data-validation-summary] li').count() == 2
                page.locator('input[name=name]').fill('Native validation QA')
                assert page.locator('[data-validation-summary] li').count() == 1
                page.locator('[data-validation-summary] a').click()
                assert page.locator('input[name=contact_name]').evaluate('el=>el===document.activeElement')
                def fail_draft(route):
                    if route.request.method == 'PUT': route.fulfill(status=503,body='Unavailable')
                    else: route.continue_()
                page.route('**/workspace/drafts/**',fail_draft)
                page.locator('input[name=contact_name]').fill('Save failure QA')
                page.wait_for_function("document.body.textContent.includes('Draft could not be saved')")
                page.unroute('**/workspace/drafts/**',fail_draft)
                page.locator('input[name=contact_name]').fill('Save recovered QA')
                page.wait_for_function("document.body.textContent.includes('Draft saved')")
                from urllib.parse import quote
                page.goto(base+'/workspace/partners?return_to='+quote('/workspace/activities?q='+'x'*220,safe=''))
                page.locator('input[name=name]').fill('Long-context retained draft')
                page.wait_for_function("document.body.textContent.includes('Draft saved')")
                assert len(page.locator('input[name=_draft_key]').input_value()) <= 160
                page.reload()
                page.wait_for_function("document.querySelector('input[name=name]').value === 'Long-context retained draft'")
                checks.append(['forms','long Back context keeps a restorable draft key'])
                checks.append(['forms','linked native validation, inline errors, failed draft save and recovery'])
                context.close()
                for role in ('director', 'coordinator', 'volunteer'):
                    dashboard = '/volunteer_dash' if role == 'volunteer' else '/workspace/overview'
                    for width in (1440, 390, 320):
                        with app.app_context():
                            user = User.query.filter_by(role=role).first()
                            user.first_use_guide_dismissed_at = None
                            db.session.commit()
                        context = browser.new_context(viewport=dict(width=width,height=800), has_touch=True,
                                                      reduced_motion='reduce')
                        context.add_cookies([dict(name='session', value=actors[role], url=base)])
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.goto(base+dashboard)
                        guide = page.locator('dialog.first-use-tour')
                        guide.wait_for(state='visible')
                        if width == 320:
                            page.add_style_tag(content='html {font-size:200%}')
                        assert page.locator('[data-tour-next]').evaluate('el => el === document.activeElement')
                        page.locator('[data-tour-next]').click()
                        page.locator('[data-tour-back]').click()
                        assert 'Step 1' in guide.inner_text()
                        if width == 320:
                            assert page.locator('.first-use-tour__card').evaluate('el=>el.scrollTop') == 0
                        box = page.locator('.first-use-tour__card').bounding_box()
                        assert box['x'] >= 0 and box['x']+box['width'] <= width+1
                        page.screenshot(path=str(artifact/f'{role}-{width}-guide.png'))
                        if width == 1440:
                            page.route('**/guide/dismiss',lambda route: route.fulfill(status=503,body='Unavailable'))
                            page.locator('[data-tour-skip]').click()
                            page.wait_for_function("document.querySelector('#tourText').textContent.includes('could not be saved')")
                            assert guide.is_visible()
                            page.unroute('**/guide/dismiss')
                        page.keyboard.press('Escape')
                        guide.wait_for(state='hidden')
                        assert page.evaluate('document.activeElement !== document.body')
                        with app.app_context():
                            saved = User.query.filter_by(role=role).first().first_use_guide_dismissed_at
                            assert saved is not None
                        page.reload()
                        assert page.locator('dialog.first-use-tour').count() == 0
                        page.locator('[data-guide-replay]').click()
                        guide.wait_for(state='visible')
                        while page.locator('[data-tour-next]').inner_text() != 'Finish':
                            page.locator('[data-tour-next]').click()
                        page.locator('[data-tour-next]').click()
                        guide.wait_for(state='hidden')
                        assert page.locator('[data-guide-replay]').evaluate('el => el === document.activeElement')
                        assert '?tour=' not in page.url
                        with app.app_context():
                            assert User.query.filter_by(role=role).first().first_use_guide_dismissed_at == saved
                        checks.append([role,width,'first use, saved dismissal, replay, Back, Next, Finish, Escape and focus'])
                        if role != 'volunteer':
                            trigger = page.locator('.metric-tile .info-tip summary').last
                            trigger.focus()
                            trigger.press('Enter')
                            content = page.locator('.metric-tile .info-tip[open] .info-tip__content')
                            assert content.is_visible()
                            rect = content.bounding_box()
                            assert rect['x'] >= 0 and rect['x']+rect['width'] <= width+1
                            assert rect['y'] >= 0 and rect['y']+rect['height'] <= 801
                            trigger.press('Escape')
                            assert trigger.evaluate('el => el === document.activeElement'), page.evaluate('document.activeElement.outerHTML')
                            assert not content.is_visible()
                            trigger.tap()
                            assert content.is_visible()
                            page.locator('main h1').first.tap()
                            assert not content.is_visible()
                            checks.append([role,width,'information tips: keyboard, Escape, touch, outside close, viewport'])
                        if width == 390:
                            more=page.get_by_role('button',name='More Navigation',exact=True)
                            more.focus(); more.press('Enter')
                            assert page.locator('#roleSidebar').evaluate('el=>!el.inert')
                            page.keyboard.press('Escape')
                            assert more.evaluate('el=>el===document.activeElement')
                            checks.append([role,'mobile More Navigation and focus restoration'])
                        context.close()
                context = browser.new_context(viewport=dict(width=844,height=390),has_touch=True)
                context.add_cookies([dict(name='session',value=actors['director'],url=base)])
                page = context.new_page()
                page.goto(base+'/workspace/overview?tour=1')
                page.locator('dialog.first-use-tour').wait_for(state='visible')
                page.locator('[data-tour-next]').click()
                page.locator('[data-tour-next]').click()
                page.keyboard.press('Escape')
                # A responsive change can remove a target between tour steps.
                page.goto(base+'/workspace/overview?tour=1')
                page.evaluate("document.querySelector('[data-tour-id=campus-comparison]').remove()")
                page.locator('[data-tour-next]').click()
                page.locator('[data-tour-next]').click()
                assert page.locator('#tourTitle').inner_text() == 'Review Annual Achievements'
                page.keyboard.press('Escape')
                checks.append(['guide','landscape, save failure recovery, missing target'])
                page.goto(base+'/admin_dash?search=volunteer')
                role_form = page.locator('form[action*="/admin/users/role/"]').filter(has=page.locator('select[name=role]')).first
                role_form.locator('select[name=role]').select_option('volunteer')
                role_form.get_by_role('button',name='Apply Role',exact=True).click()
                page.wait_for_url('**/admin_dash')
                assert 'role changed to volunteer' in page.locator('.flash-stack').inner_text()
                checks.append(['management','explicit native Apply Role submission'])
                context.close()
            browser.close()
        assert not errors, errors
        result_name = 'draft-results.json' if '--draft-only' in sys.argv else 'polish-results.json' if '--polish-only' in sys.argv else 'showcase-results.json' if '--showcase-only' in sys.argv else 'guidance-results.json' if '--guidance-only' in sys.argv else 'results.json'
        (artifact / result_name).write_text(json.dumps(dict(checks=checks, errors=errors),indent=2))
        print(f'{len(checks)} browser checks passed; no page overflow or JavaScript errors.')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
