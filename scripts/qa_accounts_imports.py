"""Capture and exercise management screens using disposable fixtures."""
import argparse
import json
import logging
import sys
from datetime import datetime,timedelta
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
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/accounts-imports')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config['PRIVATE_UPLOAD_FOLDER']=str((out/'private').resolve());checks=[];errors=[]
    with app.app_context():
        director=User.query.filter_by(role='director').first()
        if not director:
            director=User(name='Director',email='director-ui@example.org',role='director',campus_id=1,password_hash='unused');db.session.add(director)
        director.sex='prefer_not_to_say';director.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
        target=User(name='Authored Account Name with a Long Campus Affiliation',email='account-ui@example.org',role='volunteer',campus_id=1,sex='prefer_not_to_say',college_affiliation='College of Community Learning and Extension',password_hash='unused');db.session.add(target)
        old=User(name='Deactivated fixture',email='deactivated-ui@example.org',role='volunteer',campus_id=1,sex='prefer_not_to_say',password_hash='unused',_is_active=False,deactivated_at=datetime.utcnow()-timedelta(days=31));db.session.add(old);db.session.commit();target_id=target.id
        cookie=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(director.id),_fresh=True,auth_version=director.auth_version))
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);context=browser.new_context(has_touch=True,reduced_motion='reduce');context.add_cookies([dict(name='session',value=cookie,url=base)]);page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            paths=['/workspace/management','/admin_dash','/admin_dash?tab=deactivated','/admin_dash?tab=audit',f'/admin/users/{target_id}/edit','/workspace/imports','/admin/users/import','/workspace/imports/historical','/workspace/imports/annual']
            if args.stage=='after':paths.extend([f'/admin/users/{target_id}',f'/admin/users/{target_id}/reset-password'])
            for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height))
                for index,path in enumerate(paths):
                    response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(path,response.status)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(path,width,'overflow')
                    if width in (1440,390):page.screenshot(path=str(out/f'{index}-{width}.png'),full_page=True)
                    checks.append([path,width,height])
            if args.stage=='after':
                page.set_viewport_size(dict(width=1440,height=1000))
                page.goto(base+'/admin_dash?search=Authored&campus_id=1')
                page.get_by_role('link',name='View Record for',exact=False).click()
                page.get_by_role('link',name='Edit Account',exact=True).click()
                page.locator('[name=name]').fill('Retained authored draft')
                page.get_by_text('Draft saved',exact=True).wait_for()
                page.reload();page.get_by_text('Draft restored',exact=True).wait_for()
                assert page.locator('[name=name]').input_value()=='Retained authored draft'
                page.get_by_role('link',name='Back to User Record',exact=True).click()
                page.get_by_role('link',name='Back to Users',exact=True).click()
                assert 'search=Authored' in page.url and 'campus_id=1' in page.url
                page.goto(base+f'/admin/users/{target_id}/reset-password')
                page.locator('[name=new_password]').fill('SecretNotRetained1!')
                page.reload();assert page.locator('[name=new_password]').input_value()==''
                checks.append(['draft refresh, record return context, secret exclusion'])
                from tests.test_accounts_imports_ui import csv_bytes,dataset
                page.goto(base+'/admin/users/import')
                source=b'name,email,password,role,campus_code,id_number,volunteer_type,college_affiliation\nAuthored User,browser-import@example.org,StrongPassword1!,volunteer,LINGAYEN,,,\n'
                page.locator('[type=file]').set_input_files(dict(name='users.csv',mimeType='text/csv',buffer=source))
                page.get_by_role('button',name='Validate and Preview',exact=True).click()
                page.wait_for_url('**stage=review');page.reload()
                assert 'StrongPassword1!' not in page.locator('body').inner_text()
                for width in [1440,320]:
                    page.set_viewport_size(dict(width=width,height=900))
                    page.screenshot(path=str(out/f'user-review-{width}.png'),full_page=True)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.once('dialog',lambda dialog:dialog.accept())
                page.get_by_role('button',name='Confirm Import',exact=True).click()
                page.wait_for_url('**/admin_dash')
                assert page.get_by_text('browser-import@example.org',exact=True).is_visible()
                checks.append(['user preview refresh, private values, confirm'])
                for kind in ['annual','historical']:
                    page.goto(base+'/workspace/imports/'+kind)
                    page.locator('[type=file]').set_input_files(dict(name='fixture.csv',mimeType='text/csv',buffer=csv_bytes(dataset(kind,26))))
                    page.get_by_role('button',name='Validate and Preview',exact=True).click()
                    page.wait_for_url('**stage=review')
                    page.reload();page.get_by_role('link',name='Next',exact=True).click()
                    assert page.get_by_text('Page 2 of 2',exact=True).is_visible()
                    for width in [1440,320]:
                        page.set_viewport_size(dict(width=width,height=900))
                        page.screenshot(path=str(out/f'{kind}-review-{width}.png'),full_page=True)
                        overflow=page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>[e.tagName,e.className,e.getBoundingClientRect().width]).slice(0,12)")
                        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(kind,width,overflow)
                    page.get_by_role('link',name='Choose Another File',exact=True).click()
                    page.get_by_role('link',name='Resume Preview',exact=True).click()
                    page.once('dialog',lambda dialog:dialog.accept())
                    page.get_by_role('button',name='Discard Preview',exact=True).click()
                    page.get_by_role('button',name='Validate and Preview',exact=True).wait_for()
                    checks.append([kind,'refresh, paging, resume, discard'])
                page.goto(base+'/admin_dash')
                page.evaluate("document.documentElement.style.fontSize='200%'")
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.keyboard.press('Tab')
                checks.append(['200% text, keyboard focus'])
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8');print(f'{len(checks)} management layout checks passed. Artifacts: {out}')


if __name__=='__main__':main()
