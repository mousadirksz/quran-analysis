#!/usr/bin/env python3
"""Phonemic transliteration of a vowelled Quranic word, for comparing riwayat.

The Hafs (Kufi) and Warsh (Maghribi) mushafs write the same sound with
different signs: dagger alif versus written alif, small waw versus waw, two
glyph shapes for each tanwin, different hamza seats, different notation for
the wasl alif.  Comparing letters therefore measures orthography.  Comparing
a transliteration measures the recitation, which is what a farsh difference
actually is.

The three tanwin pairs below were not guessed: every word of the Hafs text
carrying one of these six signs was matched against the Quranic Arabic Corpus
Buckwalter form for the same word, and each sign resolved to exactly one of
F / N / K with no exceptions (733+2900 fathatan, 576+1806 dammatan,
599+1933 kasratan).

The transliteration is a comparison key, not a pronunciation guide. It keeps
consonants as their Arabic letters and writes vowels in Latin: a/u/i short,
A/U/I long, aN/uN/iN tanwin, ' hamza. Only the distinctions that separate one
reading from another need to survive; nothing here is meant to be read aloud.
"""
import re, unicodedata

FAT, DAM, KAS = 'َ', 'ُ', 'ِ'
SHAD, SUK = 'ّ', 'ْ'
# Six of the eight packages write most sukuns as U+06E1 (the small high
# dotless head of khah) and keep U+0652 for about 4,000 places; Warsh and
# Qaaloon use U+0652 throughout. Both are the same sign.
SUKUNS = (SUK, '\u06e1')
DAGGER = 'ٰ'
SMALLWAW, SMALLYEH, SMALLYEH2 = 'ۥ', 'ۦ', 'ۧ'
MADDA, HAMZA_AB, HAMZA_BE = 'ٓ', 'ٔ', 'ٕ'
# The Maghribi mushaf marks hamzat al-wasl with a sign over the alif rather
# than with a distinct letter.  Both signs occur; U+06EA doubles as the
# taqlil (imala) sign elsewhere in the word, where it is simply ignored.
WASL_MARKS = '۪۬'
ALIF_MAQSURA = 'ى'

VOWELS = {FAT: 'a', DAM: 'u', KAS: 'i',
          'ً': 'aN', 'ٗ': 'aN',    # fathatan, both glyph shapes
          'ٌ': 'uN', 'ٞ': 'uN',    # dammatan
          'ٍ': 'iN', 'ٖ': 'iN'}    # kasratan

IGNORE = set('ۖۗۘۙۚۛۜ۝۞۟'
             '۠ۢۤۨ۩۪ۭ۫'
             '‏‎﻿ـ')

CONSONANTS = set('بتثجحخدذرزسشصضطظعغفقكلمنهوي')
# A wasl alif stands at the head of its word, behind nothing or behind one or
# two of these prefixes. Over the 13,483 in the Hafs mushaf no other consonant
# ever precedes one; the interrogative hamza stacks in front of them (a-fa-bi-)
# but is a seat and not a consonant, so it does not count here. And the alif is
# never the second-to-last letter, because what it carries always has more to
# follow. Both guards are what keeps `qaal` -- `qaala` with its final vowel
# taken by an idghaam -- from coming out as `qal`.
PREFIXES = set('وفبكلت')


def _emit_long(out, ch):
    short = {'A': 'a', 'U': 'u', 'I': 'i'}[ch]
    if out and out[-1] == short:
        out[-1] = ch
    else:
        out.append(ch)


