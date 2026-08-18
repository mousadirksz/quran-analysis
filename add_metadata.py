#!/usr/bin/env python3
"""Add reference tables to quran.db: `surahs`, `juz_boundaries`,
`hizb_boundaries` and `verses`.

The corpus table is segment-level, so every script so far rebuilt the verse
text on the fly with nested GROUP_CONCATs and carried its own idea of what a
sura or a juz is. Those facts belong in the database:

  surahs           one row per sura: Arabic name, transliteration, revelation
                   type and order (standard Hafs/Egyptian reference data), and
                   the ayah_count *derived from the corpus itself*. The
                   reference counts are only used to verify the corpus, not to
                   fill the column, so a divergence is reported instead of
                   silently written. ayah_count is COUNT(DISTINCT ayah), the
                   number of ayat the corpus actually holds, not MAX(ayah):
                   with a hole in the corpus the highest number present says
                   nothing about how many verses are there, and the column
                   would then quietly claim more than the database contains.
                   The two are checked against each other (plus MIN(ayah) = 1)
                   and any sura whose numbering is not the unbroken run
                   1..ayah_count is named on stdout.
  juz_boundaries   the 30 ajza' with their first and last verse; the end of a
                   juz is derived from the start of the next one, so only the
                   starts are constants.
  hizb_boundaries  the 60 ahzab (each juz is two ahzab), same construction.
                   The odd hizb of a juz starts where the juz starts; the even
                   one starts at the mushaf's mid-juz mark, which is a fixed
                   published list, not a computed halfway point.
  verses           one row per aya: the joined Arabic text (segments of a word
                   concatenated, a space only between words) with the corpus'
                   leftover Buckwalter markers repaired (see MARKER_TO_ARABIC
                   below), the normalized text used for citation matching
                   (normalize() is imported from resolve_citations.py so the
                   function itself can never drift; note that the *input*
                   does differ - see the note at the end of this docstring),
                   the word count, and the juz/hizb the aya belongs to.

Why text_ar needs repairing at all. corpus.form_ar was produced by converting
the Buckwalter forms of the morphology file to Arabic script, but the mapping
used covers only the letters and the ordinary diacritics. The Quranic Arabic
Corpus writes in an *extended* Buckwalter alphabet in which a dozen ASCII
characters stand for the Quranic annotation signs of the Uthmani script: the
small silent alef of 'قَالُوا۟', the small waw and small yeh of the pronouns
'هُۥ' and 'بِهِۦ', the iqlab meem of 'مِنۢ بَعْدِ', and so on. Those characters were
passed through unconverted, so corpus.form_ar holds 'وا@' where the mushaf has
'وا۟' and 'هُ,' where it has 'هُۥ' - about 12.000 stray ASCII characters over
the corpus. Concatenating those forms straight into a verse column called
text_ar advertises readable Arabic and delivers mojibake.

Repairing beats renaming here. The markers are not noise to be stripped: the
mushaf really does write 'لَهُۥ' and not 'لَهُ', so dropping them would move the
text away from the printed page rather than towards it, and there is a
correct, well-defined Unicode sign for every one of them. Once they are
mapped, text_ar is the Uthmani text of the aya and nothing else, so a second
"clean" column would only give a reader two things to choose between where one
is simply right; the unrepaired forms stay available in corpus.form_ar for
anyone who wants them. What text_ar does *not* carry is the parts of a printed
mushaf page that are not verse text: no waqf (pause) signs, no sajda marks, no
end-of-aya numeral - the corpus does not record them. After the repair every
character of text_ar is in the Arabic Unicode block, apart from the single
genuine space inside 'إِلْ يَاسِينَ' (37:130), and that is asserted rather than
promised: an unknown marker in a future corpus version stops the build.

The repair also reaches text_normalized, and there it changes more than
cosmetics. normalize() turns every character it does not recognize into a
space, so an unrepaired 'أُو@لَٰٓئِكَ' normalized to two tokens 'او ليك' instead of
one 'اوليك', and 'ذَن[بِ' to 'ذن ب' instead of 'ذنب'. 467 of the 6236 verses
normalize differently once the markers are signs rather than ASCII; the signs
themselves fall inside the diacritic class normalize() already strips, so they
leave no trace. Worth knowing: resolve_citations.py does not read this table -
it rebuilds the verse text from corpus.form_ar itself and therefore still
matches against the split-word forms. Until it uses the same repair (or this
table), the two normalized texts are not the same text.

The link from the corpus to juz/hizb runs through verses(surah, ayah); no
existing table is touched.

Idempotent: drops and rebuilds all four tables.
"""

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from resolve_citations import normalize

