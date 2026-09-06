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

All ten pairs are classified. What differs between the packages is how they
spell things, and that belongs in the transliteration rather than in the
comparison: Qaaloon, al-Doori and al-Soosi write hamzat al-wasl as a plain
alif carrying its vowel and never use the alef wasla letter, where Hafs and
the other Kufi packages always do and Warsh marks it with a sign. Telling the
transliteration which convention a file follows removes several thousand
false differences per pair on its own.

The features that belong to some riwayat and not others each have a class.
al-Soosi's idghaam kabir takes the final vowel of a word into the next, which
al-Doori -- the same qiraa from the same qari, without that rule -- is used as
the control for, because a vowel that simply goes can as easily be a jazm.
Imaala and taqliil are read off the marks the mushaf itself writes, which
separate cleanly from the iqlaab and wasl markers by what they sit on. And
`huwa` and `hiya` lose their vowel after a prefix in Qaaloon, al-Doori and
al-Soosi and nowhere else.

**One pair has also been read.** Rules classify; only Hafs-Warsh has had its
farsh list gone through word by word afterwards, and the verdicts of that
reading are in `farsh_review.tsv`. It struck 95 rows the rules had wrongly
called farsh, 15 per cent of what they proposed. The other nine pairs carry
the rule verdict alone, so their farsh figure is an upper bound and `reviewed`
is 0.

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

from riwaya_translit import PLAIN_WASL, key

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
# Every pair is classified by rule. Only this one has also been read pair by
# pair afterwards, and only it carries the verdicts in farsh_review.tsv.
REVIEWED_PAIR = ("hafs", "warsh")

# A riwaya that applies idghaam kabiir, and the sibling transmission of the
# same qiraa that does not, which serves as its control; see undo_idghaam.
IDGHAAM_KABIR = {"soosi": "doori"}

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
# These three signs each do two jobs, told apart by what they sit on. After a
# vowel sign U+06ED is the iqlaab marker and U+06EA and U+06EC mark hamzat
# al-wasl, and the transliteration resolves all three. After a bare letter
# they mark imaala and taqliil, which are differences in the recitation and
# not in the spelling. Warsh writes 1,689 of them, al-Soosi 1,208, al-Doori
# 1,157; Hafs writes one. The transliteration ignores them, so they add no
# differences of their own, and they are read here only to give a difference
# that is there anyway its right name.
IMALA_MARKS = "\u06ea\u06ec\u06ed"
VOWEL_SIGNS = "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652"


def has_imala(w):
    """True when the word carries an imaala or taqliil mark on a letter."""
    return any(c in IMALA_MARKS and (i == 0 or w[i - 1] not in VOWEL_SIGNS)
               for i, c in enumerate(w))

