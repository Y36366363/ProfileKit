from __future__ import annotations

import argparse
import json
import os
import tempfile
import threading
import webbrowser
from pathlib import Path
from typing import Literal

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import ROOT, run_turn
from .demo import build_demo_session
from .env import load_env_file
from .models import ItemStatus, ProfileSession
from .providers import available_catalog, default_selection, find_model, model_is_ready
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


class SessionStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = threading.Lock()
        self.session = self._load()
        self.pending_sources: list[str] = []

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
    return payload


@app.get("/api/session")
def get_session() -> JSONResponse:
    return JSONResponse(public_state())


@app.post("/api/chat")
def chat(request: ChatRequest) -> JSONResponse:
    with store.lock:
        message = request.message.strip()
        if store.pending_sources:
            message += "\n\n" + "\n\n---\n\n".join(store.pending_sources)
            store.pending_sources.clear()
        try:
            store.session, reply = run_turn(
                store.session,
                message,
                store.session.model_provider,
                store.session.model_name,
            )
        except Exception as error:
            raise HTTPException(
                status_code=422,
                detail=f"ProfileKit kept the current workflow stage: {error}",
            ) from error
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


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)) -> JSONResponse:
    if len(files) > 8:
        raise HTTPException(status_code=400, detail="Upload at most 8 files at a time.")
    accepted: list[str] = []
    with tempfile.TemporaryDirectory(prefix="profilekit-upload-") as directory:
        paths: list[Path] = []
        for upload_file in files:
            safe_name = Path(upload_file.filename or "source.txt").name
            data = await upload_file.read(MAX_SOURCE_BYTES + 1)
            if len(data) > MAX_SOURCE_BYTES:
                raise HTTPException(status_code=413, detail=f"{safe_name} exceeds the 5 MB limit.")
            path = Path(directory) / safe_name
            path.write_bytes(data)
            paths.append(path)
            accepted.append(safe_name)
        try:
            bundle = build_source_bundle(paths)
        except SourceError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
    with store.lock:
        store.pending_sources.append(bundle)
    return JSONResponse({"accepted": accepted, "session": public_state()})


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
def load_demo() -> JSONResponse:
    with store.lock:
        provider = store.session.model_provider
        model = store.session.model_name
        store.session = build_demo_session()
        store.session.model_provider = provider
        store.session.model_name = model
        store.pending_sources.clear()
        store.save()
    return JSONResponse(public_state())


@app.post("/api/reset")
def reset_session() -> JSONResponse:
    with store.lock:
        provider = store.session.model_provider
        model = store.session.model_name
        store.session = ProfileSession(model_provider=provider, model_name=model)
        store.pending_sources.clear()
        store.save()
    return JSONResponse(public_state())


@app.get("/api/export")
def export_session() -> JSONResponse:
    response = JSONResponse(store.session.model_dump(mode="json"))
    response.headers["Content-Disposition"] = "attachment; filename=profilekit-session.json"
    return response


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="assets")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ProfileKit classroom web app")
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
