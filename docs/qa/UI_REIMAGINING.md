# UI reimagining — local delivery, 14 November 2026

This pass implements the approved UI reimagining on `codex/ui-workflow-overhaul`.
UI/UX Pro Max was the sole design and review skill for this pass. Earlier skill
audits remain dated evidence, not additional design constraints applied here.
The existing working changes were preserved; no commit, push, deployment,
operational database change, schema migration, new package, imagery, or skill
installation was performed. The unrelated system-documentation DOCX is untouched.

## Design and navigation

The design uses PSU navy/blue and gold, Inter, existing identity assets and
photography, white workspaces, and task-led information hierarchy. The local
skill's data-dense dashboard direction informed comparison tables and readable
lists. Generic hero templates, alternative fonts, and unrelated product palettes
were rejected. Body text remains 16px; navigation and primary controls provide
44px targets. Native forms, disclosures, links, and server-rendered pagination
are retained.

Desktop navigation groups daily work, planning/evidence, and support. Mobile
provides frequent destinations and a More drawer. The shared activity context
keeps the activity name, workspace tabs, breadcrumbs, and return location visible.
Substantial tasks have dedicated screens rather than larger dashboard dialogs.

## Old-to-new feature checklist

Every destination below is linked in the UI. Director sees university data;
Coordinator is restricted to their campus; Volunteer sees their own records.
Back links use validated local return URLs; list filters and pages survive detail
navigation. Read-only historical material does not restore retired workflows.

| Useful capability | Visible destination and authorized entry | Return path / implementation |
| --- | --- | --- |
| Director overview and campus comparison | Overview → campus chart or text drill-down → `/workspace/campuses/<id>` | Campus Back link restores overview/results scope; Director only. |
| Coordinator campus overview | Overview → activities, Reports, annual progress | Shared selected navigation and scoped Back links. |
| Director and Coordinator calendars | Sidebar Calendar; Overview → Open calendar | `/director/calendar`, `/coordinator/calendar`; activity opens workspace and returns to calendar. |
| Needs Attention | Sidebar or Overview → `/workspace/follow-up` | Scoped evidence, next action, activity/report/annual-plan links with return context. |
| Campus follow-up recommendations | Needs Attention and campus details | Existing goal-guidance service plus current activity facts; ongoing attendance entry, ended report/printed-correction guidance. |
| Notify Coordinator | Director follow-up items with an active recipient | Existing POST endpoint, authorization, CSRF, current evidence revalidation, unread duplicate-reminder suppression; no automatic notification. |
| Five headline measures | Overview and Reports results | Approved, conducted, accounts, verified attendees, AOP achieved; clickable detail links and separate information triggers. |
| Previous-period comparison | Overview/results for compatible period measures | Equal preceding period; all-time accounts and annual goals retain separate scopes; all-record scope has no delta. |
| AOP/ASP and pending evidence | Overview annual summary → Annual plans | Campus comparison, indicators, evidence/proposals/review workspaces remain linked; missing goals say Not set. |
| Annual recognition | Director Overview → Outstanding recognition → `/workspace/recognition` | Award-year selector, calculation explanation, Back; existing aggregator reused. |
| Detailed reporting | Reports directory → `/workspace/reports/results` | Registration/internal/external/presence/completion/rate/target details, activity links, pagination and matching exports. |
| Advanced report filters | Results/overview Report filters | Literal title search, category, SDG, sex, affiliation, conducting department, attention, include/exclude campuses, approved/conducted. Chips preserve other filters. |
| Explicit reporting scope | Report filters | Quarterly, semi-annual, annual, custom dates, all records. Trend bins identify years; long spans group by year. |
| Historical records and graphs | Reports → `/workspace/reports/historical` | Year/range, campus, activity type and literal search; campus comparison and CSV/Excel/PDF preserve scope. |
| Profile insights | Reports → `/workspace/reports/people` | Separate account-role, skill and interest summaries; no participation-breakdown panels. |
| Registration history filters | Volunteer My events → `/workspace/registrations` | Campus, category, dates, status and literal search; detail Back restores query/page. |
| Exact withdrawal deadline | Registration detail → Withdraw | Philippine date/time and closed reasons on details/confirmation; direct withdrawal retained. |
| Previous cancellation decisions | Registration detail | Read-only request reason, status and review note; no approval processing restored. |
| Optional cover and event NDA | Create Activity step 3 → final review | Private staged cover, validation, restored draft reference; NDA text before publication; version identifiers internal. |
| Separate capacity and numeric target | Create review, activity overview, results | Capacity, participant target and recorded presence remain separate facts. |
| Activity child workspaces | Activities → overview → registrations/attendance/documents/report | Persistent identity/tabs and contextual Back link; internal/external rosters remain distinct. |
| Volunteer recommendations/calendar | Volunteer dashboard | Existing active-upcoming-registration default rule, preferred-campus priority and positive-interest cosine ranking retained. Registration details linked from commitments. |
| Completed public highlights | Public home | Approved activities with known ended schedules; historical totals identify their source and known-count coverage. |
| Management and imports | Management task directory → dedicated destination | Accounts, imports, policies, categories and settings; existing validation preview/confirmation reused. |
| Help, guidance and account screens | Shared support/profile navigation | Role-specific tours, replay, tips, drafts, profile, partners, notifications, errors and public/auth screens share the visual system. |

