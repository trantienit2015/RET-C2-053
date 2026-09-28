"""AgentCore Platform v1.0"""

# Inner subgraph step 2 — hybrid (keyword + dense-vector) retrieval over the
# retail FAQ/store-policy knowledge base. Skipped by routing when the query
# was classified out_of_scope.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.services.kb_retrieval_service import KBRetrievalService


class HybridRetrieveNode(FunctionNode):
    """Retrieve top-k FAQ/policy passages relevant to the normalized query."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, top_k: int = 5, service: KBRetrievalService | None = None):
        self._top_k = top_k
        self._service = service or KBRetrievalService()

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        query = state.get("normalized_query", "")
        passages = self._service.search(query, top_k=self._top_k)

        emit_trace_event(
            "kb_retrieved",
            {"n_results": len(passages), "correlation_id": state.get("correlation_id")},
            state,
        )
        return {"retrieved_passages": passages, "status": AgentStatus.SUCCESS.value}
