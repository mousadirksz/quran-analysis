#!/usr/bin/env python3
"""Render a short film about nahw, video/nahw.mp4, from the textbook and the database.

The film walks through docs/nahw-nl.md: isnad, who hit whom, mu'rab and
mabni, the four positions and their signs, the 'amil, the nominal sentence
and what kaana, inna and zanna do to it, the verb and its faa'il, the
naa'ib al-faa'il, the mafa'il, haal and tamyiiz, jarr, ta'alluq, the
tawaabi', and the places where Hafs and Warsh read the i'rab differently. Like
the sarf film it is silent, with its text on screen in Dutch.

Where the sarf film colours letters, this one colours words by their position
-- raf' gold, nasb teal, jarr rose, jazm violet, mabni left as it is -- and
draws the relations between them as arcs, from the word that governs to the
word it governs. Those arcs are the treebank's: every Quranic sentence on
screen is read out of `corpus` and `syntax` here, with the words the
treebank posits drawn dashed where it puts them. Only the Warsh side of the
two riwaya pairs has no treebank behind it; its words come from the Warsh
mushaf and its analysis is the book's, written down below.

The counts are not typed into the film either. This script writes them, and
the sentences, to video/nahw_data.js, which video/nahw.html reads; a claim the
film makes in words ("the genitive is the largest", "not one in six is
zaahir") is checked here, and the run stops if the database no longer bears
it out.

    python3 nahw_video.py                    # nahw_data.js, then video/nahw.mp4
    python3 nahw_video.py --data             # only nahw_data.js; open video/nahw.html to play it
    python3 nahw_video.py --stills 12,95.5   # PNG frames at those seconds, to check a layout

It needs what sarf_video.py needs: node with playwright and its chromium,
ffmpeg, and internet access for the two fonts.
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from add_metadata import repair_markers
from compare_riwayat import flat, text_of
from nahw_examples import (case_counts, faail_kinds, irab_rows, nasikh_counts,
                           relation_counts, verb_doers)
from sarf_video import clusters, render

HERE = Path(__file__).parent
DB = HERE / "quran.db"
VIDEO = HERE / "video"

# What an arc is called on screen: the name the book gives the relation.
LABEL = {
    "Subj": "fāʿil", "Obj": "mafʿūl bihi", "Pass": "nāʾib al-fāʿil",
    "Pred": "ḫabar", "Poss": "muḍāf ilayhi", "gen": "majrūr", "link": "taʿalluq",
    "Adj": "ṣifa", "App": "badal", "conj": "maʿṭūf", "emph": "tawkīd",
    "cog": "mafʿūl muṭlaq", "prp": "mafʿūl lahu", "circ": "ḥāl", "Spec": "tamyīz",
    "subj<<in>>": "ism inna", "pred<<in>>": "ḫabar inna",
    "subj<<an>>": "ism anna", "pred<<an>>": "ḫabar anna",
    "subj<<kan>>": "ism kāna", "pred<<kan>>": "ḫabar kāna",
}
# The position a relation puts its word in, which is the colour of its arc.
# A word that is mabni still takes the arc's colour: it stands fi mahall.
POSITION = {
    "Subj": "raf", "Pass": "raf", "Pred": "raf", "pred<<in>>": "raf",
    "pred<<an>>": "raf", "subj<<kan>>": "raf",
    "Obj": "nasb", "cog": "nasb", "prp": "nasb", "circ": "nasb", "Spec": "nasb",
    "subj<<in>>": "nasb", "subj<<an>>": "nasb", "pred<<kan>>": "nasb",
    "Poss": "jarr", "gen": "jarr",
}
# The tawaabi' have no position of their own: they take their head's.
FOLLOWERS = {"Adj", "App", "conj", "emph"}
# A ta'alluq whose word is an adverb of time or place is a zarf, mafool fiihi.
ZARF = {"T", "LOC"}
# The posited pronouns, as the book writes them; the treebank leaves vowels off.
PRONOUN = {"نحن": "نَحْنُ", "أنت": "أَنْتَ", "هو": "هُوَ", "هي": "هِيَ"}
CASE = {"NOM": "raf", "ACC": "nasb", "GEN": "jarr"}
FATHA, KASRA = "\u064e", "\u0650"
PAUSE = {chr(c) for c in range(0x06D6, 0x06DD)}


def bare(text):
    """The letters without their vowels."""
    return "".join(ch for ch in text if not "\u064b" <= ch <= "\u0652")


def position(seg):
    """The colour of one segment: the position its ending shows, or mabni.

    A noun shows its case. An imperfect verb is marfu' unless the corpus says
    subjunctive or jussive -- except with the nun of the feminine plural or of
    emphasis, which make it mabni. Everything else is mabni: the perfect, the
    imperative, the pronouns, the particles."""
    tag, kind, aspect, case, mood, gender, number, emph = seg
    if case in CASE:
        return CASE[case]
    if tag == "V" and aspect == "IMPF":
        if emph or (gender == "F" and number == "P"):
            return "mabni"
        return {"SUBJ": "nasb", "JUS": "jazm"}.get(mood, "raf")
    return "mabni"


def word_spans(cur, surah, ayah, word):
    """One written word as the spans the film colours: the corpus' segments,
    the article joined to its noun, each with its treebank token."""
    segs = cur.execute(
        'SELECT c.id, c.form_ar, c.tag, c.segment_type, c.aspect, c."case", c.mood,'
        " c.gender, c.number, s.tid FROM corpus c JOIN syntax s ON s.corpus_id = c.id"
        " WHERE c.surah=? AND c.ayah=? AND c.word=? ORDER BY c.segment",
        (surah, ayah, word)).fetchall()
    if not segs:
        sys.exit(f"{surah}:{ayah}:{word}: no such word in the corpus")
    emph = any(s[2] == "EMPH" and s[3] == "SUFFIX" for s in segs)
    spans, pending = [], ""
    for _id, form, tag, kind, aspect, case, mood, gender, number, tid in segs:
        text = repair_markers(form)
        if tag == "DET":
            pending += text
            continue
        cls = position((tag, kind, aspect, case, mood, gender, number, emph))
        spans.append([pending + text, cls, tid])
        pending = ""
    return spans


def phrase(cur, ref, words, keep=None, intra=(), ghosts=True, taqdir=None):
    """A stretch of the Quran as the film draws it, with the treebank's arcs.

    `words` are word numbers in the verse of `ref`, or (ayah, word) for a
    stretch that runs on into the next verse, and None for an ellipsis. Arcs
    are drawn for the relations in `keep` (every relation in LABEL if not
    given) whose two ends are both on screen, but not inside one written word
    unless `intra` names the relation. With `ghosts`, a token the treebank
    posits is drawn where the treebank puts it, if a drawn arc reaches it; an
    empty one, (*) in the treebank, shows `taqdir`, what the book says the
    grammarians fill in."""
    surah, ayah = map(int, ref.split(":")[:2])
    keep = set(keep or LABEL)
    items = []                      # (kind, spans) in reading order
    for w in words:
        if w is None:
            items.append(("dots", [["…", "dots", ""]]))
            continue
        a, n = w if isinstance(w, tuple) else (ayah, w)
        items.append(("word", word_spans(cur, surah, a, n)))
    shown = {sp[2]: i for i, (_, spans) in enumerate(items) for sp in spans if sp[2] != ""}
    tok = {}
    for tid in shown:
        tok[tid] = cur.execute("SELECT tid, head_tid, rel_label, pos, is_implicit, token_ar"
                               " FROM syntax WHERE tid=?", (tid,)).fetchone()
    # the posited tokens that hang on, or carry, a word on screen
    posited = {}
    if ghosts:
        for tid in list(shown):
            head = tok[tid][1]
            for r in cur.execute(
                    "SELECT tid, head_tid, rel_label, pos, is_implicit, token_ar FROM syntax"
                    " WHERE is_implicit=1 AND (head_tid=? OR tid=?)", (tid, head)).fetchall():
                if r[2] in keep or (r[0] == head and tok[tid][2] in keep):
                    posited[r[0]] = r
    tok.update(posited)

    arcs = []
    for tid, (_, head, rel, _pos, _imp, _t) in tok.items():
        if head not in tok or rel not in keep or rel not in LABEL:
            continue
        if tid in shown and head in shown and shown[tid] == shown[head] and rel not in intra:
            continue
        arcs.append([head, tid, rel])
    reached = {t for a in arcs for t in a[:2]}
    for tid in list(posited):
        if tid not in reached:
            del posited[tid], tok[tid]

    # each posited token goes after the last word whose tokens all come before it
    for tid in sorted(posited):
        text = posited[tid][5].strip("()")
        if text == "*":
            if not taqdir:
                sys.exit(f"{ref}: an empty posited token and nothing to fill it with")
            text = taqdir
        else:
            text = PRONOUN.get(bare(text), text)
        at = 0
        for i, (kind, spans) in enumerate(items):
            if kind == "word" and max(sp[2] for sp in spans) < tid:
                at = i + 1
        items.insert(at, ("ghost", [[text, "ghost", tid]]))
    order = {sp[2]: i for i, (_, spans) in enumerate(items) for sp in spans}
    cls_of = {sp[2]: sp[1] for _, spans in items for sp in spans}

    def colour(tid):
        """The colour of the arc into `tid`: its relation's position, the
        position of what it follows, or for a zarf its own case."""
        _, head, rel, pos, _imp, _t = tok[tid]
        if rel in POSITION:
            return POSITION[rel]
        if rel in FOLLOWERS and head in tok:
            return colour(head) if tok[head][2] in POSITION or tok[head][2] in FOLLOWERS \
                else cls_of.get(head, "")
        if rel == "link" and pos in ZARF:
            return cls_of.get(tid, "")
        return ""

    out = []
    for head, tid, rel in sorted(arcs, key=lambda a: order[a[1]]):
        label = "mafʿūl fīhi" if rel == "link" and tok[tid][3] in ZARF else LABEL[rel]
        out.append([head, tid, label, colour(tid)])
    return dict(ref=ref, words=[spans for _, spans in items], arcs=out)


def warsh_line(cur, ref, hafs, numbers, classes, arcs):
    """The Warsh side of a pair, which no treebank annotates: the words of the
    Warsh mushaf at these places, split into spans where the Hafs words are,
    with the book's analysis over them. `classes` gives the colours of a word
    that reads differently; every other word keeps the Hafs colours."""
    surah, ayah = map(int, ref.split(":"))
    verse = [w for a, w in flat(text_of("warsh")[surah], "warsh") if a == ayah]
    out = []
    for n, spans in zip(numbers, (w for w in hafs["words"] if w[0][1] != "ghost")):
        word = "".join(ch for ch in verse[n - 1] if ch not in PAUSE)
        cl = clusters(word)
        cls = classes.get(n, [sp[1] for sp in spans])
        if len(cls) != len(spans):
            sys.exit(f"{ref}:{n}: {len(cls)} colours for {len(spans)} parts")
        parts, at = [], 0
        for i, sp in enumerate(spans):
            k = len(clusters(sp[0])) if i < len(spans) - 1 else len(cl) - at
            parts.append(["".join(cl[at:at + k]), cls[i], f"w{n}.{i}"])
            at += k
        out.append(parts)
    # the words that differ must be exactly riwaya_diff's farsh for this verse
    farsh = {"".join(ch for ch in b if ch not in PAUSE) for (b,) in cur.execute(
        "SELECT form_b FROM riwaya_diff WHERE riwaya_a='hafs' AND riwaya_b='warsh'"
        " AND kind='farsh' AND surah=? AND ayah_a=?", (surah, ayah))}
    on_screen = {"".join(p[0] for p in w) for w in out}
    if not farsh <= on_screen:
        sys.exit(f"{ref}: the Warsh line misses {farsh - on_screen}")
    arcs = [[f"w{h}.{hi}", f"w{d}.{di}", LABEL[rel], POSITION[rel]]
            for (h, hi), (d, di), rel in arcs]
    return dict(ref=ref, words=out, arcs=arcs)


def expect(cond, claim):
    if not cond:
        sys.exit(f"the film says {claim}; the database no longer does")


def word_of(p, tid):
    for spans in p["words"]:
        for sp in spans:
            if sp[2] == tid:
                return sp
    return None


def collect(cur):
    d = {}
    cases = case_counts(cur)
    d["cases"] = cases
    expect(max(cases, key=cases.get) == "GEN", "the genitive is the largest position")

    rels = {rel.replace(" ", ""): (n - imp, imp) for rel, _ar, n, imp in relation_counts(cur)}
    d["rel"] = {k: dict(written=rels[k][0], posited=rels[k][1]) for k in
                ("Subj", "Obj", "Pred", "link", "gen", "Poss", "Adj", "conj", "emph",
                 "App", "Pass", "cog", "prp", "circ", "Spec")}
    top = max(rels, key=lambda k: rels[k][0])
    expect(top == "link", "ta'alluq is the largest relation in what is written")
    expect(sum(rels["Subj"]) > sum(rels["link"]),
           "the faa'il overtakes it once the posited ones count")
    d["tokens"] = dict(zip(("written", "posited"), cur.execute(
        "SELECT SUM(is_implicit=0), SUM(is_implicit) FROM syntax").fetchone()))

    nas = nasikh_counts(cur)
    total = {g: v["subj"] + v["pred"] for g, v in nas.items()}
    expect(max(total, key=total.get) == "in", "inna is the naasikh that governs most")
    d["nawasikh"] = dict(kinds=len(nas), places=sum(total.values()),
                         inna=nas["in"], inna_total=total["in"])

    kinds = dict(faail_kinds(cur))
    n = sum(kinds.values())
    expect(kinds["zaahir"] * 6 < n, "not one faa'il in six is zaahir")
    expect(kinds["mustatir"] * 3 > n, "more than a third is mustatir")
    expect(max(kinds, key=kinds.get) == "baariz", "the baariz is the commonest")
    d["faail"] = dict(kinds, total=n,
                      pct={k: round(100 * v / n) for k, v in kinds.items()})

    v = verb_doers(cur)
    expect(v["one"] + v["both"] + v["none"] == v["verbs"], "the count adds up")
    expect(v["subj"] + v["pas"] + v["ism"] == v["one"] + 2 * v["both"],
           "no verb has more than two of the three")
    d["verbs"] = dict(v, pct=round(100 * (v["verbs"] - v["none"]) / v["verbs"]))

    irab, mabni = irab_rows(cur)
    farsh = cur.execute("SELECT COUNT(*) FROM riwaya_diff WHERE riwaya_a='hafs'"
                        " AND riwaya_b='warsh' AND kind='farsh'").fetchone()[0]
    d["irab"] = dict(farsh=farsh, last=len(irab) + len(mabni), irab=len(irab),
                     mabni=len(mabni))
    places = {(s, a) for s, a, *_ in irab}
    expect({(34, 17), (24, 9)} <= places, "34:17 and 24:9 read the i'rab differently")

    # the sentences, scene by scene
    p = {}
    p["16:75"] = phrase(cur, "16:75", [1, 2, 3])
    p["2:25"] = phrase(cur, "2:25", [4, 5], keep={"Obj"})
    p["2:125"] = phrase(cur, "2:125", [8, 9, 10], keep={"gen", "Poss"})
    p["amil"] = phrase(cur, "1:1", [1, 2], keep={"gen", "Poss"}, intra={"gen"}, ghosts=False)
    p["24:35"] = phrase(cur, "24:35", [1, 2, 3])
    p["29:44"] = phrase(cur, "29:44", [1, 2, 3])
    p["34:17"] = phrase(cur, "34:17", [5, 6, 7, 8], keep={"Subj", "Obj"})
    p["34:17w"] = warsh_line(cur, "34:17", p["34:17"], [5, 6, 7, 8],
                             {6: ["raf"], 8: ["raf"]}, [((6, 0), (8, 0), "Pass")])
    p["1:5"] = phrase(cur, "1:5", [1, 2], keep={"Subj", "Obj"})
    p["1:6"] = phrase(cur, "1:6", [1, 2], keep={"Subj", "Obj"}, intra={"Obj"})
    p["4:164"] = phrase(cur, "4:164", [11, 12, 13, 14], keep={"cog"})
    p["20:130"] = phrase(cur, "20:130", [5, None, 8, 9, 10], keep={"link"}, ghosts=False)
    p["2:19"] = phrase(cur, "2:19", [9, None, 15, 16], keep={"prp"}, ghosts=False)
    p["17:37"] = phrase(cur, "17:37", [1, 2, 3, 4, 5], keep={"Subj", "circ"})
    p["19:4"] = phrase(cur, "19:4", [7, 8, 9], keep={"Subj", "Spec"})
    p["1:4"] = phrase(cur, "1:4", [1, 2, 3])
    p["1:1"] = phrase(cur, "1:1", [1, 2], keep={"link"}, taqdir="أَبْدَأُ")
    p["1:2"] = phrase(cur, "1:2", [1, 2], keep={"Pred", "link"}, taqdir="ثَابِتٌ")
    p["1:6-7"] = phrase(cur, "1:6", [1, 2, 3, (7, 1), (7, 2)], keep={"Obj", "Adj", "App", "Poss"},
                        ghosts=False)
    p["24:9"] = phrase(cur, "24:9", [1, 2, 3, 4, 5], keep={"subj<<an>>", "Poss"}, ghosts=False)
    p["24:9w"] = warsh_line(cur, "24:9", p["24:9"], [1, 2, 3, 4, 5],
                            {1: ["mabni", "raf"], 3: ["mabni"], 4: ["raf"]},
                            [((3, 0), (4, 0), "Subj")])
    d["p"] = p

    # what the captions say about these sentences
    words = lambda k: [sp for spans in p[k]["words"] for sp in spans]
    labels = lambda k: [a[2] for a in p[k]["arcs"]]
    expect(labels("16:75") == ["fāʿil", "mafʿūl bihi"], "16:75 is fi'l, faa'il, maf'ool bihi")
    sal = words("2:25")[-1]
    expect(sal[1] == "nasb" and sal[0].endswith(KASRA), "al-saalihaat is nasb with a kasra")
    ibr = words("2:125")[-1]
    expect(ibr[1] == "jarr" and ibr[0].endswith(FATHA), "Ibraahiim is jarr with a fatha")
    expect([sp[1] for sp in words("amil")] == ["mabni", "jarr", "jarr"],
           "bismi llaahi is two kasras, one for each 'amil")
    expect(any(sp[1] == "ghost" for sp in words("1:6")), "the faa'il of ihdinaa is not written")
    expect(any(a[2] == "ḥāl" and word_of(p["17:37"], a[0])[1] == "ghost" for a in p["17:37"]["arcs"]),
           "the saahib al-haal in 17:37 is the posited anta")
    expect(labels("34:17") == ["fāʿil", "mafʿūl bihi"], "Hafs reads 34:17 with a faa'il and a maf'ool")
    expect(labels("24:9") == ["ism anna", "muḍāf ilayhi"], "Hafs reads 24:9 with anna and an idaafa")
    return d


def dumps(d):
    """The data as JSON with one line per group of figures and per sentence,
    so that a change shows in a diff as the line it is."""
    js = lambda v: json.dumps(v, ensure_ascii=False)
    rows = []
    for k, v in d.items():
        if k == "p":
            inner = ",\n".join(f"  {js(name)}: {js(sent)}" for name, sent in v.items())
            rows.append(f' "p": {{\n{inner}\n }}')
        else:
            rows.append(f" {js(k)}: {js(v)}")
    return "{\n" + ",\n".join(rows) + "\n}"


def write_data(d):
    VIDEO.mkdir(exist_ok=True)
    path = VIDEO / "nahw_data.js"
    path.write_text(
        "// Generated by nahw_video.py from quran.db -- do not edit by hand.\n"
        "window.FILM = " + dumps(d) + ";\n", encoding="utf-8")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", action="store_true", help="only write video/nahw_data.js")
    ap.add_argument("--stills", help="comma-separated seconds; PNGs instead of the film")
    ap.add_argument("--out", default=str(VIDEO / "nahw.mp4"))
    args = ap.parse_args()

    cur = sqlite3.connect(DB).cursor()
    path = write_data(collect(cur))
    print(f"wrote {path.relative_to(HERE)}")
    if not args.data:
        render(VIDEO / "nahw.html", args.out, args.stills)


if __name__ == "__main__":
    main()
