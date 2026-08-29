# PSU Volunteer Hub — Completed Work Summary

> Generated from the opencode session. Covers all implementation work performed
> against `PSU Volunteer Hub — Next Development Plan.md` up to and including the
> Final Live Acceptance Test (Phase 23).
>
> **Git state:** all changes are **uncommitted** and **not pushed** (branch `main`,
> up to date with `origin/main`). `git diff --check` is clean.

---

## Test baseline

| Milestone | Tests passing |
|-----------|---------------|
| Inherited baseline (before work) | 72 passed, 1 xfailed |
| After Phases 0–11 (Reporting) | 95 passed, 0 failed |
| After Phase 12 (Outsider workflow) | 112 passed, 0 failed |
| After Phase 13 (Recommendation engine) | 116 passed, 0 failed |
| After Phase 16 (Coordinator event editing) | 131 passed, 0 failed |
| After Phase 18 (Analytics & chart improvements) | **149 passed, 0 failed** |

Test command:
```powershell
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pytest tests/test_app.py -q -p no:cacheprovider
```
(Full suite ~5 min; the venv was rebuilt with `uv venv --python 3.11 .venv`
because the hermes-agent venv was broken; `reportlab==4.2.2` is in
`requirements.txt`.)

---

## Phases 0–11 — Reporting System (complete)

**Goal:** finish the reporting subsystem with CSV/PDF export, date / campus /
category filters, and role-correct (server-side) authorization.

### Implementation
- **New shared service `app/reports.py`**
  - `parse_date_range`, `resolve_campus`, `build_events_report`
  - `render_csv`, `render_pdf`, `_build_meta`, `ReportError`
  - Returns PSU vs External attendance breakdown (later extended in Phase 12).
- **Coordinator (`app/routes/coordinator.py`)**
  - Refactored to call the shared module.
  - Campus is **forced server-side** via `_coordinator_campus_id`; any
    `?campus_id=` query param is ignored so a coordinator can never scope to
    another campus.
- **Director / Admin (`app/routes/director.py`)**
  - Added `/reports/university.csv` and `/reports/university.pdf`, both guarded
    by `roles_required('director','admin')` with role-aware branding.
  - Live report table injected into the analytics dashboard.
- **Templates:** reporting matrix all PASS (date / campus / category filters,
  CSV, PDF, role separation).

### Tests
- Added `TestReportingSystem` class.
- Promoted `test_filter_by_category` from `xfail` to a real passing test.

---

## Phase 12 — Outsider / External Volunteer Workflow (complete)

**Goal:** let non-PSU ("outsider") individuals volunteer without creating a
`User` account, while preserving authorization boundaries.

### Requirements source
`Phase 12 — Outsider - External Volunteer Requirements.md` (manuscript-derived).
Key rules:
- Outsider = non-PSU individual; `role` stays `Volunteer`; affiliation is separate.
- Use a separate `ExternalParticipant` model (Option B), **not** a `User` extension.
- **ID Number required**; Name / Contact / Address / Email optional; no org, no
  campus required.
- Two onboarding paths: (A) public Join ("Are you currently from PSU?" → No →
  form), (B) Coordinator manual encoding (campus-scoped).
- Reuse `Registration → Attendance`; no separate attendance/hours system.
- No `Outsider` auth role; no privilege escalation; outsiders excluded from the
  recommendation engine; PSU-vs-External dashboard not mandated but Volunteer
  Type added to CSV/PDF.

### Implementation
- **`app/models/event.py`**
  - New `ExternalParticipant` model.
  - `Registration.user_id` made nullable + `external_participant_id` FK +
    `uk_external_event` + `ck_registration_participant` + `participant` /
    `is_external` helpers.
  - `Attendance.user_id` made nullable.
- **`app/__init__.py`** — registers `ExternalParticipant`.
- **`app/routes/events.py`** — `event_join` (GET/POST public join, PSU question,
  outsider creates `ExternalParticipant` + `Registration`); `_upsert_external_participant`.
- **`app/routes/coordinator.py`** — `add_external_participant`
  (campus-verified; `abort(403)` on cross-campus).
- **`app/reports.py`** — `build_events_report` now returns PSU vs External
  counts; CSV/PDF include `PSU` / `External` columns.
