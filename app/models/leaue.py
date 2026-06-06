from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class League(db.Model):
    __tablename__ = 'leagues'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(120), nullable=False, unique=True)

    members = db.relationship('LeagueMember', back_populates='league')  # Remember how this mapping works

    def __repr__(self):
        return f"<League {self.name}>"