# Extended-Buckwalter markers left unconverted in corpus.form_ar -> the Unicode
# Quranic annotation sign each of them stands for. Counts are over the whole
# corpus; the examples are the words the marker actually occurs in.
MARKER_TO_ARABIC = {
    "@": "۟",  # 3988x  small high rounded zero: silent alef, qaaluu 'قَالُوا۟'
    ",": "ۥ",  # 1257x  small waw: the long -hu of 'لَهُۥ'
    ".": "ۦ",  #  995x  small yeh: the long -hi of 'بِهِۦ'
    "[": "ۢ",  #  510x  small high meem: iqlab, 'مِنۢ بَعْدِ', 'عَلِيمٌۢ بِ'
    "]": "ۭ",  #   99x  small low meem: iqlab after kasratan, 'مَّكَانٍۭ'
    '"': "۠",  #   66x  small high rectangular zero: 'أَنَا۠'
    ":": "ۜ",  #    2x  small high seen over sad: 'وَيَبْصُۜطُ' (2:245, 7:69)
    ";": "ۣ",  #    1x  small low seen: 'ٱلْمُصَۣيْطِرُونَ' (52:37)
    "!": "ۨ",  #    1x  small high noon: 'نُۨجِى' (21:88)
    "-": "۪",  #    1x  empty centre low stop: 'مَجْر۪ىٰهَا' (11:41)
    "+": "۫",  #    1x  empty centre high stop: 'تَأْمَ۫نَّا' (12:11)
    "%": "۬",  #    1x  rounded high stop, filled centre: 'ءَا۬عْجَمِىٌّ' (41:44)
}

# What text_ar is allowed to contain once the markers are mapped: the Arabic
# block, and the space between words. The corpus writes one word with a space
# inside it (37:130 'إِلْ يَاسِينَ'), which is why the space is not merely a joiner.
NON_ARABIC_ALLOWED = {" "}


def repair_markers(text):
    """Replace the unconverted extended-Buckwalter markers by the Quranic
    annotation signs they encode (see MARKER_TO_ARABIC)."""
    return "".join(MARKER_TO_ARABIC.get(ch, ch) for ch in text)


def check_script(verses):
    """Refuse to write a text_ar that is not Arabic. A corpus update that
    introduces a marker MARKER_TO_ARABIC does not know would otherwise reach
    the column as a stray ASCII character, exactly the way these twelve did."""
    stray = {}
    for s, a, text, _ in verses:
        for ch in text:
            if ch not in NON_ARABIC_ALLOWED and not ("؀" <= ch <= "ۿ"):
                stray.setdefault(ch, (s, a))
    if stray:
        details = ", ".join(f"{ch!r} (U+{ord(ch):04X}, first at {s}:{a})"
                            for ch, (s, a) in sorted(stray.items()))
        raise SystemExit(
            f"verses.text_ar would contain non-Arabic characters: {details}. "
            f"Add them to MARKER_TO_ARABIC in {Path(__file__).name}.")


