"""Shared schedule and private-document rules for activity workspaces."""
import io
import re
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.etree import ElementTree
from flask import current_app
from werkzeug.utils import secure_filename


def local_now():
    return datetime.now(timezone(timedelta(hours=8))).replace(tzinfo=None)


def attendance_open(event, now=None):
    now = now or local_now()
    return (event.lifecycle_status == 'approved' and event.end_date is not None
            and event.date <= now < event.end_date)


def save_document(file):
    if not file or not file.filename:
        raise ValueError('Choose a PDF or DOCX document.')
    name = secure_filename(file.filename)
    suffix = Path(name).suffix.lower()
    data = file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise ValueError('Documents must be 10 MB or smaller.')
    text = ''
    if suffix == '.pdf' and data.startswith(b'%PDF-'):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = '\n'.join(page.extract_text() or '' for page in reader.pages[:50])
        except Exception:
            # Scanned/encrypted proposals remain attachable for manual review.
            text = ''
    elif suffix == '.docx' and zipfile.is_zipfile(io.BytesIO(data)):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                info = archive.getinfo('word/document.xml')
                if info.file_size > 5 * 1024 * 1024:
                    raise ValueError('The document text is too large.')
                root = ElementTree.fromstring(archive.read(info))
                text = '\n'.join(''.join(p.itertext()) for p in root.iter(
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
        except (KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            raise ValueError('Choose a valid DOCX document.') from exc
    else:
        raise ValueError('Choose a valid PDF or DOCX document.')
    folder = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'proposals'
    folder.mkdir(parents=True, exist_ok=True)
    stored = uuid.uuid4().hex + suffix
    (folder / stored).write_bytes(data)
    fields = {}
    for key, label in [('title', '(?:activity title|title)'), ('location', '(?:venue|location)'),
                       ('description', '(?:description|rationale)')]:
        match = re.search(r'^\s*' + label + r'\s*:\s*(.+)$', text, re.I | re.M)
        if match:
            fields[key] = match.group(1).strip()[:2000 if key == 'description' else 200]
    for key, label in [('date', '(?:start date|start)'), ('end_date', '(?:end date|end)')]:
        match = re.search(r'^\s*' + label + r'\s*:\s*(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2})', text, re.I | re.M)
        if match:
            fields[key] = match.group(1).replace(' ', 'T')
    return {'path': stored, 'name': name, 'readable': bool(text.strip())}, fields
