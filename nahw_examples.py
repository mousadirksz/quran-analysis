#!/usr/bin/env python3
"""Generate the tables for docs/nahw-nl.md from the database.

Where sarf_examples.py teaches word shapes, this teaches the relations
between words: what the treebank calls each token, how often, and with which
verse to point at. Everything printed here is read out of `syntax`, `corpus`
and `riwaya_diff` -- nothing is composed by hand, so a reader who doubts a
figure can re-run the mode that produced it.

  python3 nahw_examples.py relations     every relation with its count
  python3 nahw_examples.py muqaddar      the elements the grammarians posit
  python3 nahw_examples.py nawasikh      every naasikh the treebank names
  python3 nahw_examples.py cases         case and mood across the corpus
  python3 nahw_examples.py irab-diff     where the riwayat read the i'rab differently\n  python3 nahw_examples.py irab-mabni    final-vowel differences that are not i'rab\n  python3 nahw_examples.py irab-book     the i'rab differences with their chapter
  python3 nahw_examples.py rel Pred      examples of one relation
  ... any mode with --markdown for the textbook form
"""

import re
import sqlite3
import sys
from pathlib import Path

from add_metadata import repair_markers

DB = Path(__file__).parent / "quran.db"

# The treebank labels a relation in English and in Arabic; the Dutch is this
# project's, and follows the naming the sarf book already uses.
REL_NL = {
    "link": "waar een jarr-groep aan hangt", "gen": "in de genitief",
    "Obj": "lijdend voorwerp", "Subj": "onderwerp van het werkwoord",
    "Poss": "tweede lid van de idaafa", "conj": "nevenschikking",
    "sub": "betrekkelijke bijzin", "Adj": "bijvoeglijke bepaling",
    "Pred": "gezegde van de naamwoordelijke zin", "neg": "ontkenning",
    "emph": "versterking", "subj<<in>>": "onderwerp na inna",
    "cond": "voorwaarde", "pred<<in>>": "gezegde na inna",
    "circ": "toestandsbepaling", "rslt": "antwoord op de voorwaarde",
    "Pass": "onderwerp van de lijdende vorm",
    "pred <<kan>>": "gezegde na kaana", "subj <<kan>>": "onderwerp na kaana",
    "App": "bijstelling", "intg": "vraag", "voc": "aanspreking",
    "cert": "bevestiging", "res": "beperking", "Pro": "verbod",
    "subj<<an>>": "onderwerp na anna", "cog": "innerlijk lijdend voorwerp",
    "root": "kern van de zin", "NonRel": "geen relatie toegekend",
    "pred<<an>>": "gezegde na anna", "sup": "toegevoegd partikel",
    "Spec": "onderscheidende bepaling", "exp": "uitgezonderde",
    "prev": "kaaf van de vergelijking", "fut": "toekomstpartikel",
    "caus": "reden-laam", "prp": "doelbepaling", "impv": "gebiedende wijs",
    "ret": "verbetering", "imrs": "antwoord op het bevel",
    "inc": "aanhef", "amd": "tegenstelling", "exl": "opsomming",
    "int": "verduidelijking", "sur": "verrassings-idhaa",
    "exh": "aansporing", "avr": "afwijzing", "ans": "antwoord",
    "state": "toelichting", "eq": "gelijkstelling", "Cpnd": "samenstelling",
}

# The treebank spells the nawaasikh out in the label: `subj <<kan>>`,
# `subj <<lays>>`, `subj <<ka'ana>>` are all one position with a different
# governor. Grouping them is what a grammar book would call them.
NASIKH = re.compile(r"^(subj|pred) ?<<(.+)>>$")

# Which chapter of docs/nahw-nl.md treats each relation.
REL_CH = {
    "Subj": 11, "Pass": 12, "Obj": 13, "cog": 14, "prp": 14, "circ": 15,
    "Spec": 15, "exp": 16, "res": 16, "gen": 17, "Poss": 17, "link": 18,
    "Adj": 19, "conj": 19, "emph": 19, "App": 19, "sub": 20, "cond": 20,
    "rslt": 20, "Pred": 6, "neg": 20, "root": 5, "sup": 21,
    "intg": 20, "voc": 14, "cert": 20, "Pro": 20, "fut": 20,
    "imrs": 20, "impv": 20, "caus": 20, "prev": 17, "inc": 6,
    "amd": 19, "ret": 19, "exl": 19, "int": 19, "sur": 20, "exh": 20,
    "avr": 20, "ans": 20, "state": 19, "eq": 6, "Cpnd": 17,
}


