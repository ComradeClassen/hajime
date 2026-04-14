# Judoka Data Model — Design Note v0.2

*This is the spec for the `Judoka` class. Code is implemented from this document, not the other way around. If we want to change the class, we change this doc first, then the code.*

**Changes from v0.1:**
- Age expanded into a multi-vector modifier system (Q1 follow-up)
- All five body archetypes now defined (Q2 follow-up)
- Dominant-side grip system significantly amplified (Q3 follow-up)

---

## Design Philosophy

A `Judoka` holds three layers of information, kept structurally separate:

- **Identity** — who they are. Static or slow-changing across a career.
- **Capability** — what their body and mind can do *fresh*. Trained over months in the dojo. Persisted between matches.
- **State** — what's true *right now in this match*. Initialized fresh each match. Updated every tick.

This separation is what lets the same fighter have a great match one day and a terrible one the next: same Capability, different State trajectory.

For Ring 1, we build all three layers. We don't build the dojo system that *modifies* Capability — we just hand-build two judoka with reasonable values and let them fight.

---

## Layer 1 — IDENTITY

Static or near-static. Shapes how Capability and State express themselves.

| Attribute | Type | Range / Example | Notes |
|---|---|---|---|
| `name` | str | "Tanaka" | Display name. |
| `age` | int | 16–40 | Drives the age modifier system below. |
| `weight_class` | str | "-90kg" | For Ring 1, hardcoded to -90kg. |
| `height_cm` | int | 165–195 | Affects throw success biases. |
| `body_archetype` | enum | LEVER / MOTOR / GRIP_FIGHTER / GROUND_SPECIALIST / EXPLOSIVE | See definitions below. |
| `belt_rank` | enum | WHITE / YELLOW / ORANGE / GREEN / BLUE / BROWN / BLACK_1 ... BLACK_5 | Determines throw vocabulary size. |
| `dominant_side` | enum | RIGHT / LEFT | Drives the dominant-side grip system below. |
| `personality_facets` | dict | see below | Shapes behavior under stress and instruction reception. |

### Body Archetypes — Definitions

These are starting categories. Real judoka often blend two; we treat the archetype as a primary tendency that biases certain mechanics.

- **LEVER** — uses height, length, and leverage. Throws like uchi-mata, harai-goshi, sasae-tsurikomi-ashi work well. Often taller, longer-limbed. Wins by extending the opponent and lifting them off-balance. Weakness: shorter, denser opponents who can get under their center.

- **MOTOR** — high-output. Attacks constantly. Wears opponents down with relentless pressure. Wins by Round 2 fatigue management. Cardio is the weapon. Weakness: fragile if their first wave doesn't land.

- **GRIP_FIGHTER** — wins the grip war first, dictates the exchange, then attacks from a position of control. May not have flashy throws but always has *their* grip. Weakness: opponents who refuse the grip game and force scrambles.

- **GROUND_SPECIALIST** — average to good standing, dangerous on the mat. Looks for any ne-waza window and finishes there. Often a BJJ or sambo crossover. Weakness: opponents with great standing defense who never give the ground.

- **EXPLOSIVE** — one-shot ippon hunter. Patient grip work for 90 seconds, then a single full-commitment throw. High variance — wins big or loses big. Weakness: long matches where the throw window doesn't open.

*(Future expansion: COUNTER_PUNCHER, SUTEMI_SPECIALIST, DEFENSIVE_TACTICIAN. Add when needed.)*

### Personality Facets

Each on a 0–10 scale. Seed values; in later rings they shift over a career.

```
aggressive    ↔ patient
technical     ↔ athletic
confident     ↔ anxious
loyal_to_plan ↔ improvisational
```

Ring 1 uses these to bias close-call decisions (an aggressive fighter is more likely to commit to a ne-waza window; an anxious fighter loses composure faster after a stuffed throw).

---

## Layer 2 — CAPABILITY

What the body and mind can do *fresh*. Each value represents the maximum the fighter can perform when uninjured and unfatigued. Age modifiers (below) further adjust these at runtime.

### Body Capability — 15 parts

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

Each on a **0–10 scale**. A 10 is world-class for that part; a 5 is solid club-level; a 2 is a weak point an opponent can exploit.

**Calibration honesty:** 15 parts is a lot. In Phase 1 of Ring 1, only ~6 of these will *meaningfully* participate in the simulation (hands, forearms, legs, core, lower_back, neck). The other 9 are present in the data model but read as quiet. We add their behavior incrementally as we identify what they should *do*.

### Cardio — global

```
cardio_capacity   (0–10)   — total endurance pool
cardio_efficiency (0–10)   — how slowly cardio drains under load
```

Cardio is global because it's lung/heart, not localized. It modifies the recovery rate of every body part.

### Mind Capability

```
composure_ceiling  (0–10)  — maximum composure when calm
fight_iq           (0–10)  — read speed, combo recognition, opening detection
ne_waza_skill      (0–10)  — separate from standing technique
```

Composure is a *ceiling* in Capability and a *current value* in State.

---

## Age as a Multi-Vector Modifier

