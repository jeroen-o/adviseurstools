#!/usr/bin/env node
// Versleutel of ontsleutel een tool voor een met wachtwoord beveiligde pagina.
// Het wachtwoord wordt NIET opgeslagen; geef het mee via de omgevingsvariabele WACHTWOORD.
//
//   Versleutelen:  WACHTWOORD='...' node scripts/beveilig-pagina.js encrypt <tool.html> <pagina/index.html>
//                  → zet de versleutelde inhoud in de <script id="versleuteld"> van de pagina.
//   Ontsleutelen:  WACHTWOORD='...' node scripts/beveilig-pagina.js decrypt <pagina/index.html> <uit.html>
//                  → haalt de leesbare tool terug om te bewerken (niet committen!).
//   Normen:        WACHTWOORD='...' node scripts/beveilig-pagina.js normen <pagina/index.html> <assets/normen.js>
//                  → ontsleutelt alleen in het geheugen, zet de normenbibliotheek in <script id="at-normen">
//                    en versleutelt opnieuw (gebruikt door maak-normen.py; er komt geen leesbare versie op schijf).
//
// Methode: PBKDF2-SHA256 (600.000 iteraties) → AES-256-GCM, compatibel met WebCrypto in de browser.
const fs = require('fs');
const { webcrypto } = require('crypto');
const subtle = webcrypto.subtle;
const ITER = 600000;

async function sleutel(ww, salt) {
  const basis = await subtle.importKey('raw', new TextEncoder().encode(ww), 'PBKDF2', false, ['deriveKey']);
  return subtle.deriveKey({ name: 'PBKDF2', salt, iterations: ITER, hash: 'SHA-256' }, basis,
    { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}
const b64 = (u8) => Buffer.from(u8).toString('base64');
const RE = /(<script type="application\/json" id="versleuteld">)([\s\S]*?)(<\/script>)/;

(async () => {
  const [mode, a, b] = process.argv.slice(2);
  const ww = process.env.WACHTWOORD;
  if (!ww || !mode || !a || !b) { console.error('Gebruik: zie kop van dit bestand.'); process.exit(1); }
  if (mode === 'encrypt') {
    const salt = webcrypto.getRandomValues(new Uint8Array(16));
    const iv = webcrypto.getRandomValues(new Uint8Array(12));
    const ct = new Uint8Array(await subtle.encrypt({ name: 'AES-GCM', iv }, await sleutel(ww, salt),
      new TextEncoder().encode(fs.readFileSync(a, 'utf8'))));
    const payload = JSON.stringify({ v: 1, iter: ITER, salt: b64(salt), iv: b64(iv), data: b64(ct) });
    const page = fs.readFileSync(b, 'utf8');
    if (!RE.test(page)) throw new Error('Pagina mist <script type="application/json" id="versleuteld">');
    fs.writeFileSync(b, page.replace(RE, (m, p1, p2, p3) => p1 + payload + p3));
    console.log('Versleuteld:', a, '→', b);
  } else if (mode === 'decrypt') {
    const m = fs.readFileSync(a, 'utf8').match(RE);
    const p = JSON.parse(m[2]);
    const pt = await subtle.decrypt({ name: 'AES-GCM', iv: Buffer.from(p.iv, 'base64') },
      await sleutel(ww, Buffer.from(p.salt, 'base64')), Buffer.from(p.data, 'base64'));
    fs.writeFileSync(b, Buffer.from(pt));
    console.log('Ontsleuteld:', a, '→', b);
  } else if (mode === 'normen') {
    const page = fs.readFileSync(a, 'utf8');
    const m = page.match(RE);
    if (!m) throw new Error('Pagina mist versleuteld blok');
    const p = JSON.parse(m[2]);
    const pt = Buffer.from(await subtle.decrypt({ name: 'AES-GCM', iv: Buffer.from(p.iv, 'base64') },
      await sleutel(ww, Buffer.from(p.salt, 'base64')), Buffer.from(p.data, 'base64'))).toString('utf8');
    const BLOK = /(<script id="at-normen">)([\s\S]*?)(<\/script>)/;
    if (!BLOK.test(pt)) { console.log('Geen at-normen-blok:', a); return; }
    const lib = fs.readFileSync(b, 'utf8');
    const nieuw = pt.replace(BLOK, (x, p1, p2, p3) => p1 + '\n' + lib + '\n' + p3);
    if (nieuw === pt) { console.log('Normen al actueel:', a); return; }
    const salt = webcrypto.getRandomValues(new Uint8Array(16));
    const iv = webcrypto.getRandomValues(new Uint8Array(12));
    const ct = new Uint8Array(await subtle.encrypt({ name: 'AES-GCM', iv }, await sleutel(ww, salt), new TextEncoder().encode(nieuw)));
    const payload = JSON.stringify({ v: 1, iter: ITER, salt: b64(salt), iv: b64(iv), data: b64(ct) });
    fs.writeFileSync(a, page.replace(RE, (x, p1, p2, p3) => p1 + payload + p3));
    console.log('Normen bijgewerkt (versleuteld):', a);
  } else { console.error('Onbekende modus'); process.exit(1); }
})().catch((e) => { console.error('Fout:', e.message); process.exit(1); });
