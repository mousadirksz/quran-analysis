# Openstaand

Wat er nog ligt, en bij wie. Dit bestand staat in de repo omdat een sessie
verdwijnt en dit niet.

## Voor de eigenaar — kan hier niet gedaan worden

**`master` hernoemen naar `main`.** Er is geen tool voor repo-instellingen in
de omgeving waarin dit werk gebeurt, en de directe API-aanroep wordt door de
permissiecontrole geweigerd. GitHub's eigen knop doet het atomisch en verzet
alle openstaande pull requests mee: *Settings → Branches → het potloodje naast
`master`*. Daarna kunnen de verwijzingen in README en in eventuele workflows
mee.

**Twee klassieke iʿrāb-bronnen erbij.** Gewenst zijn al-ʿUkbarī's *al-Tibyān fī
iʿrāb al-Qurʾān* en Makkī al-Qaysī's *Mushkil iʿrāb al-Qurʾān*; `SOURCES.md`
noemt ze al als bekende kandidaten met hun OpenITI-identificatie. Een bestand
ophalen lukt hier als het pad bekend is, maar een pad *vinden* niet: de GitHub
API geeft 403 door de proxy voor repositories buiten de sessie, en er was geen
bereikbare index. Nodig is dus één van beide: de directe URL's, of de
OpenITI-repository toegevoegd aan de sessie.

## Beslissingen, geen fouten

Deze kwamen uit de audit van 8 september 2026 en zijn bewust niet uitgevoerd,
omdat ze de eigenaar toekomen.

- **`quran.db` blijft getrackt.** 64 MB per versie, twintig versies in de
  historie, samen ongeveer 263 MB objectopslag voor een project waarvan de
  broncode een paar honderd kilobyte is. Dat de database wordt meegecommit is
  gedocumenteerd en verdedigbaar — je kunt de repo klonen en meteen queryen —
  maar wat het kost staat nergens.
- **`quran_analysis.ipynb`** (515 KB, opgeslagen uitvoer, ongewijzigd sinds de
  eerste commit) en **`unrar-0.4-py3-none-any.whl`** (een derde-partij-wheel
  waar niets naar verwijst) staan in de repo. README noemt ze nu bij naam en
  zegt dat geen van beide nodig is om te bouwen of te queryen; of ze weg
  moeten is een keuze.

## Wat de audit nooit heeft bekeken

De audit van 8 september strandde op een sessielimiet met 15 van de 560 agents
klaar. Drie dimensies zijn nooit begonnen, en juist daar is deze repo
aantoonbaar zwak — de tekenvolgorde van handgetypt Arabisch is er in de
geschiedenis van dit project al meermaals naast gegaan:

1. **Unicode en Arabisch** — de tekenvolgorde van elk Arabisch citaat in de
   documenten tegen de mushaf-bestanden en het corpus.
2. **Schemadocumentatie** — de kolommen die README beschrijft tegen wat de
   database werkelijk heeft.
3. **Klassieke claims** — qurrāʾ, sterfjaren, uṣūl-toeschrijvingen, en de
   beschrijvingen in `SOURCES.md`.

Het volledige rapport met de bewijsvoering per bevinding, en welke van de 202
zijn nagetrokken en gerepareerd, staat op
<https://claude.ai/code/artifact/0509e509-18d8-4b71-a9e5-777598338802>.
