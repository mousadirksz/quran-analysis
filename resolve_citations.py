#!/usr/bin/env python3
"""Resolve the Quran citations in the parsed wujuh works (al-Damaghani,
Ibn al-Jawzi) to sura:aya references by matching them against the corpus
text in quran.db.

Both the quotes and the corpus text are normalized aggressively (diacritics
stripped, hamza/alef/ya variants collapsed) because the Shamela digitizations
quote from memory-orthography rather than the exact mushaf rasm.

Resolution per quote:
  1. exact normalized substring match against all verses
  2. if multiple verses match, the work's sura hint (when parsed) filters
  3. if no match, retry with the first/last word dropped (quotes often fuse
     the author's framing words onto the quote)

Output: sources/resolved_citations.json + statistics on stdout.
"""

import json
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent

DIACRITICS = re.compile(r"[ً-ٰٟۖ-ۭـ۟]")


def normalize(s):
    s = s.replace("و\u0670", "ا").replace("\u0670", "")  # dagger alif: rasm -> modern
    s = DIACRITICS.sub("", s)
    s = re.sub("[آأإٱا]", "ا", s)
    s = s.replace("ى", "ي").replace("ئ", "ي").replace("ؤ", "و").replace("ء", "")
    s = s.replace("ة", "ه")
    s = re.sub(r"[^ء-ي ]", " ", s)
    s = re.sub(r"ا+", "ا", s)  # hamza+alef spellings (e.g. ءَابَآئِكَ) collapse
    return re.sub(r"\s+", " ", s).strip()


# classical sura names (incl. variant names used by the two authors) -> number
SURA_NAMES = {
    "الفاتحه": 1, "الحمد": 1, "البقره": 2, "ال عمران": 3, "عمران": 3,
    "النسا": 4, "المايده": 5, "المائده": 5, "الانعام": 6, "الاعراف": 7,
    "الانفال": 8, "التوبه": 9, "براه": 9, "برائه": 9, "براءه": 9,
    "يونس": 10, "هود": 11, "يوسف": 12, "الرعد": 13, "ابراهيم": 14,
    "الحجر": 15, "النحل": 16, "الاسرا": 17, "بني اسرايل": 17,
    "الكهف": 18, "مريم": 19, "طه": 20, "الانبيا": 21, "الحج": 22,
    "المومنون": 23, "المومنين": 23, "النور": 24, "الفرقان": 25,
    "الشعرا": 26, "النمل": 27, "القصص": 28, "العنكبوت": 29, "الروم": 30,
    "لقمان": 31, "السجده": 32, "الم السجده": 32, "الاحزاب": 33,
    "سبا": 34, "فاطر": 35, "الملايكه": 35, "الملائكه": 35, "يس": 36,
    "الصافات": 37, "ص": 38, "الزمر": 39, "غافر": 40, "المومن": 40,
    "فصلت": 41, "حم السجده": 41, "الشوري": 42, "حم عسق": 42,
    "الزخرف": 43, "الدخان": 44, "الجاثيه": 45, "الاحقاف": 46,
    "محمد": 47, "القتال": 47, "الفتح": 48, "الحجرات": 49, "ق": 50,
    "الذاريات": 51, "الطور": 52, "النجم": 53, "القمر": 54, "اقتربت": 54,
    "الرحمن": 55, "الواقعه": 56, "الحديد": 57, "المجادله": 58,
    "الحشر": 59, "الممتحنه": 60, "الصف": 61, "الجمعه": 62,
    "المنافقون": 63, "المنافقين": 63, "التغابن": 64, "الطلاق": 65,
    "التحريم": 66, "الملك": 67, "القلم": 68, "ن": 68, "الحاقه": 69,
    "المعارج": 70, "سال سايل": 70, "نوح": 71, "الجن": 72, "المزمل": 73,
    "المدثر": 74, "القيامه": 75, "الانسان": 76, "الدهر": 76,
    "المرسلات": 77, "النبا": 78, "عم": 78, "النازعات": 79, "عبس": 80,
    "التكوير": 81, "كورت": 81, "الانفطار": 82, "انفطرت": 82,
    "المطففين": 83, "الانشقاق": 84, "انشقت": 84, "البروج": 85,
    "الطارق": 86, "الاعلي": 87, "سبح": 87, "الغاشيه": 88, "الفجر": 89,
    "البلد": 90, "الشمس": 91, "الليل": 92, "الضحي": 93, "الشرح": 94,
    "الم نشرح": 94, "التين": 95, "العلق": 96, "اقرا": 96, "القدر": 97,
    "البينه": 98, "لم يكن": 98, "الزلزله": 99, "اذا زلزلت": 99,
    "العاديات": 100, "القارعه": 101, "التكاثر": 102, "الهاكم": 102,
    "العصر": 103, "الهمزه": 104, "الفيل": 105, "قريش": 106,
    "الماعون": 107, "ارايت": 107, "الكوثر": 108, "الكافرون": 109,
    "النصر": 110, "المسد": 111, "تبت": 111, "الاخلاص": 112,
    "الفلق": 113, "الناس": 114,
}


