from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from .models import ItemStatus, ProfileRecord


THEMES: dict[str, dict[str, str]] = {
    "academic": {
        "label": "Academic",
        "description": "Structured and credible for research or course settings",
        "accent": "#147D70",
        "dark": "#17233D",
        "soft": "#E7F7F3",
    },
    "modern": {
        "label": "Modern",
        "description": "Bold color and clear blocks for a projected presentation",
        "accent": "#5B5BD6",
        "dark": "#20213A",
        "soft": "#EEEEFF",
    },
    "minimal": {
        "label": "Minimal",
        "description": "Quiet typography and generous whitespace",
        "accent": "#2F6B5F",
        "dark": "#1F2528",
        "soft": "#F1F3F2",
    },
    "sunrise": {
        "label": "Sunrise",
        "description": "Warm coral energy for events and creative introductions",
        "accent": "#D94F44",
        "dark": "#462A44",
        "soft": "#FFF0E8",
    },
    "studio": {
        "label": "Studio",
        "description": "Violet and turquoise geometry for a vivid showcase",
        "accent": "#6557CF",
        "dark": "#211D4A",
        "soft": "#F0EEFF",
    },
    "editorial": {
        "label": "Editorial",
        "description": "Cream paper and serif typography for a polished story",
        "accent": "#A23D54",
        "dark": "#352638",
        "soft": "#F8F0E9",
    },
}


def theme_catalog() -> list[dict[str, str]]:
    return [{"id": key, **value} for key, value in THEMES.items()]


def _is_visible(item: Any) -> bool:
    if item.user_decision in {"exclude", "restrict"}:
        return False
    if item.user_decision == "include":
        return True
    return item.status != ItemStatus.NEEDS_CONFIRMATION


def _find_item(items: list[Any], *needles: str) -> Any | None:
    lowered = tuple(needle.lower() for needle in needles)
    for item in items:
        haystack = f"{item.category} {item.label}".lower()
        if any(needle in haystack for needle in lowered):
            return item
    return None


def presentation_payload(
    record: ProfileRecord,
    theme: str,
    accent_color: str | None = None,
    font_style: str = "hybrid",
    layout_density: str = "balanced",
) -> dict[str, Any]:
    visible = [item for item in record.items if _is_visible(item)]
    name_item = _find_item(visible, "preferred name", "full name", "name")
    role_item = _find_item(visible, "current role", "headline", "role", "title")
    intro_item = _find_item(visible, "introduction", "summary", "bio")

    featured_ids = {id(item) for item in (name_item, role_item, intro_item) if item}
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in visible:
        if id(item) in featured_ids:
            continue
        heading = item.category.replace("_", " ").title() or "Profile"
        grouped.setdefault(heading, []).append({"label": item.label, "value": item.value})

    approved_links = [
        {"label": link.purpose or "Profile link", "value": link.value}
        for link in record.links
        if link.user_approval
    ]
    if approved_links:
        grouped["Links"] = approved_links

    metadata = record.profile_metadata
    return {
        "theme": theme if theme in THEMES else "academic",
        "accent_color": accent_color or THEMES.get(theme, THEMES["academic"])["accent"],
        "font_style": font_style,
        "layout_density": layout_density,
        "title": name_item.value if name_item else "Your Name",
        "role": role_item.value if role_item else (metadata.output_type or "Personal Profile"),
        "introduction": intro_item.value if intro_item else (metadata.purpose or "Your approved introduction will appear here."),
        "sections": [{"heading": heading, "items": items} for heading, items in grouped.items()],
        "context": " - ".join(value for value in (metadata.occasion, metadata.audience) if value),
        "is_placeholder": not bool(visible),
    }


def _paragraph(canvas: Canvas, text: str, style: ParagraphStyle, x: float, y: float, width: float) -> float:
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    _, height = paragraph.wrap(width, 10 * inch)
    paragraph.drawOn(canvas, x, y - height)
    return y - height


