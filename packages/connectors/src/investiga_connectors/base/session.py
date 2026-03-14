"""SessionManager — manages the lifecycle of a source session."""

import logging
from typing import Any

from sqlalchemy.orm import Session

from investiga_connectors.base.blocking import BlockingDetector, BlockState
from investiga_repositories.postgres.models.ops import SourceSession

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages the operational state of a source extraction session."""

    def __init__(self, db: Session, source_name: str, detector: BlockingDetector):
        self.db = db
        self.source_name = source_name
        self.detector = detector

    def get_or_create_session(self, mode: str = "api") -> SourceSession:
        """Retrieve the active session or create a new one."""
        session_record = (
            self.db.query(SourceSession)
            .filter(
                SourceSession.source_name == self.source_name,
                SourceSession.session_mode == mode,
                SourceSession.status.in_(["ready", "running"])
            )
            .order_by(SourceSession.created_at.desc())
            .first()
        )

        if not session_record:
            session_record = SourceSession(
                source_name=self.source_name,
                session_mode=mode,
                status="ready"
            )
            self.db.add(session_record)
            self.db.commit()
            self.db.refresh(session_record)

        return session_record

    def handle_response(self, session_id: int, response: Any) -> BlockState:
        """Analyze a response and update the session state accordingly."""
        state = self.detector.detect(response)
        
        session_record = self.db.query(SourceSession).get(session_id)
        if not session_record:
            return state

        if state.is_blocked:
            session_record.status = "blocked"
            session_record.last_error_code = state.block_type
            session_record.last_error_message = state.message
            logger.warning(
                f"Session {session_id} for {self.source_name} BLOCKED: {state.block_type}"
            )
            # We don't commit here immediately if part of a larger transaction, 
            # but usually session state should be committed right away.
            self.db.commit()
        else:
            # If it was blocked, but now it's fine, we reset
            if session_record.status == "blocked":
                session_record.status = "ready"
                session_record.last_error_code = None
                session_record.last_error_message = None
                self.db.commit()

        return state
