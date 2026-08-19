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
import difflib
import json
import random
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

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
        "SELECT name FROM sqlite_master WHERE type='table'")}
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
        elif path.stat().st_mtime > RESOLVED.stat().st_mtime:
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
    senses, clusters = cur.execute(
        "SELECT COUNT(*), COUNT(DISTINCT canonical_id) FROM sense_alignment"
    ).fetchone()
    return (f"{senses:,} aligned senses in {clusters:,} canonical senses, "
            "all resolving to a wujuh sense")


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
