#!/usr/bin/env python3
"""Substantiate unresolved Ibn al-Jawzi citations from the second,
independent digitization of the same work (the JK edition in OpenITI).

The Shamela and JK editions were typed independently from different print
editions, so their corruptions do not overlap: a quote that is garbled or
truncated in one is usually intact in the other. This script extracts every
quoted span from the JK edition, resolves each against the corpus with the
same resolver, and then matches still-unresolved Shamela quotes to their JK
counterpart by skeleton-word overlap, adopting its verse reference with
status 'edition_jk'.

Updates sources/resolved_citations.json in place.
"""

import json
import re
from pathlib import Path

import resolve_citations as rc

HERE = Path(__file__).parent
JK = HERE / "sources" / "ibnjawzi_nuzhat_jk.txt"


def jk_quotes():
    lines = []
    for ln in JK.read_text(encoding="utf-8").splitlines():
        if ln.startswith("#META#") or ln.startswith("######") or not ln.strip():
            continue
        if not ln.startswith("###"):
            ln = ln.removeprefix("# ").removeprefix("#").removeprefix("~~")
        lines.append(ln.strip())
    text = " ".join(lines)
    text = re.sub(r"PageV\d+P\d+", " ", text)
    text = re.sub(r"\( ?\d+ / [ء-يa-z] ?\)", " ", text)
    text = re.sub(r"\bms\d+\b", " ", text)
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text)
    # the JK edition marks Quran quotes explicitly as @QB@ ... @QE@
    return [m.group(1).strip()
            for m in re.finditer(r"@QB@ (.{4,200}?) @QE@", text)]


def main():
    verses = rc.load_verses()
    skel_verses = {k: rc.skeleton(v) for k, v in verses.items()}
    concat = rc.build_sura_concat(skel_verses)
    word_idx = rc.build_word_index(skel_verses)

    resolved_jk = []
    for q in jk_quotes():
        qn = rc.normalize(q)
        refs, status = rc.resolve_quote(qn, verses, skel_verses, concat,
                                        word_idx, set())
        if refs and status in ("unique", "cross_verse", "prefix"):
            resolved_jk.append((set(rc.skeleton(qn).split()), refs))
    print(f"JK edition: {len(resolved_jk)} independently resolved quotes")

    path = HERE / "sources" / "resolved_citations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    fixed = 0
    remaining = 0
    for e in data["ibnjawzi"] + data["damaghani"] + data["ibnsallam"]:
        for sense in e["senses"]:
            for q in sense["quotes"]:
                if q["status"] not in ("no_match", "too_short"):
                    continue
                qwords = set(rc.skeleton(rc.normalize(q["quote"])).split())
                if not qwords:
                    remaining += 1
                    continue
                best, best_ov = None, 0.0
                for jwords, refs in resolved_jk:
                    ov = len(qwords & jwords) / len(qwords)
                    if ov > best_ov:
                        best, best_ov = refs, ov
                if best and best_ov >= 0.6:
                    q["status"] = "edition_jk"
                    q["refs"] = [f"{s}:{a}" for s, a in best][:10]
                    fixed += 1
                else:
                    remaining += 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"substantiated from JK edition: {fixed}, still unresolved: {remaining}")


if __name__ == "__main__":
    main()
