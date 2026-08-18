#!/usr/bin/env python3
"""Build the `wujuh` table in quran.db from the four parsed classical works
(Yahya ibn Sallam's Tasarif, Abu Hilal al-Askari's Wujuh wa-l-Naza'ir,
al-Damaghani's Qamus, Ibn al-Jawzi's Nuzhat al-Acyun) and their resolved
citations.

One row per (citation, verse) pair: (work, headword, root, sense_nr,
gloss, surah, ayah, word), so polysemy queries like "which wujuh does
huda have, and which word of which verse attests which sense" run
directly against the database.

The entry's root is inferred from the data itself: among the roots of the
verses the entry cites, take the one that occurs in the most cited verses
AND whose letters are compatible with the headword. This works uniformly
for al-Damaghani's spaced root letters ("أت ى") and Ibn al-Jawzi's whole
words ("الأذان").

Word-level linkage
------------------
A wajh belongs to one word, not to a whole verse, and a verse may contain
the polysemous word more than once. Each row therefore also carries the
corpus segment it is about: `word` (word number within the verse),
`corpus_id` (corpus.id of that word's STEM segment) and `form_ar` (the
full word, all its segments concatenated). The target word is the word
whose root equals the entry's root; when the root occurs in several words
of the verse, the cited span decides. The span is located by laying the
normalized quote against the verse's consecutive words: exact match first,
then on the consonantal skeleton, then a difflib alignment for quotes the
digitization garbled. `word_status` records how (or why not) the link was
made:

  root_unique     one word in the verse carries the entry's root
  quote_span      several did; exactly one falls inside the cited span
  root_absent     the entry's root does not occur in this verse
  entry_root_unknown  no root could be inferred for the entry
  root_unverified the inferred root is not corroborated by the headword
                  (particle entries, where the root is an artefact)
  span_unknown    several candidates, quote could not be located
  multi_in_span   several candidates inside the cited span
  root_outside_quote  candidates exist, but none inside the cited span

The last six leave word/corpus_id/form_ar NULL rather than guess. For
entry_root_unknown and root_unverified `root_ar` is NULL as well: an
untrustworthy root is not written out, because a stored root reads as a
claim about the entry and would be counted as one.

Confidence
----------
Three columns describe how solid a row is. `match_status` keeps the
fine-grained provenance from the resolver. `candidate_count` is how many
verses the resolver returned for that one citation, i.e. how many rows
this table gives it - the breadth of a citation is thus visible in the
data instead of hidden behind its first row. `confidence` combines the
two into how much weight a row may carry in counts.

The statuses differ in how the reference was obtained:

  located        unique, cross_verse, prefix, hint_resolved - the quoted
                 words themselves were found in the mushaf
  reconstructed  fuzzy, short_hint, edition_jk - the wording had to be
                 approximated (word overlap, a sura hint, or the second
                 edition), so the verse may be the wrong one
  listed         ambiguous - the quote occurs in several verses and the
                 work does not say which, so every match is listed

But the status alone does not say where a citation landed: a hint or a
prefix match regularly leaves two or three verses standing, and a
citation pointing at one verse is stronger evidence than one pointing at
three. Confidence is therefore capped by candidate_count:

  1 verse     high  (located) / medium (reconstructed) / low (listed)
  2-3 verses  medium at best
  4+ verses   low

So `high` means the quoted words were found and in exactly one place;
`medium` means the verse is likely but not settled; `low` rows are
candidates rather than attestations and should be excluded from
attestation counts. cross_verse and composite are exempt from the cap:
their several verses are the consecutive parts of one quote, not
alternatives to choose between.

Note that resolve_citations.py truncates very long candidate lists (at
ten verses at the time of writing), so candidate_count is what reached
this table, which for the widest ambiguous citations is a lower bound.
This script itself drops nothing: every reference it is given becomes a
row.

Idempotent: builds every row first, then drops and rebuilds the table.
A run that yields no rows at all reports that and leaves the existing
table alone. Requires resolved_citations.json (from resolve_citations.py
and substantiate_jk.py).
"""

import difflib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent

