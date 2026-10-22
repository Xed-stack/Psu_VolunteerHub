"""Profile rendering, validation, participation counts, and safe photo updates."""
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from tests.test_app import app, client, _create_user, _login_as
from tests.html_helpers import parse_html
from app.models import db
from app.models.user import User, Skill, Interest
from app.models.event import Event, Registration, Attendance


@pytest.fixture
def profile_user(app, client):
    uid = _create_user(app, email='profile-repair@test.com', campus_id=1)
    with app.app_context():
        skill = Skill(name='Profile test skill')
        interest = Interest(name='Profile test interest')
        db.session.add_all([skill, interest])
        db.session.flush()
        user = db.session.get(User, uid)
        user.skills = [skill]
        user.interests = [interest]
        db.session.commit()
        values = {'skills': [str(skill.id)], 'interests': [str(interest.id)]}
    _login_as(client, uid)
    return uid, values


def photo(format='PNG'):
    stream = BytesIO()
    Image.new('RGB', (16, 16), 'blue').save(stream, format)
    stream.seek(0)
    return stream


def test_selected_render_and_links(client, profile_user):
    _, values = profile_user
    body = ' '.join(client.get('/profile').get_data(as_text=True).split())
    for name, ids in values.items():
        assert f'name="{name}" value="{ids[0]}" checked' in body
    assert 'Verified volunteer' not in body
    assert 'width="96" height="96"' in body
    assert 'assets/temp_profile.jpg' in body
    assert 'View registrations' in body
    assert 'cosine' in body


@pytest.mark.parametrize('invalid', [[], ['999999'], ['oops'], ['1', 'oops']])
def test_invalid_choices_preserve_state(app, client, profile_user, invalid):
    uid, values = profile_user
    response = client.post('/profile', data={**values, 'skills': invalid})
    assert response.status_code == 422
    body = ' '.join(response.get_data(as_text=True).split())
    assert f'name="interests" value="{values["interests"][0]}" checked' in body
    assert 'skills-error' in body
    with app.app_context():
        assert [str(s.id) for s in db.session.get(User, uid).skills] == values['skills']


@pytest.mark.parametrize('payload,filename', [
    (b'not an image', 'photo.png'), (b'bad', 'photo.exe'),
    (b'x' * (3 * 1024 * 1024 + 1), 'large.png'),
], ids=['invalid-content', 'invalid-extension', 'oversized'])
def test_invalid_photos_leave_preferences_unchanged(app, client, profile_user, payload, filename):
    uid, values = profile_user
    with app.app_context():
        replacement_skill = Skill(name='Unsaved replacement skill')
        db.session.add(replacement_skill)
        db.session.commit()
        replacement_id = str(replacement_skill.id)
    response = client.post('/profile', data={
        **values, 'skills': [replacement_id], 'profile_image': (BytesIO(payload), filename),
    })
    assert response.status_code == 422
    assert b'photo-error' in response.data
    with app.app_context():
        assert db.session.get(User, uid).profile_image_path is None
        assert [str(s.id) for s in db.session.get(User, uid).skills] == values['skills']


def test_unavailable_catalog_disables_save(app, client, profile_user):
    with app.app_context():
        db.session.get(User, profile_user[0]).skills = []
        db.session.flush()
        Skill.query.delete()
        db.session.commit()
    body = ' '.join(client.get('/profile').get_data(as_text=True).split())
    assert 'No skills are available' in body
    assert 'disabled >Save profile' in body


@pytest.mark.parametrize('format,filename', [('JPEG', 'photo.jpg'), ('WEBP', 'photo.webp')])
def test_other_allowed_image_formats(app, client, profile_user, tmp_path, format, filename):
    app.static_folder = str(tmp_path)
    uid, values = profile_user
    assert client.post('/profile', data={**values, 'profile_image': (photo(format), filename)}).status_code == 302
    with app.app_context():
        assert (tmp_path / db.session.get(User, uid).profile_image_path).is_file()


def test_photo_cleanup_does_not_delete_local_assets(app, tmp_path):
    from app.routes.volunteer import _delete_profile_image
    app.static_folder = str(tmp_path)
    asset = tmp_path / 'assets' / 'temp_profile.jpg'
    asset.parent.mkdir()
    asset.write_bytes(b'placeholder fixture')
    with app.app_context():
        _delete_profile_image('assets/temp_profile.jpg')
    assert asset.exists()


