# Minimal filters and Newspaper Case — 14 November 2026

## Analysis before design

Active filters are server-rendered GET forms. Existing `query_url`, `linked_url`
and `back_url` preserve list context; matching/report exports use authorized
services. The active route inventory includes 63 constant route templates plus
shared layouts/partials and error pages. Legacy role dashboard templates are not
current landing screens. No stored content or reporting calculations need changing.

| Interface | Primary | More Filters | Compatibility |
| --- | --- | --- | --- |
| Report results | Year, period, delivery, activity search, Director campus | Department, exact activity, category, follow-up, SDG, sex, affiliation, campus include/exclude | Keep every existing GET name and repeated campus values. |
| AOP | Year, authorized campus | None | Omit unrelated controls; exports retain `report=aop`. |
| Staff Overview | Year, period, authorized campus | Link to Reports | Share conditional quarter/half/date behavior. |
| Activity lists | Search and schedule tabs | Category and authorized campus | Volunteer/public retain campus checkbox include/exclude and ranking. |
| Registration history | Search, status | Campus, category, dates | Preserve detail return query/page. |
| Rosters | Search, attendance/registration status | None | No new unsupported filters. |
| Historical | Search, year, Director campus | Year range, activity type | Preserve year/range intersection; do not populate range from year. |
| Annual evidence | Year, target scope, plan | Program, office, status | `campus` differs from Reports `campus_id`; retain sample/basis. |
| Accounts | Search, campus | Role, affiliation | Consolidate duplicated campus/search forms, retain active tab. |
| People/partners/recognition | Existing essential scope/search | None | No empty disclosure. |

Annual goal facts stay separate from activity-period/profile filters. Coordinator
scope comes from the signed-in account. Search stays literal, case-insensitive,
button/Enter submitted, with no suggestions/logging. Export column names are a
compatibility interface and remain unchanged.

## Design before implementation

Use the existing PSU blue/gold, Inter, white surfaces and compact staff controls.
Shared native components: filter grid, one More disclosure, active-field count,
one Apply/Reset row, applied chips and conditional period fields. No framework or
package. Frontend-design provides hierarchy; design-system provides states and
reuse; Search UX provides refinement/empty-state guidance.

```text
Report Filters · [year] · [period]
Reporting Year | Period | [Quarter / Half-Year or From / To]
Activity Delivery | Search Activities | [Director Campus]
More Filters (N Active)                         [collapsed]
  Department | Exact Activity | Category | Follow-Up
  SDG | Sex | Affiliation | Campus Selection + checkboxes
Apply Filters   Reset Filters
```

Desktop uses up to three columns; tablet two; phone one. Search is wide enough
for activity titles. Controls remain 44px, body 16px, gaps 12–16px. Reuse tokens,
subtle borders, no decorative card nesting or animation. Keep primary scope
readable and explanations brief. Specialist counting explanation lives beside
those fields. Do not add a third campus disclosure.

Primary Report Filters remain visible by default; the outer container can still
be collapsed manually. More is closed after navigation/submission; applied specialist-field count and
chips stay visible. It opens automatically for field validation. Closed controls
remain enabled. Native server errors retain scope and existing recovery behavior.
Quarter/half controls offer only valid segments. Dates appear for custom periods;
resolved legacy month scopes populate their normalized dates. A small head marker
allows initial hiding only when JavaScript executes; without JS the native inputs
remain reachable. The existing script then controls relevant fields and options.

## Editorial specification

Headline style for navigation, headings, controls, fixed options, table headings
and accessible action names. Lowercase articles, conjunctions and short
prepositions unless first/last. Examples: Report Filters, More Filters, Apply
Filters, Back to Reports, Recorded Sex, Follow-Up, Semi-Annual.

Sentence style for instructions, descriptions, tooltips, validation/success and
empty-result messages. Leave authored names/titles, departments, agencies,
agreements/policies, filenames, official terminology, acronyms and machine values
alone. Make source edits only; no runtime title-casing of data or CSS transform.
Review fixed labels supplied through Jinja macro arguments, route dictionaries
and JavaScript as well as ordinary HTML text. Align guide titles with controls.

## Preservation and validation checklist

- [x] Existing GET names, repeated campuses, aliases and list return paths.
- [x] More counts, persisted selections, remove-one and complete reset.
- [x] All period modes, normalized legacy dates, errors inside closed details.
- [x] Literal search, authorized campus scope, unchanged KPI/evidence definitions.
- [x] Screen/export agreement and established export fields.
- [x] Active interface casing without changing authored/stored data.
- [x] 320–1440px, landscape, 200% text, keyboard/touch/focus and guide labels.
- [x] Draft, attendance, consent and withdrawal regressions.

Before source snapshots and private-preview captures are ignored under
`.qa-overhaul-temp/minimal-filters/`. Historical QA runs are not evidence for this
pass. Broad cleanup, new migrations, deployment, commit/push and operational data
changes are excluded.
