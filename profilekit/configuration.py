from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from .models import ItemStatus, ProfileItem, ProfileMetadata, ProfileRecord, ProfileSession, WorkflowStage


HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


class EditableProfile(BaseModel):
    name: str = ""
    role: str = ""
    introduction: str = ""


class DesignPreferences(BaseModel):
    theme: Literal["academic", "modern", "minimal", "sunrise", "studio", "editorial"] = "academic"
    accent_color: str = "#147D70"
    font_style: Literal["serif", "sans", "hybrid"] = "hybrid"
    layout_density: Literal["compact", "balanced", "airy"] = "balanced"

    @field_validator("accent_color")
    @classmethod
    def valid_color(cls, value: str) -> str:
        if not HEX_COLOR.fullmatch(value):
            raise ValueError("accent_color must use six-digit hex format, such as #147D70")
        return value.upper()


class ProfileConfig(BaseModel):
    profile_metadata: ProfileMetadata = Field(default_factory=ProfileMetadata)
    profile: EditableProfile = Field(default_factory=EditableProfile)
    items: list[ProfileItem] = Field(default_factory=list)
    design: DesignPreferences = Field(default_factory=DesignPreferences)


def _upsert(session: ProfileSession, category: str, label: str, value: str, source: str) -> None:
    if not value.strip():
        return
    existing = next((item for item in session.record.items if item.label.lower() == label.lower()), None)
    if existing:
        existing.category = category
        existing.value = value.strip()
        existing.status = ItemStatus.USER_APPROVED
        existing.source = source
        existing.user_decision = "include"
        return
    session.record.items.append(
        ProfileItem(
            category=category,
            label=label,
            value=value.strip(),
            status=ItemStatus.USER_APPROVED,
            source=source,
            user_decision="include",
        )
    )


def apply_profile_config(
    session: ProfileSession,
    config: ProfileConfig,
    source: str,
    *,
    replace_record: bool = False,
) -> ProfileSession:
    if replace_record:
        session.record = ProfileRecord()
        session.transcript = []
    session.record.profile_metadata = config.profile_metadata
    _upsert(session, "identity", "Preferred name", config.profile.name, source)
    _upsert(session, "identity", "Current role", config.profile.role, source)
    _upsert(session, "introduction", "Short introduction", config.profile.introduction, source)
    for incoming in config.items:
        _upsert(session, incoming.category, incoming.label, incoming.value, source)
    session.profile_theme = config.design.theme
    session.accent_color = config.design.accent_color
    session.font_style = config.design.font_style
    session.layout_density = config.design.layout_density
    if session.record.items:
        session.stage = WorkflowStage.PROFILE_RECORD
        session.record.draft_status = "profile_record_ready"
    session.audit_log.append(f"configuration applied: {source}")
    return session


def load_profile_config(path: Path) -> ProfileConfig:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read profile configuration: {error}") from error
    return ProfileConfig.model_validate(payload)
