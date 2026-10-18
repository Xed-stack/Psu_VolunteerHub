# Opportunities campus-filter verification

Date: 18 October 2026

## Scope and decisions

- Opportunities use repeated `campus` parameters and `campus_mode=include|exclude`.
  Existing `?campus=1` links remain compatible. No selection means all campuses.
- Inclusion matches any selected campus; exclusion hides only selected campuses,
  retaining unassigned activities. Search/category conditions still apply.
- Campus choices come from the existing catalog, ordered case-insensitively by
  name. Duplicates are normalized. Unknown/malformed choices and invalid modes
  return a usable filter page with HTTP 400, preserved valid choices, and no
  broadened results. No campus or academic-unit records are invented.
- Nine-row pagination retains all selected campuses, mode, category, and search.
  Ordering uses date then record ID for stable pages. Applying filters starts at
  page one; Clear restores the original unfiltered list.
- Design read: opportunity discovery for PSU volunteers and guests using existing
  institutional styling, ENERGY 1 / RHYTHM 2 / MOTION 1. Checkbox selections are
  visible without color; the disclosure keeps results accessible on small screens.
- Ponytail full: native GET forms, details, fieldsets, checkboxes, and a select.
  Existing Bare CSS, base.css, role shell, and PSU assets retained. Filter styles
  live in role-shell.css so guest and signed-in views share them. No new script,
  dependency, stylesheet, or migration.

## Automated evidence

- Final command: `python -m pytest tests/test_app.py::TestSearchFilterPagination tests/test_app.py::TestVolunteerFeatures tests/test_ui_structure.py -q -p no:cacheprovider`
- **49 passed in 110.88 seconds**, including 18 new campus-filter cases.
- Covers guest/volunteer inclusion and exclusion, alphabetical choices,
  duplicates, blank selections, all-campus exclusion, unassigned activities,
  unavailable catalogs, invalid IDs/modes, oversized numeric input, combined
  search/category constraints, pagination state, and existing single-campus URLs.
- Existing volunteer registration/consent/CSRF checks and shared UI structure
  remain passing. `git diff --check` passed.
- All test databases were isolated SQLite. The most recent full suite (277 passed)
  predates this enhancement and was not rerun for this scoped change.

## Browser evidence

- Isolated SQLite preview on port 5056 with CSRF enabled. A preview-only CSP
  `script-src 'none'` blocked page scripts on Opportunities, so filtering and
  disclosures were exercised without page JavaScript. Production CSP is unchanged.
- Guest: two campuses + search + category applied, then Next retained every
  selection. Exclusion, empty results, Clear, and stale-ID recovery worked.
- Signed-in volunteer: checkbox Space, disclosure Enter, Apply/clear keyboard
  activation, selected-state persistence, and collapse after Apply were exercised.
- Guest desktop (1280px), volunteer desktop (1280px), tablet (768px), and mobile
  (390px) checked. Client/scroll widths matched: 1265/1265 desktop, 753/753 tablet,
  375/375 mobile. Long unbroken campus labels wrapped without page overflow.
- New fields, choice labels, and actions have at least 44px height. Computed
  checkbox-label focus is solid 3px PSU blue; filter field edges are #526477.
- Contrast: blue/selected surface 7.71:1; edge/pale surface 5.81:1; muted/pale
  surface 8.88:1; error/pale surface 7.83:1. All pass their applicable thresholds.
- No browser JavaScript errors were reported. Native OS screen-reader output,
  actual 200% browser zoom, physical touch, and mobile keyboards were not tested.
- Temporary servers/tabs were stopped and the viewport override reset. No live
  MySQL data was read, seeded, migrated, or changed.

## Changed-surface delivery gate

- Hard gate PASS: real native controls, truthful query counts, keyboard operation,
  measured sizing/contrast/reflow, empty/catalog/error states, and no dead actions.
- Purpose gate PASS: PSU blue identifies focus/selection; existing typography
  and shared tokens retain identity; the disclosure prevents a tall filter list
  from hiding results after Apply. No decorative assets or motion added.
- Liveliness PASS: declared institutional dials retained; Apply is the primary
  filter action, with discovery results remaining the page's main content.
- Craftsmanship PASS: server-side catalog validation, stable pagination, existing
  single-campus compatibility, script-blocked browser checks, and regression tests.
- Web Interface Guidelines PASS for changed controls: native semantics, labels,
  grouped choices, visible focus, retained URL state, and guest skip/main landmarks.
  Reviewed against https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

No commit or push was made. Previous dashboard/profile/analytics and correctness
repairs are preserved.
