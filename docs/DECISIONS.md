# Architecture Decision Records

## ADR-001: API-First AI Agent Architecture (Unified Capability Registry)

**Date:** 2026-03-09
**Status:** Accepted

### Context

The chess trainer agent had two separate tool registries:
- `chat_tools.py` — 13 read-only tools for the chat agent
- `workflow_executor.py` — 28 internal tools for workflow pipelines

The chat agent could only observe data, not act on it. There was no unified capability discovery, and adding a new operation required changes in multiple places.

### Decision

Create a unified **capability registry** (`backend/capabilities/registry.py`) that replaces `chat_tools.py`. Each capability is a named operation with a handler, input schema, and metadata. The registry drives both:

1. **REST API** — `POST /api/capabilities/{name}` for any caller (frontend, scripts, integrations)
2. **Chat agent tools** — filtered subset of capabilities available during Claude conversations

Existing domain routes (`GET /api/games`, etc.) remain for the frontend. The workflow executor stays unchanged (internal plumbing).

### Consequences

**Positive:**
- Single place to add new operations — they're automatically available via REST and chat
- Chat agent gains write access (import, analyze, acknowledge, resolve)
- Capability discovery endpoint enables dynamic UI and agent introspection
- Cleaner separation: domain routers serve the frontend, capabilities serve programmatic access

**Negative:**
- Write capabilities in the chat agent require trust in the AI's judgment (mitigated by user confirmation in the chat UI)
- Two ways to access some operations (domain routes + capabilities) — acceptable since they serve different consumers

### Files Changed

| Action | File |
|--------|------|
| Created | `backend/capabilities/__init__.py` |
| Created | `backend/capabilities/registry.py` |
| Created | `backend/routers/capabilities.py` |
| Created | `tests/test_capabilities.py` |
| Modified | `backend/main.py` |
| Modified | `backend/services/chat_service.py` |
| Deleted | `backend/services/chat_tools.py` |
