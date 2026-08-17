# Observaties bij de Quran-corpusanalyse

Bevindingen uit de analyse van `quran.db` (Quranic Arabic Corpus, morfologie v0.4),
inclusief de toegevoegde `kalima_type`-kolom en de gelemmatiseerde damaa'ir.

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
van harf naar ism. Vanuit nahw-oogpunt telt de Quran zo **128.189 kalimaat**
(exclusief de 30 muqatta'aat-reeksen). De verborgen damier (mustatir) telt
niet mee; alleen wat geschreven staat is geannoteerd.

## De damaa'ir als lemma's

De corpus laat persoonlijke voornaamwoorden zonder lemma (24.661 segmenten,
een derde van alle ism-voorkomens). Elk PRON-segment is gelemmatiseerd naar
het canonieke losstaande voornaamwoord van zijn persoon-geslacht-getal-cel
(ـهُ/ـهِ/هُوَ → هُوَ; tweevouden naar أَنتُمَا en هُمَا), inclusief de
onderwerpssuffixen aan werkwoorden (كَتَبُوا۟ = fi'l + waw al-jamaa'a).
Resultaat: de 12 klassieke damaa'ir als lemma's, met هُم (8.272) als
grootste.

## Meerduidige woorden

Slechts **twee** lemma's overschrijden de ism/harf-grens: مَا en إِذَا.
Alle overige meerduidigheid speelt binnen één klasse. De belangrijkste:

- **مَا**: ism 1.594x (mawsula 1.476, istifhaam 95, shart 23);
  harf 971x (nafiya 705, kaffa 162, masdariyya 83, zaa'ida 21).
- **مَن**: alle drie ism — mawsula 650, shart 184, istifhaam 37.
- **إِن**: shartiyya 578, **nafiya 114** (vaak gemist), mukhaffafa 5.
- **لَا**: nafiya 1.406, nahiya 332.
- **إِلَّا**: hasr 558, istithnaa' 102.
- **أَن**: masdariyya 578, mufassira 47.
- **وَ** is met zes functies het veelzijdigste woord: 'atf 8.177,
  isti'naafiyya 1.034, haliyya 293, zaa'ida 59, **qasam 28** (harf jarr!),
  ma'iyya 3.
- **فَ**: isti'naafiyya 1.891, 'atf 517, jawaab ash-shart 350, sababiyya 88.
- **لَ**: laam al-jarr 1.328 naast laam at-tawkied 1.001.
- Ruim 250 naamwoorden wisselen tussen N en ADJ (vooral de Schone Namen:
  رَحِيم 112x bijvoeglijk / 4x zelfstandig; عَزِيز juist 63x zelfstandig).

## Frequentieverdeling van kalimaat

Top van de 128.189 kalimaat: وَ (9.566; 7,5%), ٱل (8.377), هُم (8.272),
أَنتُم (5.175), هُوَ (3.845), مِن (3.226), فَ (3.001), ٱللَّه (2.699).

- De top 3 is 20% van de hele tekst; de top 20 dekt 50,5%; de **top 100
  dekt 72,9%** — wie die 100 woorden kent, herkent bijna drie van elke
  vier woorden.
- Het frequentste fi'l is قَالَ (1.618x), passend voor een tekst die
  grotendeels uit weergegeven spraak bestaat.
- Het frequentste inhoudswoord is ٱللَّه.

## Roots: dekking en vruchtbaarheid

| | Met root | Zonder root |
|---|---|---|
| Unieke lemma's | 4.657 (96,1%) | 187 (3,9%) |
| Voorkomens | 49.968 (39,0%) | 78.221 (61,0%) |

- Elk fi'l heeft een root (100%); geen enkel harf heeft er een; van de
  ism-lemma's is 95,7% afgeleid. Geen enkel lemma is gemengd.
- De 187 rootloze lemma's: damaa'ir, mawsulaat, ishaara-woorden, versteende
  zuruf (إِذَا, إِذ, مَع…) en vooral niet-Arabische eigennamen (مُوسَىٰ,
  إِبْرَاهِيم, فِرْعَوْن). In de lopende tekst dekt het rootloze deel wel
  61% — het grammaticale bindweefsel domineert de frequenties.
- **6% van de roots dekt 60% van het root-dragende deel**: de top 100 roots
  leveren 781 lemma's (16,1% van het lexicon) en 23,6% van alle kalimaat.
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
