"""Tests of paratesto.py on the rows of the front matter and the appendices.

usage: vendor/venv/bin/python -I tools/ontologia/test_paratesto.py [-v]

Needs ontologia/build/paratesto.json (paratesto.py) and bibbia.json (estrai.py). Each case
is a printed item (an index reference, a chronology entry, a woodcut, an abbreviation, a
person of the dynasties, an acrostic letter) and what the stage must have made of it; only
the keys given are compared. Plain asserts, so it also runs under pytest. Exit status 1 if a
case fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paratesto as PT  # noqa: E402

_cache = {}


def dati():
    if not _cache:
        _cache['P'] = json.load(open(PT.OUT, encoding='utf-8'))
        _cache['B'] = {v['id']: v for v in json.load(open(PT.IN, encoding='utf-8'))['verses']}
    return _cache['P'], _cache['B']


def voce(indice, lemma):
    P, _ = dati()
    ix = next(x for x in P['indici'] if x['id'] == indice)
    return next(v for v in ix['voci'] if v['lemma'] == lemma)


def rif(indice, lemma, raw, sv=None):
    v = voce(indice, lemma)
    return [it for it in v['items'] if it['raw'] == raw and (sv is None or it['sv'] == sv)][0]


# ---- the index of the most important notes: (headword, reference as printed, expected)
INDICE_NOTE = [
    # a reference to the note at its verse
    ('Abbà', 'Mc 14,36', dict(targets=['Mark.14.36'], nota='nota', notes=['note:Mark.14.36'])),
    # the book inherited along the chain: "Es 25,8.10.17; Dt 4,7; Sap 9,8"
    ('Abitazione', 'Sap 9,8', dict(targets=['Wis.9.8'], nota='nota')),
    # Esther: the reference is the Hebrew text, the BJ note is on the Greek one
    ('Purìm', 'Est 3,7', dict(targets=['Esth.3.7'], notes=['note:EsthGr.3.7'])),
    # misprints kept as printed, the corrected reference added (checklist of the volume)
    ('Caleb', 'Gb 14,6', dict(targets=['Job.14.6'], correction=dict(raw='Gs 14,6', targets=['Josh.14.6'],
                                                                     notes=['note:Josh.14.6']))),
    ('Emmanuele', 'Is 7,10', dict(targets=['Isa.7.10'], correction=dict(raw='Is 7,14', targets=['Isa.7.14']))),
    ('Legge', 'Mt 5,11', dict(targets=['Matt.5.11'], correction=dict(raw='Mt 5,17', notes=['note:Matt.5.17']))),
    # the four the graph exposed (revisione R2-04, read on PDF 3032-3039): the note is at the next verse
    ('Gàlgala (gilgāl)', 'Os 9,14', dict(targets=['Hos.9.14'], nota='rimandi',
                                         correction=dict(raw='Os 9,15', targets=['Hos.9.15'], notes=['note:Hos.9.15']))),
    ('Decima', 'Eb 7,3', dict(targets=['Heb.7.3'], correction=dict(raw='Eb 7,4', notes=['note:Heb.7.4']))),
    ('Martire', 'At 7,57', dict(targets=['Acts.7.57'], correction=dict(raw='At 7,58', notes=['note:Acts.7.58']))),
    ('Scritture', '1Ts 5,25', dict(targets=['1Thess.5.25'], correction=dict(raw='1Ts 5,27', notes=['note:1Thess.5.27']))),
]
INDICE_TEMI = [
    ('Adorazione', 'Gv 2,38', dict(status='unresolved', reason='no verse Gv 2,38 (chapter has 25)')),
    ('Cuore', 'Cr 28,9', dict(status='unresolved', correction=dict(raw='1Cr 28,9', targets=['1Chr.28.9']))),
    ('Gioia', '62,5', dict(correction=dict(raw='Is 62,5', targets=['Isa.62.5']))),
    ('Speranza', '10.23', dict(correction=dict(raw='Eb 10,23', targets=['Heb.10.23']))),
    # a bare reference in parentheses takes the book named last in them: "Os 6,6 (citato in Mt 9,13 e 12,7)"
    ('Sacrificio', '12,7', dict(book='Matt', targets=['Matt.12.7'])),
]
# «v.» cross references: (index, headword, target as printed, the entries it points to, a reason given)
VEDI = [
    ('note', 'Šekina', 'Presenza', ['Presenza di Dio'], False),        # whole words: not «Presentazione»
    ('note', 'Peccato', 'Confessione', ['Confessione dei peccati'], False),
    ('note', 'Culto', 'Festa', ['Feste d’Israele'], True),              # tsv.RIMANDI
    ('note', 'Prova', 'Tentazione', ['Tentare'], True),
    ('note', 'Urìm e Tummìm', 'Sorte', ['Sorti (tirare le)'], True),
    ('note', 'Presenza di Dio', 'Abitazione', ['Abitazione'], False),
]


def test_indici():
    bad = []
    for indice, casi in (('note', INDICE_NOTE), ('temi', INDICE_TEMI)):
        for lemma, raw, want in casi:
            ln = rif(indice, lemma, raw)['link']
            for k, w in want.items():
                got = ln.get(k)
                if isinstance(w, dict):
                    got = {kk: (got or {}).get(kk) for kk in w}
                if k == 'targets':
                    got = got[:len(w)]
                if got != w:
                    bad.append('%s %s %r: %s = %r, expected %r' % (indice, lemma, raw, k, got, w))
    # «v.» to an entry, both ways; an entry's sub-entries; page numbers to the introductions
    ab, eb = voce('note', 'Abiatàr'), voce('note', 'Ebiatàr')
    if [it['to'] for it in ab['items'] if it['kind'] == 'vedi'] != [[eb['n']]]:
        bad.append('Abiatàr: v. Ebiatàr')
    if [it['to'] for it in eb['items'] if it['kind'] == 'vedi'] != [[ab['n']]]:
        bad.append('Ebiatàr: v. Abiatàr')
    if [s['name'] for s in voce('note', 'Abitazione')['sub']][:2] != ['Abitazione di Dio',
                                                                      'Abitazione del Verbo fra gli uomini']:
        bad.append('Abitazione: sub-entries %r' % voce('note', 'Abitazione')['sub'][:2])
    for indice, lemma, raw, want, why in VEDI:
        P, _ = dati()
        ix = next(x for x in P['indici'] if x['id'] == indice)
        nomi = {v['n']: v['lemma'] for v in ix['voci']}
        its = [it for it in voce(indice, lemma)['items'] if it['kind'] == 'vedi' and it['raw'] == raw]
        got = [[nomi[n] for n in it['to']] for it in its]
        if got != [want] or [bool(it.get('why')) for it in its] != [why]:
            bad.append('%s: v. %s -> %r (why %r), expected %r' % (lemma, raw, got, [it.get('why') for it in its], want))
    # page numbers that are not pages of this edition (tsv.PAGINE_ESTRANEE): no introduction, a reason
    est = [(it['raw'], it['intros'], bool(it.get('why'))) for it in voce('note', 'Sapienza')['items']
           if it['kind'] == 'pagina']
    if est != [('1111', ['intro-sapienziali'], False), ('1032', [], True), ('1376', [], True)]:
        bad.append('Sapienza: pages %r' % est)
    pagine = [it['intros'] for it in voce('note', 'Apocalisse')['items'] if it['kind'] == 'pagina']
    if pagine != [['intro-profeti'], ['intro-apocalisse']]:
        bad.append('Apocalisse: pages %r' % pagine)
    if len(voce('temi', 'Adorazione')['sub']) != 5:
        bad.append('Adorazione: %d sub-themes' % len(voce('temi', 'Adorazione')['sub']))
    P, _ = dati()
    s = P['meta']['summary']
    nums = (s['index_note']['entries'], s['index_note']['subentries'], s['index_note']['references'],
            s['index_note']['see'], s['index_note']['pages'], s['index_temi']['entries'], s['index_temi']['references'])
    if nums != (628, 550, 1663, 247, 20, 96, 3285):
        bad.append('index counts %r' % (nums,))
    assert not bad, '\n'.join(bad)


# ---- the chronology: entry -> (date as printed, start, end, circa)
DATE = {
    133: ('680–669', -680, -669, False),          # the one span in parentheses: a reign
    161: ('sett. 605–562', -605, -562, False),    # a month before the span (R2-23: Nabucodònosor, query 22)
    13: ('2030–1720 ca.', -2030, -1720, True),
    40: ('1200–1025 ca.', -1200, -1025, True),
    229: ('400 ca.', -400, -400, True),
    392: ('12–6', -12, -6, False),                # section IX before the turn: before Christ
    413: ('Dall’1/2 al 4 d.C.', 1, 4, False),     # the turn of section IX
    421: ('6 d.C.', 6, 6, False),
    461: ('Fra il 34 e il 45', 34, 45, False),
    481: ('Primavera 50-estate 51', 50, 51, False),
    423: ('19 agosto 14', 14, 14, False),         # the day first: not the reign "(14–37)" after it
    472: ('28 giugno 45', 45, 45, False),
    50: ('970ca.–931', -970, -931, True),
    105: ('Verso il 738', -738, -738, True),
    179: ('589/8', -589, -588, False),            # a shortened second year
    183: ('Giugno-luglio 587 o 586', -587, -586, False),
    336: ('141, giugno', -141, -141, False),
    456: ('37 (o 38) ca.', 37, 38, True),
    498: ('Inverno 55–56 (o 56–57)', 55, 57, False),
    556: ('Tra 70 e 80 (?)', 70, 80, False),
}


def test_cronologia():
    P, _ = dati()
    V = {v['n']: v for v in P['cronologia']['voci']}
    bad = ['%d: %r, expected %r' % (n, (V[n]['date'], V[n]['start'], V[n]['end'], V[n]['circa']), w)
           for n, w in DATE.items() if (V[n]['date'], V[n]['start'], V[n]['end'], V[n]['circa']) != w]
    if P['cronologia']['turn'] != 122:
        bad.append('turn of section IX: row %s' % P['cronologia']['turn'])
    if any(v['start'] is not None and v['start'] > v['end'] for v in V.values()):
        bad.append('a year range out of order')
    cit = {(l['source'], l['raw']): l for l in P['links'] if l['kind'] == 'chrono-cites'}
    for (src, raw), t in {('cronologia.10', 'Gen 4,22'): 'Gen.4.22', ('cronologia.304', '1Mac 4,28s'): 'Macc'}.items():
        if src not in {s for s, _ in cit} or not any(t in x for x in cit[(src, raw)]['targets']):
            bad.append('%s %s: %r' % (src, raw, cit.get((src, raw), {}).get('targets')))
    if (len(V), len(cit)) != (585, 174):
        bad.append('chronology: %d entries, %d citations' % (len(V), len(cit)))
    # the one line printed across the table (\testolargo), under the title of VIII
    larghe = [(x['roman'], x['text']) for x in P['cronologia']['sections'] if x.get('text')]
    if larghe != [('VIII', 'I diadochi si contendono l’impero di Alessandro (319–287).')]:
        bad.append('lines across the table: %r' % larghe)
    assert not bad, '\n'.join(bad)


def test_preliminari():
    P, _ = dati()
    bad = []
    T = {t['id']: t for t in P['testi']}
    if T['presentazione']['signature'] != '✠ Gianfranco card. Ravasi' or not T['presentazione']['italic']:
        bad.append('presentazione: %r' % T['presentazione']['signature'])
    if T['prefazione-filippi']['subtitle'] != 'Nuova traduzione, nuove introduzioni, nuovo commento':
        bad.append('Filippi: subtitle')
    if T['avvertenze']['author'] is not None or T['avvertenze']['page'] != 'xxv':
        bad.append('avvertenze: author or page')
    fc = [(l['source'], l['raw'], l['targets'][:1]) for l in P['links'] if l['kind'] == 'front-cites']
    if ('presentazione.1', 'Sal 119,105', ['Ps.119.105']) not in fc:
        bad.append('presentazione: Sal 119,105 %r' % fc[:3])
    X = {x['name']: x for x in P['xilografie']}
    for name, t in (('Genesi', ['Gen.1.27']), ('Salmi', ['Ps.51.3', 'Ps.51.4']), ('Abdia', ['Obad.1.15']),
                    ('2 Giovanni', ['2John.1.5', '2John.1.6']), ('Ester', ['EsthGr.5.3'])):
        got = [v for r in X[name]['refs'] for v in r['targets']]
        if got != t:
            bad.append('woodcut %s: %r' % (name, got))
    if len(P['xilografie']) != 73:
        bad.append('%d woodcuts' % len(P['xilografie']))
    eb, gr = P['canoni']
    if len(eb['items']) != 24 or eb['items'][7]['books'] != ['1Sam', '2Sam']:
        bad.append('Hebrew canon: %r' % eb['items'][7])
    sus = next(v for v in gr['items'] if v['text'].startswith('Susanna'))
    odi = next(v for v in gr['items'] if v['text'].startswith('[Odi]'))
    if sus['chapters'] != ['Dan.13'] or not sus['deuterocanonical'] or not odi['apocryphal'] or odi['books']:
        bad.append('Greek canon: %r %r' % (sus, odi))
    A = {a['form']: a for a in P['abbreviazioni']}
    for form, books, greg in (('Est', ['Esth', 'EsthGr'], None), ('1 2 3 Gv', ['1John', '2John', '3John'], None),
                              ('S (א) (01)', [], '01'), ('066', [], '066'), ('P46', [], 'P46'), ('a', [], None),
                              ('1739', [], '1739')):
        if A[form]['books'] != books or A[form].get('gregory') != greg:
            bad.append('abbreviation %s: %r %r' % (form, A[form]['books'], A[form].get('gregory')))
    e = P['edizione']
    if e['isbn'] != '978-88-10-82031-5' or [x['month'] for x in e['printings']][::4] != ['2009-01', '2011-11']:
        bad.append('edition: %r %r' % (e['isbn'], e['printings']))
    assert not bad, '\n'.join(bad)


def test_dinastie():
    P, _ = dati()
    D = {x['id']: x for x in P['dinastie']}
    bad = []
    if D['P15']['name'] != 'Erode il Grande' or D['P15']['spouses'] != ['P16', 'P17', 'P18', 'P19'] or \
            D['P15']['date'] != '37–4 a.C.':
        bad.append('Erode il Grande: %r' % D['P15'])
    if (D['P09']['father'], D['P09']['mother']) != ('P07', 'P08'):
        bad.append('Ircano II: parents')
    if (D['P16']['father'], D['P16']['mother']) != ('P12', 'P11'):
        bad.append('Mariamne I: parents')
    assert not bad, '\n'.join(bad)


def test_acrostici():
    _, B = dati()
    want = {'Nah.1.3': [('Bet', 3)], 'Nah.1.8': [('Caf', 2)], 'Ps.111.9': [('Pe', 1), ('Sade', 2), ('Kof', 3)],
            'Lam.4.10': [('Iad', 1)], 'Ps.10.12': [('Kof', 1)], 'Prov.31.10': [('Alef', 1)],
            'Ps.10.3': [('Mem', 1)], 'Ps.25.18': [('Kof', 1)], 'Ps.25.1': [('Alef', 2)], 'Prov.31.30': [('Śin', 1)],   # 25,1: line 1 is the title
            'Ps.37.28': [('Ain', 3)], 'Ps.119.1': [('Alef', 1)]}
    bad = ['%s: %r, expected %r' % (v, list(zip(B[v].get('acrostic', []), B[v].get('acrostic_lines', []))), w)
           for v, w in want.items() if list(zip(B[v].get('acrostic', []), B[v].get('acrostic_lines', []))) != w]
    # \\acrostico{(Mem)}: the name without parentheses, the brackets as a flag (the five of Sal 10 and 25)
    tonde = sorted(v for v, x in B.items() if any(x.get('acrostic_brackets', [])))
    if tonde != ['Ps.10.10', 'Ps.10.3', 'Ps.10.4', 'Ps.10.6', 'Ps.25.18']:
        bad.append('bracketed letters at %r' % tonde)
    if any('(' in a for x in B.values() for a in x.get('acrostic', [])):
        bad.append('a letter name with parentheses')
    n = sum(len(v.get('acrostic', [])) for v in B.values())
    if n != 339:
        bad.append('%d acrostic letters' % n)
    assert not bad, '\n'.join(bad)


def test_testi():
    """The labels of the indices hold no word broken by a line-end hyphen ("secondo la testimo- nianza",
    R1 F1: a hyphen at a page break, \\pag inside the word), and verifica_rdf.testi, the check of the
    literals of the graph, finds such a word, LaTeX residue and spaces (revisione R2-06)."""
    import re
    P, _ = dati()
    rotte = [(v['lemma'], s[k]) for x in P['indici'] for v in x['voci'] for s in v.get('sub', [])
             for k in ('label', 'name', 'html') if re.search(r'[a-zà-ù]- [a-zà-ù]', s.get(k) or '')]
    assert not rotte, rotte[:5]
    temi = ' '.join(s['label'] for x in P['indici'] if x['id'] == 'temi' for v in x['voci'] for s in v['sub'])
    for w in ('testimonianza di Giovanni', 'battesimo del Battista', 'mediante la morte di Cristo',
              'salvatore della chiesa'):
        assert w in temi, w
    from rdflib import Graph, Literal, URIRef
    import verifica_rdf as V
    g = Graph()
    base = 'https://massimo-nocentini.github.io/bibbia-gerusalemme/id/'
    lab = URIRef(V.PREFISSI['skos'] + 'prefLabel')
    g.add((URIRef(base + 'indice/temi/voce/49/6'), lab, Literal('secondo la testimo- nianza di Giovanni')))
    g.add((URIRef(base + 'x/1'), lab, Literal('\\emph{x}')))
    g.add((URIRef(base + 'x/2'), lab, Literal('due  spazi')))
    g.add((URIRef(base + 'x/3'), lab, Literal('(aperta')))
    g.add((URIRef(base + 'x/4'), lab, Literal('Pietra-memoriale (giusta)')))
    g.add((URIRef(base + 'x/5'), URIRef(V.PREFISSI['dcterms'] + 'title'), Literal('b) dell’assemblea d’Israele')))
    err = V.testi(g, True)
    got = sorted((e.split(' ', 1)[0], e.split(': ')[1].split(' not')[0]) for e in err)
    assert got == [('indice/temi/voce/49/6', 'a line-end hyphen left in a word'), ('x/1', 'LaTeX residue'),
                   ('x/2', 'two spaces'), ('x/3', '()')], got


TESTS = [test_indici, test_cronologia, test_preliminari, test_dinastie, test_acrostici, test_testi]


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
    n = len(INDICE_NOTE) + len(INDICE_TEMI) + len(VEDI) + len(DATE)
    print('%d tests (%d index and date cases): %s' % (len(TESTS), n, 'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
