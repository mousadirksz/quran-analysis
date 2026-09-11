#!/usr/bin/env python3
"""Validate the integrity of a built quran.db.

This is not a unit test suite for the pipeline code but a data validation of
its output: a series of assertions about the finished database, each one
reported as passed, warned, failed or skipped, with a non-zero exit code when
anything fails. It is the last step of build.py, so a build that silently
lost half the corpus, annotated the wrong segments, or never reached the
database at all does not pass unnoticed.

The checks fall into five groups: the corpus table (row counts and the two
classical annotation layers kalima_type and wazifa), the wujuh table
(referential integrity against corpus), freshness (does what is in the
database still follow from the sources on disk), shape (do the rows of a
match_status pile up in ways that betray a broken matcher), and the metadata
tables.

Freshness is the group that exists because of a real miss: parse_damaghani.py
was improved from 387 to 497 entries, but resolve_citations.py was never
re-run, so the database kept answering from the old parse and every other
check still passed. Two checks now close that hole - the parsed JSONs must
agree entry-for-entry and quote-for-quote with resolved_citations.json, and
the wujuh table must contain exactly the (citation, verse) rows that
resolved_citations.json currently implies.

Shape covers the other kind of silent damage: a matcher that is wrong rather
than absent. When 44% of one status' rows land on a single verse, or a status
carries four rows per citation, the rows exist and reference real verses but
mean nothing. Those two figures are reported for every status and warn when
they cross a threshold.

The citation spot check verifies independently that the quoted phrase really
occurs in the verse the row points at, per match_status. Because the classical
works quote from memory-orthography rather than the mushaf rasm, a quote is
verified in cumulative tiers - literal containment, then with the author's
framing word dropped, then on the consonantal skeleton, and finally on bare
word overlap - and all of them are reported side by side, because quoting one
alone misleads in both directions. The literal figure understates badly
(memory-orthography is not a defect: on 'unique' rows it is around 60% where
the skeleton tier reaches 100%), and the tolerant figures overstate: they say
the words are in the verse, not that this is the verse the author meant. The
last tier is the criterion the fuzzy matcher itself used, so for that status
it shows the matcher agreeing with itself and nothing more. A short quote can
be verifiable in a dozen wrong verses, which is why the clustering and
rows-per-citation checks sit next to it rather than under it. Statuses whose
quote runs over a verse boundary (cross_verse, composite) are checked against
their verses together, since no single verse holds the whole quote.

Sets that another script owns (which match_status values may appear, which
works exist) are imported from that script instead of repeated here, so a new
status cannot fail this validator for existing - which is how 'edition_jk',
a legitimate value, used to be reported as unknown.

Checks against tables that a given checkout does not build yet (the metadata
tables, sense_alignment) are skipped, not failed. Warnings are printed and
counted but do not by themselves make the run fail.

  python3 validate.py                  validate ./quran.db
  python3 validate.py --db /tmp/x.db   validate a copy
  python3 validate.py --sample 0       spot check every citation
"""

import argparse
import csv
import difflib
import json
import random
import re
import unicodedata
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from add_metadata import repair_markers
from compare_riwayat import IDGHAAM_KABIR, has_imala
from add_wazifa import WAZIFA
# BEST_CONFIDENCE keys are exactly the statuses add_wujuh.py turns into rows,
# and SPAN_STATUSES those whose several verses are one quote instead of
# alternatives; WORKS is the resolver's list of works with their parsed JSON.
from add_wujuh import BEST_CONFIDENCE, SPAN_STATUSES
from resolve_citations import WORKS as PARSED_WORKS
from resolve_citations import clean_quote, normalize, skeleton

HERE = Path(__file__).parent
SOURCES = HERE / "sources"
RESOLVED = SOURCES / "resolved_citations.json"

EXPECTED_SEGMENTS = 128219
EXPECTED_SURAHS = 114
EXPECTED_AYAHS = 6236
# The treebank's head pointers are not quite a forest; see the 'syntax head
# structure' check for what these two count and why they are not repaired.
EXPECTED_HEAD_CYCLES = 135
EXPECTED_ROOTLESS = 19
EXPECTED_WORDS = 77429

KALIMA_TYPES = {"ism", "fiil", "harf", "muqattaat"}

# tags that name a word class rather than a syntactic function; these keep
# wazifa NULL (see add_wazifa.py)
CONTENT_TAGS = {"N", "PN", "ADJ", "V", "PRON", "DEM", "IMPN", "INL"}

# derived, not repeated: the works the resolver knows and their parsed JSON,
# and the match_status values add_wujuh.py writes. Repeating either list here
# is how they drift apart - MATCH_STATUSES once lacked 'edition_jk' and failed
# a database that was right.
PARSED_JSON = dict(PARSED_WORKS)
WORKS = set(PARSED_JSON)
MATCH_STATUSES = set(BEST_CONFIDENCE)

SPOT_SAMPLE = 750          # citations drawn per match_status for the spot check
SPOT_SEED = 20250817       # fixed, so the same rows are checked every run
SPOT_MIN_VERIFIED = 99.0   # skeleton-tier percentage of 'unique' below
                           # which we fail
SPOT_WARN_VERIFIED = 90.0  # weakest-tier percentage of any status, below
                           # which we warn
PARTIAL_SHARE = 0.60       # words of the quote that must recur for the
                           # weakest tier

# how a status found its verse, derived from the ceiling add_wujuh.py gives it:
# a quote matched word for word can reach the strict tiers, an approximated or
# merely listed one cannot, so a low literal percentage there is expected
KIND = {"high": "", "medium": "  approximated", "low": "  candidate list"}
KIND = {status: KIND[best] for status, best in BEST_CONFIDENCE.items()}

# the tiers of verify_tier(), strictest first, and how the report names them
SPOT_TIER_LABELS = (("literal", "literal"), ("trimmed", "+framing dropped"),
                    ("skeleton", "+skeleton"), ("overlap", "+word overlap"))
SPOT_TIERS = tuple(tier for tier, _label in SPOT_TIER_LABELS)

# One verse taking a large share of a status' rows means the matcher latched
# onto something that is not the quote (an editorial 'wa-fiha' matched 44% of
# one status onto 17:69). Healthy statuses stay under 7%.
CLUSTER_SHARE = 15.0       # percent of a status' rows on one verse
CLUSTER_MIN_ROWS = 20      # ... in a status of at least this many rows
CLUSTER_MIN_HITS = 5       # ... and at least this many rows on that verse

# Rows per citation: a status listing several verses per quote is listing
# candidates, not attestations. Span statuses are exempt (their verses are the
# consecutive parts of one quote).
INFLATION_WARN = 2.0
CAP_HINT_WIDTH = 5         # citations this wide sharing one width smell
                           # of truncation

# A checkout writes files in whatever order it likes, so a parse can land a
# fraction of a second after the resolution built from it without anything
# being stale. The content comparison above catches real staleness; the
# timestamps only need to catch a re-run, which is never this close.
MTIME_SLACK = 2.0          # seconds

CHECKS = []


class Failed(Exception):
    """A check found bad data."""


class Warned(Exception):
    """A check found a pattern that is suspect rather than provably wrong."""


class Skipped(Exception):
    """A check cannot run here (a table or source it needs does not exist)."""


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
        "SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    missing = [n for n in names if n not in present]
    if missing:
        raise Skipped("table not built yet: " + ", ".join(missing))


def load_json(path):
    if not path.exists():
        raise Skipped(f"sources/{path.name} not present")
    return json.loads(path.read_text(encoding="utf-8"))


def count_quotes(entries):
    return sum(len(s["quotes"]) for e in entries for s in e["senses"])


def stamp(path):
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


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
    return (", ".join(f"{w} {per_work.get(w, 0):,}" for w in sorted(per_work))
            + f"; {len(MATCH_STATUSES)} known match_status values "
              "(from add_wujuh.BEST_CONFIDENCE)")


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


