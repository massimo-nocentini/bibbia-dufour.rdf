"""Tests of integrazione.py on real rows: alignments, persons, datings, witnesses, calendar,
measures, maps and the interventions.

usage: vendor/venv/bin/python -I tools/ontologia/test_integrazione.py [-v]

Needs ontologia/build/integrazione.json (integrazione.py). Each case is a reviewed row or a
printed item and what the stage must have made of it. Plain asserts, so it also runs under
pytest. Exit status 1 if a case fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import integrazione as IG  # noqa: E402

_cache = {}


def dati():
    if not _cache:
        _cache['I'] = json.load(open(IG.OUT, encoding='utf-8'))
    return _cache['I']


# (from, to): relation, method — accepted pairs of the review, and two the review rejected
ALLINEAMENTI = {
    ('note.7', 'voce:abramo'): ('closeMatch', 'label'),               # same label
    ('note.19', 'voce:agnello-di-dio'): ('narrowMatch', 'head'),      # «Agnello» is broader than AGNELLO DI DIO
    ('note.146', 'voce:croce'): ('broadMatch', 'head'),               # «Croce di Gesù» under CROCE
    ('note.1', 'voce:abba'): ('relatedMatch', 'rinvio'),              # a multi-target redirect headword
    ('note.571', 'voce:feste'): ('broadMatch', 'head'),               # «rivedere», accepted by F2 with a reason
    ('temi.2', 'voce:amico'): ('relatedMatch', 'mano'),               # by hand (R2-12: Amicizia -> AMICO)
    ('temi.32', 'note.255'): ('closeMatch', 'indici-head'),           # Giorno del Signore = Giorno di YHWH
    ('note.89', 'note.41'): ('closeMatch', 'doppione'),               # Caifa / Anna e Caifa (R2-10)
}
RIFIUTATI = [('note.331', 'voce:magia'), ('note.259', 'voce:giovanni-battista'), ('note.254', 'voce:giorno-del-signore')]


def test_allineamenti():
    I = dati()
    by = {(x['da'], x['a']): x for x in I['allineamenti']}
    bad = []
    for k, (rel, met) in ALLINEAMENTI.items():
        x = by.get(k)
        if not x or (x['relazione'], x['metodo']) != (rel, met):
            bad.append((k, x and (x['relazione'], x['metodo'])))
    bad += [k for k in RIFIUTATI if k in by]
    # a head-word pair reviewed by R2 alone shares a verse (the precision rule of R2-12)
    bad += [(x['da'], x['a']) for x in I['allineamenti'] if x['metodo'] == 'head' and x['chi'] == 'R2' and not x['comuni']]
    assert not bad, bad
    assert 'Isa.53.12' in by[('temi.82', 'voce:servo-di-dio')]['comuni']


# person -> verses that must name them, verses that must not
PERSONE = {
    'P15': (['Matt.2.1', 'Matt.2.22', 'Luke.1.5'], ['Matt.14.1', 'Acts.23.35']),
    'P23': (['Luke.23.7', 'Mark.6.14', 'Acts.4.27', 'Acts.13.1'], ['Matt.2.1', 'Acts.12.1']),
    'P29': (['Acts.12.1', 'Acts.12.21'], ['Luke.23.7']),
    'P04': (['1Macc.9.31', '2Macc.8.22'], ['1Macc.13.11', '1Macc.4.30', '2Macc.1.23']),
    'P01': (['1Macc.2.1', '1Macc.14.29'], ['1Macc.16.14', '1Macc.11.70']),
    'P34': (['Acts.24.24'], ['1Macc.4.45']),
    'P26': (['Luke.3.1'], ['Matt.16.13']),
}


def test_persone():
    I = dati()
    have = {(x['persona'], x['verso']) for x in I['persone']['versetti']}
    bad = []
    for p, (si, no) in PERSONE.items():
        bad += [(p, v) for v in si if (p, v) not in have] + [('not', p, v) for v in no if (p, v) in have]
    idx = {(x['persona'], x['voce'], x.get('citazione')) for x in I['persone']['indice']}
    for k in [('P29', 'note.204.1', None), ('P31', 'note.204.2', None), ('P15', 'note.204', 'indice-note.204#c3')]:
        if k not in idx:
            bad.append(k)
    cr = {(x['persona'], x['voce']) for x in I['persone']['cronologia']}
    bad += [k for k in [('P15', 380), ('P14', 359), ('P32', 484), ('P23', 430)] if k not in cr]
    bad += [k for k in [('P14', 401)] if k in cr]         # Antipatro of entry 401 is Herod's son
    assert not bad, bad


def test_datazioni():
    I = dati()
    by = {}
    for x in I['datazioni']:
        by.setdefault(x['voce'], []).append((x['tipo'], tuple(x['libri'])))
    assert ('ministero', ('Amos', 'Hos')) in by[96], by.get(96)
    assert ('composizione', ('Job', 'Prov', 'Song', 'Ruth', 'Ps')) in by[219], by.get(219)
    assert ('ministero', ('Mal',)) in by[219]
    assert ('composizione', ('1Pet', 'Mark')) in by[517]
    assert ('citato', ('Jer',)) in by[163], by.get(163)             # 605: Ger 46,2; 25,1.11


def test_testimoni():
    I = dati()
    T = I['testimoni']
    nv = dict(map(tuple, ((n, tuple(v)) for n, v in T['note_versioni'])))
    nc = dict(map(tuple, ((n, tuple(c)) for n, c in T['note_codici'])))
    # «con B, C, D, P75, Tertulliano»: D in Luke is Dᵉ (05)
    assert set(nc['note:Luke.8.26']) >= {'03', '04', '05', 'P75'}, nc.get('note:Luke.8.26')
    # «B e D hanno: «partire»» in Galatians: D is Dᵖ (06)
    assert set(nc['note:Gal.1.17']) == {'03', '06'}, nc.get('note:Gal.1.17')
    # «Il regno di A» is no list of witnesses (R2-16's one error)
    assert 'note:Judg.9.1' not in nc
    assert 'lxx' in nv['note:Acts.2.33'] and 'vetuslatina' in nv['note:John.5.3'], (nv.get('note:Acts.2.33'),)
    q = {v['id']: v['qualificatori'] for v in T['versioni']}
    assert q['lxx'] == ['LXX', 'gr.'] and q['volgata'] == ['volg.'], q


def test_tavole():
    I = dati()
    m = {x['id']: x for x in I['misure']}
    assert (m['cubito']['decimale'], m['cubito']['unita']) == (45.0, 'unit:CentiM')
    assert abs(m['dito']['rapporto_decimale'] - 1 / 24) < 1e-9 and m['dito']['base'] == 'cubito'
    assert (m['talento']['decimale'], m['talento']['unita']) == (34.272, 'unit:KiloGM')
    L = {l['id']: l for l in I['links']}
    # «cf. Zac 11,12» and «Esd 6,69» (misprints of the prose: paratesto.CORREZIONI_PROSA) read as corrected
    t = [L[x] for x in m['tetradramma-tiro']['links']]
    assert [x['targets'] for x in t if x['raw'].endswith('Zac 11,12')] == [['Zech.11.12']], [x['raw'] for x in t]
    d = [L[x] for x in m['dramme-oro']['links']]
    assert [x['targets'] for x in d if x['raw'] == 'Esd 6,69'] == [['Ezra.2.69']]
    f = {x['id']: x for x in I['feste']}
    assert f['encenie']['mese'] == 'IX' and 'note.156' in f['encenie']['anche']
    assert 'John.10.22' in [t for k in f['encenie']['links'] for t in L[k]['targets']]
    assert 'Esth.3.7' in I['mesi_versetti']['XII'] or any(v.startswith('Esth') for v in I['mesi_versetti']['XII'])
    c = {x['id']: x for x in I['carte']}
    assert c['tribu']['pdf'] == 3062 and L[c['tribu']['links'][0]]['ranges'][0][0] == 'Josh.13.1'


def test_interventi():
    I = dati()
    by = {}
    for x in I['interventi']:
        by.setdefault(x['tabella'], []).append(x)
    # every row of the tables that have rows
    import riferimenti as R
    import paratesto as PT
    import dufour as DU
    for tab, n in [('riferimenti.CORREZIONI', len(R.CORREZIONI)), ('riferimenti.AGGIUNTE', len(R.AGGIUNTE)),
                   ('numerazioni.tsv', len(R.numerazioni())), ('paratesto.CORREZIONI_INDICI', len(PT.CORREZIONI_INDICI)),
                   ('paratesto.CORREZIONI_PROSA', len(PT.CORREZIONI_PROSA)), ('dufour.CORREZIONI', len(DU.CORREZIONI)),
                   ('dufour.PARAGRAFI', len(DU.PARAGRAFI)), ('dufour.FORME', len(DU.FORME)),
                   ('riferimenti.REFUSI_RIFERIMENTI', len(R.REFUSI_RIFERIMENTI)), ('tsv.RIMANDI', 3),
                   ('tsv.PAGINE_ESTRANEE', 2)]:
        assert len({x['riga'] for x in by.get(tab, [])}) == n, (tab, len(by.get(tab, [])), n)
    caleb = next(x for x in by['paratesto.CORREZIONI_INDICI'] if x['stampato'] == 'Gb 14,6')
    assert (caleb['corretto'], caleb['motivazione'], caleb['pagina']) == ('Gs 14,6', 'editing', ['pagapp', 30]), caleb
    mt = next(x for x in by['numerazioni.tsv'] if x['stampato'] == 'Sal 103,12 (LXX)')
    assert mt['corretto'] == 'Sal 104,12' or mt['bersagli'][0][1].startswith('mref:Matt.13.32'), mt
    zac = by['riferimenti.MISPRINT']
    assert sorted(x['stampato'] for x in zac) == ['2Mc 7,9+', 'Zac 4,10', 'Zac 5,7'], [x['stampato'] for x in zac]
    assert len({x['id'] for x in I['interventi']}) == len(I['interventi'])


TESTS = [test_allineamenti, test_persone, test_datazioni, test_testimoni, test_tavole, test_interventi]


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
    n = len(ALLINEAMENTI) + len(RIFIUTATI) + len(PERSONE)
    print('%d tests (%d alignment and person cases): %s' % (len(TESTS), n, 'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
