from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import run_turn
from .models import ProfileSession
from .providers import default_selection
from .sources import SourceError, build_source_bundle


WELCOME = """I can help turn your approved information into an editable, single-page profile,
poster, resume-style page, business card, researcher profile, or project sheet.

ProfileKit organizes information you provide, but it does not independently verify your
statements, decide what you should disclose, publish your work, or confirm image and link
permissions. You remain responsible for reviewing facts, privacy choices, permissions,
accessibility, and final use.

To begin:
1. What are you creating?
2. Who will view it?
3. What is the occasion or use case?
4. Which source materials should I use?
"""


def load_session(path: Path) -> ProfileSession:
    if not path.exists():
        provider, model = default_selection()
        return ProfileSession(model_provider=provider, model_name=model)
    return ProfileSession.model_validate_json(path.read_text(encoding="utf-8"))


def save_session(path: Path, session: ProfileSession) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(session.model_dump_json(indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ProfileKit conversational agent")
    parser.add_argument("--session", type=Path, default=Path(".profilekit/session.json"))
    parser.add_argument("--reset", action="store_true", help="Start a new in-memory session")
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        default=[],
        help="User-approved source to inspect (repeat for multiple files)",
    )
    args = parser.parse_args()

    if args.reset:
        provider, model = default_selection()
        session = ProfileSession(model_provider=provider, model_name=model)
    else:
        session = load_session(args.session)
    try:
        source_bundle = build_source_bundle(args.source)
    except SourceError as error:
        parser.error(str(error))
    sources_pending = bool(source_bundle)
    if not session.transcript:
        print(WELCOME)
    else:
        print(
            f"ProfileKit resumed at stage: {session.stage.value} "
            f"using {session.model_provider}/{session.model_name}"
        )

    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession saved.")
            break
        if not message:
            continue
        if message.lower() in {"quit", "exit", "/quit"}:
            break
        if sources_pending:
            message += source_bundle
            sources_pending = False
        try:
            session, reply = run_turn(session, message)
        except Exception as error:
            print(f"\nProfileKit could not complete the turn: {error}")
            continue
        save_session(args.session, session)
        print(f"\nProfileKit: {reply}")

    save_session(args.session, session)


if __name__ == "__main__":
    main()
