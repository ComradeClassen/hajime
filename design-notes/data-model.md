# Judoka Data Model — Design Note v0.3

*This is the spec for the `Judoka` class. Code is implemented from this document, not the other way around. If we want to change the class, we change this doc first, then the code.*

**Changes from v0.2:**
- **Five physical variables added to Identity layer** (height_cm stays; arm_reach_cm, hip_height_cm, weight_distribution, mass_density are new) — the biomechanical spine described in `biomechanics.md`
- **Cultural layer hooks added to Identity**: `nationality`, `training_lineage`, `style_dna`, `stance_matchup_comfort` — declared now so Ring 2-4 cultural systems can plug in without refactor. Ring 1 does not read these fields.
- **Grip sub-loop state fields added to State**: `grip_subloop_state`, `grip_delta`, `time_in_current_state`, `stifled_reset_count` — the mechanic implemented in Ring 1 Phase 2 Session 1
- **`sub_loop_config` declared** as a per-judoka tunable parameter block for calibration

---

## Design Philosophy

A `Judoka` holds three layers of information, kept structurally separate:

- **Identity** — who they are. Static or slow-changing across a career.
- **Capability** — what their body and mind can do *fresh*. Trained over months in the dojo. Persisted between matches.
- **State** — what's true *right now in this match*. Initialized fresh each match. Updated every tick.

This separation is what lets the same fighter have a great match one day and a terrible one the next: same Capability, different State trajectory.

For Ring 1 Phase 2, we build all three layers with real physical variables in play for throw resolution and the grip sub-loop. We still don't build the dojo system that *modifies* Capability — that's Ring 3.

---

## Layer 1 — IDENTITY

Static or near-static. Shapes how Capability and State express themselves.

### Core identity fields

| Attribute | Type | Range / Example | Notes |
|---|---|---|---|
| `name` | str | "Tanaka" | Display name. |
| `age` | int | 16–40 | Drives the age modifier system. |
| `weight_class` | str | "-90kg" | For Ring 1, hardcoded to -90kg. |
| `belt_rank` | enum | WHITE / YELLOW / ORANGE / GREEN / BLUE / BROWN / BLACK_1 ... BLACK_5 | Determines throw vocabulary size and composure resistance to referee calls. |
| `body_archetype` | enum | LEVER / MOTOR / GRIP_FIGHTER / GROUND_SPECIALIST / EXPLOSIVE | See v0.2 definitions. |
| `dominant_side` | enum | RIGHT / LEFT | Drives dominant-side grip system. |
| `personality_facets` | dict | see v0.2 | Shapes close-call decisions and instruction reception. |

### The five physical variables (NEW in v0.3)

These are the biomechanical spine. They live in Identity because they are who the body IS, not what it can do. Age modifies some of them over a career, but the baselines are set at recruitment.

| Attribute | Type | Range / Units | Role |
|---|---|---|---|
| `height_cm` | int | 155–200 | Moment arm advantage on hip throws. Reach baseline. |
| `arm_reach_cm` | int | 160–210 | Grip control radius. Who grips first at engagement. Derived roughly as height × 1.03 by default, but stored independently so outliers (long-armed compact fighters, short-armed tall fighters) can exist. |
| `hip_height_cm` | int | 90–115 | Kuzushi geometry. The seoi-nage entry cost changes dramatically with hip height differential. Derived roughly from height, but stored independently. |
| `weight_distribution` | enum | FRONT_LOADED / NEUTRAL / BACK_LOADED | Frame orientation. Biases which throw directions are exploitable. Can shift during a match under fatigue. |
| `mass_density` | enum | LIGHT / AVERAGE / DENSE | Two fighters at the same weight class can have very different mass distribution. Dense = harder to move, more inertia, slower change of direction. Light = easier to redirect, less power behind own throws. |

These variables feed directly into the throw resolution formula and the grip sub-loop, as specified in `biomechanics.md`.

### Cultural layer hooks (NEW in v0.3, not read by Ring 1)

