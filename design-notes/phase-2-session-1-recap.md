# Phase 2 Session 1 Recap
## Throw Resolution & Scoring

*Written at session end. Update before Phase 2 Session 2.*

---

## What Was Built

### Step 1 — Spelling fix: Mate → Matte

Every occurrence of `Mate` (the referee call) in source files and design documents was corrected to `Matte`. The Japanese is *matte* (待って), two t's. This was committed as its own clean diff before any logic changes.

Files changed: `src/match.py`, `design-notes/data-model.md`, `design-notes/dojo-as-institution.md`, `tachiwaza-master-doc.md`, `tachiwaza-orientation.md`.

The word `stalemate` was deliberately left unchanged — that's an English word, not the referee call.

---

### Step 2 — `effective_body_part()` (already existed)

This method was already implemented on the `Judoka` class in `judoka.py` from Phase 1. It combines the capability base value, the age modifier (currently a stub returning 1.0), the fatigue from State, and the injury multiplier into a single runtime float:

```
effective = base_capability × age_modifier × (1 - fatigue) × (0.3 if injured else 1.0)
```

Session 2 and the age modifier calibration pass will rely on this without needing to change the method itself.

---

### Step 3 — `resolve_throw()` in `match.py`

A module-level function (not a method on Match) that takes an attacker, a defender, a ThrowID, and a StanceMatchup, and returns one of: `IPPON`, `WAZA_ARI`, `STUFFED`, `FAILED`.

**Why it lives in `match.py` and not `throws.py`:** `throws.py` is reference data — what throws ARE. `resolve_throw()` is match logic — what happens when a throw is ATTEMPTED. It needs to know about fatigue, stance, body condition, and outcome thresholds. That's the Match layer's business, not the throw registry's.

---

### Steps 4 & 5 — Scoring, fatigue, and match-end conditions

`Match` now:
- Tracks `ne_waza_window`, `match_over`, `winner`, and `ticks_run` as internal state fields
- Calls `resolve_throw()` on random throw attempts each tick
- Applies throw-specific fatigue to the attacker's load-bearing body parts after each attempt
- Ends the match on IPPON or two WAZA_ARI; on time expiry, highest waza-ari wins; tied time = draw (golden score Phase 3)

---

## The Throw Resolution Formula — Plain English

Here is what the formula does, with no code:

**1. Effectiveness from current side**
The attacker has two effectiveness ratings for every throw: one from their dominant side, one from their off-side. A right-dominant fighter in orthodox stance attacks dominant. If they switch stance (Phase 3), they attack off-side instead and pay the penalty.

**2. Stance matchup modifier**
If the two fighters are in mirrored stances (one orthodox, one southpaw), the standard grip map is disrupted. Most throws lose about 15% effectiveness. Sumi-gaeshi gains 20% — it was built for the inside-foot hook that only mirrored stances create.

**3. Attacker body condition**
Grip throws (seoi-nage, tai-otoshi) draw on hands, forearms, core, and lower back. Leg throws (uchi-mata, o-soto, harai, etc.) draw on the dominant leg, core, and lower back. The average of the relevant body parts is fed through a modifier that scales between 50% (completely cooked) and 100% (fully fresh). A fatigued seoi specialist is weaker in exactly the right places.

**4. Defender resistance**
Both legs, core, and neck. Legs absorb kuzushi. Core holds the torso upright. Neck is the last line before a forward bend lets the throw entry through.

**5. Noise**
A Gaussian random term with standard deviation 2.0. Wide enough that identical setups diverge across attempts — which is realistic. A small weight shift, a half-second of hesitation, a floor grip from the wrong angle. The noise captures that.

**6. Outcome**
`net = attack_strength − defender_resistance + noise`

- net ≥ 4.0 → IPPON
- net ≥ 1.5 → WAZA_ARI
- net ≥ −2.0 → STUFFED (attacker committed and was stopped)
- net < −2.0 → FAILED (attacker never really committed)

---

## Where Session 2 Plugs In

### The `ne_waza_window` flag

Set to `True` on the `Match` object when a throw resolves as STUFFED. It lasts exactly one tick, then clears. Right now nothing reads it — it exists only as a seam.

