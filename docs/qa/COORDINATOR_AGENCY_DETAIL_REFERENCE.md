# Coordinator Partner Agency Detail Reference — 25 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No database, migration, dependency,
permission, route or deployment change. Unrelated untracked work remains
untouched.

The Coordinator-only `/workspace/partners/<id>` page now follows the supplied
reference: a compact identity card with derived MOA status and Add MOA action,
a Contact Details card with three field tiles, an agreements section, and the
existing Back to Agencies, Edit Agency Details and draft-agency selection
actions. PSU navy, gold and white, Inter typography and the existing shell are
preserved. Energy 2 / Rhythm 2 / Motion 1.

## Design critique

Applied during work and against the rendered result. Design Critique is not an
installed skill in this session, so its responsibilities were applied directly.

- High, defect: the old page mixed a small heading, a bare definition list and a
  dense table. The identity and contact information now use a clear two-level
  hierarchy with real status and agreement data.
- Moderate, defect: status was only visible in the agreements table. The hero
  now carries the same MOA-derived chip as the Partner Agencies list.
- Moderate, defect: type scale was inconsistent. Field labels are 12px, values
  16px, section titles 18px and the agency name 24px, matching the other
  workspace screens.
- Low, deliberate: the reference shows an agency type chip, a contact role and
  a record creation date. The model has no such fields, so they are omitted
  rather than invented. Footer copy states only that the agency is in the
  campus directory.
- Low, preference not adopted: a wide mobile table rewrite would change the
  shared agreements pattern. The existing contained table scroll is retained.

## Changes

`templates/workspace/partner.html` was replaced with the reference composition.
`app/routes/workspace.py` now shares `describe_agency()` between the list and
detail views so status and agreement counts have one source of truth. The detail
route passes the derived status, campus name and today's date. The existing
`return_to` back link, `activity_context=create` selection form, MOA links,
pagination and validity badges are unchanged.

`ui/app.css` and rebuilt `static/styles/app.css` add scoped `.agency-reference`
and `.agency-card` styles plus a mobile stack. The focused detail test was
added to `tests/test_coordinator_partners_reference.py`.

## Verification

- 43 focused cases passed across partner journey, agency list and proposal
  record flows; the detail reference case also passed separately.
- Disposable Chromium check passed six groups: reference content and real
  agency data, then 1440, 1024, 768, 390 and 320px with no page overflow, 44px
  targets and no console errors. Evidence is ignored under the local temp
  directory used for the preview.
- Current Web Interface Guidelines and Antislop were applied during work:
  native controls, visible focus, wrapped text, real labels and no invented
  agency facts.

## Limitations and rollback

Agency type, contact role and record creation date remain unavailable because
no source field stores them. The mobile agreements table uses the existing
contained scroll rather than a new card layout. No physical-device, manual
screen-reader, true browser-zoom, full-suite or operational-database claim.
Rollback restores the route, template and CSS, rebuilds CSS and removes the new
test and note. No data rollback is needed.
