# Software Requirements Specification (SRS)
# Chess Trainer Agent
**Version:** 1.0
**Date:** 2026-03-06
**Status:** Draft

---

## 1. Introduction

### 1.1 Purpose
This document defines the requirements for the Chess Trainer Agent, a personal chess coaching application that analyzes game history, identifies recurring mistakes, and tracks improvement over time. It serves as the ground truth for all development effort.

### 1.2 Core Problem Statement
Players repeat the same mistakes across games without realizing it. These recurring errors -- in openings, middlegame strategy, tactics, and endgames -- are the primary barrier to rating progression. The Chess Trainer Agent must surface these patterns clearly and persistently until the player has demonstrably addressed them.

### 1.3 Scope
The application imports chess games from external sources (Lichess, Chess.com, PGN files), analyzes them using engine evaluation and AI-powered pattern recognition, categorizes mistakes, tracks which mistakes recur, and provides actionable feedback to the player.

### 1.4 Definitions

| Term | Definition |
|------|-----------|
| **Mistake** | A move where the engine evaluation drops beyond a defined threshold (inaccuracy, mistake, or blunder) |
| **Pattern** | A recurring type of mistake observed across multiple games, identified by AI analysis |
| **Acknowledgment** | An explicit player action confirming they have seen and understood a recurring pattern |
| **Opening Line** | A specific sequence of moves in the opening phase, typically identified by ECO code and variation name |
| **Game Phase** | One of: opening, middlegame, endgame -- determined by piece count and move number heuristics |

---

## 2. System Overview

### 2.1 Architecture
- **Backend:** FastAPI (Python 3.11+) with SQLAlchemy ORM and SQLite
- **Frontend:** React 19 + Vite with react-chessboard and recharts
- **AI Engine:** Claude API (Anthropic) for mistake annotation and pattern synthesis
- **Chess Engine:** Stockfish via ChessAgine MCP for position evaluation
- **Workflow Engine:** FastMCP-based workflow orchestration server
- **External APIs:** Lichess API, Chess.com API for game import

### 2.2 Existing Codebase State
The scaffolding exists with working game import (Lichess), PGN parsing, move classification logic, Claude integration for annotation/synthesis, database models, and workflow definitions in YAML. Key gaps: ChessAgine MCP integration (engine eval), Chess.com import, workflow execution, frontend implementation, and the specific features described in this SRS.

---

## 3. Functional Requirements

### 3.1 Opening Line Loss Analysis (FR-OPN)

**Goal:** Allow the player to see which opening lines produce the most losses, down to the specific variation and divergence move.

#### FR-OPN-1: Opening Tree Construction
The system shall build a tree of opening lines from all imported games, grouped by ECO code and variation name. Each node in the tree represents a move in the opening sequence.

#### FR-OPN-2: Win/Loss/Draw Statistics Per Line
For each opening line (defined as a unique sequence of moves through the opening phase), the system shall compute:
- Total games played
- Win / Loss / Draw count and percentage
- Average centipawn loss during the opening phase
- The **divergence move** -- the specific move number where the player's results begin to deteriorate compared to the mainline

#### FR-OPN-3: Loss-Ranked Opening Report
The system shall provide an API endpoint and frontend view that ranks opening lines by loss percentage, allowing the player to immediately see their worst-performing openings. Example output:
> "Pirc Defense, Classical Variation (B08): 12 games, 75% loss rate. You typically go wrong at move 9 (...Nbd7 instead of ...e5)."

#### FR-OPN-4: Opening Line Drill-Down
The player shall be able to click on any opening line to see:
- All games that followed that line
- The specific move where the player deviated from the most successful continuation
- Engine evaluation at the critical divergence point

---

### 3.2 Mistake Categorization and Reporting (FR-CAT)

**Goal:** Produce a structured report of mistakes organized by game phase and mistake type, highlighting which mistakes are repeated.

