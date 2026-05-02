# narration/altitudes/mat_side.py
# HAJ-144 acceptance #3 — mat-side reader (working altitude).
# HAJ-147 — the editorial layer that produces the match-clock log.
#
# Voice: coach voice — third-person observer, body-part literate, calm,
# technical. Threshold: 1 (everything except true noise; HAJ-144 default).
#
# Implements the five promotion rules (always-promote, modifier extreme,
# contradiction, sample, phase) against the BodyPartEvent + Event streams.
# This is the v0.1 module imported directly by Match._post_tick; the other
# three altitudes (stands / review / broadcast) live alongside it as
# scaffolds for Ring 2 wiring.

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

from body_part_events import (
    BodyPartEvent, BodyPartHigh, BodyPartVerb,
    Crispness, Tightness, Speed, Connection, Timing, Commitment,
    GripIntent, is_self_cancel_pair,
)
from narration.word_verbs import (
    WORD_VERBS, register_for, prose_for_event,
    _target_phrase, _side_phrase,
)
from narration.reader import Reader
from significance import THRESHOLD_MAT_SIDE

if TYPE_CHECKING:
    from match import Match
    from grip_graph import Event


# ---------------------------------------------------------------------------
# MATCH CLOCK ENTRY — one prose line at a given tick.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MatchClockEntry:
    tick:   int
    prose:  str
    source: str
    actors: tuple[str, ...] = ()


# Always-promote engine events — their bare description is already
# coach-voice prose, so the clock log echoes them rather than re-authoring.
_ALWAYS_PROMOTE_EVENT_TYPES: frozenset[str] = frozenset({
    "SCORE_AWARDED", "IPPON_AWARDED", "THROW_LANDING",
    "THROW_ENTRY", "COUNTER_COMMIT", "STUFFED",
    "SUBMISSION_VICTORY", "ESCAPE_SUCCESS", "MATTE",
    "NEWAZA_TRANSITION", "GRIP_STRIPPED", "GRIP_BREAK",
})

# Sample one prose line every N ticks during stable grip-war phases.
_STABLE_SAMPLE_INTERVAL: int = 7


# HAJ-166 — head-as-output substrate (HAJ-146 + HAJ-161) emits one
# HEAD_AS_OUTPUT BPE per fighter under steer. The mat-side prose layer
# renders an outcome-bound line citing the specific collar sub-type and
# the resulting head movement. Below the threshold the steerer's grip
# is poorly seated (force absorbed, posture stiff) — a substitute line
# fires instead. Lapel grips are filtered out at the substrate (HAJ-161
# is_collar() gate), so this template never reaches a non-collar grip.
_HEAD_STEER_GRIP_STRENGTH_THRESHOLD: float = 0.5


# HAJ-162 — the (closing, grip_war) entry is dynamic (resolved by
# `_grip_seating_prose` against engine state) so the line is honest
# about whether one or both fighters actually seated grips on the
# transition tick. The static fallback below is used only when no
# match object is available (e.g., legacy unit-test paths that exercise
# the transition table directly).
_PHASE_TRANSITION_PROSE: dict[tuple[str, str], str] = {
    ("closing", "grip_war"):  "Both fighters lock onto their grips.",
    ("grip_war", "engaged"):  "They close — chest to chest, hands fighting hot.",
    ("engaged", "grip_war"):  "The engagement breaks — back to grip-fighting.",
    ("grip_war", "scramble"): "It collapses into a scramble.",
    ("engaged", "scramble"):  "They tumble into a scramble.",
    ("scramble", "grip_war"): "They reset to their feet, gripping again.",
    ("scramble", "ne_waza"):  "It goes to the ground.",
    ("engaged", "ne_waza"):   "The throw lands — ne-waza opens up.",
    ("grip_war", "ne_waza"):  "It hits the mat — ne-waza is on.",
    ("ne_waza", "closing"):   "Matte — they're back on their feet.",
    ("ne_waza", "grip_war"):  "Matte — back to grips.",
    ("grip_war", "closing"):  "The grips reset — both fighters disengage.",
    ("engaged", "closing"):   "They break apart and reset.",
    ("scramble", "closing"):  "They reset, distance restored.",
    ("ne_waza", "match_over"): "The submission ends it.",
    ("grip_war", "match_over"): "And that's the match.",
    ("engaged", "match_over"):  "And that's the match.",
}


