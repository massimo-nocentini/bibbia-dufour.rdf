// Esploratore dei versetti: one offline page over the verse graph of the Bibbia di Gerusalemme.
// The data (built by tools/ontologia/esploratore.py) is gzip+base64 JSON in <script id="dati">.
'use strict';

const T0 = performance.now();
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s).replace(/[&<>"']/g, c => ESC[c]);
const num = n => n.toLocaleString('it-IT');
const memo = {
  get(k) { try { return localStorage.getItem('esplora.' + k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem('esplora.' + k, v); } catch (e) { /* private mode */ } },
};

let D, V;          // payload and its verse columns
const S = {};      // derived indices and UI state

// relations of the margin references, in display order; 'keynote' is a "+" reference
const REL = {
  parallel: { nome: 'Paralleli', seg: '‖', col: '--r-parallel', entr: 'Paralleli', dash: [] },
  'quoted-later': { nome: 'Citato in', seg: '↗', col: '--r-quoted', entr: 'Citano questo passo', dash: [] },
  doublet: { nome: 'Doppioni', seg: '=', col: '--r-doublet', entr: 'Doppioni', dash: [] },
  keynote: { nome: 'Nota chiave', seg: '+', col: '--r-keynote', entr: 'Rinviano qui per la nota chiave', dash: [2, 3] },
  related: { nome: 'Affini', seg: '·', col: '--r-related', txt: '--secondo', entr: 'Affini', dash: [] },
  cites: { nome: 'Citazioni nelle note', seg: '§', col: '--r-cites', txt: '--secondo', entr: 'Citato nelle note', dash: [5, 4] },
  numbering: { nome: 'Altra numerazione', seg: '#', col: '--r-related', txt: '--secondo', entr: '', dash: [] },
};
const ORDINE_REL = ['parallel', 'quoted-later', 'doublet', 'keynote', 'related', 'cites'];

// ---------------------------------------------------------------- data

async function carica() {
  const b64 = $('#dati').textContent.trim();
  let bin;
  if (Uint8Array.fromBase64) bin = Uint8Array.fromBase64(b64);
  else {
    const s = atob(b64);
    bin = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) bin[i] = s.charCodeAt(i);
  }
  const flusso = new Blob([bin]).stream().pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(flusso).text());
}

function indici() {
  V = D.V;
  const n = V.id.length;
  S.n = n;
  S.vix = new Map(V.id.map((id, i) => [id, i]));
  S.vb = new Uint8Array(n);
  S.vc = new Uint16Array(n);
  S.osis = new Map();
  D.libri.forEach((b, k) => {
    S.osis.set(b.o, k);
    b.c.forEach(([, s, e], c) => { for (let i = s; i <= e; i++) { S.vb[i] = k; S.vc[i] = c; } });
  });
  const lista = () => Array.from({ length: n }, () => null);
  S.noteAt = lista();
  D.note.forEach((x, k) => (S.noteAt[x[0]] = S.noteAt[x[0]] || []).push(k));
  S.mrefAt = lista();
  D.mref.forEach((x, k) => (S.mrefAt[x[0]] = S.mrefAt[x[0]] || []).push(k));
  S.mlOf = D.mref.map(() => []);
  D.ml.forEach((x, k) => S.mlOf[x[0]].push(k));
  S.ncOf = D.note.map(() => []);
  D.nc.forEach((x, k) => S.ncOf[x[0]].push(k));
  S.periAt = new Map();
  D.peri.forEach((p, k) => { if (!S.periAt.has(p[0])) S.periAt.set(p[0], []); S.periAt.get(p[0]).push(k); });
  S.divAt = new Map();
  D.div.forEach((d, k) => { if (!S.divAt.has(d[0])) S.divAt.set(d[0], []); S.divAt.get(d[0]).push(k); });
  // in-degree: margin references (resolved, not other numberings) naming a passage that includes the verse
  const diff = new Int32Array(n + 1);
  D.ml.forEach(l => {
    if (!vivo(l)) return;
    const r = l[2];
    for (let j = 0; j < r.length; j += 2) { diff[r[j]]++; diff[r[j + 1] + 1]--; }
  });
  S.indeg = new Int32Array(n);
  let c = 0;
  for (let i = 0; i < n; i++) { c += diff[i]; S.indeg[i] = c; }
  S.ultimoAT = D.libri.findIndex(b => b.T === 'NT') - 1;
}

const relNome = l => (l[4] ? 'keynote' : D.meta.relazioni[l[1]]);
const vivo = l => l[9] <= 1 && l[2].length > 0 && l[1] <= 3;   // resolved/partial, a real reference
function contiene(r, i) {
  for (let j = 0; j < r.length; j += 2) if (r[j] <= i && i <= r[j + 1]) return true;
  return false;
}
function sovrappone(r, a, b) {
  for (let j = 0; j < r.length; j += 2) if (r[j] <= b && a <= r[j + 1]) return true;
  return false;
}
const ampiezza = r => { let s = 0; for (let j = 0; j < r.length; j += 2) s += r[j + 1] - r[j] + 1; return s; };
const calore = d => (d >= 21 ? 5 : d >= 11 ? 4 : d >= 6 ? 3 : d >= 3 ? 2 : d >= 1 ? 1 : 0);

// ---------------------------------------------------------------- references

const parti = i => V.id[i].split('.');                    // [osis, chapter, verse]
const capDi = i => parti(i)[1];
const versoDi = i => parti(i).slice(2).join('.');
const unCapitolo = b => D.libri[b].c.length === 1;
function inizioCap(i) { return i === 0 || S.vb[i - 1] !== S.vb[i] || capDi(i - 1) !== capDi(i); }
function fineCap(i) { return i === S.n - 1 || S.vb[i + 1] !== S.vb[i] || capDi(i + 1) !== capDi(i); }
function cv(i, conCap = true) {
  const c = capDi(i), v = versoDi(i);
  if (c === 'Prol') return 'prol. ' + v;
  return conCap && !unCapitolo(S.vb[i]) ? c + ',' + v : v;
}
function rif(a, b = a, conSigla = true) {
  const ba = S.vb[a], bb = S.vb[b];
  const sig = conSigla ? D.libri[ba].s + ' ' : '';
  if (a === b) return sig + cv(a);
  if (ba !== bb) return sig + cv(a) + ' – ' + D.libri[bb].s + ' ' + cv(b);
  if (!unCapitolo(ba) && inizioCap(a) && fineCap(b) && capDi(a) !== 'Prol') {
    return sig + (capDi(a) === capDi(b) ? capDi(a) : capDi(a) + '–' + capDi(b));
  }
  if (capDi(a) === capDi(b)) return sig + cv(a) + '–' + versoDi(b);
  return sig + cv(a) + '–' + cv(b);
}
function rifRuns(r) {
  const out = [];
  for (let j = 0; j < r.length; j += 2) {
    const stesso = j > 0 && S.vb[r[j]] === S.vb[r[j - 2]];
    out.push(rif(r[j], r[j + 1], !stesso));
  }
  return out.join('; ');
}
const runsAttr = r => { const o = []; for (let j = 0; j < r.length; j += 2) o.push(r[j] + '-' + r[j + 1]); return o.join(','); };
function hashVerso(a, b = a) {
  if (a === b) return '#' + V.id[a];
  if (S.vb[a] === S.vb[b] && capDi(a) === capDi(b)) return '#' + V.id[a] + '-' + versoDi(b);
  return '#' + V.id[a] + '-' + V.id[b];
}

// "Gv 3,16", "Sal 23,1-4", "Gen 1", "1 Cor 13", "Est 4,17a", "Gd 3", "John.3.16", and the forms
// of the BJ margins and notes: "Gen 2,4b", "Mt 5,3s", "Mt 5,3ss", "Dt 7,9.12", "Gen 1,1; 2,4",
// "Gen 1,1-2,4a", "Sir prol 3", "Sir prologo", "I Cor 13", "Prima Corinzi 13", "Cantico dei Cantici 2"
function chiaveLibro(s) {
  return s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[\s.]/g, '');
}
const ORDINALI = [[/^(?:prim[oa]|i)\s+/i, '1 '], [/^(?:second[oa]|ii)\s+/i, '2 '], [/^(?:terz[oa]|iii)\s+/i, '3 ']];
function tabellaLibri() {
  const m = new Map();
  D.libri.forEach((b, k) => {
    for (const nome of [b.o, b.s, b.t, b.tl, b.n]) {
      const c = chiaveLibro(nome);
      if (!m.has(c)) m.set(c, k);
    }
  });
  for (const [k, o] of [['est', 'Esth'], ['estgr', 'EsthGr'], ['ester', 'Esth'], ['salmo', 'Ps'], ['sal', 'Ps'],
    ['cantico', 'Song'], ['qoelet', 'Eccl']]) m.set(k, S.osis.get(o));
  return m;
}
function trovaVerso(b, cap, v) {
  const o = D.libri[b].o;
  const prova = x => S.vix.get(o + '.' + cap + '.' + x) ?? (o === 'Esth' ? S.vix.get('EsthGr.' + cap + '.' + x) : undefined);
  let i = prova(v);
  if (i === undefined && /[a-z]$/.test(v)) i = prova(v.replace(/[a-z]+$/, ''));   // 2,4b: a part of verse 4
  return i;
}
function trovaCap(b, cap) {
  let c = D.libri[b].c.findIndex(x => String(x[0]) === String(cap));
  if (c < 0 && D.libri[b].o === 'Esth') return trovaCap(S.osis.get('EsthGr'), cap);
  return c < 0 ? null : [b, c];
}
function fineCapIndice(i) { let j = i; while (!fineCap(j)) j++; return j; }
function finePericope(i) {             // "ss": to the end of the pericope, within the chapter
  let z = fineCapIndice(i);
  for (const p of D.peri) if (p[0] <= i && i <= p[1]) z = Math.min(z, p[1]);
  return z;
}
function libroDi(testo) {
  let t = testo.trim();
  for (const [re, n] of ORDINALI) t = t.replace(re, n);
  S.libriTab = S.libriTab || tabellaLibri();
  const tok = t.split(' ');
  let j = tok.findIndex((x, k) => (k > 0 || !/^[1-3]$/.test(x)) && /^(\d|prol)/i.test(x));
  if (j < 0) j = tok.length;
  if (j === 0) return null;
  const b = S.libriTab.get(chiaveLibro(tok.slice(0, j).join(' ')));
  return b === undefined ? null : { b, resto: tok.slice(j).join('') };
}
// one reference without its book: "3,16", "23,1-4", "1", "2,4b-25", "prol3", "5,3ss"; ctx = the chapter in force
function versoEsatto(b, cap, v) {
  const o = D.libri[b].o;
  return S.vix.get(o + '.' + cap + '.' + v) ?? (o === 'Esth' ? S.vix.get('EsthGr.' + cap + '.' + v) : undefined);
}
function stacca(b, cap, x) {
  // "3s" -> ["3", "s"] ("and the next"), "3ss", "3p"; but Est 4,17s is a verse
  const m = x && x.match(/^(\d+)([a-z]*)$/);
  if (!m || !m[2] || versoEsatto(b, cap, x) !== undefined) return [x, ''];
  const f = m[2].match(/(ss|s|p)$/);
  return f ? [m[1] + m[2].slice(0, -f[1].length), f[1]] : [x, ''];
}
function leggiParte(b, resto, ctx) {
  const L = D.libri[b], sb = L.s;
  resto = resto.replace(/:/g, ',').replace(/^prol(?:ogo)?\.?,?/i, 'Prol,').replace(/,$/, '');
  const r = resto.match(/^([0-9]+[a-z]*|Prol)(?:,([0-9]+[a-z]*))?(?:-([0-9]+[a-z]*)(?:,([0-9]+[a-z]*))?)?$/i);
  if (!r) return { errore: `«${sb} ${resto}» non è un riferimento che so leggere` };
  let [, c1, v1, x2, v2] = r;
  if (/^prol$/i.test(c1)) c1 = 'Prol';
  if (!v1 && c1 !== 'Prol' && (unCapitolo(b) || ctx && ctx.verso)) {
    // "Gd 3", "Abd 15-21": verses of the only chapter; "Dt 7,9.12": after a verse, a verse
    v1 = c1; c1 = unCapitolo(b) ? L.c[0][0] : ctx.cap;
    if (x2 && !v2) { v2 = x2; x2 = c1; }
  }
  if (/[a-z]/.test(c1) && c1 !== 'Prol') return { errore: `«${sb} ${resto}» non è un riferimento che so leggere` };
  let suff = '';
  if (v2) [v2, suff] = stacca(b, x2, v2);
  else if (x2 && v1) [x2, suff] = stacca(b, c1, x2);
  else if (v1) [v1, suff] = stacca(b, c1, v1);
  if (!v1) {
    const c = trovaCap(b, c1);
    if (!c) return { errore: `${sb} ${c1}: capitolo inesistente (${L.t} ne ha ${L.c.filter(x => x[0] !== 'Prol').length})` };
    const [b0, c0] = c, a = D.libri[b0].c[c0][1];
    let z = D.libri[b0].c[c0][2];
    if (x2) {
      const c2 = trovaCap(b, x2);
      if (!c2) return { errore: `${sb} ${x2}: capitolo inesistente` };
      z = D.libri[c2[0]].c[c2[1]][2];
    }
    if (!x2 && !ctx) return { b: b0, c: c0, cap: c1 };
    return { a, z, cap: c1 };
  }
  const a = trovaVerso(b, c1, v1);
  if (a === undefined) {
    const c = trovaCap(b, c1);
    if (!c) return { errore: `${sb} ${c1}: capitolo inesistente` };
    const n = D.libri[c[0]].c[c[1]];
    return { errore: `${sb} ${c1 === 'Prol' ? 'prol.' : c1},${v1}: versetto inesistente (il ${c1 === 'Prol' ? 'prologo' : 'capitolo'} ne ha ${n[2] - n[1] + 1})` };
  }
  let z = a;
  if (v2 || x2) {
    z = v2 ? trovaVerso(S.vb[a], x2, v2) : trovaVerso(S.vb[a], capDi(a), x2);
    if (z === undefined) return { errore: `${sb} ${v2 ? x2 + ',' + v2 : c1 + ',' + x2}: versetto inesistente` };
    if (z < a) return { errore: `${sb} ${resto}: intervallo rovesciato` };
  }
  if (suff === 's' && !fineCap(z)) z++;
  else if (suff === 'ss') z = finePericope(z);
  return { a, z, cap: capDi(z), verso: true };
}
function leggiRif(testo) {
  let s = testo.trim().replace(/[–—]/g, '-').replace(/\s+/g, ' ').replace(/\s*-\s*/g, '-')
    .replace(/^([1-3]?\s?[A-Za-zÀ-ÿ]+)(?=\d)/, '$1 ');                 // "Gv3,16"
  if (!s) return null;
  if (S.vix.has(s)) return { a: S.vix.get(s) };
  const dot = s.split('.');
  if (S.osis.has(dot[0]) && dot.length <= 3 && !/\s/.test(s)) {
    s = dot[0] + ' ' + (dot[1] || '') + (dot[2] ? ',' + dot[2] : '');
  }
  const parti = s.split(/\s*;\s*/).filter(Boolean);
  const testa = libroDi(parti[0].replace(/^([1-3]?\s?[A-Za-zÀ-ÿ]+)\.(?=\s|\d)/, '$1'));
  if (!testa) return null;
  const { b } = testa;
  if (!testa.resto && parti.length === 1) return { b };
  // ";" separates references of the same book (or of another one named), "." verses of one chapter
  const pezzi = [];
  let ctx = null, libro = b;
  for (let k = 0; k < parti.length; k++) {
    let resto = k ? parti[k].replace(/\s/g, '') : testa.resto;
    if (k) {
      const altro = libroDi(parti[k]);
      if (altro && altro.resto) { libro = altro.b; resto = altro.resto; ctx = null; }
      else ctx = ctx && { cap: ctx.cap };              // after ";" a bare number is a chapter
    }
    const punti = resto.split('.');
    for (let j = 0; j < punti.length; j++) {
      const r = leggiParte(libro, punti[j], j ? ctx : (k ? ctx : null));
      if (r.errore) return r;
      pezzi.push(r);
      ctx = { cap: r.cap, verso: !!r.verso };
    }
  }
  const [primo, ...altri] = pezzi;
  if (!altri.length) return primo;
  return Object.assign({}, primo.a === undefined ? { a: D.libri[primo.b].c[primo.c][1], z: D.libri[primo.b].c[primo.c][2] } : primo,
    { e: altri.map(x => x.a === undefined ? [D.libri[x.b].c[x.c][1], D.libri[x.b].c[x.c][2]] : [x.a, x.z]) });
}
function hashDi(r) {
  if (r.a !== undefined) {
    const e = r.e ? '?e=' + r.e.map(([a, z]) => (a === z ? V.id[a] : V.id[a] + '-' + V.id[z])).join(',') : '';
    return hashVerso(r.a, r.z === undefined ? r.a : r.z) + e;
  }
  if (r.c !== undefined) return '#' + D.libri[r.b].o + '.' + D.libri[r.b].c[r.c][0];
  return '#' + D.libri[r.b].o;
}

