"""Rebuild the verse ontology from the proofread volumes, every stage in order.

usage: vendor/venv/bin/python -I tools/ontologia/costruisci.py   (or: make ontologia)

Each stage is a script of this folder, run with the same Python; the build stops at
the first stage whose checks fail.
  estrai.py             progetti/<volume>/*.tex -> ontologia/build/bibbia.json
  riferimenti.py        bibbia.json -> ontologia/build/collegamenti.json (typed links)
  test_riferimenti.py   the reference parser on strings of the corpus
  dufour.py             ../dufour/corpus (Dizionario di Teologia Biblica, read only) + bibbia.json
                        -> ontologia/build/dufour.json (entries, citations resolved to verses)
  test_dufour.py        the citations of the dictionary on real rows
  rdf.py                the three JSON files (Bible, links, dictionary) -> ontologia/bj-dati.{ttl,nt}.gz,
                        bj-contesto.jsonld, bj-void.ttl
  verifica_rdf.py       parsers, OWL sanity, SPARQL integrity, SHACL (whole graph), JSON-LD
  interroga.py          every ontologia/query/*.rq; rows and timings in ontologia/build/query.md
  esploratore.py        the three JSON files -> ontologia/esplora.html (offline explorer)

The headless browser test of the page, tools/ontologia/prova_esploratore.mjs, needs
playwright-core outside the repository and is not run here (see the README).
"""
import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
QUERY = sorted(glob.glob(os.path.join(C, 'ontologia', 'query', '*.rq')))

PASSI = [
    ['estrai.py', '-q'],
    ['riferimenti.py', '-q'],
    ['test_riferimenti.py'],
    ['dufour.py', '-q'],
    ['test_dufour.py'],
    ['rdf.py', '-q'],
    ['verifica_rdf.py', '-q'],
    ['interroga.py', '--limite', '5', '--riepilogo', os.path.join(C, 'ontologia', 'build', 'query.md')] + QUERY,
    ['esploratore.py', '-q'],
]


def main():
    for passo in PASSI:
        print('== ' + ' '.join(os.path.relpath(x, C) if x.startswith(C) else x for x in passo), flush=True)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, passo[0])] + passo[1:])
        if r.returncode:
            sys.exit('%s failed (exit %d)' % (passo[0], r.returncode))


if __name__ == '__main__':
    main()
