# Naḥw — de zinsleer van het Arabisch

*Een lesboek, met de voorbeelden en tellingen ontleend aan de Qoeraan zelf.*

*Over welke tekst geteld wordt: de morfologie komt uit een corpus dat de
riwaaya van Ḥafṣ ontleedt, de zinsontleding uit de Extended Quranic Treebank.
Waar de riwaayaat de uitgang zélf anders lezen — en dat doen ze op 38 plaatsen —
staat het erbij, want juist daar laat de naḥw zich het best betrappen.*

---

## Vooraf: wat dit boek doet

Het ṣarf-boek eindigde met een zin: *"Wat overblijft is de naḥw: hoe deze
woorden zich in de zin tot elkaar verhouden, en welke uitgangen dat oplevert.
Dat is een tweede boek."* Dit is dat boek.

Ṣarf kijkt naar het woord vóórdat het de zin in gaat. Naḥw kijkt naar wat de
zin ermee doet. Neem مَكْتُوب: dat het van كتب komt en volgens het patroon
مَفْعُول is gevormd, is ṣarf. Dat het in ٱلْكِتَٰبُ مَكْتُوبٌ een *ḫabar* is en
daarom een ḍamma krijgt, is naḥw.

Dit boek verschilt op drie punten van een gewoon naḥw-boek.

**Het telt.** Elke relatie die de treebank kent is telbaar over de hele
Qoeraan. Dat bepaalt de volgorde: je leert eerst wat je duizenden keren
tegenkomt, en je krijgt te horen wanneer iets zeldzaam is.

**Het laat zien wat er níet staat.** De grammatici lezen dingen in de tekst
die er niet geschreven staan — een fāʿil die in het werkwoord zelf zit, een
ḫabar die je erbij moet denken. De treebank markeert die posities, 11.157 keer.
Dit boek telt ze mee in plaats van ze weg te laten.

**Het gebruikt echte voorbeelden waar een leerboek er meestal verzint.** Om te
laten zien wat een uitgang doet, zet een leerboek twee zinnen naast elkaar die
alleen in díe uitgang verschillen. Meestal zijn die twee zinnen zelf bedacht.
Op 38 plaatsen levert de Qoeraan zo'n paar zelf: daar reciteren Ḥafṣ en Warsh
één āya met een verschillende uitgang, en dan staan de twee ontledingen in de
tekst zelf naast elkaar, zonder dat er iets bij verzonnen is.

Bij 34:17 leest Ḥafṣ وَهَلْ **نُجَازِي** إِلَّا **ٱلۡكَفُورَ**. Het werkwoord
staat dan **mabnī li-l-maʿlūm**, de vorm waarin de handelende genoemd wordt, en
dat is hier "Wij" — dezelfde spreker die net جَزَيْنَٰهُم zei. ٱلۡكَفُورَ krijgt
een fatḥa als **mafʿūl bihi**, degene aan wie de handeling voltrokken wordt.
Warsh leest وَهَلْ **يُجَازَىٰ** إِلَّا **ٱلۡكَفُورُ**: nu staat het werkwoord
**mabnī li-l-majhūl**, de vorm waarin de handelende juist níet genoemd wordt.
Er is dan geen mafʿūl bihi meer, en ٱلۡكَفُورُ schuift op naar de vrijgekomen
plaats met de ḍamma die daarbij hoort — **nāʾib al-fāʿil**, de invaller voor de
handelende.

Over de ondankbare zeggen beide lezingen hetzelfde. Wat verschuift is waar de
zin naar wijst: bij Ḥafṣ staat de Vergelder er nadrukkelijk in, bij Warsh valt
Hij weg uit de zin — wat het Arabisch juist doet wanneer de handelende vanzelf
spreekt — en blijft alleen de vergelding staan. Dat is precies de omzetting die
hoofdstuk 12 uitlegt, en beide kanten ervan staan er echt. Zulke gevallen staan
daarom niet achterin als curiosum maar bij het hoofdstuk waar ze thuishoren.

Eén zin vooraf, om misverstand te voorkomen: Ḥafṣ en Warsh zijn allebei de
Qoeraan. Waar ze verschillen is er geen goede en een
foute lezing; er zijn twee overgeleverde lezingen, elk met een sluitende
ontleding, en samen laten ze zien wat de Arabische zin allemaal aankan. Dat de
ene in een database staat en de andere niet is een eigenschap van het
gereedschap, niet van de tekst.


## Wegwijzer: alle relaties op een rij

Dit is de inhoudsopgave van het vak, zoals de treebank hem oplevert: elke
relatie die zij kent, hoe vaak zij geschreven staat, en hoe vaak zij erbij
gedacht wordt. De dertig grootste dekken samen het overgrote deel van de
tekst, en dit boek behandelt ze in volgorde van bruikbaarheid, niet van
grootte.

| Relatie | | Geschreven | Geponeerd | Wat het is | H. |
|---|---|--:|--:|---|--:|
| `Subj` | فاعل | 10.520 | 6.104 | de handelende; staat in rafʿ | 11 |
| `root` | root | 13.646 | 520 | de kern waar de rest van de zin aan hangt | 5 |
| `link` | متعلق | 14.093 | 2 | het woord waar een jarr-groep aan vasthangt | 18 |
| `gen` | مجرور | 12.961 | — | wat na een voorzetsel of als tweede lid van een iḍāfa staat | 17 |
| `Obj` | مفعول به | 10.627 | 225 | degene aan wie de handeling voltrokken wordt | 13 |
| `Poss` | مضاف إليه | 9.805 | 2 | het bepalende lid van de iḍāfa, altijd majrūr | 17 |
| `conj` | معطوف | 5.217 | 25 | aangehaakt met wa, fa, thumma; neemt de iʿrāb over | 19 |
| `Pred` | خبر | 2.955 | 1.444 | wat er over de mubtadaʾ gezegd wordt | 6 |
| `sub` | صلة | 4.039 | 310 | de zin die een betrekkelijk woord zijn inhoud geeft | 20 |
| `Adj` | صفة | 2.976 | 758 | wat een eigenschap toekent en zijn woord in vier dingen volgt | 19 |
| `neg` | نفي | 2.112 | 5 | het partikel dat ontkent | 20 |
| `circ` | حال | 1.257 | 686 | de toestand waarin de handeling zich voltrekt | 15 |
| `emph` | توكيد | 1.546 | — | herhaling die bevestigt | 19 |
| `subj<<in>>` | اسم إن | 1.542 | — | wat إنّ in naṣb zet | 9 |
| `pred<<in>>` | خبر إن | 1.304 | 154 | wat إنّ in rafʿ laat | 9 |
| `cond` | شرط | 1.434 | 6 | wat als voorwaarde gesteld wordt | 20 |
| `rslt` | جواب الشرط | 1.224 | 33 | wat er gebeurt als de voorwaarde ingaat | 20 |
| `Pass` | نائب فاعل | 826 | 255 | wat de plaats van de fāʿil inneemt als die niet genoemd wordt | 12 |
| `pred <<kan>>` | خبر كان | 819 | 86 |  | 8 |
| `subj <<kan>>` | اسم كان | 716 | 81 |  | 8 |
| `App` | بدل | 651 | 2 | het woord waar het eigenlijk om gaat, in plaats van het vorige | 19 |
| `intg` | استفهام | 595 | 3 | het vraagpartikel | 20 |
| `voc` | منادى | 489 | 5 | de aangesprokene, na يا | 14 |
| `cert` | تحقيق | 423 | 1 | قد dat bevestigt | 20 |
| `cog` | مفعول مطلق | 331 | 93 | de maṣdar van het werkwoord zelf, ter versterking | 14 |
| `res` | حصر | 414 | — | إلّا na een ontkenning: alleen | 16 |
| `Pro` | نهي | 387 | 1 | لا dat verbiedt | 20 |
| `subj<<an>>` | اسم أن | 348 | — | wat أنّ in naṣb zet | 9 |
| `pred<<an>>` | خبر أن | 279 | 30 | wat أنّ in rafʿ laat | 9 |
| `sup` | زائد | 283 | — | een partikel dat er staat zonder iets te regeren | 21 |

98 verdere labels met 3.297 plaatsen samen, waarvan 78 labels (1.730 plaatsen) een aparte naasikh benoemen: `subj <<lays>>`, `pred <<ka'ana>>`, `subj <<easaa>>` en zo voort.

Wie het boek als naslagwerk gebruikt, kan hier beginnen: zoek het label op,
en het hoofdstuk waar het bij hoort staat in de kolom ernaast.

---

# Deel I — Wat een uitgang doet

## 1. Iʿrāb en bināʾ

Arabische woorden vallen in twee soorten: woorden waarvan de uitgang verandert
naargelang hun plaats in de zin (**muʿrab**), en woorden die altijd hetzelfde
klinken (**mabnī**).

- **Muʿrab**: de meeste naamwoorden en de imperfecte werkwoordsvorm.
  ٱلْكِتَٰبُ / ٱلْكِتَٰبَ / ٱلْكِتَٰبِ — drie plaatsen, drie uitgangen.
- **Mabnī**: de ḍamāʾir (هُوَ blijft هُوَ), de aanwijzende en
  ism mawṣūl, de partikels, de māḍī en de amr.

Dat onderscheid is de eerste zeef. Wie zich afvraagt waarom een woord een
bepaalde uitgang heeft, moet eerst weten of het die uitgang überhaupt kán
veranderen.

> **Let op**
>
> Mabnī betekent niet dat het woord geen functie heeft. هُوَ kan fāʿil zijn
> en هُ mafʿūl bihi; ze veranderen alleen niet van vorm. De grammatici zeggen
> dan dat het woord *in de plaats van* een iʿrāb-positie staat — **fī maḥall** — en dat begrip komt in hoofdstuk 5 terug.

## 2. De vier posities

Een muʿrab woord staat in één van vier posities. De eerste drie gelden voor
naamwoorden, de vierde voor werkwoorden.

| Positie | Arabisch | Waar je het aan ziet | Wat het meestal betekent |
|---|---|---|---|
| **rafʿ** | رَفْع | ḍamma | de fāʿil, de mubtadaʾ, de ḫabar |
| **naṣb** | نَصْب | fatḥa | de mafʿūl, de ḥāl, de tamyīz |
| **jarr** | جَرّ | kasra | na een voorzetsel, als muḍāf ilayhi |
| **jazm** | جَزْم | sukūn | werkwoord na bepaalde partikels |

