# UI polish, search, and guidance verification

Local implementation and review: 13–14 November 2026, on
`codex/ui-workflow-overhaul`. This pass adds no schema migration or dependencies.
It does not change recommendation calculations, report definitions, consent
storage, or attendance write boundaries. No operational database, deployment,
remote branch, or unrelated documentation DOCX was changed.

## Design read

Audience: PSU volunteers, campus Extension Coordinators, and the combined
Director office. Preserve the approved institutional direction: PSU blue
`#00408b`, deep blue `#002b60`, gold `#f4bd27`, white workspaces, slate text, and
Inter. ENERGY 2 / RHYTHM 2 / MOTION 1. Gold identifies the selected destination;
blue identifies actions and activity data. Smaller control radii distinguish
controls from content panels. Shadows are reserved for floating help and tours.

Lists support scanning; dedicated detail screens carry substantial tasks.
Dashboard tiles align the five existing measures and their detail links.
Photography reuses the existing campus cleanup photograph; the authentication
photo is desktop-only so it does not push the phone form below another image.
Guides and help explain existing workflows without introducing another workflow.

Skills applied: UI/UX Pro Max, Ponytail full, Search UX, frontend-design,
antislop during work (session choice), antislop-ui, antislop-human,
antislop-layoutmobile, and Web Design Guidelines. UI/UX Pro Max's institutional
dashboard search informed the restrained direction; its unrelated portfolio
and landing-page suggestions were rejected. Its HTML/Tailwind search returned
no matches, so implementation reuses the established Flask/Jinja components.
Search suggestions, live search, and logging are excluded by the user's plan.

## Implementation

- Shared Tailwind styles cover typography, controls, navigation, loading,
  search/filter states, help disclosures, guide dialogs, and print behavior.
- Child pages retain the selected navigation section. Director chrome identifies
  the university office rather than presenting the account's campus as report scope.
- Shared search controls submit by button or Enter. Search is literal, partial,
  and case-insensitive through SQLAlchemy's escaped contains expressions.
  Highlighting escapes both user content and queries before inserting `mark`.
- Activities, people, registrations, agencies, historical records, and internal
  and external rosters have appropriate search/filter controls. Agencies and
  external rosters are paginated. Upcoming activities use ascending start time;
  past activities use descending time; people and agencies use alphabetical order.
- Chips remove one filter while retaining others and reset pagination. Explicit
  `return_to` URLs preserve list context separately from roster searches. Unsafe
  external, backslash, and control-character return destinations fall back locally.
- Report departments come from the authorized period/campus scope. Existing query
  names and shared export calculations remain in use. Campus chart links select
  conducted activities and reset the report page.
- The existing guide runner and dismissal endpoint support the three current roles.
  Existing dismissal records are retained. Dashboards and Help offer replay.
  Back/Next/Finish/Skip/Escape, save failures, unavailable targets, and focus
  restoration are handled. Guides never click application controls or navigate
  between pages. At large text sizes, long guide cards start at their heading.
- Existing native `details` information tips now have 44px triggers, keyboard,
  touch, outside-click and Escape support, viewport clamping, scrolling, and Help
  links. Metric help triggers are siblings of links, never nested inside them.
  Attendance deadlines, locking warnings, and consent remain visible.
- Required markers are rendered by shared form macros and the touched account
  forms. Native validation gains linked summaries and inline messages. Existing
  server validation remains visible. The submit spinner honors reduced motion.
- The mobile drawer only handles Escape when open. Duplicate confirmation handling
  was removed; shared confirmation handles both form and submitter messages.
  Role changes use an explicit Apply role button instead of automatic submission.

## Verification evidence

- `npm run build`: PASS with pinned Tailwind 4.3.0.
- Complete Jinja template compilation: PASS.
- JavaScript syntax for workspace controls, tour runner, charts, and confirmations:
  PASS. `git diff --check`: PASS.
- Focused workflow/report/profile run: **86 passed**.
- Subsequent workflow and new UI/search run: **55 passed**.
- Final new UI/search/template run: **6 passed**. These runs overlap; do not add
  them together as a unique test count.
- Complete disposable Chromium pass: **204 checks passed**, with no page overflow
  or JavaScript page errors. Coverage includes public/auth, three role workspaces,
  all activity steps, rosters, Reports, imports, settings, profiles, print/PDF,
  draft restoration/submission cleanup, and keyboard mobile navigation.
- Focused polish recheck after the large-text guide correction: **18 checks
  passed**. Exercises literal highlighting, pagination, nested Back navigation,
  individual chip removal, reset, empty recovery, linked native validation,
  failed/recovered draft saves, guide dismissal/replay/failure recovery, missing
  targets, keyboard/touch tips, and focus restoration.
- Final focused browser pass: **19 checks passed**, including the explicit native
  Apply role submission in management. This overlaps the preceding focused pass.
- Layouts: 320, 390, 768, 1024, and 1440px; landscape 844×390; 200% text sizing;
  reduced-motion preference. Help and guide cards remain scrollable at large text.
- Local preview login and dashboard smoke: Director, Coordinator, Volunteer PASS.
- Contrast checker: blue/white **9.97:1**; slate-600/slate-50 **7.24:1**;
  blue-100/deep-blue **11.37:1**. Gold is an identity/selection accent, not body text.

Local evidence is ignored under `.qa-overhaul-temp/browser/`:

- `results.json`, `polish-results.json`, and guide screenshots.
- `before-polish/`: screenshots retained from the earlier local baseline.
- Current `director-1440-workspace-overview.png`, `public-1440-auth-login.png`,
  `coordinator-390-filtered-search.png`, and role/width guide screenshots.
