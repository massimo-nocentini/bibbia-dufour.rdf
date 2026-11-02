"""Build the RDF graph of the verse ontology from the JSON files of stages 1, 2 and 2b.

usage: rdf.py [-q]

Reads ontologia/build/bibbia.json (estrai.py), ontologia/build/collegamenti.json
(riferimenti.py) and ontologia/build/dufour.json (dufour.py) and writes, in the
vocabulary of ontologia/bj-ontologia.ttl:
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

The Dizionario di Teologia Biblica (dufour.json) goes into the same graph: the work
(bj:Dizionario, also the skos:ConceptScheme), its 70 collaborators and 2 translators
(foaf:Person), its printed pages (bj:PaginaDizionario), every entry (bj:Voce, a
skos:Concept; redirects also bj:VoceRinvio, whose headword is an skos:altLabel of their
target when they have only one), its sections and paragraphs (dcterms:isPartOf chain,
bj:nellaVoce), every link between entries (bj:CollegamentoVoce, shortcuts
bj:richiamaVoce / bj:vediAncheVoce / bj:rinviaAVoce under skos:related, stored in both
directions) and every Bible citation (bj:Citazione to bj:Passaggio, like the BJ notes),
with the shortcuts bj:voceCitaVersetto and its inverse bj:citatoNellaVoce. Data IRIs:
id/voce/<slug>, id/voce/<slug>/sezione/<path>, .../paragrafo/<n>, .../citazione/<n>,
.../collegamento/<n>, id/persona/<id>, id/dizionario/pagina/<n>, id/dizionario.

The quotations (build/discorsi.json, virgolette.py: the text between « and », by the rules of the italic
of the Tufte edition) are bj:Discorso: id/discorso/<verse id>.<n> for the text of the books, else
id/discorso/<kind>/<local>.<n> (nota/Gen.1.2.1, paragrafo/pentateuco.3.1, ...), with their ends
(bj:iniziaIn, bj:inizioCarattere, bj:finisceIn, bj:fineCarattere), bj:parte, oa:hasSource, bj:dentroDi,
bj:attraversa (the verses spanned), bj:lunghezza, bj:testo when at most TESTO_DISCORSO characters,
bj:sbilanciato and bj:motivo; they count in the subset of the resource they are read in.

The time line (build/eventi.json, eventi.py): every dated event in one order. The chronology entries, the
persons of the dynasties, the datings of the books and the maps are already resources and take on themselves
their place (bj:posizioneLinea), years (bj:annoInizio, bj:annoFine), precision, era rule, period and the
same-event links; a date read in a note, an introduction, a front-matter text or a paragraph of the dictionary
is a bj:EventoDatato: id/evento/<source>/<offset> (evento:nota/Exod.2.10/474, evento:paragrafo/storici.16/2202,
evento:voce/gerusalemme/paragrafo/2/95), an oa:SpecificResource of its source with the date as printed, the
sentence, its citations and their verses, the anchor verse of a note. Counted in the subset of its source.

No blank nodes: every resource has an IRI under ID, so the graph can be compared as a
set of triples. Output is deterministic (same order, gzip without timestamps).

Checks (exit status 1 if any fails): every bj: term used is declared in the ontology,
and every declared term has an Italian and English rdfs:label and rdfs:comment; object
properties have IRIs as objects and datatype properties literals of their range; every
IRI of the data that is an object is also described; resource counts equal the JSON
counts (dictionary included); the verses of the passages of each link and citation equal
its targets; no duplicate triples.
"""
import gzip
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402
import virgolette  # noqa: E402

OUT = os.path.join(C, 'ontologia')
BIBBIA = os.path.join(OUT, 'build', 'bibbia.json')
COLLEGAMENTI = os.path.join(OUT, 'build', 'collegamenti.json')
PARATESTO = os.path.join(OUT, 'build', 'paratesto.json')
DUFOUR = os.path.join(OUT, 'build', 'dufour.json')
DISCORSI = os.path.join(OUT, 'build', 'discorsi.json')
EVENTI = os.path.join(OUT, 'build', 'eventi.json')
TESTO_DISCORSO = 200        # a quotation's words as bj:testo only up to this many characters (README)
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
           'paragrafo', 'nota', 'corpo', 'margine', 'rimando', 'citazione', 'passaggio', 'discorso']
# the dictionary: id/voce/<slug>[/sezione|paragrafo|citazione|collegamento/...], people, pages
RISORSE_DIZIONARIO = [('voce', ID + 'voce/'), ('persona', ID + 'persona/'),
                      ('pagdiz', ID + 'dizionario/pagina/')]
# the front matter and the appendices (paratesto.json), and the acrostic letters of the verses
RISORSE_PARATESTO = [('testopre', ID + 'testo/'), ('canone', ID + 'canone/'), ('abbreviazione', ID + 'abbreviazione/'),
                     ('manoscritto', ID + 'manoscritto/'), ('xilografia', ID + 'xilografia/'),
                     ('indice', ID + 'indice/'), ('cronologia', ID + 'cronologia/'), ('dinastia', ID + 'dinastia/'),
                     ('acr', ID + 'acrostico/'), ('pagprel', ID + 'preliminari/pagina/'),
                     ('pagapp', ID + 'appendici/pagina/')]
# the links between the parts and the corrections (integrazione.json, stage 2d)
RISORSE_INTEGRAZIONE = [('allineamento', ID + 'allineamento/'), ('intervento', ID + 'intervento/'),
                        ('versione', ID + 'versione/'), ('schemanum', ID + 'numerazione/'),
                        ('calendario', ID + 'calendario/'), ('misura', ID + 'misura/'), ('carta', ID + 'carta/')]
