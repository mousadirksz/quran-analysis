#!/usr/bin/env python3
"""Add a `kalima_type` column to the corpus table: the classical (nahw)
classification of each segment as ism, fiil or harf.

The corpus POS tags mostly map directly onto the classical three-way split,
but the corpus tags interrogative/conditional words (INTG/COND) as particles,
while classical grammar treats several of them as asma' (asma' al-istifham
and asma' al-shart). Those are corrected here per lemma. The muqatta'at
(surah-initial letter sequences, tag INL) fit none of the three classes and
get their own value.

Idempotent: safe to run again after rebuilding quran.db with to_sqlite.py.
"""

import sqlite3
from pathlib import Path

# Tags whose segments are asma' in classical grammar. T and LOC are the
# zuruf (adverbs of time/place), which are asma'.
ISM_TAGS = ("N", "PN", "ADJ", "IMPN", "PRON", "DEM", "REL", "T", "LOC")
FIIL_TAGS = ("V",)
MUQATTAAT_TAGS = ("INL",)

# (lemma, tag) pairs the corpus tags as particles but classical grammar
# considers asma': interrogative and conditional nouns, the zarf haythu,
# and the relative alladhi when used conditionally. NEG/PREV/SUB/SUP uses
# of e.g. "maA" remain huruf and are deliberately not listed.
ISM_OVERRIDES = [
    ("maA", "INTG"), ("maA", "COND"),          # maa (istifham / shart)
    ("man", "INTG"), ("man", "COND"),          # man
    ("kayof", "INTG"),                         # kayfa
    (">ayon", "INTG"), (">ayon", "COND"),      # ayna
    ("mataY`", "INTG"),                        # mataa
    (">an~aY`", "INTG"),                       # annaa
    ("kam", "INTG"),                           # kam
    ("maA*aA", "INTG"),                        # maadhaa
    (">aY~", "INTG"), (">aY~", "COND"),        # ayy
    (">ay~aAn", "INTG"),                       # ayyaana
    ("mahomaA", "COND"),                       # mahmaa
    ("Hayov2", "COND"),                        # haythu (zarf)
    ("{l~a*iY", "COND"),                       # alladhi (ism mawsul)
    ("<i*aA", "COND"),                         # idhaa shartiyya (zarf)
]


def main():
    db = Path(__file__).parent / "quran.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(corpus)")]
    if "kalima_type" not in cols:
        cur.execute("ALTER TABLE corpus ADD COLUMN kalima_type TEXT")

    def tag_in(tags):
        return "tag IN (%s)" % ",".join("?" * len(tags))

    cur.execute(f"UPDATE corpus SET kalima_type='ism' WHERE {tag_in(ISM_TAGS)}", ISM_TAGS)
    cur.execute(f"UPDATE corpus SET kalima_type='fiil' WHERE {tag_in(FIIL_TAGS)}", FIIL_TAGS)
    cur.execute(f"UPDATE corpus SET kalima_type='muqattaat' WHERE {tag_in(MUQATTAAT_TAGS)}", MUQATTAAT_TAGS)
    cur.execute(
        "UPDATE corpus SET kalima_type='harf' WHERE kalima_type IS NULL "
        f"OR NOT ({tag_in(ISM_TAGS + FIIL_TAGS + MUQATTAAT_TAGS)})",
        ISM_TAGS + FIIL_TAGS + MUQATTAAT_TAGS,
    )
    for lemma, tag in ISM_OVERRIDES:
        cur.execute(
            "UPDATE corpus SET kalima_type='ism' WHERE lemma=? AND tag=?",
            (lemma, tag),
        )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_kalima_type ON corpus(kalima_type)")
    conn.commit()

    for kalima_type, count in cur.execute(
        "SELECT kalima_type, COUNT(*) FROM corpus GROUP BY kalima_type ORDER BY 2 DESC"
    ):
        print(f"{kalima_type}: {count}")
    conn.close()


if __name__ == "__main__":
    main()
