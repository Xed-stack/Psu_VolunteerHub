# New Railway database: 2026 activity year

`seed-railway-year` provisions a **new, empty** MySQL/MariaDB database. It never
resets the main or existing demo database. Source publication and live provisioning
are separate operations; this implementation has not been run on Railway.

## Contents

- Four retained logins: `admin@psu.edu`, `director@psu.edu`,
  `coordinator@psu.edu`, `student@psu.edu`. Password hashes, IDs, roles, activation,
  profile fields, skills/interests and recorded policy acceptances are copied
  privately from the existing demo database. Campus codes preserve assignments
  even if reference IDs differ. Session cookies and password-reset tokens are
  not transferred; use a separate app secret and sign in again.
- 180 volunteers including the retained student, nine coordinators including the
  retained coordinator, and the two retained management accounts: **191 users**.
  Generated accounts have undisclosed random passwords and `.invalid` addresses.
- 90 external participants with independently assigned recorded sex, including
  some unrecorded responses. Volunteer responses also vary independently of names.
  Existing sex-disaggregated reports derive their counts from participation.
- 90 activities, ten per campus: 65 ended approved, two ongoing approved, 15 future
  approved, four drafts and four cancelled. Past sessions span the year in every
  campus. Future attendance and completed registrations are never fabricated.
- 25 published Director goals and 25 submitted commitments: three goals each for
  Lingayen, Urdaneta, Bayambang, San Carlos, Binmaley, Santa Maria and Asingan;
  two each for Infanta and Alaminos. Each goal has one assigned campus. Initial
  states: five not started, ten in progress, seven met, three above target.
  Targets vary from two to four activities; explicit eligible mappings determine
  completion. Activities may explicitly contribute to multiple goals.
- Partner agencies/MOAs, proposal records and PDFs, accomplishment documents,
  saved drafts, announcements, withdrawals/review requests, in-app notifications,
  AOP history and Needs Attention assessments/follow-ups/closed history.

Visible generated titles, references, names, PDFs and filenames have ordinary
wording. The private seed audit records generated-data provenance; these are
fictional presentation records, not institutional evidence. No signatures or seals
are generated. No historical aggregate totals are invented. Existing source
policy text is copied unchanged; missing acceptances/profile fields still require
the default account holder to complete the normal login gates.

Dates use Philippine time at execution, with an intentional **1 November through
20 December 2026** execution window. Two ongoing activities end a few hours after
execution; future activities and AOP totals then progress naturally with time.
This is a snapshot, not a permanently frozen demonstration clock.

## Prepare the separate destination

1. Provision a separate Railway presentation app, new MySQL service and persistent
   upload volume. Retain the old demo/main services and databases. Keep the new
   app private and stop its web replicas/background writers during provisioning.
   Use a private one-off operator environment with the same image, database and
   mounted upload paths; do not place the command in startup or build hooks.
2. Deploy the reviewed source containing the command using the repository's
   Dockerfile. It includes the new module automatically through `COPY app` and
   builds CSS. Do **not** run `init-production`, an old reset/seed command or
   incremental migrations first: the destination must have zero tables/views.
   The command creates the complete current schema explicitly.
3. Configure the destination's usual production settings, including its own
   `SECRET_KEY`, `DATABASE_URL`, HTTPS/proxy configuration and persistent
   `PRIVATE_UPLOAD_FOLDER=/data/private`. Its `/app/static/uploads` link must
   point to persistent `/data/public`, as established by the Docker startup.
   Ensure the operator environment also has that link if startup was bypassed.
4. Set `MAIL_SUPPRESS_SEND=true` on the **whole presentation app** and keep it
   enabled. Generated records and notifications never require email delivery.
5. Independently verify and set these private variables. Do not put secrets in
   shell history, source files, screenshots or committed manifests:

   | Variable | Value |
   | --- | --- |
   | `RAILWAY_SEED_SERVICE_ID` | The new destination app's exact service ID; checked against `RAILWAY_SERVICE_ID` |
   | `RAILWAY_SEED_DATABASE_HOST` | New MySQL private hostname, without scheme/port |
   | `RAILWAY_SEED_SOURCE_DATABASE_URL` | Existing **demo** MySQL SQLAlchemy URL, preferably using a SELECT-only account |
   | `RAILWAY_SEED_SOURCE_HOST` | Independently verified existing demo MySQL hostname |
   | `RAILWAY_SEED_SOURCE_UPLOAD_FOLDER` | Only if retained accounts have photos: protected source upload root containing `profiles/<existing filename>` |

