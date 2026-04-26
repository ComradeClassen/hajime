# dojo-as-institution.md

## Purpose

This doc establishes what a dojo is in HAJIME at the design level. It is the connective tissue between `lineage-system.md`, `cultural-layer.md`, and `career-mode-and-narrative-events.md` — each of those docs assumes a clear answer to what kind of entity is the dojo, and this is where that answer lives.

This is an expansion / unification of the existing `dojo-as-institution.md`, folding in v17 design-questions content. Diff against the existing file before replacing.

This doc commits to several decisions about the dojo's identity, continuity, and material existence. It does not specify mechanics that belong in sibling docs (cultural levers in `cultural-layer.md`, lineage transmission in `lineage-system.md`, run shape in `career-mode-and-narrative-events.md`).

## The dojo as institution

The central commitment: the dojo is an institution, not a place plus a coach plus a roster.

An institution is an entity with identity, history, reputation, material existence, and continuity across the people who pass through it. The dojo has a name. It was founded on a date. It has a public-facing identity in its community. It owns or rents physical assets and carries financial liabilities. It has accumulated history that a new coach inheriting through succession cannot ignore.

This commitment is what makes succession (`career-mode-and-narrative-events.md`) and cross-run persistence (`lineage-system.md`) coherent. If the dojo were just a place plus a coach, succession would be a reset; if the dojo is an institution, succession is a handoff of an entity that already exists.

It is also what makes the cultural feedback loop legible: students don't join a coach, they join a dojo. The dojo's culture is what they sense, what they self-select toward or away from, and what they shape by their presence. The coach is the dominant cultural lever-puller, but the levers belong to the institution.

## Institutional identity

A dojo carries the following identity data:

- **Name.** A specific name (e.g., "Umana Judo," "Newark Judo Academy," "Tokyo Sho Dojo"). Player-set or authored at founding. Persistent.
- **Founding date.** The calendar date the institution opened. Used in dialogue and reputation context ("a young dojo," "an old establishment").
- **Founding lineage.** What lineage the dojo opened with. The institutional version of "what the founder brought into the room." See `lineage-system.md` for lineage as data structure.
- **History.** Accumulated facts the simulation records: notable matches won, students promoted, antagonists faced, succession events, cultural shifts, championships entered. The institution's memory.
- **Public-facing identity.** A short stated description of what the dojo is to outsiders — derived from the Cultural Inputs and history but stable enough that the player can read it. Updates with major changes; doesn't churn on every minor decision.

This identity is data on the dojo, not on the coach. A succession event hands the identity forward unchanged unless the new coach explicitly renames or rebrands.

## The physical layer

The physical layer is a set of constraints, not flavor. It shapes what the institution can be:

- **Space.** Square footage (or abstracted equivalent). Determines maximum mat capacity, simultaneous-class capacity, what session compositions are possible. The basement-dojo opening (Personal Checkpoint, Phase 1) is small — caps at probably 4–6 students on the mat at once. A full dojo is dramatically larger.
- **Equipment.** Mat quality, throw dummies, pull-up bars, video equipment, gi laundry capacity. Constrains session components (some drills require specific equipment) and student perception of seriousness.
- **Capacity.** A maximum roster size that can train without overcrowding. Lower than total enrolled — students rotate through classes — but a hard ceiling on simultaneous bodies.
- **Neighborhood.** The dojo's geographic context. Determines who walks past it, what kinds of students are likely to enroll, what kinds of antagonists exist nearby (rival dojo two blocks away vs. nearest competition fifty miles out). Phase 1 abstracts this to a single "neighborhood character" tag; full implementation is post-Phase-1.

The physical layer is not negotiable in-run except through deliberate expansion (Phase 2 territory). Phase 1's basement opens with a fixed physical configuration. The constraints it produces are real — three classes per week at the basement-dojo's capacity is a real scheduling problem, not a tutorial setting.

## The Six Cultural Inputs as institutional levers

The Six Cultural Inputs (defined in detail in `cultural-layer.md`) are levers on the institution, not on the coach:

- Session content
- Pricing
- Father's-style lineage (the lineage in active use)
- Atmospheric choice
- Promotion philosophy
- Competition readiness pattern

The coach pulls the levers. The institution is what the levers shape. This distinction matters for two reasons:

1. Succession finds the levers where they were left. A new coach inheriting through succession does not start from neutral lever positions — they inherit the previous coach's pulls. To shift the institution's posture, the new coach must actively pull the levers in different directions over time, against the institutional inertia.
2. The institution exhibits posture independent of any single decision. The aggregate of lever positions over time produces a recognizable cultural posture that students sense and respond to. A single session-composition tweak does not change the institution; sustained patterns do.

See `cultural-layer.md` for what each lever does and how the culture vector reads from them.

## Reputation in the community

Reputation is the community's perception of the dojo. It is institutional, not coach-bound, and persistent through succession.

Reputation accumulates from history and culture:

- Match results (wins in tournaments, notable upsets) shape competitive reputation.
- Promotion patterns (do graduates of this dojo go on to teach? to win? to leave the sport?) shape pedagogical reputation.
- Cultural posture (formal? competitive? accessible?) shapes the kinds of students who present at the door.
- Visible failures and successes (a student injured, a championship won, a public falling-out) shape generic perception.

A new coach inheriting the dojo through succession inherits its reputation. If the previous coach built a competition-heavy reputation, students seeking a competition home will continue showing up regardless of the new coach's preferences. Shifting reputation takes deliberate sustained action against existing perception.

