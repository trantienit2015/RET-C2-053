# RET-C2-053 — Unit Tests: IntentClassifyNode (inner subgraph step 1)

import json

from framework.schemas.agent_status import AgentStatus
from src.nodes.intent_classify_node import IntentClassifyNode


class TestIntentClassifyNode:
    def setup_method(self):
        self.node = IntentClassifyNode()

    def test_faq_policy_intent(self):
        payload = json.dumps({"query": "What is your return policy?", "language": "en"})
        state = {"user_input": payload, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["query_intent"] == "faq_policy"
        assert result["normalized_query"] == "What is your return policy?"

    def test_out_of_scope_order_status(self):
        payload = json.dumps({"query": "Can you track my order status?", "language": "en"})
        state = {"user_input": payload, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["query_intent"] == "out_of_scope"

    def test_malformed_payload_is_error(self):
        state = {"user_input": "not json", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
        assert result["error_log"]

    def test_empty_query_is_error(self):
        payload = json.dumps({"query": "", "language": "en"})
        state = {"user_input": payload, "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.ERROR