KIND = {
    "farsh_candidate": ("farsh", "verschil in de lezing zelf"),
    "word_delete": ("farsh", "woord staat niet in de tweede riwaya"),
    "word_insert": ("farsh", "woord staat alleen in de tweede riwaya"),
    "hamza_treatment": ("usul", "hamza: ibdaal, tashiel, naql"),
    "naql": ("usul", "de klinker van een volgende hamza op de laatste letter"),
    "naql_alif": ("notatie", "zwijgende alif na naql"),
    "sila_mim": ("usul", "silat al-miem: hoem verbonden als hoemoe"),
    "sila_ha": ("usul", "silat al-haa"),
    "idghaam_kabir": ("usul", "idghaam kabier: klinker weg, volgende letter verdubbeld"),
    "ha_iskan": ("usul", "hoewa en hiya zonder klinker na een voorvoegsel"),
    "imaala": ("usul", "imaala of taqliel: de aa wordt naar de ee getrokken"),
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


def tr(w, code):
    """Transliterate a word from one package, with that package's convention."""
    return key(w, plain_wasl=code in PLAIN_WASL)


def cons(w, code="hafs"):
    return "".join(c for c in tr(w, code) if c not in VOWELS)


def load(path, sura_col, ayah_col):
    out = collections.defaultdict(list)
    with open(path, encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            out[int(row[sura_col])].append((int(row[ayah_col]), row["aya_text"]))
    for s in out:
        out[s].sort()
    return out


def flat(rows, code="hafs"):
    return [(ayah, w) for ayah, txt in rows
            for w in re.split(r"[\s ]+", txt) if cons(w, code)]


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
    # When b applies idghaam kabiir, every row carries the control riwaya's
    # form of the same word so that a rule can be told from a jazm; when the
    # control is a itself, the difference between the two already says it.
    control = IDGHAAM_KABIR.get(b)
    c_rows = text_of(control) if control and control != a else None
    found = []
    for sura in range(1, 115):
        aw, bw = flat(a_rows[sura], a), flat(b_rows[sura], b)
        ak, bk = [cons(w, a) for _, w in aw], [cons(w, b) for _, w in bw]
        ctrl = {}
        if control:
            if c_rows is None:
                ctrl = {i: tr(w, a) for i, (_, w) in enumerate(aw)}
            else:
                cw = flat(c_rows[sura], control)
                ck = [cons(w, control) for _, w in cw]
                for t, p1, p2, q1, q2 in difflib.SequenceMatcher(
                        None, ak, ck, autojunk=False).get_opcodes():
                    if t == "equal":
                        for k in range(p2 - p1):
                            ctrl[p1 + k] = tr(cw[q1 + k][1], control)
        sm = difflib.SequenceMatcher(None, ak, bk, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    x, y = aw[i1 + k], bw[j1 + k]
                    if tr(x[1], a) != tr(y[1], b):
                        found.append(dict(sura=sura, ah=x[0], aw=y[0], tag="replace",
                                          a=x[1], b=y[1],
                                          ctrl=ctrl.get(i1 + k)))
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


def undo_idghaam(th, tw, ctrl=None):
    """Reverse an idghaam kabiir in `tw`, or return None.

    al-Soosi assimilates a vowelled consonant into the one that follows it,
    across a word boundary as well as inside a word: the short vowel goes and
    the following consonant doubles. `qiila lahum` becomes `qiil llahum`, so
    one word loses its final vowel and the next gains a doubled first letter,
    and both halves land here as separate differences.

    It is a rule and not a word-by-word choice: of the 963 places where a
    final short vowel goes, 879 have the doubled consonant on the next word,
    and the 84 that do not are all miem before baa, where the assimilation is
    incomplete and no shadda is written.

    Only the losing half is recognised here, because only that half is
    unambiguous. A word that merely *begins* with a doubled consonant is far
    more often an ordinary idghaam saghiir that one mushaf writes with a
    shadda and the other does not -- `man yaquulu` is written `yyaquulu` by
    Qaaloon and `yaquulu` by Hafs, and both recite it the same way. That is
    notation, and `gemination_notation` says so. Counting the receiving half
    as a rule of its own would also count one assimilation twice.

    Even the losing half needs a control, because a final short vowel that
    goes can just as well be a jazm. At 2:284 it is: Hafs reads `fa-yaghfiru
    ... wa-yu'adhdhibu` in raf', the others `fa-yaghfir ... wa-yu'adhdhib` in
    jazm -- a farsh difference, and one of the most argued i'rab differences
    in the Quran. Reading the next word does not settle it either: al-Soosi
    assimilates the raa of `fa-yaghfir` into the laam of `li-man` as well, so
    the trace of the rule and the trace of the jazm look alike.

    The control is al-Doori. He transmits the same qiraa from the same qari
    and does not apply idghaam kabiir, so a vowel that goes in al-Soosi and
    stays in al-Doori is the rule, and one that goes in both belongs to Abu
    'Amr's reading. Over the whole Quran that splits 958 against 5, and the
    five are exactly the places a reader would name: 2:284 twice, 19:6
    `wa-yarith`, 4:81 `bayyat`, and 27:66 `bal`."""
    if ctrl is not None and tw == th[:-1] and th[-1:] in ("a", "u", "i") \
       and ctrl != tw:
        return th                                  # the vowel the rule took
    for i, ch in enumerate(th):                    # the same, inside one word
        if ch in "aui" and i + 1 < len(th) and th[i + 1] not in "auiAUIN" \
           and th[:i] + th[i + 1] + th[i + 1:] == tw:
            return th
    return None


def strip_usul(th, tw, ctrl=None):
    """Remove the suffix-level usul features; returns (th, tw, tags)."""
    tags = []
    undone = undo_idghaam(th, tw, ctrl)
    if undone is not None:
        return th, undone, ["idghaam_kabir"]
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
    # huwa and hiya lose their vowel after a prefixed particle: wa-hwa, fa-hya
    if not tags and re.sub("ه[ui]([wy])a$", r"ه\g<1>a", th) == tw != th:
        tw = th; tags.append("ha_iskan")
    return th, tw, tags


def classify(th, tw, ctrl=None, raw_b=""):
    if th == tw:
        return "identical"
    th, tw, tags = strip_usul(th, tw, ctrl)
    if th == tw:
        return tags[0]
    suffix = "+" + tags[0] if tags else ""
    for v in "aui":
        if th == "'" + v + tw or tw == "'" + v + th:
            return "wasl_notation" + suffix
    # imaala first: where the mushaf marks it, a yaa against an alif is the
    # vowel being read differently and not two ways of writing one sound
    if has_imala(raw_b) and (fold_mq(th) == fold_mq(tw)
                             or fold_len(fold_mq(th)) == fold_len(fold_mq(tw))
                             or fold_fy(th) == fold_fy(tw)):
        return "imaala" + suffix
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
        # the same word, written with alif maqsura on one side and yaa on the
        # other -- but where the mushaf also marks imaala, the yaa is there
        # because the vowel is read differently, and that is not notation
        return ("imaala" if has_imala(raw_b) else "maqsura_notation") + suffix
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
       and tw[-1] in "aui" and (re.sub("[aui]", "", th) in JUNCTION
                                or th[-4:-1] in ("هiم", "هuم", "كuم")):
        # a particle or a plural pronoun before a wasl: the vowel that joins
        # them is the reader's, not the word's
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
    person reading every word pair the rules left, and what that person
    decided lives in farsh_review.tsv rather than in the code: one line per
    pair, with a reason, so every verdict can be looked up and argued with.

    Only two verdicts appear there. A pair is either not farsh after all, or
    it could not be settled -- the ten rows of allaatie / allatie, where the
    Warsh mushaf leaves out the dagger alif and nothing here says whether
    that is the reading or the spelling.

    The largest group struck is the hamz of an-nabii' and an-nubuu'a, which
    a rule cannot judge either: what makes it usul rather than a word-by-word
    choice is that Naafi' reads it so at all 82 places the word occurs, and
    that count is a fact about the whole text and not about the pair in
    front of you."""
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
        r["th"], r["tw"] = tr(r["a"], a), tr(r["b"], b)
        if r["tag"] != "replace":
            r["cls"] = "word_" + r["tag"]
        else:
            r["cls"] = classify(r["th"], r["tw"], r.get("ctrl"), r["b"])
        if r["cls"] == "identical":
            # the letters agree and only the word boundary moved
            r["cls"] = "reviewed:alignment_or_word_split"
        if r["cls"].startswith("farsh_candidate") or r["cls"].startswith("word_"):
            again = second_look(r)
            if again:
                r["cls"] = again
    if (a, b) == REVIEWED_PAIR:
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
        riwaya_a TEXT, riwaya_b TEXT, pair_type TEXT, reviewed INTEGER,
        surah INTEGER, ayah_a INTEGER, ayah_b INTEGER,
        form_a TEXT, form_b TEXT, translit_a TEXT, translit_b TEXT,
        class TEXT, kind TEXT)""")
    for a, b in PAIRS:
        read = (a, b) == REVIEWED_PAIR
        for r in rows[(a, b)]:
            base = r["cls"].split("+")[0]
            cur.execute(
                "INSERT INTO riwaya_diff (riwaya_a, riwaya_b, pair_type,"
                " reviewed, surah, ayah_a, ayah_b, form_a, form_b,"
                " translit_a, translit_b, class, kind)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (a, b, pair_type(a, b), 1 if read else 0,
                 r["sura"], r["ah"], r["aw"], r["a"].strip(), r["b"].strip(),
                 r["th"], r["tw"], r["cls"],
                 KIND.get(base, ("onbekend", ""))[0]))
    cur.execute("CREATE INDEX idx_riwaya_diff_verse ON riwaya_diff(surah, ayah_a)")
    cur.execute("CREATE INDEX idx_riwaya_diff_kind ON riwaya_diff(kind)")
    cur.execute("CREATE INDEX idx_riwaya_diff_pair ON riwaya_diff(riwaya_a, riwaya_b)")
    conn.commit()


def summary(rows):
    """One line per pair: how far apart the two transmissions are."""
    out = []
    for a, b in PAIRS:
        cnt = collections.Counter(
            KIND.get(r["cls"].split("+")[0], ("onbekend",))[0]
            for r in rows[(a, b)])
        out.append((a, b, pair_type(a, b), len(rows[(a, b)]),
                    cnt["farsh"], cnt["usul"], cnt["notatie"],
                    (a, b) == REVIEWED_PAIR))
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
           "| Paar | | Plaatsen | farsh | usul | notatie | nagelezen |",
           "|---|---|--:|--:|--:|--:|:-:|"]
    for a, b, kind, total, f, u, n, read in summary(rows):
        out.append("| %s – %s | %s qiraa-a | %s | %s | %s | %s | %s |"
                   % (a, b, "binnen een" if kind == "binnen" else "tussen twee",
                      format(total, ","), format(f, ","), format(u, ","),
                      format(n, ","), "ja" if read else "nee"))
    out.append("")
    binnen = [f for _a, _b, k, _t, f, _u, _n, _r in summary(rows) if k == "binnen"]
    tussen = [f for _a, _b, k, _t, f, _u, _n, _r in summary(rows) if k == "tussen"]
    out.append("Kijk naar de kolom farsh, niet naar het aantal plaatsen. Het "
               "aantal plaatsen telt usul en schrijfwijze mee, en die lopen "
               "per pakket sterk uiteen: Qaaloon-Warsh staat op %s plaatsen "
               "terwijl het binnen een qiraa-a valt, omdat Warsh naql en "
               "hamza-ibdaal toepast waar Qaaloon dat niet doet. De farsh-"
               "kolom is de vergelijkbare maat, en die zegt wat je verwacht: "
               "binnen een qiraa-a %s, tussen twee qiraa-aat %s.\n"
               % (format(next(t for a, b, k, t, f, u, n, r in [x for x in summary(rows)]
                              if (a, b) == ("qaloon", "warsh")), ","),
                  "-".join(str(x) for x in (min(binnen), max(binnen))),
                  "-".join(str(x) for x in (min(tussen), max(tussen)))))
    out.append("Alle tien de paren zijn met dezelfde regels geclassificeerd. "
               "Wat per pakket verschilt is de schrijfwijze, en dat zit nu in "
               "de transliteratie: Qaaloon, Doorie en Soesie schrijven de "
               "wasl-alif als een kale alif met de klinker erop, Hafs en de "
               "Kufische pakketten als de letter alef wasla, en Warsh met een "
               "teken erboven. De kenmerken die maar bij een deel van de "
               "riwaayaat horen -- de idghaam kabier van al-Soesie, de imaala "
               "van Aboe 3Amr en van Warsh, het wegvallen van de klinker in "
               "*hoewa* en *hiya* -- hebben elk hun eigen klasse.\n")
    struck = sum(1 for r in main_rows if r["cls"].startswith("reviewed:hand"))
    unsure = sum(1 for r in main_rows if r["cls"].startswith("reviewed:onzeker"))
    kept = counts_farsh = sum(
        1 for r in main_rows
        if KIND.get(r["cls"].split("+")[0], ("", ""))[0] == "farsh")
    out.append("De kolom *nagelezen* is iets anders dan de classificatie. Bij "
               "Hafs-Warsh is de farsh-lijst daarna nog woord voor woord "
               "gelezen. Dat streepte %d rijen weg die de regels ten onrechte "
               "als farsh hadden staan en liet %d onbeslist, tegenover %d die "
               "bleven staan -- %.0f%% van wat de regels aandroegen was geen "
               "farsh. De oordelen staan per woordpaar met hun reden in "
               "`farsh_review.tsv`. Voor de negen andere paren is dat niet "
               "gedaan, en hun farsh-getal is dus een bovengrens; reken op een "
               "marge van die orde.\n"
               % (struck, unsure, kept,
                  struck / (struck + unsure + kept) * 100))
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
    print("  %-16s %-9s %8s %7s %7s %8s %s"
          % ("paar", "qiraa-a", "plaatsen", "farsh", "usul", "notatie", "gelezen"))
    for a, b, kind, tot, f, u, n, read in summary(rows):
        print("  %-16s %-9s %8s %7s %7s %8s %s"
              % ("%s-%s" % (a, b), kind, format(tot, ","), format(f, ","),
                 format(u, ","), format(n, ","), "ja" if read else ""))
    print("  (regels classificeren alle tien; alleen hafs-warsh is daarna")
    print("   ook woord voor woord nagelezen -- zie de docstring)")
    if args.markdown:
        print("  docs/hafs-warsh.md: %d regels" % markdown(conn, rows))
    conn.close()


if __name__ == "__main__":
    main()
