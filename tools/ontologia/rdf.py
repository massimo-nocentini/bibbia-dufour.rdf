"""Build the RDF graph of the verse ontology from the two JSON files of stages 1 and 2.

usage: rdf.py [-q]

Reads ontologia/build/bibbia.json (estrai.py) and ontologia/build/collegamenti.json
(riferimenti.py) and writes, in the vocabulary of ontologia/bj-ontologia.ttl:
  ontologia/bj-dati.ttl.gz      Turtle, one block per resource
  ontologia/bj-dati.nt.gz       N-Triples, the same triples in the same order
  ontologia/bj-contesto.jsonld  a JSON-LD context for the bj: terms and the data ids
  ontologia/bj-void.ttl         a VoID description of the data: sizes, classes, properties
Resources: the Bible, the two testaments, the books, chapters, divisions, pericopes,
verses, printed pages, introductions and their paragraphs, the notes (Web Annotations,
with a textual body), the margin entries, each margin reference (bj:Rimando), each
citation inside a note or introduction (bj:Citazione) and the passages they name
(bj:Passaggio, shared, identified by first and last verse). The shortcuts between
resources are materialised: bj:haNota / bj:richiamataDa, bj:commenta, bj:citaVersetto,
bj:rimandaA with bj:paralleloA and bj:doppioneDi (both directions: symmetric),
bj:citatoIn and bj:rinviaANotaChiave (only to the verse of each "+" span that holds the
key note). A "=" tied to the previous reference of its margin ("‖2Cr 1,14=9,25") is
bj:doppioneDelRimando of that reference; a margin entry anchored to the verse that
begins on its printed line keeps the verse its call is printed in as
bj:stampatoNelVersetto.

No blank nodes: every resource has an IRI under ID, so the graph can be compared as a
set of triples. Output is deterministic (same order, gzip without timestamps).

Checks (exit status 1 if any fails): every bj: term used is declared in the ontology,
and every declared term has an Italian and English rdfs:label and rdfs:comment; object
properties have IRIs as objects and datatype properties literals of their range; every
IRI of the data that is an object is also described; resource counts equal the JSON
counts; the verses of the passages of each link equal its targets; no duplicate triples.
"""
import gzip
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402

OUT = os.path.join(C, 'ontologia')
BIBBIA = os.path.join(OUT, 'build', 'bibbia.json')
COLLEGAMENTI = os.path.join(OUT, 'build', 'collegamenti.json')
ONTOLOGIA = os.path.join(OUT, 'bj-ontologia.ttl')
TTL = os.path.join(OUT, 'bj-dati.ttl.gz')
NT = os.path.join(OUT, 'bj-dati.nt.gz')
CONTESTO = os.path.join(OUT, 'bj-contesto.jsonld')
VOID = os.path.join(OUT, 'bj-void.ttl')

SITO = 'https://massimo-nocentini.github.io/bibbia-gerusalemme/'
BJ = SITO + 'ontologia#'
ID = SITO + 'id/'
# data namespaces: one per kind of resource (id/verso/John.3.16, id/libro/John, ...)
RISORSE = ['testamento', 'libro', 'capitolo', 'divisione', 'pericope', 'verso', 'pagina', 'introduzione',
           'paragrafo', 'nota', 'corpo', 'margine', 'rimando', 'citazione', 'passaggio']
PREFISSI = dict([
    ('bj', BJ), ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('xsd', 'http://www.w3.org/2001/XMLSchema#'),
    ('owl', 'http://www.w3.org/2002/07/owl#'), ('dcterms', 'http://purl.org/dc/terms/'),
    ('dc', 'http://purl.org/dc/elements/1.1/'), ('skos', 'http://www.w3.org/2004/02/skos/core#'),
    ('oa', 'http://www.w3.org/ns/oa#'), ('cito', 'http://purl.org/spar/cito/'),
    ('prov', 'http://www.w3.org/ns/prov#'), ('id', ID)] + [(r, ID + r + '/') for r in RISORSE])

RELAZIONE = {'related': 'bj:correlato', 'parallel': 'bj:parallelo', 'doublet': 'bj:doppione',
             'quoted-later': 'bj:citatoDopo', 'numbering': 'bj:numerazione', 'comment': 'bj:commento'}
DIRETTA = {'related': None, 'parallel': 'bj:paralleloA', 'doublet': 'bj:doppioneDi',
           'quoted-later': 'bj:citatoIn'}
SIMMETRICHE = ('bj:paralleloA', 'bj:doppioneDi')
STATO = {'resolved': 'bj:risolto', 'partial': 'bj:parziale', 'unresolved': 'bj:irrisolto',
         'numbering': 'bj:nonRiferimento', 'comment': 'bj:nonRiferimento'}
AMBITO = {'verses': 'bj:ambitoVersetti', 'chapter': 'bj:ambitoCapitolo', 'book': 'bj:ambitoLibro'}
TESTAMENTI = [('AT', 'Antico Testamento', 'Old Testament'), ('NT', 'Nuovo Testamento', 'New Testament')]
PAGINA_PDF = 33

