import unittest

from legal_mvp.answers import build_answer_draft, normalize_answer_payload, prepare_citation_context


class AnswerTests(unittest.TestCase):
    def test_prepare_citation_context_assigns_source_ids(self):
        citations = [
            {
                "title": "Employment onboarding review checklist",
                "issuer": "Labour counsel operations summary",
                "area": "employment",
                "jurisdiction": "Nigeria",
                "citation_label": "Counsel summary: Employment onboarding review",
                "snippet": "Example excerpt",
            }
        ]
        prepared = prepare_citation_context(citations)
        self.assertEqual(prepared[0]["source_id"], "SRC-1")

    def test_normalize_answer_payload_filters_unknown_citations(self):
        citations = [
            {
                "source_id": "SRC-1",
                "title": "Employment onboarding review checklist",
                "issuer": "Labour counsel operations summary",
                "area": "employment",
                "jurisdiction": "Nigeria",
                "citation_label": "Counsel summary: Employment onboarding review",
                "snippet": "Example excerpt",
            }
        ]
        payload = {
            "answer_status": "supported",
            "answer_text": "Use a reviewed employment packet.",
            "risk_level": "medium",
            "requires_lawyer_review": True,
            "recommended_actions": ["Prepare the packet."],
            "follow_up_questions": [],
            "citation_ids": ["SRC-1", "SRC-99"],
        }
        normalized = normalize_answer_payload(payload, citations)
        self.assertEqual(len(normalized["citations"]), 1)
        self.assertEqual(normalized["citations"][0]["source_id"], "SRC-1")

    def test_build_answer_draft_starts_with_pending_review_metadata(self):
        payload = {
            "answer_status": "supported",
            "answer_text": "Use a reviewed employment packet.",
            "risk_level": "medium",
            "requires_lawyer_review": True,
            "recommended_actions": ["Prepare the packet."],
            "follow_up_questions": [],
            "citations": [],
        }
        draft = build_answer_draft("How should I onboard a first employee?", payload, "gpt-5-mini")
        self.assertEqual(draft["jurisdiction"], "Nigeria")
        self.assertEqual(draft["review_status"], "pending_lawyer_review")
        self.assertIsNone(draft["reviewer_name"])
        self.assertIsNone(draft["review_notes"])
        self.assertIsNone(draft["reviewed_at"])


if __name__ == "__main__":
    unittest.main()
