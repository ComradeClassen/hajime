# Rename Tachiwaza → Hajime + Linear Setup
### Step-by-step execution plan. Follow in order. Do not skip steps.

*Created April 16, 2026. Written to be executed in a single sitting of ~45–60 minutes. The order matters — each step assumes the previous one completed cleanly.*

---

## BEFORE YOU START — READ THIS FIRST

### What this document does

This doc walks you through renaming the project from **Tachiwaza** to **Hajime** across:
- Your local filesystem
- Obsidian vault
- Git repository (local + GitHub)
- Python codebase (module names, identifiers, docstrings)
- Cross-referenced markdown files

Then it sets up **Linear** as the project management tool for the Hajime team, seeded with the right structure for Ring 1 work.

### Why the order matters — and the Hajime-specific trap

The rename has one major trap unique to this title: the word **"hajime" already exists throughout the codebase and design docs as the Japanese judo term itself** — it's the referee call that starts the match. You'll see it in:
- The coaching bible (`Matte-Hajime cycles`, prose describing the start of a match)
- Docstrings and comments that reference the referee call
- Prose templates that narrate `0:00 — Hajime.`
- Possibly variable names like `hajime_tick` or `ticks_since_hajime`

**These existing uses of the word `hajime` are correct and must survive the rename untouched.**

The good news: because we're renaming `Tachiwaza` → `Hajime` and doing case-sensitive whole-word replacements on `Tachiwaza` / `tachiwaza` / `TACHIWAZA`, we are never searching for the string `hajime` as a find-target. So technically there is no collision.

The caution: after the rename, some contexts will have `Hajime` appearing as both the project name and the judo term on the same page, which is semantically fine but can be visually confusing. We handle this in Step 3 with a pre-flight audit so you know where the existing `hajime` references are and can spot-check them after the rename is done.