def translit(w, sila=True, plain_wasl=False):
    """Transliterate one vowelled word.

    `plain_wasl` says which of the two mushaf conventions for hamzat al-wasl
    this word's package follows. Hafs, al-Bazzi, Qunbul and Shu'ba write the
    alef wasla letter (U+0671); Warsh marks it with a sign over a plain alif;
    Qaaloon, al-Doori and al-Soosi write a plain alif carrying the vowel the
    wasl would take if you began on it, and no distinct letter at all. In
    those three, a bare alif with a vowel is a wasl alif -- hamzat al-qat' is
    always written on a seat there, in every one of some 9,000 places against
    a single exception per package, and that exception (40:46 'adkhiluu
    against udkhuluu) is a farsh difference and not a spelling."""
    # iqlab is written as a small mim beside a single vowel sign standing for
    # the tanwin; restore the tanwin the sign implies
    w = re.sub('\u064e[\u06e2\u06ed]', '\u064b', w)
    w = re.sub('\u064f[\u06e2\u06ed]', '\u064c', w)
    w = re.sub('\u0650[\u06e2\u06ed]', '\u064d', w)
    # The silent-letter ring over a word-initial alif says two opposite
    # things, and the vowel between them is what tells them apart. Laid
    # against Hafs word for word: of the 544 that carry a vowel Hafs writes
    # the alef wasla letter at every one, and of the 112 that do not it
    # writes hamzat al-qat' at 106 and a bare hamza at the other six. Neither
    # shape ever crosses to the other's side.
    w = re.sub('^\u0627[\u064b-\u0652]\u06df', '', w)
    w = re.sub('^\u0627\u06df', '\u0623', w)
    # hamzat al-wasl, written in the Maghribi mushaf as a sign over the alif.
    # It can sit behind a prefix letter (wa-, fa-, bi-, ka-, li-, ta-), and
    # then the prefix and its vowel stay while the alif and its own vowel go.
    w = re.sub('^([\u0648\u0641\u0628\u0643\u0644\u062a]'
               '[\u064b-\u0652]?)?[\u0627\u0623\u0625]'
               '[\u064b-\u0652\u0656\u0657\u065e]*'
               '[' + WASL_MARKS + ']', lambda m: m.group(1) or '', w)
    w = ''.join(c for c in w if c not in IGNORE and unicodedata.category(c) != 'Nd')
    # The Warsh mushaf writes the wasl alif as a vowelled alif carrying
    # U+06EC; Hafs writes the alef wasla letter.  Neither is a phoneme.
    for seat, whole in (('\u064a\u0654', '\u0626'), ('\u0648\u0654', '\u0624'),
                        ('\u0627\u0654', '\u0623'), ('\u0649\u0654', '\u0626'),
                        ('\u06d2\u0654', '\u0626'), ('\u0627\u0655', '\u0625')):
        w = w.replace(seat, whole)
    for m in WASL_MARKS: w = w.replace(m, '')
    out, i, n = [], 0, len(w)
    while i < n:
        c = w[i]
        nxt = w[i + 1] if i + 1 < n else ''
        nxt2 = w[i + 2] if i + 2 < n else ''
        # The madda over a waw or yaa marks length, not a vowel of its own:
        # the Hafs mushaf writes it where the others do not, so a test for
        # "does this letter carry a diacritic" has to look past it or every
        # qaaluu / qaaluuu pair reads as a difference in the text.
        after = w[i + 1:].lstrip(MADDA)
        nxt_sig = after[0] if after else ''
        if c == 'ٱ':                       # alef wasla: no phoneme
            i += 1; continue
        if c == 'آ':                       # alef madda
            if not out: out.append("'a")
            _emit_long(out, 'A'); i += 1; continue
        if c in 'أإؤئء':   # any hamza seat, or bare
            out.append("'")
            if nxt == MADDA: _emit_long(out, 'A'); i += 1
            i += 1; continue
        if c == 'ة': out.append('h'); i += 1; continue
        if c == ALIF_MAQSURA:
            if (i == n - 1 or (i == n - 2 and w[i + 1] in VOWELS
                               and VOWELS[w[i + 1]].endswith('N'))) \
               and (out and out[-1].endswith('N') or i == n - 2):
                i += 1; continue          # silent carrier of tanwin fath
            if nxt == DAGGER:                   # alif maqsura carrying long a
                _emit_long(out, 'A'); i += 2; continue
            if out and out[-1] == 'a':          # word-final long a
                out[-1] = 'A'; i += 1; continue
            out.append('y'); i += 1; continue
        if c == 'ے': c = 'ي'          # yeh barree
        if c == 'ا' and nxt in (FAT, DAM, KAS) and plain_wasl:
            # a wasl alif and the vowel it carries; never a tanwin, whose
            # silent carrier alif these packages write before the sign
            i += 2; continue
        if c == 'ا' and not out and nxt in VOWELS:
            # word-initial bare alif carrying a vowel: the Maghribi mushaf
            # writes hamzat al-qat' this way where the Kufi one writes a seat
            out.append("'"); i += 1; continue
        if c == 'ا':                       # plain alif
            # A wasl alif is followed by a consonant that carries no vowel of
            # its own (the article's lam, or the first radical of form VII+).
            # A long a is always followed by a vowelled consonant or nothing.
            # It also has to stand where a wasl alif can stand. Without that
            # guard `qaal` -- `qaala` with its final vowel taken by al-Soosi's
            # idghaam -- comes out as `qal`, and every long a that ends up
            # before a bare consonant goes the same way.
            # Alifs before it do not count: one is either a wasl alif that
            # this same branch already dropped, or a hamza seat, and neither
            # stands between a prefix and the word it prefixes.
            head = [x for x in w[:i] if x in CONSONANTS]
            tail = [x for x in w[i + 1:] if x in CONSONANTS or x in 'اأإآءةى']
            if len(head) <= 2 and all(x in PREFIXES for x in head) \
               and len(tail) > 1 \
               and nxt in CONSONANTS and (nxt2 == '' or nxt2 in SUKUNS
                                          or nxt2 == SHAD or nxt2 in CONSONANTS
                                          # form VIII doubles the taa, and
                                          # these files write the shadda after
                                          # the vowel rather than before it
                                          or w[i + 3:i + 4] == SHAD):
                i += 1; continue
            if i <= 2 and nxt == 'ل' and nxt2 in (FAT, DAM, KAS) \
               and w[i + 3:i + 4] == 'ا':
                i += 1; continue      # al- with the hamza's vowel moved onto the lam
            _emit_long(out, 'A'); i += 1; continue
        if c == 'و':
            if out and out[-1] == 'u' and (nxt_sig == ''
                                           or unicodedata.category(nxt_sig) != 'Mn'):
                out[-1] = 'U'
            else:
                out.append('w')
            i += 1; continue
        if c == 'ي':
            if out and out[-1] == 'i' and (nxt_sig == ''
                                           or unicodedata.category(nxt_sig) != 'Mn'):
                out[-1] = 'I'
            else:
                out.append('y')
            i += 1; continue
        if c == DAGGER: _emit_long(out, 'A'); i += 1; continue
        if c == SMALLWAW:
            if sila: _emit_long(out, 'U')
            i += 1; continue
        if c in (SMALLYEH, SMALLYEH2):
            if sila: _emit_long(out, 'I')
            i += 1; continue
        if c in (HAMZA_AB, HAMZA_BE): out.append("'"); i += 1; continue
        if c == MADDA: i += 1; continue
        if c == SHAD:
            for k in range(len(out) - 1, -1, -1):
                if out[k] not in 'auiAUI' and not out[k].endswith('N'):
                    out.insert(k + 1, out[k]); break
            i += 1; continue
        if c == SUK: i += 1; continue
        if c in VOWELS: out.append(VOWELS[c]); i += 1; continue
        if unicodedata.category(c) == 'Mn': i += 1; continue
        if c.isspace(): i += 1; continue
        out.append(c); i += 1
    s = ''.join(out)
    # tanwin fath is written with a silent carrier alif, before the sign in
    # one mushaf and after it in the other; it is not a long vowel either way
    s = s.replace('aNA', 'aN').replace('AaN', 'aN')
    # a long i/u immediately before tanwin fath is really the consonant y/w
    # carrying it, written with the silent carrier alif in between
    s = s.replace('IaN', 'iyaN').replace('UaN', 'uwaN')
    return s


# Which convention each riwaya package follows; see translit's docstring.
PLAIN_WASL = {"qaloon", "doori", "soosi"}


def key(w, sila=True, plain_wasl=False):
    return translit(w, sila, plain_wasl)
