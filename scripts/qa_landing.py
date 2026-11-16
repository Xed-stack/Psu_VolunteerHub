"""Landing screenshots and carousel checks against disposable records."""
import argparse
import json
import logging
import sys
from datetime import timedelta
from pathlib import Path
from threading import Thread

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.models import db
from app.models.event import Event
from app.services.activity_workflow import local_now
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],default='after');parser.add_argument('--output-root',default='.qa-overhaul-temp/landing-restoration');args=parser.parse_args()
    out=Path(args.output_root)/args.stage;out.mkdir(parents=True,exist_ok=True)
    app=create_app('testing');logging.getLogger('werkzeug').setLevel(logging.ERROR);checks=[];errors=[]
    with app.app_context():
        now=local_now()
        for n in range(6):
            db.session.add(Event(title=f'Authored upcoming activity {n}',description='Authored community activity description.',
                campus_id=1,slots=20,date=now+timedelta(days=n+2),end_date=now+timedelta(days=n+2,hours=3),
                lifecycle_status='approved',category='Community',cover_image_path='assets/FB_IMG_1788789005999.jpg' if n%2 else None))
        for n in range(3):
            db.session.add(Event(title=f'Authored completed activity {n}',description='Authored completed activity description.',
                campus_id=1,slots=20,date=now-timedelta(days=n+2,hours=3),end_date=now-timedelta(days=n+2),
                lifecycle_status='approved',cover_image_path='assets/FB_IMG_1788789005999.jpg' if n%2 else None))
        db.session.commit()
    server=make_server('127.0.0.1',0,app);Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch();context=browser.new_context(has_touch=True,reduced_motion='reduce');page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
            for width,height in [(1440,1000),(1024,900),(768,900),(390,844),(320,800),(844,390)]:
                page.set_viewport_size(dict(width=width,height=height));response=page.goto(base+'/');page.wait_for_load_state('networkidle');assert response.status==200
                page.screenshot(path=str(out/f'landing-{width}.png'),full_page=True)
                if 'landing-footer' in args.output_root:
                    page.locator('footer').screenshot(path=str(out/f'footer-{width}.png'))
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),width
                checks.append([width,height])
            if args.stage=='after' and 'landing-footer' in args.output_root:
                page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/')
                footer=page.locator('.landing-footer')
                assert footer.locator('a[href="/help"]').count()==1
                assert page.locator('.landing-help').count()==0
                for link in footer.locator('a').all():
                    link.scroll_into_view_if_needed()
                    assert link.bounding_box()['height']>=44,(link.inner_text(),'target height')
                footer.get_by_role('link',name='Back to Top',exact=True).click()
                assert page.evaluate("document.activeElement.id==='landing-start'")
                assert page.evaluate('window.scrollY')<2
                page.evaluate("document.documentElement.style.fontSize='200%'")
                footer.screenshot(path=str(out/'footer-200.png'))
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                page.emulate_media(media='print')
                footer.screenshot(path=str(out/'footer-print.png'))
                assert footer.get_by_role('link',name='Activities',exact=True).is_visible()
                assert not footer.get_by_role('link',name='Back to Top',exact=True).is_visible()
                assert footer.locator('h2').first.evaluate('e=>getComputedStyle(e).color')!='rgb(255, 255, 255)'
                page.emulate_media(media='screen')
                fallback_context=browser.new_context(java_script_enabled=False,viewport=dict(width=390,height=844))
                fallback_page=fallback_context.new_page();fallback_page.goto(base+'/')
                fallback_page.locator('.landing-footer').get_by_role('link',name='Back to Top',exact=True).click()
                assert fallback_page.evaluate("document.activeElement.id==='landing-start' && scrollY<2")
                fallback_context.close();checks.append(['footer links, native Back to Top, no-JS, 200%, print'])
            if args.stage=='after':
                page.set_viewport_size(dict(width=390,height=844));page.goto(base+'/')
                active=lambda:page.locator('[data-hero-dot][aria-pressed=true]').get_attribute('data-hero-dot')
                assert active()=='0'
                assert page.locator('[data-hero-pause]').is_disabled()
                assert page.locator('[data-hero-slide][src]').count()==1
                page.get_by_role('button',name='Next Photo',exact=True).click();assert active()=='1'
                page.get_by_role('button',name='Previous Photo',exact=True).click();assert active()=='0'
                page.get_by_role('button',name='Show Photo 4 of 5',exact=True).click();assert active()=='3'
                page.get_by_role('button',name='Next Activity',exact=True).click()
                assert page.locator('[data-carousel]').evaluate('e=>e.scrollLeft')>0
                page.get_by_role('button',name='Previous Activity',exact=True).click()
                page.evaluate("document.documentElement.style.fontSize='200%'")
                page.screenshot(path=str(out/'landing-200.png'),full_page=True)
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                checks.append(['reduced motion, manual photos, activity scrolling, 200%'])
                no_js=browser.new_context(java_script_enabled=False,viewport=dict(width=390,height=844))
                fallback=no_js.new_page();fallback.goto(base+'/');fallback.screenshot(path=str(out/'no-javascript.png'),full_page=True)
                assert fallback.locator('[data-hero-slide].is-active').is_visible()
                assert not fallback.locator('[data-hero-controls]').is_visible()
                assert not fallback.locator('[data-carousel-controls]').is_visible()
                assert fallback.get_by_role('link',name='Explore Activities',exact=True).is_visible()
                assert not fallback.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                fallback.keyboard.press('Tab');fallback.keyboard.press('Enter')
                assert fallback.evaluate("document.activeElement.id==='main-content'")
                no_js.close();checks.append(['no-JS first photo, actions, native scroll fallback'])
                animated=browser.new_context(viewport=dict(width=1440,height=1000),reduced_motion='no-preference')
                motion=animated.new_page();motion.on('pageerror',lambda error:errors.append(str(error)));motion.clock.install()
                motion.goto(base+'/');motion.wait_for_load_state('networkidle')
                index=lambda:motion.locator('[data-hero-dot][aria-pressed=true]').get_attribute('data-hero-dot')
                motion.mouse.move(1,1);assert index()=='0'
                motion.clock.fast_forward(6100);assert index()=='1'
                motion.get_by_role('button',name='Pause Photo Rotation',exact=True).click()
                assert motion.get_by_role('button',name='Resume Photo Rotation',exact=True).is_visible()
                motion.mouse.move(1,1);paused=index();motion.clock.fast_forward(12000);assert index()==paused
                motion.get_by_role('button',name='Resume Photo Rotation',exact=True).click();motion.mouse.move(1,1)
                motion.clock.fast_forward(6100);assert index()!=paused
                motion.keyboard.press('Tab');focused=index()
                motion.clock.fast_forward(12000);assert index()==focused
                motion.get_by_role('button',name='Resume Photo Rotation',exact=True).click();motion.mouse.move(1,1)
                focused=index()
                motion.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
                motion.clock.fast_forward(12000);assert index()==focused
                motion.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'))")
                motion.clock.fast_forward(6100);assert index()!=focused
                motion.screenshot(path=str(out/'carousel-controls.png'),full_page=True)
                animated.close();checks.append(['six-second rotation, pause/resume, keyboard focus, hidden document'])
                page.goto(base+'/');page.emulate_media(media='print')
                page.screenshot(path=str(out/'print.png'),full_page=True)
                assert page.locator('#hero-title').evaluate("e=>getComputedStyle(e).color")!='rgb(255, 255, 255)'
                page.emulate_media(media='screen');checks.append(['readable print fallback'])
                with app.app_context():
                    Event.query.delete();db.session.commit()
                page.evaluate("document.documentElement.style.fontSize='100%'");page.goto(base+'/')
                assert page.get_by_text('No upcoming activities are available yet. Check back for new campus activities.',exact=True).is_visible()
                page.screenshot(path=str(out/'empty.png'),full_page=True);checks.append(['empty activity sections'])
            browser.close();assert not errors,errors
    finally:server.shutdown()
    (out/'results.json').write_text(json.dumps(dict(checks=checks,errors=errors),indent=2));print(f'{len(checks)} landing checks passed: {out}')


if __name__=='__main__':main()
