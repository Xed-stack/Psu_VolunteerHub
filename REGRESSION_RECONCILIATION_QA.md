# Baseline report/profile test reconciliation

23 October publication follow-up: the user approved committing and pushing this
verified test/documentation repair. The no-publication and HEAD/index statements
below preserve the verification-time snapshot; verify the published revision with
Git and GitHub main. This does not authorize deployment or live-database changes.

22–23 October 2026. Test and documentation changes only, based on published commit
`be44a31fce67489a82e89eba844cad11b096ca23`. Production Python, templates, CSS,
JavaScript, query contracts and database schema are unchanged. Local attachments
are preserved. No live database access, seeding, migration, deployment, commit or
push is included in this task.

## Reproduced causes

Before editing, the exact three previously failing tests reproduced with
**3 failed in 9.86s** on the current checkout:

1. `TestReportingSystem::test_director_campus_paging_and_supplementary_forms`
   counted hidden campus inputs across the whole document and expected the old
   combined live/historical view. Live and Historical Source Records now have
   separate views. The live award-year form preserves each selected campus once;
   the historical form has its own campus/year/activity-type controls.
2. `TestAnalytics::test_report_pagination_and_exports_preserve_all_selected_filters`
   required every incoming historical filter on live navigation/export URLs.
   Existing production behavior deliberately separates these destinations. Live
   pagination keeps live filters and `view=live`; live exports omit page/view and
   historical year/activity-type keys. Legacy `campus_id`, affiliation/department
   and award-year values retain their existing query compatibility.
3. `test_profile_repair.py::test_milestones_require_completed_present` searched
   for the literal `<td>Eligible</td>`. Responsive profile rows correctly render
   `<td data-label="Certificate">Eligible</td>`. Eligibility logic was not faulty.

The earlier **450 passed, 3 failed in 1130.79s** verification remains a historical
snapshot in REGISTRATION_CANCELLATION_UI_QA.md; it is not rewritten as a green run.

## Repairs and stronger checks

- A small test-only standard-library `HTMLParser` helper locates forms, successful
  named controls and table cells without relying on whitespace, attribute order
  or unrelated forms. A helper regression includes repeated controls, a same-name
  hidden control in another form, selected options, unchecked controls and escaped text.
- The award-year form is identified by its select, not the same-name hidden
  input in the primary filters. Its complete submitted values are asserted and
  followed to a rendered report.
- Thirteen matching fixtures span two selected campuses. Deliberately excluded
  campus, date, category and title fixtures must not appear. Following pagination
  yields exactly ten then three rows, in order; CSV and PDF input include all
  thirteen rows, not just the displayed page.
- Destination-specific live-link checks run for include, exclude and legacy
  campus URLs. They compare the complete generated query maps, follow page links,
  verify ten/two matching rows and all twelve exported activities, and retain
  department/award-year/sex values without redefining their report semantics.
- A separate historical test supplies conflicting live filters plus historical
  campus/year/activity type. Its form and export links contain only historical
  context. Matching records aggregate to two activities and sixteen participations;
  wrong campus, year and type records are excluded. CSV rows equal the actual
  ReportLab table input while a real historical PDF is still generated.
- Profile assertions associate each Certificate cell with its activity in Recent
  registrations. Completed/present is Eligible; pending/present, cancelled/present,
  completed/absent, completed/excused and completed/missing-attendance are not.
  Two parameterized renders each contain exactly five records, retaining the
  one-completed-participation count, Bronze milestone and responsive cell labels.
- Existing authorization, invalid-filter, empty-result, literal-search, dashboard
  scope and real live-report PDF-generation tests are retained.

Ponytail full kept the repair test-only, using the standard library and existing
fixtures. Anti Slop was applied during work to keep comments and evidence factual.
No UI redesign or production behavior change was needed, so this is not a new
visual/accessibility audit.

## Verification

- Initial repaired/new targeted selection: **8 passed in 21.25s**.
- Existing dashboard scope/count selection: **3 passed in 0.35s**.
- Broader focused selection: **97 passed in 233.32s**. This includes
  `TestReportingSystem`, `TestAnalytics`, profile repair, responsive tables, shared
  UI structure and the HTML helper check.
- Final uninterrupted full suite: **458 passed in 1141.90s (19:01)**. JUnit records
  458 tests, zero failures, zero errors and zero skipped tests. No Windows
  subprocess/upload-fixture/temporary-folder permission errors occurred.
- The collected total increased from 453 to 458: one HTML-helper check, one
  historical-scope check, two additional live-scope parameter cases and one
  additional profile-attendance case. No tests were removed, skipped or marked
  expected-to-fail to obtain this result.
- `git diff --check`: passed after the test edits.

All pytest runs use `create_app('testing')`, isolated SQLite and disposable files,
not the development application or original MySQL. Runs outside the sandbox retain
working Windows Node-subprocess and temporary-upload permissions; application
security settings are not weakened.

Evidence directory:
`C:\Users\arlro\.codex\visualizations\2026\10\18\01a14c77-a036-7241-ad82-ee16a46acd99\regression-20261022`

The full, focused and dashboard runs wrote `full-results.xml`,
`focused-results.xml` and `dashboard-results.xml` there. Evidence and temporary
files are not added to the repository.

Outcome: all three reproduced baseline failures are resolved with stronger
assertions and no production mismatch exposed. `git rev-parse HEAD` still reports
`be44a31fce67489a82e89eba844cad11b096ca23`; no changes are staged. The production-file
diff against that commit is empty. Only tests and QA/handoff/roadmap documents
changed; user attachments remain untouched.

## Remaining gates

Actual browser 200% zoom, screen-reader and physical-mobile checks remain separate
release gates. This test-only repair does not complete them, certify production
MySQL concurrency or authorize publication/deployment. Earlier QA screenshots and
verification snapshots remain historical evidence, not newly repeated checks.
