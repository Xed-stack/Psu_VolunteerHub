"""Shared presentation helpers for server-rendered search and navigation."""
import re
from datetime import timedelta, timezone
from urllib.parse import urlencode, urlsplit, parse_qs
from flask import request, url_for
from flask_login import current_user
from markupsafe import Markup, escape
from app.help_center import contextual_help


def utc_record_time(value):
    """Display UTC record timestamps without changing local activity schedules."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone(timedelta(hours=8)))


def roster_link(endpoint, event_id, **updates):
    values = {}
    internal = endpoint == 'coordinator.attendance'
    source_internal = request.endpoint == 'coordinator.attendance'
    search = request.args.get('volunteer_search' if source_internal else 'q', '')
    values['volunteer_search' if internal else 'q'] = search
    if endpoint != 'workspace.activity_registrations':
        values['attendance_status'] = request.args.get('attendance_status', '')
    else:
        values['status'] = request.args.get('status', '') if request.endpoint == endpoint else ''
    if source_internal == internal:
        values['page'] = max(1, request.args.get('page', 1, type=int) or 1)
    previous = request.args.get('return_to', '')
    if previous.startswith('/') and not previous.startswith('//') and '\\' not in previous and not any(ord(c) < 32 for c in previous):
        from flask import current_app
        from werkzeug.exceptions import HTTPException
        try:
            parsed = urlsplit(previous)
            target, args = current_app.url_map.bind('').match(parsed.path, method='GET')
            selected = args.get('event_id') or parse_qs(parsed.query).get('event_id', [str(event_id)])[0]
            if target in ('workspace.activities', 'workspace.activity', 'workspace.activity_registrations',
                          'workspace.external', 'coordinator.attendance', 'workspace.activity_report') and str(selected) == str(event_id):
                values['return_to'] = previous
        except HTTPException:
            pass
    values.update(updates)
    return url_for(endpoint, event_id=event_id, **{key:value for key,value in values.items() if value not in ('',None)})


def query_url(remove=(), **updates):
    values = request.args.to_dict(flat=False)
    for key in ((remove,) if isinstance(remove, str) else remove):
        values.pop(key, None)
    values.pop('page', None)
    values.pop('category_page', None)
    for key, value in updates.items():
        if value is None or value == '':
            values.pop(key, None)
        else:
            values[key] = value
    path = url_for(request.endpoint, **(request.view_args or {})) if request.endpoint else request.path
    return path + ('?' + urlencode(values, doseq=True) if values else '')


def linked_url(endpoint, **updates):
    values = request.args.to_dict(flat=False) if endpoint == request.endpoint else {}
    if endpoint != request.endpoint:
        if request.endpoint in RETURN_LISTS:
            values['return_to'] = request.full_path.rstrip('?')
        elif request.args.get('return_to'):
            values['return_to'] = request.args['return_to']
    values.update(updates)
    return url_for(endpoint, **values)


def back_url(endpoint, **values):
    previous = request.args.get('return_to', '')
    if (endpoint in RETURN_LISTS and previous.startswith('/') and not previous.startswith('//')
            and '\\' not in previous and not any(ord(char) < 32 or ord(char) == 127 for char in previous)
            and len(previous) < 8192):
        return previous
    if endpoint in RETURN_LISTS:
        return url_for(endpoint, **values)
    return linked_url(endpoint, **values)


def highlight(value, query=''):
    value, query = str(value or ''), str(query or '').strip()[:200]
    if not query:
        return escape(value)
    parts = re.split('(' + re.escape(query) + ')', value, flags=re.IGNORECASE)
    return Markup('').join(Markup('<mark>') + escape(part) + Markup('</mark>')
                          if index % 2 else escape(part) for index, part in enumerate(parts))


def filter_count(keys):
    """Count applied specialist fields, not individual multi-select values."""
    aliases = {'affiliation': 'college_affiliation'}
    return sum(bool(request.args.get(key, request.args.get(aliases.get(key, ''), '')).strip())
               for key in keys if not (key in ('campus', 'campus_id')
                   and current_user.is_authenticated and current_user.role == 'coordinator'
                   and request.endpoint != 'events.opportunities'))


FILTERS = {
    'events.opportunities': {'search':'Search', 'category':'Category', 'campus':'Campus'},
    'workspace.activities': {'q':'Search', 'category':'Category', 'campus_id':'Campus'},
    'workspace.volunteers': {'q':'Search', 'campus_id':'Campus'},
    'workspace.partners': {'q':'Search'},
    'workspace.external': {'q':'Search', 'attendance_status':'Attendance'},
    'workspace.activity_registrations': {'q':'Search', 'status':'Registration'},
    'workspace.registrations': {'q':'Search', 'status':'Status'},
    'workspace.historical': {'q':'Search', 'year':'Year', 'campus_id':'Campus'},
    'workspace.overview': {'year':'Year', 'period':'Period', 'campus_id':'Campus', 'event_id':'Activity', 'department':'Department', 'delivery':'Delivery'},
    'workspace.report_results': {'year':'Year', 'period':'Period', 'campus_id':'Campus', 'event_id':'Activity', 'department':'Department', 'delivery':'Delivery'},
    'workspace.aop': {'year':'Year', 'campus_id':'Campus'},
    'admin.admin_dash': {'search':'Search', 'campus_id':'Campus', 'role':'Role', 'college_affiliation':'Affiliation'},
    'coordinator.attendance': {'volunteer_search':'Search', 'attendance_status':'Attendance'},
    'goals.details': {'year':'Year', 'program':'Program', 'office':'Office', 'status':'Status', 'plan':'Plan'},
}
for endpoint in ('workspace.overview','workspace.report_results','workspace.follow_up','workspace.campus'):
    FILTERS.setdefault(endpoint, {}).update({'activity_name':'Search','q':'Search','category':'Category','sdg_id':'SDG','sex':'Recorded Sex','affiliation':'Affiliation','college_affiliation':'Affiliation','attention':'Follow-up','campus':'Campus','start_date':'From','end_date':'To'})
FILTERS['workspace.registrations'].update({'campus':'Campus','category':'Category','start_date':'From','end_date':'To'})
FILTERS['workspace.historical'].update({'start_year':'From Year','end_year':'To Year','activity_type':'Activity Type'})
FILTERS['goals.details']['campus'] = 'Target Scope'
FILTERS['workspace.recognition']={'award_year':'Recognition Year'}
FILTERS['workspace.people_insights']={'campus_id':'Campus'}
FILTERS['workspace.follow_up'] = dict(FILTERS['workspace.report_results'])
FILTERS['workspace.campus'] = dict(FILTERS['workspace.report_results'])
RETURN_LISTS = set(FILTERS) - {'workspace.external', 'workspace.activity_registrations',
                             'coordinator.attendance', 'goals.details'}
RETURN_LISTS.add('workspace.reports')
RETURN_LISTS.add('admin.user_detail')
RETURN_LISTS.update({'workspace.partner','workspace.agreement_detail'})
RETURN_LISTS.update({'goals.details', 'goals.workspace', 'goals.target_detail', 'workspace.activity_report'})

PAGES = {
    'help_page':('help','Help and Guides'),
    'workspace.about':('about','About the Hub'),
    'workspace.overview':('overview', 'Overview'), 'events.volunteer_dash':('dashboard', 'Your Dashboard'),
    'workspace.activities':('activities','Activities'), 'workspace.activity':('activities','Activity Details'),
    'workspace.activity_registrations':('activities','Registrations'), 'workspace.activity_documents':('activities','Documents and Updates'),
    'workspace.document_upload':('activities','Upload Evidence'),'workspace.announcement_new':('activities','Compose Announcement'),
    'coordinator.upload_milestone':('activities','Upload Evidence'),'coordinator.publish_announcement':('activities','Compose Announcement'),
    'workspace.external':('activities','External Attendance'), 'workspace.external_new':('activities','Add External Participants'), 'coordinator.attendance':('activities','Attendance'),
    'workspace.create_activity':('activities','Create Activity'), 'coordinator.edit_activity':('activities','Edit Activity'),
    'events.opportunities':('activities','Activities'), 'events.opportunity_detail':('activities','Activity Details'),
    'events.register_for_event':('activities','Participation Agreement'),
    'workspace.reports':('reports','Reports'), 'workspace.report_results':('reports','Activity Accomplishments'),
    'workspace.activity_report':('reports','Combined Activity Report'),
    'workspace.aop':('reports','Annual Operational Plan'), 'workspace.historical':('reports','Historical Records'),
    'workspace.partners':('partners','Partner Agencies'), 'workspace.partner':('partners','Partner Agency'),
    'workspace.partner_new':('partners','Agency Details'), 'workspace.agreement_new':('partners','Add MOA'),
    'workspace.agreement_detail':('partners','MOA Details'), 'workspace.agreement_use':('partners','MOA Details'),
    'workspace.registrations':('registrations','Registration History'), 'workspace.registration':('registrations','Registration Details'),
    'workspace.volunteers':('overview','Volunteer Accounts'),
    'events.cancel_registration':('registrations','Withdraw From Activity'),
    'workspace.management':('management','Management'), 'workspace.categories':('management','Activity Categories'),
    'catalogue.index':('management','Skills and Activity Categories'), 'catalogue.skill_form':('management','Skill Interests'),
    'workspace.imports':('imports','Import Data'), 'workspace.import_dataset':('imports','Import Validation'),
    'admin.import_users_csv':('imports','Import Accounts'), 'admin.settings':('settings','System Settings'),
    'admin.admin_dash':('management','User Accounts'), 'admin.user_detail':('management','User Record'),
    'admin.create_user':('management','Create User'), 'admin.edit_user':('management','Edit Account'),
    'admin.reset_password':('management','Reset Password'),
    'workspace.draft_list':('drafts','Saved Drafts'), 'notifications.list_notifications':('notifications','Notifications'),
}

PAGES.update({'finding_reviews.detail':('follow_up','Finding Review'), 'workspace.follow_up':('follow_up','Needs Attention'), 'workspace.campus':('overview','Campus Workspace'),
              'workspace.recognition':('reports','Outstanding Recognition'), 'workspace.people_insights':('reports','People Insights'),
              'director.activity_calendar':('calendar','University Calendar'),'coordinator.activity_calendar':('calendar','Campus Calendar')})


def presentation_context():
    endpoint = request.endpoint or ''
    section, title = PAGES.get(endpoint, ('', 'PSU Volunteer Hub'))
    if endpoint=='workspace.activity_documents' and current_user.role=='director':
        title='Documents'
    if endpoint.startswith('goals.'):
        section, title = 'goals', 'Annual Plans'
    elif endpoint.startswith('volunteer.'):
        section, title = 'profile', 'Your Profile'
    elif endpoint.startswith('admin.') and not section:
        section, title = 'management', 'Account and Policy Management'
    filters = FILTERS.get(endpoint, {})
    chips = []
    for key, label in filters.items():
        if key == 'q' and request.args.get('activity_name') or key == 'college_affiliation' and request.args.get('affiliation'):
            continue
        if key in ('campus_id','campus') and current_user.is_authenticated and current_user.role == 'coordinator' and endpoint != 'events.opportunities':
            continue
        if key in ('start_date','end_date') and endpoint in ('workspace.overview','workspace.report_results','workspace.follow_up','workspace.campus') and request.args.get('period') not in (None,'custom'):
            continue
        for value in request.args.getlist(key):
            if not value or value == 'all':
                continue
            display = value
            if key in ('campus', 'campus_id'):
                from app.campuses import official_campus
                campus = official_campus(int(value)) if value.isdigit() else None
                display = campus.name if campus else 'Unavailable Campus'
                if key == 'campus' and request.args.get('campus_mode') == 'exclude':
                    display = 'Except ' + display
            elif key == 'role':
                display = {'volunteer':'Volunteer', 'coordinator':'Coordinator', 'director':'Director'}.get(value, value)
            elif key == 'period':
                display = {'annual':'Annual', 'semiannual':'Semi-Annual', 'quarterly':'Quarterly',
                           'custom':'Custom Dates', 'this_month':'This Month', 'last_month':'Last Month'}.get(value, value)
                if value in ('quarterly','semiannual'):
                    display += ' ' + request.args.get('segment', '1')
            elif key == 'sex':
                display = {'male':'Male','female':'Female','prefer_not_to_say':'Prefer Not to Say','unrecorded':'Not Recorded'}.get(value,value)
            elif key == 'sdg_id':
                from app.models.event import SdgGoal
                goal = None
                if value.isdigit():
                    goal = SdgGoal.query.filter_by(id=int(value)).first()
                display = f'SDG {goal.number}: {goal.name}' if goal else 'Unavailable SDG'
            elif key == 'event_id':
                from app.models.event import Event
                query = Event.query.filter_by(id=int(value)) if value.isdigit() else None
                if query is not None and current_user.is_authenticated and current_user.role == 'coordinator':
                    query = query.filter_by(campus_id=current_user.campus_id)
                event = query.first() if query is not None else None
                display = event.title if event else 'Unavailable Activity'
            remaining = [item for item in request.args.getlist(key) if item != value]
            remove = ('activity_name','q') if key in ('activity_name','q') and endpoint in ('workspace.overview','workspace.report_results','workspace.follow_up','workspace.campus') else ('affiliation','college_affiliation') if key in ('affiliation','college_affiliation') and endpoint.startswith('workspace.') else ()
            chips.append(dict(label=label, value=display, url=query_url(remove=remove, **({} if remove else {key:remaining or None}), **({'segment':None} if key == 'period' else {}))))
    previous = request.args.get('return_to','').split('?',1)[0]
    return_label = next((label for prefix,label in [('/workspace/reports/results','Back to Report Results'),
        ('/workspace/reports/activities/','Back to Activity Report'),('/workspace/reports/aop','Back to Annual Plan Summary'),
        ('/workspace/registrations/','Back to Registration'),('/workspace/registrations','Back to Registrations'),
        ('/opportunities','Back to Activities'),('/volunteer_dash','Back to Dashboard'),
        ('/workspace/campuses/','Back to Campus Workspace'),('/workspace/follow-up','Back to Needs Attention'),
        ('/director/calendar','Back to Calendar'),('/coordinator/calendar','Back to Calendar'),
        ('/workspace/overview','Back to Overview'),('/annual-goals','Back to Annual Evidence')]
        if previous.startswith(prefix)),None)
    return dict(ui_section=section, ui_page_title=title, ui_filters=chips,ui_return_label=return_label,
                ui_clear_url=query_url(remove=tuple(filters) + ('segment', 'campus_mode', 'goal_year')),
                query_url=query_url, linked_url=linked_url, back_url=back_url, highlight=highlight,
                filter_count=filter_count, contextual_help=contextual_help,
                utc_record_time=utc_record_time, roster_link=roster_link)
