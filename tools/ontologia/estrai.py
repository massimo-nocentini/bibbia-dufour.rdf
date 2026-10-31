"""Parse the 14 proofread volumes into one JSON file, the base of the verse ontology.

usage: estrai.py [-o ontologia/build/bibbia.json] [-q]

Reads progetti/<volume>/<book>.tex (the sections listed in tools/progetti/progetti.py,
prova-paolo excluded) and writes books, divisions (\\parte), pericopes (\\sezione),
verses, BJ notes (\\footnote{\\notelabel{..} ..}), margin references (\\mref, raw
strings: the ";"-split and the reference grammar are the next stage) and the
introductions. Ids: Gen.1.1, EsthGr.1.1a (Greek Esther) / Esth.1.1 (Hebrew Esther),
Sir.Prol.3 (Sirach's prologue, chapter 0), note:Gen.1.1 (+ _2, _3 when several notes
are called from one verse), mref:Gen.1.1_1 (position in the verse).

A note or margin reference is anchored to the verse whose text contains its call; a
call printed before the first verse of a chapter (chapter notes, psalm notes) is
anchored to the next verse. Each call keeps its character offset in the verse's
plain text and HTML. Note labels are resolved to the verses that exist: ranges are
expanded in numeric order (so displaced verses, such as Nm 25,19 printed at the top
of chapter 26, fall where their number says), "s" adds the next verse, "ss" runs to
the end of the pericope, "c N" / "cc N–M" are whole chapters, a bare number is a
chapter at the head of a chapter (psalms) and a verse elsewhere, "Nota introduttiva"
is the whole book.

The checks at the end (printed, and the exit status) compare the verse counts per
chapter with tools/progetti/verifica.py, the note and margin counts with a plain
grep, look for calls without an anchor and for LaTeX left in the plain text.
"""
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(C, 'tools', 'progetti'))
from canone import OSIS, ORDINE, SIGLA, PROLOGO, numeric_order, testamento, verse_id  # noqa: E402
from progetti import PROGETTI, file_of  # noqa: E402
import verifica  # noqa: E402

