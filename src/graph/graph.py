"""AgentCore Platform v1.0"""

# Outer graph — Cat 2 pattern: AgentBaseGraph
# backbone (fixed initialize -> pre_process -> main -> post_process ->
# finalize) with the `main` slot wrapped by a GraphNode pointing at the inner
# faq_policy_workflow subgraph. The GraphNode subclass lives in THIS file
# (not src/nodes/) so tests/proof_of_boundary/test_pb_invoke_order.py (which
# only discovers src/nodes/) does not probe it with the wrong lifecycle.
# This outer boundary is instead covered by its own dedicated test:
# tests/proof_of_boundary/test_pb_graphnode_boundary.py.

from typing import Any, ClassVar, cast

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event
from src.nodes.query_normalize_node import QueryNormalizeNode
from src.nodes.response_finalize_node import ResponseFinalizeNode
from src.schemas.state import State


class FaqPolicyGraphNode(GraphNode):
    """Wraps the inner faq_policy_workflow subgraph; assigned to the `main` slot."""

    # S-1: explicit by design, matches agent.yaml required_trust_level.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS
    # "propagate": re-raise inner graph exceptions as SubgraphError (fail fast).
    error_strategy: ClassVar[str] = "propagate"
    # HITL is not used by this template (hitl.enabled is not set).
    propagate_hitl: ClassVar[bool] = False

    def __init__(self, top_k: int = 5):
        super().__init__()
        self._top_k = top_k

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import FaqPolicyWorkflowGraph

        sg = FaqPolicyWorkflowGraph(config=self._parent_config())
        sg.compile()
        return sg

    def extract_input(self, state: AgentState) -> str:
        # S-4: runs inside GraphNode.execute() — audit dispatch into the inner subgraph.
        emit_trace_event(
            "faq_policy_dispatched",
            {"correlation_id": state.get("correlation_id")},
            state,
        )
        return cast(str, state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        # S-4: runs inside GraphNode.execute() — audit the subgraph outcome merged back out.
        emit_trace_event(
            "faq_policy_completed",
            {"n_citations": len(sub_result.get("citations", []) or [])},
            state,
        )
        return {
            "result": sub_result.get("result"),
            "citations": sub_result.get("citations", []),
            "escalation_flagged": sub_result.get("escalation_flagged", False),
            "query_intent": sub_result.get("query_intent"),
            "detected_language": sub_result.get("detected_language"),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {"top_k": self._top_k}


class RetailFaqPolicyAgent(AgentBaseGraph):
    """RET-C2-053 — Retail FAQ and Policy Q&A Agent (Cat 2, outer graph)."""

    @property
    def name(self) -> str:
        return "ret-c2-053"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode
        top_k = self.config.get("top_k", 5) if hasattr(self, "config") else 5
        self._nodes["pre_process"] = QueryNormalizeNode()
        self._nodes["main"] = FaqPolicyGraphNode(top_k=top_k)
        self._nodes["post_process"] = ResponseFinalizeNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.


Graph = RetailFaqPolicyAgent  # alias for config/agent.yaml module:"src.graph"
