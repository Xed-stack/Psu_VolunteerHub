# Staff Overview design specification — 14 November 2026

Designed before implementation with `frontend-design` and `design-system`.
Audience: PSU Extension Director comparing campuses and campus Coordinators
organizing delivery. The memorable element is useful institutional evidence, not
a decorative hero. All content is left aligned, numbers tabular.

## Tokens and component audit

Reuse existing Tailwind theme: navy `#002b60` (identity), blue `#00408b`
(actions), gold `#f4bd27` (selected/emphasis), white `#ffffff` (work surface),
slate `#475569` (supporting text), pale blue `#eff6ff` (annual summary).
Inter remains the single family. Body 16px/1.5; page title 28–32px; section title
18–20px; KPI number 28–32px; supporting labels 14px. Use spacing 8/12/16/24/32px,
8px surface radius and thin existing borders. No shadows or entrance animation.

| Existing issue | Component decision |
| --- | --- |
| Oversized banner consumes first screen | Compact heading, scope, primary action and quiet guide button. |
| Tall equal panels flatten hierarchy | Short KPI row; principal table/agenda; pale annual summary; ruled secondary section. |
| Full report filter form on Overview | Compact GET period/year/campus controls; conditional segment/dates; advanced filters in Reports. |
| Same no-target finding repeated per campus | Director preview groups findings by condition; full queue keeps individual evidence and reminders. |
| Duplicate navigation panels | Inline relevant links; existing sidebar retains secondary destinations. |

No new public API/schema. Additive server presentation fields supply comparison
rows, campus rollup, grouped findings and five agenda items. Reuse existing native
form, info-tip, link and chart behavior; new CSS stays under `.staff-overview`.

## Wireframes

Director desktop:
```text
University overview                         Open report | Guide
Year / Period / [segment or dates] / Campus / Apply / Advanced
Selected scope and chips, when present
Approved | Conducted | Accounts | Verified attendees | AOP
Campus comparison (main, ~70%)      Campus annual achievement
Campus | Delivery | AOP | ASP       Combined obligations, pending
Pending | Open campus              Separate university targets
Concise follow-up (3 groups)        Activity delivery trend
Open full queue                    Open filtered Reports
```

Coordinator desktop:
```text
[Campus] overview                           Create activity | Guide
Year / Period / [segment or dates] / Apply / Advanced
Five campus measures
Schedule (next five, ~65%)          Urgent work (up to three)
Date | Activity | state/action     Evidence and next action
Open calendar / All activities     Open full queue
Campus annual plan: below urgent work in desktop side column
```

Mobile: heading/actions wrap; controls stack in two columns or one at 320px;
KPI grid reflows without fixed row heights. Main content precedes secondary.
Campus table rows become labelled compact records rather than page-wide overflow.
Agenda rows wrap; bottom navigation never obscures focus. 200% text remains usable.

## Behavior, variants and states

- Compact scope preserves every additional GET value, including repeated campuses,
  when applying changes. Remove pagination/tour parameters on scope submission.
  Custom date and segment controls show only when relevant; no auto-submission.
- Activity period applies to activity metrics/comparison counts. Annual year and
  authorized campus selection define campus annual context; category/date/profile
  filters do not redefine annual assessment. University-target scope stays separate.
- Preserve five KPI definitions. AOP headline says campus or university targets;
  adjacent campus rollup repairs the missing combined-campus presentation.
- Agenda uses current/future approved known-schedule events for the signed-in
  campus; known ended events are excluded. Unknown-end future events can link to
  details with limitation copy. Ongoing action opens attendance; other actions open
  the activity workspace. Full queue handles ended correction reports.
- Campus comparisons link to period-preserving activity details and separately
  scoped annual evidence. No target: “Not set”; pending: explicit count; empty:
  short recovery action. Do not invent data to occupy whitespace.
- Existing button states cover hover/active/disabled/busy. Scope forms are normal
  GET submissions; tips open by keyboard/touch and close with Escape. Guide keeps
  focus restoration; new steps only target visible controls. Chart has text values.

## Pre-build critique

Removed the generic hero, duplicate shortcuts and second Overview chart. Retained
institutional Inter/blue/gold because they are explicit PSU requirements. The
campus comparison and annual scope separation make Director decisions concrete;
the dated agenda makes Coordinator work concrete. No photography is added to staff
pages solely to fill space. Existing public imagery remains unchanged.

Visual-review adjustment: the Coordinator annual summary moved from a full-width
section below the agenda into the desktop side column below urgent work, closing
the unused space beside the agenda. On phones, date, activity and action stack;
status is inline with time/location. This fixed 200% text overflow and reduced
repeated vertical spacing. Year/period chips are omitted because the same values
are already visible in scope controls; advanced filter chips remain removable.

Acceptance: visible principal workspace without scrolling past a large hero/filter
panel at desktop; less repeated copy; complete authorized destinations; accessible
mobile reflow; same metric facts and report/export behavior.
