"""Every dated event of the material on one time line -> ontologia/build/eventi.json.

usage: eventi.py [-q] [--rivedi file.tsv]

Stage 2f of the verse ontology (after integrazione.py and its test). Reads the build files of the
stages before (bibbia.json, collegamenti.json, dufour.json, paratesto.json, integrazione.json) and the
hand table eventi-correzioni.tsv, and writes one list of events in chronological order. The sources:
  cronologia   the 585 entries of the chronological table, all of them: the date of stage 2c, else
               the first date its text gives (the rules below), else the year printed in the margin of
               its row, else the dates of the other entries of its row, else the rows around it, else
               its period (each says which in 'data_da')
  dinastie     the persons of the dynasties chart with a date: a death (†) or the years of a reign
  datazione    the datings of cronologia-libri.tsv (composizione, ministero, evento): a book or a
               part of it written, a prophet active, dated by its chronology entry
  carta        the maps of the volume with a period (carte.tsv), as spans of centuries or millennia
  nota, introduzione, testo, dizionario
               the dates written in the 10,762 notes, the 21 introductions, the front-matter texts and
               the paragraphs of the Dizionario: one event per date expression, with its sentence
The rules that read a date in free text (README, "Stage 2f"): a number is a year only after a date cue
(nel, verso il, dal … al, tra il … e il, prima del, dopo il, negli anni, a month, a colon after «anno …», …)
or before an era suffix (a.C., d.C., della nostra èra), or in parentheses (three or four digits, or a span of
two after a title: «procuratore Cuspio Fado (44–46)»), or set off by commas («Cofra (Aprie), 589–570,»,
«battaglia di Gaza, 312,»); centuries (IV secolo, sec. VIII, XIII sec.) and millennia need their word, the turn
of the era its words («all’inizio della nostra èra»). The words before an expression may make it a bound
(«anteriore al 735», «a partire dal IV secolo»). The references of the sentence (parsed by stage 2,
2b, 2c: their spans are masked first) never become years; counts (40 anni), ordinals (15°), days of a
month (14 nisan), regnal years (anno 15 di Tiberio) and numbers glued to letters (2Re, 4Q) are refused.
The era: the suffix; else a row of eventi-correzioni.tsv; else the order of a span (descending = B.C.);
else the source (notes and introductions of the Old Testament: B.C.; of the New: A.D.; front matter:
A.D.; a paragraph of the Dizionario: its section VT (B.C.) or NT (A.D. up to 135, B.C. above), else the
testament of the references of its sentence or paragraph, else B.C. above 135). What the rules cannot
date confidently goes to 'non_datati' with the reason.

Checks (exit status 1 if any fails): every chronology entry is an event; every event has integer years,
start <= end, a precision and a source; the list is ordered; ids are unique; every row of the
correction table is used; every offset points at the expression as printed in its source; every HTML
is well nested. --rivedi writes a TSV of every date read in free text and every one refused, for the
review by hand.
"""
import csv
import html as H
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402
from estrai import dump  # noqa: E402

BUILD = os.path.join(C, 'ontologia', 'build')
OUT = os.path.join(BUILD, 'eventi.json')
CORREZIONI = os.path.join(HERE, 'eventi-correzioni.tsv')
FONTI = ('cronologia', 'dinastie', 'datazione', 'carta', 'nota', 'introduzione', 'testo', 'dizionario')
PRECISIONI = ('anno', 'intervallo', 'circa', 'secolo', 'millennio', 'riga', 'periodo')
FINE_TAVOLA = 135          # the last year of the chronological table (IX: 63 a.C. - 135 d.C.)

# ------------------------------------------------------------------ the rules on strings

AP = "[’']"
ROM = r'(?<![\w])(?-i:[IVX]{1,5})(?![\w’\'])'      # upper case only, also under re.I
ORDINALI = {'primo': 1, 'secondo': 2, 'terzo': 3, 'quarto': 4, 'quinto': 5, 'sesto': 6, 'settimo': 7,
            'ottavo': 8, 'nono': 9, 'decimo': 10}
ORD = r'(?:%s)' % '|'.join(ORDINALI)
# the era suffix, with the era it gives ('prima della nostra èra' before 'della nostra èra')
ERA_IN = (r'\s*(?:a\.\s?C\.?|d\.\s?C\.?|avanti Cristo|prima di Cristo|dopo Cristo|prima della nostra [eè]ra|'
          r'(?:della|dalla|nella) nostra [eè]ra|dell' + AP + r'[eè]ra cristiana)')
ERA = r'(?P<era>' + ERA_IN + r')?'
AC = re.compile(r'a\.\s?C|avanti|prima')
# the cues before a year. Strong: a year of two digits or more; weak: three digits or more (or a suffix)
CUE_FORTE = re.compile(
    r'(?:(?<![\w])(?:(?:già|proprio|solo|soltanto|ancora|poco|subito)\s+)?'
    r'(?P<cue>nel|nell' + AP + r'|verso il|verso l' + AP + r'|intorno al|intorno all' + AP + r'|attorno al|attorno all' + AP +
    r'|circa il|circa nel|prima del|prima dell' + AP + r'|dopo il|dopo l' + AP + r'|a partire dal|a partire dall' + AP +
    r'|sin dal|sin dall' + AP + r'|fin dal|fin dall' + AP + r'|sino dal|entro il|entro l' + AP +
    r'|†|cioè il|cioè nel|ossia il)'
    r'\s*(?P<anno>anno\s+)?'
    r'|(?<![\w])(?P<cue2>l' + AP + r'anno|dall' + AP + r'anno|all' + AP + r'anno|dell' + AP + r'anno)\s+'
    # "gli anni 80", "negli anni 61–63", "verso gli anni 45–50": a decade or a span of years
    r'|(?<![\w])(?P<cue3>(?:(?:verso|intorno|tra|fra)\s+)?(?:gli|negli|degli|agli|dagli)\s+anni)\s+)$', re.I)
# a colon or comma after "anno …" or "date …": "Nel quarto anno di Ioiakìm: 605", "anno centosettantaquattro:
# 139–138", "Le date di queste deportazioni sono quindi: 598, 587 e 582", "(quinto anno dell’esilio di
# Ioiachin, 593–592)"; three digits or more
ANNO_DUEPUNTI = re.compile(r'(?<![\w])(?:anno|date)\b[^.;:()«»\d§]{0,45}[:,]\s*$', re.I)
# a title or "anni" before a span of one or two digits in parentheses: "procuratore Cuspio Fado (44–46)",
# "regno di Claudio (41–54)", "due anni (52–54)", "sotto Nerone (64 o 67?)"
TITOLO = re.compile(r'(?:(?<![\w])(?:procuratore|imperatore|regno di|legato|prefetto|tetrarca|etnarca|proconsole|'
                    r'governatore|sotto)\s+(?:[A-ZÀ-Ü][\w’\']*\s+){1,3}|(?<![\w])anni\s+)$')
# the end of "N/M–K" or "N/M–K/L": "(305/4–281)", "(359/8–338/7)", "(455/454–403 ca.)"
SPAN_BARRA = re.compile(r'\s*[–-]\s*(\d{1,4})(?:/(\d{1,4}))?(?!\d|[.,]\d|[^\W\d_])')
CUE_DEBOLE = re.compile(r'(?<![\w])(?P<cue>dal|dall' + AP + r'|al|all' + AP + r'|del|dell' + AP + r'|fino al|fino all' + AP +
                        r'|sino al|sino all' + AP + r'|il|anno|cioè|ossia)\s*$', re.I)
# a single year in parentheses after "regno di …" ("regno di Erode (37)"); an event and its year set off by commas
# ("battaglia di Gaza, 312,", "morte di Pietro, 64 o 67,"); the words of a bound before an expression
REGNO_DI = re.compile(r'(?<![\w])regno di (?:[A-ZÀ-Ü][\w’\']*\s+){1,3}$')
EVENTO_VIRGOLA = re.compile(r'(?<![\w])(?:morte|battaglia|presa|caduta|distruzione|conquista|assedio)\s+'
                            r'd(?:i|el|ella|ei|egli|ell' + AP + r')\s*[A-ZÀ-Ü][\w’\']*(?:\s+\([^()]*\))?,\s*$')
LIMITE_PRIMA = re.compile(r'(?<![\w])(?P<neg>non\s+(?:\S+\s+){0,4})?(?P<w>anterior[ei]|posterior[ei]|prima|dopo|'
                          r'a partire|sin|fin|fino|sino)\s+$', re.I)
# the date of an origin, not a bound: "un manoscritto che data probabilmente dal II sec. a.C.", "possiamo risalire
# circa fino all’VIII secolo"
ORIGINE = re.compile(r'(?<![\w])(?:dat[aeio]\w*|risal\w*)\s+(?:\S+\s+){0,2}$', re.I)
MESI = ('gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio', 'agosto', 'settembre', 'ottobre',
        'novembre', 'dicembre', 'genn', 'febbr', 'febr', 'apr', 'magg', 'giu', 'lug', 'ag', 'sett', 'ott', 'nov', 'dic',
        'nisan', 'abib', 'iyyar', 'ziv', 'sivan', 'tammuz', 'ab', 'elul', 'tishri', 'tisri', 'etanim', 'marheshvan',
        'bul', 'kisleu', 'kislev', 'tebet', 'shebat', 'sebat', 'adar', 'primavera', 'estate', 'autunno', 'inverno')
MESE = re.compile(r'(?<![\w])(?:%s)\.?(?![\w])' % '|'.join(MESI), re.I)
MESE_DOPO = re.compile(r'\s*(?:di |del )?(?:%s)\.?(?![\w])' % '|'.join(MESI), re.I)
MESE_PRIMA = re.compile(r'(?<![\w])(?:%s|pasqua|pentecoste)\.?\s*$' % '|'.join(MESI), re.I)     # "giugno-luglio 587"
UNITA = re.compile(
    r'\s*(?:anni|anno|giorni|giorno|mesi|mese|settimane|settimana|ore|volte|uomini|donne|persone|abitanti|'
    r'soldati|carri|cavalli|città|generazioni|righe|stichi|versetti|capitoli|libri|salmi|cubiti|sicli|talenti|'
    r'stadi|miglia|km|chilometri|metri|m|cm|litri|denari|dramme|mine|libbre|chili|kg|ettari|famiglie|figli|'
    r'tribù|re|profeti|discepoli|lettere|parole|nomi|pecore|buoi|cammelli|pani|pesci|navi|morti|prigionieri|'
    r'deportati|esuli|giudei|ebrei|stele|tavolette|frammenti|manoscritti|codici|papiri|secoli|anni-luce|%)(?![\w])',
    re.I)
