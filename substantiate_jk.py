#!/usr/bin/env python3
"""Substantiate unresolved Ibn al-Jawzi citations from the second,
independent digitization of the same work (the JK edition in OpenITI).

The Shamela and JK editions were typed independently from different print
editions, so their corruptions do not overlap: a quote that is garbled or
truncated in one is usually intact in the other (Shamela 'wa-dhkur bacda
ummah' vs JK 'wa-ddakara bacda ummah', 12:45). This script extracts every
quoted span from the JK edition, resolves each against the corpus with the
same resolver, and uses those located quotes as *candidates* for the quotes
the resolver could not place. A candidate is only adopted (status
'edition_jk') when the unresolved quote itself is demonstrably in the verse
the candidate names.

The evidence chain per adopted quote, in order:
  1. the quote must carry locating information at all: at least two content
     words (words whose skeleton occurs in at most MAX_DF verses; a bare
     'wa-fiha' or 'qala' identifies nothing) and 8 skeleton characters
  2. a JK quote must resemble it closely on the consonantal skeleton:
     character similarity >= MIN_SIM, tolerant of a fragment being quoted
     inside the longer of the two, so that single-letter corruptions
     (dhal/dal, tacmtum/taciimtum) do not break the pairing
  3. verification against the verse text itself, not merely against the JK
     quote: >= MIN_ORDER of the quote's skeleton characters must recur in
     the candidate verse in order, >= MIN_RUN of them in one contiguous run,
     and >= MIN_WORDS of its content words must be present (near-matching
     one verse word), which is what rules out a verse that merely shares
     scattered letters
  4. uniqueness: if two different candidate verses survive verification the
     quote is left unresolved rather than assigned to the first one

Why so defensive: the previous version adopted any JK counterpart with 0.6
bag-of-words overlap and no verification. That substantiated 91 quotes of
which about 97% named a verse the quote does not occur in; 36 of them
collapsed onto 17:69 alone because the editorial word 'wa-fiha' overlapped
with a JK quote. Re-measured on the same input, the chain above substantiates
6 quotes / 8 references, all six of them checked by hand against the verse
text and correct, and 17:69 no longer appears. Few and right beats many and
wrong: the rest stay 'no_match'/'too_short', which downstream code handles.

Updates sources/resolved_citations.json in place; re-running over an
already-substantiated file is a no-op.
"""

import difflib
import json
import re
from pathlib import Path

import resolve_citations as rc

HERE = Path(__file__).parent
JK = HERE / "sources" / "ibnjawzi_nuzhat_jk.txt"

MAX_DF = 300      # a skeleton word in >5% of the 6236 verses locates nothing
MIN_CONTENT = 2   # content words the quote must carry to be matchable
MIN_SKEL = 8      # skeleton characters, same reason
MIN_SIM = 0.80    # quote vs JK quote, consonantal skeleton
MIN_ORDER = 0.90  # quote skeleton characters recurring in the verse, in order
MIN_RUN = 0.50    # ... of which this share in one contiguous run
MIN_WORDS = 0.60  # content words of the quote present in the verse


def jk_quotes():
    lines = []
    for ln in JK.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        if not ln.startswith("###"):
            ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        lines.append(ln.strip())
    text = " ".join(lines)
    text = re.sub(r"PageV\d+P\d+", " ", text)
    text = re.sub(r"\( ?\d+ / [ء-يa-z] ?\)", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text)
    # the JK edition marks Quran quotes explicitly as @QB@ ... @QE@
    return [m.group(1).strip()
            for m in re.finditer(r"@QB@ (.{4,200}?) @QE@", text)]


def matcher(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False)


def in_order(a, b):
    """Share of a's characters that recur in b in the same order."""
    return sum(m.size for m in matcher(a, b).get_matching_blocks()) / len(a) if a else 0.0


def longest_run(a, b):
    """Share of a covered by the longest contiguous block shared with b."""
    return matcher(a, b).find_longest_match().size / len(a) if a else 0.0


