"""Disposable role fixtures for Help and header layout/interaction verification."""
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');parser.add_argument('--output-root',default='.qa-overhaul-temp/help-header');args=parser.parse_args()
    out=Path(args.output_root)/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR);cookies={};checks=[];errors=[]
    if 'refined-header' in args.output_root:
        from flask import render_template_string
        from flask_login import login_required
        @app.route('/qa-header-actions')
        @login_required
        def qa_header_actions():
            return render_template_string('''{% extends 'layouts/role_base.html' %}
                {% block header_title %}A Long Workspace Title for Layout Verification{% endblock %}
                {% block header_subtitle %}A Long Campus Context for Layout Verification{% endblock %}
                {% block header_actions %}<a class="btn btn--primary" href="{{ url_for('workspace.draft_list') }}">Open Saved Drafts</a>{% endblock %}
                {% block content %}<h1>Disposable Header Fixture</h1>{% for n in range(15) %}<p class="my-8">Layout verification {{ n }}.</p>{% endfor %}{% endblock %}''',unread_notifications=3)
    with app.app_context():
        for role in ['volunteer','coordinator','director']:
            user=User(name='Authored '+role,email=f'header-{role}@example.org',role=role,campus_id=1,
                sex='prefer_not_to_say',password_hash='unused',first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user);db.session.flush()
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for role in ['public','volunteer','coordinator','director']:
                context=browser.new_context(has_touch=True,reduced_motion='reduce')
                if role!='public':context.add_cookies([dict(name='session',value=cookies[role],url=base)])
                page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                    page.set_viewport_size(dict(width=width,height=height))
                    response=page.goto(base+'/help');page.wait_for_load_state('networkidle');assert response.status==200
                    if width in [1440,390]:page.screenshot(path=str(out/f'{role}-{width}.png'),full_page=True)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,width)
                    if args.stage=='after' and role!='public':
                        page.evaluate('window.scrollTo(0,600)')
                        assert abs(page.locator('.role-topbar').bounding_box()['y'])<2
                    checks.append([role,width,height])
                if args.stage=='after':
                    slug={'public':'account-access','volunteer':'withdrawal','coordinator':'attendance','director':'imports'}[role]
                    for width in [1440,390]:
                        page.set_viewport_size(dict(width=width,height=900))
                        response=page.goto(base+f'/help/{slug}?q=account');assert response.status==200
                        page.screenshot(path=str(out/f'{role}-article-{width}.png'),full_page=True)
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    page.get_by_role('link',name='Back to Help',exact=True).click()
                    assert 'q=account' in page.url
                    page.locator('[name=q]').fill('unfindable <script>literal</script>');page.locator('[name=q]').press('Enter')
                    page.get_by_role('heading',name='No Matching Help Topics',exact=True).wait_for()
                    page.get_by_role('link',name='Browse All Help',exact=True).click()
                    checks.append([role,'article, search, empty, preserved Back'])
                    if role!='public':
                        page.set_viewport_size(dict(width=390,height=844))
                        page.evaluate('window.scrollTo(0,650)')
                        toggle=page.get_by_role('button',name='Open Navigation',exact=True);toggle.click()
                        assert page.locator('.role-shell').evaluate('e=>e.inert')
                        page.keyboard.press('Tab');assert page.evaluate("document.querySelector('.role-sidebar').contains(document.activeElement)")
                        page.keyboard.press('Escape');assert toggle.evaluate('e=>e===document.activeElement')
                        page.goto(base+'/help/saved-drafts#steps')
                        page.wait_for_load_state('networkidle')
                        assert page.locator('#steps').bounding_box()['y']>=page.locator('.role-topbar').bounding_box()['height']-1
                        page.evaluate("document.documentElement.style.fontSize='200%';document.querySelector('.role-topbar__title strong').textContent='A long page title that wraps at narrow screen widths';document.querySelector('.role-topbar__title span').textContent='A long campus name for the university workspace'")
                        page.screenshot(path=str(out/f'{role}-200.png'),full_page=True)
                        header=page.locator('.role-topbar').bounding_box()
                        offset=page.evaluate("parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--role-header-height'))")
                        assert abs(header['height']-offset)<2
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                        page.goto(base+'/help');page.get_by_role('link',name='Show Dashboard Guide',exact=True).click()
                        page.locator('dialog.first-use-tour[open]').wait_for()
                        page.keyboard.press('Escape');assert not page.locator('dialog.first-use-tour').is_visible()
                        paths=(['/volunteer_dash','/workspace/registrations'] if role=='volunteer' else
                            ['/workspace/overview','/workspace/reports/results','/workspace/partners','/workspace/create/1'] if role=='coordinator' else
                            ['/workspace/overview','/workspace/reports/results','/admin_dash','/admin/users/create'])
                        page.set_viewport_size(dict(width=1440,height=800))
                        for path in paths:
                            response=page.goto(base+path);assert response.status==200,(role,path,response.status)
                            page.evaluate('window.scrollTo(0,600)')
                            page.screenshot(path=str(out/f'{role}-{path.rsplit("/",1)[-1]}-scrolled.png'),full_page=True)
                            assert abs(page.locator('.role-topbar').bounding_box()['y'])<2
                        if role!='volunteer':
                            page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/workspace/overview')
                            tip=page.locator('.info-tip').first
                            tip.locator('summary').focus();page.keyboard.press('Enter')
                            assert tip.evaluate('e=>e.open')
                            content=tip.locator('.info-tip__content').bounding_box()
                            assert content['x']>=-1 and content['x']+content['width']<=391
                            page.get_by_role('button',name='Open Navigation',exact=True).click()
                            assert not tip.evaluate('e=>e.open')
                            page.keyboard.press('Escape')
                        if role in ['coordinator','director']:
                            form_path='/workspace/partners/new' if role=='coordinator' else '/admin/users/create'
                            page.goto(base+form_path)
                            with page.expect_navigation():
                                page.locator('form.panel[method=post]').evaluate('form=>form.submit()')
                            summary=page.locator('[data-form-errors]');summary.wait_for()
                            assert summary.evaluate('e=>e===document.activeElement')
                            assert summary.bounding_box()['y']>=page.locator('.role-topbar').bounding_box()['height']-1
                            page.locator('[name=name]').evaluate("e=>{e.scrollIntoView({block:'start'});e.focus()}")
                            assert page.locator('[name=name]').bounding_box()['y']>=page.locator('.role-topbar').bounding_box()['height']-1
                        page.goto(base+'/help')
                        idle=page.locator('#session-idle')
                        if idle.count():
                            idle.evaluate('dialog=>dialog.showModal()')
                            assert idle.evaluate("d=>d.matches(':modal')")
                            page.get_by_role('button',name='Stay Signed In',exact=True).click()
                            idle.wait_for(state='hidden')
                        page.goto(base+f'/help/{slug}');page.emulate_media(media='print')
                        assert not page.locator('.role-topbar').is_visible()
                        page.screenshot(path=str(out/f'{role}-print.png'),full_page=True)
                        checks.append([role,'drawer, Escape/focus, anchor, 200%, guide, representative screens, print'])
                        if 'refined-header' in args.output_root:
                            page.emulate_media(media='screen')
                            for width in [1440,768,390,320,844]:
                                page.set_viewport_size(dict(width=width,height=800))
                                page.goto(base+'/qa-header-actions');page.wait_for_load_state('networkidle')
                                page.screenshot(path=str(out/f'{role}-actions-{width}.png'),full_page=True)
                                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,width,'extra actions')
                                notification=page.locator('.notification-bell')
                                assert notification.bounding_box()['width']>=44 and notification.bounding_box()['height']>=44
                                assert notification.locator('.notification-badge').inner_text()=='3'
                                label=notification.locator('.role-topbar__notification-label')
                                assert label.is_visible()==(width>=1024)
                                assert page.get_by_role('link',name='Open Saved Drafts',exact=True).is_visible()
                            page.evaluate("document.documentElement.style.fontSize='200%'")
                            page.set_viewport_size(dict(width=320,height=800))
                            page.screenshot(path=str(out/f'{role}-actions-200.png'),full_page=True)
                            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                            checks.append([role,'unread badge, extra actions, long labels, 200%'])
                context.close()
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} Help/header checks passed: {out}')


if __name__=='__main__':main()