REGNO = re.compile(r'\s*[°º]?\s*(?:di|del|dello|della|dei|dell' + AP + r')\s+(?:regno|[A-ZÀ-Ü])')
NUMERO = re.compile(r'(?<![\w.,§/–-])(\d{1,4})(?!\d|[.,]\d|[^\W\d_])')
SEGUITO = re.compile(r'(?P<sep>\s*[–/-]\s*|\s+(?:o|oppure)\s+(?:il\s+|l' + AP + r'\s*)?)(?P<b>\d{1,4})(?!\d|[.,]\d|[^\W\d_])')
ALTERNATIVA = re.compile(r'\s*\((?:o|oppure)\s+(?P<alt>\d{1,4})\s*\??\)')     # "587 (o 586?) a.C."
DALAL = re.compile(r'(?<![\w])(?P<cue>dal|dall' + AP + r'|tra il|fra il|tra l' + AP + r'|fra l' + AP + r')\s*(?P<anno>anno\s+)?'
                   r'(?P<a>\d{1,4})(?!\d|[.,]\d|[^\W\d_])(?P<q1>\s*\(\?\))?(?P<era1>' + ERA_IN + r')?' +
                   r'\s+(?:al|all' + AP + r'|e il|e l' + AP + r')\s*(?P<b>\d{1,4})(?!\d|[.,]\d|[^\W\d_])', re.I)
CIRCA_DOPO = re.compile(r'\s*(?:ca\.|circa)(?![\w])')
INCERTO = re.compile(r'\s*(?:\(\?\)|\?)')
PARTE = (r'(?<![\w])(?P<parte>(?:(?:all|dall|verso l|sin dall|fin dall)' + AP + r'\s*)?inizio\s+del(?:l' + AP + r')?\s*|'
         r'(?:(?:alla|verso la|a|nella|della)\s+)?(?:(?:prima|seconda)\s+)?metà\s+del(?:l' + AP + r')?\s*|'
         r'(?:(?:alla|verso la|sulla|della)\s+)?fine\s+del(?:l' + AP + r')?\s*|nel corso del(?:l' + AP + r')?\s*)?')
SEC = r'(?:sec\.|secolo|secoli|sec(?=\s))'
SECOLO = re.compile(
    PARTE + r'(?:(?<![\w])(?P<cue>nel|nell' + AP + r'|nei|verso il|verso l' + AP + r'|dal|dall' + AP + r'|al|all' + AP +
    r'|del|dell' + AP + r'|tra il|fra il)\s*)?'
    r'(?:' + SEC + r'\s*(?P<r7>' + ROM + r')\s+(?:al|all' + AP + r')\s*' + SEC + r'\s*(?P<r8>' + ROM + r')'
    r'|' + SEC + r'\s*(?P<r1>' + ROM + r')(?:\s*(?:–|-|e)\s*(?P<r2>' + ROM + r'))?'
    r'|(?P<r3>' + ROM + r')(?:\s*(?:–|-)\s*(?P<r4>' + ROM + r'))?\s*' + SEC +
    r'|(?P<o1>' + ORD + r')\s+secolo'
    r'|(?P<r5>' + ROM + r')\s+(?:al|all' + AP + r'|e il|e l' + AP + r')\s*(?P<r6>' + ROM + r')\s*' + SEC + r')' + ERA, re.I)
# the turn of the era: "all’inizio (al principio) della nostra èra" is the start of the I century A.D., "alla
# vigilia della nostra èra" the end of the I century B.C. (not "il 753 come inizio della nostra èra")
NOSTRA_ERA = re.compile(r'(?<![\w])(?P<cue>(?:(?:all|dall|verso l)' + AP + r'\s*|(?:al|dal)\s+)(?:inizio|principio)|'
                        r'alla\s+vigilia)\s+della\s+nostra\s+[eè]ra', re.I)
MILLENNIO = re.compile(
    PARTE + r'(?:(?P<m1>' + ROM + r')(?:\s*(?:–|-)\s*(?P<m2>' + ROM + r'))?\s+millennio|(?P<o1>' + ORD + r')\s+millennio'
    r'|millennio\s+(?P<m3>' + ROM + r'))' + ERA, re.I)
DEBOLI = ('anno', 'cioè', 'ossia', 'dal', 'dall’', "dall'", 'al', 'all’', "all'", 'del', 'dell’', "dell'", 'il', 'fino al',
          'sino al')
ALTRA_ERA = re.compile(r'\s*(?:seleucidic\w*|dell' + AP + r'\s*[eè]ra seleucid\w*|di Roma|ab urbe condita)')
DEBOLI_NT = ('dal', 'dall’', "dall'", 'al', 'all’', "all'", 'del', 'dell’', "dell'", 'fino al', 'fino all’', 'sino al',
             'mese')      # "febbraio 44", "l’autunno 48", "nell’inverno 54–55": two digits after a month, NT only
MORBIDI = ('segnale debole', 'una cifra')    # refusals a row of eventi-correzioni.tsv may overrule
PARTI = {'inizio': (0, 25), 'prima metà': (0, 50), 'metà': (25, 75), 'seconda metà': (50, 100), 'fine': (75, 100)}
# the sentence ends of stage 2, not after an abbreviation of a date (a.C., ca., sec.); a dash ends a sentence
# only after a full stop (the lemmas of a note, "… 39 d.C. — Filippo: …"), not inside one ("tempio — dal 538
# al 520 — alla negligenza"); nor inside «a. C.»; nor after an initial («J. Ziegler», «F.M. Abel», «M.-É. Boismard», «F.Ch.
# Baur») or «per es.», «Ant. Giud.», «Ann.», «gr.»; after these a sentence ends only before a word that opens one («… nel 19 a.C. Ciò
# situa la scena», «… del II sec. I vizi …»), not before a name («nel 63 a.C. Pompeo», «All’inizio del II sec.
# a.C. Gesù Ben Sira»)
assert R.FRASE.pattern.endswith(r'|\s—\s')
APRE = (r'(?:(?:Il|Lo|La|Le|Gli|Un|Una|Uno|Ma|Però|Se|Si|Ciò|Questo|Questa|Questi|Queste|'
        r'Esso|Essa|Essi|Esse|In|A|Al|Alla|Nel|Nella|Nei|Dopo|Verso|Stando|Come|Inoltre|Tutti|Tutto|Tutte|È|Non|'
        r'Anche|Da|Dal|Dalla|Della|Del|Quando|Così|Per|Con|Su|Sul|Sulla|Allora|Infatti|Tuttavia|Poi|Qui|Più|Già|'
        r'Solo|Ora|Certo|Di|Mentre|Ecco|Sono|Era|Fu|Vi|Ne|Ogni)(?![\w’\'])|(?:L|Un|Quest|D|Dall|Nell|All)[’\'])')
FRASE = re.compile(r'(?<!a\.C)(?<!d\.C)(?<!a\. C)(?<!d\. C)(?<!\bca)(?<!\bsec)(?<!\bav)(?<!\bes)(?<!\bAnt)(?<!\bAnn)'
                   r'(?<!\bgr)(?<!\bGr)(?<!\bgiud)(?<!\bGiud)(?<!\.Ch)(?<![\s.(-][A-HJ-UWYZÀ-Ü])(?<![\s(]a)(?<![\s(]d)' +
                   R.FRASE.pattern[:-len(r'|\s—\s')] +
                   r'|(?:(?<=a\.C)|(?<=d\.C)|(?<=a\. C)|(?<=d\. C)|(?<=\bca)|(?<=\bsec)|(?<=[\s.(-][A-HJ-UWYZÀ-Ü]))\.\s+(?=' +
                   APRE + r')|(?:(?<=a\.C)|(?<=d\.C)|(?<=[IVX] sec))\.\s+(?=I\s+[a-zà-ù])|(?<=[.!?])\s—\s')
LIBRO_DOPO = re.compile(r'\s?(?:Sam|Samuele|Re|Cr|Cronache|Mac|Maccabei|Cor|Corinzi|Ts|Tessalonicesi|Tm|Timoteo|Pt|'
                        r'Pietro|Gv|Giovanni|Esd|Esdra|Enoc|Clemente|Baruc|Bar)(?![\w])')
TOKEN_RIF = re.compile(r'(?<![\w])(?:vv?|cc?|capp?\.|capitol[oi]|cap|versett[oi]|salm[oi]|nn?\.|pp?\.|nota|note|'
                       r'tav\.|fig\.|col\.|coll\.|righ[ea]|linea|ll?\.)\s*\d+(?:\s*[–-]\s*\d+)?', re.I)


def frase_inizio(text, at):
    # not finditer(text, 0, at): the end would hide the look-ahead of a sentence end right before 'at' (a
    # sentence that opens with its date, «… Ez 27,21). Nel 715, Sargon …»)
    s = 0
    for m in FRASE.finditer(text):
        if m.end() > at:
            break
        s = m.end()
    return s


def romano(s):
    v = {'I': 1, 'V': 5, 'X': 10}
    s = s.upper()
    if not s or any(c not in v for c in s):
        return None
    n = 0
    for i, c in enumerate(s):
        n += -v[c] if i + 1 < len(s) and v[s[i + 1]] > v[c] else v[c]
    # only well-formed numerals (IIII, VV, IIX are not)
    return n if 1 <= n <= 30 and _rom(n) == s else None


