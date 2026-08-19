#!/usr/bin/env python3
"""Parse al-Nahhas's Icrab al-Quran (d. 338 AH) into the `irab` table.

Icrab is the syntactic reading of the text: which word is mubtada' and which
khabar, why a word carries this case ending, which of the two readings the
grammarians preferred. Al-Nahhas is the earliest complete work of the genre
still extant, and the OpenITI/Shamela digitization is unusually well suited to
this database: every passage sits under a header that names the sura by number
and the ayah by number,

    ### | [سورة البقرة (2) : آية 134]

so the reference needs no resolving against the text — unlike the wujuh works,
whose citations had to be matched verse by verse. Ranges ("الآيات 3 الى 4")
attach the same passage to each verse in the range, flagged in `is_range`.

What is stored is the passage, not a per-word annotation. Icrab as these works
write it is running argument, frequently weighing named grammarians against one
another; decomposing that into a label per token would be an interpretation
this project has no source for. Anyone wanting per-token syntax should look to
a treebank instead.

Idempotent: drops and rebuilds the table.
"""

import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "sources" / "nahhas_irab.txt"
WORK = "nahhas"

HEADER_RE = re.compile(
    r"\[سورة\s+[^\](]{1,40}\((\d+)\)\s*:\s*(?:آية\s*(\d+)|الآيات\s*(\d+)\s*ال[يى]\s*(\d+))\s*\]")


def normalized_text():
    """Join the digitization's wrapped lines so a header split across two of
    them still reads as one, and drop the page and manuscript markers."""
    out = []
    for ln in SRC.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######"):
            continue
        out.append(ln)
    t = "\n".join(out)
    t = re.sub(r"\n[#~]+ ?", " ", t)
    t = re.sub(r"</?span>|PageV\d+P\d+|\bms\d+\b", " ", t)
    return re.sub(r"[ \t]+", " ", t)


def passages():
    t = normalized_text()
    heads = list(HEADER_RE.finditer(t))
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(t)
        body = t[m.end():end].strip(" .")
        if not body:
            continue
        surah = int(m.group(1))
        if m.group(2):
            ayat = [int(m.group(2))]
        else:
            first, last = int(m.group(3)), int(m.group(4))
            ayat = list(range(first, last + 1)) if last >= first else [first]
        yield surah, ayat, body


def main():
    conn = sqlite3.connect(HERE / "quran.db")
    cur = conn.cursor()
    valid = {(s, a) for s, a in cur.execute("SELECT surah, ayah FROM corpus GROUP BY surah, ayah")}

    cur.execute("DROP TABLE IF EXISTS irab")
    cur.execute("""CREATE TABLE irab (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work TEXT, surah INTEGER, ayah INTEGER,
        passage TEXT, is_range INTEGER)""")

    rows, blocks, unknown = 0, 0, []
    for surah, ayat, body in passages():
        blocks += 1
        for a in ayat:
            if (surah, a) not in valid:
                unknown.append((surah, a))
                continue
            cur.execute("INSERT INTO irab (work, surah, ayah, passage, is_range)"
                        " VALUES (?,?,?,?,?)",
                        (WORK, surah, a, body, 1 if len(ayat) > 1 else 0))
            rows += 1

    cur.execute("CREATE INDEX IF NOT EXISTS idx_irab_verse ON irab(surah, ayah)")
    conn.commit()

    covered = cur.execute("SELECT COUNT(DISTINCT surah || ':' || ayah) FROM irab").fetchone()[0]
    total = len(valid)
    print("irab: %s rijen uit %s blokken, %s van %s verzen gedekt (%.0f%%)"
          % (format(rows, ","), format(blocks, ","), format(covered, ","),
             format(total, ","), covered / total * 100))
    if unknown:
        print("  %d verwijzingen buiten de mushaf overgeslagen, bijv. %s"
              % (len(unknown), unknown[:3]))
    conn.close()


if __name__ == "__main__":
    main()
