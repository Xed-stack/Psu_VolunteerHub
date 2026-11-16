# Help Center and Sticky Header — 15 November 2026

## Analysis and design before implementation

The application header is in `layouts/role_base.html`; `.role-topbar` is normal
flow. Sidebar/overlay layers are 50/40 and bottom navigation is 30. Keep the sticky
header at layer 20, below those controls and native dialog top layers. Its actual
height must drive anchor/focus offsets because campus labels, actions and text sizing
change it. Public/authentication headers remain unchanged. Print hides the header.

`/help` currently renders `workspace/help.html` through the public shell, even for
signed-in users. It shows all roles together and loses the application navigation.
The unused `templates/help.html` contains obsolete cancellation and attendance copy;
retire it after reference verification. Preserve the existing dashboard guide runner,
dismissal records, inactivity handling and read-only Help behavior.

Design read: campus volunteers and Extension staff need task answers and a reliable
return path. PSU blue/gold and Inter remain. ENERGY 2 / RHYTHM 2 / MOTION 1.
Use a compact title/search workspace, short quick-task links and grouped topic rows,
not repeated decorative cards. Articles are focused readable pages with steps,
visible restrictions, related topics and relevant authorized actions.

Desktop: app header → Help heading / guide replay → search → quick tasks → grouped
topic links; articles use a restrained reading width and clear Back to Help.
Mobile: stacked search/action, wrapping quick links, full-width topic rows. One main
landmark per shell; visible focus and 44px controls. No new imagery or animation.

Content is source-controlled, role filtered, searched literally, and never generated
from user data. Public/common topics plus role-specific articles cover the approved
plan. Support instructions contain no invented contacts, tickets or response promises.

## Implementation and feature coverage

- Signed-in `.role-topbar` is sticky at layer 20 with opaque white/border styling.
  Titles/campus labels allow two lines each; essential controls remain 44px. Sidebar,
  bottom navigation, overlays and native dialogs retain their established layers.
- `sticky-header.js` uses ResizeObserver for the actual header height, root scroll
  padding, direct-fragment alignment and recovery of covered validation focus. No
  scroll listener, auto-hide animation or additional application navigation was added.
- `/help` and `/help/<slug>` share the role-filtered source catalog in
  `app/help_center.py`. Signed-in Help uses the role shell and selected Help navigation;
  public Help retains a separate public shell. Each shell has one main landmark.
- **25 topics**: public sees 6; Volunteer 14; Coordinator 18; Director 15. Role task
  groups appear before shared basics. Search covers visible titles, summaries, keywords,
  steps and warnings with literal case-insensitive matching and escaped output.
- Article links retain q; Back to Help restores it. Related topics/action links are
  independently audience-filtered. Unknown/unauthorized articles return 404.
- Public/common coverage: getting started, sign-in, recovery, campus, privacy and
  participation agreements, support. Shared signed-in coverage: drafts/uploads,
  notifications/guides, filtering/Back links and missing records.
- Volunteer coverage: interest recommendations, calendar/default view, registration,
  consent, capacity, withdrawal deadlines, historical decisions, attendance evidence,
  profile interests/skills. Coordinator coverage: approved proposals, extraction,
  covers, audiences, Partners/MOAs, external groups, recording boundaries/cancellation.
  Staff/Director coverage: scope/KPIs, Reports, annual evidence, campus follow-up,
  account guards and staged full-file imports.
- Contextual tips now link directly to applicable articles where mapped; custom links
  remain intact and forbidden articles are never added. Essential rules stay visible.
- Guide replay uses the existing runner. Help itself does not alter guide preference
  or operational database records. No support contacts, tickets or response times were
  fabricated. The unused obsolete Help template was removed after reference search.

## Verification — 15 November 2026

- `pytest tests/test_help_header.py -q`: **16 passed**, including all article/audience
  combinations, single-main structure, selected navigation, literal/escaped search,
  q preservation, hidden content, valid URLs, contextual tips, GET-only methods and
  SQL write detection/guide preference preservation.
