"""Opt-in integration: creates and removes only uniquely named local QA schemas."""
import os
import re
from datetime import datetime
from secrets import token_hex

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from app import create_app
from app.models import db
from app.models.event import Event
from config import DevelopmentConfig, ProductionConfig, TestingConfig


@pytest.mark.skipif(os.environ.get('RAILWAY_YEAR_MYSQL_TEST')!='1', reason='Opt-in local MySQL integration')
def test_mysql_empty_target_and_readonly_source(monkeypatch):
    server_url=make_url(os.environ.get('RAILWAY_YEAR_MYSQL_TEST_URL', DevelopmentConfig.SQLALCHEMY_DATABASE_URI)).set(database=None)
    assert server_url.host in ('localhost','127.0.0.1')
    assert server_url.drivername.startswith(('mysql','mariadb'))
    suffix=token_hex(6)
    names=[f'psu_seed_year_qa_{suffix}_{kind}' for kind in ('source','target')]
    assert all(re.fullmatch(r'psu_seed_year_qa_[0-9a-f]{12}_(source|target)',name) for name in names)
    server=create_engine(server_url, hide_parameters=True)
    apps=[]
    created=[]
    try:
        with server.connect() as conn:
            for name in names:
                conn.exec_driver_sql(f'CREATE DATABASE `{name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
                created.append(name)
        source_url=server_url.set(database=names[0])
        target_url=server_url.set(database=names[1])
        monkeypatch.setattr(TestingConfig,'SQLALCHEMY_DATABASE_URI',source_url.render_as_string(hide_password=False))
        source=create_app('testing')
        apps.append(source)
        with source.app_context():
            from app.railway_year_dataset import _fingerprint
            before=_fingerprint()
        monkeypatch.setattr(ProductionConfig,'SQLALCHEMY_DATABASE_URI',target_url.render_as_string(hide_password=False))
        monkeypatch.setattr(ProductionConfig,'SECRET_KEY',token_hex(32))
        monkeypatch.setattr(ProductionConfig,'MAIL_SUPPRESS_SEND',True)
        monkeypatch.setattr(ProductionConfig,'PRIVATE_UPLOAD_FOLDER',os.environ['RAILWAY_YEAR_MYSQL_UPLOADS'])
        target=create_app('production')
        apps.append(target)
        monkeypatch.setenv('RAILWAY_SERVICE_ID','isolated-local-year-qa')
        monkeypatch.setenv('RAILWAY_SEED_SERVICE_ID','isolated-local-year-qa')
        monkeypatch.setenv('RAILWAY_SEED_DATABASE_HOST',target_url.host)
        monkeypatch.setenv('RAILWAY_SEED_SOURCE_HOST',source_url.host)
        monkeypatch.setenv('RAILWAY_SEED_SOURCE_DATABASE_URL',source_url.render_as_string(hide_password=False))
        now=datetime(2026,11,24,10)
        monkeypatch.setattr('app.railway_year_dataset.local_now',lambda:now)
        monkeypatch.setattr('app.services.aop_goals.local_now',lambda:now)
        monkeypatch.setattr('app.services.activity_workflow.local_now',lambda:now)
        monkeypatch.setattr('app.services.finding_reviews.local_now',lambda:now)
        monkeypatch.setattr('app.annual_goals.local_now',lambda:now)
        runner=target.test_cli_runner()
        args=['seed-railway-year','--database',names[1]]
        result=runner.invoke(args=[*args,'--dry-run'])
        assert result.exit_code==0,result.output
        with target.app_context():
            assert inspect(db.engine).get_table_names()==[]
        result=runner.invoke(args=args,input=f'SEED 2026 {target_url.host}/{names[1]}\n')
        assert result.exit_code==0,result.output
        with target.app_context():
            assert Event.query.count()==90
        result=runner.invoke(args=[*args,'--dry-run'])
        assert result.exit_code==0,result.output
        with source.app_context():
            assert _fingerprint()==before
    finally:
        for app in apps:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        with server.connect() as conn:
            for name in created:
                assert re.fullmatch(r'psu_seed_year_qa_[0-9a-f]{12}_(source|target)',name)
                conn.exec_driver_sql(f'DROP DATABASE `{name}`')
        server.dispose()
