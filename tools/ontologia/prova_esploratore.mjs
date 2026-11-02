// Headless test of ontologia/esplora.html, opened from file:// in Chromium.
//
// usage: node tools/ontologia/prova_esploratore.mjs --pw <dir with node_modules/playwright-core> [--foto <dir>]
//
// playwright-core is not a dependency of the repository: install it anywhere
// (npm install playwright-core@1.64.0, which drives the cached chromium 1248) and pass
// that folder with --pw. Checks the load time, the console, the reader and the verse
// panel (Gv 3,16 -> note -> a margin reference -> back), the search with and without
// accents, the graph, the matrix, the dark theme, the keyboard and a 390px viewport; the
// Dizionario di Teologia Biblica: the panel section, the ◊ marker and its heat, an entry
// (#voce) with its paragraph highlighted, the index (#dizionario), the search, the entry
// cards of the tree, the overview; the front matter and the appendices: the acrostic letters in
// the margin, the panel sections (index of notes, pastoral themes, chronology), #indice-note,
// #temi, #cronologia (sections, dynasties), #introduzione-generale (texts, canon, abbreviations,
// woodcuts), the search and the overview tiles; the quotations in italic (session F4: Gen 1,3, Dt 5 across
// verses, Dt 20,3 nested, Sir 16,22 and Am 7,17 unbalanced, Sal 2,3 poetry, notes, introductions, front matter,
// appendices, the «Discorsi» switch and the search in the quoted words).
// With --foto, screenshots are written there. Exit status 1 if any check fails.
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { mkdirSync } from 'node:fs';

const arg = k => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const PW = arg('--pw') || process.env.PW_DIR;
if (!PW) { console.error('usage: prova_esploratore.mjs --pw <dir> [--foto <dir>]'); process.exit(2); }
const { chromium } = createRequire(join(resolve(PW), 'package.json'))('playwright-core');
const C = resolve(dirname(fileURLToPath(import.meta.url)), '..', '..');
const URL = pathToFileURL(join(C, 'ontologia', 'esplora.html')).href;
const FOTO = arg('--foto');
if (FOTO) mkdirSync(FOTO, { recursive: true });

