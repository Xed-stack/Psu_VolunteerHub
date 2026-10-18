# PSU Volunteer Hub — Continuation Handoff

## Start here in a new chat

The user can say: **Read HANDOFF.md and continue from the current local files.**

1. Read this file, `VOLUNTEER_HUB_ROADMAP.md`, `DASHBOARD_REDESIGN_QA.md`, and
   `PROFILE_REPAIR_QA.md`. Inspect `git status` and the actual local changes
   before editing; do not assume GitHub contains the latest iteration.
2. Preserve the dashboard redesign, first-use walkthroughs, volunteer profile
   repair, and any uncommitted changes. Do not discard or overwrite unrelated work.
3. Read the applicable installed skills completely before using them:
   - **`ponytail` (full):** use existing helpers, native controls, and the smallest
     safe, maintainable implementation. Do not sacrifice validation or accessibility.
   - **`antislop` + `antislop-ui`:** apply during implementation, not only after it.
     Retain purposeful PSU styling and complete the delivery gate.
   - **`frontend-design`:** use for interface changes to improve hierarchy,
     typography, spacing, composition, and clear primary actions.
   - **`antislop-human`:** verify contrast, semantic labels, keyboard operation,
     visible focus, and understandable empty/error/selected states.
   - **`antislop-layoutmobile`:** verify intentional mobile reflow, 44px targets,
     long-content wrapping, and contained table scrolling.
   - **`web-design-guidelines`:** review the completed UI against the skill's
     current guidelines, address in-scope findings, and report remaining limits.
   These are installed skill names; resolve their paths from the current session's
   skill catalog rather than assuming a location on another laptop. If unavailable,
   report that limitation; do not silently claim the skill was used or install one
   without authorization.
4. Reuse Bare CSS, the single `static/styles/base.css`, shared role shell/sidebar,
   role stylesheets, and local PSU assets. No Bootstrap/Tailwind migration,
   dependency, new foundation stylesheet, or unrelated redesign without approval.
   Keep the institutional direction: ENERGY 1 / RHYTHM 2 / MOTION 1.
5. Preserve Flask routes, CSRF, authorization, MySQL schema, and cosine
   recommendations unless the next request explicitly changes them. Verify real
   controls and desktop/mobile layouts; distinguish isolated test data from live data.
6. If the user supplied a next task, proceed with it. Otherwise briefly summarize
   the current status and ask which improvement to work on next. Do not commit,
   push, seed, or alter the live database just because this handoff was read.

## Repository and local run

- Repository: `https://github.com/Xed-stack/Psu_VolunteerHub`
- Branch: `main`
- Current local workspace: `C:\Users\arlro\Desktop\PSU VOLUNTEER\Psu_VolunteerHub`
- Start MySQL from XAMPP, then run the Flask application with:

  ```powershell
  .\.venv\Scripts\python.exe app.py
  ```

- The expected local URL is `http://127.0.0.1:5000`.

## Completed local work

### Volunteer profile repair (18 October 2026)

- `/profile` now uses the shared PSU header, bounded 96px photo, actual account
  details, separate interests/skills checkbox grids, accessible info tips,
  navigable recommendations, and five-row recent registration history.
- Name/email and other personal account details remain read-only. The unsupported
  `Verified volunteer` badge and duplicate read-only skills panel were removed.
- Registrations, verified present attendance, and completed participation are
  distinct counts. Completed participation requires completed registration status
  and present attendance, matching certificate eligibility. Count-based profile
  milestones use that count and are explicitly separate from Director recognition.
- Invalid submissions preserve submitted checkbox selections and show inline
  errors without changing stored preferences. Missing catalogs disable saving.
- JPEG/PNG/WebP uploads remain limited to 3 MB. A successful database commit
  precedes old-photo deletion; failed saves roll back and clean newly created
  files. Cleanup cannot remove shared assets or files outside the profile folder.
- Profile-specific CSS lives in `static/styles/volunteer.css`; no migration,
  dependency, framework, or profile JavaScript was added. Cosine matching remains.
- Latest verification: **19 focused profile tests passed**. Full suite:
  **227 passed, 1 known failure** in `TestAdminUserManagement.test_admin_reset_password`.
  That assertion expects a self-reset success message after redirects, but resetting
  the password invalidates the active session and reaches sign-in. It was not
  changed as part of the profile repair.
