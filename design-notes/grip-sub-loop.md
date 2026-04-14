# The Grip Sub-Loop — Design Note v0.1
### The Mechanic That Gives a Match Its Texture

*This document specifies the continuous micro-cycle that runs between Hajime
and Matte. It is the primary mechanic added in Ring 1 Phase 2 Session 1, and
it is what separates Tachiwaza from every other simulation of combat sports.*

---

## Why This Exists

Almost every fighting game — and every judo game that has ever existed —
models a match as: setup → throw attempt → result. Either the throw works
or it doesn't. The space between throws is either loading time or a minigame
abstraction.

Real judo doesn't look like that. **A real match is mostly grip fighting.**
Two bodies searching for purchase, breaking contact, re-engaging, wearing
each other down in ways that don't produce scores but absolutely produce
outcomes. A four-minute contest at elite level typically contains two to
four committed throw attempts. The rest is the grip war — the place where
fatigue accumulates, composure drifts, and most matches are actually decided
before anyone attempts a technique.

Phase 1's match log had a rhythm problem: throw → throw → throw, too fast,
no texture between attempts. The Grip Sub-Loop solves that problem not by
slowing the tick rate but by giving the ticks something *real* to do.

---

## The Three Rhythms of a Match

Tachiwaza has three nested rhythms running simultaneously, each with its own
trigger and its own timescale:

### Rhythm 1 — The Tick
The simulation's fundamental heartbeat. ~240 ticks per match, one per
match-second. Every tick updates fatigue, composure, grip state, posture.
Most ticks are quiet — they accumulate change without producing visible
events.

### Rhythm 2 — The Grip Sub-Loop
Runs continuously between Hajime and Matte. A single sub-loop cycle spans
maybe 5–20 ticks: engagement → tug-of-war → resolution (kuzushi window,
stifled reset, or committed throw attempt) → re-engagement. **The referee
is not involved.** Dozens of sub-loop cycles occur between any two Matte
calls.

### Rhythm 3 — The Matte Cycle
Ref-driven. Triggered by stalemate, out-of-bounds, a stuffed throw the ref
won't let breathe, or penalties. Research shows 8–15 Matte cycles per
4-minute match at elite level, with a 2:1 work-rest ratio (roughly 23
seconds of live action, 11 seconds of pause). This is the coach's window —
the only time a coach may speak.

The key insight: **Rhythm 2 can resolve the match without Rhythm 3 ever
firing.** A fighter who wins the opening grip war decisively, opens a
kuzushi window at tick 12, and lands seoi-nage for ippon has ended the match
before the referee ever needed to call Matte. The coach never got to speak.
That's not a bug. That's judo.

---

## The Sub-Loop State Machine

Every sub-loop cycle passes through these states:

```
         ┌─────────────────────────────────────────┐
         │                                         │
         ▼                                         │
   ENGAGEMENT ──────► TUG_OF_WAR ──────► RESOLUTION
   (grips form)      (contested)         │
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                  KUZUSHI_WINDOW   STIFLED_RESET   THROW_ATTEMPT
                  (1–3 ticks)      (break, breathe) (committed)
                          │              │              │
                          │              │              │
                  ┌───────┴──┐           │          ┌───┴────┐
                  ▼          ▼           │          ▼        ▼
              throw        window       re-         lands   stuffed
              launched     closes       engage      (score) (ne-waza?)
```

### ENGAGEMENT
Both fighters close distance and establish initial grips. Duration: 1–3
ticks. Cost: minimal fatigue on hands/forearms. The sub-loop enters
TUG_OF_WAR the moment both fighters have at least one live grip.

### TUG_OF_WAR
The core state. Each tick resolves a micro-exchange:

```
tori_grip_strength = (
    tori_effective_hand
    × tori_effective_forearm
    × grip_security_bonus(grip_configuration, stance_matchup)
    × (1 - tori_current_forearm_fatigue)
)

uke_grip_resistance = (
    uke_effective_hand
    × uke_effective_forearm
    × frame_bonus(posture, stance_matchup)
    × (1 - uke_current_forearm_fatigue)
)

grip_delta = tori_grip_strength - uke_grip_resistance
```

Each tick, both fighters accumulate forearm fatigue proportional to how hard
they are contesting. The `grip_delta` drifts as fatigue shifts — the fighter
with better cardio and lower baseline fatigue gradually wins the delta even
if they started behind.

