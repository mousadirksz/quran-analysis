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

  python3 riwaya_sarf.py              the full table
  python3 riwaya_sarf.py --new        only what Hafs does not have
  python3 riwaya_sarf.py --markdown   the table as it appears in the textbook
"""

import argparse
import re
import sqlite3
import unicodedata
from pathlib import Path

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
    return "".join(ch for ch in key(word) if ch not in VOWELS)


def word_pair(cur, surah, ayah, root):
    """The two readings of the word this row is about: the farsh difference in
    the verse whose Hafs side is the word carrying this root."""
    forms = [w for (w,) in cur.execute(
        "SELECT w.word_ar FROM words w JOIN corpus c ON c.surah = w.surah"
        " AND c.ayah = w.ayah AND c.word = w.word WHERE w.surah = ? AND w.ayah = ?"
        " AND c.root_ar = ?", (surah, ayah, root))]
    want = {shape(f) for f in forms}
    for a, b in cur.execute("SELECT form_a, form_b FROM riwaya_diff WHERE surah = ?"
                            " AND ayah_a = ? AND kind = 'farsh'", (surah, ayah)):
        if shape(a) in want:
            return a, b
    return None, None


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
    ap.add_argument("--new", action="store_true", help="only the unattested forms")
    ap.add_argument("--markdown", action="store_true", help="print the textbook table")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    cur = conn.cursor()
    data = rows(cur)
    new = [r for r in data if r["n_hafs"] == 0]

    if args.markdown:
        print("| Vers | Wortel | Ḥafṣ leest | vorm | Warsh-vorm | Warsh leest |")
        print("|---|---|---|---|---|---|")
        for r in sorted(new, key=lambda x: (x["surah"], x["ayah"])):
            print("| %d:%d | %s | %s | %s | **%s** | %s |"
                  % (r["surah"], r["ayah"], r["root"], r["pair"][0] or "",
                     r["hafs"], r["warsh"], r["pair"][1] or ""))
        conn.close()
        return

    shown = new if args.new else data
    print("%-9s %-6s %-6s %-6s %s" % ("vers", "wortel", "hafs", "warsh", "in hafs"))
    for r in sorted(shown, key=lambda x: (x["surah"], x["ayah"])):
        print("%-9s %-6s %-6s %-6s %5d%s"
              % ("%d:%d" % (r["surah"], r["ayah"]), r["root"], r["hafs"], r["warsh"],
                 r["n_hafs"], "   <-- niet in Hafs" if r["n_hafs"] == 0 else ""))
    print("\n%d plaatsen waar de wazn verandert; %d daarvan zetten de wortel in een"
          % (len(data), len(new)))
    print("vorm die het Hafs-corpus nergens heeft (%d verschillende wortel-vormparen)."
          % len({(r["root"], r["warsh"]) for r in new}))
    order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    forms_w = sorted({r["warsh"] for r in data}, key=order.index)
    print("Warsh gebruikt hier de vormen %s: geen enkele wazn komt met de riwaya"
          % ", ".join(forms_w))
    print("de Quran binnen of verlaat hem.")
    conn.close()


if __name__ == "__main__":
    main()
