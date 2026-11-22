"""Verify posting essentials in Chromium using isolated synthetic data."""
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
    parser.add_argument('--interactions-only',action='store_true',help='Skip repeated viewport screenshots while debugging interactions.')
    args=parser.parse_args()
    out=Path('.qa-overhaul-temp/posting-essentials').resolve();out.mkdir(parents=True,exist_ok=True)
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
            for width,height in ([] if args.interactions_only else [(1440,1000),(1024,900),(768,900),(390,844),(320,800)]):
                page.set_viewport_size(dict(width=width,height=height))
                for step in (1,2,3,4):
                    response=page.goto(base+f'/workspace/create/{step}');page.wait_for_load_state('networkidle')
                    assert response.status==200
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(step,width,page.evaluate("[...document.querySelectorAll('main *')].filter(el=>el.getBoundingClientRect().right>innerWidth+1).slice(0,5).map(el=>el.outerHTML.slice(0,250))"))
                    assert page.locator('[name="pr.budget_na"], [name="pr.rationale"], [data-proposal-rows]').count()==0
                    if width in (1440,390,320):page.screenshot(path=str(out/f'step-{step}-{width}.png'),full_page=True)
                    checks.append(['step layout',step,width])
            page.goto(base+'/workspace/create/3');page.wait_for_load_state('networkidle')
            status=page.locator('[name="pr.partnership_status"]')
            status.select_option('none');expect(page.locator('#partner-details')).to_be_hidden()
            status.select_option('existing');expect(page.locator('#partner-details')).to_be_visible()
            expect(page.locator('[name="agreement_id"]')).to_have_attribute('required','')
            status.select_option('new');expect(page.locator('[name="agreement_id"]')).not_to_have_attribute('required','')
            status.focus();assert status.evaluate("el=>getComputedStyle(el).outlineStyle!=='none'")
            checks.append(['conditional partners and keyboard focus'])
            page.get_by_role('button',name='Choose or Add an Agency',exact=True).click();page.wait_for_load_state('networkidle')
            page.wait_for_url('**/workspace/partners?**')
            page.goto(base+f'/workspace/partners/{agency_id}?activity_context=create');page.wait_for_load_state('networkidle')
            page.get_by_role('button',name='Use This Agency',exact=True).click();page.wait_for_url('**/workspace/create/3');page.wait_for_load_state('networkidle')
            assert page.url.endswith('/workspace/create/3')
            expect(page.locator('[name="pr.agency_id"]')).to_have_value(str(agency_id))
            checks.append(['saved partner round trip'])
            page.goto(base+'/workspace/create/2');page.wait_for_load_state('networkidle')
            page.locator('[name="description"]').fill('Edited public posting summary.')
            expect(page.locator('.draft-status')).to_contain_text('Draft saved')
            page.reload();page.wait_for_load_state('networkidle')
            expect(page.locator('[name="description"]')).to_have_value('Edited public posting summary.')
            with app.app_context():
                saved=FormDraft.query.filter_by(user_id=people['coordinator'],key='activity:new').one()
                assert json.loads(saved.payload['proposal_record'][0])['rationale']==content['rationale']
            checks.append(['autosave and hidden authored data retention'])
            page.locator('[name="title"]').fill('')
            page.locator('[data-proposal-form]').evaluate('form=>form.noValidate=true')
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.locator('[data-form-errors]')).to_be_focused()
            expect(page.locator('[name="title"]')).to_have_attribute('aria-invalid','true')
            page.locator('[name="title"]').fill('Synthetic Community Learning Activity')
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_url('**/workspace/create/3');page.wait_for_load_state('networkidle')
            checks.append(['inline validation, summary focus and recovery'])
            page.locator('[name="pr.partnership_status"]').select_option('none')
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_load_state('networkidle')
            page.wait_for_url('**/workspace/create/4')
            assert page.locator('[name="capture_confirmed"]').count()==0
            page.locator('[name="proposal_reviewed"]').check()
            page.get_by_role('button',name='Publish Approved Activity',exact=True).click();page.wait_for_load_state('networkidle')
            page.wait_for_url('**/workspace/activities/*')
            with app.app_context():
                event=Event.query.filter_by(title='Synthetic Community Learning Activity').one()
                event_id=event.id
                record=db.session.get(ActivityProposal,event_id)
                assert record.content['_form_profile']=='posting_essentials_v1'
                assert record.content['budget']==content['budget']
                assert not FormDraft.query.filter_by(user_id=people['coordinator'],key='activity:new').first()
            page.goto(base+f'/workspace/activities/{event_id}/proposal-record');page.wait_for_load_state('networkidle')
            assert 'Total Requested' not in page.locator('main').inner_text()
            expect(page.locator('main')).to_contain_text('Edited public posting summary.')
            checks.append(['publish without full proposal checks and immutable staff record'])
            page.locator('.proposal-summary-row dd').first.evaluate("el=>el.textContent='LongAttachmentName'.repeat(20)")
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.emulate_media(media='print')
            page.screenshot(path=str(out/'record-print.png'),full_page=True)
            expect(page.locator('main')).to_contain_text('Edited public posting summary.')
            page.emulate_media(media='screen')
            checks.append(['long text and print values'])
            # Exercise a fresh draft with actual upload and conservative capture.
            page.goto(base+'/workspace/create/1');page.wait_for_load_state('networkidle')
            page.locator('[name="proposal"]').set_input_files(dict(name='Captured proposal.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=filled_docx('Captured activity title').getvalue()))
            page.get_by_role('button',name='Capture Proposal and Continue',exact=True).click();page.wait_for_url('**/workspace/create/2');page.wait_for_load_state('networkidle')
            expect(page.locator('[name="title"]')).to_have_value('Captured activity title')
            expect(page.locator('[name="location"]')).to_have_value('Lingayen community hall')
            expect(page.locator('[name="description"]')).to_have_value('')
            page.locator('[name="title"]').fill('Authored title retained')
            page.get_by_role('button',name='Save and Go Back',exact=True).click();page.wait_for_url('**/workspace/create/1');page.wait_for_load_state('networkidle')
            page.locator('[name="proposal"]').set_input_files(dict(name='Replacement.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=filled_docx('Replacement title').getvalue()))
            page.get_by_role('button',name='Save and Continue',exact=True).click();expect(page.get_by_role('heading',name='Review Replacement Proposal')).to_be_visible();page.wait_for_load_state('networkidle')
            assert page.locator('[name="replace_fields"][value="budget"]').count()==0
            page.get_by_role('button',name='Confirm Replacement',exact=True).click();page.wait_for_url('**/workspace/create/2');page.wait_for_load_state('networkidle')
            expect(page.locator('[name="title"]')).to_have_value('Authored title retained')
            checks.append(['upload capture, replacement and retained edits'])
            page.set_viewport_size(dict(width=390,height=844))
            page.evaluate("document.documentElement.style.fontSize='200%'")
            assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            page.screenshot(path=str(out/'text-200-percent.png'),full_page=True)
            checks.append(['200 percent text reflow'])
            plain=browser.new_context(java_script_enabled=False)
            plain.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            basic=plain.new_page();basic.goto(base+'/workspace/create/3');basic.wait_for_load_state('networkidle')
            expect(basic.locator('#partner-details')).to_be_visible()
            basic.locator('[name="pr.partnership_status"]').select_option('none')
            basic.get_by_role('button',name='Save and Continue',exact=True).click();basic.wait_for_load_state('networkidle')
            assert basic.url.endswith('/workspace/create/4')
            checks.append(['native no-JavaScript progression'])
            assert not errors,errors
            browser.close()
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,page_errors=errors),indent=2))
    print(f'{len(checks)} browser groups passed; evidence: {out}')


if __name__=='__main__':main()
