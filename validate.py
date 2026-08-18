#!/usr/bin/env python3
"""Validate the integrity of a built quran.db.

This is not a unit test suite for the pipeline code but a data validation of
its output: a series of assertions about the finished database, each one
reported as passed, failed or skipped, with a non-zero exit code when
anything fails. It is the last step of build.py, so a build that silently
lost half the corpus or annotated the wrong segments does not pass unnoticed.

The checks fall into four groups: the corpus table (row counts and the two
classical annotation layers kalima_type and wazifa), the wujuh table
(referential integrity against corpus), the citation spot check, and the
metadata tables. The citation spot check is the interesting one: it takes
rows whose citation the resolver called 'unique' and verifies independently
that the quoted phrase really occurs in the verse the row points at. Because
the classical works quote from memory-orthography rather than the mushaf
rasm, a quote is verified in tiers — literal containment first, then with the
author's framing word dropped, then on the consonantal skeleton — and both
the literal and the tolerant percentage are reported. That literal percentage
is the single most informative quality figure of the whole wujuh layer.

Checks against tables that a given checkout does not build yet (the metadata
tables) are skipped, not failed.

  python3 validate.py                  validate ./quran.db
  python3 validate.py --db /tmp/x.db   validate a copy
  python3 validate.py --sample 0       spot check every 'unique' citation
"""

import argparse
import random
import sqlite3
import sys
from pathlib import Path

from add_wazifa import WAZIFA
from resolve_citations import clean_quote, normalize, skeleton

HERE = Path(__file__).parent

EXPECTED_SEGMENTS = 128219
EXPECTED_SURAHS = 114
EXPECTED_AYAHS = 6236
EXPECTED_WORDS = 77429

KALIMA_TYPES = {"ism", "fiil", "harf", "muqattaat"}

# tags that name a word class rather than a syntactic function; these keep
# wazifa NULL (see add_wazifa.py)
CONTENT_TAGS = {"N", "PN", "ADJ", "V", "PRON", "DEM", "IMPN", "INL"}

WORKS = {"ibnsallam", "damaghani", "ibnjawzi"}
MATCH_STATUSES = {"unique", "ambiguous", "hint_resolved", "short_hint",
                  "cross_verse", "fuzzy", "prefix", "composite"}

SPOT_SAMPLE = 750          # 'unique' citations drawn for the spot check
SPOT_SEED = 20250817       # fixed, so the same rows are checked every run
SPOT_MIN_VERIFIED = 99.0   # tolerant-tier percentage below which we fail

CHECKS = []


class Failed(Exception):
    """A check found bad data."""


class Skipped(Exception):
    """A check cannot run here (a table it needs does not exist yet)."""


def check(name):
    def register(fn):
        CHECKS.append((name, fn))
        return fn
    return register


def expect(actual, wanted, label):
    if actual != wanted:
        raise Failed(f"{label}: {actual:,} (expected {wanted:,})")


def expect_none(cur, label, sql, params=()):
    """Assert that a diagnostic query returns no rows; report the first few."""
    rows = cur.execute(sql, params).fetchall()
    if rows:
        shown = "; ".join(str(tuple(r)) for r in rows[:3])
        more = f" (+{len(rows) - 3} more)" if len(rows) > 3 else ""
        raise Failed(f"{label}: {len(rows):,} rows, e.g. {shown}{more}")


def placeholders(values):
    return ",".join("?" * len(values))


def require_tables(cur, *names):
    present = {r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    missing = [n for n in names if n not in present]
    if missing:
        raise Skipped("table not built yet: " + ", ".join(missing))


@check("corpus totals")
def corpus_totals(cur, args):
    expect(cur.execute("SELECT COUNT(*) FROM corpus").fetchone()[0],
           EXPECTED_SEGMENTS, "segments")
    expect(cur.execute("SELECT COUNT(DISTINCT surah) FROM corpus").fetchone()[0],
           EXPECTED_SURAHS, "surahs")
    expect(cur.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT surah, ayah FROM corpus)"
    ).fetchone()[0], EXPECTED_AYAHS, "ayahs")
    expect(cur.execute(
        "SELECT COUNT(*) FROM (SELECT DISTINCT surah, ayah, word FROM corpus)"
    ).fetchone()[0], EXPECTED_WORDS, "words")
    return (f"{EXPECTED_SEGMENTS:,} segments, {EXPECTED_SURAHS} surahs, "
            f"{EXPECTED_AYAHS:,} ayahs, {EXPECTED_WORDS:,} words")


