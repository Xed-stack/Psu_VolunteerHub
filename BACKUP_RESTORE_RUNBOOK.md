# Backup and restore runbook

Status: local recovery drill passed on 20 October 2026. Not a claim of complete
production disaster-recovery readiness. See BACKUP_RESTORE_QA.md for limits.

## What must be protected together

- Native MariaDB/MySQL logical dump: current schema, all application rows,
  password hashes, constraints, triggers, routines and scheduled events where used.
- `static/uploads/` and the actual configured `PRIVATE_UPLOAD_FOLDER`, preserving
  relative paths. Do not confuse private milestone storage with public assets.
- Application release commit and dependency versions, database/client versions,
  environment/proxy/service configuration, backup time and a checksum manifest.
- Secrets through an approved separate encrypted secret store or encrypted
  recovery package. Include a recovery plan for database/SMTP credentials and
  SECRET_KEY; never include plaintext secrets in Git or an unencrypted manifest.

Admin's CSV ZIP is a data export, not a full system recovery backup: it omits
password hashes, executable schema and uploads. Do not use it as the only backup.

## Before backup

1. Confirm exact source host/database, code version and upload roots. Use an
   appropriately scoped backup account, not a publicly accessible root account.
2. Arrange an approved maintenance/write-pause window for database changes and
   uploads, including background jobs. A DB transaction alone does not snapshot
   filesystem uploads. Do not silently stop users' services to obtain a backup.
3. Keep schema migrations/DDL paused. `--single-transaction` gives an appropriate
   consistent snapshot for transactional tables; mixed/nontransactional engines
   require a separately reviewed locking or physical-backup procedure.
4. Create a new restricted directory outside the repository and public web roots.
   Use a protected client option file or interactive credential entry, never
   passwords in command arguments, source, screenshots or logs.
5. Inventory views/triggers/routines/events and grants/DEFINER dependencies. A
   same-server renamed restore needs explicit review of schema-qualified objects.
   Prefer a separately isolated restoration server for a realistic production drill.

## Native database backup

Illustrative Linux/WSL shell command, not executed by this runbook. Replace all
placeholders only after checking targets and permissions. On the tested XAMPP
installation the matching clients are named `mysqldump.exe` and `mysql.exe`.

```sh
mariadb-dump --defaults-extra-file=/secure/client.cnf \
  --single-transaction --quick --skip-lock-tables \
  --skip-add-locks --skip-add-drop-table --hex-blob \
  --routines --events --triggers \
  --result-file=/secure/backup/database.sql SOURCE_DATABASE
```

Check exit code and inspect warnings privately. Do not use `--databases` or
`--all-databases` for this renamed-target procedure: a dump containing CREATE
DATABASE/USE or source-qualified statements can redirect writes to the original.
Do not edit sensitive dumps using broad string replacement as a substitute for
review. These sample flags do not make arbitrary SQL safe to execute.

Copy both upload trees while writes remain paused; record missing/empty roots
explicitly. Record SHA-256 checksums for SQL and every copied file, plus schema
and row counts. Keep database and files from the same recovery window. Release
the approved pause only after capture is complete.

Encrypt the recovery set using an organization-approved tool, securely retain
its key separately, and store an access-controlled off-machine copy. Verify
decryptability. Local ACLs or a plaintext ZIP are not encryption. No encrypted
off-site backup/key-recovery procedure has yet been verified for this project.

## Restore drill, never onto the original

1. Obtain approval for a new uniquely named disposable target on an isolated
   server where possible. Confirm it does not already exist; create an empty
   schema with the reviewed source charset/collation. Refuse overwrite/resume.
2. Verify/decrypt the backup and validate SQL/file checksums. Inspect the dump
   for database switches, source-qualified objects and server-global operations.
3. Confirm the restore account/host/database again. Restore only into that empty
   target using the matching native client. POSIX-shell example:

   ```sh
   mariadb --defaults-extra-file=/secure/restore-client.cnf \
     --database=NEW_RESTORE_DATABASE < /secure/backup/database.sql
   ```

   Do not paste POSIX `<` redirection into Windows PowerShell. Use the native
   client's supported file-input workflow with an explicitly validated target.
   If restore fails, retain the disposable target for investigation; never retry
   into the original or automatically drop a database.

4. Restore uploads to new private/public test directories, not original roots.
   Point the restored app at the new DB and upload paths; disable outbound email,
   scheduled jobs and other real external effects. Preserve authorization checks.
5. Compare every table's schema, row counts and row fingerprints, not totals
   alone. Compare every file's relative path and checksum. Verify file references
   and permissions; report missing source files rather than inventing them.
6. Use the matching code release and production settings. Check login, core
   queries/reports and role-scoped private downloads. Test user credentials only
   with approved test accounts; do not reset a real user's password for a drill.
7. Measure recovery time, document manual steps and discrepancies, and verify
   source DB/files stayed unchanged. Retain or clean up only explicitly named
   disposable artifacts with approval. Never publish the restored personal data.

Do not run `init-production` or development auto-seeds on a restored database.
Do not blindly reapply migrations already represented in the backup. Handle any
release migration separately on the restored staging copy first.

## Operational release gates

PSU must assign a backup owner, schedule/retention, access policy, off-site
location, recovery-key custodian and accepted recovery point/time objectives.
Test scheduled backup failure alerts, off-site decryption, private files and an
independent-machine restore before treating this as production-ready recovery.

Reference: [MariaDB native dump documentation](https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump).
