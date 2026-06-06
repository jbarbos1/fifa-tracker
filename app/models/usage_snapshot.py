from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class UsageSnapshot(db.Model):
    __tablename__ = 'usage_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    total_users = db.Column(db.Integer, nullable=False)
    active_sessions = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False)
