# Director Reports: Campus Delivery Comparison

Date: 22 November 2026. Local branch: `codex/ui-workflow-overhaul`.

## Result and Compatibility

Activity Delivery renders one named line for each campus in an active comparison,
using stable campus styles, shared monthly/yearly bins, zero values, markers and
dash patterns. The accessible View Delivery Values table exposes campus counts
and period totals. The shared service computes series from all scoped activity
rows before pagination, without per-campus queries. Unassigned conducted activities
receive a named series when they are included in the effective scope.

No active comparison retains the aggregate line. Coordinator charts and dashboard
consumers retain their existing scope and aggregate chart through an optional
presentation argument. Conducted-activity rules, attendance donuts, annual-target
rules, permissions, routes, pagination, export contents and return links remain.

Top Report Filters submissions omit `campus` and `campus_mode`, including when
Campus is All Campuses. Comparison submissions omit `campus_id`, preserve other
filters, reset page to 1 and return to `#campus-comparison`. Comparison reset clears
both campus controls. Existing URLs containing both controls retain their previous
intersection until a filter form is applied. Choices do not apply automatically.

Compare Campuses is a native disclosure, closed initially, with applied count/mode.
Its options float above the charts, with four standard campus rows visible and
native scrolling. JavaScript positions the panel within available viewport space
above or below the trigger; the panel itself can scroll in small spaces. Escape
returns focus to the trigger; outside pointer interaction and focus moving outside
close it. Without JavaScript, native disclosure/form operation remains available.

## Design Read and Critique

Audience: PSU Directors reviewing campus delivery. Retained institutional Inter,
PSU blue/deep blue, restrained existing surfaces and typography. Energy 2,
Rhythm 2, Motion 1. Dropdown shadow communicates temporary overlay elevation.

- High defect: aggregated delivery hid differences between selected campuses.
  Resolved with per-campus lines, names, markers/dashes and exact text values.
- Moderate defect: intersecting form submissions could silently prevent comparison.
  Resolved with the approved last-applied campus-control behavior.
- Moderate hierarchy issue: always-visible controls displaced the visual comparison.
  Resolved with a closed-by-default floating disclosure beside the heading.
- Moderate responsive defect found in verification: absolute fallback alignment could
  put options off-screen without JavaScript. Corrected responsive bounds.
- Moderate enlarged-text defect: a rem-based width cap made dropdown contents too
  narrow. Corrected viewport bounds and label wrapping; internal horizontal overflow
  is explicitly checked at 200% text.
- Moderate overlay issue: a tall panel could cover its own trigger. Corrected by
  constraining height to the available space above or below it.

Rendered desktop/mobile, long-label, enlarged-text and print results reviewed.
Additional chart styles, motion and global navigation redesign remain optional and
outside scope. Large comparisons can still create overlapping lines; named styles
and the full text table remain available, with no arbitrary campus-selection cap.

## Verification

**30 focused regression cases passed**:

```
.venv/Scripts/python.exe -m pytest tests/test_campus_delivery_series.py tests/test_comparison_navigation.py tests/test_verified_sex_reports.py -q --basetemp=.qa-overhaul-temp/campus-series-final
```

Includes two/single campuses, zero counts, include/exclude, unassigned activity,
yearly bins, legacy intersection, participant/activity filters, Coordinator scope,
more than 25 activities, aggregation query growth, both form-precedence directions,
closed initial disclosure, report navigation and CSV/Excel/PDF reconciliation.
An initial run found two errors in new test helpers; those were corrected and the
complete final set passed. Existing matplotlib/pyparsing deprecation warnings remain.

**16 new browser groups passed**, using `scripts/qa_campus_delivery.py`:
1440/1024/768/390/320px; exact campus traces and markers; fixed overlay positioning,
no chart displacement; four-row scrolling; keyboard/focus/Escape/outside dismissal;
text table; both precedence directions; anchored application; exclude/zero lines;
tabs/reset; 200% text; print values; long labels and live resize; no-JavaScript and
Plotly-failure controls/text; unchanged Coordinator aggregate. No page errors.
Evidence: `.qa-overhaul-temp/campus-delivery/results.json` and screenshots there.

**53 existing browser groups passed**, using the updated
`scripts/qa_verified_sex_reports.py`. Its interactions now open the disclosure
before operating its controls. Both roles' Overviews, report views, sex donuts,
responsive layouts, anchored comparison journeys, exports and fallbacks remain.
Evidence: `.qa-overhaul-temp/verified-sex/results.json` and screenshots there.

Every Jinja template parsed by the browser runner. CSS build, changed Python
compilation, both JavaScript syntax checks and `git diff --check` passed.
Line colors on white: blue 9.97:1, teal 5.47:1, slate 7.58:1, dark gold 5.85:1.
Names, dashes, markers and exact tables supplement color.

## Final Audit, Limits and Rollback

Applied UI/UX Pro Max (trend chart guidance), Frontend Design, Design Critique,
Ponytail full, Antislop during, Antislop UI/Human/Layoutmobile, Webapp Testing and
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched on 22 November 2026. Changed components, results template, chart/dropdown
scripts and CSS pass the scoped final audit after the fixes above. Native semantic
controls, visible focus, 44px choices, selected/empty states, GET URL scope,
viewport containment, reduced-motion rendering and usable text fallbacks remain.

No full-suite, live MySQL, physical-device, Safari/Firefox, native print-dialog or
manual screen-reader verification claim. Global navigation at enlarged text remains
unchanged. No operational database, schema, dependency, commit, push or deployment.
Unrelated SQL update/guide/test, their HANDOFF entry, DOCX, output/tmp and deferred
audit findings remain intact.

Rollback only this task's reporting service, presentation, chart/dropdown code,
help, CSS source/generated CSS, tests, browser scripts and documentation. Preserve
unrelated working changes. No database rollback is required.
