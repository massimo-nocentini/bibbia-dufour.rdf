"""Tests of eventi.py: the rules on strings, real dates read in the volumes, the chronology and the order.

usage: vendor/venv/bin/python -I tools/ontologia/test_eventi.py [-v]

Needs ontologia/build/eventi.json (eventi.py) and the build files it reads. The string cases go
through eventi.leggi(text, context): what a date expression gives in a text of the Old Testament
('AT'), the New ('NT'), a section NT of the Dizionario ('NTd'), the front matter ('moderno'), the
chronological table before or after its turn ('aC', 'dC') or a text of no known testament (None).
The real cases were read in their note, introduction, paragraph or entry. Plain asserts, so it also
runs under pytest. Exit status 1 if a case fails.
"""
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eventi as EV  # noqa: E402
import riferimenti as R  # noqa: E402

_cache = {}


def dati():
    if not _cache:
        _cache['E'] = json.load(open(EV.OUT, encoding='utf-8'))
    return _cache['E']


def build(nome):
    k = 'b:' + nome
    if k not in _cache:
        _cache[k] = json.load(open(os.path.join(EV.BUILD, nome), encoding='utf-8'))
    return _cache[k]


# text, context -> the expressions dated: (as printed, start, end, precision); a refused one is
# (as printed, None, the start of its reason)
SI = [
    ('Gerusalemme fu presa nel 587.', 'AT', [('nel 587', -587, -587, 'anno')]),
    ('diciamo verso il 1250 o poco prima', 'AT', [('verso il 1250', -1250, -1250, 'circa')]),
    ('designa Ramses II (1290–1224) come il faraone', 'AT', [('1290–1224', -1290, -1224, 'intervallo')]),
    ('dopo Acaz (736–716) fino all’epoca persiana', 'NT', [('736–716', -736, -716, 'intervallo')]),
    ('distrusse la città nel 587 a.C. (2Re 25)', 'NT', [('nel 587 a.C.', -587, -587, 'anno')]),
    ('la città sarà distrutta nel 70 d.C. da Tito', 'AT', [('nel 70 d.C.', 70, 70, 'anno')]),
    ('Dal IV secolo d.C., la tradizione', 'AT', [('Dal IV secolo d.C.', 301, 400, 'secolo')]),
    ('a partire dal IV secolo, i Padri', 'AT', [('dal IV secolo', -400, -301, 'secolo')]),
    ('sfruttato nel XIII sec. a.C. A Meneijeh', 'AT', [('nel XIII sec. a.C.', -1300, -1201, 'secolo')]),
    ('i Filistei (sec. XI).', 'AT', [('sec. XI', -1100, -1001, 'secolo')]),
    ('fissato nei sec. VIII–IX d.C. dai rabbini', 'moderno', [('nei sec. VIII–IX d.C.', 701, 900, 'secolo')]),
    ('che va dal IV al III sec. a.C., che ci è', 'AT', [('dal IV al III sec. a.C.', -400, -201, 'secolo')]),
    ('alla fine del sec. XIII a.C.', 'AT', [('alla fine del sec. XIII a.C.', -1225, -1201, 'secolo')]),
    ('verso la metà del XII sec. a.C.', 'AT', [('verso la metà del XII sec. a.C.', -1175, -1126, 'secolo')]),
    ('all’inizio del II millennio', 'AT', [('all’inizio del II millennio', -2000, -1751, 'millennio')]),
    ('II-I millennio a.C.', None, [('II-I millennio a.C.', -2000, -1, 'millennio')]),
    ('a Gerusalemme dal 445 al 433 a.C.', 'AT', [('dal 445 al 433 a.C.', -445, -433, 'intervallo')]),
    ('scritto tra il 167 e il 164', 'AT', [('tra il 167 e il 164', -167, -164, 'intervallo')]),
    ('tetrarca dal 4 a.C. al 39 d.C.', 'NT', [('dal 4 a.C. al 39 d.C.', -4, 39, 'intervallo')]),
    ('Filone d’Alessandria (20 a.C. – 54 d.C.) e', 'AT', [('20 a.C. – 54 d.C.', -20, 54, 'intervallo')]),
    ('caduta di Samaria nel 722/721 a.C., sono', 'AT', [('nel 722/721 a.C.', -722, -721, 'intervallo')]),
    ('Fine dicembre del 589/8.', 'AT', [('del 589/8', -589, -588, 'intervallo')]),
    ('al tempo: verso l’anno 5 oppure 4 a.C., dato che', 'NT',
     [('verso l’anno 5 oppure 4 a.C.', -5, -4, 'circa')]),
    ('Gerusalemme nel 597, 587, 582 (2 Re 24, 14)', 'AT',
     [('nel 597', -597, -597, 'anno'), ('587', -587, -587, 'anno'), ('582', -582, -582, 'anno')]),
    ('pone il proconsolato di Gallione nel 51–52', 'NT', [('nel 51–52', 51, 52, 'intervallo')]),
    ('fornito da Paolo nell’anno 55, muovendo', 'NTd', [('nell’anno 55', 55, 55, 'anno')]),
    ('Nell’853, a Karkar sull’Oronte vince 12 re', 'aC', [('Nell’853', -853, -853, 'anno')]),
    ('esattamente il 16 marzo del 597, secondo una cronaca', 'AT', [('del 597', -597, -597, 'anno')]),
    ('Al quarto mese: giugno-luglio 587.', 'AT', [('587', -587, -587, 'anno')]),
    ('50 ca., ad Alessandria: la Sapienza.', 'aC', [('50 ca.', -50, -50, 'circa')]),
    ('discusso dai rabbini del I sec. della nostra èra, ma', 'AT',
     [('del I sec. della nostra èra', 1, 100, 'secolo')]),
    ('Nel primo secolo della nostra era il giudaismo', None, [('Nel primo secolo della nostra era', 1, 100, 'secolo')]),
    ('Fu procuratore della Giudea dal 52 al 59 o 60.', 'NT', [('dal 52 al 59 o 60', 52, 60, 'intervallo')]),
    ('l’apologista Giustino che, verso il 150, scrive', 'NT', [('verso il 150', 150, 150, 'circa')]),
    ('Nel 1956 esce un volume unico telato', 'moderno', [('Nel 1956', 1956, 1956, 'anno')]),
    ('fra il 1945 e il 1955 i libri', 'moderno', [('fra il 1945 e il 1955', 1945, 1955, 'intervallo')]),
    ('per iscritto, almeno in parte, prima del 721 a.C. In ogni caso', 'AT',
     [('prima del 721 a.C.', -721, -721, 'anno')]),
    ('ASSURBANIPAL (669–630?).', 'aC', [('669–630?', -669, -630, 'intervallo')]),
    ('esisteva già nel 114 (o 78) a.C., quando', 'AT', [('già nel 114 (o 78) a.C.', -114, -114, 'anno')]),
    ('la rovina di Gerusalemme del 587 (o 586?) a.C. e', 'NT', [('del 587 (o 586?) a.C.', -587, -587, 'anno')]),
    ('si trova già nella Didachè (II sec.) e in', 'NT', [('II sec.', 101, 200, 'secolo')]),
    ('anniversario sin dal sec. II a. C., perché', None, [('dal sec. II a. C.', -200, -101, 'secolo')]),
    ('la Giudea sotto il giogo nel 485, cosicché', None, [('nel 485', -485, -485, 'anno')]),
    ('Secondo il titolo, Sofonia ha profetato sotto Giosia (640–609).', 'AT',
     [('640–609', -640, -609, 'intervallo')]),
    ('GIOVANNI IRCANO (I): 134–104.', 'aC', [('134–104', -134, -104, 'intervallo')]),
    ('841 Salmanassar III vince Cazaèl', 'aC', [('841', -841, -841, 'anno')]),
    ('Senzio Saturnino legato in Siria (9–6).', 'aC', [('9–6', -9, -6, 'intervallo')]),
    ('Volusio Saturnino, legato in Siria (4–5).', 'dC', [('4–5', 4, 5, 'intervallo')]),
    ('sotto il dominio egiziano; ma nel 605, a Carchemis', 'AT', [('nel 605', -605, -605, 'anno')]),
    ('Dicembre 589 – gennaio 588.', 'AT', [('Dicembre 589 – gennaio 588', -589, -588, 'intervallo')]),
    # the classes found by the adversarial review (stage 2f, round 1): spans "N/M–K" of the table,
    ('SELEUCO I NICATORE (305/4–281). Nel 300, fonda', 'aC',
     [('305/4–281', -305, -281, 'intervallo'), ('Nel 300', -300, -300, 'anno')]),
    ('Artaserse III Ocos (359/8–338/7).', 'aC', [('359/8–338/7', -359, -337, 'intervallo')]),
    ('ARSHAM, satrapo d’Egitto (455/454–403 ca.).', 'aC', [('455/454–403 ca.', -455, -403, 'circa')]),
    ('(458: missione di Esdra, se Esd 7,7 intende', 'aC', [('458', -458, -458, 'anno')]),
    # «ca.» after «dal … al», a longer second year of an ascending span,
    ('Egitto: dal 1720 al 1552 ca., gli Hyksos', 'aC', [('dal 1720 al 1552 ca.', -1720, -1552, 'circa')]),
    ('tra le due rivolte giudaiche (64–135 d.C.), deve', 'NT', [('64–135 d.C.', 64, 135, 'intervallo')]),
    # «gli anni …»: a decade or a span, a list of them,
    ('nato dall’assemblea che si tenne verso gli anni 80. E se', 'NT', [('verso gli anni 80', 80, 89, 'circa')]),
    ('Di conseguenza la si data negli anni 61–63.', 'NT', [('negli anni 61–63', 61, 63, 'intervallo')]),
    ('occupano rispettivamente gli anni 50–52 e 53–58; ne', 'NT',
     [('gli anni 50–52', 50, 52, 'intervallo'), ('53–58', 53, 58, 'intervallo')]),
    ('nato prima della morte di Erode, forse già negli anni 8–6. Di fatto', 'NT', [('negli anni 8–6', -8, -6, 'intervallo')]),
    # a title before a span of two digits in parentheses, two digits after a month in the NT,
    ('Claudio: sotto il regno di Claudio (41–54), l’impero', 'NT', [('41–54', 41, 54, 'intervallo')]),
    ('al mandato del procuratore Cuspio Fado (44–46).', 'NT', [('44–46', 44, 46, 'intervallo')]),
    ('prima della fine del febbraio 44. Letterariamente', 'NT', [('44', 44, 44, 'anno')]),
    ('nell’inverno 54–55 (At 20,1–2)', 'NT', [('54–55', 54, 55, 'intervallo')]),
    # «il N e il M d.C.», a colon or comma after «anno …» or «date …», years of four digits in parentheses
    ('è caduto di venerdì il 30 e il 33 d.C., gli esegeti', 'NT',
     [('il 30', 30, 30, 'anno'), ('il 33 d.C.', 33, 33, 'anno')]),
    ('Nel quarto anno di Ioiakìm: 605. Ioiakìm', 'AT', [('605', -605, -605, 'anno')]),
    ('Le date di queste deportazioni sono quindi: 598, 587 e 582.', 'AT',
     [('598', -598, -598, 'anno'), ('587', -587, -587, 'anno'), ('582', -582, -582, 'anno')]),
    ('anno centosettantaquattro: 139–138. — Le prime monete', 'AT', [('139–138', -139, -138, 'intervallo')]),
    ('(quinto anno dell’esilio di Ioiachin, 593–592). L’altra', 'AT', [('593–592', -593, -592, 'intervallo')]),
    ('dalle due precedenti edizioni (1955 e 1973), che', 'moderno',
     [('1955', 1955, 1955, 'anno'), ('1973', 1973, 1973, 'anno')]),
    ('della Conferenza Episcopale Italiana (1971; 1974) seguono', 'moderno',
     [('1971', 1971, 1971, 'anno'), ('1974', 1974, 1974, 'anno')]),
    # round 2: a span or an event set off by commas, a year after «regno di», «N–M/K», spans «N–M e K–L» in
    # parentheses, «dal sec. N al sec. M», the turn of the era, «dal N al M o K»
    ('Si tratta del faraone Cofra (Aprie), 589–570, presso cui', 'AT', [('589–570', -589, -570, 'intervallo')]),
    ('AKNATON (= Amenofi IV, 1374–1347). Promuove il culto', 'aC', [('1374–1347', -1374, -1347, 'intervallo')]),
    ('per vincere Antigono (battaglia di Gaza, 312, inizio dell’èra dei Seleucidi)', 'AT', [('312', -312, -312, 'anno')]),
    ('anteriore alla morte di Pietro, 64 o 67, benché Silvano', 'NT', [('64 o 67', 64, 67, 'intervallo')]),
    ('Infine a partire dal regno di Erode (37), i sommi sacerdoti', 'AT', [('37', -37, -37, 'anno')]),
    ('Artaserse II Mnemone (404–359/358).', 'aC', [('404–359/358', -404, -358, 'intervallo')]),
    ('Demetrio II (145–140 e 129–125).', 'aC',
     [('145–140', -145, -140, 'intervallo'), ('129–125', -129, -125, 'intervallo')]),
    ('le applicazioni che ne fanno i profeti, dal sec. VIII al sec. IV, si ritrova', 'AT',
     [('dal sec. VIII al sec. IV', -800, -301, 'secolo')]),
    ('Nato a Tarso di Cilìcia verso l’inizio della nostra èra (Fm 9) da una famiglia', 'NT',
     [('verso l’inizio della nostra èra', 1, 25, 'secolo')]),
    ('un rigurgito dell’antica corrente: alla vigilia della nostra èra, l’attesa', 'AT',
     [('alla vigilia della nostra èra', -25, -1, 'secolo')]),
    # the review of the feature: spans with months or parts of a year at their ends are one event (D4), «N o nel M»
    # one event with the other year, the turn of the era said with «èra cristiana» (D9), the part of a decade (D10)
    ('e del nono anno: fra dicembre del 589 e gennaio del 588, termine', 'AT',
     [('fra dicembre del 589 e gennaio del 588', -589, -588, 'intervallo')]),
    ('Dicembre del 586 – gennaio del 585, ma questa data', 'AT', [('Dicembre del 586 – gennaio del 585', -586, -585, 'intervallo')]),
    ('cioè tra la fine del 486 e l’inizio del 485.', 'AT', [('tra la fine del 486 e l’inizio del 485', -486, -485, 'intervallo')]),
    ('centosettantadue: tra l’ottobre del 141 e il settembre del 140.', 'AT',
     [('tra l’ottobre del 141 e il settembre del 140', -141, -140, 'intervallo')]),
    ('va quindi dal 19 agosto del 28 al 18 agosto del 29, oppure', 'NT',
     [('dal 19 agosto del 28 al 18 agosto del 29', 28, 29, 'intervallo')]),
    ('in Siria, dal settembre-ottobre del 27 al settembre-ottobre del 28.', 'NT',
     [('dal settembre-ottobre del 27 al settembre-ottobre del 28', 27, 28, 'intervallo')]),
    ('secondo viaggio tra l’autunno 48 e l’estate 49 (At 16,12–40).', 'NT', [('tra l’autunno 48 e l’estate 49', 48, 49, 'intervallo')]),
    ('(At 18,1–18), dalla primavera del 50 alla fine dell’estate del 51.', 'NT',
     [('dalla primavera del 50 alla fine dell’estate del 51', 50, 51, 'intervallo')]),
    ('al periodo che va dal 626 circa al luglio del 587.', 'AT', [('dal 626 circa al luglio del 587', -626, -587, 'circa')]),
    ('quella di Tiglat-Pilèser III nel 735 o nel 732, quella', 'AT', [('nel 735 o nel 732', -735, -732, 'intervallo')]),
    ('martire a Roma sotto Nerone, nel 64 o nel 67.', 'NT', [('nel 64 o nel 67', 64, 67, 'intervallo')]),
    ('fissato dagli ebrei di Palestina sull’inizio dell’èra cristiana, è', 'moderno',
     [('sull’inizio dell’èra cristiana', 1, 25, 'secolo')]),
    ('in molte opere apocrife scritte intorno all’èra cristiana. Il NT', 'NT', [('intorno all’èra cristiana', -25, 25, 'circa')]),
    ("Nel giudaismo vicino all'era cristiana, il legato", None, [("vicino all'era cristiana", -25, 25, 'circa')]),
    ('la divisione in cinque libri è attestata prima della nostra èra dalla', 'AT',
     [('prima della nostra èra', -25, -1, 'secolo')]),
    ('nel 63 prima della nostra èra', 'AT', [('nel 63 prima della nostra èra', -63, -63, 'anno')]),
    ('va fatto risalire pressappoco al 605 la', 'AT', [('al 605', -605, -605, 'circa')]),
    ('all’inizio degli anni 40 scrive', 'NT', [('degli anni 40', 40, 42, 'intervallo')]),
]
# never a year: no expression at all
NIENTE = [
    ('Israele restò nel deserto 40 anni', 'AT'),
    ('come si legge nel cap. 10 e al cap. 12', 'AT'),
    ('i salmi dei secoli e i secoli dei secoli', 'NT'),
    ('nel 4QSam e in 1QIs', 'AT'),
    ('nel 2 Re e nel 1 Sam', 'AT'),
    ('Pio XII e sec. la LXX', 'AT'),
    ('Più di 6.000 Farisei rifiutano', 'aC'),
    ('come in 11,7, o come in 12,3', 'AT'),
    ('il v 5 e i vv 12–14', 'AT'),
    ('a p. 123 e alla nota 5', 'moderno'),
    ('Pasqua il 14 del mese', 'AT'),
    ('hanno dato il 753 come inizio della nostra èra', 'NT'),
    ('dopo 40 giorni e 40 notti', 'NT'),
    ('accordate in Cristo (9–11)? Ma', 'NT'),                     # chapters after a name, not a title
    ('Marco segue la tradizione comune (14–15), ma', 'NT'),
    ('BJ legge invece: «coppe d’argento: 1000; logorate: 410».', 'AT'),
    ('fra i 50 e i 60 anni', 'NT'),
    ('scoperte di Qumran (cf. Ant. Giud. XIII, 171–173, dove si parla', 'AT'),   # an ascending span after a comma
    ('l’imperatore Vespasiano, 69–79, e', 'NT'),                                # two digits after a comma
]
# never dated: every expression refused (the psalm numbers of a list in parentheses, a day after a month)
MAI = [
    ('quello delle salite (120–134), quello dell’Hallel (105–107; 111–118; 135; 136; 146–150).', 'AT'),
    ('tra l’autunno 48 e l’estate 49', 'AT'),
]
# refused (the first expression of the text), with the start of the reason
NO = [
    ('La LXX inserisce (fine del v 14 – inizio del 15)', 'AT', 'segnale debole'),
    ('nel pomeriggio del 14 nisan, la immolazione', 'NT', 'giorno del mese'),
    ('Tiberio, nell’anno 15 di Tiberio', 'NT', 'anno di regno'),
    ('L’anno 15° di Tiberio (Lc 3,1)', 'dC', 'ordinale'),
    ('scritta nel 169 seleucidico (142 a.C.)', 'AT', 'anno di un’altra era'),
    ('gli azzimi si fissano infine dal 15 al 21.', 'AT', 'segnale debole'),
    ('la cui base è 17, ossia 10+7 che', 'NT', 'calcolo'),
    ('scoperto a Qumran nel 1947 e', 'AT', 'anno di quattro cifre'),
    ('l’Hallel (113–118), che gli Ebrei', 'AT', 'intervallo crescente'),
    ('Dalla fine del secolo XIX in poi', 'AT', 'secolo ≥ XV'),
    ('morì nel 4, a Gerico', 'NT', 'una cifra'),
    ('dall’8 al 14 del settimo mese', 'AT', 'una cifra'),
    ('L’«èra cristiana» (fissata da Dionigi) fa cominciare all’anno 782 di Roma il', 'NT', 'anno di un’altra era'),
    ('il giudaismo rabbinico, dopo il 70, conosce', None, 'era incerta'),
    ('salto del copista dal 1° «Israele» al 3°', 'AT', 'ordinale'),
    ('all’inizio del terzo millennio, le stampe', 'moderno', 'millennio in un testo moderno'),
    ('nella Grecia del sec. VI la riflessione', None, 'era incerta'),
]