## Compatibility and calculation decisions

- One authorized reporting dataset supplies values, charts, table pages and
  CSV/Excel/PDF exports. Excel and PDF include graphs and readable scope labels.
- Legacy dashboard/Analytics URLs preserve supported dates, activity, category,
  campus and other filters. Legacy `department` meant participant affiliation and
  is translated to `affiliation`; the new workspace `department` remains the
  conducting department. Historical links preserve year ranges.
- Attendance presence after a known approved end establishes completed
  participation. Unmarked/excused records remain distinct; incomplete or legacy
  schedules do not create rates or target judgments. Participant-profile filters
  do not falsely judge the whole event's numeric target.
- Historical missing participant counts remain Unknown. Aggregated known counts
  are labelled as recorded participations, not unique people. Recognition uses
  actual recorded presence for completed-participation tie-breakers.
- Annual achievement and pending evidence retain their annual scope even when
  the activity period changes. All-record reports do not imply a previous period.
- Server drafts preserve allowlisted values and private upload references,
  exclude secrets and unsubmitted consent, and clear on successful publication.
  Long presentation-only Back URLs cannot make a draft key exceed its limit.
- Direct withdrawal, locked attendance (including bulk/import paths), permanent
  activity records, existing consents, campus isolation and consolidated Director
  permissions remain in force. No obsolete cancellation approval was reconnected.

## Verification evidence

Completed runs are overlapping evidence, not additive test totals:

- Existing workflow/UI regressions: 54 passed initially; one obsolete UI-selector
  assertion was updated to inspect activity heading links. Its six-case UI module
  passed afterward. The 49 workflow cases passed in that initial run.
- Reimagining, UI polish, report queries and profile/settings: **51 passed**.
- Final reimagining/UI polish: **14 passed**, including complete Jinja template
  compilation, scoped routes, filters, exports, history, cover/NDA drafts and
  cleanup. Existing Matplotlib/Pyparsing deprecation warnings remain.
- Focused annual-goal/queue checks: **2 passed**.
- Full Chromium matrix: **245 checks**, no recorded overflow or JavaScript errors.
  This preceded final small navigation, scope-label and focus refinements.
- Later representative-screen Chromium pass: **35 checks**, no errors.
- Final bounded Chromium polish pass: **23 checks**, no errors; guide preferences,
  missing targets, replay/Escape/focus, tips, failed saves, long return-context
  drafts and all-role mobile More navigation.
- Separate draft browser pass: **9 checks**, passed.
- Tailwind build, JavaScript syntax checks and `git diff --check` passed.
- Refreshed isolated preview: all three role logins and dashboards passed.

