# Quran analysis database

A SQLite database for querying the Quran morphologically, grammatically and
semantically from one place.

It combines four layers:

1. **The Quranic Arabic Corpus** (morphology v0.4): one row per morphological
   segment of the Quran — 128,219 segments, 77,429 written words, 6,236 verses,
   114 suras, 1,642 roots, 4,844 lemmas.
2. **Classical grammar annotation** (*nahw*): two derived columns that restate the
   corpus tags in the categories classical Arabic grammar actually uses —
   `kalima_type` (ism / fiil / harf) and `wazifa` (the function name of a
   particle or of a noun in a functional role).
3. **A wujuh layer** (polysemy): 12,344 rows linking numbered senses from four
   classical *wujuh wa-naza'ir* works — spanning four centuries, from 200 to
   597 AH — to the verses their authors cite as evidence for each sense, and,
   where it can be established, to the individual word in that verse.
4. **A sense alignment**: 5,027 of those senses grouped into 3,284 canonical
   senses that run across the works, so "which reading does the whole tradition
   carry, and which belongs to one author" becomes a query.

Alongside them sit reference tables for suras, verses, ajza' and ahzab.

Everything is plain Python 3 (standard library only) and one SQLite file.

## Quick start

`quran.db` is committed, so no build is needed to query it:

```sh
python3 query.py "SELECT text_ar FROM verses WHERE surah = 1"
```

`query.py` is a thin wrapper that prints results with right-to-left marks so
Arabic renders correctly in a terminal. Any SQLite client works equally well.

### Example queries

Every query below was run against the committed `quran.db`; the output is what
it returns.

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
attest each.** Filtering on `confidence = 'high'` keeps only the citations whose
words were actually found, in exactly one verse.

```sql
SELECT work, sense_nr, gloss, COUNT(DISTINCT surah || ':' || ayah) AS verses
FROM wujuh
WHERE root_ar = 'هدي' AND confidence = 'high'
GROUP BY work, sense_nr, gloss
ORDER BY work, sense_nr
LIMIT 6;
```

```
askari   1   البيان     2      (explanation)
askari   2   الطريق     1      (the road)
askari   3   اللطف      1      (divine kindness)
askari   4   الإيمان    1      (faith)
askari   5   الهادي     3      (the guide)
askari   6   الدعاء     4      (calling, summoning)
```

**4. Read the cited verses, and see which word of the verse the sense is
about.** `form_ar` is the written word the wajh attaches to; `verses.text_ar`
holds the repaired verse text.

```sql
SELECT DISTINCT w.sense_nr, w.gloss, w.form_ar, w.surah, w.ayah, v.text_ar
FROM wujuh w
JOIN verses v ON v.surah = w.surah AND v.ayah = w.ayah
WHERE w.work = 'ibnsallam' AND w.root_ar = 'هدي'
  AND w.confidence = 'high' AND w.corpus_id IS NOT NULL
ORDER BY w.sense_nr, w.surah, w.ayah
LIMIT 4;
```

```
1  بيانا  يَهْدِ         7:100   أَوَلَمْ يَهْدِ لِلَّذِينَ يَرِثُونَ ٱلْأَرْضَ …
1  بيانا  يَهْدِ        20:128   أَفَلَمْ يَهْدِ لَهُمْ كَمْ أَهْلَكْنَا قَبْلَهُم …
1  بيانا  هُدًى         31:5    أُو۟لَٰٓئِكَ عَلَىٰ هُدًى مِّن رَّبِّهِمْ …
1  بيانا  فَهَدَيْنَٰهُمْ  41:17   وَأَمَّا ثَمُودُ فَهَدَيْنَٰهُمْ فَٱسْتَحَبُّوا۟ ٱلْعَمَىٰ …
```

**5. The same wajh across four centuries.** `sense_alignment` gives senses that
match across works one `canonical_id`, so the sense numbering of the individual
authors no longer hides the agreement.

```sql
SELECT canonical_id, canonical_gloss, n_works,
       GROUP_CONCAT(work || ' #' || sense_nr, ', ') AS per_work
FROM sense_alignment
WHERE root_ar = 'هدي' AND n_works = 4
GROUP BY canonical_id, canonical_gloss, n_works
ORDER BY canonical_id
LIMIT 5;
```

