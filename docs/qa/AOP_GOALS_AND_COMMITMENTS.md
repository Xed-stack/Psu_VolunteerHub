# AOP Goals and Campus Commitments QA

## Design Direction and Critique

PSU Directors and campus Coordinators use this workspace to set goals, commit to
work, and see completion. Preserve the existing Inter typography, PSU blue
`#00408b`, deep blue `#002b60`, gold `#f4bd27`, ink `#111c2c`, and white surfaces.
Energy 2 / Rhythm 2 / Motion 1. Left-aligned goal periods and paired count labels
serve comparison; no decorative chart, animation, or competing visual system.

Before implementation, the main defects were independent campus proposals without
a parent goal, attendance-gated credit, unclear commitment/achievement separation,
and year-only scope. The approved design resolves them through parent goals,
immediate submissions, separate metrics, and one full-schedule eligibility rule.

Rendered critique found and repaired:

- Moderate: the shell retained “Annual Plans” while navigation said “AOP Goals.”
  Updated the shell title and historical title.
- Moderate: Coordinator details repeated campus metrics in two sections. Keep
  “Your Campus” and reserve the campus comparison section for university readers.
- Moderate: date buttons exposed a field label without the selected value to
  assistive technology. Include the label, required state, and selected value in
  the accessible name; retain native date inputs without JavaScript.
- Minor: raw schedule timestamps made linked activities harder to scan. Use
  labelled dates/times with explicit Philippine time.

No remaining in-scope visual defect was observed. A different card composition or
new visualization would be an optional preference, outside this change.

## Verification

Use `.venv/Scripts/python.exe`. Windows sandbox ACL/process restrictions required
pytest temporary directories and Chromium execution outside the sandbox. All data
was synthetic, in-memory/disposable SQLite; no existing running database was changed.

- Annual/workflow/history/migration/campus/report/presentation regression group:
  96 passed, 1 skipped (operational MySQL integration).
- Activity posting, existing partner/date refinements, and attendance regression
  group: 54 existing/negative cases passed on its initial run; the new positive
  publication fixture correctly failed because its future activity was outside its
  August goal period. Corrected the fixture to a December end date and reran the
  AOP/posting group: all 37 cases passed.
- Final AOP transactional/privacy/archive rerun: 19 passed, including explicit
  rollback after notification storage failure. Added a subsequent older-filter
  compatibility test and reran it with the posting cases: 37 passed (20 AOP + 17 posting).
- `scripts/qa_aop_commitments.py`: 17 browser groups passed, including real
  CSRF-protected publication, immediate over-target commitment, activity linking,
  period impact confirmation, and retained ineligible links.
- `scripts/qa_overview_partner_pickers.py`: 30 existing browser groups passed,
  protecting shared MOA/activity pickers, native fallbacks, partner selection,
  saved drafts, and the existing Overview reference card.
- Browser widths: 1440, 1024, 768, 390, and 320px. Checked Director/Coordinator
  lists, details, forms, activity linking and activity creation, page overflow,
  empty states, keyboard focus, enlarged text, JavaScript errors, and no-JavaScript
  date controls. New AOP links, buttons, disclosure controls and checkbox labels were checked for at least 44px targets. Native disclosure markers are retained. Temporary preview servers shut down after checks.
- Added retirement compatibility coverage for explicitly shared aggregate and
  unique-person evidence. Historical AOP reads its retained archive context without
  copying retired targets/results into AOP or affecting new progress. Final AOP/history/migration run: 35 passed (22 AOP + 11 historical + 2 schema tests); the two shared-evidence cases also passed after the final query cleanup.
- Four focused unsaved-change state checks passed: temporary picker input does not mark a form dirty, named input does, blocked submission retains the warning, and successful submission clears it.
- CSS build, changed JavaScript syntax, Python compilation, all-template parsing,
  and `git diff --check` passed.

Screenshots/results are ignored local evidence under
`.qa-overhaul-temp/aop-commitments/` and
`.qa-overhaul-temp/overview-partner-pickers/`. No private database or screenshot
containing operational data is included in source.

## Web Interface Guidelines and Antislop Gate

Fetched the current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
and audited the changed templates, shared picker, form warning script, and CSS.
Native labels/buttons/forms, live error feedback, focus return, visible focus,
44px checkbox/button targets, explicit draft saving, unsaved-navigation warnings,
wrapping/reflow, tabular numbers, and empty states are retained. Shared date
controls constrain new AOP dates to their selected year and retain server validation.
No new external script, dependency, animation, or unsized media was added.

Antislop was applied during work (session choice). PSU identity and original
authored records are preserved; actual records drive every displayed count.
Implementation uses the existing annual models and UI controls, with no invented
metrics or filler content. Draft privacy and field ownership were checked alongside
presentation because unpublished content must not become visible through history.

## Limits

No full-suite, operational database/MySQL migration, physical mobile device,
manual screen-reader, true browser zoom, or live multi-process concurrency claim.
Enlarged-text checks used a larger root font. The existing local database and its
running preview were not migrated/restarted into this workflow. See the operations
guide for the reviewed migration and rollback requirements.

Skills used: UI/UX Pro Max, Frontend Design, Design Critique before/after,
Ponytail full, Antislop core/UI/Human/Layoutmobile during work, Web Design Guidelines,
and Webapp Testing.