- Browser checks used isolated SQLite previews, not live MySQL. Desktop, tablet,
  390px mobile, keyboard controls, long names, and contained history scrolling
  were checked. Temporary preview servers were stopped afterward. See
  `PROFILE_REPAIR_QA.md` for evidence and explicit verification limitations.

### Director / Coordinator reporting redesign (18 October 2026)

- The two management dashboards and analytics screens share the PSU role shell, reusable heading/KPI/chart macros, and native information disclosures. Shared styles live in `static/styles/role-shell.css`; `base.css` remains the only global foundation.
- Live analytics has one filtered KPI strip. Campus/category comparisons, engagement trends, SDG mapping, composition, report pagination, and exports derive from the same `build_events_report` rows through `app/dashboard.py`. Historical aggregates retain a separate labelled source section and their own exports.
- Supplemental evidence states its scope: recognition is university-wide for the selected calendar year; profile demographics/affiliation and campus readiness/snapshot panels retain their independently labelled scopes.
- `/analytics` retains the ten-row live report and preserves every selected query parameter in pagination and CSV/PDF links. Coordinator reports remain restricted to the signed-in coordinator's campus.
- All four roles now use `static/scripts/first-use-tour.js`: native modal dialog, spotlight, keyboard controls, mobile coach sheet, and visible target selection. The former static Volunteer guide is removed. Help offers a plain `Show dashboard guide` replay link.
- `POST /guide/dismiss` is authenticated and CSRF protected and updates only `current_user.first_use_guide_dismissed_at`. The old volunteer dismissal URL remains compatible. Skip, Finish, and Escape share persistence; `?tour=1` replays without changing the stored timestamp.
- No new migration is required. Existing databases must already have `migrations/20260916_first_use_guide.sql` applied. This work adds no framework, runtime dependency, or database seed.
- Browser verification uses an isolated in-memory SQLite preview on port 5055, with CSRF enabled. This preview does not modify the deployment's MySQL data.
- Verification: 212 tests passed with the existing Admin self-password-reset message assertion still failing; final focused report/workspace/UI checks passed (10 tests). See `DASHBOARD_REDESIGN_QA.md` for browser evidence, the design gate, and native zoom/reduced-motion verification limits.

- Volunteer dashboard lists personal registrations, lets volunteers cancel eligible future registrations, and supports re-registration after a cancellation when capacity remains.
- Coordinators can permanently remove activities in their campus. PSU volunteers with registrations receive in-app cancellation notifications.
- Responsive sidebar behavior is mobile-only at 767px and below; mobile logout is a visible red outlined action.
- Historical participation remains visible in explicitly labelled source panels. The Director home campus comparison uses historical aggregates when live registrations are absent; filtered analytics comparisons use live report rows and do not silently substitute a different scope.
- Admin category management supports create/delete; deleted categories move affected events to `General` and notify the event creator or campus coordinators.
- Admin analytics is hidden from the admin interface while the route/template implementation remains available.
- The public `/opportunities` page now uses shared shell styling, responsive opportunity cards, CSRF-protected registration forms, and a clear `Registered` state for existing volunteer sign-ups.
- Analytics no longer displays or exports service-hour values; registration and attendance counts are the participation measures used throughout the UI and reports.
- The `seed-demo-analytics` Flask command creates idempotent presentation data across campuses, categories, registrations, and attendance without overwriting existing records.
- Phase 4 now includes an append-only Admin Activity Log, validated CSV user import/export (without password hashes), and versioned Terms of Use. An admin publishes the active terms revision; new registrations accept it during sign-up, while existing users are redirected to accept it before continuing.
- Accounts can be deactivated, request reactivation through the login flow, be reviewed in a Deactivated Users tab, and be permanently deleted manually after 30 days. Safeguards protect the last active admin and the current admin account.
- The roadmap in `VOLUNTEER_HUB_ROADMAP.md` records proposed future work. It is not implemented.
- Director demographics, SDG, and recognition are now implemented locally: volunteer sex is required at registration (existing volunteers complete it once after sign-in), coordinators tag activities with the official 17 SDGs, and Director Analytics shows sex-disaggregated verified participation plus calendar-year Top 5 recognition.
- Recognition is informational only: volunteers rank by verified present attendance then completed activities; campuses rank by verified attendance rate then verified present attendance. External, cancelled, absent, unverified, and historical aggregate records are excluded.