// ---------------------------------------------------------------- plain text and search normalisation

const testoPiano = h => h.replace(/<br>/g, ' / ').replace(/<[^>]+>/g, '');
const CARATTERI = new Map();
function normCar(c) {
  let r = CARATTERI.get(c);
  if (r === undefined) {
    r = c.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
    if (c === '’' || c === '‘' || c === 'ʼ') r = "'";
    r = r.length === 1 ? r : (r[0] || ' ');
    CARATTERI.set(c, r);
  }
  return r;
}
function normalizza(s) {         // one output char per input char, so offsets map back to s
  const f = s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase().replace(/[’‘ʼ]/g, "'");
  if (f.length === s.length) return f;
  let o = '';
  for (const c of s) o += c.length === 2 ? normCar(c) + ' ' : normCar(c);
  return o;
}
function indiceRicerca() {
  if (S.cerca) return S.cerca;
  const t = performance.now();
  const vp = V.h.map(testoPiano), np = D.note.map(x => testoPiano(x[5]));
  S.cerca = { vp, vn: vp.map(normalizza), np, nn: np.map(normalizza), ms: 0 };
  S.cerca.ms = performance.now() - t;
  return S.cerca;
}
function evidenzia(testo, norm, termini, max = 220) {
  const segni = [];
  for (const t of termini) for (const m of norm.matchAll(t.g)) segni.push([m.index, m.index + m[0].length]);
  segni.sort((x, y) => x[0] - y[0]);
  const fusi = [];
  for (const s of segni) {
    if (fusi.length && s[0] <= fusi[fusi.length - 1][1]) fusi[fusi.length - 1][1] = Math.max(fusi[fusi.length - 1][1], s[1]);
    else fusi.push(s.slice());
  }
  let da = 0, a = testo.length;
  if (testo.length > max && fusi.length) {
    da = Math.max(0, fusi[0][0] - Math.floor(max * 0.35));
    a = Math.min(testo.length, da + max);
    const sp = testo.lastIndexOf(' ', da + 12);
    if (da > 0 && sp > da - 20 && sp >= 0) da = sp + 1;
  } else if (testo.length > max) a = max;
  let o = da > 0 ? '…' : '', p = da;
  for (const [x, y] of fusi) {
    if (y <= da || x >= a) continue;
    o += esc(testo.slice(p, Math.max(p, x))) + '<mark>' + esc(testo.slice(Math.max(x, da), Math.min(y, a))) + '</mark>';
    p = Math.min(y, a);
  }
  o += esc(testo.slice(p, a)) + (a < testo.length ? '…' : '');
  return o;
}

// ---------------------------------------------------------------- routing

function vai(h, sostituisci = false) {
  if (sostituisci) { history.replaceState(null, '', h); instrada(); } else if (location.hash === h) instrada(); else location.hash = h;
}
// the hash is split on "?" and "&" first, then each part is decoded once (a "%", "&" or "?"
// typed in a search stays what it is)
function dec(x) { try { return decodeURIComponent(x); } catch (e) { return x; } }
function parametri(s) {
  const p = {};
  (s || '').split('&').forEach(kv => {
    const k = kv.indexOf('=');
    if (k > 0) p[dec(kv.slice(0, k))] = dec(kv.slice(k + 1).replace(/\+/g, ' '));
    else if (kv) p[dec(kv)] = '';
  });
  return p;
}
function viaAttuale() {
  const raw = location.hash.slice(1), q = raw.indexOf('?');
  return { via: dec(q < 0 ? raw : raw.slice(0, q)), query: q < 0 ? '' : raw.slice(q + 1) };
}
function instrada() {
  nascondiAnteprima();
  const { via, query } = viaAttuale();
  let vista = 'indice';
  if (!via) mostraIndice();
  else if (via === 'cerca') { vista = 'cerca'; mostraCerca(parametri(query)); }
  else if (via === 'panoramica' || via.startsWith('panoramica/')) { vista = 'panoramica'; mostraPanoramica(via.split('/').slice(1)); }
  else if (via === 'grafo' || via.startsWith('grafo/')) { vista = 'grafo'; mostraGrafo(via.slice(6), parametri(query)); }
  else if (via.startsWith('intro/')) { vista = 'intro'; mostraIntro(via.slice(6)); }
  else vista = mostraRif(via, parametri(query));
  $$('.schede a').forEach(a => a.classList.toggle('attiva', a.dataset.vista === vista ||
    (vista === 'lettore' && a.dataset.vista === 'indice')));
  S.vista = vista;
  if (vista !== 'lettore') chiudiPannello(false);
  annuncia(document.title);
}
function annuncia(t) { const a = $('#annuncio'); if (a) a.textContent = t; }
function mostraRif(via, par = {}) {
  const [sx, dx] = via.split('-');
  const p = sx.split('.');
  const b = S.osis.get(p[0]);
  if (b === undefined) { nonTrovato(via); return 'indice'; }
  if (p.length === 1) { mostraLibro(b); return 'indice'; }
  if (p.length === 2) {
    const c = D.libri[b].c.findIndex(x => String(x[0]) === p[1]);
    if (c < 0) { nonTrovato(via); return 'indice'; }
    mostraCapitolo(b, c);
    selezionaVerso(null);
    return 'lettore';
  }
  const a = S.vix.get(sx);
  if (a === undefined) { nonTrovato(via); return 'indice'; }
  let z = a;
  if (dx) z = S.vix.get(dx.includes('.') ? dx : p[0] + '.' + p[1] + '.' + dx) ?? a;
  mostraCapitolo(S.vb[a], S.vc[a]);
  selezionaVerso(a, z, true);
  anche(par.e);
  return 'lettore';
}
function anche(e) {
  // the other references of a list typed in the box ("Dt 7,9.12", "Gen 1,1; 2,4"): highlighted
  // when they are in this chapter, and linked above the text
  $('#vista .anche')?.remove();
  if (!e) return;
  const runs = e.split(',').map(x => x.split('-').map(y => S.vix.get(y))).filter(r => r[0] !== undefined)
    .map(r => [r[0], r[1] ?? r[0]]);
  if (!runs.length) return;
  for (const [a, z] of runs) for (let i = a; i <= z; i++) $('#v' + i)?.classList.add('int');
  const link = runs.map(([a, z]) => `<a href="${hashVerso(a, z)}" data-r="${a}-${z}">${esc(rif(a, z))}</a>`).join(' · ');
  $('#vista .testo')?.insertAdjacentHTML('beforebegin', `<p class="anche">Anche: ${link}</p>`);
}
function nonTrovato(via) {
  pagina(`<div class="pagina"><h1>Riferimento non trovato</h1><p class="sotto">«${esc(via)}» non corrisponde a un libro, un capitolo o un versetto.</p><p><a href="#">Torna all’indice dei libri</a></p></div>`);
}
function pagina(html) {
  const m = $('#vista');
  m.innerHTML = html;
  S.capitolo = null;
  window.scrollTo(0, 0);
}

// ---------------------------------------------------------------- index of books

function mostraIndice() {
  const t = D.meta.totali, r = D.meta.riepilogo;
  const col = T => {
    let h = `<section class="testamento"><h2>${T === 'AT' ? 'Antico Testamento' : 'Nuovo Testamento'}</h2>`;
    D.vol.forEach(([nome, titolo], v) => {
      const libri = D.libri.map((b, k) => [b, k]).filter(([b]) => b.v === v && b.T === T);
      if (!libri.length) return;
      const intro = D.intro.map((x, k) => [x, k]).filter(([x]) => x[3] === v && x[4].length !== 1);
      h += `<div class="volume"><h3>${esc(titolo)}${intro.map(([x]) => ` <a href="#intro/${esc(x[0])}">introduzione</a>`).join('')}</h3><div class="libri">`;
      for (const [b] of libri) h += `<a class="libro" href="#${b.o}" title="${esc(b.t)}"><b>${esc(b.n)}</b><span>${esc(b.s)} · ${b.c.length}</span></a>`;
      h += '</div></div>';
    });
    return h + '</section>';
  };
  pagina(`<div class="pagina">
    <div class="sopratitolo">CEI 2008 · note e rimandi a margine della Bible de Jérusalem</div>
    <h1>La Bibbia di Gerusalemme</h1>
    <p class="sotto">Ogni versetto è un nodo: le sue note, i rimandi a margine che partono da lui e quelli che lo raggiungono. Scrivi un riferimento in alto (<a href="#John.3.16">Gv 3,16</a>, <a href="#Ps.23.1-4">Sal 23,1-4</a>) oppure una parola da cercare.</p>
    <div class="numeri">
      <span><b>${num(t.books - 1)}</b> libri</span><span><b>${num(t.chapters)}</b> capitoli</span>
      <span><b>${num(t.verses)}</b> versetti</span><span><b>${num(t.notes)}</b> note</span>
      <span><b>${num(r.mref_items)}</b> rimandi a margine <small>in ${num(r.mref_entries)} voci</small></span>
      <span><b>${num(r.note_citations + r.intro_citations)}</b> citazioni in note e introduzioni</span>
    </div>
    <div class="testamenti">${col('AT')}${col('NT')}</div></div>`);
  document.title = 'Esploratore dei versetti';
}

