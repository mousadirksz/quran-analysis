#!/usr/bin/env python3
"""Parse Yahya ibn Sallam's at-Tasarif (d. 200 AH) — the oldest surviving
work of the wujuh genre, built on Muqatil's material — from the
OpenITI/Shamela digitization (sources/tasarif.txt).

The text is the most database-like of the three works:
  ### | تفسير "هدى" على سبعة عشر وجها       entry header with declared count
  ### | الوجه الأول: هدى يعني بيانا          per-sense header: nr + gloss
  ... quotes in {braces}, sura refs as "في <name>" using archaic sura
  names (hal ata, tah, hamalsajda, alladhina kafaru, ...)

Output: sources/tasarif_wujuh.json (same shape as the other two works).
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "sources" / "tasarif.txt"
OUT = Path(__file__).parent / "sources" / "tasarif_wujuh.json"

UNITS = {"واحد": 1, "وجهين": 2, "ثلاثة": 3, "أربعة": 4, "أربع": 4, "اربعة": 4,
         "خمسة": 5, "خمس": 5, "ستة": 6, "ست": 6, "سبعة": 7, "سبع": 7,
         "ثمانية": 8, "ثمان": 8, "تسعة": 9, "تسع": 9, "عشرة": 10, "عشر": 10,
         "أحد": 1, "اثني": 2, "اثنى": 2}
ORDS = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثانى": 2, "الثالث": 3,
        "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8,
        "التاسع": 9, "العاشر": 10, "الحادي": 1, "الحادى": 1, "الثانية": 2}

ENTRY_RE = re.compile(r'تفسير "?(.+?)"? على (\S+)(?: (عشر))?(?: وجها| أوجه| وجوه|)')
WAJH_RE = re.compile(r"الوجه (\S+)( عشر)?\s*:?\s*(.*)")
QUOTE_RE = re.compile(r"\{([^{}]+)\}")
SURA_RE = re.compile(r"في ([ء-ي]+(?: [ء-ي]+){0,2}?)\s*:?\s*\{")


def normalized_text():
    lines = []
    for ln in SRC.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        if not ln.startswith("###"):
            ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        lines.append(ln.strip())
    text = "\n".join(lines)
    text = re.sub(r"@? ?PageV\d+P\d+", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    return text


def parse_declared(unit, ashar):
    n = UNITS.get(unit.strip(':،." '))
    if n and ashar:
        n = n + 10 if n < 10 else n
    return n


def main():
    text = normalized_text()
    headers = [(m.start(), m.end(), m.group(1))
               for m in re.finditer(r"### \| ?(.+)", text)]
    entries = []
    current = None
    for i, (start, end, title) in enumerate(headers):
        body_end = headers[i + 1][0] if i + 1 < len(headers) else len(text)
        body = text[end:body_end]
        em = ENTRY_RE.search(title)
        wm = WAJH_RE.search(title)
        if em and "الوجه" not in title:
            if current:
                entries.append(current)
            current = {"headword": em.group(1).strip('"، '),
                       "declared": parse_declared(em.group(2), em.group(3)),
                       "senses": []}
            continue
        if wm:
            nr = ORDS.get(wm.group(1).strip(":"))
            if nr and wm.group(2):
                nr += 10
            rest = wm.group(3).strip()
            gloss = None
            headword_in_title = None
            if " يعني " in rest:
                headword_in_title, gloss = rest.split(" يعني ", 1)
            elif rest:
                gloss = rest
            if current is None:  # senses before any entry header
                current = {"headword": (headword_in_title or "").strip() or "؟",
                           "declared": None, "senses": []}
            quotes = [q.strip() for q in QUOTE_RE.findall(body)]
            suras = SURA_RE.findall(body)
            current["senses"].append({"nr": nr or len(current["senses"]) + 1,
                                      "gloss": (gloss or "").strip(" .،") or None,
                                      "quotes": quotes, "suras": suras})
    if current:
        entries.append(current)
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    total = sum(len(e["senses"]) for e in entries)
    quotes = sum(len(s["quotes"]) for e in entries for s in e["senses"])
    complete = sum(1 for e in entries if e["declared"] == len(e["senses"]))
    print(f"entries: {len(entries)}")
    print(f"senses: {total}, quotes: {quotes}")
    print(f"entries with all declared senses: {complete}/{len(entries)}")


if __name__ == "__main__":
    main()