# a literal is a tuple (kind, value): s string, it Italian text, i integer, b boolean
XSD = {'i': 'xsd:integer', 'b': 'xsd:boolean'}
PN_LOCAL = re.compile(r'[A-Za-z0-9_]([A-Za-z0-9_.\-]*[A-Za-z0-9_\-])?$')


def s(x):
    return ('s', x)


def it(x):
    return ('it', x)


def i(x):
    return ('i', int(x))


def b(x):
    return ('b', bool(x))


class Grafo:
    """Triples grouped by subject, in the order they are added (the output order)."""

    def __init__(self):
        self.per = {}
        self.visti = set()
        self.doppi = 0

    def add(self, sog, pred, ogg):
        if ogg is None:
            return
        t = (sog, pred, ogg)
        if t in self.visti:
            self.doppi += 1
            return
        self.visti.add(t)
        self.per.setdefault(sog, []).append((pred, ogg))

    def link(self, sog, pred, ogg):
        """A materialised shortcut: added once, duplicates are expected and dropped."""
        if (sog, pred, ogg) not in self.visti:
            self.add(sog, pred, ogg)

    def __len__(self):
        return len(self.visti)


# ---------------------------------------------------------------- ids and labels

def iri(kind, local):
    return '%s:%s' % (kind, local)


def verso(vid):
    return iri('verso', vid)


def pagina(n):
    return iri('pagina', n)


def nota(nid):
    return iri('nota', nid.split(':', 1)[1])


def margine(mid):
    return iri('margine', mid.split(':', 1)[1])


def rimando(lid):
    return iri('rimando', lid.split(':', 1)[1].replace('#', '-'))


def citazione(lid):
    return iri('citazione', lid.split(':', 1)[-1].replace('#', '-'))


def introduzione(iid):
    return iri('introduzione', iid[len('intro-'):])


def paragrafo(iid, n):
    return iri('paragrafo', '%s.%d' % (iid[len('intro-'):], n))


def capitolo(osis, n):
    return iri('capitolo', '%s.%s' % (osis, R.PROLOGO if n == 0 else n))


def passaggio(a, z):
    return iri('passaggio', a if a == z else '%s-%s' % (a, z))


def sigla(book):
    """The CEI siglum, with the text of Esther named (both are «Est»)."""
    return {'EsthGr': 'Est gr.', 'Esth': 'Est ebr.'}.get(book['osis'], book['siglum'])


def etichetta_versetto(v, book):
    if v['chapter'] == 0:
        return '%s prol. %s' % (sigla(book), v['label'])
    return '%s %s,%s' % (sigla(book), v['chapter'], v['label'])


def etichetta_passaggio(va, vz, books):
    a = etichetta_versetto(va, books[va['book']])
    if va['id'] == vz['id']:
        return a
    if va['book'] != vz['book']:
        return '%s–%s' % (a, etichetta_versetto(vz, books[vz['book']]))
    if va['chapter'] != vz['chapter']:
        return '%s–%s,%s' % (a, R.PROLOGO if vz['chapter'] == 0 else vz['chapter'], vz['label'])
    return '%s–%s' % (a, vz['label'])


# ---------------------------------------------------------------- structure

def struttura(G, data):
    G.add('id:bibbia', 'rdf:type', 'bj:Bibbia')
    G.add('id:bibbia', 'dcterms:title', it('La Bibbia di Gerusalemme'))
    G.add('id:bibbia', 'rdfs:label', it('La Bibbia di Gerusalemme'))
    G.add('id:bibbia', 'dcterms:publisher', s('EDB'))
    G.add('id:bibbia', 'dcterms:description', it(
        'Testo CEI 2008 con le note e i rimandi a margine della Bible de Jérusalem'))
    for n, (t, nome, name) in enumerate(TESTAMENTI, 1):
        T = iri('testamento', t)
        G.add(T, 'rdf:type', 'bj:Testamento')
        G.add(T, 'rdfs:label', it(nome))
        G.add(T, 'rdfs:label', ('en', name))
        G.add(T, 'dcterms:identifier', s(t))
        G.add(T, 'bj:ordine', i(n))
        G.add(T, 'dcterms:isPartOf', 'id:bibbia')
    for bk in data['books']:
        L = iri('libro', bk['osis'])
        G.add(L, 'rdf:type', 'bj:Libro')
        G.add(L, 'rdfs:label', it(bk['title']))
        G.add(L, 'dcterms:title', it(bk['title_long']))
        G.add(L, 'dcterms:identifier', s(bk['osis']))
        G.add(L, 'bj:codiceOsis', s(bk['osis']))
        G.add(L, 'bj:sigla', s(bk['siglum']))
        G.add(L, 'bj:ordine', i(bk['order']))
        G.add(L, 'bj:volume', s(bk['volume']))
        G.add(L, 'dcterms:isPartOf', iri('testamento', bk['testament']))
        for ch in bk['chapters']:
            K = capitolo(bk['osis'], ch['n'])
            G.add(K, 'rdf:type', 'bj:Capitolo')
            G.add(K, 'rdfs:label', s('%s %s' % (sigla(bk), 'prol.' if ch['n'] == 0 else ch['n'])))
            G.add(K, 'dcterms:identifier', s(K.split(':', 1)[1]))
            G.add(K, 'bj:numero', i(ch['n']))
            G.add(K, 'bj:etichetta', s(ch['label']))
            G.add(K, 'dcterms:isPartOf', L)
            G.add(K, 'bj:inLibro', L)


