# Overview, Partner Agencies, and Date Pickers

Date: 23 November 2026. Branch: `codex/ui-workflow-overhaul`. Local, uncommitted implementation.

## Delivered Behavior

The Director Needs Attention card follows the supplied reference composition: amber outline/header treatment and warning symbol, a donut with a bold actual total, matching category markers, exact counts, and accessible Review actions. Existing category definitions are retained instead of copying the illustration's labels or example numbers. Persisted reviews retain Active Reviews, follow-up totals, queue and history. Disabled/unavailable review storage uses grouped generated Findings with the correct scope explanation, no review-table reads/writes and no feature activation. Coordinator Overview retains its original task layout. The dashboard guide distinguishes the two states using an explicit persisted-review marker.

Activity hour/minute suggestions now occupy space inside their time-control unit rather than extending beyond the scrollable dialog. Suggestions scroll independently; Confirm/Cancel remain reachable through dialog scrolling. Numeric typing, keyboard selection, AM/PM, PHT, future-start/end validation and draft restoration remain. Arrow targets are 44px; narrow layouts place AM/PM beneath hour/minute controls.

Create Activity retains one Primary Agency and its Signed MOA. Additional Partner Agencies uses the existing searchable checkbox panel, with no Ctrl/Command requirement. The primary agency is excluded dynamically and server-side; other choices survive saving, refresh and partner detours. Existing stage/publication validation checks campus ownership. Autosave rejects foreign agencies without replacing the prior draft. Invalid ordinary submissions retain selections for correction. No External Partner clears the optional list; unchanged legacy drafts require no conversion.

The additive `additional_agency_ids` string array lives in existing proposal JSON, with structural validation, canonical IDs and deduplication. Publication retains IDs and a frozen name list in its existing snapshot. Later agency renames do not rewrite that published list. Expected Partner Participants and the selected MOA still apply to the primary agency only; no attendance, target or MOA-coverage calculation is broadened.

Add MOA uses the same formatted date-button/dialog styles as activity creation, with a native date field and Cancel/Confirm. It intentionally has no hour/minute/AM-PM fields, as confirmed by the user. `valid_from`/`valid_until` names, ISO date submissions, date-only storage, inclusive applicability, historical agreements and equal boundaries are preserved. Native date inputs remain available without JavaScript. Drafts restore the formatted displays and saved attachments.

## Verification and Evidence

- Final refinement/Overview/review/staff regression run: **56 passed** in 191.24 seconds.
- Clean existing proposal/posting/partner compatibility run: **57 passed** in 193.84 seconds. The two final runs cover **113 distinct Python cases**; combined collection confirmed that total.
- New browser runner `scripts/qa_overview_partner_pickers.py`: **30 groups passed**, no browser page errors. Covered both card modes at 1440/1024/768/390/320px, unclipped hour/minute options at six viewport sizes including 438x344, 44px arrows, multiple selections, save/refresh/detour/review, historical same-day MOAs, date/upload draft restoration, native no-JavaScript saving, zero reviews and blocked-Plotly text fallbacks.
- Final browser rerun also asserts focus returns to the originating date button after cancelling either picker. Both scripts explicitly restore that focus on native dialog close, including Escape.
- Existing activity-creation runner `scripts/qa_posting_essentials.py`: **29 groups passed**, including proposal capture, dates, drafts, publication and responsive checks.
- Updated existing `scripts/qa_staff_overview.py`: **32 checks passed**, including Director/Coordinator responsive layouts, enlarged text, keyboard guide/navigation, category scope/clearing, empty states, print and unaffected Volunteer pages. Old individual-type expectations were replaced with the approved category-card behavior.
- CSS build, all-template parsing during preview startup, changed Python AST checks, JavaScript syntax checks and whitespace checks passed.
- Contrast checker: amber warning foreground `#b45309` on `#fef3c7` is **4.51:1**. Existing PSU blue/white is **9.97:1**, slate-500/white **4.76:1**. Category marker colors repeat the existing chart palette; labelled exact values provide the independent non-color interpretation.

All previews use `create_app('testing')`, synthetic fixtures, in-memory SQLite and enabled CSRF. Temporary uploads are under the dedicated QA output folders; servers shut down on completion. Test execution outside the sandbox was required for Windows temporary-directory/browser process permissions. No operational database or account was used.

