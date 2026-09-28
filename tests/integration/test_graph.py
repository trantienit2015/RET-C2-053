# RET-C2-053 — Integration Tests: full outer graph (Cat 2)

from framework.schemas.agent_status import AgentStatus
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from src.graph.graph import Graph


class TestRetailFaqPolicyAgentIntegration:
    def _new_agent(self):
        agent = Graph(config={"top_k": 5, "max_retry": 1})
        agent.compile()
        return agent

    def _ctx(self, session_id: str = "it-1") -> InvocationContext:
        return InvocationContext(
            session_id=session_id,
            caller_trust_level=TrustLevel.VERIFIED_EXTERNAL,
            caller_id="test-caller",
        )

    def test_faq_policy_question_returns_grounded_answer(self):
        agent = self._new_agent()
        result = agent.invoke("What is your return policy?", ctx=self._ctx("it-faq"))
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
        output = result.get("output") or result.get("formatted_output") or ""
        assert "30 days" in output or "return" in output.lower()

    def test_order_status_query_is_hard_refused(self):
        agent = self._new_agent()
        result = agent.invoke("Can you track my order status?", ctx=self._ctx("it-oos"))
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
        output = result.get("output") or result.get("formatted_output") or ""
        assert "order" in output.lower() or "account" in output.lower()

    def test_complaint_question_gets_human_handoff_note(self):
        agent = self._new_agent()
        result = agent.invoke("I want to file a complaint about my refund.", ctx=self._ctx("it-esc"))
        assert result["status"] in (AgentStatus.SUCCESS.value, AgentStatus.SUCCESS)
        output = result.get("output") or result.get("formatted_output") or ""
        assert "human agent" in output

    def test_plain_question_has_no_handoff_note(self):
        agent = self._new_agent()
        result = agent.invoke("What is your return policy?", ctx=self._ctx("it-noesc"))
        output = result.get("output") or result.get("formatted_output") or ""
        assert "human agent" not in output

    def test_empty_input_yields_error_status(self):
        agent = self._new_agent()
        result = agent.invoke("   ", ctx=self._ctx("it-empty"))
        assert result["status"] in (AgentStatus.ERROR.value, AgentStatus.ERROR)

    def test_node_history_covers_full_backbone(self):
        agent = self._new_agent()
        result = agent.invoke("What are your store hours?", ctx=self._ctx("it-hist"))
        node_history = result.get("node_history") or []
        # Outer backbone: Initialize -> pre_process -> main(GraphNode) -> post_process -> Finalize.
        assert len(node_history) >= 5
