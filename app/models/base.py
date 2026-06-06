"""
base.py — shared db instance and declarative base.
Import `db` everywhere; never create a second SQLAlchemy instance.
"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from app.extensions import db

# Explicit naming convention keeps Alembic migrations deterministic.
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

db = SQLAlchemy(metadata=MetaData(naming_convention=convention))


class Base(db.Model):
    __abstract__ = True
