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

## Wat de audit nooit heeft bekeken — inmiddels alsnog gedaan

De audit van 8 september strandde op een sessielimiet met 15 van de 560 agents
klaar. Drie dimensies zijn toen nooit begonnen. Ze zijn daarna alle drie met de
hand gedaan, en de eerste twee hebben er een controle aan overgehouden die
voorkomt dat het opnieuw wegdrijft:

1. **Unicode en Arabisch** — afgedekt door de controle `Arabic quotations`:
   426 citaten, codepoint voor codepoint tegen de acht mushaf-bestanden,
   vergeleken op NFC. Vond drie fouten, waarvan twee ouder dan de audit.
2. **Schemadocumentatie** — afgedekt door `schema documentation`: 15 tabellen
   en views, 144 kolommen, alle in README genoemd. `syntax` miste er tien.
3. **Klassieke claims** — met de hand nagelopen; laat zich niet
   automatiseren. Alle sterfjaren van de acht riwaayaat, hun vier qurraa- en
   de negen klassieke werken in `SOURCES.md` bleken de standaardwaarden. Vier
   dingen klopten niet: Mauritanië leest Warsh en niet Qālūn; al-Naḥḥās was
   niet de eerste van zijn genre (al-Zajjāj, bij wie hij studeerde, ging hem
   voor); "5.114 passages" zijn 4.535 passages in 5.114 rijen; en dat de
   literatuur Ḥafṣ–Shuʿba en Qālūn–Warsh "aanwijst" als de verst uiteenlopende
   paren was sterker gezegd dan te verantwoorden viel.

Wat hier niet mee gedekt is: de uṣūl-toeschrijvingen rusten op de meting in
deze repo (al-Dūrī als controle voor de idghām kabīr van al-Sūsī splitst 1.152
tegen 5, silat al-mīm bij al-Bazzī en Qunbul, iskān van de hāʾ bij Qālūn,
al-Dūrī en al-Sūsī). Die metingen komen overeen met wat de handboeken geven,
maar de repo citeert geen handboek — dat blijft werk voor wie het wil naslaan.

Het volledige rapport met de bewijsvoering per bevinding, en welke van de 202
zijn nagetrokken en gerepareerd, staat op
<https://claude.ai/code/artifact/0509e509-18d8-4b71-a9e5-777598338802>.
