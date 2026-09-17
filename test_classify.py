#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Eenheidstests voor de indeler van compare_riwayat.

`test_translit.py` toetst de sleutel waarmee twee riwaayaat vergeleken
worden. Dit toetst wat er daarna gebeurt: `classify(links, rechts, controle,
ruw_rechts)` krijgt twee transliteraties en geeft er een klassenaam voor
terug, en die naam bepaalt of een plaats als usul, notatie of farsh in de
database belandt. Dat is de laag waar deze week twee defecten zaten -- een
`summary()` die over de verkeerde verzameling liep, en een gat waar twee
usul-kenmerken in een woord samenkomen.

Geen enkel Arabisch woord staat in dit bestand. Een geval wijst een rij aan
met (paar, soera, aya, hoeveelste rij van dat paar in dat vers) en haalt de
vormen bij het draaien uit quran.db. De positie is de sleutel en de klasse de
verwachting, zodat de test niet de klasse gebruikt om de rij te vinden die hij
vervolgens op die klasse toetst.

Vier soorten geval, en de laatste drie zeggen meer dan de eerste:

  KLASSEN   wat classify() in zijn eentje herkent -- een geval per klasse
  CONTROLE  wat al-Doorie als controle oplevert: zonder hem is elk van deze
            vijf plaatsen farsh, met hem is het idghaam kabier
  REDDING   wat de omgekeerde pass redt, en waarom dat veilig is
  LATER     klassen die niet uit classify komen maar uit de uitlijning, uit
            second_look of uit de handmatige oordelen; hier vastgelegd zodat
            zichtbaar blijft welke laag ze zet

    python3 test_classify.py        een regel per fout
    python3 test_classify.py -v     ook de geslaagde gevallen, met hun reden

Wat deze suite niet vangt, zodat de PASS-regel niet voor meer wordt gelezen
dan hij zegt. De gevallen halen hun woorden uit quran.db, dus een wijziging
die pas na een herbouw zichtbaar wordt, ontgaat ze: zet IDGHAAM_KABIR op een
andere riwaaya en alle 117 blijven groen, want de opgeslagen rijen zijn nog
met al-Doorie als controle gemaakt. Nagemeten met zeven mutaties; deze is de
enige die overleefde. Wat wel valt: naql aan SYMMETRIC toevoegen, ha_iskan
eruit halen, een klasse uit KIND slopen, de sila_mim-tak uitzetten, en de
residu-regel van de controle uitzetten.
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from compare_riwayat import KIND, SYMMETRIC, classify

