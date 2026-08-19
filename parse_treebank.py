#!/usr/bin/env python3
"""Load the Extended Quranic Treebank into the `syntax` table.

This is the icrab layer at the level of the individual token: which word is the
faacil of which verb, which is the mafcul, which the khabar — the analysis the
classical icrab works argue out in prose, here as a structure that can be
queried. Each token carries its relation label (English and Arabic) and points
at its head, so a verse's parse can be walked from its root.

Two things make it fit this database exactly:

The addressing is the same. Every token that corresponds to written text
carries a `location` of the form (surah:ayah:word:segment) — the corpus'
own scheme — so all 128,219 of them join onto `corpus.id` with nothing left
over on either side.

It supplies what the corpus cannot. Beside the written tokens the treebank
posits the 11,157 elements the grammarians read into the text but which are
not written: above all the damir mustatir, the pronoun contained in a verb
(6,674 of them, e.g. the implied "you" that is the faacil of qul in 112:1).
Those rows have no location and no corpus_id, and are marked `is_implicit`.
Counting kalimat with them and without them gives two different, defensible
totals, which is why they are kept and flagged rather than dropped.

Source: sources/treebank_eqtb.tsv.gz — the 14 columns used here, converted
from UTF-16 to UTF-8 and gzipped, from corpus/Quranic.rar in
github.com/NoorBayan/Quranic (MIT). Values are unaltered. See SOURCES.md.

Idempotent: drops and rebuilds the table.
"""

import csv
import gzip
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "sources" / "treebank_eqtb.tsv.gz"
LOCATION_RE = re.compile(r"^\((\d+):(\d+):(\d+):(\d+)\)$")


def main():
    conn = sqlite3.connect(HERE / "quran.db")
    cur = conn.cursor()
    corpus_ids = {(s, a, w, g): i for i, s, a, w, g in cur.execute(
        "SELECT id, surah, ayah, word, segment FROM corpus")}

    cur.execute("DROP TABLE IF EXISTS syntax")
    cur.execute("""CREATE TABLE syntax (
        tid INTEGER PRIMARY KEY,
        sentence_id INTEGER, token_id INTEGER,
        surah INTEGER, ayah INTEGER, word INTEGER, segment INTEGER,
        corpus_id INTEGER,
        token_ar TEXT, pos TEXT,
        rel_label TEXT, rel_label_ar TEXT,
        head_token_id INTEGER, head_tid INTEGER,
        constituent_label TEXT, is_implicit INTEGER)""")

    rows, by_sentence = [], {}
    with gzip.open(SRC, "rt", encoding="utf-8", newline="") as f:
        for x in csv.DictReader(f, delimiter="\t"):
            tid = int(x["tid"])
            sent, tok = int(x["sentence_id"]), int(x["token_id"])
            m = LOCATION_RE.match(x["location"])
            if m:
                s, a, w, g = (int(v) for v in m.groups())
                cid = corpus_ids.get((s, a, w, g))
            else:
                s = a = w = g = cid = None
            by_sentence.setdefault(sent, {})[tok] = tid
            head = x["ref_token_id"]
            rows.append([tid, sent, tok, s, a, w, g, cid, x["uthmani_token"],
                         x["pos"] or None, x["rel_label"] or None,
                         x["rel_label_ar"] or None,
                         int(head) if head not in ("", None) else None,
                         None, x["constituent_label"] or None,
                         0 if m else 1])

    # resolve each head to the global row id, so a parse can be walked without
    # carrying the sentence around
    for r in rows:
        if r[12] is not None and r[12] != r[2]:
            r[13] = by_sentence.get(r[1], {}).get(r[12])
    cur.executemany("INSERT INTO syntax VALUES (%s)" % ",".join("?" * 16), rows)

    # index first: the coverage checks below are joins over 139k x 128k rows
    for stmt in ("CREATE INDEX IF NOT EXISTS idx_syntax_verse ON syntax(surah, ayah)",
                 "CREATE INDEX IF NOT EXISTS idx_syntax_corpus ON syntax(corpus_id)",
                 "CREATE INDEX IF NOT EXISTS idx_syntax_sentence ON syntax(sentence_id)",
                 "CREATE INDEX IF NOT EXISTS idx_syntax_rel ON syntax(rel_label)"):
        cur.execute(stmt)

    written = cur.execute("SELECT COUNT(*) FROM syntax WHERE is_implicit=0").fetchone()[0]
    unlinked = cur.execute(
        "SELECT COUNT(*) FROM syntax WHERE is_implicit=0 AND corpus_id IS NULL").fetchone()[0]
    if unlinked:
        conn.rollback()
        raise SystemExit("%d written tokens do not match a corpus segment" % unlinked)
    missing = cur.execute(
        "SELECT COUNT(*) FROM corpus c WHERE NOT EXISTS"
        " (SELECT 1 FROM syntax s WHERE s.corpus_id = c.id)").fetchone()[0]
    if missing:
        conn.rollback()
        raise SystemExit("%d corpus segments have no syntax row" % missing)

    conn.commit()

    implicit = cur.execute("SELECT COUNT(*) FROM syntax WHERE is_implicit=1").fetchone()[0]
    sentences = cur.execute("SELECT COUNT(DISTINCT sentence_id) FROM syntax").fetchone()[0]
    rels = cur.execute("SELECT COUNT(DISTINCT rel_label) FROM syntax").fetchone()[0]
    print("syntax: %s tokens (%s geschreven, alle gekoppeld aan corpus; %s impliciet),"
          " %s zinnen, %s relatielabels"
          % (format(len(rows), ","), format(written, ","), format(implicit, ","),
             format(sentences, ","), rels))
    conn.close()


if __name__ == "__main__":
    main()
