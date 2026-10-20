# Cancellation and attendance release verification

Date: 20 October 2026. Verification only; no implementation changes, commit or push.

Subsequent publication authorization: the user approved review, commit and push
of the verified repairs and documentation. The no-commit/no-push statement above
describes the verification phase, not the later publication step.

## Actual MariaDB isolation

- Reused the existing disposable `psu_volunteer_browserqa_20261018_a14c` copy.
  Did not overwrite it or recreate the original database.
- Application configuration and `SELECT DATABASE()` both verified the copy
  before fixtures or browser writes. Localhost port 5056, CSRF enabled, debug
  disabled, email suppressed. Current repository scripts/styles served so the
  old copied submit-state script could not conceal a regression.
- Four labelled `[Repair QA 20261020]` fixture activities and registrations
  were added only to the copy. Existing dedicated browser QA accounts reused.
- Original database access used server-enforced read-only sessions. Before/after
  totals matched: 31 tables / 1,167 rows. Afterward, original contained zero
  repair QA activities and zero browser QA accounts. This is a count/isolation
  check, not a completed before/after all-row hash comparison.

## Browser and persisted-state results

| Workflow | Result |
| --- | --- |
| Early check-in, keyboard Enter | Success with CSRF; registration 101 remained Confirmed, attendance Present. Certificate predicate false because not Completed. |
| Before opening window | Controls disabled with opening-time notice; fixture registration remained Confirmed and had no attendance. |
| Final attendance on same registration | Changed only the disposable fixture schedule to an ended activity, then saved through browser. Registration became Completed/Present; certificate predicate true; exactly one attendance row. No automatic completion on changing time alone. |
| Cancellation Approve, desktop click | Request Approved, registration Cancelled, review note persisted. Reviewer and timestamp present; one audit entry and one notification. |
| Cancellation Reject, 390px keyboard Enter | Request Rejected, registration Confirmed, review note persisted. Reviewer and timestamp present; one audit entry and one notification. |

Only the two new QA cancellation requests were reviewed. Other copied requests
were deliberately left unchanged, so the overall pending queue is not empty.
No console errors captured. At 390px, page client/scroll width both 375px.

Temporary application stopped, agent tab closed, viewport reset. MariaDB itself
was already running and was not started/stopped by this verification. Disposable
fixtures remain locally for reproduction; do not publish copied data or QA files.

Screenshots in the local Codex visualization folder, not Git:
`mariadb-cancellation-rejected.png` and `mariadb-final-attendance.png`.

## Automated release gate

Full collection: **334 tests**.

- Full `pytest tests -q -p no:cacheprovider`: **328 passed, 1 failed, 5 setup
  errors in 877.26s**. The failure was Node `spawn EPERM`, not a JavaScript
  behavioral assertion. The five errors were pytest's inaccessible default
  temporary directory (`WinError 5`) before image tests could execute.
- With approved outside-sandbox execution and a fresh, previously nonexistent
  QA `--basetemp`, reran `tests/test_form_submit_state.py` and
  `tests/test_profile_repair.py`: **20 passed in 52.74s**. Includes all six
  affected test outcomes; the other 14 overlap prior passes. Node wrapper
  executes the six JavaScript behavior checks.
- Thus all **334 unique collected tests have passing outcomes across the full
  run plus targeted environment rerun**. This is not a single uninterrupted
  334-pass run. No application or assertion changes were made to get these passes.
- Earlier focused early-check-in selection: 60 passed (overlapping coverage).
- `git diff --check` passed, with line-ending notices only.

Verification gate completed. Next: review the preserved local diff for a scoped
commit/push if the user approves. No publication authorized by this verification.

Scope does not include a fresh exhaustive four-role review, destructive actions,
production deployment, SMTP delivery, physical touch, or screen-reader speech.
