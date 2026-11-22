# Dashboard and Report Visualizations

Local delivery, 22 November 2026, on `codex/ui-workflow-overhaul`.

Skills applied: UI/UX Pro Max (chart guidance and interaction direction), Frontend
Design (PSU composition), Design Critique (analysis/proposal/rendered review),
Ponytail full (shared patterns), Antislop core/UI/human/mobile during work,
Web Design Guidelines, Webapp Testing, and PDF (export rendering and inspection).

## Analysis and Approved Direction

The canonical staff screens are `/workspace/overview` and
`/workspace/reports/results`; old analytics screens are historical implementations.
The Overview lacked sex-disaggregated participation, the Coordinator had no charts,
and the Director campus table made delivery comparisons difficult to scan.
The shared workspace report already supplied authorized activity rows, attendance
facts, date scope, annual evidence, and pre-pagination aggregates. Reuse those facts.

Design read: institutional reporting for PSU Directors and campus Coordinators.
Energy 2, Rhythm 2, Motion 1. Existing Inter, PSU blue/deep blue, white/slate surfaces,
and the existing restrained gold identity remain. Horizontal bars compare counts;
the existing line chart retains delivery trends. Color never encodes sex.

The user approved verified attendance (repeats per activity), both PSU and external
participants, matching downloads, and broadening Recorded Sex to both types.
Affiliation continues to restrict participant counts to PSU accounts.

## Implementation and Preservation

- Conditional counts join account/external sex in the existing batched report
  query. Four groups keep missing sex distinct from Prefer Not to Say. No roster
  multiplication or per-activity query was added (two aggregate-service queries
  for both small and expanded activity fixtures).
- Only confirmed/completed registrations with recorded presence at conducted,
  approved activities contribute. Unknown ends, future/ongoing activities,
  cancelled/pending registrations, and system defaults do not verify attendance.
- Per-activity groups roll up before screen pagination and reconcile with the
  scoped Verified Attendees headline. Existing whole-event recording checks,
  rates, participant-filtered target restrictions, and annual evidence remain.
- Director: sorted campus bars beside annual achievement; the complete existing
  campus table is inside native, initially closed Expand Campus Details. Delivery
  and verified-sex panels follow, then the existing follow-up findings.
- Coordinator: schedule, actions, follow-ups and annual plan remain; shared delivery
  and verified-sex panels are added below. The breakdown also appears in Summary,
  Participation Records, and Combined Activity Reports. Activity Records stays focused.
- CSV retains existing fields and appends four Verified Attendance columns. Excel
  adds matching activity columns and a Verified Attendance by Sex sheet/chart. PDF
  adds a grouped heading, explanation, chart, counts, shares, and total on one page.
- Native disclosures expose values without JavaScript. Failed/missing Plotly leaves
  explanatory text and real tables. Print opens campus/delivery details temporarily,
  then restores their state; verified-sex values print as readable text.
- Existing routes, role scope, contextual links, five KPIs, annual distinctions,
  roster scope, drafts, and operational attendance policy remain. No schema,
  dependency, operational database, commit, push, or deployment change.

## Design Critique and Audit

| Severity | Finding | Resolution |
| --- | --- | --- |
| High | Required participation breakdown absent | One shared, scoped calculation and presentation for both staff roles and downloads |
| Moderate | Campus table dominates first comparison | Sorted, directly labelled bars; existing table under keyboard-operable disclosure |
| Moderate | Coordinator lacks visual delivery context | Shared delivery and verified-sex panels without replacing schedule/actions |
| Moderate | One long chart label increases every row height | Row spacing accommodates each label independently; names wrap |
| Moderate | Rapid viewport/text resize can retain an oversized Plotly canvas | Explicit parent width plus observed responsive layout updates; old 200% test passes |
| Moderate | PDF heading can separate from chart/values | Keep the new section together; rendered final sample verified |

Optional preferences deliberately omitted: new chart libraries, decorative
animation, sex-specific colors, new themes, and unrelated dashboard restructuring.

Reviewed changed UI against the current Web Design Guidelines fetched from
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md.
The native disclosure is transient local presentation state, closed on a fresh
page; existing GET filters and contextual links retain shareable report scope.
Plotly graphics remain hidden from assistive technology; equivalent native tables
and links provide the complete values and navigation. No in-scope audit finding
remains. This is not a site-wide WCAG certification.

## Verification

- Initial focused regression: 21 passed across new verified-sex tests, staff
  Overview tests, and report journeys.
- Final broader regression: **116 passed** across verified-sex reporting,
  attendance repairs, year-demo reports, Help, and workspace permissions/drafts/
  exports. One final export follow-up passed after label/Excel-chart refinement.
  Runs overlap; these counts are not a sum of unique tests. Only existing
  Matplotlib/Pyparsing deprecation warnings were emitted.
