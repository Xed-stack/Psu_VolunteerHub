# Inactivity timeout verification

Date: 21 October 2026. Local implementation, not committed or pushed.

22 October release note: this report is included in the user-approved consolidated
release. The date and publication statements above describe verification time.
See RELEASE_2026_10_22.md for current publication checks; the 393-pass result below
is not a new full-suite result for changes made after the inactivity work.

## Behavior and boundaries

- User selected 30 minutes of inactivity and a 1-minute warning, for all four
  roles. Defaults live in Config; no new dependency, schema, or migration.
- Login initializes a signed-session activity timestamp. The shared server
  guard rejects expired sessions before protected route code, including POST.
  Expiry clears authentication and shows: "Your session timed out due to
  inactivity. Please sign in again."
- GET /auth/session reads the deadline without renewal. CSRF-protected POST
  records activity; it cannot revive an expired session. Status responses and
  authenticated responses use no-store. Static files, favicon and HEAD do not
  renew activity. Existing app requests otherwise count as activity.
- Trusted keyboard, pointer-down, input and scroll events request renewal at
  most once per 30 seconds. There is no unconditional keep-alive heartbeat;
  mouse movement, the homepage slideshow and status reads do not renew.
  The server timeout measures acknowledged requests, not exact last DOM input.
- The native warning offers Stay signed in and Sign out now. Escape dismisses
  without renewal. A visible tab checks shared-cookie status before warning
  and expiry, so another tab's renewal is respected. Returning from background
  or browser history rechecks status. Hidden-tab timers may be suspended;
  the server still rejects expired requests.
- Successful checks return a fresh signed CSRF token for subsequent renewals;
  CSRF validation and its normal lifetime are not disabled or extended.
- Password-reset auth_version invalidation still runs first. Required Terms,
  Privacy and sex-completion gates remain; only the session-status endpoint
  bypasses those presentation redirects, not authentication/expiry checks.
- No persistent remember cookie, persistent draft storage or automatic form
  save was added. Users are warned about unsaved work. Offline errors remain
  retryable and do not falsely assert that the server confirmed expiry.
- Existing authenticated cookies without a timestamp get a first-request grace
  window. Invalid, nonfinite and future timestamps fail closed.
- This retains Flask's signed-cookie architecture, not a central session
  registry. There is no new global logout/revocation guarantee; valid copied
  cookies and concurrent Set-Cookie races retain that architecture's limits.
  The existing 8-hour signature-age setting is not a newly implemented absolute
  login lifetime. A separate absolute lifetime/shared store is outside this change.

The server-enforced check and client warning follow the separation described in
the [OWASP Session Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html#idle-timeout).
This is not a claim that the complete application meets all OWASP requirements.

## Verification

- Initial focused selection: 35 passed, 1 failed due to a test-fixture cached
  anonymous user. Fixed by creating a fresh app context for subsequent requests.
- Final inactivity selection: 20 passed in 52.47s. The CSRF longevity test uses
  fresh app contexts, matching real request-local CSRF caching. Its first run
  failed because the shared fixture retained g.csrf_token across requests;
  application CSRF behavior was not weakened to accommodate the test.
- Node fake-clock checks: 7 passed, including repeated warnings after renewal,
  CSRF token refresh, Escape, expiry redirect, trusted-event throttling,
  cross-tab deadlines, network failures, visibility/history restore and logout.
- Final uninterrupted full regression: **393 passed in 986.10s**, zero failures.
  Includes final server/template code and Node checks of the final script.
  Two earlier partial runs were deliberately stopped: one to include CSRF
  longevity coverage, one to correct that test's context cache. They are not
  represented as successful full runs. All pytest data was isolated SQLite.
- Python compilation, Node syntax check and git diff --check passed; Git's
  LF/CRLF notices are line-ending warnings, not diff-check failures.
- Browser: disposable in-memory SQLite, synthetic accounts, CSRF enabled,
  localhost port 5069. Accelerated timing was 60 / 30 seconds for workflows
  and 120 / 60 seconds for final stable screenshots; application defaults
  remain 1800 / 60 seconds. Original MySQL untouched. Preview stopped and its
  temporary browser tabs closed after verification.
- Volunteer, Coordinator, Director and Admin sign-ins/dashboard rendering
  verified. Warning, explicit renewal, Escape, repeated warning and automatic
  sign-out message exercised. Tab reached Sign out now with a visible 3px blue
  outline; Enter performed the existing CSRF-protected logout successfully.
- Warning dimensions at 320/390/768/1440px measured inside each viewport;
  root scroll/client widths matched (305/375/753/1425px, scrollbar excluded).
  Buttons were 49.59px high, with stacked full-width mobile actions.
- A second tab's Help navigation renewed the shared session while the first
  tab's warning was open. At its old deadline the first tab read the new
  deadline, closed its warning and stayed signed in (43 seconds remaining).
- A replayed dashboard guide and warning coexisted as native dialogs; the
  warning remained the topmost keyboard-focused decision. No walkthrough
  code or saved dismissal behavior was changed.
- A 640 x 450 CSS viewport fit the entire warning without horizontal scrolling
  (625px client/scroll width). This is a reflow check, not actual browser zoom.
- Sampled browser console had no JavaScript errors. Actual offline/retry and
  suspended-tab behavior use deterministic Node checks, not network emulation.
- Contrast computed with the antislop-human checker: blue #00408b on white
  9.97:1; text #111c2c on white 17.12:1. Blue control borders/focus exceed 3:1.

Screenshots and disposable preview are outside Git under the current
visualization root's idle-qa-20261021 directory.

## Design and review

Reading this as a session-expiry decision for PSU students and extension staff,
in the existing institutional light theme: ENERGY 1 / RHYTHM 2 / MOTION 1.

- Color/type: PSU blue and inherited Inter match the surrounding portal; solid
  white gives the warning readable contrast. No new imagery, icons or theme.
- Layout: a bounded native dialog isolates the time-sensitive decision, with
  left-aligned explanation/countdown and one blue primary action. On phones,
  controls stack with separate full-width targets. No page-shell redesign.
- Spacing: 1rem separation groups the warning, time remaining and actions;
  fluid padding preserves reading space on narrow screens.
- Motion: none added. Tabular countdown numerals avoid distracting width shifts;
  only meaningful status text uses a polite live region, not every timer tick.
- Critique/fix: initial modal focus landed on Sign out because the primary action
  was still disabled during the status check. Enable it before opening/focusing.
- Critique/fix: reset the warning-check marker after renewal, so each new idle
  period gets its own warning; Node regression exercises successive periods.

Reviewed against the current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).
Per-file review:

