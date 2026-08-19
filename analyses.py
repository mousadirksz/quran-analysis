#!/usr/bin/env python3
"""Reproduce every finding in BEVINDINGEN.md against quran.db.

Each finding in that document is produced by one named analysis here, so the
numbers can be re-derived rather than trusted:

    python3 analyses.py                 # list the analyses
    python3 analyses.py juz-amma        # run one
    python3 analyses.py --all           # run all, in document order

Analyses that quote the wujuh layer filter on confidence='high' unless stated
otherwise: the lower tiers are candidate lists, not attestations.
"""

import sqlite3
import sys
from collections import Counter
from pathlib import Path

DB = Path(__file__).parent / "quran.db"
JUZ_AMMA = 78  # juz 30 begins at 78:1


def head(title):
    print("\n" + "=" * 62 + "\n" + title + "\n" + "=" * 62)


def one(c, sql, args=()):
    return c.execute(sql, args).fetchone()[0]


# --------------------------------------------------------------- corpus layer

def basics(c):
    head("Basistellingen")
    stats = [
        ("soera's", "SELECT COUNT(DISTINCT surah) FROM corpus"),
        ("verzen", "SELECT COUNT(*) FROM verses"),
        ("geschreven woorden", "SELECT COUNT(*) FROM words"),
        ("segmenten (kalimat)", "SELECT COUNT(*) FROM corpus"),
        ("unieke roots", "SELECT COUNT(DISTINCT root_ar) FROM corpus WHERE root_ar != ''"),
        ("unieke lemma's", "SELECT COUNT(DISTINCT lemma) FROM corpus WHERE lemma != ''"),
        ("segmenten met root", "SELECT COUNT(*) FROM corpus WHERE root_ar != ''"),
    ]
    for label, sql in stats:
        print("  %-22s %8s" % (label, format(one(c, sql), ",")))


def kalima(c):
    head("Kalimat per soort (nahw-indeling)")
    rows = c.execute("SELECT kalima_type, COUNT(*), COUNT(DISTINCT lemma) FROM corpus"
                     " GROUP BY kalima_type ORDER BY 2 DESC").fetchall()
    total = sum(r[1] for r in rows)
    for kt, n, lem in rows:
        print("  %-11s %7s  %5.1f%%   %5s unieke lemma's"
              % (kt, format(n, ","), n / total * 100, format(lem, ",")))
    print("  %-11s %7s" % ("totaal", format(total, ",")))
    words = one(c, "SELECT COUNT(DISTINCT lemma || '|' || kalima_type || '|'"
                   " || IFNULL(wazifa, '')) FROM corpus WHERE lemma != ''")
    print("\n  woorden onderscheiden op (lemma, kalima_type, wazifa): %s" % format(words, ","))


def huruf(c):
    head("Hoeveel verschillende huruf")
    standalone = one(c, "SELECT COUNT(DISTINCT lemma) FROM corpus"
                        " WHERE kalima_type = 'harf' AND lemma != ''")
    affixed = one(c, "SELECT COUNT(DISTINCT tag) FROM corpus WHERE kalima_type = 'harf'"
                     " AND (lemma IS NULL OR lemma = '')")
    print("  zelfstandige harf-lemma's        %4d" % standalone)
    print("  aangehechte huruf (functietags)  %4d" % affixed)
    print("\n  meest voorkomende zelfstandige huruf:")
    for la, n in c.execute("SELECT lemma_ar, COUNT(*) n FROM corpus WHERE kalima_type = 'harf'"
                           " AND lemma != '' GROUP BY lemma_ar ORDER BY n DESC LIMIT 10"):
        print("    %-8s %6s" % (la, format(n, ",")))


