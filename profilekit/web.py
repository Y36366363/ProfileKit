from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import ROOT, run_turn
from .configuration import (
    DesignPreferences,
    EditableProfile,
    ProfileConfig,
    apply_profile_config,
    load_profile_config,
)
from .demo import build_demo_session
from .env import load_env_file
from .models import ItemStatus, ProfileSession
from .providers import available_catalog, default_selection, find_model, model_is_ready
from .profile_document import THEMES, build_profile_pdf, presentation_payload, theme_catalog
from .sources import MAX_SOURCE_BYTES, SourceError, build_source_bundle


WEB_ROOT = Path(__file__).with_name("webui")
SESSION_PATH = ROOT / ".profilekit" / "web-session.json"
load_env_file(ROOT / ".env")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)


class DecisionRequest(BaseModel):
    decision: Literal["pending", "include", "exclude", "revise", "restrict"]


class ModelSelectionRequest(BaseModel):
    provider: Literal["deepseek", "openai"]
    model: str = Field(min_length=1, max_length=80)


class ThemeSelectionRequest(BaseModel):
    theme: Literal["academic", "modern", "minimal", "sunrise", "studio", "editorial"]


class PreferencesRequest(BaseModel):
    name: str = Field(default="", max_length=120)
    role: str = Field(default="", max_length=180)
    introduction: str = Field(default="", max_length=1_200)
    audience: str = Field(default="", max_length=300)
    occasion: str = Field(default="", max_length=300)
    purpose: str = Field(default="", max_length=500)
    tone: str = Field(default="", max_length=200)
    visual_preferences: str = Field(default="", max_length=500)
    privacy_restrictions: str = Field(default="", max_length=500)
    theme: Literal["academic", "modern", "minimal", "sunrise", "studio", "editorial"] = "academic"
    accent_color: str = "#147D70"
    font_style: Literal["serif", "sans", "hybrid"] = "hybrid"
    layout_density: Literal["compact", "balanced", "airy"] = "balanced"


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.session = self._load()
        self.pending_sources: list[str] = []
        self.private_sources: list[str] = []

    def _load(self) -> ProfileSession:
        if not self.path.exists():
            provider, model = default_selection()
            return ProfileSession(model_provider=provider, model_name=model)
        try:
            return ProfileSession.model_validate_json(self.path.read_text(encoding="utf-8"))
        except Exception:
            return ProfileSession()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.session.model_dump_json(indent=2), encoding="utf-8")
        os.chmod(self.path, 0o600)


store = SessionStore(SESSION_PATH)
app = FastAPI(title="ProfileKit", docs_url=None, redoc_url=None)


DISPLAY_REDACTIONS = (
    (re.compile(r"\b[^\s@]+@[^\s@]+\b"), "[email withheld]"),
    (
        re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-])\d{3}[\s.-]\d{4}(?!\w)"),
        "[phone withheld]",
    ),
    (re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE), "[link withheld]"),
    (re.compile(r"\b(?:github|linkedin)\.com/\S+", re.IGNORECASE), "[link withheld]"),
)


def redact_sensitive_display(text: str) -> str:
    for pattern, replacement in DISPLAY_REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def public_state() -> dict:
    payload = store.session.model_dump(mode="json")
    try:
        local_session = str(store.path.relative_to(ROOT))
    except ValueError:
        local_session = store.path.name
    selected = find_model(store.session.model_provider, store.session.model_name)
    payload["pending_source_count"] = len(store.pending_sources)
    payload["runtime"] = {
        "provider": store.session.model_provider,
        "provider_label": {"deepseek": "DeepSeek", "openai": "OpenAI"}[store.session.model_provider],
        "model": store.session.model_name,
        "model_label": selected.label if selected else store.session.model_name,
        "api_key_ready": bool(selected and model_is_ready(selected)),
        "models": available_catalog(),
        "local_session": local_session,
    }
    payload["presentation"] = presentation_payload(
        store.session.record,
        store.session.profile_theme,
        store.session.accent_color,
        store.session.font_style,
        store.session.layout_density,
    )
    payload["themes"] = theme_catalog()
    return payload


@app.get("/api/session")
def get_session() -> JSONResponse:
    return JSONResponse(public_state())


@app.post("/api/chat")
def chat(request: ChatRequest) -> JSONResponse:
    with store.lock:
        display_message = request.message.strip()
        message = display_message
        private_source_count = 0
        if store.private_sources:
            message += "\n\n" + "\n\n---\n\n".join(store.private_sources)
        if store.pending_sources:
            private_source_count = sum(source.count("SOURCE:") for source in store.pending_sources)
            store.pending_sources.clear()
        if private_source_count:
            noun = "file" if private_source_count == 1 else "files"
            display_message += (
                f"\n\n[ProfileKit privately reviewed {private_source_count} uploaded {noun}. "
                "Source text is hidden from the on-screen conversation.]"
            )
        try:
            store.session, reply = run_turn(
                store.session,
                message,
                store.session.model_provider,
                store.session.model_name,
                transcript_user_message=display_message,
            )
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail=f"ProfileKit kept the current workflow stage: {error}",
            ) from error
        reply = redact_sensitive_display(reply)
        if store.session.transcript and store.session.transcript[-1].role == "assistant":
            store.session.transcript[-1].content = reply
        store.save()
    return JSONResponse({"reply": reply, "session": public_state()})


