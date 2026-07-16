"""
Database Models for PSU Volunteer Hub
=====================================
Centralized SQLAlchemy database instance shared by all models.
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine

# Single database instance used across all models
db = SQLAlchemy()