const esiti = [];
const metriche = {};
function verifica(nome, ok, dettaglio = '') {
  esiti.push([nome, !!ok, dettaglio]);
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${nome}${dettaglio ? ' — ' + dettaglio : ''}`);
}
async function foto(pagina, nome) {
  if (FOTO) await pagina.screenshot({ path: join(FOTO, nome + '.png') });
}
async function apri(contesto, hash = '') {
  const p = await contesto.newPage();
  const errori = [];
  p.on('console', m => { if (m.type() === 'error' || m.type() === 'warning') errori.push(m.type() + ': ' + m.text()); });
  p.on('pageerror', e => errori.push('pageerror: ' + e.message));
  p.on('request', r => { if (!r.url().startsWith('file:') && !r.url().startsWith('data:')) errori.push('network: ' + r.url()); });
  const t = Date.now();
  await p.goto(URL + hash);
  await p.waitForFunction(() => window.__esploratore, null, { timeout: 30000 });
  const tempo = Date.now() - t;
  return { p, errori, tempo, interno: await p.evaluate(() => window.__esploratore) };
}
const hash = p => p.evaluate(() => decodeURIComponent(location.hash));

const browser = await chromium.launch();
try {
  // ------------------------------------------------ desktop
  const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, colorScheme: 'light' });
  const { p, errori, tempo, interno } = await apri(ctx);
  metriche.caricamento_ms = tempo;
  metriche.interno = interno;
  verifica('prima resa in meno di 1 s', tempo < 1000, `${tempo} ms (dati ${interno.dati} ms, indici ${interno.indici} ms)`);
  const numeri = await p.$$eval('.numeri span', xs => xs.map(x => x.textContent.trim()));
  metriche.numeri_indice = numeri;
  verifica('indice dei libri', (await p.$$('.libro')).length === 74, numeri.join(', '));
  await foto(p, '01-indice');

  // reference box -> Gv 3,16
  await p.fill('#q', 'Gv 3,16');
  await p.press('#q', 'Enter');
  await p.waitForSelector('#pannello:not([hidden]) .pan-testa');
  verifica('Gv 3,16 dal riquadro', (await hash(p)) === '#John.3.16' && await p.$('#v' + (await p.evaluate(() => S.vix.get('John.3.16'))) + '.sel'), await hash(p));
  const pannello = await p.$eval('#pannello', x => ({
    rif: x.querySelector('.rif').textContent, note: x.querySelectorAll('.nota').length,
    aperte: x.querySelectorAll('.nota[open]').length, chips: x.querySelectorAll('.sez:nth-of-type(2) .chip').length,
    contatori: x.querySelector('.contatori').textContent.replace(/\s+/g, ' ').trim(),
  }));
  metriche.pannello_gv_3_16 = pannello;
  verifica('pannello di Gv 3,16', pannello.rif === 'Gv 3,16' && pannello.note >= 1 && pannello.chips >= 3, JSON.stringify(pannello));
  await foto(p, '02-gv-3-16');

  // open a note: the superscript call in the reader, then a collapsed note of the panel
  await p.click('.v.sel .nc');
  await p.waitForSelector('.nota.lampo[open]');
  verifica('richiamo di nota apre la nota', true);
  const chiusa = await p.$('.nota:not([open]) > summary');
  if (chiusa) {
    await chiusa.click();
    verifica('nota chiusa si apre', await chiusa.evaluate(s => s.parentNode.open));
  }
  await foto(p, '03-nota');

  // hover preview of a target, then follow it
  const chip = await p.$('.sez:nth-of-type(2) .chip[data-r]');
  await chip.hover();
  await p.waitForSelector('#anteprima:not([hidden])');
  const ant = await p.$eval('#anteprima', x => x.textContent.slice(0, 80));
  verifica('anteprima al passaggio', ant.length > 10, ant);
  await foto(p, '04-anteprima');
  const meta = await chip.getAttribute('href');
  await chip.click();
  await p.waitForFunction(h => decodeURIComponent(location.hash) === h, meta);
  await p.waitForSelector('#pannello:not([hidden])');
  verifica('segue un rimando', (await hash(p)) === meta, meta);
  await p.goBack();
  await p.waitForFunction(() => location.hash === '#John.3.16');
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Gv 3,16');
  verifica('indietro torna a Gv 3,16', true);

  // F7: a "+" chip opens the verse of its key note; F15: a one-run chip opens the whole passage
  await p.evaluate(() => { location.hash = '#John.2.20'; });
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Gv 2,20');
  const piu = await p.$eval('#pannello .chip[data-nota]', a => a.getAttribute('href'));
  verifica('chip «+» porta al versetto della nota chiave (F7)', piu === '#Matt.12.38', piu);
  await p.click('#pannello .chip[data-nota]');
  await p.waitForSelector('#pannello .nota.chiave[open]');
  verifica('… e la nota chiave è aperta', true);
  await p.evaluate(() => { location.hash = '#John.3.16'; });
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Gv 3,16');
  const intero = await p.$$eval('#pannello .chip', xs => xs.map(a => [a.textContent.trim(), a.getAttribute('href')]).find(x => /^Gen 22\b/.test(x[0])));
  verifica('chip di un capitolo intero apre tutto il passo (F15)', intero && intero[1] === '#Gen.22.1-24', JSON.stringify(intero));
  const frasi = await p.$$eval('#pannello .frase', xs => xs.map(x => x.textContent));
  verifica('frasi di contesto da inizio parola (F15)', frasi.every(f => !/^…\S*[a-zà-ù]\S*\s/.test(f) || /^…[A-ZÀ-Ù«(]|^…\S+\s/.test(f)), frasi[0]?.slice(0, 50));

  // ------------------------------------------------ the Dizionario di Teologia Biblica
  const Zm = await p.evaluate(() => ({ top: D.diz.meta.top.map(x => [V.id[x[0]], x[1], x[2]]), stretti: D.diz.meta.top_stretti.map(x => [V.id[x[0]], x[1]]), voci: D.diz.voci.length, rinvii: D.diz.meta.rinvii, pct: D.diz.meta.pct }));
  // the panel of the verse most cited by the dictionary: one entry per voce, counted in the header
  const [vtop, ntop, vocitop] = Zm.top[0];
  await p.evaluate(h => { location.hash = '#' + h; }, vtop);
  await p.waitForSelector('#pannello:not([hidden]) .sez.diz');
  const pdiz = await p.$eval('#pannello', x => ({
    n: +x.querySelector('.sez.diz > h3 .n').textContent, voci: x.querySelectorAll('.sez.diz .dvoce').length,
    contatori: x.querySelector('.contatori').textContent.replace(/\s+/g, ' '), segni: x.querySelectorAll('.sez.diz .frase mark').length,
    citazioni: [...x.querySelectorAll('.sez.diz .dvoce h4 .n')].reduce((s, y) => s + +y.textContent, 0),
  }));
  metriche.pannello_dizionario = Object.assign({ verso: vtop }, pdiz);
  verifica(`pannello: «Nel Dizionario» per ${vtop}`, pdiz.n === vocitop && pdiz.voci === vocitop && pdiz.citazioni === ntop && pdiz.segni >= vocitop && pdiz.contatori.includes(`${vocitop} voci del Dizionario`), JSON.stringify(pdiz));
  await p.evaluate(() => document.querySelector('#pannello .sez.diz').scrollIntoView());
  await foto(p, '26-diz-pannello');
  // Gen 4,5 is in ABELE «Gen 4, 4 s»: the flag, then the click opens the entry at that paragraph
  await p.evaluate(() => { location.hash = '#Gen.4.5'; });
  await p.waitForSelector('#pannello:not([hidden]) .sez.diz');
  const abele = await p.$eval('#pannello .dvoce:has(a[href="#voce/abele"])', x => ({ fl: [...x.querySelectorAll('.fl')].map(f => f.textContent), href: x.querySelector('.dsez').getAttribute('href') }));
  verifica('pannello: ABELE cita Gen 4,4 s (segno «s»)', abele.fl.includes('s') && abele.href === '#voce/abele/1?v=Gen.4.5', JSON.stringify(abele));
  await p.click('#pannello .dvoce:has(a[href="#voce/abele"]) .dsez');
  await p.waitForSelector('.voce-testo .dpar.sel');
  const voce = await p.evaluate(() => {
    const sel = document.querySelector('.dpar.sel'), r = sel.getBoundingClientRect();
    return { h1: document.querySelector('.voce-pagina h1').textContent, sel: sel.id, inVista: r.top >= 0 && r.top < innerHeight,
      cd: document.querySelectorAll('.voce-testo a.cd[href]').length, cdSel: [...document.querySelectorAll('a.cd.sel')].map(a => a.textContent),
      vl: document.querySelectorAll('.voce-testo a.vl').length, firma: document.querySelector('.firma')?.textContent,
      rinvii: document.querySelectorAll('.rinvii li').length, tab: document.querySelector('.schede a.attiva')?.dataset.vista };
  });
  metriche.voce_abele = voce;
  verifica('#voce/abele/1: paragrafo evidenziato e in vista, citazione segnata', voce.h1 === 'Abele' && voce.sel === 'p1' && voce.inVista && voce.cdSel.includes('Gen 4, 4 s') && voce.tab === 'dizionario', JSON.stringify(voce));
  verifica('voce: citazioni come link, *parole, firma, vedi anche', voce.cd >= 10 && voce.vl >= 3 && voce.firma === 'P. GRELOT' && voce.rinvii === 6, JSON.stringify(voce));
  await p.hover('.voce-testo a.cd[href]');
  await p.waitForSelector('#anteprima:not([hidden])');
  verifica('voce: anteprima di una citazione al passaggio', /\S/.test(await p.$eval('#anteprima', x => x.textContent)), await p.$eval('#anteprima .ap-rif', x => x.textContent));
  await foto(p, '27-voce');
  await p.click('.voce-testo a.vl');
  await p.waitForFunction(() => /^#voce\/(?!abele)/.test(location.hash));
  verifica('voce: una *parola apre l’altra voce', true, await hash(p));
  await p.evaluate(() => { location.hash = '#voce/abba'; });
  await p.waitForSelector('.rinvio-nota');
  verifica('voce di rinvio: le sue voci', (await p.$$('.rinvii li a.vl')).length === 11);
  await p.evaluate(() => { location.hash = '#voce/xyz'; });
  await p.waitForFunction(() => /non trovata/.test(document.querySelector('#vista h1')?.textContent || ''));
  verifica('#voce/xyz: voce non trovata', true);
  await p.evaluate(() => { location.hash = '#voce/dio/5'; });
  await p.waitForSelector('.dpar.sel');
  verifica('voce lunga: indice delle sezioni accanto al testo', await p.evaluate(() => getComputedStyle(document.querySelector('.voce-indice')).position === 'sticky' && document.querySelectorAll('.voce-indice li').length > 15));
  await foto(p, '28-voce-dio');
  // the index of the entries
  await p.click('.schede a[data-vista="dizionario"]');
  await p.waitForSelector('.dvl');
  const indiceDiz = await p.evaluate(() => ({ tutte: document.querySelectorAll('.dvl').length, rinvii: document.querySelectorAll('.dvl.rinvio').length, lettere: document.querySelectorAll('.lettera').length }));
  verifica('#dizionario: tutte le voci per lettera, i rinvii distinti', (await hash(p)) === '#dizionario' && indiceDiz.tutte === Zm.voci && indiceDiz.rinvii === Zm.rinvii && indiceDiz.lettere > 15, JSON.stringify(indiceDiz));
  await foto(p, '29-dizionario');
  await p.fill('#dq', 'agnello');
  const filtrate = await p.$$eval('.dvl:not([hidden])', xs => xs.map(x => x.textContent.trim()));
  verifica('#dizionario: il filtro', filtrate.some(t => t.startsWith('Agnello di Dio')) && filtrate.length < 5, filtrate.join(' | '));
  // search: the entries are a third group, accents ignored
  const cercaDiz = async q => {
    await p.evaluate(q => { location.hash = '#cerca?q=' + encodeURIComponent(q) + '&in=dizionario'; }, q);
    await p.waitForFunction(q => document.querySelector('#rq')?.value === q && document.querySelector('#esito')?.textContent, q);
    return p.$eval('#esito', x => x.textContent.replace(/ \(\d+ ms\)/, ''));
  };
  const jahve = [await cercaDiz('Jahvè'), await cercaDiz('jahve')];
  verifica('cerca nel Dizionario, senza accenti', jahve[0] === jahve[1] && /[1-9]\d* paragrafi/.test(jahve[0]), jahve[0]);
  await p.evaluate(() => { location.hash = '#cerca?q=agnello di dio'; });
  await p.waitForSelector('.bdiz');
  const gruppo = await p.$eval('.bdiz', x => ({ chip: [...x.querySelectorAll('.dchips .chip')].map(c => c.textContent), righe: x.querySelectorAll('.r.rd').length }));
  verifica('cerca: le voci come terzo gruppo', gruppo.chip.some(t => t.startsWith('Agnello di Dio')) && gruppo.righe > 0 && (await p.$$('.risultati .blocco')).length > 1, JSON.stringify(gruppo));
  await foto(p, '30-cerca-diz');
  // the reader: ◊ in the margin, its tooltip and label, the heat of the dictionary
  await p.evaluate(() => { location.hash = '#Isa.53'; });
  await p.waitForSelector('.testo .v');
  const md = await p.evaluate(() => ({ n: document.querySelectorAll('.testo .md').length, title: document.querySelector('.testo .md')?.title, aria: document.querySelector('#v' + S.vix.get('Isa.53.12')).getAttribute('aria-label') }));
  verifica('lettore: ◊ sui versetti citati dal Dizionario', md.n >= 10 && /Dizionario/.test(md.title) && /voci del Dizionario/.test(md.aria), JSON.stringify(md));
  await p.click('#calore');
  await p.click('.fonte-calore [data-fonte="diz"]');
  const caldo = await p.evaluate(() => [document.body.className, getComputedStyle(document.querySelector('.v.d5, .v.d4')).backgroundColor, getComputedStyle(document.querySelector('.lc-diz')).display]);
  verifica('calore del Dizionario', /calore-diz/.test(caldo[0]) && caldo[1] !== 'rgba(0, 0, 0, 0)' && caldo[2] !== 'none', caldo.join(' · '));
  await foto(p, '31-calore-diz');
  await p.keyboard.press('d');
  verifica('d: torna ai rimandi della BJ', !(await p.evaluate(() => document.body.classList.contains('calore-diz'))));
  await p.click('#calore');
  // the tree: a group of entries on the card of a verse; an entry card grows the passages it cites
  await p.evaluate(h => { location.hash = '#grafo/' + h; }, vtop);
  await p.waitForSelector('.carta.voce');
  const gd = await p.evaluate(() => {
    const c = document.querySelector('.carta.voce');
    return { gruppo: [...document.querySelectorAll('.ramo-gruppo span')].map(x => x.textContent).find(t => /Nel Dizionario/.test(t)),
      carte: document.querySelectorAll('.carta.voce').length, href: c.querySelector('.carta-rif').getAttribute('href'), mark: !!c.querySelector('.carta-testo mark'),
      fondo: getComputedStyle(c.querySelector('svg.contorno .fondo')).fill, tinta: getComputedStyle(document.documentElement).getPropertyValue('--biglietto-diz').trim(),
      filtro: !!document.querySelector('.grafo-lato input[data-rel="diz"]') };
  });
  verifica('albero: gruppo «◊ Nel Dizionario» con schede di voce', gd.gruppo === '◊ Nel Dizionario' && gd.carte === 8 && /^#voce\/[^/]+\/\d+\?v=/.test(gd.href) && gd.mark && gd.filtro, JSON.stringify(gd));
  const prima2 = await p.$$eval('.carta', xs => xs.length);
  await p.evaluate(() => document.querySelector('.carta.voce .cresci').click());
  const dopo2 = await p.evaluate(() => ({ carte: document.querySelectorAll('.carta').length, gruppo: [...document.querySelectorAll('.ramo-gruppo span')].some(x => x.textContent === '◊ La voce cita') }));
  verifica('albero: ▸ su una voce apre i passi che cita (al più 4)', dopo2.gruppo && dopo2.carte > prima2 && dopo2.carte <= prima2 + 4, `${prima2} -> ${dopo2.carte} schede`);
  await p.evaluate(() => { const n = S.albNodi.find(x => x.voce !== undefined && x.aperta); S.av.z = 0.85; S.av.x = 300 - n.x * S.av.z; S.av.y = 260 - n.y * S.av.z; applica(); });
  await foto(p, '32-grafo-diz');
  await p.evaluate(h => { location.hash = '#grafo/' + h + '?f=diz'; }, vtop);
  await p.waitForSelector('#ginfo b');
  verifica('albero: filtro «diz» nell’indirizzo', await p.$$eval('.ramo-gruppo span', xs => xs.map(x => x.textContent).join()) === '◊ Nel Dizionario');
  await p.evaluate(() => document.querySelector('.carta.voce .carta-rif').click());
  await p.waitForSelector('.voce-testo .dpar.sel');
  verifica('albero: il nome di una voce apre la voce al paragrafo', /^#voce\//.test(await hash(p)), await hash(p));
  // the overview: tiles and the 20 verses most cited, both rankings equal to dufour.json
  await p.evaluate(() => { location.hash = '#panoramica'; });
  await p.waitForSelector('#dtop tr');
  const righeTop = () => p.$$eval('#dtop tr', xs => xs.map(x => [x.querySelector('.rif').textContent, +x.querySelector('.cnt div').textContent]));
  const rif = id => p.evaluate(id => rif(S.vix.get(id)), id);
  const t1 = await righeTop();
  const atteso1 = await Promise.all(Zm.top.map(async ([id, n]) => [await rif(id), n]));
  await p.click('#dtop-scelta [data-top="stretti"]');
  const t2 = await righeTop();
  const atteso2 = await Promise.all(Zm.stretti.map(async ([id, n]) => [await rif(id), n]));
  const tessereDiz = await p.$$eval('.tessere-diz .tessera', xs => xs.map(x => x.querySelector('b').textContent + ' ' + x.querySelector('span').textContent));
  metriche.tessere_dizionario = tessereDiz;
  verifica('panoramica: tessere del Dizionario', tessereDiz.length === 4 && tessereDiz.join().includes(String(Zm.pct).replace('.', ',') + '%'), tessereDiz.join(' · '));
  verifica('panoramica: i 20 più citati dal Dizionario (come dufour.json)', JSON.stringify(t1) === JSON.stringify(atteso1), t1.slice(0, 3).join(' · '));
  verifica('panoramica: … e con le sole citazioni brevi', JSON.stringify(t2) === JSON.stringify(atteso2), t2.slice(0, 3).join(' · '));
  await p.evaluate(() => document.querySelector('.diz-h2').scrollIntoView());
  await foto(p, '33-panoramica-diz');
  // ------------------------------------------------ audit 2 of the dictionary
  const vai_ = async (h, sel) => { await p.evaluate(h => { location.hash = h; }, h); if (sel) await p.waitForSelector(sel); };
  const vociPannello = async id => { await vai_('#' + id, '#pannello:not([hidden]) .sez.diz'); return p.$$eval('#pannello .dvoce h4 a', xs => xs.map(x => x.getAttribute('href'))); };
  const es14 = await vociPannello('Exod.14.10'), gv1030 = await vociPannello('John.10.30'), gv316 = await vociPannello('John.3.16');
  verifica('dati: dopo «= Es 3, 14» FEDE cita Gv 10,30, non Es 14,10 (inciso)', !es14.includes('#voce/fede') && gv1030.includes('#voce/fede'), `Es 14,10: ${es14.length} voci; Gv 10,30: ${gv1030.join(' ')}`);
  verifica('dati: Gv 3,16 nel paragrafo di FEDE senza sigla (citazione ritrovata)', gv316.includes('#voce/fede'), gv316.length + ' voci');
  const sir = await vociPannello('Sir.36.6');
  verifica('dati: «Rinnova i prodigi» (Eccli 36, 5) è Sir 36,6 (vecchia numerazione)', sir.includes('#voce/miracolo'), sir.join(' '));
  // search: every row marked (a stale lastIndex left rows without <mark>), pages of 50, kept on Back
  await vai_('#cerca?q=dio&in=dizionario', '.r.rd');
  const senza = await p.$$eval('.risultati .r .frase', xs => xs.filter(x => !x.querySelector('mark')).length);
  verifica('cerca: ogni riga ha la parola evidenziata (lastIndex)', senza === 0, `${senza} righe senza <mark>`);
  await p.click('.bdiz [data-diz]');
  const dopo50 = await p.$$eval('.r.rd', xs => xs.length);
  const bottone = await p.$eval('.bdiz [data-diz]', x => x.textContent);
  verifica('cerca: «mostra altri» a pagine di 50', dopo50 === 75 && /mostra altri 50 paragrafi \(di /.test(bottone), `${dopo50} righe; ${bottone}`);
  await p.evaluate(() => window.scrollTo(0, 3000));
  await p.waitForTimeout(300);
  await p.click('.r.rd:nth-of-type(60) a.dove');
  await p.waitForSelector('.voce-testo');
  await p.goBack();
  await p.waitForSelector('.r.rd');
  await p.waitForTimeout(200);
  const ritorno = await p.evaluate(() => ({ righe: document.querySelectorAll('.r.rd').length, y: Math.round(scrollY) }));
  verifica('cerca: Indietro ritrova le righe aperte e la posizione', ritorno.righe === 75 && ritorno.y > 1000, JSON.stringify(ritorno));
  await vai_('#cerca?q=agnello di dio', '.bdiz');
  const uno = await p.$eval('#esito', x => x.textContent);
  verifica('cerca: singolare («1 voce»)', /\b1 voce\b/.test(uno) && !/\b1 voci\b/.test(uno), uno);
  // an entry: unresolved citations reachable by keyboard and touch, redirects counted by entry
  await vai_('#voce/fede', '.voce-testo a.cd.x');
  const x = await p.$eval('.voce-testo a.cd.x', a => ({ tab: a.tabIndex, role: a.getAttribute('role'), aria: a.getAttribute('aria-label') }));
  await p.focus('.voce-testo a.cd.x');
  await p.waitForSelector('#anteprima:not([hidden]) .ap-x');
  verifica('voce: una citazione non risolta si raggiunge da tastiera e mostra il motivo', x.tab === 0 && x.role === 'button' && /non risolto/.test(x.aria), await p.$eval('#anteprima .ap-x', e => e.textContent));
  await p.keyboard.press('Escape');
  await vai_('#voce/abba', '.rinvio-nota');
  const abba = await p.$eval('.rinvio-nota', e => e.textContent);
  verifica('voce di rinvio: conta le voci distinte', /queste 9 voci/.test(abba), abba);
  await vai_('#voce/mediatore', '.rinvii');
  const med = await p.$$eval('.rinvii li', xs => xs.map(x => x.textContent.trim()));
  verifica('vedi anche: niente bersagli fantasma («o»), «0» come introd.', !med.includes('o') && !med.some(t => / 0$/.test(t)), med.filter(t => /Ministero|Mosè/.test(t)).join(' | '));
  await vai_('#voce/monarchia', '.rinvii');
  verifica('rinvio MONARCHIA → Re', await p.$$eval('.rinvii a.vl', xs => xs.some(a => /^#voce\/re\b/.test(a.getAttribute('href')))));
  await vai_('#voce/agnello-di-dio/2?v=Isa.53.12', '.dpar.sel a.cd.sel');
  const segno = await p.$eval('.dpar.sel a.cd.sel', a => { const c = getComputedStyle(a); return { w: c.fontWeight, s: c.boxShadow }; });
  verifica('voce: la citazione del versetto si distingue nel paragrafo evidenziato', +segno.w >= 600 && segno.s !== 'none', JSON.stringify(segno));
  await foto(p, '34-voce-sel');
  await vai_('#voce/spirito-di-dio', '.voce-testo');
  const titoli = await p.$$eval('#vista [role="heading"]', xs => xs.length);
  verifica('voce: titoli delle sezioni come intestazioni (role=heading)', titoli > 20, titoli + ' intestazioni');
  await vai_('#voce/AGNELLO-DI-DIO', '.voce-pagina h1');
  verifica('#voce/AGNELLO-DI-DIO: indirizzo normalizzato', (await p.$eval('h1', e => e.textContent)) === 'Agnello di Dio' && (await hash(p)) === '#voce/agnello-di-dio');
  await vai_('#voce/agnello-di-dio/9999', '.voce-pagina .avviso');
  verifica('#voce/…/9999: dice che il paragrafo non c’è', true, await p.$eval('.avviso', e => e.textContent));
  // the index: the filter in the address, letters with nothing left disabled, kept on Back
  await vai_('#dizionario', '.dvl');
  await p.fill('#dq', 'spirito');
  const filtro = await p.evaluate(() => ({ h: location.hash, a: document.querySelector('.lettere [data-l="A"]').disabled }));
  await p.click('.dvl:not([hidden])');
  await p.waitForSelector('.voce-pagina');
  await p.goBack();
  await p.waitForSelector('.dvl:not([hidden])');
  const torna = await p.evaluate(() => ({ q: document.querySelector('#dq').value, n: document.querySelectorAll('.dvl:not([hidden])').length }));
  verifica('#dizionario: filtro nell’indirizzo, lettere vuote disattivate, Indietro', filtro.h === '#dizionario?q=spirito' && filtro.a && torna.q === 'spirito' && torna.n < 10, JSON.stringify([filtro, torna]));
  // the reader: the switch of the heat is there without the flame; it turns the heat on and off
  await vai_('#Isa.53', '.testo .v');
  const sw0 = await p.evaluate(() => ({ vis: getComputedStyle(document.querySelector('.legenda-calore')).display, on: document.body.classList.contains('calore'), pr: [...document.querySelectorAll('.fonte-calore button')].map(b => b.getAttribute('aria-pressed')).join() }));
  await p.click('.fonte-calore [data-fonte="diz"]');
  const sw1 = await p.evaluate(() => document.body.className);
  await p.click('.fonte-calore [data-fonte="diz"]');
  const sw2 = await p.evaluate(() => document.body.classList.contains('calore'));
  verifica('lettore: «Evidenzia» Rimandi BJ | Dizionario visibile senza la fiamma', sw0.vis === 'flex' && !sw0.on && sw0.pr === 'false,false' && /calore-diz/.test(sw1) && /\bcalore\b/.test(sw1) && !sw2, JSON.stringify([sw0, sw1, sw2]));

  // a literal parallel (‖): Mc 1,9 -> its parallel chip -> back
  await p.evaluate(() => { location.hash = '#Mark.1.9'; });
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Mc 1,9');
  const par = await p.$('#pannello .gruppo:has(h4 .seg:text-is("‖")) .chip');
  verifica('Mc 1,9 ha paralleli', !!par);
  if (par) {
    const dove = await par.getAttribute('href');
    await par.click();
    await p.waitForFunction(h => location.hash === h, dove);
    await p.goBack();
    await p.waitForFunction(() => location.hash === '#Mark.1.9');
    verifica('parallelo e ritorno', true, dove);
  }

  // a "+" reference opens the key note at its target
  await p.evaluate(() => { location.hash = '#Gen.1.3'; });
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Gen 1,3');
  await p.click('#pannello .chip[data-nota]');
  await p.waitForSelector('#pannello .nota.chiave[open]');
  verifica('rimando «+» apre la nota chiave', (await hash(p)) === '#John.8.12', await p.$eval('#pannello .nota.chiave .etichetta', x => x.textContent));
  await p.evaluate(() => { location.hash = '#Mark.1.9'; });
  await p.waitForFunction(() => document.querySelector('#pannello .rif')?.textContent === 'Mc 1,9');

  // keyboard: j, k, Esc, /
  await p.keyboard.press('j');
  verifica('j: versetto successivo', (await hash(p)) === '#Mark.1.10', await hash(p));
  await p.keyboard.press('k');
  verifica('k: versetto precedente', (await hash(p)) === '#Mark.1.9');
  await p.keyboard.press('Escape');
  verifica('Esc chiude il pannello', await p.$eval('#pannello', x => x.hidden) && (await hash(p)) === '#Mark.1');
  await p.keyboard.press('/');
  verifica('/ porta al riquadro', await p.evaluate(() => document.activeElement.id === 'q'));
  await p.keyboard.press('Escape');

  // range and chapter forms of the reference box, and the forms printed in the BJ (F3)
  for (const [testo, atteso] of [['Sal 23,1-4', '#Ps.23.1-4'], ['Gen 1', '#Gen.1'], ['Rm 5,12', '#Rom.5.12'], ['1 Cor 13', '#1Cor.13'], ['Gd 3', '#Jude.1.3'], ['Est 4,17a', '#EsthGr.4.17a'],
    ['Gen 2,4b', '#Gen.2.4'], ['Gen 1,1-2,4a', '#Gen.1.1-Gen.2.4'], ['Mt 5,3s', '#Matt.5.3-4'], ['Dt 7,9.12', '#Deut.7.9?e=Deut.7.12'],
    ['Gen 1,1; 2,4', '#Gen.1.1?e=Gen.2.4'], ['Sir prologo', '#Sir.Prol'], ['Sir prol 3', '#Sir.Prol.3'], ['I Cor 13', '#1Cor.13'],
    ['Prima Corinzi 13', '#1Cor.13'], ['Cantico dei Cantici 2', '#Song.2'], ['Gv3,16', '#John.3.16'], ['Est 4,17rs', '#EsthGr.4.17r-17s']]) {
    await p.fill('#q', testo);
    await p.press('#q', 'Enter');
    await p.waitForFunction(h => decodeURIComponent(location.hash) === h, atteso, { timeout: 5000 }).catch(() => {});
    verifica(`riquadro «${testo}»`, (await hash(p)) === atteso, await hash(p));
  }
  await p.fill('#q', 'Mt 5,3ss');
  await p.press('#q', 'Enter');
  await p.waitForFunction(() => location.hash.startsWith('#Matt.5.3-'));
  verifica('riquadro «Mt 5,3ss» fino alla fine della pericope', (await hash(p)) === '#Matt.5.3-12', await hash(p));
  await p.fill('#q', 'Dt 7,9.12');
  await p.press('#q', 'Enter');
  await p.waitForSelector('.anche a');
  verifica('«Dt 7,9.12» evidenzia anche il v 12', (await p.$$('.v.sel, .v.int')).length === 2);
  for (const t of ['Gv 3,99', 'Ap 22,22', 'Sal 9,22', 'Gen 51']) {
    const prima = await hash(p);
    await p.fill('#q', t);
    await p.press('#q', 'Enter');
    await p.waitForSelector('#omni .errore');
    verifica(`«${t}»: messaggio, non una ricerca (F3)`, (await hash(p)) === prima, await p.$eval('#omni .errore', x => x.textContent.split(' · ')[0]));
  }
  await p.fill('#q', '');
  await p.evaluate(() => { location.hash = '#Ps.23.1-4'; });
  verifica('Sal 23,1-4 evidenzia 4 versetti', (await p.$$('.v.sel, .v.int')).length === 4);
  await p.click('#calore');
  await foto(p, '05-salmo-calore');
  await p.click('#calore');

  // search, with and without the accent
  const conteggi = {};
  for (const q of ['Melchìsedek', 'melchisedek']) {
    await p.fill('#q', q);
    await p.press('#q', 'Enter');
    await p.waitForSelector('#esito b');
    conteggi[q] = await p.$eval('#esito', x => x.textContent.replace(/\s+/g, ' ').replace(/ \(\d+ ms\)/, '').trim());
    const segni = await p.$$eval('#risultati mark', xs => xs.length);
    verifica(`cerca «${q}»`, segni > 0, conteggi[q] + `, ${segni} evidenziati`);
  }
  verifica('stessi risultati con e senza accento', conteggi['Melchìsedek'] === conteggi['melchisedek']);
  // F4: whole words by default, "*" for the start of a word
  const quanti = async q => {
    await p.evaluate(q => { location.hash = '#cerca?q=' + encodeURIComponent(q) + '&in=versetti'; }, q);
    await p.waitForFunction(q => document.querySelector('#rq')?.value === q && document.querySelector('#esito')?.textContent, q);
    return p.$eval('#esito', x => +(x.querySelector('b')?.textContent || '0').replace(/\./g, ''));
  };
  const ira = await quanti('ira'), iraP = await quanti('ira*');
  const segnati = await p.$$eval('#risultati mark', xs => xs.slice(0, 20).map(x => x.textContent.toLowerCase()));
  verifica('«ira» trova la parola intera (F4)', ira > 200 && ira < 600 && iraP > ira && segnati.every(x => x.startsWith('ir')), `ira ${ira}, ira* ${iraP}`);
  const elia = await quanti('Elìa');
  verifica('«Elìa» non trova «Eliàb»', !(await p.$$eval('#risultati mark', xs => xs.some(x => /eliàb/i.test(x.textContent)))), `${elia} versetti`);
  // F2: the address is decoded once; "%", "&" and "?" survive
  await p.fill('#q', 'pane & vino');
  await p.press('#q', 'Enter');
  await p.waitForFunction(() => document.querySelector('#rq')?.value === 'pane & vino');
  const vivo = await p.$eval('#esito', x => x.textContent.replace(/ \(\d+ ms\)/, ''));
  await p.reload();
  await p.waitForFunction(() => window.__esploratore && document.querySelector('#esito')?.textContent);
  const ricaricato = await p.$eval('#esito', x => x.textContent.replace(/ \(\d+ ms\)/, ''));
  verifica('«pane & vino»: stessi risultati scrivendo e ricaricando (F2)', vivo === ricaricato && (await p.$eval('#rq', x => x.value)) === 'pane & vino', vivo);
  metriche.ricerca = conteggi;
  await foto(p, '06-cerca');
  await p.selectOption('#rt', 'NT');
  await p.waitForFunction(() => location.hash.includes('t=NT'));
  verifica('filtro Nuovo Testamento', await p.$$eval('.risultati .blocco h3 a', xs => xs.every(a => /Ebrei|Matteo|Marco|Luca|Giovanni|Atti|Romani|Corinzi|Galati|Efesini|Filippesi|Colossesi|Tessalonicesi|Timoteo|Tito|Filemone|Giacomo|Pietro|Giuda|Apocalisse/.test(a.textContent))));

  // graph: the tab writes the verse in the address, unknown ids say so, filters are in the address (F11)
  await p.evaluate(() => { location.hash = '#Ps.23.1'; });
  await p.waitForSelector('#pannello:not([hidden])');
  await p.click('.schede a[data-vista="grafo"]');
  await p.waitForSelector('#ginfo b');
  verifica('scheda Grafo: indirizzo stabile (F11)', (await hash(p)) === '#grafo/Ps.23.1', await hash(p));
  await p.evaluate(() => { location.hash = '#grafo/Xyz'; });
  await p.waitForFunction(() => /non trovato/.test(document.querySelector('#vista h1')?.textContent || ''));
  verifica('#grafo/Xyz: versetto non trovato', true);
  await p.evaluate(() => { location.hash = '#grafo/Gen.1.1?f=parallel'; });
  await p.waitForSelector('#ginfo b');
  verifica('filtri del grafo nell’indirizzo', await p.$$eval('.grafo-lato input[data-rel]', xs => xs.filter(x => x.checked).map(x => x.dataset.rel).join()) === 'parallel');
  await p.evaluate(() => { location.hash = '#grafo/Gen.44.1'; });      // no margin, note or dictionary link
  await p.waitForSelector('#ginfo b');
  verifica('grafo senza collegamenti lo dice (F12)', /nessun collegamento/.test(await p.$eval('.carta.radice .conta', x => x.textContent)), await p.$eval('#ginfo', x => x.textContent));
  await foto(p, '23-grafo-vuoto');
  // the tree: the root card with its text and notes, the groups, the cards of the first level
  await p.evaluate(() => { location.hash = '#grafo/John.3.16'; });
  await p.waitForSelector('#ginfo b');
  const g1 = await p.$eval('#ginfo', x => x.textContent);
  const radice = await p.$eval('.carta.radice', c => ({
    testo: c.querySelector('.carta-testo').textContent, note: c.querySelectorAll('.foglietto').length,
    contorno: !!c.querySelector('svg.contorno path.tratto'),
  }));
  verifica('albero: la radice ha testo, note e contorno a mano', /tanto amato il mondo/.test(radice.testo) && radice.note >= 1 && radice.contorno, JSON.stringify(radice));
  const primo = await p.$$eval('.carta:not(.radice)', cs => cs.length);
  verifica('albero con schede e gruppi', /^\d+ schede/.test(g1) && primo > 3 && (await p.$$('.ramo-gruppo')).length > 0 && (await p.$$('#rami path')).length >= primo, g1);
  metriche.grafo_p1 = g1;
  await foto(p, '07-grafo');
  // ▸ grows a card in place
  const prima1 = (await p.$$('.carta')).length;
  await p.evaluate(() => document.querySelector('.carta:not(.radice) .cresci:not([disabled])').click());
  verifica('▸ apre i collegamenti di una scheda', (await p.$$('.carta')).length > prima1, `${prima1} -> ${(await p.$$('.carta')).length} schede`);
  // a note slip opens whole
  const lungo = await p.$('.foglietto .altro');
  if (lungo) {
    const n0 = await p.$eval('.foglietto .altro', b => b.closest('.foglietto').textContent.length);
    await p.evaluate(() => document.querySelector('.foglietto .altro').click());
    const k = await p.$eval('.foglietto .altro', b => b.textContent);
    verifica('una nota si apre per intero', k === 'riduci', `${n0} caratteri prima`);
  }
  await p.click('.grafo-lato [data-esplora="piu"]');
  metriche.grafo_p2 = await p.$eval('#ginfo', x => x.textContent);
  verifica('apri un livello', parseInt(metriche.grafo_p2) > parseInt(g1), metriche.grafo_p2);
  await foto(p, '08-grafo-2');
  // the reference of a card makes it the root
  const prima = await hash(p);
  await p.evaluate(() => document.querySelector('.carta:not(.radice) .carta-rif').click());
  await p.waitForFunction(h => decodeURIComponent(location.hash) !== h, prima, { timeout: 5000 }).catch(() => {});
  verifica('clic su un riferimento ricentra', (await hash(p)) !== prima, await hash(p));

  // overview and matrix
  await p.evaluate(() => { location.hash = '#panoramica'; });
  await p.waitForSelector('#mcv');
  metriche.tessere = await p.$$eval('.tessera', xs => xs.map(x => x.querySelector('b').textContent + ' ' + x.querySelector('span').textContent));
  const cella = await p.evaluate(() => {
    const a = S.osis.get('2Kgs'), b = S.osis.get('2Chr');
    const r = document.querySelector('#mcv').getBoundingClientRect();
    return { x: r.left + S.m0 + (b + 0.5) * S.cella, y: r.top + S.m0 + (a + 0.5) * S.cella };
  });
  await p.evaluate(() => document.querySelector('#mcv').scrollIntoView({ block: 'center' }));
  const cella2 = await p.evaluate(() => {
    const a = S.osis.get('2Kgs'), b = S.osis.get('2Chr');
    const r = document.querySelector('#mcv').getBoundingClientRect();
    return { x: r.left + S.m0 + (b + 0.5) * S.cella, y: r.top + S.m0 + (a + 0.5) * S.cella };
  });
  await p.mouse.move(cella2.x, cella2.y);
  await foto(p, '09-matrice-hover');
  await p.mouse.click(cella2.x, cella2.y);
  await p.waitForSelector('#coppia table tr');
  await p.waitForTimeout(200);
  const righe = await p.$$eval('#coppia tr', xs => xs.length);
  verifica('clic sulla matrice elenca i rimandi', (await hash(p)) === '#panoramica/2Kgs/2Chr' && righe > 10, `${righe} righe`);
  const visibile = await p.evaluate(() => { const r = document.querySelector('#coppia').getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight; });
  verifica('al primo clic l’elenco è in vista (F5)', visibile);
  const barre = await p.$$eval('.relazioni-barre .val', xs => xs.map(x => +x.textContent.replace(/\./g, '')));
  const rimandi = await p.evaluate(() => D.meta.riepilogo.mref_items);
  verifica('le barre sommano i rimandi a margine (F1)', barre.reduce((a, b) => a + b, 0) === rimandi, `${barre.join('+')} = ${rimandi}`);
  await foto(p, '10-matrice-coppia');
  const top = await p.$$eval('.classifica:not(.diz-top) tr', xs => xs.length);
  verifica('50 versetti più rimandati', top === 50);

  // F13: one wording for margin entries and references
  const tessera = await p.$$eval('.tessera', xs => xs.map(x => x.textContent).find(t => /rimandi a margine/.test(t)));
  verifica('tessera dei rimandi a margine coerente con l’indice (F13)', tessera.includes(numeri.find(t => /rimandi a margine/.test(t)).split(' ')[0]), tessera);

  // introduction with its citations
  await p.evaluate(() => { location.hash = '#intro/intro-pentateuco.1'; });
  await p.waitForSelector('.intro-testo a.ci');
  verifica('introduzione con citazioni', (await p.$$('.intro-testo a.ci[href]')).length > 3);
  await foto(p, '20-introduzione');
  await p.evaluate(() => { location.hash = '#Gen'; });
  await p.waitForSelector('.capitoli a');
  verifica('pagina del libro', (await p.$$('.capitoli a')).length === 50 && (await p.$$('.schema li')).length > 50);
  await foto(p, '21-libro');

  // an unresolved margin reference is shown greyed, with its reason
  await p.evaluate(() => { location.hash = '#Deut.32.1'; });
  await p.waitForSelector('#pannello:not([hidden]) .chip.x');
  const motivo = await p.$eval('#pannello .motivo', x => { x.scrollIntoView({ block: 'center' }); return x.textContent; });
  verifica('rimando irrisolto in grigio con il motivo', /39,19/.test(motivo), motivo);
  await foto(p, '22-irrisolto');

  // F6: book names are not cut in the index
  await p.evaluate(() => { location.hash = '#'; });
  await p.waitForSelector('.libro');
  const tagliati = await p.$$eval('.libro b', xs => xs.filter(x => x.scrollWidth > x.clientWidth + 1).map(x => x.textContent));
  verifica('nessun titolo troncato nell’indice (F6)', !tagliati.length, tagliati.join(', '));
  // F8: contrast of the muted text, F9: keyboard
  const contrasto = await p.evaluate(() => {
    const rgb = c => { const d = document.createElement('i'); d.style.color = c; document.body.appendChild(d); const v = getComputedStyle(d).color.match(/\d+/g).map(Number); d.remove(); return v; };
    const L = c => { const [r, g, b] = rgb(c).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const cr = (a, b) => { const [x, y] = [L(a), L(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
    return ['--foglio', '--carta', '--sopra'].map(bg => cr('var(--tenue)', `var(${bg})`).toFixed(2)).concat([cr('var(--r-diz)', 'var(--foglio)').toFixed(2)]);
  });
  verifica('contrasto del testo tenue e del Dizionario ≥ 4,5 (F8, chiaro)', contrasto.every(x => +x >= 4.5), contrasto.join(', '));
  await p.evaluate(() => { location.hash = '#Mark.1'; });
  await p.waitForSelector('.testo .v');
  await p.focus('.testo .v[data-i]');
  await p.keyboard.press('Tab');
  await p.keyboard.press('Enter');
  await p.waitForSelector('#pannello:not([hidden])');
  await p.waitForTimeout(150);
  verifica('Invio su un versetto apre il pannello e vi porta il fuoco (F9)', await p.evaluate(() => document.activeElement?.classList.contains('rif')), await hash(p));
  await p.keyboard.press('Escape');
  await p.keyboard.press('?');
  verifica('guida modale con il fuoco dentro (F9)', await p.evaluate(() => document.querySelector('#guida [aria-modal="true"]')?.contains(document.activeElement)));
  await p.keyboard.press('Tab'); await p.keyboard.press('Tab'); await p.keyboard.press('Tab');
  verifica('Tab resta nella guida', await p.evaluate(() => document.querySelector('#guida').contains(document.activeElement)));
  await p.keyboard.press('Escape');
  verifica('Esc chiude la guida', await p.$eval('#guida', x => x.hidden));

  // ------------------------------------------------ the front matter and the appendices
  // the books index: four cards to the new views
  await p.evaluate(() => { location.hash = '#'; });
  await p.waitForSelector('.apparati');
  verifica('indice: le pagine iniziali e le appendici', (await p.$$('.apparati .apparato')).length === 4 && (await p.$$('.libro')).length === 74);
  // the reader: acrostic letters in the right margin, at the line each one opens
  await p.evaluate(() => { location.hash = '#Lam.1'; });
  await p.waitForSelector('.testo .v');
  const lam = await p.evaluate(() => {
    const a = [...document.querySelectorAll('.testo .acr')], t = document.querySelector('.testo').getBoundingClientRect();
    const segni = [...document.querySelectorAll('.testo .mm')].map(x => x.getBoundingClientRect().left);
    return { n: a.length, primo: a[0]?.textContent, fuori: a.every(x => x.getBoundingClientRect().right <= Math.min(t.left, ...segni) - 2 && x.getBoundingClientRect().left >= 0), larghezza: document.documentElement.scrollWidth };
  });
  verifica('Lam 1: 22 lettere acrostiche nel margine', lam.n === 22 && lam.primo.includes('א') && lam.primo.includes('Alef') && lam.fuori && lam.larghezza <= 1366, JSON.stringify(lam));
  await foto(p, '40-lam-acrostico');
  await p.evaluate(() => { location.hash = '#Nah.1'; });
  await p.waitForSelector('.testo .v');
  const nah = await p.evaluate(() => { const v = document.querySelector('#v' + S.vix.get('Nah.1.3')); const r = [...v.querySelectorAll('.r')]; return r.map(x => x.querySelector('.acr')?.textContent || '').join('|'); });
  verifica('Na 1,3: Bet nel margine del terzo rigo', /^\|\|.*Bet/.test(nah), nah);
  // Ps 10: 11 letters, the bracketed ones as printed, «(Mem)», with the Hebrew letter and the title
  await p.evaluate(() => { location.hash = '#Ps.10'; });
  await p.waitForSelector('.testo .v');
  const sal10 = await p.evaluate(() => { const a = [...document.querySelectorAll('.testo .acr')];
    const m = a.find(x => x.textContent.includes('(Mem)')); return { n: a.length, mem: m?.textContent, titolo: m?.title }; });
  verifica('Sal 10: 11 lettere acrostiche, «(Mem)» tra parentesi', sal10.n === 11 && sal10.mem?.includes('מ') && /mancante/.test(sal10.titolo || ''), JSON.stringify(sal10));
  // the verse panel: the index of notes (a misprint corrected), the themes, the chronology
  await p.evaluate(() => { location.hash = '#Josh.14.6'; });
  await p.waitForSelector('#pannello:not([hidden]) .sez.ix');
  const gs = await p.$eval('#pannello .sez.ix', x => ({ h: x.querySelector('h3').textContent, voce: x.textContent.includes('Caleb'),
    refuso: x.querySelector('.chip.refuso')?.textContent, corretto: x.querySelector('.chip.corretto')?.textContent, nota: x.querySelector('.nota-ix')?.dataset.nota }));
  const notaGs = await p.evaluate(() => D.note.findIndex(n => n[0] === S.vix.get('Josh.14.6')));
  verifica('pannello di Gs 14,6: «Nell’indice delle note», Caleb, refuso corretto e nota', gs.h.startsWith('Nell’indice delle note') && gs.voce && gs.refuso === 'Gb 14,6' && gs.corretto.includes('Gs 14,6') && +gs.nota === notaGs, JSON.stringify(gs));
  await foto(p, '41-pannello-indice-note');
  await p.evaluate(() => { location.hash = '#John.1.14'; });
  await p.waitForSelector('#pannello:not([hidden]) .sez.ix');
  const gv = await p.$$eval('#pannello .sez.ix', xs => xs.map(x => [x.querySelector('h3').textContent, x.querySelectorAll('li').length]));
  const attese114 = await p.evaluate(() => [indiceDi('note', S.vix.get('John.1.14')).length, indiceDi('temi', S.vix.get('John.1.14')).length]);
  verifica('pannello di Gv 1,14: indice delle note e temi pastorali', gv.length === 2 && gv[0][0].startsWith('Nell’indice') && gv[1][0].startsWith('Temi pastorali') && gv[0][1] === attese114[0] && gv[1][1] === attese114[1], JSON.stringify(gv) + ' ' + attese114);
  await p.click('#pannello .sez.ix .nota-ix');
  await p.waitForSelector('#pannello .nota.lampo[open]');
  verifica('«nota» dell’indice apre la nota della BJ nel pannello', (await hash(p)).startsWith('#John.1.14'), await hash(p));
  await p.evaluate(() => { location.hash = '#Gen.4.22'; });
  await p.waitForSelector('#pannello:not([hidden]) .sez.cron');
  const gen = await p.$eval('#pannello .sez.cron', x => [x.textContent.includes('Tubal-Kain'), x.querySelector('a').getAttribute('href')]);
  verifica('pannello di Gen 4,22: nella tavola cronologica, la voce più puntuale prima', gen[0] && gen[1] === '#cronologia/1?v=10', gen.join(' '));
  await p.click('#pannello .sez.cron li a');
  await p.waitForSelector('.cron-cella p.sel');
  verifica('la voce della cronologia si apre evidenziata', (await p.$eval('.cron-cella p.sel', x => x.id)) === 'cv10');
  // the index of notes: the list, the filter in the address, an entry, «v.»
  await p.evaluate(() => { location.hash = '#indice-note'; });
  await p.waitForSelector('.indice-an .dvl');
  const nIx = await p.$$eval('.indice-an .dvl', xs => xs.length);
  await p.fill('#dq', 'caleb');
  await p.waitForTimeout(100);
  const visibili = await p.$$eval('.indice-an .dvl', xs => xs.filter(x => !x.hidden).map(x => x.textContent));
  verifica('#indice-note: 628 voci, il filtro nell’indirizzo', nIx === 628 && visibili.length === 1 && visibili[0].startsWith('Caleb') && (await hash(p)) === '#indice-note?q=caleb', `${nIx}, ${visibili.join()}, ${await hash(p)}`);
  await foto(p, '42-indice-note');
  await p.click('.indice-an .dvl:not([hidden])');
  await p.waitForSelector('.voce-ix h1');
  verifica('#indice-note/91: Caleb, «Gb 14,6» stampato e «→ Gs 14,6»', (await hash(p)) === '#indice-note/91' && (await p.$eval('.voce-ix h1', x => x.textContent)) === 'Caleb' && (await p.$eval('.ix-corpo .chip.corretto', x => x.getAttribute('href'))) === '#Josh.14.6');
  await p.evaluate(() => { location.hash = '#indice-note/2'; });
  await p.waitForSelector('.voce-ix a.vedi');
  await p.click('.voce-ix a.vedi');
  await p.waitForFunction(() => location.hash === '#indice-note/186' && document.querySelector('.voce-ix h1')?.textContent === 'Ebiatàr');
  verifica('«v. Ebiatàr» apre la voce', (await p.$eval('.voce-ix h1', x => x.textContent)) === 'Ebiatàr');
  await foto(p, '43-voce-indice');
  // the pastoral themes
  await p.evaluate(() => { location.hash = '#temi'; });
  await p.waitForSelector('.indice-an .dvl');
  verifica('#temi: 96 temi', (await p.$$('.indice-an .dvl')).length === 96);
  await p.evaluate(() => { location.hash = '#temi/1'; });
  await p.waitForSelector('.ix-riga.sv');
  const ad = await p.evaluate(() => ({ sv: document.querySelectorAll('.ix-riga.sv').length, x: [...document.querySelectorAll('.ix-corpo .chip.x')].map(x => [x.textContent, x.title]) }));
  verifica('#temi/1 Adorazione: 5 sottotemi, «Gv 2,38» irrisolto con il motivo', ad.sv === 5 && ad.x.some(([t, m]) => t === 'Gv 2,38' && /versetto inesistente/.test(m)), JSON.stringify(ad));
  await foto(p, '44-tema');
  // the chronology: sections, the table of a section with its columns, citations linked, the dynasties
  await p.evaluate(() => { location.hash = '#cronologia'; });
  await p.waitForSelector('.cron-sezioni');
  verifica('#cronologia: 9 periodi e le dinastie', (await p.$$('.cron-sezioni .tessera')).length === 10);
  await p.evaluate(() => { location.hash = '#cronologia/6'; });
  await p.waitForSelector('.cron-tavola');
  const cr = await p.evaluate(() => ({ col: [...document.querySelectorAll('.cron-testata div')].map(x => x.textContent).filter(Boolean),
    righe: document.querySelectorAll('.cron-riga').length, voci: document.querySelectorAll('.cron-cella p').length,
    link: [...document.querySelectorAll('.cron-tavola a.ci[href]')].length, attese: A.cron.voci.filter(v => v[0] === 6).length,
    cit: A.cron.cit.filter(c => A.cron.voci[c[0]][0] === 6 && c[1].length).length, sez: document.querySelector('.cron-nav [aria-current]').textContent }));
  verifica('#cronologia/6: colonne, voci, riferimenti come collegamenti', cr.col.length >= 2 && cr.voci === cr.attese && cr.link === cr.cit && cr.sez === 'VI', JSON.stringify(cr));
  await foto(p, '45-cronologia');
  await p.evaluate(() => { location.hash = '#cronologia/dinastie'; });
  await p.waitForSelector('.dinastie');
  const din = await p.evaluate(() => ({ n: document.querySelectorAll('.dinastie .persona').length, erode: [...document.querySelectorAll('#din-P15 > ul > li .madre')].map(x => x.textContent) }));
  // 34 persons, 8 of them printed only as a spouse (∞), beside their husband or wife
  verifica('dinastie: 34 persone, i figli di Erode con la madre', din.n === 34 - 8 && JSON.stringify(din.erode) === JSON.stringify(['da Mariamne I', 'da Mariamne II', 'da Maltace', 'da Maltace', 'da Cleopatra']), JSON.stringify(din));
  // the front matter
  await p.evaluate(() => { location.hash = '#introduzione-generale'; });
  await p.waitForSelector('.pre-testi');
  verifica('#introduzione-generale: edizione e testi', (await p.$$('.pre-testo')).length === 11 && (await p.$eval('.preliminari .sotto', x => x.textContent)).includes('978-88-10-82031-5'));
  await p.click('.pre-testo[href="#introduzione-generale/presentazione"]');
  await p.waitForSelector('.intro-testo.corsivo');
  const pres = await p.evaluate(() => ({ firma: document.querySelector('.firma-pre b').textContent, rif: document.querySelector('.intro-testo a.ci')?.getAttribute('href'), corsivo: getComputedStyle(document.querySelector('.intro-testo p')).fontStyle }));
  verifica('Presentazione: firma, corsivo, Sal 119,105 collegato', pres.firma.includes('Ravasi') && pres.rif === '#Ps.119.105' && pres.corsivo === 'italic', JSON.stringify(pres));
  await foto(p, '46-presentazione');
  await p.evaluate(() => { location.hash = '#introduzione-generale/divisione-ebraica'; });
  await p.waitForSelector('.canone');
  const can = await p.evaluate(() => ({ n: document.querySelectorAll('.canone li').length, sam: [...document.querySelectorAll('.canone li')][7].querySelectorAll('.in-bibbia a').length }));
  verifica('Divisione della Bibbia ebraica: 24 libri, Samuele = 1Sam e 2Sam', can.n === 24 && can.sam === 2, JSON.stringify(can));
  await p.evaluate(() => { location.hash = '#introduzione-generale/abbreviazioni'; });
  await p.waitForSelector('table.abbr');
  const ab = await p.evaluate(() => ({ libri: document.querySelectorAll('.abbr-libri span').length, greg: document.body.textContent.includes('Gregory-Aland 01') }));
  verifica('Abbreviazioni e codici: sigle dei libri, codici con il numero Gregory-Aland', ab.libri === 63 && ab.greg, JSON.stringify(ab));
  await p.evaluate(() => { location.hash = '#introduzione-generale/avvertenze'; });
  await p.waitForSelector('.chips.xilo');
  verifica('Avvertenze: le 73 xilografie con i loro versetti', (await p.$$('.chips.xilo .chip')).length === 73);
  // the search reaches the indices, the chronology and the texts
  await p.evaluate(() => { location.hash = '#cerca?q=caleb'; });
  await p.waitForSelector('#esito b');
  const cb = await p.evaluate(() => [...document.querySelectorAll('.bpar .chip')].map(x => x.getAttribute('href')));
  verifica('cerca «caleb»: la voce dell’indice delle note', cb.includes('#indice-note/91'), cb.join());
  await p.evaluate(() => { location.hash = '#cerca?q=hammurabi&in=apparati'; });
  await p.waitForSelector('#esito b');
  const hm = await p.evaluate(() => ({ righe: document.querySelectorAll('.bpar .r').length, mark: document.querySelectorAll('.bpar .r mark').length, link: document.querySelector('.bpar .r a')?.getAttribute('href') }));
  verifica('cerca «hammurabi» nelle appendici: la tavola cronologica', hm.righe >= 1 && hm.mark >= hm.righe && /^#cronologia\/\d\?v=\d+$/.test(hm.link), JSON.stringify(hm));
  await p.evaluate(() => { location.hash = '#cerca?q="lampada per i miei passi"&in=apparati'; });
  await p.waitForSelector('#esito b');
  verifica('cerca una frase della Presentazione', await p.evaluate(() => [...document.querySelectorAll('.bpar .r a')].some(a => a.getAttribute('href').startsWith('#introduzione-generale/presentazione'))));
  // the overview: four tiles with the numbers of the payload
  await p.evaluate(() => { location.hash = '#panoramica'; });
  await p.waitForSelector('.tessere-par');
  const tp = await p.evaluate(() => [[...document.querySelectorAll('.tessere-par .tessera b')].map(x => x.textContent), [A.meta.note.entries, A.meta.note.references, A.meta.temi.entries, A.meta.cron].map(num)]);
  verifica('panoramica: tessere delle appendici', JSON.stringify(tp[0]) === JSON.stringify(tp[1]), tp[0].join(' · '));
  // keyboard: Tab from the filter reaches the first entry, Enter opens it
  await p.evaluate(() => { location.hash = '#temi'; });
  await p.waitForSelector('#dq');
  await p.focus('#dq');
  for (let k = 0; k < 30 && !(await p.evaluate(() => document.activeElement.classList.contains('dvl'))); k++) await p.keyboard.press('Tab');
  await p.keyboard.press('Enter');
  await p.waitForFunction(() => location.hash.startsWith('#temi/'));
  verifica('tastiera: Tab e Invio aprono un tema', (await hash(p)) === '#temi/1', await hash(p));
  // dark theme: the chronology and an index entry
  await p.click('#tema');
  await p.evaluate(() => { location.hash = '#cronologia/9'; });
  await p.waitForSelector('.cron-tavola');
  await foto(p, '47-cronologia-scuro');
  const scuroPar = await p.evaluate(() => {
    const rgb = c => { const d = document.createElement('i'); d.style.color = c; document.body.appendChild(d); const v = getComputedStyle(d).color.match(/\d+/g).map(Number); d.remove(); return v; };
    const L = c => { const [r, g, b] = rgb(c).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const cr = (a, b) => { const [x, y] = [L(a), L(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
    return [cr('var(--rubrica)', 'var(--carta)'), cr('var(--richiamo)', 'var(--foglio)'), cr('var(--secondo)', 'var(--carta)')].map(x => x.toFixed(2));
  });
  verifica('tema scuro: anni, «nota» e colonne leggibili (≥ 4,5)', scuroPar.every(x => +x >= 4.5), scuroPar.join(', '));
  await p.evaluate(() => { location.hash = '#indice-note/33'; });
  await p.waitForSelector('.voce-ix h1');
  await foto(p, '48-indice-scuro');
  await p.click('#tema');

  // dark theme
  await p.evaluate(() => { location.hash = '#John.3.16'; });
  await p.waitForSelector('#pannello:not([hidden])');
  await p.click('#tema');
  await p.waitForTimeout(400);
  const fondo = await p.evaluate(() => getComputedStyle(document.body).backgroundColor);
  verifica('tema scuro', await p.evaluate(() => document.documentElement.dataset.theme) === 'dark' && fondo !== 'rgb(248, 246, 241)', fondo);
  verifica('#tema aria-pressed (F9)', (await p.getAttribute('#tema', 'aria-pressed')) === 'true');
  const scuro = await p.evaluate(() => {
    const rgb = c => { const d = document.createElement('i'); d.style.color = c; document.body.appendChild(d); const v = getComputedStyle(d).color.match(/\d+/g).map(Number); d.remove(); return v; };
    const L = c => { const [r, g, b] = rgb(c).map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
    const cr = (a, b) => { const [x, y] = [L(a), L(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
    return [cr('var(--tenue)', 'var(--foglio)'), cr('var(--tenue)', 'var(--carta)'), cr('var(--rubrica)', 'var(--sel)'), cr('var(--r-diz)', 'var(--foglio)')].map(x => x.toFixed(2));
  });
  verifica('contrasto nel tema scuro ≥ 4,5 (F8)', scuro.every(x => +x >= 4.5), scuro.join(', '));
  await foto(p, '11-scuro');
  await p.evaluate(() => { location.hash = '#grafo/Gen.22.2'; });
  await p.waitForSelector('#ginfo b');
  await p.waitForTimeout(700);
  await foto(p, '12-grafo-scuro');
  await p.evaluate(() => { location.hash = '#panoramica'; });
  await p.waitForSelector('#mcv');
  await foto(p, '13-panoramica-scuro');
  await p.evaluate(() => { location.hash = '#voce/agnello-di-dio/3'; });
  await p.waitForSelector('.dpar.sel');
  await foto(p, '34-voce-scuro');
  // ------------------------------------------------ session F2: the review R3 (E1-E15) and the links between the parts (E19)
  const box = async q => { await vai_('#'); await p.fill('#q', q); await p.press('#q', 'Enter'); await p.waitForTimeout(150); return { h: await hash(p), err: await p.$eval('#omni', x => x.querySelector('.errore')?.textContent || '') }; };
  // E1: numbered sigla glued to the number, E7: more forms
  const forme = {};
  for (const [q, atteso] of [['1Cor 13,4', '#1Cor.13.4'], ['1Cor 13', '#1Cor.13'], ['1Sam 3', '#1Sam.3'], ['2Re 2,11', '#2Kgs.2.11'],
    ['1Gv 4,8', '#1John.4.8'], ['1Mac 1,1', '#1Macc.1.1'], ['1Cor13,4', '#1Cor.13.4'], ['1Cor 13,4-7', '#1Cor.13.4-7'],
    ['Gv 3 16', '#John.3.16'], ['Giov 3,16', '#John.3.16'], ['Ecclesiaste 3', '#Eccl.3'], ['Eccli 1', '#Sir.1'], ['Lettera di Geremia', '#Bar.6']]) {
    const r = await box(q);
    forme[q] = r.h;
    verifica(`E1/E7: «${q}» nel riquadro`, r.h === atteso, r.h + (r.err ? ' ' + r.err : ''));
  }
  const gn = await box('Gn 1,1');
  verifica('E7: «Gn» porta a Giona e lo dice', gn.h === '#Jonah.1.1' && /Giona/.test(await p.$eval('#vista', x => x.querySelector('.avviso')?.textContent || '')), gn.h);
  // E3: plurals for a count of 1
  await vai_('#John.3.16', '#pannello:not([hidden]) .contatori');
  const cont = await p.$$eval('#pannello .contatori span', xs => xs.map(x => x.textContent.trim()));
  verifica('E3: «1 nota» nel pannello, non «1 note»', cont.includes('1 nota') && !cont.some(t => /^1 (note|rimandi|citazioni|voci)\b/.test(t)), cont.join(' · '));
  await vai_('#cerca?q=golgota', '#esito b');
  const golg = await p.$eval('#esito', x => x.textContent);
  verifica('E3: riepilogo della ricerca al singolare', !/\b1 note\b|\b1 libri\b|\b1 versetti\b/.test(golg), golg);
  // E4: not-found pages with their title and message
  for (const [h, re] of [['#cronologia/99', /Periodo «99» inesistente/], ['#introduzione-generale/xyz', /non presente nell’Introduzione generale/],
    ['#Gen.51', /capitolo inesistente/], ['#persona/P99', /non è una persona/]]) {
    await vai_(h, '#vista h1');
    const r = await p.evaluate(() => [document.title, document.querySelector('#vista .sotto')?.textContent || '']);
    verifica(`E4: ${h} non trovato, con il suo titolo`, /^Non trovato/.test(r[0]) && re.test(r[1]), r.join(' | '));
  }
  // E5: the Appendici tab, its hub, highlighted on the appendix routes; the home order
  await vai_('#indice-note', '.dvl');
  verifica('E5: «Appendici» evidenziata su #indice-note', await p.$eval('.schede a.attiva', a => a.dataset.vista) === 'apparati');
  await p.click('.schede a[data-vista="apparati"]');
  await p.waitForSelector('#vista .apparato');
  const hub = await p.$$eval('#vista .apparato', xs => xs.map(a => a.getAttribute('href')));
  verifica('E5: la pagina #appendici elenca le appendici', ['#indice-note', '#temi', '#cronologia', '#cronologia/dinastie', '#calendario', '#misure', '#carte', '#introduzione-generale'].every(h => hub.includes(h)), hub.join(' '));
  await foto(p, '60-appendici');
  await vai_('#', '.apparati');
  const ordine = await p.evaluate(() => document.querySelector('.apparati').getBoundingClientRect().top < document.querySelector('.testamenti').getBoundingClientRect().top);
  verifica('E5: in prima pagina le appendici sopra i libri', ordine);
  // E2: synonyms; E6: verses first, the dictionary box closed, its entry's paragraphs first
  await vai_('#cerca?q=davide', '#esito b');
  const dav = await p.evaluate(() => ({ esito: document.querySelector('#esito').textContent, diz: document.querySelector('.bdiz h3 small')?.textContent || '' }));
  verifica('E2: «davide» trova anche «David» del Dizionario', /anche: david/.test(dav.esito) && /[1-9]/.test(dav.diz), JSON.stringify(dav));
  await vai_('#cerca?q=amore', '.bdiz');
  const amore = await p.evaluate(() => ({ chiuso: document.querySelector('details.bdiz') && !document.querySelector('details.bdiz').open,
    primo: document.querySelector('.bdiz .r.rd a.dove')?.textContent || '' }));
  verifica('E6: in «Tutto» il Dizionario è un riquadro chiuso, prima i paragrafi della voce AMORE', amore.chiuso && /^Amore/.test(amore.primo), JSON.stringify(amore));
  // E11: Back to a chapter keeps its scroll position
  await vai_('#Ps.119', '.testo .v');
  await p.evaluate(() => window.scrollTo(0, 4000));
  await p.waitForTimeout(300);
  await vai_('#voce/legge', '.voce-testo');
  await p.goBack();
  await p.waitForSelector('.testo .v');
  await p.waitForTimeout(250);
  const y119 = await p.evaluate(() => Math.round(scrollY));
  verifica('E11: Indietro a Sal 119 ritrova la posizione', y119 > 3500, `y = ${y119}`);
  // E12: titles that name the page
  await vai_('#John.3.16', '#pannello:not([hidden])');
  const t316 = await p.evaluate(() => document.title);
  await vai_('#cronologia/6', '.cron-tavola');
  const t6 = await p.evaluate(() => document.title);
  verifica('E12: titoli con il versetto e il periodo', /^Gv 3,16 · /.test(t316) && /^VI\. Fine del regno di Giuda · Tavola cronologica$/.test(t6), `${t316} | ${t6}`);
  // E13: one glossary
  await vai_('#introduzione-generale', '.pre-testo');
  verifica('E13: «Introduzione generale», non «Pagine iniziali»', await p.evaluate(() => !document.body.textContent.includes('Pagine iniziali') && document.title.startsWith('Introduzione generale')));
  // E14: no «0» on the index cards
  await vai_('#indice-note', '.dvl');
  const zeri = await p.$$eval('.dvl span', xs => xs.filter(x => x.textContent.trim() === '0').length);
  const agrippa = await p.$$eval('.dvl', xs => xs.find(a => a.textContent.startsWith('Agrippa'))?.querySelector(':scope > span').textContent);
  verifica('E14: nessuna voce con «0», «Agrippa» dice «v.»', zeri === 0 && agrippa === 'v.', `${zeri} zeri; Agrippa ${agrippa}`);
  // E15: the note summary names the verse once
  await vai_('#indice-note/91', '.ix-nota summary');
  const caleb = await p.$eval('.ix-nota summary .etichetta', x => x.textContent);
  verifica('E15: «Gs 14,6» una volta sola nella nota dell’indice', !/14,6 14,6/.test(caleb), caleb);
  // E19: «Anche in» on the index entry, the theme and the dictionary entry
  await vai_('#indice-note/' + await p.evaluate(() => A.indici.note.find(v => v[2] === 'Amore')[0]), '.voce-ix h1');
  const anche = await p.$$eval('.anche-in .anche-chip', xs => xs.map(a => [a.getAttribute('href'), a.textContent]));
  verifica('E19: «Anche in» su Amore (indice delle note): Dizionario e temi', anche.some(([h]) => h === '#voce/amore') && anche.some(([h]) => h.startsWith('#temi/')), JSON.stringify(anche));
  await foto(p, '61-anche-in-indice');
  await vai_('#voce/amore', '.voce-testo');
  const ancheV = await p.$$eval('.anche-in .anche-chip', xs => xs.map(a => a.getAttribute('href')));
  verifica('E19: «Anche in» sulla voce AMORE: indice delle note e temi', ancheV.some(h => h.startsWith('#indice-note/')) && ancheV.some(h => h.startsWith('#temi/')), ancheV.join(' '));
  await foto(p, '62-anche-in-voce');
  // persons: the page, the dynasties' links, the panel section, the index sub-entry
  await vai_('#persona/P23', '.persona h1');
  const antipa = await p.evaluate(() => ({ h1: document.querySelector('.persona h1').textContent, versi: document.querySelectorAll('.pers-libro .chip').length,
    cron: document.querySelectorAll('.persona .elenco a[href^="#cronologia/"]').length, mc: [...document.querySelectorAll('.pers-libro .chip')].some(a => a.getAttribute('href') === '#Mark.6.14') }));
  verifica('E19: pagina di Erode Antipa: versetti, tavola cronologica', /Erode Antipa/.test(antipa.h1) && antipa.versi >= 20 && antipa.cron >= 4 && antipa.mc, JSON.stringify(antipa));
  await foto(p, '63-persona');
  await vai_('#cronologia/dinastie', '.dinastie');
  verifica('E19: le dinastie portano alle persone', await p.$$eval('.dinastie a.pers-link', xs => new Set(xs.map(a => a.getAttribute('href'))).size) === 34);
  await vai_('#Matt.2.1', '#pannello:not([hidden])');
  verifica('E19: il pannello di Mt 2,1 nomina Erode il Grande', await p.$$eval('#pannello .sez.pers .chip', xs => xs.some(a => a.getAttribute('href') === '#persona/P15')));
  // chronology <-> books
  await vai_('#cronologia/5', '.cron-tavola');
  verifica('E19: la voce «750 ca.: Amos e poco dopo Osea» porta ad Am e Os', await p.$eval('#cv96', x => [...x.querySelectorAll('.cron-chips a')].map(a => a.getAttribute('href')).join(' ')) === '#Amos #Hos');
  await foto(p, '64-cronologia-libri');
  await vai_('#Amos', '.capitoli');
  verifica('E19: il libro di Amos «Nella tavola cronologica»', await p.evaluate(() => [...document.querySelectorAll('.h2')].some(x => x.textContent.startsWith('Nella tavola cronologica'))));
  // codices and versions on the abbreviations page
  await vai_('#introduzione-generale/abbreviazioni', 'table.abbr');
  const cit = await p.evaluate(() => [...document.querySelectorAll('table.abbr tr')].filter(tr => tr.querySelector('.citato')).map(tr => [tr.querySelector('.ab-f').textContent, tr.querySelector('.citato summary').textContent]));
  verifica('E19: versioni e codici «citato in N note»', cit.some(([f, t]) => f === 'LXX' && /\d+ note/.test(t)) && cit.some(([f]) => f.startsWith('P75')), JSON.stringify(cit.slice(0, 6)));
  await foto(p, '65-abbreviazioni');
  // calendar, measures, maps
  await vai_('#calendario', '.festa');
  verifica('E19: calendario: 12 mesi, 8 feste con i riferimenti', (await p.$$('.calendario-mesi tbody tr')).length === 12 && (await p.$$('.festa')).length === 8 && (await p.$$('.festa .chip')).length > 20);
  await foto(p, '66-calendario');
  await vai_('#misure', '.misure-t');
  verifica('E19: misure e monete con il valore', await p.$eval('#mis-cubito', x => x.textContent.includes('45') && x.textContent.includes('cm')));
  await foto(p, '67-misure');
  await vai_('#carte', '.carta-voce');
  verifica('E19: le dieci carte', (await p.$$('.carta-voce')).length === 10);
  // a correction: its source in the preview
  await vai_('#indice-note/91', '.chip.corretto');
  await p.hover('.chip.corretto');
  await p.waitForSelector('#anteprima:not([hidden]) .ap-corr');
  verifica('E19: l’anteprima di una correzione dice la fonte', /CORREZIONI_INDICI/.test(await p.$eval('#anteprima .ap-corr', x => x.textContent)));
  await foto(p, '68-correzione');
  await p.click('#tema');

  // ------------------------------------------------ session F4: quotations in italic (tools/ontologia/virgolette.py)
  await p.evaluate(() => tema('light'));
  const verso_ = id => p.evaluate(id => '#v' + S.vix.get(id), id);
  const corsivo_ = sel => p.$$eval(sel, xs => xs.map(x => [x.textContent, getComputedStyle(x).fontStyle]));
  const t4 = Date.now();
  await vai_('#Gen.1.3', '#pannello:not([hidden]) .pan-testa');
  metriche.lettore_gen_1_ms = Date.now() - t4;
  const g13 = await corsivo_(`${await verso_('Gen.1.3')} .ds`);
  const g13t = await p.$eval(await verso_('Gen.1.3'), x => x.textContent);
  verifica('F4: Gen 1,3 «Sia la luce!» in corsivo, le virgolette diritte', g13.length === 1 && g13[0][0] === 'Sia la luce!' &&
    g13[0][1] === 'italic' && g13t.includes('«Sia la luce!»') && await p.$eval(await verso_('Gen.1.3'), x => getComputedStyle(x).fontStyle) === 'normal',
    JSON.stringify(g13));
  const pan13 = await p.$$eval('#pannello .sez.discorsi li', xs => xs.map(x => x.textContent.replace(/\s+/g, ' ').trim()));
  verifica('F4: il pannello di Gen 1,3 elenca il discorso', pan13.length === 1 && /Gen 1,3/.test(pan13[0]) && /Sia la luce/.test(pan13[0]), pan13.join(' | '));
  const nGen1 = await p.$eval('[data-discorsi] .n', x => +x.textContent);
  verifica('F4: «Discorsi» con il conto del capitolo (Gen 1)', nGen1 >= 10, String(nGen1));
  await p.click('[data-discorsi]');
  const evid = await p.evaluate(id => ({ on: document.body.classList.contains('discorsi'), bg: getComputedStyle(document.querySelector(id + ' .ds')).backgroundColor }), await verso_('Gen.1.3'));
  verifica('F4: il pulsante evidenzia i discorsi', evid.on && evid.bg !== 'rgba(0, 0, 0, 0)', JSON.stringify(evid));
  await foto(p, 'F4-01-gen-1-discorsi');
  await p.evaluate(() => tema('dark'));
  await foto(p, 'F4-01b-gen-1-discorsi-scuro');
  await p.evaluate(() => tema('light'));
  await p.keyboard.press('q');
  verifica('F4: il tasto q spegne l’evidenza', !(await p.evaluate(() => document.body.classList.contains('discorsi'))));
  // a discourse across verses (Dt 5,1-26,19): every word of Dt 5,2-4 italic, and the verse numbers upright
  await vai_('#Deut.5.1', '#pannello:not([hidden]) .sez.discorsi');
  const dt = await p.evaluate(ids => ids.map(id => {
    const v = document.querySelector('#v' + S.vix.get(id)), corpo = [...v.childNodes].filter(n => !(n.classList && (n.classList.contains('vn') || n.classList.contains('mm') || n.classList.contains('md') || n.classList.contains('pg'))));
    const fuori = corpo.map(n => (n.nodeType === 3 ? n.textContent : n.matches('.ds, sup') ? '' : n.textContent)).join('').replace(/[\s«»“”.,;:!?’]/g, '');
    return [id, fuori, getComputedStyle(v.querySelector('.vn')).fontStyle];
  }), ['Deut.5.2', 'Deut.5.3', 'Deut.5.4']);
  verifica('F4: Dt 5: il discorso resta in corsivo da un versetto all’altro', dt.every(([, f, n]) => f === '' && n === 'normal'), JSON.stringify(dt));
  const dt1 = await p.$$eval('#pannello .sez.discorsi li', xs => xs.map(x => x.textContent.replace(/\s+/g, ' ').trim()));
  verifica('F4: Dt 5,1 nel pannello: il discorso di Mosè fino a 26,19 (532 versetti)', dt1.some(t => /Dt 5(,1)?–26(,19)?/.test(t) && /532 versetti/.test(t)), dt1.join(' | '));
  await vai_('#Deut.20.3', '#pannello:not([hidden]) .sez.discorsi');
  const dt20 = await p.$$eval('#pannello .sez.discorsi li', xs => xs.map(x => x.textContent.replace(/\s+/g, ' ').trim()));
  const dt20i = await corsivo_(`${await verso_('Deut.20.3')} .ds`);
  verifica('F4: Dt 20,3: il discorso annidato «dentro il discorso di Dt 5–26», in corsivo', dt20.length === 2 &&
    dt20.some(t => /dentro il discorso di Dt 5(,1)?–26(,19)?/.test(t)) && dt20i.length >= 1 && dt20i.every(x => x[1] === 'italic') && dt20i.some(x => x[0].includes('«')),
    dt20.join(' | '));
  await foto(p, 'F4-02-dt-20-annidato');
  // unbalanced: Sir 16,22 left as printed (no italic run; the third stich in italics, as printed); the reason in the panel
  await vai_('#Sir.16.22', '#pannello:not([hidden]) .sez.discorsi');
  const sir4 = await p.evaluate(id => { const v = document.querySelector(id); return { ds: v.querySelectorAll('.ds').length, em: v.querySelectorAll('em').length, righe: v.querySelectorAll('.r').length, testo: v.textContent }; }, await verso_('Sir.16.22'));
  const sirp = await p.$eval('#pannello .sez.discorsi .sbil', x => x.textContent);
  verifica('F4: Sir 16,22 sbilanciato: lasciato come stampato, il motivo nel pannello', sir4.ds === 0 && sir4.em === 1 && sir4.righe === 3 &&
    sir4.testo.includes("«Chi") && /corsivo/.test(sirp), JSON.stringify(sir4) + ' ' + sirp);
  const sirn = await p.$$eval('#pannello .nota-testo .ds', xs => xs.map(x => [x.textContent, getComputedStyle(x).fontStyle]));
  verifica('F4: nelle note le citazioni (anche \\detto) in corsivo', sirn.some(([t, f]) => t === 'decreto' && f === 'italic'), JSON.stringify(sirn.slice(0, 3)));
  await foto(p, 'F4-03-sir-16-22');
  await vai_('#Amos.7.17', '#pannello:not([hidden]) .sez.discorsi');
  verifica('F4: Am 7,17: la » senza apertura e il motivo (7,14)', /7\.14|7,14/.test(await p.$eval('#pannello .sez.discorsi .sbil', x => x.textContent)));
  // poetry: Sal 2,3, italic on both lines (a margin reference may split a line), no run across the line break
  await vai_('#Ps.2.3', '#pannello:not([hidden])');
  const s23 = await p.evaluate(id => { const v = document.querySelector(id); return { r: [...v.querySelectorAll('.r')].map(r => r.querySelectorAll('.ds').length), fuori: [...v.querySelectorAll('.ds')].filter(x => !x.closest('.r')).length }; }, await verso_('Ps.2.3'));
  verifica('F4: poesia (Sal 2,3): corsivo in ogni rigo, nessun tratto a cavallo dei righi', s23.r.length === 2 && s23.r.every(n => n >= 1) && s23.fuori === 0, JSON.stringify(s23));
  // note calls inside a quotation stay upright (Sal 2,6 «Io» + note)
  await vai_('#Ps.2.6', '#pannello:not([hidden])');
  const nc = await p.evaluate(id => { const v = document.querySelector(id), b = v.querySelector('.nc'); return b ? [getComputedStyle(b).fontStyle, !!b.closest('.ds')] : null; }, await verso_('Ps.2.6'));
  verifica('F4: il richiamo di nota dentro un discorso resta diritto e fuori dal corsivo', nc && nc[0] === 'normal' && !nc[1], JSON.stringify(nc));
  // introductions, front matter, appendices
  await vai_('#intro/intro-pentateuco', '.intro-testo');
  const ni = await p.$$eval('.intro-testo .ds', xs => xs.length);
  verifica('F4: introduzioni: le citazioni in corsivo', ni >= 5, String(ni));
  await vai_('#introduzione-generale/presentazione', '.intro-testo.corsivo');
  const np_ = await p.$$eval('#vista .ds', xs => xs.map(x => x.textContent));
  verifica('F4: Presentazione: le citazioni in corsivo', np_.length >= 5, np_.slice(0, 3).join(' | '));
  await vai_('#indice-note/403', '.voce-ix h1');
  verifica('F4: indice delle note: «Padre nostro» in corsivo', await p.$eval('.voce-ix h1', x => x.querySelector('.ds')?.textContent) === 'Padre nostro');
  await vai_('#introduzione-generale', '.colofone');
  verifica('F4: dati editoriali: «editio princeps» in corsivo', await p.$$eval('.colofone .ds', xs => xs.some(x => x.textContent === 'editio princeps')));
  // the search in the quoted words only
  await vai_('#cerca?q=luce&in=discorsi', '#risultati .r');
  const cl = await p.evaluate(() => ({ esito: document.querySelector('#esito').textContent, gen: [...document.querySelectorAll('#risultati .r a.dove')].some(a => a.getAttribute('href') === '#Gen.1.3'), ds: document.querySelectorAll('#risultati .r .ds mark, #risultati .r .ds').length, tutti: 0 }));
  await vai_('#cerca?q=luce&in=versetti', '#risultati .r');
  cl.tutti = await p.$$eval('#risultati .blocco h3 small', xs => xs.length);
  verifica('F4: cerca «luce» nei discorsi: Gen 1,3, meno versetti che in tutto il testo', cl.gen && cl.ds > 0 && /tra virgolette/.test(cl.esito), JSON.stringify(cl));
  await vai_('#cerca?q=luce&in=discorsi', '#risultati .r');
  await foto(p, 'F4-04-cerca-discorsi');
  // the graph: the quotations in italic in the cards and in the shortened note slips, the tags closed
  await vai_('#grafo/Gen.22.2', '.carta.radice .carta-testo');
  const gc = await p.evaluate(() => {
    const ds = [...document.querySelectorAll('.carta.radice .carta-testo .ds')];
    const fogli = [...document.querySelectorAll('.foglietto')];
    return { radice: ds.map(x => [x.textContent.slice(0, 18), getComputedStyle(x).fontStyle]), carte: document.querySelectorAll('.carta:not(.radice) .carta-testo .ds').length,
      fogli: fogli.filter(f => f.querySelector('.ds')).length, aperti: fogli.filter(f => f.querySelector('.foglietto .foglietto, .ds .ds')).length };
  });
  verifica('grafo: i discorsi in corsivo nelle schede e nei foglietti', gc.radice.length && gc.radice[0][0].startsWith('Prendi tuo figlio') && gc.radice[0][1] === 'italic' && gc.carte > 0 && gc.fogli > 0 && !gc.aperti, JSON.stringify(gc));
  verifica('nessun errore in console (desktop)', errori.length === 0, errori.slice(0, 5).join(' | '));
  await ctx.close();

  // F2: a "%" in the address does not stop the page
  const pc = await apri(await browser.newContext({ viewport: { width: 1200, height: 800 } }), '#cerca?q=100%25');
  await pc.p.waitForFunction(() => document.querySelector('#rq')?.value === '100%');
  verifica('#cerca?q=100%25 si apre (F2)', pc.errori.length === 0, pc.errori.join(' | '));

  // ------------------------------------------------ phone, 390 px, touch
  const tel = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const m = await apri(tel, '#John.3.16');
  metriche.caricamento_390_ms = m.tempo;
  await m.p.waitForSelector('#pannello:not([hidden])');
  const largo = await m.p.evaluate(() => document.documentElement.scrollWidth);
  verifica('390 px: nessuno scorrimento orizzontale', largo <= 390, `scrollWidth ${largo}`);
  await foto(m.p, '14-telefono-pannello');
  const c2 = await m.p.$('#pannello .chip[data-r]');
  await c2.tap();
  await m.p.waitForSelector('#anteprima:not([hidden]) .ap-vai');
  verifica('390 px: tocco mostra l’anteprima con «Vai»', true);
  await foto(m.p, '15-telefono-anteprima');
  await m.p.tap('#anteprima .ap-vai a');
  await m.p.waitForFunction(() => location.hash !== '#John.3.16');
  verifica('390 px: «Vai» segue il rimando', true, await hash(m.p));
  await m.p.evaluate(() => { location.hash = '#'; });
  await m.p.waitForSelector('.libro');
  verifica('390 px: indice senza scorrimento orizzontale', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await foto(m.p, '16-telefono-indice');
  await m.p.evaluate(() => { location.hash = '#grafo/John.3.16'; });
  await m.p.waitForSelector('#ginfo b');
  await m.p.waitForTimeout(600);
  verifica('390 px: grafo senza scorrimento orizzontale', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await foto(m.p, '17-telefono-grafo');
  await m.p.evaluate(() => { location.hash = '#cerca?q=melchisedek'; });
  await m.p.waitForSelector('#esito b');
  await foto(m.p, '18-telefono-cerca');
  await m.p.evaluate(() => { location.hash = '#panoramica'; });
  await m.p.waitForSelector('#mcv');
  verifica('390 px: panoramica senza scorrimento orizzontale', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await foto(m.p, '19-telefono-panoramica');
  const riga = await m.p.$eval('.classifica tr', x => x.getBoundingClientRect().height);
  verifica('390 px: righe dei 50 più rimandati compatte (F10)', riga < 160, `${Math.round(riga)} px`);
  await m.p.evaluate(() => { location.hash = '#panoramica/2Kgs/2Chr'; });
  await m.p.waitForSelector('#coppia table tr');
  const coppia = await m.p.evaluate(() => [document.documentElement.scrollWidth, Math.max(...[...document.querySelectorAll('#coppia .chip')].map(x => x.getBoundingClientRect().right))]);
  verifica('390 px: elenco della coppia nel margine di 16 px (F10)', coppia[0] <= 390 && coppia[1] <= 390 - 15, coppia.join(', '));
  await foto(m.p, '24-telefono-coppia');
  // F14: no blank half page under a chapter when the panel is closed; the handle resizes the sheet
  await m.p.evaluate(() => { location.hash = '#Gen.1'; });
  await m.p.waitForSelector('.testo .v');
  const vuoto = await m.p.evaluate(() => { scrollTo(0, 1e6); return innerHeight - document.querySelector('.fine').getBoundingClientRect().bottom; });
  verifica('390 px: niente pagina vuota a pannello chiuso (F14)', vuoto < 200, `${Math.round(vuoto)} px sotto il capitolo`);
  await m.p.evaluate(() => { location.hash = '#Gen.1.3'; });
  await m.p.waitForSelector('#pannello:not([hidden])');
  const h0 = await m.p.$eval('#pannello', x => x.getBoundingClientRect().height);
  await m.p.tap('#pannello [data-maniglia]');
  const h1 = await m.p.$eval('#pannello', x => x.getBoundingClientRect().height);
  verifica('390 px: la maniglia allarga il pannello (F14)', h1 > h0 + 100, `${Math.round(h0)} → ${Math.round(h1)} px`);
  await foto(m.p, '25-telefono-pannello-alto');
  const tocco = await m.p.$eval('.testo .nc', x => { const r = x.getBoundingClientRect(), a = getComputedStyle(x, '::after'); return [r.width - parseFloat(a.left) - parseFloat(a.right), r.height - parseFloat(a.top) - parseFloat(a.bottom)]; });
  verifica('390 px: richiamo di nota tocca ≥ 24 px (F9)', tocco.every(x => x >= 24), tocco.map(Math.round).join('×'));
  // the dictionary on the phone: the tabs on one line, the entry, the index, the panel section
  await m.p.evaluate(() => { location.hash = '#voce/agnello-di-dio/3?v=Isa.53.7'; });
  await m.p.waitForSelector('.dpar.sel');
  const barra = await m.p.evaluate(() => ({ righe: (y => (Math.max(...y) - Math.min(...y) < 12 ? 1 : 2))([...document.querySelectorAll('.schede a, .comandi')].filter(x => x.offsetParent).map(x => x.getBoundingClientRect().top)), largo: document.documentElement.scrollWidth,
    sel: (() => { const r = document.querySelector('.dpar.sel').getBoundingClientRect(); return r.top >= document.querySelector('.barra').getBoundingClientRect().bottom - 2 && r.top < innerHeight; })() }));
  verifica('390 px: le schede su una riga, voce senza scorrimento orizzontale', barra.righe === 1 && barra.largo <= 390 && barra.sel, JSON.stringify(barra));
  await foto(m.p, '35-telefono-voce');
  await m.p.evaluate(() => { location.hash = '#dizionario'; });
  await m.p.waitForSelector('.dvl');
  verifica('390 px: #dizionario senza scorrimento orizzontale', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await foto(m.p, '36-telefono-dizionario');
  await m.p.evaluate(() => { location.hash = '#John.1.14'; });
  await m.p.waitForSelector('#pannello:not([hidden]) .sez.diz .dvoce');
  await m.p.evaluate(() => document.querySelector('#pannello .sez.diz').scrollIntoView());
  const md390 = await m.p.evaluate(() => { const r = document.querySelector('#v' + S.vix.get('John.1.14') + ' .md').getBoundingClientRect(); return [Math.round(r.left), document.documentElement.scrollWidth]; });
  verifica('390 px: ◊ nel margine, sezione del Dizionario nel pannello', md390[0] >= 8 && md390[1] <= 390, md390.join(', '));
  await foto(m.p, '37-telefono-pannello-diz');
  // the front matter and the appendices on the phone: no horizontal scrolling, the letters inline
  for (const [h, sel, n] of [['#cronologia/9', '.cron-tavola', '50-telefono-cronologia'], ['#indice-note/91', '.voce-ix h1', '51-telefono-voce-indice'],
    ['#temi', '.indice-an .dvl', '52-telefono-temi'], ['#introduzione-generale/abbreviazioni', 'table.abbr', '53-telefono-abbreviazioni'],
    ['#introduzione-generale/presentazione', '.intro-testo', '54-telefono-presentazione'], ['#cronologia/dinastie', '.dinastie', '55-telefono-dinastie']]) {
    await m.p.evaluate(x => { location.hash = x; }, h);
    await m.p.waitForSelector(sel);
    verifica(`390 px: ${h} senza scorrimento orizzontale`, await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
    await foto(m.p, n);
  }
  await m.p.evaluate(() => { location.hash = '#Lam.3.1'; });
  await m.p.waitForSelector('#pannello:not([hidden])');
  const acr390 = await m.p.evaluate(() => { const a = document.querySelector('#v' + S.vix.get('Lam.3.1') + ' .acr').getBoundingClientRect(); return [Math.round(a.left), Math.round(a.right), document.documentElement.scrollWidth]; });
  verifica('390 px: lettera acrostica nel rigo, dentro lo schermo', acr390[0] >= 16 && acr390[1] <= 390 - 16 && acr390[2] <= 390, acr390.join(', '));
  await m.p.evaluate(() => { location.hash = '#Josh.14.6'; });
  await m.p.waitForSelector('#pannello:not([hidden]) .sez.ix');
  await m.p.evaluate(() => document.querySelector('#pannello .sez.ix').scrollIntoView());
  verifica('390 px: «Nell’indice delle note» nel pannello', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await foto(m.p, '56-telefono-pannello-indice');
  // session F2 on the phone: the filters wrap (E8), the graph's controls are a closed sheet (E9), the Appendici tab
  await m.p.evaluate(() => { location.hash = '#cerca?q=amore'; });
  await m.p.waitForSelector('.segmenti button');
  const seg = await m.p.$$eval('.ricerca-campi .segmenti button', xs => xs.map(b => b.getBoundingClientRect().right));
  verifica('E8: 390 px, i filtri della ricerca dentro lo schermo', Math.max(...seg) <= 390 - 15, seg.map(Math.round).join(', '));
  await foto(m.p, '70-telefono-cerca');
  await m.p.evaluate(() => { location.hash = '#grafo/John.3.16'; });
  await m.p.waitForSelector('.carta');
  const gr = await m.p.evaluate(() => ({ tela: Math.round(document.querySelector('#tela').getBoundingClientRect().height), lato: Math.round(document.querySelector('.grafo-lato').getBoundingClientRect().height) }));
  verifica('E9: 390 px, la tela del grafo occupa lo schermo, i comandi chiusi', gr.tela > 600 && gr.lato < 60, JSON.stringify(gr));
  await foto(m.p, '71-telefono-grafo');
  await m.p.tap('[data-lato]');
  await m.p.waitForTimeout(100);
  verifica('E9: 390 px, i comandi si aprono', await m.p.$eval('.grafo-lato', x => x.getBoundingClientRect().height > 200));
  await m.p.evaluate(() => { location.hash = '#appendici'; });
  await m.p.waitForSelector('#vista .apparato');
  const tab390 = await m.p.evaluate(() => ({ righe: (y => (Math.max(...y) - Math.min(...y) < 12 ? 1 : 2))([...document.querySelectorAll('.schede a, .comandi')].filter(x => x.offsetParent).map(x => x.getBoundingClientRect().top)), largo: document.documentElement.scrollWidth, attiva: document.querySelector('.schede a.attiva')?.dataset.vista }));
  verifica('E5: 390 px, «Appendici» tra le schede su una riga', tab390.righe === 1 && tab390.largo <= 390 && tab390.attiva === 'apparati', JSON.stringify(tab390));
  await foto(m.p, '72-telefono-appendici');
  for (const [h, sel, n] of [['#persona/P15', '.persona h1', '73-telefono-persona'], ['#misure', '.misure-t', '74-telefono-misure'], ['#calendario', '.festa', '75-telefono-calendario'], ['#indice-note/38', '.anche-in', '76-telefono-anche-in']]) {
    await m.p.evaluate(x => { location.hash = x; }, h);
    await m.p.waitForSelector(sel);
    verifica(`390 px: ${h} senza scorrimento orizzontale`, await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
    await foto(m.p, n);
  }
  // F4: the reader with its quotations on the phone, light and dark, highlighted
  await m.p.evaluate(() => { location.hash = '#Gen.3'; });
  await m.p.waitForSelector('#vista .lettore .ds');
  verifica('F4: 390 px, Gen 3 con i discorsi senza scorrimento orizzontale', await m.p.evaluate(() => document.documentElement.scrollWidth) <= 390);
  await m.p.tap('[data-discorsi]');
  await foto(m.p, 'F4-11-telefono-gen-3-chiaro');
  await m.p.evaluate(() => tema('dark'));
  await foto(m.p, 'F4-12-telefono-gen-3-scuro');
  await m.p.evaluate(() => { tema('light'); discorsi_(false); });
  verifica('nessun errore in console (390 px)', m.errori.length === 0, m.errori.slice(0, 5).join(' | '));
  await tel.close();
} finally {
  await browser.close();
}
const falliti = esiti.filter(x => !x[1]);
console.log(JSON.stringify(metriche, null, 1));
console.log(`${esiti.length - falliti.length}/${esiti.length} verifiche passate`);
process.exit(falliti.length ? 1 : 0);
