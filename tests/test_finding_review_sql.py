"""Opt-in integration only on a separately started disposable loopback server."""
import os
import subprocess
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import create_engine,inspect
from app.models.finding_review import FindingReview,FindingReviewEvent
from app.finding_review_migration import migrate_finding_reviews

PORT=os.environ.get('PSU_REVIEW_SQL_QA_PORT')
pytestmark=pytest.mark.skipif(not PORT,reason='Requires a disposable review SQL test server.')


@pytest.fixture
def database():
    assert int(PORT)>1024 and int(PORT)!=3306
    name='psu_review_qa_'+uuid4().hex[:12]
    server=create_engine(f'mysql+pymysql://root:@127.0.0.1:{int(PORT)}/mysql')
    with server.begin() as c:c.exec_driver_sql(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4')
    engine=create_engine(f'mysql+pymysql://root:@127.0.0.1:{int(PORT)}/{name}')
    try:yield engine
    finally:
        engine.dispose()
        assert name.startswith('psu_review_qa_')
        with server.begin() as c:c.exec_driver_sql(f'DROP DATABASE `{name}`')
        server.dispose()


def parents(engine,unsigned=False):
    kind='BIGINT UNSIGNED' if unsigned else 'INT'
    with engine.begin() as c:
        for table in ('users','campuses','events'):
            c.exec_driver_sql(f'CREATE TABLE {table} (id {kind} PRIMARY KEY, label VARCHAR(100)) ENGINE=InnoDB')
            c.exec_driver_sql(f"INSERT INTO {table} VALUES (1,'Preserved source')")


def sql(engine):
    return subprocess.run(['C:/xampp/mysql/bin/mysql.exe','--no-defaults','--host=127.0.0.1',f'--port={PORT}',
        '--user=root','--default-character-set=utf8mb4',f'--database={engine.url.database}'],
        input=Path('migrations/20261122_finding_reviews.sql').read_text(encoding='utf-8'),text=True,capture_output=True,timeout=40)


@pytest.mark.parametrize('unsigned',[False,True])
@pytest.mark.parametrize('method',['sql','python'])
def test_migrations_match_models_and_preserve_data(database,unsigned,method):
    parents(database,unsigned)
    if method=='sql':
        result=sql(database);assert result.returncode==0,result.stderr
    else:
        assert len(migrate_finding_reviews(database,database.url.database,True))==2
        assert 'finding_reviews' not in inspect(database).get_table_names()
        assert len(migrate_finding_reviews(database,database.url.database))==2
    for model in (FindingReview,FindingReviewEvent):
        assert {c['name'] for c in inspect(database).get_columns(model.__tablename__)}==set(model.__table__.columns.keys())
    with database.begin() as c:
        c.execute(FindingReview.__table__.insert().values(finding_key='a'*64,campus_id=1,event_id=1,year=2026,
            finding_type='pending_attendance',fingerprint='b'*64,snapshot={'title':'Retained'},scope={},assessment='Authored assessment'))
    if method=='sql':assert sql(database).returncode==0
    else:assert migrate_finding_reviews(database,database.url.database)==[]
    with database.begin() as c:
        assert c.exec_driver_sql('SELECT assessment FROM finding_reviews').scalar()=='Authored assessment'
        for table in ('users','campuses','events'):assert c.exec_driver_sql(f'SELECT label FROM {table}').scalar()=='Preserved source'
        assert c.exec_driver_sql('UPDATE finding_reviews SET version=2 WHERE version=1').rowcount==1
        assert c.exec_driver_sql('UPDATE finding_reviews SET version=3 WHERE version=1').rowcount==0


def test_missing_parents_refused(database):
    result=sql(database);assert result.returncode!=0
    assert 'finding_reviews' not in inspect(database).get_table_names()
    with pytest.raises(ValueError):migrate_finding_reviews(database,database.url.database)


def test_incomplete_storage_refused_without_overwriting(database):
    parents(database)
    with database.begin() as c:c.exec_driver_sql('CREATE TABLE finding_reviews (id INT PRIMARY KEY, note TEXT)')
    assert sql(database).returncode!=0
    with pytest.raises(ValueError):migrate_finding_reviews(database,database.url.database)


def test_missing_identity_constraint_refused(database):
    parents(database);assert sql(database).returncode==0
    name=next(c['name'] for c in inspect(database).get_unique_constraints('finding_reviews') if c['column_names']==['finding_key'])
    with database.begin() as c:c.exec_driver_sql(f'ALTER TABLE finding_reviews DROP INDEX `{name}`')
    assert sql(database).returncode!=0
    with pytest.raises(ValueError):migrate_finding_reviews(database,database.url.database)
