from __future__ import annotations

import json
import os
from pathlib import Path

from agents import Agent, Runner

from .env import load_env_file
from .models import AgentTurn, ProfileSession
from .workflow import InvalidTransition, apply_turn


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT = (ROOT / "config" / "system_prompt.md").read_text(encoding="utf-8")


def build_agent() -> Agent:
    load_env_file(ROOT / ".env")
    model = os.environ.get("PROFILEKIT_MODEL", "gpt-6-astra")
    return Agent(
        name="ProfileKit",
        instructions=SYSTEM_PROMPT,
        model=model,
        output_type=AgentTurn,
    )


def _turn_input(session: ProfileSession, user_message: str) -> str:
    recent = [message.model_dump() for message in session.transcript[-12:]]
    return json.dumps(
        {
            "current_workflow_stage": session.stage.value,
            "current_profile_record": session.record.model_dump(mode="json"),
            "recent_transcript": recent,
            "latest_user_message": user_message,
            "controller_rules": [
                "Propose either the same stage, the immediately following stage, or an earlier stage.",
                "Set approval_evidence only when the latest user message explicitly supplies the required decision.",
                "Ask only the next necessary question.",
            ],
        },
        ensure_ascii=False,
    )


def run_turn(session: ProfileSession, user_message: str) -> tuple[ProfileSession, str]:
    result = Runner.run_sync(build_agent(), _turn_input(session, user_message))
    turn = result.final_output
    if not isinstance(turn, AgentTurn):
        turn = AgentTurn.model_validate(turn)
    try:
        updated = apply_turn(session, user_message, turn)
    except InvalidTransition as error:
        # Preserve privacy and approval invariants even if a model proposes a skip.
        session.audit_log.append(f"blocked transition: {error}")
        raise RuntimeError(f"ProfileKit blocked an unsafe workflow transition: {error}") from error
    return updated, turn.assistant_message
