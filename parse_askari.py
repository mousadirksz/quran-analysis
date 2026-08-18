#!/usr/bin/env python3
"""Parse Abu Hilal al-cAskari's al-Wujuh wa-l-Naza'ir (d. ca. 395 AH) from the
OpenITI/Shamela digitization (sources/askari_wujuh_src.txt) into structured
wujuh data: one record per entry (headword), with its numbered senses and the
Quran citations given under each sense.

Structure of this edition, which differs from the other three works:
  ### | الباب الأول            chapter header, one per letter of the alphabet
  ### | إمام                   entry header (the headword, bare)
  ... etymology of the word, often a page or more ...
  والإمام في القرآن على أربعة أوجه:      the declaration formula + sense count
  أولها: بمعنى القائد، قال الله تعالى: (إني جاعلك للناس إماما)، أي: ...
  الثاني: الكتاب، قال الله تعالى: (يوم ندعو كل أناس بإمامهم)، أي: ...

so: senses are marked by a bare ordinal followed by a colon, and Quran quotes
sit in round brackets, not in the braces that the other three digitizations
use. Quotes therefore have to be read from balanced bracket pairs, which is
what makes the unbalanced brackets the digitization leaves behind harmless:
an opening bracket with no partner simply never pairs.

al-cAskari almost never names the sura he is quoting from. Eight citations in
the whole book carry a "fi <sura>" hint (al-Hashr, al-Baqara, al-Mumtahana,
al-Naml, al-Hajj, al-Nisa', Yasin, Maryam - all of them the ordinary titles,
none of the archaic opening-word names Yahya ibn Sallam uses), so `suras` is
empty for practically every sense and the resolver has to place these quotes
on their wording alone.

The digitization cuts the text open at page turns, and every cut has to be
repaired before parsing or it breaks an entry in half:
  * "### | ......" and "### | " headers are page-break noise inside an entry,
    not new entries; their bodies belong to the entry above them.
  * a headword split across a header boundary leaves its tail in an HTML span
    remnant on the first body line ("### | الآخ" + "رة</span>" = al-akhira);
    the tail is glued back onto the headword.
  * the same split hits sense markers ("الث" + "### | اني: " = al-thani); a
    header whose title ends in a colon is spliced back into the running text.
  * at nine cuts the digitizer put a piece of the running text on the header
    line, so "### | في" is the middle of khafifan and "### | الدين" is a word
    of the sentence around it. A header is only read as a headword when it
    stands at a page turn or behind a chapter header (see at_clean_break);
    otherwise its title goes back into the body it was cut out of.
  * four headers went missing instead (three entries and one chapter): the
    headword sits unmarked on a bare line after the page turn, and is
    promoted back to a header.

Conservatism, as in the other parsers: a sense counts only when its ordinal is
exactly the next number of the sequence, the run is capped at the count the
entry itself announces, and markers are only looked for after the declaration
formula, so the numbered lists in the etymological preamble (which enumerate
grammatical opinions, not Quranic senses) cannot be mistaken for wujuh. Where
the author lists his wujuh in running prose instead of numbering them (about
a dozen entries, e.g. al-nikah, al-zann) nothing is parsed rather than guessed.

Output: sources/askari_wujuh.json (same shape as the other three works).
"""

import json
import re
from pathlib import Path

SRC = Path(__file__).parent / "sources" / "askari_wujuh_src.txt"
OUT = Path(__file__).parent / "sources" / "askari_wujuh.json"

# "<word> fi l-Qur'an cala <count> awjuh" announces an entry's sense count
UNITS = {"واحد": 1, "وجهين": 2, "وجهان": 2, "الوجهين": 2, "ثلاثة": 3,
         "أربعة": 4, "اربعة": 4, "أربعه": 4, "خمسة": 5, "ستة": 6, "سبعة": 7,
         "ثمانية": 8, "تسعة": 9, "عشرة": 10, "أحد": 11, "احد": 11,
         "اثنا": 12, "اثني": 12, "اثنى": 12}
TEENABLE = {"ثلاثة", "أربعة", "اربعة", "أربعه", "خمسة", "ستة", "سبعة",
            "ثمانية", "تسعة"}

ORD_BASE = {"الأول": 1, "الاول": 1, "الثاني": 2, "الثانى": 2, "الثالث": 3,
            "الرابع": 4, "الخامس": 5, "السادس": 6, "السابع": 7, "الثامن": 8,
            "التاسع": 9, "العاشر": 10, "الحادي": 1, "الحادى": 1}
FIRST = {"أحدهما", "أحدها", "أحدهن", "أولها", "أولهما", "أولاها", "اولها",
         "احدهما", "احدها"}
# al-hadi only ever means "eleventh", i.e. it needs the following cashar
TEEN_ONLY = {"الحادي", "الحادى"}

