from sqlalchemy import create_engine, inspect, text
import pytest
from app.workspace_migration import migrate_workspace


def test_workspace_migration_preserves_rows_and_is_rerunnable(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    engine = create_engine('sqlite:///' + str(path))
    with engine.begin() as connection:
        for statement in [
            'CREATE TABLE campuses (id INTEGER PRIMARY KEY)',
            'CREATE TABLE users (id INTEGER PRIMARY KEY, role VARCHAR(20))',
            'CREATE TABLE events (id INTEGER PRIMARY KEY, title VARCHAR(200))',
            'CREATE TABLE external_participants (id INTEGER PRIMARY KEY)',
            "INSERT INTO users VALUES (1, 'admin')", "INSERT INTO events VALUES (1, 'Preserved activity')"]:
            connection.execute(text(statement))
    plan = migrate_workspace(engine, str(path), dry_run=True)
    assert any('CREATE TABLE form_drafts' in step for step in plan)
    assert 'form_drafts' not in inspect(engine).get_table_names()
    with pytest.raises(ValueError):
        migrate_workspace(engine, 'wrong-target')
    migrate_workspace(engine, str(path))
    migrate_workspace(engine, str(path))
    with engine.connect() as connection:
        assert connection.execute(text('SELECT role FROM users')).scalar() == 'director'
        assert connection.execute(text('SELECT title FROM events')).scalar() == 'Preserved activity'
        assert connection.execute(text('SELECT lifecycle_status FROM events')).scalar() == 'approved'
        assert connection.execute(text('SELECT proposal_document FROM events')).scalar() is None
    engine.dispose()
