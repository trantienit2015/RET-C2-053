# RET-C2-053 — Unit Tests: ResponseFinalizeNode (outer post_process)

from framework.schemas.agent_status import AgentStatus
from src.nodes.response_finalize_node import ResponseFinalizeNode


class TestResponseFinalizeNode:
    def setup_method(self):
        self.node = ResponseFinalizeNode()

    def test_formats_result_with_citations(self):
        state = {
            "result": "Returns within 30 days.",
            "citations": ["policy-returns-001"],
            "escalation_flagged": False,
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert "policy-returns-001" in result["formatted_output"]

    def test_formats_result_without_citations(self):
        state = {"result": "No matching policy found.", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["formatted_output"] == "No matching policy found."

    def test_escalation_note_appended_when_flagged(self):
        state = {
            "result": "We understand your concern.",
            "citations": [],
            "escalation_flagged": True,
            "node_history": [],
            "error_log": [],
        }
        result = self.node.execute(state)
        assert "human agent" in result["formatted_output"].lower()