- `scripts/qa_verified_sex_reports.py`: 52 browser groups passed, both roles,
  Overview/Summary/Participation, 1440/1024/768/390/320px, real plots and exact
  totals, native disclosure keyboard/focus, live resizing, 200% text, long rendered
  labels, single-category/empty states, Combined Activity Report, print restoration,
  and PDF/Excel/CSV downloads. Plotly-blocked and all-JavaScript-disabled text
  fallbacks passed. Zero page errors. Synthetic fixtures use in-memory SQLite,
  CSRF enabled; long names are substituted only in rendered QA responses so the
  official campus catalogue and its annual evidence remain valid.
- Existing `scripts/qa_staff_overview.py`: 27 groups passed after the resize repair,
  including agenda actions, guides, contextual return, annual unknowns, mobile,
  200% text, print, and unaffected Volunteer screens.
- CSS build, two changed JavaScript syntax checks, six changed Python AST checks,
  131-template parse, and `git diff --check` passed.
- Contrast checker: PSU blue/white 9.97:1, slate-600/white 7.58:1,
  ink/white 17.12:1. Reused focus is PSU blue; labels/counts provide non-color cues.
- Downloaded PDF rendered with existing Poppler and inspected; new section's
  heading, plot, four groups and total remain together. Printed campus rows and
  verified-sex values were also checked by PDF text extraction and page rendering.
  Poppler reports local Symbol/ArialUnicode font-map warnings; inspected new
  labels, numbers, and tables render correctly.

Ignored synthetic screenshots, sample exports, PDFs and result JSON are under
`.qa-overhaul-temp/verified-sex/`. Existing staff browser output is under
`.qa-overhaul-temp/staff-overview/after/`. Browser servers stop in cleanup.

## Antislop Delivery Gate (Changed Surfaces)

- R-02 PASS: new interface copy has no em dashes; authored content remains untouched.
- R-03 PASS: browser checks cover five viewport widths and 200% text without page overflow.
- R-17/R-18 PASS: counts come from report evidence; no statistics or testimonials were invented.
- R-23/R-24 PASS: no assets/navigation structure added; existing campus and report links remain.
- R-25 PASS: contrast measured above; bars have direct text values and text equivalents.
- R-26 PASS: native expansion and linked details exercised in both browser suites.
- R-27 PASS: zero data, single category, Plotly failure and JavaScript-disabled states checked.
- R-28 PASS: no FAQ introduced.
- R-32 PASS: disclosure Enter toggle, visible outline and existing contextual navigation checked.
- R-33 PASS: source edits used patches; generated CSS came from the existing build.
- R-34 PASS: no theme toggle or theme behavior changed.
- R-35 PASS: built CSS and ran both browser suites; exported files opened and checked.
- R-36/R-38 PASS: claims and fixture evidence are explicitly scoped; no fabricated production data.
- R-37 PASS: direction and three dials declared before implementation.
- R-39 PASS: native labelled summary, 44px target, focus/hover/active states, semantic tables,
  no added autoplay or transitions; reduced-motion browser context exercised.
- R-40 PASS: no remote media/scripts introduced; chart fallback and exact values are immediate.
- R-01/R-04/R-06/R-07/R-08/R-09/R-10/R-12/R-13/R-14/R-19/R-22 PASS:
  no new decorative techniques, icons, assets or motion; existing Inter/PSU surfaces reused.
- Liveliness PASS: declared 2/2/1 dials, campus comparison is the Director focal point,
  schedule remains the Coordinator focal point, spacing separates reporting tasks,
  and PSU color/type/sidebar identity remains consistent in inspected renders.
- C-1/C-2/C-3/C-4/C-5 PASS: each panel answers delivery/participation questions;
  controls, fallback data, scope and responsive results have executable evidence above.
- R-05/R-11/R-15/R-16/R-20/R-21/R-29/R-30/R-31 PASS: existing institutional layout,
  concrete labels, radii, palette and light theme retained. No marketing template,
  buzzwords, competitor style or additional decoration introduced.

## Limits and Rollback

No full-suite, operational/MySQL execution, physical-device, manual screen-reader,
or Safari/Firefox claim. Native Microsoft Excel chart rendering was not exercised;
XLSX content/chart serialization and loading were verified with the installed library.
Missing sex remains Not Recorded; historic records are not backfilled.

Rollback only this task's reporting/query, template, chart, Help/tour, print, test
and QA edits, restoring its generated CSS from the matching source. Preserve the
pre-existing HANDOFF additions and unrelated SQL/guide/test, DOCX, output and tmp
work. No database rollback is needed.
