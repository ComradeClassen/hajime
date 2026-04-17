# The Cultural Layer — Design Note v0.1
### National Styles, Inherited DNA, and Emergent Dojo Identity

*This document specifies the cultural and lineage layer of Hajime. It is
scoped to Ring 2, Ring 3, and Ring 4 — the coaching, training, and roster
systems. It is NOT part of Ring 1. The Grip Sub-Loop, throw resolution,
and match engine operate without any cultural data at all. This layer
becomes observable once multiple judoka from different backgrounds meet,
and becomes mechanically important once the dojo persists across
generations.*

---

## Why This Exists

The research document *The Chair, the Grip, and the Throw* establishes
that thirteen distinct national fighting styles exist in elite judo, each
shaped by a specific folk-wrestling ancestor (chidaoba, bökh, sambo,
kurash, BJJ, the classical Kodokan curriculum). These are not flavor.
They are mechanically observable differences in how fighters grip, which
throws they know, how they react under stress, and what their coaches
sound like in the chair.

A game that treats judoka as interchangeable stat blocks misses what
makes elite judo watchable. A game that tries to fully simulate thirteen
styles from day one will ship nothing. The Cultural Layer is the
discipline that holds both truths at once: the styles matter, and they
earn their way into the simulation ring by ring.

Equally important: **Hajime's dojo persists across generations**, and
one of the deepest game design spaces in the project is watching a
dojo's cultural identity drift over decades as different sensei inherit
the wall. This layer is where that drift becomes computable.

---

## The Thirteen Seeds

The research document enumerates these national styles. For the game,
they function as **seed presets** — starting blends of grip preferences,
throw vocabularies, tactical dispositions, and folk-wrestling
ancestries. No fighter is ever *only* one of these. Every fighter
carries a weighted mixture.

| Style | Folk Ancestor | Signature Grips | Signature Throws |
|---|---|---|---|
| Classical Kodokan (Japan) | — | Hikite / Tsurite (sleeve + lapel) | Uchi-mata, seoi-nage, osoto-gari |
| Georgian | Chidaoba | Over-shoulder, belt grip | Khabareli, sumi-gaeshi, ura-nage |
| French (INSEP) | — | High-gripping, tactical | Uchi-mata, harai-goshi variants |
| Russian / Soviet | Sambo | Russian tie, adaptable | Wrestling-influenced, post-ban adapted |
| Korean | — | Single-sleeve, incomplete grips | Drop seoi-nage, speed attacks |
| Mongolian | Bökh | Over-under, belt, underhooks | Standing-only, wrestling slams |
| Brazilian | BJJ crossover | Classical + ne-waza readiness | Standing Kodokan + ground predator |
| Cuban | — | Man's grip (strength-forward) | Combination-heavy, explosive |
| Dutch | Geesink lineage | Classical, heavyweight-coded | Technical giants, strong osaekomi |
| British | — | Transition-focused | Juji-gatame specialists |
| German | — | Classical, systematic | Drop seoi, sumi-gaeshi |
| Uzbek / Central Asian | Kurash + sambo | Standing pressure, constant attack | Versatile across throw families |
| Ryukyuan / Okinawan | — | Rare, ancestral Jujutsu-coded | [Placeholder for emergent variants] |

The thirteenth slot is deliberately a placeholder for an emergent or
researched style the designer wants to add later. The canon is not
sacred; it is a starting vocabulary.

---

## Style DNA — The Core Data Structure

Every judoka carries a **`style_dna`** field: a weighted dictionary of
style influences.

```python
style_dna: dict[StyleID, float]
# example:
# { "CLASSICAL_KODOKAN": 0.50,
#   "BRAZILIAN_BJJ": 0.30,
#   "GEORGIAN": 0.15,
#   "KOREAN": 0.05 }
# Weights always sum to 1.0
```

