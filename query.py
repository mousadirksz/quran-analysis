#!/usr/bin/env python3
"""
Query quran.db from the command line with proper Arabic (RTL) display.

Usage:
    python3 query.py "SELECT verse_ar FROM ayat WHERE surah=1"
    python3 query.py "SELECT * FROM corpus WHERE root_ar='رحم' LIMIT 10"
"""

import sqlite3
import sys
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Gebruik: python3 query.py \"SQL QUERY\"")
        print("Voorbeeld: python3 query.py \"SELECT verse_ar FROM ayat WHERE surah=1\"")
        sys.exit(1)

    query = sys.argv[1]
    db_path = Path(__file__).parent / "quran.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(query)
        rows = cur.fetchall()
    except sqlite3.Error as e:
        # A typo in the SQL is the most ordinary thing that happens at a
        # prompt, and a traceback is the wrong answer to it: the message
        # sqlite gives ("no such column: x") is the useful part.
        print("SQL-fout: %s" % e, file=sys.stderr)
        conn.close()
        sys.exit(1)

    if not rows:
        print("Geen resultaten.")
        return

    columns = [desc[0] for desc in cur.description]

    # Add RTL mark (U+200F) before Arabic text for better terminal display
    RTL_MARK = "\u200F"

    # Print header
    print("\t".join(columns))
    print("─" * 80)

    for row in rows:
        parts = []
        for col, val in zip(columns, row):
            val = str(val) if val is not None else ""
            # Add RTL mark if the value contains Arabic characters
            if any("\u0600" <= ch <= "\u06FF" or "\u0750" <= ch <= "\u077F" for ch in val):
                val = RTL_MARK + val + RTL_MARK
            parts.append(val)
        print("\t".join(parts))

    print(f"\n({len(rows)} rijen)")
    conn.close()


if __name__ == "__main__":
    main()