def test_regole():
    bad = []
    for testo, ctx, atteso in SI:
        got = [x[:4] for x in EV.leggi(testo, ctx, tavola=ctx in ('aC', 'dC'))]
        if got != atteso:
            bad.append((testo, got))
    for testo, ctx in NIENTE:
        got = EV.leggi(testo, ctx, tavola=ctx in ('aC', 'dC'))
        if got:
            bad.append((testo, got))
    for testo, ctx, motivo in NO:
        got = EV.leggi(testo, ctx, tavola=ctx in ('aC', 'dC'))
        if not got or got[0][1] is not None or not got[0][2].startswith(motivo):
            bad.append((testo, got))
    for testo, ctx in MAI:
        got = [x for x in EV.leggi(testo, ctx) if x[1] is not None]
        if got:
            bad.append((testo, got))
    assert not bad, bad


def test_frasi():
    """The sentence of a date: a dash ends it only after a full stop (the lemmas of a note), not inside it; a
    sentence that opens with its date starts there; after «a.C.», «d.C.», «sec.», «ca.» or an initial a sentence
    ends before a word that opens one, not before a name; «J. Ziegler», «per es.», «F.Ch. Baur», «a. C.» never
    end one (round 2)."""
    ev = {e['id']: e for e in dati()['eventi']}
    bad = []
    for k, inizio, fine in [('ev:note:Ezra.4.1@58', 'Ag 1,2 imputava', 'alla negligenza dei Giudei.'),
                            ('ev:note:Hos.5.8@108', 'Tutto questo brano', '(735–734; cf. 2Re 16,5+).'),
                            ('ev:intro-storici.33@182', 'L’espansione dei Filistei', None),
                            ('ev:note:Luke.3.1@1083', 'Erode: Antipa', 'dal 4 a.C. al 39 d.C.'),
                            ('ev:note:Isa.21.13@468', 'Nel 715, Sargon', 'poteva sentirsi allora minacciato.'),
                            ('ev:intro-profeti.44@1090', 'Dal 605, Nabucodònosor', None),
                            ('ev:note:Num.21.4@110', 'Questo episodio', 'già sfruttato nel XIII sec. a.C.'),
                            ('ev:note:John.2.20@93', 'Ciò situa la scena', None),
                            ('ev:intro-cattoliche.11@614', 'I vizi e la licenza', None),
                            ('ev:intro-siracide.5@265', 'Tuttavia, in seguito all’edizione critica di J. Ziegler',
                             'trasmesse dai manoscritti greci.'),
                            ('ev:note:Matt.6.13@427', 'Già dai primi secoli molti mss latini (per es. Codex', None),
                            ('ev:intro-atti.6@196', 'La scuola di F.Ch. Baur', None),
                            ('ev:pentecoste.4@294', 'L\'alleanza era stata conclusa', 'manoscritti di Qumrân.'),
                            ('ev:note:1Macc.2.42@356', 'Secondo Giuseppe Flavio', 'sadducei ed esseni).')]:
        f = ev[k]['frase']
        if not f.startswith(inizio) or (fine and not f.endswith(fine)):
            bad.append((k, f[:60], f[-40:]))
    # the references of the sentence before are not the date's: «… (Gen 25,13; Ger 49,28; Ez 27,21). Nel 715»
    if ev['ev:note:Isa.21.13@468']['versetti'] or ev['ev:note:2Macc.1.1_2@143']['riferimenti']:
        bad.append('versetti della frase precedente')
    # on strings: a name after «a.C.» does not open a sentence
    for testo, parola, nuova in [('All’inizio del II sec. a.C. Gesù Ben Sira raccoglie', 'Gesù', False),
                                 ('fu intrapresa nel 19 a.C. Ciò situa la scena', 'Ciò', True),
                                 ('il 19 agosto dell’anno 14 d.C. L’anno quindicesimo va', 'L’anno', True),
                                 ('nel 63 a.C. Pompeo prese Gerusalemme', 'Pompeo', False),
                                 ('lo gnosticismo del II sec. I vizi e la licenza', 'I vizi', True),
                                 ('dell’edizione di J. Ziegler del 1965', 'Ziegler', False),
                                 ('con il codice B. Il testo', 'Il testo', True)]:
        k = testo.index(parola)
        if (EV.frase_inizio(testo, k) == k) != nuova:
            bad.append((testo, EV.frase_inizio(testo, k)))
    assert not bad, bad