# "cala <count> awjuh"; the digitization sometimes reads the cala as kull
DECL_HEAD = r"(?:على|القرآن كل|القران كل|القرآن|القران)\s+"
DECL_RE = re.compile(
    DECL_HEAD + r"(\S+?)(?:\s+(عشر))?\s+(?:أوجه|اوجه|وجوه|وجها)\b"
    r"|" + DECL_HEAD + r"(وجهين|وجهان|الوجهين)\b")

# a sense marker: an optional "al-wajh", the ordinal, and a colon. The colon
# is written as ':' or as the semicolon ';', sometimes after a stray dash.
MARKER_RE = re.compile(
    r"(?<![ء-ي])(?:الوجه )?((?:و|ف)?(?:" + "|".join(
        sorted(FIRST | set(ORD_BASE), key=len, reverse=True)) + r"))"
    r"(\s+عشر)?(?![ء-ي])\s*-?\s*([:؛])?")

QUOTE_RE = re.compile(r"\(([^()]{1,200})\)")
SPAN_TAIL_RE = re.compile(r"^([ء-ي]{1,4})</span>$")
PAGE_RE = re.compile(r"@? ?PageV\d+P\d+")
PAGE_END_RE = re.compile(r"PageV\d+P\d+\s*$")
MS_RE = re.compile(r"\bms\d+\b")
CHAPTER_DESC_RE = re.compile(r"(?:في ما|فيما|فبما) جاء|في ذكر ")
# a headword the digitizer forgot to mark as a header: a short bare line of
# Arabic words, standing on its own right after a page turn
LOST_HEAD_RE = re.compile(r"[ء-ي]{2,}(?: [ء-ي]+){0,2}")
# the sura hint, on the rare occasions al-cAskari gives one: "wa-fi l-Hashr: (..)"
SURA_HINT_RE = re.compile(r"(?:و?في|و?من) (?:سورة )?([ء-ي]+)\s*:? ?\(")
# framing nouns the hint regex would otherwise pick up ("fi qawlihi: (..)")
HINT_NOISE = {"قوله", "قولك", "قول", "القرآن", "القران", "التفسير", "الجواب",
              "هذا", "فقال", "الآية", "الأول", "الآخرة", "الصلاة", "العالمين",
              "العبد", "أخيه", "المسبحين", "خسر"}
# a gloss is the plain paraphrase after the ordinal; these words start a
# citation instead, so a "gloss" beginning with one is no gloss at all
CITE_HEAD = re.compile(r"^(?:\(|قال|قوله|وقوله|فقوله|كقوله|قرأ|هو قوله|منه)")
GLOSS_STOP = re.compile(
    r"\s*(.{2,80}?)(?:[،.؛:(]| قال| قوله| وقوله| فقوله| كقوله| وهو | ومنه"
    r"| نحوه| ونحوه| يعني|$)")


def at_clean_break(out):
    """Does a '### | X' header stand where a new entry can start?

    A real header always sits at a page turn or right behind a chapter header
    and its description line. Where it does not, the digitizer has cut the
    running text open at a page boundary and put a fragment of that text on the
    header line ('idha kana kha' + '### | fi' + 'fan kathir' = 'khafifan'), so
    the title is running text, not a headword. A stray line of one or two
    letters, which the same cut leaves behind, is skipped on the way back."""
    for ln in reversed(out):
        if PAGE_END_RE.search(ln):
            return True
        if len(ln) <= 2:
            continue
        return ln.startswith("### |") or CHAPTER_DESC_RE.match(ln)
    return True


