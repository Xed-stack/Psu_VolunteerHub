"""Bounded PSU proposal records and conservative, local template capture."""
import io
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from xml.etree import ElementTree as ET

MAX_RECORD_BYTES = 256 * 1024
BENEFICIARIES = ['Farmers', 'Fisherfolks', 'Landless Rural Workers', 'Workers in Formal Labor / Migrant Workers',
    'Workers in Informal Sector', 'Urban Poor', 'Victims of Disasters and Calamities', 'Out-of-School Youth',
    'Women', 'Youth and Students (5–19 years old)', 'Elderly', 'Persons with Disabilities',
    'Indigenous Peoples / Cultural Communities', 'Other Stakeholders']
VOLUNTEERS = ['Teaching Staff', 'Non-Teaching Staff', 'Students', 'Other Stakeholders']
ENGAGEMENT = ['Health & Well-being', 'Lifelong Learning', 'Gender Equality', 'Technology Development',
    'Economics, Business, and Marketing', 'Computing, Data Banking, and SMART Analytics',
    'Nature, Disaster, and Environment Management', 'Open and Flexible Education',
    'Organization, Industry and Community Development', 'Governance and Policy']
TYPES = ['Research-based Extension Program/Project', 'Research-informed Outreach Program/Project',
    'Outreach', 'Volunteerism', 'Fundraising', 'Donation Drive/Relief Activity']
OUTCOMES = ['Increased Access to Services', 'Improved Skills & Knowledge', 'Distribution of Materials or Resources',
    'Enhanced Infrastructure or Facilities', 'Documented Participation', 'Partnerships & Linkages Formed',
    'Empowered Communities', 'Sustained Volunteer Engagement', 'Strengthened Social Cohesion',
    'Positive Behavioral Change', 'Increased Awareness & Advocacy', 'Replication of Good Practices',
    'Contribution to Sustainable Development Goals (SDGs)']
SCALARS = {
    'implementing_unit': 'Implementing Unit / Degree Program', 'rationale': 'Rationale',
    'general_objectives': 'General Objectives', 'specific_objectives': 'Specific Objectives',
    'methodology': 'Methodology', 'beneficiary_count': 'Estimated Number of Beneficiaries',
    'beneficiary_other': 'Other Beneficiaries', 'volunteer_count': 'Estimated Number of Volunteers',
    'volunteer_other': 'Other Volunteers', 'budget_na': 'Budget Not Applicable', 'budget_reason': 'Budget Explanation',
    'evaluation': 'Monitoring and Evaluation', 'sustainability': 'Sustainability / Replicability Plan',
    'conclusion': 'Conclusion', 'partnership_status': 'Partnership Status', 'agency_id': 'Primary Agency',
    'psu_roles': 'Roles and Responsibilities of PSU', 'partner_roles': 'Roles and Responsibilities of Partner',
    'partnership_duration': 'Duration of Partnership', 'partnership_reason': 'Partnership Explanation',
    'prepared_by': 'Prepared By', 'noted_by': 'Noted By', 'recommending_by': 'Recommending Approval',
    'approved_by': 'Approved By', 'outcomes_notes': 'Expected Outcomes Details',
}
CHOICES = {'beneficiary_groups': BENEFICIARIES, 'volunteer_groups': VOLUNTEERS,
           'engagement_areas': ENGAGEMENT, 'activity_types': TYPES, 'outcomes': OUTCOMES}