# a bound said by the words before an expression: (text, limite) (round 2)
LIMITI = [
    ('al primo periodo, anteriore al 735. Come', 'ante'),
    ('il giudaismo posteriore al 70 di fronte', 'post'),
    ('non potrebbe essere anteriore agli anni 80.', 'post'),
    ('non è attestato con certezza prima del III sec., ma', 'post'),
    ('Ma a partire dal IV secolo, i Padri', 'post'),
    ('Dalla fine del II sec., i Vangeli', 'post'),
    ('alcuni rabbini l’hanno citato fino al IV sec.: il Talmud', 'ante'),
    ('un manoscritto che data probabilmente dal II sec. a.C. Esso', None),
    ('possiamo risalire circa fino all’VIII secolo e non', None),
    ('tetrarca dal 4 a.C. al 39 d.C.', None),
    ('nel 587, la città', None),
    # the review of the feature (D9, D10)
    ('morì nel 43, in ogni caso prima della fine del febbraio 44. Letterariamente', 'ante'),
    ('Infine a partire dal regno di Erode (37), i sommi sacerdoti', 'post'),
    ('a partire dal sinodo romano del 382, il', 'post'),
    ('computato a partire dalla primavera (del 311).', None),
    ('elaborata a partire dalle due precedenti edizioni (1955 e 1973), che', None),
    ('la tradizione giudaica posteriore all’èra cristiana ha seguito', 'post'),
    ('è attestata prima della nostra èra dalla versione', 'ante'),
    ('al periodo che va dal 626 circa al luglio del 587.', None),
]


