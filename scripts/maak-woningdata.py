#!/usr/bin/env python3
"""Woningdata per gemeente ophalen en VAST in de tools zetten (geen API-aanroep tijdens gebruik).

Gebruik (één keer per jaar, of na een nieuwe CBS- of COELO-publicatie):
    python3 scripts/maak-woningdata.py            # ophalen, controleren en de tools bijwerken
    python3 scripts/maak-woningdata.py --droog    # alleen ophalen en controleren, niets schrijven

Bronnen (allemaal open data, opgehaald via HTTPS):
  CBS StatLine OData (https://opendata.cbs.nl/ODataApi/odata/<tabel>)
    83625NED  Bestaande koopwoningen; gemiddelde verkoopprijzen, regio (recentste volledige jaar)
    85792NED  Bestaande koopwoningen; verkoopprijzen, prijsindex 2020=100, regio (kwartalen)
    85036NED  Gemiddelde WOZ-waarde van woningen; eigendom, regio (koopwoningen)
    Gebieden in Nederland <jaar>  (gemeente -> provincie; tabelnummer wordt via de catalogus gezocht)
    85140NED  Energieverbruik woningen; woningtype, oppervlakte, bouwjaar en bewoning
    85592NED  Gemiddelde energietarieven voor consumenten (recentste maand, incl. btw)
  COELO, Atlas van de lokale lasten <jaar> (https://www.coelo.nl/images/...xlsx)
    Gemeentelijke_belastingen_<jaar>.xlsx, Waterschapsbelastingen_<jaar>.xlsx,
    Website_gegevens_standaardhuishoudens_en_bedrijven_<jaar>.xlsx

De tools met een blok <script id="at-woningdata"></script> krijgen hun deel van de data
(zie TOOLS hieronder) als `window.ATWoningdata = {...}`. Tools met een blok
<script id="at-normen"></script> krijgen daarnaast assets/normen.js, net als scripts/maak-normen.py doet.
Alleen standaardbibliotheek (geen pip-pakketten nodig).
"""
import datetime, io, json, os, re, sys, time, urllib.error, urllib.request, zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CBS = 'https://opendata.cbs.nl/ODataApi/odata/'
CBS_CAT = 'https://opendata.cbs.nl/ODataCatalog/Tables'
COELO = 'https://www.coelo.nl/images/'

# Welke delen van de data in welke tool komen (houdt de bestanden klein).
TOOLS = {
    'tools/hypotheek__waar-kan-ik-kopen.html': ['meta', 'provincies', 'gemeenten:prijs', 'indexNu'],
    'tools/hypotheek__woonlasten-per-gemeente.html': ['meta', 'provincies', 'gemeenten:lasten', 'waterschappen', 'energie'],
    'tools/hypotheek__biedindicatie.html': ['meta', 'provincies', 'gemeenten:bied', 'index'],
}
INDEX_VANAF = 2014  # kwartaalreeks vanaf dit jaar (WOZ-peildata tot ruim 10 jaar terug)
NAAMFIX = {'HunzeenAas': "Hunze en Aa's", 'Fryslan': 'Fryslân'}  # alleen schrijfwijze van waterschapsnamen in de COELO-bron


def haal(url, binair=False, pogingen=4, xlsx=False):
    """Download met herhaalpogingen. xlsx=True: alleen een echt xlsx-bestand (zip) telt (de COELO-server geeft soms een HTML-pagina)."""
    fout = None
    for i in range(pogingen):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'adviseurstools-woningdata/1.0', 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if xlsx and data[:2] != b'PK':
                raise ValueError('geen xlsx ontvangen')
            return data if binair else data.decode('utf-8')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            fout = e
        except Exception as e:
            fout = e
        time.sleep(3 * (i + 1))
    raise fout


class _GeenDoorsturen(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def bestaat(url):
    """True als de URL direct (zonder doorsturen) met 200 antwoordt."""
    opener = urllib.request.build_opener(_GeenDoorsturen)
    for i in range(3):
        try:
            with opener.open(urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'adviseurstools-woningdata/1.0'}), timeout=60) as r:
                return r.status == 200
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308, 404, 410):
                return False
        except Exception:
            pass
        time.sleep(3 * (i + 1))
    return False


