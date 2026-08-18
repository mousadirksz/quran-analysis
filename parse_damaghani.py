#!/usr/bin/env python3
"""Parse al-Damaghani's Qamus al-Quran (Islah al-wujuh wa-l-naza'ir) from the
OpenITI/Shamela digitization (sources/damaghani_qamus.txt) into structured
wujuh data: one record per entry (headword ~ root), with its numbered senses
and the Quran citations (sura name + quoted fragment) given for each sense.

The digitization degrades badly in the second half of the book: from the bab
al-sad onwards it loses its hamzas ("اوجه" for "أوجه"), its colons after the
sense ordinals, its quotation marks around the cited verses, and its line
breaks, so an entry arrives as one unbroken run of words. The parser
therefore recognises a sense from the bare ordinal alone, and falls back on
"في سورة X ..." to delimit a citation when no quotation marks survive. Both
fallbacks are constrained so they cannot invent material: an ordinal only
counts when it is the next number of the sequence and the entry's own
announced count has not been reached, and an unquoted citation is only read
from a sense that carries no quotation marks at all.

Output: sources/damaghani_wujuh.json
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "sources" / "damaghani_qamus.txt"
OUT = Path(__file__).parent / "sources" / "damaghani_wujuh.json"

# "<headword> cala <count> awjuh" announces an entry and its number of senses
UNITS = {"واحد": 1, "وجهين": 2, "وجهان": 2, "ثلاثة": 3, "أربعة": 4, "اربعة": 4,
         "أربعه": 4, "خمسة": 5, "ستة": 6, "سبعة": 7, "ثمانية": 8, "تسعة": 9,
         "عشرة": 10, "أحد": 11, "احد": 11, "اثنا": 12, "اثنى": 12, "اثني": 12,
         "عشرين": 20, "عشرون": 20}
TEENABLE = {"ثلاثة", "أربعة", "اربعة", "أربعه", "خمسة", "ستة", "سبعة",
            "ثمانية", "تسعة"}
AWJUH = {"أوجه", "اوجه", "وجها", "وجوه", "وجه", "وجهين", "وجهان"}

# sense ordinals; al-hadi/al-thani only reach 11/12 together with cashar,
# and 21/22 together with wa-l-cishrun
ORD_BASE = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثانى": 2, "التاني": 2,
            "الثالث": 3, "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7,
            "الثامن": 8, "التاسع": 9, "العاشر": 10, "الحادي": 1, "الحادى": 1,
            "ثانيا": 2, "ثالثا": 3, "رابعا": 4, "خامسا": 5, "سادسا": 6,
            "سابعا": 7, "ثامنا": 8, "تاسعا": 9, "عاشرا": 10}
TEEN_OK = {"الحادي", "الحادى", "الثاني", "الثانى", "التاني", "الثالث",
           "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع"}
TENS = {"العشرون": 20, "العشرين": 20}
# the unpunctuated text glues the ordinal onto the previous word
# ("ونحوه كثيرالخامس"), so a trailing ordinal still counts
MERGED_ORD = re.compile("(" + "|".join(sorted(
    (w for w in ORD_BASE if w.startswith("ال")), key=len, reverse=True)) + ")$")

# the first sense opens with "fa-wajh minha", with every scribal variant of it
SENSE1_HEAD = re.compile(r"^[وفب]?(?:ال)?(?:وجه|رجه|وجد|واحدة)$")
SENSE1_MERGED = re.compile(r"^[وفب]?(?:ال)?(?:وجه|رجه|وجد)من")
SENSE1_TAIL = {"منها", "منهما", "منه", "منهن", "مها"}

PUNCT = '.,،؛;:!؟()[]{}*"/'

GLOSS_RE = re.compile(r"^[^:]{0,25}: (.{2,60}?)(?:[.؟]| قوله| فذلك| فقوله| قال| كقوله|$)")
# words that end a gloss, and (with the citation verbs) an unquoted citation
STOP = {"قوله", "وقوله", "فقوله", "كقوله", "لقوله", "بقوله", "قال", "وقال",
        "فقال", "يقول", "فذلك", "وذلك", "ذلك", "نظيره", "نظيرها", "مثلها",
        "مثله", "كقول", "سورة", '"', ".", "،", "-"}
CITE_STOP = STOP | {"يعني", "أي", "اي", "يريد", "أراد", "اراد", "وهو", "وهي",
                    "ونظائرها", "ونظائره", "نظائرها", "وأمثالها", "وامثاله",
                    "وأمثاله", "كثير", "كثيرة", "كثيرا", "ونحوه", "نحوه",
                    "إلى", "الى", "سبحانه", "تعالى", "عز", "ومثله", "ومثلها",
                    "وكقوله", "وفي", "في", "وقيل", "قيل", "بمعنى", "وسورة"}
# sura names the authors write as more than one word (Al cImran, Ha-Mim cAsaq)
NAME_HEAD = {"آل", "ال", "حم", "خم", "بني", "الم", "سال", "لم", "اذا", "إذا", "قل",
             "هل", "سبح", "عم", "تنزيل", "اقتربت", "قد", "تبت", "ن"}
BLESS = ["صلى", "الله", "عليه", "وسلم"]

SURA_RE = re.compile(r"سورة ([ء-ي]+(?: [ء-ي]+)?)")
QUOTE_RE = re.compile(r'" ([^"]+) "')


def normalized_tokens():
    lines = []
    for ln in SRC.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        lines.append(ln.strip())
    text = " ".join(lines)
    text = re.sub(r"@?\s*PageV\d+P\d+", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    text = re.sub(r"\|\s*CHECK\s*\[[^\]]*\]", " ", text)
    text = text.replace("((", ' " ').replace("))", ' " ')  # the later chapters' quote marks
    for ch in PUNCT:
        text = text.replace(ch, " " + ch + " ")
    return re.sub(r"\s+", " ", text).strip().split(" ")


def read_count(toks, j):
    """Read the spelled-out sense count at toks[j]; return (value, next index)."""
    t = toks[j]
    if t not in UNITS:
        return None, j
    n, k = UNITS[t], j + 1
    if k < len(toks) and toks[k] in ("عشر", "عشرا"):
        if t in TEENABLE:
            n += 10
        elif n not in (11, 12):
            return None, j
        k += 1
    elif n in (11, 12):  # ahad/ithna only mean 11/12 before cashar
        return None, j
    return n, k


def find_headers(toks):
    """Yield (start_of_headword, end_after_awjuh_word, headword, n)."""
    headers = []
    i = 0
    while i < len(toks):
        pre = ""
        if toks[i] == "على":
            pass
        elif toks[i] == "وعلى":
            pre = "و"
        elif re.fullmatch(r"[ء-ي]{1,3}على", toks[i]):  # last root letters glued on
            pre = toks[i][:-3]
        else:
            i += 1
            continue
        num, k = read_count(toks, i + 1)
        if num is not None:
            if k < len(toks) and toks[k] in AWJUH:
                endk = k
            elif toks[i + 1] in ("وجهين", "وجهان"):
                endk = i + 1
            else:
                endk = None
            if endk is not None:
                hw, start = headword_before(toks, i, pre)
                if hw:
                    headers.append((start, endk + 1, hw, num))
                    i = endk
        i += 1
    return headers


def headword_before(toks, i, pre=""):
    """The headword is written as spaced root letters (tokens of 1-2 chars),
    or as one standalone word of 2-4 chars (e.g. entries for whole words),
    optionally followed by an editorial gloss: "ر ج ل ( رجال ) على .."."""
    b = i - 1
    if b >= 0 and toks[b] == ")":
        k = b - 1
        while k >= 0 and b - k < 8 and toks[k] != "(":
            k -= 1
        if k >= 0 and toks[k] == "(":
            b = k - 1
    if pre:
        hw = [pre]
    else:
        if b < 0 or not re.fullmatch(r"[ء-ي]+", toks[b]):
            return None, i
        if len(toks[b]) >= 3:
            return toks[b], b
        hw = []
    while b >= 0 and len(hw) < 4 and re.fullmatch(r"[ء-ي]{1,2}", toks[b]):
        hw.insert(0, toks[b])
        b -= 1
    return " ".join(hw), b + 1


def ordinal_at(toks, i):
    """Candidate (sense number, tokens consumed) readings of toks[i]."""
    t = toks[i].lstrip("وف")
    if t in TENS:
        return [(TENS[t], 1)]
    if t not in ORD_BASE:
        m = MERGED_ORD.search(t)
        if not m or len(t) - len(m.group(1)) < 2:
            return []
        t = m.group(1)
    base = ORD_BASE[t]
    nxt = toks[i + 1] if i + 1 < len(toks) else ""
    out = []
    if t in TEEN_OK and (nxt == "عشر" or (nxt.startswith("عشر") and len(nxt) > 4)):
        out.append((10 + base, 2))
    if nxt in ("والعشرون", "والعشرين"):
        out.append((20 + base, 2))
    if t not in ("الحادي", "الحادى"):
        out.append((base, 1))
    return out


def split_senses(body, declared):
    """Split an entry body into numbered sense spans.

    Where the digitization still has its punctuation the ordinal is followed
    by ' : '; where it does not, the ordinal stands bare in mid-sentence. To
    keep the bare-ordinal reading from inventing senses, a mark is only taken
    when it reads as exactly the next number of the sequence, and the run
    stops at the count the entry itself announced (so a missed entry header
    can no longer make one entry swallow the senses of the next).
    """
    marks = []
    expect = 1
    i = 0
    while i < len(body) and expect <= declared:
        t = body[i]
        if expect == 1 and (SENSE1_MERGED.match(t) or (
                SENSE1_HEAD.match(t) and body[i + 1:i + 2]
                and body[i + 1] in SENSE1_TAIL)):
            width = 1 if SENSE1_MERGED.match(t) else 2
            marks.append((i, 1, width))
            expect, i = 2, i + width
            continue
        hit = [(n, w) for n, w in ordinal_at(body, i) if n == expect]
        if hit and (expect > 1 or i == 0):  # sense 1 is announced, never bare
            n, width = hit[0]
            marks.append((i, n, width))
            expect, i = n + 1, i + width
            continue
        i += 1
    spans = []
    for s, (idx, n, width) in enumerate(marks):
        end = marks[s + 1][0] if s + 1 < len(marks) else len(body)
        spans.append((n, body[idx:end], width))
    return spans


def gloss_without_colon(toks, width):
    """Unpunctuated senses have no ':' after the ordinal, so take the words
    between the marker and the first citation formula."""
    words = []
    rest = toks[width:]
    for k, t in enumerate(rest):
        if t in STOP or not re.search(r"[ء-ي]", t):
            break
        if t == "في" and rest[k + 1:k + 2] == ["سورة"]:
            break
        words.append(t)
        if len(words) >= 10 or len(" ".join(words)) >= 60:
            break
    return " ".join(words).strip(" .,،:")


def unquoted_citations(span):
    """Citations from a sense whose quotation marks the digitization lost:
    the verse text is what follows "sura X" up to the first commentary word."""
    out = []
    i = 0
    while i < len(span):
        if span[i] in ("سورة", "سورتي") and i + 1 < len(span):
            k = i + 2
            if span[i + 1] in NAME_HEAD and k < len(span):
                k += 1
            if span[k:k + 4] == BLESS:
                k += 4
            words = []
            while k < len(span):
                t = span[k]
                if t in CITE_STOP or len(t) == 1 or not re.fullmatch(r"[ء-ي]+", t):
                    break
                words.append(t)
                k += 1
                if len(words) >= 12:
                    break
            if len(words) >= 3:
                out.append(" ".join(words))
            i = max(k, i + 1)
        else:
            i += 1
    return out


def parse_sense(n, toks, width):
    text = " ".join(toks)
    m = GLOSS_RE.match(text)
    gloss = m.group(1).strip(" .") if m else gloss_without_colon(toks, width)
    quotes = [q.strip() for q in QUOTE_RE.findall(text)]
    if '"' not in toks:
        quotes = unquoted_citations(toks)
    return {"nr": n, "gloss": gloss or None, "suras": SURA_RE.findall(text),
            "quotes": quotes}


def main():
    toks = normalized_tokens()
    headers = find_headers(toks)
    entries = []
    for h, (start, end, hw, num) in enumerate(headers):
        body_end = headers[h + 1][0] if h + 1 < len(headers) else len(toks)
        body = toks[end:body_end]
        senses = [parse_sense(n, sp, w) for n, sp, w in split_senses(body, num)]
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
