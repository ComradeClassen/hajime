# One Year of Worldgen

*The atomic unit of New Jersey judo simulation. Drafted May 4, 2026, following the worldgen-pivot conversation. First cut — meant to be pushed back on. Settles defaults, names open questions, surfaces the architectural cost.*

*Revised May 4, 2026 (end of session) with the revision package: competition
tier hierarchy, career-end event taxonomy, boycott events, senior-student-
return event, named-politics placeholder layer, lifespan / multi-tier career
model, and three new open questions. Cranford anchor clarified per the
resource-model addendum: procgen-everything for federations and the rest of
the world; only Cranford JKC's 1962 founding and the founding sensei's
two-initial Japanese surname (Y.Y. or equivalent) are fixed.*

---

## What this document is

This is the spec for a single year of worldgen output. It is not the full
worldgen design. It is the unit that the full worldgen design repeats across
six decades. If we can describe one year cleanly, the multi-decade arc falls
out of running this unit sixty-six times from 1960 to handoff.

The job of this doc is to surface, by being concrete about one year, the data
requirements, the rendering layer, the abstracted resolver, the legends
output, and the technology-era effects — so that the cost of the full
worldgen system is honestly visible before the work starts.

---

## The contract

A year is a state transition. It takes the world at year T and produces:

1. **The world at year T+1** — every living judoka has aged a year, dojos have
   gained or lost students, finances have moved, signatures have drifted,
   tournaments have produced winners.
2. **The chronicle of T** — a structured log of what happened during the
   year, most of which fades, a small fraction of which becomes legend.

The state vector for one year of NJ judo includes:

- **All living judoka.** Skill vector, rank, age, current dojo, lifecycle
  state, lineage. Probably 2,000–8,000 named individuals across the state at
  any given time, varying by era (fewer in 1960, more by 2010).
- **All operating judo dojos.** Cultural profile, sensei, roster pointers,
  finances, facility, reputation, lineage origin. Probably 20–80 dojos
  statewide depending on era.
- **All operating non-judo gyms.** BJJ schools (none until late 1990s),
  wrestling clubs (present throughout), boxing gyms (present throughout).
  Lighter profile than judo dojos but with population-flow effects.
- **The tournament calendar.** Regional, state, regional qualifiers, national
  qualifiers, Olympic-year qualifiers.
- **The active rulebook.** Which version of IJF rules is in effect (this
  matters most around 2010 leg-grab ban and a few other inflection points).
- **The technology era.** See below.

---

## The calendar of a year

The year divides into roughly four quarters. Most ticks within a year are
silent — a dojo runs its sessions, students train, no notable event fires.
The simulation logs only what gets remembered.

**Q1 (winter, January–March).** Regional tournaments. Indoor focus. Intake
season — kids' classes fill up after New Year's resolutions. The lightweight
churn season; many trial-week dropouts.

**Q2 (spring, April–June).** State championships. Qualification season. The
heaviest competitive period of the year. Notable upsets concentrate here.

**Q3 (summer, July–September).** Summer camps. Seminars from out-of-state
visiting senseis. Cross-training peaks — judoka travel between gyms, take
visiting BJJ classes, pick up techniques. The lineage-influence season.
Olympic years compress here for the few NJ judoka in contention.

**Q4 (fall, October–December).** Back-to-school intake. National qualifier
rounds in Olympic cycles. Year-end belt promotions. The roundup season.

Tournament density and notable-event frequency vary by quarter. Q2 is the
storytelling-rich quarter; Q1 and Q4 are the population-flow-rich quarters.

---

## The abstracted match resolver

This is the load-bearing technical commitment of worldgen. The full match
engine cannot run during worldgen — running 60+ years of simulated
tournaments through the deep engine would take days to generate a single
world. Worldgen needs a lightweight resolver.

**The lightweight resolver.** Each judoka has a sparse skill vector — maybe
five dimensions: tachiwaza, ne-waza, conditioning, fight IQ, signature
strength. A tournament bracket runs as probabilistic matchups. Higher skill
wins more often. Variance produces upsets at a calibrated rate. The output
of each match is winner, loser, score type (ippon/waza-ari/decision), and
*possibly* a tag indicating "this was notable."

**One notable match per tournament.** The resolver tags one match per
tournament as worth remembering — usually the final, sometimes an upset,
occasionally a coaching-storyline moment. The tagged match gets a single
sentence of texture from a procgen template library, written in the same
voice as the deep engine's prose.

