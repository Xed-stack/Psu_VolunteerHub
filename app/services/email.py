"""Minimal SMTP delivery used for security notifications."""
import smtplib
from email.message import EmailMessage

from flask import current_app


def send_email(recipient, subject, body):
    """Send email, or log it locally when delivery is intentionally suppressed."""
    if current_app.config.get('MAIL_SUPPRESS_SEND'):
        current_app.logger.info('Suppressed email to %s: %s', recipient, subject)
        return
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = current_app.config['MAIL_DEFAULT_SENDER']
    message['To'] = recipient
    message.set_content(body)
    with smtplib.SMTP(current_app.config['MAIL_SERVER'], current_app.config['MAIL_PORT']) as smtp:
        if current_app.config.get('MAIL_USE_TLS'):
            smtp.starttls()
        if current_app.config.get('MAIL_USERNAME'):
            smtp.login(current_app.config['MAIL_USERNAME'], current_app.config['MAIL_PASSWORD'])
        smtp.send_message(message)
