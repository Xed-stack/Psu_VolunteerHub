# 2026 Presentation Dataset

This command replaces the operational data in **PSU-Volunteer-Hub-Demo**.
All generated identities, activities, approvals, and participation records are
fictional presentation material, not institutional evidence. Names and activity
content intentionally use ordinary wording. The reset audit entry retains this
provenance. Institutional-style generated addresses can coincide with real
mailboxes: keep outbound mail suppressed throughout presentation use.

Implementation is local until explicitly released. These instructions do not
authorize a deployment or live reset. Never use the older
`reset-and-seed-demo` command for this dataset: it keeps only three accounts and
has different data volumes.

## Result and preserved records

- Keep `admin@psu.edu`, `student@psu.edu`, `director@psu.edu`, and
  `coordinator@psu.edu`, including IDs, password hashes, names, roles, campus
  assignments, activation state, session versions, profiles, interests, skills,
  reset tokens, and existing policy acceptances. Clear only obsolete profile
  participation history. The four accounts must already be active; student and
  coordinator must already have official campus assignments.
- Generate 80 student volunteers and eight staff coordinators with distinct
  Filipino names, campus-valid affiliations, skills, interests, and independently
  assigned demographic responses. Each campus has one coordinator. Generated
  accounts have random undisclosed passwords; use the four default logins.
- Keep the nine campus IDs, reference catalogues, settings, policy revisions, and
  authentication throttle records. Deleted policy publishers become null.
- Replace all activities, registrations, attendance, cancellations, historical
  aggregates, cached analytics, recommendations, announcements, milestones,
  notifications, old audit entries, annual plans, indicators, targets, results,
  mappings, proposals, and all non-default accounts and their account records.
- Create 28 activities, 30 linked annual goals, and 24 cancellation requests
  (eight each pending, approved, rejected). No external participants or invented
  aggregate results. Existing report functions calculate goal results.
- The dated definitions produce 432 registrations and 296 attendance records,
  with present, absent, excused, and unrecorded outcomes.
- Do not create policy acceptances or claim consent on behalf of preserved
  accounts. Existing profile and policy gates still apply after login.
- Uploaded files remain on disk, even when their old database references are
  removed. Do not delete uploads as part of this operation.

| Campus | New volunteers | Ended / upcoming | Targets: activities / attendance / unique | Goals met / pending |
| --- | ---: | ---: | --- | --- |
| Lingayen | 12 | 3 / 1 | 3 / 32 / 12 | 3 / 0 |
| Urdaneta | 11 | 3 / 1 | 3 / 30 / 11 | 3 / 0 |
| Bayambang | 10 | 4 / 0 | 4 / 45 / 14 | 1 / 0 |
| San Carlos | 9 | 2 / 1 | 3 / 24 / 10 | 2 / 0 |
| Binmaley | 9 | 2 / 1 | 3 / 25 / 10 | 0 / 3 |
| Santa Maria | 8 | 3 / 0 | 3 / 24 / 9 | 3 / 0 |
| Asingan | 8 | 2 / 1 | 3 / 24 / 9 | 0 / 0 |
| Infanta | 6 | 1 / 1 | 2 / 16 / 7 | 0 / 3 |
| Alaminos | 7 | 2 / 0 | 2 / 18 / 8 | 2 / 0 |

The 22 ended activities run February through 24 October. Six future activities
run 14 November through 19 December. Execution is restricted to **25 October
through 13 November 2026**, so all dates and workflow states remain coherent.
For a later presentation, review and change the dated definitions and tests;
do not bypass the date guard. Goals have 31 December deadlines, so remaining
goals are not described as overdue in November.

Binmaley has partial attendance and Infanta has none recorded. University goals
(20 activities, 220 attendance occurrences, 60 unique attendees) also remain
pending because their evidence includes those records. Asingan has three
verified shortfalls. The Director ranking can tie campuses with pending
evidence at zero achievement; goal details distinguish pending evidence from
verified shortfalls. No ranking rules are changed.

The default student has past attendance, upcoming applications, and cancellation
examples. The default coordinator receives cancellation reviews and attendance
follow-ups. If that coordinator belongs to Bayambang, Santa Maria, or Alaminos,
one pending request is an older request submitted before its activity deadline,
still unresolved after an absent attendance outcome. The existing review route
supports resolving it. Their campus assignment is never changed.

## Operator preparation and backup

1. Verify the released source includes `reset-and-seed-presentation`. Use the
   **presentation application's** interactive shell, not the main app, Python
   REPL, build command, or automatic startup hook. Check the app's database
   reference points to the presentation MySQL service.
2. Set `MAIL_SUPPRESS_SEND=true` in the presentation app's Railway variables and
   restart/redeploy that app so web workers also load the setting. Leave it
   enabled while fictional institutional addresses remain. Setting it only in
   the operator shell does not suppress the running application's mail.
3. Independently verify the presentation MySQL private hostname from Railway's
   database service reference. Set `PRESENTATION_DATABASE_HOST` in the app's
   variables to that exact hostname, without URL scheme, port, or credentials.
   The command compares it with its configured engine host. The approved app
   service ID is `5ba9ae8d-fdd4-4850-a193-dcb5760a6e72`.
