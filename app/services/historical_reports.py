"""Read-only historical record scopes and matching exports."""
import csv
import io
from xml.sax.saxutils import escape

from flask import abort, send_file
from sqlalchemy import func, or_
from app.models import db
from app.models.event import HistoricalActivity, Campus
from app.reports import csv_safe


def historical_scope(args,user):
    query = HistoricalActivity.query
    campus = user.campus_id if user.role == 'coordinator' else args.get('campus_id',type=int)
    if user.role == 'coordinator' and not campus:
        abort(403)
    if campus:
        query = query.filter_by(campus_id=campus)
    types = [r[0] for r in query.with_entities(HistoricalActivity.activity_type).filter(
        HistoricalActivity.activity_type.isnot(None)).distinct().order_by(HistoricalActivity.activity_type)]
    year = args.get('year',type=int)
    start, end = args.get('start_year',type=int),args.get('end_year',type=int)
    if any(args.get(k) and args.get(k,type=int) is None for k in ('year','start_year','end_year')):
        abort(400,description='Enter valid historical reporting years.')
    if any(y is not None and not 1900 <= y <= 2100 for y in (year,start,end)) or start and end and start > end:
        abort(400,description='Choose a historical year range from 1900 to 2100, with end after start.')
    if year:
        query = query.filter_by(year_conducted=year)
    if start:
        query = query.filter(HistoricalActivity.year_conducted >= start)
    if end:
        query = query.filter(HistoricalActivity.year_conducted <= end)
    if args.get('activity_type'):
        query = query.filter_by(activity_type=args['activity_type'])
    search = args.get('q','').strip()[:200]
    if search:
        query = query.filter(or_(HistoricalActivity.title.icontains(search,autoescape=True),
                                 HistoricalActivity.unit_name.icontains(search,autoescape=True)))
    chart = [dict(name=name,count=count,known=known,missing=records-known) for name,count,known,records in query.with_entities(
        HistoricalActivity.unit_name,func.sum(HistoricalActivity.volunteer_count),func.count(HistoricalActivity.volunteer_count),
        func.count(HistoricalActivity.id)).group_by(HistoricalActivity.unit_name).order_by(HistoricalActivity.unit_name)]
    return query.order_by(HistoricalActivity.year_conducted.desc(),HistoricalActivity.title,HistoricalActivity.id),chart,types


def export_historical(format,args,user):
    if format not in ('csv','xlsx','pdf'):
        abort(404)
    query, chart, _ = historical_scope(args,user)
    headers = ['Activity','Campus / unit','Year','Activity type','Reported participations','Source document','Source page']
    values = [[r.title,r.unit_name,r.year_conducted or 'Unknown',r.activity_type or 'Not recorded',
               r.volunteer_count if r.volunteer_count is not None else 'Unknown',r.source_document,r.source_page] for r in query]
    campus_id = user.campus_id if user.role == 'coordinator' else args.get('campus_id',type=int)
    campus = db.session.get(Campus,campus_id) if campus_id else None
    scope = 'Campus scope: ' + (campus.name if campus else 'Unavailable campus' if campus_id else 'All campuses')
    scope += ''.join('; ' + label + ': ' + args[key] for key,label in [('q','Search'),('year','Year'),
        ('start_year','From year'),('end_year','To year'),('activity_type','Activity type')] if args.get(key))
    output = io.BytesIO()
    if format == 'csv':
        stream = io.StringIO(); writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([[csv_safe(v) for v in row] for row in values])
        output.write(stream.getvalue().encode('utf-8-sig'))
    elif format == 'xlsx':
        from openpyxl import Workbook
        from openpyxl.chart import BarChart, Reference
        book=Workbook(); sheet=book.active; sheet.title='Historical records'; sheet.append(headers)
        for row in values:
            sheet.append([csv_safe(v) for v in row])
        sheet.freeze_panes='A2'
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width=28
        summary=book.create_sheet('Campus comparison'); summary.append(['Campus / unit','Known reported participations','Records with missing counts'])
        for row in chart:
            summary.append([csv_safe(row['name']),row['count'],row['missing']])
        if chart:
            graph=BarChart(); graph.title='Historical reported participations'; graph.add_data(Reference(summary,min_col=2,max_col=2,min_row=1,max_row=summary.max_row),titles_from_data=True)
            graph.set_categories(Reference(summary,min_col=1,min_row=2,max_row=summary.max_row)); summary.add_chart(graph,'E2')
        notes=book.create_sheet('Scope'); notes.append([csv_safe(scope)]); notes.append(['Aggregate participations are not unique accounts. Missing counts remain unknown.'])
        book.save(output)
    else:
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image
        from reportlab.lib.pagesizes import A4,landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from matplotlib.figure import Figure
        styles=getSampleStyleSheet()
        content=[Paragraph('PSU Volunteer Hub · Historical source records',styles['Title']),Paragraph(escape(scope),styles['Normal']),
                 Paragraph('Reported participations are aggregate counts, not unique accounts. Missing values remain unknown.',styles['Normal']),Spacer(1,12)]
        known=[r for r in chart if r['count'] is not None]
        if known:
            fig=Figure(figsize=(9,max(2,len(known)*.3)),layout='constrained'); ax=fig.subplots()
            ax.barh([r['name'] for r in known],[r['count'] for r in known],color='#00408b'); ax.set_xlabel('Known reported participations')
            image=io.BytesIO(); fig.savefig(image,format='png',dpi=100); image.seek(0)
            content.append(Image(image,width=650,height=min(260,max(140,len(known)*16))))
        table=Table([[Paragraph(escape(str(v)),styles['Normal']) for v in row] for row in [headers,*values]],repeatRows=1,colWidths=[190,85,45,65,65,210,45])
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8)])); content.append(table)
        SimpleDocTemplate(output,pagesize=landscape(A4),leftMargin=24,rightMargin=24).build(content)
    output.seek(0)
    return send_file(output,as_attachment=True,download_name='psu-historical.'+format,
        mimetype={'csv':'text/csv','xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','pdf':'application/pdf'}[format])