**The deep engine activates only when the player watches.** Randori in their
own dojo, or a tournament their own student is competing in. Every other
match in the world stays in the resolver. This is the same technique CK3
uses for off-screen battles and DF uses for off-screen historical combat.

**The cost.** This is two match resolvers — the deep one already exists, the
lightweight one needs to be built and calibrated against the deep one so
that worldgen-generated rankings produce results consistent with what the
deep engine would have produced. The calibration work is real and ongoing.

### The competition tier hierarchy

The worldgen produces results across a stratified competition surface.
Each tier has its own cadence, geographic scope, and narrative weight.
Career arcs travel through these tiers — most never leave the lower ones,
some climb steadily, a few skip levels. The tiers, low to high:

1. **Dojo internals.** Twice-yearly invitationals, Saturday open-mats,
   in-house promotion tests. Most students only ever compete here. These
   produce belt promotions and small narrative beats, not legends.
2. **Local and city.** Town tournaments, multi-dojo round-robins. Kids'
   first away tournaments. Visible only when the player's dojo competes
   here.
3. **County and regional.** USJF/USJA regional events. State sub-regions.
   The first tier where rankings start to consolidate.
4. **State.** State championships. Where strong dojos start to know each
   other's senior students by name.
5. **National.** U.S. Senior National Championships, Junior Nationals,
   Master's Nationals, U.S. Open, National Sports Festival (existed
   1978–1995, defunct after; era-gated). Title here is career-defining.
6. **Continental.** Pan American Championships (annual), Pan American
   Games (every four years), Pan American Open. Liverpool World Cup
   tier events.
7. **International circuit.** Grand Prix series, Grand Slam series,
   Continental Opens, World Cup events (older format). The qualification
   feeder system for World Championships and Olympics.
8. **World and Olympic.** Junior World Championships (under-21), Senior
   World Championships (annual outside Olympic years), Olympic Games (every
   four years). World titles and Olympic medals are extremely rare events
   that the resolver must produce contingently, not on schedule.

**Master's circuit runs in parallel.** World Masters Championships, National
Masters titles, regional Masters events. Career judoka often re-enter
competition in their 50s and 60s through this circuit. The Masters circuit
is its own legitimate career arc, not a consolation prize.

**Fog-of-war reveals tiers gradually.** A new dojo sees only tiers 1–2.
Belt-up enough students and tier 3 unfogs. Send a competitor to a state
title and tier 4 becomes legible. Produce a national-level athlete and
tier 5 opens. This produces a progression curve independent of belt rank.

---

## What gets remembered

Most of a year fades. A typical 1980 judoka in NJ trained, sparred, won some
matches, lost some, and never produced a single legend-layer event. That is
correct. Legends are sparse by design.

The events that survive into the chronicle:

- Tournament finals (winner + opponent + score)
- First-time black belt promotions and above
- Olympic qualifications and medals
- Notable upsets (significantly lower rank beating higher rank in late rounds)
- Dojo openings and closings
- Sensei transitions (death, retirement, succession)
- Cross-dojo seminars by notable senseis
- Coaching defections (a high-profile assistant leaves dojo X for dojo Y)
- Student migrations from one dojo to another, when the student is notable
- **Senior-student returns** (former student rejoins the dojo after years
  or decades away — usually triggered by a personal-life event)

A 66-year history book at handoff is mostly empty — maybe 1,500–3,000 entries
across six decades, which sounds like a lot until you realize that's roughly
30 entries per year for an entire state. The sparsity is what makes legends
feel like legends. The Yamada upset of 1974 means something because it sits
in a year that has only 28 other entries.

### Senior-student returns

A judoka who left the dojo years or decades ago can re-enter the simulation
as a returnee. The trigger is usually a personal-life event — death of a
spouse, retirement from career, divorce, child leaving home. The return is
sometimes brief (weeks), sometimes permanent. Most legends pages will have
a few of these.

The mechanic underneath: **the dojo as continuity in a fragmenting life.**
A former student NPC is rolled at low probability per year for a
return-event check. If fired, they appear in the dojo's roster again with
a flag indicating returnee status. Their training is described differently
in the legends layer — *"came back briefly in 2004 after his wife passed,
stayed for nineteen months."*

