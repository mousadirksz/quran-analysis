#!/usr/bin/env python3
"""Generate the paradigm tables for docs/sarf-nl.md from the Quran itself.

For each of the eight root types the sarf distinguishes -- salim, mahmuz,
mudaccaf, mithal, ajwaf, naqis, lafif mafruq, lafif maqrun -- this picks the
best-attested roots and prints, for each, the forms the Quran actually attests
across the fourteen persons, with a verse reference for each.

The point of teaching from attested forms is that the gaps are informative
too: no root is conjugated through the whole paradigm in the text, and which
cells are filled says something about how the Quran speaks.

    python3 sarf_examples.py            # all types
    python3 sarf_examples.py ajwaf      # one type
    python3 sarf_examples.py --markdown # tables ready for the textbook

Classification uses the corpus' own root letters. Note that the corpus writes
every hamza in a root as alif, so a root counts as mahmuz when it carries an
alif in a position where the weak-letter analysis does not explain it.
"""

import sqlite3
import sys
from pathlib import Path

from add_metadata import repair_markers

DB = Path(__file__).parent / "quran.db"

# traditional order of the fourteen persons
PGN_ORDER = ["3MS", "3FS", "3MD", "3FD", "3MP", "3FP",
             "2MS", "2FS", "2D", "2MD", "2FD", "2MP", "2FP", "1S", "1P"]
PGN_NL = {
    "3MS": "hij", "3FS": "zij (v. enk.)", "3MD": "zij tweeën (m.)",
    "3FD": "zij tweeën (v.)", "3MP": "zij (m. mv.)", "3FP": "zij (v. mv.)",
    "2MS": "jij (m.)", "2FS": "jij (v.)", "2D": "jullie tweeën",
    "2MD": "jullie tweeën (m.)", "2FD": "jullie tweeën (v.)",
    "2MP": "jullie (m.)", "2FP": "jullie (v.)", "1S": "ik", "1P": "wij",
}

TYPES = ["salim", "mahmuz", "mudaccaf", "mithal", "ajwaf", "naqis",
         "lafif mafruq", "lafif maqrun"]

TYPE_NL = {
    "salim": "Sālim — gaaf",
    "mahmuz": "Mahmūz — met hamza",
    "mudaccaf": "Muḍaʿʿaf — verdubbeld",
    "mithal": "Mithāl — eerste letter zwak",
    "ajwaf": "Ajwaf — tweede letter zwak",
    "naqis": "Nāqiṣ — derde letter zwak",
    "lafif mafruq": "Lafīf mafrūq — eerste en derde zwak",
    "lafif maqrun": "Lafīf maqrūn — tweede en derde zwak",
}


def classify(root):
    """Assign a three-letter root to its sarf type."""
    if len(root) != 3:
        return None
    f, a, l = root
    weak = [i for i, ch in enumerate(root) if ch in "وي"]
    hamza = [i for i, ch in enumerate(root) if ch == "ا"]
    if f == a or a == l:
        return "mudaccaf"
    if len(weak) >= 2:
        return "lafif maqrun" if weak == [1, 2] else "lafif mafruq"
    if weak == [0]:
        return "mithal"
    if weak == [1]:
        return "ajwaf"
    if weak == [2]:
        return "naqis"
    if hamza:
        return "mahmuz"
    return "salim"


def roots_by_type(cur):
    out = {t: [] for t in TYPES}
    for root, n in cur.execute(
            "SELECT root_ar, COUNT(*) n FROM corpus WHERE pos='V' AND root_ar != ''"
            " AND LENGTH(root_ar)=3 GROUP BY root_ar ORDER BY n DESC"):
        t = classify(root)
        if t:
            out[t].append((root, n))
    return out


