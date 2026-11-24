# Coordinator AOP Goals Reference — 24 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No database, migration, dependency,
permission, calculation or deployment change. The unrelated HANDOFF.md entry,
SQL proposals, review images, documents, output and tmp remain untouched.

The signed-in Coordinator view of `/annual-goals/workspace` now follows the
supplied compact reference. It keeps the PSU navy, gold and white identity,
Inter typography and the existing shell, routes, drafts, exports and progress
calculations. Energy 2 / Rhythm 2 / Motion 1. No new decoration or second
visual language.

## Design critique

Applied during work and against the rendered result. Design Critique is not an
installed skill in this session, so its responsibilities were applied directly.

- High, defect: linking completed activities, the action that earns AOP credit,
  was only reachable through the goal title. It now has a direct button on each
  committed card.
- Moderate, defect: campus and university figures used near-identical labels in
  repeated groups. The campus band is now a distinct, primary block with its
  own label, followed by compact university context.
- Moderate, defect: no explicit status signal existed on the list. Chips now
  show In Progress, Above Target, No Commitment Yet, Overdue · Work Remaining
  and Target Met, always with text rather than colour alone.
- Low, defect found after rendering: an orphaned required marker above AOP Year
  and the grammar "1 campuses" were corrected.
- Low, preference not adopted: a summary donut or KPI strip would add scanning
  but risks a competing visual language on a comparison-first page.

## Changes

`templates/goals/coordinator_aop_index.html` is a new Coordinator-only template.
`app/routes/aop.py` selects it for Coordinators; Directors and admins keep their
existing templates. `ui/app.css` and rebuilt `static/styles/app.css` add scoped
styles. Statuses, percentages and counts all come from the existing
`aop.progress()` service; no new calculation was introduced.

The existing Back to Annual Operational Plan link was retained even though the
reference omits it, because a regression test requires that navigation.

## Verification

- 45 focused Python cases passed across AOP commitments, Director AOP list and
  annual goals. The new page-state case covers no commitment, saved draft,
  submitted state and Director template isolation.
- 145 templates parsed, CSS build passed and `git diff --check` showed no
  whitespace error.
- Disposable Chromium check passed six groups: all statuses, draft banner,
  percentages, fixed campus, pluralisation, zero console errors, no horizontal
  overflow and 44px targets at 1440, 1024, 768, 390 and 320px. Evidence is
  ignored under the local temp directory used for the preview.
- A signed-in local preview was opened on port 5055 with synthetic data only.
- Current Web Interface Guidelines were fetched and applied: labels, accessible
  History link, `aria-hidden` icons, autocomplete off, visible focus, wrapping,
  and tabular numbers. Antislop was applied during work with real counts only.

## Limitations and rollback

The shell sidebar remains the existing PSU shell rather than the simplified
header in the reference. No physical-device, manual screen-reader, true
browser-zoom, full-suite or operational-database claim. The older
`scripts/qa_aop_commitments.py` still stops on a stale Director assertion
before this page, and an unrelated Overview-copy assertion in
`tests/test_ui_refinement_repairs.py` remains pre-existing and failing.

Rollback restores the four implementation files and removes the template and
this note, then rebuilds CSS. No data rollback is needed.
