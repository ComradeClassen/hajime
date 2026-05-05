# Master Doc Patch — Ring Reorder and Worldgen Reframe

*Drafted May 4, 2026. Drop into the master doc as a new top-level section
above the existing Ring 1 / Ring 2 / Ring 3 structure, or insert as a
"What changed on May 4, 2026" subsection. The body of the master doc
needs further revision after this lands; this patch captures the
decision while the reasoning is fresh.*

*Applied to the master doc on May 5, 2026 — see `hajime-master-doc.md`.
This file is preserved as the decision-of-record for the May 4 reframe.*

---

## The May 4, 2026 Reframe

Hajime is now a worldgen-first game. Three structural decisions follow.

### 1. The Ring reorder

The previous Ring structure has been reordered to reflect what the game
actually is.

- **Ring 1 — Match Engine.** Unchanged. Calibration-stable, ongoing tuning
  via the Godot calibration tool (HAJ-150). Grip-as-cause refactor shipped.
  This is the deep simulation engine the player watches when they choose to
  watch.

- **Ring 2 — Worldgen and Legends.** *Replaces the previous Ring 2 dojo
  loop.* Multi-decade simulation of New Jersey judo from 1960 forward.
  Includes: abstracted match resolver (lightweight, calibrated against the
  deep engine), procgen sensei and judoka with full lineage data, multi-dojo
  population flow with cross-discipline gravitational pull (BJJ, wrestling,
  boxing), tournament hierarchy from town locals through Olympic
  qualification, technology eras with mechanical effects, rules evolution
  across decades, fog-of-war progression, and the legends-rendering layer
  that produces a browsable history book at handoff. This is the
  *"Legends Mode is the game"* commitment, made structural.

- **Ring 3 — Dojo Deep-Dive.** *Inherits most of the previous Ring 2
  design body.* The within-dojo daily play layer: calendar, sessions,
  conversations, hidden inner lives, lifecycle, antagonist, pricing,
  promotion philosophy, six cultural inputs, attention scarcity at the
  session scale. Sits *inside* the Ring 2 world. The v17 design questions
  body remains valid as Ring 3 work; some answers will need revision once
  the Ring 2 architecture is concrete.

Ring 4 (Adventure Mode) and beyond shift accordingly but their relative
ordering and scope are unchanged.

### 2. The state-modular commitment

Hajime 1.0 ships with New Jersey as the simulated state. Subsequent updates
ship additional states as content expansions: Pennsylvania, California,
Texas, Hawaii, and others as the community requests them. Each state is its
real geography, real population distribution, real martial-arts cultural
profile, and real historical inflection points. The worldgen architecture
is built as a parameterized module from day one so that adding a new state
is content work, not architectural work.

International scope is explicitly out of 1.0. Country-level worldgen
becomes Hajime 2, after the state-modular architecture has been pressure-
tested by however many state additions ship across 1.0's life.

**Save-format default:** states are independent worlds. Adding a new state
in a content update does not affect existing campaigns in other states.
National rankings within each state include plausible representation of
other states as a sparse procgen layer, but those representations do not
link to actual simulations elsewhere. To play another state, the player
starts a new world.

### 3. The fog-of-war progression principle

The Ring 2 worldgen generates the entire world from 1960 to handoff —
every dojo, every notable judoka, every tournament across 70 years. The
player only ever sees the layer their dojo currently touches.

- Compete at town/city level → local landscape unfogs.
- Produce competitors who reach county tournaments → county landscape unfogs.
- Produce a state-level competitor → state landscape unfogs.
- Produce an international competitor → international rankings become
  legible.
- Produce an Olympic qualifier → Olympic-cycle worldgen output becomes
  legible.

The world is fully generated underneath. The player earns access to it
through the actual competitive presence of their dojo. This produces a
progression curve independent of belt-rank-up — the world *literally gets
bigger* as the player's reach extends. It also constrains
legends-rendering authoring effort so it scales with player progression
rather than requiring full polish on day one.

---

## Why this reframe is correct

