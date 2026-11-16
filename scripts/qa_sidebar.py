"""Role-specific sidebar captures and native drawer interaction checks."""
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
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/sidebar')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR)
    roles={'volunteer':('/profile','Profile'),'coordinator':('/workspace/activities','Activities'),'director':('/workspace/catalogue','Management')}
    with app.app_context():
        for role in roles:
            user=User(name='María O’Reyes-Santos — Student Volunteer' if role=='volunteer' else 'QA '+role,email=role+'@sidebar.test',role=role,campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
            user.set_password('StrongPassword1!');db.session.add(user)
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            for role,(path,active) in roles.items():
                context=browser.new_context(reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(base+'/auth/login');page.locator('#identifier').fill(role+'@sidebar.test');page.locator('#password').fill('StrongPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
                sizes=[(1440,1000),(390,844)] if args.stage=='before' else [(1440,1000),(1024,768),(768,900),(390,844),(320,800),(844,390),(667,375)]
                for width,height in sizes:
                    page.set_viewport_size(dict(width=width,height=height));page.goto(base+path);page.wait_for_load_state('networkidle')
                    if width<768:page.locator('[data-sidebar-toggle]').first.click()
                    sidebar=page.locator('#roleSidebar');assert sidebar.bounding_box()['width']==240
                    sidebar.screenshot(path=str(out/f'{role}-{width}.png'))
                    assert not sidebar.evaluate('(el)=>el.scrollWidth>el.clientWidth+1'),(role,width)
                    assert sidebar.locator('a[aria-current=page] span').last.inner_text().strip()==active
                    checks.append([role,width,height])
                if args.stage=='after':
                    page.set_viewport_size(dict(width=390,height=844));page.goto(base+path)
                    toggle=page.locator('[data-sidebar-toggle]').first;toggle.click();sidebar=page.locator('#roleSidebar')
                    expect(sidebar.locator('.role-brand')).to_be_focused()
                    page.keyboard.press('Shift+Tab');expect(sidebar.get_by_role('button',name='Log Out',exact=True)).to_be_focused()
                    page.keyboard.press('Tab');expect(sidebar.locator('.role-brand')).to_be_focused()
                    page.keyboard.press('Escape');expect(toggle).to_be_focused()
                    assert sidebar.evaluate('(el)=>el.inert')
                    assert not page.locator('.role-shell').evaluate('(el)=>el.inert')
                    toggle.click();page.locator('#shellOverlay').click(position=dict(x=300,y=150))
                    assert not sidebar.evaluate('(el)=>el.classList.contains("is-open")')
                    checks.append([role,'drawer focus trap, Escape, inert and outside tap'])
                    page.set_viewport_size(dict(width=320,height=375));toggle.click()
                    visited=set()
                    for _ in range(sidebar.locator('a,button').count()+2):
                        page.keyboard.press('Tab')
                        position=page.evaluate('''() => {
                            const el=document.activeElement,box=el.getBoundingClientRect();
                            return {inside:!!el.closest('#roleSidebar'),top:box.top,bottom:box.bottom,
                              height:box.height,id:(el.href||'')+'|'+el.textContent.trim()};
                        }''')
                        assert position['inside'] and position['top']>=-1 and position['bottom']<=376,position
                        assert position['height']>=44,position
                        visited.add(position['id'])
                    assert len(visited)==sidebar.locator('a,button').count()
                    checks.append([role,'short-screen keyboard access and 44px targets'])
                    page.keyboard.press('Escape');page.set_viewport_size(dict(width=390,height=844));page.goto(base+path)
                    page.evaluate('document.documentElement.style.fontSize="200%"')
                    page.locator('[data-sidebar-toggle]').first.click()
                    page.locator('.role-user small').evaluate('(el)=>el.textContent="Pangasinan State University — Campus Coordination and Volunteer Services"')
                    assert not sidebar.evaluate('(el)=>el.scrollWidth>el.clientWidth+1')
                    assert sidebar.bounding_box()['width']<=page.viewport_size['width']-44
                    sidebar.get_by_role('button',name='Log Out',exact=True).focus()
                    assert sidebar.get_by_role('button',name='Log Out',exact=True).bounding_box()['y']>=0
                    sidebar.screenshot(path=str(out/f'{role}-text-200.png'))
                    checks.append([role,'200% text, long campus and reachable footer'])
                    page.keyboard.press('Escape');page.set_viewport_size(dict(width=1440,height=1000));page.goto(base+path)
                    # Verify shell alignment and selected-state hover before logout.
                    assert page.locator('.role-shell').evaluate('(el)=>parseFloat(getComputedStyle(el).marginLeft)')==240
                    selected=sidebar.locator('a[aria-current=page]');selected.hover()
                    assert selected.evaluate('(el)=>getComputedStyle(el).color')=='rgb(0, 43, 96)'
                    assert all(link.get_attribute('href') for link in sidebar.locator('nav a').all())
                    assert page.request.get(base+'/help').status==200
                    assert page.request.get(base+'/workspace/about').status==200
                    sidebar.get_by_role('button',name='Log Out',exact=True).click();page.wait_for_load_state('load')
                    response=page.goto(base+'/profile' if role=='volunteer' else base+'/workspace/management' if role=='director' else base+'/workspace/activities')
                    assert '/auth/login' in page.url
                    checks.append([role,'offset, selected hover, support links and logout'])
                context.close()
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} sidebar groups passed: {out}')


if __name__=='__main__':main()
