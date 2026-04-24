# action_selection.py
# Physics-substrate Part 3.3: the v0.1 priority ladder.
#
# A deliberately-simple hardcoded decision function. Later rings (Ring 2
# coach instructions, Ring 3 cultural bias, Ring 4 opponent memory) layer
# on top by rewriting or filtering the ladder's output.
#
# The ladder produces up to two Actions per tick, or a single COMMIT_THROW
# compound action that supersedes the two-action cap.

from __future__ import annotations
import random
from typing import Optional, TYPE_CHECKING

from actions import (
    Action, ActionKind,
    reach, deepen, strip, release, pull, push, hold_connective, step, commit_throw,
)
from enums import (
    GripTypeV2, GripDepth, GripTarget, GripMode, DominantSide,
)
from throws import THROW_DEFS, ThrowID
from grip_presence_gate import evaluate_gate, GateResult, REASON_OK
from compromised_state import is_desperation_state

if TYPE_CHECKING:
    from judoka import Judoka
    from grip_graph import GripGraph, GripEdge


# Tuning constants (calibration stubs).
COMMIT_THRESHOLD:             float = 0.65  # perceived signature must clear this to commit
DESPERATION_KUMI_CLOCK:       int   = 22    # tick count that triggers ladder rung 5
HIGH_FATIGUE_THRESHOLD:       float = 0.65  # hand-fatigue at which rung 6 prefers connective
DRIVE_MAGNITUDE_N:            float = 400.0 # PULL/PUSH force a non-desperation drive issues
PROBE_MAGNITUDE_N:            float = 120.0 # default-rung probing force
# Side-effect: match feeds us the grasper's kumi-kata clock; it's not
# visible on the Judoka itself because it belongs to the Match.

# HAJ-49 — intentional false-attack pathway.
# A third commit motivation alongside normal-signature-clears-threshold and
# offensive-desperation. A fighter with enough composure to not be panicked
# but whose kumi-kata clock has drifted into the pre-shido zone may fire a
# deliberately low-commitment drop variant to reset the clock and earn a
# brief post-stuffed breathing window. See physics-substrate.md Part 3.3.1.
FALSE_ATTACK_CLOCK_MIN: int = 18   # earliest clock tick the tactical fake fires
FALSE_ATTACK_CLOCK_MAX: int = 29   # latest — strictly below imminent-shido (29) so
                                    # desperation (which fires at 29) takes precedence
FALSE_ATTACK_MIN_FIGHT_IQ: int = 4  # white/yellow belts don't game the clock; they panic
FALSE_ATTACK_TENDENCY_KEY: str = "false_attack_tendency"  # Identity.style_dna key
FALSE_ATTACK_TENDENCY_THRESHOLD: float = 0.40
FALSE_ATTACK_TENDENCY_DEFAULT:   float = 0.50  # neutral baseline when the key is absent
# Per-tick probability gate. A high-tendency fighter with ~11 ticks in the
# [18, 29) window doesn't fake every single tick — that would fully suppress
# offensive desperation from ever surfacing. Scale tendency by this constant
# so a tendency=0.7 fighter fakes ~7% of eligible ticks (~55% cumulatively
# over the window), leaving meaningful room for the desperation pathway to
# fire when the window expires without a fake committing.
FALSE_ATTACK_PER_TICK_SCALE: float = 0.10

# Priority order of drop-variant throws for a false attack, most preferred
# first. These are the lowest-commitment entries in standard vocabularies:
# fast recovery-to-stance is the whole point of the pathway, so we prefer
# shin-block (TAI_OTOSHI), foot-sweep (KO_UCHI_GARI), drop-seoi, and
# inner-reap (O_UCHI_GARI) over hip-fulcrum or high-amplitude throws.
FALSE_ATTACK_PREFERENCES: tuple[ThrowID, ...] = (
    ThrowID.TAI_OTOSHI,
    ThrowID.KO_UCHI_GARI,
    ThrowID.SEOI_NAGE,
    ThrowID.O_UCHI_GARI,
)

# Gate-bypass reason string for the commit log — read by match.py into the
# same tag-suffix pipeline the desperation path already uses.
REASON_INTENTIONAL_FALSE_ATTACK: str = "intentional_false_attack"


