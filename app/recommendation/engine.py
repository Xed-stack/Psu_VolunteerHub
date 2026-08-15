"""
Recommendation Engine for PSU Volunteer Hub
============================================
Content-based recommendation using Jaccard similarity between a
volunteer's skill/interest terms and each event's skill/category terms.

Jaccard similarity = |shared terms| / |all terms combined|
"""
from datetime import datetime
from app.models.event import Event, RecommendationLog
from app.models.user import User
from app.models import db


def _jaccard_similarity(user_terms: set, event_terms: set) -> float:
    """Return |intersection| / |union| of two term sets, 0.0 if both empty."""
    if not user_terms and not event_terms:
        return 0.0
    union = len(user_terms | event_terms)
    if union == 0:
        return 0.0
    return len(user_terms & event_terms) / union


def get_recommendations(volunteer_profile, events=None, top_n=5):
    """
    Score events for a volunteer using Jaccard similarity over
    combined skill + interest/category terms.

    Parameters:
      volunteer_profile : VolunteerProfile (or None for cold-start)
      events            : optional pre-filtered list of Event rows
      top_n             : number of recommendations to return

    Returns list of dicts: [{event, score, matched_skills, matched_interests, percentage}]
    """
    if volunteer_profile is None or (not volunteer_profile.skill_list and not volunteer_profile.interest_list):
        return _cold_start_recommendations(events, top_n)

    user = User.query.get(volunteer_profile.user_id)
    if user is None:
        return _cold_start_recommendations(events, top_n)

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


def _cold_start_recommendations(events=None, limit=5):
    """Fallback when no profile or skills/interests exist — return upcoming events."""
    if events is None:
        events = Event.query.filter(Event.date >= datetime.now()).order_by(
            Event.date.asc()).limit(limit).all()
    return [{
        'event': e,
        'score': 0,
        'matched_skills': set(),
        'matched_interests': set(),
        'percentage': 0,
    } for e in events[:limit]]


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
