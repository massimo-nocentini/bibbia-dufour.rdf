"""Load the verse graph (ontologia/bj-dati.nt.gz + the ontology) into rdflib, fast.

usage: from grafo import carica; g = carica()

rdflib's own N-Triples parser needs about 2 minutes for the 3.5 million triples; this
reader knows the subset rdf.py writes (one triple per line, IRIs in <>, literals with
only \\\\ \\" \\n \\r escaped, @it/@en or ^^<datatype>) and builds the terms itself, each
once, into a SimpleMemory store (no named graphs, half the insertion cost of Memory):
about 45 s. A pickled store is no faster to load (about 47 s, 650 MB), so there is
no cache. verifica_rdf.py checks that this reader and rdflib's parser give the same
graph.
"""
import gzip
import os
import re
import sys

from rdflib import Graph, Literal, URIRef

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rdf import NT, ONTOLOGIA, PREFISSI  # noqa: E402

LITERAL = re.compile(r'"(.*)"(?:@([A-Za-z\-]+)|\^\^<([^>]*)>)?$', re.S)
ESCAPE = re.compile(r'\\(.)')
ECHAR = {'n': '\n', 'r': '\r', '"': '"', '\\': '\\', 't': '\t'}


def termine(x):
    if x[0] == '<':
        return URIRef(x[1:-1])
    m = LITERAL.match(x)
    if not m:
        raise ValueError('not a term of rdf.py: %r' % x[:80])
    v = m.group(1)
    if '\\' in v:
        v = ESCAPE.sub(lambda e: ECHAR[e.group(1)], v)
    return Literal(v, lang=m.group(2), datatype=URIRef(m.group(3)) if m.group(3) else None)


def triple(path=NT):
    """The triples of an N-Triples file written by rdf.py, each term built once."""
    termini = {}
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        for n, line in enumerate(f, 1):
            if not line.endswith(' .\n'):
                raise ValueError('%s:%d: not a triple line' % (path, n))
            s, p, o = line[:-3].split(' ', 2)
            out = []
            for x in (s, p, o):
                t = termini.get(x)
                if t is None:
                    t = termini[x] = termine(x)
                out.append(t)
            yield tuple(out)


def carica(path=NT, ontologia=True, store='SimpleMemory'):
    """The data graph, plus the ontology (labels of the classes and SKOS concepts)."""
    g = Graph(store=store)
    g.addN((s, p, o, g) for s, p, o in triple(path))
    if ontologia:
        g.parse(ONTOLOGIA, format='turtle')
    for k, v in PREFISSI.items():
        g.bind(k, v, override=True)
    return g