Naamwoorden kennen rafʿ, naṣb en jarr; werkwoorden kennen rafʿ, naṣb en jazm.
Geen woordsoort kent alle vier.

Zo vaak komen ze voor in het corpus:


| Positie | Corpuslabel | Aantal |
|---|---|--:|
| rafʿ | `NOM` | 8.954 |
| naṣb | `ACC` | 10.331 |
| jarr | `GEN` | 12.629 |
| naṣb van het werkwoord | `SUBJ` | 1.330 |
| jazm | `JUS` | 1.418 |

De genitief is de grootste, en dat is geen toeval: elk voorzetsel dwingt hem
af, en elke iḍāfa ook. Wie de kasra leert herkennen, heeft de grootste groep
te pakken.

## 3. De tekens, oorspronkelijk en plaatsvervangend

De tabel hierboven is de hoofdregel. Vier groepen woorden wijken af en
gebruiken andere tekens voor dezelfde posities.

| Groep | rafʿ | naṣb | jarr |
|---|---|---|---|
| het gewone naamwoord | ـُ | ـَ | ـِ |
| de vijf asmāʾ (أَبٌ، أَخٌ، حَمٌ، فُو، ذُو) | ـو | ـا | ـي |
| de duaal | ـانِ | ـيْنِ | ـيْنِ |
| het gezonde mannelijke meervoud | ـونَ | ـينَ | ـينَ |
| het gezonde vrouwelijke meervoud | ـُ | **ـِ** | ـِ |
| ġayr munṣarif (ondiptoot) | ـُ | ـَ | **ـَ** |

Twee daarvan zijn valkuilen, en allebei komen ze veel voor.

**Het gezonde vrouwelijke meervoud krijgt in naṣb een kasra, geen fatḥa.**
ٱلصَّٰلِحَٰتِ is mafʿūl bihi met een kasra. Wie de kasra automatisch als
jarr leest, ontleedt de zin verkeerd.

**De ġayr munṣarif krijgt in jarr een fatḥa, geen kasra** — behalve na de
lidwoord-alif of in een iḍāfa, dan krijgt hij zijn kasra terug. Namen als
إِبْرَٰهِيمَ en يَعْقُوبَ horen hierbij.

> **In de riwaayaat**
>
> Bij 11:71 leest Ḥafṣ وَمِن وَرَآءِ إِسْحَٰقَ **يَعْقُوبَ** met een fatḥa, en
> Warsh **يَعْقُوبُ** met een ḍamma. Dat is niet één teken maar een andere
> ontleding: met de fatḥa hangt يعقوب aan het voorafgaande (ġayr munṣarif in
> naṣb), met de ḍamma begint er iets nieuws.

## 4. De aamil — wat een uitgang veroorzaakt

De klassieke naḥw draait om één idee: een uitgang komt niet uit de lucht
vallen, er is iets dat hem veroorzaakt. Dat veroorzakende woord heet de
**ʿāmil** (عَامِل, "werker").

- Een werkwoord maakt zijn fāʿil *marfūʿ* en zijn mafʿūl bihi *manṣūb*.
- Een voorzetsel maakt het volgende woord *majrūr*.
- Het eerste lid van een iḍāfa maakt het tweede *majrūr*.
- إِنَّ maakt haar ism *manṣūb* en haar ḫabar *marfūʿ* — precies
  andersom dan je zou verwachten.

Ontleden is daarom altijd twee vragen tegelijk: welke positie heeft dit woord,
en wat veroorzaakt die. Het antwoord op de tweede vraag is wat een iʿrāb-boek
opschrijft.

## 5. Maḥall min al-iʿrāb — als een hele zin een positie inneemt

Niet alleen woorden hebben een positie; hele zinnen kunnen er een hebben.
ٱلَّذِى **قَالَ** heeft een ṣila die als geheel de plaats van een naamwoord
inneemt. De grammatici zeggen dan dat de zin *fī maḥall* staat — in de plaats
van rafʿ, naṣb of jarr.

Dat geldt ook voor mabnī woorden. هُمْ in لَهُمْ is mabnī en verandert nooit,
maar staat *fī maḥall jarr* omdat لِ een genitief afdwingt.

Dit is het begrip dat de rest van het boek bij elkaar houdt: zodra je een zin
als bouwsteen leert zien, kun je ontleden waar geen uitgang te zien is.

---

# Deel II — De naamwoordelijke zin

## 6. Mubtadaʾ en ḫabar

De eenvoudigste Arabische zin heeft geen werkwoord. Hij bestaat uit twee
naamwoorden: waar de zin over gaat (**mubtadaʾ**, مُبْتَدَأ) en wat erover
gezegd wordt (**ḫabar**, خَبَر). Allebei staan ze in rafʿ.

ٱللَّهُ نُورُ ٱلسَّمَٰوَٰتِ — "Allah is het licht van de hemelen" (24:35).

De treebank vindt 2.955 geschreven ḫabar-relaties. Voorbeelden zoals ze in de
tekst staan, met het woord waaraan de ḫabar hangt:


| Vers | Woord | Hangt aan |
|---|---|---|
| 2:2 | هُدًى | ذَٰلِكَ |
| 2:4 | يُوقِنُونَ | هُمْ |
| 2:5 | ٱلْمُفْلِحُونَ | وَأُو۟لَٰٓئِكَ |
| 2:6 | سَوَآءٌ | ءَأَنذَرْتَهُمْ |
| 2:7 | وَعَلَىٰٓ | غِشَٰوَةٌ |
| 2:11 | مُصْلِحُونَ | نَحْنُ |

De ḫabar hoeft geen los naamwoord te zijn. Het kan een hele zin zijn
(هُمْ يُوقِنُونَ, 2:4), of een voorzetselgroep (وَعَلَىٰ أَبْصَٰرِهِمْ
غِشَٰوَةٌ, 2:7). In dat laatste geval staat de ḫabar vooraan en de mubtadaʾ
erachter — het Arabisch staat dat toe wanneer de ḫabar een bepaling is.

> **In de riwaayaat**
>
> 2:177 لَّيْسَ **ٱلْبِرَّ** أَن تُوَلُّوا۟ وُجُوهَكُمْ, met een fatḥa in
> Ḥafṣ. Dan is ٱلْبِرَّ de ḫabar van لَيْسَ en is *dat jullie je gezichten
> wenden* het ism van لَيْسَ. Warsh leest **ٱلْبِرُّ** met een ḍamma: dan is
> vroomheid het ism en de rest de ḫabar. Dezelfde woorden, en de vraag wat
> waarover uitspraak doet, valt andersom uit.
## 7. Wat er niet staat: de weggelaten ḫabar

De naamwoordelijke zin heeft twee delen, maar het Arabisch schrijft ze niet
allebei altijd op. Bij بِسْمِ ٱللَّهِ staat alleen een voorzetselgroep. De
grammatici vullen aan: *er is een ḫabar (of een fiʿl) die je erbij denkt* —
"met de naam van Allah [begin ik]".

Dat aanvullen heet **taqdīr** (تَقْدِير, "schatten"), en het weggelaten deel
heet **muqaddar** of **maḥdhūf**. Het is geen truc om een gat te dichten: het
Arabisch laat systematisch weg wat de hoorder toch invult, en de grammatica
beschrijft dat door de lege plek te benoemen.

De treebank markeert die lege plekken. Dit is hoe vaak, en op welke posities:

| Positie | | Aantal | Aandeel |
|---|---|--:|--:|
| `Subj` | فاعل | 6.104 | 55% |
| `Pred` | خبر | 1.444 | 13% |
| `Adj` | صفة | 758 | 7% |
| `circ` | حال | 686 | 6% |
| `root` | root | 520 | 5% |
| `sub` | صلة | 310 | 3% |
| `Pass` | نائب فاعل | 255 | 2% |
| `Obj` | مفعول به | 225 | 2% |
| `pred<<in>>` | خبر إن | 154 | 1% |
| `cog` | مفعول مطلق | 93 | 1% |
| `pred <<kan>>` | خبر كان | 86 | 1% |
| `subj <<kan>>` | اسم كان | 81 | 1% |

11.157 geponeerde elementen in totaal, waarvan 6.673 met een woord ingevuld en 4.484 alleen als lege positie.

Dat is één op de twaalf woorden van de Qoeraan dat *niet geschreven staat* en
toch in de ontleding meetelt. De grootste groep — de weggelaten fāʿil — komt
in hoofdstuk 11 aan de orde; die zit meestal in het werkwoord zelf. Hier
gaat het om de tweede groep: 1.444 keer een ḫabar die er niet staat.

Drie standaardgevallen:

**Na een voorzetselgroep of tijdsbepaling.** وَلِلَّهِ ٱلْمَشْرِقُ
وَٱلْمَغْرِبُ (2:115) — "en van Allah is het oosten en het westen". Er is geen
werkwoord en geen los ḫabar-woord; de jarr-groep وَلِلَّهِ hangt aan een
geschatte ḫabar (*ثابتٌ*, "staat vast").

**Na لَوْلَا.** وَلَوْلَا فَضْلُ ٱللَّهِ عَلَيْكُمْ (24:20) — "ware het niet
[dat er] de gunst van Allah over jullie [is]". De ḫabar bij لولا wordt
standaard weggelaten; de grammatici schatten *موجودٌ*.

**In het antwoord.** Op een vraag antwoordt het Arabisch met het ontbrekende
deel alleen. مَاذَآ أَنزَلَ رَبُّكُمْ ۖ قَالُوا۟ خَيْرًا (16:30).

Het spiegelbeeld bestaat ook: een **weggelaten mubtadaʾ**. Bij
سُورَةٌ أَنزَلْنَٰهَا (24:1) lezen de grammatici *هٰذِهِ سورةٌ*.

> **In de riwaayaat**
>
> 36:5 is precies dit hoofdstuk in één woord. Ḥafṣ leest **تَنزِيلَ**
> ٱلْعَزِيزِ ٱلرَّحِيمِ met een fatḥa: dan is تنزيل een *mafʿūl muṭlaq* bij een
> geschat werkwoord — "[Hij zond het neer als] een neerzending van de
> Machtige, de Genadevolle". Warsh leest **تَنزِيلُ** met een ḍamma: dan is het
> de ḫabar van een weggelaten mubtadaʾ — "[dit is] een neerzending van de
> Machtige, de Genadevolle", of de ḫabar van يٓس، وَٱلْقُرْءَانِ ٱلْحَكِيمِ dat
> eraan voorafgaat.
>
> Beide lezingen vullen iets aan wat er niet staat; ze vullen alleen niet
> hetzelfde aan. De fatḥa vraagt om een werkwoord, de ḍamma om een mubtadaʾ.
> Wie vindt dat taqdīr willekeurig is, heeft hier het tegenbewijs: de klinker
> bepaalt wélk woord je erbij moet denken.

