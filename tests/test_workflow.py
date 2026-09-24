import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from profilekit.models import (
    AgentTurn,
    ImageItem,
    ItemStatus,
    LinkItem,
    ProfileItem,
    ProfileRecord,
    ProfileSession,
    WorkflowStage,
)
from profilekit.workflow import InvalidTransition, apply_turn, validate_transition
from profilekit.sources import SourceError, build_source_bundle, extract_source
from profilekit.env import load_env_file


def turn(stage: WorkflowStage, record: ProfileRecord | None = None, approval: str | None = None):
    return AgentTurn(
        assistant_message="Next",
        proposed_stage=stage,
        record=record or ProfileRecord(),
        approval_evidence=approval,
    )


class TransitionTests(unittest.TestCase):
    def test_agent_turn_has_strict_sdk_schema(self):
        from agents.agent_output import AgentOutputSchema

        schema = AgentOutputSchema(AgentTurn).json_schema()
        self.assertEqual(schema["type"], "object")

    def test_cannot_skip_stage(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(WorkflowStage.INTAKE, WorkflowStage.PROFILE_RECORD, None)

    def test_can_return_to_earlier_stage(self):
        validate_transition(WorkflowStage.DRAFT, WorkflowStage.PROFILE_RECORD, None)

    def test_content_requires_approval_before_format(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(
                WorkflowStage.CONTENT_APPROVAL,
                WorkflowStage.FORMAT_RECOMMENDATION,
                None,
            )

    def test_visual_choice_requires_approval_before_draft(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(WorkflowStage.VISUAL_DIRECTION, WorkflowStage.DRAFT, None)

    def test_final_export_requires_approval(self):
        with self.assertRaises(InvalidTransition):
            validate_transition(WorkflowStage.FINAL_APPROVAL, WorkflowStage.EDITABLE_OUTPUT, None)


class DraftSafetyTests(unittest.TestCase):
    def setUp(self):
        self.session = ProfileSession(stage=WorkflowStage.VISUAL_DIRECTION)

    def test_home_address_is_blocked(self):
        record = ProfileRecord(
            items=[
                ProfileItem(
                    category="identity",
                    label="home address",
                    value="123 Main St",
                    status=ItemStatus.USER_APPROVED,
                    user_decision="include",
                )
            ]
        )
        with self.assertRaises(InvalidTransition):
            apply_turn(self.session, "Use A", turn(WorkflowStage.DRAFT, record, "User chose A"))

    def test_unapproved_link_is_blocked(self):
        record = ProfileRecord(links=[LinkItem(value="https://example.com")])
        with self.assertRaises(InvalidTransition):
            apply_turn(self.session, "Use A", turn(WorkflowStage.DRAFT, record, "User chose A"))

    def test_unapproved_image_is_blocked(self):
        record = ProfileRecord(images_and_logos=[ImageItem(description="portrait")])
        with self.assertRaises(InvalidTransition):
            apply_turn(self.session, "Use A", turn(WorkflowStage.DRAFT, record, "User chose A"))

    def test_unresolved_conflict_is_blocked(self):
        record = ProfileRecord(conflicts=["Graduation date differs across sources"])
        with self.assertRaises(InvalidTransition):
            apply_turn(self.session, "Use A", turn(WorkflowStage.DRAFT, record, "User chose A"))

    def test_approved_record_can_enter_draft(self):
        record = ProfileRecord(
            items=[
                ProfileItem(
                    category="education",
                    label="degree",
                    value="MSIS",
                    status=ItemStatus.USER_APPROVED,
                    user_decision="include",
                )
            ],
            links=[LinkItem(value="https://example.com", user_approval=True)],
            images_and_logos=[ImageItem(description="portrait", user_approval=True)],
        )
        updated = apply_turn(
            self.session,
            "Use A and include the approved items",
            turn(WorkflowStage.DRAFT, record, "User chose A and approved the items"),
        )
        self.assertEqual(updated.stage, WorkflowStage.DRAFT)


class SourceTests(unittest.TestCase):
    def test_text_source_is_labeled_inspection_only(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "resume.txt"
            path.write_text("Supported a research project.", encoding="utf-8")
            bundle = build_source_bundle([path])
        self.assertIn("approved for inspection only", bundle)
        self.assertIn("SOURCE: resume.txt", bundle)
        self.assertIn("Supported a research project.", bundle)

    def test_image_is_not_interpreted_or_authorized(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "portrait.png"
            path.write_bytes(b"not-real-image-data")
            content = extract_source(path)
        self.assertIn("Do not infer its contents", content)
        self.assertIn("authorization needed", content)

    def test_unsupported_source_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "archive.zip"
            path.write_bytes(b"zip")
            with self.assertRaises(SourceError):
                extract_source(path)


class EnvironmentTests(unittest.TestCase):
    def test_env_loader_does_not_override_existing_value(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TEST_PROFILEKIT_KEY=file-value\n", encoding="utf-8")
            with patch.dict("os.environ", {"TEST_PROFILEKIT_KEY": "shell-value"}, clear=False):
                load_env_file(path)
                import os

                self.assertEqual(os.environ["TEST_PROFILEKIT_KEY"], "shell-value")

    def test_env_loader_reports_duplicates_and_uses_last_file_value(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TEST_PROFILEKIT_DUP=first\nTEST_PROFILEKIT_DUP=last\n", encoding="utf-8")
            with patch.dict("os.environ", {}, clear=True):
                duplicates = load_env_file(path)
                import os

                self.assertEqual(duplicates, ["TEST_PROFILEKIT_DUP"])
                self.assertEqual(os.environ["TEST_PROFILEKIT_DUP"], "last")


if __name__ == "__main__":
    unittest.main()
