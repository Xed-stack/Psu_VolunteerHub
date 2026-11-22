# Director Overview Refinement

Date: 22 November 2026. Branch: `codex/ui-workflow-overhaul`. Local implementation.

## Result

Director Overview now shows four headline KPIs: Conducted Activities, Verified
Attendees, Campus Annual Achievement and Findings to Review. Values come directly
from existing report and Overview results. The campus annual rollup counts shared
AOP/ASP obligations once per campus; pending evidence and separate university-wide
targets retain existing semantics. There are no new dashboard calculations.

Campus Accomplishments and Needs Attention form the primary desktop pair. Approved
Activities and all-time Volunteer Accounts remain in a secondary summary. The
existing full annual achievement panel follows, then the delivery/attendance chart
pair and workspace links. All nine campuses remain available in all-campus scope,
including zero values, with the native details disclosure and existing drilldowns.

Needs Attention shows generated findings, with at most four issue groups in the
existing order, affected campuses, group links and the full total. Additional types
are explicitly noted. This is not an active-review/unique-activity count. Historical
findings remain unchanged; no status, closure or review persistence is implied.

The existing Needs Attention route accepts optional `finding_type`, validated
against the shared eight known finding codes. Filtering happens before its existing
25-item pagination. Group links preserve report scope and start at page 1; the
selected queue identifies its type and can clear only that type. Back to Overview
omits the queue-only type and page. Existing permissions, individual actions and
notification routes remain. No notification was sent during browser verification.

Director-only classes and a metrics option keep Coordinator, Report and Admin
presentations on their existing branches. The top heading/actions, complete filter
controls, contextual date/time note and applied-filter chips retain their behavior.
Guide and Help descriptions now match the Director hierarchy and finding semantics.

## Analyze, Design and Critique

Audience: PSU Directors comparing campus delivery and opening evidence for review.
Retained Inter, PSU blue/deep blue, gold identity, existing white/slate surfaces and
native controls. Energy 2 / Rhythm 2 / Motion 1. The emphasis is one restrained PSU
border around Needs Attention, with no new chart type, animation or review workflow.

Priority findings and resolutions:

- High: Active Reviews would misrepresent derived findings without persistent
  review state. Use Findings to Review and explain multiple findings per activity.
- Moderate: group actions previously opened the same full queue. They now open
  validated issue-type subsets while preserving authorization and report scope.
- Moderate: lower charts preceded the action summary. Reordered only the Director
  branch, preserving all details and lower-priority metrics.
- Moderate rendered defect: the original unlayered five-column CSS overrode the
  new component rule, leaving an empty fifth slot. Added scoped overrides alongside
  existing responsive rules; browser checks assert four equal-width desktop tiles.
- Moderate interaction defect: the new annual KPI jump could place its heading
  beneath the sticky header. Added a scoped scroll margin and focusable target.

Final desktop/mobile/enlarged-text screenshots reviewed. Primary panels lead the
page; complete nine-campus panels can naturally extend below the first viewport.
No viewport-height hacks, clipping, forced spacers or compressed filters were used.
At 1024/768px KPIs use two columns; small mobile uses one. Tables retain contained
scrolling or the existing mobile row layout. Annual detail stays full-width rather
than squeezing three supporting panels into narrow desktop columns.

## Verification

**53 unique focused tests passed:** a final combined run of 52 cases across
`test_director_overview_refinement.py`, `test_staff_overview.py`,
`test_comparison_navigation.py`, `test_verified_sex_reports.py` and
`test_help_header.py`, plus a separately added four-group preview-limit case.

Coverage: exact headline values; shared annual-obligation deduplication/pending
scope; preserved secondary metrics; unchanged Coordinator/Report five-tile layouts;
filter context; invalid/repeated finding types; group-to-queue matching; more than
25 findings; scope isolation; unchanged event/registration/attendance facts; empty
findings/Not Set; all valid finding codes; full totals when only four groups show;
existing annual queries, report navigation and export reconciliation.

Initial failures were selectors matching both a metric's strong value and its
existing tooltip heading. Selectors were corrected; the final run passed. Existing
matplotlib/pyparsing deprecation warnings remain.

**32 staff browser groups passed**, using `scripts/qa_staff_overview.py` with
synthetic in-memory SQLite: both staff roles at 1440×900, 1024, 768, 390, 320 and
landscape; KPI widths/order; preserved filter controls/custom dates; 125% and 200%
text enlargement; tooltip keyboard/focus; complete dashboard guide; finding-type
navigation/clear scope; zero findings; visible annual KPI destination; campus
return links; empty annual/agenda states; print and three unaffected volunteer
pages. Every Jinja template is parsed through this running application.
Evidence: `.qa-overhaul-temp/staff-overview/after/results.json`, PNGs and PDFs.

**53 existing attendance/report browser groups passed**, using
`scripts/qa_verified_sex_reports.py`: both staff dashboards, report views, verified
attendance donuts, counts, disclosures, long labels, mobile layouts, comparison
navigation, exports and no-JavaScript/Plotly-failure fallbacks. No page errors.
Evidence: `.qa-overhaul-temp/verified-sex/results.json` and associated captures.

CSS build, changed Python compilation, changed JavaScript syntax and
`git diff --check` passed. Existing PSU/slate colors and native focus treatments
were reused; no new color palette or low-contrast status encoding was added.
Text enlargement was emulated by root font size, not physical browser zoom.

## Final UI Audit and Delivery Limits

Applied UI/UX Pro Max (hierarchy guidance), Frontend Design, Design Critique,
Ponytail full, Antislop during, Antislop UI/Human/Layoutmobile, Webapp Testing and
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched on 22 November 2026. Reviewed changed Overview/queue templates, CSS, guide
and Help. Fixed scoped hierarchy, CSS-cascade and anchor-visibility issues above.
Labels, heading order, native links/disclosures, visible focus, 44px actions,
selected/empty states, URL scope, print values and responsive wrapping remain.

No full-suite, live/MySQL, physical-device/browser-zoom, Safari/Firefox or manual
screen-reader claim. Existing global navigation and deferred audit findings remain
outside this change. No review closure/assignment/history UI, schema, dependency,
operational database change, commit, push or deployment.

Unrelated SQL update/guide/test and their handoff entry, DOCX, output and tmp remain
intact. The attached proposal document was read as planning input and not modified.
Rollback only this task's Director presentation, optional queue filter, guide/Help,
CSS source/generated CSS, tests, browser checks and documentation. No database
rollback is required.