- Session-idle + UI-polish regressions: **25 passed; 1 existing failure**. The failure
  is `test_exact_timeout_all_roles_clears_auth_and_explains[admin]`: its fixture tries
  to create the removed Admin enum before reaching application logic. The Volunteer,
  Coordinator and Director cases passed. No broad fixture rewrite was performed.
- Chromium: **27 check groups passed**, no page errors. Public/all roles at 320, 390,
  768, 844 landscape and 1440px; articles, query Back, Enter search/empty recovery,
  sticky position, menu/Tab/Escape focus, direct fragments, 200% text and long header
  labels, replay/Escape, dashboards, Reports, lists/forms, real validation-summary/input
  focus, information tips, inactivity modal/Stay Signed In, and print captures.
  Before evidence: 20 layout checks/captures. Header is hidden in print.
- Tailwind build, **115 compiled Jinja templates**, sticky script syntax and
  `git diff --check` passed. The template count falls by one because obsolete Help
  was removed; current Help was replaced in place.
- Contrast: PSU blue/white **9.97:1**, slate-600/slate-50 **7.24:1**, ink/amber-50
  **16.51:1**. All pass normal-text AA.
- Live preview smoke: existing Director, Coordinator and Volunteer sign-ins, Help and
  their role article returned 200. Public Help returned 200 without the sticky script.

An initial test selected the navigation link by text without accounting for its icon;
corrected the selector to its href/class. No application behavior was changed for it.
The previously documented historical fixture/redirect failures remain separate from
this pass. No full historical-suite claim. No physical-device/manual screen-reader
session; viewport/touch/keyboard/200% checks use Chromium emulation.

## Audit and delivery gate

Reviewed changed UI against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched 15 November 2026. Verified native links/buttons, labelled search, visible focus,
role-filtered destinations, empty recovery, meaningful headings/one main, scrolling
offsets, modal layering, no new motion and print. No unresolved changed-screen findings.

Antislop during-work gate: ENERGY 2 / RHYTHM 2 / MOTION 1, consistent with the design
read. A role-specific task directory supplies hierarchy, focused articles supply
reading space, and blue navigation/gold notice emphasis reuse PSU identity. Every
new control has a real destination or action; content describes existing behavior.
No generated assets, decoration, fake statistics or support promises were added.

## Review and reproduction

Open `http://127.0.0.1:5000/help`. Public visitors see account/getting-started topics.
Signed-in accounts: Director `director@psu.edu`, Coordinator `coordinator@psu.edu`,
Volunteer `student@psu.edu`, each password `password`. Sign in again after restart.
Scroll Help or a long workspace to review the sticky header; open a topic, search,
use Back to Help and replay the dashboard guide. Existing private preview data and
uploads are retained, and mail remains suppressed.

Evidence: `.qa-overhaul-temp/help-header/before/` and `after/`. Files include each
role's `*-1440.png`/`*-390.png`, article, 200%, scrolled-workspace and print screenshots,
plus `results.json`. These private generated artifacts remain ignored.

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_help_header.py -q
.venv/Scripts/python.exe scripts/qa_help_header.py --stage after
```

Local launcher: `.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py`.
QA uses disposable fixtures; live smoke does not create activity/agency/import records.

## Scoped rollback

Preserve the prior uncommitted Accounts/Imports and Partners/MOAs work. Copy the current
diff/new files first. Reverse only this pass's Help handler, Help navigation metadata,
sidebar Help item, info-tip article helper integration, role-layout sticky script load,
sticky/Help styles and replacement Help template. Restore the former unused template
only if reverting its retirement. Remove only this pass's catalog, sticky script,
focused tests and QA runner as appropriate. Rebuild Tailwind and restart the preview.
Do not restore whole shared files from the published baseline or reset the branch.
No migrations, new libraries, commits, pushes, deployment or operational DB changes.
