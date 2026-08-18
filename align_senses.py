#!/usr/bin/env python3
"""Lay canonical sense ids across the three wujuh works (`sense_alignment`).

`wujuh.sense_nr` is numbered per work, so Yahya ibn Sallam's first wajh of
huda ("bayanan") and Ibn al-Jawzi's first ("al-bayan") are two unrelated
rows even though they are the same wajh. That makes the historically
interesting question unanswerable: which wujuh does the whole tradition
carry (four centuries, three independent authors) and which are the
private property of one author?

This script clusters the senses of one root across works and gives every
cluster a canonical_id. Two signals decide, and both must be earned:

  verse overlap  the strongest signal: if two senses cite the same verses,
                 they are the same wajh whatever their wording. Only
                 citations of high/medium confidence count; the 'low'
                 (ambiguous) rows list every verse containing the quoted
                 phrase, so overlap between them is not evidence.
  gloss          normalized (diacritics, tanwin alif, hamza and alif-maqsura
                 folded, article and conjunctive waw stripped) and, for
                 al-Damaghani, freed of the leading headword and its
                 "yacni"/"bi-macna" marker, since his glosses read
                 "al-khiyana yacni adh-dhanb" where the others write
                 "adh-dhanb". Equality, token-set inclusion, string ratio
                 and content-token overlap (Dice) all feed one score.

Sense order is deliberately not used: the works do run roughly parallel,
but Ibn al-Jawzi splits where Ibn Sallam lumps, so order would drag pairs
together that the two signals reject.

An edge is strong when an identical gloss carries it on its own, when one
shared verse meets a near-identical gloss, or when two shared verses
corroborate a related one; weak when the gloss is only related, or when
several shared verses meet a faint one. Verse overlap is never accepted
without some lexical affinity (gloss >= 0.25): two wujuh of one root
regularly cite the same verse precisely because the authors disagree
about which wajh it belongs to, so bare overlap aligns "al-cadl" with
"ar-rukub". Everything below that stays unaligned: a wrong alignment
costs more than a missing one, and a sense that stays alone is simply a
canonical sense of its own. Two senses of one entry can never land in
the same cluster, and a cluster is only extended by a sense that is
alignable with every sense already in it (complete linkage), so no chain
of pairwise matches can smuggle in a third reading.

Idempotent: drops and rebuilds the table. Join back with
wujuh via (work, headword, sense_nr).
"""

import re
import sqlite3
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).parent

DIACRITICS = re.compile(r"[ً-ْٓ-ٰٕۖ-ۭـ]")
NON_ARABIC = re.compile(r"[^ء-ي\s]")

# glossing formulas ("means", "that is") and pronouns that carry no sense
_MARKERS = {"يعني", "بمعنى", "معنى", "أي", "هو", "هي", "به", "بها", "بعينه",
            "بعينها", "ومعناه", "معناه", "وهو", "وهي", "نفسه"}
# too common to count as shared content between two glosses
_STOPWORDS = _MARKERS | {"في", "من", "على", "إلى", "عن", "ما", "لا", "أن",
                         "الله", "تعالى", "صلى", "عليه", "وسلم", "الذي",
                         "التي", "ذلك", "هذا", "كل", "غير", "بغير", "مثل",
                         "نحو", "بين", "عند", "بعد", "قبل", "قوله", "وجه",
                         "قال", "إذا", "ثم", "أو", "قد"}

WORK_ORDER = {"ibnsallam": 0, "damaghani": 1, "ibnjawzi": 2}


def normalize_token(tok):
    tok = tok.translate(str.maketrans("أإآٱ", "اااا"))
    tok = tok.replace("ؤ", "و").replace("ئ", "ي")
    tok = tok.replace("ى", "ي").replace("ة", "ه")
    if tok.startswith("و") and len(tok) > 3:
        tok = tok[1:]
    if tok.startswith("ال") and len(tok) > 3:
        tok = tok[2:]
    if tok.endswith("ا") and len(tok) > 3:      # accusative tanwin: bayanan
        tok = tok[:-1]
    return tok