@check("resolved citations follow the current parse")
def resolved_citations_current(cur, args):
    """The parsers write sources/*_wujuh.json, resolve_citations.py turns them
    into resolved_citations.json, and only that file reaches the database. An
    improved parser whose output never got resolved is therefore invisible in
    every other check - so compare the two directly, entry for entry and quote
    for quote (the resolver keeps all of both), and complain when a parse is
    newer than the resolution built from it."""
    resolved = load_json(RESOLVED)
    stale, counted = [], []
    for work in sorted(PARSED_JSON):
        path = SOURCES / PARSED_JSON[work]
        if not path.exists():
            continue                      # parser not in this checkout
        parsed = json.loads(path.read_text(encoding="utf-8"))
        n_e, n_q = len(parsed), count_quotes(parsed)
        entries = resolved.get(work)
        if entries is None:
            stale.append(f"{work}: {n_e:,} parsed entries, absent from "
                         f"{RESOLVED.name}")
            continue
        r_e, r_q = len(entries), count_quotes(entries)
        if (n_e, n_q) != (r_e, r_q):
            stale.append(f"{work}: parsed {n_e:,} entries/{n_q:,} quotes but "
                         f"resolved {r_e:,}/{r_q:,}")
        elif path.stat().st_mtime > RESOLVED.stat().st_mtime + MTIME_SLACK:
            stale.append(f"{work}: {path.name} ({stamp(path)}) is newer than "
                         f"{RESOLVED.name} ({stamp(RESOLVED)})")
        counted.append(f"{work} {r_e:,}/{r_q:,}")
    orphan = sorted(set(resolved) - set(PARSED_JSON))
    if orphan:
        stale.append("resolved work with no parsed source: " + ", ".join(orphan))
    if stale:
        raise Failed("; ".join(stale) +
                     " -- re-run resolve_citations.py and substantiate_jk.py")
    if not counted:
        raise Skipped("no parsed wujuh JSONs present")
    return ("entries/quotes match the parse for " + ", ".join(counted) +
            f"; {RESOLVED.name} written {stamp(RESOLVED)}")


@check("wujuh table follows resolved_citations.json")
def wujuh_matches_resolved(cur, args):
    """add_wujuh.py writes one row per (citation, verse) for every quote whose
    status it recognises, and drops nothing. That makes the row count per
    status a closed prediction from the JSON: a mismatch means the table was
    built from a different file than the one on disk now. (add_wujuh.py drops
    a reference whose verse is not in the corpus, but the resolver matched
    against that same corpus, so there are none to drop.)"""
    resolved = load_json(RESOLVED)
    want, want_work = Counter(), Counter()
    for work, entries in resolved.items():
        for entry in entries:
            for sense in entry["senses"]:
                for q in sense["quotes"]:
                    if q["status"] in MATCH_STATUSES:
                        want[q["status"]] += len(q["refs"])
                        want_work[work] += len(q["refs"])
    have = Counter(dict(cur.execute(
        "SELECT match_status, COUNT(*) FROM wujuh GROUP BY 1")))
    have_work = Counter(dict(cur.execute(
        "SELECT work, COUNT(*) FROM wujuh GROUP BY 1")))
    diff = [f"{k}: json {want[k]:,} vs table {have[k]:,}"
            for k in sorted(set(want) | set(have)) if want[k] != have[k]]
    diff += [f"{k}: json {want_work[k]:,} vs table {have_work[k]:,}"
             for k in sorted(set(want_work) | set(have_work))
             if want_work[k] != have_work[k]]
    if diff:
        raise Failed("wujuh does not match the current resolved_citations.json: "
                     + "; ".join(diff) + " -- re-run add_wujuh.py")
    return (f"{sum(want.values()):,} rows, exactly the (citation, verse) pairs "
            f"{RESOLVED.name} implies")


@check("wujuh verse clustering per match_status")
def wujuh_verse_clusters(cur, args):
    """A matcher that has gone wrong does not produce fewer rows, it produces
    rows that pile onto one verse: an editorial 'wa-fiha' once matched 44% of
    one status' rows onto 17:69. Healthy statuses stay under 7%."""
    per = defaultdict(Counter)
    for status, ref, n in cur.execute(
            "SELECT match_status, surah||':'||ayah, COUNT(*) FROM wujuh "
            "GROUP BY 1, 2"):
        per[status][ref] = n
    if not per:
        raise Failed("wujuh table is empty")
    lines, hot = [], []
    for status in sorted(per):
        total = sum(per[status].values())
        ref, n = per[status].most_common(1)[0]
        share = 100.0 * n / total
        lines.append(f"{status:<14} {total:>6,} rows   top verse {ref} "
                     f"{n} ({share:.1f}%)")
        if (share > CLUSTER_SHARE and total >= CLUSTER_MIN_ROWS
                and n >= CLUSTER_MIN_HITS):
            hot.append(f"{status}: {n}/{total} rows ({share:.1f}%) on {ref}")
    body = "\n".join(lines)
    if hot:
        raise Warned("; ".join(hot) + f" (over {CLUSTER_SHARE:.0f}% on one "
                     "verse: check what those rows matched on)\n" + body)
    return (f"no status puts over {CLUSTER_SHARE:.0f}% of its rows on one "
            f"verse\n" + body)


@check("wujuh rows per citation")
def wujuh_rows_per_citation(cur, args):
    """How many verses a status hangs on one citation. One is an attestation;
    four means the rows are candidates the author never chose between, and
    counting them as attestations inflates every figure downstream. Span
    statuses are exempt: their verses are the parts of one quote."""
    widths = defaultdict(list)
    for status, n in cur.execute(
            "SELECT match_status, COUNT(*) FROM wujuh "
            "GROUP BY match_status, work, headword, sense_nr, quote"):
        widths[status].append(n)
    if not widths:
        raise Failed("wujuh table is empty")
    lines, loud = [], []
    capped = False
    for status in sorted(widths):
        per_citation = widths[status]
        n_rows, n_cites = sum(per_citation), len(per_citation)
        ratio = n_rows / n_cites
        widest = max(per_citation)
        at_widest = per_citation.count(widest)
        capped = capped or (at_widest > 1 and widest >= CAP_HINT_WIDTH
                            and status not in SPAN_STATUSES)
        span = " (span status)" if status in SPAN_STATUSES else ""
        lines.append(f"{status:<14} {n_rows:>6,} rows / {n_cites:>5,} citations"
                     f" = {ratio:.2f}, widest {widest} ({at_widest}x){span}")
        if ratio > INFLATION_WARN and status not in SPAN_STATUSES:
            loud.append(f"{status}: {n_rows:,} rows for {n_cites:,} citations "
                        f"({ratio:.2f} verses each)")
    body = "\n".join(lines)
    body += "\nwidest = verses on one citation, (Nx) = citations at that width"
    if capped:
        # resolve_citations.py truncates long candidate lists, so several wide
        # citations stopping at the same number is a ceiling, not a
        # measurement: those citations may have had more candidates
        body += ("; several citations stopping at the same wide number is the "
                 "resolver's truncation, so their breadth is a lower bound")
    if loud:
        raise Warned("; ".join(loud) + " -- these are candidate lists, not "
                     "attestations\n" + body)
    return f"no status exceeds {INFLATION_WARN:.1f} verses per citation\n" + body


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


def word_overlap(qskel, verse_words):
    """Share of the quote's skeleton words that recur in the verse, allowing
    one to sit inside the other or to differ by a letter. This is roughly the
    criterion by which the fuzzy tier matched in the first place, so for that
    status it measures consistency rather than correctness."""
    words = [w for w in qskel.split() if len(w) >= 2]
    if not words:
        return 0.0
    hit = sum(any(w == v or (len(w) >= 4 and w in v) or (len(v) >= 4 and v in w)
                  or difflib.SequenceMatcher(None, w, v).ratio() >= 0.8
                  for v in verse_words) for w in words)
    return hit / len(words)


