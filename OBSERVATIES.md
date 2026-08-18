# Observaties bij de Quran-corpusanalyse

Bevindingen uit de analyse van `quran.db`: de Quranic Arabic Corpus
(morfologie v0.4) met de toegevoegde kolommen `kalima_type` en `wazifa`, de
gelemmatiseerde damaa'ir, en de wujuh-laag uit vier klassieke werken.

Alle getallen hieronder zijn opnieuw tegen de database gecontroleerd.
`README.md` beschrijft het schema en de pijplijn; dit document beschrijft wat
er in de data te zien is.

## Basistellingen

| Eenheid | Aantal |
|---|---|
| Soera's | 114 |
| Verzen (ayaat) | 6.236 |
| Geschreven woorden (rasm-eenheden) | 77.429 |
| Morfologische segmenten (kalimaat) | 128.219 |
| Unieke roots | 1.642 |
| Unieke lemma's | 4.844 |

Een *geschreven woord* is een spatie-gescheiden blok in de moeshaf; een *segment*
is de kleinste grammaticale bouwsteen (prefix, stam, suffix). Wat de corpus
"segmenten" noemt valt vrijwel samen met de kalima van de klassieke nahw:
لَهُمْ is één geschreven woord maar twee kalimaat (harf لَ + ism هُمْ).

## Root versus lemma

- **Root**: abstracte wortel van (meestal) drie medeklinkers, het semantische
  DNA van een woordfamilie (ك-ت-ب "schrijven").
