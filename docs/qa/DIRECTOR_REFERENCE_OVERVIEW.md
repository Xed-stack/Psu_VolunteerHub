# Director Reference Overview

24 November 2026. Local implementation on `codex/ui-workflow-overhaul`, based on
`3a158fe`. This document supersedes the older rearrangement/AOP layout notes for
the current Overview presentation. The user subsequently authorized committing
and pushing this implementation to `codex/ui-workflow-overhaul` on both `origin`
and `thesis`. No deployment, dependency, migration, or operational database change.

## Approved Experience and Data

The Director Overview follows the supplied reference: scope form, navy annual
achievement panel containing three metrics, then Needs Attention beside Campus
Annual Commitments and Accomplishments. It ends after these two supporting
panels. The shared PSU shell/footer and Reports access remain. Coordinator
Overview and report screens retain their existing components and calculations.

Annual achievement sums existing per-goal completed activity contributions and
divides by summed university Director targets. A linked activity earns credit
once per goal; campus commitments alone earn no credit. For example, 13/10 is
130%, with 3 above target. Campus selection restricts contributions/commitments,
but retains the university denominator. Period/participant filters do not alter
annual figures. No target yields an explicit unset state, not division by zero.
Existing goal-met, eligibility, permission, attendance and export rules remain.

Conducted Activities and Verified Attendees retain report-period scope; attendees
count recorded presences with repeats. Campus Committed Activities sums submitted
annual quantities. Every selected campus is listed alphabetically; no submission
is distinct from zero completed contributions. There is no certification gate,
academic-year conversion, invented deadline, or copied mockup statistic.

Director guide order: scope, annual achievement, metrics, reviews, campus
commitments, Reports. The branch has merged administration into the Director
role; compatibility is checked through actual management/settings routes rather
than fabricating an unsupported `admin` enum value.

## Design Read and Critique

University oversight for PSU Directors; ENERGY 2 / RHYTHM 2 / MOTION 1. Reuse the
existing Inter/system typography and PSU navy, blue, gold, white and slate tokens.
The reference-authorized navy gradient and single panel shadow establish annual
achievement as the focal point. Gold emphasizes achievement, with white panels
for routine tasks. No new imagery, icons, fonts, assets or navigation structure.

Pre-build findings addressed:

- High: annual/period scopes are distinguished in the headline, metrics and table.
- High: certification/unique-person claims in the reference are replaced by the
  actual submission and attendance semantics.
- Moderate: review categories wrap; every campus has an explicit row.

Rendered critique addressed a gold-on-gold badge caused by selector specificity,
cramped mobile review headings, and low-contrast donut edges. The final badge
has navy text on gold. Review headings wrap naturally; light chart segments have
dark boundaries and the navy segment a white boundary. Supporting panels use
natural content heights rather than stretching the review card into empty space.
Showing all nine campuses makes this longer than the reference's three-row
illustration; this is an intentional content difference, not omitted data.

## Verification

- Focused Overview/AOP/review tests: 46 passed in 180.02 seconds.
- Additional connected Coordinator/UI/report/export coverage: 23 passed within
  the compatibility run. Its initial unsupported-Admin test fixture was replaced
  with the two actual Director administration-route checks.
- Final AOP/administration subset: 7 passed in 25.78 seconds, including the two
  actual Director management/settings routes. Across these runs, 71 distinct
  Python cases passed. The initial obsolete ASP fixture was also corrected.
- Browser runner: `scripts/qa_director_reference.py`, 20 groups passed. Both
  review modes at 1440/1280/1024/768/390/320px, 130% plus exceeded-target text,
  three metric layouts, nine campus rows, target sizing and no horizontal spill.
- Browser checks also exercised all five evaluation periods, filtered keyboard
  queue navigation, every distinct Overview link destination, complete guide,
  empty review/no-target states, long campus names, doubled root font size,
  blocked Plotly, JavaScript disabled and unchanged Coordinator metrics.
- 141 templates parsed; CSS build, both changed JavaScript syntax checks and
  `git diff --check` passed.
- Contrast: white/PSU blue 9.97:1; gold/PSU blue 5.77:1; navy/gold badge 8.03:1;
  light-blue text/brightest target hover 4.83:1. Donut boundary pairs are at least
  8.51:1 for light segments and 9.97:1 for navy against white.

Browser evidence: ignored `.qa-overhaul-temp/director-reference/`, including
`results.json`, desktop/mobile screenshots for both modes, and enlarged text.
Data is disposable synthetic in-memory SQLite, with CSRF enabled. Temporary
browser servers stop on completion. Windows sandbox denied pytest temp paths
and Playwright pipes; these checks ran outside the sandbox without changing the
operational database. No full-suite, operational MySQL, physical-device, manual
screen-reader or true browser-zoom claim. Doubled root font is text reflow evidence.

## Current Guidelines Audit