This is one of the texture mechanics that distinguishes Hajime from
adjacent management sims. Football Manager players don't return to their
youth club after their wife dies. Judoka do.

### Boycott and political-disruption events

Real judo history includes Olympic-cycle events that interrupt
trajectory-bound careers. Worldgen must be capable of producing these,
because they are part of the texture that distinguishes a real career arc
from a simulated one.

**Boycott events** roll at low probability per Olympic cycle (under 5% per
Games is realistic). When fired, they affect a specifically rolled
political bloc — sometimes the host country's bloc declines, sometimes the
opposing bloc declines, sometimes a smaller geopolitical exclusion (the
post-2022 Russian/Belarusian model). Affected judoka are recorded as
*qualified but did not compete*. Their career records carry the asterisk
permanently.

**Mechanical effects** of being a boycott-affected judoka:
- Permanent psychological trait — increased coaching-investment probability
  in second-career roll
- Increased mentor-bond strength with future students
- Slight reputation bonus for "denied generation" within the federation
- Higher probability of remaining at original dojo (branch 1) at retirement

**Other political-disruption events** worth flagging for v1.0 or later:
- Weight-class restructuring (1996 IJF reorganization)
- Federation fragmentation events (the U.S. judo federation politics that
  shaped American judo for decades)
- Rule changes that retroactively redefine specialization (the 2010 leg-grab
  ban)

For 1.0, ship with the boycott event. Defer the others to content updates.

---

## Career-end event taxonomy

When a judoka stops competing, they don't disappear. The worldgen rolls a
**second-career event** that determines what they do next. This produces
the diaspora that makes a multi-decade dojo feel populated rather than
merely productive. The branches:

1. **Coaching at original dojo.** Stays as senior instructor. Becomes
   living memory of the dojo's older era. Often the slowest path but the
   one that preserves cultural continuity.
2. **Coaching elsewhere — opens own dojo.** Founds a new dojo, often
   nearby, sometimes far. Creates a new gravitational mass in the
   population-flow model. The branch event the lineage system needs in
   1.0.
3. **Coaching elsewhere — joins existing dojo.** Becomes head coach or
   senior instructor at another dojo, possibly competing one. Affects that
   dojo's signature and culture.
4. **National-team coaching.** Joins the federation coaching staff.
   Influences which national-team athletes succeed at the international
   tier. High reputation cost to access; high reputation reward.
5. **Federation administration.** Becomes regional president, state board
   member, eventually federation officer. Ranks promote, tournaments get
   sanctioned, rules get interpreted. Politics-layer entry point.
6. **Cross-discipline exit.** Leaves judo for another grappling/combat
   discipline (BJJ, sumo, MMA, professional wrestling, combatives). May
   succeed there in ways that reflect on the original dojo's reputation —
   Allen Coage going to WrestleMania, Yarbrough winning the sumo Worlds,
   Cestari and Ross founding combatives systems. The legends layer renders
   these exits with full dignity, not as failures.
7. **Disappearance.** Stops competing, stops coaching, leaves the
   simulation. Most judoka eventually take this branch. Sometimes returns
   decades later (see senior-student-return event).

**Probability weighting.** The second-career roll is not uniform. A judoka
who reached national-team status has higher probability of branches 1–5. A
judoka who topped out at state level is more likely to take branches 1, 6,
or 7. A judoka with strong cultural ties to the dojo is more likely to take
branch 1. Hidden goals rolled at character creation feed into the weighting.

---

## Named-politics placeholder layer

The worldgen produces a named federation politics layer for narrative
purposes in 1.0, with mechanical effects deferred to later versions.

