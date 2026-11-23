"""Explicit AOP upgrade and transactional ASP retirement, never run on startup."""
import json

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, inspect, text


archive = Table('retired_annual_archive', MetaData(),
    Column('source_table', String(64), primary_key=True),
    Column('source_id', Integer, primary_key=True),
    Column('payload', Text, nullable=False))


def asp_records(connection):
    """Read raw rows so the runtime AOP-only enum never decodes retired values."""
    tables = set(inspect(connection).get_table_names())
    records = {}
    def collect(table, clause):
        records[table] = [dict(row) for row in connection.execute(text(
            f'SELECT * FROM {table} WHERE {clause}')).mappings()]
    collect('annual_plans', "plan_type = 'ASP'")
    ids = lambda table: ','.join(str(row['id']) for row in records.get(table, [])) or 'NULL'
    collect('annual_indicators', f"plan_id IN ({ids('annual_plans')})")
    collect('annual_targets', f"indicator_id IN ({ids('annual_indicators')})")
    collect('annual_results', f"target_id IN ({ids('annual_targets')})")
    if 'annual_activity_mappings' in tables:
        collect('annual_activity_mappings', f"target_id IN ({ids('annual_targets')})")
    if 'annual_goal_proposals' in tables:
        records['annual_goal_proposals'] = []
        retired_ids = {row['id'] for row in records['annual_targets']}
        for row in connection.execute(text('SELECT * FROM annual_goal_proposals')).mappings():
            payload = row['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                raise ValueError('Malformed historical proposal payload; resolve it before retirement.')
            refs = {row['published_target_id'], row['replaces_target_id']} - {None}
            is_asp = payload.get('plan_type') == 'ASP'
            if (refs & retired_ids and (refs-retired_ids or not is_asp)) or (is_asp and refs-retired_ids):
                raise ValueError('Ambiguous cross-plan proposal references; resolve them before retirement.')
            if is_asp or refs & retired_ids:
                records['annual_goal_proposals'].append(dict(row))
    # Refuse unknown inbound dependencies instead of cascading into unrelated records.
    inspector = inspect(connection)
    for table in tables:
        for fk in inspector.get_foreign_keys(table):
            parent = fk['referred_table']
            if parent not in records or not records[parent]:
                continue
            if len(fk['constrained_columns']) != 1 or fk['referred_columns'] != ['id']:
                raise ValueError('Unsupported annual-plan reference; review the schema before retirement.')
            quote = connection.dialect.identifier_preparer.quote
            column = quote(fk['constrained_columns'][0])
            linked = connection.execute(text(f'SELECT id FROM {quote(table)} WHERE {column} IN ({ids(parent)})')).scalars().all()
            if set(linked) - {row['id'] for row in records.get(table, [])}:
                raise ValueError(f'{table} references retired records outside the archive set; nothing retired.')
    return records


def retire_asp(connection, records):
    for table, rows in records.items():
        for row in rows:
            payload = json.dumps(row, default=str, sort_keys=True, ensure_ascii=False)
            existing = connection.execute(archive.select().where(
                archive.c.source_table == table, archive.c.source_id == row['id'])).mappings().first()
            if existing and existing['payload'] != payload:
                raise ValueError('Archive identity conflict; nothing retired.')
            if not existing:
                connection.execute(archive.insert().values(source_table=table, source_id=row['id'], payload=payload))
    for table in ('annual_goal_proposals', 'annual_activity_mappings', 'annual_results',
                  'annual_targets', 'annual_indicators', 'annual_plans'):
        ids = ','.join(str(row['id']) for row in records.get(table, []))
        if ids:
            connection.execute(text(f'DELETE FROM {table} WHERE id IN ({ids})'))


def migrate_aop(engine, database, dry_run=True):
    """Require an exact target name; dry-run does not execute DDL or archive writes."""
    if engine.dialect.name not in ('mysql', 'mariadb', 'sqlite'):
        raise ValueError('Supported targets are MySQL/MariaDB and disposable SQLite test databases.')
    if not database or database != engine.url.database:
        raise ValueError('Database name must exactly match the configured target.')
    inspector = inspect(engine)
    required = {'annual_plans', 'annual_indicators', 'annual_targets', 'annual_results',
                'annual_goal_proposals', 'annual_activity_mappings'}
    if not required <= set(inspector.get_table_names()):
        raise ValueError('Apply the existing annual-goal schema first.')
    additions = {
        'annual_targets': {'workflow_kind': "VARCHAR(24) NOT NULL DEFAULT 'legacy'",
            'director_target_id': 'INTEGER NULL REFERENCES annual_targets(id)',
            'start_date': 'DATE NULL', 'end_date': 'DATE NULL', 'version': 'INTEGER NOT NULL DEFAULT 1'},
        'annual_goal_proposals': {'workflow_kind': "VARCHAR(24) NOT NULL DEFAULT 'legacy'",
            'director_target_id': 'INTEGER NULL REFERENCES annual_targets(id)', 'version': 'INTEGER NOT NULL DEFAULT 1'}}
    statements = []
    for table, columns in additions.items():
        present = {column['name'] for column in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in present:
                if engine.dialect.name in ('mysql', 'mariadb'):
                    ddl = ddl.replace(' REFERENCES annual_targets(id)', '')
                statements.append(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')
        names = {item['name'] for item in inspector.get_unique_constraints(table)} | {
            item['name'] for item in inspector.get_indexes(table)}
        index = 'uq_aop_campus_commitment' if table == 'annual_targets' else 'uq_aop_campus_draft'
        if index not in names:
            statements.append(f'CREATE UNIQUE INDEX {index} ON {table} (director_target_id, campus_id)')
        if engine.dialect.name in ('mysql', 'mariadb') and not any(
                fk['constrained_columns'] == ['director_target_id'] for fk in inspector.get_foreign_keys(table)):
            statements.append(f'ALTER TABLE {table} ADD CONSTRAINT fk_{table}_director_goal '
                              'FOREIGN KEY (director_target_id) REFERENCES annual_targets(id) ON DELETE RESTRICT')
    with engine.connect() as connection:
        records = asp_records(connection)
    report = dict(schema=statements, archive={table: len(rows) for table, rows in records.items()},
                  archive_table=archive.name, retired_plan_type='ASP', active_plan_types=['AOP'], dry_run=dry_run)
    if dry_run:
        return report
    # MySQL DDL commits independently; additions are rerunnable before transactional retirement.
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        archive.create(connection, checkfirst=True)
    with engine.begin() as connection:
        retire_asp(connection, asp_records(connection))
    if engine.dialect.name in ('mysql', 'mariadb'):
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE annual_plans MODIFY plan_type ENUM('AOP') NOT NULL"))
    return report