OUT = os.path.join(C, 'ontologia', 'build', 'bibbia.json')
DASH = '–-'
SUP = str.maketrans('0123456789+-()', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁽⁾')
SUP_LETTER = {'a': 'ª', 'o': 'º'}

anomalies = []
unknown_macros = Counter()


def anomaly(kind, where, detail=''):
    anomalies.append(dict(kind=kind, where=where, detail=detail))


# ---------------------------------------------------------------- LaTeX helpers

def group(t, i):
    """t[i] == '{': the content of the group and the index after its '}'."""
    d = 0
    for k in range(i, len(t)):
        if t[k] == '{':
            d += 1
        elif t[k] == '}':
            d -= 1
            if d == 0:
                return t[i + 1:k], k + 1
    raise ValueError('unbalanced brace at %d: %r' % (i, t[i:i + 60]))


def optional(t, i, open_, close):
    """An optional <..> or [..] argument at t[i] (brace-aware): (content or None, next i)."""
    if i < len(t) and t[i] == open_:
        d = 0
        for k in range(i + 1, len(t)):
            if t[k] == '{':
                d += 1
            elif t[k] == '}':
                d -= 1
            elif t[k] == close and d == 0:
                return t[i + 1:k], k + 1
    return None, i


def html_escape(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def superscript(s, html):
    if html:
        return '<sup>%s</sup>' % s
    if s in SUP_LETTER:
        return SUP_LETTER[s]
    return s.translate(SUP) if re.fullmatch(r'[0-9+\-()]+', s) else s


def _inline(t, i, html, out):
    """Convert t from i up to an unmatched '}' (returned index) or the end."""
    n = len(t)
    while i < n:
        ch = t[i]
        if ch == '}':
            return i
        if ch == '{':
            sub = []
            i = _inline(t, i + 1, html, sub) + 1
            out.append(''.join(sub))
            continue
        if ch != '\\':
            j = i
            while j < n and t[j] not in '\\{}':
                j += 1
            seg = t[i:j].replace('\n', ' ')
            out.append(html_escape(seg) if html else seg)
            i = j
            continue
        if t.startswith('\\\\', i):
            i += 2
            if t.startswith('*', i):
                i += 1
            if t.startswith('\\relax', i):
                i += 6
            out.append('<br>' if html else '\n')
            continue
        m = re.match(r'\\([A-Za-z]+)\*?', t[i:])
        if not m:
            unknown_macros[t[i:i + 2]] += 1
            i += 2
            continue
        name, i = m.group(1), i + m.end()
        if name in ('relax', 'allowbreak', 'nobreak', 'noindent', 'baselineskip'):
            continue
        if name == 'looseness':
            i = re.match(r'\s*=?\s*-?\d*', t[i:]).end() + i
            continue
        if name in ('enlargethispage', 'markboth'):
            for _ in range(2 if name == 'markboth' else 1):
                i = group(t, i)[1] if t.startswith('{', i) else i
            continue
        if not t.startswith('{', i):
            unknown_macros['\\' + name] += 1
            continue
        sub = []
        i = _inline(t, i + 1, html, sub) + 1
        s = ''.join(sub)
        if name in ('emph', 'textit'):
            out.append('<em>%s</em>' % s if html else s)
        elif name in ('textbf', 'titoletto'):
            out.append('<strong>%s</strong>' % s if html else s)
        elif name == 'detto':
            out.append('«%s»' % s)
        elif name == 'textsuperscript':
            out.append(superscript(s, html))
        else:
            unknown_macros['\\' + name] += 1
            out.append(s)
    return i


def inline(t, html=False):
    """LaTeX of a verse, note or paragraph -> plain text ("\\n" at line ends) or light HTML."""
    out = []
    _inline(t, 0, html, out)
    s = ''.join(out)
    if html:
        s = re.sub(r'\s+', ' ', s)
        return re.sub(r'\s*<br>\s*', '<br>', s).strip()
    lines = [re.sub(r'\s+', ' ', ln).strip() for ln in s.split('\n')]
    return '\n'.join(ln for ln in lines if ln)


SENTINEL = 0xE000


def take_sentinels(s):
    """Remove the call markers: (text, {k: offset}), without doubled spaces."""
    out, where, size = [], {}, 0

    def pop():
        nonlocal size
        size -= len(out.pop())
        for k in where:                 # a call after the removed space stays before the break
            where[k] = min(where[k], size)

    for tok in re.findall(r'<br>|.', s, re.S):
        o = ord(tok) - SENTINEL if len(tok) == 1 else -1
        if 0 <= o < 0x1000:
            where[o] = size
            continue
        brk = tok in ('\n', '<br>')
        if brk and out and out[-1] == ' ':
            pop()
        if (brk or tok == ' ') and (not out or out[-1] in (' ', '\n', '<br>')):
            continue
        out.append(tok)
        size += len(tok)
    while out and out[-1] in (' ', '\n', '<br>'):
        pop()
    return ''.join(out), where


def convert(latex):
    """Verse LaTeX with call markers -> (plain, html, {k: plain offset}, {k: html offset})."""
    plain, at = take_sentinels(inline(latex))
    html, hat = take_sentinels(inline(latex, html=True))
    return plain, html, at, hat


# ---------------------------------------------------------------- book parser

class Libro:
    """State of the scan of one book file."""

    def __init__(self, sid, volume, path):
        self.sid, self.osis, self.volume, self.path = sid, OSIS[sid], volume, path
        self.title = None
        self.cap = None          # chapter in progress (0 = Sirach's prologue)
        self.chapters = []       # chapter numbers in print order
        self.page = None
        self.poesia = False
        self.verses = []         # dicts with 'buf' (LaTeX with markers) and 'calls'
        self.cur = None          # verse in progress
        self.pending = dict(buf=[], calls=[])   # text and calls waiting for the next verse
        self.stack = []          # open inline groups ('\\emph{', '{'), reopened in the next verse
        self.heads = []          # \sezione / \parte waiting for their first verse
        self.acrostic = []       # Hebrew letters printed before the next verse
        self.pericopes, self.divisions = [], []

    def sink(self):
        return self.cur if self.cur is not None else self.pending

    def text(self, s):
        self.sink()['buf'].append(s)
        if not s.strip():
            return
        if self.poesia:
            self.sink()['poetry'] = True
        if self.cur is not None and self.heads:     # a heading printed inside a verse
            for h in self.heads:
                h['first'], h['mid_verse'] = self.cur, True
            self.heads = []

    def close_verse(self):
        if self.cur is None:
            return
        self.cur['buf'].append('}' * len(self.stack))
        self.cur = None
        self.pending = dict(buf=[''.join(self.stack)], calls=[])

    def carry_margins(self):
        """The margin references ending the verse in progress that stand beside the line
        where the next verse begins: the \\mref goes after the first word of its printed
        line, so one followed by at most CARRY_WORDS words of its verse, with no line
        break of poetry and no heading in between, is printed on a line that is mostly
        the next verse's (a word-overlap count of their targets with both verses agrees:
        README, stage 1). Taken out of the verse in progress, in print order."""
        v = self.cur
        if v is None or self.heads:
            return []
        moved = []
        while v['calls'] and v['calls'][-1]['kind'] == 'mref':
            k = len(v['calls']) - 1
            at = v['buf'].index(chr(SENTINEL + k))
            tail = ''.join(v['buf'][at + 1:])
            if '\\\\' in tail:
                break
            words = re.sub(r'\\[A-Za-z]+\*?|[{}\[\]\uE000-\uEFFF]', ' ', tail).split()
            if len(words) > CARRY_WORDS:
                break
            del v['buf'][at]
            c = v['calls'].pop()
            c.update(carried_from=v, tail=' '.join(words))
            moved.insert(0, c)
        return moved

    def open_verse(self, label):
        carried = self.carry_margins()
        self.close_verse()
        m = re.fullmatch(r'(?:(\d+),)?(\d+)([a-z]*)', label)
        if not m:
            raise ValueError('%s: odd verse label %r' % (self.sid, label))
        cap = int(m.group(1)) if m.group(1) else self.cap
        if cap is None:
            raise ValueError('%s: verse %s before any chapter' % (self.sid, label))
        v = dict(cap=cap, num=int(m.group(2)), suffix=m.group(3), label=label,
                 printed_in=self.cap, page=self.page, poetry=self.poesia or self.pending.get('poetry', False),
                 buf=self.pending['buf'], calls=self.pending['calls'])
        if self.acrostic:
            v['acrostic'], self.acrostic = self.acrostic, []
        if m.group(1):
            anomaly('verse-displaced', '%s %s' % (self.sid, label),
                    'verse %d,%d printed in chapter %s; id keeps its own chapter' % (cap, v['num'], self.cap))
        before = re.sub('[\uE000-\uEFFF\\[]', '', inline(''.join(v['buf'])))
        if before.strip():
            anomaly('text-before-verse', '%s %s,%s' % (self.sid, cap, label), before[:80])
        if carried:                     # sentinels renumbered: the carried calls come first
            calls = carried + v['calls']
            ren = {SENTINEL + k: SENTINEL + len(carried) + k for k in range(len(v['calls']))}
            v['buf'] = [chr(SENTINEL + k) for k in range(len(carried))] + [
                chr(ren[ord(x)]) if len(x) == 1 and ord(x) in ren else x for x in v['buf']]
            v['calls'] = calls
        self.pending = dict(buf=[], calls=[])
        self.verses.append(v)
        self.cur = v
        for h in self.heads:
            h['first'] = v
        self.heads = []

    def call(self, kind, content):
        sink = self.sink()
        k = len(sink['calls'])
        sink['buf'].append(chr(SENTINEL + k))
        sink['calls'].append(dict(kind=kind, latex=content, page=self.page, pre=self.cur is None))


# \acrostico{Alef}: a Hebrew letter printed before a stanza of an alphabetic poem (Sal 9-10, 25, 34,
# 37, 111, 112, 119, 145; Pr 31,10-31; Lam 1-4; Na 1); \acrostico{(Mem)}, printed in parentheses: the
# letter is missing in the Hebrew text. Stored as the name ('Mem') and, for the bracketed ones, a flag
# (acrostic_brackets).
ACROSTICO = re.compile(r'(\()?([A-Za-zŚŠ]+)(\))?$')
# a margin reference followed by at most this many words of its verse belongs to the next one
CARRY_WORDS = 2
BEFORE_VERSE = re.compile(r'\s*(?:\\pagina\{\d+\}\s*|\\begin\{poesia\}\s*|\\end\{poesia\}\s*)*\\vs\{')

INLINE_MACROS = {'emph', 'detto', 'textsuperscript', 'textit', 'textbf', 'titoletto', 'relax',
                 'allowbreak', 'nobreak'}


def scan_book(sid, volume, path):
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'(?<!\\)%.*', '', t)
    b = Libro(sid, volume, path)
    i, n = 0, len(t)
    while i < n:
        j = i
        while j < n and t[j] not in '\\{}':
            j += 1
        if j > i:
            b.text(t[i:j])
            i = j
            continue
        ch = t[i]
        if t.startswith('{[}', i):
            rest = t[i + 3:].lstrip()
            if rest.startswith('\\vs{'):        # bracket around an omitted or bracketed verse
                b.close_verse()
                b.pending['buf'].append('[')
                i += 3
                continue
            b.text('[')
            i += 3
            continue
        if t.startswith('{]}', i):
            b.text(']')
            i += 3
            continue
        if ch == '{':
            b.stack.append('{')
            b.sink()['buf'].append('{')
            i += 1
            continue
        if ch == '}':
            if not b.stack:
                raise ValueError('%s: unmatched } at %d' % (sid, i))
            b.stack.pop()
            b.sink()['buf'].append('}')
            i += 1
            continue
        if t.startswith('\\\\', i):
            m = re.match(r'\\\\\*?(\\relax)?', t[i:])
            b.sink()['buf'].append('\\\\')
            i += m.end()
            continue
        m = re.match(r'\\([A-Za-z]+)(\*?)', t[i:])
        if not m:
            raise ValueError('%s: odd escape %r' % (sid, t[i:i + 10]))
        name, i = m.group(1), i + m.end()
        if name == 'libro':
            b.title, i = group(t, i)
            b.title = inline(b.title)
        elif name == 'capitolo':
            arg, i = group(t, i)
            b.close_verse()
            b.cap = int(arg)
            b.chapters.append(b.cap)
        elif name == 'vs':
            arg, i = group(t, i)
            if b.cap is None and sid == 'Sir':
                b.cap = 0
                b.chapters.append(0)
            b.open_verse(arg)
        elif name in ('sezione', 'parte'):
            cap, i = optional(t, i, '<', '>')
            short, i = optional(t, i, '[', ']')
            title, i = group(t, i)
            h = dict(kind=name, title=inline(title), title_html=inline(title, True),
                     short=inline(short) if short else None, opens_chapter=int(cap) if cap else None,
                     page=b.page, first=None, mid_verse=False)
            (b.pericopes if name == 'sezione' else b.divisions).append(h)
            b.heads.append(h)
        elif name == 'pagina':
            arg, i = group(t, i)
            b.page = int(arg)
        elif name in ('footnote', 'mref'):
            arg, i = group(t, i)
            b.call(name, arg)
        elif name in ('begin', 'end'):
            arg, i = group(t, i)
            if arg != 'poesia':
                raise ValueError('%s: environment %s' % (sid, arg))
            b.poesia = name == 'begin'
            b.sink()['buf'].append('\\\\')
        elif name == 'acrostico':
            arg, i = group(t, i)
            m = ACROSTICO.match(arg)
            if not m or bool(m.group(1)) != bool(m.group(3)):
                raise ValueError('%s: \\acrostico{%s}' % (sid, arg))
            arg = (m.group(2), bool(m.group(1)))
            if BEFORE_VERSE.match(t, i) or b.cur is None:
                b.acrostic.append((arg, 1))     # it heads the next verse (its first line)
            else:                               # it heads a later line of this verse
                lines = [x for x in inline(''.join(b.cur['buf'])).split('\n') if x.strip()]
                b.cur.setdefault('acrostic', []).append((arg, len(lines) + 1))
        elif name == 'enlargethispage':
            i = group(t, i)[1]
        elif name in INLINE_MACROS:
            if t.startswith('{', i):
                b.stack.append('\\%s{' % name)
                b.sink()['buf'].append('\\%s{' % name)
                i += 1
            else:
                b.sink()['buf'].append('\\%s ' % name)
        else:
            raise ValueError('%s: unknown macro \\%s' % (sid, name))
    b.close_verse()
    if b.pending['calls']:
        anomaly('calls-after-last-verse', sid, '%d calls attached to the last verse' % len(b.pending['calls']))
        last = b.verses[-1]
        for c in b.pending['calls']:
            last['buf'].append(chr(SENTINEL + len(last['calls'])))
            last['calls'].append(c)
    if inline(''.join(b.pending['buf'])).strip():
        anomaly('text-after-last-verse', sid, inline(''.join(b.pending['buf']))[:80])
    for h in b.heads:
        anomaly('heading-without-verse', sid, h['title'])
    return b


# ---------------------------------------------------------------- verses, structure

def build_verses(b, order0):
    """Plain/HTML text, ids and call offsets for every verse of a scanned book."""
    out = []
    for k, v in enumerate(b.verses):
        latex = ''.join(v['buf'])
        plain, html, at, hat = convert(latex)
        vid = verse_id(b.osis, v['cap'], v['label'].split(',')[-1])
        rec = dict(id=vid, book=b.osis, chapter=v['cap'], verse=v['num'], suffix=v['suffix'],
                   label=v['label'], text=plain, html=html, poetry=bool(v['poetry']),
                   page=v['page'], pericope=None, order=order0 + k)
        if v['printed_in'] != v['cap']:
            rec['printed_in_chapter'] = v['printed_in']
        if v.get('acrostic'):
            rec['acrostic'] = [a for (a, _), _ in v['acrostic']]
            rec['acrostic_lines'] = [n for _, n in v['acrostic']]
            if any(p for (_, p), _ in v['acrostic']):
                rec['acrostic_brackets'] = [p for (_, p), _ in v['acrostic']]
        bare = plain.strip()
        if bare in ('', '[]', '[ ]'):
            rec['omitted'] = True
            rec['text'] = rec['html'] = ''
            at, hat = dict.fromkeys(at, 0), dict.fromkeys(hat, 0)
            anomaly('verse-omitted', vid, 'number printed%s, no text (CEI omits it)' %
                    (' in brackets' if bare else ''))
        elif bare.startswith('[') and bare.endswith(']'):
            rec['bracketed'] = True
            anomaly('verse-bracketed', vid, 'whole verse printed in brackets')
        v['rec'], v['at'], v['hat'] = rec, at, hat
        out.append(rec)
    if b.sid == 'Sal':
        superscriptions(out)
    return out


def superscriptions(verses):
    """Psalm titles: the italic run that opens a psalm (verse 1, and 2 when 1 is all title)."""
    by_cap = defaultdict(list)
    for v in verses:
        by_cap[v['chapter']].append(v)
    for vs in by_cap.values():
        for v in vs[:3]:
            m = re.match(r'(?:<em>[^<]*</em>(?: |<br>)?)+', v['html'])
            if not m:
                break
            title = re.sub(r'<[^>]+>', '', m.group(0).replace('<br>', '\n')).strip()
            v['superscription'] = title
            if title != v['text']:
                break


def part_level(title, has_roman, prev):
    w = title.split()[0] if title.split() else ''
    if re.fullmatch(r'[IVXL]+\.', w):
        return 1
    if re.fullmatch(r'\d+\.', w):
        return 2
    if re.fullmatch(r'[A-Z]\.', w):
        return 3
    return prev if has_roman and prev else 1


def build_structure(b, verses):
    """Divisions and pericopes with first/last verse; verse -> pericope."""
    pos = {id(v): k for k, v in enumerate(b.verses)}
    last = len(verses) - 1
    peri, used = [], Counter()
    for h in b.pericopes:
        if h['first'] is None:
            continue
        k = pos[id(h['first'])]
        if h['page'] is None:              # heading before the book's first \pagina
            h['page'] = verses[k]['page']
        base = 'peri:' + verses[k]['id']
        used[base] += 1
        pid = base if used[base] == 1 else '%s_%d' % (base, used[base])
        peri.append(dict(id=pid, book=b.osis, title=h['title'], title_html=h['title_html'],
                         short=h['short'], opens_chapter=h['opens_chapter'], page=h['page'],
                         first=verses[k]['id'], mid_verse=h['mid_verse'], _k=k))
        if h['mid_verse']:
            anomaly('pericope-mid-verse', pid, 'heading printed inside verse %s' % verses[k]['id'])
    for a, nxt in zip(peri, peri[1:] + [None]):
        e = last if nxt is None else (nxt['_k'] if nxt['mid_verse'] else nxt['_k'] - 1)
        a['last'] = verses[max(e, a['_k'])]['id']
        for k in range(a['_k'], e + 1):
            if verses[k]['pericope'] is None:
                verses[k]['pericope'] = a['id']
    divs, prev = [], None
    has_roman = any(re.match(r'[IVXL]+\. ', h['title']) for h in b.divisions)
    for n, h in enumerate(b.divisions, 1):
        if h['first'] is None:
            continue
        prev = part_level(h['title'], has_roman, prev)
        page = h['page'] if h['page'] is not None else verses[pos[id(h['first'])]]['page']
        divs.append(dict(id='div:%s.%d' % (b.osis, n), book=b.osis, title=h['title'],
                         title_html=h['title_html'], short=h['short'], level=prev, page=page,
                         first=verses[pos[id(h['first'])]]['id'], parent=None, _k=pos[id(h['first'])]))
    for x, d in enumerate(divs):
        e = last
        for nxt in divs[x + 1:]:
            if nxt['level'] <= d['level']:
                e = nxt['_k'] - 1
                break
        d['last'] = verses[max(e, d['_k'])]['id']
        for up in reversed(divs[:x]):
            if up['level'] < d['level']:
                d['parent'] = up['id']
                break
    for x in peri + divs:
        del x['_k']
    return divs, peri


# ---------------------------------------------------------------- note labels

class Indice:
    """The verses of one book, for resolving note labels."""

    def __init__(self, verses):
        self.verses = verses
        self.by_num = defaultdict(list)
        for v in verses:
            self.by_num[(v['chapter'], v['verse'])].append(v)
        for k, vs in self.by_num.items():
            self.by_num[k] = numeric_order(vs)
        self.key = {}
        for (cap, num), vs in self.by_num.items():
            for x, v in enumerate(vs):
                self.key[v['id']] = (cap, num, x)
        self.sorted = sorted(verses, key=lambda v: self.key[v['id']])
        self.rank = {v['id']: r for r, v in enumerate(self.sorted)}
        self.by_chapter = defaultdict(list)
        for v in self.sorted:
            self.by_chapter[v['chapter']].append(v)
        self.chapters = sorted(self.by_chapter)

    def point(self, cap, num, letters, end=False):
        """Verses one end of a label designates (None if no such verse)."""
        vs = self.by_num.get((cap, num))
        if not vs:
            return None
        if not letters:
            bare = [v for v in vs if not v['suffix']]
            return bare or vs
        exact = [v for v in vs if v['suffix'] == letters]
        if exact:
            return exact
        lettered = [v for v in vs if v['suffix']]
        if lettered and len(letters) == 1:
            sel = [v for v in lettered if (v['suffix'] <= letters if end else v['suffix'] >= letters)]
            if sel:
                return [sel[-1]] if end else [sel[0]]
            return None
        return vs                       # a part of a verse (1,2b): the whole verse

    def between(self, a, b):
        return self.sorted[self.rank[a['id']]:self.rank[b['id']] + 1]

    def chapter(self, cap):
        return self.by_chapter.get(cap, [])


def parse_points(spec, cap):
    """'2,4b–25' -> [((2,4,'b'), (2,25,''), flag)]; flag 's'/'ss' = and the next / following."""
    m = re.fullmatch(r'(?:(\d+),)?(.+)', spec)
    if m.group(1):
        cap = int(m.group(1))
    out = []
    for seg in m.group(2).split('.'):
        parts = re.split('[%s]' % DASH, seg, maxsplit=1)
        a, z = parts[0], parts[1] if len(parts) > 1 else ''
        ma = re.fullmatch(r'(\d+)([a-z]*)', a)
        if not ma:
            return None
        start = (cap, int(ma.group(1)), ma.group(2))
        if not z:
            if start[2] in ('s', 'ss'):
                out.append(((cap, start[1], ''), (cap, start[1], ''), start[2]))
            else:
                out.append((start, start, ''))
            continue
        mz = re.fullmatch(r'(?:(\d+),)?(\d+)?([a-z]*)', z)
        if not mz or not (mz.group(2) or mz.group(3)):
            return None
        zc = int(mz.group(1)) if mz.group(1) else start[0]
        zn = int(mz.group(2)) if mz.group(2) else start[1]
        out.append((start, (zc, zn, mz.group(3)), ''))
        cap = zc
    return out


def resolve_label(label, anchor, idx, chap_start, one_chapter):
    """(scope, targets, chapters, problem) for a note label as printed.

    chap_start: the call stands before the first verse of a chapter."""
    cap = anchor['chapter']
    if label is None:
        return 'chapter', idx.chapter(cap), [cap], None
    lab = label.strip()
    if lab == 'Nota introduttiva':
        return 'book', [], [], None
    m = re.fullmatch(r'(c{1,2}) (\d+)(?:[%s](\d+))?' % DASH, lab)
    if m:
        caps = list(range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1))
        tg = [v for c in caps for v in idx.chapter(c)]
        bad = [c for c in caps if c not in idx.chapters]
        return 'chapter', tg, caps, ('no chapter %s' % bad if bad else None)
    m = re.fullmatch(r'(?:cc|c|vv|v) (.+)', lab)
    spec = m.group(1) if m else lab
    if not m and re.fullmatch(r'[\d%s]+' % DASH, spec) and not one_chapter and chap_start:
        a = re.split('[%s]' % DASH, spec)
        caps = list(range(int(a[0]), int(a[-1]) + 1))
        return 'chapter', [v for c in caps for v in idx.chapter(c)], caps, None
    pts = parse_points(spec, cap)
    if pts is None:
        return 'verses', [], [], 'label not understood'
    tg, problems = [], []
    for start, end, flag in pts:
        exact = [v for v in idx.by_num.get(start[:2], []) if flag and v['suffix'] == flag]
        if exact:                       # Est-gr 8,12s is a verse, not "and the next"
            a = z = exact
            flag = ''
        else:
            a = idx.point(*start)
            z = a if start == end else idx.point(*end, end=True)
        if a is None or z is None:
            problems.append('no verse %d,%d%s' % (start if a is None else end))
            continue
        lo, hi = a[0], z[-1]
        if flag == 's':
            nxt = idx.point(start[0], start[1] + 1, '')
            hi = nxt[-1] if nxt else hi
        elif flag == 'ss':              # to the end of the pericope, within the chapter
            same = idx.chapter(lo['chapter'])[idx.chapter(lo['chapter']).index(lo):]
            stop = [v for v in same if lo['pericope'] and v['pericope'] == lo['pericope']] or same
            hi = stop[-1]
        if idx.key[hi['id']] < idx.key[lo['id']]:
            problems.append('reversed range')
            lo, hi = hi, lo
        for v in idx.between(lo, hi):
            if v not in tg:
                tg.append(v)
    return 'verses', tg, [], ('; '.join(problems) or None)


