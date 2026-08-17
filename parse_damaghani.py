#!/usr/bin/env python3
"""Parse al-Damaghani's Qamus al-Quran (Islah al-wujuh wa-l-naza'ir) from the
OpenITI/Shamela digitization (sources/damaghani_qamus.txt) into structured
wujuh data: one record per entry (headword ~ root), with its numbered senses
and the Quran citations (sura name + quoted fragment) given for each sense.

Output: sources/damaghani_wujuh.json
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "sources" / "damaghani_qamus.txt"
OUT = Path(__file__).parent / "sources" / "damaghani_wujuh.json"

UNITS = {"واحد": 1, "وجهين": 2, "ثلاثة": 3, "أربعة": 4, "اربعة": 4, "خمسة": 5,
         "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9, "عشرة": 10}
AWJUH = {"أوجه", "وجها", "وجوه", "وجه"}
ORDINALS = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثانى": 2, "الثالث": 3,
            "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8,
            "التاسع": 9, "العاشر": 10, "الحادي": 11, "الحادى": 11,
            "الثانية": 2, "الثالثة": 3}
# ordinal + عشر => 10 + value (الحادي عشر = 11 handled via base map below)
TEEN_BASE = {"الحادي": 1, "الحادى": 1, "الثاني": 2, "الثانى": 2, "الثالث": 3,
             "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8,
             "التاسع": 9}


def normalized_tokens():
    lines = []
    for ln in SRC.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        lines.append(ln.strip())
    text = " ".join(lines)
    text = re.sub(r"@ ?PageV\d+P\d+", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    return re.sub(r"\s+", " ", text).split(" ")


def find_headers(toks):
    """Yield (start_of_headword, end_after_awjuh_word, headword, n)."""
    headers = []
    i = 0
    while i < len(toks):
        if toks[i] in ("على", "وعلى"):
            j = i + 1
            if j < len(toks) and toks[j] in UNITS:
                num = UNITS[toks[j]]
                k = j + 1
                if k < len(toks) and toks[k] == "عشر" and num < 10:
                    num += 10
                    k += 1
                if k < len(toks) and toks[k] in AWJUH:
                    endk = k
                elif toks[j] == "وجهين":
                    endk = j
                else:
                    endk = None
                if endk is not None:
                    hw, start = headword_before(toks, i)
                    if hw:
                        if toks[i] == "وعلى":
                            hw += " و"
                        headers.append((start, endk + 1, hw, num))
                        i = endk
        i += 1
    return headers


def headword_before(toks, i):
    """The headword is written as spaced root letters (tokens of 1-2 chars),
    or as one standalone word of 2-4 chars (e.g. entries for whole words)."""
    b = i - 1
    if b < 0 or not re.fullmatch(r"[ء-ي]+", toks[b]):
        return None, i
    if len(toks[b]) >= 3:
        return toks[b], b
    hw = []
    while b >= 0 and len(hw) < 4 and re.fullmatch(r"[ء-ي]{1,2}", toks[b]):
        hw.insert(0, toks[b])
        b -= 1
    return " ".join(hw), b + 1


def split_senses(body_toks):
    """Split an entry body into numbered sense spans."""
    marks = []  # (token_index, sense_number)
    i = 0
    while i < len(body_toks):
        t = body_toks[i].lstrip("و").lstrip("ف")
        if body_toks[i] in ("فوجه", "وجه") and i + 1 < len(body_toks) and body_toks[i + 1] == "منها":
            marks.append((i, 1))
        elif t in ORDINALS:
            n = ORDINALS[t]
            if i + 1 < len(body_toks) and body_toks[i + 1] == "عشر" and t in TEEN_BASE:
                n = 10 + TEEN_BASE[t]
            # require it to start a clause: previous token ends a sentence-ish
            # unit or next token is ':' — the Shamela text uses ' : ' markers
            nxt = body_toks[i + 1] if i + 1 < len(body_toks) else ""
            nxt2 = body_toks[i + 2] if i + 2 < len(body_toks) else ""
            if ":" in (nxt, nxt2) or nxt == "عشر":
                marks.append((i, n))
        i += 1
    # keep only ascending sequences starting at 1
    senses = []
    expect = 1
    for idx, n in marks:
        if n == expect or (senses and n == expect):
            senses.append((idx, n))
            expect = n + 1
    spans = []
    for s, (idx, n) in enumerate(senses):
        end = senses[s + 1][0] if s + 1 < len(senses) else len(body_toks)
        spans.append((n, body_toks[idx:end]))
    return spans


SURA_RE = re.compile(r"سورة ([ء-ي]+(?: [ء-ي]+)?)")
QUOTE_RE = re.compile(r'" ([^"]+) "')


def parse_sense(n, toks):
    text = " ".join(toks)
    # gloss: words between the ordinal marker (+ ':') and the first citation formula
    m = re.match(r"^[^:]{0,25}: (.{2,60}?)(?:[.؟]| قوله| فذلك| فقوله| قال| كقوله|$)", text)
    gloss = m.group(1).strip(" .") if m else None
    suras = SURA_RE.findall(text)
    quotes = [q.strip() for q in QUOTE_RE.findall(text)]
    return {"nr": n, "gloss": gloss, "suras": suras, "quotes": quotes}


def main():
    toks = normalized_tokens()
    headers = find_headers(toks)
    entries = []
    for h, (start, end, hw, num) in enumerate(headers):
        body_end = headers[h + 1][0] if h + 1 < len(headers) else len(toks)
        body = toks[end:body_end]
        senses = [parse_sense(n, sp) for n, sp in split_senses(body)]
        entries.append({"headword": hw, "declared": num, "senses": senses})
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")

    total_senses = sum(len(e["senses"]) for e in entries)
    complete = sum(1 for e in entries if len(e["senses"]) == e["declared"])
    with_quote = sum(1 for e in entries for s in e["senses"] if s["quotes"])
    with_gloss = sum(1 for e in entries for s in e["senses"] if s["gloss"])
    print(f"entries: {len(entries)}")
    print(f"declared senses: {sum(e['declared'] for e in entries)}, parsed senses: {total_senses}")
    print(f"entries with all declared senses found: {complete}/{len(entries)}")
    print(f"senses with >=1 quote: {with_quote}, with gloss: {with_gloss}")


if __name__ == "__main__":
    main()
