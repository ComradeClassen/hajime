# Resource Model — First Cut

*Drafted May 4, 2026. Specifies the resource economy that drives the
scheduling-as-game insight. First cut, meant to be pushed back on. Settles
the four primary resources, the derivative reputation model, the aging
curve, the family layer, and the trade-off pairs that produce the player's
interesting choices. The scheduling UI follows from this document; do not
design UI before this model is committed.*

*Revised May 4, 2026 (end of session) with the addendum: student resource
visibility resolved to Songs-of-Syx-style at-a-glance state (with hidden
information reserved for narrative interiority); federation reputation
resolved to procgen-everything (with Cranford JKC and Y.Y. as the only
fixed anchors); and a new Family Layer section added between the aging
curve and the trade-off pairs.*

---

## The core insight this model serves

The scheduling system is the game. The player is not just a coach managing
students — they are a sensei who is also a competitor, an administrator, a
tournament host, a board member, eventually a regional president. Their
**attention is finite**, their **body is finite**, their **money is
finite**, and the choices they make about how to spend each constitutes
the moment-to-moment play.

This document specifies what those finite quantities are, how they're
supplied, how they're spent, and how their interactions produce the
reputation arcs that feed the lineage system and the federation politics
layer.

---

## The four primary resources

### 1. Attention-Hours

The fundamental scarcity. The player has a fixed pool of attention-hours
per week that gets allocated across all activities. Most decisions in the
game are decisions about how to spend attention-hours.

**Supply.** Base supply varies by life stage (see aging curve below). A
mid-career sensei in their 30s might have ~50 attention-hours per week.
The number is not realistic in real-world terms — it represents *coachable
focus*, not literal hours. Sleep, family, eating do not consume from this
pool; they are abstracted out.

**Spend categories.** Teaching kids' classes, teaching adult classes,
private lessons, personal training (your own technique), competition
preparation (your own), administrative work, board meetings, observing
other dojos, hosting tournaments, recruiting, marketing, facility
maintenance, mentoring senior students, reading IJF rule updates,
scouting at junior events.

**Allocation interface.** Calendar/scheduling UI. Each week the player
sees a grid of available hours and assigns activities. Some activities are
recurring (kids' class Tuesday and Thursday). Some are one-off (board
meeting next week). Some compound (consistent personal training builds
your competitive readiness; consistent recruiting builds your dojo
population over months).

**Decay.** Unspent attention-hours do not roll over. The week ends, the
budget resets.

### 2. Energy

The bodily resource that constrains *physical* spending — training
alongside students, demonstrating techniques, competing personally, hard
randori, intensive coaching from the mat.

**Supply.** Base supply varies sharply by age. A 25-year-old has high
energy that recovers quickly. A 60-year-old has lower energy that recovers
more slowly. Athletes with strong cardio backgrounds maintain higher
energy ceilings into older ages.

**Spend categories.** Personal training, training alongside students,
demonstrating, sparring, competing, intensive on-mat coaching.
Administrative work and observation cost almost no energy.

**Recovery.** Energy refills weekly with rest. Saunas, massage, and
recovery facilities accelerate refill (see facility investment below).

**Hard cap.** When energy hits zero, the player cannot do energy-spending
activities at all that week. Forcing through this cap risks injury (see
health below).

### 3. Health

The accumulating bodily resource that tracks long-term wear. Different
from energy in that it does not refill weekly — it tracks across years and
decades.

**Supply.** Starts at a high baseline at the beginning of a career. Decays
slowly with normal training, faster with intensive competition, sharply
with injuries. Recovers slowly with proper recovery investment, never to
the original baseline.

**Spend.** Hard training costs small amounts of health over time.
Competition costs more. Injuries cost large chunks. Health spent is mostly
permanent.

**Recovery.** Saunas, recovery facilities, lower training volume in older
ages, occasional time off the mat.

**Hard cap.** When health hits zero, the player retires from physical
activity — they can still coach, administer, mentor, but they can no
longer demonstrate, train, or spar. This is the hard age-out.

**Modifier — competition history.** A player who competed at high
intensity through their 20s and 30s reaches their 50s with more
accumulated wear than a player who took a lower-intensity coaching path.
Defeat record matters too — a player who lost difficult matches with
serious injuries (rolled at the time) carries the wear forward.

### 4. Money

The economic resource. Already present in the existing dojo loop design.

