"""Tests of dufour.py on real rows of the Dizionario di Teologia Biblica (biblerefs.tsv).

usage: vendor/venv/bin/python -I tools/ontologia/test_dufour.py [-v] [--dufour ../dufour/corpus]

Needs ontologia/build/bibbia.json (estrai.py), the Dufour corpus (read only) and, for
test_file, ontologia/build/dufour.json (dufour.py). The entries are built in memory once
(dufour.prepara, about 6 s). Each case names a citation by its id (<slug>#<n>, the n-th
row of the entry in biblerefs.tsv) and the raw text that row must have, so a case cannot
test a string the dictionary does not print; only the keys given are compared ('reason'
and 'inferred' by prefix, 'conversion' by substring). Plain asserts, so it also runs
under pytest. Exit status 1 if a case fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dufour as D  # noqa: E402

_cache = {}


def costruito():
    if not _cache:
        p = D.prepara(D.cartella(sys.argv[1:]), D.IN)
        _cache.update(p, by_id={c['id']: c for c in p['citations']},
                      paragrafi={x['id']: x for v in p['voci'] for x in v.get('paragraphs', [])},
                      voci={v['id']: v for v in p['voci']})
    return _cache


def one(first, last=None, **kw):
    """Expected: resolved, one stretch first-last."""
    return dict(status='resolved', ranges=[[first, last or first]], **kw)


# (citation id, raw as printed, expected)
CASES = [
    # ---- psalms: Hebrew numbering of the CEI, titles are verses
    ('abele#3', 'Sal 10, 9- 11', one('Ps.10.9', 'Ps.10.11', book='Ps')),
    ('pastore-e-gregge#12', 'Sal 23, 1', one('Ps.23.1')),              # «il mio pastore»
    ('peccato#102', 'Sal 51', one('Ps.51.1', 'Ps.51.21')),             # the Miserere
    ('consolare#16', 'Sal 22, 2 s', one('Ps.22.2', 'Ps.22.3', flags=['s'])),   # «Dio mio, Dio mio»
    ('comunione#12', 'Sal 119', one('Ps.119.1', 'Ps.119.176')),
    ('fede#137', '8', one('Ps.8.1', 'Ps.8.10', implicit=1)),          # a chain of psalms: Sal ...; 8
    ('misericordia#49', 'Sal 103, 8 ss. 13 s', one('Ps.103.8', 'Ps.103.12', flags=['ss'])),   # ss stops before 13
    ('misericordia#50', 'Sal 103, 8 ss. 13 s', one('Ps.103.13', 'Ps.103.14', flags=['s'])),
    # ---- s, ss, par., '...'
    ('abele#6', 'Mt 23, 35 s', one('Matt.23.35', 'Matt.23.36', flags=['s'])),
    ('apostoli#36', 'Mt 28, 18 ss', one('Matt.28.18', 'Matt.28.20', flags=['ss'])),   # to the end of the pericope
    ('adamo#63', 'Mt 19, 4 s par.', one('Matt.19.4', 'Matt.19.5', flags=['p', 's'])),
    ('angeli#102', 'Mt 28, 5 ss par.', one('Matt.28.5', 'Matt.28.8', flags=['p', 'ss'])),
    ('alleanza#71', 'Deut 30, 15...', one('Deut.30.15', flags=['...'])),
    ('egitto#5', 'Ger 42 s', one('Jer.42.1', 'Jer.43.13', flags=['s'])),       # a chapter and the next
    ('egitto#2', '42 ss', one('Gen.42.1', 'Gen.42.38', flags=['ss'])),
    # ---- ranges across chapters, chapter ranges, one-chapter books
    ('adamo#52', 'Gen 2, 8 - 3, 21', one('Gen.2.8', 'Gen.3.21')),
    ('amore#275', 'Ef 4, 25 - 5, 2', one('Eph.4.25', 'Eph.5.2')),
    ('abramo#77', 'Rom 9-11', one('Rom.9.1', 'Rom.11.36')),
    ('bestie-e-bestia#42', 'Gioe 1 - 2', one('Joel.1.1', 'Joel.2.27')),
    ('anticristo#4', '2 Gv 7', one('2John.1.7')),
    ('schiavo#19', 'Filem 14-21', one('Phlm.1.14', 'Phlm.1.21')),      # '-21' left in the qualifier by the source
    # ---- implicit book: inherited (1), named in the prose (2), read in another book of the paragraph
    ('abele#8', '18, 24', one('Rev.18.24', implicit=0)),               # a chain after Apoc 16, 6
    ('adorazione#64', '13, 4-15', one('Rev.13.4', 'Rev.13.15', implicit=2)),
    ('maria#20', '1, 46-55', one('Luke.1.46', 'Luke.1.55', inferred='book Lc of the paragraph')),
    ('predicare#40', '8, 32 s', one('Acts.8.32', 'Acts.8.33', inferred='book At')),
    ('pasqua#128', '13', dict(status='unresolved', reason='no chapter 1Pt 13', reason_kind='ambiguous-book')),
    # ---- numbering: Joel, Malachi, Daniel, Kings, Sirach / Qoelet, Esther
    ('segno#175', 'Gioe 3, 1-5', one('Joel.3.1', 'Joel.3.5')),
    ('fuoco#77', 'Mal 3, 19', one('Mal.3.19')),
    ('lode#112', 'Dan 3, 51-90', one('Dan.3.51', 'Dan.3.90')),
    ('adorazione#15', '1 Re 19, 18', one('1Kgs.19.18')),
    ('abramo#25', 'Eccli 44, 19', one('Sir.44.19')),
    ('bene-e-male#40', 'Eccle 1, 2', one('Eccl.1.2')),
    ('adorazione#42', 'Est 3, 2. 5', one('Esth.3.2')),
    ('padri-e-padre#15', 'Est 3, 13f', one('EsthGr.3.13f', conversion='letter f')),
    ('padri-e-padre#16', '8, 12l', one('EsthGr.8.12l', conversion='8,121 read as 8,12l')),
    ('liberazione-liberta#59', 'Est 4, 17', one('EsthGr.4.17g', conversion='letter g')),   # «Est 4, 17 g LXX»
    ('preghiera#55', 'Est 4, 17', one('EsthGr.4.17a', 'EsthGr.4.17z', conversion='prayers of the Greek text')),
    # ---- the source's own corrections and misreadings
    ('eucaristia#21', 'Mi 14, 19 par.', one('Matt.14.19', flags=['p'], source_status='fixed')),
    ('fedelta#71', 'Mi 25, 21. 23', one('Matt.25.21', source_status='fixed')),
    ('fedelta#72', 'Mi 25, 21. 23', one('Matt.25.23', source_status='fixed')),
    ('bene-e-male#46', 'Es 3, 7s', one('Exod.3.7', 'Exod.3.8', flags=['s'], conversion="'s' glued")),
    ('maria#89', 'Gv 3, 2l', one('John.3.21')),                        # 'l' printed for '1'
    # ---- out of range, partial, noncanonical, odd
    ('disegno-di-dio#81', 'Mt 31, 38 s', dict(status='unresolved', source_status='out_of_range',
                                              reason='no chapter Mt 31 (Mt has 28)', reason_kind='out-of-range')),
    ('edificare#36', 'Gios 28, 16', dict(status='unresolved', reason='no chapter Gs 28', targets=[])),
    ('carne#66', '1 Gv 15, 50', dict(status='unresolved', reason='no chapter 1Gv 15')),
    ('confessione#51', 'Apoc 15, 15', dict(status='unresolved', source_status='ok', reason='no verse Ap 15,15')),
    ('ricchezza#30', 'Sap 7, 8-41', dict(status='partial', ranges=[['Wis.7.8', 'Wis.7.30']],
                                         reason='no verse Sap 7,41')),
    ('ricchezza#30', 'Sap 7, 8-41', dict(status='partial', reason='no verse Sap 7,41')),
    ('battesimo#49', 'Didachè 7, 3', dict(status='unresolved', source_status='noncanonical', book=None,
                                          reason='extra-canonical book Didachè', reason_kind='extra-canonical')),
    ('elezione#19', 'Enoch 5, 24', dict(status='unresolved', reason='extra-canonical book Enoch')),
    ('profeta#45', 'Deut 18, 14-9', dict(status='unresolved', reason='reversed range', reason_kind='other')),
    # ---- audit 2: a bare reference after an aside ('(14, 16; cfr. Mt 28, 20)') goes on with
    #      the book in force before the aside, not the aside's
    ('paraclito#24', '14, 17', one('John.14.17', inferred='book Gv in force before the aside Mt 28, 20')),
    ('paraclito#30', '6, 69', one('John.6.69')),
    ('predicare#38', '3, 18', one('Acts.3.18', inferred='book At in force before the aside Deut 21, 23')),
    ('predicare#49', '2, 21. 39', one('Acts.2.21')),                   # one printed group, one book
    ('predicare#50', '2, 21. 39', one('Acts.2.39')),
    ('processo#86', '5, 18', one('John.5.18')),                        # not Mark 5,18
    ('processo#88', '10, 22- 38', one('John.10.22', 'John.10.38')),
    ('fede#398', '14, 10 s', one('John.14.10', 'John.14.11', inferred='book Gv in force before the aside Es 3')),
    ('fede#396', '10, 30', one('John.10.30')),                          # was unresolved in Exodus
    ('esodo#61', '1, 14 s', one('1Pet.1.14', '1Pet.1.15')),             # '(1 Piet ...; cfr. Es 12, 5; Is 52, 3)'
    ('esodo#63', '2, 9', one('1Pet.2.9')),
    ('sacerdozio#154', '5, 1-4', one('Heb.5.1', 'Heb.5.4')),
    ('croce#41', '19, 30', one('John.19.30')),
    ('poveri#59', '9, 14-19', one('Ps.9.14', 'Ps.9.19')),              # '(cfr. Sal 18, 28)' opens its parentheses
    ('miracolo#238', '11, 4', one('John.11.4')),                        # '(12, 33; cfr. 3, 14 = Num 21, 8)'
    ('esortare#26', '5, 12', one('1Pet.5.12', inferred='book 1Pt named in the prose')),   # 'prima lettera di Pietro (5, 12)'
    ('pasqua#17', '13, 8 ss', one('Exod.13.8', 'Exod.13.10', inferred='book Es of the paragraph, like')),
    ('pastore-e-gregge#125', '10, 15. 17 s', one('John.10.15', inferred='by hand')),
    # ---- Sirach 34-36: the older verse division, converted to the CEI
    ('miracolo#82', 'Eccli 36, 5', one('Sir.36.6', 'Sir.36.7', conversion='older verse division')),  # «Rinnova i prodigi»
    ('segno#123', 'Eccli 36, 5 s', one('Sir.36.6', 'Sir.36.9', flags=['s'])),
    ('ascensione#38', 'Eccli 35, 16 s', one('Sir.35.20', 'Sir.35.21')),   # the prayer that reaches the clouds
    ('tristezza#6', '36, 20', one('Sir.36.22')),                          # «Un cuore perverso»
    ('culto#47', 'Eccli 34, 18 ss', one('Sir.34.21', 'Sir.34.31', flags=['ss'])),   # the unjust sacrifice
    ('israele#72', 'Eccli 36, 10', one('Sir.36.13')),                      # «Raduna tutte le tribù»
    ('sapienza#50', '36, 1-17', one('Sir.36.1', 'Sir.36.19')),            # the whole prayer
    ('matrimonio#71', 'Eccli 36 - 25 ss', one('Sir.36.27', 'Sir.36.28', flags=['ss'])),
    ('sogni#4', 'Eccli 34, 6', one('Sir.34.6', conversion=None)),          # unchanged before 34,10
    # ---- Obadiah printed 'Ab', ranges the source split, misprints
    ('fuoco#89', 'Ab 18', one('Obad.1.18', book='Obad', conversion='Obadiah')),
    ('vendemmia#31', 'Ab 5 s', one('Obad.1.5', 'Obad.1.6', flags=['s'])),
    ('odio#83', 'Ab 10, 14', dict(status='resolved', ranges=[['Obad.1.10', 'Obad.1.10'], ['Obad.1.14', 'Obad.1.14']])),
    ('forza#23', 'Ab 3', one('Obad.1.3', conversion='by hand')),
    ('guerra#75', 'Mt 26 - 52', one('Matt.26.52', conversion="'26 - 52' read as the verse 26,52")),
    ('calamita#2', 'Mt 24-22', one('Matt.24.22')),
    ('nuovo#39', '47, 13-48. 29', one('Ezek.47.13', 'Ezek.48.29', conversion='across chapters')),
    ('nuovo#40', '47, 13-48. 29', one('Ezek.48.29')),
    ('nuovo#78', 'Ebr 8, 1-10. 18', one('Heb.8.1', 'Heb.10.18')),
    ('babele-babilonia#49', 'Deut 2 - 4', one('Dan.2.1', 'Dan.4.34', book='Dan')),
    ('altare#43', '1 Cor 9, 26-30', one('1Chr.9.26', '1Chr.9.30')),
    ('tempio#13', 'Es 33, 7-l l', one('Exod.33.7', 'Exod.33.11')),
    ('profeta#226', '1 s 65, 2', one('Isa.65.2', conversion="is the OCR of 'Is 65, 2'")),
    # ---- 'ss' stops before the next verse printed in the same group
    ('confessione#27', '9, 15 ss. 30-33', one('John.9.15', 'John.9.29', flags=['ss'])),
    ('cielo#16', 'Giob 38, 4 ss. 16 ss', one('Job.38.4', 'Job.38.15', flags=['ss'])),
    # ---- bare references the source did not link (FEDE after a paragraph on John)
    ('fede#r1', '5, 24', one('John.5.24', implicit=3, source_status='recovered')),
    ('fede#r5', '3, 16', one('John.3.16', inferred='book Gv cited most in the paragraph before it')),
    ('anticristo#r1', '2, 4', one('2Thess.2.4', inferred='by hand')),
    ('terra#r1', '1, 28 s', one('Gen.1.28', 'Gen.1.29')),
    # ---- section titles
    ('apparizioni-di-cristo#88', 'Gv 20, 29', one('John.20.29', where='title', para=None)),
]


def check(cid, raw, expected):
    c = costruito()['by_id'].get(cid)
    if c is None:
        return ['no citation %s' % cid]
    if c['raw'] != raw:
        return ['%s is %r, not %r' % (cid, c['raw'], raw)]
    problems = []
    for k, want in expected.items():
        got = c.get(k)
        if k in ('reason', 'inferred'):
            ok = isinstance(got, str) and got.startswith(want)
        elif k == 'conversion':
            ok = got is None if want is None else isinstance(got, str) and want in got
        else:
            ok = got == want
        if not ok:
            problems.append('%s: %r, expected %r' % (k, got, want))
    return problems


def test_cases():
    bad = {cid: p for cid, raw, exp in CASES for p in [check(cid, raw, exp)] if p}
    assert not bad, bad


def test_testo():
    """'*word' becomes a link without the asterisk; offsets point at the raw text in
    the plain text and in the HTML; glued asterisks."""
    c = costruito()
    p = c['paragrafi']['abele.1']
    assert '*' not in p['text'] and 'il tema del giusto sofferente.' in p['text']
    assert '<a class="voce" data-voce="giusto">giusto</a> <a class="voce" data-voce="sofferenza">sofferente</a>' \
        in p['html']
    x = c['by_id']['abele#3']
    assert p['text'][x['offset']:x['offset'] + x['length']] == 'Sal 10, 9- 11'
    assert p['html'][x['html_offset']:x['html_end']] == 'Sal 10, 9- 11'
    acqua = ' '.join(q['text'] for q in c['voci']['acqua']['paragraphs'])
    assert "al momento dell'uragano porta" in acqua and 'la sua legge, obbedendo alla' in acqua
    assert 'Dio onnipotente' in ' '.join(q['text'] for q in c['voci']['creazione']['paragraphs'])
    t = c['by_id']['apparizioni-di-cristo#88']
    sez = next(s for s in c['voci']['apparizioni-di-cristo']['sections'] if s['path'] == t['sec'])
    assert sez['title'][t['offset']:t['offset'] + t['length']] == 'Gv 20, 29'
    titolo = next(s for s in c['voci']['acqua']['sections'] if s['path'] == 'II 1')
    assert titolo['title_html'] == 'Acque e <a class="voce" data-voce="retribuzione">retribuzione</a> temporale'
    a, b = c['by_id']['fedelta#71'], c['by_id']['fedelta#72']
    assert (a['para'], a['offset'], a['length']) == (b['para'], b['offset'], b['length'])
    # '- *word' after a compound's hyphen: no space left ("diogmòs- persecuzione", revisione R2-03)
    for slug, ok in (('prova-tentazione', 'diogmòs-persecuzione'), ('pastore-e-gregge', 'Cristo-agnello'),
                     ('pietra', 'pietra-memoriale')):
        testo = ' '.join(q['text'] for q in c['voci'][slug]['paragraphs'])
        assert ok in testo and ok.replace('-', '- ') not in testo, (slug, ok)
    assert '<a class="voce" data-voce="persecuzione">persecuzione</a>' in ' '.join(
        q['html'] for q in c['voci']['prova-tentazione']['paragraphs'])
    # a spaced dash before a link keeps its spaces ("condannano - Satana")
    assert 'condannano - Satana' in ' '.join(q['text'] for q in c['voci']['castighi']['paragraphs'])


def test_voci():
    c = costruito()
    s = c['summary']
    assert (s['voci'], s['full'], s['redirects']) == (849, 330, 519)
    assert (s['sections'], s['paragraphs'], s['citations'] - s['recovered']) == (3022, 4149, 30111)
    assert 100 < s['recovered'] < 300, s['recovered']
    assert not any(c['para'] == 'verita.10' for c in c['citations'] if c['source_status'] == 'recovered')
    assert s['pct_resolved'] > 99.5, s['pct_resolved']
    abba = c['voci']['abba']
    assert abba['kind'] == 'redirect' and {'voce': 'adorazione', 'form': 'adorazione', 'path': 'II 3',
                                           'sec': 'II 3'} in abba['targets']
    assert c['voci']['abele']['authors'][0]['name'] == 'PIERRE GRELOT'
    assert not c['errors'], c['errors'][:5]


def test_collegamenti():
    """Targets the source left without a voce: misprinted names, pieces of a path."""
    c = costruito()
    bers = lambda slug: [(x['voce'], x['path']) for x in c['voci'][slug]['targets']]
    assert bers('monarchia') == [('re', None)]
    assert ('espiazione', '2') in bers('propiziatorio')
    assert ('trasfigurazione', '2') in bers('elia')
    assert ('tradizione', 'NT I 1') in bers('anziani') and (None, 'I 1') not in bers('anziani')
    assert not [x for x in bers('mediatore') if x[0] is None]
    assert {x['form'] for x in c['links'] if not x['target'] and x['type'] != 'star'} == {'carcere'}
    assert c['summary']['links_tsv'] == 18215 and c['summary']['links_read_again'] == 13


def test_numerazione():
    """The evidence that the psalms follow the Hebrew numbering (and count the titles)."""
    d = {x['book']: x for x in costruito()['summary']['numbering']}
    q = d['Sal']['evidence']['quotations']
    assert q['cited'] > 20 * q.get('other', 0), q
    t = d['Sal']['evidence']['titles']['quotations']
    assert t['cited'] > 2 * t.get('other', 0), t
    assert d['Ml']['evidence']['cited_3_19_24'] > 0 and d['Ml']['evidence']['cited_4'] == 0
    assert d['Est']['evidence']['vulgate_chapters_11_16'] == 0
    for sig in ('1Re', '2Re'):
        assert d[sig]['evidence']['quotations']['cited'] > 5 and not d[sig]['evidence']['quotations'].get('other')
    s = d['Sir']['evidence']['chapters_34_36']['citations']
    assert s['converted'] > 2 * s.get('printed', 0), s
    # the table of the older division of Sirach 34-36 is the scheme "dizionario" of numerazioni.tsv,
    # shared with riferimenti.py (revisione R2-21): 26 + 24 + 27 verses, the anchors of the comment
    assert [len(D.SIRACIDE[k]) for k in (34, 35, 36)] == [26, 24, 27]
    assert D.SIRACIDE[34][18] == (21, 22) and D.SIRACIDE[35][2] == (3, 4) and D.SIRACIDE[36][24] == (26, 26)
    assert D.SIRACIDE[36][5] == (6, 7) and D.SIRACIDE[36][27] == (28, 28)


def test_indice():
    c = costruito()
    v = {x['id']: x for x in c['verses']}
    assert 'pastore-e-gregge' in v['Ps.23.1']['voci'] and 'pastore-e-gregge#12' in v['Ps.23.1']['citations']
    ordine = [c['B'].verses[x['id']]['order'] for x in c['verses']]
    assert ordine == sorted(ordine)


def test_file():
    """The written dufour.json: the same citations as the build in memory."""
    if not os.path.exists(D.OUT):
        raise AssertionError('no %s: run dufour.py first' % D.OUT)
    f = json.load(open(D.OUT, encoding='utf-8'))
    assert [x['id'] for x in f['citations']] == [x['id'] for x in costruito()['citations']]
    assert f['meta']['summary']['citations'] == len(f['citations'])


def main(a):
    verbose = '-v' in a
    failed = 0
    for cid, raw, exp in CASES:
        problems = check(cid, raw, exp)
        if problems:
            failed += 1
            print('FAIL %s %r\n     %s' % (cid, raw, '\n     '.join(problems)))
        elif verbose:
            print('ok   %s %r' % (cid, raw))
    for test in (test_testo, test_voci, test_collegamenti, test_numerazione, test_indice, test_file):
        try:
            test()
        except AssertionError as e:
            failed += 1
            print('FAIL %s: %s' % (test.__name__, e))
    print('%d citation cases + text, voci, links, numbering, index, dufour.json: %s' % (
        len(CASES), 'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
