# Viewer audit — April 2026 (HAJ-153)

Audit of the Pygame top-down match viewer (`src/match_viewer.py`) against
the current simulation event log. The audit covers Tanaka (LEVER, Seoi /
Harai-goshi specialist, BLACK_1) vs Sato (MOTOR, Uchi-mata specialist,
BLACK_1) with the Suzuki-sensei referee — the canonical default match
established in `data-model.md`.

This document is the v1 baseline produced for HAJ-153. Each cluster
ticket from HAJ-152 onward extends it with its own viewer obligations
per the "Viewer Considerations" section pattern; this audit catches up
the pre-HAJ-152 drift and documents the fixes shipped under HAJ-153
itself.

---

## Methodology

- Ran ten matches with seeds spanning the standard test set (1, 5, 7,
  11, 13, 17, 19, 23, 42, 99) using `python src/main.py --runs 1
  --seed <seed> --viewer --viewer-tps 6`.
- Read the engine `--stream debug` log alongside the rendered viewer.
- Compared every distinct `event_type` emitted in the engine log to
  whether the viewer rendered any visible counterpart.
- Cross-referenced the HAJ-144 t017–t018 (waza-ari → reset),
  t003 (symmetric grips), and stuffed-throw → ne-waza chains.

---

## Findings

Each finding has: log evidence, viewer behaviour pre-fix, fix landed in
HAJ-153 (or forwarded to a follow-up ticket).

### F1 — Per-fighter state indicator missing

**Log:** `position` enum transitions on every state-machine boundary
(STANDING_DISTANT → GRIPPING → ENGAGED → NE_WAZA → ...). The summary
sidebar already shows the dyad-level position, but the *per-fighter*
state (e.g. who's chasing, who's stuffed, who's mid-throw) requires
piecing together log lines.

**Viewer pre-fix:** sidebar lists `position: GRIPPING` etc. once. No
near-figure label; readers couldn't tell at a glance who was in
desperation, who'd just been stuffed, who was committing a throw.

**Fix:** Added per-fighter state-indicator labels rendered at the
fighter's CoM dot. Pulls from existing viewer-snapshot fields
(`stun_ticks`, `off_desperation`, `def_desperation`, in-progress
throw_id, grip count) and surfaces a one-or-two-word tag like
`STUNNED`, `DEF-DESP`, `THROW`, `GRIPS-3`, `DISTANT`. Updates each
tick with the live snapshot.

### F2 — Match clock and tick counter wired to render-loop, not sim

**Log:** Engine's `tick` is the authoritative counter (HAJ-148
contract).

**Viewer pre-fix:** Sidebar already showed `tick` from the snapshot,
but the clock string was computed from `view.tick` and `view.max_ticks`
inside `_draw_summary`. Verified the values match exactly when the
engine pauses (manual paused-step test): viewer's clock pauses with
the engine. **No fix needed** — the existing wiring is already
authoritative. Documented to close the audit checklist.

### F3 — Score display update timing

**Log:** Score events fire on the landing tick (HAJ-148 contract); for
N=1 throws the score and the THROW_LANDING share a tick. HAJ-152 added
the POST_SCORE_FOLLOW_UP_OPEN event on the same tick.

**Viewer pre-fix:** Sidebar shows `waza-ari` count from the snapshot.
The snapshot is captured during `update()` which runs at the end of
the tick, so the score display ticks up on the same tick as the score
event. Verified by running a forced-WAZA_ARI integration: snapshot at
tick T shows the new count. **No fix needed.**

### F4 — Matte event has no visual cue

**Log:** `[ref] Matte! (...)` fires as `MATTE_CALLED`. With HAJ-152 the
post-score reset path also fires `MATTE_CALLED` with reason
`POST_SCORE_FOLLOW_UP_END`. With HAJ-148, stuffed-throw timeout matte
also surfaces.

**Viewer pre-fix:** Matte was visible only as a line of ticker text.
No banner, no flash, no centered overlay; readers had to scan the
ticker to spot a matte.

**Fix:** Added a centered MATTE banner overlay on the mat panel.
Banner renders for ~2 seconds (12 frames at 6 tps; scales with tps)
following any `MATTE_CALLED` event. Reason text appended in smaller
font ("stalemate" / "post-score reset" / "stuffed throw — reset" /
"out of bounds" / "osaekomi decision"). HAJ-152's
POST_SCORE_FOLLOW_UP_END matte is now visually distinguishable from
ne-waza-stalemate matte.

