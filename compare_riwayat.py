#!/usr/bin/env python3
"""Compare two riwayat word by word and store what actually differs.

A *qiraa* is the reading of a qari; a *riwaya* is one pupil's transmission of
it. Hafs and Warsh are riwayat, and they belong to two different qiraa'at --
Hafs from Aasim al-Kufi, Warsh from Naafi' al-Madani -- which is why a
comparison of the two is not a comparison of two readings of one qari.

    Naafi' al-Madani   (d. 169)  ->  Qaaloon, Warsh
    Ibn Kathir al-Makki(d. 120)  ->  al-Bazzi, Qunbul
    Abu 'Amr al-Basri  (d. 154)  ->  al-Doori, al-Soosi
    'Aasim al-Kufi     (d. 127)  ->  Shu'ba, Hafs

The comparison cannot be a text diff. The two mushaf traditions write the same
sound with different signs -- dagger alif against written alif, small waw
against waw, two glyph shapes for every tanwin, different hamza seats, a
different mark for the wasl alif -- so comparing letters measures orthography.
Every word is therefore transliterated first (riwaya_translit.py) and the
transliterations are compared: that measures the recitation, which is what a
farsh difference is.

The verse division differs in 50 suras, so a join on (surah, ayah) breaks.
Each sura is aligned on its word sequence instead, with difflib over the
consonant skeleton, and the two ayah numbers are both recorded.

**The classification holds for Hafs and Warsh only.** Its rules were written
by reading what the Warsh mushaf does -- its signs for the wasl alif, its
naql, its sila, its treatment of the hamza -- and checked against that pair.
They do not transfer: the Doori and Soosi packages write the wasl alif as a
bare vowelled alif, which those rules read as a difference in the text, and
al-Soosi's idghaam kabir is a systematic feature no rule here knows. Running
the classifier over those pairs produced thousands of "farsh" rows that are
nothing of the sort. So every pair beside Hafs-Warsh is stored with its
differences located but not labelled, `kind = 'ongeclassificeerd'`, and the
raw count is all this database claims about it. That count is sound: it is a
comparison of two texts, and it is what shows a within-qiraa pair sitting an
order of magnitude closer than a between-qiraa one.

What comes out is sorted into three kinds:

  usul       a rule of recitation that applies wherever its condition occurs:
             the sila of the mim, naql, the treatment of the hamza, the ya of
             idafa. Real differences, but not word-specific -- a per-word
             table would record the same rule hundreds of times.
  notatie    the same recitation written with different signs.
  farsh      what no rule explains: the word-by-word differences, the layer
             this table exists for.

Differences of vowel length and of short vowels are deliberately never folded
away: maalik / malik at 1:4 is exactly such a difference and it is farsh.

Idempotent: drops and rebuilds both tables.

  python3 compare_riwayat.py                     rebuild the tables
  python3 compare_riwayat.py --markdown          also rewrite docs/hafs-warsh.md
"""

import argparse
import collections
import csv
import difflib
import re
import sqlite3
import sys
from pathlib import Path

from riwaya_translit import key

HERE = Path(__file__).parent
DB = HERE / "quran.db"
# code -> (file, sura column, ayah column). The Hafs package names its sura
# column differently from the other seven; nothing else about them differs.
SRC = {code: (HERE / "sources" / ("riwaya_%s.csv" % code),
              "sora" if code == "hafs" else "sura_no", "aya_no")
       for code in ("hafs", "warsh", "qaloon", "bazzi", "qumbul",
                    "doori", "soosi", "shouba")}

# Which pairs to compare, and why these. Every riwaya is put beside Hafs,
# because that is the transmission most readers will know and it gives each
# of the eight a comparison. Beside that, the three remaining pairs that sit
# *within* one qiraa (Hafs-Shu'ba is already in the first set), because the
# contrast between a within-qiraa pair and a between-qiraa one is the whole
# point of having more than two: Hafs and Shu'ba transmit one reading, Hafs
# and Warsh two different ones, and the counts say so plainly.
# The one pair whose classification was built and reviewed; see the docstring
CLASSIFIED_PAIR = ("hafs", "warsh")

PAIRS = [("hafs", "warsh"), ("hafs", "qaloon"), ("hafs", "bazzi"),
         ("hafs", "qumbul"), ("hafs", "doori"), ("hafs", "soosi"),
         ("hafs", "shouba"),
         ("qaloon", "warsh"), ("bazzi", "qumbul"), ("doori", "soosi")]