Declared so Ring 2-4 systems have somewhere to plug in. Ring 1 Phase 2 does not read these fields.

| Attribute | Type | Example | Role (Ring 2+) |
|---|---|---|---|
| `nationality` | str | "Japanese", "Brazilian", "American" | Biases starting style_dna at generation; affects recruit demographics. |
| `training_lineage` | list[str] | ["sensei_yamamoto_id", "instituto_reacao"] | Ordered list of sensei / schools who have trained this judoka. Used by voice compatibility in Ring 2. |
| `style_dna` | dict[StyleID, float] | {"CLASSICAL_KODOKAN": 0.6, "BRAZILIAN_BJJ": 0.4} | Weighted mixture of style influences. Sums to 1.0. See `cultural-layer.md`. |
| `stance_matchup_comfort` | dict[StanceMatchup, float] | {MATCHED: 1.0, MIRRORED: 0.7, OFF_SIDE: 0.3} | How well the fighter performs in each stance matchup. A rigid right-hander has high MATCHED, low MIRRORED. A left-hander who has trained to exploit mirrored has high MIRRORED, mid MATCHED. |

### Personality Facets (unchanged from v0.2)

Each on a 0–10 scale. Seed values; in later rings they shift over a career.

```
aggressive    ↔ patient
technical     ↔ athletic
confident     ↔ anxious
loyal_to_plan ↔ improvisational
```

Ring 1 uses these to bias close-call decisions (an aggressive fighter is more likely to commit to a kuzushi window; an anxious fighter loses composure faster after a stuffed throw).

---

## Layer 2 — CAPABILITY

What the body and mind can do *fresh*. Each value represents the maximum the fighter can perform when uninjured and unfatigued. Age modifiers (v0.2) further adjust these at runtime.

### Body Capability — 15 parts (unchanged from v0.2)

```
HANDS:        right_hand,        left_hand          (grip security, finger strength)
FOREARMS:     right_forearm,     left_forearm       (grip endurance, gripping pulls)
BICEPS:       right_bicep,       left_bicep         (pulling strength, frame breaking)
SHOULDERS:    right_shoulder,    left_shoulder      (throw entry, posture)
LEGS:         right_leg,         left_leg           (throw power, defense base)
FEET:         right_foot,        left_foot          (footwork, sweeping precision)
CORE:         core                                  (rotational power, posture stability)
LOWER_BACK:   lower_back                            (throw lift, posture defense)
NECK:         neck                                  (posture defense vs. forward bend)
```

Each on a **0–10 scale**.

**Note on Phase 2 Session 1 scope:** the grip sub-loop heavily engages `right_hand`, `left_hand`, `right_forearm`, `left_forearm`. Throw resolution additionally engages `right_leg`, `left_leg`, `core`, `lower_back`. The other 9 parts are declared, accumulate some fatigue, but are not yet mechanically consequential. They earn their way in during later phases.

### Cardio — global (unchanged)

```
cardio_capacity   (0–10)   — total endurance pool
cardio_efficiency (0–10)   — how slowly cardio drains under load
```

Cardio is global because it's lung/heart, not localized. It modifies the recovery rate of every body part.

### Mind Capability (unchanged)

```
composure_ceiling  (0–10)  — maximum composure when calm
fight_iq           (0–10)  — read speed, combo recognition, opening detection
ne_waza_skill      (0–10)  — separate from standing technique
```

Composure is a *ceiling* in Capability and a *current value* in State.

---

## Age as a Multi-Vector Modifier (unchanged from v0.2)

See v0.2 for the full age curve specification. Summary:

- Fight IQ peaks 30–35+, climbs with experience
- Grip strength (hands, forearms) peaks 28–35 — "old man strength" holds late
- Core, lower_back, neck peak 28–35
- Explosive power peaks 24–28, declines after 30
- Cardio capacity peaks 26–30
- Recovery rate declines steadily from late 20s
- Composure ceiling drifts upward with experience

For Phase 2 Session 1 we continue to use a stub `age_curve_lookup()` that returns 1.0 for everything. Real curves come in calibration.

