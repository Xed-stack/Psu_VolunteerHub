"""Isolated Notifications and Saved Drafts layout and interaction checks."""
import argparse
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
from app.models.notification import Notification
from app.models.workspace import FormDraft
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['before', 'after'], default='after')
    args = parser.parse_args()
    out = Path('.qa-overhaul-temp/notifications-drafts') / args.stage
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        for role in ['volunteer', 'coordinator', 'director']:
            user = User(name='QA ' + role, email=role+'@inbox.test', role=role,
                        campus_id=1, sex='prefer_not_to_say',
                        first_use_guide_dismissed_at=datetime.utcnow())
            user.set_password('StrongPassword1!')
            db.session.add(user)
            db.session.flush()
            for i in range(28):
                db.session.add(Notification(user_id=user.id, title=f'Community outreach update {i+1}',
                    message='Review your activity schedule and the instructions provided by your campus coordinator. '
                            'This message stays readable when titles or instructions wrap across several lines.',
                    is_read=i % 3 == 0, created_at=datetime(2026, 11, 16, 4, 30)-timedelta(minutes=i)))
            keys = ['activity:new', 'form:/workspace/partners/new'] if role == 'coordinator' else ['form:/profile?section=preferences'] if role == 'volunteer' else ['form:/settings']
            for i, key in enumerate(keys):
                db.session.add(FormDraft(user_id=user.id, campus_id=1, key=key,
                    payload={}, updated_at=datetime(2026, 11, 16, 4, 30)-timedelta(minutes=i)))
        db.session.commit()
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for role in ['volunteer', 'coordinator', 'director']:
                context = browser.new_context(reduced_motion='reduce')
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(base+'/auth/login')
                page.locator('#identifier').fill(role+'@inbox.test')
                page.locator('#password').fill('StrongPassword1!')
                page.get_by_role('button', name='Sign In', exact=True).click()
                page.wait_for_load_state('networkidle')
                sizes = [(1440,1000),(390,844)] if args.stage == 'before' else [(1440,1000),(1024,768),(768,900),(390,844),(320,800),(844,390)]
                for path, name in [('/notifications','notifications'),('/workspace/drafts','drafts')]:
                    for w,h in sizes:
                        page.set_viewport_size(dict(width=w,height=h))
                        page.goto(base+path)
                        page.wait_for_load_state('networkidle')
                        page.screenshot(path=str(out/f'{role}-{name}-{w}.png'), full_page=True)
                        if w in (390,1440):
                            page.screenshot(path=str(out/f'{role}-{name}-{w}-viewport.png'))
                        if args.stage == 'after':
                            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1'), (role,name,w)
                            for el in page.locator('main a, main button').all():
                                if el.is_visible():
                                    assert el.bounding_box()['height'] >= 43, (role,name,w,el.inner_text())
                        checks.append([role,name,w,h])
                if args.stage == 'after':
                    exercise(page, context, base, out, role, checks)
                context.close()
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} browser groups passed: {out}')


