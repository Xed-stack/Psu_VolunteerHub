"""Explicit, resumable workspace schema upgrade; never called at startup."""
from sqlalchemy import inspect, text
from app.models.workspace import FormDraft, PartnerAgency, PartnerAgreement, ExternalGroup


def migrate_workspace(engine, database, dry_run=False):
    if not database or database != engine.url.database:
        raise ValueError('The exact configured database name is required; nothing changed.')
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if not {'events', 'users', 'campuses', 'external_participants'} <= tables:
        raise ValueError('The existing application schema is required.')
    mysql = engine.dialect.name in ('mysql', 'mariadb')
    if not mysql and engine.dialect.name != 'sqlite':
        raise ValueError('Only MySQL, MariaDB, and SQLite are supported.')
    additions = {'events': {
        'lifecycle_status': "VARCHAR(16) NOT NULL DEFAULT 'approved'",
        'cancellation_reason': 'TEXT NULL', 'cancelled_at': 'DATETIME NULL',
        'proposal_document': 'JSON NULL', 'conducting_department': 'VARCHAR(150) NULL',
        'participant_type': 'VARCHAR(100) NULL', 'audience': "JSON NULL" if mysql else "JSON NOT NULL DEFAULT '{}'",
        'agreement_id': 'INTEGER NULL REFERENCES partner_agreements(id) ON DELETE RESTRICT'},
        'external_participants': {'group_id': 'INTEGER NULL REFERENCES external_groups(id) ON DELETE SET NULL'}}
    statements = []
    for table, columns in additions.items():
        present = {c['name'] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in present:
                if mysql:
                    ddl = ddl.split(' REFERENCES ', 1)[0]
                statements.append(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')
    models = (FormDraft, PartnerAgency, PartnerAgreement, ExternalGroup)
    missing = [model.__table__ for model in models if model.__tablename__ not in tables]
    plan = [*(f'CREATE TABLE {table.name}' for table in missing), *statements,
            "UPDATE events SET audience = '{}' WHERE audience IS NULL",
            "UPDATE users SET role = 'director' WHERE role = 'admin'"]
    constraints = []
    if mysql:
        audience_column = next((column for column in inspector.get_columns('events') if column['name'] == 'audience'), None)
        if audience_column is None or audience_column['nullable']:
            constraints.append('ALTER TABLE events MODIFY audience JSON NOT NULL')
        for table, column, target, name, ondelete in [
            ('events', 'agreement_id', 'partner_agreements', 'fk_event_agreement', 'RESTRICT'),
            ('external_participants', 'group_id', 'external_groups', 'fk_external_group', 'SET NULL')]:
            if not any(fk['constrained_columns'] == [column] for fk in inspector.get_foreign_keys(table)):
                constraints.append(f'ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column}) REFERENCES {target}(id) ON DELETE {ondelete}')
        role_type = next(c['type'] for c in inspector.get_columns('users') if c['name'] == 'role')
        if 'admin' in getattr(role_type, 'enums', []):
            constraints.append("ALTER TABLE users MODIFY role ENUM('volunteer','coordinator','director') DEFAULT 'volunteer'")
    plan.extend(constraints)
    if not dry_run:
        with engine.begin() as connection:
            for table in missing:
                table.create(connection, checkfirst=True)
            for statement in statements:
                connection.execute(text(statement))
            connection.execute(text("UPDATE events SET audience = '{}' WHERE audience IS NULL"))
            connection.execute(text("UPDATE users SET role = 'director' WHERE role = 'admin'"))
            for statement in constraints:
                connection.execute(text(statement))
    return plan
