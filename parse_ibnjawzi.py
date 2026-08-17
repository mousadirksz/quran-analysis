#!/usr/bin/env python3
"""Parse Ibn al-Jawzi's Nuzhat al-Acyun al-Nawazir fi cilm al-wujuh
wa-l-naza'ir from the OpenITI/Shamela digitization
(sources/ibnjawzi_nuzhat.txt) into structured wujuh data.

Structure of the text:
  ### | - باب <headword>)          entry header (312 entries)
  ... prose definition ...
  وذكر أهل التفسير أن <X> في القرآن على <N> أوجه
  أحدها: <gloss>، ومنه قوله تعالى في <sura>: {<exact Quran quote>} ...
  والثاني: ...

Quotes are in curly braces and follow the Quranic text closely, which
makes them resolvable to sura:aya against the corpus text.

Output: sources/ibnjawzi_wujuh.json
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "sources" / "ibnjawzi_nuzhat.txt"
OUT = Path(__file__).parent / "sources" / "ibnjawzi_wujuh.json"

UNITS = {"واحد": 1, "وجهين": 2, "ثلاثة": 3, "أربعة": 4, "اربعة": 4, "خمسة": 5,
         "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9, "عشرة": 10}
ORD_BASE = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثانى": 2, "الثالث": 3,
            "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8,
            "التاسع": 9, "العاشر": 10, "الحادي": 1, "الحادى": 1}


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
    text = re.sub(r"\(\d+ / [ءا-ي]\}?", " ", text)  # folio markers like (3 / ب
    return text


ENTRY_RE = re.compile(r"### \| - ?(?:باب )?([^)\n]+)\)?")
DECL_RE = re.compile(r"في القرآن على (\S+)(?: عشر)?")
# sense markers: أحدها/أحدهما variants start sense 1; ordinals continue.
MARKER_RE = re.compile(
    r"(?:^|[\n.،:] ?)(?:و|ف)?(أحدهما|أحدها|أولها"
    r"|الأول|الاول|الثاني|الثانى|الثالث|الرابع|الخامس|السادس|السابع"
    r"|الثامن|التاسع|العاشر|الحادي|الحادى)( عشر)?\s*:"
)
QUOTE_RE = re.compile(r"\{([^{}]+)\}")
SURA_HINT_RE = re.compile(r"(?:و?في|من) (?:سورة )?([ء-ي]+(?: عمران)?)\s*:? ?\{")


def marker_number(word, ashar):
    if word in ("أحدهما", "أحدها", "أولها"):
        return 1
    n = ORD_BASE[word]
    return 10 + n if ashar else n


def parse_entry(headword, body):
    m = DECL_RE.search(body)
    declared = None
    decl_end = 0
    if m:
        declared = UNITS.get(m.group(1).strip(":،.- "))
        decl_end = m.end()
        if declared and declared < 10 and re.match(r"\S* عشر", body[m.start(1):m.start(1) + 20]):
            declared += 10
    senses = []
    marks = [(mm.start(), marker_number(mm.group(1), mm.group(2)), mm.end())
             for mm in MARKER_RE.finditer(body)]
    # keep the ascending run; if the sense-1 marker is missing (a handful of
    # entries), synthesize sense 1 from the text after the declaration formula
    run = []
    expect = 1
    for start, n, end in marks:
        if n == expect:
            run.append((start, n, end))
            expect += 1
        elif n == 2 and expect == 1 and declared:
            run.append((decl_end, 1, decl_end))
            run.append((start, 2, end))
            expect = 3
    for idx, (start, n, end) in enumerate(run):
        stop = run[idx + 1][0] if idx + 1 < len(run) else len(body)
        span = body[end:stop]
        gm = re.match(r"\s*(.{2,80}?)(?:[،.]| ومنه| فمنه| قوله| كقوله|$)", span)
        gloss = gm.group(1).strip(" .،") if gm else None
        quotes = [q.strip() for q in QUOTE_RE.findall(span)]
        suras = SURA_HINT_RE.findall(span)
        senses.append({"nr": n, "gloss": gloss, "quotes": quotes, "suras": suras})
    return {"headword": headword.strip(), "declared": declared, "senses": senses}


def main():
    text = normalized_text()
    entries = []
    heads = list(ENTRY_RE.finditer(text))
    for i, h in enumerate(heads):
        title = h.group(1)
        if title.startswith(("(", "أبواب", '"')):  # section headers, not entries
            continue
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        entries.append(parse_entry(title.strip('{}"() '), text[h.end():end]))
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(len(e["senses"]) for e in entries)
    declared = sum(e["declared"] or 0 for e in entries)
    complete = sum(1 for e in entries if e["declared"] == len(e["senses"]))
    quotes = sum(len(s["quotes"]) for e in entries for s in e["senses"])
    glosses = sum(1 for e in entries for s in e["senses"] if s["gloss"])
    print(f"entries: {len(entries)}")
    print(f"declared senses: {declared}, parsed senses: {total}")
    print(f"entries with all declared senses found: {complete}/{len(entries)}")
    print(f"quotes: {quotes}, senses with gloss: {glosses}")


if __name__ == "__main__":
    main()
