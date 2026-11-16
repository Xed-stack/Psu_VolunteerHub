"""Isolated Director file discoverability and read-only browser checks."""
import argparse,json,logging,sys
from datetime import datetime,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import quote
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event,Milestone,EventAnnouncement
from app.services.activity_workflow import local_now
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/director-documents')/args.stage;out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='fixtures-',dir=out.resolve()) as tmp:
        app=create_app('testing');app.config['PRIVATE_UPLOAD_FOLDER']=tmp;logging.getLogger('werkzeug').setLevel(logging.ERROR)
        with app.app_context():
            u=User(name='QA Director',email='director@files.test',role='director',campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow());u.set_password('StrongPassword1!');db.session.add(u)
            for campus in [1,2]:
                e=Event(title='Campus Outreach '+str(campus),campus_id=campus,description='Activity details and objectives. '*12,date=local_now()+timedelta(days=5),end_date=local_now()+timedelta(days=5,hours=2),slots=20,lifecycle_status='approved',proposal_document={'name':f'Approved Campus {campus} Proposal.pdf','path':f'campus{campus}.pdf'});db.session.add(e);db.session.flush()
                if campus==1:eid=e.id
                for i in range(27):db.session.add(Milestone(event_id=e.id,filename=f'Supporting Outreach Evidence {i+1}.pdf',upload_path='milestones/evidence.pdf',category='report'))
                db.session.add(EventAnnouncement(event_id=e.id,announcement_type='event_update',message='Coordinator-only history.'))
            db.session.commit()
        for folder in ['proposals','milestones']:(Path(tmp)/folder).mkdir()
        for n in [1,2]:(Path(tmp)/'proposals'/f'campus{n}.pdf').write_bytes(b'%PDF-1.4\nPrivate approved proposal')
        (Path(tmp)/'milestones/evidence.pdf').write_bytes(b'%PDF-1.4\nPrivate supporting evidence')
        server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();page=browser.new_page(reduced_motion='reduce');page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base+'/auth/login');page.locator('#identifier').fill('director@files.test');page.locator('#password').fill('StrongPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
                for path,name in [(f'/workspace/activities/{eid}?return_to=%2Fworkspace%2Factivities%3Fstate%3Dupcoming','overview'),(f'/workspace/activities/{eid}/documents','documents')]:
                    for w,h in ([(1440,1000),(390,844)] if args.stage=='before' else [(1440,1000),(1024,768),(768,900),(390,844),(320,800),(844,390)]):
                        page.set_viewport_size(dict(width=w,height=h));page.goto(base+path);page.wait_for_load_state('networkidle');page.screenshot(path=str(out/f'{name}-{w}.png'))
                        if args.stage=='after':assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,w)
                        checks.append([name,w,h])
                if args.stage=='after':exercise(page,app,base,eid,out,checks)
                browser.close()
            assert not errors,errors
        finally:server.shutdown()
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} browser groups passed: {out}')


def exercise(page,app,base,eid,out,checks):
    page.set_viewport_size(dict(width=1440,height=1000))
    origin='/workspace/activities?state=upcoming'
    page.goto(base+f'/workspace/activities/{eid}?return_to='+quote(origin,safe=''));page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='Approved Proposal',exact=True)).to_have_count(1)
    with page.expect_download() as result:
        page.get_by_role('link',name='Download Approved Proposal',exact=True).click()
    assert result.value.suggested_filename=='Approved Campus 1 Proposal.pdf'
    page.get_by_role('link',name='View All Documents',exact=True).click();page.wait_for_load_state('networkidle')
    assert 'return_to=' in page.url
    assert page.locator('.workspace-tabs a[aria-current=page]').inner_text()=='Documents'
    assert page.get_by_role('link',name='Upload Evidence',exact=True).count()==0
    assert page.get_by_role('link',name='Announcements',exact=True).count()==0
    assert page.get_by_role('link',name='Compose Announcement',exact=True).count()==0
    assert page.locator('.document-resumes').count()==0 and page.locator('main form').count()==0
    page.get_by_role('link',name='Next Page',exact=True).click();page.wait_for_load_state('networkidle')
    assert 'page=2' in page.url and 'return_to=' in page.url and page.locator('.document-row').count()==2
    page.get_by_role('link',name='Document Help',exact=True).click();assert '/help/reports' in page.url
    page.go_back();page.wait_for_load_state('networkidle');assert 'page=2' in page.url
    checks.append('Overview proposal, download, Documents navigation, read-only controls, pagination and Help/Back')
    for campus,activity in [(1,eid),(2,eid+1)]:
        page.goto(base+f'/workspace/activities/{activity}/documents?view=announcements');page.wait_for_load_state('networkidle')
        expect(page.get_by_role('heading',name='Documents',exact=True)).to_be_visible()
        assert page.get_by_text('Coordinator-only history.',exact=True).count()==0
        with page.expect_download() as proposal:page.get_by_role('link',name='Download Approved Proposal',exact=True).click()
        assert proposal.value.suggested_filename==f'Approved Campus {campus} Proposal.pdf'
        with page.expect_download() as evidence:page.locator('.document-row').first.get_by_role('link',name='Download',exact=False).click()
        assert evidence.value.suggested_filename.startswith('Supporting Outreach Evidence')
        checks.append([campus,'proposal/evidence downloads; announcement request remains Documents'])
    for route,name in [(f'/workspace/activities/{eid}','overview'),(f'/workspace/activities/{eid}/documents','documents')]:
        page.goto(base+route);page.wait_for_load_state('networkidle')
        for link in page.locator('main a').all():
            if link.is_visible():assert link.bounding_box()['height']>=43,(name,link.inner_text())
        page.set_viewport_size(dict(width=320,height=800));page.evaluate('document.documentElement.style.fontSize="200%"')
        if name=='documents':page.locator('.document-proposal > p').evaluate('(el)=>el.textContent="LongProposalFilename".repeat(12)+".pdf"')
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,'200%')
        page.get_by_role('link',name='Download Approved Proposal',exact=True).focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
        page.wait_for_function('''() => {const b=document.activeElement.getBoundingClientRect();return b.top>=document.querySelector('.role-topbar').getBoundingClientRect().bottom-1&&b.bottom<=document.querySelector('.mobile-nav').getBoundingClientRect().top+1;}''',timeout=3000)
        page.screenshot(path=str(out/f'{name}-200.png'));page.evaluate('document.documentElement.style.fontSize=""');page.set_viewport_size(dict(width=1440,height=1000))
        page.emulate_media(media='print');assert not page.locator('.role-topbar').is_visible();expect(page.get_by_role('heading',name='Approved Proposal',exact=True)).to_be_visible();page.emulate_media(media='screen')
        checks.append([name,'44px links, 200% text, long filename, keyboard and print'])
    with app.app_context():
        event=db.session.get(Event,eid);event.proposal_document=None;Milestone.query.filter_by(event_id=eid).delete();db.session.commit()
    page.goto(base+f'/workspace/activities/{eid}/documents');page.wait_for_load_state('networkidle')
    expect(page.get_by_role('heading',name='No Supporting Evidence Yet',exact=True)).to_be_visible()
    assert page.get_by_role('link',name='Download Approved Proposal',exact=True).count()==0
    page.screenshot(path=str(out/'documents-empty.png'));checks.append('Missing proposal and supporting-file empty states')


if __name__=='__main__':main()
