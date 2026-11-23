"""Read retained shared evidence for historical AOP; never create active targets."""
import json
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import inspect
from app.models import db
from app.models.event import Event
from app.aop_migration import archive


def shared_evidence(targets, year):
    keys = {(target.indicator.shared_key, target.campus_id) for target in targets if target.indicator.shared_key}
    if not keys or not inspect(db.engine).has_table(archive.name):
        return []
    records = {}
    for table, payload in db.session.execute(archive.select().with_only_columns(
            archive.c.source_table, archive.c.payload).where(archive.c.source_table.in_([
                'annual_plans', 'annual_indicators', 'annual_targets', 'annual_results', 'annual_activity_mappings']))):
        row = json.loads(payload)
        records.setdefault(table, {})[row['id']] = row
    plans = {identity: SimpleNamespace(**row) for identity, row in records.get('annual_plans', {}).items()
             if row['year'] == year and row['status'] == 'approved'}
    indicators = {identity: SimpleNamespace(**row, plan=plans[row['plan_id']])
                  for identity, row in records.get('annual_indicators', {}).items()
                  if row['plan_id'] in plans and row.get('shared_key')}
    result = []
    for identity, row in records.get('annual_targets', {}).items():
        indicator = indicators.get(row['indicator_id'])
        if not indicator or not row['is_active'] or (indicator.shared_key, row['campus_id']) not in keys:
            continue
        values = dict(row, target_value=Decimal(str(row['target_value'])))
        values['deadline'] = date.fromisoformat(row['deadline']) if row.get('deadline') else None
        results = []
        for record in records.get('annual_results', {}).values():
            if record['target_id'] != identity:
                continue
            record = dict(record)
            for key in ('coverage_start', 'coverage_end'):
                record[key] = date.fromisoformat(record[key]) if record.get(key) else None
            record['imported_at'] = datetime.fromisoformat(record['imported_at'])
            record['actual_value'] = Decimal(str(record['actual_value'])) if record.get('actual_value') is not None else None
            if isinstance(record.get('sex_counts'), str):
                record['sex_counts'] = json.loads(record['sex_counts'])
            results.append(SimpleNamespace(**record))
        result.append(SimpleNamespace(**values, indicator=indicator, results=results,
                                      archived=True, activity_mappings=[]))
    mappings = records.get('annual_activity_mappings', {}).values()
    event_ids = {row['event_id'] for row in mappings if any(target.id == row['target_id'] for target in result)}
    events = {event.id: event for event in Event.query.filter(Event.id.in_(event_ids)).all()} if event_ids else {}
    for target in result:
        target.activity_mappings = [SimpleNamespace(**row, event=events[row['event_id']]) for row in mappings
                                   if row['target_id'] == target.id and row['event_id'] in events]
    return result
