from __future__ import annotations

import os
from pathlib import Path


def load_env_file(path: Path, *, override: bool = False) -> list[str]:
    """Load simple KEY=VALUE pairs without logging values; return duplicate names."""
    if not path.is_file():
        return []
    seen: set[str] = set()
    duplicates: set[str] = set()
    file_values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip().removeprefix("export ").strip()
        if not name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if name in seen:
            duplicates.add(name)
        seen.add(name)
        file_values[name] = value
    for name, value in file_values.items():
        if override or name not in os.environ:
            os.environ[name] = value
    return sorted(duplicates)
