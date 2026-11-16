"""Bounded browser checks against the separate seeded local report demonstration."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.report_demo import DEMO_ROOT, LOGIN_EMAILS
from playwright.sync_api import sync_playwright, expect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='http://127.0.0.1:5001')
    parser.add_argument('--credentials', type=Path, default=DEMO_ROOT / 'annual-reports-2025-credentials.json')
    args = parser.parse_args()
    password = json.loads(args.credentials.read_text())['password']
    output = DEMO_ROOT / 'screenshots'
    output.mkdir(exist_ok=True)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for role in ('director', 'coordinator', 'volunteer'):
            context = browser.new_context(viewport=dict(width=1440, height=1000), reduced_motion='reduce')
            page = context.new_page()
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.goto(args.base + '/demo'); page.wait_for_load_state('networkidle')
            expect(page.get_by_role('heading', name='2025 Report Demonstration', exact=True)).to_be_visible()
            page.get_by_role('link', name='Sign In', exact=True).click()
            page.locator('#identifier').fill(LOGIN_EMAILS[role])
            page.locator('#password').fill(password)
            page.get_by_role('button', name='Sign In', exact=True).click()
            page.wait_for_load_state('networkidle')
            paths = [('/demo', 'directory'), ('/workspace/overview?year=2025', 'overview'),
                ('/workspace/reports/results?year=2025', 'summary'),
                ('/workspace/reports/results?year=2025&view=activities', 'activities'),
                ('/workspace/reports/results?year=2025&view=participation', 'participation'),
                ('/workspace/reports/aop?year=2025', 'annual'),
                ('/annual-goals?year=2025', 'indicators'),
                ('/workspace/reports/historical?year=2025', 'historical'),
                ('/workspace/reports/people?year=2025', 'people')]
            if role == 'director':
                paths.append(('/workspace/recognition?award_year=2025', 'recognition'))
            if role == 'volunteer':
                paths = [('/demo','directory'),('/workspace/registrations','registrations')]
            for path, name in paths:
                for width, height in ((1440,1000),(390,844),(320,800)):
                    page.set_viewport_size(dict(width=width,height=height))
                    response = page.goto(args.base+path);page.wait_for_load_state('networkidle')
                    assert response.status == 200, (role,path,response.status)
                    expect(page.locator('.report-demo-notice')).to_be_visible()
                    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), (role,name,width)
                    if name in ('summary','historical'):
                        expect(page.locator('.js-plotly-plot').first).to_be_visible()
                    page.screenshot(path=str(output/f'{role}-{name}-{width}.png'),full_page=True)
                    checks.append([role,name,width])
            if role == 'director':
                page.goto(args.base+'/demo');page.wait_for_load_state('networkidle')
                link = page.get_by_role('link',name='Activity Summary',exact=False)
                link.focus()
                assert link.evaluate('(el)=>el===document.activeElement')
                style = link.evaluate('(el)=>({outline:getComputedStyle(el).outlineStyle,shadow:getComputedStyle(el).boxShadow,height:el.getBoundingClientRect().height})')
                assert style['height'] >= 44 and (style['outline'] != 'none' or style['shadow'] != 'none')
                link.press('Enter');page.wait_for_load_state('networkidle')
                assert 'year=2025' in page.url and 'view=summary' in page.url
                checks.append(['director','directory-keyboard-navigation',320])
                page.goto(args.base+'/workspace/reports/results?year=2025')
                page.wait_for_load_state('networkidle')
                values = page.locator('[data-month-chart]').evaluate('(el)=>JSON.parse(el.dataset.chartValues)')
                labels = page.locator('[data-month-chart]').evaluate('(el)=>JSON.parse(el.dataset.chartLabels)')
                assert len(values)==12 and min(values)>0 and len(labels)==12
                assert sum(values)==204
                page.set_viewport_size(dict(width=844,height=390))
                page.reload();page.wait_for_load_state('networkidle')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1')
                page.screenshot(path=str(output/'director-summary-landscape.png'),full_page=True)
                page.add_style_tag(content='html {font-size:200% !important;}')
                assert not page.evaluate('document.documentElement.scrollWidth > innerWidth+1')
                page.screenshot(path=str(output/'director-summary-text-200.png'),full_page=True)
                page.emulate_media(media='print')
                assert page.locator('.report-demo-notice').is_visible()
                checks.append(['director','charts-landscape-text-print',844])
            context.close()
        browser.close()
    assert not errors, errors
    (output/'results.json').write_text(json.dumps(dict(checks=checks, errors=errors),indent=2))
    print(f'{len(checks)} browser groups passed; screenshots: {output}')


if __name__ == '__main__':
    main()