def verify_tier(quote, keys, verses, skeletons):
    """The strictest tier at which this quote is demonstrably in these verses:

      literal    the normalized quote occurs verbatim
      trimmed    it does once the author's framing word is dropped
      skeleton   only its consonantal skeleton occurs
      overlap    neither, but most of its words are there (the weakest tier:
                 it is what fuzzy and prefix matched on, so it confirms the
                 matcher agrees with itself, not that the verse is right)

    or None when even that fails. `keys` is a whole citation: for cross_verse
    and composite the quote runs over the verses together, for every other
    status it is one verse. 'missing' means the row points at a verse the
    corpus does not have - impossible unless the referential check failed too,
    but indexing blindly would crash the run over one bad row."""
    if any(k not in verses for k in keys):
        return "missing"
    text = " ".join(verses[k] for k in keys)
    skel = " ".join(skeletons[k] for k in keys)
    q = clean_quote(normalize(quote))
    qs = skeleton(q)
    if q and q in text:
        return "literal"
    if q and trimmed_hit(q, text):
        return "trimmed"
    if qs and (qs in skel or trimmed_hit(qs, skel)
               or qs.replace(" ", "") in skel.replace(" ", "")):
        return "skeleton"
    if qs and word_overlap(qs, set(skel.split())) >= PARTIAL_SHARE:
        return "overlap"
    return None


def spot_units(cur):
    """The units the spot check measures, per match_status: one (quote, verse)
    pair, except for the span statuses, where a citation's verses are one
    unit because the quote is spread over them."""
    rows = cur.execute(
        "SELECT DISTINCT match_status, work, headword, sense_nr, quote, "
        "surah, ayah FROM wujuh").fetchall()
    citations = defaultdict(list)
    for status, work, head, nr, quote, s, a in rows:
        citations[(status, work, head, nr, quote)].append((s, a))
    units = defaultdict(set)
    for (status, _work, _head, _nr, quote), refs in citations.items():
        if status in SPAN_STATUSES:
            units[status].add((quote, tuple(sorted(refs))))
        else:
            units[status].update((quote, (ref,)) for ref in refs)
    return units


@check("citation spot check (per match_status)")
def citation_spot_check(cur, args):
    verses = verse_texts(cur)
    skeletons = {k: skeleton(v) for k, v in verses.items()}
    units = spot_units(cur)
    if not units:
        raise Failed("wujuh table has no rows to check")

    lines, failures, verdict = [], {}, {}
    for status in sorted(units):
        rows = sorted(units[status])
        # seeded per status, so adding a status does not reshuffle the others
        if args.sample and args.sample < len(rows):
            rows = random.Random(f"{SPOT_SEED}:{status}").sample(rows, args.sample)
        tiers, bad = Counter(), []
        for quote, keys in rows:
            tier = verify_tier(quote, keys, verses, skeletons)
            tiers[tier] += 1
            if tier in (None, "missing"):
                bad.append((quote, keys))
        n = len(rows)
        cum, pct = 0, {}
        for tier in SPOT_TIERS:
            cum += tiers[tier]
            pct[tier] = 100.0 * cum / n
        verdict[status] = pct
        failures[status] = bad
        gone = tiers["missing"]
        note = "" if not gone else f", {gone} not in corpus"
        lines.append(
            f"{status:<14} {n:>5,} checked   " +
            "   ".join(f"{label} {pct[tier]:5.1f}%"
                       for tier, label in SPOT_TIER_LABELS) +
            f"   ({len(bad)} unverifiable{note}){KIND.get(status, '')}")

    body = ("cumulative tiers; 'verifiable' means the words are in that verse, "
            "not that it is the verse the author meant\n"
            "the last tier is the weakest: it accepts a quote whose words "
            f"merely recur in the verse for >={PARTIAL_SHARE:.0%}\n"
            "an approximated status cannot reach the strict tiers by "
            "construction - its quote deviates from the mushaf, which is why "
            "it was matched that way\n" +
            "\n".join(lines))
    hard = verdict.get("unique", {}).get("skeleton")
    if hard is not None and hard < SPOT_MIN_VERIFIED:
        shown = "; ".join(f"{q[:40]} -> {'+'.join(f'{s}:{a}' for s, a in k)}"
                          for q, k in failures["unique"][:3])
        raise Failed(f"'unique' verifiable on the skeleton for only {hard:.1f}%, "
                     f"below the {SPOT_MIN_VERIFIED}% floor, e.g. {shown}\n{body}")
    weak = [f"{st} {p['overlap']:.1f}%" for st, p in sorted(verdict.items())
            if p["overlap"] < SPOT_WARN_VERIFIED]
    if weak:
        raise Warned("verifiable even on the weakest tier for under "
                     f"{SPOT_WARN_VERIFIED:.0f}% of rows: " + ", ".join(weak)
                     + "\n" + body)
    return body


@check("sense_alignment references")
def sense_alignment_refs(cur, args):
    require_tables(cur, "sense_alignment", "wujuh")
    expect_none(cur, "aligned sense with no such sense in wujuh",
                "SELECT a.work, a.headword, a.sense_nr FROM sense_alignment a "
                "WHERE NOT EXISTS (SELECT 1 FROM wujuh w WHERE w.work=a.work "
                "AND w.headword=a.headword AND w.sense_nr=a.sense_nr)")
    expect_none(cur, "cluster size disagrees with n_senses/n_works",
                "SELECT canonical_id, COUNT(*), MAX(n_senses), "
                "COUNT(DISTINCT work), MAX(n_works) FROM sense_alignment "
                "GROUP BY 1 HAVING COUNT(*) != MAX(n_senses) "
                "OR COUNT(DISTINCT work) != MAX(n_works)")
    # (work, headword, sense_nr) is not unique in wujuh -- 83 such keys carry
    # more than one gloss, because distinct lexicon entries were collapsed onto
    # one normalised headword. Matching on that key alone can therefore be
    # satisfied by the wrong entry, so the gloss is matched too. wujuh.gloss is
    # NULL where sense_alignment stores the empty string, hence the ifnull.
    expect_none(cur, "aligned sense whose gloss is not the one wujuh holds",
                "SELECT a.work, a.headword, a.sense_nr FROM sense_alignment a "
                "WHERE NOT EXISTS (SELECT 1 FROM wujuh w WHERE w.work=a.work "
                "AND w.headword=a.headword AND w.sense_nr=a.sense_nr "
                "AND IFNULL(w.gloss,'') = a.gloss)")
    senses, clusters = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT canonical_id) FROM sense_alignment"
    ).fetchone()
    return (f"{senses:,} aligned senses in {clusters:,} canonical senses, "
            "each resolving to a wujuh sense with the same gloss")


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


@check("word glosses")
def word_glosses(cur, args):
    """The glosses come from the same corpus project as the morphology, so a
    word without one, or a gloss naming no word, means the two drifted apart —
    not a coverage shortfall to be reported as a percentage."""
    require_tables(cur, "word_glosses")
    expect(cur.execute("SELECT COUNT(*) FROM word_glosses").fetchone()[0],
           EXPECTED_WORDS, "gloss rows")
    expect_none(cur, "gloss naming no word in corpus",
                "SELECT g.surah, g.ayah, g.word FROM word_glosses g WHERE NOT"
                " EXISTS (SELECT 1 FROM corpus c WHERE c.surah=g.surah"
                " AND c.ayah=g.ayah AND c.word=g.word)")
    expect_none(cur, "word without a gloss",
                "SELECT DISTINCT c.surah, c.ayah, c.word FROM corpus c WHERE"
                " NOT EXISTS (SELECT 1 FROM word_glosses g WHERE g.surah=c.surah"
                " AND g.ayah=c.ayah AND g.word=c.word)")
    expect_none(cur, "empty gloss",
                "SELECT surah, ayah, word FROM word_glosses"
                " WHERE gloss_en IS NULL OR TRIM(gloss_en)=''")
    distinct = cur.execute("SELECT COUNT(DISTINCT gloss_en) FROM word_glosses").fetchone()[0]
    return f"all {EXPECTED_WORDS:,} words glossed, {distinct:,} distinct glosses"