# statuses from resolve_citations.py / substantiate_jk.py that carry usable
# verse references, with the best confidence each may reach; 'ambiguous' rows
# list every verse containing the quoted phrase, which for wujuh purposes is
# what the author's "and its likes" intends, but never as an attestation
BEST_CONFIDENCE = {
    "unique": "high", "hint_resolved": "high", "prefix": "high",
    "cross_verse": "high", "composite": "high",
    "fuzzy": "medium", "short_hint": "medium", "edition_jk": "medium",
    "ambiguous": "low",
}

# statuses whose several verses are the parts of one continuous quote instead
# of alternatives; for them a high candidate_count is not uncertainty
SPAN_STATUSES = {"cross_verse", "composite"}

TIERS = ("high", "medium", "low")


def confidence(status, n_candidates):
    """How much weight one row may carry: the status' ceiling, lowered when
    the citation left several verses standing (see the module docstring)."""
    best = BEST_CONFIDENCE[status]
    if status in SPAN_STATUSES or n_candidates <= 1:
        return best
    cap = "medium" if n_candidates <= 3 else "low"
    return max(best, cap, key=TIERS.index)


DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭـ۟]")


def normalize(s):
    """Same normalization the resolver used, applied per word so that the
    character offsets of a match map back onto word numbers."""
    s = s.replace("وٰ", "ا").replace("ٰ", "")
    s = DIACRITICS.sub("", s)
    s = re.sub("[آأإٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و").replace("ء", "")
    s = s.replace("ة", "ه")
    s = re.sub(r"[^ء-ي ]", " ", s)
    s = re.sub(r"ا+", "ا", s)
    return re.sub(r"\s+", " ", s).strip()


def skeleton(s):
    return re.sub(r"\s+", " ", re.sub("[اوي]", "", s)).strip()


FRAMING = re.compile(r"^(?:و?كقوله|و?قوله|قال|ومثلها|مثلها|ونحوها|نحوها)?"
                     r"(?: تعالي| سبحانه| عز وجل)?(?: في سوره [ء-ي]+)? ?")


def clean_quote(qnorm):
    qnorm = re.split(r" يعني | اي | مثلها | ونحوه| كقوله| وقوله", qnorm)[0]
    return FRAMING.sub("", qnorm).strip()


def norm_letters(s):
    s = re.sub("[آأإٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و").replace("ء", "ا")
    s = s.replace("ة", "").replace("ال", "", 1) if s.startswith("ال") else s
    return re.sub(r"[^ء-ي]", "", s)


def strong(s):
    return frozenset(s) - frozenset("اوي")


def compatible(root_n, head_n, spaced):
    """al-Damaghani's spaced-root headwords must match the root's strong
    letters exactly; Ibn al-Jawzi's whole-word headwords (derived forms like
    الاستطاعة) only need to contain them."""
    if spaced:
        return strong(root_n) == strong(head_n)
    missing = 0
    for ch in root_n:
        if ch not in head_n:
            if ch in "اوي":  # weak letters morph freely
                missing += 1
            else:
                return False
    return missing <= 1


def root_trusted(root, head):
    """Whether the inferred root may drive the word link. The frequency
    fallback in infer_root() also fires for entries on particles (thumma,
    can, illa), which have no root at all; the root it then picks is an
    artefact of the cited verses and would link the wajh to an unrelated
    word. Requiring the headword to corroborate the root's letters keeps
    typo'd and compound headwords (dhhb/dhahaba, "al-hasana wa-l-sayyi'a")
    while rejecting those artefacts."""
    return compatible(norm_letters(root), norm_letters(head), spaced=False)


def infer_root(head, verse_refs, verse_roots):
    head_n = norm_letters(head)
    spaced = " " in head.strip()
    counts = Counter()
    for ref in verse_refs:
        for r in verse_roots.get(ref, ()):
            counts[r] += 1
    # ties are broken alphabetically so the build is reproducible
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for root, n in ranked[:40]:
        if compatible(norm_letters(root), head_n, spaced):
            return root, n / len(verse_refs)
    # fallback for typo'd headwords: a root shared by most cited verses is
    # almost certainly the entry's subject
    if ranked:
        root, n = ranked[0]
        if n / len(verse_refs) >= 0.6 and len(verse_refs) >= 3:
            return root, n / len(verse_refs)
    return None, 0.0