**Supply.** Earned from class fees, private lesson fees, seminar revenue,
tournament hosting fees, federation stipends (if applicable). Modulated by
dojo population, reputation, and pricing decisions.

**Spend.** Rent, equipment replacement, facility upgrades, travel for
competition or coaching, marketing, hiring assistant coaches, paying
federation dues.

**Hard cap.** When money goes negative, the dojo enters financial
distress — cannot pay rent, cannot maintain facility, eventually closes.
The economic-pressure failure mode that gives the dojo loop its stakes.

---

## The derivative resource: Reputation

Reputation is **not** a directly allocated resource. It accumulates from
patterns of how the four primary resources get spent. Different patterns
produce reputation in different camps.

**Reputation is multi-channel.** A single judoka does not have one
reputation number — they have separate reputation tracks with each named
entity in their world:
- The four procgen federations rolled per state
- The local dojo community (other senseis nearby)
- The student community (current and former students)
- The competition community (other competitors)
- The international scene (only legible above a threshold)

**Spending patterns build reputation.** Some examples:
- Hosting tournaments → builds federation reputation
- Producing competitive students → builds competition-community reputation
- Attending board meetings → builds federation reputation more efficiently
  but slowly, and at attention-hour cost
- Training alongside students → builds local community and student
  reputation
- Cross-state seminars → builds international/scene reputation
- Long-term student retention → builds local community reputation
- Sending students to other dojos for cross-training → builds peer
  reputation among other senseis

**Reputation as gate.** High reputation in specific camps unlocks
opportunities — invitation to coach a national team, election to a board,
nomination for high-rank promotion, invitations to prestigious seminars.
Some opportunities require reputation in multiple camps simultaneously.

**Reputation as friction.** Low reputation in a camp closes doors. A
sensei with poor reputation among nearby dojos finds their tournaments
under-attended.

**Reputation decay.** Reputation slowly decays without continued spending
in patterns that built it. A sensei who stops attending board meetings for
five years loses federation reputation. A sensei who stops producing
competitive students loses competition-community reputation.

---

## The aging curve

The four primary resources change supply across the career arc. This is
the load-bearing mechanic that produces the *shape* of a long career.

**Energy** declines monotonically with age, modulated by accumulated wear.
A 25-year-old with high cardio has near-peak energy. The same person at
55, having competed hard in their 30s, has substantially less.

**Health** starts at baseline, decays with use, never recovers fully. By
age 60 most senseis have meaningful permanent wear.

**Attention-hours** *increase* with age, modulated by life circumstances.
A 25-year-old has fewer attention-hours per week than a 50-year-old —
because the younger sensei is also dealing with kids at home, financial
instability, less efficient prioritization. The 50-year-old has more
delegation skill, fewer dependents, and clearer focus. Peak attention-
hours are typically reached in the 40s-60s.

**Money** is not directly age-dependent — it depends on the dojo's
economic state, which depends on prior spending patterns. But indirectly,
older senseis often have more money because their reputation has
accumulated and their dojo is established.

**The crossover.** The reason this design produces interesting late-career
play is that the resource curves cross. The 30-year-old has high energy
and lower attention-hours. The 60-year-old has lower energy and higher
attention-hours. They play *different versions* of Hajime in different
career stages. Early career emphasizes physical presence and personal
competition. Late career emphasizes administration, mentoring, and
strategic allocation. The same player going through a multi-decade
campaign experiences several genuinely different game-feels.

**Mechanical implication.** Older senseis who try to play like young
senseis (training intensively, competing) wear out fast. Older senseis
who play to their resource shape (administration, mentoring, federation
work) accumulate reputation efficiently but at the cost of student
outcomes if they neglect on-mat presence.

---

## The Family Layer

The four primary resources gain a fifth implicit demand: **family**. Not as
a separately allocated resource, but as a category of obligatory spending
that constrains the others, and as a generator of legend-tier narrative
events.

### Sensei children — the mechanic

The worldgen rolls **child-birth events** at low probability per year per
sensei in a position to have children — meaning married or partnered,
within a plausible biological window, and with life circumstances that
support it. The probability is modulated by partner status, age, life
stability, and rolled hidden traits. Some senseis have no children. Some
have one. A few have three or more.

For the player, this fires for their own sensei at random and is not
chosen. For procgen senseis throughout the world, it fires silently and
populates their dojos with eventual successor candidates (or with adult
children who never enter judo).

