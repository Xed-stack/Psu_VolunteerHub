"""Synthetic browser verification for reference card, partner lists and date pickers."""
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
from app.models.event import Event,Registration,SdgGoal
from app.models.workspace import FormDraft,PartnerAgency,PartnerAgreement,ActivityProposal
from app.services.activity_workflow import local_now
from tests.test_proposal_record import complete_record,filled_docx
from werkzeug.datastructures import FileStorage
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect


def main():
    out=Path('.qa-overhaul-temp/overview-partner-pickers').resolve();out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');app.config.update(WTF_CSRF_ENABLED=True,FINDING_REVIEWS_ENABLED=True,PRIVATE_UPLOAD_FOLDER=str(out/'private'))
    logging.getLogger('werkzeug').setLevel(logging.ERROR);cookies={};checks=[];errors=[]
    with app.app_context():
        for role in ['director','coordinator']:
            user=User(name='Synthetic '+role,email=role+'@pickers.invalid',role=role,campus_id=1,sex='prefer_not_to_say',password_hash='unused',first_use_guide_dismissed_at=datetime.utcnow())
            db.session.add(user);db.session.flush()
            if role=='coordinator':uid=user.id
            cookies[role]=app.session_interface.get_signing_serializer(app).dumps(dict(_user_id=str(user.id),_fresh=True,auth_version=user.auth_version))
        agencies=[PartnerAgency(name=name,campus_id=1,contact_name='Synthetic Contact') for name in ['Primary Community Agency','Additional Education Agency','Additional Health Agency']]
        db.session.add_all(agencies);db.session.flush();aid=agencies[0].id;extras=[str(a.id) for a in agencies[1:]]
        start=local_now()+timedelta(days=20)
        from app.routes.proposal import _capture_file
        document,_,_,_=_capture_file(FileStorage(filled_docx(),filename='Synthetic approved proposal.docx'))
        agreement=PartnerAgreement(agency_id=aid,reference='Synthetic signed MOA',valid_from=local_now().date(),valid_until=(start+timedelta(days=30)).date(),document=document)
        db.session.add(agreement);db.session.flush()
        content=complete_record();content.update(partnership_status='existing',agency_id=str(aid))
        payload=dict(_full_proposal=1,_proposal=document,_capture={},proposal_record=[json.dumps(content)],
            title=['Synthetic Partner Activity'],description=['Synthetic browser fixture'],date=[start.isoformat(timespec='minutes')],
            end_date=[(start+timedelta(hours=2)).isoformat(timespec='minutes')],category=['General'],location=['Synthetic PSU venue'],
            slots=['20'],cancellation_days=['2'],sdg_ids=[str(SdgGoal.query.first().id)],agreement_id=[str(agreement.id)])
        db.session.add(FormDraft(user_id=uid,campus_id=1,key='activity:new',payload=payload))
        event=Event(title='Synthetic Attention Activity',description='Synthetic',date=local_now()-timedelta(hours=1),end_date=local_now()+timedelta(hours=2),lifecycle_status='approved',campus_id=1,slots=20)
        db.session.add(event);db.session.flush();db.session.add(Registration(event_id=event.id,user_id=uid,status='confirmed'));db.session.commit()
    for template in app.jinja_env.list_templates():app.jinja_env.get_template(template)
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(reduced_motion='reduce');context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            for enabled in [True,False]:
                app.config['FINDING_REVIEWS_ENABLED']=enabled
                for width in [1440,1024,768,390,320]:
                    page.set_viewport_size(dict(width=width,height=900));assert page.goto(base+'/workspace/overview?period=all').status==200;page.wait_for_load_state('networkidle')
                    card=page.locator('.review-card');expect(card).to_be_visible()
                    assert page.locator('.review-card-groups li').count()==4
                    chart=card.locator('[data-review-chart]');expect(chart).to_be_visible()
                    assert chart.get_attribute('data-review-label')==('Active Reviews' if enabled else 'Findings')
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    card.screenshot(path=str(out/f'card-{enabled}-{width}.png'));checks.append(['reference card',enabled,width])
            app.config['FINDING_REVIEWS_ENABLED']=True
            context.add_cookies([dict(name='session',value=cookies['coordinator'],url=base)])
            for width,height in [(1440,900),(1024,768),(768,900),(438,344),(390,700),(320,568)]:
                page.set_viewport_size(dict(width=width,height=height));page.goto(base+'/workspace/create/2');page.wait_for_load_state('networkidle')
                page.locator('#schedule-start-display').click()
                dialog=page.locator('#schedule-picker');expect(dialog).to_be_visible()
                assert dialog.locator('.schedule-time-arrow svg').count()==2
                for unit in ['hour','minute']:
                    page.locator(f'[data-time-toggle={unit}]').click()
                    options=page.locator(f'#schedule-{unit}-options');expect(options).to_be_visible()
                    assert options.evaluate('el=>getComputedStyle(el).position')=='static'
                    assert not dialog.evaluate('el=>el.scrollWidth>el.clientWidth+1')
                    options.get_by_role('option',name='12' if unit=='hour' else '59',exact=True).click()
                    assert page.locator(f'#schedule-picker-{unit}').input_value()==('12' if unit=='hour' else '59')
                    assert page.locator(f'[data-time-toggle={unit}]').bounding_box()['width']>=43
                dialog.screenshot(path=str(out/f'time-picker-{width}.png'))
                page.locator('#schedule-picker-cancel').click();expect(dialog).to_be_hidden();expect(page.locator('#schedule-start-display')).to_be_focused();checks.append(['unclipped time lists',width,height])
            page.set_viewport_size(dict(width=1440,height=900));page.goto(base+'/workspace/create/3');page.wait_for_load_state('networkidle')
            for value in extras:page.locator(f'[name="pr.additional_agency_ids"][value="{value}"]').check()
            expect(page.locator(f'[name="pr.additional_agency_ids"][value="{aid}"]')).to_be_disabled()
            page.get_by_role('button',name='Save Draft',exact=True).click();page.wait_for_load_state('networkidle');page.reload();page.wait_for_load_state('networkidle')
            for value in extras:expect(page.locator(f'[name="pr.additional_agency_ids"][value="{value}"]')).to_be_checked()
            for width in [1440,768,390,320]:
                page.set_viewport_size(dict(width=width,height=900));page.wait_for_function('document.documentElement.scrollWidth<=innerWidth+1')
                page.locator('#section-partnership').screenshot(path=str(out/f'partners-{width}.png'));checks.append(['multiple agency choices',width])
            page.get_by_role('button',name='Choose or Add an Agency',exact=True).click();page.wait_for_load_state('networkidle')
            page.get_by_role('link',name='Back to Activity Draft',exact=True).click();page.wait_for_load_state('networkidle')
            page.goto(base+'/workspace/create/3');page.wait_for_load_state('networkidle')
            for value in extras:expect(page.locator(f'[name="pr.additional_agency_ids"][value="{value}"]')).to_be_checked()
            page.get_by_role('button',name='Save and Continue',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.get_by_text('Additional Education Agency, Additional Health Agency',exact=True)).to_be_visible();checks.append('save, refresh, partner navigation and review')
            path=f'/workspace/partners/{aid}/agreements/new'
            assert page.request.get(base+'/static/scripts/moa-date-picker.js').status==200
            for width in [1440,768,390,320]:
                page.set_viewport_size(dict(width=width,height=900));page.goto(base+path);page.wait_for_load_state('networkidle')
                for key,value in [('valid_from','2020-02-20'),('valid_until','2020-02-20')]:
                    page.locator(f'[data-moa-picker={key}]').click()
                    expect(page.locator('#moa-date-picker')).to_be_visible()
                    if key=='valid_from':page.locator('#moa-date-picker').screenshot(path=str(out/f'moa-dialog-{width}.png'))
                    page.locator('#moa-picker-date').fill(value)
                    assert page.locator('#moa-date-picker input').count()==1
                    page.locator('[data-moa-confirm]').click();expect(page.locator(f'[data-moa-picker={key}]')).to_have_text('Feb 20, 2020')
                page.locator('[data-moa-picker=valid_from]').click();page.locator('#moa-picker-date').fill('2021-01-01');page.locator('[data-moa-cancel]').click()
                expect(page.locator('[data-moa-picker=valid_from]')).to_be_focused()
                assert page.locator('#valid_from').input_value()=='2020-02-20'
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.screenshot(path=str(out/f'moa-{width}.png'),full_page=True);checks.append(['uniform date-only MOA',width])
            page.locator('#reference').fill('Synthetic Historical MOA')
            page.locator('#document').set_input_files(dict(name='synthetic.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=filled_docx().getvalue()))
            page.get_by_text('Draft saved',exact=True).wait_for()
            page.reload();page.get_by_text('Draft restored',exact=True).wait_for()
            expect(page.locator('[data-moa-picker=valid_from]')).to_have_text('Feb 20, 2020')
            expect(page.locator('[data-moa-picker=valid_until]')).to_have_text('Feb 20, 2020')
            page.get_by_text('Saved attachment: synthetic.docx.',exact=False).wait_for();checks.append('MOA dates and upload survive draft refresh')
            page.get_by_role('button',name='Save Agreement',exact=True).click();page.wait_for_load_state('networkidle')
            expect(page.get_by_role('heading',name='Synthetic Historical MOA',exact=True)).to_be_visible();checks.append('historical same-day MOA saved')
            nojs=browser.new_context(java_script_enabled=False,storage_state=context.storage_state());native=nojs.new_page()
            native.goto(base+'/workspace/create/3')
            for value in extras:expect(native.locator(f'[name="pr.additional_agency_ids"][value="{value}"]')).to_be_checked()
            native.get_by_role('button',name='Save Draft',exact=True).click();native.wait_for_load_state('networkidle')
            native.goto(base+path);expect(native.locator('#valid_from')).to_be_visible();expect(native.locator('[data-moa-picker=valid_from]')).to_be_hidden()
            native.locator('#reference').fill('Synthetic Native MOA');native.locator('#valid_from').fill('2019-01-01');native.locator('#valid_until').fill('2019-01-01')
            native.locator('#document').set_input_files(dict(name='native.docx',mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document',buffer=filled_docx().getvalue()))
            native.get_by_role('button',name='Save Agreement',exact=True).click();native.wait_for_load_state('networkidle')
            expect(native.get_by_role('heading',name='Synthetic Native MOA',exact=True)).to_be_visible()
            nojs.close();checks.append('native no-JavaScript partner save and MOA inputs')
            context.add_cookies([dict(name='session',value=cookies['director'],url=base)])
            page.goto(base+'/workspace/overview?period=all&activity_name=NoSuchSyntheticActivity');page.wait_for_load_state('networkidle')
            expect(page.locator('.review-empty')).to_contain_text('0 Active Reviews');checks.append('zero reviews')
            page.route('**/*plotly*.js',lambda route:route.abort())
            page.goto(base+'/workspace/overview?period=all');page.wait_for_load_state('networkidle')
            assert page.locator('.review-card-groups li').count()==4 and page.locator('[data-review-chart]:visible').count()==0
            checks.append('chart failure preserves exact category counts')
            context.close();browser.close()
        assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} browser groups passed: {out}')


if __name__=='__main__':main()
