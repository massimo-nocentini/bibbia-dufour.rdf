"""The links between the parts of the graph, and the corrections in one model -> ontologia/build/integrazione.json.

usage: integrazione.py [-q]

Stage 2d of the verse ontology (session F2 of the review of 2026-10-31). Reads the four JSON
files of the stages before (bibbia.json, collegamenti.json, dufour.json, paratesto.json) and
the hand tables of this folder, all reviewed by hand (precision over recall):
  allineamenti.tsv      index of notes / pastoral themes <-> Dizionario entries, notes <-> themes,
                        and the pairs one index prints twice (SKOS mapping links, with method,
                        reviewer and the verses the two share, recomputed here)
  persone.tsv           the dynasty persons named by verses (by chapter and name), by index
                        sub-entries and references, by entries of the chronological table
  cronologia-libri.tsv  the chronology entries that date a book or a prophet (composizione,
                        ministero, evento); the entries with references also date the books they
                        cite (kind 'citato', computed)
  testimoni.tsv         the versions of the text (TM, LXX, Volgata, ...): the notes that name one,
                        the qualifiers of references that name one; the codices and papyri of the
                        abbreviations are found in the lists of witnesses of the notes
  calendario.tsv        the months and the annual feasts of the appendices, with their references
  misure.tsv            the measures and coins of the appendices, with values (QUDT units as data),
                        ratios and references; misprints by paratesto.CORREZIONI_PROSA
  carte.tsv             the ten maps (appendices and endpapers): page, image, period, books, passages
and gathers every correction table of the project into one list of interventions (`interventi`:
riferimenti.CORREZIONI, CORREZIONI_VERSO, AGGIUNTE, REFUSI, REFUSI_RIFERIMENTI, MISPRINT,
numerazioni.tsv, the rules of the sense of the sentence and the readings of stage 2,
paratesto.CORREZIONI_INDICI and CORREZIONI_PROSA, tsv.RIMANDI and PAGINE_ESTRANEE, dufour.CORREZIONI,
PARAGRAFI, FORME and its readings and conversions, the editorial notes of dinastie.tsv), each with its
table and row, rule, motivation, reason, targets and the page that is its evidence; and the numbering
schemes of numerazioni.tsv.

Checks (exit status 1 if any fails): every row of every table names known resources and is used; an
alignment by head word shares a verse or has the reviewer's reason; every verse given one by one in
persone.tsv names the person; every reference of the calendar, the measures and the maps resolves;
every correction table row has exactly one intervention and every corrected, read or converted link
has one; the interventions' ids are distinct.
"""
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from percorsi import TEX  # noqa: E402  (the LaTeX transcription)
sys.path.insert(0, os.path.join(TEX, 'progetti', 'appendici'))
import riferimenti as R  # noqa: E402
import paratesto as PT  # noqa: E402
import tsv as TSV  # noqa: E402
from estrai import dump  # noqa: E402

