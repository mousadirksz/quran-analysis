#!/usr/bin/env python3
"""Resolve the Quran citations in the parsed wujuh works (Yahya ibn Sallam,
al-Damaghani, Ibn al-Jawzi, Abu Hilal al-Askari) to sura:aya references by
matching them against the corpus text in quran.db.

Both the quotes and the corpus text are normalized aggressively (diacritics
stripped, hamza/alef/ya variants collapsed) because the Shamela digitizations
quote from memory-orthography rather than the exact mushaf rasm.

Resolution per quote:
  1. exact normalized substring match against all verses
  2. if multiple verses match, the work's sura hint (when parsed) filters
  3. if no match, retry with the first/last word dropped (quotes often fuse
     the author's framing words onto the quote)
  4. cross-verse match: quotes may span a verse boundary; each sura's verses
     are concatenated and the hit is mapped back to the verse range
  5. fuzzy word-overlap: memory-quotes and Shamela typos deviate in single
     words (qadaytum/qudiyat, fiha/fihima); verses sharing enough skeleton
     words with the quote are accepted when the best hit is clear
  6. short quotes (1-2 words) are located via the sura hint, but only when
     the evidence is unambiguous: a hint must exist, the quote must carry
     lexical content (a bare 'wa-fiha' identifies nothing), and it must
     occur as a whole phrase in exactly one verse of the hinted suras

Layer 6 used to guess without a hint and to accept up to five candidate
verses per quote: 162 rows over the three parsed works, only about half of
which name a verse the quote is demonstrably in. Tightened as above it keeps
15 rows, every one of them a verse that literally contains its quote.

The output is deterministic: every ranking over a Counter is tie-broken on
the lowest sura:aya instead of on Counter insertion order, which follows set
iteration order and therefore PYTHONHASHSEED.

A work whose parsed JSON is missing (a parser not run, or not present in the
checkout) is reported and skipped, not fatal.

Output: sources/resolved_citations.json + statistics on stdout.
"""

import difflib
import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent

DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭـ۟]")


def normalize(s):
    s = s.replace("و\u0670", "ا").replace("\u0670", "")  # dagger alif: rasm -> modern
    s = DIACRITICS.sub("", s)
    s = re.sub("[آأإٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و").replace("ء", "")
    s = s.replace("ة", "ه")
    s = re.sub(r"[^ء-ي ]", " ", s)
    s = re.sub(r"ا+", "ا", s)  # hamza+alef spellings (e.g. ءَابَآئِكَ) collapse
    return re.sub(r"\s+", " ", s).strip()


