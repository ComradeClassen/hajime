# Hajime — Design System

> *A 2D coaching simulation rooted in a specific basement on South Avenue West, Cranford, New Jersey.*

**Hajime** is the referee's call that starts every match. It's also the name of a game about what happens before that call — and after it. You don't fight. You coach. You build a stable of judoka, train them, and sit in the chair beside the mat. When the ref calls *Matte*, you get two words. Then the simulation resumes.

This design system captures the visual identity, tone, and UI vocabulary for Hajime and the sensibility around it.

---

## Product context

There is **one product**: the game itself, Hajime, currently a Python/text prototype with a planned 2D pixel-art layer (Ring 5). The design system supports:

- **The game UI** — in-match log, coach's chair / Matte panel, dojo views, tournament brackets.
- **Marketing surfaces** — title card, Steam store page, trailer, dev-log posts.
- **Working documents** — the design kit, brand dossier, pitch decks.

The designer is **Comrade (Classen Creative LLC)** — playwright, performer, and author of the parallel project *Player Two*. Hajime is the primary project through **January 9, 2027**, the target Early Access release date.

### Sources this system was built from

- **Uploaded file:** `uploads/hajime_design_kit.html` — the brand dossier the user created. Palette 01 (Basement Sanctuary), literary serif, hybrid photo+drawn art direction are the chosen directions.
- **Codebase:** `ComradeClassen/hajime` on GitHub. Python simulation code under `src/` (imported into `/src`). Design notes in `design-notes/` and research in `Research/` on the repo (browse on GitHub; not bulk-imported).
- **Key orientation docs read on source:**
  - `hajime-orientation.md` — the emotional core
  - `hajime-master-doc.md` — scope, rings, release plan
  - `design-notes/cultural-layer.md` — style DNA, coach voice
  - (more in the repo: `biomechanics.md`, `grip-graph.md`, `grip-sub-loop.md`, `dojo-as-institution.md`)

---

## Manifest (what's in here)

| File / folder | Purpose |
|---|---|
| `README.md` | This document — the brand brief + index. |
| `colors_and_type.css` | CSS variables for colors, type, spacing, radii, shadows, motion. |
| `SKILL.md` | Agent-invocable skill entry point (Claude Code compatible). |
| `fonts/` | *Reserved* — final font files go here. See Typography notes. |
| `assets/` | Logos, wordmarks, SVG marks, icon references. |
| `preview/` | The Design System tab cards (swatches, type specimens, components). |
| `ui_kits/game/` | UI kit: the in-match experience and coach's chair. |
| `source_refs/` | Preserved pointer to the uploaded design kit. |
| `src/` | Imported Python simulation code — *reference only* for UI designers. |

UI kits available:

- **`ui_kits/game/`** — the in-match view (match log + score strip + Matte panel with coach instructions). Built from the Anchoring Scene in the master doc.

---

## Content Fundamentals — *how Hajime talks*

The voice of Hajime is a **knowledgeable sportswriter who loves judo**. It is observational, specific, calm, and never hyped. It is the opposite of UFC announcer energy. It is the voice of a book about judo.

### Three voices, one system

Hajime speaks in three registers, each for a different surface:

1. **Match-log voice (sportswriter).** The scrolling prose during a simulated match. Specific, causal, present-tense. Short sentences earn their ending with a period, not a bang.
   > *"Tanaka steps in. Right hand reaches for the lapel. Sato's left hand intercepts — pistol grip on the sleeve."*
2. **Coach-chair voice (intimate).** The copy inside the Matte panel. Quiet, slightly worried, physics-aware without being clinical. This is the player's inner monologue about their fighter.
   > *"He went for his strongest throw too early. Sato read it."*
3. **Dojo voice (warm).** The copy in the dojo/menu surfaces. The texture of routine — sweat, repetition, a small joke under breath, the mats in the morning.
   > *"Tuesday. Kids' class at four. Uchikomi bands on the wall, right where you left them."*

### Casing

