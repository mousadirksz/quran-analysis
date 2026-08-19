# Bevindingen

Wat de analyse van deze database heeft opgeleverd, met per bevinding de
analyse die het cijfer reproduceert. Draai `python3 analyses.py --all` om alles
opnieuw te berekenen, of `python3 analyses.py <naam>` voor een enkele.

Waar de wujuh-laag wordt aangehaald geldt `confidence = 'high'`, tenzij anders
vermeld: de lagere niveaus zijn kandidaatlijsten, geen attestaties.

---

## 1. Wat tel je eigenlijk? (`basics`, `kalima`)

De vraag "hoeveel woorden heeft de Quran" heeft twee verdedigbare antwoorden,
en het verschil is niet triviaal.

| Eenheid | Aantal |
|---|---|
| Soera's | 114 |
| Verzen | 6.236 |
| **Geschreven woorden** (spatie-gescheiden blokken) | **77.429** |
| **Segmenten / kalimat** (grammaticale bouwstenen) | **128.219** |
| Unieke roots | 1.642 |
| Unieke lemma's | 4.844 |

Een *geschreven woord* is wat in de moeshaf tussen twee spaties staat. Een
*segment* is de kleinste grammaticale bouwsteen. Het Arabisch plakt kleine
woordjes vast: وَلَهُمْ is één geschreven woord maar drie segmenten
(وَ + لَ + هُمْ).

Dat segment-niveau valt vrijwel samen met de **kalima** van de klassieke
grammatica. لَهُمْ is per definitie twee kalimat: لَ is een *harf* en هُمْ een
*ism* — twee van de drie woordsoorten, dus onmogelijk één woord. De corpus
kent elk segment zijn eigen woordsoort toe, wat alleen zinvol is als elk
segment een zelfstandig grammaticaal woord is.