def build_profile_pdf(
    record: ProfileRecord,
    theme: str = "academic",
    accent_color: str | None = None,
    font_style: str = "hybrid",
    layout_density: str = "balanced",
) -> bytes:
    payload = presentation_payload(record, theme, accent_color, font_style, layout_density)
    colors = THEMES[payload["theme"]]
    accent = HexColor(payload["accent_color"])
    dark = HexColor(colors["dark"])
    soft = HexColor(colors["soft"])
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=letter, pageCompression=1)
    width, height = letter
    margin = 0.68 * inch
    content_width = width - 2 * margin

    canvas.setTitle(f"ProfileKit - {payload['title']}")
    canvas.setAuthor("ProfileKit")
    canvas.setFillColor(soft if payload["theme"] in {"minimal", "editorial"} else white)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)

    header_height = 1.48 * inch if payload["theme"] in {"minimal", "editorial"} else 1.72 * inch
    canvas.setFillColor(soft if payload["theme"] in {"editorial", "minimal"} else dark)
    canvas.rect(0, height - header_height, width, header_height, fill=1, stroke=0)
    if payload["theme"] == "sunrise":
        canvas.setFillColor(HexColor("#F4A261"))
        canvas.circle(width - 0.25 * inch, height - 0.26 * inch, 0.88 * inch, fill=1, stroke=0)
        canvas.setFillColor(accent)
        canvas.circle(width - 0.08 * inch, height - 1.35 * inch, 0.62 * inch, fill=1, stroke=0)
    elif payload["theme"] == "studio":
        canvas.setFillColor(accent)
        canvas.rect(width - 1.72 * inch, height - header_height, 1.72 * inch, header_height, fill=1, stroke=0)
        canvas.setFillColor(HexColor("#55D6D2"))
        canvas.circle(width - 0.3 * inch, height - 0.4 * inch, 0.55 * inch, fill=1, stroke=0)
    elif payload["theme"] == "editorial":
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(3)
        canvas.line(margin, height - header_height + 0.10 * inch, width - margin, height - header_height + 0.10 * inch)
    else:
        canvas.setFillColor(accent)
        accent_width = 0.15 * inch if payload["theme"] == "academic" else 0.28 * inch
        canvas.rect(0, height - header_height, accent_width, header_height, fill=1, stroke=0)

    title_font = "Times-Bold" if payload["font_style"] in {"serif", "hybrid"} else "Helvetica-Bold"
    body_font = "Times-Roman" if payload["font_style"] == "serif" else "Helvetica"
    canvas.setFillColor(dark if payload["theme"] in {"editorial", "minimal"} else white)
    canvas.setFont(title_font, 26 if len(payload["title"]) < 30 else 21)
    canvas.drawString(margin, height - 0.72 * inch, payload["title"][:80])
    role_color = {
        "academic": HexColor("#9EE8DC"),
        "modern": HexColor("#C5C5FF"),
        "minimal": accent,
        "studio": HexColor("#A8F1ED"),
        "sunrise": HexColor("#FFD5B3"),
    }.get(payload["theme"], accent)
    canvas.setFillColor(role_color)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(margin, height - 1.03 * inch, payload["role"][:110].upper())
    if payload["context"]:
        canvas.setFillColor(HexColor("#6F5B63") if payload["theme"] in {"editorial", "minimal"} else HexColor("#D8E0EC"))
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(margin, height - 1.30 * inch, payload["context"][:125])

    y = height - header_height - 0.38 * inch
    density_scale = {"compact": 0.88, "balanced": 1.0, "airy": 1.08}[payload["layout_density"]]
    intro_style = ParagraphStyle(
        "intro", fontName=body_font, fontSize=12.2, leading=17 * density_scale,
        textColor=dark, alignment=TA_LEFT,
    )
    y = _paragraph(canvas, payload["introduction"], intro_style, margin, y, content_width)
    y -= 0.24 * inch
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(1.4)
    canvas.line(margin, y, margin + content_width, y)
    y -= 0.30 * inch

    heading_style = ParagraphStyle(
        "heading", fontName="Helvetica-Bold", fontSize=8.5, leading=10,
        textColor=accent, spaceAfter=4,
    )
    item_style = ParagraphStyle(
        "item", fontName=body_font, fontSize=9.5, leading=13 * density_scale, textColor=dark,
    )
    label_style = ParagraphStyle(
        "label", fontName="Helvetica-Bold", fontSize=7.2, leading=9,
        textColor=HexColor("#667085"),
    )

    displayed_items = 0
    total_items = sum(len(section["items"]) for section in payload["sections"])
    for section in payload["sections"][:6]:
        if y < 1.0 * inch:
            break
        y = _paragraph(canvas, section["heading"].upper(), heading_style, margin, y, content_width)
        y -= 0.06 * inch
        for item in section["items"][:4]:
            if y < 0.82 * inch:
                break
            y = _paragraph(canvas, item["label"].upper(), label_style, margin, y, content_width)
            y -= 0.02 * inch
            y = _paragraph(canvas, item["value"], item_style, margin, y, content_width)
            displayed_items += 1
            y -= 0.15 * inch
        y -= 0.07 * inch

    footer = ("PROFILEKIT - CONTENT SHORTENED TO FIT ONE PAGE" if displayed_items < total_items
              else "PROFILEKIT - PRIVACY-REVIEWED ONE-PAGE PROFILE")
    canvas.setFillColor(HexColor("#7B8493"))
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.drawString(margin, 0.43 * inch, footer)
    page_mark = "1 / 1"
    canvas.drawString(width - margin - stringWidth(page_mark, "Helvetica-Bold", 6.8), 0.43 * inch, page_mark)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()
