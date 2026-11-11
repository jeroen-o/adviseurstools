/* Adviseurstools.nl — rekenbibliotheek normen (ATNormen)
 * Bron: data/normen.json. NIET hier waarden aanpassen: wijzig data/normen.json en draai
 *   python3 scripts/maak-normen.py
 * Gebruik in een tool:  ATNormen.maxHypotheek({...}), ATNormen.woonquote(...), enz.
 */
(function (root) {
  'use strict';
  var D = /*@DATA*/null;
  var L = D.leennormen;

  function normjaar(datum) {
    var d = datum ? new Date(datum) : new Date();
    var grens = new Date(D.standaard_normjaar.tot_en_met + 'T23:59:59');
    return d <= grens ? D.standaard_normjaar.jaar : D.standaard_normjaar.daarna;
  }
  function jaarOf(j) { j = String(j || normjaar()); return L.financieringslast[j] ? j : normjaar(); }
  // toetsrente in procenten, afgerond op 3 decimalen
  function rond3(p) { return Math.round((+p || 0) * 1000) / 1000; }
  function kolom(toetsrentePct) {
    var r = rond3(toetsrentePct), g = L.rentekolommen.bovengrenzen;
    for (var i = 0; i < g.length; i++) if (r <= g[i] + 1e-9) return i;
    return g.length;
  }
  function rij(T, inkomen) {
    var inc = T.incomes, i = 0;
    for (var k = 0; k < inc.length; k++) if ((inkomen || 0) >= inc[k]) i = k;
    return T.matrix[i];
  }
  /** Financieringslastpercentage (bv. 26.8) volgens de Trhk-tabel van het normjaar. */
  function woonquote(jaar, inkomen, toetsrentePct, opt) {
    opt = opt || {};
    var t = opt.box3 ? (opt.aow ? '4' : '3') : (opt.aow ? '2' : '1');
    return rij(L.financieringslast[jaarOf(jaar)][t], inkomen)[kolom(toetsrentePct)];
  }
  /** NHG-beheer: situatie 'paar_werk', 'alleen_aow', ... (prefix 'b3_' voor box 3). */
  function beheerquote(situatie, inkomen, toetsrentePct) {
    var T = D.nhg.beheer.tabellen[situatie];
    if (!T) throw new Error('Onbekende beheersituatie: ' + situatie);
    return rij(T, inkomen)[kolom(toetsrentePct)];
  }
  /** Toetsrente: RVP korter dan 10 jaar → minimaal 5%, anders de werkelijke rente. */
  function toetsrente(rentePct, rvpJaren) {
    var t = L.toetsrente;
    return rond3((rvpJaren || 0) < t.rvp_grens_jaren ? Math.max(t.minimum, rentePct) : rentePct);
  }
  /** Contante waarde van € 1 per maand (annuïteit), maandrente = jaarrente / 12. */
  function annuiteitFactor(rentePct, maanden) {
    var r = (rentePct || 0) / 100 / 12, n = maanden || L.toetsrente.toetslooptijd_maanden;
    return r > 0 ? (1 - Math.pow(1 + r, -n)) / r : n;
  }
  function studieschuldFactor(toetsrentePct) { return L.studieschuld_bruteringsfactor[kolom(toetsrentePct)]; }
  /** Alleenstaandenbedrag (buiten de toetslast). */
  function alleenstaandenbedrag(jaar, toetsinkomen, aowTabel, aantalAanvragers) {
    if ((aantalAanvragers || 1) > 1) return 0;
    var a = L.alleenstaandenbedrag[jaarOf(jaar)];
    return toetsinkomen > (aowTabel ? a.grens_aow : a.grens) ? a.bedrag : 0;
  }
  var LABELCODE = { G: 'EFG', F: 'EFG', E: 'EFG', D: 'CD', C: 'CD', B: 'AB', A: 'AB', 'A+': 'A+/A++', 'A++': 'A+/A++', 'A+++': 'A+++', 'A++++': 'A++++', 'A++++G': 'A++++ garantie', GEEN: 'geen' };
  function labelCode(label) { label = String(label || '').toUpperCase().replace(/\s/g, ''); return LABELCODE[label] || (L.energielabel_aankoop[label] !== undefined ? label : 'EFG'); }
  function labelAankoop(label) { return L.energielabel_aankoop[labelCode(label)] || 0; }
  function energiebesparend(label) { return L.energiebesparende_voorzieningen[labelCode(label)] || 0; }
  function nhg(jaar) { return D.nhg[jaarOf(jaar)]; }

  /**
   * Maximale hypotheek volgens de leennormen.
   * opt: {jaar, toetsinkomen, rente, rvp, aow, box3Aandeel (0..1), studieschuldMnd, kredietLimiet,
   *       erfpachtMnd, overigeLastenMnd, alimentatieBetaaldJaar, label, verduurzaming, aanvragers}
   * Betaalde partneralimentatie gaat van het toetsinkomen af (NHG V&N C.7.14.2).
   * Volledig box 3: tabel 3/4 en verplichtingen volledig van die ruimte af; gemengd: box 3-deel gebruteerd met q1/q3.
   * Label-, verduurzamings- en alleenstaandenbedrag blijven buiten de toetslast.
   */
  function maxHypotheek(o) {
    var jaar = jaarOf(o.jaar), tr = toetsrente(o.rente, o.rvp == null ? 30 : o.rvp);
    var ink = Math.max(0, (o.toetsinkomen || 0) - (o.alimentatieBetaaldJaar || 0));
    var q1 = woonquote(jaar, ink, tr, { aow: o.aow }), q3 = woonquote(jaar, ink, tr, { aow: o.aow, box3: true });
    var s3 = Math.min(1, Math.max(0, o.box3Aandeel || 0));
    // Volledig box 3 (geen aftrekbare rente): tabel 3/4, verplichtingen volledig van die ruimte af (niet gebruteerd).
    // Gemengd: tabel 1/2, het box 3-deel van de last gebruteerd met q1/q3.
    var vol3 = s3 >= 1;
    var maxLast = ink * (vol3 ? q3 : q1) / 100 / 12;
    var fBr = vol3 ? 1 : studieschuldFactor(tr);
    var verpl = (o.studieschuldMnd || 0) * fBr + (o.kredietLimiet || 0) * L.krediet_maandlast_pct_limiet / 100
      + (o.erfpachtMnd || 0) + (o.overigeLastenMnd || 0) * fBr;
    var beschikbaar = Math.max(0, maxLast - verpl);
    var verh = q3 > 0 ? q1 / q3 : 1, factorLast = vol3 ? 1 : (1 - s3) + s3 * verh;
    var opInkomen = beschikbaar * annuiteitFactor(tr) / factorLast;
    var lab = labelAankoop(o.label), verd = Math.min(o.verduurzaming || 0, o.verduurzaming ? energiebesparend(o.label) : 0);
    var alleen = alleenstaandenbedrag(jaar, ink, o.aow, o.aanvragers || 1);
    return { jaar: jaar, toetsrente: tr, kolom: L.rentekolommen.labels[kolom(tr)], woonquote: q1, woonquoteBox3: q3,
      toetsinkomen: ink, maxMaandlast: maxLast, verplichtingenMnd: verpl, opInkomen: opInkomen,
      labelBedrag: lab, verduurzamingBedrag: verd, alleenstaandenbedrag: alleen,
      totaal: opInkomen + lab + verd + alleen };
  }

  /**
   * Maximale hypotheek volgens de NHG-beheercriteria (V&N D.6) — alleen voor een bestaande lening met NHG.
   * opt: {inkomen, rente (huidige gewogen rente, %), aanvragers (1|2), aow (alle aanvragers AOW),
   *       zonderWerk, box3Aandeel (0..1), verplichtingenMnd (werkelijk, niet gebruteerd),
   *       lastPerEuro (werkelijke maandlast per € 1 hoofdsom; leeg = 50% aflossingsvrij + 50% annuïtair 30 jaar)}
   * Pensioen telt alleen als de AOW binnen 36 maanden ligt: reken dan ook met het inkomen vanaf AOW en aow:true
   * en neem de laagste uitkomst. Geen vrijgestelde bedragen; vermogenscorrectie (D.6.5) niet inbegrepen.
   */
  function maxHypotheekBeheer(o) {
    var tr = rond3(o.rente), r = tr / 100 / 12, R = D.nhg.beheer.regels.aanname_zonder_leningdelen;
    var sit = ((o.aanvragers || 1) > 1 ? 'paar' : 'alleen') + '_' + (o.aow ? 'aow' : (o.zonderWerk ? 'zonderwerk' : 'werk'));
    var s3 = Math.min(1, Math.max(0, o.box3Aandeel || 0));
    var q1 = beheerquote(sit, o.inkomen, tr), q3 = beheerquote('b3_' + sit, o.inkomen, tr);
    var q = s3 >= 1 ? q3 : q1, maxLast = (o.inkomen || 0) * q / 100 / 12;
    var lpe = o.lastPerEuro || (R.aflossingsvrij_aandeel * r + (1 - R.aflossingsvrij_aandeel) / annuiteitFactor(tr, R.annuitair_looptijd_maanden));
    var factorLast = s3 >= 1 ? 1 : (1 - s3) + s3 * (q3 > 0 ? q1 / q3 : 1);
    var beschikbaar = Math.max(0, maxLast - (o.verplichtingenMnd || 0));
    return { tabel: sit, toetsrente: tr, kolom: L.rentekolommen.labels[kolom(tr)], woonquote: q, woonquoteBox3: q3,
      maxMaandlast: maxLast, lastPerEuro: lpe, aanname5050: !o.lastPerEuro, totaal: beschikbaar / (lpe * factorLast) };
  }

  // ── AOW ──
  function aowDatum(geboortedatum) {
    var g = new Date(geboortedatum); if (isNaN(g)) return null;
    var r = D.aow.regels, extra = g <= new Date(r[0].geboren_tm + 'T23:59:59') ? r[0] : r[1];
    return new Date(g.getFullYear() + extra.leeftijd_jaren, g.getMonth() + extra.maanden, g.getDate());
  }
  // ── Fiscaal ──
  function fisc(jaar) { var f = D.fiscaal[String(jaar || '2026')] || D.fiscaal['2026']; return f; }
  function box1Belasting(inkomen, aow, jaar) {
    var b = fisc(jaar).box1, s = b.schijven, t = b.tarieven.slice(); if (aow) t[0] = b.tarief_schijf1_aow;
    var bel = 0, ondergrens = 0;
    for (var i = 0; i < t.length; i++) { var bov = i < s.length ? s[i] : Infinity; if (inkomen > ondergrens) bel += (Math.min(inkomen, bov) - ondergrens) * t[i] / 100; ondergrens = bov; }
    return bel;
  }
  function aftrekTarief(inkomen, aow, jaar) {
    var b = fisc(jaar).box1; if (inkomen > b.schijven[0]) return b.max_aftrektarief; return aow ? b.tarief_schijf1_aow : b.tarieven[0];
  }
  function eigenwoningforfait(woz, jaar) {
    var e = fisc(jaar).eigenwoningforfait;
    if (woz > e.villataks_grens) return e.villataks_basis + (woz - e.villataks_grens) * e.villataks_pct / 100;
    for (var i = 0; i < e.staffel.length; i++) if (woz <= e.staffel[i][0]) return woz * e.staffel[i][1] / 100;
    return 0;
  }
  function overdrachtsbelasting(waarde, opt, jaar) {
    opt = opt || {}; var o = fisc(jaar).overdrachtsbelasting;
    if (opt.soort === 'niet-woning') return waarde * o.niet_woning_pct / 100;
    if (!opt.hoofdverblijf) return waarde * o.overig_woning_pct / 100;
    if (opt.leeftijd >= o.starter_leeftijd[0] && opt.leeftijd <= o.starter_leeftijd[1] && !opt.eerderVrijstelling && waarde <= o.starter_max_woningwaarde) return 0;
    return waarde * o.woning_pct / 100;
  }

  root.ATNormen = {
    data: D, versie: D.versie, normjaar: normjaar, kolom: kolom, kolomLabel: function (tr) { return L.rentekolommen.labels[kolom(tr)]; },
    woonquote: woonquote, beheerquote: beheerquote, toetsrente: toetsrente, annuiteitFactor: annuiteitFactor,
    studieschuldFactor: studieschuldFactor, alleenstaandenbedrag: alleenstaandenbedrag, labelAankoop: labelAankoop,
    energiebesparend: energiebesparend, nhg: nhg, maxHypotheek: maxHypotheek, maxHypotheekBeheer: maxHypotheekBeheer, aowDatum: aowDatum,
    box1Belasting: box1Belasting, aftrekTarief: aftrekTarief, eigenwoningforfait: eigenwoningforfait,
    overdrachtsbelasting: overdrachtsbelasting, fiscaal: fisc
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.ATNormen;
})(typeof window !== 'undefined' ? window : globalThis);
