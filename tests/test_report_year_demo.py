"""A report demo must use real calculations without touching another database."""
import csv
import io
from datetime import datetime
from pathlib import Path

import pytest
from flask import template_rendered
from sqlalchemy import inspect
from werkzeug.datastructures import MultiDict

from app import report_demo as demo
from app.models import db
from app.models.annual_plan import AnnualTarget
from app.models.event import Attendance, Event, Registration
from app.models.user import User, SystemSetting
from app.services.workspace_reports import workspace_report


@pytest.fixture(scope='module')
def report_app(tmp_path_factory):
    patch = pytest.MonkeyPatch()
    root = tmp_path_factory.mktemp('report-year')
    patch.setattr(demo, 'DEMO_ROOT', root)
    app = demo.create_demo_app(root / 'year.sqlite')
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        demo.seed_year(2025, 'Test-Only-Password1!')
    yield app
    with app.app_context():
        db.session.remove(); db.engine.dispose()
    patch.undo()


def login(app, role):
    client = app.test_client()
    response = client.post('/auth/login', data={'identifier':demo.LOGIN_EMAILS[role], 'password':'Test-Only-Password1!'})
    assert response.status_code == 302
    return client


def test_target_guards_and_no_implicit_startup_seed(report_app):
    with pytest.raises(ValueError, match='inside'):
        demo.create_demo_app(Path('instance/operational.sqlite'))
    with pytest.raises(ValueError, match='completed'):
        demo.create_demo_app(demo.DEMO_ROOT / 'future.sqlite', 9999)
    with pytest.raises(ValueError, match='matching'):
        demo.create_demo_app(demo.DEMO_ROOT / 'year.sqlite', 2024)
    foreign = demo.DEMO_ROOT / 'foreign.sqlite'
    import sqlite3
    with sqlite3.connect(foreign) as connection:
        connection.execute('CREATE TABLE untouched (value TEXT)')
    before = foreign.read_bytes()
    with pytest.raises(ValueError, match='not a report'):
        demo.create_demo_app(foreign)
    assert foreign.read_bytes() == before


def test_rerun_coverage_and_attendance_integrity(report_app):
    with report_app.app_context():
        before = demo.manifest(2025)
        assert demo.seed_year(2025, 'ignored-on-rerun') == before
        assert before['activities'] == 216 and before['volunteers'] == 450 and before['external_people'] == 180
        assert len(before['monthly']) == 12 and all(before['monthly'].values())
        assert len(before['campuses']) == 9 and len({c['count'] for c in before['campuses']}) > 3
        assert sum(before['monthly'].values()) == before['report_totals']['conducted']
        assert before['attendance_states']['present'] == before['report_totals']['attendees']
        assert before['registration_states']['completed'] == before['attendance_states']['present']
        assert Registration.query.outerjoin(Attendance).filter(Attendance.id.is_(None), Registration.status=='confirmed').count() > 0
        assert not Registration.query.join(Attendance).filter(Registration.status=='cancelled').count()
        assert all(r.registered_at < r.event.date and r.participant.created_at <= r.registered_at for r in Registration.query.all())
        assert all(e.date.year == 2025 and e.date < e.end_date for e in Event.query.all())
        assert all(c['total'] == 4 for c in before['annual_campuses'])
        assert any(c['achieved'] for c in before['annual_campuses'])
        assert any(c['pending'] for c in before['annual_campuses'])
        assert before['university_targets']['total'] == 4
        assert AnnualTarget.query.count() == 60


@pytest.mark.parametrize('path', ['/demo', '/workspace/overview', '/workspace/reports/results',
    '/workspace/reports/results?view=activities', '/workspace/reports/results?view=participation',
    '/workspace/reports/aop', '/annual-goals', '/workspace/reports/historical',
    '/workspace/reports/people', '/workspace/recognition'])
def test_director_destinations_and_notice(report_app, path):
    client = login(report_app, 'director')
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200, response.text[:500]
    assert 'Synthetic Demonstration Data' in response.text
    if 'recognition' in path:
        assert 'award_year=2025' in response.request.url


