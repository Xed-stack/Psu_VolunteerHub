"""Reviewed task guidance; audience filtering also applies to direct article URLs."""
from flask import abort, request, url_for
from flask_login import current_user

SIGNED = ('volunteer', 'coordinator', 'director')
STAFF = ('coordinator', 'director')
EVERYONE = ('public',) + SIGNED


def topic(slug, title, summary, group, audience, steps, actions=(), related=(), warnings=(), keywords=''):
    return dict(slug=slug, title=title, summary=summary, group=group, audience=audience,
                steps=steps, actions=actions, related=related, warnings=warnings, keywords=keywords)


TOPICS = [
    topic('documents-updates','Activity Documents and Announcements','Upload private evidence and prepare updates for registered volunteers.','Activity Management',('coordinator',),[
        'Open an activity and choose Documents and Updates. Documents contains the approved proposal, when attached, and supporting evidence. Announcements shows the publication history.',
        'Upload Evidence accepts JPEG, PNG, WebP, PDF or DOCX within the displayed size limit. It adds supporting evidence and does not replace the approved proposal. Downloads require an authorized account.',
        'Compose Announcement has an inline preview. Publishing saves the message and creates in-app notifications for pending and confirmed account registrations. External participants and completed or cancelled registrations are excluded.',
        'Schedule Notice is a message type. It does not cancel or reschedule an activity.',
        'The upload and announcement forms save separate drafts. Restore a saved attachment or message after refresh, and check the saved indicator before leaving. Successful submission clears only the submitted part of an older combined draft.',
        'A legacy shared draft may contain both an upload and a message. Submitting either preserves the other; Discard Draft removes the entire shared draft after confirmation.',
        'Documents and announcements are separate from attendance. Ended activities retain their records and existing upload/publishing permissions.'
    ],('staff-activities','drafts'),('saved-drafts','activity-status','getting-support')),
    topic('skills-and-categories','Managing Skills and Activity Categories','Maintain university-wide skills and category choices.','Management',('director',),[
        'Open Management → Skills and Activity Categories. Use the Skills and Activity Categories tabs to manage the separate lists.',
        'Add a skill and select one or more existing interests. Active linked skills appear in signup, profiles, and activity forms. Edit Interests changes those connections without renaming the skill.',
        'Archive hides an item from new selections. Existing user skills, activity assignments, reports, and historical records remain intact. General cannot be archived.',
        'Open Archived to restore an item. A name already present in Archived must be restored rather than added again.',
        'If a saved form contains an archived selection, choose an available replacement. Existing assigned archived skills may be retained or removed when editing.'
    ],('catalogue','management'),('accounts','saved-drafts'),keywords='skill category archive restore interests configuration'),
    topic('getting-started','Getting Started','Find your campus, role, and first task.','Getting Started',EVERYONE,[
        'Volunteers can create an account using a valid institutional or non-institutional email.',
        'Choose your preferred campus, interests, and skills. Review the published terms and privacy notice before accepting.',
        'After signing in, use the dashboard for the tasks available to your role. Staff accounts and assigned campus are managed by the Director.'
    ],('signup','signin','dashboard'),('campus','account-access')),
    topic('account-access','Sign-In and Account Access','Resolve sign-in, deactivation, and permission problems.','Account Help',EVERYONE,[
        'Use the identifier requested on the Sign In screen and your current password.',
        'If you forgot the password, open Forgot Password and follow the recovery instructions. Recovery responses do not confirm whether an account exists.',
        'A deactivated account can request reactivation from Sign In. An authorized staff member must reactivate it.',
        'If a record is unavailable, return to its list. It may belong to another campus or require another role.'
    ],('signin','forgot'),('password-recovery','getting-support'),keywords='login locked forbidden 403 404'),
    topic('password-recovery','Recovering Your Password','Request recovery and return to Sign In.','Account Help',EVERYONE,[
        'Open Forgot Password and submit the requested account information.',
        'Follow a valid recovery link received through the configured account recovery process. Expired or previously used links cannot reset a password.',
        'Choose a password meeting the displayed requirements and enter its confirmation. Sign in again after resetting it.',
        'If recovery is unavailable or no message arrives, check your email folders and use your campus support channels.'
    ],('forgot','signin'),('account-access','getting-support'),('Never share passwords, recovery links, or authentication tokens with support.',)),
    topic('campus','Campus and Account Scope','Understand preferred campus and assigned staff scope.','Getting Started',EVERYONE,[
        'A volunteer’s preferred campus helps group recommendations. Review the actual campus and location on every activity.',
        'Volunteers can review their preferred campus in Profile. Existing registrations still belong to their original activities.',
        'Coordinators work within their assigned campus. Directors begin with university-wide results and can drill into a campus.',
        'If your staff campus or role is incorrect, use institutional support channels rather than creating another account.'
    ],('profile',),('getting-started','getting-support')),
    topic('agreements','Privacy and Participation Agreements','Review required agreements without losing track of consent.','Getting Started',EVERYONE,[
        'Read the terms and privacy notice shown for your account before accepting them.',
        'When joining an activity, read the displayed participation agreement and any applicable existing activity-specific consent requirements.',
        'Select the required consent controls yourself. Refreshing a form does not retain unsubmitted consent or passwords.',
        'Agreement identifiers are internal. Use the readable document and displayed requirements when deciding whether to participate.'
    ],('activities',),('registration','saved-drafts','getting-support')),
    topic('getting-support','Getting Support','Prepare useful details for your campus support contact.','Troubleshooting',EVERYONE,[
        'For volunteer access or participation questions, contact your campus Extension Coordinator through established institutional channels. Staff should use their existing institutional support channels.',
        'Include the page name, activity title or reference if relevant, the action attempted, the exact error message, and when it occurred in Philippine time.',
        'Explain whether you were using a phone or computer and whether a draft or upload was involved.',
        'For attendance questions after an activity ends, ask the Coordinator to review the combined printed report and correction process.'
    ],(),('account-access','saved-drafts'),('Do not send passwords, recovery links, authentication tokens, or unnecessary personal information.',)),
    topic('saved-drafts','Saved Drafts and Uploads','Restore unfinished input and recover from save failures.','Account Help',SIGNED,[
        'Substantial forms show Saving…, Draft saved, or Draft restored. Wait for Draft saved before leaving.',
        'If saving fails, keep the page open, check connectivity, and retry. An unsaved-change warning is not confirmation that the input was saved.',
        'Open Saved Drafts to resume or discard unfinished work. Signed-in drafts are private to your account and authorized campus.',
        'Saved Drafts shows your most recent saves first in Philippine time. Resume opens the saved form. Discard asks for confirmation and removes the draft and its saved uploads; JavaScript is required for Discard.',
        'After refresh, check the saved-attachment notice. A file input may appear empty while the retained document is still attached.',
        'Successful submission clears that form’s draft. Passwords, tokens, and unsubmitted consent are never part of saved input.'
    ],('drafts',),('getting-support','imports'),keywords='refresh reload attachment cover saving failure'),
    topic('navigation','Filters, Back Links, and Missing Records','Keep your place when moving between lists and details.','Troubleshooting',SIGNED,[
        'Enter a search and use its button or Enter. Apply Filters submits the selected controls.',
        'More Filters contains specialist refinements. Applied chips remain visible; remove one chip to preserve the others.',
        'Use the page’s Back link to return with search, filters, and pagination intact where supported.',
        'A forbidden or unavailable record may be outside your role or campus. Return to an authorized list or ask for support.'
    ],('dashboard',),('getting-support','reports'),keywords='search % _ literal pagination 403 404'),
    topic('notifications','Notifications and Dashboard Guides','Review updates and replay the introduction.','Getting Started',SIGNED,[
        'Open the notification bell to read activity and account updates. Follow an available record link to review the source.',
        'Mark individual notifications read, or use Mark All as Read when you have reviewed them.',
        'Use All to see every update, or Unread to focus on updates you have not marked read. Opening a record does not automatically mark its notification read. Times are displayed in Philippine time.',
        'Use Show Dashboard Guide in Help or on your dashboard to replay the role-specific introduction.',
        'The guide explains visible controls. Back, Next, Finish, Skip, and Escape control the guide without submitting forms.'
    ],('notifications','dashboard'),('navigation','getting-support')),
    topic('recommendations','Recommendations and Your Calendar','Find relevant activities and understand the dashboard view.','Activities and Participation',('volunteer',),[
        'Recommendations rank positive interest matches using cosine similarity. Your preferred-campus group appears first; zero-interest matches are excluded.',
        'Update interests and skills in Profile. Recommendations support your choice and do not reserve a slot.',
        'Browse all activities when you want more choices. Check campus, schedule, location, requirements, and availability.',
        'The dashboard defaults to recommendations until you have an active upcoming registration, then Calendar. Open an activity to review its registration details.'
    ],('dashboard','activities','profile'),('registration','participation-history'),keywords='matching skills interests ranking'),
    topic('registration','Joining an Activity','Review availability, agreements, and registration confirmation.','Activities and Participation',('volunteer',),[
        'Open the activity details and check the full schedule, campus, location, requirements, and available capacity.',
        'Use the participation action when registration is available. Read the agreement and explicitly select required consent before Agree and Join.',
        'Review the confirmation and your registration details. If already registered, use View Registration rather than registering again.',
        'Full, closed, or cancelled activities explain why joining is unavailable. Availability is rechecked on submission; another person may take the last slot.'
    ],('activities','registrations'),('agreements','withdrawal','participation-history')),
    topic('withdrawal','Withdrawing Before the Deadline','Find the exact withdrawal deadline and confirm your decision.','Activities and Participation',('volunteer',),[
        'Open My Registrations and select the activity’s registration details.',
        'Read the exact withdrawal deadline shown in Philippine time. Each activity can have a different deadline.',
        'When withdrawal is available, review the confirmation and submit it. Withdrawal is direct and does not require a cancellation-approval request.',
        'After the deadline, read the closed-deadline explanation and contact the campus Coordinator if needed. Historical cancellation decisions remain read-only history.'
    ],('registrations',),('registration','getting-support'),('Refreshing or opening Help does not extend a withdrawal deadline.',)),
    topic('participation-history','Registration History and Attendance Evidence','Understand status, presence, completion, and unknown attendance.','Activities and Participation',('volunteer',),[
        'Open My Registrations and use search, status, campus, category, or date refinements to find an activity.',
        'Registration status, activity cancellation, schedule progress, and attendance evidence describe different things.',
        'Completed participation comes from recorded presence. After the configured activation date, eligible ended activities display missing confirmed attendance as Not Attended (System Default). Historical unrecorded attendance remains unknown.',
        'If recorded participation appears incorrect after an event ends, contact its campus Coordinator for the printed-report correction process.'
    ],('registrations',),('withdrawal','getting-support'),keywords='not attended excused unmarked completed'),
    topic('profile','Profile Interests and Skills','Keep recommendation preferences and account information current.','Account Help',('volunteer',),[
        'Open Profile to review your interests, skills, and preferred campus.',
        'Select the relevant options and save the section. Ordinary unfinished values can be restored from a saved draft.',
        'Use the dedicated account controls for supported name, password, and profile-image changes.',
        'Re-enter passwords when needed. Never rely on draft saving to retain secret fields.'
    ],('profile',),('recommendations','saved-drafts','campus')),
    topic('create-activity','Creating an Approved Activity','Start with a proposal and review each publication step.','Activity Management',('coordinator',),[
        'Start Create Activity by uploading the approved PDF or DOCX proposal. Documents are stored privately.',
        'Readable PSU-template proposals fill matching posting fields locally. Check capture results and complete missing posting details. Scanned or unreadable documents need manual entry; extraction does not verify approval or signatures.',
        'Complete future start/end times in Philippine time, location, category, required skills, SDGs, capacity, and optional cover.',
        'Complete Activity Details and Registration and Partners, then review and publish. Budget, team lists, implementation plans, risks, and other detailed proposal sections do not need to be entered again.',
        'Capacity controls volunteer registration places. The optional total participant target includes internal and external participants. The approved proposal stays staff-only.',
        'Earlier saved drafts retain their existing completion path. Use the Shorter Posting Form converts a saved draft without removing its existing input or attachment.'
    ],('create','drafts'),('audience','partners-moas','saved-drafts'),keywords='proposal extraction scanned cover image publish'),
    topic('audience','Departments and Activity Audiences','Choose whom to notify without restricting eligible registration.','Activity Management',('coordinator',),[
        'Enter the conducting department and participant type on the activity draft.',
        'Use the department checkbox panel to select multiple campus departments; search within the panel when needed.',
        'Audience choices guide descriptions and in-app notifications. They do not restrict otherwise eligible volunteers from registering.',
        'Review the selected audience before publication. Specific Volunteer targeting is not part of the current creation form.'
    ],('create',),('create-activity','partners-moas')),
    topic('partners-moas','Partner Agencies and MOAs','Manage contact records and select an applicable signed agreement.','Activity Management',('coordinator',),[
        'Open Partners to search campus agencies. Use Add Agency or Edit Agency Details for contact information.',
        'Open an agency, select Add MOA, and provide its reference, validity dates, and signed PDF/DOCX document.',
        'View MOA shows current validity separately from applicability to an activity. The MOA must cover the activity start date inclusively.',
        'From Registration and Partners, save before opening Partners. Use This Agency selects the primary agency for the activity; Use This MOA also selects its applicable signed agreement and returns to the draft.',
        'Choose Existing MOA, For Renewal, New Partnership, or No External Partner in the proposal. Activity-specific roles and duration stay with that activity. Draft agreements are private attachments and never count as signed MOAs.',
        'Choose one Primary Agency and any Additional Partner Agencies. The selected signed MOA and Expected Partner Participants apply to the primary agency only. Additional agencies are retained in your saved draft and published staff record.',
        'Add MOA uses the same date-picker presentation as activity creation, without time controls. Valid From and Valid Until remain inclusive calendar dates; historical and same-day agreements are allowed.',
        'Selecting an MOA does not publish the activity. Agreements and downloads remain private to authorized campus Coordinators.'
    ],('partners','create'),('create-activity','saved-drafts'),('MOA selection is optional. An agreement valid today may not cover a future activity date.',),keywords='agency contact validity signed document'),
    topic('attendance','Registrations, Attendance, and External Groups','Record evidence during the event and understand the end-time lock.','Activity Management',('coordinator',),[
        'Open Activities and choose Upcoming, Ongoing, or Past. Upcoming registration lists are separate from attendance records.',
        'During the event, open its attendance workspace. Record internal attendees and named external individuals; external groups support bulk entry.',
        'Internal Volunteers and External Volunteers open separate rosters. Save Attendance affects only the displayed page; save changes before searching, paging, or leaving. Attendance is not saved automatically.',
        'From External Attendance, open Add External Participants for multiline names or a UTF-8 CSV without a header. Group name and email are optional. A selected file takes precedence over typed names and must be selected again after a validation error.',
        'Choose Attended or Not Attended. All Attended marks only the displayed page; you can change individual statuses before Save Attendance. Unrecorded values and existing Excused records remain unchanged until explicitly updated. Excused is no longer available for new entries. System-default absence never creates recorded evidence or verified participation.',
        'Every attendance write path, including bulk actions and imports, locks at the scheduled end time.',
        'After the event ends, use the combined printed report and established correction process. Legacy activities without an end time are read-only for attendance.'
    ],('staff-activities',),('activity-status','reports','getting-support'),('Attendance entry is permitted only while the event is ongoing. Missing evidence is not recorded absence.',)),
    topic('activity-status','Activity Workspaces and Cancellation','Keep lifecycle, schedule, registration, and attendance separate.','Activity Management',('coordinator',),[
        'Open an activity workspace to reach its overview, registrations, attendance, documents/updates, and report.',
        'Approved/Cancelled is the lifecycle. Upcoming/Ongoing/Past describes its schedule. Attendance and registration have their own evidence and states.',
        'A campus Coordinator may cancel an eligible upcoming or ongoing activity with a recorded reason.',
        'Activity records remain permanent. Ended events direct you to reports and printed corrections rather than attendance editing.'
    ],('staff-activities',),('attendance','reports')),
    topic('overview','University and Campus Overview','Read headline measures within their stated scope.','Reports and Annual Plans',STAFF,[
        'When review management is enabled, Directors see Active Reviews and a category donut. Otherwise, the Overview shows generated Findings to Review. Directors start with conducted activities, verified attendees, campus annual achievement, and findings to review. Campus Accomplishments and Needs Attention lead the Overview; approved activities, all-time accounts, annual details, delivery and attendance charts remain below. Coordinators see their assigned campus.',
        'Approved activities, conducted activities, verified attendees, and their period comparisons use the selected scope. Volunteer accounts are an account total, not a period attendance count.',
        'Repeated attendance across activities is different from unique volunteer accounts. Read each metric’s explanation before comparing them.',
        'Activity Delivery shows conducted activities over time. Sex-Disaggregated Verified Attendance separates Female, Male, Prefer Not to Say, and Not Recorded, including PSU and external participants. Only recorded presence on confirmed/completed registrations at conducted approved activities counts.',
        'Directors review Campus Accomplishments on Overview. Compare Campuses opens the report comparison for all campuses using the same period and other non-campus filters. Open its dropdown to select campuses; Activity Delivery shows a separate line for each compared campus. Applying comparison replaces the top Campus choice, while applying Report Filters clears comparison selections. Expand Campus Details retains the AOP, pending evidence, and campus links.',
        'AOP achievement retains its reporting-year scope. Open campus details, Reports, or Needs Attention for the source records.'
    ],('overview','reports','follow-up'),('reports','annual-plans'),keywords='KPI metrics accounts attendance comparisons findings'),
    topic('finding-reviews','Finding Reviews and Completed Assessments','Record decisions without rewriting source evidence.','Reports and Annual Plans',STAFF,[
        'When review management is enabled, Directors use Active and Reviewed on Needs Attention. Generated findings remain Needs Review until a Director records an assessment or follow-up.',
        'Open Review to compare whole-activity or annual evidence. Participant filters in Reports do not create separate assessments. System-default absence is derived and remains distinct from recorded absence.',
        'Save Assessment retains active status. Notify Coordinator, Request Plan, Request Activity Plan, or Request Evidence appears only when the current finding supports corrective action. Follow-up Sent means a notification was created, not that it was read.',
        'Mark Reviewed and Close requires an assessment and closure reason. Closing never edits attendance, targets, annual evidence, or historical report totals. Completed assessments remain in Reviewed; a Director can explicitly reopen with a reason.',
        'Materially changed evidence that still triggers the rule returns to Active with Evidence Changed. The earlier assessment remains in history. An open finding that clears remains available for Director assessment and closure.',
        'Coordinators may read completed assessments for their own campus through Reviewed Recommendations. Active Director assessments stay private. Administration is part of the existing Director role; no new account role is introduced.'
    ],('follow-up',),('overview','attendance','reports'),keywords='review close reopen assessment active history recommendation evidence'),
    topic('reports','Report Filters, Records, and Exports','Choose a scope and export the matching filtered dataset.','Reports and Annual Plans',STAFF,[
        'Directors can open Activities → an activity → Documents to read the approved proposal and supporting evidence across campuses. Published proposals are also available near the top of Activity Overview. This view is read-only; uploads and announcements remain Coordinator actions.',
        'Open Reports and select activity delivery, annual achievement, historical records, or People Insights as appropriate.',
        'Choose the reporting year, period, activity delivery, and authorized campus scope. More Filters contains specialist refinements.',
        'Quarterly uses Quarter; Semi-Annual uses Half-Year; Custom Dates uses From/To. Reporting Year still scopes annual plans for All Records and Custom Dates.',
        'Activity Accomplishments separates Summary, Activity Records, and Participation Records. Open an activity’s combined report for its named roster and source details.',
        'Exports include all matching records, not only the visible page. Presentation tabs do not silently narrow export totals. Participant filters affect participant measures rather than unrelated activity/account totals.',
        'Recorded Sex filters PSU and external participants using their recorded response. Participant Affiliation applies to PSU accounts and excludes external participants. The verified sex breakdown uses the same scoped evidence on screen and in PDF, Excel, and CSV exports.',
        'Summary shows Campus Comparison. Directors select campuses in its scrollable checkbox list, choose include or exclude, then Apply Comparison. The whole report updates and returns to that section. The Campus dropdown above still applies; choose All Campuses there to avoid a primary-campus restriction.',
        'The verified attendance donut shows shares of the scoped total. The table retains all four recorded-sex groups, exact counts, and PSU/external values, including zero groups. Downloaded PDF and Excel chart formats remain separate from the on-screen donut.'
    ],('reports',),('overview','annual-plans','navigation'),('Unknown evidence and incomplete recording must remain pending or unavailable, not invented zeroes.',),keywords='PDF Excel CSV quarter half-year department SDG sex affiliation'),
    topic('annual-plans','AOP Goals and Campus Commitments','Track Director goals, campus commitments, and completed activities.','Reports and AOP Goals',STAFF,[
        'Directors post a goal with its AOP year, activity target, Start Date, and End Date. Both dates must be within the selected year.',
        'Coordinators submit a campus commitment. It becomes the campus AOP goal immediately, without Director approval. Drafts do not change active commitments.',
        'Targets are not limits. Campuses may commit to and complete more activities than the Director target.',
        'Link approved activities explicitly. Their entire schedule must fall within the goal period in Philippine time. Credit begins when the activity ends, independently of attendance completeness.',
        'Keep attendance and reports complete using the existing recording window. Use AOP History for read-only historical evidence; historical records are separate from the new workflow.'
    ],('annual-plans','aop'),('reports','saved-drafts'),keywords='AOP commitment period start end completed activities'),
    topic('follow-up','Needs Attention and Campus Follow-Up','Use evidence and the relevant next action.','Reports and Annual Plans',STAFF,[
        'Open Needs Attention to review findings with their campus, period, and supporting records.',
        'For ongoing events, follow the authorized attendance action. For ended events, use reports and printed corrections.',
        'Needs Attention shows activity start and end times in Philippine time. Use Review Category to filter findings. Directors can use Remind Coordinator for ongoing attendance findings; equivalent unread reminders are not resent. The finding title opens its assessment and history when review management is enabled.',
        'Check the underlying evidence before taking action; an alert does not make missing evidence a verified result.'
    ],('follow-up','overview'),('attendance','reports')),
    topic('accounts','Managing User Accounts','Review records and manage access with protected actions.','Management',('director',),[
        'Open Management → User Accounts. Search the active/deactivated lists and open View Record.',
        'Use Edit Account for identity, role, campus, and affiliation. Coordinator accounts require a valid assigned campus.',
        'Use the separate Reset Password screen when authorized. Resetting a password revokes the target account’s existing sessions and recovery tokens.',
        'Your own account cannot be deactivated or deleted, and the final active Director cannot be deactivated or demoted.',
        'An inactive account becomes eligible for deletion after 30 days. Review the record and confirmation carefully. Export All Accounts ignores list filters and excludes passwords.'
    ],('accounts','management'),('imports','saved-drafts'),keywords='deactivate reactivate delete password reset role'),
    topic('imports','Importing Users, Historical Activities, and Annual Plans','Upload, review, then explicitly confirm the complete file.','Management',('director',),[
        'Open Management → Import Data and choose the data type. Use its existing institutional CSV format; users have a downloadable template.',
        'Validate the upload and review the source rows and importer message. Preview does not create records.',
        'Resume a staged preview in the same authenticated browser session, choose another file, or discard it. Missing or expired session state requires reupload.',
        'Confirm Import revalidates the complete staged file, including rows on other pages. Annual importer record counts include entities and are separate from CSV row counts.',
        'Review the reported outcome and open the corresponding records. Passwords are privately hashed and never shown in user previews.'
    ],('imports',),('accounts','saved-drafts'),('Confirmation changes institutional data. Review validation errors before retrying; do not assume an upload alone imported anything.',),keywords='CSV staged preview validation rows confirm discard'),
]

