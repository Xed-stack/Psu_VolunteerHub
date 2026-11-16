"""Session-bound private files for the three existing import workflows."""
import hashlib
import secrets
from pathlib import Path

from flask import abort, current_app, request, session
from flask_login import current_user


def folder():
    directory = Path(current_app.config['PRIVATE_UPLOAD_FOLDER']) / 'import-previews'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def staged_file(slot, verify_token=False):
    staged = session.get(slot)
    if not staged or staged.get('owner', current_user.id) != current_user.id:
        abort(400, description='This preview is unavailable. Upload and validate the file again.')
    if verify_token and not secrets.compare_digest(staged.get('token', ''), request.form.get('token', '')):
        abort(400)
    path = folder() / Path(staged['file']).name
    if not path.is_file() or (staged.get('hash') and hashlib.sha256(path.read_bytes()).hexdigest() != staged['hash']):
        discard(slot)
        abort(400, description='The preview file is unavailable or changed. Upload and validate it again.')
    return staged, path


def discard(slot):
    staged = session.pop(slot, None)
    if staged and staged.get('owner', current_user.id) == current_user.id:
        (folder() / Path(staged['file']).name).unlink(missing_ok=True)


def save(slot, content, suffix):
    path = folder() / (secrets.token_hex(24) + suffix)
    path.write_bytes(content)
    discard(slot)
    session[slot] = dict(file=path.name, token=secrets.token_urlsafe(32),
                         hash=hashlib.sha256(content).hexdigest(), owner=current_user.id)
    return session[slot]


def page_rows(rows):
    total = len(rows)
    pages = max(1, (total + 24) // 25)
    page = min(pages, max(1, request.args.get('page', 1, type=int) or 1))
    return dict(rows=rows[(page - 1) * 25:page * 25], total=total,
                page=page, pages=pages, first=(page - 1) * 25 + 1 if total else 0,
                last=min(page * 25, total))
