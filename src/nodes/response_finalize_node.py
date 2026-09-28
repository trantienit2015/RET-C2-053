"""AgentCore Platform v1.0"""

# Outer post_process node — assembles the final customer-facing text: the
# grounded answer, a source-citation footer, and (when flagged) an escalation
# note pointing the customer to a human agent.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event


class ResponseFinalizeNode(FunctionNode):
    """Format the final output: grounded answer + citations + escalation note."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        result = state.get("result", "") or ""
        citations = state.get("citations", []) or []
        escalation = bool(state.get("escalation_flagged", False))

        source_note = f" (Sources: {', '.join(citations)})" if citations else ""
        escalation_note = (
            "\n\nIf this doesn't resolve your concern, our team can connect you with a " "human agent."
            if escalation
            else ""
        )
        formatted = f"{result}{source_note}{escalation_note}"

        emit_trace_event(
            "response_finalized",
            {"escalation_flagged": escalation, "correlation_id": state.get("correlation_id")},
            state,
        )
        return {"formatted_output": formatted, "status": AgentStatus.SUCCESS.value}