def test_scope_periods_and_exports(report_app):
    client = login(report_app, 'director')
    with report_app.app_context():
        director = User.query.filter_by(role='director').one()
        manifest = demo.manifest(2025)
        data = workspace_report(Event.query, MultiDict({'year':'2025','period':'annual'}), director, datetime.now())
        expected = len(data['rows'])
        values = {r['event'].title: r for r in data['rows']}
    response = client.get('/workspace/reports/export/csv?year=2025&period=annual')
    assert response.status_code == 200 and 'synthetic-' in response.headers['Content-Disposition']
    rows = list(csv.reader(io.StringIO(response.data.decode('utf-8-sig'))))
    assert 'Synthetic Demonstration Data' in rows[0][0]
    headers = rows[1]
    assert len(rows[2:]) == expected
    assert sum(int(row[headers.index('Recorded attendees')]) for row in rows[2:]) == manifest['report_totals']['attendees']
    for row in rows[2:]:
        # Duplicate titles represent separate dated activities, not a unique key.
        assert row[0] in values
    for fmt in ('xlsx', 'pdf'):
        result = client.get(f'/workspace/reports/export/{fmt}?year=2025&period=annual')
        assert result.status_code == 200
        if fmt == 'xlsx':
            from openpyxl import load_workbook
            book = load_workbook(io.BytesIO(result.data))
            assert 'Synthetic Demonstration Data' in book['Demo Notice']['A1'].value
            assert book['Activities'].max_row == expected + 1
            assert len(book['Campus accomplishments']._charts) == 1
            assert len(book['Delivery trend']._charts) == 1
            assert sum(row[1] for row in book['Delivery trend'].iter_rows(min_row=2, values_only=True)) == manifest['report_totals']['conducted']
        else:
            from pypdf import PdfReader
            pages = PdfReader(io.BytesIO(result.data)).pages
            assert all('Synthetic Demonstration Data' in page.extract_text() for page in pages)
    assert client.get('/workspace/reports/export/csv?year=2025&sample=1').status_code == 400
    for scope in ('period=quarterly&segment=1', 'period=semiannual&segment=2',
                  'period=custom&start_date=2025-03-01&end_date=2025-04-30',
                  'period=all', 'category=Environment', 'campus=1&campus=2',
                  'campus=1&campus_mode=exclude', 'q=%25', 'q=_', 'view=activities&page=2'):
        assert client.get('/workspace/reports/results?year=2025&'+scope).status_code == 200


def test_coordinator_volunteer_and_private_documents(report_app):
    coordinator = login(report_app, 'coordinator')
    contexts = []
    def capture(sender, template, context, **extra):
        contexts.append(context)
    with template_rendered.connected_to(capture, report_app):
        assert coordinator.get('/workspace/reports/results?year=2025&campus_id=2&campus=2').status_code == 200
    assert all(row['event'].campus_id == 1 for row in contexts[-1]['rows'])
    assert contexts[-1]['deltas'] == {}
    with report_app.app_context():
        own = Event.query.filter(Event.campus_id==1, Event.proposal_document.isnot(None)).first().id
        other = Event.query.filter(Event.campus_id==2, Event.proposal_document.isnot(None)).first().id
    assert coordinator.get(f'/workspace/activities/{other}/proposal').status_code == 404
    assert coordinator.get(f'/workspace/activities/{own}/proposal').status_code == 200
    director = login(report_app, 'director')
    assert director.get(f'/workspace/activities/{other}/proposal').status_code == 200
    volunteer = login(report_app, 'volunteer')
    assert volunteer.get('/workspace/reports/results?year=2025').status_code == 403
    assert volunteer.get('/demo').status_code == 200
    assert 'Activity Summary' not in volunteer.get('/demo').text


@pytest.mark.parametrize('path', [
    '/workspace/reports/export/csv?year=2025&report=aop',
    '/workspace/reports/export/xlsx?year=2025&report=aop',
    '/workspace/reports/export/pdf?year=2025&report=aop',
    '/annual-goals?year=2025&export=csv',
    '/annual-goals?year=2025&export=pdf',
    '/workspace/reports/historical/export/csv?year=2025',
    '/workspace/reports/historical/export/xlsx?year=2025',
    '/workspace/reports/historical/export/pdf?year=2025',
    '/reports/university.csv?start_date=2025-01-01&end_date=2025-12-31'])
def test_other_report_downloads_are_labelled(report_app, path):
    client = login(report_app, 'director')
    response = client.get(path, follow_redirects=True)
    assert response.status_code == 200
    assert 'synthetic-' in response.headers['Content-Disposition']
    if '.csv' in path or '/csv' in path or 'export=csv' in path:
        assert response.data.decode('utf-8-sig').startswith('Synthetic Demonstration Data')
    elif 'xlsx' in path:
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(response.data))
        assert 'Synthetic Demonstration Data' in book['Demo Notice']['A1'].value
    else:
        from pypdf import PdfReader
        assert all('Synthetic Demonstration Data' in p.extract_text() for p in PdfReader(io.BytesIO(response.data)).pages)


def test_transaction_rolls_back(report_app, monkeypatch):
    app = demo.create_demo_app(demo.DEMO_ROOT / 'rollback.sqlite')
    def fail(year, password):
        db.session.add(SystemSetting(key='must-not-survive', value='x'))
        db.session.flush()
        raise RuntimeError('injected seed failure')
    monkeypatch.setattr(demo, '_populate', fail)
    with app.app_context():
        with pytest.raises(RuntimeError, match='injected'):
            demo.seed_year(2025, 'irrelevant')
        assert SystemSetting.query.count() == 0
        assert User.query.count() == 0
        db.engine.dispose()