def cbs(tabel, pad, filt=None, select=None):
    """Alle rijen van een CBS OData-v3 resource (met paginering)."""
    url = f'{CBS}{tabel}/{pad}?$format=json'
    if filt:
        url += '&$filter=' + urllib.request.quote(filt)
    if select:
        url += '&$select=' + ','.join(select)
    rijen = []
    while url:
        d = json.loads(haal(url))
        rijen += d['value']
        url = d.get('odata.nextLink')
    return rijen


def tabelinfo(tabel):
    return cbs(tabel, 'TableInfos')[0]


def gebieden_tabel(jaar):
    """Zoek het tabelnummer van 'Gebieden in Nederland <jaar>' in de CBS-catalogus."""
    url = CBS_CAT + "?$format=json&$select=Identifier,Title&$filter=" + urllib.request.quote(f"Title eq 'Gebieden in Nederland {jaar}'")
    v = json.loads(haal(url))['value']
    return v[0]['Identifier'] if v else None


# ── xlsx lezen zonder openpyxl ──
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def xlsx_blad(data, bladnaam):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    doel = {r.get('Id'): r.get('Target') for r in rels}
    pad = None
    for s in wb.find('m:sheets', NS):
        if s.get('name') == bladnaam:
            t = doel[s.get('{%s}id' % NS['r'])]
            pad = 'xl/' + t.lstrip('/').replace('xl/', '', 1) if not t.startswith('/xl/') else t.lstrip('/')
    if pad is None:
        raise SystemExit(f'Blad {bladnaam!r} niet gevonden')
    rijen = []
    for row in ET.fromstring(z.read(pad)).iter('{%s}row' % NS['m']):
        cellen = {}
        for c in row.findall('m:c', NS):
            ref = re.match(r'([A-Z]+)', c.get('r')).group(1)
            col = 0
            for ch in ref:
                col = col * 26 + ord(ch) - 64
            v = c.find('m:v', NS)
            t = c.get('t')
            if t == 's' and v is not None:
                val = ss[int(v.text)]
            elif t == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
            elif v is not None:
                try:
                    val = float(v.text)
                except ValueError:
                    val = v.text
            else:
                val = None
            cellen[col - 1] = val
        n = max(cellen) + 1 if cellen else 0
        rijen.append([cellen.get(i) for i in range(n)])
    return rijen


def kolom(kop, *namen, start=0):
    """Index van de eerste kolom (vanaf start) waarvan de kop gelijk is aan een van de namen (zonder hoofdletters)."""
    for i in range(start, len(kop)):
        k = (kop[i] or '')
        if isinstance(k, str) and k.strip().lower() in [n.lower() for n in namen]:
            return i
    raise SystemExit(f'Kolom {namen} niet gevonden in de kop')


def getal(x):
    if x in (None, ''):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def r2(x):
    return None if x is None else round(x, 2)


def code4(x):
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s.zfill(4)


# ── ophalen ──
def prijzen():
    T = '83625NED'
    info = tabelinfo(T)
    perioden = [p['Key'] for p in cbs(T, 'Perioden') if p['Key'].endswith('JJ00')]
    for p in reversed(perioden):
        rij = cbs(T, 'TypedDataSet', f"Perioden eq '{p}' and substringof('GM',RegioS)")
        waarden = {r['RegioS'].strip(): r['GemiddeldeVerkoopprijs_1'] for r in rij if r['GemiddeldeVerkoopprijs_1'] is not None}
        if len(waarden) > 300:
            jaar = int(p[:4])
            vj = cbs(T, 'TypedDataSet', f"Perioden eq '{jaar - 1}JJ00' and substringof('GM',RegioS)")
            vorig = {r['RegioS'].strip(): r['GemiddeldeVerkoopprijs_1'] for r in vj if r['GemiddeldeVerkoopprijs_1'] is not None}
            namen = {r['Key'].strip(): r['Title'] for r in cbs(T, 'RegioS')}
            return {'tabel': T, 'titel': info['Title'], 'jaar': jaar, 'gewijzigd': info['Modified'][:10],
                    'waarden': waarden, 'vorig': vorig, 'namen': namen}
    raise SystemExit('Geen gemeentelijke prijzen gevonden in 83625NED')