def word_before(text, off):
    w = re.findall(r'\S+', text[:off])
    return w[-1].strip('«»“”‘’"()[],.;:!?') if w else None


def build_calls(b, verses, idx):
    notes, mrefs, seen = [], [], Counter()
    one_chapter = len([c for c in b.chapters if c]) == 1
    for v in b.verses:
        rec, at, hat = v['rec'], v['at'], v['hat']
        nm = 0
        for k, c in enumerate(v['calls']):
            off, hoff = at.get(k), hat.get(k)
            base = dict(anchor=rec['id'], offset=off, html_offset=hoff, word=word_before(rec['text'], off or 0),
                        page=c['page'])
            if c['kind'] == 'mref':
                nm += 1
                m = dict(id='mref:%s_%d' % (rec['id'], nm), position=nm,
                         raw=re.sub(r'\s+', ' ', c['latex']).strip(), **base)
                if c.get('carried_from'):
                    m['printed_in_verse'] = c['carried_from']['rec']['id']
                    anomaly('mref-before-verse', m['id'], '{%s} printed in %s%s, before verse %s: anchored to it'
                            % (m['raw'], m['printed_in_verse'], ' after «%s»' % c['tail'] if c['tail'] else '',
                               rec['label']))
                mrefs.append(m)
                continue
            seen[rec['id']] += 1
            nid = 'note:' + rec['id'] + ('' if seen[rec['id']] == 1 else '_%d' % seen[rec['id']])
            m = re.match(r'\s*\\notelabel\{([^{}]*)\}', c['latex'])
            label, body = (m.group(1), c['latex'][m.end():]) if m else (None, c['latex'])
            sign = None
            lab = label
            if lab and lab.startswith('•'):
                sign, lab = '•', lab[1:].strip()
            scope, tg, caps, problem = resolve_label(lab, rec, idx, c['pre'], one_chapter)
            if label is None:
                anomaly('note-without-label', nid, 'unlabelled note (%s): taken as a note on chapter %s'
                        % (inline(body)[:40], PROLOGO if rec['chapter'] == 0 else rec['chapter']))
            if problem:
                anomaly('note-label-unresolved', nid, '{%s}: %s' % (label, problem))
            elif scope == 'chapter' and rec['chapter'] not in caps:
                anomaly('chapter-note-anchor', nid, '{%s} stands before %s, the first verse printed in '
                        'chapter %s' % (label, rec['label'], v['printed_in']))
            elif scope == 'verses' and not c['pre'] and rec['id'] not in {x['id'] for x in tg}:
                anomaly('note-label-away-from-anchor', nid, '{%s} called from %s' % (label, rec['label']))
            notes.append(dict(id=nid, label=label, sign=sign, scope=scope,
                              targets=[x['id'] for x in tg],
                              target_chapters=['%s.%s' % (b.osis, PROLOGO if x == 0 else x) for x in caps],
                              target_book=b.osis if scope == 'book' else None,
                              unresolved=problem, text=inline(body).strip(), html=inline(body, True),
                              latex=c['latex'], **base))
    return notes, mrefs