# ---------------------------------------------------------------------------
# HAJ-162 — outcome-bound prose for grip seating
# ---------------------------------------------------------------------------
def _grip_seating_prose(match: "Match") -> str:
    """Resolve the (closing → grip_war) phase-transition line against
    engine state at the transition tick.

    Pre-HAJ-162: the static "Both fighters lock onto their grips" fired
    every time the position transitioned to GRIPPING. After HAJ-151
    grip-initiative variance and HAJ-162 triage stretched the
    leader→follower lag to GRIP_CASCADE_LAG_TICKS=2, only the leader's
    grips have seated on the transition tick — claiming "both" was
    false by one fighter.

    Post-fix: read each fighter's own-grip-edge count and compose:
      - Both gripped → "Both fighters lock onto their grips." (canonical)
      - One gripped  → "{leader} secures the first grip — {follower}
                        reaches but finds nothing."
      - Neither      → fallback to the canonical line (defensive; should
                        not happen because the engine sets GRIPPING
                        position only after at least one grip seats).
    """
    a_name = match.fighter_a.identity.name
    b_name = match.fighter_b.identity.name
    a_owned = match.grip_graph.edges_owned_by(a_name)
    b_owned = match.grip_graph.edges_owned_by(b_name)
    a_has = bool(a_owned)
    b_has = bool(b_owned)
    if a_has and b_has:
        return "Both fighters lock onto their grips."
    if a_has and not b_has:
        return (
            f"{a_name} secures the first grip — "
            f"{b_name} reaches but finds nothing."
        )
    if b_has and not a_has:
        return (
            f"{b_name} secures the first grip — "
            f"{a_name} reaches but finds nothing."
        )
    # Defensive fallback — shouldn't hit unless the engine transitioned
    # to GRIPPING with no edges in the graph (test-only configuration).
    return "Both fighters lock onto their grips."


# ---------------------------------------------------------------------------
# HAJ-166 — outcome-bound prose for collar-grip head-steering
# ---------------------------------------------------------------------------
def _head_steer_prose(match: "Match", victim_name: str) -> Optional[str]:
    """Resolve the head-steer line for `victim_name` against the live
    grip graph. Returns the prose string, or None when no collar grip
    with STEER intent is on the victim (the BPE substrate would have
    suppressed the HEAD_AS_OUTPUT event in that case too — defensive).

    Discrimination:
      - COLLAR_BACK → oku-eri / nape grip; head moves down-and-forward.
      - COLLAR_SIDE → kata-eri / trapezius grip; head turns / chin off.
      - Below the strength threshold → the force is absorbed; substitute
        with a "stays planted" line instead of an effective steer.

    Lapel grips never reach this path because HAJ-161's is_collar()
    filter on `compute_head_state` suppresses the BPE; the narrator's
    detector keys off the HEAD_AS_OUTPUT BPE, so a lapel-only steer
    produces no input here.
    """
    from enums import GripTypeV2
    primary = None
    for edge in match.grip_graph.edges:
        if edge.target_id != victim_name:
            continue
        if edge.current_intent != "STEER":
            continue
        if not edge.grip_type_v2.is_collar():
            continue
        primary = edge
        break
    if primary is None:
        return None
    grasper_name = primary.grasper_id
    effective = primary.strength >= _HEAD_STEER_GRIP_STRENGTH_THRESHOLD
    if not effective:
        # Blocked — force absorbed, posture stiff. Same template across
        # both collar sub-types; the failure mode is the same beat
        # (no head movement).
        side_word = (
            "back collar" if primary.grip_type_v2 is GripTypeV2.COLLAR_BACK
            else "side collar"
        )
        return (
            f"{grasper_name} cranks at the {side_word} — "
            f"{victim_name}'s neck stays planted."
        )
    if primary.grip_type_v2 is GripTypeV2.COLLAR_BACK:
        return (
            f"{grasper_name} pulls {victim_name}'s head down with the "
            f"back collar."
        )
    if primary.grip_type_v2 is GripTypeV2.COLLAR_SIDE:
        return (
            f"{grasper_name} cranks the side collar, turning "
            f"{victim_name}'s chin off-center."
        )
    return None