Reputation surfaces to the player through: which students walk in the door, what dialogue references the dojo as "that place where ____," and how the antagonist regards the dojo as a threat or non-threat.

## Material economy

The institution has financial existence beyond any coach's tenure:

- **Assets.** Mat space (owned or leased), equipment, inventory (gi sales if any), recorded match footage library, brand value as it exists.
- **Liabilities.** Rent or mortgage, equipment loans, insurance premiums, instructor salaries (if there are assistant coaches paid), debts accrued through difficult periods.
- **Cash position.** The running balance from `HAJ-119` (three-class break-even economy).

These carry through succession unless the new coach explicitly liquidates or restructures. A new coach inheriting a dojo with debt inherits the debt; they don't get a clean balance sheet by virtue of being new. Conversely, a successor inheriting a dojo with strong cash position and good equipment receives that as a head start.

A successor character may also choose to not take over this institution — they may purchase a different dojo (per `career-mode-and-narrative-events.md`'s succession framing), in which case the original institution closes and its material residue is sold off. The lineage transmits; the material institution does not.

## Continuity through succession

Succession events (defined in `career-mode-and-narrative-events.md`) hand the institution forward when the dojo collapses past a threshold and a new player-character takes over. The continuity rules:

**Persists through succession:**

- Institutional identity (name, founding date, founding lineage, history, public-facing identity)
- The lineage, with whatever drift the previous coach produced
- Reputation in the community
- Physical assets (unless explicitly liquidated)
- Liabilities (unless explicitly restructured)
- Rituals (default behavior — see next section)
- Senior students who survived the collapse (with possible attrition)

**Resets / transforms through succession:**

- The active player-character
- Junior students who left during collapse
- Some procedural relationships (the new coach has not yet built rapport)
- The cash balance (may be near-zero post-collapse, depending on collapse type)

If a successor character chooses to purchase a different dojo instead of inheriting this one, the original institution closes and most of the above is lost — only the lineage carries with the character.

## Rituals as institutional memory

Rituals (defined as part of the lineage bundle in `lineage-system.md`) live in the institution, not in the coach. They are how the institution remembers and transmits its character across student generations within a single coach's career, and across coach changes through succession.

Rituals include: how class begins, how class ends, how promotions are conferred, how visitors are received, how mistakes are addressed, how injury is responded to, how the founding lineage is invoked or named.

Default behavior on succession: rituals continue. The new coach steps into the room and finds students already conducting class openings the way they have always been conducted. To change a ritual, the new coach must deliberately break it — and that break is itself a meaningful event in the simulation (often surfaces as a Cultural moment or Antagonist visit trigger).

This default-preserve behavior is what makes "preserve" the natural lineage-drift mode for a successor character. Active drift requires effort; institutional inertia is real.

## Two scales: basement and full dojo

The basement-dojo (Phase 1, Personal Checkpoint) and a full dojo (Phase 2 and beyond) are the same kind of entity at different scales — not different entities.

The basement has:

- Smaller physical footprint, lower capacity, less equipment.
- Smaller roster, fewer simultaneous classes possible.
- Modest reputation by virtue of being new and small (not bad — just unestablished).
- Tight material economy with the three-class break-even pressure.

But it has all the same components: identity, lineage, levers, reputation, assets, rituals. It is a real institution, fully simulated, just constrained. Phase 1's design intent is that the basement feels like a dojo, not like a tutorial scaffolding for a real dojo to come.

The Phase 2 expansion to a larger dojo is a transition between scales — the same institution growing, with reputation, lineage, rituals, history all carrying through. It is not a new dojo. The basement's history is the new dojo's foundation.

## Open questions and handoffs

This doc commits to:

- The dojo as an institution with persistent identity, history, and material existence
- Institutional identity data (name, founding date, founding lineage, history, public-facing identity)
- The physical layer as constraint
- The Six Cultural Inputs as levers on the institution, not on the coach
- Reputation as institutional and persistent
- Material economy with assets and liabilities carrying through succession
- Continuity rules through succession (what persists, what resets)
- Rituals as institutional memory with default-preserve behavior
- Two scales of dojo (basement / full) as the same kind of entity

This doc does not commit to:

- The exact data schema for history, reputation, or public-facing identity strings — implementation territory.
- Reputation calibration (how fast it shifts, how big the inertia is) — calibration territory once playing.
- The mechanics of dojo expansion between scales — Phase 2 design work.
- The market for buying / selling dojos in a successor scenario — defer to Career Mode implementation.
- The visual representation of the dojo — Ring 5 territory.

Sibling design notes that touch this:

- `lineage-system.md` — the dojo is the unit of lineage transmission; rituals live here.
- `cultural-layer.md` — the Six Cultural Inputs aggregate into institutional posture.
- `career-mode-and-narrative-events.md` — succession hands the institution forward; collapse thresholds read against material economy and roster state.
- `physics-substrate.md` — the matches the institution's reputation derives from happen there.

Linear references:

- HAJ-104 — Design question: lifecycle (lifecycle gates fire on student state transitions inside this institution).
- HAJ-109 — Design question: culture & psychology (culture vector aggregates from levers defined here).
- HAJ-110 — Design question: rankings (promotions are institutional acts; promotion philosophy is one of the levers).
- HAJ-111 — Design question: Inheritance Event (closing scene operates on the institution).
- HAJ-113 — Design question: lineage system (resolved by `lineage-system.md`; this doc establishes the institution as transmission unit).
- HAJ-118 — Basement-opening character creation (the basement institution opens here).
- HAJ-119 — Three-class break-even economy (institutional material economy, Phase 1 minimum).
