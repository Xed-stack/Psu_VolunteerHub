"""Capture the unchanged private preview before/after activity journey changes."""
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['before', 'after'], required=True)
    args = parser.parse_args()
    out = Path('.qa-overhaul-temp/activity-journeys') / args.stage
    out.mkdir(parents=True, exist_ok=True)
    base = 'http://127.0.0.1:5000'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for role, email, home in [('volunteer', 'student@psu.edu', '/volunteer_dash'),
                                 ('coordinator', 'coordinator@psu.edu', '/workspace/overview')]:
            context = browser.new_context(viewport={'width': 1440, 'height': 1000})
            page = context.new_page()
            page.goto(base + '/auth/login')
            page.locator('[name=identifier]').fill(email)
            page.locator('[name=password]').fill('password')
            page.get_by_role('button', name='Sign In', exact=True).click()
            page.wait_for_url('**' + home)
            paths = [home, '/opportunities'] if role == 'volunteer' else ['/workspace/activities']
            page.goto(base + paths[-1]); page.wait_for_load_state('networkidle')
            selector = 'a[href^="/opportunities/"]' if role == 'volunteer' else 'a[href^="/workspace/activities/"]'
            links = page.locator(selector).evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("href"))')
            if links:
                paths.append(links[0])
            for width, height in [(1440, 1000), (390, 844)]:
                page.set_viewport_size({'width': width, 'height': height})
                for index, path in enumerate(paths):
                    response = page.goto(base + path)
                    page.wait_for_load_state('networkidle')
                    assert response.status == 200, (role, path, response.status)
                    page.screenshot(path=str(out / f'{role}-{index}-{width}.png'), full_page=True)
            context.close()
        browser.close()
    print(f'Private preview screenshots: {out}')


if __name__ == '__main__':
    main()
