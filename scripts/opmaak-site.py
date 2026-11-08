#!/usr/bin/env python3
"""Site-opmaak: kop met kruimelpad, gerelateerde tools, sitefooter en nieuwe homepage.

Raakt alleen de 'verpakking' van pagina's aan (kop, titelblok, footer, home-inhoud);
de tools zelf en versleutelde inhoud blijven ongewijzigd. Idempotent.
Draai na scripts/maak-overzicht.py:  python3 scripts/opmaak-site.py
"""
import glob, html, os, re, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATS = [('hypotheek', 'Hypotheek'), ('krediet', 'Krediet'), ('assurantie', 'Assurantie'),
        ('vermogen-pensioen', 'Vermogen & pensioen'), ('overige', 'Overige tools'), ('platformen', 'Platformen')]
CATNAAM = dict(CATS)
CAT_OMS = {'hypotheek': 'Maximale hypotheek, maandlasten, pensioen, scheiding, aankoop en fiscaal',
           'krediet': 'Verantwoord lenen, VFN-normen en het effect op je hypotheek',
           'assurantie': 'Dekkingscheck, polissen, opstal en schade',
           'vermogen-pensioen': 'Pensioen, AOW, box 3 en vermogen',
           'overige': 'Levensstandaard, WOZ, klimaat, scheiding en meer',
           'platformen': 'Adviesplatforms (met wachtwoord)'}
MAIL, TEL, WA = 'jeroen@oversteegen.nl', '06-21247257', 'https://wa.me/31621247257?text=Hoi%20Jeroen%2C%20ik%20heb%20een%20vraag%20via%20je%20website.'
E = html.escape


def lees(p):
    return open(p, encoding='utf-8').read()


def schrijf(p, s):
    open(p, 'w', encoding='utf-8').write(s)


def rel(paginadir):
    d = os.path.relpath(paginadir, ROOT)
    return '' if d == '.' else '../' * (d.count('/') + 1)


# ---------- gegevens uit de tegeloverzichten ----------
INFO, GROEPEN = {}, {}   # pad (t.o.v. root, met /) -> dict ; (cat, groep) -> [pad]
for cat, naam in CATS:
    s = lees(os.path.join(ROOT, cat, 'index.html'))
    for g, blok in re.findall(r'<div class="tgroep" data-groep="([^"]+)">(.*?)</div></div>', s, re.S):
        g = html.unescape(g)
        for href, ttl, sub in re.findall(r'<a class="tcard" href="([^"]+)"[^>]*>.*?<span class="ttl">(.*?)</span>(?:<span class="tsub">(.*?)</span>)?', blok, re.S):
            href = html.unescape(href)
            if href.startswith('http'):
                pad = href
            else:
                pad = os.path.relpath(os.path.normpath(os.path.join(ROOT, cat, urllib.parse.unquote(href))), ROOT).replace(os.sep, '/') + '/'
            item = {'cat': cat, 'groep': g, 'titel': html.unescape(ttl), 'oms': html.unescape(sub or ''), 'pad': pad}
            INFO.setdefault(pad, item)
            GROEPEN.setdefault((cat, g), []).append(pad)


def kaart(r, it, nr=None):
    href = it['pad'] if it['pad'].startswith('http') else r + it['pad']
    ext = ' target="_blank" rel="noopener"' if href.startswith('http') else ''
    n = f'<span class="tnr">{nr}</span>' if nr else '<span class="tnr tpijl">→</span>'
    sub = f'<span class="tsub">{E(it["oms"])}</span>' if it['oms'] else ''
    return (f'<a class="tcard" href="{E(href)}"{ext} data-zoek="{E((it["titel"] + " " + it["oms"]).lower())}">{n}'
            f'<span class="ttx"><span class="ttl">{E(it["titel"])}</span>{sub}</span></a>')


# ---------- kop, titelblok, footer ----------
OUDE_FOOTER = None


def disclaimer_html(s):
    global OUDE_FOOTER
    m = re.search(r'<footer class="notice">.*?</footer>', s, re.S)
    if m and OUDE_FOOTER is None:
        OUDE_FOOTER = m.group(0)
    return OUDE_FOOTER


