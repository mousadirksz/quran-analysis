#!/usr/bin/env python3
"""Export the Quranic corpus TSV to a SQLite database with useful indexes."""

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

    # View: one row per word (concatenated segments)
    cur.execute("""
        CREATE VIEW IF NOT EXISTS words AS
        SELECT surah, ayah, word,
               GROUP_CONCAT(form_ar, '') AS word_ar,
               GROUP_CONCAT(form_bw, '') AS word_bw
        FROM corpus
        ORDER BY surah, ayah, word, segment
    """)

    # View: one row per ayah (full verse text)
    cur.execute("""
        CREATE VIEW IF NOT EXISTS ayat AS
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

    conn.close()

    print(f"✓ Database aangemaakt: {dst}")
    print(f"  {count:,} segmenten | {surahs} soera's | {roots:,} unieke wortels")
    print(f"  Tabellen:  corpus")
    print(f"  Views:     words (woord-niveau), ayat (vers-niveau)")
    print(f"  Indexes:   surah+ayah, root, lemma, pos, tag, aspect")


if __name__ == "__main__":
    main()
