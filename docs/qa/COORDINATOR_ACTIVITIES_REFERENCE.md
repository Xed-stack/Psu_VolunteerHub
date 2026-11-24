# Coordinator Activities Reference — 24 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No database, migration, dependency,
permission, route change for staff roles, or deployment action. Unrelated
working files and untracked proposals, documents, images, output and tmp remain
untouched.

The signed-in Coordinator view of `/workspace/activities` now follows the
supplied compact reference. PSU navy, gold and white, Inter typography, the
existing shell, all activity routes, permissions, drafts, search, filters and
pagination are preserved. Energy 2 / Rhythm 2 / Motion 1.

## Design critique

Applied during work and against the rendered result. Design Critique is not an
installed skill in this session, so its responsibilities were applied directly.

- High, defect: the previous list did not expose the decision data on the card.
  Each card now shows real registration progress, target, capacity, schedule and
  a direct View Activity action.
- Moderate, defect: the old tab row had no counts and included Cancelled beside
  the primary schedule states. The Coordinator view now shows Upcoming, Ongoing,
  Past Activities and All Activities with real scoped counts. The state=cancelled
  URL still works, and the Director and Admin tab row is unchanged.
- Moderate, defect: typography mixed 11px and 12px supporting text with a dense
  date badge. Supporting text now uses 14px, card titles 18px and the page
  description 16px, matching the other workspace screens.
- Low, deliberate: the reference displays an All Campuses selector. Coordinators
  remain scoped to their assigned campus, so the page shows a fixed campus chip
  rather than a control that would do nothing.
- Low, deliberate: the reference's milestone and partner chips are illustrative.
  Only real proposal documents and derived low-registration status are shown.

## Changes

`templates/workspace/coordinator_activities.html` is a new Coordinator-only
template. `app/routes/workspace.py` selects it for Coordinators and keeps the
existing template for Directors and Admins. Counts, registration totals,
percentages and status labels are computed in the route from scoped queries.
Search now also matches conducting department. The Coordinator page uses five
rows per page; Director and Admin remain at fifteen.

`ui/app.css` and rebuilt `static/styles/app.css` add scoped styles and a mobile
reflow that gives the search field full width below 768px.

## Verification

- Focused case `tests/test_coordinator_activities_reference.py` passed, covering
  counts, five-row pagination, real target figures, low-registration attention,
  proposal filename, department search, fixed campus scope and Director template
  isolation.
- Existing literal-search, workspace-screen and Director filter cases passed.
  One unrelated historical-reports assertion about two forms containing `year`
  remains pre-existing and failing.
- Disposable Chromium check passed six groups: sign-in, all widths at 1440, 1024,
  768, 390 and 320px with no horizontal overflow, 44px targets, no console
  errors, and screenshots at 1440 and 390px.
- Current Web Interface Guidelines were fetched earlier and applied: native
  labels and controls, visible focus, 44px targets, wrapped text, tabular
  numbers and a live result summary. Antislop was applied during work with real
  counts only.

## Limitations and rollback

The fixed bottom navigation is part of the shared shell. Full-page screenshots
can show it mid-page, but the page itself reserves scroll space. No
physical-device, manual screen-reader, true browser-zoom, full-suite or
operational-database claim. Rollback restores the route and CSS, rebuilds CSS,
and removes the new template, test and note. No data rollback is needed.