DOC = HERE / "docs" / "hafs-warsh.md"
REVIEW = HERE / "farsh_review.tsv"

# The eight riwayat King Fahd Glorious Quran Printing Complex publishes, with
# the qari each transmits from. The complex's own release notes file al-Bazzi
# and Qunbul under Abu 'Amr al-Basri; they transmit from Ibn Kathir al-Makki,
# and the reader relation below is the corrected one.
RIWAYAT = [
    # code, riwaya ar, riwaya en, died, qari ar, qari en, died, region, version
    ("qaloon", "قالون", "Qaaloon", 220, "نافع المدني", "Naafi' al-Madani", 169,
     "Libie, Tunesie, delen van Mauritanie", "10"),
    ("warsh", "ورش", "Warsh", 197, "نافع المدني", "Naafi' al-Madani", 169,
     "Maghreb, West- en Centraal-Afrika, West-Europa", "10"),
    ("bazzi", "البزي", "al-Bazzi", 250, "ابن كثير المكي", "Ibn Kathir al-Makki", 120,
     "vooral onder specialisten", "7"),
    ("qumbul", "قنبل", "Qunbul", 291, "ابن كثير المكي", "Ibn Kathir al-Makki", 120,
     "vooral onder specialisten", "7"),
    ("doori", "الدوري", "al-Doori", 246, "أبو عمرو البصري", "Abu 'Amr al-Basri", 154,
     "Soedan en Oost-Afrika", "9"),
    ("soosi", "السوسي", "al-Soosi", 261, "أبو عمرو البصري", "Abu 'Amr al-Basri", 154,
     "vooral onder specialisten", "9"),
    ("shouba", "شعبة", "Shu'ba", 193, "عاصم الكوفي", "'Aasim al-Kufi", 127,
     "vooral onder specialisten", "8"),
    ("hafs", "حفص", "Hafs", 180, "عاصم الكوفي", "'Aasim al-Kufi", 127,
     "het grootste deel van de moslimwereld", "18"),
]
SOURCE_DATE = {"hafs": "2021-10-25", "warsh": "2021-08-05", "qaloon": None,
               "bazzi": None, "qumbul": None, "doori": None, "soosi": None,
               "shouba": None}

VOWELS = set("auiAUIN")
LONG = str.maketrans("AUI", "aui")

fold_len = lambda x: x.translate(LONG)
fold_gem = lambda x: re.sub(r"(.)\1", r"\1", x)
fold_art = lambda x: re.sub(r"لل([aui]?)", "ل", x)
fold_ham = lambda x: x.replace("'", "")
fold_ham2 = lambda x: re.sub(r"'[aui]?", "", x)
fold_sil = lambda x: x.replace("uw", "u").replace("iy", "i")
fold_mq = lambda x: x.replace("yA", "A")
fold_iv = lambda x: re.sub(r"^'[aui]", "'", x)
fold_head = lambda x: re.sub(r"^('[aui]?|A|w|y)", "", x, count=1)
fold_wu = lambda x: x.replace("'U", "'w").replace("'I", "'y")
fold_nq = lambda x: x.replace("uA", "u").replace("iA", "i")
fold_fy = lambda x: re.sub("ay$", "A", x)

# particles whose final vowel is only the helper spoken at a junction
JUNCTION = {"من", "عن", "'ن", "قل", "بل", "قد", "لقد", "wلقد", "فقل", "w'ن",
            "'ذ", "'م", "'w", "w'ذ", "فمن", "wمن", "wقد", "ثم", "لكن", "wلكن",
            "فقد", "كل", "'ن'"}
MUQ = {"Aلم", "Aلر", "طسم", "Aلمر", "كهيعص", "حم", "يس", "طه", "ص", "ق", "ن",
       "عسق", "طس", "Aلمص"}
MUQATTAAT_SURAS = {2, 3, 7, 10, 11, 12, 13, 14, 15, 19, 20, 26, 27, 28, 29, 30,
                   31, 32, 36, 38, 40, 41, 42, 43, 44, 45, 46, 50, 68}
HAMZA = set("ءأإؤئٓٔ")

