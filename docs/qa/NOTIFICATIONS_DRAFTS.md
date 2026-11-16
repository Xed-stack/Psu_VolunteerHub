# Notifications and Saved Drafts

## Analysis completed 16 November 2026

Notifications are authenticated, user-owned, newest-first, and paginated by the
shared 25-row helper. Guidance content already validates the Coordinator campus
and produces authorized internal destinations. Read actions are POST requests
protected by the shared CSRF setup. The header and list use the same request-local
unread count. Current actions return to the first page and have no Unread view.

Drafts are scoped to both account and current campus, newest first. Existing
presentation labels map known form destinations, including legacy agency/MOA
drafts. Resume URLs and upload metadata are maintained by the existing services.
Discard uses native confirmation and the existing DELETE endpoint, including
staged-file cleanup. Its current failure response changes the button label but
does not announce status or prevent duplicate requests. Autosave must remain intact.

Both screen templates are intentionally small but Notifications nests a panel per
row. Drafts displays UTC directly; notification timestamps omit their timezone.
Neither screen needs a new service or model. Use a narrowly named shared
presentation helper to interpret these UTC model timestamps and display Philippine
time, without changing activity scheduling or any stored dates.

## Preservation checklist

- [x] All three signed-in roles; existing navigation and header identity.
- [x] User-only notification query/read actions and campus-safe guidance links.
- [x] Chronological ordering, pagination and header unread totals.
- [x] Native read POST actions and CSRF; no autosave on action forms.
- [x] Draft account/campus isolation and known legacy resume destinations.
- [x] Native discard confirmation, cancellation, failure/retry and upload cleanup.
- [x] Existing draft restoration, credential/consent exclusions and submit cleanup.
- [x] Empty states, escaped authored text, keyboard focus and mobile reflow.

## Design completed before application changes

The PSU audience needs a reliable inbox and a place to resume work. Use existing
Inter typography, PSU blue #00408b for links/selection, navy #002b60 for headings,
ink #111c2c for body copy, slate #475569 for metadata and white surfaces. Gold
remains part of the existing shell; no extra decoration is needed in these lists.

Desktop notification wireframe:

```text
Notifications                         Mark All as Read
3 unread notifications                Notification Help
All | Unread 3
------------------------------------------------------
Unread   Notification title                Mark Read
         Full message at readable width
         Review Campus Records
         16 Nov 2026, 11:30 AM Philippine Time
------------------------------------------------------
Read     Notification title
         Full message and timestamp
Previous Page              Page 1 of 2       Next Page
```

Desktop draft wireframe:

```text
Saved Drafts                                  Draft Help
3 drafts • Private to your account and campus
------------------------------------------------------
New Activity                        Resume     Discard
Last saved 16 Nov 2026, 11:30 AM Philippine Time
------------------------------------------------------
Agency Details                      Resume     Discard
Last saved …
```

Phone wireframe: heading, action/help links, then tabs where relevant. Every row
stacks identity, text, timestamp, and a left-aligned wrapping action row. At larger
widths draft and read actions align beside the content. No horizontal scrolling.

One surface with dividers replaces nested cards. Keep messages fully readable;
do not truncate instructions. Notification body copy is limited to 72 characters
per line. Unread has both a visible label and a pale blue surface. All/Unread uses
native links with aria-current rather than simulated JavaScript tabs.

States: unread/read, selected/hover/focus, zero records, no unread records,
unavailable guidance, discard pending, discard failure/retry. Native POST submit
feedback is reused. Confirming discard warns that its saved uploads are removed;
cancel leaves data unchanged. Resume is always a normal link. No-JavaScript copy
explains discard availability. Fixed labels use Newspaper Case; authored text is
not recased. Empty screens link to existing dashboard and role-authorized Help.

Design review: preserves every item above. All/Unread is the only new filter;
there are no search controls, metric tiles, or extra card stacks. The existing
shared shell, spacing and controls keep both screens consistent with the profile.

## Implementation and verification

Implemented the layouts above. `view=all|unread` is additive to `/notifications`;
missing/invalid values show All. Views reset pagination; action forms retain the
current view/page, and POST redirects clamp to the nearest remaining page.
Mark All as Read still affects all of the owner's unread records across pages.
GET list requests do not mark anything read. Existing guidance decoder is unchanged.

Draft list labels now use explicit Newspaper Case. No authored/stored values are
recased. Resume links and keys are unchanged. Discard uses the existing DELETE
endpoint and native confirmation, disables duplicate attempts, announces progress
and failure, and permits retry. No-JavaScript users retain Resume and read actions;
Discard is hidden with visible explanatory copy. Help articles explain both flows.

UTC timestamps are interpreted explicitly; stored values and activity schedule
semantics remain unchanged. The shared timestamp macro provides an aware ISO 8601
`datetime` and server-rendered Philippine-time fallback. Only these tagged times
receive `Intl.DateTimeFormat` enhancement using `en-PH` and `Asia/Manila`. Browser
and no-JavaScript fallback may order the date differently; both show the same instant
and explicit Philippine Time label.

