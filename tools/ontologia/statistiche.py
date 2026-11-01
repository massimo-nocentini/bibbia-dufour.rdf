"""Write the numbers of ontologia/README.md from the build: the Size tables from bj-void.ttl and the
rows and timings of the examples from build/query.md.

usage: statistiche.py [-q] [--controlla]

The README holds two generated blocks, each between an HTML comment that opens it
(`<!-- generato da tools/ontologia/statistiche.py: dimensioni -->` and `...: query -->`) and
`<!-- fine del blocco generato -->`. The size block is made from the VoID description (triples,
subjects, entities, the four subsets, the classes and the 30 largest properties); the query block
keeps the Question column already written in the README for a query and takes it from the English
comment of the .rq file for a new one. With --controlla nothing is written: exit status 1 if the
README is not up to date (the check of costruisci.py, after interroga.py).
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
README = os.path.join(C, 'ontologia', 'README.md')
VOID = os.path.join(C, 'ontologia', 'bj-void.ttl')
QUERY = os.path.join(C, 'ontologia', 'build', 'query.md')
APRI = '<!-- generato da tools/ontologia/statistiche.py: %s -->'
CHIUDI = '<!-- fine del blocco generato -->'
SITO = 'https://massimo-nocentini.github.io/bibbia-gerusalemme/'
PARTI = [('bibbia', 'the Bible'), ('dizionario', 'the dictionary'), ('paratesto', 'the front matter and appendices'),
         ('integrazione', 'the links between the parts, the calendar, measures and maps, the corrections')]


def num(n):
    return '{:,}'.format(n)


def dimensioni():
    from rdflib import Graph, Namespace, URIRef
    V = Namespace('http://rdfs.org/ns/void#')
    g = Graph().parse(VOID, format='turtle')
    D = URIRef(SITO + 'dati')
    tot = int(g.value(D, V.triples))
    out = ['%s triples about %s subjects (%s typed resources), %s classes, %s properties. Four VoID subsets:' % (
        num(tot), num(int(g.value(D, V.distinctSubjects))), num(int(g.value(D, V.entities))),
        g.value(D, V.classes), g.value(D, V.properties))]
    for k, nome in PARTI:
        out.append('- %s: %s triples (`vp:%s`);' % (nome, num(int(g.value(URIRef(SITO + 'void#' + k), V.triples))), k))
    link = []
    for ls in sorted(g.subjects(V.linkPredicate, None)):
        p = g.value(ls, V.linkPredicate)
        link.append('`%s` %s' % (g.namespace_manager.normalizeUri(p), num(int(g.value(ls, V.triples)))))
    out[-1] = out[-1][:-1] + '.'
    out += ['', 'Linksets: ' + ', '.join(link) + '.', '']
    classi = sorted(((int(g.value(c, V.entities)), g.namespace_manager.normalizeUri(g.value(c, V['class'])))
                     for c in g.objects(D, V.classPartition)), reverse=True)
    prop = sorted(((int(g.value(c, V.triples)), g.namespace_manager.normalizeUri(g.value(c, V.property)))
                   for c in g.objects(D, V.propertyPartition)), reverse=True)[:len(classi)]
    out += ['| Class | Resources | Property (largest) | Triples |', '|---|---:|---|---:|']
    for k in range(max(len(classi), len(prop))):
        a = classi[k] if k < len(classi) else ('', '')
        b = prop[k] if k < len(prop) else ('', '')
        out.append('| %s | %s | %s | %s |' % ('`%s`' % a[1] if a[1] else '', num(a[0]) if a[1] else '',
                                              '`%s`' % b[1] if b[1] else '', num(b[0]) if b[1] else ''))
    return out


def query(testo):
    vecchie = {}
    for m in re.finditer(r'^\| `(\d\d-[^`]+\.rq)` \| (.*?) \| [\d,]+ \| [\d.]+ \|$', testo, re.M):
        vecchie[m.group(1)] = m.group(2)
    rows = re.findall(r'^\| `([^`]+)` \| (\d+) \| ([\d.]+) \|$', open(QUERY, encoding='utf-8').read(), re.M)
    out = ['| Query | Question | Rows | Seconds |', '|---|---|---:|---:|']
    for f, n, t in rows:
        q = vecchie.get(f)
        if not q:
            com = [x[2:].strip() for x in open(os.path.join(C, 'ontologia', 'query', f), encoding='utf-8')
                   if x.startswith('# ')]
            q = ' '.join(com[len(com) // 2:]) if com else f      # the English half of the comment
            q = q[0].lower() + q[1:].rstrip('.') if q else q
        out.append('| `%s` | %s | %s | %s |' % (f, q, n, t))
    if len(rows) != len(glob.glob(os.path.join(C, 'ontologia', 'query', '*.rq'))):
        sys.exit('statistiche: %s is stale (run interroga.py on every query first)' % os.path.relpath(QUERY, C))
    return out


def sostituisci(testo, nome, righe):
    a, z = APRI % nome, CHIUDI
    i = testo.index(a) + len(a)
    j = testo.index(z, i)
    return testo[:i] + '\n' + '\n'.join(righe) + '\n' + testo[j:]


def main(a):
    testo = open(README, encoding='utf-8').read()
    nuovo = sostituisci(sostituisci(testo, 'dimensioni', dimensioni()), 'query', query(testo))
    if '--controlla' in a:
        if nuovo != testo:
            print('statistiche: %s is not up to date (run tools/ontologia/statistiche.py)' % os.path.relpath(README, C))
            return 1
        print('statistiche: %s up to date' % os.path.relpath(README, C))
        return 0
    if nuovo != testo:
        open(README, 'w', encoding='utf-8').write(nuovo)
    print('statistiche: %s %s' % (os.path.relpath(README, C), 'written' if nuovo != testo else 'unchanged'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