def paradigm(cur, root, form=None):
    """The form-I active forms this root is attested in, per person and aspect.

    verb_form is null for the bare form in this corpus, so that filter is what
    keeps the derived patterns out of a table meant to teach the bare one."""
    # The corpus stores a verb stem separately from its ending, so the stem
    # alone reads as qalu rather than qalu-w-a. Join the whole written word
    # back together, and prefer an occurrence that carries no prefix, so the
    # learner sees the bare form rather than wa-qala.
    rows = cur.execute(
        "SELECT v.aspect, v.person || IFNULL(v.gender,'') || v.number AS pgn,"
        " w.word_ar, v.surah, v.ayah,"
        " (SELECT COUNT(*) FROM corpus p WHERE p.surah=v.surah AND p.ayah=v.ayah"
        "   AND p.word=v.word AND p.segment_type='PREFIX') AS prefixes"
        " FROM corpus v JOIN words w"
        "   ON w.surah=v.surah AND w.ayah=v.ayah AND w.word=v.word"
        " WHERE v.root_ar = ? AND v.pos='V' AND v.person != ''"
        " AND IFNULL(v.voice,'ACT') = 'ACT'"
        + (" AND v.verb_form IS NULL" if form is None else " AND v.verb_form = ?") +
        " ORDER BY prefixes, v.surah, v.ayah",
        (root,) if form is None else (root, form)).fetchall()
    best = {}
    for aspect, pgn, form, s, a, prefixes in rows:
        key = (aspect, pgn)
        if key not in best:  # unprefixed occurrences come first
            best[key] = (repair_markers(form), f"{s}:{a}", prefixes)
    return best


def lemma_of(cur, root, form=None):
    sql = ("SELECT lemma_ar FROM corpus WHERE root_ar=? AND pos='V' AND lemma_ar != ''"
           + (" AND verb_form IS NULL" if form is None else " AND verb_form = ?")
           + " GROUP BY lemma_ar ORDER BY COUNT(*) DESC LIMIT 1")
    r = cur.execute(sql, (root,) if form is None else (root, form)).fetchone()
    return r[0] if r else "—"


def busiest_form(cur, root):
    """The derived pattern this root is most attested in, for roots whose bare
    form the Quran barely uses."""
    r = cur.execute(
        "SELECT verb_form FROM corpus WHERE root_ar=? AND pos='V'"
        " AND verb_form IS NOT NULL AND person != ''"
        " GROUP BY verb_form ORDER BY COUNT(*) DESC LIMIT 1", (root,)).fetchone()
    return r[0] if r else None


def render(par, head, plain, markdown):
    """Print one paradigm: the persons the Quran attests, over the three
    tenses. Rows the text does not attest are left out rather than filled in,
    which is the whole point of teaching from the text."""
    if markdown:
        print("\n" + head + "\n")
        print("| Persoon | Māḍī | Vers | Muḍāriʿ | Vers | Amr | Vers |")
        print("|---|---|---|---|---|---|---|")
    else:
        print("\n" + plain)
    for pgn in PGN_ORDER:
        perf, impf, impv = (par.get((a, pgn)) for a in ("PERF", "IMPF", "IMPV"))
        if not (perf or impf or impv):
            continue
        cell = lambda x, i: (x[i] if x else ("—" if i == 0 else ""))
        if markdown:
            print(f"| {PGN_NL[pgn]} | {cell(perf,0)} | {cell(perf,1)}"
                  f" | {cell(impf,0)} | {cell(impf,1)}"
                  f" | {cell(impv,0)} | {cell(impv,1)} |")
        else:
            print(f"    {PGN_NL[pgn]:<18} {cell(perf,0):<14}"
                  f" {cell(impf,0):<14} {cell(impv,0)}")


def show(cur, t, roots, markdown, per_type=2):
    title = TYPE_NL[t]
    print(("\n### " + title) if markdown else ("\n" + "=" * 62 + "\n" + title))
    shown = 0
    for root, total in roots:
        par, form = paradigm(cur, root), None
        if len(par) < 5:
            # For the lafif types the Quran barely attests the bare form. The
            # weak-letter behaviour shows just as well in a derived pattern, so
            # fall back to the one this root is most used in -- a single
            # pattern, so the table stays one paradigm rather than a mixture.
            form = busiest_form(cur, root)
            if form:
                par = paradigm(cur, root, form)
        if len(par) < 4:
            continue
        lemma = lemma_of(cur, root, form)
        cells = sum(1 for _ in par)
        note = f" · vorm {form}" if form else ""
        head = f"**{root}** — {lemma} · {total}× in de Quran, {cells} cellen geattesteerd{note}"
        plain = f"  {root}  ({lemma})  {total}x, {cells} cellen" + (f", vorm {form}" if form else "")
        render(par, head, plain, markdown)
        shown += 1
        if shown >= per_type:
            break


