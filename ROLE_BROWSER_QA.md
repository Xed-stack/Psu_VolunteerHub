# Four-role browser workflow review

Date: 18 October 2026. Outcome: **core workflows exercised; two confirmed findings**.
This is not a claim that every feature, boundary, or destructive action passed.
No application fix, commit, or push was performed during this review.

## Isolation and original database

- User approved a disposable local copy of the actual database and test accounts.
- Source `psu_volunteer_hub` connections used server-enforced read-only sessions.
  The application factory was never pointed at the source database by the QA server.
- Created `psu_volunteer_browserqa_20261018_a14c` on the local MariaDB server.
  All 31 base tables and 1,156 rows matched source row-count/SHA-256 fingerprints
  before adding fixtures. This copied actual data/schema, not SQLite fixtures.
- Dedicated accounts for Volunteer, Coordinator, Director, and Admin were added
  only in the copy. Existing passwords/accounts were not reset. Active Terms and
  Privacy records were pre-acknowledged for those QA accounts during setup; policy
  acceptance itself was not browser-tested.
- CSRF remained enabled. Email sending was suppressed. Server bound only to
  `127.0.0.1:5056`. Static/private uploads were copied into a separate QA folder.
- The test activity used a clearly nonbinding QA acknowledgement, not the real
  participation terms. No real activity was joined or cancelled.
- After browser testing, all 18 original-database read-only report checks passed
  again. Original counts remained 9 campuses, 35 activities, 98 registrations,
  81 attendance records, and 216 historical records. No QA accounts or activities
  existed in the original. This is a count/report recheck, not a full before/after
  bytewise comparison of the original after testing.
- Server stopped, temporary browser tab closed, viewport reset. The QA database,
  copied files, diagnostics, screenshots, and downloaded reports remain locally
  available for reproduction. They contain copied data and should not be published.

## Findings requiring approval to implement

### P1: Coordinator cancellation approval does not submit the decision

1. QA volunteer joined `[Browser QA] Participation workflow`, then submitted a
   cancellation request with Other and a QA-only explanation.
2. QA coordinator opened Cancellation requests and clicked Approve on that row.
3. The page reported `This request is no longer available for review.` The request
   remained pending. The failure was reproduced a second time.

Code evidence: `static/scripts/form-submit-state.js:24-30` synchronously disables
the submitting button. The cancellation form puts the decision in the clicked
button's `name="decision"` / `value="approved"`. A disabled submit button is not
included in the form payload; `app/routes/coordinator.py:258-263` then rejects a
missing decision. This is the identified code-path explanation; raw browser
request bodies were not captured. Reject shares the same named-button mechanism
but was not separately clicked. Fix the shared submission behavior and add a
real-browser regression before claiming this flow passes.

### P1: Future activity can become completed and certificate-eligible

The activity starts 1 November 2026, after this 18 October review. Attendance
Management nevertheless accepted Present and immediately set the registration
to Completed. The volunteer profile showed one verified attendance, one completed
participation, and `Eligible` in the certificate column. SQL confirmed a completed
registration with an attendance row while the event date was still in the future.

`app/routes/coordinator.py:577-635` checks campus ownership and submitted statuses
but has no activity-time guard before assigning completed status at line 619.
Help states that attendance is recorded after the activity. Recommend an explicit
server-side timing rule (including end-time/legacy behavior), matching disabled UI,
and boundary tests. No certificate was generated or issued in this review.

## Exercised coverage

| Role | Passed observations | Failed or limited |
| --- | --- | --- |
| Volunteer | Sign-in/logout, profile preference save and persistence, recommendations, activity search, nonbinding test registration, Registered state/capacity decrement, dashboard registration, Other cancellation request, profile participation/history, mobile navigation/logout, Help guide replay/Next/Back/Skip | Cancellation approval could not complete; premature eligibility observed after attendance. Photo upload/remove not tested. |
| Coordinator | Sign-in/dashboard, test activity creation with SDG/custom QA acknowledgement, location edit/save, attendance save, activity-name report search, report/count agreement, CSV/PDF downloads, logout | Cancellation approval failed. Future attendance accepted incorrectly. No destructive activity removal, external participant encoding, milestone/cover upload, or announcement publication tested. |
| Director | Sign-in/dashboard, two-campus include filter (23 activities), ten-row paging with both campuses retained, activity-name search, matching two-row CSV/PDF, exclude-filter empty state, read-only calendar, logout | Additional historical export, demographic/year combinations, and guide steps not exhaustively exercised. |
| Admin | Sign-in/dashboard, category creation, editing dedicated QA user's name, deactivation and reactivation of that QA user, audit trail, safe user CSV export, malformed CSV rejection, settings display, logout | No password/reset credential changes, successful user import/account creation, permanent deletion, policy publication, backup/restore, or security-setting changes performed. |

Authorization browser checks passed:

- Volunteer received 403 for Admin dashboard, Coordinator dashboard, and Director
  Analytics direct URLs.
- Coordinator received 403 for another campus's event-edit and attendance URLs,
  and for Admin dashboard access.
- This is sampled role/campus coverage, not a complete authorization/security audit.

## Evidence and limits

- Real browser submissions ran against the disposable MariaDB copy, with normal
  JavaScript and CSRF protection. Native form checks and actual resulting pages
  were observed, not just direct Flask-client requests.
- Coordinator searched report: 2 QA activities, 1 registration, 1 attendance,
  1 completed participation. CSV/PDF downloads completed; CSV rows/totals and
  metadata were checked. PDF visual layout was not independently rendered/audited.
- Director's two-campus report contained 23 activities, 58 registrations, and
  50 attendance records. Paging retained repeated campus parameters. Searching
  `[Browser QA]` returned the same two activities as the coordinator report.
- Admin export header excludes password hashes, auth versions, and reset tokens.
  Malformed CSV displayed the template mismatch error without creating accounts.
- Volunteer profile at 390px: client/scroll widths 375/375px. Mobile menu and guide
  navigation worked. No browser console errors were reported in the inspected log.
- Source snapshots/settings were not changed to make failed workflows pass.
  No application code was changed and no full automated suite was rerun here.
- OS screen-reader output, actual zoom, physical touch, SMTP delivery, and
  destructive browser confirmations remain outside this review.
- Screenshots in the session visualization directory:
  `qa-cancellation-failure.png`, `qa-volunteer-mobile.png`,
  `qa-coordinator-report.png`, and `qa-director-report.png`.