def affix_key(bw, tag):
    base = bw.rstrip("~^@,.").replace("~", "")
    if tag == "DET":
        return "al-"
    if base in ("wa", "w"):
        return "wa- (qasam)" if tag == "P" else "wa-"
    if base == "fa":
        return "fa-"
    if base == "bi":
        return "bi-"
    if base == "la":
        return "la- (tawkid)" if tag == "EMPH" else "la- (jarr)"
    if base in ("li", "lo"):
        return "l- (amr)" if tag == "IMPV" else "li-"
    if base == "ka":
        return "ka-"
    if base == "sa":
        return "sa-"
    if base in (">a", "'a"):
        return "a- (istifham)"
    if tag == "VOC":
        return "ya- (nida)"
    if tag == "EMPH":
        return "-n (tawkid)"
    return bw + ":" + tag


def top_kalimat(c, limit=100):
    head("Top %d kalimat (aandeel van de lopende tekst)" % limit)
    counts = Counter()
    for la, kt, n in c.execute("SELECT lemma_ar, kalima_type, COUNT(*) FROM corpus"
                               " WHERE lemma != '' GROUP BY lemma_ar, kalima_type"):
        counts[(la, kt)] += n
    for bw, tag, n in c.execute("SELECT form_bw, tag, COUNT(*) FROM corpus"
                                " WHERE (lemma IS NULL OR lemma = '')"
                                " AND kalima_type != 'muqattaat' GROUP BY form_bw, tag"):
        counts[(affix_key(bw, tag), "harf")] += n
    total = sum(counts.values())
    cum = 0
    print("  %3s %-16s %-6s %8s %6s %6s" % ("#", "kalima", "soort", "aantal", "%", "cum"))
    for i, ((name, kt), n) in enumerate(counts.most_common(limit), 1):
        cum += n
        print("  %3d %-16s %-6s %8s %5.2f%% %5.1f%%"
              % (i, name, kt, format(n, ","), n / total * 100, cum / total * 100))


def top_roots(c, limit=100):
    head("Top %d roots (aandeel van de root-dragende woorden)" % limit)
    total = one(c, "SELECT COUNT(*) FROM corpus WHERE root_ar != ''")
    cum = 0
    print("  %3s %-8s %7s %8s %6s %6s" % ("#", "root", "lemma's", "aantal", "%", "cum"))
    rows = c.execute("SELECT root_ar, COUNT(DISTINCT lemma), COUNT(*) n FROM corpus"
                     " WHERE root_ar != '' GROUP BY root_ar ORDER BY n DESC LIMIT ?",
                     (limit,))
    for i, (r, lem, n) in enumerate(rows, 1):
        cum += n
        print("  %3d %-8s %7d %8s %5.2f%% %5.1f%%"
              % (i, r, lem, format(n, ","), n / total * 100, cum / total * 100))


def root_coverage(c):
    head("Wat heeft wel en geen root")
    rows = c.execute(
        "SELECT kalima_type,"
        " SUM(CASE WHEN root_ar != '' THEN 1 ELSE 0 END), COUNT(*),"
        " COUNT(DISTINCT CASE WHEN root_ar != '' THEN lemma END),"
        " COUNT(DISTINCT CASE WHEN IFNULL(root_ar, '') = '' AND lemma != ''"
        "   THEN lemma END)"
        " FROM corpus WHERE kalima_type != 'muqattaat' GROUP BY kalima_type").fetchall()
    print("  %-8s %11s %10s %14s %14s"
          % ("soort", "met root", "totaal", "lemma's +root", "lemma's -root"))
    for kt, wr, tot, lr, lnr in rows:
        print("  %-8s %11s %10s %14s %14s"
              % (kt, format(wr or 0, ","), format(tot, ","), format(lr, ","), format(lnr, ",")))
    print("\n  rootloze ism-lemma's naar tag:")
    for tag, n in c.execute("SELECT tag, COUNT(DISTINCT lemma) n FROM corpus"
                            " WHERE IFNULL(root_ar, '') = '' AND lemma != ''"
                            " AND kalima_type = 'ism' GROUP BY tag ORDER BY n DESC"):
        print("    %-6s %4d" % (tag, n))


