"""Shared security validation for credentials entered by users or admins."""
import re


def password_error(password, minimum=8):
    if not password:
        return 'Password is required.'
    if len(password) < minimum:
        return f'Password must be at least {minimum} characters.'
    if not re.search(r'[A-Z]', password):
        return 'Password must include at least one uppercase letter.'
    if not re.search(r'[a-z]', password):
        return 'Password must include at least one lowercase letter.'
    if not re.search(r'\d', password):
        return 'Password must include at least one number.'
    if not re.search(r'[^A-Za-z0-9]', password):
        return 'Password must include at least one special character.'
    return None
