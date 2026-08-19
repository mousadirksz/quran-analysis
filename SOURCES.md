# Sources and provenance

Every row in `quran.db` derives from one of the sources below. This file records,
for each of them, what it is, where it was obtained, which edition it represents,
under what terms it may be used, and which script turns it into which table — so
that any figure this project reports can be traced back to a text someone else
can obtain and check.

Nothing in the database is authored here. Where this project has made a judgment
of its own — a classification, an inferred root, a matched citation — that is
stated as such in the "Derived, not sourced" section at the end.

---

## 1. Quranic Arabic Corpus — morphology

The text layer and its grammatical annotation.

| | |
|---|---|
| **Work** | Quranic Arabic Corpus, morphological annotation |
| **Version** | 0.4 |
| **Author** | Kais Dukes |
| **Obtained from** | https://corpus.quran.com/download/ |
| **Files in this repo** | `quranic-corpus-morphology-0.4.txt` (as downloaded), `quranic-corpus-arabic.tsv` (same data, converted to TSV by `convert.py`) |
| **Licence** | GNU General Public License |
| **Loaded by** | `to_sqlite.py` → table `corpus`, views `words`, `ayat` |

Supplies: `surah`, `ayah`, `word`, `segment`, the Arabic and Buckwalter forms,
the POS tag, `lemma`, `root` and the morphological features (aspect, voice,
person, gender, number, case, mood, state). 128,219 segment rows.

The Uthmani text of the Quran itself reaches the database only through this
file, as the `form_ar` of each segment; `verses.text_ar` is those forms joined
back together by `add_metadata.py` and is therefore a reconstruction, not an
independently sourced mushaf text.

## 2. Quranic Arabic Corpus — word-by-word English glosses

| | |
|---|---|
| **Work** | Quranic Arabic Corpus, word-by-word English |
| **Author** | Kais Dukes |
| **Obtained from** | https://github.com/Abbas1997/QuranicMorphology, file `Components/wordtranslations.js`, which redistributes the corpus data with its keys unchanged |
| **File in this repo** | `sources/word_glosses_en.tsv` (normalised to TSV; keys and gloss text unaltered) |
| **Licence** | GNU General Public License, as the corpus |
| **Loaded by** | `add_translation.py` → table `word_glosses`, view `words_en` |

77,429 glosses for 77,429 written words. They align exactly because they come
from the same project as the morphology; `add_translation.py` refuses to write
the table if either side has an unmatched row.

**These are glosses, not a translation.** They are deliberately literal and
often bracketed ("(of) Allah", "All praises and thanks"), written to show what
each Arabic word contributes to the sentence. They read poorly as a translation
of the Quran and should not be presented as one. No translation of the Quran is
included in this database.

## 3. Wujuh wa-naza'ir — four classical works