KIND = {
    "farsh_candidate": ("farsh", "verschil in de lezing zelf"),
    "word_delete": ("farsh", "woord staat niet in de tweede riwaya"),
    "word_insert": ("farsh", "woord staat alleen in de tweede riwaya"),
    "hamza_treatment": ("usul", "hamza: ibdaal, tashiel, naql"),
    "naql": ("usul", "de klinker van een volgende hamza op de laatste letter"),
    "naql_alif": ("notatie", "zwijgende alif na naql"),
    "sila_mim": ("usul", "silat al-miem: hoem verbonden als hoemoe"),
    "sila_ha": ("usul", "silat al-haa"),
    "yaa_idafa": ("usul", "yaa al-idaafa geopend"),
    "yaa_zaida": ("usul", "yaa zaa-ida hersteld"),
    "junction_vowel": ("usul", "hulpklinker bij wasl"),
    "article_lam": ("notatie", "de laam van al- met of zonder shadda"),
    "gemination_notation": ("notatie", "idghaam met of zonder shadda gemarkeerd"),
    "maqsura_notation": ("notatie", "alif maqsoera als ى of als ي"),
    "initial_alif_notation": ("notatie", "hamza aan het woordbegin, andere zetel"),
    "wasl_notation": ("notatie", "hamzat al-wasl anders geschreven"),
    "unwritten_vowel": ("notatie", "klinker op de eerste letter ongeschreven"),
    "silent_letter": ("notatie", "letter geschreven maar niet gesproken"),
    "muqattaat": ("notatie", "de losse letters, gespeld tegenover niet gespeld"),
    "reviewed:alignment_or_word_split": ("uitgesloten", "woordgrens of uitlijning"),
    "reviewed:hamza_vowel_notation": ("uitgesloten", "hamza met taqliel-teken"),
    "reviewed:hamza_seat_notation": ("uitgesloten", "hamza op een andere zetel"),
    "reviewed:muqattaat": ("uitgesloten", "losse letters"),
    "reviewed:hand": ("uitgesloten", "met de hand beoordeeld als notatie"),
    "reviewed:onzeker": ("onzeker", "met de hand bekeken, niet beslist"),
}


def cons(w):
    return "".join(c for c in key(w) if c not in VOWELS)


def load(path, sura_col, ayah_col):
    out = collections.defaultdict(list)
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            out[int(row[sura_col])].append((int(row[ayah_col]), row["aya_text"]))
    for s in out:
        out[s].sort()
    return out


def flat(rows):
    return [(ayah, w) for ayah, txt in rows
            for w in re.split(r"[\s ]+", txt) if cons(w)]


def qari_of(code):
    for c, _ar, _en, _d, _qa, qe, _qd, _r, _v in RIWAYAT:
        if c == code:
            return qe
    return None


def pair_type(a, b):
    """A pair sits within one qiraa when both transmit from the same qari."""
    return "binnen" if qari_of(a) == qari_of(b) else "tussen"


TEXTS = {}


def text_of(code):
    if code not in TEXTS:
        path, sura_col, ayah_col = SRC[code]
        TEXTS[code] = load(path, sura_col, ayah_col)
    return TEXTS[code]


