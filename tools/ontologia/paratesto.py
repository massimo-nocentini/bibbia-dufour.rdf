"""The front matter and the appendices of the BJ -> ontologia/build/paratesto.json.

usage: paratesto.py [-q]

Stage 2c of the verse ontology. Reads the two volumes that hold what comes before and
after the books (never written here):
  progetti/introduzione-generale/   the editions and the title page, the Presentazione
                                    (G. Ravasi) and the three prefaces (P. Garuti, A. Filippi,
                                    T. Verdon), the division of the Hebrew and of the Greek
                                    Bible, the abbreviations (abbreviazioni.tsv: book sigla,
                                    other abbreviations, signs, codices and papyri), the
                                    Avvertenze (with the Bible references of the woodcuts)
  progetti/appendici/               the Tavola cronologica, the Dinastie Asmonea e Erodiana
                                    (dinastie.tsv), the Indice alfabetico delle note più
                                    importanti and the Indice dei temi biblici d'interesse
                                    pastorale
and ontologia/build/bibbia.json (stage 1). The three tables of the appendices are made by
progetti/appendici/tsv.py, run here with its output redirected to ontologia/build/ (its
TSV files in the volume are compared, never written): its references are resolved by
riferimenti.py and kept as typed links ("index-cites", "chrono-cites"), each with its
verses and, in the index of the notes, the BJ notes at that verse (column `nota` of
tsv.py: nota = a note is called or starts there, copre = a note's label covers it,
capitolo = a note on the whole chapter, rimandi = margin references only, nessuna).
The references of the front-matter texts are read by riferimenti.scan_prose (no current
book), like those of an introduction ("front-cites").

Misprints of the indices stay as printed; where the checklist of the volume states the
corrected reference and its evidence (CORREZIONI_INDICI) the link also gets the corrected
target ('correction'), and the shortcuts of the entry use it.

Dates of the chronology: each entry keeps the date as printed ('date', from its start
"165:", "Nov. 164:", "Fra il 34 e il 45:", or the one span in parentheses "(51–30)") and,
when unambiguous, a year range (start, end; negative = a.C., no year 0). Sections I-VIII are
before Christ; in section IX the era changes at the first row whose entry starts with a
"d.C." date (row 122: "Dall’1/2 al 4 d.C."); an explicit "a.C." / "d.C." always wins.

Checks (exit status 1 if any fails): the regenerated tables equal the TSV files of the
volume (a difference is reported: the volume's files are stale); every reference has a
link, every target is a verse id, every note id exists; every row of CORREZIONI_INDICI is
used once and its corrected reference resolves; every "v." target is an entry; the Hebrew
canon lists the 39 books of the Hebrew text once each and the Greek list every Old
Testament book of this Bible; every book siglum of the abbreviations is a book of the
canon (canone.py); every person of the dynasties has known parents and spouses, spouse
links both ways; every citation's offsets point at its raw text.
"""
import csv
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402
from estrai import dump, inline  # noqa: E402

BUILD = os.path.join(C, 'ontologia', 'build')
IN = os.path.join(BUILD, 'bibbia.json')
OUT = os.path.join(BUILD, 'paratesto.json')
IG = os.path.join(C, 'progetti', 'introduzione-generale')
AP = os.path.join(C, 'progetti', 'appendici')
PDF_PRELIMINARI = 5          # p. v = PDF page 10
PDF_APPENDICI = 3001         # p. 3 of the appendices = PDF page 3004
CTX = dict(book=None, chapter=None, margin=False)

# ---------------------------------------------------------------- the front matter

ROMANI = dict(i=1, v=5, x=10, l=50)


def romano(s):
    n, prev = 0, 0
    for ch in reversed(s.lower()):
        v = ROMANI[ch]
        n, prev = (n - v, prev) if v < prev else (n + v, v)
    return n


# the texts of the front matter, in print order: id, file, kind, author (person id, given name,
# family name; None for the unsigned texts)
TESTI = [
    ('presentazione', 'presentazione', 'presentazione', ('gianfranco-ravasi', 'Gianfranco', 'Ravasi')),
    ('prefazione-garuti', 'prefazione-garuti', 'prefazione', ('paolo-garuti', 'Paolo', 'Garuti')),
    ('prefazione-filippi', 'prefazione-filippi', 'prefazione', ('alfio-filippi', 'Alfio', 'Filippi')),
    ('prefazione-verdon', 'prefazione-verdon', 'prefazione', ('timothy-verdon', 'Timothy', 'Verdon')),
    ('divisione-ebraica', 'divisione-ebraica', 'canone', None),
    ('divisione-greca', 'divisione-greca', 'canone', None),
    ('avvertenze', 'avvertenze', 'avvertenze', None),
]
SC_A, SC_Z = '\ue100', '\ue101'          # small caps, kept through estrai.inline


def latex_testo(t):
    """The LaTeX of a front-matter paragraph, with the macros estrai.inline does not know."""
    t = t.replace('\\ldots', '…').replace('\\maltese', '✠').replace('{[}', '[').replace('{]}', ']')
    t = re.sub(r'\\mref\{[^{}]*\}', '', t)                 # the signs printed in the margin (Avvertenze)
    t = re.sub(r'\\neretto\{', r'\\textbf{', t)
    t = re.sub(r'\\titolettoriferimenti\{', r'\\titoletto{', t)
    t = re.sub(r'\\textsc\{([^{}]*)\}', lambda m: SC_A + m.group(1) + SC_Z, t)
    t = re.sub(r'\\(?:medskip|bigskip|smallskip|noindent|hfill|par)\b\s*', ' ', t)
    t = t.replace('\\ ', ' ').replace('~', ' ')
    return t


def a_testo(t, html):
    s = inline(latex_testo(t), html)
    if html:
        return s.replace(SC_A, '<span class="sc">').replace(SC_Z, '</span>')
    return s.replace(SC_A, '').replace(SC_Z, '')


def blocchi(t, page):
    """Paragraphs of a text: [(page, LaTeX)], the page where each one starts."""
    out = []
    for block in re.split(r'\n\s*\n', t):
        block = block.strip()
        if not block or not re.sub(r'\\(?:medskip|bigskip|noindent|pagina\{[ivxl]+\}%?)', '', block).strip():
            pages = re.findall(r'\\pagina\{([ivxl]+)\}', block)
            page = pages[-1] if pages else page
            continue
        pages = re.findall(r'\\pagina\{([ivxl]+)\}', block)
        start = pages[0] if block.startswith('\\pagina') else page
        page = pages[-1] if pages else page
        out.append((start, re.sub(r'\\pagina\{[ivxl]+\}%?', '', block)))
    return out, page


