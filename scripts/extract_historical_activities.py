"""Extract PSU historical-activity tables from the supplied 36-page PDF.

This is a reproducibility helper for the committed CSV. It requires pdfplumber
but the runtime importer itself uses only Python's standard csv module.
"""
import argparse
import csv
import hashlib
import re
from pathlib import Path

import pdfplumber


SOURCE_NAME = ('data-request-covp-urdaneta-leo-villanueva-2020-2025-'
               'SUMMARY-OF-VOLUNTEER-ACTIVITIES.pdf')
HEADERS = {'N\no.', 'No.', 'TITLE'}


def clean(value):
    if not value:
        return ''
    value = value.replace('\ufffd', "'").replace('\u2019', "'")
    value = re.sub(r'\s+', ' ', value).strip()
    return value


def append_text(original, continuation):
    continuation = clean(continuation)
    if not continuation:
        return original
    return f'{original} {continuation}'.strip()


def extract(pdf_path):
    records = []
    unit_name = None
    with pdfplumber.open(pdf_path) as document:
        for page_number, page in enumerate(document.pages[2:], start=3):
            tables = page.extract_tables()
            if not tables:
                continue
            for row in tables[0]:
                row = [(cell or '') for cell in row]
                first = clean(row[0])
                if first in HEADERS or first.lower() in {'n o.', 'no.'}:
                    continue
                if first.upper().endswith(' CAMPUS') or first.upper() in {
                        'SCHOOL OF ADVANCED STUDIES', 'OPEN UNIVERSITY SYSTEMS'}:
                    unit_name = first.title() if first.isupper() else first
                    continue
                if first.isdigit():
                    if not unit_name:
                        raise ValueError(
                            f'Activity before unit heading on page {page_number}')
                    records.append({
                        'source_page': page_number,
                        'source_row': int(first),
                        'unit_name': unit_name,
                        'title': clean(row[1]),
                        'activity_type': clean(row[2]).title(),
                        'partners': clean(row[3]),
                        'participant_categories': clean(row[4]),
                        'volunteer_count': clean(row[5]),
                        'year_conducted': clean(row[6]),
                    })
                    continue
                if records and any(clean(cell) for cell in row):
                    # A record split by a PDF page boundary.
                    for index, field in enumerate((None, 'title', 'activity_type',
                                                   'partners',
                                                   'participant_categories',
                                                   'volunteer_count',
                                                   'year_conducted')):
                        if field:
                            records[-1][field] = append_text(
                                records[-1][field], row[index])

    for record in records:
        activity_type = record['activity_type'].replace(' / ', '/').upper()
        record['activity_type'] = {
            'EXTENSION': 'Extension',
            'OUTREACH': 'Outreach',
            'EXTENSION/OUTREACH': 'Extension/Outreach',
        }.get(activity_type, record['activity_type'])
        for field in ('volunteer_count', 'year_conducted'):
            value = record[field]
            record[field] = value if value.isdigit() else ''
        identity = '|'.join((record['unit_name'], str(record['source_row']),
                             record['title'], record['year_conducted']))
        record['source_key'] = hashlib.sha256(identity.encode('utf-8')).hexdigest()
        record['source_document'] = SOURCE_NAME
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pdf', type=Path)
    parser.add_argument('csv', type=Path)
    args = parser.parse_args()
    records = extract(args.pdf)
    fields = ['source_key', 'source_document', 'source_page', 'source_row',
              'unit_name', 'title', 'activity_type', 'partners',
              'participant_categories', 'volunteer_count', 'year_conducted']
    args.csv.parent.mkdir(parents=True, exist_ok=True)
    with args.csv.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(f'Extracted {len(records)} activities to {args.csv}')


if __name__ == '__main__':
    main()