def provincies(jaar):
    for j in (jaar + 1, jaar, jaar - 1):  # indeling van het peiljaar, of het jaar erna
        T = gebieden_tabel(j)
        if not T:
            continue
        rijen = cbs(T, 'TypedDataSet', select=['Code_1', 'Naam_2', 'Code_28', 'Naam_29'])
        if rijen:
            yield T, j, {r['Code_1'].strip(): (r['Naam_2'].strip(), r['Code_28'].strip(), r['Naam_29'].strip()) for r in rijen}


def prijsindex():
    T = '85792NED'
    info = tabelinfo(T)
    rijen = cbs(T, 'TypedDataSet', select=['RegioS', 'Perioden', 'PrijsindexVerkoopprijzen_1', 'OntwikkelingTOVEenJaarEerder_3', 'VerkochteWoningen_4'])
    regios = {r['Key'].strip(): r['Title'] for r in cbs(T, 'RegioS')}
    reeks, jaarwaarde = {}, {}
    for r in rijen:
        reg, p, v = r['RegioS'].strip(), r['Perioden'], r['PrijsindexVerkoopprijzen_1']
        if v is None:
            continue
        if 'KW' in p:
            reeks.setdefault(reg, {})[(int(p[:4]), int(p[-2:]))] = v
        elif p.endswith('JJ00'):
            jaarwaarde.setdefault(reg, {})[int(p[:4])] = v
    laatste = max(k for d in reeks.values() for k in d)
    return {'tabel': T, 'titel': info['Title'], 'gewijzigd': info['Modified'][:10], 'regios': regios,
            'reeks': reeks, 'jaar': jaarwaarde, 'laatste': laatste}


def woz():
    T = '85036NED'
    info = tabelinfo(T)
    perioden = sorted(p['Key'] for p in cbs(T, 'Perioden'))
    for p in reversed(perioden):
        rij = cbs(T, 'TypedDataSet', f"Perioden eq '{p}' and Eigendom eq '1014800' and substringof('GM',RegioS)")
        w = {r['RegioS'].strip(): r['GemiddeldeWOZWaardeVanWoningen_1'] for r in rij if r['GemiddeldeWOZWaardeVanWoningen_1'] is not None}
        if len(w) > 300:
            return {'tabel': T, 'titel': info['Title'], 'jaar': int(p[:4]), 'gewijzigd': info['Modified'][:10], 'waarden': w}
    raise SystemExit('Geen WOZ-waarden gevonden in 85036NED')


def energie():
    T = '85140NED'
    info = tabelinfo(T)
    perioden = sorted(p['Key'] for p in cbs(T, 'Perioden'))
    p = perioden[-1]
    types = {r['Key'].strip(): r['Title'] for r in cbs(T, 'Woningtype')}
    gas_vars = ['GemiddeldeAardgasTempGecPerOpp_13'] + [f'AardgasTempGecPerWoonoppPerc{n}0_{13 + n}' for n in range(1, 10)]
    rij = cbs(T, 'TypedDataSet',
              f"Perioden eq '{p}' and Gebruiksoppervlakte eq 'T001116' and Bouwjaar eq 'T001018' and Bewonersklasse eq 'T001351' "
              f"and HoofdverwarmingEnZonnestroom eq 'A052168'")
    uit = {}
    for r in rij:
        wt = r['Woningtype'].strip()
        if wt in ('ZW25809',):
            continue
        uit[wt] = {'naam': types[wt], 'gasPerM2': [r2(r[v]) for v in gas_vars],
                   'gas': r['GemiddeldeAardgasleveringTempGecorr_3'], 'elek': r['GemiddeldeElektriciteitslevering_23']}
    T2 = '85592NED'
    info2 = tabelinfo(T2)
    maanden = sorted(x['Key'] for x in cbs(T2, 'Perioden'))
    for m in reversed(maanden):
        t = cbs(T2, 'TypedDataSet', f"Perioden eq '{m}' and Btw eq 'A048944'")
        if t and t[0].get('VariabelLeveringstariefContractprijs_3') is not None:
            t = t[0]
            break
    tar = {
        'maand': m, 'gasVast': r2((t['Transporttarief_1'] or 0) + (t['VastLeveringstariefVasteEnVar_2'] or 0)),
        'gasM3': round((t['VariabelLeveringstariefContractprijs_3'] or 0) + (t['OpslagDuurzameEnergieODE_5'] or 0) + (t['Energiebelasting_6'] or 0), 4),
        'elekVast': r2((t['Transporttarief_7'] or 0) + (t['VastLeveringstariefVasteEnVar_8'] or 0)),
        'elekKwh': round((t['VariabelLeveringstariefContractprijs_9'] or 0) + (t['OpslagDuurzameEnergieODE_13'] or 0) + (t['Energiebelasting_14'] or 0), 4),
        'vermindering': r2(t['VerminderingEnergiebelasting_15']),
    }
    return {'tabel': T, 'titel': info['Title'], 'jaar': int(p[:4]), 'gewijzigd': info['Modified'][:10], 'types': uit,
            'tarieven': {'tabel': T2, 'titel': info2['Title'], 'gewijzigd': info2['Modified'][:10], **tar}}


