# Two-Step Account Creation — 16 November 2026

## Follow-up: Compact Signup Footer

Added a shared footer to both onboarding steps: PSU identity, About Us and Help and
Guides. One thin divider, existing blue/slate tokens, 44px native links and wrapping
phone layout. A minimum-height flex page keeps it beneath short content without fixed
positioning or covering forms. Sign In and other auth screens unchanged.

Build, 117 templates and 15 Chromium groups passed, including footer presence on both
steps at 320–1440px, working public links, 44px link heights, 200% text and the existing
signup journey. Phone screenshot inspected. Current guideline/antislop review: no
in-scope findings. No new data, routes, imagery or dependencies. To undo, remove only
the onboarding footer markup/styles and page flex sizing, then rebuild/restart preview.
Existing physical-device/screen-reader limitations remain.

## Follow-up: Actions and Public Categories

User requested replacing the summary panel with Back to Interests and Skills at the
left and Create Account at the right. Both now sit after policy controls, using the
existing responsive action row. On phones they stack with full touch targets. The
redundant summary panel and its scoped styles are removed; selections and draft return
behavior remain. Design is a navigation action row rather than another information box.

Public signup now offers Student, Faculty and Staff. External is rejected by the
signup route even in forged requests; ID and campus affiliation are required. Updated
form hints and removed obsolete conditional UI code. Existing accounts, external
attendance/roster workflows and data remain untouched. An older draft containing
External restores its ordinary fields while leaving category unselected for correction.

Verification: 10 focused signup tests passed; final browser results cover action
alignment, category options, old drafts, complete signup, no-JS, refresh, keyboard and
200% text. Build, 117 templates, script syntax and diff check passed. Current guideline
review and antislop gate: no in-scope findings; native actions and labels retained.
Private local preview refreshed, no commit/push. This section supersedes the earlier
four-category/named-summary descriptions below. To undo only this follow-up, restore
that summary and external public category/validation; leave the onboarding redesign.

## Analysis and design read

Existing `/auth/interests` validates mapped interests/skills and carries selections in
the session to `/auth/register`. Registration owns campus/category requirements,
password policy, volunteer-only account creation and policy acceptance. Existing
signup drafts save ordinary account fields in sessionStorage but not preferences;
storage failures are silent. GET affiliation selection requires JavaScript today.

Design before implementation: PSU audience includes students, employees and external
volunteers. Their job is to choose relevant causes, then create an account with clear
conditional requirements. Replace the photo sidebar with one 960px workspace.
ENERGY 2 / RHYTHM 2 / MOTION 1. Inter for readable labels and forms; PSU #00408b,
navy #002b60, gold #f4bd27, white and existing slate neutrals. Gold marks current step;
dividers separate actual form sections rather than enclosing each in a card.

Desktop wireframe: `[PSU / Home / Help] [1 Interests and Skills | 2 Account Details]`
then heading, selected-count/preferences grid OR grouped account fields, and actions.
Phone: same hierarchy, stacked fields and actions. Native checkboxes/selects, no fixed
height, 44px controls. The photograph remains specific to Sign In, not another long
column competing with onboarding. Preserve authored labels and policy text.

## Implementation and feature preservation

- New onboarding base scopes layout to the two signup screens. Existing shared
  navigation, Sign In, recovery and policy layouts remain intact. No route/API/schema
  change. Step 2 shows the real selected names with predictable edit navigation.
- Two-column desktop selection/field groups become single-column on phones. Native
  fieldsets, checkboxes, selects and labels remain. Interest rows expose related
  skills when checked; without JavaScript all choices remain available. Unselected
  group skill controls are disabled and cleared; duplicate selected skills stay in sync.
- Category changes update ID/affiliation requirements and visible markers. Campus
  changes preserve compatible affiliations and explain when reselection is needed.
  No-JS affiliation options are grouped by campus; the server still enforces scope.
- `onboarding.js` replaces the old signup-only draft block in `drafts.js`, retaining
  the existing `psu:signup` key and success cleanup. Explicit ordinary-field allowlist
  plus preference IDs; no passwords, confirmations, tokens or consent. POST-rendered
  values win over drafts. Dependent campus options load before affiliation restoration.
  Status announces restored/saved/failure, without repeating identical announcements
  on every keystroke. Storage failures preserve usable forms and visible warnings.
- Existing auth loading, native validation, linked errors, keyboard focus, server
  policy and volunteer-only assignment retained. Obsolete Admin role copy removed.
- Password-feedback styles now fit the workspace; existing checks/policy unchanged.

## Verification and screenshots

- Build, JS syntax, all **117** Jinja templates and diff whitespace checks passed.
- Combined onboarding/auth/recovery run: **42 passed, 2 deselected**. Follow-up signup
  run after adding empty-catalogue and duplicate-account checks: **10 passed** (nine
  overlap the combined run). Existing signup tests now use a compliant password and
  assert current policy text. Two unrelated existing profile/recovery heading-casing
  assertions remain excluded; no full historical-suite claim.
- **14 Chromium groups passed**: 320–1440px, tablet/landscape, both steps, selected
  counts/skill reveal, preference refresh, named review, ordinary-field and affiliation
  restoration, password/consent exclusion, Edit return, all four categories, campus
  changes, server-error precedence/focus, successful account creation and subsequent
  sign-in, draft cleanup, blocked storage, no-JS complete registration, 200% text,
  keyboard skip link and preference touch targets. No captured page errors.
- Before/after captures: `.qa-overhaul-temp/signup-onboarding/{before,after}/`, results
  JSON alongside. Desktop/phone layouts inspected. Enlarged-text checks found progress
  and password-grid overflow; fixed wrapping/minimum grid sizing and reran successfully.
- Measured white/PSU contrast **9.97:1**, white/slate explanation text **7.58:1**.

## UI audit and limitations

Current Web Interface Guidelines fetched 16 November 2026 and reviewed against changed
templates, styles and scripts. Native labels, semantic progress/current step, live
save/count feedback, no paste blocking, focus, autocomplete and disclosure fallbacks
checked. No remaining in-scope findings. Antislop gate: task-specific two-step hierarchy,
PSU identity, restrained gold current-step marker, structural spacing, no promotional
panels, fabricated claims, new imagery or dependencies.

Chromium only, with emulated viewports and text enlargement. No physical-device,
manual screen-reader or actual browser-toolbar zoom verification. Existing authored
policy/catalogue content and shared password-feedback wording otherwise retained.

## Local delivery and scoped rollback

Preview refreshed: `http://127.0.0.1:5000/auth/interests`. Private preview data/uploads
retained and mail suppressed. `npm run build` regenerates compiled styles. Repeat
browser checks: `.venv/Scripts/python.exe scripts/qa_signup.py --stage after`.

Work is local/uncommitted on `codex/ui-workflow-overhaul`; no push, deployment or
operational database changes. To roll back this pass, restore only the pre-onboarding
signup/interests templates, scoped onboarding CSS and legacy signup-draft block; remove
the new onboarding template/script, rebuild and restart preview. Keep the full-height
Sign In and all earlier changes. Never reset the shared stylesheet or working tree.