def group(t, i):
    """The braced group at t[i] == '{': (content, index after it)."""
    depth, j = 0, i
    while j < len(t):
        c = t[j]
        if c == '\\':
            j += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return t[i + 1:j], j + 1
        j += 1
    raise ValueError('unbalanced group at %d' % i)


def leggi(path):
    return re.sub(r'(?<!\\)%.*', '', open(path, encoding='utf-8').read())


def testo(tid, fname, kind, autore, B, errors):
    t = leggi(os.path.join(IG, 'introduzione-generale', fname + '.tex'))
    m = re.search(r'\\testo(?:\[([^\]]*)\])?(?:\[([^\]]*)\])?\{([^{}]*)\}', t)
    sottotitolo, titolo = m.group(1) or None, m.group(3)
    page = re.search(r'\\pagina\{([ivxl]+)\}', t).group(1)
    t = t[m.end():]
    firma = qualifica = None
    ma = re.search(r'\\begin\{autore\}(.*?)\\end\{autore\}', t, re.S)
    if ma:
        f, k = group(ma.group(1), ma.group(1).index('\\firma') + len('\\firma'))
        firma = a_testo(f, False)
        qualifica = [x for x in a_testo(ma.group(1)[k:], False).split('\n') if x.strip()]
        t = t[:ma.start()] + t[ma.end():]
    corsivo = '\\begin{corsivo}' in t
    t = re.sub(r'\\(?:begin|end)\{corsivo\}', '', t)
    if kind == 'canone':                        # the lists are the canon (below), not prose
        t = re.sub(r'\\begin\{minipage\}.*?\\end\{minipage\}', '\n\n', t, flags=re.S)
    paras = []
    bl, _ = blocchi(t, page)
    for n, (pg, block) in enumerate(bl, 1):
        tit = None
        mt = re.match(r'\\(?:titoletto|titolettoriferimenti)\{', block)
        if mt:
            tit = a_testo(group(block, mt.end() - 1)[0], False).strip()
        txt, htm = a_testo(block, False), a_testo(block, True)
        if not txt:
            continue
        paras.append(dict(n=len(paras) + 1, page=pg, titoletto=tit, text=txt, html=htm))
    if '\\' in ''.join(p['text'] for p in paras):
        errors.append('%s: a macro left in the text' % tid)
    return dict(id=tid, kind=kind, title=a_testo(titolo, False), subtitle=sottotitolo and a_testo(sottotitolo, False),
                page=page, author=autore and dict(id=autore[0], given=autore[1], family=autore[2]),
                signature=firma, qualifica=qualifica, italic=corsivo, paragraphs=paras)


def fine_html(hmap, html, end):
    """The HTML offset right after the character before plain offset end (before a closing tag:
    a reference printed in italics, "<em>Zc 9–14</em>", ends inside the <em>)."""
    if not hmap or end == 0:
        return hmap[end] if hmap else None
    i = hmap[end - 1]
    m = re.match(r'&(?:amp|lt|gt|quot);', html[i:])
    return i + (len(m.group(0)) if m else 1)


def citazioni_testo(x, B):
    """The Bible references of a front-matter text, as typed links (front-cites)."""
    links = []
    for p in x['paragraphs']:
        src = '%s.%d' % (x['id'], p['n'])
        hmap = R.html_offsets(p['text'], p['html'])
        for k, r in enumerate(R.scan_prose(p['text'], CTX), 1):
            R.resolve(r, B, CTX)
            rec = R.record('%s#c%d' % (src, k), 'front-cites', src, None, 'cites', r)
            rec.update(html_offset=hmap[r['offset']] if hmap else None,
                       html_end=fine_html(hmap, p['html'], r['offset'] + len(r['raw'])), paragraph=p['n'])
            links.append(rec)
    return links


# the woodcuts at the opening of each book: "Genesi (1,27); Esodo (2,2–3); ... 1 Samuele (9,27–10,1)"
XILO = re.compile(r'((?:[123] )?[A-ZÀ-Ý][a-zàèéìòù]+(?: dei Cantici)?) \(([^()]*)\)')
XILO_NOMI = dict(R.LIBRI_NOMI, **{'Qoèlet': 'Qo', 'Cantico dei Cantici': 'Ct', 'Atti': 'At', 'Gàlati': 'Gal',
                                  'Timòteo': 'Tm', 'Tito': 'Tt', 'Pietro': 'Pt', 'Apocalisse': 'Ap',
                                  'Samuele': 'Sam', 'Re': 'Re', 'Cronache': 'Cr', 'Maccabei': 'Mac',
                                  'Corinzi': 'Cor', 'Tessalonicesi': 'Ts', 'Giuda': 'Gd'})


def xilografie(avvertenze, B, errors):
    """One record per book: the passages its opening woodcut illustrates (Avvertenze)."""
    out = []
    pars = [p for p in avvertenze['paragraphs'] if p['titoletto'] in ('Antico Testamento', 'Nuovo Testamento')]
    for p in pars:
        body = p['text'][len(p['titoletto']):].strip()
        for m in XILO.finditer(body):
            name = m.group(1)
            num = re.match(r'([123]) (.+)', name)
            sig = (num.group(1) + XILO_NOMI[num.group(2)]) if num else XILO_NOMI.get(name)
            if name == 'Giovanni' and num is None:
                sig = 'Gv'
            if sig is None or sig not in R.SIGLA:
                errors.append('woodcuts: unknown book %r' % name)
                continue
            osis = R.SIGLA[sig][0] if sig != 'Est' else 'EsthGr'      # the Greek Esther opens the book
            ctx = dict(book=osis, chapter=None, margin=False)
            refs = []
            spec = re.sub(r',\s+(?=\d)', ',', m.group(2))      # "Salmi (51, 3–4)"
            for r in R.scan_prose(spec if ',' in spec else 'v ' + spec, dict(ctx, chapter=1)):
                R.resolve(r, B, dict(ctx, chapter=1))
                refs.append(dict(raw=r['raw'], status=r['status'], targets=r['targets'], ranges=r['ranges'],
                                 reason=r['reason']))
            if not refs or any(r['status'] != 'resolved' for r in refs):
                errors.append('woodcuts: %s (%s) not resolved' % (name, m.group(2)))
            out.append(dict(book=osis, name=name, raw=m.group(2), testament=p['titoletto'], refs=refs))
    return out


