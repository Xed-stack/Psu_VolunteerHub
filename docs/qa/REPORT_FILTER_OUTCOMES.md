# Activity Accomplishments Filters and Ended Outcomes

Implemented locally on 24 November 2026 on `codex/ui-workflow-overhaul` for both
Coordinator and Director reporting.

## Behavior and Design

Approved delivery now means an approved activity that has not finished.
Conducted delivery means an approved activity with a recorded end at or before
the current Philippine time. Missing end times remain in Approved with an
explicit schedule limitation. The Approved headline uses the same definition.

Activity, campus, department, category, SDG, delivery and date filters intersect.
Participant filters also remove activities without matching eligible
registrations. Coordinator campus scope cannot be broadened through parameters.
Malformed activity/campus IDs are rejected rather than widening Director scope.
Activity Records lists all linked SDG numbers and names beneath the title, with
No SDGs Assigned as its empty state. A select-in load keeps query count bounded.

Ended report outcomes include eligible unrecorded registrations as non-attendees
in the attendance-rate denominator. Recorded present counts are the numerator.
A positive numeric target is assessed from whole-activity recorded presence,
including when sex or affiliation filters narrow the displayed participant
counts and rate. This follows the user's Whole Activity choice.

The participation table, combined report and CSV/PDF/Excel exports use the same
report outcome fields. Whole-Activity Target identifies the assessment scope.
Recording displays Ended with its unrecorded count, or Complete where all
selected eligible registrations have attendance records. Other states use
Awaiting Activity End, No Registrations, Target Not Set, Activity Not Approved,
or End Time Not Recorded. Named report rosters apply participant filters and
exclude cancelled registrations.

Raw metrics remain separate from `row.participation` report outcomes. This
preserves existing recording completeness and review evidence/fingerprints.
Original Attendance records, historical unknown values, attendance-default
activation rules and review decisions are not rewritten. No schema, migration,
dependency or operational database changes were made.

Design read is a PSU staff reporting correction. Existing typography, tables,
navigation and colors are retained. Energy 2 / Rhythm 2 / Motion 1. SDGs sit
with their activity identity and target-scope text sits with its judgment.
New CSS only addresses desktop table wrapping at widths from 1024px. Shared
report behavior and copy apply at every width, with mobile styling retained.

## Verification

36 distinct Python cases passed across focused report, verified-attendance,
journey, UI, review-evidence and attendance-default checks. These include ten
new outcome/filter cases, both roles, exact end-time boundaries, missing end
time, unrecorded and zero registrations, external/cancelled participants,
filtered rates, whole-event targets, SDGs, CSV/PDF/Excel and unchanged evidence.
The aggregate query check remains constant at three queries across dataset sizes.

The broad initial run also exposed three existing legacy AOP tests outside this
change. Two insert retired ASP plans rejected by the existing AOP-only enum.
One expects a legacy evidence-edit POST to redirect where the existing route
returns 409. Those tests remain unresolved. An outdated Overview disclosure
assertion in a combined-report test was aligned to the previously approved
campus-commitments table, and its scoped-roster assertion passed afterward.

`scripts/qa_report_filter_outcomes.py` passed five browser groups with no page
errors. It verifies both roles at 1440, 1280 and 1024px, SDGs, native delivery
filtering, tab-state retention, ended target/rate labels, scoped CSV and rosters,
keyboard reachability, enlarged text and JavaScript-disabled results/navigation.
Evidence is under `.qa-overhaul-temp/report-filter-outcomes/`.

All templates parsed. CSS build and whitespace checks passed. The isolated local
preview was started with its existing database launcher and the authenticated
updated participation report returned HTTP 200. Test writes use disposable
synthetic storage. Full-suite, physical-device, manual screen-reader and real
browser-zoom checks were not performed. Enlarged text uses a doubled root font
with the existing chart resize handler dispatched.

## Critique and Audit

High-priority findings addressed include overlapping delivery results, withheld
ended outcomes, misleading filtered-target comparisons and unfiltered named
rosters. Moderate findings addressed include absent SDG context and desktop
enlarged-text wrapping in the existing sex-breakdown table. Numeric results
remain text-readable with chart scripts unavailable.

Current Web Design Guidelines were fetched on 24 November 2026. Changed UI was
reviewed for labeled states, semantic tables, readable wrapped text, keyboard
navigation and scope retained in URLs. Existing PSU color pairs and focus
treatments are retained. The approved AOP Antislop R-01 through R-38 gate was
applied to these additions. Applicable gates pass for sourced data, working
controls, explicit empty states, purposeful hierarchy, verified desktop layout
and native behavior. Unsupported future or unset outcomes have explicit labels.

## Local Delivery and Rollback

Work remains local and uncommitted. Rollback restores only this task's shared
report outcome/filter helpers, report templates, export/roster changes, desktop
wrapping rule, generated CSS and focused tests. Preserve unrelated working
changes, including earlier HANDOFF additions. No database rollback applies.
