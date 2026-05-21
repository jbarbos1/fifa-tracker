from . import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class League(db.Model):
    __tablename__ = 'leagues'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(120), nullable=False, unique=True)

    members = db.relationship('LeagueMember', back_populates='league')  # Remember how this mapping works

    def __repr__(self):
        return f"<League {self.name}>"


class LeagueMember(db.Model):
    __tablename__ = 'league_members'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    league_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('leagues.id'),
        nullable=True
    )

    league = db.relationship("League", back_populates="members")

    def __repr__(self):
        return f"<LeagueMember {self.username}>"


class UsageSnapshot(db.Model):
    __tablename__ = 'usage_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    total_users = db.Column(db.Integer, nullable=False)
    active_sessions = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False)