### RESOLUTION — The Three Outcomes

**KUZUSHI_WINDOW** — `grip_delta > kuzushi_threshold` for enough consecutive
ticks. A 1–3 tick window opens where tori can attempt a throw with a
substantially elevated success probability. If tori has the right
biomechanical fit (height differential, hip geometry) for a throw they know,
this is the moment to commit. If the fit is wrong, tori may let the window
close rather than force a bad-geometry throw.

**STIFLED_RESET** — `abs(grip_delta) < stalemate_threshold` for sustained
ticks (maybe 15+) with neither fighter able to dominate. Both fighters break
contact, step back, breathe for 2–4 ticks, and re-engage. No Matte is
called. No composure hit for either fighter. Fatigue carries over. This is
the most common resolution in a match.

**THROW_ATTEMPT** — A fighter commits to a throw regardless of window state.
This happens when: (a) a kuzushi window is open and the fighter has
throw-in-vocabulary fit, or (b) a fighter decides to force an attempt under
stress (running clock, trailing on score, desperation).

A forced attempt with no window open has very low success probability and
high stuff-probability. This is how shido-for-false-attack enters the
simulation organically: force enough bad attempts and the ref notices.

---

## The Biomechanical Spine

The Grip Sub-Loop is where the five physical variables from
`biomechanics.md` first become *observable in play*:

### Arm Reach
Determines who can grip first in ENGAGEMENT. Longer reach = higher chance
of securing the preferred grip configuration before the opponent does.
Inside TUG_OF_WAR, reach affects how much of the opponent's body is
accessible from the current grip.

### Hand & Forearm Strength (× Fatigue)
The direct inputs to `tori_grip_strength`. These are the variables that
drain most visibly during a long sub-loop. The first fighter whose forearms
cross their fatigue floor loses the grip war — even if they started
stronger.

### Hip Height Differential
Determines what kuzushi force is *geometrically available* when a window
opens. Two fighters with identical grip strength but different hip heights
produce different kuzushi outcomes. A tall fighter who wins the grip delta
against a compact fighter may find the kuzushi window opens in a direction
that doesn't serve their signature throw — so they don't commit.

### Height & Limb Length
Biases which grip configurations are reachable and at what cost. A 170cm
fighter reaching for a high-collar grip on a 195cm opponent pays higher
forearm cost per tick than the reverse. The grip war is not symmetrical.

### Weight Distribution
Affects frame_bonus in the uke_grip_resistance calculation. A front-loaded
fighter in TUG_OF_WAR has different resistance characteristics than a
back-loaded fighter. This also shifts as fatigue alters posture — late in
a match, a fighter whose weight has drifted backward becomes vulnerable to
inner reaps in a way they weren't at tick 0.

---

## Why the Coach Sometimes Doesn't Speak

The defining feature of this mechanic: **a match can end inside a single
sub-loop cycle.**

Scenario: Tanaka (183cm, strong right-hand grip, seoi specialist) fights
Sato (175cm, classical posture, grip vulnerable on left side in mirrored
stance). Stance matchup is mirrored. Sato's left-hand grip floor is low.

```
Tick 0   — Hajime.
Tick 3   — Engagement. Both fighters secure initial grips.
Tick 4   — Tug-of-war begins. Tanaka's right overpowers Sato's left.
Tick 9   — grip_delta crosses kuzushi_threshold. Window opens.
Tick 10  — Tanaka has perfect height + hip geometry for seoi. Commits.
Tick 11  — Throw lands clean. IPPON.
Tick 12  — Match ends.
```

Twelve ticks. No Matte was ever called. The coach never opened their mouth.

This is not a failure mode — this is one of the most beautiful outcomes in
real judo, the *ippon seoi-nage ceremony* where everything aligned in the
first exchange. The game has to allow for it or it will feel fake to anyone
who has watched a real match.

It also creates a fundamental coaching dilemma: **preparation, not
intervention, is the primary lever.** If your fighter ended a match in 12
seconds, what you did in the dojo mattered. What you said in the chair was
irrelevant because the chair never opened. Good coaching over a career is
distributed mostly across training, not chair-time.

The coach as *luxury, not certainty* — this is the game's first real lesson
about the limits of authorship. Systems are the author. Sometimes the
systems resolve before the coach arrives.

