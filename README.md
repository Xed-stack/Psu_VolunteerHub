# PSU Volunteer Hub

PSU Volunteer Hub is a centralized volunteer-management platform for Pangasinan State University. It supports public opportunity discovery, volunteer registration, campus-scoped coordination, attendance, descriptive analytics, reports, policy acknowledgements, and administrative governance.

## What it does

- Public landing page, featured activities, opportunity search/filtering, event details, external-volunteer joining, help guide, and 2020–2025 historical activity directory.
- Volunteer profiles with controlled interests and skills, cosine-similarity recommendations, image upload, a first-use guide, registration calendar, filtered history, and cancellation requests.
- Coordinator event creation and editing, agreements and optional NDAs, cancellation deadlines, announcements, attendance, external participants, milestones, reports, campus analytics, cancellation review, and campus calendar.
- Director cross-campus dashboard, activity accomplishments, target-versus-verified attendance, monthly calendars, descriptive analytics, ten-row paginated Live Activity Reports, and CSV/PDF exports.
- Admin user/campus/category management, deactivation/reactivation safeguards, validated CSV import/export, audit log, backups, Terms of Use, Privacy Notice, and default participation-agreement publishing.

Historical records are aggregate institutional reporting units. They are never represented as individual user accounts, registrations, attendance records, or verified hours.

## Requirements

- Python 3.10+
- MySQL 8.x or MariaDB 10.4+ for the shared database
- XAMPP MySQL is supported for local Windows development

SQLite can be used only for a self-contained local development database.

## Run locally

### PowerShell with MySQL

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="mysql+pymysql://root:@localhost/psu_volunteer_hub"
$env:FLASK_APP="app:create_app"
flask run --port 5000
```

Open `http://127.0.0.1:5000`.

### Self-contained SQLite development setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///psu_local.db"
$env:FLASK_APP="app:create_app"
flask run --port 5000
```

For production, set a non-default `SECRET_KEY` and a MySQL `DATABASE_URL`. Do not commit either value.

## Demo accounts

Fresh demo databases create these accounts with password `password`.

| Role | Email | Main capabilities |
| --- | --- | --- |
| Student Volunteer | `student@psu.edu` | Profile, recommendations, opportunities, registrations |
| Faculty Volunteer | `faculty@psu.edu` | Same volunteer capabilities |
| Staff Volunteer | `staff@psu.edu` | Same volunteer capabilities |
| Extension Coordinator | `coordinator@psu.edu` | Campus activities, attendance, participants, reports |
| Director | `director@psu.edu` | Cross-campus analytics, calendars, reports |
| Admin | `admin@psu.edu` | User, campus, category, policy, and audit governance |

## MySQL migrations

For an existing MySQL database, apply each migration that has not already been applied, in date order. In PowerShell:

```powershell
Get-Content -Raw ".\migrations\20260912_policy_lifecycle.sql" |
  & "C:\xampp\mysql\bin\mysql.exe" -u root psu_volunteer_hub

Get-Content -Raw ".\migrations\20260916_first_use_guide.sql" |
  & "C:\xampp\mysql\bin\mysql.exe" -u root psu_volunteer_hub
```

The earlier migrations in `migrations/` are also required for a database created before their feature sets. Do not rerun a migration containing non-idempotent `ALTER TABLE ... ADD COLUMN` statements.

Verify the latest onboarding migration:

```powershell
& "C:\xampp\mysql\bin\mysql.exe" -u root -e "USE psu_volunteer_hub; SHOW COLUMNS FROM users LIKE 'first_use_guide_dismissed_at';"
```

## Historical and panel-demo data

Import audited 2020–2025 aggregate activity data:

```powershell
flask import-historical-activities data/historical_activities_2020_2025.csv
```

Validate the source without modifying the database:

```powershell
flask import-historical-activities data/historical_activities_2020_2025.csv --dry-run
```

Seed representative live events, registrations, and attendance for a local panel demonstration:

```powershell
flask seed-demo-analytics
```

The historical import and demo seed are idempotent. Historical imports remain separate from live activity data.

## Policies and cancellations

- Admins publish versioned Terms of Use, Privacy Notice, and default Participation Agreement revisions.
- New users acknowledge active Terms and Privacy revisions. Existing users are prompted after a newly published revision.
- Every event registration stores the accepted participation-agreement version; events may have their own agreement and optional NDA.
- Volunteers request cancellation before the event deadline. A campus coordinator approves or rejects the request; approval changes the registration to cancelled.

## Reports and analytics

- Participation is measured through registrations and verified present attendance. Service-hour values are not used in current analytics or exports.
- Director Live Activity Reports display ten rows per page while CSV/PDF exports include every activity matching the active filters.
- Filters and campus boundaries apply to reports. Coordinators are restricted to their campus; Directors are read-only across campuses.

## Tests

```powershell
python -m pytest -q tests\test_app.py
```

The latest full local verification completed with `170 passed` before the final documentation update.

## Technology

- **Backend:** Flask, SQLAlchemy, Flask-Login, Werkzeug
- **Database:** MySQL/MariaDB; SQLite for isolated development
- **Recommendations:** content-based cosine similarity using scikit-learn
- **Frontend:** Jinja templates, Bare CSS, Material Symbols, locally bundled Plotly
- **Media:** Pillow validation for uploads
- **Reports:** ReportLab PDF and CSV exports
- **Testing:** pytest

## Repository hygiene

Do not commit database exports, `.env` files, virtual environments, or uploaded user files. In particular, keep `Database/psu_volunteer_hub_after_policy_lifecycle.sql` local because it can contain real account data.
