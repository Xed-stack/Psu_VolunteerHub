# Director live multi-campus verification

Date: 18 October 2026

## Scope

Native disclosure, wrapping checkbox labels, include/exclude select, and existing
GET submission reuse Opportunities' campus controls and the shared PSU role
shell. ENERGY 1 / RHYTHM 2 / MOTION 1; Inter, PSU blue, neutral surfaces, and
the single base.css remain. Ponytail full favors shared report data and native
controls. Anti Slop/UI/human/mobile and frontend-design guidance preserves
institutional styling, visible selected/focus/error states, and real actions.

Repeated `campus` values select live campuses. `campus_mode` is include/exclude;
no selection means all campuses in either mode. Exclusion preserves unassigned
activities, including when every catalog campus is excluded. Duplicates normalize.
Unknown, nonnumeric, oversized, or invalid-mode inputs cannot broaden results.
HTML returns an inline recoverable 400; downloads return 400 without a report.

The shared filtered rows feed live totals, comparisons, trends, SDG mapping,
pagination, and full CSV/PDF downloads. Director sex-disaggregated attendance
also intersects the same event IDs. Downloads name the mode and full campus
names; PDF scope metadata is escaped. Pagination and export links preserve all
choices plus search/date/category/sex/SDG inputs. Applying filters resets paging.
Historical and award forms retain repeated live choices.

The single `campus_id` continues to control historical and all-time home-campus
affiliation evidence. Legacy links containing only `campus_id` retain their live
scope too. Explicit new live parameters take precedence. Award recognition stays
university-wide for its selected year. Coordinator routes derive campus scope
from the account and do not accept a broader client-provided selection.

## Automated checks

- Reporting/analytics/UI regression rerun: **68 passed** in 165.95 seconds.
  Initial fixture expectations miscounted included/excluded campuses; corrected
  expectations passed the rerun without changing filter behavior.
- Final-code follow-up: **3 passed**, adding explicit verified-attendance
  agreement and the all-excluded/legacy/independent-scope case.
- Python compilation and `git diff --check` passed. Full suite not rerun.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_app.py::TestReportingSystem tests/test_app.py::TestAnalytics tests/test_ui_structure.py -q -p no:cacheprovider
```

New checks cover inclusion/exclusion, unassigned activities, blank/all-excluded
choices, duplicates, alphabetization, invalid/stale/oversized values, metadata,
PDF payload parity, repeated paging/export parameters, historical/award form
preservation, search/date/category combinations, verified attendance agreement,
legacy links, independent historical scope, and coordinator query tampering.

All fixtures use in-memory SQLite; no live MySQL data was changed. The last full
suite (277 passed) predates the subsequent campus/search enhancements. Full suite
not rerun for this scoped change.

## Browser evidence and limits

- Disposable in-memory SQLite preview on port 5056 with CSRF enabled.
- Enter opened the disclosure; Space selected Lingayen/Urdaneta; keyboard Apply
  produced five matching fixture activities and retained both query parameters.
- Switching to exclusion produced four other fixture activities.
- Invalid campus selection automatically opened the disclosure, showed its
  recovery message, and displayed no report rows. Clear restored nine activities.
- Desktop client/scroll width: 1265/1265px. At a 390px viewport: 375/375px.
  All nine campus checkbox labels measured 44px high. Native blue focus visible.
- Mobile screenshot: analytics-campus-mobile.png in the session visualization
  directory. Preview tab closed, viewport reset, temporary server stopped.
- Reused checkbox edge #526477 on white: 6.09:1; blue on selected pale blue:
  7.71:1 (prior measured component pairings, unchanged here).
- Changed templates reviewed against current Web Interface Guidelines: native
  fieldset/legend, labelled controls, described help, URL state, repeated-filter
  preservation, explicit empty/error recovery, and responsive grid reflow.
- Anti Slop changed-surface gate: purposeful reuse, actual report data, working
  controls, no decorative assets/motion, no new framework or foundation CSS.
- Native screen-reader output, actual browser zoom, physical touch, long custom
  campus names in this analytics preview, and a separate Admin browser session
  were not tested. Long wrapping behavior reuses the Opportunities component.
