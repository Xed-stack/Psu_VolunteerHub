# Coordinator Reference Overview

24 November 2026. Local implementation on `codex/ui-workflow-overhaul`, based on
published Director revision `983bb73`. The user subsequently authorized committing
and pushing this work with the Director AOP Goals layout to
`codex/ui-workflow-overhaul` on origin and thesis. No deployment, dependency,
migration, or operational database change is part of this task.

## Experience and Data

The supplied reference leads the Coordinator Overview: existing scope form,
navy campus AOP achievement panel with three metrics, then Your Campus Schedule
beside Needs Attention. The page ends after these two panels. The separate
five-metric strip, annual summary, delivery/sex charts and footer shortcuts are
removed from this page. Reports, AOP Goals, Partners, Calendar, Saved Drafts and
other role screens retain their routes and permissions through existing navigation.

Achievement uses the existing annual campus AOP rows, without additional queries:
sum completed per-goal activity contributions / sum submitted campus commitment
quantities. 13 completed against 10 committed displays 130% and 3 above target.
An eligible activity earns credit once per linked goal. Commitment submission
alone earns no completion credit. No commitment gives an unset percentage and
campus AOP detail link; existing goal-met calculations are unchanged.

Year and the signed-in Coordinator's campus determine annual achievement.
Activity period, participant and activity filters do not alter that annual scope.
Conducted Activities and Verified Attendees retain their existing report scope;
attendees count recorded presences including repeats. Zero attendees does not
claim attendance is unrecorded. Campus Commitments is the submitted annual
activity quantity, not a count of fully achieved goals or university targets.

The existing agenda still shows the next five approved ongoing/upcoming campus
activities independently of report filters. Calendar, activity details, ongoing
attendance and all-activities links remain; ended attendance is still locked.
Needs Attention groups all existing campus findings into the four established
categories. Its category links open the generated queue, with matching filters
and pagination reset. It does not grant Director decisions or change persistence.
Next Action comes from the first nonempty category in the existing ordering.
No invented certification process, deadline or numerical mockup claim was added.

## Design and Critique

Reading this as a campus operations dashboard for PSU Coordinators, following
the approved PSU reference: ENERGY 2 / RHYTHM 2 / MOTION 1. The existing Inter/
system typography, PSU navy/blue/gold, white panels and slate body text remain.
The reference's navy gradient and single panel shadow distinguish annual
achievement; quiet schedule/findings panels support the Coordinator's next task.
No new imagery, fonts, icons, libraries or navigation structure.

The desktop schedule/findings grid is 60%/40% from 1280px; below that, schedule
precedes findings. Metrics have three columns from 1024px, two with a spanning
last item on tablets, and one below 480px. The achievement summary stacks below
1024px. Native controls and existing agenda reflow remain in use.

Pre-build critique and decisions:

- High: replace the screenshot's inconsistent 1/1 target versus 12 commitments
  with the approved completed/committed denominator throughout.
- High: do not infer missing attendance or certification obligations from a
  zero value or illustration; use source-supported wording and actions.
- Moderate: retain annual findings as the fourth category rather than omitting
  them for a closer three-category screenshot match. Labels wrap in narrow cards.

Rendered critique fixed singular Next Action wording and the narrow desktop
donut's cramped Findings label. A Coordinator-only 140px minimum chart column
keeps the label inside its hole; Director layout rules remain unchanged.
Scope fields stack below 480px so native selected-period labels remain readable
at 320px rather than clipping inside half-width fields.
The final rendered review found no blocking visual defects. A long five-item
mobile schedule is intentionally vertical, preserving every action and label.

## Verification and Evidence

Evidence is isolated synthetic SQLite with CSRF enabled. No operational database
was loaded, copied, migrated or modified. Browser servers stop after the checks.
The current reproducible Coordinator runner is
`scripts/qa_coordinator_reference.py`; Director regression uses
`scripts/qa_director_reference.py` with its outdated Coordinator-five-tile
expectation updated to the approved three-metric screen.

- CSS build, changed JavaScript syntax and `git diff --check` passed.
- All 141 templates parsed in the browser runners.
- Director browser regression: 20 groups passed, including its two review modes,
  six widths, achievement, scope, guide, link destinations and script fallbacks.
- Coordinator browser: 21 groups passed across both review-feature configurations
  at 1440/1280/1024/768/390/320px. Checks include 0/100/130%/unset states, all five
  period submissions, unchanged annual scope/agenda, forged campus parameters,
  four category totals matching their filtered queue results, all 18 distinct
  Overview destinations, the six-step guide, long campus names, doubled root
  font, empty agenda/findings and blocked Plotly/JavaScript-disabled fallbacks.
- Python: 41 distinct cases passed in 160.19 seconds. This includes the new
  nine Coordinator cases plus existing staff, Director, attendance-window and
  draft regressions. Two finalized Next Action cases also passed separately
  (repeated cases, not an additional distinct count).
- Command: `.venv/Scripts/python.exe -m pytest tests/test_coordinator_reference_overview.py tests/test_staff_overview.py tests/test_director_overview_refinement.py tests/test_director_aop_achievement.py tests/test_workspace_overhaul.py::test_attendance_window_server_and_external tests/test_workspace_overhaul.py::test_draft_refresh_private_scope_and_secrets -q -x -p no:cacheprovider --basetemp=.qa-overhaul-temp/coordinator-focused-tests`.
- Measured unchanged palette: navy/gold badge 8.03:1, white/PSU blue 9.97:1,
  light-blue text/brightest target hover 4.83:1. Existing chart boundary colors,
  semantic warning styles and visible keyboard focus are reused.

