# Advance External Registration

Implemented locally on `codex/ui-workflow-overhaul`, 25 November 2026, after the
user confirmed that Coordinators should register external names before an
activity starts while attendance stays restricted to ongoing activities.

## Behavior

The existing named-entry/CSV form is reused. Approved upcoming activities can
accept external registrations, including an upcoming activity with no end time.
These entries create confirmed registrations with no Attendance rows.
An end time must be recorded before attendance can be opened. If a missing-end
activity has already started, both roster entry and attendance remain locked.
Cancelled/unapproved and ended activities cannot accept new external entries.

Add External Participants is available directly on the activity's internal
Attendance page and on its External Volunteers roster. The registration-only
form explains that attendance stays Unrecorded and hides the mark-attended
checkbox. A forged early mark-attended submission is rejected without saving
names or attendance. During an approved activity's valid schedule, the existing
attendance controls and optional mark-attended roster submission remain available.
At the end boundary, both entry and attendance are locked. Existing records,
report calculations, Director permissions and campus restrictions are preserved.

A shared registration-window helper separates roster permission from the existing
attendance-window helper. Both write paths retain final schedule checks and
rollback when the window closes before commit. The missing-end notice links
upcoming Coordinators to Edit Activity Schedule. No database, schema, dependency,
public signup or mobile layout redesign was introduced. No operational schedules,
registrations or attendance evidence were edited during verification.

## Design and Audit

UI/UX Pro Max, Frontend Design and Design Critique retain the existing PSU roster
flow, typography, navy/white palette, controls and spacing, Energy 2 / Rhythm 2 /
Motion 1. Ponytail full reuses the form, CSV handling, permissions and attendance
rules. Antislop core/UI/Human remain active during work.

High critique finding addressed: adding names and recording presence were coupled.
The permissions, explanatory copy and available controls now distinguish them.
Moderate findings addressed: the action is discoverable directly from Attendance;
missing-end guidance provides a real schedule-edit action; adjacent guidance links
have spacing. Empty/error states and entered names are retained. Native labels,
links, buttons and existing focus styles are reused; no color-only state or new
motion. Existing PSU link/button contrast was previously measured at 9.97:1
against white; no color styles changed.

The current Web Interface Guidelines were fetched on 25 November 2026 and applied
to changed templates: associated labels, explicit errors and state guidance,
working native controls, preserved keyboard support and no new overflow.

## Verification

30 distinct focused Python cases passed: 25 external-roster/advance-registration
cases, plus five existing attendance-window cases. Four advance cases were rerun
after route cleanup alongside those five server cases (nine passed). Coverage:
typed/CSV registration, valid/missing end time before start, no early Attendance
rows, forged presence, ongoing attendance, end boundaries, race rollback with
retained input, existing attendance evidence, role/campus authorization and CSRF.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_external_advance_registration.py tests/test_attendance_rosters_ui.py -q --tb=short -p no:cacheprovider --basetemp .qa-director-activities-temp/external-advance
.\.venv\Scripts\python.exe scripts/qa_external_advance_registration.py
```

Four Chromium groups passed with no page errors: entry and missing-end guidance at
1440/1280/1024px, CSRF-enabled keyboard submission producing registrations and zero
attendance rows, ongoing recording followed by ended locking, 200% root font
sizing and JavaScript-disabled registration. All templates parsed. Evidence and
screenshots: ignored `.qa-external-advance-temp/`. Rendered review checked the
form and addressed adjacent-link spacing. CSS build, attendance JavaScript syntax
and whitespace checks passed. The existing local preview was restarted without
seeding/migrating data; local activity 2's Attendance, external roster and entry
form returned HTTP 200 with the action available and no early attendance checkbox.

Antislop gate: Hard PASS (real server/browser flows, locks, native controls and
error/empty-state handling); Purpose PASS (existing roster composition and clear
registration/attendance distinction); Liveliness PASS (retained 2/2/1 PSU direction);
Craftsmanship PASS (shared helper/form, transaction regressions and rendered audit).

## Delivery and Limits

Local only; no commit, push or deployment authorized for this change. Preserve
unrelated `follow_up.html` work. Full-suite, physical-device, screen-reader and
actual browser-zoom checks were not performed. Text enlargement used root font
sizing. Manual roster capacity behavior is unchanged. Rollback restores only this
task's helper, route/form changes, guidance, tests and generated CSS, preserving
existing registered people and attendance. No database rollback applies.
