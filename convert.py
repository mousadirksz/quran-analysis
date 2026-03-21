#!/usr/bin/env python3
"""
Convert the Quranic Arabic Corpus morphology file from Buckwalter
transliteration to Arabic script, and expand features into separate columns.

Input:  quranic-corpus-morphology-0.4.txt  (tab-separated)
Output: quranic-corpus-arabic.tsv          (tab-separated, one column per feature)
"""

import csv
import re
from pathlib import Path

# ── Buckwalter-to-Arabic mapping ────────────────────────────────────────────
BUCKWALTER_TO_ARABIC = {
    "'": "\u0621",   # ء  hamza
    "|": "\u0622",   # آ  alef with madda
    ">": "\u0623",   # أ  alef with hamza above
    "&": "\u0624",   # ؤ  waw with hamza
    "<": "\u0625",   # إ  alef with hamza below
    "}": "\u0626",   # ئ  ya with hamza
    "A": "\u0627",   # ا  alef
    "b": "\u0628",   # ب
    "p": "\u0629",   # ة  ta marbuta
    "t": "\u062A",   # ت
    "v": "\u062B",   # ث
    "j": "\u062C",   # ج
    "H": "\u062D",   # ح
    "x": "\u062E",   # خ
    "d": "\u062F",   # د
    "*": "\u0630",   # ذ
    "r": "\u0631",   # ر
    "z": "\u0632",   # ز
    "s": "\u0633",   # س
    "$": "\u0634",   # ش
    "S": "\u0635",   # ص
    "D": "\u0636",   # ض
    "T": "\u0637",   # ط
    "Z": "\u0638",   # ظ
    "E": "\u0639",   # ع
    "g": "\u063A",   # غ
    "_": "\u0640",   # ـ  tatweel
    "f": "\u0641",   # ف
    "q": "\u0642",   # ق
    "k": "\u0643",   # ك
    "l": "\u0644",   # ل
    "m": "\u0645",   # م
    "n": "\u0646",   # ن
    "h": "\u0647",   # ه
    "w": "\u0648",   # و
    "Y": "\u0649",   # ى  alef maksura
    "y": "\u064A",   # ي
    "F": "\u064B",   # ً  fathatan
    "N": "\u064C",   # ٌ  dammatan
    "K": "\u064D",   # ٍ  kasratan
    "a": "\u064E",   # َ  fatha
    "u": "\u064F",   # ُ  damma
    "i": "\u0650",   # ِ  kasra
    "~": "\u0651",   # ّ  shadda
    "o": "\u0652",   # ْ  sukun
    "`": "\u0670",   # ٰ  superscript alef (dagger alef)
    "{": "\u0671",   # ٱ  alef wasla
    "^": "\u0653",   # ٓ  maddah above
    "#": "\u0654",   # ٔ  hamza above (combining)
}


def buckwalter_to_arabic(bw_text: str) -> str:
    """Convert a Buckwalter-encoded string to Arabic script."""
    return "".join(BUCKWALTER_TO_ARABIC.get(ch, ch) for ch in bw_text)


# ── Feature parsing ────────────────────────────────────────────────────────

# Verb forms like (II), (IV), (X), etc.
VERB_FORM_RE = re.compile(r"^\(([IVX]+)\)$")

# Person/gender/number like 1P, 2MS, 3FP, 2FD, etc.
PGN_RE = re.compile(r"^[123][MF]?[SDP]$")

# Gender+Number (no person) like MS, MP, FS, FP, MD, FD, M, F
GN_RE = re.compile(r"^[MF][SDP]?$")

# Grammatical case: NOM, ACC, GEN
CASE_RE = re.compile(r"^(NOM|ACC|GEN)$")

# Mood values
MOOD_VALUES = {"IND", "SUBJ", "JUS"}

# Verb aspect: PERF, IMPF, IMPV
ASPECT_RE = re.compile(r"^(PERF|IMPF|IMPV)$")

# Definiteness
DEF_VALUES = {"INDEF", "DEF"}

# Voice / participle
VOICE_VALUES = {"ACT", "PASS"}

# Special tags
SPECIAL_TAGS = {"PCPL", "VN"}


