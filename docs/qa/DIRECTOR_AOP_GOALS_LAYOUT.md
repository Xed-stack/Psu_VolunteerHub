# Director AOP Goals Layout

24 November 2026. Local work on `codex/ui-workflow-overhaul`, based on `983bb73`
with the earlier Coordinator overhaul preserved. The user subsequently authorized
committing and pushing both completed UI changes to `codex/ui-workflow-overhaul`
on origin and thesis. No deployment, dependency, schema migration or operational
database change.

## Approved Experience and Calculations

Director AOP Goals follows the supplied reference: Create Goal, year/campus
scope form, navy-headed annual summary, searchable deliverables table and
pagination. AOP History, filtered CSV/PDF and Saved Drafts remain accessible.
Goal titles open the existing details; Continue Draft and Create Goal retain the
existing publishing/revision workflow. Coordinator uses the original list.

Following the user's header correction, the five table headers match the
reference: Activity Title, Category, Campus Commitments, Director Baseline,
and Progress / Status. Dates remain beneath the activity title. Category shows
Not Assigned because the current goal model/form does not collect a category;
no activity category or strategic classification is inferred. Progress Status
remains the functional filter approved earlier instead of Strategic Thrust.
Search uses case-insensitive title/description substring matching, limited to
200 characters, through GET `q`. GET `progress_status` accepts empty/all,
`not_started`, `in_progress`, `met` and `above`. It deliberately avoids the
legacy `status` parameter, which continues to open historical records.

The summary uses the complete year/campus scope before search/status/pagination.
Director targets remain university baselines when a campus is selected;
completions and submitted quantities then come only from that campus. Remaining
work sums each goal's floored remainder. Example: 13/10 on one goal and 0/2 on
another leaves 2 remaining, not zero. Per-goal credit and eligibility use the
existing AOP service; one eligible event can contribute once to each linked goal.

The table shows goal title/authored description, dates, submitted campus
quantities, Director baseline and exact completed/target/percentage/status.
Percentages above 100% remain visible; only the decorative bar caps at 100%.
Native disclosures expose all row commitments and an aggregate campus breakdown.
Search/status apply before ten-row pagination and to the complete CSV/PDF export;
they do not change the annual summary. Scope/table forms reset pagination.
Selected-campus Director exports now explicitly use the displayed university
baseline; Coordinator export semantics remain unchanged.

## Design Read and Critique

Annual planning workspace for PSU Directors, using the supplied compact summary
and table composition. ENERGY 2 / RHYTHM 2 / MOTION 1. Existing Inter/system
typography, PSU navy #002b60, blue #00408b, white, slate and the shared gold
identity remain. Navy separates the annual summary from routine list controls;
no new assets, decorative icon system, fonts or animations were introduced.

High-priority critique addressed: commitments and completions are distinct;
goal dates remain visible; no official-directive/framework or attendance-based
verification claim is copied from the mockup. Status is explicit text alongside
decorative bars. Campus lists disclose fully instead of truncating authored names.
Rendered review refined column proportions, shortened the search placeholder,
and corrected singular campus/goal counts. Header follow-up restores the exact
reference labels, with a neutral Not Assigned category state and dates retained
under the activity title. Summary metrics stack into two
columns on tablets and one on phones; the table becomes labelled records below
768px with explicit table roles retained. Native forms work without JavaScript.
The inherited shared breadcrumb repeats AOP Goals; that existing navigation
presentation was not redesigned by this task.

## Verification

- `tests/test_director_aop_list.py` plus `tests/test_aop_commitments.py`:
  **30 passed** in 65.22s. Covers per-goal remaining work, all four progress
  states, scoped denominator, escaped authored titles, search before pagination,
  zero results, invalid status, unpaginated filtered CSV/PDF, legacy links and
  existing publication/commitment/revision behavior. An initial test fixture
  assumed one published goal and was corrected to support multi-goal data.
- Coordinator reference and Director achievement regressions: **16 passed**
  in 58.49s. Total: **46 distinct Python tests passed**.
- `scripts/qa_director_aop_list.py`: **13 browser groups passed** across
  1440/1280/1024/768/390/320px. Includes summary/ten rows, campus disclosures,
  44px controls, no page overflow, search/page reset/query retention, 130%,
  stable summary under no-results filters, selected campus baseline, all matching
  CSV/PDF rows, goal/create/draft/history/pagination destinations, keyboard focus,
  empty year, long goal/campus names, doubled root font and JavaScript disabled.
- **142 templates parsed**, CSS build and `git diff --check` passed.
- Contrast: light-blue summary text/deep navy **11.37:1**; progress blue/light
  track **8.09:1**. Existing native form/focus styles and semantic links reused.
- Actual prepared local preview was restarted using
  `.qa-overhaul-temp/run_existing_aop_preview.py`. Director and Coordinator
  `/annual-goals?year=2025` both returned **HTTP 200**, with the new Director
  template present only for the Director. Existing SQLite, secret, uploads and
  sessions reused without seeds/migration. This avoids stale Python/template
  mismatches from template-only reloads.

