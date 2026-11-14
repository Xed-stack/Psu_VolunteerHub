# Reports and Annual Plans: Local Implementation

14 November 2026, branch `codex/ui-workflow-overhaul`.

## Delivered behavior

- Reports is grouped by activity delivery, annual achievement, source records and
  people, with recognition retaining its dedicated Director destination.
- Activity Accomplishments has GET-based Summary, Activity Records and Participation
  Records views. Missing/invalid `view` defaults to Summary. Summary retains the five
  established measures and existing compatible previous-period comparisons; each
  records view has one paginated table. Presentation tabs do not narrow exports.
- `/workspace/reports/activities/<event_id>` provides a read-only combined report
  from the existing authorized dataset. The path ID overrides a forged query ID.
  Named rosters appear after the activity starts and use 25-record pagination;
  exports include the full roster. Participant-filtered measures and the complete
  activity roster are explicitly distinguished. Print This View prints the current
  view/page; Export PDF produces the complete matching report.
- AOP has campus-obligation rollup, separately labelled university targets, campus
  comparison and exact indicator links. Target/actual charts group verified evidence
  by identical unit; pending evidence stays visible as unknown. Annual CSV/Excel/PDF
  include the displayed campus comparison separately from selected-scope targets.
- `/annual-goals/targets/<target_id>` resolves the approved merged obligation, including
  nonrepresentative shared AOP/ASP members. Conflicting definitions/evidence remain
  pending. It shows source/coverage, member-specific authorized evidence/revision
  actions, linked activities and snapshot history.
- Annual indicators use compact rows. Director campus comparison remains available
  as a connected view with the existing plan/program/office refinements. The residual
  live participation-breakdown panel was removed; approved aggregate source evidence
  remains on indicator details. Official exports reject sample figures.
- Evidence, proposal, linked-activity and review screens share the journey hierarchy
  and preserve validated return context. Evidence saves return to the exact indicator.
  Historical and People Insights use the same reporting shell and retain separate data.
- Legacy report redirects retain recognized report views and existing filters.
  Old single-event result URLs remain functional and expose the combined-report link.
  Activity workspace Report tabs and attendance-report actions use the new screen.
- Fixed interface copy uses Newspaper Case; authored titles, departments, definitions,
  sources and existing export column names remain unchanged. Unknown annual actuals
  export as unavailable rather than a misleading provisional value.

Reused existing report/annual services, Plotly, native links/forms and compiled
Tailwind. No new schema, library or calculation definition. Coordinator campus
authorization remains server-side; an unassigned Coordinator is now explicitly
denied university target/detail activity access. Evidence writes remain Director-only.

## Analysis, design and preservation

`REPORT_JOURNEYS_DESIGN.md` records analysis, pre-implementation desktop/mobile
wireframes, tokens, states and the preservation checklist. Codebase-analysis provided
the focused read-only survey; frontend-design/design-system guided composition;
webapp-testing supplied Python Playwright checks. Existing repository antislop and
Ponytail constraints were applied during work. No skills were installed.

| Capability | Destination / Evidence |
|---|---|
| Five KPI definitions and scope | Summary uses existing metrics/services; prior staff/filter/report regressions |
| Literal search, repeated campuses, tabs | Activity Records; browser tab/Enter/highlight/Back checks |
| Complete filtered exports | Shared report_data before pagination; CSV view equality and combined Excel/roster tests |
| Campus/university annual separation | AOP rollup plus separately labelled university targets; shared-obligation/export tests |
| Shared/unknown/conflicting evidence | Exact indicator screen uses merged summary; new conflict/member assertions |
| Evidence and proposal authorization | Existing Director-only writes, Coordinator campus reads/revisions; focused permission checks |
| Samples | Labelled, no official target links; official export/write rejection retained |
| Drafts, attachments and submission cleanup | Existing draft, proposal/upload restoration and successful-submission assertions rerun |
| Withdrawal and attendance boundaries | Direct withdrawal and future/ongoing/ended/legacy/cancelled boundary assertions rerun |
| Historical/people data separation | Existing datasets retained; responsive and doubled-text browser matrix |
| Guide, tips and saving/failure feedback | Existing 23-check polish browser suite |

## Verification and existing failures

Completed runs overlap; do not sum them as unique coverage:

- **28 pytest regressions passed**: minimal filters, staff Overview, UI reimagining
  and report queries. Includes existing export agreement and scope behavior.
- **Five new report-journey tests passed** against fresh in-memory fixtures, directly
  invoking their existing test functions after Windows pytest temporary-directory
  handling became unavailable. Covers view normalization, CSV dataset equality,
  legacy view redirects, full combined roster/Excel, shared conflicts, unassigned
  Coordinator denial, annual rollup/export links, evidence Back and sample isolation.
  Evidence: `direct-fixture-checks.txt`.
- **15 final preservation checks passed** using the same fresh in-memory fixtures:
  draft refresh/isolation/secrets, proposal extraction/resume/publication, staged
  uploads and cleanup, direct withdrawal, existing external attendance locking,
  proposal review/cross-campus permissions, shared revision/history, annual filtered
  pagination, full template compilation and five attendance-window states.
  Evidence: `preservation-fixture-checks.txt`.
