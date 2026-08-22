#!/usr/bin/env python3
"""Which sarf forms does Warsh use that the Hafs text does not?

The textbook in docs/sarf-nl.md counts forms from the corpus, and the corpus
analyses one riwaya: Hafs. A farsh difference can change the wazn of a word --
Hafs reads talqafu (form I) where Warsh reads talaqqafu (form V) -- so the
question is whether Warsh puts a root into a form the Hafs text never uses.

Two levels, and they answer differently:

  the fifteen forms   No. Warsh uses I, II, III, IV, V, VI, VIII and X, all
                      of them already abundant in Hafs. No wazn enters or
                      leaves the Quran with the riwaya.
  root plus form      Yes. Fourteen (root, form) pairs occur in Warsh that
                      the Hafs text has nowhere, in any part of speech.

One caveat on the Hafs column: the corpus writes no verb_form for form I, so
a blank reads as I here. That is right everywhere but 4:42, where tusawwaa is
form II in the passive and the corpus leaves it unannotated. It does not touch
the conclusion, since form V of that root is absent from Hafs either way.

WAZN below is this project's reading of the Warsh form, word by word: the
corpus annotates Hafs only, so nothing states the Warsh form and it had to be
read off the vowelling. The Hafs form beside it comes from the corpus, and
whether the pair is attested is a query, not a judgment -- so the claim that
matters, "this form does not occur in Hafs", is checkable even where the
reading of the Warsh form is disputed.

Beside the wazn there is the *bab*: within form I the six abwab differ only
in the vowel on the ayn, and a farsh difference can move a verb from one to
another. BAB lists those. Two of them matter to the textbook. The grammars
name the sixth bab after hasiba / yahsibu, and Hafs reads that verb yahsabu,
which is the fourth -- so with a sound root the sixth bab is absent from the
Hafs text and present in Warsh, 28 times. And the fifth bab, which the Hafs
text uses for one verb only, gains a second in Warsh at 27:22.

  python3 riwaya_sarf.py              the full table
  python3 riwaya_sarf.py --only       the forms peculiar to one riwaya, both ways
  python3 riwaya_sarf.py --bab        the bab differences within form I
  python3 riwaya_sarf.py --markdown   the table as it appears in the textbook
"""

import argparse
import re
import sqlite3
import unicodedata
from pathlib import Path

from add_metadata import repair_markers
from riwaya_translit import key

HERE = Path(__file__).parent
DB = HERE / "quran.db"

# (surah, ayah, root, form in Warsh). The Hafs form is read from the corpus.
# Only places where the wazn itself changes: differences of voice, mood,
# person or bab are farsh too but leave the form alone, and are not listed.
WAZN = [
    (2, 10, "كذب", "II"), (2, 132, "وصي", "IV"), (3, 79, "علم", "I"),
    (3, 146, "قتل", "I"), (3, 176, "حزن", "IV"), (4, 33, "عقد", "III"),
    (4, 42, "سوي", "V"), (4, 128, "صلح", "VI"), (4, 154, "عدو", "VIII"),
    (5, 41, "حزن", "IV"), (6, 33, "كذب", "IV"), (6, 33, "حزن", "IV"),
    (6, 64, "نجو", "IV"), (6, 119, "ضلل", "I"), (7, 117, "لقف", "V"),
    (7, 127, "قتل", "I"), (7, 141, "قتل", "I"), (7, 193, "تبع", "I"),
    (7, 202, "مدد", "IV"), (8, 11, "غشو", "IV"), (9, 110, "قطع", "II"),
    (10, 65, "حزن", "IV"), (10, 88, "ضلل", "I"), (10, 103, "نجو", "II"),
    (11, 28, "عمي", "I"), (12, 13, "حزن", "IV"), (12, 110, "نجو", "IV"),
    (13, 39, "ثبت", "II"), (15, 8, "نزل", "V"), (16, 66, "سقي", "I"),
    (17, 90, "فجر", "II"), (18, 81, "بدل", "II"), (18, 85, "تبع", "VIII"),
    (18, 89, "تبع", "VIII"), (18, 92, "تبع", "VIII"), (19, 25, "سقط", "VI"),
    (20, 61, "سحت", "I"), (20, 69, "لقف", "V"), (22, 31, "خطف", "V"),
    (23, 21, "سقي", "I"), (23, 67, "هجر", "IV"), (25, 67, "قتر", "IV"),
    (26, 45, "لقف", "V"), (26, 224, "تبع", "I"), (27, 87, "اتي", "IV"),
    (30, 39, "ربو", "IV"), (31, 18, "صعر", "III"), (31, 23, "حزن", "IV"),
    (33, 4, "ظهر", "V"), (33, 14, "اتي", "I"), (36, 68, "نكس", "I"),
    (36, 76, "حزن", "IV"), (37, 8, "سمع", "I"), (39, 71, "فتح", "II"),
    (39, 73, "فتح", "II"), (43, 18, "نشا", "I"), (43, 19, "شهد", "IV"),
    (47, 4, "قتل", "III"), (58, 2, "ظهر", "V"), (58, 3, "ظهر", "V"),
    (58, 10, "حزن", "IV"), (66, 5, "بدل", "II"), (68, 32, "بدل", "II"),
    (68, 51, "زلق", "I"), (84, 12, "صلي", "II"), (89, 18, "حضض", "I"),
    # not a verb: Hafs reads the participle of IV, Warsh that of II
    (8, 18, "وهن", "II"),
]

