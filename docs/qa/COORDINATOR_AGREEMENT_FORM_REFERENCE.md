# Coordinator Add MOA Form Reference — 25 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No database, migration, dependency,
permission, route or deployment change. Unrelated untracked work remains
untouched.

The Coordinator-only `/workspace/partners/<id>/agreements/new` page now follows
the supplied reference: a compact heading with agency chip, a single card with
the shared draft strip, reference field, paired validity dates, upload field and
Cancel/Save actions. PSU navy, gold and white, Inter typography and the existing
shell are preserved. Energy 2 / Rhythm 2 / Motion 1.

## Design critique

Applied during work and against the rendered result. Design Critique is not an
installed skill in this session, so its responsibilities were applied directly.

- High, defect: the old form used flat panel styling with inconsistent field
  spacing. The new card groups review, dates, document and actions in one
  deliberate column with real required markers.
- Moderate, defect: the draft strip and agency context were easy to miss. The
  agency chip sits beside the heading and the shared draft status is styled as
  a highlighted strip with a red Discard Draft action.
- Moderate, defect: labels and helper text mixed sizes. Labels are 14px, inputs
  16px, section titles 18px and the heading 30px, matching the other workspace
  forms.
- Low, deliberate: the reference shows a combined saved-time suffix in the draft
  strip. The shared draft script is left as the single source of status text so
  Saving, Draft saved and Draft restored stay truthful.
- Low, deliberate: the reference shows `dd/mm/yyyy` placeholders. The existing
  MOA date picker is retained, including native date inputs when JavaScript is
  disabled.

## Changes

`templates/workspace/agreement_form.html` was rebuilt around the existing
`moa_dates`, `info_tip`, CSRF, draft key and upload markup. All field names,
validation values, error anchors, `return_to` back links, `activity_context`
and Save Agreement behaviour are unchanged. `ui/app.css` and rebuilt
`static/styles/app.css` add scoped `.agreement-form-reference` styles, a two
column date reflow and 44px controls. The layout case was added to
`tests/test_coordinator_partners_reference.py`.

## Verification

- 41 focused cases passed across partner journey and Coordinator partner
  reference flows. Two unrelated Overview review-card assertions remain
  pre-existing and failing; they do not touch this form.
- Disposable Chromium check passed six groups: reference text, placeholders,
  draft strip and real controls, then 1440, 1024, 768, 390 and 320px with no
  page overflow, 44px targets and no console errors. Evidence is ignored under
  the local temp directory used for the preview.
- Current Web Interface Guidelines and Antislop were applied during work:
  native labels and controls, visible focus, wrapped text, tabular-safe form
  layout and no invented agreement data.

## Limitations and rollback

The shared date picker shows a readable date button instead of the literal
`dd/mm/yyyy` placeholder when JavaScript is enabled. The draft strip does not
invent a save timestamp. No physical-device, manual screen-reader, true
browser-zoom, full-suite or operational-database claim. Rollback restores the
template and CSS, rebuilds CSS and removes the new test case and note. No data
rollback is needed.
