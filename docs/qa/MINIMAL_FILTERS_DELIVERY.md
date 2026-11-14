# Minimal Filters and Newspaper Case — Local Delivery

14 November 2026 · `codex/ui-workflow-overhaul` · local, uncommitted/unpushed.
No deployment, operational database changes, new schema, application library,
generated image, search service/logging, or broad cleanup. Earlier working changes
and the unrelated documentation DOCX remain preserved.

## Analysis → Design → Implementation → Testing

The codebase-analysis workflow traced active route templates, GET parameters,
shared query/navigation helpers, annual scope and export dependencies. Its survey
delegation was read-only. Findings informed the pre-implementation design and
inventory in [MINIMAL_FILTERS_DESIGN.md](MINIMAL_FILTERS_DESIGN.md).
Frontend-design and design-system defined the shared native pattern; Search UX
provided refinement/empty-result guidance. Webapp-testing supplied Playwright
verification; existing server lifecycle/test tooling was reused. UI/UX Pro Max
remained supporting accessibility/responsive guidance.

Structure: Flask routes call authorized report/list services, Jinja renders native
GET forms and shared controls, compiled Tailwind styles them, and the existing
script progressively handles period fields and validation disclosures.
Patterns: no live search, no frontend state store, shared URL/chip/Back helpers.
Flow: primary plus More values submit together, the server filters once, then the
same supported scope feeds screen values, pagination and matching exports.
Decision: change presentation/source wording without changing stored content or
counting rules. Context: preserve the previous overhaul and staff Overview fixes.

## Result and compatibility

- Reports now displays Reporting Year, Period, Activity Delivery, Search Activities
  and Director Campus as primary controls. One More Filters disclosure contains
  department, exact activity, category, follow-up, SDG, sex, affiliation and campus
  include/exclude. There is no third nested campus disclosure.
- More is closed after navigation/submission and reports the number of active
  specialist fields, counting a multi-campus selection as one field. Closed
  controls remain enabled. Chips remain available outside More; removal preserves
  other filters and resets pagination.
- Annual/All Records hide irrelevant period fields; Quarterly shows Quarter,
  Semi-Annual shows Half-Year, Custom Dates shows From/To. Legacy month URLs use
  normalized dates. Native forms also submit successfully with JavaScript disabled.
- AOP displays only year/campus. Activity/history/annual-evidence/account filters
  use the approved primary/More inventory. Simple roster/people/partner/year forms
  have consistent Apply/Reset controls without an empty More section. Account
  campus/search filters now submit together; active tab is retained.
- Historical exact year and year range still intersect. Range inputs no longer
  inherit an exact year accidentally. Existing query names are unchanged.
- Legacy `q`/`college_affiliation` report refinements are displayed and canonicalized
  on submission. Chip removal/reset clears both canonical and legacy aliases.
- Unavailable selected activity/department/category/affiliation choices retain
  their constrained value with explanatory copy instead of silently broadening
  results on the next Apply. All rendering stays escaped and campus-authorized.
- Staff Overview retains its compact composition, campus annual rollup and five
  KPI definitions, using the shared conditional period component.

## Newspaper Case review

Reviewed 89 active route templates/partials; 83 existing templates changed in the
source comparison. The pass covers active public/auth/account, role, activity,
reporting, management, annual-plan, Help, notification and error interfaces.
Fixed labels also come from Python presentation dictionaries, Jinja macro/tuple
labels, guide titles and generated controls; these were reviewed separately.

Headings/navigation/labels/buttons/table headers/fixed choices use headline style,
with short articles/conjunctions/prepositions lowercased appropriately. Supporting
instructions, validation, success messages and descriptions remain sentence style.
PSU/AOP/ASP/MOA/NDA/SDG keep their established spelling. Existing CSV/Excel field
names remain compatible. Authored activity/person/department/agency names,
agreements/policies, filenames and stored notification content are not recased.

Edits are explicit source text/display labels. A one-time ignored editorial helper
produced a source review; there is **no application title-casing function applied
to user/database values and no CSS capitalization rule added**. A mixed-case
authored activity/department regression confirms their text and stored values
remain unchanged. An existing visible mojibake separator in registration history
was corrected to a middle dot.

## Completed verification

