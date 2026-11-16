"""Seed or serve the separate local report demonstration; never copies user data."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.report_demo import DEMO_ROOT, LOGIN_EMAILS, create_demo_app, seed_year, validate_target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--year', type=int, default=2025)
    parser.add_argument('--database', type=Path, default=DEMO_ROOT / 'annual-reports-2025.sqlite')
    parser.add_argument('--dry-run', action='store_true', help='Validate the target without creating files or records.')
    parser.add_argument('--serve', action='store_true', help='Serve the seeded demo on loopback only.')
    parser.add_argument('--port', type=int, default=5001)
    args = parser.parse_args()
    path = validate_target(args.database, args.year)
    if args.dry_run:
        print(json.dumps(dict(database=str(path), year=args.year, dry_run=True,
            activities=216, volunteers=450, external_people=180, existing_database=path.exists()), indent=2))
        return
    credentials = path.parent / (path.stem + '-credentials.json')
    existed = path.exists()
    app = create_demo_app(path, args.year)
    if path.exists() and not credentials.exists():
        parser.error('Existing demo credentials are unavailable; use a new demo filename.')
    password = json.loads(credentials.read_text())['password'] if credentials.exists() else 'password'
    with app.app_context():
        try:
            result = seed_year(args.year, password)
        except Exception:
            if not existed:
                from app.models import db
                db.session.remove()
                db.engine.dispose()
                path.unlink(missing_ok=True)
            raise
    credentials.write_text(json.dumps(dict(password=password,
        accounts=list(LOGIN_EMAILS.values())), indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    print(f'Local-only credentials: {credentials}')
    if args.serve:
        print(f'Report demo: http://127.0.0.1:{args.port}/demo', flush=True)
        app.run(host='127.0.0.1', port=args.port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
