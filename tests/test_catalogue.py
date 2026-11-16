"""Managed catalogue authorization, persistence, archive and migration regressions."""
import pytest
from sqlalchemy import create_engine, inspect, text
from tests.test_app import app, client, _create_user, _login_as
from app.models import db
from app.models.user import Skill, Interest, User, CatalogueRevision
from app.models.event import ActivityCategory, Event
from app.catalogue import skill_choices, category_choices, seed_skill_links, signup_catalogue
from app.catalogue_migration import migrate_catalogue


@pytest.fixture
def director(app,client):
    uid=_create_user(app,role='director',campus_id=1)
    _login_as(client,uid)
    return uid


@pytest.mark.parametrize('role', ['coordinator','volunteer'])
def test_denies_non_directors(app,client,role):
    _login_as(client,_create_user(app,role=role,campus_id=1))
    assert client.get('/workspace/catalogue').status_code==403
    assert client.post('/workspace/catalogue/categories/new',data={'name':'Forged'}).status_code==403


def test_anonymous_and_csrf(app,client,director):
    app.config['WTF_CSRF_ENABLED']=True
    assert client.post('/workspace/catalogue/categories/new',data={'name':'Missing CSRF'}).status_code==400
    with app.app_context():
        assert app.test_client().get('/workspace/catalogue').status_code==302


def test_create_map_edit_and_duplicates(app,client,director):
    with app.app_context():
        i=Interest(name='QA Interest');db.session.add(i);db.session.commit();iid=i.id
    response=client.post('/workspace/catalogue/skills/new',data={'name':'  QA   Skill  ','interest_ids':str(iid),'q':'QA','page':2})
    assert response.status_code==302 and 'q=QA' in response.location
    with app.app_context():
        skill=Skill.query.filter_by(name='QA Skill').one();sid=skill.id
        assert [row.id for row in skill.interests]==[iid]
        assert any(skill in row['skills'] for row in signup_catalogue())
    assert b'already exists' in client.post('/workspace/catalogue/skills/new',data={'name':'qa skill','interest_ids':str(iid)}).data
    assert client.post(f'/workspace/catalogue/skills/{sid}/interests',data={'interest_ids':'999999'}).status_code==200
    assert client.post('/workspace/catalogue/skills/new',data={'name':'x'*101,'interest_ids':str(iid)}).status_code==200


def test_archive_preserves_assignments_and_restore(app,client,director):
    with app.app_context():
        interest=Interest(name='QA Cause');skill=Skill(name='QA Archived',interests=[interest])
        category=ActivityCategory(name='QA Category');db.session.add_all([skill,category]);db.session.flush()
        user=db.session.get(User,director);user.skills.append(skill)
        event=Event.query.first();event.required_skills_rel.append(skill);event.category=category.name
        db.session.commit();sid,cid,eid=skill.id,category.id,event.id
    assert client.post(f'/workspace/catalogue/skills/{sid}/archive',data={'q':'QA','status':'active'}).status_code==302
    # Legacy category deletion now archives without reassignment or notifications.
    assert client.post(f'/admin/categories/{cid}/delete').status_code==302
    with app.app_context():
        skill=db.session.get(Skill,sid)
        assert not skill.is_active and skill in db.session.get(User,director).skills
        assert skill in db.session.get(Event,eid).required_skills_rel
        assert db.session.get(Event,eid).category=='QA Category'
        assert skill not in skill_choices() and skill in skill_choices([skill])
        assert 'QA Category' not in category_choices() and 'QA Category' in category_choices('QA Category')
        assert not any(skill in row['skills'] for row in signup_catalogue())
        iid=skill.interests[0].id
    assert b'Find and Restore This Skill' in client.post('/workspace/catalogue/skills/new',data={'name':'QA Archived','interest_ids':str(iid)}).data
    duplicate=client.post('/workspace/catalogue/categories/new',data={'name':'QA Category'})
    assert 'status=archived' in duplicate.location
    assert client.post(f'/workspace/catalogue/skills/{sid}/restore').status_code==302
    with app.app_context():assert db.session.get(Skill,sid).is_active


def test_general_and_category_duplicates(app,client,director):
    client.post('/workspace/catalogue/categories/new',data={'name':'General'})
    with app.app_context():gid=ActivityCategory.query.filter_by(name='General').one().id
    client.post(f'/workspace/catalogue/categories/{gid}/archive')
    client.post('/workspace/catalogue/categories/new',data={'name':' general '})
    with app.app_context():
        assert db.session.get(ActivityCategory,gid).is_active
        assert ActivityCategory.query.count()==1
    assert '/workspace/catalogue?' in client.get('/workspace/categories').location


def test_literal_search_pagination_and_restart_seed(app,client,director):
    with app.app_context():
        for n in range(28):db.session.add(Skill(name=f'QA {n:02}'))
        literal=Skill(name='100%_QA');db.session.add(literal);db.session.commit();lid=literal.id
    body=client.get('/workspace/catalogue?q=%25_').get_data(as_text=True)
    assert '100%_QA' in body and '1 matching skills' in body
    assert b'Next' in client.get('/workspace/catalogue?q=QA').data
    client.post(f'/workspace/catalogue/skills/{lid}/archive')
    with app.app_context():
        seed_skill_links({});db.session.commit()
        assert not db.session.get(Skill,lid).is_active
    assert b'100%_QA' in client.get('/workspace/catalogue?status=archived').data


def test_migration_idempotent_and_mapping_not_reseeded():
    engine=create_engine('sqlite:///:memory:')
    with engine.begin() as c:
        for statement in ['CREATE TABLE skills (id INTEGER PRIMARY KEY,name VARCHAR(100) UNIQUE NOT NULL)',
                          'CREATE TABLE interests (id INTEGER PRIMARY KEY,name VARCHAR(100) UNIQUE NOT NULL)',
                          'CREATE TABLE activity_categories (id INTEGER PRIMARY KEY,name VARCHAR(50) UNIQUE NOT NULL)',
                          "INSERT INTO skills VALUES (7,'Agriculture/Farming')", "INSERT INTO interests VALUES (9,'Environment')"]:
            c.execute(text(statement))
    before=inspect(engine).get_table_names()
    migrate_catalogue(engine,engine.url.database,dry_run=True)
    assert inspect(engine).get_table_names()==before
    migrate_catalogue(engine,engine.url.database)
    with engine.begin() as c:
        assert c.execute(text('SELECT interest_id,skill_id FROM interest_skills')).all()==[(9,7)]
        c.execute(text('DELETE FROM interest_skills'));c.execute(text('UPDATE skills SET is_active=0 WHERE id=7'))
    migrate_catalogue(engine,engine.url.database)
    with engine.connect() as c:
        assert c.execute(text('SELECT count(*) FROM interest_skills')).scalar()==0
        assert c.execute(text('SELECT is_active FROM skills WHERE id=7')).scalar()==0
    with pytest.raises(ValueError):migrate_catalogue(engine,'wrong')
    engine.dispose()