def pagine(G, data):
    nums = set(v['page'] for v in data['verses'])
    for k in ('notes', 'mrefs', 'pericopes', 'divisions'):
        nums.update(x['page'] for x in data[k])
    nums.update(p['page'] for x in data['intros'] for p in x['paragraphs'])
    for n in sorted(nums):
        P = pagina(n)
        G.add(P, 'rdf:type', 'bj:Pagina')
        G.add(P, 'rdfs:label', s('p. %d' % n))
        G.add(P, 'bj:numero', i(n))
        G.add(P, 'bj:paginaPdf', i(n + PAGINA_PDF))


def stampato(G, X, page):
    G.add(X, 'bj:pagina', i(page))
    G.add(X, 'prov:wasDerivedFrom', pagina(page))


def html(G, X, text, markup):
    if markup != text:
        G.add(X, 'bj:testoHtml', s(markup))


def innermost(divisioni, order, v):
    """The deepest division of the book holding verse v (the latest when two are as deep)."""
    best = None
    for d in divisioni:
        if order[d['first']] <= order[v] <= order[d['last']]:
            if best is None or d['level'] >= best['level']:
                best = d
    return best


def divisioni_e_pericopi(G, data, order):
    per_libro = defaultdict(list)
    for d in data['divisions']:
        per_libro[d['book']].append(d)
        D = iri('divisione', d['id'].split(':', 1)[1])
        G.add(D, 'rdf:type', 'bj:Divisione')
        G.add(D, 'rdfs:label', it(d['title']))
        G.add(D, 'dcterms:title', it(d['title']))
        G.add(D, 'dcterms:identifier', s(d['id']))
        if d['short']:
            G.add(D, 'bj:titoloBreve', it(d['short']))
        html(G, D, d['title'], d['title_html'])
        G.add(D, 'bj:livello', i(d['level']))
        G.add(D, 'bj:inLibro', iri('libro', d['book']))
        if d['parent']:
            G.add(D, 'bj:inDivisione', iri('divisione', d['parent'].split(':', 1)[1]))
        G.add(D, 'bj:inizio', verso(d['first']))
        G.add(D, 'bj:fine', verso(d['last']))
        stampato(G, D, d['page'])
    for p in data['pericopes']:
        P = iri('pericope', p['id'].split(':', 1)[1])
        G.add(P, 'rdf:type', 'bj:Pericope')
        G.add(P, 'rdfs:label', it(p['title']))
        G.add(P, 'dcterms:title', it(p['title']))
        G.add(P, 'dcterms:identifier', s(p['id']))
        if p['short']:
            G.add(P, 'bj:titoloBreve', it(p['short']))
        html(G, P, p['title'], p['title_html'])
        G.add(P, 'bj:inLibro', iri('libro', p['book']))
        d = innermost(per_libro[p['book']], order, p['first'])
        if d:
            G.add(P, 'bj:inDivisione', iri('divisione', d['id'].split(':', 1)[1]))
        G.add(P, 'bj:inizio', verso(p['first']))
        G.add(P, 'bj:fine', verso(p['last']))
        if p['opens_chapter'] is not None:
            G.add(P, 'bj:apreCapitolo', i(p['opens_chapter']))
        G.add(P, 'bj:dentroVersetto', b(p['mid_verse']))
        stampato(G, P, p['page'])


def versetti(G, data, books):
    vs = sorted(data['verses'], key=lambda v: v['order'])
    for k, v in enumerate(vs):
        V = verso(v['id'])
        bk = books[v['book']]
        G.add(V, 'rdf:type', 'bj:Versetto')
        G.add(V, 'rdfs:label', s(etichetta_versetto(v, bk)))
        G.add(V, 'dcterms:identifier', s(v['id']))
        G.add(V, 'bj:etichetta', s(v['label']))
        G.add(V, 'bj:numero', i(v['verse']))
        if v['suffix']:
            G.add(V, 'bj:suffisso', s(v['suffix']))
        G.add(V, 'bj:numeroCapitolo', i(v['chapter']))
        G.add(V, 'bj:testo', it(v['text']))
        html(G, V, v['text'], v['html'])
        G.add(V, 'bj:ordine', i(v['order']))
        stampato(G, V, v['page'])
        G.add(V, 'bj:poesia', b(v['poetry']))
        G.add(V, 'dcterms:isPartOf', capitolo(v['book'], v['chapter']))
        G.add(V, 'bj:inLibro', iri('libro', v['book']))
        if v['pericope']:
            G.add(V, 'bj:inPericope', iri('pericope', v['pericope'].split(':', 1)[1]))
        if k + 1 < len(vs):
            G.add(V, 'bj:precede', verso(vs[k + 1]['id']))
        if k:
            G.add(V, 'bj:segue', verso(vs[k - 1]['id']))
        if v.get('omitted'):
            G.add(V, 'bj:omesso', b(True))
        if v.get('bracketed'):
            G.add(V, 'bj:traParentesi', b(True))
        if v.get('printed_in_chapter'):
            G.add(V, 'bj:stampatoNelCapitolo', i(v['printed_in_chapter']))
        if v.get('superscription'):
            G.add(V, 'bj:titoloSalmo', it(v['superscription']))
        for lettera in v.get('acrostic', []):
            G.add(V, 'bj:acrostico', s(lettera))