# Form I keeps its wazn but not its bab: the vowel on the ayn is what the six
# abwab of the thulathi mujarrad are told apart by, and a farsh difference can
# move a verb from one to another. (verse, root, bab in Hafs, bab in Warsh)
BAB = [
    (2, 273, "حسب", 4, 6), (3, 78, "حسب", 4, 6), (3, 169, "حسب", 4, 6),
    (3, 178, "حسب", 4, 6), (3, 180, "حسب", 4, 6), (3, 188, "حسب", 4, 6),
    (7, 30, "حسب", 4, 6), (8, 59, "حسب", 4, 6), (14, 42, "حسب", 4, 6),
    (14, 47, "حسب", 4, 6), (18, 18, "حسب", 4, 6), (18, 104, "حسب", 4, 6),
    (23, 55, "حسب", 4, 6), (24, 11, "حسب", 4, 6), (24, 15, "حسب", 4, 6),
    (24, 39, "حسب", 4, 6), (24, 57, "حسب", 4, 6), (25, 44, "حسب", 4, 6),
    (27, 88, "حسب", 4, 6), (33, 20, "حسب", 4, 6), (43, 37, "حسب", 4, 6),
    (43, 80, "حسب", 4, 6), (58, 18, "حسب", 4, 6), (59, 14, "حسب", 4, 6),
    (63, 4, "حسب", 4, 6), (90, 5, "حسب", 4, 6), (90, 7, "حسب", 4, 6),
    (104, 3, "حسب", 4, 6),
    (3, 157, "موت", 1, 4), (3, 158, "موت", 1, 4),   # maata / mitta, ajwaf
    (27, 22, "مكث", 1, 5),                          # makatha / makutha
    (43, 57, "صدد", 2, 1),                          # yasiddoena / yasoeddoena
    (44, 47, "عتل", 2, 1),                          # i'tiloehoe / u'tuloehoe
    (75, 7, "برق", 4, 3),                           # bariqa / baraqa
]


def attested(cur, root, form):
    """How often the Hafs corpus has this root in this form, any part of
    speech -- a participle of form VI counts as the form occurring."""
    if form == "I":
        return cur.execute(
            "SELECT COUNT(*) FROM corpus WHERE root_ar = ? AND verb_form IS NULL"
            " AND pos IS NOT NULL", (root,)).fetchone()[0]
    return cur.execute("SELECT COUNT(*) FROM corpus WHERE root_ar = ? AND verb_form = ?",
                       (root, form)).fetchone()[0]


VOWELS = set("auiAUIN")


def shape(word):
    # the words view passes the corpus' leftover Buckwalter markers through
    # unmapped, so repair them before the word can be matched on its letters
    return "".join(ch for ch in key(repair_markers(word)) if ch not in VOWELS)


