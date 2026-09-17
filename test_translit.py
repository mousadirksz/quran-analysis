#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eenheidstests voor riwaya_translit.translit.

`validate.py` toetst de *database*: 33 controles over wat er in quran.db
staat. Deze toetst de *functie* die die database vult. Dat onderscheid is
niet theoretisch. Drie echte fouten in de transliteratie zijn met de hand
gevonden, nadat ze al in de data zaten:

    U+065C, Shu'ba's imaala-punt, ontbrak in VOWELS   79x de klinker weg
    de zero width joiner en de dotless beh als zetel  woorden vielen niet samen
    alef madda als kale alif met dagger               177 valse verschillen

Samen 344 verschillen die er niet waren. Alle drie waren ze hier in een
regel gevangen.

Geen testraamwerk, net als de rest van deze repo: draaien met

    python3 test_translit.py

Elk geval wijst een woord aan met (pakket, soera, aya, woordnummer) in plaats
van het over te typen; het woord wordt uit sources/riwaya_*.csv geknipt. Dat
is geen omslachtigheid maar de les van deze repo: handgetypt Arabisch is hier
vier keer misgegaan en geknipt Arabisch nul keer. Een verwachting die
verandert omdat de bron verandert, hoort dan ook te falen.
"""
import csv
import io
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from riwaya_translit import translit, PLAIN_WASL

_TEXT = {}


def _load(code):
    """De verzen van een pakket, op (soera, aya). De Hafs-uitgave noemt zijn
    soera-kolom anders dan de andere zeven; verder verschilt er niets."""
    if code not in _TEXT:
        col = "sora" if code == "hafs" else "sura_no"
        rows = {}
        with io.open(str(HERE / "sources" / ("riwaya_%s.csv" % code)),
                     encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                rows[(int(row[col]), int(row["aya_no"]))] = row["aya_text"]
        _TEXT[code] = rows
    return _TEXT[code]


def woord(code, sura, ayah, index):
    """Het zoveelste woord van een vers, zoals dat pakket het schrijft.

    Let op: de acht pakketten tellen de aya's niet altijd hetzelfde -- de
    Maghribi-uitgaven rekenen de basmala in al-Faatiha niet als vers, en
    elders lopen nummeringen een op. Een verwijzing geldt daarom binnen een
    pakket, nooit erover heen; waar twee pakketten hetzelfde woord moeten
    opleveren, staan beide verwijzingen apart in de tabel."""
    return re.split(r"[\s\u00a0]+", _load(code)[(sura, ayah)])[index]


# ---------------------------------------------------------------- vaste waarden
# (pakket, soera, aya, woordnummer, opties, verwachte sleutel, waarom)
VAST = [
    ("hafs", 1, 1, 0, {},
     "\u0628i\u0633\u0645i",
     "bismi: de eenvoudigste keten, klinker voor klinker"),
    ("hafs", 1, 1, 1, {},
     "\u0644\u0644\u0644a\u0647i",
     "de alef wasla valt weg, de shadda verdubbelt de laam"),
    ("hafs", 1, 1, 2, {},
     "\u0644\u0631\u0631a\u062d\u0645A\u0646i",
     "dagger alif als lange a midden in het woord"),
    ("hafs", 1, 5, 0, {},
     "'iyyA\u0643a",
     "hamzat al-qat' op een zetel, plus shadda op de yaa"),
    ("hafs", 6, 19, 2, {},
     "\u0634ay'iN",
     "tanwin kasr, en een hamza zonder klinker ervoor"),
    ("hafs", 112, 4, 2, {},
     "\u0644\u0644a\u0647U",
     "silat al-miim: de kleine waw is een lange u"),
    ("hafs", 112, 4, 2, {'sila': False},
     "\u0644\u0644a\u0647u",
     "dezelfde kleine waw, nu genegeerd"),
    ("soosi", 2, 29, 1, {'plain_wasl': True},
     "\u0642A\u0644",
     "al-Soosi's idghaam kabir eet de eindklinker; de lange a moet blijven staan (dit is de `qaal`-valkuil waar de alif-tak in translit voor waakt)"),
    ("warsh", 2, 52, 2, {},
     "'A\u062aay\u0646A",
     "alef madda, in de Maghribi-mushaf geschreven als kale alif met dagger"),
    ("bazzi", 6, 20, 18, {},
     "'a\u0646\u0646a\u0643u\u0645U",
     "de dotless beh als hamza-zetel: hij draagt geen klank en mag niet als medeklinker in de sleutel belanden"),
]


# ------------------------------------------------------- moeten samenvallen
# Twee pakketten schrijven dezelfde klank anders op. De sleutel hoort dat
# verschil weg te nemen; deed hij dat niet, dan telde de vergelijking een
# spellingsverschil als een verschil in de recitatie.
GELIJK = [
    (("shouba", 6, 76, 4, {}),
     ("hafs", 6, 76, 4, {}),
     "U+065C, Shu'ba's imaala-punt, is de enige klinker op die letter"),
    (("doori", 17, 7, 11, {'plain_wasl': True}),
     ("hafs", 17, 7, 11, {}),
     "de zero width joiner als hamza-zetel, waar Hafs een tatweel gebruikt"),
    (("warsh", 1, 5, 0, {}),
     ("hafs", 1, 6, 0, {}),
     "twee wasl-conventies: teken op een kale alif tegenover de letter alef wasla"),
    (("warsh", 112, 1, 2, {}),
     ("hafs", 112, 1, 2, {}),
     "dezelfde twee conventies, nu op het lidwoord van een verdubbelde laam"),
]


# --------------------------------------------------- mogen juist niet samenvallen
# De tegenproef. Een sleutel die alles gelijkmaakt vangt geen enkele fout,
# dus hoort een echt farsh-verschil te blijven staan.
VERSCHIL = [
    (("warsh", 112, 4, 4, {}),
     ("hafs", 112, 4, 3, {}),
     "kufu'an tegenover kufuwan: een echt farsh-verschil mag niet wegvallen"),
]


# ------------------------------------------------- wat de plain_wasl-vlag doet
# Hoeveel woorden van een pakket een andere sleutel krijgen als de vlag
# aangaat. Gemeten, niet aangenomen -- en het antwoord is niet wat de
# naam PLAIN_WASL doet vermoeden: bij Qaaloon, die in de verzameling zit,
# verandert er niets, en bij Warsh, die er niet in zit, zou er het meest
# veranderen. Zie het commentaar bij test_vlag hieronder.
VLAG = {
    "qaloon": 0,
    "warsh": 1909,
    "doori": 2091,
    "soosi": 2090,
}


# Waar Warsh zou ontsporen als de vlag wel voor hem aanstond. Het woord is
# aliimun, "pijnlijk": een echte hamzat al-qat' op een kale alif. De vlag zou
# die alif voor een wasl-alif aanzien en de hamza opeten.
WARSH_GEEN_VLAG = ("warsh", 2, 9, 8)


def _sleutel(ref):
    code, sura, ayah, index, opts = ref
    return translit(woord(code, sura, ayah, index), **opts)


def _naam(ref):
    return "%s %d:%d w%d" % (ref[0], ref[1], ref[2], ref[3])


def test_vaste_waarden(meld):
    for code, sura, ayah, index, opts, verwacht, waarom in VAST:
        w = woord(code, sura, ayah, index)
        gekregen = translit(w, **opts)
        meld(gekregen == verwacht,
             "%s %d:%d w%d%s" % (code, sura, ayah, index,
                                 "" if not opts else " " + repr(opts)),
             waarom,
             "" if gekregen == verwacht
             else "verwacht %r, gekregen %r" % (verwacht, gekregen))


def test_samenvallen(meld):
    for a, b, waarom in GELIJK:
        ka, kb = _sleutel(a), _sleutel(b)
        meld(ka == kb, "%s == %s" % (_naam(a), _naam(b)), waarom,
             "" if ka == kb else "%r tegenover %r" % (ka, kb))


def test_verschillen(meld):
    for a, b, waarom in VERSCHIL:
        ka, kb = _sleutel(a), _sleutel(b)
        meld(ka != kb, "%s != %s" % (_naam(a), _naam(b)), waarom,
             "" if ka != kb else "allebei %r" % ka)


def test_vlag(meld):
    """Wat plain_wasl doet, per pakket, geteld over de hele tekst.

    Dit is de test die het meest zegt en het minst voor de hand ligt.
    PLAIN_WASL is {qaloon, doori, soosi}, en de docstring van translit legt
    uit dat de vlag een terugval is voor wasl-alifs die zo'n pakket niet
    markeert. Nagemeten klopt dat voor al-Doori en al-Soosi, maar:

      * bij Qaaloon verandert de vlag geen enkel woord. Hij markeert zijn
        wasl-alifs wel. Hem in de verzameling zetten is geen fout maar ook
        geen werk; de docstring noemt hem alsof hij de terugval nodig heeft.
      * bij Warsh zou de vlag het meeste veranderen van alle vier -- en juist
        daarom hoort hij er niet in. Wat hij kaal en ongemarkeerd laat staan
        is hamzat al-qat', geen wasl-alif.

    De getallen staan vast zodat een wijziging aan de alif-takken van
    translit hier opvalt en niet pas in een telling in een boek.
    """
    for code, verwacht in sorted(VLAG.items()):
        n = 0
        for tekst in _load(code).values():
            for w in re.split(r"[\s ]+", tekst):
                if translit(w, plain_wasl=False) != translit(w, plain_wasl=True):
                    n += 1
        meld(n == verwacht, "plain_wasl raakt %d woorden in %s" % (verwacht, code),
             "in PLAIN_WASL" if code in PLAIN_WASL else "niet in PLAIN_WASL",
             "" if n == verwacht else "geteld %d, verwacht %d" % (n, verwacht))

    code, sura, ayah, index = WARSH_GEEN_VLAG
    w = woord(code, sura, ayah, index)
    uit, aan = translit(w, plain_wasl=False), translit(w, plain_wasl=True)
    meld(uit.startswith("'") and not aan.startswith("'"),
         "warsh %d:%d w%d houdt zijn hamza zonder de vlag" % (sura, ayah, index),
         "aliimun draagt hamzat al-qat' op een kale alif; met de vlag aan "
         "wordt die opgegeten",
         "" if uit.startswith("'") and not aan.startswith("'")
         else "uit=%r aan=%r" % (uit, aan))


def main():
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
            print("      %s" % detail)

    for test in (test_vaste_waarden, test_samenvallen, test_verschillen, test_vlag):
        test(meld)

    print("%d tests op riwaya_translit: %d geslaagd, %d gefaald"
          % (gelukt + mislukt, gelukt, mislukt))
    return 1 if mislukt else 0


if __name__ == "__main__":
    sys.exit(main())
