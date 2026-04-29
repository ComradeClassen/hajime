# reaction_lag.py
# HAJ-149 — fight_iq-modulated reaction lag, the perception-to-response axis.
#
# Each fighter has a `reaction_lag` value, computed per-event from the
# perceiver's fight_iq and the situation around the perception. The lag
# is *signed* — elite fighters anticipate (negative lag), novices react
# late (positive lag).
#
#   lag ≤ −1 : anticipates the opponent's commit before it lands
#   lag ==  0 : reacts on the commit tick
#   lag ≥ +1 : reacts after the commit; sees the consequence
#
# v0.1 punts on a calibrated distribution — the ranges below are a
# reasonable starting point so the asymmetric perception axis exists
# and is testable. v0.2 calibrates against match telemetry.
#
# See HAJ-149 spec §"Signed reaction lag" for the per-axis modulators
# and §"Open questions resolved" for the v0.1 / v0.2 scope split.

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from judoka import Judoka


# ---------------------------------------------------------------------------
# CALIBRATION CONSTANTS
# ---------------------------------------------------------------------------
# fight_iq → base expected lag mapping (linear; iq runs 0..10).
#
# At iq=10 the base sits at -2.0 (elite anticipation: "reads developing
# intent two ticks before commit"). At iq=5 the base sits at 0.0 (mid:
# "reacts on the commit tick"). At iq=0 the base sits at +2.0 (novice:
# "reacts two ticks after commit; often too late"). The slope is
# (lag_at_iq0 - lag_at_iq10) / 10 = (2.0 - (-2.0)) / 10 = 0.4 per iq
# unit, and the intercept at iq=0 is +2.0.
BASE_LAG_INTERCEPT_IQ0:  float = 2.0    # iq=0 sits two ticks late
BASE_LAG_SLOPE_PER_IQ:   float = -0.4   # each iq point trims 0.4 ticks

# Distribution std around the expected lag. Discrete tick-resolution
# samples come from rounding a Gaussian draw; std=0.6 gives ~85% of
# samples within ±1 tick of the expected value (one-tick variance).
LAG_SAMPLE_STD:          float = 0.6

# How much each modulator shifts expected lag (in ticks).
DISGUISE_LAG_PENALTY:    float = 1.5    # max shift toward late at disguise=1.0
FATIGUE_LAG_PENALTY:     float = 0.8    # tired = slower perception
COMPROMISED_LAG_PENALTY: float = 1.0    # compromised state = degraded read

# Composure × desperation interaction. A high-composure fighter under
# desperation focuses (sharpens read); a low-composure fighter under
# desperation panics (dulls read). Centered around composure_frac=0.5;
# above sharpens (negative shift), below dulls (positive shift).
DESPERATION_COMPOSURE_PIVOT: float = 0.5
DESPERATION_COMPOSURE_GAIN:  float = 1.0

# Familiarity: seen this throw class before in the match. Caps the
# perception bonus so a single repeat doesn't make uke clairvoyant.
FAMILIARITY_LAG_BONUS_PER_OBS: float = 0.3
FAMILIARITY_OBS_CAP:           int   = 3

# Hard clamps on the final lag — keep it inside a sane window so the
# pre-commit / brace / re-plan scheduling doesn't try to schedule
# events more than a few ticks away.
LAG_CLAMP_MIN: int = -2
LAG_CLAMP_MAX: int = +2


# ---------------------------------------------------------------------------
# DISGUISE — composite of sequencing and pull-execution skill
# ---------------------------------------------------------------------------
def disguise_for(judoka: "Judoka") -> float:
    """A fighter's disguise level — how readable / hard-to-read their
    setup is. Returns a value in [0, 1].

    Pre-HAJ-149 there was no `kuzushi_disguise` attribute. Disguise is
    derived from existing skill axes that *should* correlate with smooth,
    hard-to-read setups: sequencing precision (clean combos that don't
    telegraph) and pull execution (no self-cancellation that gives the
    plan away). v0.2 may promote disguise to a first-class axis.
    """
    from skill_vector import axis
    seq = axis(judoka, "sequencing_precision")
    pull = axis(judoka, "pull_execution")
    return max(0.0, min(1.0, 0.5 * (seq + pull)))