def edizione(errors):
    """The edition: the printings (p. ii), the title page and its verso (pp. iii-iv)."""
    ed = leggi(os.path.join(IG, 'introduzione-generale', 'edizioni.tex'))
    fr = leggi(os.path.join(IG, 'introduzione-generale', 'frontespizio.tex'))
    mesi = 'gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre'.split()
    stampe = []
    for m in re.finditer(r'(\w+ (?:edizione|ristampa)): \\emph\{(\w+) (\d{4})\}', ed):
        stampe.append(dict(label=m.group(1), date=('%s %s' % (m.group(2), m.group(3))),
                           month='%s-%02d' % (m.group(3), mesi.index(m.group(2)) + 1)))
    verso = fr[fr.index('\\pagina{iv}'):]
    verso = verso[verso.index('\\begin{flushleft}') + len('\\begin{flushleft}'):verso.index('\\end{flushleft}')]
    verso = re.sub(r'\\setlength\{[^}]*\}\{[^}]*\}|\\footnotesize|\\hspace\*\{[^}]*\}|\\phantom\{[^{}]*\}', '', verso)
    verso = verso.replace('\\textcopyright', '©').replace('\\textregistered', '®')
    righe = [ln for ln in a_testo(verso, False).split('\n') if ln.strip()]
    plain = '\n'.join(righe)
    rec = dict(
        title='La Bibbia di Gerusalemme', publisher='Centro editoriale dehoniano (EDB)', place='Bologna',
        isbn='978-88-10-82031-5', printings=stampe, colophon=righe,
        sources=['Testo biblico di LA SACRA BIBBIA della CEI «editio princeps» 2008',
                 'Note e commenti di La Bible de Jérusalem nuova edizione 1998',
                 'Xilografie tratte da: Biblia Sacra Vulgatae editionis Sixti Quinti Pont. Max. iussu recognita '
                 'atque edita – Venetiis, 1625 apud Iuntas'],
        direction=('alfio-filippi', 'Alfio', 'Filippi'), editor=('mara-scarpa', 'Mara', 'Scarpa'),
        imprimatur=['✠ Card. Carlo Caffarra, Arcivescovo, Bologna, 14 novembre 2008',
                    '✠ Card. Pierre Eyt, presidente della Commissione dottrinale della Conferenza Episcopale '
                    'Francese, Roma, 30 settembre 1999 (per l’originale francese)'],
        rights=['© 2008 Fondazione di Religione Santi Francesco d’Assisi e Caterina da Siena (testo CEI)',
                '© 1998 Les Éditions du Cerf, Paris (note e commenti)',
                '© 2009 Centro editoriale dehoniano, via Nosadella, 6 – 40123 Bologna (edizione italiana)'],
        printer='«La Tipografica Varese S.p.A.», Varese 2011')
    flat = re.sub(r'\s+', ' ', plain)
    for k in ('isbn', 'printer'):                # the hand-made fields are printed there
        if re.sub(r'\s+', ' ', rec[k].replace('Varese 2011', '')).strip() not in flat:
            errors.append('edition: %s %r not on the title page' % (k, rec[k]))
    for w in ('Alfio Filippi', 'Mara Scarpa', 'Carlo Caffarra', 'Pierre Eyt', 'Les Éditions du Cerf', 'Nosadella',
              'Fondazione di Religione Santi Francesco d’Assisi e Caterina da Siena', '1625 apud Iuntas'):
        if w not in flat:
            errors.append('edition: %r not on the title page' % w)
    if len(stampe) != 5:
        errors.append('edition: %d printings, expected 5' % len(stampe))
    return rec


# ---------------------------------------------------------------- the canon

