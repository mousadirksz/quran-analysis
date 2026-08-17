#!/usr/bin/env python3
"""Build the `wujuh` table in quran.db from the two parsed classical works
(al-Damaghani's Qamus, Ibn al-Jawzi's Nuzhat al-Acyun) and their resolved
citations.

One row per resolved citation: (work, headword, root, sense_nr, gloss,
surah, ayah), so polysemy queries like "which wujuh does huda have, and
which verse attests which sense" run directly against the database.

The entry's root is inferred from the data itself: among the roots of the
verses the entry cites, take the one that occurs in the most cited verses
AND whose letters are compatible with the headword. This works uniformly
for al-Damaghani's spaced root letters ("أت ى") and Ibn al-Jawzi's whole
words ("الأذان").

Idempotent: drops and rebuilds the table. Requires resolved_citations.json
(from resolve_citations.py).
"""

import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent


def norm_letters(s):
    s = re.sub("[آأإٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و").replace("ء", "ا")
    s = s.replace("ة", "").replace("ال", "", 1) if s.startswith("ال") else s
    return re.sub(r"[^ء-ي]", "", s)


def strong(s):
    return frozenset(s) - frozenset("اوي")


def compatible(root_n, head_n, spaced):
    """al-Damaghani's spaced-root headwords must match the root's strong
    letters exactly; Ibn al-Jawzi's whole-word headwords (derived forms like
    الاستطاعة) only need to contain them."""
    if spaced:
        return strong(root_n) == strong(head_n)
    missing = 0
    for ch in root_n:
        if ch not in head_n:
            if ch in "اوي":  # weak letters morph freely
                missing += 1
            else:
                return False
    return missing <= 1


def infer_root(head, verse_refs, verse_roots):
    head_n = norm_letters(head)
    spaced = " " in head.strip()
    counts = Counter()
    for ref in verse_refs:
        for r in verse_roots.get(ref, ()):
            counts[r] += 1
    for root, n in counts.most_common(40):
        if compatible(norm_letters(root), head_n, spaced):
            return root, n / len(verse_refs)
    # fallback for typo'd headwords: a root shared by most cited verses is
    # almost certainly the entry's subject
    if counts:
        root, n = counts.most_common(1)[0]
        if n / len(verse_refs) >= 0.6 and len(verse_refs) >= 3:
            return root, n / len(verse_refs)
    return None, 0.0


def main():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()
    cur.execute("SELECT surah, ayah, root_ar FROM corpus WHERE root_ar!=''")
    verse_roots = {}
    for s, a, r in cur.fetchall():
        verse_roots.setdefault((s, a), set()).add(r)

    resolved = json.loads((HERE / "sources" / "resolved_citations.json")
                          .read_text(encoding="utf-8"))

    cur.execute("DROP TABLE IF EXISTS wujuh")
    cur.execute("""CREATE TABLE wujuh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work TEXT, headword TEXT, root_ar TEXT,
        sense_nr INTEGER, gloss TEXT,
        quote TEXT, surah INTEGER, ayah INTEGER, match_status TEXT)""")

    n_rows = 0
    entries_with_root = 0
    n_entries = 0
    for work, entries in resolved.items():
        for e in entries:
            refs = []
            for sense in e["senses"]:
                for q in sense["quotes"]:
                    if q["status"] in ("unique", "hint_resolved"):
                        refs += [tuple(map(int, r.split(":"))) for r in q["refs"]]
            if not refs:
                continue
            n_entries += 1
            root, cov = infer_root(e["headword"], refs, verse_roots)
            if root:
                entries_with_root += 1
            for sense in e["senses"]:
                for q in sense["quotes"]:
                    if q["status"] not in ("unique", "hint_resolved"):
                        continue
                    for ref in q["refs"]:
                        s, a = map(int, ref.split(":"))
                        cur.execute(
                            "INSERT INTO wujuh (work, headword, root_ar, sense_nr,"
                            " gloss, quote, surah, ayah, match_status)"
                            " VALUES (?,?,?,?,?,?,?,?,?)",
                            (work, e["headword"], root, sense["nr"],
                             sense["gloss"], q["quote"], s, a, q["status"]))
                        n_rows += 1

    cur.execute("CREATE INDEX IF NOT EXISTS idx_wujuh_root ON wujuh(root_ar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wujuh_verse ON wujuh(surah, ayah)")
    con.commit()
    print(f"entries with resolved citations: {n_entries}, "
          f"root inferred: {entries_with_root}")
    print(f"wujuh rows (citation-level): {n_rows}")
    cur.execute("SELECT COUNT(DISTINCT root_ar) FROM wujuh WHERE root_ar IS NOT NULL")
    print("distinct roots covered:", cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
