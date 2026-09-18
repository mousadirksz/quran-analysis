#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests voor de twee gebruikersgezichten: query.py en app.py.

De rest van de repo toetst de data en de scripts die haar bouwen. Deze twee
zijn wat iemand áánraakt, en ze hadden niets. Wat er in elk van beide stuk kan
gaan is verschillend, dus ze worden verschillend getoetst.

`query.py` is een proces. Het wordt gestart zoals een gebruiker het start, en
wat het op stdout zet is de verwachting: de kopregel, de RTL-markering om
Arabisch heen, "Geen resultaten." bij een lege uitkomst, en een leesbare
melding in plaats van een traceback bij een typefout in de SQL.

`app.py` is een Streamlit-dashboard, en Streamlit draaien in een test is meer
moeite dan het waard is. Wat er wél stilletjes breekt is de SQL: het dashboard
bevraagt zestien keer de database, en een kolom die hernoemd wordt valt pas op
als iemand de pagina opent. Dit bestand leest app.py met `ast` -- dus zonder
hem uit te voeren en zonder dat Streamlit geinstalleerd hoeft te zijn -- haalt
elke `sql(...)`-aanroep met een letterlijke query eruit, en draait die tegen
quran.db.

Wat dat níet dekt, zodat de PASS-regel niet voor meer wordt gelezen dan hij
zegt: de pandas-laag (`pd.read_sql_query`), de Streamlit-widgets, en of de
pagina er goed uitziet. Alleen dat elke kolom die het dashboard opvraagt nog
bestaat.

    python3 test_ui.py        een regel per fout
    python3 test_ui.py -v     ook de geslaagde gevallen, met hun reden
"""
import ast
import io
import sqlite3
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "quran.db"
RTL = "‏"

# (argumenten, verwachte exitcode, moet erin staan, mag er niet in staan, waarom)
QUERY = [
    ([], 1, ["Gebruik:", "Voorbeeld:"], ["Traceback"],
     "zonder argumenten hoort hij uit te leggen hoe het moet, en niet te vallen"),
    (["SELECT surah, ayah FROM verses WHERE surah=112"], 0,
     ["surah", "ayah", "(4 rijen)"], ["Traceback"],
     "kopregel uit de kolomnamen, en het aantal rijen eronder"),
    (["SELECT * FROM verses WHERE surah=999"], 0, ["Geen resultaten."], ["rijen)"],
     "een lege uitkomst is geen fout en krijgt geen kopregel"),
    (["SELECT text_ar FROM verses WHERE surah=112 AND ayah=1"], 0, [RTL], ["Traceback"],
     "Arabisch krijgt een RTL-markering, anders loopt de terminal de tekst omgekeerd af"),
    (["SELECT surah FROM verses WHERE surah=112 AND ayah=1"], 0, ["112"], [RTL],
     "een getal krijgt die markering juist niet"),
    (["SELECT root_ar FROM corpus WHERE root_ar IS NULL LIMIT 1"], 0, [], ["None"],
     "NULL wordt leeg getoond en niet als het Python-woord None"),
    (["SELECT nietbestaand FROM verses"], 1, ["SQL-fout", "no such column"], ["Traceback"],
     "een typefout aan de prompt is het gewoonste dat er is; de melding van "
     "sqlite is het nuttige deel, de traceback niet"),
]


def sql_uit_app():
    """Elke sql(...)-aanroep in app.py met een letterlijke query.

    Met ast, dus app.py wordt gelezen en niet uitgevoerd: Streamlit hoeft niet
    geinstalleerd te zijn en er wordt geen dashboard opgestart.
    """
    boom = ast.parse(io.open(str(HERE / "app.py"), encoding="utf-8").read())
    gedefinieerd = {n.name for n in ast.walk(boom)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    uit = []
    for n in ast.walk(boom):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "sql" and n.args
                and isinstance(n.args[0], ast.Constant)
                and isinstance(n.args[0].value, str)):
            uit.append((n.lineno, n.args[0].value))
    return sorted(uit), gedefinieerd


def test_query(meld):
    for args, code, moet, mag_niet, waarom in QUERY:
        r = subprocess.run([sys.executable, str(HERE / "query.py")] + args,
                           capture_output=True, text=True)
        uit = r.stdout + r.stderr
        naam = "query.py " + (repr(args[0])[:44] if args else "(zonder argumenten)")
        goed = r.returncode == code
        meld(goed, naam + " geeft exitcode %d" % code, waarom,
             "" if goed else "kreeg %d" % r.returncode)
        for s in moet:
            meld(s in uit, naam + " toont %r" % s, waarom,
                 "" if s in uit else "ontbreekt in: %r" % uit[:120])
        for s in mag_niet:
            meld(s not in uit, naam + " toont geen %r" % s, waarom,
                 "" if s not in uit else "staat wel in: %r" % uit[:120])


def test_app_sql(meld):
    vragen, gedefinieerd = sql_uit_app()
    # Alleen de aanroepen tellen is niet genoeg: hernoem de `def sql` en de
    # aanroepen blijven staan, terwijl het dashboard bij de eerste query valt.
    meld("sql" in gedefinieerd, "app.py definieert de helper `sql`",
         "de aanroepen hieronder verwijzen ernaar; bestaat hij niet, dan valt "
         "het dashboard op zijn eerste query",
         "" if "sql" in gedefinieerd else "gedefinieerd: %s" % sorted(gedefinieerd))
    meld(len(vragen) > 10, "app.py bevraagt de database %d keer" % len(vragen),
         "als dit er ineens nul zijn, is de helper hernoemd en toetst dit "
         "bestand niets meer", "" if len(vragen) > 10 else "gevonden: %d" % len(vragen))
    conn = sqlite3.connect(str(DB))
    wortel = conn.execute(
        "SELECT root_ar FROM corpus WHERE root_ar IS NOT NULL LIMIT 1").fetchone()[0]
    for lineno, q in vragen:
        params = [wortel] if "root_ar = ?" in q else [1] * q.count("?")
        kort = " ".join(q.split())[:56]
        try:
            conn.execute(q, params).fetchall()
            meld(True, "app.py:%d" % lineno, kort, "")
        except sqlite3.Error as e:
            meld(False, "app.py:%d" % lineno, kort, str(e))
    conn.close()


def main():
    if not DB.exists():
        print("quran.db ontbreekt")
        return 1
    gelukt = mislukt = 0
    breedvoerig = "-v" in sys.argv or "--verbose" in sys.argv

    def meld(goed, wat, waarom, detail):
        nonlocal gelukt, mislukt
        if goed:
            gelukt += 1
            if breedvoerig:
                print("PASS  %s" % wat)
                print("      %s" % waarom)
        else:
            mislukt += 1
            print("FAIL  %s" % wat)
            print("      %s" % waarom)
            if detail:
                print("      %s" % detail)

    for test in (test_query, test_app_sql):
        test(meld)

    print("%d tests op query.py en app.py: %d geslaagd, %d gefaald"
          % (gelukt + mislukt, gelukt, mislukt))
    return 1 if mislukt else 0


if __name__ == "__main__":
    sys.exit(main())