- templates/partials/session_idle.html:1 - pass: native dialog/actions, labelled
  explanation, polite request status, explicit CSRF field; no new images/inputs.
- static/scripts/session-idle.js:1 - pass: fetch/abort failure recovery, trusted
  interaction only, keyboard controls, restore checks, no layout-read animation.
- static/styles/base.css:8 - pass: contained scrolling, fluid sizing, 44px+
  controls, visible focus, mobile action stacking and no animation.
- templates/layouts/{role,auth,public}_base.html - pass: one conditional shared
  include; existing CSS foundations, navigation and main landmarks preserved.

## Anti Slop delivery gate (changed warning only)

- R-01 PASS: existing PSU blue/white; no gradients or glow.
- R-02 PASS: new warning/expiry copy contains no em dash.
- R-03 PASS: four measured widths, zero page overflow and 49.59px actions.
- R-04 PASS: no new icons or decorative emoji.
- R-05 PASS: warning, time remaining and two actual session decisions only.
- R-06 PASS: inherited Inter matches the existing PSU portal.
- R-07 PASS: no decorative background pattern.
- R-08 PASS: no decorative action arrows.
- R-09 PASS: no badges or unsupported status claims.
- R-10 PASS: solid dialog; no glass or blur.
- R-11 PASS: bounded dialog and smaller button radii, no pills.
- R-12 PASS: dimmed native backdrop marks modal elevation, no shadow stack.
- R-13 PASS: no glow.
- R-14 PASS: no feature-card grid introduced.
- R-15 PASS: Stay signed in and Sign out now name exact actions.
- R-16 PASS: operational copy, no marketing claims.
- R-17 PASS: countdown uses server deadline, no invented statistics.
- R-18 PASS: no testimonials or fictional people introduced into product UI.
- R-19 PASS: no animation; countdown serves the expiry decision.
- R-20 PASS: retained PSU palette/type/shell and named PSU session.
- R-21 PASS: existing user-selected institutional light theme; no toggle added.
- R-22 PASS: no illustration.
- R-23 PASS: no new visual assets or navigation structure.
- R-24 PASS: logout uses the existing route; no new navigation links.
- R-25 PASS: measured 9.97:1 primary/white and 17.12:1 body/white.
- R-26 PASS: renewal, logout and Escape exercised in browser/Node checks.
- R-27 PASS: normal hidden state, checking/renewing feedback, retryable error.
- R-28 PASS: no FAQ added.
- R-29 PASS: existing blue/text/white palette, no added accent family.
- R-30 PASS: existing PSU interface retained, not another product's template.
- R-31 PASS: color, type, layout, spacing and motion reasons above.
- R-32 PASS: native keyboard dialog; Tab/Enter/Escape and visible outline checked.
- R-33 PASS: direct source edits, no file-rewrite script.
- R-34 PASS: no theme switching introduced.
- R-35 PASS: app run on isolated SQLite, real controls and console checked;
  environment-specific unverified checks are listed below, not claimed passed.
- R-36 PASS: signed-cookie/revocation limits explicit, no compliance assertion.
- R-37 PASS: explicit institutional direction/dials before implementation.
- R-38 PASS: countdown real; synthetic QA accounts confined to isolated preview.
- Liveliness PASS: ENERGY 1 / RHYTHM 2 / MOTION 1, blue primary focal action,
  structural spacing, mobile reflow and existing PSU visual voice.
- C-1 PASS: written design reasons; no new decoration.
- C-2 PASS: both actions work; request failures remain retryable.
- C-3 PASS: every warning element supports session continuity or expiry.
- C-4 PASS: measured desktop/mobile and keyboard states; broader device/assistive
  coverage remains explicitly limited below.
- C-5 PASS: test/results evidence distinguished from production guarantees.

## Limits

Actual browser 200% zoom, OS screen-reader announcements and a physical mobile
keyboard are not independently verified in the in-app browser. Narrow CSS
reflow checks are not represented as real browser zoom. JavaScript-disabled
clients still have server enforcement but no automatic warning/navigation.
Hosted HTTPS and production multi-worker behavior are not exercised here.
No live database writes, seeds, policy publication, deployment, commit or push.
