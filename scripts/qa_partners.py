"""Exercise partner journeys with disposable fixtures and capture layouts."""
import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.workspace import PartnerAgency,PartnerAgreement,FormDraft
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/partners')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config['PRIVATE_UPLOAD_FOLDER']=str((out/'private').resolve())
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        user=User(name='Coordinator',email='partner-qa@example.org',role='coordinator',campus_id=1,sex='prefer_not_to_say',password_hash='unused',first_use_guide_dismissed_at=datetime.utcnow())
        db.session.add(user);db.session.flush()
        agency=PartnerAgency(name='Authored Community Learning Partner',contact_name='Authored Contact Person',email='contact@example.org',phone='09123456789',campus_id=1)
        db.session.add(agency);db.session.flush()
        agreement=PartnerAgreement(agency_id=agency.id,reference='MOA-2026-01',valid_from=date(2026,1,1),valid_until=date(2030,12,31),document={'name':'signed-agreement.pdf','path':'fixture.pdf'})
        db.session.add(agreement)
        db.session.add(FormDraft(user_id=user.id,campus_id=1,key='activity:new',payload={'_proposal':{'name':'proposal.pdf','path':'proposal.pdf'},'title':['Authored Activity'],'date':['2027-05-12T09:00'],'participant_type':['Community']}))
        db.session.commit();aid=agency.id;mid=agreement.id
        cookie=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(has_touch=True,reduced_motion='reduce');context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            paths=['/workspace/partners',f'/workspace/partners/{aid}']
            if args.stage=='after':paths += ['/workspace/partners/new',f'/workspace/partners/{aid}/edit',f'/workspace/partners/{aid}/agreements/new',f'/workspace/partners/{aid}/agreements/{mid}?activity_context=create']
            for width,height in [(1440,1000),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height))
                for index,path in enumerate(paths):
                    response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(path,response.status)
                    if width in (1440,390):page.screenshot(path=str(out/f'{index}-{width}.png'),full_page=True)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(path,width)
                    checks.append([path,width,height])
            if args.stage=='after':
                from tests.test_workspace_overhaul import docx
                page.set_viewport_size(dict(width=1440,height=1000))
                page.goto(base+'/workspace/create/3')
                page.locator('[name=participant_type]').fill('Retained before partner detour')
                page.get_by_role('link',name='Choose an MOA or Add a Partner',exact=True).click()
                page.wait_for_url('**/workspace/partners?activity_context=create')
                page.get_by_role('link',name='View Agency:',exact=False).click()
                page.get_by_role('link',name='View MOA ',exact=False).click()
                page.get_by_role('button',name='Use This MOA',exact=True).click()
                page.wait_for_url('**/workspace/create/3')
                assert page.locator('[name=agreement_id]').input_value()==str(mid)
                assert page.locator('[name=participant_type]').input_value()=='Retained before partner detour'
                # Failed saves keep the user on the activity form.
                page.route('**/workspace/drafts/**',lambda route:route.fulfill(status=503,body='unavailable') if route.request.method=='PUT' else route.continue_())
                page.locator('[name=participant_type]').fill('Unsaved value')
                page.get_by_role('link',name='Choose an MOA or Add a Partner',exact=True).click()
                page.get_by_text('The draft could not be saved. Keep this page open and try again.',exact=True).wait_for()
                assert '/workspace/create/3' in page.url
                page.unroute('**/workspace/drafts/**')
                page.get_by_role('link',name='Choose an MOA or Add a Partner',exact=True).click()
                page.wait_for_url('**/workspace/partners?activity_context=create')
                checks.append(['save before detour, apply MOA, failed save, retry'])
                page.goto(base+'/workspace/partners?activity_context=create&q=Authored')
                page.get_by_role('link',name='View Agency:',exact=False).click()
                page.get_by_role('link',name='Edit Agency Details',exact=True).click()
                page.locator('[name=phone]').fill('09990000000')
                page.get_by_text('Draft saved',exact=True).wait_for()
                page.get_by_role('button',name='Save Changes',exact=True).click()
                page.get_by_text('09990000000',exact=True).wait_for()
                page.get_by_role('link',name='Back to Agencies',exact=True).click()
                assert 'q=Authored' in page.url and 'activity_context=create' in page.url
                page.locator('[name=q]').fill('No matching authored agency');page.locator('[name=q]').press('Enter')
                page.get_by_role('link',name='Reset Filters',exact=True).wait_for()
                page.screenshot(path=str(out/'empty-search.png'),full_page=True)
                page.get_by_role('link',name='Reset Filters',exact=True).click()
                assert 'activity_context=create' in page.url and 'q=' not in page.url
                checks.append(['contact edit, filtered Back, Enter search, reset'])
                page.goto(base+'/workspace/partners/new')
                page.locator('[name=name]').fill('Authored New Agency')
                page.locator('[name=contact_name]').fill('Authored Contact')
                page.get_by_text('Draft saved',exact=True).wait_for()
                page.reload();page.get_by_text('Draft restored',exact=True).wait_for()
                assert page.locator('[name=name]').input_value()=='Authored New Agency'
                page.get_by_role('button',name='Save Agency',exact=True).click()
                page.get_by_role('link',name='Add MOA',exact=True).wait_for()
                page.get_by_role('link',name='Add MOA',exact=True).click()
                page.locator('[name=reference]').fill('Authored Uploaded MOA')
                page.locator('[name=valid_from]').fill('2027-01-01');page.locator('[name=valid_until]').fill('2030-12-31')
                with page.expect_response(lambda r:'/workspace/draft-uploads/' in r.url):
                    page.locator('[type=file]').set_input_files(dict(name='signed.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=docx().getvalue()))
                page.get_by_text('Draft saved',exact=True).wait_for()
                page.reload();page.get_by_text('Draft restored',exact=True).wait_for()
                page.get_by_text('Saved attachment: signed.docx.',exact=False).wait_for()
                page.get_by_role('button',name='Save Agreement',exact=True).click()
                page.get_by_role('link',name='Download Document',exact=True).wait_for()
                assert page.get_by_role('heading',name='Authored Uploaded MOA',exact=True).is_visible()
                checks.append(['agency draft refresh, agreement attachment refresh, submit'])
                page.goto(base+f'/workspace/partners/{aid}/agreements/{mid}?activity_context=create')
                page.evaluate("document.documentElement.style.fontSize='200%'")
                page.screenshot(path=str(out/'agreement-200.png'),full_page=True)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.keyboard.press('Tab');assert page.evaluate("document.activeElement.matches('a,button,input,summary')")
                page.emulate_media(media='print');page.screenshot(path=str(out/'agreement-print.png'),full_page=True)
                checks.append(['200% text, keyboard, print'])
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} partner checks passed: {out}')


if __name__=='__main__':main()