// ---------------------------------------------------------------- book page

function mostraLibro(b) {
  const L = D.libri[b];
  const s = L.c[0][1], e = L.c[L.c.length - 1][2];
  let nn = 0, nm = 0;
  for (let i = s; i <= e; i++) { nn += (S.noteAt[i] || []).length; nm += (S.mrefAt[i] || []).length; }
  const intros = D.intro.filter(x => x[4].includes(b));
  const voci = [];
  D.div.forEach(d => { if (S.vb[d[0]] === b) voci.push([d[0], 0, d]); });
  D.peri.forEach(p => { if (S.vb[p[0]] === b) voci.push([p[0], 1, p]); });
  voci.sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  const schema = voci.map(([i, tipo, x]) => tipo === 0
    ? `<li class="l${Math.min(x[2], 3)}"><a href="${hashVerso(x[0])}">${x[3]}</a></li>`
    : `<li class="peri"><a href="${hashVerso(x[0])}">${x[2]}</a><small>${esc(rif(x[0], x[1], false))}</small></li>`).join('');
  pagina(`<div class="pagina">
    <div class="sopratitolo">${esc(D.vol[L.v][1])} · ${L.T === 'AT' ? 'Antico' : 'Nuovo'} Testamento</div>
    <h1>${esc(L.tl)}</h1>
    <p class="sotto">${esc(L.s)} · ${num(L.c.length)} ${L.c.length === 1 ? 'capitolo' : 'capitoli'} · ${num(e - s + 1)} versetti · ${num(nn)} note · ${num(nm)} rimandi a margine</p>
    ${intros.map(x => `<a class="intro-link" href="#intro/${esc(x[0])}">Introduzione: ${esc(x[1])}</a>`).join('')}
    <div class="h2">Capitoli</div>
    <div class="capitoli">${L.c.map(c => `<a href="#${L.o}.${c[0]}">${c[0] === 'Prol' ? 'Prol.' : c[0]}</a>`).join('')}</div>
    ${schema ? `<div class="h2">Struttura</div><ul class="schema">${schema}</ul>` : ''}
  </div>`);
  document.title = L.t + ' · Esploratore dei versetti';
}

// ---------------------------------------------------------------- reader

function chiamate(i, lettere) {
  // the verse HTML with a superscript letter where each note is called
  let h = V.h[i];
  const note = (S.noteAt[i] || []).map(k => [D.note[k][1], k]).sort((x, y) => x[0] - y[0] || x[1] - y[1]);
  const segni = note.map(([o, k]) => [o, `<sup><button type="button" class="nc" data-n="${k}" title="Nota ${esc(D.note[k][3] + D.note[k][2])}" aria-label="Nota ${esc(D.note[k][3] + D.note[k][2])}">${lettere(k)}</button></sup>`]);
  for (let j = segni.length - 1; j >= 0; j--) h = h.slice(0, segni[j][0]) + segni[j][1] + h.slice(segni[j][0]);
  return h;
}
function segnoMargine(i) {
  const ms = S.mrefAt[i];
  if (!ms) return '';
  const rel = new Set();
  let n = 0;
  for (const m of ms) for (const k of S.mlOf[m]) { rel.add(relNome(D.ml[k])); n++; }
  const seg = rel.has('parallel') ? '‖' : rel.has('quoted-later') ? '↗' : rel.has('doublet') ? '=' : rel.has('keynote') ? '+' : '•';
  return `<span class="mm${seg === '‖' ? ' forte' : ''}" title="${n} ${n === 1 ? 'rimando' : 'rimandi'} a margine">${seg}</span>`;
}
function mostraCapitolo(b, c) {
  if (S.capitolo && S.capitolo[0] === b && S.capitolo[1] === c && $('#vista .lettore')) return;
  const L = D.libri[b];
  const [lab, s, e] = L.c[c];
  let n = 0;
  const lettera = new Map();
  const lettere = k => {
    if (!lettera.has(k)) {
      let x = n++, t = '';
      do { t = String.fromCharCode(97 + (x % 26)) + t; x = Math.floor(x / 26) - 1; } while (x >= 0);
      lettera.set(k, t);
    }
    return lettera.get(k);
  };
  let h = '', aperto = null, pag = null;
  const chiudi = () => { if (aperto) { h += aperto === 'p' ? '</p>' : '</div>'; aperto = null; } };
  for (let i = s; i <= e; i++) {
    for (const k of S.divAt.get(i) || []) { chiudi(); h += `<div class="divisione lv${D.div[k][2]}">${D.div[k][3]}</div>`; }
    for (const k of S.periAt.get(i) || []) {
      const p = D.peri[k];
      chiudi();
      h += `<h3 class="pericope">${p[2]}${p[3] ? `<span class="mezzo">dal v ${esc(versoDi(i))}</span>` : ''}</h3>`;
    }
    const poesia = V.f[i] & 1;
    if (aperto !== (poesia ? 'div' : 'p')) { chiudi(); h += poesia ? '<div class="strofa">' : '<p>'; aperto = poesia ? 'div' : 'p'; }
    if (V.ac[i]) h += `<span class="acr">${esc(V.ac[i])}</span>`;
    const pg = V.pg[i] !== pag ? `<span class="pg" title="pagina stampata">p. ${V.pg[i]}</span>` : '';
    pag = V.pg[i];
    const cl = 'v' + (poesia ? ' vp' : '') + (S.indeg[i] ? ' k' + calore(S.indeg[i]) : '');
    let corpo = chiamate(i, lettere);
    if (V.f[i] & 2) corpo += '<span class="omesso" title="Il numero è stampato, il testo CEI omette il versetto">(versetto omesso)</span>';
    if (poesia) corpo = corpo.split('<br>').map(r => `<span class="r">${r}</span>`).join('');
    h += `<span class="${cl}" id="v${i}" data-i="${i}" tabindex="0" role="button" aria-label="${esc(rif(i))}">${segnoMargine(i)}${pg}<span class="vn" aria-hidden="true">${esc(V.l[i])}</span>${corpo}</span>${poesia ? '' : ' '}`;
  }
  chiudi();
  const prec = c > 0 ? [b, c - 1] : b > 0 ? [b - 1, D.libri[b - 1].c.length - 1] : null;
  const succ = c < L.c.length - 1 ? [b, c + 1] : b < D.libri.length - 1 ? [b + 1, 0] : null;
  const capRif = ([bb, cc]) => `#${D.libri[bb].o}.${D.libri[bb].c[cc][0]}`;
  const capNome = ([bb, cc]) => `${D.libri[bb].s} ${D.libri[bb].c[cc][0] === 'Prol' ? 'prol.' : D.libri[bb].c[cc][0]}`;
  const freccia = (x, seg, tit) => x ? `<a href="${capRif(x)}" title="${tit}: ${esc(capNome(x))}" aria-label="${tit}">${seg}</a>` : `<span>${seg}</span>`;
  const titCap = lab === 'Prol' ? 'Prologo' : (L.c.length === 1 ? '' : lab);
  pagina(`<article class="lettore">
    <div class="testata"><div><div class="sopratitolo"><a href="#${L.o}">${esc(D.vol[L.v][1])}</a></div>
      <h1><a href="#${L.o}">${esc(L.t)}</a><span class="cap">${esc(titCap)}</span></h1></div>
      <div class="sfoglia">${freccia(prec, '‹', 'Capitolo precedente')}<a href="#${L.o}" title="Tutti i capitoli">${L.c.length > 1 ? '⋯' : '≡'}</a>${freccia(succ, '›', 'Capitolo successivo')}</div></div>
    <div class="legenda-calore">rimandi entranti: <i style="background:color-mix(in srgb,var(--caldo) 7%,transparent)"></i>1–2 <i style="background:color-mix(in srgb,var(--caldo) 20%,transparent)"></i>6–10 <i style="background:color-mix(in srgb,var(--caldo) 38%,transparent)"></i>21+</div>
    <div class="testo" lang="it">${h}</div>
    <div class="fine">${prec ? `<a href="${capRif(prec)}">‹ ${esc(capNome(prec))}</a>` : '<span></span>'}${succ ? `<a href="${capRif(succ)}">${esc(capNome(succ))} ›</a>` : ''}</div>
  </article>`);
  S.capitolo = [b, c, s, e];
  document.title = `${L.s} ${titCap} · ${L.t}`;
}
function selezionaVerso(a, z = a, scorri = false) {
  $$('.v.sel, .v.int').forEach(x => x.classList.remove('sel', 'int'));
  S.sel = a;
  if (a === null) { chiudiPannello(false); return; }
  for (let i = a + 1; i <= z; i++) { const x = $('#v' + i); if (x) x.classList.add('int'); }
  const el = $('#v' + a);
  if (el) el.classList.add('sel');
  mostraPannello(a);
  if (scorri && el) {
    const r = el.getBoundingClientRect();
    const alto = $('.barra').getBoundingClientRect().bottom;
    const basso = window.innerWidth <= 900 ? window.innerHeight * 0.26 : window.innerHeight;
    if (r.top < alto + 8 || r.bottom > basso - 8) {
      window.scrollTo({ top: window.scrollY + r.top - alto - (window.innerWidth <= 900 ? 12 : window.innerHeight * 0.25) });
    }
  }
}

// ---------------------------------------------------------------- side panel