# (a, b, soera, aya, hoeveelste rij van dat paar in dat vers, klasse, waarom)
KLASSEN = [
    ("qaloon", "bazzi",     1,    1, 1, "article_lam",                      
     "de laam van al- met of zonder shadda geschreven"),
    ("hafs",   "qaloon",    1,    4, 0, "farsh_candidate",                  
     "maalik tegenover malik in 1:4 -- het schoolvoorbeeld van farsh"),
    ("qaloon", "bazzi",     2,    5, 2, "farsh_candidate+sila_mim",         
     "maalik tegenover malik in 1:4 -- het schoolvoorbeeld van farsh (met sila_mim erbij)"),
    ("qaloon", "bazzi",     2,    7, 0, "gemination_notation",              
     "een idghaam die de ene kant met een shadda markeert en de andere niet"),
    ("qaloon", "bazzi",     2,   79, 0, "gemination_notation+sila_mim",     
     "een idghaam die de ene kant met een shadda markeert en de andere niet (met sila_mim erbij)"),
    ("qaloon", "warsh",     2,    2, 0, "hamza_treatment",                  
     "de hamza verzacht tot de lange klinker die eronder zit"),
    ("hafs",   "warsh",     2,    6, 2, "hamza_treatment+sila_mim",         
     "de hamza verzacht tot de lange klinker die eronder zit (met sila_mim erbij)"),
    ("hafs",   "warsh",     2,   29, 2, "imaala",                           
     "de mushaf markeert de taqliel zelf; een yaa tegen een alif is dan de klinker"),
    ("qaloon", "bazzi",     3,   15, 0, "imaala+sila_mim",                  
     "de mushaf markeert de taqliel zelf; een yaa tegen een alif is dan de klinker (met sila_mim erbij)"),
    ("qaloon", "warsh",     2,   30, 2, "initial_alif_notation",            
     "hamza aan het woordbegin, op een andere zetel"),
    ("warsh",  "bazzi",     7,   32, 1, "initial_alif_notation+sila_mim",   
     "hamza aan het woordbegin, op een andere zetel (met sila_mim erbij)"),
    ("qaloon", "warsh",     2,   13, 0, "junction_vowel",                   
     "de hulpklinker die bij wasl op de laatste letter komt"),
    ("qaloon", "bazzi",     2,   28, 3, "maqsura_notation",                 
     "alif maqsoera geschreven als ى of als ي"),
    ("qaloon", "bazzi",     2,  141, 0, "maqsura_notation+sila_mim",        
     "alif maqsoera geschreven als ى of als ي (met sila_mim erbij)"),
    ("hafs",   "qaloon",    2,    1, 0, "muqattaat",                        
     "de losse letters, gespeld tegenover niet gespeld"),
    ("qaloon", "warsh",     2,   32, 0, "naql",                             
     "de klinker van een volgende hamza verhuist naar de laatste letter"),
    ("hafs",   "doori",     3,  158, 0, "naql_alif",                        
     "de zwijgende alif die na een naql blijft staan"),
    ("qaloon", "bazzi",     2,    1, 1, "sila_ha",                          
     "silat al-haa: de lange klinker op het voornaamwoord"),
    ("qaloon", "bazzi",     1,    6, 1, "sila_mim",                         
     "silat al-miem: hoem gelezen als hoemoe"),
    ("qaloon", "warsh",     2,  160, 0, "unwritten_vowel",                  
     "de klinker op de eerste letter ongeschreven gelaten"),
    ("warsh",  "bazzi",     2,  195, 2, "unwritten_vowel+sila_mim",         
     "de klinker op de eerste letter ongeschreven gelaten (met sila_mim erbij)"),
    ("qaloon", "qumbul",    2,   30, 2, "wasl_notation",                    
     "hamzat al-wasl anders geschreven"),
    ("hafs",   "bazzi",     2,    6, 1, "wasl_notation+sila_mim",           
     "hamzat al-wasl anders geschreven (met sila_mim erbij)"),
    ("hafs",   "qaloon",    2,   30, 1, "yaa_idafa",                        
     "de yaa al-idaafa geopend"),
    ("qaloon", "warsh",     2,  185, 1, "yaa_zaida",                        
     "een yaa zaa-ida hersteld"),
]

CONTROLE = [
    ("qaloon", "soosi",     2,  247, 1, "farsh_candidate",                   "farsh_candidate+idghaam_kabir"),
    ("hafs",   "soosi",     5,   27, 2, "farsh_candidate",                   "gemination_notation+idghaam_kabir"),
    ("qaloon", "soosi",     2,   54, 1, "farsh_candidate",                   "hamza_treatment+idghaam_kabir"),
    ("qaloon", "soosi",     1,    2, 0, "farsh_candidate",                   "idghaam_kabir"),
    ("warsh",  "soosi",    22,   37, 0, "farsh_candidate",                   "unwritten_vowel+idghaam_kabir"),
]

LATER = [
    ("qaloon", "warsh",     2,   28, 2, "farsh_candidate",                   "ha_iskan"),
    ("hafs",   "qaloon",    1,    1, 0, "farsh_candidate",                   "reviewed:alignment_or_word_split"),
    ("qaloon", "bazzi",     2,   70, 0, "farsh_candidate",                   "reviewed:hamza_seat_notation"),
    ("warsh",  "bazzi",     2,   32, 4, "farsh_candidate",                   "reviewed:hamza_vowel_notation"),
    ("hafs",   "warsh",     2,  150, 0, "farsh_candidate",                   "reviewed:hand"),
    ("shouba", "qaloon",   10,    1, 0, "farsh_candidate",                   "reviewed:muqattaat"),
    ("hafs",   "warsh",     4,   15, 0, "farsh_candidate",                   "reviewed:onzeker"),
    ("bazzi",  "doori",     9,  101, 4, "farsh_candidate",                   "word_delete"),
    ("hafs",   "bazzi",     9,  100, 4, "farsh_candidate",                   "word_insert"),
]

# De omgekeerde pass. Waar de heen-richting niets herkent, probeert
# compare_riwayat het paar omgedraaid en neemt de uitkomst over als die in
# SYMMETRIC staat. (paar, soera, aya, rij, heen, terug)
REDDING = [
    ("qaloon", "warsh", 2, 28, 2, "farsh_candidate", "ha_iskan"),
]

# En de plaats waar die redding niet mag toeslaan. Het commentaar in
# compare_riwayat noemt hem bij naam: bij 2:284 fayaghfiru / fayaghfir ziet de
# omgekeerde pass een naql -- "er is een klinker aan de laatste letter
# toegevoegd" -- en zo ziet een jazm er van de andere kant uit. Zou `naql` ooit
# in SYMMETRIC belanden, dan verdwijnt de meest bediscussieerde farsh-plaats
# van de Qoeraan stilletjes in de usul, in elk paar waar hij in voorkomt.
WAARBORG = (2, 284, "farsh_candidate", "naql")