@app.patch("/api/model")
def select_model(request: ModelSelectionRequest) -> JSONResponse:
    option = find_model(request.provider, request.model)
    if option is None:
        raise HTTPException(status_code=400, detail="This model is not in the ProfileKit catalog.")
    if not model_is_ready(option):
        raise HTTPException(
            status_code=400,
            detail=f"The API key for {option.label} is not configured.",
        )
    with store.lock:
        store.session.model_provider = request.provider
        store.session.model_name = request.model
        store.session.audit_log.append(f"model selected: {request.provider}/{request.model}")
        store.save()
    return JSONResponse(public_state())


@app.patch("/api/theme")
def select_theme(request: ThemeSelectionRequest) -> JSONResponse:
    if request.theme not in THEMES:
        raise HTTPException(status_code=400, detail="This profile theme is not available.")
    with store.lock:
        store.session.profile_theme = request.theme
        store.session.accent_color = THEMES[request.theme]["accent"]
        store.session.audit_log.append(f"profile theme selected: {request.theme}")
        store.save()
    return JSONResponse(public_state())


@app.put("/api/preferences")
def update_preferences(request: PreferencesRequest) -> JSONResponse:
    metadata = store.session.record.profile_metadata.model_copy(
        update={
            "audience": request.audience or None,
            "occasion": request.occasion or None,
            "purpose": request.purpose or None,
            "tone": request.tone or None,
            "visual_preferences": request.visual_preferences or None,
            "privacy_restrictions": request.privacy_restrictions or None,
            "language": store.session.record.profile_metadata.language or "English",
            "output_type": store.session.record.profile_metadata.output_type or "One-page personal profile",
            "output_size": store.session.record.profile_metadata.output_size or "US Letter, one page",
        }
    )
    try:
        config = ProfileConfig(
            profile_metadata=metadata,
            profile=EditableProfile(
                name=request.name,
                role=request.role,
                introduction=request.introduction,
            ),
            design=DesignPreferences(
                theme=request.theme,
                accent_color=request.accent_color,
                font_style=request.font_style,
                layout_density=request.layout_density,
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    with store.lock:
        apply_profile_config(store.session, config, "Web customization form")
        store.save()
    return JSONResponse(public_state())


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)) -> JSONResponse:
    if len(files) > 8:
        raise HTTPException(status_code=400, detail="Upload at most 8 files at a time.")
    accepted: list[str] = []
    configured: list[str] = []
    bundle = ""
    configs: list[tuple[str, ProfileConfig]] = []
    with tempfile.TemporaryDirectory(prefix="profilekit-upload-") as directory:
        paths: list[Path] = []
        for upload_file in files:
            safe_name = Path(upload_file.filename or "source.txt").name
            data = await upload_file.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise HTTPException(status_code=413, detail=f"{safe_name} exceeds the 5 MB limit.")
            path = Path(directory) / safe_name
            path.write_bytes(data)
            if safe_name.lower() == "default_config.json":
                try:
                    configs.append((safe_name, load_profile_config(path)))
                except ValueError as error:
                    raise HTTPException(status_code=400, detail=str(error)) from error
                configured.append(safe_name)
            else:
                paths.append(path)
            accepted.append(safe_name)
        try:
            bundle = build_source_bundle(paths) if paths else ""
        except SourceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    with store.lock:
        for filename, config in configs:
            apply_profile_config(store.session, config, filename, replace_record=True)
        if bundle:
            store.pending_sources.append(bundle)
            store.private_sources.append(bundle)
        if configs:
            store.save()
    return JSONResponse({"accepted": accepted, "configured": configured, "session": public_state()})


@app.patch("/api/items/{item_index}")
def decide_item(item_index: int, request: DecisionRequest) -> JSONResponse:
    with store.lock:
        try:
            item = store.session.record.items[item_index]
        except IndexError as error:
            raise HTTPException(status_code=404, detail="Profile item not found.") from error
        item.user_decision = request.decision
        if request.decision == "include" and item.status in {
            ItemStatus.CONFIRMED,
            ItemStatus.SUGGESTED_WORDING,
        }:
            item.status = ItemStatus.USER_APPROVED
        store.session.audit_log.append(f"item decision: {item.label} -> {request.decision}")
        store.save()
    return JSONResponse(public_state())


@app.post("/api/demo")
def load_demo(scenario: Literal["research", "technology", "creative"] = "research") -> JSONResponse:
    with store.lock:
        provider = store.session.model_provider
        model = store.session.model_name
        store.session = build_demo_session(scenario)
        store.session.model_provider = provider
        store.session.model_name = model
        store.pending_sources.clear()
        store.private_sources.clear()
        store.save()
    return JSONResponse(public_state())


@app.post("/api/reset")
def reset_session() -> JSONResponse:
    with store.lock:
        provider = store.session.model_provider
        model = store.session.model_name
        store.session = ProfileSession(model_provider=provider, model_name=model)
        store.pending_sources.clear()
        store.private_sources.clear()
        store.save()
    return JSONResponse(public_state())


@app.get("/api/export")
def export_session() -> JSONResponse:
    response = JSONResponse(store.session.model_dump(mode="json"))
    response.headers["Content-Disposition"] = "attachment; filename=profilekit-session.json"
    return response


@app.get("/api/export/pdf")
def export_profile_pdf() -> Response:
    if not store.session.record.items:
        raise HTTPException(status_code=400, detail="Add or load profile content before exporting a PDF.")
    pdf = build_profile_pdf(
        store.session.record,
        store.session.profile_theme,
        store.session.accent_color,
        store.session.font_style,
        store.session.layout_density,
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=profilekit-profile.pdf"},
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Start ProfileKit, the privacy-first profile builder")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(f"http://{args.host}:{args.port}")).start()
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
