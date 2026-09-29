from __future__ import annotations

from .models import (
    ImageItem,
    ItemStatus,
    LinkItem,
    ProfileItem,
    ProfileMetadata,
    ProfileRecord,
    ProfileSession,
    TranscriptMessage,
    WorkflowStage,
)


def build_demo_session() -> ProfileSession:
    """Return a fictional, non-sensitive scenario for classroom demonstrations."""
    record = ProfileRecord(
        profile_metadata=ProfileMetadata(
            audience="Faculty and student researchers",
            occasion="Campus research showcase",
            purpose="Introduce a student research interest and one class project",
            output_type="Researcher profile",
            output_size="US Letter, one page",
            tone="Clear, modest, and approachable",
            language="English",
            accessibility_requirements="Readable from a projected classroom screen",
            visual_preferences="Structured layout with a blue accent",
            privacy_restrictions="No phone number or home address",
        ),
        items=[
            ProfileItem(
                category="identity",
                label="Preferred name",
                value="Lin Chen",
                status=ItemStatus.CONFIRMED,
                source="Demo resume",
            ),
            ProfileItem(
                category="identity",
                label="Current role",
                value="Graduate student in information science",
                status=ItemStatus.CONFIRMED,
                source="Demo resume",
            ),
            ProfileItem(
                category="introduction",
                label="Short introduction",
                value="Explores how people understand and use public information systems.",
                status=ItemStatus.SUGGESTED_WORDING,
                source="Demo approved research-interest statement",
            ),
            ProfileItem(
                category="project",
                label="Class project",
                value="Supported interview coding and summarized recurring themes for a course study.",
                status=ItemStatus.SUGGESTED_WORDING,
                source="Demo project notes",
            ),
            ProfileItem(
                category="contact",
                label="Professional email",
                value="lin.chen@example.edu",
                status=ItemStatus.NEEDS_CONFIRMATION,
                source="Demo resume",
                privacy="Requires explicit approval for this audience",
            ),
        ],
        links=[
            LinkItem(
                value="https://example.edu/lin-chen",
                purpose="Institutional profile",
                audience="Campus research showcase",
                authorization_status="unknown",
                source="Demo resume",
            )
        ],
        images_and_logos=[
            ImageItem(
                description="Optional portrait placeholder",
                intended_use="Profile header",
                ownership_or_permission="unknown",
            )
        ],
        privacy_decisions=["Exclude home address", "Exclude phone number"],
        uncertainties=["Confirm whether the professional email may be displayed"],
        placeholders=["Optional approved methods list"],
        draft_status="profile_record_ready",
    )
    return ProfileSession(
        stage=WorkflowStage.PROFILE_RECORD,
        record=record,
        transcript=[
            TranscriptMessage(
                role="assistant",
                content=(
                    "I reviewed the fictional demo materials and prepared a Personal Profile Record. "
                    "Use the controls beside each item to approve, revise, exclude, or restrict it."
                ),
            )
        ],
        audit_log=["demo -> personal_profile_record"],
    )
