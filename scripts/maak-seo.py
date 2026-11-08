#!/usr/bin/env python3
"""SEO en GEO: meta-tags, canonical, Open Graph, JSON-LD, sitemap.xml, robots.txt en llms.txt.

Draai als laatste stap (na maak-overzicht.py en opmaak-site.py):  python3 scripts/maak-seo.py
Idempotent: bestaande SEO-blokken (tussen <!--SEO--> en <!--/SEO-->) worden vervangen.
"""
import datetime, glob, html, json, os, re, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deelafbeelding

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = 'https://adviseurstools.nl/'
SITE = 'Adviseurstools.nl'
VANDAAG = datetime.date.today().isoformat()
BEVEILIGD = ('project-jeroen/', 'platformen/')
CATS = {'hypotheek': 'Hypotheek', 'krediet': 'Krediet', 'assurantie': 'Assurantie',
        'vermogen-pensioen': 'Vermogen & pensioen', 'overige': 'Overige tools', 'platformen': 'Platformen'}
HOME_OMS = ('Gratis rekentools voor hypotheekadviseurs en consumenten: maximale hypotheek volgens de leennormen 2026 en 2027, '
            'maandlasten, boeterente, pensioen en AOW, scheiding, overdrachtsbelasting, box 3, krediet en verzekeringen.')
E = html.escape


def lees(p):
    return open(p, encoding='utf-8').read()


def tekst(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()


def pagina_info(f, s):
    rel = os.path.relpath(os.path.dirname(f), ROOT).replace(os.sep, '/')
    pad = '' if rel == '.' else rel + '/'
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    titel = tekst(h1.group(1)) if h1 else SITE
    sub = re.search(r'<p class="pk-sub">(.*?)</p>', s, re.S)
    oms = tekst(sub.group(1)) if sub else ''
    kruimel = [(tekst(t), h) for h, t in re.findall(r'<nav class="kruimel"[^>]*>.*?</nav>', s, re.S) and
               re.findall(r'<a href="([^"]+)">(.*?)</a>', re.search(r'<nav class="kruimel"[^>]*>(.*?)</nav>', s, re.S).group(1))]
    return pad, titel, oms, kruimel


def abs_url(pad, href):
    u = urllib.parse.urljoin(BASE + pad, href)
    return u if u.startswith('http') and not u.startswith(BASE) else BASE + urllib.parse.quote(urllib.parse.unquote(u[len(BASE):]), safe='/')


def ld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(',', ':')) + '</script>'


ORG = {'@type': 'Organization', '@id': BASE + '#org', 'name': SITE, 'url': BASE,
       'logo': BASE + 'assets/logo.webp', 'email': 'jeroen@oversteegen.nl', 'telephone': '+31621247257'}