@check("kalima_type complete and known")
def kalima_type_complete(cur, args):
    expect_none(cur, "segments without kalima_type",
                "SELECT id, tag FROM corpus WHERE kalima_type IS NULL "
                "OR kalima_type=''")
    expect_none(cur, "unknown kalima_type values",
                "SELECT kalima_type, COUNT(*) FROM corpus WHERE kalima_type "
                f"NOT IN ({placeholders(KALIMA_TYPES)}) GROUP BY 1",
                tuple(KALIMA_TYPES))
    counts = dict(cur.execute(
        "SELECT kalima_type, COUNT(*) FROM corpus GROUP BY 1"))
    return ", ".join(f"{k} {counts.get(k, 0):,}" for k in sorted(counts))


@check("kalima_type roots")
def kalima_type_roots(cur, args):
    expect_none(cur, "fiil without root",
                "SELECT id, form_bw, lemma FROM corpus WHERE kalima_type='fiil'"
                " AND (root IS NULL OR root='')")
    expect_none(cur, "harf with a root",
                "SELECT id, form_bw, root FROM corpus WHERE kalima_type='harf'"
                " AND root IS NOT NULL AND root!=''")
    verbs = cur.execute(
        "SELECT COUNT(*) FROM corpus WHERE kalima_type='fiil'").fetchone()[0]
    return f"all {verbs:,} afaal carry a root, no harf does"


@check("pronoun lemmas")
def pronoun_lemmas(cur, args):
    expect_none(cur, "PRON segment without lemma",
                "SELECT id, form_bw, tag FROM corpus WHERE tag='PRON' "
                "AND (lemma IS NULL OR lemma='')")
    n = cur.execute("SELECT COUNT(*) FROM corpus WHERE tag='PRON'").fetchone()[0]
    return f"all {n:,} damair have a lemma"


@check("wazifa values")
def wazifa_values(cur, args):
    known = set(WAZIFA.values())
    expect_none(cur, "unknown wazifa values",
                "SELECT wazifa, COUNT(*) FROM corpus WHERE wazifa IS NOT NULL "
                f"AND wazifa NOT IN ({placeholders(known)}) GROUP BY 1",
                tuple(known))
    # every stored wazifa must be the one the tag maps to: catches a partially
    # applied or stale migration, which the value check alone would not
    drift = [(tag, wazifa, n) for tag, wazifa, n in cur.execute(
        "SELECT tag, wazifa, COUNT(*) FROM corpus WHERE wazifa IS NOT NULL "
        "GROUP BY 1, 2") if WAZIFA.get(tag) != wazifa]
    if drift:
        raise Failed("wazifa does not match the tag mapping: " +
                     "; ".join(f"{t}->{w} ({n:,})" for t, w, n in drift))
    n = cur.execute(
        "SELECT COUNT(*) FROM corpus WHERE wazifa IS NOT NULL").fetchone()[0]
    return f"{n:,} labelled segments, {len(known)} distinct wazaif"


@check("wazifa on content words")
def wazifa_content_words(cur, args):
    expect_none(cur, "content word with a wazifa",
                "SELECT tag, wazifa, COUNT(*) FROM corpus WHERE wazifa IS NOT "
                f"NULL AND tag IN ({placeholders(CONTENT_TAGS)}) GROUP BY 1, 2",
                tuple(CONTENT_TAGS))
    return "N, PN, ADJ, V, PRON, DEM, IMPN, INL all keep NULL"


@check("wazifa on function words")
def wazifa_function_words(cur, args):
    expect_none(cur, "function tag without a wazifa",
                "SELECT tag, COUNT(*) FROM corpus WHERE wazifa IS NULL AND tag "
                f"IN ({placeholders(WAZIFA)}) GROUP BY 1", tuple(WAZIFA))
    expect_none(cur, "tag is neither a content tag nor mapped to a wazifa",
                "SELECT tag, COUNT(*) FROM corpus WHERE tag NOT IN "
                f"({placeholders(WAZIFA)}) AND tag NOT IN "
                f"({placeholders(CONTENT_TAGS)}) GROUP BY 1",
                tuple(WAZIFA) + tuple(CONTENT_TAGS))
    return f"every segment with one of the {len(WAZIFA)} function tags is labelled"


