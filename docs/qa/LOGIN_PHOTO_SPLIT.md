# Compact Photo-Split Sign In — 15 November 2026

## Analysis and design before implementation

Current Sign In uses two separate cards: a navy brand card with large headline/photo
and a white form. It shares auth layout, form behavior and component styles with signup,
recovery and consent. Preserve their layouts and the existing login form contracts.

Design read: all roles need a focused, recognizable university account entrance. One
restrained frame, max-width about 1024px, replaces the separate panels. Desktop uses
45% existing PSU coastal-cleanup photography / 55% form with ~400px reading width.
Phone/tablet hides the large photo and centers a compact form. No fixed height or new
promotional sections. Inter, PSU blue/gold, ENERGY 2 / RHYTHM 2 / MOTION 1.

Desktop: shared PSU/Home/Help navigation → [photo with caption | Sign In / fields /
Forgot Password / primary Sign In / quieter Create an Account]. Mobile: navigation →
form. Photo caption: “Service starts with people working together.” Supporting form
copy: “Access your PSU Volunteer Hub account.” No duplicate logo in the frame.

Keep identifiers, CSRF, safe next, password-manager autocomplete, show/hide semantics,
blank password after error, throttling, role redirects, terms/privacy, reactivation and
no-JS behavior. Add a login-only body hook; do not restyle other authentication screens.
Update obsolete administrator wording in reactivation to Director; keep its endpoint.

## Implementation and preservation

Login-only body block and scoped Tailwind components leave signup, recovery, policy
and profile layouts unchanged. The form retains its original fields, autocomplete,
CSRF, safe-next action and submit behavior. No authentication calculation or policy
changed. `data-no-draft` explicitly excludes this form from saved drafts. Reactivation
dialog, no-JS fallback and success message now refer to the Director. Native modal
focus replaces the unnecessary autofocus attribute; Escape restores identifier focus.

## Verification and evidence

- Tailwind build passed; all 115 Jinja templates compiled; `git diff --check` passed.
- Chromium: 14 groups passed using disposable testing data, with no page errors.
  Widths 320, 390, 768, 844 landscape, 1024 and 1440; 200% text at 390; invalid and
  inactive states; Show/Hide accessible state; Enter submission; escaped identifier
  retention; blank password/error focus; no password in browser storage; email/ID
  sign-in to all three role shells; modal Escape/focus; no-JS fallback; reactivation
  submission and duplicate pending handling. Existing authorization/routes reused.
- Six existing auth JavaScript tests passed outside sandbox subprocess restrictions.
- Before/after screenshots: `.qa-overhaul-temp/login-photo-split/{before,after}/`.
  Desktop and 320px screenshots inspected: photo/form hierarchy, wrapping, visible
  actions and readable caption. Shared controls retain 44px targets and focus styles.
- Focused authentication/recovery pytest results are recorded in the handoff.
  Broader run found legacy expectations: signup password policy, profile heading
  casing and recovery field casing. Those unrelated four tests remain unchanged.
  Updated shared-shell regression to assert the existing 40px navigation logo and
  current accessible navigation name instead of a duplicate 128px brand image.

## UI audit and limitations

Fetched current Web Interface Guidelines on 15 November 2026. Reviewed login template,
auth-base body hook and scoped styles: native labels/actions, autocomplete, no paste
blocking, error announcement/focus, image dimensions, no new animation, readable
wrapping and no overflow. Removed lazy loading from the above-fold photograph.
No remaining in-scope audit findings. Antislop delivery gate: purposeful PSU photo,
one task, restrained blue/gold, no decorative panels, no additional dependencies.

No physical-device/manual screen-reader testing; Chromium is the browser checked.
No complete historical-suite claim. Existing Google Fonts delivery is unchanged.
No auth policy, operational database, schema, deployment, commit or push changes.

## Local review and rollback

Preview refreshed at `http://127.0.0.1:5000/auth/login`, retaining private preview data,
uploads and suppressed mail. Build: `npm run build`. Browser evidence can be regenerated
with `.venv/Scripts/python.exe scripts/qa_login.py --stage after`.

To undo this pass, reverse only the login template, auth-base body-class block,
`.login-page` component rules, Director reactivation success wording and shell-test
assertions. Rebuild Tailwind, then restart the private preview. Preserve all other
uncommitted work; do not reset the whole stylesheet, auth routes or repository.