# the dates read in free text, on the time line (eventi.json, stage 2f)
RISORSE_EVENTI = [('evento', ID + 'evento/')]
PREFISSI = dict([
    ('bj', BJ), ('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
    ('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('xsd', 'http://www.w3.org/2001/XMLSchema#'),
    ('owl', 'http://www.w3.org/2002/07/owl#'), ('dcterms', 'http://purl.org/dc/terms/'),
    ('dc', 'http://purl.org/dc/elements/1.1/'), ('skos', 'http://www.w3.org/2004/02/skos/core#'),
    ('oa', 'http://www.w3.org/ns/oa#'), ('cito', 'http://purl.org/spar/cito/'),
    ('prov', 'http://www.w3.org/ns/prov#'), ('id', ID)] + [(r, ID + r + '/') for r in RISORSE]
    + RISORSE_DIZIONARIO + [('foaf', 'http://xmlns.com/foaf/0.1/')] + RISORSE_PARATESTO
    + [('schema', 'https://schema.org/')] + RISORSE_INTEGRAZIONE + [('unit', 'http://qudt.org/vocab/unit/')]
    + RISORSE_EVENTI)
NOSTRI = RISORSE + ['id'] + [k for k, _ in RISORSE_DIZIONARIO + RISORSE_PARATESTO + RISORSE_INTEGRAZIONE
                             + RISORSE_EVENTI]
INTEGRAZIONE = os.path.join(OUT, 'build', 'integrazione.json')   # prefixes of described resources

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
# the Hebrew letters of the acrostics as printed (Iad: Lam 4,10 as printed, for Iod; Śin = Sin)
ALFABETO = {n: (k, ch) for k, (n, ch) in enumerate(zip(
    'Alef Bet Ghimel Dalet He Vau Zain Het Tet Iod Caf Lamed Mem Nun Samec Ain Pe Sade Kof Res Sin Tau'.split(),
    'אבגדהוזחטיכלמנסעפצקרשת'), 1)}
ALFABETO.update({'Iad': ALFABETO['Iod'], 'Śin': ALFABETO['Sin']})
PAGINA_PDF_DIZIONARIO = 21           # PDF page from 1; the Dufour corpus's 0-based index is page + 20

# the dictionary as a work, from its title page (../dufour/corpus/data/front/frontespizio.txt)
DIZIONARIO = {
    'titolo': 'Dizionario di Teologia Biblica',
    'originale': 'Vocabulaire de Théologie Biblique',
    'editore': 'Marietti',
    'anno': '1976',
    'edizione': 'V edizione 1976 riveduta e corretta, ristampa 2002; edizione italiana completamente '
                'rifusa sulla II edizione francese riveduta e ampliata (Les Éditions du Cerf, Paris)',
    'citazione': 'X. Léon-Dufour (ed.), Dizionario di Teologia Biblica, ed. italiana a cura di G. Viola '
                 'e A. Milanoli, V ed. 1976, ristampa 2002, Marietti, Genova',
    'curatori': ['xavier-leon-dufour', 'jean-duplacy', 'augustin-george', 'pierre-grelot',
                 'jacques-guillet', 'marc-francois-lacan'],
    'traduttori': [('giovanni-viola', 'Giovanni', 'Viola'), ('ambretta-milanoli', 'Ambretta', 'Milanoli')],
}
TIPO_COLLEGAMENTO = {'star': ('bj:collegamentoAsterisco', 'bj:richiamaVoce'),
                     'seealso': ('bj:collegamentoVediAnche', 'bj:vediAncheVoce'),
                     'redirect': ('bj:collegamentoRinvio', 'bj:rinviaAVoce')}

# a literal is a tuple (kind, value): s string, it/en/fr text in that language, i integer,
# b boolean, y year (xsd:gYear)
XSD = {'i': 'xsd:integer', 'b': 'xsd:boolean'}
LINGUE = ('it', 'en', 'fr', 'he-Latn', 'grc-Latn', 'la')     # language-tagged literals (kind = the tag)
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
    """Triples grouped by subject, in the order they are added (the output order). Each
    triple is counted in the part being built (`parte`: the Bible, then the dictionary),
    and each subject belongs to the part that described it first (VoID subsets)."""

    def __init__(self):
        self.per = {}
        self.visti = set()
        self.doppi = 0
        self.parte = 'bibbia'
        self.per_parte = Counter()
        self.per_parte_prop = Counter()
        self.parte_di = {}

    def add(self, sog, pred, ogg):
        if ogg is None:
            return
        t = (sog, pred, ogg)
        if t in self.visti:
            self.doppi += 1
            return
        self.visti.add(t)
        self.per_parte[self.parte] += 1
        self.per_parte_prop[self.parte, pred] += 1
        if sog not in self.per:
            self.parte_di[sog] = self.parte
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


# the kinds of reason of an unresolved or partial reference (R2-11), from its text or the dictionary's kind
MOTIVI = [(r'extra-canonical', 'bj:motivoExtracanonico'), (r'^no (?:chapter|verse)|out-of-range', 'bj:motivoFuoriIntervallo'),
          (r'misprinted range|reversed', 'bj:motivoIntervalloErrato'), (r'not understood', 'bj:motivoNonCompreso'),
          (r'Vulgate|numbering|no CEI', 'bj:motivoAltraNumerazione'), (r'ambiguous', 'bj:motivoLibroAmbiguo')]
QUALIFICATORI = {}          # qualifier of a reference -> the version it names (integrazione.json)


def categoria_motivo(reason, kind=None):
    for pat, c in MOTIVI:
        if re.search(pat, kind or '') or re.search(pat, reason):
            return c
    return 'bj:motivoAltro'


def nome_sottovoce(lemma, label, _minuscole={}):
    """The self-contained label of an index sub-entry (R2-08): «Lemma: label», the leading dash of the
    print dropped and an inner one (the headword's place) replaced by it; a first word that the
    Bible text writes in lower case is lowered («Amicizia: tra Davide e Giònata»)."""
    t = label.strip()
    t = re.sub(r'^[-–]\s*', '', t)
    segno = re.compile(r'(?<=[\s’\'(«])[-–](?=[\s,;.)»]|$)')
    if len(segno.findall(t)) == 1:              # one dash stands for the headword; several are dashes of the text
        t = segno.sub(lambda m: lemma, t)
    w = re.match(r'(\w+)(.*)$', t, re.S)
    if w and w.group(1)[0].isupper() and w.group(1)[1:].islower() and _minuscole.get(w.group(1).lower(), 0) > \
            _minuscole.get(w.group(1), 0):
        t = w.group(1).lower() + w.group(2)
    return '%s: %s' % (lemma, t) if t else lemma


def conta_minuscole(data):
    c = Counter(m for v in data['verses'] for m in re.findall(r'\w+', v['text']))
    nome_sottovoce.__defaults__[0].update(c)


# ---------------------------------------------------------------- structure

def struttura(G, data):
    G.add('id:bibbia', 'rdf:type', 'bj:Bibbia')
    G.add('id:bibbia', 'dcterms:title', it('La Bibbia di Gerusalemme'))
    G.add('id:bibbia', 'rdfs:label', it('La Bibbia di Gerusalemme'))
    G.add('id:bibbia', 'dcterms:identifier', s('bibbia'))
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
        G.add(P, 'dcterms:identifier', s('pagina.%d' % n))
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
        tonde = v.get('acrostic_brackets') or [False] * len(v.get('acrostic', []))
        for k, (nome, rigo, tonda) in enumerate(zip(v.get('acrostic', []), v.get('acrostic_lines', []), tonde), 1):
            G.add(V, 'bj:acrostico', s(nome))
            A = iri('acr', '%s.%d' % (v['id'], k))
            G.add(V, 'bj:haLetteraAcrostica', A)
            G.add(A, 'rdf:type', 'bj:LetteraAcrostica')
            G.add(A, 'rdfs:label', it('%s (%s)' % ('(%s)' % nome if tonda else nome, etichetta_versetto(v, bk))))
            G.add(A, 'dcterms:identifier', s('acr:%s.%d' % (v['id'], k)))
            G.add(A, 'bj:inVersetto', V)
            stampato(G, A, v['page'])
            G.add(A, 'bj:testo', s(nome))
            G.add(A, 'bj:letteraEbraica', s(ALFABETO[nome][1]))
            G.add(A, 'bj:posizioneAlfabeto', i(ALFABETO[nome][0]))
            G.add(A, 'bj:rigo', i(rigo))
            G.add(A, 'bj:ordine', i(k))
            if tonda:                                   # printed in parentheses: \acrostico{(Mem)}
                G.add(A, 'bj:mancanteNelTesto', b(True))


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
        if l['qualifier'] in QUALIFICATORI:         # the version it names (R2-16)
            G.add(X, 'bj:secondoVersione', QUALIFICATORI[l['qualifier']])
    if l['alt']:
        G.add(X, 'bj:numeroAlternativo', s(l['alt']))
    if l['reason']:
        G.add(X, 'bj:motivo', s(l['reason']))
        G.add(X, 'bj:categoriaMotivo', categoria_motivo(l['reason'], l.get('reason_kind')))
    if l.get('inferred'):
        G.add(X, 'bj:interpretazione', s(l['inferred']))
    elif l.get('corrected'):                    # read in the sense of the sentence (riferimenti.py)
        G.add(X, 'bj:interpretazione', s('%s: %s' % (l['corrected'], l['why'])))
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


# ---------------------------------------------------------------- the dictionary (dufour.json)

CF = re.compile(r'\bcfr?\.\s*$', re.I)


def voce(slug):
    return iri('voce', slug)


def tratto(path):
    """A section path as an IRI segment: ASCII letters and digits joined by "-"
    ("VT I 2" -> VT-I-2, "introd. 2 a" -> introd-2-a, "VT «Segno di ...»" -> VT-Segno-di-...)."""
    ascii_ = unicodedata.normalize('NFKD', path).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', ascii_).strip('-')


def sezione(slug, path):
    return iri('voce', '%s/sezione/%s' % (slug, tratto(path)))


def paragrafo_voce(pid):
    slug, n = pid.rsplit('.', 1)
    return iri('voce', '%s/paragrafo/%s' % (slug, n))


def citazione_voce(cid):
    slug, n = cid.rsplit('#', 1)
    return iri('voce', '%s/citazione/%s' % (slug, n))


def persona(pid):
    return iri('persona', pid)


def pagina_dizionario(n):
    return iri('pagdiz', n)


def stampato_dizionario(G, X, page):
    G.add(X, 'bj:pagina', i(page))
    G.add(X, 'prov:wasDerivedFrom', pagina_dizionario(int(page)))


def locale(X):
    return X.split(':', 1)[1]


def opera(G, dz):
    """The work and the people: title-page data, editors, translators, collaborators."""
    D, W = 'id:dizionario', DIZIONARIO
    G.add(D, 'rdf:type', 'bj:Dizionario')
    G.add(D, 'rdf:type', 'skos:ConceptScheme')
    G.add(D, 'rdfs:label', it(W['titolo']))
    G.add(D, 'dcterms:title', it(W['titolo']))
    G.add(D, 'dcterms:alternative', ('fr', W['originale']))
    G.add(D, 'dcterms:identifier', s('dizionario'))
    G.add(D, 'dcterms:publisher', s(W['editore']))
    G.add(D, 'dcterms:issued', ('y', W['anno']))
    G.add(D, 'dcterms:language', s('it'))
    G.add(D, 'bj:edizione', s(W['edizione']))
    G.add(D, 'dcterms:bibliographicCitation', s(W['citazione']))
    G.add(D, 'dcterms:source', s('../dufour/corpus/data (Dizionario di Teologia Biblica.pdf, 812 pagine)'))
    G.add(D, 'dcterms:rights', it('Testo protetto da diritto d\'autore (Marietti): solo per uso locale, '
                                  'non pubblicare.'))
    G.add(D, 'dcterms:rights', ('en', 'The text is copyrighted (Marietti): local use only, do not publish.'))
    for a in dz['meta']['authors']:
        P = persona(a['id'])
        G.add(P, 'rdf:type', 'foaf:Person')
        G.add(P, 'rdfs:label', s(a['name']))
        G.add(P, 'dcterms:identifier', s(a['id']))
        G.add(P, 'foaf:name', s(a['name']))
        G.add(P, 'foaf:givenName', s(a['given']))
        G.add(P, 'foaf:familyName', s(a['surname']))
        if a.get('order'):
            G.add(P, 'bj:ordineReligioso', s(a['order']))
        if a.get('place'):
            G.add(P, 'bj:sede', s(a['place']))
    for pid, nome, cognome in W['traduttori']:
        P = persona(pid)
        G.add(P, 'rdf:type', 'foaf:Person')
        G.add(P, 'rdfs:label', s('%s %s' % (nome, cognome)))
        G.add(P, 'dcterms:identifier', s(pid))
        G.add(P, 'foaf:name', s('%s %s' % (nome, cognome)))
        G.add(P, 'foaf:givenName', s(nome))
        G.add(P, 'foaf:familyName', s(cognome))
    for pid in W['curatori']:
        G.add(D, 'bj:curatore', persona(pid))
    for pid, _, _ in W['traduttori']:
        G.add(D, 'bj:traduttore', persona(pid))


def pagine_dizionario(G, dz):
    nums = set()
    for v in dz['voci']:
        nums.update(range(int(v['pages'][0]), int(v['pages'][1]) + 1))
        nums.update(int(x['page']) for x in v.get('sections', []) + v.get('paragraphs', []))
    for n in sorted(nums):
        P = pagina_dizionario(n)
        G.add(P, 'rdf:type', 'bj:PaginaDizionario')
        G.add(P, 'rdfs:label', s('DTB p. %d' % n))
        G.add(P, 'dcterms:identifier', s('pagdiz.%d' % n))
        G.add(P, 'bj:numero', i(n))
        G.add(P, 'bj:paginaPdf', i(n + PAGINA_PDF_DIZIONARIO))
        G.add(P, 'dcterms:isPartOf', 'id:dizionario')
    return len(nums)


def parte_firmata(v, path):
    """The top-level section holding the section a signature follows ("VT 4" -> VT)."""
    padre = {x['path']: x['parent'] for x in v['sections']}
    while padre.get(path):
        path = padre[path]
    return path if path in padre else None


def autori(G, V, v):
    """dcterms:creator of the entry; an entry signed part by part (NOME: VT, NT) also has
    each signer as dcterms:creator of the top-level section that signature closes."""
    firme = []
    for a in v['authors']:
        G.add(V, 'dcterms:creator', persona(a['id']))
        if a['signature'] not in firme:
            firme.append(a['signature'])
    for f in firme:
        G.add(V, 'bj:firma', s(f))
    if len(firme) > 1:
        for a in v['authors']:
            top = parte_firmata(v, a['part'])
            if top:
                G.add(sezione(v['id'], top), 'dcterms:creator', persona(a['id']))


def sezioni_e_paragrafi(G, V, v):
    slug, nome = v['id'], v['headword']
    for k, x in enumerate(v['sections'], 1):
        S = sezione(slug, x['path'])
        G.add(S, 'rdf:type', 'bj:SezioneVoce')
        G.add(S, 'rdfs:label', s('%s %s' % (nome, x['path'])))
        G.add(S, 'dcterms:identifier', s(locale(S)))
        if x['title']:
            G.add(S, 'dcterms:title', it(x['title']))
            html(G, S, x['title'], x['title_html'])
        if x['label']:
            G.add(S, 'bj:etichetta', s(x['label']))
        G.add(S, 'bj:percorso', s(x['path']))
        G.add(S, 'bj:tipoSezione', s(x['kind']))
        G.add(S, 'bj:livello', i(x['depth']))
        G.add(S, 'bj:ordine', i(k))
        G.add(S, 'dcterms:isPartOf', sezione(slug, x['parent']) if x['parent'] else V)
        G.add(S, 'bj:nellaVoce', V)
        stampato_dizionario(G, S, x['page'])
    for p in v['paragraphs']:
        P = paragrafo_voce(p['id'])
        G.add(P, 'rdf:type', 'bj:ParagrafoVoce')
        G.add(P, 'rdfs:label', s('%s ¶ %d' % (nome if p['sec'] == '0' else '%s %s' % (nome, p['sec']), p['n'])))
        G.add(P, 'dcterms:identifier', s(p['id']))
        G.add(P, 'bj:numero', i(p['n']))
        G.add(P, 'bj:testo', it(p['text']))
        html(G, P, p['text'], p['html'])
        G.add(P, 'dcterms:isPartOf', V if p['sec'] == '0' else sezione(slug, p['sec']))
        G.add(P, 'bj:nellaVoce', V)
        stampato_dizionario(G, P, p['page'])


def voci(G, dz):
    """Every entry: a skos:Concept of the dictionary's scheme and its article."""
    D = 'id:dizionario'
    for k, v in enumerate(dz['voci'], 1):
        V = voce(v['id'])
        G.add(V, 'rdf:type', 'bj:Voce')
        G.add(V, 'rdf:type', 'skos:Concept')
        if v['kind'] == 'redirect':
            G.add(V, 'rdf:type', 'bj:VoceRinvio')
        G.add(V, 'rdfs:label', it(v['headword']))
        G.add(V, 'skos:prefLabel', it(v['headword']))
        G.add(V, 'dcterms:identifier', s(v['id']))
        G.add(V, 'skos:inScheme', D)
        G.add(V, 'skos:topConceptOf', D)
        G.add(D, 'skos:hasTopConcept', V)
        G.add(V, 'bj:lettera', s(v['letter']))
        G.add(V, 'bj:ordine', i(k))
        prima, ultima = int(v['pages'][0]), int(v['pages'][1])
        stampato_dizionario(G, V, prima)
        if ultima != prima:
            G.add(V, 'bj:paginaFinale', i(ultima))
        for n in range(prima + 1, ultima + 1):
            G.add(V, 'prov:wasDerivedFrom', pagina_dizionario(n))
        if v['kind'] == 'full':
            G.add(V, 'bj:numeroParole', i(v['words']))
            G.add(V, 'bj:testoRinvii', s(v['seealso']))
            sezioni_e_paragrafi(G, V, v)
        else:
            G.add(V, 'bj:testoRinvii', s(v['redirect']))
        autori(G, V, v)
    for v in dz['voci']:                       # a redirect to one entry only: the USE of a thesaurus
        mete = {t['voce'] for t in v['targets'] if t['voce']}
        if v['kind'] == 'redirect' and len(mete) == 1:
            G.add(voce(mete.pop()), 'skos:altLabel', it(v['headword']))


def sezione_di_arrivo(sezioni, path):
    """The target section of a "→" item: the path itself, or for "IV 0" (the opening of
    section IV) section IV; "0" (the opening of the entry) is the entry itself."""
    if path in sezioni:
        return path
    if path and path.endswith(' 0') and path[:-2] in sezioni:
        return path[:-2]
    return None


def collegamenti_voci(G, dz):
    """Every printed link between entries, reified, and its shortcut (self-links left out);
    skos:related is stored in both directions (it is symmetric)."""
    nomi = {v['id']: v['headword'] for v in dz['voci']}
    sezioni = {v['id']: {x['path'] for x in v.get('sections', [])} for v in dz['voci']}
    n = Counter()
    for l in dz['links']:
        src, T = l['source'], l['target']
        n[src] += 1
        V = voce(src)
        L = iri('voce', '%s/collegamento/%d' % (src, n[src]))
        tipo, diretta = TIPO_COLLEGAMENTO[l['type']]
        G.add(L, 'rdf:type', 'bj:CollegamentoVoce')
        G.add(L, 'rdfs:label', s('%s %s%s' % (nomi[src], '*' if l['type'] == 'star' else '→ ',
                                               l['form'] + (' ' + l['path'] if l.get('path') else ''))))
        G.add(L, 'dcterms:identifier', s(locale(L)))
        G.add(L, 'bj:tipoCollegamento', tipo)
        G.add(L, 'bj:daVoce', V)
        G.add(L, 'bj:nellaVoce', V)
        G.add(L, 'bj:forma', s(l['form']))
        G.add(L, 'bj:stato', 'bj:risolto' if T else 'bj:irrisolto')
        if l['type'] == 'star':
            if l['para']:
                G.add(L, 'bj:daParagrafo', paragrafo_voce(l['para']))
            else:
                G.add(L, 'bj:daSezione', sezione(src, l['sec']))
            if l['method']:
                G.add(L, 'bj:metodo', s(l['method']))
        else:
            if l['path']:
                G.add(L, 'bj:percorso', s(l['path']))
            if l['path_status']:
                G.add(L, 'bj:esitoPercorso', s(l['path_status']))
            sec = sezione_di_arrivo(sezioni[T], l['sec']) if T else None
            if sec:
                G.add(L, 'bj:aSezione', sezione(T, sec))
        if not T:
            continue
        G.add(L, 'bj:aVoce', voce(T))
        if T != src:
            G.link(V, diretta, voce(T))
            G.link(V, 'skos:related', voce(T))
            G.link(voce(T), 'skos:related', V)
    return n


def citazioni_voci(G, dz, passaggi):
    """Every Bible citation of the dictionary: a bj:Citazione from its paragraph (or the
    section title it stands in) to its passages, as for the BJ notes; the entry cites
    every verse of a resolved or partial one (bj:voceCitaVersetto, bj:citatoNellaVoce)."""
    testi = {p['id']: p['text'] for v in dz['voci'] for p in v.get('paragraphs', [])}
    titoli = {(v['id'], x['path']): x['title'] for v in dz['voci'] for x in v.get('sections', [])}
    for c in dz['citations']:
        X = citazione_voce(c['id'])
        V = voce(c['voce'])
        G.add(X, 'rdf:type', 'bj:Citazione')
        riferimento(G, X, dict(c, keynote=False, qualifier=None, alt=None, keynote_notes=[],
                               keynote_mrefs=[]), passaggi)
        if c['para']:
            G.add(X, 'bj:daParagrafo', paragrafo_voce(c['para']))
            testo = testi[c['para']]
        else:
            G.add(X, 'bj:daSezione', sezione(c['voce'], c['sec']))
            testo = titoli[c['voce'], c['sec']]
        G.add(X, 'bj:nellaVoce', V)
        G.add(X, 'bj:posizioneTesto', i(c['offset']))
        G.add(X, 'bj:lunghezza', i(c['length']))
        G.add(X, 'bj:posizioneHtml', i(c['html_offset']))
        G.add(X, 'bj:fineHtml', i(c['html_end']))
        G.add(X, 'bj:conCf', b(CF.search(testo[:c['offset']])))
        if '...' in c['flags']:
            G.add(X, 'bj:eAltrove', b(True))
        if c['implicit']:
            G.add(X, 'bj:libroImplicito', i(c['implicit']))
        if c.get('conversion'):
            G.add(X, 'bj:conversione', s(c['conversion']))
        if c.get('reason_kind'):
            G.add(X, 'bj:tipoMotivo', s(c['reason_kind']))
        if c['source_status'] != 'ok':
            G.add(X, 'bj:statoFonte', s(c['source_status']))
        if c['status'] in ('resolved', 'partial'):
            for t in c['targets']:
                G.link(V, 'bj:voceCitaVersetto', verso(t))
                G.link(verso(t), 'bj:citatoNellaVoce', V)


def dizionario(G, dz, passaggi):
    """The whole dictionary, counted as its own part of the graph (VoID subset)."""
    G.parte = 'dizionario'
    opera(G, dz)
    npagine = pagine_dizionario(G, dz)
    voci(G, dz)
    collegamenti_voci(G, dz)
    citazioni_voci(G, dz, passaggi)
    G.parte = 'bibbia'
    return npagine


# ---------------------------------------------------------------- the front matter and the appendices (paratesto.json)

PDF_PRELIMINARI = 5
PDF_APPENDICI = 3001
ROMANI = dict(i=1, v=5, x=10, l=50)
COLONNA = {'universale': 'bj:colonnaUniversale', 'palestina': 'bj:colonnaPalestina', 'israele': 'bj:colonnaIsraele',
           'giuda': 'bj:colonnaGiuda', 'egitto': 'bj:colonnaEgitto', 'lagidi': 'bj:colonnaLagidi',
           'seleucidi': 'bj:colonnaSeleucidi'}
INDICI = {'note': ('Indice alfabetico delle note più importanti', 'Alphabetical index of the most important notes'),
          'temi': ('Indice dei temi biblici d’interesse pastorale', 'Index of biblical themes of pastoral interest')}


def romano(x):
    n, prev = 0, 0
    for ch in reversed(x.lower()):
        v = ROMANI[ch]
        n, prev = (n - v, prev) if v < prev else (n + v, v)
    return n


class PaginePar:
    """The printed pages of the front matter (Roman) and of the appendices, described once."""

    def __init__(self, G):
        self.G, self.fatte = G, set()

    def preliminare(self, X, page):
        P = iri('pagprel', page)
        self.G.add(X, 'bj:pagina', i(romano(page)))
        self.G.add(X, 'prov:wasDerivedFrom', P)
        if P not in self.fatte:
            self.fatte.add(P)
            n = romano(page)
            self.G.add(P, 'rdf:type', 'bj:PaginaPreliminare')
            self.G.add(P, 'rdfs:label', s('p. %s' % page))
            self.G.add(P, 'dcterms:identifier', s('pagprel.%s' % page))
            self.G.add(P, 'bj:etichetta', s(page))
            self.G.add(P, 'bj:numero', i(n))
            self.G.add(P, 'bj:paginaPdf', i(n + PDF_PRELIMINARI))
            self.G.add(P, 'dcterms:isPartOf', 'id:edizione')

    def appendice(self, X, page):
        self.G.add(X, 'bj:pagina', i(page))
        self.G.add(X, 'prov:wasDerivedFrom', self.pagina_appendice(page))

    def pagina_appendice(self, page):
        P = iri('pagapp', page)
        if P not in self.fatte:
            self.fatte.add(P)
            self.G.add(P, 'rdf:type', 'bj:PaginaAppendice')
            self.G.add(P, 'rdfs:label', s('appendici, p. %d' % page))
            self.G.add(P, 'dcterms:identifier', s('pagapp.%d' % page))
            self.G.add(P, 'bj:numero', i(page))
            self.G.add(P, 'bj:paginaPdf', i(page + PDF_APPENDICI))
            self.G.add(P, 'dcterms:isPartOf', 'id:edizione')
        return P


def persona_semplice(G, pid, nome, cognome):
    P = persona(pid)
    if P not in G.per:
        G.add(P, 'rdf:type', 'foaf:Person')
        G.add(P, 'rdfs:label', s('%s %s' % (nome, cognome)))
        G.add(P, 'dcterms:identifier', s(pid))
        G.add(P, 'foaf:name', s('%s %s' % (nome, cognome)))
        G.add(P, 'foaf:givenName', s(nome))
        G.add(P, 'foaf:familyName', s(cognome))
    return P


def edizione_bj(G, ed, pg):
    E = 'id:edizione'
    G.add(E, 'rdf:type', 'bj:Edizione')
    G.add(E, 'rdfs:label', it('La Bibbia di Gerusalemme, EDB 2009'))
    G.add(E, 'dcterms:title', it(ed['title']))
    G.add(E, 'dcterms:identifier', s('edizione'))
    G.add(E, 'bj:edizioneDi', 'id:bibbia')
    G.add(E, 'dcterms:publisher', s(ed['publisher']))
    G.add(E, 'bj:luogo', s(ed['place']))
    G.add(E, 'bj:isbn', s(ed['isbn']))
    G.add(E, 'dcterms:issued', ('y', ed['printings'][0]['month'][:4]))
    G.add(E, 'dcterms:language', s('it'))
    for x in ed['sources']:
        G.add(E, 'dcterms:source', s(x))
    for x in ed['imprimatur']:
        G.add(E, 'bj:imprimatur', s(x))
    for x in ed['rights']:
        G.add(E, 'dcterms:rights', it(x))
    G.add(E, 'bj:stampatore', s(ed['printer']))
    G.add(E, 'bj:testo', it('\n'.join(ed['colophon'])))
    G.add(E, 'bj:direzioneEditoriale', persona_semplice(G, *ed['direction']))
    G.add(E, 'bj:curatore', persona_semplice(G, *ed['editor']))
    pg.preliminare(E, 'iv')
    for k, x in enumerate(ed['printings'], 1):
        S = iri('id', 'edizione/stampa/%d' % k)
        G.add(S, 'rdf:type', 'bj:Stampa')
        G.add(S, 'rdfs:label', it('%s: %s' % (x['label'], x['date'])))
        G.add(S, 'dcterms:identifier', s('edizione.stampa.%d' % k))
        G.add(S, 'bj:dataStampata', s(x['date']))
        G.add(S, 'dcterms:date', ('ym', x['month']))
        G.add(S, 'bj:ordine', i(k))
        G.add(S, 'bj:stampaDi', E)
        pg.preliminare(S, 'ii')


def testi_preliminari(G, P, pg):
    for x in P['testi']:
        T = iri('testopre', x['id'])
        G.add(T, 'rdf:type', 'bj:TestoPreliminare')
        G.add(T, 'rdfs:label', it(x['title']))
        G.add(T, 'dcterms:title', it(x['title']))
        G.add(T, 'dcterms:identifier', s(x['id']))
        if x['subtitle']:
            G.add(T, 'bj:sottotitolo', s(x['subtitle']))
        G.add(T, 'dcterms:isPartOf', 'id:edizione')
        G.add(T, 'bj:corsivo', b(x['italic']))
        if x['author']:
            a = x['author']
            G.add(T, 'dcterms:creator', persona_semplice(G, a['id'], a['given'], a['family']))
            G.add(T, 'bj:firma', s(x['signature']))
            for q in x['qualifica']:
                G.add(T, 'bj:qualifica', s(q))
        pg.preliminare(T, x['page'])
        for p in x['paragraphs']:
            X = iri('paragrafo', '%s.%d' % (x['id'], p['n']))
            G.add(X, 'rdf:type', 'bj:Paragrafo')
            G.add(X, 'rdfs:label', s('%s, %d' % (x['title'], p['n'])))
            G.add(X, 'dcterms:identifier', s('%s.%d' % (x['id'], p['n'])))
            G.add(X, 'dcterms:isPartOf', T)
            G.add(X, 'bj:numero', i(p['n']))
            if p['titoletto']:
                G.add(X, 'bj:titoletto', it(p['titoletto']))
            G.add(X, 'bj:testo', it(p['text']))
            html(G, X, p['text'], p['html'])
            pg.preliminare(X, p['page'])


def canoni(G, P, pg):
    titoli = {'ebraico': ('Divisione della Bibbia ebraica', 'divisione-ebraica', 'xx'),
              'greco': ('Divisione della Bibbia greca', 'divisione-greca', 'xxi')}
    for c in P['canoni']:
        tit, tid, page = titoli[c['id']]
        K = iri('canone', c['id'])
        G.add(K, 'rdf:type', 'bj:Canone')
        G.add(K, 'rdfs:label', it(tit))
        G.add(K, 'dcterms:title', it(tit))
        G.add(K, 'dcterms:identifier', s(c['id']))
        G.add(K, 'dcterms:isPartOf', iri('testopre', tid))
        pg.preliminare(K, page)
        for g in c['groups']:
            X = iri('canone', '%s/gruppo/%d' % (c['id'], g['n']))
            G.add(X, 'rdf:type', 'bj:GruppoCanone')
            G.add(X, 'dcterms:identifier', s('canone.%s.gruppo.%d' % (c['id'], g['n'])))
            G.add(X, 'rdfs:label', it(g['title']))
            G.add(X, 'dcterms:title', it(g['title']))
            html(G, X, g['title'], g['html'])
            G.add(X, 'bj:ordine', i(g['n']))
            G.add(X, 'dcterms:isPartOf', iri('canone', '%s/gruppo/%d' % (c['id'], g['parent'])) if g['parent'] else K)
        for k, v in enumerate(c['items'], 1):
            X = iri('canone', '%s/voce/%d' % (c['id'], k))
            G.add(X, 'rdf:type', 'bj:VoceCanone')
            G.add(X, 'dcterms:identifier', s('canone.%s.voce.%d' % (c['id'], k)))
            G.add(X, 'rdfs:label', it(v['text']))
            G.add(X, 'bj:testo', it(v['text']))
            html(G, X, v['text'], v['html'])
            G.add(X, 'bj:ordine', i(k))
            G.add(X, 'bj:numero', i(v['n']))
            G.add(X, 'dcterms:isPartOf', iri('canone', '%s/gruppo/%d' % (c['id'], v['group'])))
            for o in v['books']:
                G.add(X, 'bj:comprendeLibro', iri('libro', o))
            for ch in v['chapters']:
                osis, n = ch.rsplit('.', 1)
                G.add(X, 'bj:comprendeCapitolo', capitolo(osis, int(n)))
            if c['id'] == 'greco':
                G.add(X, 'bj:deuterocanonico', b(v['deuterocanonical']))
                G.add(X, 'bj:apocrifo', b(v['apocryphal']))


def manoscritto_id(x):
    return x['gregory'] if x.get('gregory') else 'vl-' + x['form']


def abbreviazioni(G, P, pg):
    for x in P['abbreviazioni']:
        A = iri('abbreviazione', x['n'])
        G.add(A, 'rdf:type', 'bj:Abbreviazione')
        G.add(A, 'rdfs:label', it('%s = %s' % (x['form'], x['meaning'][:80].rstrip())))
        G.add(A, 'dcterms:identifier', s('abbreviazione.%d' % x['n']))
        G.add(A, 'skos:notation', s(x['form']))
        G.add(A, 'bj:significato', it(x['meaning']))
        G.add(A, 'bj:tipoAbbreviazione', s(x['kind']))
        G.add(A, 'bj:ordine', i(x['n']))
        pg.preliminare(A, x['page'])
        for o in x['books']:
            G.add(A, 'bj:abbreviaLibro', iri('libro', o))
        if x['kind'].startswith(('codice', 'papiro')):
            M = iri('manoscritto', manoscritto_id(x))
            G.add(A, 'bj:abbreviaManoscritto', M)
            G.add(M, 'rdf:type', 'bj:Manoscritto')
            G.add(M, 'rdfs:label', s(x['form']))
            G.add(M, 'dcterms:identifier', s('manoscritto.%s' % manoscritto_id(x)))
            pg.preliminare(M, x['page'])
            G.add(M, 'skos:notation', s(x['letter'] or x['form']))
            if x.get('gregory'):
                G.add(M, 'bj:numeroGregoryAland', s(x['gregory']))
            G.add(M, 'bj:categoriaManoscritto', s(x['kind']))
            G.add(M, 'bj:descrizione', s(x['meaning']))


def xilografie(G, P, passaggi, prima):
    for x in P['xilografie']:
        X = iri('xilografia', x['book'])
        G.add(X, 'rdf:type', 'bj:Xilografia')
        G.add(X, 'dcterms:identifier', s('xilografia.%s' % x['book']))
        stampato(G, X, prima[x['book']])            # printed at the head of its book (R2-11)
        G.add(X, 'rdfs:label', it('Xilografia di %s (%s)' % (x['name'], x['raw'])))
        G.add(X, 'bj:testo', s('%s (%s)' % (x['name'], x['raw'])))
        G.add(X, 'bj:apreLibro', iri('libro', x['book']))
        G.add(X, 'dcterms:source', s('Biblia Sacra Vulgatae editionis, Venetiis 1625 apud Iuntas'))
        for r in x['refs']:
            for a, z in r['ranges']:
                G.link(X, 'bj:illustra', passaggi(a, z))
            for t in r['targets']:
                G.link(X, 'bj:illustraVersetto', verso(t))


def citazione_par(G, l, passaggi, extra):
    X = citazione(l['id'])
    G.add(X, 'rdf:type', 'bj:Citazione')
    riferimento(G, X, l, passaggi)
    for p, o in extra:
        G.add(X, p, o)
    if 'offset' in l:
        G.add(X, 'bj:posizioneTesto', i(l['offset']))
        G.add(X, 'bj:lunghezza', i(l['length']))
    if l.get('html_offset') is not None:
        G.add(X, 'bj:posizioneHtml', i(l['html_offset']))
        G.add(X, 'bj:fineHtml', i(l['html_end']))
    G.add(X, 'bj:conCf', b(l['cf']))
    return X


def citazioni_par(G, P, passaggi):
    for l in P['links']:
        if l['kind'] == 'front-cites':
            tid, n = l['source'].rsplit('.', 1)
            chi = iri('testopre', tid)
            citazione_par(G, l, passaggi, [('bj:daParagrafo', iri('paragrafo', '%s.%s' % (tid, n)))])
        else:
            chi = iri('cronologia', 'voce/%s' % l['source'].split('.', 1)[1])
            citazione_par(G, l, passaggi, [('bj:daEvento', chi)])
        if l['status'] in ('resolved', 'partial'):
            for t in l['targets']:
                G.link(chi, 'bj:citaVersetto', verso(t))


def voce_indice(ix, n, k=0):
    return iri('indice', '%s/voce/%d%s' % (ix, n, '/%d' % k if k else ''))


def indici(G, P, passaggi, pg):
    for ix in P['indici']:
        S = iri('indice', ix['id'])
        G.add(S, 'rdf:type', 'bj:Indice')
        G.add(S, 'rdf:type', 'skos:ConceptScheme')
        G.add(S, 'rdfs:label', it(INDICI[ix['id']][0]))
        G.add(S, 'rdfs:label', ('en', INDICI[ix['id']][1]))
        G.add(S, 'dcterms:title', it(INDICI[ix['id']][0]))
        G.add(S, 'dcterms:identifier', s('indice-' + ix['id']))
        G.add(S, 'dcterms:isPartOf', 'id:edizione')
        pg.appendice(S, ix['voci'][0]['page'])
        for v in ix['voci']:
            V = voce_indice(ix['id'], v['n'])
            G.add(S, 'skos:hasTopConcept', V)
            G.add(V, 'rdf:type', 'bj:VoceIndice')
            G.add(V, 'skos:prefLabel', it(v['lemma']))
            G.add(V, 'rdfs:label', it(v['lemma']))
            G.add(V, 'skos:inScheme', S)
            G.add(V, 'skos:topConceptOf', S)
            G.add(V, 'dcterms:identifier', s('indice-%s.%d' % (ix['id'], v['n'])))
            G.add(V, 'bj:stile', s(v['style']))
            G.add(V, 'bj:ordine', i(v['n']))
            pg.appendice(V, v['page'])
            for sv in v['sub']:
                W = voce_indice(ix['id'], v['n'], sv['k'])
                G.add(W, 'rdf:type', 'bj:VoceIndice')
                G.add(W, 'skos:prefLabel', it(nome_sottovoce(v['lemma'], sv['label'])))
                G.add(W, 'rdfs:label', it(nome_sottovoce(v['lemma'], sv['label'])))
                G.add(W, 'skos:altLabel', it(sv['name']))
                G.add(W, 'bj:etichetta', s(sv['label']))
                G.add(W, 'skos:inScheme', S)
                G.add(W, 'skos:broader', V)
                G.add(V, 'skos:narrower', W)
                G.add(W, 'dcterms:identifier', s('indice-%s.%d.%d' % (ix['id'], v['n'], sv['k'])))
                G.add(W, 'bj:ordine', i(sv['k']))
                pg.appendice(W, sv['page'])
            for k, it_ in enumerate(v['items'], 1):
                W = voce_indice(ix['id'], v['n'], it_['sv'])
                if it_['kind'] == 'vedi':
                    for t in it_['to']:
                        T = voce_indice(ix['id'], t)
                        G.link(W, 'bj:vediVoce', T)
                        G.link(W, 'skos:related', T)
                        G.link(T, 'skos:related', W)
                    continue
                if it_['kind'] == 'pagina':
                    for iid in it_['intros']:
                        G.link(W, 'bj:rinviaAIntroduzione', introduzione(iid))
                    continue
                l = it_['link']
                extra = [('bj:daVoceIndice', W), ('bj:ordine', i(k))]
                if it_['seguito']:
                    extra.append(('bj:seguito', s(it_['seguito'])))
                if l.get('implicit'):
                    extra.append(('bj:libroImplicito', i(l['implicit'])))
                if l.get('nota'):
                    extra.append(('bj:corrispondenzaNota', s(l['nota'])))
                if not l.get('correction'):     # a misprint's own notes are not the ones the index means
                    for nid in l.get('notes', []):
                        extra.append(('bj:indicaNota', nota(nid)))
                X = citazione_par(G, l, passaggi, extra)
                pg.appendice(X, it_['page'])
                fix = l.get('correction')
                if fix:
                    G.add(X, 'bj:testoCorretto', s(fix['raw']))
                    G.add(X, 'bj:correzione', s(fix['why']))
                    for a, z in fix['ranges']:
                        G.add(X, 'bj:aPassaggioCorretto', passaggi(a, z))
                    for nid in fix.get('notes', []):
                        G.add(X, 'bj:indicaNota', nota(nid))
                    targets, notes = fix['targets'], fix.get('notes', [])
                elif l['status'] in ('resolved', 'partial'):
                    targets, notes = l['targets'], l.get('notes', [])
                else:
                    targets, notes = [], []
                if l.get('nota') in ('rimandi', 'nessuna') and not fix:
                    notes = []
                for t in targets:
                    G.link(W, 'bj:indicaVersetto', verso(t))
                    G.link(verso(t), 'bj:nellIndice', W)
                for nid in notes:
                    G.link(W, 'bj:indicaNota', nota(nid))


def cronologia(G, P, pg):
    cr = P['cronologia']
    T = iri('cronologia', 'tavola')
    G.add(T, 'rdf:type', 'bj:TavolaCronologica')
    G.add(T, 'dcterms:identifier', s('cronologia'))
    G.add(T, 'rdfs:label', it('Tavola cronologica'))
    G.add(T, 'dcterms:title', it('Tavola cronologica'))
    G.add(T, 'dcterms:isPartOf', 'id:edizione')
    G.add(T, 'bj:testo', it('\n\n'.join(p['text'] for p in cr['intro'])))
    pg.appendice(T, 3)
    for x in cr['sections']:
        X = iri('cronologia', 'sezione/%d' % x['n'])
        G.add(X, 'rdf:type', 'bj:SezioneCronologia')
        G.add(X, 'dcterms:identifier', s('cronologia.sezione.%d' % x['n']))
        G.add(X, 'rdfs:label', it(x['title']))
        G.add(X, 'dcterms:title', it(x['title']))
        G.add(X, 'bj:ordine', i(x['n']))
        G.add(X, 'dcterms:isPartOf', T)
    for v in cr['voci']:
        X = iri('cronologia', 'voce/%d' % v['n'])
        G.add(X, 'rdf:type', 'bj:EventoCronologia')
        G.add(X, 'dcterms:identifier', s('cronologia.%d' % v['n']))
        G.add(X, 'rdfs:label', it(v['text'] if len(v['text']) <= 90 else v['text'][:89].rstrip() + '…'))
        G.add(X, 'bj:testo', it(v['text']))
        html(G, X, v['text'], v['html'])
        G.add(X, 'dcterms:isPartOf', iri('cronologia', 'sezione/%d' % v['section']))
        G.add(X, 'bj:colonna', COLONNA[v['column']])
        G.add(X, 'bj:riga', i(v['row']))
        G.add(X, 'bj:ordine', i(v['order']))
        if v['margin']:
            G.add(X, 'bj:anniMargine', s(v['margin']))
        if v['date']:
            G.add(X, 'bj:datazione', s(v['date']))
        if v['start'] is not None:
            G.add(X, 'bj:annoInizio', i(v['start']))
            G.add(X, 'bj:annoFine', i(v['end']))
            G.add(X, 'bj:circa', b(v['circa']))
        for n in v['smallcaps']:
            G.add(X, 'bj:nomeMaiuscoletto', s(n))
        for n in v['caps']:
            G.add(X, 'bj:nomeMaiuscolo', s(n))
        pg.appendice(X, v['page'])


def dinastie(G, P, pg):
    T = iri('dinastia', 'tavola')
    G.add(T, 'rdf:type', 'bj:TavolaGenealogica')
    G.add(T, 'dcterms:identifier', s('dinastie'))
    G.add(T, 'rdfs:label', it('Dinastie Asmonea e Erodiana'))
    G.add(T, 'dcterms:title', it('Dinastie Asmonea e Erodiana'))
    G.add(T, 'dcterms:isPartOf', 'id:edizione')
    pg.appendice(T, 24)
    for x in P['dinastie']:
        X = iri('dinastia', x['id'])
        G.add(X, 'rdf:type', 'bj:PersonaStorica')
        G.add(X, 'rdf:type', 'schema:Person')
        G.add(X, 'rdfs:label', s(('%s. %s' % (x['number'], x['name'])) if x['number'] else x['name']))
        G.add(X, 'foaf:name', s(x['name']))
        G.add(X, 'dcterms:identifier', s(x['id']))
        G.add(X, 'dcterms:isPartOf', T)
        if x['number']:
            G.add(X, 'bj:numeroTavola', s(x['number']))
        if x['date']:
            G.add(X, 'bj:datazione', s(x['date']))
        G.add(X, 'bj:corsivo', b(x['italic']))
        if x['note']:
            G.add(X, 'rdfs:comment', it(x['note']))
        for k in ('father', 'mother'):
            if x[k]:
                G.link(X, 'schema:parent', iri('dinastia', x[k]))
                G.link(iri('dinastia', x[k]), 'schema:children', X)
        for y in x['spouses']:
            G.link(X, 'schema:spouse', iri('dinastia', y))


def paratesto(G, P, passaggi, prima):
    """The front matter and the appendices, counted as their own part of the graph."""
    G.parte = 'paratesto'
    pg = PaginePar(G)
    edizione_bj(G, P['edizione'], pg)
    testi_preliminari(G, P, pg)
    canoni(G, P, pg)
    abbreviazioni(G, P, pg)
    xilografie(G, P, passaggi, prima)
    citazioni_par(G, P, passaggi)
    indici(G, P, passaggi, pg)
    cronologia(G, P, pg)
    dinastie(G, P, pg)
    G.parte = 'bibbia'
    return pg


# ---------------------------------------------------------------- quotations (virgolette.py, discorsi.json)

def discorsi(G, Q, data, books):
    """Every quotation of discorsi.json as a bj:Discorso: its ends (resource and plain offsets), the part
    and the resource it is read in, the quotation around it, the verses it spans, its words when short,
    the unbalanced ones with their reason. Counted in the part of the graph of the resource it is in."""
    V = {v['id']: v for v in data['verses']}
    order = [v['id'] for v in data['verses']]
    pos = {v: k for k, v in enumerate(order)}
    ids = [virgolette.risorsa(x['id']).replace('verso:', 'discorso:', 1) if '/' not in x['id'] else
           'discorso:' + x['id'] for x in Q]

    def etichetta(seg):
        if '/' not in seg and seg != 'edizione':
            return etichetta_versetto(V[seg], books[V[seg]['book']])
        return next(o[1] for p, o in G.per[virgolette.risorsa(seg)] if p == 'rdfs:label')

    for x, D in zip(Q, ids):
        G.parte = 'paratesto' if x['part'] in ('preliminari', 'appendici') else 'bibbia'
        a, z = x['segments'][0], x['segments'][-1]
        if x['part'] == 'testo':
            dove = etichetta_passaggio(V[a], V[z], books)
        else:
            dove = etichetta(a) + ('' if a == z else ' – ' + etichetta(z))
        if x.get('unbalanced'):
            what = '« senza chiusura' if x['start'] else '» senza apertura'
        else:
            t = x['text']
            what = '«%s»' % (t if len(t) <= 60 else t[:59].rstrip() + '…')
        G.add(D, 'rdf:type', 'bj:Discorso')
        G.add(D, 'rdfs:label', it('%s: %s' % (dove, what)))
        G.add(D, 'dcterms:identifier', s(x['id']))
        G.add(D, 'bj:parte', s(x['part']))
        G.add(D, 'oa:hasSource', virgolette.risorsa(x['source']))
        if x['start']:
            G.add(D, 'bj:iniziaIn', virgolette.risorsa(x['start']['seg']))
            G.add(D, 'bj:inizioCarattere', i(x['start']['testo']))
        if x['end']:
            G.add(D, 'bj:finisceIn', virgolette.risorsa(x['end']['seg']))
            G.add(D, 'bj:fineCarattere', i(x['end']['testo']))
        if x['parent'] is not None:
            G.add(D, 'bj:dentroDi', ids[x['parent']])
        if x['part'] == 'testo':
            for v in order[pos[a]:pos[z] + 1]:
                G.add(D, 'bj:attraversa', verso(v))
        if x.get('unbalanced'):
            G.add(D, 'bj:sbilanciato', b(True))
            G.add(D, 'bj:motivo', s(x['unbalanced']))
        else:
            G.add(D, 'bj:lunghezza', i(len(x['text'])))
            if len(x['text']) <= TESTO_DISCORSO:
                G.add(D, 'bj:testo', it(x['text']))
    G.parte = 'bibbia'


# ---------------------------------------------------------------- the time line (eventi.py, eventi.json)

# the sources of a date read in free text: bj:parte, the part of the graph, the IRI of the source
FONTI_TESTO = {
    'nota': ('nota', 'bibbia', nota),
    'introduzione': ('introduzione', 'bibbia', lambda x: paragrafo(x.rsplit('.', 1)[0], int(x.rsplit('.', 1)[1]))),
    'testo': ('preliminari', 'paratesto', lambda x: iri('paragrafo', x)),
    'dizionario': ('dizionario', 'dizionario', paragrafo_voce),
}
# the resources already in the graph, and their part
FONTI_RISORSE = {
    'cronologia': ('paratesto', lambda e: iri('cronologia', 'voce/%d' % e['cronologia']['voce'])),
    'dinastie': ('paratesto', lambda e: iri('dinastia', e['sorgente'])),
    'datazione': ('integrazione', lambda e: iri('cronologia', 'datazione/%s' % e['sorgente'])),
    'carta': ('integrazione', lambda e: iri('carta', e['sorgente'])),
}


def risorsa_evento(e):
    """The resource of an event of eventi.json: the one already in the graph, or the bj:EventoDatato of a date
    read in free text, named after its source and offset (evento:nota/Exod.2.10/474)."""
    if e['fonte'] in FONTI_RISORSE:
        return FONTI_RISORSE[e['fonte']][1](e)
    src = FONTI_TESTO[e['fonte']][2](e['sorgente'])
    return iri('evento', '%s/%d' % (src.replace(':', '/', 1), e['offset']))


def citazione_di(e, lid):
    """The bj:Citazione of a reference of an event's sentence (stage 2 for the BJ, 2b for the dictionary)."""
    return citazione_voce(lid) if e['fonte'] == 'dizionario' else citazione(lid)


def eventi(G, E, data):
    """The time line: each event of eventi.json on its resource (see the module docstring). The years of the
    chronology entries dated by stage 2c are already there (G.link drops them, the checks compare them)."""
    vs = data['verses']
    ids = {e['id']: risorsa_evento(e) for e in E['eventi']}
    for e in E['eventi']:
        X = ids[e['id']]
        if e['fonte'] in FONTI_TESTO:
            parte, G.parte, sorgente = FONTI_TESTO[e['fonte']]
            G.add(X, 'rdf:type', 'bj:EventoDatato')
            G.add(X, 'rdfs:label', it(e['etichetta']))
            G.add(X, 'dcterms:identifier', s(e['id'][len('ev:'):]))
            G.add(X, 'bj:parte', s(parte))
            G.add(X, 'oa:hasSource', sorgente(e['sorgente']))
            G.add(X, 'bj:datazione', s(e['data']))
            G.add(X, 'bj:posizioneTesto', i(e['offset']))
            G.add(X, 'bj:testo', it(e['frase']))
            html(G, X, e['frase'], e['html'])
            if e['verso']:
                G.add(X, 'bj:versettoAncora', verso(e['verso']))
            for _, lid in e['riferimenti']:
                G.add(X, 'bj:citazioneNellaFrase', citazione_di(e, lid))
            r = e['versetti']
            for a, z in zip(r[::2], r[1::2]):
                for k in range(a, z + 1):
                    G.add(X, 'bj:citaVersetto', verso(vs[k]['id']))
        else:
            G.parte = FONTI_RISORSE[e['fonte']][0]
            if e['fonte'] == 'cronologia' and e.get('data_da') == 'testo':
                G.add(X, 'bj:datazione', s(e['data']))      # the date its text gives (stage 2c gave none)
            if e['fonte'] == 'dinastie':
                G.add(X, 'bj:tipoDatazione', s(e['tipo']))
        G.add(X, 'bj:posizioneLinea', i(e['n']))
        G.link(X, 'bj:annoInizio', i(e['inizio']))
        G.link(X, 'bj:annoFine', i(e['fine']))
        G.link(X, 'bj:circa', b(e['circa']))
        G.add(X, 'bj:precisione', s(e['precisione']))
        G.add(X, 'bj:regolaEra', s(e['era_da']))
        if e.get('data_da'):
            G.add(X, 'bj:datataDa', s(e['data_da']))
        if e['limite']:
            G.add(X, 'bj:limite', s(e['limite']))
        if e['incerto']:
            G.add(X, 'bj:incerto', b(True))
        if e.get('alternativa') is not None:
            G.add(X, 'bj:annoAlternativo', i(e['alternativa']))      # signed as the years
        if e['periodo']:
            G.add(X, 'bj:nelPeriodo', iri('cronologia', 'sezione/%d' % e['periodo']))
        for y in e.get('stesso_evento', []):    # symmetric, as in eventi.json (G.link drops the second copy)
            G.link(X, 'bj:stessoEvento', ids[y])
            G.link(ids[y], 'bj:stessoEvento', X)
    G.parte = 'bibbia'


def checks_eventi(G, E, data, coll, dz):
    """The time line against eventi.json: one resource per event, its years (the chronology's of stage 2c
    unchanged), the date at its offset in the text of its source, the verses equal to the targets of the
    citations of the sentence, the same-event links both ways."""
    tipi = Counter(o for po in G.per.values() for p, o in po if p == 'rdf:type')
    attesi = sum(1 for e in E['eventi'] if e['fonte'] in FONTI_TESTO)
    err = [] if tipi['bj:EventoDatato'] == attesi else [
        'bj:EventoDatato: %d resources, %d in eventi.json' % (tipi['bj:EventoDatato'], attesi)]
    vix = {v['id']: k for k, v in enumerate(data['verses'])}
    targets = {l['id']: l for l in coll['links'] + dz['citations']}
    testo = {}                                  # the plain text of each source, as the graph has it
    for X, po in G.per.items():
        for p, o in po:
            if p == 'bj:testo' or (p == 'rdf:value' and X.startswith('corpo:')):
                testo[X.replace('corpo:', 'nota:', 1) if X.startswith('corpo:') else X] = o[1]
    for e in E['eventi']:
        X = risorsa_evento(e)
        po = G.per.get(X)
        if po is None:
            err.append('%s: no resource %s' % (e['id'], X))
            continue
        val = {}
        for p, o in po:
            val.setdefault(p, []).append(o)
        if val.get('bj:annoInizio') != [i(e['inizio'])] or val.get('bj:annoFine') != [i(e['fine'])]:
            err.append('%s: years %s %s in the graph, %d %d in eventi.json' % (
                e['id'], val.get('bj:annoInizio'), val.get('bj:annoFine'), e['inizio'], e['fine']))
        if val.get('bj:posizioneLinea') != [i(e['n'])]:
            err.append('%s: position %s, %d in eventi.json' % (e['id'], val.get('bj:posizioneLinea'), e['n']))
        if e['fonte'] not in FONTI_TESTO:
            continue
        src = val['oa:hasSource'][0]
        t = testo.get(src, '')
        if t[e['offset']:e['offset'] + len(e['data'])] != e['data']:
            err.append('%s: %r not at %d in the text of %s' % (e['id'], e['data'], e['offset'], src))
        if e['frase'] not in t:
            err.append('%s: the sentence is not in the text of %s' % (e['id'], src))
        attesi = {vix[v] for _, lid in e['riferimenti'] if targets[lid]['status'] in ('resolved', 'partial')
                  for v in targets[lid]['targets']}
        got = {vix[o.split(':', 1)[1]] for o in val.get('bj:citaVersetto', [])}
        if got != attesi:
            err.append('%s: %d verses cited, %d targets of its citations' % (e['id'], len(got), len(attesi)))
    coppie = {(x, o) for x, po in G.per.items() for p, o in po if p == 'bj:stessoEvento'}
    err += ['bj:stessoEvento %s %s without its inverse' % xy for xy in sorted(coppie) if xy[::-1] not in coppie]
    return err


# ---------------------------------------------------------------- the links between the parts (integrazione.json)

MOTIVAZIONE = {'editing': 'oa:editing', 'linking': 'oa:linking', 'describing': 'oa:describing',
               'interpretando': 'bj:interpretando'}
REGOLA = {k: 'bj:regola' + ''.join(w.capitalize() for w in k.split('-')) for k in (
    'manuale', 'aggiunta', 'numerazione', 'refuso', 'catena', 'puntatore', 'capitolo', 'elenco', 'inizio', 'ester',
    'introduzione', 'nudo', 'lettura', 'indice', 'prosa', 'rimando', 'pagina-estranea', 'nota-editoriale', 'paragrafo',
    'forma', 'conversione')}
SCHEMA_DI = {'numerazioni.tsv': None}
CURATORE = ('massimo-nocentini', 'Massimo', 'Nocentini')


def decimale(x):
    """An xsd:decimal literal from a printed number («22,5») or a float (a ratio)."""
    if x is None:
        return None
    if isinstance(x, str):
        x = float(x.replace(',', '.'))
    t = ('%.6f' % x).rstrip('0')
    return ('d', t + '0' if t.endswith('.') else t)


def chiave_indice(k):
    """note.204.1 -> the IRI of the index entry or sub-entry."""
    p = k.split('.')
    return voce_indice(p[0], int(p[1]), int(p[2]) if len(p) > 2 else 0)


def integrazione(G, I, P, dz, data, passaggi, pg, tipi_link):
    """The links between the parts (alignments, persons, datings, witnesses), the calendar, the
    measures and the maps, the corrections in one model and the numbering schemes, counted as the
    fourth part of the graph (VoID subset vp:integrazione)."""
    G.parte = 'integrazione'
    bix = {b['osis']: b for b in data['books']}
    # alignments (R2-12, R2-13, R2-10): reified, with the SKOS mapping triple as the shortcut
    INV = {'closeMatch': 'closeMatch', 'relatedMatch': 'relatedMatch', 'exactMatch': 'exactMatch',
           'broadMatch': 'narrowMatch', 'narrowMatch': 'broadMatch'}
    for x in I['allineamenti']:
        A = iri('allineamento', '%d' % x['riga'])
        da = chiave_indice(x['da'])
        a = voce(x['a'][5:]) if x['a'].startswith('voce:') else chiave_indice(x['a'])
        G.add(A, 'rdf:type', 'bj:Allineamento')
        G.add(A, 'rdfs:label', s('%s %s %s' % (x['da'], x['relazione'], x['a'])))
        G.add(A, 'dcterms:identifier', s('allineamenti.tsv#%d' % x['riga']))
        G.add(A, 'bj:allineamentoDa', da)
        G.add(A, 'bj:allineamentoA', a)
        G.add(A, 'bj:proprietaMapping', 'skos:' + x['relazione'])
        G.add(A, 'bj:metodoAllineamento', s(x['metodo']))
        G.add(A, 'bj:revisore', s(x['chi']))
        if x['nota']:
            G.add(A, 'rdfs:comment', it(x['nota']))
        G.add(A, 'bj:versettiComuni', i(len(x['comuni'])))
        for t in x['comuni']:
            G.add(A, 'bj:versettoComune', verso(t))
        G.add(A, 'bj:tabellaFonte', s('tools/ontologia/allineamenti.tsv'))
        G.add(A, 'bj:rigaFonte', s(str(x['riga'])))
        G.link(da, 'skos:' + x['relazione'], a)
        G.link(a, 'skos:' + INV[x['relazione']], da)
    # persons (R2-14)
    for x in I['persone']['versetti']:
        G.link(verso(x['verso']), 'bj:nominaPersona', iri('dinastia', x['persona']))
        G.link(iri('dinastia', x['persona']), 'bj:nominatoIn', verso(x['verso']))
    for x in I['persone']['indice']:
        G.link(citazione(x['citazione']) if x.get('citazione') else chiave_indice(x['voce']), 'bj:indicaPersona',
               iri('dinastia', x['persona']))
    for x in I['persone']['cronologia']:
        G.link(iri('cronologia', 'voce/%d' % x['voce']), 'bj:riguardaPersona', iri('dinastia', x['persona']))
    # chronology <-> books (R2-15): reified, with the shortcuts both ways
    for x in I['datazioni']:
        D = iri('cronologia', 'datazione/%s' % x['id'])
        E = iri('cronologia', 'voce/%d' % x['voce'])
        G.add(D, 'rdf:type', 'bj:Datazione')
        G.add(D, 'rdfs:label', s('cronologia %d: %s %s' % (x['voce'], x['tipo'], ' '.join(x['libri']))))
        G.add(D, 'dcterms:identifier', s('cronologia.datazione.%s' % x['id']))
        G.add(D, 'bj:datazioneDi', E)
        G.add(D, 'bj:tipoDatazione', s(x['tipo']))
        for b_ in x['libri']:
            G.add(D, 'bj:datazioneLibro', iri('libro', b_))
            G.link(E, 'bj:riguardaLibro', iri('libro', b_))
            G.link(iri('libro', b_), 'bj:nellaCronologia', E)
        if x['riga']:
            G.add(D, 'bj:tabellaFonte', s('tools/ontologia/cronologia-libri.tsv'))
            G.add(D, 'bj:rigaFonte', s(str(x['riga'])))
            G.add(D, 'rdfs:comment', it(x['nota']))
    # versions and codices (R2-16)
    T = I['testimoni']
    for v in T['versioni']:
        V = iri('versione', v['id'])
        G.add(V, 'rdf:type', 'bj:Versione')
        G.add(V, 'rdfs:label', it(v['nome']))
        G.add(V, 'skos:prefLabel', it(v['nome']))
        G.add(V, 'dcterms:identifier', s('versione.%s' % v['id']))
        if v['abbreviazione']:
            G.add(iri('abbreviazione', v['abbreviazione']), 'bj:abbreviaVersione', V)
    for nid, vs in T['note_versioni']:
        for v in vs:
            G.link(nota(nid), 'bj:citaTestimone', iri('versione', v))
    for nid, cs in T['note_codici']:
        for c in cs:
            G.link(nota(nid), 'bj:citaTestimone', iri('manoscritto', c))
    # the citations of the calendar, the measures and the maps
    for l in I['links']:
        X = citazione_par(G, dict(l, html_offset=None), passaggi, [])
        if l.get('corrected') == 'prosa':
            G.add(X, 'bj:testoCorretto', s(l['corrected_raw']))
            G.add(X, 'bj:correzione', s(l['why']))
    def cita(X, ids):
        for lid in ids:
            l = linkx[lid]
            G.add(citazione(lid), 'bj:daVoceTavola', X)
            if l['status'] in ('resolved', 'partial'):
                for t in l['targets']:
                    G.link(X, 'bj:citaVersetto', verso(t))
    linkx = {l['id']: l for l in I['links']}
    # the calendar (R2-18)
    C_ = 'id:calendario'
    G.add(C_, 'rdf:type', 'skos:ConceptScheme')
    G.add(C_, 'rdf:type', 'bj:Calendario')
    G.add(C_, 'rdfs:label', it('Calendario e feste annuali'))
    G.add(C_, 'dcterms:title', it('Calendario'))
    G.add(C_, 'dcterms:identifier', s('calendario'))
    G.add(C_, 'dcterms:isPartOf', 'id:edizione')
    pg.appendice(C_, 25)
    for k, m in enumerate(I['mesi'], 1):
        M = iri('calendario', 'mese/%s' % m['id'])
        G.add(M, 'rdf:type', 'bj:Mese')
        G.add(M, 'skos:prefLabel', it(m['nome']))
        G.add(M, 'rdfs:label', it(m['nome']))
        G.add(M, 'skos:notation', s(m['id']))
        G.add(M, 'dcterms:identifier', s('calendario.mese.%s' % m['id']))
        G.add(M, 'skos:inScheme', C_)
        G.add(C_, 'skos:hasTopConcept', M)
        G.add(M, 'skos:topConceptOf', C_)
        G.add(M, 'bj:ordine', i(k))
        G.add(M, 'bj:meseSolare', s(m['solare']))
        G.add(M, 'bj:nomeMacedone', it(m['macedone']))
        G.add(M, 'skos:altLabel', it(m['macedone']))
        for a in m['altri']:
            G.add(M, 'bj:nomeAntico', it(a))
            G.add(M, 'skos:altLabel', it(a))
        pg.appendice(M, m['pagina'])
        cita(M, m['links'])
        for t in I['mesi_versetti'].get(m['id'], []):
            G.link(verso(t), 'bj:nominaMese', M)
    for f in I['feste']:
        F = iri('calendario', 'festa/%s' % f['id'])
        G.add(F, 'rdf:type', 'bj:Festa')
        G.add(F, 'skos:prefLabel', it(f['nome']))
        G.add(F, 'rdfs:label', it(f['nome']))
        G.add(F, 'dcterms:identifier', s('calendario.festa.%s' % f['id']))
        G.add(F, 'skos:inScheme', C_)
        for a in f['altri']:
            G.add(F, 'skos:altLabel', it(a))
        G.add(F, 'bj:nelMese', iri('calendario', 'mese/%s' % f['mese']))
        if f['giorno']:
            G.add(F, 'bj:giorno', s(f['giorno']))
        pg.appendice(F, f['pagina'])
        cita(F, f['links'])
        for a in f['anche']:
            T_ = voce(a[5:]) if a.startswith('voce:') else chiave_indice(a)
            G.link(F, 'skos:relatedMatch', T_)
            G.link(T_, 'skos:relatedMatch', F)
    # the measures and coins (R2-18)
    M_ = 'id:misure'
    G.add(M_, 'rdf:type', 'skos:ConceptScheme')
    G.add(M_, 'rdf:type', 'bj:TavolaMisure')
    G.add(M_, 'rdfs:label', it('Tavola delle misure e delle monete'))
    G.add(M_, 'dcterms:title', it('Tavola delle misure e delle monete'))
    G.add(M_, 'dcterms:identifier', s('misure'))
    G.add(M_, 'dcterms:isPartOf', 'id:edizione')
    pg.appendice(M_, 26)
    for x in I['misure']:
        U = iri('misura', x['id'])
        G.add(U, 'rdf:type', 'bj:Unita')
        G.add(U, 'skos:prefLabel', it(x['nome']))
        G.add(U, 'rdfs:label', it(x['nome']))
        G.add(U, 'dcterms:identifier', s('misura.%s' % x['id']))
        G.add(U, 'skos:inScheme', M_)
        G.add(M_, 'skos:hasTopConcept', U)
        G.add(U, 'skos:topConceptOf', M_)
        G.add(U, 'bj:tipoMisura', s(x['tipo']))
        if x['originale'] and x['originale'] != x['nome']:
            G.add(U, 'skos:altLabel', (x['lingua'], x['originale']))
        if x['valore']:
            G.add(U, 'bj:valoreStampato', s(x['valore']))
            G.add(U, 'bj:valore', decimale(x['valore']))
            G.add(U, 'bj:unitaQudt', 'unit:' + x['unita'].split(':')[1])
        if x['rapporto']:
            G.add(U, 'bj:rapporto', s(x['rapporto']))
            if x['rapporto_decimale'] is not None:
                G.add(U, 'bj:rapportoDecimale', decimale(x['rapporto_decimale']))
        if x['base'] and x['base'] != x['id']:
            G.add(U, 'bj:rapportoA', iri('misura', x['base']))
        if x['equivale']:
            G.link(U, 'bj:equivaleA', iri('misura', x['equivale']))
        G.add(U, 'bj:approssimativo', b(True))
        if x['nota']:
            G.add(U, 'rdfs:comment', it(x['nota']))
        pg.appendice(U, x['pagina'])
        cita(U, x['links'])
        for t in I['misure_versetti'].get(x['id'], []):
            G.link(verso(t), 'bj:nominaMisura', U)
    # the maps (R2-18)
    for x in I['carte']:
        K = iri('carta', x['id'])
        G.add(K, 'rdf:type', 'bj:Carta')
        G.add(K, 'rdfs:label', it(x['titolo']))
        G.add(K, 'dcterms:title', it(x['titolo']))
        G.add(K, 'dcterms:identifier', s('carta.%s' % x['id']))
        if x['sottotitolo']:
            G.add(K, 'bj:legenda', it(x['sottotitolo']))
        G.add(K, 'dcterms:isPartOf', 'id:edizione')
        G.add(K, 'bj:paginaPdfCarta', i(x['pdf']))
        if x['parte'] == 'appendici':
            pg.appendice(K, x['pdf'] - PDF_APPENDICI)
        G.add(K, 'bj:immagine', s(x['immagine']))
        if x['periodo']:
            G.add(K, 'dcterms:temporal', it(x['periodo']))
        for b_ in x['libri']:
            G.add(K, 'bj:raffiguraLibro', iri('libro', b_))
        for lid in x['links']:
            for a, z in linkx[lid]['ranges']:
                G.link(K, 'bj:raffiguraPassaggio', passaggi(a, z))
        cita(K, x['links'])
    # the numbering schemes (R2-21)
    for x in I['schemi']:
        N = iri('schemanum', x['id'])
        G.add(N, 'rdf:type', 'bj:SchemaNumerazione')
        G.add(N, 'rdfs:label', ('en', x['nome']))
        G.add(N, 'dcterms:identifier', s('numerazione.%s' % x['id']))
        G.add(N, 'bj:righeTabella', i(x['righe']))
    numer = R.numerazioni()
    # the corrections (R2-20): one oa:Annotation per table row, rule or reading
    curatore = persona_semplice(G, *CURATORE)
    ncoll = Counter()
    coll_ix = []
    for l in dz['links']:
        ncoll[l['source']] += 1
        coll_ix.append(iri('voce', '%s/collegamento/%d' % (l['source'], ncoll[l['source']])))

    def bersaglio(t):
        k, v = t
        if k == 'link':
            return rimando(v) if tipi_link.get(v) == 'mref' else citazione(v)
        return {'dzcit': lambda: citazione_voce(v), 'dzpar': lambda: paragrafo_voce(v),
                'dzlink': lambda: coll_ix[v], 'indice': lambda: chiave_indice(v),
                'dinastia': lambda: iri('dinastia', v), 'passaggio': lambda: passaggi(*v)}[k]()
    for x in I['interventi']:
        X = iri('intervento', x['id'])
        G.add(X, 'rdf:type', 'bj:Intervento')
        G.add(X, 'rdfs:label', s('%s %s' % (x['tabella'], x['riga'])))
        G.add(X, 'dcterms:identifier', s('%s#%s' % (x['tabella'], x['riga'])))
        G.add(X, 'oa:motivatedBy', MOTIVAZIONE[x['motivazione']])
        G.add(X, 'bj:regola', REGOLA[x['regola']])
        for t in x['bersagli']:
            T_ = bersaglio(t)
            G.add(X, 'oa:hasTarget', T_)
            if t[0] in ('link', 'dzcit'):
                G.link(T_, 'bj:regola', REGOLA[x['regola']])
        if x['motivo']:
            corpo = iri('intervento', x['id'] + '/motivo')
            G.add(X, 'oa:hasBody', corpo)
            G.add(corpo, 'rdf:type', 'oa:TextualBody')
            G.add(corpo, 'rdf:value', (x['lingua'], x['motivo']))
            G.add(corpo, 'dc:format', s('text/plain'))
            G.add(corpo, 'dc:language', s(x['lingua']))
        G.add(X, 'bj:tabellaFonte', s(x['tabella']))
        G.add(X, 'bj:rigaFonte', s(str(x['riga'])))
        if x['fonte']:
            G.add(X, 'bj:fileFonte', s(x['fonte']))
        if x['stampato']:
            G.add(X, 'bj:testoStampato', s(x['stampato']))
        if x['corretto']:
            G.add(X, 'bj:testoLetto', s(x['corretto']))
        if x['tabella'] == 'numerazioni.tsv':
            G.add(X, 'bj:schemaNumerazione', iri('schemanum', numer[x['riga'] - 1]['schema']))
        if x['pagina']:
            k, n = x['pagina']
            if k == 'pagapp':
                pg.pagina_appendice(n)
                G.add(X, 'prov:wasDerivedFrom', iri('pagapp', n))
            elif k == 'pagina' and pagina(n) in G.per:
                G.add(X, 'prov:wasDerivedFrom', pagina(n))
        G.add(X, 'prov:wasAttributedTo', curatore)
    G.parte = 'bibbia'


def link_paratesto(P):
    """Every typed link of paratesto.json: the front texts, the chronology, the indices."""
    return P['links'] + [it_['link'] for ix in P['indici'] for v in ix['voci'] for it_ in v['items'] if it_.get('link')]


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
    if kind == 'y':
        return '"%s"^^<%s>' % (v, espandi('xsd:gYear'))
    if kind == 'ym':
        return '"%s"^^<%s>' % (v, espandi('xsd:gYearMonth'))
    if kind == 'd':
        return '"%s"^^<%s>' % (v, espandi('xsd:decimal'))
    if kind in LINGUE:
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
    if kind == 'd':
        return v
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
                        ('cites', 'cito:cites'), ('creator', 'dcterms:creator'), ('related', 'skos:related'),
                        ('inScheme', 'skos:inScheme'), ('topConceptOf', 'skos:topConceptOf'),
                        ('hasTopConcept', 'skos:hasTopConcept'), ('broader', 'skos:broader'),
                        ('narrower', 'skos:narrower'), ('parent', 'schema:parent'), ('children', 'schema:children'),
                        ('spouse', 'schema:spouse')]:
        term(name, {'@id': curie, '@type': '@id'})
    for name, curie in [('label', 'rdfs:label'), ('title', 'dcterms:title'),
                        ('identifier', 'dcterms:identifier'), ('value', 'rdf:value'),
                        ('format', 'dc:format'), ('language', 'dc:language'),
                        ('prefLabel', 'skos:prefLabel'), ('altLabel', 'skos:altLabel'), ('name', 'foaf:name'),
                        ('notation', 'skos:notation'), ('date', 'dcterms:date')]:
        term(name, curie)
    return {'@context': ctx}


def void(G, tipi):
    """The VoID description of the data graph: what it is, where it comes from, its
    dumps and vocabularies, and how many triples, resources, classes and properties it
    has (one partition per class and per property, with IRIs: no blank nodes). Two
    subsets split the triples by the part of rdf.py that made them: the Bible (verses,
    notes, margins, citations of notes and introductions) and the Dizionario di Teologia
    Biblica (its resources, the passages only it names, the verse -> entry shortcuts);
    two linksets count the entry <-> verse shortcuts."""
    D = '<%sdati>' % SITO
    per_prop = Counter(p for po in G.per.values() for p, o in po)
    tipizzati = sum(1 for po in G.per.values() if any(p == 'rdf:type' for p, o in po))

    def nome(curie):
        return curie.replace(':', '-')

    out = ['# VoID description of ontologia/bj-dati.{ttl,nt}.gz (generated by tools/ontologia/rdf.py).',
           '# Do not edit.']
    out += ['@prefix %s: <%s> .' % kv for kv in PREFISSI.items() if kv[0] in
            ('bj', 'rdf', 'rdfs', 'xsd', 'owl', 'dcterms', 'skos', 'oa', 'cito', 'prov', 'dc', 'verso', 'voce',
             'foaf', 'schema', 'indice')]
    out += ['@prefix void: <http://rdfs.org/ns/void#> .', '@prefix vp: <%svoid#> .' % SITO, '']
    out += [D + ' a void:Dataset ;',
            '    dcterms:title "La Bibbia di Gerusalemme: il grafo dei versetti"@it , '
            '"La Bibbia di Gerusalemme: the verse graph"@en ;',
            '    dcterms:description "Versetti, note, rimandi a margine e citazioni della Bibbia di '
            'Gerusalemme (EDB: testo CEI 2008, note e rimandi della Bible de Jérusalem), '
            'collegati al versetto, con le voci del Dizionario di Teologia Biblica e le loro citazioni '
            'bibliche, le pagine iniziali e le appendici (edizione, canone, abbreviazioni e codici, indici, '
            'tavola cronologica, dinastie, calendario, misure e monete, carte), i collegamenti tra le parti, le '
            'correzioni e la linea del tempo di ogni evento datato (anche le date lette nelle note, nelle '
            'introduzioni e nel Dizionario)."@it , "Verses, notes, margin references and citations of La Bibbia '
            'di Gerusalemme (EDB: CEI 2008 text, Bible de Jérusalem notes and margins), linked at the '
            'verse, with the entries of the Dizionario di Teologia Biblica and their Bible citations, the front '
            'matter and the appendices (edition, canon, abbreviations and codices, indices, chronological table, '
            'dynasties, calendar, measures and coins, maps), the links between the parts, the corrections and the '
            'time line of every dated event (also the dates read in the notes, introductions and dictionary)."@en ;',
            '    dcterms:rights "Testi protetti da diritto d\'autore (EDB, Marietti): solo per uso '
            'locale, non pubblicare."@it , "The texts are copyrighted (EDB, Marietti): local use only, '
            'do not publish."@en ;',
            '    dcterms:creator "Massimo Nocentini" ;',
            '    dcterms:source "progetti/<volume>/*.tex (14 volumi corretti / 14 proofread volumes)" , '
            '"../dufour/corpus/data (Dizionario di Teologia Biblica)" , '
            '"progetti/introduzione-generale, progetti/appendici (pagine iniziali e appendici / front matter and '
            'appendices)" ;',
            '    void:vocabulary <%sontologia> , <http://www.w3.org/ns/oa#> , <http://purl.org/spar/cito/> , '
            '<http://purl.org/dc/terms/> , <http://purl.org/dc/elements/1.1/> , <http://www.w3.org/ns/prov#> , '
            '<http://www.w3.org/2004/02/skos/core#> , <http://xmlns.com/foaf/0.1/> , <https://schema.org/> ;' % SITO,
            '    void:uriSpace "%s" ;' % ID,
            '    void:dataDump <%sbj-dati.nt.gz> , <%sbj-dati.ttl.gz> ;' % (SITO, SITO),
            '    void:feature <http://www.w3.org/ns/formats/N-Triples> , <http://www.w3.org/ns/formats/Turtle> ;',
            '    void:exampleResource verso:John.3.16 , verso:Gen.1.1 , voce:abele , <%sindice/note/voce/91> ;' % ID,
            '    void:triples %d ;' % len(G),
            '    void:distinctSubjects %d ;' % len(G.per),
            '    void:entities %d ;' % tipizzati,
            '    void:classes %d ;' % len(tipi),
            '    void:properties %d ;' % len(per_prop),
            '    void:subset vp:bibbia , vp:dizionario , vp:paratesto , vp:integrazione , vp:voci-versetti , '
            'vp:versetti-voci , vp:indice-versetti , vp:versetti-indice , vp:indice-dizionario , vp:versetti-persone , '
            'vp:cronologia-libri , vp:note-testimoni ;',
            '    void:classPartition %s ;' % ' , '.join('vp:classe-' + nome(c) for c in sorted(tipi)),
            '    void:propertyPartition %s .' % ' , '.join('vp:proprieta-' + nome(p) for p in sorted(per_prop))]
    for c in sorted(tipi):
        out.append('vp:classe-%s void:class %s ; void:entities %d .' % (nome(c), c, tipi[c]))
    for p in sorted(per_prop):
        out.append('vp:proprieta-%s void:property %s ; void:triples %d .' % (nome(p), p, per_prop[p]))
    out += sottoinsiemi(G, nome)
    with open(VOID, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    from rdflib import Graph, Literal, URIRef
    g = Graph().parse(VOID, format='turtle')
    vt = URIRef('http://rdfs.org/ns/void#triples')
    n = g.value(URIRef(D[1:-1]), vt)
    parti = [g.value(URIRef(SITO + 'void#' + x), vt) for x in ('bibbia', 'dizionario', 'paratesto', 'integrazione')]
    err = [] if n == Literal(len(G)) else ['%s: void:triples %s, graph %d' % (VOID, n, len(G))]
    if sum(int(x) for x in parti) != len(G):
        err.append('%s: subsets hold %s triples, graph %d' % (VOID, parti, len(G)))
    return err


def sottoinsiemi(G, nome):
    """The two subsets (with their class and property partitions) and the two linksets."""
    out = ['']
    titoli = {'bibbia': ('La Bibbia di Gerusalemme: versetti, note, rimandi, citazioni',
                         'The Jerusalem Bible: verses, notes, margins, citations',
                         'progetti/<volume>/*.tex'),
              'dizionario': ('Dizionario di Teologia Biblica (X. Léon-Dufour, Marietti 1976): voci, '
                             'collegamenti e citazioni bibliche',
                             'Dizionario di Teologia Biblica (X. Léon-Dufour, Marietti 1976): entries, '
                             'links and Bible citations',
                             '../dufour/corpus/data'),
              'paratesto': ('La Bibbia di Gerusalemme: pagine iniziali e appendici (edizione, presentazione e '
                            'prefazioni, canone, abbreviazioni e codici, xilografie, indice delle note, indice dei '
                            'temi pastorali, tavola cronologica, dinastie)',
                            'The Jerusalem Bible: front matter and appendices (edition, presentation and prefaces, '
                            'canon, abbreviations and codices, woodcuts, index of notes, index of pastoral themes, '
                            'chronological table, dynasties)',
                            'progetti/introduzione-generale, progetti/appendici'),
              'integrazione': ('Collegamenti tra le parti (indici, temi e Dizionario; persone; cronologia e libri; '
                               'versioni e codici), calendario, misure e monete, carte, correzioni (bj:Intervento) e '
                               'schemi di numerazione',
                               'Links between the parts (indices, themes and dictionary; persons; chronology and books; '
                               'versions and codices), calendar, measures and coins, maps, corrections (bj:Intervento) '
                               'and numbering schemes',
                               'tools/ontologia/*.tsv, tools/ontologia/integrazione.py')}
    for parte, (it_, en, fonte) in titoli.items():
        tipi = Counter(o for sog, po in G.per.items() if G.parte_di[sog] == parte
                       for p, o in po if p == 'rdf:type')
        props = sorted(p for (x, p) in G.per_parte_prop if x == parte)
        q = 'vp:%s-' % parte
        out += ['vp:%s a void:Dataset ;' % parte,
                '    dcterms:title "%s"@it , "%s"@en ;' % (it_, en),
                '    dcterms:source "%s" ;' % fonte,
                '    void:triples %d ;' % G.per_parte[parte],
                '    void:entities %d ;' % sum(tipi.values()),
                '    void:classPartition %s ;' % ' , '.join(q + 'classe-' + nome(c) for c in sorted(tipi)),
                '    void:propertyPartition %s .' % ' , '.join(q + 'proprieta-' + nome(p) for p in props)]
        out += ['%sclasse-%s void:class %s ; void:entities %d .' % (q, nome(c), c, tipi[c]) for c in sorted(tipi)]
        out += ['%sproprieta-%s void:property %s ; void:triples %d .' % (q, nome(p), p, G.per_parte_prop[parte, p])
                for p in props]
        out.append('')
    for nome_, pred, da, a, parte in (('voci-versetti', 'bj:voceCitaVersetto', 'dizionario', 'bibbia', 'dizionario'),
                                      ('versetti-voci', 'bj:citatoNellaVoce', 'bibbia', 'dizionario', 'dizionario'),
                                      ('indice-versetti', 'bj:indicaVersetto', 'paratesto', 'bibbia', 'paratesto'),
                                      ('versetti-indice', 'bj:nellIndice', 'bibbia', 'paratesto', 'paratesto'),
                                      ('versetti-persone', 'bj:nominaPersona', 'bibbia', 'paratesto', 'integrazione'),
                                      ('cronologia-libri', 'bj:riguardaLibro', 'paratesto', 'bibbia', 'integrazione'),
                                      ('note-testimoni', 'bj:citaTestimone', 'bibbia', 'paratesto', 'integrazione')):
        out += ['vp:%s a void:Linkset ;' % nome_,
                '    void:linkPredicate %s ;' % pred,
                '    void:subjectsTarget vp:%s ;' % da,
                '    void:objectsTarget vp:%s ;' % a,
                '    void:triples %d .' % G.per_parte_prop[parte, pred]]
    mapping = sum(1 for sog, po in G.per.items() if sog.startswith('indice:') for p, o in po
                  if p.startswith('skos:') and p.endswith('Match') and isinstance(o, str) and o.startswith('voce:'))
    out += ['vp:indice-dizionario a void:Linkset ;',
            '    void:linkPredicate skos:mappingRelation ;',
            '    dcterms:description "Le voci e sottovoci degli indici (note, temi) allineate alle voci del Dizionario '
            '(skos:closeMatch, broadMatch, narrowMatch, relatedMatch; tools/ontologia/allineamenti.tsv)."@it ;',
            '    void:subjectsTarget vp:paratesto ;',
            '    void:objectsTarget vp:dizionario ;',
            '    void:triples %d .' % mapping]
    return out


# ---------------------------------------------------------------- checks

def checks(G, ont, data, coll, dz, passaggi, P, I, Q):
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
    attesi = dict({'i': 'integer', 'b': 'boolean', 's': 'string', 'd': 'decimal'}, **{x: 'langString' for x in LINGUE})
    usati, nostri = Counter(), set(G.per)
    for sog, po in G.per.items():
        for p, o in po:
            if p.startswith('bj:'):
                usati[p] += 1
            if isinstance(o, str):
                if o.startswith('bj:'):
                    usati[o] += 1
                if o.split(':', 1)[0] in NOSTRI and o not in nostri:
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
                  Citazione=sum(1 for l in coll['links'] if l['kind'].endswith('-cites')) + len(dz['citations']),
                  Voce=len(dz['voci']), VoceRinvio=sum(1 for v in dz['voci'] if v['kind'] == 'redirect'),
                  SezioneVoce=sum(len(v.get('sections', [])) for v in dz['voci']),
                  ParagrafoVoce=sum(len(v.get('paragraphs', [])) for v in dz['voci']),
                  CollegamentoVoce=len(dz['links']), Dizionario=1)
    plinks = link_paratesto(P)
    attese['Citazione'] += len(plinks) + len(I['links'])
    attese['Paragrafo'] += sum(len(x['paragraphs']) for x in P['testi'])
    attese.update(Edizione=1, Stampa=len(P['edizione']['printings']), TestoPreliminare=len(P['testi']),
                  Canone=len(P['canoni']), GruppoCanone=sum(len(c['groups']) for c in P['canoni']),
                  VoceCanone=sum(len(c['items']) for c in P['canoni']), Abbreviazione=len(P['abbreviazioni']),
                  Manoscritto=sum(1 for x in P['abbreviazioni'] if x['kind'].startswith(('codice', 'papiro'))),
                  Xilografia=len(P['xilografie']), Indice=len(P['indici']),
                  VoceIndice=sum(len(ix['voci']) + sum(len(v['sub']) for v in ix['voci']) for ix in P['indici']),
                  TavolaCronologica=1, SezioneCronologia=len(P['cronologia']['sections']),
                  EventoCronologia=len(P['cronologia']['voci']), TavolaGenealogica=1, PersonaStorica=len(P['dinastie']),
                  LetteraAcrostica=sum(len(v.get('acrostic', [])) for v in data['verses']),
                  Allineamento=len(I['allineamenti']), Datazione=len(I['datazioni']),
                  Versione=len(I['testimoni']['versioni']), Mese=len(I['mesi']), Festa=len(I['feste']),
                  Unita=len(I['misure']), Carta=len(I['carte']), Intervento=len(I['interventi']),
                  SchemaNumerazione=len(I['schemi']), Calendario=1, TavolaMisure=1, Discorso=len(Q))
    attese = {'bj:' + k: n for k, n in attese.items()}
    autori = {x['author']['id'] for x in P['testi'] if x['author']} | {P['edizione']['direction'][0],
                                                                        P['edizione']['editor'][0]}
    attese['foaf:Person'] = len(dz['meta']['authors']) + len(DIZIONARIO['traduttori']) + len(autori) + 1   # + the curator
    attese['schema:Person'] = len(P['dinastie'])
    for k, n in attese.items():
        if tipi[k] != n:
            err.append('%s: %d resources, %d in the JSON' % (k, tipi[k], n))
    corrette = [dict(id=l['id'] + ' (corrected)', **{k: l['correction'][k] for k in ('ranges', 'targets')})
                for l in plinks if l.get('correction')]
    for l in coll['links'] + dz['citations'] + plinks + corrette + I['links']:
        if l.get('kind') == 'note-label' and (l['scope'] == 'book' or l['scope'] == 'chapter' and l['target_chapters']):
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
    if not os.path.exists(DUFOUR):
        sys.exit('%s is missing: run tools/ontologia/dufour.py first' % os.path.relpath(DUFOUR, C))
    dz = json.load(open(DUFOUR, encoding='utf-8'))
    B = R.Bibbia(data)
    books = {bk['osis']: bk for bk in data['books']}
    order = {v['id']: v['order'] for v in data['verses']}
    conta_minuscole(data)
    I0 = json.load(open(INTEGRAZIONE, encoding='utf-8')) if os.path.exists(INTEGRAZIONE) else {'testimoni': {'versioni': []}}
    for v in I0['testimoni']['versioni']:
        for q in v['qualificatori']:
            QUALIFICATORI[q] = iri('versione', v['id'])
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
    dizionario(G, dz, passaggi)
    if not os.path.exists(PARATESTO):
        sys.exit('%s is missing: run tools/ontologia/paratesto.py first' % os.path.relpath(PARATESTO, C))
    P = json.load(open(PARATESTO, encoding='utf-8'))
    if not os.path.exists(INTEGRAZIONE):
        sys.exit('%s is missing: run tools/ontologia/integrazione.py first' % os.path.relpath(INTEGRAZIONE, C))
    I = json.load(open(INTEGRAZIONE, encoding='utf-8'))
    prima = {}
    for v in data['verses']:
        prima.setdefault(v['book'], v['page'])
    pg = paratesto(G, P, passaggi, prima)
    tipi_link = {l['id']: l['kind'] for l in links}
    tipi_link.update((l['id'], l['kind']) for l in link_paratesto(P) + I['links'])
    integrazione(G, I, P, dz, data, passaggi, pg, tipi_link)
    if not os.path.exists(DISCORSI):
        sys.exit('%s is missing: run tools/ontologia/virgolette.py first' % os.path.relpath(DISCORSI, C))
    Q = json.load(open(DISCORSI, encoding='utf-8'))['discorsi']
    discorsi(G, Q, data, books)
    if not os.path.exists(EVENTI):
        sys.exit('%s is missing: run tools/ontologia/eventi.py first' % os.path.relpath(EVENTI, C))
    E = json.load(open(EVENTI, encoding='utf-8'))
    eventi(G, E, data)
    err, tipi, usati = checks(G, ont, data, coll, dz, passaggi, P, I, Q)
    err += checks_eventi(G, E, data, coll, dz)
    scrivi(G)
    err += void(G, tipi)
    with open(CONTESTO, 'w', encoding='utf-8') as f:
        json.dump(contesto(ont), f, ensure_ascii=False, indent=1)
        f.write('\n')
    if not quiet:
        print('resources: ' + ', '.join('%s %d' % (k, n) for k, n in tipi.most_common()))
        print('bj: properties: ' + ', '.join('%s %d' % kv for kv in usati.most_common() if kv[0][3].islower()))
    print('triples: %d (%d subjects, %d passages; Bible %d, dictionary %d, front matter and appendices %d, links '
          'between the parts and corrections %d triples); %s %.1f MB, %s %.1f MB; %.1f s' % (
        len(G), len(G.per), len(passaggi.fatti), G.per_parte['bibbia'], G.per_parte['dizionario'],
        G.per_parte['paratesto'], G.per_parte['integrazione'], os.path.relpath(TTL, C),
        os.path.getsize(TTL) / 1e6, os.path.relpath(NT, C), os.path.getsize(NT) / 1e6, time.time() - t0))
    for e in err[:30]:
        print('ERROR  ' + e)
    print('checks: %s' % ('ok' if not err else '%d errors' % len(err)))
    return 1 if err else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
