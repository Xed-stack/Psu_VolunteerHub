"""Read-only Overview presentation using facts already loaded by Reports."""
from app.annual_goals import summarize


FINDING_LABELS = {
    'record_attendance': 'Ongoing Activities Need Attendance',
    'pending_attendance': 'Ended Activities Have Unrecorded Attendance',
    'schedule_limit': 'Activities Have Incomplete Schedules',
    'no_targets': 'Campuses Have No AOP Commitments',
    'missed_targets': 'Activities Did Not Reach Their Numeric Target',
    'low_attendance': 'Activities Need Participation Review',
    'remaining_goals': 'Campuses Have AOP Activities Remaining',
    'no_activities': 'Campuses Have No Approved Activities in This Period',
}


def aop_achievement(data, dataset):
    """Aggregate existing per-goal credits against university Director targets."""
    from app.services.aop_goals import progress

    goals, children = dataset
    allowed = {row['id'] for row in data['campus_chart']}
    selected = [child for child in children if child.campus_id in allowed]
    target = sum(int(goal.target_value) for goal in goals)
    completed = sum(progress(goal, selected)['completed'] for goal in goals)
    campuses = []
    for campus in sorted(data.get('campuses', []), key=lambda campus: campus.name):
        if campus.id not in allowed:
            continue
        commitments = [child for child in selected if child.campus_id == campus.id]
        campuses.append(dict(id=campus.id, name=campus.name, submitted=bool(commitments),
            committed=sum(int(child.target_value) for child in commitments),
            completed=sum(progress(goal, commitments)['completed'] for goal in goals)))
    return dict(target=target, completed=completed,
                committed=sum(int(child.target_value) for child in selected),
                rate=round(completed / target * 100, 1) if target else None,
                exceeded=max(completed - target, 0), campuses=campuses,
                campuses_completed=sum(row['completed'] > 0 for row in campuses))


def campus_aop_achievement(data):
    """Present campus activity credit without changing goal-met calculations."""
    rows = data['goals']['rows']
    target = sum(int(row['target']) for row in rows)
    completed = sum(int(row['actual'] or 0) for row in rows)
    return dict(target=target, committed=target, completed=completed,
                rate=round(completed / target * 100, 1) if target else None,
                exceeded=max(completed - target, 0))


def overview_context(data, findings):
    allowed = {row['id']: row for row in data['campus_chart']}
    annual = data['campus_goals']
    if data['campus_id']:
        campus = next((row for row in data['campuses'] if row.id == data['campus_id']), None)
        annual = [dict(data['goals'], campus=campus.name if campus else 'Unassigned')]
    comparisons = [dict(row, conducted=allowed[row['campus_id']]['count'])
                   for row in annual if row['campus_id'] in allowed]
    rollup = summarize([goal for row in comparisons for goal in row['rows']], data['year'])
    groups = {}
    for finding in findings:
        group = groups.setdefault(finding['code'], dict(code=finding['code'],
            title=FINDING_LABELS[finding['code']], count=0, campuses=set(), scope=finding['scope']))
        group['count'] += 1
        if finding['campus']:
            group['campuses'].add(finding['campus'].name)
    for group in groups.values():
        group['campuses'] = sorted(group['campuses'])
    return dict(campus_comparison=comparisons, campus_rollup=rollup,
                finding_groups=list(groups.values()), finding_total=len(findings))
