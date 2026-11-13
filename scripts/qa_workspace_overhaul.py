"""Exercise the overhaul in Chromium against a disposable in-memory app."""
import json
import logging
import sys
from pathlib import Path
from threading import Thread
from datetime import timedelta
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
                'director': ['/workspace/overview', '/workspace/reports', '/workspace/reports/results', '/workspace/reports/aop', '/workspace/reports/historical', '/workspace/imports', '/admin_dash', '/settings', '/workspace/management', '/workspace/volunteers'],
                'coordinator': ['/workspace/overview', '/workspace/activities', f'/workspace/activities/{event_id}', '/workspace/create/1', '/workspace/create/2', '/workspace/create/3', '/workspace/create/4', '/workspace/partners', '/workspace/reports/historical', f'/workspace/activities/{event_id}/registrations', f'/attendance?event_id={event_id}', f'/workspace/activities/{event_id}/external', f'/workspace/activities/{event_id}/documents'],
                'volunteer': ['/volunteer_dash', '/workspace/registrations', '/profile', '/profile?section=preferences', '/profile?section=impact', '/opportunities']
            }
            if '--draft-only' in sys.argv:
                scenarios = {'coordinator': ['/workspace/partners']}
            for role, paths in scenarios.items():
                context = browser.new_context()
                if role != 'public':
                    context.add_cookies([dict(name='session', value=actors[role], url=base)])
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                for width in (1440, 1024, 768, 390, 320):
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
                        if width in (1440,390) and path in ('/','/workspace/overview','/auth/login','/workspace/create/1','/profile'):
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
                    page.get_by_role('button', name='Save agency', exact=True).click()
                    page.wait_for_url('**/workspace/partners/*')
                    page.wait_for_timeout(800)
                    from urllib.parse import quote
                    draft = page.request.get(base+'/workspace/drafts/'+quote(draft_key, safe='')).json()
                    assert draft['payload'] == {}, draft
                    checks.append(['draft','submission cleared without recreation'])
                if role != 'public':
                    page.set_viewport_size(dict(width=390,height=900))
                    page.goto(base+paths[0])
                    toggle = page.locator('[data-sidebar-toggle]')
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
            browser.close()
        assert not errors, errors
        result_name = 'draft-results.json' if '--draft-only' in sys.argv else 'results.json'
        (artifact / result_name).write_text(json.dumps(dict(checks=checks, errors=errors),indent=2))
        print(f'{len(checks)} browser checks passed; no page overflow or JavaScript errors.')
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
