"""
PSU Volunteer Hub - Entry Point
=================================
Application entry point that creates and runs the Flask application.
"""
from app import create_app


app = create_app()


if __name__ == '__main__':
    if not app.debug:
        raise SystemExit('Use a production WSGI server with wsgi:app; app.py is development-only.')
    app.run(debug=app.debug)
