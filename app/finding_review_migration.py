"""Explicit, additive review storage; never run on ordinary startup."""
from sqlalchemy import inspect,MetaData,Table,Column
from app.models.finding_review import FindingReview, FindingReviewEvent


def migrate_finding_reviews(engine, database, dry_run=False):
    if not database or database != engine.url.database:
        raise ValueError('The exact configured database name is required.')
    if engine.dialect.name not in ('sqlite', 'mysql', 'mariadb'):
        raise ValueError('Only SQLite, MySQL and MariaDB are supported.')
    tables = set(inspect(engine).get_table_names())
    if not {'users', 'campuses', 'events'} <= tables:
        raise ValueError('The existing user, campus and activity schema is required.')
    for model in (FindingReview,FindingReviewEvent):
        if model.__tablename__ in tables and not set(model.__table__.columns.keys()) <= {
            column['name'] for column in inspect(engine).get_columns(model.__tablename__)}:
            raise ValueError('Existing review storage is incomplete. Inspect it before migrating; no data was changed.')
    if 'finding_reviews' in tables and not any(c['column_names']==['finding_key'] for c in inspect(engine).get_unique_constraints('finding_reviews')):
        raise ValueError('Review storage requires a unique finding key. Inspect it before migrating.')
    missing = [model.__table__ for model in (FindingReview, FindingReviewEvent) if model.__tablename__ not in tables]
    if not dry_run:
        metadata=MetaData()
        inspector=inspect(engine)
        for parent in ('users','campuses','events'):
            id_type=next(column['type'] for column in inspector.get_columns(parent) if column['name']=='id')
            Table(parent,metadata,Column('id',id_type,primary_key=True))
        copies={model.__tablename__:model.__table__.to_metadata(metadata) for model in (FindingReview,FindingReviewEvent)}
        for table in copies.values():
            for name,parent in [('campus_id','campuses'),('event_id','events'),('actor_id','users')]:
                if name in table.c:table.c[name].type=metadata.tables[parent].c.id.type
        with engine.begin() as connection:
            for table in missing:
                copies[table.name].create(connection, checkfirst=True)
    return ['CREATE TABLE '+table.name for table in missing]