**What's in 1.0.** Federation presidents have names. Rule changes have
named decision-makers attributed. Rank promotions are signed by named
officials. The legends layer renders these names. (*"[Sensei] was promoted
to 9th dan in 2007 by [State] Judo Federation President [name]. The
leg-grab ban of 2010 was finalized under IJF President [name]."*)

**What's deferred.** Mechanical effects of federation politics on the
player — sanctioning of player tournaments, voting privileges on rule
changes, board-meeting attendance requirements — are designed as future
hooks but not implemented in 1.0. The 1.0 system carries the data needed
for these effects to be added later without retroactive lineage rewrites.

**The four procgen federations.** Per the resource-model design, the
worldgen rolls four named federations across the player's region/state
that accumulate reputation separately. Each has a roster of named
officials, a procgen history of presidencies, and a placeholder ledger
of the rule changes they've voted on or against. This data is rendered
in legends and not yet connected to gameplay.

The federations are entirely procgen, named with believable patterns
(e.g., *"[State] Judo Federation," "Northern [State] Judo Association,"
"Eastern Judo Yudanshakai"*). Real-world federations (USJF, USJA, USA
Judo, USJI) are not modeled in 1.0. See `resource-model.md` Open Question
G for the rationale.

---

## Lifespan / multi-tier career model

The worldgen models judoka careers across the full lifespan, not just the
competitive prime. The career stages:

- **Kids (under 13).** Dojo internals and local events only. High dropout
  rate. Beltups are slow and ceremonial.
- **Juniors (13–20).** Cadet, junior, and U21 international competition.
  Junior World Championships are the proving ground. Many never compete
  again after this stage.
- **Seniors (21–35).** Peak competitive years. The Olympic, Worlds, and
  Continental tiers happen here. Fewer than 5% of judoka who entered as
  kids reach this tier with notable results.
- **Veterans (36–50).** Late competition. Most have transitioned to
  coaching or administration. A small fraction continues at Masters
  events.
- **Masters (50+).** Veterans World Championships, National Masters
  titles. Genuine competition with its own ranking system. Many alumni
  return to the mat in this stage after decades away.

A **single judoka's career arc spans 50–60 years** if they stay in the
sport. The senior student in your dojo who's 70 and still teaches kids'
classes once a week is a real character type, and worldgen generates them
naturally as veterans of the 1970s and 1980s who never left.

**Career-end probability distributions** vary by stage. Most kids drop out.
Most juniors stop after their last Junior Worlds eligibility. Seniors
either ascend to international relevance or transition. Masters who reach
their 60s mostly continue indefinitely until health intervenes.

---

## The Cranford anchor

Whatever else the worldgen produces, in 1962 a judo dojo opens in Cranford,
NJ. The dojo's name is fixed: **Cranford JKC**. The founding date is fixed
at **1962**. The founding sensei's name uses a Japanese surname rendered
as initials — **Y.Y.**, or an equivalent two-letter form — paired with a
procgen-rolled given name that honors the inspiration without literalizing
it. Everything else about the sensei is rolled per campaign: competitive
attributes, throw signatures, coaching style, lineage origin, personal
trajectory across decades. The eventual fate of the dojo across the
campaign is also rolled.

This is the game's personal anchor. It costs nothing mechanically — the
worldgen seeds one entity at one location at one date with a fixed
name-shape — and it gives every campaign a shared reference point that
ties the procedural to the personal. A player who has played multiple
campaigns will see Cranford JKC produce different histories each time, but
it will always be in Cranford and it will always have started in 1962
under a sensei whose surname renders as Y.Y. That continuity-amid-variation
is exactly the texture DF achieves with its Tarn-named-after-Tarn easter
eggs at scale.

The worldgen never overwrites this. If procgen would have placed a
different dojo in Cranford in 1959, it doesn't — Cranford is reserved. If
procgen would have closed Cranford JKC in 1985, it doesn't — Cranford
persists.

This anchor can be revised in future versions — including by replacing the
procgen sensei with a fully named real-world figure — at the player's or
developer's discretion, with appropriate consent.

(The implicit cost: every other place becomes procgen-fungible. Newark
might have a dojo in one campaign and not another. Princeton might be
judo-rich in one world and a desert in another. Only Cranford persists.)

---

## Technology eras

The technology era is part of the world state. It has mechanical effects, not
just flavor. The eras are roughly:

**1960–1985: Paper and Radio.** Records kept in pen on legal pads.
Tournament results spread by phone calls between senseis and one or two
regional newspapers covering local sports. National rankings are
near-invisible to anyone outside the major hubs. A judoka in Trenton may
not know who the top middleweight in Bergen County is unless they meet at
a tournament. Information is geographically local. *Mechanical effect:* the
player's roster surface is a paper notepad; rankings beyond the player's
direct attendance are unknown unless explicitly investigated.

**1985–2000: Phone and Fax.** Tournament registration moves to fax.
Long-distance phone calls let senseis stay in touch across the state. VHS
tapes of national-level matches circulate informally. Rankings start to
consolidate. *Mechanical effect:* the player can phone-network for
information at a small attention cost. National rankings are partially
visible.

**2000–2015: Email and Web.** Dojo websites appear. Email lists distribute
seminar announcements. Digital cameras let dojos record technique sessions.
Online forums (Judoforum, Bullshido) start propagating reputation faster
than word-of-mouth ever could. *Mechanical effect:* roster surface upgrades
to a computer (the existing notepad-to-computer transition from Q11 in the
design questions doc, but now era-gated rather than facility-gated). Online
reputation propagation accelerates the cultural feedback loop's word-of-mouth
component.

**2015–present: Smartphone.** Video instantly shared. Social media drives
reputation in real time. Olympic medalists become recognizable to casual
observers. A young judoka can study elite-level technique from their phone.
*Mechanical effect:* information flow is fast and asymmetric — a single
viral randori clip can reshape a dojo's reputation overnight. The player
gets new attention-economy pressures (responding to online presence) and
new opportunities (recruitment via social media).

The notepad-to-computer transition originally framed in the design questions
as a facility milestone now becomes era-gated by default, with facility
upgrades acting as multipliers. This is a cleaner mechanic than the original.

---

## Rules evolution

The IJF rulebook has changed across the worldgen window. The biggest
inflection points:

- **1960s–early 1970s:** legacy rules, leg grabs legal, golden score not
  formalized.
- **1980s:** point system formalizes, first major rule consolidations.
- **2010:** leg grab ban (kani-basami already banned earlier). This is the
  big rules cliff — pre-2010 worlds let drop-knee-style leg-grab throws
  function; post-2010 they're hansoku-make.
- **2017:** further refinements to grip-fighting penalties.

For worldgen purposes, each match is tagged with the era's ruleset. The
abstracted resolver doesn't need to fully model rules — it just needs the
*style distribution* to differ by era. Pre-2010 worlds produce more
leg-grab-finalists. Post-2010 worlds don't. The deep match engine can later
be extended to support era-specific rules for matches the player watches in
a non-modern campaign; for the first version of worldgen, all matches use
modern rules and the era-tag is data-only — accurate enough that the
legends layer can describe a 1975 match with period-correct flavor without
the engine needing to actually simulate kani-basami.

Cost flag: actually simulating period-correct judo rules in the deep engine
is real work. Defer it. Worldgen records the era; the engine catches up
later or never.

---

## New Jersey geography and population

NJ has 21 counties and a real population distribution that should drive dojo
density. Major hubs by population (rough order, varying by era): Newark,
Jersey City, Paterson, Elizabeth, Edison, Toms River, Trenton, Camden,
Hamilton, Clifton, Cherry Hill. Cranford sits in Union County — mid-density,
suburban.

**Density rules.** A city of 250,000+ supports multiple dojos competing for
students. A town of 30,000 supports one dojo if any. Rural areas support
none. The worldgen places dojos with density weighted by real population,
modulated by era (1960 NJ had less martial-arts presence per capita than 2010).

**Geographic friction.** Population flow between dojos has commute friction.
A student in Bergen County does not realistically commute to Atlantic
County. The flow model is local — neighboring towns, same county, adjacent
counties. Cross-state migration (a judoka moves to NY for college) leaves
the simulation rather than redistributing within it.

**The Cranford neighborhood.** Cranford is in Union County, adjacent to
Newark and the Elizabeth corridor. Realistic competing dojos for Cranford
JKC's student population: Newark dojos (large urban), Edison dojos
(suburban), Westfield/Summit area dojos (affluent suburban). The worldgen
should place a few of these consistently enough that Cranford JKC has
believable competitive context, even if the specific competing dojos are
procgen.

---

## The non-judo gyms

Wrestling clubs are present throughout the worldgen window. NJ high school
wrestling is real and significant; the worldgen should reflect it.

Boxing gyms are present throughout, more concentrated in urban areas.

BJJ schools begin to appear in NJ in the late 1990s, expanding rapidly through
the 2000s and 2010s. By 2020 NJ has dozens of BJJ schools, many of which
exert real gravitational pull on judo populations.

Each non-judo gym has a simpler profile than a judo dojo — name, location,
discipline, rough quality tier, current student count. They don't carry
full lineage data. Their role in the simulation is gravitational: they pull
on the local martial-arts population, especially when students aren't
getting what they need from their current dojo.

**The pull mechanic.** A judo student whose hidden goals don't align with
their dojo's offering — who wants more ne-waza than their judo dojo
provides, who wants a competition focus their judo dojo doesn't have, who
wants a culture their judo dojo isn't building — has a chance per quarter
to investigate alternatives. If a nearby gym better matches their unmet
need, they migrate. The worldgen records the migration and the reason. The
records page can later show: *Marco trained with us 2018–2021. Left to
pursue ne-waza specialization at Garden State BJJ.* Not "stolen by enemy."
A real, legible reason.

This is the version of the faction layer that respects how martial arts
actually share populations. No tribal warfare. Just gravitational
competition for finite human attention.

---

## Player handoff

When worldgen completes (at the player-chosen handoff year, default
present-day), the player gets:

1. **A history book.** Browsable legends, organized by year, by dojo, by
   notable individual. Cranford JKC has its own page from 1962 onward.
2. **A current-state snapshot of NJ judo.** Active dojos, current rankings,
   notable active judoka, recent tournament results, regional reputation
   landscape.
3. **An opening choice.**
   - **First run / tutorial:** locked to basement-or-garage-from-scratch.
     The tutorial path. Teaches the cultural feedback loop from zero.
   - **Subsequent runs:** choice of (a) basement again, (b) inherit a
     mid-tier dojo from a worldgen-generated retiring sensei, (c) buy out
     a struggling existing dojo with reputation baggage, (d) take over an
     established dojo with an Olympian on the roster — the "advanced
     start" option.

Each opening choice has different starting conditions, different inherited
relationships, different cultural baggage, different financial position.
The basement is hardest and slowest; the established-dojo start is the most
mechanically loaded but you inherit problems too.

---

## Open questions

Real ones, not rhetorical ones.

**A. Is worldgen visible to the player as it generates, or produced silently
and presented as a finished history book?** DF shows worldgen visually with
its little growing map and population counter. CK3 doesn't. Showing it
makes worldgen itself a piece of entertainment; hiding it makes the
handoff cleaner. Cost differs significantly. *Suggested default: silent for
1.0, visible-toggle in a later version.*

**B. Is each campaign a fresh worldgen, or does the player play in a "default
NJ" that's been generated once and stored?** DF is fresh every fortress.
CK3 is fixed historical setting. Comrade's stated inspirations point toward
fresh-each-time. *Suggested default: fresh worldgen per campaign, with a
seed system so a notable world can be replayed or shared.*

**C. Can the player choose their handoff year?** Default present-day, but a
"start in 1985" or "start in 2010" option would be a different game — older
tech era, different rules, different cultural moment. *Suggested default:
handoff is always at the worldgen's end-year (present-day) for 1.0; era
choice is post-EA.*

**D. How rich is the legends-rendering layer?** A history book of bare facts
("1968: Yamada wins state.") is boring. The trick is producing *narratives*
— notable upsets that feel notable, lineages with texture, dojo histories
with arcs. This is real authoring/design work. The procgen template library
needs significant content to produce variety. *This is the biggest hidden
cost in the worldgen system.*

**E. How does the abstracted resolver get calibrated against the deep engine?**
If worldgen produces a national champion in 2015, and the player encounters
that champion in a deep-engine match, the champion needs to feel like the
deep engine's idea of a national champion. The two resolvers must agree on
what skill levels mean. *Suggested approach: build the abstracted resolver
as a probabilistic surrogate of the deep engine, calibrated by running both
on the same matchups during development.*

**F. What happens to the existing Ring 2 dojo loop design?** Most of the v17
design questions remain valid — the calendar, sessions, conversations,
pricing, lifecycle, antagonist. But the *antagonist* specifically becomes a
worldgen entity (some procgen rival owner with rolled motivations) rather
than the cartoon-villain "slimy suit" of the v17 doc. The Inheritance Event
becomes a worldgen-generated father-figure-and-his-dojo. Several v17
answers need to be revised or recast. *This is the real architectural
cost of the worldgen pivot.*

**G. Cranford JKC's specific seeded sensei: rolled or named?** The dojo's
existence is fixed and the founding sensei's surname renders as Y.Y. (or
equivalent two-initial Japanese form). The given name and competitive
attributes are rolled. *Resolution under the resource-model addendum:
name-shape fixed, full identity rolled. The two-initial surname carries
the personal anchor; the rolled attributes vary so each campaign's
Cranford has a different texture. Future versions may revisit naming the
inspiration directly with appropriate consent.*