Evidence: `.qa-overhaul-temp/overview-partner-pickers/results.json` and its `card-*`, `time-picker-*`, `partners-*`, `moa-*` captures; `.qa-overhaul-temp/posting-essentials/`; `.qa-overhaul-temp/staff-overview/`. These local evidence folders are ignored.

An older `qa_partners.py` run stopped on its pre-existing text-input assumption for Participant Type, which is now a select in the application. That runner was not rewritten as part of this task. Current partner/date/draft flows were exercised by the new browser runner and focused HTTP regressions instead. An initial combined regression run passed 80 cases before reaching an outdated individual-type Overview assertion; its category navigation assertions were updated and passed in the final refinement run.

## Design Critique and Guidelines Audit

UI/UX Pro Max guided the tasks, interactions and responsive behavior. Frontend Design retained PSU blue/deep blue/gold, Inter, established surfaces and spacing. Design read: university operational screens for Directors and Coordinators, Energy 2 / Rhythm 2 / Motion 1. Ponytail full reused Plotly, choice panels, native dialogs/date fields, draft events, existing JSON snapshots and validation infrastructure. Antislop core/UI/Human/Layoutmobile applied during work.

Preimplementation critique prioritized clipped time lists, undersized arrows and the single-agency data path as moderate issues. Reference-card composition and MOA presentation inconsistency were minor. Rendered critique fixed the agency panel's intrinsic-width/legend overflow, made filter buttons wrap, excluded the primary agency from selection counts and tightened donut-center typography. Responsive test loops now wait for viewport settling instead of treating transient resize frames as final layout defects. Existing guide copy was corrected so the new fallback card does not imply persisted reviews.

Fetched the current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) and reviewed changed templates/scripts/CSS for semantics, labels, focus, keyboard operation, error/empty states, long text, URL scope, draft preservation, no-JavaScript behavior and responsive containment. New fixed labels use Newspaper Case; explanations use sentence case. No remaining critical/moderate defect was identified in the changed UI under the verified browser scenarios. Extra decoration and changing category meanings were deliberately excluded.

## Antislop Delivery Gate

### Hard Gate

- R-02 PASS: new interface copy has no em dashes; authored proposal content is retained.
- R-03 PASS: new and existing browser runners verify narrow layouts, short dialogs and enlarged text without persistent page overflow.
- R-17 PASS: totals and category counts derive from existing records; the reference's example numbers are not copied.
- R-18 PASS: no testimonials or fictional production people are added.
- R-23 PASS: existing assets/navigation remain; the requested warning symbol is a dimensioned inline SVG with a clear attention purpose.
- R-24 PASS: category, queue, history and partner links use existing routes and were exercised.
- R-25 PASS: changed text/control tokens reuse verified contrast pairs; colored chart markers have labelled exact-value equivalents.
- R-26 PASS: filters, agency checkboxes, primary selection, date/time lists, Confirm/Cancel and native saves have tested behavior.
- R-27 PASS: zero reviews, chart failure, unavailable selections, validation errors, saved/restored drafts and native loading behavior remain explicit.
- R-28 PASS: no FAQ is added.
- R-32 PASS: native dialogs, labelled controls, 44px arrows, keyboard suggestion handling and existing Overview keyboard/focus checks passed.
- R-33 PASS: UI changes were authored directly with apply_patch; no external source-rewriting script was used.
- R-34 PASS: existing PSU theme is retained; no toggle is added or changed.
- R-35 PASS: build and recorded synthetic browser interactions passed.
- R-36 PASS: no invented performance/security/compliance/customer claim is introduced.
- R-37 PASS: reference composition, PSU direction and explicit dials preceded implementation.
- R-38 PASS: product content uses real application records; synthetic content stays in disposable QA apps.
- R-39 PASS: native labels/buttons/checkboxes/dialogs retain names, focus and state; warning/chart visuals do not replace text meaning.
- R-40 PASS: warning SVG has dimensions; no new remote media or third-party script is added, and no performance measurement is invented.

### Purpose Gate

- R-01 PASS: amber tint identifies the Needs Attention header; no decorative gradient/glow is added.
- R-04 PASS: the warning symbol communicates attention, and category dots map directly to the existing chart.
- R-06 PASS: existing Inter hierarchy is retained for operational consistency; no monospace or wide-tracked uppercase treatment is added.
- R-07 PASS: no background grid/pattern is added.
- R-08 PASS: no decorative action arrow pattern is added.
- R-09 PASS: no decorative badge or duplicated headline label is added.
- R-10 PASS: no glass effect is added.
- R-12 PASS: card surfaces retain their established treatment; date-only dialogs reuse existing modal elevation.
- R-13 PASS: no glow is added.
- R-14 PASS: four uniform category rows intentionally support comparing real counts/actions.
- R-19 PASS: Motion 1 is retained; no new animation is added.
- R-22 PASS: no decorative illustration is added.