def word_pair(cur, surah, ayah, root):
    """The two readings of the word this row is about: the farsh difference in
    the verse whose Hafs side is the word carrying this root."""
    forms = [w for (w,) in cur.execute(
        "SELECT w.word_ar FROM words w JOIN corpus c ON c.surah = w.surah"
        " AND c.ayah = w.ayah AND c.word = w.word WHERE w.surah = ? AND w.ayah = ?"
        " AND c.root_ar = ?", (surah, ayah, root))]
    want = {shape(f) for f in forms}
    # riwaya_diff now holds ten pairs; this file is about Hafs and Warsh
    for a, b in cur.execute("SELECT form_a, form_b FROM riwaya_diff WHERE surah = ?"
                            " AND ayah_a = ? AND kind = 'farsh'"
                            " AND riwaya_a = 'hafs' AND riwaya_b = 'warsh'",
                            (surah, ayah)):
        if shape(a) in want:
            return a, b
    return None, None


def only_in_hafs(cur, data):
    """(root, form) pairs the Hafs text has and the Warsh text has not.

    The mirror of the n_hafs column, and it has to be computed differently:
    nothing annotates Warsh, so the test is whether every place that root
    stands in that form in Hafs is a place where Warsh reads it otherwise.
    Where that holds, the form leaves the text with the riwaya."""
    elsewhere = {}
    changed = {}
    for r in data:
        changed.setdefault(r["root"], set()).add((r["surah"], r["ayah"]))
    for r in data:
        if r["hafs"] == "I":
            places = cur.execute(
                "SELECT surah, ayah FROM corpus WHERE root_ar = ? AND verb_form IS NULL"
                " AND pos IS NOT NULL", (r["root"],)).fetchall()
        else:
            places = cur.execute("SELECT surah, ayah FROM corpus WHERE root_ar = ?"
                                 " AND verb_form = ?", (r["root"], r["hafs"])).fetchall()
        rest = [p for p in places if tuple(p) not in changed[r["root"]]]
        if not rest:
            elsewhere.setdefault((r["root"], r["hafs"]), []).append(r)
    return elsewhere