### Verification

- **34 focused tests passed**: new UI/state tests, existing notification ownership
  and actions, malformed legacy guidance, secret exclusions, refresh restoration,
  campus boundaries, staged uploads, legacy agency/MOA resume, submission cleanup,
  and the previously approved campus-change cleanup regression.
- **54 final Chromium groups passed** across Director, Coordinator and Volunteer.
  Each screen checked at 320, 390, 768, 844 landscape, 1024 and 1440px; 200% text
  with very long unbroken titles, reduced motion, native keyboard focus, selected
  states, 44px targets, Help/Back, print visibility and contained page overflow.
  Native no-JavaScript read actions and Resume passed. Discard cancellation,
  pending/duplicate guard, injected HTTP 503, announced retry, actual removal and
  empty state passed. Mark All as Read and retained history passed. No JS errors.
- **12 baseline browser capture groups** completed before application changes.
- Tailwind build, **120 templates**, changed Python compilation and both changed
  JavaScript syntax checks passed. Standard Git whitespace check passed.
- Measured text contrast: PSU blue on white **9.97:1**; slate metadata on white
  **7.58:1**. Unread status also has text and a blue edge; selected links have an
  underline/border and aria-current. Existing visible focus is retained.
- Current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md)
  fetched and audited 16 November 2026. Changed templates/scripts/styles checked
  for semantics, URL state, CSRF/native actions, focus, live feedback, formatting,
  overflow, hover states and responsive behavior. No outstanding in-scope finding.
  Antislop delivery gate passed: PSU-specific palette, useful whitespace, no added
  decoration, animation, metrics, generic card stacks, or unsupported product claims.

The enlarged-text browser check initially read geometry before Chromium completed
its resize/scroll. It now waits for layout and actual unobscured focus rather than
using an immediate stale rectangle; the application did not need a focus workaround.

### Existing failures separate from this pass

An exploratory broader run finished **41 passed / 4 failed** in
`tests/test_prescriptive_guidance.py`. These failures occur before the changed
notification presentation paths:

- `test_reminder_delivery_identity_links_and_scope_state`: old reminder fixture
  expects legacy calendar query values on the redirect.
- `test_reminder_is_director_only[admin]`: creates the removed Admin enum role.
- `test_operational_reminder_and_resolved_condition`: old reminder payload produces
  no notification under the current follow-up interface.
- `test_coordinator_lookup_is_batched`: expects `/director_dash` to render 200;
  the current compatibility route redirects to the connected Overview.

These routes, reminder rules and old fixtures were not changed in this task. The
new authorized-guidance tests directly verify current same-campus links, rejection
of cross-campus/other-role links, and legacy/malformed message display. No full
historical-suite pass is claimed.

### Screenshots and repeat commands

Evidence lives under `.qa-overhaul-temp/notifications-drafts/{before,after}/` with
role-specific desktop/mobile PNGs and `results.json`. The fixtures are disposable
in-memory data, not private preview records. Representative comparisons:

- `before/coordinator-notifications-390.png` and
  `after/coordinator-notifications-390-viewport.png`.
- `before/coordinator-drafts-390.png` and
  `after/coordinator-drafts-390-viewport.png`.
- `after/director-drafts-1440-viewport.png`, role `*-nojs-drafts.png`,
  `*-discard-failure.png`, `*-unread-empty.png`, and `*-focus-check.png`.

Run `npm run build` and
`.venv/Scripts/python.exe scripts/qa_notifications_drafts.py --stage after`.
Run the focused backend set with `tests/test_notifications_drafts_ui.py`,
`tests/test_app.py::TestNotifications` and the draft/upload/profile cases named
above. Use a task-local pytest temporary directory or normal temporary-folder
permissions. Browser subprocesses require normal process permissions on Windows.

### Local review and scoped rollback

The existing isolated preview was restarted and verified at
`http://127.0.0.1:5000/notifications` and
`http://127.0.0.1:5000/workspace/drafts`. All three existing preview role accounts
returned 200 for both redesigned screens. Its private database/uploads were retained;
no sample notifications/drafts were inserted into that preview.

To undo only this pass, revert the inbox layouts/rules, new timestamp macro and
presentation helper, tagged-time enhancement, notification view/redirect additions,
explicit draft display labels, discard feedback block and two Help paragraphs.
Rebuild Tailwind and restart the same isolated launcher. Preserve all earlier
working-tree edits, and do not reset the shared stylesheet, workspace routes or
draft script wholesale. There is no migration or data rollback.

Skills actually used: UI/UX Pro Max (primary UX; local search confirmed submit
feedback and readable line length), Frontend Design (PSU composition), Ponytail full,
antislop core/UI/human/mobile during work, Webapp Testing (Python Playwright), and
current Web Design Guidelines. No new dependency. Physical-device, manual screen-
reader, actual browser toolbar zoom and the full historical suite remain unverified.
Work remains local/uncommitted on `codex/ui-workflow-overhaul`; no push or deployment.