def ambiguity(c):
    head("Meerduidige woorden (een vorm, meer dan een woord)")
    rows = c.execute("SELECT lemma_ar, COUNT(DISTINCT kalima_type) k,"
                     " COUNT(DISTINCT wazifa) w, COUNT(*) n FROM corpus WHERE lemma != ''"
                     " GROUP BY lemma HAVING k > 1 OR w > 1 ORDER BY n DESC LIMIT 15")
    print("  %-10s %8s %9s %9s" % ("lemma", "klassen", "functies", "aantal"))
    for la, k, w, n in rows:
        print("  %-10s %8d %9d %9s" % (la, k, w, format(n, ",")))
    print("\n  ma uitgesplitst naar klasse en functie:")
    for kt, wz, n in c.execute("SELECT kalima_type, wazifa, COUNT(*) n FROM corpus"
                               " WHERE lemma = 'maA' GROUP BY kalima_type, wazifa"
                               " ORDER BY n DESC"):
        print("    %-6s %-16s %6s" % (kt, wz or "-", format(n, ",")))
    # The written form itself separates the two words: after a preposition the
    # interrogative ma loses its alif (li-ma, bi-ma, cam-ma), the relative and
    # masdariyya keep it (li-ma, bi-ma written with alif). That is a
    # morphological difference, not only a functional one.
    alifless = ("FROM corpus c JOIN corpus p ON p.surah = c.surah AND p.ayah = c.ayah"
                " AND p.word = c.word AND p.segment = c.segment - 1"
                " WHERE c.lemma = 'maA' AND p.tag = 'P'"
                " AND c.form_ar NOT LIKE '%ا%' AND c.form_ar NOT LIKE '%آ%'"
                " AND c.form_ar NOT LIKE '%ٰ%'")
    print("\n  maa na een voorzetsel, geschreven zonder alif:")
    for wz, n in c.execute("SELECT c.wazifa, COUNT(*) n " + alifless
                           + " GROUP BY c.wazifa ORDER BY n DESC"):
        print("    %-16s %4d" % (wz, n))
    for s, a, pf, cf in c.execute("SELECT c.surah, c.ayah, p.form_ar, c.form_ar "
                                  + alifless + " AND c.wazifa != 'istifhamiyyah'"):
        print("    uitzondering: %d:%d %s%s (corpus leest mawsulah; de meeste"
              " grammatici lezen hier istifham)" % (s, a, pf, cf))


# ------------------------------------------------------------------ juz layer

def _lemma_index(c):
    freq, nolem = Counter(), 0
    for lem, n in c.execute("SELECT lemma, COUNT(*) FROM corpus GROUP BY lemma"):
        if lem:
            freq[lem] += n
        else:
            nolem += n
    return freq, nolem


def juz(c):
    head("Rijkdom en transferwaarde per djoez")
    freq, nolem = _lemma_index(c)
    jz = {(s, a): j for s, a, j in c.execute("SELECT surah, ayah, juz FROM verses")}
    roots_by, lems_by, toks = {}, {}, Counter()
    for s, a, r, lem, n in c.execute("SELECT surah, ayah, root_ar, lemma, COUNT(*)"
                                     " FROM corpus GROUP BY surah, ayah, root_ar, lemma"):
        j = jz[(s, a)]
        toks[j] += n
        if r:
            roots_by.setdefault(j, set()).add(r)
        if lem:
            lems_by.setdefault(j, set()).add(lem)
    total = sum(freq.values()) + nolem
    rows = []
    for j in range(1, 31):
        cov = nolem + sum(freq[l] for l in lems_by[j])
        rows.append((j, len(roots_by[j]), len(lems_by[j]), toks[j], cov / total * 100))
    print("  meeste unieke roots:")
    for j, r, l, t, cov in sorted(rows, key=lambda x: -x[1])[:5]:
        print("    djoez %2d: %3d roots, %3d lemma's, %6s kalimat, dekt %.1f%%"
              % (j, r, l, format(t, ","), cov))
    print("  hoogste transferwaarde (welk deel van de hele Quran dekt dit vocabulaire):")
    for j, r, l, t, cov in sorted(rows, key=lambda x: -x[4])[:5]:
        print("    djoez %2d: dekt %.1f%% met %d lemma's (%.4f%% per lemma)"
              % (j, cov, l, cov / l))
    print("  laagste transferwaarde:")
    for j, r, l, t, cov in sorted(rows, key=lambda x: x[4])[:3]:
        print("    djoez %2d: dekt %.1f%% met %d lemma's (%.4f%% per lemma)"
              % (j, cov, l, cov / l))