# number -> (Arabic name, transliteration, revelation type, revelation order).
# Revelation order and type follow the Egyptian standard edition, as used by
# Tanzil; the type of a handful of suras (13 al-Rad, 55 al-Rahman, 99
# al-Zalzala, 76 al-Insan) is disputed in the classical sources and the
# Egyptian classification is taken here.
SURAHS = [
    (1, "الفاتحة", "Al-Fatiha", "meccan", 5),
    (2, "البقرة", "Al-Baqara", "medinan", 87),
    (3, "آل عمران", "Aal-Imran", "medinan", 89),
    (4, "النساء", "An-Nisa", "medinan", 92),
    (5, "المائدة", "Al-Maida", "medinan", 112),
    (6, "الأنعام", "Al-Anaam", "meccan", 55),
    (7, "الأعراف", "Al-Araf", "meccan", 39),
    (8, "الأنفال", "Al-Anfal", "medinan", 88),
    (9, "التوبة", "At-Tawba", "medinan", 113),
    (10, "يونس", "Yunus", "meccan", 51),
    (11, "هود", "Hud", "meccan", 52),
    (12, "يوسف", "Yusuf", "meccan", 53),
    (13, "الرعد", "Ar-Rad", "medinan", 96),
    (14, "إبراهيم", "Ibrahim", "meccan", 72),
    (15, "الحجر", "Al-Hijr", "meccan", 54),
    (16, "النحل", "An-Nahl", "meccan", 70),
    (17, "الإسراء", "Al-Isra", "meccan", 50),
    (18, "الكهف", "Al-Kahf", "meccan", 69),
    (19, "مريم", "Maryam", "meccan", 44),
    (20, "طه", "Ta-Ha", "meccan", 45),
    (21, "الأنبياء", "Al-Anbiya", "meccan", 73),
    (22, "الحج", "Al-Hajj", "medinan", 103),
    (23, "المؤمنون", "Al-Muminun", "meccan", 74),
    (24, "النور", "An-Nur", "medinan", 102),
    (25, "الفرقان", "Al-Furqan", "meccan", 42),
    (26, "الشعراء", "Ash-Shuara", "meccan", 47),
    (27, "النمل", "An-Naml", "meccan", 48),
    (28, "القصص", "Al-Qasas", "meccan", 49),
    (29, "العنكبوت", "Al-Ankabut", "meccan", 85),
    (30, "الروم", "Ar-Rum", "meccan", 84),
    (31, "لقمان", "Luqman", "meccan", 57),
    (32, "السجدة", "As-Sajda", "meccan", 75),
    (33, "الأحزاب", "Al-Ahzab", "medinan", 90),
    (34, "سبأ", "Saba", "meccan", 58),
    (35, "فاطر", "Fatir", "meccan", 43),
    (36, "يس", "Ya-Sin", "meccan", 41),
    (37, "الصافات", "As-Saffat", "meccan", 56),
    (38, "ص", "Sad", "meccan", 38),
    (39, "الزمر", "Az-Zumar", "meccan", 59),
    (40, "غافر", "Ghafir", "meccan", 60),
    (41, "فصلت", "Fussilat", "meccan", 61),
    (42, "الشورى", "Ash-Shura", "meccan", 62),
    (43, "الزخرف", "Az-Zukhruf", "meccan", 63),
    (44, "الدخان", "Ad-Dukhan", "meccan", 64),
    (45, "الجاثية", "Al-Jathiya", "meccan", 65),
    (46, "الأحقاف", "Al-Ahqaf", "meccan", 66),
    (47, "محمد", "Muhammad", "medinan", 95),
    (48, "الفتح", "Al-Fath", "medinan", 111),
    (49, "الحجرات", "Al-Hujurat", "medinan", 106),
    (50, "ق", "Qaf", "meccan", 34),
    (51, "الذاريات", "Adh-Dhariyat", "meccan", 67),
    (52, "الطور", "At-Tur", "meccan", 76),
    (53, "النجم", "An-Najm", "meccan", 23),
    (54, "القمر", "Al-Qamar", "meccan", 37),
    (55, "الرحمن", "Ar-Rahman", "medinan", 97),
    (56, "الواقعة", "Al-Waqia", "meccan", 46),
    (57, "الحديد", "Al-Hadid", "medinan", 94),
    (58, "المجادلة", "Al-Mujadila", "medinan", 105),
    (59, "الحشر", "Al-Hashr", "medinan", 101),
    (60, "الممتحنة", "Al-Mumtahana", "medinan", 91),
    (61, "الصف", "As-Saff", "medinan", 109),
    (62, "الجمعة", "Al-Jumua", "medinan", 110),
    (63, "المنافقون", "Al-Munafiqun", "medinan", 104),
    (64, "التغابن", "At-Taghabun", "medinan", 108),
    (65, "الطلاق", "At-Talaq", "medinan", 99),
    (66, "التحريم", "At-Tahrim", "medinan", 107),
    (67, "الملك", "Al-Mulk", "meccan", 77),
    (68, "القلم", "Al-Qalam", "meccan", 2),
    (69, "الحاقة", "Al-Haqqa", "meccan", 78),
    (70, "المعارج", "Al-Maarij", "meccan", 79),
    (71, "نوح", "Nuh", "meccan", 71),
    (72, "الجن", "Al-Jinn", "meccan", 40),
    (73, "المزمل", "Al-Muzzammil", "meccan", 3),
    (74, "المدثر", "Al-Muddaththir", "meccan", 4),
    (75, "القيامة", "Al-Qiyama", "meccan", 31),
    (76, "الإنسان", "Al-Insan", "medinan", 98),
    (77, "المرسلات", "Al-Mursalat", "meccan", 33),
    (78, "النبأ", "An-Naba", "meccan", 80),
    (79, "النازعات", "An-Naziat", "meccan", 81),
    (80, "عبس", "Abasa", "meccan", 24),
    (81, "التكوير", "At-Takwir", "meccan", 7),
    (82, "الانفطار", "Al-Infitar", "meccan", 82),
    (83, "المطففين", "Al-Mutaffifin", "meccan", 86),
    (84, "الانشقاق", "Al-Inshiqaq", "meccan", 83),
    (85, "البروج", "Al-Buruj", "meccan", 27),
    (86, "الطارق", "At-Tariq", "meccan", 36),
    (87, "الأعلى", "Al-Ala", "meccan", 8),
    (88, "الغاشية", "Al-Ghashiya", "meccan", 68),
    (89, "الفجر", "Al-Fajr", "meccan", 10),
    (90, "البلد", "Al-Balad", "meccan", 35),
    (91, "الشمس", "Ash-Shams", "meccan", 26),
    (92, "الليل", "Al-Layl", "meccan", 9),
    (93, "الضحى", "Ad-Duha", "meccan", 11),
    (94, "الشرح", "Ash-Sharh", "meccan", 12),
    (95, "التين", "At-Tin", "meccan", 28),
    (96, "العلق", "Al-Alaq", "meccan", 1),
    (97, "القدر", "Al-Qadr", "meccan", 25),
    (98, "البينة", "Al-Bayyina", "medinan", 100),
    (99, "الزلزلة", "Az-Zalzala", "medinan", 93),
    (100, "العاديات", "Al-Adiyat", "meccan", 14),
    (101, "القارعة", "Al-Qaria", "meccan", 30),
    (102, "التكاثر", "At-Takathur", "meccan", 16),
    (103, "العصر", "Al-Asr", "meccan", 13),
    (104, "الهمزة", "Al-Humaza", "meccan", 32),
    (105, "الفيل", "Al-Fil", "meccan", 19),
    (106, "قريش", "Quraysh", "meccan", 29),
    (107, "الماعون", "Al-Maun", "meccan", 17),
    (108, "الكوثر", "Al-Kawthar", "meccan", 15),
    (109, "الكافرون", "Al-Kafirun", "meccan", 18),
    (110, "النصر", "An-Nasr", "medinan", 114),
    (111, "المسد", "Al-Masad", "meccan", 6),
    (112, "الإخلاص", "Al-Ikhlas", "meccan", 22),
    (113, "الفلق", "Al-Falaq", "meccan", 20),
    (114, "الناس", "An-Nas", "meccan", 21),
]