# ---------------------------------------------------------------- de abwab

FATHA, KASRA, DAMMA = "\u064e", "\u0650", "\u064f"
VOWEL_NAME = {FATHA: "a", KASRA: "i", DAMMA: "u"}

BAB_NAMES = {
    ("a", "u"): ("1", "فَعَلَ / يَفْعُلُ"),
    ("a", "i"): ("2", "فَعَلَ / يَفْعِلُ"),
    ("a", "a"): ("3", "فَعَلَ / يَفْعَلُ"),
    ("i", "a"): ("4", "فَعِلَ / يَفْعَلُ"),
    ("u", "u"): ("5", "فَعُلَ / يَفْعُلُ"),
    ("i", "i"): ("6", "فَعِلَ / يَفْعِلُ"),
}


def ayn_vowel(form, root):
    """The vowel on the second root letter, which is what the bab turns on.

    Walks the root letters through the written form in order, so that prefixes
    and the letters of the pattern do not shift the count."""
    pos, found = 0, []
    for i, ch in enumerate(form):
        if pos < 3 and ch == root[pos]:
            found.append(i)
            pos += 1
    if len(found) < 2:
        return None
    j = found[1]
    return VOWEL_NAME.get(form[j + 1]) if j + 1 < len(form) else None


def bare_3ms(cur, root, aspect):
    r = cur.execute(
        "SELECT form_ar FROM corpus WHERE root_ar=? AND pos='V' AND aspect=?"
        " AND person='3' AND gender='M' AND number='S' AND verb_form IS NULL"
        " AND IFNULL(voice,'ACT')='ACT' ORDER BY surah, ayah LIMIT 1",
        (root, aspect)).fetchone()
    return r[0] if r else None


def bab_roots(cur):
    """Group the sound form-I roots into the six abwab by their vowels.

    Only salim roots are classified: in a weak root the vowel of the cayn is
    obscured by the very changes chapter 9 describes, so reading a bab off it
    would be guesswork."""
    found = {k: [] for k in BAB_NAMES}
    # fetchall first: bare_3ms runs on the same cursor, and iterating a cursor
    # while re-executing it silently truncates the outer result set
    candidates = cur.execute(
        "SELECT root_ar, COUNT(*) n FROM corpus WHERE pos='V' AND verb_form IS NULL"
        " AND LENGTH(root_ar)=3 AND root_ar != '' GROUP BY root_ar ORDER BY n DESC"
    ).fetchall()
    for root, n in candidates:
        if classify(root) != "salim":
            continue
        m, i = bare_3ms(cur, root, "PERF"), bare_3ms(cur, root, "IMPF")
        if not (m and i):
            continue
        vm, vi = ayn_vowel(m, root), ayn_vowel(i, root)
        if (vm, vi) in found:
            found[(vm, vi)].append((root, repair_markers(m), repair_markers(i), n))
    return found


def fullest(cur, roots, form=None):
    """Of these roots, the one the Quran conjugates most fully: first by how
    many of the three tenses it attests at all, then by how many persons."""
    best = None
    for root, n in roots:
        par = paradigm(cur, root, form)
        if not par:
            continue
        score = (len({a for a, _ in par}), len(par))
        if best is None or score > best[0]:
            best = (score, root, n, par)
    return best


ATTESTED_FORMS = ["II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XII"]