def rel_ch(label):
    """The chapter for a relation; every naasikh label lands in 8 or 9."""
    if label in REL_CH:
        return REL_CH[label]
    m = NASIKH.match(label)
    if m:
        return 9 if m.group(2) in ("in", "an", "lel", "layt", "lakin",
                                   "lakun", "ka'ana", "ka") else 8
    return None


def num(n):
    """Dutch thousands separator, as the sarf book uses."""
    return format(n, ",").replace(",", ".")


def whole(cur, surah, ayah, word):
    """The written word, segments joined and the corpus' markers repaired."""
    r = cur.execute("SELECT word_ar FROM words WHERE surah=? AND ayah=? AND word=?",
                    (surah, ayah, word)).fetchone()
    return repair_markers(r[0]) if r else None


def relations(cur, markdown=False, limit=30):
    rows = cur.execute(
        "SELECT rel_label, rel_label_ar, COUNT(*) n,"
        " SUM(is_implicit) implicit FROM syntax WHERE rel_label IS NOT NULL"
        " GROUP BY rel_label ORDER BY n DESC").fetchall()
    rows = [r for r in rows if r[0] != "NonRel"]
    head, tail = rows[:limit], rows[limit:]
    if markdown:
        print("| Relatie | | Geschreven | Geponeerd | Wat het is | H. |")
        print("|---|---|--:|--:|---|--:|")
    for rel, ar, n, imp in head:
        nl = REL_NL.get(rel, "")
        if markdown:
            print("| `%s` | %s | %s | %s | %s | %s |"
                  % (rel, ar or "", num(n - (imp or 0)),
                     num(imp) if imp else "—", nl,
                     rel_ch(rel) or "—"))
        else:
            print("  %-14s %-14s %8s %8s  %-38s %s"
                  % (rel, ar or "", num(n - (imp or 0)), imp or "",
                     nl, rel_ch(rel) or ""))
    if tail:
        nas = [r for r in tail if NASIKH.match(r[0])]
        print("\n%d verdere labels met %s plaatsen samen, waarvan %d labels "
              "(%s plaatsen) een aparte naasikh benoemen: `subj <<lays>>`, "
              "`pred <<ka'ana>>`, `subj <<easaa>>` en zo voort."
              % (len(tail), num(sum(r[2] for r in tail)), len(nas),
                 num(sum(r[2] for r in nas))))


def nawasikh(cur, markdown=False):
    """Every naasikh the treebank names, with how often it governs."""
    rows = cur.execute(
        "SELECT rel_label, COUNT(*) n FROM syntax WHERE rel_label IS NOT NULL"
        " GROUP BY rel_label").fetchall()
    per = {}
    for rel, n in rows:
        m = NASIKH.match(rel)
        if m:
            slot, gov = m.group(1), m.group(2)
            d = per.setdefault(gov, {"subj": 0, "pred": 0})
            d[slot] += n
    order = sorted(per.items(), key=lambda kv: -(kv[1]["subj"] + kv[1]["pred"]))
    if markdown:
        print("| Naasikh | اسم (onderwerpspositie) | خبر (gezegdepositie) |")
        print("|---|--:|--:|")
    for gov, d in order[:20]:
        print(("| `%s` | %s | %s |" if markdown else "  %-12s %6s %6s")
              % (gov, num(d["subj"]), num(d["pred"])))
    print("\n%d verschillende nawaasikh, samen %s plaatsen."
          % (len(per), num(sum(d["subj"] + d["pred"] for d in per.values()))))


def muqaddar(cur, markdown=False):
    """What the grammarians read into the text but that is not written."""
    rows = cur.execute(
        "SELECT rel_label, rel_label_ar, COUNT(*) n FROM syntax WHERE is_implicit=1"
        " GROUP BY rel_label ORDER BY n DESC").fetchall()
    total = sum(n for _, _, n in rows)
    named = cur.execute("SELECT COUNT(*) FROM syntax WHERE is_implicit=1"
                        " AND token_ar != '(*)'").fetchone()[0]
    if markdown:
        print("| Positie | | Aantal | Aandeel |")
        print("|---|---|--:|--:|")
    for rel, ar, n in rows[:12]:
        line = ("| `%s` | %s | %s | %.0f%% |" if markdown
                else "  %-14s %-14s %7s  %.0f%%")
        print(line % (rel, ar or "", num(n), n / total * 100))
    tail = ("\n%s geponeerde elementen in totaal, waarvan %s met een woord "
            "ingevuld en %s alleen als lege positie."
            % (num(total), num(named), num(total - named)))
    print(tail)


