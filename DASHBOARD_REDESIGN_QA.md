# Dashboard redesign verification

Date: 18 October 2026

## Implementation

Director and Coordinator dashboards and analytics use shared Jinja headings,
metrics, chart fallbacks, and native information disclosures. The role shell
contains the common responsive styles. `base.css` remains the only global
foundation; its focus outline now uses solid PSU blue.

Live analytics summaries, campus/category comparisons, trends, composition, SDG
mapping, and exports use the same filtered event report rows. Director report
pagination remains ten rows. Historical records have a separate source section.
Recognition, profile evidence, and campus readiness state their independent scope.

The four role guides share one native dialog and script. Completion, Skip, and
Escape save the authenticated account's dismissal timestamp with CSRF protection.
Help replays the appropriate guide without resetting that timestamp. Missing or
hidden anchors are skipped; responsive changes select a visible equivalent.

## Automated evidence

- Full pytest run: **212 passed, 1 failed**, approximately nine minutes.
- The remaining failure is the existing
  `TestAdminUserManagement.test_admin_reset_password`: it resets the signed-in
  administrator's own password and expects the earlier success message after
  session invalidation. The password-reset route and session-invalidation behavior
  were not changed by this redesign.
- Subsequent report-summary, workspace-status, and shared UI checks: **10 passed**. The extra status
  check verifies that past activities do not appear in the default upcoming target
  progress view.
- Coverage includes four role guide flags, saved dismissal, replay preservation,
  cross-account isolation, anonymous rejection, CSRF rejection/acceptance, report
  filter preservation, pagination, empty series, and report/chart count agreement.
- Python compilation, JavaScript syntax checks, and `git diff --check` passed.
- General test-account fixtures now supply a declared sex response. Legacy missing
  data tests explicitly use null, so profile-completion redirects do not mask role
  isolation tests.

## Browser evidence

The app was run against an isolated in-memory SQLite database on port 5055 with
CSRF enabled. Deployment MySQL records were not altered.

- Director, Coordinator, Volunteer, and Admin guide steps rendered for their roles.
- Back, Next, Finish, Skip, Escape, and focus restoration were exercised.
- Keyboard Tab remained in the modal. The first-step Back action was hidden.
- Volunteer profile completion preceded the automatic guide.
- Saved dismissal survived reload. Help returned to the correct `?tour=1` dashboard.
- Resizing a Coordinator guide from desktop to 390px selected the visible Create
  Activity link instead of the collapsed sidebar link.
- Director/Coordinator pages were inspected at desktop, 1024px tablet, and 390px
  mobile widths. The mobile disclosure expanded inline. Page width stayed within
  the viewport; tables use named internal scroll containers.
- A 640 x 450 CSS viewport checked reflow equivalent to a 1280 x 900 display at
  200% zoom. Native browser zoom itself was not available in the preview controls.
- Native chart-value disclosures opened successfully. Their values are rendered
  by Jinja and do not depend on Plotly or JavaScript. JavaScript was not disabled
  in the preview browser.
- A filtered Coordinator CSV and PDF were downloaded. The CSV contained only the
  selected Lingayen Environment activities and retained the selected date range.
- No browser JavaScript errors were reported during the final analytics check.
- Destructive account/activity actions were deliberately not exercised.

Reduced-motion CSS disables sidebar/tour transitions; spotlight scrolling is
instant. OS reduced-motion emulation was not exposed by the preview browser and
still merits a final check in the deployment browser.

## Design decisions

- PSU blue establishes hierarchy and actionable focus; gold marks the current
  guided target.
- Existing Inter typography keeps the institutional identity consistent.
- One filtered metric strip removes repeated totals with conflicting scopes.
- Paired comparison charts precede supporting evidence and detailed reports.
- Activity row actions use a native disclosure to keep schedules readable.
- Native details and dialog preserve platform semantics without a new dependency.
- Dials: **ENERGY 1 / RHYTHM 2 / MOTION 1**.

## Anti Slop delivery gate

- Hard gate PASS: sourced report counts, local PSU assets, real route controls,
  native keyboard behavior, measured responsive reflow, explicit empty/error
  states, and no new framework or decorative assets.
- Purpose gate PASS: the visual decisions above explain the palette, hierarchy,
  typography, disclosures, spacing, and limited spotlight accent.
- Liveliness gate PASS: the declared institutional direction uses a clear primary
  action, comparison-first reporting, structured spacing, and PSU identity.
- Craftsmanship gate PASS for the changed UI: shared components, role-specific
  content, persistent account state, labelled controls, and actual report scopes.
  The unrelated baseline test failure and browser-check limits are recorded above.

## Web interface review

Reviewed against the [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md).

- `templates/partials/info_tip.html`: native disclosure, accessible name, hidden
  decorative icon, 44px target, solid focus outline.
- `templates/layouts/role_base.html`: skip link, named main region, CSRF metadata,
  and inert mobile sidebar while closed.
- `static/scripts/first-use-tour.js`: labelled modal, keyboard containment,
  dismissal error handling, focus restoration, visible targets, resize handling.
- `static/styles/role-shell.css`: contained table overflow, mobile coach sheet,
  safe-area padding, reduced-motion rule, and visually hidden helper text.
- Contrast evidence on white: PSU blue **9.97:1**, secondary text **9.31:1**,
  second chart series **6.09:1**. PSU blue on the selected pale-blue surface is
  **7.71:1**.