def form_paradigms(cur, markdown=False):
    """One conjugation per derived form, from the root the Quran conjugates
    most fully in it. Form I has the paradigms of chapter 10 and the six abwab
    below; these are the mazid patterns, whose prefix vowel (yu-, not ya-) and
    whose imperative are what the learner needs to see side by side."""
    for form in ATTESTED_FORMS:
        roots = cur.execute(
            "SELECT root_ar, COUNT(*) n FROM corpus WHERE pos='V' AND verb_form=?"
            " AND root_ar IS NOT NULL AND root_ar != '' GROUP BY root_ar"
            " ORDER BY n DESC LIMIT 15", (form,)).fetchall()
        # a sound root shows the pattern of the form; a weak one shows the
        # pattern plus the changes of chapter 9 on top of it, which is not
        # what this table is for. Fall back only when no sound root carries
        # the form well enough to be worth printing.
        sound = [(r, n) for r, n in roots if classify(r) == "salim"]
        best = fullest(cur, sound, form)
        if not best or best[0][0] < 2:
            best = fullest(cur, roots, form) or best
        if not best:
            continue
        (_, cells), root, n, par = best
        total = cur.execute("SELECT COUNT(*) FROM corpus WHERE pos='V' AND verb_form=?",
                            (form,)).fetchone()[0]
        lemma = lemma_of(cur, root, form)
        kind = TYPE_NL[classify(root)].split(" — ")[0]
        head = (f"**Vorm {form} — {root}** · {lemma} · {kind} · {n}× voor deze "
                f"wortel, {total}× voor de vorm · {cells} cellen")
        plain = (f"  vorm {form}  {root} ({lemma}, {kind})  {n}x van {total}x, "
                 f"{cells} cellen")
        render(par, head, plain, markdown)


def bab_paradigms(cur, markdown=False):
    """One conjugation per bab of form I, from the sound root the Quran
    conjugates most fully in that bab. Bab 6 has no sound root in this text,
    so it is shown with the mithal that does carry it."""
    found = bab_roots(cur)
    for key in sorted(BAB_NAMES, key=lambda k: BAB_NAMES[k][0]):
        num, pattern = BAB_NAMES[key]
        roots = [(r, n) for r, _m, _i, n in found[key]][:10]
        note = ""
        if not roots:
            # waritha / yarithu is bab 6 but a mithal: the waw drops in the
            # present, which is why the sound-root scan cannot see it
            roots, note = [("ورث", 0)], " · mithāl, geen gave wortel in deze tekst"
        best = fullest(cur, roots)
        if not best:
            continue
        (_, cells), root, n, par = best
        lemma = lemma_of(cur, root)
        head = f"**Bāb {num} — {pattern} — {root}** · {lemma} · {cells} cellen{note}"
        plain = f"  bab {num}  {pattern}  {root} ({lemma})  {cells} cellen{note}"
        render(par, head, plain, markdown)


def abwab(cur, markdown=False, per_bab=3):
    """Group the sound form-I roots into the six abwab by their vowels.

    Only salim roots are classified: in a weak root the vowel of the cayn is
    obscured by the very changes chapter 9 describes, so reading a bab off it
    would be guesswork."""
    found = bab_roots(cur)

    if markdown:
        print("| Bāb | Patroon | Wortel | Māḍī | Muḍāriʿ | In de Quran |")
        print("|---|---|---|---|---|---|")
    for key in sorted(BAB_NAMES, key=lambda k: BAB_NAMES[k][0]):
        num, pattern = BAB_NAMES[key]
        examples = found[key][:per_bab]
        if not examples:
            if markdown:
                # the scan covers sound roots only, and one riwaya: bab 6 is
                # empty here but does occur in Hafs with a mithal (waritha /
                # yarithu) and in Warsh with a sound one (hasiba / yahsibu)
                print(f"| {num} | {pattern} | — | — | — | "
                      "niet bij gave wortels |")
            continue
        for root, m, i, n in examples:
            if markdown:
                print(f"| {num} | {pattern} | {root} | {m} | {i} | {n}× |")
            else:
                print(f"  bab {num} {pattern:<16} {root:<5} {m:<12} {i:<12} {n}x")
    return found


# ------------------------------------------------------- de verbale vormen

