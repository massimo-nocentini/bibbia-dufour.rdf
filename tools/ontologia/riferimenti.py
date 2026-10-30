"""Parse and resolve the biblical references of the margins, the notes and the introductions.

usage: riferimenti.py [-i ontologia/build/bibbia.json] [-o ontologia/build/collegamenti.json] [-q]

Stage 2 of the verse ontology: reads bibbia.json (stage 1, estrai.py) and writes one
typed link per reference to collegamenti.json:
  mref         one reference of a margin (\\mref, ";"-separated): relation related (no
               sign), parallel (‖), doublet (=), quoted-later (/); numbering when the
               margin prints the verse number of another tradition (Vulgate, LXX, TM),
               comment for "(aramaico)", "(ebraico)"
  note-label   the verses a BJ note comments on (its label, resolved by stage 1)
  note-cites   a reference cited in the text of a note
  intro-cites  a reference cited in an introduction
Each link has its targets (verse ids, ranges expanded), a status (resolved, partial,
unresolved, numbering, comment) and, when not resolved, the reason. Misprints stay
as printed and are reported, never corrected.

The grammar (README, "Stage 2"): CEI sigla, "c,v", "." joins verses of a chapter,
"–" ranges (also across chapters), ";" separates references, which inherit the book
(and the verse/chapter mode) of the previous one; a reference without a book is the
current book; letters a/b/c are verse parts (or lettered verses where they exist);
suffixes s (and the next), ss (and following: to the end of the pericope, within the
chapter), p (and parallels), + (key note there); qualifiers (LXX), (volg.), (TM),
Tg; "v"/"vv" verses and "c"/"cc" chapters of the current chapter/book; "cf.".

parse(text, ctx) and resolve(ref, bibbia) are the API used by test_riferimenti.py.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from canone import LIBRI, PROLOGO, numeric_order  # noqa: E402
from estrai import dump  # noqa: E402

IN = os.path.join(C, 'ontologia', 'build', 'bibbia.json')
OUT = os.path.join(C, 'ontologia', 'build', 'collegamenti.json')

ESTER = ('Esth', 'EsthGr')                      # both answer to "Est": Hebrew first
UN_CAPITOLO = ('Obad', 'Phlm', '2John', '3John', 'Jude')
SIGLA = defaultdict(list)                       # CEI siglum -> OSIS codes
for _sid, _osis, _sig in LIBRI:
    SIGLA[_sig].append(_osis)
SIGLA['Est'] = list(ESTER)
OSIS2SIGLA = {osis: sig for _, osis, sig in LIBRI}

# books the notes cite that are not in this Bible (their references are kept, unresolved)
EXTRA = {'3 Esdra': '3Esdr', '1 Esdra': '1Esdr', '4 Esdra': '4Esdr', '1 Enoc': '1En', 'Enoc': '1En',
         'Libro di Enoc': '1En', 'Giubilei': 'Jub', 'Didachè': 'Did', '3 Mac': '3Macc', '4 Mac': '4Macc',
         'Testamento di Levi': 'TLevi', '1QS': '1QS'}
# sigla as misprinted in the notes (reported as unknown, with the likely siglum)
MISPRINT = {'Zac': 'Zc', '2Mc': '2Mac'}

RELATION = {None: 'related', '‖': 'parallel', '=': 'doublet', '/': 'quoted-later'}
TRADITION = ('LXX', 'volg.', 'TM', 'TM var.')
DASH = '–-'
SUP = str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾ªº', '0123456789+-()ao')


# ---------------------------------------------------------------- grammar

def _book_alternation():
    names = []
    for sig in SIGLA:
        m = re.fullmatch(r'([123])(\w+)', sig)
        names.append(r'%s\ ?%s' % m.groups() if m else re.escape(sig))   # "\ ": also in re.X
    names += [re.escape(x).replace(r'\ ', r'\ ?') for x in list(EXTRA) + list(MISPRINT)]
    return '|'.join(sorted(names, key=len, reverse=True))


BOOK = r'(?<![\w])(?:%s)(?![\w])' % _book_alternation()
# a book named in full right before "(3,1": "Isaia (65,17; 66,22)" (only names that are
# not also common persons or words in the notes: no Giuda, Ebrei, Sapienza, Cantico ...)
NOMI = {'Genesi': 'Gen', 'Levitico': 'Lv', 'Deuteronomio': 'Dt', 'Giobbe': 'Gb', 'Siracide': 'Sir',
        'Qoèlet': 'Qo', 'Isaia': 'Is', 'Geremia': 'Ger', 'Ezechiele': 'Ez', 'Daniele': 'Dn', 'Osea': 'Os',
        'Gioele': 'Gl', 'Amos': 'Am', 'Abdia': 'Abd', 'Michea': 'Mi', 'Naum': 'Na', 'Abacuc': 'Ab',
        'Sofonia': 'Sof', 'Aggeo': 'Ag', 'Zaccaria': 'Zc', 'Malachia': 'Ml', 'Matteo': 'Mt', 'Marco': 'Mc',
        'Luca': 'Lc', 'Giovanni': 'Gv', 'Romani': 'Rm', 'Galati': 'Gal', 'Efesini': 'Ef', 'Filippesi': 'Fil',
        'Colossesi': 'Col', 'Apocalisse': 'Ap', 'Salmi': 'Sal', 'Proverbi': 'Pr', 'Lamentazioni': 'Lam',
        'Baruc': 'Bar'}
NOME = r'(?<![\w])(?:%s)(?=\s*[:(]?\s*(?:cf\.\s*)?(?:\d+,\d+|cc?\s\d))' % '|'.join(NOMI)
NOME_LIBERO = re.compile(r'(?<![\w])(?:%s)(?![\w])' % '|'.join(NOMI))     # "Ezechiele lo sviluppa (cc 16 e 23)"
# "neovolg. (2,21)", "Libro dei Giubilei (48,14)": another numbering or an unknown book
NOT_CEI = re.compile(r'(?:\b(?:neo)?volg\.|\blat\.|\bLXX|\bgr\.|\bTM|\bsir\.|\bLibro d\w* \w+)\s*\(?$')
# "circa 22,5 cm", "4,50 litri": decimal numbers, not references
MISURA = re.compile(r'\d+,\d+\s*(?:cm|m|km|metri|litri|l|grammi|g|kg|chili|ettari|sicli|talenti|%)(?![\w])')
PT = r'\d+(?:,\d+)?[a-z]{0,3}\+?'
SEG = r'%s(?:[%s](?:\d+(?:,\d+)?[a-z]{0,2}|[a-z])(?![\dA-Z]|\ (?:Sam|Re|Cr|Mac|Cor|Ts|Tm|Pt|Gv)\b)\+?)?' % (
    PT, DASH)                                   # not the start of "–2Re 1" (a range across books)
SPEC = r'%s(?:\.%s)*' % (SEG, SEG)
ITEM = r"""
  (?P<cf>[Cc]fr?\.\s*(?:anche\s+|già\s+)?)?
  (?P<sign>[‖=/])?\s*
  (?P<lxx>LXX:\s*)?
  (?:(?P<book>%s)\s*%s)?
  (?P<prol>prol(?:ogo(?![\w])|\.)\s*)?
  (?P<pfx>(?:vv|v|cc|c)\.?\s+(?=\d))?
  (?P<spec>%s)?
  (?P<xbook>[–-]\ ?(?:%s)\ ?(?P<xspec>\d+(?:,\d+)?[a-z]?))?
  (?P<alt>\((?:\d+[a-z]{0,2}|[a-z])\))?
  (?P<qual>\s*\((?:LXX|volg\.|TM(?:\ var\.)?|passim|aramaico|ebraico)\)|\s+Tg(?![\w]))?