---

## Prose Rules

Following the "physics resolves; prose marks" principle from
`biomechanics.md`:

**The sub-loop runs silently most of the time.** A kuzushi window that
opens and closes without commitment is not narrated unless it's
significant. Stifled resets early in a match are not narrated. The log
doesn't say "sub-loop cycle 14 resolved with stifled reset."

**The log marks thresholds being crossed.** When a fighter's grip
genuinely fails after sustained resistance, that gets a sentence. When a
kuzushi window opens in a direction the fighter's signature throw can't
exploit, and they let it close — that gets a sentence when it matters to
the match's trajectory. When a fighter forces a throw under stress and
stuffs it badly, the log earns that moment.

**Stifled resets become visible through cumulative language.** Early in
the match: silent. Mid-match, once a pattern emerges: *"They've broken
apart four times now. Neither can find the grip he wants."* Late-match,
once fatigue is genuine: *"Another reset. Sato is breathing through his
mouth."*

**The sentence reflects the physics.** A throw that lands because the
kuzushi window opened cleanly reads differently from a throw that lands
because the opponent was exhausted and the sub-loop had already decided
things tick 80 ago. The log never explains this — it just sounds
different.

---

## Calibration Knobs

These are the tunable parameters. They do not have correct values yet;
they will be calibrated by watching many matches in Phase 3.

| Parameter | Role | Starting Estimate |
|---|---|---|
| `kuzushi_threshold` | grip_delta required to open window | 2.5 |
| `kuzushi_window_duration` | ticks the window stays open | 1–3 |
| `stalemate_threshold` | grip_delta band considered stalemate | ±0.8 |
| `stalemate_duration` | ticks of stalemate before reset | 15 |
| `reset_recovery_ticks` | breath time before re-engagement | 2–4 |
| `engagement_duration` | ticks to establish grips | 1–3 |
| `forearm_fatigue_rate` | per-tick cost of TUG_OF_WAR | 0.004 |
| `force_attempt_penalty` | success multiplier when no window | 0.15 |

All of these live in a single `sub_loop_config` dict that can be adjusted
per-fighter, per-match, or globally during calibration.

---

## What Phase 2 Session 1 Builds

✅ `GripSubLoop` state machine with five states (ENGAGEMENT, TUG_OF_WAR,
KUZUSHI_WINDOW, STIFLED_RESET, THROW_ATTEMPT)

✅ Per-tick grip_delta calculation using hand/forearm effective values

✅ Three resolution paths wired to match state:
- Kuzushi window → throw_attempt() → existing throw resolution
- Stifled reset → fatigue persists, match continues, no Matte
- Forced throw attempt → throw_attempt() with penalty

✅ Forearm fatigue accumulation tied to time-in-tug-of-war

✅ Stifled reset counter in State for prose triggers

✅ Log output that stays quiet on silent sub-loop activity, marks
threshold crossings, and increases density as fatigue develops

## What Phase 2 Session 1 Does NOT Build

- Matte detection (Session 2)
- Referee class (Session 2)
- Full prose templating (Phase 3+ territory; Session 1 uses placeholder
  log strings that mark the right moments but don't yet sound good)
- Ne-waza window resolution (flagged but not playable)
- Shido escalation from forced attempts (noted in state; consequence in
  Session 2 when the Referee exists)

---

## How This Changes Ring 1

Before the Grip Sub-Loop, Ring 1 was: tick loop + throw attempts + scoring.

After the Grip Sub-Loop, Ring 1 is: tick loop + continuous grip physics +
throw attempts arising from grip physics + scoring. The match has a pulse
underneath the events.

This is the layer that makes the Anchoring Scene real. When Tanaka "steps
in" and "reaches for the lapel," that's the Sub-Loop entering
ENGAGEMENT. When Sato's "left hand intercepts," that's a contested initial
grip. When "Tanaka's forearms fatiguing" appears in the log, that's
forearm fatigue crossing a visible threshold inside TUG_OF_WAR.

The scene in the master doc was describing this mechanic before it
existed. Phase 2 Session 1 is the session where the words finally have
code underneath them.

---

*Document version: April 14, 2026 (v0.1).
Written before Phase 2 Session 1 code exists.
Update after calibration passes reveal the real values.*