- **142 report Chromium checks passed**: Director, Coordinator and representative
  Volunteer; 320, 390, 768, 1440 and landscape 844×390; 200% root text; populated,
  empty and sample scopes; table containment, tab keyboard operation, repeated
  campuses, literal highlighting, roster pagination, exact indicator/evidence Back,
  grouped-unit charts and print PDFs. No document overflow or page script errors.
- **129 existing filter Chromium checks passed** after adjusting its title-highlight
  assertion to explicitly open Activity Records. No page script errors.
- **23 existing polish browser checks passed**, covering guides, tips, draft feedback,
  filtering/pagination and return navigation.
- Final Tailwind build, chart-script syntax, complete template compilation and
  `git diff --check` passed. Print text was verified in the generated three-page
  activity view and four-page annual view PDFs.

Existing failures recorded separately:

1. `test_sample_drilldown_export_isolation_and_all_templates` expects legacy
   `/director_dash` and `/analytics` requests to return 200; those routes intentionally
   redirect and return 302. Their route implementations were not changed in this pass.
2. `test_invalid_targets_and_sample_posts_never_publish` expects validation directly
   on a legacy redirect URL rather than its destination. The initial response is 302.
3. Matplotlib/Pyparsing deprecation warnings remain.

The annual filtered-summary test's old prose assertion was updated to the new
`Goals Achieved: 5 / 11` presentation, retaining the whole-scope-versus-filtered-list
check. New fixture assumptions were corrected (campus ordering and required external
IDs). No application validation was weakened to satisfy those tests.

The final large combined pytest process's completion could not be recovered after
the tool session changed. A retry encountered Windows temporary-directory access
denial. The focused direct-fixture reruns above completed successfully; no claim is
made that the entire historical suite passed.

## UI audit

Reviewed changed templates, route presentation, shared navigation and chart script
against the [current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), fetched 14 November 2026.
User-specified Philippine-time formatting and Newspaper Case remain authoritative.

- Hard gate PASS for tested UI: real authorized links/native controls, chart value
  alternatives, existing labels/focus/errors/saving feedback, no fabricated content,
  no page overflow in the bounded matrix, reduced-motion browser contexts and print
  checks. Read-only report pages introduce no destructive actions.
- Purpose gate PASS: PSU blue identifies navigation/data; restrained gold separates
  annual achievement. No new gradients, glows, icons, imagery, framework or animation.
- Liveliness PASS: energy 2/rhythm 2/motion 1 declared before implementation. Summary
  charts, record tables and evidence-reading layouts have distinct hierarchy; real
  scope and results supply the focal point.
- Craftsmanship PASS for tested UI: existing services and definitions reused;
  source-backed counts, shared obligations and unknown evidence preserved. Visual
  review found shared mutable Plotly axis configuration; each plot now receives an
  independent layout. A browser assertion verifies numeric delivery-axis direction.
  People Insights overflow at doubled text was contained in a labelled keyboard
  scroll region. Evidence history tolerates missing coverage dates.

Physical-device, screen-reader, production-load and every browser's native zoom
behavior were not certified. Print This View is page-local; use PDF/Excel/CSV for
complete matching records. The private-preview refresh remains blocked as below.

## Preview, artifacts and remaining local action

**The private preview is currently stopped.** Its restart was rejected because
automatic approval review hit a usage limit and could not complete. The tool stated
this was a review-service failure, not a determination that the action was unsafe.
The approval check was not bypassed. The old preview was stopped before this failure.

When local execution is available, run from the repository:

```powershell
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Then open `http://127.0.0.1:5000` and sign in again. The launcher reuses the existing
private preview database/uploads, suppresses mail, and does not reseed. Accounts:
`director@psu.edu`, `coordinator@psu.edu`, `student@psu.edu`; password `password`.

Artifacts under `.qa-overhaul-temp/report-journeys/`:

- `before/`: pre-change private-preview report/annual/indicator/empty screens at
  desktop and phone sizes.
- `browser/`: populated disposable-fixture after screenshots, print PDFs and final
  `results.json` (142 checks). These fixture counts are not institutional data.
- `before-source/` and `source-review.patch`: scoped source rollback references.
- `direct-fixture-checks.txt`, `preservation-fixture-checks.txt`: completed final
  assertion evidence. `pytest-final.txt` records the Windows access failure.

Matching post-change private-preview screenshots are **not yet captured**, because
the restart was blocked. Capture after restart with:

```powershell
.venv/Scripts/python.exe scripts/qa_reports_preview.py --stage after
```

Build and standard QA commands:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_report_journeys.py tests/test_workspace_overhaul.py tests/test_activity_journeys.py tests/test_minimal_filters.py tests/test_staff_overview.py tests/test_ui_reimagining.py tests/test_report_queries.py -q
.venv/Scripts/python.exe -m pytest tests/test_annual_goals.py -q
.venv/Scripts/python.exe scripts/qa_report_journeys.py
.venv/Scripts/python.exe scripts/qa_minimal_filters.py
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
```

For rollback, save current work, restore only this pass's touched existing files
from `before-source/`, remove only its new report partial/detail templates/tests/QA
scripts/docs if desired, rebuild Tailwind and restart the isolated preview. One
backup for the existing filter QA script is named `scripts-qa_minimal_filters.py`.
Do not blanket reset/clean the mixed working tree. No database rollback is needed.

No commit, push, deployment, operational database change, schema migration, new
application dependency, generated imagery or broad cleanup was performed. Existing
working changes and the unrelated DOCX remain preserved.
