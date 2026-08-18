#!/usr/bin/env python3
"""Export the Quranic corpus TSV to a SQLite database with useful indexes.

The corpus is segment-level: a written word such as `wa-bi-l-kitabi` occupies
several rows (prefix, stem, suffix). The `words` and `ayat` views put those
segments back together so that word- and verse-level queries do not have to
re-implement the concatenation each time.

Both views concatenate over an ordered subquery instead of using the
`GROUP_CONCAT(... ORDER BY ...)` syntax: SQLite only accepts that form from
3.44 on, and quran.db is meant to open in older clients too. SQLite may not
flatten a subquery that carries an ORDER BY into an aggregating outer query,
so the segments reach GROUP_CONCAT in segment order.
"""

import sqlite3
import csv
from pathlib import Path

def main():
    src = Path(__file__).parent / "quranic-corpus-arabic.tsv"
    dst = Path(__file__).parent / "quran.db"

    conn = sqlite3.connect(str(dst))
    cur = conn.cursor()

    # Main table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surah INTEGER, ayah INTEGER, word INTEGER, segment INTEGER,
            form_bw TEXT, form_ar TEXT, tag TEXT,
            segment_type TEXT, pos TEXT,
            lemma TEXT, lemma_ar TEXT,
            root TEXT, root_ar TEXT,
            aspect TEXT, verb_form TEXT, voice TEXT, derivation TEXT,
            person TEXT, gender TEXT, number TEXT,
            "case" TEXT, mood TEXT, state TEXT,
            prefix TEXT, suffix_pron TEXT, special TEXT
        )
    """)

    # Read TSV and insert
    with open(src, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        rows = []
        for row in reader:
            rows.append((
                int(row["surah"]), int(row["ayah"]), int(row["word"]), int(row["segment"]),
                row["form_bw"], row["form_ar"], row["tag"],
                row["segment_type"] or None, row["pos"] or None,
                row["lemma"] or None, row["lemma_ar"] or None,
                row["root"] or None, row["root_ar"] or None,
                row["aspect"] or None, row["verb_form"] or None,
                row["voice"] or None, row["derivation"] or None,
                row["person"] or None, row["gender"] or None, row["number"] or None,
                row["case"] or None, row["mood"] or None, row["state"] or None,
                row["prefix"] or None, row["suffix_pron"] or None, row["special"] or None,
            ))

    cur.executemany("""
        INSERT INTO corpus (
            surah, ayah, word, segment,
            form_bw, form_ar, tag,
            segment_type, pos,
            lemma, lemma_ar, root, root_ar,
            aspect, verb_form, voice, derivation,
            person, gender, number,
            "case", mood, state,
            prefix, suffix_pron, special
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)

    # Indexes for fast queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_surah_ayah ON corpus(surah, ayah)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_root ON corpus(root)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_root_ar ON corpus(root_ar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lemma ON corpus(lemma)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lemma_ar ON corpus(lemma_ar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pos ON corpus(pos)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tag ON corpus(tag)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_aspect ON corpus(aspect)")

    # The views are dropped first so that a re-run replaces an older, possibly
    # wrong definition; CREATE VIEW IF NOT EXISTS would silently keep it.
    # View: one row per written word, its segments concatenated in segment
    # order. Without the GROUP BY this collapsed the whole corpus into a
    # single row.
    cur.execute("DROP VIEW IF EXISTS words")
    cur.execute("""
        CREATE VIEW words AS
        SELECT surah, ayah, word,
               GROUP_CONCAT(form_ar, '') AS word_ar,
               GROUP_CONCAT(form_bw, '') AS word_bw
        FROM (
            SELECT surah, ayah, word, segment, form_ar, form_bw
            FROM corpus
            ORDER BY surah, ayah, word, segment
        )
        GROUP BY surah, ayah, word
    """)

    # View: one row per ayah (full verse text)
    cur.execute("DROP VIEW IF EXISTS ayat")
    cur.execute("""
        CREATE VIEW ayat AS
        SELECT surah, ayah,
               GROUP_CONCAT(word_ar, ' ') AS verse_ar
        FROM (
            SELECT surah, ayah, word,
                   GROUP_CONCAT(form_ar, '') AS word_ar
            FROM corpus
            GROUP BY surah, ayah, word
            ORDER BY surah, ayah, word
        )
        GROUP BY surah, ayah
    """)

    conn.commit()

    # Stats
    count = cur.execute("SELECT COUNT(*) FROM corpus").fetchone()[0]
    surahs = cur.execute("SELECT COUNT(DISTINCT surah) FROM corpus").fetchone()[0]
    roots = cur.execute("SELECT COUNT(DISTINCT root) FROM corpus WHERE root IS NOT NULL").fetchone()[0]
    words = cur.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    ayat = cur.execute("SELECT COUNT(*) FROM ayat").fetchone()[0]

    conn.close()

    print(f"✓ Database aangemaakt: {dst}")
    print(f"  {count:,} segmenten | {words:,} woorden | {ayat:,} verzen | "
          f"{surahs} soera's | {roots:,} unieke wortels")
    print(f"  Tabellen:  corpus")
    print(f"  Views:     words (woord-niveau), ayat (vers-niveau)")
    print(f"  Indexes:   surah+ayah, root, lemma, pos, tag, aspect")


if __name__ == "__main__":
    main()
