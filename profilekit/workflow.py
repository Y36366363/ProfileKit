from __future__ import annotations

from .models import AgentTurn, ProfileSession, TranscriptMessage, WorkflowStage


STAGE_ORDER = list(WorkflowStage)

APPROVAL_GATES = {
    (WorkflowStage.CONTENT_APPROVAL, WorkflowStage.FORMAT_RECOMMENDATION),
    (WorkflowStage.VISUAL_DIRECTION, WorkflowStage.DRAFT),
    (WorkflowStage.FINAL_APPROVAL, WorkflowStage.EDITABLE_OUTPUT),
}


class InvalidTransition(ValueError):
    pass


def validate_record_for_draft(session: ProfileSession) -> None:
    record = session.record
    forbidden = [item for item in record.items if item.label.lower().replace(" ", "_") == "home_address"]
    if forbidden:
        raise InvalidTransition("Home addresses must never be included")

    unapproved = [
        item.label
        for item in record.items
        if item.user_decision == "include" and item.status.value not in {"user_approved", "suggested_wording"}
    ]
    if unapproved:
        raise InvalidTransition(f"Included content lacks approval: {', '.join(unapproved)}")

    unauthorized_links = [link.value for link in record.links if link.user_approval is False]
    unauthorized_media = [item.description for item in record.images_and_logos if item.user_approval is False]
    if unauthorized_links or unauthorized_media:
        details = unauthorized_links + unauthorized_media
        raise InvalidTransition(f"Links or media still require a public-use decision: {', '.join(details)}")

    if record.conflicts:
        raise InvalidTransition("Source conflicts must be resolved or excluded before drafting")


def validate_transition(current: WorkflowStage, proposed: WorkflowStage, approval: str | None) -> None:
    """Allow staying put, advancing one stage, or returning to an earlier stage."""
    current_index = STAGE_ORDER.index(current)
    proposed_index = STAGE_ORDER.index(proposed)

    if proposed_index <= current_index:
        return
    if proposed_index != current_index + 1:
        raise InvalidTransition(f"Cannot skip from {current.value} to {proposed.value}")
    if (current, proposed) in APPROVAL_GATES and not (approval and approval.strip()):
        raise InvalidTransition(
            f"Transition from {current.value} to {proposed.value} requires explicit user approval"
        )


def apply_turn(session: ProfileSession, user_message: str, turn: AgentTurn) -> ProfileSession:
    validate_transition(session.stage, turn.proposed_stage, turn.approval_evidence)
    if turn.proposed_stage == WorkflowStage.DRAFT:
        candidate = session.model_copy(deep=True)
        candidate.record = turn.record
        validate_record_for_draft(candidate)
    previous = session.stage
    session.stage = turn.proposed_stage
    session.record = turn.record
    session.transcript.extend(
        [
            TranscriptMessage(role="user", content=user_message),
            TranscriptMessage(role="assistant", content=turn.assistant_message),
        ]
    )
    session.audit_log.append(
        f"{previous.value} -> {turn.proposed_stage.value}"
        + (f"; approval: {turn.approval_evidence}" if turn.approval_evidence else "")
    )
    return session
