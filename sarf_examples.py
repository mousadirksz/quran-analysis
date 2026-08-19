#!/usr/bin/env python3
"""Generate the paradigm tables for docs/sarf-nl.md from the Quran itself.

For each of the eight root types the sarf distinguishes -- salim, mahmuz,
mudaccaf, mithal, ajwaf, naqis, lafif mafruq, lafif maqrun -- this picks the
best-attested roots and prints, for each, the forms the Quran actually attests
across the fourteen persons, with a verse reference for each.

The point of teaching from attested forms is that the gaps are informative
too: no root is conjugated through the whole paradigm in the text, and which
cells are filled says something about how the Quran speaks.

    python3 sarf_examples.py            # all types
    python3 sarf_examples.py ajwaf      # one type
    python3 sarf_examples.py --markdown # tables ready for the textbook

Classification uses the corpus' own root letters. Note that the corpus writes
every hamza in a root as alif, so a root counts as mahmuz when it carries an
alif in a position where the weak-letter analysis does not explain it.
"""

import sqlite3
import sys
from pathlib import Path

from add_metadata import repair_markers

DB = Path(__file__).parent / "quran.db"

# traditional order of the fourteen persons
PGN_ORDER = ["3MS", "3FS", "3MD", "3FD", "3MP", "3FP",
             "2MS", "2FS", "2D", "2MD", "2FD", "2MP", "2FP", "1S", "1P"]
PGN_NL = {
    "3MS": "hij", "3FS": "zij (v. enk.)", "3MD": "zij tweeën (m.)",
    "3FD": "zij tweeën (v.)", "3MP": "zij (m. mv.)", "3FP": "zij (v. mv.)",
    "2MS": "jij (m.)", "2FS": "jij (v.)", "2D": "jullie tweeën",
    "2MD": "jullie tweeën (m.)", "2FD": "jullie tweeën (v.)",
    "2MP": "jullie (m.)", "2FP": "jullie (v.)", "1S": "ik", "1P": "wij",
}

TYPES = ["salim", "mahmuz", "mudaccaf", "mithal", "ajwaf", "naqis",
         "lafif mafruq", "lafif maqrun"]

TYPE_NL = {
    "salim": "Sālim — gaaf",
    "mahmuz": "Mahmūz — met hamza",
    "mudaccaf": "Muḍaʿʿaf — verdubbeld",
    "mithal": "Mithāl — eerste letter zwak",
    "ajwaf": "Ajwaf — tweede letter zwak",
    "naqis": "Nāqiṣ — derde letter zwak",
    "lafif mafruq": "Lafīf mafrūq — eerste en derde zwak",
    "lafif maqrun": "Lafīf maqrūn — tweede en derde zwak",
}


def classify(root):
    """Assign a three-letter root to its sarf type."""
    if len(root) != 3:
        return None
    f, a, l = root
    weak = [i for i, ch in enumerate(root) if ch in "وي"]
    hamza = [i for i, ch in enumerate(root) if ch == "ا"]
    if f == a or a == l:
        return "mudaccaf"
    if len(weak) >= 2:
        return "lafif maqrun" if weak == [1, 2] else "lafif mafruq"
    if weak == [0]:
        return "mithal"
    if weak == [1]:
        return "ajwaf"
    if weak == [2]:
        return "naqis"
    if hamza:
        return "mahmuz"
    return "salim"


def roots_by_type(cur):
    out = {t: [] for t in TYPES}
    for root, n in cur.execute(
            "SELECT root_ar, COUNT(*) n FROM corpus WHERE pos='V' AND root_ar != ''"
            " AND LENGTH(root_ar)=3 GROUP BY root_ar ORDER BY n DESC"):
        t = classify(root)
        if t:
            out[t].append((root, n))
    return out


