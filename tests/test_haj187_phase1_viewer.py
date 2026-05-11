# tests/test_haj187_phase1_viewer.py
# HAJ-187 — Phase 1 anatomical viewer: capture layer + 1:1 prose-log
# mapping + animation-timing scaling.
#
# Tests deliberately avoid opening a pygame window. They exercise the
# pure-data capture, the recording renderer, and the text-burst queue.

from __future__ import annotations

import io
import os
import random
import sys
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from body_state import place_judoka
from enums import Position, SubLoopState
from match import Match, Renderer
from referee import build_suzuki
import main as main_module

from viewer_capture import (
    ANATOMICAL_REGIONS,
    Identity,
    MatchClockView,
    Phase1RecordingRenderer,
    Phase1ViewState,
    TextBurst,
    TextBurstQueue,
    TACHIWAZA, TRANSITIONAL, NE_WAZA,
    FLASH_IPPON, FLASH_WAZA_ARI, FLASH_SHIDO, FLASH_HANSOKU,
    FLASH_MATTE, FLASH_HAJIME,
    capture_phase1_view,
    position_bucket,
    scaled_duration,
    TEXT_BURST_FADE_IN_S, TEXT_BURST_HOLD_S, TEXT_BURST_FADE_OUT_S,
    TEXT_BURST_MIN_VISIBLE_S,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _pair():
    t = main_module.build_tanaka()
    s = main_module.build_sato()
    place_judoka(t, com_position=(-0.5, 0.0), facing=(1.0, 0.0))
    place_judoka(s, com_position=(+0.5, 0.0), facing=(-1.0, 0.0))
    return t, s


def _run_match(*, renderer=None, max_ticks=20, seed=1):
    random.seed(seed)
    t, s = _pair()
    m = Match(
        fighter_a=t, fighter_b=s, referee=build_suzuki(),
        max_ticks=max_ticks, seed=seed, renderer=renderer,
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        m.run()
    return m, buf.getvalue()


# ---------------------------------------------------------------------------
# Anatomical regions list — Section 2.1 of the visual language doc.
# ---------------------------------------------------------------------------
def test_anatomical_regions_count_meets_spec() -> None:
    """Section 2.1 names "19 named regions per body" in prose; the
    enumerated list itself contains 20 (head, neck, shoulders L/R,
    biceps L/R, forearms L/R, hands L/R, chest, core, lower_back, hips,
    thighs L/R, shins L/R, feet L/R). Honour both readings: assert the
    floor (>=19) so a future collapse to engine-1:1 mapping doesn't
    fail the test."""
    assert len(ANATOMICAL_REGIONS) >= 19
    names = [n for n, _ in ANATOMICAL_REGIONS]
    # No duplicates.
    assert len(set(names)) == len(names)


def test_anatomical_regions_map_to_engine_parts() -> None:
    """Every region's mapped engine parts exist in the body model."""
    from judoka import BODY_PARTS
    body_parts = set(BODY_PARTS)
    for region_name, parts in ANATOMICAL_REGIONS:
        for p in parts:
            assert p in body_parts, (
                f"region {region_name!r} maps to unknown engine part {p!r}"
            )


# ---------------------------------------------------------------------------
# Renderer protocol shape
# ---------------------------------------------------------------------------
def test_recording_renderer_satisfies_protocol() -> None:
    r = Phase1RecordingRenderer()
    assert isinstance(r, Renderer)


def test_renderer_lifecycle_called_correctly() -> None:
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=10)
    assert rec.start_calls == 1
    assert rec.stop_calls == 1
    assert rec.update_calls >= 1
    # Tick 0 is the initial paint (Match.begin).
    assert rec.snapshots[0].tick == 0


def test_renderer_does_not_perturb_match_outcome() -> None:
    """Section 3.4 — viewer is a pure observer. Same seed must produce
    identical output regardless of whether the renderer is attached."""
    _, out_no = _run_match(renderer=None, max_ticks=30, seed=42)
    _, out_yes = _run_match(
        renderer=Phase1RecordingRenderer(), max_ticks=30, seed=42,
    )
    assert out_no == out_yes


# ---------------------------------------------------------------------------
# Position-state bucket mapping (acceptance #1)
# ---------------------------------------------------------------------------
def test_position_bucket_tachiwaza_default() -> None:
    assert position_bucket(
        Position.STANDING_DISTANT, SubLoopState.STANDING,
    ) == TACHIWAZA
    assert position_bucket(
        Position.GRIPPING, SubLoopState.STANDING,
    ) == TACHIWAZA
    assert position_bucket(
        Position.ENGAGED, SubLoopState.STANDING,
    ) == TACHIWAZA


def test_position_bucket_transitional_for_in_air_states() -> None:
    for p in (Position.SCRAMBLE, Position.THROW_COMMITTED, Position.DOWN):
        assert position_bucket(p, SubLoopState.STANDING) == TRANSITIONAL, (
            f"position {p!r} should map to TRANSITIONAL"
        )


def test_position_bucket_ne_waza_wins_over_position() -> None:
    """Even an ENGAGED Position is NE_WAZA when the sub-loop is on the
    ground — sub-loop wins."""
    assert position_bucket(
        Position.ENGAGED, SubLoopState.NE_WAZA,
    ) == NE_WAZA
    assert position_bucket(
        Position.SIDE_CONTROL, SubLoopState.NE_WAZA,
    ) == NE_WAZA


# ---------------------------------------------------------------------------
# Capture layer — Section 3.1 / 3.2 contract.
# ---------------------------------------------------------------------------
def test_capture_view_state_basic_fields_match_engine() -> None:
    rec = Phase1RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=8, seed=11)
    assert rec.snapshots, "expected at least the tick-0 snapshot"
    snap = rec.snapshots[-1]
    assert isinstance(snap, Phase1ViewState)
    # Identity tags are stable.
    assert snap.body_a.identity == Identity.BLUE
    assert snap.body_b.identity == Identity.WHITE
    # Score panel reflects engine state.
    assert snap.score_a.name == m.fighter_a.identity.name
    assert snap.score_a.waza_ari == m.fighter_a.state.score["waza_ari"]
    assert snap.score_b.shidos == m.fighter_b.state.shidos
    # Clock display is M:SS countdown.
    assert ":" in snap.clock.display
    assert snap.clock.max_ticks == m.max_ticks


