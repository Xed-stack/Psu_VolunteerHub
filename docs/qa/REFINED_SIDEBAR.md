# Refined Navy Sidebar — 16 November 2026

## Analyze

Read AGENTS.md/current HANDOFF and the shared sidebar, CSS, presentation mapping and
role-shell drawer script. Existing width/content offset is 240px at 768px+. The drawer
already traps Tab, restores toggle focus on Escape, makes the shell inert and closes
on navigation. Preserve that script and all role destinations. Redundant CSS currently
overrides 256px sizing and adds spacing rules later in the file.

Baseline captures use disposable app data in `scripts/qa_sidebar.py --stage before`.
All three roles retain authored account names/campuses and native POST logout/CSRF.
About the Hub is a public destination; preserve its route and public layout. Give its
sidebar link the shared markup/mapping without adding a signed-in About screen.
No business logic/API/data changes needed.

Design phase begins after baseline capture; UI/UX Pro Max is primary, Frontend Design
supplies visual composition. Antislop applies during work (existing session choice).

## Design (before implementation)

Baseline: six desktop/mobile captures across the three roles. Approved refined navy:
PSU deep #002b60 canvas, white selected row with navy text/icon, narrow #f4bd27 gold
accent. Inactive links use existing blue-100 and group captions quieter blue-200.
Inter, 14px navigation and account name, 12px secondary captions, consistent 22px
existing Material Symbols. ENERGY 2 / RHYTHM 2 / MOTION 1. No decorative animation.

Wireframe: `[PSU seal / Hub + role] → [group caption / route rows] → open space →
[avatar / readable name + campus] [separate labelled Log Out]`. Selected row alone
uses the white surface. Icon/label columns align across all states; selection never
shifts their horizontal positions. Entire row stays at least 44px.

Keep default width 240px and desktop offset unchanged. Sidebar remains one natural
scroll region: short heights/enlarged text can scroll the entire navigation/footer;
no nested scrollbar, hidden links or footer overlap. At enlarged phone text, clamp
drawer width to leave an outside touch strip for closing. Existing Tab/Escape/inert
behavior and mobile bottom navigation stay unchanged. No new account dropdown,
collapse mode, badges, data queries, imagery or destinations.

Plan checked against analysis: all existing links and the native CSRF logout remain.

## Implement

Consolidated sidebar width/spacing/state rules rather than layering another override.
Brand copy and account details use bounded grid/flex columns. All navigation states
share the transparent/colored border width, so selecting a page does not shift text.
Active row has white surface/navy text and filled existing icon; hover stays readable.
Group labels are quieter, footer name is readable at 14px, campus remains secondary.
Log Out is its own full-width native action. Safe-area padding and contained overscroll
keep drawer content usable. Shared About link now uses the navigation helper and
presentation mapping, while its existing public destination stays unchanged.

No drawer script, route, backend business rule, API, schema, data query or dependency
change. Sidebar remains the existing single scroll container. Public/auth navigation,
mobile bottom navigation and existing print hiding/zero-offset rules are preserved.

## Test

- **10 focused navigation tests passed**: selected parent on profile, registrations,
  activity documents, Reports, catalogue form and imports; Help; role-specific links;
  native POST logout and CSRF enforcement for all three roles.
- **33 Chromium groups passed**: three roles at 1440,1024,768,390,320 and landscape
  844×390/667×375; 240px default sidebar and matching desktop offset; no horizontal
  sidebar overflow; active state and hover; Tab wrap/Shift-Tab, Escape focus return,
  shell/sidebar inert state and outside tap; every link/logout reachable by keyboard
  at 320×375 with at least 44px targets; 200% text/long campus and readable footer;
  support links and actual logout/session protection. No JavaScript page errors.
- Tailwind build, all **119** templates and diff whitespace checks passed.
- Measured contrast against PSU deep navy: white **13.87:1**, inactive blue-100
  **11.37:1**, secondary blue-200 **9.76:1**, gold focus outline **8.03:1**.
- Current Web Interface Guidelines fetched/reviewed 16 November 2026. Native navigation,
  aria-current, decorative icon hiding, focus, touch targets, responsive wrapping,
  safe areas and contained drawer overscroll checked. No in-scope findings remain.
  Antislop gate: explicit selected hierarchy, real PSU assets, useful open space,
  no decorative widgets/motion/claims. UI/UX Pro Max + Frontend Design applied together.

Artifacts: `.qa-overhaul-temp/sidebar/{before,after}/` with role/width PNGs and results.
Volunteer desktop/phone and role captures generated from disposable test data. No
full historical-suite claim; no physical-device/manual screen-reader or actual toolbar
zoom testing. Existing Google Fonts/Material Symbols delivery remains unchanged.

## Local delivery and rollback

Private preview refreshed at `http://127.0.0.1:5000/`; sign in with an existing preview
role to review its sidebar. Build with `npm run build`; repeat captures/checks using
`.venv/Scripts/python.exe scripts/qa_sidebar.py --stage after`.

Undo only the sidebar markup/rules and About presentation-map entry, rebuild and restart
preview. Preserve every earlier profile, catalogue, signup, Help and landing change.
Do not reset the whole stylesheet or working tree. Work remains local/uncommitted on
`codex/ui-workflow-overhaul`; no production/data migration, commit, push or deployment.
