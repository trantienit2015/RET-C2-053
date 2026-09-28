# RET-C2-053 — Unit Tests: HybridRetrieveNode (inner subgraph step 2)

from framework.schemas.agent_status import AgentStatus
from src.nodes.hybrid_retrieve_node import HybridRetrieveNode


class TestHybridRetrieveNode:
    def setup_method(self):
        self.node = HybridRetrieveNode()

    def test_success_path_returns_ranked_passages(self):
        state = {"normalized_query": "return policy refund", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["retrieved_passages"]
        assert result["retrieved_passages"][0]["doc_id"]

    def test_no_match_returns_empty_list(self):
        state = {"normalized_query": "zzz-unrelated-gibberish-000", "node_history": [], "error_log": []}
        result = self.node.execute(state)
        assert result["status"] == AgentStatus.SUCCESS
        assert result["retrieved_passages"] == []

    def test_default_construction_uses_top_k_default(self):
        node = HybridRetrieveNode()
        assert node._top_k == 5
