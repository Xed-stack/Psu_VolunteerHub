"""Exercise the proposal UI on isolated synthetic data; optionally serve it locally."""
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
from app.models.workspace import FormDraft,PartnerAgency,ActivityProposal
from app.models.event import Event,SdgGoal,ActivityCategory
from app.models.user import User
from app.services.activity_workflow import local_now
from tests.test_proposal_record import complete_record,filled_docx
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--serve',action='store_true',help='Keep an isolated in-memory preview on loopback port 5002.')
    parser.add_argument('--interactions-only',action='store_true',help='Skip repeated viewport screenshots while debugging interactions.')
    args=parser.parse_args()
    out=Path('.qa-overhaul-temp/proposal-remake').resolve();out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing')
    app.config.update(PRIVATE_UPLOAD_FOLDER=str(out/'private'),WTF_CSRF_ENABLED=True)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    with app.app_context():
        people={}
        for role,email in [('coordinator','coordinator@proposal.example'),('director','director@proposal.example'),('volunteer','student@proposal.example')]:
            user=User(name='Proposal Preview '+role.title(),email=email,role=role,campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow())
            user.set_password('password');db.session.add(user);db.session.flush();people[role]=user.id
        if not SdgGoal.query.first():db.session.add(SdgGoal(number=4,name='Quality Education'))
        if not ActivityCategory.query.filter_by(name='General').first():db.session.add(ActivityCategory(name='General'))
        agency=PartnerAgency(name='Synthetic Community Learning Association',campus_id=1,contact_name='Synthetic Contact',email='contact@proposal.example')
        db.session.add(agency);db.session.flush()
        content=complete_record();content.update(partnership_status='new',agency_id=str(agency.id),psu_roles='Provide trainers.',partner_roles='Provide venue.',partnership_duration='Activity day')
        start=local_now()+timedelta(days=20)
        from werkzeug.datastructures import FileStorage
        from app.routes.proposal import _capture_file
        document,_,_,capture=_capture_file(FileStorage(filled_docx(),filename='Synthetic completed PSU proposal.docx'))
        payload={'_full_proposal':1,'_proposal':document,'_capture':capture,'proposal_record':[json.dumps(content)],
            'title':['Synthetic Community Learning Activity'],'description':['Synthetic proposal preview. Volunteers will assist with community training.'],
            'date':[start.isoformat(timespec='minutes')],'end_date':[(start+timedelta(hours=3)).isoformat(timespec='minutes')],
            'location':['Lingayen community hall'],'category':['General'],'slots':['20'],'cancellation_days':['2'],
            'sdg_ids':[str(SdgGoal.query.first().id)]}
        db.session.add(FormDraft(user_id=people['coordinator'],campus_id=1,key='activity:new',payload=payload));db.session.commit()
        agency_id=agency.id
        cookies={role:app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(uid),_fresh=True,auth_version=1)) for role,uid in people.items()}
    for name in app.jinja_env.list_templates():app.jinja_env.get_template(name)
    if args.serve:
        print('Isolated proposal preview: http://127.0.0.1:5002/workspace/create/1',flush=True)
        print('Coordinator: coordinator@proposal.example / password',flush=True)
        app.run(host='127.0.0.1',port=5002,debug=False,use_reloader=False)
        return
    from playwright.sync_api import sync_playwright,expect
    server=make_server('127.0.0.1',0,app)
    Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    checks=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(reduced_motion='reduce')
            context.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('dialog',lambda dialog:dialog.accept())
            paths=['/workspace/create/'+str(step) for step in (1,2,3,4)]+['/workspace/partners/new',f'/workspace/partners/{agency_id}?activity_context=create']
            for width,height in ([] if args.interactions_only else [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]):
                page.set_viewport_size(dict(width=width,height=height))
                for index,path in enumerate(paths):
                    response=page.goto(base+path);page.wait_for_load_state('networkidle')
                    assert response.status==200,(path,response.status)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(path,width,'overflow')
                    if width in (1440,390):page.screenshot(path=str(out/f'after-{index}-{width}.png'),full_page=True)
                    checks.append([path,width,height])
            page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/workspace/create/2');page.wait_for_load_state('networkidle')
            summary=page.locator('.proposal-index summary');summary.focus();summary.press('Enter')
            assert page.locator('.proposal-index details').get_attribute('open') is not None
            assert summary.evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
            page.locator('[name="pr.rationale"]').focus()
            assert page.locator('[name="pr.rationale"]').evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
            checks.append(['keyboard section disclosure and visible focus'])
            page.locator('[name="pr.rationale"]').fill('Authored rationale retained after refresh.')
            page.get_by_role('button',name='Add Team Member',exact=True).click()
            page.locator('[name="pr.team.name"]').nth(1).fill('Second Synthetic Member')
            page.locator('[name="pr.team.designation"]').nth(1).fill('Staff')
            page.locator('[name="pr.team.campus"]').nth(1).fill('Lingayen')
            page.locator('[name="pr.team.role"]').nth(1).select_option('Member')
            expect(page.locator('.draft-status')).to_contain_text('Draft saved')
            page.reload();page.wait_for_load_state('networkidle')
            expect(page.locator('[name="pr.rationale"]')).to_have_value('Authored rationale retained after refresh.')
            expect(page.locator('[name="pr.team.name"]').nth(1)).to_have_value('Second Synthetic Member')
            checks.append(['structured autosave and row restoration'])
            page.locator('[data-remove-proposal-row]').nth(1).click();expect(page.locator('.draft-status')).to_contain_text('Draft saved')
            page.reload();page.wait_for_load_state('networkidle');assert page.locator('[name="pr.team.name"]').count()==1
            checks.append(['row deletion survives refresh'])
            page.locator('[name="pr.budget.quantity"]').fill('1.005')
            page.locator('[name="pr.budget.unit_cost"]').fill('1.00')
            expect(page.locator('[data-budget-total]')).to_have_text('PHP 1.01')
            checks.append(['exact half-cent budget rounding'])
            # A failed autosave must not discard typed fields or navigate away.
            page.route('**/workspace/drafts/activity%3Anew',lambda route:route.fulfill(status=503,body='Unavailable') if route.request.method=='PUT' else route.continue_())
            page.locator('[name="pr.methodology"]').fill('Retained during simulated save failure.')
            expect(page.locator('.draft-status')).to_contain_text('could not be saved')
            page.get_by_role('button',name='Save and Continue',exact=True).click()
            expect(page.locator('.draft-status')).to_contain_text('could not be saved')
            assert '/create/2' in page.url
            page.unroute('**/workspace/drafts/activity%3Anew')
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_url('**/workspace/create/3')
            checks.append(['failed save retention and retry'])
            page.get_by_role('button',name='Choose or Add an Agency',exact=True).click();page.wait_for_url('**/workspace/partners?activity_context=create')
            page.get_by_role('link',name='Add Agency',exact=True).click();page.wait_for_load_state('networkidle')
            page.locator('#name').fill('New Synthetic Agency');page.locator('#contact_name').fill('Synthetic Contact')
            page.get_by_role('button',name='Save Agency',exact=True).click();page.wait_for_load_state('networkidle')
            page.get_by_role('button',name='Use This Agency',exact=True).click();page.wait_for_url('**/workspace/create/3')
            expect(page.locator('[name="pr.agency_id"] option:checked')).to_have_text('New Synthetic Agency')
            checks.append(['create agency and return with proposal preserved'])
            for step in (2,3,4):
                page.goto(base+f'/workspace/create/{step}');page.wait_for_load_state('networkidle');page.set_viewport_size(dict(width=320,height=800))
                page.evaluate("document.documentElement.style.fontSize='200%'")
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(step,'200% text')
                page.screenshot(path=str(out/f'text200-{step}.png'),full_page=True)
                checks.append([step,'200% text'])
            page.goto(base+'/workspace/create/3');page.wait_for_load_state('networkidle')
            last=page.get_by_role('button',name='Save and Continue',exact=True);last.focus()
            assert last.evaluate("el=>{const r=el.getBoundingClientRect(),nav=document.querySelector('.mobile-nav');return r.top>=0&&r.bottom<=(nav?nav.getBoundingClientRect().top:innerHeight)+1}")
            checks.append(['keyboard action stays above phone navigation'])
            page.goto(base+'/workspace/create/4');page.wait_for_load_state('networkidle')
            for checkbox in page.locator('[name="capture_confirmed"]').all():checkbox.check()
            page.locator('[name="proposal_reviewed"]').check()
            page.get_by_role('button',name='Publish Approved Activity',exact=True).click();page.wait_for_url('**/workspace/activities/*')
            page.get_by_role('link',name='View Proposal Record',exact=True).click();page.wait_for_load_state('networkidle')
            assert 'Authored rationale retained after refresh.' in page.locator('body').inner_text()
            record_url=page.url;checks.append(['review, publish and staff record'])
            director=browser.new_context();director.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            assert director.new_page().goto(record_url).status==200
            volunteer=browser.new_context();volunteer.add_cookies([dict(name='session',value=cookies['volunteer'],url=base)])
            assert volunteer.new_page().goto(record_url).status==403
            checks.append(['Director read access and Volunteer denial'])
            nojs=browser.new_context(java_script_enabled=False)
            nojs.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            n=nojs.new_page();n.goto(base+'/workspace/create/1')
            n.locator('[name="proposal"]').set_input_files(dict(name='nojs.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=filled_docx().getvalue()))
            n.get_by_role('button',name='Capture Proposal and Continue',exact=True).click();n.wait_for_url('**/workspace/create/2')
            n.locator('[name="pr.rationale"]').fill('Saved without JavaScript.')
            n.get_by_role('button',name='Add Team Member',exact=True).click();n.wait_for_load_state('networkidle')
            expect(n.locator('[name="pr.rationale"]')).to_have_value('Saved without JavaScript.')
            assert n.locator('[name="pr.team.name"]').count()==2
            checks.append(['no JavaScript capture, field save and add row'])
            n.get_by_role('button',name='Save and Continue',exact=True).click()
            n.wait_for_load_state('networkidle')
            assert '/workspace/create/3' in n.url, (n.url,n.locator('[data-form-errors]').all_text_contents(),n.locator(':invalid').evaluate_all('els=>els.map(el=>[el.name,el.validationMessage])'))
            n.get_by_role('button',name='Save and Continue',exact=True).click();n.wait_for_load_state('networkidle')
            assert '/workspace/create/4' in n.url, (n.url,n.locator('[data-form-errors]').all_text_contents(),n.locator(':invalid').evaluate_all('els=>els.map(el=>[el.name,el.validationMessage])'))
            n.get_by_role('button',name='Publish Approved Activity',exact=True).click();n.wait_for_load_state('networkidle')
            assert n.locator('[data-form-errors]').count()==1
            assert 'Choose a partnership status.' in n.locator('[data-form-errors]').inner_text()
            n.get_by_role('button',name='Edit Activity Details',exact=True).click();n.wait_for_load_state('networkidle')
            assert '/workspace/create/2' in n.url,(n.url,n.locator('form').evaluate_all('els=>els.map(el=>[el.noValidate,el.action])'),n.locator('[data-form-errors]').all_text_contents(),n.locator(':invalid').evaluate_all('els=>els.map(el=>[el.name,el.validationMessage])'))
            checks.append(['no JavaScript validation and correction navigation'])
            assert not errors,errors
            browser.close()
    finally:server.shutdown()
    (out/'browser-checks.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8')
    print(f'{len(checks)} browser groups passed; screenshots: {out}',flush=True)


if __name__=='__main__':main()