@check("wujuh verse references")
def wujuh_verse_refs(cur, args):
    expect_none(cur, "wujuh row pointing at a verse that does not exist",
                "SELECT w.id, w.work, w.surah, w.ayah FROM wujuh w WHERE NOT "
                "EXISTS (SELECT 1 FROM corpus c WHERE c.surah=w.surah "
                "AND c.ayah=w.ayah)")
    n, v = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT surah||':'||ayah) FROM wujuh").fetchone()
    return f"{n:,} rows referencing {v:,} distinct verses"


@check("wujuh column values")
def wujuh_column_values(cur, args):
    expect_none(cur, "unknown work",
                f"SELECT work, COUNT(*) FROM wujuh WHERE work NOT IN "
                f"({placeholders(WORKS)}) OR work IS NULL GROUP BY 1",
                tuple(WORKS))
    expect_none(cur, "sense_nr below 1 or missing",
                "SELECT id, work, headword, sense_nr FROM wujuh "
                "WHERE sense_nr IS NULL OR sense_nr < 1")
    expect_none(cur, "unknown match_status",
                "SELECT match_status, COUNT(*) FROM wujuh WHERE match_status "
                f"NOT IN ({placeholders(MATCH_STATUSES)}) OR match_status IS "
                "NULL GROUP BY 1", tuple(MATCH_STATUSES))
    expect_none(cur, "row without a quote",
                "SELECT id, work, headword FROM wujuh WHERE quote IS NULL "
                "OR quote=''")
    per_work = dict(cur.execute("SELECT work, COUNT(*) FROM wujuh GROUP BY 1"))
    return ", ".join(f"{w} {per_work.get(w, 0):,}" for w in sorted(per_work))


@check("wujuh roots exist in corpus")
def wujuh_roots(cur, args):
    expect_none(cur, "root_ar absent from corpus.root_ar",
                "SELECT DISTINCT w.root_ar FROM wujuh w WHERE w.root_ar IS NOT "
                "NULL AND w.root_ar!='' AND NOT EXISTS (SELECT 1 FROM corpus c "
                "WHERE c.root_ar=w.root_ar)")
    total, rooted, distinct = cur.execute(
        "SELECT COUNT(*), SUM(root_ar IS NOT NULL AND root_ar!=''), "
        "COUNT(DISTINCT root_ar) FROM wujuh").fetchone()
    return (f"{rooted:,}/{total:,} rows carry a root, {distinct:,} distinct, "
            "all attested in the corpus")


def verse_texts(cur):
    """Rebuild every verse from the segment-level corpus, normalized the same
    way resolve_citations.py normalized it when matching the citations."""
    cur.execute("SELECT surah, ayah, word, form_ar FROM corpus "
                "ORDER BY surah, ayah, word, segment")
    words = {}
    for s, a, w, form in cur.fetchall():
        words.setdefault((s, a), {}).setdefault(w, []).append(form)
    return {k: normalize(" ".join("".join(v[w]) for w in sorted(v)))
            for k, v in words.items()}


def trimmed_hit(quote, text):
    """The works fuse framing words onto their quotes; the resolver therefore
    also accepts a quote minus its first and/or last word."""
    w = quote.split()
    return any(len(t) >= 3 and " ".join(t) in text
               for t in (w[1:], w[:-1], w[1:-1]))


@check("citation spot check ('unique' rows)")
def citation_spot_check(cur, args):
    verses = verse_texts(cur)
    skeletons = {k: skeleton(v) for k, v in verses.items()}
    rows = cur.execute("SELECT DISTINCT quote, surah, ayah FROM wujuh "
                       "WHERE match_status='unique'").fetchall()
    if not rows:
        raise Failed("no rows with match_status 'unique' to check")
    if args.sample and args.sample < len(rows):
        rows = random.Random(SPOT_SEED).sample(rows, args.sample)

    literal = trimmed = skeletal = 0
    failures = []
    for quote, s, a in rows:
        text, skel = verses[(s, a)], skeletons[(s, a)]
        q = clean_quote(normalize(quote))
        qs = skeleton(q)
        if q and q in text:
            literal += 1
        elif q and trimmed_hit(q, text):
            trimmed += 1
        elif qs and (qs in skel or trimmed_hit(qs, skel)
                     or qs.replace(" ", "") in skel.replace(" ", "")):
            skeletal += 1
        else:
            failures.append((quote, s, a))

    n = len(rows)
    verified = n - len(failures)
    pct_literal = 100.0 * literal / n
    pct_verified = 100.0 * verified / n
    detail = (f"{n:,} sampled: {pct_literal:.1f}% literal, "
              f"{100.0 * (literal + trimmed) / n:.1f}% after trimming framing "
              f"words, {pct_verified:.1f}% verified on the consonantal "
              f"skeleton ({len(failures)} unverifiable)")
    if pct_verified < SPOT_MIN_VERIFIED:
        shown = "; ".join(f"{q[:40]} -> {s}:{a}" for q, s, a in failures[:3])
        raise Failed(f"{detail}; below the {SPOT_MIN_VERIFIED}% floor, "
                     f"e.g. {shown}")
    return detail


