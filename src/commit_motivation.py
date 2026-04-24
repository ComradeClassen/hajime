# commit_motivation.py
# HAJ-67 — non-scoring attack motivations as a first-class typed concept.
#
# Extends the HAJ-49 / HAJ-50 "intentional false attack" pathway (a single
# bool flag) into four distinct motivations, each with its own trigger
# conditions, per-tick probability, and prose narration template. All four
# route to the same TACTICAL_DROP_RESET compromised state (HAJ-50) — the
# referee's shido evaluation operates on the commit itself, not the
# motivation. A motivation is a label on tori's internal decision; the mat
# state after the fake is identical regardless.
#
# The four motivations:
#   - CLOCK_RESET         — reset the kumi-kata passivity clock (HAJ-49)
#   - GRIP_ESCAPE         — break contact when the grip war is lost
#   - SHIDO_FARMING       — pressure a passive opponent into a shido
#   - STAMINA_DESPERATION — cooked fighter forces something to happen
#
# What lives here:
#   - CommitMotivation enum (the four values)
#   - DEBUG_TAGS        — short snake-case name for the engineer log line
#   - COMPACT_NARRATION — prose templates per motivation for the failure line
#
# Trigger logic (which motivation fires when) lives in action_selection.py.
# Failure-outcome routing lives in match.py + failure_resolution.py.

from __future__ import annotations
from enum import Enum, auto


class CommitMotivation(Enum):
    """Non-scoring attack motivations (HAJ-67).

    Mutually exclusive — a commit carries at most one motivation label. A
    throw commit with no motivation is either a normal signature-clears-
    threshold commit or an offensive-desperation commit (which is already
    flagged on the Action via `offensive_desperation` and `gate_bypass_*`).
    """
    CLOCK_RESET         = auto()  # reset kumi-kata passivity (HAJ-49 legacy)
    GRIP_ESCAPE         = auto()  # grip war is lost, break contact
    SHIDO_FARMING       = auto()  # exploit opponent's passivity clock
    STAMINA_DESPERATION = auto()  # cooked; forcing anything to happen


# ---------------------------------------------------------------------------
# DEBUG TAGS — surfaced on the THROW_ENTRY commit line via the existing
# tag-suffix pipeline. Short snake-case so downstream parsers can match on
# the literal.
# ---------------------------------------------------------------------------
DEBUG_TAGS: dict[CommitMotivation, str] = {
    CommitMotivation.CLOCK_RESET:         "clock_reset",
    CommitMotivation.GRIP_ESCAPE:         "grip_escape",
    CommitMotivation.SHIDO_FARMING:       "shido_farming",
    CommitMotivation.STAMINA_DESPERATION: "stamina_desperation",
}


# ---------------------------------------------------------------------------
# COMPACT NARRATION — failure-line prose per motivation.
# One short two-beat line each. The register deliberately *slides past* the
# reader the way uke's reading should slide past tori's fake. These replace
# the generic `(tag; recovery N tick(s))` line that other failure outcomes
# produce — see match._format_failure_events.
#
# Each template is a format string with `{tori}` and `{throw}` placeholders.
# ---------------------------------------------------------------------------
COMPACT_NARRATION: dict[CommitMotivation, str] = {
    CommitMotivation.CLOCK_RESET:
        "[throw] {tori} drops on {throw}. Nothing there. Back up.",
    CommitMotivation.GRIP_ESCAPE:
        "[throw] {tori} breaks contact with a half-{throw}. Grips reset.",
    CommitMotivation.SHIDO_FARMING:
        "[throw] {tori} poses an attack — {throw}. Kept moving; clock ticks.",
    CommitMotivation.STAMINA_DESPERATION:
        "[throw] {tori} falls into {throw}. Out of gas, out of options.",
}


def narration_for(motivation: CommitMotivation, tori: str, throw: str) -> str:
    """Render the compact failure-line prose for a motivation."""
    template = COMPACT_NARRATION[motivation]
    return template.format(tori=tori, throw=throw)


def debug_tag_for(motivation: CommitMotivation) -> str:
    """Short snake-case tag for the THROW_ENTRY log line's tag suffix."""
    return DEBUG_TAGS[motivation]
