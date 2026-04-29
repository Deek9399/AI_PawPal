from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    source_id: str
    score: float


def _chunk_markdown(text: str, source_id: str, max_chars: int = 800) -> List[Tuple[str, str]]:
    """Split into paragraphs; assign chunk ids."""
    parts = re.split(r"\n\s*\n+", text.strip())
    chunks: List[Tuple[str, str]] = []
    for i, p in enumerate(parts):
        p = p.strip()
        if len(p) < 40:
            continue
        # split long paragraphs
        if len(p) > max_chars:
            for j in range(0, len(p), max_chars):
                sub = p[j : j + max_chars]
                chunks.append((sub, f"{source_id}#{len(chunks)}"))
        else:
            chunks.append((p, f"{source_id}#{i}"))
    return chunks


class KnowledgeIndex:
    """TF-IDF retrieval over markdown knowledge files."""

    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = Path(knowledge_dir)
        self._chunks: List[str] = []
        self._ids: List[str] = []
        self._matrix = None
        self._vectorizer: TfidfVectorizer | None = None

    def load(self) -> None:
        self._chunks.clear()
        self._ids.clear()
        if not self.knowledge_dir.is_dir():
            logger.warning("Knowledge dir missing: %s", self.knowledge_dir)
            return
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            for chunk, cid in _chunk_markdown(text, path.name):
                self._chunks.append(chunk)
                self._ids.append(cid)
        if not self._chunks:
            return
        self._vectorizer = TfidfVectorizer(stop_words="english", max_features=4096)
        self._matrix = self._vectorizer.fit_transform(self._chunks)

    def search(self, query: str, top_k: int = 4) -> List[RetrievedChunk]:
        if not self._chunks or self._vectorizer is None or self._matrix is None:
            return []
        qv = self._vectorizer.transform([query])
        sims = cosine_similarity(qv, self._matrix)[0]
        idx = np.argsort(-sims)[:top_k]
        out: List[RetrievedChunk] = []
        for i in idx:
            score = float(sims[i])
            if score <= 0:
                continue
            out.append(
                RetrievedChunk(text=self._chunks[int(i)], source_id=self._ids[int(i)], score=score)
            )
        return out
