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

The verse division differs from Hafs in 50 suras for Warsh and Qaaloon, 52
for al-Bazzi and Qunbul, 43 for al-Doori and al-Soosi and none for Shu'ba,
so a join on (surah, ayah) breaks.
Each sura is aligned on its word sequence instead, with difflib over the
consonant skeleton, and the two ayah numbers are both recorded.

All twenty-eight pairs are classified -- every pair the eight riwayat make,
so that a question like "does Warsh sit closer to al-Doori than to Qunbul?"
has a row to answer it. What differs between the packages is how they spell
things, and that belongs in the transliteration rather than in the comparison.
There are two conventions for hamzat al-wasl, not three: Hafs and Shu'ba
(Kufa) and al-Bazzi and Qunbul (Mecca) write the alef wasla letter, while the
four Maghribi packages write a plain alif with a sign over it -- Qaaloon and
Warsh marking practically all of theirs, al-Doori and al-Soosi leaving some
two thousand to be inferred from position. Telling the transliteration which
convention a file follows removes several thousand false differences per pair
on its own.

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
reading are in `farsh_review.tsv`. It struck 116 rows the rules had wrongly
called farsh, 18 per cent of what they proposed. The other 27 pairs carry the
rule verdict alone, so their farsh figure is an upper bound and `reviewed`
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
  python3 compare_riwayat.py --reverse           print the same summary with
                                                 every pair's sides swapped,
                                                 writing nothing; this is what
                                                 the direction figures in the
                                                 documents are measured with
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

# Every pair is classified by rule; see ORDER below for which pairs and in
# which direction. Only this one has also been read word by word afterwards,
# and only it carries the verdicts in farsh_review.tsv.
REVIEWED_PAIR = ("hafs", "warsh")

# A riwaya that applies idghaam kabiir, and the sibling transmission of the
# same qiraa that does not, which serves as its control; see undo_idghaam.
IDGHAAM_KABIR = {"soosi": "doori"}

# Classes that describe a feature without saying which side carries it, so
# they may be recognised with the two sides swapped. Everything not here is
# one-way, either because the rule names a direction (naql moves a vowel onto
# the last letter) or because reading it backwards collides with real farsh.
SYMMETRIC = {"sila_mim", "sila_ha", "yaa_idafa", "ha_iskan"}

# The order the pairs are built from, and it is not arbitrary. Hafs comes
# first so that he stands on the left of all seven pairs he is in; Shu'ba
# follows because they transmit one qiraa; then the three remaining qurraa
# with their two riwayat each. Taking every combination from that order
# reproduces the ten pairs this list held before it grew to all of them, with
# the same side on the left and therefore the same counts.
#
# Keeping those ten oriented as they were is not housekeeping. Half the usul
# classes name a direction -- naql moves the vowel of a following hamza onto
# the last letter, silat al-haa adds a long vowel, idghaam kabiir takes the
# final vowel away -- and they are written from the side that does *not* apply
# the feature. Put that side on the right and its own usul is no longer
# recognised: it falls through to farsh. Measured over all 28 pairs in both
# directions, that is worth a factor of three where Warsh is involved
# (Hafs-Warsh 523 farsh, Warsh-Hafs 1,611) and a factor of five for al-Soosi's
# idghaam kabiir (al-Doori-al-Soosi 25, al-Soosi-al-Doori 124), while pairs
# that apply no usul the other lacks barely move (al-Bazzi-Qunbul 34 and 30).
#
# There is no order that puts every riwaya on its best side -- al-Soosi wants
# to be on the right of al-Doori and on the left of al-Bazzi -- so the farsh
# column is comparable only down a fixed left-hand side, and the places column
# is what compares across pairs. docs/hafs-warsh.md says so in full.
ORDER = ("hafs", "shouba", "qaloon", "warsh", "bazzi", "qumbul", "doori", "soosi")
# The farsh count of a pair with its two sides swapped. This cannot be read off
# the database, which stores one orientation, and measuring it means
# classifying every pair a second time -- so it lives here, in one place, with
# the command that refreshes it:
#
#     python3 compare_riwayat.py --reverse
#
# The forward half of every figure quoted beside these is computed from the
# rows, so only this dict can go stale, and only deliberately.
REVERSE_FARSH = {("hafs", "warsh"): 1611, ("qaloon", "warsh"): 1293,
                 ("doori", "soosi"): 124, ("hafs", "shouba"): 400,
                 ("bazzi", "qumbul"): 30}