def footer(r, s):
    oud = disclaimer_html(s) or ''
    body = ''
    m = re.search(r'<p class="lead">.*?</div>\s*</div>\s*</footer>', oud, re.S)
    if m:
        body = re.sub(r'\s*</div>\s*</footer>$', '', m.group(0))
        body = re.sub(r'href="(?:\.\./)*project-jeroen/"', f'href="{r}project-jeroen/"', body)
    cats = ''.join(f'<li><a href="{r}{c}/">{E(n)}</a></li>' for c, n in CATS)
    uit = ''.join(f'<li><a href="{r}{p}">{E(t)}</a></li>' for p, t in
                  [('max-hyp-2027/', 'Max. hyp. 2027'), ('pensioenklif/', 'Pensioenklif'), ('max-hyp-box-1-3/', 'Max. hyp. box 1 & 3'),
                   ('hypotheek/besteedbaar-inkomen-afm/', 'Besteedbaar inkomen'), ('hypotheek/risicoscan-life-events/', 'Risicoscan life events')])
    return f'''<footer class="sitefoot">
  <div class="wrap fgrid">
    <div class="fcol fover">
      <a class="fmerk" href="{r or './'}"><img src="{r}assets/logo.webp" alt="" width="44" height="25"> ADVISEURSTOOLS.NL</a>
      <p>Het tool-lab: experimentele rekentools die financieel advies sneller en scherper maken.</p>
      <p class="fknop"><a class="kbtn kgoud" href="mailto:{MAIL}?subject=Verzoek%20nieuwe%20rekentool">Vraag een tool aan</a> <a class="kbtn kwa" href="{WA}" target="_blank" rel="noopener">WhatsApp</a></p>
    </div>
    <div class="fcol"><h3>Categorieën</h3><ul>{cats}</ul></div>
    <div class="fcol"><h3>Uitgelicht</h3><ul>{uit}</ul></div>
    <div class="fcol"><h3>Contact</h3><ul><li><a href="mailto:{MAIL}">{MAIL}</a></li><li><a href="tel:+31621247257">{TEL}</a></li><li><a href="{r}contact/">Contactpagina</a></li><li><a href="{r}methodiek/">Rekenmethode</a></li><li><a href="{r}api/">API normen</a></li></ul></div>
  </div>
  <div class="wrap fdisc">
    <p class="fkern"><b>Let op:</b> experimentele (AI)tools. Uitkomsten zijn indicatief en geen financieel advies. Gebruik alleen fictieve testgegevens en laat berekeningen controleren door een erkend adviseur.</p>
    <details><summary>Volledige disclaimer</summary><div class="fdetails">{body}</div></details>
    <p class="fcopy">© 2026 Adviseurstools.nl · Het tool-lab</p>
  </div>
</footer>'''


def pagekop(r, titel, sub, kruimel):
    k = ' <span>›</span> '.join(f'<a href="{E(h)}">{E(t)}</a>' for t, h in kruimel) + f' <span>›</span> <b aria-current="page">{E(titel)}</b>'
    sub = f'<p class="pk-sub">{E(sub)}</p>' if sub else ''
    return f'<div class="pagekop"><div class="wrap"><nav class="kruimel" aria-label="Kruimelpad">{k}</nav><h1>{E(titel)}</h1>{sub}</div></div>'


def vervang_kop(s, nieuw):
    s, n = re.subn(r'<div class="hero-title">.*?</div>|<div class="pagekop">.*?</div></div>', nieuw, s, count=1, flags=re.S)
    return s


def brand(s):
    return re.sub(r'(<a class="brand"[^>]*>\s*<img[^>]*>\s*)<span>.*?</span>',
                  r'\1<span><b>ADVISEURSTOOLS.NL</b> <i>het tool-lab</i></span>', s, count=1, flags=re.S)


def gerelateerd(r, pad):
    it = INFO.get(pad)
    if not it:
        return ''
    andere = [p for p in GROEPEN.get((it['cat'], it['groep']), []) if p != pad]
    if len(andere) < 2:   # klein thema: vul aan uit de categorie
        andere += [p for (c, g), ps in GROEPEN.items() if c == it['cat'] for p in ps if p != pad and p not in andere]
    andere = andere[:6]
    if not andere:
        return ''
    kop = it['groep'] if it['groep'] not in ('Tools', 'Nieuw', 'Uitgelicht') else CATNAAM[it['cat']]
    kaarten = ''.join(kaart(r, INFO[p]) for p in andere)
    return (f'<section class="blk gerelateerd"><h2>Meer tools: {E(kop)}</h2><div class="tgrid">{kaarten}</div>'
            f'<p><a class="kmeer" href="{r}{it["cat"]}/">Alle {E(CATNAAM[it["cat"]].lower())}-tools →</a></p></section>\n')