# ---------------------------------------------------------------- introductions

def build_intro(sid, volume, path, books):
    t = open(path, encoding='utf-8').read()
    t = re.sub(r'(?<!\\)%.*', '', t)
    title, heading, paras, page = None, None, [], None
    m = re.match(r'\s*\\libro\*', t)
    if m:
        title, k = group(t, m.end())
        t = t[group(t, k)[1]:]
        title = inline(title)
    for block in re.split(r'\n\s*\n', t):
        block = block.strip()
        m = re.match(r'\\parte\{', block)
        if m:
            h, k = group(block, m.end() - 1)
            heading = inline(h)
            block = block[k:].strip()
        if not block:
            continue
        pages = [int(x) for x in re.findall(r'\\pagina\{(\d+)\}', block)]
        start = pages[0] if block.startswith('\\pagina') else page
        page = pages[-1] if pages else page
        block = re.sub(r'\\pagina\{\d+\}', '', block)
        tit = None
        mt = re.match(r'(?:\\markboth\{[^{}]*\}\{[^{}]*\})?\\titoletto\{', block)
        if mt:
            tit = inline(group(block, mt.end() - 1)[0]).strip()
        paras.append(dict(n=len(paras) + 1, page=start, titoletto=tit, text=inline(block),
                          html=inline(block, html=True)))
    return dict(id=sid, volume=volume, title=title, heading=heading, books=books, paragraphs=paras)