| Run | Result |
| --- | --- |
| New filters + staff Overview + existing UI/reimagining tests | 26 passed |
| Workflow overhaul + report query + profile/settings | 85 passed; one stale import-heading assertion updated and then passed separately |
| Later filters/template/annual-rollup/reminder regressions | 9 passed |
| Final filters + complete template compilation | 7 passed |
| Final filter/browser matrix | 129 checks, zero JavaScript errors |
| Final existing guide/draft/navigation browser pass | 23 checks, no page overflow or JavaScript errors |
| Staff browser regression earlier in this pass | 27 checks passed |
| Tailwind build, changed JS syntax, whitespace check | Passed |
| Refreshed private preview | All three role login/dashboard smoke checks passed; reviewed filter destinations HTTP 200 |

Runs overlap and must not be added as one unique test total. Existing
Matplotlib/Pyparsing deprecation warnings appeared in PDF tests. The complete
legacy repository suite was not rerun; obsolete UI/role assertions remain outside
this pass. No full WCAG, physical-device, screen-reader or production/MySQL load
certification is claimed.

The 129-check matrix covers Director/Coordinator/Volunteer/public routes at
1440, 768, 390 and 320px plus 844×390 landscape; conditional periods, normalized
legacy dates, collapsed selection retention, active counts, quarter/half/custom/
all submissions, campus include values, remove-one/reset, matching CSV scope,
validation revealing More, 200% text with More expanded, native no-JS submission,
authored casing, and print generation. Unit regressions add campus isolation,
literal `%`/`_` search, historical year intersections, query/Back persistence,
export agreement, attendance boundaries, drafts/consent and submission cleanup.

QA fixes made before the final pass:

- Missing source fallback labels and old exact-label test selectors were aligned
  with the intended headline-style interface. Two initial new-test assumptions
  were corrected (out-of-range empty-result pagination and authenticated login
  redirect); these were not product defects.
- Screen-reader-only link text was escaping a horizontally scrolled annual table.
  Relative link containment fixed the document overflow without hiding records.
- Long topbar labels now wrap. Phone padding remains physical 16px, and topbar
  icon targets stay 44px when text grows.
- Checkbox inputs were unintentionally inheriting full text-input width inside
  the filter grid; that rule now excludes checkboxes/radios.
- AOP campus results are in a keyboard-accessible scroll region. Detailed report
  tables have readable minimum widths rather than wrapping titles one letter at
  a time; print removes those minimums.
- The no-JS fallback no longer depends on a noscript-only style override. Fields
  are reachable without script execution and progressively hidden with JS.

Print output was generated and text verified (three pages on the disposable
fixture); physical printing was not performed. Screenshots were visually reviewed
for compact primary filters, expanded More, AOP and responsive copy.

## Local review and artifacts

Open `http://127.0.0.1:5000`. The existing ignored preview launcher uses its private
database/uploads and suppresses mail; no data was reseeded. Accounts:
`director@psu.edu`, `coordinator@psu.edu`, `student@psu.edu`, password `password`.
Sign in again after restart because the preview session secret rotates.

Evidence under `.qa-overhaul-temp/minimal-filters/`:

- `before-live/`, `after-live/`: same private-preview report/AOP/historical and
  Volunteer activity/history captures at desktop/phone widths.
- `after-live/report-filters-1440.png`, `report-filters-390.png`,
  `report-filters-more-390.png`: focused review images.
- `after/`: disposable fixture matrix screenshots, expanded/active More, 200% text,
  print PDF and final `results.json` (129 checks).
- `before-source/`, `working-before.patch`: source rollback reference preserving
  earlier working changes. The patch alone does not include all untracked files.
- `active-templates.json`, `changed-active-templates.json`,
  `interface-source-review.patch`: interface coverage and source comparison.

Existing browser regression evidence remains in
`.qa-overhaul-temp/browser/polish-results.json` (23 checks).

## Commands and scoped rollback

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_minimal_filters.py tests/test_staff_overview.py tests/test_ui_polish.py tests/test_ui_reimagining.py -q
.venv/Scripts/python.exe -m pytest tests/test_workspace_overhaul.py tests/test_report_queries.py tests/test_profile_settings.py -q
.venv/Scripts/python.exe scripts/qa_minimal_filters.py
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Stop the existing preview before restarting. Browser scripts use their own
disposable app; never point fixture initialization at operational data. Windows
Chromium/pytest may need the same approved local execution access used here.

No database rollback is needed. Save the current working tree first, reverse only
this pass's template/helper/script/CSS/copy changes against `before-source/`, and
remove only this pass's new filter partial/tests/QA script/documents if desired.
Rebuild Tailwind and restart the isolated preview. Do not blanket reset/clean the
mixed working tree or overwrite uploads, databases, credentials or unrelated work.
Commit, push and deployment remain separate release actions.