def sites(a="hafs", b="warsh"):
    """Every place the two texts diverge, before classification."""
    a_rows, b_rows = text_of(a), text_of(b)
    found = []
    for sura in range(1, 115):
        aw, bw = flat(a_rows[sura]), flat(b_rows[sura])
        ak, bk = [cons(w) for _, w in aw], [cons(w) for _, w in bw]
        sm = difflib.SequenceMatcher(None, ak, bk, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    x, y = aw[i1 + k], bw[j1 + k]
                    if key(x[1]) != key(y[1]):
                        found.append(dict(sura=sura, ah=x[0], aw=y[0], tag="replace",
                                          a=x[1], b=y[1]))
            else:
                ha = [w for _, w in aw[i1:i2]]
                wa = [w for _, w in bw[j1:j2]]
                ah = aw[min(i1, len(aw) - 1)][0]
                aa = bw[min(j1, len(bw) - 1)][0]
                # difflib merges neighbouring changed words into one block;
                # split it back when both sides hold the same number of words,
                # so each difference is judged on its own
                if tag == "replace" and len(ha) == len(wa) > 1:
                    for h, w in zip(ha, wa):
                        found.append(dict(sura=sura, ah=ah, aw=aa, tag=tag,
                                          a=h, b=w))
                else:
                    found.append(dict(sura=sura, ah=ah, aw=aa, tag=tag,
                                      a=" ".join(ha), b=" ".join(wa)))
    return found


def strip_usul(th, tw):
    """Remove the suffix-level usul features; returns (th, tw, tags)."""
    tags = []
    if tw.endswith("U") and tw[:-1].endswith("م") and th.endswith("م"):
        tw = tw[:-1]; tags.append("sila_mim")
    if not tags and len(th) > 1 and th[-2] == "ه" and len(tw) > 1 \
       and tw[-2] == "ه" and th[:-1] == tw[:-1] and fold_len(th) == fold_len(tw):
        tw = th; tags.append("sila_ha")
    if not tags and tw == th + "a" and th.endswith("iy"):
        tw = th; tags.append("yaa_idafa")
    if not tags and th.endswith("iya") and tw == th[:-3] + "I":
        tw = th; tags.append("yaa_idafa")
    if not tags and th.endswith("I") and tw == th[:-1] + "iya":
        tw = th; tags.append("yaa_idafa")
    if not tags and len(tw) == len(th) + 1 and tw[:-1] == th and tw[-1] in "aui":
        tw = th; tags.append("naql")
    return th, tw, tags


def classify(th, tw):
    if th == tw:
        return "identical"
    th, tw, tags = strip_usul(th, tw)
    if th == tw:
        return tags[0]
    suffix = "+" + tags[0] if tags else ""
    for v in "aui":
        if th == "'" + v + tw or tw == "'" + v + th:
            return "wasl_notation" + suffix
    if fold_gem(th) == fold_gem(tw):
        return "gemination_notation" + suffix
    if fold_art(th) == fold_art(tw) or fold_art(fold_gem(th)) == fold_art(fold_gem(tw)):
        return "article_lam" + suffix
    if (th in MUQ or tw in MUQ or re.sub("[aui]", "", tw) in MUQ) and len(th) > 1:
        return "muqattaat" + suffix
    if ("yA" in tw) != ("yA" in th) and (
            fold_mq(th) == fold_mq(tw)
            or fold_len(fold_mq(th)) == fold_len(fold_mq(tw))
            or vowels_only_dropped(fold_mq(th), fold_mq(tw))):
        return "maqsura_notation" + suffix
    if fold_iv(th) == fold_iv(tw):
        return "unwritten_vowel" + suffix
    if fold_sil(th) == fold_sil(tw):
        return "silent_letter" + suffix
    if th.endswith("A") != tw.endswith("A") and (th.endswith("ay") or tw.endswith("ay")) \
       and (fold_fy(th) == fold_fy(tw)
            or fold_nq(fold_ham(fold_fy(th))) == fold_nq(fold_ham(fold_fy(tw)))):
        return "maqsura_notation" + suffix
    if th.endswith("wA") and tw.endswith("wiA") and th[:-2] == tw[:-3]:
        return "junction_vowel" + suffix
    if th.endswith("i") and tw == th[:-1] + "I":
        return "yaa_zaida" + suffix
    # a vowel the Maghribi mushaf leaves unwritten on the word's first letter
    if th[1:] == tw[1:] and len(th) == len(tw) + 1 and th[1] in "aui" \
       or (len(th) > 1 and len(tw) > 1 and th[2:] == tw[1:]
           and th[0] == tw[0] and th[1] in "aui"):
        return "unwritten_vowel" + suffix
    if fold_head(th) == fold_head(tw) or fold_head(th) == tw or th == fold_head(tw) \
       or fold_wu(th) == fold_wu(tw) or fold_head(fold_wu(th)) == fold_head(fold_wu(tw)):
        return "initial_alif_notation" + suffix
    if fold_nq(th) == fold_nq(tw):
        return "naql_alif" + suffix
    if len(th) == len(tw) and th[:-1] == tw[:-1] and th[-1] in "aui" \
       and tw[-1] in "aui" and re.sub("[aui]", "", th) in JUNCTION:
        return "junction_vowel" + suffix
    # the hamza, but only where the two actually differ in how many they have,
    # so that a pure difference of vowel length is never absorbed here
    if th.count("'") != tw.count("'"):
        if fold_nq(fold_ham(th)) == fold_nq(fold_ham(tw)) or \
           fold_nq(fold_ham2(th)) == fold_nq(fold_ham2(tw)) or \
           fold_ham2(th) == fold_ham2(tw) or \
           vowels_only_dropped(fold_ham2(th), fold_ham2(tw)) or \
           fold_mq(fold_ham2(th)) == fold_mq(fold_ham2(tw)) or \
           fold_len(fold_ham2(th)) == fold_len(fold_ham2(tw)):
            return "hamza_treatment" + suffix
        a, b = fold_ham(th), fold_ham(tw)
        for f in (lambda x: x, fold_len, fold_gem, fold_art, fold_sil, fold_mq,
                  fold_iv, lambda x: fold_mq(fold_len(x)),
                  lambda x: fold_iv(fold_sil(x)),
                  lambda x: fold_len(fold_gem(x)), lambda x: fold_len(fold_art(x)),
                  lambda x: fold_len(fold_sil(x)), lambda x: fold_gem(fold_art(x))):
            if f(a) == f(b):
                return "hamza_treatment" + suffix
    return "farsh_candidate" + suffix


def vowels_only_dropped(a, b):
    """True when one string is the other with some short vowels left unwritten."""
    if re.sub("[aui]", "", a) != re.sub("[aui]", "", b):
        return False
    long_, short_ = (a, b) if len(a) > len(b) else (b, a)
    i = 0
    for ch in long_:
        if i < len(short_) and short_[i] == ch:
            i += 1
        elif ch not in "aui":
            return False
    return i == len(short_)


def second_look(row):
    """A hand review over what the rules left as farsh.

    Reading the remaining word pairs one by one turned up further groups no
    rule had caught but that are still not farsh. Each is written as a test on
    the data rather than as a list of copied words, so the judgment is visible
    and reversible.
    """
    h, w = row["a"].strip(), row["b"].strip()
    th, tw = row["th"], row["tw"]
    if " " in h or " " in w:
        return "reviewed:alignment_or_word_split"
    # the Warsh file does not count the basmala of al-Faatiha as a verse: those
    # words are missing from the file, not from the riwaya. A single word on
    # one side only is a real difference (57:24 huwa) and stays.
    if (not h or not w) and row["sura"] == 1:
        return "reviewed:alignment_or_word_split"
    if row["ah"] == 1 and row["sura"] in MUQATTAAT_SURAS \
       and len(re.sub("[aui]", "", th)) <= 6:
        return "reviewed:muqattaat"
    if set(h) & HAMZA and set(w) & HAMZA:
        if re.sub("[aui]", "", th) == re.sub("[aui]", "", tw):
            return "reviewed:hamza_vowel_notation"
        if fold_ham(re.sub("[aui]", "", th)) == fold_ham(re.sub("[aui]", "", tw)):
            return "reviewed:hamza_seat_notation"
    return None


def hand_verdicts():
    """The verdicts of reading the farsh list pair by pair.

    Rules ran over these rows already, and a rule cannot see what a reader
    sees: two attempts to catch the residue automatically flagged
    kalimatu / kalimaatu (singular against plural) and al-birra / al-birru
    (a case ending) as mere notation. What looks like noise here -- a dagger
    alif, a final vowel -- is often the farsh itself. So the last pass is a
    person reading all 468 word pairs, and what that person decided lives in
    farsh_review.tsv rather than in the code: one line per pair, with a
    reason, so every verdict can be looked up and argued with.

    Only two verdicts appear there. A pair is either notation after all, or
    it could not be settled -- the six rows of allaatie / allatie, where the
    Warsh mushaf leaves out the dagger alif and nothing here says whether
    that is the reading or the spelling."""
    out = {}
    if not REVIEW.exists():
        return out
    with open(REVIEW, encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="\t")
        next(reader, None)
        for row in reader:
            if len(row) >= 4:
                out[(row[0], row[1])] = (row[2], row[3])
    return out


def classified(a="hafs", b="warsh"):
    rows = sites(a, b)
    for r in rows:
        r["th"], r["tw"] = key(r["a"]), key(r["b"])
        if r["tag"] != "replace":
            r["cls"] = "word_" + r["tag"]
        else:
            r["cls"] = classify(r["th"], r["tw"])
        if r["cls"] == "identical":
            # the letters agree and only the word boundary moved
            r["cls"] = "reviewed:alignment_or_word_split"
        if r["cls"].startswith("farsh_candidate") or r["cls"].startswith("word_"):
            again = second_look(r)
            if again:
                r["cls"] = again
    if (a, b) == CLASSIFIED_PAIR:
        verdicts = hand_verdicts()
        for r in rows:
            if not (r["cls"].startswith("farsh_candidate")
                    or r["cls"].startswith("word_")):
                continue
            v = verdicts.get((r["a"].strip(), r["b"].strip()))
            if v:
                r["cls"] = ("reviewed:hand" if v[0] == "geen-farsh"
                            else "reviewed:onzeker")
    return rows


def write(conn, rows):
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS riwayat")
    cur.execute("""CREATE TABLE riwayat (
        code TEXT PRIMARY KEY, riwaya_ar TEXT, riwaya_en TEXT,
        riwaya_died_ah INTEGER, qari_ar TEXT, qari_en TEXT, qari_died_ah INTEGER,
        region TEXT, kfgqpc_version TEXT, source_date TEXT, in_database INTEGER)""")
    for code, ra, re_, rd, qa, qe, qd, region, ver in RIWAYAT:
        cur.execute("INSERT INTO riwayat VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (code, ra, re_, rd, qa, qe, qd, region, ver,
                     SOURCE_DATE.get(code), 1 if code in SRC else 0))

    cur.execute("DROP TABLE IF EXISTS riwaya_diff")
    cur.execute("""CREATE TABLE riwaya_diff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        riwaya_a TEXT, riwaya_b TEXT, pair_type TEXT, classified INTEGER,
        surah INTEGER, ayah_a INTEGER, ayah_b INTEGER,
        form_a TEXT, form_b TEXT, translit_a TEXT, translit_b TEXT,
        class TEXT, kind TEXT)""")
    for a, b in PAIRS:
        known = (a, b) == CLASSIFIED_PAIR
        for r in rows[(a, b)]:
            base = r["cls"].split("+")[0]
            cur.execute(
                "INSERT INTO riwaya_diff (riwaya_a, riwaya_b, pair_type,"
                " classified, surah, ayah_a, ayah_b, form_a, form_b,"
                " translit_a, translit_b, class, kind)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (a, b, pair_type(a, b), 1 if known else 0,
                 r["sura"], r["ah"], r["aw"], r["a"].strip(), r["b"].strip(),
                 r["th"] if known else None, r["tw"] if known else None,
                 r["cls"] if known else None,
                 KIND.get(base, ("onbekend", ""))[0] if known
                 else "ongeclassificeerd"))
    cur.execute("CREATE INDEX idx_riwaya_diff_verse ON riwaya_diff(surah, ayah_a)")
    cur.execute("CREATE INDEX idx_riwaya_diff_kind ON riwaya_diff(kind)")
    cur.execute("CREATE INDEX idx_riwaya_diff_pair ON riwaya_diff(riwaya_a, riwaya_b)")
    conn.commit()


