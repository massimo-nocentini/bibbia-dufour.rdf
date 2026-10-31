"""Check the verse graph: parsers, OWL sanity, SPARQL integrity, SHACL, JSON-LD context.

usage: verifica_rdf.py [-q]

Runs after rdf.py on ontologia/bj-dati.{nt,ttl}.gz, bj-ontologia.ttl, bj-forme.ttl and
bj-contesto.jsonld:
  parsers   rdflib's N-Triples and Turtle parsers (two worker processes) and the fast
            reader of grafo.py give the same set of triples (order-free digest)
  OWL       the ontology parses; every bj: term used in the data is declared, with one
            kind only (class, object / datatype / annotation property, concept); every
            subject and object of a bj: property is of its rdfs:domain / rdfs:range
  SPARQL    integrity queries on the whole graph: cardinalities, inverse and symmetric
            closures, shortcuts backed by the reified links, counts equal to the JSON; for
            the dictionary: counts equal to dufour.json (entries, sections, paragraphs,
            links, citations by status, verses cited), every citation target a declared
            verse, every entry link resolved to an entry (and its section to that entry),
            the entry <-> verse and entry <-> entry shortcuts backed and closed
  SHACL     pyshacl with bj-forme.ttl on the whole graph (about 4.5 minutes)
  JSON-LD   a few resources (John 3,16, the entry ABELE) serialised with the context and
            parsed back unchanged
Exit status 1 if any check fails.
"""
import gzip
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rdf import BJ, BIBBIA, COLLEGAMENTI, CONTESTO, DUFOUR, NT, ONTOLOGIA, PREFISSI, TTL  # noqa: E402
import grafo  # noqa: E402

FORME = os.path.join(os.path.dirname(ONTOLOGIA), 'bj-forme.ttl')
PREFIX = ''.join('PREFIX %s: <%s>\n' % kv for kv in PREFISSI.items())


def digest(triples):
    """An order-free digest of a set of triples: the sum of their SHA-1, and their number."""
    tot, n = 0, 0
    for t in triples:
        tot += int.from_bytes(hashlib.sha1(' '.join(x.n3() for x in t).encode('utf-8')).digest(), 'big')
        n += 1
    return n, tot % (1 << 160)


def parse_rdflib(args):
    path, fmt = args
    from rdflib import Graph
    t = time.time()
    g = Graph()
    g.parse(gzip.open(path), format=fmt)
    return fmt, digest(g), time.time() - t


# ---------------------------------------------------------------- OWL sanity

def owl(g, ont):
    from rdflib import OWL, RDF, RDFS, SKOS, URIRef
    err = []
    kinds = (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty,
             SKOS.Concept, SKOS.ConceptScheme)
    declared = {}
    for t in set(ont.subjects(RDF.type, None)):
        if isinstance(t, URIRef) and str(t).startswith(BJ):
            k = [x for x in ont.objects(t, RDF.type) if x in kinds]
            declared[t] = k
            if len(k) != 1:
                err.append('%s declared as %s' % (t, k))
    used = set(g.predicates()) | set(g.objects(None, RDF.type)) | set(
        o for o in g.objects() if isinstance(o, URIRef) and str(o).startswith(BJ))
    for t in sorted(used):
        if str(t).startswith(BJ) and t not in declared:
            err.append('%s used in the data, not declared' % t)

    def classes(c):
        """A class or the members of an owl:unionOf."""
        u = ont.value(c, OWL.unionOf)
        return set(ont.items(u)) if u is not None else {c}

    tipi = defaultdict(set)
    for gr in (g, ont):                             # the SKOS concepts are typed in the ontology
        for s, o in gr.subject_objects(RDF.type):
            tipi[s].add(o)
    sub = defaultdict(set)                          # class -> itself and its superclasses
    for c in set(ont.subjects(RDF.type, OWL.Class)) | set(o for v in tipi.values() for o in v):
        sub[c] = {c} | set(ont.transitive_objects(c, RDFS.subClassOf))
    checked = 0
    for p, k in declared.items():
        if k[0] not in (OWL.ObjectProperty, OWL.DatatypeProperty):
            continue
        dom = ont.value(p, RDFS.domain)
        rng = ont.value(p, RDFS.range) if k[0] == OWL.ObjectProperty else None
        dom = classes(dom) if dom is not None else None
        rng = classes(rng) if rng is not None else None
        bad = 0
        for s, o in g.subject_objects(p):
            checked += 1
            if dom and not any(dom & sub[c] for c in tipi[s]):
                bad += 1
            if rng and not any(rng & sub[c] for c in tipi[o]):
                bad += 1
        if bad:
            err.append('%s: %d subjects/objects outside its domain/range' % (p.n3(g.namespace_manager), bad))
    return err, len(declared), checked


