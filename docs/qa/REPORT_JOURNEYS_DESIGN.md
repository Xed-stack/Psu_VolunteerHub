# Reports and Annual Plans: Analysis and Design

## Analysis before implementation — 14 November 2026

Structure: Flask/Jinja routes in workspace/goals compose the existing workspace
report service and annual_goals module; Plotly and compiled Tailwind supply the UI.
`report_results` currently slices 25 rows only after computing the full report.
Export recomputes the same authorized scope before pagination. Preserve this pattern.
The current results template stacks charts, delivery, participation and a full roster.

Annual summary uses request-cached batched results and merges shared AOP/ASP rows
within each campus. `target_id` identifies a representative member: exact detail must
resolve the merged obligation by shared key, never assess the member independently.
Campus targets and university targets are separate. Director manages evidence;
Coordinator reads their campus and proposes revisions. Existing permission rules stay.

AOP links currently open the general indicator list and lose exact campus/indicator.
Annual evidence/proposal Back links discard list context. The annual list also retains
an unwanted live participation breakdown. Remove that panel, retaining aggregate
evidence with its obligation and live measures in Activity Accomplishments.

## Design read and tokens

Institutional reporting workspace for Directors and campus Coordinators. Energy 2,
rhythm 2, motion 1. PSU blue #00408b, deep blue #002b60, gold #f4bd27, ink #111c2c,
white and slate surfaces; Inter, 16px body, existing heading scale and 44px targets.
Scope and results are the focal point. Gold is a restrained annual-achievement accent.
Charts compare like units; no decorative imagery or motion. Native GET links/tabs.

Desktop:
```text
Reports / Activity Accomplishments                     Export PDF / Excel / CSV
Compact scope explanation + existing primary/More Filters
Summary | Activity Records | Participation Records
Summary: five scoped measures → campus comparison | delivery trend
Records: one paginated table → source activity / combined activity report
```

```text
Annual Operational Plan                                Export selected scope
Year / authorized campus
Campus obligations achieved/total | pending    University targets (separate)
Campus comparison table → scoped indicator list
Selected-scope indicators table → exact indicator detail
Verified target/actual comparisons grouped by unit
```

Phone: heading → scope → wrapping export actions/tabs → main results; charts stack.
Keep detailed tables in labelled keyboard-scrollable regions with readable columns.
No fixed action bars. Indicator details use a readable facts column and a secondary
evidence/actions rail; long definitions/source references wrap.

Annual list: compact summary then indicator rows; campus comparisons live on AOP
summary. Proposal/evidence screens share the journey heading and content surfaces.
Existing historical/people reports receive the same shell, retaining separate data.

States: explicit unknown/pending evidence, no approved targets, no matching records,
validation errors, saving/failure feedback and disabled submit feedback reuse existing
components. Chart text alternatives and source links remain usable without Plotly.
Fixed labels use Newspaper Case; authored content/export field names do not change.

## Preservation checklist

- [x] Five KPI definitions, periods, literal filters, authorized scope and comparisons.
- [x] Summary/records navigation, repeated campuses, pagination and contextual Back.
- [x] Matching complete filtered CSV/Excel/PDF datasets and single-activity roster.
- [x] Shared obligations, unknown evidence, campus/university separation and sample mode.
- [x] Exact indicator links, evidence permissions, proposal review and history.
- [x] Drafts/uploads, attendance locks, guide/tip behavior and unaffected dashboards.
- [x] Mobile, 200% text, keyboard, print, build/template and focused regressions.

Private-preview restart and matching after captures remain pending because automatic
approval review could not run. See REPORT_JOURNEYS_DELIVERY.md for the exact blocker.