# classical sura names (incl. variant names used by the two authors) -> number
SURA_NAMES = {
    "الفاتحه": 1, "الحمد": 1, "البقره": 2, "ال عمران": 3, "عمران": 3,
    "النسا": 4, "المايده": 5, "المائده": 5, "الانعام": 6, "الاعراف": 7,
    "الانفال": 8, "التوبه": 9, "براه": 9, "برائه": 9, "براءه": 9,
    "يونس": 10, "هود": 11, "يوسف": 12, "الرعد": 13, "ابراهيم": 14,
    "الحجر": 15, "النحل": 16, "الاسرا": 17, "بني اسرايل": 17,
    "الكهف": 18, "مريم": 19, "طه": 20, "الانبيا": 21, "الحج": 22,
    "المومنون": 23, "المومنين": 23, "النور": 24, "الفرقان": 25,
    "الشعرا": 26, "النمل": 27, "القصص": 28, "العنكبوت": 29, "الروم": 30,
    "لقمان": 31, "السجده": 32, "الم السجده": 32, "الاحزاب": 33,
    "سبا": 34, "فاطر": 35, "الملايكه": 35, "الملائكه": 35, "يس": 36,
    "الصافات": 37, "ص": 38, "الزمر": 39, "غافر": 40, "المومن": 40,
    "فصلت": 41, "حم السجده": 41, "الشوري": 42, "حم عسق": 42,
    "الزخرف": 43, "الدخان": 44, "الجاثيه": 45, "الاحقاف": 46,
    "محمد": 47, "القتال": 47, "الفتح": 48, "الحجرات": 49, "ق": 50,
    "الذاريات": 51, "الطور": 52, "النجم": 53, "القمر": 54, "اقتربت": 54,
    "الرحمن": 55, "الواقعه": 56, "الحديد": 57, "المجادله": 58,
    "الحشر": 59, "الممتحنه": 60, "الصف": 61, "الجمعه": 62,
    "المنافقون": 63, "المنافقين": 63, "التغابن": 64, "الطلاق": 65,
    "التحريم": 66, "الملك": 67, "القلم": 68, "ن": 68, "الحاقه": 69,
    "المعارج": 70, "سال سايل": 70, "نوح": 71, "الجن": 72, "المزمل": 73,
    "المدثر": 74, "القيامه": 75, "الانسان": 76, "الدهر": 76,
    "المرسلات": 77, "النبا": 78, "عم": 78, "النازعات": 79, "عبس": 80,
    "التكوير": 81, "كورت": 81, "الانفطار": 82, "انفطرت": 82,
    "المطففين": 83, "الانشقاق": 84, "انشقت": 84, "البروج": 85,
    "الطارق": 86, "الاعلي": 87, "سبح": 87, "الغاشيه": 88, "الفجر": 89,
    "البلد": 90, "الشمس": 91, "الليل": 92, "الضحي": 93, "الشرح": 94,
    "الم نشرح": 94, "التين": 95, "العلق": 96, "اقرا": 96, "القدر": 97,
    "البينه": 98, "لم يكن": 98, "الزلزله": 99, "اذا زلزلت": 99,
    "العاديات": 100, "القارعه": 101, "التكاثر": 102, "الهاكم": 102,
    "العصر": 103, "الهمزه": 104, "الفيل": 105, "قريش": 106,
    "الماعون": 107, "ارايت": 107, "الكوثر": 108, "الكافرون": 109,
    "النصر": 110, "المسد": 111, "تبت": 111, "الاخلاص": 112,
    "الفلق": 113, "الناس": 114,
    # archaic names, as used by Yahya ibn Sallam (2nd c. AH): suras are cited
    # by their opening words rather than by the later canonical titles
    "سبحان": 17, "بني اسراييل": 17, "طاه": 20, "الم تنزيل": 32,
    "الم السجده": 32, "تنزيل السجده": 32, "المين": 36,
    "حم السجده": 41, "حمالسجده": 41, "حم عساقا": 42, "حمعساقا": 42,
    "حمعاساقا": 42, "عساقا": 42, "حم الزخرف": 43, "حمالزخرف": 43,
    "حم الدخان": 44, "حمالدخان": 44, "حم المومن": 40, "حمالمومن": 40,
    "حم الاحقاف": 46, "حمالاحقاف": 46, "الذين كفروا": 47, "اقتربت الساعه": 54,
    "قد سمع": 58, "الحواريون": 61, "قل اوحي": 72, "هل اتي": 76,
    "لا اقسم": 75, "عم يتسايلون": 78, "هل اتاك": 88, "الليل اذا يغشي": 92,
    "لم يكن الذين كفروا": 98, "اذا زلزلت الارض": 99, "الهاكم التكاثر": 102,
    "اريت الذي": 107, "قل يا ايها الكافرون": 109, "تبت يدا": 111,
    "قل هو الله احد": 112, "قل اعوذ برب الفلق": 113, "قل اعوذ برب الناس": 114,
}


HINT_NOISE = re.compile(r"^(?:اخر |اول |سوره |قوله |وقوله |تفسير )+")


def hint_to_sura(raw):
    """Map a parsed sura hint to a number, tolerating the framing words the
    authors wrap around it ('in the end of sura Bara'a', 'his word in
    al-Zumar') and trailing words swept up by the citation regex."""
    n = normalize(raw)
    n = HINT_NOISE.sub("", n).strip()
    while n:
        if n in SURA_NAMES:
            return SURA_NAMES[n]
        parts = n.split()
        if len(parts) == 1:
            return None
        n = " ".join(parts[:-1])  # drop trailing words that are not the name
    return None


def load_verses():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()
    cur.execute("""SELECT surah, ayah, GROUP_CONCAT(form_ar, '') FROM
        (SELECT surah, ayah, word, GROUP_CONCAT(form_ar,'') form_ar
         FROM corpus GROUP BY surah, ayah, word ORDER BY surah, ayah, word, segment)
        GROUP BY surah, ayah""")
    rows = cur.fetchall()
    # rebuild with spaces between words
    cur.execute("""SELECT surah, ayah, word, GROUP_CONCAT(form_ar,'')
        FROM corpus GROUP BY surah, ayah, word ORDER BY surah, ayah, word, segment""")
    verses = {}
    for s, a, w, form in cur.fetchall():
        verses.setdefault((s, a), []).append(form)
    return {k: normalize(" ".join(v)) for k, v in verses.items()}