def normalized_text():
    """Strip the OpenITI markup, page/microfilm markers and HTML remnants, and
    fold the '### | ...' artefact headers back into the entry they interrupt."""
    lines = []
    for ln in SRC.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        if not ln.startswith("###"):
            ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        ln = MS_RE.sub(" ", ln)
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if ln:
            lines.append(ln)

    out = []
    for ln in lines:
        tail = SPAN_TAIL_RE.match(ln)
        if tail and out and out[-1].startswith("### |"):
            out[-1] += tail.group(1)  # headword torn across the header boundary
            continue
        if ln.startswith("### |"):
            title = ln[len("### |"):].strip()
            if not title or set(title) <= set(". "):
                continue  # page-break noise, not an entry
            if title.endswith(":") and out and not out[-1].startswith("### |"):
                # a sense marker torn in two by the page break: glue it back on
                out[-1] = out[-1] + title
                continue
            if not at_clean_break(out):
                out.append(title)  # running text, not a headword
                continue
            ln = "### | " + title
        elif LOST_HEAD_RE.fullmatch(ln) and out and (
                PAGE_END_RE.search(out[-1]) or CHAPTER_DESC_RE.match(out[-1])):
            ln = "### | " + ln  # an entry header the digitizer left unmarked
        out.append(ln)

    text = "\n".join(out)
    text = PAGE_RE.sub(" ", text)
    text = re.sub(r"</?span[^>]*>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text


def read_declared(m):
    """Sense count from a declaration match, or None when it is not a number
    ('cala ciddat awjuh', 'cala hadhihi l-wujuh')."""
    if m.group(3):
        return 2
    n = UNITS.get(m.group(1).strip("،.:"))
    if n is None:
        return None
    if m.group(2):
        return n + 10 if m.group(1) in TEENABLE else (n if n in (11, 12) else None)
    return None if n in (11, 12) else n


def marker_number(word, ashar):
    word = word.lstrip("وف") if word not in FIRST else word
    if word in FIRST or word.lstrip("وف") in FIRST:
        return 1
    if word in TEEN_ONLY:
        return 11 if ashar else None
    n = ORD_BASE.get(word)
    if n is None:
        return None
    return n + 10 if ashar else n


def sense_spans(body, declared):
    """Numbered sense spans: the ascending run of ordinals starting at one,
    stopped at the count the entry announced.

    An ordinal that carries no colon at all is only read as a sense marker when
    the entry announced a count, so that the ordinals of ordinary prose ('and
    the first is the sounder reading') cannot open a run of their own."""
    marks = []
    expect = 1
    for m in MARKER_RE.finditer(body):
        if declared and expect > declared:
            break
        if not m.group(3) and not declared:
            continue
        n = marker_number(m.group(1), m.group(2))
        if n == expect:
            marks.append((m.end(), n))
            expect += 1
    spans = []
    for i, (start, n) in enumerate(marks):
        stop = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        spans.append((n, body[start:stop]))
    return spans


def parse_sense(n, span):
    gloss = None
    if not CITE_HEAD.match(span.strip()):
        gm = GLOSS_STOP.match(span)
        if gm:
            gloss = gm.group(1).strip(" .،؛:") or None
    quotes = []
    for q in QUOTE_RE.findall(span):
        if "###" in q or not re.search(r"[ء-ي]", q):
            continue  # footnote numbers and swallowed headers
        quotes.append(re.sub(r"\s+", " ", q).strip(" .،؛:"))
    suras = [h for h in SURA_HINT_RE.findall(span) if h not in HINT_NOISE]
    return {"nr": n, "gloss": gloss, "quotes": quotes, "suras": suras}


def parse_entry(headword, body):
    """The wujuh list follows the declaration formula, so the senses are only
    looked for behind it. A few entries carry the phrase 'cala <n> awjuh' in
    their etymological preamble as well (about a grammatical point, not about
    the Quran), so every occurrence is tried and the first one that is actually
    followed by a numbered list wins; the count of the first occurrence is kept
    when none of them is."""
    decls = list(DECL_RE.finditer(body))
    declared = read_declared(decls[0]) if decls else None
    # a formula that names a number is the better anchor than one that does not
    # ("cala khamsina wajhan afradtuha fi kitab" precedes the real "cala wajhayn")
    for m in sorted(decls, key=lambda m: read_declared(m) is None):
        n = read_declared(m)
        found = [parse_sense(k, sp)
                 for k, sp in sense_spans(body[m.end():], n)]
        if found:
            return {"headword": headword, "declared": n, "senses": found}
    senses = [] if decls else [parse_sense(k, sp)
                               for k, sp in sense_spans(body, None)]
    return {"headword": headword, "declared": declared, "senses": senses}


def main():
    text = normalized_text()
    heads = list(re.finditer(r"### \| (.+)", text))
    entries = []
    for i, h in enumerate(heads):
        title = h.group(1).strip()
        if title.startswith("الباب") or title.startswith("مقد"):
            continue  # chapter header / the author's preface
        body = text[h.end():heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        entry = parse_entry(re.sub(r'[{}"()]', "", title).strip(), body)
        if entry["senses"] or entry["declared"]:
            entries.append(entry)
    OUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    total = sum(len(e["senses"]) for e in entries)
    declared = sum(e["declared"] or 0 for e in entries)
    complete = sum(1 for e in entries if e["declared"] == len(e["senses"]))
    quotes = sum(len(s["quotes"]) for e in entries for s in e["senses"])
    glosses = sum(1 for e in entries for s in e["senses"] if s["gloss"])
    hints = sum(len(s["suras"]) for e in entries for s in e["senses"])
    print(f"entries: {len(entries)}")
    print(f"declared senses: {declared}, parsed senses: {total}")
    print(f"entries with all declared senses found: {complete}/{len(entries)}")
    print(f"quotes: {quotes}, senses with gloss: {glosses}, sura hints: {hints}")


if __name__ == "__main__":
    main()