@check("irab passages")
def irab_passages(cur, args):
    """Al-Nahhas comments on the verses that raise a syntactic question, not on
    every verse, so partial coverage is expected and is reported rather than
    asserted. What must hold is that every passage names a verse that exists."""
    require_tables(cur, "irab")
    expect_none(cur, "irab passage naming no verse in corpus",
                "SELECT i.surah, i.ayah FROM irab i WHERE NOT EXISTS"
                " (SELECT 1 FROM corpus c WHERE c.surah=i.surah AND c.ayah=i.ayah)")
    expect_none(cur, "empty irab passage",
                "SELECT surah, ayah FROM irab WHERE passage IS NULL OR TRIM(passage)=''")
    expect_none(cur, "unknown irab work",
                "SELECT DISTINCT work FROM irab WHERE work NOT IN ('nahhas')")
    covered = cur.execute("SELECT COUNT(DISTINCT surah || ':' || ayah) FROM irab").fetchone()[0]
    rows = cur.execute("SELECT COUNT(*) FROM irab").fetchone()[0]
    # A passage that covers a range of verses is stored once per verse of the
    # range, so the row count is not the number of passages: say both, or the
    # table reads as holding several hundred more discussions than it does.
    distinct = cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT work, passage FROM irab)").fetchone()[0]
    return (f"{distinct:,} distinct passages in {rows:,} rows (a passage on a range of "
            f"verses is stored once per verse), covering {covered:,} of "
            f"{EXPECTED_AYAHS:,} verses "
            f"({covered / EXPECTED_AYAHS * 100:.0f}%, the rest raise no question he treats)")


@check("syntax tokens")
def syntax_tokens(cur, args):
    """Every written token must join a corpus segment and every segment must
    have one: the treebank uses the corpus' own addressing, so a gap means the
    two came from different versions, not that coverage is partial. Implicit
    tokens (the damir mustatir and other posited elements) legitimately have
    neither location nor corpus_id."""
    require_tables(cur, "syntax")
    expect_none(cur, "written syntax token without a corpus segment",
                "SELECT tid FROM syntax WHERE is_implicit=0 AND corpus_id IS NULL")
    expect_none(cur, "corpus segment without a syntax token",
                "SELECT c.id FROM corpus c WHERE NOT EXISTS"
                " (SELECT 1 FROM syntax s WHERE s.corpus_id = c.id)")
    expect_none(cur, "implicit token carrying a location",
                "SELECT tid FROM syntax WHERE is_implicit=1 AND corpus_id IS NOT NULL")
    expect_none(cur, "head pointing outside its own sentence",
                "SELECT s.tid FROM syntax s JOIN syntax h ON h.tid = s.head_tid"
                " WHERE h.sentence_id != s.sentence_id")
    written = cur.execute("SELECT COUNT(*) FROM syntax WHERE is_implicit=0").fetchone()[0]
    implicit = cur.execute("SELECT COUNT(*) FROM syntax WHERE is_implicit=1").fetchone()[0]
    return (f"{written:,} written tokens all linked to corpus, "
            f"{implicit:,} implicit tokens posited by the treebank")


@check("syntax head structure")
def syntax_heads(cur, args):
    """The head pointers are nearly a forest, and the exceptions are counted.

    Code that walks upward from a token wants a root to stop at, and almost
    everywhere there is one. Not everywhere: the treebank's own analyses leave
    some head chains running in a circle, and some sentences in which every
    token has a head, so no token is the root. Those are the source's readings
    and are not rewritten here -- but a naive upward walk over them never ends,
    and the numbers are pinned so they cannot grow unnoticed. Anything that
    walks heads should carry a seen-set.
    """
    require_tables(cur, "syntax")
    expect_none(cur, "token that is its own head",
                "SELECT tid FROM syntax WHERE head_tid = tid")
    expect_none(cur, "head_tid pointing at no token",
                "SELECT s.tid FROM syntax s WHERE s.head_tid IS NOT NULL"
                " AND NOT EXISTS (SELECT 1 FROM syntax h WHERE h.tid = s.head_tid)")
    head = dict(cur.execute("SELECT tid, head_tid FROM syntax"))
    colour, cycles, in_cycles = {}, 0, 0
    for start in head:
        if colour.get(start):
            continue
        path, node = [], start
        while node is not None and not colour.get(node):
            colour[node] = 1
            path.append(node)
            node = head.get(node)
        if node is not None and colour.get(node) == 1:
            cycles += 1
            in_cycles += len(path) - path.index(node)
        for n in path:
            colour[n] = 2
    rootless = cur.execute(
        "SELECT COUNT(*) FROM (SELECT sentence_id FROM syntax GROUP BY sentence_id"
        " HAVING SUM(head_tid IS NULL) = 0)").fetchone()[0]
    sentences = cur.execute("SELECT COUNT(DISTINCT sentence_id) FROM syntax").fetchone()[0]
    expect(cycles, EXPECTED_HEAD_CYCLES, "head_tid cycles")
    expect(rootless, EXPECTED_ROOTLESS, "sentences with no root token")
    return (f"{sentences - rootless:,} of {sentences:,} sentences have a root; "
            f"{rootless} do not, and {cycles} head chains ({in_cycles} tokens) "
            "run in a circle -- the treebank's own analyses, left as they came")


@check("corpus_id references")
def corpus_id_refs(cur, args):
    """A corpus_id must name a row that exists, and the same verse.

    Two tables point into `corpus` by id, and nothing checked either. An id
    that survives a rebuild of the corpus while pointing at a row that moved is
    the failure this catches: not a dangling reference, which would be obvious,
    but a live one that now names a different word in a different verse.
    """
    require_tables(cur, "corpus")
    for table in ("syntax", "wujuh"):
        if not cur.execute("SELECT name FROM sqlite_master WHERE name=?", (table,)).fetchone():
            continue
        expect_none(cur, f"{table}.corpus_id naming no corpus row",
                    f"SELECT corpus_id FROM {table} WHERE corpus_id IS NOT NULL"
                    " AND corpus_id NOT IN (SELECT id FROM corpus)")
        expect_none(cur, f"{table}.corpus_id naming another verse than its own",
                    f"SELECT t.corpus_id FROM {table} t JOIN corpus c ON c.id = t.corpus_id"
                    " WHERE t.surah != c.surah OR t.ayah != c.ayah")
    linked = cur.execute("SELECT COUNT(*) FROM syntax WHERE corpus_id IS NOT NULL").fetchone()[0]
    wl = cur.execute("SELECT COUNT(*) FROM wujuh WHERE corpus_id IS NOT NULL").fetchone()[0]
    return (f"{linked:,} syntax and {wl:,} wujuh rows point into corpus, "
            "every one at a row that exists and names the same verse")


@check("verses: derived columns")
def verses_derived(cur, args):
    """word_count, juz and hizb are derived, so they can drift from what they
    describe. Each is checked against the table it was derived from."""
    require_tables(cur, "verses", "juz_boundaries", "hizb_boundaries")
    expect_none(cur, "verses.word_count disagreeing with the words view",
                "SELECT v.surah, v.ayah FROM verses v LEFT JOIN"
                " (SELECT surah, ayah, COUNT(*) n FROM words GROUP BY 1,2) w"
                " ON w.surah=v.surah AND w.ayah=v.ayah"
                " WHERE IFNULL(w.n, 0) != v.word_count")
    expect_none(cur, "verses.juz outside 1..30", "SELECT surah, ayah FROM verses"
                " WHERE juz IS NULL OR juz < 1 OR juz > 30")
    expect_none(cur, "verses.hizb outside 1..60", "SELECT surah, ayah FROM verses"
                " WHERE hizb IS NULL OR hizb < 1 OR hizb > 60")
    expect_none(cur, "hizb that does not sit in its own juz",
                "SELECT v.surah, v.ayah FROM verses v JOIN hizb_boundaries h"
                " ON h.hizb = v.hizb WHERE h.juz != v.juz")
    hizbs = cur.execute("SELECT COUNT(*) FROM hizb_boundaries").fetchone()[0]
    expect(hizbs, 60, "ahzaab")
    return (f"{hizbs} ahzaab over 30 ajzaa', and every verse's word_count, juz "
            "and hizb agree with what they were derived from")


