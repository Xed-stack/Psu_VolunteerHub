# PSU Volunteer Hub — UX, Analytics, and Administration Roadmap

## Purpose and delivery order

This roadmap improves the current Volunteer Hub while keeping the first releases aligned with the manuscript: volunteer profiles, activity posting and registration, attendance and participation history, milestone transparency, recommendations, descriptive analytics, and PDF/CSV reports. The work is ordered to improve the public and volunteer experience first, then the reporting experience, then governance extensions.

The working tagline is: **“Serve with purpose. See the impact.”**

Use clear Filipino-English wording where it improves comprehension, but retain English labels for institutional reports and data fields. Replace the volunteer-facing word **Register** with **Join Now**; keep `Registration` as the internal data term.

## Phase 1 — Landing page, discovery, and joining

- Rebuild the public home page as a content-driven landing page with: a PSU volunteer image hero, the tagline, clear sign-in and Browse Opportunities calls to action, a small feature section, upcoming events, recent completed activities, and help/contact links for non-technical users.
- Use approved PSU images when supplied. Until then, show existing coordinator-uploaded event cover images and milestone photos; cards without an image use the present accessible fallback artwork. Do not add unlicensed stock photos.
- Add a featured-events carousel from the nearest upcoming activities. Each slide shows cover image, title, campus, category, start and end date/time, remaining slots, and a **Join Now** action.
- Add event preview modals for public and signed-in users. The modal contains the complete event information, dates, location, required skills, cancellation deadline, and the Join Now action. A signed-in volunteer submits the normal registration form; a guest is offered sign-in and then returns to the selected event. The existing outsider join path remains available.
- Rework the opportunities list with a banner, image cards, start/end dates, specific campus/category dropdown filters, alphabetical campus ordering, keyword search, and a multi-select campus filter that supports excluding campuses. Keep the listing paginated and accessible without JavaScript.
- Make the homepage’s historical-activity summary clickable. It opens a paginated historical-activity list with title, unit/campus, activity type, year, aggregate participant count, source information, and any available details. Historical aggregates remain separate from live events.
- Add completed-event story cards below the upcoming section. They are generated from finished live events and their milestone uploads, showing the event date range, completion status, featured image, and a details modal/page; no separate editorial article workflow is introduced in this phase.
- Add an application-wide loading state for form submissions and data-driven navigation: disable the submitting control, show a labeled spinner, retain keyboard focus, and restore controls after validation errors. Do not use an indefinite blocking overlay for ordinary page loads.
- Add a lightweight, dismissible first-use guide for new users. It highlights profile completion, recommendation results, event browsing, and the Join Now action. Store dismissal per account so it does not recur.
- Add an always-visible Help link to the public navigation and role sidebar. The help page explains signing up, profile interests/skills, joining, cancelling, attendance, recommendations, and who to contact for account issues.

## Phase 2 — profile, registration, and coordinator controls

- Convert volunteer skills and interests to controlled multi-select choices backed by the existing `Skill` and `Interest` catalogs. Require at least one interest and one skill at account creation and profile update; do not create free-text categories from volunteer input. Display an explanation that recommendation quality depends on profile and participation data and that results are decision support, not guarantees.
- Improve password entry with a show/hide control, a strength checklist, confirmation field during account creation or password reset, and server-side validation. Preserve the administrator-configured minimum length and reject passwords that fail the chosen policy.
- Add an optional profile image upload with validation, a generated unique filename, image type/size checks, and a default avatar. Display it in the sidebar and volunteer profile. Deleting a user removes the associated image safely.
- Extend `Event` with `cancellation_deadline` (`DATETIME`, nullable). Coordinators must set a deadline before the event start when creating or editing an event; the UI may offer a quick preset such as “2 days before” but saves the actual deadline. Volunteer cancellation is allowed only for eligible statuses before that deadline. Show the deadline in the event preview, Join confirmation, dashboard registration list, and cancellation confirmation.
- Keep existing event start and optional end dates, but make both date/time inputs explicit in coordinator create/edit forms. Validate that end is after start and that cancellation deadline is before start.
- Add coordinator announcements per event: **last call**, **event update**, and **cancelled/postponed**. Publishing an announcement creates in-app notifications for active registered PSU volunteers and shows it in event details. This uses no SMS or email integration.
- Record the uploading coordinator and timestamp for event covers, milestones, historical imports, and administrative bulk imports. Show that provenance in coordinator/admin management screens and event transparency details.
- Replace the Activity Categories text **Remove** control with an accessible icon-only **×** button, retaining confirmation, tooltip/accessible name, and the existing reassignment-to-General behavior.
- Keep QR attendance as a documented standby item only; do not add QR generation, scanning, or check-in flows in this roadmap release.