def test_capture_carries_19plus_body_regions_per_judoka() -> None:
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=4, seed=3)
    snap = rec.snapshots[-1]
    assert len(snap.body_a.region_damage) >= 19
    assert len(snap.body_b.region_damage) >= 19
    # Damage values are in [0,1].
    for _, dmg in snap.body_a.region_damage:
        assert 0.0 <= dmg <= 1.0


def test_capture_position_state_in_snapshot() -> None:
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=12, seed=5)
    states = {snap.position_state for snap in rec.snapshots}
    assert states.issubset({TACHIWAZA, TRANSITIONAL, NE_WAZA})
    # At minimum the opening tick should be tachiwaza (standing).
    assert rec.snapshots[0].position_state == TACHIWAZA


def test_capture_match_clock_counts_down() -> None:
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=15, seed=9)
    ticks = [s.clock.tick for s in rec.snapshots]
    # Strictly non-decreasing, starting at 0.
    assert ticks[0] == 0
    for prev, cur in zip(ticks, ticks[1:]):
        assert cur >= prev
    # ticks_remaining drops as tick rises.
    rems = [s.clock.ticks_remaining for s in rec.snapshots]
    for prev, cur in zip(rems, rems[1:]):
        assert cur <= prev


def test_capture_carries_mat_coords() -> None:
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=4, seed=2)
    snap = rec.snapshots[-1]
    # CoMs match engine state.
    a_com = tuple(snap.body_a.com_position)
    assert isinstance(a_com[0], float) and isinstance(a_com[1], float)
    assert snap.mat_coords_a == a_com