## 8. Kāna en haar zusters

Een naamwoordelijke zin kan een werkwoord vóór zich krijgen dat er een tijd
aan geeft. كَانَ is het bekendste. Het laat de mubtadaʾ in rafʿ staan — die
heet dan **ism kāna** — en zet de ḫabar in naṣb: **ḫabar kāna**.

ٱلْبَيْتُ كَبِيرٌ → كَانَ ٱلْبَيْتُ كَبِيرًا.

De zusters van كان doen hetzelfde: لَيْسَ, أَصْبَحَ, أَمْسَى, ظَلَّ, بَاتَ,
صَارَ, مَا زَالَ, مَا دَامَ. Ze heten samen de **nawāsikh** (نَوَاسِخ,
"opheffers"), omdat ze de gewone rafʿ–rafʿ opheffen.

De treebank noemt de naasikh in het label zelf. Dit zijn de twintig die het
vaakst regeren:

| Naasikh | اسم | خبر |
|---|--:|--:|
| `in` | 1.542 | 1.458 |
| `kan` | 797 | 905 |
| `an` | 348 | 309 |
| `lel` | 127 | 129 |
| `la` | 136 | 76 |
| `kn` | 111 | 68 |
| `ma` | 62 | 101 |
| `lays` | 73 | 61 |
| `ykon` | 52 | 55 |
| `tkon` | 33 | 61 |
| `lakin` | 35 | 39 |
| `lakun` | 27 | 27 |
| `ykn` | 29 | 25 |
| `ka'ana` | 25 | 22 |
| `ka` | 25 | 19 |
| `asbah` | 18 | 19 |
| `kant` | 13 | 19 |
| `easaa` | 10 | 16 |
| `layt` | 13 | 10 |
| `tkn` | 10 | 12 |

45 verschillende nawaasikh, samen 7.089 plaatsen.

De lijst is langer dan een grammaticaboek pleegt te geven omdat de treebank
elke vervoegde vorm apart telt: `kan`, `kn`, `ykon`, `tkon`, `ykn`, `kant`,
`nkon` zijn allemaal كان. Bij elkaar opgeteld is كان met bijna 1.400 plaatsen
de grootste naasikh onder de werkwoorden, en إِنَّ met 3.000 de grootste
onder de partikels — die krijgt het volgende hoofdstuk.

Voorbeelden zoals de treebank ze aanwijst:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:75 | فَرِيقٌ | كَانَ |
| 2:114 | أَن | كَانَ |
| 2:143 | ٱللَّهُ | كَانَ |
| 2:170 | ءَابَآؤُهُمْ | كَانَ |
| 2:213 | ٱلنَّاسُ | كَانَ |
| 2:282 | ٱلَّذِى | كَانَ |

**Kāna tāmma.** Soms is كان geen naasikh maar een gewoon werkwoord dat
"gebeuren, bestaan" betekent. Dan heeft het alleen een fāʿil en geen ḫabar.
وَإِن كَانَ ذُو عُسْرَةٍ (2:280) — "en als er een in nood verkerende ís". Het
verschil is te zien aan de uitgang van wat erop volgt: bij كان tāmma blijft
alles in rafʿ.

> **In de riwaayaat**
>
> 30:10 ثُمَّ كَانَ **عَٰقِبَةَ** ٱلَّذِينَ أَسَٰٓـُٔوا۟ ٱلسُّوٓأَىٰٓ, met een
> fatḥa in Ḥafṣ: عاقبة is de ḫabar kāna, en ٱلسُّوٓأَىٰ het ism kāna in rafʿ —
> "toen was het einde van hen die kwaad deden: het slechtste". Warsh leest
> **عَٰقِبَةُ** met een ḍamma en draait het om: عاقبة is dan het ism, en
> السوأى de ḫabar in naṣb. Het ism en de ḫabar wisselen van plaats.
>
> 21:47 laat de andere schakelaar zien. Ḥafṣ: وَإِن كَانَ **مِثْقَالَ** حَبَّةٍ
> — naṣb, dus كان is naasikh en مثقال is de ḫabar, met een weggelaten ism.
> Warsh: **مِثْقَالُ** in rafʿ, dus كان is tāmma en مثقال is gewoon de
> fāʿil: "en al is er [maar] het gewicht van een mosterdzaadje". Dezelfde
> keuze staat op 31:16.

## 9. Inna en haar zusters

إِنَّ doet het omgekeerde van كان: zij zet in **naṣb** wat de mubtadaʾ was en
laat in **rafʿ** wat de ḫabar was.

ٱللَّهَ غَفُورٌ → إِنَّ ٱللَّهَ غَفُورٌ. Het eerste deel heet **ism inna**, het
tweede **ḫabar inna**.

De zusters zijn أَنَّ, كَأَنَّ, لَٰكِنَّ, لَيْتَ en لَعَلَّ. Ze zijn alle zes
partikels, geen werkwoorden, en ze zijn alle zes mabnī.

Met 1.542 ism en 1.458 ḫabar is إِنَّ de vaakst voorkomende naasikh van de
Qoeraan. Voorbeelden:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:6 | ٱلَّذِينَ | إِنَّ |
| 2:20 | ٱللَّهَ | إِنَّ |
| 2:26 | ٱللَّهَ | إِنَّ |
| 2:62 | ٱلَّذِينَ | إِنَّ |
| 2:67 | ٱللَّهَ | إِنَّ |

En de bijbehorende ḫabar:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:6 | لَا | إِنَّ |
| 2:12 | هُمُ | إِنَّهُمْ |
| 2:20 | قَدِيرٌ | إِنَّ |
| 2:26 | لَا | إِنَّ |
| 2:30 | جَاعِلٌ | إِنِّى |

**إِنَّ tegenover أَنَّ.** Dezelfde letters, twee taken. إِنَّ met kasra begint
een zelfstandige zin; أَنَّ met fatḥa maakt van de zin een naamwoord dat
ergens in past — als mubtadaʾ, als mafʿūl bihi, na een voorzetsel. De
vuistregel is dat je أنّ in het Nederlands met "dat" vertaalt en إنّ met niets.

**De verlichte inna.** إِنَّ en أَنَّ kunnen hun shadda verliezen: إِنْ en
أَنْ. Dan verdwijnt de werking meestal ook, en volgt er een gewone zin. Dat
levert het volgende geval op.

> **In de riwaayaat**
>
> 24:9 is één woordgroep die twee kanten op valt. Ḥafṣ leest
> وَٱلْخَٰمِسَةَ **أَنَّ** **غَضَبَ** **ٱللَّهِ** عَلَيْهَآ: أنّ met shadda,
> غضب als haar ism in naṣb, en الله als tweede lid van de iḍāfa in jarr —
> "en het vijfde [getuigenis is] dat de toorn van Allah over haar is".
>
> Warsh leest وَٱلْخَٰمِسَةُ **أَنْ** **غَضِبَ** **ٱللَّهُ** عَلَيْهَا: أن
> zonder shadda en zonder werking, غضب als *fiʿl māḍī*, en
> الله als fāʿil in rafʿ — "en het vijfde is dat Allah toornt over haar". Een
> naamwoord wordt een werkwoord, een iḍāfa wordt een fāʿil, en het
> voorafgaande الخامسة verschuift van naṣb naar rafʿ.
>
> Vier woorden op rij, en de hele constructie kantelt mee. Dit is het beste
> voorbeeld in het boek van iets dat een grammaticaboek zelden kan laten zien:
> dat de klinkers niet ná de ontleding komen, maar de ontleding zíjn.

## 10. Ẓanna en haar zusters

De derde groep die de naamwoordelijke zin verstoort zijn werkwoorden van
menen en weten: ظَنَّ, حَسِبَ, زَعَمَ, رَأَى, عَلِمَ, وَجَدَ, جَعَلَ,
ٱتَّخَذَ. Zij zetten **allebei** de delen in naṣb, en die worden dan hun
eerste en tweede mafʿūl bihi.

زَيْدٌ قَائِمٌ → ظَنَنْتُ زَيْدًا قَائِمًا.

وَتَظُنُّونَ بِٱللَّهِ ٱلظُّنُونَا۠ (33:10). En met جعل:
وَجَعَلُوا۟ ٱلْمَلَٰٓئِكَةَ ... إِنَٰثًا (43:19) — "en zij maakten de engelen
tot vrouwelijke wezens": ٱلْمَلَٰٓئِكَةَ en إِنَٰثًا allebei manṣūb.

De treebank labelt beide leden gewoon als `Obj`; het onderscheid tussen een
eerste en een tweede mafʿūl maakt zij niet. Wie de tweede wil vinden, zoekt
een werkwoord uit deze lijst met twee manṣūb naamwoorden erachter.

Samengevat over de drie groepen:

| Groep | eerste deel | tweede deel |
|---|---|---|
| gewone naamwoordelijke zin | rafʿ | rafʿ |
| كان en zusters | rafʿ | naṣb |
| إنّ en zusters | naṣb | rafʿ |
| ظنّ en zusters | naṣb | naṣb |

Dat is de hele tabel van hoofdstuk 6 tot en met 10 op één regel per groep, en
het is het lonendste rijtje van het boek om uit het hoofd te kennen.

---

# Deel III — De werkwoordelijke zin

## 11. Fiʿl en fāʿil

De tweede grondvorm van de Arabische zin begint met een werkwoord. Daarachter
staat de **fāʿil** (فَاعِل), de handelende, altijd in rafʿ.

خَلَقَ ٱللَّهُ ٱلسَّمَٰوَٰتِ — "Allah schiep de hemelen" (29:44).

Twee dingen die het Nederlands anders doet:

**De volgorde is werkwoord–fāʿil.** Niet ٱللَّهُ خَلَقَ maar خَلَقَ
ٱللَّهُ. Staat het naamwoord tóch voorop, dan is het een naamwoordelijke zin
met een werkwoordelijke ḫabar, en dat is een ander accent — ongeveer het
verschil tussen "Allah schiep" en "Allah, Hij is het die schiep".

**Het werkwoord blijft enkelvoud bij een meervoudige fāʿil.** قَالَ
ٱلرِّجَالُ, niet قَالُوا۟ ٱلرِّجَالُ. Het werkwoord richt zich alleen naar het
geslacht, niet naar het aantal, zolang het vóór de fāʿil staat.