# Dezelfde plaats, maar nu tegenover al-Soesie, en dan is het de controle die
# hem farsh houdt. Een ontbrekende eindklinker kan twee dingen zijn, en 2:284
# is het geval waar het uitmaakt: al-Doorie leest fayaghfir net zo goed zonder
# klinker, dus is het een jazm en geen idghaam. Zou de controle wegvallen of
# een klinker aandragen, dan zou de regel deze plaats opeisen.
# (paar, soera, aya, rij, met een controle zónder eindklinker, met een controle
#  die er wel een heeft)
JAZM = ("hafs", "soosi", 2, 284, 0, "farsh_candidate", "idghaam_kabir")


def _rij(cur, a, b, sura, ayah, n):
    rows = cur.execute(
        "SELECT translit_a, translit_b, form_a, form_b, class, kind"
        " FROM riwaya_diff WHERE riwaya_a=? AND riwaya_b=? AND surah=? AND ayah_a=?"
        " ORDER BY rowid", (a, b, sura, ayah)).fetchall()
    if n >= len(rows):
        return None
    return rows[n]


def _naam(a, b, sura, ayah, n):
    return "%s-%s %d:%d #%d" % (a, b, sura, ayah, n)


def test_klassen(cur, meld):
    for a, b, sura, ayah, n, verwacht, waarom in KLASSEN:
        r = _rij(cur, a, b, sura, ayah, n)
        if r is None:
            meld(False, _naam(a, b, sura, ayah, n), waarom, "die rij bestaat niet meer")
            continue
        got = classify(r[0] or "", r[1] or "", None, r[3] or "")
        meld(got == verwacht, _naam(a, b, sura, ayah, n), waarom,
             "" if got == verwacht else "verwacht %r, gekregen %r" % (verwacht, got))
        meld(r[4] == verwacht, _naam(a, b, sura, ayah, n) + " staat zo in de database",
             "de opgeslagen klasse hoort dezelfde te zijn", ""
             if r[4] == verwacht else "database zegt %r" % r[4])


def test_controle(cur, meld):
    """Wat al-Doorie als controle oplevert.

    Een klinker die aan het eind van een woord ontbreekt kan twee dingen zijn:
    de idghaam kabier van al-Soesie, of een jazm -- en dat laatste is farsh.
    al-Doorie overlevert dezelfde qiraa-a van dezelfde qaari- zonder die regel,
    dus waar hij de klinker wel schrijft, was het de regel. Zonder hem is elk
    van deze vijf plaatsen een farsh-kandidaat; met hem is het usul.
    """
    for a, b, sura, ayah, n, zonder, met in CONTROLE:
        r = _rij(cur, a, b, sura, ayah, n)
        if r is None:
            meld(False, _naam(a, b, sura, ayah, n), "controle", "die rij bestaat niet meer")
            continue
        los = classify(r[0] or "", r[1] or "", None, r[3] or "")
        # de controle schrijft de klinker die de regel wegnam; de linkerkant
        # doet dat hier ook, dus die staat model voor de controle
        vast = classify(r[0] or "", r[1] or "", r[0] or "", r[3] or "")
        meld(los == zonder, _naam(a, b, sura, ayah, n) + " zonder controle",
             "zonder al-Doorie is dit farsh", ""
             if los == zonder else "verwacht %r, gekregen %r" % (zonder, los))
        meld(vast == met, _naam(a, b, sura, ayah, n) + " met controle",
             "met al-Doorie is het %s" % met, ""
             if vast == met else "verwacht %r, gekregen %r" % (met, vast))


def test_redding(cur, meld):
    for a, b, sura, ayah, n, heen, terug in REDDING:
        r = _rij(cur, a, b, sura, ayah, n)
        h = classify(r[0] or "", r[1] or "", None, r[3] or "")
        t = classify(r[1] or "", r[0] or "", None, r[2] or "")
        meld(h == heen, _naam(a, b, sura, ayah, n) + " heen",
             "de heen-richting herkent het kenmerk niet", ""
             if h == heen else "verwacht %r, gekregen %r" % (heen, h))
        meld(t == terug, _naam(a, b, sura, ayah, n) + " terug",
             "de omgekeerde richting wel", ""
             if t == terug else "verwacht %r, gekregen %r" % (terug, t))
        meld(t.split("+")[0] in SYMMETRIC, "%s staat in SYMMETRIC" % terug,
             "en daarom mag de uitkomst overgenomen worden", "")
        meld(r[4] == terug, _naam(a, b, sura, ayah, n) + " staat zo in de database",
             "de redding is dus toegepast", "" if r[4] == terug else "database zegt %r" % r[4])


