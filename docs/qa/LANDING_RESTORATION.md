# Landing Page Restoration — 15 November 2026

## Analysis and design before implementation

Selected reference: `5265c00^:templates/Homepage.html`, the photo-carousel version.
The active page is `workspace/home.html`; current `/` supplies approved upcoming
activities, ended approved activities and separately sourced historical totals.
Restore presentation only; keep those queries and the current copy/links intact.

Design read: prospective volunteers need PSU's actual community photographs and a
clear path to activities. Restore the full-width five-photo hero, readable navy
scrim, gold primary action, feature rhythm, horizontal activity cards, completed
stories, historical record band and dark Help band. Keep Inter, PSU identity and
compiled Tailwind. ENERGY 2 / RHYTHM 2 / MOTION 1. The image scrim has a contrast
purpose; photo rotation has explicit controls, reduced-motion and no-JS fallbacks.

Copy mapping:
- Hero keeps “Your campus. Your community. Your contribution.”, current description,
  eligibility, Explore Activities / Become a Volunteer and photo caption.
- Features keep Choose Your Cause / Find Your Activity / Follow Your Commitment.
- Upcoming Campus Activities / Service in Action retain descriptions and empty states.
- PSU’s Documented Service retains labels, unknown-count fallback and source caveats.
- Current Activities / About Us / Help / Sign In or Dashboard navigation remains.
- Dark Help band uses current Help and Process Guide wording, not obsolete claims.

No old direct-join controls, “Opportunities” terminology, assumed historical year
range or audited claims are restored. Authored activity content remains unchanged.
Styles are landing-scoped; signed-in header, Help and authentication stay untouched.

## Implemented restoration

The active template keeps the current text and root-route context while recovering
the selected old composition. The hero uses all five existing photographs, a contrast
scrim, gold Explore Activities and conditional Become a Volunteer. Current navigation
and Dashboard/Sign In behavior remain. The photo caption is retained beside controls.
Features use the existing three current titles/descriptions; upcoming activities use
horizontal cover/text-first cards; historical source values and caveats remain separate
from completed stories. The dark Help band uses current Help and Process Guide wording.

Current activity detail links are retained instead of restoring old direct-join
controls or inline full-description dialogs. No route/query/permission/calculation
changes, legacy stylesheet imports, new imagery, libraries or database changes.

Carousel behavior:
- First hero image has explicit dimensions and high priority. Secondary photographs
  have data-src and load when selected; no-JS retains the first image and page actions.
- Six-second rotation has native Previous/Next, dots and Pause/Resume. Manual selection
  and keyboard focus pause it until explicit resume. Hidden pages stop the timer.
- Reduced motion disables automatic rotation and fades; manual selection remains.
  Controls are hidden until the script initializes, so no-JS exposes no dead buttons.
- Activity rows support native touch/keyboard scrolling and arrow buttons with boundary
  states. No-JS keeps the scroll region. Selected photo dots differ in size and color,
  with aria-pressed state. Skip to Main Content focuses the single main landmark.
- Narrow layouts use a uniform navy scrim for reliable text contrast. Print switches
  overlay text to ink and displays activity cards without clipped horizontal overflow.

## Verification — 15 November 2026

- `pytest tests/test_landing_restoration.py -q`: **15 passed**. Exact current-copy
  coverage, public/signed-in actions, deferred images/dimensions, no old direct join,
  activity-start/end/lifecycle boundaries, legacy no-end-time behavior, latest three
  completed records, missing covers, empty states, known/unknown historical totals.
- Chromium: **11 check groups passed**, no page errors. 320/390/768/844 landscape/
  1024/1440px; manual photo controls, activity arrows/native scroll, 200% text,
  reduced motion, no-JS/keyboard skip, empty sections, print, six-second automatic
  rotation, pause/resume, keyboard pause, hidden/visible document timer behavior.
  Timing uses Playwright's clock in real Chromium rather than wall-clock waits.
- Matching before evidence: **6** viewport captures/checks. After screenshots are
  `.qa-overhaul-temp/landing-restoration/after/landing-<width>.png`, plus
  `landing-200.png`, `no-javascript.png`, `carousel-controls.png`, `empty.png`, and
  `print.png`; JSON evidence is beside them. Fixture activity values are not live data.
- Tailwind build, **115 compiled Jinja templates**, public-home script syntax and
  `git diff --check` passed.
- Contrast: white against conservative small-screen overlay-on-white composite
  `#293e5e` **10.80:1**; navy/gold primary action **8.03:1**. Both pass normal-text AA.
- Refreshed preview public `/` returned 200 with the restored hero and current copy.
  All three existing accounts signed in, retained Dashboard navigation, and opened
  the unchanged Help/sticky-header shell successfully.

Browser verification caught the initial minmax(0, percentage) card tracks shrinking
instead of overflowing; fixed to definite responsive percentage tracks. Pause handling
distinguishes keyboard focus from pointer activation so clicking Pause actually pauses.
The final checks pass. Old homepage tests still reference retired wording, old story
selectors and direct-join semantics; they were not broadly rewritten or claimed to
pass. No full historical-suite, physical-device or manual screen-reader claim.

## UI audit and delivery gate

Reviewed changed landing markup/style/script against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched 15 November 2026. Native named controls, meaningful image alternatives,
dimensions, first-image priority/deferred secondary images, focus, 44px controls,
non-color selected cue, paused/reduced motion, no-JS fallback, contrast, empty states
and scoped overflow verified. No unresolved changed-landing findings.

Antislop during-work gate: ENERGY 2 / RHYTHM 2 / MOTION 1. The user-selected photo
composition and controlled rotation are purposeful; the scrim protects copy contrast.
The feature/story/source sections use different real content structures. No new stock
images, invented counts, marketing claims, decorative effects or obsolete workflows.

## Local review and scoped rollback

Open `http://127.0.0.1:5000/`. Existing preview data/uploads remain; mail is suppressed.
Compare the six before/after widths under `.qa-overhaul-temp/landing-restoration/`.
Sign in again after restart when checking the conditional Dashboard navigation.

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_landing_restoration.py -q
.venv/Scripts/python.exe scripts/qa_landing.py --stage after
```

Rollback: first copy the diff and new files. This pass changed only the active home
template, public-home script and landing-scoped additions to ui/app.css (plus QA/docs).
The template and script were unchanged at the start of this pass relative to
`b76a620`; restore only those two from that baseline if reverting. Remove only the
landing-specific styles/media overrides and rebuild Tailwind, preserving the uncommitted
header/Help/Partners/Accounts changes in shared files. Remove this pass's QA runner/test
only if no longer needed. Restart the existing private preview launcher afterward.
Do not reset the branch or replace databases/uploads. No commits, pushes or deployment.