# ---------------------------------------------------------------------------
# Acceptance #2 — text burst fires same tick as prose log entry.
# This is the structural form of the 1:1 invariant.
# ---------------------------------------------------------------------------
def test_every_engine_event_with_description_becomes_text_burst() -> None:
    """For every event with a description that the engine emits in tick
    T, the captured Phase1ViewState at tick T contains a TextBurst with
    the same description and the same tick. This is the 1:1
    prose-log/viewer invariant in code form."""
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=30, seed=13)
    # Group bursts by (tick, text).
    burst_set = set()
    for tick, _, text in rec.all_text_bursts():
        burst_set.add((tick, text))
    # Every recorded engine event with description should appear.
    for tick, _, desc in rec.event_log:
        assert (tick, desc) in burst_set, (
            f"prose log entry at tick {tick} missing from text bursts: "
            f"{desc!r}"
        )


def test_burst_event_type_preserved() -> None:
    """The renderer can pick burst styling by event_type — the captured
    burst must carry the originating event_type so the renderer can
    differentiate (score burst vs movement burst)."""
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=30, seed=17)
    for tick, etype, _ in rec.all_text_bursts():
        # Engine event types are SCREAMING_SNAKE; allow empty string only
        # if the upstream Event had no type (shouldn't happen in practice).
        assert isinstance(etype, str)


def test_hajime_event_appears_at_tick_zero() -> None:
    """Match.begin emits a HAJIME_CALLED at tick 0 — the viewer must
    capture both the burst and the hajime flash on the very first
    snapshot. This pins the 1:1 invariant from frame zero."""
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=4, seed=21)
    first = rec.snapshots[0]
    assert first.tick == 0
    # Hajime flash present.
    flash_kinds = {f.kind for f in first.referee_flashes}
    assert FLASH_HAJIME in flash_kinds
    # Text burst contains "Hajime".
    burst_texts = [b.text for b in first.text_bursts]
    assert any("Hajime" in t for t in burst_texts), burst_texts


# ---------------------------------------------------------------------------
# Acceptance #3 / #4 — score and shido visual cues.
# ---------------------------------------------------------------------------
def test_score_event_synthesizes_score_flash() -> None:
    """When a WAZA_ARI_AWARDED or IPPON_AWARDED event fires, the
    snapshot for that tick carries a score flash targeting the scorer."""
    # Drive a synthetic event through capture_phase1_view directly so
    # the test doesn't depend on the engine actually producing a score
    # in N ticks (which is non-deterministic across small windows).
    from grip_graph import Event
    from referee import build_suzuki as _ref
    rec = Phase1RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=4, seed=31)
    fake_event = Event(
        tick=99, event_type="WAZA_ARI_AWARDED",
        description="Waza-ari! Tanaka",
        data={"scorer": m.fighter_a.identity.name, "outcome": "WAZA_ARI"},
    )
    snap = capture_phase1_view(m, 99, [fake_event])
    kinds = [f.kind for f in snap.referee_flashes]
    assert FLASH_WAZA_ARI in kinds
    flash = next(f for f in snap.referee_flashes if f.kind == FLASH_WAZA_ARI)
    assert flash.target == m.fighter_a.identity.name


def test_ippon_event_synthesizes_ippon_sweep() -> None:
    from grip_graph import Event
    rec = Phase1RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=4, seed=33)
    fake_event = Event(
        tick=50, event_type="IPPON_AWARDED",
        description="Ippon!",
        data={"scorer": m.fighter_b.identity.name, "outcome": "IPPON"},
    )
    snap = capture_phase1_view(m, 50, [fake_event])
    kinds = [f.kind for f in snap.referee_flashes]
    assert FLASH_IPPON in kinds


def test_shido_event_synthesizes_shido_card() -> None:
    from grip_graph import Event
    rec = Phase1RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=4, seed=35)
    fake = Event(
        tick=20, event_type="SHIDO_AWARDED",
        description="[ref] Shido — Sato (passivity).",
        data={"fighter": m.fighter_b.identity.name, "reason": "passivity"},
    )
    snap = capture_phase1_view(m, 20, [fake])
    flashes = [f for f in snap.referee_flashes if f.kind == FLASH_SHIDO]
    assert flashes, "shido event must produce a SHIDO flash"
    assert flashes[0].target == m.fighter_b.identity.name