**H. Project-level: is this a Ring 2 expansion or a Ring 3 rebuild?**
Worldgen is a substantial new subsystem. It probably doesn't slot into Ring
2 cleanly — Ring 2 is the dojo loop. Worldgen is a layer underneath Ring 2
that produces the world Ring 2 takes place in. *Resolution: the master doc
formally adopts worldgen as Ring 2, with the dojo deep-dive moving to
Ring 3 and subsequent rings shifting up by one. The 2-3 year EA horizon is
now a 3-4 year horizon.*

**I. How are the four named federations rolled per state?** Real federation
politics in the U.S. has USJF, USJA, USA Judo, and USJI as actual entities.
Should worldgen use real federation names where they map to real history,
or always procgen-name them? *Resolution under the resource-model addendum:
procgen-everything for federations. The four federations rolled per state
are entirely fictional, named with believable patterns. Real-world
federations are not modeled in 1.0. See `resource-model.md` Open Question
G for the full rationale.*

**J. How does the boycott event interact with non-NJ states in future
content updates?** A 1980-style boycott affects Olympic-tier judoka
nationally, not just New Jersey. When other states ship as content, the
1980 boycott event in their worldgens needs to be the *same* event — not
each state rolling its own independent boycott. *Suggested default: a
small set of national/global events (boycotts, rule changes, IJF
reorganizations) ship as fixed-history events that apply uniformly across
all state worldgens. Each state's worldgen is otherwise independent.*

