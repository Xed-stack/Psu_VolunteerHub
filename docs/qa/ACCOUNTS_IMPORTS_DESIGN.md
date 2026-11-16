# Accounts and Imports: Analysis and Design

## Analysis before implementation — 14 November 2026

Admin account routes already enforce Director access, self/final-Director protection,
30-day deletion eligibility and session/token invalidation. Preserve those POST routes.
The list currently mixes global account counts/database health with filtered records,
and embeds deactivation actions. Editing also embeds password reset. Move those tasks
to a record screen and a dedicated reset screen; leave audit history reachable.

Create preserves only some submitted selections after failure. Edit mutates ORM fields
before validating, redirects away on duplicate ID and does not validate duplicate email.
Collect and validate submitted values before assignment, render failures with the same
values, and retain existing role/profile synchronization. Passwords never become drafts.

User imports privately stage password-hashed JSON with a session token. Dataset imports
stage CSV with a session token and content hash, dry-run the existing importer, then
confirm transactionally. Neither currently restores preview presentation on GET. Add
GET review/pagination and POST discard around the existing staged files; never put
tokens/credentials/private paths in URLs or display hashes. Confirm always processes
the complete validated file and revalidates against current data.

Historical validation returns trusted importer text, not structured per-row outcomes.
Keep that text as readable validation messages rather than inventing row statuses.
CSV rows can be previewed as source records, explicitly distinguished from changes.
Annual importer counts database records, not CSV rows; label those measures separately.

## Design read and wireframes

PSU administrative workspace for Directors. Energy 2/rhythm 2/motion 1. Reuse Inter,
blue #00408b, deep blue #002b60, gold #f4bd27, ink #111c2c and white/slate surfaces.
Use existing compact headings, 44px controls, minimal filters and Newspaper Case.

```text
User Accounts                                      Add User
Active | Deactivated | Activity Log
Search / Campus     More Filters: Role / Affiliation
User, email | Role | Campus / affiliation | Status | View Record
Matching result count / pagination
```

```text
Back to filtered user list
User identity / status                              Edit Account
Account facts                              Access and account actions
Created / deactivated / reactivation dates  Reset Password / Deactivate / Reactivate
                                           Deletion eligibility + confirmation
```

```text
Import Accounts / Historical Activities / Annual Plans
Upload → Review → Confirm
Upload: format guidance / file control / Validate and Preview
Review: filename / trustworthy outcome / source rows / pagination
        Choose Another File | Discard Preview | Confirm All N Records (or Rows)
Success: actual outcome + relevant destination
```

Phone: heading/actions stack, filters remain primary/More, record facts become one
column, source tables have labelled keyboard scroll regions. Forms use a narrow
reading width and grouped Identity / Campus and Affiliation / Access fields.
Password reset is separate, has no autosave, and clears secret inputs after failure.
No new charts, imagery, animation, framework, database schema or CSV format.

States: populated/empty/search-empty, validation errors with field links, saved/error
draft feedback, active/deactivated/ineligible actions, private preview available,
missing/tampered/stale preview, successful confirmation and repeat-confirm rejection.
Technical database status belongs in an optional Management disclosure. Account CSV
is explicitly Export All Accounts; it does not claim to follow list filters.

## Preservation checklist

- [x] List filters, literal matching, pagination and safe contextual Back links.
- [x] Account guards, role/profile synchronization, session invalidation and audit.
- [x] Ordinary draft restoration, validation values and secret exclusion.
- [x] Private import tokens/files, revalidation, transactional rollback and full confirm.
- [x] Review refresh/resume, replacement/discard, pagination and recovery states.
- [x] Mobile/200% text, keyboard, build/templates, focused/browser regressions and preview.

## Implemented destinations and behavior

| Previous presentation | Current destination | Return path |
| --- | --- | --- |
| List role/deactivation/reactivation/deletion controls | User Record → Edit Account / Account Access | Back to the filtered list; action completion restores its context |
| Password reset below Edit | User Record → Reset Password | Back to User Record, with the original list context retained |
| Flat Management directory and account-list database status | Accounts / Data / Configuration; optional System Information | Management remains the parent |
| User preview returned only by POST | Upload → GET `stage=review`, 25 rows/page → Confirm | Resume from Upload or Import Data; choose replacement or discard |
| Annual/historical raw console panel | Validation message + paginated, allowlisted source columns | Same review, resume, replacement and discard actions |
| Ambiguous account export | Export All Accounts | Clearly independent from list filters |

Account create/edit retains submitted fields on validation errors. Drafts include role,
campus and ordinary identity/affiliation values, exclude passwords, and clear after
successful submission. Reset has no draft and renders blank secret fields on failure.
Legacy reset POST callers may still omit confirmation; the visible form requires it.

Imports use existing routes/CSV formats and importers. Source rows are not invented
per-row validation statuses. Annual record counts cover entities, not CSV rows.
Confirmation consumes the entire file and rechecks current constraints. User stages
now also have integrity/owner checks and detect a changed minimum-password policy.
Valid replacement removes the previous private file; invalid replacement preserves
it. Missing/changed files cannot import and clear the unusable session preview.
Resume requires the same authenticated browser session; clearing/expiring that
session requires reupload. Tokens are hidden POST fields, never URL parameters.