"""
ITEM_MARGIN = re.compile(ITEM % (BOOK + r'|(?<![\w])\d?[A-Z][a-z]{0,4}(?![\w])', '', SPEC, BOOK), re.X)
ITEM_PROSE = re.compile(ITEM % (BOOK + '|' + NOME, r'(?:[:(]\s*(?=(?:cf\.\s*)?(?:\d+,\d+|cc?\s\d)))?', SPEC, BOOK),
                        re.X)
NEXT_PROSE = r'(?:[Cc]fr?\.\s*)?(?:(?:%s)\s?\d|\d+,\d+)' % BOOK
SEP_MARGIN = re.compile(r'\s*;\s*|\s+(?=(?:%s)\s?\d|\d+,\d+)|(?=[=‖/])' % BOOK)   # "2Cr 1,14=9,25"
SEP_PROSE = re.compile(r'\s*\]?\s*;\s*(?=%s|(?:vv?|cc?)\s\d|\d)|,\s+(?=%s)|\s+(?:e|o)(?:\s+(?:forse|anche|già))?\s+(?=%s)'
                       r'|\s*[\[(]\s*(?=%s)'
                       r'|\s+(?==\s*(?:%s)\s?\d)' % (NEXT_PROSE, NEXT_PROSE, NEXT_PROSE, NEXT_PROSE, BOOK))
SEP_VERSI = re.compile(r'\s+e\s+(?=\d+(?![,\d]))|,\s+(?=\d+[\s);.]|\d+$)')
START_PROSE = re.compile(r'(?:%s)(?=\s?\d|\s+prol|\s\(\d+,\d+)|%s'
                         r'|(?<![\w])[Cc]fr?\.\s*(?=\d+,\d+|(?:%s)(?:\s?\d|\s+prol))'
                         r'|(?<=\()(?=\d+,\d+)|(?<![\w])(?:vv|v|cc|c)\.?\s(?=\d)|(?<![\w])prologo\s(?=\d)'
                         r'|(?<![\w,.–\-/:+])(?=\d{1,3},\d{1,3}(?![\d,]))'
                         % (BOOK, NOME, BOOK))
POINT = re.compile(r'(\d+)(?:,(\d+))?([a-z]{0,3})(\+?)$')


def norm_book(name):
    """'1 Cor' -> '1Cor'; extra-canonical names and misprints stay as printed."""
    if name in EXTRA or name in MISPRINT:
        return name
    if name in NOMI:
        return NOMI[name]
    k = re.sub(r'(?<=\d) (?=[A-Z])', '', name)
    return k if k in SIGLA or k in MISPRINT else name


def split_spec(spec, chapter_mode, cap):
    """'2,4b–25.27s+' -> spans {c1, v1, t1, c2, v2, t2, plus}; v None = whole chapters.

    chapter_mode: a number without a comma is a chapter (else a verse of cap). A range
    from a chapter to a verse ("Sal 9–10,32", "Gen 1–2,4a") starts at the first verse
    of its chapter: the span has v1 = 1 and from_start = True."""
    spans = []
    for k, seg in enumerate(spec.split('.')):
        parts = re.split('[%s]' % DASH, seg, maxsplit=1)
        a = POINT.match(parts[0])
        if not a:
            return None
        plus = bool(a.group(4))
        if a.group(2):
            cap, v1, chapter_mode = int(a.group(1)), int(a.group(2)), False
        elif chapter_mode:
            cap, v1 = int(a.group(1)), None
        else:
            v1 = int(a.group(1))
        span = dict(c1=cap, v1=v1, t1=a.group(3), c2=cap, v2=v1, t2=a.group(3), plus=plus)
        if len(parts) > 1:
            z = re.fullmatch(r'(?:(\d+)(?:,(\d+))?)?([a-z]{0,2})(\+?)', parts[1])
            if not z or not (z.group(1) or z.group(3)):
                return None
            span['t1'] = a.group(3)
            if z.group(2):
                span.update(c2=int(z.group(1)), v2=int(z.group(2)))
                if v1 is None:
                    span.update(v1=1, from_start=True)
            elif z.group(1) and v1 is None:
                span.update(c2=int(z.group(1)))
            elif z.group(1):
                span.update(v2=int(z.group(1)))
            span['t2'] = z.group(3)
            span['plus'] = plus or bool(z.group(4))
            cap = span['c2']
        spans.append(span)
    return spans


def parse(text, ctx, prose=False, start=0):
    """References of text[start:] as a list of dicts (and the end of what was read).

    ctx: book (OSIS of the current book, or None in an introduction), chapter (current
    chapter, or None), margin (True for an \\mref). In prose the reading stops at the
    first thing that is not a reference; in a margin the rest becomes an unresolved
    item ('not understood')."""
    item_re, sep_re = (ITEM_PROSE, SEP_PROSE) if prose else (ITEM_MARGIN, SEP_MARGIN)
    m = re.fullmatch(r'\((volg\.|LXX|TM)\)\s*(.+)', text)
    if m and not prose:                         # 2Re 12,1 "(volg.) 21 12,1"
        return [dict(raw=text, offset=0, sign=None, cf=False, qualifier=m.group(1), alt=m.group(2),
                     spans=[], siglum=None, current=True, numbering=True)], len(text)
    refs, i = [], start
    book, verse_mode = None, False              # inherited across ";"
    glued = False                               # no separator before this item: "2Cr 1,14=9,25"
    while i < len(text):
        m = item_re.match(text, i)
        if not m or not any(m.group(g) for g in ('book', 'spec', 'prol', 'qual')) or \
                prose and not (m.group('spec') or m.group('prol')):
            if prose:
                break
            j = text.find(';', i + 1)           # a margin: skip to the next ";"
            j = len(text) if j < 0 else j
            refs.append(dict(raw=text[i:j].strip(), offset=i, sign=None, cf=False, qualifier=None, alt=None,
                             spans=[], siglum=book, current=book is None, problem='not understood'))
            s = sep_re.match(text, j)
            i = s.end() if s else j
            continue
        g = m.groupdict()
        ref = dict(raw=text[m.start():m.end()].strip(), offset=m.start() + len(m.group(0)) - len(
            m.group(0).lstrip()), sign=g['sign'], cf=bool(g['cf']), qualifier=None, alt=None, spans=[],
            explicit=bool(g['book']), glued=glued)
        before = (book, verse_mode)
        if g['book']:
            book = norm_book(g['book'].strip())
            verse_mode = False
        elif g['pfx']:
            verse_mode = g['pfx'].startswith('v')
        elif g['sign'] == '=' and not prose and not glued and refs and refs[-1]['sign'] != '‖':
            book, verse_mode = None, False      # "Is 25,8; =21,4" (Ap 7,17): a doublet in this book
        ref['siglum'] = book
        ref['current'] = book is None
        qual = (g['qual'] or '').strip().strip('()')
        if g['lxx']:                            # Jer 26,1 "LXX: 33": the LXX chapter
            qual = 'LXX'
            ref.update(numbering=True, current=True)
        if qual in ('aramaico', 'ebraico'):
            ref['comment'] = qual
        elif qual == 'passim':
            ref['passim'] = True
        elif qual:
            ref['qualifier'] = qual
        if g['alt']:
            alt = g['alt'].strip('()')
            if re.fullmatch('[a-z]', alt) and g['spec'] and not g['spec'][-1].isalpha():
                g['spec'] += alt                # Est 4,17(b) = 4,17b
            else:
                ref['alt'] = alt
        target_book = ctx.get('book') if book is None else (SIGLA.get(book) or [None])[0]
        one_chapter = target_book in UN_CAPITOLO
        if g['prol']:
            ref['spans'] = [dict(c1=0, v1=None, t1='', c2=0, v2=None, t2='', plus=False)]
            if g['spec']:
                ref['spans'] = split_spec(g['spec'], False, 0)
        elif g['spec']:
            if g['pfx']:
                chapter_mode = g['pfx'].startswith('c')
            else:                               # also a bare number in a margin: Gen 25,9 "23"
                chapter_mode = not verse_mode and not one_chapter
            if chapter_mode and not g['pfx'] and not prose and book is None and \
                    '.' in g['spec'] and ',' not in g['spec']:
                chapter_mode = False            # "9.11": "." joins verses, never chapters
            cap = 1 if one_chapter else ctx.get('chapter')
            if chapter_mode and not g['pfx'] and ',' not in g['spec'] and refs and refs[-1]['spans'] and \
                    refs[-1]['spans'][-1]['v2'] is not None and refs[-1]['siglum'] == book:
                ref.update(verse_chapter=refs[-1]['spans'][-1]['c2'], raw_spec=g['spec'])   # "Mt 27,56; 61"
            ref['spans'] = split_spec(g['spec'], chapter_mode, cap)
            if ref['spans'] is None:
                ref['problem'] = 'not understood'
                ref['spans'] = []
            elif any(s['v1'] is not None and s['c1'] is None for s in ref['spans']):
                ref['problem'] = 'no chapter context'
        if g['xbook'] and ref['spans']:        # "1Re 17–2Re 1": a range across books
            to = norm_book(re.sub(r'^[–-] ?| ?%s$' % re.escape(g['xspec']), '', g['xbook']))
            end = split_spec(g['xspec'], True, None)
            ref.update(to_book=to, to_span=end[0] if end else None)
        refs.append(ref)
        i = m.end()
        if prose and g['sign'] == '=' and g['book']:
            book, verse_mode = before           # "37,4 = 2Re 19,4; 37,31": back to Isaiah
        s = sep_re.match(text, i) or (prose and verse_mode and SEP_VERSI.match(text, i))
        if not s and not prose and i < len(text) and not text[i].isspace():
            j = text.find(';', i)               # "‖Lc 23,2–5,13–25": one misprinted item
            j = len(text) if j < 0 else j
            ref.update(raw=text[m.start():j].strip(), spans=[], problem='not understood')
            s = sep_re.match(text, j)
            i = s.end() if s else j
            glued = False
            continue
        glued = bool(s) and not s.group(0)
        if s:
            i = s.end()
        elif prose:
            break
    return refs, i


def scan_prose(text, ctx):
    """All the references cited in a note or an introduction paragraph.

    A chain starts at an explicit siglum ("1 Cor" too), at a book named in full before
    "(3,1" or ": 3,1" (NOMI), or, when the context has a current book, at "cf. 3,1",
    "(3,1", "3,1", "v 6", "vv 3–5", "c 2", "cc 8–10". Dates ("36-25 a.C."), manuscript
    sigla (P46, 1QpAb), measures ("22,5 cm") and other numberings ("neovolg. (2,21)")
    never start one."""
    refs, pos = [], 0
    last, last_at = None, -1                    # the last book named in the text (siglum or name)
    while True:
        m = START_PROSE.search(text, pos)
        if not m:
            return refs
        if not m.group(0) and text[m.start() - 1:m.start()] != '(' and (
                MISURA.match(text, m.start()) or re.search(r'circa\s+$', text[max(0, m.start() - 12):m.start()])):
            pos = m.start() + 1                 # a bare "3,1": not a measure
            continue
        got, end = parse(text, ctx, prose=True, start=m.start())
        pos = max(end, m.end(), m.start() + 1)
        if got and got[0]['current'] and (not ctx.get('book') or got[0].get('problem') or
                                          m.group(0).startswith('prologo') and ctx['book'] != 'Sir' or
                                          NOT_CEI.search(text[max(0, m.start() - 30):m.start()])):
            continue                            # no current book (introductions), chapter or numbering
        named = list(NOME_LIBERO.finditer(text, last_at + 1, m.start()))
        if named:
            last, last_at = NOMI[named[-1].group(0)], named[-1].start()
        aside = re.search(r'\(\s*=\s*$', text[max(0, m.start() - 6):m.start()])   # "10,34 (= Sal 82,6); 14,20"
        for r in got:
            if r['explicit']:
                if r['siglum'] in SIGLA and not aside:
                    last, last_at = r['siglum'], r['offset']
            elif r['siglum'] not in EXTRA and r['siglum'] not in MISPRINT:
                # other readings, tried when the book in force has no such verse (resolve)
                cur = OSIS2SIGLA.get(ctx.get('book'))
                if r['current']:                # "(cc 16 e 23)" after "Ezechiele" in a note on Osea
                    alts = [last] if last and last != cur else []
                else:                           # "Sal 110 (cf. 22,41s)" in a note on Mt
                    alts = [None] + ([last] if last and last not in (r['siglum'], cur) else [])
                if alts:
                    r['fallback_books'] = alts
        refs += got


# ---------------------------------------------------------------- resolution

class Bibbia:
    """The verses of bibbia.json by book, chapter and number, and the notes by verse."""

    def __init__(self, data):
        self.verses = {v['id']: v for v in data['verses']}
        self.books = {b['osis']: b for b in data['books']}
        self.by_num = defaultdict(list)
        self.by_chapter = defaultdict(list)
        self.sorted = defaultdict(list)
        for v in sorted(data['verses'], key=lambda v: (v['book'], v['chapter'], v['verse'], v['order'])):
            self.by_num[(v['book'], v['chapter'], v['verse'])].append(v)
        for key in sorted(self.by_num):         # lettered verses by letter: Isa 10,18a before 18b
            self.by_num[key] = numeric_order(self.by_num[key])
            for v in self.by_num[key]:
                self.by_chapter[key[:2]].append(v)
                self.sorted[key[0]].append(v)
        self.rank = {v['id']: r for vs in self.sorted.values() for r, v in enumerate(vs)}
        self.notes_first, self.notes_at, self.notes_on = defaultdict(list), defaultdict(list), defaultdict(list)
        for n in sorted(data['notes'], key=lambda n: len(n['targets'])):     # narrowest first
            if n['targets']:
                self.notes_first[n['targets'][0]].append(n['id'])
            self.notes_at[n['anchor']].append(n['id'])
            if n['scope'] == 'verses' and len(n['targets']) <= 20:
                for t in n['targets']:
                    self.notes_on[t].append((len(n['targets']), n['id']))
        self.mrefs_at = defaultdict(list)
        for m in data['mrefs']:
            self.mrefs_at[m['anchor']].append(m['id'])

    def chapters(self, osis):
        return [c['n'] for c in self.books[osis]['chapters']]

    def letters(self, osis, cap, num, tail):
        """(letters, flags) of a tail like 'b', 's', 'ss', 'p', 'sp', 'bs'; None if odd."""
        if not tail:
            return '', ''
        if any(v['suffix'] == tail for v in self.by_num.get((osis, cap, num), [])):
            return tail, ''                     # EsthGr 8,12s is a verse, not "and the next"
        if tail in ('s', 'ss', 'p', 'sp'):
            return '', tail
        if len(tail) == 2 and tail[1] in 'sp':
            return tail[0], tail[1]
        if len(tail) == 1:
            return tail, ''
        if re.fullmatch('[a-h]+', tail) and list(tail) == sorted(set(tail)):
            return tail[0], ''                  # parts of a verse: Sir 41,21ab
        return None

    def point(self, osis, cap, num, letters, end=False):
        """The verses one end of a span designates (None if there is no such verse)."""
        vs = self.by_num.get((osis, cap, num))
        if not vs:
            return None
        if not letters:
            return [v for v in vs if not v['suffix']] or vs
        exact = [v for v in vs if v['suffix'] == letters]
        if exact:
            return exact
        lettered = [v for v in vs if v['suffix']]
        if lettered and len(letters) == 1:
            sel = [v for v in lettered if (v['suffix'] <= letters if end else v['suffix'] >= letters)]
            if sel:
                return [sel[-1]] if end else [sel[0]]
            return None
        return [v for v in vs if not v['suffix']] or vs     # a part of a verse (1,2b)

    def between(self, osis, a, z):
        return self.sorted[osis][self.rank[a['id']]:self.rank[z['id']] + 1]

    def keynote(self, vid):
        """(notes, margins) a '+' sends to: the note whose label starts at vid, else one
        called from vid, else the narrowest (at most 20 verses) commenting on vid; with no
        such note, the group of margin references printed beside vid."""
        notes = self.notes_first.get(vid) or self.notes_at.get(vid) or \
            [n for _, n in sorted(self.notes_on.get(vid, []))[:1]]
        return notes, ([] if notes else self.mrefs_at.get(vid, []))


def label(osis, cap, num=None, tail=''):
    c = PROLOGO if cap == 0 else cap
    return '%s %s' % (OSIS2SIGLA.get(osis, osis), c if num is None else '%s,%s%s' % (c, num, tail))


def resolve_span(B, osis, sp):
    """(verses, flags, keynote verse, problem) of one span in book osis."""
    if osis not in B.books:
        return [], set(), None, 'no book %s' % osis
    chapters = B.chapters(osis)
    if sp['v1'] is None:                        # whole chapters
        flags = set()
        for t in (sp['t1'], sp['t2']):
            if t in ('s', 'ss', 'p', 'sp'):
                flags |= set(t) if t == 'sp' else {t}
            elif t:
                return [], set(), None, 'letter %r after chapter %s' % (t, label(osis, sp['c1']))
        lo, hi = sp['c1'], sp['c2']
        if 's' in flags:
            hi += 1
        bad = [c for c in (lo, hi) if c not in chapters]
        if bad:
            return [], flags, None, 'no chapter %s (%s has %d)' % (
                label(osis, bad[0]), OSIS2SIGLA.get(osis), len([c for c in chapters if c]))
        if hi < lo:
            return [], flags, None, 'reversed range'
        vs = [v for c in chapters if lo <= c <= hi for v in B.by_chapter[(osis, c)]]
        return vs, flags, (vs[0] if sp['plus'] else None), None
    t = sp['t1']
    if len(t) == 2 and (sp['c1'], sp['v1'], t) == (sp['c2'], sp['v2'], sp['t2']) and \
            set(t) <= {v['suffix'] for v in B.by_num.get((osis, sp['c1'], sp['v1']), [])}:
        sp = dict(sp, t1=t[0], t2=t[1])         # Est 4,17de = 4,17d–e
    ends = []
    flags = set()
    for c, n, t, end in ((sp['c1'], sp['v1'], sp['t1'], False), (sp['c2'], sp['v2'], sp['t2'], True)):
        if not end and sp.get('from_start') and B.by_chapter.get((osis, c)):
            ends.append(B.by_chapter[(osis, c)][:1])   # "Sal 9–10,32": from the head of Ps 9
            continue
        lf = B.letters(osis, c, n, t)
        if lf is None:
            return [], flags, None, 'odd suffix %r in %s' % (t, label(osis, c, n))
        if lf[1]:
            flags |= {'s', 'p'} if lf[1] == 'sp' else {lf[1]}
        p = B.point(osis, c, n, lf[0], end)
        if p is None:
            if c not in chapters:
                return [], flags, None, 'no chapter %s (%s has %d)' % (
                    label(osis, c), OSIS2SIGLA.get(osis), len([x for x in chapters if x]))
            return [], flags, None, 'no verse %s (chapter has %d)' % (
                label(osis, c, n, lf[0]), len(B.by_chapter[(osis, c)]))
        ends.append(p)
    lo, hi = ends[0][0], ends[1][-1]
    if B.rank[hi['id']] < B.rank[lo['id']]:
        return [], flags, None, 'reversed range %s–%s' % (lo['label'], hi['label'])
    if 's' in flags:
        nxt = B.sorted[osis][B.rank[hi['id']] + 1:B.rank[hi['id']] + 2]
        if nxt:
            hi = nxt[0]
    elif 'ss' in flags:                         # to the end of the pericope, within the chapter
        same = B.by_chapter[(osis, hi['chapter'])]
        same = same[same.index(hi):]
        stop = [v for v in same if hi['pericope'] and v['pericope'] == hi['pericope']] or same
        hi = stop[-1]
    return B.between(osis, lo, hi), flags, (lo if sp['plus'] else None), None


def resolve_across(ref, B, osis):
    """A range from one book to a later one: "1Sam 16,14–2Sam 1", "1Re 17–2Re 1"."""
    to = (SIGLA.get(ref['to_book']) or [None])[0]
    if to not in B.books or not ref['to_span']:
        ref['reason'] = 'unknown siglum %s' % ref['to_book']
        return ref
    last, first = B.sorted[osis][-1], B.sorted[to][0]
    sp = ref['spans'][0]
    head = dict(sp, c2=last['chapter'], v2=None if sp['v1'] is None else last['verse'], t2='')
    tail = dict(ref['to_span'], c1=first['chapter'], v1=None if ref['to_span']['v1'] is None else first['verse'],
                t1='')
    got = [resolve_span(B, osis, head), resolve_span(B, to, tail)]
    problems = [g[3] for g in got if g[3]]
    order = [b['osis'] for b in sorted(B.books.values(), key=lambda b: b['order'])]
    if not problems and order.index(to) <= order.index(osis):
        problems = ['reversed range across books']
    if problems:
        ref['reason'] = '; '.join(problems)
        return ref
    middle = [v for b in order[order.index(osis) + 1:order.index(to)] for v in B.sorted[b]]
    vs = got[0][0] + middle + got[1][0]
    ref.update(book=osis, targets=[v['id'] for v in vs], ranges=[[vs[0]['id'], vs[-1]['id']]],
               status='resolved')
    return ref


def books_for(ref, ctx):
    """Candidate OSIS codes, in order of preference; Esther: Hebrew first."""
    if ref['current']:
        osis = ctx.get('book')
        if osis in ESTER:
            return [osis] + [x for x in ESTER if x != osis]
        return [osis] if osis else []
    return list(SIGLA.get(ref['siglum'], []))


def greek_letters(B, cap, num, tail):
    """The letters after an Esther reference name an addition of the Greek text:
    "4,17a", "4,17rs" (= 17r–17s), "3,13de", "1,1bs" (not "s", "ss", "p" alone)."""
    if not tail or num is None:
        return False
    suffixes = {v['suffix'] for v in B.by_num.get(('EsthGr', cap, num), [])}
    if tail in suffixes:
        return True
    return tail not in ('s', 'ss', 'p', 'sp') and tail[0] in suffixes


def resolve(ref, B, ctx):
    """Fill ref with book, targets, spans (first/last ids), flags, keynote, status, reason.

    When a reference without its own siglum names a chapter or verse that does not
    exist in the book it inherits, the readings scan_prose / parse noted are tried in
    order (the current book, the last book named in the text, a verse of the previous
    chapter for "Mt 27,56; 61"); the first that resolves is kept and said in 'inferred'.
    A reference whose start exists but whose end does not ("2Mac 12,43–46") stays as
    printed: a misprint or another numbering, not another book."""
    resolve_as_printed(ref, B, ctx)
    if ref['status'] in ('resolved', 'numbering', 'comment'):
        return ref
    if ref['book'] and ref['spans'] and starts_in(B, ref['book'], ref['spans'][0]):
        return ref                              # "2Mac 7,9s; 12,43–46": a wrong end, not another book
    tries = []
    if ref.get('verse_chapter') is not None:
        spans = split_spec(ref['raw_spec'], False, ref['verse_chapter']) if ref.get('raw_spec') else None
        if spans:
            tries.append((dict(ref, spans=spans), 'verses of chapter %d' % ref['verse_chapter']))
    for alt in ref.get('fallback_books', []):
        tries.append((dict(ref, siglum=alt, current=alt is None),
                      'book %s from the text' % (alt or OSIS2SIGLA.get(ctx.get('book'), ctx.get('book')))))
    for alt, how in tries:
        alt = resolve_as_printed(dict(alt), B, ctx)
        if alt['status'] == 'resolved':
            ref.update({k: alt[k] for k in ('book', 'targets', 'ranges', 'flags', 'keynote', 'keynote_notes',
                                            'keynote_mrefs', 'keynote_verses', 'status', 'reason') if k in alt})
            ref['inferred'] = how
            break
    return ref


def starts_in(B, osis, sp):
    """The first chapter or verse of a span exists in book osis."""
    if osis not in B.books:
        return False
    if sp['v1'] is None or sp.get('from_start'):
        return sp['c1'] in B.chapters(osis)
    return bool(B.by_num.get((osis, sp['c1'], sp['v1'])))


def resolve_as_printed(ref, B, ctx):
    ref.update(book=None, targets=[], ranges=[], flags=[], keynote=False, keynote_notes=[], keynote_verses=[],
               status='unresolved', reason=None)
    if ref.get('comment'):
        ref.update(status='comment')
        return ref
    if ref.get('problem'):
        ref['reason'] = ref['problem']
        return ref
    sig = ref['siglum']
    if sig in EXTRA:
        ref['reason'] = 'extra-canonical book %s' % sig
        return ref
    if sig in MISPRINT:
        ref['reason'] = 'unknown siglum %s (%s?)' % (sig, MISPRINT[sig])
        return ref
    cands = books_for(ref, ctx)
    if not cands:
        ref['reason'] = 'unknown siglum %s' % sig if sig else 'no current book'
        return ref
    if 'EsthGr' in cands and any(greek_letters(B, c, v, t) for sp in ref['spans']
                                 for c, v, t in ((sp['c1'], sp['v1'], sp['t1']), (sp['c2'], sp['v2'], sp['t2']))):
        cands = ['EsthGr'] + [c for c in cands if c != 'EsthGr']
    if ref.get('passim') or not ref['spans']:
        ref.update(book=cands[0], status='resolved', target_book=cands[0])
        return ref
    if ref.get('to_book'):
        return resolve_across(ref, B, cands[0])
    best = None
    for osis in cands:
        got = [resolve_span(B, osis, sp) for sp in ref['spans']]
        ok = sum(1 for g in got if not g[3])
        if best is None or ok > best[0]:
            best = (ok, osis, got)
        if ok == len(got):
            break
    ok, osis, got = best
    targets, ranges, flags, keys, problems = [], [], set(), [], []
    for vs, fl, key, problem in got:
        flags |= fl
        if problem:
            problems.append(problem)
            continue
        ranges.append([vs[0]['id'], vs[-1]['id']])
        for v in vs:
            if v['id'] not in targets:
                targets.append(v['id'])
        if key:
            keys.append(key['id'])
    ref.update(book=osis, targets=targets, ranges=ranges, flags=sorted(flags), keynote_verses=keys,
               keynote=any(sp['plus'] for sp in ref['spans']),
               status='resolved' if not problems else 'partial' if targets else 'unresolved',
               reason='; '.join(problems) or None)
    if problems and ref['qualifier'] == 'volg.':
        ref['status'] = 'numbering'             # Gdt 13,21 (volg.): a Vulgate verse number
    for k in keys:
        notes, group = B.keynote(k)
        ref['keynote_notes'] += [n for n in notes if n not in ref['keynote_notes']]
        ref['keynote_mrefs'] = ref.get('keynote_mrefs', []) + [m for m in group if m not in ref.get(
            'keynote_mrefs', [])]
    return ref


# ---------------------------------------------------------------- margins

def margin_context(v):
    return dict(book=v['book'], chapter=v.get('printed_in_chapter', v['chapter']), margin=True)


BARE = r'\d+(?:[%s]\d+)?(?:[ .]\d+(?:[%s]\d+)?)*' % (DASH, DASH)     # "23", "7–8", "4 5 6", "9.11"


def vulgate_esther(r, ctx):
    """A margin of Esther pointing at 10,4–16,24: the Vulgate number of an addition
    (EsthGr 1,1a "11,2"; the Vulgate moves the Greek additions to chapters 10,4–16)."""
    if not (r['current'] and ctx['book'] in ESTER and r['spans']):
        return False
    sp = r['spans'][0]
    return sp['v1'] is not None and (sp['c1'] > 10 or sp['c1'] == 10 and sp['v1'] >= 4)


def numbering_runs(mrefs, B, parsed):
    """Ids of the bare-number margins ("\\mref{5}") that print another tradition's verse
    number. A chapter holds such a run when it has an explicit one ("32,1 (volg.)",
    "24 (TM)"; not a chapter heading such as "LXX: 36", which says nothing of the verse
    numbers), three or more bare numbers, or two close ones; elsewhere a bare number is
    a chapter of the current book (Gen 25,9 "23" = Gen 23; Jer 29,17 "24" = Jer 24)."""
    groups = defaultdict(lambda: dict(bare=[], explicit=[]))
    for m in mrefs:
        v = B.verses[m['anchor']]
        key = (v['book'], v['chapter'])
        if re.fullmatch(BARE, m['raw']):
            groups[key]['bare'].append(m)
        elif any(r['current'] and r['qualifier'] in TRADITION and not r['raw'].startswith('LXX:')
                 for r in parsed[m['id']]):
            groups[key]['explicit'].append(m)
    run = {}
    for key, g in groups.items():
        bare = g['bare']
        close = len(bare) == 2 and abs(B.rank[bare[0]['anchor']] - B.rank[bare[1]['anchor']]) <= 6 and \
            abs(int(re.match(r'\d+', bare[0]['raw']).group()) - int(re.match(r'\d+', bare[1]['raw']).group())) <= 6
        if bare and (g['explicit'] or len(bare) >= 3 or close):
            trad = {r['qualifier'] for m in g['explicit'] for r in parsed[m['id']] if r['qualifier'] in TRADITION}
            for m in bare:
                run[m['id']] = trad.pop() if len(trad) == 1 else None
    return run


def margin_links(data, B):
    links = []
    parsed = {}
    for m in data['mrefs']:
        parsed[m['id']] = parse(m['raw'], margin_context(B.verses[m['anchor']]))[0]
    runs = numbering_runs(data['mrefs'], B, parsed)
    for m in data['mrefs']:
        ctx = margin_context(B.verses[m['anchor']])
        refs = parsed[m['id']]
        if m['id'] in runs:                     # "4 5 6": one numbering entry
            refs = [dict(refs[0], raw=m['raw'], alt=m['raw'], qualifier=runs[m['id']])]
        for k, r in enumerate(refs, 1):
            vulg = vulgate_esther(r, ctx)
            if m['id'] in runs or r.get('numbering') or vulg or r['current'] and r['qualifier'] in TRADITION:
                r.update(book=None, targets=[], ranges=[], flags=[], keynote=False, keynote_notes=[],
                         status='numbering', reason=None,
                         alt=r['alt'] or re.sub(r'\s*\([^()]*\)|LXX:\s*', '', r['raw']),
                         qualifier=r['qualifier'] or ('volg.' if vulg else None))
                relation = 'numbering'
            else:
                resolve(r, B, ctx)
                relation = 'comment' if r.get('comment') else RELATION[r['sign']]
                prev = refs[k - 2] if k > 1 else None
                if r['sign'] == '=' and prev and (r['glued'] or prev['sign'] == '‖') and r['book'] and \
                        r['book'] != B.verses[m['anchor']]['book']:
                    # "‖2Cr 1,14=9,25", "‖Lc 8,16; =11,33": the doublet is of the previous
                    # reference; this verse relates to it as to the previous one
                    relation = RELATION[prev['sign']]
                    r['doublet_of'] = '%s#%d' % (m['id'], k - 1)
            links.append(record('%s#%d' % (m['id'], k), 'mref', m['id'], m['anchor'], relation, r))
    return links


def record(lid, kind, source, verse, relation, r):
    rec = dict(id=lid, kind=kind, source=source, source_verse=verse, relation=relation, raw=r['raw'],
               sign=r.get('sign'), book=r.get('book'), targets=r.get('targets', []),
               ranges=r.get('ranges', []), flags=r.get('flags', []), keynote=r.get('keynote', False),
               keynote_notes=r.get('keynote_notes', []), keynote_mrefs=r.get('keynote_mrefs', []),
               qualifier=r.get('qualifier'), alt=r.get('alt'),
               status=r['status'], reason=r.get('reason'))
    for k in ('target_book', 'doublet_of', 'inferred'):
        if r.get(k):
            rec[k] = r[k]
    if r.get('keynote_verses'):
        rec['keynote_verses'] = r['keynote_verses']
    if kind.endswith('-cites'):
        rec.update(offset=r['offset'], length=len(r['raw']), cf=r['cf'])
    return rec


# ---------------------------------------------------------------- notes and introductions

def html_offsets(text, html):
    """Map each offset of a plain text to its offset in the HTML (tags and entities
    skipped, <br> = newline); None if the two do not agree."""
    out, i = [], 0
    ent = {'&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"'}
    for ch in text:
        while i < len(html) and html[i] == '<' and not html.startswith('<br>', i):
            i = html.index('>', i) + 1
        out.append(i)
        if ch == '\n' and html.startswith('<br>', i):
            i += 4
            continue
        e = next((k for k in ent if html.startswith(k, i)), None)
        if e and ent[e] == ch:
            i += len(e)
        elif i < len(html) and html[i] in (ch, ch.translate(SUP)):     # ¹⁶ = <sup>16</sup>
            i += 1
        else:
            return None
    out.append(i)
    return out


def note_context(n, B):
    v = B.verses[n['anchor']]
    cap = v.get('printed_in_chapter', v['chapter'])
    if n['targets']:
        cap = B.verses[n['targets'][0]]['chapter']
    return dict(book=v['book'], chapter=cap, margin=False)


def cite_links(kind, source, verse, text, html, ctx, B, extra=None):
    links = []
    hmap = html_offsets(text, html) if html else None
    for k, r in enumerate(scan_prose(text, ctx), 1):
        resolve(r, B, ctx)
        rec = record('%s#c%d' % (source, k), kind, source, verse, 'cites', r)
        rec['html_offset'] = hmap[r['offset']] if hmap else None
        rec['html_end'] = hmap[r['offset'] + len(r['raw'])] if hmap else None
        rec.update(extra or {})
        links.append(rec)
    return links


def runs(B, ids):
    """[[first, last], ...]: the stretches of consecutive verses in a list of verse ids."""
    out = []
    for vid in ids:
        v = B.verses[vid]
        if out and out[-1][2] == v['book'] and B.rank[vid] == B.rank[out[-1][1]] + 1:
            out[-1][1] = vid
        else:
            out.append([vid, vid, v['book']])
    return [x[:2] for x in out]


def note_links(data, B):
    links = []
    for n in data['notes']:
        r = dict(raw=n['label'] or '', sign=n['sign'], book=B.verses[n['anchor']]['book'], targets=n['targets'],
                 ranges=runs(B, n['targets']), target_book=n['target_book'],
                 status='unresolved' if n['unresolved'] else 'resolved', reason=n['unresolved'])
        rec = record('%s#label' % n['id'], 'note-label', n['id'], n['anchor'], 'comments-on', r)
        rec.update(scope=n['scope'], target_chapters=n['target_chapters'])
        links.append(rec)
        links += cite_links('note-cites', n['id'], n['anchor'], n['text'], n['html'], note_context(n, B), B)
    return links


def intro_links(data, B):
    links = []
    for it in data['intros']:
        ctx = dict(book=it['books'][0] if len(it['books']) == 1 else None, chapter=None, margin=False)
        for p in it['paragraphs']:
            links += cite_links('intro-cites', '%s.%d' % (it['id'], p['n']), None, p['text'], p['html'], ctx, B,
                                dict(paragraph=p['n']))
    return links


# ---------------------------------------------------------------- report

def checks(links, data, B):
    """Every margin and note has a link, ids are unique, targets exist, unresolved links
    say why, and each citation's offsets point at its raw text in the plain text and HTML."""
    errors = []
    texts = {n['id']: (n['text'], n['html']) for n in data['notes']}
    texts.update({'%s.%d' % (i['id'], p['n']): (p['text'], p['html']) for i in data['intros'] for p in i['paragraphs']})
    with_links = {x['source'] for x in links}
    for coll in ('mrefs', 'notes'):
        lost = [x['id'] for x in data[coll] if x['id'] not in with_links]
        if lost:
            errors.append('%d %s without a link: %s' % (len(lost), coll, lost[:5]))
    dup = [k for k, n in Counter(x['id'] for x in links).items() if n > 1]
    if dup:
        errors.append('duplicate link ids: %s' % dup[:10])
    for x in links:
        if x['status'] not in ('resolved', 'partial', 'unresolved', 'numbering', 'comment'):
            errors.append('%s: status %s' % (x['id'], x['status']))
        bad = [t for t in x['targets'] if t not in B.verses]
        if bad:
            errors.append('%s: unknown targets %s' % (x['id'], bad[:3]))
        if x['status'] == 'resolved' and not x['targets'] and not x.get('target_book'):
            errors.append('%s: resolved without targets' % x['id'])
        if x['status'] in ('unresolved', 'partial') and not x['reason']:
            errors.append('%s: %s without a reason' % (x['id'], x['status']))
        if x['kind'].endswith('-cites'):
            text, html = texts[x['source']]
            if text[x['offset']:x['offset'] + x['length']] != x['raw']:
                errors.append('%s: offset does not match the text' % x['id'])
            if x['html_offset'] is None or re.sub(r'<[^>]+>', '', html[x['html_offset']:x['html_end']]).replace(
                    '&amp;', '&').translate(SUP) != x['raw'].translate(SUP):
                errors.append('%s: HTML offsets do not match the HTML' % x['id'])
    return errors