def test_limiti():
    """A bound said by the words before an expression (round 2): «anteriore al», «posteriore al», «fino al»,
    «a partire dal», «Dalla fine del», a negation turns it; the date of an origin («che data dal») is none."""
    bad = []
    for testo, atteso in LIMITI:
        x = EV.espressioni(testo)
        if not x or x[-1]['limite'] != atteso:
            bad.append((testo, x and x[-1]['limite']))
    assert not bad, bad


def test_riferimenti_mai_anni():
    """A reference parsed by stage 2 (masked first) never becomes a year, on strings and in the file."""
    bad = []
    ctx = dict(book='Gen', chapter=12, margin=False)
    for testo, ctx_ev in [('cf. Gen 12,1 nel 587', 'AT'), ('(Gs 5,10; 2Re 23,21) nel 622', 'AT'),
                          ('nel Sal 110 e nel 1 Sam 4', 'AT'), ('di 8,14 (1150), di 12,11 (1290)', 'AT')]:
        spans = [(r['offset'], len(r['raw'])) for r in R.scan_prose(testo, ctx)]
        got = [x for x in EV.leggi(testo, ctx_ev, spans) if x[1] is not None]
        if any(re.search(r'\d+,\d+|Sal|Sam', x[0]) for x in got) or len(got) > 1:
            bad.append((testo, got))
    E = dati()
    # in the file: no date overlaps a reference of its sentence, none looks like "c,v"
    coll = build('collegamenti.json')
    spans = {}
    for l in coll['links']:
        if l['kind'] in ('note-cites', 'intro-cites') and l.get('offset') is not None:
            spans.setdefault(l['source'], []).append((l['offset'], l['offset'] + l['length']))
    for c in build('dufour.json')['citations']:
        if c.get('where') == 'paragraph' and c.get('offset') is not None:
            spans.setdefault(c['para'], []).append((c['offset'], c['offset'] + c['length']))
    for e in E['eventi']:
        if e['offset'] is None or not e['data']:
            continue
        a, b = e['offset'], e['offset'] + len(e['data'])
        if any(x < b and a < y for x, y in spans.get(e['sorgente'], ())) or re.search(r'\d,\d', e['data']):
            bad.append(e['id'])
    assert not bad, bad[:20]


