"""Disposable document/update fixtures and browser captures."""
import argparse
import json
import logging
import sys
from datetime import datetime,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.user import User
from app.models.event import Event,Milestone,EventAnnouncement,Registration
from app.models.notification import Notification
from app.services.activity_workflow import local_now
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');args=parser.parse_args()
    out=Path('.qa-overhaul-temp/documents-announcements')/args.stage;out.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix='docs-qa-',dir=out.resolve()) as tmp:
        app=create_app('testing');app.config['PRIVATE_UPLOAD_FOLDER']=tmp
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        with app.app_context():
            u=User(name='QA Coordinator',email='coordinator@docs.test',role='coordinator',campus_id=1,sex='prefer_not_to_say',first_use_guide_dismissed_at=datetime.utcnow());u.set_password('StrongPassword1!');db.session.add(u);db.session.flush()
            e=Event(title='Community Literacy and Digital Skills Outreach',description='Disposable browser fixture',campus_id=1,date=local_now()-timedelta(days=2),end_date=local_now()-timedelta(days=1),lifecycle_status='approved',slots=50);db.session.add(e);db.session.flush();eid=e.id
            folder=Path(tmp)/'milestones';folder.mkdir();(folder/'example.pdf').write_bytes(b'%PDF-1.4\nQA document')
            for i in range(28):
                db.session.add(Milestone(event_id=eid,filename=f'Community Outreach Supporting Evidence {i+1}.pdf',upload_path='milestones/example.pdf',category='report',uploaded_by_id=u.id,uploaded_at=datetime(2026,11,16,4,30)-timedelta(minutes=i)))
                db.session.add(EventAnnouncement(event_id=eid,author_id=u.id,announcement_type='event_update',message=f'Activity update {i+1}: Review your schedule and contact the campus coordinator through established channels for questions.',created_at=datetime(2026,11,16,4,30)-timedelta(minutes=i)))
            db.session.commit()
        server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}';checks=[];errors=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch();context=browser.new_context(reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base+'/auth/login');page.locator('#identifier').fill('coordinator@docs.test');page.locator('#password').fill('StrongPassword1!');page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_load_state('networkidle')
                paths=[(f'/workspace/activities/{eid}/documents','documents')]
                if args.stage=='after':paths += [(f'/workspace/activities/{eid}/documents?view=announcements','announcements'),(f'/workspace/activities/{eid}/documents/upload','upload'),(f'/workspace/activities/{eid}/announcements/new','compose')]
                for route,name in paths:
                    for w,h in ([(1440,1000),(390,844)] if args.stage=='before' else [(1440,1000),(1024,768),(768,900),(390,844),(320,800),(844,390)]):
                        page.set_viewport_size(dict(width=w,height=h));page.goto(base+route);page.wait_for_load_state('networkidle');page.screenshot(path=str(out/f'{name}-{w}.png'))
                        if args.stage=='after':assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,w)
                        checks.append([name,w,h])
                if args.stage=='after':exercise(page,context,app,base,eid,out,checks)
                context.close();browser.close()
            assert not errors,errors
        finally:server.shutdown()
        (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} browser groups passed: {out}')


