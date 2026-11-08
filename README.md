# adviseurstools.nl

Statische versie van www.adviseurstools.nl (voorheen Google Sites). Geen build-step nodig.

## Structuur
- `index.html` – homepage
- `<categorie>/<pagina>/index.html` – alle pagina's, met dezelfde URL's als op de oude site
- `tools/*.html` – de rekentools zelf (standalone HTML), op de pagina's ingeladen via een iframe die zich automatisch aan de hoogte aanpast
- `assets/site.css`, `assets/site.js` – gedeelde opmaak, mobiel menu en iframe-hoogte
- `assets/img/` – afbeeldingen

## Tool aanpassen
Bewerk het bestand in `tools/`. De pagina eromheen hoeft niet te veranderen.

## Nieuwe pagina
Kopieer een bestaande `index.html` uit een map op dezelfde diepte en pas de titel en de iframe-`src` aan.

## Beveiligde pagina (Project Jeroen)
`project-jeroen/` is met een wachtwoord beveiligd: de tool staat alleen versleuteld (AES-256-GCM, PBKDF2) in de pagina en wordt in de browser ontsleuteld. Het wachtwoord staat nergens in de repo.
- Bewerken: `WACHTWOORD='…' node scripts/beveilig-pagina.js decrypt project-jeroen/index.html /tmp/pj.html`
- Na bewerken opnieuw versleutelen: `WACHTWOORD='…' node scripts/beveilig-pagina.js encrypt /tmp/pj.html project-jeroen/index.html`
- Commit nooit de leesbare versie.

## Zoeker
In de kop van elke pagina staat een zoekveld ("Wat zoek je, wat wil je berekenen?"), toegevoegd door `assets/site.js`. De zoekindex staat in `assets/zoekindex.js`.
- Na het toevoegen of hernoemen van pagina's: `python3 scripts/maak-zoekindex.py`
- Zonder resultaat biedt de zoeker een concept-mail aan (mailto) naar jeroen@oversteegen.nl met de zoekvraag erin.
- Sneltoets: `/` zet de cursor in het zoekveld.

## Tooloverzicht op categoriepagina's
De categoriepagina's (hypotheek, krediet, assurantie, vermogen-pensioen, overige, platformen) tonen tegels in plaats van lijsten, doorlopend genummerd, met filterveld. Op de homepage lopen de nummers ook door.
- Titels, omschrijvingen en thema's staan in `scripts/maak-overzicht.py` (CURATED, UITGELICHT, THEMAS).
- Na wijzigingen: `python3 scripts/maak-overzicht.py` en daarna `python3 scripts/maak-zoekindex.py`.

## Site-opmaak
Kop met kruimelpad, gerelateerde tools onder elke tool, sitefooter en de homepage worden gemaakt door `scripts/opmaak-site.py`. Volgorde na wijzigingen:
1. `python3 scripts/maak-overzicht.py` (tegels op categoriepagina's)
2. `python3 scripts/opmaak-site.py` (kop, footer, gerelateerde tools, homepage)
3. `python3 scripts/maak-zoekindex.py` (zoeker)
4. `python3 scripts/maak-seo.py` (meta-tags, canonical, Open Graph, JSON-LD, sitemap.xml, robots.txt, llms.txt)

## Normen aanpassen (één plek)
Alle leennormen, NHG-grenzen en fiscale waarden staan in `data/normen.json`.
1. Pas de waarde aan in `data/normen.json` (bijv. een nieuw normjaar toevoegen onder `leennormen.financieringslast`, `alleenstaandenbedrag` en `nhg`).
2. Draai `python3 scripts/maak-normen.py`. Dat controleert de data en werkt bij:
   - de open data: `api/normen.json`, `api/normen-<jaar>.json` (uitleg op `/api/`);
   - de rekenbibliotheek `assets/normen.js` (`window.ATNormen`, zie `scripts/normen-lib.js`);
   - elke tool met een blok `<script id="at-normen"></script>`: daarin wordt de bibliotheek met de actuele normen gezet, zodat de tool een losstaand bestand blijft.
3. Daarna de gebruikelijke stappen (opmaak, zoekindex, SEO) en committen.
