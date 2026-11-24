# Director Needs Attention Desktop Reference

Implemented locally on 24 November 2026 on `codex/ui-workflow-overhaul`.

## Design and Behavior

The Director review queue follows the supplied institutional desktop reference.
It has a pending count, compact year/period/campus scope, Active and Reviewed
counts, category links with live counts, native sorting, audit guidance, a CSV
export toolbar, five findings per page, evidence disclosures and status badges.
The PSU shell and existing review detail workflow remain in use.

Design read is a PSU evidence-review workspace for university Directors. Energy
2 / Rhythm 2 / Motion 1. Gold marks the active view and pending work. Navy marks
review actions. White row panels separate findings. Status labels communicate
state through text as well as color. Styling applies from 1024px. The original
queue presentation remains below that width, using the same five-item Director
pagination. Coordinator and admin queue presentation retain their existing path
and 25-item pagination. The unavailable-storage fallback remains available.

Counts come from canonical review reconciliation under the existing source
scope. Category counts cover the selected tab before category/finding filters.
Annual findings retain annual scope. Filtering and sorting happen before paging.
Actionable First sorts eligible reminders first, then changed evidence, with
campus/title tie-breakers. Campus and Finding Title sorting are also available.
Reviewed history keeps its existing newest-first database order.

CSV exports every matching finding before pagination and escapes spreadsheet
formula prefixes using the existing helper. Exports include campus, finding,
activity, scope, evidence and review status. Reads do not persist review records.
Quick reminders use the existing signed source/version/revision form and
Director-only transaction. The existing detail page records assessments and
closure reasons, preserving attendance and source outcomes.

## Reference Differences and Critique

The screenshot's bulk selection, batch reminder, Remind All and bulk closure
controls are not implemented. Individual reminder and assessment controls are
provided. The reference's unsupported audit-active claim is replaced by the
actual Director role. Highest Priority is labelled Actionable First to describe
the actual ordering. Screenshot figures and fictional finding types are not
inserted into the data.

High-priority critique findings addressed include truthful statuses and counts,
safe per-finding actions, and evidence discoverability. Moderate findings
addressed include row density, five-row pagination and enlarged-text overflow.
Evidence summaries expand to full text and schedules with native details.
Wrapped action groups and bounded widths resolve the enlarged-text issue.

## Verification

The disposable browser runner `.qa-overhaul-temp/check_needs_reference.py` passed
five groups covering these behaviors.

- Populated queue at 1440, 1280 and 1024px without horizontal overflow.
- Category filtering, native sorting, scoped CSV and an eligible reminder.
- Individual assessment/closure, Reviewed history and expanded evidence.
- Keyboard reachability and 200% root-font enlargement.
- JavaScript-disabled category navigation and explicit empty/invalid states.

47 distinct focused Python cases passed across the final full run and a two-case
missing-Coordinator rerun. The full run passed 46 cases and exposed one notice
that could be paged away. A scope-wide notice resolves that issue, and both
enabled/disabled workflow cases passed afterward.

Template parsing and CSS build passed. New focused Python cases cover category
and tab totals, CSV before pagination, formula escaping, selected-campus scope,
invalid sorting and reviewed-history export. Existing permission, stale-evidence,
deduplicated-reminder and attendance-boundary regressions are also exercised.

Current Web Design Guidelines were fetched on 24 November 2026 and applied to
the changed UI. Native controls, visible labels, links for navigation, focus
styles, touch-sized actions and wrapping content were checked. Amber status
text is 6.61:1 and muted status text is 9.45:1 against their backgrounds.

Antislop delivery review uses the existing AOP R-01 through R-38 gate for the
same PSU workspace. New decisions have written purposes above. Counts and dates
are sourced, every displayed control has working behavior, unsupported bulk
controls are omitted, and the design is verified in the browser. Final Python
checks cover permissions, stale evidence, concurrency, duplicate reminders,
history, source preservation, CSV safety and pagination.

Browser evidence is under `.qa-overhaul-temp/needs-desktop-reference/`. Tests
use disposable synthetic data. Full-suite, physical-device and manual
screen-reader verification are outside the recorded checks. Enlarged text uses
root font sizing rather than browser UI zoom.

## Local Delivery

The prepared port-5000 preview was reloaded using its existing isolated database
launcher. Work remains local. Rollback restores this task's Director queue
template, queue presentation/count/export additions, desktop CSS and associated
test changes. Preserve the pre-existing fallback queue and other working edits.
No database rollback is required.
