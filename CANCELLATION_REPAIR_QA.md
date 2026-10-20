# Cancellation decision submission repair

Date: 20 October 2026. Scope: the shared form-submit loading-state script.

Later release verification: desktop approval and mobile keyboard rejection now
passed on the existing disposable MariaDB copy, including persisted notes,
reviewer/time, audit and notification checks. See REPAIR_RELEASE_QA.md for
automated results and isolation; earlier pending notes are retained snapshots.
No migration, new runtime dependency, CSS/template redesign, or route change.

## Cause and fix

The prior script disabled the clicked native submit button synchronously in the
submit handler. Disabled submitters lose their name/value in submitted form data,
including the cancellation form's decision=approved/rejected. The route therefore
received no valid decision and retained the pending request.

The shared fix keeps the native submitter enabled, marks it aria-disabled=true
and aria-busy=true for loading feedback, and prevents subsequent submissions while
the form is aria-busy. This covers repeated activation, the other decision button,
and implicit Enter. The existing loading text/spinner is retained. pageshow removes
busy/disabled ARIA state and restores the original label. Opted-out forms,
non-button submitters, and already-prevented submit events are not changed.

Ponytail full favors a shared fix instead of a cancellation-only workaround.
Existing Bare CSS, base.css, native forms, PSU identity and focus are preserved.
Anti Slop/human/mobile review: no new visual asset, color, layout, or animation;
native keyboard submission, textual loading, selected outcome, and error recovery
remain visible. Dials remain ENERGY 1 / RHYTHM 2 / MOTION 1. Changed behavior was
reviewed against current Web Interface Guidelines for forms, focus, and states.

## Automated evidence

- Before the fix, the new Node behavior checks failed 4 of 6 cases, including
  both named decisions and duplicate-submit prevention. After the fix: **6 passed**.
- Dependency-free Node VM checks execute the real shared JavaScript with small DOM
  doubles. They cover Approve/Reject value preservation, duplicate/other-button/
  implicit submissions, pageshow restoration, opt-outs, pre-cancelled submits,
  unnamed buttons, and independence of separate forms. They are not a browser DOM
  simulation; actual form serialization is verified by the browser check below.
- Focused pytest cancellation/coordinator/UI run: **18 passed** in 37.03 seconds.
  New route checks cover both decisions, CSRF rejection/acceptance, notes, reviewer
  identity/time, registration status, one audit/notification, final-decision replay,
  and denial of cross-campus or wrong-role decisions.
- The pytest wrapper for the JavaScript checks passed (**1 passed**, invoking
  those 6 Node cases). It explicitly skips when Node.js is unavailable.
- Windows sandbox blocked Node's subprocess (EPERM). The approved rerun outside
  the sandbox passed; no application protection was weakened.

Commands:

```powershell
node --test tests/form-submit-state.test.cjs
.\.venv\Scripts\python.exe -m pytest tests/test_app.py::TestCancellationReview tests/test_app.py::TestCoordinatorFeatures tests/test_ui_structure.py -q -p no:cacheprovider
.\.venv\Scripts\python.exe -m pytest tests/test_form_submit_state.py -q -p no:cacheprovider
```

## Browser evidence

- MariaDB connection was refused (10061), including the approved outside-sandbox
  probe. No database service was started, no actual data was modified, and the
  existing copied MariaDB database was not used or changed.
- Safe fallback: isolated in-memory SQLite preview on localhost:5056 with CSRF
  enabled, email suppressed, one QA coordinator and two pending fixture requests.
- Real sign-in reached the requested cancellation queue. Desktop click Approve
  displayed success and moved the correct volunteer to Approved with its note.
- At a 390px viewport, Enter on Reject displayed success and moved the other
  volunteer to Rejected with its note. Pending queue became explicitly empty.
  All view showed both final decisions and no review forms for them.
- Mobile client/scroll widths: 390/390px. No browser console errors were reported.
- Screenshot: cancellation-decisions-fixed.png in the session visualization folder.
  Preview tab closed, viewport reset, and temporary server stopped afterward.

## Limits and remaining work

Full pytest suite and copied-MariaDB browser rerun were not performed. Browser
duplicate-click throttling and actual back-forward cache restoration were covered
only by the Node behavioral checks, not browser timing instrumentation. Native
screen-reader announcements, actual browser zoom, and physical touch were not
independently tested. Other form workflows were not exhaustively repeated.

The separate future-attendance/premature completion and certificate-eligibility
finding was subsequently repaired locally; see ATTENDANCE_TIMING_QA.md for its
separate verification and limits. All changes in this repair are local and uncommitted.