class Verse:
    """A verse as a token stream: normalized tokens with the word number and
    the char offset each token has in the joined verse text, once in full
    orthography and once as consonantal skeleton."""

    def __init__(self, words, roots_by_word):
        self.words = words                      # {word_nr: full form_ar}
        self.roots_by_word = roots_by_word      # {root: {word_nr, ...}}
        self.full = self._layer(lambda t: t, words)
        self.skel = self._layer(skeleton, words)

    @staticmethod
    def _layer(fn, words):
        toks, nums, starts = [], [], []
        pos = 0
        for w in sorted(words):
            for tok in fn(normalize(words[w])).split():
                toks.append(tok)
                nums.append(w)
                starts.append(pos)
                pos += len(tok) + 1
        return " ".join(toks), nums, starts

    def _find(self, layer, q):
        """Word spans where q sits on token boundaries in this layer."""
        text, nums, starts = layer
        spans = []
        for i, st in enumerate(starts):
            end = st + len(q)
            if not text.startswith(q, st):
                continue
            if end != len(text) and text[end] != " ":
                continue
            j = i
            while j + 1 < len(starts) and starts[j + 1] < end:
                j += 1
            spans.append((nums[i], nums[j]))
        return spans

    def _align(self, q):
        """Last resort: difflib alignment of the quote's skeleton words onto
        the verse's, for quotes the digitization garbled or that run over a
        verse boundary."""
        text, nums, _ = self.skel
        toks = text.split()
        qtoks = q.split()
        if not qtoks or not toks:
            return []
        sm = difflib.SequenceMatcher(None, toks, qtoks, autojunk=False)
        blocks = [b for b in sm.get_matching_blocks() if b.size]
        if not blocks:
            return []
        solid = [b for b in blocks if b.size >= 2] or [max(blocks, key=lambda b: b.size)]
        matched = sum(b.size for b in solid)
        if matched < 2 or matched / len(qtoks) < 0.4:
            return []
        lo = min(b.a for b in solid)
        hi = max(b.a + b.size - 1 for b in solid)
        return [(nums[lo], nums[hi])]

    def spans(self, qnorm):
        for layer, q in ((self.full, qnorm), (self.skel, skeleton(qnorm))):
            if len(q.replace(" ", "")) >= 3:
                found = self._find(layer, q)
                if found:
                    return found
        return self._align(skeleton(qnorm))


def load_verses(cur):
    """Per verse: the full word forms, the stem segment id per root, and the
    set of roots attested."""
    cur.execute("SELECT surah, ayah, word, segment, form_ar, root_ar, segment_type"
                " FROM corpus ORDER BY surah, ayah, word, segment")
    forms, stems, roots = {}, {}, {}
    for s, a, w, _seg, form, root, styp in cur.fetchall():
        key = (s, a)
        forms.setdefault(key, {})
        forms[key][w] = forms[key].get(w, "") + (form or "")
        if root and styp == "STEM":
            stems.setdefault(key, {}).setdefault(root, set()).add(w)
            roots.setdefault(key, set()).add(root)
    return forms, stems, roots


def load_stem_ids(cur):
    cur.execute("SELECT id, surah, ayah, word, root_ar FROM corpus"
                " WHERE segment_type='STEM' AND root_ar!=''")
    ids = {}
    for i, s, a, w, root in cur.fetchall():
        ids[(s, a, w, root)] = i
    return ids


def locate_word(verse, root, trusted, qnorm):
    """Return (word_nr, word_status) for the word of this verse the wajh is
    about. Never guesses: ambiguity leaves the word unset. `trusted` is
    root_trusted() for the entry, computed once by the caller because it also
    decides whether the root itself is written out."""
    if not root:
        return None, "entry_root_unknown"
    if not trusted:
        return None, "root_unverified"
    cands = sorted(verse.roots_by_word.get(root, ()))
    if not cands:
        return None, "root_absent"
    if len(cands) == 1:
        return cands[0], "root_unique"
    spans = verse.spans(qnorm)
    if not spans:
        return None, "span_unknown"
    inside = [w for w in cands if any(lo <= w <= hi for lo, hi in spans)]
    if len(inside) == 1:
        return inside[0], "quote_span"
    if inside:
        return None, "multi_in_span"
    return None, "root_outside_quote"


