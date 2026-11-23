"""Completed activity contributions remain distinct from campus commitments met."""
from datetime import date, datetime
from types import SimpleNamespace as NS

import pytest
from app.models import db
from app.models.event import Event, Campus
from app.models.annual_plan import AnnualTarget, AnnualActivityMapping
from app.report_demo import seed_aop_commitments
from app.services.staff_overview import aop_achievement
from tests.test_workspace_overhaul import app, client, actors, sign_in
from tests.test_ui_reimagining import screen
from tests.html_helpers import parse_html


def test_pure_aggregation_preserves_goal_credits_and_scoped_denominator():
    goals=[NS(id=i,target_value=5,start_date=date(2025,1,1),end_date=date(2025,12,31)) for i in (1,2)]
    event=NS(id=1,campus_id=1,date=datetime(2025,6,1),end_date=datetime(2025,6,2),lifecycle_status='approved')
    mapping=NS(event_id=1,event=event)
    children=[NS(director_target_id=i,campus_id=1,target_value=7,activity_mappings=[mapping,mapping]) for i in (1,2)]
    children.append(NS(director_target_id=1,campus_id=2,target_value=6,activity_mappings=[]))
    result=aop_achievement(dict(campus_chart=[dict(id=1),dict(id=3)],
        campuses=[NS(id=1,name='Submitted'),NS(id=3,name='No Commitment')]),(goals,children))
    assert (result['target'],result['committed'],result['completed'],result['rate'])==(10,14,2,20)
    assert result['campuses']==[
        dict(id=3,name='No Commitment',submitted=False,committed=0,completed=0),
        dict(id=1,name='Submitted',submitted=True,committed=14,completed=2)]
    assert aop_achievement(dict(campus_chart=[]),(goals,children))['rate']==0
    assert aop_achievement(dict(campus_chart=[]),([],[]))['rate'] is None


@pytest.mark.parametrize('completed,rate',[(0,'0'),(4,'40'),(10,'100'),(13,'130')])
def test_director_hero_uses_ended_activities_and_preserves_scope(client,app,actors,completed,rate):
    events=[]
    for index in range(completed):
        event=Event(title=f'Completed AOP {index}',description='Synthetic',campus_id=1 if index<7 else 2,
                    date=datetime(2025,6,1,8),end_date=datetime(2025,6,1,9),lifecycle_status='approved')
        db.session.add(event);events.append(event)
    db.session.flush()
    seed_aop_commitments(2025,Campus.query.order_by(Campus.id).all(),events)
    goal=AnnualTarget.query.filter_by(workflow_kind='director_goal').one()
    children=AnnualTarget.query.filter_by(workflow_kind='campus_commitment').all()
    for child in children:
        child.target_value=7 if child.campus_id==1 else 6
    child=next(child for child in children if child.campus_id==1)
    for status,start,end in [('cancelled',datetime(2025,6,1),datetime(2025,6,2)),
                             ('approved',datetime(2024,12,31),datetime(2025,1,1)),
                             ('approved',datetime(2025,6,1),None)]:
        event=Event(title='Ineligible AOP',description='Synthetic',campus_id=1,
                    date=start,end_date=end,lifecycle_status=status)
        db.session.add(event);db.session.flush()
        db.session.add(AnnualActivityMapping(target_id=child.id,event_id=event.id))
    db.session.commit()
    sign_in(client,actors,'director')
    response,context=screen(client,app,'/workspace/overview?year=2025&period=annual')
    hero=parse_html(response.text).one('section',**{'class':'director-achievement'})
    assert rate+'% AOP Goal Achievement Rate' in hero.text
    assert context['aop_achievement']['completed']==completed
    assert context['aop_achievement']['target']==10
    assert context['aop_achievement']['committed']==13
    rows=context['aop_achievement']['campuses']
    assert sum(row['completed'] for row in rows)==completed
    assert sum(row['committed'] for row in rows)==13
    assert len(rows)==9
    assert ('exceed the Director AOP target of 10 by 3.' in hero.text)==(completed==13)
    assert response.text.index('class="staff-scope"')<response.text.index('class="director-achievement"')
    assert len(parse_html(response.text).all('h2',id='annual-title'))==1
    for query in ('&period=quarterly&segment=1&sex=female','&activity_name=NoMatch'):
        _,filtered=screen(client,app,'/workspace/overview?year=2025'+query)
        assert filtered['aop_achievement']==context['aop_achievement']
    _,campus=screen(client,app,'/workspace/overview?year=2025&campus_id=1')
    assert campus['aop_achievement']['completed']==min(completed,7)
    assert campus['aop_achievement']['committed']==7 and campus['aop_achievement']['target']==10
    _,included=screen(client,app,'/workspace/overview?year=2025&campus=1&campus_mode=include')
    assert included['aop_achievement']==campus['aop_achievement']
    _,excluded=screen(client,app,'/workspace/overview?year=2025&campus=1&campus_mode=exclude')
    assert excluded['aop_achievement']['completed']==max(completed-7,0)
    assert excluded['aop_achievement']['target']==10
    assert goal.target_value==10


@pytest.mark.parametrize('path',['/workspace/management','/settings'])
def test_director_retains_merged_administration_access(client,actors,path):
    sign_in(client,actors,'director')
    response=client.get(path)
    assert response.status_code==200