ACTIONS = {
    'signup': ('Create an Account','auth.interests',('public',),{}),
    'signin': ('Sign In','auth.login',('public',),{}),
    'forgot': ('Forgot Password','auth.forgot_password',EVERYONE,{}),
    'activities': ('Find Activities','events.opportunities',('public','volunteer'),{}),
    'profile': ('Open Profile','volunteer.profile_page',('volunteer',),{}),
    'registrations': ('My Registrations','workspace.registrations',('volunteer',),{}),
    'drafts': ('Saved Drafts','workspace.draft_list',SIGNED,{}),
    'notifications': ('Notifications','notifications.list_notifications',SIGNED,{}),
    'create': ('Create Activity','workspace.create_activity',('coordinator',),{'step':1}),
    'partners': ('Partner Agencies','workspace.partners',('coordinator',),{}),
    'staff-activities': ('Activities','workspace.activities',STAFF,{}),
    'overview': ('Overview','workspace.overview',STAFF,{}),
    'reports': ('Reports','workspace.reports',STAFF,{}),
    'annual-plans': ('AOP Goals','goals.workspace',STAFF,{}),
    'aop': ('Annual Plan Summary','workspace.aop',STAFF,{}),
    'follow-up': ('Needs Attention','workspace.follow_up',STAFF,{}),
    'accounts': ('User Accounts','admin.admin_dash',('director',),{}),
    'management': ('Management','workspace.management',('director',),{}),
    'catalogue': ('Skills and Activity Categories','catalogue.index',('director',),{}),
    'imports': ('Import Data','workspace.imports',('director',),{}),
}


