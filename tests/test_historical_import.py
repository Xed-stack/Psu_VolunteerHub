from pathlib import Path

import pytest

from app import create_app
from app.models.event import HistoricalActivity


SEED_CSV = Path(__file__).resolve().parents[1] / 'data' / \
    'historical_activities_2020_2025.csv'


@pytest.fixture
def app():
    return create_app('testing')


def test_historical_import_is_idempotent(app):
    runner = app.test_cli_runner()
    first = runner.invoke(args=[
        'import-historical-activities', str(SEED_CSV)])
    assert first.exit_code == 0, first.output
    assert '216 created' in first.output

    second = runner.invoke(args=[
        'import-historical-activities', str(SEED_CSV)])
    assert second.exit_code == 0, second.output
    assert '216 unchanged' in second.output

    with app.app_context():
        assert HistoricalActivity.query.count() == 216
        assert HistoricalActivity.query.filter_by(
            year_conducted=None).count() == 14


def test_historical_import_dry_run_rolls_back(app):
    result = app.test_cli_runner().invoke(args=[
        'import-historical-activities', str(SEED_CSV), '--dry-run'])
    assert result.exit_code == 0, result.output
    assert 'Dry run: 216 created' in result.output
    with app.app_context():
        assert HistoricalActivity.query.count() == 0