# real cases: event id -> (as printed, start, end, precision, the start of era_da)
REALI = {
    'ev:note:2Kgs.25.8@66': ('nel 587', -587, -587, 'anno', 'fonte AT'),            # «di Sedecìa (v 2) nel 587»
    'ev:note:Josh.15.45@92': ('736–716', -736, -716, 'intervallo', 'ordine'),       # «dopo Acaz (736–716)»
    'ev:note:2Sam.5.9@1210': ('nel 70 d.C.', 70, 70, 'anno', 'suffisso'),           # «distrutta nel 70 d.C. da Tito»
    'ev:note:2Sam.5.9@751': ('nel 587 a.C.', -587, -587, 'anno', 'suffisso'),
    'ev:note:2Sam.5.9@802': ('nel 515', -515, -515, 'anno', 'fonte AT'),             # «riedificato nel 515 (Esd 6,15)»
    'ev:note:Exod.19.2@41': ('Dal IV secolo d.C.', 301, 400, 'secolo', 'suffisso'),
    'ev:note:Num.21.4@110': ('nel XIII sec. a.C.', -1300, -1201, 'secolo', 'suffisso'),
    'ev:intro-storici.11@1836': ('verso il 1250', -1250, -1250, 'circa', 'fonte AT'),
    'ev:note:Josh.3.16@41': ('nel 1267', 1267, 1267, 'anno', 'correzione'),          # «un cronista arabo»
    'ev:note:Luke.3.1@969': ('dal 26 al 36 d.C.', 26, 36, 'intervallo', 'suffisso'), # Ponzio Pilato
    'ev:note:Luke.3.1@1083': ('dal 4 a.C. al 39 d.C.', -4, 39, 'intervallo', 'suffisso'),  # Erode Antipa
    'ev:esilio.1@428': ('nel 597', -597, -597, 'anno', 'riferimenti AT'),           # Dizionario, ESILIO (no section VT)
    'ev:esilio.1@437': ('587', -587, -587, 'anno', 'riferimenti AT'),
    'ev:esilio.1@442': ('582', -582, -582, 'anno', 'riferimenti AT'),
    'ev:prefazione-filippi.4@0': ('Nel 1956', 1956, 1956, 'anno', 'fonte moderna'),
    'ev:note:Amos.1.1@195': ('783–743', -783, -743, 'intervallo', 'ordine'),
    'ev:cronologia.85': ('841', -841, -841, 'anno', 'tavola'),                      # «841 Salmanassar III vince…»
    'ev:cronologia.342': ('134–104', -134, -104, 'intervallo', 'ordine'),           # «GIOVANNI IRCANO (I): 134–104.»
    'ev:cronologia.401': ('4', -4, -4, 'anno', 'tavola'),
    'ev:cronologia.423': ('19 agosto 14', 14, 14, 'anno', 'tavola'),                # not the reign 14–37
    'ev:cronologia.1': ('2000000', -2000000, -2000000, 'riga', 'tavola'),
    'ev:cronologia.33': (None, -1250, -1250, 'riga', 'tavola'),                   # margin «1300; 1250», after «verso il 1250»
    'ev:dinastie.P15': ('37–4 a.C.', -37, -4, 'intervallo', 'suffisso'),
    'ev:dinastie.P29': ('† 44', 44, 44, 'anno', 'dinastie'),                        # Erode Agrippa I, 44 d.C.
    'ev:dinastie.P05': ('134–104', -134, -104, 'intervallo', 'dinastie'),
    'ev:carta.esodo': ('XIII sec. a.C.', -1300, -1201, 'secolo', 'suffisso'),
    'ev:carta.antico-oriente': ('II-I millennio a.C.', -2000, -1, 'millennio', 'suffisso'),
    # added or corrected by the adversarial review (round 1)
    'ev:note:Jer.52.30@49': ('587', -587, -587, 'anno', 'fonte AT'),               # «quindi: 598, 587 e 582»
    'ev:note:Acts.11.28@36': ('41–54', 41, 54, 'intervallo', 'ordine'),            # «regno di Claudio (41–54)»
    'ev:intro-sinottici.13@1232': ('verso gli anni 80', 80, 89, 'circa', 'fonte NT'),
    'ev:note:Luke.2.2@265': ('negli anni 8–6', -8, -6, 'intervallo', 'ordine'),
    'ev:note:Acts.12.1@249': ('44', 44, 44, 'anno', 'fonte NT'),                   # «del febbraio 44»
    'ev:note:Sir.1.1@1037': ('1971', 1971, 1971, 'anno', 'correzione'),            # «(1971 e 1974)»
    'ev:cronologia.252': ('305/4–281', -305, -281, 'intervallo', 'ordine'),        # not «Nel 300»
    'ev:cronologia.416': ('6–41', 6, 41, 'intervallo', 'ordine'),                  # «provincia procuratoria (6–41)»
    'ev:cronologia.18': ('dal 1720 al 1552 ca.', -1720, -1552, 'circa', 'ordine'),
    'ev:cronologia.131': ('verso il 690', -690, -690, 'circa', 'tavola'),          # not «nato verso il 710»
    'ev:cronologia.220': ('428', -428, -428, 'anno', 'tavola'),                    # «(428: missione di Esdra, se …)»
    # added or corrected by the adversarial review (round 2)
    'ev:cronologia.227': ('404–359/358', -404, -358, 'intervallo', 'ordine'),     # Artaserse II, not its row (401)
    'ev:cronologia.24': ('1374–1347', -1374, -1347, 'intervallo', 'ordine'),       # AKNATON, not the margin (1400)
    'ev:cronologia.327': ('145–140', -145, -140, 'intervallo', 'ordine'),          # «Demetrio II (145–140 e 129–125)»
    'ev:note:Ezek.29.2@37': ('589–570', -589, -570, 'intervallo', 'ordine'),       # «Cofra (Aprie), 589–570,»
    'ev:note:Dan.11.5@241': ('312', -312, -312, 'anno', 'fonte AT'),              # «battaglia di Gaza, 312,»
    'ev:intro-cattoliche.16@59': ('64 o 67', 64, 67, 'intervallo', 'fonte NT'),    # «morte di Pietro, 64 o 67,»
    'ev:sacerdozio.9@790': ('37', -37, -37, 'anno', 'fonte AT'),                  # «dal regno di Erode (37)»
    'ev:note:Acts.23.24@131': ('dal 52 al 59 o 60', 52, 60, 'intervallo', 'fonte NT'),
    'ev:intro-paolo.2@74': ('verso l’inizio della nostra èra', 1, 25, 'secolo', 'suffisso'),
    'ev:giorno-del-signore.2@249': ('dal sec. VIII al sec. IV', -800, -301, 'secolo', 'ordine'),
    # the review of the feature: spans with months (D4: the ids moved to the start of the span), the datings by their
    # own words (D5), the turn of the era (D9), the testament of the references said so (D13)
    'ev:note:Jer.39.1_2@31': ('fra dicembre del 589 e gennaio del 588', -589, -588, 'intervallo', 'ordine'),
    'ev:note:Luke.3.1@251': ('dal 19 agosto del 28 al 18 agosto del 29', 28, 29, 'intervallo', 'ordine'),
    'ev:note:Jer.1.2@45': ('dal 626 circa al luglio del 587', -626, -587, 'circa', 'ordine'),
    'ev:cronologia.431': ('dal 19 agosto del 28 al 18 agosto del 29', 28, 29, 'intervallo', 'ordine'),
    'ev:note:Isa.5.26@120': ('nel 735 o nel 732', -735, -732, 'intervallo', 'fonte AT'),
    'ev:datazione.96-1': ('750 ca.', -750, -750, 'circa', 'la voce della tavola'),     # not GEROBOAMO II (783–743)
    'ev:datazione.492-30': ('Dal 53', 53, 53, 'anno', 'la voce della tavola'),
    'ev:datazione.238-18': ('336–323', -336, -323, 'intervallo', 'la voce della tavola'),   # «Del tempo di Alessandro»
    'ev:divisione-ebraica.1@65': ('sull’inizio dell’èra cristiana', 1, 25, 'secolo', 'suffisso'),
    'ev:intro-apocalisse.2@303': ('intorno all’èra cristiana', -25, 25, 'circa', 'suffisso'),
    'ev:eresia.5@796': ('del 49', 49, 49, 'anno', 'riferimenti NT, ≤ 135'),
}


