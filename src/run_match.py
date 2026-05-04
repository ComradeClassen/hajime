"""
src/run_match.py

Entry point invoked by the Godot debug calibration tool (HAJ-150).
Reads a JSON config, runs a real Hajime match, writes the structured event log.

Place this file at: C:\\Users\\jackc\\hajime\\src\\run_match.py
(alongside judoka.py, match.py, etc. — same directory level)

Usage from command line:
    python C:\\Users\\jackc\\hajime\\src\\run_match.py --config in.json --output out.json

Because this script lives inside src/, when invoked directly the script's
directory is automatically added to sys.path. Sibling modules (judoka,
match, referee, etc.) import flat, just like main.py does.

Phase 5 status: real simulation wired through. Forced-throw and
starting-position config fields are accepted but not yet honored (TODO
comments below); everything else flows end-to-end.
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

# Sibling-module imports. Same import style main.py uses.
from enums import (
    BodyArchetype, BeltRank, DominantSide, PositionalStyle,
)
from throws import THROW_REGISTRY
from judoka import Identity, Capability, State, Judoka
from body_state import place_judoka
from match import Match
from referee import Referee


# ----------------------------------------------------------------------
# Config dict shape (produced by calibration_tool.gd)
# ----------------------------------------------------------------------
# {
#   "fighter1": {
#     "name": str, "age": int, "height_cm": int,
#     "weight_class": str, "body_archetype": str, "belt_rank": str,
#     "dominant_side": str,
#     "personality_facets": {
#         "aggressive_patient": float, "technical_athletic": float,
#         "confident_anxious": float,  "loyal_improv": float,
#     },
#     "capability": {
#         "hands_left": float, "hands_right": float,
#         "forearms_left": float, "forearms_right": float,
#         "legs_left": float, "legs_right": float,
#         "core": float, "lower_back": float, "neck": float,
#         "cardio_capacity": float, "cardio_efficiency": float,
#         "fight_iq": float, "composure_ceiling": float,
#         "ne_waza_skill": float,
#         "other_body_parts_global": float,
#     },
#   },
#   "fighter2": { ...same shape... },
#   "match": {
#     "starting_position": str,   # NOT YET WIRED — Match always begins STANDING_DISTANT
#     "time_on_clock": int,
#     "forced_throw": str,        # NOT YET WIRED — see TODO below
#     "ref_personality": str,     # GENEROUS / STRICT / NEUTRAL
#     "seed": int (optional),
#   },
# }
# ----------------------------------------------------------------------


# Godot UI uses bipolar slider labels for personality facets;
# Identity.personality_facets stores them under the shorter "first pole"
# key (per main.py's canonical build_tanaka / build_sato).
_PERSONALITY_KEY_MAP: dict[str, str] = {
    "aggressive_patient": "aggressive",
    "technical_athletic": "technical",
    "confident_anxious":  "confident",
    "loyal_improv":       "loyal_to_plan",
}


# ----------------------------------------------------------------------
# Config -> Judoka
# ----------------------------------------------------------------------
def _build_judoka(fighter_config: dict[str, Any]) -> Judoka:
    """Convert the Godot UI config dict into a real Judoka.

    Mismatches handled here:
      - Godot sends `hands_left` / `hands_right`; Capability uses
        `left_hand` / `right_hand` (and the same for forearms / legs).
      - Godot exposes one `other_body_parts_global` slider; Capability
        requires individual values for biceps, shoulders, feet, plus
        the v0.4 additions (hips, thighs, knees, wrists, head). They
        all read from the global slider so the fighter's overall
        robustness is consistent.
      - Godot sends bipolar facet labels ("aggressive_patient");
        Identity.personality_facets stores them under the first pole
        ("aggressive").
      - Godot sliders are floats 0-10; Capability fields are ints.
        Rounded here.

    Anything not surfaced by the Godot UI uses a sensible default. This
    is a debug tool — full attribute coverage will live in Career Mode.
    """
    # ---- Identity ----
    facets_in = fighter_config.get("personality_facets", {})
    facets = {
        _PERSONALITY_KEY_MAP[k]: int(round(v))
        for k, v in facets_in.items()
        if k in _PERSONALITY_KEY_MAP
    }

    identity = Identity(
        name=fighter_config["name"],
        age=int(fighter_config["age"]),
        weight_class=fighter_config["weight_class"],
        height_cm=int(fighter_config["height_cm"]),
        body_archetype=BodyArchetype[fighter_config["body_archetype"]],
        belt_rank=BeltRank[fighter_config["belt_rank"]],
        dominant_side=DominantSide[fighter_config["dominant_side"]],
        personality_facets=facets,
        # HOLD_CENTER is the safe default for a calibration tool —
        # the locomotion ladder doesn't push or retreat unless we ask
        # it to. Future: surface positional_style on the Godot UI.
        positional_style=PositionalStyle.HOLD_CENTER,
    )

    # ---- Capability ----
    cap_in = fighter_config["capability"]

    def cap(key: str) -> int:
        return int(round(cap_in[key]))

    other = cap("other_body_parts_global")

    capability = Capability(
        # Hands / forearms / legs — explicit Godot keys, side-swapped.
        right_hand=cap("hands_right"),
        left_hand=cap("hands_left"),
        right_forearm=cap("forearms_right"),
        left_forearm=cap("forearms_left"),
        right_leg=cap("legs_right"),
        left_leg=cap("legs_left"),
        # Biceps / shoulders / feet — fanned out from the global slider.
        right_bicep=other, left_bicep=other,
        right_shoulder=other, left_shoulder=other,
        right_foot=other, left_foot=other,
        # Core / lower back / neck — explicit Godot keys.
        core=cap("core"),
        lower_back=cap("lower_back"),
        neck=cap("neck"),
        # Cardio / mind — explicit Godot keys.
        cardio_capacity=cap("cardio_capacity"),
        cardio_efficiency=cap("cardio_efficiency"),
        composure_ceiling=cap("composure_ceiling"),
        fight_iq=cap("fight_iq"),
        ne_waza_skill=cap("ne_waza_skill"),
        # v0.4 body parts — overridden from the global slider so a
        # uniformly-rated fighter actually feels uniform. (Otherwise
        # the dataclass defaults of 5–7 would surface a hidden tilt.)
        head=other,
        right_hip=other, left_hip=other,
        right_thigh=other, left_thigh=other,
        right_knee=other, left_knee=other,
        right_wrist=other, left_wrist=other,
        # Throw vocabulary: every throw in THROW_REGISTRY, no per-throw
        # tuning. The action selector picks throws based on signature
        # match against current grip / posture, so an untuned vocab
        # still produces real throw attempts.
        #
        # TODO Phase 6: when forced_throw is set in match_cfg, restrict
        # signature_throws to that one throw to bias selection toward it.
        throw_vocabulary=list(THROW_REGISTRY.keys()),
        throw_profiles={},
        signature_throws=[],
        signature_combos=[],
    )

    state = State.fresh(capability, identity)
    return Judoka(identity=identity, capability=capability, state=state)


# ----------------------------------------------------------------------
# Config -> Referee
# ----------------------------------------------------------------------
def _build_referee(personality: str) -> Referee:
    """Map the Godot ref_personality string onto Referee's seven 0.0-1.0
    personality knobs. Mirrors the spirit of build_petrov / build_suzuki
    in referee.py.
    """
    if personality == "GENEROUS":
        # Petrov-flavored: long leashes everywhere.
        return Referee(
            name="Generous Ref", nationality="Calibration",
            newaza_patience=0.7, stuffed_throw_tolerance=0.7,
            match_energy_read=0.4, grip_initiative_strictness=0.3,
            ippon_strictness=0.4, waza_ari_strictness=0.4,
            mat_edge_strictness=0.3,
        )
    if personality == "STRICT":
        # Quick whistle on every dimension.
        return Referee(
            name="Strict Ref", nationality="Calibration",
            newaza_patience=0.3, stuffed_throw_tolerance=0.3,
            match_energy_read=0.7, grip_initiative_strictness=0.7,
            ippon_strictness=0.8, waza_ari_strictness=0.7,
            mat_edge_strictness=0.7,
        )
    # NEUTRAL — IJF-default 0.5 baseline on all knobs.
    return Referee(name="Neutral Ref", nationality="Calibration")


# ----------------------------------------------------------------------
# Event capture
# ----------------------------------------------------------------------
class _JSONCaptureRenderer:
    """Push-style Renderer that captures every per-tick events list.

    Match's Renderer Protocol is @runtime_checkable and probes for
    start/update/stop/is_open at runtime — no inheritance needed.
    Match.step() calls update(tick, match, events) after each tick;
    we just collect the events into a flat list.
    """

    def __init__(self) -> None:
        self.events: list = []
        self._open = True

    def start(self) -> None:
        return None

    def update(self, tick: int, match: "Match", events: list) -> None:
        # Match passes the same list it just printed; copy refs out so
        # we don't hold the live tick-buffer (defensive — the list isn't
        # currently mutated post-update, but cheap insurance).
        self.events.extend(events)

    def stop(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open


def _event_to_dict(ev: Any) -> dict[str, Any]:
    """Convert a grip_graph.Event into the JSON shape the Godot side renders.

    Output shape:
        {"tick": int, "type": str, "prose": str, "engineering": dict|Any}
    """
    return {
        "tick": getattr(ev, "tick", 0),
        "type": getattr(ev, "event_type", "UNKNOWN"),
        "prose": getattr(ev, "description", ""),
        "engineering": _sanitize(getattr(ev, "data", {})),
    }


def _sanitize(value: Any) -> Any:
    """Recursively convert a value into JSON-safe primitives.

    Event.data can carry Enums, dataclass instances, tuples, sets — none
    of which json.dump handles natively. Anything non-primitive falls
    back to repr() so the output file stays valid JSON.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize(v) for v in value]
    return repr(value)


