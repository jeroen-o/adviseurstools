#!/usr/bin/env python3
"""Zet de linklijsten op categoriepagina's om naar een tegeloverzicht (doorlopend genummerd)
en nummert de lijsten op de homepage door. Idempotent: draai opnieuw na wijzigingen.

Gebruik: python3 scripts/maak-overzicht.py
"""
import html, os, re, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGINAS = ['hypotheek', 'krediet', 'assurantie', 'vermogen-pensioen', 'overige', 'platformen']

# Thema's voor de hypotheekpagina: (naam, trefwoorden in titel/omschrijving). Eerste match wint.
THEMAS = [
    ('Maximale hypotheek & toetsing', ['max', 'maximale', 'toets', 'nhg', 'calculator 2026', 'hypotheekcalculator', 'hypotheek 2', 'alles in één', 'alles-in-één', 'werkelijke last', '40-jarige', '40 jarige', 'toetsinkomen', 'besteedbaar']),
    ('Pensioen & AOW', ['pensioen', 'aow', 'rvp', 'aflosvrij', 'klif']),
    ('Scheiding & draagplicht', ['scheiding', 'oha', 'hoofdelijke', 'draagplicht', 'rentecompensatie']),
    ('Aankoop, starters & overbrugging', ['kosten koper', 'overdrachtsbelasting', 'starter', 'overbrugg', 'koopovereenkomst', 'koopakte', 'bouwdepot', 'familie']),
    ('Maandlasten, aflossen & rente', ['maandlast', 'lasten', 'aflos', 'rente', 'oversluit', 'boeterente', 'bespaar', 'looptijd', 'vergelijk']),
    ('Fiscaal & vermogen', ['box', 'fiscale', 'schenk', 'eigen woning', 'ewr', 'verhuur']),
    ('Verzekeren & risico', ['orv', 'aov', 'life events', 'risico']),
]

# Handmatige titels, omschrijvingen en thema's (sleutel = laatste deel van de link). Thema alleen voor hypotheek.
M, P, S, A, R, F, V = ('Maximale hypotheek & toetsing', 'Pensioen & AOW', 'Scheiding & draagplicht',
                       'Aankoop, starters & overbrugging', 'Maandlasten, aflossen & rente', 'Fiscaal & vermogen', 'Verzekeren & risico')