def introduzioni(G, data):
    for x in data['intros']:
        I = introduzione(x['id'])
        G.add(I, 'rdf:type', 'bj:Introduzione')
        G.add(I, 'rdfs:label', it(x['title']))
        G.add(I, 'dcterms:title', it(x['title']))
        G.add(I, 'dcterms:identifier', s(x['id']))
        G.add(I, 'bj:intestazione', s(x['heading']))
        G.add(I, 'bj:volume', s(x['volume']))
        for osis in x['books']:
            G.add(I, 'bj:introduce', iri('libro', osis))
        for p in x['paragraphs']:
            P = paragrafo(x['id'], p['n'])
            G.add(P, 'rdf:type', 'bj:Paragrafo')
            G.add(P, 'rdfs:label', s('%s, %d' % (x['title'], p['n'])))
            G.add(P, 'dcterms:identifier', s('%s.%d' % (x['id'], p['n'])))
            G.add(P, 'dcterms:isPartOf', I)
            G.add(P, 'bj:numero', i(p['n']))
            if p['titoletto']:
                G.add(P, 'bj:titoletto', it(p['titoletto']))
            G.add(P, 'bj:testo', it(p['text']))
            html(G, P, p['text'], p['html'])
            stampato(G, P, p['page'])


# ---------------------------------------------------------------- notes, margins, links

class Passaggi:
    """The passages named by the links: (first, last) -> verse ids, described once."""

    def __init__(self, G, B, books):
        self.G, self.B, self.books = G, B, books
        self.fatti = {}
        self.libri = [bk['osis'] for bk in sorted(books.values(), key=lambda x: x['order'])]

    def versi(self, a, z):
        va, vz = self.B.verses[a], self.B.verses[z]
        if va['book'] == vz['book']:
            return [v['id'] for v in self.B.between(va['book'], va, vz)]
        out = [v['id'] for v in self.B.sorted[va['book']][self.B.rank[a]:]]
        for osis in self.libri[self.libri.index(va['book']) + 1:self.libri.index(vz['book'])]:
            out += [v['id'] for v in self.B.sorted[osis]]
        return out + [v['id'] for v in self.B.sorted[vz['book']][:self.B.rank[z] + 1]]

    def __call__(self, a, z):
        P = passaggio(a, z)
        if P not in self.fatti:
            va, vz = self.B.verses[a], self.B.verses[z]
            self.fatti[P] = self.versi(a, z)
            G = self.G
            G.add(P, 'rdf:type', 'bj:Passaggio')
            G.add(P, 'rdfs:label', s(etichetta_passaggio(va, vz, self.books)))
            G.add(P, 'dcterms:identifier', s(P.split(':', 1)[1]))
            G.add(P, 'oa:hasSource', iri('libro', va['book']))
            G.add(P, 'bj:inizio', verso(a))
            G.add(P, 'bj:fine', verso(z))
            for vid in self.fatti[P]:
                G.add(P, 'bj:comprende', verso(vid))
        return P


def note(G, data, label_links, passaggi):
    for n in data['notes']:
        N = nota(n['id'])
        anchor = verso(n['anchor'])
        sig = sigla_di(data, n['anchor'])
        G.add(N, 'rdf:type', 'bj:Nota')
        G.add(N, 'rdfs:label', s(('Nota %s %s' % (sig, n['label'])) if n['label'] else 'Nota ' + sig))
        G.add(N, 'dcterms:identifier', s(n['id']))
        if n['label']:
            G.add(N, 'bj:etichetta', s(n['label']))
        if n['sign']:
            G.add(N, 'bj:segno', s(n['sign']))
        G.add(N, 'oa:motivatedBy', 'oa:commenting')
        corpo = iri('corpo', N.split(':', 1)[1])
        G.add(N, 'oa:hasBody', corpo)
        html(G, N, n['text'], n['html'])
        G.add(N, 'bj:ambito', AMBITO[n['scope']])
        lk = label_links[n['id']]
        if n['scope'] == 'book':
            G.add(N, 'oa:hasTarget', iri('libro', n['target_book']))
        elif n['scope'] == 'chapter' and n['target_chapters']:
            for ch in n['target_chapters']:
                osis, c = ch.rsplit('.', 1)
                G.add(N, 'oa:hasTarget', capitolo(osis, 0 if c == R.PROLOGO else int(c)))
        else:
            for a, z in lk['ranges']:
                G.add(N, 'oa:hasTarget', passaggi(a, z))
        for t in n['targets']:
            G.add(N, 'bj:commenta', verso(t))
        G.add(N, 'bj:richiamataDa', anchor)
        G.add(N, 'bj:posizioneTesto', i(n['offset']))
        G.add(N, 'bj:posizioneHtml', i(n['html_offset']))
        if n['word']:
            G.add(N, 'bj:parolaPrecedente', s(n['word']))
        stampato(G, N, n['page'])
        G.add(anchor, 'bj:haNota', N)
        G.add(corpo, 'rdf:type', 'oa:TextualBody')
        G.add(corpo, 'rdf:value', s(n['text']))
        G.add(corpo, 'dc:format', s('text/plain'))
        G.add(corpo, 'dc:language', s('it'))


