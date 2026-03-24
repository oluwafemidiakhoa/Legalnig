import unittest

from legal_mvp.answers import build_answer_draft
from legal_mvp.matters import build_matter_for_answer, build_matter_from_intake
from legal_mvp.workflows import build_intake_request, create_record


class MatterTests(unittest.TestCase):
    def test_build_matter_from_intake_reuses_record_matter_id(self):
        request = build_intake_request(
            {
                "founder_name": "Amina Yusuf",
                "business_name": "Northstar Health",
                "entity_type": "Private Company Limited by Shares",
                "sector": "health",
                "use_case": "Incorporate the business and prepare an employment packet for first hires.",
                "contact_email": "amina@example.com",
                "consent": True,
            }
        )
        record = create_record(request)
        matter = build_matter_from_intake(record)
        self.assertEqual(matter.id, record.matter_id)
        self.assertEqual(matter.jurisdiction, "Nigeria")
        self.assertEqual(len(matter.tasks), len(record.workflow))
        self.assertTrue(all(task.source_record_id == record.id for task in matter.tasks))

    def test_build_matter_for_answer_creates_review_artifacts(self):
        draft = build_answer_draft(
            "What should I review before onboarding a first employee?",
            {
                "answer_status": "supported",
                "answer_text": "Collect role details and route for legal review.",
                "risk_level": "medium",
                "requires_lawyer_review": True,
                "recommended_actions": ["Collect role details."],
                "follow_up_questions": [],
                "citations": [],
            },
            "gpt-5-mini",
        )
        matter = build_matter_for_answer(draft["question"], draft)
        self.assertEqual(matter.jurisdiction, "Nigeria")
        self.assertEqual(matter.source_record_type, "answer_draft")
        self.assertEqual(matter.source_record_id, draft["id"])
        self.assertEqual(len(matter.tasks), 1)
        self.assertEqual(matter.tasks[0].source_record_id, draft["id"])
        self.assertEqual(len(matter.approvals), 1)
        self.assertEqual(len(matter.document_versions), 1)


if __name__ == "__main__":
    unittest.main()