@check("riwaya differences")
def riwaya_differences(cur, args):
    """Every difference must name two riwayat that the riwayat table knows,
    sit in a real verse, and carry a kind. The two spot checks are the ones a
    silent regression in the transliterator would break first: 1:4 maalik /
    malik must be farsh (it is a difference of vowel length, and folding those
    away is exactly the mistake this comparison is built to avoid), and the
    sila of the mim must never be farsh (it is a rule, not a word)."""
    require_tables(cur, "riwaya_diff", "riwayat")
    expect_none(cur, "difference naming an unknown riwaya",
                "SELECT id FROM riwaya_diff WHERE riwaya_a NOT IN"
                " (SELECT code FROM riwayat) OR riwaya_b NOT IN"
                " (SELECT code FROM riwayat)")
    # ayah_a is numbered in riwaya_a's own division, and the riwayat divide
    # the verses differently -- sura 5 runs to 120 in Hafs and to 122 in the
    # Qaaloon package -- so only the Hafs side can be checked against corpus
    expect_none(cur, "difference outside the mushaf",
                "SELECT d.id FROM riwaya_diff d WHERE d.riwaya_a = 'hafs'"
                " AND NOT EXISTS (SELECT 1 FROM corpus c WHERE c.surah = d.surah"
                "  AND c.ayah = d.ayah_a)")
    expect_none(cur, "difference with an impossible reference",
                "SELECT id FROM riwaya_diff WHERE surah NOT BETWEEN 1 AND 114"
                " OR ayah_a < 1 OR ayah_b < 1")
    expect_none(cur, "difference without a kind",
                "SELECT id FROM riwaya_diff WHERE kind IS NULL OR kind = ''"
                " OR kind = 'onbekend'")
    expect_none(cur, "difference where both sides are the same word",
                "SELECT id FROM riwaya_diff WHERE form_a = form_b")
    expect_none(cur, "sila of the mim classed as farsh",
                "SELECT id FROM riwaya_diff WHERE class LIKE 'sila_mim%'"
                " AND kind = 'farsh'")
    expect_none(cur, "pair_type disagreeing with the qari of both riwayat",
                "SELECT d.id FROM riwaya_diff d JOIN riwayat ra ON ra.code = d.riwaya_a"
                " JOIN riwayat rb ON rb.code = d.riwaya_b WHERE d.pair_type !="
                " CASE WHEN ra.qari_en = rb.qari_en THEN 'binnen' ELSE 'tussen' END")
    expect_none(cur, "difference without a class",
                "SELECT id FROM riwaya_diff WHERE class IS NULL"
                " OR translit_a IS NULL OR translit_b IS NULL")
    # exactly one pair has been read word by word after the rules ran, and
    # only that pair may carry the verdicts of farsh_review.tsv
    expect_none(cur, "hand verdict on a pair that was not read",
                "SELECT id FROM riwaya_diff WHERE reviewed = 0"
                " AND class LIKE 'reviewed:hand%'")
    read = cur.execute("SELECT DISTINCT riwaya_a || '-' || riwaya_b"
                       " FROM riwaya_diff WHERE reviewed = 1").fetchall()
    if [r[0] for r in read] != ["hafs-warsh"]:
        raise Failed("pairs marked as read: %s (expected hafs-warsh alone)"
                     % (", ".join(r[0] for r in read) or "none"))
    # idghaam kabiir is read off one riwaya against its sibling as control, so
    # it can only ever be claimed for a riwaya the comparison knows applies it
    applies = ", ".join("'" + r + "'" for r in sorted(IDGHAAM_KABIR))
    expect_none(cur, "idghaam kabiir claimed for a riwaya without that rule",
                "SELECT id FROM riwaya_diff WHERE class LIKE 'idghaam_kabir%'"
                " AND riwaya_b NOT IN (" + applies + ")")
    # imaala is read off the mark the mushaf writes, so every row called imaala
    # has to carry one; a rule that drifted off its evidence shows up here
    marked = [row for row in cur.execute(
        "SELECT id, form_b FROM riwaya_diff WHERE class LIKE 'imaala%'")
        if not has_imala(row[1])]
    if marked:
        raise Failed("%d rows called imaala carry no imaala mark, e.g. id %s"
                     % (len(marked), marked[0][0]))
    # a verdict in farsh_review.tsv that matches nothing is a leftover from an
    # earlier run of the comparison, and would quietly stop excluding anything
    review = HERE / "farsh_review.tsv"
    if review.exists():
        import csv as _csv
        with open(review, encoding="utf-8") as fh:
            reader = _csv.reader(fh, delimiter="\t")
            next(reader, None)
            stale = [r[0] for r in reader if len(r) >= 2 and not cur.execute(
                "SELECT 1 FROM riwaya_diff WHERE riwaya_a='hafs' AND riwaya_b='warsh'"
                " AND TRIM(form_a)=? AND TRIM(form_b)=? LIMIT 1",
                (r[0], r[1])).fetchone()]
        if stale:
            raise Failed("farsh_review.tsv: %d verdicts match no difference, "
                         "e.g. %s" % (len(stale), "; ".join(stale[:3])))
    row = cur.execute("SELECT kind FROM riwaya_diff WHERE surah=1 AND ayah_a=4"
                      " AND riwaya_a='hafs' AND riwaya_b='warsh'").fetchone()
    if not row or row[0] != "farsh":
        raise Failed("1:4 maalik/malik is %s, expected farsh"
                     % (row[0] if row else "absent"))
    kinds = dict(cur.execute("SELECT kind, COUNT(*) FROM riwaya_diff GROUP BY kind"))
    total = sum(kinds.values())
    pairs = cur.execute("SELECT COUNT(*) FROM (SELECT DISTINCT riwaya_a, riwaya_b"
                        " FROM riwaya_diff)").fetchone()[0]
    return ("%s differences over %d pairs: %s"
            % (format(total, ","), pairs,
               ", ".join("%s %s" % (format(n, ","), k)
                         for k, n in sorted(kinds.items(), key=lambda x: -x[1]))))


@check("riwayat and their qurra")
def riwayat_readers(cur, args):
    """A riwaya is one pupil's transmission of a qari's qiraa, so every row
    must name both, and each qari must have exactly the two transmitters the
    canonical set gives him. Only the riwayat marked in_database have a source
    file here."""
    require_tables(cur, "riwayat")
    expect_none(cur, "riwaya without a qari",
                "SELECT code FROM riwayat WHERE qari_ar IS NULL OR qari_en IS NULL"
                " OR qari_died_ah IS NULL")
    expect_none(cur, "qari without exactly two riwayat",
                "SELECT qari_en FROM riwayat GROUP BY qari_en HAVING COUNT(*) != 2")
    expect_none(cur, "transmitter said to have died before the reader he cites",
                "SELECT code FROM riwayat WHERE riwaya_died_ah <= qari_died_ah")
    expect_none(cur, "riwaya with a source file but no comparison",
                "SELECT code FROM riwayat WHERE in_database = 1 AND code NOT IN"
                " (SELECT riwaya_a FROM riwaya_diff UNION"
                "  SELECT riwaya_b FROM riwaya_diff)")
    loaded = cur.execute("SELECT COUNT(*) FROM riwayat WHERE in_database=1").fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM riwayat").fetchone()[0]
    qurra = cur.execute("SELECT COUNT(DISTINCT qari_en) FROM riwayat").fetchone()[0]
    return f"{total} riwayat from {qurra} qurra, {loaded} of them compared here"


