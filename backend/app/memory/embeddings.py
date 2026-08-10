"""Deterministic local embeddings for offline development and tests."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

EMBEDDING_DIMENSIONS = 1536
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class EmbeddingProvider(Protocol):
    """Minimal provider boundary for replaceable embedding implementations."""

    name: str
    model: str
    dimensions: int

    def embed(self, text: str) -> list[float]:
        """Embed non-empty text into the declared vector dimension."""
        ...


class HashingEmbeddingProvider:
    """Sparse feature-hashing vectors with no network or training dependency."""

    name = "local_feature_hashing"
    model = "sha256-token-hash-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def embed(self, text: str) -> list[float]:
        """Return a deterministic L2-normalized bag-of-token vector."""
        tokens = _TOKEN_PATTERN.findall(text.casefold())
        if not tokens:
            raise ValueError("embedding text must contain at least one alphanumeric token")

        vector = [0.0] * self.dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            raise ValueError("embedding vector unexpectedly has zero norm")
        return [value / norm for value in vector]