def skeleton(s):
    """Consonantal skeleton: long vowels stripped, so that Uthmani rasm and
    modern orthography (slwh/slah, smwt/smawat) collapse together."""
    return re.sub(r"\s+", " ", re.sub("[اوي]", "", s)).strip()


def build_sura_concat(skel_verses):
    """Per sura: concatenated skeleton text with verse offsets, for quotes
    that span a verse boundary."""
    by_sura = {}
    for (s, a) in sorted(skel_verses):
        by_sura.setdefault(s, []).append((a, skel_verses[(s, a)]))
    concat = {}
    for s, items in by_sura.items():
        text, spans = "", []
        for a, v in items:
            start = len(text)
            text += v + " "
            spans.append((start, len(text), a))
        concat[s] = (text, spans)
    return concat


def build_word_index(skel_verses):
    idx = {}
    for k, v in skel_verses.items():
        for w in set(v.split()):
            if len(w) >= 2:
                idx.setdefault(w, set()).add(k)
    return idx


def cross_verse_match(qs, concat, sura_hints):
    hits = []
    suras = sura_hints or concat.keys()
    for s in suras:
        if s not in concat:
            continue
        text, spans = concat[s]
        pos = text.find(qs)
        while pos != -1:
            ayahs = [a for (st, en, a) in spans if st < pos + len(qs) and en > pos]
            if ayahs:
                hits.append((s, ayahs))
            pos = text.find(qs, pos + 1)
    return hits


def top_votes(votes, n):
    """The n best-voted verses. Counter.most_common breaks ties in insertion
    order, which follows set iteration order and therefore PYTHONHASHSEED;
    ranking on (-votes, sura, aya) makes a tied race resolve to the earliest
    verse in every run."""
    return sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def fuzzy_match(qs, word_idx, sura_hints):
    words = [w for w in qs.split() if len(w) >= 2]
    if len(words) < 3:
        return None
    from collections import Counter
    votes = Counter()
    for w in sorted(set(words)):
        for k in sorted(word_idx.get(w, ())):
            votes[k] += 1
    if sura_hints:
        hinted = Counter({k: v for k, v in votes.items() if k[0] in sura_hints})
        if hinted:
            votes = hinted
    if not votes:
        return None
    best = top_votes(votes, 2)
    score = best[0][1] / len(set(words))
    margin = (best[0][1] - best[1][1]) / len(set(words)) if len(best) > 1 else 1.0
    if score >= 0.7 and (margin >= 0.15 or len(best) == 1):
        return [best[0][0]]
    return None


# Particles, pronouns, relatives and demonstratives in their normalized
# shape, including the preposition+pronoun fusions ('fiha', 'lahum') the
# editors like to fuse onto a quote. None of these narrows a quote down: they
# occur in hundreds of verses, and a quote made of them alone is usually the
# editor's own connective rather than Quranic text.
FUNCTION_WORDS = {
    "من", "في", "علي", "الي", "عن", "مع", "عند", "بين", "حتي", "لدي",
    "اذا", "اذ", "ان", "انا", "انت", "انتم", "انتما", "انتن", "نحن",
    "هو", "هي", "هم", "هن", "هما", "ما", "لا", "لم", "لن", "لو", "قد",
    "ثم", "او", "ام", "بل", "يا", "اي", "كل", "بعض", "غير", "كما", "كذلك",
    "الذي", "التي", "الذين", "اللاتي", "اللايي", "ذلك", "تلك", "ذلكم",
    "هذا", "هذه", "هولا", "اوليك", "به", "بها", "بهم", "بهما",
    "له", "لها", "لهم", "لهما", "لك", "لكم", "لنا", "لي", "منه", "منها",
    "منهم", "فيه", "فيها", "فيهم", "فيهما", "عليه", "عليها", "عليهم",
    "اليه", "اليها", "اليهم", "انه", "انها", "انهم", "بعد", "قبل", "دون",
}

MIN_SOLO_LEN = 5  # a one-word quote must at least be a long word


def _stem(tok):
    """Strip the clitics that hide a function word ('wa-fiha' -> 'fiha'),
    but never so far that a content word is eaten ('allah' keeps its alif
    lam, 'lahu' is not shortened to a single letter)."""
    if len(tok) > 3 and tok[0] in "وف":
        tok = tok[1:]
    if len(tok) > 3 and tok[0] in "بلك":
        tok = tok[1:]
    if len(tok) > 4 and tok.startswith("ال"):
        tok = tok[2:]
    return tok


