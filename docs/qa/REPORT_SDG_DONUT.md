# Activity Accomplishments SDG Donut

Implemented locally on `codex/ui-workflow-overhaul`, 24 November 2026.

## Behavior and Design

Director, Coordinator and Admin Activity Accomplishments now show SDG Alignment
beside Sex-Disaggregated Verified Attendance in Summary and Participation Records
on desktop (1024px and above). Activity Records retain their existing SDG labels.
Mobile-specific styling and the existing narrow attendance layout are retained;
the new panel is hidden below 1024px, following the desktop-only instruction.

The panel counts one link per matching activity per linked SDG, across the full
filtered result before pagination. It uses the existing eager-loaded SDGs and
does not add database queries. An activity with multiple SDGs contributes to
each; percentages represent links, not attendees or unique activities.
Unassigned activities are counted separately and excluded from the donut.
At most five segments are shown: when needed, four leading goals and Other SDGs.
The exact-value table always lists all linked goals. No export format, stored
data, attendance calculation, permission or route changes were needed.

Design read: institutional reporting for PSU staff; Energy 2 / Rhythm 2 / Motion 1.
The existing typography, white bordered panels, PSU navy and gold are reused for
consistency with the adjacent attendance panel. Two equal desktop columns make
the requested comparison visible. Existing slate and light blue chart colors
distinguish additional segments; labels and the table avoid color-only meaning.
No decorative imagery, new dependencies or animation were added.

## Design Critique

- High, addressed: overlapping SDGs could imply mutually exclusive activity or
  attendee shares. Both the description and table specify activity-to-SDG links.
- High, addressed: totals must not change with pagination. Aggregation happens
  before the route slices rows; a 26-activity/page-two test verifies this.
- Moderate, addressed: a 17-segment donut would become difficult to read. The
  donut groups smaller slices while the table retains every linked goal.
- Moderate, addressed during rendered review: the new two-column layout cramped
  attendance labels at 1024px. Desktop-only table sizing now preserves full sex
  labels and keeps numeric values together.
- Optional preference: identical donut vertical alignment despite differently
  sized explanatory text. Panel tops align; content follows its reading order.

## Verification

23 focused tests passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_report_filter_outcomes.py tests/test_verified_sex_reports.py -q --tb=short -p no:cacheprovider --basetemp .qa-sdg-verified-temp
```

Coverage includes deduplicated mappings, multi-goal activities, grouped segments,
unassigned/empty scopes, year changes, participant/SDG/delivery filtering, forged
Coordinator campus parameters, full-result pagination totals, existing attendance
outcomes and exports, and constant aggregate query count. Existing Matplotlib /
Pyparsing deprecation warnings remain. Initial sandbox runs could not access
temporary folders; the successful run used approved execution access.

Six Chromium groups passed with no page errors:

```powershell
.\.venv\Scripts\python.exe scripts/qa_report_filter_outcomes.py
```

Both roles were checked at 1440, 1280 and 1024px for side-by-side placement, live
donuts, exact values, filters, tab navigation and page overflow. Checks also cover
200% root text sizing, keyboard navigation, empty assignment states, JavaScript
disabled, a blocked Plotly library and unchanged narrow layout at 390px.
The runner parses all templates. Screenshots and results are under the ignored
`.qa-overhaul-temp/report-filter-outcomes/` directory. Final 1024px rendered
review confirmed readable labels and no page overflow.

CSS build, JavaScript syntax and whitespace checks passed. The current
[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
were fetched on 24 November 2026 and applied to the changed templates, chart
script and CSS. No remaining in-scope findings: semantic headings/tables,
explicit empty/error fallback text, long-content wrapping, and exact values
available without pointer hover or JavaScript.

Contrast checks passed for all donut text/background pairings: navy/white 9.97:1,
ink/gold 9.91:1, white/slate 7.58:1, ink/light blue 8.51:1, ink/light slate 11.53:1.
Existing slate text on white is 7.58:1.

## Antislop Delivery Gate

- Hard Gate PASS: built and ran the UI; six browser groups verify navigation,
  empty states, fallbacks and overflow; all figures come from filtered data;
  labeled values and checked text contrast supplement the donut.
- Purpose Gate PASS: layout, typography and chart colors reuse PSU report patterns
  for comparison and continuity; no new decorative assets, effects or controls.
- Liveliness PASS: declared 2/2/1 direction; existing report hierarchy and navy/gold
  motif retained; paired analytical panels serve the requested reporting task.
- Craftsmanship PASS: 23 tests, browser evidence, source audit, native semantic
  tables, explicit multi-SDG denominator and preserved mobile presentation.

## Delivery and Limitations

The user authorized committing and pushing this addition to both configured
`codex/ui-workflow-overhaul` remote branches. No manual deployment was requested.
Before publication, an isolated snapshot of the staged changes passed the 13
report-filter/outcome tests and all six Chromium groups again. Its CSS was built
from that snapshot, excluding the concurrent unfinished Activities-page work.
The existing port-5000 preview was restarted without seeding or migrating its
database. Unrelated concurrent Activities-page edits are preserved.
Full-suite, physical-device, screen-reader and actual browser-zoom checks were
not performed. Text enlargement used root font sizing. Existing exports are
unchanged and do not gain the new SDG aggregate visualization.

Rollback removes only the SDG helper/route context, panel macro/call, desktop
styles, chart handler and this task's QA/test additions, then rebuilds CSS.
Preserve other changes in shared files. No database rollback applies.