TABLES = {
    'team': ('Project Leader and Members', [('name','Name'),('designation','Designation'),('campus','Campus'),('role','Leader / Member')]),
    'implementation': ('Implementation Plan', [('activity','Activity'),('people','Persons Involved'),('timeline','Timeline'),('output','Expected Output')]),
    'budget': ('Detailed Budget Breakdown', [('item','Item / Description'),('unit','Unit of Measure'),('quantity','Quantity'),('unit_cost','Unit Cost (PHP)'),('classification','Expense Classification'),('source','Source of Funds')]),
    'risks': ('Risk Management and Contingency Plan', [('risk','Identified Risk'),('impact','Likelihood / Impact'),('mitigation','Mitigation / Contingency Strategy')]),
}
GROUPS = [
    ('identity','Basic Information',['implementing_unit','activity_types','team']),
    ('purpose','Rationale and Objectives',['rationale','general_objectives','specific_objectives','methodology']),
    ('delivery','Implementation Plan',['implementation']),
    ('budget','Budget',['budget_na','budget_reason','budget']),
    ('outcomes','Outcomes and Follow-through',['outcomes','outcomes_notes','evaluation','sustainability','conclusion']),
    ('risks','Risk Management',['risks']),
    ('signatories','Recorded Signatories',['prepared_by','noted_by','recommending_by','approved_by']),
]
PARTICIPATION = [('beneficiaries','Target Beneficiaries',['beneficiary_count','beneficiary_groups','beneficiary_other']),
    ('volunteers','Volunteer Participation',['volunteer_count','volunteer_groups','volunteer_other','engagement_areas'])]
REQUIRED = ['implementing_unit','rationale','general_objectives','specific_objectives','methodology',
            'evaluation','sustainability','conclusion','beneficiary_count','volunteer_count']


def normalize_record(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError) as exc:
            raise ValueError('The proposal record could not be read. Reload the saved draft and try again.') from exc
    if not isinstance(value, dict) or len(json.dumps(value).encode()) > MAX_RECORD_BYTES:
        raise ValueError('Keep the proposal record within 256 KiB.')
    if set(value) - (SCALARS.keys() | CHOICES.keys() | TABLES.keys()):
        raise ValueError('The proposal contains an unsupported field.')
    result = {}
    for key, item in value.items():
        if key in SCALARS:
            if not isinstance(item, str) or len(item) > 10000:
                raise ValueError('Use 10,000 characters or fewer in each proposal field.')
            result[key] = item.strip()
        elif key in CHOICES:
            if not isinstance(item, list) or any(not isinstance(v,str) or v not in CHOICES[key] for v in item):
                raise ValueError('Choose available proposal options.')
            result[key] = list(dict.fromkeys(item))
        else:
            columns = {column for column, _ in TABLES[key][1]}
            if not isinstance(item,list) or len(item) > 50:
                raise ValueError('Use 50 rows or fewer in each proposal table.')
            rows = []
            for row in item:
                if not isinstance(row,dict) or set(row)-columns or any(not isinstance(v,str) or len(v)>10000 for v in row.values()):
                    raise ValueError('Check the proposal table values.')
                clean = {column: row.get(column,'').strip() for column in columns}
                if any(clean.values()):
                    rows.append(clean)
            result[key] = rows
    return result


def record_from_form(form, previous, remove=None):
    result = dict(previous)
    for key in SCALARS:
        if 'pr.'+key in form:
            result[key] = form['pr.'+key]
    for key in CHOICES:
        if 'pr.present.'+key in form:
            result[key] = form.getlist('pr.'+key)
    for key, (_, columns) in TABLES.items():
        if 'pr.present.'+key in form:
            values = [form.getlist('pr.'+key+'.'+column) for column,_ in columns]
            if len({len(v) for v in values}) > 1:
                raise ValueError('A proposal table has incomplete columns. Reload and try again.')
            result[key] = [dict(zip([c for c,_ in columns], row)) for index,row in enumerate(zip(*values))
                           if remove != (key,index)]
    return normalize_record(result)