One existing account defect was repaired: eligible deletion now explicitly deletes
the account's password-reset tokens, avoiding an ORM attempt to set a non-null
token owner to NULL. The 30-day, inactive-account and self-deletion guards remain.

## Verification — 14 November 2026

- `pytest tests/test_accounts_imports_ui.py tests/test_historical_import.py -q`:
  **27 passed**. Full-file confirmation across pages, refresh/resume, secret exclusion,
  replacement/discard, wrong token, missing/tampered file, different session, late
  account conflict, importer rollback, role restrictions, form values/drafts, reset
  revocation, password-policy change, protected accounts and eligible deletion.
- Connected workspace + annual importer regression: **50 passed**. Includes drafts,
  upload restoration, consent exclusion, registrations, attendance boundaries, exports
  and annual immutable-definition/rollback checks. Existing plotting warnings remain.
- Existing filter grouping and Newspaper Case checks: **2 passed**.
- Final narrow file-recovery checks: **2 passed**; final create-error rendering: **1 passed**.
- Chromium: **60 check groups**, no page errors. Viewports 320, 390, 768, 844 landscape,
  and 1440px; account draft refresh and filtered return path; all three import review
  screens, user confirmation, dataset paging/resume/discard; reduced motion and 200%
  text sizing. Before: 45 layout checks. Wide tables use contained horizontal scrolling.
- `npm run build`, **112 Jinja templates compiled**, `node --check
  static/scripts/drafts.js`, and `git diff --check` passed.
- Contrast: PSU blue/white **9.97:1**, slate-600/white **7.58:1**, red-700/white
  **6.47:1**. All pass WCAG AA normal text.
- Live preview login smoke: Director, Coordinator and Volunteer each returned 200 to
  their appropriate dashboard, using the existing private preview database.

An early browser assertion expected “Draft saved” after restoration; corrected to
the actual “Draft restored” state. A viewport transition assertion needed to wait
for the rendered capture before measuring layout. Both final journeys pass.

### Existing failures and limits

The older `tests/test_app.py` account suite creates the removed `admin` enum role and
fails in fixture setup before exercising routes (`LookupError: admin ... user_roles`).
It also contains immediate-import and old redirect expectations. These were not
globally rewritten; current Director fixtures cover the affected protections.
The existing two-step workspace import test was updated to follow the new review
redirect. Do not claim the complete historical test suite passed.

Browser checks emulate touch/viewport/text sizing; no physical-device or manual
screen-reader session was performed. No production data, migration, dependency,
commit, push or deployment was part of this pass. No broad dead-code cleanup.

## UI audit and delivery gate

Reviewed changed templates and shared helper/script edits against the current
[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
retrieved 14 November 2026. In-scope fixes: meaningful labels/selected destinations,
native confirmations, linked and focused validation summary, inline described field
errors, secret exclusion, visible scopes and unfiltered-export wording. Native table
scroll regions have names and keyboard access. Existing focus, motion, submit/loading,
empty and error treatments are reused. Fixed role chip labels use explicit display
labels; authored values are unchanged. No unresolved changed-screen audit findings.

Antislop during-work delivery gate: ENERGY 2 / RHYTHM 2 / MOTION 1, as specified in
the design read. PSU blue identifies primary action/navigation; gold remains the
existing selected-navigation accent. Record content leads, access actions are secondary;
import progress expresses the real three-stage workflow. No invented metrics, decorative
imagery, added animation or generic marketing sections. Existing directories retain
task links, lists retain real data, and errors/empty states offer an available next step.

## Local review, artifacts and rollback

Open `http://127.0.0.1:5000`. Director: `director@psu.edu` / `password`.
Management → User Accounts → View Record → Edit Account / Reset Password.
Management → Import Data → choose type → upload → review → confirm or discard.
Coordinator `coordinator@psu.edu` and Volunteer `student@psu.edu` also use `password`.
Sign in again after restart. Mail is suppressed in the private preview.

Screenshots and JSON evidence are in `.qa-overhaul-temp/accounts-imports/before/`
and `after/`, including `9-1440.png`, `9-390.png`, and each
`user-review`, `annual-review`, `historical-review` at 1440/320px. Private generated
artifacts and databases remain ignored; no fixture values become dashboard data.

Repeat with `.venv/Scripts/python.exe scripts/qa_accounts_imports.py --stage after`
and the pytest/build commands above. The QA runner uses disposable test fixtures.
Preview launcher: `.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py`.

Rollback: first copy this pass's diff and new files. Baseline is commit
`b76a620ede55835371c021d325cd7812e615a6fa`. Restore only this pass's tracked account,
import, UI-helper/draft, and template files from that baseline; remove only its added
`app/import_previews.py`, account detail/reset templates, shared import-review macro,
test and QA runner if no longer needed. Rebuild Tailwind and restart the private preview.
Do not reset the branch, remove unrelated files, or replace databases/uploads.
