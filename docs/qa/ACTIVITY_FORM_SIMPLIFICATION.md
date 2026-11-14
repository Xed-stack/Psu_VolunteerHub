# Activity Form Simplification

## Analysis and design before implementation — 14 November 2026

The four-step creation route stores an allowlisted `activity:new` draft. Skills use
catalogue IDs; Edit Activity currently submits skill names. Departments use campus
affiliation strings, SDGs use IDs. Keep these contracts, replacing only their controls.
Native checkboxes are already compatible with drafts.js, including empty arrays.
The new component must update after draft:restored and reset, without firing changes
on initial render. Local filtering must not submit the activity form.

Cover staging currently runs on step 3 and publication consumes the private staged
reference. Move the direct upload handling to step 2; existing staged cover references
stay valid. Browser staging remains on the same upload endpoint and draft key.

Custom agreements, NDAs and named invitations are currently accepted by creation and
Edit Activity. Removing their markup alone would leave forged creation values active
and cause omitted edit fields to erase historical consent settings. Remove acceptance
of these creation fields and leave persisted consent attributes untouched on edit.
Strip obsolete fields from activity-specific saved drafts on access/save, preserving
all other fields, proposal metadata and `_files`. Generic policy forms remain intact.

Audience departments continue to guide notifications, not registration eligibility.
No selection keeps the existing behavior; do not silently notify the entire campus.
Existing named audience records and historical policy/acceptance data remain stored.

## Design read

PSU campus activity forms for coordinators, energy 2/rhythm 2/motion 1. Keep Inter,
PSU blue #00408b, deep blue #002b60, gold #f4bd27, ink #111c2c and white/slate
surfaces. Fixed labels use Newspaper Case; source department, skill and SDG names
remain authored catalogue content. No new libraries, imagery or decorative motion.

Desktop / tablet:
```text
Activity Details
Title / Description
Activity Cover Image (optional, always visible; saved filename / replace)
Schedule / category / capacity / withdrawal deadline
Required Skills: selected count + selected items
[Find Skills…                    ] [Filter Options] [Clear Selection]
[bounded checkbox list, labels wrap]
SDGs: selected count + selected items
[Find SDGs…                      ] [Filter Options] [Clear Selection]
[bounded checkbox list with SDG numbers and full names]
```

```text
Audience and Partners
Participant Type / Conducting Department
Audience Departments: searchable checkbox panel, campus caption
Numeric Participant Target / Existing Partner or MOA
Previous Step                                    Save and Continue
```

Phone: single column with full-width option rows and wrapping selected-item buttons.
Each checkbox row is at least 44px. The search/filter/clear controls wrap; the option
list scrolls internally without clipping labels. Selected items remain outside the
filtered list. Selected summaries show up to five initially, with a native disclosure
for the remaining selected items. Cover upload never sits inside a disclosure.

Component states: unselected, selected, filtered, zero matches, empty catalogue,
restored draft, invalid required SDGs and intentionally cleared selections. Use native
fieldsets/legends and labelled checkboxes. The filter input has no submitted name;
Enter filters only that option list. Hide enhancement-only controls without JS and
show every checkbox. Keep server validation authoritative. No query logging/network
search. Draft saving/failure/upload feedback reuses the existing runner.

## Verification and preservation

- [x] Removed fields cannot affect new publication or overwrite legacy edit consent.
- [x] Department notifications remain campus-scoped and do not restrict registration.
- [x] Search/filter, selected summary/removal, clear, keyboard and no-JS operation.
- [x] Draft restore, empty selection, failed validation, staged cover and step navigation.
- [x] Default agreement still required; legacy NDA/acceptance remains intact.
- [x] Tailwind/templates, focused regressions, mobile/200% text, audit and preview.

## Implemented locally

The cover upload is always visible below Description in creation step 2 and in Edit.
Server multipart staging moved from step 3 to step 2; existing staged references stay
valid. Duplicate restored-cover notices are suppressed when the server already shows
the filename. Step 3 now contains participant type, conducting department, the new
department selector, participant target and partner/MOA selection.

One shared Jinja partial and a small native JavaScript enhancement replace the
department/skill multiselects and the long SDG checklist. Skills/SDGs use the same
panel in Edit; audience departments remain in their existing creation step. There
is no Ctrl/Command selection, external search, suggestions, logging or new dependency.
Hidden matching rows stay enabled and submit their selections. Unavailable saved
choices are visibly marked and removable rather than silently disappearing.

Removed custom NDA/agreement and named-invitee controls from creation/edit/review.
New publication ignores stale/forged values. Activity-specific draft cleanup preserves
ordinary fields, private proposal metadata and staged files; unrelated form drafts
are untouched. Editing never writes the existing policy/NDA/version/acceptance or
historical audience attributes. Default agreement acceptance still applies to new
registrations; legacy registration consent behavior remains supported.

Edit validation errors now retain full choice catalogues and submitted arrays,
including intentional empty selections. Edit skill names map directly to existing
catalogue records so a name containing a comma cannot create unintended skills.

Browser verification exposed a pre-existing clean-draft submission issue: retrying
`requestSubmit` during the original native event's microtask checkpoint could be
ignored by Chromium. The retry now runs in the next task, retaining validation and
upload/save waits. Inline group errors sit beneath their checkbox panel.