def parse_features(raw: str) -> dict:
    """
    Parse the pipe-delimited FEATURES string into a dict of named columns.

    Returns a dict with these possible keys:
        segment_type  – PREFIX / STEM / SUFFIX
        pos           – part of speech (N, V, ADJ, PN, …)
        lemma         – lemma in Buckwalter
        lemma_ar      – lemma in Arabic
        root          – triliteral root in Buckwalter
        root_ar       – root in Arabic
        person        – 1 / 2 / 3
        gender        – M / F
        number        – S / P / D
        case          – NOM / ACC / GEN
        mood          – IND / SUBJ / JUS
        state         – INDEF / DEF
        voice         – ACT / PASS
        derivation    – PCPL / VN
        aspect        – PERF / IMPF / IMPV
        verb_form     – II, III, IV, …, XII
        prefix        – raw prefix string (e.g. bi+, Al+, w:CONJ+)
        suffix_pron   – pronoun encoded in suffix (e.g. 1P, 3MS)
        special       – SP:… value
    """
    result = {}
    tokens = raw.split("|")

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # ── segment type ──
        if token in ("PREFIX", "STEM", "SUFFIX"):
            result["segment_type"] = token
            continue

        # ── POS:X ──
        if token.startswith("POS:"):
            result["pos"] = token[4:]
            continue

        # ── LEM:X ──
        if token.startswith("LEM:"):
            lem = token[4:]
            result["lemma"] = lem
            result["lemma_ar"] = buckwalter_to_arabic(lem)
            continue

        # ── ROOT:X ──
        if token.startswith("ROOT:"):
            root = token[5:]
            result["root"] = root
            result["root_ar"] = buckwalter_to_arabic(root)
            continue

        # ── PRON:X (suffix pronoun) ──
        if token.startswith("PRON:"):
            result["suffix_pron"] = token[5:]
            continue

        # ── SP:X (special particle info) ──
        if token.startswith("SP:"):
            result["special"] = token[3:]
            continue

        # ── MOOD:X ──
        if token.startswith("MOOD:"):
            result["mood"] = token[5:]
            continue

        # ── Prefix with + ──
        if token.endswith("+"):
            result.setdefault("prefix", "")
            if result["prefix"]:
                result["prefix"] += " + " + token
            else:
                result["prefix"] = token
            continue

        # ── Verb form (II)…(XII) ──
        m = VERB_FORM_RE.match(token)
        if m:
            result["verb_form"] = m.group(1)
            continue

        # ── Aspect PERF/IMPF/IMPV ──
        if ASPECT_RE.match(token):
            result["aspect"] = token
            continue

        # ── Case NOM/ACC/GEN ──
        if CASE_RE.match(token):
            result["case"] = token
            continue

        # ── Mood (standalone) ──
        if token in MOOD_VALUES:
            result["mood"] = token
            continue

        # ── Voice ACT/PASS ──
        if token in VOICE_VALUES:
            result["voice"] = token
            continue

        # ── PCPL / VN ──
        if token in SPECIAL_TAGS:
            result["derivation"] = token
            continue

        # ── INDEF ──
        if token in DEF_VALUES:
            result["state"] = token
            continue

        # ── Person-Gender-Number (verb/pronoun subject) ──
        if PGN_RE.match(token):
            result["person"] = token[0]
            if len(token) == 3:
                result["gender"] = token[1]
                result["number"] = token[2]
            elif len(token) == 2:
                # Could be 1P, 1S (no gender) or MS, etc.
                if token[1] in "SPD":
                    result["number"] = token[1]
                else:
                    result["gender"] = token[1]
            continue

        # ── Gender-Number without person (MS, MP, FS, FP, M, F, …) ──
        if GN_RE.match(token):
            result["gender"] = token[0]
            if len(token) == 2:
                result["number"] = token[1]
            continue

    return result


# ── Column definitions (output order) ──────────────────────────────────────
FEATURE_COLUMNS = [
    "segment_type",
    "pos",
    "lemma",
    "lemma_ar",
    "root",
    "root_ar",
    "aspect",
    "verb_form",
    "voice",
    "derivation",
    "person",
    "gender",
    "number",
    "case",
    "mood",
    "state",
    "prefix",
    "suffix_pron",
    "special",
]


def main():
    src = Path(__file__).parent / "quranic-corpus-morphology-0.4.txt"
    dst = Path(__file__).parent / "quranic-corpus-arabic.tsv"

    with open(src, encoding="utf-8") as fin, \
         open(dst, "w", encoding="utf-8", newline="") as fout:

        writer = csv.writer(fout, delimiter="\t")

        # Header
        writer.writerow([
            "surah", "ayah", "word", "segment",
            "form_bw", "form_ar", "tag",
        ] + FEATURE_COLUMNS)

        for line in fin:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("LOCATION"):
                continue

            parts = line.split("\t")
            if len(parts) < 4:
                continue

            location, form_bw, tag, features_raw = parts[0], parts[1], parts[2], parts[3]

            # Parse location (chapter:verse:word:segment)
            loc = location.strip("()")
            loc_parts = loc.split(":")
            surah, ayah, word, segment = loc_parts

            # Convert form to Arabic
            form_ar = buckwalter_to_arabic(form_bw)

            # Parse features into columns
            feat = parse_features(features_raw)

            row = [
                surah, ayah, word, segment,
                form_bw, form_ar, tag,
            ] + [feat.get(col, "") for col in FEATURE_COLUMNS]

            writer.writerow(row)

    print(f"✓ Written to {dst}")
    print(f"  Columns: surah, ayah, word, segment, form_bw, form_ar, tag, "
          + ", ".join(FEATURE_COLUMNS))


if __name__ == "__main__":
    main()