**K. How does the second-career roll handle judoka who *also* compete in
Masters?** A retired senior who continues at Masters tier hasn't fully
retired. Is Masters competition a separate roll from second-career, or do
they coexist? *Suggested default: they coexist — Masters competition is a
parallel layer that runs alongside whatever second-career branch the
judoka took. A senior who teaches at Tech Judo while winning Masters
titles in his sixties is two layers running simultaneously.*

---

## What this changes about the master doc

If this design lands, a few master-doc updates follow:

- The opening scenario reframes. Basement is the tutorial path; worldgen
  produces the alternative paths.
- The antagonist becomes worldgen-generated.
- The Inheritance Event becomes worldgen-generated.
- The lineage data model from 1.0 (Q15) is now load-bearing for worldgen,
  not a Ring 4 hedge. The entire critique made about lineage being
  overinvestment evaporates.
- Q16 (dojo records) gains a real systems reason to exist — the records
  page is the legends-mode readout for the player's dojo across the
  worldgen window plus their tenure.
- The six cultural inputs survive but get reframed: they're not just the
  player's levers, they're also the *worldgen's levers*. The procgen senseis
  in the world also accumulate cultural decisions; the cultural feedback
  loop runs on every dojo, not just the player's.

*All of the above landed in the master doc rewrite of May 5, 2026. See
`hajime-master-doc.md`.*