def summary(rows):
    """One line per pair: how far apart the two transmissions are."""
    out = []
    for a, b in PAIRS:
        n = len(rows[(a, b)])
        if (a, b) == CLASSIFIED_PAIR:
            cnt = collections.Counter(
                KIND.get(r["cls"].split("+")[0], ("onbekend",))[0]
                for r in rows[(a, b)])
            out.append((a, b, pair_type(a, b), n, cnt["farsh"], cnt["usul"],
                        cnt["notatie"]))
        else:
            out.append((a, b, pair_type(a, b), n, None, None, None))
    return out


def markdown(conn, rows):
    cur = conn.cursor()
    names = dict(cur.execute("SELECT number, name_ar FROM surahs")) \
        if cur.execute("SELECT name FROM sqlite_master WHERE name='surahs'").fetchone() \
        else {}
    main_rows = rows[("hafs", "warsh")]
    farsh = [r for r in main_rows
             if KIND.get(r["cls"].split("+")[0], ("", ""))[0] == "farsh"]
    counts = collections.Counter(r["cls"].split("+")[0] for r in main_rows)
    out = ["# Hafs tegenover Warsh\n",
           "*Gegenereerd door `compare_riwayat.py --markdown`; niet met de hand "
           "bijwerken. Twee riwaayaat uit twee verschillende qiraa-aat: Hafs "
           "`عن` Aasim al-Koefie, Warsh `عن` Naafi3 al-Madanie. Beide zijn "
           "Qoeraan; dit is geen lijst van afwijkingen.*\n",
           "## Alle vergeleken paren\n",
           "| Paar | | Plaatsen | farsh | usul | notatie |",
           "|---|---|--:|--:|--:|--:|"]
    dash = lambda v: format(v, ",") if v is not None else "—"
    for a, b, kind, total, f, u, n in summary(rows):
        out.append("| %s – %s | %s qiraa-a | %s | %s | %s | %s |"
                   % (a, b, "binnen een" if kind == "binnen" else "tussen twee",
                      format(total, ","), dash(f), dash(u), dash(n)))
    out.append("")
    out.append("Het verschil tussen die twee soorten paren is de reden om meer "
               "dan twee riwaayaat te vergelijken: twee overleveringen van "
               "*dezelfde* qaari- liggen een orde van grootte dichter bij "
               "elkaar dan twee van verschillende qurraa-.\n")
    out.append("De kolommen farsh, usul en notatie staan alleen bij Hafs-Warsh "
               "ingevuld. De classificatie is op dat paar gebouwd en nagelopen "
               "en gaat niet mee naar de andere: de pakketten van Doorie en "
               "Soesie schrijven de wasl-alif anders, en de idghaam kabier van "
               "al-Soesie is een systematisch kenmerk dat geen regel hier kent. "
               "Wat die paren wel geven is de telling, en die is een "
               "tekstvergelijking en geen oordeel.\n")
    out.append("## Hafs – Warsh in detail\n")
    out.append("| klasse | soort | plaatsen | wat het is |")
    out.append("|---|---|--:|---|")
    for cls, n in counts.most_common():
        soort, uitleg = KIND.get(cls, ("onbekend", ""))
        out.append("| `%s` | %s | %d | %s |" % (cls, soort, n, uitleg))
    out.append("| **totaal** | | **%d** | |\n" % sum(counts.values()))
    out.append("Verschillen in klinkerlengte en korte klinkers zijn met opzet "
               "niet weggevouwen: `maalik` / `malik` in 1:4 is precies zo'n "
               "verschil en dat is farsh.\n")
    out.append("### Farsh al-huroef: %d plaatsen, %d woordparen, %d ayaat, %d soerahs\n"
               % (len(farsh),
                  len({(r["a"].strip(), r["b"].strip()) for r in farsh}),
                  len({(r["sura"], r["ah"]) for r in farsh}),
                  len({r["sura"] for r in farsh})))
    out.append("| soerah:ayah | Hafs | Warsh |")
    out.append("|---|---|---|")
    for r in sorted(farsh, key=lambda x: (x["sura"], x["ah"])):
        out.append("| %d:%d %s | %s | %s |"
                   % (r["sura"], r["ah"], names.get(r["sura"], ""),
                      r["a"].strip() or "—", r["b"].strip() or "—"))
    DOC.parent.mkdir(exist_ok=True)
    DOC.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", action="store_true",
                    help="also rewrite docs/hafs-warsh.md")
    args = ap.parse_args()

    for path, _s, _a in SRC.values():
        if not path.exists():
            sys.exit("ontbreekt: %s" % path)

    rows = {}
    for a, b in PAIRS:
        rows[(a, b)] = classified(a, b)

    conn = sqlite3.connect(DB)
    write(conn, rows)

    total = sum(len(v) for v in rows.values())
    print("riwaya_diff: %s plaatsen over %d paren" % (format(total, ","), len(PAIRS)))
    print("  %-16s %-9s %8s %7s %7s %8s"
          % ("paar", "qiraa-a", "plaatsen", "farsh", "usul", "notatie"))
    dash = lambda v: format(v, ",") if v is not None else "—"
    for a, b, kind, tot, f, u, n in summary(rows):
        print("  %-16s %-9s %8s %7s %7s %8s"
              % ("%s-%s" % (a, b), kind, format(tot, ","), dash(f), dash(u),
                 dash(n)))
    print("  (alleen hafs-warsh is geclassificeerd; zie de docstring)")
    if args.markdown:
        print("  docs/hafs-warsh.md: %d regels" % markdown(conn, rows))
    conn.close()


if __name__ == "__main__":
    main()
