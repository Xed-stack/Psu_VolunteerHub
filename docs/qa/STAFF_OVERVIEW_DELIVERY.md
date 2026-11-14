# Staff Overview delivery — 14 November 2026

Implemented locally on `codex/ui-workflow-overhaul` in the agreed sequence:
analyze, design, implement, test. Existing working changes and unrelated files were
preserved. No commit, push, deployment, operational database changes, new schema,
application dependency, generated imagery, or broad dead-code cleanup.

## Result

Director: compact heading/scope/five metrics, principal campus comparison, restored
combined campus achievement with university targets separately labelled, grouped
follow-up preview and one delivery trend. Coordinator: five campus metrics,
chronological next-five agenda, urgent work and annual summary in the side column.
Mobile stacks these workspaces and turns campus rows into labelled records.

The five existing KPI definitions are unchanged. Campus rollup uses already-loaded
annual rows: weighted achieved/total obligations, shared AOP/ASP memberships merged
within each campus, distinct obligations retained across campuses, and pending
evidence kept in the denominator. No-target scopes have no achievement percentage.
Activity date/category/profile filters do not redefine annual evidence. Campus
selection narrows the campus comparison/rollup; the original university KPI stays
explicitly labelled. Individual annual table links open exact campus evidence;
all-campus annual summary links open the annual comparison destination.

Current/future campus agenda is explicitly independent of report filters. Ongoing
events link to attendance; full queues preserve ended-event correction reports.
The next-five query is bounded and own-campus. Full calendars, recognition,
Reports, management and individual reminder actions remain connected.

## Skills and installed files

- `codebase-analysis`: `solatis/claude-config`, installed under
  `C:/Users/arlro/.codex/skills/codebase-analysis`. Its companion analysis modules
  and shared Python helper library live inside that skill's `scripts` directory;
  no whole-repository configuration or other skill was imported. The standard
  installer could not install a support-only directory without SKILL.md, so the
  required support files were copied selectively from the upstream archive.
- Existing `frontend-design` was read/applied and left unchanged.
- `design-system`: `anthropics/knowledge-work-plugins`, installed under
  `C:/Users/arlro/.codex/skills/design-system`.
- `webapp-testing`: `anthropics/skills`, installed under
  `C:/Users/arlro/.codex/skills/webapp-testing`; its server helper `--help` was
  checked. Tests reused existing Python Playwright and disposable Flask fixtures.
- UI/UX Pro Max supplied supporting accessibility/responsive checks only.

New skills are installed for subsequent turns and were read directly for this
pass. No new Python/npm application package was installed.

Analysis and preservation checklist: [STAFF_OVERVIEW_ANALYSIS.md](STAFF_OVERVIEW_ANALYSIS.md).
Pre-build wireframes, tokens and component states: [STAFF_OVERVIEW_DESIGN.md](STAFF_OVERVIEW_DESIGN.md).

## Verification

| Completed run | Result |
| --- | --- |
| Staff Overview + existing reimagining/UI regressions | 20 passed |
| Existing workflow overhaul + report query regressions | 57 passed |
| Final staff regressions + complete Jinja template compilation | 7 passed |
| Final staff Chromium pass | 27 checks, no page errors |
| Existing bounded UI polish Chromium pass | 23 checks, no page overflow or JavaScript errors |
| Tailwind build, changed script syntax, diff whitespace | Passed |
| Refreshed actual private preview | Director, Coordinator, Volunteer login/dashboard smoke passed |

Runs overlap; do not sum them into one unique total. Existing plotting-library
Pyparsing deprecations appeared in export tests. The full legacy suite was not
rerun: older assertions expect replaced roles/DOM and direct legacy dashboard
responses. No full WCAG or production capacity claim.

New cases cover weighted campus rollup versus university targets, shared plan
membership, missing evidence, campus scopes, repeated GET values and literal
search preservation, grouped findings with full-queue reminders, chronological
five-item agenda including ongoing actions, own-campus isolation, campus-detail
return links and query behavior. Pure rollup/group presentation issues **zero SQL
queries**. Increasing approved aggregate targets from one to thirteen stays within
the same query bound (at most two extra statements); no per-target query growth.
Existing report builder query-budget tests passed.

Browser coverage: 320, 390, 768, 1024 and 1440px, 844×390 landscape, 200% root text,
reduced motion, conditional quarter/custom-date controls, Enter/Apply submission,
repeated campus filters, Back navigation, guide replay/first use/dismissal/save
failure/missing targets/focus return, information tips by keyboard and touch,
mobile More navigation, draft restoration and failed saves. Representative
Volunteer dashboard/profile/history stayed outside the scoped style changes.

The first visual pass found 200% Coordinator status/date-column overflow; phone
agenda elements now stack. Visual review also removed a floating required marker,
duplicate year/period chips, and excess Coordinator annual-summary space. A first
Director text-size assertion sampled a Plotly resize before it settled; the test
now allows its resize observer to finish before checking overflow. Final checks
pass. Screenshots were visually inspected after these corrections.

Print PDFs generated successfully and text extraction confirms content: Director
three pages, Coordinator two for the disposable fixture. Physical printing,
screen readers, mobile hardware and production/MySQL load remain unverified.

## Review artifacts and local commands

Open `http://127.0.0.1:5000`; the refreshed preview uses its existing private copy
under `.qa-overhaul-temp/`, mail suppressed, no data reseed. Accounts:
`director@psu.edu`, `coordinator@psu.edu`, `student@psu.edu`; preview password
`password`. Restart rotates the session secret; sign in again.

Ignored evidence under `.qa-overhaul-temp/staff-overview/`:

- `before-live/` and `after-live/`: same private preview's real before/after state,
  both staff roles at 1440/390px.
- `after/`: explicitly disposable populated annual/agenda screenshots, empty
  annual/agenda screenshots, 200% text captures, Volunteer comparison, print PDFs
  and `results.json` (27 checks).
- `before-source/`: pre-pass copies of the affected existing source files.
- `working-before.patch`: tracked working diff before this pass, preserving prior
  overhaul changes as reference. It is not a standalone complete repository backup.

Existing all-role browser results remain in
`.qa-overhaul-temp/browser/polish-results.json` (23 checks).

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_staff_overview.py tests/test_ui_reimagining.py tests/test_ui_polish.py -q
.venv/Scripts/python.exe -m pytest tests/test_workspace_overhaul.py tests/test_report_queries.py -q
.venv/Scripts/python.exe scripts/qa_staff_overview.py
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Stop the existing preview before restarting the launcher. Browser tests launch
their own disposable app and never seed the running preview. Windows pytest
fixtures/Chromium may need the local execution permissions used in this session.

## Scoped rollback

No database rollback is required for this pass. Preserve a copy of the current
working tree first. Reverse only this pass's Overview route changes, templates,
staff CSS, conditional-scope script and staff guide copy; use `before-source/`
as comparison, not as a blanket overwrite after further edits. Remove only the
new presenter/components/tests/script and these new documents if rolling back the
whole pass. Rebuild Tailwind and restart the isolated preview. Do not reset/clean
the mixed working tree, delete uploads/databases, or change operational credentials.

Broader website redesign, outstanding panel-suggestion gaps and release actions
remain separate work.
