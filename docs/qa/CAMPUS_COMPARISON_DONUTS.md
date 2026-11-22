# Campus Comparison Navigation and Donut Charts

Local implementation on `codex/ui-workflow-overhaul`, 22 November 2026.

## Analysis and Approved Choices

The Director Overview used Campus Comparison with an Annual Details link; report
Summary used Campus Accomplishments with comparison checkboxes in More Filters.
Both roles shared the verified-attendance horizontal bars and exact values table.
Reuse existing report data, Plotly, native GET filters and campus authorization.

The user approved whole-report comparison filtering, an Apply button that reloads
at the comparison section, all-campus initial navigation from Overview, and keeping
the primary Campus dropdown at the top. Include/exclude checkboxes move beside the
comparison chart. Previous flow-audit repairs remain explicitly deferred.

Design read: institutional reporting for PSU Directors and Coordinators, Energy 2,
Rhythm 2, Motion 1. Retain PSU blue/gold, existing Inter, slate surfaces and clear
section hierarchy. The screenshot identifies labels/navigation, not a new backdrop
or visual theme. Skills applied: UI/UX Pro Max, Frontend Design, Design Critique,
Ponytail full, Antislop core/UI/human/mobile, Web Design Guidelines and Webapp Testing.

## Delivered Behavior

- Director Overview says Campus Accomplishments. Compare Campuses opens report
  Summary at `#campus-comparison`, removing only campus restrictions, pagination
  and old view/replay context while retaining period and other report filters.
  The existing expandable annual/evidence table and links remain.
- Report Summary says Campus Comparison. Its Director-only GET form has Selection
  Mode, alphabetical campus checkboxes, Apply Comparison and Reset Comparison.
  Four standard 44px rows fit in the scrollable list; oversized labels/text grow
  naturally rather than clip. Keyboard focus scrolls remaining choices into view.
- The top primary Campus dropdown stays. When active, the comparison form clearly
  names its restriction. Reset Comparison clears only multi-campus choices/mode.
  Report record tabs provide Adjust Campus Comparison back to Summary's anchor.
- Independent forms preserve current applied scope through hidden GET values;
  they do not duplicate visible campus checkboxes in More Filters. Top filter
  submission retains multi-campus selections. Comparison submission resets page
  to one; exports still use the whole authorized filtered scope. Annual KPI
  calculations and primary-campus semantics are unchanged.
- Native fragment navigation works without JavaScript. A small load handler aligns
  the panel below the sticky header and focuses its heading without a second jump.
- Shared verified attendance now uses a donut in both Overviews, Summary,
  Participation Records and Combined Activity Reports. Center shows total; ring
  labels/hover use the server-provided rounded shares, preserving table rounding.
  Zero groups remain in the four-row text table. Zero totals keep the empty state.
- Female uses PSU blue, Male PSU gold, Prefer Not to Say slate, Not Recorded light
  slate, consistently. Dark slice boundaries and text/key labels avoid color-only
  meaning. Native table retains PSU, External, Total and Share. No slice toggling
  can change the displayed denominator.
- Responsive chart sizing and fallback values remain. PDF/Excel chart formats,
  CSV fields, calculations, routes, account/campus permissions, and published
  proposal/draft handling were not changed. Help and tour wording were updated.

## Design Critique and Final Audit

| Priority | Finding | Resolution |
| --- | --- | --- |
| Moderate | Headings and destination do not match the comparison task | Dashboard/report headings corrected; comparison opens the report panel |
| Moderate | Comparison choices are remote from the chart | In-panel selector with four visible standard rows and native scrolling |
| Moderate | Filter submission returns to page top | Native anchored GET, sticky-header offset and heading focus |
| Moderate | Primary Campus can silently restrict comparison | Visible named restriction; user explicitly kept dropdown above |
| Moderate | Donut can depend on color or hide tiny/zero groups | Labelled exact table, matching color keys, counts/shares and fixed total |
| Moderate | Enlarged text overflows native fieldset/buttons | Fieldset minimum reset and wrapping buttons; 200% browser check passes |
| Minor | Short delivery panel stretches to comparison-panel height | Chart grid aligns panels at the start |

Fresh Web Design Guidelines reviewed from
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md.
Changed templates/scripts/styles were checked for labels, focus, native forms,
query state, non-color equivalents, responsive overflow and reduced motion. No
in-scope finding remains; this is not a site-wide conformance certification.

## Verification

- **51 focused regression cases passed**: comparison navigation/scope/reset,
  primary/More filters, sex calculations/exports, staff Overview, report journeys,
  Help and role boundaries. Existing Matplotlib/Pyparsing deprecation warnings
  remain non-failing. Tests use isolated in-memory SQLite and dedicated temp paths.
- **53 browser groups passed** on synthetic in-memory SQLite with CSRF enabled:
  both roles, Overview/Summary/Participation, 1440/1024/768/390/320px, donut type,
  total/percentage reconciliation, four standard campus rows, scrolling/focus,
  include/exclude/reset, dashboard navigation, report tabs, live resizing, 200%
  text, long labels, single-category/empty states, combined reports, print state
  restoration, downloads, Plotly failure and JavaScript-disabled anchored filtering.
  Zero page errors. Final chart-container width checks and normal-viewport captures
  supplement full-page captures, which can show Plotly repaint artifacts.
- CSS build, 131-template parse, JavaScript syntax, contrast and whitespace checks
  passed. Dark text on gold is 9.91:1; dark text on light slate 11.53:1; white on
  slate 7.58:1. Reused blue/white pairing is 9.97:1. Dark boundaries remain visible.
- Screenshots and result JSON: ignored `.qa-overhaul-temp/verified-sex/`.
  `*-donut-viewport-*.png` and `*-comparison-viewport-*.png` show actual viewport
  rendering; synthetic browser servers stop in cleanup.

## Antislop Delivery Gate (Changed UI)

- Hard gate PASS: native controls/links, 44px campus targets, focus, exact sourced
  values, zero/failure states, four category labels and text alternatives verified
  in the browser suite; no new assets, unsupported claims, theme or dead controls.
- Purpose gate PASS: donut communicates part-to-whole attendance; four fixed
  palette entries identify the existing categories; outlined boundaries and text
  keys support readability. No decorative imagery, gradients or animation added.
- Liveliness PASS: explicit 2/2/1 direction, report comparison/task hierarchy,
  structural spacing, existing PSU accents/type/navigation preserved in renders.
- Craftsmanship PASS: source edits plus existing CSS build, matching calculation
  evidence, wrapped mobile/200% controls, zero page errors and reviewed viewport
  captures. Newspaper Case labels and sentence-case explanations retained.

## Limits and Rollback

No full-suite, operational database/MySQL, physical-device, manual screen-reader,
native Excel, Safari or Firefox validation claim. At enlarged text/very long labels
the selector may show fewer than four complete rows to preserve readable wrapping.
Primary Campus intentionally still intersects the comparison choices. Downloads
retain their existing chart types. Other audited defects remain deferred.

No commit, push, deployment, migration, dependency or operational data change.
Unrelated SQL update/guide/test, HANDOFF additions, DOCX, output and tmp preserved.
Rollback only this task's UI/help/test/QA edits and rebuild the matching stylesheet;
no database rollback is needed.
