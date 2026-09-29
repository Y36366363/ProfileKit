#!/usr/bin/env python3
"""Safely test local API credentials without printing secrets or model output."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import certifi


@dataclass
class Result:
    provider: str
    authentication: str
    generation: str
    detail: str


def load_dotenv(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    seen: set[str] = set()
    duplicates: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name in seen:
            duplicates.append(name)
        seen.add(name)
        values[name] = value
    return values, sorted(set(duplicates))


def request_json(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers)
    if payload is not None:
        request.method = "POST"
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
        body = response.read()
        parsed = json.loads(body) if body else {}
        return response.status, parsed


def safe_failure(error: Exception) -> str:
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code} {error.reason}"
    if isinstance(error, urllib.error.URLError):
        return f"network error: {error.reason}"
    return f"{type(error).__name__}: request failed"


def test_openai(key: str, generate: bool, env: dict[str, str]) -> Result:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        status, body = request_json("https://api.openai.com/v1/models", headers=headers)
        model_ids = {item.get("id") for item in body.get("data", [])}
    except Exception as error:
        return Result("OpenAI", "failed", "not run", safe_failure(error))
    model = env.get("OPENAI_MODEL", "gpt-6-luna")
    if not generate:
        return Result("OpenAI", "passed", "skipped", f"HTTP {status}; {len(model_ids)} models visible")
    try:
        request_json(
            "https://api.openai.com/v1/responses",
            headers=headers,
            payload={
                "model": model,
                "input": "Reply with exactly: OK",
                "max_output_tokens": 16,
                "store": False,
            },
        )
        return Result("OpenAI", "passed", "passed", f"model={model}")
    except Exception as error:
        visibility = "visible" if model in model_ids else "not listed"
        return Result("OpenAI", "passed", "failed", f"model={model} ({visibility}); {safe_failure(error)}")


def test_deepseek(key: str, generate: bool, env: dict[str, str]) -> Result:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    try:
        status, body = request_json("https://api.deepseek.com/models", headers=headers)
        model_ids = {item.get("id") for item in body.get("data", [])}
    except Exception as error:
        return Result("DeepSeek", "failed", "not run", safe_failure(error))
    model = env.get("DEEPSEEK_MODEL", "deepseek-flash")
    if not generate:
        return Result("DeepSeek", "passed", "skipped", f"HTTP {status}; {len(model_ids)} models visible")
    try:
        request_json(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            payload={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 16,
                "stream": False,
            },
        )
        return Result("DeepSeek", "passed", "passed", f"model={model}")
    except Exception as error:
        visibility = "visible" if model in model_ids else "not listed"
        return Result("DeepSeek", "passed", "failed", f"model={model} ({visibility}); {safe_failure(error)}")


def test_gemini(key: str, generate: bool, env: dict[str, str]) -> Result:
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
    try:
        status, body = request_json(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers=headers,
        )
        models = body.get("models", [])
        model_names = {item.get("name", "").removeprefix("models/") for item in models}
    except Exception as error:
        return Result("Gemini", "failed", "not run", safe_failure(error))
    requested = env.get("GEMINI_MODEL", "gemini-3.5-flash")
    capable = [
        item.get("name", "").removeprefix("models/")
        for item in models
        if "generateContent" in item.get("supportedGenerationMethods", [])
    ]
    model = requested if requested in model_names else next(
        (name for name in capable if "flash" in name and "preview" not in name),
        capable[0] if capable else requested,
    )
    if not generate:
        return Result("Gemini", "passed", "skipped", f"HTTP {status}; {len(models)} models visible")
    try:
        request_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers=headers,
            payload={
                "contents": [{"parts": [{"text": "Reply with exactly: OK"}]}],
                "generationConfig": {"maxOutputTokens": 16},
            },
        )
        chosen = "requested" if model == requested else "discovered fallback"
        return Result("Gemini", "passed", "passed", f"model={model} ({chosen})")
    except Exception as error:
        return Result("Gemini", "passed", "failed", f"model={model}; {safe_failure(error)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--generate", action="store_true", help="Also make one minimal generation request per provider")
    args = parser.parse_args()

    if not args.env_file.is_file():
        parser.error(f"Environment file not found: {args.env_file}")
    file_values, duplicates = load_dotenv(args.env_file)
    env = {**file_values, **os.environ}
    if duplicates:
        print("Warning: duplicate variables (last value used): " + ", ".join(duplicates))

    checks = [
        ("OPENAI_API_KEY", test_openai),
        ("DEEPSEEK_API_KEY", test_deepseek),
        ("GEMINI_API_KEY", test_gemini),
    ]
    results: list[Result] = []
    for variable, check in checks:
        key = env.get(variable, "").strip()
        if not key:
            results.append(Result(variable.removesuffix("_API_KEY").title(), "missing", "not run", f"{variable} is empty"))
            continue
        results.append(check(key, args.generate, env))

    print("Provider | Authentication | Generation | Detail")
    print("--- | --- | --- | ---")
    for result in results:
        print(f"{result.provider} | {result.authentication} | {result.generation} | {result.detail}")
    return 0 if all(r.authentication == "passed" and r.generation != "failed" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