PAIRS = [(a, b) for i, a in enumerate(ORDER) for b in ORDER[i + 1:]]
DOC = HERE / "docs" / "hafs-warsh.md"
REVIEW = HERE / "farsh_review.tsv"

# The eight riwayat King Fahd Glorious Quran Printing Complex publishes, with
# the qari each transmits from. The complex's own release notes file al-Bazzi
# and Qunbul under Abu 'Amr al-Basri; they transmit from Ibn Kathir al-Makki,
# and the reader relation below is the corrected one.
RIWAYAT = [
    # code, riwaya ar, riwaya en, died, qari ar, qari en, died, region, version
    ("qaloon", "قالون", "Qaaloon", 220, "نافع المدني", "Naafi' al-Madani", 169,
     "Libie, Tunesie, delen van Algerije", "10"),
    ("warsh", "ورش", "Warsh", 197, "نافع المدني", "Naafi' al-Madani", 169,
     "Marokko, Algerije, Mauritanie, West- en Centraal-Afrika", "10"),
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
# The second hamza of a pair is often given as tashiel or ibdaal, and the
# mushaf then writes it as the long vowel it is drawn out into: 'a'iذA against
# 'AذA. Reaching those needs the long vowel folded away with the hamza too --
# as a disjunct beside fold_ham2 and never in place of it, because replacing
# it loses
# waلصصAبi'Uنa against waلصصAبUنa, where the hamza goes and the vowel stays.
# Order in the chain does not matter; being additional is what does.
fold_ham3 = lambda x: re.sub(r"'[auiAUI]?", "", x)
fold_sil = lambda x: x.replace("uw", "u").replace("iy", "i")
fold_mq = lambda x: x.replace("yA", "A")
fold_iv = lambda x: re.sub(r"^'[aui]", "'", x)
fold_head = lambda x: re.sub(r"^('[aui]?|A|w|y)", "", x, count=1)
fold_wu = lambda x: x.replace("'U", "'w").replace("'I", "'y")
fold_nq = lambda x: x.replace("uA", "u").replace("iA", "i")
fold_fy = lambda x: re.sub("ay$", "A", x)
# a final alif maqsura written as a bare yaa, which is how the Warsh, al-Doori
# and al-Soosi mushafs write the alif they read with imaala: waتaرy for waتaرA
fold_ya = lambda x: re.sub("y$", "A", x)

# particles whose final vowel is only the helper spoken at a junction
JUNCTION = {"من", "عن", "'ن", "قل", "بل", "قد", "لقد", "wلقد", "فقل", "w'ن",
            "'ذ", "'م", "'w", "w'ذ", "فمن", "wمن", "wقد", "ثم", "لكن", "wلكن",
            "فقد", "كل", "'ن'"}
MUQ = {"Aلم", "Aلر", "طسم", "Aلمر", "كهيعص", "حم", "يس", "طه", "ص", "ق", "ن",
       "عسق", "طس", "Aلمص"}
MUQATTAAT_SURAS = {2, 3, 7, 10, 11, 12, 13, 14, 15, 19, 20, 26, 27, 28, 29, 30,
                   31, 32, 36, 38, 40, 41, 42, 43, 44, 45, 46, 50, 68}
HAMZA = set("ءأإؤئٓٔ")
# These three signs each do two jobs, told apart by the letter they sit on.
# U+06ED is the small low meem of iqlaab where it sits on a vowelled letter.
# The packages are nowhere near equal in it: Hafs writes it 99 times, al-Bazzi,
# Qunbul and Shu'ba 100 each, al-Doori 66, al-Soosi 38, and Warsh and Qaaloon
# not once. U+06EA and U+06EC on an alif mark hamzat
# al-wasl, which is what the ten thousand and some of them in Warsh, Qaaloon,
# al-Doori and al-Soosi are, and the transliteration resolves those. On any
# other letter U+06EA and U+06EC mark imaala and taqliil on the alif that
# follows -- Warsh 1,911, al-Doori 737, al-Soosi 609, Qaaloon 11, al-Bazzi,
# Qunbul and Shu'ba 3 each, Hafs 2 -- as does U+06ED on a bare letter, which
# adds 560 more for al-Doori and 555 for al-Soosi and nothing for the rest.
# What has_imala() counts is therefore the sum: al-Doori 1,297, al-Soosi
# 1,164, and for the other six the figures above. That
# is a difference in the recitation
# and not in the spelling. The transliteration ignores them, so they add no
# differences of their own, and they are read here only to give a difference
# that is there anyway its right name.
IMALA_MARKS = "\u06ea\u06ec\u06ed"
VOWEL_SIGNS = "\u064b\u064c\u064d\u064e\u064f\u0650\u0651\u0652"


ALIFS = "\u0627\u0649\u0670"


def has_imala(w):
    """True when the word carries an imaala or taqliil mark on a letter.

    The mark that says the aa is drawn towards the ee is told apart from the
    other two jobs these three signs do by what they sit on, not by whether a
    vowel sign comes in between. U+06ED is the iqlaab marker and appears even
    in Hafs; U+06EA and U+06EC on an alif mark hamzat al-wasl, which is what
    the ten thousand and some of them in Warsh, Qaaloon, al-Doori and al-Soosi
    are. On any other letter the two of them mark imaala or taqliil.
    """
    for i, c in enumerate(w):
        if c not in IMALA_MARKS:
            continue
        if c == "\u06ed":
            # iqlaab sits on a vowelled letter; on a bare one it is not that
            if i == 0 or w[i - 1] not in VOWEL_SIGNS:
                return True
            continue
        j = i - 1
        while j >= 0 and w[j] in VOWEL_SIGNS:
            j -= 1
        if j < 0 or w[j] not in ALIFS:
            return True
    return False

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
                # so each difference is judged on its own.
                #
                # The control belongs here too. It used to be attached only in
                # the `equal` branch above -- to words whose consonant skeletons
                # already agree -- and a word that carries a second feature
                # beside the idghaam has skeletons that do not agree, so it
                # lands in a changed block. Those were exactly the rows that had
                # no control and so could not be told from farsh: all 63 that
                # doori-soosi reported.
                if tag == "replace" and len(ha) == len(wa) > 1:
                    for k, (h, w) in enumerate(zip(ha, wa)):
                        found.append(dict(sura=sura, ah=ah, aw=aa, tag=tag,
                                          a=h, b=w, ctrl=ctrl.get(i1 + k)))
                else:
                    found.append(dict(sura=sura, ah=ah, aw=aa, tag=tag,
                                      a=" ".join(ha), b=" ".join(wa),
                                      ctrl=(ctrl.get(i1) if len(ha) == len(wa) == 1
                                            else None)))
    return found


def undo_idghaam(th, tw, ctrl=None):
    """Reverse an idghaam kabiir in `tw`, or return None.

    al-Soosi assimilates a vowelled consonant into the one that follows it,
    across a word boundary as well as inside a word: the short vowel goes and
    the following consonant doubles. `qiila lahum` becomes `qiil llahum`, so
    one word loses its final vowel and the next gains a doubled first letter,
    and both halves land here as separate differences.

    It is a rule and not a word-by-word choice: a final short vowel goes in
    1,157 places over the whole Quran, against the five below that the control
    picks out as jazm. Most of them have the doubled consonant on the next
    word; those that do not are miem before baa, where the assimilation is
    incomplete and no shadda is written. That second split is not re-derived
    here, because only the losing half is counted at all -- see below.

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
    'Amr's reading. Over the whole Quran that splits 1,152 against 5, and the
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
    # The idghaam does not always come alone. Where the final vowel went by the
    # rule -- the control still writes it -- but the two sides differ in
    # something else as well (a hamza softened into its long vowel, a shadda
    # carried over from the word before), the exact test above cannot see it,
    # and the row fell through to farsh: every one of the 63 that doori-soosi
    # reported was of that shape. So take the vowel the rule took and let the
    # rest of the chain judge what is left. A residue nothing explains still
    # ends up as farsh, which is the point of keeping the control.
    if (ctrl is not None and th[-1:] in ("a", "u", "i")
            and tw[-1:] not in ("a", "u", "i")
            and ctrl != tw and ctrl[-1:] in ("a", "u", "i")):
        th = th[:-1]
        tags.append("idghaam_kabir")
    if tw.endswith("U") and tw[:-1].endswith("م") and th.endswith("م"):
        tw = tw[:-1]; tags.append("sila_mim")
    # The sila of the haa is the long vowel a transmission gives the pronoun
    # between two vowelled letters. Three shapes of the same thing: both sides
    # carry it at different length, one side drops it altogether, or the word
    # also carries a shadda from the word before it, which is notation and has
    # to be folded away first or the two sides never line up.
    if not tags:
        ga, gb = fold_gem(th), fold_gem(tw)
        if len(ga) > 1 and ga[-2] == "ه" and len(gb) > 1 and gb[-2] == "ه" \
           and ga[:-1] == gb[:-1] and fold_len(ga) == fold_len(gb):
            tw = th; tags.append("sila_ha")
        elif gb == ga[:-1] and ga[-1:] in ("U", "I") and ga[-2:-1] == "ه":
            tw = th; tags.append("sila_ha")
    if not tags and tw == th + "a" and th.endswith("iy"):
        tw = th; tags.append("yaa_idafa")
    if not tags and th.endswith("iya") and tw == th[:-3] + "I":
        tw = th; tags.append("yaa_idafa")
    if not tags and th.endswith("I") and tw == th[:-1] + "iya":
        tw = th; tags.append("yaa_idafa")
    # yaa bunayya against yaa bunayyi: the same yaa al-idaafa, opened by one
    # transmission and read with a kasra by the other
    if not tags and th.endswith("yya") and tw == th[:-1] + "i":
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
                             or fold_fy(th) == fold_fy(tw)
                             or fold_ya(th) == fold_ya(tw)
                             or fold_ya(fold_mq(th)) == fold_ya(fold_mq(tw))):
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
    # The hamza, but only where the two sides differ in how many they write.
    #
    # Two folds that are sound everywhere else are wrong *here*, because with
    # the hamza already taken out they stop describing its treatment and start
    # equating different words:
    #
    #   vowels_only_dropped, which reads a missing short vowel as an unwritten
    #   one. At 43:19 that turned أَشَهِدُوٓاْ against اَ۟شْهِدُوٓاْ into one
    #   spelling of one word, where it is a-shahiduu against ushhiduu -- ma'luum
    #   against majhuul, and the difference lives in exactly those vowels. The
    #   proof it was this branch and not the reading: the same difference came
    #   out as farsh against Qaaloon, who writes that hamza on a seat, and as
    #   usul against Warsh, who does not.
    #
    #   fold_sil, which drops the yaa of `iy` and the waw of `uw` as a written
    #   trace of a long vowel. With the hamza gone from the other side there is
    #   nothing left to hold the two apart, and 18:86 حَمِئَةٖ against حَٰمِيَةٖ
    #   came out as one word: hami'a "muddy" (ح م أ) against haamiya "hot"
    #   (ح م ي), two roots and the farsh every reader names.
    #
    # fold_len stays. It carries the dagger alif against the written alif, which
    # is notation and not the reading, and taking it out of this branch alone
    # moves some 1,500 rows that are nothing but that.
    if th.count("'") != tw.count("'"):
        if fold_nq(fold_ham(th)) == fold_nq(fold_ham(tw)) or \
           fold_nq(fold_ham2(th)) == fold_nq(fold_ham2(tw)) or \
           fold_ham2(th) == fold_ham2(tw) or \
           fold_ham3(th) == fold_ham3(tw) or \
           fold_len(fold_ham3(th)) == fold_len(fold_ham3(tw)) or \
           fold_mq(fold_ham2(th)) == fold_mq(fold_ham2(tw)) or \
           fold_len(fold_ham2(th)) == fold_len(fold_ham2(tw)):
            return "hamza_treatment" + suffix
        a, b = fold_ham(th), fold_ham(tw)
        for f in (lambda x: x, fold_len, fold_gem, fold_art, fold_mq,
                  fold_iv, lambda x: fold_mq(fold_len(x)),
                  lambda x: fold_len(fold_gem(x)), lambda x: fold_len(fold_art(x)),
                  lambda x: fold_gem(fold_art(x))):
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
    choice is that Naafi' reads it so at every place the word occurs, and
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
            if r["cls"].startswith("farsh_candidate"):
                # Most rules describe a feature without saying which side
                # carries it -- silat al-haa is silat al-haa whichever
                # transmission opens the yaa. They were written with Hafs on
                # the left, so on a pair like Qaaloon-Warsh they fire on the
                # wrong side and 216 rows of wa-hwa / wa-huwa come out as
                # farsh. Retrying with the sides swapped costs nothing and is
                # what symmetry means here -- but only for the classes that
                # really are symmetric. Read backwards, `naql` says "a vowel
                # was added to the last letter", and that is what a jazm looks
                # like from the other side: at 2:284 fa-yaghfiru / fa-yaghfir
                # the reverse pass called the most argued farsh difference in
                # the Quran a spelling rule. Idghaam kabiir stays one-way for
                # the same reason, and because only one riwaya applies it.
                back = classify(r["tw"], r["th"], None, r["a"])
                if back.split("+")[0] in SYMMETRIC:
                    r["cls"] = back
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
    """One line per pair: how far apart the two transmissions are.

    Over the pairs it was handed, in the order they were built -- not over
    PAIRS. That mattered once: with --reverse the keys are swapped, and
    reading PAIRS here raised a KeyError on the first pair instead.
    """
    out = []
    for a, b in rows:
        cnt = collections.Counter(
            KIND.get(r["cls"].split("+")[0], ("onbekend",))[0]
            for r in rows[(a, b)])
        out.append((a, b, pair_type(a, b), len(rows[(a, b)]),
                    cnt["farsh"], cnt["usul"], cnt["notatie"],
                    (a, b) == REVIEWED_PAIR))
    return out


def markdown(conn, rows):
    cur = conn.cursor()
    # the farsh count of every pair as it is stored, so the prose below never
    # has to repeat a figure the data already holds
    fw = {(a, b): f for a, b, _k, _t, f, _u, _n, _r in summary(rows)}
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
           "`عن` Aasim al-Koefie, Warsh `عن` Naafi3 al-Madanie.*\n"]
    # A page of counted differences reads as a list of deviations unless it
    # says, in so many words, that it is not one. The two quotations below are
    # taken verbatim from the two mushaf files, and their ayah numbers differ
    # from each other on purpose -- that is itself part of what is being said.
    out.append("## Beide zijn Qoeraan\n")
    out.append("Deze pagina telt waar twee overleveringen uiteenlopen, en "
               "die telling is een indeling naar het soort verschil -- geen "
               "rangorde en geen lijst van afwijkingen. Vier dingen die "
               "daarbij horen.\n")
    out.append("**Er is geen origineel waarvan de ander afwijkt.** Beide "
               "riwaayaat zijn mutawaatir: langs zoveel onafhankelijke "
               "ketens overgeleverd dat afspraak of vergissing is "
               "uitgesloten. Elk van de twee *is* de Qoeraan, en niet een "
               "variant erop. Het Oethmaanse rasm is bovendien zonder punten "
               "en zonder klinkertekens geschreven en draagt daardoor meer "
               "dan een lezing tegelijk: de qiraa-aat verwijderen zich niet "
               "van dat schriftbeeld, het schriftbeeld is zo gekozen dat het "
               "ze draagt.\n")
    out.append("**Dat Hafs links staat, is gereedschap en geen norm -- maar "
               "het is niet vrijblijvend.** In %d van de %d paren staat "
               % (len(ORDER) - 1, len(PAIRS)) + "Hafs in de linkerkolom, omdat dat de overlevering is die de "
               "meeste lezers kennen en omdat het elk van de acht pakketten "
               "een vergelijking geeft. Vier paren zetten twee "
               "overleveringen van een en dezelfde qaari- naast elkaar; de "
               "overige stellen twee qiraa-aat tegenover elkaar. *Welke* "
               "plaatsen uiteenlopen is bijna symmetrisch: draai het paar om "
               "en vrijwel dezelfde plaatsen komen terug -- 14 van de 28 "
               "paren tellen er 2 of 7 meer of minder, op duizenden, dus "
               "hoogstens twee promille. Die rest komt niet uit de indeling "
               "maar uit de uitlijning, en de richting die netter uitvalt is "
               "niet altijd de onze: bij لِلَّذِينَ tegenover لِلذِينَ maakt "
               "de uitlijner met Hafs links drie rijen waarvan een "
               "farsh-kandidaat, en met Qaaloon links een enkele rij "
               "`article_lam`. De *indeling* van die plaatsen is helemaal "
               "niet symmetrisch. De "
               "usul-regels hebben een richting -- naql legt de klinker van "
               "een volgende hamza op de laatste letter, silat al-haa voegt "
               "er een lange klinker aan toe, idghaam kabier neemt de "
               "eindklinker juist weg -- en ze zijn geschreven met Hafs als "
               "de kant waarvandaan gekeken wordt. Zet Warsh links en de "
               "regels herkennen hun eigen kenmerk niet meer: dan valt dat "
               "kenmerk door naar farsh en telt dit paar geen %d maar "
               "%s. Dat is nagemeten over alle %d paren in beide "
               % (fw[("hafs", "warsh")], format(REVERSE_FARSH[("hafs", "warsh")], ",").replace(",", "."), len(PAIRS)) +
               "richtingen, en het patroon is scherp. Waar Warsh links komt "
               "te staan verdrievoudigt zijn farsh ongeveer, en al-Soesie "
               "gaat van %d naar %d zodra hij links van al-Doorie staat in "
               % (fw[("doori", "soosi")], REVERSE_FARSH[("doori", "soosi")]) +
               "plaats van rechts, omdat zijn idghaam kabier dan geen "
               "controle meer heeft. Paren waar geen van beide kanten usul "
               "toepast die de ander niet kent, bewegen nauwelijks: "
               "al-Bazzie-Qoenboel %d tegen %d, Hafs-Shu3ba %d tegen %d. "
               % (fw[("bazzi", "qumbul")], REVERSE_FARSH[("bazzi", "qumbul")],
                  fw[("hafs", "shouba")], REVERSE_FARSH[("hafs", "shouba")]) +
               "En er is geen volgorde die elke riwaaya op zijn beste kant "
               "zet -- al-Soesie wil rechts van al-Doorie staan en links van "
               "al-Bazzie. De farsh-kolom is dus vergelijkbaar zolang je hem "
               "afleest langs een vaste linkerkolom, en niet daarbuiten. "
               "Ook de versnummering is trouwens niet gedeeld -- het "
               "woord hieronder staat bij Hafs in 57:24 en bij Warsh in "
               "57:23 -- en de tabel houdt daarom aan beide kanten een eigen "
               "ayah-nummer bij.\n")
    out.append("**Farsh betekent niet fout.** *Farsh al-hoeroef* is de "
               "klassieke term voor de plaatsen waar twee lezingen in het "
               "woord zelf verschillen, tegenover de *usul*, de regels die "
               "gelden overal waar hun voorwaarde zich voordoet. Het "
               "onderscheid gaat over de soort van het verschil en niet over "
               "de juistheid ervan. En een woord dat maar aan een kant staat "
               "-- هُوَ, Hafs 57:24 tegenover Warsh 57:23 -- ontbreekt niet "
               "aan de andere kant: daar loopt de zin anders.\n")
    out.append("**Het verschil is vaak juist de winst.** Waar de lezingen "
               "uiteenlopen, loopt de betekenis niet zelden mee, en dan zijn "
               "dat twee betekenissen die allebei Qoeraan zijn. Bij 34:17 "
               "leest Hafs وَهَلۡ نُجَٰزِيٓ إِلَّا ٱلۡكَفُورَ -- het "
               "werkwoord actief, eerste persoon meervoud, en de ondankbare "
               "als lijdend voorwerp in de nasb: *en vergelden Wij anders "
               "dan de ondankbare?* Warsh leest وَهَلْ يُجَٰز۪ىٰٓ إِلَّا "
               "اَ۬لْكَفُورُۖ -- hetzelfde werkwoord in de lijdende vorm, en "
               "de ondankbare daardoor in de raf3 als naa-ib al-faa3il: *en "
               "wordt anders dan de ondankbare vergolden?* Twee ontledingen, "
               "twee betekenissen, en de tafsier neemt ze allebei mee. Dat "
               "is geen tegenspraak die opgelost moet worden; het is bereik "
               "dat een enkele lezing niet zou hebben gehad.\n")
    out += ["## Alle vergeleken paren\n",
            "| Paar | | Plaatsen | farsh | usul | notatie | nagelezen |",
            "|---|---|--:|--:|--:|--:|:-:|"]
    for a, b, kind, total, f, u, n, read in summary(rows):
        out.append("| %s – %s | %s qiraa-a | %s | %s | %s | %s | %s |"
                   % (a, b, "binnen een" if kind == "binnen" else "tussen twee",
                      format(total, ","), format(f, ","), format(u, ","),
                      format(n, ","), "ja" if read else "nee"))
    out.append("")
    hafs_binnen = [f for a, b, k, _t, f, _u, _n, _r in summary(rows)
                   if a == "hafs" and k == "binnen"]
    hafs_tussen = [f for a, b, k, _t, f, _u, _n, _r in summary(rows)
                   if a == "hafs" and k == "tussen"]
    out.append("**Twee kolommen, twee vragen.** Het *aantal plaatsen* telt "
               "elk verschil mee, ook usul en schrijfwijze, en het hangt "
               "vrijwel niet van de richting af -- op twee promille na, zie "
               "hierboven. Dat maakt het de maat "
               "die over alle %d paren vergelijkt. De *farsh*-kolom zegt iets "
               "scherpers -- waar de lezingen in het woord zelf uiteenlopen "
               "-- maar hangt van de richting af, en is dus vergelijkbaar "
               "binnen een blok met dezelfde riwaaya links.\n"
               % len(PAIRS))
    out.append("Langs de zeven paren met Hafs links zegt de farsh-kolom wat "
               "je verwacht: binnen een qiraa-a %s, tussen twee qiraa-aat "
               "%s. En dat het aantal plaatsen iets anders meet dan afstand "
               "tussen lezingen, laat Qaaloon-Warsh zien: %s plaatsen "
               "terwijl het binnen een qiraa-a valt, omdat Warsh naql en "
               "hamza-ibdaal toepast waar Qaaloon dat niet doet.\n"
               % ("-".join(str(x) for x in sorted(set((min(hafs_binnen), max(hafs_binnen))))),
                  "-".join(str(x) for x in sorted(set((min(hafs_tussen), max(hafs_tussen))))),
                  format(next(t for a, b, k, t, f, u, n, r in summary(rows)
                              if (a, b) == ("qaloon", "warsh")), ",")))
    out.append("Alle %d paren zijn met dezelfde regels geclassificeerd. "
               % len(PAIRS) + "Wat per pakket verschilt is de schrijfwijze, en dat zit nu in "
               "de transliteratie. Er zijn twee conventies voor de "
               "wasl-alif, niet drie: Hafs en Shu3ba (Koefa) en al-Bazzie en "
               "Qoenboel (Mekka) schrijven de letter alef wasla, de vier "
               "Maghribie-uitgaven een kale alif met een teken erboven. "
               "Binnen die tweede groep markeren Qaaloon en Warsh er "
               "praktisch alle; al-Doorie en al-Soesie laten er ruim "
               "tweeduizend ongemarkeerd, en die worden uit de stand "
               "afgeleid -- dat is wat de vlag `plain_wasl` doet, en "
               "`test_translit.py` legt per pakket vast hoeveel woorden hij "
               "raakt. De kenmerken die maar bij een deel van de "
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
               "`farsh_review.tsv`. Voor de %d andere paren is dat niet "
               "gedaan, en hun farsh-getal is dus een bovengrens; reken op een "
               "marge van die orde.\n"
               % (struck, unsure, kept,
                  struck / (struck + unsure + kept) * 100, len(PAIRS) - 1))
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
    ap.add_argument("--reverse", action="store_true",
                    help="classify every pair with the sides swapped and print "
                         "the summary; touches neither the database nor the "
                         "documents. This is how the direction figures quoted "
                         "in README, BEVINDINGEN and docs/hafs-warsh.md are "
                         "reproduced: the usul rules name a direction, so which "
                         "riwaya stands on the left changes the farsh count.")
    args = ap.parse_args()

    for path, _s, _a in SRC.values():
        if not path.exists():
            sys.exit("ontbreekt: %s" % path)

    pairs = [(b, a) for a, b in PAIRS] if args.reverse else list(PAIRS)
    rows = {}
    for a, b in pairs:
        rows[(a, b)] = classified(a, b)

    if args.reverse:
        # Read-only on purpose: the database holds one orientation, the one
        # PAIRS names, and a reversed run is a measurement about the rules and
        # not a second version of the data.
        total = sum(len(v) for v in rows.values())
        print("omgekeerde richting -- niets weggeschreven")
        print("riwaya_diff zou %s plaatsen over %d paren geven"
              % (format(total, ","), len(pairs)))
        print("  %-16s %-9s %8s %7s %7s %8s"
              % ("paar", "qiraa-a", "plaatsen", "farsh", "usul", "notatie"))
        for a, b, kind, tot, f, u, n, _read in summary(rows):
            print("  %-16s %-9s %8s %7s %7s %8s"
                  % ("%s-%s" % (a, b), kind, format(tot, ","), format(f, ","),
                     format(u, ","), format(n, ",")))
        return

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
    print("  (regels classificeren alle %d; alleen hafs-warsh is daarna" % len(PAIRS))
    print("   ook woord voor woord nagelezen -- zie de docstring)")
    if args.markdown:
        print("  docs/hafs-warsh.md: %d regels" % markdown(conn, rows))
    conn.close()


if __name__ == "__main__":
    main()
