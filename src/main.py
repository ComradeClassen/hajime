# main.py
# Entry point for the Phase 1 skeleton.
# Builds two hand-crafted judoka (Tanaka and Sato), creates a Match, and runs it.
#
# Run from the project root:
#   python src/main.py
#
# Phase 1 success criterion (from data-model.md):
#   - 240 lines of tick output print without error
#   - Both judoka objects look correct at the end (right fatigue values, capability
#     unchanged, archetypes and dominant sides match what we set below)

# --- Import the enums we need to describe each judoka's identity ---
from enums import BodyArchetype, BeltRank, DominantSide

# --- Import throw/combo types for building vocabularies and profiles ---
from throws import (
    ThrowID,              # enum of all available throws
    ComboID,              # enum of all available combos
    JudokaThrowProfile,   # per-judoka, per-throw effectiveness ratings
)

# --- Import the three data layers and the composed Judoka object ---
from judoka import Identity, Capability, State, Judoka

# --- Import the Match runner ---
from match import Match


# ===========================================================================
# BUILD TANAKA
# LEVER archetype. Seoi-nage specialist. Age 26. Right-dominant.
#
# Design notes (from data-model.md):
#   LEVER = uses height, length, leverage. Harai-goshi, uchi-mata, seoi-nage work
#   well for tall fighters who can get under and extend the opponent.
#   Tanaka is the anchoring scene's protagonist — his right side is his weapon.
# ===========================================================================
def build_tanaka() -> Judoka:
    """Construct Tanaka: LEVER archetype, seoi-nage specialist, age 26."""

    # --- IDENTITY LAYER ---
    identity = Identity(
        name="Tanaka",
        age=26,              # Prime for a LEVER — explosive power still high, fight IQ growing
        weight_class="-90kg",
        height_cm=183,       # Tall for -90kg — gives him the reach advantage for seoi-nage entry
        body_archetype=BodyArchetype.LEVER,       # Uses height and length, not cardio volume
        belt_rank=BeltRank.BLACK_1,               # Shodan — 15-22 throw vocabulary ceiling
        dominant_side=DominantSide.RIGHT,         # Attacks from the right side
        personality_facets={
            # 0 = aggressive, 10 = patient — Tanaka is measured, waits for his opening
            "aggressive": 4,
            # 0 = technical, 10 = athletic — Tanaka is a technician
            "technical": 2,
            # 0 = confident, 10 = anxious — high confidence
            "confident": 3,
            # 0 = loyal_to_plan, 10 = improvisational — sticks to the game plan
            "loyal_to_plan": 3,
        },
    )

    # --- CAPABILITY LAYER ---
    capability = Capability(
        # Right side significantly stronger — his seoi-nage lives and dies on right_hand/shoulder.
        # The asymmetry is intentional: this is the 'dominant-side grip system' from the spec.
        right_hand=9,        # Elite grip on the right — his gi grab is nearly unbreakable
        left_hand=6,         # Decent left, but not a weapon
        right_forearm=8,     # Sustained right-side pulling endurance
        left_forearm=6,
        right_bicep=8,       # Strong right pull for throw entry and frame-breaking
        left_bicep=6,
        right_shoulder=9,    # The pivot point for seoi-nage; must be strong
        left_shoulder=7,
        right_leg=8,         # Solid leg drive for seoi-nage lift
        left_leg=7,
        right_foot=8,        # Precise footwork for the seoi entry step
        left_foot=7,
        core=8,              # Rotational power for the shoulder throw; also posture defense
        lower_back=7,        # Lift strength; a seoi-nage puts real load on the lower back
        neck=7,              # Resistance to being bent forward (opponent's favourite counter)

        # LEVER archetype: solid but not exceptional cardio — he wins by technique, not attrition
        cardio_capacity=7,
        cardio_efficiency=7,

        # High fight IQ — he reads openings and grip configurations quickly
        composure_ceiling=8,   # Stays calm; his composure drops more slowly after setbacks
        fight_iq=8,            # Quick to spot the kuzushi window
        ne_waza_skill=5,       # Respectable on the mat, not a specialist

        # Throw vocabulary — 6 throws (BLACK_1 ceiling is 15-22; we hand-build a focused set)
        throw_vocabulary=[
            ThrowID.SEOI_NAGE,    # Signature — his A-game
            ThrowID.HARAI_GOSHI,  # Second signature — hip throw works with his height
            ThrowID.TAI_OTOSHI,   # Body drop — finisher when harai-goshi is read
            ThrowID.O_UCHI_GARI,  # Inner reap — combo opener, sets up seoi entry
            ThrowID.KO_UCHI_GARI, # Minor reap — smaller version; fast setup tool
            ThrowID.O_SOTO_GARI,  # Outer reap — occasional threat from the right side
        ],

        # Per-throw effectiveness profiles (dominant side vs. off-side)
        throw_profiles={
            # Seoi-nage: elite from the right (9), nearly useless from the left (3)
            # — he's a one-sided seoi specialist; this is a real vulnerability
            ThrowID.SEOI_NAGE: JudokaThrowProfile(
                ThrowID.SEOI_NAGE, effectiveness_dominant=9, effectiveness_off_side=3
            ),
            # Harai-goshi: excellent from the right, workable from the left
            ThrowID.HARAI_GOSHI: JudokaThrowProfile(
                ThrowID.HARAI_GOSHI, effectiveness_dominant=7, effectiveness_off_side=4
            ),
            # Tai-otoshi: more symmetric — the entry doesn't require deep hip rotation
            ThrowID.TAI_OTOSHI: JudokaThrowProfile(
                ThrowID.TAI_OTOSHI, effectiveness_dominant=6, effectiveness_off_side=5
            ),
            ThrowID.O_UCHI_GARI: JudokaThrowProfile(
                ThrowID.O_UCHI_GARI, effectiveness_dominant=6, effectiveness_off_side=5
            ),
            # Ko-uchi: low commitment, so side matters less — used as a setup, not a finisher
            ThrowID.KO_UCHI_GARI: JudokaThrowProfile(
                ThrowID.KO_UCHI_GARI, effectiveness_dominant=7, effectiveness_off_side=6
            ),
            ThrowID.O_SOTO_GARI: JudokaThrowProfile(
                ThrowID.O_SOTO_GARI, effectiveness_dominant=5, effectiveness_off_side=4
            ),
        },

        # Signature throws: 2 specialisations — the ones he's truly drilled
        signature_throws=[ThrowID.SEOI_NAGE, ThrowID.HARAI_GOSHI],

        # Signature combos: two chains he can execute with the chain_bonus applied
        signature_combos=[
            ComboID.KO_UCHI_TO_SEOI,      # Ko-uchi reap → seoi-nage — his bread and butter
            ComboID.HARAI_TO_TAI_OTOSHI,  # Harai → tai-otoshi when the hip throw is read
        ],
    )

    # --- STATE LAYER ---
    # Initialize fresh from capability — Tanaka is fully rested, first match of the day.
    # State.fresh() sets all fatigue to 0.0, cardio to 1.0, composure to ceiling (8.0).
    state = State.fresh(capability)

    return Judoka(identity=identity, capability=capability, state=state)