pages_sitemap, llms = [], {}
for f in sorted(glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True)):
    rp = os.path.relpath(f, ROOT)
    if rp.startswith(('tools', 'assets', 'scripts')):
        continue
    s = lees(f)
    if 'http-equiv="refresh"' in s:       # /home/ doorverwijzing
        if 'name="robots"' not in s:
            s = s.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta name="robots" content="noindex,follow">')
            open(f, 'w', encoding='utf-8').write(s)
        continue
    pad, titel, oms, kruimel = pagina_info(f, s)
    beveiligd = pad.startswith(BEVEILIGD)
    is_home, is_cat = pad == '', pad.rstrip('/') in CATS
    url = BASE + urllib.parse.quote(pad, safe='/')
    if is_home:
        ttl = f'{SITE} — rekentools voor hypotheek, krediet en pensioen (normen 2026 en 2027)'
        desc = HOME_OMS
    elif is_cat:
        ttl = f'{CATS[pad.rstrip("/")]} rekentools — {SITE}'
        desc = f'{oms}. Gratis rekentools volgens de normen 2026 en 2027.' if oms else HOME_OMS
    else:
        ttl = f'{titel} — gratis rekentool | {SITE}'
        desc = (oms.rstrip('.') + '. ' if oms else '') + f'Gratis rekentool van {SITE}, normen 2026 en 2027. Indicatief, geen financieel advies.'
    desc = desc[:300]
    graph = [ORG]
    if is_home:
        graph.append({'@type': 'WebSite', '@id': BASE + '#site', 'url': BASE, 'name': SITE, 'inLanguage': 'nl-NL',
                      'publisher': {'@id': BASE + '#org'}, 'description': HOME_OMS,
                      'potentialAction': {'@type': 'SearchAction', 'target': BASE + '?q={search_term_string}',
                                          'query-input': 'required name=search_term_string'}})
    elif is_cat:
        items = [{'@type': 'ListItem', 'position': i + 1, 'name': tekst(t), 'url': abs_url(pad, html.unescape(h))}
                 for i, (h, t) in enumerate(re.findall(r'<a class="tcard" href="([^"]+)"[^>]*>.*?<span class="ttl">(.*?)</span>', s, re.S))]
        graph.append({'@type': 'CollectionPage', 'name': ttl, 'url': url, 'description': desc, 'inLanguage': 'nl-NL',
                      'mainEntity': {'@type': 'ItemList', 'numberOfItems': len(items), 'itemListElement': items}})
    elif not beveiligd and 'iframe class="autofit"' in s:
        graph.append({'@type': 'WebApplication', 'name': titel, 'url': url, 'description': desc, 'inLanguage': 'nl-NL',
                      'applicationCategory': 'FinanceApplication', 'operatingSystem': 'Any', 'isAccessibleForFree': True,
                      'offers': {'@type': 'Offer', 'price': '0', 'priceCurrency': 'EUR'}, 'publisher': {'@id': BASE + '#org'}})
    if kruimel:
        bc = [{'@type': 'ListItem', 'position': i + 1, 'name': t, 'item': abs_url(pad, h)} for i, (t, h) in enumerate(kruimel)]
        bc.append({'@type': 'ListItem', 'position': len(bc) + 1, 'name': titel, 'item': url})
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': bc})
    # Deelafbeelding per pagina (LinkedIn, WhatsApp, Teams, X): titel, korte omschrijving en rubriek
    if beveiligd or is_home:
        og_naam, og_alt = 'og.png', f'{SITE} — gratis rekentools voor hypotheek, krediet en pensioen'
        if is_home:
            deelafbeelding.maak(SITE, 'Maximale hypotheek, maandlasten, boeterente, pensioen en AOW — voor adviseurs en consumenten',
                                '', os.path.join(ROOT, 'assets', 'og.png'))
    else:
        slug = re.sub(r'[^a-z0-9]+', '-', urllib.parse.unquote(pad).lower().replace('é', 'e').replace('ë', 'e')).strip('-')
        og_naam = 'og/' + slug + '.png'
        og_titel = (CATS[pad.rstrip('/')] + ' rekentools') if is_cat else titel
        og_sub = oms or ('Gratis rekentools volgens de normen 2026 en 2027' if is_cat else '')
        rubriek = '' if is_cat else CATS.get(pad.split('/')[0], '')
        deelafbeelding.maak(og_titel, og_sub, rubriek, os.path.join(ROOT, 'assets', og_naam))
        og_alt = f'{og_titel} — {SITE}'
    og_url = BASE + 'assets/' + og_naam
    meta = [f'<meta name="description" content="{E(desc)}">',
            f'<meta name="robots" content="{"noindex,nofollow" if beveiligd else "index,follow,max-image-preview:large"}">',
            f'<link rel="canonical" href="{E(url)}">',
            '<meta name="theme-color" content="#003057">',
            f'<meta property="og:type" content="{"website" if is_home else "article"}">',
            f'<meta property="og:site_name" content="{SITE}">', '<meta property="og:locale" content="nl_NL">',
            f'<meta property="og:title" content="{E(ttl)}">', f'<meta property="og:description" content="{E(desc)}">',
            f'<meta property="og:url" content="{E(url)}">', f'<meta property="og:image" content="{og_url}">',
            f'<meta property="og:image:secure_url" content="{og_url}">', '<meta property="og:image:type" content="image/png">',
            '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
            f'<meta property="og:image:alt" content="{E(og_alt)}">',
            '<meta name="twitter:card" content="summary_large_image">',
            f'<meta name="twitter:title" content="{E(ttl)}">', f'<meta name="twitter:description" content="{E(desc)}">',
            f'<meta name="twitter:image" content="{og_url}">', f'<meta name="twitter:image:alt" content="{E(og_alt)}">',
            ld({'@context': 'https://schema.org', '@graph': graph})]
    blok = '<!--SEO-->' + '\n'.join(meta) + '<!--/SEO-->'
    s = re.sub(r'<!--SEO-->.*?<!--/SEO-->\n?', '', s, flags=re.S)
    s = re.sub(r'<meta name="description"[^>]*>\n?', '', s)  # losse (dubbele) description buiten het SEO-blok
    s = re.sub(r'<title>.*?</title>', f'<title>{E(ttl)}</title>', s, count=1, flags=re.S)
    s = s.replace('</title>', '</title>\n' + blok, 1)
    open(f, 'w', encoding='utf-8').write(s)
    if not beveiligd:
        pages_sitemap.append((url, '1.0' if is_home else '0.8' if is_cat else '0.6'))
        cat = 'Algemeen' if is_home else CATS.get(pad.split('/')[0], 'Overige tools')
        if not is_home and not is_cat and pad != 'contact/':
            llms.setdefault(cat, []).append((titel, url, oms))
        # canonical in de losse tool (inhoud hoort bij deze pagina)
        m = re.search(r'src="(?:\.\./)*tools/([^"]+)"', s)
        if m:
            tf = os.path.join(ROOT, 'tools', urllib.parse.unquote(html.unescape(m.group(1))))
            if os.path.exists(tf):
                t = lees(tf)
                t2 = re.sub(r'<link rel="canonical" href="[^"]*" data-site>\n?', '', t)
                if '<head>' in t2 or re.search(r'<head[^>]*>', t2):
                    t2 = re.sub(r'(<head[^>]*>)', r'\1\n<link rel="canonical" href="' + E(url) + '" data-site>', t2, count=1)
                    if t2 != t:
                        open(tf, 'w', encoding='utf-8').write(t2)