def rows(cur):
    out = []
    for surah, ayah, root, warsh_form in WAZN:
        # prefer the verb: a verse can hold a noun of the same root
        hafs_form = cur.execute(
            "SELECT verb_form FROM corpus WHERE surah = ? AND ayah = ? AND root_ar = ?"
            " AND pos IS NOT NULL ORDER BY (pos = 'V') DESC LIMIT 1",
            (surah, ayah, root)).fetchone()
        out.append(dict(surah=surah, ayah=ayah, root=root,
                        hafs=(hafs_form[0] if hafs_form and hafs_form[0] else "I"),
                        warsh=warsh_form,
                        n_hafs=attested(cur, root, warsh_form),
                        pair=word_pair(cur, surah, ayah, root)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", "--new", action="store_true", dest="only",
                    help="the forms peculiar to one riwaya, in both directions")
    ap.add_argument("--bab", action="store_true",
                    help="the bab differences within form I")
    ap.add_argument("--markdown", action="store_true", help="print the textbook table")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = conn.cursor()

    if args.bab:
        by = {}
        for surah, ayah, root, h, w in BAB:
            by.setdefault((root, h, w), []).append("%d:%d" % (surah, ayah))
        print("%-6s %-6s %-7s %5s  %s" % ("wortel", "hafs", "warsh", "n", "plaatsen"))
        for (root, h, w), places in sorted(by.items(), key=lambda x: -len(x[1])):
            print("%-6s baab %-1d baab %-1d %5d  %s"
                  % (root, h, w, len(places),
                     ", ".join(places[:6]) + (" ..." if len(places) > 6 else "")))
        six = sum(1 for *_, w in BAB if w == 6)
        print("\n%d plaatsen waar de baab verschilt; %d daarvan zetten een gave"
              % (len(BAB), six))
        print("wortel in baab 6, die de Hafs-tekst bij gave wortels niet gebruikt.")
        conn.close()
        return

    data = rows(cur)
    new = [r for r in data if r["n_hafs"] == 0]
    mirror = only_in_hafs(cur, data)

    if args.markdown:
        print("**Alleen in de riwaaya van Warsh** — %d plaatsen, %d wortel-vormparen\n"
              % (len(new), len({(r["root"], r["warsh"]) for r in new})))
        print("| Vers | Wortel | Ḥafṣ leest | vorm | Warsh leest | vorm |")
        print("|---|---|---|---|---|---|")
        for r in sorted(new, key=lambda x: (x["surah"], x["ayah"])):
            print("| %d:%d | %s | %s | %s | %s | **%s** |"
                  % (r["surah"], r["ayah"], r["root"], r["pair"][0] or "",
                     r["hafs"], r["pair"][1] or "", r["warsh"]))
        print("\n**Alleen in de riwaaya van Ḥafṣ** — %d plaatsen, %d wortel-vormparen\n"
              % (sum(len(v) for v in mirror.values()), len(mirror)))
        print("| Vers | Wortel | Ḥafṣ leest | vorm | Warsh leest | vorm |")
        print("|---|---|---|---|---|---|")
        for (root, form), rs in sorted(mirror.items(),
                                       key=lambda x: (x[1][0]["surah"], x[1][0]["ayah"])):
            r = rs[0]
            plaatsen = ", ".join("%d:%d" % (x["surah"], x["ayah"]) for x in rs)
            print("| %s | %s | %s | **%s** | %s | %s |"
                  % (plaatsen, root, r["pair"][0] or "", form,
                     r["pair"][1] or "", r["warsh"]))
        conn.close()
        return

    if args.only:
        print("Vormen die maar in een van beide riwaayaat staan.")
        print("Beide zijn Qoeraan; dit is geen lijst van afwijkingen.\n")
        print("alleen in Warsh (%d plaatsen, %d wortel-vormparen):"
              % (len(new), len({(r["root"], r["warsh"]) for r in new})))
        for r in sorted(new, key=lambda x: (x["surah"], x["ayah"])):
            print("  %-9s %-6s Hafs %-4s -> Warsh %-4s   %s | %s"
                  % ("%d:%d" % (r["surah"], r["ayah"]), r["root"], r["hafs"],
                     r["warsh"], r["pair"][0] or "", r["pair"][1] or ""))
        print("\nalleen in Hafs (%d plaatsen, %d wortel-vormparen):"
              % (sum(len(v) for v in mirror.values()), len(mirror)))
        for (root, form), rs in sorted(mirror.items(),
                                       key=lambda x: (x[1][0]["surah"], x[1][0]["ayah"])):
            r = rs[0]
            plaatsen = ", ".join("%d:%d" % (x["surah"], x["ayah"]) for x in rs)
            print("  %-9s %-6s Hafs %-4s -> Warsh %-4s   %s | %s"
                  % (plaatsen, root, form, r["warsh"],
                     r["pair"][0] or "", r["pair"][1] or ""))
        conn.close()
        return

    print("%-9s %-6s %-6s %-6s %s" % ("vers", "wortel", "hafs", "warsh", "in hafs"))
    for r in sorted(data, key=lambda x: (x["surah"], x["ayah"])):
        print("%-9s %-6s %-6s %-6s %5d%s"
              % ("%d:%d" % (r["surah"], r["ayah"]), r["root"], r["hafs"], r["warsh"],
                 r["n_hafs"], "   <-- niet in Hafs" if r["n_hafs"] == 0 else ""))
    print("\n%d plaatsen waar de wazn verschilt. %d daarvan zetten een wortel in een"
          % (len(data), len(new)))
    print("vorm die de Hafs-tekst nergens heeft (%d wortel-vormparen); omgekeerd staan"
          % len({(r["root"], r["warsh"]) for r in new}))
    print("%d wortel-vormparen alleen in Hafs. Geen van beide riwaayaat kent een wazn"
          % len(mirror))
    order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    print("die de ander mist: het zijn aan weerskanten de vormen %s."
          % ", ".join(sorted({r["warsh"] for r in data}, key=order.index)))
    conn.close()


if __name__ == "__main__":
    main()