Session 2 should:
1. Read the flag during the tick where it's set
2. Roll for whether either fighter commits to the ground
3. If commitment happens: transition both fighters to `Position.NE_WAZA`, resolve the ground exchange (pin, choke, armbar, scramble-to-stand), and apply the result to scoring

The flag being a one-tick boolean on `Match` (not on a fighter's State) reflects that the ground window is a *match-level event*, not something owned by either individual.

### Match-end hooks

`Match.match_over` and `Match.winner` are set inside `_apply_throw_result()`. Anything that needs to happen on match end — ceremonial ippon announcement, Matte call, referee positioning — should check `self.match_over` after `_apply_throw_result()` returns. The hook is already there.

### Composure changes

The score dict updates correctly (`state.score["waza_ari"]`, `state.score["ippon"]`) but composure doesn't change in response to scoring events yet. Getting scored on is a big composure hit in real judo. Session 2 should add:

```
# After a WAZA_ARI or IPPON is scored against a fighter:
defender.state.composure_current = max(0.0, defender.state.composure_current - composure_drop)
```

Where `composure_drop` scales with the event weight (IPPON is a bigger hit than WAZA_ARI).

---

## Tuning Knobs to Know About

All constants are at the top of `match.py` under `# TUNING CONSTANTS`. The ones that will most affect match feel:

| Constant | Current value | Effect |
|---|---|---|
| `ATTEMPT_PROB` | MOTOR=0.08, LEVER=0.06 | How often each archetype attacks. Raise to get more events per match; lower to slow the pace. |
| `NOISE_STD` | 2.0 | Spread of random variance per throw. Higher = more upsets; lower = more deterministic. |
| `IPPON_THRESHOLD` | 4.0 | How much better the attack needs to be than the defense for a clean ippon. |
| `WAZA_ARI_THRESHOLD` | 1.5 | Waza-ari cutoff. Raising this makes scoring rarer. |
| `STUFFED_THRESHOLD` | −2.0 | How committed the attacker has to be before a ne-waza window opens. |
| `THROW_FATIGUE` | FAILED=0.030 worst | How quickly repeated failed attempts cook the relevant body parts. |
| `SIGNATURE_PICK_RATE` | 0.65 | How often a fighter falls back on their signature throw vs mixing in others. |

The **age modifier** in `judoka.py` is still a stub returning 1.0. When real curves are implemented, a 26-year-old Tanaka will get a slight explosive power boost and a 24-year-old Sato will be near his cardio peak. Matches will shift.

---

## Open Questions Discovered During the Build

**1. Matches end very fast in some runs.**
Sato's uchi-mata is genuinely dangerous against Tanaka's defense values. Some runs end before tick 50. This may be correct — a MOTOR specialist with elite legs against a defender with lower leg scores *should* score quickly. But it's worth watching over many runs to see if the typical match length feels like 4 minutes of judo or 45 seconds.

**2. Tanaka's seoi-nage doesn't fire often.**
Because seoi-nage is a grip throw and the formula checks hands/forearms, it's slightly weaker than Sato's uchi-mata (which checks the dominant leg, and Sato's right_leg is 9). The design intent is that Tanaka's technique should be competitive, not clearly inferior. Session 2 calibration should verify this balance. Tanaka's high right_hand (9) should make his seoi more dangerous — and it does — but Sato's leg-based attacks may still have an edge.

**3. The stance matchup is always MATCHED.**
Both fighters start ORTHODOX and neither ever switches. The MIRRORED path (and Sato's sumi-gaeshi off-side bonus) is code that exists but never fires in Phase 2 matches. Phase 3's stance-switch instruction will finally activate that path.

**4. Composure is not wired into anything.**
`composure_current` starts at ceiling and never moves. The formula doesn't read it either (it only reads body part effective values). Before Session 2, decide: should composure be part of the throw resolution formula (as an attacker modifier or defender modifier), or should it only affect the Matte window instruction reception?

**5. The two throw attempts per tick can both fire.**
Both fighters can attempt a throw in the same tick if their random rolls both succeed. This is unrealistic — two simultaneous full-commitment throws don't happen — but for Phase 2 it's acceptable since the probability of both firing in the same tick is low (LEVER × MOTOR = 0.06 × 0.08 = 0.48% per tick). Session 2 may want to add a brief cooldown after any throw attempt.

---

*Document version: Phase 2 Session 1. Update before Session 2.*
