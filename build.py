#!/usr/bin/env python3
"""Run the whole pipeline in order, from the raw corpus TSV to the finished
quran.db, so the order does not have to live in anyone's head.

The steps fall into three groups: the corpus migrations that build and enrich
the `corpus` table, the parsers that turn the classical wujuh works
(Yahya ibn Sallam, al-Damaghani, Ibn al-Jawzi, al-Askari) into JSON plus the
citation resolver, and the steps that build and check the derived tables. Each
step is an ordinary standalone script; build.py only runs them as subprocesses
with the same interpreter and stops at the first failure.

Every step except to_sqlite.py is idempotent, which is what --keep exploits:
it re-runs the migrations over the committed quran.db instead of rebuilding
the corpus table from the TSV.

A full rebuild cannot simply delete quran.db first (to_sqlite.py inserts
rather than replaces): a checkout missing one script would then be left with
no database at all. Two things prevent that. First, every planned step and the
source files it reads are checked before anything is touched, so a build that
cannot finish never starts. Second, the existing quran.db is moved aside to
quran.db.tmp for the duration of the build and only deleted once the last step
has succeeded; any failure — a failing script, Ctrl-C, an exception — moves it
back and keeps the half-finished database as quran.db.bak, so no build can
cost more than the time it ran. Both names are the ones .gitignore already
covers, so a stray one cannot be committed by accident.

--keep runs edit the existing quran.db in place, as they always have; that
file is committed, so `git checkout quran.db` undoes a half-applied migration.

Steps marked optional may legitimately be absent from a checkout; they are
reported as skipped instead of failing the build.

  python3 build.py                     full rebuild from the TSV
  python3 build.py --keep              keep quran.db, re-run the migrations
  python3 build.py --from add_wujuh.py restart at a step (the parsers are slow)
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "quran.db"
BACKUP = HERE / "quran.db.tmp"   # the previous db, parked while a rebuild runs
FAILED = HERE / "quran.db.bak"   # the half-built db, kept after a failure

# (script, required, inputs). The optional ones are recent additions that a
# given checkout may not have yet; missing them costs annotations, not a
# database. `inputs` names the committed source files a step reads, relative
# to the repo root, so that a missing source is caught before the build starts
# rather than halfway through. Files another step writes earlier in the same
# run (the parsed *_wujuh.json, resolved_citations.json) are deliberately not
# listed: they need not exist yet when the build begins.
STEPS = [
    ("to_sqlite.py", True, ("quranic-corpus-arabic.tsv",)),
    ("add_kalima_type.py", True, ()),
    ("add_damair_lemmas.py", True, ()),
    ("add_wazifa.py", True, ()),
    ("add_metadata.py", False, ()),
    ("add_translation.py", False, ("sources/word_glosses_en.tsv",)),
    ("parse_tasarif.py", True, ("sources/tasarif.txt",)),
    ("parse_damaghani.py", True, ("sources/damaghani_qamus.txt",)),
    ("parse_ibnjawzi.py", True, ("sources/ibnjawzi_nuzhat.txt",)),
    # al-Askari's Wujuh wa-l-naza'ir is the newest work in the set; the parser
    # checks for its own source text and reports what it needs, so no input is
    # declared here.
    ("parse_askari.py", False, ()),
    ("parse_irab.py", False, ("sources/nahhas_irab.txt",)),
    ("parse_treebank.py", False, ("sources/treebank_eqtb.tsv.gz",)),
    ("compare_riwayat.py", False, ("sources/riwaya_hafs.csv",
                                   "sources/riwaya_warsh.csv")),
    ("resolve_citations.py", True, ()),
    ("substantiate_jk.py", True, ("sources/ibnjawzi_nuzhat_jk.txt",)),
    ("add_wujuh.py", True, ()),
    ("align_senses.py", False, ()),
    ("validate.py", False, ()),
]

NAMES = [name for name, _, _ in STEPS]


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


def mb(path):
    return f"{path.stat().st_size / 1e6:.1f} MB"


class StepFailed(Exception):
    """A step exited non-zero; carries what the resume hint needs."""

    def __init__(self, name, returncode, elapsed):
        super().__init__(name)
        self.name = name
        self.returncode = returncode
        self.elapsed = elapsed


def preflight(planned):
    """Check every planned step before the database is touched.

    Returns (runnable, skipped) with the steps that will actually run and the
    optional ones that are absent, or exits with everything that is wrong at
    once — listing all problems beats fixing them one build at a time.
    """
    runnable, skipped, problems = [], [], []
    for name, required, inputs in planned:
        if not (HERE / name).exists():
            if required:
                problems.append(f"required step {name} is missing")
            else:
                skipped.append((name, "not present in this checkout"))
            continue
        missing = [src for src in inputs if not (HERE / src).exists()]
        if missing:
            what = ", ".join(missing)
            if required:
                problems.append(f"{name} needs {what}, which is missing")
            else:
                skipped.append((name, f"source data missing: {what}"))
            continue
        runnable.append(name)

    if problems:
        sys.exit("build not started, nothing was changed:\n  "
                 + "\n  ".join(problems))
    return runnable, skipped


def run_step(name, nr, total):
    """Run one script; return its elapsed time or raise StepFailed."""
    print(f"\n[{nr}/{total}] {name}")
    print("-" * 60)
    started = time.time()
    result = subprocess.run([sys.executable, str(HERE / name)], cwd=str(HERE))
    elapsed = time.time() - started
    if result.returncode != 0:
        print("-" * 60)
        raise StepFailed(name, result.returncode, elapsed)
    print("-" * 60)
    print(f"ok ({fmt_time(elapsed)})")
    return elapsed


def recover_leftovers():
    """Clean up after a build that was killed before it could restore itself.

    Only a SIGKILL or a crashed machine can get here: every ordinary failure
    path restores the database itself.
    """
    if not BACKUP.exists():
        return
    if DB.exists():
        BACKUP.unlink()
        print(f"removed a stale {BACKUP.name} left by an interrupted build")
    else:
        os.replace(BACKUP, DB)
        print(f"restored {DB.name} ({mb(DB)}) from {BACKUP.name}, "
              "left by an interrupted build")


def table_count(cur, table):
    try:
        return cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return None


def report_counts():
    """Print the row counts of the two main tables, if there is a db to ask."""
    if not DB.exists():
        print("corpus: no database | wujuh: no database")
        return
    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    corpus = table_count(cur, "corpus")
    wujuh = table_count(cur, "wujuh")
    con.close()
    print(f"corpus: {corpus:,} rows | " if corpus is not None
          else "corpus: table missing | ", end="")
    print(f"wujuh: {wujuh:,} rows" if wujuh is not None
          else "wujuh: table missing")


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
        for i, (name, required, _) in enumerate(STEPS, 1):
            print(f"{i:2}. {name}" + ("" if required else "   (optional)"))
        return

    start = step_index(args.start) if args.start else 0
    planned = STEPS[start:]
    if args.keep:
        planned = [step for step in planned if step[0] != "to_sqlite.py"]

    rebuilding = any(name == "to_sqlite.py" for name, _, _ in planned)
    recover_leftovers()
    if not rebuilding and not DB.exists():
        sys.exit(f"{DB.name} does not exist, so there is nothing to keep; "
                 "run a full build without --keep")

    # Everything that can be checked is checked here, while the database on
    # disk is still the one the user had.
    runnable, skipped = preflight(planned)
    if not runnable:
        sys.exit("build not started: no step in this run can be executed")

    if rebuilding and DB.exists():
        os.replace(DB, BACKUP)
        print(f"moved existing {DB.name} ({mb(BACKUP)}) aside to "
              f"{BACKUP.name}; it comes back if the build fails")
    elif not rebuilding:
        why = "--keep" if args.keep else "run starts after to_sqlite.py"
        print(f"keeping existing {DB.name} ({mb(DB)}, {why})")

    total = len(planned)
    why_skipped = dict(skipped)
    started = time.time()
    ran = 0
    current = None
    # BaseException so that Ctrl-C restores the database too; the handler ends
    # in sys.exit(1), so nothing is swallowed.
    try:
        for nr, (name, _, _) in enumerate(planned, 1):
            if name in why_skipped:
                print(f"\n[{nr}/{total}] {name}\n"
                      f"skipped: {why_skipped[name]} (optional step)")
                continue
            current = name
            run_step(name, nr, total)
            ran += 1
    except BaseException as exc:
        restored = False
        if rebuilding and BACKUP.exists():
            if DB.exists():
                os.replace(DB, FAILED)
            os.replace(BACKUP, DB)
            restored = True
        if isinstance(exc, StepFailed):
            print(f"FAILED: {exc.name} exited with code {exc.returncode} "
                  f"after {fmt_time(exc.elapsed)}")
            resume = exc.name
        elif isinstance(exc, KeyboardInterrupt):
            print(f"\ninterrupted during {current}")
            resume = current
        else:
            print(f"FAILED: {type(exc).__name__}: {exc}")
            resume = current
        if restored:
            print(f"restored the previous {DB.name} ({mb(DB)}); the "
                  f"half-built database is kept as {FAILED.name}")
            print("rebuild from scratch with:\n  python3 build.py")
            if resume:
                print("or resume the half-built database where it stopped:\n"
                      f"  mv {FAILED.name} {DB.name} && "
                      f"python3 build.py --keep --from {resume}")
        elif resume:
            print(f"resume with: python3 build.py --keep --from {resume}")
        sys.exit(1)

    elapsed = time.time() - started
    if BACKUP.exists():
        BACKUP.unlink()

    print("\n" + "=" * 60)
    print(f"build ok: {ran} step{'' if ran == 1 else 's'} run "
          f"in {fmt_time(elapsed)}")
    if skipped:
        print("skipped: " + ", ".join(f"{n} ({r})" for n, r in skipped))
    report_counts()


if __name__ == "__main__":
    main()
