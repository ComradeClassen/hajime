# Ring 2 — Worldgen and Legends, Full Spec (v2)

*Drafted May 7, 2026, following four review conversations against v1.
The body has been substantially revised: five architectural commitments
now (was three), the worldgen presentation has been promoted from open
question to commitment, the physical dojo as chronicle surface has been
named as load-bearing rather than aesthetic, the calibration substrate
has been clarified as a shared development artifact between Ring 1 and
Ring 2, and the mentor tutorial has replaced basement-from-scratch as
the default first-run experience. Several v1 open questions are closed.
Several new ones are surfaced. The structure has shifted from five parts
to six to accommodate the additions cleanly.*

*v1 is preserved as `ring-2-worldgen-spec.md`. This is its superset.*

---

## What this document is

The full specification for Ring 2, the worldgen and legends layer of
Hajime. It extends `one-year-of-worldgen.md` (the atomic unit of
worldgen output) and `resource-model.md` (the resource economy) into
the system that runs the unit across 66 years and produces the world
the player inherits.

This v2 absorbs four review conversations after the v1 draft. The
substantive additions:

The calibration corpus is now specified as a belt-grid triangular
coverage matrix (Black5 vs Black5 down through Yellow, etc.) and is a
shared development artifact between the Ring 1 deep engine and the
Ring 2 abstracted resolver, not a Ring-2-only structure. The five
abstracted-resolver dimensions (tachiwaza, ne-waza, conditioning,
fight IQ, signature strength) are now defined rather than just named.
Golden score is named as a Ring 1 prerequisite for calibration, not
something to fold in later.

Worldgen is now a visible presentation by default — a New Jersey map
that populates from 1960 forward with dojo icons (Kodokan emblem for
judo, Gracie triangle for BJJ, crossed gloves for boxing, wrestlers
grappling for wrestling) as the cultural landscape evolves. The
campaign opens with a 1960 cold open: the announcement that judo will
be at the 1964 Tokyo Olympics, framed as a radio broadcast or
newspaper clipping. The visible worldgen is now Commitment 4.

The opening-choice menu has committed to difficulty profiles per
option, and the default first-run experience has shifted from
basement-from-scratch to a mentor-tutorial — a relationship-rolled
older sensei (father, uncle, brother, family friend, first sensei)
who is near retirement, runs a working dojo, and teaches the player
the dojo loop's mechanics in their full context before retiring or
dying. The mentor's death is a scripted Anchoring Scene candidate
with the dedication ceremony and portrait-on-the-wall mechanic.

Procgen portraits for every chronicle-active judoka, group photos as
a first-class chronicle entry type, the dojo's walls as a spatial
memory surface, and the visual-Easter-eggs principle (cohort members
bowing to a deceased member's photo in the daily-grain layer) are
named as Ring 2 commitments and the dojo as physical chronicle has
been promoted to Commitment 5.

The cohort tracking system has been promoted from a chronicle indexing
structure to a load-bearing retention mechanic in the dojo loop —
white belts who walk in alongside peers stay; isolated white belts
walk away. Cohort cohesion is a per-student state contributing to
retention probability and surfacing on the roster UI.

The nationality tag system replaces the open question on era-specific
population evolution. Every character carries a nationality (or
hyphenated American nationality), cities have nationality
distributions weighted by real demographic data per era, and the
chronicle's prose templates carry slot-pool variants that surface
this texture without commentary.

The senior-student-return mechanic has been refined: returnees roll an
"absence trajectory" that determines what they carry — time-enriched
in some dimensions, time-degraded in others, with an IQ-modulated
recovery rate.

Indefinite play past the 66-year horizon is now an option. Time
freezes culturally (no new technology eras, no new rule cliffs) but
human-level texture continues. The 2.0 recommendation language nudges
players toward starting fresh.

The Cranford anchor is locked: dojo name fixed at Cranford JKC,
founding date fixed at 1962, founding sensei's surname uses a Y.Y.-
shape Japanese rendering with rolled given name, everything else
procgen per campaign. The Y.Y. surname carries the personal anchor as
an Easter egg legible to those who know and as a normal Japanese name
to those who don't.

A new section names three story-type wells (technique-discovery,
person-stories, diseases-and-injuries) as the texture sources the
legends-rendering layer renders against. The legends-rendering
authoring section now provides a worked grid structure (entry type ×
tier band × era × N variants), with multiple example templates per
entry type, and a 500–900-template scope estimate for 1.0.

The operational discovery layer is named as a Ring 3 mechanic that
intersects with Ring 2 at specific points (procgen senseis carry
operational legacies in their chronicles; first-encounter triggers
are Ring 4 narrative events; era-flavored variation feeds back into
the technology-era system).

A few additional small changes throughout: the tier ladder is revised
from eight to nine tiers (sub-state regional becomes its own tier),
the 1960 initial state numbers are revised down to 3–8 dojos
(reflecting the actual pre-Olympic era), the 1964 Olympic-driven and
1969–72 returning-competitor waves are named as worldgen events
explicitly, the 40-year minimum runway is recommended (with slider-
and-warning shape for shorter windows).

That is what's new. Read order remains: master doc patch, then
`one-year-of-worldgen.md`, then this document. `resource-model.md` is
referenced throughout.

This spec gates the next year of work. Push back on what's wrong;
push on what's underdeveloped. The next document after this is the
scheduling UI working from the resource model.

---

## Part I — The Architectural Commitments

Five commitments now organize Ring 2. They were arrived at across the
four design conversations following v1 and they are not open for
revision in this draft. Every system in the spec supports them.

### Commitment 1: The dojo is the persistent thing; the character is the temporary thing

The simulation is dojo-centered and continuous. Every dojo in the
simulated state is a persistent entity that runs from its founding
date to its closing date or to the end of the campaign window.
Cranford JKC opens in 1962 and runs continuously across multiple
sensei generations, founder retirements and successions, facility
moves, name changes, the entire arc of the dojo's life as an
institution.

The player's character — the sensei the player is currently piloting
— is a window into that dojo. The character has a finite arc: thirty
to sixty in-game years from when the player picks them up to when
they retire, hand off, or die. The character is the lens. The dojo is
the world behind the lens.

This is the architectural commitment that organizes Ring 2's data
model. Saves store the dojo and the world it sits in, not the player
character. The character is a pointer into the dojo's roster —
specifically, the pointer to the entity flagged as "currently piloted
by player." When that pointer moves (succession, perspective-switch
in a future content update, end-of-campaign new run), the dojo
persists.

This commitment dissolves several earlier design tensions. The
dojo's records page becomes obvious — it's the player's dojo's
chronicle view, accumulated across generations of player characters.
Succession in 1.0 becomes a perspective-switch rather than a
save-and-restart. The multi-generational lineage data the seed doc
named as load-bearing for worldgen pays for itself a second time as
the substrate that succession needs.

When this spec uses the word "dojo," it means the persistent
institution. When it uses "character" or "sensei being piloted," it
means the temporary lens. Keep the distinction clean.

### Commitment 2: Tick is grain, not speed

The simulation runs atomically at weekly resolution. Every system in
Ring 2 — the abstracted resolver, the chronicle writer, the
population-flow model, the resource economy, the family-event roller,
the federation politics layer, the cohort retention mechanic, the
operational discovery layer's drift — operates on weekly state
transitions. The week is the irreducible unit of time.

The player does not always see weeks. The player chooses calendar
grain from a menu: daily, weekly, monthly, quarterly, yearly. The
"advance" button steps forward by the chosen grain by running multiple
weeks underneath. A monthly advance runs four weeks of simulation and
presents the result as one observation. A yearly advance runs 52
weeks. The simulation underneath is identical regardless of grain;
the player's view changes.

Calendar-anchored events interrupt advance regardless of grain.
Tournaments the player's dojo has competitors in, belt promotions,
narrative events from the Ring 4 framework, board meetings the
player has accepted invitations to, family events (child-birth,
child-interest-reveal, adult-choice points), boycott events firing
during Olympic cycles that affect the player's competitors, sensei
transitions in dojos the player has relationships with, mentor's
death week if the player is in the tutorial period, any chronicle
event the worldgen tags as high-salience to the player's current
visibility tier — all interrupt.

When an interrupt fires, the advance halts at the week the event
occurs and the player gets the event presentation. After resolution,
the player chooses to continue advancing at the same grain or switch
grain.

Pacing target. A full white-to-black-belt cohort cycle is roughly six
to eight in-game years. The design target is that this maps to ten to
twenty hours of real-time play for a player engaging at default grain
with normal interrupt frequency. At default weekly grain, this yields
roughly 60 to 120 seconds of real time per simulated week. Watched
scenes — Ring 1 randori the player is observing, Anchoring Scene
moments — expand the felt pace. Yearly advances through quiet
stretches collapse it. The grain system is the player's primary tool
for managing their own engagement curve.

The choice of grain has a second-order effect that surfaces only late
in development: the daily-grain player sees visual Easter eggs the
weekly-grain player misses. See Part V on visual Easter eggs.

### Commitment 3: Reports are legends-layer views

There is no separate report system. The yearly, five-year, and
ten-year reports are higher-resolution views into the same chronicle
data the worldgen produces for every dojo in the world. The player's
dojo and a stranger's dojo are read through the same renderer; the
player's dojo is just turned to a higher resolution.

The first yearly report fires automatically at the end of the
player's first in-game year as a teaching moment. It interrupts
advance and presents itself with brief framing text. Future reports
generate silently and sit in the History menu until the player
requests them.

When the player switches perspective, the previous dojo's reports
remain in the world's chronicle. The new character can read what was
previously their privileged view as a normal reader at the appropriate
(lower) resolution. The chronicle was always written at multiple
resolutions; the player's access privilege just moved.

### Commitment 4: Worldgen is theater, not loading

This commitment was an open question (WG-A) in v1 with a default
toward silent worldgen. It has flipped.

The campaign opens with a 1960 cold open. The screen presents a brief
historical framing — the announcement that judo will be at the 1964
Tokyo Olympics, presented as a radio broadcast snippet or a newspaper
clipping headline, with restrained 1960s typography. *"Tokyo, Japan.
The International Olympic Committee has announced that judo will
debut as a medal sport at the 1964 Summer Olympic Games."* The framing
text rolls. Then the New Jersey map appears.

Three to eight founding-generation dojos populate the map at their
real geographic locations, each with a brief textual roll fading in
beside its icon: a one-or-two-sentence biography of the founding
sensei. *"Tetsuo Watanabe, born Yokohama 1923, opened a dojo in
Newark in 1958 after teaching judo at the Buddhist Temple."* *"Frank
Mitchell, U.S. Army, trained 1947–1951 at the Kodokan, opened in
Trenton in 1961."* These are the apostolic generation. Most dojos
that will exist in the player's eventual handoff year trace back to
one of them.

The map then begins ticking forward. Each year takes roughly one to
three seconds at default presentation speed (with a configurable
slider, and a skip-to-handoff option for players who want fast).
Dojo openings spawn icons at their geographic locations. Dojo
closings remove them. Cross-discipline gym openings appear with the
appropriate icon — wrestlers grappling, crossed gloves, eventually
Gracie triangles in the late 1990s.

The 1964 Olympic spike shows visibly: a cluster of new judo dojos
opening in 1964 and 1965 that would otherwise be silent. The 1969–72
returning-competitor wave shows visibly: a second cluster opening as
competitors who participated at Tokyo and Mexico City finish their
careers and turn to coaching. The 1990s BJJ explosion shows visibly:
the first Gracie triangles appear in late-90s Newark and Jersey City,
expanding rapidly through the 2000s and 2010s as judo dojos thin
slightly in the same regions. The 2010 leg-grab ban shows as a quiet
cultural shift — perhaps a brief tonal change in the map's visual
treatment, perhaps a one-frame note flagging the rule change.

By the time worldgen completes at the player's chosen handoff year,
the player has watched 60+ years of NJ judo history happen visually.
They are invested in the world before they have made a single
decision. The cultural-pull mechanic is no longer abstract — they
have seen the BJJ schools spread, they understand viscerally why
their judo students will be tempted to migrate.

Cranford appears in 1962 as one of the earliest icons. The player
will see it appear before they know it is the player's anchor, which
is correct — it lands in the chronicle as a real founding event, not
as a UI tutorial.

The implementation is bounded. The map is geometry data (real NJ
counties, towns, population centers). The icons are simple sprites.
The placement logic reads chronicle dojo-opening events and renders
them at their stored locations. The animation is "advance simulation
by one year, render new chronicle events as visual events on the
map, wait briefly, advance again." Probably two to four weeks of
focused work for a working version, plus polish over time.

The case for theater over loading: the worldgen pivot is the
project's load-bearing commitment, and the visible worldgen sells the
pivot to anyone who watches a trailer or a devlog episode. It is the
moment-of-magic that "the legends are the game" tagline is promising.
A silent worldgen and a chronicle-only handoff is honest. A visible
worldgen with the map populating before the player's eyes is theater
— the CK3 zoom-out into the Mediterranean as worldgen completes is
one of the best opening moments in the genre. Hajime gets its own
version.