### The years before judo eligibility (0–5)

A new child generates an **involuntary attention-hour and money draw** on
the sensei. The amounts are not catastrophic but they are real — a new
parent in their 30s loses, say, 20–30% of attention-hours for the first
few years. The player can mitigate by hiring assistants, scaling back
personal training, or reducing administrative ambitions. They cannot
eliminate the draw entirely.

This is the resource model's **first involuntary supply shock**, and it
arrives uninvited. The mechanic models reality: senseis with new children
make different decisions than those without.

### Early exposure (4–7)

The first parenting decision: how much does the child come to the dojo?
The choices roughly:

- **High exposure.** Bring them along to most classes, let them play on
  the mats, expose them to dojo culture from infancy. Builds early
  cultural transmission. Risks burning the child out before they can
  consent.
- **Medium exposure.** Bring them occasionally, let it be their world but
  not consume them. The middle path. Most likely to produce balanced
  outcomes regardless of the child's eventual feelings about judo.
- **Low exposure.** Keep them away. Let judo be the parent's work, not the
  child's life. Lowest cultural transmission but lowest risk of resentment.

These are not numerical sliders. They're choices that fire at specific
ages and accumulate as a parenting-style profile.

### First formal training (6–10)

The second parenting decision: how does the child enter formal training,
if at all?

- **Regular kids' class.** Treat them as one student among many. Fair to
  the dojo. The child gets less individual attention from the parent in
  this context.
- **Private instruction.** The child gets dedicated parent-coaching. Other
  students notice and react. Affects the player's local-community
  reputation if perceived as favoritism. Higher early skill gain for the
  child.
- **Other coach.** Send the child to another dojo or assign an assistant
  coach as their primary instructor. Avoids the favoritism problem at the
  cost of weaker direct relationship.
- **No formal training.** The child does other things. Soccer. Music.
  Reading. The non-judo path begins here.

### The interest reveal (10–14)

The most consequential mechanic. **Whether the child actually loves judo
is rolled at the system level, modulated but not determined by the
player's parenting choices.** The player discovers their child's
relationship to judo through play, not through assignment.

