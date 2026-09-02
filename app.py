"""
PSU Volunteer Hub - Entry Point
=================================
Application entry point that creates and runs the Flask application.
"""
from app import create_app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)