def _rom(n):
    out = ''
    for v, r in ((10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')):
        while n >= v:
            out += r
            n -= v
    return out


def era_suffisso(s):
    """'a.C.' or 'd.C.' from a printed suffix, None without one."""
    if not s or not s.strip():
        return None
    return 'a.C.' if AC.search(s) else 'd.C.'


def anno(n, era):
    return -n if era == 'a.C.' else n


def maschera(text, spans):
    """The text with the references (spans [offset, length]) and the tokens of a reference written in words
    (v 5, cap. 10, p. 123, nota 3) blanked out with '§': same length, so offsets stay."""
    t = list(text)
    for a, n in spans:
        for i in range(a, min(a + n, len(t))):
            t[i] = '§'
    for m in TOKEN_RIF.finditer(text):
        for i in range(m.start(), m.end()):
            t[i] = '§'
    return ''.join(t)


def espressioni(text, spans=(), tavola=False):
    """The date expressions of a text, read on the string alone (no era default): a list of dicts with
    raw, offset, kind (anno, intervallo, secolo, millennio), the numbers as printed (a, b), the era of a
    suffix (era, and era_b for the second year of "dal 4 a.C. al 39 d.C.") or None, circa, limite (ante,
    post), incerto, alternativa, parte (of a century), cue, forte, and 'scarto' (the reason) for a
    candidate refused. A candidate is a number after a cue or before a suffix, a span in parentheses, a
    century or a millennium; spans: the references [offset, length], masked first. tavola: a text of the
    chronological table, where a weak cue takes any number, a year may open the entry ("841 Salmanassar")
    or follow a name and a colon ("IRCANO (I): 134–104") and a span in parentheses may have one digit."""
    t = maschera(text, spans)
    out, preso = [], [False] * (len(t) + 1)

    def prendi(a, b):
        for i in range(a, b):
            preso[i] = True

    def libero(a, b):
        return not any(preso[a:b])

    # 1. millennia and centuries
    for m in MILLENNIO.finditer(t):
        g = m.groupdict()
        r1 = romano(g['m1'] or g['m3'] or '') if (g['m1'] or g['m3']) else ORDINALI.get((g['o1'] or '').lower())
        r2 = romano(g['m2']) if g['m2'] else None
        if not r1 or (g['m2'] and not r2):
            continue
        out.append(_espr(text, m, 'millennio', r1, r2 or r1, g))
        prendi(m.start(), m.end())
    for m in SECOLO.finditer(t):
        g = m.groupdict()
        if not libero(m.start(), m.end()):
            continue
        if g['o1']:
            r1, r2 = ORDINALI[g['o1'].lower()], None
        else:
            x1, x2 = g['r7'] or g['r1'] or g['r3'] or g['r5'], g['r8'] or g['r2'] or g['r4'] or g['r6']
            r1, r2 = romano(x1), romano(x2) if x2 else None
            if not r1 or (x2 and not r2):
                continue
        out.append(_espr(text, m, 'secolo', r1, r2 or r1, g))
        out[-1]['incerto'] = bool(INCERTO.match(t, m.end()))           # "(fine del I sec.?)"
        prendi(m.start(), m.end())
    for m in NOSTRA_ERA.finditer(t):
        if not libero(m.start(), m.end()):
            continue
        cue = ' '.join(m.group('cue').lower().split())
        vigilia = 'vigilia' in cue
        out.append(dict(raw=text[m.start():m.end()], offset=m.start(), kind='secolo', a=1, b=1,
                        era='a.C.' if vigilia else 'd.C.', circa=True, limite='post' if cue.startswith('dal') else None,
                        incerto=False, cue='nostra èra', forte=True, parte='fine' if vigilia else 'inizio'))
        prendi(m.start(), m.end())
    # 2. "dal N al M", "tra il N e il M"
    for m in DALAL.finditer(t):
        if not libero(m.start(), m.end()):
            continue
        a, b = int(m.group('a')), int(m.group('b'))
        fine = m.end()
        alt = None
        o = re.match(r'\s+(?:o|oppure)\s+(\d{1,4})(?!\d|[.,]\d|[^\W\d_])', t[fine:])
        if o and (int(o.group(1)) > b if a < b else int(o.group(1)) < b):
            alt, b = b, int(o.group(1))                                 # "dal 52 al 59 o 60": 52–60, or 59
            fine += o.end()
        c1 = CIRCA_DOPO.match(t, fine)                                  # "dal 1720 al 1552 ca."
        if c1:
            fine = c1.end()
        e = re.match(ERA, t[fine:])
        era2 = e.group('era') if e and e.group('era') else None
        fine += e.end() if era2 else 0
        c2 = None if c1 else CIRCA_DOPO.match(t, fine)
        if c2:
            fine = c2.end()
        e1, e2 = era_suffisso(m.group('era1')), era_suffisso(era2)
        x = dict(raw=text[m.start():fine], offset=m.start(), kind='intervallo', a=a, b=b, era=e1 or e2,
                 circa=bool(c1 or c2), limite=None, incerto=False, cue=m.group('cue').lower(), forte=True)
        if alt:
            x['alternativa'] = alt
        if e1 and e2 and e1 != e2:
            x['era_b'] = e2                                             # "dal 4 a.C. al 39 d.C." 
        dopo = t[fine:fine + 30]
        if INCERTO.match(dopo) or m.group('q1'):
            x['incerto'] = True
        if x['era'] is None and min(a, b) < 100 and not m.group('cue').lower().startswith(('tra', 'fra')):
            x['forte'] = False                                          # "dal 15 al 21": two digits need a suffix
        _scarti_numero(t, m.start('a'), m.end('b') + (o.end() if alt else 0), x, text, 1 if tavola else 100)
        out.append(x)
        prendi(m.start(), fine)
    # 3. single years, spans and lists
    prec = None
    for m in NUMERO.finditer(t):
        if not libero(m.start(), m.end()):
            continue
        a = int(m.group(1))
        prima, dopo = t[max(0, m.start() - 40):m.start()], t[m.end():m.end() + 60]
        cf, cd = CUE_FORTE.search(prima), CUE_DEBOLE.search(prima)
        par = re.search(r'\(\s*$', prima)
        x = dict(raw=None, offset=m.start(), kind='anno', a=a, b=a, era=None, circa=False, limite=None,
                 incerto=False, cue=None, forte=False)
        fine = m.end()
        s = SEGUITO.match(t, fine)
        # the second year has no more digits than the first ("589/8", "143-37"), or more in an ascending span
        # ("64–135 d.C.")
        if s and (len(s.group('b')) <= len(m.group(1)) or int(s.group('b')) > a and '/' not in s.group('sep')):
            b = int(s.group('b'))
            if len(s.group('b')) < len(m.group(1)) and '/' in s.group('sep'):     # 589/8 = 589-588
                b = int(m.group(1)[:len(m.group(1)) - len(s.group('b'))] + s.group('b'))
            if b != a:
                x.update(kind='intervallo', b=b, alternativa=b if s.group('sep').strip() in ('o', 'oppure') else None)
                fine = s.end()
            sb = SPAN_BARRA.match(t, fine) if '/' in s.group('sep') else None
            if sb:                                                       # "305/4–281", "359/8–338/7"
                k, l2 = sb.group(1), sb.group(2)
                b = int(k[:len(k) - len(l2)] + l2 if l2 and len(l2) < len(k) else (l2 or k))
                x.update(kind='intervallo', b=b, alternativa=None)
                fine = sb.end()
            sk = re.match(r'/(\d{1,4})(?!\d|[.,]\d|[^\W\d_])', t[fine:]) if x['kind'] == 'intervallo' and \
                '/' not in s.group('sep') else None
            if sk:                                                       # "(404–359/358)": 404–358
                k, l2 = s.group('b'), sk.group(1)
                x['b'] = int(k[:len(k) - len(l2)] + l2 if len(l2) < len(k) else l2)
                fine += sk.end()
        al = ALTERNATIVA.match(t, fine)
        if al:
            x['alternativa'] = int(al.group('alt'))
            fine = al.end()
        ca = CIRCA_DOPO.match(t, fine)
        if ca:
            x['circa'] = True
            fine = ca.end()
        e = re.match(ERA, t[fine:])
        if e and e.group('era'):
            x['era'] = era_suffisso(e.group('era'))
            fine += e.end()
            m2 = re.match(r'\s*[–-]\s*(\d{1,4})(?!\d|[.,]\d)' + ERA, t[fine:])
            if x['kind'] == 'anno' and m2 and m2.group('era') and era_suffisso(m2.group('era')) != x['era']:
                x.update(kind='intervallo', b=int(m2.group(1)), era_b=era_suffisso(m2.group('era')))
                fine += m2.end()                                        # "(20 a.C. – 54 d.C.)"
        q = INCERTO.match(t, fine)
        if q:
            x['incerto'] = True
            fine = q.end()
        lista = re.search(r'(?:\s*,\s*|\s+e\s+|\s+o\s+|\s*;\s*)$', prima)
        if lista and ';' in lista.group(0) and not (len(m.group(1)) == 4 and prec and len(str(prec['a'])) == 4):
            lista = None                                                # "(1971; 1974)": only years of four digits
        if cf:
            cue = (cf.group('cue') or cf.group('cue2') or cf.group('cue3') or '').lower()
            x.update(cue=' '.join(cue.split()) + (' anno' if cf.group('anno') else ''), forte=True)
            inizio = m.start() - len(cf.group(0))
            if cf.group('cue3') and x['kind'] == 'anno' and a % 10 == 0 and a < 100:
                x.update(kind='intervallo', b=a + 9, decennio=True)     # "gli anni 80": 80–89
        elif cd:
            x.update(cue=cd.group('cue').lower())
            inizio = m.start() - len(cd.group(0))
            if re.search(r'(?<![\w])(?:%s)\.?\s*$' % '|'.join(MESI), prima[:len(prima) - len(cd.group(0))], re.I):
                x.update(forte=True, dopo_mese=True)                    # "16 marzo del 597"
        elif MESE_PRIMA.search(prima) and (len(m.group(1)) >= 2 or tavola):
            # "giugno-luglio 587", "Pentecoste 163"; two digits ("febbraio 44") are a weak cue, read in the NT only
            x.update(cue='mese', forte=len(m.group(1)) >= 3 or tavola, dopo_mese=True)
            inizio = m.start()
        elif par and (len(m.group(1)) >= 3 or x['era'] or (tavola and x['kind'] == 'intervallo') or
                      (x['kind'] == 'intervallo' and TITOLO.search(prima[:par.start()])) or
                      (len(m.group(1)) >= 2 and REGNO_DI.search(prima[:par.start()]))) and \
                (re.match(r'\s*[);,]', t[fine:]) or len(m.group(1)) == 4 and re.match(r'\s+e\s+\d{4}(?!\d)', t[fine:]) or
                 x['kind'] == 'intervallo' and x['a'] > x['b'] and len(m.group(1)) >= 3 and
                 re.match(r'\s+e\s+\d{3,4}\s*[–-]', t[fine:])):
            # "(736–716)", "Acazia (841)", "(598; cf. …", "(1955 e 1973)", "procuratore Cuspio Fado (44–46)",
            # "regno di Erode (37)", "Demetrio II (145–140 e 129–125)"
            x.update(cue='(', forte=True)
            inizio = m.start()
            if prima[:par.start()].rstrip().endswith('§') and not x['era']:
                x['scarto'] = 'numero tra parentesi dopo un riferimento'   # "di 12,11 (1290)": a number of the verse
        elif len(m.group(1)) >= 3 and ANNO_DUEPUNTI.search(t[max(0, m.start() - 80):m.start()]):
            x.update(cue='anno:', forte=True)                           # "Nel quarto anno di Ioiakìm: 605"
            inizio = m.start()
        elif x['kind'] == 'intervallo' and len(m.group(1)) >= 3 and x['b'] >= 100 and x['a'] > x['b'] and \
                re.search(r'[\w)],\s*$', prima) and re.match(r'\s*[,)]', t[fine:]):
            x.update(cue='apposizione', forte=True)                     # "Cofra (Aprie), 589–570, presso cui"
            inizio = m.start()
        elif len(m.group(1)) >= 2 and EVENTO_VIRGOLA.search(prima) and re.match(r'\s*[,;.)]', t[fine:]):
            x.update(cue='apposizione', forte=True)                     # "battaglia di Gaza, 312,", "morte di Pietro, 64 o 67,"
            inizio = m.start()
        elif tavola and (re.search(r'^\s*$', prima) and m.start() == 0 and re.match(r'\s+[A-ZÀ-Ü]', t[fine:]) and
                         len(m.group(1)) >= 3 or re.search(r'[\w)]:\s*$', prima) and (x['kind'] == 'intervallo' or
                                                                              re.match(r'\s*\)', t[fine:]))):
            x.update(cue='voce', forte=True)                            # "841 Salmanassar…", "IRCANO (I): 134–104"
            inizio = m.start()
        elif tavola and par and par.start() == 0 and len(m.group(1)) >= 3 and re.match(r'\s*:', t[fine:]):
            x.update(cue='voce', forte=True, incerto=True)              # "(458: missione di Esdra, se …)": a hypothesis
            inizio = m.start()
        elif x['era'] or (x['circa'] and len(m.group(1)) >= 2):
            x.update(cue='suffisso' if x['era'] else 'ca.', forte=True)
            inizio = m.start()
        elif prec is not None and lista and prec['fine'] == m.start() - len(lista.group(0)) and \
                not prec.get('scarto') and (len(m.group(1)) >= 3 or prec['cue'].endswith('anni')):
            x.update(cue='elenco', forte=True, elenco=prec['offset'])   # "nel 597, 587, 582", "gli anni 50–52 e 53–58"
            if prec['cue'].endswith('anni'):
                x['cue'] = prec['cue']
            inizio = m.start()
        else:
            continue
        if a <= 4 and LIBRO_DOPO.match(t, m.end()):
            continue                                                    # "nel 1 Sam", "il 4 Esdra"
        if x['cue'] in ('il',) and not x['era'] and not x['forte']:
            e2 = re.match(r'\s+e\s+il\s+\d{1,4}(?P<era>' + ERA_IN + ')', t[fine:])
            if not e2:
                continue                                                # "il 14": only with a suffix or a month
            x.update(era=era_suffisso(e2.group('era')), era_elenco=True, forte=True)  # "il 30 e il 33 d.C."
        x['raw'] = text[inizio:fine].strip()
        x['offset'] = inizio + (len(text[inizio:fine]) - len(text[inizio:fine].lstrip()))
        _cue_limite(x)
        _scarti_numero(t, m.start(), fine, x, text, 1 if tavola else 100)
        x['fine'] = fine
        out.append(x)
        prendi(inizio, fine)
        prec = x
    # a suffix at the end of a list applies to the years before it ("nel 597, 587, 582 a.C.")
    for x in reversed(out):
        if x.get('elenco') is not None and x['era']:
            for y in out:
                if y['offset'] == x['elenco'] and not y['era']:
                    y['era'], y['era_elenco'] = x['era'], True
    for x in out:
        x.pop('fine', None)
        _limite_contesto(t, x)
    out.sort(key=lambda x: x['offset'])
    return out


def _limite_contesto(t, x):
    """A bound said by the words before the expression: «anteriore al 735», «posteriore al 70», «fino al sec. II»,
    «a partire dal IV secolo», «Dalla fine del II sec.», «dal sec. VIII»; «non … anteriore agli anni 80» is the
    other bound. Not a span «dal N al M», nor the date of an origin («che data dal II sec. a.C.», ORIGINE)."""
    if x['limite'] or x['kind'] == 'intervallo' and x['cue'] in ('dal', 'dall’', "dall'", 'tra il', 'fra il', 'tra l’',
                                                                  'fra l’', "tra l'", "fra l'"):
        return
    r = x['raw'].lower()
    pre = t[max(0, x['offset'] - 50):x['offset']]
    m = LIMITE_PRIMA.search(pre)
    if ORIGINE.search(pre[:m.start('w')] if m else pre):
        return
    a_ = r.startswith(('al ', 'all’', "all'", 'agli ', 'alla ', 'del ', 'dell’', "dell'", 'della ', 'dei '))
    da = r.startswith(('dal ', 'dall’', "dall'", 'dalla ', 'dai ', 'dagli '))
    lim = None
    if m:
        w = m.group('w').lower()
        if w.startswith(('anterior', 'prima')) and a_:
            lim = 'ante'
        elif w.startswith(('posterior', 'dopo')) and a_:
            lim = 'post'
        elif w in ('fino', 'sino') and (a_ or da):
            lim = 'ante' if a_ else 'post'
        elif w in ('a partire', 'sin', 'fin') and da:
            lim = 'post'
        if lim and m.group('neg'):
            lim = 'post' if lim == 'ante' else 'ante'                   # "non potrebbe essere anteriore agli anni 80"
    elif x['kind'] in ('secolo', 'millennio') and x['a'] == x['b'] and \
            (da or re.search(r'(?<![\w])(?:dalla|dall[’\'])\s*$', pre, re.I)):
        lim = 'post'                                                    # "Dal IV secolo d.C.", "Dalla fine del II sec."
    if lim:
        x['limite'] = lim


def _espr(text, m, kind, r1, r2, g):
    parte = (g.get('parte') or '').strip().lower()
    p = None
    for k in ('prima metà', 'seconda metà', 'metà', 'inizio', 'fine'):
        if k in parte:
            p = k
            break
    cue = (g.get('cue') or '').lower()
    x = dict(raw=m.group(0).strip(), offset=m.start() + len(m.group(0)) - len(m.group(0).lstrip()), kind=kind,
             a=r1, b=r2, era=era_suffisso(g.get('era')), circa=cue.startswith('verso') or 'verso' in parte,
             limite=None, incerto=False, cue=cue or kind, forte=True, parte=p)
    return x


def _cue_limite(x):
    c = x['cue'] or ''
    if c.startswith(('verso', 'intorno', 'attorno', 'circa')):
        x['circa'] = True
    if c.startswith(('prima', 'entro', 'fino', 'sino al')):
        x['limite'] = 'ante'
    elif c.startswith(('dopo', 'a partire', 'sin', 'fin', 'sino dal')) or c in ('dal', 'dall’', "dall'", 'dall’anno', "dall'anno"):
        x['limite'] = 'post'


def _scarti_numero(t, a, fine, x, text, minimo=100):
    """The reasons a number after a cue is not a year."""
    dopo = t[fine:fine + 40]
    n = min(x['a'], x['b']) if x['kind'] == 'intervallo' else x['a']
    if re.match(r'\s*[+×=]\s*\d', t[fine:]):
        x['scarto'] = 'calcolo'
    elif re.match(r'\s*[°ºª]', t[fine:]) or re.match(r'\s*[°ºª]', t[a + len(str(x['a'])):]):
        x['scarto'] = 'ordinale'
    elif UNITA.match(dopo) and not x['era']:
        x['scarto'] = 'conteggio («%s»)' % UNITA.match(dopo).group(0).strip()
    elif MESE_DOPO.match(dopo) and n <= 31:
        x['scarto'] = 'giorno del mese'
    elif (x['cue'] or '').endswith('anno') and REGNO.match(dopo) and not x['era']:
        x['scarto'] = 'anno di regno'
    elif ALTRA_ERA.match(dopo):
        x['scarto'] = 'anno di un’altra era («%s»)' % ALTRA_ERA.match(dopo).group(0).strip()
    elif x['era'] is None and n < 10 and x['cue'] not in ('(',) and not x['cue'].endswith('anni') and minimo > 1:
        x['scarto'] = 'una cifra senza era'
    elif not x['forte'] and x['era'] is None and n < minimo:
        x['scarto'] = 'segnale debole («%s») e meno di tre cifre' % x['cue']
    else:
        # a day of a month named in the same sentence ("il 14 del mese; ... dal 15 al 21")
        s = frase_inizio(text, a)
        e = FRASE.search(text, a)
        frase = text[s:e.start() if e else len(text)]
        if n <= 31 and x['era'] is None and not x.get('dopo_mese') and x['cue'] in DEBOLI and \
                re.search(r'(?<![\w])mes[ei](?![\w])|' + MESE.pattern, frase, re.I):
            x['scarto'] = 'giorno del mese'


# ------------------------------------------------------------------ the era and the years


def data(x, ctx, corr=None):
    """(start, end, era, era_da) of an expression of espressioni(), or (None, reason). ctx, the default
    era of the source: 'AT' (B.C.), 'NT' (A.D.), 'NTd' (a section NT of the Dizionario: A.D. up to 135,
    B.C. above), 'moderno' (the front matter: A.D.), 'aC'/'dC' (the chronological table, by its turn),
    None (no testament known: B.C. above 135, else refused); corr: the decision of a row of
    eventi-correzioni.tsv (a.C., d.C., scarta)."""
    if corr == 'scarta':
        return None, 'correzione: scartato'
    if x.get('scarto') and not (corr in ('a.C.', 'd.C.') and x['scarto'].startswith(MORBIDI)) and \
            not (ctx in ('NT', 'NTd') and x['scarto'].startswith('segnale debole') and min(x['a'], x['b']) >= 10 and
                 x['cue'] in DEBOLI_NT):
        return None, x['scarto']
    if x.get('era_b'):
        s, e = anno(x['a'], x['era']), anno(x['b'], x['era_b'])
        return ((s, e, 'a.C.–d.C.', 'suffisso'), None) if s <= e else (None, 'intervallo non ordinato')
    era, da = x['era'], 'suffisso' if x['era'] else None
    if x.get('era_elenco'):
        da = 'suffisso dell’elenco'
    a, b = x['a'], x['b']
    if corr:
        era, da = corr, 'correzione'
    if era is None and x['kind'] in ('anno', 'intervallo') and a != b and not x.get('alternativa') and \
            not x.get('decennio'):
        era, da = ('a.C.' if a > b else 'd.C.'), 'ordine'
        if ctx == 'AT' and era == 'd.C.':
            return None, 'intervallo crescente in un testo dell’AT'
    if era is None and x['kind'] in ('secolo', 'millennio') and a != b:
        era, da = ('a.C.' if a > b else 'd.C.'), 'ordine'
    if era is None:
        if ctx in ('aC', 'dC'):
            era, da = ('a.C.' if ctx == 'aC' else 'd.C.'), 'tavola'
        elif ctx == 'moderno':
            era, da = 'd.C.', 'fonte moderna'
            if x['kind'] == 'millennio':
                return None, 'millennio in un testo moderno'
        elif ctx == 'AT':
            era, da = 'a.C.', 'fonte AT'
            if x['kind'] == 'anno' and max(a, b) >= 1500:
                return None, 'anno di quattro cifre ≥ 1500 senza era in un testo dell’AT'
            if x['kind'] == 'secolo' and max(a, b) >= 15:
                return None, 'secolo ≥ XV senza era in un testo dell’AT'
        elif ctx == 'NT':
            # the notes and introductions of the NT: their years without suffix are of the Christian era
            # (Paul, the war of 66-70, the Fathers, the canon, the manuscripts); the B.C. ones are suffixed
            era, da = ('d.C.', 'fonte NT') if x['kind'] != 'millennio' else ('a.C.', 'fonte NT (millennio)')
        elif ctx == 'NTd':
            # a section NT of the Dizionario: A.D. up to 135, B.C. above (it names no later events)
            if x['kind'] in ('anno', 'intervallo'):
                era, da = ('d.C.', 'sezione NT, ≤ 135') if max(a, b) <= FINE_TAVOLA else ('a.C.', 'sezione NT, > 135')
                if max(a, b) >= 1500:
                    return None, 'anno di quattro cifre ≥ 1500 senza era nel Dizionario'
            elif x['kind'] == 'secolo':
                era, da = 'd.C.', 'sezione NT'
            else:
                era, da = 'a.C.', 'sezione NT (millennio)'
        else:
            if x['kind'] in ('anno', 'intervallo') and min(a, b) > FINE_TAVOLA and max(a, b) < 1500:
                era, da = 'a.C.', 'grandezza (> 135)'
            else:
                return None, 'era incerta (nessun suffisso, testamento non determinato)'
    if x.get('scarto'):
        da += '; due cifre dopo «%s» in un testo del NT' % x['cue'] if not corr else ''
    s, e = estremi(x['kind'], a, b, era, x.get('parte'))
    if s > e:
        return None, 'intervallo non ordinato per l’era %s' % era
    return (s, e, era, da), None


def leggi(text, ctx, spans=(), tavola=False):
    """The rules on one string, for the tests and the review: [(raw, start, end, precision, era_da)] for
    each expression dated, [(raw, None, reason)] for each one refused."""
    out = []
    for x in espressioni(text, spans, tavola):
        d, motivo = data(x, ctx)
        out.append((x['raw'], d[0], d[1], precisione(x), d[3]) if d else (x['raw'], None, motivo))
    return out


def estremi(kind, a, b, era, parte=None):
    """First and last year of an expression (negative = B.C.)."""
    if kind == 'secolo' or kind == 'millennio':
        u = 100 if kind == 'secolo' else 1000
        lo, hi = (max(a, b), min(a, b)) if era == 'a.C.' else (min(a, b), max(a, b))
        if era == 'a.C.':
            s, e = -lo * u, -((hi - 1) * u + 1)
        else:
            s, e = (lo - 1) * u + 1, hi * u
        if parte and lo == hi:
            p0, p1 = PARTI[parte]
            k = u // 100
            s, e = s + p0 * k, s + p1 * k - 1
        return s, e
    if era == 'a.C.':
        return -max(a, b) if a != b else -a, -min(a, b) if a != b else -a
    return min(a, b), max(a, b)


def precisione(x):
    if x['kind'] in ('secolo', 'millennio'):
        return x['kind']
    if x['circa']:
        return 'circa'
    return 'intervallo' if x['a'] != x['b'] else 'anno'


# ------------------------------------------------------------------ helpers


def runs(ix):
    """Sorted runs of consecutive verse indices, flattened: [a, b, a, b, ...] (as esploratore.py)."""
    ix = sorted(set(ix))
    out = []
    for i in ix:
        if out and out[-1] == i - 1:
            out[-1] = i
        else:
            out += [i, i]
    return out


def taglia_html(h, a, b):
    """h[a:b] with the tags open at a reopened and the ones left open closed."""
    pila = []
    for m in re.finditer(r'<(/?)([a-z]+)[^>]*>', h[:a]):
        if m.group(2) == 'br':
            continue
        if m.group(1):
            if pila and pila[-1][0] == m.group(2):
                pila.pop()
        else:
            pila.append((m.group(2), m.group(0)))
    pezzo = h[a:b]
    aperti = list(pila)
    for m in re.finditer(r'<(/?)([a-z]+)[^>]*>', pezzo):
        if m.group(2) == 'br':
            continue
        if m.group(1):
            if aperti and aperti[-1][0] == m.group(2):
                aperti.pop()
        else:
            aperti.append((m.group(2), m.group(0)))
    # a tag cut in the middle at either end
    pezzo = re.sub(r'^[^<]*?>', '', pezzo) if re.match(r'^[^<]*>', pezzo) and '<' not in pezzo[:pezzo.find('>')] else pezzo
    pezzo = re.sub(r'<[^>]*$', '', pezzo)
    return ''.join(x[1] for x in pila) + pezzo + ''.join('</%s>' % x[0] for x in reversed(aperti))


def etichetta(s, lim=150):
    s = ' '.join(s.split())
    if len(s) <= lim:
        return s
    k = s.rfind(' ', 0, lim)
    return s[:k if k > 60 else lim].rstrip(' ,;:') + '…'


def finestra(frase, a, b, lim=170):
    """A label: the sentence, or a window of it around [a, b) cut at words."""
    f = ' '.join(frase.split())
    if len(frase) <= lim:
        return f
    s = max(0, a - (lim - (b - a)) // 2)
    e = min(len(frase), s + lim)
    s = max(0, e - lim)
    if s:
        k = frase.find(' ', s)
        s = k + 1 if 0 <= k < a else s
    if e < len(frase):
        k = frase.rfind(' ', b, e)
        e = k if k > b else e
    return ('…' if s else '') + ' '.join(frase[s:e].split()).strip(' ,;:') + ('…' if e < len(frase) else '')


def tabella_correzioni():
    """The rows of eventi-correzioni.tsv: (source, expression as printed, occurrence or 0) -> row."""
    rows = {}
    with open(CORREZIONI, encoding='utf-8') as f:
        lines = [x.rstrip('\n') for x in f if x.strip() and not x.startswith('#')]
    for k, r in enumerate(csv.DictReader(lines, delimiter='\t', quoting=csv.QUOTE_NONE), 1):
        r = {a: (b or '').strip() for a, b in r.items()}
        r['riga'] = k
        rows[(r['fonte'], r['espressione'], int(r['n'] or 0))] = r
    return rows


# ------------------------------------------------------------------ the periods


def periodi(P):
    """The 9 periods of the chronological table with the span used to give a date its period: from the
    start of the period (the years of its title, else the year in the margin of its first row) to the
    year before the start of the next; IX ends at 135 d.C."""
    sez, voci = P['cronologia']['sections'], P['cronologia']['voci']
    inizi = []
    for s in sez:
        m = re.search(r'\((\d+)(?:\s*a\.C\.)?\s*[–-]', s['title'])
        if m:
            inizi.append(-int(m.group(1)))
        else:
            prima = next(v for v in voci if v['section'] == s['n'] and v['margin'])
            inizi.append(-int(re.match(r'\d+', prima['margin']).group(0)))
    out = []
    for k, s in enumerate(sez):
        fine = inizi[k + 1] - 1 if k + 1 < len(sez) else FINE_TAVOLA
        out.append(dict(n=s['n'], romano=s['roman'], titolo=s['title'], inizio=inizi[k], fine=fine))
    return out


def periodo_di(y, per):
    """The period of a year: the last one starting at or before it; None before the first or after 135 d.C."""
    if y > FINE_TAVOLA or y < per[0]['inizio']:
        return None
    k = None
    for p in per:
        if p['inizio'] <= y:
            k = p['n']
    return k


# ------------------------------------------------------------------ the sources


class Raccolta:
    def __init__(self, data, P, I, vix, per, corr):
        self.data, self.P, self.I, self.vix, self.per, self.corr = data, P, I, vix, per, corr
        self.eventi, self.non_datati, self.usate = [], [], Counter()
        self.errors = []
        self.testamento = {b['osis']: b['testament'] for b in data['books']}

    def runs_link(self, links):
        return runs(self.vix[t] for l in links for t in l.get('targets', []) if t in self.vix)

    def aggiungi(self, ev):
        ev.setdefault('periodo', periodo_di(ev['inizio'], self.per))
        self.eventi.append(ev)

    # --- free text

    def testo(self, fonte, sorgente, text, html, links, ctx, rank, apri, verso=None, ctx_rif=None):
        """The events of one text (a note, a paragraph): one per date expression accepted."""
        spans = [(l['offset'], l['length'] if 'length' in l else len(l['raw'])) for l in links if l.get('offset') is not None]
        hmap = R.html_offsets(text, html) if html else None
        visti = Counter()
        for x in espressioni(text, spans):
            visti[x['raw']] += 1
            key = (sorgente, x['raw'], visti[x['raw']])
            row = self.corr.get(key) or self.corr.get((sorgente, x['raw'], 0))
            dec = None
            if row:
                self.usate[(row['fonte'], row['espressione'], int(row['n'] or 0))] += 1
                dec = row['decisione']
            if x['cue'] == '(' and not x['era'] and max(x['a'], x['b']) <= 150 and \
                    (sorgente.startswith('note:Ps.') or sorgente.startswith('intro-salmi.')):
                x['scarto'] = 'numero di salmo tra parentesi'               # "un inno regale (144)"
            c = ctx
            s0 = frase_inizio(text, x['offset'])
            # from the last character of a date that ends with a full stop («… nel XIII sec. a.C. A Meneijeh …»)
            e0 = FRASE.search(text, x['offset'] + len(x['raw']) - x['raw'].endswith('.'))
            e0 = e0.start() + 1 if e0 and text[e0.start()] in '.!?' else (e0.start() if e0 else len(text))
            frase = text[s0:e0].strip()
            nella = [l for l in links if l.get('offset') is not None and s0 <= l['offset'] < e0]
            if c is None and ctx_rif:
                c = ctx_rif(nella)
            d, motivo = data(x, c, dec)
            base = dict(fonte=fonte, sorgente=sorgente, apri=apri, data=x['raw'], offset=x['offset'])
            if d is None:
                if row and dec == 'scarta':
                    motivo = 'correzione: %s' % row['motivo']
                self.non_datati.append(dict(base, motivo=motivo, frase=finestra(frase, x['offset'] - s0,
                                                                              x['offset'] - s0 + len(x['raw']))))
                continue
            s, e, era, da = d
            if row and dec != 'scarta':
                da = 'correzione: %s' % row['motivo']
            h = None
            if hmap:
                a0 = s0 + (len(text[s0:e0]) - len(text[s0:e0].lstrip()))
                h = taglia_html(html, hmap[a0], hmap[e0])
            ev = dict(id='ev:%s@%d' % (sorgente, x['offset']), fonte=fonte, sorgente=sorgente, apri=apri,
                      data=x['raw'], offset=x['offset'], inizio=s, fine=e, precisione=precisione(x),
                      circa=x['circa'], limite=x['limite'], incerto=x['incerto'], era=era, era_da=da,
                      etichetta=finestra(frase, x['offset'] - s0, x['offset'] - s0 + len(x['raw'])),
                      frase=frase, html=h or H.escape(frase, quote=False), verso=verso,
                      versetti=self.runs_link(nella),
                      riferimenti=[[l['raw'], l['id']] for l in nella], rango=rank + (x['offset'],))
            if x.get('alternativa'):
                ev['alternativa'] = anno(x['alternativa'], era)      # signed as the years: «del 587 (o 586?) a.C.» -586
            if x.get('parte'):
                ev['parte'] = x['parte']
            self.aggiungi(ev)

    # --- the chronological table

    def cronologia(self):
        C_ = self.P['cronologia']
        voci, turn = C_['voci'], C_['turn']
        cit = defaultdict(list)
        for l in self.P['links']:
            if l['kind'] == 'chrono-cites':
                cit[int(l['source'].split('.')[1])].append(l)
        righe = defaultdict(list)
        for v in voci:
            righe[(v['section'], v['row'])].append(v)
        ordine = list(righe)
        # first the date of each entry by itself (stage 2c, else its text)
        proprie = {}
        for v in voci:
            ctx = 'aC' if v['section'] < 9 or v['row'] < turn else 'dC'
            if v['start'] is not None:
                k = 'circa' if v['circa'] else ('intervallo' if v['start'] != v['end'] else 'anno')
                off = v['text'].find(v['date']) if v['date'] else -1
                proprie[v['n']] = dict(inizio=v['start'], fine=v['end'], precisione=k, circa=v['circa'],
                                       data=v['date'], offset=off if off >= 0 else None, data_da='tavola',
                                       era='a.C.' if v['start'] < 0 else 'd.C.', era_da='tavola (stage 2c)')
                continue
            spans = [(l['offset'], l['length']) for l in cit[v['n']]]
            for x in espressioni(v['text'], spans, tavola=True):
                if x['limite'] and not x.get('scarto'):
                    x['scarto'] = 'un limite («%s»), non la data della voce' % x['cue']
                elif re.search(r'(?<![\w])nat[oa]\s*$', v['text'][:x['offset']]) and not x.get('scarto'):
                    x['scarto'] = 'una nascita («nato»), non la data della voce'   # "TIRAKA, … nato verso il 710"
                d, motivo = data(x, ctx)
                if d is None:
                    self.non_datati.append(dict(fonte='cronologia', sorgente='cronologia.%d' % v['n'],
                                                apri=hash_cron(v), data=x['raw'], offset=x['offset'],
                                                motivo=motivo + ' (la voce resta nella linea, datata altrimenti)',
                                                frase=etichetta(v['text'])))
                    continue
                proprie[v['n']] = dict(inizio=d[0], fine=d[1], precisione=precisione(x), circa=x['circa'],
                                       limite=x['limite'], incerto=x['incerto'], data=x['raw'], offset=x['offset'],
                                       data_da='testo', era=d[2], era_da=d[3])
                break
        # then the row: the year in its margin, the dates of its entries, the rows around it, the period
        anni_riga = {}
        for k, r in enumerate(ordine):
            mg = next((v['margin'] for v in righe[r] if v['margin']), None)
            if mg:
                ys = [-int(y) for y in re.findall(r'\d+', mg)]
                anni_riga[r] = (min(ys), max(ys), 'etichetta', mg, ys)
            else:
                ds = [proprie[v['n']] for v in righe[r] if v['n'] in proprie]
                if ds:
                    anni_riga[r] = (min(d['inizio'] for d in ds), max(d['fine'] for d in ds), 'voci', None,
                                    [d['inizio'] for d in ds])
        for v in voci:
            r = (v['section'], v['row'])
            ev = dict(id='ev:cronologia.%d' % v['n'], fonte='cronologia', sorgente='cronologia.%d' % v['n'],
                      apri=hash_cron(v), etichetta=etichetta(v['text']), html=v['html'], frase=v['text'],
                      verso=None, versetti=self.runs_link(cit[v['n']]),
                      riferimenti=[[l['raw'], l['id']] for l in cit[v['n']]], rango=(0, v['n']),
                      cronologia=dict(voce=v['n'], sezione=v['section'], riga=v['row'], colonna=v['column'],
                                      margine=v['margin']),
                      circa=False, limite=None, incerto=False, periodo=v['section'])
            testa = intestazione(v, C_['columns'])
            if v['n'] in proprie:
                ev.update(proprie[v['n']])
            elif testa:
                # the heading of a column («ISRAELE», «GIUDA», «EGITTO»: one word in italic capitals, the name of
                # its column) is not an event: it opens its column, at the first year of the entry it heads
                d = next((proprie[w['n']] for w in voci if w['n'] > v['n'] and w['section'] == v['section']
                          and w['column'] == v['column'] and w['n'] in proprie), None)
                if d is None:
                    self.errors.append('cronologia.%d: the heading %r heads no dated entry' % (v['n'], v['text']))
                    d = dict(inizio=self.per[v['section'] - 1]['inizio'])
                ev.update(inizio=d['inizio'], fine=d['inizio'], precisione='riga', data=None, offset=None,
                          era='a.C.' if d['inizio'] < 0 else 'd.C.', data_da='colonna: intestazione', era_da='tavola')
            elif r in anni_riga:
                s, e, da, mg, _ = anni_riga[r]
                # inside its row, an entry follows the dated entries of its column: «Pasqua 70 … / Presa
                # delle mura … / Inizio di agosto … / 29 agosto 70» is 70, not the 69-79 of the row
                # (it would sort before «Pasqua 70»); not when the column is out of order there
                col = [w['n'] for w in righe[r] if w['column'] == v['column']]
                k = col.index(v['n'])
                a = next((proprie[n] for n in reversed(col[:k]) if n in proprie), None)
                b = next((proprie[n] for n in col[k + 1:] if n in proprie), None)
                s2 = max(s, a['inizio']) if a else s
                e2 = min(e, b['fine']) if b else e
                if s2 <= e2 and (s2, e2) != (s, e):
                    s, e, mg = s2, e2, None
                    da = 'colonna'
                ev.update(inizio=s, fine=e, precisione='riga', data=mg, offset=None,
                          era='a.C.' if e < 0 else ('d.C.' if s > 0 else 'a.C.–d.C.'),
                          data_da='riga: ' + {'etichetta': 'anno a margine', 'voci': 'date delle altre voci',
                                              'colonna': 'tra le voci della colonna'}[da],
                          era_da='tavola')
            else:
                # between the rows around it (across the sections too): from the latest start of the row
                # before to the earliest start of the row after; if the table is not in order there, from
                # the earliest start before to the latest start after; else the period
                k = ordine.index(r)
                prima = next((anni_riga[q] for q in reversed(ordine[:k]) if q in anni_riga), None)
                dopo = next((anni_riga[q] for q in ordine[k + 1:] if q in anni_riga), None)
                p = self.per[v['section'] - 1]
                se = None
                if prima and dopo:
                    if max(prima[4]) <= min(dopo[4]):
                        se = (max(prima[4]), min(dopo[4]))
                    elif min(prima[4]) <= max(dopo[4]):
                        se = (min(prima[4]), max(dopo[4]))
                if se:
                    ev.update(inizio=se[0], fine=se[1], precisione='riga', data=None, offset=None,
                              data_da='riga: tra le righe vicine', era_da='tavola',
                              era='a.C.' if se[1] < 0 else ('d.C.' if se[0] > 0 else 'a.C.–d.C.'))
                else:
                    ev.update(inizio=p['inizio'], fine=p['fine'], precisione='periodo', data=None, offset=None,
                              data_da='periodo', era='a.C.' if p['fine'] < 0 else 'a.C.–d.C.', era_da='tavola')
            ev.setdefault('limite', None)
            ev.setdefault('incerto', False)
            self.aggiungi(ev)
        return {v['n']: e for v, e in zip(voci, self.eventi[-len(voci):])}

    # --- the dynasties

    def dinastie(self):
        """A death (†) or the years of a reign as printed; the era: «a.C.» printed on Herod; the
        Hasmoneans before him are B.C., his descendants after him A.D. (ERE_DINASTIE)."""
        for p in self.P['dinastie']:
            if not p['date']:
                continue
            m = re.match(r'(†\s*)?(\d+)(?:\s*[–-]\s*(\d+))?\s*(a\.C\.|d\.C\.)?$', p['date'])
            if not m:
                self.errors.append('%s: the date %r is not read' % (p['id'], p['date']))
                continue
            era = era_suffisso(m.group(4)) or ERE_DINASTIE.get(p['id'])
            if not era:
                self.errors.append('%s: no era for %r' % (p['id'], p['date']))
                continue
            a = int(m.group(2))
            b = int(m.group(3)) if m.group(3) else a
            s, e = estremi('anno', a, b, era)
            tipo = 'morte' if m.group(1) else 'regno'
            nome = p['name']
            ramo = 'asmonei' if p['id'] < 'P15' else 'erodi'           # the chart: Hasmoneans P01-P14, Herod P15-
            self.aggiungi(dict(
                id='ev:dinastie.%s' % p['id'], fonte='dinastie', sorgente=p['id'], apri='#persona/%s' % p['id'],
                data=p['date'], offset=None, inizio=s, fine=e, precisione='anno' if a == b else 'intervallo',
                circa=False, limite=None, incerto=False, era=era,
                era_da='suffisso' if m.group(4) else 'dinastie: %s' % ERE_DINASTIE_PERCHE[ramo],
                etichetta='%s: %s %s' % (nome, 'morte' if tipo == 'morte' else 'anni di regno', p['date'].replace('† ', '')),
                html='%s%s %s' % ('%s. ' % p['number'] if p['number'] else '',
                                  '<em>%s</em>' % H.escape(nome) if p['italic'] else H.escape(nome), H.escape(p['date'])),
                frase=None, verso=None, versetti=[], riferimenti=[], rango=(1, int(p['id'][1:])),
                persona=p['id'], tipo=tipo))

    # --- the datings of the books

    def datazioni(self, cron):
        for d in self.I['datazioni']:
            if d['tipo'] == 'citato':
                continue
            c = cron[d['voce']]
            libri = [self.data_books[b] for b in d['libri']]
            self.aggiungi(dict(
                id='ev:datazione.%s' % d['id'], fonte='datazione', sorgente=d['id'], apri=c['apri'],
                data=c.get('data'), offset=None, inizio=c['inizio'], fine=c['fine'],
                precisione=c['precisione'], circa=c['circa'], limite=c.get('limite'), incerto=c.get('incerto', False),
                era=c['era'], era_da='la voce della tavola', data_da=c.get('data_da'),
                etichetta='%s: %s%s' % (TIPO_DATAZIONE[d['tipo']], ', '.join(libri),
                                        '' if d['nota'] == ', '.join(libri) else ' (%s)' % d['nota']),   # not «Abdia (Abdia)»
                html='<b>%s</b>: %s. %s' % (TIPO_DATAZIONE[d['tipo']], H.escape(', '.join(libri)), c['html']),
                frase=d['nota'], verso=None, versetti=c['versetti'], riferimenti=c['riferimenti'],
                rango=(2, d['riga']), libri=d['libri'], tipo=d['tipo'], voce=d['voce'],
                periodo=c['periodo'], stesso_evento=[c['id']]))
            c.setdefault('stesso_evento', []).append('ev:datazione.%s' % d['id'])     # both ways

    # --- the maps

    def carte(self):
        links = defaultdict(list)
        for l in self.I['links']:
            links[l['source']].append(l)
        for k, c in enumerate(self.I['carte']):
            src = 'carta.' + c['id']
            if not c['periodo']:
                self.non_datati.append(dict(fonte='carta', sorgente=c['id'], apri='#carte?c=' + c['id'], data=None, offset=None,
                                            motivo='carta senza periodo (carte.tsv)', frase=c['titolo']))
                continue
            xs = espressioni(c['periodo'])
            if len(xs) != 1:
                self.errors.append('%s: the period %r is not one expression' % (c['id'], c['periodo']))
                continue
            d, motivo = data(xs[0], None)
            if d is None:
                self.errors.append('%s: %r %s' % (c['id'], c['periodo'], motivo))
                continue
            self.aggiungi(dict(
                id='ev:carta.%s' % c['id'], fonte='carta', sorgente=c['id'], apri='#carte?c=' + c['id'], data=c['periodo'],
                offset=None, inizio=d[0], fine=d[1], precisione=precisione(xs[0]), circa=False, limite=None,
                incerto=False, era=d[2], era_da=d[3],
                etichetta='Carta: %s%s' % (c['titolo'], ' (%s)' % c['sottotitolo'] if c['sottotitolo'] else ''),
                html='<b>Carta</b>: %s%s · %s' % (H.escape(c['titolo']),
                                                 ' (%s)' % H.escape(c['sottotitolo']) if c['sottotitolo'] else '',
                                                 H.escape(c['periodo'])),
                frase=None, verso=None, versetti=self.runs_link_ranges(links[src]),
                riferimenti=[[l['raw'], l['id']] for l in links[src]], rango=(3, k), libri=c['libri']))

    def runs_link_ranges(self, links):
        ix = []
        for l in links:
            for a, b in l.get('ranges', []):
                ix += range(self.vix[a], self.vix[b] + 1)
        return runs(ix)


ERE_DINASTIE = {'P01': 'a.C.', 'P05': 'a.C.', 'P07': 'a.C.', 'P29': 'd.C.', 'P31': 'd.C.'}
ERE_DINASTIE_PERCHE = {'asmonei': 'gli Asmonei, prima di Erode (37–4 a.C.)',
                       'erodi': 'i discendenti di Erode (37–4 a.C.)'}
TIPO_DATAZIONE = {'composizione': 'Composizione', 'ministero': 'Ministero', 'evento': 'Evento'}


def intestazione(v, colonne):
    """Whether an entry of the table is the heading of its column: one word in italic capitals that names it."""
    nome = next(c['it'] for c in colonne if c['id'] == v['column']).lower()
    return bool(re.fullmatch(r'[A-ZÀ-Ü]+', v['text'])) and v['html'] == '<em>%s</em>' % v['text'] and \
        v['text'].lower() in nome.split()


def hash_cron(v):
    return '#cronologia/%d?v=%d' % (v['section'], v['n'])


def testamento_rif(testamento):
    def f(links):
        ts = {testamento.get(l['book']) for l in links if l.get('book') and l.get('status') in ('resolved', 'partial')}
        ts.discard(None)
        t = ts.pop() if len(ts) == 1 else None
        return 'NTd' if t == 'NT' else t
    return f


def stesso_evento(eventi, cron_nomi, persone_cron):
    """Link a dated sentence to a chronology entry with the same years when they share a cited verse
    or a name of a ruler printed in small capitals or capitals in the entry; a person of the dynasties to
    the entries that name them (integrazione.json, persone.tsv) with the same years."""
    per_anni = defaultdict(list)
    for e in eventi:
        if e['fonte'] == 'cronologia' and e['precisione'] in ('anno', 'intervallo', 'circa') and \
                e.get('data_da') in ('tavola', 'testo'):
            per_anni[(e['inizio'], e['fine'])].append(e)
    n = 0
    for e in eventi:
        if e['fonte'] == 'dinastie':
            for c in per_anni.get((e['inizio'], e['fine']), []):
                if c['cronologia']['voce'] in persone_cron.get(e['persona'], ()):
                    e.setdefault('stesso_evento', []).append(c['id'])
                    c.setdefault('stesso_evento', []).append(e['id'])
                    e.setdefault('stesso_perche', []).append('persona nominata nella voce (persone.tsv)')
                    n += 1
            continue
        if e['fonte'] not in ('nota', 'introduzione', 'testo', 'dizionario') or \
                e['precisione'] not in ('anno', 'intervallo', 'circa'):
            continue
        vs = set(_espandi(e['versetti']))
        for c in per_anni.get((e['inizio'], e['fine']), []):
            comuni = vs & set(_espandi(c['versetti']))
            nomi = [x for x in cron_nomi.get(c['cronologia']['voce'], ())
                    if re.search(r'(?<![\w])%s(?![\w])' % re.escape(x), e['frase'] or '', re.I)]
            if comuni or nomi:
                e.setdefault('stesso_evento', []).append(c['id'])
                c.setdefault('stesso_evento', []).append(e['id'])
                e.setdefault('stesso_perche', []).append('versetti comuni' if comuni else 'nome: ' + nomi[0])
                n += 1
    return n


def _espandi(r):
    for k in range(0, len(r), 2):
        yield from range(r[k], r[k + 1] + 1)


def nomi_cronologia(P):
    """The names a chronology entry prints in small capitals or capitals (rulers, governors), as words
    of 4 letters or more: the evidence of the same event."""
    out = {}
    for v in P['cronologia']['voci']:
        ns = set()
        for s in v['smallcaps'] + v['caps']:
            for w in re.findall(r'[A-Za-zÀ-ÿ’]+', s):
                if len(w) >= 4 and w.lower() not in NOMI_GENERICI:
                    ns.add(w[0].upper() + w[1:].lower())
        out[v['n']] = sorted(ns)
    return out


NOMI_GENERICI = {'egitto', 'israele', 'giuda', 'regno', 'impero', 'ellenistica', 'persiana', 'romana', 'dinastia',
                 'imperatore', 'sommo', 'sacerdote', 're', 'figlio', 'fratello', 'giudea', 'siria', 'palestina'}


# ------------------------------------------------------------------ main


def raccogli(data, coll, dz, P, I):
    vix = {v['id']: i for i, v in enumerate(data['verses'])}
    per = periodi(P)
    corr = tabella_correzioni()
    T = Raccolta(data, P, I, vix, per, corr)
    T.data_books = {b['osis']: b['title'] for b in data['books']}
    cron = T.cronologia()
    T.dinastie()
    T.datazioni(cron)
    T.carte()
    testamento = T.testamento
    # notes and introductions: the citations of stage 2 (with their offsets) are the references
    per_fonte = defaultdict(list)
    for l in coll['links']:
        if l['kind'] in ('note-cites', 'intro-cites') and l.get('offset') is not None:
            per_fonte[l['source']].append(l)
    for k, n in enumerate(data['notes']):
        t = testamento[n['anchor'].split('.')[0]]
        T.testo('nota', n['id'], n['text'], n['html'], per_fonte[n['id']], t, (4, k), '#' + n['anchor'], verso=n['anchor'])
    for k, it in enumerate(data['intros']):
        ts = {testamento[b] for b in it['books']}
        t = ts.pop() if len(ts) == 1 else None
        for p in it['paragraphs']:
            sid = '%s.%d' % (it['id'], p['n'])
            T.testo('introduzione', sid, p['text'], p['html'], per_fonte[sid], t, (5, k, p['n']), '#intro/' + sid)
    pl = defaultdict(list)
    for l in P['links']:
        if l['kind'] == 'front-cites':
            pl[l['source']].append(l)
    for k, x in enumerate(P['testi']):
        for p in x['paragraphs']:
            sid = '%s.%d' % (x['id'], p['n'])
            T.testo('testo', sid, p['text'], p['html'], pl[sid], 'moderno', (6, k, p['n']), '#introduzione-generale/' + sid)
    dl = defaultdict(list)
    for c in dz['citations']:
        if c.get('where') == 'paragraph' and c.get('offset') is not None:
            dl[c['para']].append(dict(c, id=c['id']))
    rif = testamento_rif(testamento)
    for k, v in enumerate(dz['voci']):
        for p in v.get('paragraphs', []):
            parti = p['sec'].split()
            t = 'NTd' if 'NT' in parti else ('AT' if 'VT' in parti else None)
            tutta = rif(dl[p['id']])

            def ctx_rif(nella, tutta=tutta):
                return rif(nella) or tutta
            T.testo('dizionario', p['id'], p['text'], p['html'], dl[p['id']], t, (7, k, p['n']),
                    '#voce/%s/%d' % (v['id'], p['n']), ctx_rif=ctx_rif)
    # the correction table: every row used
    for key, row in corr.items():
        if not T.usate[key]:
            T.errors.append('eventi-correzioni.tsv row %d (%s, %r) matches no expression' % (row['riga'], key[0], key[1]))
    T.eventi.sort(key=lambda e: (e['inizio'], e['fine'], e['rango']))
    for k, e in enumerate(T.eventi, 1):
        e['n'] = k
    pc = defaultdict(set)
    for x in I['persone']['cronologia']:
        pc[x['persona']].add(x['voce'])
    nl = stesso_evento(T.eventi, nomi_cronologia(P), pc)
    return T, per, nl


def checks(T, data_testi):
    errors = list(T.errors)
    ids = Counter(e['id'] for e in T.eventi)
    errors += ['duplicate id %s' % k for k, n in ids.items() if n > 1]
    cron = {e['cronologia']['voce'] for e in T.eventi if e['fonte'] == 'cronologia'}
    if len(cron) != 585:
        errors.append('%d chronology entries on the line, not 585' % len(cron))
    prev = None
    for e in T.eventi:
        if not (isinstance(e['inizio'], int) and isinstance(e['fine'], int) and e['inizio'] <= e['fine']):
            errors.append('%s: years %r %r' % (e['id'], e['inizio'], e['fine']))
        if e['precisione'] not in PRECISIONI or e['fonte'] not in FONTI:
            errors.append('%s: precision %r source %r' % (e['id'], e['precisione'], e['fonte']))
        k = (e['inizio'], e['fine'], e['rango'])
        if prev and k < prev:
            errors.append('%s out of order' % e['id'])
        prev = k
        if e['offset'] is not None and e['data']:
            t = data_testi.get(e['sorgente'])
            if t is not None and t[e['offset']:e['offset'] + len(e['data'])] != e['data']:
                errors.append('%s: offset %d is not %r' % (e['id'], e['offset'], e['data']))
    for e in T.eventi:
        if e['html'] and not bilanciato(e['html']):
            errors.append('%s: the HTML is not well nested' % e['id'])
    for x in T.non_datati:
        if x['offset'] is not None and x['data']:
            t = data_testi.get(x['sorgente'])
            if t is not None and t[x['offset']:x['offset'] + len(x['data'])] != x['data']:
                errors.append('non datato %s: offset %d is not %r' % (x['sorgente'], x['offset'], x['data']))
    return errors


def bilanciato(h):
    pila = []
    for m in re.finditer(r'<(/?)([a-z]+)[^>]*>', h):
        if m.group(2) == 'br':
            continue
        if not m.group(1):
            pila.append(m.group(2))
        elif not pila or pila.pop() != m.group(2):
            return False
    return not pila


def testi_sorgente(data, dz, P):
    t = {n['id']: n['text'] for n in data['notes']}
    for it in data['intros']:
        for p in it['paragraphs']:
            t['%s.%d' % (it['id'], p['n'])] = p['text']
    for x in P['testi']:
        for p in x['paragraphs']:
            t['%s.%d' % (x['id'], p['n'])] = p['text']
    for v in dz['voci']:
        for p in v.get('paragraphs', []):
            t[p['id']] = p['text']
    for v in P['cronologia']['voci']:
        t['cronologia.%d' % v['n']] = v['text']
    return t


def main(a):
    quiet = '-q' in a
    data = json.load(open(os.path.join(BUILD, 'bibbia.json'), encoding='utf-8'))
    coll = json.load(open(os.path.join(BUILD, 'collegamenti.json'), encoding='utf-8'))
    dz = json.load(open(os.path.join(BUILD, 'dufour.json'), encoding='utf-8'))
    P = json.load(open(os.path.join(BUILD, 'paratesto.json'), encoding='utf-8'))
    I = json.load(open(os.path.join(BUILD, 'integrazione.json'), encoding='utf-8'))
    T, per, nl = raccogli(data, coll, dz, P, I)
    errors = checks(T, testi_sorgente(data, dz, P))
    for e in T.eventi:
        e.pop('rango')
    s = dict(eventi=len(T.eventi), fonti=dict(Counter(e['fonte'] for e in T.eventi)),
             precisione=dict(Counter(e['precisione'] for e in T.eventi)),
             era_da=dict(Counter(re.sub(r'[:;].*', '', e['era_da']) for e in T.eventi)),
             periodi=dict(Counter(str(e['periodo']) for e in T.eventi)),
             cronologia_data_da=dict(Counter(e['data_da'] for e in T.eventi if e['fonte'] == 'cronologia')),
             non_datati=len(T.non_datati), non_datati_motivi=dict(Counter(re.sub(r' \(.*', '', x['motivo'])
                                                                          for x in T.non_datati).most_common()),
             stesso_evento=nl)
    out = dict(meta=dict(generated_by='tools/ontologia/eventi.py', summary=s,
                         precisioni=list(PRECISIONI), fonti=list(FONTI),
                         ordine='inizio, fine, poi la fonte (cronologia, dinastie, datazioni, carte, note, '
                                'introduzioni, testi, dizionario) e la posizione nella fonte'),
               periodi=per, eventi=T.eventi, non_datati=T.non_datati)
    dump(out, OUT)
    if '--rivedi' in a:
        rivedi(T, a[a.index('--rivedi') + 1])
    if not quiet:
        print(json.dumps(s, ensure_ascii=False, indent=1))
    print('eventi: %d events (%s), %d not dated, %d same-event links' % (
        len(T.eventi), ', '.join('%s %d' % (k, v) for k, v in s['fonti'].items()), len(T.non_datati), nl))
    for e in errors[:40]:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errors else '%d errors' % len(errors), os.path.relpath(OUT, C)))
    return 1 if errors else 0


def rivedi(T, path):
    """A table for the review by hand: every event read in free text and every candidate refused."""
    with open(path, 'w', encoding='utf-8') as f:
        f.write('esito\tfonte\tsorgente\tdata\tinizio\tfine\tprecisione\tera_da\tfrase\n')
        for e in T.eventi:
            if e['fonte'] in ('nota', 'introduzione', 'testo', 'dizionario') or e.get('data_da') == 'testo':
                f.write('\t'.join(str(x) for x in ('evento', e['fonte'], e['sorgente'], e['data'], e['inizio'], e['fine'],
                                                   e['precisione'], e['era_da'], e['etichetta'])) + '\n')
        for x in T.non_datati:
            f.write('\t'.join(str(y) for y in ('non datato', x['fonte'], x['sorgente'], x['data'], '', '', '',
                                               x['motivo'], x['frase'])) + '\n')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
