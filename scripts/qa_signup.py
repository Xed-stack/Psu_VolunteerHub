"""Run signup checks with disposable SQLite data and local Chromium."""
import argparse
import json
import logging
import sys
from pathlib import Path
from threading import Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import Interest, Skill, User
from app.models.policy import TermsRevision, PrivacyRevision
from config import Config
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['before', 'after'], default='after')
    args = parser.parse_args()
    out = Path('.qa-overhaul-temp/signup-onboarding') / args.stage
    out.mkdir(parents=True, exist_ok=True)
    app = create_app('testing')
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        for name, skills in list(Config.INTEREST_SKILL_MAP.items())[:3]:
            if not Interest.query.filter_by(name=name).first():
                db.session.add(Interest(name=name))
            for skill in skills:
                if not Skill.query.filter_by(name=skill).first():
                    db.session.add(Skill(name=skill)); db.session.flush()
        db.session.add(TermsRevision(title='QA Terms', body='Read these test terms.', version='1'))
        db.session.add(PrivacyRevision(title='QA Privacy', body='Read this test privacy notice.', version='1'))
        db.session.commit()
    server = make_server('127.0.0.1', 0, app)
    Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    checks, errors = [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('dialog', lambda dialog: dialog.accept())
            for width, height in [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width, height=height))
                for step, path in [('interests','/auth/interests'),('account','/auth/register')]:
                    assert page.goto(base+path).status == 200
                    page.wait_for_load_state('networkidle')
                    page.screenshot(path=str(out/f'{step}-{width}.png'), full_page=True)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(step,width)
                    if args.stage == 'after':
                        footer=page.get_by_role('contentinfo',name='Signup Footer')
                        assert footer.count()==1
                        assert footer.get_by_role('link',name='About Us').bounding_box()['height']>=44
                        assert footer.get_by_role('link',name='Help and Guides').bounding_box()['height']>=44
                        if width==1440:
                            for link in footer.get_by_role('link').all():
                                assert page.request.get(base+link.get_attribute('href')).status==200
                checks.append([width,height])
            if args.stage == 'after':
                page.set_viewport_size(dict(width=1024,height=900))
                page.goto(base+'/auth/interests')
                group = page.locator('.choice-group').first
                assert not group.locator('.related-skills').is_visible()
                interest_id = group.locator('[name=interests]').get_attribute('value')
                group.locator('[name=interests]').check()
                assert group.locator('.related-skills').is_visible()
                skill_id = group.locator('[name=skills]').first.get_attribute('value')
                group.locator('[name=skills]').first.check()
                assert '1 interest and 1 skill' in page.locator('[data-selection-count]').inner_text()
                page.reload()
                assert page.locator(f'[name=interests][value="{interest_id}"]').is_checked()
                assert page.locator('[name=skills]:checked').count() >= 1
                page.screenshot(path=str(out/'selected-1024.png'),full_page=True)
                page.get_by_role('button',name='Continue to Account Details').click()
                page.wait_for_url('**/auth/register')
                assert page.locator('.onboarding-preferences-summary').count()==0
                actions=page.locator('form[data-signup-draft] .form-actions')
                assert actions.get_by_role('link',name='Back to Interests and Skills').bounding_box()['x'] < actions.get_by_role('button',name='Create Account').bounding_box()['x']
                assert page.locator('[name=volunteer_type] option[value=external]').count()==0
                checks.append(['selection reveal, refresh, left/right actions and internal categories'])
                for name,value in [('first_name','QA'),('last_name','Onboarding'),('email','onboarding@example.org')]:
                    page.locator(f'[name={name}]').fill(value)
                page.locator('[name=sex]').select_option('prefer_not_to_say')
                page.locator('[name=volunteer_type]').select_option('student')
                assert page.locator('#id_number').evaluate('(el)=>el.required')
                page.locator('[name=campus]').select_option(index=1)
                page.locator('#college_affiliation').select_option(index=1)
                affiliation=page.locator('#college_affiliation').input_value()
                page.locator('#id_number').fill('QA-ONBOARDING-1')
                page.locator('#password').fill('StrongPassword1!');page.locator('#password_confirmation').fill('StrongPassword1!')
                page.locator('#terms_accepted').check();page.locator('#privacy_acknowledged').check()
                stored=json.loads(page.evaluate('sessionStorage.getItem("psu:signup")'))
                assert not any(key in stored for key in ['password','password_confirmation','terms_accepted','privacy_acknowledged','csrf_token'])
                page.reload()
                assert page.locator('[name=first_name]').input_value()=='QA'
                assert page.locator('#college_affiliation').input_value()==affiliation
                assert page.locator('#password').input_value()==''
                assert not page.locator('#terms_accepted').is_checked()
                assert not page.locator('#privacy_acknowledged').is_checked()
                checks.append(['ordinary fields, dependent affiliation restoration, password/consent exclusion'])
                page.get_by_role('link',name='Back to Interests and Skills').click()
                assert page.locator('[name=interests]:checked').count()>=1
                page.get_by_role('button',name='Continue to Account Details').click();page.wait_for_url('**/auth/register')
                assert page.locator('[name=first_name]').input_value()=='QA'
                page.locator('[name=campus]').select_option(index=2)
                if page.locator('#college_affiliation').input_value()!=affiliation:
                    assert 'Choose an affiliation again' in page.locator('#college-affiliation-hint').inner_text()
                for category in ['student','faculty','staff']:
                    page.locator('[name=volunteer_type]').select_option(category)
                    assert page.locator('#id_number').evaluate('(el)=>el.required')
                    assert page.locator('#college_affiliation').evaluate('(el)=>el.required')
                if not page.locator('#college_affiliation').input_value():
                    page.locator('#college_affiliation').select_option(index=1)
                checks.append(['Edit return, campus changes and all category requirements'])
                page.locator('#password').fill('StrongPassword1!');page.locator('#password_confirmation').fill('StrongPassword1!')
                page.locator('#terms_accepted').check();page.locator('#privacy_acknowledged').check()
                # Force server validation to verify draft values cannot overwrite the response.
                page.locator('[name=first_name]').fill('')
                page.locator('form[data-signup-draft]').evaluate('(form)=>{form.noValidate=true;form.requestSubmit(form.querySelector("button[type=submit]"));}')
                page.locator('[data-error-summary]').wait_for()
                assert page.locator('[name=first_name]').input_value()==''
                assert page.locator('[name=first_name]').evaluate('(el)=>el===document.activeElement')
                assert page.locator('#password').input_value()==''
                assert not page.locator('#terms_accepted').is_checked()
                page.screenshot(path=str(out/'account-error.png'),full_page=True)
                page.locator('[name=first_name]').fill('QA')
                page.locator('#password').fill('StrongPassword1!');page.locator('#password_confirmation').fill('StrongPassword1!')
                page.locator('#terms_accepted').check();page.locator('#privacy_acknowledged').check()
                page.get_by_role('button',name='Create Account',exact=True).click();page.wait_for_url('**/auth/login')
                assert page.evaluate('sessionStorage.getItem("psu:signup")') is None
                page.locator('#identifier').fill('onboarding@example.org');page.locator('#password').fill('StrongPassword1!')
                page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
                assert '/auth/login' not in page.url
                checks.append(['server validation precedence, account creation, cleanup and sign-in'])
                broken=browser.new_context()
                broken.add_init_script('Object.defineProperty(window,"sessionStorage",{get(){throw new Error("Blocked")}})')
                bp=broken.new_page();bp.goto(base+'/auth/interests')
                assert 'unavailable' in bp.locator('[data-onboarding-status]').inner_text()
                bp.locator('[name=interests]').first.check()
                assert 'could not be saved' in bp.locator('[data-onboarding-status]').inner_text()
                broken.close();checks.append(['storage failure feedback'])
                legacy=browser.new_context()
                legacy.add_init_script('sessionStorage.setItem("psu:signup",JSON.stringify({first_name:"Retained",volunteer_type:"external"}))')
                lp=legacy.new_page();lp.goto(base+'/auth/register')
                assert lp.locator('[name=first_name]').input_value()=='Retained'
                assert lp.locator('[name=volunteer_type]').input_value()==''
                legacy.close();checks.append(['removed category draft retains other fields'])
                nojs=browser.new_context(java_script_enabled=False);np=nojs.new_page();np.goto(base+'/auth/interests')
                assert np.locator('.related-skills').first.is_visible()
                np.locator('[name=interests]').first.check();np.locator('[name=skills]').first.check()
                np.get_by_role('button',name='Continue to Account Details').click();np.wait_for_url('**/auth/register')
                assert np.locator('#college_affiliation').is_enabled()
                assert np.locator('#college_affiliation option').count()>1
                for name,value in [('first_name','NoJS'),('last_name','Volunteer'),('email','nojs@example.org'),('password','StrongPassword1!'),('password_confirmation','StrongPassword1!')]:
                    np.locator(f'[name={name}]').fill(value)
                np.locator('[name=sex]').select_option('prefer_not_to_say')
                np.locator('[name=volunteer_type]').select_option('student')
                np.locator('#id_number').fill('QA-NOJS-1')
                np.locator('[name=campus]').select_option(label='Lingayen')
                np.locator('#college_affiliation').select_option('College of Arts, Sciences and Letters (CASL)')
                np.locator('#terms_accepted').check();np.locator('#privacy_acknowledged').check()
                np.get_by_role('button',name='Create Account',exact=True).click();np.wait_for_url('**/auth/login')
                nojs.close();checks.append(['no-JS selections and campus affiliation options'])
                zoom=browser.new_context(viewport=dict(width=390,height=844));zp=zoom.new_page()
                for path in ['/auth/interests','/auth/register']:
                    zp.goto(base+path);zp.evaluate('document.documentElement.style.fontSize="200%"')
                    zp.screenshot(path=str(out/('text-200-'+path.rsplit('/',1)[-1]+'.png')),full_page=True)
                    assert not zp.evaluate('document.documentElement.scrollWidth>innerWidth+1'), (path,zp.evaluate('[...document.querySelectorAll("body *")].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,8).map(el=>[el.tagName,el.className])'))
                zoom.close();checks.append(['200% text on both steps'])
                keyboard=browser.new_context();kp=keyboard.new_page();kp.goto(base+'/auth/interests')
                kp.keyboard.press('Tab');kp.keyboard.press('Enter')
                assert kp.evaluate('document.activeElement.id')=='main-content'
                for label in kp.locator('.choice').all():
                    if label.is_visible(): assert label.bounding_box()['height']>=44
                keyboard.close();checks.append(['keyboard skip link and preference touch targets'])
            browser.close()
            assert not errors, errors
    finally:
        server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} signup groups passed: {out}')


if __name__ == '__main__':
    main()