One final test invocation initially failed before database fixtures ran because
the sandbox could not read pytest's existing Windows temporary directory. It was
rerun with the required local access; this was an environment/setup failure.
No application defect was inferred from that interrupted invocation.

Chromium covers 320, 390, 768, 1024 and 1440px, portrait and 844px landscape,
200% text sizing, reduced motion, native keyboard interaction and focus return,
role guides, touch/click disclosures, contained calendars/tables and print output.
Screenshots were visually inspected and layout defects corrected (KPI wrapping,
chart date labels, mobile footer clearance, guide heading focus and duplicate
authentication branding).

Artifacts are ignored local files under `.qa-overhaul-temp/browser/`:

- `before-reimagining/` contains the prior UI captures.
- `director-1440-workspace-overview.png`,
  `coordinator-390-workspace-overview.png`,
  `volunteer-390-volunteer_dash.png` and other role/width captures show this pass.
- Public home/login, Reports/results/recognition, creation, annual-plan and
  profile/history captures provide representative secondary screens.
- `results.json`, `showcase-results.json`, `polish-results.json` record assertions;
  PDFs record activity/AOP/report print checks.

## UI/UX Pro Max review checklist

| Review area | Result / evidence |
| --- | --- |
| Intentional hierarchy and consistency | Institutional shell, single primary task/action, grouped navigation, task directories, readable comparisons and activity lists. |
| Typography and contrast | Inter/16px body, navy/blue on white, dark text on gold, restrained borders; labels/status meaning do not rely on color. |
| Keyboard, focus and labels | Native controls and labels, skip link, visible focus (gold on navy), Escape and focus restoration; bottom navigation clearance. |
| Touch and responsive layout | 44px controls, mobile More menu, safe-area spacing, wrapping KPI grid, contained calendars/tables; browser matrix above. |
| Help and chart alternatives | Role-relevant tours and replay, supporting click/touch/keyboard tips, text drill-downs and value disclosures; essential deadlines/warnings stay visible. |
| Form and async states | Inline errors/summary, save feedback and failed-save handling, restored references, empty-result recovery and explicit role submission retained. |
| Motion and assets | Reduced motion respected; existing icons/photos/logo; no generated images or new dependency. |
| Data density and delivery | Paginated lists, compiled Tailwind, batched attendance facts; no claim of production-scale capacity certification. |

Limitations: this is local Chromium/SQLite verification, not a physical-device,
screen-reader, MySQL/staging, or production load certification. The complete
legacy suite was not rerun; some old tests encode replaced roles/screens. Report
facts are batched, but matching rows are currently materialized before report
pagination; very large datasets still require a measured capacity review. Existing
library deprecation warnings were not addressed by this UI pass. Missing real
evidence stays pending rather than being filled to make dashboards look complete.

## Review, build, test and rollback

Open `http://127.0.0.1:5000`. The ignored local launcher uses its existing private
database copy and private uploads, suppresses mail, and does not change operational
credentials. Preview accounts are `director@psu.edu`, `coordinator@psu.edu`, and
`student@psu.edu`, each with password `password`. Restarting rotates the preview
session secret, so sign in again after refresh.

From the repository root in PowerShell:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_ui_reimagining.py tests/test_ui_polish.py tests/test_report_queries.py tests/test_profile_settings.py -q
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --showcase-only
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Use the full browser script without flags for the longer matrix. Stop an existing
preview before restarting it; do not start two servers on port 5000. The launcher
and preview artifacts are local-only and excluded from delivery commits. Tests
need access to pytest's temporary directories; Chromium needs permission to launch.

There is no new database migration to roll back. Source rollback must preserve
earlier uncommitted polish and unrelated changes: save a copy of the current diff
and all new source files, then reverse only the reviewed reimagining hunks and
rebuild Tailwind. Do not use blanket `git reset --hard`, `git clean`, or replace
operational data with a preview copy. Commit/push/deployment remain separate
release actions.
