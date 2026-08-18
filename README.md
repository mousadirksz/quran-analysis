# Quran analysis database

A SQLite database for querying the Quran morphologically, grammatically and
semantically from one place.

It combines three layers:

1. **The Quranic Arabic Corpus** (morphology v0.4): one row per morphological
   segment of the Quran — 128,219 segments, 77,429 written words, 6,236 verses,
   1,642 roots, 4,844 lemmas.
2. **Classical grammar annotation** (*nahw*): two derived columns that restate the
   corpus tags in the categories classical Arabic grammar actually uses —
   `kalima_type` (ism / fiil / harf) and `wazifa` (the function name of a
   particle or of a noun in a functional role).
3. **A wujuh layer** (polysemy): 7,637 rows linking numbered senses from three
   classical *wujuh wa-naza'ir* works to the specific verses their authors cite
   as evidence for each sense.

Everything is plain Python 3 (standard library only) and one SQLite file.

## Quick start

`quran.db` is committed, so no build is needed to query it:

```sh
python3 query.py "SELECT verse_ar FROM ayat WHERE surah = 1"
```

`query.py` is a thin wrapper that prints results with right-to-left marks so
Arabic renders correctly in a terminal. Any SQLite client works equally well.

### Example queries

**1. The most frequent roots, with how many distinct lemmas each spawns.**

```sql
SELECT root_ar, COUNT(*) AS segments, COUNT(DISTINCT lemma) AS lemmas
FROM corpus
WHERE root_ar IS NOT NULL
GROUP BY root_ar
ORDER BY segments DESC
LIMIT 5;
```

```
اله   2851   3
قول   1722   6
كون   1390   3
ربب    980   4
امن    879  17
```

**2. One written form, seven different words.** `maa` (مَا) is spelled the same
everywhere; `kalima_type` + `wazifa` separate the relative pronoun from the
negator, the *masdariyya*, the redundant *maa*, and so on.

```sql
SELECT kalima_type, wazifa, COUNT(*) AS n
FROM corpus
WHERE lemma_ar = 'مَا'
GROUP BY kalima_type, wazifa
ORDER BY n DESC;
```

```
ism    mawsulah        1476
harf   nafiyah          705
harf   kaffah           162
ism    istifhamiyyah     95
harf   masdariyyah       83
ism    shartiyyah        23
harf   zaidah            21
```

**3. Which senses the classical authors give a root, and how many cited verses
attest each sense.**

```sql
SELECT work, sense_nr, gloss, COUNT(DISTINCT surah || ':' || ayah) AS verses
FROM wujuh
WHERE root_ar = 'صلو'
GROUP BY work, sense_nr, gloss
ORDER BY work, sense_nr;
```

```
ibnjawzi   1   (no gloss parsed)   3
ibnjawzi   2   المغفرة              1
ibnjawzi   4   الدعاء               1
ibnjawzi   5   القراءة              1
...
ibnsallam  1   الاستغفار من المخلوقين، ومن الله المغفرة   6
ibnsallam  2   الصلاة التي يصلي المخلوقن لله              4
```

Join `wujuh` to the `ayat` view to read the verses themselves:

```sql
SELECT w.sense_nr, w.gloss, w.surah, w.ayah, a.verse_ar
FROM wujuh w
JOIN ayat a ON a.surah = w.surah AND a.ayah = w.ayah
WHERE w.root_ar = 'صلو' AND w.work = 'ibnjawzi'
ORDER BY w.sense_nr;
```

### Rebuilding the database

`to_sqlite.py` appends rows to an existing table, so delete the database first;
every later script is idempotent.

```sh
rm quran.db
python3 to_sqlite.py            # TSV -> corpus table, views, indexes
python3 add_kalima_type.py      # + kalima_type column
python3 add_damair_lemmas.py    # lemmas for personal pronouns
python3 add_wazifa.py           # + wazifa column
python3 parse_tasarif.py        # sources/tasarif_wujuh.json
python3 parse_damaghani.py      # sources/damaghani_wujuh.json
python3 parse_ibnjawzi.py       # sources/ibnjawzi_wujuh.json
python3 resolve_citations.py    # citations -> surah:ayah
python3 substantiate_jk.py      # retry failures against a second digitization
python3 add_wujuh.py            # build the wujuh table
```

