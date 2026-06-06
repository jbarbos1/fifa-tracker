from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

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