De treebank telt 10.520 geschreven fāʿil-relaties:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:7 | ٱللَّهُ | خَتَمَ |
| 2:10 | ٱللَّهُ | فَزَادَهُمُ |
| 2:13 | ٱلنَّاسُ | ءَامَنَ |

### De verborgen fāʿil

Daarnaast poneert de treebank er 6.104 die niet geschreven staan — meer dan de
helft van alle geponeerde elementen in de hele Qoeraan, en de grootste enkele
post uit de tabel van hoofdstuk 7.

De reden is eenvoudig: in قَالَ zit de fāʿil al. Het Arabisch schrijft
geen los "hij". De grammatici zeggen dat de fāʿil een **ḍamīr mustatir** is —
een verborgen ḍamīr — en ze geven zelfs aan of hij verplicht verborgen
is (bij أَقُولُ kán er geen los أنا staan zonder nadruk) of facultatief (bij
قَالَ mag هو erbij).

ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ (1:6): het werkwoord is een amr, de
fāʿil is verplicht verborgen (*أنتَ*), نا is mafʿūl bihi en ٱلصِّرَٰطَ de
tweede mafʿūl bihi. Drie van de vier delen zijn zichtbaar; de fāʿil niet.

Voor wie leert ontleden is dit de belangrijkste gewoonte om aan te wennen:
**wijs bij elk werkwoord de fāʿil aan, ook als er niets staat.** Zes van de
tien keer staat er niets.

## 12. Nāʾib al-fāʿil

Staat het werkwoord **mabnī li-l-majhūl** — de vorm waarin de handelende niet
genoemd wordt (hoofdstuk 12 van het ṣarf-boek: كُتِبَ, يُكْتَبُ) — dan
verdwijnt de fāʿil helemaal uit de zin. De mafʿūl bihi schuift op naar zijn
plaats en neemt zijn iʿrāb over: van naṣb naar **rafʿ**. Hij heet dan
**nāʾib al-fāʿil** (نَائِب ٱلْفَاعِل), de invaller voor de handelende.

كَتَبَ ٱلرَّجُلُ ٱلْكِتَٰبَ → كُتِبَ ٱلْكِتَٰبُ.

Dat de handelende wegvalt is geen slordigheid maar de betekenis van de vorm:
het Arabisch grijpt naar de majhūl juist wanneer die niet genoemd wordt of niet
genoemd hoeft te worden. Een مِن قِبَلِ-constructie erbij zetten is een
moderne gewoonte, geen klassieke.

826 geschreven plaatsen, en 255 geponeerde:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:48 | شَفَٰعَةٌ | يُقْبَلُ |
| 2:48 | عَدْلٌ | يُؤْخَذُ |
| 2:61 | ٱلذِّلَّةُ | وَضُرِبَتْ |

Staat er geen mafʿūl bihi om te promoveren, dan neemt iets anders die
plaats in — een jarr-groep, een tijdsbepaling, een mafʿūl muṭlaq. In
1:7 ٱلْمَغْضُوبِ **عَلَيْهِمْ** is de jarr-groep de nāʾib al-fāʿil bij het
ism mafʿūl.

> **In de riwaayaat**
>
> 34:17 is de majhūl zelf het verschil. Ḥafṣ leest
> وَهَلْ **نُجَٰزِىٓ** إِلَّا **ٱلْكَفُورَ** — maʿlūm, eerste persoon meervoud,
> met الكفور als mafʿūl bihi in naṣb: "en vergelden Wij [zo] iemand
> anders dan de ondankbare?"
>
> Warsh leest وَهَلْ **يُجَٰزَىٰٓ** إِلَّا **ٱلْكَفُورُ** — majhūl, derde
> persoon, met الكفور als nāʾib al-fāʿil in rafʿ: "en wordt [zo] iemand anders
> vergolden dan de ondankbare?"
>
> Precies de omzetting die dit hoofdstuk beschrijft, en de twee riwaayaat
> voeren hem elk aan één kant uit. In de ene lezing staat de Vergelder er
> nadrukkelijk in ("Wij"); in de andere staat er alleen de vergelding. De
> uitspraak over de ondankbare blijft dezelfde.

## 13. Mafʿūl bihi

De **mafʿūl bihi** (مَفْعُول بِهِ) is degene aan wie de handeling voltrokken
wordt, en hij staat in **naṣb**. Met 10.627 geschreven plaatsen is hij na de
fāʿil de grootste werkwoordsrelatie.

| Vers | Woord | Hangt aan |
|---|---|---|
| 1:5 | إِيَّاكَ | نَعْبُدُ |
| 1:5 | وَإِيَّاكَ | نَسْتَعِينُ |
| 1:6 | ٱلصِّرَٰطَ | ٱهْدِنَا |
| 2:3 | ٱلصَّلَوٰةَ | وَيُقِيمُونَ |
| 2:8 | ءَامَنَّا | يَقُولُ |
| 2:9 | ٱللَّهَ | يُخَٰدِعُونَ |

Drie dingen die de tabel laat zien.

**Hij kan een ḍamīr zijn die aan het werkwoord vastzit.**
In ٱهْدِنَا is نا de mafʿūl bihi, mabnī, *fī maḥall naṣb*.

**Het kan vooropgaan.** إِيَّاكَ نَعْبُدُ (1:5) zet de mafʿūl bihi vóór
het werkwoord. Dat kan alleen met de losse vorm إِيَّا + achtervoegsel, en het
is nadrukkelijk: "U alleen aanbidden wij". De volgorde is hier de betekenis.

**Het kan een hele zin zijn.** يَقُولُ **ءَامَنَّا** (2:8): de zin ءامنّا staat
*fī maḥall naṣb* als mafʿūl bihi van قال. Zeggen neemt in het Arabisch
altijd een zin als voorwerp.

### Overgankelijk en onovergankelijk

Niet elk werkwoord neemt een mafʿūl bihi. جَلَسَ, ذَهَبَ, نَامَ zijn
**lāzim** (لَازِم) — ze blijven bij hun fāʿil. Een deel van de vormen uit het
ṣarf-boek bestaat juist om een lāzim werkwoord overgankelijk te maken: vorm II
en vorm IV doen dat, en de bijbehorende vorm V en X draaien het weer terug.