CURATED = {
    'hypotheek-calculator': ('Hypotheekcalculator', 'Snel de maximale hypotheek op basis van inkomen en rente', M),
    'max-mortgages': ('Max. mortgage (English)', 'Maximum mortgage for expats — Dutch lending norms 2026', M),
    'kosten-koper-calculator': ('Kosten koper', 'Overdrachtsbelasting, notaris, taxatie, advies en NHG: totaal eigen geld', A),
    'nhg-toets-2026': ('NHG-toets 2026', 'Kostengrens, financieringslast en voorwaarden voor NHG', M),
    'hypotheek-betaalbaar-met-pensioen': ('Hypotheek betaalbaar na pensioen', 'Toets op pensioeninkomen met de AOW-tabel', P),
    'energiekosten-verduurzamen': ('Energiekosten & verduurzamen', 'Energielasten, maatregelen, terugverdientijd en extra leenruimte', R),
    'krediet-calculator': ('Krediet en maximale hypotheek', 'Effect van een lening of creditcard op je leenruimte', M),
    'maximale-hypotheek-berekening': ('Maximale hypotheekberekening', 'Financieringslastnormen 2026 met pensioentoets 57/52', M),
    'ontslag-hoofdelijke-aansprakelijkheid-oha-toets': ('OHA-toets', 'Ontslag hoofdelijke aansprakelijkheid met NHG-beheercriteria', S),
    'de-alles-in-één-tool': ('Alles-in-één', 'Maximale hypotheek, maandlasten, scenario\'s en adviesrapport', M),
    'toetsrente-verbeteraar': ('Toetsrente verbeteraar', 'Optimale verdeling over leningdelen voor een lagere toetsrente', M),
    'maximale-hypotheek-calculator-2026': ('Maximale hypotheek 2026', 'Box 1 en box 3, verplichtingen, energielabel en pensioentoets', M),
    'overbruggingscalculator': ('Overbruggingscalculator', 'Overbruggingskrediet, dubbele lasten en risico verkoopprijs', A),
    'eigenwoningregeling-ewr': ('Eigenwoningregeling (EWR)', 'Eigenwoningreserve en -schuld, bijleenregeling en overgangsrecht', F),
    'hypotheek-werkelijke-last-toets': ('Werkelijke-lasttoets', 'Contractuele maandlast getoetst aan GHF en NHG-beheer', M),
    '40-jarige-hypotheek': ('40-jarige hypotheek', 'Maandlasten 40 jaar looptijd vergeleken met 30 jaar', R),
    'max-hyp-2027': ('Max. hyp. 2027', 'Maximale hypotheek en maandlasttoets volgens de normen 2026 en 2027', M),
    'max-hyp-box-1-3': ('Max. hyp. box 1 & 3', 'Toetsmomenten over de looptijd met box 1- en box 3-delen', M),
    'pensioenklif': ('Pensioenklif', 'Hypotheek in leningdelen getoetst op inkomen nu en na pensioen', P),
    '10-jaar-voor-aow-planner': ('10 jaar voor AOW-planner', 'Maximale hypotheek per maand tot en na de AOW-datum', P),
    'aflosvrij-loop-je-risico': ('Aflossingsvrij: loop je risico?', 'Check in twee stappen of je aflossingsvrije hypotheek houdbaar is', P),
    'hypotheek-hulpbrief-aflossingsvrij': ('Hulpbrief aflossingsvrij', 'Brief met feitenvragen aan de geldverstrekker', P),
    'na-einde-rvp-hypotheek-nog-betaalbaar': ('Na einde rentevaste periode betaalbaar?', 'Stresstest met rentescenario\'s na de rentevaste periode', R),
    'einde-rvp-betaalbaar': ('Einde rentevaste periode betaalbaar', 'Toets van de nieuwe maandlast op inkomen en pensioen', R),
    'vergelijk-annuitaire-lineaire-aflosvrije-hypotheek': ('Annuïtair, lineair of aflossingsvrij', 'Maandlasten en totale kosten van de drie aflosvormen', R),
    'draagplichtovereenkomst-assistent': ('Draagplichtovereenkomst', 'Risicoscan en modeldocumenten voor partners', S),
    'rentecompensatie-echtscheiding-berekenen': ('Rentecompensatie bij scheiding', 'Indicatieve compensatie voor de partner die vertrekt', S),
    'hypotheek-na-scheiding': ('Hypotheek na scheiding', 'Uitkoop partner en draagkracht volgens leennormen of NHG-beheer', S),
    'familie-hypotheek-calculator': ('Familiehypotheek', 'Bank- en familielening, renteaftrek en terugschenking', A),
    'bouwdepot-calculator': ('Bouwdepot', 'Bouwdepot, rentevergoeding en dubbele lasten tijdens de bouw', A),
    'hypotheek-uit-koopovereenkomst': ('Hypotheek uit koopovereenkomst', 'Financieringsopzet op basis van de koopovereenkomst', A),
    'koopakte-uitlezen': ('Koopakte uitlezen', 'Gegevens uit een koopovereenkomst (PDF) automatisch uitlezen', A),
    'netto-gelijkblijvende-lasten': ('Netto gelijkblijvende lasten', 'Leningdelen zo kiezen dat de netto last gelijk blijft', R),
    'boeterente-calculator': ('Boeterente', 'Vergoeding bij vervroegd aflossen volgens de AFM-leidraad', R),
    'hypotheekoversluit-calculator': ('Oversluiten', 'Is oversluiten financieel verstandig? In drie stappen', R),
    'netto-maandlasten': ('Netto maandlasten', 'Bruto-netto met renteaftrek, eigenwoningforfait en erfpacht', R),
    'kosten-hypotheek-over-de-looptijd': ('Kosten over de looptijd', 'Totale rente en netto kosten per aflosvorm', R),
    'rentemiddeling': ('Rentemiddeling', 'Is rentemiddeling voordelig en wat is de opslag?', R),
    'hypotheekrente-overzicht': ('Hypotheekrente-overzicht', 'Rentetabel om zelf bij te houden en te vergelijken', R),
    'hypotheek-bespaarcheck': ('Bespaarcheck', 'Huidige rente versus markt: oversluiten of middelen', R),
    'extra-aflossen-calculator': ('Extra aflossen', 'Effect van extra aflossen op maandlast en looptijd', R),
    'boeterenteberekening-afm': ('Boeterente (AFM-leidraad)', 'Contante-waardemethode volgens de AFM-leidraad', R),
    'rentemix-optimizer': ('Rentemix optimizer', 'Verdeling over leningdelen voor een gewenste gewogen rente', R),
    'box-3-calculator': ('Box 3', 'Heffing 2026 met forfaitaire rendementen en heffingsvrij vermogen', F),
    'schenkinsvrijstelling': ('Schenkingsvrijstelling', 'Vrijstellingen en schenkbelasting 2026', F),
    'box-3-verhuurrendement-calculator': ('Verhuurrendement box 3', 'Rendement van een verhuurde woning na box 3', F),
    'orv-passend-advies': ('ORV passend advies', 'Benodigde overlijdensdekking inclusief Anw', V),
    'aov-calculator': ('AOV', 'Inkomensgat bij arbeidsongeschiktheid en benodigde dekking', V),
    'orv-calculator': ('ORV', 'Premie-indicatie overlijdensrisicoverzekering', V),
    'bank-analyse-nibud': ('Uitgaven uit bankafschrift', 'Nibud-formulier invullen op basis van banktransacties', V),
    'brondata-verrijker': ('Brondata verrijker', 'Aangifte (PDF) lokaal uitlezen voor het dossier', F),
    'besteedbaar-inkomen-afm': ('Besteedbaar inkomen (AFM-leidraad)', 'Wat blijft er over na woonlasten, energie en onderhoud?', None),
    'toetsinkomen-bepaler': ('Toetsinkomen bepalen', 'Per inkomensbron: wat telt mee en hoe lang', None),
    'risicoscan-life-events': ('Risicoscan life events', 'Tekort bij arbeidsongeschiktheid, werkloosheid, overlijden, scheiding en AOW', None),
    'fiscale-splitsing-box1-box3': ('Fiscale splitsing box 1 / box 3', 'Eigenwoningschuld, eigenwoningreserve en overgangsrecht', None),
    'overdrachtsbelasting-meerdere-kopers': ('Overdrachtsbelasting meerdere kopers', 'Per koper over het eigen aandeel, met startersvrijstelling', None),
    'overbrugging-dubbele-lasten': ('Overbrugging en dubbele lasten', 'Netto dubbele lasten met de 3-jaarsregel voor renteaftrek', None),
    'starterslening-check': ('Starterslening check', 'Tekort, 20%-grens, gemeentelijk maximum en NHG', None),
    'hypothekenplatform.nl': ('Hypotheekwoordenboek', 'Begrippen uitgelegd (externe site)', 'Overige hypotheektools'),
    'www.ai-battle.nl': ('AI-battle', 'Externe site', 'Overige hypotheektools'),
    # overige categorieën
    'krediet': ('VFN-normcalculator', 'Maximaal verantwoord krediet volgens de VFN-methodiek', None),
    'krediet-2': ('Krediet adviseur suite', 'Aflossingstabel, doorlopend en zakelijk krediet', None),
    'lening-vergelijken-en-aanvragen': ('Lening vergelijken', 'Huidige en nieuwe lening vergelijken en aanvraag opstellen', None),
    'toetsinkomen-calculator-kredieten': ('Toetsinkomen kredieten', 'Toetsinkomen en normbedragen voor consumptief krediet', None),
    'opstalverzekering': ('Opstalverzekering', 'Herbouwwaarde en premie-indicatie, onderverzekering voorkomen', None),
    'verzekeringscheck': ('Verzekeringscheck', 'Welke verzekeringen passen bij jouw situatie?', None),
    'polischeck': ('Polischeck', 'Polissen uploaden en dekkingshiaten vinden', None),
    'impact-eigen-risico': ('Impact eigen risico', 'Premievoordeel versus risico van een hoger eigen risico', None),
    'schade-risicoprofiel': ('Schade-risicoprofiel', 'Risicoprofiel voor schadeverzekeringen', None),
    'schade-inschatting-chatbot': ('Schade-inschatting', 'Is mijn schade gedekt en moet ik die melden?', None),
    'pensoencijfer': ('Pensioencijfer', 'Hoe staat je pensioen ervoor? Score en dekkingsgraad', None),
    'vermogen-pensioen': ('AOW & pensioen calculator', 'Externe site', None),
    'vp-2': ('Box 3 optimizer', 'Externe site', None),
    'vp3': ('Vrij besteedbaar', 'Externe site', None),
    'vermogensberekeningen': ('Vermogensberekeningen', 'Box 3, opnamen en vermogensverloop', None),
    'levensstandaard': ('Levensstandaard planner', 'Inkomen, uitgaven, buffer en pensioengat', None),
    'pep-sanctielijst': ('PEP- en sanctielijstcheck', 'Controle op politiek prominente personen en sancties', None),
    'nazorg-formulieren': ('Nazorgformulieren', 'Scans voor hypotheek, verzekeringen en leningen', None),
    'nazorg': ('Nazorg', 'Periodieke klantcheck', None),
    'financiële-tijdscapsule': ('Financiële tijdscapsule', 'Prijzen en lonen vroeger en nu', None),
    'klimaatcijfer-nl': ('Klimaatcijfer', 'Klimaatrisico\'s van een adres', None),
    'woningcijfer-nl': ('Woningcijfer', 'Bouwkundige en omgevingsscore van een woning', None),
    'woz-bezwaar': ('WOZ-bezwaar', 'Bezwaar tegen de WOZ-waarde voorbereiden', None),
    'ww-tool-impact-hypotheek': ('WW en hypotheek', 'WW-uitkering en het effect op je woonlasten', None),
    'echtscheidingstools': ('Echtscheidingstools', 'Alimentatie, pensioenverevening, boedel en woning', None),
    'fatuurtool-verhuur': ('Factuurtool verhuur', 'Facturen en inzicht voor verhuur', None),
    'www.pseudomaker.nl': ('Pseudonimiseren', 'Externe site', None),
    'pandwise.nl': ('PandWise', 'Woningdossier en woningwaarderapport per adres (externe site)', None),
    'diverse-tools': ('Diverse tools', 'WW, transitievergoeding, toeslagen en zzp', None),
}