def juz_amma(c):
    head("Djoez Amma (soera 78-114)")
    w = " WHERE surah >= %d" % JUZ_AMMA
    stats = [
        ("verzen", "SELECT COUNT(*) FROM verses" + w),
        ("geschreven woorden", "SELECT COUNT(*) FROM words" + w),
        ("kalimat", "SELECT COUNT(*) FROM corpus" + w),
        ("unieke roots", "SELECT COUNT(DISTINCT root_ar) FROM corpus" + w + " AND root_ar != ''"),
        ("unieke lemma's", "SELECT COUNT(DISTINCT lemma) FROM corpus" + w + " AND lemma != ''"),
    ]
    for label, sql in stats:
        print("  %-20s %6s" % (label, format(one(c, sql), ",")))
    excl_r = one(c, "SELECT COUNT(*) FROM (SELECT root_ar FROM corpus WHERE root_ar != ''"
                    " GROUP BY root_ar HAVING MIN(surah) >= ?)", (JUZ_AMMA,))
    excl_l = one(c, "SELECT COUNT(*) FROM (SELECT lemma FROM corpus WHERE lemma != ''"
                    " GROUP BY lemma HAVING MIN(surah) >= ?)", (JUZ_AMMA,))
    verbs = one(c, "SELECT COUNT(DISTINCT lemma) FROM corpus" + w + " AND kalima_type = 'fiil'")
    verbs_all = one(c, "SELECT COUNT(DISTINCT lemma) FROM corpus WHERE kalima_type = 'fiil'")
    print("  %-20s %6s" % ("exclusieve roots", format(excl_r, ",")))
    print("  %-20s %6s" % ("exclusieve lemma's", format(excl_l, ",")))
    print("  %-20s %6s van %s" % ("werkwoordlemma's", format(verbs, ","), format(verbs_all, ",")))
    known = {r[0] for r in c.execute("SELECT DISTINCT lemma FROM corpus" + w + " AND lemma != ''")}
    freq, nolem = _lemma_index(c)
    total = sum(freq.values()) + nolem
    cov = nolem + sum(freq[l] for l in known)
    best = {l for _, l in sorted(((n, l) for l, n in freq.items()), reverse=True)[:len(known)]}
    cov2 = nolem + sum(freq[l] for l in best)
    print("\n  het vocabulaire van djoez amma (%d lemma's) dekt %.1f%% van de hele Quran"
          % (len(known), cov / total * 100))
    print("  de %d FREQUENTSTE lemma's zouden %.1f%% dekken" % (len(known), cov2 / total * 100))
    print("  overlap tussen die twee sets: %d lemma's" % len(known & best))


def surah_coverage(c, limit=10):
    head("Welke soera's zijn het toegankelijkst met alleen Djoez Amma")
    known_l = {r[0] for r in c.execute("SELECT DISTINCT lemma FROM corpus"
                                       " WHERE surah >= ? AND lemma != ''", (JUZ_AMMA,))}
    known_r = {r[0] for r in c.execute("SELECT DISTINCT root_ar FROM corpus"
                                       " WHERE surah >= ? AND root_ar != ''", (JUZ_AMMA,))}
    tot, cl, cr = Counter(), Counter(), Counter()
    for s, lem, r, n in c.execute("SELECT surah, lemma, root_ar, COUNT(*) FROM corpus"
                                  " WHERE surah < ? GROUP BY surah, lemma, root_ar",
                                  (JUZ_AMMA,)):
        tot[s] += n
        if not lem or lem in known_l:
            cl[s] += n
        if not lem or not r or r in known_r:
            cr[s] += n
    names = dict(c.execute("SELECT number, name_en FROM surahs"))
    ay = dict(c.execute("SELECT surah, COUNT(*) FROM verses GROUP BY surah"))
    order = sorted(tot, key=lambda s: -cl[s] / tot[s])

    def show(s):
        print("  %3d %-24s %6.1f%% %6.1f%% %7d"
              % (s, names.get(s, ""), cl[s] / tot[s] * 100, cr[s] / tot[s] * 100, ay[s]))

    print("  %-28s %7s %7s %7s" % ("soera", "lemma", "root", "verzen"))
    for s in order[:limit]:
        show(s)
    print("  laagste:")
    for s in order[-3:]:
        show(s)