def cases(cur, markdown=False):
    if markdown:
        print("| Positie | Corpuslabel | Aantal |")
        print("|---|---|--:|")
    for label, nl in (("NOM", "rafʿ"), ("ACC", "naṣb"), ("GEN", "jarr")):
        n = cur.execute('SELECT COUNT(*) FROM corpus WHERE "case"=?', (label,)).fetchone()[0]
        print(("| %s | `%s` | %s |" if markdown else "  %-6s %-6s %8s")
              % (nl, label, num(n)))
    for label, nl in (("SUBJ", "naṣb (werkwoord)"), ("JUS", "jazm")):
        n = cur.execute("SELECT COUNT(*) FROM corpus WHERE mood=?", (label,)).fetchone()[0]
        print(("| %s | `%s` | %s |" if markdown else "  %-6s %-6s %8s")
              % (nl, label, num(n)))


def rel(cur, label, markdown=False, limit=6):
    """Examples of one relation: the word, what it hangs on, and the verse."""
    rows = cur.execute(
        "SELECT s.surah, s.ayah, s.word, h.surah, h.ayah, h.word, s.token_ar"
        " FROM syntax s LEFT JOIN syntax h ON h.tid = s.head_tid"
        " WHERE s.rel_label = ? AND s.is_implicit = 0 AND s.word IS NOT NULL"
        " ORDER BY s.surah, s.ayah LIMIT ?", (label, limit * 4)).fetchall()
    if markdown:
        print("| Vers | Woord | Hangt aan |")
        print("|---|---|---|")
    shown = 0
    for s, a, w, hs, ha, hw, tok in rows:
        word = whole(cur, s, a, w)
        head = whole(cur, hs, ha, hw) if hs else None
        if not word or word == head:
            continue
        loc = "%d:%d" % (s, a)
        print(("| %s | %s | %s |" if markdown else "  %-8s %-16s %s")
              % (loc, word, head or "—"))
        shown += 1
        if shown >= limit:
            break


def irab_diff(cur, markdown=False, mode="irab"):
    """Places where the two riwayat read the final vowel differently.

    The last vowel is where the i'rab lives, so most of these are two
    analyses of one sentence. Not all: a mabni word also carries a final
    vowel, and so does a pronoun or a lengthened yaa'. Those are separated
    out rather than quietly counted as i'rab -- telling them apart is the
    first thing chapter 1 asks the reader to do."""
    rows = cur.execute(
        "SELECT surah, ayah_a, form_a, form_b FROM riwaya_diff"
        " WHERE riwaya_a='hafs' AND riwaya_b='warsh' AND kind='farsh'"
        " ORDER BY surah, ayah_a").fetchall()
    sys.path.insert(0, str(Path(__file__).parent))
    from riwaya_translit import key
    irab, mabni = [], []
    for s_, a, fa, fb in rows:
        ta, tb = key(fa), key(fb)
        if not (len(ta) == len(tb) and ta[:-1] == tb[:-1]
                and ta[-1] in "aui" and tb[-1] in "aui"):
            continue
        why = not_irab(fa, (s_, a))
        (mabni if why else irab).append((s_, a, fa, fb, why))
    rows = mabni if mode == "mabni" else irab
    last = {"mabni": "Waarom geen iʿrāb", "book": "Waar het in dit boek staat"}.get(mode)
    if markdown:
        print("| Vers | Ḥafṣ | Warsh |%s" % (" %s |" % last if last else ""))
        print("|---|---|---|%s" % ("---|" if last else ""))
    for s_, a, fa, fb, why in rows:
        loc = "%d:%d" % (s_, a)
        extra = why if mode == "mabni" else IRAB_CH.get((s_, a), "")
        if last:
            print(("| %s | %s | %s | %s |" if markdown else "  %-8s %-18s %-18s %s")
                  % (loc, fa, fb, extra))
        else:
            print(("| %s | %s | %s |" if markdown else "  %-8s %-18s %s") % (loc, fa, fb))
    print("\n%d plaatsen." % len(rows))