EXTRA = {'overige': [('https://pandwise.nl/', 'PandWise')]}
UITGELICHT = ['max-hyp-2027', 'pensioenklif', 'max-hyp-box-1-3']


def sleutel(href):
    return [x for x in href.rstrip('/').split('/') if x][-1]


def schoon(t):
    t = re.sub(r'<[^>]+>', ' ', t)
    t = html.unescape(t).replace('->', ' ').replace('→', ' ')
    return re.sub(r'\s+', ' ', t).strip(' -–')


def omschrijving(pagina_dir, href):
    """Korte omschrijving uit de tool achter een interne link."""
    if href.startswith(('http', 'mailto')):
        return ''
    doel = os.path.normpath(os.path.join(ROOT, pagina_dir, urllib.parse.unquote(href), 'index.html'))
    if not os.path.exists(doel):
        return ''
    s = open(doel, encoding='utf-8').read()
    if 'id="versleuteld"' in s:
        return 'Beveiligd met wachtwoord'
    m = re.search(r'src="(?:\.\./)*tools/([^"]+)"', s)
    if not m:
        return ''
    tf = os.path.join(ROOT, 'tools', urllib.parse.unquote(html.unescape(m.group(1))))
    if not os.path.exists(tf):
        return ''
    t = open(tf, encoding='utf-8', errors='ignore').read()
    t = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', t, flags=re.S | re.I)
    for pat in (r'class="[^"]*hdr-sub[^"]*"[^>]*>(.*?)</', r'<header[^>]*>.*?<p[^>]*>(.*?)</p>', r'<h1[^>]*>.*?</h1>\s*<(?:p|div)[^>]*>(.*?)</(?:p|div)>'):
        m = re.search(pat, t, re.S | re.I)
        if m:
            d = schoon(m.group(1))
            if 12 < len(d):
                return (d[:110].rsplit(' ', 1)[0] + '…') if len(d) > 115 else d
    return ''


