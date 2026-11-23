"""Read-only Director list totals using the existing AOP eligibility rules."""
from app.services.aop_goals import progress


STATUSES = {'not_started': 'Not Started', 'in_progress': 'In Progress',
            'met': 'Target Met', 'above': 'Above Target'}


def director_list(parents, children, campus_id=None):
    selected = [child for child in children if campus_id is None or child.campus_id == campus_id]
    cards = []
    for goal in parents:
        values = progress(goal, selected)
        actual, target = values['completed'], values['target']
        status = 'above' if actual > target else 'met' if actual == target else 'in_progress' if actual else 'not_started'
        cards.append(dict(goal=goal, result=values, status=status,
                          rate=round(actual / target * 100, 1) if target else None,
                          committed=sum(int(child.target_value) for child in values['commitments'])))
    campus_ids = sorted({child.campus_id for child in selected})
    breakdown = []
    for identity in campus_ids:
        members = [child for child in selected if child.campus_id == identity]
        breakdown.append(dict(id=identity, name=members[0].campus.name,
            committed=sum(int(child.target_value) for child in members),
            completed=sum(progress(goal, members)['completed'] for goal in parents)))
    breakdown.sort(key=lambda row: row['name'])
    summary = dict(target=sum(card['result']['target'] for card in cards),
        completed=sum(card['result']['completed'] for card in cards),
        remaining=sum(card['result']['remaining'] for card in cards),
        committed=sum(card['committed'] for card in cards), campuses=len(campus_ids))
    return cards, summary, breakdown