### F5 — Symmetric grip seating (HAJ-144 t003) invisible

**Log:** Up to four `GRIP_ESTABLISH` events firing on a single tick
when both fighters seat both hands simultaneously.

**Viewer pre-fix:** The grip lines updated correctly, but
because all four lines appeared on the same frame with no flash, the
"too many grips at once" anomaly didn't visually pop. The viewer
showed a complete dyad of grips without indicating it was unusual.

**Fix:** Added a "grip-seat flash" — when 3+ `GRIP_ESTABLISH` events
fire on a single tick, the affected grip lines flash brighter and a
small warning marker (yellow ring) appears at each fighter's CoM for
~0.5 second. Lets the t003 reproduction visually surface as
"something is firing too fast" without needing to read the log.

### F6 — Stuff event has no impact cue

**Log:** `STUFFED` event description, `[throw] X stuffed on Y — Z
defends. Ne-waza window open.`

**Viewer pre-fix:** Visible only as a ticker line.

**Fix:** Added a stuff impact cue — the stuffed fighter's CoM dot
flashes red for ~0.5 second on a `STUFFED` event, mirroring the
existing kuzushi flash. Combined with the kuzushi halo (which often
also fires on a stuff because the attacker becomes off-balance), the
fighter clearly registers as "just got driven into the mat."

### F7 — Reset / score-reset is a snap, not a walk-back

**Log:** `SCORE_RESET` (post-score) and `MATTE_CALLED` events trigger
`_reset_dyad_to_distant`, which sets each fighter's CoM to (-0.5, 0)
and (+0.5, 0).

**Viewer pre-fix:** Fighters teleport from wherever they were
(possibly mid-mat) to the centre line in a single frame. Looks like
a teleport, not a walk-back.

**Fix:** Added position interpolation between snapshots
(see F11). Combined with the new MATTE banner (F4), the reset now
plays as: matte banner appears → fighters tween from their last
position back to the centre over the tick interval → banner fades out
→ next tick begins. The visual cue is much clearer.

### F8 — Ne-waza positions visually undifferentiated

**Log:** `NEWAZA_TRANSITION` event with `start_pos` field set to
`GUARD_TOP`, `SIDE_CONTROL`, `MOUNT`, `BACK_CONTROL`, `TURTLE_TOP`,
`TURTLE_BOTTOM`. Position machine transitions between these as the
ground exchange develops.

**Viewer pre-fix:** Both fighters render as CoM dots regardless of
position. No way to tell from the viewer alone whether the dyad is
in `GUARD_TOP` vs `SIDE_CONTROL` vs `MOUNT`.

**Fix:** Added a ne-waza position label rendered at the dyad
midpoint when `sub_loop_state == NE_WAZA`, plus a small icon-style
schematic (top fighter as larger dot, bottom as smaller dot, line
between them indicating relative orientation). Distinguishes the four
most common ne-waza positions at a glance. The dominant fighter
(top) is shown in the larger dot; the bottom fighter is offset
beneath it.

### F9 — Post-score follow-up window has no visual cue (HAJ-152)

**Log:** HAJ-152 added `POST_SCORE_FOLLOW_UP_OPEN`, `CHASE_DECISION`,
`DEFENSE_DECISION`, `POST_SCORE_FOLLOW_UP_MATTE` events. While the
window is open, neither fighter can fire a fresh commit.

**Viewer pre-fix:** Visible only as ticker lines. No on-mat
indication that a follow-up window is pending.

**Fix:** Added a follow-up-window pill above the scoring fighter for
the duration of the follow-up state — text reads `CHASING` / `STAND` /
`DEFENSIVE` based on the chase decision once it's been computed; while
the decision is pending it reads `FOLLOW-UP`. Closes when
`_post_score_follow_up` clears (via matte, escape, or match end).

### F10 — Counter-commit visually undifferentiated from a normal commit

**Log:** `COUNTER_COMMIT` event has its own type; HAJ-157 V2 routes
the counter through staging so an INTENT_SIGNAL precedes the counter
THROW_ENTRY by one tick.

**Viewer pre-fix:** Counter throws looked indistinguishable from
regular commits in the viewer.

**Fix:** Added a brief counter-arrow visualization — when
`COUNTER_COMMIT` fires, a yellow chevron renders between the two
fighters for ~0.8 second pointing from the defender (counter-attacker)
to the original attacker. Reads as "this fighter just turned the
attack around."

### F11 — Position changes look like teleports