`convert.py` regenerates `quranic-corpus-arabic.tsv` from the raw corpus file
(`quranic-corpus-morphology-0.4.txt`); both files are committed, so this is only
needed if you change the conversion. `app.py` is an optional Streamlit dashboard
and needs `streamlit` and `pandas`.

## Concepts, for readers without Arabic

**Root vs lemma vs segment.** A *root* is an abstract sequence of (usually three)
consonants carrying a semantic field: ك-ت-ب has to do with writing. A *lemma* is a
concrete dictionary word formed from that root (kitab "book", kataba "he wrote").
A *segment* is the smallest grammatical unit: Arabic writes prefixes and suffixes
attached to the stem, so the single written word لَهُمْ is two segments — the
preposition لَ and the pronoun هُمْ. Classical grammar calls such a unit a
*kalima*, which is why the corpus segment, not the written word, is the row here.

**Ism, fiil, harf.** Classical grammar divides every kalima into exactly three
classes: *ism* (noun-like: nouns, adjectives, pronouns, demonstratives,
adverbs of time and place), *fiil* (verb), *harf* (particle — anything that has
meaning only in combination, like prepositions and conjunctions). The corpus'
finer part-of-speech tags map onto this three-way split, with a few corrections
where the corpus tags an interrogative or conditional word as a particle while
classical grammar counts it as an ism.

**Wazifa.** The "job" a word does in the sentence: the same written particle can
be a negator (*nafiyah*), a subordinator (*masdariyyah*), or redundant
(*zaidah*). A word in the classical sense is uniquely identified by
(lemma, kalima_type, wazifa), not by spelling.

**Wujuh wa-naza'ir.** A classical genre of Quranic lexicography: a *wajh*
(plural *wujuh*) is one of the distinct meanings a single Quranic word carries in
different places, and each is documented by quoting verses in which the word
carries that meaning. So "huda" is listed as "explanation" in one verse, "the
religion of Islam" in another, "prayer" in a third. The `wujuh` table turns those
lists into rows: sense number, gloss, and the verse cited for it.

## Schema

### Table `corpus` — 128,219 rows, one per morphological segment

| Column | Meaning |
|---|---|
| `id` | surrogate key |
| `surah`, `ayah`, `word`, `segment` | position: sura, verse, written word, segment within the word |
| `form_bw`, `form_ar` | the segment as written, in Buckwalter transliteration and in Arabic script |
| `tag` | corpus part-of-speech tag, present on every segment (45 values: `N`, `PRON`, `V`, `P`, `CONJ`, `DET`, …) |
| `segment_type` | `PREFIX` (28,670), `STEM` (77,915), `SUFFIX` (21,634) |
| `pos` | part of speech; filled on stems only, NULL on prefixes and suffixes |
| `lemma`, `lemma_ar` | dictionary form, Buckwalter and Arabic |
| `root`, `root_ar` | root, Buckwalter and Arabic; NULL for words without a root (particles, most proper names) |
| `aspect` | `PERF`, `IMPF`, `IMPV` |
| `verb_form` | derived verb form `II`–`XII`; NULL for form I |
| `voice` | `ACT`, `PASS` (marked only where the corpus disambiguates) |
| `derivation` | `PCPL` (participle), `VN` (verbal noun) |
| `person`, `gender`, `number` | `1`/`2`/`3`, `M`/`F`, `S`/`D`/`P` |
| `case` | `NOM`, `ACC`, `GEN` (quoted in SQL: `"case"`) |
| `mood` | `SUBJ`, `JUS` |
| `state` | `INDEF` |
| `prefix` | raw corpus prefix string, e.g. `Al+`, `w:CONJ+`, `bi+` |
| `suffix_pron` | person-gender-number of an attached pronoun, e.g. `3MS`, `2MP` |
| `special` | corpus `SP:` value: `<in~`, `kaAn`, `kaAd` |
| `kalima_type` | **added**: classical word class (below) |
| `wazifa` | **added**: classical function name (below) |

