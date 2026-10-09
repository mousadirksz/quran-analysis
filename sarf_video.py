#!/usr/bin/env python3
"""Render a short film about sarf, video/sarf.mp4, from the textbook and the database.

The film walks through docs/sarf-nl.md in seventeen scenes: the three kinds of
word, the root, the mizan, the ten added letters, the verb and its six abwab,
the derived forms, the weak roots, conjugation, the majhul and one root's
family of nouns. It is silent and its text is on screen, in Dutch, like the
book.

The figures on screen are not typed into the film. This script reads every
count and every Quranic example from quran.db and writes them to
video/sarf_data.js, and video/sarf.html takes them from there -- the way
sarf_examples.py fills the tables in the book. A claim the film makes in words
("both are weak", "no root fills the whole paradigm") is checked here too, and
the run stops if the database no longer bears it out.

    python3 sarf_video.py                    # sarf_data.js, then video/sarf.mp4
    python3 sarf_video.py --data             # only sarf_data.js; open video/sarf.html to play it
    python3 sarf_video.py --stills 12,95.5   # PNG frames at those seconds, to check a layout

Unlike the pipeline this needs more than the standard library: node with
playwright and its chromium to draw the frames, ffmpeg to encode them, and
internet access for the two fonts (Amiri, Inter) from Google Fonts.
"""

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

from add_metadata import repair_markers
from riwaya_sarf import BAB as RIWAYA_BAB, word_pair
from sarf_examples import BAB_NAMES, DAMMA, ayn_vowel, bab_roots, classify

HERE = Path(__file__).parent
DB = HERE / "quran.db"
VIDEO = HERE / "video"

WEAK = {"mithal", "ajwaf", "naqis", "lafif mafruq", "lafif maqrun"}

# One root through the Quran: the word shown, the lemma the corpus files it
# under (in its own spelling), and what the patterns make of it.
FAMILY = [
    ("عَلِمَ", "عَلِمَ"), ("عِلْم", "عِلْم"), ("عَالِم", "عَٰلِم"),
    ("مَعْلُوم", "مَّعْلُوم"), ("عَلِيم", "عَلِيم"), ("عَلَّام", "عَلَّٰم"),
    ("أَعْلَم", "أَعْلَم"), ("عَلَّمَ", "عَلَّمَ"), ("مُعَلَّم", "مُعَلَّم"),
]


def one(cur, sql, args=()):
    return cur.execute(sql, args).fetchone()[0]


def clusters(word):
    """A letter with the marks on it: the unit the page colours. Splitting
    anywhere else would tear a haraka from its letter."""
    out = []
    for ch in word:
        if out and unicodedata.category(ch).startswith("M"):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def ayn_mask(word, root):
    """The colouring of a verb in the abwab scene: r for a root letter, v for
    the ayn whose vowel the bab turns on, z for everything added. Walks the
    root through the word the way sarf_examples.ayn_vowel does."""
    out, pos = [], 0
    for cl in clusters(word):
        if pos < 3 and cl[0] == root[pos]:
            out.append("v" if pos == 1 else "r")
            pos += 1
        else:
            out.append("z")
    if pos < 3:
        sys.exit(f"{word}: the root {root} cannot be walked through it")
    return "".join(out)


def bare(cur, root, aspect):
    """The 3MS form of a bare verb, indicative where it has a mood, so the
    film shows yajcalu rather than the yajcala the book's table happens to
    attest first."""
    r = cur.execute(
        "SELECT form_ar FROM corpus WHERE root_ar=? AND pos='V' AND aspect=?"
        " AND person='3' AND gender='M' AND number='S' AND verb_form IS NULL"
        " AND IFNULL(voice,'ACT')='ACT' AND mood IS NULL ORDER BY surah, ayah LIMIT 1",
        (root, aspect)).fetchone()
    if not r:
        sys.exit(f"{root}: no bare {aspect} 3MS in the corpus")
    return repair_markers(r[0])


def bab_count(cur, root, key):
    """How often this verb stands in the Quran in its own bab.

    A root can carry two verbs: كبر is kabura (bab 5) seven times and kabira
    (bab 4) once, at 4:6, and sarf_examples counts the root. So an active form
    whose ayn says otherwise is left out. A form that opens on a damma is
    passive whether or not the corpus tags it so -- 4:140 yukfaru is not --
    and the ayn of a passive shows the voice, not the bab."""
    n = 0
    for form, aspect, voice in cur.execute(
            "SELECT form_ar, aspect, voice FROM corpus WHERE root_ar=? AND pos='V'"
            " AND verb_form IS NULL", (root,)).fetchall():
        form = repair_markers(form)
        passive = voice == "PASS" or DAMMA in clusters(form)[0]
        want = key[0] if aspect == "PERF" else key[1]
        if passive or ayn_vowel(form, root) in (want, None):
            n += 1
    return n


