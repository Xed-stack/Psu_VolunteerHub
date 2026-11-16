# Attendance and Participant Rosters

## Analyze completed before application changes

Internal attendance uses `/attendance`, 15 rows per page, campus ownership and
start-inclusive/end-exclusive write checks. It rechecks time before commit. Blank
status leaves existing evidence unchanged. The route docstring still describes
obsolete early check-in and post-event editing; executable behavior is authoritative.
The current template has repeated activity/navigation panels and disabled selects
for locked records. Its unsaved-change script is not connected to the active form.

External attendance uses a campus-owned activity, 25-row pages, and the same
recording boundary. One handler currently combines attendance updates and named
group creation. CSV input takes precedence over multiline text; names are required,
email optional, at most 100 people/100000 input characters. Attendance batches are
limited to 100. Keep these parsing rules and final transactional boundary check.

Registration records are separate, read-only, newest first and available to the
Director and owning Coordinator. They preserve cancellation history and historical
named invitees. Existing workspace identity/navigation should remain shared.

## Design completed before application changes

PSU coordinators need a readable working roster during an event, with an explicit
deadline and one save action. Use existing Inter, blue #00408b, deep navy #002b60,
ink #111c2c, slate metadata #475569 and white surfaces. Gold remains in the shell.
No decorative cards, extra metrics, bulk marking buttons or competing action stacks.

Desktop wireframe:

```text
Shared Activity Identity and Workspace Navigation
Internal Attendance                     Attendance Help
Starts … | Ends … | Philippine Time
Attendance Open — Record before [exact end]
Internal Volunteers | External Volunteers
Search                           Attendance Status   Apply / Reset
Matching results, alphabetical order
Volunteer                Registration         Attendance
Name / email             Confirmed            [Unrecorded]
Name / email             Confirmed            [Attending]
Unsaved changes         Save Attendance
Previous Page                              Next Page
```

Phone: same hierarchy; labels and controls stack, participant rows become labelled
blocks without horizontal scrolling. All controls remain 44px. Existing mobile
navigation and sticky-header offsets are retained. Locked pages use text status,
specific upcoming/cancelled/ended/missing-schedule explanations and a Combined
Report link. No disabled input maze. No automatic absent/completed judgments.

External roster has the same workspace plus Add External Participants. Its dedicated
screen has group name, multiline or CSV input, visible required-name/format guidance,
the existing optional mark-attending checkbox, and Save Named Roster. Keep ordinary
values on validation failure and clearly require file reselection. No autosave for
attendance or this entry form; warn before leaving unsaved input. Existing save and
duplicate-submit feedback is reused. Empty/filter-error/save-failure states are
visible. No-JavaScript access uses native forms and server validation.

Registration screen has a compact audience disclosure (including historical invitees),
Search/Status filters and a single list. Form-type fields/statuses use explicit
Newspaper Case; names, event titles and authored departments remain unchanged.

## Preservation checklist

- [x] Role/campus authorization, CSRF and forged-ID rejection.
- [x] Registrations separate from evidence; unrecorded/absent/excused distinct.
- [x] Schedule/cancellation locks, final pre-commit check, no partial writes.
- [x] Existing CSV rules, group membership and mark-attending option.
- [x] Existing POST interfaces and batch limits; one shared external write handler.
- [x] Filter/pagination/return context, legacy links and matching reports.
- [x] Unsaved warnings without draft/credential/consent persistence.
- [x] Mobile/no-JavaScript/keyboard/print/empty/error states.

Baseline/final artifacts: `.qa-overhaul-temp/attendance-rosters/{before,after}/`.

## Implementation

The three roster templates now use shared heading, timing, roster navigation,
status and page-save components. Existing recorded attendance has only the three
recordable options; an empty choice is offered only where evidence is unrecorded.
Blank POST values still leave records unchanged. Locked records display plain text.
Print retains roster tables and saved status text while hiding editing controls.
Director registration records link to authorized Reports Help, rather than the
Coordinator-only attendance article. Historical invitees remain in the audience
disclosure. Labels are explicit; authored titles/names/departments are not recased.

`/workspace/activities/<event_id>/external/new` adds GET/POST entry using the same
decorated, campus-owned external handler. No duplicate parser or write service.
Legacy POSTs still work. Validation retains text/group/checkbox values with linked
inline errors and a file-reselection explanation. Expiry returns HTTP 409 with an
unsaved-input recovery view; the transaction rolls back and files are not retained.

`roster_link` maps existing internal/external search names, preserves supported
filters/pages on return, resets pages when switching roster type and validates
activity return destinations. Save actions keep the roster context. The external
list now uses the existing shared pagination helper to clamp emptied pages. Report
links carry the filtered roster URL back. Existing report services/calculations and
exports are unchanged. Schedules use explicit Philippine-local ISO offsets; the
existing Intl helper enhances tagged schedule text, with server/no-JavaScript fallback.

