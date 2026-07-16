"""
Coordinator Routes for PSU Volunteer Hub
==========================================
Manages event creation, attendance tracking, and coordinator dashboard.
"""
import os
import uuid
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import login_required, current_user
from app.models import db
from app.models.event import Event, Registration, Attendance, Campus, Milestone
from app.utils.decorators import role_required
from datetime import datetime

coordinator_bp = Blueprint('coordinator', __name__, url_prefix='')


@coordinator_bp.route('/coordinator_dash')
@login_required
@role_required('coordinator')
def coordinator_dash():
    status = request.args.get('status', 'upcoming')
    events = Event.query.filter_by(campus_id=current_user.campus_id)
    if status == 'upcoming':
        events = events.filter(Event.date >= datetime.now())
    elif status == 'past':
        events = events.filter(Event.date < datetime.now())
    events = events.order_by(Event.date.desc()).all()
    upcoming_count = sum(1 for e in events if e.date >= datetime.now())
    event_ids = [e.id for e in events]
    total_volunteers = db.session.query(Registration.user_id).filter(Registration.event_id.in_(event_ids)).distinct().count() if event_ids else 0
    total_regs = db.session.query(Registration).filter(Registration.event_id.in_(event_ids)).count() if event_ids else 0
    confirmed_regs = db.session.query(Registration).filter(Registration.event_id.in_(event_ids), Registration.status.in_(['confirmed', 'completed'])).count() if event_ids else 0
    attendance_rate = round((confirmed_regs / total_regs * 100), 1) if total_regs > 0 else 0
    recent_activities = Registration.query.filter(Registration.event_id.in_(event_ids)).order_by(Registration.registered_at.desc()).limit(5).all() if event_ids else []
    return render_template('Coordinator_dash.html',
                           events=events,
                           upcoming_count=upcoming_count,
                           total_volunteers=total_volunteers,
                           attendance_rate=attendance_rate,
                           recent_activities=recent_activities,
                           selected_status=status)


@coordinator_bp.route('/create_activity', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def create_activity():
    campuses = Campus.query.all()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        date_str = request.form.get('date', '').strip()
        location = request.form.get('location', '').strip()
        required_skills = request.form.get('required_skills', '').strip()
        category = request.form.get('category', 'General').strip()
        slots = request.form.get('slots', 0, type=int)
        campus_id = request.form.get('campus_id', current_user.campus_id, type=int)
        if not title or not description or not date_str:
            flash('Title, description, and date are required.', 'error')
            return render_template('create_act_scrn1.html', campuses=campuses)
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            flash('Invalid date format. Use YYYY-MM-DD.', 'error')
            return render_template('create_act_scrn1.html', campuses=campuses)
        event = Event(title=title, description=description, date=date, category=category, location=location, required_skills=required_skills, slots=slots, campus_id=campus_id)
        db.session.add(event)
        db.session.commit()
        flash('Activity created successfully!', 'success')
        return redirect(url_for('coordinator.coordinator_dash'))
    return render_template('create_act_scrn1.html', campuses=campuses)


@coordinator_bp.route('/attendance', methods=['GET', 'POST'])
@login_required
@role_required('coordinator')
def attendance():
    events = Event.query.filter_by(campus_id=current_user.campus_id).order_by(Event.date.desc()).all()
    selected_event_id = request.args.get('event_id', type=int)
    registrations = []
    if selected_event_id:
        registrations = Registration.query.filter_by(event_id=selected_event_id).all()
    if request.method == 'POST':
        event_id = request.form.get('event_id', type=int)
        reg_ids = request.form.getlist('registration_id')
        statuses = request.form.getlist('status')
        hours_list = request.form.getlist('hours_completed')
        for i, reg_id in enumerate(reg_ids):
            reg = Registration.query.get(int(reg_id))
            if reg:
                status = statuses[i] if i < len(statuses) else 'present'
                hour_val = float(hours_list[i]) if i < len(hours_list) else 0.0
                existing = Attendance.query.filter_by(registration_id=reg.id).first()
                if existing:
                    existing.status = status
                    existing.hours_completed = hour_val
                else:
                    db.session.add(Attendance(registration_id=reg.id, user_id=reg.user_id, event_id=reg.event_id, status=status, hours_completed=hour_val))
        db.session.commit()
        flash('Attendance updated successfully!', 'success')
        return redirect(url_for('coordinator.attendance', event_id=event_id))
    return render_template('attendance_MnGmt.html', events=events, registrations=registrations)


@coordinator_bp.route('/events/<int:event_id>/milestones', methods=['POST'])
@login_required
@role_required('coordinator')
def upload_milestone(event_id):
    event = Event.query.get_or_404(event_id)
    if 'file' not in request.files:
        flash('No file selected.', 'error')
        return redirect(url_for('coordinator.coordinator_dash'))
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'error')
        return redirect(url_for('coordinator.coordinator_dash'))
    category = request.form.get('category', 'photo')
    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'milestones')
    os.makedirs(upload_dir, exist_ok=True)
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    filename = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    milestone = Milestone(event_id=event.id, filename=file.filename, upload_path=f'uploads/milestones/{filename}', category=category)
    db.session.add(milestone)
    db.session.commit()
    flash('Milestone uploaded successfully!', 'success')
    return redirect(url_for('coordinator.coordinator_dash'))


@coordinator_bp.route('/reports/events.csv')
@login_required
@role_required('coordinator')
def export_events_csv():
    events = Event.query.filter_by(campus_id=current_user.campus_id).order_by(Event.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Date', 'Location', 'Category', 'Slots', 'Registered'])
    for e in events:
        reg_count = Registration.query.filter_by(event_id=e.id).count()
        writer.writerow([e.title, e.date.strftime('%Y-%m-%d'), e.location, e.category, e.slots, reg_count])
    return Response(output.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=events.csv'})