# 404: niet indexeren
p404 = os.path.join(ROOT, '404.html')
s = lees(p404)
if 'name="robots"' not in s:
    s = s.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex">', 1)
    open(p404, 'w', encoding='utf-8').write(s)

# sitemap.xml
with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as out:
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
    for u, prio in pages_sitemap:
        out.write(f'  <url><loc>{E(u)}</loc><lastmod>{VANDAAG}</lastmod><priority>{prio}</priority></url>\n')
    out.write('</urlset>\n')

# robots.txt
with open(os.path.join(ROOT, 'robots.txt'), 'w', encoding='utf-8') as out:
    out.write('# Adviseurstools.nl — zoekmachines en AI-assistenten zijn welkom\n'
              'User-agent: *\nAllow: /\nDisallow: /project-jeroen/\nDisallow: /platformen/\n\n'
              + ''.join(f'User-agent: {b}\nAllow: /\nDisallow: /project-jeroen/\nDisallow: /platformen/\n\n'
                        for b in ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-User', 'PerplexityBot', 'Google-Extended', 'Applebot-Extended'])
              + f'Sitemap: {BASE}sitemap.xml\n')

# llms.txt (GEO)
volg = ['Hypotheek', 'Krediet', 'Assurantie', 'Vermogen & pensioen', 'Overige tools']
with open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8') as out:
    out.write(f'# {SITE}\n\n> {HOME_OMS} Alle berekeningen draaien in de browser; uitkomsten zijn indicatief en geen financieel advies.\n\n'
              'Belangrijk:\n- Normen: Tijdelijke regeling hypothecair krediet 2026 (Nibud-financieringslasttabellen), Trhk 2027 (Stcrt. 2026, 38415) met normjaarkeuze 2026/2027, NHG Voorwaarden en normen 2026 en NHG-kostengrens 2027, fiscale waarden 2026.\n'
              '- Doelgroep: hypotheekadviseurs, financieel planners en consumenten in Nederland.\n'
              f'- Contact en tool-aanvragen: jeroen@oversteegen.nl\n\n')
    for cat in volg:
        if cat in llms:
            out.write(f'## {cat}\n\n')
            for t, u, o in sorted(llms[cat], key=lambda x: x[0].lower()):
                out.write(f'- [{t}]({u})' + (f': {o}' if o else '') + '\n')
            out.write('\n')
    out.write(f'## Optioneel\n\n- [Contact]({BASE}contact/)\n- [Sitemap]({BASE}sitemap.xml)\n')

print(len(pages_sitemap), 'pagina\'s in sitemap;', sum(len(v) for v in llms.values()), 'tools in llms.txt')