> **In de riwaayaat**
>
> 6:55 draait precies op dat onderscheid. Ḥafṣ leest
> وَلِتَسْتَبِينَ **سَبِيلُ** ٱلْمُجْرِمِينَ met een ḍamma: تستبين is
> onovergankelijk en vrouwelijk ("opdat de weg van de misdadigers duidelijk
> wórdt"), met سبيل als fāʿil. Warsh leest **سَبِيلَ** met een fatḥa: dan is
> تستبين tweede persoon en overgankelijk ("opdat jij de weg van de misdadigers
> duidelijk máákt"), met سبيل als mafʿūl bihi. Eén klinker beslist of het
> werkwoord een voorwerp heeft.

### De ishtighāl

Er is een constructie waarin een naamwoord vooropgaat terwijl het werkwoord
daarna zijn eigen mafʿūl al bij zich heeft, als ḍamīr. Dan mag het
vooropstaande woord óók in naṣb — veroorzaakt door een geschat werkwoord — of
in rafʿ als mubtadaʾ. Die keuze heet **ishtighāl** (اِشْتِغَال, "bezig zijn"),
en beide zijn correct.

> **In de riwaayaat**
>
> 36:39 laat de twee kanten van de ishtighāl naast elkaar zien. Ḥafṣ:
> **وَٱلْقَمَرَ** قَدَّرْنَٰهُ مَنَازِلَ — القمر met een fatḥa, manṣūb door een
> geschat *قدّرنا*, waarna het geschreven قدّرناه zijn eigen ه als voorwerp
> heeft. Warsh: **وَٱلْقَمَرُ** قَدَّرْنَٰهُ — rafʿ, dus mubtadaʾ, met de hele
> zin قدّرناه منازل als ḫabar. "En de maan — Wij hebben haar standen bepaald."
>
> 16:12 doet hetzelfde binnen één vers. Ḥafṣ: وَٱلشَّمْسَ وَٱلْقَمَرَ
> وَٱلنُّجُومُ **مُسَخَّرَٰتٌۢ** — de eerste twee manṣūb (aangehaakt aan
> سَخَّرَ eerder in het vers), maar النجوم in rafʿ met مسخّرات als ḫabar
> ernaast. Warsh trekt de reeks door: **وَٱلنُّجُومَ مُسَخَّرَٰتٍۭ**, allebei
> manṣūb, النجوم als vierde mafʿūl bihi en مسخّرات als ḥāl daarbij. Waar
> Ḥafṣ halverwege de opsomming naar een nieuwe zin overstapt, loopt Warsh door.

## 14. De andere mafāʿīl

Het Arabisch kent vijf soorten mafʿūl. Alle vijf staan in naṣb; ze verschillen
in wat ze over de handeling zeggen. De mafʿūl bihi is er één van; dit
zijn de andere vier.

**Mafʿūl muṭlaq** (مَفْعُول مُطْلَق), de innerlijke: een maṣdar van hetzelfde
werkwoord, om het te versterken of nader te bepalen.
وَكَلَّمَ ٱللَّهُ مُوسَىٰ **تَكْلِيمًا** (4:164) — "en Allah sprak met Mūsā,
een [werkelijk] spreken". Het Nederlands heeft er geen equivalent voor en
behelpt zich met "waarlijk" of "met nadruk". De treebank telt er 331 geschreven
en 93 geponeerde.

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:25 | رِّزْقًا | رُزِقُوا۟ |
| 2:121 | حَقَّ | يَتْلُونَهُۥ |

> **In de riwaayaat**
>
> 19:34 ذَٰلِكَ عِيسَى ٱبْنُ مَرْيَمَ ۚ **قَوْلَ** ٱلْحَقِّ. Ḥafṣ leest naṣb: een
> mafʿūl muṭlaq bij een geschat *أقول* — "[ik zeg dat] als het ware woord".
> Warsh leest **قَوْلُ** in rafʿ, en dan is het de ḫabar bij een herhaald
> mubtadaʾ: "dat is ʿĪsā de zoon van Maryam — het ware woord."
>
> 10:23 doet hetzelfde: Ḥafṣ **مَّتَٰعَ** ٱلْحَيَوٰةِ ٱلدُّنْيَا als mafʿūl
> muṭlaq of ẓarf, Warsh **مَّتَٰعُ** als ḫabar van een weggelaten mubtadaʾ.
> Allebei de keren is de naṣb de bepaling bij een geschat werkwoord en de rafʿ
> een zelfstandige mededeling.

**Mafʿūl fīhi** (مَفْعُول فِيهِ), tijd en plaats — ook **ẓarf** genoemd.
وَسَبِّحْ بِحَمْدِ رَبِّكَ قَبْلَ طُلُوعِ ٱلشَّمْسِ (20:130). قَبْلَ,
بَعْدَ, عِنْدَ, فَوْقَ, تَحْتَ, يَوْمَ, حِينَ zijn allemaal ẓarf: manṣūb, en
zelf eerste lid van een iḍāfa.

**Mafʿūl lahu** (مَفْعُول لَهُ), de reden: een maṣdar die zegt waaróm.
يَجْعَلُونَ أَصَٰبِعَهُمْ فِىٓ ءَاذَانِهِم مِّنَ ٱلصَّوَٰعِقِ **حَذَرَ**
ٱلْمَوْتِ (2:19) — "uit angst voor de dood". De treebank labelt hem `prp`, 84
plaatsen.

**Mafʿūl maʿahu** (مَفْعُول مَعَهُ), de begeleider: na een وَ die "samen met"
betekent in plaats van "en". Zeldzaam, en in de Qoeraan nauwelijks eenduidig
aan te wijzen.

### De munādā

Bij de manṣūbāt hoort ook de aangesprokene. Na يَا (of أَيُّهَا, of niets) staat
de **munādā** (مُنَادَى) in naṣb wanneer hij muḍāf is of onbepaald-onbedoeld, en
mabnī op ḍamma wanneer hij een enkelvoudige eigennaam is of bepaald bedoeld.

- يَٰعِبَادِ فَٱتَّقُونِ (39:16) — muḍāf, dus manṣūb.
- يَٰٓأَيُّهَا ٱلنَّاسُ (2:21) — أيّها is mabnī op ḍamma *fī maḥall naṣb*, en
  ٱلنَّاسُ is er de ṣifa van, in rafʿ met de bouwvorm mee.

De treebank telt 489 geschreven munādā's. Verreweg de meeste zijn
رَبَّنَا en رَبِّ, allebei muḍāf en dus manṣūb:

| Vers | Woord |
|---|---|
| 2:126 | رَبِّ |
| 2:127 | رَبَّنَا |
| 2:200 | رَبَّنَآ |

## 15. Ḥāl en tamyīz

Twee bepalingen die allebei in naṣb staan en allebei onbepaald zijn, en die
beginners door elkaar halen.

De **ḥāl** (حَال) zegt in welke toestand iemand verkeert terwijl hij iets doet.
Hij hoort bij een persoon of ding — de **ṣāḥib al-ḥāl** — en die is bepaald.

وَلَا تَمْشِ فِى ٱلْأَرْضِ **مَرَحًا** (17:37) — "loop niet uitgelaten over de
aarde".

1.257 geschreven, en 686 geponeerd. Dat de treebank er zoveel poneert komt
doordat een ḥāl ook een hele zin kan zijn:

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:15 | يَعْمَهُونَ | طُغْيَٰنِهِمْ |
| 2:22 | وَأَنتُمْ | تَجْعَلُوا۟ |
| 2:24 | أُعِدَّتْ | ٱلنَّارَ |
| 2:25 | مُتَشَٰبِهًا | وَأُتُوا۟ |

De **tamyīz** (تَمْيِيز) doet iets anders: hij verduidelijkt een vage
hoeveelheid of eigenschap door te zeggen *waarvan*.

وَٱشْتَعَلَ ٱلرَّأْسُ **شَيْبًا** (19:4) — "en het hoofd is ontvlamd van
grijsheid". Niet: het hoofd is in grijze toestand ontvlamd; wél: wat er
ontvlamd is, is de grijsheid.

De treebank labelt hem `Spec`, 223 plaatsen — bijna zes keer minder dan de ḥāl.

**Het onderscheid.** Vraag je "hoe?", dan is het een ḥāl. Vraag je "waarvan?"
of "waarin?", dan is het een tamyīz. Praktisch: een ḥāl hoort bij een bepaald
woord dat al in de zin staat, een tamyīz vult een tekort aan in een woord dat
zonder hem onvolledig is (een getal, een maat, een vergelijkende vorm).

Na een telwoord van 11 tot 99 staat de tamyīz altijd enkelvoud en manṣūb:
إِنِّى رَأَيْتُ **أَحَدَ عَشَرَ كَوْكَبًا** (12:4).

## 16. Istithnāʾ en ḥaṣr

**Istithnāʾ** (اِسْتِثْنَاء) is uitzondering: إِلَّا, غَيْر, سِوَى, خَلَا,
عَدَا, حَاشَا. De hoofdregel:

- Is de zin bevestigend en de **mustathnā minhu** — het geheel waaruit
  uitgezonderd wordt — genoemd, dan staat de **mustathnā** in **naṣb**:
  قَامَ ٱلْقَوْمُ إِلَّا زَيْدًا.
- Is de zin ontkennend en de mustathnā minhu genoemd, dan mag de mustathnā
  naṣb zijn óf de iʿrāb van het geheel overnemen (**badal**).
- Is de mustathnā minhu níet genoemd — de **istithnāʾ mufarragh** — dan krijgt
  het woord na إلّا de iʿrāb die het zonder إلّا ook zou hebben. إلّا werkt dan
  helemaal niet.

Dat laatste geval is verreweg het vaakst, en het is meteen de **ḥaṣr**
(حَصْر): مَا … إِلَّا zegt "niet … behalve", en snijdt zo alles weg behalve
wat er na إلّا staat — "alleen".
De treebank labelt die إلّا als `res`, 414 plaatsen:

| Vers | Woordgroep |
|---|---|
| 2:9 | وَمَا يَخْدَعُونَ إِلَّآ أَنفُسَهُمْ |
| 2:26 | وَمَا يُضِلُّ بِهِۦٓ إِلَّا ٱلْفَٰسِقِينَ |
| 2:99 | وَمَا يَكْفُرُ بِهَآ إِلَّا ٱلْفَٰسِقُونَ |

Let op 2:26 tegenover 2:99: ٱلْفَٰسِقِينَ is manṣūb omdat het mafʿūl bihi
van يُضِلُّ is, ٱلْفَٰسِقُونَ is marfūʿ omdat het fāʿil van يَكْفُرُ is.
Dezelfde constructie, twee iʿrāb-posities, en إلّا heeft er geen van beide
veroorzaakt. Dat is wat "mufarragh" betekent.

De echte mustathnā — `exp` — telt maar 193 plaatsen.

> **In de riwaayaat**
>
> 4:95 لَّا يَسْتَوِى ٱلْقَٰعِدُونَ مِنَ ٱلْمُؤْمِنِينَ **غَيْرُ** أُو۟لِى
> ٱلضَّرَرِ. Ḥafṣ leest غَيْرُ met een ḍamma: dan is het een *ṣifa* bij
> ٱلْقَٰعِدُونَ — "de thuisblijvers ánders dan zij die een gebrek hebben zijn
> niet gelijk". De gehandicapte zit dan niet in de groep die vergeleken wordt.
>
> Warsh leest **غَيْرَ** met een fatḥa: dan is het een istithnāʾ — "de
> thuisblijvers zijn niet gelijk [aan de strijders], behalve zij die een
> gebrek hebben". De gehandicapte zit dan wél in de groep, en wordt er
> uitgezonderd.
>
> Het is een verschil in redenering, niet in uitkomst: allebei zeggen ze dat
> wie een gebrek heeft niet achterblijft bij wie strijdt. De ene lezing bereikt
> dat door hem buiten de vergelijking te houden, de andere door hem er
> uitdrukkelijk uit te tillen. Precies de twee wegen die dit hoofdstuk
> beschrijft.

---

# Deel IV — Wat aan een woord hangt

## 17. Jarr: het voorzetsel en de iḍāfa

Jarr is met 12.629 plaatsen de grootste positie van de Qoeraan, en er
zijn maar twee dingen die hem veroorzaken.

**Het voorzetsel.** مِنْ, إِلَى, عَنْ, عَلَى, فِى, بِ, لِ, كَ, حَتَّى, en de
partikels van de eed وَ, تَ. Alles wat erop volgt is majrūr. De treebank telt
12.961 `gen`-relaties.

**De iḍāfa** (إِضَافَة), de aanhechting: twee naamwoorden waarvan het tweede
het eerste bepaalt. Het eerste heet **muḍāf**, het tweede **muḍāf ilayhi** en
staat in jarr. 9.805 plaatsen.

| Vers | Woord | Hangt aan |
|---|---|---|
| 1:1 | ٱللَّهِ | بِسْمِ |
| 1:2 | ٱلْعَٰلَمِينَ | رَبِّ |
| 1:4 | يَوْمِ | مَٰلِكِ |
| 1:4 | ٱلدِّينِ | يَوْمِ |
| 1:7 | ٱلَّذِينَ | صِرَٰطَ |
| 1:7 | ٱلْمَغْضُوبِ | غَيْرِ |

De vierde regel laat zien dat een iḍāfa door kan lopen: يَوْمِ is muḍāf ilayhi
bij مَٰلِكِ én muḍāf bij ٱلدِّينِ. De hele Fātiḥa staat er vol mee.

Drie regels over de muḍāf die je nergens omheen kunt:

**De muḍāf krijgt nooit een lidwoord en nooit tanwīn.** Niet ٱلْكِتَٰبُ
ٱلرَّجُلِ en niet كِتَٰبٌ ٱلرَّجُلِ, maar كِتَٰبُ ٱلرَّجُلِ. De bepaaldheid
komt van het tweede lid.

**Het gezonde mannelijke meervoud en de duaal verliezen hun nūn.**
مُسْلِمُونَ + ٱلْمَدِينَةِ → مُسْلِمُو ٱلْمَدِينَةِ.

**De muḍāf houdt zijn eigen iʿrāb**, bepaald door zijn plaats in de zin. In
بِسْمِ ٱللَّهِ is اسم majrūr door بِ, en الله majrūr door de iḍāfa — twee
kasra's met twee verschillende oorzaken.

> **In de riwaayaat**
>
> 2:184 is een iḍāfa die er in de ene lezing wel en in de andere niet is.
> Ḥafṣ: وَعَلَى ٱلَّذِينَ يُطِيقُونَهُۥ **فِدْيَةٌ** **طَعَامُ** **مِسْكِينٍ**
> — فدية met tanwīn is een uitgestelde mubtadaʾ, طعام staat er als badal naast
> in rafʿ, en مسكين is enkelvoud: "en op wie het [maar net] aankan rust een
> losprijs: het voeden van één behoeftige."
>
> Warsh: **فِدْيَةُ** **طَعَامِ** **مَسَٰكِينَ** — nu is het één iḍāfa-keten
> van drie leden, فدية zonder tanwīn als muḍāf, طعام als muḍāf ilayhi in jarr
> én zelf muḍāf, en مساكين in het meervoud: "de losprijs van het voeden van
> behoeftigen."
>
> En let op de laatste kasra die er geen is: مَسَٰكِينَ eindigt op een fatḥa
> terwijl het majrūr is. Dat is de ġayr munṣarif uit hoofdstuk 3, hier in het
> wild.
>
> 8:18 laat de iḍāfa met een ism fāʿil zien. Ḥafṣ: إِنَّ ٱللَّهَ **مُوهِنُ**
> **كَيْدِ** ٱلْكَٰفِرِينَ — het ism fāʿil van vorm IV zonder tanwīn, dus in
> iḍāfa met wat erop volgt: "verzwakker van de list der ongelovigen". Warsh:
> **مُوَهِّنٌ** **كَيْدَ** — het ism fāʿil van vorm II *mét* tanwīn, en dan
> werkt het als zijn werkwoord en neemt een mafʿūl bihi in naṣb: "hij die
> de list der ongelovigen verzwakt". Het is de standaardregel van het
> ism fāʿil: met tanwīn regeert het als zijn werkwoord, zonder tanwīn als muḍāf.

### De ẓarf die op een zin uitkomt

Een tijds- of plaatsbepaling die als muḍāf een hele zin bij zich krijgt in
plaats van een naamwoord, mág mabnī worden op een fatḥa in plaats van zijn
eigen iʿrāb te tonen. De grammatici verschillen erover of dat verplicht is.

> **In de riwaayaat**
>
> 5:119 قَالَ ٱللَّهُ هَٰذَا **يَوْمُ** يَنفَعُ ٱلصَّٰدِقِينَ صِدْقُهُمْ.
> Ḥafṣ leest يَوْمُ met een ḍamma: يوم is gewoon de ḫabar van هٰذا, muʿrab, met
> de zin erachter als muḍāf ilayhi. Warsh leest **يَوْمَ** met een fatḥa: dan
> is يوم mabnī omdat het aan een zin is gehecht, en staat het *fī maḥall rafʿ*
> als ḫabar. Dezelfde functie, en toch een andere klinker — omdat de ene
> lezing het woord muʿrab noemt en de andere mabnī. Dit is hoofdstuk 1 en
> hoofdstuk 5 in één woord.

## 18. Taʿalluq — waar een jarr-groep aan hangt

Een voorzetselgroep staat nooit op zichzelf. Hij hangt altijd ergens aan: aan
een werkwoord, aan een ism fāʿil of ism mafʿūl, aan een maṣdar, of — als er niets anders is
— aan een geschat woord. Dat aanhangen heet **taʿalluq** (تَعَلُّق), en het
woord waar hij aan hangt de **mutaʿallaq**.

Met 14.093 plaatsen is dit de grootste relatie in de hele treebank. Groter dan
de fāʿil, groter dan de mafʿūl bihi. Wie Arabisch leest, is meer tijd
bezig met de vraag *waar hangt dit voorzetsel aan* dan met welke vraag ook.

| Vers | Woord | Hangt aan |
|---|---|---|
| 1:1 | بِسْمِ | — |
| 1:2 | لِلَّهِ | — |
| 1:7 | عَلَيْهِمْ | أَنْعَمْتَ |
| 2:2 | فِيهِ | — |
| 2:2 | لِّلْمُتَّقِينَ | — |
| 2:3 | بِٱلْغَيْبِ | يُؤْمِنُونَ |

De streepjes zijn het punt van dit hoofdstuk. Vier van de zes jarr-groepen
hierboven hangen aan een woord dat niet geschreven staat. بِسْمِ ٱللَّهِ hangt
aan een geschat *أبدأ*; ٱلْحَمْدُ لِلَّهِ hangt aan een geschat *ثابتٌ* of
*مستقرٌّ*. De grammatici noemen dat **mutaʿallaq maḥdhūf**, en het is de reden
dat een iʿrāb-commentaar bij het eerste vers van de Qoeraan al een halve
bladzijde nodig heeft.

Wanneer een jarr-groep aan een geschat woord hangt en dat woord een ḫabar of
een ṣifa is, spreken de grammatici van een **shibh al-jumla** (شِبْه ٱلْجُمْلَة,
"zinsgelijkende"): een voorzetselgroep of ẓarf die de plaats van een
naamwoord inneemt. فِى ٱلدَّارِ رَجُلٌ — "in het huis is een man", waarbij de
jarr-groep de ḫabar is.

## 19. De tawābiʿ

Vier soorten woorden hebben geen eigen iʿrāb: ze nemen die van het woord
ervóór over. Ze heten samen de **tawābiʿ** (تَوَابِع, "volgers").

| | Arabisch | Wat het doet | Plaatsen |
|---|---|---|--:|
| **ṣifa** | صِفَة / نَعْت | kent een eigenschap toe | 2.976 |
| **ʿaṭf** | عَطْف | haakt aan met wa, fa, thumma | 5.217 |
| **tawkīd** | تَوْكِيد | herhaalt om te bevestigen | 1.546 |
| **badal** | بَدَل | vervangt wat eraan voorafging | 651 |

**De ṣifa** volgt het bepaalde woord in iʿrāb, aantal, geslacht én
bepaaldheid — vier dingen tegelijk. ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ (1:6): allebei
manṣūb, allebei enkelvoud mannelijk, allebei met lidwoord.

| Vers | Woord | Hangt aan |
|---|---|---|
| 1:1 | ٱلرَّحْمَٰنِ | ٱللَّهِ |
| 1:1 | ٱلرَّحِيمِ | ٱللَّهِ |
| 1:6 | ٱلْمُسْتَقِيمَ | ٱلصِّرَٰطَ |
| 2:3 | ٱلَّذِينَ | لِّلْمُتَّقِينَ |

**Het ʿaṭf** koppelt met وَ, فَ, ثُمَّ, أَوْ, بَلْ, لَٰكِنْ, أَمْ. Wat na het
koppelwoord komt neemt de iʿrāb van wat ervoor stond. Dat maakt het ʿaṭf tot
de gevoeligste van de vier: verandert er één klinker, dan hangt het woord
ineens aan iets anders.

**De tawkīd** herhaalt: نَفْس, عَيْن, كُلّ, جَمِيع, of het woord zelf.
فَسَجَدَ ٱلْمَلَٰٓئِكَةُ **كُلُّهُمْ أَجْمَعُونَ** (15:30) — twee versterkers
achter elkaar, allebei marfūʿ met ٱلْمَلَٰٓئِكَةُ mee.

**De badal** vervangt: het tweede woord is waar het eigenlijk om gaat, het
eerste was een opstapje. ٱهْدِنَا ٱلصِّرَٰطَ ٱلْمُسْتَقِيمَ **صِرَٰطَ**
ٱلَّذِينَ أَنْعَمْتَ عَلَيْهِمْ (1:6–7): het tweede صراط is badal van het
eerste en staat daarom ook in naṣb.

> **In de riwaayaat**
>
> De badal is de plek waar de riwaayaat het vaakst uiteenlopen, en het patroon
> is steeds hetzelfde: waar Ḥafṣ doorloopt met een badal, begint Warsh een
> nieuwe zin — of andersom.
>
> 44:6–7 رَبِّكَ ۚ إِنَّهُۥ هُوَ ٱلسَّمِيعُ ٱلْعَلِيمُ ۝ **رَبِّ**
> ٱلسَّمَٰوَٰتِ. Ḥafṣ leest رَبِّ in jarr: badal van رَبِّكَ, over het
> versnummer heen. Warsh leest **رَبُّ** in rafʿ: een nieuwe zin, "de Heer van
> de hemelen [is Hij]".
>
> 78:37 doet het twee keer in één vers: Ḥafṣ **رَّبِّ** ٱلسَّمَٰوَٰتِ …
> **ٱلرَّحْمَٰنِ**, allebei badal in jarr bij رَبِّكَ uit 78:36; Warsh
> **رَّبُّ** … **ٱلرَّحْمَٰنُ**, allebei rafʿ als mubtadaʾ en ṣifa van een
> nieuwe zin.
>
> 37:126 ٱللَّهَ رَبَّكُمْ وَرَبَّ ءَابَآئِكُمُ ٱلْأَوَّلِينَ bij Ḥafṣ: drie
> woorden in naṣb, badal bij أَحْسَنَ ٱلْخَٰلِقِينَ uit het vers ervoor —
> "verlaten jullie de beste der scheppers, Allah, jullie Heer en de Heer van
> jullie voorvaderen?" Warsh: **ٱللَّهُ رَبُّكُمْ وَرَبُّ** in rafʿ, een
> zelfstandige mededeling: "Allah is jullie Heer en de Heer van jullie
> voorvaderen."
>
> 23:92 en 34:3 herhalen dezelfde keuze bij **عَٰلِمِ** / **عَٰلِمُ**
> ٱلْغَيْبِ.

En bij het ʿaṭf:

> **In de riwaayaat**
>
> 13:4 وَجَنَّٰتٌ مِّنْ أَعْنَٰبٍ وَزَرْعٌ وَنَخِيلٌ صِنْوَانٌ **وَغَيْرُ**
> صِنْوَانٍ. Ḥafṣ leest غَيْرُ in rafʿ, aangehaakt aan نَخِيلٌ. Warsh leest
> **وَغَيْرِ** in jarr, aangehaakt aan صِنْوَانٍ. De opsomming is dezelfde; de
> vraag is alleen op welke hoogte in de opsomming het volgende lid aanhaakt.
>
> 7:26 وَرِيشًا ۖ **وَلِبَاسُ** ٱلتَّقْوَىٰ ذَٰلِكَ خَيْرٌ. Ḥafṣ leest rafʿ:
> een nieuwe naamwoordelijke zin, "en het kleed van de godvrezendheid — dát is
> beter". Warsh leest **وَلِبَاسَ** in naṣb, aangehaakt aan لِبَاسًا eerder in
> het vers: nog een voorwerp van أَنزَلْنَا, en pas daarna begint met ذٰلك de
> mededeling.
>
> 38:84 قَالَ **فَٱلْحَقُّ** **وَٱلْحَقَّ** أَقُولُ. Ḥafṣ zet de twee naast
> elkaar in verschillende posities — de eerste rafʿ als mubtadaʾ, de tweede
> naṣb als mafʿūl bihi van أقول. Warsh leest ze allebei in naṣb:
> **فَٱلْحَقَّ وَٱلْحَقَّ**, de eerste door een geschat werkwoord (*أُحِقُّ*).

### Naṣb ʿalā al-madḥ wa-l-dhamm

Er is nog een reden voor een naṣb die geen van de vier tawābiʿ is: een
naamwoord kan manṣūb staan puur om lof of blaam uit te drukken, veroorzaakt
door een geschat *أمدح* of *أذمّ*. Het onderbreekt dan de reeks tawābiʿ waar
het middenin staat.

> **In de riwaayaat**
>
> 111:4 وَٱمْرَأَتُهُۥ **حَمَّالَةَ** ٱلْحَطَبِ. Ḥafṣ leest naṣb terwijl
> ٱمْرَأَتُهُۥ ervoor in rafʿ staat — dat is precies de naṣb ʿalā al-dhamm:
> "en zijn vrouw — draagster van het brandhout [die zij is]". Warsh leest
> **حَمَّالَةُ** in rafʿ, gewoon als ṣifa bij امرأته of als ḫabar. De blaam
> zit in de ene lezing in de grammatica en in de andere in de woordkeus.

## 20. Zinnen als bouwsteen

Een zin kan in het Arabisch de plaats van een woord innemen. Dat is wat
hoofdstuk 5 *maḥall min al-iʿrāb* noemde, en dit hoofdstuk zet de gevallen op
een rij.

**De ṣila** (صِلَة), de zin na een **ism mawṣūl**. ٱلَّذِى,
ٱلَّتِى, مَا, مَنْ nemen een zin bij zich die hen inhoud geeft. Die zin heeft
zélf geen iʿrāb — de ism mawṣūl heeft er een, en de ṣila
hoort erbij. 4.039 plaatsen, en 310 geponeerde.

| Vers | Woord | Hangt aan |
|---|---|---|
| 2:3 | يُؤْمِنُونَ | ٱلَّذِينَ |
| 2:3 | رَزَقْنَٰهُمْ | وَمِمَّا |
| 2:4 | أُنزِلَ | بِمَآ |
| 2:6 | كَفَرُوا۟ | ٱلَّذِينَ |

Onmisbaar bij de ṣila is de **ʿāʾid** (عَائِد), het terugverwijzende
ḍamīr: رَزَقْنَٰ**هُمْ** — de هم wijst terug naar ما. Zonder ʿāʾid
hangt de ṣila nergens aan vast.

**De sharṭ-zin.** إِنْ, مَنْ, مَا, إِذَا, لَوْ, كُلَّمَا nemen twee zinnen: de
**sharṭ** (شَرْط), wat gesteld wordt, en de **jawāb** (جَوَاب), wat er dan
gebeurt.
1.434 en 1.224 plaatsen.

| Vers | sharṭ | jawāb |
|---|---|---|
| 2:11 | وَإِذَا قِيلَ | قَالُوٓا۟ |
| 2:14 | وَإِذَا لَقُوا۟ | قَالُوٓا۟ |
| 2:17 | فَلَمَّآ أَضَآءَتْ | ذَهَبَ |
| 2:20 | كُلَّمَآ أَضَآءَ | مَّشَوْا۟ |

Bij de echte sharṭ-partikels — إِنْ, مَنْ, مَا, مَهْمَا, أَيْنَ, مَتَىٰ —
staan beide werkwoorden in **jazm**. Bij إِذَا en لَوْ niet: die
nemen een gewone māḍī.

### De uitgangen van het werkwoord

Het imperfectum is het enige muʿrab werkwoord, en het heeft drie posities.

| Positie | Wanneer | Uitgang | Plaatsen |
|---|---|---|--:|
| **rafʿ** | er is geen partikel dat iets doet | ـُ | (rest) |
| **naṣb** | na أَنْ, لَنْ, كَيْ, إِذَنْ, حَتَّىٰ, لَامُ ٱلتَّعْلِيلِ, فَاءُ ٱلسَّبَبِيَّةِ | ـَ | 1.330 |
| **jazm** | na لَمْ, لَمَّا, لَا ٱلنَّاهِيَة, لَامُ ٱلْأَمْرِ, en in de sharṭ-zin | ـْ | 1.418 |

Bij de vijf werkwoorden (تَفْعَلَانِ, يَفْعَلَانِ, تَفْعَلُونَ, يَفْعَلُونَ,
تَفْعَلِينَ) is de nūn het teken van rafʿ, en het wegvallen ervan het teken
van naṣb en jazm.

> **In de riwaayaat**
>
> Vier plaatsen waar de riwaayaat het werkwoord anders vervoegen, en elke keer
> is de vraag dezelfde: hoort deze zin nog bij de vorige of begint hij
> opnieuw?
>
> 2:214 وَزُلْزِلُوا۟ **حَتَّىٰ يَقُولَ** ٱلرَّسُولُ. Ḥafṣ leest naṣb: حتى is
> hier het partikel van doel of grens, en het spreken van de boodschapper is
> het eindpunt waar het schudden op uitloopt. Warsh leest **يَقُولُ** in
> rafʿ: حتى is dan *ibtidāʾiyya*, het begin van een nieuwe zin, en het spreken
> is een feit dat gebeurd ís — "totdat de boodschapper zei".
>
> 42:35 **وَيَعْلَمَ** ٱلَّذِينَ يُجَٰدِلُونَ. Ḥafṣ leest naṣb, aangehaakt aan
> de maṣdar-constructie ervoor. Warsh leest **وَيَعْلَمُ** in rafʿ: een
> zelfstandige mededeling.
>
> 42:51 أَوْ **يُرْسِلَ** رَسُولًا. Ḥafṣ naṣb, aangehaakt aan وَحْيًا via de
> geschatte أن; Warsh **يُرْسِلُ** in rafʿ, opnieuw als losse zin.
>
> 6:27 يَٰلَيْتَنَا نُرَدُّ **وَلَا نُكَذِّبَ** بِـَٔايَٰتِ رَبِّنَا
> **وَنَكُونَ** مِنَ ٱلْمُؤْمِنِينَ. Ḥafṣ leest allebei in naṣb: ze hangen aan
> de wens, en het geheel is één verzoek — "hadden wij maar mogen terugkeren
> zónder de tekenen te loochenen en als gelovigen". Warsh leest **نُكَذِّبُ**
> en **نَكُونُ** in rafʿ: dan zijn het twee losse beloften naast de wens —
> "hadden wij maar mogen terugkeren; wij zullen de tekenen van onze Heer niet
> loochenen en wij zullen tot de gelovigen behoren."
>
> Bij de naṣb is de belofte onderdeel van de wens en dus even onvervuld als de
> wens zelf. Bij de rafʿ staat de belofte er zelfstandig, en het volgende vers
> — بَلْ بَدَا لَهُم مَّا كَانُوا۟ يُخْفُونَ مِن قَبْلُ — antwoordt er dan
> rechtstreeks op. Twee klinkers, en de opbouw van de passage verandert mee.

---

# Deel V — Waar het onbeslist is

## 21. Wanneer de grammatici het oneens zijn

Iʿrāb is een ontleding, geen meting. Twee lezers kunnen dezelfde zin
verschillend ontleden zonder dat een van beiden een fout maakt, en de
klassieke commentaren doen dat voortdurend: al-Naḥḥās, al-ʿUkbarī en Makkī
schrijven halve bladzijden vol met *ويجوز أن يكون* — "en het kan ook zijn dat
het …".

Dit boek gebruikt één ontleding, die van de Extended Quranic Treebank. Het is
belangrijk om te weten wáár die ontleding een keuze maakt.

**De treebank kiest, en zegt dat niet.** Bij بِسْمِ ٱللَّهِ hangt de
jarr-groep aan een geschat woord; welk woord dat is — *أبدأ*, *ابتدائي*,
*باسم الله أقرأ* — is een klassiek twistpunt, en de database noteert alleen
dát er iets geschat wordt.

**21.429 tokens hebben het label `NonRel`.** Dat is een zesde van alle
geschreven tokens: partikels, voegwoorden en voorzetsels waar de treebank geen
zelfstandige relatie aan toekent omdat ze in het label van hun buurman al
verwerkt zijn. Ze zijn niet ongeanalyseerd, maar ze zijn ook niet apart
geteld, en wie de wegwijzertabel vooraan optelt komt daarom niet op
128.219 uit.

**4.484 geponeerde posities zijn leeg.** Van de 11.157 elementen die de
treebank aanvult, is er bij 6.673 een woord ingevuld; bij de rest staat alleen
dát er iets hoort. Meestal is dat een verborgen ḍamīr waarover geen
verschil van mening bestaat. Soms is het een ḫabar of een werkwoord waarover
dat wel bestaat.

**129 verschillende relatielabels.** De 30 uit de wegwijzer dekken het meeste;
de overige 99 zijn goed voor 3.297 plaatsen, en 78 daarvan bestaan alleen
omdat de treebank elke naasikh apart benoemt. `subj <<tkn>>` en
`subj <<kant>>` zijn allebei "ism kāna"; dat het twee labels zijn is een
eigenschap van de database, niet van de grammatica.

Wie een iʿrāb-oordeel uit dit boek in een discussie wil gebruiken, doet er
goed aan de klassieke commentaren ernaast te leggen. De database vertelt
betrouwbaar hoe váák iets voorkomt. Of het op één bepaalde plaats zó ontleed
moet worden, is een vraag die de database niet beantwoordt maar beantwoordt
alsof ze het wel kon.

## 22. Als de riwaayaat de uitgang anders lezen

Het hele boek door stond er telkens een kader met twee lezingen. Dit hoofdstuk
zet ze bij elkaar en telt ze.

Ḥafṣ en Warsh verschillen op 515 plaatsen in de woorden zelf — dat is de
*farsh al-ḥurūf*, en de rest van hun verschillen (ruim 8.000 plaatsen) zit in
de uitspraakregels en de spelling, niet in de tekst. Van die 515 vallen er 48
op de **laatste klinker**: dezelfde medeklinkers, een ander teken aan het eind.

Tien daarvan zijn geen iʿrāb. Ze staan er eerst, omdat het uit elkaar halen
van deze twee groepen precies de vaardigheid is die hoofdstuk 1 vraagt.

| Vers | Ḥafṣ | Warsh | Waarom geen iʿrāb |
|---|---|---|---|
| 7:143 | وَلَٰكِنِ | وَلَٰكِنُ | hulpklinker voor een waṣl-hamza (وَلَٰكِنِ ٱنظُرْ); لكن is mabnī |
| 11:42 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 12:5 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 12:31 | وَقَالَتِ | وَقَالَتُ | hulpklinker voor een waṣl-hamza (وَقَالَتِ ٱخْرُجْ); de تْ is mabnī |
| 15:54 | تُبَشِّرُونَ | تُبَشِّرُونِۖ | yāʾ zāʾida: de weggelaten yāʾ van تُبَشِّرُونَنِي |
| 31:13 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 31:16 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 31:17 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 37:102 | يَٰبُنَيَّ | يَٰبُنَيِّ | yāʾ al-iḍāfa: de yāʾ die "mijn" zegt, geen iʿrāb-uitgang |
| 48:10 | عَلَيۡهُ | عَلَيْهِ | de klinker van de ḍamīr هُ; die is mabnī |

De overige 38 zijn wél iʿrāb: op elk van deze plaatsen lezen de twee
riwaayaat een andere zinsbouw.

| Vers | Ḥafṣ | Warsh | Waar het in dit boek staat |
|---|---|---|---|
| 2:177 | ٱلۡبِرَّ | اَ۬لْبِرُّ | 6 — mubtadaʾ en ḫabar |
| 2:177 | ٱلۡبِرَّ | اِ۬لْبِرُّ | 6 — mubtadaʾ en ḫabar |
| 2:184 | طَعَامُ | طَعَامِ | 17 — de iḍāfa |
| 2:189 | ٱلۡبِرَّ | اِ۬لْبِرُّ | 6 |
| 2:214 | يَقُولَ | يَقُولُ | 20 — de wijzen van het werkwoord |
| 4:95 | غَيۡرُ | غَيْرَ | 16 — istithnāʾ |
| 5:95 | طَعَامُ | طَعَامِ | 17 |
| 5:119 | يَوۡمُ | يَوْمَ | 17 — de ẓarf op een zin |
| 6:27 | نُكَذِّبَ | نُكَذِّبُ | 20 |
| 6:27 | وَنَكُونَ | وَنَكُونُ | 20 |
| 6:55 | سَبِيلُ | سَبِيلَ | 13 — overgankelijk of niet |
| 7:26 | وَلِبَاسُ | وَلِبَاسَ | 19 — ʿaṭf |
| 8:18 | كَيۡدِ | كَيْدَ | 17 — ism fāʿil met of zonder tanwīn |
| 10:23 | مَّتَٰعَ | مَّتَٰعُ | 14 — mafʿūl muṭlaq |
| 11:71 | يَعۡقُوبَ | يَعْقُوبُۖ | 3 — ġayr munṣarif |
| 13:4 | وَغَيۡرُ | وَغَيْرِ | 19 — ʿaṭf |
| 14:2 | ٱللَّهِ | اِ۬للَّهُ | 19 — badal |
| 16:12 | وَٱلنُّجُومُ | وَالنُّجُومَ | 13 — ishtighāl |
| 19:34 | قَوۡلَ | قَوْلُ | 14 |
| 21:47 | مِثۡقَالَ | مِثْقَالُ | 8 — kāna nāqiṣa of tāmma |
| 23:92 | عَٰلِمِ | عَٰلِمُ | 19 — badal |
| 24:9 | وَٱلۡخَٰمِسَةَ | وَالْخَٰمِسَةُ | 9 — inna en anna |
| 24:9 | ٱللَّهِ | اَ۬للَّهُ | 9 — inna en anna |
| 30:10 | عَٰقِبَةَ | عَٰقِبَةُ | 8 — ism en ḫabar van kāna |
| 31:16 | مِثۡقَالَ | مِثْقَالُ | 8 |
| 34:3 | عَٰلِمِ | عَٰلِمُ | 19 |
| 34:17 | ٱلۡكَفُورَ | اَ۬لْكَفُورُۖ | 12 — nāʾib al-fāʿil |
| 36:5 | تَنزِيلَ | تَنزِيلُ | 7 — de weggelaten ḫabar |
| 36:39 | وَٱلۡقَمَرَ | وَالْقَمَرُ | 13 — ishtighāl |
| 37:126 | ٱللَّهَ | اَ۬للَّهُ | 19 — badal |
| 37:126 | وَرَبَّ | وَرَبُّ | 19 — badal |
| 38:84 | فَٱلۡحَقُّ | فَالْحَقَّ | 19 — ʿaṭf |
| 42:35 | وَيَعۡلَمَ | وَيَعْلَمُ | 20 |
| 42:51 | يُرۡسِلَ | يُرْسِلُ | 20 |
| 44:7 | رَبِّ | رَبُّ | 19 — badal |
| 78:37 | رَّبِّ | رَّبُّ | 19 |
| 78:37 | ٱلرَّحۡمَٰنِۖ | اَ۬لرَّحْمَٰنُ | 19 |
| 111:4 | حَمَّالَةَ | حَمَّالَةُ | 19 — naṣb ʿalā al-dhamm |

De vormen staan er zoals de twee mushafs ze schrijven, met de notatie en al —
اَ۬لْبِرُّ is de Maghribi manier om ٱلْبِرُّ te schrijven. 2:177 staat er in de
bron tweemaal in, met twee schrijfwijzen van diezelfde Warsh-lezing; het zijn
38 regels over 37 plaatsen. `docs/hafs-warsh.md` legt de notatie uit.

### Wat de tabel laat zien

Sorteer je de 38 op wat er grammaticaal aan de hand is, dan blijkt het geen
willekeurige verzameling.

**Veertien keer gaat het om de vraag: loopt de zin door of begint hij
opnieuw?** Dat zijn alle badal-gevallen (14:2, 23:92, 24:9, 34:3, 37:126 ×2,
44:7, 78:37 ×2), de drie werkwoordsgevallen van hoofdstuk 20, en 7:26. Steeds
leest de ene riwaaya het woord als aanhaking bij wat eraan voorafging, en de
andere als het begin van een nieuwe mededeling. In een tekst die hardop
gereciteerd wordt is dat geen theoretisch verschil: het bepaalt waar je
adem haalt.

**Zeven keer wisselt een woord van functie binnen dezelfde zin.** 30:10 (ism
wordt ḫabar), 21:47 en 31:16 (ḫabar wordt fāʿil), 34:17 (mafʿūl wordt nāʾib
al-fāʿil), 6:55 (fāʿil wordt mafʿūl), 16:12 en 36:39 (mubtadaʾ wordt mafʿūl).

**Vijf keer verandert de bouw van een woordgroep.** 2:184 en 5:95 (badal wordt
iḍāfa), 8:18 (iḍāfa wordt mafʿūl), 24:9 (iḍāfa wordt fāʿil), 13:4 (het lid
waar de opsomming aanhaakt).

**De rest zijn losse gevallen**: een ġayr munṣarif (11:71), een ẓarf die mabnī
wordt (5:119), een istithnāʾ tegenover een ṣifa (4:95), taqdīr van een
werkwoord tegenover taqdīr van een mubtadaʾ (36:5, 19:34, 10:23, 38:84,
111:4), en tweemaal de ḫabar van لَيْسَ (2:177, 2:189).

### Waarom dit het boek afmaakt

Een naḥw-boek zegt: deze uitgang hoort bij deze functie. Dat is waar, maar het
laat de indruk achter dat de uitgang een gevolg is — eerst staat de zin vast,
daarna volgt de klinker.

Deze 38 plaatsen laten het omgekeerde zien. Hier ligt de zin níet vast. De
medeklinkers zijn identiek, de overlevering is aan beide kanten
ononderbroken, en het is de klinker die bepaalt wat er staat: of الحق hier
mubtadaʾ is of mafʿūl, of غاضب Allah is of Zijn toorn, of de maan de mubtadaʾ
van een nieuwe zin is of de mafʿūl van een geschat werkwoord, of
de wens van de verdoemden in 6:27 hun belofte omvat of ernaast staat.

Dat is de sterkste illustratie die er bestaat van waar dit vak over gaat. De
iʿrāb is niet de administratie achteraf van een zin die er al was. De iʿrāb
ís de zin. En dat twee ononderbroken overleveringen op deze zevenendertig
plaatsen twee verschillende zinnen doorgeven — elk sluitend, elk klassiek
Arabisch, elk de Qoeraan — is niet een probleem dat een grammaticaboek moet
wegpoetsen. Het is het mooiste dat een grammaticaboek te laten heeft.

---

## Verantwoording

De tellingen in dit boek komen uit `quran.db`, de database van dit project.
Elke tabel is met een commando te reproduceren:

| Tabel | Commando |
|---|---|
| de wegwijzertabel (vooraan, h. 21) | `python3 nahw_examples.py relations --markdown` |
| de posities en de wijzen (h. 2) | `python3 nahw_examples.py cases --markdown` |
| geponeerde elementen (h. 7) | `python3 nahw_examples.py muqaddar --markdown` |
| de nawaasikh (h. 8) | `python3 nahw_examples.py nawasikh --markdown` |
| voorbeelden van één relatie | `python3 nahw_examples.py rel Pred --markdown` |
| de 38 iʿrāb-verschillen (h. 22) | `python3 nahw_examples.py irab-book --markdown` |
| de 10 die het niet zijn (h. 22) | `python3 nahw_examples.py irab-mabni --markdown` |

En `python3 validate.py` leest het boek terug: de controle `nahw book examples`
zoekt elk voorbeeld en elk geciteerd woord opnieuw op in de database, zodat een
herbouw dit boek niet stil laat citeren uit gegevens die er niet meer zijn.

De zinsontleding komt uit de **Extended Quranic Treebank** (EQTB), die
128.219 geschreven tokens ontleedt en er 11.157 aan poneert. De morfologie en
de iʿrāb-labels komen uit het **Quranic Arabic Corpus**. Beide beschrijven
de riwaaya van Ḥafṣ.

De riwaaya-verschillen komen uit de mushaf-teksten van het King Fahd Complex,
vergeleken door `compare_riwayat.py`; welke van die verschillen echte
*farsh al-ḥurūf* zijn en welke uitspraakregel of spelling, is per paar
nagelezen en staat in `farsh_review.tsv`. `docs/hafs-warsh.md` beschrijft die
vergelijking, en `SOURCES.md` de herkomst en de licentie van elke bron.

Het bijbehorende vormleerboek is `docs/sarf-nl.md`.
