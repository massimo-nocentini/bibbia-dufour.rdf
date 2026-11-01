"""Tests of virgolette.py, the quotation detector shared by the ontology, the explorer and the Tufte edition.

usage: vendor/venv/bin/python -I tools/ontologia/test_virgolette.py [-v]

Two kinds of cases: strings (the rules: matching, nesting, unbalanced guillemets, what is skipped, the
runs set in italic), and real quotations of ontologia/build/discorsi.json (virgolette.py, after
estrai.py and paratesto.py): Gen 1,3, Moses' discourse Dt 5,1-26,19 with the nested ones of Dt 20-22,
the two unbalanced guillemets of the text and their reasons, a poem, a note, the counts by part. Plain
asserts, so it also runs under pytest. Exit status 1 if a case fails.
"""
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import virgolette as V  # noqa: E402

_cache = {}


def dati():
    if not _cache:
        Q = json.load(open(V.OUT, encoding='utf-8'))['discorsi']
        _cache.update(Q=Q, per_id={x['id']: x for x in Q})
    return _cache['Q'], _cache['per_id']


def test_accoppia():
    pairs, bad = V.accoppia([(0, '«'), (1, '«'), (2, '»'), (3, '»'), (4, '«'), (5, '»')])
    assert pairs == [(0, 3, None), (1, 2, 0), (4, 5, None)], pairs
    assert bad == []
    # a » with none open, then a « never closed; the pair after the open one is not inside it
    pairs, bad = V.accoppia([(0, '»'), (1, '«'), (2, '«'), (3, '»')])
    assert pairs == [(2, 3, None)] and bad == [(0, '»'), (1, '«')], (pairs, bad)


def test_html():
    # guillemets inside <em> are skipped (already italic)
    assert V.eventi_html('a «b» <em>«c»</em>') == [(2, '«'), (4, '»')]
    # one scope across segments; offsets of the guillemets; the plain offset maps <br> to a line end
    q = V.trova([('a', 'disse: «Va’'), ('b', 'pure<br>e poi». Fine')])
    assert len(q) == 1 and q[0]['apre'] == [0, 7] and q[0]['chiude'] == [1, 13] and q[0]['padre'] is None
    assert V.piano('pure<br>e poi».', 13) == 10
    # the runs: split at <br> and at a cut, an <em> inside kept, the spaces at the edges outside;
    # a run only in italic already («<em>bohû</em>») is not set
    segs = [(0, '«il <em>tohû</em> è<br>vuoto» e «<em>bohû</em>»')]
    r = V.corse(segs)[0]
    h = segs[0][1]
    assert [h[r[j]:r[j + 1]] for j in range(0, len(r), 2)] == ['il <em>tohû</em> è', 'vuoto'], r
    assert V.corsivo([(0, '«a b»')]) == ['«<i class="ds">a b</i>»']
    r = V.corse([(0, '«uno due»')], tagli={0: [4]})[0]
    assert r == [1, 4, 5, 8], r
    # ... but not inside an <em> (the LaTeX keeps an \emph whole): the run stays whole and well nested
    h = '«a <em>b c</em> d»'
    r = V.corse([(0, h)], tagli={0: [8]})[0]
    assert r == [1, len(h) - 1] and V.bilanciato(V.corsivo([(0, h)])[0]), r
    # a tag crossing the end of the quotation: the run stops before it and goes on inside it
    r = V.corse([(0, '«a <strong>b» c</strong>')])[0]
    assert r == [1, 2, 11, 12], r


def test_reali():
    Q, per = dati()
    g = per['Gen.1.3.1']
    assert g['text'] == 'Sia la luce!' and g['start'] == dict(seg='Gen.1.3', html=11, testo=11), g
    dt = per['Deut.5.1.1']
    assert dt['end']['seg'] == 'Deut.26.19' and len(dt['segments']) == 532 and dt['parent'] is None
    nested = [x for x in Q if x['part'] == 'testo' and x['parent'] is not None]
    assert len(nested) == 7 and all(Q[x['parent']]['id'] == 'Deut.5.1.1' for x in nested), [x['id'] for x in nested]
    sir, am = per['Sir.16.22.1'], per['Amos.7.17.1']
    assert sir['end'] is None and 'inside italic text (Sir.16.22)' in sir['unbalanced'], sir
    assert am['start'] is None and 'closed in Amos.7.14' in am['unbalanced'], am
    # a poem: Sal 2,3 on two lines, its words with the line end
    s = next(x for x in Q if x['start'] and x['start']['seg'] == 'Ps.2.3')
    assert s['text'].startswith('Spezziamo le loro catene,\n'), s
    # a note: \detto is a quotation of the note (Sir 16,22: «decreto»)
    n = per['nota/Sir.16.22.1']
    assert n['part'] == 'nota' and n['text'] == 'decreto', n
    # an index headword and the edition
    assert per['indice/note/voce/403.1']['text'] == 'Padre nostro'
    assert [x['text'] for x in Q if x['source'] == 'edizione'] == ['editio princeps', 'editio princeps',
                                                                   'La Tipografica Varese S.p.A.']


def test_conti():
    Q, _ = dati()
    c = Counter((x['part'], 'unbalanced' if x.get('unbalanced') else 'nested' if x['parent'] is not None
                 else 'outermost') for x in Q)
    # the text equals the Tufte edition (tools/tufte/test_genera.py, test_lettori: book by book)
    assert (c['testo', 'outermost'], c['testo', 'nested'], c['testo', 'unbalanced']) == (5948, 7, 2), c
    assert c['preliminari', 'outermost'] == 59, c
    assert c['nota', 'outermost'] > 10000 and c['introduzione', 'outermost'] > 500, c


TESTS = [test_accoppia, test_html, test_reali, test_conti]


def main(a):
    failed = 0
    for t in TESTS:
        try:
            t()
            if '-v' in a:
                print('ok   %s' % t.__name__)
        except AssertionError as e:
            failed += 1
            print('FAIL %s: %s' % (t.__name__, e))
    print('test_virgolette: %d tests: %s' % (len(TESTS), 'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
