#!/usr/bin/env python3
"""Add the word-by-word English glosses to quran.db (`word_glosses`).

These are the interlinear glosses of the Quranic Arabic Corpus — the same
project that supplies the morphology in `corpus`, which is why they align
exactly: 77,429 glosses for 77,429 written words, no orphans on either side.
Keyed on (surah, ayah, word), because a gloss covers a whole written word, not
a segment: 1:1:1 is bi- + ism together, glossed "In (the) name".

What this is and is not: a gloss is a reading aid for the morphology, chosen
to show what each Arabic word contributes to the sentence. It is deliberately
literal and often bracketed ("(of) Allah", "All praises and thanks"). It is
not a translation of the Quran, and reads poorly as one. Anything presented to
a reader as meaning should come from a translation proper.

Source: sources/word_glosses_en.tsv, normalised from the corpus word-by-word
data as redistributed in github.com/Abbas1997/QuranicMorphology
(Components/wordtranslations.js), keys unchanged. The Quranic Arabic Corpus is
GPL-licensed, as is the morphology already in this database.

Idempotent: drops and rebuilds the table.
"""

import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "sources" / "word_glosses_en.tsv"


def main():
    if not SRC.exists():
        sys.exit("ontbreekt: %s" % SRC)
    conn = sqlite3.connect(HERE / "quran.db")
    cur = conn.cursor()

    with SRC.open(encoding="utf-8") as f:
        rows = [(int(r["surah"]), int(r["ayah"]), int(r["word"]), r["gloss_en"])
                for r in csv.DictReader(f, delimiter="\t")]

    cur.execute("DROP TABLE IF EXISTS word_glosses")
    cur.execute("""CREATE TABLE word_glosses (
        surah INTEGER, ayah INTEGER, word INTEGER, gloss_en TEXT,
        PRIMARY KEY (surah, ayah, word))""")
    cur.executemany("INSERT INTO word_glosses VALUES (?,?,?,?)", rows)

    # A gloss that names no word in the corpus would be a silent misalignment,
    # so refuse to leave one behind rather than reporting a coverage number.
    orphans = cur.execute(
        "SELECT COUNT(*) FROM word_glosses g LEFT JOIN corpus c"
        " ON c.surah = g.surah AND c.ayah = g.ayah AND c.word = g.word"
        " WHERE c.id IS NULL").fetchone()[0]
    missing = cur.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT surah, ayah, word FROM corpus"
        " EXCEPT SELECT surah, ayah, word FROM word_glosses)").fetchone()[0]
    if orphans or missing:
        conn.rollback()
        sys.exit("misalignment: %d glossen zonder woord, %d woorden zonder glos"
                 % (orphans, missing))

    cur.execute("DROP VIEW IF EXISTS words_en")
    cur.execute("""CREATE VIEW words_en AS
        SELECT w.surah, w.ayah, w.word, w.word_ar, g.gloss_en
        FROM words w JOIN word_glosses g
          ON g.surah = w.surah AND g.ayah = w.ayah AND g.word = w.word""")
    conn.commit()

    n = cur.execute("SELECT COUNT(*) FROM word_glosses").fetchone()[0]
    distinct = cur.execute("SELECT COUNT(DISTINCT gloss_en) FROM word_glosses").fetchone()[0]
    print("word_glosses: %s rijen, %s verschillende glossen, 0 wezen" %
          (format(n, ","), format(distinct, ",")))
    conn.close()


if __name__ == "__main__":
    main()