function chiudiPannello(aggiornaHash = true) {
  const p = $('#pannello');
  if (!p.hidden) { p.hidden = true; $('.corpo').classList.remove('con-pannello'); }
  if (aggiornaHash && S.vista === 'lettore' && S.capitolo) {
    $$('.v.sel, .v.int').forEach(x => x.classList.remove('sel', 'int'));
    S.sel = null;
    const L = D.libri[S.capitolo[0]];
    history.replaceState(null, '', `#${L.o}.${L.c[S.capitolo[1]][0]}`);
  }
}
function chip(r, testo, extra = '', cls = '', col = '', dove = null) {
  // href: the whole passage when it is one run (Gen 22, Gv 12,46-50), else its first verse;
  // dove: the verse to open instead (the key note of a "+" reference)
  const h = dove !== null ? hashVerso(dove) : r.length === 2 ? hashVerso(r[0], r[1]) : hashVerso(r[0]);
  return `<a class="chip ${cls}" href="${h}" data-r="${runsAttr(r)}"${col ? ` style="--c:var(${col})"` : ''}${extra}>${testo}</a>`;
}
function versoChiave(l) {
  // the verse a "+" chip opens: the one whose key note the chip opens ("Mt 12,6+.38–40+":
  // 12,6 has no note, the key note is at 12,38), else the first verse carrying "+"
  if (!l[13].length) return null;
  const k = l[5][0];
  if (k === undefined) return l[13][0];
  return l[13].find(v => D.note[k][0] === v || contiene(D.note[k][6], v)) ?? l[13][0];
}
function noteDi(i) {
  const qui = (S.noteAt[i] || []).slice();
  const altre = [];
  D.note.forEach((x, k) => { if (x[0] !== i && contiene(x[6], i)) altre.push(k); });
  altre.sort((x, y) => ampiezza(D.note[x][6]) - ampiezza(D.note[y][6]) || x - y);
  return { qui, altre };
}
function schedaNota(k, i, aperta, chiave) {
  const x = D.note[k];
  const piano = testoPiano(x[5]);
  const ambito = x[4] === 2 ? 'nota al libro' : x[4] === 1 ? 'nota al capitolo' : '';
  const dove = x[0] === i ? 'chiamata qui' : `da <a href="${hashVerso(x[0])}" data-nota="${k}">${esc(rif(x[0]))}</a>`;
  return `<details class="nota${chiave ? ' chiave' : ''}" data-k="${k}"${aperta ? ' open' : ''}>
    <summary><span class="etichetta">${esc(x[3])}${esc(x[2] || 'nota')}</span><span class="assaggio">${esc(piano.slice(0, 140))}</span><span class="dove">${ambito ? ambito + ' · ' : ''}${x[0] === i ? 'chiamata qui' : 'da ' + esc(rif(x[0]))}</span></summary>
    <div class="nota-testo">${x[5]}<div class="contatori"><span>${dove}</span><span>copre <b>${esc(rifRuns(x[6]))}</b></span><span>p. ${x[7]}</span></div></div>
  </details>`;
}
function entranti(i) {
  const rel = {}, note = [], intro = [];
  D.ml.forEach((l, k) => {
    if (!vivo(l) || !contiene(l[2], i)) return;
    const src = D.mref[l[0]][0];
    if (src === i) return;
    (rel[relNome(l)] = rel[relNome(l)] || []).push(k);
  });
  D.nc.forEach((c, k) => { if (c[2] <= 1 && contiene(c[1], i)) note.push(k); });
  D.ic.forEach((c, k) => { if (c[3] <= 1 && contiene(c[2], i)) intro.push(k); });
  return { rel, note, intro };
}
function contesto(testo, raw, max = 200) {
  const k = Math.max(0, testo.indexOf(raw));
  let da = Math.max(0, k - 80);
  if (da > 0) { const sp = testo.indexOf(' ', da); if (sp >= 0 && sp < k) da = sp + 1; }   // from a word start
  let a = Math.min(testo.length, da + max);
  if (a < testo.length) { const sp = testo.lastIndexOf(' ', a); if (sp > k + raw.length) a = sp; }
  return (da > 0 ? '…' : '') + esc(testo.slice(da, k)) + '<mark>' + esc(testo.slice(k, k + raw.length)) + '</mark>' + esc(testo.slice(k + raw.length, a)) + (a < testo.length ? '…' : '');
}
function mostraPannello(i) {
  const p = $('#pannello');
  const b = S.vb[i], L = D.libri[b];
  const { qui, altre } = noteDi(i);
  const chiave = S.notaChiave;
  // outgoing margin references, grouped by relation
  const gruppi = {}, stampati = [];
  let nUscita = 0;
  for (const m of S.mrefAt[i] || []) {
    stampati.push(D.mref[m][2]);
    for (const k of S.mlOf[m]) {
      const l = D.ml[k];
      const g = l[1] >= 4 ? 'numbering' : relNome(l);
      (gruppi[g] = gruppi[g] || []).push(k);
      nUscita++;
    }
  }
  const E = entranti(i);
  const nEntr = Object.values(E.rel).reduce((s, x) => s + x.length, 0);
  let h = `<div class="pan-testa"><button type="button" class="maniglia" data-maniglia aria-label="Allarga o riduci il pannello"></button><div><h2 class="rif" tabindex="-1">${esc(rif(i))}</h2><div class="libro-tit">${esc(L.t)} · p. ${V.pg[i]}</div></div>
    <div class="azioni"><a class="bottone" href="#grafo/${V.id[i]}" title="Rete dei collegamenti (g)">Grafo</a>
    <button class="bottone" type="button" data-chiudi title="Chiudi (Esc)" aria-label="Chiudi">✕</button></div></div>
    <div class="pan-corpo">
    <div class="citazione">${V.h[i] || '<span class="omesso">(versetto omesso nel testo CEI)</span>'}</div>
    <div class="contatori"><span><b>${qui.length + altre.length}</b> note</span><span><b>${nUscita}</b> rimandi in uscita</span><span><b>${nEntr}</b> rimandi entranti</span><span><b>${E.note.length + E.intro.length}</b> citazioni</span></div>`;

  h += `<section class="sez"><h3>Note della BJ <span class="n">${qui.length + altre.length}</span></h3>`;
  if (!qui.length && !altre.length) h += '<p class="vuoto">Nessuna nota riguarda questo versetto.</p>';
  for (const k of qui) h += schedaNota(k, i, true, k === chiave);
  altre.forEach(k => { h += schedaNota(k, i, k === chiave, k === chiave); });
  h += '</section>';

  h += `<section class="sez"><h3>Rimandi a margine <span class="n">${nUscita}</span></h3>`;
  if (!nUscita) h += '<p class="vuoto">Nessun rimando a margine accanto a questo versetto.</p>';
  else h += `<div class="margine-stampato" title="Come stampati a margine">${stampati.map(s => `<span>${esc(s)}</span>`).join('')}</div>`;
  for (const g of [...ORDINE_REL, 'numbering']) {
    const ks = gruppi[g];
    if (!ks) continue;
    const R = REL[g];
    let chips = '', motivi = '';
    for (const k of ks) {
      const l = D.ml[k];
      const fl = l[3] ? ` <small>${esc(l[3])}</small>` : '';
      const qual = l[7] ? ` <small>(${esc(l[7])})</small>` : '';
      if (g === 'numbering') { chips += `<span class="chip num" title="Numerazione di un’altra tradizione">${esc(l[11])}</span>`; continue; }
      if (!l[2].length) {
        chips += `<span class="chip x" title="${esc(l[10])}">${esc(l[11])}</span>`;
        motivi += `<span class="motivo">«${esc(l[11])}»: ${esc(l[10])}</span>`;
        continue;
      }
      const nota = l[5].length ? ` data-nota="${l[5][0]}"` : '';
      const legato = l[14] ? ' <small title="stampato con «=»: doppione del riferimento precedente">=</small>' : '';
      chips += chip(l[2], esc(rifRuns(l[2])) + (g === 'keynote' ? ' +' : '') + fl + qual + legato,
        ` title="stampato: ${esc(l[11])}"${nota}`, '', R.col, g === 'keynote' ? versoChiave(l) : null);
      if (l[9] === 1) motivi += `<span class="motivo">«${esc(l[11])}»: in parte irrisolto, ${esc(l[10])}</span>`;
    }
    h += `<div class="gruppo"><h4><span class="seg" style="color:var(${R.txt || R.col})">${R.seg}</span>${R.nome} <span class="n">${ks.length}</span></h4><div class="chips">${chips}</div>${motivi}</div>`;
  }
  h += '</section>';

  h += `<section class="sez"><h3>Collegamenti entranti <span class="n">${nEntr + E.note.length + E.intro.length}</span></h3>`;
  if (!nEntr && !E.note.length && !E.intro.length) h += '<p class="vuoto">Nessun rimando o citazione punta a questo versetto.</p>';
  for (const g of ORDINE_REL) {
    const ks = E.rel[g];
    if (!ks) continue;
    const R = REL[g];
    ks.sort((x, y) => ampiezza(D.ml[x][2]) - ampiezza(D.ml[y][2]) || D.mref[D.ml[x][0]][0] - D.mref[D.ml[y][0]][0]);
    const visti = new Set();
    let chips = '', n = 0;
    for (const k of ks) {
      const l = D.ml[k], src = D.mref[l[0]][0];
      if (visti.has(src)) continue;
      visti.add(src);
      const via = ampiezza(l[2]) > 1 ? ` <small>→ ${esc(rifRuns(l[2]))}</small>` : '';
      chips += chip([src, src], esc(rif(src)) + via, ` title="a margine di ${esc(rif(src))}: ${esc(l[11])}"`, '', R.col);
      n++;
    }
    h += `<div class="gruppo"><h4><span class="seg" style="color:var(${R.txt || R.col})">${R.seg}</span>${R.entr} <span class="n">${n}</span></h4><div class="chips">${chips}</div></div>`;
  }
  if (E.note.length) {
    const righe = E.note.map(k => {
      const c = D.nc[k], x = D.note[c[0]];
      return `<li><a href="${hashVerso(x[0])}" data-nota="${c[0]}" data-r="${x[0]}-${x[0]}">Nota ${esc(x[3] + x[2])}</a> <small>${esc(D.libri[S.vb[x[0]]].s)}</small><span class="frase">${contesto(testoPiano(x[5]), c[4])}</span></li>`;
    });
    h += elencoLungo(`<span class="seg">§</span>Citato nelle note <span class="n">${E.note.length}</span>`, righe);
  }
  if (E.intro.length) {
    const righe = E.intro.map(k => {
      const c = D.ic[k], x = D.intro[c[0]];
      const par = x[5].find(q => q[0] === c[1]);
      return `<li><a href="#intro/${esc(x[0])}.${c[1]}">${esc(x[1])}</a> <small>§ ${c[1]}</small><span class="frase">${contesto(testoPiano(par[2]), c[5])}</span></li>`;
    });
    h += elencoLungo(`<span class="seg">¶</span>Citato nelle introduzioni <span class="n">${E.intro.length}</span>`, righe);
  }
  h += '</section></div>';
  p.innerHTML = h;
  collegaCitazioni(p);
  p.hidden = false;
  $('.corpo').classList.add('con-pannello');
  p.scrollTop = 0;
  if (S.fuocoPannello) $('#pannello .rif').focus({ preventScroll: true });
  S.fuocoPannello = false;
  if (chiave !== undefined && chiave !== null) {
    const n = p.querySelector(`.nota[data-k="${chiave}"]`);
    if (n) { n.open = true; n.classList.add('lampo'); n.scrollIntoView({ block: 'start' }); p.scrollTop -= 60; }
  }
  S.notaChiave = null;
}
function elencoLungo(titolo, righe, primi = 6) {
  const resto = righe.length - primi;
  return `<div class="gruppo"><h4>${titolo}</h4><ul class="elenco">${righe.slice(0, primi).join('')}</ul>${resto > 0
    ? `<details class="altri"><summary class="altro">mostra altri ${resto}</summary><ul class="elenco">${righe.slice(primi).join('')}</ul></details>` : ''}</div>`;
}
function collegaCitazioni(radice) {
  // the <a class="ci" data-c|data-i> spans of notes and introductions get their target
  $$('a.ci', radice).forEach(a => {
    const c = a.dataset.c !== undefined ? D.nc[+a.dataset.c] : null;
    const r = c ? c[1] : D.ic[+a.dataset.i][2];
    const motivo = c ? c[3] : D.ic[+a.dataset.i][4];
    if (!r.length) { a.classList.add('x'); a.title = motivo || 'riferimento non risolto'; a.removeAttribute('href'); return; }
    a.href = hashVerso(r[0]);
    a.dataset.r = runsAttr(r);
    if (motivo) a.title = motivo;
  });
}

// ---------------------------------------------------------------- preview of a target

let tAnteprima = null, puntatore = 'mouse', bersaglio = null;
function nascondiAnteprima() { clearTimeout(tAnteprima); $('#anteprima').hidden = true; bersaglio = null; }
function mostraAnteprima(el, tocco) {
  const r = el.dataset.r.split(',').map(x => x.split('-').map(Number));
  const box = $('#anteprima');
  let h = `<div class="ap-rif">${esc(rifRuns(r.flat()))}${r.length === 1 && r[0][1] > r[0][0] ? `<small>${r[0][1] - r[0][0] + 1} versetti</small>` : ''}</div>`;
  let mostrati = 0, totale = 0;
  for (const [a, b] of r) {
    totale += b - a + 1;
    for (let i = a; i <= b && mostrati < 3; i++, mostrati++) {
      let t = testoPiano(V.h[i]);
      if (t.length > 280) t = t.slice(0, 280).replace(/\s\S*$/, '') + '…';
      h += `<p class="ap-v"><b>${esc(versoDi(i))}</b>${esc(t) || '<i>(omesso)</i>'}</p>`;
    }
  }
  if (totale > mostrati) h += `<div class="ap-piu">… e altri ${totale - mostrati} versetti</div>`;
  if (tocco) h += `<div class="ap-vai"><a class="bottone primario" href="${esc(el.getAttribute('href'))}">Vai a ${esc(rif(r[0][0]))} ›</a></div>`;
  box.innerHTML = h;
  box.hidden = false;
  const q = el.getBoundingClientRect(), w = box.offsetWidth, ht = box.offsetHeight;
  let x = Math.min(Math.max(8, q.left), window.innerWidth - w - 8);
  let y = q.bottom + 6;
  if (y + ht > window.innerHeight - 8) y = Math.max(8, q.top - ht - 6);
  box.style.left = x + 'px';
  box.style.top = y + 'px';
  bersaglio = el;
}

// ---------------------------------------------------------------- introductions

function mostraIntro(arg) {
  const m = arg.match(/^(.*?)(?:\.(\d+))?$/);
  const k = D.intro.findIndex(x => x[0] === m[1]);
  if (k < 0) return nonTrovato(arg);
  const x = D.intro[k];
  let pag = null;
  const pars = x[5].map(([n, pg, h]) => {
    const seg = pg !== pag ? `<span class="pg">p. ${pg}</span>` : '';
    pag = pg;
    return `<p id="par${n}">${seg}${h}</p>`;
  }).join('');
  const libri = x[4].map(b => `<a href="#${D.libri[b].o}">${esc(D.libri[b].t)}</a>`).join(' · ');
  pagina(`<div class="pagina"><div class="sopratitolo">${esc(D.vol[x[3]][1])} · introduzione</div>
    <h1>${esc(x[1])}</h1><p class="sotto">${libri}</p><div class="intro-testo">${pars}</div></div>`);
  collegaCitazioni($('#vista'));
  document.title = x[1] + ' · introduzione';
  if (m[2]) {
    const p = $('#par' + m[2]);
    if (p) { p.classList.add('sel'); window.scrollTo(0, p.getBoundingClientRect().top + window.scrollY - 110); }
  }
}

// ---------------------------------------------------------------- search