A pure seed fighter — a judoka recruited fresh from a national program
with no other influences — has a single style at 1.0. Most fighters, and
nearly all judoka who have trained under multiple sensei, carry a
weighted mix.

### What style_dna influences

The weights bias several systems across Ring 2-4:

**Grip preference** — which grip configurations the fighter instinctively
seeks at engagement. A 0.15 Georgian weighting gives a fighter a small
bias toward over-the-shoulder grips; a 0.6 Georgian weighting makes it
their default.

**Throw vocabulary additions** — above the throws granted by belt rank,
style_dna weights add access to style-specific throws. A fighter with
any Georgian weighting above 0.2 has a chance to know Khabareli above
their belt's normal vocabulary. A fighter with any BJJ weighting above
0.15 has elevated ne-waza skill regardless of belt rank.

**Tactical disposition bias** — score_manager vs ippon_hunter vs
pressure_fighter vs counter_fighter. Japanese weights skew toward ippon;
French weights skew toward score management; Georgian weights skew
toward pressure; Korean weights skew toward speed-counter.

**Instruction reception** — see "Coach Voice Compatibility" below.

**Training receptivity** — in the dojo, a fighter picks up style-matched
techniques faster. Teaching Khabareli to a 0.6 Georgian fighter goes
quickly. Teaching Khabareli to a 1.0 Classical Kodokan fighter is a
long project.

### Style DNA is NOT body type

This is the critical distinction. `style_dna` is cultural-technical
training. The five biomechanical variables in `biomechanics.md` are
physical. A Georgian fighter with BJJ influences in their style_dna is
not a different *body* from a Japanese fighter — they just grip
differently, know different throws, and have different tactical
defaults. The body is biomechanics. The training is style_dna. Both
feed throw resolution independently.

---

## Inheritance Rules — How Styles Pass Down

### Student from sensei
When a judoka is trained under a sensei for a sustained period, a
fraction of the sensei's style_dna is added to theirs (then re-
normalized to sum to 1.0). Default fraction: 0.15 for a full career
under one sensei, scaled by time trained. Shorter training periods pass
smaller fractions. A fighter who trained under three sensei will carry
traces of all three.

### Sensei becomes dojo
When a judoka retires and inherits the dojo as its new sensei, their
personal `style_dna` becomes part of the **Dojo's institutional
style_dna** — a separate field tracked on the Dojo object. Over
generations, the dojo's style_dna converges toward whatever has been
reinforced by successive sensei, with each generation contributing
~25% of the dojo's new blend (older history fading but not disappearing).

### Kids' class as pipeline
See `dojo-as-institution.md`. Kids trained in a dojo inherit a small
fraction of the dojo's current style_dna (default 0.10), giving a
subtle generational style identity to anyone who came up through the
pipeline.

### The emergent result
After three or four sensei generations, a dojo may have a blended
style_dna that doesn't match any of the thirteen seeds — for example, a
weird Georgian-BJJ-Japanese hybrid with traces of Dutch from a visiting
seminar fifteen years ago. This is the point. The game is a
multigenerational style generator.

---

## Events That Add Style DNA

Beyond the slow drip of training and inheritance, **events** add
style_dna directly:

### Seminars
A visiting champion runs a seminar at your dojo. Duration: typically
one week of in-game time. Anyone attending receives a small addition
of the visitor's style_dna — default 0.03 to 0.08 per attendee,
depending on seminar length and attendee attentiveness (composure and
trust factor in). The dojo's institutional style_dna also gains a tiny
trace (0.01).

The research doc's example of an American dojo where a Japanese specialist
runs a one-week seminar becomes real here: three attendees each get a
0.05 Classical Kodokan bump, and the dojo itself remembers that week
forever.

### Cross-training stints
A judoka who spends a training period at another dojo (exchange,
vacation, injury rehab elsewhere) picks up a portion of that dojo's
style_dna — typically 0.05 to 0.12 depending on length.