def test_waarborg(cur, meld):
    sura, ayah, heen, terug = WAARBORG
    meld(terug not in SYMMETRIC, "%r staat niet in SYMMETRIC" % terug,
         "anders zou 2:284 fayaghfiru/fayaghfir stil van farsh naar usul gaan", "")
    rijen = cur.execute(
        "SELECT riwaya_a, riwaya_b, translit_a, translit_b, form_a, form_b, class, kind"
        " FROM riwaya_diff WHERE surah=? AND ayah_a=? AND class='farsh_candidate'"
        " AND translit_b NOT LIKE '%a' AND translit_a LIKE translit_b || 'u'",
        (sura, ayah)).fetchall()
    meld(len(rijen) > 0, "2:284 levert paren op om te toetsen",
         "de plaats moet in de database staan", "" if rijen else "geen rij gevonden")
    for a, b, ta, tb, fa, fb, cls, kind in rijen:
        h = classify(ta or "", tb or "", None, fb or "")
        t = classify(tb or "", ta or "", None, fa or "")
        goed = h == heen and t == terug and kind == "farsh"
        meld(goed, "2:284 %s-%s blijft farsh" % (a, b),
             "heen %s, terug %s, en terug is niet symmetrisch" % (heen, terug),
             "" if goed else "heen=%r terug=%r kind=%r" % (h, t, kind))


def test_jazm(cur, meld):
    """De controle moet ook tegenhouden, niet alleen toestaan.

    Alle CONTROLE-gevallen hierboven laten zien wat al-Doorie *toestaat*: een
    plaats die zonder hem farsh heet, is met hem usul. Dit geval laat het
    omgekeerde zien, en het is het geval waar het om gaat. Bij 2:284 ontbreekt
    de eindklinker aan beide kanten -- al-Doorie leest fayaghfir net zo goed
    zonder -- dus is het een jazm, en jazm is farsh. Geef dezelfde plaats een
    controle die de klinker wel schrijft, en de regel eist hem op.
    """
    a, b, sura, ayah, n, zonder_klinker, met_klinker = JAZM
    r = _rij(cur, a, b, sura, ayah, n)
    if r is None:
        meld(False, "2:284 %s-%s" % (a, b), "jazm-waarborg", "die rij bestaat niet meer")
        return
    ta, tb, fb = r[0] or "", r[1] or "", r[3] or ""
    houdt = classify(ta, tb, tb, fb)
    eist = classify(ta, tb, ta, fb)
    meld(houdt == zonder_klinker, "2:284 blijft %s met een controle zonder eindklinker" % zonder_klinker,
         "al-Doorie leest fayaghfir ook zonder klinker, dus het is een jazm",
         "" if houdt == zonder_klinker else "gekregen %r" % houdt)
    meld(eist == met_klinker, "2:284 wordt %s met een controle die er wel een heeft" % met_klinker,
         "dat is precies het onderscheid dat de controle maakt",
         "" if eist == met_klinker else "gekregen %r" % eist)
    meld(r[5] == "farsh", "2:284 staat als farsh in de database",
         "de controle heeft dus gedaan wat hij moest", ""
         if r[5] == "farsh" else "database zegt %r" % r[5])


# De hele bijdrage van de controle, in één getal en vijf plaatsen. Dit staat
# zo in de docstring van undo_idghaam en wordt in vier bestanden geciteerd,
# en tot nu toe rekende niets het na.
SPLITSING = (1152, 5, [(2, 284), (2, 284), (4, 81), (19, 6), (27, 66)])