def budget_totals(record):
    total = Decimal('0.00')
    lines = []
    for row in record.get('budget',[]):
        try:
            quantity, cost = Decimal(row.get('quantity','')), Decimal(row.get('unit_cost',''))
            if not quantity.is_finite() or not cost.is_finite() or quantity <= 0 or cost < 0 or quantity > Decimal('1000000000') or cost > Decimal('1000000000'):
                raise InvalidOperation
            if quantity.as_tuple().exponent < -3 or cost.as_tuple().exponent < -2:
                raise InvalidOperation
            line = (quantity*cost).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError):
            raise ValueError('Budget quantities must be positive (up to 3 decimal places); unit costs must be non-negative PHP amounts (up to 2 decimal places).') from None
        lines.append(format(line,'.2f'))
        total += line
    return lines, format(total,'.2f')


def validate_record(record):
    errors = {}
    if record.get('budget_na') not in ('yes','no'):
        errors['budget_na'] = 'Choose whether a budget applies.'
    for key in REQUIRED:
        if not record.get(key):
            errors[key] = 'Complete '+SCALARS[key]+'.'
    for key in ('beneficiary_count','volunteer_count'):
        value = record.get(key,'')
        if value and (not re.fullmatch(r'\d{1,9}',value)):
            errors[key] = 'Enter a whole number of zero or more.'
    for key in CHOICES:
        if not record.get(key):
            errors[key] = 'Select at least one option.'
    for key, (_, columns) in TABLES.items():
        if key == 'budget' and record.get('budget_na') == 'yes':
            if not record.get('budget_reason'):
                errors['budget_reason'] = 'Explain why no budget applies.'
            if record.get('budget'):
                errors['budget'] = 'Remove budget rows or choose Budget Applies.'
            continue
        rows = record.get(key,[])
        if not rows or any(any(not row.get(c) for c,_ in columns) for row in rows):
            errors[key] = 'Complete at least one row and every column, or remove incomplete rows.'
    team = record.get('team',[])
    if team and (sum(row.get('role','').lower()=='leader' for row in team)!=1 or any(row.get('role','').lower() not in ('leader','member') for row in team)):
        errors['team'] = 'Choose exactly one Leader; other team rows must be Member.'
    for group, other in [('beneficiary_groups','beneficiary_other'),('volunteer_groups','volunteer_other')]:
        if 'Other Stakeholders' in record.get(group,[]) and not record.get(other):
            errors[other] = 'Specify the other stakeholders.'
    try:
        budget_totals(record)
    except ValueError as exc:
        errors['budget'] = str(exc)
    status = record.get('partnership_status','')
    if status not in ('none','existing','renewal','new'):
        errors['partnership_status'] = 'Choose a partnership status.'
    elif status=='none':
        if not record.get('partnership_reason'):
            errors['partnership_reason'] = 'Explain why no external partnership applies.'
    else:
        for key in ('agency_id','psu_roles','partner_roles','partnership_duration'):
            if not record.get(key):
                errors[key] = 'Complete '+SCALARS[key]+'.'
    return errors


def _usable(text):
    text = re.sub(r'[_\u2026]{2,}', '', text).strip(' :\t\n')
    if not text or text.startswith(('(', '[Name', '[Designation', '[Signature')):
        return ''
    return text


def _paragraph_text(node):
    local=node.tag.rsplit('}',1)[-1]
    if local=='t':return node.text or ''
    if local=='sdtPr':return ''
    if local=='sdt':
        checked=next((child for child in node.iter() if child.tag.rsplit('}',1)[-1]=='checked'),None)
        content=''.join(_paragraph_text(child) for child in node)
        if checked is not None:
            value=next(iter(checked.attrib.values()),'0')
            mark='☒' if value.lower() in ('1','true','on') else '☐'
            content=re.sub(r'[☐☑☒□■]', '',content).strip()
            return mark+' '+content
        return content
    return ''.join(_paragraph_text(child) for child in node)


