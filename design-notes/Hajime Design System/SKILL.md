---
name: hajime-design
description: Use this skill to generate well-branded interfaces and assets for Hajime, a 2D coaching simulator about judo, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick orientation

- **Voice:** sportswriter/booky. Sentence case. No exclamation marks. No emoji. No hype.
- **Colors:** Basement Sanctuary — ink black `#1a1410`, amber bulb `#d4a04a`, mat green `#4a5838`, oxblood `#7b2418`, trophy wood `#6b4a2e`, gi cream `#f5edd8`, paper `#efe6d0`. See `colors_and_type.css`.
- **Type:** Sorts Mill Goudy (serif, primary), IBM Plex Mono (mono, numerics), Inter Tight Light (broadcast caps). All CSS-var driven.
- **Corners:** small (2–4px). Shadows: print-offset, not diffused. Motion: fades only, 120–220ms.
- **Logos:** `assets/logo/*.svg`. Kanji mark: `assets/mark/hajime-kanji.svg`.
- **Reference UI kit:** `ui_kits/game/index.html` — title, dojo, match, matte, post.