def role():
    if not current_user.is_authenticated:
        return 'public'
    return 'director' if current_user.role == 'admin' else current_user.role


def contextual_help(label, fallback=''):
    if fallback and fallback != url_for('help_page'):
        return fallback
    subjects = {
        'interest matching':'recommendations', 'proposal extraction':'create-activity',
        'draft saving':'saved-drafts', 'audience targeting':'audience', 'moa validity':'partners-moas',
        'attendance locking':'attendance', 'import preview':'imports', 'report filters':'reports',
        'reporting scope':'reports', 'participation measures':'reports', 'annual scope':'annual-plans',
        'annual achievement':'annual-plans', 'annual obligations':'annual-plans', 'aop achievement':'annual-plans',
        'campus obligations':'annual-plans', 'targets and verified actuals':'annual-plans', 'verified achievement':'annual-plans',
        'approved activities':'overview', 'conducted activities':'overview', 'volunteer accounts':'overview',
        'verified attendees':'overview', 'aop targets achieved':'annual-plans',
        'capacity, targets, and presence':'attendance',
    }
    slug = subjects.get(str(label).casefold())
    if slug and any(item['slug'] == slug and role() in item['audience'] for item in TOPICS):
        return url_for('help_page',slug=slug)
    return fallback


def action_links(keys):
    links = []
    for key in keys:
        if key == 'dashboard':
            if role() in SIGNED:
                links.append(dict(label='Open Dashboard',url=url_for('events.volunteer_dash' if role() == 'volunteer' else 'workspace.overview')))
        else:
            label, endpoint, audience, values = ACTIONS[key]
            if role() in audience:
                links.append(dict(label=label,url=url_for(endpoint,**values)))
    return links


