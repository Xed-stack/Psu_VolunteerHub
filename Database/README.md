# Database artifacts

Full database exports are private local artifacts, not source code. The two
previously tracked SQL dumps are removed from source tracking in this revision;
local files are preserved and ignored by `Database/*.sql`. The user approved
publication of the removal. No history rewrite, restore, or live database
modification was performed by this cleanup.

Removing tracked files in this commit does not erase their contents from
previous commits, clones, forks or downloads. Review repository exposure and
affected-account security separately; do not treat this step as remediation of
all historical exposure.

## Safe setup

- Development/demo: follow README's isolated development setup. Existing code
  creates synthetic demo users/events locally. Those accounts are not production
  accounts and must never be deployed as privileged institutional accounts.
- Existing production database: use reviewed incremental scripts in `migrations/`
  after backup/staging validation. Do not blindly rerun migrations or import a
  private full dump as a schema update.
- Fresh production database: the explicit `init-production` command builds the
  current model schema plus reference data and one Admin only in an empty,
  exactly named target. See README for confirmation, password and failure-safety
  details. Actual disposable MariaDB provisioning passed; see PRODUCTION_INIT_QA.md.
  This is not hosted-deployment approval. Production
  startup itself still does not create schema or seed accounts; the development
  seed path is not a production bootstrap procedure.
- Backups/data transfers: keep outside Git with encryption and restricted access,
  include required uploads, and test restore. The Admin CSV export alone is not
  a complete recoverable system backup.

No schema-only export is supplied here: mechanically removing INSERT statements
from an old dump would not establish that its schema matches current models and
migrations. Any future fixture must be synthetic or explicitly sanitized and
reviewed before committing; never include real password hashes or personal data.
