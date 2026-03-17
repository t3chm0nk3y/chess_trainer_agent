# Root Cause Analysis: Chessboard Not Updating on Move Navigation

## Symptom

On the Analysis page, selecting a game and using arrow keys (or clicking moves) correctly updates:
- The move highlight in the move table
- The ply counter (e.g., "3/73")
- The Move Detail panel (shows correct move, eval, phase)

But the **chess board visual remains frozen on the starting position**.

## Investigation Summary

### What works correctly
- **API data**: `/api/games/{id}` returns moves with valid `fen_after` values (confirmed via browser fetch)
- **React state**: `currentPly` updates correctly, `currentFen` is recomputed to the correct FEN string
- **Props delivery**: The `ChessBoard` wrapper component receives the correct `fen` prop
- **react-chessboard props**: The `<Chessboard>` component from react-chessboard receives the correct `position` prop (confirmed via React fiber inspection)
- **FEN parsing**: The library's `convertPositionToObject()` correctly parses the FEN into a position object

### What fails
- **DOM does not update**: `document.querySelectorAll('[data-square]')` always shows pieces on starting squares (e2=wP, d2=wP, etc.) even when position prop contains the correct post-move position (e4=wP, d4=wP)
- **No console errors**: No React errors, no DnD errors, nothing in console

### Attempted fixes (none worked)
1. **`key={fen}`** on `<Chessboard>` — forces full React remount on every position change. The component remounts but DOM still shows starting position.
2. **Pre-converted position object** — bypassed FEN string parsing entirely by converting FEN to a `BoardPosition` object in our wrapper and passing that. Same result.
3. **`animationDuration={0}`** — eliminated animation timing as a factor. Same result.

## Root Cause (High Confidence)

**React 19 incompatibility with react-chessboard v4.7.3 and/or react-dnd v16.0.1.**

### Evidence
- **React version**: 19.2.4
- **react-chessboard**: 4.7.3 (peer dep: `>=16.14.0`, but untested against React 19)
- **react-dnd**: 16.0.1 (last published well before React 19)

React 19 introduced breaking changes to:
- Internal fiber/reconciliation behavior
- `forwardRef` (now optional, behavior changes)
- Context and state batching
- `useDrag`/`useDrop` hooks from react-dnd rely on internal React APIs

The `ChessboardProvider` uses `useState(convertPositionToObject(position))` to initialize board state, and a `useEffect([position])` to animate updates. The internal `currentPosition` state — which drives piece rendering at line 4867 of the library source — never updates despite the effect firing. This is consistent with react-dnd's state management layer silently failing under React 19.

The `ChessboardDnDRoot` component (lines 5630-5644) also has a two-phase mount pattern (`backendSet` state + useEffect) that may interact poorly with React 19's stricter batching.

## Recommended Fix Options

### Option A: Replace react-chessboard (Recommended)
Use `chessboard.js` or a simpler SVG-based board that doesn't depend on react-dnd. Since we only need a **read-only display board** (no drag-and-drop), the DnD dependency is unnecessary overhead.

A lightweight alternative:
- **chessground** (used by Lichess) — framework-agnostic, battle-tested, no DnD dependency
- **Custom SVG board** — render 64 squares + piece images from a position object directly

### Option B: Downgrade React to 18.x
Change `react` and `react-dom` to `^18.2.0` in package.json. This would fix the react-dnd compatibility issue but limits access to React 19 features.

### Option C: Upgrade react-chessboard
Check if a newer version of react-chessboard (post-4.7.3) adds React 19 support. As of investigation date, this is unconfirmed.

### Option D: Fork/patch react-chessboard
Remove the react-dnd dependency from the library and render pieces directly from the position prop without DnD state management. Significant effort.

## Files Involved
- `frontend/src/components/ChessBoard.jsx` — our wrapper (currently has attempted fixes)
- `frontend/node_modules/react-chessboard/dist/index.esm.js` — library source (lines 472-588: state management, 4867: piece rendering)
- `frontend/package.json` — dependency versions
