# HAJIME — Master Design & Development Document

> *Renamed from Tachiwaza on April 16, 2026. The title* Hajime *refers to the
> referee's call that starts every match — the game is everything that happens
> before Hajime is set, and everything that happens after. As of April 23, 2026,
> the title was also doing a second, structural job: the game is what happens
> when you start your dojo. The match is one of many things that happens inside
> the world the call opens. As of May 4, 2026, the title takes on a third
> meaning. The dojo is itself one of many things that happens inside the world
> the call opens — a world that is now generated, simulated, and remembered
> across decades before the player ever walks onto the mat. Hajime is the
> moment a single match begins, the moment a single dojo opens, and the
> moment seventy years of judo history finishes settling into a world the
> player can step into.*

### A Living Brainstorm / Build Roadmap / Reference

*This document is a working artifact. Update it after every session.*

---

## THE MAY 4, 2026 WORLDGEN REFRAME

*Drafted from `master-doc-patch-2026-05-04.md` and `one-year-of-worldgen.md`,
both produced May 4, 2026 in an extended worldgen-pivot conversation.
Supersedes the April 23 dojo-loop reshape as the load-bearing architectural
commitment of the project.*

**Hajime is now a worldgen-first game.** The dojo loop is not the bottom
layer; the world the dojo lives inside is. Three structural decisions follow
from this — a ring reorder, a state-modular commitment, and a fog-of-war
progression principle. Together they reshape the entire build plan and make
visible work that was always going to be needed for Hajime to be the game it
should be.

### The tagline this earns

> *The legends are the game.*

That sentence belongs on the Steam page when the time comes. Everything below
is the architecture that makes it true.

### 1. The ring reorder

The previous Ring 2 (Dojo Loop) is no longer Ring 2. It is Ring 3. A new
Ring 2 sits beneath it — multi-decade worldgen of a real martial-arts
ecosystem (New Jersey from 1960 forward, in 1.0). The dojo deep-dive is now
the *daily play layer inside* a world that already exists, has already
produced legends, and continues producing them around the player throughout
the campaign. Full ring inventory in *The Simulation Rings* below.

The Tarn Adams parallel is exact. Dwarf Fortress did not begin as a worldgen
game; it began as a fortress simulator. Worldgen arrived when the fortress
needed a world to exist *in* — somewhere migrants had biographies before
arrival, somewhere historical figures had done things before the player's
clock started, somewhere the goblins came from. The world made the fortress
make sense.

Hajime's dojo loop wants the same scaffolding. A student arriving with a
hidden goal is meaningfully more interesting if worldgen has rolled *why*
they have that goal — they trained at a dojo that closed in 2019, their
first sensei was a 1990s national champion, they carry a specific lineage.
The Ring 3 daily play gets its emotional weight from the Ring 2 world the
dojo is embedded in. Building daily play in isolation produces a competent
management sim. Building the world first produces Hajime.

The reframe also resolves several earlier design tensions in one move:

- The authored opening (basement, twins, Inheritance Event) becomes one
  rolled outcome among many that worldgen can produce, with the basement-
  from-zero path preserved as the tutorial / first-run anchor.
- The cartoon antagonist becomes a procgen rival owner whose motivations are
  rolled, not asserted.
- The Q15 lineage data commitment, previously a forward-compatibility hedge
  for the old Ring 4, now pays for itself in Ring 2 because worldgen needs it.
- The Q16 dojo records system, previously justified by marketing logic,
  gains a real systems reason: it is the legends-mode readout for the
  player's dojo across the worldgen window plus their tenure.
- The six cultural inputs survive but extend their scope. They are not only
  the player's levers — worldgen senseis accumulate cultural decisions too.
  The cultural feedback loop runs on every dojo in NJ, not just the player's.

### 2. The state-modular commitment

Hajime 1.0 ships with **New Jersey** as the simulated state. Subsequent updates
ship additional states as content expansions — Pennsylvania, California,
Texas, Hawaii, and others as the community asks for them. Each state is its
real geography, real population distribution, real martial-arts cultural
profile, and real historical inflection points. The worldgen architecture is
built as a parameterized module from day one so that adding a new state is
content work, not architectural work.

International scope is explicitly out of 1.0. Country-level worldgen becomes
**Hajime 2**, after the state-modular architecture has been pressure-tested
by however many state additions ship across 1.0's life.

**Save-format default:** states are independent worlds. Adding a new state
in a content update does not affect existing campaigns in other states.
National rankings within each state include plausible representation of
other states as a sparse procgen layer, but those representations do not
link to actual simulations elsewhere. To play another state, the player
starts a new world.

### 3. The fog-of-war progression principle

Ring 2 worldgen generates the entire world from 1960 to handoff — every
dojo, every notable judoka, every tournament across roughly 70 years. The
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
bigger* as the player's reach extends. It also constrains legends-rendering
authoring effort so it scales with player progression rather than requiring
full polish on day one.

### Cranford JKC anchor

Whatever else worldgen produces, in 1962 a judo dojo opens in Cranford, NJ.
The sensei's attributes are rolled. The signature style is rolled. The
trajectory across decades is rolled. But the fact of Cranford JKC's 1962
founding in Cranford is fixed. Worldgen never overwrites this. If procgen
would have placed a different dojo in Cranford in 1959, it doesn't —
Cranford is reserved. If procgen would have closed Cranford JKC in 1985, it
doesn't — Cranford persists.

This is the game's personal anchor. It costs nothing mechanically and gives
every campaign a shared reference point that ties the procedural to the
personal. A more direct homage to Yoshisada Yonezuka — by name, by
dedication, or by other means — remains an open personal decision and is
not committed in this section.

---

## THE PRIORITY DECISION — UPDATED MAY 4, 2026

**Hajime is the primary creative project. Player Two remains paused. The
horizon is now 3–4 years to Early Access — not 2–3, and certainly not nine
months. January 9, 2027 is preserved as a personal checkpoint, not a ship
date, with its scope adjusted for the worldgen reframe.**

This is the third iteration of the priority decision. The first (April 15,
2026) prioritized Hajime over Player Two on a January 9, 2027 ship
assumption. The second (April 23) extended to a 2–3 year horizon after the
v17 reshape revealed the dojo loop was the actual game. The third (May 4)
extends again to 3–4 years after the worldgen reframe revealed that the
dojo loop is itself a layer inside a multi-decade simulated world.

This is not a regression. The reframe surfaces work that was always going
to be needed for Hajime to be the game it should be. The previous plan
underestimated what was required because it had not yet identified worldgen
as the load-bearing architecture. Now that worldgen is named, the timeline
reflects the real scope. Ship-discipline still applies — the horizon is
longer, not unbounded.

The shape:

1. **Hajime continues to be the primary project.** The April 15
   prioritization stands. Player Two remains paused.

2. **The horizon extends to 3–4 years.** Realistic Early Access is mid-2029
   to mid-2030. This is consistent with what an ambitious solo dev project
   of this scope actually takes once worldgen is included. (Reference points:
   Wildermyth was ~6 years to 1.0 with a small team; Dwarf Fortress is its
   own thing; Football Manager has 30 years of iteration behind it; CK3
   shipped after CK2's decade of iteration. Hajime is more modest in scope
   than any of these but is still a serious multi-year build.)

3. **January 9, 2027 — Personal Checkpoint, scope adjusted.** Not a ship
   date. The internal target remains *further than where I began*. Under
   the worldgen reframe, the proof by Comrade's birthday in 2027 should be
   a Ring 1 + early Ring 2 demonstration: a calibrated match engine, a
   worldgen v0 that produces a browsable proto-history of NJ judo from 1960
   to present with Cranford JKC's 1962 opening anchored, and a sketch of
   the Ring 3 dojo deep-dive sitting on top. Not a working basement-opening
   campaign yet. Not public, not for sale. A working slice of the game's
   *substrate* that proves the world is real. Birthday gift to self from a
   more capable builder.

4. **Player Two architecture continues to be built earlier than planned.**
   The v17 dojo-loop reshape committed Hajime to building Player Two's
   psychology layer (immediate needs + long-term goals + emergent goal
   evolution) as the student inner-lives mechanic in the dojo deep-dive.
   The relational/lineage data model is similarly Player-Two-shaped, and
   becomes more load-bearing under worldgen — every entity in the simulated
   state carries lineage from day one. By the time Player Two resumes,
   those architectures will already exist as working code at scale. See
   *Relationship to Player Two* below.

5. **The decision protects future-Comrade from second-guessing.** When a
   weak moment arrives in November 2026 or July 2027 or January 2028 and
   the temptation is to feel behind schedule — the answer is here. Each
   reshape made the schedule longer because each reshape made the game
   bigger and more itself. Build at the right pace.

---

## THE CORE LOOP

*Updated May 4, 2026. The April 13 framing put the match at center; the
v17 reshape put the dojo at center; the May 4 reframe puts the world at
center, with the dojo and the match nested inside.*

A world has already happened. New Jersey judo from 1960 forward — sixty-
some years of senseis opening dojos, students arriving and leaving,
tournaments producing winners, lineages branching, BJJ and wrestling and
boxing pulling on the population, rules changing, technology changing,
legends settling into a history book the player can browse. Cranford JKC
opened in 1962. Some of the senseis in the current worldgen output trained
under senseis who trained under senseis going back to that opening.

Then you start a dojo. (Or inherit one. Or buy one out. Or take over an
established dojo with an Olympian on the roster — depending on which
opening the campaign rolls.) You set the weekly calendar — which sessions
run, when, and what each one contains. Procedurally generated students
walk in at various levels of commitment, carrying lineages that connect
back into the worldgen history: some try a free week and disappear, some
plateau at yellow or green belt and stay for years, a few become champions.
Inside each session you choose where to spend your attention — watching one
randori match while four others run unwatched, or pulling a student aside
for a conversation that begins to reveal who they are. Your students have
inner lives — needs and goals — that you only learn about by spending time
on them. The dojo's culture emerges from your accumulated choices. The
dojo's reputation shapes who walks through the door next, drawn from the
world's ongoing population flow. And every so often, a tournament arrives,
and you sit in the chair beside the mat for the same Matte windows you
used to think the game was about. The competitor across the mat from your
student trained at a dojo that has been in the worldgen for thirty years
under a sensei whose own teacher you read about in last week's idle scroll
through the history book.

