#!/usr/bin/env python3
"""Assign lemmas to the personal pronouns (dama'ir), which the corpus
leaves without one.

Every PRON segment is lemmatized to the canonical detached pronoun of its
person-gender-number cell (like lemmatizing "him"/"his" to "he"): detached
pronouns, possessive/object suffixes and verbal subject suffixes alike.
Detached segments carry PGN in the person/gender/number columns; attached
segments carry a combined code (e.g. 3MS, 2MP) in suffix_pron. Dual forms
make no gender distinction (2D/2MD/2FD -> antuma, 3D/3MD/3FD -> huma).

Lemma spellings follow the corpus' own conventions (dotless ya, no final
sukun, Buckwalter in `lemma`, Arabic in `lemma_ar`).

Idempotent: only fills PRON segments that still lack a lemma.
"""

import sqlite3
from pathlib import Path

# PGN code -> (lemma Buckwalter, lemma Arabic)
DAMAIR = {
    "1S": (">anaA", "أَنَا"),
    "1P": ("naHonu", "نَحْنُ"),
    "2MS": (">anta", "أَنتَ"),
    "2FS": (">anti", "أَنتِ"),
    "2D": (">antumaA", "أَنتُمَا"),
    "2MD": (">antumaA", "أَنتُمَا"),
    "2FD": (">antumaA", "أَنتُمَا"),
    "2MP": (">antum", "أَنتُم"),
    "2FP": (">antun~a", "أَنتُنَّ"),
    "3MS": ("huwa", "هُوَ"),
    "3FS": ("hiYa", "هِىَ"),
    "3D": ("humaA", "هُمَا"),
    "3MD": ("humaA", "هُمَا"),
    "3FD": ("humaA", "هُمَا"),
    "3MP": ("hum", "هُم"),
    "3FP": ("hun~a", "هُنَّ"),
}


def main():
    db = Path(__file__).parent / "quran.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    for code, (bw, ar) in DAMAIR.items():
        # Attached pronouns: PGN code in suffix_pron.
        cur.execute(
            "UPDATE corpus SET lemma=?, lemma_ar=? "
            "WHERE tag='PRON' AND (lemma IS NULL OR lemma='') AND suffix_pron=?",
            (bw, ar, code),
        )
        # Detached pronouns: PGN in separate columns (gender may be absent).
        person, rest = code[0], code[1:]
        gender = rest[:-1] or None
        number = rest[-1]
        cur.execute(
            "UPDATE corpus SET lemma=?, lemma_ar=? "
            "WHERE tag='PRON' AND (lemma IS NULL OR lemma='') "
            "AND person=? AND number=? AND IFNULL(gender,'')=?",
            (bw, ar, person, number, gender or ""),
        )
    conn.commit()

    cur.execute(
        "SELECT COUNT(*) FROM corpus WHERE tag='PRON' AND (lemma IS NULL OR lemma='')"
    )
    print("PRON segments still without lemma:", cur.fetchone()[0])
    for lemma_ar, count in cur.execute(
        "SELECT lemma_ar, COUNT(*) FROM corpus WHERE tag='PRON' "
        "AND lemma IN (%s) GROUP BY lemma_ar ORDER BY 2 DESC"
        % ",".join("?" * len(DAMAIR)),
        [bw for bw, _ in DAMAIR.values()],
    ):
        print(f"{lemma_ar}: {count}")
    conn.close()


if __name__ == "__main__":
    main()
