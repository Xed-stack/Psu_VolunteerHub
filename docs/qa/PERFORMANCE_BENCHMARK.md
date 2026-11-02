# Performance verification, 2 November 2026

The candidate is based on `c960159`. Local measurements use isolated MariaDB
10.4.32, mysqlclient, a 128 MiB database buffer pool and a five-connection app
pool. The benchmark contains 1,000 activities, 50,000 registrations, 1,000 new
volunteers, active Terms/Privacy acceptances, 30 mapped annual targets,
cancellations, incomplete attendance, notifications and historical records.
The existing presentation and performance seed commands were not changed.

## Baseline

Warmed probes of the previous code using the same policy-aware fixture:

| Workflow | SQL statements | Local elapsed |
|---|---:|---:|
| Public opportunities | 6 | 11.6 ms |
| Volunteer dashboard | 33 | 73.8 ms |
| Coordinator dashboard | 34 | 379.5 ms |
| Coordinator analytics | 31 | 347.0 ms |
| Attendance page, 50 participants | 109 | 39.4 ms |
| Director dashboard | 46 | 3,505.5 ms |
| Live analytics | 47 | 3,494.2 ms |
| Historical analytics | 48 | 3,452.4 ms |
| Annual-goal details | 27 | 4,671.8 ms |
| Notifications | 7 | 4.1 ms |
| Full CSV | 11 | 175.4 ms |
| Full PDF | 11 | 440.2 ms |

These are individual warmed probes, not p95 results or Railway measurements.
The baseline fails the planned query budgets. Query counts include policy checks.

## Final local comparison and load test

| Workflow | SQL before / after | Warmed elapsed before / after |
|---|---:|---:|
| Public opportunities | 6 / 4 | 11.6 / 6.4 ms |
| Volunteer dashboard | 33 / 16 | 73.8 / 23.1 ms |
| Coordinator dashboard | 34 / 19 | 379.5 / 102.5 ms |
| Coordinator analytics | 31 / 18 | 347.0 / 83.8 ms |
| Attendance page | 109 / 9 | 39.4 / 10.6 ms |
| Director dashboard | 46 / 21 | 3,505.5 / 601.4 ms |
| Live analytics | 47 / 18 | 3,494.2 / 368.3 ms |
| Historical analytics | 48 / 10 | 3,452.4 / 7.2 ms |
| Annual-goal details | 27 / 10 | 4,671.8 / 576.0 ms |
| Notifications | 7 / 5 | 4.1 / 5.3 ms |
| Full CSV | 11 / 6 | 175.4 / 178.5 ms |
| Full PDF | 11 / 6 | 440.2 / 544.6 ms |

The final policy-aware workload completed 12,568 requests and 1,250 writes in
1,035.37 seconds (12.14 requests/second), including the 15-minute 50-user hold.
There were zero HTTP errors, inconsistent persisted writes or duplicate
registrations. All 50 actors completed registration/cancellation/review; twenty
contenders for the last place admitted exactly one. Peak app RSS was 242.08 MiB,
74.5% below the explicit local 950 MiB budget; database connections peaked at five.
CPU time was 620.23 seconds, including local clients.

| Workflow at 50 users | p95 | Maximum SQL statements |
|---|---:|---:|
| Signed-in opportunities | 560 ms | 7 |
| Volunteer dashboard | 599 ms | 16 |
| Coordinator dashboard | 732 ms | 19 |
| Attendance page | 497 ms | 9 |
| Director dashboard | 1,400 ms | 21 |
| Live analytics | 1,147 ms | 18 |
| Annual-goal details | 1,362 ms | 10 |
| Notifications | 485 ms | 5 |
| Registration save | 1,419 ms | 13 |
| Cancellation save | 384 ms | 11 |
| Cancellation review | 399 ms | 9 |

Attendance saves used six statements in the workload. The separate 50-request
opportunities burst had 305 ms p95 while its concurrent PDF completed in 673 ms.
All measured local latency/query/headroom checks passed. The runner's JSON is at
`.qa-presentation-temp/performance-final-policies.json`; baseline and index
evidence are alongside it. These ignored local artifacts contain no live backups.

The runner uses local Werkzeug with four request slots. It checks Flask session
isolation, query growth and MySQL behavior, but does not prove Gunicorn worker
health or Railway latency/capacity. CPU includes the local client work; RSS excludes
the separate database process. Cold starts, actual hosting memory headroom and
the 30-minute Demo observation require separate Railway validation.

## Index evidence

All eight candidates were selected by the disposable MariaDB optimizer. Event
date and campus/date lists, registration history and notification order lost their
filesort; capacity, attendance, unread and throttling obtained composite coverage.
Warmed median SELECT times improved in these small local probes; this is evidence
for the plans, not a claim of a large latency gain on a small presentation dataset.
Apply, repeat application and rollback were verified on disposable MariaDB.
Rollback recreates required foreign-key support indexes before dropping owned
composites because MySQL/MariaDB can silently replace their original automatic indexes.

Actual Railway indexes still require preview/EXPLAIN review before applying DDL.
Commands, backup requirements and rollback are in
[the operations guide](../operations/PERFORMANCE_ROLLOUT.md).

## Correctness and interface evidence

Focused reporting, annual-goal, shared-target, ranking, cancellation, registration
and unchanged-fixture regressions passed in staged runs. The final 50-person save
check verifies real single SQL statements rather than hiding per-row driver loops
behind `executemany`, and verifies that records on the next page remain unchanged.
New query budgets use active policy records and cover both anonymous and signed-in
opportunities. Request-local values reflect the next committed notification update.
The final performance/loader run passed 22 tests. Startup/configuration/error/security
checks passed 79 tests; the remaining loader assertion was updated for eager loading
and then passed in that final run.

Forty browser checks cover eight paginated workflows at 1440, 900, 768, 390 and
320 pixels. Checks passed for keyboard navigation, visible focus, 44px link targets,
contained table overflow, no page overflow and unsaved-attendance protection.
No JavaScript errors were observed. No manual screen-reader or physical-device
verification is claimed.

PSU direction is unchanged: Inter, navy/blue/gold, existing spacing and native
navigation/disclosures. Antislop was applied during implementation as chosen in
the conversation, with ponytail/full, frontend-design, UI, human and mobile checks.
The current Web Interface Guidelines were reviewed for the changed UI. No new
decorative assets, animations or component system were introduced.

Five existing public-signup test failures reproduce on unchanged `c960159`:
`test_public_registration_cannot_create_privileged_role`,
`test_register_creates_user`, `test_register_accepts_prefer_not_to_say`,
`test_signup_errors_are_linked_and_retain_non_password_values`, and
`test_signup_preserves_existing_password_policy_and_records_consents`.
Do not describe the entire repository suite as green. These failures were not
removed or weakened as part of the performance work.

## Hosting observations before rollout

Demo app: Singapore; Demo database: US East; both use Serverless. A cold wake
initially refused a MySQL connection, followed by successful reads after startup.
Verified live totals: 92 accounts, 28 activities, 432 registrations and 296
attendance records. A protected dump restored into a separate recovery database;
all 37 table checksums matched. No dataset reset, live index change or region
change has been performed during this verification stage.

Main's database was offline and its last app deployment had failed before this
candidate. Main must not receive the candidate automatically before Demo passes.