```
3056  البيان                              4  ibnsallam #1, damaghani #1, ibnjawzi #1, askari #1
3057  الهدى دين الإسلام                    4  ibnsallam #2, damaghani #2, ibnjawzi #2, askari #9
3058  الإيمان                             4  ibnsallam #3, damaghani #3, ibnjawzi #3, askari #4
3061  الهدى أمر محمد صلى الله عليه وسلم     4  ibnsallam #6, damaghani #8, ibnjawzi #7, askari #8
3069  الإلهام                             4  ibnsallam #17, damaghani #16, ibnjawzi #12, askari #12
```

**6. How much of the wujuh layer is evidence and how much is a candidate list.**

```sql
SELECT confidence, COUNT(*) AS rows,
       COUNT(DISTINCT work || '/' || headword || '/' || sense_nr) AS senses,
       COUNT(DISTINCT surah || ':' || ayah) AS verses
FROM wujuh
GROUP BY confidence
ORDER BY rows DESC;
```

```
high    9242   4713   3008
low     2622    483   1404
medium   480    323    367
```

**7. Join the corpus to the sura metadata.**

```sql
SELECT s.number, s.name_en, s.revelation_type, COUNT(*) AS segments
FROM corpus c
JOIN surahs s ON s.number = c.surah
WHERE c.root_ar = 'صبر'
GROUP BY s.number
ORDER BY segments DESC
LIMIT 5;
```

```
 2  Al-Baqara    medinan   9
18  Al-Kahf      meccan    8
 3  Aal-Imran    medinan   8
16  An-Nahl      meccan    7
 8  Al-Anfal     medinan   5
```

**8. Verses and words per juz.**

```sql
SELECT juz, COUNT(*) AS verses, SUM(word_count) AS words
FROM verses
GROUP BY juz
ORDER BY juz
LIMIT 3;
```

```
1  148  2522
2  111  2578
3  125  2607
```

### Building the database

`build.py` is the canonical runner: it executes every step in order, stops at
the first failure, and never leaves you without a database — the existing
`quran.db` is parked as `quran.db.tmp` for the duration of a full rebuild and
restored if anything goes wrong, with the half-built file kept as
`quran.db.bak`.

```sh
python3 build.py                       # full rebuild from the corpus TSV
python3 build.py --keep                # keep quran.db, re-run the migrations
python3 build.py --from add_wujuh.py   # restart at a step (the parsers are slow)
python3 build.py --list                # print the pipeline order and exit
```

A full run takes a while; the parsers and `resolve_citations.py` are the slow
steps. Every step except `to_sqlite.py` is idempotent, which is what `--keep`
exploits. The last step is `validate.py`, which runs 19 checks over the
finished database (see *Data quality* below) and can also be run on its own:

