"""Disposable catalogue browser journeys and responsive evidence."""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User, Skill, Interest
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    out=Path('.qa-overhaul-temp/catalogue/screenshots');out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        for role in ['director','coordinator','volunteer']:
            user=User(name='Catalogue '+role,email=role+'@catalogue.test',role=role,campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
            user.set_password('StrongPassword1!');db.session.add(user)
        for index in range(30):db.session.add(Skill(name=f'QA Browser {index:02}'))
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(reduced_motion='reduce');page=context.new_page()
            page.on('pageerror',lambda error:errors.append(str(error)));page.on('dialog',lambda dialog:dialog.accept())
            page.goto(base+'/auth/login');page.locator('#identifier').fill('director@catalogue.test');page.locator('#password').fill('StrongPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
            for width,height in [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height))
                for tab in ['skills','categories']:
                    page.goto(base+'/workspace/catalogue?tab='+tab);page.wait_for_load_state('networkidle')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(tab,width)
                    page.screenshot(path=str(out/f'{tab}-{width}.png'))
                checks.append([width,height])
            page.set_viewport_size(dict(width=1440,height=1000));page.goto(base+'/workspace/catalogue?tab=skills&q=QA')
            page.get_by_role('link',name='Next',exact=True).click();assert 'q=QA' in page.url and 'page=2' in page.url
            page.get_by_role('link',name='Add Skill',exact=True).click();page.locator('[name=name]').fill('QA Campus Facilitation')
            page.locator('[name=interest_ids]').first.check();iid=page.locator('[name=interest_ids]').first.get_attribute('value')
            page.screenshot(path=str(out/'add-skill.png'));page.get_by_role('button',name='Add Skill',exact=True).click()
            assert 'q=QA' in page.url
            page.goto(base+'/workspace/catalogue?q=QA%20Campus')
            page.get_by_role('button',name='Archive QA Campus Facilitation',exact=True).click()
            assert page.get_by_role('heading',name='QA Campus Facilitation',exact=True).count()==0
            page.get_by_label('Status',exact=True).select_option('archived');page.get_by_role('button',name='Search',exact=True).click()
            assert page.get_by_role('heading',name='QA Campus Facilitation',exact=True).is_visible()
            page.screenshot(path=str(out/'archived.png'))
            page.get_by_role('button',name='Restore QA Campus Facilitation',exact=True).click()
            page.get_by_label('Status',exact=True).select_option('active');page.get_by_role('button',name='Search',exact=True).click()
            page.get_by_role('link',name='Edit Interests for QA Campus Facilitation',exact=True).click()
            assert page.locator('[name=interest_ids]:checked').count()==1
            page.get_by_role('button',name='Save Interests').click();checks.append(['skill create, pagination context, archive, restore, connections'])
            anonymous=browser.new_context();ap=anonymous.new_page();ap.goto(base+'/auth/interests')
            ap.locator(f'[name=interests][value="{iid}"]').check()
            assert ap.get_by_text('QA Campus Facilitation',exact=True).is_visible()
            with app.app_context():sid=Skill.query.filter_by(name='QA Campus Facilitation').one().id
            ap.locator(f'[name=skills][value="{sid}"]').check()
            page.goto(base+'/workspace/catalogue?q=QA%20Campus');page.get_by_role('button',name='Archive QA Campus Facilitation',exact=True).click()
            ap.reload();assert 'QA Campus Facilitation' in ap.locator('[data-onboarding-status]').inner_text()
            anonymous.close();checks.append(['signup integration and stale draft notice'])
            page.goto(base+'/workspace/catalogue?tab=categories');page.locator('[name=name]').fill('QA Browser Category');page.get_by_role('button',name='Add Category',exact=True).click()
            page.get_by_role('button',name='Archive QA Browser Category',exact=True).click()
            assert page.get_by_role('button',name='Archive General',exact=True).count()==0
            checks.append(['category create/archive and protected General'])
            page.goto(base+'/workspace/catalogue');page.evaluate('document.documentElement.style.fontSize="200%"')
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out/'text-200.png'));checks.append(['200% text'])
            for role in ['coordinator','volunteer']:
                rc=browser.new_context();rp=rc.new_page();rp.goto(base+'/auth/login');rp.locator('#identifier').fill(role+'@catalogue.test');rp.locator('#password').fill('StrongPassword1!');rp.get_by_role('button',name='Sign In',exact=True).click();rp.wait_for_load_state('networkidle')
                assert rp.goto(base+'/workspace/catalogue').status==403
                rc.close()
            checks.append(['other roles denied']);browser.close();assert not errors,errors
    finally:server.shutdown()
    (out.parent/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2))
    print(f'{len(checks)} catalogue browser groups passed: {out}')


if __name__=='__main__':main()
