#!/usr/bin/env python3
"""Centrale normen: één bron (data/normen.json) → API, rekenbibliotheek en alle tools.

Gebruik na het aanpassen van data/normen.json:
    python3 scripts/maak-normen.py
Alleen bepaalde tools bijwerken (bijv. tijdens het ombouwen van een tool):
    python3 scripts/maak-normen.py --alleen tools/a.html tools/b.html

Wat het doet:
1. Controleert data/normen.json (tabellen compleet, inkomens oplopend, 12 rentekolommen).
2. Schrijft de openbare API: api/normen.json en api/normen-<jaar>.json.
3. Schrijft de rekenbibliotheek assets/normen.js (window.ATNormen) voor pagina's op de site.
4. Werkt elke tool bij die een blok <script id="at-normen">…</script> bevat: de bibliotheek
   met de actuele normen wordt daarin gezet, zodat de tool een losstaand HTML-bestand blijft.
"""
import fcntl, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRON = os.path.join(ROOT, 'data', 'normen.json')
LIB = os.path.join(ROOT, 'scripts', 'normen-lib.js')


def fout(msg):
    sys.exit('FOUT in data/normen.json: ' + msg)


def controleer(n):
    ln = n['leennormen']
    nk = len(ln['rentekolommen']['bovengrenzen']) + 1
    if len(ln['rentekolommen']['labels']) != nk:
        fout('aantal kolomlabels klopt niet')
    if len(ln['studieschuld_bruteringsfactor']) != nk:
        fout('aantal bruteringsfactoren klopt niet')
    for jaar, tabs in ln['financieringslast'].items():
        for t in '1234':
            T = tabs.get(t) or fout(f'tabel {t} ontbreekt voor {jaar}')
            inc = T['incomes']
            if inc != sorted(inc) or len(inc) != len(T['matrix']):
                fout(f'tabel {jaar}/{t}: inkomens niet oplopend of aantal rijen klopt niet')
            for r in T['matrix']:
                if len(r) != nk or any(not (0 < v < 100) for v in r):
                    fout(f'tabel {jaar}/{t}: rij met {len(r)} waarden of waarde buiten 0–100')
        for k in ('alleenstaandenbedrag',):
            if jaar not in ln[k]:
                fout(f'{k} ontbreekt voor {jaar}')
        if jaar not in n['nhg']:
            fout(f'NHG ontbreekt voor {jaar}')
    for k, T in n['nhg']['beheer']['tabellen'].items():
        if len(T['incomes']) != len(T['matrix']) or any(len(r) != nk for r in T['matrix']):
            fout(f'beheertabel {k} onvolledig')


def main():
    alleen = None
    if '--alleen' in sys.argv:
        alleen = {os.path.abspath(x) for x in sys.argv[sys.argv.index('--alleen') + 1:]}
    slot = open(os.path.join(ROOT, 'data', '.normen.lock'), 'w')
    fcntl.flock(slot, fcntl.LOCK_EX)  # één tegelijk (API en bibliotheek schrijven)
    n = json.load(open(BRON, encoding='utf-8'))
    controleer(n)
    os.makedirs(os.path.join(ROOT, 'api'), exist_ok=True)
    compact = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
    open(os.path.join(ROOT, 'api', 'normen.json'), 'w', encoding='utf-8').write(compact(n))
    for jaar in n['leennormen']['financieringslast']:
        ln = n['leennormen']
        sub = {
            'versie': n['versie'], 'jaar': jaar, 'bron': ln['bron'].get(jaar),
            'rentekolommen': ln['rentekolommen'], 'tabelnamen': ln['tabelnamen'],
            'financieringslast': ln['financieringslast'][jaar], 'toetsrente': ln['toetsrente'],
            'studieschuld_bruteringsfactor': ln['studieschuld_bruteringsfactor'],
            'krediet_maandlast_pct_limiet': ln['krediet_maandlast_pct_limiet'],
            'alleenstaandenbedrag': ln['alleenstaandenbedrag'][jaar],
            'energielabel_aankoop': ln['energielabel_aankoop'],
            'energiebesparende_voorzieningen': ln['energiebesparende_voorzieningen'],
            'nhg': n['nhg'][jaar], 'nhg_beheer': n['nhg']['beheer'], 'pensioentoets': n.get('pensioentoets'), 'fiscaal': n['fiscaal'].get(jaar) or n['fiscaal'][max(n['fiscaal'])],
        }
        open(os.path.join(ROOT, 'api', f'normen-{jaar}.json'), 'w', encoding='utf-8').write(compact(sub))
    lib = open(LIB, encoding='utf-8').read().replace('/*@DATA*/null', compact(n))
    open(os.path.join(ROOT, 'assets', 'normen.js'), 'w', encoding='utf-8').write(lib)
    blok = re.compile(r'(<script id="at-normen">)(.*?)(</script>)', re.S)
    bijgewerkt = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'tools', '*.html'))):
        if alleen is not None and os.path.abspath(f) not in alleen:
            continue
        s = open(f, encoding='utf-8').read()
        if 'id="at-normen"' not in s:
            continue
        s2 = blok.sub(lambda m: m.group(1) + '\n' + lib + '\n' + m.group(3), s, count=1)
        if s2 != s:
            open(f, 'w', encoding='utf-8').write(s2)
        bijgewerkt.append(os.path.basename(f))
    print(f'normen {n["versie"]}: API ({len(n["leennormen"]["financieringslast"])} normjaren), assets/normen.js, '
          f'{len(bijgewerkt)} tools bijgewerkt' + (': ' + ', '.join(bijgewerkt) if bijgewerkt else ''))


if __name__ == '__main__':
    main()