- **Templates**
  - New: `templates/events/event_join.html`, `templates/coordinator/add_external.html`
  - Modified: `attendance_MnGmt.html` (outsider-safe cells + add-external link),
    `coordinator_analytics.html`, `Director_impact_anlaytics_dash.html`
    (PSU/External columns), `Volunteer_opportunities.html` ("Join as external
    volunteer" link).
- **`migrations/20260829_outsider_volunteers.sql`** — schema migration.

### Tests
- Added `TestOutsiderVolunteers` (17 tests). Full suite 112 passed.

---

## Phase 13 — Recommendation Engine Improvements (complete)

**Goal:** improve the cosine-similarity engine and resolve the manuscript's
TF-IDF / scikit-learn inconsistency.

### Decision on the manuscript inconsistency
**Option B** — kept the existing **binary** term-vector cosine similarity
(already locked by tests) and updated the module docstring to state explicitly
that it is *not* TF-IDF and does *not* import scikit-learn. No false TF-IDF claim
remains.

### Implementation (`app/recommendation/engine.py`)
- **Taxonomy normalization** (`normalize_terms` / `_normalize_token`): lowercases,
  trims, strips trailing punctuation, collapses whitespace. Applied identically
  to user and event terms.
- **Duplicate / synonym handling** (`SYNONYM_MAP`): curated variant→canonical map
  (e.g. `IT`→`IT/Computer Skills`, `Env`→`Environmental Conservation`,
  `Teach`→`Teaching`) so variant spellings match instead of diverging.
- **Participation-history weighting:** events whose category matches a category
  the volunteer previously joined get a small, capped boost (`+0.15`, max `1.0`).
  Cold-start-safe (empty history → no boost).
- Cold-start popularity / campus / soonest-date fallback left intact.

### Tests
- Added 4 deterministic tests: `test_normalize_terms_collapses_variants`,
  `test_synonym_matches_variant_skill`, `test_participation_history_weights_category`,
  `test_recommendations_deterministic`.
- Full suite **116 passed, 0 failed**; `git diff --check` clean.

---

## Remaining backlog (not started)

Per the plan, the next section is the **Remaining Backlog**. None of these have
been implemented; most feature items require manuscript-derived requirements
(like Phase 12) before coding:

1. In-app notifications
2. Coordinator event editing
3. Campus organization support
4. Analytics / chart improvements
5. Social sharing (if required)
6. Remaining UI placeholders
7. Accessibility / usability cleanup
8. Deprecated code cleanup
9. Test warning cleanup
10. Final manuscript-to-software compliance audit

> Status as of this report (pre-Phase-14): Phase 13 done; backlog pending user
> selection + (where applicable) manuscript spec. No live/manual verification was
> run (no running MySQL/DB in this environment); coverage via automated suite.

---

## Phase 14 — Live Verification & MySQL Migration (complete)

**Environment:** Live database is **MariaDB 10.4.32** (not MySQL). Flask dev
server run via `python app.py` (DevelopmentConfig → MariaDB). Browser testing
added via Playwright + headless Chromium.

### Migration verification
- `enforce_attendance_uniqueness.sql` was **already applied** to the DB
  (`uq_attendance_registration`, `fk_attendance_registration` present).
- Applied `20260829_outsider_volunteers.sql`:
  - `external_participants` table created.
  - `registrations.user_id` and `attendance.user_id` made **nullable**.
  - `external_participant_id` column + `fk_registration_external` +
    `uk_external_event` (unique) + `ck_registration_participant` (check) added.
- **No data loss:** `registrations`/`attendance` were empty; 9 events and 6
  seeded users preserved.

### Browser (Playwright) end-to-end checks — 24 passed, 0 failed
| Area | Result |
|------|--------|
| Volunteer login / dashboard / recommendations / register / profile / logout | PASS |
| External join (anonymous) → `ExternalParticipant` + `Registration` created | PASS |
| Coordinator login / attendance / add-external / CSV / PDF export | PASS |
| Coordinator blocked from Director (redirect to own dashboard) | PASS |
| Director login / analytics / university + campus CSV + PDF | PASS |
| Admin login / user-create / settings | PASS |
| Volunteer blocked from Coordinator & Admin (redirect) | PASS |

Role authorization is enforced via **redirect to the user's own dashboard**
(not 403) — verified, not a vulnerability. CSRF protection works (forms get a
token via `partials/csrf_forms_script.html` auto-injection).

### Caveats
- Seeded user passwords were set to `Test@1234` in the live DB to enable login
  testing; they can be reset.
- Flask dev server is left running (PID 8172) for subsequent phases.
- Full automated suite remains **116 passed, 0 failed**; `git diff --check` clean.

---

## Phase 15 — In-App Notifications (complete)

**Scope (from plan):** basic in-app notifications only — no SMS/email/push/social.
Notifications belong to authenticated PSU users; `ExternalParticipant` is never
given an authenticated notification account.

### Implementation
- **`app/models/notification.py`** — `Notification` model (`user_id`, `title`,
  `message`, `notification_type`, `related_event_id`, `is_read`, `created_at`)
  + `notify()` / `notify_campus_coordinators()` helpers.
- **`app/__init__.py`** — registers `notifications_bp`; context processor exposes
  `unread_notifications` to templates (badge count).
- **`app/routes/notifications.py`** — `GET /notifications` (list),
  `POST /notifications/<id>/read` (owner-only), `POST /notifications/read-all`.
  Cross-user access denied (flash + redirect; no status change).
- **`templates/notifications/list.html`** (new) + notification **bell/badge** in
  `layouts/role_base.html`.
- **`migrations/20260829_notifications.sql`** — `notifications` table (applied to
  live MariaDB).
- **Conservative triggers** (manuscript undefined → tied to existing actions):
  - PSU volunteer registers for an event → notifies that event's campus
    coordinators.
  - External volunteer joins / is manually added → notifies that event's campus
    coordinators.

### Tests
- Added `TestNotifications` (7 tests): list requires login, owner visibility,
  hidden from other user, mark-as-read, mark-all-read, cross-user mark-read
  denied, registration notifies coordinator.
- Full suite **123 passed, 0 failed**; `git diff --check` clean.

### Browser (Playwright) verification — 5 passed, 0 failed
| Area | Result |
|------|--------|
| Volunteer registration triggers coordinator notification | PASS |
| Coordinator unread badge shows count | PASS |
| Coordinator sees "New registration" notification | PASS |
| Mark-as-read clears the badge | PASS |
| Read notification remains listed | PASS |

---

## Phase 16 — Coordinator Event Editing (complete)

**Scope (from plan):** authorized coordinators edit activities in their assigned
campus. No destructive event deletion added. Campus ownership enforced
server-side; capacity cannot drop below existing registrations.

### Implementation
- **`app/routes/coordinator.py`** — `GET/POST /coordinator/events/<id>/edit`:
  - `abort(403)` if `event.campus_id != current_user.campus_id`.
  - Editable fields mirror creation: title, description, date, location,
    category, required skills, slots. `campus_id` is **never** changed by the
    edit (submitted value ignored) — a coordinator cannot move an event to
    another campus.
  - Validation: title/description/date required; valid date; slots ≥ 1;
    slots cannot be reduced below existing registrations (PSU + external).
- **`templates/coordinator/edit_activity.html`** (new) — pre-filled form.
- **`Coordinator_dash.html`** — added an "Edit" link per campus activity.

### Tests
- Added `TestCoordinatorEventEditing` (8 tests): own-campus edit succeeds,
  cross-campus edit denied (403), volunteer cannot edit, director cannot edit,
  invalid values rejected, slots-below-registrations rejected, registrations
  survive edit, CSRF blocks edit without token.
- Full suite **131 passed, 0 failed**; `git diff --check` clean.

### Browser (Playwright) verification — 3 passed, 0 failed
| Area | Result |
|------|--------|
| Own-campus edit page loads (prefilled) | PASS |
| Own-campus edit persists to DB | PASS |
| Cross-campus edit denied (403) | PASS |

---

## Phase 18 — Analytics & Chart Improvements (DONE)

**Approach:** Descriptive-analytics improvement only (no predictive ML added).
Audited existing `app/recommendation/analytics.py`, centralized metric
definitions, and aligned the reporting system so dashboard/CSV/PDF agree.

**Changes made**
- `app/reports.py` — `build_events_report` now counts **valid registrations**
  (status != `cancelled`) for `Registrations`, `PSU`, and `External`. Aligns
  with the coordinator attendance view and the Phase 18 "exclude cancelled" rule,
  and keeps analytics == report == PDF for the same scope/filters.
- `app/recommendation/analytics.py` — added centralized descriptive methods:
  `participation_summary`, `campus_comparison`, `activity_performance`,
  `category_distribution`, `monthly_engagement`, `weekly_engagement`,
  `psu_vs_outsider`, `skill_distribution`, `interest_distribution`, plus a
  private `_scoped_event_query` helper. All campus/date/category scoping is
  server-side; the module never reads a client `campus_id`.
- `app/routes/coordinator.py` — `coordinator_dash` now uses
  `participation_summary` (removed duplicated inline calc); `coordinator_analytics`
  passes the new campus-scoped metrics.
- `app/routes/director.py` — `analytics` passes university-wide participation,
  campus comparison, category, activity performance, monthly/weekly engagement,
  PSU-vs-outsider, and top skills/interests.
- Templates — `coordinator/coordinator_analytics.html` and
  `director/Director_impact_anlaytics_dash.html` gained Participation Summary,
  Cross-Campus Comparison, Category, Activity Performance, Monthly/Weekly
  Engagement, PSU-vs-Outsider, and Top Skills/Interests panels (responsive CSS
  bars/tables; server-rendered, no external chart lib).
- `tests/test_app.py` — new `TestAnalytics` (18 deterministic tests).

**Calculation definitions (explicit)**
- Registrations = COUNT(valid registrations) where status != `cancelled`.
- PSU Registrations = registrations linked to a `User`; External = linked to an
  `ExternalParticipant`.
- Unique Volunteers = COUNT(DISTINCT `Registration.user_id`).
- Attended = COUNT(`Attendance.status == 'present'`).
- Attendance Rate = Attended / Registrations × 100 (0 if no registrations).
- Conversion Rate (sign-up → attendance) = Attended / Registrations × 100.
- Service Hours = SUM(`Attendance.hours_completed`).

**Role scope**
- Coordinator → own campus only (server-enforced; no cross-campus leak).
- Director → university-wide, view-only.
- Admin → university-wide, separate branding (not "Director Console").
- Volunteer → no privileged analytics (redirect).

**Tests:** `tests/test_app.py::TestAnalytics` — 18 passed. Full suite
**149 passed, 0 failed**. `git diff --check` clean (only pre-existing CRLF
warnings).

**Live verification (Playwright, in-process server, real MariaDB):** director
`/analytics` 200 with new panels; admin branding correct; coordinator analytics
campus-scoped (campus-2 event absent); volunteer denied `/analytics`. 4/4 PASS.

**Remaining gaps (manuscript requirements not implementable with current data)**
- Student/Faculty/Staff classification and College affiliation: **not collected**
  in the schema → cannot be produced without a new data-collection subsystem
  (out of scope per 18.21/18.37). Provided PSU-vs-Outsider instead.
- Trend charts are rendered as responsive CSS bars (no Chart.js/Plotly wired);
  all required metrics, labels, units, and chronological ordering are present.

---

## Phase 19 — UI Placeholder / Dead-Control Cleanup (DONE)

**Audit result:** The UI was already largely clean. A full-template sweep for
`TODO`/`TBD`/`FIXME`/`coming soon`/`Under Construction`/`Lorem`/`placeholder`
(stub) text, dead `href="#"` anchors, empty `action=""` forms, `disabled`
controls, and `onclick=` stubs found **no dead controls and no placeholder
stubs**. All sidebar/role-nav links resolve to real, tested endpoints
(`events.volunteer_dash`, `events.opportunities`, `volunteer.analytics`,
`volunteer.profile_page`, `coordinator.*`, `director.analytics`,
`admin.admin_dash`, `admin.settings`, `admin.create_user`, `admin.edit_user`,
`admin.change_role`, `notifications.list_notifications`). The volunteer
"Edit matching profile" form is wired (POST handler saves skills/interests).

**Change made**
- `templates/login.html` — removed the "Password recovery is not yet available."
  note. It advertised an unimplemented feature, which Phase 19 calls out as a
  placeholder to remove (the login form, "Create an account", and logout remain
  fully functional). Input `placeholder=` hints (e.g. `name@psu.edu.ph`) were
  kept because they are legitimate field guidance, not missing-feature stubs.

**Verification:** `git diff --check` clean (only pre-existing CRLF warnings).
Live smoke (Playwright + real MariaDB): login page renders without the removed
note; volunteer/coordinator/director/admin dashboards all return 200. 5/5 PASS.
No automated test asserts the removed string, so the 149-test suite remains
green.

---

## Phase 20 — Accessibility / Usability Cleanup (DONE)

**Audit:** Recursively scanned every template for accessibility gaps. No
`<img>` missing `alt`, no dead controls, and all form fields use either
wrapping `<label>` or explicit `for=`/`id` association (login, volunteer
profile, attendance event filter, report filters). The real gaps were
unlabeled table headers and two unlabeled inline `<select>`s.

**Changes made (all template-only, safe attribute additions)**
- Added `scope="col"` to every `<th>` in data tables across:
  `volunteer/Volunteer_Profile.html`, `volunteer/Volunteer_analytics.html`,
  `director/Director_impact_anlaytics_dash.html`,
  `coordinator/coordinator_analytics.html`,
  `coordinator/attendance_MnGmt.html`, `admin/Admin_mngmt_dash.html`,
  `coordinator/Coordinator_dash.html`. Improves screen-reader table navigation.
- `admin/Admin_mngmt_dash.html` — added `aria-label="Filter by campus"` to the
  campus filter `<select>` and `aria-label="Change role for {{ user.name }}"`
  to each row's change-role `<select>` (both previously unlabeled).
- `coordinator/Coordinator_dash.html` — added `aria-label="Milestone file"` to
  the unlabeled milestone `<input type="file">`.

**Verification:** `git diff --check` clean (only pre-existing CRLF warnings).
Live smoke (Playwright + real MariaDB): all four role dashboards return 200;
director tables contain `scope="col"`; admin campus filter carries its
`aria-label`. 6/6 PASS. Template-only changes cannot affect the 149-test suite.

---

## Phase 21 — Deprecated-Code / Test-Warning Cleanup (DONE)

**Goal:** Eliminate the `LegacyAPIWarning` (SQLAlchemy `Query.get()` is legacy;
use `Session.get()`) surfaced in the test run.

**Changes made (behavior-preserving)**
- Migrated every `Model.query.get(id)` to `db.session.get(Model, id)` in app
  code (`app/__init__.py` `load_user`, `app/reports.py` campus resolver,
  `app/recommendation/engine.py`, `app/routes/director.py`) and in
  `tests/test_app.py` (User/Event/Notification/Registration lookups).
- Migrated every `Model.query.get_or_404(id)` to the explicit equivalent
  `obj = db.session.get(Model, id); if obj is None: abort(404)` in
  `app/routes/admin.py` (4), `app/routes/coordinator.py` (3),
  `app/routes/events.py` (2), `app/routes/notifications.py` (1). Added `abort`
  to the Flask imports of `admin.py`, `events.py`, and `notifications.py`.
  (Flask-SQLAlchemy 3.1.1 does not expose `db.session.get_or_404`, so the
  manual form is required to clear the framework-internal warning.)

**Verification:** Full suite **149 passed, 0 warnings** (down from 149 passed /
141 warnings). `git diff --check` clean (only pre-existing CRLF warnings). No
behavioral change — 404 handling is identical.

---

## Phase 22 — Final Manuscript-to-Software Compliance Audit (DONE)

> Note: the manuscript PDF itself was not machine-readable in this session, so
> this audit is derived from the controlling plan artifacts (the Next Phases
> Plan, the Phase 18 manuscript-grounded spec, and prior phase summaries). Each
> requirement is marked PASS / PARTIAL / DATA UNAVAILABLE.

**Verification re-run:** security + feature test classes
(`TestRoleAccess`, `TestCoordinatorEventEditing`, `TestAnalytics`,
`TestReportingSystem`, `TestOutsiderVolunteers`, `TestNotifications`,
`TestAuth`) → **90 passed, 0 failed**. Full suite remains **149 passed, 0
warnings**. `git diff --check` clean.

### Consolidated compliance matrix

| # | Manuscript / plan requirement | Status |
|---|---|---|
| A1 | RBAC (volunteer/coordinator/director/admin) with server-side enforcement | PASS |
| A2 | CSRF protection on all state-changing requests | PASS |
| A3 | Coordinator scoped to own campus (server-side, no forged `?campus_id`) | PASS |
| A4 | Director/Admin university-wide, view-only (no event/user mgmt) | PASS |
| A5 | Volunteer denied privileged analytics/reports (redirect) | PASS |
| B1 | Coordinator campus-scoped CSV/PDF reports | PASS |
| B2 | Director/Admin university-wide CSV/PDF with date/campus/category filters | PASS |
| B3 | Dashboard == CSV == PDF for same scope (Phase 18 alignment) | PASS |
| B4 | Historical (audited) records kept separate from live data | PASS |
| C1 | ExternalParticipant model; nullable `Registration.user_id` | PASS |
| C2 | Public join + coordinator manual encode for outsiders | PASS |
| C3 | PSU vs Outsider classification in analytics (no fake User accounts) | PASS |
| D1 | In-app notifications + list + owner-only mark-read | PASS |
| D2 | Coordinators notified on registrations / external adds | PASS |
| E1 | Coordinator edits own-campus events; 403 cross-campus | PASS |
| E2 | Edit never changes campus; capacity ≥ existing registrations | PASS |
| F1 | Recommendation = binary cosine similarity (NOT TF-IDF, no scikit-learn) | PASS |
| F2 | Synonym normalization + participation-history weighting; cold-start ok | PASS |
| G1 | Participation trends (monthly + weekly engagement) | PASS |
| G2 | Attendance rates | PASS |
| G3 | Sign-up → attendance conversion rate | PASS |
| G4 | Cross-campus comparison (registrations/attended/rate/hours) | PASS |
| G5 | Activity performance (registrations/attended/conversion) | PASS |
| G6 | Campus distribution / participation levels | PASS |
| G7 | Category distribution | PASS |
| G8 | Skill / interest affinity distribution (descriptive) | PASS |
| G9 | PSU vs Outsider participation | PASS |
| G10 | Role distribution (RBAC roles) | PASS |
| G11 | Student/Faculty/Staff distribution | **DATA UNAVAILABLE** |
| G12 | College affiliation distribution | **DATA UNAVAILABLE** |
| G13 | Longitudinal trends (monthly; semester labels N/A) | PARTIAL |
| H1 | No placeholder text / dead controls in UI | PASS |
| I1 | Accessibility: `scope="col"` on tables, labeled controls | PASS |
| J1 | No deprecated-code / test warnings (`Session.get` migration) | PASS |
| K1 | Social media sharing / analytics | **Excluded by plan** |

### Residual gaps (documented, not defects)
- **G11/G12** — Student/Faculty/Staff classification and College affiliation are
  not collected by the schema; cannot be produced without a new data-collection
  subsystem (out of scope per Phase 18.21/18.37). PSU-vs-Outsider is provided.
- **G13** — Live longitudinal trend is monthly (and spans years via month keys);
  academic-semester bucketing is unavailable because the schema has no semester
  field. Historical module supplies year-level aggregates separately.
- **Charts** — trend/campus/comparison visuals are responsive CSS bars (no
  Chart.js/Plotly wired); all required metrics, labels, units, and chronological
  ordering are present. Predictive analytics (`forecast_turnout`, `volunteer_segments`,
  `campus_engagement_significance`) exist but are out of the descriptive scope and
  are not advertised as required manuscript outputs.

---

## Phase 23 — Final Live Acceptance Test (DONE)

**Method:** Playwright (headless Chromium) drove the running app on the **live
MariaDB** database (`DevelopmentConfig`). Each role used a fresh browser context
to isolate sessions. A temp script `verify_phase23.py` (not committed) ran the
battery; live DB was not mutated (read-only checks + one expected 403).

**Result: 19/19 PASS**

| Check | Result |
|---|---|
| server:reachable (live MariaDB) | PASS |
| login: volunteer / coordinator / director / admin | PASS (land on role dashboards) |
| volunteer denied `/analytics` | PASS (redirected to `/volunteer_dash`) |
| volunteer denied `/coordinator_analytics` | PASS (redirected) |
| coordinator `/coordinator_analytics` renders | PASS (200) |
| director `/analytics` renders + `scope="col"` | PASS (200, scope present) |
| director export university.csv / .pdf | PASS (downloads) |
| director export campus.csv / .pdf | PASS (downloads) |
| coordinator export events.csv / .pdf | PASS (downloads) |
| coordinator `/attendance` loads | PASS (200) |
| coordinator `/notifications` loads | PASS (200) |
| coordinator cross-campus event edit → 403 | PASS (event campus 2, coord campus 1) |
| responsive: no horizontal overflow @375px | PASS (overflow 0px) |

Downloaded filenames confirmed: `psu_university_activity.csv/.pdf`,
`psu_historical_campus_participation.csv/.pdf`, `campus_events.csv/.pdf`.

---

## Remaining backlog (not started)

Per the plan's final priority order, remaining item (Phase 17 skipped — not
manuscript-supported; Phases 18–23 done):

1. Commit / push preparation — Phase 24

> Social media sharing is intentionally excluded per the plan.

> Status: Phase 23 done. Phase 24 (commit/push) was **deferred by user choice
> ("Do nothing") — no commit and no push performed**. All changes remain
> uncommitted and unpushed. `git diff --check` clean. Tests: 149 passed / 0
> warnings. Live acceptance: 19/19 PASS. When committing later: add `*.log` to
> `.gitignore` (excludes `server_err.log`/`server_out.log`) and include
> `Completed_Work_Summary.md`.

