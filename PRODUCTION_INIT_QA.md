# Fresh production initialization verification

Date: 20 October 2026. Local implementation, not deployed or published.

Publication follow-up: the user subsequently approved committing and pushing
this verified feature, tests and documentation. Earlier local/unpublished notes
describe verification snapshots. No deployment or original database changes.

## Full regression follow-up

All **352 tests passed in 885.51s (14:45)** in one uninterrupted full run:

```text
python -m pytest tests -q -p no:cacheprovider --basetemp=<fresh-private-QA-directory>
```

Used approved outside-sandbox execution to avoid previously confirmed Node spawn
and default pytest temp-directory permission errors. The explicitly named QA
directory was verified nonexistent before the run. No skipped outcomes or
environment-related failures in this run; no application/assertion edits needed.
Scoped diff reviewed: provisioning command, deferred-commit reference helpers,
tests and documentation only. `git diff --check` passed (line-ending notices only).
No SQL dumps, credentials or diagnostic scripts included. Ready for publication
approval; no commit/push performed during this verification.

## Actual MariaDB result

Created a new disposable database: `psu_volunteer_initqa_20261020_bfdd5f4c`.
The script refused an existing target name before creation and verified the
application's selected database before any provisioning writes. No database was
overwritten. The test database is retained locally; credentials were randomly
generated in memory, not printed, saved or committed.

Used the real `init-production` CLI handler through Flask's CLI test runner,
production configuration, and the actual MariaDB engine. Ponytail full: reuse
the command and existing reference-data helpers; no parallel setup implementation.

| Check | Result |
| --- | --- |
| Production startup | Target remained empty until explicit command execution. |
| Wrong database name | Refused before writes. |
| Declined confirmation | Refused; schema remained empty. |
| Explicit confirmed setup | 31 tables, one Admin, 9 campuses, 8 interests, 12 skills, 17 SDGs. |
| No demo participation | Zero events, registrations, attendance, historical records. |
| Password handling | Generated password absent from command output; stored hash verified. |
| First Admin sign-in | HTTPS-scheme Flask test-client login with CSRF and Referer accepted; Admin dashboard returned 200. |
| Second initialization | Refused nonempty schema; all target table row hashes unchanged. |

The original `psu_volunteer_hub` was accessed only through server-enforced
read-only sessions. All 31 original table row counts and SHA-256 fingerprints
matched before/after (1,167 rows total). No original schema, account, password,
or record changes, no migrations applied there.

## Other evidence and limits

- Previously focused SQLite provisioning/startup/app-init/historical-import run:
  24 passed. No application or test code changed during the MariaDB verification.
- This is actual MariaDB-backed command and HTTP-handler verification, not a
  browser walkthrough, actual TLS certificate/proxy test, or Gunicorn deployment.
- The full-suite follow-up above supersedes the earlier pending-regression gate.
  Interrupted-DDL recovery remains a manual
  operational procedure; MariaDB DDL rollback is not claimed. Existing-table/view,
  invalid-input and simulated failure cases have isolated SQLite coverage.
- The diagnostic script lives outside Git in the local visualization folder;
  neither it nor database files or credentials are publication artifacts.
- No commit/push/deploy performed. Remaining gates include publication approval,
  hosting/HTTPS, SMTP, persistent uploads, backup/restore, policy setup and the
  deferred historical dump-exposure review.