def test_reali():
    E = dati()
    ev = {e['id']: e for e in E['eventi']}
    bad = []
    for k, (raw, s, e, p, da) in REALI.items():
        x = ev.get(k)
        if not x or (x['data'], x['inizio'], x['fine'], x['precisione']) != (raw, s, e, p) or not x['era_da'].startswith(da):
            bad.append((k, x and (x['data'], x['inizio'], x['fine'], x['precisione'], x['era_da'])))
    # the note's anchor verse, where it opens, the references of its sentence and their verses
    data = build('bibbia.json')
    vid = [v['id'] for v in data['verses']]
    x = ev['ev:note:2Sam.5.9@1210']
    corse = [vid[i] for i in x['versetti']]
    if (x['verso'], x['apri'], x['riferimenti']) != ('2Sam.5.9', '#2Sam.5.9', [['cf. Lc 21,20', 'note:2Sam.5.9#c14']]) or \
            corse != ['Luke.21.20', 'Luke.21.20']:
        bad.append(('2Sam.5.9', x['verso'], x['apri'], x['riferimenti'], corse))
    x = ev['ev:carta.esodo']
    if [vid[i] for i in x['versetti']] != ['Exod.12.37', 'Exod.19.2', 'Num.33.1', 'Num.33.56']:
        bad.append(('esodo', x['versetti']))
    # rows and periods of the table: undated entries by their row
    for k, (s, e, da) in {'ev:cronologia.400': (-6, -4, 'riga: date delle altre voci'),         # Nascita di GESÙ
                          'ev:cronologia.551': (74, 81, 'riga: tra le righe vicine'),     # after «Masada (Pasqua 74)»
                          'ev:cronologia.247': (-323, -300, 'riga: tra le righe vicine'),        # In Egitto: i LAGIDI
                          'ev:cronologia.19': (-1700, -1700, 'riga: anno a margine'),
                          # between the dated entries of its column (review of stage 5)
                          'ev:cronologia.402': (-4, -4, 'riga: tra le voci della colonna'),   # morte di Erode
                          'ev:cronologia.404': (-4, -4, 'riga: tra le voci della colonna'),   # Sabino procuratore
                          'ev:cronologia.539': (70, 70, 'riga: tra le voci della colonna'),   # cessano i sacrifici
                          'ev:cronologia.33': (-1250, -1250, 'riga: tra le voci della colonna'),
                          # the headings of a column open it, at the first year of the entry they head
                          'ev:cronologia.55': (-931, -931, 'colonna: intestazione'),       # ISRAELE: Geroboamo I
                          'ev:cronologia.56': (-931, -931, 'colonna: intestazione')}.items():   # GIUDA: Roboamo
        x = ev[k]
        if (x['inizio'], x['fine'], x['data_da'], x['precisione']) != (s, e, da, 'riga'):
            bad.append((k, x['inizio'], x['fine'], x['data_da']))
    # so the siege of 70 reads in the order of the table, and a row across the eras is «a.C.–d.C.»
    pos = {x['id']: k for k, x in enumerate(E['eventi'])}
    if [pos['ev:cronologia.%d' % n] for n in range(537, 543)] != sorted(pos['ev:cronologia.%d' % n] for n in range(537, 543)):
        bad.append('order of the entries 537-542')
    # an entry placed by its row comes after the entry printed above it in its column, in its row or in the
    # rows above (fix D2 of the review of the feature), and a heading before the entry under it (D12)
    for su, giu in [(239, 240), (272, 273), (461, 462), (578, 579), (298, 300), (121, 126), (382, 384), (479, 482),
                    (81, 82), (218, 219), (549, 551), (550, 552), (119, 120), (55, 60), (56, 63)]:
        if pos['ev:cronologia.%d' % su] > pos['ev:cronologia.%d' % giu]:
            bad.append('entry %d shown before %d, printed above it' % (giu, su))
    if (ev['ev:cronologia.408']['inizio'], ev['ev:cronologia.408']['era']) != (-4, 'a.C.–d.C.'):
        bad.append(('era 408', ev['ev:cronologia.408']['era']))
    # a hypothesis of the table is uncertain; «dall’anno 200» is a lower bound
    if not ev['ev:cronologia.220']['incerto'] or ev['ev:intro-cattoliche.10@14']['limite'] != 'post':
        bad.append('incerto 220 / limite intro-cattoliche.10')
    # the same event: a note and the chronology entry of the same reign
    if 'ev:cronologia.96' not in ev['ev:note:Amos.1.1@195'].get('stesso_evento', ()) or \
            'ev:note:Amos.1.1@195' not in ev['ev:cronologia.96'].get('stesso_evento', ()):
        bad.append('stesso evento Amos.1.1 / 96')
    # a dating of a book carries its entry's date and link
    d = next(x for x in E['eventi'] if x['fonte'] == 'datazione' and x['voce'] == 285)
    c = ev['ev:cronologia.285']
    if (d['inizio'], d['fine'], d['libri'], d['stesso_evento']) != (c['inizio'], c['fine'], ['Sir'], ['ev:cronologia.285']):
        bad.append(('datazione 285', d['inizio'], d['libri']))
    # every same-event link both ways (the entry lists its dating too); the other year signed as the years;
    # a map opens on itself (review of stage 5)
    for x in E['eventi']:
        for y in x.get('stesso_evento', []):
            if x['id'] not in ev[y].get('stesso_evento', ()):
                bad.append(('one-way link', x['id'], y))
    if (ev['ev:note:Luke.19.43@240'].get('alternativa'), ev['ev:note:Acts.24.27@23'].get('alternativa')) != (-586, 60):
        bad.append('alternativa not signed')
    if ev['ev:carta.esodo']['apri'] != '#carte?c=esodo':
        bad.append(('carta apri', ev['ev:carta.esodo']['apri']))
    # review of the feature: a death of the dynasties only to the entry of the death (D3), no link from a bound, a
    # note to the entry citing its verse in a passage, not in a whole chapter (1Mac 7)
    if ev['ev:dinastie.P29'].get('stesso_evento') != ['ev:cronologia.465'] or \
            ev['ev:intro-profeti.49@371'].get('stesso_evento') or ev['ev:note:1Macc.7.1@266'].get('stesso_evento'):
        bad.append(('stesso evento P29 / bound / chapter', ev['ev:dinastie.P29'].get('stesso_evento')))
    for x, y in [('ev:note:Isa.6.1_2@48', 'ev:cronologia.104'), ('ev:note:Jer.46.2@170', 'ev:cronologia.163'),
                 ('ev:note:Dan.11.19@171', 'ev:cronologia.284')]:
        if y not in ev[x].get('stesso_evento', ()):
            bad.append(('stesso evento by the note\'s verse', x, y))
    # «prima del 70? o verso l’80?»: 80 with the other hypothesis, in the entry and its dating (D5); bounds and circa
    # said by the words before (D10); no sentence opens with the dash of a lemma (D14)
    if ev['ev:datazione.96-1'].get('stesso_evento') or 'ev:datazione.96-1' in ev['ev:cronologia.96'].get('stesso_evento', ()):
        bad.append('a dating with years of its own is not the same event as its entry')
    if (ev['ev:cronologia.519'].get('alternativa'), ev['ev:datazione.519-36'].get('alternativa')) != (70, 70):
        bad.append('alternativa 519')
    if (ev['ev:note:Acts.12.1@249']['limite'], ev['ev:sacerdozio.9@790']['limite'], ev['ev:intro-tobia.5@414']['limite'],
            ev['ev:note:Jer.49.7@44']['circa'], ev['ev:intro-paolo.2@1223']['fine']) != ('ante', 'post', 'post', True, 42):
        bad.append('limite / circa / decade')
    trattino = [x['id'] for x in E['eventi'] if (x['frase'] or '').startswith('—') or x['etichetta'].startswith('—')]
    if trattino:
        bad.append(('sentence opening with a dash', trattino[:5]))
    assert not bad, bad


