# Opportunities, details and joining QA

Publication follow-up: the user approved commit/push on 22 October 2026. The
local-only statements below describe the verification snapshot, not a permanent
publication restriction. See RELEASE_2026_10_22.md; verify Git publication separately.

Date: 22 October 2026. Local implementation only; no commit, push, deployment,
schema/dependency changes, live data seeding or original MySQL database writes.
The disposable browser preview used the testing factory, in-memory SQLite and
clearly synthetic users/activity text with explicitly non-binding QA agreements.

## Scope and design read

The audience is PSU volunteers deciding whether they can attend an activity.
The focal point is the activity title and schedule, not promotional decoration.
Inter matches the existing dashboards; PSU blue #00408b identifies actions and
fact labels, white surfaces separate facts from requirements, and background
#f9f9ff keeps continuity with the institutional shell. Text #111c2c and error
#ba1a1a retain readable contrast. ENERGY 1 / RHYTHM 2 / MOTION 1.

Ponytail full reused native forms/details/checkboxes, the existing joining route,
shared loading state, role shell and styles. No filtering framework, drawer,
duplicated form, persistent draft, dependency or new global stylesheet was added.
Frontend-design informed facts-first hierarchy, left alignment and the desktop
joining summary; Anti Slop was applied during implementation. Mobile stacks facts,
participation and description in that order, with actions in normal flow.

## Automated verification

- Final focused run: **43 passed in 111.42s**, zero failures. Command:
  `.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/test_opportunity_journey.py tests/test_app.py::TestSearchFilterPagination`
  with an external disposable `--basetemp`.
- Uninterrupted full suite: **413 passed, 3 failed in 1033.25s** (416 total).
  All three failures reproduce on an untouched `git archive HEAD` extraction of
  committed baseline **21a0545**, using the same isolated testing factory:
  - `TestReportingSystem::test_director_campus_paging_and_supplementary_forms`:
    expects two hidden campus fields, but the current separated report views
    render one in the live view.
  - `TestAnalytics::test_report_pagination_and_exports_preserve_all_selected_filters`:
    expects historical `start_year` on live report links, where it is absent.
  - `test_profile_repair.py::test_milestones_require_completed_present`:
    expects literal `<td>Eligible</td>`; the existing responsive table has cell
    attributes. The completed/present count assertions pass before this failure.
  These are baseline report/profile verification issues, not a green full run;
  unrelated application behavior and assertions were left unchanged. The baseline
  comparison ran only those three cases, not another entire suite.
- Final shared UI structure checks: **6 passed in 0.03s**. Both changed scripts
  passed `node --check`. `git diff --check` passed (line-ending warnings only).
- Coverage includes anonymous read-only details, all four roles, unknown IDs,
  POST rejection on details, safe sign-in destination and repeated campus keys,
  consent restoration/version records, missing NDA consent, cancelled-registration
  restoration, duplicate POSTs, full/started/existing-registration GET/POST guards,
  changed availability, expired session, escaped/long/missing data, legacy zero
  capacity, result counts, out-of-range pages, ordering and filter pagination.
- Existing UI assertions were updated only for intended links, truthful result
  ranges and redirects. Earlier exploratory runs exposed stale markup assertions
  and a test selector that selected the logout form; these were corrected, not
  bypassed. No authorization or consent requirement was removed to pass tests.

## Browser evidence

Disposable preview: `127.0.0.1:5071`, never the original application/database.

- Anonymous listing to details to sign-in returned to the same consent endpoint
  with search/category/campus context intact. Back links retain that context.
- Volunteer joined the explicitly non-binding synthetic activity; confirmation
  named the activity, remaining capacity changed 20 to 19, and My registrations
  opened the dashboard record. Refresh kept Registered without another POST.
- Coordinator, Director and Admin each saw the existing role shell and the
  volunteer-account notice, not an actionable joining link.
- Native missing-consent validation focused `accept_agreement`; submitted valid
  checkboxes and server-rendered error associations are also covered by tests.
- Listing, details, consent and registered confirmation were checked at 320,
  390, 768 and 1440 CSS pixels. Document scroll widths stayed within viewport
  widths. Listing columns reflowed 1/1/2/3. Details stacked below 48rem and placed
  the joining summary beside facts above that breakpoint.