def content_words(qnorm):
    """The tokens of a quote that carry lexical content, i.e. that make the
    phrase identifiable at all."""
    out = []
    for tok in qnorm.split():
        stem = _stem(tok)
        if tok in FUNCTION_WORDS or stem in FUNCTION_WORDS or len(stem) < 3:
            continue
        out.append(stem)
    return out


def short_match(qnorm, verses, sura_hints):
    """Place a short quote only on unambiguous evidence: a parsed sura hint,
    enough lexical content to identify anything, and exactly one verse in the
    hinted suras containing the quote as a whole phrase.

    The looser predecessor (no hint needed, skeleton fallback, up to five
    candidates kept) placed 162 rows of which barely half named a verse the
    quote is demonstrably in, next to layers scoring 96-100%. Returning
    nothing is the better answer for a quote this thin."""
    if not sura_hints:
        return None
    content = content_words(qnorm)
    if not content:
        return None
    if len(content) < 2 and len(content[0]) < MIN_SOLO_LEN:
        return None
    q = " " + qnorm + " "
    hits = [k for k, v in verses.items()
            if k[0] in sura_hints and q in " " + v + " "]
    return hits if len(hits) == 1 else None


FRAMING = re.compile(r"^(?:و?كقوله|و?قوله|قال|ومثلها|مثلها|ونحوها|نحوها)?"
                     r"(?: تعالي| سبحانه| عز وجل)?(?: في سوره [ء-ي]+)? ?")


def clean_quote(qnorm):
    """Cut the author's commentary off the quote: everything from yacni/ay
    onwards, and leading citation formulas."""
    qnorm = re.split(r" يعني | اي | مثلها | ونحوه| كقوله| وقوله", qnorm)[0]
    qnorm = FRAMING.sub("", qnorm)
    return qnorm.strip()


def is_commentary(qnorm):
    """Fragments like 'yacni X' or 'and likewise in sura Y' are the author
    speaking, not the Quran — sloppy quote marks in the digitization."""
    return bool(re.match(
        r"^(يعني|اي |مثلها|ونحوها?|نحوها?|و?كقوله|وقوله|قوله) |^في سوره ",
        qnorm)) or not clean_quote(qnorm)


def prefix_match(qnorm, verses, skel_verses):
    """Longest quote prefix that is a verse substring (quote + fused
    commentary tails)."""
    words = qnorm.split()
    for k in range(len(words) - 1, 2, -1):
        t = " ".join(words[:k])
        hits = [key for key, v in verses.items() if t in v]
        if hits:
            return hits
        ts = skeleton(t)
        if len(ts.replace(" ", "")) >= 8:
            hits = [key for key, v in skel_verses.items() if ts in v]
            if hits:
                return hits
    return None


def verify_fuzzy(qs, key, skel_verses):
    ratio = difflib.SequenceMatcher(
        None, qs.replace(" ", ""),
        skel_verses[key].replace(" ", "")).find_longest_match()
    return ratio.size


