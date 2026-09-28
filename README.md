# RET-C2-053 — Retail FAQ and Policy Q&A Agent

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific use case)
> **Industry**: RET

## Overview

A retail customer (or a store support agent) asks a question about store policy: returns,
exchanges, shipping, warranty, opening hours. The agent answers from a small FAQ and policy
knowledge base, cites the entries it used, refuses order-status and account questions, and adds
a hand-off note when the customer's wording asks for a human.

Input is a plain question string in English or Japanese, for example:

```text
What is your return policy for items bought with a receipt?
```

The output is the answer text with a `(Sources: ...)` footer listing the knowledge-base entry
ids, plus a hand-off note when escalation was flagged.

How it works today:

- **Query normalisation** (outer `pre_process`): rejects empty input, detects Japanese vs
  English, and builds the envelope for the inner workflow. The framework input gate masks
  contact details (email, phone numbers, ...) before this step runs.
- **Inner workflow** (a `GraphNode` in the `main` slot):
  1. classifies the question: order-status and account questions (for example "track my order",
     注文状況) are answered with a fixed redirect message and never reach retrieval. This template
     makes no order or account API call;
  2. retrieves entries by keyword and token overlap over the bundled knowledge base in
     `src/services/kb_retrieval_service.py`. There is no embedding search;
  3. answers with the text of the best-scoring entry (or a fixed "couldn't find" message);
  4. validates the answer: an answer in which the framework PII detector finds contact data is
     blocked with an error, and escalation words in the question or the answer (for example
     "complaint", "lawyer", 苦情) set the escalation flag.
- **Formatting** (outer `post_process`) adds the source footer and the hand-off note.

The bundled knowledge base is five sample policy entries with English keywords. Replace it with
your own policies before use. Because matching is on English keywords, a Japanese policy
question currently gets the Japanese "couldn't find" message; Japanese order-status questions
are still recognised and redirected. The source footer lists every retrieved entry, not only the
one whose text is returned.

No model is used. `ResponseAssembleNode` accepts an optional client, but the graph does not pass
one, so answers are always the deterministic entry text described above.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
