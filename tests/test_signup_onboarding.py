"""Onboarding presentation and unchanged registration trust boundaries."""
import pytest
from tests.test_app import app, client
from tests.test_auth_remake import catalog, signup_data as legacy_signup_data, Tags
from app.models import db
from app.models.user import User
from app.models.policy import TermsRevision, PrivacyRevision, TermsAcceptance, PrivacyAcknowledgement


def signup_data(**overrides):
    data = legacy_signup_data()
    data.update(overrides)
    return data


@pytest.mark.parametrize('path,step', [('/auth/interests','1'),('/auth/register','2')])
def test_onboarding_shell(client, path, step):
    body = client.get(path).get_data(as_text=True)
    assert 'onboarding-page' in body and 'Account Creation Progress' in body
    assert 'aria-current="step"' in body
    assert 'auth-brand__photo' not in body
    assert 'scripts/onboarding.js' in body
    assert 'data-server-values="false"' in body
    assert 'Coordinator, Director, and Admin' not in body


def test_back_action_preserves_preferences_and_error_values_are_authoritative(client, catalog):
    interest, skill = catalog
    client.post('/auth/interests', data={'interests':interest, 'skills':skill})
    body = client.get('/auth/register').get_data(as_text=True)
    assert 'Back to Interests and Skills' in body
    assert 'onboarding-preferences-summary' not in body
    with client.session_transaction() as session:
        assert session['selected_interests'] == [interest]
        assert session['selected_skills'] == [skill]
    body = client.post('/auth/register', data=signup_data(password='Bad', password_confirmation='Bad')).get_data(as_text=True)
    assert 'data-server-values="true"' in body
    assert Tags(body).named('first_name')['value'] == 'QA'
    assert not Tags(body).named('password').get('value')


@pytest.mark.parametrize('category', ['student','faculty','staff'])
def test_category_requirements_and_volunteer_only_creation(app, client, category):
    data = signup_data(password='StrongPassword1!',password_confirmation='StrongPassword1!')
    data.update(volunteer_type=category, role='director', account_type='director')
    response = client.post('/auth/register', data=data)
    assert response.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email=data['email']).one()
        assert user.role == 'volunteer' and user.check_password('StrongPassword1!')
    with client.session_transaction() as session:
        assert session['clear_signup_draft']
    duplicate = client.post('/auth/register', data=data)
    assert duplicate.status_code == 200
    assert b'An account with this email already exists.' in duplicate.data


def test_consent_is_not_retained_and_success_records_current_policies(app, client):
    with app.app_context():
        db.session.add(TermsRevision(title='Test Terms',body='Terms <script>authored</script>',version='1'))
        db.session.add(PrivacyRevision(title='Test Privacy',body='Privacy text.',version='1'))
        db.session.commit()
    data = signup_data(password='StrongPassword1!',password_confirmation='Mismatch1!')
    data.update(terms_accepted='on', privacy_acknowledged='on')
    body = client.post('/auth/register',data=data).get_data(as_text=True)
    assert 'checked' not in Tags(body).named('terms_accepted')
    assert 'checked' not in Tags(body).named('privacy_acknowledged')
    assert 'Terms &lt;script&gt;authored&lt;/script&gt;' in body
    data['password_confirmation'] = data['password']
    assert client.post('/auth/register',data=data).status_code == 302
    with app.app_context():
        user = User.query.filter_by(email=data['email']).one()
        assert TermsAcceptance.query.filter_by(user_id=user.id).count() == 1
        assert PrivacyAcknowledgement.query.filter_by(user_id=user.id).count() == 1


def test_internal_missing_affiliation_is_rejected_and_select_available_without_js(client):
    body = client.get('/auth/register').get_data(as_text=True)
    assert 'disabled' not in Tags(body).named('college_affiliation')
    data = signup_data(password='StrongPassword1!',password_confirmation='StrongPassword1!')
    data.update(id_number='',college_affiliation='')
    response = client.post('/auth/register',data=data)
    assert response.status_code == 200
    assert b'PSU ID Number is required' in response.data
    assert b'Select a College Affiliation for the selected campus.' in response.data


def test_empty_catalog_explains_recovery_without_a_dead_end(client):
    body = client.get('/auth/interests').get_data(as_text=True)
    assert 'No interests are configured' in body
    assert client.post('/auth/interests',data={}).status_code == 302


def test_external_category_is_not_offered_or_accepted(app, client):
    body = client.get('/auth/register').get_data(as_text=True)
    assert 'value="external"' not in body
    data = signup_data(password='StrongPassword1!',password_confirmation='StrongPassword1!',volunteer_type='external')
    response = client.post('/auth/register',data=data)
    assert response.status_code == 200
    assert b'Select Student, Faculty, or Staff.' in response.data
    with app.app_context():
        assert User.query.filter_by(email=data['email']).first() is None
