"""Flask CLI commands for importing institutional historical data."""
import csv
from pathlib import Path

import click
from flask.cli import with_appcontext

from app.models import db
from app.models.event import Campus, HistoricalActivity


def _optional_int(value, field, line_number):
    value = (value or '').strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise click.ClickException(
            f'Invalid {field} on CSV line {line_number}: {value!r}') from exc


@click.command('import-historical-activities')
@click.argument('csv_path', type=click.Path(exists=True, dir_okay=False,
                                             path_type=Path))
@click.option('--dry-run', is_flag=True,
              help='Validate and report changes without committing them.')
@with_appcontext
def import_historical_activities(csv_path, dry_run):
    """Idempotently import aggregate historical activities from CSV."""
    required = {
        'source_key', 'source_document', 'source_page', 'source_row',
        'unit_name', 'title', 'activity_type', 'partners',
        'participant_categories', 'volunteer_count', 'year_conducted',
    }
    campuses = {c.name.casefold(): c for c in Campus.query.all()}
    aliases = {'sta. maria': 'santa maria'}
    created = updated = unchanged = 0

    with csv_path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise click.ClickException(
                f'Missing CSV columns: {", ".join(sorted(missing))}')

        for line_number, row in enumerate(reader, start=2):
            source_key = row['source_key'].strip()
            title = row['title'].strip()
            unit_name = row['unit_name'].strip()
            if not source_key or not title or not unit_name:
                raise click.ClickException(
                    f'CSV line {line_number} requires source_key, unit_name, and title')

            campus_key = unit_name.removesuffix(' Campus').strip().casefold()
            campus = campuses.get(aliases.get(campus_key, campus_key))
            values = {
                'source_document': row['source_document'].strip(),
                'source_page': _optional_int(row['source_page'], 'source_page', line_number),
                'source_row': _optional_int(row['source_row'], 'source_row', line_number),
                'unit_name': unit_name,
                'campus_id': campus.id if campus else None,
                'title': title,
                'activity_type': row['activity_type'].strip() or None,
                'partners': row['partners'].strip() or None,
                'participant_categories': row['participant_categories'].strip() or None,
                'volunteer_count': _optional_int(row['volunteer_count'], 'volunteer_count', line_number),
                'year_conducted': _optional_int(row['year_conducted'], 'year_conducted', line_number),
            }
            item = HistoricalActivity.query.filter_by(source_key=source_key).first()
            if item is None:
                db.session.add(HistoricalActivity(source_key=source_key, **values))
                created += 1
            elif any(getattr(item, key) != value for key, value in values.items()):
                for key, value in values.items():
                    setattr(item, key, value)
                updated += 1
            else:
                unchanged += 1

    if dry_run:
        db.session.rollback()
    else:
        db.session.commit()
    click.echo(
        f'{"Dry run: " if dry_run else ""}{created} created, '
        f'{updated} updated, {unchanged} unchanged.')


def register_commands(app):
    app.cli.add_command(import_historical_activities)
