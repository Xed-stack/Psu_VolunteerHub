# Joining flow verification

Date: 18 October 2026

## Scope and design

Homepage featured-card and activity-dialog Join Now actions now navigate to the
existing agreement/NDA review page. The PSU registration endpoint rejects GET and
POST requests when the activity start is at or before the current time.

Ponytail full: two existing controls and one shared route guard, with no new
helper, dependency, migration, or registration workflow. Bare CSS, base.css, the
shared role shell, local PSU assets, authorization, and cosine matching remain.

Design read: participation review for PSU volunteers in the established
institutional style, ENERGY 1 / RHYTHM 2 / MOTION 1. Native links communicate
navigation; the existing consent form remains the confirmation step. PSU blue
focus outlines identify the changed homepage actions against white surfaces.

## Automated evidence

- `python -m pytest tests/test_app.py::TestVolunteerFeatures -q -p no:cacheprovider`:
  **19 passed**, including 10 new regression cases.
- Outsider volunteers, Phase One public experience, role access, non-volunteer
  registration rejection, and shared UI structure: **55 passed**.
- Tests cover homepage links reaching review without creating registrations,
  agreement/NDA version recording, missing consent, missing/valid CSRF, the exact
  start boundary, and a start occurring between review and submission.
- Rejected stale submissions preserve cancelled status, previous agreement/NDA
  evidence, audit-log count, and notification count.
- `git diff --check`: passed.
- Full suite was not rerun for this bounded change. The previously documented
  Admin self-password-reset assertion remains outside this fix.

## Browser evidence

Isolated in-memory SQLite preview on port 5056, CSRF enabled. No live MySQL data
was read, seeded, migrated, or modified. The temporary server and tab were closed.

- Keyboard Enter on a featured-card Join Now link opened agreement review.
- Mobile activity-dialog Join Now opened agreement and optional NDA review.
- Both consent checkboxes operated with Space; submitting the preview agreements
  produced a success notice, Registered state, and one fewer remaining slot.
- At 390px mobile, page client/scroll widths were both 375px, excluding scrollbar.
  At 1280px desktop, homepage widths were both 1265px and review widths both 1280px.
- Changed mobile Join Now action measured 297 x 44px. Tab reached the link and
  its computed outline was solid 3px PSU blue. Blue/white contrast: **9.97:1**.
- Browser error log was empty during the successful registration check.
- Native screen-reader output, physical mobile keyboard, and actual 200% browser
  zoom were not tested. Existing consent-page styling was reused.

## Changed-surface delivery gate

- Hard gate PASS: real GET navigation, protected POST with consent/CSRF checks,
  native keyboard controls, measured 44px action, no page overflow, and explicit
  started-event recovery through the existing Opportunities page.
- Purpose gate PASS: existing PSU typography/layout/assets retained; blue focus
  makes navigation visible against the white card/dialog surface.
- Liveliness PASS: declared institutional dials retained, with one clear Join Now
  action leading to the existing participation-review task.
- Craftsmanship PASS: 74 focused/compatibility tests and desktop/mobile browser
  checks; no fabricated content, new motion, alternate theme, or decorative asset.
- Web Interface Guidelines PASS for changed controls: semantic navigation links,
  visible keyboard focus, existing responsive sizing, and unchanged protected
  confirmation form. Source: https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

The pre-existing VOLUNTEER_HUB_ROADMAP.md refresh was left unchanged. No commit or
push was made.