- Existing report print PDF and activity/AOP export PDFs.

Screenshots use disposable seeded records, not institutional performance claims.
Before captures came from the preceding baseline run; they are representative
comparisons, not an identical-data pixel-diff fixture.

## Current Web Interface Guidelines audit

Reviewed changed templates, shared controls, tour/help scripts, and styles against
the [current guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched again on 14 November 2026. Findings addressed:

- `templates/layouts/role_base.html:100` - fixed Escape stealing focus from help.
- `templates/partials/sidebar.html:19` - child-page selection uses shared sections.
- `templates/workspace/components.html:58` - replaced free-text report department
  with scoped choices; delivery selection preserves the corresponding report scope.
- `templates/workspace/overview.html:21` - metric help sits outside metric links;
  links align along a shared row.
- `templates/admin/admin_user_form.html:67` - restored visible affiliation label.
- `templates/admin/Admin_mngmt_dash.html:140` - explicit role submit action;
  campus and search filters use explicit submission and retain each other.
- `static/scripts/workspace.js:40` - inline native errors with linked summaries.
- `static/scripts/workspace.js:65` - tips support Escape and viewport edges.
- `static/scripts/first-use-tour.js:173` - long guide content starts at its heading.
- `ui/app.css:245` - tour/help scroll containment and reduced-motion handling.

Intentional guideline adaptations: retain the approved sentence-case PSU copy,
descriptive search placeholders, and Philippine reporting dates. React hydration
rules do not apply to server-rendered Jinja. Existing Google font delivery uses
swap and a system fallback; offline rendering can use that fallback.

## Antislop delivery gate

Scope: this UI change set and its connected paths; evidence above is not a full
WCAG certification or exhaustive audit of every older repository workflow.

- R-02 PASS: changed interface copy introduces no decorative em dashes.
- R-03 PASS: completed responsive run found no document overflow; table scrolling
  stays contained and guide/help content scrolls at 200% text size.
- R-17 PASS: KPI values still come from existing report queries.
- R-18 PASS: no testimonials added.
- R-23 PASS: reused existing logo, icons, photo, and approved navigation structure.
- R-24 PASS: templates compile and connected route checks resolve actual pages.
- R-25 PASS: shared foreground/background contrast measured above.
- R-26 PASS: native search, chips, Back, guide/help, validation, and submission
  actions have recorded regression or browser checks.
- R-27 PASS: empty search recovery, busy submission, draft and guide failure
  feedback exercised; existing server errors remain readable.
- R-28 PASS: Help covers PSU registration, attendance, reports, drafts, and imports.
- R-32 PASS: keyboard drawer, tour controls, information tips, and focus return
  checked in Chromium; visible focus styles remain shared.
- R-33 PASS: behavior is implemented in versioned Flask/Jinja/JS/CSS source.
- R-34 PASS: approved light theme retained; no unrequested theme switch introduced.
- R-35 PASS: build, rendered screenshots, focused regressions, and connected
  browser click-through completed; repeat-run interruption is recorded below.
- R-36 PASS: no fabricated compliance/performance claims; limitations are explicit.
- R-37 PASS: approved institutional direction and 2/2/1 dials retained.
- R-38 PASS: production measures remain database-derived; QA fixtures identified.
- R-39 PASS: new controls use native elements, names, visible labels, focus,
  loading/error feedback, and reduced-motion handling.
- R-40 PASS: reused photo has explicit dimensions; no new blocking head script.
- Purpose gate PASS: no gradients, glows, glass, generic illustrations, or decorative
  animations added. Navigation icons describe destinations; shadows mark overlays;
  equal KPI columns support comparison; gold identifies current navigation.
- Liveliness PASS: task headings and figures are focal points; list/detail layouts
  establish rhythm; existing PSU identity, Inter, and campus photography remain.
- C-1–C-5 PASS: decisions follow the PSU brief; changed paths have real behavior;
  no filler sections or invented claims; responsive and keyboard evidence above.
- Consistency locks PASS: restrained palette, distinct control/panel radii,
  task-specific labels, existing institutional identity, and no forced dark mode.

## Existing warnings and verification limits

Existing Matplotlib/Pyparsing deprecation warnings occur during PDF export tests;
the exports pass. The complete older repository suite was not rerun; it contains
expectations for workflows replaced by the preceding overhaul. No new regression
failure remains in the focused suites.

A repeat of the full browser run stopped with Windows Chromium
`net::ERR_NO_BUFFER_SPACE` while loading a document screen. This was an
environment-level repeat-run interruption; the earlier complete 204-check pass
and the focused post-fix pass are recorded separately. Do not claim that every
repeat completed. Physical mobile devices, screen-reader combinations, MySQL
deployment behavior, production capacity, and a full WCAG audit remain release
verification work. No production or operational database migration was attempted.

## Reproduce locally

From the repository in PowerShell:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_ui_polish.py tests/test_workspace_overhaul.py --basetemp=.qa-overhaul-temp/ui-polish-tests -p no:cacheprovider -q
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py
```

Browser checks start an isolated in-memory test application. Allow the operating
system to reclaim sockets between repeated full runs. The authorized preview
uses `.qa-overhaul-temp/run_local_preview.py` and its existing private database
copy at `http://127.0.0.1:5000`. Restart it after Python changes; rebuild after
Tailwind changes. Existing preview credentials remain unchanged.

This pass needs no additional migration. The preceding overhaul's migration and
release instructions remain in `docs/operations/UI_WORKSPACE_OVERHAUL.md`.
For a source rollback, review and revert only this polish change set, rebuild
Tailwind, and restart the preview. No draft/database rollback is required for
these presentation/search changes. Publishing remains a separate action.