def coelo():
    nu = datetime.date.today().year
    for jaar in (nu + 1, nu, nu - 1):
        if not bestaat(f'{COELO}Gemeentelijke_belastingen_{jaar}.xlsx'):
            continue  # nog niet gepubliceerd: de server stuurt door (301) of geeft 404
        gb = haal(f'{COELO}Gemeentelijke_belastingen_{jaar}.xlsx', binair=True, xlsx=True)
        wb = haal(f'{COELO}Waterschapsbelastingen_{jaar}.xlsx', binair=True, xlsx=True)
        sh = haal(f'{COELO}Website_gegevens_standaardhuishoudens_en_bedrijven_{jaar}.xlsx', binair=True, xlsx=True)
        break
    else:
        raise SystemExit('Geen COELO-bestanden gevonden')
    # gemeenten
    R = xlsx_blad(gb, 'Gegevens per gemeente')
    hi = next(i for i, r in enumerate(R) if r and any(isinstance(c, str) and c.strip().lower() == 'gemeentenaam' for c in r))
    kop, kop0 = R[hi], R[hi - 1]
    c_code, c_naam = kolom(kop, 'Gemeente code'), kolom(kop, 'Gemeentenaam')
    c_ozb = kolom(kop, 'Tarief woningen')
    c_ozbgem = kolom(kop, 'Gemiddeld betaalde ozb woningen')
    a = next(i for i, k in enumerate(kop0) if isinstance(k, str) and k.strip().lower() == 'afvalstoffenheffing')
    r_ = next(i for i, k in enumerate(kop0) if isinstance(k, str) and k.strip().lower() == 'rioolheffing huishoudens')
    c_af1, c_afm = kolom(kop, 'Eénpersoonshuishouden', start=a), kolom(kop, 'Meerpersoonshuishouden', start=a)
    c_ri1, c_rim = kolom(kop, 'Eénpersoonshuishouden', start=r_), kolom(kop, 'Meerpersoonshuishouden', start=r_)
    c_hk1, c_hkm = kolom(kop, 'Heffingskorting éénpersoonshuishouden'), kolom(kop, 'Heffingskorting meerpersoonshuishouden')
    gem = {}
    for r in R[hi + 2:]:
        if not r or len(r) <= c_hkm or r[c_code] in (None, '') or r[c_naam] in (None, ''):
            continue
        ozb = getal(r[c_ozb])
        gem[code4(r[c_code])] = {'naam': str(r[c_naam]).strip(), 'ozb': ozb, 'ozbGem': getal(r[c_ozbgem]),
                                 'afval': [r2(getal(r[c_af1])), r2(getal(r[c_afm]))],
                                 'riool': [r2(getal(r[c_ri1])), r2(getal(r[c_rim]))],
                                 'korting': [r2(getal(r[c_hk1]) or 0), r2(getal(r[c_hkm]) or 0)]}
    # waterschappen
    W = xlsx_blad(wb, 'Gegevens per waterschap')
    hi = next(i for i, r in enumerate(W) if r and len(r) > 1 and isinstance(r[1], str) and r[1].strip().lower() == 'waterschap')
    kop, kop0 = W[hi], W[hi - 1]
    wsg = next(i for i, k in enumerate(kop0) if isinstance(k, str) and k.strip().lower() == 'watersysteemheffing')
    weg = next((i for i, k in enumerate(kop0) if isinstance(k, str) and k.strip().lower() == 'wegenheffing'), None)
    c_z1, c_zm = kolom(kop, 'Eénpersoonshuishouden'), kolom(kop, 'Meerpersoonshuishouden')
    c_in, c_gw = kolom(kop, 'Ingezetenen', start=wsg), kolom(kop, 'Gebouwd woningen', start=wsg)
    c_win = kolom(kop, 'Ingezetenen', start=weg) if weg is not None else None
    c_wgb = kolom(kop, 'Gebouwd', start=weg) if weg is not None else None
    ws = []
    for r in W[hi + 2:]:
        if not r or len(r) < 3 or r[1] in (None, '') or getal(r[c_zm]) is None:
            continue
        naam = str(r[1]).strip()
        ws.append({'code': code4(r[0]), 'naam': NAAMFIX.get(naam, naam), 'zuiv': [r2(getal(r[c_z1])), r2(getal(r[c_zm]))],
                   'ingez': r2((getal(r[c_in]) or 0) + (getal(r[c_win]) or 0 if c_win is not None else 0)),
                   'gebouwd': round((getal(r[c_gw]) or 0) + ((getal(r[c_wgb]) or 0) if c_wgb is not None else 0), 5)})
    # standaardhuishouden koopwoning: (gewogen) waterschapslasten per gemeente -> waterschap afleiden
    S = xlsx_blad(sh, 'Decentrale lasten')
    hi = next(i for i, r in enumerate(S) if r and len(r) > 1 and isinstance(r[1], str) and r[1].strip().lower() == 'gemeentenaam')
    kop, kop2 = S[hi], S[hi - 2]
    k0 = next(i for i, k in enumerate(kop2) if isinstance(k, str) and 'koopwoning' in k.lower())
    c_zu, c_ig, c_hg = kolom(kop, 'Zuiveringsheffing', start=k0), kolom(kop, 'Ingezetenenheffing', start=k0), kolom(kop, 'Heffing gebouwd', start=k0)
    for r in S[hi + 2:]:
        if not r or r[0] in (None, '') or len(r) <= c_hg:
            continue
        c = code4(r[0])
        if c not in gem:
            continue
        zu, ig, hg = getal(r[c_zu]), getal(r[c_ig]), getal(r[c_hg])
        g = gem[c]
        wozC = g['ozbGem'] / (g['ozb'] / 100) if g['ozb'] and g['ozbGem'] else None
        match = [i for i, w in enumerate(ws) if abs(w['zuiv'][1] - zu) < 0.02 and abs(w['ingez'] - ig) < 0.02]
        g['ws'] = match[0] if len(match) == 1 else -1
        # gewogen gemiddelde (COELO) als terugval of als de gemeente onder meer waterschappen valt
        g['wsGew'] = {'zuivM': r2(zu), 'ingez': r2(ig), 'gebouwd': round(hg / wozC * 100, 5) if wozC and hg is not None else None}
    return {'jaar': jaar, 'gemeenten': gem, 'waterschappen': ws,
            'bestanden': [f'{COELO}Gemeentelijke_belastingen_{jaar}.xlsx', f'{COELO}Waterschapsbelastingen_{jaar}.xlsx',
                          f'{COELO}Website_gegevens_standaardhuishoudens_en_bedrijven_{jaar}.xlsx']}


