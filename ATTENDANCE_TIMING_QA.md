# Attendance timing repair

Date: 20 October 2026. Local and uncommitted; no push or live database changes.

Later release verification: copied-MariaDB browser retest now passed, including
early check-in then final attendance on the same registration. See
REPAIR_RELEASE_QA.md for persisted-state checks, automated results and isolation.
This supersedes earlier pending-retest notes, which retain their snapshot context.

## Approved early-check-in follow-up (latest behavior)

The user approved a 30-minute early check-in window. This supersedes the
end-only write lock in the original repair snapshot below.

- Server accepts saves at or after start minus 30 minutes, not one second earlier.
  GET and POST use the same opening policy, including after schedule changes.
- Present before effective end records check-in, but registration stays Confirmed
  and certificate-ineligible. No timer automatically completes participation.
- Coordinator must save final attendance at/after effective end. Present then
  becomes Completed and certificate-eligible; absent/excused stay Confirmed.
  Legacy activities without end times use start as effective end, as before.
- Native button labels distinguish Save check-in from Save final attendance.
  Visible instructions explain the two stages; Help is updated. Existing PSU
  palette, layout, typography and focus/scroll styles are reused, with no new CSS.
- Isolated CSRF-enabled SQLite browser: keyboard early check-in succeeded,
  upcoming activity controls stayed disabled, ended final attendance succeeded.
  At 390px, page client/scroll width both 375px; no captured console errors.
  Screenshot: early-checkin-mobile.png in the local visualization folder.
- Automated tests now cover 30-minute before/at/after boundaries, end boundaries,
  legacy fallback, external check-in, stale schedule, preservation outside the
  window, and finalization without duplicate attendance. Final focused
  timing/existing-attendance/external-participant/UI run: **60 passed in 146.25s**.
  This is not a full-suite result.
- No migration, dependency, live database write, commit, or push. Full suite and
  copied-MariaDB browser retest remain pending; preview is isolated SQLite.

### Scoped design delivery gate

- Hard Gate PASS: native labelled controls, CSRF-protected real submissions,
  closed-window feedback, mobile containment, and keyboard save verified above.
- Purpose Gate PASS: existing institutional palette/type/layout retained for
  continuity; only timing and action copy changed to distinguish the two stages.
- Liveliness PASS: existing PSU identity and Attendance heading retained, ENERGY 1 /
  RHYTHM 2 / MOTION 1; no new decoration, assets, navigation, or motion.
- Craftsmanship PASS: early/closed/final states exercised; tests cover timing and
  eligibility. Physical touch, screen-reader speech and 200% zoom not independently
  reverified; no broader accessibility certification claimed.

## Original end-only repair snapshot (superseded policy)

## Behavior

- Server rejects every attendance status before the scheduled activity end,
  falling back to the start when no end is recorded. Saving at the exact boundary
  is allowed. The guard runs after ownership checks and before record changes.
- Both PSU and external participants are covered. A stale form is checked again
  against the current schedule when submitted.
- Existing records, including previously premature attendance, are preserved.
  No migration or retrospective certificate/registration correction was performed.
- Native status controls and Save are disabled before opening. A visible notice
  states the opening time and legacy fallback. Explicit CSRF field, individually
  named status controls, and a keyboard-focusable named scrolling region remain.
- Existing Bare CSS/base.css, role shell, campus/role checks, local assets, and
  cosine recommendations are retained. Minimal role-scoped CSS makes disabled
  Save neutral and keeps mobile status values readable; no dependency added.

## Automated verification

- Broader timing, existing attendance, external-participant and UI selection:
  **56 passed**. An added external-participant future-timing case: **1 passed**.
- Final timing/cancellation/UI selection: **22 passed**. Counts overlap and
  must not be added as a unique-test total.
- Timing cases cover before/at/after boundaries with and without end dates,
  absent/excused attempts, rescheduling after GET, existing-record preservation,
  CSRF enforcement, and external-participant writes.
- Existing successful attendance fixtures now use past activity dates; their
  completion/certificate assertions remain intact.

## Browser verification

Used a temporary localhost preview backed by isolated in-memory SQLite with
CSRF enabled, not the source MariaDB database. Upcoming and ongoing activities
showed disabled controls and the opening-time notice. Ended activities and
legacy past activities accepted keyboard-submitted attendance successfully.

At 390px viewport, the page had equal client/scroll widths (375px); the status
control remained 128px wide inside the contained table scroller. No captured
console errors. Evidence: attendance-timing-locked-mobile.png in the local
Codex visualization folder (not committed).

## Remaining gate

MariaDB was stopped (connection refused). Full pytest suite and browser rerun
of both local repairs on the existing disposable MariaDB copy remain pending.
Do not interpret isolated SQLite checks as actual-MariaDB verification. No
source service was started, database seeded, or existing data rewritten.

Native screen-reader output, physical touch and real browser zoom were not
independently tested. No unrelated workflows were claimed as reverified.