The first devlog episode now has two candidate set-pieces: the moment
the first match renders visually in Godot, and the moment the
worldgen map first populates with NJ judo history. Both are real
"this is the game" moments.

### Commitment 5: The dojo is a physical chronicle

The player's dojo is not just a roster, a calendar, and a financial
ledger. It is a physical space rendered in 2D, with walls, with mats,
with benches and equipment, with portraits and photographs hung on
the walls, with belts in glass cases, with the visible accumulation
of decades of training across its surfaces.

This commitment makes the dojo a *spatial* memory surface, not just a
data surface. The chronicle is not only a History menu; it is also a
wall the player walks through when they enter their own dojo. Every
champion belt hung in a glass case, every portrait of a deceased
mentor, every group photograph from a tournament or seminar or
anniversary, is a chronicle entry rendered as architecture.

A player who has piloted Cranford JKC across four sensei generations
walks into a dojo whose walls are covered in portraits and belts
going back to 1962. The dojo-as-sediment principle landing as
architecture rather than data. This is texture no abstract records
page can produce because it is encountered spatially — the player
walks past their lineage, they don't browse it.

This commitment requires four supporting systems, all of which are
specified in Part V: the procgen portrait system (every chronicle-
active judoka has a portrait), the group-photo entry type (a major
chronicle entry type, with composite rendering on dojo walls), the
visual Easter eggs principle (cohort members bowing to deceased
members' photos in the daily layer), and the hyperlinking of photos
into the chronicle (hovering or clicking on a face in a photo opens
that judoka's chronicle entry).

Visitors to the player's dojo can react to specific photos. *"That's
[name] in your 1982 photo. We competed against each other at the
Pan-Ams. He was tough."* A visiting sensei recognizes someone in the
wall. Reputation effects, conversational hooks, and narrative-event
triggers become possible against the photo-as-data structure. This
is a 1.0+ enrichment, not a 1.0 commitment, but the substrate ships
in 1.0 to make it cheap to add.

These five commitments — dojo persistent, tick is grain, reports as
chronicle views, worldgen as theater, dojo as physical chronicle —
are the architectural north for everything that follows. They
organize the rest of the spec.

---

## Part II — The Substrate

This part specifies the systems that all of Ring 2 sits on top of:
the chronicle data structure with its photo and cohort entry types,
the abstracted match resolver with its five-dimension definitions,
the shared calibration corpus that ties Ring 1 and Ring 2 together,
the state-module architecture with its regional and demographic data,
and the seed-roll-to-handoff pipeline.

### The chronicle data structure

The chronicle is the world's memory. It is the substrate that
legends rendering reads from, that reports filter into views, that
the fog-of-war system reveals layers of, that succession reads when
deciding who can plausibly take over a dojo, that the cultural
feedback loop writes its sediment into, that the dojo's physical
walls render their photographs from. Everything in Ring 2 that
persists between weeks lives in the chronicle.

The chronicle is composed of **entries**. Each entry has a year-and-
quarter (or week-stamp where relevant), an entry type, one or more
actor pointers into the world's entity table, a location reference,
a structured payload, an era tag, a rules-era tag where relevant, a
resolution level, and a visibility flag set populated as the player's
fog-of-war state evolves.

The entry types for 1.0:

- `tournament_result` — match outcomes at any tier
- `belt_promotion` — first-time-this-belt-rank promotions
- `dojo_opening` — a new dojo founded
- `dojo_closing` — a dojo closes
- `sensei_transition` — death, retirement, succession at a dojo
- `student_migration` — a notable student moves between dojos or to a
  cross-discipline gym
- `senior_return` — a former student returns after a long absence
- `cross_dojo_seminar` — a notable visiting sensei teaches at a dojo
- `coaching_defection` — a high-profile assistant leaves dojo X for Y
- `boycott_affected` — Olympic-tier judoka recorded as qualified-but-
  did-not-compete during a boycott year
- `child_birth` — a child is born to a sensei or judoka in the
  worldgen
- `notable_death` — a chronicle-active judoka dies (natural causes,
  accident, or in rare cases tragedy in their judo career)
- `photo_event` — *new in v2.* A group photograph is taken at a
  notable occasion (tournament, seminar, anniversary, promotion).
  See *Photos as architectural memory* in Part V.
- `cohort_formation` — *new in v2.* A new cohort is established as a
  set of students enrolling within a 12-month window. See *The cohort
  retention mechanic* in Part IV.
- `operational_event` — *new in v2.* Something happened in the dojo's
  operations that a chronicle reader should know — a ringworm
  outbreak, a piece of equipment broke, the mats were replaced. See
  *The operational discovery layer* in Part IV.

Roughly twelve to fifteen distinct entry types. Each will need its
own template library in the legends-rendering authoring effort (see
Part IV).

The chronicle is **indexed**. By year. By dojo. By individual. By
tier. By type. By location. By cohort. Reports are queries across
these indices — "give me every entry where dojo equals Cranford JKC
and year equals 1987" returns the data the 1987 yearly report
renders. "Give me every entry where actor includes [former-student-X]
and year is greater than 1995" returns what the History menu shows
when the player clicks on a former student to see their post-
departure career. "Give me every entry where cohort equals
(1985, Cranford-JKC)" returns the data a five-year retrospective
needs to surface a cohort's collective trajectory.

#### Resolution levels

Not every entry is written at the same depth.

- **High resolution.** The full payload. All structured slots filled.
  Era-appropriate textural details. Tier-appropriate gravity. The
  player's dojo writes high-resolution entries; tier 6+ matches write
  high-resolution entries everywhere because they are globally
  legible; notable upsets are tagged for high resolution at the
  moment of resolution.
- **Medium resolution.** Structural information — who, what, when,
  where, the result — without the texture. A tier-3 county tournament
  result in 1978 in a county the player has never visited gets a
  medium-resolution entry.
- **Low resolution.** A bare flag that something happened. Most
  entries in the chronicle are low resolution. Aggregate.

The resolution level is set at write time. The legends-rendering
budget is what high resolution costs. Most entries cost only
structured data.

#### Visibility flags

Each entry carries a flag set indicating which fog-of-war tiers can
read it. Not stored as redundant data; computed on read by querying
the player's current fog state against the entry's tier and other
relevant fields. Fog state advancement is a single update to the
player's view state, not a global rewrite.

#### Cohort tracking as a first-class entity

In v2, cohorts are first-class chronicle entities, not just an
indexing convenience. Each cohort has: a formation date and dojo, a
roster of members (pointers into the world entity table), a cohort
cohesion state (per-member, decays as members leave or advance
ahead, contributes to retention probability), a cohort lineage tag
(do later cohorts at this dojo trace back to this one through the
sensei's coaching style and signature evolution), and the chronicle
entries about this cohort across its life.

A new student enrolling at the dojo gets attached to either an
existing cohort (if their belt level and recent-enrollment state
match a current cohort's profile) or to a new cohort (if no current
cohort is a fit). Attachment biases the student's retention
probability immediately. A white belt walking into a roster of green
and brown belts with no matching cohort gets attached to a one-person
cohort with low cohesion; their retention probability is correspondingly
lower until either another white belt arrives to share their cohort
or the lone white belt accumulates enough other reasons to stay
(strong relationship with sensei, hidden goals being met, family ties
to the dojo).

This matters in Part IV. It is named here because it is a chronicle
data structure commitment.

#### The player's dojo is not architecturally special

The chronicle structure is the same for Cranford JKC and for the YMCA
judo program in Trenton. The differences are that the player's dojo's
entries are written at high resolution by default, and that the
player's view privileges them in default queries. Switch the player's
character to a successor or, in a future content update, to a
different dojo entirely, and the chronicle structure is the same —
what changes is which dojo's entries are queried at high resolution.
No separate code path.

### The abstracted match resolver

The deep engine — the Ring 1 match simulator — is too expensive to
run for off-screen matches. Worldgen needs a lightweight resolver
that produces results consistent enough with the deep engine that the
world feels coherent across the abstracted-deep boundary.

The resolver is a probabilistic comparison between sparse skill
vectors. Each judoka in the worldgen has a five-dimensional skill
vector. A match takes two judoka, weights their vectors by tier,
applies a calibrated variance term, and returns: winner, loser, score
type (ippon / waza-ari / decision / hansoku-make), match duration in
seconds (a rough bell-shaped distribution around a tier-appropriate
mean), and an optional notable-tag flag.

#### The five dimensions, defined

In v2 the five dimensions are defined rather than just named.

**Tachiwaza.** Standing competence. Absorbs grip-fighting skill,
kuzushi creation, throw entry, throw completion, and standing
defense. Hand strength is a feeder into tachiwaza, not a separate
dimension — strong hands help win grip exchanges, but a judoka with
strong hands and bad fight IQ still loses grip exchanges to a smarter
opponent. A high-tachiwaza judoka wins grip exchanges, generates
kuzushi efficiently, finishes throws cleanly, and defends against
opponents' throw attempts. Most judoka have moderate tachiwaza;
elites have very high values.

**Ne-waza.** Ground competence. Pins, chokes, joint locks,
transitions, escapes. Architecturally separate from tachiwaza
because the skill profiles diverge in the population — there are
pure ne-waza specialists (the BJJ-curious judoka of the 2000s and
2010s) and pure tachiwaza specialists (classic competitive judo
through the 80s and 90s). A high-ne-waza judoka can stall and grind
weaker ground opponents into pins, and can escape from ground
positions other judoka would have to tap out of.

**Conditioning.** The fuel tank. Cardio, muscular endurance, recovery
between rounds and between matches in a tournament day. Distinct
from raw strength (which feeds tachiwaza/ne-waza). A strong but
poorly-conditioned judoka can throw hard for ninety seconds and gas;
a well-conditioned but technique-light judoka can outlast their
opponent and win on shidos. Conditioning's impact on outcome
escalates with match duration. It is the dominant dimension in
golden-score scenarios and is one of the larger contributors at
late-tournament matches when the judoka has already fought two or
three rounds that day.

**Fight IQ.** The strategic and tactical layer. Reading opponents,
choosing techniques, managing tempo, recognizing when to commit and
when to defer, exploiting weaknesses identified mid-match. Composure
folds in here rather than getting its own dimension; an inability to
stay composed under pressure reads as fight IQ failing under load.
Fight IQ is the dimension that produces upsets — a moderate-skill
judoka with high fight IQ beating a higher-skill opponent by
out-thinking them. It also drives all the matchup-dependent texture
that makes the deep engine interesting; the abstracted resolver
doesn't simulate this at depth, but it weights fight IQ when biasing
upset probability and decisive-moment selection.

**Signature strength.** How finished and reliable the judoka's
primary techniques are. Two judoka with identical tachiwaza scores
can have very different signature strengths — one has a broad but
shallow toolkit, one has a devastating uchi-mata they hit at 60%
completion rate against any opponent in the world. Signature strength
produces the *"their uchi-mata is unstoppable"* texture in the
legends layer. It is also why some judoka rise specifically at the
higher tiers — at tier 7 and 8, signature reliability matters more
than total skill breadth.

Each dimension is a value in roughly the [0.0, 1.0] range, with the
distribution skewed strongly low (most judoka are mediocre at most
things; elites are rare).

#### Tier weighting

A tier-1 dojo internal weights tachiwaza and conditioning heavily;
fight IQ and signature strength matter less because matches are
short and unsophisticated. A tier-7 international circuit match
weights all five dimensions but heaviest on fight IQ and signature
strength because those are what distinguish elites from sub-elites.
The weighting per tier is a small calibration table — nine tiers
(see *Tier ladder* below), five dimensions, forty-five numbers to fit.

#### The variance term

The upset-rate dial. Calibrated to produce upsets at a rate consistent
with what the deep engine produces on the same skill vectors. In
practice this is a normal distribution added to the skill comparison
with a standard deviation tuned per tier.

#### The notable-tag heuristic

One match per tournament gets flagged notable on average. The flag
is more likely on tournament finals, matches where a significantly
lower-ranked judoka beat a significantly higher-ranked one, matches
in late rounds where the skill gap was narrow, matches involving
judoka with unusual hidden-trait combinations, and matches the
player's dojo participates in (regardless of result). When notable,
the match gets a high-resolution chronicle entry; otherwise medium
or low depending on tier.

### The shared calibration corpus

This is one of the substantive v2 revisions. The corpus that
calibrates the abstracted resolver is *the same corpus* that
calibrates the Ring 1 deep engine. Both engines share a single
ground-truth set of matchups, and the corpus is a development
artifact maintained jointly across both engines' development cycles.

The structure is a triangular belt-grid coverage matrix. With roughly
ten belt levels (white, yellow, orange, green, blue, brown, black 1
through 5), the unique-pair triangle has 55 cells. Each cell is a
belt-level pairing — Black5-vs-Black5, Black5-vs-Black4, Black5-vs-
Brown, ..., down to White-vs-White. Each cell needs roughly four to
six matchups within it, varying along secondary axes (different
signature throws, different ne-waza specialists, different
conditioning profiles, different fight IQ levels) so the cell is not
just a single matchup repeated. Total corpus size: 200 to 350 matchups.

The two engines consume the corpus differently:

**Ring 1 calibration uses the corpus to verify rank-gap behavior in
the deep engine.** Does Black5 reliably beat Yellow? Does Black5 vs
Black4 stay competitive? Does the variance feel right at each gap?
Does golden score, when it fires, weight conditioning the way the
design wants? When does a match enter golden score, and does the
distribution of when match? The corpus is what HAJ-150 and its
successors are checking the deep engine's outputs against.

**Ring 2 calibration fits the abstracted resolver to the deep engine's
outputs on the same corpus.** Run a corpus matchup through the deep
engine many times to get an outcome distribution. Run the same
matchup through the abstracted resolver and check that it produces a
consistent distribution within tolerance. Adjust the abstracted
resolver's parameters until the match.

One corpus, two consumers, one set of ground-truth matchups. The
corpus is how the two engines stay in agreement over time.

The tolerances:

- Win probability for any matchup: ±5% between the two engines.
- Score-type distribution (ippon / waza-ari / decision split): ±10%
  on each category.
- Duration distribution mean: ±20 seconds, with shape roughly
  bell-shaped around it.

These tolerances are loose because the two engines do not need to be
identical. They need to be statistically equivalent. A player who has
watched twenty deep-engine matches has internalized a distribution
of outcomes that the worldgen's results need to fall inside, not a
specific outcome they need to predict.

#### Golden score as a Ring 1 prerequisite

In v2 this is a named prerequisite. If golden score is not modeled in
the deep engine before the calibration corpus runs, conditioning is
systematically under-weighted — because the matches that go to
overtime are exactly the matches where conditioning matters most, and
those matches don't exist in a no-golden-score deep engine. The
abstracted resolver gets fitted to a deep engine missing one of
conditioning's primary load-bearing scenarios, and then in actual
play, golden-score matches the abstracted resolver produces use a
conditioning weight calibrated against a world where conditioning
didn't matter as much. It would skew.

The golden-score implementation, sketched (this belongs in a Ring 1
ticket, not in this spec, but is named here as the prerequisite):
match continues until first score after regulation, all penalties
accumulated during regulation persist (three shido equals
hansoku-make, can fire in golden score), conditioning's contribution
to decision-making escalates (high-conditioned judoka press;
low-conditioned judoka try for desperate ippon attempts and risk
being countered), tactical behavior shifts away from defensive
shido-baiting and toward technique commitment.

Calibration cannot proceed until this is in place. File the ticket
in Ring 1's backlog with a clear "Ring 2 calibration depends on
this" note.

#### The development tooling

The calibration is not a one-time event. It is ongoing infrastructure.
Every Ring 1 calibration update risks invalidating the abstracted
resolver's fit; every change to the resolver's tier weighting or
variance term risks drifting away from the deep engine's outputs.
The two engines need to be re-calibrated against each other on a
regular cadence.

This requires development tooling. The right shape: a side-by-side
calibration interface — a tool window where the developer picks a
matchup from the corpus, sees what the deep engine produces (over
many runs to get distributions), sees what the abstracted resolver
predicts, sees the divergence, adjusts the resolver's parameters with
sliders or numerical inputs, watches the prediction update, runs the
full corpus and gets aggregate divergence metrics with one button.

This probably extends the Godot calibration tool already in
development under the HAJ-150 line, rather than being a separate app.
Same UI conventions. Same Python-data backend. The calibration
interface is part of the dev environment, not a one-time fitting
script.

Budget: probably one to two weeks for an initial version of the
side-by-side tool, plus ongoing maintenance as the engines evolve.
This is substrate work, not Ring 2-specific work. The calibration
tooling is a permanent part of the development environment.

#### Calibration phases

**Phase 1 — Build the seed corpus.** Construct the 200 to 350 matchups
spanning the belt-grid triangular matrix. Run them through the deep
engine. Record outcomes: winner, score type, duration distribution.
This is the calibration ground truth.

**Phase 2 — Fit the abstracted resolver.** Hand-tuning likely
sufficient for 1.0 — the parameter count is small, the corpus is
small. If precision becomes an issue, escalate to analytic
optimization (least-squares fit on residuals).

**Phase 3 — Validate on a holdout set.** Generate another 50
matchups not in the corpus, run both resolvers, check distributions
match within tolerance.

**Phase 4 — Re-calibrate when either engine changes.** The hidden
ongoing cost. Run the corpus through the deep engine after every
Ring 1 calibration commit and check whether the abstracted resolver
still hits tolerance. If yes, no action. If no, hand-tune back into
tolerance. Half a day per Ring 1 calibration cycle.

**Phase 5 — Fold in tier-specific and era-specific behavior over
time.** Deferred until needed. The 1.0 calibration treats all matches
as modern-rules matches and stamps the era on the entry rather than
simulating it.

#### What the resolver doesn't do

Doesn't simulate technique selection at the per-throw level. Doesn't
model grip exchange, kuzushi, the counter-window state regions, the
body-state vector, or any of the architecture making Ring 1 the deep
engine. Produces aggregate match outcomes consistent with what the
deep engine would produce on the same inputs, nothing more.

Doesn't produce coaching prose for matches. The notable-tag triggers
a chronicle entry; the legends-rendering layer fills that entry's
prose slot from a template library at chronicle write time.

Doesn't run the player's own matches. When the player watches a
match, the deep engine runs. The resolver runs everywhere else.

#### Federation rule variation

USJF, USJA, USA Judo, and AAU have had slightly different rule
interpretations over the years. Modeling these as variations against
the IJF baseline is plausible. The cost is real: each variant needs
its own style-distribution adjustment in the abstracted resolver, the
deep engine needs rule-set flags for matches the player watches at
federation events, and the legends layer needs to understand which
federation a tournament was sanctioned by.

The benefit is texture — *"Cranford competed at USJF events but never
USA Judo events because Y.Y.-sensei didn't agree with their 1985 rule
package"* is a real legends-layer beat.

Honest call for v2: defer to a content update. The 1.0 model treats
federations as having reputation but not their own rule variants;
rule changes come from the IJF era timeline. Federation-specific
rule drift is enrichment, not load-bearing.

### The state-module architecture

The 1.0 commitment is that Hajime ships with New Jersey as the only
simulated state. Subsequent updates ship additional states as content
expansions: Pennsylvania, California, Texas, Hawaii, others as the
community requests them. For this to be a content commitment rather
than an engineering commitment, the worldgen must be parameterized
over a state module.

A state module is a set of data files (and possibly a small amount of
state-specific code for unusual cases) specifying everything
state-specific about the worldgen. The worldgen engine itself does
not change between states. Adding a state is content work.

Architecturally, all 50 states are feasible. The bottleneck is data
authoring per state — geography, demographics, cultural profile,
naming pools, federation seeds, historical inflection points. A few
days of focused work per state for someone who knows the state. The
community contribution model is interesting here: a player who knows
Pennsylvania judo could plausibly draft the PA module themselves and
submit it. That is post-1.0 ecosystem work, not a 1.0 commitment.

A state module specifies:

**Geography.** County boundaries (or equivalent administrative units).
Population centers and their populations across the worldgen window.
Real population data is available for U.S. states from census records
back to 1960; using it gives each state's worldgen the right urban /
suburban / rural distribution. Per-decade interpolated for
in-between years.

**Sub-state regional partition.** *New in v2.* Each state has a
regional structure that becomes a tier in the fog-of-war ladder.
NJ has its specific regions — South Jersey, Central Jersey, Jersey
Coast, North Jersey, Northwest. Pennsylvania has its own
(Philadelphia metro, Pittsburgh metro, Central PA, etc.). California
has its own (Bay Area, LA, Central Valley, San Diego). The state
module specifies the partition. The fog-of-war system reads it.

**Cultural profile.** Wrestling intensity (NJ very high, California
medium, Hawaii low). Boxing intensity. BJJ adoption timing and
intensity (varies by state). Regional preferences for specific judo
styles. Modulates the population-flow model and the cultural
feedback loop.

**Historical inflection points.** State-specific events. Most are
rare — most worldgen events are national or regional. Modeled as a
small list of fixed-history events that fire in the appropriate year
if the state module is loaded.

**Naming conventions.** What names get rolled for procgen entities.
NJ draws from Italian-American, Polish-American, Irish-American,
Black, Korean, Latin American, and Japanese-American naming pools
weighted by real demographic distribution. California draws from a
different mix. Hawaii draws from a different mix again.

**Demographic distributions per city per era.** *New in v2.*
Connected to the nationality-tag system (see below). Each population
center has a per-era nationality distribution. Newark in 1970 is
heavy on Italian-American, Black, and Polish-American populations;
Newark in 2020 looks different. The distributions drive who walks in
to dojos in each city and which nationality slots fire in chronicle
entries.

**Fixed anchors (if any).** NJ has Cranford JKC. Other states may or
may not get analogous fixed anchors. Pennsylvania probably doesn't.
Hawaii might. The state module declares zero or more fixed anchors,
each specifying location, founding date, and any fixed-shape
information.

**Federation seeds.** The four procgen federations rolled per state
have different rivalry patterns and naming conventions per state.

**National-event interaction.** Most national or international events
— the 1980 boycott, IJF rule changes, Olympic cycles — apply
uniformly across all state worldgens. National events live outside
any state module.

#### The nationality tag system

Every character in the worldgen has a nationality (or hyphenated
American nationality). Italian-American, Japanese-American,
Korean-American, Black, Latin American, Polish-American, Irish-
American, Brazilian-American, Russian-American, and so on. The tags
drive name-pool selection at character creation and feed slot-pool
selection in chronicle templates.

Cities have nationality distributions weighted by real demographic
data per era. Newark in 1970 is heavy on Italian-American, Black, and
Polish-American populations; Newark in 2020 looks different. Jersey
City has its own distinct profile. Cherry Hill has another.

When a new student walks into a dojo, their nationality is rolled
from the dojo's local population's nationality distribution. A
Cranford JKC roster that has been mostly Italian-American and
Polish-American for two decades suddenly gets a Korean-American
student walking in. The chronicle entry carries the slight
unusualness — *"[name], the dojo's first Korean-American student,
started in March 1985."* No commentary, no editorial weight, just
the honest noticing.

Later entries can reference this. *"By 1992, Cranford JKC's roster
reflected the changing demographics of Union County, with [name]
training a generation of Korean-American competitors who would later
anchor the state's [weight_class] field."*

Real American judo history is a story of changing demographics —
early Japanese-American teaching cohorts handing off to first-
generation American students, the late-century arrival of Russian and
Eastern European immigrants bringing sambo-influenced styles, the
ongoing Brazilian connection through BJJ adjacency. The nationality-
tag system models all of this without modeling it explicitly. It
ships the data and lets the chronicle render it.

Implementation cost is small. A single field on the character data
structure. A demographic distribution per city per era as part of
state-module data. Naming pools per nationality (already needed for
naming work). Slot-pool variants for chronicle templates that
reference nationality where relevant. One to two weeks of design
work plus the data authoring, incremental on the existing state-
module work.

#### What makes adding Pennsylvania a content task

Concretely, post-1.0 PA addition means: writing PA geography and
sub-state regional partition data, writing PA's per-decade population
numbers, writing PA's cultural profile (wrestling intensity high,
BJJ adoption medium), writing the historical inflection points list
(probably short), writing PA's nationality demographic distributions
per city per era, writing PA naming pool weightings, deciding on
fixed anchors (probably none), writing the federation seed shape, and
testing by running a few PA campaigns to verify the worldgen output
feels Pennsylvania-shaped. None of this requires changes to the
worldgen engine, the chronicle structure, the abstracted resolver, or
the legends-rendering templates.

#### Save format

Each campaign loads exactly one state module. Saves are state-bound.
Adding a new state in a content update does not affect existing
campaigns in other states. National rankings within each state
include plausible representation of other states as a sparse procgen
layer. To play another state, the player starts a new world. There
is no multi-state campaign mode in 1.0.

### The seed-roll → 1960 → handoff pipeline

How a campaign starts. The pipeline phases:

**Phase A — Seed roll.** A seed value, either user-provided or
randomly generated, determines the entire campaign. Same seed
produces the same campaign byte-for-byte. Critical for shareability,
debugging, and replay.

**Phase B — 1960 cold open.** *New in v2.* Before any worldgen
ticking, the campaign opens with the 1960 historical framing — the
announcement of judo at the 1964 Tokyo Olympics, presented as a brief
period-appropriate interstitial. This sets the campaign's emotional
ground. Then the New Jersey map appears.

**Phase C — 1960 initial state generation.** *Numbers revised in v2.*
NJ judo in 1960 was small — three to eight dojos statewide (revised
down from v1's five to fifteen), almost entirely run by first-
generation Japanese-American practitioners and a small number of
WWII-era servicemen who'd trained in occupied Japan. The 1960 state
generator places these dojos with population-density weighting.
Rolls senseis with appropriate background profiles for the era.
Generates roughly 100 to 300 active practitioners statewide, with
skill distributions skewed strongly low. Rolls the initial federation
entities with seed names and starter rosters of officials.

Cranford JKC does not exist in 1960. It opens in 1962 as a
deterministic insertion. The state generator reserves Cranford as a
location.

The brief textual rolls of each founding sensei — one or two
sentences of biography per dojo — fade in beside their icons on the
map. The player reads them as the worldgen ticking begins.

**Phase D — Year-by-year worldgen run.** *Now visibly rendered to the
map per Commitment 4.* Run the year-tick from 1960 forward. Each
year produces chronicle entries that render as visual events on the
map. The 1964 Olympic-driven dojo wave shows visibly; the 1969–72
returning-competitor wave shows visibly; the 1990s BJJ explosion
shows visibly; the 2010 leg-grab ban shows as a quiet cultural shift.

Cranford JKC is born in 1962 as the deterministic insertion. The
founding sensei is generated with the fixed Y.Y.-shape Japanese
surname (Yashima Yonezu, Yoshi Yazuke, or similar two-initial
rendering) and rolled given name, rolled competitive attributes,
rolled coaching style, rolled lineage origin, rolled personal
trajectory across decades. Everything else about Cranford JKC's
history is rolled by the worldgen alongside every other dojo.

The full run produces, for an average campaign, roughly 1500 to 3000
chronicle entries above low-resolution threshold across decades.

**Phase E — Handoff state assembly.** When the run reaches the
handoff year, the worldgen packages the current world state, the
chronicle, and the opening-choice menu derived from worldgen output.

**Phase F — Opening-choice presentation.** Present the player with
their options. See Part III on the opening menu's revised structure
with difficulty profiles and the mentor tutorial as the default
first-run experience.

#### The 40-year minimum runway

*New in v2.* Recommended default handoff is present-day, giving 66
years from 1960. The slider allows handoff anywhere from 2000 forward.
A soft warning fires if the player picks a window under 40 years —
the world will feel younger, with shallower lineages, fewer
multi-generational arcs, and a sparser chronicle. Players who want
the frontier-feeling world that comes from a shorter runway can
still pick it. The system informs; it does not block.

The 40-year reasoning is structural. Below 40 years, there has not
been enough time for procgen entities to develop multi-generational
depth, for legends to accumulate enough texture, for two full sensei
generations to cycle through a dojo. The world reads as freshly
minted rather than inhabited.

#### Indefinite play past 66 years

*New in v2.* The 66-year ceiling is recommended, not enforced. A
player can continue past handoff year indefinitely. The architecture
supports it: the year-tick worldgen unit is the same regardless of
which year is running.

What freezes: technology era stays at smartphone (no new tech eras
are authored beyond present-day). Rules era stays at the latest IJF
rule set. Some texture flattens because there are no new cultural
inflection points to render.

What continues: people are born, people compete, people retire,
people die, dojos open and close, lineages extend, cohorts form and
disperse, nationality demographics shift gradually within the
distributions modeled. The chronicle keeps accumulating. A player
who runs Cranford JKC for 150 years gets a chronicle the size of two
normal campaigns and a fourth or fifth sensei generation under the
same dojo.

When 2.0 ships with new content (additional technology eras, rule
updates, new state modules, new authored anchoring scenes), a
recommendation appears to players still running pre-2.0 worlds.
Suggested language: *"This world has continued past its natural
horizon. Future content updates may add new technology or rules eras;
for now, time has frozen culturally even as years pass. Consider
starting a new world to experience future content updates fully."*
Players who want to keep going get to keep going. Players who want
fresh experiences are nudged toward starting over. Neither path is
blocked.

#### Time budget for the worldgen run

On modern hardware running a sparse-vector resolver across roughly
5000 entities and 80 dojos for 66 years, the worldgen run is probably
30 seconds to 3 minutes depending on optimization. With the visible
presentation slowing this to a per-year tempo of one to three seconds,
the visible run lasts somewhere from one to three and a half minutes.
A skip-to-handoff option compresses this for replay players. First-
time players should be encouraged to watch — it is theater.

---

## Part III — The Visible Worldgen and the Opening Choice

This part specifies the campaign-creation experience: the visible
worldgen presentation in implementation detail, the opening-choice
menu with difficulty profiles, and the mentor tutorial as the default
first-run experience.

### The visible worldgen in implementation

Per Commitment 4, the worldgen is theater. The implementation has
five components:

**The map.** New Jersey rendered in 2D with real geography — county
boundaries, major roads or river systems for orientation, population
centers as visible-but-unobtrusive markers. The visual style is
period-appropriate to 1960 at the start: muted color palette,
slightly textured paper-map aesthetic, restrained typography. The
visual style modernizes subtly across the decades — the map's
treatment shifts as the eras tick by — but never breaks the unifying
geographic frame.

**The icons.** Four icon families render dojo and gym openings:

- **Kodokan emblem (judo)** — appears at every judo dojo opening from
  1960 forward.
- **Gracie triangle (BJJ)** — appears at every BJJ school opening.
  Rare in the 1970s and 1980s (one or two in the entire state at
  most, mostly in major urban areas where Brazilian immigration
  patterns aligned). Common from the late 1990s forward; explosive
  growth through the 2000s and 2010s.
- **Crossed gloves (boxing)** — appears at every boxing gym opening.
  Present throughout the worldgen window, more concentrated in urban
  areas.
- **Wrestlers grappling (wrestling)** — appears at every wrestling
  club opening. Present throughout, with the high-school-wrestling
  ecosystem strong in NJ across all eras.

The icons are simple sprites. Probably 64x64 pixel or vector
equivalents. Distinguishable at the map's normal zoom level. No
animation required for the icon itself; appearance and removal are
the only animations needed.

**The ticking.** The map advances one year per cycle, with the cycle
length configurable via slider (one to three seconds per year at
default presentation). Per cycle, the worldgen runs the year-tick;
chronicle events generated during the year render as visual events
on the map. Dojo openings spawn icons. Dojo closings remove them.
Cross-discipline migrations might fire a brief thin line from one
icon to another, fading. The year display in the corner advances. A
small counter in another corner shows total active dojos and total
named judoka.

**The cultural inflection moments.** Specific events get visual
treatment beyond the routine. The 1964 Olympic spike: the year
counter lingers slightly, a small text overlay reads *"1964: Judo
debuts at Tokyo Olympics,"* and the 1964–65 wave of judo dojos opens
in noticeably faster sequence. The 1969–72 returning-competitor wave:
similar treatment, with text overlay *"1969: Tokyo and Mexico City
competitors return to coaching."* The 1990s BJJ inflection: when the
first Gracie triangle appears (in Newark or Jersey City, late 1990s),
a text overlay reads *"1996: First BJJ academy opens in New Jersey."*
The 2010 leg-grab ban: a brief tonal shift in the map's treatment, a
text overlay reads *"2010: IJF bans leg grabs."*

These are restrained. They are not modal interruptions; they are
text overlays that appear briefly and fade. They give the player
historical hooks for the visual events without breaking the worldgen
flow.

**The handoff.** When the worldgen reaches the player's chosen
handoff year, the ticking stops. The map remains visible, populated
with all the dojos and gyms that exist at handoff. A brief pause —
half a second — and then the opening-choice menu fades in over the
map.

#### Skip-to-handoff option

Players who do not want to watch worldgen render — replay players,
players who have already seen it once and are starting their fifth
campaign — can skip. The skip option is a button visible during the
ticking. Clicking it jumps the worldgen to handoff completion in one
step (probably 30 seconds to 3 minutes depending on optimization,
same time as a hidden worldgen would have taken). The map remains
visible after; the player did not skip the result, just the
animation.

A dedicated re-watch option in the History menu lets players replay
any past worldgen for any seed, in case they want to revisit a
notable world's accumulation.

### The opening-choice menu

When worldgen completes and the menu fades in, the player sees three
to five options derived from worldgen output. Each option has a
difficulty profile that gestures at what is hard about it. The
options are populated by what the worldgen actually produced — the
inheritance option presents a specific worldgen-rolled retiring
sensei, the buy-out option presents a specific worldgen-rolled
struggling dojo with its specific reputation baggage. The structure
is curated; the content is procedural.

The five canonical options for 1.0:

**Mentor tutorial (first-run default).** A small dojo with an aging
sensei who is the player character's mentor — relationship-rolled at
character creation. The sensei is near retirement or close to dying.
The player takes over the dojo gradually over the tutorial period.
*Difficulty: gentle introduction, narratively supported.* See *The
mentor tutorial* below for full mechanics.

**Basement from scratch (legacy default).** Empty space, no students,
no inherited reputation, no inherited assistant, no inherited
schedule. The player builds everything. *Difficulty: highest pure
difficulty, lowest narrative weight.* Slow burn. The cultural
feedback loop runs on a small enough surface that the player can see
how each decision plays out.

**Inheritance.** A worldgen-rolled retiring sensei at a mid-tier dojo
hands off to the player. The sensei has spent decades building this
place. The player inherits a working dojo, a partially defined
schedule, a small student roster, a reputation in their community,
and the sensei's relationships with neighboring dojos, federation
officials, and former students. *Difficulty: medium. The player
inherits a working machine and must avoid breaking it.* Most
inheritances arrive with a request — keep teaching the senior
students, keep the kids' class running on Tuesday and Thursday, don't
let the bench-press corner fall apart. Honoring or revising those
requests is the player's choice.

**Buy-out.** A struggling dojo with reputation baggage. The previous
sensei did something — folded under financial pressure, quit after a
federation dispute, lost students to a rival — and the player
inherits the consequences. The chronicle records what happened. The
player can read the dojo's recent history and decide whether to lean
into that narrative or actively try to reframe the dojo's reputation.
*Difficulty: medium-high. Inherited problems are visible from day
one.* This option is narratively rich; the worldgen has done the
authoring work for the situation already, and the player is dropped
into a story-in-progress.

**Established dojo.** A large, well-established dojo with an Olympian
or near-Olympian on the roster. Twenty-five-plus students. Existing
schedule with assistant coaches who have their own opinions.
Existing pricing, existing federation relationships, existing
rivalries with nearby dojos. High revenue but high expenses. The
challenge isn't survival — it's not collapsing the inherited
institution under the weight of its own complexity. *Difficulty:
overwhelming. Most options for first-pass play.* Recommended only
after the player has run at least one campaign at lower difficulty
to learn the dojo loop's rhythms.

A small dojo in a low-population area is structurally a sub-variant
of either the mentor tutorial, the basement, or the inheritance —
depending on whether there is an existing sensei, whether the player
is starting empty, or whether the player is taking over. The
geographic-monopoly dynamic (no competitor for thirty miles, but very
narrow recruitment pool) is rolled into whatever the parent option
is.

For first-run players, the mentor tutorial is the default and the
other options are visible-but-not-recommended. For subsequent runs,
all five options are equally available with their difficulty
profiles displayed.

### The mentor tutorial

*New in v2 as the replacement for the v1 first-run-locked-to-basement
default.* The substantive design move is that the tutorial is
narratively grounded rather than abstract. The tutorial gym is a
small, near-retirement dojo run by a sensei who is the player
character's mentor.

#### The relationship roll

At character creation, the player picks the relationship between
their character and the tutorial sensei. The mechanical role is the
same; the narrative weight varies. Options:

- **Father.** The classical setup. The sensei is the player
  character's father, who taught them judo from childhood.
- **Uncle.** A close family relative who became their sensei. Common
  in family-dojo lineages.
- **Older brother / older sister.** A sibling who is significantly
  older and has been their sensei since they could walk.
- **Family friend.** A man or woman who became close to the player's
  family and took the player under their wing.
- **First sensei.** The first sensei the player ever trained under,
  unrelated by blood but binding through years of training. The
  pure-judo version of the relationship.

Each option produces the same mechanical tutorial. The narrative
prose differs — the mentor's commentary references the relationship
appropriately, and the death-of-mentor anchoring scene plays out with
the right emotional weight.

The relationship-roll matters because many players' relationships to
fathers are not the right register for this material. Letting the
player pick the relationship that fits the story they want to tell is
respectful and produces broader appeal.

#### The mentor's mechanics

The mentor sits in the dojo. He is older — late sixties to early
eighties. He is in his retirement period, still teaching but at
reduced output. He is visibly aging across the tutorial.

He demonstrates each of the dojo loop's basic mechanics across
several in-game weeks. He shows how to schedule. He shows how to coach
during randori (the watched-randori surface activates with him
commenting on what he sees). He shows how to set up training routines
and what kinds of training affect what skill dimensions. He shows
how to sign students up for competitions and prepare them for weigh-
ins. Each is a single-session tutorial beat.

After the basic mechanics are taught, he transitions to passive
presence. He stays in the dojo. He is available for limited weekly
questions — two or three per week, refreshing weekly, not
accumulating. The player goes to him with specific questions: *"Hey,
what kind of move does this improve?"* *"What does this drill
develop?"* *"How do I prepare a student for their first competition?"*
He answers. The questions cost a small slice of attention-hours from
the player's budget — choosing to spend Tuesday afternoon sitting
with him is choosing not to spend it on the schedule or recruitment
or paperwork. The choice means something.

A player who advances at weekly grain through the tutorial period
gets many more conversations with him than a player who advances at
monthly grain. Both are valid. Both produce different relationships
with the mentor. The player who skipped through his last six months
at monthly grain may regret it when he dies, which is exactly the
texture this mechanic should produce.

#### Era-bridging commentary

The mentor's commentary track is era-aware. Whatever era the
campaign opens in, the mentor's experience extends back further. He
remarks on technology: *"Back in my day I had to use a notepad and
calendar."* If the player simulates forward through an era transition
during the tutorial period, he comments on the change with surprise:
*"What is this, an email?"* *"I had to use a fax machine."* *"How does
this thing know who's coming on Thursday?"*

The commentary works for *other* long-tenure characters too. A senior
student who has been at the dojo since the 1970s remarks on the 1990s
arrival of the first dojo computer. A returnee who left in the 1980s
and comes back in 2015 spending a few weeks visibly catching up to
the modern world. Era-bridging commentary becomes a general mechanic
for differentiating long-memory characters from short-memory ones.

When the mentor dies, the commentary track dies with him. That is
not just narrative loss — it is a felt absence. The player gets used
to him noticing things, and then he stops noticing things, because
he is gone.

#### The mentor's death

The mentor's death is a scripted Anchoring Scene candidate. The week
of death is rolled within a window during the player's first few
in-game years (suggested: between in-game year 2 and year 5 of the
campaign, with weighting that puts most occurrences in years 3 and 4).

The scene: the mentor's death is announced. The dojo's regular
schedule pauses for a week. The dedication ceremony happens during
the player's normal visit to the dojo — students gather in the main
training space, all bow in unison toward where the mentor used to
sit, and the player chooses (with the senior students' input) where
to hang the mentor's portrait on the wall. The portrait is procgen-
generated based on the mentor's face data and is permanent — it
hangs on the dojo wall for the rest of the campaign.

This is one of the strongest Anchoring Scene candidates in the entire
project. It is scripted enough to land reliably; rolled enough that
the timing varies; emotionally weighted by the player's choice of
relationship; chronicle-recording enough to seed everything that
comes after (cohort members bowing to the photo, returnees in 2015
asking about him, the new sensei watching the portrait and making
their own decisions about what hangs next to it).

#### The retired-sensei-as-masters-competitor

*New in v2 as a refinement of the second-career taxonomy.* If the
mentor retires from active dojo duty without dying — voluntary
retirement triggered by a player choice or by the mentor's health
crossing a threshold short of death — and his health and energy state
permit, he can continue as a masters-tier competitor. The worldgen
rolls this branch as one of the second-career taxonomy options
(branch 6 or a sub-branch of branch 1), modulated by health/energy
at retirement.

The new sensei (the player) pilots the dojo. The old sensei
occasionally appears at masters tournaments. The new sensei can
attend their old mentor's masters matches. This produces a specific
authority inversion — the old sensei is no longer teaching the new
sensei to coach; they are showing up as a competitor and asking the
new sensei to coach *them* through their masters matches.

A scripted Ring 4 event where the retired mentor asks the new sensei
for coaching at a masters championship is the kind of scene the
design-by-story principle wants to generate.

When the mentor finally dies — at an older age, having extended his
career as a masters competitor — the dedication ceremony happens
then. The mentor figure has been the tutorial character not just for
the first few months but for years.

#### The mentor's chronicle preamble

Before the player's first week of play, the mentor's career is
written into the chronicle as preamble. The player can read his pre-
1964 lineage if any (was he trained by one of the apostolic
generation?), his founding of the dojo in some year between 1962 and
1980, his decades of students, his major tournaments, his federation
relationships, his most successful former students, the major
departures from the dojo across his tenure, the operational legacy he
leaves behind. The player's character starts the campaign already
weighted with the mentor's history. The History menu's first entries
are him.

#### Cost

The mentor tutorial is a more authored experience than basement-
from-scratch. It requires writing the mentor character with at least
baseline depth, scripting the tutorial beats, integrating the
worldgen-rolled history with the scripted teaching moments, the
dedication ceremony, the era-bridging commentary library, and the
optional retired-sensei-as-masters-competitor extension. Probably
two to four weeks of focused work plus iteration. Worth it. This is
the tutorial that teaches the dojo loop's mechanics in their full
context (a working dojo with real students, real schedule, real
history) rather than in the artificial simplicity of an empty
basement. It also seeds the lineage system from the very first hour
of play in a way that pays off in every subsequent succession the
player makes.

---

## Part IV — Player-Facing Systems

This part specifies what the player interacts with day-to-day: the
fog-of-war system, the technology and rules era handling, the
legends-rendering authoring strategy with its grid structure and
worked examples, and the reports system.

### Fog-of-war mechanics in implementation detail

The fog-of-war progression is the player's main extra-belt
progression curve. Belt advances mark personal student development;
fog unfogging marks the player's reach extending into the world. Two
independent curves.

The world is fully generated underneath, from the first week of the
player's first year. The chronicle contains complete data through
handoff and accumulates new entries each week. What changes is the
player's *legibility* of that data.

#### The revised tier ladder

*Revised in v2 from eight to nine tiers.* Sub-state regional becomes
its own tier:

1. **Dojo internals.** Twice-yearly invitationals, Saturday open-mats,
   in-house promotion tests.
2. **Local / town and city.** Town tournaments, multi-dojo round-
   robins. Kids' first away tournaments.
3. **County.** USJF/USJA county events. Most students who compete at
   all reach this tier.
4. **Sub-state regional.** *New in v2.* For NJ: South Jersey,
   Central Jersey, Jersey Coast, North Jersey, Northwest. Each state
   module specifies its sub-state regional partition. Regional events
   are a structural step between county and state, and serve as the
   geographic bridge between local and state-level competitive
   identity.
5. **State.** State championships. Where strong dojos start to know
   each other's senior students by name.
6. **National.** U.S. Senior National Championships, Junior Nationals,
   Master's Nationals, U.S. Open, National Sports Festival
   (1978–1995).
7. **Continental.** Pan American Championships, Pan American Games,
   Pan American Open. Liverpool World Cup tier events.
8. **International circuit.** Grand Prix series, Grand Slam series,
   Continental Opens, World Cup events.
9. **World and Olympic.** Junior World Championships, Senior World
   Championships, Olympic Games.

Master's circuit runs in parallel as a separate progression layer,
not a separate tier.

#### The visibility spectrum

Each tier has a visibility state for the player's view: fogged,
rumored, visible-low-resolution, visible-high-resolution. See v1 spec
for the full descriptions; v2 retains them unchanged.

#### Triggers for advancement

Same as v1. Tier N fogged → rumored when the player's dojo first
produces a competitor at tier N-1 who places (top three) or wins.
Rumored → visible-low-res when the player's dojo first sends a
competitor to a tier-N event regardless of result. Visible-low-res →
visible-high-res with sustained presence (three-plus student-
tournament-appearances at tier N spread across at least two years).
Tier 9 stays rumored even when the player's competitor qualifies for
the Olympics; advances to visible-low-res only when they actually
compete (boycott implication preserved); advances to visible-high-res
only on an actual medal.

#### Revelation density per tier

Suggested rough defaults, to be calibrated by playtest:

- Tiers 1–4 inclusive: roughly 30 entries per year statewide.
- Tier 5 (state): adds 20 entries per year.
- Tier 6 (national): adds 50 per year.
- Tier 7 (continental): adds 20 per year.
- Tier 8 (international circuit): adds 30 per year.
- Tier 9 (world / Olympic): adds 5 per year.

These will need playtest. Too many entries per tier and the History
menu becomes overwhelming once the player unfogs. Too few and the
world feels thin when the player reaches it. Open question (OQ-2 in
v2).

### Technology and rules era handling

Each chronicle entry stamps its era at write time. The legends-
rendering layer reads the era stamp and selects era-appropriate
vocabulary, technology references, and contextual details from the
template library.

Concrete examples of era effects in legends prose. A 1973 tournament
result references newspaper coverage and word-of-mouth spreading the
news. A 2003 result references a brief mention on the dojo's
website. A 2018 result references social media virality. Same
tournament, same structural payload, different era stamp, different
prose template selected.

The roster surface is era-gated. Notepad in Paper-and-Radio.
Notepad-or-early-spreadsheet in Phone-and-Fax. Computer in Email-
and-Web and Smartphone. Facility upgrades act as multipliers within
an era.

Information flow era effects are mechanical. Paper-and-Radio: rankings
beyond direct attendance unknown unless explicitly investigated.
Phone-and-Fax: phone networking unlocks partial visibility at small
attention cost. Email-and-Web: the player can subscribe to email
lists and see most rankings passively. Smartphone: information is
fast and asymmetric; viral randori clips can reshape reputation
overnight.

Rules era handling: each match entry stamps its rules era. Pre-2010
worlds produce more leg-grab finalists. Post-2010 don't. The
abstracted resolver biases style distribution by era. The deep
engine modeling era-correct rules at depth is post-1.0 work.

In v2, the technology era system also drives the operational
discovery layer's era-flavored variation (see Part V): 1965 ringworm
prevention is a bottle of bleach and a mop; 2010 mat hygiene is a
whole industry of antimicrobial cleansers.

### Reports as legends-layer views

Per Commitment 3, reports are not a separate authoring effort. They
are higher-resolution views into the same chronicle data the worldgen
produces for every dojo in the world.

Yearly reports generate at year-end, filtered to the player's dojo at
high resolution. The first yearly fires forced as a teaching moment;
subsequent yearlies sit in the History menu.

Five-year retrospectives generate at five-year marks. Higher-level
summary. Cohort outcomes are a primary surface (cohort tracking
shipping from start makes this work).

Ten-year legacy reports generate at ten-year marks. The big picture.
Lineage tree extensions, sensei career arc summary, cultural sediment.

Cross-perspective continuity per Commitment 3: when the player
switches perspective, the previous dojo's reports remain in the
world's chronicle and the new character can read them as a normal
observer.

---

## Part V — Legends-Rendering Authoring

This part is substantively expanded in v2. The 1.0 commitment is
templated-only prose. The grid structure, worked examples, tonal
targets, and authoring scope are all specified.

### The commitment

*Templated procgen prose, no LLM rendering.* Reasons:

The templated approach is proven. CK3 and DF have demonstrated that
well-authored templates produce output that feels narrative at scale.
The first hundred chronicle entries don't show repetition; the first
thousand do, but by then the player has invested hundreds of hours
and the repetition reads more as formal grammar than machine output.

LLM rendering introduces dependencies that complicate distribution
(model files, system requirements, network requirements), introduces
support cost, and is opaque to debugging. For a small-team labor-of-
love project that needs to ship reliably, templated wins.

The hybrid approach (templated baseline, LLM-rendered headlines)
remains available as a 2.0+ option. The chronicle data structure is
the same regardless. The legends-rendering interface is "give me prose
for this entry." Adding hybrid in 2.0 is a new implementation behind
the same interface. The templated work is not wasted.

### The grid structure

For each entry type, the authoring work fills a grid with three axes:

- **Tier band** — low (tiers 1–3), mid (tiers 4–6), high (tiers 7–9).
  Some entry types collapse this to a single band where tier doesn't
  apply (a child-birth entry doesn't have a tier).
- **Era** — Paper-and-Radio (1960–1985), Phone-and-Fax (1985–2000),
  Email-and-Web (2000–2015), Smartphone (2015+). Some entry types
  collapse this where era effects don't apply.
- **Variant index** — three to five distinct templates within each
  cell, so the same entry doesn't read identically across a long
  chronicle.

Slots within templates draw from era-bound or context-bound phrase
pools. A `[result_propagation_phrase]` slot has different fills in
different eras: *"reported in the local sports column"* in 1970s,
*"covered briefly on the dojo's email list"* in 2000s, *"went viral
on JudoTok within hours"* in 2020s. Authoring a template is partly
authoring its slot pools.

#### Worked example: tournament_result

Tournament results are the highest-frequency entry type and serve as
the worked example.

Slots in the structured payload:
- `[year]` — pulled from entry data
- `[tournament_name]` — pulled from entry data
- `[judoka_name]` — pulled from actor pointer
- `[opponent_name]` — pulled from actor pointer
- `[dojo_name]`, `[opponent_dojo_name]` — derived
- `[score_type]` — ippon, waza-ari, decision, hansoku-make
- `[match_duration_descriptor]` — derived from match duration
- `[decisive_moment_descriptor]` — slot, drawn from decisive-moment pool
- `[career_implication_descriptor]` — slot, drawn from career-state pool
- `[result_propagation_phrase]` — era-bound slot, drawn from era pool

**Low-tier, Paper-and-Radio era, variant 1 (skeletal):**

> *"In the [year] [tournament_name], [judoka_name] of [dojo_name] beat
> [opponent_name] of [opponent_dojo_name] by [score_type]."*

Renders as: *"In the 1974 Union County Open, Marco Castellano of
Cranford JKC beat Tom Reilly of Newark Buddhist Judo by waza-ari."*

**Low-tier, Paper-and-Radio era, variant 2 (sparser):**

> *"[year] [tournament_name]: [judoka_name] over [opponent_name],
> [score_type]."*

Renders as: *"1974 Union County Open: Castellano over Reilly,
waza-ari."*

**Mid-tier, notable flag set, Email-and-Web era, variant 1:**

> *"At the [year] [tournament_name], [judoka_name] beat
> [opponent_name] in [match_duration_descriptor]. [judoka_name] won
> by [score_type] after [decisive_moment_descriptor]."*

With slots filled: *"At the 2008 NJ State Championships, Marco
Castellano beat Tomasz Kowalski in a tight five-minute match.
Castellano won by waza-ari after a late uchi-mata in the second
period."*

**High-tier, notable flag set, Smartphone era, variant 1:**

> *"The [year] [tournament_name] [weight_class] final went
> [duration]. [judoka_name] of [dojo_name] beat [opponent_name] of
> [opponent_dojo_name] by [score_type], [decisive_moment_descriptor].
> The win [career_implication_descriptor]."*

With slots filled: *"The 2019 Pan American Open -73kg final went
seven minutes. Marco Castellano of Cranford JKC beat Diego Pereira of
Garden State BJJ by ippon, a counter-throw against the cage. The win
marked Castellano's first continental title and set up a Pan-Am
qualification campaign."*

#### Worked example: sensei_transition

A simpler entry type, fewer tier variations because senseis at all
tiers transition.

**Single-tier, Paper-and-Radio era, retirement variant:**

> *"In [year], [sensei_name] retired from active teaching at
> [dojo_name] after [years_of_service]. [successor_name] took over."*

**Single-tier, Email-and-Web era, death variant:**

> *"[sensei_name] of [dojo_name] died in [year] at age [age].
> [years_of_service]. [death_circumstance]. [successor_name] took
> over the dojo."*

**High-tier (chronicle-active sensei), Smartphone era, retirement
variant with weight:**

> *"[sensei_name] retired from [dojo_name] in [year] after
> [years_of_service]. The dojo had produced [notable_accomplishments]
> under his tenure. [successor_name] took over, having [successor_path]."*

#### Worked example: child_birth

No tier banding. Era-flavored.

**Paper-and-Radio era, sensei-child variant:**

> *"[sensei_name]'s [first/second/third] child, [child_name], was
> born in [year]."*

**Email-and-Web era, judoka-competitor variant:**

> *"[judoka_name]'s [first/second/third] child, [child_name], was
> born in [year]. [judoka_name]'s competition schedule scaled back
> through [year+1]."*

**Smartphone era, twins variant:**

> *"[judoka_name]'s twins, [twin_a_name] and [twin_b_name], were
> born in [year]. [judoka_name] withdrew from the [year_competition_year]
> [tournament_name] qualifier."*

#### Worked example: photo_event

*New entry type in v2.*

No tier banding (photos exist at all tiers). Era-flavored. Captions
template against the photo's structured payload.

**Paper-and-Radio era, tournament-contingent photo:**

> *"[dojo_name]'s [year] [tournament_name] contingent. Front row:
> [front_row_names]. Back row: [back_row_names]."*

**Email-and-Web era, seminar photo:**

> *"[year] [seminar_title] at [dojo_name]. Visiting:
> [visiting_sensei_name]. Attendees: [attendee_names]."*

**Smartphone era, anniversary photo:**

> *"[dojo_name]'s [anniversary_year]th anniversary, [year]. All
> generations: [attendee_names_with_belt_levels]."*

The composite portrait rendering happens at view time when the
player encounters the photo on a dojo wall. The template's caption
becomes the photo's title text.

### Tonal targets

Calm register. English with Japanese nouns where appropriate. Technical
specificity in demonstration mode (high-tier matches, succession
descriptions, lineage retrospectives), looser register in foundational
mode (most other entries). No overwriting, no sentimentality, no
narratorial commentary that tells the player what to feel.

Tonal indicators (not actual templates, just register illustrations):

> *"In the 1974 NJ State Championships -86kg division, Tanaka-sensei
> beat the defending champion by waza-ari in the final. The match
> went to golden score."*

> *"Cranford JKC closed temporarily in 1981 when Y.Y.-sensei broke
> his hand demonstrating osoto-gari. The dojo reopened in March 1982
> with a new mat."*

> *"Marco trained with us 2018–2021. Left to pursue ne-waza
> specialization at Garden State BJJ. Returned for randori sometimes
> in 2023."*

Sparse, specific, era-flavored, no commentary.

### The three story-type wells

*New section in v2.* Most chronicle entries draw their texture from
one of three wells:

**The discovery of what techniques to use to train people.** A
sensei discovers that a particular drill produces certain results in
certain students. A drill that lands for one body type fails for
another. A teaching emphasis that worked for one cohort produces
different outcomes for the next. The chronicle entries that draw
from this well render technique-discovery moments — the first time a
student lands a specific throw, the first time a teaching method
produces a champion, the first time a sensei realizes a particular
kind of student needs a particular kind of training. Templated
against entry types: belt promotions, notable training moments
(rare entry type, higher-resolution), competition results that
implicate teaching method.

**What stories emerge from the people who walk in.** Procgen students
arrive with rolled hidden goals, rolled family backgrounds, rolled
nationalities, rolled relationships to the sport. The chronicle
entries that draw from this well render the texture of the people
themselves — who walked in, what they wanted, where they ended up,
what happened to them across years and decades. Templated against
entry types: student migrations, senior returns, notable
accomplishments by individual students, sensei-student conversation
events (Ring 3 mechanic).

**The diseases and the injuries that occur.** The operational
discovery layer (Part VI) renders entries against this well —
ringworm outbreaks, mat injuries, equipment failure injuries, late-
career injuries that affect retirement timing, infectious-disease
incidents that closed a dojo for a week. These are the texture of
running a real institution rather than a sterilized management sim.
Templated against entry types: operational events, notable injuries
(if elevated above low-resolution), dojo-closure events when caused
by operational failure.

The three wells are not exhaustive — there are chronicle texture
sources outside them (federation politics, lineage extensions, family
events) — but they are the *primary* sources, and naming them
explicitly helps the authoring work focus on what makes the chronicle
feel like a record of a real institution rather than a record of a
gameworld.

### Authoring scope for 1.0

Across roughly twelve to fifteen entry types:

- High-frequency types (tournament_result, photo_event, belt_promotion,
  student_migration): 3 tier bands × 4 eras × 4-5 variants = ~50-60
  templates per type.
- Mid-frequency types (sensei_transition, dojo_opening, dojo_closing,
  cross_dojo_seminar, senior_return): 3 tier bands × 4 eras × 3-4
  variants = ~35-50 templates per type.
- Low-frequency types (child_birth, boycott_affected, notable_death,
  cohort_formation, operational_event, coaching_defection): mostly
  flat — no tier banding, era-flavored, 3-4 variants per era = ~12-16
  templates per type.

Total: roughly 500 to 900 templates for 1.0. Closer to 600 than 1200.
That is finishable.

Plus per-template slot pools (decisive moments, career implications,
result propagation phrases, death circumstances, retirement framings,
etc.) that draw from era-bound and context-bound libraries. Slot pool
authoring is a parallel effort, probably 200-400 phrase entries
across all pools.

### Authoring approach

The recommended authoring approach: write systematically by entry
type, one type at a time. For each type, fill the grid completely
before moving to the next. Probably 50–100 templates per writing
session if you find a rhythm. Twelve to fifteen sessions and the 1.0
library is done.

Voice consistency across the library is critical. Use the existing
coaching-language bible (`The Chair, the Grip, and the Throw`) as the
voice reference. The chronicle prose adopts the "foundational mode"
register most of the time, with the "demonstration mode" register
for tournament final entries and similar high-gravity moments.

A starter file companion to this spec — `legends-templates-skeleton.md`
— will list every entry type, name its structured slots, break down
its grid, and provide 2-3 worked example templates per type as voice
anchors. The starter file is separate from this spec and ships
alongside it as the authoring substrate.

---

## Part VI — The Character Lifecycle and the Physical Dojo

This part specifies what surrounds the player's day-to-day play: the
family layer with its child-birth and judoka-children mechanics, the
cohort retention mechanic, succession with its absence-trajectory
returns, the portraits-and-photos system that makes the dojo a
physical chronicle, the visual Easter eggs that reward daily-grain
players, and the operational discovery layer at its Ring 2 / Ring 3
boundary.

### The family layer

The resource model specifies the family layer in depth. The May 6
design conversation locked the partner shape and the attention-shock
curve. v2 extends both with additional commitments around children
probability, twins/triplets, judoka-children mechanics, and natural
deaths.

#### Partners as decorative background

Partners are not simulated entities. Each sensei has the possibility
of a partner; the partner has a name, an occupation, a basic
personality profile for narrative-event flavor, and otherwise no
independent simulation. Partners do not have their own resource
pools, their own career trajectories, or their own chronicle entries
beyond appearances in the player's sensei's family events.

Partner dynamics beyond the child-birth mechanic are post-1.0. No
partner career interactions, no partners-also-in-judo plots, no
divorce, no partner illness in 1.0.

#### Child-birth attention shock for senseis

When a child-birth event fires for the player's sensei (rolled at
low probability per year per sensei in eligible life circumstances),
the sensei's weekly attention-hours budget drops on a fixed
three-year recovery curve:

- Year 1 after birth: 50% of normal.
- Year 2 after birth: 75% of normal.
- Year 3 after birth: 100% restored.

The recovery is fixed. Not a player choice. The sensei must delegate
dojo work during the recovery window — hire an assistant coach,
elevate a senior student to teaching responsibilities, or accept
reduced output.

#### Judoka children

*New explicit commitment in v2.* All judoka in the worldgen — not
just senseis — can have children. The mechanic parallels the sensei
version but applies to the judoka's competitive availability rather
than to a teaching attention-hour budget.

The recovery curve for competitive judoka:

- Year 1 after birth: 25–50% competition attendance, escalating up to
  75% if the judoka is a high-tier competitor with strong support
  structure (a partner managing more of the home load, family help,
  a coaching relationship that adapts).
- Year 2 after birth: 80–100% restored.

This is a real career-arc disruptor and exactly the kind of monkey
wrench that produces the texture distinguishing a real career from
an optimizer's career. An Olympic-bound competitor whose first child
arrives during their qualification cycle has a meaningfully lower
probability of qualifying than an otherwise equivalent competitor
without that disruption. The chronicle records the cause when the
qualification fails. *"Reilly missed the 1996 Olympic qualification
window. His first child had been born that February."*

#### Children probability variability

*New in v2.* Some senseis and judoka roll zero children across a full
career. Some roll one. Some roll three or more. Multi-birth events —
twins, triplets — fire at realistic rates: twins at maybe 2–3% of
births, triplets at fractions of a percent. The worldgen produces
them when they happen because they create their own narrative texture
(a sensei suddenly responsible for three infants instead of one is a
different attention-shock entirely).

#### CK3-style naming

*New in v2.* Each child gets named at birth. Procgen names by default,
drawing from era-appropriate naming pools weighted by the parent's
nationality. For player-character offspring, the player gets a naming
prompt — they can name each child. The names persist into the
chronicle permanently. Player-named children carry the player's
choices forward through every chronicle entry that mentions them
across decades.

#### Multiple children variance

The roll fires multiple times across a career. Different children get
different relationships to the dojo. A sensei with three children
might have one successor candidate, one occasional helper, and one
estranged adult child who hasn't been on the mat in twenty years. The
mechanic supports this kind of variance.

#### Tragedy events

Family tragedy events — death of a child, death of a partner,
serious illness — remain post-1.0 per the resource model. They are
designable but require careful authoring of legend-layer prose.
Boycott events provide enough heavy material for 1.0.

#### Natural deaths in the worldgen

*New explicit commitment in v2, distinct from the deferred family-
tragedy events.* Judoka in the worldgen naturally die across the
66-year (or longer) window because that is what happens to people
across decades. Cohort members of the player die. Senior students of
the player die. Sometimes the player's own students die — at low
rates, in age-appropriate ways, occasionally tragically (a young
judoka in an accident, a competitor who pushed too hard in a match
and didn't recover). These deaths are part of the chronicle. They
fire the `notable_death` entry type.

When a chronicle-active judoka dies, the chronicle records the
event. If the dead judoka has a portrait, it can be hung in their
home dojo's wall (player choice for player-affiliated deaths;
automatic for the worldgen's procgen senseis). The visual Easter
eggs system then activates around the photo (see *Visual Easter
eggs* below).

### The cohort retention mechanic

*Promoted in v2 from chronicle indexing structure to load-bearing
retention mechanic in the dojo loop.*

The reality the mechanic models: every sensei tries to bunch new
student intake into cohorts on purpose, because a class of five new
white belts is exponentially more retainable than five new white
belts spread across five quarters. A white belt who walks in during
a quarter when three other white belts also start has a high
probability of staying — they have peers, they advance together,
they pair up for randori, they hit yellow belt as a small cohort and
feel collectively accomplished. A white belt who walks into a roster
of green and brown belts with no peers has a much higher probability
of dropping out, because being the only beginner in a room of
advanced practitioners is intimidating and isolating.

#### Cohort cohesion as a per-student state

Each student carries a cohort cohesion value. High when the student
has multiple peers within one belt level of themselves who entered
the dojo within roughly twelve months of their own start date. Drops
as cohort members leave or advance ahead. A student whose cohort has
fully dispersed — graduated up, dropped out, moved away — sees their
retention probability drop unless they have meanwhile bonded with a
different cohort or accumulated other reasons to stay (relationship
with sensei, hidden goals being met, family ties to the dojo).

#### Cohort cohesion drives retention

Retention probability is calculated weekly per student. Cohort
cohesion is one input. Other inputs: relationship strength with
sensei, hidden-goals satisfaction, financial pressure, family
context, recent injury or illness state, dojo cultural fit. Cohort
cohesion is a substantial factor — a student in a strong cohort
gets a meaningful retention bonus; a student in a one-person cohort
gets a meaningful retention penalty.

#### The recruitment-strategy texture

This connects to the dojo loop's recruitment strategy. A player who
scatters new students one at a time across many months produces low
cohort cohesion and watches retention struggle. A player who
concentrates intake into recruitment pushes — twice a year, building
cohorts of four to six simultaneously — produces high cohort
cohesion and watches retention soar. The choice is in the player's
hands; the consequence is felt in the chronicle.

This dynamic also produces a felt difference between the basement-
from-scratch opening (where the player can structure their initial
intake into a single tight cohort) and the established-dojo opening
(where the player inherits an existing population with mixed and
already-decohering cohorts).

#### Cohort UI surface

Cohort state is visible on the roster UI, alongside the Songs-of-
Syx-style at-a-glance student state. Each student card shows their
cohort affiliation and cohort cohesion. The player can see at a
glance that Marco's cohort just lost two members and his cohesion
has dropped, before retention probability silently does its work.

#### Cohort lineage tags

When a cohort matures and members advance, they form a lineage tag —
the cohort that came up under [this sensei] in [these years] with
[this character]. Later cohorts at the same dojo trace back to
earlier cohorts through the sensei's coaching evolution. The
chronicle's five-year and ten-year reports surface cohort lineages
as primary structure.

### Senior-student returns

*Refined in v2 from the v1 three-options framing.* When a former
student returns to the dojo after years or decades away, the
worldgen rolls an *absence trajectory* that determines what they
carry. The trajectory has multiple sub-fields:

- **Time elapsed.** Years between leaving and returning.
- **What they did during the absence.** Powerlifted. Did yoga.
  Trained another martial art. Raised children. Worked a demanding
  career outside martial arts. Was institutionalized. Was
  imprisoned. Was hospitalized for a long-term condition. Each
  option has a profile of what it leaves on the body.
- **Their fight IQ at departure.** Persists across the absence.

The carry profile derives from these. Some characteristics persist
across any absence (skill ceiling memory, technique repertoire
breadth, lineage relationships). Some degrade in expected ways
(conditioning, signature reliability, fight reflexes). Some can
improve in unexpected directions (a returnee who spent five years
powerlifting comes back with substantially higher strength but
degraded technique fluency; a returnee who spent ten years as a
yoga instructor returns with extraordinary flexibility but minimal
current judo IQ).

The IQ modulator: high-IQ judoka adapt faster on return. They regain
match-readiness in months, not years. They integrate their absence-
period changes into their judo intelligently. Low-IQ returnees stay
in their absence-shape longer.

Default carry profiles by absence-trajectory:

- **Trained another martial art.** Time-enriched in unexpected
  directions, time-degraded in pure judo execution.
- **Powerlifted or strength-trained.** Higher strength contribution to
  tachiwaza and ne-waza, degraded conditioning, degraded signature
  reliability.
- **Raised children, no training.** Generally time-degraded,
  particularly conditioning and reflexes; sometimes time-enriched in
  empathy and patience contributing to fight IQ.
- **Worked demanding career outside martial arts.** Generally time-
  degraded across all dimensions, modulated by stress level.
- **Coached at another dojo.** Time-enriched in fight IQ and signature
  understanding, time-neutral or time-degraded in personal
  conditioning.

#### Frozen-at-leaving is rare

Frozen-at-leaving is implausible — it implies the absence period
involved no physical or mental change at all. It is mostly avoided as
a default. The system only produces it for very short absences (under
a year) when the absence-trajectory was nominal.

#### What the player sees

When a returnee enters the chronicle, the entry can render the
absence trajectory as part of the prose: *"[name] returned to
Cranford JKC in 2015 after fourteen years away. He had been training
BJJ in Brazil. His ne-waza had sharpened; his tachiwaza was rusty."*
Or simpler: *"[name] returned in 2015 after thirteen years. He had
not trained in that time."*

The IQ modulator can also render: *"[name] regained match-readiness
within three months."* Or: *"[name] was still rebuilding his
conditioning a year after his return."*

### Succession

When the player's character's arc ends — health zero forcing
retirement, voluntary retirement, or death — the player faces the
succession choice. Three doors are named in the design. Only door
(a) ships in 1.0.

**Door (a): switch perspective to the successor.** The player picks a
new character to pilot from candidates within the dojo. The dojo
persists. The world persists. The simulation continues.

**Door (b): stay with the original sensei in retirement.** Post-1.0.
Gameplay shifts to board meetings, seminars, mentoring.

**Door (c): leave entirely and start elsewhere.** Post-1.0, after
worldgen-as-shared-state has been pressure-tested.

#### Door (a) implementation

The succession menu lists candidate successors derived from the
worldgen state of the dojo:

- **Children of the current sensei who took the judo path.** Per the
  family layer, some children become successor candidates. Player-
  named children persist by name.
- **Senior students with successor-track flags.** Senior students who
  have stayed at the dojo for years, accumulated coaching
  responsibilities, and shown the right combination of judo skill and
  cultural alignment with the dojo.
- **Outsider candidates (low probability).** Worldgen may roll a
  transfer-sensei candidate from elsewhere — a former student of
  another dojo who has been looking for a place to take over, a
  federation officer who wants to return to teaching, a displaced
  sensei whose previous dojo closed. Rolled at low probability,
  weighted by the player's federation reputation and dojo's regional
  standing.

The player picks one. The character pointer updates. The previous
sensei becomes a chronicle entity.

If the previous sensei retired without dying and their health and
energy permit, they may continue as a masters-tier competitor. The
new sensei pilots the dojo; the old sensei occasionally appears at
masters tournaments. See *Retired-sensei-as-masters-competitor* in
Part III on the mentor system.

The dojo's resources, fog-of-war state, and chronicle are inherited.
The new character starts in the dojo as it exists, with all its
history, with all its physical chronicle on the walls.

### Portraits, photos, and walls — the physical chronicle

*Substantial expansion in v2.* The dojo as physical chronicle
(Commitment 5) requires this set of supporting systems.

#### Procgen portraits for every chronicle-active judoka

Every judoka with chronicle presence has a portrait. The portrait is
generated at character creation from a procgen system — face shape,
hair, eyes, skin tone, jawline, age progression markers. Distinct
enough that the player can recognize Marco vs. Tom vs. Diego at a
glance. The DF / RimWorld lineage of low-fidelity-but-distinguishable
faces is the reference model.

Hand-authored faces for load-bearing characters: the player's mentor,
named federation officials in late game, the player's own succession
line, the founding sensei (Y.Y.) of Cranford JKC. The hand-authored
list is small (probably under twenty faces total in 1.0); the rest
are procgen.

Portraits age. As a judoka ages across the simulation, their portrait
ages with them — graying hair, deepening lines, slumping posture,
eventually frailty markers. Multiple portraits across a long career
let the chronicle and the wall display age-appropriate portraits per
era.

When a judoka dies, their final portrait is the one hung on the wall
if anyone hangs it. The portrait of an eighty-year-old mentor at
death looks like an eighty-year-old, not the thirty-year-old who
founded the dojo.

#### Group photos as a first-class entry type

The `photo_event` chronicle entry type fires at notable occasions:

- Every tournament where the dojo had competitors — a contingent
  photo before or after the tournament.
- Every cross-dojo seminar where the dojo hosted or visited — a group
  photo with attendees and the visiting sensei.
- Every black-belt promotion — the new black belt with the senior
  student community present.
- Every dojo anniversary at five-year intervals — a multi-generational
  photo.
- Every rare special occasion (a champion returning to visit, a
  former student bringing their children to the dojo, a wedding or
  memorial).

A photo entry stores: occasion, year/date, location, list of
attendees with their procgen portraits, and a brief caption. The
caption is templated per the legends-rendering grid (see Part V).

The photo renders in 2D as a group-portrait composite — the portraits
of the listed attendees arranged in rows, framed, with the caption
underneath. Hung on a wall.

#### Hyperlinks into the chronicle

Hovering over any face in any photo opens that judoka's chronicle
entry. A photo from 1974 shows seven people. The player taps one —
*who's that?* — and gets that judoka's full chronicle. Their career,
their lineage, where they ended up. Photos become hyperlinked into
the chronicle. The dojo's wall becomes a clickable index into 60+
years of the world's history, encountered visually rather than
navigated through menus.

#### Cross-dojo cross-references

Every dojo in the simulated NJ has its own photo wall. The 1974
chronicle entry where Cranford JKC competed at the state
championships also appears as a photo at the *winning* dojo's wall.
Photos cross-reference. A player visiting another dojo (a Ring 3
mechanic — observation, seminar attendance, scouting) can see that
dojo's photo wall and recognize members of their own lineage on it.
The sediment accumulates not just in your own dojo but across the
visible world.

#### Belts as decoration

Champion belts won by the dojo's competitors can be hung in glass
cases on dojo walls. State championship belts, national belts,
continental and international belts. Each belt is a chronicle entry
with its own structured payload (which competitor won it, in which
year, at which tournament, against whom in the final). Hovering over
a belt opens the same kind of hyperlinked chronicle path that photos
provide.

When a competitor who won a hung belt dies, the belt remains hung. It
becomes part of the dojo's accumulated history.

### Visual Easter eggs

*New in v2 as a named principle.* The reward for daily-grain players.
Subtle 2D-layer animations and behaviors that surface only when the
player chooses to live in the daily-grain layer rather than skim at
higher grain.

#### The cohort photo-bow

When a chronicle-active judoka dies and their photo is hung, their
cohort members who are still active retain a relationship-state
pointer to them. Every time those cohort members enter the dojo room
where the deceased's photo hangs, they perform a small bow toward
the photo as a 2D-layer animation. The player who watches the daily
classes sees this happen.

The animation is subtle. The player's read of it depends on whether
they have the chronicle context. A player who has paid attention
knows what they are looking at. A player who has not sees a small
ritual without context.

A cohort of three remaining judoka, all now in their forties, bow
each Tuesday and Thursday as they pass the photo of the fourth
member of their cohort who died of cancer in 2009. This is the
texture.

#### Other Easter eggs in the same family

The mentor (during his life) sits in his usual spot at his usual
time. His absence from that spot becomes visible after his death.

Senior students perform extra cleanup before a visiting sensei
arrives.

A returnee judoka who has rejoined after a decade away walks the
dojo's perimeter the first day back, looking at every photo on the
wall, recognizing some, not recognizing others.

Children of senseis who have been playing in the dojo for years
suddenly become visible as junior students in their first session
on the mat, and continue to age across visits.

The mentor's portrait, after his death, occasionally has a fresh
flower placed beside it on a particular date. The player can see the
flower if they happen to visit on the day. The senior student who
placed it can be identified through chronicle context.

Each of these is low-cost animation. Together they reward the player
who chooses to live in the daily.

### The operational discovery layer

*Promoted in v2 from a Ring 3 mechanic to a named system at the Ring
2 / Ring 3 boundary.* This is properly Ring 3 work (within-dojo
daily play) but it intersects with Ring 2 in specific places that
this spec addresses.

#### The hidden-until-encountered pattern

The dojo has operational details that affect the dojo loop's
outcomes: mat hygiene, parent comfort, equipment wear, water quality,
locker room maintenance, hand-wrap supply, mat replacement schedules.
These are hidden from the player until the first time one of them
surfaces in play.

The first encounter is always narratively framed. The mentor (during
his life) names cause-and-effect. *"You haven't scheduled mat cleanup
this week. When I started, I lost three students to ringworm in
1968 and never made that mistake again."* The chronicle entry that
records the consequence names the cause: *"[Student] contracted
ringworm. Mat hygiene at the dojo had been intermittent that month."*
A student or parent surfaces the cause through conversation: a parent
pulls the player aside — *"I love what you're doing here, but my back
is killing me. Have you thought about benches?"*

After the first encounter, the operational state becomes glance-
readable. The dojo's status panel surfaces it. The player can ignore
it — that's their choice — but they can't say they didn't see it
coming.

This is the critical principle. *Don't punish the second time without
changing the surface.* The first encounter is hidden discovery. The
second time is informed choice. The Gladiator Manager failure mode
(consequences fire without the player being able to trace causes) is
explicitly designed against.

#### Era-flavored operational practices

Operational practices evolve across the technology eras:

- **Paper-and-Radio (1965).** Mat hygiene is bleach and a mop. The
  mentor's commentary: *"We used straight bleach and didn't ask
  questions."*
- **Phone-and-Fax (1990).** Antimicrobial cleaners are emerging as
  industry-standard. Awareness of bloodborne pathogens is growing.
- **Email-and-Web (2005).** Mat-grade disinfectants are well-
  established. Insurance considerations drive operational standards.
- **Smartphone (2020).** A whole industry of antimicrobial cleansers,
  mat-grade disinfectants, locker room HVAC, hand-sanitizer
  stations. Best practices are codified and visible.

Era-flavored variation feeds back into the technology era system as
another textural layer.

#### Chronicle integration

Procgen senseis in the worldgen also have operational practices that
the chronicle reflects. A 1970s sensei who never invested in mat
hygiene produces a chronicle entry stream with a ringworm pattern in
the dojo's history. When the player visits or buys out that dojo,
the chronicle is honest about what was happening. *"Cranford JKC's
mat hygiene was inconsistent through the 1980s, with two notable
infection outbreaks in 1983 and 1987."* The player who inherits a
dojo inherits its operational legacy.

#### Ring 4 narrative event candidates

First-encounter triggers are Ring 4 narrative event candidates. The
first ringworm outbreak. The first parent who complains about
benches. The first equipment failure injury. Each is a candidate for
a scripted-but-rolled narrative event with branch choices.

### Cranford anchor — locked

Cranford JKC opens in 1962 in Cranford, NJ. The founding sensei's
surname uses a Y.Y.-shape Japanese rendering — Yashima Yonezu, Yoshi
Yazuke, or similar two-initial Japanese form — paired with a
procgen-rolled given name. Everything else is rolled per campaign:
competitive attributes, throw signatures, coaching style, lineage
origin, personal trajectory across decades, the eventual fate of the
dojo across the campaign.

The Y.Y. surname is the personal anchor. Hidden in plain sight,
identifiable to anyone who knows the lineage you came up in but
legible as just-a-Japanese-name to anyone who doesn't. The Easter
egg framing is exactly right.

Future versions can revisit the literal naming if a more direct
homage is wanted, with appropriate consent. Not committed now.

---

## Part VII — What This Spec Doesn't Decide

Open questions remaining after v2. Several v1 questions are now
closed and noted in passing.

### Closed in v2

- **WG-A (worldgen visible vs silent).** Closed. Visible by default
  per Commitment 4.
- **OQ-3 (senior-student-return what-they-carry).** Closed. Combo of
  time-enriched and time-degraded based on absence-trajectory and
  IQ. See *Senior-student returns* in Part VI.
- **OQ-4 (opening-choice menu shape).** Closed. Hybrid: curated
  structure (mentor tutorial, basement, inheritance, buy-out,
  established) with worldgen-rolled content within each option.
- **OQ-5 (era-specific population evolution).** Closed and replaced
  by the nationality tag system. See Part II.
- **OQ-9 (cohort tracking implementation cost / when to ship).**
  Closed. Ships from start. Cohort tracking is now load-bearing for
  retention, not just reports.

### Open in v2

**OQ-1. The Y.Y. anchor's degree of constraint.** Currently locked at
name-shape-fixed, attributes-rolled. Open: is the rolled freedom
enough to feel like a real Cranford lineage anchor, or does it dilute
into "any procgen sensei could have been here"? Requires playthrough.
A more direct homage to the inspiration — by name, by dedication, by
other means — remains a personal decision deferred from this spec.

**OQ-2. Fog-of-war revelation density at each tier.** Suggested rough
defaults given in Part IV. Playtest will calibrate. Open question is
whether these numbers produce the right "the world feels real and
inhabited" texture without overwhelming the player's history-reading
bandwidth.

**OQ-3 (renumbered from v1's OQ-5). Era-specific population
evolution within a single campaign.** The state module specifies
geography and population data. The question: does population data
need to evolve across decades within a single campaign, or is the
1960 distribution good enough? Real population data is available at
decade granularity for U.S. states. Modeling the shift across decades
would let dojo density evolve realistically. Suggested default: yes,
model decade-shifts for NJ in 1.0; defer for other states until
needed.

**OQ-4. Hybrid LLM rendering as a 2.0+ option.** The 1.0 commitment
is templated-only. The hybrid path remains available as a future
option. Open: when to revisit. Possible triggers — when local-LLM
technology becomes reliable enough to ship as a default distribution
component; when the 1.0 player base grows large enough that template
repetition becomes a noticeable problem; when a contributor wants to
do the hybrid implementation. Not on the 1.0 roadmap.

**OQ-5. Resolver re-calibration cadence.** Suggested default:
calibrate against tagged Ring 1 milestones rather than every commit
for 1.0; escalate to per-commit if drift is observed. Open: which
cadence balances development tax against drift risk.

**OQ-6. Save migration when a state module updates.** If Pennsylvania
ships in 1.1 and gets a content update in 1.2 (adding more
historical inflection points, refining the cultural profile), what
happens to existing PA campaigns? Suggested default: version-
locking. State module changes are content; existing campaigns
shouldn't be disturbed. New campaigns get the latest module.

**OQ-7. The boycott event's interaction with player perspective.**
The boycott event is one of the heaviest narrative beats in the
worldgen. When it fires and affects the player's competitor, what
does the player see? Suggested default: an interrupting narrative
event for the player's own competitors (they should feel it
directly), a chronicle entry for procgen-affected judoka (who appear
later in the History menu).

**OQ-8. The chronicle's storage and query implementation.** Specified
conceptually as entries with indices and visibility flags. The
implementation question: relational database, document store, in-
memory indexed structure, custom binary format? The chronicle is the
most-read structure in the running game and the most-written during
worldgen. Open with a strong "this is engineering, not design" lean.

**OQ-9. Visual Easter eggs density.** *New.* The cohort photo-bow
and other daily-grain Easter eggs need playtest to settle density —
how often, how subtle, how much they reward the daily-grain player
without becoming noise. Open.

**OQ-10. Photo-event firing rate.** *New.* Photos fire at named
occasions but the rate per dojo per year needs calibration. Too few
and dojo walls feel sparse. Too many and the chronicle bloats with
photo entries. Open.

**OQ-11. Federation-specific rule variation.** *New.* Deferred to
content updates per Part II. Open: when to revisit. The benefit is
texture. The cost is calibration burden. Probably revisit when 2-3
state modules have shipped and the calibration tooling has matured.

**OQ-12. The mentor's death timing window.** *New.* Suggested default
is rolled within in-game years 2–5 of the campaign with weighting
toward years 3 and 4. Open: is this the right window? Earlier and
the tutorial truncates; later and the player has already internalized
the dojo loop and the mentor's value diminishes.

### Questions deliberately not addressed in this spec

- The scheduling UI. The resource model is the spec for what the
  scheduling UI implements. The UI itself is its own document, due
  next, after this spec lands.
- The lineage system. Lineage data is load-bearing for worldgen but
  the full lineage system spec is downstream of this one. Will be
  drafted as `lineage-system.md` after this spec is committed.
- The narrative event framework details (Ring 4). This spec assumes
  Ring 4 exists and produces interrupting events; the Ring 4 spec is
  its own future document.
- The deep engine's eventual handling of period-correct rules.
  Deferred to post-1.0.
- Multi-state campaigns and country-level worldgen. Hajime 2
  territory.

---

## What this spec gates

The next year of work organizes around five parallel tracks:

**Track 1 — Continue Ring 1 calibration with golden score as
prerequisite.** This work continues unchanged in scope but gains a
named blocking dependency: golden score must be implemented before
the calibration corpus runs. File the Ring 1 ticket.

**Track 2 — Build the chronicle and the abstracted resolver.** The
substrate work. The chronicle data structure with all entry types
including photo_event and cohort_formation. The abstracted resolver
with the five defined dimensions. The shared calibration corpus as
belt-grid triangular matrix. The development tooling for side-by-side
calibration (extending the Godot calibration tool).

**Track 3 — Build the state module and the worldgen pipeline.** The
NJ state module including the sub-state regional partition,
nationality demographic distributions, naming pools, and cultural
profile. The 1960 initial-state generator with the revised 3–8 dojo
numbers. The year-tick worldgen run. The handoff state assembly. The
visible worldgen presentation with the map, the icons, the ticking,
and the cultural inflection moments. The opening-choice menu
generation with difficulty profiles. The mentor tutorial as default
first-run experience.

**Track 4 (in parallel) — Author the templated legends prose.** The
500–900 templates across the chronicle entry types. This is authoring
work that runs alongside the engineering tracks. It has its own
cadence and doesn't block the other tracks until the chronicle and
resolver are working well enough to feed it. The starter file
(`legends-templates-skeleton.md`) ships alongside this spec as the
authoring substrate.

**Track 5 (in parallel) — Build the procgen portrait system and the
photo composite renderer.** Visual layer work that supports
Commitment 5 (dojo as physical chronicle). Probably extends into
Ring 6 (2D Visual Layer) work but the substrate (portraits, photos,
walls, hyperlinks) is Ring 2 commitment.

The fog-of-war system, the reports system, the perspective-switch
implementation, and the family-event integration follow from these
five tracks reaching working state. They are the player-facing
surfaces that complete Ring 2.

The 1.0 cut decisions — templated-only legends prose, door (a) only
for succession, partner-shape decorative-only for family layer — are
what make the 3 to 4 year horizon plausible for Ring 2.

---

## What the master doc body needs to absorb

Following this spec's commitment, the master doc body will need a
revision pass to:

- Update the Ring 2 section with the five architectural commitments
  (dojo persistent, tick is grain, reports as views, worldgen as
  theater, dojo as physical chronicle).
- Add the partner-shape commitment, the child-birth attention-shock
  curve, the judoka-children mechanic, the natural-deaths commitment,
  and the children-probability-variability with twins/triplets.
- Add the cohort retention mechanic with cohort cohesion as load-
  bearing for retention.
- Add the mentor-tutorial commitment as default first-run experience.
- Add the visible worldgen / map commitment.
- Add the procgen portrait, group photo, and visual Easter egg
  commitments under Commitment 5.
- Add the nine-tier ladder revision.
- Add the operational discovery layer at the Ring 3 boundary.
- Update the open questions list to close the v1 questions resolved
  here and add the v2 questions surfaced.
- Reference this document as the full Ring 2 spec landed.

---

## Closing note

This spec is comfortable with what it doesn't yet know. The open
questions are real; the suggested defaults are not commitments; the
calibration numbers are placeholders; the authoring scope estimates
are rough.

What is committed: the five architectural commitments in Part I, the
chronicle structure in Part II including the photo and cohort entry
types, the state-module commitment, the templated-only 1.0 legends
decision, the family-layer commitments (partner-shape, child-birth
curve, judoka-children, natural deaths, twins/triplets, CK3 naming),
the succession door (a) commitment, the visible worldgen commitment,
the mentor tutorial as default first-run, the cohort retention
mechanic, the senior-student-return absence-trajectory framing, the
Cranford anchor with Y.Y. shape preserved, the procgen portrait
system and photo entry type and visual Easter eggs principle, the
operational discovery layer's hidden-until-encountered pattern, the
nine-tier ladder, and the nationality tag system.

Everything else is design surface that moves under playtest pressure.

The next document is the scheduling UI, working from
`resource-model.md`. After that, `legends-templates-skeleton.md` as
the authoring substrate. After that, `lineage-system.md`. After that,
the Ring 4 narrative event framework spec.

Worldgen is the load-bearing architecture. This spec is the design.
Implementation begins when the spec is read and ratified.

---

*Drafted May 7, 2026, following four review conversations against v1.
Open to push-back on anything wrong; especially open to push-back on
the five commitments in Part I, since they organize everything else.
The v1 spec is preserved as `ring-2-worldgen-spec.md`. v2 is its
superset.*
