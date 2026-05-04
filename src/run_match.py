"""
src/run_match.py

Entry point invoked by the Godot debug calibration tool.
Reads a JSON config, runs the simulation, writes the structured event log.

Place this file at: C:\\Users\\jackc\\hajime\\src\\run_match.py
(alongside judoka.py, match.py, etc. — same directory level)

Usage from command line:
    python C:\\Users\\jackc\\hajime\\src\\run_match.py --config in.json --output out.json

Because this script lives inside src/, when invoked directly the script's
directory is automatically added to sys.path. That means we can import
sibling modules just like the other src/*.py files do:
    # from judoka import Judoka
    # from match import run_match
"""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any


# ----------------------------------------------------------------------
# Stubs — replace these with real imports from the Hajime simulation core
# ----------------------------------------------------------------------
# from hajime.judoka import Judoka
# from hajime.match import run_match
# from hajime.config import build_referee, build_starting_state


def _build_judoka(fighter_config: dict[str, Any]):
    """
    TODO (Comrade): replace this with the real Judoka constructor.

    Take the dict produced by the Godot UI and convert it into whatever
    your existing Python code expects when constructing a fighter.
    The dict has the shape:
        {
          "name": str,
          "age": int,
          "height_cm": int,
          "weight_class": str,
          "body_archetype": str,
          "belt_rank": str,
          "dominant_side": str,
          "personality_facets": {
              "aggressive_patient": float,
              "technical_athletic": float,
              "confident_anxious": float,
              "loyal_improv": float,
          },
          "capability": {
              "hands_left": float, "hands_right": float,
              "forearms_left": float, "forearms_right": float,
              "legs_left": float, "legs_right": float,
              "core": float, "lower_back": float, "neck": float,
              "cardio_capacity": float, "cardio_efficiency": float,
              "fight_iq": float, "composure_ceiling": float,
              "ne_waza_skill": float,
              "other_body_parts_global": float,
          },
        }
    """
    # Placeholder — return the raw dict so the script runs end-to-end
    # before the real wiring is done.
    return fighter_config


def _run_simulation(fighter1, fighter2, match_cfg: dict[str, Any]) -> list[dict]:
    """
    TODO (Comrade): replace this with the real simulation entry point.

    Should return a list of event dicts of the shape:
        {
          "tick": int,
          "type": str,        # e.g. "GRIP_ENGAGE", "THROW_ATTEMPT", "SCORE", ...
          "prose": str,       # human-readable description
          "engineering": dict # optional: structured causal data (see HAJ-148)
        }
    """
    # Placeholder — emit a fake handful of events so the Godot side renders
    # something visible during early integration testing.
    return [
        {
            "tick": 0,
            "type": "MATCH_START",
            "prose": "Stub simulation: %s vs %s" % (
                fighter1.get("name", "Fighter 1"),
                fighter2.get("name", "Fighter 2"),
            ),
        },
        {
            "tick": 30,
            "type": "GRIP_ENGAGE",
            "prose": "Stub: fighters establish initial grip.",
        },
        {
            "tick": 120,
            "type": "THROW_ATTEMPT",
            "prose": "Stub: %s attempts %s." % (
                fighter1.get("name", "Fighter 1"),
                match_cfg.get("forced_throw", "(no forced throw)"),
            ),
        },
        {
            "tick": 240,
            "type": "TIME_EXPIRED",
            "prose": "Stub: clock expired.",
        },
    ]


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Hajime match from a JSON config.")
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
        _write_error_log(args.output, "Simulation crashed:\n" + traceback.format_exc())
        return 2

    try:
        with args.output.open("w", encoding="utf-8") as f:
            json.dump({"events": events}, f, indent=2)
    except Exception as exc:
        sys.stderr.write("Failed to write output: %s\n" % exc)
        return 3

    return 0


def _write_error_log(output_path: Path, message: str) -> None:
    """Write a single-event error log so the Godot side has something to render."""
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(
                {"events": [{"tick": 0, "type": "ERROR", "prose": message}]},
                f,
                indent=2,
            )
    except Exception:
        # If even error logging fails, just print to stderr.
        sys.stderr.write(message + "\n")


if __name__ == "__main__":
    sys.exit(main())
