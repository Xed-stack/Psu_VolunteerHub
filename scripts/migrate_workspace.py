"""Upgrade an existing database without running the application factory."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from config import config
from app.workspace_migration import migrate_workspace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True, help='Exact configured database name; confirm against your backup.')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    settings = config[os.environ.get('APP_ENV', 'development')]
    if not settings.SQLALCHEMY_DATABASE_URI:
        parser.error('A database URL must be configured.')
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    try:
        statements = migrate_workspace(engine, args.database, args.dry_run)
        for statement in statements:
            print(statement)
        print('Inspection only; nothing changed.' if args.dry_run else 'Workspace migration completed.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