### Liveliness

- Dials PASS: Energy 2 / Rhythm 2 / Motion 1 remain explicit and consistent with the PSU workspace.
- Consistency PASS: rendered results retain existing color/type/surface decisions and the requested composition.
- Focal point PASS: the attention total and category actions lead the card; selection and date fields lead their forms.
- Whitespace PASS: header, chart/list separator and row spacing structure the card; picker lists occupy deliberate layout space.
- Accent PASS: amber marks attention, while PSU blue marks existing actions and focus.
- Identity PASS: PSU branding, campus scope and established typography remain.
- Design Read PASS: audience, task, reference and dials were set in the approved plan.

### Craftsmanship and Quality Locks

- C-1 PASS: each change addresses the reference, clipping, multiple selection or date uniformity.
- C-2 PASS: changed controls have native behavior and browser/backend coverage.
- C-3 PASS: no filler section is added; additional agencies are part of the existing partnership task.
- C-4 PASS: responsive, short-height, enlarged-text, keyboard, no-JavaScript, blocked-chart, empty and draft scenarios passed within the recorded scope.
- C-5 PASS: no fabricated production statistic/testimonial is introduced.
- R-05 PASS: existing operational card/form structures are refined rather than replaced by a generic template.
- R-11 PASS: existing radius hierarchy is retained.
- R-15 PASS: Review, Confirm, Cancel and existing save labels describe the available task.
- R-16 PASS: changed copy contains no marketing buzzwords.
- R-20 PASS: campus context, real findings, PSU colors and operational forms retain product identity.
- R-21 PASS: the existing institutional theme is retained; no unrelated theme work is added.
- R-29 PASS: PSU blue/deep blue, attention gold/amber and neutrals are reused; data markers have a defined chart purpose.
- R-30 PASS: the supplied reference informs the requested card; no competing product style is introduced.
- R-31 PASS: amber signals attention; blue signals actions; the donut/list enables count comparison; existing Inter/spacing preserve consistency; shared dialog styling makes dates uniform; searchable checkboxes enable native multi-selection.

## Limits and Rollback

### Running Preview Repair, 23 November 2026

The user's port-5000 preview was running `.qa-overhaul-temp/run_finding_review_preview.py` with `debug=False` and `use_reloader=False`. It retained an older compiled Add MOA template even though the static script endpoint served the latest workspace file. Browser refresh alone did not repair the server-side template cache. The confirmed preview processes were restarted using the same launcher, SQLite file and private upload folder, with `TEMPLATES_AUTO_RELOAD=True` and Jinja auto-reload enabled. No reset or operational database was used. The launcher's existing random session key rotates on restart, so existing preview browsers need to sign in again.

Verified the actual `http://127.0.0.1:5000/workspace/partners/3/agreements/new` through a legitimate preview Coordinator sign-in in headless Chromium. The native source field is hidden, the date button opens Choose Valid From Date with exactly one date input and Cancel/Confirm, and no JavaScript errors occurred. No agreement was submitted. Actual-instance evidence: `.qa-overhaul-temp/running-moa-dialog.png`; local verification script: `.qa-overhaul-temp/check_running_moa.py`.

Hour/minute toggle buttons now use centered, dimensioned SVG chevrons styled like the native AM/PM caret instead of the tiny text glyph. The isolated 30-group browser runner passed again, including SVG-arrow assertions and MOA dialog captures. The running preview loads the current Python code and templates after restart; future Python-code changes still require a restart because process reloading remains off.

No full-suite, operational MySQL, physical-device, Safari/Firefox, manual screen-reader or true browser-zoom claim. Enlarged-text tests change root font size. Additional partner agencies do not have independently selected MOAs or participant estimates; the user explicitly chose the primary-plus-others model. MOA validity remains date-only.

No commit, push, deployment, dependency installation, migration, operational-data update or review-feature activation. Prior attendance/queue refinements and unrelated SQL, DOCX, JPG, output/tmp work remain intact. Presentation rollback can restore the previous card/form UI while retaining the additive JSON parser compatibility so drafts with `additional_agency_ids` still open. Do not delete selections, attachments, publication snapshots or review history. No database rollback is needed.
