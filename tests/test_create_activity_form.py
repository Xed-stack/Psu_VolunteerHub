from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'templates' / 'coordinator' / 'create_act_scrn1.html'
CSS = ROOT / 'static' / 'styles' / 'coordinator.css'


def test_create_activity_stages_existing_fields_without_changing_their_contract():
    content = TEMPLATE.read_text(encoding='utf-8')

    assert 'class="panel activity-form"' in content
    assert '<legend>Activity details</legend>' in content
    assert '<legend>Volunteer requirements</legend>' in content
    assert '<details class="activity-form__additional"' in content
    assert "{% set show_additional =" in content
    assert "{{ 'open' if show_additional }}" in content
    assert content.index('Activity details') < content.index('Volunteer requirements')
    assert content.index('Volunteer requirements') < content.index('Additional settings')

    for name in (
        'title', 'description', 'date', 'end_date', 'cancellation_days',
        'location', 'category', 'slots', 'required_skills', 'sdg_ids',
        'target_participants', 'participation_agreement_text',
        'participation_agreement_version', 'nda_required', 'nda_text',
        'nda_version', 'cover_image',
    ):
        assert f'name="{name}"' in content


def test_create_activity_mobile_action_bar_and_disclosure_have_scoped_styles():
    css = CSS.read_text(encoding='utf-8')

    for selector in (
        '.activity-form__section',
        '.activity-form__additional > summary',
        '.activity-form__actions',
        '.activity-form__actions .btn',
    ):
        assert selector in css
