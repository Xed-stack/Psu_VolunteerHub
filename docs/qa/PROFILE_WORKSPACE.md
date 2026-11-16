# Volunteer Profile Workspace — 16 November 2026

## Phase 1 — Analysis

Sources read: AGENTS.md, current HANDOFF.md, PROFILE_SETTINGS.md and PROFILE_REPAIR_QA.md;
profile template, `profile-settings.js`, shared drafts, volunteer routes and existing
profile/account tests. Dated publication notes are history, not release authorization.

Current `/profile` defaults to account settings; `section=preferences|impact` selects
connected views. Errors select the relevant account/preference view. Three independent
account POSTs save name/campus/password; success 303 anchors stay intact. Profile/photo
POST saves preferences and uploads; photo removal is separate. No backend changes are
needed. Old tests expect preferences/milestones in the default view and an Admin enum.

Preservation checklist:
- [x] Section URLs, selected state, default account view, hash disclosures and return links.
- [x] Identity, read-only email/type, independent name/campus/password forms and errors.
- [x] Campus pairing, security/throttling/session behavior and failed-save rollback.
- [x] Independent interests/skills, archived assignments, saved drafts and loading states.
- [x] Photo input/preview/removal, 3 MB rules, upload references and safe file cleanup.
- [x] Participation measures, level definitions, badges and registration-history destination.
- [x] Keyboard/no-JS paths, focus, 44px targets, 200% text and responsive layouts.

Baseline captures use disposable SQLite data and `scripts/qa_profile.py --stage before`.
No operational data, routes or calculations will change.

Baseline completed: 7 browser groups, all three sections at 320–1440px and landscape,
plus server-side name error. Captures in `.qa-overhaul-temp/profile-workspace/before/`.

## Phase 2 — Design specification (before application edits)

UI/UX Pro Max leads UX structure, interaction and accessibility. Verified local UX
search results: Focusable Error Summary, inline/announced validation, Focus Not Obscured.
Frontend Design supplies composition. Existing Tailwind tokens govern implementation;
no new product-wide palette or alternate design system. Antislop applies during work
per the user's saved session choice; Ponytail full keeps native components/reuse.

PSU #00408b primary, #002b60 identity headings, #f4bd27 restrained selected emphasis;
white workspace and existing slate supporting text/dividers. Inter, 16px body/inputs,
32–36px page heading, 20px section headings, minimum 44px controls. ENERGY 2 / RHYTHM 2 /
MOTION 1. No decorative animation, invented statistics or image assets.

Desktop wireframe:
```
Your Profile
[64px photo/initial] Name / email                 Campus / Volunteer Type
---------------------------------------------------------------------
Account Settings        | Account Settings
Interests and Photo     | Current name       [Change Name disclosure]
Participation Milestones| Campus/affiliation [Change Campus disclosure]
                       | Password            [Change Password disclosure]
Registration History   | (independent form opens beneath its row)
```
Phone/tablet: title → compact identity → wrapping section links → one-column main.
Desktop section menu starts at 1024px; it is not sticky. Controls scroll naturally
under the existing shared header offset and above the bottom navigation.

Preferences: thumbnail/file/removal controls → linked error summary → independent
Interests and Skills fieldsets with selected counts → Save Profile and existing draft
feedback. Milestones: three measures, existing definitions and level/progress, badges,
then Registration History link. Never fabricate certification or recognition claims.

States: selected navigation has aria-current plus border/tint; checked native choices
retain blue background and checkbox; empty catalog disables save with explanation;
archived choices stay labelled; native details show open state; submitted errors link
to fields/group and receive focus; existing draft/loading/success/failure feedback
retained. No fixed toolbar or new motion. All authored names/labels remain unchanged.

Design reviewed against Phase 1 checklist: no route/model/calculation changes needed.
Only templates, scoped CSS, profile UI script and corresponding tests will change.

## Phase 3 — Implementation

Common compact identity, desktop left navigation, wrapping phone navigation and one
main surface replace nested cards. Account rows preserve native details, hashes and
independent forms. Current values appear beneath their summaries. Fixed interface
labels and accessible password-toggle names now use headline case.