# ===========================================================================
# BUILD SATO
# MOTOR archetype. Uchi-mata specialist. Age 24. Right-dominant.
#
# Design notes:
#   MOTOR = relentless pressure, wears opponents down. Wins by attrition in
#   Round 2. Cardio is the weapon. Sato is physically younger and less
#   technical than Tanaka, but he doesn't need to be — he outlasts you.
# ===========================================================================
def build_sato() -> Judoka:
    """Construct Sato: MOTOR archetype, uchi-mata specialist, age 24."""

    identity = Identity(
        name="Sato",
        age=24,              # Young MOTOR — explosive power near peak, cardio at ceiling
        weight_class="-90kg",
        height_cm=178,       # Slightly shorter than Tanaka; uchi-mata favours good hip drive
        body_archetype=BodyArchetype.MOTOR,
        belt_rank=BeltRank.BLACK_1,
        dominant_side=DominantSide.RIGHT,
        personality_facets={
            "aggressive": 8,     # Very aggressive — he's always attacking
            "technical": 6,      # More athletic than technical
            "confident": 8,      # High confidence, sometimes bordering on reckless
            "loyal_to_plan": 6,  # Slightly improvisational — freelances under pressure
        },
    )

    capability = Capability(
        # Sato's strength is more balanced across the body than Tanaka's.
        # MOTOR fighters need total-body endurance, not one elite weapon.
        right_hand=7,        # Good grip on both sides — symmetry is the point
        left_hand=7,
        right_forearm=8,     # High forearm endurance — he grips constantly and hard
        left_forearm=7,
        right_bicep=7,
        left_bicep=7,
        right_shoulder=7,
        left_shoulder=7,
        right_leg=9,         # Elite leg strength — uchi-mata is a leg-dominant throw
        left_leg=8,          # Both legs strong because MOTOR fighters attack from either leg
        right_foot=7,
        left_foot=7,
        core=9,              # Elite core — rotational power for uchi-mata; posture under pressure
        lower_back=8,        # Strong lower back; MOTOR fighters put their back through sustained load
        neck=7,

        # MOTOR archetype: exceptional cardio — this is the differentiator
        cardio_capacity=9,   # He barely notices fatigue in a 4-minute match
        cardio_efficiency=9, # His cardio drains at roughly half the rate of an average fighter

        composure_ceiling=7,   # Lower than Tanaka — Sato can get rattled
        fight_iq=6,            # Average fight IQ; makes up for it with pressure volume
        ne_waza_skill=6,       # Decent on the mat — opportunistic, not specialist

        throw_vocabulary=[
            ThrowID.UCHI_MATA,    # Signature — his best throw by a wide margin
            ThrowID.O_UCHI_GARI,  # Second signature — feeds the uchi-mata combo
            ThrowID.O_SOTO_GARI,  # Outer reap — complements the inner attacks
            ThrowID.KO_UCHI_GARI, # Setup tool for the O_UCHI_TO_UCHI_MATA combo
            ThrowID.HARAI_GOSHI,  # Hip throw — occasional threat when opponent squares up
            ThrowID.SUMI_GAESHI,  # Sacrifice throw — his mirrored-stance weapon
        ],

        throw_profiles={
            # Uchi-mata: excellent from the right, solid from the left (more two-sided than Tanaka)
            ThrowID.UCHI_MATA: JudokaThrowProfile(
                ThrowID.UCHI_MATA, effectiveness_dominant=9, effectiveness_off_side=5
            ),
            ThrowID.O_UCHI_GARI: JudokaThrowProfile(
                ThrowID.O_UCHI_GARI, effectiveness_dominant=7, effectiveness_off_side=6
            ),
            ThrowID.O_SOTO_GARI: JudokaThrowProfile(
                ThrowID.O_SOTO_GARI, effectiveness_dominant=7, effectiveness_off_side=5
            ),
            ThrowID.KO_UCHI_GARI: JudokaThrowProfile(
                ThrowID.KO_UCHI_GARI, effectiveness_dominant=6, effectiveness_off_side=6
            ),
            ThrowID.HARAI_GOSHI: JudokaThrowProfile(
                ThrowID.HARAI_GOSHI, effectiveness_dominant=6, effectiveness_off_side=4
            ),
            # Sumi-gaeshi: note off-side is *higher* — sacrifice throws work differently
            # in mirrored stances, and Sato has trained this for exactly that scenario
            ThrowID.SUMI_GAESHI: JudokaThrowProfile(
                ThrowID.SUMI_GAESHI, effectiveness_dominant=5, effectiveness_off_side=7
            ),
        },

        signature_throws=[ThrowID.UCHI_MATA, ThrowID.O_UCHI_GARI],
        signature_combos=[
            ComboID.O_UCHI_TO_UCHI_MATA,  # His bread and butter: inner reap → inner thigh sweep
        ],
    )

    state = State.fresh(capability)  # fresh match state — all fatigue 0.0, cardio 1.0

    return Judoka(identity=identity, capability=capability, state=state)


# ===========================================================================
# ENTRY POINT
# Builds both judoka, creates a Match, runs it.
# ===========================================================================
if __name__ == "__main__":
    # Construct both fighters from the hand-built specs above
    tanaka = build_tanaka()
    sato   = build_sato()

    # Create the match — Tanaka is judoka_a (blue), Sato is judoka_b (white)
    match = Match(judoka_a=tanaka, judoka_b=sato)

    # Run the full 240-tick loop, print the result, and verify the final state
    match.run()
