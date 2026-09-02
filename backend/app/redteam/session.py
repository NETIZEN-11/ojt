from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.domain.enums import Verdict


class RedTeamTurn(BaseModel):
    turn_number: int
    prompt: str
    response: str
    tool_calls: list[dict[str, Any]] = []
    judge_verdict: Verdict | None = None
    judge_rationale: str | None = None
    judge_confidence: float | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RedTeamSession(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    target_agent_id: UUID
    strategy: dict[str, Any]
    turns: list[RedTeamTurn] = []
    current_turn: int = 0
    max_turns: int = 8
    objective_achieved: bool = False
    final_verdict: Verdict | None = None
    transcript: list[dict[str, Any]] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None


class RedTeamSessionManager:
    def __init__(self):
        self.sessions: dict[UUID, RedTeamSession] = {}

    def create_session(
        self, target_agent_id: UUID, strategy: dict[str, Any], max_turns: int = 8
    ) -> RedTeamSession:
        session = RedTeamSession(
            target_agent_id=target_agent_id,
            strategy=strategy,
            max_turns=max_turns,
        )
        self.sessions[session.id] = session
        return session

    def get_session(self, session_id: UUID) -> RedTeamSession | None:
        return self.sessions.get(session_id)

    def add_turn(self, session_id: UUID, turn: RedTeamTurn) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.turns.append(turn)
        session.current_turn = turn.turn_number
        return True

    def complete_session(
        self, session_id: UUID, verdict: Verdict, objective_achieved: bool = False
    ) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.final_verdict = verdict
        session.objective_achieved = objective_achieved
        session.completed_at = datetime.utcnow()
        return True

    def set_error(self, session_id: UUID, error: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.error = error
        session.completed_at = datetime.utcnow()
        return True


session_manager = RedTeamSessionManager()