Possible outcomes (rolled with weighting from parenting profile and the
child's hidden traits):

- **Loves and gifted.** The successor track candidate.
- **Loves but average ability.** Stays in the dojo, becomes a senior
  student, takes coaching roles eventually.
- **Gifted but resistant.** The hardest case. Talent without love
  produces the worst outcomes if pushed — burnout, resentment, eventual
  rejection. May find love later if the parent backs off.
- **Neither gifted nor interested.** Drifts away from judo, pursues other
  paths. Most common outcome.
- **Active rebellion.** Rejects judo entirely, possibly including a
  period of rejecting the parent. Fires at non-zero probability
  regardless of the player's choices, because children are not the
  player's project.

### Adult phase (18+)

If the child is on a judo path, they enter the worldgen as a regular
judoka with a flag indicating they are the player's child. Their
accomplishments affect both their reputation and the parent's. Their
relationship to the parent is colored by everything that happened in
their childhood — adult successor relationships have the texture of the
parenting choices that produced them.

If the child is not on a judo path, they exit the worldgen as a non-judo
adult. The legends layer can render them periodically — *"[Sensei]'s
daughter became a chef in Manhattan. They speak weekly"* — without
requiring them to be active simulation entities.

**Adult children may return.** A non-judo adult child may decide later in
life to teach kids' classes at the dojo, especially after their own
children grow up or after personal-life shifts. This is the senior-
student-return event applied to family.

### Multiple children

The roll fires multiple times across a career. Different children get
different relationships to the dojo. A sensei with three children might
have one successor candidate, one occasional helper, and one estranged
adult child who hasn't been on the mat in twenty years. All three are
valid outcomes that the worldgen should produce.

The Yonezuka family example is instructive: Nick competed at Olympic
level, Natacha did not pursue high-level competition, Jack became the
third-generation Olympian. Three siblings, three different relationships
to the family discipline. The mechanic must support this kind of variance.

### What's deferred to post-1.0

**Tragedy events** — death of a child, death of a partner, serious
illness — are easy to design wrong and hard to design right. They are
also heavy material that requires careful authoring of legend-layer
prose. **Defer all tragedy events to post-1.0 content updates.** The
boycott event (in `one-year-of-worldgen.md`) provides enough heavy
material for 1.0.

**Partner career interactions** — a partner whose own career affects the
sensei's resource allocation, a partner who is also in martial arts, a
divorce — are similarly deferred. 1.0 models partners as background
context that enables family events but does not simulate their
independent trajectories.

### Why this mechanic matters

Most management games abstract family entirely. They ship a single-purpose
career optimizer where the player's avatar has no spouse, no children, no
parents to care for, no personal-life supply shocks. Hajime treating
family as part of the resource economy is the kind of move that makes
the systems-literate player notice that this is not a Kairosoft game.

It also gives the lineage system real generational drama. The Yonezuka
history is the children mechanic producing legend output across three
generations. Worldgen needs to be capable of producing that same kind of
arc procedurally for any sensei who plays it long enough.

The cost: family events touch personal-life territory that can land
heavily on players in difficult life situations. Authoring will need to
be careful, especially around child-rejection-of-parent outcomes and
adult-estrangement legend prose. The reward: the deepest version of the
"Legends Mode is the game" promise. Every multi-decade campaign produces
not just a dojo's history but a *family's* history, with all the texture
that entails.

---

## The trade-off pairs (the design surface)

These are the choices that produce the moment-to-moment play. Each pair
has a clear cost and a clear benefit.

### Train alongside students
- **Costs:** Energy, health.
- **Returns:** Reputation (local + student), student retention, recruitment
  bump from your visible competence, marginal money from retention.
- **Trade-off shape:** Bodily wear for community gravity.

### Spend hours on administration
- **Costs:** Attention-hours, lost on-mat presence (slowing student
  progress).
- **Returns:** Federation reputation (per the four procgen federations),
  unlocks tournament hosting, rank promotions, board nominations.
- **Trade-off shape:** Student outcomes for institutional standing.

### Marketing spend
- **Costs:** Money, small attention-hour spend for campaign management.
- **Returns:** Recruitment bump, slight reputation boost in local
  community.
- **Trade-off shape:** Capital for time and visibility.

### Facility investment
- **Costs:** Money, possibly attention-hours during construction phase.
- **Returns:** Health recovery for self and students (sauna), reduced
  injury rate (better mat surfaces), retention boost (better facility
  attracts and keeps students), reputation bump.
- **Trade-off shape:** Capital for systemic resilience across the dojo.

### Personal competition
- **Costs:** Energy, health, attention-hours, money for travel.
- **Returns:** Reputation (large in competition community, smaller
  elsewhere), student inspiration (retention boost), potential prize money
  at high tiers.
- **Trade-off shape:** Personal investment for legacy and credibility.

### Tournament hosting
- **Costs:** Money (large), attention-hours (large for the hosting period),
  small energy.
- **Returns:** Federation reputation (large), local community reputation
  (large), money (variable depending on attendance), increased visibility
  bringing in students.
- **Trade-off shape:** Concentrated spending for concentrated reputation
  and money returns.

### Cross-dojo seminars (giving)
- **Costs:** Attention-hours, travel money, time away from your dojo.
- **Returns:** Inter-dojo reputation, marginal income, exposure to
  potential transfer students.
- **Trade-off shape:** Reach extension for absence cost.

### Cross-dojo observation (attending others)
- **Costs:** Attention-hours, small travel money.
- **Returns:** Knowledge — observing rival dojos teaches you about their
  signatures and weaknesses (strategic information for competition
  matchmaking), improves your own coaching when you absorb techniques.
- **Trade-off shape:** Learning for time.

---

## Open design questions

**A. Do the four resources have visible numerical values, or are they
softer indicators?** A pure number-go-up dashboard collapses the
interesting design back to optimization. A purely qualitative indicator
makes the player guess. *Suggested default: visible bars/values for energy
and money (immediate), qualitative descriptors for health and attention-
hours (slow-changing). Reputation always qualitative — descriptive rather
than numerical.*

**B. How granular is the time unit?** Weekly scheduling is the natural
unit. Daily is too granular for a multi-decade game. Monthly is too coarse
for the texture of a sensei's calendar. *Suggested default: weekly
scheduling with monthly review summaries.*

**C. How do students' resource pools relate to the player's?** Each
student NPC has their own energy, health, mood, fatigue, and current
injury state. **All of this is visible to the player at a glance**,
following the Dwarf Fortress / Songs of Syx model — student cards or
rosters surface real-time state without requiring conversation. The
hidden-information principle remains load-bearing for **long-term
goals, aspirations, family situations, and relationship complications**,
which still require conversation to surface. The split: moment-to-
moment state is glance-readable; deep narrative information is
conversation-gated.

*Rationale: at twenty-five students, conversation-gated visibility on
basic physical and emotional state would produce cognitive overload that
breaks the play loop. The hidden-information principle works only when
applied to information that's worth hiding. A torn meniscus is not
narratively interesting to hide. A secret hope of competing
internationally despite a parent's wishes is. Different layers, different
visibility rules.*

**D. How does the federation-reputation system handle player vs. student
accomplishments?** When a student wins a national title, does the player's
federation reputation increase, the student's, or both? *Suggested
default: both, weighted by the player's coaching investment. Coaching a
student to a title gives the coach more reputation than the title alone
would give the student.*

**E. How does retirement work mechanically?** When the player's health
drops past a threshold, do they retire automatically, or do they have a
choice? *Suggested default: automatic retirement from physical activity
is forced by health = 0; voluntary retirement from competition is
available earlier. Retirement from coaching/admin is the player's choice
and triggers the multi-dojo retire-and-start-again loop already designed.*

**F. Do the four federations have overlapping or disjoint reputation
domains?** If federation A and federation B are rivals, does spending to
build reputation with A cost reputation with B? *Suggested default: yes,
mildly. Federations have rivalry levels rolled at worldgen, and reputation
spent with one slightly decreases standing with rivals. This produces the
political-allegiance texture without making it a primary mechanic.*

**G. How does the procedurally-rolled federation politics interact with
real-world federation history?** Procgen everything for federations,
with realistic naming conventions. The four federations rolled per
state are entirely fictional, named by procgen using believable patterns
(e.g., *"[State] Judo Federation," "Northern [State] Judo Association,"
"Eastern Judo Yudanshakai"*). They have rolled histories, rolled
presidencies, and rolled rivalries with each other. Real-world
federations (USJF, USJA, USA Judo, USJI) are not modeled in 1.0. **The
only fixed-history elements in the worldgen are Cranford JKC's 1962
founding in Cranford, NJ, and the founding sensei's name (Y.Y. or
equivalent two-initial Japanese surname).** The remainder of the world
is procgen.