def kw(t):
    return f'{t[0]}-K{t[1]}'


def bouw():
    vandaag = datetime.date.today().isoformat()
    print('CBS 83625NED (verkoopprijzen) …')
    P = prijzen()
    print('CBS Gebieden in Nederland …')
    prov = {}
    gebieden_bron = []
    for T, j, m in provincies(P['jaar']):
        gebieden_bron.append(f'{T} ({j})')
        for k, v in m.items():
            prov.setdefault(k, v)
    print('CBS 85792NED (prijsindex) …')
    I = prijsindex()
    print('CBS 85036NED (WOZ) …')
    Wz = woz()
    print('CBS 85140NED en 85592NED (energie) …')
    E = energie()
    print('COELO …')
    C = coelo()

    pv_namen = sorted({v[2] for v in prov.values()})
    pv_codes = {v[2]: v[1] for v in prov.values()}
    gemeenten, missen = [], []
    alle = sorted(set(P['waarden']) | set('GM' + c for c in C['gemeenten']) | set(Wz['waarden']))
    for gm in alle:
        c = gm[2:]
        p = prov.get(gm)
        naam = (C['gemeenten'].get(c) or {}).get('naam') or (p[0] if p else re.sub(r'\s*\(gemeente\)$', '', P['namen'].get(gm, gm)))
        if not p:
            missen.append(gm)
            continue
        cg = C['gemeenten'].get(c)
        gemeenten.append({
            'c': c, 'n': naam, 'p': pv_namen.index(p[2]),
            'prijs': P['waarden'].get(gm), 'prijsVJ': P['vorig'].get(gm),
            'woz': round(Wz['waarden'][gm] * 1000) if gm in Wz['waarden'] else None,
            'idx': gm if gm in I['reeks'] else pv_codes[p[2]],
            'cg': cg,
        })
    if missen:
        print('LET OP: zonder provincie (overgeslagen):', ', '.join(missen))

    # controles
    n_prijs = sum(1 for g in gemeenten if g['prijs'])
    n_lasten = sum(1 for g in gemeenten if g['cg'])
    n_ws = sum(1 for g in gemeenten if g['cg'] and g['cg'].get('ws', -1) >= 0)
    print(f'{len(gemeenten)} gemeenten: {n_prijs} met verkoopprijs {P["jaar"]}, {n_lasten} met COELO-lasten {C["jaar"]} '
          f'({n_ws} met één waterschap), {sum(1 for g in gemeenten if g["woz"])} met WOZ {Wz["jaar"]}')
    if n_prijs < 300 or n_lasten < 300:
        raise SystemExit('Te weinig gemeenten met data; controleer de bronnen.')

    lq = I['laatste']
    jaar_idx = P['jaar']
    meta = {
        'downloaddatum': vandaag,
        'prijzen': {'bron': 'CBS StatLine', 'tabel': P['tabel'], 'titel': P['titel'], 'peiljaar': P['jaar'], 'gewijzigd': P['gewijzigd'],
                    'url': f'https://opendata.cbs.nl/#/CBS/nl/dataset/{P["tabel"]}/table'},
        'index': {'bron': 'CBS/Kadaster', 'tabel': I['tabel'], 'titel': I['titel'], 'laatsteKwartaal': kw(lq), 'gewijzigd': I['gewijzigd'],
                  'url': f'https://opendata.cbs.nl/#/CBS/nl/dataset/{I["tabel"]}/table'},
        'woz': {'bron': 'CBS StatLine', 'tabel': Wz['tabel'], 'titel': Wz['titel'], 'peiljaar': Wz['jaar'], 'gewijzigd': Wz['gewijzigd'],
                'url': f'https://opendata.cbs.nl/#/CBS/nl/dataset/{Wz["tabel"]}/table'},
        'gebieden': {'bron': 'CBS StatLine', 'tabel': ', '.join(gebieden_bron)},
        'lasten': {'bron': 'COELO, Atlas van de lokale lasten', 'jaar': C['jaar'], 'bestanden': C['bestanden'],
                   'url': f'https://coelo.nl/atlas-lokale-lasten-{C["jaar"]}/bijlagen-{C["jaar"]}-en-databestanden/'},
        'energie': {'bron': 'CBS StatLine', 'tabel': E['tabel'], 'titel': E['titel'], 'peiljaar': E['jaar'], 'gewijzigd': E['gewijzigd'],
                    'url': f'https://opendata.cbs.nl/#/CBS/nl/dataset/{E["tabel"]}/table',
                    'tarieven': {k: E['tarieven'][k] for k in ('tabel', 'titel', 'maand', 'gewijzigd')}},
    }
    regios_nodig = sorted({g['idx'] for g in gemeenten} | {'NL01'})
    start = (INDEX_VANAF, 1)
    reeksen = {}
    for reg in regios_nodig:
        d = I['reeks'][reg]
        ks = sorted(k for k in d if k >= start)
        reeksen[reg] = [round(d[k], 1) for k in ks]
        if ks[0] != start or ks[-1] != lq or len(ks) != (lq[0] - start[0]) * 4 + lq[1]:
            raise SystemExit(f'Indexreeks {reg} niet aaneengesloten')
    delen = {
        'meta': meta,
        'provincies': pv_namen,
        'indexNu': {'regios': {r: I['regios'][r].replace(' (PV)', '').replace(' (gemeente)', '') for r in regios_nodig},
                    'jaar': jaar_idx, 'kwartaal': kw(lq),
                    'factor': {r: round(I['reeks'][r][lq] / I['jaar'][r][jaar_idx], 4) for r in regios_nodig}},
        'index': {'regios': {r: I['regios'][r].replace(' (PV)', '').replace(' (gemeente)', '') for r in regios_nodig},
                  'start': kw(start), 'laatste': kw(lq), 'reeks': reeksen,
                  'jaar': {r: {str(j): round(v, 1) for j, v in I['jaar'][r].items() if j >= INDEX_VANAF} for r in regios_nodig}},
        'waterschappen': [[w['code'], w['naam'], w['zuiv'][0], w['zuiv'][1], w['ingez'], w['gebouwd']] for w in C['waterschappen']],
        'energie': {'types': E['types'], 'tarieven': E['tarieven']},
    }
    gvar = {
        # kolommen per variant; zie 'kolommen' in de uitvoer
        'prijs': (['code', 'naam', 'prov', 'prijs', 'prijsVorigJaar', 'indexRegio'],
                  lambda g: [g['c'], g['n'], g['p'], g['prijs'], g['prijsVJ'], g['idx']], lambda g: g['prijs']),
        'bied': (['code', 'naam', 'prov', 'prijs', 'prijsVorigJaar', 'indexRegio', 'wozKoop'],
                 lambda g: [g['c'], g['n'], g['p'], g['prijs'], g['prijsVJ'], g['idx'], g['woz']], lambda g: True),
        'lasten': (['code', 'naam', 'prov', 'wozKoop', 'ozbPct', 'afval1', 'afvalMeer', 'riool1', 'rioolMeer', 'korting1', 'kortingMeer',
                    'waterschap', 'wsGewZuivMeer', 'wsGewIngez', 'wsGewGebouwdPct'],
                   lambda g: [g['c'], g['n'], g['p'], g['woz'], g['cg']['ozb'], *g['cg']['afval'], *g['cg']['riool'], *g['cg']['korting'],
                              g['cg'].get('ws', -1), g['cg']['wsGew']['zuivM'], g['cg']['wsGew']['ingez'], g['cg']['wsGew']['gebouwd']],
                   lambda g: g['cg'] and 'wsGew' in g['cg']),
    }
    for v, (kols, f, ok) in gvar.items():
        delen['gemeenten:' + v] = {'kolommen': kols, 'rijen': [f(g) for g in sorted(gemeenten, key=lambda x: x['n'].lower()) if ok(g)]}
    return delen


