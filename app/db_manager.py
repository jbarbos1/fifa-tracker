from . import db
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class DBManager:
    @staticmethod
    def get_by_id(model, record_id):
        """Safely getch a single record by its primary key"""
        try:
            return db.session.get(model, record_id)
        except SQLAlchemyError as e:
            logger.error(f"Database read error for {model.__name__} ID {record_id}: {e}")
            return None

    @staticmethod
    def execute_transaction(operations_callback):
        """Executes a sequence of db ops within a strict transaction block. Ensures all ines process prior to committing. """
        try:
            # Execute business logic passed into manager
            result = operations_callback(db.session)

            db.session.commit()
            return True, result
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Transaction aborted and rolled back. Error: {e}")
            return False, str(e)
