# Finding Review Workflow

The workflow is disabled by default. Deploying the code alone preserves the existing generated findings and notification behavior. Ordinary application startup does not create review storage.

## Enable in a Prepared Environment

An authorized operator should back up the intended database and confirm the application's configured database name. Use the existing environment and credentials; do not run database initialization or demo-seeding commands.

```powershell
.venv/Scripts/python.exe -m flask --app wsgi:app migrate-finding-reviews --database EXACT_DATABASE_NAME --dry-run
.venv/Scripts/python.exe -m flask --app wsgi:app migrate-finding-reviews --database EXACT_DATABASE_NAME
```

The explicit migration requires existing `users`, `campuses`, and `events` tables. It adds only `finding_reviews` and `finding_review_events`, matching parent ID types. It refuses incomplete existing review tables or a missing unique finding key. Repeat application creates nothing. The exact database-name check is mandatory.

Alternatively, select the intended MySQL/MariaDB database in a client supporting `DELIMITER` and execute `migrations/20261122_finding_reviews.sql`. Use either migration path. DDL may implicitly commit; inspect storage after an interrupted operation before retrying. The SQL path uses a temporary migration procedure and requires permission to create/drop it.

After verifying the two tables, set `FINDING_REVIEWS_ENABLED=true` in the application's environment and restart the application. Confirm the Director Overview shows Active Reviews and that a synthetic or operator-approved assessment can be saved and retrieved. No operational migration or activation was performed during local implementation.

## Behavior and Permissions

- GET requests derive findings and reconcile saved decisions without inserting or updating reviews. A finding is first persisted on an explicit Director action.
- Directors can save assessments, send eligible follow-ups, close with an assessment and reason, or reopen with an explanation. Concurrent changes produce a conflict instead of overwriting another decision.
- Completed occurrences preserve evidence, assessment, author and timestamp in append-only application history. Coordinators can read completed occurrences for their own campus. The current role model merges administration into Director; there is no separate read-only Admin account type.
- Event identity is campus/activity/finding type; annual identity is campus/year/type; planning identity uses canonical period boundaries. Participant filters cannot create alternate review identities or partial-event evidence.
- A closed finding returns to Active when materially changed evidence still triggers it. Cosmetic names and cancelled registrations do not reopen it. Earlier completed occurrences remain readable. A saved open finding whose source clears remains available for a final assessment.
- Historical attendance, participant targets, annual calculations and editing restrictions are unchanged. System-default absence remains distinct from recorded absence. No historical backfill or bulk closure occurs.
- Follow-up is available only where the source supports an actionable request and an active campus Coordinator exists. Equivalent unread notifications are reused. Legacy notifications do not establish persisted review status.
- Active results are derived over the complete report scope before pagination. Reviewed history and detail history use database pagination, 25 records per page. Schema availability is cached only for the current request; review state is read again on each request.

## Rollback and Limits

Set `FINDING_REVIEWS_ENABLED=false` and restart to restore the existing findings interface. Retain both tables and their history. Code rollback must remove only this workflow's source/presentation changes and restore its generated CSS; do not remove unrelated working files or delete review data.

Both migration paths passed isolated MariaDB 10.4.32 tests with signed INT and BIGINT UNSIGNED parent IDs. SQLite workflow tests also passed. MySQL 8, operational migration, production concurrency/load, physical devices and manual screen-reader use were not tested. Database availability still depends on the existing application connection/error handling.
