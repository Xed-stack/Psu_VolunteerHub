# PSU Volunteer Hub

Centralized volunteer management platform for Pangasinan State University. Built with Flask + SQLAlchemy + Tailwind CSS.

## Quick Start (Command Prompt)

```cmd
python -m venv venv
venv\Scripts\activate
pip install flask flask-sqlalchemy flask-login werkzeug
set FLASK_APP=app
python -m flask run --host=0.0.0.0 --port=5000
```

Open **http://127.0.0.1:5000** in your browser. The database and seed data are created automatically on first run.

## Quick Start (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install flask flask-sqlalchemy flask-login werkzeug
$env:FLASK_APP="app"
python -m flask run --host=0.0.0.0 --port=5000
```

## Example Accounts

All accounts use password: **`password`**

| Role | Email | Can Do |
|------|-------|--------|
| **Student Volunteer** | `student@psu.edu` | Browse events, register, view recommendations, track profile |
| **Faculty Volunteer** | `faculty@psu.edu` | Same as student |
| **Staff Volunteer** | `staff@psu.edu` | Same as student |
| **Extension Coordinator** | `coordinator@psu.edu` | Create/manage events, track attendance, upload milestones, export reports |
| **Director** | `director@psu.edu` | View cross-campus analytics, compare participation, export campus reports |
| **Admin** | `admin@psu.edu` | Manage all users, system settings, campus filter |

## Registration

New users can register at `/auth/register`. The form asks:

- **PSU Student/Faculty/Staff** — requires ID number + home campus
- **External Volunteer** — requires preferred campus + email

## Features

### Volunteer
- Browse opportunities with filter + pagination
- Receive personalized recommendations
- Register for events
- View participation history
- View earned certificates

### Coordinator
- Create and manage events
- Define required skills per event
- Track attendance
- Upload milestone documents
- Export event reports (CSV)

### Director
- Cross-campus analytics dashboard
- Compare campus participation
- Export campus reports (CSV)

### Admin
- User management (add, edit, suspend, change role, reset password)
- Campus filter for user list
- System settings (community value rate, max slots, etc.)
- Audit log

## Run Tests

```powershell
python -m pytest tests/ -v
```

## Tech Stack

- **Backend:** Flask, SQLAlchemy, Flask-Login
- **Frontend:** Tailwind CSS (CDN), Material Symbols, Jinja2
- **Database:** SQLite (dev) / MySQL (production)
- **Auth:** Werkzeug password hashing, session-based
- **Testing:** pytest