#### FR-CAT-1: Two-Axis Mistake Classification
Every identified mistake shall be classified along two axes:

**Axis 1 -- Game Phase:**
- Opening (determined by ECO/move number/piece development)
- Middlegame (determined by piece count and board state)
- Endgame (determined by reduced material)

**Axis 2 -- Mistake Type:**
- Tactical (missed tactic, hung piece, failed combination, missed fork/pin/skewer)
- Strategic (bad pawn structure, poor piece placement, weak square control, wrong plan)

These two axes combine into six categories:
| | Tactical | Strategic |
|---|---|---|
| **Opening** | Opening tactical errors | Opening strategic errors |
| **Middlegame** | Middlegame tactical errors | Middlegame strategic errors |
| **Endgame** | Endgame tactical errors | Endgame strategic errors |

#### FR-CAT-2: Mistake Type Extensibility
The mistake type axis shall be implemented as a **hierarchical, extensible taxonomy** stored in a configuration structure (database table or config file), not hardcoded. This allows future additions such as:
- Time management mistakes (moving too fast/slow at critical moments)
- Psychological patterns (blundering after gaining advantage, playing passively when behind)
- Calculation depth issues (missing moves at depth 3+)
- Prophylaxis failures (not considering opponent's threats)

Each category in the taxonomy shall have:
- `id` (unique identifier)
- `parent_id` (nullable, for hierarchy)
- `name` (display name)
- `description` (what this category means)
- `detection_method` (how the system identifies this type: engine-based, AI-based, or hybrid)
- `active` (boolean, allows enabling/disabling categories)

#### FR-CAT-3: Categorized Mistake Report
The system shall generate a report (API endpoint + frontend view) containing:
- Mistake counts per category (the 6-cell matrix above, extensible)
- For each category: the top 3 most-repeated specific mistakes with example positions
- Overall accuracy metrics broken down by phase and type
- Trend over time (is the player improving in each category?)

#### FR-CAT-4: Repeat Frequency Tracking
Each identified pattern shall track:
- `frequency` -- total number of occurrences
- `first_seen` -- date of first occurrence
- `last_seen` -- date of most recent occurrence
- `occurrence_game_ids` -- list of games where it appeared
- `acknowledged` -- whether the player has acknowledged this pattern
- `post_acknowledgment_count` -- occurrences after the player acknowledged the pattern

---

### 3.3 Recent Game Repeated-Mistake Notifications (FR-NOT)

**Goal:** When reviewing a recent game, the player sees immediate, prominent notifications for any mistakes that match previously identified patterns.

#### FR-NOT-1: Automatic Pattern Matching on Analysis
When a game is analyzed (either on import or manually triggered), the system shall automatically compare each mistake against all known active patterns using Claude AI.

#### FR-NOT-2: Inline Notifications on Game Review
When viewing a game's move list, any move that matches a known pattern shall be visually flagged with:
- The pattern name/label
- How many times this pattern has occurred before
- Whether it was previously acknowledged
- A severity indicator (based on centipawn loss and recurrence)

#### FR-NOT-3: Game Summary Notification Panel
When viewing a recently analyzed game, the system shall display a summary panel showing:
- Total repeated mistakes found in this game
- List of matched patterns with occurrence count
- Any **new** patterns detected for the first time
- Comparison to the player's recent average (better/worse)

#### FR-NOT-4: Notification Priority
Notifications shall be ordered by:
1. Previously acknowledged but recurring patterns (highest priority -- player said they'd fix it)
2. High-frequency unacknowledged patterns
3. New patterns detected for the first time
4. Low-frequency patterns

---

### 3.4 Mistake Acknowledgment System (FR-ACK)

**Goal:** Allow the player to explicitly acknowledge identified patterns, creating a clear record of awareness. If the pattern recurs after acknowledgment, it is flagged with higher severity.

#### FR-ACK-1: Acknowledge Action
The player shall be able to acknowledge any identified pattern via a dedicated UI action. Acknowledgment records:
- `pattern_id`
- `acknowledged_at` (timestamp)
- `player_note` (optional free-text: what the player plans to do about it)

#### FR-ACK-2: Acknowledgment State Display
Each pattern shall display one of three states:
- **New** -- Pattern identified but not yet acknowledged
- **Acknowledged** -- Player has seen it and confirmed awareness
- **Recurring** -- Pattern has occurred again after acknowledgment (elevated severity)

#### FR-ACK-3: Post-Acknowledgment Tracking
After a pattern is acknowledged, the system shall separately track any new occurrences. The `post_acknowledgment_count` field increments for each new match. These post-acknowledgment recurrences shall:
- Appear with heightened visual emphasis in game review
- Be called out explicitly in the game summary panel
- Factor into the progress report as "unresolved acknowledged patterns"

#### FR-ACK-4: Resolution
A pattern may be marked as **resolved** (manually by the player or automatically if no occurrences in N games, configurable). Resolved patterns move to a historical archive but can be re-activated if they recur.

---

### 3.5 Progress Tracking (FR-PRG)

**Goal:** Track improvement over time across sessions and days.

#### FR-PRG-1: Progress Snapshots
The system shall create progress snapshots that capture:
- Date
- Games analyzed in period
- Overall accuracy (% of moves classified as "best" or "good")
- Accuracy by phase (opening / middlegame / endgame)
- Active pattern count
- Acknowledged pattern count
- Recurring (post-acknowledgment) pattern count
- Patterns resolved since last snapshot

#### FR-PRG-2: Session Tracking
The system shall support session-based grouping of games (e.g., "games played on March 6, 2026") to allow end-of-day review.

#### FR-PRG-3: Progress Dashboard
The frontend shall display:
- Accuracy trend chart (overall and per-phase) over time
- Pattern resolution rate (how many patterns have been fixed)
- "Unresolved acknowledged patterns" count as a key metric
- Comparison of current session to trailing average
- Opening performance trend (worst openings improving or not)

#### FR-PRG-4: Day-to-Day and Session-to-Session Comparison
The player shall be able to compare two time periods side by side:
- Accuracy differences
- New patterns vs resolved patterns
- Opening line performance changes

---

## 4. Non-Functional Requirements

### 4.1 Performance
- Game import and PGN parsing shall complete within 5 seconds for up to 100 games
- Engine analysis shall process at minimum 1 game per minute (dependent on ChessAgine MCP)
- Pattern synthesis (Claude API call) shall complete within 30 seconds
- Frontend shall render game review with annotations within 2 seconds

### 4.2 Data Integrity
- All game imports shall be deduplicated by source_id
- Pattern matching results shall be deterministic given the same inputs and Claude model
- Progress snapshots shall be immutable once created

### 4.3 Extensibility
- Mistake taxonomy shall be configurable without code changes (FR-CAT-2)
- New game sources (beyond Lichess/Chess.com) shall be addable via the existing MCP client pattern
- Workflow definitions shall be modifiable via YAML without code changes

### 4.4 Usability
- Game review with notifications shall require no more than 2 clicks from the main dashboard
- Acknowledging a pattern shall be a single-click action
- All reports shall be accessible from a top-level navigation menu

---

## 5. Data Model Changes Required

The following changes to the existing data model (backend/models.py) are required:

### 5.1 New Table: MistakeCategory
```
MistakeCategory
  id: int (PK)
  parent_id: int (FK -> MistakeCategory.id, nullable)
  name: str
  description: str
  detection_method: str (engine | ai | hybrid)
  active: bool (default True)
```

### 5.2 New Table: PatternAcknowledgment
```
PatternAcknowledgment
  id: int (PK)
  pattern_id: int (FK -> Pattern.id)
  acknowledged_at: datetime
  player_note: str (nullable)
```

### 5.3 New Table: OpeningStats
```
OpeningStats
  id: int (PK)
  eco_code: str
  opening_name: str
  variation_name: str (nullable)
  move_sequence: str (JSON -- array of SAN moves defining this line)
  total_games: int
  wins: int
  losses: int
  draws: int
  avg_cp_loss: float (nullable)
  divergence_move: int (nullable -- typical move number where player goes wrong)
  last_updated: datetime
```

### 5.4 Modifications to Existing Tables

**Pattern table additions:**
- `category_id: int (FK -> MistakeCategory.id)` -- replaces free-text category field
- `mistake_type: str` -- tactical | strategic (second axis)
- `post_acknowledgment_count: int (default 0)`
- `acknowledged: bool (default False)`
- `acknowledged_at: datetime (nullable)`

**Move table additions:**
- `mistake_type: str (nullable)` -- tactical | strategic

**ProgressSnapshot additions:**
- `accuracy_opening: float (nullable)`
- `accuracy_middlegame: float (nullable)`
- `accuracy_endgame: float (nullable)`
- `acknowledged_patterns: int`
- `recurring_patterns: int`
- `resolved_patterns: int`
- `session_id: str (nullable)` -- groups games by play session

---

## 6. API Endpoints Required

### 6.1 Opening Analysis
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/openings` | List all opening lines with win/loss/draw stats, sorted by loss % |
| GET | `/api/openings/{eco_code}` | Drill-down into a specific opening with game list and divergence analysis |
| POST | `/api/openings/refresh` | Recalculate opening statistics from all analyzed games |

### 6.2 Mistake Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reports/mistakes` | Full categorized mistake report (matrix view) |
| GET | `/api/reports/mistakes?phase={phase}&type={type}` | Filtered by phase and/or type |
| GET | `/api/reports/repeated` | Repeated mistakes only, ordered by frequency |

### 6.3 Notifications
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/games/{game_id}/notifications` | Get pattern-match notifications for a specific game |
| GET | `/api/notifications/recent` | Get notifications from the most recently analyzed game |

### 6.4 Acknowledgments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/patterns/{pattern_id}/acknowledge` | Acknowledge a pattern (body: optional player_note) |
| DELETE | `/api/patterns/{pattern_id}/acknowledge` | Revoke acknowledgment |
| POST | `/api/patterns/{pattern_id}/resolve` | Mark pattern as resolved |
| GET | `/api/patterns/acknowledged` | List all acknowledged but unresolved patterns |

### 6.5 Progress
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/progress/sessions` | List play sessions with summary stats |
| GET | `/api/progress/compare?from={date}&to={date}` | Compare two time periods |

---

## 7. Implementation Phases

### Phase 1: Foundation (Engine Analysis + Data Model)
**Goal:** Get engine evaluation working so all downstream features have data.

1. Integrate ChessAgine MCP or direct Stockfish for position evaluation
2. Implement the data model changes from Section 5
3. Seed the MistakeCategory table with the initial taxonomy
4. Update `analysis_worker.py` to populate engine evals, classifications, and phases
5. Verify end-to-end: import game -> analyze -> moves have evals and classifications

**Deliverable:** Games can be imported and fully analyzed with engine evaluations.

### Phase 2: Opening Line Analysis (FR-OPN)
**Goal:** Surface worst-performing openings.

1. Build `OpeningStats` computation logic (aggregate from analyzed games)
2. Implement `/api/openings` endpoints
3. Build frontend opening report view
4. Add divergence move detection (compare player moves to most successful continuations)

**Deliverable:** Player can see ranked list of openings by loss rate with drill-down.

### Phase 3: Mistake Categorization (FR-CAT)
**Goal:** Produce the categorized mistake report.

1. Implement two-axis classification (phase already exists; add tactical vs strategic via Claude)
2. Build `/api/reports/mistakes` endpoint
3. Build frontend report view (matrix + drill-down)
4. Add trend-over-time computation per category

**Deliverable:** Player can view categorized mistake report with repeat tracking.

### Phase 4: Notifications + Acknowledgment (FR-NOT, FR-ACK)
**Goal:** Flag repeated mistakes in game review and let the player acknowledge them.

1. Implement automatic pattern matching on game analysis completion
2. Build `/api/games/{game_id}/notifications` endpoint
3. Build `/api/patterns/{id}/acknowledge` endpoints
4. Implement post-acknowledgment tracking
5. Build frontend game review with inline notifications
6. Build game summary notification panel

**Deliverable:** Player sees repeated mistake warnings during game review and can acknowledge them.

### Phase 5: Progress Tracking (FR-PRG)
**Goal:** Track improvement across sessions and over time.

1. Implement enhanced progress snapshots (per-phase accuracy, acknowledgment counts)
2. Build session grouping logic
3. Build `/api/progress/sessions` and `/api/progress/compare` endpoints
4. Build frontend progress dashboard with charts
5. Implement period comparison view

**Deliverable:** Player can track progress day-to-day and session-to-session.

### Phase 6: Polish and Integration
**Goal:** End-to-end workflow execution, Chess.com import, UX refinement.

1. Wire up workflow execution engine (connect YAML definitions to service calls)
2. Implement Chess.com game import
3. Frontend navigation, responsive design, error handling
4. Auto-resolution of patterns (configurable threshold)
5. Testing and documentation

**Deliverable:** Complete, polished application.

---

## 8. Progress Tracking for Development

Development progress will be tracked using the following convention:

### 8.1 Phase Checklist
Each phase has numbered tasks. Track completion in `docs/PROGRESS.md` with:
- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete
- `[!]` Blocked

### 8.2 Daily Log
Maintain a daily log in `docs/PROGRESS.md` recording:
- Date
- Tasks completed
- Tasks in progress
- Blockers
- Next steps

### 8.3 Definition of Done
A task is complete when:
- Code is written and passes linting (`ruff check`)
- Tests exist for new logic (pytest)
- API endpoints return correct responses (verified via manual or automated test)
- Frontend components render correctly (if applicable)

---

## 9. Acceptance Criteria Summary

| Requirement | Acceptance Criteria |
|---|---|
| FR-OPN | Player can view openings ranked by loss %, drill into specific lines, see divergence move |
| FR-CAT | Mistake report shows 6-category matrix (phase x type), extensible taxonomy, repeat counts |
| FR-NOT | Game review shows inline pattern-match flags; summary panel shows all repeated mistakes |
| FR-ACK | Player can acknowledge patterns; post-acknowledgment recurrences are flagged with elevated severity |
| FR-PRG | Progress dashboard shows accuracy trends, pattern resolution rate, session comparison |

---

## Appendix A: Existing Codebase Inventory

| Component | Status | File(s) |
|---|---|---|
| Database + ORM | Complete | `backend/database.py`, `backend/models.py` |
| PGN Parsing | Complete | `backend/services/pgn_parser.py` |
| Move Classification | Complete | `backend/services/classifier.py` |
| Lichess Import | Complete (direct API) | `backend/services/lichess_api.py` |
| Claude Integration | Complete | `backend/services/claude_agent.py` |
| Pattern Engine | Complete | `backend/services/pattern_engine.py` |
| Analysis Worker | Partial (needs engine) | `backend/tasks/analysis_worker.py` |
| Game CRUD API | Complete | `backend/routers/games.py` |
| Pattern API | Partial | `backend/routers/patterns.py` |
| Progress API | Complete (basic) | `backend/routers/progress.py` |
| Workflow MCP Server | Complete (server only) | `workflow-mcp/server.py` |
| Workflow Definitions | Defined (not wired) | `workflow-mcp/workflows/*.yaml` |
| MCP Client | Stubbed | `backend/services/mcp_client.py` |
| Chess.com Import | Stubbed | N/A |
| Frontend | Dependencies only | `frontend/package.json` |