---

## Summary

A year of worldgen produces 30-ish remembered events from thousands of
silent ones. It runs probabilistic tournaments on a sparse skill vector
across an eight-tier competition hierarchy, flows population between gyms
based on hidden goals and gravitational pull, records dojo openings and
closings and sensei transitions, fires career-end events that spread
retiring judoka across a seven-branch diaspora taxonomy, occasionally
interrupts trajectories with boycotts and other political-disruption
events, and tags era-specific rules and technology context to everything
it generates.

The unit is small. The compounding effect across 66 years is the world
the player inherits.

The biggest costs are the abstracted resolver (which needs calibration
against the deep engine), the legends-rendering layer (which needs real
authoring depth to produce narrative-feeling output), and the project-level
framing question (now resolved — worldgen is Ring 2, dojo deep-dive is
Ring 3, EA horizon shifts to 3–4 years).

The biggest wins are that the worldgen pivot solves several existing design
problems at once — authored opening becomes one rolled outcome among many,
cartoon antagonist becomes a procgen rival with real motivations, lineage
data pays for itself in 1.0, the Q16 records page gets a real reason to
exist, and the cultural feedback loop scales from one dojo to a state.

---

*Drafted May 4, 2026, end of session. First cut + revision package +
addendum Cranford clarification, all integrated. Push back on anything
wrong; push on anything underdeveloped. The next document is the full
Ring 2 spec, which extends this one with the abstracted resolver's
calibration plan, the legends-rendering authoring strategy, the
state-module architecture, the fog-of-war mechanics, and the
technology/rules era handling. After that, the scheduling UI design (which
follows from `resource-model.md`).*
