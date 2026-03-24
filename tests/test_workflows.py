import unittest

from legal_mvp.workflows import build_document_briefs, build_intake_request, build_workflow


class WorkflowTests(unittest.TestCase):
    def make_payload(self, **overrides):
        payload = {
            "founder_name": "Amina Yusuf",
            "business_name": "Northstar Health",
            "entity_type": "Private Company Limited by Shares",
            "sector": "health",
            "use_case": "Incorporate the business and prepare an employment packet for first hires.",
            "contact_email": "amina@example.com",
            "consent": True,
        }
        payload.update(overrides)
        return payload

    def test_build_intake_requires_consent(self):
        with self.assertRaises(ValueError):
            build_intake_request(self.make_payload(consent=False))

    def test_regulated_sector_triggers_lawyer_review(self):
        request = build_intake_request(self.make_payload())
        workflow = build_workflow(request)
        titles = [step.title for step in workflow]
        self.assertTrue(any("Escalate sector licensing review" in t for t in titles))
        self.assertEqual(request.jurisdiction, "Nigeria")

    def test_employment_use_case_adds_employment_packet(self):
        request = build_intake_request(self.make_payload())
        documents = build_document_briefs(request)
        titles = [document.title for document in documents]
        self.assertIn("Employment packet outline", titles)

    def test_intake_normalizes_ng_alias(self):
        request = build_intake_request(self.make_payload(jurisdiction="ng"))
        self.assertEqual(request.jurisdiction, "Nigeria")


if __name__ == "__main__":
    unittest.main()
