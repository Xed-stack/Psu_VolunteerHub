# Restored AOP Goals Desktop Reference

Implemented locally on 24 November 2026 on `codex/ui-workflow-overhaul`.

Subsequent user correction removes the pictured deliverables table, search/status
filters, pagination and AOP Records links from the Director desktop presentation.
One desktop CSS rule removes those sections from display and keyboard navigation.
The summary, campus tiles, Create Goal and saved drafts remain available. Browser
verification passed at 1440, 1280 and 1024px with no horizontal overflow. CSS build
and whitespace checks passed. Existing narrow-width presentation is retained.
The earlier populated-table browser results below are historical verification.

## Result and Design Critique

AOP Goals is visible and selected throughout goal management. Reports keeps its
own navigation destination and management link. The Director desktop page follows
the supplied reference with a compact context bar, heading and Create Goal action,
year/campus scope panel, annual date caption, navy summary, four measures, native
campus breakdown and official campus tiles. The existing goal table and drafts
continue below the summary. The PSU seal and typography are retained.

Design read is an institutional annual-planning workspace for PSU Directors.
Energy 2 / Rhythm 2 / Motion 1. Navy anchors the official summary, gold marks the
directive, and restrained green/blue figures distinguish contributions and
commitments. Borders divide measures and campus entries. Motion is limited to
existing interaction feedback. The new presentation is scoped to desktop from
1024px. Additional elements are hidden below that width.

High-priority findings addressed include restoring management discoverability,
uncapped achievement, per-goal remaining work, and truthful campus submission
states. Moderate findings addressed include top-of-page density, consistent
scope context, and legible wrapping campus tiles. The existing native disclosure
continues to expose submitted campus details. Selected-campus tiles, totals and
goal rows use the same scope. An unset plan lifecycle is represented by the year
context, with no invented active state.

## Verification

- 33 focused Python tests passed in 76.64 seconds, including the new all-campus,
  selected-campus, 130% achievement, remaining-work and empty-year checks.
- The existing Director AOP browser runner passed 13 groups and parsed all 142
  templates. It covers filters, pagination, exports, creation, draft destinations,
  native breakdown, long content, enlarged text and JavaScript fallback.
- Prepared-preview checks passed for Director and Coordinator at 1440, 1280 and
  1024px. Verified restored sidebar entry, active goal navigation, scope continuity,
  Director context bar and selected-campus tile, no horizontal overflow, CSV/PDF/
  Excel responses, empty year and navigation with JavaScript disabled.
- CSS build, JavaScript syntax and whitespace checks passed. The isolated preview
  was restarted using its existing database launcher and returned HTTP 200.
- New green text on white is 5.48:1. White scope text on muted navy is 9.35:1.
  Existing PSU pairings retain their previously verified contrast.

Current Web Design Guidelines were fetched on 24 November 2026. Changed files
were reviewed for semantic navigation, labels, heading hierarchy, native form
behavior, visible focus, content wrapping and numeric alignment. Rendered review
of the populated page confirmed hierarchy and preserved table headers. Evidence
is under `.qa-overhaul-temp/director-aop-list/` and
`.qa-overhaul-temp/aop-restored-reference/`.

## Antislop Delivery Gate

- R-01 PASS. The navy gradient distinguishes the summary header within PSU branding.
- R-02 PASS. New interface copy uses ordinary punctuation.
- R-03 PASS. Desktop widths have no overflow and existing narrow regression checks pass.
- R-04 PASS. The plus sign identifies goal creation and is hidden from assistive text.
- R-05 PASS. Composition follows scope, annual results, campus obligations and goal actions.
- R-06 PASS. Existing PSU typography and legible numeric hierarchy are retained.
- R-07 PASS. Surfaces have no decorative background patterns.
- R-08 PASS. Links use explicit action text.
- R-09 PASS. Badges communicate year, scope, achievement or a real directive label.
- R-10 PASS. Surfaces are opaque.
- R-11 PASS. Radii follow existing PSU controls and panels.
- R-12 PASS. Existing restrained elevation is retained.
- R-13 PASS. The page uses flat emphasis without glow.
- R-14 PASS. Summary measures and campus tiles serve distinct comparison tasks.
- R-15 PASS. Actions name creation, scope application and campus details.
- R-16 PASS. New copy describes the existing annual-planning workflow.
- R-17 PASS. Existing annual services supply every count and percentage.
- R-18 PASS. Content contains no testimonials.
- R-19 PASS. Existing interaction feedback matches Motion 1.
- R-20 PASS. PSU branding and the approved institutional reference drive the layout.
- R-21 PASS. The established PSU workspace theme is retained.
- R-22 PASS. The official existing seal is retained.
- R-23 PASS. The user approved the navigation and layout reference.
- R-24 PASS. Restored sidebar and campus links reach existing routes.
- R-25 PASS. New color pairs and established PSU pairs meet AA text contrast.
- R-26 PASS. Browser checks exercise goal actions, scope, exports and disclosures.
- R-27 PASS. Existing empty states, errors and form loading feedback remain available.
- R-28 PASS. The workspace contains no FAQ.
- R-29 PASS. PSU navy and gold lead with limited semantic data colors.
- R-30 PASS. The supplied reference and PSU identity guide the composition.
- R-31 PASS. The design reasons are recorded above.
- R-32 PASS. Native links/forms/disclosures retain keyboard and focus behavior.
- R-33 PASS. Source changes were made directly using apply_patch.
- R-34 PASS. Existing theme behavior is retained.
- R-35 PASS. Build, Python tests, browser checks and rendered review completed.
- R-36 PASS. Claims are limited to existing workflow and recorded verification.
- R-37 PASS. Approved direction and design dials preceded implementation.
- R-38 PASS. Counts are derived from actual data, with explicit submission states.
- C-1 through C-5 PASS. Purposeful styling, working controls, task-led content,
  tested desktop resilience and sourced figures are evidenced above.

Full-suite, physical-device and manual screen-reader checks were not performed.
Desktop styling was the requested scope. Existing browser regression coverage
also exercised narrow widths, without a mobile redesign.

## Delivery and Rollback

Work is local and uncommitted. The isolated preview serves port 5000. Restore
only this task's Director template, header-context block, navigation selection,
campus tile presentation, CSS and new test when rolling back. Preserve prior
report upgrades and unrelated working changes. No database rollback applies.