function mostraCerca(par) {
  const q = par.q || '', dove = par.in || 'tutto', T = par.t || '', bsel = par.b || '';
  const opz = D.libri.map(b => `<option value="${b.o}"${b.o === bsel ? ' selected' : ''}>${esc(b.t)}</option>`).join('');
  if ($('#vista .ricerca') && S.vista === 'cerca') {
    if (document.activeElement !== $('#rq')) $('#rq').value = q;
    $$('.segmenti button').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.in === dove)));
    $('#rt').value = T;
    $('#rb').value = bsel;
    aggiornaRisultati(q, dove, T, bsel);
    return;
  }
  pagina(`<div class="pagina ricerca"><h1>Cerca nel testo e nelle note</h1>
    <p class="sotto">Parole intere, senza distinguere accenti e maiuscole: <a href="#cerca?q=melchisedek">melchisedek</a> trova «Melchìsedek». Più parole devono comparire tutte; tra virgolette una frase esatta; un asterisco cerca l’inizio di parola (<a href="#cerca?q=ira*">ira*</a> trova anche «irato»).</p>
    <div class="ricerca-campi">
      <input type="search" id="rq" value="${esc(q)}" placeholder="Parola o frase…" aria-label="Testo da cercare" spellcheck="false">
      <div class="segmenti" role="group" aria-label="Dove cercare">
        ${[['tutto', 'Tutto'], ['versetti', 'Versetti'], ['note', 'Note']].map(([v, t]) => `<button type="button" data-in="${v}" aria-pressed="${v === dove}">${t}</button>`).join('')}
      </div>
      <select id="rt" aria-label="Testamento"><option value="">Tutta la Bibbia</option><option value="AT"${T === 'AT' ? ' selected' : ''}>Antico Testamento</option><option value="NT"${T === 'NT' ? ' selected' : ''}>Nuovo Testamento</option></select>
      <select id="rb" aria-label="Libro"><option value="">Tutti i libri</option>${opz}</select>
    </div>
    <div class="esito" id="esito"></div><div class="risultati" id="risultati"></div></div>`);
  document.title = 'Cerca · Esploratore dei versetti';
  const leggi = () => ({
    q: $('#rq').value, in: $('.segmenti [aria-pressed="true"]').dataset.in, t: $('#rt').value, b: $('#rb').value,
  });
  const scrivi = () => {
    const p = leggi();
    const h = '#cerca?q=' + encodeURIComponent(p.q) + (p.in !== 'tutto' ? '&in=' + p.in : '') + (p.t ? '&t=' + p.t : '') + (p.b ? '&b=' + p.b : '');
    history.replaceState(null, '', h);
    aggiornaRisultati(p.q, p.in, p.t, p.b);
  };
  let t = null;
  $('#rq').addEventListener('input', () => { clearTimeout(t); t = setTimeout(scrivi, 180); });
  $('.segmenti').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('.segmenti button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    scrivi();
  });
  $('#rt').addEventListener('change', scrivi);
  $('#rb').addEventListener('change', scrivi);
  aggiornaRisultati(q, dove, T, bsel);
  if (!q) $('#rq').focus();
}
// a term matches whole words of the normalised text ("ira" is not in "apparirà"); "ira*" matches
// the words starting with it; a "phrase" matches whole words at both ends; terms with no letter
// or digit ("&") are ignored
const LETTERA = '\\p{L}\\p{N}';
function termini(q) {
  const out = [];
  q.replace(/"([^"]+)"|(\S+)/g, (_, f, w) => {
    let t = normalizza((f || w).trim()).replace(/\s+/g, ' ');
    const prefisso = !f && t.endsWith('*');
    t = t.replace(/^\*+|\*+$/g, '');
    if (!/[\p{L}\p{N}]/u.test(t)) return;
    const corpo = t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const fine = prefisso ? `[${LETTERA}]*` : `(?![${LETTERA}])`;
    out.push({ t, g: new RegExp(`(?<![${LETTERA}])${corpo}${fine}`, 'gu') });
  });
  return out;
}
function aggiornaRisultati(q, dove, T, bsel) {
  const box = $('#risultati'), esito = $('#esito');
  const ts = termini(q);
  if (!ts.length) { box.innerHTML = ''; esito.textContent = 'Scrivi almeno una parola.'; return; }
  const I = indiceRicerca();
  const t0 = performance.now();
  const bfil = bsel ? S.osis.get(bsel) : -1;
  const ok = b => (bfil < 0 || b === bfil) && (!T || D.libri[b].T === T);
  const per = new Map();
  let nv = 0, nn = 0;
  const tutti = s => ts.every(t => s.includes(t.t) && (t.g.lastIndex = 0, t.g.test(s)));
  if (dove !== 'note') {
    for (let i = 0; i < S.n; i++) {
      if (!ok(S.vb[i]) || !tutti(I.vn[i])) continue;
      if (!per.has(S.vb[i])) per.set(S.vb[i], []);
      per.get(S.vb[i]).push([0, i]);
      nv++;
    }
  }
  if (dove !== 'versetti') {
    D.note.forEach((x, k) => {
      const b = S.vb[x[0]];
      if (!ok(b) || !tutti(I.nn[k])) return;
      if (!per.has(b)) per.set(b, []);
      per.get(b).push([1, k]);
      nn++;
    });
  }
  const ms = performance.now() - t0;
  esito.innerHTML = nv + nn ? `<b>${num(nv)}</b> versetti e <b>${num(nn)}</b> note in <b>${per.size}</b> libri <small>(${ms.toFixed(0)} ms)</small>` : `Nessun risultato per «${esc(q)}».`;
  const libri = [...per.keys()].sort((a, b) => a - b);
  const riga = ([tipo, k]) => {
    if (tipo === 0) return `<div class="r"><a class="dove" href="${hashVerso(k)}" data-r="${k}-${k}">${esc(rif(k))}</a><div class="frase">${evidenzia(I.vp[k], I.vn[k], ts)}</div></div>`;
    const x = D.note[k];
    return `<div class="r rn"><a class="dove" href="${hashVerso(x[0])}" data-nota="${k}">nota ${esc(x[3] + x[2])}<small>${esc(rif(x[0]))}</small></a><div class="frase">${evidenzia(I.np[k], I.nn[k], ts)}</div></div>`;
  };
  let h = '', righe = 0;
  for (const b of libri) {
    const xs = per.get(b);
    xs.sort((x, y) => (x[0] ? D.note[x[1]][0] : x[1]) - (y[0] ? D.note[y[1]][0] : y[1]) || x[0] - y[0]);
    const nvb = xs.filter(x => !x[0]).length;
    const lim = righe > 600 ? 3 : 25;
    h += `<section class="blocco"><h3><a href="#${D.libri[b].o}">${esc(D.libri[b].t)}</a><small>${nvb} versetti · ${xs.length - nvb} note</small></h3>${xs.slice(0, lim).map(riga).join('')}`;
    if (xs.length > lim) h += `<button class="altro" type="button" data-libro="${b}">mostra altri ${xs.length - lim}</button>`;
    h += '</section>';
    righe += Math.min(lim, xs.length);
  }
  box.innerHTML = h;
  box.onclick = e => {
    const btn = e.target.closest('[data-libro]');
    if (!btn) return;
    const xs = per.get(+btn.dataset.libro);
    btn.insertAdjacentHTML('beforebegin', xs.slice(btn.parentNode.querySelectorAll('.r').length).map(riga).join(''));
    btn.remove();
  };
}

// ---------------------------------------------------------------- graph view