# ---------------------------------------------------------------- wujuh layer

def syntax(c):
    head("Syntaxis: relaties en weggelaten elementen")
    written = one(c, "SELECT COUNT(*) FROM syntax WHERE is_implicit = 0")
    implicit = one(c, "SELECT COUNT(*) FROM syntax WHERE is_implicit = 1")
    named = one(c, "SELECT COUNT(*) FROM syntax WHERE is_implicit = 1 AND token_ar != '(*)'")
    print("  geschreven tokens   %8s" % format(written, ","))
    print("  geponeerd, benoemd  %8s" % format(named, ","))
    print("  geponeerd, positie  %8s" % format(implicit - named, ","))
    print("  totaal              %8s" % format(written + implicit, ","))
    print("\n  De drie verdedigbare antwoorden op 'hoeveel woorden':")
    print("    %8s geschreven woorden (rasm-eenheden)" % format(one(c, "SELECT COUNT(*) FROM words"), ","))
    print("    %8s kalimat zoals geschreven" % format(
        one(c, "SELECT COUNT(*) FROM corpus WHERE kalima_type != 'muqattaat'"), ","))
    print("    %8s kalimat inclusief de muqaddar-elementen" % format(written + implicit, ","))

    print("\n  meest voorkomende relaties (geschreven tokens):")
    for r, ar, n in c.execute("SELECT rel_label, rel_label_ar, COUNT(*) n FROM syntax"
                              " WHERE is_implicit = 0 AND rel_label IS NOT NULL"
                              " GROUP BY rel_label ORDER BY n DESC LIMIT 8"):
        print("    %-10s %-14s %6s" % (r, ar or "", format(n, ",")))

    print("\n  benoemd geponeerd (damir mustatir en verwanten):")
    for f, ar, n in c.execute("SELECT token_ar, rel_label_ar, COUNT(*) n FROM syntax"
                              " WHERE is_implicit = 1 AND token_ar != '(*)'"
                              " GROUP BY token_ar ORDER BY n DESC LIMIT 6"):
        print("    %-12s %-14s %6s" % (f, ar or "", format(n, ",")))

    print("\n  positie geponeerd zonder het woord in te vullen:")
    for r, ar, n in c.execute("SELECT rel_label, rel_label_ar, COUNT(*) n FROM syntax"
                              " WHERE is_implicit = 1 AND token_ar = '(*)'"
                              " GROUP BY rel_label ORDER BY n DESC LIMIT 8"):
        print("    %-10s %-14s %6s" % (r, ar or "", format(n, ",")))
    print("\n  De khabar mahdhuf is geponeerd maar niet gereconstrueerd: geen enkel")
    print("  geponeerd token is kain, mustaqarr of istaqarra, waar de grammatici")
    print("  onderling over verschillen. Voorbeeld 1:2 al-hamdu li-llah: al-hamd is")
    print("  root, (*) is khabar, en de li- hangt daaraan als mutacalliq.")