def capture_proposal(content, filename):
    """Capture only identifiable values; leave ambiguous layout for manual review."""
    pages, tables = [], []
    try:
        if filename.lower().endswith('.docx'):
            ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                info=archive.getinfo('word/document.xml')
                if info.file_size > 5*1024*1024:
                    raise ValueError('The document text is too large.')
                root=ET.fromstring(archive.read(info))
            # One paragraph once; checkbox XML is never inferred from an empty box.
            text='\n'.join(_paragraph_text(p) for p in root.findall('.//w:p',ns))
            pages=[text]
            for table in root.findall('.//w:tbl',ns):
                tables.append([[' '.join(_paragraph_text(p) for p in cell.findall('.//w:p',ns)) for cell in row.findall('w:tc',ns)] for row in table.findall('w:tr',ns)])
        else:
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(content))
            pages=[page.extract_text(extraction_mode='layout') or '' for page in reader.pages[:50]]
    except Exception:
        return {}, {}, {}, False
    text='\n'.join(pages)
    # Remove repeating page furniture before identifying numbered sections.
    text=re.sub(r'(?im)^\s*(?:Pangasinan State University|Research, Extension, and Innovation.*|A\.\s*PSU Outreach.*|Page\s+\d+\s+of\s+\d+)\s*$', '', text)
    headings=list(re.finditer(r'(?m)^\s*(XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|IX|VIII|VII|VI|IV|III|II|X|V|I)\.\s+([^\n]+)',text))
    sections={}
    for i, match in enumerate(headings):
        sections[match[1]]=text[match.start():headings[i+1].start() if i+1<len(headings) else len(text)]
    record, operational, provenance = {}, {}, {}
    labels={
        'implementing_unit':r'Campus\s*/\s*Implementing Unit\s*/\s*Degree Program',
        'beneficiary_count':r'Estimated Number of Beneficiaries', 'volunteer_count':r'Estimated Number of Volunteers',
        'general_objectives':r'General Objectives?', 'specific_objectives':r'Specific Objectives?',
        'psu_roles':r'Roles? and Responsibilities of PSU', 'partner_roles':r'Roles? and Responsibilities of Partner',
        'partnership_duration':r'Duration of Partnership', 'prepared_by':r'Prepared By', 'noted_by':r'Noted By',
        'recommending_by':r'Recommending Approval', 'approved_by':r'Approved By'}
    for key,label in labels.items():
        separator=r'[ \t]*:?[ \t]*' if key=='implementing_unit' else r'[ \t]*:[ \t]*'
        match=re.search(r'(?im)^[ \t]*(?:[IVX]+\.[ \t]*)?(?:[●•][ \t]*)?'+label+separator+r'([^\n]*)',text)
        if match and (value:=_usable(match[1])):
            if key.endswith('_count') and not re.fullmatch(r'\d{1,9}',value):
                continue
            record[key]=value
            provenance[key]={'state':'Captured','source':'Label: '+SCALARS[key], 'excerpt':value[:240]}
    for key,roman in [('rationale','IV'),('methodology','VI'),('evaluation','XIII'),('sustainability','XIV'),('conclusion','XV')]:
        section=sections.get(roman,'')
        if section:
            first,*remaining=section.strip().splitlines()
            inline=first.partition(':')[2]
            body='\n'.join(([inline] if inline else [])+remaining).strip()
            # Printed instructions are a separate parenthesized block in this template.
            body=re.sub(r'^\s*\([^)]*\)\s*','',body,flags=re.S).strip()
            if value:=_usable(body):
                record[key]=value[:10000]
                provenance[key]={'state':'Captured','source':'Section '+roman,'excerpt':value[:240]}
    for key,label in [('title',r'(?:Title of the Outreach\s*/\s*Volunteer Activity|Activity Title|Title)'),('location',r'(?:Location\s*/\s*Community|Location|Venue)')]:
        match=re.search(r'(?im)^\s*(?:[IVX]+\.\s*)?(?:[●•]\s*)?'+label+r'\s*:\s*([^\n]+)',text)
        if match and (value:=_usable(match[1])) and len(value)<= (200 if key=='title' else 500):
            operational[key]=value
            provenance[key]={'state':'Captured','source':'Proposal label','excerpt':value[:240]}
    for key,label in [('date','Start Date'),('end_date','End Date')]:
        match=re.search(r'(?im)^\s*'+label+r'\s*:\s*(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2})\s*$',text)
        if match:
            operational[key]=match[1].replace(' ','T')
            provenance[key]={'state':'Captured','source':label,'excerpt':match[1]}
    choice_sections={'beneficiary_groups':'VII','volunteer_groups':'VIII','engagement_areas':'VIII','activity_types':'IX','outcomes':'XII'}
    for key,options in CHOICES.items():
        source=sections.get(choice_sections[key],text)
        found=[]
        for option in options:
            # Checkbox extraction must carry an explicit selected mark next to its label.
            pattern=re.escape(option).replace(r'\ ',r'\s+')
            if re.search(r'(?:☒|☑|\[[xX✓]\])\s*'+pattern+r'(?=\s|$|\()',source,re.I):
                found.append(option)
        if found:
            record[key]=found
            provenance[key]={'state':'Captured','source':'Selected proposal choices','excerpt':', '.join(found)[:240]}
    aliases={
        'team':[['name'],['designation'],['campus'],['role','leader / member']],
        'implementation':[['activity'],['persons involved'],['timeline'],['expected output']],
        'budget':[['item/description','item / description','item'],['unit of measure'],['quantity'],['unit cost','unit cost (php)'],['expense classification'],['source of funds']],
        'risks':[['identified risk','identified risk (logistical, safety, financial, etc.)'],['likelihood/impact','likelihood / impact'],['mitigation/contingency strategy','mitigation / contingency strategy']]}
    # PDF rows are accepted only where layout preserves distinct columns.
    for page in pages:
        block=[]
        for line in page.splitlines()+['']:
            cells=re.split(r'\s{2,}|\s*\|\s*',line.strip())
            if len(cells)>1:
                block.append(cells)
            elif block:
                tables.append(block);block=[]
    funding={}
    for table in tables:
        if not table:continue
        header=[re.sub(r'\s+',' ',c).strip().lower() for c in table[0]]
        if 'item' in header and 'source of funds' in header:
            for row in table[1:51]:
                if len(row)>max(header.index('item'),header.index('source of funds')):
                    item=_usable(row[header.index('item')])
                    source=_usable(row[header.index('source of funds')])
                    if item and source:funding.setdefault(item.lower(),set()).add(source)
    for table in tables:
        if not table:
            continue
        header=[re.sub(r'\s+',' ',c).strip().lower() for c in table[0]]
        for key,columns in aliases.items():
            indexes=[next((i for i,h in enumerate(header) if h in options),None) for options in columns]
            optional={'team':{3},'budget':{5}}.get(key,set())
            if any(index is None and column not in optional for column,index in enumerate(indexes)):
                continue
            rows=[]
            for values in table[1:51]:
                if len(values)<=max(index for index in indexes if index is not None):
                    continue
                row={column:_usable(values[index]) if index is not None else '' for (column,_),index in zip(TABLES[key][1],indexes)}
                if key=='budget' and not row['source'] and len(funding.get(row['item'].lower(),set()))==1:
                    row['source']=next(iter(funding[row['item'].lower()]))
                if any(row.values()):
                    rows.append(row)
            if rows:
                record[key]=rows
                provenance[key]={'state':'Needs Review','source':TABLES[key][0], 'excerpt':'Check row boundaries and every captured column against the approved proposal.'}
    for key in REQUIRED+list(CHOICES)+list(TABLES)+['title','date','end_date','location']:
        provenance.setdefault(key,{'state':'Not Found','source':'Proposal','excerpt':'Enter this value or confirm it from the approved document.'})
    try:
        record=normalize_record(record)
    except ValueError:
        return {},operational,{},bool(text.strip())
    return record, operational, provenance, bool(text.strip())
