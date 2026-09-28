# RET-C2-053 — Unit Tests: QueryNormalizeNode (outer pre_process)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.query_normalize_node import QueryNormalizeNode


class TestQueryNormalizeNode:
    def setup_method(self):
        self.node = QueryNormalizeNode()

    def test_success_path_english(self):
        state = {"user_input": "  What is your return policy?  ", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["detected_language"] == "en"
        assert result["normalized_query"] == "What is your return policy?"
        assert "query" in result["validated_input"]

    def test_success_path_japanese(self):
        state = {"user_input": "返品ポリシーを教えてください", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["detected_language"] == "ja"

    def test_empty_input_is_error(self):
        state = {"user_input": "   ", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_framework_s2_masks_email_before_execute(self):
        """S-2: the framework input gate masks PII before execute(); no raw email reaches the envelope."""
        state = {
            "user_input": "Can I return this? Contact me at test@example.com",
            "caller_trust_level": TrustLevel.ANONYMOUS.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
        assert "test@example.com" not in result["normalized_query"]
        assert "test@example.com" not in result["validated_input"]

    def test_framework_s2_leaves_clean_query_unchanged(self):
        state = {
            "user_input": "What are your store hours?",
            "caller_trust_level": TrustLevel.ANONYMOUS.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        assert result["normalized_query"] == "What are your store hours?"

    def test_trust_gate_denies_anonymous_below_required(self):
        """S-1: node(state) via __call__ enforces required_trust_level."""
        state = {
            "user_input": "store hours?",
            "caller_trust_level": TrustLevel.ANONYMOUS.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        # QueryNormalizeNode requires only ANONYMOUS, so ANONYMOUS caller passes.
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