# Hafs ayah counts, for verification against the corpus only. They are never
# written to the table: ayah_count is what the corpus actually contains.
REFERENCE_AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109, 123, 111, 43, 52, 99,
    128, 111, 110, 98, 135, 112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85, 54, 53, 89, 59, 37, 35, 38,
    29, 18, 45, 60, 49, 62, 55, 78, 96, 29, 22, 24, 13, 14, 11, 11, 18,
    12, 12, 30, 52, 52, 44, 28, 28, 20, 56, 40, 31, 50, 40, 46, 42, 29,
    19, 36, 25, 22, 17, 19, 26, 30, 20, 15, 21, 11, 8, 8, 19, 5, 8, 8,
    11, 11, 8, 3, 9, 5, 4, 7, 3, 6, 3, 5, 4, 5, 6,
]

# First verse of each juz (standard Hafs division of the mushaf).
JUZ_STARTS = [
    (1, 1), (2, 142), (2, 253), (3, 92), (4, 24), (4, 148), (5, 82),
    (6, 111), (7, 88), (8, 41), (9, 93), (11, 6), (12, 53), (15, 1),
    (17, 1), (18, 75), (21, 1), (23, 1), (25, 21), (27, 56), (29, 46),
    (33, 31), (36, 28), (39, 32), (41, 47), (46, 1), (51, 31), (58, 1),
    (67, 1), (78, 1),
]

