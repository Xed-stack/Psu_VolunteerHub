"""Disposable sign-in fixtures and responsive/authentication browser checks."""
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
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/login-photo-split')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR);checks=[];errors=[]
    with app.app_context():
        for role in ['volunteer','coordinator','director']:
            user=User(name='Authored '+role,email=f'login-{role}@example.org',id_number='LOGIN-'+role,role=role,campus_id=1,
                sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
            user.set_password('StrongPassword1!');db.session.add(user)
        inactive=User(name='Inactive fixture',email='login-inactive@example.org',role='volunteer',campus_id=1,sex='prefer_not_to_say',_is_active=False)
        inactive.set_password('StrongPassword1!');db.session.add(inactive);db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(has_touch=True,reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width,height in [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height));response=page.goto(base+'/auth/login');page.wait_for_load_state('networkidle');assert response.status==200
                page.screenshot(path=str(out/f'login-{width}.png'),full_page=True)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),width
                if args.stage == 'after':
                    assert page.locator('.login-workspace .auth-nav').count()==1
                    if width>=1024:
                        photo=page.locator('.login-photo').bounding_box()
                        assert photo['x']==0 and photo['y']==0 and abs(photo['width']-width/2)<2
                        assert photo['height']>=height
                    else:assert not page.locator('.login-photo').is_visible()
                checks.append([width,height])
            page.set_viewport_size(dict(width=390,height=844))
            page.locator('#identifier').fill('wrong@example.org');page.locator('#password').fill('WrongPassword1!')
            page.get_by_role('button',name='Sign In',exact=True).click();page.locator('[data-error-summary]').wait_for()
            page.screenshot(path=str(out/'invalid-390.png'),full_page=True)
            page.goto(base+'/auth/login');page.locator('#identifier').fill('login-inactive@example.org');page.locator('#password').fill('StrongPassword1!')
            page.get_by_role('button',name='Sign In',exact=True).click();page.locator('dialog[open]').wait_for()
            page.screenshot(path=str(out/'inactive-390.png'),full_page=True)
            checks.append(['invalid and deactivated screenshots'])
            if args.stage == 'after':
                page.keyboard.press('Escape');page.locator('dialog').wait_for(state='hidden')
                assert page.locator('#identifier').evaluate('(el)=>el===document.activeElement')
                checks.append(['reactivation Escape restores focus'])
                page.goto(base+'/auth/login');page.locator('#password').fill('NeverPersist123!')
                page.get_by_role('button',name='Show Password',exact=True).click()
                assert page.locator('#password').get_attribute('type')=='text'
                assert page.get_by_role('button',name='Hide Password').get_attribute('aria-pressed')=='true'
                page.get_by_role('button',name='Hide Password').click()
                assert page.locator('#password').get_attribute('type')=='password'
                page.locator('#identifier').fill('bad\"<id>@example.org');page.locator('#password').press('Enter')
                page.locator('[data-error-summary]').wait_for()
                assert page.locator('#identifier').input_value()=='bad\"<id>@example.org'
                assert page.locator('#password').input_value()==''
                assert page.locator('#identifier').evaluate('(el)=>el===document.activeElement')
                assert 'NeverPersist123!' not in page.content()
                assert page.evaluate('!JSON.stringify({...localStorage,...sessionStorage}).includes("NeverPersist123!")')
                checks.append(['password toggle, Enter, escaped identifier, blank password and error focus'])
                page.goto(base+'/auth/login');page.evaluate('document.documentElement.style.fontSize="200%"')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out/'text-200-390.png'),full_page=True)
                assert not page.locator('.login-photo').is_visible()
                checks.append(['200% text and mobile photo hidden'])
                page.goto(base+'/auth/login')
                for label in ['Home','Help','Forgot Your Password?','Create an Account']:
                    href=page.get_by_role('link',name=label,exact=True).get_attribute('href')
                    assert page.request.get(base+href).status==200,(label,href)
                assert page.locator('#identifier').evaluate('(el)=>el.required')
                assert page.locator('#password').evaluate('(el)=>el.required')
                page.locator('#identifier').fill('busy@example.org');page.locator('#password').fill('TestPassword1!')
                page.evaluate('''() => {
                  window.submitStates=[];
                  document.addEventListener('submit',e=>{
                    window.submitStates.push(e.defaultPrevented);e.preventDefault();
                  });
                }''')
                page.get_by_role('button',name='Sign In',exact=True).click()
                assert page.locator('form[data-no-draft]').get_attribute('aria-busy')=='true'
                page.locator('form[data-no-draft]').evaluate('(el)=>el.requestSubmit(el.querySelector("button[type=submit]"))')
                assert page.evaluate('window.submitStates')==[False,True]
                page.evaluate('dispatchEvent(new Event("pageshow"))')
                assert page.get_by_role('button',name='Sign In',exact=True).get_attribute('aria-busy') is None
                checks.append(['navigation, required fields, loading and duplicate submission guard'])
                for next_path in ['/help','https://example.org/']:
                    nc=browser.new_context();npage=nc.new_page()
                    npage.goto(base+'/auth/login?next='+next_path)
                    npage.locator('#identifier').fill('login-volunteer@example.org');npage.locator('#password').fill('StrongPassword1!')
                    npage.get_by_role('button',name='Sign In',exact=True).click();npage.wait_for_load_state('networkidle')
                    assert npage.url.startswith(base+'/')
                    if next_path=='/help':assert npage.url==base+'/help'
                    else:assert '/auth/login' not in npage.url
                    nc.close()
                checks.append(['safe next and external redirect rejection'])
                zoom=browser.new_context(viewport=dict(width=720,height=500),device_scale_factor=2)
                zp=zoom.new_page();zp.goto(base+'/auth/login');zp.wait_for_load_state('networkidle')
                assert not zp.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                zp.screenshot(path=str(out/'zoom-equivalent-200.png'),full_page=True);zoom.close()
                checks.append(['200% zoom-equivalent responsive viewport'])
                for role in ['volunteer','coordinator','director']:
                    role_context=browser.new_context();role_page=role_context.new_page()
                    role_page.goto(base+'/auth/login');role_page.locator('#identifier').fill('LOGIN-'+role if role=='coordinator' else f'login-{role}@example.org')
                    role_page.locator('#password').fill('StrongPassword1!');role_page.locator('#password').press('Enter')
                    role_page.wait_for_load_state('networkidle')
                    assert '/auth/login' not in role_page.url,role_page.url
                    assert role_page.locator('.role-topbar').is_visible(),role_page.url
                    checks.append([role+' email/ID sign-in',role_page.url.replace(base,'')]);role_context.close()
                nojs=browser.new_context(java_script_enabled=False);np=nojs.new_page();np.goto(base+'/auth/login')
                assert not np.locator('[data-toggle-password]').is_visible()
                np.locator('#identifier').fill('login-inactive@example.org');np.locator('#password').fill('StrongPassword1!')
                np.get_by_role('button',name='Sign In',exact=True).click()
                assert np.locator('noscript').get_by_role('button',name='Request Reactivation').is_visible()
                np.locator('noscript').get_by_role('button',name='Request Reactivation').click()
                assert 'sent to the Director' in np.content()
                np.locator('#identifier').fill('login-inactive@example.org');np.locator('#password').fill('StrongPassword1!')
                np.get_by_role('button',name='Sign In',exact=True).click()
                np.locator('noscript').get_by_role('button',name='Request Reactivation').click()
                assert 'already pending review' in np.content()
                nojs.close();checks.append(['no-JS password field and reactivation fallback'])
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} sign-in groups passed: {out}')


if __name__=='__main__':main()
