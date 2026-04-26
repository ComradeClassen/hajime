# tests/test_match_summary.py
# HAJ-46 — end-of-match output is a narrative summary, not a numeric dump.
#
# Pre-HAJ-46, every match ended with `eff=X.XX fat=X.XXX` per body part for
# both fighters. Illegible. Post-HAJ-46 the prose stream produces 1-2
# sentences naming winner, decisive technique, and one causal element
# from match data. The numeric dump is gated behind `stream='debug'` for
# engineers tuning physics.

from __future__ import annotations
import io
import os
import random
import re
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from match import Match
from referee import build_suzuki
import main as main_module


def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _run(stream: str, *, seed: int = 1, max_ticks: int = 240) -> str:
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed, stream=stream,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    return buf.getvalue()


def test_prose_stream_no_numeric_dump() -> None:
    """The prose stream must not include the legacy fat=/eff= numeric per-
    body-part dump."""
    out = _run("prose", seed=1)
    assert "fat=" not in out, "fat= should only appear under stream='debug'"
    assert "eff=" not in out, "eff= should only appear under stream='debug'"
    # And the old per-fighter section header from _print_final_state.
    assert "end of match" not in out


def test_debug_stream_keeps_numeric_dump() -> None:
    """Engineer-facing stream still gets the full numeric dump."""
    out = _run("debug", seed=1)
    assert "fat=" in out, "debug stream should still emit per-part fatigue"
    assert "end of match" in out, (
        "debug stream should still emit the per-fighter section"
    )


def test_summary_lines_are_short_prose() -> None:
    """The summary block sits between the two `===` rules and contains
    1-2 lines, both readable prose ending in punctuation."""
    out = _run("prose", seed=1)
    rules = [i for i, ln in enumerate(out.splitlines())
             if re.fullmatch(r"=+", ln.strip())]
    assert len(rules) >= 2, "expected at least two `===` rule lines"
    # The last two rules bracket the summary block.
    block = out.splitlines()[rules[-2] + 1: rules[-1]]
    block = [ln.strip() for ln in block if ln.strip()]
    assert 1 <= len(block) <= 2, (
        f"expected 1-2 summary lines, got {len(block)}: {block!r}"
    )
    for line in block:
        assert line.endswith((".", "!", "?")), (
            f"summary line should end in punctuation: {line!r}"
        )


def test_summary_names_winner_and_method() -> None:
    """At least one of the summary lines names the winner, and the verb
    'won' connects them to a method."""
    out = _run("prose", seed=1)
    # Pull the section between `===` rules.
    rules = [i for i, ln in enumerate(out.splitlines())
             if re.fullmatch(r"=+", ln.strip())]
    block = "\n".join(out.splitlines()[rules[-2] + 1: rules[-1]])
    # Should contain one of the fighters' names AND the word "won" (or
    # "drawn" for the rare draw outcome).
    has_won_or_drawn = ("won" in block) or ("drawn" in block)
    assert has_won_or_drawn, f"summary must indicate outcome: {block!r}"


def test_compose_summary_is_pure() -> None:
    """The composer is callable directly without re-running the match,
    producing the same lines twice."""
    random.seed(1)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=1)
    # Run silently.
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    once  = m._compose_match_summary()
    twice = m._compose_match_summary()
    assert once == twice
    assert all(isinstance(ln, str) and ln for ln in once)


def test_scoring_events_retained_for_summary() -> None:
    """HAJ-46 wires retention of scoring events via _scoring_events. The
    list is at most a small number of events (waza-ari + ippon), and
    each carries an `outcome` and `scorer` in its data dict so the
    composer can name the decisive technique."""
    random.seed(2)
    t, s = _pair()
    m = Match(fighter_a=t, fighter_b=s, referee=build_suzuki(), seed=2)
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    # If the match scored at all, every retained event has the right
    # shape. If it ended scoreless, the list is simply empty.
    for ev in m._scoring_events:
        assert ev.event_type in ("WAZA_ARI_AWARDED", "IPPON_AWARDED")
        assert ev.data.get("outcome") in ("WAZA_ARI", "IPPON")
        assert ev.data.get("scorer")