# Every pattern the language forms, whether or not the Quran uses it. The
# example is filled from the corpus where the form occurs; the ones the Quran
# does not use carry an example from the language, marked as such.
FORMS = [
    ("I", "فَعَلَ", "grondvorm", None),
    ("II", "فَعَّلَ", "intensief, causatief", None),
    ("III", "فَاعَلَ", "gericht op een ander", None),
    ("IV", "أَفْعَلَ", "causatief", None),
    ("V", "تَفَعَّلَ", "wederkerend van II", None),
    ("VI", "تَفَاعَلَ", "wederkerend van III", None),
    ("VII", "ٱنْفَعَلَ", "lijdend, vanzelf", None),
    ("VIII", "ٱفْتَعَلَ", "wederkerend, voor zichzelf", None),
    ("IX", "ٱفْعَلَّ", "kleuren en gebreken", None),
    ("X", "ٱسْتَفْعَلَ", "vragen om, achten als", None),
    ("XI", "ٱفْعَالَّ", "versterkte kleur", "ٱحْمَارَّ — diep rood worden"),
    ("XII", "ٱفْعَوْعَلَ", "intensief", None),
    ("XIII", "ٱفْعَوَّلَ", "intensief", "ٱجْلَوَّذَ — voortjagen"),
    ("XIV", "ٱفْعَنْلَلَ", "zeldzaam", "ٱقْعَنْسَسَ — achteroverleunen"),
    ("XV", "ٱفْعَنْلَى", "zeldzaam", "ٱسْلَنْقَىٰ — op de rug liggen"),
]


def verb_forms(cur, markdown=False):
    if markdown:
        print("| Vorm | Patroon | Betekenis (hoofdlijn) | Voorbeeld | Vers | Aantal |")
        print("|---|---|---|---|---|---|")
    for form, pattern, sense, fallback in FORMS:
        where = "verb_form IS NULL" if form == "I" else "verb_form = ?"
        args = () if form == "I" else (form,)
        row = cur.execute(
            "SELECT lemma_ar, surah, ayah, COUNT(*) OVER () FROM corpus"
            f" WHERE pos='V' AND {where} AND lemma_ar != ''"
            " ORDER BY surah, ayah LIMIT 1", args).fetchone()
        total = cur.execute(
            f"SELECT COUNT(*) FROM corpus WHERE pos='V' AND {where}", args).fetchone()[0]
        if row and total:
            example, ref, n = repair_markers(row[0]), f"{row[1]}:{row[2]}", f"{total}×"
        else:
            example, ref, n = (fallback or "—"), "—", "niet in de Quran"
        if markdown:
            print(f"| {form} | {pattern} | {sense} | {example} | {ref} | {n} |")
        else:
            print(f"  {form:<5} {pattern:<14} {example:<22} {ref:<8} {n}")


def quadriliteral(cur, markdown=False):
    if markdown:
        print("| Vorm | Patroon | Voorbeeld | Vers | Aantal |")
        print("|---|---|---|---|---|")
    rows = cur.execute(
        "SELECT lemma_ar, root_ar, surah, ayah, COUNT(*) n FROM corpus"
        " WHERE pos='V' AND LENGTH(root_ar)=4 AND lemma_ar != ''"
        " GROUP BY root_ar ORDER BY n DESC LIMIT 6").fetchall()
    for lemma, root, s, a, n in rows:
        if markdown:
            print(f"| mujarrad | فَعْلَلَ | {repair_markers(lemma)} ({root}) | {s}:{a} | {n}× |")
        else:
            print(f"  {root:<6} {repair_markers(lemma):<14} {s}:{a}  {n}x")
    if markdown:
        for pattern, ex in (("تَفَعْلَلَ", "تَدَحْرَجَ — rollen"),
                            ("ٱفْعَنْلَلَ", "ٱحْرَنْجَمَ — samendrommen"),
                            ("ٱفْعَلَلَّ", "ٱطْمَأَنَّ — tot rust komen")):
            print(f"| mazīd | {pattern} | {ex} | — | zie hieronder |")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    markdown = "--markdown" in sys.argv
    cur = sqlite3.connect(DB).cursor()
    modes = {"abwab": abwab, "forms": verb_forms, "quad": quadriliteral,
             "form-paradigms": form_paradigms, "bab-paradigms": bab_paradigms}
    if args and args[0] in modes:
        modes[args[0]](cur, markdown)
        return
    by_type = roots_by_type(cur)
    wanted = args or TYPES
    for t in wanted:
        if t not in TYPES:
            sys.exit("onbekend type: %s (kies uit %s)" % (t, ", ".join(TYPES)))
        show(cur, t, by_type[t], markdown)


if __name__ == "__main__":
    main()