## Phase 3 — descriptive analytics and reports

Current implementation note: descriptive analytics, PDF/CSV reporting, historical aggregate views, and an idempotent local `seed-demo-analytics` fixture are implemented. The fixture supplies representative live events, registrations, and attendance for panel demonstrations; it does not alter deployment data unless the command is explicitly run against that database.

- Keep analytics limited to descriptive reporting defined by the manuscript: counts, percentages, means, attendance/sign-up conversion, participation by campus/category/demographic, activity performance, and weekly/monthly trends. Do not expose K-means segmentation or ANOVA in the user interface.
- Move role-appropriate KPI summaries to the top of analytics pages. Make each event-count KPI clickable and route it to the corresponding filtered event/report list; for example, a summary of 50 events opens that 50-event filtered list.
- Add a search field to the Live Activity Report and initially display ten rows. Provide **View all** to expand/paginate without losing the active filters.
- Add date range plus multi-year comparison controls. A user may choose one or more years; comparisons use the same selected campus, category, and activity-name criteria. If a same-named activity has no comparable data, show an explicit empty state rather than inventing a match.
- Add the existing campus filter as a multi-select include/exclude control, alphabetize the options, and keep it restricted to the role’s permitted campus scope. “School of Graduate Studies” is treated as a selectable campus only if it exists in the existing campus catalog; no new academic-unit data model is added.
- Let users change supported visualizations where the metric is compatible: line for time series, bar for comparisons, and pie/donut for composition. Preserve a text/table equivalent for accessibility.
- Add Plotly chart controls for zoom, reset, and exporting the active chart image. Retain current PDF/CSV report exports for the filtered report as a whole; do not attempt browser screenshots as official reports.
- Label historical imports as aggregate records and show a short data-quality note: historical counts cannot produce individual attendance, demographics, or precise event dates not recorded in the source. Add the same limitation to analytics export metadata.
- Keep the repeatable `seed-demo-analytics` fixture for local development and panel demonstrations. It creates representative events, registrations, and attendance without modifying real deployment data unless explicitly run there. Historical aggregate imports remain separate through `import-historical-activities`.

## Phase 4 — administration and governance extensions

Current implementation note: the administrative activity log, safe CSV user import/export, and versioned Terms of Use acceptance are implemented. The remaining governance enhancement is any broader administrative policy workflow beyond the currently published Terms of Use revisions.

- Add CSV bulk-user import and export. Import uses a downloadable template, validates all rows before committing, reports row-level errors, hashes passwords server-side, and honors the existing role/campus constraints. Export excludes password hashes, tokens, and other secrets.
- Add an append-only activity log with actor, action, target type/id, timestamp, and a concise metadata summary. Record account actions, role changes, category changes, event create/edit/delete, attendance updates, milestone uploads, announcement publication, historical imports, and bulk-import outcomes. Admins can filter and export the log; coordinators see only records within their campus.
- Add versioned Terms and Conditions managed by an administrator. A published revision has title, body, version, publisher, and publication timestamp. New registrations and existing users on their next sign-in must accept the current revision before continuing; record user, revision, and acceptance timestamp. Do not retroactively invalidate attendance or historical registrations.
- Add a migration for profile images, event cancellation deadlines, announcement records, upload provenance, activity logs, and terms acceptance. Backfill upload provenance as unknown where the historical record lacks an actor. Existing events retain a null cancellation deadline and continue to use their start time until a coordinator sets one.

## Phase 5 — policy, agreements, cancellation review, and accomplishment management

Current status: planned only. Do not replace the existing direct cancellation flow until the full request-and-review workflow, migration, authorization checks, notifications, and regression tests are ready together.