def verwerk_pagina(f):
    d = os.path.dirname(f)
    padrel = os.path.relpath(d, ROOT).replace(os.sep, '/') + '/'
    s = lees(f)
    if 'http-equiv="refresh"' in s or '<header class="top">' not in s:
        return False
    r = rel(d)
    s = brand(s)
    h1 = re.search(r'<div class="hero-title"><h1>(.*?)</h1></div>|<div class="pagekop">.*?<h1>(.*?)</h1>', s, re.S)
    oud_titel = html.unescape((h1.group(1) or h1.group(2)) if h1 else '')
    cat = padrel.split('/')[0]
    it = INFO.get(padrel)
    if cat in CATNAAM and padrel == cat + '/':          # categoriepagina
        n = s.count('class="tcard"')
        kop = pagekop(r, CATNAAM[cat], f'{n} tools · {CAT_OMS[cat]}', [('Home', r or './')])
    elif it:                                              # toolpagina
        kop = pagekop(r, it['titel'], it['oms'], [('Home', r or './'), (CATNAAM[it['cat']], r + it['cat'] + '/')])
    else:                                                 # overige pagina (contact e.d.)
        t = oud_titel.title() if oud_titel.isupper() else oud_titel
        kop = pagekop(r, t, '', [('Home', r or './')])
    s = vervang_kop(s, kop)
    # gerelateerde tools onder de tool
    s = re.sub(r'<section class="blk gerelateerd">.*?</section>\n?', '', s, flags=re.S)
    if it and 'class="tcard"' not in s.split('<main', 1)[1].split('</main>')[0]:
        s = s.replace('</main>', gerelateerd(r, padrel) + '</main>', 1)
    # footer
    s = re.sub(r'<footer class="(?:notice|sitefoot)">.*?</footer>', lambda m: footer(r, s), s, count=1, flags=re.S)
    schrijf(f, s)
    return True