# ---------------------------------------------------------------- SPARQL integrity

def conta(classe, sopra=''):
    return 'SELECT (COUNT(?x) AS ?n) WHERE { ?x a %s %s}' % (classe, sopra)


def integrita(data, coll, dz):
    """(name, query, expected value of the single result ?n)."""
    links = coll['links']
    nmref = sum(1 for l in links if l['kind'] == 'mref')
    ncit = sum(1 for l in links if l['kind'].endswith('-cites')) + len(dz['citations'])
    cited = set((l['source'].rsplit('.', 1)[0] if l['kind'] == 'intro-cites' else l['source'], t)
                for l in links if l['kind'].endswith('-cites') and l['status'] in ('resolved', 'partial')
                for t in l['targets'])
    return [
        ('verses', conta('bj:Versetto'), len(data['verses'])),
        ('notes', conta('bj:Nota'), len(data['notes'])),
        ('margin entries', conta('bj:Margine'), len(data['mrefs'])),
        ('margin references', conta('bj:Rimando'), nmref),
        ('citations', conta('bj:Citazione'), ncit),
        ('pericopes', conta('bj:Pericope'), len(data['pericopes'])),
        ('unresolved references and citations', conta('?c', '; bj:stato bj:irrisolto ; a ?k FILTER (?k != bj:CollegamentoVoce) '),
         sum(1 for l in links + dz['citations'] if l['status'] == 'unresolved' and l.get('kind') != 'note-label')),
        ('verses without exactly one text',
         'SELECT (COUNT(?v) AS ?n) WHERE { { SELECT ?v WHERE { ?v a bj:Versetto . OPTIONAL { ?v bj:testo ?t } }'
         ' GROUP BY ?v HAVING (COUNT(?t) != 1) } }', 0),
        ('verses without exactly one chapter',
         'SELECT (COUNT(?v) AS ?n) WHERE { { SELECT ?v WHERE { ?v a bj:Versetto . OPTIONAL { ?v dcterms:isPartOf ?c } }'
         ' GROUP BY ?v HAVING (COUNT(?c) != 1) } }', 0),
        ('verse chain: precede goes to order + 1',
         'SELECT (COUNT(?a) AS ?n) WHERE { ?a bj:precede ?b . ?a bj:ordine ?x . ?b bj:ordine ?y FILTER (?y != ?x + 1) }', 0),
        ('verse chain: segue is the inverse of precede',
         'SELECT (COUNT(?a) AS ?n) WHERE { ?a bj:precede ?b FILTER NOT EXISTS { ?b bj:segue ?a } }', 0),
        ('notes without body, anchor or target',
         'SELECT (COUNT(?x) AS ?n) WHERE { ?x a bj:Nota FILTER (NOT EXISTS { ?x oa:hasBody/rdf:value ?t }'
         ' || NOT EXISTS { ?x bj:richiamataDa ?v } || NOT EXISTS { ?x oa:hasTarget ?b }) }', 0),
        ('haNota is the inverse of richiamataDa',
         'SELECT (COUNT(?x) AS ?n) WHERE { { ?v bj:haNota ?x FILTER NOT EXISTS { ?x bj:richiamataDa ?v } }'
         ' UNION { ?x bj:richiamataDa ?v FILTER NOT EXISTS { ?v bj:haNota ?x } } }', 0),
        ('note commenta = verses of its targets',
         'SELECT (COUNT(?x) AS ?n) WHERE { ?x bj:commenta ?v FILTER NOT EXISTS {'
         ' { ?x oa:hasTarget/bj:comprende ?v } UNION { ?x oa:hasTarget ?c . ?v dcterms:isPartOf ?c } } }', 0),
        ('margin references without verse, margin or relation',
         'SELECT (COUNT(?x) AS ?n) WHERE { ?x a bj:Rimando FILTER (NOT EXISTS { ?x bj:daVersetto ?v }'
         ' || NOT EXISTS { ?x bj:relazione ?r } || NOT EXISTS { ?x bj:nelMargine ?m }) }', 0),
        ('resolved references without a passage or a book (links: an entry)',
         'SELECT (COUNT(?x) AS ?n) WHERE { ?x bj:stato ?s VALUES ?s { bj:risolto bj:parziale }'
         ' FILTER NOT EXISTS { ?x bj:aPassaggio|bj:libroCitato|bj:aVoce ?p } }', 0),
        ('passages include their ends',
         'SELECT (COUNT(?p) AS ?n) WHERE { ?p bj:inizio|bj:fine ?v ; a bj:Passaggio'
         ' FILTER NOT EXISTS { ?p bj:comprende ?v } }', 0),
        ('paralleloA and doppioneDi are symmetric',
         'SELECT (COUNT(?a) AS ?n) WHERE { { ?a bj:paralleloA ?b FILTER NOT EXISTS { ?b bj:paralleloA ?a } }'
         ' UNION { ?a bj:doppioneDi ?b FILTER NOT EXISTS { ?b bj:doppioneDi ?a } } }', 0),
        ('subproperties are in rimandaA',
         'SELECT (COUNT(?a) AS ?n) WHERE { { ?a bj:paralleloA ?b } UNION { ?a bj:doppioneDi ?b }'
         ' UNION { ?a bj:citatoIn ?b } UNION { ?a bj:rinviaANotaChiave ?b }'
         ' FILTER NOT EXISTS { ?a bj:rimandaA ?b } }', 0),
        ('rimandaA backed by a printed margin reference (either direction)',
         'SELECT (COUNT(?a) AS ?n) WHERE { ?a bj:rimandaA ?b FILTER NOT EXISTS {'
         ' { ?r bj:daVersetto ?a ; bj:aPassaggio/bj:comprende ?b }'
         ' UNION { ?r bj:daVersetto ?b ; bj:aPassaggio/bj:comprende ?a } } }', 0),
        ('citaVersetto: (note or intro, verse) pairs of the JSON',
         'SELECT (COUNT(*) AS ?n) WHERE { ?x bj:citaVersetto ?v }', len(cited)),
        ('citaVersetto backed by a citation of that note or introduction',
         'SELECT (COUNT(*) AS ?n) WHERE { SELECT DISTINCT ?x ?v WHERE { { ?c bj:daNota ?x }'
         ' UNION { ?c bj:daParagrafo/dcterms:isPartOf ?x } ?c bj:aPassaggio/bj:comprende ?v .'
         ' ?x bj:citaVersetto ?v } }', len(cited)),
        ('quoted-later references in the shortcut',
         'SELECT (COUNT(?r) AS ?n) WHERE { ?r bj:relazione bj:citatoDopo ; bj:stato bj:risolto ;'
         ' bj:daVersetto ?a ; bj:aPassaggio/bj:comprende ?b FILTER (?a != ?b)'
         ' FILTER NOT EXISTS { ?a bj:citatoIn ?b } }', 0),
    ] + integrita_dizionario(dz)


