# UI and workspace overhaul · 13 November 2026

This release is local source work. It has not been committed, pushed, deployed,
or applied to an existing operational database. Preview and acceptance checks
use disposable SQLite data. Existing account data, uploads, and the untracked
system documentation document were not reset or replaced.

## Build and entry points

- Install Python dependencies from `requirements.txt` in the project environment.
- Run `npm ci --ignore-scripts`, then `npm run build`. The pinned Tailwind CLI
  compiles `ui/app.css` into `static/styles/app.css`; all four shared layouts load
  this file. Existing role styles remain as unused migration reference files.
- The Dockerfile builds CSS in a Node build stage and copies only the compiled
  stylesheet into the Python runtime. Node is not a production runtime dependency.
- Existing Director/Coordinator dashboard links redirect to `/workspace/overview`.
  Analytics links open `/workspace/reports`; explicit `view=historical` URLs
  redirect to the separate, campus-scoped historical source-record screen.
- `/workspace/activities` opens a paginated schedule list. Each activity has
  separate details, registrations/expected audience, attendance, external roster,
  documents/announcements, and combined report screens. Upcoming registrations
  remain separate from attendance records.
- `/workspace/create/1` through `/workspace/create/4` form one saved activity draft.
- `/workspace/management` links users, categories, settings, policies, and imports.
- `/profile?section=account`, `preferences`, and `impact` separate account forms,
  interests/photo, and participation milestones. Registration history has its own
  `/workspace/registrations` list and individual detail screens.

## Upgrade an existing database

Do this separately from source review. Take and verify a database/upload backup
first, record the exact deployed source revision, and retain the IDs of accounts
whose role is `admin`. Pause writes while upgrading the schema and application.
Never run a seed/reset command as part of this upgrade.

Use the standalone script when the old development schema cannot start the new
application factory. It reads the configured database URL without starting Flask:

```powershell
.venv/Scripts/python.exe scripts/migrate_workspace.py --database EXACT_DATABASE_NAME --dry-run
.venv/Scripts/python.exe scripts/migrate_workspace.py --database EXACT_DATABASE_NAME
```

The database name must exactly match the configured connection. Inspect the dry
run before applying. The equivalent Flask command is `flask migrate-workspace
--database EXACT_DATABASE_NAME`, with optional `--dry-run`, when the factory can
start against the target. `migrations/20261113_workspace_overhaul.sql` is a
one-time SQL alternative; use one migration method, not both.

The resumable migration adds draft, agency/MOA, and external-group tables; activity
lifecycle/proposal/audience/department fields; and the external group reference.
It backfills published activities as Approved, with no fabricated attachments,
and changes existing Admin accounts to Director without changing account IDs or
passwords. The MySQL enum then permits exactly three roles. Audit JSON and old
cancellation-request records remain intact. MySQL DDL commits independently;
if interrupted, inspect the schema and rerun the resumable command.

Production startup does not execute this migration. The existing application
database was not upgraded during this implementation. The MySQL-specific DDL and
full Docker build require validation in the target staging environment; the
Docker daemon was unavailable locally.

## Behavior and calculation rules

- Schedules are naive Philippine local datetimes, matching existing storage.
  New activities require future start and later end times. Server time checks
  use an explicit UTC+8 clock rather than the host timezone.
- Publishing requires a privately stored approved PDF/DOCX proposal. Readable
  labeled fields are extracted locally, then reviewed. Unreadable/scanned files
  use manual entry. This is not OCR or arbitrary-document semantic extraction.
- The activity's numeric participant target and capacity remain separate from
  participant type and audience departments. Audience targeting does not enforce
  admission restrictions. Matching accounts receive in-app notifications.
- New agency records contain a name, contact person, email/phone. MOAs contain a
  reference, validity dates, and private document. Selected MOAs must cover the
  activity date.
- Attendance can be written only while `start <= Philippine now < end`, for an
  Approved activity. All current internal/external write paths recheck the time
  before commit. Legacy activities without an end are read-only. Unrecorded rows
  remain unrecorded; later corrections use printed reports.
- Present/confirmed participation derives completion after the scheduled end,
  without a late attendance write. Existing completed attendance remains valid.
- Coordinators cancel their own campus activities with a reason, preserving the
  activity and registration history. Volunteer withdrawals free a place directly
  before the deadline. Old cancellation decisions are retained but not processed.
- Recommendations require a positive cosine match to selected interests, with
  preferred-campus matches first, then descending similarity, date, and ID.
  Missing interests show an actionable empty state, not unrelated recommendations.
- Dashboard account totals are all-time within campus scope; activity measures
  use the selected reporting period. Verified attendee values count recorded
  presences at conducted activities, so repeat attendance counts again.
- Annual goal evidence reuses existing approved definitions and calculations.
  Unknown evidence stays pending. Different units have separate comparisons.
  Annual AOP results remain annual even when activity reporting is quarterly.
- Activity report tables paginate; exports cover all matching records. A selected
  activity's PDF/Excel/CSV also includes its named attendance roster. AOP exports
  use `report=aop` and include verified target/actual charts in PDF/Excel.

## Saved input and imports

Signed-in ordinary data-entry forms use allowlisted fields in server-side drafts,
owned by account and campus. A campus change prevents access to the previous
campus draft. Save status distinguishes pending, saved, restored, and failed saves.
The browser waits for pending draft operations before final submission so a late
autosave cannot recreate the submitted draft.

Supported staged attachments are privately retained and reattached on submission;
replacement and completed/discarded generic drafts clean up staged files.
Activity proposals are retained directly in their activity draft and transferred
to the published activity. Passwords, CSRF/authentication tokens, action commands,
and unsubmitted consent are excluded from draft payloads. Public signup uses
browser-session storage for ordinary fields only and clears it after success.

Director Import exposes user, historical-activity, and annual-plan imports through
validation preview and explicit confirmation. Existing duplicate/immutability
rules are retained. User previews store password hashes, never plain passwords.
Private abandoned import-preview files have no automatic retention schedule;
operators may remove expired unreferenced previews during routine maintenance.

## Rollback

Roll back application source to the recorded prior revision while retaining the
additive schema and private files. Restore the four-value role enum before
restoring the recorded former-Admin role assignments. Keep newly created users
and event/attendance changes; do not overwrite the live database with an old dump.
Retain the new workflow data for recovery. An older release does not understand
activity cancellation or locked-attendance policy, so keep activity writes paused
until those semantics have been explicitly addressed in the rollback release.

## Verification

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_workspace_overhaul.py tests/test_workspace_migration.py tests/test_report_queries.py tests/test_profile_settings.py -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py
```

See `docs/qa/UI_WORKSPACE_OVERHAUL.md` for measured results and limitations.
