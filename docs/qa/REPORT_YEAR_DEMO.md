# Full-Year Report Demonstration — 2025

## Purpose and boundaries

Separate, fictional local data for the existing reporting interfaces. No operational
database is read, copied, migrated, or seeded. The existing preview on port 5000
continues independently. No commit, push, deployment, or new dependency in this pass.

Analyze: inspected both older destructive seeders, report scopes/calculations,
annual shared-target rules, private downloads, account permissions, and preview
configuration. Kept the older seeders unchanged.

Design: retain the existing PSU report layouts and components. Add a compact
directory grouped into delivery/participation and annual/source-record tasks.
Desktop uses the existing two-column directory layout; phone stacks those groups.
A pale-blue notice with a gold divider identifies fictional data without competing
with report headings. Use existing Inter, navy text, visible focus, and 44px links.
No new imagery, metrics, libraries, animations, or chart definitions.

Implement: dedicated local app configuration skips development account/activity
fixtures. Seed only existing models, in one transaction, with a fixed random seed.
Create the database/schema only under `.qa-report-year-temp`. Reject other paths,
unmarked existing databases, mismatched years, and incomplete/future years.
`--dry-run` validates without creating a database. Normal reruns retain IDs and
records. A failed first seed rolls back records; the command removes only its newly
created unsuccessful database. Generated fictional PDFs may remain in the private
demo directory after a failure and can be reused on retry.

## Dataset and preservation checklist

| Coverage | Final fixture |
|---|---:|
| Calendar year | January–December 2025 |
| Campuses | 9 |
| Activities | 216 |
| Approved / cancelled activities | 204 / 12 |
| Volunteer accounts | 450 |
| Named external participants | 180 |
| Registrations | 8,342 |
| Recorded presence | 5,984 |
| Recorded absence / excused | 893 / 371 |
| Eligible registrations without attendance | 69 |
| Cancelled registrations | 1,025 |
| Historical aggregate records | 27, separate from live totals |
| Annual targets before shared-plan deduplication | 60 |
| Campus obligations after deduplication | 36: 8 achieved, 16 pending |
| University obligations after deduplication | 4: 3 achieved, 1 below target |

- Activities use believable titles, campus departments, categories, skills, SDGs,
  schedules, capacities, participant targets, internal/external rosters, and varied
  attendance. Semester peaks and campus activity volumes differ.
- Completion requires presence. Withdrawn/cancelled registrations have no attendance;
  unmarked attendance remains unknown. Attendance write policies are unchanged.
- Representative proposals and nine fictional partner agreements are private PDFs
  visibly labelled synthetic. Supporting evidence links resolve through existing
  guarded downloads. No actual approval, consent, or personal information is claimed.
- AOP/ASP shared activity and attendance obligations deduplicate per campus. Separate
  partnership obligations include verified aggregates and pending evidence.
- University-supported activity/attendance targets explicitly cover the linked
  Lingayen, Bayambang, and San Carlos cohort. They do not substitute for campus totals.
  University AOP results: 74/70 activities, 2,105/2,500 attendance occurrences,
  and 6/5 fictional partnerships. Charts remain separated by unit.
- Historical records are separate illustrative aggregates, not duplicate live events.
  People Insights and recognition use actual seeded profile and presence records.
- Only 2025 is seeded. Demo presentation suppresses comparisons against unseeded
  previous years. Within-year comparisons still use existing calculations.
- Director is university-wide; Coordinator is restricted to Lingayen. Volunteer
  cannot access staff reports. Existing routes and operational defaults remain intact.

## Run and review

From the repository root, in PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/report_demo.py --dry-run
.\.venv\Scripts\python.exe scripts/report_demo.py
.\.venv\Scripts\python.exe scripts/report_demo.py --serve
```

Open `http://127.0.0.1:5001/demo`. Default database:
`.qa-report-year-temp/annual-reports-2025.sqlite`.
The directory links to Overview, Summary, Activity Records, Participation Records,
Annual Plans, Indicators, Historical Records, People Insights, and Recognition.
Follow record links for combined activity reports, proposal downloads, and evidence.