- **Lemma**: de woordenboekvorm van een concreet woord (كِتَٰب "boek",
  كَتَبَ "schrijven", كَاتِب "schrijver" — drie lemma's, één root).
- Hiërarchie: root (1.642) → lemma (4.844) → woordvorm in de tekst.
- Gebroken meervouden zijn in de corpus aparte lemma's (رَجُل en رِجَال),
  regelmatige verbuigingen niet (رَجُلَيْنِ valt onder رَجُل).

## Kalima-classificatie (kolom `kalima_type`)

| Soort | Voorkomens | Aandeel | Unieke lemma's |
|---|---|---|---|
| Ism | 62.747 | 48,9% | 3.325 |
| Harf | 46.086 | 36,0% | 46 (+ ~14 aangehechte) |
| Fi'l | 19.356 | 15,1% | 1.475 |
| Muqatta'aat | 30 | 0,02% | — |

De corpustags zijn gecorrigeerd naar de klassieke indeling: vraag- en
voorwaardewoorden (مَن, كَيْف, أَيْن, مَتَىٰ, كَم, مَاذَا, أَىّ, أَيَّان,
أَنَّىٰ, مَهْمَا, حَيْثُ, ٱلَّذِى voorwaardelijk, إِذَا shartiyya en مَا als
istifhaam/shart) zijn asmaa', geen huruf — 583 segmenten verhuisden daarmee
van harf naar ism (346 met tag `INTG`, 237 met tag `COND`). Vanuit
nahw-oogpunt telt de Quran zo **128.189 kalimaat** (exclusief de 30
muqatta'aat-reeksen). De verborgen damier (mustatir) telt niet mee; alleen wat
geschreven staat is geannoteerd.

## De damaa'ir als lemma's

De corpus laat persoonlijke voornaamwoorden zonder lemma (24.685 segmenten,
bijna 40% van alle ism-voorkomens). Elk PRON-segment is gelemmatiseerd naar
het canonieke losstaande voornaamwoord van zijn persoon-geslacht-getal-cel
(ـهُ/ـهِ/هُوَ → هُوَ; tweevouden naar أَنتُمَا en هُمَا), inclusief de
onderwerpssuffixen aan werkwoorden (كَتَبُوا۟ = fi'l + waw al-jamaa'a).
Resultaat: de 12 klassieke damaa'ir als lemma's, met هُم (8.272) als
grootste.

## Meerduidige woorden

Slechts **twee** lemma's overschrijden de ism/harf-grens: مَا en إِذَا.
Alle overige meerduidigheid speelt binnen één klasse. De belangrijkste
(geteld per lemma waar de corpus er een geeft, anders per geschreven vorm):

- **مَا**: ism 1.594x (mawsula 1.476, istifhaam 95, shart 23);
  harf 971x (nafiya 705, kaffa 162, masdariyya 83, zaa'ida 21).
- **مَن**: alle drie ism — mawsula 650, shart 184, istifhaam 37.
- **إِن**: shartiyya 578, **nafiya 114** (vaak gemist), mukhaffafa 5.
- **لَا**: nafiya 1.406, nahiya 332.
- **إِلَّا**: hasr 558, istithnaa' 102.
- **أَن**: masdariyya 578, mufassira 47.
- **وَ** is met zes functies het veelzijdigste woord: 'atf 8.177,
  isti'naafiyya 1.034, haliyya 293, zaa'ida 59, **qasam 28** (harf jarr!),
  ma'iyya 3 — samen 9.594 voorkomens van وَ en de geassimileerde variant وَّ.
- **فَ**: isti'naafiyya 1.891, 'atf 517, jawaab ash-shart 350, zaa'ida 155,
  sababiyya 88.
- **لَ/لِ**: laam al-jarr 2.451 naast laam at-tawkied 1.001, laam at-ta'liel
  319 en laam al-amr 78.
- Ruim 230 naamwoorden wisselen tussen N en ADJ (vooral de Schone Namen:
  عَزِيز is 63x zelfstandig en 38x bijvoeglijk getagd).

## Frequentieverdeling van kalimaat

Geteld per lemma waar de corpus er een geeft, anders per geschreven
segmentvorm, met alle vormen van het lidwoord samengenomen. Top van de
128.189 kalimaat: وَ (9.572; 7,5%), ٱل (8.377), هُم (8.272), أَنتُم (5.175),
هُوَ (3.845), مِن (3.226), فَ (3.001), ٱللَّه (2.699).

- De top 3 dekt 20,5% van de hele tekst; de top 20 dekt 51,8%; de **top 100
  dekt 72,8%** — wie die 100 woorden kent, herkent bijna drie van elke
  vier woorden.
- Het frequentste fi'l is قَالَ (1.618x), passend voor een tekst die
  grotendeels uit weergegeven spraak bestaat.
- Het frequentste inhoudswoord is ٱللَّه (2.699x).

## Roots: dekking en vruchtbaarheid

| | Met root | Zonder root |
|---|---|---|
| Unieke lemma's | 4.657 (96,1%) | 187 (3,9%) |
| Voorkomens | 49.968 (39,0%) | 78.251 (61,0%) |

- Elk fi'l heeft een root (100%); geen enkel harf heeft er een; van de
  ism-lemma's is 95,7% afgeleid. Geen enkel lemma is gemengd.
- De 187 rootloze lemma's: damaa'ir, mawsulaat, ishaara-woorden, versteende
  zuruf (إِذَا, إِذ, مَع…) en de niet-Arabische eigennamen (مُوسَىٰ,
  إِبْرَاهِيم, فِرْعَوْن). In de lopende tekst dekt het rootloze deel wel
  61% — het grammaticale bindweefsel domineert de frequenties.
- **Eigennamen zijn niet overwegend rootloos.** Van de 3.911 PN-segmenten
  hebben er 3.016 (77%) juist wél een root, omdat de meeste eigennamen
  gewone Arabische woorden zijn (صبر, حمد). Het is op *lemma*-niveau dat ze
  uitdunnen: van de 107 verschillende PN-lemma's hebben er maar 30 een root.
  De rootloze eigennamen zijn weinig in aantal maar frequent in de tekst.
- **6% van de roots dekt 60% van het root-dragende deel**: de top 100 roots
  leveren 779 lemma's (16,1% van het lexicon) en 23,6% van alle kalimaat.
- Frequentie en vruchtbaarheid zijn onafhankelijk: ارض is 461x aanwezig met
  één lemma; قوم brengt 22 lemma's voort; اله (2.851x, nr. 1) heeft er maar
  drie: ٱللَّه (2.699), إِلَٰه (147, waarvan 34x meervoud ءَالِهَة) en
  ٱللَّهُمَّ (5).

### Top 25 roots (percentage van 49.968 root-dragende kalimaat)

| # | Root | Kernbetekenis | Lemma's | Aantal | % | Cum. |
|---|---|---|---|---|---|---|
| 1 | اله | God, godheid | 3 | 2.851 | 5,71% | 5,7% |
| 2 | قول | zeggen | 6 | 1.722 | 3,45% | 9,2% |
| 3 | كون | zijn | 3 | 1.390 | 2,78% | 11,9% |
| 4 | ربب | Heer | 4 | 980 | 1,96% | 13,9% |
| 5 | امن | geloven | 17 | 879 | 1,76% | 15,7% |
| 6 | علم | weten | 14 | 854 | 1,71% | 17,4% |
| 7 | قوم | staan, volk | 22 | 660 | 1,32% | 18,7% |
| 8 | اتي | komen | 6 | 549 | 1,10% | 19,8% |
| 9 | كفر | ongeloof | 14 | 525 | 1,05% | 20,8% |
| 10 | بين | duidelijk, tussen | 13 | 523 | 1,05% | 21,9% |
| 11 | شيا | willen, ding | 2 | 519 | 1,04% | 22,9% |
| 12 | رسل | zenden | 8 | 513 | 1,03% | 23,9% |
| 13 | ارض | aarde | 1 | 461 | 0,92% | 24,9% |
| 14 | يوم | dag | 1 | 405 | 0,81% | 25,7% |
| 15 | ايي | teken | 1 | 382 | 0,76% | 26,4% |
| 16 | سمو | hemel | 6 | 381 | 0,76% | 27,2% |
| 17 | كلل | alle | 4 | 377 | 0,75% | 28,0% |
| 18 | عذب | bestraffing | 5 | 373 | 0,75% | 28,7% |
| 19 | عمل | handelen | 4 | 360 | 0,72% | 29,4% |
| 20 | جعل | maken | 2 | 346 | 0,69% | 30,1% |
| 21 | رحم | barmhartigheid | 9 | 339 | 0,68% | 30,8% |
| 22 | راي | zien | 8 | 328 | 0,66% | 31,5% |
| 23 | كتب | schrijven | 7 | 319 | 0,64% | 32,1% |
| 24 | هدي | leiden | 12 | 316 | 0,63% | 32,7% |
| 25 | ظلم | onrecht | 12 | 315 | 0,63% | 33,4% |

De top leest als de kernboodschap zelf: God (اله, ربب) spreekt (قول) tot de
mens over geloof (امن) en ongeloof (كفر), kennis (علم), tekenen (ايي),
boodschappers (رسل), leiding (هدي), barmhartigheid (رحم) en bestraffing (عذب).

## Wujuh wa-naza'ir: de polysemielaag

Voor betekenisverschillen binnen één woord (polysemie) is een `wujuh`-tabel
toegevoegd, gebouwd uit **vier** klassieke werken (OpenITI-digitaliseringen van
Shamela en JK) die samen vier eeuwen traditie beslaan. Per werk, zoals de
parsers ze uit de tekst halen en zoals ze in de tabel terechtkomen:

| Werk | Sterfjaar | Entries geparst | Senses geparst | Citaten | Geresolved | Rijen in `wujuh` |
|---|---|---|---|---|---|---|
| Yahya ibn Sallam, *at-Tasarif* | 200 AH | 114 | 551 | 1.871 | 96,5% | 2.571 |
| Abu Hilal al-Askari, *al-Wujuh wa-l-Naza'ir* | ca. 395 AH | 210 | 848 | 2.079 | 96,2% | 2.584 |
| al-Damaghani, *Qamus al-Qur'an* | 478 AH | 497 | 2.329 | 3.723 | 98,2% | 4.319 |
| Ibn al-Jawzi, *Nuzhat al-a'yun al-nawazir* | 597 AH | 300 | 1.500 | 2.749 | 96,8% | 2.870 |

*at-Tasarif* is het oudste overgeleverde werk van het genre, gebouwd op
Muqatils materiaal. Al-Askari is als vierde werk het laatst toegevoegd; zijn
editie nummert de wujuh met kale rangtelwoorden en zet de citaten tussen ronde
haken in plaats van de accolades die de andere drie digitaliseringen gebruiken,
en hij noemt vrijwel nooit de soera waaruit hij citeert (acht keer in het hele
boek). De
al-Damaghani-parse is fors verbeterd: van 387 naar 497 entries, waarmee de
dekking van het boek van ongeveer de helft naar ongeveer 98% ging — de
digitalisering verliest vanaf *baab as-saad* haar hamza's, dubbele punten,
aanhalingstekens en regeleindes, en de parser vangt dat nu met begrensde
terugvalregels op.

Totaal: **12.344 citaatrijen** over 1.083 entries (werk + trefwoord), 4.935
senses en 450 roots, verwijzend naar 3.635 verschillende verzen. 9.947 rijen
noemen bovendien het concrete *woord* in dat vers waar de wajh over gaat
(kolommen `word`, `corpus_id`, `form_ar`).

Van de 450 roots wordt er 167 door één werk behandeld, 129 door twee, 87 door
drie en **67 door alle vier** — dat laatste is het vergelijkingsmateriaal over
vier eeuwen.

### Sense-uitlijning over de werken heen

Omdat `sense_nr` per werk telt, is Ibn Sallams eerste wajh van هدى ("bayaanan")
formeel iets anders dan die van Ibn al-Jawzi ("al-bayaan"), terwijl het
dezelfde wajh is. De tabel `sense_alignment` legt daarom canonieke sense-ids
over de werken heen: **5.027 uitgelijnde senses in 3.284 canonieke senses**,
waarvan 442 door drie of meer werken worden gedragen en 140 door alle vier.

Twee signalen beslissen, en beide moeten verdiend worden: overlap in de
geciteerde verzen (alleen citaten met confidence high/medium tellen mee — de
low-rijen zijn kandidatenlijsten) en gelijkenis van de glossen. Verzenoverlap
alleen is nooit genoeg, want twee wujuh van één root citeren juist regelmatig
hetzelfde vers omdát de auteurs het oneens zijn over welke wajh erbij hoort.
Volgordematching is bewust niet gebruikt: de werken lopen grofweg parallel,
maar Ibn al-Jawzi splitst waar Ibn Sallam samenneemt.

Mooiste validatie blijft هدى: Ibn Sallam (2e eeuw) geeft 17 wujuh, al-Askari
(4e eeuw) 12, al-Damaghani (5e eeuw) 16 en Ibn al-Jawzi (6e eeuw) 19 — en zes
daarvan (al-bayaan, dien al-islaam, al-imaan, amr Muhammad, al-ilhaam en
al-ma'rifa) staan bij alle vier in de lijst, meestal zelfs op een
vergelijkbare plaats in de volgorde; nog eens zes worden door drie van de
vier gedragen. De traditie blijkt over vier eeuwen opmerkelijk stabiel
overgeleverd. Waar ze uiteenlopen is dat even sprekend: voor خير geeft Ibn
al-Jawzi 19
senses, al-Askari 10, Ibn Sallam 8 en al-Damaghani 7.

Statusonderscheid dat hierbij is vastgelegd: homonymie over de klassegrens
(ما ism/harf) en functiesplitsing binnen een klasse (istifhamiyya vs
shartiyya — verschillend 'amal) zijn **andere woorden**; de wujuh van
bijvoorbeeld هدى zijn **één woord met meerdere betekenissen**.

## Gemeten kwaliteit van de wujuh-laag

De laag is niet uniform betrouwbaar, en dat is per inferentiestap gemeten in
plaats van geschat. Dat leverde de belangrijkste correctie van het hele
project op.

### De confidence-kolom

| Waarde | Rijen | Betekenis |
|---|---|---|
| `high` | 9.242 (75%) | de geciteerde woorden zijn gevonden, in precies één vers — attestatie |
| `medium` | 480 (4%) | het vers is waarschijnlijk maar niet vastgesteld: de bewoording moest benaderd worden, of er bleven twee à drie verzen over |
| `low` | 2.622 (21%) | kandidatenlijst, geen attestatie: de zinsnede komt in vier of meer verzen voor en het werk zegt niet welk |

Filter hierop vóór je iets telt. Wie de low-rijen als attestaties meetelt,
blaast juist de meest generieke zinsneden op.

### Twee lagen die de toets niet doorstonden en herbouwd zijn

- **`substantiate_jk`** (het redden van mislukte citaten met behulp van de
  tweede, onafhankelijk getypte digitalisering van de Nuzhat, die correct
  getypte tegenhangers van verminkte citaten levert — ook voor citaten uit de
  andere drie werken) accepteerde eerder elke tegenhanger met 0,6
  woordoverlap, zonder verificatie. Dat leverde 82 rijen op waarvan ongeveer
  **91% een vers noemde waar het citaat niet in staat**;
  44% ervan klapte samen op 17:69 alleen, doordat het redactionele woord
  *wa-fiehaa* toevallig overlapte. De keten eist nu locatie-informatie, een
  skeletgelijkenis, verificatie tegen de verstekst zélf en uniciteit onder de
  overgebleven kandidaten. Resultaat: **9 rijen voor 7 citaten**, stuk voor
  stuk met de hand nagelopen.
- **`short_hint`** (zeer korte citaten geplaatst via een soeraverwijzing) was
  bij 162 rijen ongeveer **50% fout**. Nu 15 rijen, alle 15 letterlijk
  verifieerbaar in het aangewezen vers.

### Een laag die juist goed bleek

- **`fuzzy`** stond te boek als de zwakke schakel, maar meet **96% correct**.
  Hij blijft op `medium` staan omdat een match op woordoverlap niet kan
  bewijzen wélk vers de auteur bedoelde, niet omdat hij onbetrouwbaar is.

### Ambiguous is een kandidatenlijst

De `ambiguous`-rijen zijn geen attestaties: **2.588 rijen voor 584 citaten**,
gemiddeld 4,43 verzen per citaat. De breedste lijst telt **152 verzen** (het
citaat الذين كفروا onder al-Damaghani's *k-f-r*). Eerder werd die breedte
verborgen door een stille afkapping op tien kandidaten; die is verwijderd, en
`candidate_count` toont nu de werkelijke breedte. Alle ambiguous-rijen staan op
confidence `low`.

### Wat een match écht garandeert

De klassieke auteurs citeren uit het hoofd en in de spelling van hun eigen
tijd, niet uit de rasm van de moeshaf. `validate.py` verifieert daarom elk
citaat in cumulatieve niveaus en rapporteert ze naast elkaar, omdat elk
niveau afzonderlijk misleidt. Op een steekproef van 750 `unique`-rijen:

| Niveau | `unique` | `ambiguous` | `hint_resolved` |
|---|---|---|---|
| letterlijk aanwezig in het vers | 58,0% | 61,1% | 52,3% |
| na weglaten van het inleidende woord | 71,5% | 76,3% | 70,6% |
| op het medeklinkerskelet | 100% | 100% | 100% |

`unique` betekent dus **niet** "het genormaliseerde citaat komt letterlijk in
precies één vers voor". Het betekent dat het citaat op het niveau waarop de
matcher werkte in precies één vers gevonden is: letterlijk geldt dat voor
ongeveer 58%, op medeklinkerskeletniveau voor alle. De tolerante niveaus
overdrijven de andere kant op: ze zeggen dat de woorden in dat vers staan,
niet dat het het vers is dat de auteur bedoelde.

`validate.py` draait in totaal 19 controles over de afgebouwde database; op de
huidige database slagen er 17 en waarschuwen er 2 (de breedte van
`ambiguous`, en het feit dat `prefix` en `edition_jk` op het zwakste niveau
onder de 90% blijven — samen 76 rijen).

## Wat er bewust níet in zit

- **Geen tafsir-mining.** Het idee om betekenistoekenningen uit al-Tabari's
  *Jaami' al-bayaan* te halen — en zo verder te komen dan de verzen die de
  wujuh-werken zelf citeren — is onderzocht en afgeraden. Gemeten haalde het
  ongeveer **35% precisie bij een recall-plafond van ongeveer 35%**. Dat ligt
  ver onder de maat waaraan de rest van deze laag gehouden wordt, dus er wordt
  geen tafsir gebruikt.
- **Geen vijfde wujuh-werk.** Al-Hiri (431 AH) en het zelfstandige
  *Wujuh*-werk van Muqatil ibn Sulayman zijn uitputtend gezocht in heel
  OpenITI — 36 eeuw-repositories, 13.364 tekstversies — en komen daar niet in
  voor. Al-Askari was de laatste beschikbare volledige wujuh-tekst; de laag is
  daarmee zo breed als de gedigitaliseerde traditie toelaat.
- **Geen sense-label per voorkomen.** De klassieke werken citeren
  voorbeeldverzen per sense; ze annoteren de Quran niet uitputtend. De 450
  gedekte roots komen 38.785 keer voor in de corpus, en slechts 6.530 daarvan
  (17%) staan in een vers waar een wujuh-rij naar wijst — bij alleen
  `high`-rijen 5.155 (13%). Een label per voorkomen zou een moderne laag
  vergen, geen klassieke.
