# match.py
# The Match class and its 240-tick loop.
#
# Phase 1 goal: prove the architecture compiles and classes compose correctly.
# The tick loop is a placeholder — it prints events and accumulates fatigue,
# but has no real combat logic yet. Real throws, grip graphs, and Mate
# detection all come in Phase 2.

from dataclasses import dataclass, field  # dataclass for Match; field for mutable defaults
from judoka import Judoka                 # the composed three-layer fighter object


# ---------------------------------------------------------------------------
# PLACEHOLDER EVENT STRINGS
# A short cycling list of canned event descriptions. Each tick picks one by
# index (tick % len) so the output isn't 240 identical lines.
# Phase 2 replaces this entirely with real combat events and prose templates.
# ---------------------------------------------------------------------------
PLACEHOLDER_EVENTS: list[str] = [
    "grip exchange - no commitment",
    "{a} probes for collar grip",
    "{b} pulls - {a}'s grip holds",
    "grip battle - both forearms engaged",
    "{a} breaks {b}'s posture forward",
    "{b} resets - both fighters separate briefly",
    "{a} steps in - {b} squares up",
    "stalemate at center - referee watching",
]
# {a} and {b} are format placeholders filled in at runtime with the fighters' names


# ---------------------------------------------------------------------------
# FATIGUE CONSTANTS
# How much fatigue accumulates per tick on each tracked body part.
# These are placeholder values for Phase 1 — calibration happens in Phase 5
# once we can watch many simulated matches and see if the numbers feel right.
#
# The spec notes: hands fatigue under grip resistance; cardio is a slow drain.
# ---------------------------------------------------------------------------
HAND_FATIGUE_PER_TICK: float  = 0.002   # Each hand loses ~0.002 per tick
                                         # Over 240 ticks: right_hand fatigue peaks at 0.48
CARDIO_DRAIN_PER_TICK: float  = 0.003   # Cardio depletes ~0.003 per tick
                                         # Over 240 ticks: cardio drops to ~0.28 (physically hard match)