def thema(titel, oms):
    x = (titel + ' ' + oms).lower()
    for naam, woorden in THEMAS:
        if any(w in x for w in woorden):
            return naam
    return 'Overige hypotheektools'


def tegel(nr, href, titel, oms):
    extern = href.startswith('http')
    doel = ' target="_blank" rel="noopener"' if extern else ''
    sub = 'Externe site ↗' if extern and not oms else html.escape(oms)
    return (f'<a class="tcard" href="{html.escape(href)}"{doel} data-zoek="{html.escape((titel + " " + oms).lower())}">'
            f'<span class="tnr">{nr}</span><span class="ttx"><span class="ttl">{html.escape(titel)}</span>'
            + (f'<span class="tsub">{sub}</span>' if sub else '') + '</span></a>')


def verwerk(pagina):
    f = os.path.join(ROOT, pagina, 'index.html')
    s = open(f, encoding='utf-8').read()
    a, b = s.index('<main'), s.index('</main>')
    main = s[a:b]
    if 'id="tooloverzicht"' in main:   # opnieuw opbouwen uit de bewaarde lijst
        links = [(html.unescape(h), html.unescape(t)) for h, t in
                 re.findall(r'<a class="tcard" href="([^"]+)"[^>]*>.*?<span class="ttl">(.*?)</span>', main, re.S)]
        nieuw_set = set(html.unescape(h) for h in re.findall(r'data-groep="Nieuw".*?(?=data-groep=|$)', main, re.S)
                        for h in re.findall(r'href="([^"]+)"', h))
        main = re.sub(r'<section class="blk" id="tooloverzicht">.*?</section>\n?', '<!--OVERZICHT-->', main, flags=re.S)
    else:
        links, nieuw_set, eerste = [], set(), None
        for sec in re.findall(r'<section[^>]*>.*?</section>', main, re.S):
            if 'iframe' in sec:
                continue
            ls = [(html.unescape(h), schoon(t)) for h, t in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', sec, re.S)]
            ls = [(h, t) for h, t in ls if t and not re.fullmatch(r'Versie \d+', t)]
            if len(ls) < 2:
                continue
            if 'id="nieuw-2026"' in sec:
                nieuw_set |= {h for h, _ in ls}
            links += ls
            main = main.replace(sec, '<!--OVERZICHT-->' if eerste is None else '', 1)
            eerste = True
        if not links:
            print('geen lijsten:', pagina); return
    links = links + EXTRA.get(pagina, [])
    # dubbele links weg (eerste voorkomen telt)
    gezien, uniek = set(), []
    for h, t in links:
        if h not in gezien:
            gezien.add(h); uniek.append((h, t))
    items, themas = [], {}
    for h, t in uniek:
        c = CURATED.get(sleutel(h))
        if c:
            t, o = c[0], c[1]
            themas[h] = c[2]
        else:
            o = omschrijving(pagina, h)
        items.append((h, t, o))
    groepen = {}
    for h, t, o in items:
        g = 'Uitgelicht' if sleutel(h) in UITGELICHT else 'Nieuw' if h in nieuw_set else ((themas.get(h) or thema(t, o)) if pagina == 'hypotheek' else 'Tools')
        groepen.setdefault(g, []).append((h, t, o))
    volgorde = ['Uitgelicht', 'Nieuw'] + [n for n, _ in THEMAS] + ['Overige hypotheektools', 'Tools']
    if 'Uitgelicht' in groepen:
        groepen['Uitgelicht'].sort(key=lambda x: UITGELICHT.index(sleutel(x[0])))
    nr, delen = 0, []
    for g in volgorde:
        if g not in groepen:
            continue
        kaarten = []
        for h, t, o in groepen[g]:
            nr += 1
            kaarten.append(tegel(nr, h, t, o))
        kop = '' if (g == 'Tools' and len(groepen) == 1) else f'<h2 class="tgkop">{html.escape(g)} <span>{len(kaarten)}</span></h2>'
        delen.append(f'<div class="tgroep" data-groep="{html.escape(g)}">{kop}<div class="tgrid">{"".join(kaarten)}</div></div>')
    blok = ('<section class="blk" id="tooloverzicht">'
            f'<div class="tfilter"><input type="search" placeholder="Filter de {nr} tools op deze pagina…" aria-label="Filter tools">'
            '<span class="tleeg" hidden>Geen tool gevonden. Gebruik de zoeker bovenaan of <a href="mailto:jeroen@oversteegen.nl?subject=Verzoek%20nieuwe%20rekentool">vraag een tool aan</a>.</span></div>'
            + ''.join(delen) + '</section>\n')
    main = main.replace('<!--OVERZICHT-->', blok, 1)
    s = s[:a] + main + s[b:]
    open(f, 'w', encoding='utf-8').write(s)
    print(f'{pagina}: {nr} tools in {len(groepen)} groep(en)')


def home():
    f = os.path.join(ROOT, 'index.html')
    s = open(f, encoding='utf-8').read()
    nr = 0
    def ol(m):
        nonlocal nr
        start = nr + 1
        nr += m.group(2).count('<li')
        return f'<ol start="{start}"{m.group(1)}>{m.group(2)}</ol>'
    s2 = re.sub(r'<ol(?: start="\d+")?([^>]*)>(.*?)</ol>', ol, s, flags=re.S)
    open(f, 'w', encoding='utf-8').write(s2)
    print(f'home: {nr} items doorlopend genummerd')


for p in PAGINAS:
    verwerk(p)
home()