def help_context(slug=None):
    query = request.args.get('q','').strip()[:200]
    visible = [item for item in TOPICS if role() in item['audience']]
    selected = next((item for item in visible if item['slug'] == slug),None)
    if slug and selected is None:
        abort(404)
    matches = [item for item in visible if not query or query.casefold() in ' '.join([
        item['title'],item['summary'],item['keywords'],*item['steps'],*item['warnings']]).casefold()]
    groups = {}
    for item in matches:
        groups.setdefault(item['group'],[]).append(item)
    priorities = {
        'public': ('Getting Started','Account Help','Troubleshooting'),
        'volunteer': ('Activities and Participation','Account Help','Getting Started','Troubleshooting'),
        'coordinator': ('Activity Management','Reports and Annual Plans','Account Help','Getting Started','Troubleshooting'),
        'director': ('Reports and Annual Plans','Management','Account Help','Getting Started','Troubleshooting'),
    }
    groups = {group:groups[group] for group in priorities[role()] if group in groups}
    dashboard_url = url_for('events.volunteer_dash' if role() == 'volunteer' else 'workspace.overview',tour=1) if role() in SIGNED else None
    quick = {'public':('signup','signin','forgot'),'volunteer':('activities','registrations','profile'),
             'coordinator':('create','staff-activities','partners'),'director':('reports','accounts','imports')}[role()]
    return dict(help_role=role(),help_query=query,help_groups=groups,help_total=len(matches),
        article=selected,help_actions=action_links(selected['actions'] if selected else quick),
        related_topics=[item for item in visible if selected and item['slug'] in selected['related']],
        dashboard_url=dashboard_url)