Fetched 24 November 2026 from
<https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md>.

- `templates/workspace/director_overview.html`: pass; named links, logical
  headings, scoped table headers, exact values and meaningful empty states.
- `templates/workspace/review_card.html`: pass; categories wrap, counts and
  navigation survive missing charts, factual recommendation and keyboard links.
- `templates/workspace/staff_overview_components.html`: pass; native labelled
  scope fields, preserved URL state and year validation.
- `templates/partials/filter_ui.html`: pass; optional period-label argument
  preserves existing callers and native period/date behavior.
- `ui/app.css`: pass; mobile records, bounded grids, visible focus and tabular
  counts, verified contrast, no added animation or clipped overflow.
- `static/scripts/first-use-tour.js`: pass; updated visible targets and factual
  instructions reuse the existing native dialog and keyboard behavior.
- `static/scripts/workspace-charts.js`: pass; segment boundary contrast improved,
  existing hidden-chart fallback and accessible category values retained.

## Antislop Delivery Gate

- R-02 PASS: no em dashes added to interface copy.
- R-03 PASS: six viewport widths, mobile records, enlarged text and long names checked.
- R-17 PASS: all metrics use existing reporting facts or AOP progress.
- R-18 PASS: no testimonials or invented people added.
- R-23 PASS: supplied reference authorizes the layout; no new visual assets created.
- R-24 PASS: all distinct Overview navigation destinations returned HTTP 200.
- R-25 PASS: contrast calculations and chart boundary checks recorded above.
- R-26 PASS: scope submit, metric/detail links, queue links and guide exercised.
- R-27 PASS: empty reviews, no targets, missing charts and native request states checked.
- R-28 PASS: no FAQ added.
- R-32 PASS: visible keyboard focus and Enter queue navigation checked; guide completed.
- R-33 PASS: source templates/CSS edited directly with patches; generated CSS uses existing build.
- R-34 PASS: no theme toggle introduced; existing light shell preserved.
- R-35 PASS: running isolated app exercised in Chromium; build and link checks recorded.
- R-36 PASS: no fabricated security, performance or compliance claims added.
- R-37 PASS: approved reference and declared design read drove implementation.
- R-38 PASS: synthetic values confined to isolated tests and labelled fixture records.
- R-39 PASS: native controls, existing pointer/focus rules, named links and reduced-motion browser checked.
- R-40 PASS: no new media or render-blocking script; existing chart fallback retained.
- R-01 PASS: navy gradient is limited to the reference's focal annual panel.
- R-04 PASS: existing warning icon denotes actual review work; no decorative icons added.
- R-06 PASS: existing PSU typography retained; fixed labels use Newspaper Case.
- R-07 PASS: no background pattern added.
- R-08 PASS: no decorative arrows added.
- R-09 PASS: achievement badge conveys a real calculated result; no duplicate eyebrow above H1.
- R-10 PASS: no glass or backdrop blur added.
- R-12 PASS: shadow limited to the reference's primary achievement panel.
- R-13 PASS: no glows introduced.
- R-14 PASS: three metric tiles group comparable headline facts, with scope captions.
- R-19 PASS: no new animation; MOTION 1 retained.
- R-22 PASS: no generic illustrations.
- Liveliness PASS: declared dials, one gold/navy focal panel, structural spacing and PSU identity.
- C-1 PASS: major visual choices follow the approved reference and PSU tokens.
- C-2 PASS: interactive destinations and scope submission checked.
- C-3 PASS: only approved Overview sections remain.
- C-4 PASS: responsive, empty, keyboard and script-failure cases checked.
- C-5 PASS: no fictional claims introduced.
- R-05 PASS: composition follows the user's reference rather than an unrelated template.
- R-11 PASS: bounded input, card and panel radii; no universal pill styling.
- R-15 PASS: actions name their destinations, including Apply Scope and Review All Campus Commitments.
- R-16 PASS: no promotional buzzwords added.
- R-20 PASS: PSU annual targets, campuses and review work define the content.
- R-21 PASS: no forced dark theme; navy is confined to the approved achievement panel.
- R-29 PASS: existing PSU palette with semantic review warning colors retained.
- R-30 PASS: no other product's interface introduced.
- R-31 PASS: written visual rationale appears above.

## Rollback

Restore only this task's route/service, Overview/filter/review templates, guide,
chart outline and CSS changes; rebuild CSS. Remove this task's new Director
template and browser runner if reverting. Preserve unrelated untracked files and
older QA evidence. No schema or data rollback applies. The reused AOP test file
was adapted from the untracked earlier implementation; do not delete unrelated
SQL proposal tests or private preview artifacts.

Skills used: UI/UX Pro Max, Frontend Design, Design Critique before/after,
Ponytail full, Antislop core/UI/Human/Layoutmobile during work, Web Design
Guidelines and Webapp Testing.
