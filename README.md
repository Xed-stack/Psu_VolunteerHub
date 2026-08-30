# PSU Volunteer Hub

Centralized volunteer management platform for Pangasinan State University. Built with Flask, SQLAlchemy, MySQL/SQLite, Jinja, and CSS.

## Quick Start (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=sqlite:///psu_local.db
python -m flask --app "app:create_app" run --host=0.0.0.0 --port=5000
```

Open **http://127.0.0.1:5000** in your browser. A fresh development database and demo data are created automatically on first run.

## Quick Start (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///psu_local.db"
python -m flask --app "app:create_app" run --host=0.0.0.0 --port=5000
```

Development defaults to `mysql+pymysql://root:@localhost/psu_volunteer_hub` when `DATABASE_URL` is not set. Use the SQLite value above for a self-contained local setup. Production requires `DATABASE_URL` and a non-default `SECRET_KEY`.

## Example Accounts

All accounts use password: **`password`**

| Role                      | Email                 | Can Do                                                                    |
| ------------------------- | --------------------- | ------------------------------------------------------------------------- |
| **Student Volunteer**     | `student@psu.edu`     | Browse events, register, view recommendations, track profile              |
| **Faculty Volunteer**     | `faculty@psu.edu`     | Same as student                                                           |
| **Staff Volunteer**       | `staff@psu.edu`       | Same as student                                                           |
| **Extension Coordinator** | `coordinator@psu.edu` | Manage events, attendance, external volunteers, milestones, and reports    |
| **Director**              | `director@psu.edu`    | View cross-campus analytics, compare participation, export campus reports |
| **Admin**                 | `admin@psu.edu`       | Manage users/campuses/settings, monitor health, and download backups      |

## Registration

New users can register at `/auth/register`. Public registration always creates a volunteer account and requires:

- A unique PSU ID and case-insensitive unique email
- Volunteer type: Student, Faculty, or Staff
- College affiliation and home campus
- A password meeting the Admin-configured minimum length

The onboarding wizard collects configured interests and their related skills together. The former separate `/auth/skills` step redirects to `/auth/interests`. Login accepts either email or the exact PSU ID.

External or outsider volunteers do not need platform accounts. They can join an individual opportunity through its public registration form, and coordinators can encode external participants from attendance management.

## Features

### Volunteer

- Browse opportunities with filter + pagination
- Receive personalized recommendations
- Register for events
- View participation history
- View earned certificates
- View event cover images on opportunity cards
- Receive and manage in-app registration notifications

### Coordinator

- Create and manage events
- Define required skills per event
- Upload or replace optional JPEG, PNG, or WebP event covers (maximum 5 MB)
- Prevent event capacity from being reduced below existing PSU and external registrations
- Track attendance and service hours for PSU and external volunteers
- Add external volunteers to campus activities
- Upload milestone documents
- Export event reports (CSV/PDF)
- Review interactive Plotly analytics for activity categories, volunteer types, and engagement trends

### Director

- Cross-campus analytics dashboard
- Compare campus participation
- Filter analytics by campus, date, category, and activity type
- Review interactive Plotly campus and engagement charts
- Compare PSU and outsider participation
- Export live and historical reports (CSV/PDF)

### Admin

- User management (add, edit, suspend, change role, reset password)
- Campus filter for user list
- Create campuses
- Download a credential-free ZIP backup containing table CSVs and a manifest
- System settings for event capacity and password-length limits
- Protect the final active Admin from deactivation or demotion
- Live database health check
- Review in-app system activity notifications
- Audit log

Unauthorized role access returns HTTP `403`. The volunteer global analytics page was removed; `/volunteer_analytics` redirects volunteers to their dashboard.

## Run Tests

```powershell
python -m pytest tests/ -v
```

## Historical Activity Import

The audited 2020–2025 institutional report is stored separately from live
events and attendance because it contains aggregate volunteer participations,
not individual registrations, exact dates, or service hours.

The reviewed seed file is `data/historical_activities_2020_2025.csv`. Import it
into the configured MySQL database with:

```powershell
python -m flask --app "app:create_app" import-historical-activities `
  data/historical_activities_2020_2025.csv
```

Validate without saving changes:

```powershell
python -m flask --app "app:create_app" import-historical-activities `
  data/historical_activities_2020_2025.csv --dry-run
```

The command is idempotent: rerunning it updates changed source rows and does
not create duplicates. The application factory creates the table automatically;
`migrations/20260828_add_historical_activities.sql` is provided for managed
MySQL deployments that apply schema changes explicitly.

## Profile And Event-Cover Migration

Existing MySQL 8.x or MariaDB 10.4+ deployments must apply
`migrations/20260830_profile_and_event_cover.sql` before deploying this version.
It:

- Converts blank PSU IDs to `NULL` and adds a unique PSU-ID index
- Adds volunteer type and college affiliation fields
- Adds event cover path and original-name fields

Uploaded event covers are stored under `static/uploads/events`. Production
deployments must provide writable, persistent storage for that directory.

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-Login, scikit-learn, pandas
- **Frontend:** CSS, Material Symbols, Jinja2, locally bundled Plotly
- **Database:** SQLite (dev) / MySQL (production)
- **Media:** Pillow image validation for event covers
- **Reports:** ReportLab PDF generation and CSV/ZIP exports
- **Auth:** Werkzeug password hashing, session-based
- **Testing:** pytest
