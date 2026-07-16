"""
Recommendation Engine for PSU Volunteer Hub
============================================
Multi-factor scoring: matches volunteers to events using keyword overlap,
category match, past participation, availability, and recency.

Scoring weights:
  - Keyword overlap:  30%
  - Category match:   25%
  - Past participation: 20%
  - Availability:     15%
  - Recency:          10%

Formula:
  total = 0.30 * keyword_norm + 0.25 * category_match + 0.20 * participation
          + 0.15 * availability + 0.10 * recency
"""
from datetime import datetime
from app.models.event import Event, RecommendationLog
from app.models.user import User
from app.models import db


def get_recommendations(volunteer_profile, events=None, top_n=5):
    """
    Score events for a volunteer based on five weighted factors.

    Parameters:
      volunteer_profile : VolunteerProfile (or None for cold-start)
      events            : optional pre-filtered list of Event rows
      top_n             : number of recommendations to return

    Returns list of dicts: [{event, score, matched_skills, matched_interests, percentage}]
    """
    if volunteer_profile is None or (not volunteer_profile.skills and not volunteer_profile.interests):
        return _cold_start_recommendations(events, top_n)

    user_skills = set(s.strip().lower() for s in volunteer_profile.skills.split(',') if s.strip())
    user_interests = set(s.strip().lower() for s in volunteer_profile.interests.split(',') if s.strip())

    user = User.query.get(volunteer_profile.user_id)
    if user is None:
        return _cold_start_recommendations(events, top_n)

    registered_ids = {r.event_id for r in user.registrations if r.status not in ('cancelled', 'rejected')}
    attended_ids = {a.event_id for a in user.attendance_records if a.status == 'present'}
    confirmed_ids = {r.event_id for r in user.registrations if r.status == 'confirmed'}

    # Candidate events
    if events is not None:
        candidates = [e for e in events if e.id not in registered_ids]
    else:
        candidates = Event.query.filter(
            db.not_(Event.id.in_(registered_ids))
        ).filter(Event.date >= datetime.now()).order_by(Event.date.asc()).limit(50).all()

    now = datetime.now()
    scored = []

    for event in candidates:
        event_skills = set()
        if event.required_skills:
            event_skills = set(s.strip().lower() for s in event.required_skills.split(',') if s.strip())

        # 1. Keyword overlap (30%) — Jaccard-like over skill+interest union
        skill_overlap = user_skills & event_skills
        interest_overlap = user_interests & event_skills
        total_keywords = len(user_skills | event_skills)
        keyword_score = (len(skill_overlap) + len(interest_overlap)) / total_keywords if total_keywords else 0

        # 2. Category match (25%) — fraction of user interests present in event
        category_score = len(interest_overlap) / len(user_interests) if user_interests else 0

        # 3. Past participation (20%)
        if event.id in attended_ids:
            participation_score = 1.0
        elif event.id in confirmed_ids:
            participation_score = 0.5
        else:
            participation_score = 0.0

        # 4. Availability (15%)
        if event.slots <= 0:
            availability_score = 0.5
        else:
            rem = event.slots_remaining()
            availability_score = min(rem / event.slots, 1.0) if rem > 0 else 0.1

        # 5. Recency (10%)
        if event.date >= now:
            days_until = (event.date - now).days
            recency_score = max(0.0, 1.0 - (days_until / 365.0))
        else:
            recency_score = 0.0

        total_score = (
            0.30 * keyword_score +
            0.25 * category_score +
            0.20 * participation_score +
            0.15 * availability_score +
            0.10 * recency_score
        )

        scored.append({
            'event': event,
            'score': round(total_score, 4),
            'matched_skills': skill_overlap,
            'matched_interests': interest_overlap,
            'percentage': min(round(total_score * 100), 100),
        })

    scored.sort(key=lambda x: x['score'], reverse=True)
    top = scored[:top_n]
    _log_recommendations(user, top)
    return top


def _cold_start_recommendations(events=None, limit=5):
    """Fallback when no profile or skills exist — return upcoming events."""
    if events is None:
        events = Event.query.filter(Event.date >= datetime.now()).order_by(Event.date.asc()).limit(limit).all()
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