---

## Dominant-Side Grip System (unchanged from v0.2)

Per-side grip strength already exists in the body model. Per-throw side modifiers and stance matchup already specified in v0.2. The grip sub-loop (Phase 2 Session 1) reads these directly.

### New in v0.3: `stance_matchup_comfort`

The v0.2 dominant-side system described *mechanical* asymmetry (right_hand=9, left_hand=3). The new `stance_matchup_comfort` field captures *psychological* asymmetry: how the fighter performs in MATCHED, MIRRORED, and OFF_SIDE stances regardless of their physical capability.

Three character archetypes fall out of the combination:

- **The ambidextrous orthodox** — symmetric physical stats + high MATCHED + high MIRRORED. Rare.
- **The rigid specialist** — asymmetric physical stats + high MATCHED + low MIRRORED. Freaks out when stance flips. Most ippon-hunters.
- **The mirrored-stance predator** — left-handed with high MIRRORED + moderate MATCHED. Trained to exploit kenka-yotsu against right-handers. Freaks out in lefty-vs-lefty matches.

`stance_matchup_comfort` multiplies into throw effectiveness and into the grip sub-loop's TUG_OF_WAR calculation when stance matchup is non-optimal for the fighter.

---

## Layer 2 (continued) — Repertoire: Throws & Combos (unchanged from v0.2)

```python
throw_vocabulary: list[ThrowID]
throw_profiles: dict[ThrowID, JudokaThrowProfile]
signature_throws: list[ThrowID]
signature_combos: list[ComboID]
```

Belt-rank vocabulary sizes unchanged. In Ring 2+, high `style_dna` weights add style-specific throws above the belt-rank baseline (e.g., Georgian weighting >0.2 unlocks chance of Khabareli).

---

## Layer 3 — STATE

Initialized at match start from Capability. Updated every tick. Fully resets at the next match start (with the tournament-carryover exception).

### Body State (unchanged from v0.2)

For each of the 15 body parts:

```
fatigue:    float (0.0 – 1.0)
injured:    bool
```

Effective strength formula:

```
effective = capability_age_modified × (1 - fatigue) × (0.3 if injured else 1.0)
```

### Cardio State (unchanged)

```
cardio_current   (float, 0.0 – 1.0)
```

### Mind State (unchanged)

```
composure_current              float (0.0 – composure_ceiling)
last_event_emotional_weight    float (spike; decays)
```

### Match State (with new Phase 2 Session 1 additions)

```python
position             enum   STANDING_DISTANT / GRIPPING / ENGAGED / SCRAMBLE / NE_WAZA / DOWN
posture              enum   UPRIGHT / SLIGHTLY_BENT / BROKEN
current_stance       enum   ORTHODOX / SOUTHPAW
grip_configuration   dict
score                dict   # waza-ari count, ippon flag
shidos               int
recent_events        list
current_instruction  str
instruction_received_strength  float (0.0 – 1.0)

# NEW IN v0.3 — Grip Sub-Loop state fields
grip_subloop_state            enum   ENGAGEMENT / TUG_OF_WAR / KUZUSHI_WINDOW / STIFLED_RESET / THROW_ATTEMPT / IDLE
grip_delta                    float  # current tug-of-war delta (positive = tori winning)
time_in_current_state         int    # ticks since entering current sub-loop state
stifled_reset_count           int    # total stifled resets this match; drives late-match prose density
time_since_last_engagement    int    # ticks since last sub-loop ENGAGEMENT began
current_sub_loop_config       SubLoopConfig  # per-match tunable parameters
```

### SubLoopConfig (NEW in v0.3)

Per-match tunable parameters for the grip sub-loop. Initialized from a judoka-level default but can be adjusted per-match or globally during calibration. See `grip-sub-loop.md` for full descriptions.