# ---------------------------------------------------------------------------
# TOP-LEVEL ENTRY POINT
# ---------------------------------------------------------------------------
def select_actions(
    judoka: "Judoka",
    opponent: "Judoka",
    graph: "GripGraph",
    kumi_kata_clock: int,
    rng: random.Random | None = None,
    defensive_desperation: bool = False,
) -> list[Action]:
    """Return the judoka's chosen actions for this tick.

    Implements the Part 3.3 priority ladder. Returns 1-2 Actions, or a
    single-element list containing COMMIT_THROW.

    HAJ-35/36: `defensive_desperation` is computed Match-side (requires
    cross-tick history the ladder can't see) and bypasses the grip-
    presence gate when True. Offensive desperation is derived locally
    from composure + kumi_kata_clock.
    """
    r = rng if rng is not None else random

    # Rung 1: stunned → defensive-only (v0.1: just idle).
    if judoka.state.stun_ticks > 0:
        return _defensive_fallback(judoka)

    own_edges = graph.edges_owned_by(judoka.identity.name)
    opp_edges = graph.edges_owned_by(opponent.identity.name)

    # Engagement precedes commit: a throw requires at least pocket contact.
    # Without this, low-fight_iq perception noise on a Couple throw's always-
    # on body/posture dimensions lifts the perceived signature over the commit
    # threshold before any grip exists, and the novice throws from thin air.
    if not own_edges and not defensive_desperation:
        return _reach_actions(judoka)

    # Rung 2: commit if a throw is perceived available AND the grip-presence
    # gate passes (or desperation bypasses it).
    offensive_desperation = is_desperation_state(judoka, kumi_kata_clock)
    commit = _try_commit(
        judoka, opponent, graph, r,
        offensive_desperation=offensive_desperation,
        defensive_desperation=defensive_desperation,
        kumi_kata_clock=kumi_kata_clock,
    )
    if commit is not None:
        return [commit]

    # No edges + no commit path open (e.g. defensive desperation that
    # couldn't find a throw) — fall back to reach.
    if not own_edges:
        return _reach_actions(judoka)

    # Rung 5: kumi-kata clock nearing shido → escalate.
    escalated = (kumi_kata_clock >= DESPERATION_KUMI_CLOCK)

    # If every grip is still shallow (POCKET/SLIPPING), spend both actions
    # seating them — deepen primary, strip the opponent's strongest grip.
    deep_enough = [e for e in own_edges
                   if e.depth_level in (GripDepth.STANDARD, GripDepth.DEEP)]
    if not deep_enough:
        out: list[Action] = [deepen(own_edges[0])]
        if opp_edges:
            target = max(opp_edges, key=lambda e: e.depth_level.modifier())
            strip_hand = _free_hand(judoka) or "right_hand"
            out.append(strip(strip_hand, target))
        else:
            out.append(hold_connective(_primary_hand(judoka)))
        return out

    # Rung 6: fatigued + composed → recover connective.
    hand_fat = _avg_hand_fatigue(judoka)
    if hand_fat > HIGH_FATIGUE_THRESHOLD and not escalated:
        return [
            hold_connective("right_hand"),
            hold_connective("left_hand"),
        ]

    # Rungs 4/5 overlap: drive through the seated grip toward kuzushi.
    drive_mag = DRIVE_MAGNITUDE_N if not escalated else DRIVE_MAGNITUDE_N * 1.3

    # Direction convention: actions carry a force vector in world frame that
    # acts ON THE OPPONENT. PULL draws opponent toward attacker → opp→me;
    # PUSH drives opponent away → me→opp.
    attacker_to_opp = _direction_toward(judoka, opponent)
    pull_dir = (-attacker_to_opp[0], -attacker_to_opp[1])
    push_dir = attacker_to_opp

    primary = deep_enough[0]
    # Secondary action: deepen a shallow grip if any, else push with 2nd hand.
    shallow = [e for e in own_edges if e.depth_level != GripDepth.DEEP
               and e is not primary]
    out = [pull(primary.grasper_part.value, pull_dir, drive_mag)]
    if shallow:
        out.append(deepen(shallow[0]))
    elif len(own_edges) > 1:
        secondary = own_edges[1] if own_edges[0] is primary else own_edges[0]
        out.append(push(secondary.grasper_part.value, push_dir, drive_mag * 0.5))
    return out