That's the loop. Three nested layers. The match engine that Ring 1 has
been building is still real and still load-bearing — but it lives inside
the dojo loop, which lives inside the world. Most of a campaign is the
dojo deep-dive. The matches are the consequential events the dojo produces.
And the world is the substrate that gives every dojo and every match its
meaning.

---

## THE FIVE THESIS-LEVEL DESIGN PRINCIPLES

*Originally added April 23, 2026 around the v17 dojo-loop reshape. The May 4
worldgen reframe extends each principle's scope rather than replacing them.
Every system in the game still traces back to at least one of these.*

### 1. Attention scarcity at every scale

The single most important mechanic. Originally identified as the Tournament
Attention Economy (three fighters, one chair); the v17 reshape generalized
it to every scale of the dojo loop. The May 4 reframe extends it to the
world layer: there are dozens of dojos in NJ at any given era, hundreds of
notable judoka the player could investigate, decades of history the player
could read — and the player only has time for what's adjacent to where
their dojo currently competes. Fog-of-war progression is attention scarcity
at the world scale.

Same primitive, four scales now: match (one chair, three fighters), session
(one watched pair, four unwatched), week (three conversations, fifteen
students), career (one campaign, dozens of takeable openings, hundreds of
worldgen-generated lives the player will never read).

This is what makes coaching feel like coaching at every depth.

### 2. The cultural feedback loop

Your accumulated choices produce a dojo with a character — chill,
fun-for-kids, companion-oriented, trial-by-fire. The character is
emergent, not authored. The character then shapes who walks in.

Under the May 4 reframe, the cultural feedback loop is no longer a
single-dojo phenomenon. It runs on every dojo in NJ. Worldgen senseis
accumulate session-content patterns, pricing patterns, promotion
philosophies, and the same feedback dynamic produces the variety of dojos
the player encounters in the world. A 1980s Newark dojo with a hard-randori
culture has that culture because some 1970s sensei made a sequence of
choices the worldgen recorded. The player's dojo is one feedback loop
among many running in parallel.

This means there is still no neutral move. Every decision is cultural
input. The six primary cultural inputs are listed in their own section
below — they are now both *the player's levers* and *worldgen's levers*.

### 3. Continuous simulation, render on demand

Football Manager architecture, now with two simulation layers. The match
engine (Ring 1) is the deep simulation; the abstracted match resolver
(Ring 2's load-bearing technical commitment) is the lightweight simulation
worldgen runs across decades. Both produce judo; the deep engine produces
the textured kind the player watches, the resolver produces the
statistical kind that fills the chronicles.

The deep engine activates only when the player watches — randori in their
own dojo, or a tournament their own student is competing in. Every other
match in the world stays in the resolver. This is the same technique CK3
uses for off-screen battles and DF uses for off-screen historical combat.

Hajime's match engine already IS the hour-by-hour zoom. The new work
includes the abstracted resolver (calibrated against the deep engine), the
calendar UI, the time-scaling controls, the aggregated-naturalistic-
simulation for zoomed-out views, and the event-pause infrastructure.

### 4. Compositional emergence

The big legible thing is built from small invisible events. A student's
"grip" stat at the top of the roster is emergent from thousands of atomic
exchanges in randori. A dojo's culture is emergent from accumulated
session content + pricing + promotion decisions. A match's meaning is
emergent from per-tick force application and posture state. A worldgen
legend is emergent from sixty-six iterations of a one-year worldgen
simulation, most of whose ticks fade into silence and a small fraction of
which become remembered. The 1974 Yamada upset means something because it
sits in a year that has only twenty-eight other entries in the chronicle.

This is now the fourth system to express this pattern (Ring 1 physics;
cultural feedback; student stats; worldgen legends). It's worth naming.
It's what makes the simulation feel authentic — no number on the screen
is a lie, because every number traces back to events.

### 5. Either choice is okay

Major narrative events present binding decisions with no morally graded
answers. The game does not reward "correct" choices or penalize "wrong"
ones — it produces a *different* story from each choice. Inheritance
Event: stay with basement, take father's dojo (where, under the worldgen
reframe, "father's dojo" is a worldgen-generated mid-tier dojo with rolled
cultural baggage and a rolled retiring sensei). Succession at retirement:
blood child, top student. Push the reluctant fighter to compete, or honor
their wishes. Both paths are legitimate.

Disco Elysium / Citizen Sleeper / Wildermyth territory. Choices carry
weight because they reshape the story, not because they're evaluated.

---

## THE THREE ANCHORING SCENES

*The game must be able to produce these three scenes. If the systems can
produce them, the systems are right. If they can't, something is wrong.
Updated May 4, 2026 to reflect that the dojo arc scenes now sit inside the
basement-opening tutorial path; other openings produce different first-
month and long-arc scenes that are equally valid but not load-bearing for
the architecture.*

The three scenes form an arc — match-level inside the loop, opening of the
basement-dojo tutorial arc, closing of the basement-dojo tutorial arc.
Together they prove the architecture. Other arcs (inheriting a mid-tier
dojo from a worldgen-retiring sensei, buying out a struggling existing
dojo with reputation baggage, taking over an established dojo with an
Olympian on the roster) produce different first-month and long-term
scenes; the architecture must support those too, but the basement-arc
scenes are the named proof points.

### The Match Anchoring Scene — Tanaka vs. Sato

Existing scene. Still load-bearing. Drives Ring 1.

```
Round 1 · 0:00 — Tanaka (blue) vs. Sato (white)

0:03  Tanaka steps in. Right hand reaches for the lapel.
0:04  Sato's left hand intercepts — pistol grip on the sleeve.
0:06  Tanaka pulls — Sato's grip holds. Right grip strength -1.
0:09  Tanaka secures high collar. Deep grip.
0:11  Sato breaks posture forward, framing the bicep.
0:14  Grip battle. Both hands engaged. Tanaka's forearms fatiguing.
0:18  Tanaka attempts seoi-nage —
       → Sato sprawls. Hips back. Throw stuffed.
       → Slight scramble. Sato briefly exposes back.
       → ne-waza window: 11% — Tanaka does not commit.
       → Both stand. Grips reset.
0:22  Sato attacks o-uchi-gari — Tanaka's left leg absorbs.
0:24  Matte.
```