The Tarn Adams parallel is exact. Dwarf Fortress did not begin as a
worldgen game; it began as a fortress simulator. Worldgen arrived when the
fortress needed a world to exist *in* — somewhere migrants had biographies
before arrival, somewhere historical figures had done things before the
player's clock started, somewhere the goblins came from. The world made
the fortress make sense.

Hajime's dojo loop wants the same scaffolding. A student arriving with a
hidden goal is meaningfully more interesting if the worldgen has rolled
why they have that goal — they trained at a dojo that closed in 2019,
their first sensei was a 1990s national champion, they carry a specific
lineage. The Ring 3 daily play gets its emotional weight from the Ring 2
world the dojo is embedded in. Building the daily play in isolation
produces a competent management sim. Building the world first produces
Hajime.

This reframe also resolves several earlier design tensions in one move:

- The authored opening (basement, twins, Inheritance Event) becomes one
  rolled outcome among many that the worldgen can produce.
- The cartoon antagonist becomes a procgen rival owner whose motivations
  are rolled, not asserted.
- The Q15 lineage data commitment, previously a forward-compatibility hedge
  for Ring 4, now pays for itself in Ring 2 because worldgen needs it.
- The Q16 dojo records system, previously justified by marketing logic,
  gains a real systems reason: it is the legends-mode readout for the
  player's dojo across the worldgen window plus their tenure.
- The six cultural inputs survive but extend their scope. They are not
  only the player's levers — the worldgen senseis accumulate cultural
  decisions too. The cultural feedback loop runs on every dojo in NJ,
  not just the player's.

---

## What this means for current work

**Ring 1 work continues unchanged.** Calibration via the Godot tool, ongoing
tuning, the existing Linear backlog through HAJ-160s. The match engine is
the substrate Ring 2's abstracted resolver will be calibrated against.
Don't pause Ring 1.

**v17 design body parks until Ring 3.** The dojo loop design questions —
calendar, sessions, conversations, lifecycle, antagonist, pricing — remain
valid work but they are no longer the next priority. Some answers will
need to be revised once Ring 2 architecture is concrete (notably: the
antagonist becomes worldgen-generated, not a fixed cartoon character; the
Inheritance Event becomes a worldgen-driven beat rather than a scripted
authored scene). Park the v17 work; do not delete it.

**The next design artifact is Ring 2's full spec.** The
`one-year-of-worldgen.md` draft (May 4, 2026) is the seed. The full spec
extends it with the abstracted resolver's calibration plan, the legends-
rendering authoring strategy, the state-module architecture, the fog-of-war
mechanics, and the technology/rules era handling. This is the next major
design document.

**Cranford JKC anchor preserved.** Whatever else the worldgen produces,
Cranford JKC opens in Cranford in 1962. The sensei is a procgen entity with
attributes that gesture toward the man who shaped this project, but is not
named after him. A more direct homage to Yoshisada Yonezuka — by name, by
dedication, or by other means — remains an open personal decision and is
not committed in this patch.

---

## What this changes about the shipping plan

The 2-3 year EA horizon (mid-2028 to mid-2029) was set against the previous
Ring 2 = dojo loop framing. The new Ring 2 is a substantially larger
subsystem and the shipping plan likely shifts to a 3-4 year horizon.

This is not a regression. The reframe surfaces work that was always going
to be needed for Hajime to be the game it should be. The previous plan
underestimated what was required because it had not yet identified
worldgen as the load-bearing architecture. Now that worldgen is named,
the timeline reflects the real scope. Ship-discipline still applies — the
horizon is longer, not unbounded. The personal checkpoint of January 9,
2027 (working slice that proves the loop is real) remains preserved with
its scope adjusted: by that date the proof should now be a Ring 1 + early
Ring 2 demonstration, not a Ring 1 + early dojo loop.

---

## The tagline this earns

*The legends are the game.*

That sentence belongs on the Steam page when the time comes.

---

*Drafted May 4, 2026, following extended design conversation. Patch
captures decision and immediate implications. Master doc body to be
revised in a follow-up pass. Ring 2 full spec to be drafted from
`one-year-of-worldgen.md` as the seed.*