**The defensive order:**
1. Commit current state (so you can roll back if anything goes wrong).
2. Audit existing `hajime` usages first — know where they live so you can verify they survived.
3. Do case-sensitive replacements on `Tachiwaza` variants in a specific order.
4. Test the code still runs.
5. Rename the folders and GitHub repo last (so you aren't fighting path changes mid-edit).
6. Linear setup comes after the rename is clean.

### What you'll need

- Laptop or desktop — don't do this on mobile.
- VS Code open.
- Terminal open (Git Bash or PowerShell on Windows).
- GitHub logged in, with permission to rename the repo.
- Obsidian closed (you will reopen it at the end).
- ~45–60 minutes of uninterrupted time.
- This document open in a second window you can reference.

---

## PART 1 — RENAME EXECUTION (Steps 1–13)

### STEP 1 — Commit and push current state (safety net)

Open terminal in `C:\Users\jackc\Documents\tachiwaza` and run:

```bash
git status
git add -A
git commit -m "Pre-rename checkpoint: snapshot before Tachiwaza → Hajime migration"
git push origin main
```

**Why:** If anything goes sideways in the next 12 steps, you can `git reset --hard HEAD~1` or clone fresh from GitHub. This is your escape hatch.

**Verify:** `git status` reports "nothing to commit, working tree clean."

---

### STEP 2 — Close Obsidian completely

Fully quit Obsidian. Not just close the window — exit the app. File watchers that Obsidian keeps open will block folder renames on Windows.

**Verify:** Obsidian is not in the system tray or Task Manager.

---

### STEP 3 — Audit existing uses of "hajime" BEFORE renaming anything

This is the critical pre-flight check. You need to know where `hajime` already appears as the judo term so you can verify those references survive the rename intact.

In VS Code, open the project folder. Then:

1. Press `Ctrl+Shift+F` (global find).
2. Search for: `hajime` (case-insensitive, no "match case" toggle).
3. Note the files where `hajime` appears. Expected hits:
   - `The_Chair__the_Grip__and_the_Throw...md` — multiple references to "Matte-Hajime cycles"
   - `tachiwaza-master-doc.md` — possibly in prose examples (`0:00 Hajime`)
   - `data-model.md` or `grip-sub-loop.md` — possibly in state descriptions
   - Python files: potentially `hajime_tick` or similar timing variables
4. **Copy this list somewhere you can reference it after Step 7.** A scratch text file, a note in Obsidian (before you close it — too late, then just jot it on paper), whatever works.

**Why:** These existing `hajime` usages are **the judo term and must survive**. The rename is not searching for `hajime` as a find-target, so they should survive automatically — but knowing where they live lets you verify that in Step 7.

**A bonus benefit:** this audit also tells you where you might want to eventually add prose that plays on the fact that the game title *is* the referee call. That's future creative territory, not for tonight.

---

### STEP 4 — Replace `Tachiwaza` (capitalized) across the project

In VS Code:

1. `Ctrl+Shift+H` (global find-and-replace).
2. Find: `Tachiwaza`
3. Replace: `Hajime`
4. **Toggle "Match Case" ON** (the Aa icon).
5. **Toggle "Match Whole Word" ON** (the `ab` icon with brackets).
6. Review the results panel. Expected locations:
   - Markdown headings
   - Docstrings
   - Comments
   - Cross-file references
7. Click "Replace All."

**Verify:** Spot-check `tachiwaza-master-doc.md` → the title should now read `# HAJIME — Master Design & Development Document` (or similar — your exact heading style).

**A note on the result:** you'll see sentences now like "Hajime is the primary project through January 9, 2027." That sentence is correct in two ways at once — it refers to the game and nods at the referee call. Lean into that; it's one of the reasons the title works.

---

### STEP 5 — Replace `tachiwaza` (lowercase) across the project

**Caution:** This step cannot collide with existing `hajime` uses because we're matching whole words and case-sensitively — `hajime` and `tachiwaza` are completely different character strings. Still, be deliberate.

In VS Code:

1. `Ctrl+Shift+H`.
2. Find: `tachiwaza`
3. Replace: `hajime`
4. **Toggle "Match Case" ON.**
5. **Toggle "Match Whole Word" ON.**
6. Review results. Expected hits:
   - Filenames referenced in wiki-links: `[[tachiwaza-master-doc]]` → `[[hajime-master-doc]]`
   - Python imports (if any): `from tachiwaza import ...` → `from hajime import ...`
   - Variable names like `tachiwaza_root` or `TACHIWAZA_VERSION`
7. Click "Replace All."

**Verify:** Spot-check one of your Python files — imports should now read correctly. Spot-check the files from your Step 3 audit — existing `hajime` (judo term) references should be untouched. If any of them say `hajime` now where they said `hajime` before, you're fine. If any of them got garbled, something went wrong — `git diff` will show you what.

---

### STEP 6 — Replace `TACHIWAZA` (all caps, if any)

Some constants may be all-caps. Quick sweep:

1. `Ctrl+Shift+H`.
2. Find: `TACHIWAZA`
3. Replace: `HAJIME`
4. **Match Case ON, Match Whole Word ON.**
5. Review and replace all.

**Verify:** If you had no all-caps constants, the result will be "No results found" — that's fine.

---

### STEP 7 — Verify existing `hajime` (judo term) uses survived

Revisit the list you captured in Step 3. Open each file and confirm the `hajime` references still read as the judo term in context. Examples of what you should see:

- Coaching bible: `Matte-Hajime cycles` — still there, still reads as judo jargon.
- Prose examples: `0:00 — Hajime.` — still there, still reads as the match opening.
- Variable names: `hajime_tick` — still there, still functional.

If anything got corrupted (unlikely given case-sensitive whole-word replacement, but worth checking), run `git diff` in terminal and scan for unexpected changes.

**Verify:** Every `hajime` reference in your Step 3 audit list still exists and still reads correctly in context.

---

### STEP 8 — Run the Python code to confirm it still works

Before renaming files, confirm the code still imports and runs with the new identifiers.

In terminal:

```bash
python main.py
```

Or whatever the entrypoint is for your match simulation.

**Expected:** The simulation runs. A match plays out. No `ImportError`, no `NameError`, no references to the old name.

**If it fails:** The error message will tell you which file still has an old reference. Fix that one, rerun. Do not proceed to Step 9 until the code runs cleanly.

---

### STEP 9 — Rename the markdown files

Files to rename in the Obsidian vault (likely in `C:\Users\jackc\Documents\tachiwaza\` or an `obsidian-vault` subfolder):

| Old filename | New filename |
|---|---|
| `tachiwaza-master-doc.md` | `hajime-master-doc.md` |
| `tachiwaza-orientation.md` | `hajime-orientation.md` |
| `The_Chair__the_Grip__and_the_Throw__A_Judo_Coaching_Language_and_Style_Bible_for_Tachiwaza.md` | `The_Chair__the_Grip__and_the_Throw__A_Judo_Coaching_Language_and_Style_Bible_for_Hajime.md` |
| `From_Tissue_Layers_to_Tatami__What_Dwarf_Fortress_Teaches_Tachiwaza.md` | `From_Tissue_Layers_to_Tatami__What_Dwarf_Fortress_Teaches_Hajime.md` |

Use File Explorer or VS Code's file tree to rename (right-click → Rename).

**Verify:** The files are renamed and still open correctly.

---

### STEP 10 — Update wiki-links in markdown files

Renaming files breaks `[[link]]` references. In VS Code, do one more global find-and-replace pass for the markdown link syntax:

1. `Ctrl+Shift+H`.
2. Find: `[[tachiwaza-master-doc]]`
3. Replace: `[[hajime-master-doc]]`
4. Match Case ON.
5. Replace All.

Repeat for each renamed file. Do the same for the two research docs if they're wiki-linked anywhere.

**Verify:** Open `hajime-master-doc.md` and scan for broken links. None should appear as unresolved.

---

### STEP 11 — Rename the project folder on disk

In File Explorer:

1. Navigate to `C:\Users\jackc\Documents\`.
2. Right-click `tachiwaza` → Rename → `hajime`.
3. Press Enter.

**If Windows refuses** with "folder in use": VS Code is still holding the folder open. Close VS Code, rename, then reopen.

**Verify:** The folder at `C:\Users\jackc\Documents\hajime` exists. The old folder is gone.

---

### STEP 12 — Rename the GitHub repo

1. Go to `https://github.com/<your-username>/tachiwaza` (or whatever the current URL is).
2. Click **Settings** (top tab).
3. Scroll down to the **Repository name** field.
4. Change `tachiwaza` to `hajime`.
5. Click **Rename**.

GitHub auto-redirects the old URL to the new one, so any old clones won't immediately break — but the correct thing to do is update your local remote.

Open terminal in `C:\Users\jackc\Documents\hajime` and run:

```bash
git remote set-url origin https://github.com/<your-username>/hajime.git
git remote -v
```

The output of `git remote -v` should show the new URL on both fetch and push lines.

**Verify:** Run `git pull`. It should succeed and report "Already up to date."

---

### STEP 13 — Reopen Obsidian and confirm the vault is clean

1. Launch Obsidian.
2. It will likely flag the vault as missing (since the folder moved). Point it at the new location: `C:\Users\jackc\Documents\hajime\`.
3. Open `hajime-master-doc.md`.
4. Click through 3–5 wiki-links to confirm they resolve.
5. Check the Files panel on the left — every file should be findable, no broken links in the graph view.

**Verify:** No Obsidian warnings about missing files. Wiki-links resolve.

---

### STEP 14 — Final commit of the rename

Back in terminal:

```bash
cd C:\Users\jackc\Documents\hajime
git status
git add -A
git commit -m "Rename Tachiwaza → Hajime: full rename across vault, codebase, and repo"
git push origin main
```

**Verify:** GitHub now shows the repo at the new URL with a fresh commit titled "Rename Tachiwaza → Hajime..."

---

## PART 2 — LINEAR SETUP

You've got the Linear account ready. Here is how to structure it for Hajime so it earns its place rather than becoming another tool you maintain.

### STEP 15 — Create the workspace

If you haven't already:

1. Sign into Linear.
2. Create a workspace named `Hajime Studio` (or whatever feels right — one workspace to house both Hajime and Player Two eventually).
3. Free tier is fine for a solo dev. No need to upgrade.

---

### STEP 16 — Create the first team

Inside the workspace:

1. Create a team called **Hajime**.
2. Team identifier: `HAJ` (this will prefix every issue — `HAJ-1`, `HAJ-2`, etc.).
3. Skip the templated setup flow — you want clean slates.

**Why a team prefix:** Once you commit with `git commit -m "HAJ-15: add grip sub-loop tick"`, GitHub's Linear integration auto-links the commit to the issue. Later, when Player Two resumes, it gets its own team (`P2`) with its own prefix.

---

### STEP 17 — Create the Projects structure (one per Ring)

Inside the Hajime team, create four Projects:

| Project name | State | Purpose |
|---|---|---|
| Ring 1 — Match Engine | Active | Everything in-scope for January 9 ship, match-simulation side |
| Ring 2 — Coach Instructions | Planned | Matte window, reception calc, cultural voices |
| Ring 3 — Dojo as Institution | Backlog | Parked for post-January (Scenario B only) |
| Infrastructure & Polish | Active | Renames, tooling, documentation, sound, art, marketing |

Only **Ring 1** and **Infrastructure & Polish** should be Active at start. Ring 2 becomes Active in August. Ring 3 stays Backlog indefinitely.

---

### STEP 18 — Connect GitHub

Critical — this is the integration that makes Linear pay rent:

1. In Linear → Settings → Integrations → GitHub.
2. Authorize Linear to access your `hajime` repo.
3. Enable **two-way sync**:
   - Linear issue status updates based on PR state.
   - Commits with `HAJ-<n>` in the message auto-link to the issue.
   - Merging a PR that references `HAJ-<n>` auto-closes the issue.
4. Test it: make a trivial commit like `git commit -m "HAJ-1: test integration" --allow-empty` and push. In a minute or two, if you've created `HAJ-1`, you'll see the commit appear on it.

---

### STEP 19 — Seed Ring 1 Project with the initial issue set

Do not seed everything. Seed **only the next two cycles (4 weeks) of work**. You'll add more as clarity arrives. The goal is 10–15 issues to start.

**Suggested seed issues for Ring 1 — Match Engine (the next four weeks):**

*Calibration pass (after the playthrough sharpening):*
1. `HAJ-1` — Complete the playthrough observation pass with `[FEEL] / [BUG] / [PROSE] / [PACE]` tagged notes (15–20 more beyond the 12 done)
2. `HAJ-2` — Synthesize playthrough notes into a Session 3 decision doc (A/B/C modes)
3. `HAJ-3` — Make the Session 3 mode decision and commit to it in writing

*Known bugs from the 12 playthroughs completed so far:*
4. `HAJ-4` — Fix duplicate throw-log lines (the `t234 forces Tai-otoshi` / `t234 → Tai-otoshi → failed` doubling)
5. `HAJ-5` — Prevent impossible ne-waza → throw transitions within 2 ticks (force standing reset between side-control and kuzushi window)
6. `HAJ-6` — Tune draw frequency downward (too many matches ending in stalemate)
7. `HAJ-7` — Slow the grip-establishment rate (grips shouldn't lock in within 2 ticks for both judoka)
8. `HAJ-8` — Add shido escalation for grips held without attack (the t037–t076 stalemate pattern)

*Log-readability improvements:*
9. `HAJ-9` — Clarify the "net" value in throw-result log lines or remove it from player-facing output
10. `HAJ-10` — Clarify what `delta` and `Window: N tick(s)` mean in player-facing output
11. `HAJ-11` — Add between-tick state descriptors (what are judoka doing during stuffed-throw aftermath?)

*Tooling for faster iteration:*
12. `HAJ-12` — Add a "simulate N matches" CLI flag so you don't have to re-run the full Python script each time

*Design work gated behind the playthrough decision:*
13. `HAJ-13` — (Session 3 Mode B or C) Spec the force / posture physics model as a design doc before coding
14. `HAJ-14` — (Session 3 Mode C only) Implement continuous posture value driven by grip-transmitted forces

Adjust these to reflect what's actually in your head tonight — this is a starting skeleton, not a commandment.

---

### STEP 20 — Create the first Cycle (sprint)

In Linear:

1. Go to the Hajime team → Cycles.
2. Enable cycles (if not already on).
3. Set cycle length: **2 weeks**.
4. Start the first cycle today (April 16) or Monday April 20, whichever fits your rhythm.
5. Pull `HAJ-1` through `HAJ-6` into the first cycle. Leave the rest in the backlog for now.

**The rule:** never pull more into a cycle than you think you can finish in two weeks. If you over-commit once, Linear's burndown chart will tell you. If you under-commit, it'll tell you that too. Trust the data after two full cycles before adjusting.

---

### STEP 21 — Set the daily workflow

Print this or save it as a sticky note in your workspace:

1. **Session start:** Open Linear → Current Cycle → pick next issue → move to "In Progress."
2. **Work:** Code in VS Code / Claude Code. Commit frequently with `HAJ-<n>` in the message.
3. **Session end:**
   - Merge PR → issue auto-closes.
   - Capture any new issues you discovered into the backlog (don't groom them yet, just write them down).
   - Write a one-line note in the commit history about what you did.

**Discipline rules (carried over from the April 16 synthesis):**
- Linear grooming happens at **session start/end only**, not mid-coding.
- Master doc = *why and what it means*. Linear = *what's next and is it done*.
- Do not duplicate between Obsidian and Linear. Obsidian is design. Linear is execution.
- Give the tool two full cycles (four weeks) before deciding whether it's sticking. Don't abandon early; don't celebrate early.

---

## PART 3 — AFTER BOTH ARE DONE

Before closing the laptop:

1. **Update `hajime-master-doc.md`** — change the title block, add a line near the top saying "Renamed from Tachiwaza on April 16, 2026. The title *Hajime* refers to the referee's call that starts every match — the game is everything that happens before Hajime is set, and everything that happens after."
2. **Create `post-january.md`** — empty file at first, with just a header. This is the parking lot for Ring 3+ ideas that arrive during Ring 1/2 work.
3. **Commit it all:**
   ```bash
   git add -A
   git commit -m "HAJ-setup: rename complete, Linear wired, post-january.md stub created"
   git push origin main
   ```

---

## TROUBLESHOOTING

### "VS Code won't let me rename the folder — file in use"
Close VS Code entirely. Close Obsidian. Close any terminal that has `cd`'d into the folder. Then rename. Then reopen.

### "Git says the remote isn't found after GitHub rename"
You forgot `git remote set-url origin <new-url>` in Step 12. Run it.

### "Wiki-links in Obsidian are broken"
You likely missed a file in Step 10's wiki-link update pass. Use Obsidian's "Files" sidebar → look for red/unresolved links → fix them manually.

### "Python code throws an error after the rename"
An import statement still references the old name. Open the file the traceback points to. Run `Ctrl+Shift+F` and search for `tachiwaza` globally — find the last one and replace it.

### "Linear's GitHub integration doesn't auto-close issues"
Check that your commit message format is **exactly** `HAJ-<number>: ...` with a space after the colon. Linear's parser is picky. Also verify the PR was merged to `main`, not just closed.

### "An existing 'hajime' reference (the judo term) looks weird after the rename"
Run `git diff` against the pre-rename commit from Step 1. The diff will show every change made. If a `hajime` (judo term) reference got corrupted, the diff will point you to it. Very unlikely given the case-sensitive whole-word matching, but this is your forensic tool if something feels off.

---

*Document created April 16, 2026. Execute in one sitting. Delete this file after Part 3 is complete, or move it to an `archive/` folder for future reference.*
