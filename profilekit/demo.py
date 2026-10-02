from __future__ import annotations

from .models import (
    ImageItem,
    ItemStatus,
    LinkItem,
    ProfileItem,
    ProfileMetadata,
    ProfileRecord,
    ProfileSession,
    TranscriptMessage,
    WorkflowStage,
)


def build_demo_session(scenario: str = "research") -> ProfileSession:
    """Return a fictional, non-sensitive scenario for classroom demonstrations."""
    record = ProfileRecord(
        profile_metadata=ProfileMetadata(
            audience="Faculty and student researchers",
            occasion="Campus research showcase",
            purpose="Introduce a student research interest and one class project",
            output_type="Researcher profile",
            output_size="US Letter, one page",
            tone="Clear, modest, and approachable",
            language="English",
            accessibility_requirements="Readable from a projected classroom screen",
            visual_preferences="Structured layout with a blue accent",
            privacy_restrictions="No phone number or home address",
        ),
        items=[
            ProfileItem(
                category="identity",
                label="Preferred name",
                value="Lin Chen",
                status=ItemStatus.CONFIRMED,
                source="Demo resume",
            ),
            ProfileItem(
                category="identity",
                label="Current role",
                value="Graduate student in information science",
                status=ItemStatus.CONFIRMED,
                source="Demo resume",
            ),
            ProfileItem(
                category="introduction",
                label="Short introduction",
                value="Explores how people understand and use public information systems.",
                status=ItemStatus.SUGGESTED_WORDING,
                source="Demo approved research-interest statement",
            ),
            ProfileItem(
                category="project",
                label="Class project",
                value="Designed an interview-coding workflow, organized recurring themes, and presented a concise evidence summary for a course research study.",
                status=ItemStatus.SUGGESTED_WORDING,
                source="Demo project notes",
            ),
            ProfileItem(
                category="education",
                label="Education",
                value="M.S. student in Information Science, Example University, expected 2027",
                status=ItemStatus.CONFIRMED,
                source="Demo resume",
            ),
            ProfileItem(
                category="skills",
                label="Methods",
                value="Qualitative coding, usability testing, information organization, and research synthesis",
                status=ItemStatus.CONFIRMED,
                source="Demo resume and course notes",
            ),
            ProfileItem(
                category="experience",
                label="Selected experience",
                value="Student research assistant supporting literature review, participant coordination, and thematic analysis.",
                status=ItemStatus.SUGGESTED_WORDING,
                source="Demo resume",
            ),
            ProfileItem(
                category="contact",
                label="Professional email",
                value="lin.chen@example.edu",
                status=ItemStatus.NEEDS_CONFIRMATION,
                source="Demo resume",
                privacy="Requires explicit approval for this audience",
            ),
        ],
        links=[
            LinkItem(
                value="https://example.edu/lin-chen",
                purpose="Institutional profile",
                audience="Campus research showcase",
                authorization_status="unknown",
                source="Demo resume",
            )
        ],
        images_and_logos=[
            ImageItem(
                description="Optional portrait placeholder",
                intended_use="Profile header",
                ownership_or_permission="unknown",
            )
        ],
        privacy_decisions=["Exclude home address", "Exclude phone number"],
        uncertainties=["Confirm whether the professional email may be displayed"],
        placeholders=["Optional approved methods list"],
        draft_status="profile_record_ready",
    )
    session = ProfileSession(
        stage=WorkflowStage.PROFILE_RECORD,
        model_provider="deepseek",
        model_name="deepseek-flash",
        profile_theme="modern",
        accent_color="#5667D8",
        font_style="hybrid",
        layout_density="balanced",
        record=record,
        transcript=[
            TranscriptMessage(
                role="assistant",
                content=(
                    "I reviewed the fictional demo materials and prepared a Personal Profile Record. "
                    "Use the controls beside each item to approve, revise, exclude, or restrict it."
                ),
            )
        ],
        audit_log=["demo -> personal_profile_record"],
    )
    if scenario == "research":
        return session

    examples = {
        "technology": {
            "name": "Maya Patel",
            "role": "Student developer and accessibility advocate",
            "intro": "Builds practical web tools that make campus information easier to find and use.",
            "project": "Built a searchable campus-resource prototype and tested navigation with five student volunteers; revised labels using their feedback.",
            "education": "B.S. student in Computer Science, Example University, expected 2027",
            "skills": "Python, JavaScript, accessible interface design, and usability testing",
            "experience": "Peer technology mentor helping students troubleshoot tools and document repeatable solutions.",
            "audience": "Internship reviewers and campus collaborators",
            "occasion": "Student technology showcase",
            "theme": "studio",
        },
        "creative": {
            "name": "Alex Rivera",
            "role": "Student designer and visual storyteller",
            "intro": "Turns complex community stories into clear, welcoming visual experiences.",
            "project": "Created a visual identity and information poster for a fictional neighborhood arts event, then refined the hierarchy after peer critique.",
            "education": "B.A. student in Graphic Design, Example University, expected 2027",
            "skills": "Editorial layout, illustration, typography, and audience research",
            "experience": "Student design volunteer producing event graphics and accessible social posts for campus clubs.",
            "audience": "Creative collaborators and course reviewers",
            "occasion": "Design portfolio showcase",
            "theme": "sunrise",
        },
    }
    if scenario not in examples:
        raise ValueError(f"Unknown demo scenario: {scenario}")
    example = examples[scenario]
    replacements = {
        "Preferred name": example["name"],
        "Current role": example["role"],
        "Short introduction": example["intro"],
        "Class project": example["project"],
        "Education": example["education"],
        "Methods": example["skills"],
        "Selected experience": example["experience"],
    }
    session.record.items = [
        item.model_copy(update={"value": replacements[item.label]})
        for item in session.record.items
        if item.label in replacements
    ]
    session.record.links = []
    session.record.profile_metadata.audience = example["audience"]
    session.record.profile_metadata.occasion = example["occasion"]
    session.record.profile_metadata.visual_preferences = f"Distinctive {example['theme']} layout with readable text"
    session.record.uncertainties = []
    session.profile_theme = example["theme"]
    session.accent_color = "#6557CF" if scenario == "technology" else "#D94F44"
    session.audit_log.append(f"fictional scenario selected: {scenario}")
    return session