def load_verses():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()
    cur.execute("""SELECT surah, ayah, GROUP_CONCAT(form_ar, '') FROM
        (SELECT surah, ayah, word, GROUP_CONCAT(form_ar,'') form_ar
         FROM corpus GROUP BY surah, ayah, word ORDER BY surah, ayah, word, segment)
        GROUP BY surah, ayah""")
    rows = cur.fetchall()
    # rebuild with spaces between words
    cur.execute("""SELECT surah, ayah, word, GROUP_CONCAT(form_ar,'')
        FROM corpus GROUP BY surah, ayah, word ORDER BY surah, ayah, word, segment""")
    verses = {}
    for s, a, w, form in cur.fetchall():
        verses.setdefault((s, a), []).append(form)
    return {k: normalize(" ".join(v)) for k, v in verses.items()}


def skeleton(s):
    """Consonantal skeleton: long vowels stripped, so that Uthmani rasm and
    modern orthography (slwh/slah, smwt/smawat) collapse together."""
    return re.sub(r"\s+", " ", re.sub("[اوي]", "", s)).strip()


def resolve_quote(qnorm, verses, skel_verses, sura_hints):
    if len(qnorm) < 8:  # too short to be distinctive
        return None, "too_short"
    hits = [k for k, v in verses.items() if qnorm in v]
    if not hits:
        words = qnorm.split()
        for trial in (words[1:], words[:-1], words[1:-1]):
            if len(trial) >= 3:
                t = " ".join(trial)
                hits = [k for k, v in verses.items() if t in v]
                if hits:
                    break
    if not hits:
        # tier 2: skeleton match, tolerant of rasm/orthography differences
        qs = skeleton(qnorm)
        if len(qs.replace(" ", "")) >= 6:
            hits = [k for k, v in skel_verses.items() if qs in v]
            if not hits:
                words = qs.split()
                for trial in (words[1:], words[:-1], words[1:-1]):
                    if len(trial) >= 3:
                        t = " ".join(trial)
                        hits = [k for k, v in skel_verses.items() if t in v]
                        if hits:
                            break
            if not hits:
                # tier 3: space-insensitive (mushaf joins e.g. يٰأبت)
                qss = qs.replace(" ", "")
                hits = [k for k, v in skel_verses.items()
                        if qss in v.replace(" ", "")]
    if not hits:
        return None, "no_match"
    if len(hits) == 1:
        return hits, "unique"
    hinted = [h for h in hits if h[0] in sura_hints]
    if len(set(h[0] for h in hinted)) == 1 and hinted:
        return hinted, "hint_resolved"
    return hits, "ambiguous"


def main():
    verses = load_verses()
    skel_verses = {k: skeleton(v) for k, v in verses.items()}
    out = {}
    for work, fn in (("damaghani", "damaghani_wujuh.json"),
                     ("ibnjawzi", "ibnjawzi_wujuh.json")):
        entries = json.loads((HERE / "sources" / fn).read_text(encoding="utf-8"))
        stats = {"unique": 0, "hint_resolved": 0, "ambiguous": 0,
                 "no_match": 0, "too_short": 0}
        resolved_entries = []
        for e in entries:
            r_senses = []
            for sense in e["senses"]:
                hints = {SURA_NAMES[normalize(s)] for s in sense.get("suras", [])
                         if normalize(s) in SURA_NAMES}
                r_quotes = []
                for q in sense["quotes"]:
                    refs, status = resolve_quote(normalize(q), verses, skel_verses, hints)
                    stats[status] += 1
                    r_quotes.append({"quote": q, "status": status,
                                     "refs": [f"{s}:{a}" for s, a in (refs or [])][:10]})
                r_senses.append({"nr": sense["nr"], "gloss": sense["gloss"],
                                 "quotes": r_quotes})
            resolved_entries.append({"headword": e["headword"],
                                     "declared": e["declared"], "senses": r_senses})
        out[work] = resolved_entries
        total = sum(stats.values())
        ok = stats["unique"] + stats["hint_resolved"]
        print(f"{work}: {total} quotes -> resolved {ok} ({ok/total*100:.0f}%) "
              f"[unique {stats['unique']}, via sura-hint {stats['hint_resolved']}, "
              f"ambiguous {stats['ambiguous']}, no match {stats['no_match']}, "
              f"too short {stats['too_short']}]")
    (HERE / "sources" / "resolved_citations.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