def test_splitsing(cur, meld):
    """1.152 tegen 5, en welke vijf.

    Neem elke plaats waar al-Soesie een eindklinker mist die Hafs wel heeft.
    Schrijft al-Doorie hem daar wel, dan was het de idghaam kabier; mist hij
    hem ook, dan hoort het bij de lezing van Aboe 3Amr zelf en is het farsh.
    Dat is de hele redenering achter de controle, en ze is hier na te rekenen
    in plaats van te geloven.
    """
    regel, geen_regel, plaatsen = SPLITSING

    def gevallen(b):
        # rijen, niet unieke drietallen: hetzelfde woord komt op meer plaatsen
        # in een vers voor, en elke plaats telt apart -- dat is wat de 1.157
        # in de docstring van undo_idghaam telt
        return [(r[0], r[1], r[2]) for r in cur.execute(
            "SELECT surah, ayah_a, translit_a, translit_b FROM riwaya_diff"
            " WHERE riwaya_a='hafs' AND riwaya_b=?", (b,))
            if r[2] and r[3] and r[2][-1:] in "aui" and r[3] == r[2][:-1]]

    s_kant = gevallen("soosi")
    d_kant = set(gevallen("doori"))
    is_regel = [x for x in s_kant if x not in d_kant]
    niet = [x for x in s_kant if x in d_kant]
    meld(len(is_regel) == regel,
         "de controle wijst %d plaatsen aan als idghaam kabier" % regel,
         "al-Doorie schrijft daar de klinker die al-Soesie wegneemt",
         "" if len(is_regel) == regel else "geteld %d" % len(is_regel))
    meld(len(niet) == geen_regel,
         "en %d plaatsen niet" % geen_regel,
         "daar mist al-Doorie de klinker ook, dus hoort hij bij de lezing",
         "" if len(niet) == geen_regel else "geteld %d" % len(niet))
    gevonden = sorted((s, a) for s, a, _t in niet)
    meld(gevonden == sorted(plaatsen),
         "en het zijn deze vijf: 2:284 tweemaal, 4:81, 19:6, 27:66",
         "de plaatsen die een lezer zelf zou noemen",
         "" if gevonden == sorted(plaatsen) else "gevonden %s" % gevonden)
    alle_farsh = all(
        cur.execute("SELECT kind FROM riwaya_diff WHERE riwaya_a='hafs'"
                    " AND riwaya_b='soosi' AND surah=? AND ayah_a=?"
                    " AND translit_a=?", (s, a, t)).fetchone()[0] == "farsh"
        for s, a, t in niet)
    meld(alle_farsh, "en alle vijf staan als farsh in de database",
         "een jazm is farsh, en dat is wat de controle beschermt", "")


def test_later(cur, meld):
    """Klassen die niet uit classify komen.

    Vastgelegd omdat het anders onzichtbaar is welke laag ze zet: de
    uitlijning (word_insert, word_delete, een verschoven woordgrens),
    second_look, of de handmatige oordelen uit farsh_review.tsv. classify
    alleen geeft hier een farsh-kandidaat, en dat hoort ook.
    """
    for a, b, sura, ayah, n, los, uiteindelijk in LATER:
        r = _rij(cur, a, b, sura, ayah, n)
        if r is None:
            meld(False, _naam(a, b, sura, ayah, n), "latere laag", "die rij bestaat niet meer")
            continue
        got = classify(r[0] or "", r[1] or "", None, r[3] or "")
        meld(got == los, _naam(a, b, sura, ayah, n),
             "classify geeft %s; %s komt van een latere laag" % (los, uiteindelijk),
             "" if got == los else "verwacht %r, gekregen %r" % (los, got))
        meld(r[4] == uiteindelijk, _naam(a, b, sura, ayah, n) + " eindigt als %s" % uiteindelijk,
             "en die laag heeft gedraaid", "" if r[4] == uiteindelijk else "database zegt %r" % r[4])


def test_invarianten(cur, meld):
    zelfde = [t for (t,) in cur.execute(
        "SELECT DISTINCT translit_a FROM riwaya_diff WHERE translit_a <> '' LIMIT 400")]
    fout = [t for t in zelfde if classify(t, t, None, "") != "identical"]
    meld(not fout, "twee gelijke sleutels geven 'identical'",
         "over %d verschillende sleutels" % len(zelfde),
         "" if not fout else "%d uitzonderingen, bv. %r" % (len(fout), fout[0]))

    onbekend = sorted({deel for (cls,) in cur.execute("SELECT DISTINCT class FROM riwaya_diff")
                       for deel in cls.split("+") if deel not in KIND})
    meld(not onbekend, "elke klasse in de database staat in KIND",
         "een klasse die KIND niet kent, wordt stil 'onbekend' en heeft geen soort",
         "" if not onbekend else "ontbreekt: %s" % ", ".join(onbekend))


def main():
    db = HERE / "quran.db"
    if not db.exists():
        print("quran.db ontbreekt")
        return 1
    cur = sqlite3.connect(str(db)).cursor()
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

    for test in (test_klassen, test_controle, test_redding,
                 test_waarborg, test_jazm, test_splitsing,
                 test_later, test_invarianten):
        test(cur, meld)

    print("%d tests op de indeler: %d geslaagd, %d gefaald"
          % (gelukt + mislukt, gelukt, mislukt))
    return 1 if mislukt else 0


if __name__ == "__main__":
    sys.exit(main())