- Add distinct Terms of Use acceptance and Privacy Notice acknowledgement to account registration. Record each document version and timestamp separately; never combine the two acknowledgements into one checkbox.
- Require a versioned Event Participation Agreement for every event registration. Store acceptance on the registration record, not only on the volunteer account, so each event remains auditable.
- Let coordinators configure an optional event-specific NDA, including its text and version. Require NDA acceptance only after the participation agreement. Cancelling a registration must never invalidate a previously accepted NDA or prevent a volunteer from requesting cancellation.
- Replace direct volunteer cancellation with a cancellation-request workflow. A volunteer chooses a structured reason (medical/health, family emergency, academic conflict, work/schedule conflict, transportation problem, personal emergency, or other); `Other` requires an explanation. A pending request leaves participation registered until reviewed.
- Add campus-scoped coordinator review for cancellation requests with pending, approved, and rejected filters; reviewer note; reviewer identity; and review timestamp. Approval changes participation to cancelled. Rejection keeps it registered. Preserve every request and decision as an audit-relevant record.
- Reuse the existing notification service to alert coordinators about new requests and volunteers about submission, approval, or rejection. Do not create a second notification system.
- Extend event list filters for coordinator activity management: Active by default, with Upcoming, Completed, Cancelled, and All options plus category, date, campus, and department where data exists. Replace vague `Unavailable` labels with disabled actions and accessible supporting text that explains why the action cannot be used.
- Add a list/calendar switch for activities. The calendar supports monthly navigation, status, campus/department, date range, and event details; list filters should apply where practical.
- Add optional activity targets: target participants, verified actual participants, and safe target completion percentage. For completed events, actual participants must be verified attendance—not registrations. Clearly label registrations for upcoming/active activities.
- Reorder Coordinator and Director dashboards around accomplishments: KPI cards, charts, targets, actual participants, activity/campus comparisons, and supporting lists. Add a simple role-appropriate volunteer dashboard visualization without exposing coordinator/director analytics.
- Introduce centralized, data-driven campus acronyms for compact director comparisons, while retaining full campus names in reports, details, tooltips, and accessible labels.
- Test agreement/NDA acceptance, every cancellation boundary and role scope, audit retention, notification recipients, target calculations including zero targets, and the distinction between registrations, attendance, absence, cancellation, and actual participants.

## Interfaces and safeguards

- New public/volunteer views: event details/preview, historical activity list, help page, and terms acceptance page.
- New protected actions: profile image upload/remove, event announcement create, terms publish, terms accept, CSV user import/export, and activity-log listing/export.
- All state-changing forms use the existing CSRF protection, role checks, server-side ownership checks, input validation, and explicit success/error notices.
- Enforce image file allow-lists and size limits; never serve user-selected filesystem paths directly.
- Preserve role boundaries: volunteers cannot access analytics or other users’ records; coordinators remain campus-scoped; directors remain read-only; administrators retain user/configuration governance. Admin analytics remains hidden from navigation as currently requested, even though its implementation remains intact for possible panel restoration.

## Verification and acceptance criteria

- Test desktop and mobile landing pages, keyboard-accessible carousel/modal behavior, empty states, image fallbacks, readable contrast, and loaders for successful and failed submissions.
- Test guest Join Now redirects back after sign-in, volunteer registration/re-registration, outsider registration, capacity checks, start/end-date validation, and each cancellation-deadline boundary.
- Test controlled skill/interest selection, password validation, profile image validation/removal, first-use guide persistence, and recommendation limitation copy.
- Test all analytics filters together: alphabetical campuses, include/exclude campuses, multi-year comparison, first-ten/View all, KPI drill-down, chart type switching, chart image export, and report export with unchanged role scoping.
- Test historical versus live data separation and the simulated fixture in an isolated development/test database.
- Test CSV import validation/atomicity, safe export columns, audit-log completeness and access control, terms re-acceptance after a new publication, and announcement recipients.
- Run existing authorization, event, volunteer, coordinator, admin, analytics, and UI-structure tests; add coverage for every new endpoint, migration backfill, and destructive action.

## Defaults and exclusions

- The first implementation focus is public/volunteer UX, followed by analytics, then administration extensions.
- Images are PSU-approved or system-uploaded only; placeholders remain until approved images exist.
- Event stories are derived from completed events and milestone uploads, not manually authored news articles.
- Cancellation is controlled per event by an explicit deadline, with a quick two-day preset available to coordinators.
- QR attendance, automated certificate generation, email/SMS, SIS integration, GIS, financial features, and automated account purging remain out of scope.
