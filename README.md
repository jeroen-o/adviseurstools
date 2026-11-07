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
