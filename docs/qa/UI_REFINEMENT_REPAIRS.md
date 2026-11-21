# Activity and Panel Refinement Repairs — 21 November 2026

## Scope and Delivery

Local implementation of the approved combined repair plan on
`codex/ui-workflow-overhaul`, following analysis → design → implementation → test.
Baseline: `03f8fe8`. No commit, push, deployment, dependency installation, schema
migration, or operational database changes in this pass. The unrelated documentation
DOCX, `output/`, and `tmp/` remain untouched.

Fresh synthetic preview: `http://127.0.0.1:5003/workspace/create/1`.
Coordinator: `coordinator@proposal.example` / `password`.
Restart: `.venv/Scripts/python.exe scripts/qa_proposal_record.py --serve --port 5003`.
This preview uses a disposable in-memory database and generated proposal; stopping
it discards its data. Existing private previews and saved drafts are separate.

## Analysis and Preservation

Older handoff claims were checked against the current code. The proposal remake
had replaced the established date/time controls with native controls and omitted
many required markers. The earlier custom picker also had a required temporary
date field capable of blocking restored schedules. These were defects to repair,
not reasons to introduce a different visual direction.

The existing four creation routes, legacy draft path, capture/source states,
structured proposal fields and exact budget calculations, consent, campus scope,
MOA rules, agency return flow, cover handling, and lifecycle restrictions remain.
Historical specific-volunteer targeting and custom NDA controls were deliberately
removed in earlier approved work; this pass does not reintroduce them.

## Design and Critique

The retained direction is the PSU institutional workspace: existing blue/gold
identity, typography, bordered form surfaces, role shell, and established buttons.
The task is reviewing an approved proposal accurately, rather than decorating the
form. Desktop keeps the section index beside the form. Mobile collapses the index,
stacks controls, and keeps section headings readable. Existing scrollable checkbox
panels remain for skills, SDGs, and notification departments.

| Finding | Severity | Resolution |
| --- | --- | --- |
| Temporary picker field blocks a valid restored schedule | High defect | Canonical named fields remain authoritative; temporary fields do not participate in native required validation. |
| Required sections and missing capture values lack sufficient guidance | High defect | Required/conditional markers, current-step server validation, focusable error summary, field errors, and incomplete/review disclosure states. |
| Incomplete drafts or row actions are blocked by unrelated required fields | High defect | Explicit Save Draft/back/row actions bypass forward validation; publication still validates the whole record. |
| Partner count can be confused with overall participation target | Moderate defect | Total Participant Target plus optional Expected Partner Participants tied to the primary agency. |
| Completed events offer a correction action on Coordinator overview | Moderate defect | The finding remains explanatory; its action is removed only from this overview card. Other report links are read-only and say View Activity Report. |
| Annual evidence navigation implies a previous visit | Moderate defect | Outline View {Campus} Annual Evidence button with trusted scope and selected year. |
| Three-part disclosure heading becomes cramped on narrow screens | Moderate rendered defect | Mobile status occupies a separate aligned row. |
| Preference for a different visual theme or new typography | Optional preference | Not adopted; PSU identity and existing design patterns remain. |

The custom date/time dialog follows the supplied interaction: calendar date,
separate hour/minute controls, AM/PM, Confirm and Cancel, Philippine-time errors.
Arrow/Escape keyboard support, visible focus, native dialog behavior, 44px time
options, scroll containment, and native datetime fallback are retained or verified.
Complete sections collapse; incomplete or uncertain sections open. Section and
error links reveal the relevant disclosure. Conditional markers update without
clearing authored values.

## Data Flow and Attendance Policy

`target_participants` keeps its existing storage and calculation meaning. Optional
partner estimates use Event `audience` JSON keys `expected_partner_participants`
and `expected_partner_agency_id`; proposal snapshots include the displayed value.
Blank means unspecified; zero is accepted; positive values require a primary agency
(or its signed MOA for legacy drafts). Estimates must be whole numbers up to
999,999,999 and cannot exceed an entered total target. Department selection is
campus-scoped and independent from notification departments. Existing unavailable
department values may remain on Edit Activity.

