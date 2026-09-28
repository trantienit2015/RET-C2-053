"""AgentCore Platform v1.0"""

# Service layer: retail FAQ/policy knowledge-base retrieval (hybrid keyword +
# dense-vector search). Deterministic, in-memory implementation so the agent
# is fully testable without a live vector-store dependency. A production
# deployment can swap `KBRetrievalService` for a client backed by a real
# vector index (e.g. Qdrant) without changing the node contract.
#
# Must NOT contain business-logic branching (that lives in the nodes) or
# credentials. Nodes call this; this module never imports agenticstar/mediator.

from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass, field


@dataclass(frozen=True)
class KBDocument:
    doc_id: str
    topic: str
    language: str  # "ja" | "en" | "any"
    text: str
    keywords: tuple[str, ...] = field(default_factory=tuple)


# Small deterministic retail FAQ + store-policy corpus (returns, exchanges,
# shipping, warranty, store hours). Real deployments replace this list with a
# managed KB source; the retrieval interface below stays the same.
_KB_CORPUS: tuple[KBDocument, ...] = (
    KBDocument(
        doc_id="policy-returns-001",
        topic="returns",
        language="any",
        text=(
            "Items may be returned within 30 days of purchase with a valid receipt, in "
            "original condition and packaging. Refunds are issued to the original payment "
            "method within 5-7 business days."
        ),
        keywords=("return", "refund", "receipt", "returns"),
    ),
    KBDocument(
        doc_id="policy-exchange-002",
        topic="exchange",
        language="any",
        text=(
            "Exchanges for a different size or color are accepted within 30 days of "
            "purchase, subject to stock availability, at any store location."
        ),
        keywords=("exchange", "size", "color", "swap"),
    ),
    KBDocument(
        doc_id="policy-shipping-003",
        topic="shipping",
        language="any",
        text=(
            "Standard shipping takes 3-5 business days domestically. Express shipping "
            "(1-2 business days) is available at checkout for an additional fee."
        ),
        keywords=("shipping", "delivery", "express", "days"),
    ),
    KBDocument(
        doc_id="policy-warranty-004",
        topic="warranty",
        language="any",
        text=(
            "Electronics carry a 1-year manufacturer warranty covering defects in "
            "materials and workmanship. Warranty claims require proof of purchase."
        ),
        keywords=("warranty", "defect", "manufacturer", "guarantee"),
    ),
    KBDocument(
        doc_id="faq-hours-005",
        topic="store_hours",
        language="any",
        text="Stores are open daily from 10:00 to 21:00, including public holidays.",
        keywords=("hours", "open", "close", "holiday"),
    ),
)


class KBRetrievalService:
    """Hybrid keyword + dense-vector retrieval over the retail FAQ/policy KB.

    `dense_score()` is a deterministic stand-in for a real embedding-similarity
    score (token-overlap ratio) so the agent is fully testable offline; a
    production build swaps it for a real vector-store client without changing
    the `search()` contract.
    """

    def __init__(self, corpus: tuple[KBDocument, ...] = _KB_CORPUS) -> None:
        self._corpus = corpus

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        return set(re.findall(r"[a-zA-Z0-9぀-ヿ一-鿿]+", text.lower()))

    def _keyword_score(self, query_tokens: set[str], doc: KBDocument) -> float:
        if not doc.keywords:
            return 0.0
        hits = sum(1 for kw in doc.keywords if kw in query_tokens)
        return hits / len(doc.keywords)

    def _dense_score(self, query_tokens: set[str], doc: KBDocument) -> float:
        doc_tokens = self._tokenize(doc.text)
        if not query_tokens or not doc_tokens:
            return 0.0
        overlap = query_tokens & doc_tokens
        return len(overlap) / len(query_tokens | doc_tokens)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Hybrid search: combined keyword + dense score, descending, top_k."""
        query_tokens = self._tokenize(query)
        scored: list[dict[str, Any]] = []
        for doc in self._corpus:
            kw = self._keyword_score(query_tokens, doc)
            dense = self._dense_score(query_tokens, doc)
            combined = (0.5 * kw) + (0.5 * dense)
            if combined > 0:
                scored.append(
                    {
                        "doc_id": doc.doc_id,
                        "topic": doc.topic,
                        "text": doc.text,
                        "score": round(combined, 4),
                    }
                )
        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:top_k]
