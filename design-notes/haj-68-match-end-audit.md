# HAJ-68: Match-End Logic Audit

## Overview

Audit of the eight match-end paths across [match.py](../src/match.py), [referee.py](../src/referee.py), and [ne_waza.py](../src/ne_waza.py). There is no `scoring.py`. Tests live in [test_force_model.py](../tests/test_force_model.py) and [test_execution_quality.py](../tests/test_execution_quality.py).

## Path-by-path findings

### 1. Ippon → immediate match end — Implemented, tested
- Standing throw: [match.py:1605-1625](../src/match.py) (`win_method = "ippon"`, `match_over = True`)
- Pin: [match.py:1954-1967](../src/match.py) (`win_method = "ippon (pin)"`)
- Submission: [match.py:773-779](../src/match.py) (`win_method = "ippon (submission)"`), fired from [ne_waza.py:327](../src/ne_waza.py)
- Test: [test_force_model.py:213-214](../tests/test_force_model.py) asserts `win_method` set
- No bugs visible.

### 2. Two waza-ari (same fighter) → immediate end — Implemented, tested
- Standing: [match.py:1628-1649](../src/match.py) increments counter and checks `wa_count >= 2` → `win_method = "two waza-ari"`
- Pin: [match.py:1968-1980](../src/match.py) mirrors the same logic
- Test: [test_force_model.py:213-214](../tests/test_force_model.py) includes `"two waza-ari"` in expected set
- No bugs visible.

### 3. Time-expired, unequal waza-ari → decision — Partial
- Decision comparison: [match.py:2240-2249](../src/match.py) (`a_wa > b_wa` → `win_method = "decision"`)
- Trigger path: main loop [match.py:528-537](../src/match.py) exits naturally at `max_ticks`, then calls `_resolve_match()`
- Test: [test_force_model.py:192-214](../tests/test_force_model.py) `test_match_reaches_decision_within_240_ticks`
- **Gap:** time expiration is implicit (loop exit). No explicit Matte call or time-expired event fires at `tick == max_ticks`. Decision is computed post-loop only. Worth a follow-up ticket if referees are expected to announce matte at the horn.

### 4. Time-expired, equal waza-ari → golden score — Not implemented
- Draw branch: [match.py:2250-2253](../src/match.py) sets `win_method = "draw"` and prints *"Golden score pending (Phase 3)"*
- Comment at [match.py:217](../src/match.py) confirms golden-score overtime is "not yet wired"
- No state transition, no clock extension, no overtime loop
- No tests
- **Critical gap** — blocker for Paths 7 and 8.

### 5. Third shido → hansoku-make — Implemented, tested
- Kumi-kata passivity: [match.py:2127-2141](../src/match.py) (`shidos >= 3` → opponent wins, `win_method = "hansoku-make"`)
- General passivity: [match.py:2151-2165](../src/match.py) same logic
- Test: [test_force_model.py:213-214](../tests/test_force_model.py) includes `"hansoku-make"`
- No bugs visible.

### 6. Direct hansoku-make (dangerous technique / spirit violations) — Not implemented
- Zero code for illegal-technique detection, dangerous-technique flags, or spirit-of-judo violations
- Only route to hansoku-make is shido accumulation (Path 5)
- No tests
- **Critical gap.**

### 7. Golden score scoring event → scorer wins — Not implemented
- Blocked by Path 4. No overtime state exists, so no overtime scoring logic.

### 8. Golden score third shido → hansoku-make — Not implemented
- Blocked by Path 4. Shido logic (Path 5) would apply *if* golden score existed, but it does not.

## Summary

| Path | Code | Tests | Notes |
|---|---|---|---|
| 1. Ippon | Yes | Yes | — |
| 2. 2x waza-ari | Yes | Yes | — |
| 3. Decision on unequal WA | Partial | Yes | No explicit time-expiration event; decision computed only on loop exit |
| 4. GS transition on equal WA | No | No | Explicitly deferred to Phase 3 (match.py:2253) |
| 5. 3rd shido -> hansoku-make | Yes | Yes | — |
| 6. Direct hansoku-make | No | No | No illegal-technique framework exists |
| 7. GS scoring -> win | No | No | Blocked by Path 4 |
| 8. GS 3rd shido -> hansoku-make | No | No | Blocked by Path 4 |

**Fully covered:** 1, 2, 5
**Partial:** 3 (works in practice, but no explicit horn event)
**Missing:** 4, 6, 7, 8

No bugs found in implemented paths. The gaps are missing features, not defects. Follow-up tickets to be filed for Paths 3, 4, and 6.
