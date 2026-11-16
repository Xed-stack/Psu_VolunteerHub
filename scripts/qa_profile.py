"""Disposable profile fixtures, before/after captures and browser checks."""
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
from app.models.user import User, Skill, Interest, VolunteerProfile
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/profile-workspace')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config['PRIVATE_UPLOAD_FOLDER']=str((out.parent/'private').resolve());logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        interest=Interest.query.first();active=Skill.query.filter_by(is_active=True).first()
        archived=Skill(name='Previously Assigned Skill',is_active=False)
        user=User(name='María O’Reyes-Santos',email='profile@qa.example',campus_id=1,volunteer_type='student',sex='prefer_not_to_say',college_affiliation='College of Arts, Sciences and Letters (CASL)',first_use_guide_dismissed_at=datetime.utcnow())
        user.set_password('OriginalPassword1!');user.skills=[active,archived];user.interests=[interest]
        db.session.add(user);db.session.flush();uid=user.id;db.session.add(VolunteerProfile(user_id=uid));db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(reduced_motion='reduce');page=context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)));page.on('dialog',lambda dialog:dialog.accept())
            page.goto(base+'/auth/login');page.locator('#identifier').fill('profile@qa.example');page.locator('#password').fill('OriginalPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
            for width,height in [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height))
                for section in ['account','preferences','impact']:
                    assert page.goto(base+'/profile?section='+section).status==200
                    page.wait_for_load_state('networkidle')
                    page.screenshot(path=str(out/f'{section}-{width}.png'),full_page=True)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(section,width)
                checks.append([width,height])
            page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/profile#change-name')
            page.locator('#change-name').evaluate('(el)=>el.open=true')
            page.locator('#account-name').fill('   ')
            page.locator('#change-name form').evaluate('(form)=>{form.noValidate=true;form.requestSubmit(form.querySelector("button[type=submit]"));}')
            page.locator('[data-profile-errors]').wait_for();page.screenshot(path=str(out/'name-error-390.png'),full_page=True)
            checks.append(['name validation screenshot'])
            if args.stage=='after':
                assert page.locator('#change-name').get_attribute('open') is not None
                assert page.locator('[data-profile-errors]').evaluate('(el)=>el===document.activeElement')
                assert page.locator('#account-name').input_value()==''
                checks.append(['validation opens disclosure and focuses linked error summary'])
                page.locator('#account-name').fill('QA Profile Name')
                page.get_by_role('button',name='Save Name',exact=True).click();page.wait_for_url('**/profile#change-name')
                expect(page.locator('#profile-name')).to_have_text('QA Profile Name')
                page.locator('#account-name').fill('Draft Name')
                expect(page.locator('#change-name .draft-status')).to_contain_text('Draft saved')
                page.reload();expect(page.locator('#account-name')).to_have_value('Draft Name')
                page.locator('#change-name .draft-status button').click()
                page.reload();expect(page.locator('#account-name')).to_have_value('QA Profile Name')
                checks.append(['independent name save, refresh restoration and discard'])
                def fail_put(route):
                    if route.request.method=='PUT':route.fulfill(status=500,body='Test save failure')
                    else:route.continue_()
                page.route('**/workspace/drafts/**',fail_put)
                page.locator('#account-name').fill('Failed Draft')
                expect(page.locator('#change-name .draft-status')).to_contain_text('Draft could not be saved')
                page.unroute('**/workspace/drafts/**',fail_put)
                page.locator('#account-name').fill('QA Profile Name')
                expect(page.locator('#change-name .draft-status')).to_contain_text('Draft saved')
                checks.append(['failed draft save feedback and retry'])
                page.goto(base+'/profile#change-campus');page.locator('#change-campus').evaluate('(el)=>el.open=true')
                page.locator('#account-campus_id').select_option(label='Urdaneta')
                page.locator('#account-college_affiliation').select_option(index=1)
                page.get_by_role('button',name='Save Campus',exact=True).click();page.wait_for_url('**/profile#change-campus')
                expect(page.locator('.profile-facts')).to_contain_text('Urdaneta')
                checks.append(['campus affiliation pairing and return hash'])
                page.goto(base+'/profile?section=preferences');page.wait_for_load_state('networkidle')
                expect(page.locator('[data-profile-count=skills]')).to_contain_text('2 of')
                assert page.get_by_text('Previously Assigned Skill (Archived)',exact=True).is_visible()
                checkbox=page.locator('#profile-interests input:not(:checked)').first
                checkbox.check();expect(page.locator('#profile-form .draft-status')).to_contain_text('Draft saved')
                page.reload();expect(page.locator('[data-profile-count=interests]')).to_contain_text('2 of')
                page.locator('#profile-image').set_input_files('static/assets/PSU-logo.png')
                expect(page.locator('[data-profile-photo-preview]')).to_be_visible()
                assert page.locator('[data-profile-photo-preview]').get_attribute('src').startswith('blob:')
                expect(page.locator('#profile-form .draft-status')).to_contain_text('Draft saved')
                page.reload();assert page.locator('#profile-image').input_value()==''
                expect(page.get_by_text('Saved attachment: PSU-logo.png. It will be submitted unless replaced.',exact=True)).to_be_visible()
                page.get_by_role('button',name='Save Profile',exact=True).click();page.wait_for_url('**/profile')
                with app.app_context():assert db.session.get(User,uid).profile_image_path
                page.goto(base+'/profile?section=preferences')
                page.get_by_role('button',name='Remove Profile Photo',exact=True).click();page.wait_for_url('**/profile')
                with app.app_context():assert not db.session.get(User,uid).profile_image_path
                checks.append(['selection counts, archived skill, photo preview, upload restoration/save/removal'])
                page.goto(base+'/profile#change-password');page.locator('#change-password').evaluate('(el)=>el.open=true')
                page.locator('#account-current_password').fill('WrongPassword1!')
                page.locator('#account-new_password').fill('UpdatedPassword2!');page.locator('#account-password_confirmation').fill('UpdatedPassword2!')
                page.get_by_role('button',name='Show New Password',exact=True).click()
                assert page.locator('#account-new_password').get_attribute('type')=='text'
                page.get_by_role('button',name='Hide New Password',exact=True).click()
                page.get_by_role('button',name='Change Password',exact=True).click();page.locator('[data-profile-errors]').wait_for()
                assert all(page.locator('#account-'+key).input_value()=='' for key in ['current_password','new_password','password_confirmation'])
                page.locator('#account-current_password').fill('OriginalPassword1!')
                page.locator('#account-new_password').fill('UpdatedPassword2!');page.locator('#account-password_confirmation').fill('UpdatedPassword2!')
                page.get_by_role('button',name='Change Password',exact=True).click();page.wait_for_url('**/profile#change-password')
                with app.app_context():assert db.session.get(User,uid).check_password('UpdatedPassword2!')
                assert '/auth/login' not in page.url
                checks.append(['password show/hide, blank errors, successful change and retained session'])
                for section in ['account','preferences','impact']:
                    page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/profile?section='+section);page.wait_for_load_state('networkidle')
                    page.evaluate('document.documentElement.style.fontSize="200%"')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),section
                    page.screenshot(path=str(out/f'{section}-text-200.png'),full_page=True)
                checks.append(['200% text on all sections'])
                page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/profile');page.locator('.profile-workspace').wait_for()
                page.locator('#change-name summary').focus();page.keyboard.press('Enter')
                for _ in range(10):
                    page.keyboard.press('Tab')
                    position=page.evaluate('''() => {
                      const el=document.activeElement;
                      if(!el.closest('.profile-workspace'))return null;
                      const box=el.getBoundingClientRect();
                      return {top:box.top,bottom:box.bottom,header:document.querySelector('.role-topbar').getBoundingClientRect().bottom,
                        limit:document.querySelector('.mobile-nav').getBoundingClientRect().top,label:el.id||el.textContent};
                    }''')
                    if position:assert position['top']>=position['header']-1 and position['bottom']<=position['limit']+1,position
                checks.append(['keyboard focus outside fixed header and phone navigation'])
                nojs=browser.new_context(java_script_enabled=False);np=nojs.new_page();np.goto(base+'/auth/login')
                np.locator('#identifier').fill('profile@qa.example');np.locator('#password').fill('UpdatedPassword2!');np.get_by_role('button',name='Sign In',exact=True).click()
                np.goto(base+'/profile');np.locator('#change-name summary').click();np.locator('#account-name').fill('NoJS Profile Name')
                np.get_by_role('button',name='Save Name',exact=True).click();np.wait_for_url('**/profile#change-name')
                assert np.locator('#profile-name').inner_text()=='NoJS Profile Name'
                np.locator('#change-password summary').click()
                assert not np.locator('[data-profile-password]').first.is_visible()
                nojs.close();checks.append(['no-JS disclosures and account save'])
            browser.close();assert not errors,errors
    finally:
        with app.app_context():
            row=db.session.get(User,uid)
            if row and row.profile_image_path:
                path=(Path(app.static_folder)/row.profile_image_path).resolve()
                if path.parent==(Path(app.static_folder)/'uploads/profiles').resolve():path.unlink(missing_ok=True)
        server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} profile browser groups passed: {out}')


if __name__=='__main__':main()