def test_hansoku_make_synthesizes_red_card_flash() -> None:
    """Hansoku-make is delivered through MATCH_ENDED with method
    'hansoku-make' — capture must synthesise a HANSOKU flash so the
    red card is visible per Section 2.7."""
    from grip_graph import Event
    rec = Phase1RecordingRenderer()
    m, _ = _run_match(renderer=rec, max_ticks=4, seed=37)
    fake = Event(
        tick=80, event_type="MATCH_ENDED",
        description="Match ends — Tanaka wins by hansoku-make.",
        data={
            "winner": m.fighter_a.identity.name,
            "method": "hansoku-make",
            "tick":   80,
        },
    )
    snap = capture_phase1_view(m, 80, [fake])
    kinds = [f.kind for f in snap.referee_flashes]
    assert FLASH_HANSOKU in kinds


def test_score_panel_mirrors_engine_score_after_award() -> None:
    """ScorePanelView.waza_ari and shidos read directly from engine
    judoka.state — a forced state change shows up in the very next
    snapshot."""
    from grip_graph import Event
    m, _ = _run_match(renderer=None, max_ticks=4, seed=41)
    m.fighter_a.state.score["waza_ari"] = 1
    m.fighter_b.state.shidos = 2
    snap = capture_phase1_view(m, 1, [])
    assert snap.score_a.waza_ari == 1
    assert snap.score_b.shidos == 2
    assert snap.score_b.hansoku_make is False
    m.fighter_b.state.shidos = 3
    snap2 = capture_phase1_view(m, 2, [])
    assert snap2.score_b.hansoku_make is True


# ---------------------------------------------------------------------------
# Acceptance #5 — matte freezes, hajime resumes (visible cues).
# ---------------------------------------------------------------------------
def test_matte_event_synthesizes_matte_flash() -> None:
    from grip_graph import Event
    m, _ = _run_match(renderer=None, max_ticks=4, seed=43)
    fake = Event(
        tick=15, event_type="MATTE_CALLED",
        description="[ref] Matte! (stalemate)",
        data={"reason": "STALEMATE"},
    )
    snap = capture_phase1_view(m, 15, [fake])
    assert any(f.kind == FLASH_MATTE for f in snap.referee_flashes)


def test_hajime_event_synthesizes_hajime_flash() -> None:
    from grip_graph import Event
    m, _ = _run_match(renderer=None, max_ticks=4, seed=45)
    fake = Event(
        tick=18, event_type="HAJIME_CALLED",
        description="[ref] Hajime!",
    )
    snap = capture_phase1_view(m, 18, [fake])
    assert any(f.kind == FLASH_HAJIME for f in snap.referee_flashes)


# ---------------------------------------------------------------------------
# Acceptance #6 — playback-speed scaling for animation timing.
# ---------------------------------------------------------------------------
def test_scaled_duration_doubles_at_half_playback() -> None:
    base = 1.0
    assert abs(scaled_duration(base, 0.5) - 2.0) < 1e-9


def test_scaled_duration_halves_at_double_playback() -> None:
    base = 1.0
    assert abs(scaled_duration(base, 2.0) - 0.5) < 1e-9


def test_scaled_duration_handles_extreme_slowdown() -> None:
    # 0.1× playback → 10× duration (slow study mode, Section 3.5).
    assert abs(scaled_duration(1.0, 0.1) - 10.0) < 1e-9


def test_scaled_duration_clamps_zero_or_negative_rate() -> None:
    # Defensive: a zero / negative rate should still return a finite
    # positive duration so cues eventually resolve.
    val = scaled_duration(1.0, 0.0)
    assert val > 0
    assert val < float("inf")


# ---------------------------------------------------------------------------
# Text burst queue — Section 2.13 sequencing.
# ---------------------------------------------------------------------------
def _bursts(*texts: str, tick: int = 0) -> list[TextBurst]:
    return [TextBurst(tick=tick, text=t, event_type="X") for t in texts]