def similarity(a, b):
    """Skeleton similarity of two quotes, tolerant of one being a fragment of
    the other: the editions differ in where the editor cut the quote."""
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return max(matcher(a, b).ratio(), in_order(short, long))


class Locator:
    """Corpus-side lookup: content words, and verification of a quote against
    the verses a candidate names."""

    def __init__(self):
        self.verses = rc.load_verses()
        self.skel = {k: rc.skeleton(v) for k, v in self.verses.items()}
        self.concat = rc.build_sura_concat(self.skel)
        self.word_idx = rc.build_word_index(self.skel)
        self.df = {w: len(keys) for w, keys in self.word_idx.items()}

    def content(self, qnorm):
        return [w for w in rc.skeleton(qnorm).split()
                if len(w) >= 2 and self.df.get(w, 0) <= MAX_DF]

    def prepare(self, quote):
        """(skeleton string, content words) of a quote, or None when the
        quote carries too little to locate anything."""
        qnorm = rc.clean_quote(rc.normalize(quote))
        words = self.content(qnorm)
        skel = rc.skeleton(qnorm).replace(" ", "")
        if len(words) < MIN_CONTENT or len(skel) < MIN_SKEL:
            return None
        return skel, words

    def resolve(self, quote):
        qnorm = rc.normalize(quote)
        refs, status = rc.resolve_quote(qnorm, self.verses, self.skel,
                                        self.concat, self.word_idx, set())
        # only the tiers that locate a quote by its own wording; the hinted
        # and fuzzy tiers are guesses and would propagate their guess
        if refs and status in ("unique", "cross_verse"):
            return tuple(sorted(refs))
        return None

    def verifies(self, skel, words, refs):
        """Is this quote demonstrably in these verses?"""
        text = "".join(self.skel[k].replace(" ", "") for k in refs)
        verse_words = set(" ".join(self.skel[k] for k in refs).split())
        if in_order(skel, text) < MIN_ORDER or longest_run(skel, text) < MIN_RUN:
            return False
        present = sum(any(w == v or (len(w) >= 4 and w in v)
                          or matcher(w, v).ratio() >= 0.8 for v in verse_words)
                      for w in words)
        return present / len(words) >= MIN_WORDS


def jk_candidates(loc):
    """Located JK quotes, as (skeleton, refs) pairs."""
    out = []
    for quote in jk_quotes():
        prepared = loc.prepare(quote)
        if not prepared:
            continue
        refs = loc.resolve(quote)
        if refs:
            out.append((prepared[0], refs))
    return out


def substantiate(loc, candidates, quote):
    """The single verse reference the JK edition supports for this quote, or
    None when no candidate resembles it, or more than one survives."""
    prepared = loc.prepare(quote)
    if not prepared:
        return None
    skel, words = prepared
    proposed = []
    for jk_skel, refs in candidates:
        if refs not in proposed and similarity(skel, jk_skel) >= MIN_SIM:
            proposed.append(refs)
    verified = [refs for refs in proposed if loc.verifies(skel, words, refs)]
    return verified[0] if len(verified) == 1 else None


def main():
    loc = Locator()
    candidates = jk_candidates(loc)
    print(f"JK edition: {len(candidates)} independently located quotes")

    path = HERE / "sources" / "resolved_citations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = rows = remaining = 0
    for work in data.values():
        for entry in work:
            for sense in entry["senses"]:
                for q in sense["quotes"]:
                    if q["status"] not in ("no_match", "too_short"):
                        continue
                    refs = substantiate(loc, candidates, q["quote"])
                    if refs:
                        q["status"] = "edition_jk"
                        q["refs"] = [f"{s}:{a}" for s, a in refs]
                        fixed += 1
                        rows += len(refs)
                    else:
                        remaining += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"substantiated from JK edition: {fixed} quotes / {rows} references, "
          f"still unresolved: {remaining}")


if __name__ == "__main__":
    main()