The polysemy layer: which meanings the classical scholars assign to a word, and
at which verses. All four were obtained from the [OpenITI](https://openiti.org)
corpus, which republishes digitizations made by al-Maktaba al-Shamela.

Each entry below gives the OpenITI text identifier. The full path is
`data/<author>/<author>.<work>/<identifier>` inside the century repository named
in the table, e.g.
`https://github.com/OpenITI/0500ah` →
`data/0478IbnMuhammadDamghani/0478IbnMuhammadDamghani.QamusQuran/0478IbnMuhammadDamghani.QamusQuran.ShamAY0034085-ara1`.

| Author | Died | Work | OpenITI repo | Text identifier | File here |
|---|---|---|---|---|---|
| Yahya ibn Sallam al-Taymi | 200 AH | al-Tasarif li-tafsir al-Quran mimma ishtabahat asma'uhu wa-tasarrafat ma'anih | `0200AH` | `Shamela0011783-ara1` | `sources/tasarif.txt` |
| Abu Hilal al-Askari | ≈395 AH | al-Wujuh wa-l-naza'ir | `0400AH` | `Shamela0037586-ara1` | `sources/askari_wujuh_src.txt` |
| al-Husayn ibn Muhammad al-Damaghani | 478 AH | Qamus al-Quran, aw Islah al-wujuh wa-l-naza'ir fi l-Quran al-karim | `0500AH` | `ShamAY0034085-ara1` | `sources/damaghani_qamus.txt` |
| Ibn al-Jawzi | 597 AH | Nuzhat al-a'yun al-nawazir fi 'ilm al-wujuh wa-l-naza'ir | `0600AH` | `Shamela0006334-ara1` | `sources/ibnjawzi_nuzhat.txt` |
| Ibn al-Jawzi (second digitization) | 597 AH | as above, independently typed from a different printed edition | `0600AH` | `JK007134-ara1` | `sources/ibnjawzi_nuzhat_jk.txt` |

Printed editions, where the digitization records them: al-Damaghani is the third
edition, ed. Abd al-Aziz Sayyid al-Ahl, Dar al-Ilm li-l-Malayin, Beirut 1980.
The other files carry OpenITI metadata headers but no edition fields; the
Shamela library identifiers above are what identifies them.

**Parsed by** `parse_tasarif.py`, `parse_askari.py`, `parse_damaghani.py`,
`parse_ibnjawzi.py` → `sources/*_wujuh.json`, then `resolve_citations.py` and
`substantiate_jk.py` → `sources/resolved_citations.json`, then `add_wujuh.py` →
table `wujuh` and `align_senses.py` → table `sense_alignment`.

The second Ibn al-Jawzi digitization is used only by `substantiate_jk.py`: where
one edition's citation is corrupt the other is usually intact, and its verse
reference can be adopted (recorded as `match_status = 'edition_jk'`).

**Why these four and no more.** All 36 OpenITI century repositories (13,364 text
versions) were searched by title and by author for further Quranic wujuh works.
These four are what exists there. Al-Hiri / al-Nisaburi (d. 431 AH), Muqatil ibn
Sulayman's standalone *al-Wujuh wa-l-naza'ir* (d. 150 AH) and Ibn al-Jawzi's
abridgement *Muntakhab Qurrat uyun al-nawazir* are not in OpenITI in any form;
they exist elsewhere only as PDF scans or on sites this project has not drawn
from.

## 4. Icrab — al-Nahhas

The syntactic layer: which word is subject and which predicate, why a word
carries the ending it does, and where the grammarians disagreed.

| | |
|---|---|
| **Author** | Abu Ja'far al-Nahhas, Ahmad ibn Muhammad ibn Isma'il |
| **Died** | 338 AH |
| **Work** | I'rab al-Quran |
| **Obtained from** | OpenITI repo `0350AH`, text `Shamela0023587-ara1` |
| **File in this repo** | `sources/nahhas_irab.txt` |
| **Loaded by** | `parse_irab.py` → table `irab` |

The earliest complete work of the genre still extant. 5,114 passages covering
5,108 of the 6,236 verses; al-Nahhas comments where a verse raises a syntactic
question, not on every verse. Each passage is stored whole against its verse:
the reference comes from the header of the passage itself, so no matching was
needed.

Two further i'rab works were located in OpenITI but are not loaded, because
their digitizations do not carry per-verse references: Makki ibn Abi Talib
al-Qaysi (d. 437 AH), *Mushkil i'rab al-Quran* (`0450AH`, `Shamela0005538-ara1`),
whose headers name only the sura; and al-Muntajib al-Hamadhani (d. 643 AH),
*al-Farid fi i'rab al-Quran* (`0650AH`, `Sham19Y0147312-ara1`), which is
organised thematically. Both are parseable with more work.

## 5. Extended Quranic Treebank — syntax

The syntactic layer at token level: which word is the faacil of which verb,
which the mafcul, which the khabar — the analysis the classical icrab works
argue out in prose, as a structure that can be queried.

| | |
|---|---|
| **Work** | Extended Quranic Treebank (EQTB) |
| **Published** | 5 August 2025, DOI [10.1016/j.dib.2025.111940](https://doi.org/10.1016/j.dib.2025.111940) |
| **Obtained from** | https://github.com/NoorBayan/Quranic, file `corpus/Quranic.rar` (also on [Mendeley Data](https://data.mendeley.com/datasets/rk96pn66m4/1)) |
| **File in this repo** | `sources/treebank_eqtb.tsv.gz` |
| **Licence** | MIT |
| **Loaded by** | `parse_treebank.py` → table `syntax` |

The published file holds 51 columns; 14 are kept here — the token identity
needed to join, the relation labels, the head reference and the constituent
label. The morphological columns are deliberately **not** loaded: lemma, root,
POS and features come from the same Quranic Arabic Corpus lineage as section 1,
and loading them again would put two morphology layers in one database. What is
taken is what this database lacks. Values are unaltered; the file was converted
from UTF-16 to UTF-8 and gzipped.

Every one of the 128,219 tokens that corresponds to written text joins a corpus
segment, with nothing unmatched on either side — the treebank uses the corpus'
own (surah:ayah:word:segment) addressing. Beside those it posits 11,157
elements that the grammarians read into the text but which are not written,
6,674 of them the damir mustatir: the implied "you" that is the faacil of *qul*
in 112:1, and so on. Those carry `is_implicit = 1` and no location, since
counting kalimat with and without them gives two different and defensible
totals.

## 6. Reference data with no external source

`add_metadata.py` builds `surahs`, `juz_boundaries`, `hizb_boundaries` and
`verses`. The ayah counts and the verse text are derived from `corpus`. The sura
names, revelation type and revelation order, and the juz and hizb boundaries,
are the standard Hafs values, carried in the script as constants; the ayah
counts derived from the corpus are checked against an independent Hafs reference
list in the same script, and agree exactly.

---

## Licences

The Quranic Arabic Corpus is GPL-licensed, which covers both the morphology and
the word glosses. The OpenITI corpus is openly licensed for scholarly use and
its texts are digitizations of printed editions of works long in the public
domain. This repository redistributes the source texts unmodified under
`sources/`, except where a file is noted above as normalised, in which case the
normalisation is described and the keys and content are unaltered.

## Derived, not sourced

The following exist in the database because this project computed them, not
because a source states them. Each is reproducible from the scripts named.

| What | How | Where |
|---|---|---|
| `corpus.kalima_type` | the corpus POS tag mapped to the classical ism / fi'l / harf classes, with interrogative and conditional words reclassified as asma' per (lemma, tag) | `add_kalima_type.py` |
| `corpus.wazifa` | the classical function name for each POS tag (36 mappings) | `add_wazifa.py` |
| pronoun `lemma` values | the corpus leaves the dama'ir unlemmatised; each is assigned the canonical detached pronoun of its person-gender-number cell | `add_damair_lemmas.py` |
| `wujuh.surah` / `ayah` | the works cite a fragment and often a sura name; the verse is found by matching the fragment against the corpus text through several tiers, each recorded in `match_status` | `resolve_citations.py` |
| `wujuh.root_ar` | inferred from the verses an entry cites: the root occurring in most of them whose letters match the headword, stored only when that test is passed | `add_wujuh.py` |
| `wujuh.word` / `corpus_id` | the token within the cited verse that carries the entry's root and falls inside the quoted span | `add_wujuh.py` |
| `wujuh.confidence` | derived from `match_status` and the number of candidate verses for that citation | `add_wujuh.py` |
| `sense_alignment.canonical_id` | senses of one root clustered across works on gloss similarity and shared cited verses | `align_senses.py` |

Two consequences worth stating plainly. First, a `wujuh` row asserts that a
named scholar assigned a meaning and cited a verse; that a given verse is the
one cited is this project's matching, not the scholar's statement, which is why
every row carries its evidence tier. Second, the wujuh layer covers the verses
the authors themselves cite — about 17% of the occurrences of the roots
concerned — and says nothing about the rest.
