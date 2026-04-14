# enums.py
# All shared enumerations for the Tachiwaza simulation.
# Keeping enums in one file prevents circular imports — everything else can
# import from here without pulling in the full Judoka or Match machinery.

from enum import Enum, auto  # 'auto()' assigns integer values automatically so we don't hardcode them


# ---------------------------------------------------------------------------
# BODY ARCHETYPES
# Defines the five fighting styles a judoka can embody. This is an Identity-
# layer attribute — it shapes how Capability and State express themselves in
# combat, but it doesn't directly store stats.
# ---------------------------------------------------------------------------
class BodyArchetype(Enum):
    LEVER            = auto()  # Height + leverage; harai-goshi, uchi-mata friendly
    MOTOR            = auto()  # Relentless pressure; wins by attrition
    GRIP_FIGHTER     = auto()  # Controls the grip war before committing to a throw
    GROUND_SPECIALIST = auto() # Average standing, dangerous on the mat
    EXPLOSIVE        = auto()  # Patient build-up then one full-commit ippon attempt


# ---------------------------------------------------------------------------
# BELT RANK
# Determines how large a judoka's throw vocabulary can be.
# White = 3-5 throws; Black 1-2 = 15-22; Black 3+ = 22-30.
# ---------------------------------------------------------------------------
class BeltRank(Enum):
    WHITE   = auto()
    YELLOW  = auto()
    ORANGE  = auto()
    GREEN   = auto()
    BLUE    = auto()
    BROWN   = auto()
    BLACK_1 = auto()  # Shodan
    BLACK_2 = auto()  # Nidan
    BLACK_3 = auto()  # Sandan
    BLACK_4 = auto()  # Yondan
    BLACK_5 = auto()  # Godan


# ---------------------------------------------------------------------------
# DOMINANT SIDE
# Judo is asymmetric. A right-handed (orthodox) judoka drives attacks from
# their right side. This feeds the dominant-side grip system in Capability.
# ---------------------------------------------------------------------------
class DominantSide(Enum):
    RIGHT = auto()  # Orthodox — most judoka
    LEFT  = auto()  # Southpaw — rarer, tactically disruptive


# ---------------------------------------------------------------------------
# POSITION
# Tracks where in the match space the judoka currently is.
# This is a State-layer attribute — it changes every few ticks.
# ---------------------------------------------------------------------------
class Position(Enum):
    STANDING_DISTANT = auto()  # Both fighters separated, no grip yet
    GRIPPING         = auto()  # Grip contact established, no full engagement
    ENGAGED          = auto()  # Close quarters, throw attempts possible
    SCRAMBLE         = auto()  # Chaotic transition after a stuffed throw
    NE_WAZA          = auto()  # Ground work — pins, chokes, armbars
    DOWN             = auto()  # Judoka is on the ground (thrown or fallen)


# ---------------------------------------------------------------------------
# POSTURE
# How upright the judoka is right now. Broken posture is the prerequisite
# for most throws — you need kuzushi (off-balance) before commitment.
# ---------------------------------------------------------------------------
class Posture(Enum):
    UPRIGHT       = auto()  # Neutral, stable base
    SLIGHTLY_BENT = auto()  # Pushed or pulled slightly off-balance
    BROKEN        = auto()  # Kuzushi achieved — vulnerable to throw entry


# ---------------------------------------------------------------------------
# STANCE
# Whether the judoka is fighting orthodox (right foot back) or southpaw
# (left foot back). Can change mid-match via a coach instruction.
# ---------------------------------------------------------------------------
class Stance(Enum):
    ORTHODOX = auto()  # Right-handed lead — standard
    SOUTHPAW = auto()  # Left-handed lead — mirrors the opponent's grip map


# ---------------------------------------------------------------------------
# STANCE MATCHUP
# Describes the relationship between *both* fighters' stances at any moment.
# Mirrored stances (one orthodox, one southpaw) change which throws are
# available and which grips are dominant.
# ---------------------------------------------------------------------------
class StanceMatchup(Enum):
    MATCHED  = auto()  # Both orthodox or both southpaw — standard grip war
    MIRRORED = auto()  # Opposite stances — opens sumi-gaeshi, changes grip map


# ---------------------------------------------------------------------------
# EMOTIONAL STATE
# Carries over between matches in a tournament day (Ring 2+ feature).
# Declared here now so the State data model has the field from day one.
# Not used in Phase 1 — all judoka start each match emotionally neutral.
# ---------------------------------------------------------------------------
class EmotionalState(Enum):
    ELATED   = auto()  # Just won a dominant match — might get reckless
    RELIEVED = auto()  # Scraped through — composure slightly elevated
    DRAINED  = auto()  # Emotional or physical cost was high
    SHAKEN   = auto()  # Lost composure in the last match — carries anxiety
    FOCUSED  = auto()  # Clean mental state entering the next match