Credentials are recorded locally in
`.qa-report-year-temp/annual-reports-2025-credentials.json`:
`director@psu.edu`, `coordinator@psu.edu`, and `student@psu.edu`.
These three fictional local accounts use `password` per user request. Other synthetic accounts
have an unknown generated password. Do not publish credentials or demo databases.
The demo uses a separate session cookie and suppresses outgoing email.

`--year 2024 --database .qa-report-year-temp/reports-2024.sqlite` creates a separate
completed-year fixture. Always pair a different year with a new database path.
Use `--port` only for another loopback port; keep the original preview on 5000.

The JSON manifest beside the database records calculated totals, monthly values,
campus counts, attendance states, and annual results. Rerunning the seed does not
reset edits or upgrade an existing fixture; use a new database filename to generate
a fresh fixture from changed seed definitions.

CSV downloads have a synthetic-notice row before the existing header. Excel adds a
Demo Notice sheet. PDF reports carry a notice on every page. Report filenames are
prefixed `synthetic-`, including canonical annual/historical and legacy exports.
Existing `sample=1` export restrictions remain in force. This formatting applies
only to the isolated demo, never operational exports.

## Verification

```powershell
npm.cmd run build
.\.venv\Scripts\python.exe -m pytest tests/test_report_year_demo.py tests/test_report_journeys.py -q -p no:cacheprovider --basetemp=.qa-report-demo-tests-temp
.\.venv\Scripts\python.exe scripts/qa_report_year_demo.py
```

Use normal Windows subprocess/temp permissions. **29 tests passed**: 24 demo cases
and 5 existing report-journey cases. Coverage includes target guards, dry-run manual
check, no implicit fixtures, repeatability, transaction rollback, all-month/campus
coverage, participant chronology, attendance integrity, annual deduplication, route
rendering, role isolation, private proposals, filters/periods, and labelled exports.
CSV attendee sums and Excel activity/trend/chart values match the report manifest;
PDF notices are verified on every page. Tested canonical activity/AOP, annual
indicator, historical CSV/Excel/PDF, and a legacy university CSV download.

**65 Chromium groups passed**, covering all three roles, 320/390/1440px layouts,
actual Plotly rendering and monthly values, landscape, 200% root text sizing,
reduced motion, overflow containment, visible keyboard focus/Enter navigation,
and visible print notice. No browser script
errors. Screenshots/results: `.qa-report-year-temp/screenshots/`.
Representative images: `director-summary-1440.png`, `director-annual-1440.png`,
`director-directory-320.png`, `coordinator-summary-390.png`, and
`volunteer-registrations-390.png`.

Tailwind build, 126-template parse, changed Python compilation, and Git whitespace
check passed. Existing Matplotlib/Pyparsing deprecation warnings remain; no test
failures. Original preview login on 5000 and demo directory on 5001 both returned 200.

Current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
reviewed: native navigation links, semantic headings/landmarks, readable sample
notice, visible focus, wrapping, print notice, role-limited destinations, escaped
template content, and retained export guards. No outstanding finding in the added UI.
Antislop gate: retain PSU tokens and hierarchy; use real report calculations, no
invented dashboard totals or decorative panels; contextual task groups and complete
mobile reflow. Skills: UI/UX Pro Max, Frontend Design, Ponytail full, antislop
core/UI/human/mobile during work, Webapp Testing, Web Design Guidelines.

Limitations: no full-suite/MySQL, physical-device, manual screen-reader, or actual
browser-toolbar zoom claim. Browser checks cover root text enlargement and print
visibility; automated export validation is not a page-by-page visual PDF audit.
Current-year calendars intentionally have no 2025 upcoming events.

## Stop, remove, or roll back

Stop the terminal running `scripts/report_demo.py --serve` with Ctrl+C. Identify
the exact demo process if the terminal wrapper leaves its Python child running;
do not stop other Python processes or the original preview.

To remove data, close the demo first, verify that the selected resolved paths are
inside `.qa-report-year-temp`, then remove only the chosen demo `.sqlite`, matching
`-private` directory, manifest, and credentials. Never delete `instance` or the
original `.qa-overhaul-temp` preview. No operational data rollback is required.

For source rollback, remove only this pass's demo modules/scripts/templates/tests,
conditional notice includes, demo-only factory guard and CSS rules; rebuild Tailwind.
Preserve all preceding overhaul work and unrelated files. Work remains local on
`codex/ui-workflow-overhaul`.
