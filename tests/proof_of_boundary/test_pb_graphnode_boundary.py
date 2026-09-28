# Cat 2 GraphNode boundary test — PB-6 only discovers concrete BaseNode
# subclasses under src/nodes/. FaqPolicyGraphNode lives in src/graph/graph.py
# (by design — see its docstring), which is OUTSIDE that discovery path. This
# outer GraphNode is the first thing that receives caller input for the
# `main` slot, so it is a real security boundary and must be probed here
# instead.

from framework.nodes.base_node import BaseNode
from framework.nodes.graph_node import GraphNode
from framework.schemas.trust_level import TrustLevel

from src.graph.graph import FaqPolicyGraphNode
from src.nodes.intent_classify_node import IntentClassifyNode


class TestGraphNodeS1TrustGate:
    """S-1: the outer GraphNode inherits BaseNode.__call__() unmodified, so
    the trust gate still runs before its execute() — it is NOT exempt just
    because it lives outside src/nodes/."""

    def test_does_not_override_call(self):
        # If FaqPolicyGraphNode (or GraphNode itself) ever overrode __call__,
        # the S-1 gate + S-4 audit events would silently stop running for the
        # outer boundary. Confirms the security pipeline is inherited, not
        # bypassed.
        assert FaqPolicyGraphNode.__call__ is BaseNode.__call__
        assert GraphNode.__call__ is BaseNode.__call__

    def test_trust_gate_denies_before_execute(self, monkeypatch):
        # FaqPolicyGraphNode itself declares ANONYMOUS (matches agent.yaml —
        # this template has no privileged operation to gate at this node).
        # To prove the *mechanism* actually engages for this class (rather
        # than just being inherited in principle), raise the bar for this
        # one call via monkeypatch and confirm a below-bar caller is denied
        # before execute() runs.
        monkeypatch.setattr(FaqPolicyGraphNode, "required_trust_level", TrustLevel.VERIFIED_EXTERNAL)
        executed = []
        monkeypatch.setattr(FaqPolicyGraphNode, "execute", lambda self, state: executed.append(state) or {})

        node = FaqPolicyGraphNode()
        state = {"caller_trust_level": TrustLevel.ANONYMOUS.value, "correlation_id": "pb-gn-s1-test"}
        result = node(state)

        assert executed == [], "execute() must NOT run when the caller is below required_trust_level"
        assert result.get("status") == "error"
        assert any("S-1 trust gate denied" in e for e in result.get("error_log", []))


class TestGraphNodeBoundaryMapping:
    """Criterion #9: extract_input() must only read the field it needs;
    merge_output() must map fields explicitly, not pass the raw subgraph
    dict straight through into parent state."""

    def test_extract_input_reads_only_the_expected_field(self):
        node = FaqPolicyGraphNode()
        state = {
            "validated_input": "what is your return policy?",
            "user_input": "raw-unvalidated-should-not-be-used",
            "some_unrelated_field": "must not leak into subgraph input",
            "correlation_id": "pb-gn-boundary-test",
        }
        assert node.extract_input(state) == "what is your return policy?"

    def test_merge_output_maps_fields_explicitly_no_raw_passthrough(self):
        node = FaqPolicyGraphNode()
        state = {"correlation_id": "pb-gn-boundary-test"}
        sub_result = {
            "result": "Our return window is 30 days.",
            "citations": ["policy-001"],
            "escalation_flagged": False,
            "query_intent": "faq_policy",
            "detected_language": "en",
            "status": "success",
            # fields the inner subgraph carries that must NOT leak to the
            # parent verbatim (they are inner-graph bookkeeping, not part of
            # the outer AgentState contract at this boundary):
            "trace_id": "inner-trace-should-not-leak",
            "node_history": ["intent_classify", "hybrid_retrieve", "response_assemble"],
        }
        merged = node.merge_output(state, sub_result)

        assert merged == {
            "result": "Our return window is 30 days.",
            "citations": ["policy-001"],
            "escalation_flagged": False,
            "query_intent": "faq_policy",
            "detected_language": "en",
            "status": "success",
        }
        assert "trace_id" not in merged
        assert "node_history" not in merged


class TestGraphNodeDelegatesGatingToInnerSubgraph:
    """Delegation is a deliberate design choice (framework/nodes/graph_node.py
    GraphNode.execute() calls subgraph.invoke(), which runs the inner
    entry node's own S-1/S-2/S-3 pipeline via BaseNode.__call__) — not an
    unguarded boundary. Confirm the inner entry node actually carries that
    pipeline rather than silently opting out of it."""

    def test_inner_entry_node_has_own_trust_and_security_gates(self):
        assert IntentClassifyNode.__call__ is BaseNode.__call__
        assert IntentClassifyNode.required_trust_level == TrustLevel.ANONYMOUS