def attest(cur, root, aspect, pgn, voice="ACT"):
    """Where the Quran has this form of a bare verb: the written word and its
    verse, an occurrence without prefix first, as sarf_examples.paradigm."""
    r = cur.execute(
        "SELECT w.word_ar, v.surah, v.ayah,"
        " (SELECT COUNT(*) FROM corpus p WHERE p.surah=v.surah AND p.ayah=v.ayah"
        "   AND p.word=v.word AND p.segment_type='PREFIX') AS prefixes"
        " FROM corpus v JOIN words w ON w.surah=v.surah AND w.ayah=v.ayah AND w.word=v.word"
        " WHERE v.root_ar=? AND v.pos='V' AND v.verb_form IS NULL AND v.aspect=?"
        " AND v.person || IFNULL(v.gender,'') || v.number = ? AND IFNULL(v.voice,'ACT')=?"
        " ORDER BY prefixes, v.surah, v.ayah LIMIT 1", (root, aspect, pgn, voice)).fetchone()
    if not r:
        sys.exit(f"{root} {aspect} {pgn} {voice}: not in the corpus")
    return dict(word=repair_markers(r[0]), ref=f"{r[1]}:{r[2]}")


def word_at(cur, word):
    """The first verse with exactly this written word."""
    r = cur.execute("SELECT surah, ayah FROM words WHERE word_ar=? ORDER BY surah, ayah"
                    " LIMIT 1", (word,)).fetchone()
    if not r:
        sys.exit(f"{word}: not in the text")
    return dict(word=word, ref=f"{r[0]}:{r[1]}")


def spelled(cur, lemma):
    """The corpus' own spelling of a lemma. It writes shadda before fatha,
    the reverse of Unicode's canonical order, so a lemma typed here only
    meets it after both are normalised."""
    want = unicodedata.normalize("NFC", lemma)
    for (own,) in cur.execute("SELECT DISTINCT lemma_ar FROM corpus WHERE lemma_ar != ''"):
        if unicodedata.normalize("NFC", own) == want:
            return own
    sys.exit(f"{lemma}: no such lemma in the corpus")


def lemma_at(cur, lemma):
    lemma = spelled(cur, lemma)
    r = cur.execute(
        "SELECT w.word_ar, v.surah, v.ayah FROM corpus v JOIN words w ON w.surah=v.surah"
        " AND w.ayah=v.ayah AND w.word=v.word WHERE v.lemma_ar=? ORDER BY v.surah, v.ayah"
        " LIMIT 1", (lemma,)).fetchone()
    if not r:
        sys.exit(f"{lemma}: no such lemma")
    return dict(word=repair_markers(r[0]), ref=f"{r[1]}:{r[2]}")


