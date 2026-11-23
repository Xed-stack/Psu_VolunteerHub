# Director Needs Attention and Attendance Refinements

Date: 23 November 2026. Branch: `codex/ui-workflow-overhaul`. Local implementation only.

## Behavior and Preservation

- Both finding interfaces show labelled activity schedules in Philippine time. Completed review occurrences render their retained schedule facts, with no source-record lookup or evidence-fingerprint change. Missing ends are explicit.
- Review Category is the visible finding selector. Existing exact-type URLs remain supported with a removable scope note. Applying a category removes the old exact-type parameter. Both selectors filter before pagination. Only Needs Attention hides the shared Advanced Filters in Reports link.
- An actionable ongoing attendance finding has one Remind Coordinator button. The enabled queue's finding title retains access to assessments/history. Reminders use existing POST handlers, CSRF, signed evidence/revisions where enabled, campus authorization, unread deduplication, transactions and current timing checks. Quick sends preserve authored assessment/recommendation fields and return to the originating queue. Missing Coordinator and failed/stale submissions remain explicit.
- Internal/external attendance uses Attended/Not Attended without changing stored present/absent values. All Attended changes only displayed inputs; individual exceptions remain editable until Save. No-JavaScript users retain native dropdown/save operation, with the bulk button hidden. Existing event-window restrictions and off-page records remain.
- Excused is removed from new choices and rejected as a new write. An existing Excused row offers an unchanged blank submission and remains labelled Excused (Existing Record). Legacy forms posting the same existing value are harmless no-ops. Historical storage, reports and calculations remain intact; no enum migration or backfill occurs.
- Outstanding Recognition now uses the existing Reports directory-card pattern. The ranking route, award-year behavior and formulas are unchanged.

## Verification

- Main focused run: **79 passed** in 302.92 seconds across the new refinement cases, finding reviews, attendance rosters, Director overview refinement and staff overview tests. This run preceded the final category-pagination and submission-edge additions.
- Additional compatibility/edge run: **57 passed** in 153.75 seconds across refinement, attendance-default/report/export repairs and notification/draft cases. Thirteen Matplotlib/Pyparsing deprecation warnings were emitted by existing export dependencies; no test failed.
- Final refinement-only run: **23 passed** in 86.33 seconds, including before-pagination category filtering, legacy-scope replacement, timing changing during submission with complete rollback, CSRF/role checks, unchanged legacy Excused submission and source-snapshot preservation. Runs overlap; they are not additive test counts.
- Together the successful runs cover **121 distinct Python cases**; collection of the combined seven-file set confirmed that total.
- JavaScript: **4 passed**, including bulk marking, cancellation, individual absence after bulk presence, and unsaved-navigation handling. The existing mock was updated to provide the DOM APIs used by the current script.
- New browser runner: `scripts/qa_attention_attendance_refinements.py`, **30 groups passed**, no browser page errors. Covers enabled/fallback queues and both attendance rosters at 1440/1024/768/390/320px, schedule labels, one reminder action, native reminders/deduplication, keyboard review tabs/category submission, keyboard bulk marking, individual exceptions, explicit persistence, off-page preservation, enlarged text, no-JavaScript saving, locked attendance, missing ends, reviewed empty state, and recognition navigation.
- Existing `scripts/qa_attendance_rosters.py --stage after`: **37 groups passed**, including roster/entry/registration layouts, filters, context navigation, unsaved warnings, validation, no-JavaScript saving, 200% text, touch targets, focus clearance, print, and read-only activity states. Its no-JavaScript scenario now records absence instead of creating an Excused entry.
- `npm run build`, changed Python AST parsing, changed JavaScript syntax and `git diff --check` passed. Browser initialization parsed all Jinja templates. Contrast checker: PSU blue/white **9.97:1**, slate-500/white **4.76:1**.
- Python tests use isolated in-memory SQLite. Windows sandbox temporary-directory restrictions required the successful runs outside the sandbox; no operational database was used. Chromium previews used `create_app('testing')` with synthetic fixtures and CSRF enabled; servers were shut down afterward.

Evidence is local/ignored under `.qa-overhaul-temp/attention-attendance-refinements/` and `.qa-overhaul-temp/attendance-rosters/after/`. Each includes `results.json` and screenshots. Representative captures: `queue-True-390.png`, `internal-320.png`, `external-1440.png`, `reports-recognition-320.png`, and enlarged-text images.

## Design Critique and Audit

UI/UX Pro Max guided task flow, native bulk editing and responsive behavior. Frontend Design retained existing PSU palette, Inter typography, surfaces and spacing. Design read: operational university workspaces for Directors and Coordinators, Energy 2 / Rhythm 2 / Motion 1. Antislop core/UI/Human/Layoutmobile applied during work; Ponytail full reused the existing roster, notification, report and review infrastructure.

Before implementation, moderate issues were missing activity schedules, unnecessary reminder navigation, overlapping visible finding selectors, missing bulk marking and ambiguous Attending wording. The report-entry inconsistency was minor. The proposed direction addressed these using existing patterns rather than a new visual language.

Rendered review found Active/Reviewed links touching without a visible selected state. Added wrapping, spaced 44px links and PSU-blue selection. Final desktop/mobile/enlarged-text captures retain legible schedule/action hierarchy, individually editable roster controls and the existing Reports card composition. No remaining critical/moderate defect was identified in the changed UI. Extra decoration and alternate ranking layouts remain optional and outside scope.

Fetched the current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) and reviewed the changed queue, roster, Reports, scope-control templates, bulk script and CSS for semantics, labels, focus, native keyboard operation, touch targets, filter URLs, long text, reduced motion, unsaved feedback, empty/error states and print behavior. Existing locale-aware schedule enhancement is reused, with server-rendered Philippine-time fallback.

