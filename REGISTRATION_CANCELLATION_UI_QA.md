# My registrations and cancellation UI QA

23 October test-only follow-up: see REGRESSION_RECONCILIATION_QA.md for the
subsequent repair and verification of the three baseline assertions. Results and
unpublished/release-gate statements below describe the earlier delivery snapshot;
they are preserved as history. No cancellation UI or production behavior changed
in that follow-up. Manual zoom/screen-reader/physical-mobile gates remain open.

Publication follow-up: the user approved commit/push on 22 October 2026, with the
three baseline failures explicitly remaining open. The local-only statements below
describe the verification snapshot. See RELEASE_2026_10_22.md and actual Git state.

22 October 2026. Local changes only. Original MySQL, live data, policy records,
deployment, dependencies, schema, commits and pushes were not changed. The prior
uncommitted opportunity journey and user attachments are preserved.

## Design and implementation

Reading this as a commitments workspace for PSU volunteers, using the existing
institutional visual language: ENERGY 1 / RHYTHM 2 / MOTION 1. Inter stays consistent
with the completed dashboards; PSU blue #00408b marks navigable activity titles,
white panels separate work areas, #111c2c carries body text, and #ba1a1a identifies
the cancellation submission. No new illustration, icon set, animation or theme.

Ponytail full reused the role shell, native forms/disclosures, existing routes,
shared loading state and styles. Frontend-design informed activity-first records,
clear status labels and whitespace between facts and decisions. Anti Slop was
applied during implementation, with human/accessibility and mobile checks.

- Registration titles, recommended Details and upcoming schedule titles open the
  existing activity-details page. Calendar anchors, filters and Show more/less remain.
- Records show the effective deadline, with activity-start fallback labelled.
  Registration status and cancellation outcome are distinct; pending explicitly
  remains active until approval. Empty and filtered-empty states have recovery links.
- One shared PSU cancellation helper drives dashboard actions and GET/POST guards.
  It prevents requests after attendance, ineligible statuses, or the effective
  deadline, and enforces the selected one-request-per-registration rule. Existing
  reviewed requests are retained; an approved cancellation followed by restoration
  is labelled as a previous decision, not the current registration status.
- Native disclosures show the owning volunteer's reason/details and review note.
  Request/review timestamps are labelled UTC, matching their existing UTC storage;
  activity schedule/deadline formatting retains the application's existing convention.
- Form errors are inline and summarized, retain submitted values, and focus the
  first invalid field. JavaScript sets the conditional native details requirement;
  server validation always requires nonblank Other details. Static HTML deliberately
  does not lock details as required, allowing no-script users to change reason after
  an error. No entries are stored as drafts or promised saved after session expiry.
- Back and success URLs use only existing status/campus/category/date/show/calendar
  keys and a server-generated registration anchor. Arbitrary return URLs are ignored.
- Existing unique constraints backstop duplicate inserts; the losing request rolls
  back and returns to the record when an existing request is found. Other integrity
  failures without an existing request are re-raised. Notification/audit services
  and coordinator review remain in place; external signed-link flows are unchanged.
- Record rows stack below 64rem because the shared sidebar leaves insufficient
  content width for two readable columns at 768px. Desktop separates facts/decisions.
  This retains the requested stacking below 48rem and improves the tablet case.

## Automated verification

- Initial focused run: **60 passed in 166.07s**. Selection:
  `tests/test_registration_ui.py`, `TestCancellationReview`, `TestVolunteerFeatures`.
- Final focused run: **66 passed in 165.81s**, including the same selection plus
  `tests/test_ui_structure.py` and the no-script reason-switch regression assertion.
  Tests use the testing factory, isolated SQLite and external disposable temporary
  directories.
- Final uninterrupted full suite outside the sandbox: **450 passed, 3 failed in
  1130.79s** (453 total), with no permission errors. The only failures are the
  same three assertions already reproduced on committed baseline 21a0545:
  `TestReportingSystem::test_director_campus_paging_and_supplementary_forms`,
  `TestAnalytics::test_report_pagination_and_exports_preserve_all_selected_filters`,
  and `test_profile_repair.py::test_milestones_require_completed_present`.
  See OPPORTUNITY_JOURNEY_QA.md for the baseline comparison and exact expectations.
  All 37 new registration/cancellation cases passed in this full run. This is not
  a green full-suite claim; unrelated assertions were not changed to hide failures.
