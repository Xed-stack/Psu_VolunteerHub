"""Create an isolated synthetic year and check it in headless Chromium."""
import json
import os
import sqlite3
import sys
import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from app import create_app
from app.models import db
from app.models.event import Event
from app.models.user import SystemSetting, User
from app.railway_year_dataset import MARKER
from config import TestingConfig
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server


def main():
    from secrets import token_hex
    folder=ROOT/'.qa-railway-year-browser-temp'/token_hex(5)
    folder.mkdir(parents=True)
    source=folder/'source.sqlite'
    TestingConfig.SQLALCHEMY_DATABASE_URI='sqlite:///'+source.as_posix()
    app=create_app('testing')
    with app.app_context():
        # This is a disposable source account, not a retained operational profile.
        User.query.filter_by(email='student@psu.edu').one().sex='female'
        db.session.commit()
        db.session.remove()
        db.engine.dispose()
    TestingConfig.SQLALCHEMY_DATABASE_URI='sqlite:///'+(folder/'year.sqlite').as_posix()
    TestingConfig.REPORT_DEMO_MODE=True
    app=create_app('testing')
    app.config.update(PRIVATE_UPLOAD_FOLDER=str(folder/'private'), WTF_CSRF_ENABLED=True,
                      SESSION_COOKIE_SECURE=False, FINDING_REVIEWS_ENABLED=True, REPORT_DEMO_MODE=False)
    os.environ['RAILWAY_SEED_SOURCE_DATABASE_URL']='sqlite:///'+source.as_posix()
    now=datetime(2026,11,24,10)
    patches=['app.railway_year_dataset.local_now','app.services.aop_goals.local_now',
             'app.services.activity_workflow.local_now','app.services.finding_reviews.local_now','app.annual_goals.local_now']
    from contextlib import ExitStack
    with ExitStack() as stack:
        for name in patches:
            stack.enter_context(patch(name,lambda:now))
        name=str(folder/'year.sqlite').replace('\\','/')
        result=app.test_cli_runner().invoke(args=['seed-railway-year','--database',name],input=f'SEED 2026 local/{name}\n')
        assert result.exit_code==0,result.output
        with app.app_context():
            manifest=json.loads(SystemSetting.query.filter_by(key=MARKER).one().value)
            event_id=Event.query.filter_by(lifecycle_status='approved').first().id
        server=make_server('127.0.0.1',0,app,threaded=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        checks=[]
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                try:
                    for email in ('director@psu.edu','admin@psu.edu','coordinator@psu.edu','student@psu.edu'):
                        context=browser.new_context(viewport={'width':1440,'height':1000})
                        page=context.new_page()
                        errors=[]
                        page.on('pageerror',lambda err:errors.append(str(err)))
                        assert page.goto(origin+'/auth/login').status==200
                        page.locator('input[name="identifier"]').fill(email)
                        page.locator('input[name="password"]').fill('password')
                        page.locator('button[type="submit"]').click()
                        page.wait_for_load_state('networkidle')
                        assert '/auth/login' not in page.url,page.url
                        skip=page.get_by_role('button',name='Skip Guide')
                        if skip.is_visible():
                            skip.click()
                        checks.append(email+' signed in')
                        paths=['/workspace/overview','/workspace/activities','/annual-goals?year=2026','/workspace/follow-up?year=2026',
                               '/workspace/reports/aop?year=2026','/workspace/reports/results?year=2026'] if email!='student@psu.edu' else [
                                   '/profile','/opportunities','/workspace/registrations']
                        for path in paths:
                            response=page.goto(origin+path)
                            page.wait_for_load_state('networkidle')
                            skip=page.get_by_role('button',name='Skip Guide')
                            if skip.is_visible():
                                skip.click()
                            assert response.status==200,(email,path,response.status)
                            checks.append(email+' '+path)
                        if email=='director@psu.edu':
                            for report in ('','&report=aop'):
                                for extension in ('csv','pdf'):
                                    response=context.request.get(origin+f'/workspace/reports/export/{extension}?year=2026'+report)
                                    assert response.status==200,response.status
                                    assert len(response.body())>100
                                    checks.append('export '+extension+report)
                            response=context.request.get(origin+f'/workspace/activities/{event_id}/proposal')
                            assert response.status==200 and response.body().startswith(b'%PDF')
                            checks.append('authorized proposal download')
                            page.goto(origin+'/workspace/overview?year=2026')
                            page.wait_for_load_state('networkidle')
                            page.screenshot(path=str(folder/'director-desktop.png'),full_page=True)
                            page.set_viewport_size({'width':390,'height':844})
                            page.reload()
                            page.wait_for_load_state('networkidle')
                            page.screenshot(path=str(folder/'director-mobile.png'),full_page=True)
                        assert not errors,errors
                        context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=10)
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        (folder/'checks.json').write_text(json.dumps(dict(checks=checks,manifest=manifest),indent=2),encoding='utf-8')
        print(json.dumps(dict(passed=len(checks),evidence=str(folder))))


if __name__=='__main__':
    main()