def paradigm(cur, root, form=None):
    """The form-I active forms this root is attested in, per person and aspect.

    verb_form is null for the bare form in this corpus, so that filter is what
    keeps the derived patterns out of a table meant to teach the bare one."""
    # The corpus stores a verb stem separately from its ending, so the stem
    # alone reads as qalu rather than qalu-w-a. Join the whole written word
    # back together, and prefer an occurrence that carries no prefix, so the
    # learner sees the bare form rather than wa-qala.
    rows = cur.execute(
        "SELECT v.aspect, v.person || IFNULL(v.gender,'') || v.number AS pgn,"
        " w.word_ar, v.surah, v.ayah,"
        " (SELECT COUNT(*) FROM corpus p WHERE p.surah=v.surah AND p.ayah=v.ayah"
        "   AND p.word=v.word AND p.segment_type='PREFIX') AS prefixes"
        " FROM corpus v JOIN words w"
        "   ON w.surah=v.surah AND w.ayah=v.ayah AND w.word=v.word"
        " WHERE v.root_ar = ? AND v.pos='V' AND v.person != ''"
        " AND IFNULL(v.voice,'ACT') = 'ACT'"
        + (" AND v.verb_form IS NULL" if form is None else " AND v.verb_form = ?") +
        " ORDER BY prefixes, v.surah, v.ayah",
        (root,) if form is None else (root, form)).fetchall()
    best = {}
    for aspect, pgn, form, s, a, prefixes in rows:
        key = (aspect, pgn)
        if key not in best:  # unprefixed occurrences come first
            best[key] = (repair_markers(form), f"{s}:{a}", prefixes)
    return best


def lemma_of(cur, root, form=None):
    sql = ("SELECT lemma_ar FROM corpus WHERE root_ar=? AND pos='V' AND lemma_ar != ''"
           + (" AND verb_form IS NULL" if form is None else " AND verb_form = ?")
           + " GROUP BY lemma_ar ORDER BY COUNT(*) DESC LIMIT 1")
    r = cur.execute(sql, (root,) if form is None else (root, form)).fetchone()
    return r[0] if r else "—"


def busiest_form(cur, root):
    """The derived pattern this root is most attested in, for roots whose bare
    form the Quran barely uses."""
    r = cur.execute(
        "SELECT verb_form FROM corpus WHERE root_ar=? AND pos='V'"
        " AND verb_form IS NOT NULL AND person != ''"
        " GROUP BY verb_form ORDER BY COUNT(*) DESC LIMIT 1", (root,)).fetchone()
    return r[0] if r else None


def show(cur, t, roots, markdown, per_type=2):
    title = TYPE_NL[t]
    print(("\n### " + title) if markdown else ("\n" + "=" * 62 + "\n" + title))
    shown = 0
    for root, total in roots:
        par, form = paradigm(cur, root), None
        if len(par) < 5:
            # For the lafif types the Quran barely attests the bare form. The
            # weak-letter behaviour shows just as well in a derived pattern, so
            # fall back to the one this root is most used in -- a single
            # pattern, so the table stays one paradigm rather than a mixture.
            form = busiest_form(cur, root)
            if form:
                par = paradigm(cur, root, form)
        if len(par) < 4:
            continue
        lemma = lemma_of(cur, root, form)
        cells = sum(1 for _ in par)
        if markdown:
            note = f" · vorm {form}" if form else ""
            print(f"\n**{root}** — {lemma} · {total}× in de Quran, "
                  f"{cells} cellen geattesteerd{note}\n")
            print("| Persoon | Māḍī | Vers | Muḍāriʿ | Vers | Amr | Vers |")
            print("|---|---|---|---|---|---|---|")
        else:
            print(f"\n  {root}  ({lemma})  {total}x, {cells} cellen"
                  + (f", vorm {form}" if form else ""))
        for pgn in PGN_ORDER:
            perf = par.get(("PERF", pgn))
            impf = par.get(("IMPF", pgn))
            impv = par.get(("IMPV", pgn))
            if not (perf or impf or impv):
                continue
            cell = lambda x, i: (x[i] if x else ("—" if i == 0 else ""))
            if markdown:
                print(f"| {PGN_NL[pgn]} | {cell(perf,0)} | {cell(perf,1)}"
                      f" | {cell(impf,0)} | {cell(impf,1)}"
                      f" | {cell(impv,0)} | {cell(impv,1)} |")
            else:
                print(f"    {PGN_NL[pgn]:<18} {cell(perf,0):<14}"
                      f" {cell(impf,0):<14} {cell(impv,0)}")
        shown += 1
        if shown >= per_type:
            break


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    markdown = "--markdown" in sys.argv
    cur = sqlite3.connect(DB).cursor()
    by_type = roots_by_type(cur)
    wanted = args or TYPES
    for t in wanted:
        if t not in TYPES:
            sys.exit("onbekend type: %s (kies uit %s)" % (t, ", ".join(TYPES)))
        show(cur, t, by_type[t], markdown)


if __name__ == "__main__":
    main()
