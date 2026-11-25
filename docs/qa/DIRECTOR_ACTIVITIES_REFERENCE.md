# Director Activities and Conditional Entry

Implemented locally on `codex/ui-workflow-overhaul`, 25 November 2026.

## Behavior

Director desktop Activities reuses the Coordinator cards through
`workspace/activity_cards.html`: schedule tabs/counts, search, campus/category
filters, registration progress and five-item pagination. Director cards add
location, SDGs, approval state and active finding counts. Create Activity and
Coordinator editing/attendance controls remain unavailable to Directors.
Director-only CSS takes effect from 1024px. The prior narrow presentation is
retained; both presentations use the same conditional entry action and pagination.
Coordinator card behavior and campus restrictions remain intact.

Activity title and action links open a Director-only `/activities/<id>/open`
endpoint. It rechecks the current findings instead of trusting the list badge:

- Active findings: redirect to `/workspace/follow-up` with the activity ID,
  all recorded dates, activity year, Active tab and page one.
- No active findings: redirect to Activity Details.

The existing review service determines active findings, including reviewed/
closed decisions and changed evidence. When review storage is unavailable, the
same generated findings used by the fallback queue determine routing. A
Coordinator's low-registration advisory alone does not create a Director review.
No new findings, thresholds, decisions or automatic review writes were added.
Campus/annual findings are excluded from an individual activity badge.

Direct Activity Details URLs remain available, including source links from review
pages. Return links preserve Activities filters/page. Existing Past Activities
date rules, permissions, report calculations and attendance locking are retained.
No schema, dependencies or operational database changes.

## Design Review

Read: PSU institutional operations dashboard, Energy 2 / Rhythm 2 / Motion 1.
Reuse the Coordinator composition, PSU navy/gold, typography and existing status
colors to maintain the requested direction. Gold attention styling marks actual
active findings. Registration progress is labelled as registrations against the
target, without implying completed attendance or a final target outcome.

High findings addressed: badge/queue consistency, event-scoped navigation,
closed/changed review handling, and preserving direct source-details access.
Moderate rendered findings addressed: a long campus dropdown squeezed search;
the Director filter grid now reserves search space. The fixed card rail caused
overflow at enlarged text; the Director rail now uses available grid width.
Multi-day end dates and missing end times are explicit. The pre-existing desktop
rule hiding `.needs-original` now applies only when a desktop replacement exists,
so the Director's generated fallback remains visible.

## Verification

30 focused cases passed across Director Activities, Coordinator Activities and
the existing finding-review workflow. Six Director/Coordinator cases passed again
after final route cleanup and campus validation. Tests cover active/no findings,
both workflow modes, closed decisions, changed/cleared evidence, stale list
entry, matching queue totals, filtering, ordering, pagination, return context,
invalid campus selection, authorization and read-only GETs.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_director_activities.py tests/test_coordinator_activities_reference.py tests/test_finding_reviews.py -q --tb=short -p no:cacheprovider --basetemp .qa-director-activities-temp/regressions
.\.venv\Scripts\python.exe scripts/qa_director_activities.py
```

Five Chromium groups passed with no page errors: 1440/1280/1024px layouts,
long campus names, scoped filters/counts/tabs, conditional entry in both workflow
modes, keyboard entry, return navigation, 200% root text sizing, existing narrow
presentation at 390px and JavaScript-disabled routing. Templates all parsed.
Evidence: ignored `.qa-director-activities-temp/browser/`. Final rendered review
confirmed visible search text, readable controls and no desktop page overflow.

CSS build and whitespace checks passed. No application JavaScript was changed.
The current Web Interface Guidelines were fetched on 25 November 2026 from
`https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md`.
Audit: no remaining in-scope findings. Native links/forms, accessible campus
label, visible focus, 44px controls, explicit empty states and overflow checks
cover the changed interface. Status text contrast passed: blue 7.15:1, green
6.78:1, gold 8.15:1 and neutral 9.45:1; existing PSU button/text pairings retained.

## Antislop Delivery Gate

- Hard PASS: build/browser/link/keyboard/empty-state checks; real scoped figures;
  no new assets or invented outcomes; contrast and overflow verified.
- Purpose PASS: shared Coordinator composition and PSU styling serve campus
  oversight; attention accents correspond to active findings.
- Liveliness PASS: declared 2/2/1 direction retained, clear Activities hierarchy
  and existing institutional navy/gold motif.
- Craftsmanship PASS: shared template and existing review service, native
  navigation, focused regressions and rendered critique; no decorative additions.

## Delivery and Limits

The existing port-5000 preview was restarted without seeding/migrations; the
authenticated Director Activities page returned HTTP 200 with new entry links.
The user authorized committing and pushing the remake and Cancelled-tab removal
to both configured `codex/ui-workflow-overhaul` branches. No manual deployment was
requested. Preserve
concurrent edits, including the fallback queue's return-link adjustment.
The isolated publication snapshot passed all six Director/Coordinator cases and
five Chromium groups again, including absence of the Cancelled tab. Generated
CSS was rebuilt from the staged source; unrelated Calendar/fallback edits were
excluded from publication.
Full-suite, physical-device, screen-reader and actual browser-zoom checks were
not performed; enlarged text used root font sizing. The mobile layout was not
redesigned. Rollback restores only this task's route/helper, shared card extraction,
Director presentation/styles, return-label support, tests and generated CSS.
Restore only task-owned portions of shared files. No database rollback applies.