# ---------------------------------------------------------------------------
# RUNGS / HELPERS
# ---------------------------------------------------------------------------
def _defensive_fallback(judoka: "Judoka") -> list[Action]:
    # Stunned: minimal-fatigue action.
    return [hold_connective("right_hand"), hold_connective("left_hand")]


def _reach_actions(judoka: "Judoka") -> list[Action]:
    dom = judoka.identity.dominant_side
    is_right = dom == DominantSide.RIGHT
    lapel_target  = GripTarget.LEFT_LAPEL if is_right else GripTarget.RIGHT_LAPEL
    sleeve_target = GripTarget.RIGHT_SLEEVE if is_right else GripTarget.LEFT_SLEEVE
    return [
        reach("right_hand" if is_right else "left_hand", GripTypeV2.LAPEL_HIGH, lapel_target),
        reach("left_hand"  if is_right else "right_hand", GripTypeV2.SLEEVE,     sleeve_target),
    ]


def _try_commit(
    judoka: "Judoka",
    opponent: "Judoka",
    graph: "GripGraph",
    rng: random.Random,
    *,
    offensive_desperation: bool = False,
    defensive_desperation: bool = False,
    kumi_kata_clock: int = 0,
) -> Optional[Action]:
    """If there's a throw whose *perceived* signature clears the commit
    threshold AND the formal grip-presence gate allows it (or is bypassed
    by desperation), return a COMMIT_THROW Action for it. Otherwise None.

    Three commit pathways in priority order (HAJ-49):

      1. Normal signature-clears-threshold commit — the classical path.
      2. Offensive desperation — panicked or imminent-shido (Part 6.3).
      3. Intentional false attack — composed fighter, clock in pre-shido
         zone, picks a drop variant to reset the clock on purpose.

    Normal commit is tried first; desperation is resolved by the
    grip-presence gate inside the main loop (gate bypass is how its bypass
    semantics are wired). The intentional false attack is a separate branch
    consulted only when no normal commit is available AND desperation isn't
    firing.

    The returned Action carries the motivation metadata so Match can
    surface it on the commit log line.
    """
    from perception import actual_signature_match, perceive

    # Try signature throws first, then full vocabulary.
    candidates: list[ThrowID] = list(judoka.capability.signature_throws)
    for t in judoka.capability.throw_vocabulary:
        if t not in candidates:
            candidates.append(t)

    # Rank candidates by perceived signature; we'll walk in descending order
    # and pick the first that clears both the threshold AND the grip gate.
    ranked: list[tuple[float, ThrowID]] = []
    for tid in candidates:
        td = THROW_DEFS.get(tid)
        if td is None:
            continue
        if judoka.capability.throw_profiles.get(tid) is None:
            continue
        actual = actual_signature_match(tid, judoka, opponent, graph)
        perceived = perceive(actual, judoka, rng=rng)
        # Small bonus for signature throws — tokui-waza bias.
        if tid in judoka.capability.signature_throws:
            perceived += 0.05
        ranked.append((perceived, tid))
    ranked.sort(key=lambda pair: pair[0], reverse=True)

    for perceived, tid in ranked:
        if perceived < COMMIT_THRESHOLD:
            break   # ranked descending; nothing below will clear either
        td = THROW_DEFS[tid]
        gate = evaluate_gate(
            judoka, td, graph,
            offensive_desperation=offensive_desperation,
            defensive_desperation=defensive_desperation,
        )
        if not gate.allowed:
            continue   # try the next throw
        return commit_throw(
            tid,
            offensive_desperation=offensive_desperation,
            defensive_desperation=defensive_desperation,
            gate_bypass_reason=gate.reason if gate.bypassed else None,
            gate_bypass_kind=gate.bypass_kind,
        )

    # HAJ-49 — intentional false attack. Falls through only when the normal
    # pathway found nothing committable and offensive desperation isn't
    # firing. The commit resets the kumi-kata clock (in _resolve_commit_throw)
    # and routes to TACTICAL_DROP_RESET on failure — fast recovery, minimal
    # counter exposure. That is the whole point.
    if (not offensive_desperation
            and not defensive_desperation
            and _should_fire_false_attack(judoka, kumi_kata_clock, rng)):
        tid = _select_false_attack_throw(judoka, graph)
        if tid is not None:
            return commit_throw(
                tid,
                intentional_false_attack=True,
                gate_bypass_reason=REASON_INTENTIONAL_FALSE_ATTACK,
                gate_bypass_kind="false_attack",
            )
    return None