# First verse of each hizb. The odd ones repeat the juz starts above; the
# even ones are the mid-juz marks of the mushaf al-Madina, which are a fixed
# published list (a juz is not split at an arbitrary halfway point).
HIZB_STARTS = [
    (1, 1), (2, 75), (2, 142), (2, 203), (2, 253), (3, 15), (3, 92),
    (3, 171), (4, 24), (4, 88), (4, 148), (5, 27), (5, 82), (6, 36),
    (6, 111), (7, 1), (7, 88), (7, 196), (8, 41), (9, 34), (9, 93),
    (10, 26), (11, 6), (11, 84), (12, 53), (13, 19), (15, 1), (16, 51),
    (17, 1), (17, 99), (18, 75), (20, 1), (21, 1), (22, 1), (23, 1),
    (24, 21), (25, 21), (26, 111), (27, 56), (29, 1), (29, 46), (31, 22),
    (33, 31), (34, 24), (36, 28), (38, 1), (39, 32), (40, 41), (41, 47),
    (43, 24), (46, 1), (48, 18), (51, 31), (54, 9), (58, 1), (61, 1),
    (67, 1), (71, 1), (78, 1), (82, 1),
]


def load_verses(cur):
    """Rebuild every verse from the segment-level corpus: the segments of one
    word are concatenated without a separator, words are joined with a space,
    and the leftover Buckwalter markers are mapped to their Arabic signs."""
    cur.execute("SELECT surah, ayah, word, form_ar FROM corpus "
                "ORDER BY surah, ayah, word, segment")
    words = {}
    for s, a, w, form in cur.fetchall():
        words.setdefault((s, a), {}).setdefault(w, []).append(form)
    verses = []
    for (s, a) in sorted(words):
        forms = [("".join(words[(s, a)][w])) for w in sorted(words[(s, a)])]
        verses.append((s, a, repair_markers(" ".join(forms)), len(forms)))
    return verses


def count_ayat(order):
    """ayah_count per sura, and the suras whose ayah numbering is not the
    unbroken run 1..count. Returns (counts, breaks) where a break is
    (sura, count, max, missing numbers)."""
    seen = {}
    for s, a in order:
        seen.setdefault(s, set()).add(a)
    counts = {s: len(ayat) for s, ayat in seen.items()}
    breaks = []
    for s, ayat in sorted(seen.items()):
        top = max(ayat)
        if len(ayat) != top or min(ayat) != 1:
            missing = sorted(set(range(1, top + 1)) - ayat)
            breaks.append((s, len(ayat), top, missing))
    return counts, breaks


def assign(order, starts):
    """Map every verse to the 1-based index of the division it falls in,
    given the ordered verse list and the division's first verses."""
    pos = {key: i for i, key in enumerate(order)}
    missing = [st for st in starts if st not in pos]
    if missing:
        raise SystemExit(f"division starts absent from the corpus: {missing}")
    cuts = [pos[st] for st in starts]
    division = {}
    for n, start in enumerate(cuts, 1):
        end = cuts[n] if n < len(cuts) else len(order)
        for i in range(start, end):
            division[order[i]] = n
    return division


