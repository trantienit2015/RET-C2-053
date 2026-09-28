"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict — never Pydantic BaseModel.
# LangGraph checkpoints use msgpack serialization; Pydantic objects
# cause silent corruption.  Extend AgentState with agent-specific
# fields only.  Do NOT add credentials, secrets, or Pydantic models.
#
# State-safety rule: every agent-specific field (list, dict, or
# scalar) MUST be wrapped in NotRequired[...] — a field absent from a given
# invocation must not raise KeyError on checkpoint deserialization or on a
# node running before the field is first written.

from typing import NotRequired

from framework.schemas.agent_state import AgentState


# Type-check note: the wheel ships no py.typed, so mypy resolves AgentState to Any
# and reports every NotRequired below as valid-type. The fields are correct (the state
# contract requires NotRequired) -- the report is a packaging artifact, suppressed per field.
# Drop these ignores once the wheel ships py.typed.
class State(AgentState):
    """Agent state for the Retail FAQ and Policy Q&A Agent (RET-C2-053).

    Shared fields (user_input, validated_input, result, formatted_output,
    status, node_history, error_log, intent, hitl_*, ...) are inherited from
    AgentState and are NOT re-declared here.
    """

    # Outer pre_process (QueryNormalizeNode) output.
    detected_language: NotRequired[str]  # type: ignore[valid-type]  # "ja" | "en"
    normalized_query: NotRequired[str]  # type: ignore[valid-type]

    # Inner subgraph (faq_policy_workflow) output.
    query_intent: NotRequired[str]  # type: ignore[valid-type]  # "faq_policy" | "out_of_scope"
    retrieved_passages: NotRequired[list[dict]]  # type: ignore[valid-type]  # [{"doc_id","text","score","topic"}, ...]
    citations: NotRequired[list[str]]  # type: ignore[valid-type]  # doc_id list backing the answer
    escalation_flagged: NotRequired[bool]  # type: ignore[valid-type]  # S-3 escalation-keyword detection