- `node --check static/scripts/cancellation-form.js` and `git diff --check` passed.
  A final shared-structure recheck after the 44px minimum-width refinement also
  passed all 6 tests in 0.03s. Browser warning/error log was empty at final review.
- The first sandboxed full attempt reached 100% but could not produce its summary:
  Windows denied temporary-folder cleanup. It also blocked Node child processes
  (`spawn EPERM`) and temporary upload fixtures. No aggregate count is claimed for
  that attempt. An outside-sandbox recheck of profile, auth-script, shared-submit
  and session checks completed with **40 passed, 1 known baseline failure in
  103.07s**; the remaining assertion is the existing profile Eligible-cell markup.
  Application security settings were not changed. The full suite was restarted
  outside the sandbox with a fresh disposable temporary directory.
- Cases cover pending/confirmed/completed/cancelled registrations against every
  present/absent/excused/missing attendance state; exact effective deadline boundaries;
  existing pending/approved/rejected requests on GET and POST; prior approved
  decisions on restored registrations; invalid reason/Other details; escaped notes;
  owner/role/anonymous isolation; CSRF; stale deadline; expired sessions; duplicate
  POSTs, audit count and coordinator recipient scope; whitelisted context and PRG.
- Unique-conflict recovery is simulated deterministically after rollback; no claim
  is made of a real concurrent MySQL stress test or live database verification.
- Three report/profile assertions reproduced on committed baseline 21a0545 in
  OPPORTUNITY_JOURNEY_QA.md remain outside this UI change. Their failures must not
  be relabelled as new cancellation regressions or hidden by weakening assertions.

## Browser verification

Disposable preview on port 5072 used synthetic SQLite users/activities/requests.
No real volunteer request, coordinator decision or binding agreement was submitted.

- Dashboard records, form and server-error state were measured at 320, 390, 768 and
  1440 CSS pixels. Scroll widths stayed within viewport widths. Tablet records were
  rechecked after the breakpoint refinement and used a single readable column.
- Record links/disclosures measured at least 44px high (long labels grew to 64px).
  Reason labels measured 44px; narrow submit actions grew rather than clipped.
- Browser submission with Other and whitespace-only details returned inline error
  plus linked summary, retained Other, and focused `details`. Native required
  validation also focused that field before a blank submission.
- A valid synthetic request returned to `?show=10#registration-1`, retained Confirmed
  registration status and displayed Pending cancellation separately. The message
  named the activity and explained that approval was still required. Refresh was GET.
- Pending, approved, rejected, attendance-blocked, deadline-blocked, completed and
  restored-after-approval records rendered. Long review notes wrapped on mobile;
  literal script markup in synthetic details displayed as text, not executable HTML.
- Enter toggled the decision disclosure with a visible 3px PSU-blue focus outline.
  Record title navigation opened the matching details page. Show less displayed five
  records, and Show 5 more displayed all eight synthetic records.
- With script execution actually disabled, native keyboard status selection and
  Apply filters submitted a GET and returned confirmed records. The no-script form
  rejected Other without details, then accepted Academic Conflict with empty details
  after changing the reason through native controls. Scripts were restored afterward.
- Ctrl+Plus was attempted five times; viewport width and device-pixel ratio remained
  unchanged. Actual 200% browser zoom is therefore unverified, not replaced by a
  narrow-viewport claim. Physical phone/on-screen keyboard and assistive screen-reader
  checks were unavailable. Server session-expiry tests replace no actual 30-minute
  browser wait; they do not imply unsaved entries are retained.

Evidence outside Git:
`C:/Users/arlro/.codex/visualizations/2026/10/18/01a14c77-a036-7241-ad82-ee16a46acd99/registration-20261022/`.
Includes `form-{320,390,768,1440}.jpg`, `error-{320,390,768,1440}.jpg`,
`dashboard-{320,390,768,1440}.jpg`, `decision-mobile.jpg`,
`confirmation-{320,390,768,1440}.jpg`, `registration-final.jpg`,
`native-filter-no-js.jpg` and `confirmation-no-js.jpg`. Full-page captures can contain
extra browser capture whitespace; viewport screenshots and DOM measurements were
used for layout review. Screenshots depict synthetic QA content, not production.

## Current Web Interface Guidelines audit