# ===========================================================================
# MATCH
# Contains two Judoka objects and runs the simulation loop.
# Phase 1: prints placeholder events, accumulates fatigue, declares a winner.
# Phase 2: adds the grip state graph, throw success rolls, and Mate detection.
# ===========================================================================
@dataclass
class Match:
    """Runs a single judo match between two judoka across a tick-based loop.

    Phase 1: placeholder events only. Architecture proof — not combat logic.
    The tick loop lives here; the Judoka objects are passed in from main.py.
    """
    judoka_a: Judoka  # Fighter assigned to the blue (ao) side
    judoka_b: Judoka  # Fighter assigned to the white (shiro) side
    total_ticks: int = 240  # 240 ticks = 4 minutes at 1 tick per second (IJF senior match)

    def run(self) -> None:
        """Entry point. Prints the header, runs the tick loop, resolves the match."""
        self._print_header()
        self._run_tick_loop()
        self._resolve_match()

    # -----------------------------------------------------------------------
    # HEADER
    # -----------------------------------------------------------------------
    def _print_header(self) -> None:
        """Print a match header so we know who is fighting before the log starts."""
        a = self.judoka_a.identity  # shorthand — we only need the Identity layer here
        b = self.judoka_b.identity
        print()
        print("=" * 56)
        print(f"  MATCH: {a.name} (blue) vs {b.name} (white)")
        # Print archetype and dominant side so we can verify the data composed correctly
        print(f"  {a.name}: {a.body_archetype.name}, {a.dominant_side.name}-dominant, age {a.age}")
        print(f"  {b.name}: {b.body_archetype.name}, {b.dominant_side.name}-dominant, age {b.age}")
        print("=" * 56)
        print()

    # -----------------------------------------------------------------------
    # TICK LOOP
    # The heart of Phase 1. Runs for self.total_ticks iterations.
    # Each tick:
    #   1. Picks a placeholder event string and prints it.
    #   2. Accumulates fatigue on right_hand, left_hand, and cardio for both fighters.
    # Phase 2 will replace step 1 with real combat state transitions.
    # -----------------------------------------------------------------------
    def _run_tick_loop(self) -> None:
        """Iterate through all 240 ticks, printing events and updating fatigue."""
        a_name = self.judoka_a.identity.name  # cache names to avoid repeated attribute lookups
        b_name = self.judoka_b.identity.name

        for tick in range(1, self.total_ticks + 1):

            # --- Pick the placeholder event for this tick ---
            # tick % len wraps around the list so we cycle through all 8 strings
            template = PLACEHOLDER_EVENTS[tick % len(PLACEHOLDER_EVENTS)]
            # Fill in fighter names for events that reference {a} or {b}
            event = template.format(a=a_name, b=b_name)

            # Print the tick line — format tick number to 3 digits so columns stay aligned
            print(f"tick {tick:03d}: {event}")

            # --- Update fatigue for both fighters ---
            # We call the same helper for both so the logic stays in one place.
            self._accumulate_fatigue(self.judoka_a)
            self._accumulate_fatigue(self.judoka_b)

    # -----------------------------------------------------------------------
    # FATIGUE ACCUMULATION
    # Updates State for the tracked body parts each tick.
    # min/max guards prevent fatigue from going below 0 or above 1.
    # -----------------------------------------------------------------------
    def _accumulate_fatigue(self, judoka: Judoka) -> None:
        """Add one tick's worth of fatigue to right_hand, left_hand, and cardio."""
        state = judoka.state  # shorthand — we're writing to State layer only

        # --- Hands ---
        # Grip resistance is constant during a live match — both hands fatigue continuously.
        # min(1.0, ...) caps fatigue at fully cooked so it can't go above 1.0
        state.body["right_hand"].fatigue = min(
            1.0,
            state.body["right_hand"].fatigue + HAND_FATIGUE_PER_TICK,
        )
        state.body["left_hand"].fatigue = min(
            1.0,
            state.body["left_hand"].fatigue + HAND_FATIGUE_PER_TICK,
        )

        # --- Cardio ---
        # Cardio drains from 1.0 downward — max(0.0, ...) floors it at empty.
        # Note: cardio drains slightly faster per tick than hands fatigue, because
        # sustained cardiovascular output is the first thing to show in a real match.
        state.cardio_current = max(
            0.0,
            state.cardio_current - CARDIO_DRAIN_PER_TICK,
        )

    # -----------------------------------------------------------------------
    # MATCH RESOLUTION (PLACEHOLDER)
    # In Phase 1, Tanaka always wins by ippon. This is hardcoded purely to
    # prove that the Match class can produce a result and print it.
    # Phase 2 replaces this with real scoring from the combat logic.
    # -----------------------------------------------------------------------
    def _resolve_match(self) -> None:
        """Declare the match winner and print final state for architecture verification."""
        # Hardcoded: judoka_a wins. Phase 2 will derive the winner from the score dict.
        winner  = self.judoka_a
        loser   = self.judoka_b

        print()
        print("=" * 56)
        print(f"  MATCH OVER - {winner.identity.name} wins by ippon (placeholder)")
        print("=" * 56)

        # Print final state for both fighters so we can visually verify:
        #   - fatigue accumulated at expected rates
        #   - capability values are unchanged (State should never write back to Capability)
        #   - archetype and dominant side are what we set in main.py
        self._print_final_state(self.judoka_a)
        self._print_final_state(self.judoka_b)

    def _print_final_state(self, judoka: Judoka) -> None:
        """Print a readable summary of one judoka's end-of-match state.

        This is the Phase 1 'architecture verification' output — confirms all
        three layers composed correctly and the tick loop wrote to State properly.
        """
        ident = judoka.identity
        cap   = judoka.capability
        state = judoka.state

        print()
        print(f"  {ident.name} - end of match")
        print(f"    archetype:          {ident.body_archetype.name}")
        print(f"    dominant_side:      {ident.dominant_side.name}")
        print(f"    age:                {ident.age}")

        # Show a few capability values to confirm they were NOT modified during the match
        print(f"    cap right_hand:     {cap.right_hand}  (unchanged - capability is not modified during match)")
        print(f"    cap cardio_cap:     {cap.cardio_capacity}  (unchanged)")

        # Show the State values that the tick loop DID modify
        print(f"    state right_hand fatigue:  {state.body['right_hand'].fatigue:.3f}  (accumulated over {self.total_ticks} ticks)")
        print(f"    state left_hand fatigue:   {state.body['left_hand'].fatigue:.3f}")
        print(f"    state cardio_current:      {state.cardio_current:.3f}  (drained from 1.0)")

        # Show effective right_hand — demonstrates all three layers interacting
        effective_rh = judoka.effective_body_part("right_hand")
        print(f"    effective right_hand now:  {effective_rh:.3f}  (cap * age_mod * (1 - fatigue))")

        # Signature throws — pull display names from the global registry to confirm
        # the throw vocabulary composed correctly during judoka construction.
        from throws import THROW_REGISTRY  # local import to avoid circular dependency risk at module level
        sig_display = [THROW_REGISTRY[t].name for t in cap.signature_throws]
        print(f"    signature throws:   {', '.join(sig_display)}")