# ---------------------------------------------------------------------------
# HAJ-49 — intentional false attack: helpers
# ---------------------------------------------------------------------------
def _should_fire_false_attack(
    judoka: "Judoka", kumi_kata_clock: int,
    rng: Optional[random.Random] = None,
) -> bool:
    """Gate for the intentional-false-attack pathway.

    Four hard gates (all must hold) plus a per-tick probability roll:
      - clock is in the [MIN, MAX) pre-shido zone (18..28 inclusive by default)
      - fighter has fight_iq >= threshold (whites/yellows panic, don't fake)
      - style_dna[false_attack_tendency] >= threshold (tactical disposition —
        French INSEP / modern European competition styles favor this;
        classical Kodokan ura-schools lean less on it)
      - fighter has at least one drop-variant throw in their vocabulary
      - probabilistic firing: per-tick probability = tendency × scale, so
        a high-tendency fighter doesn't fake every eligible tick — they
        pick their moment. This leaves room for offensive desperation to
        fire when the window elapses without a fake.

    `rng` is optional — when None the probability roll is skipped and the
    function returns True whenever the hard gates pass. This keeps unit
    tests deterministic without bolting in a seed.
    """
    if not (FALSE_ATTACK_CLOCK_MIN <= kumi_kata_clock < FALSE_ATTACK_CLOCK_MAX):
        return False
    if judoka.capability.fight_iq < FALSE_ATTACK_MIN_FIGHT_IQ:
        return False
    tendency = judoka.identity.style_dna.get(
        FALSE_ATTACK_TENDENCY_KEY, FALSE_ATTACK_TENDENCY_DEFAULT,
    )
    if tendency < FALSE_ATTACK_TENDENCY_THRESHOLD:
        return False
    if not any(tid in judoka.capability.throw_vocabulary
               for tid in FALSE_ATTACK_PREFERENCES):
        return False
    if rng is None:
        return True
    return rng.random() < tendency * FALSE_ATTACK_PER_TICK_SCALE


def _select_false_attack_throw(
    judoka: "Judoka", graph: "GripGraph",
) -> Optional[ThrowID]:
    """Pick the most-preferred drop variant that's (a) in the fighter's
    vocabulary, (b) has a registered THROW_DEFS entry, and (c) passes
    minimal grip-presence: at least one owned edge exists (the `not
    own_edges` rung 1 check already enforced this upstream, but being
    explicit here keeps the helper self-contained).

    Returns None if no candidate qualifies — caller falls through.
    """
    own_edges = graph.edges_owned_by(judoka.identity.name)
    if not own_edges:
        return None
    for tid in FALSE_ATTACK_PREFERENCES:
        if tid not in judoka.capability.throw_vocabulary:
            continue
        if tid not in THROW_DEFS:
            continue
        return tid
    return None


def _direction_toward(judoka: "Judoka", opponent: "Judoka") -> tuple[float, float]:
    """Unit vector from judoka's CoM toward opponent's CoM, in world frame."""
    ax, ay = judoka.state.body_state.com_position
    bx, by = opponent.state.body_state.com_position
    dx, dy = bx - ax, by - ay
    norm = (dx * dx + dy * dy) ** 0.5
    if norm < 1e-9:
        return (1.0, 0.0)
    return (dx / norm, dy / norm)


def _avg_hand_fatigue(judoka: "Judoka") -> float:
    rh = judoka.state.body.get("right_hand")
    lh = judoka.state.body.get("left_hand")
    if rh is None or lh is None:
        return 0.0
    return 0.5 * (rh.fatigue + lh.fatigue)


def _primary_hand(judoka: "Judoka") -> str:
    return ("right_hand"
            if judoka.identity.dominant_side == DominantSide.RIGHT
            else "left_hand")


def _free_hand(judoka: "Judoka") -> Optional[str]:
    from body_state import ContactState as _CS
    for key in ("right_hand", "left_hand"):
        ps = judoka.state.body.get(key)
        if ps is not None and ps.contact_state != _CS.GRIPPING_UKE:
            return key
    return None