def pct(a, b):
    return 100.0 * a / b if b else 0.0


def summary(links):
    by_kind = defaultdict(list)
    for x in links:
        by_kind[x['kind']].append(x)
    mr = by_kind['mref']
    per_mref = defaultdict(list)
    for x in mr:
        per_mref[x['source']].append(x['status'])
    refs = [x for x in mr if x['status'] not in ('numbering', 'comment')]
    cites = by_kind['note-cites']
    icites = by_kind['intro-cites']
    keys = [x for x in links if x.get('keynote')]
    s = dict(
        mref_entries=len(per_mref),
        mref_entries_fully_resolved=sum(1 for v in per_mref.values()
                                        if all(st in ('resolved', 'numbering', 'comment') for st in v)),
        mref_items=len(mr), mref_references=len(refs),
        mref_references_resolved=sum(1 for x in refs if x['status'] == 'resolved'),
        mref_numbering=sum(1 for x in mr if x['status'] == 'numbering'),
        mref_comments=sum(1 for x in mr if x['status'] == 'comment'),
        relations=dict(Counter(x['relation'] for x in mr)),
        keynotes=len(keys), keynotes_to_margins=sum(1 for x in keys if x['keynote_mrefs']),
        keynotes_without_target=sum(1 for x in keys if x['status'] == 'resolved'
                                    and not x['keynote_notes'] and not x['keynote_mrefs']),
        flags=dict(Counter(f for x in links for f in x.get('flags', []))),
        qualifiers=dict(Counter(x['qualifier'] for x in links if x.get('qualifier'))),
        note_labels=len(by_kind['note-label']),
        note_citations=len(cites), note_citations_resolved=sum(1 for x in cites if x['status'] == 'resolved'),
        note_citations_numbering=sum(1 for x in cites if x['status'] == 'numbering'),
        notes_with_citations=len({x['source'] for x in cites}),
        intro_citations=len(icites), intro_citations_resolved=sum(1 for x in icites if x['status'] == 'resolved'),
        status=dict(Counter(x['status'] for x in links)),
        links=len(links))
    s['pct_mref_entries_fully_resolved'] = round(pct(s['mref_entries_fully_resolved'], s['mref_entries']), 2)
    s['pct_mref_references_resolved'] = round(pct(s['mref_references_resolved'], s['mref_references']), 2)
    s['pct_note_citations_resolved'] = round(pct(s['note_citations_resolved'],
                                                 s['note_citations'] - s['note_citations_numbering']), 2)
    s['pct_intro_citations_resolved'] = round(pct(s['intro_citations_resolved'], s['intro_citations']), 2)
    return s