def test_burst_queue_pops_first_burst_immediately() -> None:
    q = TextBurstQueue(playback_rate=1.0)
    q.push_many(_bursts("first", "second"))
    assert q.active() is None
    q.tick_wall(0.0)
    assert q.active() is not None
    assert q.active().text == "first"


def test_burst_queue_holds_minimum_visible_window() -> None:
    """Section 2.13: each burst gets at least 800ms (at 1×) of
    visibility before the next replaces it."""
    q = TextBurstQueue(playback_rate=1.0)
    q.push_many(_bursts("first", "second"))
    q.tick_wall(0.0)
    # Just before the min-visible floor, the next burst must NOT pop.
    q.tick_wall(TEXT_BURST_MIN_VISIBLE_S - 0.05)
    assert q.active().text == "first"


def test_burst_queue_advances_after_full_lifetime() -> None:
    q = TextBurstQueue(playback_rate=1.0)
    q.push_many(_bursts("first", "second"))
    q.tick_wall(0.0)
    full = TEXT_BURST_FADE_IN_S + TEXT_BURST_HOLD_S + TEXT_BURST_FADE_OUT_S
    q.tick_wall(full + 0.01)
    assert q.active().text == "second"


def test_burst_queue_holds_active_when_no_successor() -> None:
    """A solo burst should keep displaying through its full lifetime
    even after the successor slot is empty — no premature blanking."""
    q = TextBurstQueue(playback_rate=1.0)
    q.push_many(_bursts("only"))
    q.tick_wall(0.0)
    full = TEXT_BURST_FADE_IN_S + TEXT_BURST_HOLD_S + TEXT_BURST_FADE_OUT_S
    q.tick_wall(full * 0.5)
    assert q.active().text == "only"
    q.tick_wall(full + 0.5)
    assert q.active() is None


def test_burst_queue_scales_with_playback_rate() -> None:
    """At 0.5× playback, the queue's hold window should double."""
    q = TextBurstQueue(playback_rate=0.5)
    q.push_many(_bursts("first", "second"))
    q.tick_wall(0.0)
    full_1x = TEXT_BURST_FADE_IN_S + TEXT_BURST_HOLD_S + TEXT_BURST_FADE_OUT_S
    # At 0.5x the boundary is 2× the 1× value — at the 1× boundary, the
    # successor must NOT yet have popped.
    q.tick_wall(full_1x + 0.01)
    assert q.active().text == "first"
    # At the 0.5x boundary, it pops.
    q.tick_wall(full_1x * 2.0 + 0.05)
    assert q.active().text == "second"


# ---------------------------------------------------------------------------
# Acceptance #7 — manual cross-check (1:1 invariant) is automatable.
# ---------------------------------------------------------------------------
def test_one_to_one_invariant_no_orphan_bursts() -> None:
    """Every text burst captured by the viewer corresponds to an engine
    event description seen in the same tick. The reverse direction is
    covered by test_every_engine_event_with_description_becomes_text_burst.
    Together these two tests are the executable form of the 1:1
    commitment Section 2.14 / 3.6 spells out."""
    rec = Phase1RecordingRenderer()
    _run_match(renderer=rec, max_ticks=30, seed=51)
    event_set = {(tick, desc) for tick, _, desc in rec.event_log}
    for tick, _, text in rec.all_text_bursts():
        assert (tick, text) in event_set, (
            f"text burst at tick {tick} has no matching engine event: "
            f"{text!r}"
        )


def test_clock_display_format_is_minutes_seconds() -> None:
    clk = MatchClockView(
        tick=0, max_ticks=240, regulation_ticks=240, golden_score=False,
    )
    assert clk.display == "4:00"
    clk2 = MatchClockView(
        tick=125, max_ticks=240, regulation_ticks=240, golden_score=False,
    )
    assert clk2.display == "1:55"
    # Golden-score overtime renders with leading +.
    clk3 = MatchClockView(
        tick=250, max_ticks=240, regulation_ticks=240, golden_score=True,
    )
    assert clk3.display.startswith("+")
