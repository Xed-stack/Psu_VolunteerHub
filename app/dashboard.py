"""Presentation summaries derived from the same rows as PDF and CSV reports."""


def summarize_report(rows):
    """Group existing report counts without querying or changing their meaning."""
    campuses, categories, months, weeks, sdgs = {}, {}, {}, {}, {}
    for row in rows:
        for groups, key in (
            (campuses, row['campus'] or 'Unassigned'),
            (categories, row['category']),
            (months, row['date'].strftime('%Y-%m')),
            (weeks, row['date'].strftime('%G-W%V')),
        ):
            counts = groups.setdefault(key, {'registrations': 0, 'attended': 0})
            counts['registrations'] += row['registrations']
            counts['attended'] += row['attended']
        for goal in row['sdgs'].split(', '):
            sdgs[goal] = sdgs.get(goal, 0) + 1

    def comparison(groups):
        return [
            {'label': label, **counts,
             'rate': round(counts['attended'] / counts['registrations'] * 100, 1)
             if counts['registrations'] else 0}
            for label, counts in sorted(
                groups.items(), key=lambda item: (-item[1]['registrations'], item[0]))
        ]

    def trend(groups):
        periods = sorted(groups)
        return {
            'labels': periods,
            'primary': [groups[period]['registrations'] for period in periods],
            'secondary': [groups[period]['attended'] for period in periods],
            'primaryName': 'Registrations', 'secondaryName': 'Attended',
        }

    return {
        'campuses': comparison(campuses),
        'categories': comparison(categories),
        'monthly': trend(months),
        'weekly': trend(weeks),
        'sdgs': sorted(sdgs.items()),
        'activities': sorted(rows, key=lambda row: row['registrations'], reverse=True)[:10],
    }
