#!/usr/bin/env python3
"""Add a `wazifa` column: the classical (nahw) function name of each segment.

A "word" in the classical sense is then uniquely identified by
(lemma, kalima_type, wazifa): maa/ism/istifhamiyyah, maa/ism/shartiyyah and
maa/harf/nafiyah are three different words sharing one written form.

The function follows directly from the corpus POS tag, which was assigned
contextually per occurrence by the corpus annotators. Plain content words
(nouns, verbs, adjectives, pronouns, proper names, demonstratives) carry no
function label and keep NULL; the zuruf tags T/LOC get zarf labels.

Idempotent: safe to run again after rebuilding quran.db and re-running the
earlier migrations (add_kalima_type.py, add_damair_lemmas.py).
"""

import sqlite3
from pathlib import Path

# Corpus tag -> classical function name.
WAZIFA = {
    # functions on asma'
    "REL": "mawsulah",          # relative: alladhi, maa, man
    "INTG": "istifhamiyyah",    # interrogative: maa, man, kayfa, hamza
    "COND": "shartiyyah",       # conditional: in, man, maa, mahmaa
    "T": "zarf_zaman",          # time adverb: idhaa, idh, yawma'idhin
    "LOC": "zarf_makan",        # place adverb: 'inda, bayna, haythu
    # huruf
    "P": "jarr",                # prepositions: min, fii, bi-, li-, waw qasam
    "CONJ": "atf",              # coordinating waw/fa
    "REM": "istinafiyyah",      # resumption waw/fa
    "CIRC": "haliyyah",         # circumstantial waw
    "COM": "maiyyah",           # waw of accompaniment
    "SUP": "zaidah",            # supplemental/redundant maa, waw
    "NEG": "nafiyah",           # negation: laa, maa, in, lam, lan
    "PRO": "nahiyah",           # prohibition: laa
    "PREV": "kaffah",           # preventive maa (innamaa)
    "SUB": "masdariyyah",       # subordinating: an, maa, law, kay
    "INT": "mufassirah",        # interpretive an
    "EXP": "istithnaiyyah",     # exceptive illaa
    "RES": "hasr",              # restriction illaa, innamaa
    "CERT": "tahqiq",           # certainty: qad
    "ACC": "nasikhah",          # inna and sisters
    "EMPH": "tawkid",           # lam/nun of emphasis
    "RSLT": "jawab_shart",      # fa in conditional apodosis
    "CAUS": "sababiyyah",       # causal fa
    "PRP": "taliliyyah",        # lam of purpose
    "IMPV": "amr",              # lam of command
    "FUT": "istiqbal",          # sa-, sawfa
    "DET": "tarif",             # definite article
    "VOC": "nida",              # yaa, ayyuhaa (the vocative particle prefix)
    "EQ": "taswiyah",           # equalization hamza (sawaa'un a-...)
    "INC": "ibtidaiyyah",       # inceptive: hattaa, bal
    "RET": "idrab",             # retraction: bal
    "ANS": "jawab",             # answer: na'am, balaa, idhan
    "SUR": "fujaiyyah",         # surprise: idhaa
    "EXH": "tahdid",            # exhortation: lawlaa, alaa
    "EXL": "tafsiliyyah",       # detailing: ammaa
    "AMD": "istidrak",          # amendment: laakin
    "AVR": "zajr",              # aversion: kallaa
    # content tags (N, PN, ADJ, IMPN, V, PRON, DEM, INL) keep NULL
}


def main():
    db = Path(__file__).parent / "quran.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    cols = [row[1] for row in cur.execute("PRAGMA table_info(corpus)")]
    if "wazifa" not in cols:
        cur.execute("ALTER TABLE corpus ADD COLUMN wazifa TEXT")

    for tag, wazifa in WAZIFA.items():
        cur.execute("UPDATE corpus SET wazifa=? WHERE tag=?", (wazifa, tag))

    cur.execute("CREATE INDEX IF NOT EXISTS idx_wazifa ON corpus(wazifa)")
    conn.commit()

    cur.execute(
        "SELECT COUNT(DISTINCT lemma||'|'||kalima_type||'|'||IFNULL(wazifa,'')) "
        "FROM corpus WHERE lemma!=''"
    )
    print("distinct words (lemma, kalima_type, wazifa):", cur.fetchone()[0])
    for row in cur.execute(
        "SELECT lemma_ar, kalima_type, wazifa, COUNT(*) FROM corpus "
        "WHERE lemma='maA' GROUP BY kalima_type, wazifa ORDER BY 4 DESC"
    ):
        print(row)
    conn.close()


if __name__ == "__main__":
    main()
