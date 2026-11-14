# Activity Journeys: Local Delivery

14 November 2026. Local branch: `codex/ui-workflow-overhaul`.

## Delivered

- Compact Volunteer heading; recommendations/calendar remain primary, with a
  contrasting commitments rail, recent participation below and a supporting Profile
  link. The existing default-view and ranking rules are unchanged.
- Phone calendar has a chronological agenda using the same registrations as the
  desktop month grid. Previous/Next month links remain available in both layouts.
- Discovery now uses schedule rows with readable metadata and availability. Existing
  covers are optional; absent covers do not reserve an empty thumbnail column.
- Volunteer details, review/consent, registration, withdrawal and staff activity
  overview use consistent headings, facts and next-action areas. Registration status,
  activity lifecycle, schedule progress and recorded attendance remain separate.
- Registered details open the actual registration. Successful joining and withdrawal
  land on that record. Discovery filters, repeated campus choices and history return
  context survive the connected journey. Back links use the existing validated helper.
- Cancelled activities show cancellation explanations; zero capacity is shown as no
  capacity limit, matching the existing registration checks. Only the built-in default
  agreement copy changed to direct withdrawal; authored/published agreements did not.
- Staff workspace tabs retain the connected destinations. Duplicate action stacks and
  the duplicate title on the root activity overview were removed. Upcoming Coordinator
  activities offer Edit; ongoing activities offer Record Attendance; ended activities
  offer Report and explain printed corrections. Legacy end-time warnings remain.
- Recommendation presentation fields/campus are eager loaded with the existing
  candidate query; no new ranking algorithm or metrics were introduced.
- Removed the unused CSS for the replaced welcome banner, opportunity cards and
  old detail grid after checking active template/script references. This is scoped
  replacement cleanup, not a broad dead-code pass.

Analysis, pre-implementation wireframes, tokens and component states are in
`ACTIVITY_JOURNEYS_DESIGN.md`. Codebase-analysis supplied a read-only journey survey;
frontend-design/design-system guided composition; Search UX informed retained search
behavior; webapp-testing supplied Python Playwright verification. Repository
Ponytail/antislop constraints were applied during work; no skills were installed.

## Preservation evidence

| Capability | Visible Destination and Return Path | Verification |
|---|---|---|
| Ranked recommendations and preferred campus | Dashboard → activity → Back to Dashboard | Existing recommendation tests; browser recommended/default views |
| Calendar and commitments | Dashboard Calendar → registration; month navigation | Desktop grid/mobile agenda checks with identical source data |
| Discovery refinements | Activities → detail → review → registration → withdrawal → original list | New end-to-end browser path retains search/repeated campuses; existing literal-search/paging tests |
| History filters | My Registrations → registration → withdrawal → registration → original history | Existing history tests; context regression |
| Consent/NDA | Detail → Review and Join → registration | Required validation, fresh GET unchecked, no draft status, accepted policy versions recorded |
| Withdrawal and historical decisions | Registration → Withdraw confirmation; historical decision below current record | Deadline/withdrawal/history regressions; browser confirm/keep paths |
| Staff registrations and rosters | Activity Workspace tabs → Registrations/Attendance → internal/external rosters → Back | Connected-screen regressions and existing browser filter/Back path |
| Documents and reports | Activity Workspace tabs → Documents and Updates / Report | Existing connected-screen/export tests; retained authorized routes |
| Editing, proposal and cancellation | Activity Overview → Edit, proposal download, cancellation disclosure | Workflow/publication/cancellation regressions; state-specific action tests |
| Drafts and upload retention | Existing Create Activity and form draft screens | Existing draft isolation, upload resume, submission cleanup and failed-save browser checks |
| Campus isolation and attendance locks | Existing authorized routes, every attendance write boundary unchanged | Focused workflow boundary and isolation tests |
| Guides and information tips | Dashboard Show Dashboard Guide; interest/capacity help | Replay/Escape/focus and existing first-use/dismissal/tip browser checks |

## Verification

Completed runs overlap; do not add their counts as unique coverage:

- **68 passed**: new activity-journey tests plus workspace-overhaul, UI-polish and
  UI-reimagining regressions. Includes drafts/uploads, consent, recommendations,
  permanent cancellation, direct withdrawal, attendance windows, reports/exports,
  history, authorization and complete template compilation.
- **12 passed**: existing minimal-filter and staff-Overview regressions.
- **6 passed** final: new journey regressions and complete template compilation
  after the final activity-context/navigation changes.