def quoted_words(text, verses, extra=None):
    """Every Arabic word a book quotes beside a verse reference, checked.

    Two shapes are recognised, `phrase (S:A)` and `S:A phrase`, and only what
    sits directly against the reference is checked. A looser rule was tried --
    every Arabic word on a line that names one verse -- and it had to go: prose
    puts paradigm forms next to citations all the time, and `waratha / yarithu
    ("erven", 19:6 yarithunii)` quotes one word from 19:6 and illustrates with
    two others. Anchoring on the reference is what separates the two.

    Words are compared without their vowels: a quote inside a sentence is
    sometimes cut short of a final vowel or a pause mark, and the question is
    whether the words are in that verse, not how they were typeset. `extra`
    holds what else counts as standing there: forms from another riwaya than
    the one `verses` was built from, and the roots of the words -- a book cites
    a root beside its verse as readily as a word, and `sahat (20:61)` is a true
    statement about 20:61 even though the word written there is
    `fa-yushitakum`."""
    here = r"([\u0621-\u06ff][\u0600-\u06ff\s]*?)\s*\((\d+):(\d+)\)"
    there = r"(\d+):(\d+)\s+([\u0621-\u06ff][\u0600-\u06ff\s*]*)"
    # A table row is the third shape, and it is the one the books use most: a
    # cell holding nothing but S:A, with Arabic cells beside it on the same row.
    # Skipping every line that starts with a pipe left the fifteen-forms table
    # of the sarf book unchecked, and that table cited a form-IX example from
    # the wrong verse for as long as it existed.
    bad, seen = [], 0
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            refs = [c for c in cells if re.fullmatch(r"\d+:\d+", c)]
            if len(refs) != 1:
                continue
            # Only rows that open with the reference, and only the cell next to
            # it. Those are the tables of literal quotations -- the riwaya
            # tables of both books, where the cell beside the verse number is
            # the word as that mushaf writes it.
            #
            # Deliberately out of scope: a table that puts the reference in a
            # later column, because the Arabic beside it there is the citation
            # form and not a quotation. The sarf book's fifteen-forms table
            # gives أَنْعَمَ for form IV at 1:7, where the verse writes
            # أَنْعَمْتَ, and ٱسْتَعِينُ at 1:5 for نَسْتَعِينُ. Both are true
            # about those verses and neither is the word standing in them, and
            # telling that apart from a wrong reference needs morphology this
            # check does not have.
            if cells[0] != refs[0]:
                continue
            surah, ayah = (int(x) for x in refs[0].split(":"))
            found = [(c, surah, ayah) for c in cells[1:2]
                     if re.search(r"[\u0621-\u06ff]", c)]
        else:
            found = [(m.group(1), int(m.group(2)), int(m.group(3)))
                     for m in re.finditer(here, line)]
            found += [(m.group(3), int(m.group(1)), int(m.group(2)))
                      for m in re.finditer(there, line)]
        for phrase, surah, ayah in found:
            if (surah, ayah) not in verses:
                continue
            hay = verses[(surah, ayah)] | (extra or {}).get((surah, ayah), set())
            for token in re.sub(r"[*_>|\u2014\u2013\-\u2026\u060c]", " ",
                                phrase).split():
                bare = normalize(token)
                if not bare:
                    continue
                seen += 1
                # A table gives the citation form -- أَنْعَمَ for form IV -- beside
                # the verse where it stands as أَنْعَمْتَ, and prose quotes a word
                # without the fa- or wa- the verse writes. Both are true
                # statements about that verse, so a word also counts as standing
                # there when a word of the verse contains it. A word that is not
                # in the verse in any shape still fails, which is what caught
                # ٱبْيَضَّتْ cited from 3:106 where the verse has تَبْيَضُّ.
                if bare not in hay and not any(bare in w for w in hay):
                    bad.append("%d:%d %s" % (surah, ayah, token))
    return seen, bad


# The figures the prose quotes, and where they are quoted. Each entry is a
# label, the query that produces the true value, and the patterns that find the
# claim in a document -- one capture group, the number. See document_figures.
DOC_FIGURES = [
    ("corpus segments", "SELECT COUNT(*) FROM corpus", [
        r"— ([\d.,]+) segments, ",
        r"### Table `corpus` — ([\d.,]+) rows",
        r"Van de ([\d.,]+) morfologische segmenten"]),
    ("posited syntax tokens", "SELECT COUNT(*) FROM syntax WHERE is_implicit=1", [
        r"including ([\d.,]+) elements the grammarians",
        r"staat: ([\d.,]+) elementen die de",
        r"([\d.,]+) geponeerde elementen in totaal"]),
    ("verses", "SELECT COUNT(*) FROM verses", [
        r"written words, ([\d.,]+) verses",
        r"\| `verses` \| ([\d.,]+) \|"]),
    ("written words", "SELECT COUNT(*) FROM words", [
        r"segments, ([\d.,]+) written words",
        r"([\d.,]+) geschreven woorden"]),
    ("kalimaat (written plus posited)", "SELECT COUNT(*) FROM syntax", [
        r"Quran op \*\*([\d.,]+) kalimat"]),
    ("distinct roots", "SELECT COUNT(DISTINCT root_ar) FROM corpus "
                       "WHERE root_ar IS NOT NULL AND root_ar<>''", [
        r"suras, ([\d.,]+) roots,",
        r"are ([\d.,]+) distinct roots"]),
    ("wujuh rows", "SELECT COUNT(*) FROM wujuh", [
        r"\(polysemy\): ([\d.,]+) rows linking",
        r"### Table `wujuh` — ([\d.,]+) rows"]),
    ("wujuh distinct senses",
     "SELECT COUNT(*) FROM (SELECT DISTINCT work, headword, sense_nr FROM wujuh)", [
        r"across the four works, ([\d.,]+) distinct senses",
        r"entries and ([\d.,]+) senses\."]),
    ("aligned senses", "SELECT COUNT(*) FROM sense_alignment", [
        r"sense alignment\*\*: ([\d.,]+) of those senses",
        r"### Table `sense_alignment` — ([\d.,]+) rows",
        r"works: ([\d.,]+) aligned senses"]),
    ("canonical senses", "SELECT COUNT(DISTINCT canonical_id) FROM sense_alignment", [
        r"senses grouped into\s+([\d.,]+) canonical",
        r"^([\d.,]+) canonical senses, of which",
        r"([\d.,]+) canonieke senses"]),
    ("riwaya_diff rows", "SELECT COUNT(*) FROM riwaya_diff", [
        r"`riwaya_diff` — ([\d.,]+) rows over"]),
]

# Every pair's places and farsh, in both documents' table shapes.
PAIR_NAMES = {"hafs": ("hafs", "Ḥafṣ"), "warsh": ("warsh", "Warsh"),
              "qaloon": ("qaloon", "Qālūn"), "bazzi": ("bazzi", "al-Bazzī"),
              "qumbul": ("qumbul", "Qunbul"), "doori": ("doori", "al-Dūrī"),
              "soosi": ("soosi", "al-Sūsī"), "shouba": ("shouba", "Shuʿba")}


def _num(text):
    return int(text.replace(".", "").replace(",", ""))


# Column headers whose Arabic is deliberately from somewhere else: the head a
# word hangs on (another verse, often), a grammatical explanation, a pointer
# into a chapter. Only columns outside this list are read as quotations.
ELSEWHERE_COLUMNS = {"Hangt aan", "Waarom geen iʿrāb", "Waar het in dit boek staat",
                     "Betekenis (hoofdlijn)", "Patroon", "Wat het is"}


@check("schema documentation")
def schema_documentation(cur, args):
    """README must name every table, every view and every column, and must not
    name a column that is gone.

    The third of the three things this repository kept getting wrong, after the
    figures and the Arabic. A column added by a migration and never written up
    is invisible to anyone reading the README, and a column documented after it
    was renamed sends them looking for something that is not there. Neither
    fails loudly on its own; both fail here.

    The `syntax` table is why this is worth a check: it carries the whole
    treebank layer the nahw book is built on, and until this check was written
    README named ten of its sixteen columns nowhere at all."""
    readme = HERE / "README.md"
    if not readme.exists():
        raise Skipped("README.md is not here")
    text = readme.read_text(encoding="utf-8")
    # Only what stands between backticks on one line counts as documentation;
    # a bare word in a sentence is prose, not a column name.
    quoted = set()
    for chunk in re.findall(r"`([^`\n]+)`", text):
        quoted |= set(re.findall(r"[A-Za-z_]\w*", chunk))

    objects = [(r[0], r[1]) for r in cur.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table','view')"
        " AND name NOT LIKE 'sqlite_%'")]
    unnamed, undocumented = [], []
    for name, kind in sorted(objects):
        if name not in quoted:
            unnamed.append("%s %s" % (kind, name))
        for row in cur.execute('PRAGMA table_info("%s")' % name):
            if row[1] not in quoted:
                undocumented.append("%s.%s" % (name, row[1]))

    # A column table documents the object its section is about; a row naming a
    # column that object does not have is stale documentation.
    known = {n for n, _ in objects}
    columns = {n: {r[1] for r in cur.execute('PRAGMA table_info("%s")' % n)} for n in known}
    lines, current, ghosts = text.splitlines(), None, []
    for i, line in enumerate(lines):
        if line.startswith("#") or line.startswith("`"):
            for m in re.finditer(r"`([a-z_]+)`", line):
                if m.group(1) in known:
                    current = m.group(1)
        if line.startswith("| Column | Meaning |") and current:
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                for word in re.findall(r"`([A-Za-z_]\w*)`", lines[j].split("|")[1]):
                    if word not in columns[current]:
                        ghosts.append("%s.%s" % (current, word))
                j += 1

    problems = []
    if unnamed:
        problems.append("%d never named in README: %s"
                        % (len(unnamed), ", ".join(unnamed)))
    if undocumented:
        problems.append("%d column(s) named nowhere: %s"
                        % (len(undocumented), ", ".join(undocumented[:8])))
    if ghosts:
        problems.append("%d documented column(s) the table does not have: %s"
                        % (len(ghosts), ", ".join(ghosts[:8])))
    if problems:
        raise Failed("; ".join(problems))
    total = sum(len(columns[n]) for n in known)
    return ("%d tables and views with %d columns, all named in README"
            % (len(objects), total))


