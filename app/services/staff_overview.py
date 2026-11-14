"""Read-only Overview presentation using facts already loaded by Reports."""
from app.annual_goals import summarize


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
    labels = {
        'record_attendance': 'Ongoing Activities Need Attendance',
        'pending_attendance': 'Ended Activities Have Unrecorded Attendance',
        'schedule_limit': 'Activities Have Incomplete Schedules',
        'no_targets': 'Campuses Have No Approved Annual Targets',
        'missed_targets': 'Activities Did Not Reach Their Numeric Target',
        'low_attendance': 'Activities Need Participation Review',
        'remaining_goals': 'Campuses Have Annual Evidence or Targets to Review',
        'no_activities': 'Campuses Have No Approved Activities in This Period',
    }
    for finding in findings:
        group = groups.setdefault(finding['code'], dict(code=finding['code'],
            title=labels[finding['code']], count=0, campuses=set(), scope=finding['scope']))
        group['count'] += 1
        if finding['campus']:
            group['campuses'].add(finding['campus'].name)
    for group in groups.values():
        group['campuses'] = sorted(group['campuses'])
    return dict(campus_comparison=comparisons, campus_rollup=rollup,
                finding_groups=list(groups.values()), finding_total=len(findings))
