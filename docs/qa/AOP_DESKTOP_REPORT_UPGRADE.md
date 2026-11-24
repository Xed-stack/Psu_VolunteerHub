# AOP Desktop Report Upgrade

Implemented locally on 24 November 2026 on `codex/ui-workflow-overhaul`.

## Design and Critique

Reading this as an annual reporting workspace for PSU Directors, Coordinators,
and administrators. Energy 2 / Rhythm 2 / Motion 1.

The existing report becomes the reporting entry point with a prominent Manage
AOP Goals action. Administrators receive View AOP Goals. Reports stays selected
through the goal workflow. The separate desktop sidebar goal entry is hidden
from 1024px. Existing mobile styles are retained. Shared links and breadcrumb
context also appear at smaller widths.

Navy establishes the annual summary as the focal point. Gold emphasizes its
existing achievement count. PSU typography and a restrained spacing scale keep
the page consistent with the existing workspace. A compact filter toolbar and
aligned tables support comparison. Exact tables continue to support chart
fallbacks. The report directory has one annual-plan entry with evidence and
history links available inside the report.

High-priority critique findings addressed include management discoverability,
campus scope continuity, role-specific actions, and distinguishing university
targets from campus obligations. Moderate findings addressed include oversized
filter spacing and draft discoverability. Desktop drafts move above the goal
list through DOM placement so keyboard and visual order agree. Without
JavaScript they retain their original position. The original placement is
restored below 1024px. Category remains Not Assigned as the current data model
has no category field.

## Verification

- 30 existing focused AOP tests passed.
- Two new staff-role navigation tests cover campus parameter translation,
  Coordinator campus restriction, and the scoped return link.
- 13 existing Director AOP browser groups passed with synthetic data, including
  search, pagination, exports, drafts, long content, and enlarged text.
- Prepared-preview browser checks passed for Director and Coordinator at
  1440, 1280, and 1024px with no horizontal overflow or page errors. Checked
  report-to-management-to-report navigation, Reports selection, empty years,
  CSV/PDF/Excel responses, keyboard reachability, and JavaScript fallback.
- All 142 templates parsed. CSS build, JavaScript syntax and whitespace checks
  passed. Local preview root returned HTTP 200 after restart.
- Contrast is 11.37:1 for summary supporting text and 8.03:1 for gold figures
  against PSU deep navy.

Current Web Design Guidelines were fetched from the Vercel guidelines source
on 24 November 2026. Changed controls use semantic links and native forms,
visible labels, existing focus treatment, wrapping content, and numeric alignment.
Rendered critique found an initial nested draft placement error, corrected by
selecting only the goal page's direct-child list. The management browser suite
passed again after correction.

## Antislop Delivery Gate

- PASS for real data and claims. Existing reporting services supply all values.
- PASS for purposeful styling. Navy, gold, spacing and tables establish reporting
  hierarchy within the existing PSU identity.
- PASS for navigation and controls. Staff-role tests and browser checks exercise
  report links, management, exports, filters, disclosures and draft destinations.
- PASS for desktop layout and interaction. Three desktop widths, visible focus,
  native keyboard interaction, and chart fallback were checked.
- PASS for craftsmanship. Templates, build, syntax, regressions and rendered
  review completed. The new styles are contained in a desktop media query.

No full-suite, physical-device, manual screen-reader or admin-browser claim.
An attempted admin fixture exposed that the current user-role enum supports
volunteer, Coordinator and Director accounts only. The admin label is retained
as compatibility with existing route guards, and verification covers the two
supported staff roles.
Desktop report checks used the prepared preview's current data, including empty
campus results. The populated management review used disposable synthetic data.
Mobile redesign is deferred at the user's request. Existing browser regression
coverage exercised narrow layouts without changing their CSS.

## Delivery and Rollback

The isolated preview is available on loopback port 5000. Work stays local.
Rollback restores this task's report/navigation templates, UI context change,
desktop CSS block, draft-placement script, tests and generated CSS. Preserve
pre-existing working changes in the workspace route, queue templates and CSS.
No database rollback applies.