### Competition exposure
Fighting — not just training — under specific stylistic traditions
applies a trickle-feed effect. A judoka who competes on the French
circuit for a season picks up a small French weighting (default 0.02
per season). This is subtle but accumulates over a long career.

### Defeat as teacher
A judoka thrown cleanly by a Georgian-style Khabareli they have never
seen before, in a high-stakes match, gains a tiny Georgian style_dna
bump (default 0.01-0.03) regardless of whether they train it
afterward. The body remembers what beat it. This is a small effect but
a real one — and it creates interesting emergent behavior where a
fighter who has been beaten by a variety of stylists becomes more
stylistically diverse over their career.

---

## School Demographics — Who Shows Up

When your dojo exists in a specific place, the recruit pool is biased
by that place. The starting demographics of your first roster are not
random — they reflect the real-world likelihoods of the city you're in.

### Default demographic tables

**American mid-size city (default starting option):**
- 70% Classical Kodokan (1.0)
- 15% Classical Kodokan (0.6) + Brazilian BJJ (0.4)
- 10% Classical Kodokan (0.7) + Asian heritage influences (0.3)
- 3% outlier: Russian / Georgian / French heritage family
- 2% rare: someone who trained abroad before moving

**American coastal city:**
- 50% Classical Kodokan (1.0)
- 25% Classical + BJJ blends (higher BJJ weighting than mid-size)
- 15% Japanese heritage (higher Classical purity)
- 5% Brazilian heritage
- 5% assorted international exposure

**Japanese city:**
- 90% Classical Kodokan (1.0)
- 7% Classical + one foreign training stint
- 3% outlier: returned Brazilian-Japanese, foreign-trained

**Central European city:**
- 40% Classical Kodokan (1.0)
- 25% Classical + French INSEP influence
- 15% Classical + Russian sambo trace
- 10% Georgian heritage (higher in some specific cities)
- 10% assorted

**Tbilisi / Georgian city:**
- 85% Georgian (0.8+)
- 10% Georgian + Russian blend
- 5% outlier

These tables are design stubs. They will be refined as the game's world
map is built out in Ring 4.

### Starter belt distribution

Most prospects showing up to a new dojo are white belts or very junior
yellow belts, regardless of city. The rare exception — a colored belt
walking in — is a meaningful event. Belt rank is independent of
style_dna; a white belt with 0.6 Brazilian BJJ weighting is a kid whose
father taught them jiu-jitsu on the living room floor, not a champion
in disguise.

### Seminars as demographic amplifiers
A visiting specialist temporarily shifts the dojo's cultural gravity.
Recruits during and immediately after a seminar have a higher
probability of carrying some of the visiting style's DNA — because
real recruits often show up *because* they heard about the seminar.
This creates a soft feedback loop where cultural investment attracts
culturally-matched prospects over time.

---

## Coach Voice and Instruction Reception

This is where the Cultural Layer directly touches Ring 2.

The research document identifies **seven instruction categories** and
several **cultural voice modifiers** (volume, emotional register,
language mix, technical specificity, instruction length). A coach's
voice is defined by both:

```python
coach_voice: {
    categories_used: list[InstructionCategory]  # which of the 7 they reach for
    volume: float                                # 0.0 quiet ↔ 1.0 loud
    emotional_register: float                    # 0.0 restrained ↔ 1.0 intense
    technical_specificity: float                 # 0.0 motivational ↔ 1.0 technical
    language_mix: dict[Language, float]          # e.g. {EN: 0.7, JP: 0.3}
    instruction_length_bias: float               # 0.0 single-word ↔ 1.0 sentences
}
```

### Cultural defaults

- **Japanese coach**: quiet, restrained, high technical specificity, high
  Japanese language mix, single-word bias
- **Georgian coach**: loud, intense, low technical specificity (more
  motivational), Georgian language mix, short bias