# ----------------------------------------------------------------------
# Simulation runner
# ----------------------------------------------------------------------
def _run_simulation(
    fighter1: Judoka, fighter2: Judoka, match_cfg: dict[str, Any],
) -> list[dict]:
    """Run a real Hajime match and return its events as a JSON-safe list."""

    # Place fighters at the canonical match-start dyad — mirrors
    # main.py's _run_one_match. Match.begin() then pushes them out to
    # the wider STANDING_DISTANT pose via _seat_at_distant_pose, which
    # is what produces the closing-phase rendered separation.
    place_judoka(fighter1, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(fighter2, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))

    # TODO Phase 6: starting_position is accepted from the UI but not
    # honored. Match always begins STANDING_DISTANT (HAJ-141). Wiring
    # GROUND_NEUTRAL / GROUND_TOP_FIGHTER1 etc. will require seeding
    # match.position and possibly the OsaekomiClock before run().
    starting_position = match_cfg.get("starting_position", "STANDING_NEUTRAL")
    _ = starting_position  # silence linter; flag in log only when wired

    # TODO Phase 6: forced_throw is accepted but not honored. Cleanest
    # implementation: when forced_throw != "NONE", build the corresponding
    # ThrowID, replace fighter1.capability.signature_throws with [that_id],
    # and bias the action selector via existing signature-throw weighting.
    forced_throw = match_cfg.get("forced_throw", "NONE")
    _ = forced_throw

    referee = _build_referee(match_cfg.get("ref_personality", "NEUTRAL"))
    max_ticks = int(match_cfg.get("time_on_clock", 240))
    seed = match_cfg.get("seed")
    if seed is not None:
        seed = int(seed)

    capture = _JSONCaptureRenderer()

    match = Match(
        fighter_a=fighter1,
        fighter_b=fighter2,
        referee=referee,
        max_ticks=max_ticks,
        seed=seed,
        stream="both",
        renderer=capture,
    )
    match.run()

    return [_event_to_dict(ev) for ev in capture.events]


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a Hajime match from a JSON config."
    )
    parser.add_argument("--config", type=Path, required=True,
                        help="Path to the input config JSON written by the Godot UI.")
    parser.add_argument("--output", type=Path, required=True,
                        help="Path to write the structured event log JSON.")
    args = parser.parse_args(argv)

    try:
        with args.config.open("r", encoding="utf-8-sig") as f:
            config = json.load(f)
    except Exception as exc:
        _write_error_log(args.output, "Failed to read config: %s" % exc)
        return 1

    try:
        fighter1 = _build_judoka(config["fighter1"])
        fighter2 = _build_judoka(config["fighter2"])
        match_cfg = config["match"]
        events = _run_simulation(fighter1, fighter2, match_cfg)
    except Exception:
        _write_error_log(
            args.output,
            "Simulation crashed:\n" + traceback.format_exc(),
        )
        return 2

    try:
        with args.output.open("w", encoding="utf-8") as f:
            json.dump({"events": events}, f, indent=2)
    except Exception as exc:
        sys.stderr.write("Failed to write output: %s\n" % exc)
        return 3

    return 0


def _write_error_log(output_path: Path, message: str) -> None:
    """Write a single-event error log so the Godot side has something
    visible to render when something goes wrong."""
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                {"events": [{"tick": 0, "type": "ERROR", "prose": message}]},
                f,
                indent=2,
            )
    except Exception:
        sys.stderr.write(message + "\n")


if __name__ == "__main__":
    sys.exit(main())