def integrita_dizionario(dz):
    """The dictionary: counts of stage 2b, targets, links and shortcuts."""
    stato = lambda k: sum(1 for c in dz['citations'] if c['status'] == k)  # noqa: E731
    coppie = set((c['voce'], t) for c in dz['citations'] if c['status'] in ('resolved', 'partial')
                 for t in c['targets'])
    corte = 'bj:richiamaVoce|bj:vediAncheVoce|bj:rinviaAVoce'
    return [
        ('dictionary: entries', conta('bj:Voce'), len(dz['voci'])),
        ('dictionary: redirect entries', conta('bj:VoceRinvio'), sum(1 for v in dz['voci'] if v['kind'] == 'redirect')),
        ('dictionary: sections', conta('bj:SezioneVoce'), sum(len(v.get('sections', [])) for v in dz['voci'])),
        ('dictionary: paragraphs', conta('bj:ParagrafoVoce'), sum(len(v.get('paragraphs', [])) for v in dz['voci'])),
        ('dictionary: links between entries', conta('bj:CollegamentoVoce'), len(dz['links'])),
        ('dictionary: unresolved links', conta('bj:CollegamentoVoce', '; bj:stato bj:irrisolto '),
         sum(1 for l in dz['links'] if not l['target'])),
        ('dictionary: citations', conta('bj:Citazione', '; bj:nellaVoce ?v '), len(dz['citations'])),
        ('dictionary: resolved citations', conta('bj:Citazione', '; bj:nellaVoce ?v ; bj:stato bj:risolto '),
         stato('resolved')),
        ('dictionary: partial citations', conta('bj:Citazione', '; bj:nellaVoce ?v ; bj:stato bj:parziale '),
         stato('partial')),
        ('dictionary: unresolved citations', conta('bj:Citazione', '; bj:nellaVoce ?v ; bj:stato bj:irrisolto '),
         stato('unresolved')),
        ('dictionary: citation targets that are not declared verses',
         'SELECT (COUNT(*) AS ?n) WHERE { ?c bj:nellaVoce ?x ; bj:aPassaggio ?p . ?p bj:comprende ?v'
         ' FILTER NOT EXISTS { ?v a bj:Versetto } }', 0),
        ('dictionary: link targets that are not entries',
         'SELECT (COUNT(*) AS ?n) WHERE { ?l bj:aVoce ?t FILTER NOT EXISTS { ?t a bj:Voce } }', 0),
        ('dictionary: target sections outside their target entry',
         'SELECT (COUNT(*) AS ?n) WHERE { ?l bj:aSezione ?s FILTER NOT EXISTS { ?l bj:aVoce ?t . ?s bj:nellaVoce ?t } }', 0),
        ('dictionary: parts outside their entry',
         'SELECT (COUNT(*) AS ?n) WHERE { ?p bj:nellaVoce ?x ; dcterms:isPartOf ?s FILTER (?s != ?x)'
         ' FILTER NOT EXISTS { ?s bj:nellaVoce ?x } }', 0),
        ('dictionary: entry shortcuts backed by a printed link',
         'SELECT (COUNT(*) AS ?n) WHERE { ?a %s ?b FILTER NOT EXISTS { ?l bj:daVoce ?a ; bj:aVoce ?b } }' % corte, 0),
        ('dictionary: skos:related symmetric and backed by a shortcut',
         'SELECT (COUNT(*) AS ?n) WHERE { ?a skos:related ?b FILTER (NOT EXISTS { ?b skos:related ?a }'
         ' || NOT EXISTS { { ?a %s ?b } UNION { ?b %s ?a } }) }' % (corte, corte), 0),
        ('dictionary: voceCitaVersetto = (entry, verse) pairs of the JSON',
         'SELECT (COUNT(*) AS ?n) WHERE { ?x bj:voceCitaVersetto ?v }', len(coppie)),
        ('dictionary: voceCitaVersetto backed by a citation of the entry',
         'SELECT (COUNT(*) AS ?n) WHERE { SELECT DISTINCT ?x ?v WHERE { ?c bj:nellaVoce ?x ;'
         ' bj:aPassaggio/bj:comprende ?v . ?x bj:voceCitaVersetto ?v } }', len(coppie)),
        ('dictionary: citatoNellaVoce is the inverse of voceCitaVersetto',
         'SELECT (COUNT(*) AS ?n) WHERE { { ?x bj:voceCitaVersetto ?v FILTER NOT EXISTS { ?v bj:citatoNellaVoce ?x } }'
         ' UNION { ?v bj:citatoNellaVoce ?x FILTER NOT EXISTS { ?x bj:voceCitaVersetto ?v } } }', 0),
        ('dictionary: verses cited (verse index of dufour.json)',
         'SELECT (COUNT(DISTINCT ?v) AS ?n) WHERE { ?v bj:citatoNellaVoce ?x }', len(dz['verses'])),
    ]


