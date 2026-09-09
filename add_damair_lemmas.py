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
sukun, Buckwalter in `lemma`, Arabic in `lemma_ar`), and the Arabic is produced
by convert.buckwalter_to_arabic rather than typed, so the combining marks come
out in the same order as everywhere else in the table.

Idempotent: only fills PRON segments that still lack a lemma.
"""

import sqlite3
from pathlib import Path

import convert

# PGN code -> lemma in Buckwalter. The Arabic is derived with the same
# converter the rest of the corpus went through, not typed beside it: the two
# hand-typed shadda forms (hun~a, >antun~a) had drifted to vowel-before-shadda,
# the opposite order of every other lemma in the table, so `WHERE lemma_ar =
# 'هُنَّ'` spelled the way the database spells it everywhere else found nothing.
DAMAIR_BW = {
    "1S": ">anaA",
    "1P": "naHonu",
    "2MS": ">anta",
    "2FS": ">anti",
    "2D": ">antumaA",
    "2MD": ">antumaA",
    "2FD": ">antumaA",
    "2MP": ">antum",
    "2FP": ">antun~a",
    "3MS": "huwa",
    "3FS": "hiYa",
    "3D": "humaA",
    "3MD": "humaA",
    "3FD": "humaA",
    "3MP": "hum",
    "3FP": "hun~a",
}


def main():
    db = Path(__file__).parent / "quran.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    for code, bw in DAMAIR_BW.items():
        ar = convert.buckwalter_to_arabic(bw)
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