def wujuh(c):
    head("Wujuh-laag")
    for w, n, e, r in c.execute("SELECT work, COUNT(*), COUNT(DISTINCT headword),"
                                " COUNT(DISTINCT root_ar) FROM wujuh"
                                " GROUP BY work ORDER BY work"):
        print("  %-11s %6s rijen  %4d entries  %4d roots" % (w, format(n, ","), e, r))
    print()
    for cf, n in c.execute("SELECT confidence, COUNT(*) FROM wujuh"
                           " GROUP BY confidence ORDER BY 2 DESC"):
        print("  confidence %-7s %6s" % (cf, format(n, ",")))
    linked = one(c, "SELECT COUNT(*) FROM wujuh WHERE corpus_id IS NOT NULL")
    canon = one(c, "SELECT COUNT(DISTINCT canonical_id) FROM sense_alignment")
    triple = one(c, "SELECT COUNT(*) FROM (SELECT canonical_id FROM sense_alignment"
                    " GROUP BY canonical_id HAVING COUNT(DISTINCT work) >= 3)")
    print("\n  rijen gekoppeld aan een concreet woord  %6s" % format(linked, ","))
    print("  canonieke senses                       %6s" % format(canon, ","))
    print("  gedragen door 3 of meer werken         %6s" % format(triple, ","))
    roots = {r[0] for r in c.execute("SELECT DISTINCT root_ar FROM wujuh"
                                     " WHERE root_ar IS NOT NULL")}
    occ = dict(c.execute("SELECT root_ar, COUNT(*) FROM corpus"
                         " WHERE root_ar != '' GROUP BY root_ar"))
    tot = sum(occ.get(r, 0) for r in roots)
    lab = one(c, "SELECT COUNT(DISTINCT corpus_id) FROM wujuh WHERE corpus_id IS NOT NULL")
    print("\n  dekking: %d polyseme roots, %s voorkomens, %s gelabeld (%.0f%%)"
          % (len(roots), format(tot, ","), format(lab, ","), lab / tot * 100))


def wujuh_juz_amma(c):
    head("Polyseme lemma's binnen Djoez Amma")
    rows = c.execute(
        "SELECT co.lemma_ar, w.root_ar,"
        " COUNT(DISTINCT IFNULL(sa.canonical_id,"
        "   w.work || ':' || w.headword || ':' || w.sense_nr)) n,"
        " COUNT(DISTINCT w.surah || ':' || w.ayah) v"
        " FROM wujuh w JOIN corpus co ON co.id = w.corpus_id"
        " LEFT JOIN sense_alignment sa ON sa.work = w.work AND sa.headword = w.headword"
        "   AND sa.sense_nr = w.sense_nr AND IFNULL(sa.gloss, '') = IFNULL(w.gloss, '')"
        " WHERE w.surah >= ? AND w.confidence = 'high' AND co.lemma_ar IS NOT NULL"
        " GROUP BY co.lemma_ar HAVING n > 1 ORDER BY n DESC, v DESC", (JUZ_AMMA,)).fetchall()
    labelled = one(c, "SELECT COUNT(DISTINCT co.lemma_ar) FROM wujuh w"
                      " JOIN corpus co ON co.id = w.corpus_id WHERE w.surah >= ?"
                      " AND w.confidence = 'high' AND co.lemma_ar IS NOT NULL", (JUZ_AMMA,))
    print("  %d lemma's met meer dan een wajh, van %d gelabelde lemma's"
          % (len(rows), labelled))
    for la, r, n, v in rows[:12]:
        print("    %-12s root %-6s %2d wujuh over %d verzen" % (la, r or "-", n, v))


def referents(c, lemma="إِنسَٰن"):
    head("Referentiele wujuh: wie is al-insan volgens de werken")
    print("  Ibn al-Jawzi rekent dit type in zijn inleiding zelf tot de pseudo-wujuh:")
    print("  een woord waarvan de betekenis overal een is, maar de referent verschilt.")
    print("\n  %-8s %-11s identificatie" % ("vers", "werk"))
    for s, a, wk, g in c.execute(
            "SELECT w.surah, w.ayah, w.work, w.gloss FROM wujuh w"
            " JOIN corpus co ON co.id = w.corpus_id"
            " WHERE co.lemma_ar = ? AND w.surah >= ? AND w.confidence = 'high'"
            " ORDER BY w.surah, w.ayah, w.work", (lemma, JUZ_AMMA)):
        print("  %-8s %-11s %s" % ("%d:%d" % (s, a), wk, g))