def test_unsafe_image_dimensions_are_rejected(client, profile_user, monkeypatch):
    def unsafe_image(*args, **kwargs):
        raise Image.DecompressionBombError('unsafe dimensions')
    monkeypatch.setattr(Image, 'open', unsafe_image)
    response = client.post('/profile', data={
        **profile_user[1], 'profile_image': (BytesIO(b'oversized dimensions fixture'), 'photo.png'),
    })
    assert response.status_code == 422
    assert b'photo-error' in response.data


def test_photo_replacement_and_removal(app, client, profile_user, tmp_path):
    uid, values = profile_user
    app.static_folder = str(tmp_path)
    assert client.post('/profile', data={**values, 'profile_image': (photo(), 'first.png')}).status_code == 302
    with app.app_context():
        old = Path(app.static_folder) / db.session.get(User, uid).profile_image_path
    assert old.exists()
    assert client.post('/profile', data={**values, 'profile_image': (photo(), 'second.png')}).status_code == 302
    with app.app_context():
        new = Path(app.static_folder) / db.session.get(User, uid).profile_image_path
    assert new.exists() and not old.exists()
    assert client.post('/profile/image/remove').status_code == 302
    assert not new.exists()
    assert b'assets/temp_profile.jpg' in client.get('/profile').data


def test_failed_commit_keeps_old_photo(app, client, profile_user, tmp_path, monkeypatch):
    uid, values = profile_user
    app.static_folder = str(tmp_path)
    client.post('/profile', data={**values, 'profile_image': (photo(), 'original.png')})
    with app.app_context():
        original = db.session.get(User, uid).profile_image_path
    def fail():
        raise SQLAlchemyError('simulated save failure')
    with monkeypatch.context() as patch:
        patch.setattr(db.session, 'commit', fail)
        response = client.post('/profile', data={**values, 'profile_image': (photo(), 'replacement.png')})
    assert response.status_code == 422
    with app.app_context():
        assert db.session.get(User, uid).profile_image_path == original
    assert list((tmp_path / 'uploads' / 'profiles').iterdir()) == [tmp_path / original]


@pytest.mark.parametrize('extra_attendance', ['excused', None], ids=['excused', 'missing-attendance'])
def test_milestones_require_completed_present(app, client, profile_user, extra_attendance):
    uid, _ = profile_user
    expected = {}
    with app.app_context():
        for event_id, status, attendance in [(1, 'pending', 'present'), (2, 'cancelled', 'present'),
                                              (3, 'completed', 'absent'), (4, 'completed', 'present'),
                                              (5, 'completed', extra_attendance)]:
            reg = Registration(user_id=uid, event_id=event_id, status=status)
            db.session.add(reg)
            db.session.flush()
            if attendance is not None:
                db.session.add(Attendance(user_id=uid, event_id=event_id, registration_id=reg.id, status=attendance))
            expected[db.session.get(Event, event_id).title] = (
                'Eligible' if status == 'completed' and attendance == 'present' else 'Not eligible')
        db.session.commit()
    body = client.get('/profile').get_data(as_text=True)
    assert 'Based on 1 completed participation records' in body
    assert 'Bronze: Newcomer' in body
    region = parse_html(body).one('div', **{'aria-label': 'Recent registrations'})
    rows = region.one('tbody').all('tr')
    assert len(rows) == 5
    certificates = {}
    for row in rows:
        assert [cell.attrs.get('data-label') for cell in row.all('td')] == [
            'Activity', 'Registered', 'Status', 'Certificate']
        certificates[row.one('td', **{'data-label': 'Activity'}).text] = row.one(
            'td', **{'data-label': 'Certificate'}).text
    assert certificates == expected
    assert list(certificates.values()).count('Eligible') == 1


@pytest.mark.parametrize('role', ['coordinator', 'director', 'admin'])
def test_profile_role_isolation(app, client, role):
    uid = _create_user(app, email=f'{role}-profile@test.com', role=role)
    _login_as(client, uid)
    assert client.get('/profile').status_code == 403
    assert client.post('/profile').status_code == 403
    assert client.post('/profile/image/remove').status_code == 403