- **Sentence case** for everything. Headlines, buttons, menu items, tooltips. Title-case feels marketed-at. Hajime is not marketed-at.
- **ALL CAPS** only for broadcast chrome (score strip during a match: *"ROUND 1 · –73KG · TANAKA vs. SATO"*) and for referee calls (*"MATTE."*). The caps earn their weight by being rare.
- **Japanese terms** stay lowercase and italic when used in English prose (*ippon*, *matte*, *kuzushi*, *uchi-mata*). No ALL CAPS, no bolding. They are just words in the sport.

### Pronouns & stance

- Address the player as **you**. *"You have two words."*
- Refer to the judoka by name or by pronoun. The judoka is not "your character." They are a person.
- The narrator (match-log) never says *I* or *we*. It describes what happened.
- The coach-chair voice is the *player's* thinking. It can say *you* about the fighter (*"You taught him that last spring"*) — the second person is intentionally ambiguous here.

### Rules of tone

- **No exclamation marks.** Not one. (The match ends on a period, even ippon.)
- **No hype words.** No "EPIC," "CRUSHED," "INSANE," "AMAZING." Not here.
- **No jargon-flex.** Japanese words are used where they are the *real* word for the thing (ippon, matte, kuzushi). Each is explained once, in-world (tooltip on first appearance).
- **Dignity for everyone, especially the loser.** Opponents are named, described specifically, and treated as athletes.
- **Physics resolves; prose marks.** The sim never says *"moment arm modifier succeeded."* It says something that earns the moment. *"The smaller fighter got under him."*
- **Reverent about the ritual, not solemn.** The bow matters. A match can also end funny.

### Emoji

**No emoji.** Not in the product, not in marketing, not in dev logs. The identity is old-style serif on ink — emoji break it. The only unicode glyphs that appear are the Japanese characters used where Japanese is the real word (*始め*), and typographic marks (*—*, *·*, *↓*, *✓*, *⚠*) used as quiet signal in the Matte panel.

### Example copy in all three voices

| Surface | Copy |
|---|---|
| **Match log** | `0:18 Tanaka attempts seoi-nage — Sato sprawls. Hips back. Throw stuffed.` |
| **Coach chair** | *His entry window is closing. Right forearm is going.* |
| **Dojo menu** | Tuesday — kids' class at four. Uchikomi on the wall. |
| **Button (primary)** | Begin the match |
| **Button (danger)** | Withdraw Tanaka |
| **Empty state** | The wall is blank. No champion has signed it yet. |

---

## Visual Foundations — *how Hajime looks*

### The guiding image

**Walking down the stairs at 107 South Avenue West.** Street noise drops. The air gets warmer. A single amber bulb under the stairs catches an old trophy case. Someone is already on the mat. That's the feeling. Every visual choice traces back to it.

### Color — Basement Sanctuary

The palette is **ink-dominant, amber-accented, with mat green as the working surface and oxblood as rare urgency**. Full tokens in `colors_and_type.css`.

- **Ink black `#1a1410`** is the canvas. Never pure `#000` — Hajime's black always has a warm undertone.
- **Amber bulb `#d4a04a`** is *the only warm light source.* Use it for numerics, focus states, accents, and the wordmark on ink. If something glows, amber is why.
- **Mat green `#4a5838`** is the tatami — training UI surfaces, the mat in match view, dojo floor panels.
- **Oxblood `#7b2418`** is urgency. Exit signs. Ippon calls. Shido counters. Withdraw actions. Use rarely — rarity is the point.
- **Trophy wood `#6b4a2e`** is for frames, trophy cases, category dividers in the dojo, ranked-list surrounds.
- **Gi cream `#f5edd8`** is the body-text color on ink, and the color of the judogi in any illustration.
- **Paper `#efe6d0`** is the document surface — menus, guides, documentation, the README itself when printed. The counterpart to the ink sanctuary.

Imagery leans **warm, amber-biased, with visible grain**. Never cool-blue, never hi-gloss. If there is a reference aesthetic, it is a photograph of a small American dojo taken on a 35mm camera with tungsten-balanced film, slightly pushed.