Fetched [the current guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
on 22 October 2026. Reviewed the changed dashboard/form/decision partial, styles
and cancellation script. Native semantics, errors, focus, link destinations,
wrapping, states, query preservation and duplicate-submit behavior were checked.
The audit prompted no-script conditional-validation recovery and the tablet reflow
refinement. No new motion, dependency, fixed action bar or global stylesheet.

Contrast checker: PSU blue/white **9.97:1**, cancellation/error red/white **6.46:1**,
muted #424752/white **9.31:1**. Blue focus is 3px; status meaning is written in text.
Confirmation reuses the earlier activity-page in-flow high-contrast treatment on
registration lists. Existing dashboard KPI/calendar content was not redesigned.

Remaining audit limits: actual zoom/device/screen-reader checks above; existing
activity dates use the established server formatting rather than adding a new
locale system. No unsaved-navigation dialog or persistent draft was introduced;
the form explicitly warns that session expiry does not save entries.

## Anti Slop delivery gate

PASS is scoped to the changed surfaces and observed checks, not an application-wide
accessibility certification. Unavailable manual verification is listed above.

- R-01 PASS: PSU palette reused; no new gradient or glow.
- R-02 PASS: new UI copy contains no em dash.
- R-03 PASS: measured widths contain content; records stack on mobile/tablet.
- R-04 PASS: no new decorative icon set or emoji.
- R-05 PASS: registration decisions refine the existing dashboard, not a new template.
- R-06 PASS: Inter preserves dashboard typography; factual labels establish hierarchy.
- R-07 PASS: no decorative background grid.
- R-08 PASS: no decorative action arrows; disclosure markers are native controls.
- R-09 PASS: registration and request states are factual text, not fake buttons.
- R-10 PASS: no glass or backdrop effects.
- R-11 PASS: existing PSU control/panel radii retained.
- R-12 PASS: no new record-card shadow; borders separate records.
- R-13 PASS: no glow added.
- R-14 PASS: record structure compares actual commitments; no filler feature cards.
- R-15 PASS: actions name cancellation, details, filters or record expansion.
- R-16 PASS: no promotional buzzwords added.
- R-17 PASS: counts come from registration data; synthetic QA is labelled.
- R-18 PASS: no testimonials added.
- R-19 PASS: no new decorative animation; shared loading behavior retained.
- R-20 PASS: campus, activity facts and PSU typography/actions retain institutional identity.
- R-21 PASS: user-selected institutional light theme retained; no theme toggle added.
- R-22 PASS: no new illustrations.
- R-23 PASS: existing PSU assets only; synthetic records explicitly labelled.
- R-24 PASS: changed activity and Back links resolve to existing destinations.
- R-25 PASS: text/action pairings verified with the skill contrast checker.
- R-26 PASS: links, native disclosures, filters and request submission exercised.
- R-27 PASS: distinct empty/filter-empty, inline errors, busy submit and pending state.
- R-28 PASS: no generic FAQ added.
- R-29 PASS: existing blue/red plus neutral token palette retained.
- R-30 PASS: no external-product clone or new dashboard shell.
- R-31 PASS: hierarchy, type, color, spacing and tablet breakpoint reasons recorded above.
- R-32 PASS: Enter disclosure operation, native controls and visible focus observed.
- R-33 PASS: source changes made directly with patches, not rewriting scripts.
- R-34 PASS: no additional theme shipped.
- R-35 PASS: isolated app run, responsive interactions exercised; manual limits recorded.
- R-36 PASS: no invented security/compliance/performance claims.
- R-37 PASS: explicit approved PSU direction and dials declared before implementation.
- R-38 PASS: real model fields drive UI; synthetic data stays in disposable QA.
- Liveliness PASS: title/activity identity is the record focal point; whitespace
  separates facts/decisions; PSU blue marks navigation; declared dials retained.
- C-1 PASS: each changed treatment has an explicit work-related purpose.
- C-2 PASS: changed controls have working destinations/behavior.
- C-3 PASS: each record section answers schedule, status or cancellation questions.
- C-4 PASS: measured breakpoints, long content and error/empty states hold; manual limits remain.
- C-5 PASS: no fictional production claims or fabricated activity evidence.

Publication remains unapproved for these changes. Next release gate remains the
three baseline report/profile assertions plus manual zoom/device checks.