## Database requirement

Apply `migrations/20260903_admin_categories_and_deactivation.sql` to the configured MySQL database before testing the administration features on a fresh database. It adds activity categories, event creator ownership, and deactivation/reactivation fields.

Also apply `migrations/20260912_add_audit_logs.sql` and `migrations/20260912_add_terms_revisions.sql` for the Phase 4 audit and policy features on an existing database.

Apply `migrations/20261016_director_demographics_sdgs.sql` before using the Director demographics and SDG features against an existing MySQL database. Then restart Flask so the built-in SDG catalogue seed can verify the 17 official goals.

Apply `migrations/20261016_security_hardening.sql` before deploying the security update to an existing MySQL database. It adds session-version invalidation, database-backed authentication throttling, and password-reset tokens. Production also requires `SECRET_KEY`, `DATABASE_URL`, HTTPS behind a trusted proxy, a writable `PRIVATE_UPLOAD_FOLDER` outside the web root, and SMTP configuration for reset emails.

Historical CSV data can be imported with:

```powershell
flask import-historical-activities data/historical_activities_2020_2025.csv
```

For a local panel/demo dashboard with live registration and attendance charts:

```powershell
.\.venv\Scripts\flask.exe seed-demo-analytics
```

The command is safe to rerun. It creates records titled `[Demo Analytics] ...` only when they do not already exist. To move the exact current local database to another laptop, import `database/psu_volunteer_hub_latest.sql` into the configured `psu_volunteer_hub` MySQL/MariaDB database; Git transfers the seed command and SQL file, not a running database server.

## Recommended first checks

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
git status -sb
```

Then manually check:

1. A volunteer can register, cancel before the event start, and see the registration history.
2. A campus coordinator can only delete activities from their own campus.
3. A deactivated user sees the reactivation-request modal after valid credentials.
4. An admin can review Deactivated Users and categories without an Analytics navigation item.
5. The sidebar hamburger and red logout action render correctly at a mobile width and remain hidden/compact on desktop.

## Next recommended work

### Director demographics, SDG, and recognition phase

Implemented locally; apply the migration noted above before using it with an existing MySQL database. The policy lifecycle, cancellation review, Coordinator/Director calendars, accomplishment reporting, and first-use guide are already implemented. Apply `migrations/20260912_policy_lifecycle.sql` and `migrations/20260916_first_use_guide.sql` to an existing MySQL database before using those features there.

1. **Sex-disaggregated data**
   - Registration supports `Male`, `Female`, and `Prefer Not to Say`; legacy missing values remain `Not recorded`.
   - Redirect existing volunteers with no recorded value to complete it before accessing their dashboard.
   - Add a Director-only sex filter plus clearly labeled sex-disaggregated participation chart/table. Legacy records remain `Not recorded` until completed.

2. **Sustainable Development Goals (SDGs)**
   - [x] Seed the official 17 UN SDGs as a catalog.
   - [x] Let coordinators assign all applicable SDGs to an activity through a many-to-many relationship.
   - [x] Show assigned SDGs in the live report and PDF/CSV exports, with a Director SDG filter.
   - [ ] Show assigned SDGs in activity details/calendars and add a dedicated participation-by-SDG comparison when that reporting view is needed.
   - Keep historical aggregate records separate; never infer SDGs for them.

3. **Automatic annual recognition**
   - Add a Director-only calendar-year selector and Top 5 recognition lists.
   - Rank Outstanding Volunteers by verified present attendance, then completed activities; equal values share a rank.
   - Rank Outstanding Campuses by verified attendance rate, then total verified present attendance.
   - Exclude registrations without verified attendance, absences, cancellations, external participants, and historical aggregate data. The labels are informational; PSU retains final award approval.

4. **Verification**
   - Add a versioned MySQL migration for sex, SDG catalog, and the event–SDG relationship.
   - Test registration/profile completion, Director-only authorization, multi-SDG event editing/filtering, reporting, ranking order/ties/year scope, and zero-data states.
   - Run the full pytest suite and check Director analytics at desktop and mobile widths.

QR attendance, SMS/email, SIS integration, financial features, and automatic account purging remain out of scope.

## Working-tree note

This repository has accumulated related user-requested changes in one working tree. Preserve existing modifications and avoid reset/checkout commands that discard changes. Use migrations for schema changes and add regression tests with each feature.