def normalize(text):
    text = NON_ARABIC.sub(" ", DIACRITICS.sub("", text or ""))
    return [normalize_token(t) for t in text.split() if t]


MARKERS = {normalize_token(t) for t in _MARKERS}
STOPWORDS = {normalize_token(t) for t in _STOPWORDS}


def is_root_form(tok, root):
    """True if tok is a word built on root (root letters in order)."""
    if not root:
        return False
    letters = [c for c in normalize_token(root.replace(" ", "")) if c.strip()]
    if not letters or len(tok) > len(letters) + 4:
        return False
    i = 0
    for c in tok:
        if i < len(letters) and c == letters[i]:
            i += 1
    return i == len(letters)


def gloss_key(gloss, headword, root):
    """Normalized token list of the sense proper, headword formula removed."""
    tokens = normalize(gloss)
    head = {normalize_token(t) for t in normalize(headword)}
    body = list(tokens)
    while body and (body[0] in MARKERS or body[0] in head
                    or is_root_form(body[0], root)):
        body.pop(0)
    while body and body[-1] in MARKERS:
        body.pop()
    return body or tokens


def gloss_similarity(a, b):
    """0 when either gloss carries no content word: 'fi' or a lost gloss
    must not match everything by inclusion."""
    ca, cb = set(a) - STOPWORDS, set(b) - STOPWORDS
    if not {t for t in ca if len(t) > 1} or not {t for t in cb if len(t) > 1}:
        return 0.0
    sa, sb = set(a), set(b)
    if a == b:
        return 1.0
    if sa <= sb or sb <= sa:
        return 0.85
    ratio = SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    shared = ca & cb
    if shared:
        dice = 2 * len(shared) / (len(ca) + len(cb))
        ratio = max(ratio, dice)
        if max(len(t) for t in shared) >= 3:
            ratio = max(ratio, 0.7)
    return ratio


def score_pair(a, b):
    """(rank, strength, gloss_sim, shared_verses) or None if unalignable."""
    g = gloss_similarity(a["key"], b["key"])
    n = len(a["verses"] & b["verses"])
    smallest = min(len(a["verses"]), len(b["verses"]))
    cov = n / smallest if smallest else 0.0
    if g >= 1.0 or (n >= 1 and g >= 0.8) or (n >= 2 and cov >= 0.3 and g >= 0.45):
        strength = "strong"
    elif (n >= 1 and g >= 0.6) or g >= 0.85 or (n >= 2 and cov >= 0.3 and g >= 0.25):
        strength = "weak"
    else:
        return None
    return (g + min(n, 4) * 0.5 + cov, strength, g, n)


def load_senses(cur):
    columns = {r[1] for r in cur.execute("PRAGMA table_info(wujuh)")}
    if "confidence" not in columns:
        raise SystemExit("wujuh has no confidence column; run add_wujuh.py first")
    senses = {}
    for work, head, root, nr, gloss in cur.execute(
            "SELECT DISTINCT work, headword, root_ar, sense_nr, gloss FROM wujuh"):
        senses[(work, head, nr)] = {
            "root": root, "gloss": gloss or "",
            "key": gloss_key(gloss, head, root),
            "verses": set()}
    for work, head, nr, s, a in cur.execute(
            "SELECT work, headword, sense_nr, surah, ayah FROM wujuh"
            " WHERE confidence IN ('high','medium')"):
        senses[(work, head, nr)]["verses"].add((s, a))
    return senses