@check("Arabic quotations")
def arabic_quotations(cur, args):
    """Arabic quoted beside a verse number, compared codepoint for codepoint.

    The sibling of `document figures`, for the other thing that keeps drifting
    here. `sarf book examples` and `nahw book examples` ask whether a quoted
    word is *in* the verse, and they compare with the vowels stripped, because
    a quote is often cut short of a final vowel. That leaves the notation
    unchecked, and the notation is exactly where hand-typed Arabic goes wrong.

    One thing had to be settled before this could mean anything: the mushaf
    files write the shadda before the vowel it carries, and the documents
    write the vowel first. Neither is wrong. Unicode's canonical order is
    vowel-then-shadda (combining classes 30-32 against 33), so the documents
    are in NFC and the sources are not, and the two are canonically equivalent
    -- they render identically and NFC makes them equal. So the comparison is
    on NFC, and anything that still differs is a real difference and not a
    storage detail.

    A word that matches only once its vowels are stripped is reported apart
    from one that is not in the verse at all: the first is a notation
    mismatch, the second a wrong reference. Both fail.
    """
    require_tables(cur, "words")
    index = {}

    # A pause sign belongs to the page, not to the word: prose quotes قَالُوٓاْ
    # where the mushaf writes قَالُوٓاْۖ, and that is not a notation mismatch.
    pause = "\u06d6\u06d7\u06d8\u06d9\u06da\u06db\u06dc\u06dd\u06de\u06e9\u06e0"

    def bare(word):
        return unicodedata.normalize("NFC", word).rstrip(pause)

    def add(surah, ayah, word):
        index.setdefault((surah, ayah), set()).add(bare(word))

    for surah, ayah, ar in cur.execute("SELECT surah, ayah, word_ar FROM words"):
        add(surah, ayah, repair_markers(ar))
    for surah, ayah, root in cur.execute(
            "SELECT surah, ayah, root_ar FROM corpus WHERE root_ar IS NOT NULL AND root_ar<>''"):
        add(surah, ayah, root)
    # The eight mushaf packages, each word as that package writes it.
    for path in sorted((HERE / "sources").glob("riwaya_*.csv")):
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                s, a = row.get("sora") or row.get("sura_no"), row.get("aya_no")
                if not (s and a):
                    continue
                text = max((x for x in row.values()
                            if x and any("\u0600" <= c <= "\u06ff" for c in x)),
                           key=len, default="")
                for word in text.split():
                    add(int(s), int(a), word)
    # A riwaya form is cited under the verse number of the side it is compared
    # against, which for nine of the ten pairs is Hafs', not its own.
    if cur.execute("SELECT name FROM sqlite_master WHERE name='riwaya_diff'").fetchone():
        for surah, ayah, fa, fb in cur.execute(
                "SELECT surah, ayah_a, form_a, form_b FROM riwaya_diff"):
            for form in (fa, fb):
                for word in (form or "").split():
                    add(surah, ayah, word)
    loose = {k: {normalize(w) for w in ws} for k, ws in index.items()}

    letter = re.compile(r"[\u0620-\u064a\u0671-\u06d3]")
    here = r"([\u0621-\u06ff][\u0600-\u06ff\s]*?)\s*\((\d+):(\d+)\)"
    there = r"(\d+):(\d+)\s+([\u0621-\u06ff][\u0600-\u06ff\s*]*)"
    notation, absent, seen = [], [], 0
    for name in ("README.md", "BEVINDINGEN.md", "docs/nahw-nl.md",
                 "docs/sarf-nl.md", "docs/hafs-warsh.md"):
        path = HERE / name
        if not path.exists():
            continue
        header = []
        for line in path.read_text(encoding="utf-8").splitlines():
            found = []
            if line.startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    if any(c.startswith("Vers") or c == "Paar" for c in cells[:1]):
                        header = cells
                refs = [c for c in cells if re.fullmatch(r"\d+:\d+", c)]
                if len(refs) == 1 and cells and cells[0] == refs[0]:
                    s, a = (int(x) for x in refs[0].split(":"))
                    for i, cell in enumerate(cells[1:], 1):
                        col = header[i] if i < len(header) else ""
                        if col in ELSEWHERE_COLUMNS or not letter.search(cell):
                            continue
                        found.append((cell, s, a))
            else:
                found = [(m.group(1), int(m.group(2)), int(m.group(3)))
                         for m in re.finditer(here, line)]
                found += [(m.group(3), int(m.group(1)), int(m.group(2)))
                          for m in re.finditer(there, line)]
            for phrase, s, a in found:
                for token in re.sub(r"[*_>|\u2014\u2013\u2026\u060c()\[\];:,.`]",
                                    " ", phrase).split():
                    if not letter.search(token):
                        continue
                    seen += 1
                    if bare(token) in index.get((s, a), ()):
                        continue
                    where = "%s %d:%d %s" % (name, s, a, token)
                    if normalize(token) in loose.get((s, a), ()):
                        notation.append(where)
                    else:
                        absent.append(where)
    if notation or absent:
        parts = []
        if notation:
            parts.append("%d written with different marks than any mushaf or the "
                         "corpus: %s" % (len(notation), "; ".join(notation[:4])))
        if absent:
            parts.append("%d not in the verse they name at all: %s"
                         % (len(absent), "; ".join(absent[:4])))
        raise Failed("; ".join(parts))
    return ("%d Arabic quotations across %d documents match the mushaf "
            "codepoint for codepoint (compared on NFC)" % (seen, 5))


