"""Coordinator Partner Agencies reference layout and MOA-derived states."""
from datetime import date, timedelta

from app.models import db
from app.models.workspace import PartnerAgency, PartnerAgreement
from app.services.activity_workflow import local_now
from tests.test_app import app, client
from tests.test_workspace_overhaul import actors, sign_in, docx
from tests.test_partner_journey import records


def _agreement(agency_id, reference, start, end):
    from werkzeug.datastructures import FileStorage
    from app.services.activity_workflow import save_document
    document, _ = save_document(FileStorage(docx(), filename='signed.docx'))
    agreement = PartnerAgreement(agency_id=agency_id, reference=reference,
                                 valid_from=start, valid_until=end, document=document)
    db.session.add(agreement)
    return agreement


def test_partners_reference_layout_and_moa_statuses(app, client, actors, records):
    today = local_now().date()
    active = PartnerAgency(name='Active Partner Agency', contact_name='Active Contact',
                           campus_id=1, email='active@example.org', phone='0917')
    none = PartnerAgency(name='Unassigned Partner Agency', contact_name='Unassigned Contact',
                         campus_id=1, email='none@example.org')
    db.session.add_all([active, none])
    db.session.flush()
    _agreement(active.id, 'MOA-CURRENT', today - timedelta(days=2), today + timedelta(days=5))
    db.session.commit()
    sign_in(client, actors)

    body = client.get('/workspace/partners').get_data(as_text=True)
    assert 'partners-reference' in body and 'Quick Summary:' in body
    assert 'All MOA Statuses' in body and 'Apply Filters' in body
    assert 'Campus directory' in body and 'Agency Name (A–Z)' in body
    assert 'Active Valid' in body and 'Upcoming MOA' in body and 'No MOA on file' in body
    assert 'MOA-CURRENT' in body and 'View Agency' in body
    assert 'Total Agencies' in body and 'Pending / Unassigned' in body
    assert 'Other campus' not in body

    only_active = client.get('/workspace/partners?moa_status=active').get_data(as_text=True)
    assert 'Active Partner Agency' in only_active and 'Unassigned Partner Agency' not in only_active
    only_none = client.get('/workspace/partners?moa_status=none').get_data(as_text=True)
    assert 'Unassigned Partner Agency' in only_none and 'Active Partner Agency' not in only_none
    assert client.get('/workspace/partners?moa_status=invalid').status_code == 400

    by_email = client.get('/workspace/partners?q=active%40example.org').get_data(as_text=True)
    assert 'Active Partner Agency' in by_email
    context = client.get('/workspace/partners?activity_context=create').get_data(as_text=True)
    assert 'Back to Activity Draft' in context and 'name="activity_context" value="create"' in context
