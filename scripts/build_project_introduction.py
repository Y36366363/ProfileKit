from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "docs" / "ProfileKit_Project_Introduction.docx"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_borders(cell, color: str = "D9D9D9") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:color"), color)
        borders.append(element)


def set_cell_margins(cell, top: int = 110, start: int = 120, bottom: int = 110, end: int = 120) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for key, value in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = OxmlElement(f"w:{key}")
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")
        margins.append(node)


def set_run_font(run, name: str = "Aptos", size: float | None = None, bold: bool | None = None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), name)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    set_run_font(run, size=9)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instruction, end])


def remove_paragraph_border(paragraph_or_style) -> None:
    p_pr = paragraph_or_style._element.get_or_add_pPr()
    border = p_pr.find(qn("w:pBdr"))
    if border is not None:
        p_pr.remove(border)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    paragraph = doc.add_heading(text, level=level)
    paragraph.paragraph_format.keep_with_next = True


def add_body(doc: Document, text: str, *, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.keep_together = True
    if bold_lead and text.startswith(bold_lead):
        lead = paragraph.add_run(bold_lead)
        lead.bold = True
        paragraph.add_run(text[len(bold_lead):])
    else:
        paragraph.add_run(text)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.add_run(item)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.width = Inches(widths[index])
        set_cell_shading(cell, "1F3A5F")
        set_cell_borders(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = paragraph.add_run(header)
        run.font.color.rgb = RGBColor(255, 255, 255)
        set_run_font(run, size=9, bold=True)
    for row_index, values in enumerate(rows):
        row = table.add_row()
        cant_split = OxmlElement("w:cantSplit")
        row._tr.get_or_add_trPr().append(cant_split)
        cells = row.cells
        for index, value in enumerate(values):
            cell = cells[index]
            cell.width = Inches(widths[index])
            set_cell_borders(cell)
            set_cell_margins(cell)
            if row_index % 2:
                set_cell_shading(cell, "F2F6FA")
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            run = paragraph.add_run(value)
            set_run_font(run, size=9)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def build_document() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = Document()
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.72)
    section.bottom_margin = Inches(0.68)
    section.left_margin = Inches(0.82)
    section.right_margin = Inches(0.82)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Aptos")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Aptos")
    normal.font.size = Pt(10.8)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.12
    for style_name, size in (("Title", 28), ("Heading 1", 18), ("Heading 2", 13)):
        style = styles[style_name]
        style.font.name = "Aptos Display" if style_name != "Normal" else "Aptos"
        style._element.rPr.rFonts.set(qn("w:ascii"), style.font.name)
        style._element.rPr.rFonts.set(qn("w:hAnsi"), style.font.name)
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.font.bold = style_name != "Title"
    styles["Title"].font.bold = True
    styles["Title"].paragraph_format.space_after = Pt(12)
    remove_paragraph_border(styles["Title"])
    styles["Heading 1"].paragraph_format.space_before = Pt(16)
    styles["Heading 1"].paragraph_format.space_after = Pt(7)
    styles["Heading 2"].paragraph_format.space_before = Pt(11)
    styles["Heading 2"].paragraph_format.space_after = Pt(5)

    header = section.header.paragraphs[0]
    header.text = "PROFILEKIT PROJECT DOCUMENTATION"
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header_run = header.runs[0]
    set_run_font(header_run, size=8.5, bold=True)
    header_run.font.color.rgb = RGBColor(0, 0, 0)
    add_page_number(section.footer.paragraphs[0])

    title = doc.add_paragraph(style="Title")
    title.add_run("ProfileKit Project Introduction and Demonstration Guide")
    remove_paragraph_border(title)
    subtitle = doc.add_paragraph()
    subtitle_run = subtitle.add_run("A privacy conscious local agent for editable single page personal profiles")
    set_run_font(subtitle_run, size=14)
    subtitle_run.font.color.rgb = RGBColor(0, 0, 0)
    meta = doc.add_paragraph()
    meta.add_run("Prepared for an in-class project demonstration\n")
    meta.add_run("Current implementation status: locally runnable and tested")
    for run in meta.runs:
        set_run_font(run, size=10)
        run.font.color.rgb = RGBColor(0, 0, 0)

    add_heading(doc, "Project Overview")
    add_body(
        doc,
        "ProfileKit is a local, privacy-conscious conversational agent that helps a user turn approved personal information into an editable, audience-specific, single-page profile. The current version runs as a local web application, accepts source documents and structured configuration, supports low-cost model selection, keeps a reviewable profile record, provides live visual customization, and exports a one-page PDF. The implementation is ready for a classroom demonstration, while the user remains responsible for reviewing facts, privacy choices, permissions, and final use.",
    )

    add_heading(doc, "Problem and Motivation")
    add_body(
        doc,
        "Creating a short personal profile is deceptively difficult. A resume may contain too much information, personal details may not be suitable for every audience, and a generic language model may invent stronger claims or overlook permissions. ProfileKit addresses this problem by separating evidence, suggested wording, privacy decisions, design preferences, and final export. It is designed for students, early-career professionals, researchers, applicants, and conference participants who need a concise profile without losing control of their information.",
    )

    add_heading(doc, "Project Goals")
    add_bullets(
        doc,
        [
            "Create an editable one-page profile from user-provided and user-approved information.",
            "Keep source evidence distinct from rewritten or suggested wording.",
            "Require explicit decisions for sensitive contact information, links, images, logos, and third-party details.",
            "Allow the user to control audience, purpose, tone, visual style, typography, color, and information density.",
            "Run locally for a reliable classroom demonstration and avoid exposing API keys to the browser.",
            "Prefer lower-cost models while retaining selectable higher-capability alternatives.",
        ],
    )

    doc.add_page_break()
    add_heading(doc, "Current User Experience")
    add_body(doc, "ProfileKit supports three complementary setup paths. A user can combine them in one session.")
    add_table(
        doc,
        ["Setup path", "How it works", "Best use"],
        [
            ["Source upload", "Upload a resume or personal-information DOCX, PDF, text file, or image. Extracted text enters agent review.", "Evidence-based generation from existing material"],
            ["Conversation", "Describe the audience, occasion, purpose, restrictions, and requested output in natural language.", "Iterative clarification and wording refinement"],
            ["Configuration", "Edit and upload default_config.json for deterministic profile and design setup without a model call.", "Fast classroom setup and repeatable demonstrations"],
            ["Customization panel", "Edit core profile content and visual preferences directly in the browser.", "Fine control over the live page and exported PDF"],
        ],
        [1.2, 3.45, 2.15],
    )

    add_heading(doc, "Workflow and Agent Behavior")
    add_body(
        doc,
        "The agent follows an explicit eleven-stage workflow: Intake, Source Review, Personal Profile Record, Privacy and Authorization Review, User Content Approval, Format Recommendation, Visual Direction Choice, Draft, Final Review, User Approval, and Editable Output. A controller prevents skipped approval gates and can return the session to an earlier stage when the user revises information.",
    )
    add_body(
        doc,
        "At each stage, the model receives the current profile record, recent conversation, current stage, and saved design preferences. It must distinguish confirmed facts, suggested wording, unresolved claims, and unsupported content. The runtime also blocks unsafe transitions, such as drafting with unresolved source conflicts or unauthorized links and images.",
    )

    add_heading(doc, "Privacy and User Control")
    add_bullets(
        doc,
        [
            "The local .env file stores API keys and is excluded from Git.",
            "API keys remain server-side and are never included in browser state.",
            "Home addresses are prohibited from public output, and phone numbers are excluded by default.",
            "Unconfirmed sensitive items do not appear in the live page or PDF.",
            "Each profile item can be included, excluded, revised, or restricted independently.",
            "Uploaded images and links are not treated as publicly authorized merely because they were supplied.",
            "The session is stored locally with user-only file permissions and is ignored by Git.",
        ],
    )

    add_heading(doc, "Model Strategy")
    add_body(
        doc,
        "DeepSeek Flash is the default model because it provides a lower-cost route for classroom use. OpenAI GPT-6 Luna is the preferred OpenAI alternative, with GPT-6 Sol and GPT-6 Astra available when a user deliberately chooses a higher-cost option. The interface shows the relative cost tier and disables choices whose API keys are unavailable. Gemini is currently covered by the API-key diagnostic but is not yet a conversation provider in the web interface.",
    )

    add_heading(doc, "Visual Output and Customization")
    add_body(
        doc,
        "The right side of the workspace switches between the reviewable record and a live US Letter preview. Academic, Modern, and Minimal templates are available. The user can also choose a custom accent color, serif, sans-serif, or hybrid typography, and compact, balanced, or airy density. The PDF generator uses the same saved profile and design preferences as the browser preview, reducing mismatch between what the user sees and what is exported.",
    )

    add_heading(doc, "Implementation Architecture")
    add_table(
        doc,
        ["Layer", "Responsibility", "Key technology"],
        [
            ["Web interface", "Uploads, conversation, item decisions, customization, live preview, and export controls", "HTML, CSS, JavaScript"],
            ["Local API", "Session state, file limits, validation, model routing, configuration import, and exports", "FastAPI and Pydantic"],
            ["Agent layer", "Structured turns, evidence-aware wording, questions, and workflow proposals", "DeepSeek compatible API and OpenAI Agents SDK"],
            ["Safety controller", "Stage order, approval gates, draft validation, and audit entries", "Deterministic Python rules"],
            ["Document layer", "DOCX/PDF extraction and one-page PDF generation", "python-docx, pypdf, ReportLab"],
            ["Local storage", "Private session state and configuration", "JSON files with restricted permissions"],
        ],
        [1.15, 3.75, 1.9],
    )

    add_heading(doc, "Validation Results")
    add_body(
        doc,
        "The current build passed 30 automated tests covering workflow transitions, privacy safeguards, source handling, model selection, configuration import, direct customization, theme persistence, DOCX upload, and single-page PDF export. Package checks and Python compilation also pass. A real local end-to-end test uploaded a fictional DOCX resume, used DeepSeek Flash to review it, advanced from Intake through Source Review to the Personal Profile Record, preserved the course-project context, and excluded the email when instructed. OpenAI GPT-6 Luna and DeepSeek Flash have both been exercised successfully through the application during development.",
    )
    add_table(
        doc,
        ["Capability", "Verification", "Result"],
        [
            ["Local web application", "Started on 127.0.0.1 and inspected in the browser", "Pass"],
            ["DOCX resume upload", "Extracted a fictional resume and queued it for model review", "Pass"],
            ["Configuration import", "Applied default_config.json without an API call", "Pass"],
            ["DeepSeek agent flow", "Completed two structured turns through the local API", "Pass"],
            ["Privacy filtering", "Excluded an unapproved email from preview and PDF", "Pass"],
            ["PDF export", "Rendered as one US Letter page and visually inspected", "Pass"],
            ["Automated test suite", "30 tests", "Pass"],
        ],
        [1.55, 4.25, 1.0],
    )

    add_heading(doc, "Known Limitations and Next Steps")
    add_bullets(
        doc,
        [
            "The interface does not yet provide drag-and-drop reordering of individual sections.",
            "The browser preview and PDF share data and preferences, but their typography engines can still produce small visual differences.",
            "Image content is intentionally not interpreted automatically; approved portrait placement remains future work.",
            "Gemini is not yet available in the conversation model selector.",
            "The PDF exporter prioritizes single-page safety and may omit lower-priority overflow content rather than create a second page; a future version should show an explicit omitted-content list.",
            "Formal accessibility compliance and institutional privacy requirements still require human review.",
        ],
    )

    add_heading(doc, "Conclusion")
    add_body(
        doc,
        "ProfileKit demonstrates a practical pattern for combining a language model with deterministic controls. The model helps interpret sources and refine language, while the application retains authority over workflow order, privacy decisions, state, and export. The current local version is suitable for a classroom demonstration because it includes a one-click fictional demo, a repeatable configuration path, editable controls, a live visual result, and a tested PDF output.",
    )

    doc.add_section(WD_SECTION.NEW_PAGE)
    add_heading(doc, "Appendix A Classroom Demonstration Script")
    add_body(doc, "Use this five-minute sequence to demonstrate the project without relying on personal information.")
    add_table(
        doc,
        ["Time", "Action", "What to explain"],
        [
            ["0:00", "Start the local app and open http://127.0.0.1:8765", "The application and session run locally; only selected prompts are sent to the chosen model provider."],
            ["0:30", "Click Load demo", "The case is fictional and safe for classroom projection."],
            ["1:00", "Switch between Review record and Live preview", "Evidence review and public presentation are separate views of the same state."],
            ["1:40", "Exclude or restrict one item", "The preview updates immediately and respects item-level privacy decisions."],
            ["2:15", "Open Customize", "Change audience, tone, accent color, typography, or density and apply the preferences."],
            ["3:10", "Switch Academic, Modern, and Minimal themes", "The user controls design instead of accepting one automatic result."],
            ["3:45", "Export PDF", "The exported document is one page and uses the saved privacy and design settings."],
            ["4:20", "Optionally upload default_config.json", "This provides a deterministic fallback if an external model is unavailable."],
        ],
        [0.65, 2.0, 4.15],
    )

    doc.add_page_break()
    add_heading(doc, "Appendix B Configuration Reference")
    add_body(
        doc,
        "The repository includes default_config.json. Keep that exact filename when uploading it through the web interface. The configuration replaces the existing profile record so a previous demo does not leak into the new result.",
    )
    add_table(
        doc,
        ["Object", "Fields", "Purpose"],
        [
            ["profile_metadata", "audience, occasion, purpose, output_type, output_size, tone, language, accessibility_requirements, visual_preferences, privacy_restrictions", "Defines the intended use and constraints"],
            ["profile", "name, role, introduction", "Sets the three primary elements in the page header and introduction"],
            ["items", "category, label, value, status, source, user_decision", "Adds education, projects, experience, skills, or other supported content"],
            ["design", "theme, accent_color, font_style, layout_density", "Controls presentation and PDF styling"],
        ],
        [1.25, 3.65, 1.9],
    )
    add_body(
        doc,
        "Accepted design values are academic, modern, or minimal for theme; serif, sans, or hybrid for font_style; and compact, balanced, or airy for layout_density. accent_color must be a six-digit hexadecimal color such as #147D70.",
    )

    add_heading(doc, "Appendix C Preclass Checklist")
    add_bullets(
        doc,
        [
            "Run python -m profilekit.preflight and confirm every local check passes.",
            "Open the local page before class and confirm the header shows DeepSeek Flash and local session.",
            "Click Load demo and confirm the preview displays a fictional profile rather than personal information.",
            "Open Customize once and verify the dialog fits the projector resolution.",
            "Export a PDF and confirm it opens as one page.",
            "Keep default_config.json available as a no-model fallback.",
            "Do not display .env or API keys during the presentation.",
            "If classroom internet is unavailable, demonstrate the built-in demo, configuration import, customization, privacy controls, themes, and PDF export; those functions do not require a model call.",
        ],
    )

    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build_document()
