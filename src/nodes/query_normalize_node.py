"""AgentCore Platform v1.0"""

# Outer pre_process node — language detection + query normalization.
# S-2: no domain hook. The framework's default input gate (FunctionNode) already
# masks PII (email, phone, card numbers, ...) in user_input / validated_input
# with detect_pii()/mask_pii() before execute() runs, so this node never sees
# raw contact details.

import json
import re
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_JP_CHAR_PATTERN = re.compile(r"[぀-ヿ一-鿿]")


class QueryNormalizeNode(FunctionNode):
    """Detect language (ja/en), normalize the query, and seed the inner-subgraph payload."""

    # S-1: explicit by design, not inherited implicitly.
    # Public-facing FAQ/policy Q&A — no privileged operation.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        user_input = state.get("user_input", "")
        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["QueryNormalizeNode: user_input is empty or missing"],
            }

        normalized = user_input.strip()
        language = "ja" if _JP_CHAR_PATTERN.search(normalized) else "en"
        # Cat 2 data flow: the inner subgraph only receives a string (extract_input()),
        # so the JSON envelope carries both the normalized query and detected language.
        validated_input = json.dumps({"query": normalized, "language": language}, ensure_ascii=False)

        emit_trace_event(
            "query_normalized",
            {"detected_language": language, "correlation_id": state.get("correlation_id")},
            state,
        )
        return {
            "normalized_query": normalized,
            "detected_language": language,
            "validated_input": validated_input,
            "status": AgentStatus.SUCCESS.value,
        }