function colori() {
  const cs = getComputedStyle(document.documentElement);
  const c = {};
  for (const k of ['--s-at', '--s-nt', '--inchiostro', '--secondo', '--tenue', '--foglio', '--linea', '--sel-bordo', '--rubrica', '--carta', '--seq0', '--seq1', '--seq9', '--linea2']) c[k] = cs.getPropertyValue(k).trim();
  for (const r in REL) c[r] = cs.getPropertyValue(REL[r].col).trim();
  return c;
}
function vicini(a, b, filtro) {
  // edges of the passage [a, b]: margin references from its verses and towards it, note citations both ways
  const out = [];
  const lim = Math.min(b, a + 40);
  for (let v = a; v <= lim; v++) {
    for (const m of S.mrefAt[v] || []) for (const k of S.mlOf[m]) {
      const l = D.ml[k];
      if (!vivo(l) || !filtro.has(relNome(l))) continue;
      const r = l[2];
      for (let j = 0; j < r.length; j += 2) out.push({ x: r[j], y: r[j + 1], rel: relNome(l), dir: 1, w: r[j + 1] - r[j] });
    }
    if (filtro.has('cites')) for (const n of S.noteAt[v] || []) for (const k of S.ncOf[n]) {
      const c = D.nc[k];
      if (c[2] > 1) continue;
      for (let j = 0; j < c[1].length; j += 2) out.push({ x: c[1][j], y: c[1][j + 1], rel: 'cites', dir: 1, w: c[1][j + 1] - c[1][j] });
    }
  }
  D.ml.forEach(l => {
    if (!vivo(l) || !filtro.has(relNome(l)) || !sovrappone(l[2], a, b)) return;
    const s = D.mref[l[0]][0];
    out.push({ x: s, y: s, rel: relNome(l), dir: -1, w: ampiezza(l[2]) });
  });
  if (filtro.has('cites')) D.nc.forEach(c => {
    if (c[2] > 1 || !sovrappone(c[1], a, b)) return;
    const s = D.note[c[0]][0];
    out.push({ x: s, y: s, rel: 'cites', dir: -1, w: ampiezza(c[1]) + 5 });
  });
  const pri = { parallel: 0, 'quoted-later': 1, doublet: 2, keynote: 3, related: 4, cites: 5 };
  return out.filter(e => !(e.x === a && e.y === b)).sort((p, q) => pri[p.rel] - pri[q.rel] || p.w - q.w || p.x - q.x);
}
function costruisciEgo(i, prof, filtro) {
  const nodi = new Map(), archi = new Map();
  const nodo = (x, y, d) => {
    const k = x + '-' + y;
    if (!nodi.has(k)) nodi.set(k, { k, a: x, b: y, d, deg: 0 });
    return nodi.get(k);
  };
  const arco = (p, q, rel, dir) => {
    const [s, t] = dir > 0 ? [p, q] : [q, p];
    const k = s.k + '>' + t.k + '>' + rel;
    const inv = t.k + '>' + s.k + '>' + rel;
    if (archi.has(k) || archi.has(inv)) return;
    archi.set(k, { s, t, rel });
    s.deg++; t.deg++;
  };
  const centro = nodo(i, i, 0);
  const CAP1 = 60, CAP2 = 5, MAX = prof > 1 ? 150 : 70;
  for (const e of vicini(i, i, filtro)) {
    if (nodi.size >= CAP1 + 1 && !nodi.has(e.x + '-' + e.y)) continue;
    const n = nodo(e.x, e.y, 1);
    if (e.dir > 0 && e.rel !== 'cites') n.uscita = true;      // printed beside the centre: labelled first
    arco(centro, n, e.rel, e.dir);
  }
  if (prof > 1) {
    const primi = [...nodi.values()].filter(n => n.d === 1);
    for (const n of primi) {
      let presi = 0;
      for (const e of vicini(n.a, n.b, filtro)) {
        const k = e.x + '-' + e.y;
        if (k === centro.k) continue;
        if (!nodi.has(k)) { if (presi >= CAP2 || nodi.size >= MAX) continue; presi++; }
        arco(n, nodo(e.x, e.y, 2), e.rel, e.dir);
      }
    }
  }
  return { nodi: [...nodi.values()], archi: [...archi.values()], centro };
}
function mostraGrafo(id, par) {
  let i = S.vix.get(id);
  if (i === undefined && id) {
    pagina(`<div class="pagina"><h1>Versetto non trovato</h1><p class="sotto">«${esc(id)}» non è l’identificativo di un versetto (per esempio <a href="#grafo/John.3.16">John.3.16</a>).</p></div>`);
    return;
  }
  const prof = par.p === '2' ? 2 : 1;
  if (i === undefined) {                 // the Grafo tab: the selected verse, written in the address
    i = S.sel ?? S.ultimo ?? S.vix.get('John.3.16');
    history.replaceState(null, '', `#grafo/${V.id[i]}${prof > 1 ? '?p=2' : ''}`);
  }
  S.ultimo = i;
  // the relation filters are part of the address (?f=parallel,doublet); none given = all
  S.filtro = new Set(par.f !== undefined ? par.f.split(',').filter(r => ORDINE_REL.includes(r)) : ORDINE_REL);
  const indirizzo = (p = prof) => {
    const q = [p > 1 ? 'p=2' : '', S.filtro.size < ORDINE_REL.length ? 'f=' + [...S.filtro].join(',') : ''].filter(Boolean).join('&');
    return `#grafo/${V.id[i]}${q ? '?' + q : ''}`;
  };
  const conta = {};
  for (const e of vicini(i, i, new Set(ORDINE_REL))) conta[e.rel] = (conta[e.rel] || 0) + 1;
  const linea = (r, w = 26) => `<svg width="${w}" height="10" aria-hidden="true"><line x1="1" y1="5" x2="${w - 1}" y2="5" stroke="var(${REL[r].col})" stroke-width="${r === 'parallel' ? 3 : 2}" stroke-dasharray="${REL[r].dash.join(' ')}"/></svg>`;
  pagina(`<div class="grafo-vista">
    <div class="grafo-tela" id="tela"><canvas id="cv" aria-label="Rete dei collegamenti di ${esc(rif(i))}"></canvas>
      <div class="grafo-titolo"><b>${esc(rif(i))}</b><span>${esc(D.libri[S.vb[i]].t)} · rete dei collegamenti, profondità ${prof}</span></div>
      <div class="grafo-zoom"><button type="button" data-z="1.25" aria-label="Ingrandisci">+</button><button type="button" data-z="0.8" aria-label="Riduci">−</button><button type="button" data-z="0" aria-label="Centra" title="Centra">⌂</button></div></div>
    <div class="grafo-lato">
      <h3>Versetto</h3><div class="grafo-info"><a class="bottone primario" href="#${V.id[i]}">Apri nel lettore</a></div>
      <h3>Profondità</h3>
      <div class="segmenti" role="group"><button type="button" data-p="1" aria-pressed="${prof === 1}">1 passo</button><button type="button" data-p="2" aria-pressed="${prof === 2}">2 passi</button></div>
      <h3>Relazioni (archi)</h3>
      ${ORDINE_REL.map(r => `<label class="leg"><input type="checkbox" data-rel="${r}"${S.filtro.has(r) ? ' checked' : ''}>${linea(r)}<span>${REL[r].seg} ${REL[r].nome}</span><span class="n">${conta[r] || 0}</span></label>`).join('')}
      <h3>Nodi</h3>
      <div class="leg"><svg width="26" height="14"><circle cx="13" cy="7" r="6" fill="var(--s-at)"/></svg>Antico Testamento</div>
      <div class="leg"><svg width="26" height="14"><circle cx="13" cy="7" r="6" fill="var(--s-nt)"/></svg>Nuovo Testamento</div>
      <div class="leg"><svg width="26" height="14"><rect x="5" y="2" width="16" height="10" rx="5" fill="none" stroke="var(--tenue)" stroke-width="1.5"/></svg>passo di più versetti</div>
      <h3>Rete</h3><div class="grafo-info" id="ginfo"></div>
      <details class="grafo-nodi"><summary>Elenco dei nodi</summary><ul id="gnodi"></ul></details>
      <p class="grafo-info nota-grafo">Clic su un nodo (o sul suo nome nell’elenco): diventa il centro. Trascina per spostare, rotella o +/− per lo zoom. Le frecce vanno dal versetto che stampa il rimando al passo indicato.</p>
    </div></div>`);
  document.title = `Grafo ${rif(i)} · Esploratore dei versetti`;
  $('.grafo-lato').addEventListener('change', e => {
    const r = e.target.dataset.rel;
    if (!r) return;
    if (e.target.checked) S.filtro.add(r); else S.filtro.delete(r);
    history.replaceState(null, '', indirizzo());
    disegnaGrafo(i, prof);
  });
  $('.grafo-lato .segmenti').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (b) vai(indirizzo(+b.dataset.p), true);
  });
  disegnaGrafo(i, prof);
}
function rng(seed) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }
function disegnaGrafo(i, prof) {
  if (S.anim) cancelAnimationFrame(S.anim);
  const G = costruisciEgo(i, prof, S.filtro);
  const tela = $('#tela'), cv = $('#cv');
  const ctx = cv.getContext('2d');
  const casuale = rng(i + 1);
  const n1 = G.nodi.filter(n => n.d === 1);
  const R1 = Math.min(300, Math.max(140, n1.length * 7));
  const box = tela.getBoundingClientRect();
  const EX = Math.max(0.8, Math.min(1.7, (box.width / Math.max(1, box.height)) * 1.15));   // ellipse follows the canvas
  G.nodi.forEach(n => {
    if (n.d === 0) { n.x = 0; n.y = 0; n.fisso = true; return; }
    const ang = n.d === 1 ? (2 * Math.PI * n1.indexOf(n)) / Math.max(1, n1.length) : casuale() * 2 * Math.PI;
    const rag = n.d === 1 ? R1 : R1 * 1.8 + casuale() * 60;
    n.x = Math.cos(ang) * rag * EX; n.y = Math.sin(ang) * rag; n.vx = 0; n.vy = 0;
  });
  const nAT = G.nodi.filter(n => D.libri[S.vb[n.a]].T === 'AT').length;
  const vuota = !S.filtro.size ? 'Nessuna relazione scelta: spunta almeno una casella qui a lato.'
    : !G.archi.length ? 'Nessun collegamento: nessun rimando a margine o citazione parte da questo versetto o vi arriva.' : '';
  $('#ginfo').innerHTML = `<b>${G.nodi.length}</b> nodi, <b>${G.archi.length}</b> archi<br>${nAT} nell’AT, ${G.nodi.length - nAT} nel NT${G.nodi.length >= (prof > 1 ? 150 : 61) ? '<br><small>rete troncata: mostrati i collegamenti più specifici</small>' : ''}`;
  $('#tela .grafo-vuoto')?.remove();
  if (vuota) $('#tela').insertAdjacentHTML('beforeend', `<p class="grafo-vuoto">${vuota}</p>`);
  $('#gnodi').innerHTML = G.nodi.filter(n => n.d > 0).sort((p, q) => p.d - q.d || p.a - q.a)
    .map(n => `<li><a href="#grafo/${V.id[n.a]}${prof > 1 ? '?p=2' : ''}" data-r="${n.a}-${n.b}">${esc(rif(n.a, n.b))}</a>${n.d > 1 ? ' <small>2° passo</small>' : ''}</li>`).join('');
  const vista = { z: 1, x: 0, y: 0 };
  let C = colori(), alpha = 1, giri = 0, sopra = null, trasc = null;
  const raggio = n => (n.d === 0 ? 11 : 4.5 + Math.min(6, Math.sqrt(n.deg) * 1.4));
  const etichetta = n => rif(n.a, n.b);
  function misura() {
    const r = tela.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
    cv.width = Math.max(1, r.width * dpr); cv.height = Math.max(1, r.height * dpr);
    S.gdim = { w: r.width, h: r.height, dpr };
    const t = $('#tela .grafo-titolo').getBoundingClientRect();     // labels keep out of the title
    S.gtitolo = [t.left - r.left - 4, t.top - r.top - 4, t.left - r.left + t.width + 4, t.top - r.top + t.height + 4];
  }
  function passo() {
    const ns = G.nodi;
    for (let p = 0; p < ns.length; p++) {
      const A = ns[p];
      for (let q = p + 1; q < ns.length; q++) {
        const B = ns[q];
        let dx = A.x - B.x, dy = A.y - B.y, d2 = dx * dx + dy * dy;
        if (d2 < 1) { dx = casuale() - 0.5; dy = casuale() - 0.5; d2 = 1; }
        if (d2 > 250000) continue;
        const f = (2200 / d2) * alpha;
        const d = Math.sqrt(d2);
        A.vx += (dx / d) * f; A.vy += (dy / d) * f; B.vx -= (dx / d) * f; B.vy -= (dy / d) * f;
      }
    }
    for (const e of G.archi) {
      const dx = e.t.x - e.s.x, dy = e.t.y - e.s.y, d = Math.sqrt(dx * dx + dy * dy) || 1;
      const L = e.s.d === 0 || e.t.d === 0 ? R1 : 70;
      const f = ((d - L) / d) * 0.05 * alpha;
      e.s.vx += dx * f; e.s.vy += dy * f; e.t.vx -= dx * f; e.t.vy -= dy * f;
    }
    for (const n of ns) {
      if (n.fisso || n === trasc) { n.vx = n.vy = 0; continue; }
      const d = Math.hypot(n.x / EX, n.y) || 1, rr = n.d === 1 ? R1 : R1 * 1.9, k = n.d === 1 ? 0.08 : 0.03;
      n.vx += (n.x / d) * (rr - d) * k * alpha; n.vy += (n.y / d) * (rr - d) * k * alpha;
      n.vx *= 0.62; n.vy *= 0.62;
      n.x += Math.max(-30, Math.min(30, n.vx)); n.y += Math.max(-30, Math.min(30, n.vy));
    }
    alpha = Math.max(0.02, alpha * 0.985);
  }
  function freccia(x1, y1, x2, y2, r) {
    const a = Math.atan2(y2 - y1, x2 - x1), x = x2 - Math.cos(a) * (r + 2), y = y2 - Math.sin(a) * (r + 2), s = 5 / vista.z;
    ctx.beginPath(); ctx.moveTo(x, y);
    ctx.lineTo(x - Math.cos(a - 0.45) * s * 1.6, y - Math.sin(a - 0.45) * s * 1.6);
    ctx.lineTo(x - Math.cos(a + 0.45) * s * 1.6, y - Math.sin(a + 0.45) * s * 1.6);
    ctx.closePath(); ctx.fill();
  }
  function disegna() {
    const { w, h, dpr } = S.gdim;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.setTransform(dpr * vista.z, 0, 0, dpr * vista.z, dpr * (w / 2 + vista.x), dpr * (h / 2 + vista.y));
    const vicino = sopra ? new Set(G.archi.filter(e => e.s === sopra || e.t === sopra).flatMap(e => [e.s, e.t])) : null;
    for (const e of G.archi) {
      const tenue = vicino && !(e.s === sopra || e.t === sopra);
      ctx.globalAlpha = tenue ? 0.12 : e.rel === 'related' || e.rel === 'cites' ? 0.75 : 0.95;
      ctx.strokeStyle = ctx.fillStyle = C[e.rel];
      ctx.lineWidth = (e.rel === 'parallel' ? 2.6 : e.rel === 'related' || e.rel === 'cites' ? 1.2 : 2) / vista.z;
      ctx.setLineDash(REL[e.rel].dash.map(x => x / vista.z));
      ctx.beginPath(); ctx.moveTo(e.s.x, e.s.y); ctx.lineTo(e.t.x, e.t.y); ctx.stroke();
      ctx.setLineDash([]);
      if (e.rel !== 'parallel' && e.rel !== 'doublet') freccia(e.s.x, e.s.y, e.t.x, e.t.y, raggio(e.t) / 1);
    }
    ctx.globalAlpha = 1;
    for (const n of G.nodi) {
      const r = raggio(n), tenue = vicino && !vicino.has(n);
      ctx.globalAlpha = tenue ? 0.25 : 1;
      ctx.fillStyle = D.libri[S.vb[n.a]].T === 'AT' ? C['--s-at'] : C['--s-nt'];
      ctx.strokeStyle = C['--foglio'];
      ctx.lineWidth = 2 / vista.z;
      ctx.beginPath();
      if (n.b > n.a) { const lw = r * 1.7; ctx.roundRect(n.x - lw, n.y - r, lw * 2, r * 2, r); } else ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
      ctx.fill(); ctx.stroke();
      if (n.d === 0 || n === sopra) { ctx.strokeStyle = C['--inchiostro']; ctx.lineWidth = 2 / vista.z; ctx.beginPath(); ctx.arc(n.x, n.y, r + 4 / vista.z, 0, Math.PI * 2); ctx.stroke(); }
    }
    ctx.globalAlpha = 1;
    ctx.textBaseline = 'middle';
    // labels: the centre, the hovered node and its neighbours first, then by depth and degree;
    // a label overlapping one already drawn is skipped (hover a node to read it)
    const ordine = G.nodi.filter(n => !(vicino && !vicino.has(n)))
      .sort((p, q) => (q === sopra) - (p === sopra) || p.d - q.d || !!q.uscita - !!p.uscita || q.deg - p.deg);
    const tt = S.gtitolo;                  // the title box, in world units: no label under it
    const presi = tt ? [[(tt[0] - w / 2 - vista.x) / vista.z, (tt[1] - h / 2 - vista.y) / vista.z,
      (tt[2] - w / 2 - vista.x) / vista.z, (tt[3] - h / 2 - vista.y) / vista.z]] : [];
    const destra = (w / 2 - vista.x) / vista.z - 4 / vista.z, sinistraMax = (-w / 2 - vista.x) / vista.z + 4 / vista.z;
    for (const n of ordine) {
      if (n.d === 2 && vista.z < 1.1 && !vicino) continue;
      const fs = (n.d === 0 ? 14 : 11.5) / vista.z;
      ctx.font = `${n.d === 0 ? 700 : 500} ${fs}px system-ui, sans-serif`;
      const t = etichetta(n), w = ctx.measureText(t).width, r = raggio(n) * (n.b > n.a ? 1.8 : 1) + 4 / vista.z;
      let sinistra = n.d > 0 && n.x < 0;
      if (!sinistra && n.x + r + w > destra) sinistra = true;          // no label cut at the right edge
      else if (sinistra && n.x - r - w < sinistraMax) sinistra = false;
      const x = sinistra ? n.x - r - w : n.x + r;
      const q = [x - 2 / vista.z, n.y - fs * 0.6, x + w + 2 / vista.z, n.y + fs * 0.6];
      if (n.d > 0 && n !== sopra && presi.some(o => q[0] < o[2] && o[0] < q[2] && q[1] < o[3] && o[1] < q[3])) continue;
      presi.push(q);
      ctx.lineWidth = 3.5 / vista.z; ctx.strokeStyle = C['--foglio']; ctx.lineJoin = 'round';
      ctx.strokeText(t, x, n.y);
      ctx.fillStyle = n.d === 0 ? C['--inchiostro'] : C['--secondo'];
      ctx.fillText(t, x, n.y);
    }
  }
  function ciclo() {
    for (let k = 0; k < 3; k++) passo();
    giri += 3;
    disegna();
    if (giri < 90 || trasc) S.anim = requestAnimationFrame(ciclo);
  }
  const mondo = (cx, cy) => ({ x: (cx - S.gdim.w / 2 - vista.x) / vista.z, y: (cy - S.gdim.h / 2 - vista.y) / vista.z });
  const colpito = (cx, cy) => {
    const p = mondo(cx, cy);
    let best = null, bd = Infinity;
    for (const n of G.nodi) {
      const d = Math.hypot(n.x - p.x, n.y - p.y) - raggio(n) * (n.b > n.a ? 1.7 : 1);
      if (d < 6 / vista.z && d < bd) { best = n; bd = d; }
    }
    return best;
  };
  const tip = document.createElement('div');
  tip.className = 'suggerimento';
  tip.hidden = true;
  tela.appendChild(tip);
  let giu = null;
  cv.onpointerdown = e => {
    cv.setPointerCapture(e.pointerId);
    const r = cv.getBoundingClientRect();
    const n = colpito(e.clientX - r.left, e.clientY - r.top);
    giu = { x: e.clientX, y: e.clientY, vx: vista.x, vy: vista.y, n, mosso: false };
    if (n && n.d !== 0) { trasc = n; alpha = Math.max(alpha, 0.3); giri = 0; cancelAnimationFrame(S.anim); ciclo(); }
    cv.classList.add('trascina');
  };
  cv.onpointermove = e => {
    const r = cv.getBoundingClientRect(), cx = e.clientX - r.left, cy = e.clientY - r.top;
    if (giu) {
      if (Math.hypot(e.clientX - giu.x, e.clientY - giu.y) > 4) giu.mosso = true;
      if (trasc) { const p = mondo(cx, cy); trasc.x = p.x; trasc.y = p.y; }
      else { vista.x = giu.vx + e.clientX - giu.x; vista.y = giu.vy + e.clientY - giu.y; disegna(); }
      return;
    }
    const n = colpito(cx, cy);
    if (n !== sopra) { sopra = n; disegna(); }
    cv.style.cursor = n ? 'pointer' : '';
    if (n) {
      let t = testoPiano(V.h[n.a]);
      if (t.length > 160) t = t.slice(0, 160).replace(/\s\S*$/, '') + '…';
      tip.innerHTML = `<b>${esc(etichetta(n))}</b> · ${esc(D.libri[S.vb[n.a]].t)}<br><span style="font-family:var(--serif)">${esc(t)}</span>`;
      tip.hidden = false;
      tip.style.left = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8) + 'px';
      tip.style.top = Math.min(e.clientY + 14, window.innerHeight - tip.offsetHeight - 8) + 'px';
    } else tip.hidden = true;
  };
  cv.onpointerup = () => {
    cv.classList.remove('trascina');
    const g = giu;
    giu = null;
    if (trasc) { trasc.fisso = true; trasc = null; }
    if (g && g.n && !g.mosso && g.n.d !== 0) vai(`#grafo/${V.id[g.n.a]}${prof > 1 ? '?p=2' : ''}`);
  };
  cv.onpointerleave = () => { if (!giu) { sopra = null; tip.hidden = true; disegna(); } };
  cv.onwheel = e => {
    e.preventDefault();
    const r = cv.getBoundingClientRect();
    zoom(e.deltaY < 0 ? 1.12 : 1 / 1.12, e.clientX - r.left, e.clientY - r.top);
  };
  function zoom(f, cx = S.gdim.w / 2, cy = S.gdim.h / 2) {
    const p = mondo(cx, cy);
    vista.z = Math.max(0.25, Math.min(5, vista.z * f));
    vista.x = cx - S.gdim.w / 2 - p.x * vista.z;
    vista.y = cy - S.gdim.h / 2 - p.y * vista.z;
    disegna();
  }
  $('.grafo-zoom').onclick = e => {
    const z = e.target.closest('button');
    if (!z) return;
    if (+z.dataset.z === 0) { adatta(); disegna(); } else zoom(+z.dataset.z);
  };
  function adatta() {
    // nodes in world units, labels in screen pixels: fit both in the canvas
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, ls = 0, ld = 0;
    for (const n of G.nodi) {
      x0 = Math.min(x0, n.x); x1 = Math.max(x1, n.x); y0 = Math.min(y0, n.y); y1 = Math.max(y1, n.y);
    }
    for (const n of G.nodi) {
      if (n.d === 2) continue;
      const lw = etichetta(n).length * (n.d ? 6.4 : 8) + 18;
      if (n.d > 0 && n.x < 0 && n.x - x0 < 40) ls = Math.max(ls, lw);
      if (!(n.d > 0 && n.x < 0) && x1 - n.x < 40) ld = Math.max(ld, lw);
    }
    const alto = S.gtitolo ? S.gtitolo[3] + 8 : 56, W = S.gdim.w, H = S.gdim.h;
    vista.z = Math.max(0.25, Math.min(1.4, (W - ls - ld - 24) / Math.max(1, x1 - x0), (H - alto - 40) / Math.max(1, y1 - y0)));
    vista.x = (-W / 2 + 12 + ls) - x0 * vista.z + Math.max(0, (W - ls - ld - 24) - (x1 - x0) * vista.z) / 2;
    vista.y = -((y0 + y1) / 2) * vista.z + alto / 2;
  }
  misura();
  for (let k = 0; k < 360; k++) passo();      // settle before the first frame
  adatta();
  ciclo();
  if (S.ro) S.ro.disconnect();
  S.ro = new ResizeObserver(() => { if (!document.body.contains(cv)) return S.ro.disconnect(); misura(); disegna(); });
  S.ro.observe(tela);
  S.ridisegna = () => { C = colori(); disegna(); };
}