def resolve_quote(qnorm, verses, skel_verses, concat, word_idx, sura_hints):
    if is_commentary(qnorm):
        return None, "not_quote"
    qnorm = clean_quote(qnorm)
    if " - " in qnorm:  # composite quote: resolve the parts separately
        refs = []
        for part in qnorm.split(" - "):
            r, st = resolve_quote(part.strip(), verses, skel_verses, concat,
                                  word_idx, sura_hints)
            if r and st != "ambiguous":
                refs += r
        if refs:
            return refs, "composite"
    if len(qnorm) < 8:  # too short to be distinctive without a sura hint
        hits = short_match(qnorm, verses, sura_hints)
        if hits:
            return hits, "short_hint"
        return None, "too_short"
    hits = [k for k, v in verses.items() if qnorm in v]
    if not hits:
        words = qnorm.split()
        for trial in (words[1:], words[:-1], words[1:-1]):
            if len(trial) >= 3:
                t = " ".join(trial)
                hits = [k for k, v in verses.items() if t in v]
                if hits:
                    break
    if not hits:
        # tier 2: skeleton match, tolerant of rasm/orthography differences
        qs = skeleton(qnorm)
        if len(qs.replace(" ", "")) >= 6:
            hits = [k for k, v in skel_verses.items() if qs in v]
            if not hits:
                words = qs.split()
                for trial in (words[1:], words[:-1], words[1:-1]):
                    if len(trial) >= 3:
                        t = " ".join(trial)
                        hits = [k for k, v in skel_verses.items() if t in v]
                        if hits:
                            break
            if not hits:
                # tier 3: space-insensitive (mushaf joins e.g. يٰأبت)
                qss = qs.replace(" ", "")
                hits = [k for k, v in skel_verses.items()
                        if qss in v.replace(" ", "")]
    if not hits:
        qs = skeleton(qnorm)
        cross = cross_verse_match(qs, concat, sura_hints)
        if len(cross) == 1:
            s_, ayahs = cross[0]
            return [(s_, a) for a in ayahs], "cross_verse"
        fz = fuzzy_match(qs, word_idx, sura_hints)
        if fz:
            return fz, "fuzzy"
        hits = prefix_match(qnorm, verses, skel_verses)
        if hits and len(hits) <= 5:
            return hits, "prefix"
        # last resort: best word-overlap candidate verified by longest
        # common substring on the spaceless skeleton
        from collections import Counter
        votes = Counter()
        for w in sorted({w for w in qnorm.split() if len(w) >= 3}):
            for key, v in verses.items():
                if sura_hints and key[0] not in sura_hints:
                    continue
                if w in v:
                    votes[key] += 1
        best = top_votes(votes, 3)
        qss = qs.replace(" ", "")
        for key, _ in best:
            if len(qss) >= 10 and verify_fuzzy(qs, key, skel_verses) >= max(8, int(len(qss) * 0.55)):
                return [key], "fuzzy"
        hits = short_match(qnorm, verses, sura_hints)
        if hits:
            return hits, "short_hint"
        return None, "no_match"
    if len(hits) == 1:
        return hits, "unique"
    hinted = [h for h in hits if h[0] in sura_hints]
    if len(set(h[0] for h in hinted)) == 1 and hinted:
        return hinted, "hint_resolved"
    return hits, "ambiguous"


# The parsed wujuh works, each written by its own parser into sources/ in the
# same shape (entries with headword, declared, senses of nr/gloss/quotes/suras).
WORKS = (("damaghani", "damaghani_wujuh.json"),
         ("ibnjawzi", "ibnjawzi_wujuh.json"),
         ("ibnsallam", "tasarif_wujuh.json"),
         ("askari", "askari_wujuh.json"))


def main():
    verses = load_verses()
    skel_verses = {k: skeleton(v) for k, v in verses.items()}
    concat = build_sura_concat(skel_verses)
    word_idx = build_word_index(skel_verses)
    out = {}
    for work, fn in WORKS:
        path = HERE / "sources" / fn
        if not path.exists():
            # a parser that has not run (or is not in this checkout) costs
            # this work's citations, not the whole resolution run
            print(f"{work}: sources/{fn} not found, skipped")
            continue
        entries = json.loads(path.read_text(encoding="utf-8"))
        stats = {"unique": 0, "hint_resolved": 0, "ambiguous": 0,
                 "cross_verse": 0, "fuzzy": 0, "short_hint": 0,
                 "prefix": 0, "composite": 0, "not_quote": 0,
                 "no_match": 0, "too_short": 0}
        resolved_entries = []
        for e in entries:
            r_senses = []
            for sense in e["senses"]:
                hints = {n for n in (hint_to_sura(s)
                                     for s in sense.get("suras", [])) if n}
                r_quotes = []
                for q in sense["quotes"]:
                    refs, status = resolve_quote(normalize(q), verses, skel_verses,
                                                 concat, word_idx, hints)
                    stats[status] += 1
                    # 'ambiguous' quotes can have far more candidates than
                    # these ten; the list is a sample of the candidates, not
                    # the attestation set, and consumers must treat it so
                    r_quotes.append({"quote": q, "status": status,
                                     "refs": [f"{s}:{a}" for s, a in (refs or [])]})
                r_senses.append({"nr": sense["nr"], "gloss": sense["gloss"],
                                 "quotes": r_quotes})
            resolved_entries.append({"headword": e["headword"],
                                     "declared": e["declared"], "senses": r_senses})
        out[work] = resolved_entries
        total = sum(stats.values())
        ok = (stats["unique"] + stats["hint_resolved"] + stats["cross_verse"]
              + stats["fuzzy"] + stats["short_hint"] + stats["ambiguous"]
              + stats["prefix"] + stats["composite"])
        real = total - stats["not_quote"]
        pct = f"{ok / real * 100:.0f}%" if real else "n/a"
        print(f"{work}: {total} quote-marked spans, {stats['not_quote']} are "
              f"commentary -> {real} real quotes, resolved {ok} ({pct})")
        print(f"  {stats}")
    (HERE / "sources" / "resolved_citations.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
