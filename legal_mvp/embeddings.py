from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.request

from legal_mvp.runtime_env import load_env_file


load_env_file()

EMBEDDING_DIMENSIONS = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
DEFAULT_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
DEFAULT_OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(text: str) -> str:
    return " ".join(TOKEN_PATTERN.findall(text.lower()))


def get_embedding_backend_name() -> str:
    return "openai" if os.getenv("OPENAI_API_KEY") else "local"


def get_embedding_model_name() -> str:
    if get_embedding_backend_name() == "openai":
        return DEFAULT_EMBEDDING_MODEL
    return "local-hash"


def embed_text(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    return embed_texts([text], dimensions=dimensions)[0]


def embed_texts(texts: list[str], dimensions: int = EMBEDDING_DIMENSIONS) -> list[list[float]]:
    if get_embedding_backend_name() == "openai":
        return _embed_with_openai(texts, dimensions=dimensions)
    return [_embed_text_local(text, dimensions=dimensions) for text in texts]


def _embed_text_local(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    normalized = normalize_text(text)
    vector = [0.0] * dimensions

    if not normalized:
        normalized = "empty"

    for token in normalized.split():
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        first_slot = int.from_bytes(digest[:8], "big") % dimensions
        second_slot = int.from_bytes(digest[8:], "big") % dimensions
        first_weight = 1.0 if digest[0] % 2 == 0 else -1.0
        second_weight = 0.5 if digest[1] % 2 == 0 else -0.5
        vector[first_slot] += first_weight
        vector[second_slot] += second_weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def _embed_with_openai(texts: list[str], dimensions: int = EMBEDDING_DIMENSIONS) -> list[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for OpenAI embeddings.")

    payload = {
        "model": DEFAULT_EMBEDDING_MODEL,
        "input": texts,
        "dimensions": dimensions,
    }
    request = urllib.request.Request(
        f"{DEFAULT_OPENAI_BASE_URL}/embeddings",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:  # pragma: no cover - networked runtime path
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI embeddings request failed: {details}") from exc
    except urllib.error.URLError as exc:  # pragma: no cover - networked runtime path
        raise RuntimeError(f"OpenAI embeddings request failed: {exc}") from exc

    return [item["embedding"] for item in body.get("data", [])]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.6f}" for value in values) + "]"
