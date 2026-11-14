"""Capture before/after reports using existing private-preview data only."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['before','after'],required=True);args=parser.parse_args()
    out=Path('.qa-overhaul-temp/report-journeys')/args.stage;out.mkdir(parents=True,exist_ok=True)
    base='http://127.0.0.1:5000'
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for role in ['director','coordinator']:
            c=browser.new_context();page=c.new_page();page.goto(base+'/auth/login')
            page.locator('[name=identifier]').fill(role+'@psu.edu');page.locator('[name=password]').fill('password')
            page.get_by_role('button',name='Sign In',exact=True).click();page.wait_for_url('**/workspace/overview')
            for width,height in [(1440,1000),(390,844)]:
                page.set_viewport_size(dict(width=width,height=height))
                for name,path in [('directory','/workspace/reports'),('results','/workspace/reports/results?period=all'),('annual','/workspace/reports/aop'),('indicators','/annual-goals'),('empty','/workspace/reports/results?activity_name=NoMatchingPreviewActivity')]:
                    response=page.goto(base+path);page.wait_for_load_state('networkidle');assert response.status==200,(role,path,response.status)
                    page.screenshot(path=str(out/f'{role}-{name}-{width}.png'),full_page=True)
            c.close()
        browser.close()
    print('Private preview report screenshots:',out)


if __name__=='__main__':main()