**Vanuit nahw-oogpunt telt de Quran dus 128.189 kalimat** (128.219 minus de 30
muqatta'at-reeksen, die in geen van de drie klassen vallen). De 77.429 zijn
rasm-eenheden, geen kalimat.

Er is nog een derde antwoord. De *damir mustatir* — het هُوَ dat volgens de
grammatici in يَكْتُبُ verborgen zit — is *muqaddar*: verondersteld, niet
geschreven. De corpus annoteert alleen wat er staat, maar de treebank (deel 10)
poneert die elementen wel. Tel je ze mee zoals de grammatici doen, dan komt de
Quran op **139.376 kalimat**. Zichtbare onderwerpssuffixen
(كَتَبُوا۟ = fi'l + waw al-jama'a) tellen in alle drie de tellingen mee.

### Verdeling over de drie klassen

| Soort | Voorkomens | Aandeel | Unieke lemma's |
|---|---|---|---|
| Ism | 62.747 | 48,9% | 3.325 |
| Harf | 46.086 | 35,9% | 46 (+ ~16 aangehecht) |
| Fi'l | 19.356 | 15,1% | 1.475 |
| Muqatta'at | 30 | 0,02% | — |

Bijna de helft van de Quran bestaat uit *asma'*, en voornaamwoorden alleen al
(24.685) zijn goed voor bijna een vijfde van alle kalimat — meer dan alle
werkwoorden samen.

## 2. Root, lemma, woordvorm (`basics`, `root-coverage`)

- **Root**: de abstracte wortel van meestal drie medeklinkers, het semantische
  DNA van een woordfamilie (ك-ت-ب = alles rond schrijven). Zelf geen
  uitspreekbaar woord.
- **Lemma**: de woordenboekvorm van een concreet woord (كِتَٰب "boek",
  كَتَبَ "schrijven", كَاتِب "schrijver" — drie lemma's, één root).
- **Woordvorm**: wat er in de tekst staat, verbogen of vervoegd.

Hiërarchie: 1.642 roots → 4.844 lemma's → alle woordvormen.

Gebroken meervouden zijn in deze corpus **aparte lemma's**: رَجُل (man) en
رِجَال (mannen) staan los van elkaar, terwijl het tweevoud رَجُلَيْنِ wel onder
رَجُل valt. Dat verklaart mede waarom er bijna drie lemma's per root zijn.

### Wat heeft wel en geen root

| Soort | Met root | Totaal | Lemma's met root | Lemma's zonder |
|---|---|---|---|---|
| Fi'l | 19.356 | 19.356 | 1.475 | 0 |
| Harf | 0 | 46.086 | 0 | 46 |
| Ism | 30.612 | 62.747 | 3.182 | 143 |

Het patroon is precies wat de *sarf*-theorie voorspelt: **elk werkwoord heeft
een root, geen enkel harf heeft er een**, en de ism zit ertussenin. De 143
rootloze ism-lemma's zijn de damaa'ir, mawsulaat, ishara-woorden, versteende
zuruf (إِذَا, إِذ, مَع) en vooral **niet-Arabische eigennamen** (مُوسَىٰ,
إِبْرَاهِيم, فِرْعَوْن) die per definitie buiten het wortelsysteem vallen.
Arabische namen als مُحَمَّد (ح-م-د) hebben er wél een.

In unieke lemma's: 96,1% heeft een root. In de lopende tekst: **39,0%**. Het
semantische gewicht zit in vier op de tien woorden; de overige zes zijn
grammaticaal bindweefsel uit een klein, versteend, rootloos vocabulaire.

## 3. Eén vorm, meer dan één woord (`ambiguity`)

Wanneer is iets een ander woord en wanneer een andere betekenis? Drie niveaus,
met drie verschillende toetsen — alle drie apart queryable in de database.

**Verschillende kalima-klasse = ander woord.** مَا als *ism* en مَا als *harf*
zijn categorisch verschillend: een ism heeft *i'rab*-positie, een harf niet.
Slechts **twee** lemma's overschrijden deze grens: مَا en إِذَا.

**Verschillende functie binnen één klasse = ook een ander woord**, op twee
gronden:

- *De 'amal-toets.* مَا/مَن *shartiyya* is *jazima* en regeert twee werkwoorden
  in de *majzum*; de *istifhamiyya* regeert niets. In de nahw is 'amal een
  lexicale eigenschap van het woord zelf.
- *De vormtoets, en die staat in de data.* Na een voorzetsel verliest de
  istifhamiyya haar alif (لِمَ, بِمَ, عَمَّ); de mawsula en masdariyya houden
  hem. Van de 25 alif-loze gevallen zijn er **24 istifhamiyya**. De enige
  uitzondering is 86:5 مِمَّ خُلِقَ, dat de corpus als mawsula tagt terwijl de
  meeste grammatici er istifham lezen — zou dat kloppen, dan is de regel
  uitzonderingsloos. Twee woorden met een verschillende geschreven vorm zijn
  geen één woord.

Op die basis telt de Quran **4.929 verschillende woorden** (onderscheiden op
lemma + kalima_type + wazifa) tegenover 4.844 kale lemma's.

مَا splitst in zeven woorden:

| Klasse | Functie | Aantal |
|---|---|---|
| ism | mawsulah | 1.476 |
| harf | nafiyah | 705 |
| harf | kaffah (إنّما) | 162 |
| ism | istifhamiyyah | 95 |
| harf | masdariyyah | 83 |
| ism | shartiyyah | 23 |
| harf | zaidah | 21 |

**Wujuh zijn iets anders.** De zeventien betekenissen van هدى zijn géén
zeventien woorden — dat is één woord met meerdere betekenissen (polysemie).
Zie deel 7.

Grensgeval: مَن *mawsula* en *shartiyya* liggen semantisch vlak naast elkaar
en de mufassirun twisten geregeld over welke er staat. Taalkundig heet dit
heterosemie: geen zuivere homonymie, maar ook geen gewone polysemie.

## 4. Frequentie (`top-kalimat`, `top-roots`, `huruf`)

De top van de 128.189 kalimat wordt gedomineerd door wat in de traditionele
telling niet eens als woord meetelt:

| # | Kalima | Soort | Aantal | Cum. |
|---|---|---|---|---|
| 1 | وَ | harf | 9.566 | 7,5% |
| 2 | ٱل | harf | 8.377 | 14,0% |
| 3 | هُم | ism | 8.272 | 20,5% |
| 4 | أَنتُم | ism | 5.175 | 24,5% |
| 5 | هُوَ | ism | 3.845 | 27,5% |
| 6 | مِن | harf | 3.226 | 30,0% |
| 7 | فَ | harf | 3.001 | 32,3% |
| 8 | ٱللَّه | ism | 2.699 | 34,4% |
| 14 | قَالَ | fi'l | 1.618 | 43,7% |

- **De top 3 is 20% van de hele tekst.** De top 20 dekt 50,5%, de **top 100
  dekt 72,9%** — wie die honderd woorden kent herkent bijna drie van elke vier.
- Het frequentste werkwoord is قَالَ, passend voor een tekst die grotendeels
  uit weergegeven spraak bestaat.
- Het hele grammaticale skelet draait op ongeveer **60 verschillende huruf**
  (46 zelfstandige lemma's plus ~16 aangehechte), tegenover ~4.800 inhoudelijke
  lemma's.

De وَ is met zes functies het veelzijdigste woord: 'atf 8.177, isti'nafiyya
1.034, haliyya 293, za'ida 59, **qasam 28** (dan is het een *harf jarr*) en
ma'iyya 3.

### Roots

| # | Root | Betekenis | Lemma's | Aantal | Cum. |
|---|---|---|---|---|---|
| 1 | اله | God | 3 | 2.851 | 5,7% |
| 2 | قول | zeggen | 6 | 1.722 | 9,2% |
| 3 | كون | zijn | 3 | 1.390 | 11,9% |
| 4 | ربب | Heer | 4 | 980 | 13,9% |
| 5 | امن | geloven | 17 | 879 | 15,7% |
| 6 | علم | weten | 14 | 854 | 17,4% |
| 7 | قوم | staan, volk | 22 | 660 | 18,7% |

De top 25 dekt een derde van alle root-dragende woorden, de top 100 zes-tiende.
De lijst leest als de kernboodschap zelf: God (اله, ربب) spreekt (قول) tot de
mens over geloof (امن) en ongeloof (كفر), kennis (علم), tekenen (ايي),
boodschappers (رسل), leiding (هدي), barmhartigheid (رحم) en straf (عذب).

**Frequentie en vruchtbaarheid zijn onafhankelijk.** قوم brengt 22 lemma's
voort, اله maar drie (ٱللَّه 2.699×, إِلَٰه 147× waarvan 34× het meervoud
ءَالِهَة, en ٱللَّهُمَّ 5×). Omgekeerd zijn er zeer frequente roots met precies
één lemma: ارض (461×), يوم, ايي, سبل, اهل, يدي — concrete naamwoorden die in
de Qurantekst nooit een woordfamilie ontwikkelden.

## 5. Djoez Amma (`juz-amma`, `surah-coverage`)

| | Djoez Amma | Hele Quran | Aandeel |
|---|---|---|---|
| Unieke roots | **529** | 1.642 | 32% |
| Unieke lemma's | **849** | 4.844 | 18% |
| Verzen | 564 | 6.236 | 9% |
| Geschreven woorden | 2.308 | 77.429 | **3%** |

Met 3% van de tekst raak je een derde van alle roots aan: de korte Mekkaanse
soera's herhalen weinig en gebruiken veel gevarieerd, beeldend vocabulaire.
Bovendien komen **65 roots en 233 lemma's uitsluitend hier voor** — nergens
anders in de Quran.

Wie Djoez Amma volledig beheerst kent ongeveer **875 woorden**: 849 lemma's,
plus ~14 aangehechte huruf, minus/plus de dubbelgangers die naar functie
uiteenvallen (zoals de vier verschillende مَا's die er voorkomen).

### Is Djoez Amma een goede start om Quran-Arabisch te leren?

Ja, maar niet om de reden die je zou denken.

- Het vocabulaire dekt **83,2% van de hele Quran** — je krijgt het complete
  grammaticale skelet (huruf en damaa'ir, samen 61% van de tekst) cadeau.
- Maar als **pure vocabulaire-investering** is het inefficiënt: de 849
  frequentste lemma's van de Quran zouden **92,5%** dekken, en de overlap
  tussen beide sets is maar 382 lemma's. Ruim de helft van het Djoez
  Amma-vocabulaire is relatief zeldzaam.
- Je ziet er maar **263 van de 1.475 werkwoordlemma's**: weinig verhalend
  proza, dus weinig vervoegingsvariatie.
- Stilistisch is het juist het *moeilijkste* register: eden, elliptische zinnen,
  apocalyptische beeldspraak.

Advies dat hieruit volgt: gebruik het als startpunt (motivatie, bestaande
memorisatie, grammaticaal skelet), maar combineer het met gerichte
frequentiestudie.

### Welke soera is daarna het toegankelijkst

Dekkingspercentage van elke soera buiten Djoez Amma, gegeven dat je het
Djoez Amma-vocabulaire kent:

| Soera | Lemma-dekking | Root-dekking | Verzen |
|---|---|---|---|
| 64 At-Taghabun | **87,7%** | 95,0% | 18 |
| 45 Al-Jathiya | 87,2% | 95,2% | 37 |
| 29 Al-Ankabut | 85,5% | 93,2% | 69 |
| 41 Fussilat | 85,4% | 94,3% | 54 |
| 67 Al-Mulk | 84,3% | 92,1% | 30 |
| ... | | | |
| 55 Ar-Rahman | **70,9%** | 87,3% | 78 |

At-Taghabun is thematisch een verlengstuk van Djoez Amma: schepping,
opstanding, *yawm at-taghabun*, geloof en ongeloof. Ar-Rahman staat onderaan
door zijn paradijsbeschrijvingen vol vocabulaire dat nergens in Djoez Amma
voorkomt. Zelfs Al-Fatiha haalt maar 77,1%: op 29 woorden wegen unieke woorden
als نَسْتَعِينُ en ٱلضَّآلِّينَ meteen zwaar.

De bandbreedte is smal (71–88%): élke soera is voor ruim zeven tiende
herkenbaar, want het grammaticale skelet is overal hetzelfde.

## 6. Is de lexicaal meest gevarieerde djoez de nuttigste start? (`juz`)

Nee — en dit is de contra-intuïtiefste bevinding van deze analyse.

Op **lexicale variatie** telt djoez 29 (Tabarak, soera 67–77) nipt meer unieke
roots dan Djoez Amma: 537 tegen 529. De laatste twee djoez tellen er de meeste
van alle dertig; de midden-djoez (10, 11, 24) de minste met ~370. Dat verschil
is een eigenschap van het register: korte, opeenvolgende soera's introduceren
per woord vaker een nieuwe root dan doorlopend verhalend proza, dat een
kernvocabulaire herneemt.

Maar meet je **transferwaarde** — welk deel van de héle Quran je met dat
vocabulaire dekt — dan kantelt de ranglijst compleet:

| Djoez | Lemma's | Dekt van hele Quran | Per lemma |
|---|---|---|---|
| 26 | 783 | **87,4%** | 0,112% |
| 25 | 706 | 87,3% | 0,124% |
| 21 | 699 | 87,1% | 0,125% |
| ... | | | |
| 10 | 637 | 84,3% | 0,132% |
| **30 (Amma)** | 849 | **83,2%** | **0,098%** |

**Djoez Amma staat op transferwaarde helemaal onderaan** — dankzij, niet
ondanks, zijn 849 lemma's. Veel van dat vocabulaire komt zelden elders voor, en
draagt dus weinig bij aan het lezen van de rest. Het rendement per geleerd
lemma is er het laagst van alle dertig; de midden-djoez, waar een kleiner
kernvocabulaire vaker terugkeert, leveren per woord ~35% meer op.

De eerlijke relativering: de bandbreedte is slechts 83–87%. Elke djoez geeft
grofweg hetzelfde fundament. Het verschil tussen de "beste" en "slechtste"
startkeuze is vier procentpunten — verwaarloosbaar tegenover het verschil
tussen wél of niet beginnen.

## 7. Wujuh: één woord, meer betekenissen (`wujuh`, `wujuh-juz-amma`)

De corpus annoteert vorm en functie, maar geen betekenis. Die laag komt uit
vier klassieke werken over *al-wujuh wa-n-naza'ir*, samen vier eeuwen traditie
(200–597 AH). Zie README.md voor de bronnen en de pijplijn.

**7.637 → 12.344 citaatrijen**, 1.083 entries, 450 roots, waarvan 9.947 rijen
gekoppeld aan het concrete woord in het vers. 3.284 canonieke senses, waarvan
**442 door drie of meer werken gedragen**.

De sterkste validatie kwam van هدى: Ibn Sallam (2e eeuw) geeft er 17 wujuh,
Ibn al-Jawzi (6e eeuw) 18 — met vrijwel dezelfde glossen in dezelfde volgorde
(*bayan*, *din al-islam*, *iman*, *du'a*, *ma'rifa/'irfan*, *amr Muhammad*,
*rashad*…). Vier eeuwen overlevering, nagenoeg identiek doorgegeven, langs
drie onafhankelijk gedigitaliseerde teksten en drie eigen parsers.

### Polysemie in Djoez Amma

31 lemma's dragen daar meer dan één wajh (van 137 gelabelde lemma's):

| Lemma | Root | Wujuh | Verzen |
|---|---|---|---|
| إِنسَٰن | انس | 10 | 15 |
| أَحَد | احد | 6 | 4 |
| كَرِيم | كرم | 6 | 4 |
| دِين | دين | 5 | 3 |

دِين krijgt er drie verschillende betekenissen: *hisab/jaza'* (83:11),
*tawhid/milla* (98:5) en *'adad* (107:1).

En breder: **436 van de 849 lemma's** in Djoez Amma (51%) behoren tot een root
die de geleerden ergens in de Quran meerdere betekenissen toekennen.

## 8. Referentiële wujuh (`referents`)

Bij إِنسَٰن gebeurt iets anders dan polysemie: de betekenis blijft "de mens",
maar de exegeten identificeren per vers een andere **persoon**.

| Vers | al-Damaghani | Ibn al-Jawzi |
|---|---|---|
| 79:35 | — | kinderen van Adam |
| 80:17 | 'Utba ibn Abi Lahab | — |
| 80:24 | 'Utba ibn Abi Lahab | **Abu Jahl** |
| 82:6 | Asid ibn Khalaf | **Abu Jahl** |
| 86:5 | **Abu Talib** | **Abu Jahl** |
| 89:15, 89:23 | Umayya ibn Khalaf | **Abu Jahl** |
| 90:4 | Kalada ibn Asid | **Abu Jahl** |
| 95:4 | Hisham óf al-Walid ibn al-Mughira | al-Walid ibn al-Mughira |
| 96:6 | Abu Jahl | Abu Jahl ✓ |
| 100:6 | Qaraz ibn 'Abdallah | Qarat ibn 'Abdallah ✓ |

Ibn al-Jawzi noemt Abu Jahl in tien van zijn dertien identificaties;
al-Damaghani spreidt veel breder en noemt hem één keer. Ze zijn het maar
tweemaal eens. Het scherpste geval is 86:5, waar al-Damaghani **Abu Talib**
leest — de oom die de Profeet beschermde — en Ibn al-Jawzi Abu Jahl.

**De traditie kent dit onderscheid zelf.** Ibn al-Jawzi schrijft in zijn
inleiding dat sommige samenstellers woorden opnamen "waarvan de betekenis op
alle plaatsen één is — zoals *al-balad*, *al-qarya*, *al-madina*, *ar-rajul* en
**al-insan** — behalve dan dat met *al-balad* in dit vers een ander *balad*
bedoeld is dan in dat vers", en dat zij die behandelden "naar het model van de
échte wujuh wa-naza'ir" (*al-haqiqiyya*). Hij noemt precies dit geval, en neemt
het toch op omdat zijn voorgangers dat deden.

Een `wajh_type`-laag (semantisch / referentieel / grammaticaal) is daarmee op
de traditie zelf te funderen. Niet gebouwd: naamdetectie alleen haalt 1,5% van
de senses, en een volledige classificatie zou interpretatiewerk vergen dat niet
op bronnen te baseren is.

## 9. Wat er bewust niet in zit

Eerst het overzicht: elke laag dekt een ander deel van de mushaf, en die
verschillen zijn groot. Dat een vers in een laag ontbreekt betekent dat de
database er niets over zegt — niet dat er niets over te zeggen valt.
`analyses.py dekking` drukt deze tabel af uit de database zelf.

| laag | verzen | dekking | wat erbuiten valt |
|---|--:|--:|---|
| `word_glosses` | 6.236 | 100% | niets: elk geschreven woord is geglosseerd |
| `syntax` (EQTB) | 6.236 | 100% | niets, maar het is één ontleding, geen feit |
| `irab` (al-Nahhas) | 5.108 | 82% | de 1.128 verzen waar hij geen vraag ziet |
| `wujuh` | 3.635 | 58% | verzen die geen van de vier werken citeert — en binnen een gedekt vers alleen het geciteerde woord |
| `riwaya_diff`, farsh | 489 | 8% | verzen waar Hafs en Warsh gelijk lezen |

Binnen het corpus zelf dragen 27.947 van de 77.915 stems geen root (36%): de
partikels, de voornaamwoorden en de namen die het corpus onontleed laat. Van de
1.642 unieke roots heeft 450 (27%) een ingang in een wujuh-werk.

Waar helemaal geen laag voor is:

- **Sense-labels per voorkomen.** De klassieke werken citeren voorbeeldverzen,
  geen uitputtende dekking: 17% van de voorkomens van polyseme roots is
  gelabeld. Tafsir-mining op al-Tabari is geprototypeerd en **gemeten op ~35%
  precisie bij een recall-plafond van ~35%** — afgewezen, omdat een kolom die
  in twee van de drie gevallen fout is de waarde ondermijnt van een laag
  waarvan het hele punt is dat elke rij herleidbaar is tot een genoemde
  autoriteit en een geciteerd vers.
- **Meer klassieke bronnen.** al-Hiri (431 AH) en Muqatils zelfstandige
  *Wujuh* zijn uitputtend gezocht in alle 36 OpenITI-eeuwrepositories
  (13.364 versies) en bestaan daar niet. al-Askari was de laatste beschikbare
  volledige wujuh-tekst.
- **Betekenisverschillen binnen één woordsoort** die de klassieke werken niet
  behandelen. De database kent alleen wat een bron zegt.
- **Een vertaling van de Qoeraan.** De Engelse glossen zijn woord-voor-woord
  hulp, bewust letterlijk; als lopende tekst lezen ze slecht en als vertaling
  moeten ze niet gepresenteerd worden.
- **Tafsir**, in welke vorm dan ook.
- **De zes andere riwaayaat**, en elke qiraa-a buiten die van Aasim en Naafi3.
  Ook de tellingen die per riwaaya verschillen — de versnummering, de ahzaab —
  staan er alleen in de Hafs-vorm in.

## 10. Syntaxis en wat er niet staat (`syntax`)

De laag die zegt welk woord *fa'il* is van welk werkwoord, welk *maf'ul*, welk
*khabar* — de analyse die de klassieke *i'rab*-werken in proza uitvechten, hier
als bevraagbare structuur. 139.376 tokens over 11.693 syntactische zinnen, elk
met zijn relatielabel en een verwijzing naar zijn hoofd.

| Relatie | Arabisch | Voorkomens |
|---|---|---|
| link | متعلق | 14.093 |
| root | — | 13.646 |
| gen | مجرور | 12.961 |
| Obj | مفعول به | 10.627 |
| Subj | فاعل | 10.520 |
| Poss | مضاف إليه | 9.805 |
| conj | معطوف | 5.217 |

### De weggelaten elementen

Het interessantste zit in wat er *niet* staat: 11.157 elementen die de
grammatici in de tekst lezen maar die niet geschreven zijn. De treebank maakt
daarbij een principieel onderscheid.

**Benoemd waar het eenduidig is** (6.673). De *damir mustatir* wordt met vorm en
al ingevuld: (هُوَ) 3.878x, (أَنْتَ) 1.414x, (نحْنُ) 582x, (هِيَ) 371x,
(أنا) 355x. Dat kan ook — يَكْتُبُ kan morfologisch niets anders verbergen dan
هُوَ.

**Alleen als positie waar de reconstructie een oordeel vergt** (4.484), met een
anonieme plaatshouder:

| Rol | Aantal |
|---|---|
| خبر | 1.417 |
| صفة | 756 |
| حال | 684 |
| root (weggelaten hoofdpredicaat) | 437 |
| صلة | 307 |
| مفعول به | 193 |
| خبر إنّ | 152 |
| مفعول مطلق | 93 |

De *khabar mahdhuf* is daarmee wél geponeerd maar niet gereconstrueerd. Bij
1:2 ٱلْحَمْدُ لِلَّهِ staat ٱلْحَمْد als root, dan een lege خبر-positie, en de
لِ hangt daaraan als **متعلق** — precies de relatie waar het grammaticaal om
gaat. Welk woord is weggelaten laat de treebank open, en terecht: de Basriers
neigen naar een *ism fa'il* (كائن، مستقر), de Koefiers naar een werkwoord
(استقر). Een zoekopdracht op die woorden levert nul geponeerde tokens op — het
is consequent doorgevoerd.

Dat maakt deze laag complementair aan al-Nahhas' prozacommentaar uit deel 4:
de treebank geeft de structuur van elk vers, al-Nahhas het argument bij de
verzen waar iets te betwisten valt.

## 11. Riwaayaat: Hafs tegenover Warsh (`riwayat`)

Een **qiraa-a** is de lezing van een qaari-; een **riwaaya** is de overlevering
daarvan door een van zijn leerlingen. Dat onderscheid is niet cosmetisch: Hafs
en Warsh zijn riwaayaat uit **twee verschillende qiraa-aat**, Hafs `عن` Aasim
al-Koefie en Warsh `عن` Naafi3 al-Madanie. Een vergelijking Hafs–Shu3ba zou een
vergelijking bínnen één qiraa-a zijn; Hafs–Warsh is er een tussen twee.

| qaari- | | overleden | riwaayaat |
|---|---|---|---|
| Ibn Kathir al-Makkie | ابن كثير المكي | 120 AH | al-Bazzie, Qoenboel |
| Aasim al-Koefie | عاصم الكوفي | 127 AH | Hafs, Shu3ba |
| Aboe 3Amr al-Basrie | أبو عمرو البصري | 154 AH | al-Doerie, al-Soesie |
| Naafi3 al-Madanie | نافع المدني | 169 AH | Warsh, Qaaloen |

### Letters vergelijken meet het verkeerde

De eerste poging vergeleek de twee teksten letter voor letter. Dat leverde 1.497
verschilplaatsen op, waarvan een filter de alif-gevallen wegsneed — en daarmee
1:4 مَٰلِكِ / مَلِكِ, precies het bekendste verschil dat er is.

De fout zat dieper dan het filter. De twee mushaf-tradities **schrijven dezelfde
klank anders**: dolk-alif tegenover geschreven alif, kleine waw tegenover waw,
twee glyph-vormen voor elke tanwien, andere hamza-zetels, een ander teken voor
de wasl-alif. Wie letters vergelijkt meet spelling. Bij 1:4 is de rasm in beide
tradities identiek (م ل ك); het verschil zit in een diacritisch teken.

Daarom wordt elk woord nu eerst omgezet naar een fonemische transcriptie en
worden díe vergeleken. Dat meet de recitatie, en dat is wat een farsh-verschil
is. De drie tanwien-paren in die omzetting zijn niet geraden maar getoetst: elk
Hafs-woord met een van de zes tanwien-tekens is naast de Buckwalter-vorm van
hetzelfde woord in het corpus gelegd, en elk teken loste op naar precies één van
F / N / K, zonder uitzondering (8.547 gevallen; de twee glyph-vormen per
tanwien blijken 733 tegen 2.900 fathataan, 576 tegen 1.806 dammataan en 599
tegen 1.933 kasrataan).

### Wat er dan overblijft

8.581 plaatsen waar de teksten uiteenlopen, gesorteerd naar wat het verschil ís:

| soort | plaatsen | |
|---|--:|---|
| usul | 4.643 | een regel die geldt waar zijn voorwaarde zich voordoet: silat al-miem, naql, de behandeling van de hamza, de geopende yaa al-idaafa |
| notatie | 3.297 | dezelfde recitatie, andere tekens |
| **farsh** | **564** | wat geen regel verklaart: het verschil per woord |
| uitgesloten | 77 | verschoven woordgrens, uitlijningsartefact, de losse letters |

De 564 farsh-plaatsen zijn 468 woordparen in 489 ayaat, verspreid over 84
soerahs. Al-Baqara heeft er de meeste (41), dan Aal 3Imraan (29) en al-An3aam
(26).

Dat het overgrote deel *usul* is, is zelf het resultaat. Waar mensen "Hafs en
Warsh verschillen" zeggen, gaat het meestal over een handvol woorden; wat de
teksten werkelijk uit elkaar houdt zijn regels die honderden keren toeslaan.
Silat al-miem alleen al — عَلَيْهِمْ dat als عَلَيْهِمُو wordt verbonden — is
819 plaatsen. Eén regel, 819 keer.

### Verschillen die wél per woord zijn

| | Hafs | Warsh |
|---|---|---|
| 1:4 | مَٰلِكِ | مَلِكِ |
| 2:9 | يَخۡدَعُونَ | يُخَٰدِعُونَ |
| 2:132 | وَوَصَّىٰ | وَأَوْصىٰ |
| 3:146 | قَٰتَلَ | قُتِلَ |
| 43:19 | عِبَٰدُ | عِندَ |
| 57:24 | هُوَ | *(ontbreekt)* |
| 72:28 | عَدَدَۢا | عَدَداٗ |

57:24 is het enige geval waar een heel woord aan één kant ontbreekt.

### Wat er niet klopt

Ongeveer 5% van de farsh-lijst is vermoedelijk nog spelling en geen lezing. De
twee tekens die de wasl-alif markeren staan in 0,7% van de gevallen op een
hamzat qat3, waardoor woorden als إذ en إلى als kandidaat binnenkomen. En de
klasse `article_lam` vouwt één korte klinker weg om ٱلَّذِينَ tegen اَ۬لذِينَ
te kunnen leggen — de enige plek waar een korte klinker als notatie wordt
behandeld.

`docs/hafs-warsh.md` bevat de volledige lijst met alle klassen, bedoeld om
nagelopen te worden. Zes riwaayaat staan wel in de tabel `riwayat` maar hun
tekst niet in de repo; zie `SOURCES.md` voor waarom.