@check("metadata: surahs")
def metadata_surahs(cur, args):
    require_tables(cur, "surahs")
    expect(cur.execute("SELECT COUNT(*) FROM surahs").fetchone()[0],
           EXPECTED_SURAHS, "surah rows")
    expect(cur.execute("SELECT SUM(ayah_count) FROM surahs").fetchone()[0],
           EXPECTED_AYAHS, "sum of ayah_count")
    expect_none(cur, "ayah_count disagrees with the corpus",
                "SELECT s.number, s.ayah_count, COUNT(DISTINCT c.ayah) FROM "
                "surahs s JOIN corpus c ON c.surah=s.number GROUP BY 1 "
                "HAVING s.ayah_count != COUNT(DISTINCT c.ayah)")
    return f"{EXPECTED_SURAHS} surahs summing to {EXPECTED_AYAHS:,} ayahs"


@check("metadata: juz boundaries")
def metadata_juz(cur, args):
    require_tables(cur, "juz_boundaries")
    expect(cur.execute("SELECT COUNT(*) FROM juz_boundaries").fetchone()[0],
           30, "juz rows")
    first = cur.execute("SELECT start_surah, start_ayah FROM juz_boundaries "
                        "WHERE juz=1").fetchone()
    last = cur.execute("SELECT end_surah, end_ayah FROM juz_boundaries "
                       "WHERE juz=30").fetchone()
    if first != (1, 1) or last != (114, 6):
        raise Failed(f"juz 1 starts at {first} and juz 30 ends at {last} "
                     "(expected (1, 1) and (114, 6))")
    return "30 ajza', from 1:1 through 114:6"


@check("metadata: verses")
def metadata_verses(cur, args):
    require_tables(cur, "verses")
    expect(cur.execute("SELECT COUNT(*) FROM verses").fetchone()[0],
           EXPECTED_AYAHS, "verse rows")
    expect_none(cur, "corpus verse missing from verses",
                "SELECT DISTINCT c.surah, c.ayah FROM corpus c WHERE NOT EXISTS"
                " (SELECT 1 FROM verses v WHERE v.surah=c.surah "
                "AND v.ayah=c.ayah)")
    expect_none(cur, "verse row without text",
                "SELECT surah, ayah FROM verses WHERE text_ar IS NULL "
                "OR text_ar=''")
    return f"all {EXPECTED_AYAHS:,} corpus verses covered"


def main():
    ap = argparse.ArgumentParser(
        description="Validate the integrity of a built quran.db.")
    ap.add_argument("--db", default=str(HERE / "quran.db"), metavar="PATH",
                    help="database to validate (default: ./quran.db)")
    ap.add_argument("--sample", type=int, default=SPOT_SAMPLE, metavar="N",
                    help=f"citations drawn for the spot check "
                         f"(default {SPOT_SAMPLE}, 0 = all)")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        sys.exit(f"{db} does not exist; build it first with build.py")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()

    passed, failed, skipped = 0, 0, 0
    for name, fn in CHECKS:
        try:
            detail = fn(cur, args)
            passed += 1
            print(f"PASS  {name}: {detail}")
        except Skipped as exc:
            skipped += 1
            print(f"SKIP  {name}: {exc}")
        except Failed as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")
        except sqlite3.Error as exc:
            failed += 1
            print(f"FAIL  {name}: database error: {exc}")
    con.close()

    print(f"\n{len(CHECKS)} checks on {db.name}: {passed} passed, "
          f"{failed} failed, {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