**Log:** `_apply_physics_update` mutates `com_position` once per tick,
producing per-tick position deltas that range from millimetres
(grip-tug noise) to ~0.3 m (locomotion + force impulses).

**Viewer pre-fix:** Each frame draws the latest snapshot's
`com_position` directly. With 60 FPS render and ~6 tps simulation,
the same snapshot was drawn for 10 frames before the next tick
swapped in — visible as an instant jump every ten frames.

**Fix:** Added position interpolation between consecutive snapshots.
The renderer tracks the wall-clock fraction of the current tick
(`_wall_t_last_step`-derived) and tweens fighter CoM and hand
positions linearly between the previous snapshot and the live one.
Trail rendering still samples the snapshots directly so the trail
remains a faithful per-tick history. In review mode, interpolation
is disabled (each scrub-step lands on a discrete snapshot).

### F12 — Locomotion-side gap (forwarded to HAJ-157 / HAJ-156)

**Log + viewer:** Even with interpolation (F11) live, fighters spend
most of the match within a ~1 m square around the centre. The
locomotion layer (HAJ-128) does emit STEP actions, but the
displacement per tick is small enough that the static-figures
complaint Comrade flagged in HAJ-144 is partially a *simulation-side*
issue, not a presentation issue.

**Disposition:** Forwarded to **HAJ-156** (the renumbered movement +
locomotion ticket; in this repo's commit history that work has
already shipped under HAJ-148/156-equivalent locomotion in
`action_selection`). For HAJ-153 we ship interpolation to remove the
*presentation*-layer teleport feel; the underlying per-tick mat
displacement is governed by the simulation and will be revisited in
its own ticket.

### F13 — Intent signals (HAJ-149) have no visual representation

**Log:** `INTENT_SIGNAL` events fire one tick before the actual
THROW_ENTRY. `PERCEPTION_BRACE` fires when the perceiver reads it.

**Viewer pre-fix:** No visual cue.

**Disposition:** Forwarded to a follow-up viewer ticket. HAJ-149's
own viewer obligation per the cluster pattern lands the visualization
(ghost-arrow or equivalent) in its own scope. For HAJ-153 we leave
the intent signals as ticker-only and add a TODO marker in the
audit follow-up section below.

---

## Follow-up forwarded items

| Finding | Forwarded to | Notes |
| ------- | ------------ | ----- |
| F12 — locomotion sparseness | HAJ-156 (movement + locomotion) | Simulation-side; the interpolation fix covers the presentation half. |
| F13 — intent signals not rendered | HAJ-149 viewer obligation | Ghost-arrow visualization is the intent ticket's scope. |
| Ne-waza body shapes | Ring-5 polish | Ne-waza schematic is intentionally abstract; pixel-art body shapes are post-EA polish per the master doc. |

---

## Verification pass

After landing the F1, F4, F5, F6, F8, F9, F10, F11 fixes, the same
ten seeds were re-run:

- **Seed 13** (HAJ-152 verification): waza-ari → CHASE → ne-waza
  transition all visible as: state pill change → MATTE banner not
  fired (chase path) → ne-waza schematic appears → escape → return to
  centre. Reads exactly as the engine log does.
- **Seed 11** (counter-storm): COUNTER_COMMIT chevrons fire correctly
  at the trigger ticks, distinguishing the counter from the original
  attempt.
- **Seed 99** (multi-stuff): both stuffs flash on the same tick; the
  ne-waza door (with HAJ-157 dedupe) fires once.

All ten seeds pass the viewer-log parity check.

---

## Acceptance criteria coverage

- [x] AC#1 — Audit document produced (this file).
- [x] AC#2 — Per-fighter state indicator (F1).
- [x] AC#3 — Match clock / tick counter wired to simulation (F2).
- [x] AC#4 — Score display updates on score-fire tick (F3).
- [x] AC#5 — Matte event banner + visible separation (F4 + F11).
- [x] AC#6 — Grip events render at hand-to-target lines (existing
      HAJ-128 wiring, plus F5 flash for the symmetric-seat case).
- [x] AC#7 — Ne-waza positions visually distinguishable (F8).
- [x] AC#8 — Stuff and reset events have visual cues (F6 + F11).
- [x] AC#9 — Position interpolation between ticks (F11).
- [x] AC#10 — Movement findings forwarded (F12 → HAJ-156).
- [x] AC#11 — No simulation regression (full pytest suite green
      before and after).
- [x] AC#12 — Tanaka vs. Sato baseline match works end-to-end.
