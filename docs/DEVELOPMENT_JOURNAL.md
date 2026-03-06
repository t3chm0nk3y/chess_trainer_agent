# Development Journal Process
# Chess Trainer Agent

This document defines how work is recorded during development. Any developer (human or AI agent) working on this project should follow this process.

---

## Where Things Are Recorded

| What | Where | When to Update |
|------|-------|----------------|
| Task completions | `docs/PROGRESS.md` (phase checklist) | When a task moves to `[x]` |
| Daily work log | `docs/PROGRESS.md` (daily log section) | At the end of each work session |
| Key decisions | `docs/DECISIONS.md` | When a non-obvious choice is made |
| Blockers | `docs/PROGRESS.md` (daily log: Blockers) | As soon as identified |
| Architecture changes | `docs/ARCHITECTURE.md` | When components are added/changed |
| API changes | `docs/API_REFERENCE.md` | When endpoints are added/modified |
| Data model changes | `docs/DATA_MODEL.md` | When tables/columns change |
| Documentation changes | `docs/DOC_PLAN.md` (change tracking table) | When any doc is created/updated |

---

## Task Completion Recording

### Phase Checklist (PROGRESS.md)

Update the checkbox status as you work:

```markdown
- [ ] Not started
- [~] In progress (actively working on it)
- [x] Complete (code written, tests pass, verified)
- [!] Blocked (with reason noted in daily log)
```

### Definition of Done

A task is complete (`[x]`) when:
1. Code is written and passes `ruff check`
2. Tests exist for new logic and pass with `pytest`
3. API endpoints return correct responses
4. Related documentation is updated

---

## Daily Log Format (PROGRESS.md)

Add an entry at the end of each work session:

```markdown
### YYYY-MM-DD
- **Completed:**
  - Brief description of what was finished
  - Reference the task number (e.g., "2.1 Build OpeningStats computation logic")
- **In Progress:**
  - What is partially done and the current state
- **Decisions:**
  - Any non-trivial choices made and why (link to DECISIONS.md for details)
- **Blockers:**
  - What is preventing progress, on what task
  - What information or resolution is needed
- **Next Steps:**
  - Ordered list of what to work on next
```

---

## Decision Recording (DECISIONS.md)

Create `docs/DECISIONS.md` when the first decision needs recording. Format:

```markdown
### DEC-NNN: Short Title

**Date:** YYYY-MM-DD
**Status:** Accepted | Superseded by DEC-XXX | Revisiting
**Context:** What situation prompted this decision
**Decision:** What was chosen
**Alternatives Considered:** What else was evaluated
**Rationale:** Why this choice was made
**Consequences:** What this means going forward
```

Examples of decisions worth recording:
- Choosing direct Stockfish over ChessAgine MCP (already made)
- Choosing a specific data structure or algorithm
- Changing the API contract from what the SRS specifies
- Adding or removing a dependency
- Deviating from the planned phase order

---

## Blocker Recording

Blockers get recorded in two places:

1. **Immediately** in `docs/PROGRESS.md` daily log under "Blockers"
2. **In the phase checklist** by changing `[ ]` to `[!]`

A blocker entry should include:
- What task is blocked
- What the blocking issue is
- What resolution path is being considered
- Whether external input is needed (and from whom)

When a blocker is resolved, note the resolution in the next daily log entry.

---

## Process for a Typical Work Session

1. **Start:** Read `docs/PROGRESS.md` to see current state and next steps
2. **Work:** Implement tasks, updating checklist status as you go
3. **Decide:** If you make a non-obvious choice, note it for DECISIONS.md
4. **Blocked?** Record immediately in the daily log
5. **End:** Write the daily log entry
6. **Update docs:** If you changed architecture, API, or data model, update the relevant doc
7. **Update DOC_PLAN.md:** Add a row to the change tracking table for any doc changes

---

## For Claude Code Agents Specifically

When operating as a Claude Code agent on this project:

- **Before starting work:** Read `docs/PROGRESS.md` to understand current state
- **After completing a task:** Update the checklist and write a daily log entry
- **When making design choices:** Record them -- future sessions won't have your context
- **When hitting a blocker:** Record it clearly so the next session (or a human) can resolve it
- **Keep docs accurate:** If your code changes contradict existing documentation, update the docs

The goal is that any new session (human or AI) can read the docs and immediately understand:
- What has been done
- What is being worked on
- What decisions were made and why
- What is blocked and what needs to happen next