*The Cranford anchor — clarified:* the dojo's name remains Cranford JKC.
The founding date is fixed at 1962. The founding sensei's name uses a
Japanese surname rendered as initials (Y.Y., or similar two-letter form)
and a procgen-rolled given name that honors the inspiration without
literalizing it. The sensei's competitive attributes, throw signatures,
coaching style, and personal trajectory are rolled per campaign. This
anchor can be revised — including by replacing the procgen sensei with
a fully named real-world figure — at the player's or developer's
discretion in future versions, with appropriate consent. See also
`one-year-of-worldgen.md` § *The Cranford anchor*.

---

## What this document does not specify

- **The scheduling UI.** That's the next document, and it follows from
  this model being committed.
- **Specific numerical values.** Energy supply, attention-hour budgets,
  reputation thresholds — these are tuning numbers that get set during
  implementation, not design.
- **The full relationship between the resource model and the existing
  dojo loop design** (v17 questions on lifecycle, antagonist, pricing).
  Those need a revision pass to align with the resource model, but that
  pass is its own future document.
- **The implementation architecture.** Where this lives in code, how
  Python and Godot communicate about resource state, how saves are
  structured. That's engineering, not design.

---

## Next steps

1. Review and push back on this draft. Especially the trade-off pairs,
   the aging curve, and the family layer — those are the load-bearing
   pieces.
2. Apply the one-year-worldgen revisions (✅ applied to
   `one-year-of-worldgen.md` on May 4–5, 2026).
3. Drop this document into the repo as `resource-model.md` (✅ this file).
4. Then design the scheduling UI as a separate document, working from
   this resource model as the underlying spec.

The scheduling UI is the natural deliverable. But it has to wait until
this model is committed. Designing UI for resources whose supply curves
haven't been decided produces UI that gets torn up.

---

*Drafted May 4, 2026, end of session. First cut + addendum integrated
(student visibility, procgen federations, family layer). Push back on
anything wrong. The next document is the scheduling UI — separate
session.*