def riwayat(c):
    head("Riwaayaat: Hafs tegenover Warsh")
    print("  Een qiraa-a is de lezing van een qaari-; een riwaaya is de")
    print("  overlevering daarvan door een leerling. Hafs en Warsh horen bij")
    print("  twee verschillende qiraa-aat:\n")
    # fetchall first: the inner query below runs on the same connection and
    # would otherwise reset this cursor after the first row
    for qe, qa, qd in c.execute("SELECT DISTINCT qari_en, qari_ar, qari_died_ah"
                                " FROM riwayat ORDER BY qari_died_ah").fetchall():
        namen = [r[0] for r in c.execute(
            "SELECT riwaya_en FROM riwayat WHERE qari_en = ? ORDER BY riwaya_died_ah",
            (qe,))]
        print("    %-20s %-16s d. %3d AH   %s" % (qe, qa, qd, " en ".join(namen)))

    total = one(c, "SELECT COUNT(*) FROM riwaya_diff")
    print("\n  %s plaatsen waar de twee teksten uiteenlopen, gesorteerd naar"
          % format(total, ","))
    print("  wat het verschil is:\n")
    for kind, n in c.execute("SELECT kind, COUNT(*) n FROM riwaya_diff"
                             " GROUP BY kind ORDER BY n DESC"):
        print("    %-12s %6s   %4.1f%%" % (kind, format(n, ","), n / total * 100))

    print("\n  klassen binnen usul en notatie:")
    for cls, kind, n in c.execute(
            "SELECT class, kind, COUNT(*) n FROM riwaya_diff"
            " WHERE kind IN ('usul','notatie') GROUP BY class"
            " ORDER BY n DESC LIMIT 8"):
        print("    %-24s %-8s %6s" % (cls.split("+")[0], kind, format(n, ",")))

    farsh = one(c, "SELECT COUNT(*) FROM riwaya_diff WHERE kind = 'farsh'")
    ayat = one(c, "SELECT COUNT(DISTINCT surah || ':' || ayah_a) FROM riwaya_diff"
                  " WHERE kind = 'farsh'")
    suwar = one(c, "SELECT COUNT(DISTINCT surah) FROM riwaya_diff WHERE kind = 'farsh'")
    print("\n  farsh al-huroef: %s plaatsen in %s ayaat, %s soerahs"
          % (format(farsh, ","), format(ayat, ","), suwar))
    print("  (usul geldt overal waar de voorwaarde zich voordoet; farsh is per woord)")

    print("\n  soerahs met de meeste farsh-verschillen:")
    for s, nm, n in c.execute(
            "SELECT d.surah, sr.name_ar, COUNT(*) n FROM riwaya_diff d"
            " JOIN surahs sr ON sr.number = d.surah WHERE d.kind = 'farsh'"
            " GROUP BY d.surah ORDER BY n DESC LIMIT 6"):
        print("    %3d %-12s %4s" % (s, nm, n))

    print("\n  een greep uit de farsh-verschillen:")
    for s, a, fa, fb in c.execute(
            "SELECT surah, ayah_a, form_a, form_b FROM riwaya_diff"
            " WHERE kind = 'farsh' AND surah IN (1,2,3,43,57,72)"
            " ORDER BY surah, ayah_a LIMIT 10"):
        print("    %-8s %-18s %s" % ("%d:%d" % (s, a), fa, fb or "(ontbreekt)"))