The source snapshot uses a read-only consistent transaction and never starts the
source application. Only the four accounts, their profile/association/acceptance
records and required policy/reference information are read. The source account
roles must match the current three-role app (`admin@psu.edu` is a Director). A
legacy `admin` role stops preflight instead of silently changing it.

If photos exist, privately copy only those files from the old upload volume to
the protected source-upload folder. The new seed copies them to the destination
public upload folder and preserves their original paths. Missing photos stop the
operation before schema creation. Existing unrelated destination files are never
overwritten.

## Review and run

From the **new app's configured operator environment**, substitute the exact
destination database name (often `railway`, but verify it):

```sh
python -m flask --app wsgi:app seed-railway-year --database EXACT_DATABASE_NAME --year 2026 --dry-run
```

Dry run checks the destination, four source accounts, required photo availability
and date window. It writes no schema, rows or uploads. Review the displayed host,
database and totals; independently verify the source still points to demo.

```sh
python -m flask --app wsgi:app seed-railway-year --database EXACT_DATABASE_NAME --year 2026
```

Enter `SEED 2026 <displayed-host>/<exact-database-name>` at the interactive prompt.
Do not pipe a confirmation. All inserts use one transaction with foreign keys
enabled; documents are staged and copied exclusively before commit. Generated
file collisions abort without replacing existing files.

The internal manifest records reference time, goal expectations, row fingerprints,
actual registration/attendance totals and upload checksums. Run the same command
with `--dry-run` **immediately before opening the app** to verify the result.
A repeat run performs verification only. Once users log in or operate the system,
changed rows can make strict manifest verification fail; this never resets data.
No command option bypasses the populated-database restriction.

Remove source connection variables and the temporary protected photo copy after
provisioning, keeping only the new app's own database credentials. Preserve the
manifest and audit in the destination. Back up the new database and uploads,
then enable presentation access after the checks below.

## Acceptance and recovery

Sign in using the four existing passwords. Check Director campus totals/AOP
progress, sex-disaggregated participation, annual charts, Needs Attention and
review history; Coordinator scope, drafts, MOAs, attendance and withdrawal
requests; Student past participation and future registrations. Download a proposal,
MOA and accomplishment PDF, plus activity/AOP CSV and PDF exports. Check a mobile
viewport and the same uploads after a redeploy.

Review persistence feature flags independently. The seeder creates review storage
and history but does not change `FINDING_REVIEWS_ENABLED`. Either existing review
mode retains its configured behavior.

MySQL DDL commits independently. A failed run can leave an empty schema even when
all seed rows roll back. Do not rerun schema initialization or delete existing
data to get past preflight: inspect the failed destination, retain diagnostics,
and deliberately provision another empty QA/presentation database. The command
cleans only files it created before a failed transaction. A process kill may leave
orphan files; inspect these before retrying. A post-commit cleanup failure retains
committed data and files and directs the operator to verification.

Recovery switches only the new presentation app to its retained prior configuration
or restores a verified matching database/upload backup. The old demo and main
databases are never modified by this command.

## Verification

Focused tests: `tests/test_railway_year_dataset.py`. Optional local MySQL/MariaDB
integration: `tests/test_railway_year_mysql.py`; it requires
`RAILWAY_YEAR_MYSQL_TEST=1`, an explicitly local `RAILWAY_YEAR_MYSQL_TEST_URL`, and
an empty private `RAILWAY_YEAR_MYSQL_UPLOADS` folder. It creates/removes only unique
`psu_seed_year_qa_<random>_{source,target}` schemas; it never reads operational tables.

Headless browser runner: `python scripts/qa_railway_year.py`. It creates its own
synthetic SQLite source/destination under ignored `.qa-railway-year-browser-temp`,
uses CSRF-protected real login forms, and checks the four accounts, reports,
exports and a protected download. Its known password exists only in this synthetic
QA source. No operational passwords are introduced or changed by the seeder.

24 November 2026 verification: 62 focused seed/Railway/AOP/review cases passed;
the final 14-case seed rerun also passed. One separate MariaDB 10.4 integration
passed on a newly initialized local server at port 33319, including read-only
source access, complete provisioning and strict repeat verification. Headless
Chromium passed 30 checks. The reference run produced 1,970 registrations, 1,327
recorded attendance rows and 135 readable PDFs. A representative PDF was rendered
with Poppler and visually inspected. No full-suite, hosted Railway, physical-device,
manual screen-reader or backup-restore verification is claimed.
