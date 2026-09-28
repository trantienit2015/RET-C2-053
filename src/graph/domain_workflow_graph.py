"""AgentCore Platform v1.0"""

# Inner graph for the Cat 2 faq_policy_workflow — custom topology (BaseGraph),
# called by FaqPolicyGraphNode.get_subgraph() in src/graph/graph.py.
#
# Pipeline:
#   START -> intent_classify -> {route}
#              (faq_policy)   -> hybrid_retrieve -> response_assemble -> response_validate -> END
#              (out_of_scope) -> response_assemble -> response_validate -> END
#              (error)        -> END

from typing import Any
from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_state import AgentState
from framework.schemas.agent_status import AgentStatus
from src.nodes.hybrid_retrieve_node import HybridRetrieveNode
from src.nodes.intent_classify_node import IntentClassifyNode
from src.nodes.response_assemble_node import ResponseAssembleNode
from src.nodes.response_validate_node import ResponseValidateNode
from src.schemas.state import State


class FaqPolicyWorkflowGraph(BaseGraph):
    """Inner graph for the Cat 2 retail FAQ/policy Q&A workflow.

    Inherits BaseGraph directly for a fully custom node topology (order-status/
    account queries skip retrieval entirely — see route()).
    """

    @property
    def name(self) -> str:
        return "faq_policy_workflow"

    @property
    def state_schema(self) -> type:
        return State

    def _validate_config(self) -> None:
        # No mandatory config keys; top_k defaults to 5 in register_nodes().
        pass

    def register_nodes(self) -> None:
        # No super() call — BaseGraph.register_nodes() is abstract. Do NOT
        # register initialize/finalize here — outer backbone concern.
        top_k = self.config.get("top_k", 5) if hasattr(self, "config") else 5
        self._nodes["intent_classify"] = IntentClassifyNode()
        self._nodes["hybrid_retrieve"] = HybridRetrieveNode(top_k=top_k)
        self._nodes["response_assemble"] = ResponseAssembleNode()
        self._nodes["response_validate"] = ResponseValidateNode()

    def add_edges(self) -> None:
        self._sg.add_edge(START, "intent_classify")
        self._sg.add_conditional_edges("intent_classify", self.route)
        self._sg.add_edge("hybrid_retrieve", "response_assemble")
        self._sg.add_edge("response_assemble", "response_validate")
        self._sg.add_edge("response_validate", END)

    def route(self, state: AgentState) -> str:
        """After intent_classify: skip retrieval for out-of-scope / error queries."""
        if state.get("status") == AgentStatus.ERROR.value:
            return END
        if state.get("query_intent") == "out_of_scope":
            return "response_assemble"
        return "hybrid_retrieve"

    def get_output(self, state: AgentState) -> dict[str, Any]:
        """Shape the sub_result dict consumed by FaqPolicyGraphNode.merge_output()."""
        return {
            "result": state.get("result"),
            "citations": state.get("citations", []),
            "escalation_flagged": state.get("escalation_flagged", False),
            "query_intent": state.get("query_intent"),
            "detected_language": state.get("detected_language"),
            "status": state.get("status"),
            "trace_id": state.get("trace_id"),
            "correlation_id": state.get("correlation_id"),
            "node_history": state.get("node_history", []),
        }
