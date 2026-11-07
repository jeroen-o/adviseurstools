#!/usr/bin/env python3
"""Maak assets/zoekindex.js: titel, categorie, url en trefwoorden van elke pagina.

Draai na het toevoegen of hernoemen van pagina's/tools:  python3 scripts/maak-zoekindex.py
Versleutelde pagina's (met <script id="versleuteld">) krijgen alleen titel en categorie.
"""
import glob, html, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = {'hypotheek': 'Hypotheek', 'krediet': 'Krediet', 'assurantie': 'Assurantie',
       'vermogen-pensioen': 'Vermogen & pensioen', 'overige': 'Overige', 'platformen': 'Platformen'}
STOP = set('de het een en of van voor met op in te is je jouw uw u wat bij als aan tot naar om door dan dit die deze niet ook zijn wordt'.split())


def tekst(s):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()


def kopjes(s, n=25):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    uit = []
    for tag in ('title', 'h1', 'h2', 'h3', 'label', 'button'):
        for m in re.findall(rf'<{tag}[^>]*>(.*?)</{tag}>', s, flags=re.S | re.I):
            t = tekst(m)
            if 2 < len(t) < 90 and t not in uit:
                uit.append(t)
    return uit[:n]


RUIS = {'LET OP!', 'DISCLAIMER', 'ADVISEURSTOOLS.NL', 'GEEN FINANCIEEL ADVIES', 'FOUTEN EN AANSPRAKELIJKHEID',
        'RAADPLEEG EEN DESKUNDIGE', 'BEPERKT RESPONSIEF', 'TOOL VOOR OP JE EIGEN WEBSITE?'}
AFK = {'aow', 'nhg', 'orv', 'aov', 'bkr', 'vfn', 'woz', 'ewr', 'rvp', 'oha', 'ww', 'pep', 'hdn', 'ghf', 'afm', 'duo',
       'nibud', 'svn', 'chf', 'wia', 'anw', 'ibl', 'itc', 'afd', 'ai', 'zzp'}


def netjes(t):
    if t != t.upper() or not re.search('[A-Z]', t):
        return t
    w = t.lower().split(' ')
    w = [x.upper() if x.strip('.,-:()') in AFK else x for x in w]
    w = [re.sub(r'^([a-z]+)-([a-z]+)$', lambda m: (m.group(1).upper() if m.group(1) in AFK else m.group(1)) + '-' + m.group(2), x) for x in w]
    out = ' '.join(w)
    return out[0].upper() + out[1:]


items = []
for f in sorted(glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True)):
    rel = os.path.relpath(os.path.dirname(f), ROOT).replace(os.sep, '/')
    if rel.startswith(('tools', 'assets', 'scripts', 'home')):
        continue
    s = open(f, encoding='utf-8').read()
    if 'http-equiv="refresh"' in s:
        continue
    url = '' if rel == '.' else rel + '/'
    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
    titel = tekst(h1.group(1)) if h1 else rel
    if rel == '.':
        titel = 'Home'
    titel = netjes(titel)
    cat = CAT.get(url.split('/')[0], 'Algemeen')
    beveiligd = 'id="versleuteld"' in s
    woorden = []
    if not beveiligd:
        m = re.search(r'src="(?:\.\./)*tools/([^"]+)"', s)
        if m:
            tf = os.path.join(ROOT, 'tools', html.unescape(m.group(1)))
            if os.path.exists(tf):
                woorden += kopjes(open(tf, encoding='utf-8', errors='ignore').read(), 30)
    woorden = [re.sub(r'\s*[–|-]\s*ADVISEURSTOOLS\.NL.*$', '', w, flags=re.I) for w in woorden]
    woorden = [w for w in woorden if w and w.upper() not in RUIS]
    kw = ' '.join(w for w in woorden if w.lower() != titel.lower())
    kw = ' '.join(t for t in kw.split() if t.lower() not in STOP)[:600]
    items.append({'t': titel, 'c': 'Beveiligd' if beveiligd else cat, 'u': url, 'k': kw})

items.sort(key=lambda x: (x['u'] != '', x['t'].lower()))
with open(os.path.join(ROOT, 'assets', 'zoekindex.js'), 'w', encoding='utf-8') as out:
    out.write('// Automatisch gemaakt door scripts/maak-zoekindex.py — niet handmatig bewerken.\n')
    out.write('window.ZOEKINDEX=' + json.dumps(items, ensure_ascii=False, separators=(',', ':')) + ';\n')
print(len(items), 'pagina\'s in de zoekindex')