# ---------------------------------------------------------------- checks

def check_counts(b, verses):
    """Verses per chapter against verifica.check() (labels \\d+[a-z]* only, by printed chapter)."""
    _, _, seq = verifica.check(b.path)
    ours = Counter(v['printed_in'] for v in b.verses if re.fullmatch(r'\d+[a-z]*', v['label']))
    theirs = {(0 if k is None else k): len(x) for k, x in seq.items()}
    bad = []
    for c in sorted(set(ours) | set(theirs)):
        if ours.get(c, 0) != theirs.get(c, 0):
            bad.append('%s: ours %d, verifica %d' % (c, ours.get(c, 0), theirs.get(c, 0)))
    return bad


def offsets_agree(v, off, hoff):
    """The HTML before a call, without tags, is the plain text before it."""
    h = v['html'][:hoff]
    if h.count('<') != h.count('>'):
        return False
    h = re.sub(r'<br>', '\n', h)
    h = re.sub(r'<[^>]+>', '', h).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    return h == v['text'][:off]


def grep_count(path, what):
    return open(path, encoding='utf-8').read().count('\\%s{' % what)


def ocr_counts():
    out = {}
    for name in ('notes.tsv', 'xrefs.tsv'):
        n = Counter()
        with open(os.path.join(C, 'data', name), encoding='utf-8') as f:
            next(f)
            for ln in f:
                n[ln.split('\t', 1)[0]] += 1
        out[name] = n
    return out