```sh
python3 validate.py                    # validate ./quran.db
python3 validate.py --sample 0         # spot check every citation, not a sample
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
carries that meaning. Ibn Sallam lists *huda* as *bayan* "explanation" in one
verse, as *din al-islam* "the religion of Islam" in another, as *al-Qur'an* in a
third, and so on through seventeen senses. The `wujuh` table turns those lists
into rows: sense number, gloss, the quoted fragment, and the verse (and where
possible the word) it points at.

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
| `root`, `root_ar` | root, Buckwalter and Arabic; NULL where the corpus gives none — every particle, and the loan names it treats as unanalysable |
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
the corpus leaves empty: all 24,685 pronoun segments — detached, possessive
suffix or verbal subject suffix — are lemmatized to the canonical detached
pronoun of their person-gender-number cell, the way English "him"/"his"
lemmatize to "he".

Proper names are *not* generally rootless: of the 3,911 `PN` segments, 3,016
(77%) carry a root, because most of them are ordinary Arabic words used as names
(`صبر`, `حمد`). It is the *lemma* inventory where they thin out — only 30 of the
107 distinct PN lemmas have a root, the other 77 being the frequent non-Arabic
names (مُوسَىٰ, إِبْرَاهِيم, فِرْعَوْن).

#### `kalima_type`

| Value | Count | Meaning |
|---|---|---|
| `ism` | 62,747 | noun-like: `N`, `PN`, `ADJ`, `IMPN`, `PRON`, `DEM`, `REL`, `T`, `LOC`, plus interrogative/conditional words that the corpus tags as particles |
| `harf` | 46,086 | particle: everything not ism, fiil or muqatta'at |
| `fiil` | 19,356 | verb (`V`) |
| `muqattaat` | 30 | the disconnected sura-initial letters (`INL`), which fit none of the three classes |

The corrections are made per (lemma, tag) pair and move 583 segments from harf
to ism: 346 tagged `INTG` (interrogative) and 237 tagged `COND` (conditional).

#### `wazifa`

NULL on content words (nouns, verbs, adjectives, pronouns, proper names,
demonstratives, muqatta'at) — 76,140 segments. The other 37 values are derived
one-to-one from the corpus tag, which the corpus annotators assigned in context,
so the label reflects the actual use in that verse:

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

### Table `wujuh` — 12,344 rows, one per (citation, verse) pair

1,083 entries (work + headword) across the four works, 4,935 distinct senses,
450 roots, pointing at 3,635 different verses. 9,947 rows also name the
individual word of the verse.

| Column | Meaning |
|---|---|
| `id` | surrogate key |
| `work` | `ibnsallam` (2,571 rows), `askari` (2,584), `damaghani` (4,319), `ibnjawzi` (2,870) |
| `headword` | the entry heading as printed: al-Damaghani writes spaced root letters (`ر ي ب`), the other three whole words (`الريب`) |
| `root_ar` | root inferred from the data: among the roots of the entry's cited verses, the one whose letters are compatible with the headword. NULL on 602 rows, where no root could be established or the inferred one is not corroborated by the headword |
| `sense_nr` | the author's own sense number within the entry (the *wajh*) |
| `gloss` | the author's short paraphrase of that sense, as parsed; NULL on 224 rows |
| `quote` | the quoted fragment as it appears in the source text |
| `surah`, `ayah` | the verse the quote resolves to |
| `word` | the number of the written word within that verse that the wajh is about; NULL when it could not be established |
| `corpus_id` | `corpus.id` of that word's STEM segment; NULL likewise |
| `form_ar` | that word in full, all its segments concatenated |
| `match_status` | fine-grained provenance: how the resolver found the verse (below) |
| `candidate_count` | how many verses the resolver returned for this one citation, i.e. how many rows of this table it produced |
| `confidence` | `high` / `medium` / `low` — how much weight the row may carry (below) |
| `word_status` | how (or why not) the word-level link was made (below) |

#### `confidence` — the column to filter on

`confidence` combines the provenance with the breadth of the citation:

| Value | Rows | Meaning |
|---|---|---|
| `high` | 9,242 | the quoted words were found in the mushaf, and in exactly one verse. Attestation. |
| `medium` | 480 | the verse is likely but not settled: either the wording had to be approximated, or the citation left two or three verses standing |
| `low` | 2,622 | candidate list, not attestation: the phrase occurs in four or more verses and the work does not say which one is meant |

A status ceiling and a breadth cap produce this. The ceiling is per
`match_status`: `unique`, `hint_resolved`, `prefix`, `cross_verse` are *located*
(the quoted words themselves were found) and may reach `high`; `fuzzy`,
`short_hint`, `edition_jk` are *reconstructed* (approximated) and stop at
`medium`; `ambiguous` is *listed* and stays `low`. The cap then lowers anything
whose citation left several verses standing: 2–3 candidates cap at `medium`,
4 or more at `low`. `cross_verse` is exempt from the cap, because its several
verses are the consecutive parts of one quote rather than alternatives.

#### `match_status` — the provenance underneath

`add_wujuh.py` accepts nine statuses; eight of them occur in the current data.
The ninth, `composite` (a citation split into parts that were resolved
separately), is defined and would reach `high`, but no citation currently
resolves that way.

| Value | Rows | Confidence reached | Meaning |
|---|---|---|---|
| `unique` | 8,582 | high | the normalized quote occurs in exactly one verse |
| `ambiguous` | 2,588 | low | the quote occurs in several verses and the author gave no usable sura hint; every matching verse is stored as its own row |
| `hint_resolved` | 702 | high / medium / low | several verses matched and the author's sura name narrowed it down — to one verse (431 rows), to two or three (237), or to more (34) |
| `fuzzy` | 199 | medium | no literal match; accepted on consonantal word overlap with a clear best candidate |
| `cross_verse` | 182 | high | the quote runs across a verse boundary; matched against the concatenated sura text and mapped back to the verses it spans |
| `prefix` | 67 | high / medium | only the longest leading part of the quote matched a verse — the tail is the author's own commentary, fused into the quotation by the digitizer |
| `short_hint` | 15 | medium | a quote of one or two words, located through the sura hint |
| `edition_jk` | 9 | medium | 7 citations rescued with the help of the second, independently typed digitization of Ibn al-Jawzi, which supplies correctly typed counterparts of garbled quotes. The seven happen to belong to al-Damaghani (5), Ibn Sallam (1) and al-Askari (1) — a quote is matched against the JK text whatever work it comes from |

#### `word_status` — the word-level link

| Value | Rows | Meaning |
|---|---|---|
| `root_unique` | 8,883 | exactly one word in the verse carries the entry's root |
| `quote_span` | 1,064 | several did; exactly one falls inside the cited span |
| `root_absent` | 1,106 | the entry's root does not occur in this verse |
| `multi_in_span` | 577 | several candidates inside the cited span |
| `root_unverified` | 326 | the inferred root is not corroborated by the headword (particle entries, where a root is an artefact) |
| `entry_root_unknown` | 276 | no root could be inferred for the entry |
| `root_outside_quote` | 108 | candidates exist, but none inside the cited span |
| `span_unknown` | 4 | several candidates, and the quote could not be located in the verse |

Only the first two fill `word`, `corpus_id` and `form_ar`; the other six leave
them NULL rather than guess. For `entry_root_unknown` and `root_unverified`,
`root_ar` is NULL as well: a stored root reads as a claim about the entry and
would be counted as one.

### Table `sense_alignment` — 5,027 rows

Canonical sense ids laid across the works: 5,027 aligned senses grouped into
3,284 canonical senses, of which 442 are carried by three or more works and 140
by all four. Primary key `(work, headword, sense_nr, gloss)` — the gloss is part
of the key because a headword is not unique within a work (al-Damaghani has 26
headwords heading two to four separate entries).

| Column | Meaning |
|---|---|
| `canonical_id` | the cluster this sense belongs to |
| `root_ar`, `canonical_gloss` | root and representative gloss of the cluster |
| `n_works`, `n_senses` | how many works and how many senses the cluster holds |
| `work`, `headword`, `sense_nr`, `gloss` | the individual sense, joinable back to `wujuh` |
| `confidence` | `strong` (2,585), `single` (2,131 — a cluster of one), `weak` (311) |
| `evidence` | why the sense was aligned, e.g. `gloss 1.00, shared verses 2` |

Two signals decide, and both must be earned: overlap in the cited verses
(counting only high/medium confidence citations, since `low` rows are candidate
lists) and gloss similarity. Verse overlap is never accepted without lexical
affinity, because two wujuh of one root regularly cite the same verse precisely
*because* the authors disagree about which wajh it belongs to. Complete linkage:
a cluster is only extended by a sense alignable with every sense already in it.

### Reference tables

| Table | Rows | Content |
|---|---|---|
| `surahs` | 114 | `number`, `name_ar`, `name_en`, `revelation_type` (`meccan`/`medinan`), `revelation_order`, `ayah_count`. The ayah counts are derived from the corpus itself and only *checked* against the standard reference list |
| `verses` | 6,236 | `surah`, `ayah`, `text_ar` (the joined verse text, with the corpus' leftover Buckwalter markers repaired), `text_normalized` (the form used for citation matching), `word_count`, `juz`, `hizb` |
| `juz_boundaries` | 30 | `juz`, `start_surah`, `start_ayah`, `end_surah`, `end_ayah`; the ends are derived from the next juz' start |
| `hizb_boundaries` | 60 | the same for the 60 ahzab, with the `juz` each belongs to |

### Views

| View | Content |
|---|---|
| `ayat` | one row per verse: `surah`, `ayah`, `verse_ar` (words joined with spaces), reconstructed on the fly from `corpus` |
| `words` | one row per written word: `surah`, `ayah`, `word`, `word_ar`, `word_bw` (segments concatenated in segment order) |

Prefer the `verses` table over the `ayat` view for reading text: `ayat` passes
the corpus' extended-Buckwalter markers (`@`, `,`, `.`, `[`) through unmapped,
so 2,240 of its rows contain characters that are not Arabic script, where
`verses.text_ar` has them repaired to the Quranic annotation signs they stand
for.

## Data quality

`validate.py` runs 19 checks over the finished database and is the last step of
`build.py`. On the committed database, 17 pass and 2 warn — the two warnings are
about the wujuh layer and are described below. It checks the corpus totals and
the two annotation layers, the referential integrity of `wujuh` against
`corpus`, *freshness* (the parsed JSONs, `resolved_citations.json` and the
`wujuh` table must all still agree with each other), *shape* (does a
`match_status` pile its rows onto one verse, or produce several verses per
citation), a per-status spot check of the citations, and the reference tables.

### What a citation match really guarantees

The classical authors quote from memory and in the orthography of their own
time, not from the mushaf rasm, and the digitizations add their own typos. The
spot check therefore verifies each quote in cumulative tiers and reports all of
them side by side, because any one of them alone misleads. For `unique` — the
largest and strictest status — on a sample of 750 rows:

| Tier | `unique` | `ambiguous` | `hint_resolved` | `cross_verse` |
|---|---|---|---|---|
| literal: the normalized quote occurs verbatim in the verse | 58.0% | 61.1% | 52.3% | 36.5% |
| with the author's framing word dropped | 71.5% | 76.3% | 70.6% | 41.7% |
| on the consonantal skeleton | 100% | 100% | 100% | 100% |

So `unique` does **not** mean "the quote occurs literally in exactly one verse".
It means the quote was located in exactly one verse *at the level the matcher
worked on*; literally it holds for about 58%, and on the consonantal skeleton
for all of them. The tolerant tiers overstate in the other direction: they say
the words are in that verse, not that it is the verse the author meant. This is
why the clustering and rows-per-citation checks sit next to the spot check
rather than under it.

The two weak statuses are visible here too: on the weakest tier (bare word
overlap) `prefix` verifies for 71.6% and `edition_jk` for 77.8%, both below the
90% warning threshold. Together they are 76 rows.

### Layers that were measured and rebuilt

An adversarial review measured each inference layer separately, and two of them
did not survive it:

- **`substantiate_jk`** (rescuing failed quotes from a second digitization) used
  to adopt any counterpart with 0.6 bag-of-words overlap and no verification.
  That produced 82 rows of which about 91% named a verse the quote does not
  occur in, 44% of them collapsing onto 17:69 alone because the editorial word
  *wa-fiha* happened to overlap. It now demands locating information, a
  skeleton-level resemblance, verification against the verse text itself, and
  uniqueness among surviving candidates. Result: 9 rows for 7 citations, each
  checked by hand.
- **`short_hint`** (very short quotes placed by a sura hint) was about 50%
  wrong at 162 rows. It is now 15 rows, all 15 literally verifiable.
- **`fuzzy`**, which had been assumed to be the weak one, measured 96% correct
  and was left as it is. It is capped at `medium` because a word-overlap match
  cannot prove which verse the author meant, not because it is unreliable.
- **`ambiguous`** rows are candidate lists, not attestations: 2,588 rows for 584
  citations, 4.43 verses per citation on average, with the widest list running
  to 152 verses (al-Damaghani's *k-f-r*, quoting الذين كفروا). A silent cap at
  ten candidates used to hide that width; it has been removed, so
  `candidate_count` now shows the real breadth. These rows carry `confidence =
  'low'`. Exclude them from any count of attestations — that is the standing
  warning `validate.py` prints.

### Reach versus correctness

Of 10,422 real quoted fragments across the four works, 10,123 (97%) resolved to
at least one verse: Yahya ibn Sallam 96.5%, al-Askari 96.2%, al-Damaghani
98.2%, Ibn al-Jawzi 96.8%. That figure measures reach, not correctness. The
correctness figure is the confidence distribution: 9,242 rows (75%) are `high`,
480 (4%) `medium`, 2,622 (21%) `low`.

## Pipeline

`build.py` runs these in order.

| Script | What it does |
|---|---|
| `convert.py` | Buckwalter → Arabic script, splits the corpus feature string into columns → `quranic-corpus-arabic.tsv` (not part of the build; run only when the conversion changes) |
| `to_sqlite.py` | loads the TSV into the `corpus` table, creates the `words` and `ayat` views and the indexes |
| `add_kalima_type.py` | adds `kalima_type` from the corpus tag, with per-lemma corrections where classical grammar disagrees with the corpus |
| `add_damair_lemmas.py` | fills lemmas for personal pronouns |
| `add_wazifa.py` | adds `wazifa`, mapping each corpus tag to its classical function name |
| `add_metadata.py` | builds `surahs`, `juz_boundaries`, `hizb_boundaries` and `verses` (optional step) |
| `parse_tasarif.py` | parses Yahya ibn Sallam's *at-Tasarif* → `sources/tasarif_wujuh.json` (114 entries, 551 senses, 1,871 quotes) |
| `parse_damaghani.py` | parses al-Damaghani's *Qamus al-Quran* → `sources/damaghani_wujuh.json` (497 entries, 2,329 senses, 3,736 quotes) |
| `parse_ibnjawzi.py` | parses Ibn al-Jawzi's *Nuzhat al-A'yun* → `sources/ibnjawzi_wujuh.json` (300 entries, 1,500 senses, 2,752 quotes) |
| `parse_askari.py` | parses Abu Hilal al-Askari's *al-Wujuh wa-l-Naza'ir* → `sources/askari_wujuh.json` (210 entries, 848 senses, 2,080 quotes; optional step) |
| `resolve_citations.py` | resolves every quoted fragment to sura:aya against the corpus text, in tiers (exact → sura hint → cross-verse → prefix → fuzzy) → `sources/resolved_citations.json` |
| `substantiate_jk.py` | retries the quotes that failed, using a second, independently typed digitization of Ibn al-Jawzi as a source of correctly typed counterparts (for every work, not only his), and updates `resolved_citations.json` in place |
| `add_wujuh.py` | drops and rebuilds the `wujuh` table: root inference, word-level linkage, and the three confidence columns |
| `align_senses.py` | builds `sense_alignment`: canonical sense ids across the works (optional step) |
| `validate.py` | 19 checks over the finished database (optional step) |
| `query.py` | command-line query tool with RTL output |
| `app.py` | optional Streamlit dashboard (needs `streamlit`, `pandas`) |

| `add_translation.py` | builds `word_glosses`: the corpus' word-by-word English glosses (optional step) |
| `parse_irab.py` | parses al-Nahhas' I'rab al-Quran into `irab` (optional step) |
| `analyses.py` | reproduces every finding in `BEVINDINGEN.md` (`--all`, or one by name) |

`SOURCES.md` records the provenance of every source: what it is, where it was
obtained, which edition, under what licence, which script loads it into which
table, and — separately — what this project derived rather than sourced. Read it
before citing any figure from this database.

`BEVINDINGEN.md` (Dutch) is the analytical companion to this file: what the
data turned out to say. Word counting under two definitions, what does and does
not carry a root, when one written form is two different words, frequency and
coverage, juz Amma as a starting point for learning, why the lexically richest
juz is not the most useful one, and the wujuh findings including the cases where
the four works disagree. Every figure in it is produced by a named analysis in
`analyses.py`, so it can be re-derived rather than trusted.

`OBSERVATIES.md` (Dutch) records findings from the data: counts, distributions,
what the kalima/lemma distinction changes about them, and what the four wujuh
works do and do not agree on.

## Sources

**Quranic Arabic Corpus, morphology version 0.4** — Copyright (C) 2011 Kais
Dukes, University of Leeds. GNU General Public License. Built on the verified
Arabic text of the Tanzil project. <https://corpus.quran.com>. The raw file
`quranic-corpus-morphology-0.4.txt` is included verbatim, including its copyright
block; its terms require that the source is credited and linked.

The four wujuh works are OpenITI mARkdown releases of Shamela and JK
digitizations. Edition details are taken from the `#META#` headers of the source
files.

| File | Work | Author | Edition |
|---|---|---|---|
| `sources/tasarif.txt` | *at-Tasarif li-tafsir al-Quran mimma ishtabahat asma'uhu wa-tasarrafat ma'anihi* | Yahya ibn Sallam al-Taymi al-Basri al-Qayrawani (d. 200 AH / 815 CE) | al-Sharika al-Tunisiyya li-l-Tawzi', 1979. Shamela_0011783 |
| `sources/askari_wujuh_src.txt` | *al-Wujuh wa-l-Naza'ir* | Abu Hilal al-Hasan ibn Abd Allah ibn Sahl al-Askari (d. ca. 395 AH / 1005 CE) | ed. Muhammad Uthman, Maktabat al-Thaqafa al-Diniyya, Cairo, 1st ed., 1428/2007. Shamela_0037586 |
| `sources/damaghani_qamus.txt` | *Qamus al-Quran*, i.e. *Islah al-wujuh wa-l-naza'ir fi l-Quran al-karim* | al-Husayn ibn Muhammad al-Damaghani (d. 478 AH / 1085 CE) | ed. Abd al-Aziz Sayyid al-Ahl, Dar al-Ilm li-l-Malayin, Beirut, 3rd ed., 1980. Shamela bkid 34085 |
| `sources/ibnjawzi_nuzhat.txt` | *Nuzhat al-A'yun al-Nawazir fi ilm al-wujuh wa-l-naza'ir* | Jamal al-Din Abu l-Faraj Ibn al-Jawzi (d. 597 AH / 1201 CE) | ed. Muhammad Abd al-Karim Kazim al-Radi, Mu'assasat al-Risala, Beirut, 1st ed., 1404/1984. Shamela_0006334 |
| `sources/ibnjawzi_nuzhat_jk.txt` | same work, second digitization, used only by `substantiate_jk.py` | | same edition, typed independently. JK_007134 |

The OpenITI files carry no license field in their `#META#` headers. OpenITI
generally releases its corpus under CC BY-NC-SA 4.0, but the underlying printed
editions are modern and their status is not settled by that; check before
redistributing. See <https://openiti.org>.

### Why these four, and not more

Two further wujuh works were looked for and are not available: al-Hiri
(d. 431 AH) and Muqatil ibn Sulayman's independent *Wujuh* work. Both were
searched for exhaustively across the whole of OpenITI — 36 century repositories,
13,364 text versions — and neither is there. Al-Askari was the last complete
wujuh text still to be had, so the layer is as wide as the available digitized
tradition allows.

Mining a *tafsir* instead was investigated as a way to widen sense coverage
beyond what the wujuh works themselves cite, using al-Tabari's *Jami al-bayan*.
It was measured and rejected: extracting sense assignments from running
commentary reached about 35% precision at a recall ceiling of about 35%. That is
far below the standard the rest of this layer is held to, so no tafsir is used.

## Known limitations

**The wujuh layer only labels the verses the authors themselves quote.** It is
evidence for a sense, not a full sense-annotation of the Quran. The 450 roots
covered occur 38,785 times in the corpus; only 6,530 of those occurrences (17%)
sit in a verse that a wujuh row points at, and only 5,155 (13%) in one a
`high`-confidence row points at. Every other occurrence of a polysemous word is
unlabelled — the database does not know which *wajh* applies there. At word
level the linkage is tighter but narrower still: 9,947 rows name a specific
word, covering 5,384 distinct corpus segments.

**Filter on `confidence` before counting anything.** 2,622 rows (21%) are `low`,
i.e. candidate lists in which at most one row per citation is the verse the
author meant. Counting them as attestations inflates the frequent, generic
phrases most: the single widest citation contributes 152 rows on its own.

**Roots in the `wujuh` table are inferred, not read.** The classical works index
by headword, not by root, so `add_wujuh.py` derives the root from the roots the
cited verses actually contain. This cannot work on entries for particles, and
misfires on headwords the digitization typo'd; 602 rows carry no root. Check the
`headword` before trusting a `root_ar` on a small entry.

**One verse can appear more than once for the same sense** when an author quotes
two different fragments of it, and joining `wujuh` to `corpus` on
(surah, ayah, root_ar) multiplies rows further when a verse contains several
segments of the root. Use `DISTINCT`, aggregate, or join on `corpus_id`.

**Not every parsed sense reaches the table.** The parsers produce 1,121 entries
and 5,228 senses; the `wujuh` table holds 1,083 entries and 4,935 senses. The
difference is entries and senses all of whose citations failed to resolve, or
that carry no citation at all. Sense numbers can therefore have gaps.

**The four works do not agree, and are not meant to.** They differ in how many
wujuh a word has, in the order of the senses, and in which verse illustrates
which sense: for خير Ibn al-Jawzi lists 19 senses, al-Askari 10, Ibn Sallam 8
and al-Damaghani 7. Of the 450 roots, 167 are covered by a single work, 129 by
two, 87 by three and 67 by all four. Treat `work` as a dimension, not as
replicate measurements — and use `sense_alignment` when the question is what the
works have in common.

**Parsing is imperfect on both layers.** Glosses are extracted with regular
expressions from continuous prose and are sometimes truncated or missing (224
rows have none); the al-Damaghani digitization degrades badly in its second half
and the parser leans on fallbacks there; al-Askari lists his wujuh in running
prose in about a dozen entries, where nothing is parsed rather than guessed.
`kalima_type` and `wazifa` are derived from the corpus' own tagging and inherit
its analytical choices, which are one defensible reading among several.
