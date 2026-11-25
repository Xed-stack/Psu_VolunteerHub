"""Activity entry decisions use the same active evidence as Needs Attention."""
from collections import Counter
from werkzeug.datastructures import MultiDict
from app.models.event import Event
from app.services import finding_reviews
from app.services.workspace_reports import workspace_report, follow_up_items


def attention_counts(events, user, now):
    ids = {event.id for event in events}
    if not ids:
        return Counter()
    data = workspace_report(Event.query.filter(Event.id.in_(ids)),
                            MultiDict(dict(period='all', year=str(now.year))), user, now)
    data.update(show_annual_findings=False, allow_scheduling=False)
    if finding_reviews.available():
        return Counter(item['snapshot']['event_id'] for item in finding_reviews.active_items(data)
                       if item['snapshot'].get('event_id') in ids)
    return Counter(item['event'].id for item in follow_up_items(data) if item.get('event'))
