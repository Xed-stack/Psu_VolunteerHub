# Director AOP Goals Typography — 24 November 2026

## Scope and direction

Local work on `codex/ui-workflow-overhaul`. No commit, push, deployment,
migration, dependency, permission, calculation or data change. Unrelated
working files, including the concurrent HANDOFF.md live-activation entry and
all untracked SQL proposals, documents, review JPGs, older QA notes, output and
tmp, remain intact.

The Director AOP Goals desktop page now uses the same type scale as Needs
Attention, Overview and Reports. The composition, PSU navy/gold/white palette,
summary figures, labels, scope behaviour, saved drafts and the earlier approved
removal of the desktop deliverables table are unchanged. Energy 2 / Rhythm 2 /
Motion 1. No new colour, icon, animation or competing visual style.

## Design critique before implementation

- High, defect: supporting text, metric captions and campus tile labels were
  11px to 13px, below the 14px small-text and 16px body convention used by
  other workspace pages.
- Moderate, defect: the summary header was 16px and its description 12px, so
  the official evidence panel read like a footnote.
- Moderate, defect: at 1024px campus tiles kept narrow 12px labels. Larger
  type needed room to wrap without overflow.
- Low, deliberate: the empty space below the summary comes from the approved
  removal of the desktop deliverables table. Reintroducing it was out of scope.

## Changes

Only `ui/app.css` lines 1507-1549 and the rebuilt `static/styles/app.css`
changed. Desktop values: context and year chips 14px, heading description 16px,
scope labels 14px, inputs and selects 15px, scope caption 14px, summary header
18px with a 14px description, directive and active-scope chips 13px, metric
labels and captions 14px, status badges 13px, campus note and disclosure 14px,
campus tiles 14px with 13px sublabels. Metric figures stay 36px. The summary
header can wrap, and campus tiles use a 6.5rem minimum width with a 44px-plus
label area so longer campus names stay contained.

## Verification

- Browser runner `scripts/qa_aop_goals_typography.py` passed 4 checks with zero
  console errors: 1440, 1280 and 1024px, computed font-size floors for ten
  selectors, no horizontal overflow, contained campus tiles, the hidden
  deliverables table retained, and 200% root-font text. Evidence:
  `.qa-overhaul-temp/aop-goals-typography/`.
- Rendered review at 1440 and 1024px found no in-scope defects. At 1024px the
  summary chip and some metric captions wrap to a second line, which is the
  intended reflow.
- Web Interface Guidelines were fetched from
  `vercel-labs/web-interface-guidelines` on 24 November 2026 and applied to the
  changed CSS: clear heading hierarchy, tabular figures, wrapped content, no
  clipping, native focus and 44px targets. Antislop delivery gate passed:
  real counts, retained PSU identity, no new decoration. Contrast was
  recomputed for affected pairings: gold on navy text 9.35:1 and white on navy
  16.15:1. CSS build passed.

## Limitations and rollback

Narrow and mobile layouts are unchanged. The deliverables table remains hidden
from 1024px. Five-metric density and current page length are retained. No
physical-device, manual screen-reader, true browser-zoom, full-suite or
operational-database claim. Rollback restores the two CSS files and removes the
runner and this note; no database rollback is needed.

## Publication, 24 November 2026

The user authorized committing this task's source and generated CSS, browser
runner and QA note to both `origin/codex/ui-workflow-overhaul` and
`thesis/codex/ui-workflow-overhaul`. Both remote heads were verified at
`0af06d7` before publication. The concurrent HANDOFF.md live-activation entry
and all other untracked SQL proposals, documents, review JPGs, older QA notes,
output and tmp remain local and uncommitted. This publication does not
authorize deployment, migration, operational database changes or dependency
changes.
