"""Capture and exercise activity forms using disposable, repeatable fixtures."""
import argparse
import json
import logging
import io
import sys
from datetime import datetime,timedelta
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event,SdgGoal
from app.models.user import User,Skill
from app.models.workspace import FormDraft
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from PIL import Image


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');parser.add_argument('--interactions-only',action='store_true');args=parser.parse_args()
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    out=Path('.qa-overhaul-temp/activity-forms')/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');checks=[];errors=[]
    app.config['PRIVATE_UPLOAD_FOLDER']=str((out/'private').resolve())
    with app.app_context():
        user=User.query.filter_by(role='coordinator').first()
        if not user:
            user=User(name='Coordinator',email='coordinator-forms@example.org',role='coordinator',campus_id=1,password_hash='unused');db.session.add(user)
        user.sex='prefer_not_to_say';user.first_use_guide_dismissed_at=datetime.utcnow();db.session.flush()
        cookie=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        event=Event.query.first();event.date=local_now()+timedelta(days=20);event.end_date=event.date+timedelta(hours=2);event.cancellation_deadline=event.date-timedelta(days=1);event.lifecycle_status='approved';event.campus_id=user.campus_id
        event.participation_agreement_text='Preserved legacy agreement';event.participation_agreement_version='legacy-policy';event.nda_required=True;event.nda_text='Preserved legacy NDA';event.nda_version='legacy-nda'
        skills=Skill.query.order_by(Skill.name).limit(2).all();sdgs=SdgGoal.query.order_by(SdgGoal.number).limit(2).all()
        from app.routes.coordinator import _activity_categories
        payload=dict(_proposal=dict(name='Approved proposal.docx',readable=True,path='private-fixture.docx'),title=['Campus community learning activity'],description=['Authored proposal description.'],date=[event.date.isoformat(timespec='minutes')],end_date=[event.end_date.isoformat(timespec='minutes')],category=[_activity_categories()[0]],slots=['20'],cancellation_days=['2'],required_skills=[str(s.id) for s in skills],sdg_ids=[str(s.id) for s in sdgs])
        db.session.add(FormDraft(user_id=user.id,campus_id=user.campus_id,key='activity:new',payload=payload));db.session.commit();event_id=event.id
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);context=browser.new_context(has_touch=True,reduced_motion='reduce');context.add_cookies([dict(name='session',value=cookie,url=base)])
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            paths=['/workspace/create/2','/workspace/create/3','/workspace/create/4',f'/coordinator/events/{event_id}/edit']
            for width,height in ([] if args.interactions_only else [(1440,1000),(768,900),(390,844),(320,800),(844,390)]):
                page.set_viewport_size(dict(width=width,height=height))
                for index,path in enumerate(paths):
                    response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(path,response.status)
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(path,width,'overflow')
                    if width in (1440,390):page.screenshot(path=str(out/f'{index}-{width}.png'),full_page=True)
                    checks.append([path,width,height])
            if args.stage=='before':
                browser.close();print('Before form screenshots captured:',out);return
            for index,path in enumerate([] if args.interactions_only else paths):
                page.set_viewport_size(dict(width=320,height=800));page.goto(base+path);page.wait_for_load_state('networkidle');page.evaluate("document.documentElement.style.fontSize='200%'")
                if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                    page.screenshot(path=str(out/'text200-overflow.png'),full_page=True);raise AssertionError((path,'200% overflow'))
                page.screenshot(path=str(out/f'{index}-320-text200.png'),full_page=True);checks.append([path,'200% text'])
            page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/workspace/create/2');page.wait_for_load_state('networkidle')
            assert page.locator('[name=cover_image]').is_visible() and page.locator('[name=cover_image]').locator('xpath=ancestor::details').count()==0
            for name in ['nda_required','nda_text','participation_agreement_text','volunteer_ids']:
                assert page.locator(f'[name="{name}"]').count()==0
            skills_panel=page.locator('[data-choice-panel]').filter(has=page.locator('[name=required_skills]'))
            skills_panel.locator('[data-choice-query]').fill('NoSuchSkillLiteral%_');old_url=page.url
            skills_panel.locator('[data-choice-query]').press('Enter')
            assert page.url==old_url and 'No options match' in skills_panel.locator('[data-choice-results]').inner_text()
            assert skills_panel.locator('[data-choice-selected] button').count()==2
            skills_panel.locator('[data-choice-selected] button').first.click();page.wait_for_function("document.querySelector('.draft-status').textContent.includes('Draft saved')")
            page.reload();page.wait_for_load_state('networkidle');assert skills_panel.locator('[data-choice-selected] button').count()==1
            skills_panel.locator('[data-choice-clear]').click();page.wait_for_function("document.querySelector('.draft-status').textContent.includes('Draft saved')")
            page.reload();page.wait_for_load_state('networkidle');assert skills_panel.locator('input:checked').count()==0
            checks.append(['filter Enter does not submit; selected removal and intentionally empty draft restore'])
            inputs=skills_panel.locator('input[type=checkbox]');inputs.first.check();inputs.last.check();last_value=inputs.last.get_attribute('value')
            first_label=inputs.first.get_attribute('data-choice-label');skills_panel.locator('[data-choice-query]').fill(first_label);skills_panel.locator('[data-choice-filter]').click()
            assert inputs.last.is_checked() and not inputs.last.is_visible()
            sdg_panel=page.locator('[data-choice-panel]').filter(has=page.locator('[name=sdg_ids]'))
            sdg_panel.locator('[data-choice-clear]').click();page.get_by_role('button',name='Save and Continue',exact=True).click()
            assert page.url==old_url and page.locator('[name=sdg_ids]').first.get_attribute('aria-invalid')=='true'
            sdg_panel.locator('input[type=checkbox]').first.check()
            image=io.BytesIO();Image.new('RGB',(8,8),'blue').save(image,format='PNG')
            page.locator('[name=cover_image]').set_input_files(dict(name='retained-cover.png',mimeType='image/png',buffer=image.getvalue()))
            page.wait_for_function("document.querySelector('.draft-status').textContent.includes('Draft saved')")
            page.reload();page.wait_for_load_state('networkidle');assert 'retained-cover.png' in page.locator('main').inner_text()
            invalid=page.locator('form[data-draft-key]').evaluate("form=>[...form.elements].filter(e=>e.willValidate && !e.validity.valid).map(e=>({name:e.name,value:e.value,error:e.validationMessage}))")
            if invalid:
                page.screenshot(path=str(out/'invalid-before-continue.png'),full_page=True)
                raise AssertionError(('invalid after cover reload',invalid))
            page.get_by_role('button',name='Save and Continue',exact=True).click()
            try:page.wait_for_url('**/workspace/create/3',timeout=10000)
            except Exception:
                page.screenshot(path=str(out/'failed-continue.png'),full_page=True)
                raise AssertionError(('continue blocked',page.url,errors))
            draft=context.request.get(base+'/workspace/drafts/activity:new').json()['payload'];assert last_value in draft['required_skills'] and draft['_files']['cover_image']['name']=='retained-cover.png'
            checks.append(['hidden selections submit; required SDG; staged cover survives refresh and next step'])
            departments=page.locator('[name=departments]');departments.first.check();departments.last.check();page.wait_for_function("document.querySelector('.draft-status').textContent.includes('Draft saved')")
            page.screenshot(path=str(out/'selected-departments-390.png'),full_page=True)
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_url('**/workspace/create/4')
            assert 'retained-cover.png' in page.locator('main').inner_text() and page.locator('[name=volunteer_ids]').count()==0
            checks.append(['multiple departments persist into final review'])
            page.goto(base+'/workspace/create/2');page.wait_for_load_state('networkidle')
            def fail_save(route):
                if route.request.method=='PUT':route.fulfill(status=500,content_type='application/json',body='{}')
                else:route.continue_()
            page.route('**/workspace/drafts/**',fail_save);skills_panel.locator('input[type=checkbox]').nth(2).check()
            page.wait_for_function("document.querySelector('.draft-status').textContent.includes('could not be saved')")
            page.unroute('**/workspace/drafts/**',fail_save);skills_panel.locator('input[type=checkbox]').nth(2).uncheck();page.wait_for_function("document.querySelector('.draft-status').textContent.includes('Draft saved')")
            checks.append(['save failure stays visible and recovers'])
            sdg_panel=page.locator('[data-choice-panel]').filter(has=page.locator('[name=sdg_ids]'))
            for checkbox in sdg_panel.locator('input[type=checkbox]').all()[:6]:checkbox.check()
            assert sdg_panel.locator('[data-choice-selected] details').count()==1
            sdg_panel.locator('[data-choice-selected] summary').focus();page.keyboard.press('Enter');assert sdg_panel.locator('[data-choice-selected] details').evaluate('e=>e.open')
            page.screenshot(path=str(out/'selected-sdgs-390.png'),full_page=True);checks.append(['selected overflow disclosure works by keyboard'])
            nojs=browser.new_context(java_script_enabled=False,viewport=dict(width=390,height=844));nojs.add_cookies([dict(name='session',value=cookie,url=base)]);plain=nojs.new_page();plain.goto(base+'/workspace/create/2')
            assert not plain.locator('[data-choice-tools]').first.is_visible() and plain.locator('[name=required_skills]').first.is_visible()
            plain.locator('[name=required_skills]').first.check();plain.get_by_role('button',name='Save and Continue',exact=True).click();plain.wait_for_url('**/workspace/create/3')
            checks.append(['native checkboxes and form submission without JavaScript']);nojs.close()
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2),encoding='utf-8')
    print(f'{len(checks)} activity form checks passed. Artifacts: {out}')


if __name__=='__main__':main()