4. Pause all public access, app replicas, background writers, and other operator
   sessions for this database while retaining a private operator shell. The
   command is not a maintenance-mode feature and does not stop concurrent
   writers. Do not resume writes until verification completes.
5. From an environment with database client access, create a full SQL backup and
   a separate copy/snapshot of the upload volume. The following Linux shell
   commands assume privately supplied `PRESENTATION_DB_HOST`,
   `PRESENTATION_DB_USER`, and `PRESENTATION_DB_NAME` values for the verified
   destination, and a protected writable backup directory. Enter passwords at
   the prompt; do not put them in command arguments or source files.

   ```sh
   umask 077
   mysqldump --host="$PRESENTATION_DB_HOST" --user="$PRESENTATION_DB_USER" \
     --password --single-transaction --quick --routines --triggers --events \
     --hex-blob --result-file=/secure-backups/presentation-before-reset.sql \
     "$PRESENTATION_DB_NAME"
   ```

   Require exit status zero and a nonempty dump. Use a client compatible with
   the server; do not suppress dump errors. If the service shell lacks the
   client, use a private administrative environment or a verified Railway
   database backup plus an export. Never install tools as an unreviewed reset
   side effect. Store backups outside Git with restricted access and encryption.
   Test the SQL and upload restoration into a separate disposable database and
   upload location before relying on them.

## Inspect, reset, and verify

The schema must already match the current application models, every table must
use InnoDB, and foreign key checks must be enabled. Resolve any preflight error
before continuing; this command performs no schema migrations or provisioning.

```sh
flask --app wsgi:app reset-and-seed-presentation --database railway --dry-run
```

Check the displayed host/database and app service ID, all four preserved IDs and
roles, every deletion count, and replacement totals. Dry-run never writes.
Then, with the backup verified and writers paused:

```sh
flask --app wsgi:app reset-and-seed-presentation --database railway
```

Type exactly `RESET PRESENTATION <displayed-host>/railway` when prompted. Never
pipe an automatic confirmation. The command deletes and inserts in one
transaction with foreign keys enabled, validates preserved accounts and goal
outcomes, then commits once. Failure before commit rolls back all row changes;
auto-increment gaps on MySQL/MariaDB can remain after rollback.

The success message includes exact registration and attendance totals. Verify
92 users (81 volunteers, nine coordinators, one Admin, one Director), 28
activities, 30 goals, 24 requests, no external participants, and one reset audit
entry. Sign in using all four preserved accounts. Check:

- Student: opportunities, participation history, upcoming applications and
  cancellation statuses; complete existing policy/profile gates if necessary.
- Coordinator: its own activities, attendance follow-ups, and pending requests.
- Director: 2026 annual goals, campus details, attendance analytics, calendar,
  and CSV/PDF reports. Confirm Asingan's shortfalls and pending campus evidence.
- Admin: user list/export and retained policies/settings.

Confirm the running app still suppresses email before restoring public access.
Repeated runs replace this dataset rather than append duplicates; generated
account passwords and database IDs may change. All four default IDs/passwords
remain unchanged.

## Recovery

Keep writers stopped after a failed or uncertain operation. If the command
failed before commit, inspect the preserved records and original counts first;
do not automatically run another reset. A lost connection during commit has an
uncertain outcome and must be checked against the reset audit and counts.

For post-commit recovery, restore the verified dump into a **separate empty
recovery database** and restore uploads into a separate volume/location:

```sh
mysql --host="$RECOVERY_DB_HOST" --user="$RECOVERY_DB_USER" --password \
  "$RECOVERY_DB_NAME" < /secure-backups/presentation-before-reset.sql
```

Verify restored counts, preserved account sign-ins, relationships, and upload
access, then explicitly reconfigure only the presentation app to use the
restored database and uploads. Keep the replaced database for investigation.
Resume access after validation. Do not overwrite the main database, drop a
database, or restore old credentials into another application automatically.

## Local verification

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_presentation_dataset.py tests/test_demo_dataset.py tests/test_system_performance.py tests/test_annual_goals.py tests/test_campus_ranking.py tests/test_report_queries.py -q -p no:cacheprovider
git diff --check
```

The optional MariaDB/MySQL test requires `PRESENTATION_TEST_DATABASE_URL` to name
an **empty disposable database**, using `127.0.0.1` and a name starting with
`psu_presentation_test_`. It creates and retains test tables there and never
uses the configured application database. Run the selected test against a fresh
empty target; do not reuse a database containing application data.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_presentation_dataset.py -k disposable_mariadb -q -p no:cacheprovider
```

No production credentials or SQL exports belong in this repository.

Verified locally on 1 November 2026: 19 presentation tests and 59 existing
regression cases passed across targeted runs. The optional integration test
also passed separately against disposable MariaDB 10.4.32 with foreign keys
enabled, including rollback and repeat replacement. Five final presentation
checks passed after the last content/capacity adjustments. This evidence does
not establish that the code is deployed or that Railway has been reset.
