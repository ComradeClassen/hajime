# kuzushi.py
# Phase A.1 — grip-as-cause polarity reversal foundation (HAJ-130).
#
# Spec: design-notes/grip-as-cause.md §2 (Event-Driven Kuzushi) and §3.6
# (Combo Pulls and Sequence Composition).
#
# Kuzushi was previously a momentary CoM-envelope predicate
# (body_state.is_kuzushi). The spec wants it as a decaying *event log*: each
# pull or foot attack emits a force event into uke's buffer, and the throw
# selection layer reads the *accumulated, decayed* state to decide whether
# uke is currently compromised in a way some throw's signature matches.
#
# This module is data + math only. Nothing here mutates Judoka or fires from
# action handlers — that wiring is HAJ-A.2 (PULL emits) and HAJ-A.3
# (signature_match reads).
#
# Naming note: the existing `compromised_state.py` module uses the same word
# for the *failed-throw* tori-state machine (Part 6.3). Different concept,
# different namespace. Importing both side-by-side is fine because the
# clashing name `compromised_state` only exists as a function in this module
# and as a module name elsewhere.

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from judoka import Judoka

# 2D vector in the mat frame, meters or m/s depending on context. Aligned
# with body_state.py's convention so events can be composed directly with
# CoM velocities without a wrapper type.
Vector2 = tuple[float, float]


# ---------------------------------------------------------------------------
# SOURCE
# ---------------------------------------------------------------------------
class KuzushiSource(Enum):
    """Where a kuzushi event came from. Drives source-specific scoring at the
    signature-match layer (HAJ-A.3 onward) — e.g. foot attacks may compose
    with pulls but score differently for sweep-family throws."""
    PULL        = auto()  # Emitted by a PULL action through an established grip.
    FOOT_ATTACK = auto()  # Emitted by ko-uchi / o-uchi / de-ashi style foot attacks.
    OTHER       = auto()  # Catch-all for future emitters; tests use this too.


# ---------------------------------------------------------------------------
# EVENT
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KuzushiEvent:
    """A single force event applied to uke's CoM at a single tick.

    `vector` is the unit (or near-unit) direction the kuzushi pushes uke's
    CoM; `magnitude` is the force amplitude at emission. Decay is applied
    later by `compromised_state` so the stored magnitude is always the raw
    emission value — calibration can re-tune the decay curve without
    re-emitting events.
    """
    tick_emitted: int
    vector:       Vector2
    magnitude:    float
    source_kind:  KuzushiSource


# ---------------------------------------------------------------------------
# DECAY
# ---------------------------------------------------------------------------
# Half-life of an event in ticks. Spec §2: "a pull two ticks ago is mostly
# live; one from ten ticks ago is mostly faded". With a 5-tick half-life:
#   age=0  → 1.000   (just emitted)
#   age=2  → 0.757   (mostly live)
#   age=5  → 0.500   (half)
#   age=10 → 0.250   (mostly faded — spec wanted "mostly faded", this leaves
#                    a small tail; calibration may want a steeper curve)
#   age=20 → 0.0625  (essentially gone, but buffer cap drops it before then)
#
# Calibration target: HAJ-A.7 will tune against telemetry. Until then the
# 5-tick half-life and 20-tick buffer give a clean mostly-live → mostly-gone
# arc inside one combo's worth of ticks.
DECAY_HALF_LIFE_TICKS: float = 5.0
KUZUSHI_BUFFER_CAPACITY: int = 20


def decay_factor(age_ticks: int) -> float:
    """Multiplicative decay applied to an event's magnitude given its age.

    Negative ages (event from the future) are clamped to 1.0 — defensive
    against caller bugs, not an expected condition.
    """
    if age_ticks <= 0:
        return 1.0
    return 0.5 ** (age_ticks / DECAY_HALF_LIFE_TICKS)


# ---------------------------------------------------------------------------
# COMPROMISED STATE (accumulated decayed kuzushi)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CompromisedState:
    """Sum of all live kuzushi events on uke at a given tick, with decay
    applied. `vector` is the resultant push direction (post-cancellation);
    `magnitude` is its Euclidean length. `total_decayed_magnitude` is the
    *uncancelled* sum — useful when callers care about how much kuzushi
    pressure exists regardless of direction (e.g. "is uke being worked
    over right now?" vs. "is uke pushed in any one direction?").
    """
    vector:                   Vector2
    magnitude:                float
    total_decayed_magnitude:  float

    @classmethod
    def empty(cls) -> "CompromisedState":
        return cls(vector=(0.0, 0.0), magnitude=0.0, total_decayed_magnitude=0.0)


def compromised_state(
    events:       Iterable[KuzushiEvent],
    current_tick: int,
) -> CompromisedState:
    """Collapse a stream of events into a single compromised-state snapshot.

    Each event contributes `vector * magnitude * decay_factor(age)` to the
    resultant. Same-direction events stack additively; opposing events
    partially or fully cancel via vector summation.

    `total_decayed_magnitude` is computed from per-event magnitudes (not
    from the resultant), so two equal-and-opposite pulls yield magnitude=0
    but total_decayed_magnitude=2*decayed_each. That distinction matters
    for the HAJ-A.3 layer: a fighter being yanked in two directions at once
    is still being kuzushi'd, even if the net vector is zero.
    """
    rx = ry = 0.0
    total = 0.0
    for ev in events:
        d = decay_factor(current_tick - ev.tick_emitted)
        contribution = ev.magnitude * d
        vx, vy = ev.vector
        rx += vx * contribution
        ry += vy * contribution
        total += contribution
    mag = (rx * rx + ry * ry) ** 0.5
    return CompromisedState(
        vector=(rx, ry),
        magnitude=mag,
        total_decayed_magnitude=total,
    )


# ---------------------------------------------------------------------------
# BUFFER HELPERS
# ---------------------------------------------------------------------------
def fresh_buffer() -> deque[KuzushiEvent]:
    """Construct an empty per-fighter buffer with the standard cap. Used as
    the default_factory for `Judoka.kuzushi_events`."""
    return deque(maxlen=KUZUSHI_BUFFER_CAPACITY)


def record_kuzushi_event(judoka: "Judoka", event: KuzushiEvent) -> None:
    """Append an event to the judoka's buffer. The deque's `maxlen` handles
    auto-drop of the oldest event when the buffer is full."""
    judoka.kuzushi_events.append(event)