def collect(cur):
    d = {}
    d["segments"] = one(cur, "SELECT COUNT(*) FROM corpus")
    d["words"] = one(cur, "SELECT COUNT(*) FROM words")
    kal = dict(cur.execute("SELECT kalima_type, COUNT(*) FROM corpus GROUP BY 1"))
    d["kalima"] = {k: kal[k] for k in ("ism", "harf", "fiil")}
    d["kalima_pct"] = {k: round(100 * v / d["segments"], 1) for k, v in d["kalima"].items()}
    # the book counts the kalimat without the muqatta'at, which are no word
    d["kalimat"] = d["segments"] - kal.get("muqattaat", 0)
    d["pronouns"] = one(cur, "SELECT COUNT(*) FROM corpus WHERE tag='PRON'")
    d["verbs"] = one(cur, "SELECT COUNT(*) FROM corpus WHERE pos='V'")
    if d["pronouns"] <= d["verbs"]:
        sys.exit("the film says there are more pronouns than verbs; there are not")

    roots = [r for (r,) in cur.execute(
        "SELECT DISTINCT root_ar FROM corpus WHERE root_ar != ''")]
    d["roots"] = dict(total=len(roots), tri=sum(len(r) == 3 for r in roots),
                      quad=sum(len(r) == 4 for r in roots))

    d["aspect"] = dict(cur.execute(
        "SELECT aspect, COUNT(*) FROM corpus WHERE pos='V' GROUP BY aspect"))
    passive = dict(cur.execute(
        "SELECT aspect, COUNT(*) FROM corpus WHERE pos='V' AND voice='PASS' GROUP BY aspect"))
    d["passive"] = dict(PERF=passive.get("PERF", 0), IMPF=passive.get("IMPF", 0),
                        IMPV=passive.get("IMPV", 0))
    d["passive"]["total"] = sum(passive.values())
    if d["passive"]["IMPV"]:
        sys.exit("the film says no amr is majhul; the corpus now has one")

    # the six abwab, each with the verb the Quran uses most in it
    found = bab_roots(cur)
    d["abwab"] = []
    for key in sorted(BAB_NAMES, key=lambda k: BAB_NAMES[k][0]):
        num, pattern = BAB_NAMES[key]
        row = dict(bab=int(num), madi_p=pattern.split(" / ")[0],
                   mudari_p=pattern.split(" / ")[1])
        if found[key]:
            root = found[key][0][0]
            madi, mudari = bare(cur, root, "PERF"), bare(cur, root, "IMPF")
            row.update(root=root, madi=madi, madi_m=ayn_mask(madi, root),
                       mudari=mudari, mudari_m=ayn_mask(mudari, root),
                       n=bab_count(cur, root, key))
        d["abwab"].append(row)
    if d["abwab"][5].get("root"):
        sys.exit("bab 6 now has a sound root in Hafs; the film says it has none")
    if len(found[("u", "u")]) != 1:
        sys.exit("the film says bab 5 has one verb in the Quran")
    hafs, warsh = word_pair(cur, 104, 3, "حسب")
    d["warsh_bab6"] = dict(
        places=sum(1 for r in RIWAYA_BAB if r[2] == "حسب" and r[4] == 6),
        hafs=hafs, hafs_m=ayn_mask(hafs, "حسب"),
        warsh=warsh, warsh_m=ayn_mask(warsh, "حسب"), ref="104:3")

    forms = {f or "I": n for f, n in cur.execute(
        "SELECT verb_form, COUNT(*) FROM corpus WHERE pos='V' GROUP BY verb_form")}
    d["forms"] = forms
    d["forms_used"] = len(forms)

    types = Counter(classify(r) for r in roots if len(r) == 3)
    types["lafif"] = types.pop("lafif mafruq", 0) + types.pop("lafif maqrun", 0)
    d["root_types"] = dict(types)

    top = cur.execute(
        "SELECT root_ar, COUNT(*) FROM corpus WHERE pos='V' AND root_ar != ''"
        " GROUP BY root_ar ORDER BY 2 DESC LIMIT 2").fetchall()
    if any(classify(r) not in WEAK for r, _ in top):
        sys.exit("the film says the two commonest verbs are both weak")
    d["top_verbs"] = [dict(root=r, n=n, word=attest(cur, r, "PERF", "3MS")["word"])
                      for r, n in top]

    # the fullest paradigm, against 14 persons in two tenses and 5 in the amr
    root, cells = cur.execute(
        "SELECT root_ar, COUNT(DISTINCT aspect || person || IFNULL(gender,'') || number) n"
        " FROM corpus WHERE pos='V' AND person != '' AND IFNULL(voice,'ACT')='ACT'"
        " AND verb_form IS NULL AND root_ar != '' GROUP BY root_ar"
        " ORDER BY n DESC LIMIT 1").fetchone()
    if cells >= 14 + 14 + 5:
        sys.exit(f"{root} fills the whole paradigm; the film says no root does")
    d["fullest"] = dict(root=root, cells=cells,
                        word=attest(cur, root, "PERF", "3MS")["word"])

    # Quranic attestations quoted beside the textbook forms
    d["at"] = dict(
        qala=attest(cur, "قول", "PERF", "3MS"),
        qultum=attest(cur, "قول", "PERF", "2MP"),
        yaidu=attest(cur, "وعد", "IMPF", "3MS"),
        dacawtu=word_at(cur, "دَعَوْتُ"),
        qina=attest(cur, "وقي", "IMPV", "2MS"),
        qu=attest(cur, "وقي", "IMPV", "2MP"),
        kutiba=attest(cur, "كتب", "PERF", "3MS", "PASS"),
        qila=attest(cur, "قول", "PERF", "3MS", "PASS"),
        mucallam=lemma_at(cur, "مُعَلَّم"),
    )

    d["family"] = []
    for shown, lemma in FAMILY:
        lemma = spelled(cur, lemma)
        n = one(cur, "SELECT COUNT(*) FROM corpus WHERE lemma_ar=?", (lemma,))
        if not n:
            sys.exit(f"{lemma}: the film counts this lemma and the corpus has none")
        d["family"].append(dict(word=shown, lemma=lemma, n=n))
    return d


def write_data(d):
    VIDEO.mkdir(exist_ok=True)
    path = VIDEO / "sarf_data.js"
    path.write_text(
        "// Generated by sarf_video.py from quran.db -- do not edit by hand.\n"
        "window.SARF = " + json.dumps(d, ensure_ascii=False, indent=1) + ";\n",
        encoding="utf-8")
    return path


def node_env():
    """Let node find a globally installed playwright, which is where
    `npm install -g playwright` puts it."""
    env = dict(os.environ)
    try:
        root = subprocess.run(["npm", "root", "-g"], capture_output=True, text=True,
                              check=True).stdout.strip()
        env["NODE_PATH"] = os.pathsep.join(p for p in (env.get("NODE_PATH"), root) if p)
    except (OSError, subprocess.CalledProcessError):
        pass
    return env


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", action="store_true", help="only write video/sarf_data.js")
    ap.add_argument("--stills", help="comma-separated seconds; PNGs instead of the film")
    ap.add_argument("--out", default=str(VIDEO / "sarf.mp4"))
    args = ap.parse_args()

    cur = sqlite3.connect(DB).cursor()
    path = write_data(collect(cur))
    print(f"wrote {path.relative_to(HERE)}")
    if args.data:
        return
    for tool in ("node", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is needed to render the film; --data writes the data alone")
    cmd = ["node", str(VIDEO / "render.cjs"), "--out", args.out]
    if args.stills:
        cmd = ["node", str(VIDEO / "render.cjs"), "--stills", args.stills,
               "--dir", str(VIDEO / "stills")]
    sys.exit(subprocess.run(cmd, env=node_env()).returncode)


if __name__ == "__main__":
    main()