def exercise(page, context, base, out, role, checks):
    page.set_viewport_size(dict(width=1440,height=1000))
    page.goto(base+'/notifications?view=all&page=2');page.wait_for_load_state('networkidle')
    page.locator('.inbox-row button').first.click();page.wait_for_load_state('networkidle')
    assert 'view=all' in page.url and 'page=2' in page.url
    page.get_by_role('link',name='Unread',exact=False).filter(has=page.locator('.inbox-count')).click()
    page.wait_for_load_state('networkidle')
    assert 'view=unread' in page.url and 'page=2' not in page.url
    assert page.locator('.inbox-state').all_text_contents()==['Unread']*page.locator('.inbox-row').count()
    assert page.locator('.draft-status').count()==0
    assert page.locator('.notification-badge').inner_text()==page.locator('.inbox-count').inner_text()
    selected=page.locator('.inbox-tabs a[aria-current=page]')
    selected.focus();page.keyboard.press('Tab')
    assert page.locator(':focus-visible').count()==1
    page.get_by_role('link',name='Notification Help',exact=True).click()
    assert '/help/notifications' in page.url
    page.go_back();page.wait_for_load_state('networkidle')
    assert 'view=unread' in page.url
    checks.append([role,'views, read return page, counts, focus, Help and Back'])

    # Native read forms and Resume still work when scripts are disabled.
    nojs=context.browser.new_context(java_script_enabled=False,storage_state=context.storage_state())
    np=nojs.new_page();np.goto(base+'/notifications?view=unread')
    np.locator('.inbox-row button').first.click();np.wait_for_load_state('networkidle')
    assert 'view=unread' in np.url
    np.goto(base+'/workspace/drafts');np.wait_for_load_state('networkidle')
    np.screenshot(path=str(out/f'{role}-nojs-drafts.png'))
    expect(np.locator('.inbox-notice')).to_be_visible()
    expect(np.locator('.inbox-notice')).to_contain_text('JavaScript is required to discard a draft.')
    assert np.locator('[data-discard-draft]').first.is_hidden()
    np.locator('.inbox-row a').first.click();assert '/workspace/drafts' not in np.url
    nojs.close();checks.append([role,'no-JavaScript read action and Resume'])

    for path,name in [('/notifications','notifications'),('/workspace/drafts','drafts')]:
        page.goto(base+path);page.wait_for_load_state('networkidle')
        page.set_viewport_size(dict(width=320,height=800))
        page.evaluate('document.documentElement.style.fontSize="200%"')
        page.locator('.inbox-row h2').first.evaluate('(el)=>el.textContent="Long activity name " + "CommunityCoordination".repeat(12)')
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(role,name,'200%')
        page.locator('.inbox-row button').first.focus()
        page.wait_for_function('''() => {
            const box=document.activeElement.getBoundingClientRect();
            const header=document.querySelector('.role-topbar').getBoundingClientRect();
            const nav=document.querySelector('.mobile-nav').getBoundingClientRect();
            return box.top >= header.bottom-1 && box.bottom <= nav.top+1;
        }''',timeout=3000)
        box=page.locator(':focus').bounding_box()
        top=page.locator('.role-topbar').bounding_box()
        assert box['y']>=top['height']-1
        page.screenshot(path=str(out/f'{role}-{name}-focus-check.png'))
        assert box['y']+box['height']<=page.locator('.mobile-nav').bounding_box()['y']+1,(role,name,box,page.locator('.mobile-nav').bounding_box())
        page.screenshot(path=str(out/f'{role}-{name}-200.png'))
        page.evaluate('document.documentElement.style.fontSize=""')
        page.emulate_media(media='print')
        assert not page.locator('.role-topbar').is_visible()
        assert page.locator('.inbox-row h2').first.is_visible()
        page.emulate_media(media='screen')
        checks.append([role,name,'200% long content, focus and print'])

    page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/workspace/drafts')
    page.wait_for_load_state('networkidle')
    before=page.locator('[data-draft-row]').count()
    discard=page.locator('[data-discard-draft]').first
    page.once('dialog',lambda dialog:dialog.dismiss());discard.click()
    assert page.locator('[data-draft-row]').count()==before
    failures=[]
    def fail_delete(route):
        if route.request.method=='DELETE':
            assert discard.is_disabled() and discard.get_attribute('aria-busy')=='true'
            failures.append(route.request.url)
            route.fulfill(status=503,body='Temporary failure')
        else:route.continue_()
    page.route('**/workspace/drafts/**',fail_delete)
    page.once('dialog',lambda dialog:dialog.accept());discard.click()
    expect(page.locator('[data-discard-status]').first).to_contain_text('could not be discarded')
    expect(discard).to_be_enabled()
    assert page.locator('[data-draft-row]').count()==before and len(failures)==1
    page.screenshot(path=str(out/f'{role}-discard-failure.png'))
    page.unroute('**/workspace/drafts/**',fail_delete)
    page.once('dialog',lambda dialog:dialog.accept());discard.click();page.wait_for_load_state('networkidle')
    expect(page.locator('[data-draft-row]')).to_have_count(before-1)
    while page.locator('[data-discard-draft]').count():
        page.once('dialog',lambda dialog:dialog.accept())
        page.locator('[data-discard-draft]').first.click();page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='No Saved Drafts',exact=True)).to_be_visible()
    page.screenshot(path=str(out/f'{role}-drafts-empty.png'))
    checks.append([role,'discard cancellation, pending guard, failure, retry and empty state'])
    page.goto(base+'/notifications?view=unread')
    page.get_by_role('button',name='Mark All as Read',exact=True).click();page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='You’re All Caught Up',exact=True)).to_be_visible()
    assert page.locator('.inbox-count').inner_text()=='0'
    assert page.locator('.notification-badge').count()==0
    page.screenshot(path=str(out/f'{role}-unread-empty.png'))
    page.get_by_role('link',name='View All Notifications',exact=True).click()
    assert page.locator('.inbox-row').count()==25
    checks.append([role,'mark all, unread empty state and full history'])


if __name__ == '__main__':
    main()
