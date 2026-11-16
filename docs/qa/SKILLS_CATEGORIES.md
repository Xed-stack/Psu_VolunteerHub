# Director Skills and Activity Categories — 16 November 2026

## Analysis and design

The former categories page used hard deletion and reassigned activities to General.
Skill selection came from database rows but signup connections came from Config.
Category creation helpers merged configured lists back into selectable rows. Those
paths must change together for archival and signup connectivity to be reliable.

Approved design: Management → Skills and Activity Categories → Skills / Activity
Categories tabs. One search/status row, alphabetical paginated results, one primary
add action, concise usage counts, and Archive/Restore. Skill creation and connection
editing use a dedicated connected form. Existing PSU blue/gold, Inter, institutional
white workspace, native controls and shared Tailwind components; no new libraries.
ENERGY 2 / RHYTHM 2 / MOTION 1. Gold/navigation states retain existing shell meaning.

Desktop: `[heading/back] [tabs] [search/status] [add] [result rows/actions] [pagination]`.
Phone: same reading order, wrapping filters/actions and single-column skill form.
Catalogue is university-wide and Director-only. Interests remain a separate fixed
institutional list; skills may connect to several existing interests.

## Implementation and verification

Implemented `/workspace/catalogue` with tab/status/q/page, explicit CSRF-protected
Director actions, skill creation/interest editing, protected General, archive/restore,
usage counts, literal search, escaped highlighting and 25-row pagination. Existing
category GET redirects to its new tab; legacy create/delete POSTs delegate to the new
actions. Delete now archives without activity reassignment or notifications. Archived
duplicates lead to their Restore action. Sidebar/header identity and Help updated.

`Skill.is_active`, `ActivityCategory.is_active`, `interest_skills` and a one-time
backfill marker keep IDs/assignments intact. Database choices replace Config fallback.
Startup seeding never reactivates archived rows or replaces managed connections.
New skills are mapped to existing interests; interest/category identities stay separate.

Profile/activity edits can retain an assigned archived skill/category; new forged
archive assignments are rejected. Signup revalidates mapping/active IDs at submission.
Stale signup drafts name unavailable skills; activity drafts show replacement warnings.
Profile bootstrapping skips archived skills. Existing recommendation scoring and
historical reporting datasets remain unchanged.

## Verification

- Catalogue/signup/auth run: **34 passed, 1 deselected** (existing profile-heading
  casing assertion). Final catalogue/workflow run: **11 passed**. Activity workflow
  run: **7 passed**. Legacy redirect/proposal/profile follow-up: **10 passed**.
  These runs overlap. Archived duplicate Restore regression passed separately.
- Broad initial profile/activity/workspace run: **91 passed, 11 failed**. Five failures
  resolved and rerun: catalogue fixtures now seed actual database categories, legacy
  GET permission assertion follows its new redirect, and profile impact helpers now
  receive their template context. Six old `test_profile_repair.py` cases remain:
  `selected_render_and_links`, `unavailable_catalog_disables_save`,
  `photo_replacement_and_removal`, two `milestones_require_completed_present` variants,
  and `profile_role_isolation[admin]`. They assume prior default profile content or the
  removed Admin enum; no full historical-suite pass claimed.
- **11 catalogue Chromium groups** passed: 320–1440px, tablet/landscape, create,
  pagination context, archive/restore, mapping edit, signup/stale draft integration,
  category actions, General protection, 200% text and other-role denial. No page errors.
- **15 signup Chromium groups** passed after database mapping integration, covering
  ordinary draft restoration, consent/password exclusion and complete signup/sign-in.
- Tailwind build, all **119** templates, JS syntax and diff checks passed. Desktop and
  phone captures inspected under `.qa-overhaul-temp/catalogue/screenshots/`; signup
  evidence remains under `.qa-overhaul-temp/signup-onboarding/after/`.
- Current Web Interface Guidelines fetched/reviewed 16 November 2026. Native actions,
  explicit Status label, linked/inline skill errors, focus, preserved URL state,
  escaped authored values, touch targets and responsive wrapping checked. Existing
  measured PSU contrast retained. Antislop gate reviewed: no in-scope findings.

Limits: Chromium/emulated viewports; no physical-device/manual screen-reader test.
SQLite migration executed; MySQL/MariaDB DDL supported but not runtime-verified here.

## Explicit migration and rollback

The migration is never invoked at production startup. Back up the exact target first.
Set `DATABASE_URL` securely for the intended database, then run:

```powershell
.venv/Scripts/python.exe scripts/migrate_catalogue.py --database '<exact database name or SQLite path>' --dry-run
.venv/Scripts/python.exe scripts/migrate_catalogue.py --database '<exact database name or SQLite path>'
```

Exact database identity is required. Run sequentially. Existing metadata tables and
managed flags are added, General ensured, and configured mapping backfilled only once.
Changing connections afterward is not undone by repeating migration or restarting.

Local evidence: `.qa-overhaul-temp/catalogue/migration-evidence.json` records dry-run,
repeat upgrade, restore-from-backup rehearsal and private preview upgrade. All sampled
rows matched exactly: 6 users, 9 events, 33 event-skill links, 9 user-skill and 9
user-interest links; attendance/consent tables retained (empty in this preview).
Backup: `.qa-overhaul-temp/catalogue/preview-before-db7cdb31.sqlite`.

For rollback stop the preview, preserve a new snapshot of any subsequently entered
data, and restore the appropriate backup with the corresponding pre-catalogue code.
The backup restores earlier data, so never overwrite later changes without reconciling
them. SQLite restore was rehearsed on a disposable copy. MySQL DDL may commit in steps;
use its database backup/release procedure rather than assuming transactional DDL undo.

Code-only rollback must reverse this catalogue pass in models, routes, choices,
templates, seed/migration integration and tests together; retain every prior local UI
pass. Do not reset the working tree or apply schema downgrades to operational data.

## Local delivery

Director → Management → Skills and Activity Categories, or
`http://127.0.0.1:5000/workspace/catalogue`. Private preview data/uploads retained,
mail suppressed. Work local/uncommitted on `codex/ui-workflow-overhaul`. No operational
database changes, commits, pushes or deployment. New dependencies: none.