def sigla_di(data, vid, _cache={}):
    if not _cache:
        books = {bk['osis']: bk for bk in data['books']}
        _cache.update((v['id'], sigla(books[v['book']])) for v in data['verses'])
    return _cache[vid]


def margini(G, data):
    for m in data['mrefs']:
        M = margine(m['id'])
        G.add(M, 'rdf:type', 'bj:Margine')
        G.add(M, 'rdfs:label', s(m['raw']))
        G.add(M, 'dcterms:identifier', s(m['id']))
        G.add(M, 'bj:testo', s(m['raw']))
        G.add(M, 'bj:accantoA', verso(m['anchor']))
        G.add(M, 'bj:posizione', i(m['position']))
        G.add(M, 'bj:posizioneTesto', i(m['offset']))
        G.add(M, 'bj:posizioneHtml', i(m['html_offset']))
        if m['word']:
            G.add(M, 'bj:parolaPrecedente', s(m['word']))
        if m.get('printed_in_verse'):
            G.add(M, 'bj:stampatoNelVersetto', verso(m['printed_in_verse']))
        stampato(G, M, m['page'])


def riferimento(G, X, l, passaggi):
    """What a margin reference and a citation share: text, status, passages, signs."""
    G.add(X, 'rdfs:label', s(l['raw']))
    G.add(X, 'dcterms:identifier', s(l['id']))
    G.add(X, 'bj:testo', s(l['raw']))
    G.add(X, 'bj:stato', STATO[l['status']])
    for a, z in l['ranges']:                    # parts of one verse ("41,20a.20b") name it twice
        G.link(X, 'bj:aPassaggio', passaggi(a, z))
    if l.get('target_book'):
        G.add(X, 'bj:libroCitato', iri('libro', l['target_book']))
    G.add(X, 'bj:notaChiave', b(l['keynote']))
    G.add(X, 'bj:conParalleli', b('p' in l['flags']))
    ext = [f for f in l['flags'] if f in ('s', 'ss')]
    if ext:
        G.add(X, 'bj:estensione', s(ext[0]))
    if l['qualifier']:
        G.add(X, 'bj:qualificatore', s(l['qualifier']))
    if l['alt']:
        G.add(X, 'bj:numeroAlternativo', s(l['alt']))
    if l['reason']:
        G.add(X, 'bj:motivo', s(l['reason']))
    if l.get('inferred'):
        G.add(X, 'bj:interpretazione', s(l['inferred']))
    for nid in l['keynote_notes']:
        G.add(X, 'bj:mandaANota', nota(nid))
    for mid in l['keynote_mrefs']:
        G.add(X, 'bj:mandaAMargine', margine(mid))


def rimandi(G, links, passaggi):
    for l in links:
        X = rimando(l['id'])
        G.add(X, 'rdf:type', 'bj:Rimando')
        riferimento(G, X, l, passaggi)
        G.add(X, 'bj:posizione', i(l['id'].rsplit('#', 1)[1]))
        G.add(X, 'bj:nelMargine', margine(l['source']))
        G.add(X, 'bj:daVersetto', verso(l['source_verse']))
        G.add(X, 'bj:relazione', RELAZIONE[l['relation']])
        if l['sign']:
            G.add(X, 'bj:segno', s(l['sign']))
        if l.get('doublet_of'):
            G.add(X, 'bj:doppioneDelRimando', rimando(l['doublet_of']))
        if l['status'] not in ('resolved', 'partial') or l['relation'] not in DIRETTA:
            continue
        src = verso(l['source_verse'])
        chiave = set(l.get('keynote_verses', []))    # "17,8.23+": only 23 holds the key note
        for t in l['targets']:
            T = verso(t)
            if T == src:
                continue
            props = ['bj:rimandaA'] + ([DIRETTA[l['relation']]] if DIRETTA[l['relation']] else [])
            if t in chiave:
                props.append('bj:rinviaANotaChiave')
            for p in props:
                G.link(src, p, T)
                if p in SIMMETRICHE:
                    G.link(T, p, src)
                    G.link(T, 'bj:rimandaA', src)


