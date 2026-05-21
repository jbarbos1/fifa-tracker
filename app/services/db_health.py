from app import db

from datetime import datetime


def check_database_health():
    result = db.session.execute(db.text('SELECT 1')).scalar()

    print({
        'task': 'db_health_check',
        'status': 'healthy' if result == 1 else 'warning',
        'checked_at': datetime.utcnow()
    })