Age is not a single curve. Different capabilities peak at different ages. Effective Capability at runtime is computed as `base_capability × age_modifier(attribute, age)`.

### The curves

| Attribute cluster | Peak age | Decline behavior |
|---|---|---|
| Fight IQ | 30–35+ | Climbs steadily with match experience; declines slowly if at all. A 38-year-old with 20 years of competition reads situations a 22-year-old cannot. |
| Grip strength (hands, forearms) | 28–35 | "Old man strength." Holds high into late 30s, especially in trained athletes. Declines slowly in 40s. |
| Core, lower_back, neck | 28–35 | Same as grip — trained, deep-tissue strength holds late. |
| Explosive power (legs, shoulders for committed throws) | 24–28 | Peaks early, declines noticeably after 30. The big burst for sutemi or full-commit uchi-mata fades first. |
| Cardio capacity | 26–30 | Peaks late 20s, declines slowly. |
| Recovery rate | 25 and earlier | Declines steadily from late 20s. **This is where age actually hurts in a tournament** — the veteran might win the first match, but recover from it more slowly than the prospect. |
| Composure ceiling | climbs slowly with experience | A veteran who has lost in the finals before is calmer there the next time. Slight drift upward. |

### How this is implemented

```python
def effective_capability(attribute_name, base_value, age):
    modifier = age_curve_lookup(attribute_name, age)
    return base_value * modifier
```

A 38-year-old veteran might have *higher* effective fight IQ and grip strength than his trained baseline (modifiers > 1.0), but lower explosive power and noticeably slower recovery (modifiers < 1.0). That's a fundamentally different fighter than a 22-year-old with the same baseline numbers.

For Phase 1 we implement the modifier function as a stub (returns 1.0 for everything). Real curves get tuned in calibration.

---

## Dominant-Side Grip System

Real judo is asymmetric. The data model treats this as a first-class concept, not an afterthought.

### Per-side grip strength

Already in the body model — `right_hand`, `left_hand`, `right_forearm`, `left_forearm`, etc. all carry independent Capability values. A right-handed seoi specialist might have right_hand = 9 and left_hand = 6. That asymmetry is intentional and meaningful.

### Per-throw side modifiers

Every throw in a judoka's vocabulary stores two effectiveness ratings — one from the dominant side, one from the off-side. They can differ dramatically.

```python
class JudokaThrowProfile:
    throw_id: ThrowID
    effectiveness_dominant: int    # 0-10
    effectiveness_off_side: int    # 0-10
```

A right-handed seoi specialist might be a 9 from the right side and a 3 from the left. A truly two-sided fighter might be 8/7 — rare and dangerous.

### Stance matchup

The match engine knows whether the two judoka are in matched stances (both orthodox, or both southpaw) or mirrored stances (one of each).

```
stance_matchup: enum  MATCHED / MIRRORED
```

Matched stance produces the standard sleeve-and-collar grip war. Mirrored stance produces a different grip game with different dominant configurations and different available throws (and much higher rates of certain throws — sumi-gaeshi is a mirrored-stance favorite).

Throw effectiveness is further modified by stance matchup. A throw might have a hidden third value: `effectiveness_mirrored`, used when fighting a southpaw.

### Switching stance as a tactical move

The instruction "Switch stance — attack the other side" already exists in the taxonomy. With this system it has real teeth:

- The judoka can switch their dominant side mid-match
- Switching costs efficiency (-15% to all effectiveness ratings on the new side, applied multiplicatively)
- But it can disrupt an opponent who has settled into reading your right-side attacks
- A fighter with high `improvisational` facet handles a switch better; a `loyal_to_plan` fighter loses more efficiency

### Preferred grip configurations

*(Optional for Phase 1 — note for later.)* Beyond just dominant side, individual judoka have preferred *configurations*. Sleeve-and-collar standard. Sleeve-and-back. Over-the-top. Russian tie. This could live in the Identity layer as a `preferred_grip_configurations` list. We'll add this once the basic grip system is observable.

---

## Layer 2 (continued) — Repertoire: Throws & Combos

```python
throw_vocabulary: list[ThrowID]      # Throws this judoka knows at all
throw_profiles: dict[ThrowID, JudokaThrowProfile]   # per-throw side modifiers
signature_throws: list[ThrowID]      # 2–4 throws they specialize in
signature_combos: list[ComboID]      # Sequences they've drilled
```

**Throw vocabulary size by belt rank:**

| Belt | Vocabulary size |
|---|---|
| White / Yellow | 3–5 |
| Orange / Green | 6–10 |
| Blue / Brown | 10–15 |
| Black 1–2 | 15–22 |
| Black 3+ | 22–30 |

A throw they don't know, they can't attempt.

**Combos** are stored as ordered sequences: `[ko_uchi_gari → seoi_nage]`. When a judoka attempts the first move, there's a small chance to chain into the second if conditions allow. Signature combos chain at higher rates.

For Phase 1, we hand-build:
- A `Throw` registry with 8 throws (seoi-nage, uchi-mata, o-soto-gari, o-uchi-gari, ko-uchi-gari, harai-goshi, tai-otoshi, sumi-gaeshi)
- A `Combo` registry with 3 combos
- Two judoka with chosen vocabularies and signatures

