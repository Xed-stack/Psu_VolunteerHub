# Local backup and restore drill

Date: 20 October 2026. No application implementation change, commit or push.

## Verified

- Used installed MariaDB 10.4.32 native dump and restore clients. Source tables
  were all InnoDB. Inventory found zero views, triggers, routines and events;
  their nonempty restoration/DEFINER cases are not claimed as tested.
- Created new target `psu_volunteer_restoreqa_20261020_0bbf28ad`, refusing an
  existing destination. No restore into source, no database overwrite/deletion.
- Dump was single-database SQL without CREATE DATABASE/USE or source-qualified
  object references, using transactional snapshot and no source table locks.
- Restored **31 tables / 1,167 rows**, with matching schema and all row hashes.
  Includes password hashes; unlike the Admin CSV export, this preserves them.
- Restored ORM queries: 8 users, 35 events, 98 registrations, 81 attendance rows,
  216 historical records. Production-mode login page returned HTTP 200 through
  Flask test client using the restored database, with no automatic initialization.
- Copied and restored **2 public upload files** with identical relative paths
  and SHA-256 hashes. Configured private upload root had **0 files**.
- All original table schema/row hashes and original upload hashes matched
  before/after. Original comparison connections enforced read-only transactions.
- Native capture, restore, hash checks and HTTP smoke check took about **1.62s**
  for this small local dataset, excluding preparation. Not a production RTO claim.

## Artifact protection and retention

Artifacts retained outside Git under the local visualization folder:
`backup-restore-drill-0bbf28ad`. Contains SQL, file copies, restored file copies
and private checksum manifest. Directory ACL inheritance was removed; access
granted to the executing user, SYSTEM and Administrators. The initial sandbox
attempt could not set ACLs and stopped before data capture; approved execution
outside sandbox completed the restricted drill. An empty failed-attempt directory
may remain (`backup-restore-drill-e9e0394b`), containing no captured database data.

Temporary native-client credential file was removed by its temporary-directory
context. No credentials, private manifest or backup SQL added to the repository.
Backup and restored database are retained locally; no cleanup or history rewrite.

## Limits and remaining gates

- This is an **access-restricted plaintext local drill**, not an encrypted,
  scheduled or off-site backup. Encryption/key recovery, retention, monitoring
  and independent-machine recovery remain mandatory operational work.
- No original services were stopped or write pause enforced. The before/after
  database/file fingerprints were stable during this observed capture, but this
  does not establish a general online database/filesystem snapshot guarantee.
- No private files existed to recover. Actual private milestone restoration,
  download authorization and missing-reference audit remain unverified.
- No real-user credential changes or sign-in, browser workflow, TLS/proxy,
  Gunicorn deployment or independent-server restoration performed.
- No full test-suite rerun: application/test code unchanged. Last full run for
  the published initialization release was 352 passed; this drill is separate.

See BACKUP_RESTORE_RUNBOOK.md for procedure and the remaining production gates.