def sparql(g, data, coll, dz, quiet):
    err, rows = [], []
    for name, q, atteso in integrita(data, coll, dz):
        t = time.time()
        n = int(list(g.query(PREFIX + q))[0][0])
        dt = time.time() - t
        rows.append((name, n, atteso, dt))
        if n != atteso:
            err.append('SPARQL %s: %d, expected %d' % (name, n, atteso))
        if not quiet:
            print('  %-66s %7d  %s  %5.1f s' % (name, n, 'ok' if n == atteso else 'EXPECTED %d' % atteso, dt))
    print('  %d queries, %d as expected, %.1f s' % (len(rows), len(rows) - len(err), sum(r[3] for r in rows)))
    return err, rows


# ---------------------------------------------------------------- SHACL

def shacl(g):
    """pyshacl on the whole graph. (Its focus_nodes option compares each target with the
    whole focus list: about 36 ms a node, an hour for the graph; plain validation of
    every target takes about 4.5 minutes.)"""
    from pyshacl import validate
    from rdflib import Graph, RDF
    from rdflib.namespace import SH
    forme = Graph().parse(FORME, format='turtle')
    t = time.time()
    conforms, report, text = validate(g, shacl_graph=forme, inference='none', inplace=True)
    dt = time.time() - t
    risultati = len(set(report.subjects(RDF.type, SH.ValidationResult)))
    forme_n = len(set(forme.subjects(RDF.type, SH.NodeShape)))
    nodi = len(set(g.subjects(RDF.type, None)))
    if not conforms:
        print('\n'.join(text.splitlines()[:40]))
    return conforms, risultati, nodi, forme_n, dt


