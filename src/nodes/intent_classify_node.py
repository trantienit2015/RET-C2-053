"""AgentCore Platform v1.0"""

# Inner subgraph step 1 — classify FAQ/policy questions vs. out-of-scope
# order-status / account queries. Out-of-scope queries are hard-refused
# (redirected) with NO live order/account API call from this template.
#
# Inner graphs do not see outer state directly (Cat 2 GraphNode boundary):
# the JSON envelope built by
# QueryNormalizeNode arrives here as state["user_input"].

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_OUT_OF_SCOPE_PATTERN = re.compile(
    r"(order\s*status|track\s*(my\s*)?order|my\s*order|order\s*number|account\s*balance|"
    r"注文状況|注文番号|配送状況|アカウント残高)",
    re.IGNORECASE,
)


class IntentClassifyNode(FunctionNode):
    """Route FAQ/policy questions to retrieval; hard-refuse order-status/account queries."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        raw = state.get("user_input", "")
        try:
            payload = json.loads(raw) if isinstance(raw, str) and raw else {}
        except (ValueError, TypeError):
            payload = {}

        query = payload.get("query", "") if isinstance(payload, dict) else ""
        language = payload.get("language", "en") if isinstance(payload, dict) else "en"

        if not isinstance(query, str) or not query.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["IntentClassifyNode: empty or malformed query payload"],
            }

        intent = "out_of_scope" if _OUT_OF_SCOPE_PATTERN.search(query) else "faq_policy"

        emit_trace_event(
            "intent_classified",
            {"intent": intent, "correlation_id": state.get("correlation_id")},
            state,
        )
        return {
            "normalized_query": query,
            "detected_language": language,
            "query_intent": intent,
            "status": AgentStatus.SUCCESS.value,
        }