// ---------------------------------------------------------------- overview

function matriceDati() {
  if (S.matrice) return S.matrice;
  const nb = D.libri.length, M = Array.from({ length: nb }, () => new Int32Array(nb));
  D.ml.forEach(l => {
    if (!vivo(l)) return;
    M[S.vb[D.mref[l[0]][0]]][S.vb[l[2][0]]]++;
  });
  let max = 0;
  M.forEach((r, a) => r.forEach((v, b) => { if (v > max) max = v; }));
  S.matrice = { M, max };
  return S.matrice;
}
function mostraPanoramica(sel) {
  const t = D.meta.totali, r = D.meta.riepilogo;
  const top = Array.from({ length: S.n }, (_, i) => i).sort((a, b) => S.indeg[b] - S.indeg[a] || a - b).slice(0, 50);
  const tessere = [
    [num(t.books - 1), 'libri', `${num(t.books)} sezioni: Ester due volte`],
    [num(t.chapters), 'capitoli', ''],
    [num(t.verses), 'versetti', `${num(t.poetry_verses)} in poesia`],
    [num(t.notes), 'note della BJ', `${num(r.notes_with_citations)} citano altri passi`],
    [num(r.mref_items), 'rimandi a margine', `in ${num(t.mrefs)} voci a margine, ${String(r.pct_mref_references_resolved).replace('.', ',')}% risolti`],
    [num(r.note_citations), 'citazioni nelle note', `${String(r.pct_note_citations_resolved).replace('.', ',')}% risolte`],
    [num(r.intro_citations), 'citazioni nelle introduzioni', `${t.intros} introduzioni`],
    [num(t.pericopes), 'pericopi', `${num(t.divisions)} divisioni`],
  ];
  // grouped as in the verse panel: a "+" reference is under Nota chiave whatever its sign;
  // the bars add up to the margin references
  const conta = {};
  D.ml.forEach(l => { const g = l[1] >= 4 ? 'numbering' : relNome(l); conta[g] = (conta[g] || 0) + 1; });
  const barre = ['related', 'parallel', 'quoted-later', 'doublet', 'keynote', 'numbering'].map(k => [k, conta[k] || 0]);
  const mx = Math.max(...barre.map(x => x[1]));
  const totBarre = barre.reduce((a, x) => a + x[1], 0);
  pagina(`<div class="pagina"><div class="sopratitolo">Panoramica</div><h1>I collegamenti nel loro insieme</h1>
    <p class="sotto">Conteggi dal testo dei 14 volumi corretti. I rimandi irrisolti (refusi, numerazioni di altre edizioni, libri non canonici) restano visibili in grigio nel pannello del versetto.</p>
    <div class="tessere">${tessere.map(([n, l, s]) => `<div class="tessera"><b>${n}</b><span>${l}</span>${s ? `<small>${s}</small>` : ''}</div>`).join('')}</div>
    <div class="h2">Rimandi a margine per relazione</div>
    <div class="relazioni-barre">${barre.map(([k, v]) => `<span>${REL[k].seg} ${k === 'numbering' ? 'Altra numerazione, commenti' : REL[k].nome}</span><div class="barra-r" style="--c:var(${REL[k].col});width:${(100 * v / mx).toFixed(1)}%"></div><span class="val">${num(v)}</span>`).join('')}</div>
    <p class="sotto nota-barre">${num(totBarre)} rimandi a margine, raggruppati come nel pannello del versetto: un riferimento con «+» sta sotto Nota chiave qualunque sia il suo segno. In tutto i riferimenti con «+» sono ${num(r.keynotes)}: ${num(conta.keynote || 0)} a margine e ${num(r.keynotes - (conta.keynote || 0))} citati nelle note e nelle introduzioni.</p>
    <div class="h2">Matrice libro × libro dei rimandi a margine</div>
    <p class="sotto" style="margin-bottom:.6rem">Righe: il libro dove il rimando è stampato; colonne: il libro indicato. Clic su una cella per l’elenco dei rimandi.</p>
    <div class="matrice-box" id="mbox"><canvas id="mcv"></canvas></div>
    <div class="matrice-leg"><span>1</span><span class="scala" id="mscala"></span><span id="mmax"></span><span>· scala logaritmica · diagonale = rimandi interni al libro</span></div>
    <div id="coppia" class="coppia"></div>
    <div class="h2">I 50 versetti più rimandati</div>
    <p class="sotto" style="margin-bottom:.4rem">Quanti rimandi a margine indicano un passo che comprende il versetto.</p>
    <table class="classifica"><tbody>${top.map((i, k) => `<tr><td class="pos">${k + 1}</td><td class="rif"><a href="${hashVerso(i)}" data-r="${i}-${i}">${esc(rif(i))}</a></td><td class="cnt"><div><i style="width:${(5 * S.indeg[i] / S.indeg[top[0]]).toFixed(2)}rem"></i>${S.indeg[i]}</div></td><td class="frase">${esc(testoPiano(V.h[i]).slice(0, 120))}${testoPiano(V.h[i]).length > 120 ? '…' : ''}</td></tr>`).join('')}</tbody></table>
  </div>`);
  document.title = 'Panoramica · Esploratore dei versetti';
  disegnaMatrice(sel, sel.length === 2);
}
function disegnaMatrice(sel, scorri = false) {
  const { M, max } = matriceDati();
  const nb = D.libri.length, m0 = 48;
  S.m0 = m0;
  const cs = Math.max(7, Math.min(13, Math.floor(($('#mbox').clientWidth - m0 - 8) / nb)));
  S.cella = cs;
  const cv = $('#mcv'), dpr = window.devicePixelRatio || 1, lato = m0 + nb * cs + 6;
  cv.width = lato * dpr; cv.height = lato * dpr; cv.style.width = cv.style.height = lato + 'px';
  const ctx = cv.getContext('2d');
  const C = colori();
  const mix = (a, b, t) => {
    const p = x => [1, 3, 5].map(k => parseInt(x.slice(k, k + 2), 16));
    const A = p(a), B = p(b);
    return `rgb(${A.map((v, k) => Math.round(v + (B[k] - v) * t)).join(',')})`;
  };
  const colore = v => (v ? mix(C['--seq1'], C['--seq9'], Math.log(v) / Math.log(max)) : C['--seq0']);
  $('#mscala').style.background = `linear-gradient(90deg, ${C['--seq1']}, ${C['--seq9']})`;
  $('#mmax').textContent = num(max);
  const [sa, sb] = (sel || []).map(o => S.osis.get(o));
  function disegna(h) {
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, lato, lato);
    for (let a = 0; a < nb; a++) for (let b = 0; b < nb; b++) {
      ctx.fillStyle = colore(M[a][b]);
      ctx.fillRect(m0 + b * cs, m0 + a * cs, cs - 1, cs - 1);
    }
    ctx.strokeStyle = C['--tenue'];
    ctx.lineWidth = 1;
    const s = m0 + (S.ultimoAT + 1) * cs - 0.5;
    ctx.beginPath(); ctx.moveTo(s, m0 - 4); ctx.lineTo(s, m0 + nb * cs); ctx.moveTo(m0 - 4, s); ctx.lineTo(m0 + nb * cs, s); ctx.stroke();
    ctx.font = '600 10px system-ui, sans-serif';
    ctx.fillStyle = C['--secondo'];
    ctx.textBaseline = 'middle';
    D.libri.forEach((b, k) => {
      const forte = k === h?.[0] || k === sa;
      ctx.fillStyle = forte ? C['--inchiostro'] : C['--tenue'];
      ctx.textAlign = 'right';
      ctx.fillText(b.s, m0 - 4, m0 + k * cs + cs / 2);
      ctx.save(); ctx.translate(m0 + k * cs + cs / 2, m0 - 4); ctx.rotate(-Math.PI / 2); ctx.textAlign = 'left';
      ctx.fillStyle = k === h?.[1] || k === sb ? C['--inchiostro'] : C['--tenue'];
      ctx.fillText(b.s, 0, 0); ctx.restore();
    });
    for (const [a, b, col] of [[sa, sb, C['--rubrica']], ...(h ? [[h[0], h[1], C['--inchiostro']]] : [])]) {
      if (a === undefined || b === undefined) continue;
      ctx.strokeStyle = col; ctx.lineWidth = 2;
      ctx.strokeRect(m0 + b * cs - 1, m0 + a * cs - 1, cs + 1, cs + 1);
    }
  }
  disegna();
  const tip = document.createElement('div');
  tip.className = 'suggerimento'; tip.hidden = true;
  document.body.appendChild(tip);
  S.tipMatrice?.remove();
  S.tipMatrice = tip;
  const cella = e => {
    const r = cv.getBoundingClientRect();
    const b = Math.floor((e.clientX - r.left - m0) / cs), a = Math.floor((e.clientY - r.top - m0) / cs);
    return a >= 0 && b >= 0 && a < nb && b < nb ? [a, b] : null;
  };
  cv.onpointermove = e => {
    const c = cella(e);
    disegna(c);
    if (!c) { tip.hidden = true; return; }
    tip.innerHTML = `${esc(D.libri[c[0]].t)} → ${esc(D.libri[c[1]].t)}: <b>${num(M[c[0]][c[1]])}</b> rimandi`;
    tip.hidden = false;
    tip.style.left = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8) + 'px';
    tip.style.top = (e.clientY + 14) + 'px';
  };
  cv.onpointerleave = () => { tip.hidden = true; disegna(); };
  cv.onclick = e => {
    // the list is updated in place, below the matrix, and scrolled into view (no page rebuild)
    const c = cella(e);
    if (!c) return;
    history.replaceState(null, '', `#panoramica/${D.libri[c[0]].o}/${D.libri[c[1]].o}`);
    disegnaMatrice([D.libri[c[0]].o, D.libri[c[1]].o], true);
  };
  if (sa !== undefined && sb !== undefined) mostraCoppia(sa, sb, scorri);
  else if ($('#coppia')) $('#coppia').innerHTML = '<p class="vuoto">Scegli una cella della matrice.</p>';
}
function mostraCoppia(a, b, scorri) {
  const righe = [];
  D.ml.forEach(l => {
    if (!vivo(l)) return;
    const s = D.mref[l[0]][0];
    if (S.vb[s] === a && S.vb[l[2][0]] === b) righe.push([s, l]);
  });
  righe.sort((x, y) => x[0] - y[0]);
  const riga = ([s, l]) => {
    const g = relNome(l), R = REL[g];
    return `<tr><td>${chip([s, s], esc(rif(s)), '', '', '--r-related')}</td><td><span style="color:var(${R.col});font-weight:700" title="${R.nome}">${R.seg}</span></td><td>${chip(l[2], esc(rifRuns(l[2])), ` title="stampato: ${esc(l[11])}"`, '', R.col)}</td></tr>`;
  };
  const lim = 200;
  $('#coppia').innerHTML = `<div class="h2" style="margin-top:1rem">${esc(D.libri[a].t)} → ${esc(D.libri[b].t)} · ${num(righe.length)} rimandi</div>
    <table><tbody>${righe.slice(0, lim).map(riga).join('')}</tbody></table>${righe.length > lim ? `<button class="altro" type="button" id="cmore">mostra altri ${righe.length - lim}</button>` : ''}`;
  const m = $('#cmore');
  if (m) m.onclick = () => { $('#coppia tbody').insertAdjacentHTML('beforeend', righe.slice(lim).map(riga).join('')); m.remove(); };
  if (scorri) {
    const alto = $('.barra').getBoundingClientRect().bottom;
    window.scrollTo({ top: window.scrollY + $('#coppia').getBoundingClientRect().top - alto - 12 });
  }
}