### Type — Literary serif + broadcast sans

Two families carry the whole system:

- **Serif (primary):** Iowan Old Style, Palatino, or Hoefler Text. We ship with **Sorts Mill Goudy** as a Google Fonts substitute (the nearest open-source old-style match). *FLAG: replace with licensed Iowan Old Style or Hoefler Text for final production — font files should drop into `fonts/`.*
- **Mono:** **IBM Plex Mono** (substitute for SF Mono). Used for timecodes, numeric readouts, the grip-graph edge list. The voice of data.
- **Broadcast sans:** **Inter Tight Light** (substitute for Helvetica Neue Light). Used *only* for tournament score strips and broadcast chrome. The contrast between serif-sanctuary and sans-broadcast is load-bearing.

The scale is set in `colors_and_type.css` (see `--fs-micro` through `--fs-display`). The whole system wants air — generous line-height (1.6 body, 1.75 loose), short measure (~52ch for quotes, 68ch for prose).

### Layout — document, not dashboard

Hajime's layouts are **page-like**. Centered `1080px` container for prose surfaces. Booky margins. Section headings numbered with a small circled `01 / 02 / 03`. The match screen departs from this — it is an instrument panel — but every other surface reads like a typeset document.

### Backgrounds

- **Solid ink or solid paper.** No gradients as primary backgrounds. The two exceptions below are subtle and tied to the metaphor.
- **Amber bulb vignette.** On key title/menu surfaces, a very soft `radial-gradient` of `rgba(212,160,74,0.08)` in one corner — the implied bulb under the stairs. Never centered; always offset like real light.
- **Paper radial.** On document surfaces, a warm `radial-gradient` from top-left light and bottom-right shadow, tinting the paper unevenly like an old book. Already built into the design kit.
- **No stock textures.** No noise filters, no paper grain overlays. Texture comes from real photography when photography is used (see Art Direction).
- **Art direction: photograph + drawn paper-doll judoka.** Photographed dojo backgrounds, hand-drawn figures layered on. Match view uses a warm-lit drawn tatami. See the master design kit for reference.

### Borders, rules, dividers

- **Hairline amber on ink** (`rgba(212,160,74,0.3)`) for panel edges on dark surfaces.
- **Paper-dark hairline** (`#d8cdb0`) for card borders on light surfaces.
- **Dotted divider** (`1px dotted rgba(212,160,74,0.22)`) between stat lines in the Matte panel. This is a direct quote from old printed match stats sheets.
- **Solid 1px**, never 2px+ except for a single `border-left: 2px solid` on pull-quotes.

### Corners & radii

- **Small.** `2–4px`. Hajime is printed material, not app-store-glossy. Nothing is a pill except micro chips.
- **`--r-3` (4px)** is the ceiling for section and major surface radius.
- **No `border-radius: 16px` or larger** anywhere except a full-round `--r-full` for the numbered section markers (`01`, `02`, etc.).

### Shadows

Three systems, used sparingly:

- **Print-offset** `2px 3px 0 rgba(60,45,20,0.06)` — paper cards. This is a letterpress tell, not a material tell.
- **Ink** `0 2px 12px rgba(0,0,0,0.35)` — lift for dark-surface panels. Subtle.
- **Bulb glow** `0 0 24px rgba(212,160,74,0.18)` — rare, reserved for focus on the primary amber element (e.g., the wordmark on the title screen).

No drop-shadows-as-decoration. No inner shadows on inputs.

### Transparency & blur

- **Transparency**, yes — for tints (`rgba(245,237,216,0.06)` as a hover veil on ink).
- **Blur (`backdrop-filter`)**, no. The aesthetic is printed, not materialist. Blur belongs to iOS, not to a basement.

### Motion

