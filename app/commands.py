"""Flask CLI commands for importing institutional historical data."""
import csv
from pathlib import Path

import click
from flask.cli import with_appcontext
from datetime import datetime, timedelta

from app.models import db
from app.models.event import (Campus, HistoricalActivity, Event, Registration,
                              Attendance)
from app.models.user import User


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


@click.command('seed-demo-analytics')
@with_appcontext
def seed_demo_analytics():
    """Create idempotent demo registrations and attendance for presentations."""
    prefix = '[Demo Analytics]'
    volunteers = User.query.filter_by(role='volunteer').order_by(User.id).all()
    campuses = Campus.query.order_by(Campus.id).limit(4).all()
    if not volunteers or not campuses:
        raise click.ClickException('Seed campuses and volunteer users first.')

    now = datetime.now()
    definitions = [
        ('Community Food Drive', 'Community', 1, 7, 4),
        ('Green Campus Initiative', 'Environment', 2, 6, 5),
        ('Youth Coding Mentor', 'Technology', 3, 5, 3),
        ('Rural Literacy Program', 'Education', 4, 4, 2),
        ('Coastal Cleanup Drive', 'Environment', 5, 8, 7),
        ('Community Wellness Fair', 'Health', 6, 3, 2),
    ]
    extra_categories = [
        ('Tree Growing Day', 'Environment'),
        ('Reading Buddies', 'Education'),
        ('Digital Skills Clinic', 'Technology'),
        ('Barangay Health Caravan', 'Health'),
        ('Nutrition Pack Distribution', 'Community'),
        ('Riverbank Restoration', 'Environment'),
        ('Math Mentoring Day', 'Education'),
        ('Computer Basics Workshop', 'Technology'),
        ('Wellness Screening', 'Health'),
        ('Relief Goods Packing', 'Community'),
        ('Coastal Habitat Survey', 'Environment'),
        ('Youth Tutoring Circle', 'Education'),
        ('Online Safety Seminar', 'Technology'),
        ('First Aid Orientation', 'Health'),
        ('Community Garden Build', 'Community'),
        ('Mangrove Stewardship', 'Environment'),
        ('Library Learning Lab', 'Education'),
        ('Device Repair Clinic', 'Technology'),
    ]
    definitions.extend(
        (title, category, index + 1, 10 + index * 8,
         3 + (index * 3) % 10)
        for index, (title, category) in enumerate(extra_categories)
    )
    created_events = created_registrations = created_attendance = 0
    for title, category, campus_offset, days_ago, registration_count in definitions:
        campus = campuses[(campus_offset - 1) % len(campuses)]
        event = Event.query.filter_by(title=f'{prefix} {title}').first()
        if event is None:
            event = Event(
                title=f'{prefix} {title}',
                description='Presentation data for PSU Volunteer Hub analytics.',
                date=now - timedelta(days=days_ago),
                category=category,
                required_skills='Communication, Teamwork',
                slots=max(registration_count, 10),
                campus_id=campus.id)
            db.session.add(event)
            db.session.flush()
            created_events += 1
        for index in range(registration_count):
            volunteer = volunteers[index % len(volunteers)]
            registration = Registration.query.filter_by(
                user_id=volunteer.id, event_id=event.id).first()
            if registration is None:
                registration = Registration(
                    user_id=volunteer.id, event_id=event.id, status='confirmed')
                db.session.add(registration)
                db.session.flush()
                created_registrations += 1
            if index < max(1, registration_count - 1):
                attendance = Attendance.query.filter_by(
                    registration_id=registration.id).first()
                if attendance is None:
                    db.session.add(Attendance(
                        registration_id=registration.id,
                        user_id=volunteer.id,
                        event_id=event.id,
                        status='present'))
                    registration.status = 'completed'
                    created_attendance += 1
    db.session.commit()
    click.echo(
        f'{created_events} events, {created_registrations} registrations, '
        f'{created_attendance} attendance records created.')


def register_commands(app):
    app.cli.add_command(import_historical_activities)
    app.cli.add_command(seed_demo_analytics)
