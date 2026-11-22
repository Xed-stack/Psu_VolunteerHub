# Director Finding Review Workflow — Local QA

Date: 22 November 2026. Branch: `codex/ui-workflow-overhaul`.

## Delivered Behavior

The Director Overview shows Active Reviews in a four-category donut card. The queue has Active and Reviewed views, scoped category/type filters and 25-item pagination. Review details support assessment, contextual follow-up, closure, manual reopening, previous evidence and paginated history. Completed occurrences are read-only for the campus Coordinator. The review workflow does not change source activity, attendance, annual evidence or target calculations.

Stable identity excludes participant/display filters. Full-event evidence determines material changes. GET requests do not persist state. Closed findings reappear when changed evidence still triggers them, while previous completed occurrences retain their snapshots. Saved open findings remain assessable after the generating condition clears. Deleted/transferred sources retain the original campus history without exposing the new campus source to a Coordinator.

## Verification

- 79 unique focused regression cases across `test_finding_reviews.py`, `test_director_overview_refinement.py`, `test_staff_overview.py`, `test_notifications_drafts_ui.py` and `test_proposal_record.py`: 78 passed in the combined run; the remaining test initially assumed pending registrations were excluded from existing reporting. Inspection confirmed they count toward registration/missing totals. Its expectation was corrected to cancelled registrations and the targeted check passed, preserving current reporting formulas. The final workflow-only rerun passed all 22 cases (85.43 seconds).
- Seven opt-in SQL integration cases passed against an isolated MariaDB 10.4.32 loopback server on port 13309. Both SQL-client and Python migration paths covered signed INT and BIGINT UNSIGNED parents, repeat application, source preservation, JSON writes and compare-and-swap versions. Missing parents, incomplete storage and missing unique identity were refused. The disposable server was shut down; operational MySQL/MariaDB was untouched.
- 20 browser groups passed with synthetic SQLite data and CSRF enabled. Widths: 1440, 1024, 768, 390 and 320px. Checked card/detail layout, exact counts, validation/focus, saving, closure, completed print output, own-campus access, foreign-campus denial, material changes, previous assessment, 200% text, follow-up, no-JavaScript native save, blocked Plotly and zero results. No browser page errors.
- Reviewed history and detail history database pagination tested beyond 25 entries. Active aggregation tested beyond 25 activities with no per-finding query growth. Schema readiness is cached only within a request; review state is not cached across requests.
- CSS build (`npm run build`), changed JavaScript syntax, template parsing through the browser fixture, changed Python syntax and whitespace checks passed. The registered migration CLI dry run planned two tables and left the isolated schema unchanged. An initial `build:css` invocation was corrected to the repository's existing `build` script; no dependencies were installed.

Browser runner: `scripts/qa_finding_reviews.py`. Evidence is local and ignored under `.qa-overhaul-temp/finding-reviews/`: `results.json`, `card-*.png`, `detail-*.png`, `detail-text200.png` and `completed-print.png`.

## Design Critique and Audit

UI/UX Pro Max directed navigation, role access, states and mobile reading order; Frontend Design retained PSU blue, restrained gold, Inter and existing surfaces (Energy 2, Rhythm 2, Motion 1). Ponytail full reused report generation, scope controls, native forms/disclosures, existing Plotly and shared layout. Antislop core/UI/Human/Layoutmobile applied during implementation.

Preimplementation critique prioritized the missing review end state and misleading corrective action for locked historical attendance. The selected design separates assessment from actionable follow-up without introducing a competing visual style. Rendered critique corrected the detail page's generic header, planning evidence destination and reopening field wording. Counts and category text remain usable without the chart. Mobile panels stack, controls retain 44px targets, long content wraps, validation receives focus and entered text survives errors/conflicts. Assessment/history content preserves paragraph whitespace.

The current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) were fetched for the final audit. Changed review templates, chart/dirty-guard scripts and scoped CSS were reviewed for semantic controls, labels, visible focus, keyboard operation, empty/error states, reduced motion, URL-based filters/history, unsaved changes and mobile overflow. No unresolved high/moderate defect was identified in the reviewed scope. Extra animation and alternate chart decoration remain optional preferences.

## Rollout, Limitations and Rollback

`FINDING_REVIEWS_ENABLED` defaults to false. The existing findings UI remains until explicit review-table migration and enablement. See `docs/operations/FINDING_REVIEW_WORKFLOW.md`. Missing/incomplete storage also falls back to generated findings instead of presenting nonfunctional review actions.

The repository has volunteer/coordinator/director roles; administration is merged into Director. This implementation preserves that model rather than inventing a separate read-only Admin role. Coordinators can read only their campus's completed occurrences.

No full-suite, production/load test, operational migration, MySQL 8, physical-device, true browser-zoom or manual screen-reader verification is claimed. Enlarged text is a 200% root-font-size browser check. The source document remains unchanged. Unrelated SQL catalogue/proposal work, DOCX, output/tmp and deferred audit findings remain intact. No commit, push, deployment or dependency change occurred.

Rollback: disable the flag and restart, retaining review storage/history. Revert only this workflow's implementation, generated CSS, tests and notes if code rollback is required. Do not delete historical decisions or unrelated working files.
