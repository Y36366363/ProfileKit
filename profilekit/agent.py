from __future__ import annotations

import json
from pathlib import Path

from agents import Agent, Runner, set_tracing_disabled

from .env import load_env_file
from .models import AgentTurn, ProfileSession
from .providers import deepseek_client, find_model, resolve_openai_model
from .workflow import InvalidTransition, apply_turn


ROOT = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT = (ROOT / "config" / "system_prompt.md").read_text(encoding="utf-8")
set_tracing_disabled(True)


def build_agent(provider: str | None = None, model: str | None = None) -> Agent:
    load_env_file(ROOT / ".env")
    selected_provider = provider or "openai"
    selected_model = model or "gpt-6-luna"
    if selected_provider != "openai":
        raise ValueError("The Agents SDK runner is used only for OpenAI models")
    return Agent(
        name="ProfileKit",
        instructions=SYSTEM_PROMPT,
        model=resolve_openai_model(selected_provider, selected_model),
        output_type=AgentTurn,
    )


def _turn_input(session: ProfileSession, user_message: str) -> str:
    recent = [message.model_dump() for message in session.transcript[-12:]]
    return json.dumps(
        {
            "current_workflow_stage": session.stage.value,
            "current_profile_record": session.record.model_dump(mode="json"),
            "current_design_preferences": {
                "theme": session.profile_theme,
                "accent_color": session.accent_color,
                "font_style": session.font_style,
                "layout_density": session.layout_density,
            },
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


def _run_deepseek_turn(session: ProfileSession, user_message: str, model: str) -> AgentTurn:
    option = find_model("deepseek", model)
    if option is None:
        raise ValueError(f"Unsupported DeepSeek model: {model}")
    schema = AgentTurn.model_json_schema()
    system = (
        SYSTEM_PROMPT
        + "\n\nReturn exactly one JSON object and no Markdown. The JSON must match this schema:\n"
        + json.dumps(schema, ensure_ascii=False)
    )
    with deepseek_client() as client:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": _turn_input(session, user_message)},
            ],
            response_format={"type": "json_object"},
            max_tokens=6_000,
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("DeepSeek returned no structured ProfileKit output")
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return AgentTurn.model_validate_json(cleaned)


def run_turn(
    session: ProfileSession,
    user_message: str,
    provider: str | None = None,
    model: str | None = None,
    transcript_user_message: str | None = None,
) -> tuple[ProfileSession, str]:
    selected_provider = provider or session.model_provider
    selected_model = model or session.model_name
    if selected_provider == "deepseek":
        turn = _run_deepseek_turn(session, user_message, selected_model)
    else:
        result = Runner.run_sync(
            build_agent(selected_provider, selected_model),
            _turn_input(session, user_message),
        )
        turn = result.final_output
        if not isinstance(turn, AgentTurn):
            turn = AgentTurn.model_validate(turn)
    try:
        updated = apply_turn(session, user_message, turn, transcript_user_message)
    except InvalidTransition as error:
        # Preserve privacy and approval invariants even if a model proposes a skip.
        session.audit_log.append(f"blocked transition: {error}")
        raise RuntimeError(f"ProfileKit blocked an unsafe workflow transition: {error}") from error
    updated.model_provider = selected_provider  # type: ignore[assignment]
    updated.model_name = selected_model
    return updated, turn.assistant_message