def exercise(page,context,app,base,eid,out,checks):
    docs=f'/workspace/activities/{eid}/documents'
    compose=f'/workspace/activities/{eid}/announcements/new'
    upload=docs+'/upload'
    page.set_viewport_size(dict(width=1440,height=1000))
    page.goto(base+docs+'?page=2');page.wait_for_load_state('networkidle')
    assert page.locator('.document-row').count()==3
    page.get_by_role('link',name='Announcements',exact=True).click();page.wait_for_load_state('networkidle')
    assert 'page=1' in page.url
    page.goto(base+docs+'?view=announcements&page=2')
    page.get_by_role('link',name='Compose Announcement',exact=True).click();page.wait_for_load_state('networkidle')
    page.locator('#announcement_type').select_option('cancelled_postponed')
    text='Meet at the gate.\n<img src=x onerror="alert(1)">'
    page.locator('#message').fill(text)
    expect(page.locator('[data-preview-message]')).to_have_text(text)
    assert page.locator('[data-preview-message] img').count()==0
    expect(page.locator('.draft-status')).to_contain_text('Draft saved')
    page.get_by_role('link',name='Cancel',exact=True).click();page.wait_for_load_state('networkidle')
    assert 'page=2' in page.url and 'view=announcements' in page.url
    page.goto(base+compose);page.wait_for_load_state('networkidle')
    expect(page.locator('#message')).to_have_value(text)
    expect(page.locator('[data-preview-type]')).to_have_text('Schedule Notice')
    with app.app_context():
        assert EventAnnouncement.query.count()==28 and Notification.query.count()==0
    page.screenshot(path=str(out/'compose-restored-preview.png'))
    posts=[]
    def count_publish(route):
        if route.request.method=='POST':posts.append(route.request.url)
        route.continue_()
    page.route('**/announcements/new**',count_publish)
    page.get_by_role('button',name='Publish Announcement',exact=True).evaluate('(el)=>{el.click();el.click();}')
    page.wait_for_url('**/documents?**');page.wait_for_load_state('networkidle')
    assert len(posts)==1 and 'view=announcements' in page.url and '#announcement-' in page.url
    with app.app_context():
        assert EventAnnouncement.query.count()==29 and Notification.query.count()==0
    page.unroute('**/announcements/new**',count_publish)
    checks.append('Preview escaping, draft refresh, Cancel context, explicit publish and duplicate guard')

    page.goto(base+upload);page.wait_for_load_state('networkidle')
    page.locator('#file').set_input_files(dict(name='browser-evidence.pdf',mimeType='application/pdf',buffer=b'%PDF-1.4\nBrowser evidence'))
    expect(page.locator('.draft-status')).to_contain_text('Draft saved')
    expect(page.locator('[data-saved-upload=file]')).to_contain_text('browser-evidence.pdf')
    page.locator('#file').set_input_files(dict(name='invalid.pdf',mimeType='application/pdf',buffer=b'Invalid PDF contents'))
    expect(page.locator('.draft-status')).to_contain_text('Attachment could not be saved')
    page.once('dialog',lambda d:d.accept());page.reload();page.wait_for_load_state('networkidle')
    expect(page.locator('[data-saved-upload=file]')).to_contain_text('browser-evidence.pdf')
    assert page.locator('#file').input_value()==''
    page.get_by_role('button',name='Upload Evidence',exact=True).click();page.wait_for_url('**/documents?**');page.wait_for_load_state('networkidle')
    assert '#document-' in page.url
    with page.expect_download() as download:
        page.locator('.document-row').first.get_by_role('link',name='Download',exact=False).click()
    assert download.value.suggested_filename=='browser-evidence.pdf'
    checks.append('Upload restoration, invalid replacement protection, submit and private download')

    page.goto(base+compose);page.wait_for_load_state('networkidle')
    def fail_save(route):
        if route.request.method=='PUT':route.fulfill(status=503,body='Temporary save failure')
        else:route.continue_()
    page.route('**/workspace/drafts/**',fail_save)
    page.locator('#announcement_type').select_option('event_update');page.locator('#message').fill('Keep this unsaved message.')
    expect(page.locator('.draft-status')).to_contain_text('Draft could not be saved')
    page.get_by_role('link',name='Cancel',exact=True).click()
    expect(page.locator('#message')).to_have_value('Keep this unsaved message.')
    assert '/announcements/new' in page.url
    page.screenshot(path=str(out/'compose-save-failure.png'))
    page.unroute('**/workspace/drafts/**',fail_save)
    page.locator('#message').fill('Recovered saved message.')
    expect(page.locator('.draft-status')).to_contain_text('Draft saved')
    page.once('dialog',lambda d:d.accept())
    page.get_by_role('button',name='Discard Draft',exact=True).click()
    expect(page.locator('#message')).to_have_value('')
    expect(page.locator('[data-preview-message]')).to_have_text('Your message preview will appear here.')
    checks.append('Failed save, retained input, blocked Cancel, retry and draft discard')

    nojs=context.browser.new_context(java_script_enabled=False,storage_state=context.storage_state())
    np=nojs.new_page();np.goto(base+compose);np.locator('#announcement_type').select_option('event_update');np.locator('#message').fill('No-JavaScript update.')
    np.get_by_role('button',name='Publish Announcement',exact=True).click();np.wait_for_load_state('networkidle')
    assert 'view=announcements' in np.url
    np.goto(base+upload);np.locator('#file').set_input_files(dict(name='native.pdf',mimeType='application/pdf',buffer=b'%PDF-1.4\nNative form evidence'))
    np.get_by_role('button',name='Upload Evidence',exact=True).click();np.wait_for_load_state('networkidle')
    assert '#document-' in np.url
    nojs.close();page.bring_to_front();checks.append('Native no-JavaScript compose and upload submissions')

    for path,name in [(docs,'documents'),(docs+'?view=announcements','announcements'),(upload,'upload'),(compose,'compose')]:
        page.goto(base+path);page.wait_for_load_state('networkidle')
        for el in page.locator('main a,main button,main input:not([type=hidden]),main select,main textarea').all():
            if el.is_visible():assert el.bounding_box()['height']>=43,(name,el.inner_text())
        page.set_viewport_size(dict(width=320,height=800));page.evaluate('document.documentElement.style.fontSize="200%"')
        if name=='documents':page.locator('.document-row h3').first.evaluate('(el)=>el.textContent="LongEvidenceFilename".repeat(12)+".pdf"')
        page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),(name,'200%')
        target=page.locator('main input:not([type=hidden]),main select').first if name in ('upload','compose') else page.locator('main .btn').first
        target.focus()
        page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
        expect(target).to_be_focused()
        page.screenshot(path=str(out/f'{name}-focus-check.png'))
        page.wait_for_function('''() => {
            const box=document.activeElement.getBoundingClientRect();
            return box.top>=document.querySelector('.role-topbar').getBoundingClientRect().bottom-1 && box.bottom<=document.querySelector('.mobile-nav').getBoundingClientRect().top+1;
        }''',timeout=3000)
        page.screenshot(path=str(out/f'{name}-200.png'))
        page.evaluate('document.documentElement.style.fontSize=""');page.set_viewport_size(dict(width=1440,height=1000))
        if name in ('documents','announcements'):
            page.emulate_media(media='print');assert page.locator('.document-list').is_visible() and not page.locator('.role-topbar').is_visible();page.emulate_media(media='screen')
        checks.append([name,'touch targets, long content, 200% text, focus and list print'])
    page.goto(base+docs);page.get_by_role('link',name='Document and Update Help',exact=True).click()
    assert '/help/documents-updates' in page.url
    page.go_back();assert '/documents' in page.url
    checks.append('Connected Help and Back')
    with app.app_context():
        Milestone.query.delete();EventAnnouncement.query.delete();db.session.commit()
    for path,name in [(docs,'documents'),(docs+'?view=announcements','announcements')]:
        page.goto(base+path);page.wait_for_load_state('networkidle')
        expect(page.locator('.inbox-empty')).to_be_visible();page.screenshot(path=str(out/f'{name}-empty.png'))
    checks.append('Independent document and announcement empty states')


if __name__=='__main__':main()