Attendance defaults are derived, never inserted into the attendance table. Set
`ATTENDANCE_DEFAULTS_EFFECTIVE_FROM` once to an authorized ISO timestamp with an
explicit timezone. **Unset disables the policy; this pass does not set the real
environment value.** The example in `.env.example` is documentation only.

Only approved activities with a known end strictly after activation and at/before
the current Philippine time qualify. Missing attendance for confirmed/completed
internal or external registrations displays Not Attended (System Default).
Recorded statuses win. Pending/cancelled registrations, cancelled activities,
unknown end times, and events ending on/before activation do not receive defaults.
Historical missing values stay unknown. Roster filters, counts, report completeness,
CSV/Excel/PDF exports and attendance labels use the same policy. Exports identify
the basis. Recorded presence remains the basis of verified participation and
certificate eligibility; defaults do not manufacture attendance evidence.

## Verification

- 89 proposal/workspace/attendance regression cases passed.
- 67 final acceptance/activity/proposal/UI/help/catalogue cases passed, including
  17 new refinement acceptance cases. Runs overlap; these are not unique totals.
- 60 Chromium groups passed across six viewport sizes (320px through 1440px,
  including landscape), with 200% text checks, no page overflow, agency round trip,
  failed-save retention, row persistence, review/publication and role access.
- A subsequent 25-group interaction run passed after field-error improvements,
  including focused server-error summary, associated title error, native fallback,
  keyboard picker navigation, conditional markers, legacy creation and editing.
- A final focused rerun passed all 17 new acceptance cases and four activity-form
  cases, including workspace and legacy CSV/PDF provenance and Excel output.
  An expanded historical `TestReportingSystem` run stopped at
  `test_director_multiple_campuses[include-6]`: it expects `/analytics` to render
  directly (200), while both baseline `03f8fe8` and current code deliberately
  redirect it to the canonical report workspace (302). That obsolete expectation
  was not used to undo existing navigation or silently changed in this pass.
- Six supported legacy export checks passed. Two additional old export tests fail
  while creating an `admin` fixture; the baseline user-role enum already contains
  only volunteer/coordinator/director. Those fixtures cannot represent the current
  merged Director role and were left outside this repair's scope.
- Tailwind build, 131-template parsing, changed Python/JavaScript syntax and
  `git diff --check` passed. Existing Matplotlib/Pyparsing deprecation warnings
  appeared during report tests; no new dependency was introduced.

Browser artifacts: `.qa-overhaul-temp/proposal-remake/`. The current
`browser-checks.json` represents the most recent interaction run, while viewport
screenshots remain from the preceding full run. No claim of a full-suite,
MySQL, physical-device, or manual screen-reader run.

## Final UI Audit

Reviewed the changed templates and scripts against the current
[Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
retrieved 21 November 2026. Applied UI/UX Pro Max for interaction direction,
Frontend Design for composition, Design Critique before and after rendering,
Ponytail full, Antislop during work, human/mobile checks and Webapp Testing.

- `templates/partials/activity_schedule.html`: pass — named canonical fields,
  labelled controls, native fallback and dialog association.
- `static/scripts/activity-date-picker.js`: pass — restored draft refresh,
  keyboard option navigation, validation/focus and no temporary required field.
- `templates/workspace/proposal_create.html`: pass — preserved routes and values,
  Save Draft/back semantics, disclosure hierarchy and error navigation.
- `static/scripts/proposal-form.js`: pass — disclosure reveal, conditional
  markers, current-step navigation and associated errors.
- `templates/coordinator/edit_activity.html`: pass — shared controls, CSRF,
  preserved policy explanation, campus-scoped department and partner estimate.
- `ui/app.css`: pass — narrow heading reflow, visible focus, contained dialog
  scrolling and 44px time options.

Existing PSU blue/white and muted slate/white pairings also passed the local
contrast checker; no new palette or typography was introduced.

No unresolved in-scope critical or moderate design defect was identified in the
reviewed Chromium flows. The screenshot's exact browser calendar appearance varies
by platform. Extraction still requires human review for missing/ambiguous content;
this repair does not add OCR or electronic approval verification.

## Rollback

No schema rollback or attendance-row cleanup is necessary. Disable the policy by
unsetting its activation value. Keep the new JSON estimate values if reverting
presentation code; older code ignores them. Restore only this pass's files after
reviewing the working diff; never reset unrelated changes or private data.