# ---------------------------------------------------------------------------
# HAJ-165 — movement prose (circling / posture / pull-without-commit)
#
# Three connective-beat families that fill the dead air between grip events
# and throw commits. Each follows the HAJ-162 dynamic-resolver pattern:
# read engine state at emission time, render only what's actually true.
# ---------------------------------------------------------------------------

# Suppress movement prose on ticks that already carry a state-change event
# — those have their own prose lines (always-promote / phase / contradiction)
# and movement beats would just duplicate the slot. THROW_ENTRY is included
# because a commit-tick is precisely when movement prose should defer.
_MOVEMENT_SUPPRESS_EVENT_TYPES: frozenset[str] = frozenset({
    "THROW_ENTRY", "THROW_LANDING", "STUFFED", "FAILED",
    "SCORE_AWARDED", "IPPON_AWARDED", "COUNTER_COMMIT",
    "MATTE", "NEWAZA_TRANSITION",
    "KUZUSHI_INDUCED",
    "GRIP_ESTABLISH",
})


# Per-tactical-intent prose. Keys are the tactical_intent string carried
# on the MOVE event; the resolver picks the line for the actor / opponent
# pair. Intents not listed return None (no movement prose for that step).
def _circling_prose(
    tactical_intent: Optional[str], actor: str, opponent: str,
) -> Optional[str]:
    if tactical_intent is None:
        return None
    if tactical_intent in ("circle", "circle_closing"):
        return f"{actor} circles, looking for an angle on {opponent}."
    if tactical_intent == "lateral_approach":
        return f"{actor} steps wide, working {opponent} into space."
    if tactical_intent == "bait_retreat":
        return f"{actor} steps back, baiting {opponent} forward."
    if tactical_intent in ("closing", "step_in"):
        return f"{actor} closes ground on {opponent}."
    if tactical_intent == "pressure":
        return f"{actor} drives forward, pressing {opponent}."
    if tactical_intent == "give_ground":
        return f"{actor} gives ground, ceding the center."
    if tactical_intent == "gain_angle":
        return f"{actor} works for an angle on {opponent}."
    return None


def _posture_change_prose(
    name: str, old_posture, new_posture,
) -> Optional[str]:
    """Render a one-line beat for a posture transition that didn't go
    through kuzushi. Transitions INTO BROKEN are kuzushi events and own
    their own prose; transitions OUT of BROKEN are recoveries; the
    UPRIGHT ↔ SLIGHTLY_BENT pair is the "settling in / straightening
    up" beat the ticket calls for."""
    from enums import Posture
    if old_posture is new_posture:
        return None
    # BROKEN entry is a kuzushi event — engine emits KUZUSHI_INDUCED on
    # the same tick and that's the prose line. Don't double-author.
    if new_posture is Posture.BROKEN:
        return None
    if old_posture is Posture.BROKEN:
        return f"{name} recovers posture, base re-set."
    if (old_posture is Posture.UPRIGHT
            and new_posture is Posture.SLIGHTLY_BENT):
        return f"{name} bends in, weight rolling onto the front foot."
    if (old_posture is Posture.SLIGHTLY_BENT
            and new_posture is Posture.UPRIGHT):
        return f"{name} straightens up, posture restored."
    return None


def _pull_without_commit_prose(
    actor: str, opponent: str, target: Optional[str],
) -> str:
    """Outcome-bound line for a PULL / REACH BPE that didn't reach the
    commit threshold. The grip referent (sleeve / lapel / collar)
    sharpens the prose; uke 'rides it out' reads the absence of a
    follow-up commit honestly."""
    if target == "SLEEVE":
        return f"{actor} tugs at the sleeve — {opponent} rides it out."
    if target == "LAPEL":
        return (
            f"{actor} hauls on the lapel, but {opponent} stays "
            f"square."
        )
    if target == "COLLAR":
        return (
            f"{actor} hooks the collar and tries to break "
            f"{opponent}'s posture — no give."
        )
    return f"{actor} pulls in but {opponent} absorbs the load."


