# Staff Overview analysis — 14 November 2026

Analysis completed before application changes using the installed
`codebase-analysis` workflow. Its focused survey delegation was limited to annual
data and test constraints; no repository-wide workflow configuration was imported.

## Findings grounded in current source

| Finding | Source | Decision |
| --- | --- | --- |
| Both staff roles render one Overview template after legacy redirects. | `app/routes/workspace.py:overview` | Retain route and shared authorization; compose role-specific content. |
| The annual KPI uses university targets when campus is absent. Campus summaries are separately loaded. | `app/services/workspace_reports.py:workspace_report` | Preserve KPI definition, explicitly label scope; add a distinct campus rollup. |
| Earlier campus rollup is gated to an endpoint now redirected away. | `app/annual_goals.py:dashboard_context`, HANDOFF November 1 campus-summary fix | Reuse `summarize` on loaded campus rows, not the obsolete endpoint-conditioned presenter. |
| Annual summaries already batch mappings/results and cache per request/year. | `app/annual_goals.py:_university_summaries`, `comparisons` | No per-campus calls or extra evidence queries for presentation. |
| Upcoming query takes four future events independently of report scope. | `app/routes/workspace.py:overview` | Five-row campus agenda, explicitly independent of report period; include ongoing events with known ends. |
| Tall hero/KPIs, full report filters, repeated findings, two charts and shortcut panels compete. | `templates/workspace/overview.html`, `ui/app.css` | Compact heading/KPIs/controls; role-led primary workspace; contextual links. |
| Tour targets refer to charts and old workspace groupings. | `static/scripts/first-use-tour.js` | Keep persistence/focus runner; update staff steps and visible target IDs. |
| Shared UI styles also affect Volunteer, Reports and campus details. | `ui/app.css`, `workspace/reimagined_components.html` | Scope new rules under `.staff-overview`; do not globally shrink controls or panels. |
| Historical query budgets cover older endpoints or shared report builders. | `tests/test_report_queries.py`, `test_performance_workflows.py` | Record as historical evidence; measure current Overview using identical populated fixtures. |

Annual rollup: each campus's already-merged shared obligation counts once overall,
and once in each relevant AOP/ASP membership. Do not merge obligations across
campuses. Rate is total achieved / total obligations; pending stays in denominator,
and no targets means unavailable. University targets remain separate. Activity
filters never turn annual evidence into activity-scoped annual calculations.

## Preservation checklist

- [x] Five KPI definitions unchanged; campus and university annual scopes labelled.
- [x] Campus/year links reach correct details; query values and safe Back links retained.
- [x] No-target and unknown evidence remain explicit, never fabricated zero achievement.
- [x] Follow-up detail queue, reminder authorization/CSRF/deduplication retained.
- [x] Full calendars, recognition, Reports and management remain reachable.
- [x] Coordinator agenda is own-campus and chronological; attendance timing preserved.
- [x] Guide dismissal/replay/keyboard/focus retained with new visible targets.
- [x] Drafts, consent, withdrawals, permanent activity records remain untouched.
- [x] Batched annual evidence and report/export scopes preserved.

## Codebase understanding summary

**Structure:** Flask workspace routes orchestrate shared reporting services and
Jinja components; Tailwind compiles the existing stylesheet. No frontend service
or new API is needed.

**Patterns:** Authorization is server-side; GET scopes are shareable; evidence is
batched and cached per request. Native links/forms and existing guide/tip runners
provide interaction.

**Flows:** Overview obtains the authorized report context, derives follow-up
findings and pure annual/group presentation, then adds a bounded own-campus
Coordinator agenda. Reports/exports retain their existing filtered dataset.

**Decisions:** Add a query-free presenter instead of reviving an endpoint-specific
legacy dashboard helper. Keep the original AOP headline and explicitly separate
the restored campus rollup. Scope visual rules to staff Overview.

**Context:** Preserve the user's existing mixed working changes and earlier
business-rule fixes. This pass repairs hierarchy and one presentation regression;
it is not a new reporting calculation or deployment project.

## Baseline and deferred cleanup

Fresh before screenshots use the existing private preview and live in
`.qa-overhaul-temp/staff-overview/before-live/`. Pre-pass copies of files changed
by this pass and the prior working diff live alongside them for scoped rollback.
Existing reimagining QA captures are retained separately as dated evidence.

Prior completed evidence: 51 focused tests, then 14 focused tests; full 245 browser
checks, later 35 and 23 bounded checks. These are overlapping historical runs, not
proof for this pass. Plotting-library deprecations and obsolete legacy dashboard
DOM assertions are known limitations. No production load claim.

Potential cleanup only: legacy dashboard templates, endpoint-conditioned annual
presentation, repeated chart/panel composition. They may still support compatibility
or tests; broad deletion is outside this pass. Panel-suggestion gaps remain separate.