def cluster(senses):
    """Greedy highest-evidence-first union of senses per root."""
    by_root = defaultdict(list)
    for key, sense in senses.items():
        if sense["root"]:
            by_root[sense["root"]].append(key)

    edges = []
    for root, keys in by_root.items():
        for i, x in enumerate(keys):
            for y in keys[i + 1:]:
                if (x[0], x[1]) == (y[0], y[1]):
                    continue
                scored = score_pair(senses[x], senses[y])
                if scored:
                    edges.append((scored[0], x, y, scored[1], scored[2], scored[3]))
    edges.sort(key=lambda e: -e[0])

    parent = {k: k for k in senses}
    members = {k: [k] for k in senses}
    entries = {k: {(k[0], k[1])} for k in senses}
    joined = {}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    scores = {(x, y): (strength, g, n) for _r, x, y, strength, g, n in edges}

    def compatible(left, right):
        """Complete linkage: every cross pair must be alignable on its own,
        so a chain of pairwise matches cannot drag in a third sense that
        neither of the other two would have accepted."""
        for a in left:
            for b in right:
                if (a[0], a[1]) == (b[0], b[1]):
                    return False
                if (a, b) not in scores and (b, a) not in scores:
                    return False
        return True

    for _rank, x, y, strength, g, n in edges:
        rx, ry = find(x), find(y)
        if rx == ry or entries[rx] & entries[ry]:
            continue
        if not compatible(members[rx], members[ry]):
            continue
        parent[ry] = rx
        members[rx] += members[ry]
        entries[rx] |= entries[ry]
        note = f"gloss {g:.2f}, shared verses {n}"
        for k in (x, y):
            prev = joined.get(k)
            if prev is None or (prev[0] == "weak" and strength == "strong"):
                joined[k] = (strength, note)
    return members, joined, find


def canonical_gloss(keys, senses):
    freq = Counter(" ".join(senses[k]["key"]) for k in keys)
    return min(keys, key=lambda k: (
        -freq[" ".join(senses[k]["key"])],
        0 if senses[k]["gloss"].strip().startswith("ال") else 1,
        len(senses[k]["gloss"]), WORK_ORDER.get(k[0], 9)))


def main():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()
    senses = load_senses(cur)
    members, joined, find = cluster(senses)

    cur.execute("DROP TABLE IF EXISTS sense_alignment")
    cur.execute("""CREATE TABLE sense_alignment (
        canonical_id INTEGER,
        root_ar TEXT, canonical_gloss TEXT, n_works INTEGER, n_senses INTEGER,
        work TEXT, headword TEXT, sense_nr INTEGER, gloss TEXT,
        confidence TEXT, evidence TEXT,
        PRIMARY KEY (work, headword, sense_nr))""")

    rows = []
    clusters = sorted({find(k) for k in senses},
                      key=lambda r: (senses[r]["root"] or "", r))
    for cid, root in enumerate(clusters, 1):
        keys = sorted(members[root], key=lambda k: (WORK_ORDER.get(k[0], 9), k[2]))
        head = canonical_gloss(keys, senses)
        n_works = len({k[0] for k in keys})
        for k in keys:
            strength, note = joined.get(k, ("single", ""))
            rows.append((cid, senses[k]["root"], senses[head]["gloss"],
                         n_works, len(keys), k[0], k[1], k[2],
                         senses[k]["gloss"], strength, note))

    cur.executemany(
        "INSERT INTO sense_alignment (canonical_id, root_ar, canonical_gloss,"
        " n_works, n_senses, work, headword, sense_nr, gloss, confidence,"
        " evidence) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_align_canonical"
                " ON sense_alignment(canonical_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_align_root"
                " ON sense_alignment(root_ar)")
    con.commit()

    conf = Counter(r[9] for r in rows)
    per_cluster = {r[0]: r[3] for r in rows}
    shared = Counter(per_cluster.values())
    print(f"senses: {len(rows)}, canonical senses: {len(clusters)}, "
          f"aligned: {conf['strong'] + conf['weak']} "
          f"(strong {conf['strong']}, weak {conf['weak']})")
    print(f"canonical senses by works: one {shared[1]}, two {shared[2]}, "
          f"all three {shared[3]}")
    con.close()


if __name__ == "__main__":
    main()
