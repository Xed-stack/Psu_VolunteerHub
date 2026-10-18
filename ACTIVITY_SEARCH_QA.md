# Live activity-name search verification

Date: 18 October 2026

## Scope and decisions

Native labelled search inputs reuse the shared role shell and filter grid.
Existing Inter typography, PSU blue focus, 44px controls, and single base.css
remain unchanged. Institutional dials: ENERGY 1 / RHYTHM 2 / MOTION 1.
Ponytail full and the requested Anti Slop/design/accessibility skills favor the
existing GET form and report builder, without JavaScript or a new dependency.

Search is a literal case-insensitive title substring. SQL wildcard characters
are escaped; whitespace-only input means no title filter. Search combines with
existing report filters. Director pagination remains ten rows; exports contain
all matching rows and include the search term in metadata. PDF search metadata
is escaped before rendering. Stable ID ordering resolves equal event dates.

Coordinator campus scope is server-derived. Historical reports and annual
recognition remain separate; profile, affiliation, and readiness evidence keep
their labelled independent scopes. Director sex-disaggregated participation
also applies title search. No View all interaction or migration was added.

## Automated checks

- Reporting, analytics, and UI structure regression run: **57 passed** in
  138.80 seconds. An initial test used a nonexistent context key; that test was
  corrected to inspect the actual chart data before this passing rerun.
- Final-code follow-up after adding attendance-table search: **3 passed**,
  including both role/export checks and the additional literal-symbol,
  participation, attendance-table, and actual PDF rendering case.
- `git diff --check` passed. Full suite not rerun.

Run reporting, analytics, and UI structure tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_app.py::TestReportingSystem tests/test_app.py::TestAnalytics tests/test_ui_structure.py -q -p no:cacheprovider
```

New cases cover case/whitespace, blank/unmatched titles, literal percent and
underscore, combined date/category/campus scope, real participation counts,
sex-disaggregated attendance, preserved pagination/export links, both role
routes, coordinator scope tampering, CSV metadata, PDF payload parity, and actual
PDF rendering with markup characters in the search metadata.

All database fixtures use isolated in-memory SQLite, not live MySQL.
The previous full-suite result (277 passed) predates both campus filtering and
this search enhancement; the full suite was not rerun for this scoped change.

## Browser and interface review

- Isolated CSRF-enabled Director preview on port 5056; no deployment data used.
- Enter submitted the title search and displayed only Coastal Cleanup Drive.
- Unmatched search displayed the existing explicit empty state; keyboard Clear
  restored all nine fixture activities and blanked the input.
- Desktop client/scroll width: 1265/1265px. Mobile 390px viewport: 375/375px;
  search field 305px wide and 44px high. Shared grid stacks naturally.
- Mobile evidence: report-search-mobile.png in the session visualizations folder.
- Preview tab closed, viewport reset, and temporary server stopped.
- Reviewed changed templates against current Web Interface Guidelines: wrapping
  labels, meaningful query names, search input type, autocomplete off, described
  help, native keyboard submission, retained URL state, and inherited focus.
- Anti Slop changed-surface gate: purposeful PSU styling, real report data and
  controls, explicit empty/recovery state, no decorative assets or new motion.
- Native screen-reader output, physical touch, actual browser zoom, and a
  separate Coordinator browser session were not tested. Coordinator routes and
  exports are covered by automated checks. No claim of a full accessibility audit.