def test_cronologia():
    """All 585 entries, once each, with the dates of stage 2c unchanged and the period of their section."""
    E = dati()
    P = build('paratesto.json')
    voci = {v['n']: v for v in P['cronologia']['voci']}
    cr = [e for e in E['eventi'] if e['fonte'] == 'cronologia']
    assert len(cr) == 585 and sorted(e['cronologia']['voce'] for e in cr) == list(range(1, 586))
    bad = []
    for e in cr:
        v = voci[e['cronologia']['voce']]
        if e['periodo'] != v['section'] or e['cronologia']['colonna'] != v['column'] or e['html'] != v['html']:
            bad.append((e['id'], 'section/column/html'))
        if v['start'] is not None and (e['inizio'], e['fine'], e['data_da']) != (v['start'], v['end'], 'tavola'):
            bad.append((e['id'], e['inizio'], v['start']))
        if v['start'] is None and e['data_da'] == 'tavola':
            bad.append((e['id'], 'undated in stage 2c'))
    assert not bad, bad
    c = Counter(e['data_da'] for e in cr)
    assert c['tavola'] == 388 and c['periodo'] == 0, c


def test_conteggi():
    E = dati()
    c = Counter(e['fonte'] for e in E['eventi'])
    atteso = dict(cronologia=585, dinastie=6, datazione=40, carta=8, nota=546, introduzione=267, testo=26, dizionario=68)
    assert dict(c) == atteso, dict(c)
    s = E['meta']['summary']
    assert s['fonti'] == dict(c) and s['eventi'] == len(E['eventi']) and s['non_datati'] == len(E['non_datati'])
    assert Counter(e['precisione'] for e in E['eventi']) == Counter(s['precisione'])
    # every person with a date, every non-«citato» dating, every map with a period
    I = build('integrazione.json')
    assert c['datazione'] == sum(1 for x in I['datazioni'] if x['tipo'] != 'citato')
    assert c['carta'] + sum(1 for x in E['non_datati'] if x['fonte'] == 'carta') == len(I['carte'])
    assert c['dinastie'] == sum(1 for p in build('paratesto.json')['dinastie'] if p['date'])


