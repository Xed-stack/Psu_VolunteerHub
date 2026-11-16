"""Explicit catalogue upgrade; never invoked by application startup."""
from sqlalchemy import inspect, text
from app.models.user import interest_skills, CatalogueRevision
from config import Config
from app.catalogue import VERSION


def migrate_catalogue(engine, database, dry_run=False):
    if not database or database != engine.url.database:
        raise ValueError('Provide the exact target database name.')
    if engine.dialect.name not in ('sqlite', 'mysql', 'mariadb'):
        raise ValueError('Only SQLite and MySQL/MariaDB are supported.')
    inspector = inspect(engine)
    if not {'skills','interests','activity_categories'} <= set(inspector.get_table_names()):
        raise ValueError('Existing skill, interest and activity category tables are required.')
    statements = []
    for table in ('skills','activity_categories'):
        if 'is_active' not in {column['name'] for column in inspector.get_columns(table)}:
            statements.append(f'ALTER TABLE {table} ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1')
    plan = [*statements, 'CREATE interest_skills IF MISSING', 'CREATE catalogue_revisions IF MISSING', 'BACKFILL configured interest–skill links ONCE']
    if dry_run:
        return plan
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        interest_skills.create(connection, checkfirst=True)
        CatalogueRevision.__table__.create(connection, checkfirst=True)
        if not connection.execute(text("SELECT id FROM activity_categories WHERE name='General'")).first():
            connection.execute(text("INSERT INTO activity_categories (name,is_active) VALUES ('General',1)"))
        if not connection.execute(text('SELECT version FROM catalogue_revisions WHERE version=:v'), {'v':VERSION}).first():
            for name, skills in Config.INTEREST_SKILL_MAP.items():
                interest = connection.execute(text('SELECT id FROM interests WHERE name=:name'),{'name':name}).scalar()
                if interest is None:
                    continue
                for skill in skills:
                    skill_id = connection.execute(text('SELECT id FROM skills WHERE name=:name'),{'name':skill}).scalar()
                    params = {'i':interest,'s':skill_id}
                    if skill_id is not None and not connection.execute(text('SELECT 1 FROM interest_skills WHERE interest_id=:i AND skill_id=:s'),params).first():
                        connection.execute(text('INSERT INTO interest_skills (interest_id,skill_id) VALUES (:i,:s)'),params)
            connection.execute(text('INSERT INTO catalogue_revisions (version) VALUES (:v)'),{'v':VERSION})
    return plan
