# Coordinator Partner Agencies Reference — 24 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No database, migration, dependency,
permission, route or deployment change. Unrelated untracked proposals,
documents, images, output and tmp remain untouched.

The Coordinator-only `/workspace/partners` page now follows the supplied
reference layout: compact header, search and MOA status filters, a real quick
summary, a five-column agency table and numbered pagination. PSU navy, gold and
white, Inter typography, the existing shell and every partner/agreement route
are preserved. Energy 2 / Rhythm 2 / Motion 1.

## Design critique

Applied during work and against the rendered result. Design Critique is not an
installed skill in this session, so its responsibilities were applied directly.

- High, defect: the old list showed only an agreement count. Each row now shows
  the contact, agreement reference and a status derived from real MOA dates.
- Moderate, defect: the old header had no scope chip or purpose line. The page
  now states the campus and the three jobs it supports.
- Moderate, defect: typography mixed very small table text with inconsistent
  row spacing. Supporting text is 14px, agency names 16px, headings 30px and
  status chips 12px, matching the other workspace screens.
- Low, defect found after rendering: a squeezed search field at 768px and the
  grammar "1 Agreements". The filters now reflow below 1024px and singular
  counts read correctly.
- Low, deliberate: the reference shows agency type, contact role and an
  accreditation validity claim. No such fields exist in the model, so they are
  omitted rather than invented. The summary shows the current campus directory
  year only.

## Changes

`templates/workspace/partners.html` was replaced with the reference composition.
`app/routes/workspace.py` now derives Active Valid, Pending Renewal, Upcoming MOA
and No MOA on file from agreement dates, adds an `moa_status` filter, and extends
search to email. Counts come from the whole campus directory, independent of
search and status filters. Pagination remains at 25 rows per page and preserves
query strings. `activity_context=create` and the Back to Activity Draft link are
unchanged.

`ui/app.css` and rebuilt `static/styles/app.css` add scoped styles and a mobile
reflow that gives the search field full width below 1024px. The model's selectin
eager loading was retained, so adding agencies does not produce N+1 queries.

## Verification

- 30 focused cases passed across the new reference test, the partner journey and
  literal search checks. The new case covers real summary counts, all four MOA
  states, status filtering, email search, invalid status and draft context.
- Disposable Chromium check passed six groups: sign-in, summary/status text and
  real references, then 1440, 1024, 768, 390 and 320px with no horizontal
  overflow, 44px targets and no console errors. Evidence is ignored under the
  local temp directory used for the preview.
- Current Web Interface Guidelines and Antislop were applied during work: native
  labels and controls, visible focus, wrapped text, tabular numbers, a live
  result summary and no invented agency facts.

## Limitations and rollback

Agency type, contact role and accreditation claims remain unavailable because no
source field stores them. The fixed bottom navigation is part of the shared
shell; full-page screenshots can show it mid-page, but the page reserves scroll
space. No physical-device, manual screen-reader, true browser-zoom, full-suite or
operational-database claim. Rollback restores the route, template, source and
built CSS, then removes the new test and note. No data rollback is needed.