// ---------------------------------------------------------------- events

function tema(nuovo) {
  const r = document.documentElement;
  if (nuovo) { r.dataset.theme = nuovo; memo.set('tema', nuovo); }
  if (S.ridisegna && S.vista === 'grafo') S.ridisegna();
  $('#tema').setAttribute('aria-pressed', String(scuro()));
  if (S.vista === 'panoramica' && $('#mcv')) disegnaMatrice(viaAttuale().via.split('/').slice(1));
}
function scuro() {
  const t = document.documentElement.dataset.theme;
  return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
}
function muovi(delta) {
  if (S.vista !== 'lettore' || !S.capitolo) return;
  const [b, c, s, e] = S.capitolo;
  let i = S.sel;
  if (i === null || i === undefined || i < s || i > e) {
    const alto = $('.barra').getBoundingClientRect().bottom;
    i = s;
    for (let k = s; k <= e; k++) { const r = $('#v' + k).getBoundingClientRect(); if (r.bottom > alto + 4) { i = k; break; } }
    delta = 0;
  }
  let j = i + delta;
  if (j < 0 || j >= S.n) return;
  history.replaceState(null, '', '#' + V.id[j]);
  if (j < s || j > e) mostraCapitolo(S.vb[j], S.vc[j]);
  selezionaVerso(j, j, true);
}
function guida() {
  // a modal dialog: focus moves in, Tab stays in, Esc or the button closes and gives focus back
  const g = $('#guida');
  S.primaGuida = document.activeElement;
  g.innerHTML = `<div role="dialog" aria-modal="true" aria-labelledby="guida-tit" tabindex="-1"><div class="guida-testa"><h2 id="guida-tit">Tasti</h2><button type="button" class="bottone" data-chiudi-guida aria-label="Chiudi">✕</button></div><table>
    <tr><td><kbd>/</kbd></td><td>vai a un riferimento o cerca</td></tr>
    <tr><td><kbd>j</kbd> <kbd>k</kbd></td><td>versetto successivo / precedente</td></tr>
    <tr><td><kbd>n</kbd> <kbd>p</kbd></td><td>capitolo successivo / precedente</td></tr>
    <tr><td><kbd>g</kbd></td><td>grafo del versetto selezionato</td></tr>
    <tr><td><kbd>h</kbd></td><td>evidenzia i versetti più rimandati</td></tr>
    <tr><td><kbd>t</kbd></td><td>tema chiaro / scuro</td></tr>
    <tr><td><kbd>Tab</kbd> <kbd>Invio</kbd></td><td>scorre versetti e richiami di nota, li apre</td></tr>
    <tr><td><kbd>Esc</kbd></td><td>chiude pannello, anteprima, guida</td></tr></table>
    <p class="guida-nota">Indietro e avanti del browser ripercorrono la navigazione; ogni indirizzo (#John.3.16) si può salvare nei preferiti.</p></div>`;
  g.hidden = false;
  g.querySelector('[role="dialog"]').focus();
}
function chiudiGuida() {
  $('#guida').hidden = true;
  S.primaGuida?.focus?.();
}
function calore_(on) {
  document.body.classList.toggle('calore', on);
  $('#calore').setAttribute('aria-pressed', String(on));
  memo.set('calore', on ? '1' : '0');
}

function eventi() {
  window.addEventListener('hashchange', instrada);
  $('#omni').addEventListener('submit', e => {
    e.preventDefault();
    const q = $('#q').value.trim();
    if (!q) return;
    const r = leggiRif(q);
    $('#omni .errore')?.remove();
    if (r && r.errore) {                   // a known book with a chapter or verse it does not have
      $('#omni').insertAdjacentHTML('beforeend', `<div class="errore" role="alert">${esc(r.errore)} · <a href="#cerca?q=${encodeURIComponent(q)}">cerca «${esc(q)}» nel testo</a></div>`);
      return;
    }
    $('#q').blur();
    if (r) vai(hashDi(r));
    else vai('#cerca?q=' + encodeURIComponent(q));
  });
  $('#q').addEventListener('input', () => $('#omni .errore')?.remove());
  $('#calore').onclick = () => calore_(!document.body.classList.contains('calore'));
  $('#tema').onclick = () => tema(scuro() ? 'light' : 'dark');
  $('#aiuto').onclick = guida;
  $('#guida').onclick = e => { if (e.target === $('#guida') || e.target.closest('[data-chiudi-guida]')) chiudiGuida(); };
  $('#guida').addEventListener('keydown', e => {
    if (e.key !== 'Tab') return;
    const f = $$('#guida button, #guida [tabindex="-1"]');
    const primo = f[0], ultimo = f[f.length - 1];
    if (e.shiftKey && document.activeElement === primo) { e.preventDefault(); ultimo.focus(); }
    else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primo.focus(); }
  });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => tema());
  document.addEventListener('pointerdown', e => { puntatore = e.pointerType; }, true);
  document.addEventListener('click', e => {
    if (e.detail === 0) S.fuocoPannello = true;   // activated from the keyboard: focus follows to the panel
    if (e.target.closest('[data-maniglia]')) { $('#pannello').classList.toggle('alto'); return; }
    const nota = e.target.closest('[data-nota]');
    if (nota) S.notaChiave = +nota.dataset.nota;
    const chiudi = e.target.closest('[data-chiudi]');
    if (chiudi) { chiudiPannello(true); return; }
    const anteprima = e.target.closest('[data-r]');
    if (anteprima && puntatore === 'touch' && bersaglio !== anteprima && !e.target.closest('#anteprima')) {
      e.preventDefault();
      mostraAnteprima(anteprima, true);
      return;
    }
    if (!e.target.closest('#anteprima')) nascondiAnteprima();
    const nc = e.target.closest('.nc');
    if (nc) {
      const v = nc.closest('.v');
      S.notaChiave = +nc.dataset.n;
      const id = '#' + V.id[+v.dataset.i];
      if (location.hash === id) mostraPannello(+v.dataset.i); else location.hash = id;
      return;
    }
    const v = e.target.closest('.testo .v');
    if (v && !e.target.closest('a') && !String(getSelection()).trim()) {
      const id = '#' + V.id[+v.dataset.i];
      if (location.hash !== id) location.hash = id;
    }
  });
  document.addEventListener('pointerover', e => {
    if (e.pointerType === 'touch') return;
    const el = e.target.closest('[data-r]');
    if (!el || el.closest('#anteprima')) return;
    clearTimeout(tAnteprima);
    tAnteprima = setTimeout(() => mostraAnteprima(el, false), 120);
  });
  document.addEventListener('pointerout', e => {
    if (e.pointerType === 'touch') return;
    const el = e.target.closest('[data-r]');
    if (!el || (e.relatedTarget && el.contains(e.relatedTarget))) return;
    clearTimeout(tAnteprima);
    tAnteprima = setTimeout(nascondiAnteprima, 150);
  });
  $('#anteprima').addEventListener('pointerover', () => clearTimeout(tAnteprima));
  $('#anteprima').addEventListener('pointerout', e => { if (e.pointerType !== 'touch') tAnteprima = setTimeout(nascondiAnteprima, 150); });
  const via = () => { if (!$('#anteprima').hidden && puntatore !== 'touch') nascondiAnteprima(); };
  window.addEventListener('scroll', via, { passive: true });
  $('#pannello').addEventListener('scroll', via, { passive: true });
  document.addEventListener('keydown', e => {
    const campo = e.target.closest('input, select, textarea');
    if (e.key === 'Escape') {
      if (!$('#guida').hidden) { chiudiGuida(); return; }
      if (!$('#anteprima').hidden) { nascondiAnteprima(); return; }
      if (campo) { e.target.blur(); return; }
      if (!$('#pannello').hidden) chiudiPannello(true);
      return;
    }
    if (campo || e.ctrlKey || e.metaKey || e.altKey) return;
    if (!$('#guida').hidden) return;
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.testo .v')) {
      e.preventDefault();
      S.fuocoPannello = true;
      const id = '#' + V.id[+e.target.dataset.i];
      if (location.hash === id) mostraPannello(+e.target.dataset.i); else location.hash = id;
      return;
    }
    const cap = S.capitolo;
    switch (e.key) {
      case '/': e.preventDefault(); $('#q').focus(); $('#q').select(); break;
      case 'j': muovi(1); break;
      case 'k': muovi(-1); break;
      case 'n': case 'p': {
        if (!cap) break;
        const a = e.key === 'n' ? $('.sfoglia a[aria-label="Capitolo successivo"]') : $('.sfoglia a[aria-label="Capitolo precedente"]');
        if (a) location.hash = a.getAttribute('href');
        break;
      }
      case 'g': if (S.sel !== null && S.sel !== undefined && S.vista === 'lettore') location.hash = '#grafo/' + V.id[S.sel]; break;
      case 'h': calore_(!document.body.classList.contains('calore')); break;
      case 't': tema(scuro() ? 'light' : 'dark'); break;
      case '?': guida(); break;
      default: return;
    }
  });
}

async function avvia() {
  const t = memo.get('tema');
  if (t === 'light' || t === 'dark') document.documentElement.dataset.theme = t;
  $('#tema').setAttribute('aria-pressed', String(scuro()));
  if (!('DecompressionStream' in window)) {
    $('#attesa').textContent = 'Questo browser non sa decomprimere i dati (DecompressionStream): serve un browser recente.';
    return;
  }
  try {
    D = await carica();
  } catch (err) {
    $('#attesa').textContent = 'Impossibile leggere i dati incorporati: ' + err;
    throw err;
  }
  const t1 = performance.now();
  indici();
  eventi();
  calore_(memo.get('calore') === '1');
  instrada();
  const t2 = performance.now();
  window.__esploratore = { dati: Math.round(t1 - T0), indici: Math.round(t2 - t1), pronto: Math.round(t2 - T0) };
  console.info('esploratore pronto in %d ms (dati %d ms)', t2 - T0, t1 - T0);
}
avvia();