Evidence: ignored `.qa-overhaul-temp/director-aop-list/results.json`, six-width
screenshots and enlarged-text capture. Browser data is disposable synthetic
in-memory SQLite with CSRF enabled. Temporary browser server stops on completion;
the existing prepared local preview remains available at port 5000.

Limits: no full-suite, production MySQL, physical-device, manual-screen-reader,
performance benchmark or true browser-zoom claim. Root font enlargement checks
text reflow. Windows sandbox restrictions required isolated tests/browser pipes
to run outside the sandbox. No external services or operational data were used.

## Current Guidelines Audit

Fetched 24 November 2026 from
[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).

- `templates/goals/director_aop_index.html`: PASS; labelled native forms, GET
  state, native disclosures, explicit scoped headings, accessible table/records,
  escaped authored content, clear reset and meaningful empty states.
- `ui/app.css`: PASS; bounded responsive grids, visible focus inherited,
  tabular numeric data, long-content wrapping, no clipped table overflow.
- `app/routes/aop.py`: PASS; Director-specific filtering/exports; other roles and
  legacy URL handling retained; status input validated.
- `app/services/aop_presentation.py`: PASS; existing progress eligibility reused,
  stable campus grouping, per-goal remaining work and no invented metrics.

## Antislop Delivery Gate

- R-02 PASS: no em dash added to interface copy.
- R-03 PASS: six widths, mobile records, long names and enlarged text checked.
- R-17 PASS: summary/table values derive from published goals and eligible mappings.
- R-18 PASS: no testimonials or people added.
- R-23 PASS: approved reference/plan authorizes layout; no assets created.
- R-24 PASS: list, detail, creation, draft, history and pagination destinations exercised.
- R-25 PASS: measured palette ratios and existing visible focus styles retained.
- R-26 PASS: forms, reset, disclosures, exports and navigation exercised.
- R-27 PASS: empty year, no matches and invalid status checked; native request/error handling retained.
- R-28 PASS: no FAQ introduced.
- R-32 PASS: keyboard focus and Enter creation navigation verified; native disclosures retained.
- R-33 PASS: source edited directly; generated CSS built through existing npm script.
- R-34 PASS: no theme toggle introduced; existing light shell retained.
- R-35 PASS: isolated application, browser interactions and build completed.
- R-36 PASS: no invented security, compliance or performance claim.
- R-37 PASS: approved reference and design read established before building.
- R-38 PASS: synthetic fixtures confined to tests; production interface reads source data.
- R-39 PASS: native named controls, inherited hover/focus/pointer behavior; no new motion.
- R-40 PASS: no new media or blocking script, no unsourced performance claims.
- R-01 PASS: no new gradient/glow; navy summary header has a hierarchy purpose.
- R-04 PASS: no decorative icons introduced.
- R-06 PASS: established PSU typography and Newspaper Case labels retained.
- R-07 PASS: no background pattern introduced.
- R-08 PASS: no decorative arrows introduced.
- R-09 PASS: no generic badges or duplicate eyebrow labels.
- R-10 PASS: no glass or blur introduced.
- R-12 PASS: no new elevated card shadows.
- R-13 PASS: no glows introduced.
- R-14 PASS: four aligned metrics compare annual facts, not filler features.
- R-19 PASS: MOTION 1; no new animation.
- R-22 PASS: no generic illustration introduced.
- Liveliness PASS: explicit dials, navy focal summary, structural spacing and PSU identity.
- C-1 PASS: major choices follow the reference and existing tokens.
- C-2 PASS: displayed controls have verified real behavior.
- C-3 PASS: summary, retrieval, details and drafts serve goal-management tasks.
- C-4 PASS: responsive, empty, keyboard and no-JavaScript cases checked.
- C-5 PASS: no fictional interface claims.
- R-05 PASS: reference-led summary/table rather than unrelated template sections.
- R-11 PASS: existing input/card radii retained, no universal pill styling.
- R-15 PASS: Create Goal, Apply Scope, Apply Filters and Clear Table Filters name real actions.
- R-16 PASS: no promotional buzzwords introduced.
- R-20 PASS: dated PSU AOP goals/commitments determine the content.
- R-21 PASS: existing light shell retained; navy confined to summary hierarchy.
- R-29 PASS: existing PSU palette reused.
- R-30 PASS: no competing product style introduced.
- R-31 PASS: visual rationale documented above.

## Rollback and Skills

Restore only this task's AOP list route/service, Director list template and
CSS additions, then rebuild CSS. Remove this task's new tests/browser runner
if reverting. Preserve earlier Coordinator/Director Overview changes, drafts,
unrelated untracked documents/SQL/images and private previews. Restart the local
preview after restoring Python. No database rollback applies.

Skills used: UI/UX Pro Max, Frontend Design, Design Critique before/after,
Ponytail full, Antislop core/UI/Human/Layoutmobile during work, Search UX,
Web Design Guidelines and Webapp Testing.
