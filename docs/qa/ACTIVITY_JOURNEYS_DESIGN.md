# Activity Journeys: Analysis and Design

## Analysis before implementation — 14 November 2026

The current Volunteer dashboard (`events.volunteer_dash`) already supplies ranked
positive-interest recommendations, a calendar, upcoming registrations and recent
participation. Its large dark welcome banner and three equally framed supporting
panels compete with the activity workspace. Preserve these datasets and the
recommendations/calendar default rule; change presentation only.

`events.opportunities` owns literal search, campus grouping, pagination and
availability. Retain its filter form and ordering. Replace repeated image fallback
cards with schedule rows; use an optional real cover without reserving an empty
image column. Activity titles and other authored fields are never recased.

`events.opportunity_detail` shares a capacity-loaded event and the current user's
registration. Its registered action incorrectly opens the dashboard. The cancelled
state currently reuses copy saying the activity started. Repair these destinations
and explanations using existing registration/state data, without changing join
authorization. Registration POST still locks and rechecks availability and records
exact accepted policy versions. Do not edit published agreement bodies. The default
fallback agreement needs direct-withdrawal wording rather than cancellation requests.

`workspace.activity` supplies owned activity, registration counts, recorded presence
and attendance-window state. Its side stack repeats the persistent workspace tabs.
Keep tabs, remove duplicates and promote only the action appropriate to the current
schedule. Director remains read-only; Coordinator remains campus-isolated.

`workspace.registration` already provides withdrawal eligibility and the deadline.
Use these rather than infer participation from registration status. Preserve historical
cancellation decisions. Carry return context through the withdrawal confirmation
and return to registration details afterwards, rather than dropping users at Dashboard.

## Design read

A university service portal for volunteers and campus coordinators. Energy 2,
rhythm 2, motion 1. The schedule and actual activity title provide the focal point,
not a welcome banner. PSU blue identifies headings/navigation; gold identifies the
primary participation moment. No gradients, decorative icons or new imagery.

Tokens reuse PSU blue #00408b, deep blue #002b60, gold #f4bd27, ink #111c2c,
slate-50 surfaces and white content. Inter remains the only family. Body 1rem;
headings use the existing type scale. Use 1/1.5rem internal spacing, 2rem between
major sections, compact date blocks, dividers rather than nested cards.

## Wireframes

Desktop Volunteer Dashboard:
```text
Dashboard / Preferred campus        Find an Activity   Show Dashboard Guide
Recommended Activities | Calendar
[Main recommendation list/calendar          ] [Upcoming Commitments]
[date | title, campus, location | View       ] [date | registration ]
Recent Participation: title | status | details         Profile link
```

Desktop detail/workspace:
```text
Back to filtered list
Activity title                         Campus / schedule status
Staff only: Overview | Registrations | Attendance | Documents | Report
[Schedule and location summary              ] [Participation / Next Action]
[Optional existing cover + description      ] [Deadline / capacity / target]
[Skills and SDGs                            ] [Supporting help]
Staff only: cancellation disclosure (reason required)
```

Phone: title → action → workspace tabs → schedule summary → participation action
→ description/requirements. Dashboard shows commitments before recent participation,
with recommendations/calendar remaining the main workspace. Calendar uses a compact
day agenda on phones, full month grid on larger screens; both share existing data.
No fixed bottom CTA that could obscure consent or the existing mobile navigation.

Agreement: narrow reading column; compact schedule summary; full agreement/NDA text;
unchecked consent on fresh GET; linked errors; one Agree and Join action.
Registration: status and next schedule first; visible deadline and eligibility;
attendance evidence separate; historical decisions after the current record.

## Component and state specification

- Journey heading: compact, left aligned, wraps actions; one primary button.
- Schedule row: date, title, campus, location, category, state and details link;
  mobile wraps metadata below title; optional existing cover only on wider screens.
- Facts strip: semantic dl, two/three columns when space allows, one on phone.
- Participation rail: pale PSU surface, top rule; no sticky positioning at zoom.
- Record sections: ruled headings and readable line length; avoid nested panels.
- Buttons reuse native links/forms and existing variants, 44px targets and focus.
- Pending evidence stays Unrecorded; unknown end remains an explicit limitation.
- Empty results retain query recovery; validation/error/saving states reuse existing
  components. No simulated loading for server navigation. Native submission and
  current draft saving/failure feedback remain intact.
- Headline style for fixed labels; sentence style for prose, warnings and errors.

Design review: the approved layouts preserve the existing destinations and data;
the change is hierarchy, action placement and return-path repairs. Staff Overview,
Reports, annual calculations and public homepage remain outside this pass.

## Preservation checklist

- [x] Recommendations, preferred campus ranking, default view and calendar navigation.
- [x] Discovery search, More Filters, chips, paging and filtered Back links.
- [x] Registration states, capacity checks, agreement/NDA and consent exclusion.
- [x] Exact withdrawal deadline, direct withdrawal and historical decisions.
- [x] Activity tabs, rosters, documents, reports, proposal, edit and cancellation.
- [x] Campus authorization, attendance boundaries, drafts and uploads.
- [x] Guide replay, dismissal, Escape/focus; information tips.
