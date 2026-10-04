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
    payload = {
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
    return _fit_one_page(payload)


def _text_height(text: str, font: str, size: float, leading: float, width: float) -> float:
    style = ParagraphStyle("measure", fontName=font, fontSize=size, leading=leading)
    paragraph = Paragraph(escape(text).replace("\n", "<br/>"), style)
    return paragraph.wrap(width, 10 * inch)[1]


def _one_line(text: str, font: str, size: float, width: float) -> str:
    text = " ".join(text.split())
    if stringWidth(text, font, size) <= width:
        return text
    while text and stringWidth(text + "...", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "..."


def _limit_lines(text: str, font: str, size: float, leading: float, width: float, lines: int) -> tuple[str, bool]:
    if _text_height(text, font, size, leading, width) <= lines * leading:
        return text, False
    words = text.split()
    low, high = 1, len(words)
    best = ""
    while low <= high:
        middle = (low + high) // 2
        candidate = " ".join(words[:middle]).rstrip(".,;: ") + "..."
        if _text_height(candidate, font, size, leading, width) <= lines * leading:
            best = candidate
            low = middle + 1
        else:
            high = middle - 1
    if best:
        return best, True
    # A single unbroken token still needs a finite, visible prefix.
    return _one_line(text, font, size, width), True


def _fit_one_page(payload: dict[str, Any]) -> dict[str, Any]:
    """Choose one deterministic content/layout plan for both preview and PDF."""
    width, height = letter
    margin = 0.68 * inch
    content_width = width - 2 * margin
    header_height = (1.48 if payload["theme"] in {"minimal", "editorial"} else 1.72) * inch
    body_font = "Times-Roman" if payload["font_style"] == "serif" else "Helvetica"
    title_font = "Times-Bold" if payload["font_style"] in {"serif", "hybrid"} else "Helvetica-Bold"
    title_size = 26 if len(payload["title"]) < 30 else 21
    title = _one_line(payload["title"], title_font, title_size, content_width)
    role = _one_line(payload["role"].upper(), "Helvetica-Bold", 10, content_width)
    context = _one_line(payload["context"], "Helvetica", 8.5, content_width)
    payload["header_shortened"] = (title != payload["title"] or role != payload["role"].upper()
                                   or context != payload["context"])
    payload["title"], payload["role"], payload["context"] = title, role, context
    density = {"compact": 0.88, "balanced": 1.0, "airy": 1.08}[payload["layout_density"]]
    source_sections = []
    for section in payload["sections"]:
        planned_items = []
        for item in section["items"]:
            value, shortened = _limit_lines(item["value"], body_font, 9.5 * 0.84,
                                            13 * density * 0.84, content_width, 6)
            planned_items.append({**item, "value": value, "_shortened": shortened})
        source_sections.append({"heading": section["heading"], "items": planned_items})
    total_items = sum(len(section["items"]) for section in source_sections)
    intro = payload["introduction"]
    intro_shortened = False
    # The introduction is capped before fitting entries, so one long paragraph
    # cannot consume the entire page. The original remains in the editable record.
    intro, intro_shortened = _limit_lines(intro, body_font, 12.2, 17 * density, content_width, 6)

    chosen_sections: list[dict[str, Any]] = []
    chosen_scale = 0.84
    for scale in (1.0, 0.94, 0.88, 0.84):
        y = height - header_height - 0.38 * inch
        y -= _text_height(intro, body_font, 12.2 * scale, 17 * density * scale, content_width)
        y -= 0.54 * inch * scale
        fitted: list[dict[str, Any]] = []
        stop = False
        for section in source_sections:
            section_items: list[dict[str, str]] = []
            heading_height = _text_height(section["heading"].upper(), "Helvetica-Bold", 8.5 * scale, 10 * scale, content_width)
            for item in section["items"]:
                item_height = (
                    _text_height(item["label"].upper(), "Helvetica-Bold", 7.2 * scale, 9 * scale, content_width)
                    + _text_height(item["value"], body_font, 9.5 * scale, 13 * density * scale, content_width)
                    + (0.17 * inch) * scale
                )
                needed = item_height + (heading_height + 0.06 * inch * scale if not section_items else 0)
                if y - needed < 0.82 * inch:
                    stop = True
                    break
                y -= needed
                section_items.append(item)
            if section_items:
                fitted.append({"heading": section["heading"], "items": section_items})
                y -= 0.07 * inch * scale
            if stop:
                break
        chosen_sections, chosen_scale = fitted, scale
        if sum(len(section["items"]) for section in fitted) == total_items:
            break

    shown = sum(len(section["items"]) for section in chosen_sections)
    shortened_items = sum(item.pop("_shortened") for section in chosen_sections for item in section["items"])
    payload["sections"] = chosen_sections
    payload["introduction"] = intro
    payload["layout_scale"] = chosen_scale
    payload["omitted_items"] = total_items - shown
    payload["shortened_items"] = shortened_items
    payload["introduction_shortened"] = intro_shortened
    return payload


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
    canvas.drawString(margin, height - 0.72 * inch, payload["title"])
    role_color = {
        "academic": HexColor("#9EE8DC"),
        "modern": HexColor("#C5C5FF"),
        "minimal": accent,
        "studio": HexColor("#A8F1ED"),
        "sunrise": HexColor("#FFD5B3"),
    }.get(payload["theme"], accent)
    canvas.setFillColor(role_color)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(margin, height - 1.03 * inch, payload["role"])
    if payload["context"]:
        canvas.setFillColor(HexColor("#6F5B63") if payload["theme"] in {"editorial", "minimal"} else HexColor("#D8E0EC"))
        canvas.setFont("Helvetica", 8.5)
        canvas.drawString(margin, height - 1.30 * inch, payload["context"])

    y = height - header_height - 0.38 * inch
    density_scale = {"compact": 0.88, "balanced": 1.0, "airy": 1.08}[payload["layout_density"]]
    scale = payload["layout_scale"]
    intro_style = ParagraphStyle(
        "intro", fontName=body_font, fontSize=12.2 * scale, leading=17 * density_scale * scale,
        textColor=dark, alignment=TA_LEFT,
    )
    y = _paragraph(canvas, payload["introduction"], intro_style, margin, y, content_width)
    y -= 0.24 * inch * scale
    canvas.setStrokeColor(accent)
    canvas.setLineWidth(1.4)
    canvas.line(margin, y, margin + content_width, y)
    y -= 0.30 * inch * scale

    heading_style = ParagraphStyle(
        "heading", fontName="Helvetica-Bold", fontSize=8.5 * scale, leading=10 * scale,
        textColor=accent, spaceAfter=4,
    )
    item_style = ParagraphStyle(
        "item", fontName=body_font, fontSize=9.5 * scale, leading=13 * density_scale * scale, textColor=dark,
    )
    label_style = ParagraphStyle(
        "label", fontName="Helvetica-Bold", fontSize=7.2 * scale, leading=9 * scale,
        textColor=HexColor("#667085"),
    )

    for section in payload["sections"]:
        y = _paragraph(canvas, section["heading"].upper(), heading_style, margin, y, content_width)
        y -= 0.06 * inch * scale
        for item in section["items"]:
            y = _paragraph(canvas, item["label"].upper(), label_style, margin, y, content_width)
            y -= 0.02 * inch * scale
            y = _paragraph(canvas, item["value"], item_style, margin, y, content_width)
            y -= 0.15 * inch * scale
        y -= 0.07 * inch * scale

    footer = ("PROFILEKIT - CONTENT SHORTENED TO FIT ONE PAGE" if payload["omitted_items"] or payload["shortened_items"] or payload["introduction_shortened"] or payload["header_shortened"]
              else "PROFILEKIT - PRIVACY-REVIEWED ONE-PAGE PROFILE")
    canvas.setFillColor(HexColor("#7B8493"))
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.drawString(margin, 0.43 * inch, footer)
    page_mark = "1 / 1"
    canvas.drawString(width - margin - stringWidth(page_mark, "Helvetica-Bold", 6.8), 0.43 * inch, page_mark)
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()