# ---------------------------------------------------------------- main

def dump(data, path):
    """One record per line, so that rebuilt files diff well."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{\n')
        keys = list(data)
        for n, k in enumerate(keys):
            v = data[k]
            f.write('%s: ' % json.dumps(k))
            if isinstance(v, list):
                f.write('[\n' + ',\n'.join(json.dumps(x, ensure_ascii=False) for x in v) + '\n]')
            else:
                f.write(json.dumps(v, ensure_ascii=False, indent=1))
            f.write(',\n' if n < len(keys) - 1 else '\n')
        f.write('}\n')


def main(a):
    out = a[a.index('-o') + 1] if '-o' in a else OUT
    quiet = '-q' in a
    manifest = {s['id']: s for s in json.load(open(os.path.join(C, 'data', 'manifest.json'), encoding='utf-8'))}
    books, verses, notes, mrefs, divs, peris, intros = [], [], [], [], [], [], []
    errors, stats = [], []
    grep = Counter()
    for p in PROGETTI:
        if p.get('prova'):
            continue
        secs = p['sections']
        for x, sid in enumerate(secs):
            path = os.path.join(C, 'progetti', p['nome'], file_of(sid, p) + '.tex')
            rel = os.path.relpath(path, C)
            if sid.startswith('intro-'):
                follow = []
                for s in secs[x + 1:]:
                    if s.startswith('intro-'):
                        break
                    follow.append(OSIS[s])
                if not follow:
                    follow = [OSIS[s] for s in secs if not s.startswith('intro-')]
                intro = build_intro(sid, p['nome'], path, follow)
                intro['file'] = rel
                intros.append(intro)
                continue
            b = scan_book(sid, p['nome'], path)
            vs = build_verses(b, len(verses) + 1)
            d, pe = build_structure(b, vs)
            idx = Indice(vs)
            no, mr = build_calls(b, vs, idx)
            chapters = defaultdict(list)
            for v in sorted(vs, key=lambda v: (v['chapter'], idx.key[v['id']])):
                chapters[v['chapter']].append(v['id'])
            books.append(dict(osis=b.osis, id=sid, siglum=SIGLA[sid], title=b.title,
                              title_long=manifest[sid]['title'], volume=p['nome'], order=ORDINE[sid],
                              testament=testamento(sid), file=rel,
                              chapters=[dict(n=c, label=PROLOGO if c == 0 else str(c), verses=chapters[c])
                                        for c in sorted(chapters)]))
            verses += vs
            notes += no
            mrefs += mr
            divs += d
            peris += pe
            # checks for this book
            for e in check_counts(b, vs):
                errors.append('%s verses per chapter %s' % (sid, e))
            nch = len([c for c in chapters if c])
            if nch != manifest[sid]['chapters']:
                errors.append('%s: %d chapters, manifest says %s' % (sid, nch, manifest[sid]['chapters']))
            for what, got in (('footnote', len(no)), ('mref', len(mr))):
                g = grep_count(path, what)
                grep[what] += g
                if g != got:
                    errors.append('%s: %d \\%s by grep, %d extracted' % (sid, g, what, got))
            stats.append((sid, b.osis, nch, len(vs), len(no), len(mr), len(pe), len(d),
                          sum(v['poetry'] for v in vs), sum(1 for v in vs if v.get('omitted'))))
    books.sort(key=lambda b: b['order'])
    # global checks
    for name, coll in (('verse', verses), ('note', notes), ('mref', mrefs), ('pericope', peris),
                       ('division', divs)):
        dup = [k for k, n in Counter(x['id'] for x in coll).items() if n > 1]
        if dup:
            errors.append('duplicate %s ids: %s' % (name, dup[:10]))
    vmap = {v['id']: v for v in verses}
    for coll in (notes, mrefs):
        for x in coll:
            if not x['anchor'] or x['offset'] is None or x['html_offset'] is None:
                errors.append('%s without anchor or offset' % x['id'])
            elif not offsets_agree(vmap[x['anchor']], x['offset'], x['html_offset']):
                errors.append('%s: plain and HTML offsets disagree' % x['id'])
    texts = [(v['id'], v['text']) for v in verses] + [(x['id'], x['text']) for x in notes] + \
        [(i['id'], p['text']) for i in intros for p in i['paragraphs']] + \
        [(x['id'], x['title']) for x in peris + divs] + [(b['id'], b['title']) for b in books]
    leftovers = [(k, s) for k, s in texts if re.search('[\\\\{}\uE000-\uEFFF]', s or '')]
    for k, s in leftovers[:20]:
        errors.append('LaTeX left in %s: %r' % (k, s[:80]))
    htmls = [x['html'] for x in verses + notes] + [p['html'] for i in intros for p in i['paragraphs']]
    if any('\\' in h for h in htmls):
        errors.append('backslash left in HTML')
    if unknown_macros:
        errors.append('unknown macros: %s' % dict(unknown_macros))

    totals = dict(books=len(books), chapters=sum(len(b['chapters']) for b in books),
                  verses=len(verses), notes=len(notes), mrefs=len(mrefs), pericopes=len(peris),
                  divisions=len(divs), intros=len(intros),
                  intro_paragraphs=sum(len(i['paragraphs']) for i in intros),
                  poetry_verses=sum(v['poetry'] for v in verses),
                  omitted_verses=sum(1 for v in verses if v.get('omitted')),
                  psalm_superscriptions=sum(1 for v in verses if v.get('superscription')),
                  acrostic_letters=sum(len(v.get('acrostic', [])) for v in verses),
                  grep_footnotes=grep['footnote'], grep_mrefs=grep['mref'],
                  anomalies=dict(Counter(x['kind'] for x in anomalies)))
    meta = dict(source='progetti/<volume>/*.tex (La Bibbia di Gerusalemme, EDB: CEI 2008 + BJ notes)',
                generated_by='tools/ontologia/estrai.py',
                ids=dict(verse='<OSIS>.<chapter>.<verse label>; Sir.Prol.<n> = prologue (chapter 0); '
                                'EsthGr = Greek Esther (Est-gr), Esth = Hebrew Esther (Est-ebr)',
                         note='note:<anchor verse id>[_<n>]', mref='mref:<anchor verse id>_<position>',
                         pericope='peri:<first verse id>[_<n>]', division='div:<OSIS>.<n>'),
                page='printed page number (PDF page = page + 33)', totals=totals)
    data = dict(meta=meta, books=books, divisions=divs, pericopes=peris, verses=verses, notes=notes,
                mrefs=mrefs, intros=intros, anomalies=anomalies)
    dump(data, out)

    ocr = ocr_counts()
    if not quiet:
        print('book    osis    chap verses notes(ocr)   mrefs(ocr)  peric divis poetry omit')
        for s in stats:
            print('%-7s %-7s %4d %6d %5d(%5d) %5d(%5d) %5d %5d %6d %4d' % (
                s[0], s[1], s[2], s[3], s[4], ocr['notes.tsv'][s[0]], s[5], ocr['xrefs.tsv'][s[0]],
                s[6], s[7], s[8], s[9]))
        print()
        kinds = defaultdict(list)
        for x in anomalies:
            kinds[x['kind']].append(x)
        for k, xs in sorted(kinds.items()):
            print('anomaly %-28s %5d   e.g. %s' % (k, len(xs), '; '.join(
                '%s %s' % (x['where'], x['detail']) for x in xs[:3])[:300]))
        print()
    print('totals: ' + ', '.join('%s %s' % (k, v) for k, v in totals.items() if k != 'anomalies'))
    print('grep: \\footnote %d, \\mref %d; extracted notes %d, mrefs %d' % (
        grep['footnote'], grep['mref'], len(notes), len(mrefs)))
    for e in errors:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errors else '%d errors' % len(errors), os.path.relpath(out, C)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