Ignored screenshots/results: `.qa-overhaul-temp/coordinator-reference/` and
`.qa-overhaul-temp/director-reference/`. Desktop/mobile screenshots are labelled
synthetic through fixture content; they are not institutional activity records.

Limits: focused tests and headless Chromium only; no full-suite, operational
MySQL, physical-device, manual-screen-reader or true browser-zoom claim. Doubled
root font size is text-reflow evidence. Windows sandbox temp-directory/pipe
permissions required running the isolated checks outside the sandbox.

## Current Web Interface Guidelines Audit

Fetched 24 November 2026:
[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).

- `templates/workspace/overview.html`: PASS; source order matches visual order,
  role-specific panels and meaningful existing actions remain.
- `templates/workspace/director_overview.html`: PASS; shared native links and
  scoped metrics, explicit unset state, stable heading/guide targets.
- `templates/workspace/review_card.html`: PASS; category values survive chart
  failures; controls have accessible names and next actions reflect real counts.
- `templates/workspace/staff_overview_components.html`: PASS; native labelled
  scope controls and current-year/period validation preserved.
- `static/scripts/first-use-tour.js`: PASS; six Coordinator steps target existing
  sections and reuse the established native modal keyboard behavior.
- `ui/app.css`: PASS; bounded responsive grids, wrapping labels, existing 44px
  controls, visible focus and no new motion or overflow clipping.

## Antislop Delivery Gate

- R-02 PASS: no em dashes added to interface copy.
- R-03 PASS: six widths, stacked mobile schedule, long names and enlarged text checked.
- R-17 PASS: metrics derive from existing annual/report rows.
- R-18 PASS: no invented people or testimonials.
- R-23 PASS: supplied reference and approved plan authorize layout; no assets created.
- R-24 PASS: existing campus-scoped destinations verified in browser navigation checks.
- R-25 PASS: palette ratios above; existing high-contrast focus/chart edges reused.
- R-26 PASS: scope controls, category links, activity links and guide exercised.
- R-27 PASS: no commitments, no findings, empty agenda and failed-chart states checked; native request/error handling retained.
- R-28 PASS: no FAQ introduced.
- R-32 PASS: native controls, visible focus, keyboard queue navigation and guide checked.
- R-33 PASS: source edited directly; generated CSS uses the existing build.
- R-34 PASS: existing light PSU shell remains; no theme toggle added.
- R-35 PASS: running isolated application exercised in Chromium; build succeeded.
- R-36 PASS: no fabricated security, compliance or performance claims.
- R-37 PASS: approved direction and explicit design dials established before building.
- R-38 PASS: synthetic fixtures confined to isolated tests; interface uses source data.
- R-39 PASS: native named controls, existing pointer/focus behavior and reduced-motion checks retained.
- R-40 PASS: no new media, blocking scripts or animation; existing chart fallback retained.
- R-01 PASS: reference-authorized navy gradient marks the annual focal panel.
- R-04 PASS: reused warning icon denotes findings; no generic decorative icons.
- R-06 PASS: existing PSU typography and Newspaper Case fixed labels.
- R-07 PASS: no background pattern introduced.
- R-08 PASS: no decorative arrows introduced.
- R-09 PASS: real achievement badge within the annual panel; no duplicate eyebrow above H1.
- R-10 PASS: no glass or blur introduced.
- R-12 PASS: existing annual-panel shadow reused for hierarchy.
- R-13 PASS: no glow added.
- R-14 PASS: three comparable headline measures share tiles with explicit scope captions.
- R-19 PASS: MOTION 1; no new animation.
- R-22 PASS: no generic illustration introduced.
- Liveliness PASS: declared dials, structural spacing, navy/gold focus and PSU identity.
- C-1 PASS: visual choices follow the approved reference and existing tokens.
- C-2 PASS: displayed controls retain real behavior and destinations.
- C-3 PASS: only approved Overview sections remain.
- C-4 PASS: responsive, empty, keyboard and script-failure scenarios checked.
- C-5 PASS: no fictional UI claims.
- R-05 PASS: follows the user's composition and campus task hierarchy.
- R-11 PASS: existing varied input/card/panel radii retained.
- R-15 PASS: existing specific activity and queue action names retained.
- R-16 PASS: no promotional buzzwords added.
- R-20 PASS: campus commitments, activities and findings define the screen.
- R-21 PASS: navy is confined to the focal panel; light shell retained.
- R-29 PASS: existing PSU palette and semantic warnings reused.
- R-30 PASS: no competing product style introduced.
- R-31 PASS: visual rationale and critique decisions documented above.

## Rollback and Skills

Revert only this task's service/route, shared template/CSS and Coordinator guide
changes, and rebuild the generated CSS. Restore the preceding Coordinator-specific
test expectations if reverting the layout. Preserve the published Director work,
unrelated untracked files, older QA documents and private preview artifacts.
No data or schema rollback applies.

Skills applied: UI/UX Pro Max, Frontend Design, Design Critique before/after,
Ponytail full, Antislop core/UI/Human/Layoutmobile during work, Web Design
Guidelines and Webapp Testing.