BUILD = os.path.join(C, 'ontologia', 'build')
OUT = os.path.join(BUILD, 'integrazione.json')
CTX = dict(book=None, chapter=None, margin=False)
REL = ('closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'exactMatch')
TIPI_DATAZIONE = ('composizione', 'ministero', 'evento', 'citato')
CODICE = re.compile(r'(?<![\w*])(?:[SABCDLWKEFGMNPQYZΓΔΘΛΠΣψא][ᵉᵖᵃ]?\*?|P\d{1,2}|0\d{2,3})(?![\w])')
LISTA = re.compile(r'(?<![\w])(?:[SABCDLWKEFGMNPQYZΓΔΘΛΠΣψא][ᵉᵖᵃ]?\*?|P\d{1,2}|0\d{2,3}|\d{2,4})'
                   r'(?:\s*(?:,|e)\s*(?:[SABCDLWKEFGMNPQYZΓΔΘΛΠΣψא][ᵉᵖᵃ]?\*?|P\d{1,2}|0\d{2,3}|\d{2,4}))+(?![\w])')
SEGNALE = re.compile(r'\b(?:con|hanno|ha|leggono|legge|omett\w+|aggiung\w+|var\.|mss|testimon\w+|ecc\.|'
                     r'e altri|attestat\w+|lezione)\b')
PAOLO = ('Rom', '1Cor', '2Cor', 'Gal', 'Eph', 'Phil', 'Col', '1Thess', '2Thess', '1Tim', '2Tim', 'Titus', 'Phlm', 'Heb')
VANGELI_ATTI = ('Matt', 'Mark', 'Luke', 'John', 'Acts')


def piega(s):
    """Lower case, no accents: the text the patterns of the tables read."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def tabella(nome):
    """(row number from 1, row) of a TSV of this folder: '#' comments, a header."""
    with open(os.path.join(HERE, nome), encoding='utf-8') as f:
        lines = [x.rstrip('\n') for x in f if x.strip() and not x.startswith('#')]
    rows = list(csv.DictReader(lines, delimiter='\t', quoting=csv.QUOTE_NONE))
    return [(k, {a: (b or '').strip() for a, b in r.items()}) for k, r in enumerate(rows, 1)]


def leggi_rif(testo, B, src, kind='table-cites', corr=()):
    """The references of a printed string with no current book, as typed links; a pair (printed,
    corrected) of `corr` is read in its corrected form (the text stays as printed)."""
    out = []
    for k, r in enumerate(R.scan_prose(testo, CTX), 1):
        fix = next((c for c in corr if r['raw'] == c[0] or r['raw'].endswith(' ' + c[0])), None)
        if fix:
            got, end = R.parse(fix[1], CTX, prose=True)
            if len(got) != 1 or end != len(fix[1]):
                raise ValueError('%s: %r not read' % (src, fix[1]))
            new = dict(got[0], raw=r['raw'], offset=r['offset'], cf=r.get('cf', False))
            R.resolve(new, B, CTX)
            r = new
        else:
            R.resolve(r, B, CTX)
        rec = R.record('%s#c%d' % (src, k), kind, src, None, 'cites', r)
        rec.update(cf=bool(r.get('cf')), offset=r['offset'])
        if fix:
            rec.update(corrected='prosa', why=fix[2], corrected_raw=fix[1])
        out.append(rec)
    return out


# ---------------------------------------------------------------- alignments (R2-12, R2-13, R2-10)

def versi_indici(P):
    """{'note.7': set of verses} of each index entry (its sub-entries too) and sub-entry."""
    out = defaultdict(set)
    for ix in P['indici']:
        for v in ix['voci']:
            for it in v['items']:
                l = it.get('link')
                if not l:
                    continue
                fix = l.get('correction')
                t = fix['targets'] if fix else (l['targets'] if l['status'] in ('resolved', 'partial') else [])
                out['%s.%d' % (ix['id'], v['n'])] |= set(t)
                if it['sv']:
                    out['%s.%d.%d' % (ix['id'], v['n'], it['sv'])] |= set(t)
    return out


def allineamenti(P, dz, errors):
    voci = {v['id'] for v in dz['voci']}
    vv = defaultdict(set)
    for c in dz['citations']:
        if c['status'] in ('resolved', 'partial'):
            vv[c['voce']] |= set(c['targets'])
    vi = versi_indici(P)
    entrate = {'%s.%d' % (ix['id'], v['n']) for ix in P['indici'] for v in ix['voci']}
    out, visti = [], set()
    for k, r in tabella('allineamenti.tsv'):
        a, b = r['da'], r['a']
        if a not in entrate:
            errors.append('allineamenti.tsv:%d: %s is not an index entry' % (k, a))
            continue
        if b.startswith('voce:'):
            if b[5:] not in voci:
                errors.append('allineamenti.tsv:%d: %s is not a dictionary entry' % (k, b))
                continue
            comuni = vi[a] & vv[b[5:]]
        elif b in entrate:
            comuni = vi[a] & vi[b]
        else:
            errors.append('allineamenti.tsv:%d: %s unknown' % (k, b))
            continue
        if r['relazione'] not in REL:
            errors.append('allineamenti.tsv:%d: relation %r' % (k, r['relazione']))
        if (a, b) in visti:
            errors.append('allineamenti.tsv:%d: %s %s twice' % (k, a, b))
        visti.add((a, b))
        if r['metodo'] == 'head' and not comuni and r['chi'] == 'R2':
            errors.append('allineamenti.tsv:%d: head-word match %s %s shares no verse and has no reason' % (k, a, b))
        out.append(dict(riga=k, da=a, a=b, relazione=r['relazione'], metodo=r['metodo'], chi=r['chi'],
                        nota=r['nota'], comuni_revisione=int(r['comuni']) if r['comuni'] else None,
                        comuni=sorted(comuni)))
    return out


# ---------------------------------------------------------------- persons (R2-14)

def persone(P, data, B, errors):
    pid = {x['id'] for x in P['dinastie']}
    by_ch = defaultdict(list)
    for v in data['verses']:
        by_ch[(v['book'], v['chapter'])].append(v)
    entrate = {}
    for ix in P['indici']:
        for v in ix['voci']:
            entrate['%s.%d' % (ix['id'], v['n'])] = v
            for s in v['sub']:
                entrate['%s.%d.%d' % (ix['id'], v['n'], s['k'])] = s
    cron = {v['n'] for v in P['cronologia']['voci']}
    versi, indice, cronologia = [], [], []
    for k, r in tabella('persone.tsv'):
        p = r['persona']
        if p not in pid:
            errors.append('persone.tsv:%d: unknown person %s' % (k, p))
            continue
        if r['tipo'] == 'versetti':
            pat = re.compile(r['nome'])
            scelti, fuori, uno = [], set(), []
            for d in r['dove'].split():
                meno = d.startswith('-')
                d = d.lstrip('-')
                parts = d.split('.')
                if len(parts) == 3 and d in B.verses:
                    (fuori.add(d) if meno else (scelti.append(B.verses[d]), uno.append(d)))
                elif len(parts) == 2 and (parts[0], int(parts[1])) in by_ch:
                    scelti += by_ch[(parts[0], int(parts[1]))]
                elif len(parts) == 1 and parts[0] in B.books:
                    scelti += [v for v in data['verses'] if v['book'] == parts[0]]
                else:
                    errors.append('persone.tsv:%d: %s is not a verse, chapter or book' % (k, d))
            ids = [v['id'] for v in scelti if v['id'] not in fuori and pat.search(piega(v['text']))]
            for d in uno:
                if d not in ids:
                    errors.append('persone.tsv:%d: %s does not name %s' % (k, d, r['nome']))
            if not ids:
                errors.append('persone.tsv:%d: no verse' % k)
            versi += [dict(persona=p, verso=x, riga=k) for x in dict.fromkeys(ids)]
        elif r['tipo'] == 'indice':
            d = r['dove']
            if '/' in d:
                e, raw = d.split('/', 1)
                ix, n = e.split('.')
                v = entrate.get(e)
                its = [it for it in (v or {}).get('items', []) if it['raw'] == raw and it.get('link')]
                if len(its) != 1:
                    errors.append('persone.tsv:%d: %s not one reference of the entry' % (k, d))
                    continue
                indice.append(dict(persona=p, citazione=its[0]['link']['id'], voce=e, riga=k))
            elif d in entrate and d.count('.') == 2:
                indice.append(dict(persona=p, voce=d, riga=k))
            else:
                errors.append('persone.tsv:%d: %s is not a sub-entry' % (k, d))
        elif r['tipo'] == 'cronologia':
            for n in r['dove'].split():
                if int(n) not in cron:
                    errors.append('persone.tsv:%d: no chronology entry %s' % (k, n))
                cronologia.append(dict(persona=p, voce=int(n), riga=k))
        else:
            errors.append('persone.tsv:%d: tipo %r' % (k, r['tipo']))
    dup = [x for x, n in Counter((x['persona'], x['verso']) for x in versi).items() if n > 1]
    if dup:
        errors.append('persone.tsv: verse rows twice %s' % dup[:3])
    return dict(versetti=versi, indice=indice, cronologia=cronologia)


# ---------------------------------------------------------------- chronology <-> books (R2-15)

def datazioni(P, data, errors):
    books = {b['osis'] for b in data['books']}
    cron = {v['n']: v for v in P['cronologia']['voci']}
    out = []
    for k, r in tabella('cronologia-libri.tsv'):
        n = int(r['voce'])
        libri = r['libri'].split()
        if n not in cron or r['tipo'] not in TIPI_DATAZIONE[:3] or any(b not in books for b in libri):
            errors.append('cronologia-libri.tsv:%d: %r' % (k, r))
            continue
        out.append(dict(id='%d-%d' % (n, k), voce=n, libri=libri, tipo=r['tipo'], riga=k, nota=r['nota']))
    bv = {v['id']: v['book'] for v in data['verses']}
    cit = defaultdict(list)
    for l in P['links']:
        if l['kind'] == 'chrono-cites' and l['status'] in ('resolved', 'partial'):
            n = int(l['source'].split('.', 1)[1])
            for t in l['targets']:
                if bv[t] not in cit[n]:
                    cit[n].append(bv[t])
    for n in sorted(cit):
        out.append(dict(id='%d-c' % n, voce=n, libri=cit[n], tipo='citato', riga=None, nota=None))
    return out


# ---------------------------------------------------------------- versions and codices (R2-16)

LIBRI_NT = {'Vangeli': ('Matt', 'Mark', 'Luke', 'John'), 'Matteo': ('Matt',), 'Marco': ('Mark',), 'Luca': ('Luke',),
            'Giovanni': ('John',), 'Atti': ('Acts',), 'Apocalisse': ('Rev',),
            'Lettere': PAOLO + ('Jas', '1Pet', '2Pet', '1John', '2John', '3John', 'Jude')}


def copertura(x):
    """The books a codex holds, from its row of the abbreviations («Vangeli», «Atti e Lettere»); None: any
    (the whole Bible, the NT, a papyrus)."""
    m = x['meaning']
    if x['kind'] == 'papiro' or re.search(r'\b(?:AT|NT)\b', m):
        return None
    out = set()
    for k, v in LIBRI_NT.items():
        if re.search(r'\b%s\b' % k, m):
            out |= set(v)
    return out or None


def testimoni(P, data, errors):
    abbr = {x['form']: x for x in P['abbreviazioni']}
    versioni = []
    for k, r in tabella('testimoni.tsv'):
        if r['abbreviazione'] and r['abbreviazione'] not in abbr:
            errors.append('testimoni.tsv:%d: no abbreviation %r' % (k, r['abbreviazione']))
        versioni.append(dict(id=r['id'], nome=r['nome'], riga=k, abbreviazione=abbr[r['abbreviazione']]['n']
                             if r['abbreviazione'] in abbr else None,
                             forme=re.compile(r'(?<![\w.])(?:%s)(?![\w])' % r['forme']),
                             qualificatori=[q for q in r['qualificatori'].split('|') if q]))
    # codex sigla -> manuscript id (paratesto/rdf: the Gregory-Aland number)
    sig, copre = {}, {}
    for x in P['abbreviazioni']:
        if x.get('gregory'):
            copre[x['gregory']] = copertura(x)
        if x['kind'].startswith(('codice-maiuscolo', 'codice-minuscolo', 'papiro')) and x.get('gregory'):
            for f in (x.get('letter') or x['gregory']).replace('(', ' ').replace(')', ' ').split():
                sig.setdefault(f, x['gregory'])
            sig.setdefault(x['gregory'], x['gregory'])
    sig.update({'א': '01', 'D': None})       # D: Dᵉ (05) in the Gospels and Acts, Dᵖ (06) in Paul
    bv = {v['id']: v['book'] for v in data['verses']}
    nv, nc = [], []
    for n in data['notes']:
        t = n['text']
        found = [v['id'] for v in versioni if v['forme'].search(t)]
        if found:
            nv.append([n['id'], found])
        libro = bv.get(n['anchor'])
        codici = []
        for m in LISTA.finditer(t):
            ctx = t[max(0, m.start() - 60):m.end() + 60]
            if not SEGNALE.search(ctx) or not CODICE.search(m.group(0)):
                continue
            for c in CODICE.findall(m.group(0)) + re.findall(r'(?<![\w])\d{2,4}(?![\w])', m.group(0)):
                c0 = c.rstrip('*').rstrip('ᵉᵖᵃ') if c not in sig else c
                if c0 == 'D' or c in ('Dᵉ', 'Dᵖ'):
                    g = '06' if libro in PAOLO else ('05' if libro in VANGELI_ATTI else None)
                elif c0 == 'E':
                    g = '08' if libro == 'Acts' else None
                else:
                    g = sig.get(c0)
                if g and g not in codici and (copre.get(g) is None or libro in copre[g]):
                    codici.append(g)
        if codici:
            nc.append([n['id'], codici])
    for v in versioni:
        del v['forme']
    return dict(versioni=versioni, note_versioni=nv, note_codici=nc)


# ---------------------------------------------------------------- calendar, measures, maps (R2-18)

def calendario(P, B, errors):
    mesi, feste, links = [], [], []
    for k, r in tabella('calendario.tsv'):
        src = '%s.%s' % (r['tipo'], r['id'])
        ls = leggi_rif(r['riferimenti'], B, src) if r['riferimenti'] else []
        links += ls
        x = dict(id=r['id'], nome=r['nome'], altri=[a for a in r['altri'].split('|') if a], mese=r['mese'],
                 giorno=r['giorno'] or None, pagina=int(r['pagina']), riga=k, anche=r['anche'].split(),
                 parole=r['parole'].split(), links=[l['id'] for l in ls], riferimenti=r['riferimenti'])
        if r['tipo'] == 'mese':
            x.update(solare=r['solare'], macedone=r['macedone'])
            mesi.append(x)
        else:
            feste.append(x)
    nomi = {m['id'] for m in mesi}
    for f in feste:
        if f['mese'] not in nomi:
            errors.append('calendario.tsv: %s: month %s' % (f['id'], f['mese']))
    return mesi, feste, links


def frazione(s):
    m = re.fullmatch(r'(\d+)(?:,(\d+))?(?:/(\d+))?', s or '')
    if not m:
        return None
    v = float(m.group(1) + ('.' + m.group(2) if m.group(2) else ''))
    return v / int(m.group(3)) if m.group(3) else v


def misure(B, errors):
    prosa = [(raw, cei, why) for t, raw, cei, why in PT.CORREZIONI_PROSA if t == 'misure']
    out, links, usate = [], [], Counter()
    for k, r in tabella('misure.tsv'):
        src = 'misura.%s' % r['id']
        ls = leggi_rif(r['riferimenti'], B, src, corr=prosa) if r['riferimenti'] else []
        for l in ls:
            if l.get('corrected') == 'prosa':
                usate[next(c[0] for c in prosa if l['raw'].endswith(c[0]))] += 1
        links += ls
        out.append(dict(id=r['id'], tipo=r['tipo'], nome=r['nome'], originale=r['originale'] or None,
                        lingua=r['lingua'] or None, valore=r['valore'] or None,
                        decimale=frazione(r['valore']), unita=r['unita'] or None, rapporto=r['rapporto'] or None,
                        rapporto_decimale=frazione(r['rapporto']), base=r['base'] or None, equivale=r['equivale'] or None,
                        pagina=int(r['pagina']), riga=k, parole=r['parole'].split(), nota=r['nota'] or None,
                        links=[l['id'] for l in ls], riferimenti=r['riferimenti']))
    ids = {x['id'] for x in out}
    for x in out:
        for kk in ('base', 'equivale'):
            if x[kk] and x[kk] not in ids:
                errors.append('misure.tsv: %s: %s %s unknown' % (x['id'], kk, x[kk]))
        if x['unita'] and not re.fullmatch(r'unit:(CentiM|M|KiloM|L|GM|KiloGM)', x['unita']):
            errors.append('misure.tsv: %s: unit %s' % (x['id'], x['unita']))
    for raw, cei, why in prosa:
        if usate[raw] != 1:
            errors.append('CORREZIONI_PROSA %r used %d times' % (raw, usate[raw]))
    return out, links


def carte(B, data, errors):
    books = {b['osis'] for b in data['books']}
    out, links = [], []
    for k, r in tabella('carte.tsv'):
        src = 'carta.%s' % r['id']
        ls = leggi_rif(r['passi'], B, src) if r['passi'] else []
        links += ls
        if not os.path.exists(os.path.join(TEX, r['immagine'])) or any(b not in books for b in r['libri'].split()):
            errors.append('carte.tsv:%d: %r' % (k, r))
        out.append(dict(id=r['id'], titolo=r['titolo'], sottotitolo=r['sottotitolo'] or None, parte=r['parte'],
                        pdf=int(r['pdf']), immagine=r['immagine'], periodo=r['periodo'] or None,
                        libri=r['libri'].split(), riga=k, links=[l['id'] for l in ls]))
    return out, links


def parole(data, oggetti, chiave):
    """{object id: [verse ids]} of the verses whose text holds one of its words (whole words)."""
    pats = [(x['id'], re.compile(r'(?<![\w])(?:%s)(?![\w])' % '|'.join(map(re.escape, x['parole']))))
            for x in oggetti if x['parole']]
    out = defaultdict(list)
    for v in data['verses']:
        t = piega(v['text'])
        for oid, p in pats:
            if p.search(t):
                out[oid].append(v['id'])
    return {k: out[k] for k, _ in pats}


# ---------------------------------------------------------------- the corrections (R2-20) and numberings (R2-21)

def sicuro(x):
    return re.sub(r'[^A-Za-z0-9_.\-]', '_', x)


def pagina_di(l, B, notes, P):
    """The page that is the evidence of a link: (kind, n)."""
    sv = l.get('source_verse')
    if l['kind'] == 'note-cites' or l['kind'] == 'note-label':
        n = notes.get(l['source'])
        if n and n.get('page'):
            return ['pagina', n['page']]
    if sv and sv in B.verses and B.verses[sv].get('page'):
        return ['pagina', B.verses[sv]['page']]
    return None


def interventi(data, coll, dz, P, I, B, errors):
    notes = {n['id']: n for n in data['notes']}
    intros = {'%s.%d' % (x['id'], p['n']): p for x in data['intros'] for p in x['paragraphs']}
    out = []

    def add(tab, riga, regola, motivazione, bersagli, motivo, lingua, pagina=None, stampato=None, corretto=None,
            fonte=None):
        out.append(dict(id='%s/%s' % (tab, sicuro(str(riga))), tabella=tab, riga=riga, regola=regola,
                        motivazione=motivazione, bersagli=bersagli, motivo=motivo, lingua=lingua, pagina=pagina,
                        stampato=stampato, corretto=corretto, fonte=fonte))

    # the Bible: the table rows, then the rules and readings of stage 2
    corr = list(enumerate(R.CORREZIONI, 1))
    usate = Counter()
    numer = [r for r in R.numerazioni()]
    nrow = {(r['fonte'], r['stampato'], r['n']): k for k, r in enumerate(numer, 1)}
    ref_rows = {(src, raw): k for k, (src, raw, cei, why) in enumerate(R.REFUSI_RIFERIMENTI, 1)}
    seen = Counter()
    fatti = set()
    for l in coll['links']:
        if not (l.get('corrected') or l.get('inferred')):
            continue
        pg = pagina_di(l, B, notes, P)
        if l['kind'] == 'intro-cites' and l['source'] in intros:
            pg = ['pagina', intros[l['source']].get('page')] if intros[l['source']].get('page') else pg
        tgt = [['link', l['id']]]
        rule, why = l.get('corrected'), l.get('why')
        if not rule:
            add('riferimenti.lettura', l['id'], 'lettura', 'interpretando', tgt, l['inferred'], 'en', pg, l['raw'])
            continue
        if rule == 'manuale':
            k = next((k for k, row in corr if row[0] == l['source'] and row[1] == l['raw'] and not usate[k]), None)
            if k is None:
                errors.append('%s: manual correction with no row of CORREZIONI' % l['id'])
                continue
            usate[k] += 1
            row = corr[k - 1][1]
            add('riferimenti.CORREZIONI', k, 'manuale', 'interpretando', tgt, row[5], 'en', pg, l['raw'],
                fonte='tools/ontologia/riferimenti.py')
            if (row[0], row[1]) in R.CORREZIONI_VERSO:
                add('riferimenti.CORREZIONI_VERSO', 1, 'manuale', 'editing', tgt,
                    'a misprinted range read as the verse %s' % R.CORREZIONI_VERSO[(row[0], row[1])], 'en', pg,
                    l['raw'], R.CORREZIONI_VERSO[(row[0], row[1])], 'tools/ontologia/riferimenti.py')
        elif rule == 'aggiunta':
            k = next((k for k, row in enumerate(R.AGGIUNTE, 1) if row[0] == l['source']
                      and ('agg', k) not in fatti), None)     # the rows of a note in the order of its text
            if k is None:
                errors.append('%s: added link with no row of AGGIUNTE' % l['id'])
                continue
            fatti.add(('agg', k))
            add('riferimenti.AGGIUNTE', k, 'aggiunta', 'linking', tgt, why, 'en', pg, l['raw'],
                fonte='tools/ontologia/riferimenti.py')
        elif rule == 'numerazione' or (rule == 'refuso' and (l['source'], l['raw']) in ref_rows):
            if rule == 'refuso':
                add('riferimenti.REFUSI_RIFERIMENTI', ref_rows[(l['source'], l['raw'])], 'refuso', 'editing', tgt,
                    why, 'en', pg, l['raw'], R.REFUSI_RIFERIMENTI[ref_rows[(l['source'], l['raw'])] - 1][2],
                    'tools/ontologia/riferimenti.py')
                continue
            seen[(l['source'], l['raw'])] += 1
            k = nrow.get((l['source'], l['raw'], '0')) or nrow.get((l['source'], l['raw'], str(seen[(l['source'], l['raw'])])))
            if k is None:
                errors.append('%s: numbering with no row of numerazioni.tsv' % l['id'])
                continue
            r = numer[k - 1]
            add('numerazioni.tsv', k, 'numerazione', 'interpretando', tgt, why, 'en', pg, l['raw'],
                None if r['cei'] in ('=', '—') else r['cei'], 'tools/ontologia/numerazioni.tsv')
        elif rule == 'refuso':
            sig = next((s for s in R.MISPRINT if re.match(re.escape(s) + r'\s?\d', l['raw'])), None)
            key = next((s for s, (fix, w) in R.REFUSI.items() if w == why), None)
            if sig:
                add('riferimenti.MISPRINT', '%s-%s' % (sig, l['id']), 'refuso', 'editing', tgt, why, 'en', pg, l['raw'],
                    R.MISPRINT[sig] + l['raw'][len(sig):], 'tools/ontologia/riferimenti.py')
            elif key:
                add('riferimenti.REFUSI', '%d-%s' % (list(R.REFUSI).index(key) + 1, l['id']), 'refuso', 'editing', tgt,
                    why, 'en', pg, key, R.REFUSI[key][0], 'tools/ontologia/riferimenti.py')
            else:
                errors.append('%s: misprint with no table' % l['id'])
        else:
            add('riferimenti.regola-' + rule, l['id'], rule, 'interpretando', tgt, why, 'en', pg, l['raw'],
                fonte='tools/ontologia/riferimenti.py')
    for k, row in corr:
        if not usate[k]:
            errors.append('riferimenti.CORREZIONI row %d (%s %s) has no corrected link' % (k, row[0], row[1]))
    # numbering rows of the dictionary scheme: what each maps (the converted citations name them in
    # their reason); rows of other schemes not used by a link (none: riferimenti.py fails on one)
    used_n = {x['riga'] for x in out if x['tabella'] == 'numerazioni.tsv'}
    for k, r in enumerate(numer, 1):
        if k in used_n:
            continue
        if r['schema'] != 'dizionario':
            errors.append('numerazioni.tsv row %d: no link' % k)
            continue
        m = re.fullmatch(r'(\d+),(\d+)(?:–(\d+))?', r['cei'])
        a, z = 'Sir.%s.%s' % (m.group(1), m.group(2)), 'Sir.%s.%s' % (m.group(1), m.group(3) or m.group(2))
        add('numerazioni.tsv', k, 'numerazione', 'interpretando', [['passaggio', [a, z]]],
            '%s; %s' % (R.SCHEMI[r['schema']], r['motivo'] or 'Sir %s (dictionary) = Sir %s (CEI)' % (r['stampato'], r['cei'])),
            'en', None, 'Sir %s' % r['stampato'], 'Sir %s' % r['cei'], 'tools/ontologia/numerazioni.tsv')
    # the front matter and the appendices
    ilinks = {}
    for ix in P['indici']:
        for v in ix['voci']:
            for it in v['items']:
                if it.get('link'):
                    ilinks[(ix['id'], v['lemma'], it['raw'])] = (it['link'], it['page'])
    for k, (ix, lemma, raw, fix, why) in enumerate(PT.CORREZIONI_INDICI, 1):
        l, page = ilinks.get((ix, lemma, raw), (None, None))
        if not l or not l.get('correction'):
            errors.append('CORREZIONI_INDICI row %d: no link' % k)
            continue
        add('paratesto.CORREZIONI_INDICI', k, 'indice', 'editing', [['link', l['id']]], why, 'it', ['pagapp', page],
            raw, fix, 'tools/ontologia/paratesto.py')
    for k, (t, raw, fix, why) in enumerate(PT.CORREZIONI_PROSA, 1):
        ls = [l for l in I['links'] if l.get('corrected') == 'prosa' and l['raw'].endswith(raw)]
        m = re.search(r'p\. (\d+)', why)
        add('paratesto.CORREZIONI_PROSA', k, 'prosa', 'editing', [['link', l['id']] for l in ls], why, 'it',
            ['pagapp', int(m.group(1))] if m else None, raw, fix, 'tools/ontologia/paratesto.py')
        if len(ls) != 1:
            errors.append('CORREZIONI_PROSA row %d: %d links' % (k, len(ls)))
    lemma = {(ix['id'], PT_chiave(v['lemma'])): (ix['id'], v) for ix in P['indici'] for v in ix['voci']}
    for k, (form, (head, why)) in enumerate(TSV.RIMANDI.items(), 1):
        hits = [(ix['id'], v, it) for ix in P['indici'] for v in ix['voci'] for it in v['items']
                if it['kind'] == 'vedi' and it['raw'] == form]
        to = lemma.get(('note', PT_chiave(head))) or lemma.get(('temi', PT_chiave(head)))
        if len(hits) != 1 or not to:
            errors.append('tsv.RIMANDI row %d (%s): %d items' % (k, form, len(hits)))
            continue
        ixid, v, it = hits[0]
        key = '%s.%d%s' % (ixid, v['n'], '.%d' % it['sv'] if it['sv'] else '')
        add('tsv.RIMANDI', k, 'rimando', 'linking', [['indice', key]], why, 'en', ['pagapp', it['page']],
            'v. ' + form, 'v. ' + head, 'progetti/appendici/tsv.py')
    for k, ((head, page), why) in enumerate(TSV.PAGINE_ESTRANEE.items(), 1):
        hits = [(ix['id'], v, it) for ix in P['indici'] for v in ix['voci'] for it in v['items']
                if it['kind'] == 'pagina' and page in it['raw'] and v['lemma'].startswith(head)]
        if not hits:
            errors.append('tsv.PAGINE_ESTRANEE row %d: no item' % k)
            continue
        ixid, v, it = hits[0]
        key = '%s.%d%s' % (ixid, v['n'], '.%d' % it['sv'] if it['sv'] else '')
        add('tsv.PAGINE_ESTRANEE', k, 'pagina-estranea', 'describing', [['indice', key]], why, 'en',
            ['pagapp', it['page']], 'p. ' + page, None, 'progetti/appendici/tsv.py')
    for l in P['links'] + [it['link'] for ix in P['indici'] for v in ix['voci'] for it in v['items'] if it.get('link')]:
        if l.get('inferred') and not l.get('correction'):      # a reading of the front matter, an index, the chronology
            add('paratesto.lettura', l['id'], 'lettura', 'interpretando', [['link', l['id']]], l['inferred'], 'en',
                None, l['raw'], fonte='tools/ontologia/paratesto.py')
    for x in P['dinastie']:
        if x['note']:
            add('dinastie.tsv', x['id'], 'nota-editoriale', 'describing', [['dinastia', x['id']]], x['note'], 'it',
                ['pagapp', 24], fonte='progetti/appendici/dinastie.tsv')
    # the dictionary
    import dufour as DU
    cits = {c['id']: c for c in dz['citations']}
    for k, (cid, (raw, fields, why)) in enumerate(DU.CORREZIONI.items(), 1):
        if cid not in cits:
            errors.append('dufour.CORREZIONI row %d: no citation %s' % (k, cid))
            continue
        add('dufour.CORREZIONI', k, 'manuale', 'editing', [['dzcit', cid]], why, 'en', None, raw, None,
            'tools/ontologia/dufour.py')
    per_par = defaultdict(list)
    for c in dz['citations']:
        per_par[c.get('para')].append(c)
    paras = {p['id'] for v in dz['voci'] for p in v.get('paragraphs', [])}
    for k, (pid, (sig, why)) in enumerate(DU.PARAGRAFI.items(), 1):
        if pid not in paras:
            errors.append('dufour.PARAGRAFI row %d: no paragraph %s' % (k, pid))
            continue
        add('dufour.PARAGRAFI', k, 'paragrafo', 'interpretando', [['dzpar', pid]], why, 'en', None, None, sig,
            'tools/ontologia/dufour.py')
    for k, (form, voce) in enumerate(DU.FORME.items(), 1):
        ls = [n for n, l in enumerate(dz['links']) if l.get('form') == form and l['target'] == voce]
        if not ls:
            errors.append('dufour.FORME row %d: no link' % k)
            continue
        add('dufour.FORME', k, 'forma', 'editing', [['dzlink', n] for n in ls],
            'link printed «%s», read as the entry %s' % (form, voce), 'en', None, form, voce, 'tools/ontologia/dufour.py')
    done = {b[1] for x in out if x['tabella'] == 'dufour.CORREZIONI' for b in x['bersagli']}
    for c in dz['citations']:
        if c.get('inferred') and c['id'] not in done:
            add('dufour.lettura', c['id'], 'lettura', 'interpretando', [['dzcit', c['id']]], c['inferred'], 'en')
        if c.get('conversion') and c['id'] not in done:
            add('dufour.conversione', c['id'], 'conversione', 'interpretando', [['dzcit', c['id']]], c['conversion'],
                'en')
    dup = [x for x, n in Counter(x['id'] for x in out).items() if n > 1]
    if dup:
        errors.append('interventions with the same id: %s' % dup[:5])
    for x in out:
        if not x['bersagli']:
            errors.append('%s: no target' % x['id'])
    return out


def PT_chiave(s):
    return TSV.chiave(s)


def schemi():
    """The numbering schemes: the CEI's (the graph's) and those of numerazioni.tsv."""
    n = Counter(r['schema'] for r in R.numerazioni())
    out = [dict(id='cei', nome='CEI 2008 numbering (the verses of this graph)', righe=0)]
    out += [dict(id=k, nome=v, righe=n[k]) for k, v in R.SCHEMI.items()]
    return out


# ---------------------------------------------------------------- main

def main(a):
    quiet = '-q' in a
    data = json.load(open(os.path.join(BUILD, 'bibbia.json'), encoding='utf-8'))
    coll = json.load(open(os.path.join(BUILD, 'collegamenti.json'), encoding='utf-8'))
    dz = json.load(open(os.path.join(BUILD, 'dufour.json'), encoding='utf-8'))
    P = json.load(open(os.path.join(BUILD, 'paratesto.json'), encoding='utf-8'))
    B = R.Bibbia(data)
    errors = []
    I = dict(allineamenti=allineamenti(P, dz, errors), persone=persone(P, data, B, errors),
             datazioni=datazioni(P, data, errors), testimoni=testimoni(P, data, errors))
    mesi, feste, l1 = calendario(P, B, errors)
    mis, l2 = misure(B, errors)
    car, l3 = carte(B, data, errors)
    I['links'] = l1 + l2 + l3
    for l in I['links']:
        if l['status'] not in ('resolved', 'partial'):
            errors.append('%s: %r %s (%s)' % (l['id'], l['raw'], l['status'], l['reason']))
    I.update(mesi=mesi, feste=feste, misure=mis, carte=car,
             mesi_versetti=parole(data, mesi, 'id'), misure_versetti=parole(data, mis, 'id'))
    I['interventi'] = interventi(data, coll, dz, P, I, B, errors)
    I['schemi'] = schemi()
    s = dict(allineamenti=dict(Counter('%s %s' % (x['relazione'], 'voce' if x['a'].startswith('voce:') else 'indice')
                                       for x in I['allineamenti'])),
             persone=dict(versetti=len(I['persone']['versetti']), indice=len(I['persone']['indice']),
                          cronologia=len(I['persone']['cronologia'])),
             datazioni=dict(Counter(x['tipo'] for x in I['datazioni'])),
             note_versioni=len(I['testimoni']['note_versioni']), note_codici=len(I['testimoni']['note_codici']),
             menzioni_codici=sum(len(x[1]) for x in I['testimoni']['note_codici']),
             mesi=len(mesi), feste=len(feste), misure=len(mis), carte=len(car), citazioni=len(I['links']),
             versetti_misure=sum(len(x) for x in I['misure_versetti'].values()),
             versetti_mesi=sum(len(x) for x in I['mesi_versetti'].values()),
             interventi=dict(Counter(x['tabella'] for x in I['interventi'])))
    I['meta'] = dict(generated_by='tools/ontologia/integrazione.py', summary=s)
    dump(I, OUT)
    if not quiet:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    print('integrazione: %d alignments, %d person links (verses %d), %d datings, %d notes naming a version, %d a codex '
          '(%d mentions), %d months, %d feasts, %d measures, %d maps, %d references, %d interventions' % (
              len(I['allineamenti']), sum(s['persone'].values()), s['persone']['versetti'], len(I['datazioni']),
              s['note_versioni'], s['note_codici'], s['menzioni_codici'], len(mesi), len(feste), len(mis), len(car),
              len(I['links']), len(I['interventi'])))
    for e in errors[:40]:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errors else '%d errors' % len(errors), os.path.relpath(OUT, C)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