def schrijf(delen):
    lib = open(os.path.join(ROOT, 'assets', 'normen.js'), encoding='utf-8').read()
    blok_n = re.compile(r'(<script id="at-normen">)(.*?)(</script>)', re.S)
    blok_w = re.compile(r'(<script id="at-woningdata">)(.*?)(</script>)', re.S)
    for pad, keys in TOOLS.items():
        f = os.path.join(ROOT, pad)
        if not os.path.exists(f):
            print('overgeslagen (bestaat niet):', pad)
            continue
        data = {}
        for k in keys:
            data[k.split(':')[0]] = delen[k]
        js = ('\n/* Woningdata — gegenereerd door scripts/maak-woningdata.py op ' + delen['meta']['downloaddatum'] +
              '. Niet met de hand aanpassen. */\nwindow.ATWoningdata = ' +
              json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + ';\n')
        s = open(f, encoding='utf-8').read()
        s2 = blok_w.sub(lambda m: m.group(1) + js + m.group(3), s, count=1)
        if 'id="at-normen"' in s2:
            s2 = blok_n.sub(lambda m: m.group(1) + '\n' + lib + '\n' + m.group(3), s2, count=1)
        if s2 != s:
            open(f, 'w', encoding='utf-8').write(s2)
        print(f'{pad}: {len(s2.encode("utf-8")) // 1024} kB')


if __name__ == '__main__':
    d = bouw()
    if '--droog' in sys.argv:
        print(json.dumps({k: (v if k == 'meta' else '…') for k, v in d.items()}, ensure_ascii=False, indent=1))
    else:
        schrijf(d)