@check("document figures")
def document_figures(cur, args):
    """The figures the prose quotes must be the figures the database holds.

    This is the check the repository most needed and did not have. Every
    headline number in README.md, BEVINDINGEN.md and the two books is typed by
    hand out of a script that keeps changing underneath it, and an audit found
    them drifted in more than a dozen places at once -- 5,027 senses against
    5,043, a control split of 958 against 1,152, a chapter counting 515 farsh
    places where the database held 523. Each was true when it was written.

    So: a small registry of figures, each with the query that produces it and
    the phrasings that quote it. A claim whose number no longer matches fails.
    A phrasing that matches nothing at all is reported too, because a sentence
    that was reworded silently stops being checked, and that is how the drift
    started."""
    require_tables(cur, "corpus", "riwaya_diff")
    docs = {}
    for name in ("README.md", "BEVINDINGEN.md", "SOURCES.md",
                 "docs/nahw-nl.md", "docs/sarf-nl.md", "docs/hafs-warsh.md"):
        path = HERE / name
        if path.exists():
            docs[name] = path.read_text(encoding="utf-8")

    checks = list(DOC_FIGURES)
    # fetchall first: the loop body runs its own queries on this same cursor,
    # which would reset it and end the loop after one pair
    pairs = cur.execute("SELECT DISTINCT riwaya_a, riwaya_b FROM riwaya_diff").fetchall()
    for a, b in pairs:
        en, nl_a = PAIR_NAMES[a][0], PAIR_NAMES[a][1]
        eb, nl_b = PAIR_NAMES[b][0], PAIR_NAMES[b][1]
        total, farsh = cur.execute(
            "SELECT COUNT(*), SUM(kind='farsh') FROM riwaya_diff "
            "WHERE riwaya_a=? AND riwaya_b=?", (a, b)).fetchone()
        # the row shape of both pair tables: name | kind | places | **farsh** |
        row = r"\| %s [–-] %s \|[^|]*\| ([\d.,]+) \|"
        checks.append(("%s-%s places" % (a, b), total,
                       [row % (en, eb), row % (nl_a, nl_b)]))
        rowf = r"\| %s [–-] %s \|[^|]*\| [\d.,]+ \| \*\*([\d.,]+)\*\* \|"
        checks.append(("%s-%s farsh" % (a, b), farsh,
                       [rowf % (en, eb), rowf % (nl_a, nl_b)]))

    bad, unseen, seen = [], [], 0
    for label, source, patterns in checks:
        want = cur.execute(source).fetchone()[0] if isinstance(source, str) else source
        for pattern in patterns:
            hit = False
            for name, text in docs.items():
                for m in re.finditer(pattern, text, re.M):
                    hit = True
                    seen += 1
                    if _num(m.group(1)) != want:
                        bad.append("%s: %s says %s, the database says %s"
                                   % (name, label, m.group(1), f"{want:,}"))
            if not hit:
                unseen.append("%s: no document matches %r" % (label, pattern))
    if bad:
        raise Failed("%d figure(s) in the documents disagree with the database: %s"
                     % (len(bad), "; ".join(bad[:6])))
    if unseen:
        raise Warned(
            "%d registered figure(s) match no document any more, so nothing "
            "checks them: %s" % (len(unseen), "; ".join(unseen[:4])))
    return ("%d quoted figures in %d documents all agree with the database"
            % (seen, len(docs)))


@check("sarf book examples")
def sarf_book(cur, args):
    """Every word the sarf book quotes in running prose beside a verse number.

    Scope, so the PASS line is not read for more than it says: this checks the
    quotations the book sets in its own sentences -- `19:6 yarithunii`,
    `famakatha (27:22)` -- and not the several hundred bare verse references,
    nor the Arabic inside its tables, which are pasted from sarf_examples.py
    and are that script's to reproduce. Prose quotations are typed by hand, so
    they are exactly what goes stale. It also quotes Warsh where the two riwayat read a word differently,
    and those forms are not in the corpus at all, so the riwaya table is
    consulted as a second source: a word counts as found when it stands in the
    verse in either transmission.

    The paradigm tables are not checked here. They are pasted from
    sarf_examples.py, and re-running it is the check for those."""
    book = HERE / "docs" / "sarf-nl.md"
    if not book.exists():
        raise Skipped("docs/sarf-nl.md is not here")
    require_tables(cur, "words")
    verse = {}
    for surah, ayah, ar in cur.execute("SELECT surah, ayah, word_ar FROM words"):
        verse.setdefault((surah, ayah), set()).add(normalize(repair_markers(ar)))
    other = {}
    for surah, ayah, root in cur.execute(
            "SELECT surah, ayah, root_ar FROM corpus WHERE root_ar IS NOT NULL"):
        other.setdefault((surah, ayah), set()).add(normalize(root))
    if cur.execute("SELECT name FROM sqlite_master WHERE name='riwaya_diff'").fetchone():
        for surah, ayah, form in cur.execute(
                "SELECT surah, ayah_a, form_b FROM riwaya_diff WHERE form_b != ''"):
            other.setdefault((surah, ayah), set()).add(normalize(form))
    seen, bad = quoted_words(book.read_text(encoding="utf-8"), verse, other)
    if bad:
        raise Failed("%d quoted word(s) in docs/sarf-nl.md are not in the verse "
                     "they are cited from: %s" % (len(bad), "; ".join(bad[:4])))
    return (f"{seen} quoted words in docs/sarf-nl.md all found in the verses "
            f"they name")


@check("nahw book examples")
def nahw_book(cur, args):
    """Every example in docs/nahw-nl.md must still be in the database.

    The book quotes the text twice over: as three-column example rows
    (verse, word, what it hangs on) taken from the treebank, and as verses
    quoted in running prose. Both are pasted in, so both go stale silently
    when the database is rebuilt from a corrected source. This check reads
    the book back and looks every one of them up again.

    Verse quotes are compared without their vowels. The book writes them as
    the mushaf does, but a quote inside a sentence is sometimes cut short of
    a final vowel or a pause mark, and the point here is whether the words
    are in that verse, not how they were typeset. The example rows are
    compared literally, because those are pasted from the generator."""
    book = HERE / "docs" / "nahw-nl.md"
    if not book.exists():
        raise Skipped("docs/nahw-nl.md is not here")
    require_tables(cur, "syntax", "words")
    text = book.read_text(encoding="utf-8")
    written = {}
    for surah, ayah, word, ar in cur.execute(
            "SELECT surah, ayah, word, word_ar FROM words"):
        written[(surah, ayah, word)] = repair_markers(ar)

    def whole(surah, ayah, word):
        return written.get((surah, ayah, word))

    rows_bad, rows_n = [], 0
    for line in text.splitlines():
        m = re.match(r"^\| (\d+):(\d+) \| (\S+) \| (\S+) \|$", line)
        if not m:
            continue
        surah, ayah, word, head = (int(m.group(1)), int(m.group(2)),
                                   m.group(3), m.group(4))
        rows_n += 1
        found = cur.execute(
            "SELECT s.word, h.surah, h.ayah, h.word FROM syntax s"
            " LEFT JOIN syntax h ON h.tid = s.head_tid WHERE s.surah=?"
            " AND s.ayah=? AND s.is_implicit=0 AND s.word IS NOT NULL",
            (surah, ayah)).fetchall()
        if not any(whole(surah, ayah, w) == word
                   and (whole(hs, ha, hw) if hs else "\u2014") == head
                   for w, hs, ha, hw in found):
            rows_bad.append(line.strip())

    verse = {}
    for (surah, ayah, _), ar in written.items():
        verse.setdefault((surah, ayah), set()).add(normalize(ar))
    quotes_n, quotes_bad = quoted_words(text, verse)

    if rows_bad or quotes_bad:
        bad = rows_bad + quotes_bad
        raise Failed(f"{len(bad)} example(s) in docs/nahw-nl.md are not in the "
                     f"database: {'; '.join(bad[:3])}")
    return (f"{rows_n} treebank example rows and {quotes_n} quoted words in "
            f"docs/nahw-nl.md all found")


def report(outcome, name, text):
    """Print one result; multi-line details are indented under the first."""
    head, *rest = str(text).splitlines()
    print(f"{outcome:<5} {name}: {head}")
    for line in rest:
        print(f"        {line}")


def main():
    ap = argparse.ArgumentParser(
        description="Validate the integrity of a built quran.db.")
    ap.add_argument("--db", default=str(HERE / "quran.db"), metavar="PATH",
                    help="database to validate (default: ./quran.db)")
    ap.add_argument("--sample", type=int, default=SPOT_SAMPLE, metavar="N",
                    help=f"citations drawn per match_status for the spot check "
                         f"(default {SPOT_SAMPLE}, 0 = all)")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        sys.exit(f"{db} does not exist; build it first with build.py")
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()

    passed = warned = failed = skipped = 0
    for name, fn in CHECKS:
        try:
            detail = fn(cur, args)
            passed += 1
            report("PASS", name, detail)
        except Skipped as exc:
            skipped += 1
            report("SKIP", name, exc)
        except Warned as exc:
            warned += 1
            report("WARN", name, exc)
        except Failed as exc:
            failed += 1
            report("FAIL", name, exc)
        except sqlite3.Error as exc:
            failed += 1
            report("FAIL", name, f"database error: {exc}")
    con.close()

    print(f"\n{len(CHECKS)} checks on {db.name}: {passed} passed, "
          f"{warned} warned, {failed} failed, {skipped} skipped "
          "(warnings do not fail the run)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