def test_ordine():
    E = dati()
    ev = E['eventi']
    assert [e['n'] for e in ev] == list(range(1, len(ev) + 1))
    assert all((a['inizio'], a['fine']) <= (b['inizio'], b['fine']) for a, b in zip(ev, ev[1:]))
    assert len({e['id'] for e in ev}) == len(ev)
    assert all(e['inizio'] <= e['fine'] and isinstance(e['inizio'], int) for e in ev)
    assert all(e['precisione'] in EV.PRECISIONI and e['fonte'] in EV.FONTI for e in ev)
    # the period of a free-text date is the one its start falls in
    per = E['periodi']
    assert [p['n'] for p in per] == list(range(1, 10)) and per[-1]['fine'] == 135
    bad = [e['id'] for e in ev if e['fonte'] != 'cronologia' and e['fonte'] != 'datazione' and
           e['periodo'] != EV.periodo_di(e['inizio'], per)]
    assert not bad, bad[:10]
    # within one source, events of the same years keep the order of the text
    for a, b in zip(ev, ev[1:]):
        if a['sorgente'] == b['sorgente'] and (a['inizio'], a['fine']) == (b['inizio'], b['fine']) and \
                a['offset'] is not None and b['offset'] is not None:
            assert a['offset'] < b['offset'], (a['id'], b['id'])


def test_periodi():
    """The periods by their numbers, not by the code that makes them (review of the feature, C7): the start of each
    period is in it, the year before is in the one before; the HTML cut keeps its tags open and closed."""
    per = dati()['periodi']
    assert [(p['inizio'], p['fine']) for p in per] == [
        (-2000000, -3001), (-3000, -1501), (-1500, -1201), (-1200, -932), (-931, -722), (-721, -539), (-538, -334),
        (-333, -64), (-63, 135)], per
    casi = [(-538, 7), (-539, 6), (-721, 6), (-722, 5), (-63, 9), (-64, 8), (135, 9), (136, None), (-2000000, 1),
            (-2000001, None), (1, 9)]
    got = [(y, EV.periodo_di(y, per)) for y, _ in casi]
    assert got == casi, got
    h = '<p>Nel <em>tempo di <b>Erode</b> il</em> grande</p>'
    assert EV.taglia_html(h, h.index('tempo'), h.index(' il</em>')) == '<p><em>tempo di <b>Erode</b></em></p>'
    assert EV.taglia_html(h, h.index('Erode'), h.index('grande')) == '<p><em><b>Erode</b> il</em> </p>'
    assert EV.bilanciato('<em>a <b>b</b></em>') and not EV.bilanciato('<em>a</b>') and not EV.bilanciato('<em>a') \
        and EV.bilanciato('a<br>b')


def test_non_datati():
    E = dati()
    nd = E['non_datati']
    assert all(x['motivo'] and x['fonte'] and x['sorgente'] for x in nd)
    k = {(x['sorgente'], x['data']): x['motivo'] for x in nd}
    for key, motivo in [(('note:Dan.12.11', '1290'), 'numero tra parentesi dopo un riferimento'),  # «di 12,11 (1290)»
                        (('note:2Macc.1.7', 'nel 169'), 'anno di un’altra era'),
                        (('note:Ps.113.1', '113–118'), 'numero di salmo'),
                        (('palestina-at', None), 'carta senza periodo'),
                        (('note:Rom.7.15', '1074–1080'), 'correzione')]:
        assert k.get(key, '').startswith(motivo), (key, k.get(key))


def test_correzioni():
    """Every row of eventi-correzioni.tsv decides one expression or more (eventi.py fails otherwise), and
    the ones that set an era are said so in era_da."""
    rows = EV.tabella_correzioni()
    E = dati()
    usate = Counter((e['sorgente'], e['data']) for e in E['eventi'] if e['era_da'].startswith('correzione'))
    scartate = Counter((x['sorgente'], x['data']) for x in E['non_datati'] if x['motivo'].startswith('correzione'))
    bad = [k for k, r in rows.items() if not (usate if r['decisione'] != 'scarta' else scartate)[(k[0], k[1])]]
    assert not bad, bad


def test_html():
    E = dati()
    bad = [e['id'] for e in E['eventi'] if not EV.bilanciato(e['html'] or '')]
    assert not bad, bad[:10]


TESTS = [test_regole, test_frasi, test_limiti, test_riferimenti_mai_anni, test_reali, test_cronologia, test_conteggi, test_ordine,
         test_periodi, test_non_datati, test_correzioni, test_html]


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
    n = len(SI) + len(NIENTE) + len(NO) + len(MAI) + len(LIMITI)
    print('%d tests (%d string cases, %d real dates): %s' % (len(TESTS), n, len(REALI),
                                                              'ok' if not failed else '%d failed' % failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