# ---------- homepage ----------
def home():
    f = os.path.join(ROOT, 'index.html')
    s = lees(f)
    disclaimer_html(lees(os.path.join(ROOT, 'contact', 'index.html')))
    r = ''
    s = brand(s)
    tellingen = {c: lees(os.path.join(ROOT, c, 'index.html')).count('class="tcard"') for c, _ in CATS}
    voorbeelden = {}
    for (c, g), ps in GROEPEN.items():
        voorbeelden.setdefault(c, [])
        for p in ps:
            if len(voorbeelden[c]) < 3 and p not in voorbeelden[c] and not p.startswith('http'):
                voorbeelden[c].append(p)
    catkaarten = ''.join(
        f'<a class="catkaart" href="{c}/"><span class="ck-top"><span class="ck-naam">{E(n)}</span><span class="ck-n">{tellingen[c]}</span></span>'
        f'<span class="ck-oms">{E(CAT_OMS[c])}</span><span class="ck-vb">{" · ".join(E(INFO[p]["titel"]) for p in voorbeelden.get(c, []))}</span></a>'
        for c, n in CATS)
    uit = [p for p in ['max-hyp-2027/', 'pensioenklif/', 'max-hyp-box-1-3/'] if p in INFO]
    nieuw = GROEPEN.get(('hypotheek', 'Nieuw'), [])
    nr = 0
    def kaarten(lijst):
        nonlocal nr
        out = ''
        for p in lijst:
            nr += 1
            out += kaart(r, INFO[p], nr)
        return out
    chips = ''.join(f'<button type="button" class="chip" data-q="{E(q)}">{E(t)}</button>' for t, q in
                    [('Maximale hypotheek', 'maximale hypotheek'), ('Maandlasten', 'netto maandlasten'), ('Boeterente', 'boeterente'),
                     ('Pensioen & AOW', 'pensioen'), ('Scheiding', 'scheiding'), ('Overdrachtsbelasting', 'overdrachtsbelasting'),
                     ('Box 3', 'box 3'), ('Krediet', 'krediet')])
    main = f'''<main class="home">
  <section class="hhero"><div class="wrap">
    <h1>Wat wil je berekenen?</h1>
    <p class="hh-sub">{sum(tellingen.values())} rekentools voor hypotheek, krediet, verzekeringen en pensioen — normen 2026.</p>
    <div id="zoekplek"></div>
    <div class="chips">{chips}</div>
  </div></section>

  <section class="wrap hsec"><h2>Kies een categorie</h2><div class="catgrid">{catkaarten}</div></section>

  <section class="wrap hsec"><div class="tgroep" data-groep="Uitgelicht"><h2 class="tgkop">Uitgelicht</h2><div class="tgrid">{kaarten(uit)}</div></div>
    <div class="tgroep"><h2 class="tgkop">Nieuw <span>{len(nieuw)}</span></h2><div class="tgrid">{kaarten(nieuw)}</div></div></section>

  <section class="wrap hsec hbouw">
    <div class="hb-tekst">
      <h2>Mis je een tool? Bouw met ons mee</h2>
      <p>Heb je een idee voor een slimme rekentool, calculator of AI-toepassing? Wij bouwen er kosteloos een werkend prototype van. Wat we vragen: een vrijwillige donatie aan <a href="http://hypotheekbos.nl" target="_blank" rel="noopener">Hypotheekbos.nl</a>, zodat er ergens in Nederland een boom 🌳 de grond in gaat. De donatie is vrijwillig, gaat rechtstreeks naar Hypotheekbos.nl en staat los van (financieel) advies of andere dienstverlening.</p>
      <p>Een tool op je eigen website? We leveren een werkende tool op, ontwikkeld met aandacht voor veiligheid en privacy en afgestemd op jouw eisen. De meeste tools kunnen in elke taal geleverd worden.</p>
    </div>
    <div class="hb-acties">
      <a class="kbtn kgoud" href="mailto:{MAIL}?subject=Verzoek%20nieuwe%20rekentool">✉ Vraag een tool aan</a>
      <a class="kbtn kwa" href="{WA}" target="_blank" rel="noopener">💬 App direct</a>
      <a class="kbtn kwit" href="tel:+31621247257">☎ {TEL}</a>
    </div>
  </section>

  <section class="wrap hsec hlet"><h2>Goed om te weten</h2><div class="letgrid">
    <div><b>Fictieve testgegevens</b><p>Gebruik voor je eigen veiligheid alleen fictieve gegevens. Alles wordt in je browser berekend.</p></div>
    <div><b>Indicatief</b><p>De tools zijn volop in ontwikkeling. Slimme techniek, maar reken het altijd zelf even na.</p></div>
    <div><b>Normen 2026</b><p>Leennormen, NHG en fiscale waarden zijn bijgewerkt naar 2026.</p></div>
    <div class="let27"><b>Nieuw: normen 2027</b><p>In elke hypotheektool kies je normjaar 2026 of 2027; vanaf 1 januari 2027 staat 2027 vanzelf aan. Wat verandert er?</p>
      <ul>
        <li><b>Hogere woonquotes</b>, dus meer leenruimte: bijvoorbeeld € 80.000 inkomen bij 4,17% rente van 26,3% naar 26,8% (ca. + € 6.850).</li>
        <li><b>Alleenstaandenbedrag</b> € 18.000 bij een toetsinkomen boven € 31.000 (2026: € 17.000 boven € 30.000).</li>
        <li><b>NHG-kostengrens</b> € 500.000, met energiebesparende voorzieningen € 530.000; borgtochtprovisie blijft 0,4%.</li>
        <li><b>Ongewijzigd:</b> energielabel- en verduurzamingsbedragen, toetsrente 5% bij rentevast korter dan 10 jaar, NHG-beheernormen 2026.</li>
      </ul>
      <p class="let27bron">Bron: Wijzigingsregeling hypothecair krediet 2027 (Stcrt. 2026, 38415). Uitkomsten blijven indicatief. <a href="{r or './'}max-hyp-2027/">Vergelijk 2026 en 2027 in MAX. HYP. 2027 →</a></p></div>
  </div></section>
</main>'''
    s = re.sub(r'<div class="hero-title".*?</div>\s*', '', s, count=1, flags=re.S)
    s = re.sub(r'<main.*?</main>', main, s, count=1, flags=re.S)
    s = re.sub(r'<footer class="(?:notice|sitefoot)">.*?</footer>', lambda m: footer(r, s), s, count=1, flags=re.S)
    schrijf(f, s)


# eerst de oude disclaimer veiligstellen (uit een willekeurige pagina)
disclaimer_html(lees(os.path.join(ROOT, 'contact', 'index.html')))
if OUDE_FOOTER is None:
    for f in glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True):
        if 'class="sitefoot"' in lees(f):
            m = re.search(r'<details><summary>Volledige disclaimer</summary><div class="fdetails">(.*?)</div></details>', lees(f), re.S)
            if m:
                body = m.group(1)
                while body.count('</div>') > body.count('<div') and body.rstrip().endswith('</div>'):
                    body = body.rstrip()[:-len('</div>')]   # overtollige sluit-tags van eerdere runs opruimen
                OUDE_FOOTER = '<footer class="notice"><div class="wrap"><h2>x</h2>' + body + '</div></footer>'
                break
n = 0
for f in sorted(glob.glob(os.path.join(ROOT, '**', 'index.html'), recursive=True)):
    rp = os.path.relpath(f, ROOT)
    if rp == 'index.html' or rp.startswith(('tools', 'assets', 'scripts')):
        continue
    n += verwerk_pagina(f)
home()
print(n, "pagina's opgemaakt + homepage")
