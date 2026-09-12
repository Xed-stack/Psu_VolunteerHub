# PSU Volunteer Hub — Continuation Handoff

## Repository and local run

- Repository: `https://github.com/Xed-stack/Psu_VolunteerHub`
- Branch: `main`
- Local workspace: `C:\Users\Jeuryn\Documents\Codex\2026-09-03\pu\Psu_VolunteerHub`
- Start MySQL from XAMPP, then run the Flask application with:

  ```powershell
  .\.venv\Scripts\python.exe app.py
  ```

- The expected local URL is `http://127.0.0.1:5000`.

## Completed work in this commit

- Volunteer dashboard lists personal registrations, lets volunteers cancel eligible future registrations, and supports re-registration after a cancellation when capacity remains.
- Coordinators can permanently remove activities in their campus. PSU volunteers with registrations receive in-app cancellation notifications.
- Responsive sidebar behavior is mobile-only at 767px and below; mobile logout is a visible red outlined action.
- Historical activity data now provides fallbacks for participation-by-category and cross-campus analytics when live activity data is absent.
- Admin category management supports create/delete; deleted categories move affected events to `General` and notify the event creator or campus coordinators.
- Admin analytics is hidden from the admin interface while the route/template implementation remains available.
- The public `/opportunities` page now uses shared shell styling, responsive opportunity cards, CSRF-protected registration forms, and a clear `Registered` state for existing volunteer sign-ups.
- Analytics no longer displays or exports service-hour values; registration and attendance counts are the participation measures used throughout the UI and reports.
- The `seed-demo-analytics` Flask command creates idempotent presentation data across campuses, categories, registrations, and attendance without overwriting existing records.
- Phase 4 now includes an append-only Admin Activity Log, validated CSV user import/export (without password hashes), and versioned Terms of Use. An admin publishes the active terms revision; new registrations accept it during sign-up, while existing users are redirected to accept it before continuing.
- Accounts can be deactivated, request reactivation through the login flow, be reviewed in a Deactivated Users tab, and be permanently deleted manually after 30 days. Safeguards protect the last active admin and the current admin account.
- The roadmap in `VOLUNTEER_HUB_ROADMAP.md` records proposed future work. It is not implemented.

## Database requirement

Apply `migrations/20260903_admin_categories_and_deactivation.sql` to the configured MySQL database before testing the administration features on a fresh database. It adds activity categories, event creator ownership, and deactivation/reactivation fields.

Also apply `migrations/20260912_add_audit_logs.sql` and `migrations/20260912_add_terms_revisions.sql` for the Phase 4 audit and policy features on an existing database.

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

Use `VOLUNTEER_HUB_ROADMAP.md` as the source of truth. Verify the current landing page, opportunities view, analytics seed data, and MySQL import before starting remaining roadmap items. The next planned feature set is policy and agreement management: separate Terms of Use and Privacy Notice acknowledgements at account registration, per-event Participation Agreements, optional event NDAs, and reasoned cancellation requests reviewed by a campus-scoped coordinator. These are not implemented yet; the current direct cancellation workflow remains in place until its request-and-review replacement is delivered. Reuse approved PSU photos or coordinator-uploaded event/milestone imagery; do not add unlicensed stock photos. The requested QR attendance, SMS/email, SIS integration, and automatic purging are explicitly out of scope.

## Working-tree note

This repository has accumulated related user-requested changes in one working tree. Preserve existing modifications and avoid reset/checkout commands that discard changes. Use migrations for schema changes and add regression tests with each feature.
