// Esploratore dei versetti: one offline page over the verse graph of the Bibbia di Gerusalemme.
// The data (built by tools/ontologia/esploratore.py) is gzip+base64 JSON in <script id="dati">.
'use strict';

const T0 = performance.now();
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const ESC = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = s => String(s).replace(/[&<>"']/g, c => ESC[c]);
const num = n => n.toLocaleString('it-IT');
const quanti = (n, uno, tanti) => `${num(n)} ${n === 1 ? uno : tanti}`;
const pl = (n, uno, tanti) => (n === 1 ? uno : tanti);          // the Italian plural of a count (R3 E3)
const conta = (n, uno, tanti) => `<b>${num(n)}</b> ${pl(n, uno, tanti)}`;
const memo = {
  get(k) { try { return localStorage.getItem('esplora.' + k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem('esplora.' + k, v); } catch (e) { /* private mode */ } },
};

let D, V, Z;       // payload, its verse columns, the dictionary
const S = {};      // derived indices and UI state

// relations of the margin references, in display order; 'keynote' is a "+" reference
const REL = {
  parallel: { nome: 'Paralleli', seg: '‖', col: '--r-parallel', entr: 'Paralleli', dash: [] },
  'quoted-later': { nome: 'Citato in', seg: '↗', col: '--r-quoted', entr: 'Cita questi passi', dash: [] },
  doublet: { nome: 'Doppioni', seg: '=', col: '--r-doublet', entr: 'Doppioni', dash: [] },
  keynote: { nome: 'Nota chiave', seg: '+', col: '--r-keynote', entr: 'Rinviano qui per la nota chiave', dash: [2, 3] },
  related: { nome: 'Affini', seg: '·', col: '--r-related', txt: '--secondo', entr: 'Affini', dash: [] },
  cites: { nome: 'Citazioni nelle note', seg: '§', col: '--r-cites', txt: '--secondo', entr: 'Citato nelle note', dash: [5, 4] },
  numbering: { nome: 'Altra numerazione', seg: '#', col: '--r-related', txt: '--secondo', entr: '', dash: [] },
  // the entries of the Dizionario di Teologia Biblica (X. Léon-Dufour) citing the verse
  diz: { nome: 'Nel Dizionario', seg: '◊', col: '--r-diz', entr: 'Nel Dizionario', dash: [1, 3] },
};
const ORDINE_REL = ['parallel', 'quoted-later', 'doublet', 'keynote', 'related', 'cites', 'diz'];
const STRETTA = 3;   // a citation of at most 3 verses names the verse "on its own" (marker, heat)

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
  indiciDizionario();
  indiciParatesto();
  indiciIntegrazione();
}
function indiciDizionario() {
  // per verse: the citations of the dictionary naming a passage that includes it (all, and those
  // of at most STRETTA verses); per entry: its citations; entries by slug
  Z = D.diz;
  const n = S.n, tutte = new Int32Array(n + 1), strette = new Int32Array(n + 1);
  S.citDi = Z.voci.map(() => []);
  Z.cit.forEach((c, k) => {
    S.citDi[c[0]].push(k);
    const r = c[3], stretta = ampiezza(r) <= STRETTA;
    for (let j = 0; j < r.length; j += 2) {
      tutte[r[j]]++; tutte[r[j + 1] + 1]--;
      if (stretta) { strette[r[j]]++; strette[r[j + 1] + 1]--; }
    }
  });
  S.dizN = new Int32Array(n);
  S.dizS = new Int32Array(n);
  let a = 0, b = 0;
  for (let i = 0; i < n; i++) { a += tutte[i]; b += strette[i]; S.dizN[i] = a; S.dizS[i] = b; }
  S.voceSlug = new Map(Z.voci.map((v, k) => [v[0], k]));
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
    ['cantico', 'Song'], ['qoelet', 'Eccl'], ['giov', 'John'], ['ecclesiaste', 'Eccl'], ['eccle', 'Eccl'], ['ecc', 'Eccl'],
    ['ecclesiastico', 'Sir'], ['eccli', 'Sir'], ['qohelet', 'Eccl'], ['apoc', 'Rev'], ['deut', 'Deut']]) m.set(k, S.osis.get(o));
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
  let j = tok.findIndex((x, k) => (k > 0 || !/^[1-3]$/.test(x) && !/^[1-3][A-Za-zÀ-ÿ]/.test(x)) && /^(\d|prol)/i.test(x));
  if (j < 0) j = tok.length;
  if (j === 0) return null;
  const b = S.libriTab.get(chiaveLibro(tok.slice(0, j).join(' ')));
  if (b === undefined) return null;
  const r = tok.slice(j);
  // "Gv 3 16": chapter and verse when the first number is a chapter of the book (R3 E7)
  if (r.length === 2 && /^\d+$/.test(r[0]) && /^\d+[a-z]*$/.test(r[1]) && trovaCap(b, r[0])) return { b, resto: r[0] + ',' + r[1], sigla: tok.slice(0, j).join(' ') };
  return { b, resto: r.join(''), sigla: tok.slice(0, j).join(' ') };
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
  // «Lettera di Geremia» is Baruch 6 in this Bible (R3 E7)
  testo = testo.replace(/^\s*lettera di geremia\b\s*/i, m => 'Bar 6' + (m.trim() === testo.trim() ? '' : ','));
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
function indiceDiz(I) {
  // the dictionary, normalised on the first search that includes it: names and paragraphs
  if (I.dp) return;
  const t = performance.now();
  I.dk = [];
  I.dp = [];
  Z.voci.forEach((v, k) => v[9].forEach((p, j) => { I.dk.push([k, j]); I.dp.push(testoPar(k, j)); }));
  I.dpn = I.dp.map(normalizza);
  I.dnomi = Z.voci.map(v => normalizza(v[1]));
  I.ms += performance.now() - t;
}
function evidenzia(testo, norm, termini, max = 220) {
  const segni = [];
  for (const t of termini) {
    t.g.lastIndex = 0;               // matchAll copies lastIndex, which a test() elsewhere may have moved
    for (const m of norm.matchAll(t.g)) segni.push([m.index, m.index + m[0].length]);
  }
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

// ---------------------------------------------------------------- the dictionary: helpers

// Z.voci: [slug, name, kind 0 full / 1 redirect, letter, pages, authors [[k, part]], signatures
// [[text, after paragraph j]], targets [[entry, path, paragraph n, form]], sections [[path, label,
// title HTML, depth, kind]], paragraphs [[n, section, page, HTML]]]; Z.cit: [entry, paragraph
// index (-1 a section title), section index (-1 before the first heading), runs, status, flags,
// printed text, reason]. Citations are <a class="cd" data-d="k k2"> in the HTML.
const FLAG_DIZ = {
  s: ['s', 'e il versetto seguente'], ss: ['ss', 'e seguenti (fino alla fine della pericope)'],
  p: ['par.', 'e i passi paralleli (non elencati)'], '…': ['…', 'e altrove'],
};
const nomeVoce = k => Z.voci[k][1];
const rinvio = k => Z.voci[k][2] === 1;
function hashVoce(k, n = 0, verso = null) {
  return `#voce/${Z.voci[k][0]}${n ? '/' + n : ''}${verso !== null && verso !== undefined ? '?v=' + V.id[verso] : ''}`;
}
const sezioneDi = (k, s) => (s < 0 ? null : Z.voci[k][8][s]);
function etichettaSez(x) {
  // a heading as printed: "Antico Testamento", "A. L'IRA DELL'UOMO", "I. DIO È PRIMO", "1. El",
  // "a) La vita intera", «Segno di benedizione», "INTRODUZIONE"
  const [, lab, tit, , kind] = x;
  if (kind === 'testament') return tit === lab ? esc(lab) : tit;
  if (kind === 'alpha') return `${esc(lab)}) ${tit}`;
  if (kind === 'runin') return `«${tit}»`;
  if (kind === 'caps' || !lab) return tit;
  return `${esc(lab)}. ${tit}`;
}
function primoParDi(k, s) {
  // the first paragraph of section s or after it (a citation in a section title opens there)
  const ps = Z.voci[k][9];
  const j = ps.findIndex(p => p[1] >= s);
  return j < 0 ? 0 : ps[j][0];
}
function testoPar(k, j) {
  const p = Z.voci[k][9][j];
  if (p[4] === undefined) p[4] = testoPiano(p[3]);
  return p[4];
}
function htmlCit(k) {
  const c = Z.cit[k];
  return c[1] >= 0 ? Z.voci[c[0]][9][c[1]][3] : Z.voci[c[0]][8][c[2]][2];
}
function fraseCit(k, max = 200) {
  // the paragraph around citation k, from a word start, the citation marked
  const h = htmlCit(k);
  const m = new RegExp(`<a class="cd" data-d="(?:\\d+ )*${k}(?: \\d+)*">([^<]*)</a>`).exec(h);
  const testo = testoPiano(h);
  if (!m) return esc(testo.slice(0, max));
  return contestoA(testo, testoPiano(h.slice(0, m.index)).length, m[1].length, max);
}
function flagsDiz(f) {
  return f ? f.split(' ').map(x => `<span class="fl" title="${esc(FLAG_DIZ[x][1])}">${esc(FLAG_DIZ[x][0])}</span>`).join('') : '';
}
function dizDi(i) {
  // the entries citing verse i, with their citations: the most specific first, then by name
  const per = new Map();
  Z.cit.forEach((c, k) => {
    if (!contiene(c[3], i)) return;
    if (!per.has(c[0])) per.set(c[0], []);
    per.get(c[0]).push(k);
  });
  const largo = ks => Math.min(...ks.map(k => ampiezza(Z.cit[k][3])));
  return [...per].sort((x, y) => largo(x[1]) - largo(y[1]) || nomeVoce(x[0]).localeCompare(nomeVoce(y[0]), 'it'));
}
function vociCapitolo(s, e) {
  // verse -> the entries citing it (all citations), for the verses s..e of a chapter
  const out = new Map();
  Z.cit.forEach(c => {
    const r = c[3];
    for (let j = 0; j < r.length; j += 2) {
      for (let i = Math.max(s, r[j]); i <= Math.min(e, r[j + 1]); i++) {
        if (!out.has(i)) out.set(i, new Set());
        out.get(i).add(c[0]);
      }
    }
  });
  return out;
}
function segnoDiz(i, voci) {
  // ◊ in the margin: a citation of the dictionary names this verse on its own or in a passage
  // of at most STRETTA verses
  if (!S.dizS[i]) return '';
  const nv = voci ? voci.size : 0;
  return `<span class="md" title="Nel Dizionario di Teologia Biblica: ${nv} ${nv === 1 ? 'voce' : 'voci'}, ${S.dizN[i]} ${S.dizN[i] === 1 ? 'citazione' : 'citazioni'}">◊</span>`;
}
const caloreDiz = d => (d >= 10 ? 5 : d >= 5 ? 4 : d >= 3 ? 3 : d >= 2 ? 2 : d >= 1 ? 1 : 0);
function collegaDiz(radice, verso = null) {
  // the <a class="cd" data-d> citations of the dictionary get their target (the whole passage
  // when it is one run) and the preview; unresolved ones are grey with their reason
  $$('a.cd', radice).forEach(a => {
    const r = [], motivi = [];
    for (const k of a.dataset.d.split(' ').map(Number)) {
      r.push(...Z.cit[k][3]);
      if (Z.cit[k][7] && !motivi.includes(Z.cit[k][7])) motivi.push(Z.cit[k][7]);
    }
    if (!r.length) {
      // unresolved: no target; the reason is shown in the preview (hover, tap, keyboard focus)
      const perche = motivi.join('; ') || 'riferimento non risolto';
      a.classList.add('x');
      a.dataset.x = perche;
      a.tabIndex = 0;
      a.setAttribute('role', 'button');
      a.setAttribute('aria-label', `${a.textContent}: riferimento non risolto, ${perche}`);
      return;
    }
    a.href = r.length === 2 ? hashVerso(r[0], r[1]) : hashVerso(r[0]);
    a.dataset.r = runsAttr(r);
    if (motivi.length) a.title = motivi.join('; ');
    if (verso !== null && contiene(r, verso)) a.classList.add('sel');
  });
}
function rigaCitDiz(k, i) {
  // one citation of verse i in the panel: section of the entry, the passage when wider, flags,
  // the sentence around it
  const c = Z.cit[k], s = sezioneDi(c[0], c[2]);
  const n = c[1] >= 0 ? Z.voci[c[0]][9][c[1]][0] : primoParDi(c[0], c[2]);
  const sez = s ? `<span class="percorso">${esc(s[0])}</span>${esc(testoPiano(s[2]))}` : '<span class="percorso">introd.</span>';
  const largo = ampiezza(c[3]) > 1 ? `<small class="passo">${esc(rifRuns(c[3]))}</small>` : '';
  return `<li><a class="dsez" href="${hashVoce(c[0], n, i)}">${sez}</a>${largo}${flagsDiz(c[5])}<span class="frase">${fraseCit(k)}</span></li>`;
}
function sezioneDiz(i, DZ) {
  const n = DZ.reduce((t, x) => t + x[1].length, 0);
  let h = `<section class="sez diz"><h3>Nel Dizionario di Teologia Biblica <span class="n">${DZ.length}</span></h3>`;
  if (!DZ.length) return h + '<p class="vuoto">Nessuna voce del Dizionario cita questo versetto.</p></section>';
  h += `<p class="diz-sotto">${DZ.length} ${DZ.length === 1 ? 'voce' : 'voci'}, ${n} ${n === 1 ? 'citazione' : 'citazioni'}; prima le più puntuali. Clic su una sezione per leggerla nella voce.</p>`;
  const blocco = ([v, ks]) => `<div class="dvoce"><h4><span class="seg">◊</span><a href="${hashVoce(v)}">${esc(nomeVoce(v))}</a><span class="n">${ks.length}</span></h4><ul class="elenco">${ks.map(k => rigaCitDiz(k, i)).join('')}</ul></div>`;
  const primi = 8;
  h += DZ.slice(0, primi).map(blocco).join('');
  if (DZ.length > primi) h += `<details class="altri"><summary class="altro">mostra altre ${DZ.length - primi} voci</summary>${DZ.slice(primi).map(blocco).join('')}</details>`;
  return h + '</section>';
}

// ---------------------------------------------------------------- the dictionary: an entry

function entrantiVoce(k) {
  // the entries pointing here: a *word in their text, a see-also or a redirect (memoised)
  if (!S.entrantiVoci) {
    S.entrantiVoci = Z.voci.map(() => new Set());
    Z.voci.forEach((v, j) => {
      for (const t of v[7]) if (t[0] >= 0 && t[0] !== j) S.entrantiVoci[t[0]].add(j);
      for (const p of v[9]) for (const m of p[3].matchAll(/href="#voce\/([^"]+)"/g)) {
        const t = S.voceSlug.get(m[1]);
        if (t !== undefined && t !== j) S.entrantiVoci[t].add(j);
      }
    });
  }
  return [...S.entrantiVoci[k]].sort((a, b) => nomeVoce(a).localeCompare(nomeVoce(b), 'it'));
}
function linkVoce(k, testo = nomeVoce(k)) {
  return `<a class="vl${rinvio(k) ? ' rinvio' : ''}" href="${hashVoce(k)}">${esc(testo)}</a>`;
}
const percorsoStampato = p => (p === '0' ? 'introd.' : p);
const vociDistinte = v => new Set(v[7].filter(t => t[0] >= 0).map(t => t[0])).size;
function bersagliVoce(v) {
  // targets of a redirect or a see-also list: the entry, the section path as printed ('0':
  // the paragraphs before the first heading); a target that is itself a redirect shows where
  // it leads
  return v[7].map(([t, path, n, form]) => {
    const p = path ? ` <small>${esc(percorsoStampato(path))}</small>` : '';
    if (t < 0) return `<li><span class="vl-x" title="voce non trovata nel Dizionario">${esc(form)}</span>${p}</li>`;
    const oltre = rinvio(t) ? ` <small class="oltre">→ ${[...new Set(Z.voci[t][7].filter(x => x[0] >= 0).map(x => x[0]))]
      .map(j => linkVoce(j)).join(', ')}</small>` : '';
    return `<li>${linkVoce(t).replace(`href="${hashVoce(t)}"`, `href="${hashVoce(t, n)}"`)}${p}${oltre}</li>`;
  }).join('');
}
function slugVoce(s) {
  // 'AGNELLO-DI-DIO', 'agnello di dio', 'Agnello di Dio' -> 'agnello-di-dio'
  return normalizza(s).replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}
function mostraVoce(arg, par = {}) {
  const [slug0, nn] = arg.split('/');
  let slug = slug0, k = S.voceSlug.get(slug);
  if (k === undefined && S.voceSlug.has(slugVoce(slug0))) {
    slug = slugVoce(slug0);
    k = S.voceSlug.get(slug);
    const q = location.hash.indexOf('?');
    history.replaceState(null, '', `#voce/${slug}${nn ? '/' + nn : ''}${q < 0 ? '' : location.hash.slice(q)}`);
  }
  if (k === undefined) {
    pagina(`<div class="pagina"><h1>Voce non trovata</h1><p class="sotto">«${esc(arg)}» non è una voce del Dizionario di Teologia Biblica.</p><p><a href="#dizionario">Tutte le voci</a></p></div>`);
    document.title = 'Voce non trovata · Dizionario';
    return;
  }
  const v = Z.voci[k], [, nome, tipo, , pag, autori, firme, bersagli, sezioni, paragrafi] = v;
  const verso = par.v !== undefined ? S.vix.get(par.v) ?? null : null;
  const ks = S.citDi[k], risolte = ks.filter(c => Z.cit[c][3].length);
  const libri = new Set(risolte.map(c => S.vb[Z.cit[c][3][0]]));
  const ent = entrantiVoce(k);
  const nomiAut = [...new Set(autori.map(a => Z.aut[a[0]]))];
  let h = '';
  if (tipo === 1) {
    const nv = vociDistinte(v);
    h = `<p class="rinvio-nota">Voce di rinvio: l’argomento è trattato in ${nv === 1 ? 'questa voce' : `queste ${nv} voci`}${bersagli.length > nv ? ` (${bersagli.length} rimandi a sezioni)` : ''}.</p><ul class="rinvii">${bersagliVoce(v)}</ul>`;
  } else {
    // the text: headings of the sections as printed, paragraphs with their page, signatures
    // the path as printed ("VT II 1") beside a heading below the first level, where it says more
    const titolo = s => `<div class="dsez-tit l${Math.min(4, sezioni[s][3])} k-${sezioni[s][4]}" id="s${s}" role="heading" aria-level="${Math.min(6, sezioni[s][3] + 1)}">${sezioni[s][3] > 1 ? `<span class="percorso">${esc(sezioni[s][0])}</span>` : ''}${etichettaSez(sezioni[s])}</div>`;
    let pg = null, s0 = -1;
    paragrafi.forEach(([n, s, p, html], j) => {
      for (let t = s0 + 1; t <= s; t++) h += titolo(t);
      s0 = Math.max(s0, s);
      h += `<p class="dpar" id="p${n}" data-n="${n}">${p !== pg ? `<span class="pg">p. ${esc(p)}</span>` : ''}${html}</p>`;
      pg = p;
      for (const [f, dopo] of firme) if (dopo === j) h += `<p class="firma">${esc(f)}</p>`;
    });
    for (let t = s0 + 1; t < sezioni.length; t++) h += titolo(t);
    const indice = sezioni.length > 3 ? `<details class="voce-indice"${window.innerWidth > 1240 ? ' open' : ''}><summary>Sezioni <span class="n">${sezioni.length}</span></summary><ol>${sezioni.map((x, s) =>
      `<li class="l${Math.min(4, x[3])}"><a href="${hashVoce(k, primoParDi(k, s))}">${etichettaSez(x).replace(/<a [^>]*>|<\/a>/g, '')}</a></li>`).join('')}</ol></details>` : '';
    h = `<div class="voce-corpo">${indice}<div class="voce-testo">${h}</div></div>`;
    if (bersagli.length) h += `<div class="h2" role="heading" aria-level="2">Vedi anche</div><ul class="rinvii">${bersagliVoce(v)}</ul>`;
  }
  if (ent.length) {
    h += `<div class="h2" role="heading" aria-level="2">Rimandano a questa voce <span class="n">${ent.length}</span></div><p class="entranti">${ent.map(j => linkVoce(j)).join(' · ')}</p>`;
  }
  const sotto = tipo === 1 ? `rinvio · p. ${esc(pag)}`
    : `${nomiAut.length ? 'di ' + nomiAut.map(esc).join(', ') + ' · ' : ''}p. ${esc(pag)} · ${sezioni.length} ${sezioni.length === 1 ? 'sezione' : 'sezioni'} · ${paragrafi.length} paragrafi · ${num(ks.length)} citazioni bibliche${libri.size ? ` in ${libri.size} ${libri.size === 1 ? 'libro' : 'libri'}` : ''}`;
  pagina(`<div class="pagina voce-pagina"><div class="sopratitolo"><a href="#dizionario">Dizionario di Teologia Biblica</a>${verso !== null ? ` · da <a href="${hashVerso(verso)}">${esc(rif(verso))}</a>` : ''}</div>
    <h1>${esc(nome)}</h1>${ancheIn('v' + k, [], S.festaAnche.get('v' + k) || [])}<p class="sotto">${sotto}</p>${h}</div>`);
  collegaDiz($('#vista'), verso);
  document.title = `${nome} · Dizionario di Teologia Biblica`;
  if (nn) {
    const p = $('#p' + nn);
    if (p) {
      p.classList.add('sel');
      // the headings right above the paragraph stay in view
      let cima = p;
      while (cima.previousElementSibling?.classList.contains('dsez-tit')) cima = cima.previousElementSibling;
      const alto = $('.barra').getBoundingClientRect().bottom;
      window.scrollTo(0, cima.getBoundingClientRect().top + window.scrollY - alto - 16);
    } else if (tipo === 0) {
      $('#vista h1').insertAdjacentHTML('afterend', `<p class="avviso">Questa voce non ha un paragrafo ${esc(nn)}: ne ha ${paragrafi.length}.</p>`);
    }
  }
}

// ---------------------------------------------------------------- the dictionary: index

function mostraDizionario(par = {}) {
  const m = Z.meta;
  const lettere = [...new Set(Z.voci.map(v => v[3]))];
  const conta = k => S.citDi[k].length;
  const per = l => Z.voci.map((v, k) => k).filter(k => Z.voci[k][3] === l).map(k => rinvio(k)
    ? `<a class="dvl rinvio" href="${hashVoce(k)}" data-nome="${esc(normalizza(nomeVoce(k)))}" title="rinvio a ${quanti(vociDistinte(Z.voci[k]), 'voce', 'voci')}"><i>${esc(nomeVoce(k))}</i><span>→ ${vociDistinte(Z.voci[k])}</span></a>`
    : `<a class="dvl" href="${hashVoce(k)}" data-nome="${esc(normalizza(nomeVoce(k)))}" title="${conta(k)} citazioni bibliche"><b>${esc(nomeVoce(k))}</b><span>${num(conta(k))}</span></a>`).join('');
  pagina(`<div class="pagina dizionario"><div class="sopratitolo">X. Léon-Dufour (a cura di) · Marietti 1976</div>
    <h1>Dizionario di Teologia Biblica</h1>
    <p class="sotto">${num(m.piene)} voci e ${num(m.rinvii)} rinvii (in corsivo, con il numero delle voci a cui rimandano). Accanto a ogni voce il numero delle citazioni bibliche: ${num(m.citazioni)} in tutto, ${String(m.pct).replace('.', ',')}% riconosciute in ${num(m.versetti)} versetti di questa Bibbia.</p>
    <div class="diz-campi"><input type="search" id="dq" value="${esc(par.q || '')}" placeholder="Filtra le voci…" aria-label="Filtra le voci" spellcheck="false">
    <nav class="lettere" aria-label="Lettere">${lettere.map(l => `<button type="button" data-l="${esc(l)}">${esc(l)}</button>`).join('')}</nav></div>
    ${lettere.map(l => `<section class="lettera" id="lett-${esc(l)}"><h2>${esc(l)}</h2><div class="dvoci">${per(l)}</div></section>`).join('')}
    <p class="vuoto" id="dnessuna" hidden>Nessuna voce corrisponde.</p></div>`);
  document.title = 'Dizionario di Teologia Biblica · Esploratore dei versetti';
  $('.lettere').addEventListener('click', e => {
    const b = e.target.closest('[data-l]');
    if (!b) return;
    const alto = $('.barra').getBoundingClientRect().bottom;
    window.scrollTo(0, $('#lett-' + b.dataset.l).getBoundingClientRect().top + window.scrollY - alto - 8);
  });
  // the filter is kept in the address (#dizionario?q=), so Back returns to it; a letter with no
  // entry left is disabled
  const filtra = () => {
    const testo = $('#dq').value.trim(), q = normalizza(testo);
    let tot = 0;
    $$('.lettera').forEach(sez => {
      let n = 0;
      $$('.dvl', sez).forEach(a => { const ok = !q || a.dataset.nome.includes(q); a.hidden = !ok; n += ok; });
      sez.hidden = !n;
      $(`.lettere [data-l="${sez.id.slice(5)}"]`).disabled = !n;
      tot += n;
    });
    $('#dnessuna').hidden = tot > 0;
    return testo;
  };
  $('#dq').addEventListener('input', () => {
    const testo = filtra();
    history.replaceState(history.state, '', '#dizionario' + (testo ? '?q=' + encodeURIComponent(testo) : ''));
  });
  if (par.q) filtra();
  ripristinaScorrimento();
}
function ripristinaScorrimento() {
  // Back to the index or a search: the scroll position this history entry had (memoScorrimento)
  const y = history.state?.y;
  if (y) requestAnimationFrame(() => window.scrollTo(0, y));
}
let tScorri = null;
function memoScorrimento() {
  // the scroll position of the dictionary index and of the search, kept in the history entry
  clearTimeout(tScorri);
  tScorri = setTimeout(() => {
    if (S.vista === 'dizionario' && !location.hash.startsWith('#voce/') || S.vista === 'cerca' || S.vista === 'apparati' ||
        S.vista === 'lettore' && S.sel === null) {
      history.replaceState({ ...(history.state || {}), y: Math.round(window.scrollY) }, '', location.href);
    }
  }, 120);
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
  else if (via === 'dizionario') { vista = 'dizionario'; mostraDizionario(parametri(query)); }
  else if (via.startsWith('voce/')) { vista = 'dizionario'; mostraVoce(via.slice(5), parametri(query)); }
  else if (/^(introduzione-generale|indice-note|temi|cronologia|appendici|persona|calendario|misure|carte)(\/|$)/.test(via)) {
    vista = 'apparati';
    const [v0, ...resto] = via.split('/'), arg = resto.join('/');
    if (v0 === 'introduzione-generale') mostraPreliminari(arg);
    else if (v0 === 'appendici') mostraAppendici();
    else if (v0 === 'persona') mostraPersona(arg);
    else if (v0 === 'calendario') mostraCalendario(parametri(query));
    else if (v0 === 'misure') mostraMisure(parametri(query));
    else if (v0 === 'carte') mostraCarte();
    else if (v0 === 'cronologia') mostraCronologia(arg, parametri(query));
    else mostraIndiceAnalitico(v0 === 'temi' ? 'temi' : 'note', arg, parametri(query));
  }
  else vista = mostraRif(via, parametri(query));
  $$('.schede a').forEach(a => a.classList.toggle('attiva', a.dataset.vista === vista ||
    (vista === 'lettore' && a.dataset.vista === 'indice') || (vista === 'panoramica' && a.dataset.vista === 'apparati' && window.innerWidth <= 720)));
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
    const giaQui = S.capitolo && S.capitolo[0] === b && S.capitolo[1] === c && $('#vista .lettore');
    mostraCapitolo(b, c);
    selezionaVerso(null);
    if (!giaQui) ripristinaScorrimento();
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
function nonTrovato(via, cosa = null) {
  // a message for the view the address names (R3 E4), and a title of its own (announced to screen readers)
  let msg = `«${esc(via)}» non corrisponde a un libro, un capitolo o un versetto.`, torna = '<a href="#">Torna all’indice dei libri</a>';
  const p = via.split('.'), b = S.osis.get(p[0]);
  if (cosa) [msg, torna] = cosa;
  else if (b !== undefined && p.length >= 2) {
    const r = leggiParte(b, p.slice(1, 2).join('') + (p[2] ? ',' + p.slice(2).join('.') : ''), null);
    if (r && r.errore) msg = esc(r.errore) + '.';
    torna = `<a href="#${D.libri[b].o}">${esc(D.libri[b].t)}: tutti i capitoli</a>`;
  }
  pagina(`<div class="pagina"><h1>Non trovato</h1><p class="sotto">${msg}</p><p>${torna}</p></div>`);
  document.title = 'Non trovato · Esploratore dei versetti';
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
      <span><b>${num(Z.meta.piene)}</b> voci del <a href="#dizionario">Dizionario di Teologia Biblica</a> <small>${num(Z.meta.citazioni)} citazioni</small></span>
    </div>
    <div class="h2"><a href="#appendici">Introduzione generale e appendici</a></div>
    <div class="apparati">
      <a class="apparato" href="#introduzione-generale"><b>Introduzione generale</b><span>presentazione, prefazioni, canone, abbreviazioni, avvertenze</span></a>
      <a class="apparato" href="#indice-note"><b>Indice delle note</b><span>${num(A.meta.note.entries)} voci · ${num(A.meta.note.references)} riferimenti alle note</span></a>
      <a class="apparato" href="#temi"><b>Temi pastorali</b><span>${num(A.meta.temi.entries)} temi · ${num(A.meta.temi.references)} riferimenti</span></a>
      <a class="apparato" href="#cronologia"><b>Tavola cronologica</b><span>${num(A.meta.cron)} voci · dinastie</span></a>
    </div>
    <p class="sotto altre-app"><a href="#appendici">Tutte le appendici</a>: <a href="#cronologia/dinastie">dinastie</a> · <a href="#calendario">calendario</a> · <a href="#misure">misure e monete</a> · <a href="#carte">carte</a></p>
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
    <p class="sotto">${esc(L.s)} · ${quanti(L.c.length, 'capitolo', 'capitoli')} · ${quanti(e - s + 1, 'versetto', 'versetti')} · ${quanti(nn, 'nota', 'note')} · ${quanti(nm, 'rimando', 'rimandi')} a margine</p>
    ${intros.map(x => `<a class="intro-link" href="#intro/${esc(x[0])}">Introduzione: ${esc(x[1])}</a>`).join('')}
    <div class="h2">Capitoli</div>
    <div class="capitoli">${L.c.map(c => `<a href="#${L.o}.${c[0]}">${c[0] === 'Prol' ? 'Prol.' : c[0]}</a>`).join('')}</div>
    ${cronLibro(b)}
    ${schema ? `<div class="h2">Struttura</div><ul class="schema">${schema}</ul>` : ''}
  </div>`);
  document.title = L.t + ' · Esploratore dei versetti';
}

// ---------------------------------------------------------------- reader

function cronLibro(b) {
  // the chronology entries dating the book (cronologia-libri.tsv) or citing it (R2-15)
  const xs = (S.libroDat.get(b) || []).sort((x, y) => (x[1] === 3) - (y[1] === 3) || x[0] - y[0]);
  if (!xs.length) return '';
  const riga = ([n, t]) => { const v = A.cron.voci[n - 1]; return `<li><a href="${hashCron(n)}">${v[7] ? esc(v[7]) : esc(A.cron.sez[v[0] - 1][1].split('.')[0])}</a> <small>${DATAZIONE[t]}</small><span class="frase">${esc(v[11].length > 150 ? v[11].slice(0, 149) + '…' : v[11])}</span></li>`; };
  return `<div class="h2">Nella tavola cronologica <span class="n">${xs.length}</span></div>${elencoBreve(xs.map(riga), 4)}`;
}
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
  const dv = vociCapitolo(s, e);
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
    const pg = V.pg[i] !== pag ? `<span class="pg" title="pagina stampata">p. ${V.pg[i]}</span>` : '';
    pag = V.pg[i];
    const cl = 'v' + (poesia ? ' vp' : '') + (S.indeg[i] ? ' k' + calore(S.indeg[i]) : '') + (S.dizS[i] ? ' d' + caloreDiz(S.dizS[i]) : '');
    const nv = dv.get(i)?.size || 0;
    const aria = rif(i) + (nv ? `, citato in ${nv} ${nv === 1 ? 'voce' : 'voci'} del Dizionario` : '');
    let corpo = chiamate(i, lettere);
    if (V.f[i] & 2) corpo += '<span class="omesso" title="Il numero è stampato, il testo CEI omette il versetto">(versetto omesso)</span>';
    // the acrostic letters in the margin, beside the line each one opens (Na 1,3: Bet at line 3)
    const lettera = l => `<span class="acr" title="Lettera acrostica ${esc(l)}${l.startsWith('(') ? ', mancante nel testo ebraico' : ''}"><b lang="he">${esc(A.ebr[l.replace(/[()]/g, '')] || '')}</b> ${esc(l)}</span>`;
    const acr = n => (V.ac[i] || []).filter(x => x[1] === n).map(([l]) => lettera(l)).join('');
    if (poesia) corpo = corpo.split('<br>').map((r, n) => `<span class="r">${acr(n + 1)}${r}</span>`).join('');
    else if (V.ac[i]) corpo = V.ac[i].map(([l]) => lettera(l)).join('') + corpo;
    h += `<span class="${cl}" id="v${i}" data-i="${i}" tabindex="0" role="button" aria-label="${esc(aria)}">${segnoMargine(i)}${segnoDiz(i, dv.get(i))}${pg}<span class="vn" aria-hidden="true">${esc(V.l[i])}</span>${corpo}</span>${poesia ? '' : ' '}`;
  }
  chiudi();
  const prec = c > 0 ? [b, c - 1] : b > 0 ? [b - 1, D.libri[b - 1].c.length - 1] : null;
  const succ = c < L.c.length - 1 ? [b, c + 1] : b < D.libri.length - 1 ? [b + 1, 0] : null;
  const capRif = ([bb, cc]) => `#${D.libri[bb].o}.${D.libri[bb].c[cc][0]}`;
  const capNome = ([bb, cc]) => `${D.libri[bb].s} ${D.libri[bb].c[cc][0] === 'Prol' ? 'prol.' : D.libri[bb].c[cc][0]}`;
  const freccia = (x, seg, tit) => x ? `<a href="${capRif(x)}" title="${tit}: ${esc(capNome(x))}" aria-label="${tit}">${seg}</a>` : `<span>${seg}</span>`;
  const titCap = lab === 'Prol' ? 'Prologo' : (L.c.length === 1 ? '' : lab);
  const calo = document.body.classList.contains('calore');
  pagina(`<article class="lettore">
    <div class="testata"><div><div class="sopratitolo"><a href="#${L.o}">${esc(D.vol[L.v][1])}</a></div>
      <h1><a href="#${L.o}">${esc(L.t)}</a><span class="cap">${esc(titCap)}</span></h1></div>
      <div class="sfoglia">${freccia(prec, '‹', 'Capitolo precedente')}<a href="#${L.o}" title="Tutti i capitoli">${L.c.length > 1 ? '⋯' : '≡'}</a>${freccia(succ, '›', 'Capitolo successivo')}</div></div>
    <div class="legenda-calore"><span class="lc-et" id="lc-et">Evidenzia</span><div class="segmenti fonte-calore" role="group" aria-labelledby="lc-et"><button type="button" data-fonte="bj" aria-pressed="${calo && !S.caloreDiz}">Rimandi BJ</button><button type="button" data-fonte="diz" aria-pressed="${calo && !!S.caloreDiz}">Dizionario</button></div>
      <span class="lc-bj">rimandi entranti: <i style="background:color-mix(in srgb,var(--caldo) 7%,transparent)"></i>1–2 <i style="background:color-mix(in srgb,var(--caldo) 20%,transparent)"></i>6–10 <i style="background:color-mix(in srgb,var(--caldo) 38%,transparent)"></i>21+</span>
      <span class="lc-diz" title="citazioni di al più ${STRETTA} versetti">citazioni brevi del Dizionario: <i style="background:color-mix(in srgb,var(--r-diz) 9%,transparent)"></i>1 <i style="background:color-mix(in srgb,var(--r-diz) 22%,transparent)"></i>3–4 <i style="background:color-mix(in srgb,var(--r-diz) 40%,transparent)"></i>10+</span></div>
    <div class="testo" lang="it">${h}</div>
    <div class="fine">${prec ? `<a href="${capRif(prec)}">‹ ${esc(capNome(prec))}</a>` : '<span></span>'}${succ ? `<a href="${capRif(succ)}">${esc(capNome(succ))} ›</a>` : ''}</div>
  </article>`);
  S.capitolo = [b, c, s, e];
  document.title = `${L.s} ${titCap} · ${L.t}`;
  if (S.avviso) { $('#vista .testo').insertAdjacentHTML('beforebegin', `<p class="avviso" role="status">${esc(S.avviso)}</p>`); S.avviso = null; }
}
function selezionaVerso(a, z = a, scorri = false) {
  $$('.v.sel, .v.int').forEach(x => x.classList.remove('sel', 'int'));
  S.sel = a;
  if (a === null) { chiudiPannello(false); return; }
  for (let i = a + 1; i <= z; i++) { const x = $('#v' + i); if (x) x.classList.add('int'); }
  const el = $('#v' + a);
  if (el) el.classList.add('sel');
  mostraPannello(a);
  document.title = `${rif(a, z)} · ${D.libri[S.vb[a]].t}`;
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
  return contestoA(testo, Math.max(0, testo.indexOf(raw)), raw.length, max);
}
function contestoA(testo, k, n, max = 200) {
  // the text around [k, k + n), from a word start, cut at a word, the span marked
  let da = Math.max(0, k - 80);
  if (da > 0) { const sp = testo.indexOf(' ', da); if (sp >= 0 && sp < k) da = sp + 1; }   // from a word start
  let a = Math.min(testo.length, da + max);
  if (a < testo.length) { const sp = testo.lastIndexOf(' ', a); if (sp > k + n) a = sp; }
  return (da > 0 ? '…' : '') + esc(testo.slice(da, k)) + '<mark>' + esc(testo.slice(k, k + n)) + '</mark>' + esc(testo.slice(k + n, a)) + (a < testo.length ? '…' : '');
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
  const DZ = dizDi(i);
  let h = `<div class="pan-testa"><button type="button" class="maniglia" data-maniglia aria-label="Allarga o riduci il pannello"></button><div><h2 class="rif" tabindex="-1">${esc(rif(i))}</h2><div class="libro-tit">${esc(L.t)} · p. ${V.pg[i]}</div></div>
    <div class="azioni"><a class="bottone" href="#grafo/${V.id[i]}" title="Rete dei collegamenti (g)">Grafo</a>
    <button class="bottone" type="button" data-chiudi title="Chiudi (Esc)" aria-label="Chiudi">✕</button></div></div>
    <div class="pan-corpo">
    <div class="citazione">${V.h[i] || '<span class="omesso">(versetto omesso nel testo CEI)</span>'}</div>
    <div class="contatori"><span>${conta(qui.length + altre.length, 'nota', 'note')}</span><span>${conta(nUscita, 'rimando', 'rimandi')} in uscita</span><span>${conta(nEntr, 'rimando entrante', 'rimandi entranti')}</span><span>${conta(E.note.length + E.intro.length, 'citazione', 'citazioni')}</span><span>${conta(DZ.length, 'voce', 'voci')} del Dizionario</span></div>`;

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
      const cr = G.corr.ml[k];
      chips += chip(l[2], esc(rifRuns(l[2])) + (g === 'keynote' ? ' +' : '') + fl + qual + legato + (cr ? ' <small title="letto dal curatore">*</small>' : ''),
        ` title="stampato: ${esc(l[11])}"${nota}${cr ? ` data-corr="${esc(`${l[10] || 'letto dal curatore'} (fonte: ${cr[0]}, riga ${cr[1]})`)}"` : ''}`, '', R.col, g === 'keynote' ? versoChiave(l) : null);
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
  let app = sezioneIndice('note', i) + sezioneIndice('temi', i) + sezioneCronologia(i);
  if (DZ.length && window.innerWidth <= 720) app = app.replace(/<section class="sez ([^"]+)"><h3([^>]*)>([\s\S]*?)<\/h3>([\s\S]*?)<\/section>/g, '<details class="sez $1 chiusa"><summary><h3$2>$3</h3></summary>$4</details>');
  h += '</section>' + sezionePersone(i) + app + sezioneDiz(i, DZ) + '</div>';
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
  // (and data-p, data-t: the front-matter texts and the chronology)
  $$('a.ci', radice).forEach(a => {
    const c = a.dataset.c !== undefined ? D.nc[+a.dataset.c] : null;
    const x = a.dataset.p !== undefined ? A.pc[+a.dataset.p] : a.dataset.t !== undefined ? A.cron.cit[+a.dataset.t] : null;
    const r = c ? c[1] : x ? (a.dataset.p !== undefined ? x[2] : x[1]) : D.ic[+a.dataset.i][2];
    const motivo = c ? c[3] : x ? (a.dataset.p !== undefined ? x[4] : x[3]) : D.ic[+a.dataset.i][4];
    if (!r.length) { a.classList.add('x'); a.title = motivo || 'riferimento non risolto'; a.removeAttribute('href'); return; }
    a.href = hashVerso(r[0]);
    a.dataset.r = runsAttr(r);
    if (motivo) a.title = motivo;
    const cr = c ? G.corr.nc[+a.dataset.c] : a.dataset.i !== undefined ? G.corr.ic[+a.dataset.i] : null;
    if (cr) { a.dataset.corr = `${motivo || 'letto dal curatore'} (fonte: ${cr[0]}, riga ${cr[1]})`; a.classList.add('letto'); }
  });
}

// ---------------------------------------------------------------- preview of a target

let tAnteprima = null, puntatore = 'mouse', bersaglio = null;
function nascondiAnteprima() { clearTimeout(tAnteprima); $('#anteprima').hidden = true; bersaglio = null; }
function mostraAnteprima(el, tocco) {
  const box = $('#anteprima');
  if (el.dataset.x !== undefined) {
    // an unresolved citation of the dictionary: why it has no target
    box.innerHTML = `<div class="ap-rif">${esc(el.textContent)}</div><p class="ap-x">Riferimento non risolto: ${esc(el.dataset.x)}.</p>`;
    return posaAnteprima(el, box);
  }
  const r = el.dataset.r.split(',').map(x => x.split('-').map(Number));
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
  if (el.dataset.corr) h += `<p class="ap-corr">Lettura del curatore: ${esc(el.dataset.corr)}</p>`;
  if (tocco) h += `<div class="ap-vai"><a class="bottone primario" href="${esc(el.getAttribute('href'))}">Vai a ${esc(rif(r[0][0]))} ›</a></div>`;
  box.innerHTML = h;
  posaAnteprima(el, box);
}
function posaAnteprima(el, box) {
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
  pagina(`<div class="pagina ricerca"><h1>Cerca nel testo, nelle note e nel Dizionario</h1>
    <p class="sotto">Parole intere, senza distinguere accenti e maiuscole: <a href="#cerca?q=melchisedek">melchisedek</a> trova «Melchìsedek». Più parole devono comparire tutte; tra virgolette una frase esatta; un asterisco cerca l’inizio di parola (<a href="#cerca?q=ira*">ira*</a> trova anche «irato»).</p>
    <div class="ricerca-campi">
      <input type="search" id="rq" value="${esc(q)}" placeholder="Parola o frase…" aria-label="Testo da cercare" spellcheck="false">
      <div class="segmenti" role="group" aria-label="Dove cercare">
        ${[['tutto', 'Tutto'], ['versetti', 'Versetti'], ['note', 'Note'], ['dizionario', 'Dizionario'], ['apparati', 'Appendici']].map(([v, t]) => `<button type="button" data-in="${v}" aria-pressed="${v === dove}">${t}</button>`).join('')}
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
  ripristinaScorrimento();
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
    // the other spellings of a name (sinonimi.tsv: David / Davide, Horeb / Oreb; R3 E2)
    const alt = !f && !prefisso && S.sin && S.sin.has(t) ? S.sin.get(t) : [t];
    const corpo = alt.map(x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    const fine = prefisso ? `[${LETTERA}]*` : `(?![${LETTERA}])`;
    out.push({ t, alt, g: new RegExp(`(?<![${LETTERA}])(?:${corpo})${fine}`, 'gu') });
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
  const tutti = s => ts.every(t => t.alt.some(x => s.includes(x)) && (t.g.lastIndex = 0, t.g.test(s)));
  // the dictionary: entry names and paragraphs (the testament and book filters leave it out)
  const dv = [], dpar = [];
  const conDiz = (dove === 'tutto' || dove === 'dizionario') && !T && bfil < 0;
  if (conDiz) {
    indiceDiz(I);
    I.dnomi.forEach((x, k) => { if (tutti(x)) dv.push(k); });
    I.dpn.forEach((x, j) => { if (tutti(x)) dpar.push(j); });
    // the paragraphs of the entries whose name matches first, then by the number of hits (R3 E6)
    const nomi = new Set(dv), colpi = j => ts.reduce((n, t) => (t.g.lastIndex = 0, n + (I.dpn[j].match(t.g) || []).length), 0);
    const w = new Map(dpar.map(j => [j, (nomi.has(I.dk[j][0]) ? 1e6 : 0) + colpi(j)]));
    dpar.sort((a, b) => w.get(b) - w.get(a) || a - b);
  }
  if (dove === 'tutto' || dove === 'versetti') {
    for (let i = 0; i < S.n; i++) {
      if (!ok(S.vb[i]) || !tutti(I.vn[i])) continue;
      if (!per.has(S.vb[i])) per.set(S.vb[i], []);
      per.get(S.vb[i]).push([0, i]);
      nv++;
    }
  }
  if (dove === 'tutto' || dove === 'note') {
    D.note.forEach((x, k) => {
      const b = S.vb[x[0]];
      if (!ok(b) || !tutti(I.nn[k])) return;
      if (!per.has(b)) per.set(b, []);
      per.get(b).push([1, k]);
      nn++;
    });
  }
  // the front matter and the appendices: index entries, chronology, the texts (no testament or book filter)
  const conPar = (dove === 'tutto' || dove === 'apparati') && !T && bfil < 0;
  const [hPar, np] = conPar ? bloccoPar(I, ts, tutti) : ['', 0];
  const ms = performance.now() - t0;
  const nd = dpar.length + dv.length + np;
  const parti = [];
  if (dove !== 'dizionario' && dove !== 'apparati') parti.push(`${conta(nv, 'versetto', 'versetti')} e ${conta(nn, 'nota', 'note')} in ${conta(per.size, 'libro', 'libri')}`);
  if (conDiz) parti.push(`${conta(dv.length, 'voce', 'voci')} e ${conta(dpar.length, 'paragrafo', 'paragrafi')} del Dizionario`);
  if (conPar) parti.push(`<b>${num(np)}</b> nell’Introduzione generale e nelle appendici`);
  const anche = [...new Set(ts.flatMap(t => t.alt.filter(x => x !== t.t)))];
  esito.innerHTML = nv + nn + nd ? `${parti.join('; ')} <small>(${ms.toFixed(0)} ms)</small>${anche.length ? ` <span class="sinonimi">anche: ${anche.map(esc).join(', ')}</span>` : ''}`
    : `Nessun risultato per «${esc(q)}»${!conDiz && dove !== 'versetti' && dove !== 'note' ? ' (i filtri di testamento e libro escludono il Dizionario e le appendici)' : ''}.`;
  const libri = [...per.keys()].sort((a, b) => a - b);
  const riga = ([tipo, k]) => {
    if (tipo === 0) return `<div class="r"><a class="dove" href="${hashVerso(k)}" data-r="${k}-${k}">${esc(rif(k))}</a><div class="frase">${evidenzia(I.vp[k], I.vn[k], ts)}</div></div>`;
    const x = D.note[k];
    return `<div class="r rn"><a class="dove" href="${hashVerso(x[0])}" data-nota="${k}">nota ${esc(x[3] + x[2])}<small>${esc(rif(x[0]))}</small></a><div class="frase">${evidenzia(I.np[k], I.nn[k], ts)}</div></div>`;
  };
  let h = '', righe = 0, hDiz = '';
  const rigaDiz = x => {
    const [k, j] = I.dk[x], p = Z.voci[k][9][j], sz = sezioneDi(k, p[1]);
    return `<div class="r rd"><a class="dove" href="${hashVoce(k, p[0])}">${esc(nomeVoce(k))}<small>${sz ? esc(sz[0]) : 'introd.'}</small></a><div class="frase">${evidenzia(I.dp[x], I.dpn[x], ts)}</div></div>`;
  };
  const PAGINA_DIZ = 50;
  const altriDiz = n => `<button class="altro" type="button" data-diz="1">mostra altri ${num(Math.min(PAGINA_DIZ, dpar.length - n))} paragrafi${dpar.length - n > PAGINA_DIZ ? ` (di ${num(dpar.length - n)})` : ''}</button>`;
  if (dv.length || dpar.length) {
    // the rows shown before leaving the page come back with Back (history state)
    const st = history.state || {};
    const lim = Math.max(dove === 'dizionario' ? 25 : 5, st.q === q && st.in === dove ? st.dizN || 0 : 0);
    const chiuso = dove === 'tutto' && nv + nn > 0;
    const tit = `<h3><span class="seg">◊</span>Dizionario di Teologia Biblica<small>${quanti(dv.length, 'voce', 'voci')} · ${quanti(dpar.length, 'paragrafo', 'paragrafi')}</small></h3>`;
    const chips = dv.length ? `<div class="chips dchips">${dv.map(k => `<a class="chip" href="${hashVoce(k)}" style="--c:var(--r-diz)">${evidenzia(nomeVoce(k), I.dnomi[k], ts)}${rinvio(k) ? ' <small>rinvio</small>' : ''}</a>`).join('')}</div>` : '';
    hDiz = (chiuso ? `<details class="blocco bdiz chiuso"><summary>${tit}${chips}</summary>` : `<section class="blocco bdiz">${tit}${chips}`) +
      dpar.slice(0, lim).map(rigaDiz).join('') + (dpar.length > lim ? altriDiz(lim) : '') + (chiuso ? '</details>' : '</section>');
  }
  const chiudiPar = dove === 'tutto' && nv + nn > 0 && hPar;
  const hP = chiudiPar ? hPar.replace(/^<section class="blocco bpar">(<h3>[\s\S]*?<\/h3>(?:<div class="chips pchips">[\s\S]*?<\/div>)?)/, '<details class="blocco bpar chiuso"><summary>$1</summary>').replace(/<\/section>$/, '</details>') : hPar;
  if (dove !== 'tutto' || !(nv + nn)) h += hDiz + hP;
  else h += `<div class="altri-gruppi">${hDiz}${hP}</div>`;
  for (const b of libri) {
    const xs = per.get(b);
    xs.sort((x, y) => (x[0] ? D.note[x[1]][0] : x[1]) - (y[0] ? D.note[y[1]][0] : y[1]) || x[0] - y[0]);
    const nvb = xs.filter(x => !x[0]).length;
    const lim = righe > 600 ? 3 : 25;
    h += `<section class="blocco"><h3><a href="#${D.libri[b].o}">${esc(D.libri[b].t)}</a><small>${quanti(nvb, 'versetto', 'versetti')} · ${quanti(xs.length - nvb, 'nota', 'note')}</small></h3>${xs.slice(0, lim).map(riga).join('')}`;
    if (xs.length > lim) h += `<button class="altro" type="button" data-libro="${b}">mostra altri ${xs.length - lim}</button>`;
    h += '</section>';
    righe += Math.min(lim, xs.length);
  }
  box.innerHTML = h;
  box.onclick = e => {
    const dz = e.target.closest('[data-diz]');
    if (dz) {
      const n = dz.parentNode.querySelectorAll('.r').length, m = Math.min(dpar.length, n + PAGINA_DIZ);
      dz.insertAdjacentHTML('beforebegin', dpar.slice(n, m).map(rigaDiz).join('') + (m < dpar.length ? altriDiz(m) : ''));
      dz.remove();
      history.replaceState({ ...(history.state || {}), q, in: dove, dizN: m }, '', location.href);
      return;
    }
    const btn = e.target.closest('[data-libro]');
    if (!btn) return;
    const xs = per.get(+btn.dataset.libro);
    btn.insertAdjacentHTML('beforebegin', xs.slice(btn.parentNode.querySelectorAll('.r').length).map(riga).join(''));
    btn.remove();
  };
}

// ---------------------------------------------------------------- the front matter and the appendices
// D.par (esploratore.py, paratesto()): the edition and the texts before the Old Testament, the
// canon lists, the abbreviations and codices, the woodcuts, the two indices of the appendices,
// the chronological table and the dynasties.

let A;
const INDICI = {
  note: { via: 'indice-note', breve: 'Indice delle note', nome: 'Indice alfabetico delle note più importanti', seg: '¤' },
  temi: { via: 'temi', breve: 'Temi pastorali', nome: 'Indice dei temi biblici d’interesse pastorale', seg: '✦' },
};
const CORRISP = ['nota', 'copre', 'capitolo', 'rimandi', 'nessuna'];
const TIPI_ABBR = [['libro', 'Abbreviazioni bibliche'], ['libro-forma-antica', 'Forme antiche'],
  ['abbreviazione', 'Altre abbreviazioni'], ['segno', 'Segni delle referenze marginali'],
  ['codice-maiuscolo', 'Codici maiuscoli'], ['codice-minuscolo', 'Codici minuscoli'], ['papiro', 'Papiri'],
  ['codice-vetus-latina', 'Codici della vetus latina']];

function indiciParatesto() {
  A = D.par;
  // every printed reference of the two indices with the runs it names for the verse panel (the
  // corrected passage for a misprint the checklist corrects; nothing for an unresolved one)
  S.ixRefs = [];
  S.ixN = {};
  for (const id of Object.keys(INDICI)) {
    S.ixN[id] = new Map(A.indici[id].map((v, k) => [v[0], k]));
    A.indici[id].forEach((v, k) => v[6].forEach((it, j) => {
      const r = it[11] ? it[11][1] : it[7] <= 1 ? it[6] : [];
      if (r.length) S.ixRefs.push([id, k, j, r]);
    }));
  }
  S.cronDi = A.cron.voci.map(() => []);
  A.cron.cit.forEach((c, k) => S.cronDi[c[0]].push(k));
}
const hashIndice = (id, n, sv = 0) => `#${INDICI[id].via}/${n}${sv ? '.' + sv : ''}`;
const hashCron = n => `#cronologia/${A.cron.voci[n - 1][0]}?v=${n}`;
const romanoInt = s => { let n = 0, p = 0; for (const ch of s.toLowerCase().split('').reverse()) { const v = { i: 1, v: 5, x: 10, l: 50 }[ch]; n += v < p ? -v : v; p = Math.max(p, v); } return n; };

// the entries of an index naming verse i: [[entry, [[sub, item], ...]], ...], the most specific first
function indiceDi(id, i) {
  const per = new Map();
  for (const [x, k, j, r] of S.ixRefs) {
    if (x !== id || !contiene(r, i)) continue;
    if (!per.has(k)) per.set(k, { js: [], w: Infinity });
    const e = per.get(k);
    e.js.push(j);
    e.w = Math.min(e.w, ampiezza(r));
  }
  return [...per.entries()].sort((a, b) => a[1].w - b[1].w || a[0] - b[0]).map(([k, e]) => [k, e.js]);
}
function nomeSotto(id, k, sv) {
  const v = A.indici[id][k];
  return sv ? v[5][sv - 1][2] : v[2];
}
function chipIndice(it, conNote) {
  // one printed reference of an index: the passage, what follows it, the BJ note it points to
  const [, , raw, , cf, seg, r, st, mot, note, corr, fix, extra] = it;
  const pre = cf ? '<small>cf.</small> ' : '';
  const dopo = seg ? ` <small>${esc(seg)}</small>` : '';
  if (it[0] === 1) return `<a class="chip" href="#${D.libri[extra[0]].o}" title="tutto il libro">${pre}${esc(raw)}${dopo}</a>`;
  let h = '';
  if (fix) {
    h += `<span class="chip x refuso" title="refuso: ${esc(fix[3])}">${pre}${esc(raw)}</span>` +
      chip(fix[1], '→ ' + esc(fix[0]) + dopo, ` title="${esc('corretto: ' + fix[3])}" data-corr="${esc(fix[3] + ' (fonte: paratesto.CORREZIONI_INDICI, registro dei dubbi del volume)')}"`, 'corretto');
  } else if (!r.length || st === 2) {
    return `<span class="chip x" title="${esc(mot || 'riferimento non risolto')}">${pre}${esc(raw)}</span>`;
  } else h += chip(r, pre + esc(raw) + dopo, st === 1 ? ` title="${esc('in parte: ' + mot)}"` : '');
  if (!conNote) return h;
  const ns = fix ? fix[2] : note;
  const tipo = fix ? 0 : corr;
  if (ns.length) {
    h += ns.map(k => `<a class="nota-ix${tipo === 1 ? ' copre' : ''}" href="${hashVerso(D.note[k][0])}" data-nota="${k}" title="${tipo === 1 ? 'la nota comprende questo versetto' : 'la nota della BJ a cui l’indice manda'}">nota ${esc(D.note[k][3] + (D.note[k][2] || ''))}</a>`).join('');
  } else if (tipo >= 3) h += `<small class="senza-nota">${tipo === 3 ? 'nessuna nota qui, solo rimandi' : 'nessuna nota qui'}</small>`;
  return h;
}
function etichettaNota(x) {
  // «Gs 14,6» when the note's label is its verse, «Gs 14,6 · nota 14,6–15» otherwise (R3 E15)
  const r = rif(x[0]), l = (x[3] || '') + (x[2] || '');
  return !l || r.endsWith(' ' + l) ? r : `${r} · nota ${l}`;
}
function elencoBreve(righe, primi) {
  const resto = righe.length - primi;
  return `<ul class="elenco">${righe.slice(0, primi).join('')}</ul>${resto > 0
    ? `<details class="altri"><summary class="altro">mostra altre ${resto}</summary><ul class="elenco">${righe.slice(primi).join('')}</ul></details>` : ''}`;
}
function sezioneIndice(id, i) {
  const E = indiceDi(id, i);
  if (!E.length) return '';
  const I = INDICI[id];
  const righe = E.map(([k, js]) => {
    const v = A.indici[id][k];
    const sotto = [...new Set(js.map(j => v[6][j][1]))].filter(s => s).map(s => esc(v[5][s - 1][2]));
    const refs = js.map(j => chipIndice(v[6][j], id === 'note')).join(' ');
    return `<li><a href="${hashIndice(id, v[0], js.length === 1 ? v[6][js[0]][1] : 0)}">${v[1]}</a>${sotto.length ? ` <small>› ${sotto.join(' · ')}</small>` : ''}<span class="frase chips">${refs}</span></li>`;
  });
  return `<section class="sez ix"><h3 title="${esc(I.nome)}">${id === 'note' ? 'Nell’indice delle note' : 'Temi pastorali'} <span class="n">${E.length}</span></h3>${elencoBreve(righe, 5)}</section>`;
}
function sezioneCronologia(i) {
  const ks = [];
  A.cron.cit.forEach((c, k) => { if (c[2] <= 1 && contiene(c[1], i)) ks.push(k); });
  const xilo = A.xilo.find(x => contiene(x[3], i));
  if (!ks.length && !xilo) return '';
  let h = '<section class="sez cron">';
  if (ks.length) {
    ks.sort((x, y) => ampiezza(A.cron.cit[x][1]) - ampiezza(A.cron.cit[y][1]) || A.cron.cit[x][0] - A.cron.cit[y][0]);
    const righe = [...new Set(ks.map(k => A.cron.cit[k][0]))].map(n => {
      const v = A.cron.voci[n], c = ks.find(k => A.cron.cit[k][0] === n);
      return `<li><a href="${hashCron(n + 1)}">${v[7] ? esc(v[7]) : 'senza data'}</a> <small>${esc(A.cron.col[v[4]][1])} · ${esc(A.cron.sez[v[0] - 1][1].split(' ')[0])}</small><span class="frase">${contesto(v[11], A.cron.cit[c][4])}</span></li>`;
    });
    h += `<h3>Nella tavola cronologica <span class="n">${righe.length}</span></h3>${elencoBreve(righe, 4)}`;
  }
  if (xilo) h += `<p class="xilo-nota"><span class="seg">▣</span>Illustrato dalla xilografia che apre ${esc(D.libri[xilo[0]].t)} (${esc(xilo[1])} ${esc(xilo[2])}; <a href="#introduzione-generale/avvertenze">Avvertenze</a>).</p>`;
  return h + '</section>';
}

// ---------------------------------------------------------------- the links between the parts (D.int, session F2)
// D.int (esploratore.py, integrazione()): concept alignments of the indices and the dictionary, the
// persons of the dynasties where the volume names them, the chronology entries dating a book, the
// versions and codices the notes name, the calendar, the measures and coins, the maps, the
// interventions of the editor on the links, the synonyms of the search.

let G;
const SKOS = [['≈', 'quasi lo stesso concetto (skos:closeMatch)'], ['⊂', 'più ampio (skos:broadMatch)'],
  ['⊃', 'più specifico (skos:narrowMatch)'], ['~', 'concetto affine (skos:relatedMatch)'], ['=', 'lo stesso concetto (skos:exactMatch)']];
const INVERSA = [0, 2, 1, 3, 4];
const DATAZIONE = ['composizione', 'ministero', 'evento narrato', 'citato'];
function indiciIntegrazione() {
  G = D.int;
  S.al = new Map();                    // key -> [[other key, relation from key, method, shared]]
  for (const [a, b, r, m, n] of G.al) {
    if (!S.al.has(a)) S.al.set(a, []);
    if (!S.al.has(b)) S.al.set(b, []);
    S.al.get(a).push([b, r, m, n]);
    S.al.get(b).push([a, INVERSA[r], m, n]);
  }
  S.pers = new Map(G.pers.map(x => [x[0], x]));
  S.persCron = new Map();
  S.persIx = new Map();
  for (const [id, , cr, ix] of G.pers) {
    for (const n of cr) { if (!S.persCron.has(n)) S.persCron.set(n, []); S.persCron.get(n).push(id); }
    for (const [k] of ix) { const kk = k.split('.').slice(0, 2).join('.'); if (!S.persIx.has(kk)) S.persIx.set(kk, []); if (!S.persIx.get(kk).includes(id)) S.persIx.get(kk).push(id); }
  }
  S.datDi = new Map();                 // chronology entry (from 1) -> [[books, kind]]
  S.libroDat = new Map();              // book -> [[entry, kind]]
  for (const [n, bs, t] of G.dat) {
    if (!S.datDi.has(n)) S.datDi.set(n, []);
    S.datDi.get(n).push([bs, t]);
    for (const b of bs) { if (!S.libroDat.has(b)) S.libroDat.set(b, []); S.libroDat.get(b).push([n, t]); }
  }
  S.festaAnche = new Map();
  for (const f of G.feste) for (const a of f[7]) { if (!S.festaAnche.has(a)) S.festaAnche.set(a, []); S.festaAnche.get(a).push(f); }
  S.sin = new Map();
  for (const g of G.sin) for (const w of g) S.sin.set(w, g);
}
const nomePersona = x => A.din.find(y => y[0] === x)?.[2] || x;
const hashPersona = id => `#persona/${id}`;
function concetto(key) {
  // [href, name, sign, colour] of an index entry ('note.7'), a theme ('temi.4') or a dictionary entry ('v12')
  if (key[0] === 'v') { const k = +key.slice(1); return [hashVoce(k), nomeVoce(k), '◊', '--r-diz', 'Dizionario']; }
  const [id, n] = key.split('.'), v = A.indici[id][S.ixN[id].get(+n)];
  return [hashIndice(id, +n), v[2], INDICI[id].seg, id === 'note' ? '--r-keynote' : '--r-quoted', INDICI[id].breve];
}
// «Anche in»: one strip of typed chips under the h1 of an entity page (R3 E19), most shared verses first
function ancheIn(key, persone = [], feste = []) {
  const xs = (S.al.get(key) || []).slice().sort((x, y) => y[3] - x[3]);
  const chips = xs.map(([b, r, m, n]) => {
    const [h, nome, seg, col, dove] = concetto(b);
    return `<a class="chip anche-chip" href="${h}" style="--c:var(${col})" title="${esc(`${dove}: ${SKOS[r][1]}; ${n ? quanti(n, 'versetto', 'versetti') + ' in comune' : 'nessun versetto in comune'} (metodo: ${m})`)}"><span class="seg">${seg}</span>${esc(nome)} <small>${SKOS[r][0]}${n ? ' ' + num(n) : ''}</small></a>`;
  });
  for (const p of persone) chips.push(`<a class="chip anche-chip" href="${hashPersona(p)}" style="--c:var(--r-parallel)" title="persona delle dinastie"><span class="seg">◆</span>${esc(nomePersona(p))}</a>`);
  for (const f of feste) chips.push(`<a class="chip anche-chip" href="#calendario?f=${f[0]}" style="--c:var(--r-doublet)" title="festa del calendario"><span class="seg">☾</span>${esc(f[1])}</a>`);
  if (!chips.length) return '';
  const MAX = 6, resto = chips.length - MAX;
  return `<div class="anche-in"><span class="anche-et">Anche in</span><span class="chips">${chips.slice(0, MAX).join('')}${resto > 0
    ? `<details class="anche-altri"><summary>+${resto}</summary><span class="chips">${chips.slice(MAX).join('')}</span></details>` : ''}</span></div>`;
}
function chipsVersetti(runs) {
  // the verses of a person or a measure, one chip per book with the verses in its title
  const per = new Map();
  for (let j = 0; j < runs.length; j += 2) for (let i = runs[j]; i <= runs[j + 1]; i++) {
    const b = S.vb[i];
    if (!per.has(b)) per.set(b, []);
    per.get(b).push(i);
  }
  return [...per.entries()].map(([b, is]) => `<div class="pers-libro"><b>${esc(D.libri[b].t)}</b> <span class="chips">${is.map(i => chip([i, i], esc(rif(i, i, false)))).join('')}</span></div>`).join('');
}
function mostraPersona(id) {
  const x = A.din.find(y => y[0] === id);
  if (!x) return nonTrovato('persona/' + id, [`«${esc(id)}» non è una persona della tavola delle dinastie.`, '<a href="#cronologia/dinastie">Le dinastie</a>']);
  const P = S.pers.get(id) || [id, [], [], []];
  const per = y => y ? `<a href="${hashPersona(y)}">${esc(nomePersona(y))}</a>` : '';
  const figli = A.din.filter(y => y[5] === id || y[6] === id).map(y => per(y[0]));
  const famiglia = [['padre', per(x[5])], ['madre', per(x[6])], [pl(x[7].length, 'coniuge', 'coniugi'), x[7].map(per).join(', ')],
    [pl(figli.length, 'figlio', 'figli'), figli.join(', ')]].filter(r => r[1]);
  const nv = ampiezza(P[1]);
  const cron = P[2].map(n => { const v = A.cron.voci[n - 1]; return `<li><a href="${hashCron(n)}">${v[7] ? esc(v[7]) : 'senza data'}</a> <small>${esc(A.cron.col[v[4]][1])}</small><span class="frase">${esc(v[11].length > 160 ? v[11].slice(0, 159) + '…' : v[11])}</span></li>`; });
  const ix = P[3].map(([k, raw]) => { const [i, n, sv] = k.split('.'); const v = A.indici[i][S.ixN[i].get(+n)]; return `<li><a href="${hashIndice(i, +n, sv ? +sv : 0)}">${v[1]}${sv ? ' › ' + esc(v[5][sv - 1][2]) : ''}</a>${raw ? ` <small>il riferimento ${esc(raw)}</small>` : ''}</li>`; });
  pagina(`<div class="pagina persona"><div class="sopratitolo"><a href="#cronologia/dinastie">Dinastie Asmonea e Erodiana</a> · appendici, p. 24</div>
    <h1>${x[1] ? `<span class="num">${esc(x[1])}.</span> ` : ''}${esc(x[2])}</h1>
    <p class="sotto">${x[4] ? esc(x[4]) + ' · ' : ''}${quanti(nv, 'versetto lo nomina', 'versetti lo nominano')} · ${quanti(P[2].length, 'voce', 'voci')} della tavola cronologica${x[8] ? ' · ' + esc(x[8]) : ''}</p>
    ${famiglia.length ? `<dl class="famiglia">${famiglia.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join('')}</dl>` : ''}
    ${nv ? `<div class="h2">Nei versetti <span class="n">${num(nv)}</span></div>${chipsVersetti(P[1])}` : ''}
    ${cron.length ? `<div class="h2">Nella tavola cronologica <span class="n">${cron.length}</span></div><ul class="elenco">${cron.join('')}</ul>` : ''}
    ${ix.length ? `<div class="h2">Nell’indice delle note</div><ul class="elenco">${ix.join('')}</ul>` : ''}
    <p class="nota-fonte">Dalla tabella rivista <code>tools/ontologia/persone.tsv</code>: i versetti per capitolo e nome, con le eccezioni (precisione prima della completezza).</p></div>`);
  document.title = `${x[2]} · Dinastie`;
}
function rigaRif(rs) {
  return rs.map(([raw, r, corr]) => r.length ? chip(r, esc(raw) + (corr ? ` <small>→ ${esc(corr)}</small>` : ''), corr ? ` title="${esc('refuso della stampa, letto ' + corr + ' (paratesto.CORREZIONI_PROSA)')}"` : '') : `<span class="chip x">${esc(raw)}</span>`).join('');
}
function mostraCalendario(par = {}) {
  const sel = par.f || '';
  const mesi = G.mesi.map(m => `<tr id="mese-${esc(m[0])}"><td class="ab-f">${esc(m[0])}</td><td><b>${esc(m[1])}</b>${m[2].length ? ` <small>= ${m[2].map(esc).join(', ')}</small>` : ''}</td><td>${esc(m[3])}</td><td>${esc(m[4])}</td><td class="chips">${rigaRif(m[6])}${m[7].length ? ` <small title="versetti che nominano il mese">nominato in ${quanti(ampiezza(m[7]), 'versetto', 'versetti')}</small>` : ''}</td></tr>`).join('');
  const feste = G.feste.map(f => {
    const anche = f[7].map(k => { const [h, nome, seg, col] = concetto(k); return `<a class="chip anche-chip" href="${h}" style="--c:var(${col})"><span class="seg">${seg}</span>${esc(nome)}</a>`; }).join('');
    const mese = G.mesi.find(m => m[0] === f[3]);
    return `<div class="festa${f[0] === sel ? ' sel' : ''}" id="festa-${esc(f[0])}"><h3><em>${esc(f[1])}</em> <small>${f[4] ? esc(f[4]) + ' ' : ''}${mese ? 'di ' + esc(mese[1]) : ''}</small></h3>${f[2].length ? `<p class="sotto">anche: ${f[2].map(esc).join(', ')}</p>` : ''}<div class="chips">${rigaRif(f[6])}</div>${anche ? `<div class="anche-in"><span class="anche-et">Anche in</span><span class="chips">${anche}</span></div>` : ''}</div>`;
  }).join('');
  pagina(`<div class="pagina calendario"><div class="sopratitolo"><a href="#appendici">Appendici</a> · pp. 25–26</div>
    <h1>Calendario e feste annuali</h1><p class="sotto">I mesi del calendario lunisolare con i nomi antichi e macedoni, e le feste annuali menzionate nella Bibbia, con i riferimenti stampati.</p>
    <div class="h2">I mesi</div><table class="abbr calendario-mesi"><thead><tr><th>AT</th><th>nome babilonese</th><th>mesi solari</th><th>nome macedone</th><th>riferimenti</th></tr></thead><tbody>${mesi}</tbody></table>
    <div class="h2">Feste annuali</div>${feste}</div>`);
  document.title = 'Calendario · Appendici';
  if (sel) { const x = $('#festa-' + sel); if (x) window.scrollTo(0, x.getBoundingClientRect().top + window.scrollY - 110); }
}
function mostraMisure(par = {}) {
  const TIPI = [['lunghezza', 'Misure di lunghezza'], ['capacita', 'Misure di capacità o volume'], ['peso', 'Misure di peso'], ['moneta', 'Monete']];
  const UNITA = { 'unit:CentiM': 'cm', 'unit:M': 'm', 'unit:KiloM': 'km', 'unit:L': 'litri', 'unit:GM': 'g', 'unit:KiloGM': 'kg' };
  const nome = id => G.mis.find(x => x[0] === id)?.[2] || id;
  const riga = x => `<tr id="mis-${esc(x[0])}"${x[0] === par.u ? ' class="sel"' : ''}><td><b>${esc(x[2])}</b>${x[3] && x[3] !== x[2] ? ` <i lang="${esc(x[4].split('-')[0])}">${esc(x[3])}</i>` : ''}</td><td class="num">${x[5] ? esc(x[5]) + ' ' + esc(UNITA[x[6]] || '') : ''}</td><td>${x[7] ? esc(x[7]) + (x[8] && x[8] !== x[0] ? ` <small>di ${esc(nome(x[8]))}</small>` : '') : ''}${x[9] ? ` <small>≈ ${esc(nome(x[9]))}</small>` : ''}</td><td class="chips">${rigaRif(x[11])}${x[13].length ? `<details class="altri"><summary class="altro">nominata in ${quanti(ampiezza(x[13]), 'versetto', 'versetti')}</summary>${chipsVersetti(x[13])}</details>` : ''}</td><td><small>${esc(x[12])}</small></td></tr>`;
  pagina(`<div class="pagina misure"><div class="sopratitolo"><a href="#appendici">Appendici</a> · pp. 26–28</div>
    <h1>Tavola delle misure e delle monete</h1><p class="sotto">Cifre approssimative, come stampate; il rapporto è quello della tavola (per le monete alla dramma attica o al denaro). Nel grafo ogni valore ha la sua unità QUDT.</p>
    ${TIPI.map(([t, tit]) => `<div class="h2">${tit}</div><table class="abbr misure-t"><tbody>${G.mis.filter(x => x[1] === t).map(riga).join('')}</tbody></table>`).join('')}</div>`);
  document.title = 'Misure e monete · Appendici';
  if (par.u) { const x = $('#mis-' + par.u); if (x) window.scrollTo(0, x.getBoundingClientRect().top + window.scrollY - 110); }
}
function mostraCarte() {
  const carta = c => `<div class="carta-voce"><h3>${esc(c[1])}${c[2] ? ` <small>${esc(c[2])}</small>` : ''}</h3><p class="sotto">${c[3] === 'appendici' ? `appendici, PDF p. ${c[4]}` : `risguardo, PDF p. ${c[4]}`}${c[6] ? ' · ' + esc(c[6]) : ''} · <a href="../${esc(c[5])}" target="_blank" rel="noopener">immagine</a></p><div class="chips">${c[7].map(b => `<a class="chip" href="#${D.libri[b].o}">${esc(D.libri[b].s)}</a>`).join('')}${rigaRif(c[8])}</div></div>`;
  pagina(`<div class="pagina carte"><div class="sopratitolo"><a href="#appendici">Appendici</a> · pp. 59–67 e risguardi</div>
    <h1>Carte</h1><p class="sotto">Le dieci carte del volume, con i libri di cui mostrano la storia e i passi che disegnano (le immagini sono nel progetto, accanto a questa pagina).</p>${G.carte.map(carta).join('')}</div>`);
  document.title = 'Carte · Appendici';
}
function mostraAppendici() {
  // the hub of the front matter and the appendices (R3 E5)
  const t = (h, b, sp) => `<a class="apparato" href="${h}"><b>${b}</b><span>${sp}</span></a>`;
  pagina(`<div class="pagina"><div class="sopratitolo">Introduzione generale e appendici</div><h1>Appendici</h1>
    <p class="sotto">Quello che il volume stampa prima dell’Antico Testamento e dopo l’Apocalisse, collegato ai versetti; ${quanti(G.nint, 'intervento', 'interventi')} del curatore (refusi, letture, rimandi) sono nel grafo con la loro fonte.</p>
    <div class="h2">Introduzione generale</div><div class="apparati">
      ${t('#introduzione-generale', 'Introduzione generale', 'presentazione, prefazioni, canone, avvertenze')}
      ${t('#introduzione-generale/abbreviazioni', 'Abbreviazioni e codici', `${num(A.abbr.length)} sigle · versioni e codici citati nelle note`)}</div>
    <div class="h2">Appendici</div><div class="apparati">
      ${t('#indice-note', 'Indice delle note', `${num(A.meta.note.entries)} voci · ${num(A.meta.note.references)} riferimenti`)}
      ${t('#temi', 'Temi pastorali', `${num(A.meta.temi.entries)} temi · ${num(A.meta.temi.references)} riferimenti`)}
      ${t('#cronologia', 'Tavola cronologica', `${num(A.meta.cron)} voci · ${num(G.dat.filter(x => x[2] < 3).length)} datano un libro`)}
      ${t('#cronologia/dinastie', 'Dinastie', `${num(A.din.length)} persone · ${num(G.pers.length)} nominate nel volume`)}
      ${t('#calendario', 'Calendario', `${G.mesi.length} mesi · ${G.feste.length} feste`)}
      ${t('#misure', 'Misure e monete', `${G.mis.length} unità con il loro valore`)}
      ${t('#carte', 'Carte', `${G.carte.length} carte`)}
      ${t('#panoramica', 'Panoramica', 'i numeri dei collegamenti')}</div></div>`);
  document.title = 'Appendici · Esploratore dei versetti';
}
function sezionePersone(i) {
  // the persons of the dynasties the verse names (persone.tsv)
  const ps = G.pers.filter(p => contiene(p[1], i));
  if (!ps.length) return '';
  return `<section class="sez pers"><h3>Persone delle dinastie <span class="n">${ps.length}</span></h3><div class="chips">${ps.map(p => `<a class="chip" href="${hashPersona(p[0])}" style="--c:var(--r-parallel)"><span class="seg">◆</span>${esc(nomePersona(p[0]))}</a>`).join('')}</div></section>`;
}
function chipsCronologia(n) {
  // the books an entry dates and the persons it names (R3 E19), at the end of the entry
  const ds = (S.datDi.get(n) || []).filter(([, t]) => t < 3), ps = S.persCron.get(n) || [];
  if (!ds.length && !ps.length) return '';
  return ` <span class="cron-chips">${ds.flatMap(([bs, t]) => bs.map(b => `<a class="chip mini" href="#${D.libri[b].o}" title="${esc(D.libri[b].t)}: ${DATAZIONE[t]}">${esc(D.libri[b].s)}</a>`)).join('')}${ps.map(p => `<a class="chip mini" href="${hashPersona(p)}" title="persona delle dinastie" style="--c:var(--r-parallel)">◆ ${esc(nomePersona(p))}</a>`).join('')}</span>`;
}

// ---------------------------------------------------------------- views: the two indices

function inizialeIndice(v) { return normalizza(v[2].replace(/^[«(‘’'"\s]+/, '')).charAt(0).toUpperCase(); }
function mostraIndiceAnalitico(id, arg, par = {}) {
  const I = INDICI[id], voci = A.indici[id], m = A.meta[id];
  if (arg) return mostraVoceIndice(id, arg);
  const lettere = [...new Set(voci.map(inizialeIndice))];
  const nref = v => v[6].filter(it => it[0] <= 1).length;
  const vedi = v => v[6].filter(it => it[0] === 2).flatMap(it => it[12]).map(t => A.indici[id][S.ixN[id].get(t)]?.[2]).filter(Boolean);
  const quanto = v => nref(v) ? num(nref(v)) : vedi(v).length ? 'v.' : v[6].some(it => it[0] === 3) ? 'pp.' : '–';
  const titolo = v => nref(v) ? quanti(nref(v), 'riferimento', 'riferimenti') + (v[5].length ? ', ' + quanti(v[5].length, 'sottovoce', 'sottovoci') : '')
    : vedi(v).length ? 'v. ' + vedi(v).join(', ') : 'rinvio alle pagine di un’introduzione';
  const card = (v, k) => `<a class="dvl ixl" href="${hashIndice(id, v[0])}" data-nome="${esc(normalizza(v[2] + ' ' + v[5].map(s => s[2]).join(' ')))}" title="${esc(titolo(v))}"><b>${v[1]}</b><span>${quanto(v)}</span></a>`;
  const sotto = id === 'note'
    ? `${num(m.entries)} voci e ${num(m.subentries)} sottovoci; ${num(m.references)} riferimenti, ${num(m.nota.nota || 0)} alla prima riga di una nota della BJ, ${num(m.nota.copre || 0)} dentro una nota che li comprende. L’indice esiste per portare alle note: ogni riferimento apre il versetto con la sua nota. ${num(m.see)} rimandi «v.».`
    : `${num(m.entries)} temi e ${num(m.subentries)} sottotemi (di G. Barbaglio), ${num(m.references)} riferimenti biblici, ${num(m.books)} a libri interi.`;
  pagina(`<div class="pagina dizionario indice-an"><div class="sopratitolo">Appendici · pp. ${id === 'note' ? '29–39' : '40–58'}</div>
    <h1>${esc(I.nome)}</h1><p class="sotto">${sotto}</p>
    <div class="diz-campi"><input type="search" id="dq" value="${esc(par.q || '')}" placeholder="Filtra le voci…" aria-label="Filtra le voci" spellcheck="false">
    <nav class="lettere" aria-label="Lettere">${lettere.map(l => `<button type="button" data-l="${esc(l)}">${esc(l)}</button>`).join('')}</nav></div>
    ${lettere.map(l => `<section class="lettera" id="lett-${esc(l)}"><h2>${esc(l)}</h2><div class="dvoci">${voci.map((v, k) => [v, k]).filter(([v]) => inizialeIndice(v) === l).map(([v, k]) => card(v, k)).join('')}</div></section>`).join('')}
    <p class="vuoto" id="dnessuna" hidden>Nessuna voce corrisponde.</p></div>`);
  document.title = `${I.breve} · Esploratore dei versetti`;
  $('.lettere').addEventListener('click', e => {
    const b = e.target.closest('[data-l]');
    if (!b) return;
    const alto = $('.barra').getBoundingClientRect().bottom;
    window.scrollTo(0, $('#lett-' + b.dataset.l).getBoundingClientRect().top + window.scrollY - alto - 8);
  });
  const filtra = () => {
    const testo = $('#dq').value.trim(), q = normalizza(testo);
    let tot = 0;
    $$('.lettera').forEach(sez => {
      let n = 0;
      $$('.dvl', sez).forEach(a => { const ok = !q || a.dataset.nome.includes(q); a.hidden = !ok; n += ok; });
      sez.hidden = !n;
      $(`.lettere [data-l="${sez.id.slice(5)}"]`).disabled = !n;
      tot += n;
    });
    $('#dnessuna').hidden = tot > 0;
    return testo;
  };
  $('#dq').addEventListener('input', () => {
    const testo = filtra();
    history.replaceState(history.state, '', `#${I.via}` + (testo ? '?q=' + encodeURIComponent(testo) : ''));
  });
  if (par.q) filtra();
  ripristinaScorrimento();
}
function mostraVoceIndice(id, arg) {
  const I = INDICI[id];
  const [n0, sv0] = arg.split('.');
  const k = S.ixN[id].get(+n0);
  if (k === undefined) {
    pagina(`<div class="pagina"><h1>Voce non trovata</h1><p class="sotto">«${esc(arg)}» non è una voce dell’${esc(I.nome.charAt(0).toLowerCase() + I.nome.slice(1))}.</p><p><a href="#${I.via}">Tutte le voci</a></p></div>`);
    document.title = 'Voce non trovata · ' + I.breve;
    return;
  }
  const v = A.indici[id][k], [n, html, , stile, pag, subs, items] = v;
  const gruppi = [[0, null], ...subs.map(s => [s[0], s])];
  let h = '';
  for (const [sv, s] of gruppi) {
    const its = items.filter(it => it[1] === sv);
    if (!its.length && sv) continue;
    let riga = its.map(it => {
      if (it[0] === 2) return it[12].map(t => { const kk = S.ixN[id].get(t); return `<a class="vedi" href="${hashIndice(id, t)}">v. ${A.indici[id][kk][1]}</a>`; }).join(' ') || `<span class="vedi x" title="nessuna voce con questo lemma">v. ${esc(it[2])}</span>`;
      if (it[0] === 3) return it[12].map(j => `<a class="vedi" href="#intro/${esc(D.intro[j][0])}" title="${esc(D.intro[j][1])}">p. ${esc(it[2])}</a>`).join(' ') || `<span class="vedi">p. ${esc(it[2])}</span>`;
      return chipIndice(it, id === 'note');
    }).join(' ');
    if (!riga) continue;
    // the index exists to point to the notes: each one is here, closed, to be read in place
    const note = id === 'note' ? [...new Set(its.flatMap(it => (it[11] ? it[11][2] : it[9])))] : [];
    const schede = note.map(nk => {
      const x = D.note[nk], piano = testoPiano(x[5]);
      return `<details class="nota ix-nota"><summary><span class="etichetta">${esc(etichettaNota(x))}</span><span class="assaggio">${esc(piano.slice(0, 160))}</span></summary><div class="nota-testo">${x[5]}<div class="contatori"><a href="${hashVerso(x[0])}" data-nota="${nk}">apri ${esc(rif(x[0]))} con la nota</a><span>copre <b>${esc(rifRuns(x[6]))}</b></span><span>p. ${x[7]}</span></div></div></details>`;
    }).join('');
    h += `<div class="ix-riga${sv ? ' sv' : ''}" id="sv${sv}">${s ? `<span class="ix-sv">${esc(s[1])}</span>` : ''}<div><span class="chips">${riga}</span>${schede}</div></div>`;
  }
  const nr = items.filter(it => it[0] <= 1).length;
  const vicine = [A.indici[id][k - 1], A.indici[id][k + 1]];
  pagina(`<div class="pagina voce-ix"><div class="sopratitolo"><a href="#${I.via}">${esc(I.nome)}</a> · appendici, p. ${pag}</div>
    <h1 class="st-${esc(stile)}">${html}</h1>${ancheIn(`${id}.${n}`, S.persIx.get(`${id}.${n}`) || [], S.festaAnche.get(`${id}.${n}`) || [])}<p class="sotto">${quanti(nr, 'riferimento', 'riferimenti')}${subs.length ? ' · ' + quanti(subs.length, 'sottovoce', 'sottovoci') : ''}${id === 'note' ? ' · ogni «nota» apre il versetto con la nota della BJ' : ''}</p>
    <div class="ix-corpo">${h}</div>
    <div class="fine">${vicine[0] ? `<a href="${hashIndice(id, vicine[0][0])}">‹ ${vicine[0][1]}</a>` : '<span></span>'}${vicine[1] ? `<a href="${hashIndice(id, vicine[1][0])}">${vicine[1][1]} ›</a>` : ''}</div></div>`);
  collegaCitazioni($('#vista'));
  document.title = `${v[2]} · ${I.breve}`;
  if (sv0) {
    const r = $('#sv' + sv0);
    if (r) { r.classList.add('sel'); const alto = $('.barra').getBoundingClientRect().bottom; window.scrollTo(0, r.getBoundingClientRect().top + window.scrollY - alto - 16); }
  }
}

// ---------------------------------------------------------------- views: the chronological table

function annoTesto(a) { return a < 0 ? `${-a} a.C.` : `${a} d.C.`; }
// «VI. FINE DEL REGNO DI GIUDA (721–587) (2Re 18–25; …)» -> «VI. Fine del regno di Giuda», as the Tufte outline
function titoloPeriodo(t) {
  const m = t.match(/^([IVX]+)\.\s*([^(]*)/);
  if (!m) return t;
  const x = m[2].trim().toLowerCase().replace(/\b(giuda|israele|giosuè|mosè|alessandro|adriano|roma|egitto|persia|babilonia|davide|salomone|abramo|cristo)\b/g, w => w[0].toUpperCase() + w.slice(1));
  return `${m[1]}. ${x.charAt(0).toUpperCase()}${x.slice(1)}`;
}
function mostraCronologia(arg, par = {}) {
  const C = A.cron;
  if (arg === 'dinastie') return mostraDinastie();
  const s = arg ? +arg : 0;
  if (arg && !(s >= 1 && s <= C.sez.length)) return nonTrovato('cronologia/' + arg, [`Periodo «${esc(arg)}» inesistente: la tavola cronologica ne ha ${C.sez.length}.`, '<a href="#cronologia">La tavola cronologica</a>']);
  const span = sz => {
    const vs = C.voci.filter(v => v[0] === sz && v[8] !== null);
    if (!vs.length) return '';
    const lo = Math.min(...vs.map(v => v[8])), hi = Math.max(...vs.map(v => v[9]));
    return `${annoTesto(lo)} – ${annoTesto(hi)}`;
  };
  const nav = `<nav class="cron-nav" aria-label="Sezioni della tavola">${C.sez.map(([n, t]) => `<a href="#cronologia/${n}"${n === s ? ' aria-current="page"' : ''} title="${esc(t)}">${esc(t.split('.')[0])}</a>`).join('')}<a href="#cronologia/dinastie"${arg === 'dinastie' ? ' aria-current="page"' : ''}>Dinastie</a></nav>`;
  if (!s) {
    pagina(`<div class="pagina cronologia"><div class="sopratitolo">Appendici · pp. 3–23</div><h1>Tavola cronologica</h1>
      <p class="sotto">${num(C.voci.length)} voci in ${num(C.sez.length)} periodi e ${num(new Set(C.voci.map(v => v[1])).size)} righe; ${num(A.meta.datate)} con una data leggibile, ${num(C.cit.length)} riferimenti biblici. Le date sono quelle stampate; gli anni a margine sono la scala della stampa.</p>
      ${C.intro.map(p => `<p class="cron-intro">${p}</p>`).join('')}
      ${nav}<div class="cron-sezioni">${C.sez.map(([n, t]) => `<a class="tessera" href="#cronologia/${n}"><b>${esc(t.split('.')[0])}</b><span>${esc(t.slice(t.indexOf('.') + 1).trim())}</span><small>${num(C.voci.filter(v => v[0] === n).length)} voci${span(n) ? ' · ' + span(n) : ''}</small></a>`).join('')}
      <a class="tessera" href="#cronologia/dinastie"><b>Dinastie</b><span>Asmonea e Erodiana</span><small>${num(A.din.length)} persone</small></a></div></div>`);
    collegaCitazioni($('#vista'));
    document.title = 'Tavola cronologica · Esploratore dei versetti';
    return;
  }
  const vs = C.voci.map((v, k) => [v, k]).filter(([v]) => v[0] === s);
  const righe = [...new Set(vs.map(([v]) => v[1]))];
  // the columns in print order: within a row the entries follow the cells from left to right
  const posto = new Map();
  for (const r of righe) {
    const cs = [...new Set(vs.filter(([v]) => v[1] === r).map(([v]) => v[4]))];
    cs.forEach((c, j) => { const x = posto.get(c) || [0, 0]; posto.set(c, cs.length > 1 ? [x[0] + j / (cs.length - 1), x[1] + 1] : x); });
  }
  const media = c => { const x = posto.get(c); return x[1] ? x[0] / x[1] : c / 10; };
  const cols = [...posto.keys()].sort((a, b) => media(a) - media(b) || a - b);
  const sel = par.v ? +par.v - 1 : null;
  let pag = null;
  const corpo = righe.map(r => {
    const qui = vs.filter(([v]) => v[1] === r);
    const anni = qui[0][0][2];
    const pg = qui[0][0][3] !== pag ? `<span class="pg">p. ${qui[0][0][3]}</span>` : '';
    pag = qui[0][0][3];
    return `<div class="cron-riga" style="--n:${cols.length}"><div class="cron-anni">${pg}${anni ? anni.split('; ').map(esc).join('<br>') : ''}</div>${cols.map(c => {
      const cella = qui.filter(([v]) => v[4] === c);
      return `<div class="cron-cella" data-col="${esc(C.col[c][1])}">${cella.map(([v, k]) => `<p id="cv${k + 1}" class="${k === sel ? 'sel' : ''}"${v[7] ? ` title="${esc(v[7])}${v[8] !== null ? ` · ${annoTesto(v[8])}${v[9] !== v[8] ? ' – ' + annoTesto(v[9]) : ''}${v[10] ? ' circa' : ''}` : ''}"` : ''}>${v[6]}${chipsCronologia(k + 1)}</p>`).join('')}</div>`;
    }).join('')}</div>`;
  }).join('');
  const prec = s > 1 ? s - 1 : null, succ = s < C.sez.length ? s + 1 : null;
  pagina(`<div class="pagina cronologia larga"><div class="sopratitolo"><a href="#cronologia">Tavola cronologica</a> · ${span(s)}</div>
    <h1>${esc(C.sez[s - 1][1])}</h1>${nav}
    <div class="cron-testata" style="--n:${cols.length}"><div></div>${cols.map(c => `<div>${esc(C.col[c][1])}</div>`).join('')}</div>
    <div class="cron-tavola">${corpo}</div>
    <div class="fine">${prec ? `<a href="#cronologia/${prec}">‹ ${esc(C.sez[prec - 1][1].split('.')[0])}</a>` : '<span></span>'}${succ ? `<a href="#cronologia/${succ}">${esc(C.sez[succ - 1][1].split('.')[0])} ›</a>` : '<a href="#cronologia/dinastie">Dinastie ›</a>'}</div></div>`);
  collegaCitazioni($('#vista'));
  document.title = `${titoloPeriodo(C.sez[s - 1][1])} · Tavola cronologica`;
  if (sel !== null) {
    const p = $('#cv' + (sel + 1));
    if (p) { const alto = $('.barra').getBoundingClientRect().bottom; window.scrollTo(0, p.getBoundingClientRect().top + window.scrollY - alto - 60); }
  }
}
function mostraDinastie() {
  const P = new Map(A.din.map(x => [x[0], x]));
  const figli = new Map(A.din.map(x => [x[0], []]));
  A.din.forEach(x => { for (const g of [x[5], x[6]]) if (g && !figli.get(g).includes(x[0])) figli.get(g).push(x[0]); });
  const nome = x => `<a class="pers-link" href="${hashPersona(x[0])}">${x[1] ? `<span class="num">${esc(x[1])}.</span> ` : ''}${x[3] ? `<em>${esc(x[2])}</em>` : esc(x[2])}</a>${x[4] ? ` <small>${esc(x[4])}</small>` : ''}${S.pers.has(x[0]) && ampiezza(S.pers.get(x[0])[1]) ? ` <small class="pers-n" title="versetti che la nominano">◆ ${num(ampiezza(S.pers.get(x[0])[1]))}</small>` : ''}`;
  const visti = new Set();
  const ramo = id => {
    const x = P.get(id);
    visti.add(id);
    const coniugi = x[7].map(c => P.get(c)).map(c => `<span class="sposo" title="matrimonio">∞</span> ${nome(c)}`).join(' ');
    const fs = figli.get(id).filter(f => P.get(f)[5] === id || !P.get(f)[5]);    // under the father (or the mother alone)
    return `<li id="din-${esc(id)}"><span class="persona">${nome(x)}</span>${coniugi ? ` ${coniugi}` : ''}${x[8] ? `<span class="nota-din">${esc(x[8])}</span>` : ''}${fs.length ? `<ul>${fs.map(f => {
      const madre = P.get(f)[6];
      return ramo(f).replace('<span class="persona">', madre && P.get(id)[7].length > 1 ? `<span class="madre">da ${esc(P.get(madre)[2])}</span><span class="persona">` : '<span class="persona">');
    }).join('')}</ul>` : ''}</li>`;
  };
  const radici = A.din.filter(x => !x[5] && !x[6] && !A.din.some(y => y[7].includes(x[0]) && (y[5] || y[6])));
  const albero = radici.map(x => ramo(x[0])).join('');
  pagina(`<div class="pagina cronologia"><div class="sopratitolo"><a href="#cronologia">Tavola cronologica</a> · appendici, p. 24</div>
    <h1>Dinastie Asmonea e Erodiana</h1>
    <p class="sotto">${num(A.din.length)} persone, i figli sotto il padre (con la madre quando le mogli sono più d’una); ∞ indica matrimonio, i numeri d’ordine, il corsivo e le date sono quelli stampati. Alcune persone stampate due volte nella tavola sono qui una sola (nota accanto).</p>
    <nav class="cron-nav" aria-label="Sezioni della tavola">${A.cron.sez.map(([n, t]) => `<a href="#cronologia/${n}" title="${esc(t)}">${esc(t.split('.')[0])}</a>`).join('')}<a href="#cronologia/dinastie" aria-current="page">Dinastie</a></nav>
    <ul class="dinastie">${albero}</ul></div>`);
  document.title = 'Dinastie Asmonea e Erodiana · Tavola cronologica';
}

// ---------------------------------------------------------------- views: the front matter

function mostraPreliminari(arg) {
  if (arg === 'abbreviazioni') return mostraAbbreviazioni();
  const m = (arg || '').match(/^(.*?)(?:\.(\d+))?$/);
  if (arg) {
    const k = A.testi.findIndex(x => x[0] === m[1]);
    if (k < 0) return nonTrovato('introduzione-generale/' + arg, [`Testo «${esc(m[1])}» non presente nell’Introduzione generale.`, '<a href="#introduzione-generale">L’Introduzione generale</a>']);
    return mostraTestoPreliminare(k, m[2]);
  }
  const E = A.ed;
  const voce = (x, k) => `<a class="pre-testo" href="#introduzione-generale/${esc(x[0])}"><b>${esc(x[1])}</b>${x[2] ? `<i>${esc(x[2])}</i>` : ''}<span>${x[4] ? esc(x[4]) + ' · ' : ''}p. ${esc(x[3])}</span></a>`;
  pagina(`<div class="pagina preliminari"><div class="sopratitolo">Introduzione generale · pp. ii–xxviii</div>
    <h1>${esc(E.t)}</h1><p class="sotto">${esc(E.pub)}, ${esc(E.luogo)} · ISBN ${esc(E.isbn)} · ${E.stampe.map(s => `${esc(s[0])}: ${esc(s[1])}`).join('; ')}</p>
    <details class="colofone"><summary>Dati editoriali (p. iv)</summary><p>${E.colofone.map(esc).join('<br>')}</p></details>
    <div class="h2">Presentazione e prefazioni</div><div class="pre-testi">${A.testi.filter(x => x[7] === 'presentazione' || x[7] === 'prefazione').map(voce).join('')}</div>
    <div class="h2">Il canone e le abbreviazioni</div><div class="pre-testi">${A.testi.filter(x => x[7] === 'canone').map(voce).join('')}
      <a class="pre-testo" href="#introduzione-generale/abbreviazioni"><b>Abbreviazioni e codici</b><span>${num(A.abbr.filter(a => a[2] === 'libro').length)} sigle dei libri, ${num(A.abbr.filter(a => a[2].startsWith('codice') || a[2] === 'papiro').length)} codici e papiri · pp. xxii–xxiv</span></a></div>
    <div class="h2">Avvertenze</div><div class="pre-testi">${A.testi.filter(x => x[7] === 'avvertenze').map(voce).join('')}</div>
    <div class="h2">Nelle appendici</div><div class="pre-testi">
      <a class="pre-testo" href="#indice-note"><b>${esc(INDICI.note.nome)}</b><span>${num(A.meta.note.entries)} voci · ${num(A.meta.note.references)} riferimenti</span></a>
      <a class="pre-testo" href="#temi"><b>${esc(INDICI.temi.nome)}</b><span>${num(A.meta.temi.entries)} temi · ${num(A.meta.temi.references)} riferimenti</span></a>
      <a class="pre-testo" href="#cronologia"><b>Tavola cronologica</b><span>${num(A.meta.cron)} voci · dinastie Asmonea e Erodiana</span></a></div></div>`);
  document.title = 'Introduzione generale · Esploratore dei versetti';
}
function mostraTestoPreliminare(k, nn) {
  const [id, titolo, sotto, pag0, firma, qual, corsivo, tipo, pars] = A.testi[k];
  let pag = null;
  const corpo = pars.map(([n, pg, h]) => {
    const seg = pg !== pag ? `<span class="pg">p. ${esc(pg)}</span>` : '';
    pag = pg;
    return `<p id="par${n}">${seg}${h}</p>`;
  }).join('');
  let extra = '';
  if (tipo === 'canone') {
    const c = A.canoni[id === 'divisione-ebraica' ? 0 : 1];
    const voce = it => {
      const dove = [...it[3].map(b => `<a href="#${D.libri[b].o}">${esc(D.libri[b].s)}</a>`), ...it[4].map(x => `<a href="#${x}">${esc(D.libri[S.osis.get(x.split('.')[0])].s)} ${esc(x.split('.')[1])}</a>`)];
      return `<li class="${it[6] ? 'apocrifo' : ''}"><span class="cn">${c[0] === 'ebraico' ? it[0] + '.' : ''}</span>${it[2]}${dove.length ? ` <small class="in-bibbia">→ ${dove.join(', ')}</small>` : it[6] ? ' <small class="in-bibbia">non in questa Bibbia</small>' : ''}</li>`;
    };
    extra = c[1].map(g => `<div class="canone-gruppo${g[2] ? ' sotto' : ''}"><div class="canone-tit">${g[1]}</div><ul class="canone">${c[2].filter(it => it[1] === g[0]).map(voce).join('')}</ul></div>`).join('');
    extra = `<div class="h2">L’elenco</div><div class="canone-box">${extra}</div>`;
  }
  if (id === 'avvertenze') {
    extra = `<div class="h2">Le xilografie e i passi che illustrano</div><p class="sotto">Dai riferimenti qui sopra: la xilografia che apre ogni libro, con i suoi versetti.</p><div class="chips xilo">${A.xilo.map(x => chip(x[3], `${esc(D.libri[x[0]].s)} ${esc(x[2])}`, ` title="${esc(x[1])}"`)).join('')}</div>`;
  }
  pagina(`<div class="pagina"><div class="sopratitolo"><a href="#introduzione-generale">Introduzione generale</a> · p. ${esc(pag0)}</div>
    <h1>${esc(titolo)}</h1>${sotto ? `<p class="sotto"><i>${esc(sotto)}</i></p>` : ''}
    ${firma ? `<div class="firma-pre"><b>${esc(firma)}</b>${qual.map(q => `<span>${esc(q)}</span>`).join('')}</div>` : ''}
    <div class="intro-testo${corsivo ? ' corsivo' : ''}">${corpo}</div>${extra}</div>`);
  collegaCitazioni($('#vista'));
  document.title = titolo + ' · Introduzione generale';
  if (nn) {
    const p = $('#par' + nn);
    if (p) { p.classList.add('sel'); window.scrollTo(0, p.getBoundingClientRect().top + window.scrollY - 110); }
  }
}
function mostraAbbreviazioni() {
  const riga = a => {
    const libri = a[4].map(b => `<a href="#${D.libri[b].o}">${esc(D.libri[b].t)}</a>`).join(', ');
    const ns = a[5] ? G.cod[a[5]] || [] : (G.ver.find(v => v[2] === A.abbr.indexOf(a) + 1) || [, , , []])[3];
    const citato = ns.length ? `<details class="altri citato"><summary class="altro">citato in ${quanti(ns.length, 'nota', 'note')}</summary><span class="chips">${ns.slice(0, 400).map(k => `<a class="chip" href="${hashVerso(D.note[k][0])}" data-nota="${k}" data-r="${D.note[k][0]}-${D.note[k][0]}">${esc(etichettaNota(D.note[k]))}</a>`).join('')}${ns.length > 400 ? ` <small>e altre ${num(ns.length - 400)}</small>` : ''}</span></details>` : '';
    return `<tr><td class="ab-f">${esc(a[0])}</td><td>${esc(a[1])}${libri && a[2] === 'libro' && a[4].length > 1 ? ` <small>(${libri})</small>` : ''}${a[5] && a[5] !== a[0] ? ` <small class="greg">Gregory-Aland ${esc(a[5])}</small>` : ''}${citato}</td></tr>`;
  };
  const libro = a => a[4].length === 1 ? `<a href="#${D.libri[a[4][0]].o}">${esc(a[1])}</a>` : esc(a[1]);
  const gruppi = TIPI_ABBR.map(([t, tit]) => {
    const xs = A.abbr.filter(a => a[2] === t);
    if (!xs.length) return '';
    if (t === 'libro') return `<div class="h2">${tit} <span class="n">${xs.length}</span></div><div class="abbr-libri">${xs.map(a => `<span><b>${esc(a[0])}</b> ${libro(a)}</span>`).join('')}</div>`;
    return `<div class="h2">${tit} <span class="n">${xs.length}</span></div><table class="abbr"><tbody>${xs.map(riga).join('')}</tbody></table>`;
  }).join('');
  pagina(`<div class="pagina preliminari"><div class="sopratitolo"><a href="#introduzione-generale">Introduzione generale</a> · pp. xxii–xxiv</div>
    <h1>Abbreviazioni e codici</h1><p class="sotto">Come stampate. Le sigle dei libri sono quelle del canone di questa Bibbia (Est indica i due testi di Ester); i codici con il loro numero nella lista Gregory-Aland.</p>${gruppi}</div>`);
  document.title = 'Abbreviazioni e codici · Introduzione generale';
}

// ---------------------------------------------------------------- search in the front matter and appendices

function indicePar(I) {
  if (I.pt) return;
  I.pt = [];          // [kind, a, b, plain]: 0 text paragraph (text, paragraph index), 1 chronology entry, 2 index entry (index, entry)
  A.testi.forEach((x, k) => x[8].forEach((p, j) => I.pt.push([0, k, j, testoPiano(p[2])])));
  A.cron.voci.forEach((v, k) => I.pt.push([1, k, 0, v[11]]));
  for (const id of Object.keys(INDICI)) A.indici[id].forEach((v, k) => I.pt.push([2, id, k, v[2] + (v[5].length ? ' · ' + v[5].map(s => s[2]).join(' · ') : '')]));
  I.ptn = I.pt.map(x => normalizza(x[3]));
}
function bloccoPar(I, ts, tutti) {
  indicePar(I);
  const hit = [];
  I.ptn.forEach((x, j) => { if (tutti(x)) hit.push(j); });
  if (!hit.length) return ['', 0];
  const voci = hit.filter(j => I.pt[j][0] === 2), altri = hit.filter(j => I.pt[j][0] !== 2);
  const riga = j => {
    const [t, a, b] = I.pt[j];
    if (t === 0) { const x = A.testi[a]; return `<div class="r rp"><a class="dove" href="#introduzione-generale/${esc(x[0])}.${x[8][b][0]}">${esc(x[1])}<small>p. ${esc(x[8][b][1])}</small></a><div class="frase">${evidenzia(I.pt[j][3], I.ptn[j], ts)}</div></div>`; }
    const v = A.cron.voci[a];
    return `<div class="r rp"><a class="dove" href="${hashCron(a + 1)}">Cronologia<small>${v[7] ? esc(v[7]) : esc(A.cron.sez[v[0] - 1][1].split('.')[0])}</small></a><div class="frase">${evidenzia(I.pt[j][3], I.ptn[j], ts)}</div></div>`;
  };
  let h = `<section class="blocco bpar"><h3><span class="seg">¶</span>Introduzione generale e appendici<small>${quanti(voci.length, 'voce d’indice', 'voci d’indice')} · ${quanti(altri.length, 'altro risultato', 'altri risultati')}</small></h3>`;
  if (voci.length) h += `<div class="chips pchips">${voci.map(j => { const [, id, k] = I.pt[j], v = A.indici[id][k]; return `<a class="chip" href="${hashIndice(id, v[0])}" title="${esc(INDICI[id].nome)}">${v[1]} <small>${id === 'note' ? 'indice note' : 'tema'}</small></a>`; }).join('')}</div>`;
  h += altri.slice(0, 30).map(riga).join('');
  if (altri.length > 30) h += `<details class="altri"><summary class="altro">mostra altri ${altri.length - 30}</summary>${altri.slice(30).map(riga).join('')}</details>`;
  return [h + '</section>', hit.length];
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
  if (filtro.has('diz')) {
    // the entries of the dictionary citing the passage: one card per entry, at its most
    // specific citation
    const per = new Map();
    Z.cit.forEach((c, k) => {
      if (!sovrappone(c[3], a, b)) return;
      const w = ampiezza(c[3]), x = per.get(c[0]);
      if (!x || w < x.w) per.set(c[0], { voce: c[0], cit: k, x: -1, y: -1, rel: 'diz', dir: 1, w });
    });
    out.push(...per.values());
  }
  const pri = { parallel: 0, 'quoted-later': 1, doublet: 2, keynote: 3, related: 4, cites: 5, diz: 6 };
  return out.filter(e => !(e.x === a && e.y === b)).sort((p, q) => pri[p.rel] - pri[q.rel] || p.w - q.w || p.x - q.x);
}
function viciniVoce(c) {
  // the passages an entry cites: those of the paragraph that led here first, then the others,
  // in the order printed
  const ks = S.citDi[c.voce], par = Z.cit[c.cit][1], sez = Z.cit[c.cit][2];
  const qui = k => Z.cit[k][1] === par && (par >= 0 || Z.cit[k][2] === sez);
  const out = [];
  for (const k of [...ks.filter(qui), ...ks.filter(k => !qui(k))]) {
    const r = Z.cit[k][3];
    for (let j = 0; j < r.length; j += 2) out.push({ x: r[j], y: r[j + 1], rel: 'diz', dir: 1, w: r[j + 1] - r[j] });
  }
  return out;
}
// The graph view is a tree to explore: the chosen verse is the root, its links hang from it
// grouped by relation and direction, and every card can grow its own links (▸) in turn.
// A card is HTML (the verse text, its BJ notes as yellow slips) inside a hand-drawn SVG
// contour; the branches are SVG curves under the cards.
const ALB = { CARTA: 300, RADICE: 400, SPAZIO: 46, SPAZIO_G: 22, PASSO: 16, RADICE_N: 8, ALTRI_N: 4, PIU: 10, MAX: 260 };

function rng(seed) { return () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; }; }
function schizzo(w, h, seme) {
  // a rectangle drawn twice by hand: wobbly sides that overshoot the corners a little,
  // over a slightly crooked sheet
  const r = rng(seme + 1), q = j => (r() - 0.5) * 2 * j;
  const lato = (x1, y1, x2, y2) => {
    const dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1, ux = dx / L, uy = dy / L;
    const s1 = 1 + r() * 5, s2 = 1 + r() * 5, m = 0.3 + r() * 0.4, b = q(Math.min(4.5, L / 35));
    const ax = x1 - ux * s1 + q(1.6), ay = y1 - uy * s1 + q(1.6), bx = x2 + ux * s2 + q(1.6), by = y2 + uy * s2 + q(1.6);
    const cx = x1 + dx * m - uy * b, cy = y1 + dy * m + ux * b;
    return `M${ax.toFixed(1)} ${ay.toFixed(1)}Q${cx.toFixed(1)} ${cy.toFixed(1)} ${bx.toFixed(1)} ${by.toFixed(1)}`;
  };
  let d = '';
  for (let p = 0; p < 2; p++) d += lato(0, 0, w, 0) + lato(w, 0, w, h) + lato(w, h, 0, h) + lato(0, h, 0, 0);
  const f = () => q(1.6).toFixed(1);
  const fondo = `M${f()} ${f()}L${(w + +f()).toFixed(1)} ${f()}L${(w + +f()).toFixed(1)} ${(h + +f()).toFixed(1)}L${f()} ${(h + +f()).toFixed(1)}Z`;
  return { d, fondo };
}
function contorno(el, seme) {
  const w = el.offsetWidth, h = el.offsetHeight, { d, fondo } = schizzo(w, h, seme);
  el.querySelector(':scope > svg.contorno')?.remove();
  el.insertAdjacentHTML('afterbegin', `<svg class="contorno" width="${w + 16}" height="${h + 16}" viewBox="-8 -8 ${w + 16} ${h + 16}" aria-hidden="true"><path class="fondo" d="${fondo}"/><path class="tratto" d="${d}"/></svg>`);
}

// ---- the tree: cards (passages) and, between them, the groups of one relation and direction

const nuovaCarta = (a, b, padre) => ({ tipo: 'carta', a, b, k: a + '-' + b, padre, aperta: false, figli: null });
// an entry of the dictionary as a card: cit is the citation that brought it into the tree
const nuovaVoce = (e, padre) => ({ tipo: 'carta', voce: e.voce, cit: e.cit, k: 'v' + e.voce, padre, aperta: false, figli: null });
const chiaveVicino = e => (e.voce !== undefined ? 'v' + e.voce : e.x + '-' + e.y);
function antenati(n) {
  const s = new Set();
  for (let x = n; x; x = x.padre) if (x.tipo === 'carta') s.add(x.k);
  return s;
}
function collegamenti(c) {
  // the links of a card grouped by relation and direction, without the passages on its
  // path from the root (a tree has no cycles); memoised per card
  if (c.gruppi) return c.gruppi;
  const gruppi = new Map(), visti = antenati(c);
  for (const e of c.voce !== undefined ? viciniVoce(c) : vicini(c.a, c.b, S.filtro)) {
    const k = chiaveVicino(e);
    if (visti.has(k)) continue;
    visti.add(k);
    const due = e.rel === 'parallel' || e.rel === 'doublet';       // printed both ways
    const g = e.rel + (due ? '' : e.dir > 0 ? '>' : '<');
    if (!gruppi.has(g)) gruppi.set(g, { tipo: 'gruppo', rel: e.rel, dir: due ? 0 : e.dir, padre: c, voci: [], figli: [] });
    gruppi.get(g).voci.push(e);
  }
  c.gruppi = [...gruppi.values()];
  c.nvoci = c.gruppi.reduce((s, g) => s + g.voci.length, 0);
  return c.gruppi;
}
function altri(g, n) {
  g.figli.push(...g.voci.slice(g.figli.length, g.figli.length + n).map(e => (e.voce !== undefined ? nuovaVoce(e, g) : nuovaCarta(e.x, e.y, g))));
}
function apri(c) {
  if (!c.figli) {
    c.figli = collegamenti(c);
    for (const g of c.figli) altri(g, c.padre ? ALB.ALTRI_N : ALB.RADICE_N);
  }
  c.aperta = true;
}
const figliVisibili = n => (n.tipo === 'gruppo' ? n.figli : n.aperta ? n.figli : []);
function tutti(n, out = []) {
  out.push(n);
  for (const c of figliVisibili(n)) tutti(c, out);
  return out;
}
function titoloGruppo(g) {
  const R = REL[g.rel];
  if (g.rel === 'cites') return g.dir > 0 ? '§ Le sue note citano' : '§ Citato nelle note di';
  if (g.rel === 'diz') return g.padre.voce !== undefined ? '◊ La voce cita' : '◊ Nel Dizionario';
  if (!g.dir) return `${R.seg} ${R.nome}`;
  return g.dir > 0 ? `${R.seg} ${R.nome} →` : `← ${R.seg} ${R.entr}`;
}

// ---- what a card shows

function testoCarta(a, b, max) {
  // the passage with its verse numbers, cut at a word after max characters
  const fine = Math.min(b, a + 8);
  let out = '', len = 0;
  for (let v = a; v <= fine; v++) {
    let t = testoPiano(V.h[v]).replace(/\s+/g, ' ').trim();
    if (len + t.length > max) { t = t.slice(0, Math.max(0, max - len)).replace(/\s+\S*$/, '') + '…'; }
    out += (b > a ? `<sup>${esc(versoDi(v))}</sup>` : '') + esc(t) + ' ';
    len += t.length;
    if (len >= max) break;
  }
  if (len < max && fine < b) out += '…';
  return out.trim() || '<i>versetto omesso dalla CEI</i>';
}
function foglietti(c, radice) {
  // the BJ notes called from the passage, as yellow slips (a click opens the whole note)
  const ks = [];
  for (let v = c.a; v <= Math.min(c.b, c.a + 8); v++) ks.push(...(S.noteAt[v] || []));
  const max = radice ? 6 : 2;
  const html = ks.slice(0, max).map(k => {
    const x = D.note[k], intera = S.noteAperte.has(k), piano = testoPiano(x[5]), lim = radice ? 420 : 120;
    const corpo = intera || piano.length <= lim ? x[5] : esc(piano.slice(0, lim).replace(/\s+\S*$/, '')) + '…';
    const bottone = piano.length > lim ? `<button type="button" class="altro" data-nota="${k}">${intera ? 'riduci' : 'continua'}</button>` : '';
    return `<div class="foglietto" data-n="${k}"><b>${esc(x[3])}${esc(x[2] || 'nota')}</b>${corpo} ${bottone}</div>`;
  }).join('');
  return html + (ks.length > max ? `<div class="foglietti-altre">${ks.length - max === 1 ? 'e un’altra nota' : `e altre ${ks.length - max} note`}: <a href="${hashVerso(c.a)}">nel lettore</a></div>` : '');
}
function htmlVoceCarta(c) {
  // an entry: its name (opens the entry at the paragraph), the section, the sentence around the
  // citation; ▸ grows the passages it cites
  collegamenti(c);
  const n = c.nvoci, k = c.voce, cz = Z.cit[c.cit], s = sezioneDi(k, cz[2]);
  const pn = cz[1] >= 0 ? Z.voci[k][9][cz[1]][0] : primoParDi(k, cz[2]);
  const dove = hashVoce(k, pn, c.padre?.padre?.a);
  return `<div class="carta voce" data-i="${c.i}" style="width:${S.albW.carta}px">
    <div class="carta-testa"><span class="pallino diz" title="Dizionario di Teologia Biblica"></span><a class="carta-rif" href="${dove}" title="Apri la voce">${esc(nomeVoce(k))}</a><span class="carta-libro">Dizionario</span></div>
    ${s ? `<div class="carta-sez"><span class="percorso">${esc(s[0])}</span>${esc(testoPiano(s[2]))}</div>` : ''}
    <div class="carta-testo">${fraseCit(c.cit, 230)}</div>
    <div class="carta-piede"><button type="button" class="cresci" data-i="${c.i}" aria-expanded="${c.aperta}"${n ? '' : ' disabled'}>${n ? `${c.aperta ? '▾' : '▸'} ${n} ${n === 1 ? 'passo citato' : 'passi citati'}` : 'nessun altro passo'}</button><a class="leggi" href="${dove}">leggi ›</a></div></div>`;
}
function htmlCarta(c) {
  if (c.voce !== undefined) return htmlVoceCarta(c);
  const radice = !c.padre, id = V.id[c.a], AT = D.libri[S.vb[c.a]].T === 'AT';
  collegamenti(c);
  const n = c.nvoci;
  const cresci = radice ? `<span class="conta">${n ? `${n} collegament${n === 1 ? 'o' : 'i'}` : 'nessun collegamento'}</span>`
    : `<button type="button" class="cresci" data-i="${c.i}" aria-expanded="${c.aperta}"${n ? '' : ' disabled'}>${n ? `${c.aperta ? '▾' : '▸'} ${n} collegament${n === 1 ? 'o' : 'i'}` : 'nessun altro collegamento'}</button>`;
  return `<div class="carta${radice ? ' radice' : ''}" data-i="${c.i}" style="width:${radice ? S.albW.radice : S.albW.carta}px">
    <div class="carta-testa"><span class="pallino ${AT ? 'at' : 'nt'}" title="${AT ? 'Antico' : 'Nuovo'} Testamento"></span><a class="carta-rif" href="#grafo/${id}${S.albProf > 1 ? '?p=2' : ''}" title="Metti al centro">${esc(rif(c.a, c.b))}</a><span class="carta-libro">${esc(D.libri[S.vb[c.a]].t)}</span></div>
    <div class="carta-testo">${testoCarta(c.a, c.b, radice ? 900 : 260)}</div>
    ${foglietti(c, radice)}
    <div class="carta-piede">${cresci}<a class="leggi" href="${hashVerso(c.a, c.b)}">leggi ›</a></div></div>`;
}
function htmlGruppo(g) {
  const resto = g.voci.length - g.figli.length;
  return `<div class="ramo-gruppo" data-i="${g.i}" style="--c:var(${REL[g.rel].txt || REL[g.rel].col})"><span>${esc(titoloGruppo(g))}</span><small>${g.voci.length}</small>${resto > 0 ? `<button type="button" class="altri" data-i="${g.i}">+${Math.min(resto, ALB.PIU)} di ${resto}</button>` : ''}</div>`;
}

// ---- layout: a tidy tree from left to right; each node is centred on its children

function disponi(n, x, top) {
  n.x = x;
  const figli = figliVisibili(n);
  if (!figli.length) { n.y = top; return top + n.h; }
  const dx = x + n.w + (n.tipo === 'carta' ? ALB.SPAZIO : ALB.SPAZIO_G);
  let y = top;
  figli.forEach((c, j) => { if (j) y += c.tipo === 'gruppo' ? ALB.PASSO * 1.8 : ALB.PASSO; y = disponi(c, dx, y); });
  const p = figli[0], u = figli[figli.length - 1];
  n.y = Math.max(top, (p.y + p.h / 2 + u.y + u.h / 2) / 2 - n.h / 2);
  return Math.max(y, n.y + n.h);
}
function ramo(p, n) {
  const x1 = p.x + p.w, y1 = p.y + Math.min(p.h / 2, p.tipo === 'carta' ? 60 : p.h / 2), x2 = n.x, y2 = n.y + Math.min(n.h / 2, n.tipo === 'carta' ? 28 : n.h / 2);
  const g = n.tipo === 'gruppo' ? n : p, dm = (x2 - x1) / 2;
  const dash = REL[g.rel].dash.length ? ` stroke-dasharray="${REL[g.rel].dash.map(x => x * 1.5).join(' ')}"` : '';
  return `<path class="ramo" style="stroke:var(${REL[g.rel].col})"${dash} d="M${x1} ${y1}C${x1 + dm} ${y1} ${x2 - dm} ${y2} ${x2} ${y2}"/>`;
}

// ---- the view

function mostraGrafo(id, par) {
  let i = S.vix.get(id);
  if (i === undefined && id) {
    pagina(`<div class="pagina"><h1>Versetto non trovato</h1><p class="sotto">«${esc(id)}» non è l’identificativo di un versetto (per esempio <a href="#grafo/John.3.16">John.3.16</a>).</p></div>`);
    document.title = 'Non trovato · Grafo';
    return;
  }
  const prof = par.p === '2' ? 2 : 1;
  if (i === undefined) {                 // the Grafo tab: the selected verse, written in the address
    i = S.sel ?? S.ultimo ?? S.vix.get('John.3.16');
    history.replaceState(null, '', `#grafo/${V.id[i]}${prof > 1 ? '?p=2' : ''}`);
  }
  S.ultimo = i;
  S.albProf = prof;
  const stretto = window.innerWidth < 700;
  S.albW = { carta: stretto ? 250 : ALB.CARTA, radice: stretto ? 290 : ALB.RADICE, zmin: stretto ? 0.72 : 0.6 };
  S.noteAperte = S.noteAperte || new Set();
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
    <div class="grafo-tela" id="tela"><div class="mondo" id="mondo"></div>
      <div class="grafo-titolo"><b>${esc(rif(i))}</b><span>${esc(D.libri[S.vb[i]].t)} · albero dei collegamenti</span></div>
      <div class="grafo-zoom"><button type="button" data-z="1.2" aria-label="Ingrandisci">+</button><button type="button" data-z="0.83" aria-label="Riduci">−</button><button type="button" data-z="0" aria-label="Adatta alla finestra" title="Adatta alla finestra">⌂</button></div></div>
    <div class="grafo-lato"><button type="button" class="lato-apri" aria-expanded="false" data-lato>Comandi e relazioni</button>
      <h3>Versetto</h3><div class="grafo-info"><a class="bottone primario" href="#${V.id[i]}">Apri nel lettore</a></div>
      <h3>Esplora</h3>
      <div class="segmenti" role="group"><button type="button" data-esplora="piu">Apri un livello</button><button type="button" data-esplora="chiudi">Chiudi tutto</button></div>
      <h3>Relazioni (rami)</h3>
      ${ORDINE_REL.map(r => `<label class="leg"><input type="checkbox" data-rel="${r}"${S.filtro.has(r) ? ' checked' : ''}>${linea(r)}<span>${REL[r].seg} ${REL[r].nome}</span><span class="n">${conta[r] || 0}</span></label>`).join('')}
      <h3>Schede</h3>
      <div class="leg"><svg width="26" height="14"><circle cx="13" cy="7" r="5" fill="var(--s-at)"/></svg>Antico Testamento</div>
      <div class="leg"><svg width="26" height="14"><circle cx="13" cy="7" r="5" fill="var(--s-nt)"/></svg>Nuovo Testamento</div>
      <div class="leg"><svg width="26" height="16"><rect x="3" y="2" width="20" height="12" fill="var(--foglietto)" stroke="var(--foglietto-tratto)"/></svg>nota della BJ</div>
      <div class="leg"><svg width="26" height="16"><rect x="3" y="2" width="20" height="12" fill="var(--biglietto-diz)" stroke="var(--tratto)"/></svg>voce del Dizionario</div>
      <h3>Albero</h3><div class="grafo-info" id="ginfo"></div>
      <details class="grafo-nodi"><summary>Elenco delle schede</summary><ul id="gnodi"></ul></details>
      <p class="grafo-info nota-grafo">▸ su una scheda apre i suoi collegamenti, raggruppati per relazione; il riferimento la mette al centro (il nome di una voce del Dizionario la apre). Trascina per spostarti, rotella per scorrere, Ctrl + rotella o +/− per lo zoom.</p>
    </div></div>`);
  document.title = `Grafo ${rif(i)} · Esploratore dei versetti`;
  S.ridisegna = null;
  $('.grafo-lato').addEventListener('change', e => {
    const r = e.target.dataset.rel;
    if (!r) return;
    if (e.target.checked) S.filtro.add(r); else S.filtro.delete(r);
    history.replaceState(null, '', indirizzo());
    nuovoAlbero(i, prof);
  });
  $('.grafo-lato .segmenti').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.esplora === 'chiudi') { tutti(S.albero).forEach(n => { if (n.tipo === 'carta' && n.padre) n.aperta = false; }); disegnaAlbero(null, true); return; }
    // one more level: every visible leaf card with links, up to the cap
    let quante = tutti(S.albero).length;
    for (const n of tutti(S.albero)) {
      if (n.tipo !== 'carta' || n.aperta || !n.padre || quante > ALB.MAX) continue;
      collegamenti(n);
      if (!n.nvoci) continue;
      apri(n);
      quante += n.figli.length + n.figli.reduce((s, g) => s + g.figli.length, 0);
    }
    disegnaAlbero(null, true);
  });
  interazioni();
  $('[data-lato]')?.addEventListener('click', e => {
    // on the phone the controls are a sheet under the canvas, closed at first (R3 E9)
    const l = $('.grafo-lato'), ap = !l.classList.contains('aperto');
    l.classList.toggle('aperto', ap);
    e.currentTarget.setAttribute('aria-expanded', String(ap));
  });
  nuovoAlbero(i, prof);
}
function nuovoAlbero(i, prof) {
  S.albero = nuovaCarta(i, i, null);
  apri(S.albero);
  if (prof > 1) for (const g of S.albero.figli) for (const c of g.figli) { collegamenti(c); if (c.nvoci) apri(c); }
  disegnaAlbero(null, true);
}
function disegnaAlbero(fermo, adattare) {
  // fermo: a node that keeps its place on the screen (the one just opened)
  const mondo = $('#mondo');
  if (!mondo) return;
  const prima = fermo ? { x: S.av.x + fermo.x * S.av.z, y: S.av.y + fermo.y * S.av.z } : null;
  const nodi = tutti(S.albero);
  nodi.forEach((n, k) => { n.i = k; n.liv = !n.padre ? 0 : n.tipo === 'carta' ? n.padre.padre.liv + 1 : n.padre.liv; });
  S.albNodi = nodi;
  mondo.innerHTML = '<svg class="rami" id="rami"></svg>' + nodi.map(n => (n.tipo === 'carta' ? htmlCarta(n) : htmlGruppo(n))).join('');
  const els = mondo.children;
  nodi.forEach((n, k) => { n.el = els[k + 1]; n.w = n.el.offsetWidth; n.h = n.el.offsetHeight; });
  disponi(S.albero, 0, 0);
  let y0 = Infinity, X = 0, Y = 0;
  nodi.forEach(n => { y0 = Math.min(y0, n.y); });
  nodi.forEach(n => {
    n.y -= y0;
    n.el.style.transform = `translate(${n.x}px,${n.y}px)`;
    X = Math.max(X, n.x + n.w); Y = Math.max(Y, n.y + n.h);
  });
  nodi.forEach(n => {
    if (n.tipo !== 'carta') return;
    contorno(n.el, n.voce !== undefined ? 100003 + n.voce * 7 : n.a * 7 + n.b);
    $$('.foglietto', n.el).forEach((f, j) => contorno(f, +f.dataset.n * 3 + j));
  });
  const rami = $('#rami');
  rami.setAttribute('width', X); rami.setAttribute('height', Y);
  rami.innerHTML = nodi.filter(n => n.padre).map(n => ramo(n.padre, n)).join('');
  S.albDim = { w: X, h: Y };
  if (adattare) adatta();
  else if (prima) { S.av.x = prima.x - fermo.x * S.av.z; S.av.y = prima.y - fermo.y * S.av.z; }
  applica();
  const carte = nodi.filter(n => n.tipo === 'carta' && n.voce === undefined), nAT = carte.filter(n => D.libri[S.vb[n.a]].T === 'AT').length;
  const voci = nodi.filter(n => n.voce !== undefined);
  const nNote = carte.reduce((s, n) => s + n.el.querySelectorAll('.foglietto').length, 0);
  $('#ginfo').innerHTML = `<b>${carte.length}</b> ${carte.length === 1 ? 'scheda' : 'schede'}, <b>${nNote}</b> ${nNote === 1 ? 'nota' : 'note'} della BJ<br>${nAT} nell’AT, ${carte.length - nAT} nel NT` +
    (voci.length ? `<br><b>${voci.length}</b> ${voci.length === 1 ? 'voce' : 'voci'} del Dizionario` : '') +
    (!S.filtro.size ? '<br><small>nessuna relazione scelta: spunta almeno una casella</small>' : '');
  $('#gnodi').innerHTML = nodi.filter(n => n.tipo === 'carta' && n.padre).map(n => (n.voce !== undefined
    ? `<li><a href="${hashVoce(n.voce)}">◊ ${esc(nomeVoce(n.voce))}</a> <small>Dizionario</small></li>`
    : `<li><a href="#grafo/${V.id[n.a]}${S.albProf > 1 ? '?p=2' : ''}">${esc(rif(n.a, n.b))}</a></li>`)).join('');
}
function applica() {
  const m = $('#mondo');
  if (m) m.style.transform = `translate(${S.av.x}px,${S.av.y}px) scale(${S.av.z})`;
}
function adatta(tutto = false) {
  // the whole tree if it fits at a readable size (or always, with ⌂), else the root at the
  // left, centred, at reading size
  const t = $('#tela').getBoundingClientRect(), d = S.albDim, r = S.albero;
  const alto = $('#tela .grafo-titolo').getBoundingClientRect().bottom - t.top + 14;     // below the title
  const z = Math.min(1, (t.width - 48) / d.w, (t.height - alto - 24) / d.h);
  // first view: the root and the next one or two columns of cards at a readable size
  const vicine = Math.max(...S.albNodi.filter(n => n.liv <= (window.innerWidth < 700 ? 1 : 2)).map(n => n.x + n.w));   // the phone: root and first level (R3 E9)
  const leggibile = Math.max(window.innerWidth < 700 ? 0.42 : S.albW.zmin, Math.min(1, (t.width - 48) / vicine));
  S.av = { z: tutto ? Math.max(0.3, z) : z < leggibile ? leggibile : z, x: 0, y: 0 };
  S.av.x = d.w * S.av.z <= t.width - 48 ? (t.width - d.w * S.av.z) / 2 : 24;
  if (d.h * S.av.z <= t.height - alto - 24) S.av.y = alto + (t.height - alto - d.h * S.av.z) / 2;
  else S.av.y = Math.max(alto - r.y * S.av.z, t.height / 2 - (r.y + r.h / 2) * S.av.z);   // root centred, its top in view
}
function interazioni() {
  const tela = $('#tela');
  S.av = { x: 0, y: 0, z: 1 };
  let giu = null;
  tela.addEventListener('pointerdown', e => {
    if (e.button !== 0 || e.target.closest('a, button, .foglietto')) return;
    giu = { x: e.clientX, y: e.clientY, vx: S.av.x, vy: S.av.y, mosso: false };
    tela.setPointerCapture(e.pointerId);
  });
  tela.addEventListener('pointermove', e => {
    if (!giu) return;
    if (Math.hypot(e.clientX - giu.x, e.clientY - giu.y) > 4) { giu.mosso = true; tela.classList.add('trascina'); }
    if (giu.mosso) { S.av.x = giu.vx + e.clientX - giu.x; S.av.y = giu.vy + e.clientY - giu.y; applica(); }
  });
  const su = () => { giu = null; tela.classList.remove('trascina'); };
  tela.addEventListener('pointerup', su);
  tela.addEventListener('pointercancel', su);
  tela.addEventListener('wheel', e => {
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) {
      const r = tela.getBoundingClientRect();
      zoomAlbero(e.deltaY < 0 ? 1.1 : 1 / 1.1, e.clientX - r.left, e.clientY - r.top);
    } else { S.av.x -= e.shiftKey ? e.deltaY : e.deltaX; S.av.y -= e.shiftKey ? 0 : e.deltaY; applica(); }
  }, { passive: false });
  tela.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.closest('.grafo-zoom')) {
      if (+b.dataset.z === 0) { adatta(true); applica(); } else zoomAlbero(+b.dataset.z);
      return;
    }
    const n = S.albNodi[+b.dataset.i];
    if (b.classList.contains('cresci')) {
      if (n.aperta) n.aperta = false; else apri(n);
      disegnaAlbero(n);
    } else if (b.classList.contains('altri')) {
      altri(n, ALB.PIU);
      disegnaAlbero(n);
    } else if (b.classList.contains('altro')) {
      const k = +b.dataset.nota, c = S.albNodi[+b.closest('.carta').dataset.i];
      if (S.noteAperte.has(k)) S.noteAperte.delete(k); else S.noteAperte.add(k);
      disegnaAlbero(c);
    }
  });
}
function zoomAlbero(f, cx, cy) {
  const t = $('#tela').getBoundingClientRect();
  if (cx === undefined) { cx = t.width / 2; cy = t.height / 2; }
  const z = Math.max(0.3, Math.min(2.2, S.av.z * f));
  S.av.x = cx - (cx - S.av.x) * (z / S.av.z);
  S.av.y = cy - (cy - S.av.y) * (z / S.av.z);
  S.av.z = z;
  applica();
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
    ${panoramicaDiz()}
    ${panoramicaPar()}
  </div>`);
  document.title = 'Panoramica · Esploratore dei versetti';
  disegnaMatrice(sel, sel.length === 2);
  $('#dtop-scelta').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    $$('#dtop-scelta button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    $('#dtop tbody').innerHTML = righeTopDiz(b.dataset.top === 'stretti');
  });
}
function panoramicaPar() {
  const m = A.meta, n = m.note, t = m.temi;
  const pct = (a, b) => (100 * a / b).toFixed(1).replace('.', ',') + '%';
  const tessere = [
    [num(n.entries), 'voci dell’indice delle note', `${num(n.subentries)} sottovoci · <a href="#indice-note">l’indice</a>`],
    [num(n.references), 'riferimenti alle note della BJ', `${pct(n.nota.nota || 0, n.references)} alla prima riga di una nota, ${pct(n.nota.copre || 0, n.references)} dentro una nota`],
    [num(t.entries), 'temi pastorali', `${num(t.subentries)} sottotemi · ${num(t.references)} riferimenti · <a href="#temi">i temi</a>`],
    [num(m.cron), 'voci della tavola cronologica', `${num(m.datate)} datate · ${num(m.ccit)} riferimenti · <a href="#cronologia">la tavola</a>`],
  ];
  return `<div class="h2 par-h2"><span class="seg">¶</span>Introduzione generale e appendici</div>
    <p class="sotto">Gli indici e la tavola cronologica collegati ai versetti; ${num(m.corr)} refusi degli indici hanno anche il riferimento corretto (dal registro dei dubbi del volume). <a href="#introduzione-generale">Introduzione generale</a>: ${num(A.testi.length)} testi, ${num(m.pcit)} citazioni bibliche, ${num(A.abbr.length)} abbreviazioni.</p>
    <div class="tessere tessere-par">${tessere.map(([x, l, s]) => `<div class="tessera"><b>${x}</b><span>${l}</span>${s ? `<small>${s}</small>` : ''}</div>`).join('')}</div>`;
}
function topDiz(stretti) {
  // the 20 verses most cited by the dictionary: every citation naming a passage that includes
  // the verse, or only those of at most STRETTA verses; ties in canonical order
  const A = stretti ? S.dizS : S.dizN, idx = [];
  for (let i = 0; i < S.n; i++) if (A[i]) idx.push(i);
  return idx.sort((a, b) => A[b] - A[a] || a - b).slice(0, 20);
}
function righeTopDiz(stretti) {
  const A = stretti ? S.dizS : S.dizN, top = topDiz(stretti);
  return top.map((i, k) => {
    const nv = dizDi(i).length, t = testoPiano(V.h[i]);
    return `<tr><td class="pos">${k + 1}</td><td class="rif"><a href="${hashVerso(i)}" data-r="${i}-${i}">${esc(rif(i))}</a></td><td class="cnt"><div><i style="width:${(5 * A[i] / A[top[0]]).toFixed(2)}rem"></i>${A[i]}</div><small>in ${nv} voci</small></td><td class="frase">${esc(t.slice(0, 120))}${t.length > 120 ? '…' : ''}</td></tr>`;
  }).join('');
}
function panoramicaDiz() {
  const m = Z.meta;
  let soli = 0;
  for (let i = 0; i < S.n; i++) if (S.dizS[i]) soli++;
  const tessere = [
    [num(m.piene), 'voci del Dizionario', `${num(m.rinvii)} rinvii · ${num(m.paragrafi)} paragrafi`],
    [num(m.citazioni), 'citazioni bibliche', `in ${num(m.libri)} libri`],
    [String(m.pct).replace('.', ',') + '%', 'citazioni riconosciute', `${num(m.stati[1])} in parte, ${num(m.stati[2])} irrisolte`],
    [num(m.versetti), 'versetti citati', `${num(soli)} da soli o in passi di al più ${STRETTA} versetti`],
  ];
  return `<div class="h2 diz-h2"><span class="seg">◊</span>Dizionario di Teologia Biblica</div>
    <p class="sotto">X. Léon-Dufour (a cura di), Marietti 1976: le citazioni bibliche delle voci, lette con la numerazione di questa Bibbia (i Salmi con quella ebraica, come la CEI). <a href="#dizionario">Tutte le voci</a></p>
    <div class="tessere tessere-diz">${tessere.map(([n, l, s]) => `<div class="tessera"><b>${n}</b><span>${l}</span>${s ? `<small>${s}</small>` : ''}</div>`).join('')}</div>
    <div class="h2">I 20 versetti più citati dal Dizionario</div>
    <div class="segmenti" id="dtop-scelta" role="group" aria-label="Quali citazioni contare"><button type="button" data-top="tutte" aria-pressed="true">Tutte le citazioni</button><button type="button" data-top="stretti" aria-pressed="false">Di al più ${STRETTA} versetti</button></div>
    <p class="sotto nota-barre">Quante citazioni indicano un passo che comprende il versetto: con tutte, i capitoli interi e i passi lunghi pesano (Is 53); con le sole citazioni brevi resta il versetto nominato da solo.</p>
    <table class="classifica diz-top" id="dtop"><tbody>${righeTopDiz(false)}</tbody></table>`;
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
    <tr><td><kbd>d</kbd></td><td>evidenzia invece i più citati dal Dizionario (e viceversa)</td></tr>
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
  premiFonte();
}
function premiFonte() {
  // the switch above the text: the source pressed while the heat is on, none when it is off
  const on = document.body.classList.contains('calore');
  $$('.fonte-calore button').forEach(b => b.setAttribute('aria-pressed', String(on && (b.dataset.fonte === 'diz') === !!S.caloreDiz)));
}
function fonteCalore(diz) {
  // what the heat shows: margin references of the BJ or citations of the dictionary
  S.caloreDiz = diz;
  document.body.classList.toggle('calore-diz', diz);
  $('#calore').title = diz ? 'Evidenzia i versetti più citati dal Dizionario' : 'Evidenzia i versetti più rimandati';
  memo.set('fonte', diz ? 'diz' : 'bj');
  premiFonte();
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
    if (r && /^gn\s?\d/i.test(q)) S.avviso = '«Gn» è la sigla CEI di Giona; Genesi è «Gen».';
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
    const fonte = e.target.closest('[data-fonte]');
    if (fonte) {
      // the switch above the text: a source turns the heat on, the pressed one turns it off
      const diz = fonte.dataset.fonte === 'diz';
      if (document.body.classList.contains('calore') && diz === !!S.caloreDiz) calore_(false);
      else { fonteCalore(diz); calore_(true); }
      return;
    }
    const nota = e.target.closest('[data-nota]');
    if (nota) S.notaChiave = +nota.dataset.nota;
    if (nota && nota.matches('.nota-ix') && nota.getAttribute('href') === location.hash && S.sel !== null && S.sel !== undefined) {
      e.preventDefault();             // the note of the verse already open: show it in the panel
      mostraPannello(S.sel);
      return;
    }
    const chiudi = e.target.closest('[data-chiudi]');
    if (chiudi) { chiudiPannello(true); return; }
    const anteprima = e.target.closest('[data-r], [data-x]');
    if (anteprima && anteprima.dataset.x !== undefined && !e.target.closest('#anteprima')) {
      mostraAnteprima(anteprima, puntatore === 'touch');
      return;
    }
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
    // a link to the address already shown (the section index of an entry clicked again after
    // scrolling) shows it again instead of doing nothing
    const stesso = e.target.closest('a[href^="#voce/"]');
    if (stesso && stesso.getAttribute('href') === location.hash && !e.defaultPrevented) {
      e.preventDefault();
      instrada();
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
    const el = e.target.closest('[data-r], [data-x]');
    if (!el || el.closest('#anteprima')) return;
    clearTimeout(tAnteprima);
    tAnteprima = setTimeout(() => mostraAnteprima(el, false), 120);
  });
  document.addEventListener('focusin', e => {
    const el = e.target.closest?.('a.cd.x');
    if (el) mostraAnteprima(el, false);
  });
  document.addEventListener('pointerout', e => {
    if (e.pointerType === 'touch') return;
    const el = e.target.closest('[data-r], [data-x]');
    if (!el || (e.relatedTarget && el.contains(e.relatedTarget))) return;
    clearTimeout(tAnteprima);
    tAnteprima = setTimeout(nascondiAnteprima, 150);
  });
  $('#anteprima').addEventListener('pointerover', () => clearTimeout(tAnteprima));
  $('#anteprima').addEventListener('pointerout', e => { if (e.pointerType !== 'touch') tAnteprima = setTimeout(nascondiAnteprima, 150); });
  // scrolling hides the preview, except the one of the element that has the keyboard focus
  const via = () => { if (!$('#anteprima').hidden && puntatore !== 'touch' && bersaglio !== document.activeElement) nascondiAnteprima(); };
  window.addEventListener('scroll', via, { passive: true });
  window.addEventListener('scroll', memoScorrimento, { passive: true });
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
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('a.cd.x')) {
      e.preventDefault();
      mostraAnteprima(e.target, false);
      return;
    }
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
      case 'd': fonteCalore(!S.caloreDiz); calore_(true); break;
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
  fonteCalore(memo.get('fonte') === 'diz');
  instrada();
  const t2 = performance.now();
  window.__esploratore = { dati: Math.round(t1 - T0), indici: Math.round(t2 - t1), pronto: Math.round(t2 - T0) };
  console.info('esploratore pronto in %d ms (dati %d ms)', t2 - T0, t1 - T0);
}
avvia();
