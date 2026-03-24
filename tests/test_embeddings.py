import math
import unittest
from unittest.mock import patch

from legal_mvp.embeddings import (
    EMBEDDING_DIMENSIONS,
    embed_text,
    get_embedding_backend_name,
    normalize_text,
    vector_literal,
)


class EmbeddingTests(unittest.TestCase):
    def test_normalize_text(self):
        self.assertEqual(normalize_text("CAC Registration!!!"), "cac registration")

    def test_embed_text_is_stable_and_normalized(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            first = embed_text("employment compliance for health startups")
            second = embed_text("employment compliance for health startups")
        self.assertEqual(first, second)
        self.assertEqual(len(first), EMBEDDING_DIMENSIONS)
        magnitude = math.sqrt(sum(value * value for value in first))
        self.assertAlmostEqual(magnitude, 1.0, places=5)

    def test_vector_literal_shape(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            literal = vector_literal(embed_text("tax onboarding"))
        self.assertTrue(literal.startswith("["))
        self.assertTrue(literal.endswith("]"))

    def test_backend_defaults_to_local_without_api_key(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            self.assertEqual(get_embedding_backend_name(), "local")


if __name__ == "__main__":
    unittest.main()
