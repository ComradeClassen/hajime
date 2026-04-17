#!/usr/bin/env python3
"""
rename_to_hajime.py
===================

Renames Hajime → Hajime across all text files in the project.

Replaces Steps 4, 5, 6, and 10 of the rename execution doc in a single
deterministic pass. Does NOT rename files or folders — that stays manual
(Steps 9, 11, 12) because folder renames have OS-level side effects you
want to do with your eyes open.

Behavior:
  - Walks the project root recursively.
  - Skips: .git/, __pycache__/, .obsidian/, node_modules/, venv/, .venv/,
           and any binary files (detected by attempting UTF-8 decode).
  - In each text file, performs three case-sensitive whole-word replacements:
      Hajime  -> Hajime
      hajime  -> hajime
      HAJIME  -> HAJIME
  - Also updates Obsidian wiki-links of the form [[hajime-*]]
    to [[hajime-*]] (Step 10 work).
  - Existing uses of "hajime" as the judo term are NEVER touched
    because we never search for "hajime" as a find-target.

Safety:
  - Dry-run mode by default. Run with --apply to actually write changes.
  - Prints a summary of every file that would change and how many
    replacements would happen in each.
  - Aborts immediately if it can't write to a file.

Usage:
  cd C:\\Users\\jackc\\Documents\\hajime
  python rename_to_hajime.py            # dry run, shows what would change
  python rename_to_hajime.py --apply    # actually write the changes
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Folders we never descend into.
SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".obsidian",
    "node_modules",
    "venv",
    ".venv",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".pytest_cache",
    ".mypy_cache",
}

# File extensions we consider safe to read as text. Anything else is skipped.
# This is conservative on purpose — we'd rather skip a file we could have
# touched than corrupt a binary.
TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml",
    ".cfg", ".ini", ".html", ".css", ".js", ".jsx", ".ts", ".tsx",
    ".gitignore", ".gitattributes", ".env",
}

# Files with no extension that we still want to read (rare but possible).
TEXT_FILENAMES = {
    "README", "LICENSE", "Makefile", "Dockerfile",
    ".gitignore", ".gitattributes",
}

# The replacement rules. Order matters: do the longer/more-specific
# patterns first so they don't get partially eaten by later passes.
# Each rule is (regex_pattern, replacement_string, human_label).
# We use \b word boundaries to enforce whole-word matching, mirroring
# the "Match Whole Word" toggle in VS Code.
REPLACEMENTS = [
    # Wiki-link prefix replacements first (Step 10 work) — these are
    # technically subsumed by the bare-word replacements below, but
    # listing them explicitly makes the dry-run output more readable.
    (re.compile(r"\[\[hajime-"), "[[hajime-", "wiki-link [[hajime-* ]]"),

    # Then the three case-sensitive whole-word replacements (Steps 4-6).
    (re.compile(r"\bTachiwaza\b"), "Hajime",   "Hajime (capitalized)"),
    (re.compile(r"\btachiwaza\b"), "hajime",   "hajime (lowercase)"),
    (re.compile(r"\bTACHIWAZA\b"), "HAJIME",   "HAJIME (all caps)"),
]


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def is_text_file(path: Path) -> bool:
    """Return True if this looks like a file we should try to rewrite."""
    if path.name in TEXT_FILENAMES:
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return False


def iter_project_files(root: Path):
    """Yield every text file under root, skipping SKIP_DIRS."""
    for path in root.rglob("*"):
        # Skip if any parent directory is in SKIP_DIRS
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if not is_text_file(path):
            continue
        yield path


# ---------------------------------------------------------------------------
# Replacement engine
# ---------------------------------------------------------------------------

def process_file(path: Path, apply: bool) -> dict:
    """
    Process a single file. Returns a dict with replacement counts per rule
    and the new content. If apply=True, also writes the file.
    """
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Looked like a text file by extension but isn't valid UTF-8.
        # Skip it rather than risk corruption.
        return {"skipped": True, "reason": "not-utf8", "counts": {}, "new": None}

    new_content = original
    counts = {}
    for pattern, replacement, label in REPLACEMENTS:
        new_content, n = pattern.subn(replacement, new_content)
        if n > 0:
            counts[label] = n

    if not counts:
        return {"skipped": False, "counts": {}, "new": None}

    if apply and new_content != original:
        path.write_text(new_content, encoding="utf-8")

    return {"skipped": False, "counts": counts, "new": new_content}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Rename Hajime -> Hajime across all text files."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually write the changes. Without this flag, runs as a dry-run.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root to scan (defaults to current working directory).",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory.", file=sys.stderr)
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"=== Hajime rename: {mode} ===")
    print(f"Root: {root}")
    print()

    total_files_changed = 0
    total_replacements = 0
    skipped_non_utf8 = []

    for path in iter_project_files(root):
        result = process_file(path, args.apply)

        if result.get("skipped"):
            skipped_non_utf8.append(path)
            continue

        counts = result["counts"]
        if not counts:
            continue

        rel = path.relative_to(root)
        file_total = sum(counts.values())
        total_files_changed += 1
        total_replacements += file_total

        print(f"  {rel}")
        for label, n in counts.items():
            print(f"      {n:>4}  {label}")

    print()
    print(f"=== Summary ===")
    print(f"Files changed: {total_files_changed}")
    print(f"Total replacements: {total_replacements}")

    if skipped_non_utf8:
        print(f"Skipped (not valid UTF-8): {len(skipped_non_utf8)} file(s)")
        for path in skipped_non_utf8:
            print(f"  - {path.relative_to(root)}")

    print()
    if not args.apply:
        print("This was a DRY RUN. No files were modified.")
        print("Re-run with --apply to actually write the changes.")
    else:
        print("Changes written. Now:")
        print("  1. Run `python main.py` (or whatever your entrypoint is) to verify the code still works (Step 8).")
        print("  2. Spot-check existing 'hajime' (judo term) references from your Step 3 audit (Step 7).")
        print("  3. Move on to Step 9 (rename markdown files) in the rename doc.")


if __name__ == "__main__":
    main()