- Checkbox label targets measured at least 44px; consent labels ranged 47–80px.
  Card titles, View details, Back links and primary actions have 44px minima.
- Campus inclusion returned four Lingayen activities; exclusion returned five
  others. An unmatched search showed a specific recovery state.
- With JavaScript actually disabled through the development browser capability,
  the listing rendered, a native checkbox was toggled using browser input, and
  the GET form submitted repeated campus keys. The server returned the selected
  campuses and accurate summary. JavaScript was restored after this test.
- Tab reached the visible skip link; Enter focused main content. Native controls
  and links retain keyboard operation; required-checkbox focus was observed.

Screenshots are outside Git under:
`C:/Users/arlro/.codex/visualizations/2026/10/18/01a14c77-a036-7241-ad82-ee16a46acd99/opportunity-20261022/`.
Files include `listing-{320,390,768,1440}.jpg`,
`details-{320,390,768,1440}.jpg`, `consent-{320,390,768,1440}.jpg`,
`confirmation-{320,390,768,1440}.jpg`, and `native-filter-no-js.jpg`.
Full-page captures may include extra browser capture whitespace; viewport details
captures and DOM width measurements were used to judge layout.

## Web Interface Guidelines audit

Fetched the current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
on 22 October 2026. Reviewed the changed listing/details/consent templates, shared
partials, homepage links, shared styles and scripts.

- Semantic headings, anchors for navigation, labelled native filters/checkboxes,
  skip links, visible focus and text-based states retained or added.
- Card images have dimensions; the below-fold details cover is lazy-loaded.
  Missing covers omit broken images or use the existing restrained fallback.
- Errors have inline associations, a linked summary and first-invalid focus.
  Agreement/NDA choices are unchecked on GET; shared loading/busy behavior remains.
- Filter state lives in URLs. Return links are generated server-side from only
  page/search/category/campus/campus_mode, never arbitrary return URLs.
- No new animation; card-lift motion was removed. Long text wraps; no fixed join
  bars, drawers or dependency-based controls were introduced.
- Audit repair: inherited white success text on #2f8f5b measured only **4.04:1**.
  On the changed activity pages, success now uses PSU blue and messages are in
  document flow to avoid covering content. Other pages were not redesigned.
- Skill contrast checker: blue/white **9.97:1**, red/white **6.46:1**, body text
  on #f9f9ff **16.33:1**; all meet normal-text AA. Existing token-based muted text
  and native control styling remain, with no text over photographs.

## Anti Slop delivery gate and limitations

- Hard gate: no invented statistics, trust claims, fictional testimonials,
  dead navigation, new visual assets, fake status buttons, decoration-only motion
  or observed overflow. Synthetic QA content is explicitly labelled and external
  to the repository/database. Error, empty, selected, loading and success states
  have concrete behavior. No theme toggle was introduced.
- Purpose gate: listing cards compare activities; details panels separate facts,
  requirements and participation. PSU blue, Inter and local covers serve continuity
  with the institution. Whitespace groups decisions; no glass, glow, decorative
  grids, illustration library or excessive new ornament was added.
- Liveliness: title/schedule and the participation action are the focal points;
  repeated PSU fact labels and campus/activity content provide identity. The
  declared restrained dials are retained, not a new generic marketing theme.
- Craftsmanship: security/consent branches have runnable isolated checks, sources
  are escaped, no arbitrary return URLs are accepted, and native behavior covers
  the journey without inventing a second interaction model.
- Actual 200% browser zoom was attempted with Ctrl+Plus, but the embedded browser
  did not change zoom (viewport and device-pixel ratio unchanged). Narrow-width
  checks are not claimed as an actual zoom pass. Physical phone/on-screen keyboard
  and assistive screen-reader checks were unavailable. These remain manual release
  checks, not evidence of verified device or screen-reader conformance.
- Expired consent and changed availability are verified in isolated server tests,
  not by waiting 30 minutes in the browser. No unsaved-choice preservation is claimed.
- Existing concurrent last-slot races are outside this UI change; sequential stale
  and duplicate submissions are tested. No new transaction/locking policy was added.

Next safe step: user review of these local changes and the outstanding manual
device/zoom checks. Investigate and reconcile the three baseline assertions with
the approved separated-report/responsive-table contracts before a green release
claim. Publication requires a new explicit request.