def main(a):
    inp = a[a.index('-i') + 1] if '-i' in a else IN
    out = a[a.index('-o') + 1] if '-o' in a else OUT
    quiet = '-q' in a
    data = json.load(open(inp, encoding='utf-8'))
    B = Bibbia(data)
    links = margin_links(data, B) + note_links(data, B) + intro_links(data, B)
    errors = checks(links, data, B)
    s = summary(links)
    bad = [x for x in links if x['status'] in ('unresolved', 'partial')]
    worst = Counter((x['raw'], x['reason']) for x in bad)
    meta = dict(source=os.path.relpath(inp, C), generated_by='tools/ontologia/riferimenti.py',
                ids='<mref id>#<n> (n-th reference of the margin), <note id>#label, <note id>#c<n>, '
                    '<intro id>.<paragraph>#c<n>',
                relations=dict(related='no sign', parallel='‖ literary parallel in another book',
                               doublet='= doublet in the same book', **{
                                   'quoted-later': '/ (printed ↗) quoted or used in a later book'},
                               numbering='another tradition\'s number for this verse/chapter',
                               comment='a remark, not a reference', cites='cited in a note or intro',
                               **{'comments-on': 'the verses a note comments on'}),
                flags=dict(s='and the next verse', ss='and following (to the end of the pericope)',
                           p='and its parallels'),
                summary=s)
    dump(dict(meta=meta, links=links,
              unresolved=[dict(raw=k[0], reason=k[1], count=n) for k, n in worst.most_common()]), out)
    if not quiet:
        print('relations (margins): ' + ', '.join('%s %d' % kv for kv in Counter(
            x['relation'] for x in links if x['kind'] == 'mref').most_common()))
        print('status: ' + ', '.join('%s %d' % kv for kv in Counter(x['status'] for x in links).most_common()))
        print('most frequent unresolved (raw | reason | count):')
        for (raw, reason), n in worst.most_common(30):
            print('  %4d  %-28s %s' % (n, raw, reason))
    print('margins: %d \\mref, %.2f%% fully resolved; %d references, %.2f%% resolved; %d numbering, %d comments'
          % (s['mref_entries'], s['pct_mref_entries_fully_resolved'], s['mref_references'],
             s['pct_mref_references_resolved'], s['mref_numbering'], s['mref_comments']))
    print('notes: %d label links; %d citations in %d notes, %.2f%% resolved; intros: %d citations, %.2f%% resolved'
          % (s['note_labels'], s['note_citations'], s['notes_with_citations'], s['pct_note_citations_resolved'],
             s['intro_citations'], s['pct_intro_citations_resolved']))
    print('keynotes (+) in margins, notes and intros: %d, %d to a margin group (no note there), %d to neither'
          % (s['keynotes'], s['keynotes_to_margins'], s['keynotes_without_target']))
    for e in errors[:30]:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errors else '%d errors' % len(errors), os.path.relpath(out, C)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