# A final vowel is not always an i'rab ending. Thirteen of these places
# carry one for another reason, and no string rule tells them apart from the
# real endings: نَكُونَ and تُبَشِّرُونَ end alike, and so do اللَّهِ and عَلَيْهِ. So
# they were read, like the farsh list itself, and named here with the reason.
YAA_IDAAFA = "yāʾ al-iḍāfa: de bezitters-yāʾ in بُنَيَّ, geen naamvalsuitgang"
NOT_IRAB = {
    "\u064a\u064e\u0670\u0628\u064f\u0646\u064e\u064a\u0651\u064e": YAA_IDAAFA,  # yaa bunayya, 6x
    "\u062a\u064f\u0628\u064e\u0634\u0651\u0650\u0631\u064f\u0648\u0646\u064e":  # tubashshiruuna 15:54
        "yāʾ zāʾida: de weggelaten yāʾ van تُبَشِّرُونَنِي",
    "\u0639\u064e\u0644\u064e\u064a\u06e1\u0647\u064f":  # 'alayhu 48:10
        "de klinker van het voornaamwoord هُ; ه is mabnī",
}
# Where each i'rab difference is discussed in docs/nahw-nl.md.
IRAB_CH = {
    (2, 177): "6 — mubtadaʾ en ḫabar", (2, 184): "17 — de iḍāfa",
    (2, 189): "6", (2, 214): "20 — de wijzen van het werkwoord",
    (4, 95): "16 — istithnāʾ", (5, 95): "17",
    (5, 119): "17 — de ẓarf op een zin", (6, 27): "20",
    (6, 55): "13 — overgankelijk of niet", (7, 26): "19 — ʿaṭf",
    (8, 18): "17 — deelwoord met of zonder tanwīn", (10, 23): "14 — mafʿūl muṭlaq",
    (11, 71): "3 — ġayr munṣarif", (13, 4): "19 — ʿaṭf", (14, 2): "19 — badal",
    (16, 12): "13 — ishtighāl", (19, 34): "14",
    (21, 47): "8 — kāna nāqiṣa of tāmma", (23, 92): "19 — badal",
    (24, 9): "9 — inna en anna", (30, 10): "8 — ism en ḫabar van kāna",
    (31, 16): "8", (34, 3): "19", (34, 17): "12 — nāʾib al-fāʿil",
    (36, 5): "7 — de weggelaten ḫabar", (36, 39): "13 — ishtighāl",
    (37, 126): "19 — badal", (38, 84): "19 — ʿaṭf", (42, 35): "20",
    (42, 51): "20", (44, 7): "19 — badal", (78, 37): "19",
    (111, 4): "19 — naṣb ʿalā al-dhamm",
}
JUNCTION = {  # the vowel that removes a sukuun before the next word's wasl-hamza
    (7, 143): "hulpklinker voor een waṣl-hamza (وَلَٰكِنِ ٱنظُرْ); لكن is mabnī",
    (12, 31): "hulpklinker voor een waṣl-hamza (وَقَالَتِ ٱخْرُجْ); de تْ is mabnī",
}


def not_irab(form, place):
    """Why this final vowel is not an i'rab ending -- or None if it is."""
    return NOT_IRAB.get(form) or JUNCTION.get(place)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    markdown = "--markdown" in sys.argv
    cur = sqlite3.connect(f"file:{DB}?mode=ro", uri=True).cursor()
    if not args:
        print(__doc__)
        return
    mode = args[0]
    if mode == "relations":
        relations(cur, markdown)
    elif mode == "muqaddar":
        muqaddar(cur, markdown)
    elif mode == "nawasikh":
        nawasikh(cur, markdown)
    elif mode == "cases":
        cases(cur, markdown)
    elif mode == "irab-diff":
        irab_diff(cur, markdown)
    elif mode == "irab-mabni":
        irab_diff(cur, markdown, mode="mabni")
    elif mode == "irab-book":
        irab_diff(cur, markdown, mode="book")
    elif mode == "rel" and len(args) > 1:
        rel(cur, args[1], markdown)
    else:
        sys.exit("onbekende modus: %s" % mode)


if __name__ == "__main__":
    main()