---

## Layer 3 — STATE

Initialized at match start from Capability. Updated every tick. Fully resets at the next match start (with one exception — see Tournament Carryover below).

### Body State

For each of the 15 body parts:

```
fatigue:    float (0.0 – 1.0)   # 0.0 = fresh, 1.0 = completely cooked
injured:    bool                # set true if a serious event hits this part
```

Effective strength of a part at any moment:
```
effective = capability_age_modified × (1 - fatigue) × (0.3 if injured else 1.0)
```

Fatigue accumulates based on what the part is *doing*. Recovery happens slowly during action and faster during Matte. Cardio modifies recovery rate. Age modifies recovery rate even more (older judoka recover slower).

### Cardio State

```
cardio_current   (float, 0.0 – 1.0)   # depleted by sustained action
```

### Mind State

```
composure_current   (float, 0.0 – composure_ceiling)
last_event_emotional_weight   (float)   # spike from significant events; decays over ticks
```

### Match State

```
position             enum   STANDING_DISTANT / GRIPPING / ENGAGED / SCRAMBLE / NE_WAZA / DOWN
posture              enum   UPRIGHT / SLIGHTLY_BENT / BROKEN
current_stance       enum   ORTHODOX / SOUTHPAW   # can change mid-match via instruction
grip_configuration   dict   # which hand has what grip on which part of the opponent's gi
score                dict   # waza-ari count, ippon flag
shidos               int    # penalty count
recent_events        list   # last N tick events, used for short-term decision context
current_instruction  str    # most recent coach instruction; biases next decisions
instruction_received_strength  float (0.0 – 1.0)   # how cleanly it's being executed
```

### Relationship with Sensei (Ring 2+ hook)

Declared now, unused in Ring 1. Listed here so the field exists in the data model from day one.

```
relationship_with_sensei: dict
    chair_time_received        int
    chair_time_denied          int
    perceived_priority         float
    loyalty                    float (0.0 – 10.0)
```

### Tournament Carryover (Ring 2 prep)

Q7 introduces an architectural requirement: **some State must persist across matches in the same tournament day.**

```
matches_today                     int
cumulative_fatigue_debt           dict[body_part, float]   # incomplete recovery between matches
emotional_state_from_last_match   enum   ELATED / RELIEVED / DRAINED / SHAKEN / FOCUSED
```

After each match, fatigue partially recovers but not fully. Composure ceiling is temporarily modified by the emotional state. An anxious fighter who just won a tough quarterfinal might enter the semi-final with elevated composure; a confident fighter who won easily might be reckless.

**For Ring 1, we do not implement this.** But we structure the State class so that "initialize from Capability" and "initialize from previous match's residual state" are two separate code paths.

---

## What Ring 1 Phase 1 Actually Builds

To be concrete about the scope of the first Claude Code session:

✅ All three layers as Python classes (`Identity`, `Capability`, `State`, composed into `Judoka`)
✅ The 15-body-part structure declared
✅ Throw and Combo registries with ~8 throws and ~3 combos hand-defined
✅ `JudokaThrowProfile` with dominant/off-side effectiveness ratings
✅ Age modifier function declared as a stub (returns 1.0)
✅ Two hand-built judoka in `main.py`: a Tanaka (LEVER, seoi-nage specialist, age 26) and a Sato (MOTOR, uchi-mata specialist, age 24)
✅ A `Match` class with a tick loop that runs for 240 ticks (one match-second per tick, 4-minute match)
✅ The tick loop *does not yet have real combat logic.* It just prints `"tick N: [placeholder event]"` and updates fatigue on a couple of body parts.
✅ Match ends with a placeholder winner.

That's it. No Matte window yet. No prose templates. No real grip state graph. We're proving the architecture is sound and the classes compose properly.

**Phase 1 success criterion:** you can run `python src/main.py`, see 240 lines of output, and the two judoka objects look correct when inspected at the end (fatigue accumulated reasonably, capabilities unchanged, state populated, archetypes and dominant sides reflected in the data).

---

## What Comes After Phase 1

- **Phase 2:** Real grip state graph. Throw attempts with proper success rolls (using archetype, dominant side, age-modified capability, fatigue). Matte detection. Scoring.
- **Phase 3:** Matte window. Stat panel. Instructions. Reception calculation. Resume.
- **Phase 4:** Prose template system. Events get wrapped in real sentences using the tone guide.
- **Phase 5:** Calibration pass. Watch many simulated matches. Tune curves.

---

## Open Calibration Questions (for later)

These don't block Phase 1. They become real once we can watch matches:

- How fast does grip fatigue accumulate?
- How much does composure actually swing per event?
- What's the right base rate for throw attempts per minute?
- How often should Matte be called?
- How big is the ne-waza window after a stuffed throw?
- What are the exact age curve shapes for each attribute cluster?
- What's the right efficiency penalty for a stance switch?

---

*Document version: April 13, 2026 (v0.2). Update before changing the class.*
