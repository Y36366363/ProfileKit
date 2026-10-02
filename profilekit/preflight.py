from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from .agent import ROOT
from .configuration import load_profile_config
from .demo import build_demo_session
from .env import load_env_file
from .profile_document import THEMES, build_profile_pdf
from .providers import available_catalog


def main() -> None:
    load_env_file(ROOT / ".env")
    checks: list[tuple[str, bool, str]] = []
    checks.append(("Local environment file", (ROOT / ".env").exists(), ".env exists and remains private"))
    catalog = available_catalog()
    checks.append(("At least one model", any(option["ready"] for option in catalog), "a configured provider is available"))
    checks.append(("Default configuration", True, f"valid: {load_profile_config(ROOT / 'default_config.json').design.theme}"))
    checks.append(("Web interface", (ROOT / "profilekit" / "webui" / "index.html").exists(), "static interface found"))
    for scenario, name in (("research", "Lin Chen"), ("technology", "Maya Patel"), ("creative", "Alex Rivera")):
        demo = build_demo_session(scenario)
        for theme in THEMES:
            pdf = build_profile_pdf(demo.record, theme, THEMES[theme]["accent"], demo.font_style, demo.layout_density)
            reader = PdfReader(BytesIO(pdf))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            checks.append((f"{scenario}/{theme}", len(reader.pages) == 1 and name in text,
                           "one page with the expected profile"))
            checks.append((f"{scenario}/{theme} privacy", "lin.chen@example.edu" not in text,
                           "unconfirmed contact omitted"))

    print("ProfileKit classroom preflight")
    for label, passed, detail in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {label}: {detail}")
    if not all(passed for _, passed, _ in checks):
        raise SystemExit(1)
    print("Ready for the local classroom demonstration.")


if __name__ == "__main__":
    main()