The existing attendance script is connected to active forms, including the new entry
screen. It announces dirty state, warns before leaving, handles restored-page state
and retains the warning after a validation failure with ordinary input. No new bulk
controls and no attendance autosave. Native submission/loading/duplicate prevention
remain shared. Help explains explicit page saves and the separate entry screen.

## Verification completed 16 November 2026

- **21 new acceptance cases passed** across focused runs: entry/legacy POSTs,
  preserved query context, CSV precedence/BOM, named groups and optional attendance,
  retained validation values, invalid UTF-8, role/campus access, CSRF, forged IDs,
  blank-as-unchanged, all locked states, literal `%`/`_` search and escaped authored
  markup, exact start/end, invalid external batches and final-check rollback for
  internal attendance, external attendance and new group insertion.
- **49 existing workspace regressions passed**, including drafts/uploads/secrets,
  activity publication, attendance boundaries, withdrawal, imports and PDF/Excel/CSV
  report exports. The combined initial run had 64 passed and one new test-selector
  failure; that selector was corrected and all new cases subsequently passed.
  Existing tests had no failures. Existing Matplotlib/Pyparsing deprecation warnings
  in PDF tooling remain; no calculation or plotting tooling was changed.
- **37 final Chromium groups passed** with disposable in-memory fixtures. Four
  screens at 320, 390, 768, 844 landscape, 1024 and 1440px; unsaved cancellation,
  explicit save/restoration, page/search preservation, report navigation, native
  no-JavaScript attendance/roster saves, linked validation/focus and post-error
  leave warning, text at 200% with unbroken long names, unobscured keyboard focus,
  44px controls, print visibility, all locked states and expiry after form load.
  Typed names remained available after rejected expiry. No JavaScript page errors.
- **6 baseline screenshot groups** captured before application changes.
- Tailwind build, **122 templates**, changed Python compilation, both changed-script
  syntax checks and Git whitespace check passed. Existing app design tokens retained.
- Measured PSU text on the pale blue timing surface: **9.16:1**. Existing blue/white
  and slate/white combinations remain 9.97:1 and 7.58:1. Status/selection use labels
  and borders as well as color. No motion or new imagery/dependencies introduced.

Current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
fetched/reviewed 16 November 2026. Changed layouts/scripts checked for native forms,
associated labels, status announcements, visible errors/focus, explicit submit,
URL state, long-content reflow, timezone interpretation, target sizes and print.
No outstanding in-scope finding. Antislop delivery gate passed: existing PSU tokens,
one operational timing notice, readable roster rows, no decorative metrics/cards,
no invented data and no hidden essential warning. UI/UX Pro Max guided feedback and
labels; Frontend Design guided composition. Ponytail full, antislop core/UI/human/
mobile, Webapp Testing and current Web Design Guidelines were supporting skills.

Physical devices, manual screen readers, actual browser toolbar zoom, MySQL and the
full historical test suite were not tested. 200% above means CSS text sizing.
Unexpected infrastructure failures still use the established application error
handling; attendance rejected after the deadline remains locked, with corrections
handled by printed reports. There is no background autosave of attendance.

## Evidence and repeat commands

Screenshots/results: `.qa-overhaul-temp/attendance-rosters/{before,after}/`.
Representative files: `internal-1440.png`, `external-390.png`,
`add-external-1440.png`, `registrations-390.png`, `external-after-add.png`,
`*-200.png` and `*-{upcoming,ended,cancelled,missing}.png`.
Browser checks are recorded in `after/results.json`.

Build: `npm run build`.
Backend: `.venv/Scripts/python.exe -m pytest tests/test_attendance_rosters_ui.py tests/test_workspace_overhaul.py -q`.
Browser: `.venv/Scripts/python.exe scripts/qa_attendance_rosters.py --stage after`.
Use task-local pytest temporary folders/normal Windows process permissions as needed.

## Local delivery and scoped rollback

Private preview refreshed at `http://127.0.0.1:5000/` using the existing isolated
launcher and database/uploads. Existing Coordinator preview activity 7 returned
200 for registrations, `/attendance?event_id=7`, external attendance and the new
entry screen. No fixture participants were inserted into private preview data.
Start from Activities and choose the relevant activity/roster; edit controls are
available only when its actual schedule permits them.

Rollback only this pass: remove the external-new route alias, entry rendering and
roster-specific navigation additions; restore the previous roster templates and
scoped styles, shared attendance-script changes and two Help paragraphs. Remove the
new roster components/form and schedule-only Intl enhancement if unused. Rebuild
Tailwind and restart the isolated launcher. Preserve earlier Notifications/Drafts,
profile, sidebar, activity forms and all unrelated working changes; do not reset
shared files wholesale. No schema/data rollback is required.

Local/uncommitted on `codex/ui-workflow-overhaul`. No migrations, new libraries,
operational database changes, commits, pushes or deployment.