Preferences retain the same form/fields and upload association. Added local photo
preview with revoked blob URLs, independent selected counts, linked/inline error summary,
and archive labels. Shared draft events refresh the counts; submitted errors prevent
draft restoration from overwriting invalid server-returned values. Existing upload
staging and save/removal paths remain. Milestones retain measures, progress, badge
definitions and a Registration History destination.

Authorized exception: during Chromium testing, successful campus changes committed
but cleanup then rejected their previous-campus draft, producing a server error.
On 16 November the user explicitly approved a minimal backend cleanup fix. The request
records its trusted previous campus and cleanup deletes only the signed-in user's
submitted draft from that campus, with the existing locking read. Other draft access
still uses ordinary campus checks. Regression verifies other-user/unrelated drafts
remain and old-campus GET access stays forbidden. No account validation/security rule,
route, model, calculation, migration or API changed.

Stale tests now open preferences/impact explicitly. Certificate eligibility assertions
remain, exercised through the existing registration list/details; the removed Admin
fixture is replaced by the two supported non-volunteer roles. No coverage was skipped.

## Phase 4 — Verification

- **51 profile/account/archive cases passed**, including the repaired connected-screen
  tests and existing security, credential/session, file cleanup and rollback coverage.
- The new campus draft cleanup isolation regression passed separately; a subsequent
  account/workspace selection passed **42 cases, 37 deselected**. These runs overlap.
  No selected profile regressions remain; no complete historical-suite claim.
- **16 Chromium groups passed**: three sections across 320–1440px and landscape;
  linked validation/focus; name save/draft restore/discard; simulated failed draft
  save/retry; campus pairing/save/hash; counts/archived skill; preview/upload references
  after refresh/save/removal; password toggle/blank error inputs/change/current session;
  200% text on all sections; keyboard focus outside fixed header/mobile navigation;
  no-JS disclosure/name save. No captured JavaScript page errors.
- Final Tailwind build, JS syntax, all **119** templates and diff whitespace checks passed.
  Measured PSU/white **9.97:1**, slate-600 explanation/white **7.58:1**.
- Before/after artifacts and results: `.qa-overhaul-temp/profile-workspace/`.
  Desktop/phone account and preference captures inspected. Fixed bottom navigation
  appears inside full-page phone captures at the viewport boundary; keyboard checks
  separately verify actual focused controls remain visible as the page scrolls.
- Current Web Interface Guidelines fetched/reviewed 16 November 2026. Native controls,
  labels, image dimensions, focused/linked errors, URL state, no credential persistence,
  contrast and wrapping checked. Photo removal now uses existing confirmation behavior.
  Antislop delivery gate reviewed: one clear task/section, real PSU tokens, structural
  whitespace, restrained selected accent, no invented badges/statistics or new imagery.
  No remaining in-scope audit findings.
- Live isolated preview smoke: Account Settings, Interests and Photo, and Participation
  Milestones return HTTP 200 with the new workspace. Existing preview credentials/data
  retained, mail suppressed; no operational database migration/change.

Limits: Chromium/emulated viewports and text enlargement only; physical device,
manual screen-reader, actual browser-toolbar zoom and current MariaDB concurrency
testing were not performed. Previous historical MariaDB results are dated evidence.

## Build, review and scoped rollback

Review as Volunteer at `http://127.0.0.1:5000/profile`. Use section links or
`?section=preferences` and `?section=impact`. Build: `npm run build`. Regenerate captures:
`.venv/Scripts/python.exe scripts/qa_profile.py --stage before|after` (baseline should
only be regenerated on the corresponding prior layout).

Rollback only this profile pass: restore the prior profile template/script, remove
the `.profile-workspace`/section-layout scoped CSS, reverse the authorized campus-cleanup
exception and its regression together if reverting that fix, then rebuild and restart
the private preview. Preserve all earlier catalogue, signup, landing, Help and staff
changes. Do not reset shared files or restore the whole working tree. No schema or
data rollback is required. Work remains local/uncommitted; no push or deployment.
