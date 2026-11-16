# Full-Height PSU Sign In — 15 November 2026

## Analysis and design

Replaces the compact photo-split card documented in LOGIN_PHOTO_SPLIT.md. Existing
login scripts already provide loading/repeat-submit guards, native validation,
password-toggle state, invalid-field focus and native reactivation dialog behavior.
The server owns credential checks, CSRF, throttling, safe-next and consent routing.
No authentication policy or server interface change was needed.

Design: existing PSU community photograph supplies identity; white form workspace
supplies focus. Inter, PSU #00408b, deep navy #002b60, gold #f4bd27, white and existing
slate neutrals. ENERGY 2 / RHYTHM 2 / MOTION 1. All content is left aligned; the form
has a 25rem maximum width. No decorative shadow, card frame or new motion.

Desktop wireframe: `[photo + navy caption | PSU / Home / Help; centered Sign In form]`.
Below 1024px: `[PSU / Home / Help; single-column form]`, with no image or outer card.
The shell uses minimum viewport height, never a fixed content height; short screens
top-align the form and permit scrolling. Workspace padding respects safe-area insets.

## Implementation and feature preservation

- Shared navigation extracted verbatim to a partial. Default auth-base blocks keep
  other authentication screens unchanged; login moves navigation/messages inside its
  workspace and selects a white browser theme color.
- Existing caption and supporting copy retained. Photo has dimensions and high fetch
  priority. Login-only Tailwind rules replace the superseded card rules.
- Visible labels, identifier hint, integrated Show/Hide boundary, recovery action in
  error summary, secondary account link, visible focus and 44px controls retained.
- Login fields, POST action/next, CSRF, autocomplete and blank password after errors
  preserved. No credentials in drafts or browser storage. No new dependencies.
- Reactivation dialog and no-JS fallback retain existing routes, pending-request
  handling, keyboard dismissal and focus restoration. Other auth routes remain usable.

## Verification

- Tailwind build and all **116** Jinja templates passed; diff whitespace check passed.
- **31** focused authentication/recovery regressions passed, including existing JS
  checks; four previously documented legacy signup-policy/profile/recovery-copy
  assertions excluded. No claim that the complete historical suite passed.
- **17** Chromium check groups passed: 320–1440px, tablet, landscape, exact desktop
  split geometry, no horizontal overflow, desktop-only photograph, 200% text, 200%
  zoom-equivalent responsive viewport, links, native required fields, Show/Hide,
  Enter, blank passwords/escaped identifiers/error focus, no browser storage password,
  loading/repeat-submit/pageshow, role email/ID login, safe next/external rejection,
  modal Escape/focus, no-JS submission and duplicate reactivation.
- Before/after screenshots: `.qa-overhaul-temp/login-photo-split/{before,after}/`.
  Desktop and 320px images visually inspected. Results saved alongside screenshots.
- White/PSU contrast **9.97:1**; white/deep-navy **13.87:1** (checker measured).
- Current Web Interface Guidelines fetched and reviewed against touched templates and
  styles. Addressed photo priority, safe-area padding, modal overscroll and matching
  browser theme. No remaining in-scope findings. Antislop gate reviewed: one clear
  task, actual PSU photograph, restrained accent, structural spacing, no false claims.

Limitations: Chromium only; no physical device, manual screen-reader or actual browser
toolbar zoom verification. Zoom-equivalent viewport checks are explicitly emulation.
Existing third-party font delivery remains. No new APIs, migrations or release actions.

## Local review and scoped rollback

Preview: `http://127.0.0.1:5000/auth/login`, existing private data/uploads and suppressed
mail. Build with `npm run build`; regenerate evidence with
`.venv/Scripts/python.exe scripts/qa_login.py --stage after`.

Work stays local and uncommitted on `codex/ui-workflow-overhaul`. Undo only the full-height
login markup/styles, navigation/message/theme block changes and navigation partial;
restore the compact pass if desired, then rebuild and restart preview. Preserve all
earlier UI work, auth behavior, unrelated files and private preview data. Do not reset
the entire shared stylesheet or working tree.
