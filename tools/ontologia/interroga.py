"""Run SPARQL queries on the verse graph and print the results as a table.

usage: interroga.py <query.rq> [<query.rq> ...] [--limite N] [--largo] [--tsv] [--riepilogo F]
       interroga.py -e "SELECT ?v WHERE { ?v bj:haNota ?n } LIMIT 5"

Loads ontologia/bj-dati.nt.gz and the ontology once (grafo.py, about 20 s) and runs
each query in turn. Queries given with -e may use the prefixes of the data without
declaring them (bj:, verso:, libro:, nota:, dcterms:, oa:, skos:, ...). IRIs are
printed in their short form (verso:John.3.16), long values are cut at 70 characters
(--largo keeps them whole, --tsv prints tab-separated values); --limite N prints only
the first N rows (the count is of all of them). After several queries a summary of rows
and timings is printed; --riepilogo F also writes it to F as a Markdown table. Exit
status 1 if a query returns no rows.
For faster queries, load the .nt.gz into Oxigraph, Fuseki or GraphDB (README).
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import grafo  # noqa: E402
from rdflib import URIRef  # noqa: E402
from rdf import C, PREFISSI  # noqa: E402

LARGHEZZA = 70


def valore(x, g):
    if x is None:
        return ''
    if isinstance(x, URIRef):
        return g.namespace_manager.normalizeUri(x)
    return str(x)


def tabella(rows, vars_, largo, tsv, limite):
    if tsv:
        return '\n'.join(['\t'.join(vars_)] + ['\t'.join(c.replace('\t', ' ').replace('\n', ' ') for c in r)
                                               for r in rows[:limite]])
    rows = [[c.replace('\n', ' / ') for c in r] for r in rows[:limite]]
    if not largo:
        rows = [[c if len(c) <= LARGHEZZA else c[:LARGHEZZA - 1] + '…' for c in r] for r in rows]
    w = [max([len(v)] + [len(r[k]) for r in rows]) for k, v in enumerate(vars_)]
    line = lambda r: '  '.join(c.ljust(w[k]) for k, c in enumerate(r)).rstrip()  # noqa: E731
    return '\n'.join([line(vars_), line(['-' * x for x in w])] + [line(r) for r in rows])


def esegui(g, testo, largo=False, tsv=False, limite=None):
    t = time.time()
    res = g.query(testo, initNs=PREFISSI)
    vars_ = [str(v) for v in res.vars]
    rows = [[valore(x, g) for x in r] for r in res]
    dt = time.time() - t
    print(tabella(rows, vars_, largo, tsv, limite))
    print('(%d rows, %.2f s)' % (len(rows), dt), flush=True)
    return len(rows), dt


def main(a):
    opt = lambda k: a[a.index(k) + 1] if k in a else None  # noqa: E731
    limite = int(opt('--limite')) if opt('--limite') else None
    riepilogo = opt('--riepilogo')
    largo, tsv = '--largo' in a, '--tsv' in a
    salta = {x for k in ('--limite', '--riepilogo', '-e') if k in a for x in (k, opt(k))}
    query = [(f, open(f, encoding='utf-8').read()) for f in a if f not in salta and not f.startswith('--')]
    if '-e' in a:
        query.append(('-e', opt('-e')))
    if not query:
        sys.exit(__doc__)
    t = time.time()
    g = grafo.carica()
    print('graph: %d triples loaded in %.1f s' % (len(g), time.time() - t), file=sys.stderr, flush=True)
    sommario = []
    for nome, testo in query:
        if len(query) > 1:
            print('\n== %s' % nome)
        n, dt = esegui(g, testo, largo, tsv, limite)
        sommario.append((os.path.basename(nome), n, dt))
    if len(query) > 1:
        print('\n%-28s %8s %9s' % ('query', 'rows', 'seconds'))
        for nome, n, dt in sommario:
            print('%-28s %8d %9.2f' % (nome, n, dt))
    if riepilogo:
        with open(riepilogo, 'w', encoding='utf-8') as f:
            f.write('| query | rows | seconds |\n|---|---:|---:|\n')
            f.writelines('| `%s` | %d | %.2f |\n' % r for r in sommario)
        print('wrote %s' % os.path.relpath(riepilogo, C))
    vuote = [nome for nome, n, _ in sommario if not n]
    if vuote:
        print('ERROR  no rows: ' + ', '.join(vuote))
    return 1 if vuote else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