def dekking(c):
    head("Dekking: wat weet de database wel en niet")
    verses = one(c, "SELECT COUNT(*) FROM verses")
    print("  Elke laag dekt een ander deel van de mushaf. Wat hier niet staat,")
    print("  weet de database niet -- het is geen aanwijzing dat er niets is.\n")
    print("  laag                    verzen    dekking   wat er buiten valt")
    rows = [
        ("word_glosses", "SELECT COUNT(DISTINCT surah || ':' || ayah) FROM word_glosses",
         "niets: elk geschreven woord is geglosseerd"),
        ("syntax (EQTB)", "SELECT COUNT(DISTINCT c.surah || ':' || c.ayah) FROM syntax s"
                          " JOIN corpus c ON c.id = s.corpus_id",
         "niets, maar het is een analyse, geen feit"),
        ("irab (al-Nahhas)", "SELECT COUNT(DISTINCT surah || ':' || ayah) FROM irab",
         "verzen waar hij geen vraag ziet"),
        ("wujuh", "SELECT COUNT(DISTINCT surah || ':' || ayah) FROM wujuh",
         "verzen die geen van de vier werken citeert"),
        ("riwaya_diff (farsh)", "SELECT COUNT(DISTINCT surah || ':' || ayah_a)"
                                " FROM riwaya_diff WHERE kind = 'farsh'",
         "verzen waar Hafs en Warsh gelijk lezen"),
    ]
    for label, sql, gap in rows:
        try:
            n = one(c, sql)
        except Exception:
            print("  %-22s %8s" % (label, "n.v.t."))
            continue
        print("  %-22s %6s   %5.1f%%    %s" % (label, format(n, ","), n / verses * 100, gap))

    print("\n  Binnen het corpus zelf:")
    stems = one(c, "SELECT COUNT(*) FROM corpus WHERE segment_type = 'STEM'")
    noroot = one(c, "SELECT COUNT(*) FROM corpus WHERE segment_type = 'STEM' AND root IS NULL")
    print("    %6s van %s stems zonder root (%.1f%%) -- partikels, voornaamwoorden"
          % (format(noroot, ","), format(stems, ","), noroot / stems * 100))
    print("       en de namen die het corpus onontleedbaar laat")
    print("    %6s unieke roots, %s unieke lemma's"
          % (format(one(c, "SELECT COUNT(DISTINCT root_ar) FROM corpus"
                          " WHERE root_ar IS NOT NULL"), ","),
             format(one(c, "SELECT COUNT(DISTINCT lemma_ar) FROM corpus"
                          " WHERE lemma_ar IS NOT NULL"), ",")))
    wr = one(c, "SELECT COUNT(DISTINCT root_ar) FROM wujuh WHERE root_ar IS NOT NULL")
    print("    %6s van die roots heeft een wujuh-ingang (%.1f%%)"
          % (format(wr, ","), wr / one(c, "SELECT COUNT(DISTINCT root_ar) FROM corpus"
                                          " WHERE root_ar IS NOT NULL") * 100))

    print("\n  Waar helemaal geen laag voor is:")
    for line in ("een vertaling van de Qoeraan (de glossen zijn woord-voor-woord",
                 "  hulp, geen vertaling)",
                 "tafsir",
                 "een sense-label per voorkomen: de wujuh-werken citeren",
                 "  voorbeeldverzen, ze dekken niet af",
                 "de zes andere riwaayaat, en de qiraa-aat buiten Aasim en Naafi3",
                 "de aantallen die per riwaaya verschillen (verzen, ahzaab)"):
        print("    %s%s" % ("" if line.startswith("  ") else "- ", line))


ANALYSES = {
    "basics": basics,
    "kalima": kalima,
    "huruf": huruf,
    "top-kalimat": top_kalimat,
    "top-roots": top_roots,
    "root-coverage": root_coverage,
    "ambiguity": ambiguity,
    "juz": juz,
    "juz-amma": juz_amma,
    "surah-coverage": surah_coverage,
    "syntax": syntax,
    "wujuh": wujuh,
    "wujuh-juz-amma": wujuh_juz_amma,
    "referents": referents,
    "riwayat": riwayat,
    "dekking": dekking,
}


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        print("Analyses:")
        for name in ANALYSES:
            print("  " + name)
        return
    c = sqlite3.connect(DB).cursor()
    names = list(ANALYSES) if args[0] == "--all" else args
    for name in names:
        if name not in ANALYSES:
            sys.exit("onbekende analyse: " + name)
        ANALYSES[name](c)


if __name__ == "__main__":
    main()