## Verification evidence

Completed runs overlap; do not add them as unique coverage:

- **17 pytest cases passed**: new activity-form tests, UI-reimagining and activity
  journeys. Includes cover restoration/publication/cleanup, ignored obsolete fields,
  default agreement acceptance, legacy consent retention and campus notifications.
- **Six final pytest cases passed**: activity forms (including punctuation in skill
  names), full template compilation and legacy agreement/NDA validation.
- **50 workflow/registration cases passed before one pre-existing failure** in
  `test_join_confirmation_is_database_backed_and_refresh_safe[False]`. That old test
  expects the opportunity-details redirect; the previously approved activity journey
  now redirects successful registration to its registration record. This pass did
  not change that route or alter the unrelated assertion. Plotting deprecation
  warnings also remain.
- **30 final Chromium check groups passed**: four form screens at 1440, 768, 390,
  320 and landscape 844×390; four 200% root-text cases; local filtering/Enter,
  selected-item removal, intentionally empty draft restoration, hidden selections,
  required SDGs, cover upload/refresh/next step, multiple departments/final review,
  failed-save recovery, selected overflow keyboard disclosure and no-JS submission.
  No page overflow or page script errors. Supersedes the initial 20-layout run.
- **23 existing polish browser checks passed**, rechecking guide behavior,
  information tips, drafts/saving failures and filter/Back navigation after the
  shared draft-submit fix.
- Tailwind build, syntax checks for choice-panels/drafts/workspace scripts, full
  template compilation and `git diff --check` passed.
- Refreshed private preview: Director, Coordinator and Volunteer login/dashboard
  smoke checks passed. Live Coordinator Edit/Create controls were checked separately.

## UI audit and delivery gate

Reviewed changed templates, choice-panel interaction, draft retry and scoped styles
against the [current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md), fetched 14 November 2026.
The user's Newspaper Case and Philippine-time requirements remain authoritative.

- Hard gate PASS for the tested scope: native fieldsets/checkboxes/labels/buttons,
  real form submission, visible focus, asynchronous saving/error feedback, no page
  overflow, full labels, no fabricated data and working empty/invalid/filter states.
  Browser checks include keyboard and no-JS operation. No new media assets shipped.
- Purpose gate PASS: no decorative icons, gradients or added animation. Blue identifies
  selected choices; boundaries contain option scrolling; the visible cover field
  follows Description because both describe the activity.
- Liveliness PASS: energy 2/rhythm 2/motion 1 declared before implementation. The
  proposal/detail/audience/review sequence remains the structure; focused fields,
  selected summaries and the native choice list each serve a distinct task.
- Craftsmanship PASS for the tested scope: existing upload/draft/consent services
  reused, catalogue values preserved, no new library/schema, prior working changes
  retained, source backups and regression/browser evidence available.

Computed contrast: PSU #00408b on #eff6ff is **9.16:1**; secondary #475569 on white
is **7.58:1**. Existing focus and control tokens are reused. Physical-device and
screen-reader certification and the full historical suite were not performed;
200% root text is a stress test rather than every browser's native zoom mode.

## Local review, evidence and rollback

Preview is running at `http://127.0.0.1:5000`, using the existing isolated private
database/uploads without reseeding; mail remains suppressed. Sign in again after
restart. Accounts: `coordinator@psu.edu`, `director@psu.edu`, `student@psu.edu`;
password `password`. Earlier handoff entries describing a stopped preview are dated
history; this pass successfully restarted and verified it.

Artifacts in `.qa-overhaul-temp/activity-forms/`:

- `before/`, `after/`: repeatable disposable-fixture desktop/phone screenshots;
  selected-department/SDG and 200% captures; final `after/results.json` (30 groups).
- `live/`: refreshed private-preview Coordinator form screenshots.
- `before-source/`, `source-review.patch`: scoped pre-pass source reference.
- Old diagnostic failure images are debugging evidence, not final screenshots;
  use numbered final images and selected/200% captures for review.

Commands:

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_activity_forms.py tests/test_ui_reimagining.py tests/test_activity_journeys.py -q
.venv/Scripts/python.exe -m pytest tests/test_workspace_overhaul.py tests/test_opportunity_journey.py::test_consent_validation_preserves_only_submitted_choices -q
.venv/Scripts/python.exe scripts/qa_activity_forms.py --stage after
.venv/Scripts/python.exe scripts/qa_workspace_overhaul.py --polish-only
.venv/Scripts/python.exe .qa-overhaul-temp/run_local_preview.py
```

Stop the existing preview before restarting. For rollback, save current work and
restore only this pass's existing files from `before-source/`; remove only its new
choice partial/script, tests and QA files if desired; rebuild Tailwind and restart.
Draft-only obsolete fields already removed on authorized access are intentionally
not reconstructed. No published activity, consent, acceptance or historical audience
data was cleared. Do not reset/clean the mixed working tree.

Work remains local on `codex/ui-workflow-overhaul`. No commit, push, deployment,
operational migration, new application dependency, generated UI imagery or broad
cleanup. Unrelated files and earlier work remain preserved.