def boundaries(order, starts):
    pos = {key: i for i, key in enumerate(order)}
    rows = []
    for n, st in enumerate(starts, 1):
        last = pos[starts[n]] - 1 if n < len(starts) else len(order) - 1
        rows.append((n,) + st + order[last])
    return rows


def main():
    con = sqlite3.connect(HERE / "quran.db")
    cur = con.cursor()

    verses = load_verses(cur)
    check_script(verses)
    order = [(s, a) for s, a, _, _ in verses]
    ayah_counts, numbering_breaks = count_ayat(order)

    juz = assign(order, JUZ_STARTS)
    hizb = assign(order, HIZB_STARTS)

    cur.execute("DROP TABLE IF EXISTS surahs")
    cur.execute("""CREATE TABLE surahs (
        number INTEGER PRIMARY KEY,
        name_ar TEXT, name_en TEXT,
        revelation_type TEXT, revelation_order INTEGER,
        ayah_count INTEGER)""")
    cur.executemany(
        "INSERT INTO surahs VALUES (?,?,?,?,?,?)",
        [(n, ar, en, typ, rev, ayah_counts[n]) for n, ar, en, typ, rev in SURAHS])

    cur.execute("DROP TABLE IF EXISTS juz_boundaries")
    cur.execute("""CREATE TABLE juz_boundaries (
        juz INTEGER PRIMARY KEY,
        start_surah INTEGER, start_ayah INTEGER,
        end_surah INTEGER, end_ayah INTEGER)""")
    cur.executemany("INSERT INTO juz_boundaries VALUES (?,?,?,?,?)",
                    boundaries(order, JUZ_STARTS))

    cur.execute("DROP TABLE IF EXISTS hizb_boundaries")
    cur.execute("""CREATE TABLE hizb_boundaries (
        hizb INTEGER PRIMARY KEY, juz INTEGER,
        start_surah INTEGER, start_ayah INTEGER,
        end_surah INTEGER, end_ayah INTEGER)""")
    cur.executemany(
        "INSERT INTO hizb_boundaries VALUES (?,?,?,?,?,?)",
        [(n, (n + 1) // 2, ss, sa, es, ea)
         for n, ss, sa, es, ea in boundaries(order, HIZB_STARTS)])

    cur.execute("DROP TABLE IF EXISTS verses")
    cur.execute("""CREATE TABLE verses (
        surah INTEGER, ayah INTEGER,
        text_ar TEXT, text_normalized TEXT,
        word_count INTEGER, juz INTEGER, hizb INTEGER,
        PRIMARY KEY (surah, ayah))""")
    cur.executemany(
        "INSERT INTO verses VALUES (?,?,?,?,?,?,?)",
        [(s, a, text, normalize(text), wc, juz[(s, a)], hizb[(s, a)])
         for s, a, text, wc in verses])

    cur.execute("CREATE INDEX IF NOT EXISTS idx_verses_juz ON verses(juz)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_verses_hizb ON verses(hizb)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_surahs_rev "
                "ON surahs(revelation_order)")
    con.commit()

    deviations = [(n, ayah_counts[n], ref)
                  for (n, *_), ref in zip(SURAHS, REFERENCE_AYAH_COUNTS)
                  if ayah_counts[n] != ref]
    total = sum(ayah_counts.values())
    con.close()

    print(f"surahs: {len(SURAHS)} | juz_boundaries: 30 | hizb_boundaries: 60 "
          f"| verses: {len(verses)} (ayat totaal {total})")
    if numbering_breaks:
        print("  LET OP: ayah-nummering niet aaneengesloten, ayah_count telt "
              "wat er staat en niet het hoogste nummer:")
        for n, got, top, missing in numbering_breaks:
            gaps = ", ".join(str(m) for m in missing[:10])
            more = f" (+{len(missing) - 10})" if len(missing) > 10 else ""
            print(f"    sura {n}: {got} ayat, hoogste nummer {top}, "
                  f"ontbreekt: {gaps}{more}")
    if deviations:
        for n, got, ref in deviations:
            print(f"  ayah_count sura {n}: corpus {got}, Hafs-referentie {ref}")
    else:
        print("  ayah_count komt voor alle 114 soera's overeen met Hafs")


if __name__ == "__main__":
    main()
