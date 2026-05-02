# Narration decouple v1 — architecture

HAJ-167. Companion notes to grip-as-cause.md §11. Defines the windowed-
pull narration architecture that replaces the per-event push pattern
HAJ-162 patched for two specific families.

## Why decouple

The pre-decouple narrator (`MatSideNarrator.consume_tick`) was already a
per-tick pull (the engine handed it `events` + `bpes` once per tick),
but its detectors only ever read the current tick's slice. Every prose
family that needed history (a pull followed by no commit; an intent
followed by an outcome) had to either fire blindly on the current tick
or ad-hoc track per-actor state on the narrator instance. The latter
worked but didn't generalize: each new family bolted on its own state
field. HAJ-165 alone added two (`_last_posture`, `_last_actor_source_tick`),
and the per-region tracking in HAJ-142 added a third.

The decouple inverts this. The narrator owns a fixed-size **tick window**
— the last N frames of (events, BPEs, lightweight match snapshot) —
and runs an explicit ordered **rule pipeline** over the whole window
each tick. Rules can read across frames; gap-surfacing prose becomes
straightforward; promotion rules are first-class.

## The tick window

`TickFrame` carries the engine state for one tick:

```
TickFrame:
    tick:           int
    events:         list[Event]
    bpes:           list[BodyPartEvent]
    snapshot:       MatchSnapshot
```

`MatchSnapshot` is the *minimum* set of match-level fields a rule might
need to read against the past:

```
MatchSnapshot:
    tick:                  int
    position:              Position
    sub_loop_state:        SubLoopState
    fighter_a_region:      MatRegion
    fighter_b_region:      MatRegion
    fighter_a_posture:     Posture
    fighter_b_posture:     Posture
    fighter_a_com:         tuple[float, float]
    fighter_b_com:         tuple[float, float]
    grip_count_a:          int
    grip_count_b:          int
    in_progress_attackers: frozenset[str]
```

Snapshots are immutable per-tick; we don't deep-copy the live `Match`.

Window size N is **8 ticks** at v1 (≈8 s game time at 1 tick/s). This
is enough for:

- Throw resolution chains (typical N=1 throw spans 4 ticks; N=2 spans
  5; the 8-tick window catches both with margin).
- Pull → commit gap surfacing (ladder picks a commit within ~3 ticks
  of a pull when one is coming).
- Intent → outcome readback (HAJ-149 N+1 contract is at most a couple
  of ticks).

Stride is 1 — the window slides every tick. Older frames are dropped.

## The promotion-rule pipeline

The rules below run in order each pull tick. Each rule reads the
window and may emit `MatchClockEntry` candidates plus optional
`SuppressTag` entries that block lower-priority rules.

| # | Rule                  | Source                | Window read                   |
|---|-----------------------|-----------------------|-------------------------------|
| 1 | always_promote        | engine event types    | current frame only            |
| 2 | phase_transition      | match snapshot delta  | current vs prev frame         |
| 3 | contradiction         | self-cancel / mismatch| current frame BPEs            |
| 4 | modifier_extreme      | counter BPE modifiers | current frame BPEs            |
| 5 | head_steer            | HEAD_AS_OUTPUT BPE    | current frame BPEs + grips    |
| 6 | posture_change        | posture-derive delta  | current vs prev frame         |
| 7 | region_transition     | mat-region delta      | current vs prev frame         |
| 8 | circling              | MOVE events           | current frame events          |
| 9 | pull_without_commit   | PULL BPE + commit gap | trailing window slice (4-tick) |
| 10| sample                | rate-limited fill     | current frame BPEs            |

Suppression happens via a per-tick `SuppressTag` set. Today only the
"state-change" tag is used: rules 1-4 emit it when they fire so rules
5-10 know to defer. Future rules can introduce more granular tags.

The new rule is **rule 9, pull_without_commit**, which fires K=3 ticks
*after* a PULL BPE if no THROW_ENTRY for the same actor landed in
between. This is the architectural improvement — pre-decouple it fired
on the PULL tick, blind to whether a commit was coming.

## Intent-vs-outcome gap surfacing

The window read makes one canonical gap surfacing trivial:

> A fighter pulls. Three ticks later the engine has either committed
> a throw (the pull was a setup) or hasn't (the pull went nowhere).
> The deferred rule reads the trailing 4 ticks; if no THROW_ENTRY for
> the same actor landed within that span, the gap is real and the
> "tugs at the sleeve — rides it out" line fires honestly.

Pre-decouple the line fired on the pull tick itself. Sometimes it was
right (most pulls don't lead to commits) but it didn't *know* that —
on the ticks when a commit actually followed, the prose still claimed
"rides it out" because it never re-read.

This same pattern applies to other families as the architecture grows:
intent signals followed by no commit, kuzushi setups followed by no
finish, etc. v1 ships only the pull rule; future families slot in.

## Migration

All HAJ-162 / HAJ-165 / HAJ-166 / HAJ-142 detectors migrate to the new
pipeline. The detector method bodies are largely preserved but they
receive a `Window` instead of raw `(tick, events, bpes, match)`. The
state fields each detector previously kept on the narrator instance
(`_last_posture`, `_last_region`) become reads against `window[-2]` —
the previous frame's snapshot — which removes the bookkeeping.

Posture-change detection illustrates the win: pre-decouple required a
per-fighter dict updated on every consume_tick call, with explicit
suppression on KUZUSHI_INDUCED ticks. Post-decouple the rule reads
`window[-1].snapshot.fighter_a_posture` vs `window[-2].snapshot.
fighter_a_posture` and checks if a KUZUSHI_INDUCED event lives in
`window[-1].events` — same logic, half the state.

## Tick interleaving

The narrator runs after the engine has fully resolved a tick (events
emitted, BPEs attached, consequences applied). It does NOT see the
next tick's events when emitting prose for tick T. This is the same
ordering pre-decouple; the decouple doesn't change WHEN the narrator
runs, just WHAT it has access to (window vs single tick).

## What v1 doesn't ship

- **Look-ahead resolvers.** Rules can only read window[-N..0]; they
  can't see the future. The deferred pull-without-commit rule fires
  K ticks late, not predictively.
- **Non-mat-side altitudes.** Stands / review / broadcast altitudes
  (HAJ-144) still use the legacy per-event factory; HAJ-167 only
  migrates mat-side.
- **Full grip-as-cause §11 vision.** Significance scoring, recognition
  modulation, and earned-recognition gating are all HAJ-144 territory.
  v1 just establishes the substrate they will plug into.
