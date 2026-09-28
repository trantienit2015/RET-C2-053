# RET-C2-053 — Unit Tests: ResponseValidateNode (inner subgraph step 4, S-3 output gate)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from src.nodes.response_validate_node import ResponseValidateNode


class TestResponseValidateNode:
    def setup_method(self):
        self.node = ResponseValidateNode()

    def test_clean_response_passes(self):
        state = {"result": "Returns are accepted within 30 days.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["escalation_flagged"] is False

    def test_escalation_keyword_flagged(self):
        state = {"result": "I want to file a complaint about this.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["escalation_flagged"] is True

    def test_pii_leak_blocks_response(self):
        """S-3: PII leak in the assembled answer FAILs — no silent suppression."""
        state = {"result": "Contact john.doe@example.com for details.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_phone_number_leak_blocks_response(self):
        """S-3: detect_pii phone findings block the answer as well."""
        state = {"result": "Call our manager on 03-1234-5678.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR

    def test_title_case_policy_text_is_not_blocked(self):
        """The detector's Latin-name heuristic is ignored, so policy wording still passes."""
        state = {"result": "Standard Shipping takes 3-5 business days. Express Shipping is faster.",
                 "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS

    def test_escalation_keyword_in_question_flags_response(self):
        """The customer's question alone triggers escalation; the grounded answer has no keyword."""
        state = {
            "normalized_query": "I want to file a complaint about my refund.",
            "result": "Items may be returned within 30 days of purchase with a valid receipt.",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["escalation_flagged"] is True

    def test_plain_question_is_not_escalated(self):
        state = {
            "normalized_query": "What is your return policy?",
            "result": "Items may be returned within 30 days of purchase with a valid receipt.",
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["escalation_flagged"] is False

    def test_trust_gate_allows_anonymous(self):
        state = {
            "result": "Returns are accepted within 30 days.",
            "caller_trust_level": TrustLevel.ANONYMOUS.value,
            "node_history": [],
            "error_log": [],
        }
        result = self.node(state)
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