class MatSideNarrator:
    """Per-match instance held by Match. Filters BPE + Event streams each
    tick and emits MatchClockEntry records. Stateful — tracks last-promoted
    tick, last seen phase, last-sample tick — so promotion rule 4 (sampling)
    and rule 5 (phase transitions) work.
    """

    _RATE_LIMIT_TICKS: int = 6

    def __init__(self) -> None:
        self._last_phase: Optional[str] = None
        self._last_sample_tick: int = -1_000
        self._last_promoted_tick: int = -1
        self._last_actor_source_tick: dict[tuple[str, str], int] = {}
        # HAJ-165 — per-fighter posture tracking. A change between ticks
        # (excluding kuzushi-driven BROKEN entries) drives the posture
        # beat. Initialized to None so the first tick the narrator runs
        # establishes the baseline without firing prose.
        self._last_posture: dict[str, object] = {}

    def consume_tick(
        self, tick: int, events: list, bpes: list[BodyPartEvent],
        match: "Match",
    ) -> list[MatchClockEntry]:
        out: list[MatchClockEntry] = []

        # Rule 5 — phase transition always promotes (run first so the
        # transition line precedes whatever else happened on this tick).
        phase = self._phase_label(match)
        if self._last_phase is not None and phase != self._last_phase:
            transition = (self._last_phase, phase)
            # HAJ-162 — outcome-bound prose for the (closing → grip_war)
            # transition. Reads grip state at the transition tick so the
            # line is honest about which fighters actually seated grips
            # this tick. HAJ-151 / HAJ-161 / HAJ-162 triage stretched the
            # leader→follower lag; on the staging tick only the leader
            # has grips, so "both fighters lock" was false-by-one-fighter.
            if transition == ("closing", "grip_war"):
                prose = _grip_seating_prose(match)
            else:
                prose = _PHASE_TRANSITION_PROSE.get(
                    transition,
                    f"phase shifts: {self._last_phase} → {phase}.",
                )
            out.append(MatchClockEntry(
                tick=tick, prose=prose, source="phase",
            ))
        self._last_phase = phase

        # Rule 1 — always-promote events.
        for ev in events:
            et = ev.event_type
            if et in _ALWAYS_PROMOTE_EVENT_TYPES:
                out.append(MatchClockEntry(
                    tick=tick, prose=ev.description,
                    source=self._source_for(et),
                ))
            # HAJ-144 acceptance #13 — desperation overlay + failed_dimension
            # surface as body-part prose, not enum names. The engine emits
            # OFFENSIVE_DESPERATION_ENTER / DEFENSIVE_DESPERATION_ENTER with
            # a numeric breakdown in description; we re-author them into
            # coach prose that names the body-part feel.
            elif et in (
                "OFFENSIVE_DESPERATION_ENTER",
                "DEFENSIVE_DESPERATION_ENTER",
            ):
                actor = ev.data.get("type", "")
                # The engine description carries the actor name first;
                # extract a coach-voice rewrite that drops the breakdown
                # numerics and keeps the structural cue.
                desc = ev.description
                # Heuristic: pull "{name} enters …" out of the legacy line.
                name = ""
                if "[state] " in desc:
                    rest = desc.split("[state] ", 1)[1]
                    name = rest.split(" enters ", 1)[0]
                if et == "OFFENSIVE_DESPERATION_ENTER":
                    prose = (
                        f"{name}'s posture stiffens — composure leaks "
                        f"as the kumi-kata clock runs hot."
                    )
                else:
                    prose = (
                        f"{name} backs onto the heels — eyes widening, "
                        f"reading the next attack before it lands."
                    )
                out.append(MatchClockEntry(
                    tick=tick, prose=prose,
                    source="desperation",
                    actors=(name,) if name else (),
                ))

        # Rule 3 — contradiction detection.
        out.extend(self._detect_self_cancel(tick, bpes))
        out.extend(self._detect_intent_outcome_mismatch(tick, bpes))

        # Rule 2 — non-default-modifier promotion.
        out.extend(self._promote_modifier_extremes(tick, bpes))

        # HAJ-166 — collar-grip head-steering. Reads HEAD_AS_OUTPUT BPEs
        # and renders an outcome-bound line citing the specific collar
        # sub-type (back vs side) and whether the head actually moved
        # past the grip-strength threshold. Lapel-grip steering is
        # filtered at the substrate (HAJ-161 is_collar() gate) so no
        # HEAD_AS_OUTPUT BPE fires for lapel — the detector naturally
        # respects that.
        out.extend(self._detect_head_steer(tick, bpes, match))

        # HAJ-165 — movement prose. Three connective-beat families that
        # fill the dead air between grip events and throw commits.
        # Posture beats fire on state change (always promote, no rate
        # limit); circling and pull-without-commit beats are sample-
        # rate-limited. All three suppress on ticks that already carry
        # a state-change event (commit / land / kuzushi / matte / score)
        # so they don't double-author the slot.
        suppress_movement = any(
            ev.event_type in _MOVEMENT_SUPPRESS_EVENT_TYPES
            for ev in events
        )
        # Posture state-change is independent of the suppress gate
        # (UPRIGHT ↔ SLIGHTLY_BENT is the same kind of state-change beat
        # the issue calls out); it just declines to fire on KUZUSHI_INDUCED
        # ticks where the engine already authors the BROKEN line.
        out.extend(self._detect_posture_change(tick, events, match))
        if not suppress_movement:
            out.extend(self._detect_circling(tick, events, match))
            out.extend(self._detect_pull_without_commit(tick, bpes, match))

        # Rule 4 — sample.
        if not out and (tick - self._last_sample_tick) >= _STABLE_SAMPLE_INTERVAL:
            sample = self._sample_phase(tick, match, bpes)
            if sample is not None:
                out.append(sample)
                self._last_sample_tick = tick

        if out:
            self._last_promoted_tick = tick
        return out

    def _detect_self_cancel(
        self, tick: int, bpes: list[BodyPartEvent],
    ) -> list[MatchClockEntry]:
        out: list[MatchClockEntry] = []
        by_actor: dict[str, list[BodyPartEvent]] = {}
        for b in bpes:
            if b.tick != tick:
                continue
            by_actor.setdefault(b.actor, []).append(b)
        for actor, evs in by_actor.items():
            pulls = [e for e in evs
                     if e.verb in (BodyPartVerb.PULL, BodyPartVerb.PUSH)
                     and e.direction is not None]
            steps = [e for e in evs
                     if e.part is BodyPartHigh.FEET
                     and e.verb is BodyPartVerb.STEP
                     and e.direction is not None]
            disconnected = any(
                e.modifiers.connection is Connection.DISCONNECTED
                for e in evs
            )
            for pull in pulls:
                for step in steps:
                    if not is_self_cancel_pair(pull, step):
                        continue
                    if not disconnected:
                        continue
                    out.append(MatchClockEntry(
                        tick=tick,
                        prose=(
                            f"{actor}'s pull dies in the sleeve as he "
                            f"steps in over his own feet."
                        ),
                        source="self_cancel",
                        actors=(actor,),
                    ))
                    return out
        return out

    def _detect_intent_outcome_mismatch(
        self, tick: int, bpes: list[BodyPartEvent],
    ) -> list[MatchClockEntry]:
        out: list[MatchClockEntry] = []
        seen_actors: set[str] = set()
        for b in bpes:
            if b.tick != tick:
                continue
            if b.intent is GripIntent.BREAK and b.verb is BodyPartVerb.SNAP:
                if b.actor in seen_actors:
                    continue
                if not self._rate_check(b.actor, "intent_mismatch", tick):
                    continue
                seen_actors.add(b.actor)
                tgt = _target_phrase(b.target).lstrip()
                out.append(MatchClockEntry(
                    tick=tick,
                    prose=(
                        f"{b.actor} tries to rip {tgt} but can't budge it."
                    ),
                    source="intent_mismatch",
                    actors=(b.actor,),
                ))
        return out

    def _detect_head_steer(
        self, tick: int, bpes: list[BodyPartEvent], match: "Match",
    ) -> list[MatchClockEntry]:
        """HAJ-166 — render a single outcome-bound head-steer line per
        victim per tick (rate-limited). Fires off HEAD_AS_OUTPUT BPEs
        so the narration follows the substrate; the live grip graph
        supplies the collar sub-type and effectiveness."""
        out: list[MatchClockEntry] = []
        seen_victims: set[str] = set()
        for b in bpes:
            if b.tick != tick:
                continue
            if b.source != "HEAD_AS_OUTPUT":
                continue
            if b.actor in seen_victims:
                continue
            if not self._rate_check(b.actor, "head_steer", tick):
                continue
            prose = _head_steer_prose(match, b.actor)
            if prose is None:
                continue
            seen_victims.add(b.actor)
            out.append(MatchClockEntry(
                tick=tick, prose=prose,
                source="head_steer",
                actors=(b.actor,),
            ))
        return out

    def _detect_circling(
        self, tick: int, events: list, match: "Match",
    ) -> list[MatchClockEntry]:
        """HAJ-165 — read MOVE engine events with a tactical_intent
        label and render at most one circling beat per actor per tick,
        rate-limited through _rate_check (default 6-tick window). The
        prose cites the actual locomotion intent so the line matches
        the geometry. Only fires while the dyad is mid-fight (gripping
        / engaged / standing-distant) — ne-waza has its own substrate."""
        from enums import SubLoopState, Position
        if match.sub_loop_state == SubLoopState.NE_WAZA:
            return []
        if match.position not in (
            Position.GRIPPING, Position.ENGAGED, Position.STANDING_DISTANT,
        ):
            return []
        out: list[MatchClockEntry] = []
        seen_actors: set[str] = set()
        for ev in events:
            if ev.event_type != "MOVE":
                continue
            actor = ev.data.get("fighter")
            if not actor or actor in seen_actors:
                continue
            opponent = self._opponent_of(actor, match)
            if opponent is None:
                continue
            tactical = ev.data.get("tactical_intent")
            prose = _circling_prose(tactical, actor, opponent)
            if prose is None:
                continue
            if not self._rate_check(actor, "circling", tick):
                continue
            seen_actors.add(actor)
            out.append(MatchClockEntry(
                tick=tick, prose=prose,
                source="circling",
                actors=(actor,),
            ))
        return out

    def _detect_posture_change(
        self, tick: int, events: list, match: "Match",
    ) -> list[MatchClockEntry]:
        """HAJ-165 — fire a single line per fighter whose discrete
        posture (UPRIGHT / SLIGHTLY_BENT / BROKEN) changed since the
        last tick. Transitions INTO BROKEN are owned by KUZUSHI_INDUCED
        prose; transitions OUT of BROKEN are recoveries. Always
        promotes on state change (no rate limit) per AC#4."""
        from body_state import derive_posture
        # Defensive — legacy unit-test stubs don't always carry fighter
        # references. Skip silently in that case so the existing test
        # surface (e.g. desperation-prose stub matches) isn't broken.
        fighter_a = getattr(match, "fighter_a", None)
        fighter_b = getattr(match, "fighter_b", None)
        if fighter_a is None or fighter_b is None:
            return []
        # KUZUSHI_INDUCED ticks belong to the engine's kuzushi prose; a
        # posture beat would just paraphrase the same beat.
        if any(ev.event_type == "KUZUSHI_INDUCED" for ev in events):
            for fighter in (fighter_a, fighter_b):
                bs = fighter.state.body_state
                self._last_posture[fighter.identity.name] = derive_posture(
                    bs.trunk_sagittal, bs.trunk_frontal,
                )
            return []
        out: list[MatchClockEntry] = []
        for fighter in (fighter_a, fighter_b):
            name = fighter.identity.name
            bs = fighter.state.body_state
            current = derive_posture(bs.trunk_sagittal, bs.trunk_frontal)
            previous = self._last_posture.get(name)
            self._last_posture[name] = current
            if previous is None:
                continue  # baseline tick; no prose
            prose = _posture_change_prose(name, previous, current)
            if prose is None:
                continue
            out.append(MatchClockEntry(
                tick=tick, prose=prose,
                source="posture",
                actors=(name,),
            ))
        return out

    def _detect_pull_without_commit(
        self, tick: int, bpes: list[BodyPartEvent], match: "Match",
    ) -> list[MatchClockEntry]:
        """HAJ-165 — render a connective beat when a PULL BPE fires
        this tick without the actor being mid-commit. The suppression
        gate at the call site already handles THROW_ENTRY ticks; this
        detector additionally checks _throws_in_progress so a multi-
        tick attempt that started earlier doesn't get described as
        'no commit' just because THROW_ENTRY isn't on this tick.
        Rate-limited through _rate_check.
        REACH BPEs are excluded — REACH is "extending the hand toward
        a grip target," fired before any edge exists. The "hauls on
        the lapel" / "tugs at the sleeve" prose family describes
        force through a live grip, so emitting it for REACH produces
        false copy ('Renard hauls on the lapel' before contact, with
        no lapel grip seated). Only PULL (which requires an existing
        edge) drives this template.
        """
        out: list[MatchClockEntry] = []
        seen_actors: set[str] = set()
        in_progress = set(getattr(match, "_throws_in_progress", {}).keys())
        for b in bpes:
            if b.tick != tick:
                continue
            if b.source != "PULL":
                continue
            actor = b.actor
            if actor in seen_actors or actor in in_progress:
                continue
            opponent = self._opponent_of(actor, match)
            if opponent is None:
                continue
            if not self._rate_check(actor, "pull_no_commit", tick):
                continue
            target = b.target.name if b.target is not None else None
            seen_actors.add(actor)
            out.append(MatchClockEntry(
                tick=tick,
                prose=_pull_without_commit_prose(actor, opponent, target),
                source="pull_no_commit",
                actors=(actor,),
            ))
        return out

    def _opponent_of(self, actor: str, match: "Match") -> Optional[str]:
        fighter_a = getattr(match, "fighter_a", None)
        fighter_b = getattr(match, "fighter_b", None)
        if fighter_a is None or fighter_b is None:
            return None
        a = fighter_a.identity.name
        b = fighter_b.identity.name
        if actor == a:
            return b
        if actor == b:
            return a
        return None

    def _rate_check(self, actor: str, source: str, tick: int) -> bool:
        key = (actor, source)
        last = self._last_actor_source_tick.get(key, -10_000)
        if tick - last < self._RATE_LIMIT_TICKS:
            return False
        self._last_actor_source_tick[key] = tick
        return True

    def _promote_modifier_extremes(
        self, tick: int, bpes: list[BodyPartEvent],
    ) -> list[MatchClockEntry]:
        out: list[MatchClockEntry] = []
        seen_actors: set[str] = set()
        for b in bpes:
            if b.tick != tick:
                continue
            # HAJ-154 — commit-source BPEs no longer drive modifier-reveal
            # prose. The modifier-reveal text reads as an outcome claim
            # ("X's commit lands crisp and explosive"), but on the commit
            # tick the throw hasn't resolved yet — five out of six
            # instances in the audit log made factually wrong claims
            # (the throw failed). HAJ-148 AC3 requires no prose to
            # co-occur with a commit event tag; this is the prose source
            # that violated it. COUNTER_COMMIT BPEs still surface — a
            # counter is itself a resolution event.
            if b.source != "COUNTER_COMMIT":
                continue
            if b.actor in seen_actors:
                continue
            m = b.modifiers
            extreme = (
                m.crispness is Crispness.CRISP
                or m.crispness is Crispness.SLOPPY
                or m.speed is Speed.EXPLOSIVE
                or m.tightness is Tightness.FLARING
                or m.timing is Timing.LATE
                or m.timing is Timing.EARLY
                or m.commitment is Commitment.OVERCOMMITTED
            )
            if not extreme:
                continue
            if not self._rate_check(b.actor, "skill_reveal", tick):
                continue
            seen_actors.add(b.actor)
            out.append(MatchClockEntry(
                tick=tick,
                prose=self._modifier_reveal_prose(b),
                source="skill_reveal",
                actors=(b.actor,),
            ))
        return out

    def _modifier_reveal_prose(self, b: BodyPartEvent) -> str:
        m = b.modifiers
        if m.crispness is Crispness.CRISP and m.speed is Speed.EXPLOSIVE:
            return f"{b.actor}'s commit lands crisp and explosive."
        if m.crispness is Crispness.CRISP:
            return f"{b.actor}'s commit reads clean and on-time."
        if m.crispness is Crispness.SLOPPY:
            return f"{b.actor}'s commit comes apart at the seams."
        if m.tightness is Tightness.FLARING:
            return f"{b.actor}'s elbow flares — power leaks out the side."
        if m.timing is Timing.LATE:
            return f"{b.actor} commits late — uke has already moved."
        if m.timing is Timing.EARLY:
            return f"{b.actor} commits early — the kuzushi hasn't stacked."
        if m.commitment is Commitment.OVERCOMMITTED:
            return f"{b.actor} throws himself at it — no recovery if it misses."
        if m.speed is Speed.SLOW:
            return f"{b.actor}'s commit is slow and telegraphed."
        return prose_for_event(b)

    def _sample_phase(
        self, tick: int, match: "Match", bpes: list[BodyPartEvent],
    ) -> Optional[MatchClockEntry]:
        head_evs = [b for b in bpes
                    if b.tick == tick and b.part is BodyPartHigh.HEAD]
        if head_evs:
            h = head_evs[0]
            verb_word = WORD_VERBS.get(
                h.verb, {"mid": h.verb.name.lower()}
            ).get(register_for(h), h.verb.name.lower())
            return MatchClockEntry(
                tick=tick,
                prose=f"{h.actor}'s head {verb_word}.",
                source="sample",
                actors=(h.actor,),
            )
        return None

    def _phase_label(self, match: "Match") -> str:
        from enums import SubLoopState, Position
        if match.match_over:
            return "match_over"
        if match.sub_loop_state == SubLoopState.NE_WAZA:
            return "ne_waza"
        if match.position == Position.STANDING_DISTANT:
            return "closing"
        if match.position == Position.GRIPPING:
            return "grip_war"
        if match.position == Position.ENGAGED:
            return "engaged"
        if match.position == Position.SCRAMBLE:
            return "scramble"
        return "standing"

    def _source_for(self, event_type: str) -> str:
        if event_type in ("THROW_ENTRY", "THROW_LANDING", "STUFFED"):
            return "throw"
        if event_type == "COUNTER_COMMIT":
            return "counter"
        if event_type in ("SCORE_AWARDED", "IPPON_AWARDED"):
            return "score"
        if event_type == "MATTE":
            return "matte"
        if event_type in ("SUBMISSION_VICTORY", "ESCAPE_SUCCESS",
                          "NEWAZA_TRANSITION"):
            return "newaza"
        if event_type in ("GRIP_STRIPPED", "GRIP_BREAK"):
            return "grip_kill"
        return "phase"


# ---------------------------------------------------------------------------
# Reader factory — independent (threshold, voice) construction (acceptance #4).
# This wraps MatSideNarrator's per-event voice into the generic Reader
# interface so test_threshold_voice_independence can swap voices freely.
# ---------------------------------------------------------------------------
def _mat_side_voice(
    event: "Event", bpes: list[BodyPartEvent], match: "Match",
) -> Optional[str]:
    """Per-event mat-side voice (coach register). Stateless wrapper —
    most prose composition happens in MatSideNarrator's tick-level
    pipeline; this adapter renders one event at a time when callers
    want the Reader interface instead. Returns None for events the
    mat-side voice doesn't speak (debug-only and below threshold)."""
    if event.event_type in _ALWAYS_PROMOTE_EVENT_TYPES:
        return event.description
    return None


def build_mat_side_reader(threshold: int = THRESHOLD_MAT_SIDE) -> Reader:
    """v0.1 mat-side reader: coach voice + everything-above-noise threshold.
    Caller can override threshold for testing decoupling."""
    return Reader(
        threshold=threshold,
        voice=_mat_side_voice,
        name="mat_side",
    )
