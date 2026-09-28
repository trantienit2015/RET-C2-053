# Template Design Specification — RET-C2-053

## Position in AgentCore Architecture

- **Agent Class**: `RetailFaqPolicyAgent` (`src/graph/graph.py`)
- **L1 Base**: AgentBaseGraph (outer graph, Cat 2 pattern — `main` slot wraps an inner
  `FaqPolicyWorkflowGraph` subgraph via `FaqPolicyGraphNode`)
- **Three-Layer Separation**:
  - State: flat TypedDict composition (`src/schemas/state.py`, no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution; outer + inner)

## Architecture Overview

### Node Configuration

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | Session/trust bootstrap | — | `session_id`, `caller_trust_level` | InitializeNode (default) |
| pre_process | Language detect + normalize query (PII already masked by the framework S-2 gate) | `user_input` | `normalized_query`, `detected_language`, `validated_input` | `QueryNormalizeNode` |
| main | Dispatch to inner FAQ/policy subgraph | `validated_input` | `result`, `citations`, `escalation_flagged`, `query_intent` | `FaqPolicyGraphNode` (GraphNode wrapping `FaqPolicyWorkflowGraph`) |
| ↳ inner: intent_classify | FAQ/policy vs. out-of-scope (order-status/account) routing | `user_input` (JSON envelope) | `query_intent`, `normalized_query`, `detected_language` | `IntentClassifyNode` |
| ↳ inner: hybrid_retrieve | Hybrid keyword + dense retrieval over FAQ/policy KB | `normalized_query` | `retrieved_passages` | `HybridRetrieveNode` |
| ↳ inner: response_assemble | Answer = top retrieved passage, with mandatory citation (no model is wired by the graph) | `retrieved_passages` | `result`, `citations` | `ResponseAssembleNode` |
| ↳ inner: response_validate | S-3 output gate: PII leak block (`detect_pii`) + escalation-keyword detection on question and answer | `result`, `normalized_query` | `escalation_flagged` | `ResponseValidateNode` |
| post_process | Format final text (citations footer + escalation note) | `result`, `citations`, `escalation_flagged` | `formatted_output` | `ResponseFinalizeNode` |
| finalize | Response metadata / total time | — | `response_metadata` | FinalizeNode (default) |

### Data Flow

```
OUTER (AgentBaseGraph):
  START → initialize → pre_process → main(GraphNode) → post_process → finalize → END

INNER (BaseGraph, faq_policy_workflow — dispatched from `main`):
  START → intent_classify → {route}
            (faq_policy)   → hybrid_retrieve → response_assemble → response_validate → END
            (out_of_scope) → response_assemble → response_validate → END
            (error)        → END
```

Cat 2 boundary: the inner subgraph receives only a string (`GraphNode.extract_input()`), not
the outer state. `QueryNormalizeNode` (outer pre_process) therefore serializes
`{"query": normalized_query, "language": detected_language}` into `validated_input`
(JSON string); `IntentClassifyNode` (inner, first node) `json.loads()`s it back.
`FaqPolicyGraphNode._parent_config()` forwards `top_k` from `config/agent.yaml` to the inner
graph's node construction (not via state).

### State Definition

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `detected_language` | `NotRequired[str]` | "ja" \| "en", detected by pre_process | No |
| `normalized_query` | `NotRequired[str]` | Trimmed query text | No |
| `query_intent` | `NotRequired[str]` | "faq_policy" \| "out_of_scope" | No |
| `retrieved_passages` | `NotRequired[list[dict]]` | KB hits: `{doc_id, topic, text, score}` | No |
| `citations` | `NotRequired[list[str]]` | `doc_id` list backing the answer | No |
| `escalation_flagged` | `NotRequired[bool]` | Escalation keyword detected in the customer question or the answer | No |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, caller_trust_level)
- [x] ConnectionPolicy (retry/timeout strategy — `max_retry: 3`, `timeout_seconds: 30`)
- [ ] SecurityViolationError (not raised directly by this template's domain logic)
- [x] S-2: framework default input gate — masks PII in `user_input` / `validated_input`
      (`detect_pii` / `mask_pii`) before `QueryNormalizeNode.execute()`; no domain hook.
- [x] S-3: `ResponseValidateNode.execute()` (last inner node) blocks an answer in which
      `detect_pii` finds contact data (email, phone, card, ...); the Latin-script `name`
      heuristic is ignored because it matches ordinary Title Case policy wording. No
      `_extra_security_gate_output()` hook: that hook only sees the node's own return dict.
- [x] S-4: `emit_trace_event()` — every node (outer and inner) emits ≥1 domain event per
      invocation path, including the `GraphNode` wrapper (via `extract_input()`/`merge_output()`
      hooks).

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass → framework `@final` gate always runs automatically;
>   extend via `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` / `RemoteAgentNode` → deliberate no-op (upstream or remote node's gate already applied)
> - Custom `BaseNode` subclass → must implement `_security_gate_input()` and
>   `_security_gate_output()` directly (`@abstractmethod` — omission raises `TypeError` at instantiation)

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — Cat 2 outer/inner pattern
- **Composition target**: `FaqPolicyWorkflowGraph` (`src/graph/domain_workflow_graph.py`),
  wrapped by `FaqPolicyGraphNode` in `src/graph/graph.py` `main` slot
- **Error propagation strategy**: `propagate` (fail fast — `FaqPolicyGraphNode.error_strategy =
  "propagate"`; no HITL, `propagate_hitl = False`)

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: `framework/` and `shared/` only (no `agents/base/` required)

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | AgentBaseGraph | Fixed pipeline (normalize → classify → retrieve → assemble → validate); no autonomous think-act loop is needed — termination is not self-directed. |
| Composition pattern | Flat 3-slot (Cat 1 style) | GraphNode + inner subgraph (Cat 2) | GraphNode + inner subgraph | Cat 2 requires `AgentBaseGraph` (outer) + `GraphNode` (main slot) wrapping a domain-specific inner `BaseGraph`; a flat `MainNode` ohm-ing 4 business steps would fail `gate-composition`. |
| KB retrieval backend | Live vector-store client (e.g. Qdrant) | Deterministic in-memory hybrid search | Deterministic in-memory (`KBRetrievalService`) | Keeps the template fully offline-testable (CI, local smoke) while preserving the same `search(query, top_k)` interface a real vector-store client would implement — swappable without touching node contracts. |
| Order-status handling | Live order/account API call | Hard-refuse redirect (no live call) | Hard-refuse redirect | Scope explicitly excludes order-status/account lookups; `IntentClassifyNode` routes these to a refusal message with no external call. |
