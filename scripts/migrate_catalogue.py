"""Explicit managed catalogue migration. Set DATABASE_URL; target must match exactly."""
import argparse
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine
from app.catalogue_migration import migrate_catalogue

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    engine = create_engine(os.environ['DATABASE_URL'])
    try:
        for action in migrate_catalogue(engine, args.database, args.dry_run):
            print(action)
    finally:
        engine.dispose()