- **113 final Chromium checks passed**: Volunteer/Coordinator/public/Director and
  empty-profile screens; 1440, 768, 390, 320 and landscape 844×390; 200% root text;
  existing cover and missing-cover layouts; long title; cancelled/legacy/ended/ongoing
  states; consent refresh, join/withdrawal/return context, guide Escape focus, phone
  calendar equivalence and registration print PDF. No page script errors or document
  overflow. Supersedes the earlier 95-check run.
- **23 existing browser checks passed**: guide preferences/replay, information tips,
  draft restore/failure feedback and filter/pagination/Back navigation. The old
  Internal Attendance duplicate-link selector now uses the retained Attendance tab.
- Tailwind build, guide-script syntax check and `git diff --check` passed.
- Computed contrast: PSU #00408b on blue-50 #eff6ff **9.16:1**; ink #111c2c on gold
  #f4bd27 **9.91:1**. Shared focus/controls reuse the existing audited tokens.

Initial failures were corrected: one duplicated Jinja cover conditional; two test
expectations (checkbox prose accidentally matching `checked`, campus 404 versus 403);
a browser wait expecting a closed guide to be visible; and the obsolete duplicate
attendance-link selector. These are not remaining application failures.

## UI audit and delivery gate

Reviewed changed templates, shared context, guide copy and scoped Tailwind source
against the [current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), fetched 14 November 2026.
Fixed the duplicated heading and obsolete navigation expectation during review.
Explicit Philippine-time server formatting and the user's Newspaper Case policy
take precedence over generic locale/copy suggestions.

- Hard gate PASS: native controls/links and real authorized destinations; responsive
  matrix and doubled text without document overflow; cover dimensions/alt text;
  no fictional statistics, assets or testimonials; visible consent/deadlines and
  existing validation, empty, saving/failure and focus states retained. Browser
  interactions exercise primary join, keep, withdraw, guide and calendar actions;
  existing suites exercise filter, draft and staff workflow actions.
- Purpose gate PASS: no added gradients, glows, decorative icons, stock imagery or
  animation. Pale blue distinguishes commitments/participation; gold identifies the
  participation action; ruled sections separate facts and narrative.
- Liveliness PASS: energy 2/rhythm 2/motion 1 declared before implementation. Actual
  activity title/schedule is the focal point; schedule lists, facts and reading
  columns have different layouts; PSU blue and the existing gold-topped date motif
  supply identity without repeated welcome panels.
- Craftsmanship PASS: existing services and native behavior reused; authored names,
  titles and agreements unchanged; all changed screens built/rendered and reviewed;
  evidence, permission and attendance semantics retained. Scoped source backups
  and regression evidence support local rollback.

Limitations: bounded Chromium checks are not physical-device or screen-reader
certification. 200% root text is a text-size stress test, not every browser's native
zoom implementation. Print PDF was generated and its deadline/participation text
verified; no physical printer test. The full historical test suite and production
load testing were not run. Existing Matplotlib/Pyparsing deprecation warnings remain.

## Review, artifacts and rollback

Preview: `http://127.0.0.1:5000`. Sign in again after restart. Accounts:
`student@psu.edu`, `coordinator@psu.edu`, `director@psu.edu`; password `password`.
The existing private database/uploads are reused without reseeding; mail is suppressed.

Artifacts under `.qa-overhaul-temp/activity-journeys/`:

- `before/` and `after/`: matching private-preview dashboard/discovery/detail/staff
  captures at desktop and phone widths. These are existing preview data.
- `browser/`: separate disposable-fixture screenshots, print PDF and final
  `results.json`. Fixture titles/counts must never be reported as institutional data.
- `before-source/`: exact pre-pass copies of touched existing source files and CSS;
  `source-review.patch`: scoped source comparison (CSS source reviewed separately).

Commands:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_activity_journeys.py tests/test_workspace_overhaul.py tests/test_ui_polish.py tests/test_ui_reimagining.py -q
.venv/Scripts/python.exe -m pytest tests/test_minimal_filters.py tests/test_staff_overview.py -q
.venv/Scripts/python.exe scripts/qa_activity_journeys.py
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe scripts/qa_activity_journey_preview.py --stage after
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Stop the existing preview before restarting it. For rollback, save current work,
restore only this pass's touched files from `before-source/`, remove only its new
tests/QA scripts/docs if desired, rebuild Tailwind and restart the isolated preview.
Do not reset/clean the mixed working tree. No database rollback is necessary.

No commit, push, deployment, operational database change, schema migration, new
application dependency, generated imagery or unrelated cleanup was performed.
