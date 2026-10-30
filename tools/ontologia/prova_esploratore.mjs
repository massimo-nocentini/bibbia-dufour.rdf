// Headless test of ontologia/esplora.html, opened from file:// in Chromium.
//
// usage: node tools/ontologia/prova_esploratore.mjs --pw <dir with node_modules/playwright-core> [--foto <dir>]
//
// playwright-core is not a dependency of the repository: install it anywhere
// (npm install playwright-core@1.64.0, which drives the cached chromium 1248) and pass
// that folder with --pw. Checks the load time, the console, the reader and the verse
// panel (Gv 3,16 -> note -> a margin reference -> back), the search with and without
// accents, the graph, the matrix, the dark theme, the keyboard and a 390px viewport.
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
  verifica('carica in meno di 3 s', tempo < 3000, `${tempo} ms (dati ${interno.dati} ms, indici ${interno.indici} ms)`);
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
  await p.evaluate(() => { location.hash = '#grafo/Gen.25.5'; });
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
  const top = await p.$$eval('.classifica tr', xs => xs.length);
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
    return ['--foglio', '--carta', '--sopra'].map(bg => cr('var(--tenue)', `var(${bg})`).toFixed(2));
  });
  verifica('contrasto del testo tenue ≥ 4,5 (F8, chiaro)', contrasto.every(x => +x >= 4.5), contrasto.join(', '));
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
    return [cr('var(--tenue)', 'var(--foglio)'), cr('var(--tenue)', 'var(--carta)'), cr('var(--rubrica)', 'var(--sel)')].map(x => x.toFixed(2));
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
  await p.click('#tema');
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
  verifica('nessun errore in console (390 px)', m.errori.length === 0, m.errori.slice(0, 5).join(' | '));
  await tel.close();
} finally {
  await browser.close();
}
const falliti = esiti.filter(x => !x[1]);
console.log(JSON.stringify(metriche, null, 1));
console.log(`${esiti.length - falliti.length}/${esiti.length} verifiche passate`);
process.exit(falliti.length ? 1 : 0);
