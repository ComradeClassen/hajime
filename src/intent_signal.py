# intent_signal.py
# HAJ-149 — pre-commit intent signals.
#
# A substantive action emits a non-substantive *intent signal* that the
# opposing fighter's perception system can read. Signals are the
# perception-window substrate the reaction-lag math operates against.
#
# v0.1 emits a single signal at the commit tick (the start of a multi-
# tick attempt or the silent-prose tick of an N=1 deferred commit). The
# spec calls for signals on N−2 and N−1 *before* the commit; that
# requires a planning-ahead selector rewrite (HAJ-150 / HAJ-152 work).
# v0.1 collapses the perception window into the deferral gap that
# HAJ-148 already produces between commit (tick N) and resolution
# (tick N+1). Elite perceivers (sampled_lag <= 0) read the commit on
# its own tick and brace for resolution; novices (sampled_lag >= +2)
# only see the consequence after the fact.
#
# The IntentSignal dataclass is the wire format the perception system
# consumes; it carries enough metadata for downstream consumers (HAJ-153
# narration) to author Neil-Adams-style anticipation prose later.

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from throws import ThrowID


# ---------------------------------------------------------------------------
# SIGNAL CATEGORY
# ---------------------------------------------------------------------------
# v0.1 signal taxonomy. Throw-class is THROW_CLASS_* derived from
# ThrowDef.preferred_stance_parity / category. v0.2 expands per the
# physics-substrate.md new-section work tagged in HAJ-149's Out-of-scope.
SETUP_THROW_COMMIT:    str = "throw_commit"
SETUP_GRIP_STRIP:      str = "grip_strip"
SETUP_NE_WAZA_INIT:    str = "ne_waza_init"
SETUP_PULL:            str = "pull"
SETUP_FOOT_ATTACK:     str = "foot_attack"
SETUP_DEFENSIVE_BLOCK: str = "defensive_block"


@dataclass
class IntentSignal:
    """A non-substantive event emitted alongside a substantive action.

    `tick` is the tick the signal was emitted (the commit / setup tick
    in v0.1). `setup_class` is the high-level intent the perceiver can
    read at any specificity. `throw_id` is populated when the signal
    originated from a throw commit; None for grip / ne-waza signals.
    `specificity` ∈ [0, 1] — 1.0 means the perceiver can fully name the
    technique (when their fight_iq + the signal pass thresholds);
    0.0 means "something is happening, can't tell what." `disguise`
    captures tori's read difficulty at the moment of emission.
    """
    tick: int
    fighter: str
    setup_class: str
    throw_id: Optional[ThrowID] = None
    specificity: float = 0.5
    disguise: float = 0.0
    # Reference back to the source action's bookkeeping for downstream
    # consumers (perception state, narration). Engine event consumers
    # use this to associate intent → response → resolution.
    source_event_type: Optional[str] = None
