# Dojo Loop Design Questions
### Reshape of Ring 2/3/4 — complete first-pass design, now in triage phase

*Drafted April 23, 2026, mid-week between Session 4 and Session 5. Triggered by the realization that the real gameplay loop is "run a dojo, develop students, go to tournaments with them" — not "coach during a match, with a dojo for context." The original January 9, 2027 ship date has since been recognized as a personal milestone marker (Comrade's birthday), not a hard deadline. The scope of the design that emerged from this document exceeds what any solo dev ships in 9 months; the real horizon is 2–3 years to Early Access, with January 9, 2027 reframed as an internal checkpoint — "further than where I began." See chat for the quarterly breakdown.*

---

## Quick-reference: open sub-questions

All 12 core questions have been answered. What remains is a flat list of tactical sub-questions that opened during the week's work. Return to any of these to think them through — they don't have to be answered in order, and most aren't blockers for the high-level scoping triage.

**Lifecycle (Q1):**
- **Q1a-i** — Should quit probability be visible to the player, or hidden with proxies?
- **Q1a-ii** — What's the target first-year quit rate for the "trial by fire" feel (20%? 40%?)?
- **Q1b-i** — Is a student's competition preference visible by default, or only revealed through conversation?
- **Q1b-ii** — Can sensei influence on competition preference fail outright?
- **Q1d-i** — The reputation formula: what inputs (departures, destinations, results, retention, culture axes) compose into the reputation score?
- **Q1e-i** — Are belt promotions scripted ritual moments (a scene, a ceremony) or stat updates with notifications?
- **Q1e-ii** — Can a student refuse a promotion the sensei offers?

**Economy / antagonist (Q2):**
- **Q2a** — How often does the suit visit when savings are below threshold? What's the escalation cadence?
- **Q2b** — On recovery, does his next visit start from step 1 or resume where he left off?
- **Q2c** — Is there a grace period at zero savings before losing the dojo?
- **Q2d** — Can the sensei change prices freely, or are there frictions (notice periods, grandfathering existing students)?
- **Q2f** — Does the sensei know a student's potential at arrival, or is it blind (revealed through conversation)?
- **Q2g** — Do high-paying students actively complain when neglected, or is it silent retention pressure?
- **Q2h** — Can the sensei self-subsidize a talented student indefinitely from dojo savings?

**Opening scenario (Q7a):**
- **Q7a-i** — Does the calendar start empty for the player to fill, or with a pre-set opening schedule?
- **Q7a-iii** — Is the father's style choice locked for the run, or can the dojo's style evolve over time? (Partially answered by Q13 — the Inheritance Event choice is itself a style-direction commitment.)
- **Q7a-iv** — Exact starting numbers: savings, rent, class revenue, class cost. Opening difficulty curve lives here.

**Session composition (Q7b):**
- **Q7b-i** — Which 10–15 activity types form the January activity library?
- **Q7b-ii** — How do students respond when a session's composition mismatches their skill level?

**Culture & psychology (Q8):**
- **Q8a** — What are the dojo culture axes? Is the {chill / fun-for-kids / companion / trial-by-fire} set complete? Are axes independent or constrained?
- **Q8b** — How fast do long-term goals shift — weeks, months, or years in-game? Event-triggered or gradual?
- **Q8c** — Minimum viable needs count per student for January (2? 3? 5?), and which ones?
- **Q8e** — Can the player deliberately shift dojo culture mid-run, or does accumulated momentum resist? What's the cost of a pivot?

**Rankings (Q12):**
- **Q12a** — Which ranking tiers get meaningful simulation for January vs. sparse narrative layer?
- **Q12b** — Are rankings publicly visible on a screen, or surfaced only as a scouting cost mechanic?
- **Q12c** — Are all ranked judoka simulated continuously, or statistical ghosts who only materialize when your student faces them?

**The Inheritance Event (Q13):**
- **Q13a** — Time ceiling: does the event fire regardless if economic/belt conditions aren't met by year 5?
- **Q13b** — What happens to students at the dojo the player leaves behind — scatter, follow, or come under new management?
- **Q13c** — Are there other "moments of destiny" later in the campaign (Olympic decisions, lineage splits, antagonist challenges)?
- **Q13d** — Can the player refuse both dojos outright?

**Career Mode and Narrative Events (Q14):**
- **Q14a** — ~~Is there a defined ending to Career Mode?~~ Partially resolved by Q15: retirement + succession is the Career Mode ending. Remaining: is retirement timing player-chosen or age-forced?
- **Q14b** — How many major narrative events ship at EA?
- **Q14c** — Are events fixed in sequence, or adaptive to player state?
- **Q14d** — Does the player choose Career vs. Sandbox at game start, or transition mid-run?
- **Q14e** — Does a partner/spouse affect the dojo mechanically, or narrative-only?
- **Q14f** — First Team Tournament vs. Inheritance Event timing resolution.

**Lineage (Q15):**
- **Q15a** — Can successor-start runs chain infinitely, or does lineage eventually terminate?
- **Q15b** — Does the successor-start variant preserve physical dojo and facility upgrades, or just reputation and roster?
- **Q15c** — If the player retires without choosing a successor, what happens to the dojo?
- **Q15d** — Is lineage data exportable/shareable (community feature, probably post-1.0)?

---

## What triggered this

In the chat preceding this document, Comrade described a mode where the main gameplay loop is the coach running their dojo day-to-day: procedurally generated students walk in at various commitment levels, some drop out after a free week, some plateau at yellow/green belt, some stay for years, some become champions. The emotional spine is the gradient — attachment to students who may or may not make it. Ring 1's matches become consequential events inside this loop, not the loop itself.

This reshape expanded Ring 2, pulled some Ring 3 content forward, and revealed that the original Scenario A/B/C framing and January 9, 2027 ship date were both built before the real design existed. Both have since been recalibrated — see the chat for the updated timeline.

---

## Answered so far

### Q5 — The coach's sensei. ANSWERED.

**Answer:** There is no sensei above the coach. The coach **is** the sensei — the senior authority of the dojo.

The sensei:
- Directs what is taught in classes
- Decides who goes to tournaments
- Runs weigh-ins at tournaments
- Assigns black belts as coaches for other students
- Assigns brown belts to teach the kids' classes

**Architectural consequence:** there is no relational layer above the player. The player is at the top of the dojo hierarchy. The upward-relational mechanic (mentor, legitimacy pressure) is out of scope for the January release. Relational layers go sideways (to students) and downward (to assistant coaches / kids' class teachers), not upward.

**What this simplifies:** the whole "managing reputation with a sensei who sent students your way" subplot drops out. What remains is ownership — you are the dojo.

---

### Q4 — Auto-battler volume and attention. ANSWERED.

**Answer:** The Tournament Attention Economy generalizes. It isn't a tournament-specific mechanic — it's the core attention mechanic at every scale of the game.

Concretely: in a randori session with ten students on the mat, five sparring matches run in parallel. The sensei can watch one at a time. The watched match resolves with granular detail — specific grip improvement, technique progression, composure moments, IQ development. The other four matches resolve naturalistically — students improve on random axes (grip, experience, technique, composure, IQ) without the coach seeing the specifics.

**Architectural consequence:** the match engine needs two rendering paths from the same underlying simulation:

1. **Watched-match path.** Full prose rendering. The path Session 5 is cleaning up. What the coach sees.
2. **Unattended-match path.** Fast resolution. Outcome + coarse improvement deltas. No prose. What happens on the other four sparring pairs while the coach is watching one.

This is the same tech that Ring 3 will need for background simulation (students training while the coach isn't at the dojo, world-simulation Ring 4+ style). Building the unattended path now pays forward.

**What this means for design:** attention is the scarcity mechanic across the entire game. Tournaments: three fighters, one chair. Randori: five pairs, one sensei. Dojo management: many students, limited weekly attention. Same primitive, different scales. This is probably a thesis-level design principle worth naming in the master doc.

---

### Q8 — Student inner lives. ANSWERED.

**Answer:** Students have independent inner lives. This pulls directly from Player Two's architecture — immediate needs (Dwarf Fortress style) plus long-term goals that can evolve over time based on experience.

Structure:

- **Immediate needs.** The short-term state — wants exercise, wants social connection, wants to have fun, wants to be seen. The Dwarf Fortress temporary-state layer.
- **Long-term goals.** The current ambition — "make dad happy," "get to black belt," "compete at nationals," "teach." One primary goal at a time.
- **Goal evolution.** Goals shift when experience changes the student. Marco (10) starts with "make dad happy" → the fun kids' class fulfills his needs → goal shifts to "become a champion." James starts with "just exercise" → stays long enough to care → goal shifts to "black belt." Amanda starts competitive → finds something she loves more → goal shifts to "teach." The shift is emergent, not scripted per character.

**Architectural consequence 1 — Player Two transfer is live.** This is exactly what the master doc predicted: building Hajime advances Player Two's architecture. The needs/goals/shift structure here is the foundation of the Player Two psychology layer, arriving earlier than planned. Worth noting in the master doc's "relationship to Player Two" section when the doc-pruning pass happens.

**Architectural consequence 2 — atmosphere as a coach decision axis.** "Make the kids' class fun" is now a real coach choice, not a narrative flourish. Atmospheric decisions (game-based vs. competitive, relaxed vs. strict, collaborative vs. trial-by-fire) have emergent effects on students whose needs happen to align with the atmosphere. The coach isn't manipulating student goals directly — they're shaping the environment that shapes the students.

**Architectural consequence 3 — dojo culture as emergent property.** Your aggregate choices produce a dojo with a character: chill, fun-for-kids, companion-oriented, trial-by-fire. The culture is emergent, not authored — it's what your choices add up to.

**Architectural consequence 4 — the cultural feedback loop.** (Thesis-level insight, sibling to the attention scarcity principle.) The dojo's emergent culture attracts specific kinds of procedurally generated students. Trial-by-fire dojos attract students seeking intensity. Fun kids' dojos attract families looking for warmth. The students who walk in are biased by the reputation your choices have produced. Your early choices cast a long shadow — the dojo you end up running is downstream of the culture your first choices seeded.

**What this means emotionally:** you can't keep them all, you can't satisfy them all. That's the core tension. The students you lose matter because each one represents a choice you couldn't make in their favor. The students who stay matter because their goals happen to fit the dojo you're becoming.

**What this means for January:** the full Player Two-depth psychology layer (needs, facets, beliefs, memories, stress) is out of scope. A stripped-down version — 1–3 needs per student, one current long-term goal, a small number of goal-transition templates, a 2–3 axis dojo reputation that biases new arrivals — is probably what ships. The minimum-viable spec is a sub-question that needs its own thinking (Q8c below).

**Sub-questions this opens:**

- **Q8a — Dojo culture axes.** Is {chill / fun-for-kids / companion / trial-by-fire} the complete set, or are there more? Are the axes independent, or does position on one constrain position on others?
- **Q8b — Goal shift tempo.** How fast do long-term goals change? Over weeks, months, years of in-game time? Tied to specific events (a tournament loss, a belt test), or gradual pressure from accumulated needs?
- **Q8c — Minimum viable needs per student for January.** How many axes? Which ones? Exercise, social, recognition, challenge, belonging — what's the smallest set that still produces differentiated students?
- **Q8d — Reputation propagation.** How does dojo reputation reach new arrivals? Word-of-mouth narrative events, or just a silent bias on procedural generation?
- **Q8e — Culture momentum.** Can you deliberately shift your dojo's culture mid-run, or does the momentum resist (because current students, assistants, and facilities reflect the old culture)? Does a "pivot" cost you?

**Implications for other open questions:**

- **Q1 (lifecycle):** goal shifts should probably be first-class lifecycle events alongside belt advances and competition milestones.
- **Q3 (coach decisions):** atmospheric / tone choices become a decision axis. "What kind of class am I running today?" is a real lever, not flavor.
- **Q6 (interface):** the watched-student view probably needs to surface their current needs and long-term goal — otherwise the granular-attention mechanic has nothing to show.
- **Q9 (dojo Anchoring Scene):** "Marco's goal shifts from pleasing dad to wanting to be a champion" is a strong candidate. It captures the whole architecture in one moment.

---

### Q7 — Tempo. ANSWERED.

**Answer:** Player agency over simulation depth. Modeled on Football Manager. The simulation runs continuously at whatever speed the player chooses — from granular hour-by-hour session rendering down to weekly or monthly time-lapse. Events (injuries, quit notices, competitions, scheduled milestones) pause the clock regardless of zoom level.

**The core mechanic — calendar as session planner.** The coach sets up the dojo's weekly schedule like a Google Calendar. Each session is a block of time with a focus. Sessions cost something — money, facility capacity, coach energy — so the player starts with limited capacity and earns more as the dojo grows.

Examples from the brief:
- Tue/Wed/Thu 5–6pm kids' class, 6–7pm adult fundamentals, 7–8pm green-and-above
- Morning/noon/afternoon/evening variations
- Weekend blocks (4-hour Saturday randori)
- Theme days (ne-waza day, women's judo day)

**Student availability as a matching mechanic.** Students have their own lives — jobs, school, kids. Their attendance is constrained by when the dojo offers sessions that match their availability. Kids only attend after-school times. Working adults only attend evenings or weekends. If your calendar doesn't have slots that fit a potential student's life, they don't come.

**Zoom levels:**

1. **Hour-by-hour.** Full Ring 1 match-engine rendering inside a specific session. The player picks a student to watch (the Q4 mechanic nests here). Most granular.
2. **Weekly.** Set a focus/priority for the week, let it play.
3. **Monthly / seasonal.** High-speed simulation — e.g., January–March steady-state.
4. **Event-pause layer.** Regardless of zoom, time stops for injuries, quit notices, competitions, milestones.

**Competition ramp as a natural rhythm.** Example from the brief: competition in April, so January–March runs steady-state, then two weeks before the competition the player zooms in to intensify training, add weight cutting, manage injury risk.

**Architectural consequence 1 — continuous simulation, render-on-demand.** (Thesis-level principle, third alongside attention scarcity and cultural feedback.) The engine runs at a consistent base tick rate; what changes with zoom level is how much of that simulation gets rendered. This is the Football Manager architecture — the match is always happening; the player decides whether to watch each kick or just see the final score.

**Architectural consequence 2 — calendar as first-class data structure.** Sessions, times, focuses, attendance patterns, recurring schedules all need modeling. Substantial UI and substantial state.

**Architectural consequence 3 — student availability model.** Each student's identity includes when they can attend — school-age, working-adult, retired, shift-worker, weekend-only, etc. This is a new axis in student identity at generation time.

**Architectural consequence 4 — session focus as the primary lever for development and culture.** What happens in a session (kids' games, randori, drilling, ne-waza, competition-prep intensity) is the real input to student growth AND dojo culture. Q3's "atmosphere as coach decision axis" and this are the same mechanism viewed from two angles.

**Architectural consequence 5 — culture shift tempo.** (Also partially answers Q8e.) Culture is a slow-moving variable. Brief's metaphor: "a big ship you have to turn very slowly." Changing a dojo's character takes months of sustained calendar and focus choices, not a single week's decisions.

**What this means for January — scope honesty.** The full Football Manager multi-zoom architecture is genuinely ambitious. Sports Interactive spent years getting it right. The good news: Ring 1's match engine already IS the hour-by-hour zoom. The new work is (a) calendar UI, (b) time-scaling controls, (c) aggregated-naturalistic-simulation for zoomed-out views, and (d) event-pause infrastructure. Minimum-viable for January: calendar with preset session templates, a small set of speed settings (daily / weekly / monthly), event pauses, and the existing granular match engine as the zoom-in mode. Full custom-calendar flexibility might be stretch.

**Partial answers to other questions:**

- **Q2 (economic layer):** sessions cost money. The economic layer has concrete mechanical bite — not just "can't afford transport" but "can't afford to offer more classes." Calendar capacity is downstream of finances. Q2 upgrades from "decide role of economic layer" to "economic layer has at least this function, decide if more."
- **Q3 (coach decisions):** calendar setup IS the central coach decision. Individual-day choices (who teaches, who pairs with whom) sit inside the calendar structure. Most decisions may happen at weekly/monthly planning time, not every day.
- **Q4 (attention):** granular-watched-student nests inside zoom. Zoom to a session → pick a student to watch. Multi-level zoom.
- **Q6 (interface):** the dojo interface is now substantially defined. Calendar view at center. Session detail on click. Student list. Zoom controls. Event-alert layer.
- **Q8e (culture momentum):** partially answered — culture shift takes months of sustained calendar/focus input. Big-ship metaphor confirmed.

**Sub-questions this opens:**

- **Q7a — Initial session capacity.** ANSWERED. Three classes at start — the break-even point. Adding more draws from savings. See full answer below.
- **Q7b — Session cost model.** Money only, facility rental, coach fatigue, combination? Does cost scale with session length or session focus?
- **Q7c — Aggregate simulation fidelity.** When running at weekly/monthly speed, what level of per-student update do you get? Every randori simulated silently with skill deltas? Statistical improvement? This matters for min-maxers who need to trust fast-sim isn't cheating them.

---

### Q7a — Starting conditions and opening narrative. ANSWERED.

**Answer:** The game opens with the sensei moving out on his own to open a basement dojo. First month's rent paid. Modest savings. The player can schedule three classes at break-even; adding more draws from savings. Father's lineage is the starting cultural DNA.

**Opening scenario (January release).** Your father ran a successful dojo — either in Japan or in another state. You're starting fresh: a small basement, first month paid, a bit of savings. The player chooses a style their father was good at. That style becomes the dojo's starting identity, not a locked constraint.

**Alternate opening (post-January).** Inheriting the father's established dojo — existing students, routines, infrastructure already in place. Substantially different starting economy and different gameplay pressures. Scoped out of January.

**Starting capacity: three classes at break-even.** Three is the floor where the dojo doesn't bleed money. Scheduling a fourth draws from savings — a real choice with real cost, not a free option. This sets the early pacing: the player feels scarcity immediately but isn't starved. The first stretch of the game is "earn the fourth class."

**Father's style as cultural seed.** The player picks a style their father practiced (one of the 13 national fighting styles in the cultural layer — or a specific named school within one). The style is the dojo's starting cultural DNA. It biases:
- Which techniques the sensei teaches well
- Which kinds of students are initially attracted (family friends, old students of the father, judoka who know the name)
- Dojo reputation seed values

**The recognition moment.** A specific player experience worth preserving: one of the first walk-ins recognizes the father's name and the style. "You're teaching Tochi Owaza? Your father studied under—" That recognition is a narrative hook and a mechanical nudge. It validates the choice and biases the early dojo toward the father's lineage. The player can lean into the inherited identity or deliberately diverge from it over time.

**Architectural consequences:**

1. **Character generation for the player-sensei.** Need a creation flow: name, father's name, father's style, starting savings amount. Minimum scope: one or two screens.
2. **Style-knowledge as a sensei attribute.** The sensei has competencies biased by the chosen father's style. This is a Ring 2 data model addition.
3. **Narrative event triggers.** The "recognizes the father" event needs scripting infrastructure — or at least a templated event library that can fire when conditions align (new student + knowledge of father's style + early in run). This is narrative event infrastructure the game didn't previously need.
4. **Starting reputation seed.** The dojo launches with a small reputation weighted toward the father's style, not reputation-neutral. This affects the Q8 cultural feedback loop from turn one.

**Implications for other questions:**

- **Q2 (economic layer):** three-class break-even pins the economic starting state. You now have concrete numbers to anchor the rest of the economy around.
- **Q8 (cultural feedback):** the dojo doesn't start culturally blank. Father's style seeds the first culture vector. The player can drift or reinforce from there.
- **Q8d (reputation propagation):** the recognition event is a concrete mechanism. Name-based, style-based, lineage-based recognition events. At least one such event definitely ships.
- **Q9 (dojo Anchoring Scene):** the first-walk-in-recognizes-the-father moment is another strong candidate — possibly the *opening* Anchoring Scene while Marco's goal shift is the *midgame* one.

**Sub-questions this opens:**

- **Q7a-i — How many classes scheduled at launch?** Zero, letting the player set the initial three? Three pre-set (Tue/Wed/Thu 6pm adult fundamentals, say)? The difference shapes the first 15 minutes of play.
- **Q7a-ii — Is the father alive?** A living, reachable father is a different game than a deceased one. The first is a relational-mentor axis (maybe post-January); the second is a pure-legacy axis. The brief doesn't specify. Worth deciding.
- **Q7a-iii — Does the style choice lock, or can the dojo evolve?** Can you teach your father's style while students from other styles walk in and gradually change what you teach? Or is the style a fixed identity?
- **Q7a-iv — Exact starting numbers.** Savings amount, rent cost, class revenue, class cost. The game's opening difficulty curve lives in these four numbers. Probably sets during playtesting, not now — but worth acknowledging they'll need calibration.

---

### Q1 — Student lifecycle. ANSWERED.

**Answer:** The full lifecycle is the spec — because the whole range is what gives the match engine emotional teeth.

**The full lifecycle states:**

1. Trial week
2. First paying month (subscription starts)
3. First competition (sensei decides whether they're ready) → belt advance often follows
4. Win
5. Loss
6. Injury
7. Plateau
8. Break (paused attendance)
9. Dropout (from trial, from paying, from break)
10. Return (from break, sometimes from dropout)
11. Stops competing, keeps training
12. Leaves for another dojo
13. Retires
14. Becomes assistant for kids' class (any belt above a threshold)
15. Becomes assistant for main dojo (black belt)
16. Starts their own dojo
17. Advances to competition circuit (regional → national → international)
18. Olympics
19. Leads seminars (post-dojo life)

**Why the full set matters.** This is the whole point. The match engine's job is to produce meaningful matches. Meaningful requires stakes. Stakes require that the student matters to the coach. Students matter because each end-state represents a different kind of outcome — some celebratory, some bittersweet, some painful. Without dropouts, champions feel hollow. Without "leaves for another dojo," loyalty means nothing. Without "retires" and "becomes assistant," continuity has no emotional resolution. The full range is what produces the gradient you've been describing since the start of this chat.

**Player-agency reframe of loss.** This is the key design insight: *losing a student is not always bad.* Some dojos celebrate the student who leaves to start their own dojo — that's succession, that's legacy. Some coaches want a small, tight-knit dojo and would rather see ambitious students graduate and go elsewhere than grow big themselves. Other coaches want to build an empire and treat every departure as a defection.

The game doesn't tell you which is right. The student reaching "starts their own dojo" is a lifecycle end-state, but whether that *feels like* a win or a loss depends on the coach the player is playing. This is where dojo culture (Q8) and player identity intersect with the lifecycle.

**Architectural consequences:**

1. **State machine per student.** Students have lifecycle state as a first-class attribute. Transitions are driven by events (competition result, injury roll, belt test pass/fail, dues missed, satisfaction collapse) and by time (months without advancement triggers plateau eligibility, for example).
2. **State-dependent needs and goals.** (Ties to Q8.) A student's needs and long-term goals shift across lifecycle states. A plateaued student has different immediate needs than a trial-week student. A competitive-circuit student's goals look nothing like a kids'-class veteran's.
3. **Advanced states are rare by default.** Most students never reach competition circuit. Almost none reach Olympics. The gradient only produces the intended feeling if the high-end states are statistically rare. The design needs a distribution — maybe 10% reach first competition, 1% reach national circuit, 0.1% reach international.
4. **Lifecycle events as narrative events.** Each transition is a scene the prose layer can render. "Marco has decided he wants to try for his first competition." "James told you today he's leaving to train at the Kenzo dojo across town." "Amanda won her first regional." These are the dojo-loop equivalent of the match engine's prose output.
5. **Post-dojo lifecycle is a minor simulation layer.** States 16–19 (started own dojo, competition circuit, Olympics, seminars) live mostly outside your dojo. Tracked as rare events and callbacks ("Marco's dojo just beat a rival of yours in a team competition" or "Amanda invited you to attend her seminar"). Full world-simulation depth is Ring 4+; January version is sparse callbacks.

**Scope for January — not all states need equal depth.** Full fidelity on states 1–13 (through "leaves for another dojo") is the core dojo loop. States 14–15 (assistant roles) become real when the player's dojo is big enough, mechanically useful because they expand teaching capacity. States 16–19 can ship as sparse narrative events and statistical callbacks — the student who started their own dojo isn't fully simulated in January, just referenced. That's acceptable depth for a first release.

**Implications for other questions:**

- **Q8 (student inner lives):** lifecycle state is a major input to what a student's immediate needs look like. Plateaued students need different things than fresh-white-belts. Goals shift across lifecycle states.
- **Q9 (dojo Anchoring Scene):** you now have a rich library of candidate scenes — Marco's goal shift, the recognition walk-in, the first-competition, the student-leaving conversation, the assistant-coach promotion, the first-belt-test-pass. Probably one of these becomes the dojo's Anchoring Scene, and others become supporting moments.
- **Q2 (economic layer):** dropout rates drive monthly revenue variance. A dojo with high churn has unpredictable finances. This is a mechanical consequence that deserves real teeth.
- **Q7 (tempo) / Q7c (aggregate simulation fidelity):** when zoomed out, most students are advancing silently through early lifecycle states. The zoom-in is for the rare transitions — first competition, injury, a quit conversation. Lifecycle transitions should probably be in the event-pause set that stops the clock regardless of zoom level.

**Sub-questions this opens:**

- **Q1a — Can the player override lifecycle decisions?** A student is about to quit. Can the sensei have a conversation that changes the outcome? If yes, that's a coach-action layer. If no, lifecycle is destiny once conditions align. The design tension: too much player control removes stakes; too little makes the player a spectator.
- **Q1b — How does "ready for first competition" work?** The brief says "the sensei decides whether they're ready." Is that a yes/no coach call with a calculated risk, or a more nuanced readiness meter? Either way, this decision is probably one of the most emotionally loaded recurring choices in the game.
- **Q1c — Belt advances as gated or earned?** Tied to lifecycle state and competition results, or a separate sensei-administered test? Both? The sensei-run belt test is a potentially great ritual moment in the game.
- **Q1d — Relationship between "leaves for another dojo" and the cultural feedback loop.** Students leaving to join other dojos is a cultural signal — it reveals something about your dojo. Does the game surface why they left? Does it affect your reputation?

---

### Q6 — Weekly interface. ANSWERED (first-pass sketch).

**Answer:** The core dojo interface is a weekly calendar grid — days as columns, hours as rows, sessions as blocks placed into the grid. Sketched on paper as a Monday-through-Sunday view with hour rows from 5am to 9pm, and three "Adult Fundamentals" sessions blocked in at Wed/Thu/Fri 5–7pm.

**Interface components (from the sketch):**
- **Day columns.** Mon–Sun horizontal layout.
- **Hour rows.** Approximately 5am–9pm vertical scale. Finer than hourly isn't needed for scheduling at this zoom.
- **Session blocks.** Drag/place/size blocks into the grid. Each block is a class with a label, time window, and (eventually) a focus.
- **Capacity indicator.** "3 sessions: free / 4 sessions: slowly burns through savings" — visible capacity budget so the player feels the cost scaling as they place blocks.

**The Google-Calendar analogy locks in.** This is the mental model the player brings to it. Very few players need a tutorial for placing an event on a calendar. Low friction to the core interaction.

**Architectural consequences:**

1. **Calendar-native data model.** Sessions are first-class objects with a day, start time, duration, and recurrence. Recurring weekly schedules are probably the default, with the ability to edit individual instances.
2. **Time columns match student availability constraints.** The availability model from Q7 (kids after school, working adults evenings/weekends) maps directly onto specific grid cells. If a kid walks in who can only attend 4–6pm on weekdays, the player can instantly see whether the schedule has slots that fit them.
3. **Visual capacity feedback.** The "3 free / 4 burns savings" note from the sketch needs a live UI indicator — something that shows the financial cost as blocks are added. Not a hidden economy; a visible one.
4. **Scheduling is probably the game's most-used screen.** More time spent here than at any tournament. Polish budget should reflect that priority.

**Implications for other questions:**

- **Q2 (economic layer):** confirms sessions cost money at the scheduling layer. The visual indicator makes the economic pressure immediate — you see your savings deplete as you add a fourth class. This is good design; economic pressure is felt at the moment of the decision, not in a separate accounting screen.
- **Q3 (coach decisions):** the primary decision-making surface IS the calendar. Most weekly coach decisions happen at scheduling time, not at session time.
- **Q7a (starting capacity):** three break-even sessions confirmed, matching the earlier answer.

---

### Q7b — Session cost model and structure. ANSWERED.

**Answer:** Sessions are flexible in length and internal structure. The player chooses duration, and then decides how the time inside a session is used.

**Session duration tiers (from sketch):** 30, 45, 60, 90, or 120 minutes. Five tiers — enough variety for different class types without overwhelming the player with knobs.

**Internal structure is composable.** Within a session, the player allocates time across activities. Examples from the sketch for a 60-minute session:

*Technical-focus variant:*
- 5 min Warm Up
- 15 min Instruction / Lesson
- 10 min Questions / Answers / Practice
- 30 min Tachi-Waza
  - 10 min O-Soto entries
  - 10 min O-Uchi entries
  - 10 min Grip battles

*Live-sparring variant:*
- 5 min Warm Up
- 15 min Ne-Waza (5 min per partner, then switch)
- 10 min Tachi-Waza
- 30 min Randori

**This is the inner-structure that Q8 and Q3 were circling.** The coach's "atmosphere choice" and the "what does the coach do in the dojo" question both resolve here. The session structure IS the atmospheric choice. A dojo that runs 30 minutes of randori every session has a different feel than one that spends 30 minutes on instruction. A dojo that breaks tachi-waza into O-Soto entries specifically is biasing students toward a particular style. Session content is the primary mechanism by which dojo culture gets built.

**Architectural consequences:**

1. **Session-as-composed-object.** Each session contains an ordered list of activity blocks with duration and focus. Activity blocks are the atomic unit; sessions are compositions.
2. **Activity library.** Need a vocabulary of activity types: warm-up, instruction, Q&A, specific technique drilling (by named technique), grip battles, tachi-waza randori, ne-waza randori, competition-format sparring, kata, conditioning, etc. Starts small — maybe 10–15 activity types for January — and grows.
3. **Technique-level granularity.** The sketch shows "O-Soto entries" and "O-Uchi entries" — specific techniques as drilling targets. Student skill development should be sensitive to this: a student whose sensei drills O-Soto every week gets better at O-Soto than one whose sensei drills varied techniques. This directly feeds the cultural-identity loop — what you drill becomes what your dojo is known for.
4. **Preset templates.** The activity-allocation screen could offer presets (Technical Focus, Randori Heavy, Beginner Intro, Competition Prep) so players who don't want to micromanage can pick a shape. Preset is probably the default UX path; custom is the advanced option.
5. **Cost is duration-based, not content-based.** A 120-minute session costs more than a 30-minute one regardless of internal structure. Keeps the economic model simple. Content affects what students get out of a session, not what it costs to run.

**Implications for other questions:**

- **Q3 (coach decisions):** the session-composition screen IS a major decision surface alongside the calendar. Weekly coach decision-making happens at two zoom levels — schedule (which sessions, when) and content (what each session contains).
- **Q8 (cultural feedback loop):** session content is a primary input to dojo identity. What you drill becomes what your dojo is known for. This tightens the feedback loop — dojo reputation is computable from accumulated session content.
- **Q7 (tempo / zoom):** when the player zooms in to an individual session, they're zooming into the activity blocks they composed. The simulation runs activity-by-activity.
- **Q1 (lifecycle):** technique-specific skill development means a student's specific capability profile reflects the dojo's drilling history. Students from a Tachi-Waza-heavy dojo are different from students at a Ne-Waza-heavy dojo. Real mechanical consequence for student identity.

**Sub-questions this opens:**

- **Q6a — Session-duration-to-price mapping.** Is it linear (1 minute = 1 unit cost)? Stepped by tier? Specific session types cost more? Probably linear is cleanest.
- **Q7b-i — Activity library scope for January.** Which 10–15 activity types ship? Probably anchored to what Ring 1 simulates well — so tachi-waza, ne-waza, grip battles, specific-technique drilling, randori, warm-up. Skip anything too narrative (like "Q&A sessions") unless it has mechanical hooks.
- **Q7b-ii — How do students respond to session composition mismatched to their level?** A white belt dropped into a 30-min randori block isn't going to improve the same way a brown belt would. Does the activity-block specify a skill-level target? Or does the sensei's pairing decisions handle this at a finer layer?

---

### Q9 — Dojo Anchoring Scene. ANSWERED.

**Answer:** The dojo has *two* Anchoring Scenes — an opening and a closing, forming an arc. The arc is the twins.

**Opening Anchoring Scene — The twins arrive.** Within the first month of a new dojo, two twin brothers walk in, excited. They saw the name on the small directory outside the basement. They'd heard stories from their own father, who had trained with the sensei's father decades ago. They came to check if it was really true. It is. Because of this coincidence, they're joining the gym. They want to be like their father. They want to become champions.

This scene delivers:
- Father's lineage as felt history, not data (Q7a)
- The recognition-walk-in mechanic at maximum emotional weight (Q7a)
- The cultural feedback loop's opening iteration — reputation precedes reality (Q8)
- Concrete starting characters with stated long-term goals (Q1, Q8)

**Closing Anchoring Scene — The twins as disciples.** Years later, the twins have both earned their black belts. They didn't just compete — they stayed. They teach alongside you. They're your disciples. Two of the lifecycle-state-14/15 "assistant" endings, resolved for a pair of characters the player has known since month one.

This scene delivers:
- Full lifecycle arc traversed (Q1: trial → paying → competition → belt advances → assistant roles)
- The player-agency reframe of retention — keeping them isn't always the goal, but in this case it was, and it happened because of the work
- Cultural continuity — the sensei's father's style has now produced a new generation, in a new basement, in a new city, via students who knew the name before they walked in
- An ending worth fighting the attention scarcity battle for

**The tension between the two scenes — this is the point.** Twins create a built-in attention conflict. One of them might feel they're getting less of your time than the other. One might plateau while the other advances. One might leave. Getting to *both* of them as assistants is the happy ending, not the default outcome. The player has to manage the jealousy, the pacing, the individual needs. A game that produces this arc will have produced every supporting system correctly — the match engine, the lifecycle, the needs/goals layer, the cultural feedback, the attention scarcity, the calendar, the session composition. This is a valid design north star because you cannot produce this scene with a shortcut.

**Supporting insight — "A good week" is concrete and measurable.** A good week is one where students come to every class they're scheduled for. Consistency of attendance IS the local metric of dojo health. When students only come Wednesdays or Saturdays, that's a worse week than when they come to every session available to them — because they're getting less out of what you're offering. This has two consequences:

1. **Weekly roundup screen.** After each week, show each student and what they improved on — the stat deltas, the skill bumps, the small gains. This is a natural place to surface the zoomed-out simulation output (Q7c) and close the week with a satisfying summary.
2. **Attendance is a success signal.** The game can measure dojo health in part by average attendance rates per student. If students are skipping sessions they're supposed to attend, something is off — maybe the schedule doesn't fit their lives, maybe their needs aren't being met, maybe the culture isn't working for them.

---

### Q3 — What the coach does in-session. ANSWERED (via Q9).

**Answer (pulled out of Q9 for clarity):** The coach's in-session action is the "get to know" mechanic — spending time on relationship-building during training blocks.

Concretely: inside a session, the coach can allocate time to conversation. In a 10-minute randori block, the coach might spend 5 minutes actually watching the match (Q4 granular attention) and 5 minutes getting to know one individual student. The conversation unlocks visibility of one of that student's wants or needs. Conversations can also chain — a student might mention what someone else said, unlocking visibility into a second student's needs through the social graph.

**Wants and needs are hidden by default.** This is the critical design move. Q8's needs/goals layer isn't transparent. A student walks in with needs and goals, but you don't see them. You earn visibility by spending attention on them. Until you do, you're coaching blind.

**Attention scarcity operates at three scales now:** tournaments (three fighters, one chair), randori (five pairs, one watched match), weekly time (many students, limited conversations). Same primitive, three scales. The attention scarcity principle is now the main cross-system thesis of the game.

**Architectural consequences:**

1. **Conversation as a first-class in-session action.** Alongside watched-match-attention, the coach has a conversation action available during sessions. Time spent on conversation is time not spent on match watching — the player chooses.
2. **Visibility as earned information.** Student data has a visibility layer. The player sees only what they've uncovered. This is a UX pattern (Dwarf Fortress preference-inspection style) and a gameplay pattern — you literally don't know what you don't know about your students.
3. **Social graph for chained conversations.** Students have relationships with each other, and those relationships carry information. A conversation with Ken can reveal something about Marco if they've talked. This needs a lightweight student-to-student relationship model — at minimum, "has been paired with in randori" and "has chatted outside class" edges, so the game knows who plausibly shares information.
4. **Rebuilds pressure on the scheduling layer.** If you don't schedule enough randori, you don't have time to hold conversations. Session composition is now directly tied to how much you can learn about your students.

**Implications for other questions:**

- **Q8 (student inner lives):** confirmed. Needs and goals are hidden data. The whole "students have inner lives" layer only matters if the player engages with the conversation mechanic.
- **Q8c (minimum viable needs per student):** the conversation mechanic works with any number of needs, but probably 2–3 needs and 1 long-term goal per student is enough for January. The point is the discovery process, not the combinatorial depth of need libraries.
- **Q6 (interface):** the student detail view needs a "known" / "unknown" visibility layer. Probably grayed-out sections that fill in as conversations land.
- **Q7c (aggregate simulation fidelity):** conversations during fast-forwarded weeks probably don't happen (the coach isn't actively sensei-ing). Another reason to slow down and zoom in — you can't learn your students on fast-forward.

---

### Q11 — Roster view / the sensei's spreadsheet. ANSWERED.

**Answer:** The sensei has access to a spreadsheet-style roster of every judoka currently at the dojo. A player-controlled granularity toggle shifts the view between macro (quick overview across the roster) and granular (all available detail for each student).

**Fields visible in the roster:**
- Stats (the physical / mental / technical capability axes)
- Usual needs and desires (Q8 psychology layer, subject to visibility — see below)
- Weight class
- Belt level
- Preferred moves / technique repertoire
- (Plus likely: age, attendance pattern, lifecycle state, time at dojo, father's-style kinship if applicable)

**Critical interaction with Q9's hidden-information principle.** The spreadsheet is a view over what the sensei *knows*, not a god-view of ground truth. Fields that haven't been uncovered through conversation, pairing history, or enough shared time on the mat appear as "unknown" or grayed out. The spreadsheet fills in as the coach earns visibility. A brand-new student joining this week has almost everything blank except what you can see on the surface — name, approximate age, weight class, starting belt. Their inner life is opaque until you've put time in.

This tension resolves cleanly: the spreadsheet is the inventory of your accumulated knowledge, not a cheat sheet that bypasses the conversation mechanic. Two senseis running the same dojo would have different spreadsheets depending on who they'd talked to.

**Granularity toggle is the key UI lever.** At macro view, the player sees 15 students as a compact grid — name, belt, one summary indicator (maybe attendance health or "needs attention" flag). At granular view, one student fills the screen with every unlocked field visible. Match Football Manager's squad-view pattern: overview for triage, zoom-in for deep decisions.

**Architectural consequences:**

1. **Roster is the third primary surface.** The three main screens of the game now name themselves: the calendar (scheduling), the session (live simulation + conversations), and the roster (status + knowledge). Most play time is across these three.
2. **Visibility layer lives at the data-model level.** Every student attribute has a revealed-or-not flag, not just a value. The roster UI renders based on these flags. The session conversation mechanic writes to them.
3. **Weekly roundup nests into the roster.** The Q9 "weekly roundup" screen is probably a roster view with deltas highlighted — each student's stat changes this week visible in the grid, clickable for details. No separate roundup screen needed; the roster IS the roundup when you view it at week-end.
4. **Sort and filter affordances matter.** With 15+ students and many columns, sort-by-column and filter-by-attribute become necessary. Filter by "needs attention," by belt level, by "hasn't talked to in 3+ weeks," by weight class (for tournament selection). These aren't nice-to-haves — without them the roster becomes a wall of numbers.
5. **The roster is how the game makes attachment legible.** You see the same names week after week, watch the blank fields fill in, watch the stats climb, and the student stops being a row and starts being a person. The spreadsheet is where attachment accumulates mechanically.

**Implications for other questions:**

- **Q1 (lifecycle):** the roster needs to show lifecycle state, or at least surface state changes (a student who moved to "plateau" this week should surface as a flag on the roster).
- **Q3 (coach decisions):** a lot of coach decisions happen by looking at the roster and acting. Who pairs with whom in randori, who's ready for a tournament, who needs a conversation — all of this starts by scanning the roster.
- **Q6 (calendar interface):** the calendar and roster are sibling surfaces. Clicking a student on the roster probably highlights their available time slots on the calendar; placing a session on the calendar probably affects who appears on the roster via attendance.
- **Q8 (hidden needs/goals):** confirms the visibility layer is a real data architecture commitment, not a prose trick.
- **Q9 (Anchoring Scene):** the twins' arc will partially be visible *through the roster* over time — watching their grayed-out fields fill in, watching their stats climb, watching them move through lifecycle states. The roster is where the years of accumulated work become a legible thing.

**Scope note — this is real UI work.** Football Manager's squad view is one of the most complex interface components in the game. A functional Hajime roster needs: grid rendering, multiple columns, sort, filter, granularity toggle, visibility-layer rendering, per-student drilldown, delta highlighting. Not trivial. Probably the single most expensive UI component to build for the January release after the calendar itself. Worth acknowledging now so it doesn't get under-scoped.

**Sub-questions this opens:**

- **Q11a — Does the roster also show former students?** Students who left, retired, moved to assistant, started their own dojo. A "history" tab that tracks your lineage might be a separate view — or might be post-January scope.
- **Q11b — Does the roster show students at rival dojos?** Probably limited and late — you'd need to have coached against them or scouted them. This is post-January Ring 3+ territory.
- **Q11c — Do student stats update live during a session, or only at session close?** Affects whether the roster is "always current" or "end-of-session accurate." Probably end-of-session keeps the interface calmer and reinforces the zoom-in-to-see-what-happened rhythm.

---

### Q2 — The economic layer. ANSWERED.

**Answer:** The economic layer has two mechanical functions — a warning/loss pressure via a recurring antagonist character, and a demographic-shaping lever via the pricing structure. Consistent with the game's "sweet spot" philosophy, both can be engaged lightly (default prices, stay above threshold) or deeply (precise pricing strategy, targeted demographics).

**The antagonist — economic pressure as narrative pressure.** When the dojo's savings drop below a threshold, a man in a suit shows up. He's a specific character — slimy, not into martial arts, known for buying up struggling small dojos and converting them into predatory Taekwondo kids' mills that extract money from parents. He's not a bank foreclosure notification. He's a person, with a face and a reputation, who *wants* your dojo to fail so he can buy it cheap.

The mechanic:
- Stay above the savings threshold → he doesn't appear. You don't have to think about him.
- Drop below → he visits. Warning event. You know what's coming if things don't improve.
- Stay below too long → he makes an offer.
- Financial collapse → he buys the dojo. Game-over state, but a narrative one, not an abstract one.
- Recover after a visit → he backs off, but he'll be back if you dip again.

**Why this works.** Economic failure is abstract and unsatisfying as a game mechanic. Losing your dojo to a *specific person you hate* is dramatically complete. Every warning visit is a reminder with a face attached. The pressure is felt as antagonism, not accounting.

**The antagonist → rival dojo pipeline.** Eventually, with enough capital, the suit opens his own judo dojo. He's no longer just threatening to buy you out; he's competing with you directly. His students start showing up at tournaments. This is the first rival dojo in the game's world — and it arrives with dramatic continuity. The guy you spent months keeping at arm's length is now the guy whose students your students are fighting.

This links the January release's contained economy to Ring 3+ rival-dojo content. The suit is the hook. Other rival dojos appear later at the competition level — people you meet on the circuit — but the suit is rival dojo #1 because he's already in the story.

**Pricing as demographic lever.** The sensei sets prices. Options across the pricing structure:
- **Base monthly subscription** in a range (sketched at $75–$200)
- **Group / family plans** — cheaper per-person, attracts multiple-member households, may correlate with lower individual commitment
- **Belt-level discounts** — cheaper rates for advanced students, rewards loyalty and retains talent
- **Mat fees** — daily drop-in pricing, attracts uncommitted people who might convert, might not

Price choice shapes who walks in:
- High prices → status-conscious students, fewer walk-ins, more committed on average
- Low prices → higher volume, more kids, more casual attendance, higher churn
- Group plans → families, social-motivated attendance
- Belt discounts → retention
- Mat fees → tourists, potential converts, irregular cash flow

Player can ignore this layer (set mid-range prices, run the dojo) or tune it aggressively to target a specific culture (high subscription + black-belt-only discounts to build an elite competitive room, or low base + group plans to build a community kids' dojo).

**The fourth system expressing the game's depth philosophy.** Calendar tempo (Q7), session composition (Q7b), roster granularity (Q11), and now pricing — all four primary systems offer a default/light mode and a detailed/optimized mode. Hajime has a consistent design language across systems: player agency over engagement depth. Worth naming in the master doc as a design principle that disciplines future features.

**Architectural consequences:**

1. **Antagonist as first-class recurring NPC.** Named character, dialogue, state machine (not-yet-met → visited-once → escalating → offering-to-buy → ultimate-offer → bought-you-out / backed-off). Reusable narrative event infrastructure.
2. **Threshold-based event triggers.** "Savings below X for Y weeks triggers event Z" is a general pattern that other narrative events can use. Getting this infrastructure right once pays forward.
3. **Pricing data model.** Five or so price knobs total: base subscription, group discount, belt-level discount brackets, mat fee rate, maybe trial-week pricing. Small enough to be designable, rich enough to produce real demographic variance.
4. **Student-attraction function.** Procedural generation of walk-ins becomes a weighted distribution biased by current pricing, dojo reputation (Q8), session schedule availability (Q7), and father's-style lineage (Q7a). Probably the single most consequential procedural system in the game — it determines who the player's story is about.
5. **Savings-threshold indicator in the UI.** The antagonist should not be a surprise the first time. Some visible signal when savings are drifting toward the threshold — a sidebar number going yellow, a warning icon — so the player can react before the story fires. The game wants players to fear the antagonist, not resent him for ambushing them.

**Implications for other questions:**

- **Q1 (lifecycle):** pricing affects who enters the "trial week" state at all. A dojo with high prices sees fewer trials but better conversion; a low-price dojo sees a flood of trials with high dropout.
- **Q8 (cultural feedback):** pricing is a major culture input, sitting alongside session content and sensei style as primary determinants of dojo identity. Cultural axes (Q8a) probably correlate with pricing strategy in recognizable ways.
- **Q11 (roster):** the roster doesn't just need to show current students — eventually (post-January) the rival dojo's notable students should be scoutable, with the antagonist's dojo as the first scouting target.
- **Q7a (starting conditions):** the three-class break-even and modest savings imply the antagonist threshold is tuned to be encountered naturally in an early-game bad stretch but not immediately. Possibly a mid-first-year encounter in normal play.

**Sub-questions this opens:**

- **Q2a — Frequency and escalation cadence.** How often does the suit visit when you're under the threshold? Every month? Every time savings drop by another tier? The pacing defines the pressure's intensity.
- **Q2b — Recovery behavior.** Once he's visited and you've recovered, does his next visit start from escalation step 1 or pick up where he left off? If the latter, a player who bounces around the threshold gets progressively squeezed; if the former, they get forgiveness for recovering.
- **Q2c — Grace period at zero savings.** Does hitting zero savings mean immediate loss, or is there a month-long grace during which the player can try to recover? A grace period makes the mechanic feel fair; immediate loss makes it brutal.
- **Q2d — Pricing changeability.** Can the sensei change prices freely, or are there frictions (locked in for 3 months, notice period, current students continue at old rates)? The frictions make the decision meaningful but add complexity.
- **Q2e — When does the suit open his rival dojo?** Triggered by player success (rival opens when you're established), by time (rival opens eventually regardless), or by a failed acquisition (rival opens if he fails to buy you out)? Each has different dramatic implications.

**Scope for January.** Minimum viable: base subscription pricing (single tier), antagonist appears below threshold as a warning, game-over state if things collapse, student attraction function weighted by pricing and reputation. Stretch: full pricing structure (group/belt/mat), antagonist escalation arc, rival-dojo opening late-game. The antagonist-as-rival-dojo pipeline is probably post-January content regardless, since it depends on Ring 3+ rival-dojo simulation.

---

### Q1 addendum — Belt progression timeline and promotion philosophy. ANSWERED.

**Answer:** Belt advancement is suggestion-assisted but sensei-decided. The system surfaces candidates when they cross threshold conditions; the sensei chooses whether to promote, hold them back, or require more from them first.

**Real-world timing data (ground truth for calibration):**

- **Yellow belt:** 6 weeks to 1 year. Highly variable depending on school philosophy. Some dojos award yellow after the student's first competition (regardless of weeks elapsed); others use a purely time-based cadence and a student could reach yellow in a few months without ever competing.
- **Green belt:** 1 to 3 years, depending on training frequency and intensity.
- **Brown belt:** 2 to 5 years. A common long-term plateau — students can remain at brown belt indefinitely.
- **Black belt:** 4 to 7 years of intense training, minimum.

**Promotion philosophy as a cultural-layer signal.** This is important. Yellow belt variability isn't just a number — it's a philosophical choice the sensei makes that reveals the dojo's identity. A "compete to earn it" dojo promotes fast after first competition results, biasing the culture toward competitive students. A "time and discipline" dojo promotes on measured cadence, biasing toward students who value tradition over achievement. A "rigorous gatekeeping" dojo holds students longer than average at each level, building a smaller but more capable room.

Promotion philosophy is the *fifth* primary input to dojo culture, alongside session content (Q7b), pricing (Q2), father's-style lineage (Q7a), and the sensei's direct atmospheric choices (Q8 via Q7b). The player's accumulated promotion decisions across many students become a reputation signal: "this dojo is where you actually have to earn it."

**The system suggests; the sensei decides.** Same pattern as the "first competition readiness" call in Q1b, and consistent with the game's overall depth philosophy. The system crunches thresholds (time at level, competition results, attendance, skill levels, sensei's observed familiarity with the student) and surfaces suggestions on the roster. The sensei can accept, reject, or defer. Rejecting a system-suggested promotion has narrative weight — you're telling a student "not yet," and that matters for their needs/goals/retention.

**Major architectural consequence — the game's time scale.** A complete run spans many in-game years, not months. If the twins arrive at white belt in year 1 and become black-belt disciples (Q9 closing scene), that arc takes 6–8 in-game years minimum, probably more. This has cascading implications:

1. **Fast-forward simulation (Q7c) is not optional.** It's the only way the game is playable. Most of a campaign is time passing between notable events. The aggregate simulation layer carries the bulk of the runtime hours.
2. **A "campaign" is long.** A January release probably aims for runs of 10–15 in-game years to let the full lifecycle play out — white belts become black belts, assistants become rival senseis, the antagonist arc resolves. Roughly one in-game year per 20–60 minutes of real playtime, varying with zoom.
3. **Early-game pacing matters enormously.** The first in-game year — basement dojo, first students, twins arriving, maybe first yellow belt — establishes the tone for a campaign that will last dozens of hours. If the opening stretch doesn't hook the player, nothing that comes later will matter.
4. **Retention of student identity across years.** A student who joined in year 1 and is still there in year 5 needs to feel like the same person, with a visible history. The roster (Q11) must surface accumulated history, not just current state — past competitions, past belt advances, past moments where the sensei chose to promote or hold back.

**Brown belt as a common plateau is a design gift.** Most students who reach brown belt stay there. That's real judo, and it gives the game a natural population distribution: a few white/yellow (new arrivals), a working middle (green/brown), and rare blacks (the champions and the disciples). The brown-belt plateau is where most of the emotional middle of the game lives — students who've been with you for years, who probably won't reach black belt, who are the backbone of the dojo.

**Implications for other questions:**

- **Q1 (lifecycle):** confirms belt advances as discrete events spaced at real-world-calibrated intervals, not uniform pacing.
- **Q1b (first competition readiness):** the "suggest-but-sensei-decides" pattern from here generalizes to that question. Same mechanic.
- **Q1c (belt advances as gated or earned):** answered — both. Thresholds gate eligibility; sensei decides promotion.
- **Q8 (dojo culture):** promotion philosophy is the fifth primary cultural input. Cultural layer is more richly specified than it was.
- **Q8b (goal shift tempo):** goals probably shift on the order of months to years in-game, not weeks. A student whose long-term goal is "become a champion" might hold that for 2–3 in-game years before it evolves or hardens.
- **Q9 (dojo Anchoring Scenes):** the twins arc takes 6–8 in-game years minimum. The closing scene isn't a few months' gameplay — it's a long campaign's payoff.
- **Q7 / Q7c (tempo and aggregate simulation):** fast-forward gets upgraded from "useful feature" to "the architecture the game depends on." Most campaign hours happen at zoomed-out speeds.

**Scope for January.** All four belts need to exist, with thresholds and a promotion suggestion mechanic, because the full campaign arc demands them. However: only the first 2–3 in-game years need to play out at granular fidelity in the base game — a January release doesn't need to prove it can produce a 10-year arc, only that the player can *start* that arc and feel where it's heading. Late-campaign polish (assistant roles, student-starts-own-dojo endings, Olympics-tier competition) is post-January content.

**Sub-questions this opens:**

- **Q1e-i — Belt promotion as ritual.** Is a belt promotion its own scripted moment — a scene, maybe tied to a specific session or ceremony — or is it a stat change on the roster with a notification? The ritual framing is much stronger narratively but more expensive.
- **Q1e-ii — Can students refuse promotion?** If Marco feels he isn't ready and the sensei is pushing him forward, does he have agency to push back? This would be a rare and emotionally loaded moment, consistent with the hidden-needs/goals layer.
- **Q1e-iii — Does the sensei's own belt level constrain what he can award?** A brown-belt sensei presumably can't promote students to black belt. The father's-style inheritance (Q7a) should probably include the sensei's own rank. This also affects Q10 — the coach's own fighting status might determine what ceiling the dojo can produce without outside examiners.

---

### Q7c — Aggregate simulation fidelity. ANSWERED.

**Answer:** Silent background simulation runs continuously. Randori is *always* being simulated — every student, every pairing, every week, regardless of whether the player is watching. General capability builds up naturally. What the player loses by not zooming in is *style* — the specific technique development, the specific grip choices, the preferred-moves signature that distinguishes one judoka from another.

**The tradeoff is calibration by design.** Granular attention produces *distinctive* judoka. Aggregate simulation produces *capable* judoka. Both improve; the difference is whether a student is "good at judo" or "known for their uchi-mata entries off a broken grip." This tradeoff is what makes granular attention worth the time cost. A player who only ever plays at monthly zoom will have a full dojo of competent but generic judoka. A player who zooms into specific sessions will produce a few stylistically distinctive standouts surrounded by generic depth. The granular mode is how champions are forged.

**Monthly training focus — the player's aggregate-mode lever.** When the player is zoomed out at weekly or monthly speed, they still make meaningful choices by setting the month's focus area: footwork, ne-waza, specific grips, conditioning, competition prep, etc. The monthly focus biases the aggregate simulation — students improve in the focused areas faster than in untargeted ones, though still without the specific-technique granularity that zoomed-in sessions produce. This makes fast-forward a *choice-laden* mode, not a passive "let it run" mode.

**Event-pause triggers confirmed.** Fast-forward stops regardless of zoom level when:
- A student is injured
- A student wants to leave (or needs a conversation to retain)
- A competition is approaching (probably 2 weeks out, tunable)
- A promotion suggestion surfaces (system thinks someone is ready for a belt)
- Savings drop below threshold (antagonist visit triggers)
- Any narrative event fires that requires the coach's attention

These are not optional — the game *forces* the zoom-in. The player doesn't miss the moments that matter. The dread of the antagonist walking in, the weight of deciding whether to promote Marco, the decision about whether James fights injured — all of these halt the clock.

**Architectural consequences:**

1. **Three zoom levels, not two.** Session / weekly / monthly is the confirmed set. Each has different fidelity:
   - **Monthly:** aggregate stat drift weighted by monthly focus. Cheap to simulate. Probably 5-10 minutes of play per in-game month of straight fast-forward.
   - **Weekly:** weekly roundup (Q9/Q11), per-student stat deltas visible, individual events surface. Medium fidelity.
   - **Session:** full Ring 1 match-engine granularity for the session the player zoomed into. Highest fidelity. Conversations (Q3) happen here.
2. **Randori simulation is always running — the cost is capped by fidelity, not frequency.** The simulation tick runs at the same base rate; what changes per zoom level is how much detail is generated and rendered. Cheaper to fast-forward, not cheaper in world-sim terms.
3. **Monthly-focus is a first-class input to the aggregate update function.** Student capability updates as: base drift + monthly-focus bias + attendance modifier + age/lifecycle modifier. Simple, auditable, tunable.
4. **Event-pause requires a priority queue of pending events.** The simulation builds up a queue as it fast-forwards. When an event qualifies (severity > threshold), it pops and halts the clock. The player reacts, then chooses the zoom level to proceed from.

**Implications for other questions:**

- **Q1 (lifecycle):** lifecycle transitions are event-pause triggers. Belt promotions, injuries, departures all halt fast-forward.
- **Q3 (coach decisions):** conversations are session-level only. Fast-forward means you are not getting to know your students. Enforced tradeoff.
- **Q7b (session composition):** monthly training focus is the coarser sibling of session composition. Detailed composition at session zoom; themed focus at monthly zoom.
- **Q8 (culture):** the monthly focus compounds into cultural identity over time. Six months of ne-waza focus builds a ne-waza-forward dojo.
- **Q9 (Anchoring Scenes):** the twins arc's years of training happen mostly at weekly/monthly fidelity, with key moments (first competition, brown-belt promotion, first teaching session) forcing zoom-ins. The payoff scenes are the zoom-in events.

---

### Q2 extension — Quality/price tension, sponsorships, and facility progression. ANSWERED.

This extends the earlier Q2 answer with three new dimensions of the economic layer that emerged from the randori/simulation discussion: pricing as a quality/financial tradeoff, sponsorships as a retention mechanic, and facility progression as the primary money sink beyond survival.

**The quality/price tension — possibly the game's most distinctive design pitch.** Critical insight: *the students who can pay the most are not the students with the most potential.* High-paying students come with expectations — they want service, attention, amenities, status. They are reliable revenue. Meanwhile, genuinely talented students may be working-class kids who can barely afford the cheapest tier, and whose ability to train seriously depends on financial support you either provide or find for them.

The moral architecture this produces:
- Do you subsidize the kid who might reach the Olympics but can't pay, knowing it costs you the revenue you need to keep the lights on?
- Do you tolerate the high-paying students who demand a quality of experience that pulls your attention away from the kid who could be a champion?
- Is your dojo a business that trains strong people, or a talent-development project that happens to need money?
- Who are you, as a sensei, when those two goals pull against each other?

This is the game's most distinctive thematic hook. Most management sims collapse "pay more" and "deserve more" into the same vector. Hajime explicitly separates them. The player runs *both* the business and the mission, and has to decide how much of each they're willing to sacrifice for the other.

**Sponsorships — keeping the talented-but-poor student training.** A mechanic for sustaining students whose talent exceeds their means. Forms it could take:
- Local business sponsors (small, reliable)
- Regional sports associations
- Name-brand sportswear companies (contingent on competition results)
- Alumni / former students who succeeded and now give back
- The sensei's own subsidy (coming out of dojo savings)

The sensei's role in sponsorships: applying on the student's behalf, negotiating terms, presenting results, maintaining the relationship. Probably works as a late-early-game unlock — not in the first months, but available once the dojo is established and a student has competition results to show.

**Facility progression as a primary money sink.** Once the dojo is financially stable, money buys upgrades that concretely change what the dojo can do:
- **Mat space:** start with ~2 simultaneous randori pairs, expand up to 5. Directly affects session capacity and how much attention can be distributed.
- **Weight room:** enables conditioning training as a session activity. Different stat improvements, different student appeal.
- **Mini sauna:** weight cutting assistance (for competition prep), community bonding (dojo as social hub, a cultural-layer signal).
- **Move out of basement to proper facility:** major progression milestone. Probably comes with a reputation bump, pricing flexibility, and new kinds of students considering you. Could be a mid-to-late-campaign milestone, with its own narrative moment.

Facility upgrades give money a second purpose beyond "stay above the antagonist threshold" — it becomes something to strive toward. The slimy guy's threshold is the floor; the weight room and proper facility are the ceiling.

**Implications for other questions:**

- **Q1 (lifecycle):** Olympic-tier students (states 17-18) probably require sponsorship to sustain — building in dependency on late-game mechanics.
- **Q2 (original):** the antagonist isn't the only economic pressure. Facility upgrades create positive pressure too — not just fear of loss but desire to grow.
- **Q8 (culture):** facility choices are culture signals. A dojo with a sauna feels different from a dojo without one. Mat space affects how much community gathers in one place.
- **Q11 (roster):** students should show sponsor status on the roster, and sponsor-contingent retention becomes another visibility/management axis.

**Sub-questions this opens:**

- **Q2f — Does the sensei know at student-arrival time how much potential a kid has?** If no, the talent/money tension is played blind — you don't know which poor kid is the future champion. If yes, the tension becomes an explicit moral choice. The hidden-needs principle (Q9) suggests blind is consistent — you learn potential through conversation and observation.
- **Q2g — Do high-paying students actively demand attention?** An explicit "complaining" mechanic, or just a retention-penalty if they feel neglected? The former adds pressure; the latter stays quiet.
- **Q2h — Can the sensei self-subsidize indefinitely?** If the dojo's savings grow, can the sensei cover the scholarship of one talented student perpetually? This might be the simplest sponsorship system for January, deferring external sponsors to Ring 3+.

---

### Q12 — Competitive ranking hierarchy. ANSWERED (scope placeholder).

**Answer:** The full competitive ladder the game recognizes has five tiers: **local → state → national → international → Olympic**. Rankings are computed from tournament results and student records, the same way real-world sports rankings work. This is the ladder that late-lifecycle students (Q1 states 17-18) climb.

**This is Ring 3+ content being acknowledged.** January release almost certainly doesn't ship full five-tier competitive simulation. Full rival-dojo simulation, procedural competitor generation, accurate ranking math across scales, international scouting — that's a larger game than nine months allows.

**What probably ships in January:**
- Local and state rankings, because they're reachable in 2-3 in-game years
- Tournaments at local and state level
- National ranking as a statistical concept (a student "has a ranking" but the depth of the national circuit is sparse)
- International / Olympic tiers exist as narrative endpoints, gestured at but not simulated in depth

**What probably does not ship in January:**
- Full international competitor simulation
- Live rival-dojo tracking at the national+ level
- Olympic games as a simulated event

**Why acknowledging the full ladder matters anyway.** The late-lifecycle states (Q1 states 17-19) require this ladder to exist. A student "advancing to the competition circuit" needs circuits to advance to. Even if the January release only mechanically simulates local/state, the narrative of national/international/Olympic exists in the world and surfaces as callbacks — "Marco won his first national tournament" is a narrative event, even if the national tournament isn't a fully playable screen.

**Architectural consequences:**

1. **Ranking is a computed attribute, not a simulated world (for January).** Student rankings within the dojo's reach tier are computed from wins/losses. Tiers above the reachable horizon are sparse narrative layer.
2. **World-outside-the-dojo begins to exist.** Other dojos, other competitors, other circuits. Even if only sketched, the game now has a world. Ring 3+ content has a framework to slot into.
3. **The ladder creates long-campaign structure.** The twins reaching black belt (Q9) is one arc. A student reaching national ranking is another. The Olympics arc is the ultimate endgame. The game has multiple kinds of late-campaign payoff.
4. **Ranking hierarchy links back to the antagonist arc.** The suit's dojo (Q2) eventually competes on rankings. Rival dojos at higher tiers create natural antagonists for late-campaign play.

**Implications for other questions:**

- **Q1 (lifecycle):** states 17-18 (competition circuit, Olympics) are now named in the ranking hierarchy. Advancement through the ladder becomes part of the late-game lifecycle.
- **Q2 (economic):** higher-tier competition is expensive. Transportation to nationals, international travel, Olympic qualification costs — all of these push on the economic layer in ways that tie back to sponsorships.
- **Q11 (roster):** student profiles eventually show their current ranking. Long-term, ranking history becomes part of the student's legible history.

**Sub-questions this opens:**

- **Q12a — Scope honesty: which tiers get meaningful simulation for January?** Probably local + state with hand-wavy national. International and Olympic as narrative-layer endpoints.
- **Q12b — Are rankings publicly visible or a scouting-cost mechanic?** A rankings screen anyone can see is simpler; requiring the sensei to "check the rankings" (small cost) makes the information feel earned.
- **Q12c — How do non-player-dojo students exist statistically?** Is every ranked judoka simulated, or are most of them statistical ghosts who only become real if your student faces them? The latter is much cheaper and probably necessary.

---

### Q11 extension — Roster UI evolution from notepad to computer. ANSWERED.

**The roster's visual presentation evolves with the dojo.** At game start, the roster is a yellow legal notepad — the sensei's handwritten list of his handful of students. Names and weights on each line. As conversations uncover needs, wants, and goals (Q9 conversation mechanic), the sensei writes them in the margins, circles keywords ("wants to compete," "likes to try this more," "wants to learn this"), adds annotations in his own hand. The notepad fills up with the sensei's own observations, messy and informal and personal.

Once the dojo grows beyond what a notepad can handle — roughly 10 students, possibly tied to a milestone of in-game time or savings — the sensei invests in (or must purchase) a computer. The roster transitions from handwritten pages to digital: sortable columns, filter controls, granularity toggles. The full Football Manager squad-view that the original Q11 answer described isn't the *starting* interface; it's what the interface *becomes* once the sensei has outgrown the notepad.

**Why this is a strong design pattern:**

1. **The UI tells the dojo's growth story.** A player looking at a yellow notepad has a different emotional relationship to the game than one looking at a spreadsheet. The interface evolution IS narrative.
2. **Onboarding is built into the world.** New players start with a small handwritten page — minimal information, minimal friction. As they learn the game, the interface grows to match. No tutorial wall.
3. **UI as a reward the player earns.** The computer is a purchase, a facility upgrade alongside the weight room and the mat expansion (Q2 extension). The interface upgrade is part of the dojo's growth.
4. **Aesthetic continuity with the design philosophy.** The notepad stage fits the quiet, diagnostic Neil Adams prose register. The handwritten annotations feel like a real sensei's real notes, not like a game surfacing information.

**Architectural consequence:** the roster needs at least two visual modes — notepad (early game, ~10 students max) and computer (mid-to-late game, scales to any size) — with a one-way transition tied to a specific progression milestone. The notepad mode is a designed UI with fewer affordances; the computer mode is the full power-user interface. This is more UI work than a single design, but the split is natural because the early game genuinely doesn't need the computer's complexity.

---

### Q11a / Q11b / Q11c. ANSWERED.

**Q11a — Former students visible on the roster: YES.** Students who have left, retired, moved to assistant, started their own dojo, advanced to the competition circuit — all accessible via the roster, probably as a separate "alumni" or "history" view. This is where the dojo's accumulated lineage becomes legible. The sensei's legacy is written on this page.

**Q11b — Rival students visible: YES, via film, plus a favorites mechanic.** The sensei can purchase film of competitors — footage of other students in his students' weight classes. Watching the film reveals their preferred moves, their signature techniques, their apparent weaknesses. The sensei can then design training to counter specific rivals his students will face. This is the scouting mechanic and it has a real money cost, so it's a strategic investment.

Beyond film, any student in the wider world can be "pinned" to a favorites tab (Crusader Kings-style) where the player tracks their career over time. This lets the player follow a student who left the dojo, or a rival they developed an attachment to, or just someone they find interesting. Attachment accumulated in interface form — the favorites tab is where your emotional history with people outside your own dojo lives.

**Q11c — Stat update timing: both live and aggregate.** Stats update in real time during granular (session-level) simulation. A student successfully breaks a grip in randori and the display ticks visibly: +0.001 grip. These micro-events aggregate through the session into a composite delta: +0.3 grip at session end. The player sees the small ticks live when zoomed in; they see the consolidated deltas at the weekly roundup.

**This is a compositional simulation — consistent with Ring 1's physics substrate philosophy.** The hierarchy:

- **Atomic events** — per-exchange ticks (a broken grip, a failed throw attempt, a successful ukemi, a grip battle won). Smallest simulation unit. Largely invisible to the player except during close zoom.
- **Session aggregates** — composite deltas across categories (+0.3 grip across a 10-minute randori block). Visible at session end.
- **Pattern emergence** — accumulated sessions reveal stylistic signatures (this student *always* goes for the collar grip first; this student *never* commits to ne-waza). Visible over weeks and months.
- **Character-level understanding** — the legible stats the roster displays are emergent from the tree of smaller events. What you see at the top is the crystallization of thousands of invisible ticks.

This mirrors the design philosophy already baked into Ring 1 — the big legible thing is built from small invisible events. The roster's visible numbers are not authored values; they're emergent properties of lived simulation time. This is now the *third* system expressing that compositional-emergence pattern: Ring 1 physics (atomic exchanges compose into match meaning), cultural feedback (accumulated decisions compose into dojo identity), and student stats (atomic events compose into character).

**Architectural consequence:** the student data model is multi-layer. Atomic event counters, session-aggregate deltas, emergent style signatures, top-level stats — each layer computed from the one below. Debugging the simulation means being able to drill from a legible stat back to the events that produced it. This is a real investment in data-model depth, but it pays back in authenticity: no stat on the roster is a lie, because every stat is traceable to simulated events.

---

### Q10 — The sensei is retired. ANSWERED.

**Answer:** The sensei is retired from competition. He doesn't do randori himself. He only demonstrates instruction — showing techniques, explaining, correcting — without live sparring against students.

**This resolves Q10 with a clean scope-reducing decision.** The sensei doesn't need active competition stats, doesn't need randori physics for himself, doesn't need to be modeled as an active participant in sessions. He's the authority who runs the room, not a fighter in it. This matches most real-world judo dojo structures, where senseis past their prime focus on pedagogy rather than active sparring.

**What this simplifies:**
- No sensei fatigue model
- No balancing the sensei's performance against students'
- No "sensei injured" mechanic
- The sensei's presence in the session simulation is a narrative / coaching overlay, not a physics participant

**What remains implied but not blocking:**
- **Sensei's retired rank.** He's retired at *some* rank. That rank presumably constrains what he can award (Q1e-iii) and influences the dojo's starting reputation. Probably a character-creation attribute alongside father's style.
- **Demonstration quality.** When he "just shows the instructions," that demonstration quality affects how well students learn from it. Tied to the sensei's rank and accumulated teaching experience.
- **Whether the sensei's past competition record affects reputation.** A retired national champion attracts different students than a retired local competitor. Sibling to the father's-style lineage (Q7a) but about the sensei himself.

These can be simple defaults for January (medium rank, medium demonstration quality, modest past record) with depth added post-January.

---

### Q1a — Lifecycle override (quit prevention). ANSWERED.

**Answer:** The sensei cannot directly override a student's decision to quit or leave. What they *can* do: spend more conversation time with the student (raising retention probability), or restructure the class to better fit their needs (which slows other students' progression as a direct cost). Even with maximum investment, the quit probability has a floor above zero — some students will always leave.

**Design intent — trial by fire.** The initial years of a campaign are explicitly designed as a painful learning process for the player. You cannot keep everyone. Attempting to keep one person costs you the others. The game expects the player to internalize this through loss, not through a tutorial. This matches real dojo life: you don't know who will stay, and you can only do so much.

**Architectural consequences:**

1. **Quit probability model with a floor.** Retention is a continuous function of accumulated investment (conversations, matched needs, appropriate session content, good pairings) with a non-zero minimum. The floor represents human unpredictability.
2. **Class restructuring as a lever with costs.** "Restructure the week around Marco's needs" is a schedulable action that has negative externalities for other students. The Q7b session composition is where this plays out — targeting one student's needs means not targeting others'.
3. **Resistance to save-scumming.** The probability floor means even a reloaded-from-save player will sometimes lose the same student. This preserves emotional stakes.

**Sub-questions this opens:**

- **Q1a-i** — Should the quit probability be visible to the player, or hidden? Probably hidden for emotional reasons, with conversation count and need-fulfillment as visible proxies.
- **Q1a-ii** — What's the "trial by fire" failure rate target for the first year? Meaningful fraction of starting students (20%? 40%?) regardless of effort, to teach the lesson. Tunable later.

---

### Q1b — First competition readiness. ANSWERED.

**Answer:** Readiness is a two-party negotiation, not a one-way sensei decision. Every student has an opinion — they either want to go or they don't. The sensei can accept the student's preference, influence a wants-to-go student to sit out, or influence a doesn't-want-to-go student to try. The direction of influence reveals what the sensei wants for the dojo.

**Design consequence — readiness pattern is a cultural input.** A "push everyone into tournaments" dojo produces one kind of student. A "wait until they're ready" dojo produces another. A "let them decide" dojo is a third. The player's accumulated competition-influence decisions become another primary cultural input alongside session content, pricing, father's style, atmospheric choice, and promotion philosophy. **Cultural input count is now six.**

**Decision space:**

- Student wants to go + sensei agrees → normal path
- Student wants to go + sensei says no → disappointed, possible relationship cost
- Student doesn't want to go + sensei pushes → competes anxious, outcome uncertain (growth or trauma)
- Student doesn't want to go + sensei agrees → stays in training, continues developing

**Architectural consequences:**

1. **Student preference attribute.** Every student has a current "wants to compete" value, revealed through conversation (Q9), possibly evolving over time.
2. **Influence is probabilistic, not deterministic.** Sensei can shift preference, not overwrite it. Probability of success tied to relationship depth, student trust, time invested.
3. **Relationship cost for ignored preferences.** Telling a student "no" when they want to go, or pushing a reluctant student, has narrative consequences.

**Sub-questions this opens:**

- **Q1b-i** — Is the student's competition preference visible by default, or only through conversation (like needs/goals)?
- **Q1b-ii** — Can the sensei's influence fail outright (student insists on their preference despite influence)?

---

### Q1d — Dojo reputation and departures. ANSWERED. (Also resolves Q8d.)

**Answer:** Students leaving for another dojo affects your reputation — but only through word-of-mouth. There's no central reputation score that ticks down when a student leaves. Instead, former students talk about your dojo, and that talk propagates into the procedural generation of new arrivals and into narrative events the player encounters.

**What the player sees:**

- Former students appearing at competitions, wearing your dojo's name or a rival's
- Overheard conversations between students at tournaments or between new arrivals
- New students arriving with pre-formed opinions about your dojo, surfaced in initial conversations

**What the player does NOT see:** an explicit reputation meter.

**The Persona/Fire Emblem inverse.** Hajime deliberately rejects the explicit relationship-quality UI that games like Persona and Fire Emblem use. There's no affinity bar, no heart level, no social link rank. The player has to hold the relationship in their own memory. The more you talk to someone, the more you know them, the better you coach them — but nothing on screen tells you "you have a Level 4 bond with Marco." This is a design commitment with teeth: **relationships live in the player's head, not in the UI.** Consistent with Crusader Kings' and Rimworld's approach; inconsistent with JRPG and dating-sim conventions.

**Student-to-student social graph — a new layer.** Students also have relationships with each other, hidden by default. Two students might secretly dislike each other. Pairing them over and over in randori could produce friction the player won't see unless they invest conversation time. This is the student-to-student version of the hidden-needs principle (Q9). A pairing decision is not just a skill decision — it's a social decision.

**Architectural consequences:**

1. **Reputation as computed value, not stored stat.** Recalculated as needed for propagation and event generation; never displayed as a single number. Inputs include student departures and destinations, competition results, retention rates, culture axes, etc.
2. **Student-to-student relationship graph.** Each pair of students has a relationship value (default: neutral), modified by shared sessions, pairings, and context. Hidden until conversation unlocks visibility.
3. **Word-of-mouth event system.** Former students exist in a lightweight ongoing-world simulation — they talk to people, those people talk to others, and the dojo's reputation reaches new arrivals through many small paths, not one central broadcast.
4. **Narrative surfacing.** Competition events generate scouting-style narrative moments — "you see Marco across the venue, wearing another dojo's colors" — that surface reputation in emotionally loaded ways, not dashboard ways.

**Q8d is answered alongside Q1d.** How does reputation propagate? Both ways: silent internal computation AND narrative surfacing. The formula runs in the background; the player learns through moments.

**Implications for other questions:**

- **Q3 (coach decisions) — expanded.** Pairing decisions carry social weight beyond skill matching.
- **Q9 (hidden needs) — generalized.** Hidden-information principle extends to student-student relationships.
- **Q11 (roster) — possible new layer.** Eventually the roster might surface unlocked student-student relationships as small connection indicators.

**Acknowledged open work:** the reputation formula is not fully specified. This is flagged below as a follow-up.

**Sub-questions this opens:**

- **Q1d-i** — The reputation formula itself. What inputs (departures, destinations, competition results, retention, culture axes) compose into the reputation score that biases new-arrival generation? Comrade flagged this as "I really have to sit and think about what that formula is."

---

### Q13 — The Inheritance Event. ANSWERED. (Also resolves Q7a-ii and Q2e.)

**Answer:** Approximately 1–2 in-game years into a campaign, when triggering conditions align (savings threshold met, at least one student at green or brown belt, sufficient time elapsed), a major narrative event fires: the player's father comes to visit.

The father is alive. He runs his own dojo in a different part of the state. He is now terminally ill, and he comes to offer his son (the player) the choice to take over the established dojo before it's too late. Explicitly without pressure: "I see you're running your own thing. It's okay if you don't." The framing is gift, not obligation.

**The choice — two paths with permanent consequences:**

- **Stay with the basement dojo.** The player continues building what they started. The father's dojo passes to the antagonist — the slimy suit, now transitioning from Taekwondo-mill operator into a rival judo dojo. The father's former students appear at competitions under new management.
- **Take over the father's dojo.** The player inherits an established room — larger facility, existing students, existing reputation, staff, cultural legacy. The basement dojo is sold to the antagonist, who converts it into a rival judo dojo. The player's former students are now in enemy colors.

Either way, the antagonist ends up running a judo dojo. The only question is which one. There is no neutral choice — the event cannot be deferred, and the antagonist acts regardless.

**Why this is powerful design:**

1. **The father's existence is emotionally grounded.** Until this event, the father is backstory. When it fires, he's present — and dying. The style inheritance from Q7a goes from abstract DNA to a person saying goodbye.
2. **Neither choice is wrong.** Stay: loyalty to what you built, to the students who came because of you. Take over: honor to the father, larger scope, higher ceiling, his legacy preserved. Both paths are legitimate.
3. **The antagonist's character deepens.** He becomes a real rival — someone who paid attention, waited his chance, and moved when the moment came. His willingness to run a judo dojo (though he doesn't care about judo) adds moral weight to him.
4. **Whatever you leave behind becomes your most personal rival.** You will face your own former students in competition, dressed in the antagonist's colors. That is dramatic gold.
5. **Two campaign shapes from one decision.** The stay-path and take-over-path produce meaningfully different games across the years that follow. Replay value baked into a single choice.

**Scope framing — this isn't extra scope, it's activation scope.** The Q2 extension already acknowledged the antagonist-as-rival-dojo pipeline as Ring 3+ content. The Inheritance Event is the *narrative mechanism* that turns that Ring 3 groundwork into Ring 2 payoff. It's not adding a new system — it's the storytelling that makes an already-planned system land emotionally. Probably ships at Early Access (mid-2028), not at the January 2027 checkpoint.

**Architectural consequences:**

1. **The father is a lightweight simulated entity.** His dojo, his students, his reputation exist offscreen until the event brings him onstage. Never interactive until the visit.
2. **Triggering conditions are multi-factor.** Elapsed in-game time (~1–2 years), savings threshold, at least one green/brown belt. All must align — with a probable time ceiling so the event fires regardless after year 5 or so, possibly reframed (more urgent, father sicker).
3. **Narrative event system is confirmed as a first-class design tool.** The game has scripted branch events alongside its simulated systems. These are rare and weight-bearing — not every week brings a moment of destiny, but moments of destiny exist as a category.
4. **Dojo transitions as a supported operation.** The codebase must support the player's active dojo switching — from basement to father's established room, or losing yours to the suit. All data that defines "your dojo" (calendar, roster, facility upgrades, savings, reputation) must be portable.
5. **Antagonist's judo-dojo state is activated here.** Before: threatening visitor. After: owner of a real competing dojo with his own schedule and students. The antagonist's transformation is mechanically significant, not just narrative.

**Resolves open questions:**

- **Q7a-ii (father alive or dead): ANSWERED.** Father is alive at game start, terminally ill at the Inheritance Event, likely passes during or shortly after.
- **Q2e (when the suit opens his rival dojo): ANSWERED.** Triggered by the Inheritance Event. The rival dojo is whichever one the player didn't choose.
- **Q7a-iii (style lock vs. evolve): partially answered.** Taking over the father's dojo reinforces his style; staying in the basement leaves more room to drift. The choice at the Inheritance Event is itself a style-direction decision.

**Sub-questions this opens:**

- **Q13a** — Time ceiling. If the player hasn't met economic/belt conditions by year 5, does the event fire anyway with different framing (father sicker, more urgent)? Or wait indefinitely?
- **Q13b** — What happens to students at the dojo you leave behind? Do they scatter, follow the player, or come under new management? Each has implications for the word-of-mouth reputation mechanic (Q1d).
- **Q13c** — Are there other "moments of destiny" at similar weight later in the campaign? (Olympic qualification, a senior student's own inheritance event, a challenge from the antagonist, a lineage student asking to break off…)
- **Q13d** — Can the player refuse both options outright? If so, the outcome is identical to "stay with basement" (antagonist takes father's dojo). Might still be worth supporting for role-play reasons.

---

### Q14 — Career Mode structure and the Narrative Event Framework. ANSWERED.

**Answer:** Hajime has two play modes, with Career Mode as the primary entry point for Early Access:

1. **Career Mode** — structured by major scripted narrative events that mark the campaign's spine. Closer to **Wildermyth** than to Dwarf Fortress. The player lives a defined sensei's life — basement dojo start, through decades of career, with recurring moments of destiny that shape the story's direction.
2. **Sandbox Mode** — post-EA content. Open-ended simulation with narrative events disabled. The player drops into a procedurally generated dojo, often mid-world, and plays emergent story. Closer to Dwarf Fortress.

**Career Mode as a life; Sandbox Mode as a world.** This is how the two modes divide labor. Career mode is about *your* sensei's story, with a defined opening and inevitable middle moments. Sandbox is about *a* sensei in a simulated world, where emergence is the storyteller.

**The Narrative Event Framework — first-class design infrastructure.** The Inheritance Event (Q13) is one event in a framework of many. Examples the player can expect:

- **First Team Tournament.** The dojo's first competitive outing, against the antagonist's dojo. Introduces tournament systems and the rivalry.
- **The Antagonist's Fall.** If you beat him enough, the antagonist (who is only in it for money) loses his dojo. A new rival emerges from the void — introducing the rival system as a *class* of content, not just one character.
- **Marriage / Partner.** Optional mid-campaign arc. The sensei may choose to partner.
- **Children.** The sensei may have children. If twins, a mirror of the opening twin-students Anchoring Scene — recursion built into the design's shape.
- **Retirement & Succession.** Decades into the dojo. The sensei must choose a successor. If there are children, the hardest version of this choice is: own blood, or most qualified student? Both are legitimate.
- **Olympics Run.** A late-career student reaching Olympic qualification is its own narrative arc.
- **Two Rising Stars, Same Weight Class.** A recurring structural dilemma: who qualifies, who gets attention, who you back.

**The "either choice is okay" principle — thesis-level.** Every major narrative event presents a binding decision with no morally graded answer. Either path is a legitimate version of the story. The game does not reward "correct" choices or penalize "wrong" ones — it produces a *different* story from each choice. This is the fifth thesis-level design principle in Hajime, sitting alongside attention scarcity, cultural feedback, continuous-sim-with-zoom, and compositional emergence.

Narrative pedigree: this is **Disco Elysium / Citizen Sleeper / Wildermyth** territory. Choices carry weight because they reshape the story, not because they're evaluated.

**The playwright lens — a genuine competitive advantage.** Most management-sim games have weak writing because their developers are systems-first. Hajime has a playwright at the helm. The Narrative Event Framework is the system that leans most directly into that strength. The major events get the prose they deserve.

This also informs scope: Hajime-quality narrative events take real writing time, not just engineering. Plan accordingly.

**Architectural consequences:**

1. **Career Mode and Sandbox Mode are two configurations of the same underlying systems.** Same match engine, same student lifecycle, same economic layer. Career Mode runs the Narrative Event Framework on top; Sandbox Mode disables it. This means the systems build for Ring 1 and the dojo loop serve both modes — no double-building.
2. **Narrative events need a triggering/sequencing system.** Multi-factor triggers (time elapsed, economic state, roster state, prior event history). Ordering rules (Event B blocked until Event A resolves). State tracking (Event A's choice affects Event C's variants).
3. **Writing infrastructure.** Each major event needs dialogue, framing, branch text, consequences. A writing-focused tooling pipeline — Markdown or a light DSL — will pay off as the library grows.
4. **Event library ships incrementally.** Jan 2027 checkpoint: the opening (twins' arrival, basement-dojo first steps). Mid-2028 EA: 5–8 major events including First Tournament and Inheritance. Post-EA (2028–2029): the full arc through marriage, children, succession, Olympics, retirement.

**Scope honesty — the game is a Wildermyth-scale writing project, not just a simulation project.** A full career-length narrative framework (20–30 in-game years) requires significant writing across many branches. Career Mode for EA is probably the first 5–10 in-game years — through first Olympics-reach or first antagonist-fall. The late-career marriage/family/succession arc ships in Early Access updates through 2029. This also reshapes the 2–3 year development timeline: Career Mode writing is a substantial parallel track alongside systems engineering.

**Resolves / revisits open questions:**

- **Q12c (ranked judoka simulation): preference expressed.** Comrade leans toward full procedural simulation — every ranked judoka in the world gets named, nationality'd, and simulated through the years, getting better or stopping. This is Football Manager territory without the real-world API backing. Scope-contingent but direction is set.

**Implications for other questions:**

- **Q1 lifecycle:** late-game states (state 19 "leads seminars" and beyond) nest inside Career Mode narrative events, not just pure simulation.
- **Q9 Anchoring Scenes:** the twins arc is the *opening* of Career Mode. If the player marries and has children, a succession choice for their own children becomes a potential *closing* Anchoring Scene — the full career arc.
- **Q11b (rival students via film):** the rival system is generalized. Rival dojos emerge and fall; film-scouting has an ongoing target pool.

**Sub-questions this opens:**

- **Q14a** — Is there a defined ending to Career Mode, or does it continue indefinitely until the player retires? (Retirement may itself be the ending.)
- **Q14b** — How many major narrative events ship at EA? 5–8 feels right given writing effort vs. event density.
- **Q14c** — Are events fixed in sequence, or do they adapt to player state? Fixed is simpler; adaptive is richer.
- **Q14d** — Does the player choose Career vs. Sandbox at game start, or can they transition mid-run?
- **Q14e** — How does the partner/marriage arc interact mechanically with dojo gameplay? Is a partner an NPC who affects the dojo (helps run it, adds a second coach voice, brings in economic pressure), or narrative-only?
- **Q14f** — First Team Tournament vs. Inheritance Event timing. The first tournament implies the antagonist already has a dojo, but Q13 frames the Inheritance Event as when the antagonist *transitions into judo*. Resolve: possibly the antagonist runs Taekwondo mills pre-Inheritance and acquires a judo dojo *at* the Inheritance Event, so the First Team Tournament postdates the Inheritance. Or the first tournament is against a generic rival, not the antagonist specifically. Needs a decision.

---

### Q15 — Lineage system. ANSWERED.

**Answer:** Every sensei, dojo, and student in Hajime carries lineage-aware data from 1.0 onward, even though the full Crusader-Kings-style multi-dojo simulation doesn't arrive until 2.0. The 1.0 version captures ~80% of the emotional payoff with ~20% of the engineering effort by recording lineage data comprehensively and simulating it narratively rather than continuously.

**The core insight driving this decision.** Recording lineage data is cheap. Simulating an entire living world of dojos evolving over generations is expensive — CK-scale work that Paradox has iterated across 15 years with a 30-person studio. By decoupling the *data model* from the *simulation depth*, Hajime ships a lineage-aware game at 1.0 that feels authentic at the moments the player sees, and unlocks a full multi-dojo world at 2.0 without restructuring the data underneath.

**Lineage-aware fields from 1.0, every entity:**

Each student carries:
- `sensei_who_trained_them` — the sensei responsible for their development
- `dojo_of_origin` — where they trained
- `previous_dojos` — lineage if they transferred between dojos
- `students_they_went_on_to_train` — filled in post-graduation if they become an assistant or start their own dojo

Each dojo carries:
- `founding_sensei` — the original sensei (often the player's father, in Career Mode)
- `succession_history` — ordered list of senseis who ran the dojo
- `lineage_style` — the martial style passed through the dojo's history
- `alumni` — complete record of students who ever trained there

Each sensei carries:
- `trained_at_dojo` — where they themselves were a student
- `trained_by_sensei` — who taught them
- `dojos_run` — history of dojos they've operated
- `students_trained` — aggregate list across all their dojos

**1.0 lineage features (seed version):**

1. **Career Mode retirement as ending.** The player's sensei eventually retires. This is a recognized narrative ending state, not a game-over.
2. **Succession choice as the closing Anchoring Scene.** At retirement, the player chooses a successor — typically a student they've raised through the full lifecycle. In late-campaign runs with children, the choice may be between a child and a top student (echoing the Q14 thesis that either path is legitimate).
3. **Legacy screen.** A summary view of the dojo's history — students who came through, champions produced, belts awarded, the succession choice made, significant narrative moments. This is where the player's multi-decade investment becomes legible as a *history*.
4. **Successor-start Career Mode variant.** An optional new run configuration: begin as the successor who inherited your previous run's dojo. The starting state carries a named roster with some original students still present, inherited reputation, the old sensei's style lineage, and facility upgrades earned in the prior run. This gives the player the full emotional loop — *watch your legacy continue* — without requiring world-scale simulation.
5. **Lineage callbacks in scouting.** When the player views film of a rival's student (Q11b), the lineage data surfaces — "trained by Aya, who trained under Marco, who trained at your basement dojo in 2028." Connection points emerge narratively.

**2.0 lineage features (full world simulation):**

- Ex-students' dojos run as real simulated entities in parallel with the player's.
- Cross-dojo student relationships persist and evolve.
- Multiple senseis in the world all have lineages interweaving across generations.
- The ranking hierarchy (Q12) operates against this living population, not statistical ghosts.
- The player can follow (pin, Crusader-Kings-style) any named judoka anywhere in the world and watch their career.
- The web of dojos becomes a living structure the player can explore — trace any ranked judoka back to their origin, see which dojos descend from which, observe how styles spread or mutate across generations.

**Architectural consequences:**

1. **Data model commits to lineage from day one.** Every entity carries its lineage fields from the first 1.0 build. This is the only load-bearing architectural commitment the 1.0 version must make — without it, 2.0 is a data migration project rather than a simulation layer addition.
2. **Simulation depth is decoupled from data richness.** The same lineage fields that support narrative callbacks at 1.0 support full generational simulation at 2.0. No data model rewrite needed.
3. **Career Mode endings generate lineage artifacts.** A retirement doesn't just save a game state — it saves a *legacy file* that captures the completed run. This file can be referenced by the successor-start variant, used for stat tracking across runs, and eventually feed 2.0's world-simulation seed data.
4. **Successor-start variant is ~2 months of work at 1.0, not ~12.** Two existing systems (endings, openings) wired together with lineage data flowing between, not a new continuous-simulation system.

**The recursion pays off.** Q13 gave the game an opening Inheritance Event — your father passes his dojo to you. Q15 gives the game a closing Inheritance Event — you pass your dojo to your successor. The opening and closing structural mirrors resolve cleanly, and each subsequent Career Mode run can start from the previous run's closing. Over many plays, a player generates a personal history of dojos stretching across generations — at 1.0, stored locally; at 2.0, simulated as a living world.

**Implications for other questions:**

- **Q1 lifecycle:** late-game states (own dojo, seminars, teaching) are now lineage-aware. A student who "starts their own dojo" at 1.0 becomes a retrievable lineage artifact, simulated for real at 2.0.
- **Q9 Anchoring Scenes:** confirms the closing scene — succession — as the symmetric counterpart to the opening Twins scene. The game's narrative arc has both poles now.
- **Q11 (roster):** former students already shown on the roster (Q11a) should surface lineage — who they train now, where they went, what they founded.
- **Q12c (ranked judoka simulation):** the preference for full simulation aligns with 2.0 ambition. 1.0 uses statistical ghosts; 2.0 unlocks the full population as lineage-bearing simulated entities.
- **Q13 (Inheritance Event):** the opening inheritance was always scoped at Early Access / 1.0. The closing inheritance (succession) is now explicitly scoped to 1.0 as well, completing the arc.
- **Q14 (Career Mode):** Career Mode endings are now fully specified — retirement, succession, legacy screen. The mode has a defined shape from opening to closing.

**Sub-questions this opens:**

- **Q15a** — How many successor-start variants are supported? Can you chain infinitely (successor → their successor → *their* successor...) or does the lineage eventually terminate (for performance, for narrative coherence, or by design choice)?
- **Q15b** — Does the successor-start variant preserve the physical dojo and facility upgrades, or just the reputation and roster? Preservation is richer narratively; restart-with-legacy is simpler mechanically.
- **Q15c** — If the player doesn't choose a successor (retires without naming one), what happens? Dojo closes? Sold to the antagonist? Passes to a default senior student?
- **Q15d** — Is the lineage data exportable/shareable (imagine Steam Workshop-style dojo histories)? Out of 1.0 scope but worth noting as a possible community-building post-launch feature.

---

## Meta-questions

Things to notice *about* the week of thinking, not about the questions themselves:

- Which questions pull at you when you sit down to think? That's probably the load-bearing one.
- Which questions keep expanding into new sub-questions? That's probably over-scoped and needs narrowing.
- Which feel like you already know the answer but haven't written it down? Those are the easy wins.
- Is there a question you've been avoiding? Worth noticing.

---

## How to use this document

Return to this chat and answer questions as they clarify. The artifact will update as answers land — moving items from "open" to "answered," flagging new questions that surface. When enough has settled (probably after Session 5 lands and the log split is working), the answered set becomes the input to the actual scope reshape — at which point this document's job is done, and its content migrates into the master doc and `dojo-as-institution.md`.

No pressure to answer in order. No pressure to finish by any particular date. The document is a scratchpad, not a form.

---

*Session 5 is still the next action item. This document waits until after.*
