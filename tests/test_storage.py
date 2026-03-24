import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import legal_mvp.storage as storage


class StorageFactoryTests(unittest.TestCase):
    def tearDown(self):
        storage.get_backend.cache_clear()

    def test_defaults_to_json_without_database_url(self):
        with patch.dict("os.environ", {}, clear=True):
            backend = storage.get_backend()
            self.assertEqual(backend.name, "json")

    def test_uses_postgres_when_database_url_is_present(self):
        with patch.dict(
            "os.environ",
            {"DATABASE_URL": "postgresql://lexpilot:lexpilot@127.0.0.1:5432/lexpilot"},
            clear=True,
        ):
            backend = storage.get_backend()
            self.assertEqual(backend.name, "postgres")

    def test_json_backend_updates_answer_review_metadata(self):
        with tempfile.TemporaryDirectory() as tempdir:
            temp_path = Path(tempdir)
            with patch.dict("os.environ", {}, clear=True):
                with patch.object(storage, "DATA_DIR", temp_path):
                    with patch.object(storage, "INTAKES_FILE", temp_path / "intakes.json"):
                        with patch.object(storage, "QUEUE_FILE", temp_path / "review_queue.json"):
                            with patch.object(storage, "SOURCE_DOCS_FILE", temp_path / "source_documents.json"):
                                with patch.object(storage, "ANSWER_DRAFTS_FILE", temp_path / "answer_drafts.json"):
                                    with patch.object(storage, "MATTERS_FILE", temp_path / "matters.json"):
                                        storage.get_backend.cache_clear()
                                        backend = storage.get_backend()
                                        backend.initialize()
                                        backend.save_answer_draft(
                                            {
                                                "id": "draft-1",
                                                "matter_id": None,
                                                "created_at": "2026-03-23T19:00:00+00:00",
                                                "question": "What should I review before hiring?",
                                                "status": "supported",
                                                "answer_text": "Prepare a reviewed packet.",
                                                "risk_level": "medium",
                                                "requires_lawyer_review": True,
                                                "recommended_actions": [],
                                                "follow_up_questions": [],
                                                "citations": [],
                                                "model": "gpt-5-mini",
                                                "review_status": "pending_lawyer_review",
                                                "reviewer_name": None,
                                                "review_notes": None,
                                                "reviewed_at": None,
                                                "disclaimer": "Draft operational guidance only.",
                                            }
                                        )
                                        reviewed = backend.review_answer_draft(
                                            "draft-1",
                                            review_status="approved_for_use",
                                            reviewer_name="Ada Obi, Esq.",
                                            review_notes="Approved for internal pilot use.",
                                        )
        self.assertEqual(reviewed["review_status"], "approved_for_use")
        self.assertEqual(reviewed["reviewer_name"], "Ada Obi, Esq.")
        self.assertEqual(reviewed["review_notes"], "Approved for internal pilot use.")
        self.assertIsNotNone(reviewed["reviewed_at"])


if __name__ == "__main__":
    unittest.main()
