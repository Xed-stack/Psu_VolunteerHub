# Fixed PSU Campus Catalogue QA

## Behavior and Decisions

- `app/campuses.py` defines the nine existing PSU name/code pairs once.
- Database rows and foreign keys remain in use. Missing official rows are added
  by initialization or the explicit `sync-campus-catalogue` command.
- Unsupported names/codes fail validation with names, codes, and IDs in the
  diagnostic. Automatic deletion, renumbering, and reassignment were ruled out
  because they would change existing user/activity/report relationships.
- Production startup validates existing rows without seeding or schema writes.
  Empty production databases remain available for explicit `init-production`.
- Selectors and import lookups use the canonical query; request validation rejects
  unknown IDs while existing registration/report validation keeps its feedback.
- Campus creation returns 410. Add Campus and duplicate System Settings cards
  are removed; the sidebar Settings page remains available.
- Admin campus controls receive a minimum 44px height and a visible PSU-blue
  keyboard outline, addressing the selector check during this review.

## Verification

79 tests passed across `test_fixed_campuses.py`, `test_production_init.py`,
`test_production_startup.py`, `test_system_performance.py`, `test_auth_remake.py`,
`test_report_queries.py`, and `test_create_activity_form.py`.

The new tests cover partial/idempotent seed repair, preserved IDs, custom-row
diagnostics and preservation, production startup refusal, invalid query IDs,
disabled campus creation, retained Settings access, and the sync command.
An additional targeted run passed all five invalid-ID cases, including an
oversized integer that must be rejected before reaching the database driver.
The broader `test_app.py` selection for Admin, registration, campus, Coordinator
creation, and reports passed all 132 selected tests (180 unrelated tests excluded).

Isolated in-memory Chromium checks at 1440px, 720px, and 390px:

- PASS: seven Admin control cards; removed cards absent.
- PASS: sidebar Settings navigates to System Settings.
- PASS: Create User shows nine campus options plus the existing unassigned option.
- PASS: campus selector keyboard focus and 44px targets.
- PASS: dashboard/form page width contained; no browser page errors.

The 720px check represents 200% reflow from a 1440px viewport, not native browser
zoom. Browser tests used isolated synthetic records and did not modify app data.

## UI Delivery Gate

- Hard Gate PASS for changed controls: real Settings navigation, preserved option
  IDs, server-side validation, visible focus, 44px targets and contained layouts.
- Purpose Gate PASS: removing duplicate cards simplifies Admin controls; PSU blue
  marks existing navigation/focus. Existing type and card styles are reused.
- Liveliness PASS: existing PSU identity and ENERGY 1 / RHYTHM 2 / MOTION 1 retained;
  no new visual assets, decoration, typography, or animation.
- Craftsmanship PASS for changed UI: native selectors/links, desktop/mobile checks,
  keyboard focus, and existing empty/error layouts retained.
- Current Web Interface Guidelines fetched from the Vercel source and reviewed
  against the changed Admin controls, onboarding copy, and campus selector rules.
  No remaining findings in the changed UI scope.

## Delivery

No dependencies or schema changes. No application database cleanup or remapping.
No commit, push, or deployment. Unrelated workspace edits are preserved.
