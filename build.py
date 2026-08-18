#!/usr/bin/env python3
"""Run the whole pipeline in order, from the raw corpus TSV to the finished
quran.db, so the order does not have to live in anyone's head.

The steps fall into three groups: the corpus migrations that build and enrich
the `corpus` table, the parsers that turn the three classical wujuh works
(Yahya ibn Sallam, al-Damaghani, Ibn al-Jawzi) into JSON plus the citation
resolver, and the steps that build and check the derived tables. Each step is
an ordinary standalone script; build.py only runs them as subprocesses with
the same interpreter and stops at the first failure.

Every step except to_sqlite.py is idempotent, which is what --keep exploits:
it re-runs the migrations over the committed quran.db instead of rebuilding
the corpus table from the TSV. A full build deletes quran.db first, because
to_sqlite.py inserts rather than replaces.

Steps marked optional may legitimately be absent from a checkout; they are
reported as skipped instead of failing the build.

  python3 build.py                     full rebuild from the TSV
  python3 build.py --keep              keep quran.db, re-run the migrations
  python3 build.py --from add_wujuh.py restart at a step (the parsers are slow)
"""

import argparse
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "quran.db"

# (script, required). The optional ones are recent additions that a given
# checkout may not have yet; missing them costs annotations, not a database.
STEPS = [
    ("to_sqlite.py", True),
    ("add_kalima_type.py", True),
    ("add_damair_lemmas.py", True),
    ("add_wazifa.py", True),
    ("add_metadata.py", False),
    ("parse_tasarif.py", True),
    ("parse_damaghani.py", True),
    ("parse_ibnjawzi.py", True),
    ("resolve_citations.py", True),
    ("substantiate_jk.py", True),
    ("add_wujuh.py", True),
    ("align_senses.py", False),
    ("validate.py", False),
]

NAMES = [name for name, _ in STEPS]


def step_index(wanted):
    """Resolve a --from value to a step index, with or without the .py."""
    name = wanted if wanted.endswith(".py") else wanted + ".py"
    if name not in NAMES:
        sys.exit(f"unknown step: {wanted}\nknown steps: " + ", ".join(NAMES))
    return NAMES.index(name)


def fmt_time(seconds):
    if seconds < 90:
        return f"{seconds:.1f}s"
    return f"{seconds / 60:.1f} min ({seconds:.0f}s)"


def run_step(name, nr, total):
    """Run one script; return its elapsed time or exit the build on failure."""
    print(f"\n[{nr}/{total}] {name}")
    print("-" * 60)
    started = time.time()
    result = subprocess.run([sys.executable, str(HERE / name)], cwd=str(HERE))
    elapsed = time.time() - started
    if result.returncode != 0:
        print("-" * 60)
        sys.exit(f"FAILED: {name} exited with code {result.returncode} "
                 f"after {fmt_time(elapsed)}\nfix it and resume with: "
                 f"python3 build.py --keep --from {name}")
    print("-" * 60)
    print(f"ok ({fmt_time(elapsed)})")
    return elapsed


def table_count(cur, table):
    try:
        return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return None


def main():
    ap = argparse.ArgumentParser(
        description="Build quran.db by running the pipeline in order.")
    ap.add_argument("--from", dest="start", metavar="SCRIPT",
                    help="restart at this step instead of the first one")
    ap.add_argument("--keep", action="store_true",
                    help="keep the existing quran.db instead of rebuilding "
                         "the corpus table from the TSV")
    ap.add_argument("--list", action="store_true",
                    help="print the pipeline order and exit")
    args = ap.parse_args()

    if args.list:
        for i, (name, required) in enumerate(STEPS, 1):
            print(f"{i:2}. {name}" + ("" if required else "   (optional)"))
        return

    start = step_index(args.start) if args.start else 0
    planned = STEPS[start:]
    if args.keep:
        planned = [(n, r) for n, r in planned if n != "to_sqlite.py"]

    rebuilding = any(name == "to_sqlite.py" for name, _ in planned)
    if rebuilding and DB.exists():
        DB.unlink()
        print(f"removed existing {DB.name} (full rebuild from the TSV)")
    elif not rebuilding:
        if not DB.exists():
            sys.exit(f"{DB.name} does not exist, so there is nothing to keep; "
                     "run a full build without --keep")
        why = "--keep" if args.keep else "run starts after to_sqlite.py"
        print(f"keeping existing {DB.name} "
              f"({DB.stat().st_size / 1e6:.1f} MB, {why})")

    total = len(planned)
    started = time.time()
    ran, skipped = 0, []
    for nr, (name, required) in enumerate(planned, 1):
        if not (HERE / name).exists():
            if required:
                sys.exit(f"FAILED: required step {name} is missing from "
                         f"{HERE}")
            print(f"\n[{nr}/{total}] {name}\nskipped: not present in this "
                  "checkout (optional step)")
            skipped.append(name)
            continue
        run_step(name, nr, total)
        ran += 1
    elapsed = time.time() - started

    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    corpus = table_count(cur, "corpus")
    wujuh = table_count(cur, "wujuh")
    con.close()

    print("\n" + "=" * 60)
    print(f"build ok: {ran} step{'' if ran == 1 else 's'} run "
          f"in {fmt_time(elapsed)}")
    if skipped:
        print("skipped (not present): " + ", ".join(skipped))
    print(f"corpus: {corpus:,} rows | " if corpus is not None
          else "corpus: table missing | ", end="")
    print(f"wujuh: {wujuh:,} rows" if wujuh is not None
          else "wujuh: table missing")


if __name__ == "__main__":
    main()
