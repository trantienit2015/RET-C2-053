# RET-C2-053 — Unit Tests: ResponseAssembleNode (inner subgraph step 3)

from framework.schemas.agent_status import AgentStatus
from src.nodes.response_assemble_node import ResponseAssembleNode


class TestResponseAssembleNode:
    def setup_method(self):
        self.node = ResponseAssembleNode()

    def test_out_of_scope_returns_refusal(self):
        state = {
            "query_intent": "out_of_scope",
            "detected_language": "en",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["citations"] == []
        assert "order" in result["result"].lower() or "account" in result["result"].lower()

    def test_no_match_returns_fallback_message(self):
        state = {
            "query_intent": "faq_policy",
            "detected_language": "en",
            "retrieved_passages": [],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["citations"] == []

    def test_grounded_answer_includes_citation(self):
        state = {
            "query_intent": "faq_policy",
            "detected_language": "en",
            "normalized_query": "return policy",
            "retrieved_passages": [
                {"doc_id": "policy-returns-001", "topic": "returns", "text": "Returns within 30 days.", "score": 0.9}
            ],
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["citations"] == ["policy-returns-001"]
        assert "30 days" in result["result"]

    def test_injected_llm_client_is_used_when_provided(self):
        class FakeLLM:
            def complete(self, query, passages):
                return f"llm-answer for {query} ({len(passages)} passages)"

        node = ResponseAssembleNode(llm=FakeLLM())
        state = {
            "query_intent": "faq_policy",
            "detected_language": "en",
            "normalized_query": "warranty",
            "retrieved_passages": [
                {"doc_id": "policy-warranty-004", "topic": "warranty", "text": "1-year warranty.", "score": 0.8}
            ],
            "node_history": [],
            "error_log": [],
        }
        result = node.execute(state)
        assert result["result"].startswith("llm-answer for warranty")