# ---------------------------------------------------------------- JSON-LD

def jsonld(g):
    """John 3,16 with its notes, their bodies, its margin entries and references and their
    passages, and the entry ABELE with its sections, paragraphs, citations and links:
    serialised with the context, parsed back, compared."""
    from rdflib import Graph, URIRef
    ctx = json.load(open(CONTESTO, encoding='utf-8'))['@context']
    B = lambda x: URIRef(BJ + x)  # noqa: E731
    v = URIRef(PREFISSI['verso'] + 'John.3.16')
    note = list(g.objects(v, B('haNota')))
    rimandi = list(g.subjects(B('daVersetto'), v))
    voce = URIRef(PREFISSI['voce'] + 'abele')
    risorse = [v] + note + [g.value(n, URIRef(PREFISSI['oa'] + 'hasBody')) for n in note] + rimandi + \
        list(g.subjects(B('accantoA'), v)) + [p for r in rimandi for p in g.objects(r, B('aPassaggio'))] + \
        [voce] + list(g.subjects(B('nellaVoce'), voce))
    sub = Graph()
    for x in risorse:
        for t in g.triples((x, None, None)):
            sub.add(t)
    doc = sub.serialize(format='json-ld', context=ctx, auto_compact=True)
    back = Graph().parse(data=doc, format='json-ld')
    usa_termini = all(k in doc for k in ('"testoIt"', '"rimandaA"', '"haNota"', '"aPassaggio"', '"hasBody"',
                                         '"pagina"', '"pag:', '"verso:John.3.16"', '"citatoNellaVoce"',
                                         '"voce:abele"', '"prefLabel"', '"nellaVoce"', '"pagdiz:'))
    return set(sub) == set(back) and len(sub) > 0 and usa_termini, len(sub)


def main(a):
    quiet = '-q' in a
    t0 = time.time()
    err = []
    with Pool(2) as pool:
        lavori = pool.map_async(parse_rdflib, [(NT, 'nt'), (TTL, 'turtle')])
        t = time.time()
        g = grafo.carica(ontologia=False, store='Memory')     # pyshacl needs a context-aware store
        print('fast reader: %d triples in %.1f s' % (len(g), time.time() - t), flush=True)
        from rdflib import Graph
        ont = Graph().parse(ONTOLOGIA, format='turtle')
        for k, v in PREFISSI.items():
            g.bind(k, v, override=True)
        data = json.load(open(BIBBIA, encoding='utf-8'))
        coll = json.load(open(COLLEGAMENTI, encoding='utf-8'))
        dz = json.load(open(DUFOUR, encoding='utf-8'))
        e, ndecl, nchecked = owl(g, ont)
        err += e
        print('OWL: ontology %d triples, %d bj: terms declared; domain/range of %d triples checked: %s'
              % (len(ont), ndecl, nchecked, 'ok' if not e else '%d errors' % len(e)), flush=True)
        print('SPARQL integrity (whole graph):', flush=True)
        e, _ = sparql(g, data, coll, dz, quiet)
        err += e
        mio = digest(g)
        for fmt, dg, dt in lavori.get():
            ok = dg == mio
            print('parser %-7s %d triples in %.1f s, %s the fast reader' % (
                fmt, dg[0], dt, 'same graph as' if ok else 'DIFFERENT from'), flush=True)
            if not ok:
                err.append('%s parse differs from the fast reader' % fmt)
    ok, n = jsonld(g)
    print('JSON-LD context: %d triples round-tripped: %s' % (n, 'ok' if ok else 'FAILED'))
    if not ok:
        err.append('JSON-LD round trip')
    conforms, risultati, n, nforme, dt = shacl(g)
    print('SHACL (whole graph, %d node shapes, %d typed resources): %s, %d violations, %.1f s' % (
        nforme, n, 'conforms' if conforms else 'DOES NOT CONFORM', risultati, dt))
    if not conforms:
        err.append('SHACL: %d violations' % risultati)
    for x in err[:30]:
        print('ERROR  ' + x)
    print('checks: %s (%.0f s)' % ('ok' if not err else '%d errors' % len(err), time.time() - t0))
    return 1 if err else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