**[ Match paused — coach's chair ]**

```
TANAKA          status
─────────────────────────
Composure       7/10  ↓ (-1 from stuffed throw)
Right grip      5/10  ↓↓ (fatigued)
Left grip       8/10
Legs            8/10
Read speed      6/10
Trust in coach  9/10  ← high. He'll listen.

Height advantage over Sato: +5cm  ← moment arm favors seoi entry
Hip height differential: neutral  ← neither fighter has leverage edge yet

GRIP STATE (visible at coach IQ 7+):
  Tanaka R.hand →→ DEEP COLLAR →→ Sato L.lapel  (depth: 0.8) ✓
  Tanaka L.hand →→ SLEEVE GRIP →→ Sato R.sleeve (depth: 0.5) ⚠️ fatiguing
  Sato R.hand   →→ STANDARD    →→ Tanaka L.lapel (depth: 0.4)
  Sato L.hand   →→ PISTOL      →→ Tanaka R.sleeve (depth: 0.7) ← controlling

What you saw: He went for his strongest throw too early.
Sato read it. The grip fight is going against him on the right side.

→ Choose 2 instructions (max):

  A. Switch stance. Attack the left side.
  B. Break his grip first. Don't engage until you have yours.
  C. Stay patient. Let him come to you.
  D. Go to the ground if he opens up again.
  E. Tighten up. He's reading you.
  F. [Write your own — short phrase]
```

This is the Ring 1 north star. Everything in the match engine — grip graph,
position state machine, throw resolution, referee personality, the Matte
window — exists to make this scene work and to make matches like it emerge
from any pair of fighters, including the pairs worldgen produces decades
before the player walks in.

### The Opening Anchoring Scene — The Twins Arrive (basement-opening path)

Within the first month of a new basement dojo. Two boys walk in together —
twin brothers, maybe twelve, excited in a way that can't be faked. They
saw the small directory plate by the basement door and the family name on
it, and they ran home and asked their father, and their father said *yes,
that's the son. His father trained mine, decades ago, before I was anyone.*
And so they came to check.

The recognition lands. The sensei's father's name is real to them. The
father's name is real because worldgen rolled him — a sensei active in NJ
in some specific decade, with a rolled style and a rolled lineage of his
own, whose record exists in the chronicle the player can browse. The twins'
father trained under that man briefly in 1988 or 1996, the chronicle says
so, and his sons want to be like *their* father, the way their father
wanted to be like the sensei's father. They want to become champions.

They sign up that day, both of them. The first two students whose presence
in the dojo is owed not to a flyer or a price point but to a story carried
across generations. The cultural feedback loop's opening iteration:
reputation preceded reality. The lineage is felt history now, not a stat,
and the felt history is grounded in the chronicle worldgen produced.

This scene drives Ring 3's recognition-walk-in mechanic, the father's-style
seed (the cultural DNA the player chose at character creation, which
worldgen used to backfill the father's record), and the hidden-needs/goals
layer (the twins arrive with a stated long-term goal — *be like our
father, become champions* — which the player gets for free as the opening
scene's gift, and which can evolve over years of play). It also depends on
Ring 2 producing a coherent backstory for the father; without worldgen,
the recognition is a stat trick, with worldgen, it's earned.

### The Closing Anchoring Scene — The Twins as Disciples (basement-opening path)

Years later. Both brothers earned their black belts under you. Neither
left. Neither plateaued. Neither chose a different dojo when they had the
chance — and worldgen made sure they had the chance, because BJJ schools
opened in the area in their teens, and a rival judo dojo offered them
spots when they were brown belts, and one of them dated a girl whose
brother trained somewhere else for two years. They stayed. They competed.
They won enough. They lost enough. They learned to teach. And now they
teach alongside you. Two of the lifecycle's terminal states ("assistant")
resolved for a pair of characters the player has known since month one.

This is the happy ending, not the default outcome. Twins create a built-in
attention conflict — one will feel they're getting less of your time than
the other; one might plateau while the other advances; one might leave to
chase a worldgen-generated opportunity at another dojo. Getting to *both*
of them as assistants is the payoff for managing the jealousy, the pacing,
the individual needs across years of in-game time, against the
gravitational pull of a real surrounding ecosystem. A game that can
produce this scene has every supporting system working: match engine,
worldgen, lifecycle, needs/goals, cultural feedback, attention scarcity,
calendar, session composition, conversation, retention, promotion
philosophy, gravitational pull from competing gyms.

This is a valid design north star because it cannot be produced with a
shortcut. The arc is the architecture working.

### Why other openings don't get named anchoring scenes (yet)

The mid-tier-inheritance opening produces its own first-month and long-arc
scenes (a retiring sensei hands over keys; the player negotiates with an
existing roster they didn't choose; a former student of the previous
sensei tests the new owner). The advanced-start opening produces its own
(a dojo with an Olympian on the roster, inheriting that judoka's training
plan, deciding whether to honor it or reshape it). These arcs are real
and the architecture has to support them. But the basement-from-zero arc
remains the named tutorial path because it builds up from nothing — every
mechanic the player learns is one the architecture is also building from
nothing. Once the basement arc plays cleanly, the other arcs are
parameterizations of the same machinery.

---

## THE NORTH STAR — DESIGN BY STORY

*The working principle of the project. Unchanged across the April 23 and
May 4 reshapes — the principle is what produced both reshapes.*

Tarn Adams described his design philosophy for Dwarf Fortress as: write
the stories you want the game to produce, then design the systems that
produce them. Narrative-first design.

Hajime is built the same way. The three Anchoring Scenes above are not
mockups. They are stories the designer wants to read. The grip graph
exists because the Tanaka-Sato scene needs a grip graph to be legible.
The recognition-walk-in mechanic exists because the twins-arrive scene
needs the father's name to be real. The full lifecycle and conversation
mechanic exist because the twins-as-disciples scene needs years of
accumulated knowledge of those two specific kids to feel earned. The
worldgen reframe arrived because the recognition-walk-in scene was
*pretending* the father's name was real when it was just a stat — and the
designer noticed the pretending and decided the stat had to become a real
chronicle entry.

Every architectural decision in this document traces back to a scene the
designer wanted to be able to witness.

**The discipline going forward:**

1. Write a scene. Concrete. A specific match, a specific training session,
   a specific coaching moment, a specific page of the chronicle.
2. Identify what systems would be required to produce it.
3. Build the smallest version of those systems that lets the scene happen.
4. Run the simulation. See if the scene emerges. If it doesn't, refine.
5. Write the next scene. Build what it needs.

When in doubt about what to build next, do not look at the ring roadmap.
Look at the scenes. Write one that excites you. Ask: "What systems does
this scene require?" Build those.

The game is not a feature pile. The game is the collection of stories it
can produce.

---

## THE PHYSICS PRINCIPLE

*Added April 14, 2026. Drives Ring 1.*

Two judoka walk onto the mat. They have never met before — not as people,
and not as bodies. The height differential, the arm reach, the hip
geometry, the weight distribution — these specific numbers have never
been in this specific combination before.

That is what makes every match unrepeatable.

Not random numbers. **Combinatorial physics.**

A throw that wins one match loses the next — not because of luck, but
because of geometry. The same seoi-nage that Tanaka lands on a 178cm
opponent fails against a 165cm fighter who gets *under* his entry. The
physics changes. The prose reflects the physics. The moments that get
marked are the moments the physics resolves something unexpected.

This is the difference between an arcade simulation and *the* simulation.
It is also what creates the game's skill ceiling.

Five core physical variables (full spec in `biomechanics.md`):
1. Height & limb length — moment arm advantage on hip throws
2. Arm reach — grip control radius
3. Hip height & hip-to-shoulder ratio — kuzushi geometry, throw entry cost
4. Weight distribution — which directions are exploitable
5. Body type (mass & density) — inertia, recovery rate

These live in the Identity layer. They are who the judoka IS. They shape
every calculation in every ring — including the abstracted resolver, which
must respect them in aggregate even when it doesn't simulate them
tick-by-tick.

---

## THE GRIP GRAPH

*Added April 14, 2026. Drives Ring 1. Full spec in `grip-graph.md`.*

A judo match is not two fighters with stat sheets — it is a relational
state between two bodies. The grip graph models this state explicitly as
a bipartite graph: each active grip is a typed edge connecting one
fighter's grasping body part to one location on the other fighter's gi or
body, with metadata for grip type, depth, strength, and how long it's
been held.

Both fighters can have multiple edges into each other simultaneously.
Edges form at engagement, contest each tick, slip or break under fatigue,
and persist or transform across position transitions. Architecture
borrowed directly from Dwarf Fortress's grapple system.

What the graph enables:

- **Throws gated on real prerequisites.** No throw fires without the
  edges to support it. Seoi-nage requires a deep collar grip; without
  one, the fighter can't launch it (or force-attempts at massive penalty —
  the desperate, sloppy attempt that earns shido).
- **Ne-waza becomes structural, not abstract.** Chokes, joint locks, and
  pins all read from the graph. Multi-turn commitment chains operate on it.
- **The Matte panel renders the graph.** Coach IQ gates how much of the
  graph is visible: a novice coach sees position and qualitative fatigue;
  an elite coach sees numeric depth values and the opponent's fatigue
  distribution per body part.
- **The prose engine has specificity to draw on.** "Tanaka's right hand
  still on the collar" maps to a specific GripEdge. "Sato strips the
  sleeve grip" maps to a specific edge transitioning to FAILURE.

The grip graph is the foundation of Ring 1. Every other system reads from
it or writes to it.

---

## THE GRIP SUB-LOOP

*Added April 14, 2026. Drives Ring 1. Full spec in `grip-sub-loop.md`.*

Underneath the Matte cycle and the tick heartbeat, a third rhythm runs
continuously: the Grip Sub-Loop. Two fighters engage, contest for grip
dominance, and the micro-exchange resolves in one of three ways — a
kuzushi window opens, a stifled reset breaks them apart, or a fighter
commits to a throw attempt. Dozens of sub-loop cycles occur between any
two Matte calls.

**Three outcomes, not two.** Most judo games model throws as binary:
attempted/not attempted. Hajime models the space between throws as
active, contested, and resolution-bearing. Most of a real match's time —
and most of where matches are actually decided — lives inside this
sub-loop.

**The coach is not always involved.** A match can end inside a single
sub-loop cycle. A fighter who wins the opening grip war decisively, opens
a kuzushi window at tick 12, and lands seoi-nage for ippon has ended the
match before the referee called Matte. The coach never spoke. This is
not a failure mode — it's one of the most beautiful outcomes in real
judo.

The lesson the sub-loop teaches: **preparation is the primary lever, not
intervention.** Over a career, good coaching is distributed across
training, not chair-time. The dojo deep-dive (Ring 3) is where most
coaching actually happens.

---

## THE TWO PLAY MODES

*Added April 23, 2026. Updated May 4, 2026 to reflect that both modes now
run on top of worldgen — the difference is whether the Narrative Event
Framework is on or off.*

Hajime ships with two play modes, structured around a primary/secondary
split. Both modes use the same Ring 1 + Ring 2 + Ring 3 substrate; the
difference is one toggle on Ring 4 (Narrative Event Framework).

### Career Mode — the EA entry point

Primary mode at Early Access. Closer to **Wildermyth** than to Dwarf
Fortress. The player lives a defined sensei's life inside a fresh
worldgen-NJ — opening (basement, by default), through decades of career,
with recurring Anchoring-Scene-weight narrative events that shape the
story's direction. Same systems underneath the simulation, but the
Narrative Event Framework (Ring 4) is *on*, scripting the spine of the
campaign.

The opening defaults to basement-from-zero (the tutorial path) but admits
worldgen-driven alternatives on subsequent runs: inherit a mid-tier
worldgen dojo from a retiring sensei, buy out a struggling existing dojo
with reputation baggage, or take over an established dojo with an
Olympian on the roster. The middle has shape: Inheritance Event around
year 2 (now worldgen-driven — the father is a chronicle entity, the
offered dojo is a worldgen dojo with rolled history), First Team
Tournament shortly after, antagonist-arc events (the antagonist is now a
procgen rival owner whose motivations are rolled, not asserted), optional
Marriage / Children arcs, recurring "two rising stars same weight class"
dilemmas. The closing is defined: Retirement and Succession — the sensei
chooses who inherits the dojo, and the campaign's last image is a future
worldgen tick in which the player's dojo continues without them.

Most of a career run is the systemic dojo deep-dive; a handful of moments
per in-game year are scripted narrative events. Either-choice-is-okay
applies throughout.

### Sandbox Mode — post-EA, emergent

Closer to Dwarf Fortress. Open-ended simulation with the Narrative Event
Framework *off*. The player drops into a procedurally generated dojo (or
inherits a previous run's dojo via the successor-start variant) in the
same worldgen-NJ Career Mode uses. No scripted events. Pure emergence.
Whatever story the simulation produces — including via the worldgen world
running in parallel around the player — is the story.

Sandbox Mode ships post-EA, deeper into the 1.x horizon. Career Mode is
the EA face of the game; Sandbox is the long tail.

### Why the split exists

Career Mode is *your sensei's story*, with a defined opening and
inevitable middle moments scripted on top of an emergent world. Sandbox
Mode is *a sensei in a simulated world*, where emergence is the
storyteller. Hajime serves both; the split lets each mode do what it does
best.

Architecturally, the systems are shared. The Narrative Event Framework is
one toggle on top of the Ring 1 + Ring 2 + Ring 3 substrate. This means
every system built for those rings serves both modes — no double-
building.

---

## THE SIMULATION RINGS

*Reshaped April 23, 2026 (v17 dojo-loop reshape) and again May 4, 2026
(worldgen reframe). Concentric layers, inner rings get built first.
Physics, grip graph, sub-loop, the world, the dojo deep-dive, the
narrative event framework, and the optional adventure mode build up in
this order.*

### Ring 1 — The Match Engine

**Status: Phase 1 ✅ done, Phase 2 ✅ done, Phase 3 calibration in
progress (grip-as-cause refactor ✅ shipped; Godot calibration tool
HAJ-150 active and ongoing; Session 5 next).**

Tick-driven simulation of two judoka grappling on a relational state
graph. The grip sub-loop runs continuously, producing kuzushi windows,
stifled resets, and throw attempts. Throw resolution computes landing
geometry (angle, impact, control) which the referee personality reads to
award scores. Stuffed throws can open ne-waza windows. The Referee class
governs Matte calls and shido escalation.

The grip-as-cause refactor — pulls becoming the cause of throws via
emitted kuzushi events, replacing the grip-as-gate model — has shipped.
Calibration ongoing via the Godot calibration tool (HAJ-150 and the
HAJ-160s), which lets matches run at scale with thresholds tunable in a
live UI rather than via code edits. This is the substrate Ring 2's
abstracted match resolver will be calibrated against.

Match-end logic gaps surfaced by the HAJ-68 audit (golden score, direct
hansoku-make, time-expiration event) remain on the Ring 1 polish list.

Ring 1 also produces the *unattended-match* path that Ring 3 needs for
background simulation. When the sensei watches one randori pair, the
other pairs run the unattended path silently — same simulation, no prose
output, coarse improvement deltas only. Building the unattended path now
pays forward into both Ring 2 (where it shares architecture with the
abstracted resolver's match output) and Ring 3.

### Ring 2 — Worldgen and Legends

**Status: Not yet started. Largest single subsystem in the project.
Replaces what was previously called Ring 2 (now Ring 3). Full first-cut
spec in `one-year-of-worldgen.md`. Ring patch decision in
`master-doc-patch-2026-05-04.md`.**

Multi-decade simulation of New Jersey judo from 1960 forward. Includes:

- **The abstracted match resolver.** Lightweight probabilistic resolver
  that runs across decades of simulated tournaments. Each judoka has a
  sparse skill vector (~5 dimensions: tachiwaza, ne-waza, conditioning,
  fight IQ, signature strength). Tournament brackets resolve as
  probabilistic matchups. One match per tournament gets tagged "notable"
  and earns a sentence of texture from the procgen template library. The
  deep engine (Ring 1) activates only when the player watches. The
  resolver must be calibrated against the deep engine so worldgen-
  generated rankings produce results consistent with what the deep engine
  would have produced. The calibration work is real and ongoing
  throughout Ring 2 development.
- **Procgen senseis and judoka with full lineage data.** Every entity in
  the simulated state carries lineage from day one — who-trained-whom,
  who-came-from-where, what-history-do-they-carry. The Q15 lineage
  commitment, previously a forward-compatibility hedge, now load-bearing.
  Probably 2,000–8,000 named individuals across the state at any given
  time, varying by era; 20–80 operating dojos statewide.
- **Multi-dojo population flow with cross-discipline gravitational pull.**
  Wrestling clubs (present throughout), boxing gyms (present throughout),
  BJJ schools (appearing late 1990s, expanding through 2010s). Non-judo
  gyms have lighter profiles than judo dojos but exert real gravitational
  pull on the local martial-arts population. A judo student whose hidden
  goals don't align with their dojo's offering has a chance per quarter
  to investigate alternatives; if a nearby gym better matches their
  unmet need, they migrate. Records: *Marco trained with us 2018–2021.
  Left to pursue ne-waza specialization at Garden State BJJ.* Real,
  legible reasons. Not "stolen by enemy." This is the version of the
  faction layer that respects how martial arts actually share
  populations.
- **Tournament hierarchy.** Town locals, regional, county, state,
  regional qualifiers, national qualifiers, Olympic-cycle qualifiers.
  Tournament density and notable-event frequency vary by quarter (Q2 is
  the storytelling-rich quarter; Q1/Q4 are the population-flow quarters).
- **Technology eras with mechanical effects.** Paper and Radio
  (1960–1985), Phone and Fax (1985–2000), Email and Web (2000–2015),
  Smartphone (2015+). Each era has mechanical effects on information
  flow, the roster surface, and reputation propagation — not just flavor.
  The notepad-to-computer roster transition becomes era-gated by default,
  with facility upgrades acting as multipliers.
- **Rules evolution across decades.** Pre-2010 leg-grab era; post-2010
  leg-grab ban (the big rules cliff). The abstracted resolver only needs
  the *style distribution* to differ by era — pre-2010 worlds produce
  more leg-grab finalists, post-2010 don't. Actually simulating
  period-correct rules in the deep engine is real work and is deferred;
  worldgen records the era; the engine catches up later or never.
- **NJ geography and population.** 21 counties. Real population
  distribution drives dojo density. Major hubs (Newark, Jersey City,
  Paterson, Elizabeth, Edison, Toms River, Trenton, Camden, Hamilton,
  Clifton, Cherry Hill). Cranford sits in Union County — mid-density,
  suburban — and Cranford JKC opens there in 1962, invariant. Geographic
  friction on population flow: students don't realistically commute
  cross-state.
- **Fog-of-war progression.** The world is fully generated underneath.
  The player earns access through their dojo's competitive presence.
  See *The May 4 Worldgen Reframe* above for the ladder.
- **The legends-rendering layer.** A browsable history book at handoff,
  organized by year, by dojo, by notable individual. Cranford JKC has
  its own page from 1962 onward. A 66-year history book is mostly empty
  — maybe 1,500–3,000 entries across six decades, ~30 entries per year
  for an entire state. The sparsity is what makes legends feel like
  legends. Authoring the procgen template library to produce
  narrative-feeling output (notable upsets that feel notable, lineages
  with texture, dojo histories with arcs) is the biggest hidden cost in
  Ring 2.
- **State-modular architecture.** NJ is the 1.0 state. The worldgen
  pipeline is parameterized so adding Pennsylvania or California is
  content work, not architectural work. International scope = Hajime 2.

The patch document calls this Ring 2.5 as a hedge framing, but the doc
formally adopts it as Ring 2 — the worldgen sits beneath the dojo
deep-dive structurally and gets built first.

### Ring 3 — The Dojo Deep-Dive

**Status: Not yet started. Inherits most of the previous Ring 2 design
body. The v17 design questions doc remains valid as Ring 3 work; some
answers will need revision once Ring 2 architecture is concrete. Park
the v17 work; do not delete it.**

The within-dojo daily play layer. Sits *inside* the Ring 2 world. Most
of a campaign is here. Ring 3 contains:

- **Calendar as primary surface.** Weekly schedule, session blocks,
  attendance patterns. Sessions cost money and capacity.
- **Session composition.** Each session is an ordered sequence of
  activity blocks (warm-up, technique drilling, randori, ne-waza,
  conditioning, kata, competition prep). Starting library of ~10
  activity types, growing toward 15–20 by Early Access.
- **Roster as second primary surface.** Notepad (early game, ~10
  students, handwritten margin notes) → computer (Football
  Manager-style spreadsheet, era-gated by default with facility
  upgrades as multipliers). The roster is where attachment accumulates
  mechanically. Visibility layer — fields fill in only as
  conversations uncover them.
- **Watched session as third primary surface.** Inside any session,
  attention scarcity operates: the sensei can watch one randori pair
  (full Ring 1 rendering) while others run unattended. Conversations
  are an alternative attention spend during a session — pull a student
  aside, unlock visibility on one of their needs or goals.
- **Student lifecycle.** Procedural generation (drawing from the Ring 2
  population), trial week, paying student, belt advances, plateau,
  departure (often to a Ring 2 destination — rival judo dojo, BJJ
  school, wrestling room, leaving the sport), late-game terminal
  states (assistant, starts own dojo, joins competition circuit, leads
  seminars). Quit probability has a floor — some students always leave,
  regardless of effort.
- **Hidden inner lives.** Each student has 1–3 immediate needs and one
  long-term goal, hidden by default, revealed through conversation.
  Goals evolve over months/years of in-game time. Direct lift from
  Player Two's psychology architecture, arriving earlier than planned.
- **The antagonist (reframed).** No longer the cartoon "slimy suit." A
  procgen rival owner whose motivations are rolled — sometimes a
  predatory consolidator, sometimes a former judoka turned operator,
  sometimes a generational figure who inherited a dojo and runs it
  like a business. Appears when savings drop below threshold (or
  worldgen places one in a position that produces conflict). State
  machine: not-yet-met → visited-once → escalating → offering →
  buys-you-out / backs-off. The Inheritance Event becomes worldgen-
  driven (see Ring 4); the antagonist may acquire one of the dojos
  the player declines.
- **Pricing as demographic lever.** Base subscription, group/family
  discounts, belt-level discounts, mat fees. Price choice biases who
  walks in, drawn from the Ring 2 population.
- **Six cultural inputs.** See *The Six Cultural Inputs* below.
- **Word-of-mouth reputation.** No reputation meter. Reputation
  propagates through procedural generation of new arrivals and through
  narrative surfacing (former students appearing at competitions in
  rival colors — and now those rivals are real worldgen entities with
  their own histories).
- **Facility progression.** Mat space, weight room, mini sauna,
  eventual move out of basement. Each upgrade is a culture signal AND
  a capacity unlock. Now also acts as a multiplier on era-gated
  information flow.
- **Sponsorships.** Late-early-game unlock for sustaining talented
  students whose families can't pay. Thematic core preserved: who
  deserves more vs who pays more.

Most of the above is specified in `dojo-as-institution.md` (expanded
version pending) and the v17 questions doc. Some sections will need
revision once Ring 2 architecture is concrete — notably the
antagonist (reframed above) and the Inheritance Event (now in Ring 4).

### Ring 4 — The Narrative Event Framework

**Status: Not yet started. Sits on top of Ring 3, shapes Career Mode.**

The scripted-event spine of Career Mode. Each event is an
Anchoring-Scene-weight moment with multi-factor triggers (time
elapsed, economic state, roster state, prior-event history, *worldgen
state* — what's happening in the surrounding ecosystem) and meaningful
branches. Either-choice-is-okay applies. Events ship incrementally —
the EA library is 5–8 major events; the post-EA library grows toward
the full career arc.

Confirmed events:
- **Twins Arrive** (basement-opening only; fires within first month;
  worldgen-grounded recognition of the father's name)
- **First Team Tournament** (mid-early game, against a worldgen rival
  dojo)
- **The Inheritance Event** (~year 2, a worldgen-rolled retiring
  sensei offers his established dojo; the player chooses;
  worldgen-rolled antagonist takes whichever the player doesn't)
- **The Antagonist's Fall** (mid-late game, if you've competed
  successfully against the antagonist's dojo)
- **Marriage / Partner** (optional mid-campaign)
- **Children** (optional, may include twins as recursion)
- **Olympics Run** (late-career, a student qualifies — fog-of-war
  unfogs the international layer)
- **Two Rising Stars Same Weight Class** (recurring structural
  dilemma)
- **Retirement & Succession** (closing, choose your successor; the
  campaign's last image is a future worldgen tick)

Full spec lands in `career-mode-and-narrative-events.md`.

Ring 4 is also where the lineage system's *narrative* features live
for 1.0 (succession choice, legacy screen, successor-start variant).
The lineage *data* is captured in Ring 2 (worldgen) and Ring 3 (dojo
roster). Ring 4 surfaces it as story.

### Ring 5 — Adventure Mode (play-as-judoka)

**Status: Post-1.0 / Hajime 2.x direction. Sketch in
`play-as-judoka-mode.md`. Don't build for it; don't promise it; don't
lose it.**

Coaching is the soul of Hajime. But the grip graph architecture also
opens the door to a separate mode where the player controls a judoka
directly — the same way DF's Adventure Mode lets you wrestle with
explicit control over which body part grabs which target.

In Adventure Mode, the grip graph IS the chess board. You see the
live edges. You choose which grasper goes for which target. You commit
to throw entries. You roll counter-actions in ne-waza. The action
choices flow from the visible graph state.

This could be:
- Single-player vs. AI
- Multiplayer (turn-based or real-time) where two players grapple
  through the same graph — a chess match of attacks, counters, and
  5-moves-ahead planning

Architecturally requires Ring 1 (grip graph + ne-waza) to be solid,
which the EA work delivers. Out of scope until 1.0 ships.

### Ring 6 — The 2D Visual Layer

**Status: Post-EA polish. Pixel-art figures, stripe-based grip
indicators, Kairosoft-style top-down dojo view.** Always paired with
the prose log, never replacing it.

Visual rendering of the grip graph (each edge as a visible stripe of
varying thickness/opacity). Dojo facility view (mats, weight room,
sauna). Tournament venue rendering. Calendar visualization that goes
beyond the spreadsheet. The legends layer's history-book UI sits here
too — the chronicle is structured data underneath, but the rendering
of it (with worldgen maps, lineage trees, dojo-records pages) is
visual work. Symbols that change state, not animation frames.

### Ring 7 — Sound

**Status: Post-EA polish.** Dojo ambient theme, match tension layers
responsive to score and fatigue, signature motif when one of *your*
judoka enters their finals, audio language for graph state changes,
distinct register for legends-mode browsing (quieter, more
archival). Built when the world is ready to hold it.

---

## THE SIX CULTURAL INPUTS

*Added April 23, 2026. Updated May 4, 2026 — under the worldgen reframe,
the six cultural inputs are no longer only the player's levers. Worldgen
senseis accumulate cultural decisions too. The cultural feedback loop
runs on every dojo in NJ, not just the player's. The worldgen output is
in part a record of how dozens of senseis settled into their cultures
across decades.*

1. **Session content.** What you drill, week after week. A dojo that
   runs 30 minutes of randori per session has a different feel than one
   that runs 30 minutes of instruction. A dojo that drills O-Soto
   entries specifically is biasing students toward a particular style.
   Session content is the primary mechanism by which dojo culture gets
   built into student capability — and worldgen records this for every
   dojo in the chronicle.

2. **Pricing.** High prices attract status-conscious committed students;
   low prices flood the room with kids and casual attendance; group
   plans build a family-social dojo; belt discounts retain advanced
   talent. Price choice shapes who walks through the door. Worldgen
   dojos have pricing histories too, and the era-appropriate price
   norms vary by decade.

3. **Father's-style lineage.** The cultural DNA you started with. The
   style chosen at character creation seeds the dojo's initial
   reputation, biases which kinds of students are first attracted
   (family friends, old students of the father, judoka who recognize
   the name from worldgen history), and determines what the sensei
   teaches well. Under the worldgen reframe, the father is now a
   chronicle entity — he has a specific lineage, a specific era, a
   specific record. The starting cultural seed is grounded in real
   simulated history.

4. **Atmospheric choice.** Within a session, what the air feels like —
   game-based vs competitive, relaxed vs strict, collaborative vs
   trial-by-fire. The coach isn't manipulating student goals directly;
   they're shaping the environment that shapes the students.

5. **Promotion philosophy.** "Compete to earn it" vs "time and
   discipline" vs "rigorous gatekeeping." The pattern of belt-promotion
   decisions becomes a reputation signal across many students. *This
   dojo is where you actually have to earn it.* Worldgen dojos carry
   their own promotion patterns into the chronicle.

6. **Competition readiness pattern.** Every student has an opinion
   about competing. The accumulated pattern reveals what the dojo is
   for: a "push everyone in" dojo produces one kind of student; a
   "wait until they're ready" dojo produces another.

The six inputs are not independent. A high-pricing trial-by-fire
push-everyone-into-tournaments rigorous-gatekeeping dojo is internally
coherent. So is a low-pricing companion-oriented wait-until-they're-
ready dojo. Mixed signals produce mixed results. A dojo that hasn't
settled on its culture struggles to attract students of any kind — and
the worldgen chronicles include plenty of dojos that never settled and
closed within five years because of it.

---

## THE SKILL CEILING

*This is what separates Hajime from other sports sims. Updated May 4,
2026 to add a worldgen-reading layer.*

**Casual player, match-engine experience:**
- Tanaka is strong on the right side
- His seoi-nage works well
- He's getting tired in round two
- The ref is calling Matte quickly — should probably reset

**Advanced player, match-engine experience:**
- Tanaka's moment arm advantage disappears against anyone under 172cm
- His hip drop speed is the bottleneck, not his grip strength
- The fatigue curve on his right forearm hits the threshold around
  tick 180 — build the game plan around early ippon, not attrition
- This ref has low stuffed_throw_tolerance and high
  match_energy_read — instruct conservative early
- His training lineage is 100% Classical Kodokan; under a
  Georgian-voiced coach in the chair, reception efficiency drops
- His preferred grip configuration is HIGH_COLLAR with sleeve;
  against a southpaw, his engagement edge formation drops 30%

**Casual player, dojo-loop experience:**
- Marco is improving on grip
- The new student wants to compete
- Savings are getting low — should run more classes
- The roster has too many gaps to fill in — better just trust the
  schedule

**Advanced player, dojo-loop experience:**
- Marco's grip is improving but only against light resistance
  partners — pair him with Sato in randori to expose him to a real
  grip war
- The new student wants to compete but their long-term goal
  (uncovered in three conversations) is "make dad happy" — pushing
  them into a tournament too early risks the goal evolution
- Savings are getting low because the kids' class roster has churned;
  drop the Saturday morning slot, add a Tuesday evening for the
  working-adult demographic
- Three students are crossing into yellow-belt threshold this week.
  Promoting all three reinforces the "fast cadence" reputation the
  dojo is becoming known for

**Casual player, world-reading experience:**
- There's a BJJ school down the road that's pulling some of my
  students
- A new dojo opened in the next town
- The Olympics are coming up; one of my students might qualify
- Cranford JKC has been around forever

**Advanced player, world-reading experience:**
- Garden State BJJ opened in 2003 under a Gracie-lineage instructor
  who briefly trained at Edison Judo in the early 90s — that's why my
  ne-waza-curious students drift there specifically. If I shift session
  content toward more ne-waza, the gravitational pull weakens.
- The mid-tier dojo on offer in this Inheritance Event was founded in
  1978, switched senseis in 1994, and has been in cultural decline
  since 2011 — its remaining roster skews older and wants tradition,
  not competition. Inheriting it means inheriting that culture, not
  rebuilding from scratch.
- My student's likely Olympic-qualifier opponent trained at a dojo
  that produced two national medalists in the 2010s under a sensei
  whose grip game is famous in the chronicle — I should expect
  pistol-grip pressure from round one and prep for it specifically.
- Cranford JKC has produced four assistant-grade lineages I can trace
  through the chronicle; one of my own assistants comes from one of
  those lines. The recognition the twins felt is the same recognition
  half the room would feel if I read out the name on the directory
  plate at the right tournament.

Same simulation. Different depths of reading. Neither player is wrong.
The game rewards depth if you go looking for it.

The world has its own skill ceiling layered on top of the dojo loop's,
which is layered on top of the match engine's. Together, they produce a
game that can be enjoyed lightly across many runs and studied deeply
across one.

---

## THE INSTRUCTION TAXONOMY

*Initial set. Will grow with playtesting. Seven categories drawn from
the research doc `coaching-bible.md`.*

**Score / Time status** — You're up. Shido him. Two minutes. One
minute.

**Grip-focused** — Break his grip first. Get the dominant grip before
you commit. Switch stance — attack the other side. Stop reaching with
your tired hand. Strip his pistol grip.

**Tempo-focused** — Stay patient. Let him come to you. Push the pace.
Tire him out. Slow it down. Reset. Attack on his next breath.

**Technique** — Seoi. Uchi-mata. Tokui-waza (your best). Ko-uchi
first, then seoi.

**Tactical** — Go to the ground if he opens up. Stay standing — he's
better on the mat. Attack his weak leg. Counter, don't initiate.

**Composure / Defensive** — Tighten up. He's reading you. Head up.
Posture. Block. Don't let him turn in. Breathe. You have time.

**Motivational / Risk** — Take the chance. Go for ippon. Play for
shidos. He'll panic. Defensive grip. Run the clock.

**Physics-aware** — Use your height. Make him reach up. Get lower than
him. Take away his entry. He can't sustain that grip. Wait him out.
His left side is weaker. Circle that direction.

---

## TONE RULES

**The voice of the match log is a knowledgeable sportswriter.** Specific.
Calm. Loves the sport. Doesn't explain what kuzushi is — assumes the
reader is paying attention or willing to learn. Neil Adams commentary
register — quiet, diagnostic, annotating deltas.

**The voice of the coach window is intimate.** It's the player's view of
their fighter. Quiet, focused, slightly worried. Physics-aware without
being clinical — *"His entry window is closing"* not *"moment arm
modifier is below threshold."*

**The voice of the dojo is warm.** This is home. This is where the work
happens. The dojo prose has the texture of routine — sweat, repetition,
small jokes, the smell of the mats. The notepad-stage roster is
handwritten; margin notes feel like a real sensei's real notes, not
like a game surfacing information.

**The voice of the legends is archival.** Added May 4, 2026 with the
worldgen reframe. The chronicle's prose is calm, distant, and complete.
Past tense. No drama in the writing — drama is in the reader's
recognition that *this happened*. *"Yamada won the 1974 state final on
a contested decision over the favorite. He retired the following year
and never coached. His sensei was Yonezuka of Cranford."* No
adjectives the events don't earn. The history book speaks the way a
serious sportswriter writes about a previous generation of the sport
— with respect, without embellishment.

**No hype. No announcer voice.** Hajime is not the UFC. It is judo —
a sport with deep roots, formal etiquette, and an understated culture.
The writing respects that. The chronicle especially respects it; the
chronicle is the closest thing the game has to a record of dignity.

**Every fighter is treated with dignity. Including the opponents.
Including the ones who lose. Especially the ones who lose. Especially
the ones in the chronicle whose careers ended in single sentences.**

**Physics resolves; prose marks.** The simulation never announces the
physics. When a smaller fighter lifts a heavier one, the log doesn't
say "moment arm calculation succeeded." It says something that earns
the moment.

**The graph is the source of specificity.** "Tanaka's right hand still
on the collar" maps to a specific GripEdge. "Sato strips the sleeve
grip" maps to a specific edge transitioning to FAILURE. The prose
names what the graph has just done.

**The grip sub-loop runs silently most of the time.** Stifled resets
early in a match are not narrated. The log gets denser as fatigue
develops and the sub-loop starts resolving things that matter.

**The dojo prose has its own register.** Different from match prose,
different from coach-window prose. Weekly roundups feel like the
sensei sitting down on a Sunday evening with the notepad.
Conversations during sessions feel like the moment they are — pulled
aside, the rest of the room going on without you.

**The chronicle's procgen template library is the biggest hidden cost
in Ring 2.** Producing narrative-feeling output (notable upsets that
feel notable, lineages with texture, dojo histories with arcs) is
real authoring/design work. The library needs significant content to
produce variety. Plan for it.

---

## OPEN QUESTIONS

*Pre-v17 questions answered. v17 dojo-loop sub-questions parked until
Ring 3 work begins (full list in `dojo-loop-design-questions-v17.md`
and `dojo-loop-design-questions-v18.md`). Ring 2 worldgen questions are
new and live below. Top-level architectural questions worth preserving
here:*

### Top-level (preserved)

**Q1: How real-time is the watched-match path?** Live-scrolling log
with player-controlled speed seems right. Worth playtesting with the
zoom-level controls layered on top.

**Q2: How many students in a starting roster?** Active enrolled count
probably grows from 0 → 5–10 across the first in-game year, ceiling
around 15–25 mid-game, larger for established late-game dojos.
Calibration target.

**Q3: How long is a "campaign"?** A complete Career Mode run spans
10–15 in-game years minimum to let the twins arc complete. Roughly one
in-game year per 20–60 minutes of real playtime, varying with zoom.
Total: probably 10–30 hours of real time per campaign. Multiple
campaigns possible.

**Q4: How does a non-judoka learn the sport through play?** Glossary
tooltips on every term. Tutorial mode optional — for many players the
basement-dojo opening should be self-explanatory through play.

**Q5: AI prose generation for matches and dojo events?** Build
deterministic prose templates first as fallback; layer Claude-in-Claude
generation on top once the system works. The grip graph and the rich
dojo-state make Claude-generated prose dramatically more grounded.
Same architecture applies to the chronicle's procgen templates in
Ring 2.

**Q6: How granular does the physics get in Ring 1?** Five variables
specified. Phase 3 calibration is tuning what we have. Adding more
variables is post-EA unless calibration reveals one is needed.

**Q7: How does the advanced player *see* the dojo state?** The roster
(notepad → computer) is the primary surface. The weekly roundup is
secondary. The session-watching mechanism is tertiary. All three
layered with the visibility (hidden-info) principle.

**Q8: When does Adventure Mode (play-as-judoka) get scoped?** Not
until 1.0 ships. The sketch preserves the idea; the discipline holds.

### Ring 2 worldgen questions (new — May 4, 2026)

*Suggested defaults below come from `one-year-of-worldgen.md`. They
are tentative until the Ring 2 spec lands.*

**WG-A: Is worldgen visible to the player as it generates, or produced
silently and presented as a finished history book?** DF shows worldgen
visually with its little growing map and population counter. CK3
doesn't. Showing it makes worldgen itself a piece of entertainment;
hiding it makes the handoff cleaner. Cost differs significantly.
*Suggested default: silent for 1.0, visible-toggle in a later update.*

**WG-B: Is each campaign a fresh worldgen, or does the player play in
a "default NJ" that's been generated once and stored?** *Suggested
default: fresh worldgen per campaign, with a seed system so a notable
world can be replayed or shared.*

**WG-C: Can the player choose their handoff year?** Default present-
day, but a "start in 1985" or "start in 2010" option would be a
different game. *Suggested default: handoff is always at the
worldgen's end-year (present-day) for 1.0; era choice is post-EA.*

**WG-D: How rich is the legends-rendering layer?** A history book of
bare facts ("1968: Yamada wins state.") is boring. The procgen
template library needs significant content to produce variety. *This
is the biggest hidden cost in the worldgen system. Treat it as real
authoring work in the Ring 2 budget.*

**WG-E: How does the abstracted resolver get calibrated against the
deep engine?** *Suggested approach: build the abstracted resolver as
a probabilistic surrogate of the deep engine, calibrated by running
both on the same matchups during development. Calibration is real
ongoing work, not a one-time pass.*

**WG-F: What survives and what gets recast from the v17 dojo-loop
work?** Most of v17 remains valid as Ring 3 work. Specifically
recast: the antagonist becomes worldgen-generated; the Inheritance
Event becomes worldgen-driven; the recognition-walk-in mechanic
backfills against the chronicle. Specifically parked: the v17
sub-question list waits until Ring 3 begins.

**WG-G: Cranford JKC's specific seeded sensei — rolled or named?**
The dojo's existence is fixed. *Suggested default: name fixed,
sensei attributes rolled. The name carries the personal anchor; the
attributes vary so each campaign's Cranford has a different texture.
The exact name is Comrade's call; this is one of the only places in
the design where naming a real person would be appropriate, if
Comrade wants. If not, a respectful fictional name keeps the anchor
without the surface reference.*

**WG-H: Is worldgen Ring 2, Ring 2.5, or its own thing?** The patch
hedged ("Ring 2.5 or its own ring"). This master doc adopts it
formally as Ring 2 — the worldgen sits beneath the dojo deep-dive
structurally and gets built first. Ring 3 is the dojo deep-dive (the
old Ring 2). Subsequent rings shift up by one.

---

## PROJECT ARCHITECTURE

*Sessions roll up into phases. Phases roll up into rings. Rings roll
up into the game. Each layer is a committable, reviewable unit.
Ring 1 is mostly done; Ring 2 (worldgen) is the next major build
target; Ring 3 (dojo deep-dive) follows.*

**Ring 1 — Match Engine**
- Phase 1 — Skeleton ✅ April 13, 2026
- Phase 2 — Real Combat + Grip Graph + Ne-Waza + Referee
  - Session 1 ✅ April 14, 2026 (throw resolution, scoring, fatigue,
    match-end)
  - Session 2 ✅ April 15, 2026 (grip graph, position machine,
    ne-waza, Referee)
  - Session 3 ✅ April 17, 2026 (physics substrate design, Mode B)
  - Session 4 ✅ April 22, 2026 (worked throws, four-dim signature,
    compromised states)
  - HAJ-20 / 35 / 36 ✅ April 21, 2026 (debug overlay, defensive
    desperation, grip-presence gate)
  - HAJ-31 through HAJ-34 ✅ Session 4 QA hotfixes
- Phase 3 — Calibration (current)
  - Grip-as-cause architectural refactor ✅ shipped
  - Godot calibration tool (HAJ-150 + HAJ-160s) — active
  - Watching matches at scale, tuning thresholds via the tool
  - HAJ-68 audit gaps (golden score, direct hansoku-make,
    time-expiration event) — Ring 1 polish list
  - Session 5 next (queued)

**Ring 2 — Worldgen and Legends**
- Not yet started. Largest single subsystem in the project.
- Will likely break into: Phase 1 Foundation (state vector, year-tick,
  abstracted resolver v0, NJ geography, era data), Phase 2 Population
  (procgen senseis, judoka, lineage data, dojo lifecycle), Phase 3
  Resolver Calibration (abstracted vs. deep engine agreement), Phase 4
  Cross-Discipline (BJJ, wrestling, boxing gravitational pull),
  Phase 5 Chronicle (legends-rendering, procgen template library,
  history-book UI), Phase 6 Fog-of-War + Handoff (player handoff
  flow, opening choices).
- Phase ordering and session breakdown to be detailed in the Ring 2
  full spec, drafted from `one-year-of-worldgen.md` as the seed.

**Ring 3 — The Dojo Deep-Dive**
- Not yet started. Inherits previous Ring 2 design body.
- Will likely break into: Phase 1 Foundation (calendar, roster
  notepad, basement opening), Phase 2 Sessions (session composition +
  watched-randori), Phase 3 Inner Lives (conversations + visibility +
  needs/goals), Phase 4 Lifecycle + Economy (lifecycle, antagonist —
  now worldgen-rolled, pricing), Phase 5 Cultural Inputs (six inputs
  functional + reputation propagation back into Ring 2), Phase 6
  Lineage Surface (the in-dojo half of the lineage data; the worldgen
  half lives in Ring 2).
- Some v17 answers will need revision once Ring 2 is concrete.

**Ring 4 — Narrative Event Framework**
- Not yet started. Sits on top of Ring 3, shapes Career Mode.
- Phase 1: Event triggering/sequencing infrastructure + first event
  (Twins Arrive opening).
- Phase 2: Inheritance Event + dojo-switching support.
- Phase 3: First Team Tournament + antagonist arc events.
- Phase 4+: Marriage / Children / Olympics / Succession events.

**Ring 5 — Adventure Mode (play-as-judoka)**
- Post-1.0 / Hajime 2.x direction.

**Ring 6 — Visual Layer / Ring 7 — Sound**
- Post-EA polish.

---

## THE SHIPPING PLAN

*Updated May 4, 2026. Replaces the April 23 2–3 year horizon with a
3–4 year horizon under the worldgen reframe. Drops the January 9, 2027
hard ship date (already dropped April 23) and reframes the personal
checkpoint to match the new ring structure.*

### What changed

The April 23 plan assumed the dojo loop was the bottom layer. The May 4
reframe revealed that the dojo loop is itself a layer inside a multi-
decade simulated world — the worldgen of Ring 2 is the substrate Ring 3
sits on. Worldgen is a substantial new subsystem with its own
calibration work (abstracted resolver vs. deep engine), its own
authoring work (chronicle templates), and its own architectural
commitments (state-modular pipeline, lineage data at scale, fog-of-war
progression).

The scope of the design that emerged from the May 4 reframe exceeds
what 2–3 years of solo development can ship. The new plan accepts
that and reshapes the calendar.

### The new horizon

**Early Access target: mid-2029 to mid-2030.** A 3–4 year arc from
now. Specifically determined by the rate at which Ring 2 (worldgen),
Ring 3 (dojo deep-dive), and Ring 4 (narrative events) come together.
Calendar-quartered detail sits in ongoing chat work, not in this doc
— the master doc commits to the horizon, not to specific quarter-by-
quarter milestones.

### January 9, 2027 — Personal Checkpoint, scope adjusted

The original ship date is preserved as an internal checkpoint. The
rule: *further than where I began.* By Comrade's birthday in 2027,
the project should have visibly progressed past where it is now in a
way that justifies the year's work.

Under the worldgen reframe, the proof by January 9, 2027 should be:
- Ring 1 fully calibrated (Godot tool retired, grip-as-cause settled,
  HAJ-68 gaps closed)
- Ring 2 worldgen v0 producing a browsable proto-chronicle of NJ judo
  from 1960 to present, with Cranford JKC's 1962 opening anchored,
  the abstracted resolver running, and the NJ population/geography
  pipeline producing plausible output
- An early Ring 3 sketch — calendar surface, roster notepad,
  basement-opening flow at draft fidelity
- Not public, not for sale. A working slice of the substrate that
  proves the world is real.

This is achievable in ~9 months from now if Ring 1 calibration
finishes by end of June 2026 and Ring 2 Phase 1 + 2 (foundation +
population) is the second half of 2026 plus a chunk of January 2027.
It is *not* achievable as a polished public release — and was not
going to be under the April 23 plan either. The checkpoint reframe
keeps the date emotionally meaningful without forcing the project to
bend around it.

### What ships at Early Access

- **Career Mode as the entry point**, running on top of full Ring 1
  + Ring 2 + Ring 3 + Ring 4 substrate.
- **Ring 2 (NJ worldgen)** producing a complete chronicle from 1960
  to handoff, with Cranford JKC anchored, technology and rules eras
  modeled at the chronicle level, BJJ/wrestling/boxing population
  flow active, fog-of-war progression working, and the legends layer
  authored to ~70–80% template coverage.
- **Ring 3 (dojo deep-dive)** with all six cultural inputs
  functional. Calendar, sessions (15–20 activity types), roster
  (notepad → computer transition, era-gated), conversations with
  hidden-info layer, lifecycle with quit floor, antagonist now
  worldgen-rolled with full state machine and arc, pricing as
  demographic lever, lineage data fully surfaced.
- **Ring 1 polished.** All calibration debt paid. HAJ-68 gaps
  closed. Both ne-waza and tachi-waza feel like real judo at the
  four-minute scale.
- **Ring 4 (Narrative Event Framework) with 5–8 major events.**
  Twins Arrive, Inheritance Event, First Team Tournament,
  Antagonist's Fall (or evolution), one or two recurring "two
  rising stars" dilemmas, optional Marriage arc. Late-career arcs
  (Children, Olympics, Succession) ship in EA updates through
  2029–2030.
- **Content.** Hand-built starting roster pool of 30–50 procgen
  seeds across several cultural styles. Multiple opening
  configurations driven by worldgen output (basement, mid-tier
  inheritance, struggling-buyout, established-with-Olympian).
  Tournament generator at local + state tier with national
  gestured at narratively.
- **Prose templates.** ~80% coverage of common events. Multiple
  stress registers (warm when calm, flat when tired). Cultural
  flavoring in coach voices. Chronicle template library at
  release-quality depth.
- **Visual layer.** Pixel-art top-down dojo + match views. Visible
  grip indicators. Stat panel rendering the filtered grip graph.
  Dojo facility scene that grows with upgrades. Chronicle / history
  book UI.
- **Sound.** Ambient dojo theme, match tension layers, signature
  motif for *your* finalists, archival register for legends-mode
  browsing.

### What does NOT ship at Early Access

- Additional states beyond NJ (1.x content updates: PA, CA, TX, HI,
  community-requested)
- International / country-level worldgen (Hajime 2)
- Adventure Mode / play-as-judoka (post-1.0)
- Sandbox Mode toggle (1.x update — same substrate, NEF off)
- Late-career narrative arcs in full depth (ship through 2029–2030
  EA updates)
- Olympics simulated as a real event (narrative-layer endpoint at
  1.0; full simulation post-1.0)
- Era-correct rules in the deep engine (worldgen records the era;
  the engine catches up later or never)

### Working principles for the 3–4 year build

- **Build by ring.** Ring 1 first (almost done). Ring 2 next.
  Ring 3 on top of Ring 2. Ring 4 on top of Ring 3. Don't skip
  ahead.
- **Build by phase, ship by ring.** Each phase is a committable
  slice. The ring isn't done until all its phases ship and the
  calibration debt is paid.
- **Build to scenes.** When unsure what to build next, return to
  the Anchoring Scenes — and now also to specific chronicle pages
  the designer wants to read. Build what they need.
- **Calibrate continuously.** Don't accumulate calibration debt
  across ring boundaries. Ring 1 Phase 3 calibration finishes
  before Ring 2 Phase 1 begins. The abstracted-vs-deep resolver
  calibration is its own ongoing track inside Ring 2.
- **Cultural layer hooks stay modular.** Cranford-lineage
  implementation, sensei collaboration, deeper sensei-style
  content all stay optional and modular. Conversation about
  deeper involvement happens post-Ring 4.
- **State-modular from day one.** Ring 2 is built so PA / CA / TX
  / HI are content additions, not architectural rebuilds. Don't
  let NJ-specific shortcuts harden into the pipeline.
- **Keep Player Two warm but closed.** Hajime gets all primary
  creative attention. Player Two ideas get noted in its repo and
  the chat returns to Hajime.

---

## DESIGN DOCUMENTS

*Living reference files. Read before building their corresponding
ring.*

**Ring 1:**
- `data-model.md` — Judoka class spec (Identity / Capability /
  State).
- `grip-graph.md` — Bipartite state structure, edges, multi-turn
  chains, throw prerequisites, coach IQ visibility.
- `grip-sub-loop.md` — The continuous micro-cycle that drives the
  graph.
- `biomechanics.md` — Five physical variables and how they feed
  each ring.
- `physics-substrate.md` — Body state, force model, throw
  templates, compromised states, skill compression, counter-window
  state regions.
- `grip-as-cause.md` — The architectural shift from grip-as-gate to
  grip-as-cause. Refactor shipped; doc retained as design record.

**Ring 2 (worldgen and legends):**
- `master-doc-patch-2026-05-04.md` — The patch that landed the ring
  reorder, state-modular commitment, and fog-of-war principle.
  Decision-of-record for the May 4 reframe.
- `one-year-of-worldgen.md` — *landed.* First-cut spec for the atomic
  unit of worldgen output. Seed for the full Ring 2 spec.
- `resource-model.md` — *landed.* Four-resource economy
  (attention-hours, energy, health, money), derivative reputation
  model, aging curve, family layer, and trade-off pairs. Underlying
  spec for the scheduling UI and the resource-driven shape of a
  multi-decade career.
- *Pending:* full Ring 2 spec extending `one-year-of-worldgen.md`
  and `resource-model.md` with the abstracted resolver's calibration
  plan, the legends-rendering authoring strategy, the state-module
  architecture, the fog-of-war mechanics, and the technology/rules
  era handling.
- `lineage-system.md` — *downstream of the Ring 2 spec, not alongside it.* Lineage data model load-bearing for worldgen; expanded scope under the May 4 reframe, to be drafted after the full Ring 2 spec lands.

**Ring 3 (the dojo deep-dive):**
- `dojo-as-institution.md` — Calendar, sessions, roster,
  conversations, lifecycle, antagonist (now reframed to worldgen-
  rolled), pricing, six cultural inputs, attendance signal, weekly
  roundup, facility progression, sponsorships. Some sections will
  need revision once Ring 2 is concrete.
- `cultural-layer.md` — 13 national styles as seeds, style_dna
  inheritance, seminars, school demographics, coach voice
  compatibility.
- `dojo-loop-design-questions-v17.md` — The triage doc from the
  v17 reshape. Open sub-questions live here until Ring 3 begins;
  parked under the May 4 reframe but still valid.
- `dojo-loop-design-questions-v18.md` — Continuation triage from
  late April / early May.

**Ring 4 (narrative event framework):**
- `career-mode-and-narrative-events.md` — *new doc, pending.*
  Narrative Event Framework, event library (revised under the May 4
  reframe — twins, Inheritance Event, antagonist arc all become
  worldgen-grounded), triggering/sequencing infrastructure, branch
  text patterns, either-choice-is-okay implementation, scope by EA
  vs post-EA.

**Ring 5+ / parallel:**
- `play-as-judoka-mode.md` — Adventure Mode sketch. Post-1.0.

**Research / canonical references:**
- `The Chair, the Grip, and the Throw` (coaching bible) — National
  fighting styles, Matte window research, referee behavior, prose
  voice reference.
- `From Tissue Layers to Tatami` — Dwarf Fortress combat / grapple
  architecture and what translates to Hajime.
- `Judo Biomechanics for Simulation` — Kuzushi, couples, levers
  research.
- `Cranford five-video synthesis` — Sensei lineage video analysis.
  Modular hooks for post-Ring 4 deeper involvement.

---

## RELATIONSHIP TO PLAYER TWO

*Updated May 4, 2026. The April 15 framing was "Hajime earns the tools
for Player Two." The April 23 reshape upgraded that to "Hajime is
actively building Player Two's psychology layer earlier than planned."
The May 4 worldgen reframe upgrades it again — Hajime is now also
building Player Two's world-substrate architecture.*

Hajime remains the primary project through Early Access. Player Two
remains paused. The two projects are architecturally related, and
Hajime's build now *directly* advances Player Two — by skill transfer,
by building Player Two's psychology architecture, and by building
Player Two's world-substrate architecture.

### What Hajime is building that Player Two needs

**The psychology layer (immediate needs + long-term goals + emergent
goal evolution).** Built in Ring 3 as the student inner-lives mechanic.
Direct lift to Player Two's character interiority.

**The relational data model.** Now scaled up under worldgen.
Lineage-aware data on every entity (sensei, dojo, student) at the
state-population scale — thousands of entities, all linked. Player
Two's relational substrate (the boy's life thread intersects the
grandmother's, the grandmother's intersects the teacher's) becomes
much easier to build at smaller scope after Hajime builds it at
larger scope.

**The hidden-information principle.** Visibility-as-earned-information
as a core mechanic — needs, goals, preferences, lineage, history all
hidden by default and revealed through play. Player Two needs the
same thing.

**The continuous-simulation-with-zoom architecture.** Football
Manager-style time-scaling with event-pause infrastructure, now
running across both the dojo loop and the worldgen substrate. Player
Two needs the same thing for life-scale simulation across years and
decades. Hajime builds the engine.

**The narrative-event-on-top-of-simulation pattern.** Ring 4's
Narrative Event Framework — scripted scenes layered on top of
emergent simulation, branching with no morally graded answers.
Player Two's choice-prompt architecture is the same problem in a
different content domain.

**The worldgen-as-substrate pattern (new under May 4).** A
multi-decade procedural simulation that produces the world the
player walks into, with sparse legend-events and dense statistical
output. Player Two doesn't need a state of NJ judo, but it does
need a generated history that gives the boy's life its texture —
who his ancestors were, who lived in his town, what events shaped
the place. Hajime now ships this architecture before Player Two
needs it.

### What changes about the resumption plan

When Player Two resumes (no specific date — when Hajime EA ships
and the horizon is clear), it will be even less of a from-scratch
project than the April 23 framing suggested. It will be a port of
Hajime's psychology, relational, visibility, simulation-zoom,
narrative-event, *and worldgen-substrate* architectures into a
different content domain. The scope of "build Player Two" drops
substantially. The scope of "design Player Two's content and prose"
remains what it always was.

### Working model

- Hajime has all primary creative attention through EA.
- Player Two's repo stays closed during Hajime sessions.
- Player Two's design documents remain valid and untouched.
- Ideas that arrive belonging to Player Two are noted in Player
  Two's repo as quick capture and the chat returns to Hajime.
- After Hajime EA, the resumption decision gets made deliberately.
  By that point, Player Two's hardest architectural problems will
  already be solved.

The April 15 decision protected future-Comrade from second-
guessing the priority. The April 23 reshape strengthened it. The
May 4 reframe strengthens it further: 3–4 years on Hajime is no
longer "earning the tools" or even "building the psychology
layer." It is *building most of Player Two's substrate*. The ROI
on Hajime time has gone up again.

---

## WHAT'S BEEN BUILT

**Ring 1 — Phase 1 Skeleton ✅** April 13, 2026.

**Ring 1 — Phase 2 Real Combat ✅** April 14–22, 2026.
- Session 1 (April 14): throw resolution, scoring, fatigue,
  match-end conditions.
- Session 2 (April 15): grip graph, position state machine,
  ne-waza door, Referee.
- Session 3 (April 17): physics substrate design (Mode B,
  design-only).
- Session 4 (April 22): worked throw templates, four-dimension
  signature, worked throw instances, failed-throw compromised
  states, skill-compression, counter-windows as state regions.
- HAJ-20 / 35 / 36 (April 21): debug overlay, defensive
  desperation, formal grip-presence commit gate.
- HAJ-31 through HAJ-34 (Session 4 QA): white-belt zero-grips
  hotfix, log event order canonicalization, counter outcome
  display, grip oscillation spam suppression. Four commits on main.

**Ring 1 — Phase 3 Calibration (in progress).**
- HAJ-68 audit completed (April 24): match-end logic gaps
  inventoried. Implemented: ippon end, two-waza-ari end, decision
  on unequal WA, third shido hansoku-make. Missing: golden-score
  transition on equal WA at time, direct hansoku-make for
  dangerous-technique/spirit violations, golden-score scoring
  win, golden-score third shido hansoku-make.
- Grip-as-cause architectural refactor ✅ shipped (late April /
  early May). Pulls now cause throws via emitted kuzushi events,
  replacing the grip-as-gate model.
- Godot calibration tool ✅ shipped under HAJ-150; ongoing
  threshold tuning via the HAJ-160s. Matches run at scale with
  thresholds tunable in a live UI.
- Session 5 queued.

**Ring 2 — Worldgen and Legends.** Not yet started in code.
Design seeds shipped May 4:
- `master-doc-patch-2026-05-04.md` — ring reorder, state-modular
  commitment, fog-of-war principle.
- `one-year-of-worldgen.md` — atomic unit spec.

**Design corpus.**
- `data-model.md` v0.4
- `grip-graph.md` v0.1
- `grip-sub-loop.md` v0.2
- `biomechanics.md` v0.1
- `physics-substrate.md` v0.1
- `cultural-layer.md` v0.1
- `dojo-as-institution.md` v0.2 (now Ring 3 work; expansion
  pending and partially recast under May 4)
- `grip-as-cause.md` (refactor shipped; design record)
- `play-as-judoka-mode.md` v0.1 (now Ring 5)
- `dojo-loop-design-questions-v17.md` (parked under May 4)
- `dojo-loop-design-questions-v18.md` (parked under May 4)
- `master-doc-patch-2026-05-04.md` (NEW)
- `one-year-of-worldgen.md` (NEW)
- Coaching bible (research)
- Tissue layers (research)
- Cranford five-video synthesis
- Three Gemini prompt templates (QA, elite match, instructional)

**Tooling.**
- Linear for ticketing (HAJ- prefix, GitHub auto-close via
  commit magic words).
- Two-tier Gemini-assisted video analysis workflow for
  calibration ground truth and ticket synthesis.
- Debug overlay for live calibration observation.
- Godot calibration tool (HAJ-150) for tunable threshold work.

---

## WHAT'S NEXT

*Updated May 4, 2026. The headline move is that Ring 2 (worldgen) is
now the next major design and build target, replacing the previous
"expand `dojo-as-institution.md`" priority. Ring 1 calibration
continues in parallel.*

Ordered by priority for the immediate cycle:

1. **Master doc rewrite** ✅ (this doc — current).

2. **Linear restructure for the new ring order.** New milestone /
   cycle / quarter framing for the 3–4 year horizon. Reshape
   projects to reflect the worldgen Ring 2 + dojo Ring 3 split.
   Keep Ring 1 calibration tickets where they are. Park v17 dojo-
   loop sub-question tickets behind a Ring 3 epic. Triage HAJ-68
   gaps into tickets. Proposal-first; full restructure on green
   light.

3. **Ring 2 full spec.** Extend `one-year-of-worldgen.md` into the
   full Ring 2 design document. Cover the abstracted resolver's
   calibration plan, the legends-rendering authoring strategy
   (the biggest hidden cost), the state-module architecture, the
   fog-of-war mechanics, the technology/rules era handling, the
   handoff flow and opening choices, and the cross-discipline
   gravitational-pull model. This is the next major design
   artifact.

4. **`lineage-system.md` rewrite.** Now load-bearing for Ring 2
   rather than a forward-compatibility hedge. Spec the
   chronicle-grade lineage data model the worldgen needs at
   state-population scale.

5. **`dojo-as-institution.md` recast.** Park the in-flight
   expansion. When Ring 3 begins, recast the doc to (a) inherit
   the surviving v17 work and (b) defer to Ring 2 for the
   antagonist, the Inheritance Event, and the recognition-walk-in
   mechanics.

6. **`career-mode-and-narrative-events.md` (Ring 4 spec).** Drafts
   after the Ring 2 spec stabilizes. Event library reflects
   worldgen-grounded versions of Twins, Inheritance, antagonist
   arc.

7. **`cultural-layer.md` light update.** Extend the six-cultural-
   inputs framing to acknowledge worldgen senseis as cultural-
   feedback-loop participants alongside the player.

8. **Design notes cleanup.** Sessions / plans / templates folder
   is getting crowded. Pass to consolidate, archive completed
   sessions, prune templates that have outlived their use.

9. **README rewrite** (eventually — after the doc layer settles).

10. **Session 5** (Ring 1 calibration work, queued).

11. **HAJ-68 gap implementation.** Golden score, direct
    hansoku-make, time-expiration event. Lands as Ring 1 Phase 3
    work.

12. **Ongoing Godot calibration tool work.** HAJ-160s and follow-
    ups. Continue until Ring 1 calibration debt is paid.

---

*Document version: May 5, 2026. Substantial rewrite from the April 24
version. Reflects the May 4 worldgen reframe (`master-doc-patch-2026-
05-04.md` + `one-year-of-worldgen.md`), the new ring structure
(Ring 2 = Worldgen and Legends; Ring 3 = Dojo Deep-Dive; Rings 4–7
shifted), the 3–4 year shipping horizon (mid-2029 to mid-2030 EA
target), the personal-checkpoint scope adjustment, the "legends are
the game" tagline, and the upgraded relationship to Player Two.
Snapshot of the April 24 version saved at
`design-notes/archive/hajime-master-doc-2026-04-24-snapshot.md`.
Update after the next session that meaningfully changes scope or
structure.*
