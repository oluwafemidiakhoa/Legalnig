import unittest

from legal_mvp.ingestion import build_source_document, chunk_text, content_hash


class IngestionTests(unittest.TestCase):
    def test_build_source_document_validates_required_fields(self):
        document = build_source_document(
            {
                "source_key": "demo-doc",
                "title": "Demo Document",
                "issuer": "Counsel",
                "jurisdiction": "Nigeria",
                "area": "company formation",
                "citation_label": "Counsel summary: Demo",
                "body_text": "A short body of text.",
            }
        )
        self.assertEqual(document.source_key, "demo-doc")
        self.assertFalse(document.production_ready)

    def test_chunk_text_breaks_long_text(self):
        text = " ".join(f"word{i}" for i in range(240))
        chunks = chunk_text(text, max_words=80, overlap_words=10)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(chunk for chunk in chunks))

    def test_content_hash_is_stable(self):
        self.assertEqual(content_hash("same"), content_hash("same"))


if __name__ == "__main__":
    unittest.main()
