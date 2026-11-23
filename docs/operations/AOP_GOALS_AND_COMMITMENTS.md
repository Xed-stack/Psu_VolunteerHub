# Dated AOP Goals and Campus Commitments

Source change on `codex/ui-workflow-overhaul`. The user subsequently authorized
commit/push to that branch on both `origin` and `thesis`. Operational migration and
deployment remain unauthorized.

## Behavior

- A Director publishes a university activity target with a year and inclusive
  Start Date/End Date, both within that year. Campus commitments share that period.
- A Coordinator saves a draft or submits a positive whole-number commitment.
  Submission takes effect immediately; there is no Director approval or return step.
  Revisions preserve earlier submitted values in audit history. Draft revisions
  leave active targets unchanged and remain private until submitted/published.
- Explicitly linked approved activities earn credit once they end, independently
  of attendance. The entire schedule must be contained in the Director period in
  Philippine time. The upper bound is midnight after End Date, exclusive.
- Distinct activities count once per goal at university/campus scope. Explicit
  contributions to multiple goals remain supported. Targets are not quotas.
  Remaining is `max(target - completed, 0)`; targets are never decremented by reads.
- Earlier completed eligible activities may be linked after commitment submission.
  Schedule/status/link changes recalculate progress. Existing links that become
  ineligible remain visible with their reason. Attendance entry windows, attendance
  reporting, and recognition calculations are unchanged.
- Published year changes are blocked. Period revisions require a signed impact
  preview and confirmation, including changed linked schedules and completion counts.
- Active Coordinators receive publication/change notifications; active Directors
  receive commitment submission/revision notifications. Records and notifications
  commit together. No email or new external integration is introduced.

## Storage and Interfaces

Existing annual plans, indicators, targets, proposals, mappings, and histories are
reused. New target/proposal discriminators separate `legacy`, `director_goal`, and
`campus_commitment`; parent target IDs connect campus records to the Director goal.
Director targets store their date period; children inherit it without duplicated
editable dates. Unique campus/parent constraints and compare-and-swap versions
protect drafts, submissions, revisions, and link changes.

Existing `/annual-goals`, `/annual-goals/workspace`, proposal edit, and target detail
routes now open the new workflow. Target commitment and link-activities POST routes
enforce campus ownership, CSRF, goal versions, and eligibility server-side.
Historical AOP is available with `history=1`. Explicitly shared historical evidence
is read from the retirement archive when needed to preserve the original AOP
assessment, including aggregates and unique-person counts. This read-only context
creates no AOP target/result copies and never enters new-goal progress. Older office/program/status/basis
filters open that history explicitly rather than silently broadening their scope.
ASP requests are retired with HTTP 410; new ASP definitions/imports are rejected.

New activity draft payloads add optional `aop_goal_ids` string arrays. Existing
drafts remain valid. Publication revalidates the complete selection and records
mapping audit entries plus a named AOP snapshot. Historical AOP imports create
separate legacy records; they cannot revise existing historical evidence or write
new Director goals/commitments. No old AOP relationships or dates are inferred.

## Migration Review and Later Authorized Rollout

The explicit migration is `app/aop_migration.py`, registered as
`migrate-aop-commitments`. It is never invoked on application startup. Existing
databases need this reviewed upgrade before running the new source.

For a later authorized operation, pause application writes and take a verified
full database backup first. Review the configured database identity independently.
Use the existing deployment's Flask entry point/configuration; a development
example is:

```powershell
.venv/Scripts/python.exe -m flask --app app.py migrate-aop-commitments --database EXACT_DATABASE_NAME
```

The default is a read-only dry run. It lists schema changes and archive row counts.
There is deliberately no implicit apply. Only after a separately authorized review:

```powershell
.venv/Scripts/python.exe -m flask --app app.py migrate-aop-commitments --database EXACT_DATABASE_NAME --apply
```

The upgrade requires the existing annual workflow schema and exact configured
database name. It adds nullable period/parent columns and legacy/version defaults,
plus parent foreign keys and unique campus constraints. It snapshots retired ASP
plans, indicators, targets, results, mappings, proposals, and their original JSON
history in `retired_annual_archive` before removing active ASP rows. It does not
delete activities, registrations, attendance, or AOP evidence. Ambiguous cross-plan
proposals, unknown inbound references, and conflicting archive identities stop
retirement instead of guessing. Preserve the private archive in the database/backup;
do not export its contents into source control.

MySQL/MariaDB DDL commits independently. Additions are inspected for safe reruns;
archive insertion and active ASP removal share a transaction. After retirement,
the active plan enum is narrowed to AOP. Interrupted schema changes may already
exist even when retirement rolls back; inspect the report and rerun after repair.
Verify archive counts/content, zero active ASP, read-only AOP history, existing
activity/attendance totals, and a publish/commit/link smoke test before reopening.

Only disposable SQLite migration tests were executed here. MySQL/MariaDB execution,
concurrent multi-process locking, backup restoration, and operational volumes remain
to be verified on an authorized database clone.

## Rollback

Preserve unrelated working files and all private uploads. Before any operational
write, rollback can restore the pre-upgrade database backup and matching previous
application together. A source-only downgrade is unsafe: the older application
does not distinguish the new campus commitments from independent historical targets.

If new records have been submitted, first retain a complete post-upgrade backup
and review a recovery/merge procedure for those records before restoring or switching
databases. Do not discard commitments, notifications, mappings, audit history, or
the retired ASP archive. No automatic destructive down-migration is supplied.
