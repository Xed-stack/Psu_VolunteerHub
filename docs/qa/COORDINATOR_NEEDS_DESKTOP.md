# Coordinator Needs Attention Desktop Queue — 24 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No commit, push, deployment,
migration, dependency, permission or calculation change. Unrelated untracked
SQL, documents, review JPGs, output/tmp and preview data remain intact.

Coordinator Needs Attention now uses the Director queue's institutional desktop
composition from 1024px, adapted to a campus read-only role: pending count and
Campus Coordinator label, existing scope controls, two view links with counts,
category chips with live counts, a campus-evidence note, a result toolbar,
single-column findings with expandable evidence and text status labels, and
five-row pagination. Below 1024px both Coordinator presentations retain their
previous narrow layout. Director, admin, Coordinator Overview and Reports are
unchanged. Energy 2 / Rhythm 2 / Motion 1; no new palette, icon set or motion.

Purposes: gold marks the current view for orientation, navy marks the one next
action per row, amber marks findings that need attention, and white row panels
separate evidence for scanability. Every count and label comes from existing
data.

## Design critique

Before implementation:

- High, defect: the narrow tile labelled Reviewed rendered `phases.annual`
  (annual-plan findings). Relabelled Annual Plans.
- High, defect: both narrow phase segments linked to `#past-findings`, which
  does not exist. The dead segment section was removed; the accurate summary
  tiles remain.
- Moderate, defect: no desktop composition for Coordinator findings. Resolved
  by reusing the Director `.needs-*` structure and CSS.
- Moderate, defect: Reviewed Recommendations used 25 rows and no category
  counts. Aligned to five rows and existing category counts.
- Low, deliberate: no bulk controls, CSV export or sort control for
  Coordinators. Those would need new endpoints or parameters; Reports exports
  and the existing canonical finding order remain.

Rendered review found no in-scope defects. The fixed mobile sidebar in the
shell overlaps content in full-page screenshots at 390px; this is pre-existing
shell behavior and unchanged by this task. The reviewed view shows a count on
the active tab but not on the generated tab; adding it would require another
COUNT query and is intentionally left as a minor difference.

## Typography pass, 24 November 2026

The shared desktop block was below the app's type scale. High-priority critique:
the page `h1` was 26px against a 30px to 36px baseline, and finding titles were
14px against 20px headings elsewhere. Moderate critique: body copy, counts and
status labels were 11px to 14px, and the 12px action button looked undersized
inside its 44px hit box.

The fix changes only `font-size` values and small spacing allowances inside the
existing 1024px needs block, so Director and Coordinator stay aligned: `h1` 32px,
finding titles 18px, meta and evidence 14px, chips 14px with 13px counts, scope
inputs and action buttons 15px, toolbar count 16px, and status badges 13px.
The row action column moved from `min(16rem,40%)` to `min(18rem,42%)` so larger
labels wrap instead of crowding the evidence. No colour, route, template or
motion changed. At 1024px the chips and policy label wrap, the evidence summary
truncates with an ellipsis and expands natively, and there is no horizontal
overflow.

## Verification

- 4 new focused Python cases cover the generated desktop composition, category
  links and counts, the reviewed read-only five-row queue, and the unchanged
  Director queue. The corrected runs passed after test expectations were
  aligned with seeded fixture data.
- 60 focused cases passed across the new file and
  `test_finding_reviews.py`, `test_attention_attendance_refinements.py` and
  `test_director_overview_refinement.py` (overlapping earlier runs included).
- Browser runner `scripts/qa_coordinator_needs_desktop.py` passed 12 checks with
  zero console errors: generated queue at 1440/1280/1024/768/390/320px,
  desktop/narrow switch at 1024px, no horizontal overflow, computed type-scale
  floors for both roles, keyboard focus and Enter activation of a category
  chip, evidence disclosure, 200% root-font text, reviewed queue at 1440/390px,
  and the Director queue regression.
  Evidence: `.qa-overhaul-temp/coordinator-needs-desktop/`.
- All templates parsed, CSS build passed, changed Python compiled, and the
  generated CSS contains the new selectors.

Web Interface Guidelines were fetched from
`vercel-labs/web-interface-guidelines` on 24 November 2026 and applied to the
changed templates and CSS: native links/buttons/details, labels in existing
scope controls, visible focus, no `outline: none`, state in the URL, wrapped
long content and 44px targets. Antislop delivery gate passed: real counts,
no dead controls, no invented numbers, retained PSU identity. New colour
pairings were computed with the contrast checker: `#713f12` on `#fffbeb` is
8.36:1 and `#475569` on white is 7.58:1.

`tests/test_dashboard_followups.py` has 18 pre-existing failures at HEAD:
`/coordinator_dash` and `/director_dash` are legacy redirects to
`/workspace/overview` in `app/routes/coordinator.py:242` and
`app/routes/director.py:193`, so those stale assertions never see the expected
dashboard markup. No file in that path was changed by this task.

## Local delivery and rollback

The prepared port-5000 preview needs a Python restart after route changes;
template-only reload does not load changed Python code. No operational
database, deployment or skill installation was performed. Design Critique and
Webapp Testing are not installed in this session; their roles were performed as
structured review passes and browser verification. No physical-device, manual
screen-reader, true browser-zoom, full-suite or operational-MySQL claim.

Rollback restores `templates/workspace/follow_up.html`, removes
`templates/workspace/coordinator_review_queue.html`, reverts the two route
additions, the help sentence, `ui/app.css` and the generated CSS, and removes
this task's tests, runner and QA note. No database rollback is required.

## Publication, 24 November 2026

The user authorized committing this task's template, new Coordinator queue
template, two route additions, help sentence, source and generated CSS, focused
tests, browser runner and QA note to both `origin/codex/ui-workflow-overhaul`
and `thesis/codex/ui-workflow-overhaul`. Both remote heads were verified at
`c49c150` before publication. The unrelated concurrent HANDOFF.md
live-activation entry and all other untracked SQL proposals, documents, review
JPGs, older QA notes, output and tmp remain local and uncommitted. This
publication does not authorize deployment, migration, operational database
changes or dependency changes.