`add_damair_lemmas.py` also fills `lemma`/`lemma_ar` for personal pronouns, which
the corpus leaves empty: every pronoun segment — detached, possessive suffix or
verbal subject suffix — is lemmatized to the canonical detached pronoun of its
person-gender-number cell, the way English "him"/"his" lemmatize to "he".

#### `kalima_type`

| Value | Count | Meaning |
|---|---|---|
| `ism` | 62,747 | noun-like: `N`, `PN`, `ADJ`, `IMPN`, `PRON`, `DEM`, `REL`, `T`, `LOC`, plus interrogative/conditional words that the corpus tags as particles |
| `harf` | 46,086 | particle: everything not ism, fiil or muqatta'at |
| `fiil` | 19,356 | verb (`V`) |
| `muqattaat` | 30 | the disconnected sura-initial letters (`INL`), which fit none of the three classes |

#### `wazifa`

NULL on content words (nouns, verbs, adjectives, pronouns, proper names,
demonstratives, muqatta'at) — 76,140 segments. The other 37 values are derived
one-to-one from the corpus tag, which the corpus annotators assigned in context,
so the label reflects the actual use in that verse. The most frequent:

`jarr` (preposition, 13,006) · `atf` (coordinating conjunction, 9,450) ·
`tarif` (definite article, 8,377) · `mawsulah` (relative, 3,575) ·
`istinafiyyah` (resumptive, 2,925) · `nafiyah` (negation, 2,688) ·
`nasikhah` (inna and its sisters, 2,283) · `tawkid` (emphatic, 1,244) ·
`zarf_zaman` / `zarf_makan` (adverb of time / place, 1,166 / 669) ·
`shartiyyah` (conditional, 1,049) · `istifhamiyyah` (interrogative, 946) ·
`masdariyyah` (subordinating, 684) · `hasr` (restrictive, 558) ·
`tahqiq` (certainty *qad*, 414) · `nida` (vocative, 376) ·
`jawab_shart` (apodosis *fa*, 350) · `nahiyah` (prohibitive, 332) ·
`taliliyyah` (purpose *lam*, 319) · `haliyyah` (circumstantial *waw*, 293) ·
`zaidah` (redundant, 235) · `kaffah` (preventive *maa*, 162) ·
`istiqbal` (future marker, 161) · `idrab` (retraction *bal*, 122) ·
`istithnaiyyah` (exceptive *illa*, 104) · `ibtidaiyyah` (inceptive, 90) ·
`sababiyyah` (causal *fa*, 88) · `amr` (imperative *lam*, 78) ·
`tafsiliyyah` (detailing *amma*, 66) · `istidrak` (amendment *lakin*, 65) ·
`mufassirah` (explicative *an*, 47) · `jawab` (answer particle, 40) ·
`tahdid` (exhortation, 40) · `fujaiyyah` (surprise *idha*, 35) ·
`zajr` (aversion *kalla*, 33) · `taswiyah` (equalizing hamza, 6) ·
`maiyyah` (*waw* of accompaniment, 3).

### Views

| View | Content |
|---|---|
| `words` | one row per written word: `surah`, `ayah`, `word`, `word_ar`, `word_bw` (segments concatenated) |
| `ayat` | one row per verse: `surah`, `ayah`, `verse_ar` (words joined with spaces) |

### Table `wujuh` — 7,637 rows, one per resolved citation

614 headwords across the three works, 3,030 distinct senses, 348 roots, covering
2,955 different verses.

| Column | Meaning |
|---|---|
| `id` | surrogate key |
| `work` | `ibnsallam` (2,343 rows), `damaghani` (2,374), `ibnjawzi` (2,920) |
| `headword` | the entry heading as printed: al-Damaghani writes spaced root letters (`ر ي ب`), Ibn al-Jawzi and Ibn Sallam whole words (`الريب`) |
| `root_ar` | root inferred from the data: the root shared by the entry's cited verses whose letters are compatible with the headword. NULL for 234 rows where no root could be inferred |
| `sense_nr` | the author's own sense number within the entry (the *wajh*) |
| `gloss` | the author's short paraphrase of that sense, as parsed; NULL for 86 rows |
| `quote` | the quoted fragment as it appears in the source text |
| `surah`, `ayah` | the verse the quote resolves to |
| `match_status` | how the quote was resolved (below) |

#### `match_status`

| Value | Rows | Meaning |
|---|---|---|
| `unique` | 5,536 | the normalized quote occurs in exactly one verse — an exact match |
| `ambiguous` | 1,107 | the quote occurs in several verses and the author gave no usable sura hint; every matching verse is stored as its own row |
| `hint_resolved` | 555 | several verses matched, and the author's sura name picked one out |
| `short_hint` | 160 | a quote of one or two words, located through the sura hint or because the phrase occurs in at most three verses Quran-wide |
| `cross_verse` | 131 | the quote runs across a verse boundary; matched against the concatenated sura text and mapped back to the verses it spans |
| `fuzzy` | 112 | no literal match; accepted on consonantal word overlap with a clear best candidate. Authors quote from memory and the digitizations contain typos |
| `prefix` | 36 | only the longest leading part of the quote matched a verse — the tail is the author's own commentary, fused into the quotation by the digitizer |

`unique`, `hint_resolved` and `cross_verse` reproduce the verse text literally
after normalization (`cross_verse` on the consonantal skeleton); `short_hint`,
`prefix` and especially `ambiguous` and `fuzzy` involve inference.

## Pipeline

| Script | What it does |
|---|---|
| `convert.py` | Buckwalter → Arabic script, splits the corpus feature string into columns → `quranic-corpus-arabic.tsv` |
| `to_sqlite.py` | loads the TSV into the `corpus` table, creates the `words` and `ayat` views and the indexes |
| `add_kalima_type.py` | adds `kalima_type` from the corpus tag, with per-lemma corrections where classical grammar disagrees with the corpus |
| `add_damair_lemmas.py` | fills lemmas for personal pronouns |
| `add_wazifa.py` | adds `wazifa`, mapping each corpus tag to its classical function name |
| `parse_tasarif.py` | parses Yahya ibn Sallam's *at-Tasarif* → `sources/tasarif_wujuh.json` |
| `parse_damaghani.py` | parses al-Damaghani's *Qamus al-Quran* → `sources/damaghani_wujuh.json` |
| `parse_ibnjawzi.py` | parses Ibn al-Jawzi's *Nuzhat al-A'yun* → `sources/ibnjawzi_wujuh.json` |
| `resolve_citations.py` | resolves every quoted fragment to sura:aya against the corpus text, in tiers (exact → skeleton → cross-verse → fuzzy) → `sources/resolved_citations.json` |
| `substantiate_jk.py` | retries the quotes that failed against a second, independently typed digitization of Ibn al-Jawzi, and updates `resolved_citations.json` in place |
| `add_wujuh.py` | drops and rebuilds the `wujuh` table from the resolved citations, inferring each entry's root |
| `query.py` | command-line query tool with RTL output |
| `app.py` | optional Streamlit dashboard (needs `streamlit`, `pandas`) |

`OBSERVATIES.md` (Dutch) records findings from the corpus layer: counts,
distributions, and what the kalima/lemma distinction changes about them.

## Sources

**Quranic Arabic Corpus, morphology version 0.4** — Copyright (C) 2011 Kais
Dukes, University of Leeds. GNU General Public License. Built on the verified
Arabic text of the Tanzil project. <https://corpus.quran.com>. The raw file
`quranic-corpus-morphology-0.4.txt` is included verbatim, including its copyright
block; its terms require that the source is credited and linked.

The three wujuh works are OpenITI mARkdown releases of Shamela and JK
digitizations:

| File | Work | Author | Edition |
|---|---|---|---|
| `sources/tasarif.txt` | *at-Tasarif li-tafsir al-Quran mimma ishtabahat asma'uhu wa-tasarrafat ma'anihi* | Yahya ibn Sallam al-Taymi al-Basri al-Qayrawani (d. 200 AH / 815 CE) | al-Sharika al-Tunisiyya li-l-Tawzi', 1979. Shamela_0011783 |
| `sources/damaghani_qamus.txt` | *Qamus al-Quran*, i.e. *Islah al-wujuh wa-l-naza'ir fi l-Quran al-karim* | al-Husayn ibn Muhammad al-Damaghani (d. 478 AH / 1085 CE) | ed. 'Abd al-'Aziz Sayyid al-Ahl, Dar al-'Ilm li-l-Malayin, Beirut, 3rd ed., 1980. Shamela bkid 34085 |
| `sources/ibnjawzi_nuzhat.txt` | *Nuzhat al-A'yun al-Nawazir fi 'ilm al-wujuh wa-l-naza'ir* | Jamal al-Din Abu l-Faraj Ibn al-Jawzi (d. 597 AH / 1201 CE) | ed. Muhammad 'Abd al-Karim Kazim al-Radi, Mu'assasat al-Risala, Beirut, 1st ed., 1404/1984. Shamela_0006334 |
| `sources/ibnjawzi_nuzhat_jk.txt` | same work, second digitization | | same edition, typed independently. JK_007134 |

The OpenITI files carry no license field in their `#META#` headers. OpenITI
generally releases its corpus under CC BY-NC-SA 4.0, but the underlying printed
editions are modern and their status is not settled by that; check before
redistributing. See <https://openiti.org>.

## Known limitations

**The wujuh layer only labels the verses the authors themselves quote.** It is
evidence for a sense, not a full sense-annotation of the Quran. The 348 roots
covered occur 35,814 times in the corpus; only 4,927 of those occurrences (about
14%) sit in a verse that a wujuh row points at. Every other occurrence of a
polysemous word is unlabelled — the database does not know which *wajh* applies
there.

**Part of the citations are matched heuristically.** About 81% of the rows
(`unique`, `hint_resolved`, `cross_verse`) rest on a literal match of the
normalized or consonantal text. The rest do not: `ambiguous` rows list every verse containing
the phrase, so one citation may produce up to ten rows of which only one is the
verse the author meant; `fuzzy` rows were accepted on word overlap. Filter on
`match_status` when precision matters. Across all three works about 99% of the
quoted fragments resolved to something, but that figure measures reach, not
correctness.

**Not every resolved citation reaches the table.** 80 quotes were rescued from
the second Ibn al-Jawzi digitization with status `edition_jk`; `add_wujuh.py`
does not include that status in its accepted set, so those citations are in
`sources/resolved_citations.json` but not in the `wujuh` table. Sense numbers can
therefore have gaps, and a sense whose only citation failed to resolve is absent
entirely.

**Roots in the `wujuh` table are inferred, not read.** The classical works index
by headword, not by root, so `add_wujuh.py` derives the root from the roots the
cited verses actually contain. This misfires on entries for particles and on
headwords typo'd in the digitization; 234 rows have no root at all. Check the
`headword` before trusting a `root_ar` on a small entry.

**One verse can appear more than once for the same sense** when an author quotes
two different fragments of it, and joining `wujuh` to `corpus` on
(surah, ayah, root_ar) multiplies rows further when a verse contains several
segments of the root. Use `DISTINCT` or aggregate.

**The three works do not agree, and are not meant to.** They differ in how many
wujuh a word has, in the order of senses, and in which verse illustrates which
sense — Ibn al-Jawzi lists 19 senses for خير where Ibn Sallam lists 8 and
al-Damaghani 7. Only 36 roots are covered by all three works, and 163 by more
than one. Treat `work` as a dimension, not as replicate measurements.

**Parsing is imperfect on both layers.** Glosses are extracted with regular
expressions from continuous prose and are sometimes truncated or missing;
`kalima_type` and `wazifa` are derived from the corpus' own tagging and inherit
its analytical choices, which are one defensible reading among several. The
reconstructed verse text in the `ayat` view keeps the corpus' non-Arabic markup
characters (`@`, `,`, `.`, `[`), which mark silent letters and pause signs in the
corpus' extended Buckwalter encoding and are passed through unmapped.
