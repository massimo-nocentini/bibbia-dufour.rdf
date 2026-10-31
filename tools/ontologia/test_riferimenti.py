"""Tests of riferimenti.py on strings taken from the corpus (margins, notes, introductions).

usage: vendor/venv/bin/python -I tools/ontologia/test_riferimenti.py [-v]

Needs ontologia/build/bibbia.json (estrai.py) and, for test_collegamenti_file,
collegamenti.json (riferimenti.py). Each case gives the string, where it is printed
(the verse of a margin, or the note / context of a citation) and what each of its
references must resolve to; only the keys given are compared. Margin cases use
printed(), which takes the real \\mref beside that verse, so they cannot test a string
the corpus does not print; the few strings that are not printed are under "probes"
and use margin(). The cases marked F1-F12 are the regressions of the stage 5 audit;
CONTEXT checks the links read in the sense of the sentence (one or more per rule, a sample of
the table CORREZIONI) in the written collegamenti.json.
Plain asserts, so it also runs under pytest. Exit status 1 if a case fails.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402

_cache = {}


def bibbia():
    if not _cache:
        data = json.load(open(R.IN, encoding='utf-8'))
        B = R.Bibbia(data)
        _cache.update(data=data, B=B, notes={n['id']: n for n in data['notes']},
                      margins={x['id']: x for x in R.margin_links(data, B)})
    return _cache


def margin(raw, anchor):
    """The references of a margin string beside verse anchor (parse + resolve)."""
    B = bibbia()['B']
    ctx = R.margin_context(B.verses[anchor])
    return [R.resolve(r, B, ctx) for r in R.parse(raw, ctx)[0]]


def printed_margin(mref_id):
    """The links of a real \\mref, numbering runs included (as margin_links builds them)."""
    ms = bibbia()['margins']
    return [ms['%s#%d' % (mref_id, k)] for k in range(1, 50) if '%s#%d' % (mref_id, k) in ms]


def cites(text, book=None, chapter=None, note=None):
    """The references a note text (or a snippet in the context of note / book, chapter) cites."""
    c = bibbia()
    ctx = R.note_context(c['notes'][note], c['B']) if note else dict(book=book, chapter=chapter, margin=False)
    text = c['notes'][note]['text'] if text is None else text
    return [R.resolve(r, c['B'], ctx) for r in R.scan_prose(text, ctx)]


def one(first, last=None, **kw):
    """Expected: one resolved span first–last."""
    return dict(status='resolved', ranges=[[first, last or first]], **kw)


ROM_5_12 = 'all’«ultimo Adamo» (vv 15–19; 1Cor 15,21s.25). Come «nuovo Adamo'

def printed(raw, anchor):
    """The links of the real \\mref printed as raw beside verse anchor (the whole pipeline:
    numbering runs, doublets tied to the previous reference); none if no such margin,
    so a case cannot test a string that is not in the corpus."""
    ms = [m for m in bibbia()['data']['mrefs'] if m['anchor'] == anchor and m['raw'] == raw]
    return printed_margin(ms[0]['id']) if ms else [dict(raw='(no margin %r beside %s)' % (raw, anchor))]


def margins_at(anchor):
    """The margin entries anchored to a verse (stage 1), in print order."""
    return [m for m in bibbia()['data']['mrefs'] if m['anchor'] == anchor]


# (function, arguments, [expected per reference])
CASES = [
    # ---- margins: books, chapters, inheritance
    (printed, ('Gb 38–39; Sal 8; 104; Pr 8,22–31; /Gv 1,1–3; Col 1,15–17; Eb 1,2–3', 'Gen.1.1'),
     [one('Job.38.1', 'Job.39.30'), one('Ps.8.1', 'Ps.8.10'), one('Ps.104.1', 'Ps.104.35'),
      one('Prov.8.22', 'Prov.8.31'), one('John.1.1', 'John.1.3', sign='/', relation='quoted-later'),
      one('Col.1.15', 'Col.1.17'), one('Heb.1.2', 'Heb.1.3')]),
    (printed, ('Dt 7,9.12', 'Neh.1.5'),
     [dict(status='resolved', ranges=[['Deut.7.9', 'Deut.7.9'], ['Deut.7.12', 'Deut.7.12']],
           targets=['Deut.7.9', 'Deut.7.12'])]),
    (printed, ('‖2Cr 2,10–11', '1Kgs.5.21'), [one('2Chr.2.10', '2Chr.2.11', sign='‖', relation='parallel')]),
    (printed, ('1Re 1,47; /Eb 11,21', 'Gen.47.31'), [one('1Kgs.1.47', sign=None), one('Heb.11.21', sign='/')]),
    (printed, ('Is 2,11–17; 49,3; 66,5; Sal 89,8 (LXX); 68,35 (LXX)', '2Thess.1.10'),
     [one('Isa.2.11', 'Isa.2.17'), one('Isa.49.3'), one('Isa.66.5'), one('Ps.89.8', qualifier='LXX'),
      one('Ps.68.35', qualifier='LXX')]),
    (printed, ('Rm 1,1+', '1Cor.1.1'),          # the key note: the narrowest one starting at 1,1
     [one('Rom.1.1', keynote=True, keynote_notes=['note:Rom.1.1_2', 'note:Rom.1.1'], keynote_verses=['Rom.1.1'])]),
    (printed, ('20,29; Mt 12,38sp', 'John.4.47'), [one('John.20.29'), one('Matt.12.38', 'Matt.12.39', flags=['p', 's'])]),
    (printed, ('11,44s+; 17,1+', 'Lev.20.7'),
     [one('Lev.11.44', 'Lev.11.45', flags=['s'], keynote=True), one('Lev.17.1', keynote=True)]),
    (printed, ('15,1+.19s.28s', 'Acts.21.25'),
     [dict(status='resolved', ranges=[['Acts.15.1', 'Acts.15.1'], ['Acts.15.19', 'Acts.15.20'],
                                      ['Acts.15.28', 'Acts.15.29']], keynote=True, keynote_verses=['Acts.15.1'])]),
    (printed, ('/Ap 22,1s.14', 'Gen.3.24'),
     [dict(status='resolved', sign='/', ranges=[['Rev.22.1', 'Rev.22.2'], ['Rev.22.14', 'Rev.22.14']])]),
    (printed, ('Ag 1,14–2,9', 'Ezra.5.1'), [one('Hag.1.14', 'Hag.2.9')]),
    (printed, ('Gdc 13–16; 3,12–30', '1Sam.12.9'), [one('Judg.13.1', 'Judg.16.31'), one('Judg.3.12', 'Judg.3.30')]),
    (printed, ('Sal 18,5; 69,2–3.15–16; Ger 38,6', 'Ps.40.3'),
     [one('Ps.18.5'), dict(status='resolved', ranges=[['Ps.69.2', 'Ps.69.3'], ['Ps.69.15', 'Ps.69.16']]),
      one('Jer.38.6')]),
    (printed, ('Gen 9,6 Tg; Es 20,13; Dt 5,17', 'Matt.5.21'),
     [one('Gen.9.6', qualifier='Tg'), one('Exod.20.13'), one('Deut.5.17')]),
    (printed, ('Dt 34,9 Gs 22,2', 'Matt.28.20'), [one('Deut.34.9'), one('Josh.22.2')]),     # no ";"
    (printed, ('=Es 34,6+; Sal 103,8; 145,8', 'Ps.86.15'),     # "=" with another book: kept as printed
     [one('Exod.34.6', sign='=', relation='doublet', keynote=True), one('Ps.103.8'), one('Ps.145.8')]),
    (printed, ('/Mt 19,4p', 'Gen.1.27'), [one('Matt.19.4', sign='/', flags=['p'])]),
    # ---- margins: one-chapter books, bare numbers
    (printed, ('Is 5,24; Abd 18; Na 1,10', 'Exod.15.7'), [one('Isa.5.24'), one('Obad.1.18'), one('Nah.1.10')]),
    (printed, ('Lv 10,1–3; Sal 106,16–18; Sir 45,18–20; Gd 11', 'Num.16.1'),
     [one('Lev.10.1', 'Lev.10.3'), one('Ps.106.16', 'Ps.106.18'), one('Sir.45.18', 'Sir.45.20'), one('Jude.1.11')]),
    (printed, ('Gal 4,19; 1Ts 2,11; Fm 10', '1Cor.4.15'), [one('Gal.4.19'), one('1Thess.2.11'), one('Phlm.1.10')]),
    (printed, ('3Gv 1', '2John.1.1'), [one('3John.1.1')]),
    (printed, ('23', 'Gen.25.9'), [dict(relation='related', ranges=[['Gen.23.1', 'Gen.23.20']])]),  # a chapter
    (printed, ('13; 15', 'Lev.22.4'), [one('Lev.13.1', 'Lev.13.59'), one('Lev.15.1', 'Lev.15.33')]),
    (printed, ('23', 'Dan.6.24'), [dict(relation='numbering', status='numbering', alt='23')]),
    (printed, ('4 5 6', 'Neh.10.6'), [dict(status='numbering', alt='4 5 6')]),
    # ---- margins: other numberings, Esther, odd entries
    (printed, ('32,1 (volg.)', 'Gen.32.2'), [dict(status='numbering', qualifier='volg.', alt='32,1')]),
    (printed, ('18 (TM var.)', 'Deut.5.21'), [dict(status='numbering', qualifier='TM var.')]),
    (printed, ('LXX: 34', 'Jer.27.1'), [dict(status='numbering', qualifier='LXX', alt='34')]),
    (printed, ('30,25 (LXX); Is 24,13; Ger 49,9', 'Sir.33.16'),
     [dict(status='numbering', qualifier='LXX'), one('Isa.24.13'), one('Jer.49.9')]),
    (printed, ('11,2', 'EsthGr.1.1a'), [dict(status='numbering', qualifier='volg.', alt='11,2')]),
    (printed, ('(volg.) 21 12,1', '2Kgs.12.1'), [dict(status='numbering', qualifier='volg.')]),
    (printed, ('(aramaico)', 'Dan.2.3'), [dict(relation='comment', status='comment')]),
    (printed, ('Bar 6 (volg.)', '2Macc.2.1'), [one('Bar.6.1', 'Bar.6.72', qualifier='volg.')]),
    (printed, ('Gs (passim)', '1Macc.2.54'), [dict(status='resolved', target_book='Josh', targets=[])]),
    (printed, ('3,96(29)', 'Dan.6.27'), [one('Dan.3.96', alt='29')]),
    (printed, ('4,17u–y', 'EsthGr.2.17'), [one('EsthGr.4.17u', 'EsthGr.4.17y')]),
    (printed, ('1,1a–c', 'Esth.2.5'), [one('EsthGr.1.1a', 'EsthGr.1.1c', book='EsthGr')]),
    (printed, ('4,17de', 'EsthGr.3.2'), [one('EsthGr.4.17d', 'EsthGr.4.17e')]),
    (printed, ('Est 4,17(b)', 'Jdt.16.14'), [one('EsthGr.4.17b')]),
    # ---- margins: misprints stay unresolved
    (printed, ('Fil 1,21–32', '2Cor.5.8'), [dict(status='unresolved', reason='no verse Fil 1,32 (chapter has 30)')]),
    (printed, ('Sal 23,31 (LXX)', 'Eph.5.17'), [dict(status='unresolved', qualifier='LXX')]),
    (printed, ('+2Re 10,15', '1Chr.2.55'), [dict(status='unresolved', reason='not understood')]),
    # ---- regressions of the audit (F1-F12)
    # F1: a margin printed after the last words of a verse belongs to the verse that begins on its line
    (margins_at, ('Gen.2.2',), [dict(raw='Es 20,8+; /Es 20,11; 31,12s; /Eb 4,4', offset=0, printed_in_verse='Gen.2.1')]),
    (margins_at, ('Luke.6.32',), [dict(raw='‖Mt 5,46', printed_in_verse='Luke.6.31'), dict(raw='14,12–14')]),
    (margins_at, ('Matt.19.4',), [dict(raw='Gen 1,27', printed_in_verse='Matt.19.3'), dict(raw='Gen 2,24; Ef 5,31')]),
    (margins_at, ('Acts.7.20',), [dict(raw='Es 2,2; Eb 11,23s'), dict(raw='Es 2,5.10')]),
    (margins_at, ('Gen.4.3',), []),             # "Es 34,19; Lv 3,16" (the firstlings) is 4,4's
    (margins_at, ('Jer.24.1',), [dict(raw='29,1–20; Ez 11,14–21; Mt 21,18–19p'), dict(raw='2Re 24,12–16')]),
    # F2: two letters after an Esther verse name the Greek additions
    (printed, ('Est 4,17rs; Gdt 10,4; 11,20.23; 16,6.9', 'Jdt.9.12'),
     [one('EsthGr.4.17r', 'EsthGr.4.17s', book='EsthGr'), one('Jdt.10.4'),
      dict(status='resolved', ranges=[['Jdt.11.20', 'Jdt.11.20'], ['Jdt.11.23', 'Jdt.11.23']]),
      dict(status='resolved', ranges=[['Jdt.16.6', 'Jdt.16.6'], ['Jdt.16.9', 'Jdt.16.9']])]),
    (printed, ('Est 3,8.13de', 'Wis.2.15'),
     [dict(status='resolved', book='EsthGr', ranges=[['EsthGr.3.8', 'EsthGr.3.8'], ['EsthGr.3.13d', 'EsthGr.3.13e']])]),
    (printed, ('4,17de', 'Esth.3.2'), [one('EsthGr.4.17d', 'EsthGr.4.17e', book='EsthGr')]),
    (printed, ('3,13de; Dn 3,8–12; Sap 2,14–15', 'Esth.3.8'),
     [one('EsthGr.3.13d', 'EsthGr.3.13e', book='EsthGr'), one('Dan.3.8', 'Dan.3.12'), one('Wis.2.14', 'Wis.2.15')]),
    # F3: "=" is a doublet in the same book, or of the reference it is tied to
    (printed, ('Is 25,8; =21,4', 'Rev.7.17'), [one('Isa.25.8'), one('Rev.21.4', relation='doublet', book='Rev')]),
    (printed, ('‖Lc 8,16; =11,33; ‖Mt 5,15', 'Mark.4.21'),
     [one('Luke.8.16', relation='parallel'), one('Luke.11.33', relation='parallel', sign='=',
                                                  doublet_of='mref:Mark.4.21_1#1'), one('Matt.5.15')]),
    (printed, ('‖2Cr 1,14=9,25; 1Re 5,6; 9,19', '1Kgs.10.26'),
     [one('2Chr.1.14', sign='‖', relation='parallel'),
      one('2Chr.9.25', sign='=', relation='parallel', doublet_of='mref:1Kgs.10.26_2#1'), one('1Kgs.5.6'),
      one('1Kgs.9.19')]),
    (printed, ('2Re 19,3=Is 37,3', 'Sir.48.19'),
     [one('2Kgs.19.3'), one('Isa.37.3', sign='=', relation='related', doublet_of='mref:Sir.48.19_1#1')]),
    (printed, ('=3,5; =8,4', 'Song.2.7'), [one('Song.3.5', relation='doublet'), one('Song.8.4', relation='doublet')]),
    # F4: a range from a chapter to a verse starts at the head of the chapter
    (printed, ('8,12; Sal 9–10,32+', 'Ezek.9.9'),
     [one('Ezek.8.12'), dict(status='unresolved', reason='no verse Sal 10,32 (chapter has 18)')]),
    (cites, ('come in 2Re 18–25,31', 'Ezra', 1), [dict(status='unresolved', reason='no verse 2Re 25,31 (chapter has 30)')]),
    # F5: "9.11" beside Gdt 14,12 is a Vulgate numbering, and "." never joins chapters
    (printed, ('9.11', 'Jdt.14.12'), [dict(status='numbering', relation='numbering', alt='9.11')]),
    # F6: a chapter heading "LXX: 36" does not make a lone bare number a numbering
    (printed, ('24', 'Jer.29.17'), [one('Jer.24.1', 'Jer.24.10', relation='related')]),
    # F7: the key note is at the verse carrying "+", not at every verse of the reference
    (printed, ('17,8.23+', 'Prov.21.14'),
     [dict(status='resolved', keynote=True, keynote_verses=['Prov.17.23'],
           ranges=[['Prov.17.8', 'Prov.17.8'], ['Prov.17.23', 'Prov.17.23']])]),
    # F8: a misprinted item stays one unresolved reference
    (printed, ('‖Mc 15,2–15; ‖Lc 23,2–5,13–25; ‖Gv 18,28–19,1; 19,4–16', 'Matt.27.11'),
     [one('Mark.15.2', 'Mark.15.15', sign='‖'), dict(status='unresolved', sign='‖', raw='‖Lc 23,2–5,13–25'),
      one('John.18.28', 'John.19.1', sign='‖'), one('John.19.4', 'John.19.16', sign=None)]),
    # F10: lettered verses in letter order
    (printed, ('Sal 83,15; Is 9,17; 10,17–19; Ger 21,14; Ez 17,24; Lc 23,31', 'Ezek.21.3'),
     [one('Ps.83.15'), one('Isa.9.17'),
      dict(targets=['Isa.10.17', 'Isa.10.18a', 'Isa.10.18b', 'Isa.10.19']), one('Jer.21.14'), one('Ezek.17.24'),
      one('Luke.23.31')]),
    # ---- probes: strings not printed in the margins, for the grammar alone
    (margin, ('Gen 1–2,4a', 'John.1.1'), [one('Gen.1.1', 'Gen.2.4')]),
    (margin, ('Gen 1–2,99', 'John.1.1'), [dict(status='unresolved', reason='no verse Gen 2,99 (chapter has 25)')]),
    (margin, ('Mt 5,3p', 'Luke.6.20'), [one('Matt.5.3', flags=['p'])]),
    (margin, ('5', 'Jude.1.6'), [one('Jude.1.5')]),                 # bare number, one-chapter book: a verse
    (margin, ('8.10', 'Gen.1.1'), [dict(status='resolved', ranges=[['Gen.1.8', 'Gen.1.8'], ['Gen.1.10', 'Gen.1.10']])]),
    # ---- notes: siglum-less references, v/vv, c/cc
    (cites, (None, None, None, 'note:Gen.1.7'),
     [one('Gen.1.16', raw='v 16'), one('Gen.1.25'), one('Gen.1.26'), one('Gen.2.4', 'Gen.2.25', raw='2,4b–25')]),
    (cites, (ROM_5_12, 'Rom', 5),
     [one('Rom.5.15', 'Rom.5.19'), dict(status='resolved', flags=['s'],
                                         ranges=[['1Cor.15.21', '1Cor.15.22'], ['1Cor.15.25', '1Cor.15.25']])]),
    (cites, ('il parallelismo con 1,1–2,4a è solo parziale', 'Gen', 2), [one('Gen.1.1', 'Gen.2.4')]),
    (cites, ('che chiamiamo Pentateuco (cf. Sir prol.; 24,23). Il', '2Chr', 23),
     [one('Sir.Prol.1', 'Sir.Prol.35', cf=True), one('Sir.24.23')]),
    (cites, ('proviene dal giudaismo (cf. Sir prol. v 5).', '1Cor', 5), [one('Sir.Prol.5')]),
    (cites, ('ma già efficaci (cf. Ger 18,1+). I dieci', '1Kgs', 11), [one('Jer.18.1', keynote=True, cf=True)]),
    (cites, ('Ma cf. Est 9,27ss; 1Mac 7,48–49.', 'Jdt', 16),
     [dict(status='resolved', book='Esth', flags=['ss']), one('1Macc.7.48', '1Macc.7.49')]),
    (cites, ('(specialmente 1,19ss) e dove', 'Deut', 1), [dict(status='resolved', flags=['ss'], book='Deut')]),
    (cites, ('cf. Is 9,5; 22,21; Est 3,13f (', 'Gen', 45), [one('Isa.9.5'), one('Isa.22.21'), one('EsthGr.3.13f')]),
    (cites, ('cf. Is 9,5, Mi 5,4', 'Matt', 2), [one('Isa.9.5'), one('Mic.5.4')]),
    (cites, ('Essa evoca già Mt 26,67; 27,30p.', 'Isa', 50), [one('Matt.26.67'), one('Matt.27.30', flags=['p'])]),
    (cites, ('come in Mt 5,3p e cf. 3,1ss.', 'Matt', 5), [one('Matt.5.3', flags=['p']),
                                                        dict(status='resolved', flags=['ss'], book='Matt')]),
    (cites, ('narrata in 1 Cor 15,3 e', 'Rom', 1), [one('1Cor.15.3')]),
    (cites, ('Storia di Sòdoma e di Gomorra (cc 18–19). Essa', 'Gen', 13), [one('Gen.18.1', 'Gen.19.38')]),
    (cites, ('Ger 1,11–12 (cf. 31,28; 44,27) il simbolo', 'Dan', 9),
     [one('Jer.1.11', 'Jer.1.12'), one('Jer.31.28'), one('Jer.44.27')]),
    (cites, ('come il suo Dio è santo (Lv 19,2, cf. 11,44s; 20,7.26) e', 'Exod', 19),
     [one('Lev.19.2'), one('Lev.11.44', 'Lev.11.45'),
      dict(status='resolved', ranges=[['Lev.20.7', 'Lev.20.7'], ['Lev.20.26', 'Lev.20.26']])]),
    (cites, ('vidi un cielo nuovo: in Isaia (65,17; 66,22), l’espressione', 'Rev', 21),
     [one('Isa.65.17'), one('Isa.66.22')]),
    (cites, ('come formula di adozione, come in Sal 2,7; 110,3 (LXX), ma è', '2Sam', 7),
     [one('Ps.2.7'), one('Ps.110.3', qualifier='LXX')]),
    (cites, ('fratello di Giacomo (Gd 1). Così', 'Acts', 1), [one('Jude.1.1')]),
    (cites, ('appellativo (Nm 20,14; Am 1,11; Abd 10.12), anche', 'Deut', 23),
     [one('Num.20.14'), one('Amos.1.11'),
      dict(status='resolved', ranges=[['Obad.1.10', 'Obad.1.10'], ['Obad.1.12', 'Obad.1.12']])]),
    (cites, ('Della grande narrazione di 2Sam 9–1Re 2 sul regno', '1Chr', 18), [one('2Sam.9.1', '1Kgs.2.46')]),
    (cites, ('ammessa in 2Mac 7,9–14.23–36; 12,43–46 (cf.', 'Ezek', 37),
     [dict(status='resolved'), dict(status='unresolved', reason='no verse 2Mac 12,46 (chapter has 45)')]),
    # ---- notes: what is not a reference
    (cites, ('(6 d.C.; cf. Lc 2,2+) e al mandato (44–46).', 'Acts', 5), [one('Luke.2.2', keynote=True)]),
    (cites, ('una spanna: circa 22,5 cm.', 'Exod', 28), []),
    (cites, ('un decimo di efa: cioè 4,50 litri circa.', 'Exod', 29), []),
    (cites, ('La ricchezza: hôn, 1QpAb; il TM ha: yayin; P46 legge', 'Hab', 2), []),
    (cites, ('al suo cospetto: la neovolg. (2,21) aggiunge', 'Sir', 2), []),
    (cites, ('Un’aggiunta della volg. (vv 12–18) paragona', 'Tob', 2), []),
    (cites, ('in un discorso (cf. v 3) e il v 5', None, None), []),       # introduction: no current book
    # ---- notes: other books and misprints
    (cites, ('(cf. Enoc 61,8; 62,25; 69,27)', 'Matt', 25),
     [dict(status='unresolved', reason='extra-canonical book Enoc')] * 3),
    (cites, ('con 3 Esdra 5,45 e la LXX', 'Ezra', 2),
     [dict(status='unresolved', reason='extra-canonical book 3 Esdra')]),
    (cites, ('lo stagno è bᵉdîl in Zac 4,10 e', 'Amos', 7),
     [dict(status='unresolved', reason='unknown siglum Zac (Zc?)')]),
    (cites, ('assegnato ai peccatori (Col 5,2). Le sue', '2Cor', 8),
     [dict(status='unresolved', reason='no chapter Col 5 (Col has 4)')]),
    (cites, ('l’originale ebraico del Sal 151 greco', 'Ps', None), [dict(status='unresolved')]),
    # ---- F12: a reference without siglum that does not exist in the book it inherits
    (cites, (None, None, None, 'note:Phil.3.2'), None),      # filled below: "Mt 15,26 e forse 7,6"
    (cites, (None, None, None, 'note:Matt.26.64'), None),    # "Sal 110 (cf. 22,41s)" = Mt 22,41s
    (cites, (None, None, None, 'note:Song.2.10'), None),     # "In 12,1" after "Gen 12,1" = Gen 12,1
    (cites, (None, None, None, 'note:Isa.4.3'), None),       # "37,4 = 2Re 19,4; 37,31–32" = Is 37,31
    (cites, (None, None, None, 'note:Matt.28.1'), None),     # "Mt 27,56; 61" = Mt 27,61
    (cites, (None, None, None, 'note:Hos.1.2'), None),       # "Ezechiele ... (cc 16 e 23)" = Ez 16; 23
    (cites, (None, None, None, 'note:2Pet.1.4'), None),      # "10,34 (= Sal 82,6); 14,20" = Gv 14,20
    (cites, (None, None, None, 'note:Matt.22.32'), None),    # "2Mac 7,9s; 12,43–46": stays unresolved
    (cites, ('lo stesso (cf. Enoc 61,8; 2,3)', 'Matt', 25),
     [dict(status='unresolved', reason='extra-canonical book Enoc')] * 2),   # no fallback after a non-canonical book
]

# F12: the expected readings of whole notes, by the raw text of the citation
F12 = {
    'note:Phil.3.2': {'7,6': one('Matt.7.6')},
    'note:Matt.26.64': {'cf. 22,41s': one('Matt.22.41', 'Matt.22.42', inferred='book Mt from the text')},
    'note:Song.2.10': {'12,1': one('Gen.12.1', inferred='book Gen from the text')},
    'note:Isa.4.3': {'37,31–32': one('Isa.37.31', 'Isa.37.32')},
    'note:Matt.28.1': {'61': one('Matt.27.61', inferred='verses of chapter 27')},
    'note:Hos.1.2': {'cc 16': one('Ezek.16.1', 'Ezek.16.63', inferred='book Ez from the text')},
    'note:2Pet.1.4': {'14,20': one('John.14.20'), '15,4–5': one('John.15.4', 'John.15.5')},
    'note:Matt.22.32': {'12,43–46': dict(status='unresolved', book='2Macc')},
}


def check(fn, args, expected):
    got = fn(*args)
    problems = []
    if expected is None:                        # F12: only the citations named in the table
        want = F12[args[3]]
        by_raw = {g['raw']: g for g in got}
        for raw, e in want.items():
            g = by_raw.get(raw)
            if g is None:
                problems.append('no citation %r in %s' % (raw, [x['raw'] for x in got]))
                continue
            problems += ['%s %s: %r, expected %r' % (raw, k, g.get(k), v) for k, v in e.items() if g.get(k) != v]
        return problems
    if len(got) != len(expected):
        problems.append('%d references, expected %d: %s' % (len(got), len(expected), [g['raw'] for g in got]))
    for k, (g, e) in enumerate(zip(got, expected), 1):
        for key, want in e.items():
            if g.get(key) != want:
                problems.append('#%d %s: %r, expected %r' % (k, key, g.get(key), want))
    return problems


def test_cases():
    for fn, args, expected in CASES:
        problems = check(fn, args, expected)
        assert not problems, '%s%r: %s' % (fn.__name__, args, problems)


def test_parse_structure():
    """parse() alone: spans, inheritance, signs (no resolution)."""
    refs, _ = R.parse('Sal 8; 104', dict(book='Gen', chapter=1))
    assert [r['siglum'] for r in refs] == ['Sal', 'Sal']
    assert [(s['c1'], s['v1'], s['c2']) for r in refs for s in r['spans']] == [(8, None, 8), (104, None, 104)]
    refs, _ = R.parse('Gen 1,1–2,4a', dict(book='John', chapter=1))
    assert refs[0]['spans'] == [dict(c1=1, v1=1, t1='', c2=2, v2=4, t2='a', plus=False)]
    refs, _ = R.parse('1Re 1,47; /Eb 11,21', dict(book='Gen', chapter=47))
    assert [r['sign'] for r in refs] == [None, '/'] and refs[1]['siglum'] == 'Eb'
    refs, _ = R.parse('5', dict(book='Gen', chapter=1))
    assert refs[0]['current'] and refs[0]['spans'][0]['v1'] is None       # a chapter
    refs, _ = R.parse('5', dict(book='Jude', chapter=1))
    assert refs[0]['spans'][0]['v1'] == 5                                 # a verse
    refs, _ = R.parse('Sal 9–10,32+', dict(book='Ezek', chapter=9))                  # F4
    assert refs[0]['spans'] == [dict(c1=9, v1=1, t1='', c2=10, v2=32, t2='', plus=True, from_start=True)]
    refs, _ = R.parse('9.11', dict(book='Jdt', chapter=14, margin=True))            # F5
    assert [(s['c1'], s['v1']) for s in refs[0]['spans']] == [(14, 9), (14, 11)]
    refs, _ = R.parse('‖Lc 23,2–5,13–25; ‖Gv 18,28', dict(book='Matt', chapter=27))  # F8
    assert [r['raw'] for r in refs] == ['‖Lc 23,2–5,13–25', '‖Gv 18,28'] and refs[0]['problem']
    refs, _ = R.parse('vv 3–5; 8', dict(book='Gen', chapter=2), prose=True)
    assert [(s['c1'], s['v1'], s['v2']) for r in refs for s in r['spans']] == [(2, 3, 5), (2, 8, 8)]


def test_collegamenti_file():
    """The written collegamenti.json: every link has a string raw (F11), and the targets of
    each link follow the canonical numeric order (F10)."""
    c = bibbia()
    links = json.load(open(R.OUT, encoding='utf-8'))['links']
    assert all(isinstance(x['raw'], str) for x in links), [x['id'] for x in links if not isinstance(x['raw'], str)]
    rank = c['B'].rank
    bad = [x['id'] for x in links if any(c['B'].verses[a]['book'] == c['B'].verses[b]['book'] and rank[a] > rank[b]
                                         for a, b in zip(x['targets'], x['targets'][1:]))
           and x['kind'] == 'mref' and len(x['ranges']) == 1]
    assert not bad, bad[:5]
    label = next(x for x in links if x['id'] == 'note:Sir.Prol.1#label')
    assert label['raw'] == '' and label['status'] == 'resolved'


# ---- the sense of the sentence (riferimenti.context_links, run after all the links are made;
# the cases of the Tufte content audit, tools/tufte/test_genera.py CONTESTO): (source, reference as
# printed, n-th so printed or 0 for the first, the first verse it must link to, the rule that read it
# (None: left as the grammar reads it), the status)
CONTEXT = [
    # catena: the chain goes on in the book of the reference before
    ('note:Exod.12.48', '26,12', 0, 'Deut.26.12', 'catena', 'resolved'),          # "Dt 24 passim; 26,12"
    ('note:Prov.8.22', '24,1–29', 0, 'Sir.24.1', 'catena', 'resolved'),           # ", e soprattutto 24,1–29"
    ('note:Isa.4.2', '33,15', 0, 'Jer.33.15', 'catena', 'resolved'),              # "Ger 23,5 = 33,15"
    ('note:Prov.30.15', '11,2', 0, 'Eccl.11.2', 'catena', 'resolved'),            # "Qo 4,12 [?]; 11,2"
    ('note:Sir.49.9', 'cf. 38,22', 0, 'Ezek.38.22', 'catena', 'resolved'),        # "Ez 38–39, in particolare (cf."
    # puntatore: "v N" of the chapter just named
    ('note:2Kgs.24.18', 'v 3', 0, 'Jer.39.3', 'puntatore', 'resolved'),           # "(con un’aggiunta nel v 3)"
    ('note:John.19.36', 'v 21', 0, 'Ps.34.21', 'puntatore', 'resolved'),          # "un v del Sal 34 (il v 21)"
    ('note:Sir.14.21', 'vv 15.23.148', 0, 'Ps.119.15', 'puntatore', 'resolved'),
    # capitolo: a note on several chapters, or a verse the chapter does not have
    ('note:Judg.13.1', 'v 20', 0, 'Judg.15.20', 'capitolo', 'resolved'),
    ('note:Judg.13.1', 'v 31', 0, 'Judg.16.31', 'capitolo', 'resolved'),
    ('note:Num.13.1', 'vv 39–45', 0, 'Num.14.39', 'capitolo', 'resolved'),
    ('note:1Sam.16.14', 'v 31', 0, '1Sam.17.31', 'capitolo', 'resolved'),
    ('note:Isa.15.1', 'vv 13–14', 0, 'Isa.16.13', 'capitolo', 'resolved'),
    ('note:Jdt.15.14', 'vv 13–16', 0, 'Jdt.16.13', 'capitolo', 'resolved'),       # the next chapter
    # elenco: "Dopo i vv 4,7,15"
    ('note:Ps.66.4', 'vv 4,7', 0, 'Ps.66.4', 'elenco', 'resolved'),
    # ester: the key note is in the Greek text
    ('note:Jdt.5.4', 'cf. Est 3,8+', 0, 'EsthGr.3.8', 'ester', 'resolved'),
    ('mref:Dan.6.9_1', 'Est 1,19+', 0, 'EsthGr.1.19', 'ester', 'resolved'),
    # inizio: a misprinted end, linked to the first verse
    ('note:Sir.7.33', '2Mac 12,38–46', 0, '2Macc.12.38', 'inizio', 'partial'),
    ('mref:Luke.5.1_1', '‖Mt 4,18–29', 0, 'Matt.4.18', 'inizio', 'partial'),
    ('mref:2Cor.5.8_1', 'Fil 1,21–32', 0, 'Phil.1.21', 'inizio', 'partial'),
    # manuale: rows of the table CORREZIONI
    ('note:Luke.1.43', 'Marco (7,13', 0, 'Luke.7.13', 'manuale', 'resolved'),
    ('note:Luke.7.11', 'Giovanni (7,22', 0, 'Luke.7.22', 'manuale', 'resolved'),
    ('note:Rev.10.8', 'Giovanni (1,1–2.9–20', 0, 'Rev.1.1', 'manuale', 'resolved'),
    ('note:1Macc.1.16', 'v 28', 0, 'Dan.11.28', 'manuale', 'resolved'),
    ('note:1Macc.1.16', 'vv 31–39', 0, 'Dan.11.31', 'manuale', 'resolved'),
    ('note:Jer.5.11', '8,14', 0, 'Isa.8.14', 'manuale', 'resolved'),
    ('note:Jer.18.1', 'c 5', 0, 'Ezek.5.1', 'manuale', 'resolved'),
    ('note:1Pet.1.23', '1,25', 1, 'Jas.1.25', 'manuale', 'resolved'),
    ('note:1Pet.1.23', '1,25', 2, '1Pet.1.25', None, 'resolved'),                 # only the first one
    ('note:Exod.20.1', 'v 9', 0, 'Jer.7.9', 'manuale', 'resolved'),
    ('note:1Cor.12.31', 'v 13', 0, '1Cor.13.13', 'manuale', 'resolved'),
    ('note:Josh.8.30', 'cc 11', 0, 'Deut.11.1', 'manuale', 'resolved'),
    ('note:Matt.8.3', '8,1–4,5', 0, 'Matt.8.1', 'manuale', 'partial'),            # a misprint: its first verse
    ('intro-atti.8', '15,22ss', 0, 'Rom.15.22', 'manuale', 'resolved'),
    ('intro-apocalisse.2', 'Giovanni (1,9', 0, 'Rev.1.9', 'manuale', 'resolved'),
    # introduzione: introductions to several books
    ('intro-pentateuco.6', '1,1–15,21', 0, 'Exod.1.1', 'introduzione', 'resolved'),
    ('intro-storici.11', '13,1–6', 0, 'Josh.13.1', 'introduzione', 'resolved'),
    ('intro-profeti.51', '4,20', 0, 'Lam.4.20', 'introduzione', 'resolved'),
    ('intro-sinottici.25', '1,32–34', 0, 'Mark.1.32', 'introduzione', 'resolved'),
    ('intro-sinottici.18', '3,2', 0, 'Matt.3.2', 'introduzione', 'resolved'),
    # nudo: "come in 11,7, o"
    ('note:Gen.1.26', '11,7', 0, 'Gen.11.7', 'nudo', 'resolved'),
    ('note:John.2.4', '19,26', 0, 'John.19.26', 'nudo', 'resolved'),
    # aggiunta: rows of the table AGGIUNTE (the grammar does not read them)
    ('note:Isa.11.2', '25–26', 0, 'Num.11.25', 'aggiunta', 'resolved'),          # "Nm 11,17 (Mosè); 25–26"
    ('note:Josh.8.30', '27', 0, 'Deut.27.1', 'aggiunta', 'resolved'),             # "ai cc 11, 27 e 31 del Dt"
    ('note:Josh.8.30', '31', 0, 'Deut.31.1', 'aggiunta', 'resolved'),
    ('note:Exod.20.1', '22', 0, 'Deut.5.22', 'aggiunta', 'resolved'),             # "Dt 5, soprattutto vv 4 e 22"
    # left as the grammar reads them (the current book is right)
    ('note:Gen.1.1_2', '22,1a', 0, 'Gen.22.1', None, 'resolved'),
    ('note:Deut.14.21', '5,14', 0, 'Deut.5.14', None, 'resolved'),
]


def test_contesto():
    """The links of collegamenti.json read in the sense of the sentence (CONTEXT), the record of
    each correction, and the table: every row used, every row with its reason."""
    links = json.load(open(R.OUT, encoding='utf-8'))['links']
    by = {}
    for x in links:
        by.setdefault((x['source'], x['raw']), []).append(x)
    bad = []
    for src, raw, nth, want, rule, status in CONTEXT:
        lns = sorted(by.get((src, raw), []), key=lambda x: (x.get('offset', 0), x['id']))
        if len(lns) < max(nth, 1):
            bad.append('%s %r: no such link' % (src, raw))
            continue
        x = lns[max(nth, 1) - 1]
        got = (R.first_target(x), x.get('corrected'), x['status'])
        if got != (want, rule, status):
            bad.append('%s %r: %s, expected %s' % (src, raw, got, (want, rule, status)))
        if rule and not x.get('why'):
            bad.append('%s %r: no reason' % (src, raw))
        if rule and rule not in R.AGGIUNTI and x.get('corrected_from') == want:
            bad.append('%s %r: corrected_from is the new target' % (src, raw))
    first = next(x for x in links if x['id'] == 'note:Exod.12.48#c16')
    if first.get('corrected_from') != 'Exod.26.12':
        bad.append('note:Exod.12.48#c16: corrected_from %r, expected Exod.26.12' % first.get('corrected_from'))
    rows = [r for r in R.CORREZIONI if not (r[0] and r[1] and r[3] in R.SIGLA and r[5])]
    if rows:
        bad.append('table rows without source, reference, siglum or reason: %s' % rows)
    manual = sum(1 for x in links if x.get('corrected') == 'manuale')
    if manual != len(R.CORREZIONI):
        bad.append('%d links corrected by the table, %d rows' % (manual, len(R.CORREZIONI)))
    if sum(1 for x in links if x.get('corrected') == 'aggiunta') != len(R.AGGIUNTE):
        bad.append('the table AGGIUNTE: %d rows, %d links' % (
            len(R.AGGIUNTE), sum(1 for x in links if x.get('corrected') == 'aggiunta')))
    added = [x for x in links if x.get('corrected') in R.AGGIUNTI]
    spans = {}
    for x in links:
        if x['kind'].endswith('-cites') and not x.get('corrected') in R.AGGIUNTI:
            spans.setdefault(x['source'], []).append((x['offset'], x['offset'] + x['length']))
    over = [x['id'] for x in added if any(a < x['offset'] + x['length'] and x['offset'] < b
                                          for a, b in spans.get(x['source'], []))]
    if over:
        bad.append('added links overlapping a link of the grammar: %s' % over[:5])
    assert not bad, '\n'.join(bad)


def main(a):
    verbose = '-v' in a
    failed = 0
    for fn, args, expected in CASES:
        problems = check(fn, args, expected)
        if problems:
            failed += 1
            print('FAIL %s%r\n     %s' % (fn.__name__, args, '\n     '.join(problems)))
        elif verbose:
            print('ok   %s%r' % (fn.__name__, args))
    for test in (test_parse_structure, test_collegamenti_file, test_contesto):
        try:
            test()
        except AssertionError as e:
            failed += 1
            print('FAIL %s: %s' % (test.__name__, e))
    print('%d cases + parse structure + collegamenti.json + %d read in the sense of the sentence: %s' % (
        len(CASES), len(CONTEXT), 'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