def main():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()

    forms, stems, verse_roots = load_verses(cur)
    stem_ids = load_stem_ids(cur)
    verses = {key: Verse(words, stems.get(key, {}))
              for key, words in forms.items()}

    resolved = json.loads((HERE / "sources" / "resolved_citations.json")
                          .read_text(encoding="utf-8"))

    # everything is built before the table is touched, so a run that yields
    # nothing (an empty or unusable resolved_citations.json) leaves the
    # previous table in place instead of replacing it with an empty one
    rows = []
    n_entries = entries_with_root = entries_root_trusted = 0
    for work, entries in resolved.items():
        for e in entries:
            refs = []
            for sense in e["senses"]:
                for q in sense["quotes"]:
                    if q["status"] in BEST_CONFIDENCE:
                        refs += [tuple(map(int, r.split(":"))) for r in q["refs"]]
            if not refs:
                continue
            n_entries += 1
            root, _cov = infer_root(e["headword"], refs, verse_roots)
            if root:
                entries_with_root += 1
            # an unverified root is an artefact of the cited verses (particle
            # entries have no root at all), so it drives nothing and is not
            # written out either
            trusted = bool(root) and root_trusted(root, e["headword"])
            entries_root_trusted += 1 if trusted else 0
            stored_root = root if trusted else None
            for sense in e["senses"]:
                for q in sense["quotes"]:
                    if q["status"] not in BEST_CONFIDENCE:
                        continue
                    qnorm = clean_quote(normalize(q["quote"]))
                    n_cand = len(q["refs"])
                    conf = confidence(q["status"], n_cand)
                    for ref in q["refs"]:
                        s, a = map(int, ref.split(":"))
                        verse = verses.get((s, a))
                        if verse is None:
                            continue
                        word, wstatus = locate_word(verse, root, trusted, qnorm)
                        rows.append((
                            work, e["headword"], stored_root, sense["nr"],
                            sense["gloss"], q["quote"], s, a,
                            word,
                            stem_ids.get((s, a, word, stored_root)) if word else None,
                            verse.words.get(word) if word else None,
                            q["status"], n_cand, conf, wstatus))

    if not rows:
        con.close()
        raise SystemExit("no citations with usable verse references in "
                         "sources/resolved_citations.json; wujuh table left "
                         "untouched (re-run resolve_citations.py)")

    cur.execute("DROP TABLE IF EXISTS wujuh")
    cur.execute("""CREATE TABLE wujuh (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work TEXT, headword TEXT, root_ar TEXT,
        sense_nr INTEGER, gloss TEXT,
        quote TEXT, surah INTEGER, ayah INTEGER,
        word INTEGER, corpus_id INTEGER, form_ar TEXT,
        match_status TEXT, candidate_count INTEGER,
        confidence TEXT, word_status TEXT)""")
    cur.executemany(
        "INSERT INTO wujuh (work, headword, root_ar, sense_nr, gloss, quote,"
        " surah, ayah, word, corpus_id, form_ar, match_status,"
        " candidate_count, confidence, word_status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_wujuh_root ON wujuh(root_ar)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wujuh_verse ON wujuh(surah, ayah)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_wujuh_corpus ON wujuh(corpus_id)")
    con.commit()

    linked = sum(1 for r in rows if r[8] is not None)
    multi = sum(1 for r in rows if r[12] > 1)
    conf = Counter(r[13] for r in rows)
    cur.execute("SELECT COUNT(DISTINCT root_ar) FROM wujuh WHERE root_ar IS NOT NULL")
    print(f"entries with resolved citations: {n_entries}, root inferred: "
          f"{entries_with_root}, of which trusted: {entries_root_trusted}")
    print(f"wujuh rows (citation x verse): {len(rows)}, "  # rows is non-empty here
          f"linked to a word: {linked} ({linked / len(rows):.1%}), "
          f"from citations with several candidate verses: {multi}")
    print("confidence: " + ", ".join(f"{k} {conf[k]}" for k in TIERS))
    print("distinct roots covered:", cur.fetchone()[0])
    con.close()


if __name__ == "__main__":
    main()
