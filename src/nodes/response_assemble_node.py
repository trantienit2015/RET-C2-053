"""AgentCore Platform v1.0"""

# Inner subgraph step 3 — ground the answer on retrieved passages with
# mandatory source citation. Handles the out-of-scope refusal path and the
# no-match path deterministically; delegates grounded phrasing to an injected
# LLM client when available, otherwise falls back to a deterministic composer
# (fully offline-testable).

from typing import Any, ClassVar, cast

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.utils.audit_logger import emit_trace_event

_OUT_OF_SCOPE_MESSAGE = {
    "en": (
        "I'm not able to look up order status or account details here. Please check "
        "your order confirmation email or contact our order-support line, and a team "
        "member will help with your order/account question directly."
    ),
    "ja": (
        "こちらでは注文状況やアカウント情報の確認は行えません。ご注文確認メールをご確認いただくか、"
        "注文サポート窓口までお問い合わせください。担当者が直接対応いたします。"
    ),
}

_NO_MATCH_MESSAGE = {
    "en": (
        "I couldn't find a policy or FAQ entry that answers this question. Please "
        "rephrase your question, or our team can look into it for you."
    ),
    "ja": (
        "ご質問にお答えできるポリシーまたはFAQが見つかりませんでした。質問内容をご変更いただくか、"
        "担当者が確認いたします。"
    ),
}


class ResponseAssembleNode(FunctionNode):
    """Compose the grounded answer with mandatory source citation."""

    # S-1: explicit by design, not inherited implicitly.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.ANONYMOUS

    def __init__(self, llm: Any = None) -> None:
        # Optional injected grounding LLM (must expose .complete(...)); when absent,
        # a deterministic composer is used so the agent stays fully offline-testable.
        self._llm = llm

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        language = state.get("detected_language", "en")
        query_intent = state.get("query_intent", "faq_policy")

        if query_intent == "out_of_scope":
            answer = _OUT_OF_SCOPE_MESSAGE.get(language, _OUT_OF_SCOPE_MESSAGE["en"])
            emit_trace_event(
                "response_out_of_scope",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {"result": answer, "citations": [], "status": AgentStatus.SUCCESS.value}

        passages = state.get("retrieved_passages", []) or []
        if not passages:
            answer = _NO_MATCH_MESSAGE.get(language, _NO_MATCH_MESSAGE["en"])
            emit_trace_event(
                "response_no_match",
                {"correlation_id": state.get("correlation_id")},
                state,
            )
            return {"result": answer, "citations": [], "status": AgentStatus.SUCCESS.value}

        query = state.get("normalized_query", "")
        if self._llm is not None:
            raw = self._llm.complete(query=query, passages=passages)
            # Normalise: our injected-client contract documents a plain str
            # return, but the framework's canonical BaseLLM.complete() returns
            # a dict ({"content": ...}) — accept either so a real BaseLLM
            # instance injected here does not silently become a dict-as-string.
            answer = raw.get("content", "") if isinstance(raw, dict) else raw
        else:
            answer = self._compose_grounded_answer(passages)
        citations = [p["doc_id"] for p in passages if "doc_id" in p]

        emit_trace_event(
            "response_assembled",
            {"n_passages": len(passages), "correlation_id": state.get("correlation_id")},
            state,
        )
        return {"result": answer, "citations": citations, "status": AgentStatus.SUCCESS.value}

    @staticmethod
    def _compose_grounded_answer(passages: list[dict[str, Any]]) -> str:
        top = passages[0]
        return cast(str, top["text"])