- **French coach**: moderate volume, calm, very high technical
  specificity, French-English-Japanese mix, moderate length
- **Brazilian coach**: loud, emotional, moderate technical specificity,
  Portuguese-Japanese mix, moderate length

### Instruction reception formula

Building on the existing formula
(`composure × trust × fight_iq × (1 - fatigue)`), the Cultural Layer
adds a **compatibility term**:

```python
reception = (
    composure
    × trust
    × fight_iq
    × (1 - fatigue)
    × voice_compatibility(coach_voice, fighter_training_lineage)
)
```

`voice_compatibility` returns 1.0 when the coach's voice profile aligns
with what the fighter grew up hearing in their training, and drifts
toward 0.6–0.8 as the mismatch grows. A fighter whose training lineage
is 100% Classical Kodokan receiving instructions from a Georgian-voiced
coach receives them at ~0.7 efficiency, even if trust is high. The
instructions don't feel wrong — they just don't *parse* as fast.

This creates a meaningful game design space: a sensei who wants to
coach a Georgian-trained prospect well must either adopt some of the
Georgian voice pattern in their chair (possible, with effort), or
accept the reception penalty, or train the prospect long enough to
shift their training lineage closer to the dojo's norm.

---

## How This Layer Grows Ring by Ring

### Ring 1 — Not involved
The match engine, grip sub-loop, and throw resolution operate on
biomechanics and belt rank alone. A fighter's style_dna is dormant
data. Nothing observable happens.

### Ring 2 — Coach voice becomes real
The Matte window uses coach_voice × fighter_training_lineage to
modulate reception. The seven-category instruction taxonomy is
implemented. The first fully-realized cultural coaches ship with
the game as NPCs.

### Ring 3 — Seminars and cross-training
The Dojo system gains the event framework: schedule a seminar,
send a judoka on a cross-training stint. Style_dna begins to shift
observably over training cycles. The dojo's institutional style_dna
is tracked but only barely — its effect is subtle.

### Ring 4 — The full lineage system
Recruitment tables by city go live. Sensei style_dna passes to
students and to the dojo. Multigenerational drift becomes the
central drama. The Wall remembers which style each champion came
from. The thirteen seeds fade into hybridized reality.

---

## Explicit Non-Goals

**Not a geopolitics game.** The thirteen styles are not nations in a
strategy sense. There is no World Cup bracket, no national rivalries
with mechanical consequences, no "prestige" earned by beating a
specific country. The cultural layer is about *how fighters fight and
how coaches speak*, not about international politics.

**Not a stereotype engine.** The seeds are starting vocabulary, not
destiny. A Georgian-heritage fighter may blossom into a ne-waza
specialist under a Brazilian sensei. The game rewards the designer
and player who refuses to treat culture as a fixed label.

**Not cultural tourism.** No caricatures, no decorative exoticism. The
research document is rigorous about what each tradition actually
produces in the sport. The game's implementation will be equally
rigorous.

**Not for Ring 1.** Phase 2 Session 1 does not touch this. The
grip sub-loop ships without any cultural data wired in. This document
exists so the hooks are declared and the architecture doesn't
accidentally rule out the layer later.

---

## Required Data Model Additions (for Ring 2+)

See `data-model.md` v0.3 for the full spec. Summary:

**Added to Identity layer:**
- `nationality: str`
- `training_lineage: list[str]` (ordered list of sensei IDs or school IDs)
- `style_dna: dict[StyleID, float]` (sums to 1.0)
- `stance_matchup_comfort: dict[MATCHED|MIRRORED|OFF_SIDE, float]`

**Added to Dojo object (Ring 3+):**
- `institutional_style_dna: dict[StyleID, float]`
- `seminar_history: list[SeminarEvent]`
- `sensei_lineage: list[JudokaID]`

---

*Document version: April 14, 2026 (v0.1).
Written before any cultural-layer code exists.
Update as each ring implements its cultural systems.*
