# Unified Navy Landing Footer — 15 November 2026

## Compact follow-up

User feedback: the footer was too big. Reduced top/bottom padding and grid gaps,
removed the redundant explanatory sentence, reduced the logo to 44px, and arranged
links horizontally with wrapping instead of full vertical lists. All destinations,
14px link text, 44px touch targets, Help action, year and native Back to Top remain.
Desktop footer height: **373px → 225px**, about **40% shorter**. Phone at 390px:
**677px → 389px**. Existing page/footer scope remains unchanged.

The existing landing browser runner passed **12 groups** after the compact change,
including link targets, no-JS Back to Top, 200% text, print and carousel behavior.
Tailwind build and diff check passed. Current Web Interface Guidelines were refreshed
and the changed sizing/spacing reviewed; focus, contrast and native link behavior are
retained. Screenshots: `.qa-overhaul-temp/landing-footer-compact/after/`.
Preview refreshed; no new functionality, commits or pushes. Physical-device/manual
screen-reader testing was not performed. Revert only these compact size/spacing and
sentence changes to return to the preceding navy design, not the old white footer.

## Design read before implementation

The current page ends twice: an isolated blue Help strip, followed by a sparse white
footer that repeats Help. Replace both with one full-width navy ending, aligned with
the landing content. Keep the shared `.public-footer` rules for other pages.

Audience: prospective volunteers and signed-in visitors need useful destinations and
clear PSU identity. Use Inter, PSU deep navy/white, and one restrained gold top rule.
ENERGY 2 / RHYTHM 2 / MOTION 1. No new images, decoration, contacts or policy claims.

Desktop: [PSU logo / Hub / University] [Explore links] [Help description / Open Help / topic links]
Tablet: identity spans top row, Explore and Help share the next row.
Phone: identity → Explore → Help, then copyright / Back to Top.

Explore: Activities, About Us, Review Source Records. Help: one Open Help directory
link plus account-access and privacy/participation help articles. These are guidance,
not official policy documents. Back to Top is a native fragment/focus target. Use the
existing Philippine-local home timestamp's year with no new query.

Preserve the carousel, all other landing sections, existing calculations, public/auth
and signed-in footers, unrelated work and preview data. Scope all changes to landing.

## Implemented behavior

One landing-only navy footer replaces the blue Help strip and white footer. The
desktop grid contains identity, Explore and Help. Tablet identity spans the first row;
phone stacks all three. A gold top border and compact lower row close the page.

Explore retains Activities, About Us and Review Source Records. Open Help is the
footer's only Help-directory link; Account Access Help and Privacy and Participation
Help lead to existing public-safe articles. No official-policy, contact or social
destinations were invented. Current copy outside the footer is unchanged.

`footer_year` reuses the already computed Philippine-local `now.year` from the home
route, adding no query. Back to Top links to the native focusable navigation fragment.
No JavaScript is required. Focus is gold, links have hover feedback and 44px targets.
Print changes the navy surface/text to readable ink and keeps useful links visible;
Back to Top is hidden in print. Shared `.public-footer` and role/auth footers remain.

## Verification — 15 November 2026

- `pytest tests/test_landing_footer.py tests/test_landing_restoration.py -q`:
  **21 passed**. Public and all three signed-in roles resolve every footer destination;
  one Help-directory link; native fragment target; dynamic year; other footer scope;
  existing wording, activity eligibility, covers/empty states and historical counts.
- Chromium: **12 check groups passed**, no page errors. 320/390/768/844 landscape/
  1024/1440px; footer link target heights, Back to Top position/focus with and without
  JavaScript, 200% text and readable print. Existing photo/activity controls, six-second
  timing, pause/resume, reduced motion, empty states and keyboard skip remain covered.
- Before evidence: **6** matching viewport captures. Footer-only screenshots are in
  `.qa-overhaul-temp/landing-footer/before/` and `after/`, named `footer-<width>.png`.
  Full landing, `footer-200.png`, `footer-print.png` and JSON evidence are beside them.
- Tailwind build, **115 Jinja templates compiled**, `git diff --check` passed.
- Blue-100/navy **11.37:1**; navy/gold Help action **8.03:1**. Both pass normal-text AA.
- No full historical-suite, physical-device or manual screen-reader claim. Earlier
  unrelated historical fixture/selector failures remain documented in prior QA notes.

## Audit and delivery gate

Reviewed changed footer against the
[current Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md),
fetched 15 November 2026. Native named links/navigation, headings, logo dimensions and
decorative alt, contrast, hover/focus, 44px targets, intentional reflow, long text,
fragment focus and print checked. No unresolved changed-footer findings.

Antislop during-work gate: ENERGY 2 / RHYTHM 2 / MOTION 1. The PSU identity group,
real Explore links and single Help action provide a purposeful ending; gold is the
existing institutional accent. No fake contacts, claims, decorative cards, animation
or new imagery. Other page areas and workflows are preserved.

## Local review and rollback

Open `http://127.0.0.1:5000/#footer-explore`, or scroll to the landing footer. Existing
preview accounts remain available, all password `password`; data/uploads are retained
and mail suppressed. Scope is landing only, not a shared public-footer replacement.

```powershell
npm run build
.venv/Scripts/python.exe -m pytest tests/test_landing_footer.py tests/test_landing_restoration.py -q
.venv/Scripts/python.exe scripts/qa_landing.py --stage after --output-root .qa-overhaul-temp/landing-footer
```

Rollback only this pass's footer markup/navigation target, `footer_year` context,
`.landing-footer` rules and associated print rules; restore the former landing Help
strip rules if reverting. Keep the restored carousel template content/script and all
prior uncommitted header/Help/Partners/Accounts work. Rebuild Tailwind and restart the
private preview. The landing QA runner belongs to the prior restoration pass; do not
delete it during footer rollback. No branch reset, database replacement, new dependency,
migration, commit, push or deployment.
