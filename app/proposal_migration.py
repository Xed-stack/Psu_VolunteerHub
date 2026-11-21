"""Explicit additive proposal migration. No startup hook or data rewrite."""
from sqlalchemy import inspect
from app.models.workspace import ActivityProposal


def migrate_proposals(engine, database, dry_run=False):
    if not database or database != engine.url.database:
        raise ValueError('The exact configured database name is required.')
    if engine.dialect.name not in ('sqlite','mysql','mariadb'):
        raise ValueError('Only SQLite, MySQL, and MariaDB are supported.')
    tables=set(inspect(engine).get_table_names())
    if not {'events','partner_agencies'} <= tables:
        raise ValueError('The existing activity and agency schema is required.')
    if 'activity_proposals' in tables:
        return []
    if not dry_run:
        with engine.begin() as connection:
            ActivityProposal.__table__.create(connection,checkfirst=True)
    return ['CREATE TABLE activity_proposals (staff proposal records; existing records unchanged)']
