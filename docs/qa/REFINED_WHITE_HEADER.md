# Refined White Header — 15 November 2026

## Design read before implementation

The current signed-in header uses 14px title/12px context, a white outlined bell,
and separate 80/72px minimum-height rules. The selected refined-white direction
needs stronger page identity and a coordinated utility group, not new features.
Preserve the existing title/subtitle extension blocks, role/campus data and actions.

PSU audience: volunteers and Extension staff moving through long workspaces. Reuse
Inter, PSU navy/blue, gold and existing icons. ENERGY 2 / RHYTHM 2 / MOTION 1.
The short gold rule repeats selected-navigation identity; it is not another panel.

Desktop: [gold rule | 18px navy title / clear context]    [bell Notifications] [existing actions]
Phone:   [menu] [gold rule | 16px title / context] [bell] [existing actions]

Keep an opaque white surface and fine bottom border; no gradients, blur, new shadow,
avatar, account menu, search or extra navigation. Target 72px desktop / 64px phone
minimum height with natural growth at 200% text sizing. Keep 44px controls, actual
ResizeObserver offsets, drawer/dialog layering and print hiding. Scope control styles
to `.role-topbar` so other icon buttons and public/auth headers stay unchanged.

## Implementation

- Header title is 18px desktop / 16px phone, navy and semibold. Scope caption has
  clearer spacing/contrast. Fixed fallback labels use University Office / Campus Not
  Assigned; authored campus names and template overrides are unchanged.
- Short gold identity rule repeats selected-navigation styling. The white surface,
  restrained border and content-aligned padding preserve the institutional direction.
- Matching soft-blue menu/notification controls have distinct hover and existing
  visible keyboard focus. Notifications has a desktop label (1024px and wider) and
  keeps its accessible name on smaller screens. Unread count/destination are unchanged.
- Existing extra actions wrap in a bounded utility group. Minimum heights are 72px
  from tablet/desktop and 64px on phone, with natural growth for long/enlarged text.
- Styling is scoped to the role header. No changes to routes, permissions, sticky
  measurement, public/auth layouts, application workflows or operational data.

## Verification — 15 November 2026

- Before: **20** matching layout captures/checks for public and three roles. After:
  **30 Chromium check groups passed**, no page errors. 320/390/768/844 landscape/1440px,
  scrolling, anchors, menu/Tab/Escape focus, information tips, guide replay, validation
  focus, session dialogs, 200% text, representative workspaces and print.
- Additional disposable fixture checks exercise the retained title/subtitle/action
  blocks with long text, 3 unread notifications and a real Saved Drafts action at all
  widths and 200%. The fixture URL exists only inside the isolated QA test app; no
  application route or new product action was added.
- Focused Help/navigation/read-only/authorization regressions: **16 passed**.
- Tailwind build, **115 Jinja templates compiled**, sticky script syntax and
  `git diff --check` passed.
- Title navy/white **13.87:1**; control blue/soft-blue **9.16:1**. Normal text AA passes.
- Physical-device/manual screen-reader checks were not performed. Existing historical
  Admin-role fixture failures remain documented in the prior Help pass; this pass did
  not rewrite those fixtures or claim the entire historical suite passed.

## Audit and delivery gate

Reviewed scoped template/style changes against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched 15 November 2026. Native named controls, contrast, focus, wrapping, 44px targets,
sticky offsets, modal layering, no motion and print behavior verified. No unresolved
changed-header findings. Existing title/subtitle hooks remain compatible.

Antislop during-work gate: ENERGY 2 / RHYTHM 2 / MOTION 1. Stronger type supplies the
focal point; gold uses an existing identity motif; control backgrounds group utilities.
No decoration without purpose, generated imagery, extra navigation or invented data.

## Review and rollback

Open `http://127.0.0.1:5000/help` after signing in with an existing preview account.
Director `director@psu.edu`, Coordinator `coordinator@psu.edu`, Volunteer `student@psu.edu`;
all use password `password`. The refreshed preview retains private data/uploads and
suppressed mail. Sign in again after restart.

Matching screenshots and JSON: `.qa-overhaul-temp/refined-header/before/` and `after/`.
Compare `director-1440.png`, `coordinator-1440.png`, `volunteer-1440.png` and each 390px
variant. Additional `*-actions-*.png` show long labels/unread/action cases; `*-200.png`
and print captures record accessibility/print checks. Fixtures remain separate from
current dashboard data.

Repeat browser verification:

```powershell
.venv/Scripts/python.exe scripts/qa_help_header.py --stage after --output-root .qa-overhaul-temp/refined-header
```

Rollback only this pass's `.role-topbar` typography/layout/scoped-control rules, removal
of the redundant minimum-height override, desktop notification-label span and fixed
fallback label casing. Preserve the sticky positioning/measurement and all prior
Help, Accounts/Imports and Partners work. Rebuild Tailwind and restart the private
preview. Do not restore entire shared files from the published baseline or reset the
branch. No migrations, new dependencies, commits, pushes or deployment.