## Antislop Delivery Gate

### Hard Gate

- R-02 PASS: changed interface copy adds no em dashes; authored content is untouched.
- R-03 PASS: queue/roster browser checks pass at all five widths and 200% text without page overflow.
- R-17 PASS: product counts come from existing report/roster queries; browser fixtures are explicitly synthetic.
- R-18 PASS: no testimonials or invented people are added to product content.
- R-23 PASS: existing logo/assets/navigation are retained; no new visual asset or navigation structure is introduced.
- R-24 PASS: reminder destinations and the recognition card use existing authorized routes; browser navigation passed.
- R-25 PASS: tested changed blue/white and slate/white pairings exceed AA; existing focus and form tokens are reused.
- R-26 PASS: category apply/clear, tabs, reminders, dropdowns, bulk edits, saves and recognition navigation have native behavior and regression coverage.
- R-27 PASS: reviewed empty state, missing-end/Coordinator, stale/conflicting/failed reminder and unsaved/success feedback are covered; native server submissions retain browser loading behavior.
- R-28 PASS: no FAQ is added.
- R-32 PASS: keyboard tab navigation, bulk Space activation, native selects and focus clearance passed browser checks.
- R-33 PASS: UI changes were written directly in source with apply_patch; no external source-rewriting script was used.
- R-34 PASS: no theme toggle is added or changed; existing PSU surfaces are retained.
- R-35 PASS: CSS build, synthetic browser runners and recorded action checks passed.
- R-36 PASS: no fabricated security, compliance, performance or customer claim is introduced.
- R-37 PASS: the approved PSU direction and dials were established before implementation.
- R-38 PASS: production rendering uses existing records; synthetic QA content stays in disposable test apps.
- R-39 PASS: native labelled controls, visible focus, selected/disabled states and text feedback are used; no new animation or conflicting ARIA is introduced.
- R-40 PASS: no media or third-party script is added; no unmeasured performance result is reported.

### Purpose Gate

- R-01 PASS: no gradient/glow is added; existing PSU-blue emphasis identifies selected navigation and actions.
- R-04 PASS: no new icon set or generic icon decoration is added.
- R-06 PASS: existing Inter hierarchy is retained for consistency with PSU operational screens; no wide-tracked uppercase or monospace decoration is added.
- R-07 PASS: no background grid/pattern is added.
- R-08 PASS: no decorative action arrows are added.
- R-09 PASS: no decorative badges or duplicate headline labels are added.
- R-10 PASS: no glass effect is added.
- R-12 PASS: no shadow elevation is added.
- R-13 PASS: no glow is added.
- R-14 PASS: the recognition card intentionally matches its sibling report destinations; queue rows follow evidence/action hierarchy.
- R-19 PASS: Motion 1 is retained; no entrance, looping or template animation is added.
- R-22 PASS: no decorative illustration is added.

### Liveliness

- Dials PASS: Energy 2 / Rhythm 2 / Motion 1 match the existing institutional workspace.
- Consistency PASS: screenshots retain the approved palette/type/surface direction.
- Focal point PASS: actionable evidence and Remind Coordinator lead each ongoing finding; attendance editing leads each roster.
- Whitespace PASS: existing panel/row spacing separates scope, evidence and actions; tabs now have intentional gaps.
- Accent PASS: PSU-blue focus/selection/actions remain deliberate; gold stays in the existing PSU shell.
- Identity PASS: PSU branding, campus context, local schedules and existing typography remain visible.
- Design Read PASS: audience, page purpose, visual direction and dials were declared in the approved plan.

### Craftsmanship and Quality Locks

- C-1 PASS: palette/type/layout reuse preserves the PSU workspace; each added control serves the approved task.
- C-2 PASS: all changed controls have tested native navigation/submission or explicit disabled feedback.
- C-3 PASS: no filler section is added; the recognition card replaces its existing link.
- C-4 PASS: responsive/enlarged-text/keyboard/no-JavaScript/locked/print scenarios passed within recorded browser scope.
- C-5 PASS: no invented production statistic or testimonial is added.
- R-05 PASS: existing task-based queues/rosters/report directory are retained.
- R-11 PASS: existing button/input/card radii are reused; no pill-shaped redesign is introduced.
- R-15 PASS: Remind Coordinator, All Attended and Save Attendance describe their concrete actions.
- R-16 PASS: changed copy contains no AI marketing claims.
- R-20 PASS: PSU branding, campuses, Philippine schedules and review evidence retain product identity.
- R-21 PASS: the existing university light theme is retained; no unrelated theme work is introduced.
- R-29 PASS: the existing PSU blue/deep blue/gold/neutral palette is preserved.
- R-30 PASS: no external product visual language is introduced.
- R-31 PASS: blue denotes PSU action/selection; existing row/panel layouts separate evidence from actions; Inter and existing spacing preserve operational consistency; the recognition card matches report destinations; no new illustration is needed.

## Limits and Rollback

No full-suite, operational MySQL, physical-device, Safari/Firefox, manual screen-reader or true browser-zoom verification is claimed. Enlarged-text checks use 200% root font size. Existing historical Excused values intentionally remain visible and unchanged. Review functionality still depends on the pre-existing rollout flag/schema; neither is activated or migrated here.

No commit, push, deployment, dependency, operational migration or private-data update. Existing SQL catalogue/proposal work and handoff entry, DOCX, review JPGs, output/tmp and other unrelated changes remain intact. Rollback restores only this task's source/generated CSS/tests/docs; retain attendance records and review history. No database rollback is needed.
