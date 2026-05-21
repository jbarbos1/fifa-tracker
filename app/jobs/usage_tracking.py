from datetime import datetime
from app import db
from app.models import UsageSnapshot, LeagueMember


def track_usage_snapshot():
    user_count = LeagueMember.query.count()

    snapshot = UsageSnapshot(
        total_users=user_count,
        active_sessions=0,
        created_at=datetime.utcnow()
    )

    db.session.add(snapshot)
    db.session.commit()