def citazioni(G, links, passaggi):
    for l in links:
        X = citazione(l['id'])
        G.add(X, 'rdf:type', 'bj:Citazione')
        riferimento(G, X, l, passaggi)
        if l['kind'] == 'note-cites':
            G.add(X, 'bj:daNota', nota(l['source']))
            chi = nota(l['source'])
        else:
            iid, n = l['source'].rsplit('.', 1)
            G.add(X, 'bj:daParagrafo', paragrafo(iid, int(n)))
            chi = introduzione(iid)
        G.add(X, 'bj:posizioneTesto', i(l['offset']))
        G.add(X, 'bj:lunghezza', i(l['length']))
        G.add(X, 'bj:posizioneHtml', i(l['html_offset']))
        G.add(X, 'bj:fineHtml', i(l['html_end']))
        G.add(X, 'bj:conCf', b(l['cf']))
        if l['status'] in ('resolved', 'partial'):
            for t in l['targets']:
                G.link(chi, 'bj:citaVersetto', verso(t))


# ---------------------------------------------------------------- output

def esc(x):
    return x.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')


def espandi(curie):
    p, local = curie.split(':', 1)
    return PREFISSI[p] + local


def nt_term(o):
    if isinstance(o, str):
        return '<%s>' % espandi(o)
    kind, v = o
    if kind == 'i':
        return '"%d"^^<%s>' % (v, espandi('xsd:integer'))
    if kind == 'b':
        return '"%s"^^<%s>' % ('true' if v else 'false', espandi('xsd:boolean'))
    if kind in ('it', 'en'):
        return '"%s"@%s' % (esc(v), kind)
    return '"%s"' % esc(v)


def ttl_term(o):
    if isinstance(o, str):
        if o == 'rdf:type':
            return 'a'
        return o if PN_LOCAL.match(o.split(':', 1)[1]) else '<%s>' % espandi(o)
    kind, v = o
    if kind == 'i':
        return str(v)
    if kind == 'b':
        return 'true' if v else 'false'
    return nt_term(o)


def gz(path):
    return gzip.GzipFile(filename='', mode='wb', fileobj=open(path, 'wb'), mtime=0, compresslevel=9)


def scrivi(G):
    with gz(NT) as f:
        for sog, po in G.per.items():
            S = nt_term(sog)
            f.write(''.join('%s %s %s .\n' % (S, nt_term(p), nt_term(o)) for p, o in po).encode('utf-8'))
    with gz(TTL) as f:
        head = ['# La Bibbia di Gerusalemme: the verse graph (generated by tools/ontologia/rdf.py,',
                '# vocabulary in ontologia/bj-ontologia.ttl). Do not edit.']
        head += ['@prefix %s: <%s> .' % kv for kv in PREFISSI.items()]
        f.write(('\n'.join(head) + '\n').encode('utf-8'))
        for sog, po in G.per.items():
            per_pred = {}
            for p, o in po:
                per_pred.setdefault(p, []).append(ttl_term(o))
            body = ' ;\n    '.join('%s %s' % (ttl_term(p), ' , '.join(os_)) for p, os_ in per_pred.items())
            f.write(('\n%s %s .\n' % (ttl_term(sog), body)).encode('utf-8'))


def contesto(ont):
    """The JSON-LD context: prefixes, one term per bj: class and property, with the
    datatype or "@id" from the ontology, and the external properties used. A term may
    not also be a prefix: the page prefix is "pag" here, since "pagina" is bj:pagina,
    and "id" is "@id" (the one resource under id/, the Bible, has a full IRI)."""
    from rdflib import RDF, RDFS, OWL, URIRef
    xsd = PREFISSI['xsd']
    ctx = {'@version': 1.1}

    def term(name, value):
        if name in ctx:
            raise ValueError('JSON-LD term %r defined twice' % name)
        ctx[name] = value

    term('id', '@id')
    term('tipo', '@type')
    for k, v in PREFISSI.items():
        if k != 'id':
            term('pag' if k == 'pagina' else k, v)
    for t in sorted(set(ont.subjects(RDF.type, None)), key=str):
        if not isinstance(t, URIRef) or not str(t).startswith(BJ):
            continue
        name = str(t)[len(BJ):]
        tipi = set(ont.objects(t, RDF.type))
        rng = str(ont.value(t, RDFS.range) or '')
        if OWL.ObjectProperty in tipi:
            term(name, {'@id': 'bj:' + name, '@type': '@id'})
        elif OWL.DatatypeProperty in tipi and rng in (xsd + 'integer', xsd + 'boolean'):
            term(name, {'@id': 'bj:' + name, '@type': 'xsd:' + rng[len(xsd):]})
        elif OWL.DatatypeProperty in tipi and rng.endswith('#langString'):
            term(name, {'@id': 'bj:' + name, '@language': 'it'})
        else:
            term(name, 'bj:' + name)                    # strings, classes, SKOS concepts
    term('testoIt', {'@id': 'bj:testo', '@language': 'it'})     # verse and paragraph text
    for name, curie in [('isPartOf', 'dcterms:isPartOf'), ('hasTarget', 'oa:hasTarget'),
                        ('hasBody', 'oa:hasBody'), ('hasSource', 'oa:hasSource'),
                        ('motivatedBy', 'oa:motivatedBy'), ('wasDerivedFrom', 'prov:wasDerivedFrom'),
                        ('cites', 'cito:cites')]:
        term(name, {'@id': curie, '@type': '@id'})
    for name, curie in [('label', 'rdfs:label'), ('title', 'dcterms:title'),
                        ('identifier', 'dcterms:identifier'), ('value', 'rdf:value'),
                        ('format', 'dc:format'), ('language', 'dc:language')]:
        term(name, curie)
    return {'@context': ctx}