```python
kuzushi_threshold            float  # grip_delta required to open window. Default: 2.5
kuzushi_window_duration      int    # ticks window stays open. Default: 2
stalemate_threshold          float  # grip_delta band considered stalemate. Default: 0.8
stalemate_duration           int    # ticks of stalemate before reset. Default: 15
reset_recovery_ticks         int    # breath time before re-engagement. Default: 3
engagement_duration          int    # ticks to establish grips. Default: 2
forearm_fatigue_rate         float  # per-tick cost of TUG_OF_WAR. Default: 0.004
force_attempt_penalty        float  # success multiplier with no window open. Default: 0.15
```

### Relationship with Sensei (Ring 2+ hook, unchanged from v0.2)

Declared now, unused in Ring 1.

```
relationship_with_sensei: dict
    chair_time_received        int
    chair_time_denied          int
    perceived_priority         float
    loyalty                    float (0.0 – 10.0)
```

### Tournament Carryover (Ring 2 prep, unchanged from v0.2)

Declared now, unused in Ring 1.

```
matches_today                     int
cumulative_fatigue_debt           dict[body_part, float]
emotional_state_from_last_match   enum   ELATED / RELIEVED / DRAINED / SHAKEN / FOCUSED
```

---

## What Ring 1 Phase 2 Session 1 Builds

This session implements the first real match logic on top of the Phase 1 skeleton.

✅ Fix `Mate` → `Matte` everywhere (clean first commit)

✅ `effective_body_part()` method on Judoka using the v0.2 formula

✅ Five physical variables added to Identity layer with baseline values for Tanaka and Sato

✅ Throw resolution: IPPON / WAZA_ARI / STUFFED / FAILED using:
  - Per-throw side effectiveness from JudokaThrowProfile
  - Stance matchup modifier
  - Attacker body part effective values (legs, core, lower_back)
  - Defender body part effective values (posture cluster)
  - **NEW**: height differential as moment arm modifier — the first physics variable to become observable

✅ Scoring wired to match state; match end on IPPON, two WAZA_ARI, or time expiration

✅ **Grip Sub-Loop** state machine with five states (ENGAGEMENT, TUG_OF_WAR, KUZUSHI_WINDOW, STIFLED_RESET, THROW_ATTEMPT)
  - Per-tick grip_delta calculation using hand/forearm effective values
  - Three resolution paths (window → throw, stalemate → reset, forced → throw attempt)
  - Forearm fatigue accumulation tied to time-in-tug-of-war
  - stifled_reset_count in State

✅ Log output that stays quiet on silent sub-loop activity, marks threshold crossings

## What Ring 1 Phase 2 Session 2 Builds

Next session, architecturally adjacent but scoped separately:

- Referee class in `src/referee.py` with `newaza_patience`, `stuffed_throw_tolerance`, `match_energy_read`, and `grip_initiative_strictness` (new from research doc)
- Referee-driven Matte detection (reads match state, decides when to intervene)
- Hajime ceremonial call at match start, proper Ippon as final call
- Belt rank gating on composure hits from ref calls (GREEN and below feel it; BROWN and above don't)
- Shido tracking for forced attempts under stress (the ref notices)

## What Ring 1 Phase 2 Does NOT Build

- Coach instruction UI (Ring 2 / Phase 3)
- Full prose templating (Phase 4+)
- Ne-waza window resolution (flagged this session, playable later)
- Any cultural layer fields being *read* — they are declared in Identity but dormant

---

## Open Calibration Questions (for later)

These don't block Phase 2. They become real once we can watch matches:

- How fast does grip fatigue accumulate? (default 0.004/tick)
- How big should `kuzushi_threshold` be? (default 2.5)
- How often does stifled_reset happen at the current stalemate_duration?
- How much does composure actually swing per event?
- What's the right base rate for throw attempts per minute?
- How often should Matte be called?
- How big is the ne-waza window after a stuffed throw?
- What are the exact age curve shapes for each attribute cluster?
- What's the right efficiency penalty for a stance switch?
- At what style_dna weighting does a style-specific throw become accessible? (default 0.2)
- What is the biomechanical cost of stance switching as a function of dominant-side asymmetry?

---

*Document version: April 14, 2026 (v0.3). Update before changing the class.*