- **Fades and color shifts only.** No slides, no scales, no springs.
- **Ease:** `cubic-bezier(0.25, 0.1, 0.25, 1)` — standard, honest.
- **Durations:** 120ms / 220ms / 400ms. Almost everything is 120–220ms.
- **No bounce. No elastic.** The dojo does not bounce.
- **One exception:** the match log's new-line appears with a **0.4s opacity fade-in** to simulate pace. That is the only expressive motion in the product.
- **Hover:** on amber text, lift to `--amber-glow` (`#e8ba66`). On cream text, lift opacity by ~0.15. On paper cards, no transform — a slight `box-shadow` deepening is enough.
- **Press:** darken by ~6%. No scale-down. (The dojo does not shrink when you tap it.)

### Cards — what a card is

- **On ink:** background `rgba(245,237,216,0.06)`, border `1px solid rgba(212,160,74,0.35)`, radius `--r-2`, no shadow, padding `--s-3` or `--s-4`.
- **On paper:** background `--paper-card` (`#faf4e2`), border `1px solid --paper-dark`, radius `--r-2`, shadow `--shadow-print`, padding `--s-5`.

### Wordmark

Primary is **"Hajime"** set in Sorts Mill Goudy/Iowan at `--fs-display`, with the subtitle **"— 始め —"** in oxblood italic beneath. Secondary lockups: broadcast caps in amber (`HAJIME` spaced `0.24em`), and the lowercase-with-period variant (`hajime.`) for intimate placements.

### Protection & clear space

Around the wordmark, reserve clear space equal to the cap-height of the `H`. Against paper, the wordmark is ink-black. Against ink, it is gi-cream or amber. Never place it on a photograph directly — put it on a solid plate cut from the photograph's darkest area.

---

## Iconography

Hajime's icon approach is **restrained, typographic, and nearly invisible**. The game's visual language does most of the work; icons are used only where copy alone would be ambiguous.

- **No icon font bundled with the game.** Typography and unicode marks cover ~90% of in-product needs.
- **For non-ambiguous cases (arrows, check, warn), use unicode typographic marks**: `→` `←` `↑` `↓` `↓↓` `✓` `⚠` `·` `—`. These are already part of the Matte panel specimen in `preview/`.
- **For the remaining ~10%** (menu, close, play/pause, settings, medal, trophy, dojo, calendar), we reference **[Lucide](https://lucide.dev/)** icons via CDN — lineweight `1.5`, rounded caps, monochrome in `--amber-bulb` on ink or `--ink-soft` on paper. Lucide is the closest stroke match to our literary aesthetic and is the standard flagged substitute. *FLAG: if a custom icon set is drawn for v1, replace the Lucide dependency; this is a placeholder choice and has been documented as such.*
- **No filled icons.** Everything is stroked.
- **No emoji.** (Repeated from tone rules — but it's also the iconography rule.)
- **No branded pictograms in the UI.** The judoka figures in the match view are illustration, not iconography. They will live in `assets/illustrations/` when drawn; for now a placeholder is shown.

### SVG assets shipped in `assets/`

- `assets/logo/hajime-wordmark-serif.svg` — primary wordmark on paper.
- `assets/logo/hajime-wordmark-amber.svg` — broadcast lockup on ink.
- `assets/logo/hajime-lowercase.svg` — intimate lockup (`hajime.`).
- `assets/mark/hajime-kanji.svg` — standalone *始め* mark in oxblood.
- `assets/illustrations/judoka-silhouette.svg` — placeholder for the drawn-judoka layer.

All wordmarks are typeset SVGs — they reference the web font at render time and are flattened for final production. They are not hand-drawn letterforms.

---

## Caveats the reader should know

- **Fonts are substitutes.** Sorts Mill Goudy, Inter Tight, and IBM Plex Mono stand in for Iowan Old Style, Helvetica Neue Light, and SF Mono respectively. Licensed replacements should drop into `fonts/` and the `@import` in `colors_and_type.css` should be removed.
- **Icons are a flagged Lucide placeholder.** See Iconography above.
- **The drawn-judoka illustration is a placeholder silhouette.** Final art is Ring 5 work and will require an illustrator.
- **No photography has been shot yet.** The hybrid art direction (photo dojo backgrounds, drawn characters) is aspirational until the designer has permission to photograph Cranford JKC.
