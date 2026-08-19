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


def _emit_long(out, ch):
    short = {'A': 'a', 'U': 'u', 'I': 'i'}[ch]
    if out and out[-1] == short:
        out[-1] = ch
    else:
        out.append(ch)


def translit(w, sila=True):
    # iqlab is written as a small mim beside a single vowel sign standing for
    # the tanwin; restore the tanwin the sign implies
    w = re.sub('\u064e[\u06e2\u06ed]', '\u064b', w)
    w = re.sub('\u064f[\u06e2\u06ed]', '\u064c', w)
    w = re.sub('\u0650[\u06e2\u06ed]', '\u064d', w)
    # a word-initial alif carrying the "silent letter" ring is a hamza seat
    # whose vowel this mushaf leaves unwritten
    w = re.sub('^\u0627\u06df', '\u0623', w)
    # hamzat al-wasl, written in the Maghribi mushaf as a sign over the alif
    w = re.sub('^[\u0627\u0623\u0625][\u064b-\u0652\u0656\u0657\u065e]*'
               + '[' + WASL_MARKS + ']', '', w)
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
        if c == 'ا' and not out and nxt in VOWELS:
            # word-initial bare alif carrying a vowel: the Maghribi mushaf
            # writes hamzat al-qat' this way where the Kufi one writes a seat
            out.append("'"); i += 1; continue
        if c == 'ا':                       # plain alif
            # A wasl alif is followed by a consonant that carries no vowel of
            # its own (the article's lam, or the first radical of form VII+).
            # A long a is always followed by a vowelled consonant or nothing.
            if nxt in CONSONANTS and (nxt2 == '' or nxt2 == SUK or
                                      nxt2 == SHAD or nxt2 in CONSONANTS):
                i += 1; continue
            if i <= 2 and nxt == 'ل' and nxt2 in (FAT, DAM, KAS) \
               and w[i + 3:i + 4] == 'ا':
                i += 1; continue      # al- with the hamza's vowel moved onto the lam
            _emit_long(out, 'A'); i += 1; continue
        if c == 'و':
            if out and out[-1] == 'u' and (nxt == '' or unicodedata.category(nxt) != 'Mn'):
                out[-1] = 'U'
            else:
                out.append('w')
            i += 1; continue
        if c == 'ي':
            if out and out[-1] == 'i' and (nxt == '' or unicodedata.category(nxt) != 'Mn'):
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


def key(w, sila=True):
    return translit(w, sila)
