"""
Recommendation Engine for PSU Volunteer Hub
============================================
Content-based recommendation using Jaccard similarity between a
volunteer's skill/interest terms and each event's skill/category terms.

Jaccard similarity = |shared terms| / |all terms combined|
"""
from datetime import datetime
from app.models.event import Event, RecommendationLog, Registration
from app.models.user import User, Skill, Interest
from app.models import db


def _jaccard_similarity(user_terms: set, event_terms: set) -> float:
    """Return |intersection| / |union| of two term sets, 0.0 if both empty."""
    if not user_terms and not event_terms:
        return 0.0
    union = len(user_terms | event_terms)
    if union == 0:
        return 0.0
    return len(user_terms & event_terms) / union


def get_recommendations(volunteer_profile, events=None, top_n=5, campus_id=None):
    """
    Score events for a volunteer using Jaccard similarity over
    combined skill + interest/category terms.

    Parameters:
      volunteer_profile : VolunteerProfile (or None for cold-start)
      events            : optional pre-filtered list of Event rows
      top_n             : number of recommendations to return
      campus_id         : campus used by the cold-start fallback

    Returns list of dicts: [{event, score, matched_skills, matched_interests, percentage}]
    """
    if volunteer_profile is None or (not volunteer_profile.skill_list and not volunteer_profile.interest_list):
        return _cold_start_recommendations(events, top_n, campus_id=campus_id)

    user = User.query.get(volunteer_profile.user_id)
    if user is None:
        return _cold_start_recommendations(events, top_n, campus_id=campus_id)

    user_skills = set(s.lower() for s in volunteer_profile.skill_list)
    user_interests = set(s.lower() for s in volunteer_profile.interest_list)
    user_terms = user_skills | user_interests

    registered_ids = {r.event_id for r in user.registrations if r.status not in (
        'cancelled', 'rejected')}

    if events is not None:
        candidates = [e for e in events if e.id not in registered_ids]
    else:
        candidates = Event.query.filter(
            db.not_(Event.id.in_(registered_ids))
        ).filter(Event.date >= datetime.now()).order_by(Event.date.asc()).limit(50).all()

    scored = []
    for event in candidates:
        event_skills = set(s.name.lower() for s in event.required_skills_rel)
        event_terms = set(event_skills)
        if event.category:
            event_terms.add(event.category.strip().lower())

        score = _jaccard_similarity(user_terms, event_terms)
        matched = user_terms & event_terms

        scored.append({
            'event': event,
            'score': round(score, 4),
            'matched_skills': matched & user_skills,
            'matched_interests': matched & user_interests,
            'percentage': min(round(score * 100), 100),
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    top = scored[:top_n]
    _log_recommendations(user, top)
    return top


def _cold_start_recommendations(events=None, limit=5, campus_id=None):
    """
    Fallback when no profile, skills, or interests exist.
    Ranks upcoming events by popularity (registration count), preferring
    the volunteer's campus, with soonest events breaking ties.
    """
    if events is None:
        query = Event.query.filter(Event.date >= datetime.now())
        if campus_id:
            query = query.filter(Event.campus_id == campus_id)
        events = query.all()

    reg_counts = dict(
        db.session.query(Registration.event_id, db.func.count(Registration.id))
        .group_by(Registration.event_id).all()
    )

    events = sorted(
        events,
        key=lambda e: (reg_counts.get(e.id, 0), e.date.timestamp() * -1),
        reverse=True,
    )
    return [{
        'event': e,
        'score': 0,
        'matched_skills': set(),
        'matched_interests': set(),
        'percentage': 0,
    } for e in events[:limit]]


def bootstrap_from_event(user, event, top_skills=3):
    """
    Seed a cold-start volunteer's skills/interests from their first
    registered event, so future recommendations become personalized.
    No-op once the user already has any skills or interests.
    """
    if user.skills or user.interests:
        return

    for name in [s.name for s in event.required_skills_rel][:top_skills]:
        skill = Skill.query.filter_by(name=name).first() or Skill(name=name)
        db.session.add(skill)
        user.skills.append(skill)

    if event.category:
        interest = Interest.query.filter_by(
            name=event.category).first() or Interest(name=event.category)
        db.session.add(interest)
        user.interests.append(interest)

    db.session.commit()


def _log_recommendations(user, recommendations):
    """Persist recommendation results for analysis."""
    for rec in recommendations:
        log = RecommendationLog(
            user_id=user.id,
            event_id=rec['event'].id,
            similarity_score=rec['score'],
        )
        db.session.add(log)
    db.session.commit()