# ---------------------------------------------------------------------------
# EXPECTED LAG
# ---------------------------------------------------------------------------
def expected_lag(
    perceiver: "Judoka",
    attacker: "Judoka",
    *,
    fatigue_frac: Optional[float] = None,
    compromised: bool = False,
    in_desperation: bool = False,
    composure_frac: Optional[float] = None,
    familiarity_count: int = 0,
) -> float:
    """Compute the perceiver's expected reaction lag in (signed) ticks.

    The result is a continuous expected value; `sample_lag` samples a
    discrete tick from a Gaussian centered on this expected value.

    All modulator arguments are optional because callers may pass `None`
    when they don't have the relevant signal handy (e.g., a unit test of
    the base mapping). Keep call sites uncluttered: only fill the
    arguments that are actually load-bearing for this perception event.
    """
    iq = float(perceiver.capability.fight_iq)
    base = BASE_LAG_INTERCEPT_IQ0 + BASE_LAG_SLOPE_PER_IQ * iq

    # Opponent's disguise — high disguise pushes our lag toward zero /
    # positive (we read them less well).
    base += disguise_for(attacker) * DISGUISE_LAG_PENALTY

    # Fatigue — defaults to derived from cardio if not supplied.
    if fatigue_frac is None:
        cardio = float(getattr(perceiver.state, "cardio_current", 1.0))
        fatigue_frac = max(0.0, min(1.0, 1.0 - cardio))
    base += fatigue_frac * FATIGUE_LAG_PENALTY

    # Compromised state.
    if compromised:
        base += COMPROMISED_LAG_PENALTY

    # Composure × desperation.
    if in_desperation:
        if composure_frac is None:
            ceiling = max(1.0, float(perceiver.capability.composure_ceiling))
            composure_frac = max(0.0, min(
                1.0, perceiver.state.composure_current / ceiling
            ))
        # > pivot → sharpens (negative shift); < pivot → dulls (positive shift).
        delta = (DESPERATION_COMPOSURE_PIVOT - composure_frac)
        base += delta * DESPERATION_COMPOSURE_GAIN

    # Familiarity.
    obs = max(0, min(FAMILIARITY_OBS_CAP, familiarity_count))
    base -= obs * FAMILIARITY_LAG_BONUS_PER_OBS

    return base


# ---------------------------------------------------------------------------
# DISCRETE LAG SAMPLING
# ---------------------------------------------------------------------------
def sample_lag(
    perceiver: "Judoka",
    attacker: "Judoka",
    *,
    rng: Optional[random.Random] = None,
    **modulators,
) -> int:
    """Sample a discrete reaction-lag (in ticks) from the distribution
    centered on `expected_lag(...)`. Clamped to [LAG_CLAMP_MIN,
    LAG_CLAMP_MAX] so consequence-queue scheduling doesn't drift into
    multi-tick anticipation (out of v0.1 scope).
    """
    r = rng if rng is not None else random
    mu = expected_lag(perceiver, attacker, **modulators)
    raw = r.gauss(mu, LAG_SAMPLE_STD)
    return max(LAG_CLAMP_MIN, min(LAG_CLAMP_MAX, int(round(raw))))


# ---------------------------------------------------------------------------
# RESPONSE TYPE
# ---------------------------------------------------------------------------
@dataclass
class PerceptionResponse:
    """A perceiver's chosen response to an observed intent signal."""
    kind: str               # "INTERRUPT" | "BRACE" | "REPLAN" | "NONE"
    perceiver: str          # fighter name
    target_actor: str       # opponent name
    target_tick: int        # the tick the response acts upon (typically the
                            # attacker's resolution tick)
    sampled_lag: int        # the lag this perceiver rolled
    notes: str = ""


def choose_response(
    perceiver: "Judoka",
    attacker: "Judoka",
    *,
    sampled_lag: int,
    commit_tick: int,
    rng: Optional[random.Random] = None,
) -> PerceptionResponse:
    """Pick a response type for a perceived commit.

    v0.1 implements the BRACE-for-N+1 path as the concrete behavior:
    when the perceiver reads the commit in time (lag <= 0), they choose
    to brace for the opponent's resolution tick. Lag == +1 still allows
    reaction on the resolution tick (just barely in time). Lag >= +2 is
    "too late" — no response.

    INTERRUPT and REPLAN are scaffolded for HAJ-150 / HAJ-152 to wire in;
    the response kinds are valid in the type system but not yet
    selected here. See the HAJ-149 spec §"Three perception responses".
    """
    a_name = attacker.identity.name
    p_name = perceiver.identity.name
    # Resolution tick is commit_tick + 1 under HAJ-148's deferral rule.
    resolution_tick = commit_tick + 1
    # The perceiver's effective awareness tick.
    awareness_tick = commit_tick + sampled_lag

    if awareness_tick <= resolution_tick:
        return PerceptionResponse(
            kind="BRACE",
            perceiver=p_name, target_actor=a_name,
            target_tick=resolution_tick, sampled_lag=sampled_lag,
            notes=f"awareness@t{awareness_tick}, brace for resolution",
        )
    return PerceptionResponse(
        kind="NONE",
        perceiver=p_name, target_actor=a_name,
        target_tick=resolution_tick, sampled_lag=sampled_lag,
        notes=f"awareness@t{awareness_tick}, after resolution — too late",
    )