def void(G, tipi):
    """The VoID description of the data graph: what it is, where it comes from, its
    dumps and vocabularies, and how many triples, resources, classes and properties it
    has (one partition per class and per property, with IRIs: no blank nodes)."""
    D = '<%sdati>' % SITO
    per_prop = Counter(p for po in G.per.values() for p, o in po)
    tipizzati = sum(1 for po in G.per.values() if any(p == 'rdf:type' for p, o in po))

    def nome(curie):
        return curie.replace(':', '-')

    out = ['# VoID description of ontologia/bj-dati.{ttl,nt}.gz (generated by tools/ontologia/rdf.py).',
           '# Do not edit.']
    out += ['@prefix %s: <%s> .' % kv for kv in PREFISSI.items() if kv[0] in
            ('bj', 'rdf', 'rdfs', 'xsd', 'owl', 'dcterms', 'skos', 'oa', 'cito', 'prov', 'dc', 'verso')]
    out += ['@prefix void: <http://rdfs.org/ns/void#> .', '@prefix vp: <%svoid#> .' % SITO, '']
    out += [D + ' a void:Dataset ;',
            '    dcterms:title "La Bibbia di Gerusalemme: il grafo dei versetti"@it , '
            '"La Bibbia di Gerusalemme: the verse graph"@en ;',
            '    dcterms:description "Versetti, note, rimandi a margine e citazioni della Bibbia di '
            'Gerusalemme (EDB: testo CEI 2008, note e rimandi della Bible de Jérusalem), '
            'collegati al versetto."@it , "Verses, notes, margin references and citations of La Bibbia '
            'di Gerusalemme (EDB: CEI 2008 text, Bible de Jérusalem notes and margins), linked at the '
            'verse."@en ;',
            '    dcterms:rights "Testo e note protetti da diritto d\'autore (EDB): solo per uso '
            'locale, non pubblicare."@it , "The text and notes are copyrighted (EDB): local use only, '
            'do not publish."@en ;',
            '    dcterms:creator "Massimo Nocentini" ;',
            '    dcterms:source "progetti/<volume>/*.tex (14 volumi corretti / 14 proofread volumes)" ;',
            '    void:vocabulary <%sontologia> , <http://www.w3.org/ns/oa#> , <http://purl.org/spar/cito/> , '
            '<http://purl.org/dc/terms/> , <http://www.w3.org/ns/prov#> , '
            '<http://www.w3.org/2004/02/skos/core#> ;' % SITO,
            '    void:uriSpace "%s" ;' % ID,
            '    void:dataDump <%sbj-dati.nt.gz> , <%sbj-dati.ttl.gz> ;' % (SITO, SITO),
            '    void:feature <http://www.w3.org/ns/formats/N-Triples> , <http://www.w3.org/ns/formats/Turtle> ;',
            '    void:exampleResource verso:John.3.16 , verso:Gen.1.1 ;',
            '    void:triples %d ;' % len(G),
            '    void:distinctSubjects %d ;' % len(G.per),
            '    void:entities %d ;' % tipizzati,
            '    void:classes %d ;' % len(tipi),
            '    void:properties %d ;' % len(per_prop),
            '    void:classPartition %s ;' % ' , '.join('vp:classe-' + nome(c) for c in sorted(tipi)),
            '    void:propertyPartition %s .' % ' , '.join('vp:proprieta-' + nome(p) for p in sorted(per_prop))]
    for c in sorted(tipi):
        out.append('vp:classe-%s void:class %s ; void:entities %d .' % (nome(c), c, tipi[c]))
    for p in sorted(per_prop):
        out.append('vp:proprieta-%s void:property %s ; void:triples %d .' % (nome(p), p, per_prop[p]))
    with open(VOID, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    from rdflib import Graph, Literal, URIRef
    g = Graph().parse(VOID, format='turtle')
    n = g.value(URIRef(D[1:-1]), URIRef('http://rdfs.org/ns/void#triples'))
    return [] if n == Literal(len(G)) else ['%s: void:triples %s, graph %d' % (VOID, n, len(G))]


# ---------------------------------------------------------------- checks

def checks(G, ont, data, coll, passaggi):
    from rdflib import RDF, RDFS, OWL, URIRef
    err = []
    dichiarati = {str(t)[len(BJ):]: set(ont.objects(t, RDF.type)) for t in ont.subjects(RDF.type, None)
                  if isinstance(t, URIRef) and str(t).startswith(BJ)}
    for name in sorted(dichiarati):
        t = URIRef(BJ + name)
        for p in (RDFS.label, RDFS.comment):
            langs = {o.language for o in ont.objects(t, p)}
            if not {'it', 'en'} <= langs:
                err.append('bj:%s: %s without it/en' % (name, p.n3(ont.namespace_manager)))
    rng = {str(t)[len(BJ):]: str(ont.value(URIRef(BJ + str(t)[len(BJ):]), RDFS.range) or '')
           for t in ont.subjects(RDF.type, OWL.DatatypeProperty) if str(t).startswith(BJ)}
    attesi = {'i': 'integer', 'b': 'boolean', 'it': 'langString', 's': 'string'}
    usati, nostri = Counter(), set(G.per)
    for sog, po in G.per.items():
        for p, o in po:
            if p.startswith('bj:'):
                usati[p] += 1
            if isinstance(o, str):
                if o.startswith('bj:'):
                    usati[o] += 1
                if o.split(':', 1)[0] in RISORSE + ['id'] and o not in nostri:
                    err.append('dangling object %s (%s %s)' % (o, sog, p))
            name = p[3:] if p.startswith('bj:') else None
            if name and name in dichiarati:
                if OWL.ObjectProperty in dichiarati[name] and not isinstance(o, str):
                    err.append('%s %s: literal for an object property' % (sog, p))
                if OWL.DatatypeProperty in dichiarati[name]:
                    if isinstance(o, str):
                        err.append('%s %s: IRI for a datatype property' % (sog, p))
                    elif rng.get(name) and not rng[name].endswith(attesi[o[0]]):
                        err.append('%s %s: %s literal, range %s' % (sog, p, o[0], rng[name]))
    for t in sorted(usati):
        if t[3:] not in dichiarati:
            err.append('%s used but not declared in the ontology' % t)
    tipi = Counter(o for po in G.per.values() for p, o in po if p == 'rdf:type')
    attese = dict(Versetto=len(data['verses']), Libro=len(data['books']), Nota=len(data['notes']),
                  Margine=len(data['mrefs']), Pericope=len(data['pericopes']),
                  Divisione=len(data['divisions']), Introduzione=len(data['intros']),
                  Paragrafo=sum(len(x['paragraphs']) for x in data['intros']),
                  Capitolo=sum(len(bk['chapters']) for bk in data['books']),
                  Rimando=sum(1 for l in coll['links'] if l['kind'] == 'mref'),
                  Citazione=sum(1 for l in coll['links'] if l['kind'].endswith('-cites')))
    for k, n in attese.items():
        if tipi['bj:' + k] != n:
            err.append('bj:%s: %d resources, %d in the JSON' % (k, tipi['bj:' + k], n))
    for l in coll['links']:
        if l['kind'] == 'note-label' and (l['scope'] == 'book' or l['scope'] == 'chapter' and l['target_chapters']):
            continue                            # targets chapters or the book, not passages
        got = set(v for a, z in l['ranges'] for v in passaggi.fatti[passaggio(a, z)])
        if got != set(l['targets']):
            err.append('%s: passages hold %d verses, targets %d' % (l['id'], len(got), len(l['targets'])))
    if G.doppi:
        err.append('%d duplicate triples' % G.doppi)
    return err, tipi, usati


def main(a):
    quiet = '-q' in a
    t0 = time.time()
    from rdflib import Graph
    ont = Graph().parse(ONTOLOGIA, format='turtle')
    data = json.load(open(BIBBIA, encoding='utf-8'))
    coll = json.load(open(COLLEGAMENTI, encoding='utf-8'))
    B = R.Bibbia(data)
    books = {bk['osis']: bk for bk in data['books']}
    order = {v['id']: v['order'] for v in data['verses']}
    G = Grafo()
    struttura(G, data)
    divisioni_e_pericopi(G, data, order)
    pagine(G, data)
    versetti(G, data, books)
    introduzioni(G, data)
    passaggi = Passaggi(G, B, books)
    links = coll['links']
    note(G, data, {l['source']: l for l in links if l['kind'] == 'note-label'}, passaggi)
    margini(G, data)
    rimandi(G, [l for l in links if l['kind'] == 'mref'], passaggi)
    citazioni(G, [l for l in links if l['kind'].endswith('-cites')], passaggi)
    err, tipi, usati = checks(G, ont, data, coll, passaggi)
    scrivi(G)
    err += void(G, tipi)
    with open(CONTESTO, 'w', encoding='utf-8') as f:
        json.dump(contesto(ont), f, ensure_ascii=False, indent=1)
        f.write('\n')
    if not quiet:
        print('resources: ' + ', '.join('%s %d' % (k, n) for k, n in tipi.most_common()))
        print('bj: properties: ' + ', '.join('%s %d' % kv for kv in usati.most_common() if kv[0][3].islower()))
    print('triples: %d (%d subjects, %d passages); %s %.1f MB, %s %.1f MB; %.1f s' % (
        len(G), len(G.per), len(passaggi.fatti), os.path.relpath(TTL, C), os.path.getsize(TTL) / 1e6,
        os.path.relpath(NT, C), os.path.getsize(NT) / 1e6, time.time() - t0))
    for e in err[:30]:
        print('ERROR  ' + e)
    print('checks: %s' % ('ok' if not err else '%d errors' % len(err)))
    return 1 if err else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
