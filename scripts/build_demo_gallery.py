"""Regenerate fictional, safe-to-share one-page ProfileKit examples."""

from pathlib import Path

from profilekit.demo import build_demo_session
from profilekit.profile_document import build_profile_pdf


def main() -> None:
    output = Path(__file__).resolve().parents[1] / "output" / "pdf"
    output.mkdir(parents=True, exist_ok=True)
    for scenario in ("research", "technology", "creative"):
        demo = build_demo_session(scenario)
        pdf = build_profile_pdf(
            demo.record, demo.profile_theme, demo.accent_color,
            demo.font_style, demo.layout_density,
        )
        path = output / f"profilekit-{scenario}-demo.pdf"
        path.write_bytes(pdf)
        if scenario == "research":
            (output / "profilekit-demo-profile.pdf").write_bytes(pdf)
        print(path)


if __name__ == "__main__":
    main()
