from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    INTAKE = "intake"
    SOURCE_REVIEW = "source_review"
    PROFILE_RECORD = "personal_profile_record"
    PRIVACY_REVIEW = "privacy_and_authorization_review"
    CONTENT_APPROVAL = "user_content_approval"
    FORMAT_RECOMMENDATION = "format_recommendation"
    VISUAL_DIRECTION = "visual_direction_choice"
    DRAFT = "draft"
    FINAL_REVIEW = "final_review"
    FINAL_APPROVAL = "user_approval"
    EDITABLE_OUTPUT = "editable_output_or_export_instructions"


class ItemStatus(str, Enum):
    CONFIRMED = "confirmed"
    USER_APPROVED = "user_approved"
    NEEDS_CONFIRMATION = "needs_confirmation"
    SUGGESTED_WORDING = "suggested_wording"
    PLACEHOLDER = "placeholder"
    NOT_SUPPORTED = "not_supported"


class ProfileItem(BaseModel):
    category: str
    label: str
    value: str
    status: ItemStatus
    source: str | None = None
    privacy: str | None = None
    user_decision: Literal["pending", "include", "exclude", "revise", "restrict"] = "pending"


class LinkItem(BaseModel):
    value: str
    purpose: str | None = None
    audience: str | None = None
    authorization_status: str = "unknown"
    source: str | None = None
    user_approval: bool = False


class ImageItem(BaseModel):
    description: str
    intended_use: str | None = None
    ownership_or_permission: str = "unknown"
    alternative_text: str | None = None
    status: str = "authorization_needed"
    user_approval: bool = False


class ProfileMetadata(BaseModel):
    audience: str | None = None
    occasion: str | None = None
    purpose: str | None = None
    output_type: str | None = None
    output_size: str | None = None
    tone: str | None = None
    language: str | None = None
    accessibility_requirements: str | None = None
    visual_preferences: str | None = None
    privacy_restrictions: str | None = None
    approval_status: str = "awaiting_user_review"


class ProfileRecord(BaseModel):
    profile_metadata: ProfileMetadata = Field(default_factory=ProfileMetadata)
    items: list[ProfileItem] = Field(default_factory=list)
    links: list[LinkItem] = Field(default_factory=list)
    images_and_logos: list[ImageItem] = Field(default_factory=list)
    privacy_decisions: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    placeholders: list[str] = Field(default_factory=list)
    selected_format: str | None = None
    selected_visual_direction: str | None = None
    draft_status: str = "intake"
    final_review_status: str | None = None


class AgentTurn(BaseModel):
    assistant_message: str = Field(description="User-facing response in the user's language")
    proposed_stage: WorkflowStage
    record: ProfileRecord
    approval_evidence: str | None = Field(
        default=None,
        description="Quote or concise description of explicit approval in the latest user message",
    )
    safety_notes: list[str] = Field(default_factory=list)


class TranscriptMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ProfileSession(BaseModel):
    stage: WorkflowStage = WorkflowStage.INTAKE
    model_provider: Literal["deepseek", "openai"] = "deepseek"
    model_name: str = "deepseek-flash"
    profile_theme: Literal["academic", "modern", "minimal"] = "academic"
    record: ProfileRecord = Field(default_factory=ProfileRecord)
    transcript: list[TranscriptMessage] = Field(default_factory=list)
    audit_log: list[str] = Field(default_factory=list)
