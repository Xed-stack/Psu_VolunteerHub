# Security remediation — 29 October 2026

Continuation note, 31 October 2026: this is a separate local remediation
workstream and its recorded evidence, not a new audit performed by the dashboard
task. Unrelated security changes were preserved during Director UI integration
and remain outside that feature's publication scope. See
[HANDOFF.md](HANDOFF.md#current-handoff-31-october-2026) for current state,
decisions, skills actually used, next steps, and verification boundaries.

These changes address the run-2 report in the local worktree. They have not been
deployed. Historical audit evidence remains unchanged.

| Plan item | Local change | Remaining work |
| --- | --- | --- |
| 1. Confirmation handlers | Autoescaped `data-confirm` text and a shared submit listener replace executable interpolation in both dashboards. | Validate the deployed release after rollout. |
| 2. PDF metadata | Escape title, category, role label and historical note before ReportLab Paragraph parsing. | None for the reported source path. |
| 3. External participant reuse | Lock an existing participant row and require registrations exclusively in the destination campus before reuse. Reject unowned or mixed-campus records before disclosure or mutation. | Interim authorization fix; IDs remain globally unique. A campus-key migration requires explicit handling of multi-campus registrations and orphan rows. No production schema change was made. |
| 4. Deactivation | Consume recovery tokens and increment `auth_version` in the same transaction as deactivation. | None for the reported lifecycle path. |
| 5. Coordinator scope | Dashboard calls the fail-closed campus helper; Admin creation, promotion, editing and CSV import reject campus-less coordinators. | Assign a valid campus to existing unassigned coordinators before restoring access. |
| 6. Recovery throttling | Independent account, source and combined budgets. | Operator must verify the ingress-derived IP. |
| 7. Recovery timing | Commit recovery token, then dispatch provider delivery in a background thread, capped at four deliveries per process. | Mitigated: database/dispatch timing remains. Delivery is best effort, without durable retries; restarts or exhausted dispatch capacity can lose mail. Restart-safe delivery needs an outbox/worker. |
| 8. Deployment identifiers | Replace live identifiers in recovery QA notes with placeholders. | Historical Git exposure remains known. No history rewrite or infrastructure change. |
| 9. Spreadsheet export | Prefix formula-leading text in human-facing CSV exports. Backup serialization remains unchanged. | Actual supported spreadsheet/import settings still need owner validation. |
| 10. Proxy trust | Explicit `x_host=0`, production hop-count validation (1–10), existing Werkzeug 3.0.3 pin retained. | Operator must confirm hop count and edge header overwrite behavior. |

## Operator checks before release

Confirm that `TRUSTED_PROXY_COUNT` is the number of trusted forwarding hops and
that ingress overwrites untrusted forwarding headers. Zero is now rejected in
production. Do not choose a count from the allowed range without checking the
actual ingress chain.

The participant guard preserves the existing schema. It deliberately refuses
linking an ID already used by another campus. Before replacing it with a campus
dimension, rehearse a migration on a disposable database copy: a participant with
registrations in multiple campuses needs separate records and registration
relinking, not an arbitrary campus assignment. Review orphan rows explicitly.

## UI review

Design read: existing PSU administration controls for university staff; retain
the established blue/gold identity, typography, spacing and action hierarchy.
ENERGY 1 / RHYTHM 1 / MOTION 1. Native confirmation serves the existing destructive
action workflow and supports ordinary keyboard activation. No visual redesign.

The changed form attributes retain labels and native buttons. Confirmation runs
before the existing busy-state listener, so cancelling leaves controls usable.
The current [Web Interface Guidelines](https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md) were fetched and reviewed for the changed
interaction. Browser verification checks benign and quote-bearing values,
Cancel/Accept, focus and busy-state behavior. Physical-device, screen-reader and
deployment checks are separate from this local regression result.

## Verification

103 distinct targeted Python cases passed in the isolated no-network sandbox:
29 security remediation, 28 recovery/email, 15 external-participant, 13 Admin
management, and 18 production startup/provisioning cases. The full application
suite was not run. Native image/ML imports were guarded and unused; ReportLab
rendered PDF fixtures with resource loading patched to fail immediately.

Real Chromium checked the production-factory pages with benign and hostile
values. Cancel stopped submission without entering the busy state; Accept
reached the busy state. No destructive request was delivered to the app.
Native Enter-key confirmation passed on both pages. At 320px and 375px,
confirmation targets measured at least 44 × 44px and document width equaled
viewport width. Existing danger-button text measured 6.46:1 contrast and the
category icon's blue on white measured 9.97:1. No visual styles changed.
The historical audit and per-group source hashes are retained outside the repo
in the run-2 audit artifacts.