# the items of the two lists, in print order: the books of this Bible each one is (and the
# chapters, when the item is part of a book: "Susanna (= Daniele 13)")
CANONE_EBRAICO = [['Gen'], ['Exod'], ['Lev'], ['Num'], ['Deut'], ['Josh'], ['Judg'], ['1Sam', '2Sam'],
                  ['1Kgs', '2Kgs'], ['Isa'], ['Jer'], ['Ezek'],
                  ['Hos', 'Joel', 'Amos', 'Obad', 'Jonah', 'Mic', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal'],
                  ['Ps'], ['Job'], ['Prov'], ['Ruth'], ['Song'], ['Eccl'], ['Lam'], ['Esth'], ['Dan'],
                  ['Ezra', 'Neh'], ['1Chr', '2Chr']]
CANONE_GRECO = [['Gen'], ['Exod'], ['Lev'], ['Num'], ['Deut'], ['Josh'], ['Judg'], ['Ruth'],
                ['1Sam', '2Sam', '1Kgs', '2Kgs'], ['1Chr', '2Chr'], [], ['Ezra', 'Neh'], ['EsthGr'], ['Jdt'],
                ['Tob'], ['1Macc', '2Macc'],
                ['Ps'], [], ['Prov'], ['Eccl'], ['Song'], ['Job'], ['Wis'], ['Sir'], [],
                ['Hos', 'Amos', 'Mic', 'Joel', 'Obad', 'Jonah', 'Nah', 'Hab', 'Zeph', 'Hag', 'Zech', 'Mal'],
                ['Isa'], ['Jer'], ['Bar'], ['Lam'], ['Bar.6'], ['Ezek'], ['Dan.13'], ['Dan'], ['Dan.14']]


def canone(fname, mappa, cid, errors):
    t = leggi(os.path.join(IG, 'introduzione-generale', fname + '.tex'))
    gruppi, voci = [], []
    for m in re.finditer(r'\\(gruppocanone|sottogruppocanone)\{|\\item(?:\[(\d+)\.\])?\s', t):
        if m.group(1):
            arg, _ = group(t, m.end() - 1)
            parent = None
            if m.group(1) == 'sottogruppocanone':
                parent = [g for g in gruppi if g['parent'] is None][-1]['n']
            gruppi.append(dict(n=len(gruppi) + 1, title=a_testo(arg, False), html=a_testo(arg, True), parent=parent))
            continue
        end = re.compile(r'\\item\b|\\end\{(?:canone|elencogreco)\}').search(t, m.end()).start()
        raw = t[m.end():end].strip()
        k = len(voci)
        if k >= len(mappa):
            errors.append('%s: more items than the table' % cid)
            break
        voci.append(dict(n=int(m.group(2)) if m.group(2) else k + 1, group=gruppi[-1]['n'], text=a_testo(raw, False),
                         html=a_testo(raw, True), books=[b for b in mappa[k] if '.' not in b],
                         chapters=[b for b in mappa[k] if '.' in b],
                         deuterocanonical=raw.startswith('\\emph'), apocryphal=raw.startswith('{[}')))
    if len(voci) != len(mappa):
        errors.append('%s: %d items, %d in the table' % (cid, len(voci), len(mappa)))
    return dict(id=cid, groups=gruppi, items=voci)


def controlla_canoni(canoni, data, errors):
    at = [b['osis'] for b in data['books'] if b['testament'] == 'AT']
    ebr = Counter(b for v in canoni[0]['items'] for b in v['books'])
    want = [o for o in at if o not in ('Tob', 'Jdt', 'EsthGr', '1Macc', '2Macc', 'Wis', 'Sir', 'Bar')]
    if sorted(ebr) != sorted(want) or set(ebr.values()) != {1}:
        errors.append('Hebrew canon: %s, expected the %d books of the Hebrew text' % (sorted(ebr), len(want)))
    gr = {b for v in canoni[1]['items'] for b in v['books']}
    if gr != set(at) - {'Esth'}:
        errors.append('Greek canon: missing %s, extra %s' % (sorted(set(at) - {'Esth'} - gr), sorted(gr - set(at))))
    for v in canoni[1]['items']:
        if bool(v['books'] or v['chapters']) == v['apocryphal']:
            errors.append('Greek canon: %r apocryphal %s with books %s' % (v['text'], v['apocryphal'], v['books']))


# ---------------------------------------------------------------- abbreviations, codices

GREGORY = re.compile(r'^(.*?)\s*\((0\d+)\)$')


def abbreviazioni(errors):
    rows = list(csv.DictReader(open(os.path.join(IG, 'abbreviazioni.tsv'), encoding='utf-8'), delimiter='\t'))
    out = []
    for k, r in enumerate(rows, 1):
        books = []
        for sig in r['sigle_libri'].split():
            if sig not in R.SIGLA:
                errors.append('abbreviations: %r is not a siglum of canone.py' % sig)
            books += R.SIGLA.get(sig, [])
        rec = dict(n=k, form=r['sigla'], meaning=r['nome'], kind=r['tipo'], page=r['pagina'], books=books,
                   sigla=r['sigle_libri'].split())
        if r['tipo'].startswith(('codice', 'papiro')):
            m = GREGORY.match(r['sigla'])
            rec['gregory'] = m.group(2) if m else (r['sigla'] if re.fullmatch(r'0?\d+', r['sigla']) else
                                                   'P' + r['sigla'][1:] if r['tipo'] == 'papiro' else None)
            rec['letter'] = m.group(1) if m else None
        out.append(rec)
    sig = {x for r in out if r['kind'] == 'libro' for x in r['sigla']}
    if sig != set(R.SIGLA):
        errors.append('abbreviations: book sigla %s != canone.py (missing %s)' % (len(sig), sorted(set(R.SIGLA) - sig)))
    return out


# ---------------------------------------------------------------- the appendices (tsv.py)

def carica_tsv():
    """progetti/appendici/tsv.py as a module, its output redirected to ontologia/build/."""
    sys.path.insert(0, AP)
    scrivi, sys.dont_write_bytecode = sys.dont_write_bytecode, True      # no __pycache__ in the volume
    import tsv  # noqa: E402
    sys.dont_write_bytecode = scrivi
    sys.path.remove(AP)
    tsv.OUT = os.path.join(BUILD, 'cronologia.tsv')
    tsv.BIBBIA = IN
    for k, (src, out) in list(tsv.INDICI.items()):
        tsv.INDICI[k] = (src, os.path.join(BUILD, out))
    return tsv


class Cattura:
    """riferimenti.py as tsv.py sees it: every resolved reference is kept, in order."""

    def __init__(self):
        self.risolti = []

    def __getattr__(self, k):
        return getattr(R, k)

    def resolve(self, r, B, ctx):
        out = R.resolve(r, B, ctx)
        self.risolti.append(out)
        return out


def leggi_tsv(path):
    return list(csv.DictReader(open(path, encoding='utf-8'), delimiter='\t'))


def confronta(nome, errors, warnings):
    a, b = os.path.join(AP, nome), os.path.join(BUILD, nome)
    if open(a, encoding='utf-8').read() != open(b, encoding='utf-8').read():
        warnings.append('%s differs from the one made now (the volume\'s file is stale: run '
                        'progetti/appendici/tsv.py)' % os.path.relpath(a, C))


# misprints of the indices whose correction the checklist (progetti/appendici/checklist-ocr.md)
# states with its evidence: (index, headword, reference as printed, corrected reference, why: in
# Italian, it is shown in the explorer and kept in the graph as bj:correzione)
CORREZIONI_INDICI = [
    ('note', 'Caleb', 'Gb 14,6', 'Gs 14,6', 'Caleb è in Gs 14,6: lì c’è una nota della BJ, in Gb 14,6 nessuna'),
    ('note', 'Anziani', 'Lc 22,60', 'Lc 22,66', 'la nota della BJ sugli anziani del popolo è a Lc 22,66'),
    ('note', 'Amore', 'Gv 13,24', 'Gv 13,34', 'la nota della BJ sul comandamento nuovo è a Gv 13,34'),
    ('note', 'Legge', 'Mt 5,11', 'Mt 5,17', 'la nota della BJ sulla Legge antica e nuova è a Mt 5,17'),
    ('note', 'Emmanuele', 'Is 7,10', 'Is 7,14', 'la nota della BJ sull’Emmanuele è a Is 7,14'),
    ('note', 'Gàlgala (gilgāl)', 'Os 9,14', 'Os 9,15', 'la nota della BJ su Gàlgala è a Os 9,15 («a Gàlgala: …»); '
     'a Os 9,14 nessuna nota (p. 33, PDF 3034)'),
    ('note', 'Decima', 'Eb 7,3', 'Eb 7,4', 'la nota della BJ sulla decima è a Eb 7,4 («la decima del suo bottino»; '
     'p. 31, PDF 3032)'),
    ('note', 'Martire', 'At 7,57', 'At 7,58', 'la nota della BJ sulla morte del «primo martire» è a At 7,58 '
     '(p. 34, PDF 3035)'),
    ('note', 'Scritture', '1Ts 5,25', '1Ts 5,27', 'la nota della BJ sulla «prima menzione della lettura pubblica» di '
     'una lettera dell’apostolo è a 1Ts 5,27 (p. 38, PDF 3039)'),
    ('temi', 'Cuore', 'Cr 28,9', '1Cr 28,9', 'la sigla è stampata senza il numero (1Cr)'),
    ('temi', 'Gioia', '62,5', 'Is 62,5', 'i riferimenti a Isaia seguono Sof senza la sigla'),
    ('temi', 'Gioia', '66,10–14', 'Is 66,10–14', 'i riferimenti a Isaia seguono Sof senza la sigla'),
    ('temi', 'Gioia', '65,17–19', 'Is 65,17–19', 'i riferimenti a Isaia seguono Sof senza la sigla'),
    ('temi', 'Insegnare', 'Na 8,7–9', 'Ne 8,7–9', 'Na per Ne (Ne 8: Esdra legge la Legge)'),
    ('temi', 'Lode', '135,1ss', 'Sal 135,1ss', 'i salmi seguono Gdc 5 senza la sigla'),
    ('temi', 'Lode', '136,1ss', 'Sal 136,1ss', 'i salmi seguono Gdc 5 senza la sigla'),
    ('temi', 'Obbedienza', 'Sap 24,22', 'Sir 24,22', 'Sap per Sir (Sap ha 19 capitoli)'),
    ('temi', 'Promessa', 'Gn 17,8', 'Gen 17,8', 'Gn (Giona) per Gen'),
    ('temi', 'Speranza', '10.23', 'Eb 10,23', 'un punto per la virgola: Eb 10,23'),
    ('temi', 'Uomo', '12,47', 'Gv 12,47', 'Gv 12,47 segue 1Gv senza la sigla'),
]
# misprinted references in the prose of the appendices (not in the graph: only the Tufte edition
# links them, tools/tufte/paratesti.py): the link goes to the corrected verse, the text stays as
# printed. (text of progetti/appendici, reference as printed, corrected reference, why; the
# evidence in the checklist of the volume). Every row must be used exactly once.
CORREZIONI_PROSA = [
    ('misure', 'Zac 5,5–11', 'Zc 5,5–11', 'Zac per Zc: la donna nell’efa è in Zc 5,5–11 (p. 27, PDF 3028)'),
    ('misure', 'Zac 11,12', 'Zc 11,12', 'Zac per Zc: i trenta sicli d’argento di Zc 11,12 (p. 28, PDF 3029)'),
    ('misure', 'Esd 6,69', 'Esd 2,69', 'il parallelo di Ne 7,70 è Esd 2,69 (Esd 6 ha 22 versetti; p. 27, PDF 3028)'),
]
NOTA_ORDINE = ('nota', 'capitolo', 'copre', 'rimandi', 'nessuna')


def note_alla(B, notes_idx, vid):
    """The BJ notes at a verse, as tsv.py's `nota` column (for a corrected reference)."""
    ids = list(dict.fromkeys(B.notes_first.get(vid, []) + B.notes_at.get(vid, [])))
    if ids:
        return 'nota', ids
    if notes_idx.get(vid):
        return 'copre', notes_idx[vid]
    return ('rimandi' if B.mrefs_at.get(vid) else 'nessuna'), []


def indice(which, tsv, data, B, errors, warnings):
    cat = Cattura()
    tsv.R = cat
    rows = tsv.indice(which, B, data)
    tsv.R = R
    confronta(os.path.basename(tsv.INDICI[which][1]), errors, warnings)
    risolti = iter(cat.risolti)
    copre = {}
    for n in data['notes']:
        for t in n['targets']:
            copre.setdefault(t, []).append(n['id'])
    voci, by_n = [], {}
    used = Counter()
    for row in rows:
        n = int(row['voce'])
        if n not in by_n:
            html = tex_html(row['lemma_tex'].replace('\\textsuperscript{e}', 'ᵉ'))     # "Nᵉpîlîm"
            by_n[n] = dict(n=n, lemma=row['lemma'], tex=row['lemma_tex'], html=html, style=row['stile'],
                           page=int(row['pagina']), sub=[], items=[])
            voci.append(by_n[n])
        v = by_n[n]
        sv = 0
        if row['sottovoce']:
            labels = [s['label'] for s in v['sub']]
            if not labels or labels[-1] != row['sottovoce'] or v['sub'][-1]['name'] != row['percorso'].split(' > ', 1)[1]:
                v['sub'].append(dict(k=len(v['sub']) + 1, label=row['sottovoce'], html=tex_html(sv_tex(row['sottovoce'])),
                                     name=row['percorso'].split(' > ', 1)[1], page=int(row['pagina'])))
            sv = v['sub'][-1]['k']
        item = dict(kind=row['tipo'], sv=sv, raw=row['riferimento'], page=int(row['pagina']), cf=bool(row['cf']),
                    seguito=row['seguito'] or None)
        lid = 'indice-%s.%d#c%d' % (which, n, sum(1 for x in v['items'] if x['kind'] in ('rif', 'libro')) + 1)
        if row['tipo'] == 'vedi':
            item['to'] = [int(x.split()[1]) for x in re.findall(r'voce \d+', row['destinazione_vedi'])]
            if not item['to']:
                warnings.append('index %s: v. %r of %s matches no entry' % (which, row['riferimento'], row['lemma']))
            if row['motivo']:                        # tsv.RIMANDI: a target read by hand
                item['why'] = row['motivo']
        elif row['tipo'] == 'pagina':
            item['intros'] = row['destinazione_vedi'].split()
            if row['motivo']:                        # tsv.PAGINE_ESTRANEE: not a page of this edition
                item['why'] = row['motivo']
        elif row['tipo'] == 'libro':
            r = dict(raw=row['riferimento'], sign=None, book=row['osis'], target_book=row['osis'], targets=[],
                     ranges=[], status='resolved', reason=None, qualifier=None, alt=None, flags=[], keynote=False,
                     keynote_notes=[], offset=0, cf=bool(row['cf']))
            item['link'] = R.record(lid, 'index-cites', 'indice-%s.%d' % (which, n), None, 'cites', r)
            del item['link']['offset'], item['link']['length']
        else:
            if row['motivo'] == 'not read by riferimenti.py':
                r = dict(raw=row['riferimento'], sign=None, book=None, targets=[], ranges=[], status='unresolved',
                         reason='not understood', qualifier=None, alt=None, flags=[], keynote=False, keynote_notes=[],
                         offset=0, cf=bool(row['cf']))
            else:
                r = next(risolti)
                exp = ' '.join(a if a == z else '%s..%s' % (a, z) for a, z in r['ranges'])
                if exp != row['destinazioni'] or r['status'] != row['stato']:
                    errors.append('index %s %s %r: captured %s, row %s' % (which, row['lemma'], row['riferimento'],
                                                                           exp, row['destinazioni']))
            rec = R.record(lid, 'index-cites', 'indice-%s.%d' % (which, n), None, 'cites', dict(r, cf=bool(row['cf'])))
            rec['raw'] = row['riferimento']
            del rec['offset'], rec['length']
            if row['ereditato']:
                rec['implicit'] = 1 if row['ereditato'] == 'sì' else 2
            if which == 'note':
                rec['nota'] = row['nota'] or None
                rec['notes'] = row['note'].split()
            fix = [x for x in CORREZIONI_INDICI if x[0] == which and x[1] == v['lemma'] and x[2] == row['riferimento']]
            if fix:
                used[fix[0]] += 1
                ref = R.scan_prose(fix[0][3], CTX)
                ref = R.resolve(ref[0], B, CTX) if len(ref) == 1 else None
                if not ref or ref['status'] != 'resolved':
                    errors.append('index correction %r does not resolve' % (fix[0],))
                else:
                    corr = dict(raw=fix[0][3], targets=ref['targets'], ranges=ref['ranges'], why=fix[0][4],
                                book=ref['book'])
                    if which == 'note':
                        corr['nota'], corr['notes'] = note_alla(B, copre, ref['targets'][0])
                    rec['correction'] = corr
            item['link'] = rec
        v['items'].append(item)
    rest = list(risolti)
    if rest:
        errors.append('index %s: %d references resolved but not in the rows' % (which, len(rest)))
    for x in CORREZIONI_INDICI:
        if x[0] == which and used[x] != 1:
            errors.append('index correction %r used %d times' % (x, used[x]))
    nums = {v['n'] for v in voci}
    for v in voci:
        for it in v['items']:
            for t in it.get('to', []):
                if t not in nums:
                    errors.append('index %s: v. %s of %s points to no entry' % (which, t, v['lemma']))
            ln = it.get('link')
            if ln:
                for t in ln['targets'] + (ln.get('correction') or {}).get('targets', []):
                    if t not in B.verses:
                        errors.append('%s: unknown verse %s' % (ln['id'], t))
                for nid in ln.get('notes', []) + (ln.get('correction') or {}).get('notes', []):
                    if nid not in NOTE_IDS:
                        errors.append('%s: unknown note %s' % (ln['id'], nid))
    return dict(id=which, voci=voci)


NOTE_IDS = set()


# ---------------------------------------------------------------- chronology

COLONNE = [('universale', 'Storia universale', 'World history'),
           ('palestina', 'Storia palestinese e biblica', 'Palestinian and biblical history'),
           ('israele', 'Regno di Israele', 'Kingdom of Israel'), ('giuda', 'Regno di Giuda', 'Kingdom of Judah'),
           ('egitto', 'Egitto', 'Egypt'), ('lagidi', 'Lagidi (Tolomei)', 'Lagids (Ptolemies)'),
           ('seleucidi', 'Seleucidi', 'Seleucids')]
MESE = (r'(?:Inizio|Fine|Primavera|Estate|Autunno|Inverno|Pasqua|Pentecoste|Verso Pentecoste|Verso|Prima|'
        r'Gennaio|Febbraio|Marzo|Aprile|Maggio|Giugno|Luglio|Agosto|Settembre|Ottobre|Novembre|Dicembre|'
        r'Genn?\.|Febbr?\.|Mar\.|Apr\.|Ag\.|Sett?\.|Ott\.|Nov\.|Dic\.)')
MESE = MESE + r'(?:\s+(?:primavera|estate|autunno|inverno))?(?:\s+o\s+[a-zà-ù]+)?'   # "Fine estate 51", "Estate o autunno 63"
MESI = r'(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)'
ERA = r'(?:\s*(?P<e>a\.C\.|d\.C\.))?'
A, Z = r'(?P<a>\d{1,4})', r'(?P<z>\d{1,4})'
# the date an entry starts with (groups a, z: first and last year as printed; e: the era; s: a
# shortened last year, "589/8"); else the one span in parentheses (a reign: "(680–669)", "(sett. 605–562)")
DATA_INIZIO = [
    # "Fra il 34 e il 45:", "Tra 70 e 80 (?):"
    re.compile(r'^(?:Fra|Tra) (?:il )?' + A + r' e (?:il )?' + Z + ERA + r'(?:\s*\(\?\))?\s*:'),
    # "Primavera 50-estate 51:"
    re.compile(r'^(?:%s\s+)?' % MESE + A + r'\s*[-–]\s*[a-z]+ ' + Z + ERA + r'\s*:'),
    # "Dall’1/2 al 4 d.C.,", "Dal 721 al 711 e nel 703:"
    re.compile(r'^Dall’' + A + r'(?:/\d+)? al ' + Z + ERA + r'\s*[,:]'),
    re.compile(r'^Dal ' + A + r' al (?:\d{1,4} e nel )?' + Z + ERA + r'\s*:'),
    # "19 agosto 14:", "28 giugno 45:"
    re.compile(r'^\d{1,2} %s ' % MESI + A + ERA + r'\s*:'),
    # "Verso il 738:", "Verso l’84:"
    re.compile(r'^Verso (?:il |l’)' + A + ERA + r'\s*:'),
    # "589/8:", "582/581:"
    re.compile(r'^' + A + r'/(?P<s>\d{1,4})' + ERA + r'\s*:'),
    # "Giugno-luglio 587 o 586:", "Aprile-maggio 160:", "Giugno (?) 37:"
    re.compile(r'^%s(?:[-–][a-z]+|\s+\(\?\))\s+' % MESE + A + r'(?:\s+o\s+' + Z + r')?' + ERA + r'\s*:'),
    # "141, giugno:", "4, Pasqua (11 aprile):"
    re.compile(r'^' + A + r',\s+[A-Za-z]+(?:\s*\([^)]*\))?' + ERA + r'\s*:'),
    # "37 (o 38) ca.:", "64 (o 67):", "Inverno 55–56 (o 56–57):"
    re.compile(r'^(?:%s\s+)?' % MESE + A + r'(?:\s*[–-]\s*\d{1,4})?\s*\(o (?:\d{1,4}\s*[–-]\s*)?' + Z +
               r'\)(?:\s*ca\.)?' + ERA + r'\s*:'),
    # "Nov. 164:", "164 inizio:", "Estate 55 o 56:", "41–30:", "50 ca.:", "6 d.C.:", "970ca.–931:"
    re.compile(r'^(?:%s\s+)?(?P<a>\d{1,7})(?:\s*ca\.)?(?:\s*(?:[–-]|o)\s*' % MESE + Z +
               r')?(?:\s+(?:inizio|fine|ca\.|circa))?' + ERA + r'\s*:'),
]
PARENTESI = re.compile(r'\((?:ca\.\s*|verso il\s*|(?:genn?|febbr?|mar|apr|ag|sett?|ott|nov|dic)\.\s*)?(\d{2,4})\s*[–-]\s*(\d{1,4})(?:\s*ca\.)?' + ERA + r'\)')


def anno(n, era):
    return -n if era == 'a' else n


def data_voce(testo, era_riga):
    """(date as printed, start, end, circa) of a chronology entry; start/end None if ambiguous."""
    for k, pat in enumerate(DATA_INIZIO):
        m = pat.match(testo)
        if m:
            g = m.groupdict()
            s, a, z, e = m.group(0).rstrip(' :,'), g['a'], g.get('z') or g['a'], g.get('e')
            if g.get('s'):                       # "589/8": 589 to 588
                z = g['a'][:max(0, len(g['a']) - len(g['s']))] + g['s']
            break
    else:
        spans = {m.group(0) for m in PARENTESI.finditer(testo)}
        if len(spans) != 1:
            return None, None, None, False
        m = PARENTESI.search(testo)
        s, a, z, e = m.group(0).strip('()'), m.group(1), m.group(2), m.group(3)
    circa = bool(re.search(r'(?:\b|(?<=\d))ca\.|\bcirca\b|^Verso\b', s))      # "970ca.–931"
    era = {'a.C.': 'a', 'd.C.': 'd'}.get(e, era_riga)
    a, z = int(a), int(z)                        # as printed: no shortened ends in the table
    lo, hi = anno(a, era), anno(z, era)
    if hi < lo:
        return s, None, None, circa              # the order does not fit the era: ambiguous
    return s, lo, hi, circa


def cronologia(tsv, B, errors, warnings):
    tsv.R = R
    tsv.cronologia()
    confronta('cronologia.tsv', errors, warnings)
    rows = leggi_tsv(tsv.OUT)
    src = leggi(os.path.join(AP, 'appendici', 'cronologia.tex'))
    intro = src[src.index('\\testo{Tavola cronologica}'):src.index('\\sezione')]
    intro = re.sub(r'\\testo\{[^}]*\}|\\pagina\{\d+\}%?', '', intro)
    intro = [dict(text=a_testo(b, False), html=a_testo(b, True)) for b in re.split(r'\n\s*\n', intro) if b.strip()]
    sezioni, voci, links = [], [], []
    svolta = None                                    # section IX: the first row dated d.C.
    for r in rows:
        if r['sezione'].startswith('IX') and re.match(r'^[^:]*\bd\.C\.\s*[,:]', r['testo']) and svolta is None:
            svolta = int(r['riga'])
    for r in rows:
        if not sezioni or sezioni[-1]['title'] != r['sezione']:
            sezioni.append(dict(n=len(sezioni) + 1, title=r['sezione'], roman=r['sezione'].split('.')[0]))
        riga = int(r['riga'])
        era = 'd' if sezioni[-1]['roman'] == 'IX' and svolta and riga >= svolta else 'a'
        s, lo, hi, circa = data_voce(r['testo'], era)
        html = tex_html(r['testo_tex'])
        n = int(r['voce'])
        rec = dict(n=n, section=sezioni[-1]['n'], row=riga, margin=r['anni_margine'] or None, page=int(r['pagina']),
                   column=r['colonna'], order=int(r['ordine']), text=r['testo'], html=html,
                   smallcaps=[x for x in r['maiuscoletto'].split('; ') if x],
                   caps=[x for x in r['maiuscolo'].split('; ') if x], date=s, start=lo, end=hi, circa=circa)
        voci.append(rec)
        hmap = R.html_offsets(r['testo'], html)
        if hmap is None:
            errors.append('chronology %d: HTML does not match the text' % n)
        for k, ref in enumerate(R.scan_prose(r['testo'], CTX), 1):
            R.resolve(ref, B, CTX)
            ln = R.record('cronologia.%d#c%d' % (n, k), 'chrono-cites', 'cronologia.%d' % n, None, 'cites', ref)
            ln.update(html_offset=hmap[ref['offset']] if hmap else None,
                      html_end=fine_html(hmap, html, ref['offset'] + len(ref['raw'])))
            links.append(ln)
        got = ' | '.join(x['raw'] for x in links if x['source'] == 'cronologia.%d' % n)
        if got != r['riferimenti']:
            errors.append('chronology %d: references %r, the table %r' % (n, got, r['riferimenti']))
    return dict(intro=intro, sections=sezioni, columns=[dict(id=a, it=b, en=c) for a, b, c in COLONNE],
                turn=svolta, voci=voci), links


def sv_tex(label):
    """A sub-entry label is plain text in the tables: as HTML it only needs escaping."""
    return label


def tex_html(t):
    """The LaTeX of a chronology entry (\\emph, \\textsc) -> the HTML of the explorer."""
    t = t.replace('\\dots', '…').replace('\\textdagger', '†').replace('\\sposo{}', '∞')
    t = re.sub(r'\\textsuperscript\{(\w)\}', lambda m: {'a': 'ª', 'o': 'º'}.get(m.group(1), m.group(1)), t)
    t = t.replace('\\newline', ' ').replace('\\ ', ' ').replace('~', ' ')
    t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    for _ in range(3):
        t = re.sub(r'\\emph\{([^{}]*)\}', r'<em>\1</em>', t)
        t = re.sub(r'\\textsc\{([^{}]*)\}', r'<span class="sc">\1</span>', t)
        t = re.sub(r'\\textbf\{([^{}]*)\}', r'<strong>\1</strong>', t)
    return re.sub(r'\s+', ' ', t).strip()


# ---------------------------------------------------------------- dynasties

def dinastie(errors):
    rows = leggi_tsv(os.path.join(AP, 'dinastie.tsv'))
    ids = {r['id'] for r in rows}
    out = []
    for r in rows:
        rec = dict(id=r['id'], number=r['numero'] or None, name=r['nome'], italic=r['corsivo'] == '1',
                   date=r['date'] or None, father=r['padre'] or None, mother=r['madre'] or None,
                   spouses=[x.strip() for x in r['coniugi'].split(';') if x.strip()], note=r['nota'] or None)
        for k in ('father', 'mother'):
            if rec[k] and rec[k] not in ids:
                errors.append('dynasties: %s %s %s unknown' % (r['id'], k, rec[k]))
        out.append(rec)
    by = {x['id']: x for x in out}
    for x in out:
        for s in x['spouses']:
            if s not in by or x['id'] not in by[s]['spouses']:
                errors.append('dynasties: %s ∞ %s not both ways' % (x['id'], s))
    return out


# ---------------------------------------------------------------- main

def checks_links(links, P, B, errors):
    texts = {'%s.%d' % (t['id'], p['n']): p for t in P['testi'] for p in t['paragraphs']}
    texts.update({'cronologia.%d' % v['n']: v for v in P['cronologia']['voci']})
    ids = Counter(x['id'] for x in links)
    dup = [k for k, n in ids.items() if n > 1]
    if dup:
        errors.append('duplicate link ids %s' % dup[:5])
    for x in links:
        if any(t not in B.verses for t in x['targets']):
            errors.append('%s: unknown target' % x['id'])
        if x['status'] in ('unresolved', 'partial') and not x['reason']:
            errors.append('%s: %s without a reason' % (x['id'], x['status']))
        if x['kind'] in ('front-cites', 'chrono-cites'):
            p = texts[x['source']]
            if p['text'][x['offset']:x['offset'] + x['length']] != x['raw']:
                errors.append('%s: offset does not match the text' % x['id'])
            if x['html_offset'] is None or re.sub(r'<[^>]+>', '', p['html'][x['html_offset']:x['html_end']]).replace(
                    '&amp;', '&') != x['raw']:
                errors.append('%s: HTML offsets do not match' % x['id'])


def main(a):
    quiet = '-q' in a
    data = json.load(open(IN, encoding='utf-8'))
    B = R.Bibbia(data)
    NOTE_IDS.update(n['id'] for n in data['notes'])
    errors, warnings = [], []
    testi = [testo(tid, f, kind, aut, B, errors) for tid, f, kind, aut in TESTI]
    links = [x for t in testi for x in citazioni_testo(t, B)]
    av = next(t for t in testi if t['id'] == 'avvertenze')
    xilo = xilografie(av, B, errors)
    canoni = [canone('divisione-ebraica', CANONE_EBRAICO, 'ebraico', errors),
              canone('divisione-greca', CANONE_GRECO, 'greco', errors)]
    controlla_canoni(canoni, data, errors)
    tsv = carica_tsv()
    old_out = sys.stdout
    if quiet:
        sys.stdout = open(os.devnull, 'w')
    try:
        crono, clinks = cronologia(tsv, B, errors, warnings)
        indici = [indice('note', tsv, data, B, errors, warnings), indice('temi', tsv, data, B, errors, warnings)]
    finally:
        if quiet:
            sys.stdout.close()
            sys.stdout = old_out
    links += clinks
    ilinks = [it['link'] for ix in indici for v in ix['voci'] for it in v['items'] if it.get('link')]
    P = dict(edizione=edizione(errors), testi=testi, canoni=canoni, abbreviazioni=abbreviazioni(errors),
             xilografie=xilo, indici=indici, cronologia=crono, dinastie=dinastie(errors))
    checks_links(links + ilinks, P, B, errors)
    st = Counter((x['kind'], x['status']) for x in links + ilinks)
    summary = dict(
        texts=len(testi), paragraphs=sum(len(t['paragraphs']) for t in testi), abbreviations=len(P['abbreviazioni']),
        codices=sum(1 for x in P['abbreviazioni'] if 'gregory' in x), woodcuts=len(xilo),
        chronology_entries=len(crono['voci']), chronology_dated=sum(1 for v in crono['voci'] if v['start'] is not None),
        chronology_dates_printed=sum(1 for v in crono['voci'] if v['date']),
        persons=len(P['dinastie']), links={'%s %s' % k: n for k, n in sorted(st.items())},
        corrections=sum(1 for x in ilinks if x.get('correction')))
    for ix in indici:
        its = [it for v in ix['voci'] for it in v['items']]
        refs = [it['link'] for it in its if it['kind'] == 'rif']
        summary['index_' + ix['id']] = dict(
            entries=len(ix['voci']), subentries=sum(len(v['sub']) for v in ix['voci']), references=len(refs),
            resolved=sum(1 for x in refs if x['status'] == 'resolved'), books=sum(1 for it in its if it['kind'] == 'libro'),
            see=sum(1 for it in its if it['kind'] == 'vedi'), pages=sum(1 for it in its if it['kind'] == 'pagina'),
            nota=dict(Counter(x.get('nota') for x in refs if x.get('nota'))))
    P['meta'] = dict(source='progetti/introduzione-generale, progetti/appendici', generated_by='tools/ontologia/paratesto.py',
                     summary=summary, warnings=warnings)
    P['links'] = links
    dump(P, OUT)
    if not quiet:
        for k, v in summary.items():
            print('  %s: %s' % (k, v))
    n = summary['index_note']
    print('paratesto: %d texts (%d paragraphs), %d abbreviations (%d codices), %d woodcuts; index of notes %d entries, '
          '%d sub-entries, %d references (%d resolved), %d «v.»; themes %d, %d, %d; chronology %d entries (%d dated), '
          '%d references; dynasties %d persons; %d index corrections' % (
              summary['texts'], summary['paragraphs'], summary['abbreviations'], summary['codices'], summary['woodcuts'],
              n['entries'], n['subentries'], n['references'], n['resolved'], n['see'],
              summary['index_temi']['entries'], summary['index_temi']['subentries'], summary['index_temi']['references'],
              summary['chronology_entries'], summary['chronology_dated'], len(clinks), summary['persons'],
              summary['corrections']))
    for w in warnings:
        print('WARNING ' + w)
    for e in errors[:30]:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errors else '%d errors' % len(errors), os.path.relpath(OUT, C)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
