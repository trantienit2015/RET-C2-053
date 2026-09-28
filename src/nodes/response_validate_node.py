"""AgentCore Platform v1.0"""

# Inner subgraph step 4 (S-3 output gate) — non-suppressible PII leak check on
# the assembled answer (FAIL + log, no silent suppression) and escalation
# keyword detection on the customer question and the answer.
#
# The PII check reuses the framework detector (detect_pii). Its Latin-script
# "name" type is skipped here: it matches any two Title Case words, which
# policy text contains routinely, and would block ordinary answers.

from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from framework.security import detect_pii
from shared.utils.audit_logger import emit_trace_event

_IGNORED_PII_TYPES = frozenset({"name"})
_ESCALATION_KEYWORDS = (
    "lawyer",
    "legal action",
    "complaint",
    "fraud",
    "not resolved",
    "escalate",
    "speak to a manager",
    "弁護士",
    "苦情",
    "訴訟",
)


class ResponseValidateNode(FunctionNode):
    """S-3: reject responses that leak PII; flag responses needing human escalation."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        answer = state.get("result", "") or ""
        question = state.get("normalized_query", "") or ""

        pii_types = sorted({f["type"] for f in detect_pii(answer)} - _IGNORED_PII_TYPES)
        if pii_types:
            emit_trace_event(
                "output_pii_blocked",
                {"pii_types": pii_types, "correlation_id": state.get("correlation_id")},
                state,
            )
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["S-3 output gate: PII pattern detected in assembled response — response blocked"],
            }

        # The customer's own wording ("I want to file a complaint") is the main
        # escalation signal; the answer text is checked as well.
        lowered = f"{question} {answer}".lower()
        escalation = any(keyword in lowered for keyword in _ESCALATION_KEYWORDS)

        emit_trace_event(
            "response_validated",
            {"escalation_flagged": escalation, "correlation_id": state.get("correlation_id")},
            state,
        )
        return {"escalation_flagged": escalation, "status": AgentStatus.SUCCESS.value}
