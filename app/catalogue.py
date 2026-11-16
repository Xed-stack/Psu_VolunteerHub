"""Shared selectable catalogue; existing assignments may retain archived records."""
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from app.models import db
from app.models.user import Skill, Interest, CatalogueRevision
from app.models.event import ActivityCategory

VERSION = 'managed-catalogue-v1'


def seed_skill_links(mapping):
    if db.session.get(CatalogueRevision, VERSION):
        return
    for name, names in mapping.items():
        interest = Interest.query.filter_by(name=name).first()
        if interest:
            for skill in Skill.query.filter(Skill.name.in_(names)).all():
                if interest not in skill.interests:
                    skill.interests.append(interest)
    db.session.add(CatalogueRevision(version=VERSION))


def skill_choices(existing=()):
    ids = [item.id for item in existing]
    return Skill.query.filter(or_(Skill.is_active.is_(True), Skill.id.in_(ids))).order_by(db.func.lower(Skill.name), Skill.id).all()


def category_choices(existing=None):
    names = [row.name for row in ActivityCategory.query.filter_by(is_active=True).order_by(db.func.lower(ActivityCategory.name)).all()]
    if existing and existing not in names:
        names.append(existing)
    return names


def signup_catalogue():
    return [dict(interest=interest, skills=sorted(
        [skill for skill in interest.skills if skill.is_active], key=lambda row: row.name.casefold()))
        for interest in Interest.query.options(selectinload(Interest.skills)).order_by(db.func.lower(Interest.name)).all()
        if any(skill.is_active for skill in interest.skills)]


def signup_selections(interest_ids, skill_ids):
    catalogue = signup_catalogue()
    interests = [row['interest'] for row in catalogue if str(row['interest'].id) in set(map(str, interest_ids))]
    allowed = {str(skill.id): skill for row in catalogue if row['interest'] in interests for skill in row['skills']}
    skills = [allowed[value] for value in dict.fromkeys(map(str, skill_ids)) if value in allowed]
    return interests, skills
