"""Direct speech and quoted sentences: the text between « and », for the ontology and the Tufte edition.

usage: virgolette.py [-q]      (stage 2e: the four JSON files -> ontologia/build/discorsi.json)

One detector, two readers. The language rules live here; tools/tufte/discorsi.py walks the LaTeX of the
Tufte edition and only wraps what this module matched in \\discorso{...}, the ontology (rdf.py) and the
explorer (esploratore.py) read the HTML of the JSON files of stages 1 and 2c with the same rules:

- a *scope* is matched on its own: the text of a book (all its verses in the printed order, the headings
  apart), each note, an introduction (all its paragraphs), a text of the front matter, an item of the
  canon, the edition, an entry of the chronology or of an index;
- in a scope « opens and » closes the last one open (stack matching), so a quotation inside a quotation
  stays part of it (Dt 5,1-26,19: Moses' discourse quotes the Lord); only the *outermost* pairs set the
  italic, a pair inside another is nested (its parent the innermost pair around it);
- a « still open at the end of the scope and a » with none open are *unbalanced*: reported and left as
  printed, nothing is guessed across them (Sir 16,22, Am 7,17), and the pairs after them are matched as
  if they were not there;
- guillemets already in italic (inside \\emph or \\detto in the LaTeX, inside <em> in the HTML) and those
  of headings or of arguments not walked are skipped: they are not events;
- a run of a quotation that is only italic text already («\\emph{tohû}») is not set again; a run is a
  stretch of a quotation between two things that stay upright (a verse number, a margin reference, a note
  call, a poetry line end, a paragraph end; in the LaTeX also a footnote, a heading, an environment).

In the HTML of the ontology a \\detto of the volumes is «...» (estrai.py): a quotation of a note or an
introduction like the typed ones, as the volumes print it (italic in guillemets). The Tufte reader leaves
\\detto to its macro (already italic), so in the notes and introductions it counts only the typed pairs.

API (both readers):
  accoppia(eventi)         [(key, '«' | '»')] in text order -> (pairs [(open key, close key, parent)],
                           unbalanced [(key, char, reason)]); parent: the index of the pair around, or None
  solo_corsivo(s)          a run that holds no letter outside text already italic (not set again)
  eventi_html(h)           the guillemets of an HTML string outside <em>: [(offset, char)]
  trova(segmenti)          a scope of HTML segments [(key, html)] -> the quotations with their ends
                           (segment, plain and HTML offsets), parent, segments spanned, inner text
  corse(segmenti, q)       the HTML runs to set in italic: per segment [a, b, a, b, ...]
  corsivo(segmenti)        the segments' HTML with those runs in <i class="ds">
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
BUILD = os.path.join(C, 'ontologia', 'build')
OUT = os.path.join(BUILD, 'discorsi.json')

APRE, CHIUDE = '«', '»'
LETTER = re.compile(r'[^\W\d_]')
# the LaTeX macros whose argument is already italic (the guillemets inside them are skipped)
CORSIVO_TEX = {'emph', 'detto'}
# why a guillemet is unbalanced
MAI_CHIUSA = '« never closed before the end of the %s'
CHIUSA_IN_CORSIVO = '« closed only by a » inside italic text (%s), which is skipped'
MAI_APERTA = '» with no « open in the %s'
GIA_CHIUSA = '» with no « open: the quotation before it closed in %s'
# the parts of the volume
PARTI = ['testo', 'nota', 'introduzione', 'preliminari', 'appendici']
NOME_PARTE = {'testo': 'book', 'nota': 'note', 'introduzione': 'introduction', 'preliminari': 'text',
              'appendici': 'entry'}


def accoppia(eventi):
    """Stack matching of one scope. eventi: [(key, c)] in text order (key: any position, increasing).
    Returns (pairs, unbalanced): pairs [(open, close, parent)] in the order of their «, parent the index
    of the innermost pair around it (None for an outermost one); unbalanced [(key, c)]: every » with none
    open in text order, then every « left open (in the order of the stack)."""
    stack, pairs, bad = [], [], []
    for key, c in eventi:
        if c == APRE:
            stack.append(key)
        elif stack:
            pairs.append((stack.pop(), key))
        else:
            bad.append((key, CHIUDE))
    bad += [(o, APRE) for o in stack]
    pairs.sort()
    out, around = [], []          # around: the indices of the pairs that contain the current one
    for o, c in pairs:
        while around and out[around[-1]][1] < o:
            around.pop()
        out.append((o, c, around[-1] if around else None))
        around.append(len(out) - 1)
    return out, bad


def solo_corsivo(bare):
    """bare: a run with its text already in italic taken out (and its markup): no letter left."""
    return not LETTER.search(bare)


# ---------------------------------------------------------------- the HTML reader

TAG = re.compile(r'<(/?)([a-z]+)[^>]*>')


def eventi_html(h):
    """The guillemets of h outside <em>...</em> (already italic): [(offset, c)]."""
    out, em = [], 0
    for m in re.finditer(r'<(/?)em>|[«»]', h):
        g = m.group(0)
        if g == '<em>':
            em += 1
        elif g == '</em>':
            em -= 1
        elif not em:
            out.append((m.start(), g))
    return out


def corsivi_html(h):
    """The guillemets of h inside <em>...</em>: [(offset, c)] (skipped by eventi_html)."""
    out, em = [], 0
    for m in re.finditer(r'<(/?)em>|[«»]', h):
        g = m.group(0)
        em += (g == '<em>') - (g == '</em>')
        if g in (APRE, CHIUDE) and em:
            out.append((m.start(), g))
    return out


def motivo(segs, q, x, part):
    """Why x (of trova(segs)) is unbalanced: a « whose » stands in italic text later in the scope (Sir
    16,22: the third stich, an addition printed in italics, holds it); a » after a quotation already
    closed (Am 7,17: the volume closes Amos' answer at 7,14 «...sicomòro».); else the end of the scope."""
    if x['sbilanciata'] == APRE:
        k0, o0 = x['apre']
        for k in range(k0, len(segs)):
            if any(c == CHIUDE and (k, o) > (k0, o0) for o, c in corsivi_html(segs[k][1])):
                return CHIUSA_IN_CORSIVO % segs[k][0]
        return MAI_CHIUSA % NOME_PARTE[part]
    prima = [y['chiude'] for y in q if not y['sbilanciata'] and y['chiude'] < x['chiude']]
    return GIA_CHIUSA % segs[max(prima)[0]][0] if prima else MAI_APERTA % NOME_PARTE[part]


def piano(h, off):
    """The plain-text offset of HTML offset off (tags removed, <br> a line end; off never inside a tag)."""
    return len(re.sub(r'<[^>]+>', '', h[:off].replace('<br>', '\n')))


def testo_piano(h):
    return re.sub(r'<[^>]+>', '', h.replace('<br>', '\n'))


def trova(segmenti):
    """The quotations of one scope. segmenti: [(key, html)]. Each quotation is a dict:
    apre / chiude: [segment index, html offset] of its « / » (None when unbalanced on that side),
    padre: the index of the quotation around it (None: outermost), sbilanciata: the guillemet ('«' or
    '»') when unbalanced, else None. Offsets are those of the guillemets."""
    ev = [((k, o), c) for k, sg in enumerate(segmenti) for o, c in eventi_html(sg[1])]
    pairs, bad = accoppia(ev)
    out = [dict(apre=list(o), chiude=list(c), padre=p, sbilanciata=None) for o, c, p in pairs]
    for key, c in bad:
        # an unbalanced guillemet is in the quotation around it, if any (Sir 16,22 opens none)
        around = [j for j, (o, cc, _) in enumerate(pairs) if o < key < cc]
        out.append(dict(apre=list(key) if c == APRE else None, chiude=list(key) if c == CHIUDE else None,
                        padre=around[-1] if around else None, sbilanciata=c))
    return out


def _runs(h, a, b, cuts=()):
    """The runs of h[a:b] as [x, y, ...]: no <br> inside, and no tag that opens or closes outside the run
    (the run is cut there), nor any of the offsets cuts where no tag is open (where a note or a margin
    reference is called; inside an <em> the run stays whole, as an \\emph of the LaTeX is);
    a run that is only italic already (solo_corsivo) or only spaces is dropped, the spaces at the edges
    of a run stay outside it."""
    pieces, start, stack = [], a, []

    def cut(end):
        p = start
        for pos, tend, _ in stack:            # tags opened in the stretch and not closed in it
            pieces.append((p, pos))
            p = tend
        pieces.append((p, end))

    cuts = [c for c in cuts if a < c < b]
    for m in TAG.finditer(h, a, b):
        while cuts and cuts[0] <= m.start():
            if not stack:                      # a cut only where no tag is open (an <em> stays whole)
                cut(cuts[0])
                start = cuts[0]
            cuts.pop(0)
        if m.group(2) == 'br':
            cut(m.start())
            start, stack = m.end(), []
        elif m.group(1):
            if stack and stack[-1][2] == m.group(2):
                stack.pop()
            else:                              # it closes a tag opened before the stretch
                cut(m.start())
                start, stack = m.end(), []
        else:
            stack.append((m.start(), m.end(), m.group(2)))
    for c in cuts:
        if not stack:
            cut(c)
            start = c
    cut(b)
    out = []
    for p, q in pieces:
        s = h[p:q]
        if solo_corsivo(re.sub(r'<[^>]+>', '', re.sub(r'<em>.*?</em>', '', s))):
            continue
        out += [p + len(s) - len(s.lstrip()), q - len(s) + len(s.rstrip())]
    return out


def corse(segmenti, quotations=None, tagli=None):
    """The HTML runs in italic of each segment, [a, b, a, b, ...]: the inside of every outermost
    balanced pair (the guillemets stay upright), split at <br>, at tags it does not hold whole and at the
    offsets tagli[k] of segment k (its note calls and margin references: a run of the LaTeX ends there)."""
    q = trova(segmenti) if quotations is None else quotations
    out = [[] for _ in segmenti]
    for x in q:
        if x['padre'] is not None or x['sbilanciata']:
            continue
        (ka, oa), (kb, ob) = x['apre'], x['chiude']
        for k in range(ka, kb + 1):
            h = segmenti[k][1]
            a = oa + 1 if k == ka else 0
            b = ob if k == kb else len(h)
            out[k] += _runs(h, a, b, sorted(set((tagli or {}).get(k, ()))))
    return out


def tagli(data, ids):
    """For the verses ids (a scope of verse text): {index in ids: html offsets of its note calls and margin
    references}, where a run of the LaTeX stops. A margin reference anchored to the next verse is cut where
    it is printed, before the last words of the verse it stands in (estrai.py, 'mref-before-verse')."""
    pos = {v: k for k, v in enumerate(ids)}
    html = {}
    out = {}
    for x in data['notes'] + data['mrefs']:
        if x['anchor'] in pos:
            out.setdefault(pos[x['anchor']], []).append(x['html_offset'])
    tail = {a['where']: a['detail'] for a in data['anomalies'] if a['kind'] == 'mref-before-verse'}
    for m in data['mrefs']:
        if m.get('printed_in_verse') in pos:
            if not html:
                html.update((v['id'], v['html']) for v in data['verses'] if v['id'] in pos)
            h = html[m['printed_in_verse']]
            t = re.search(r' after «(.*)», before verse', tail.get(m['id'], ''))
            n = len(t.group(1).split()) if t else 0
            starts = [mm.start() for mm in re.finditer(r'(?:^|(?<=\s)|(?<=<br>))[^\s<]', h)]
            out.setdefault(pos[m['printed_in_verse']], []).append(starts[-n] if 0 < n <= len(starts) else len(h))
    return out


def bilanciato(h):
    """h holds its tags well nested (the check of the runs inserted)."""
    stack = []
    for m in TAG.finditer(h):
        if m.group(2) == 'br' or m.group(0).endswith('/>'):
            continue
        if m.group(1):
            if not stack or stack.pop() != m.group(2):
                return False
        else:
            stack.append(m.group(2))
    return not stack


def corsivo(segmenti, cls='ds'):
    """The HTML of each segment with its runs in <i class="ds">...</i>."""
    out = []
    for (_, h, *_), r in zip(segmenti, corse(segmenti)):
        for j in range(len(r) - 2, -1, -2):
            a, b = r[j], r[j + 1]
            h = '%s<i class="%s">%s</i>%s' % (h[:a], cls, h[a:b], h[b:])
        out.append(h)
    return out


# ---------------------------------------------------------------- stage 2e: the scopes of the volume

def risorsa(seg):
    """The RDF resource (CURIE of rdf.py) of a segment or source id: 'Gen.1.3' a verse, 'edizione' the
    edition, '<kind>/<local>' the resource <kind>:<local> (nota/Gen.1.2, libro/Gen, paragrafo/pentateuco.3,
    introduzione/pentateuco, testopre/presentazione, canone/ebraico/voce/3, abbreviazione/68,
    cronologia/voce/5, indice/note/voce/145/1)."""
    if seg == 'edizione':
        return 'id:edizione'
    if '/' not in seg:
        return 'verso:' + seg
    k, local = seg.split('/', 1)
    return '%s:%s' % (k, local)


def scopi(data, pt):
    """Every scope of the volume: (part, source, [(segment, html, plain text)]), the plain text the one of
    the graph (bj:testo; the rdf:value of a note's body; skos:prefLabel of an index entry, bj:etichetta of
    a sub-entry, bj:significato of an abbreviation); ids as risorsa() reads them. The calendar, the
    measures and the comments between the references of the indices are not text of the graph."""
    out, cur, ks = [], None, []
    for v in data['verses']:
        if v['book'] != cur:
            if ks:
                out.append(('testo', 'libro/' + cur, ks))
            cur, ks = v['book'], []
        ks.append((v['id'], v['html'], v['text']))
    out.append(('testo', 'libro/' + cur, ks))
    for n in data['notes']:
        k = 'nota/' + n['id'].split(':', 1)[1]
        out.append(('nota', k, [(k, n['html'], n['text'])]))
    for x in data['intros']:
        iid = x['id'][len('intro-'):]
        out.append(('introduzione', 'introduzione/' + iid, [('paragrafo/%s.%d' % (iid, p['n']), p['html'], p['text'])
                                                            for p in x['paragraphs']]))
    ed = pt['edizione']
    out.append(('preliminari', 'edizione', [('edizione', '<br>'.join(ed['colophon']), '\n'.join(ed['colophon']))]))
    for t in pt['testi']:
        out.append(('preliminari', 'testopre/' + t['id'], [('paragrafo/%s.%d' % (t['id'], p['n']), p['html'], p['text'])
                                                           for p in t['paragraphs']]))
    for c in pt['canoni']:
        for n, g in enumerate(c['items'], 1):
            k = 'canone/%s/voce/%d' % (c['id'], n)
            out.append(('preliminari', k, [(k, g['html'], g['text'])]))
    for x in pt['abbreviazioni']:
        k = 'abbreviazione/%d' % x['n']
        out.append(('preliminari', k, [(k, x['meaning'], x['meaning'])]))
    for v in pt['cronologia']['voci']:
        k = 'cronologia/voce/%d' % v['n']
        out.append(('appendici', k, [(k, v['html'], v['text'])]))
    for ix in pt['indici']:
        for v in ix['voci']:
            k = 'indice/%s/voce/%d' % (ix['id'], v['n'])
            out.append(('appendici', k, [(k, v['html'], v['lemma'])]))
            for sv in v.get('sub', []):
                k2 = '%s/%d' % (k, sv['k'])
                out.append(('appendici', k2, [(k2, sv['html'], sv['label'])]))
    return out


def discorsi(data, pt):
    """The quotations of the volume, one record each, in text order within each scope: id ('<segment where
    it starts>.<n>'), part, source, start / end ({seg, html, testo}: the offsets of the « and after the »,
    in the HTML and in the plain text of the segment; None on the missing side of an unbalanced one),
    parent (index in the list, or None), segments (spanned, in order), text (the words inside the
    guillemets, the segments joined by a space) or unbalanced (the reason)."""
    out = []
    for part, src, segs in scopi(data, pt):
        q = trova(segs)
        if not q:
            continue
        base = len(out)
        # in text order; ids: the segment where it starts, the n-th quotation starting there
        order = sorted(range(len(q)), key=lambda j: tuple(q[j]['apre'] or q[j]['chiude']))
        rank = {j: r for r, j in enumerate(order)}
        seen = {}
        for j in order:
            sid = segs[(q[j]['apre'] or q[j]['chiude'])[0]][0]
            seen[sid] = seen.get(sid, 0) + 1
            q[j]['id'] = '%s.%d' % (sid, seen[sid])
        for j in order:
            x = q[j]
            ends = {}
            for side in ('apre', 'chiude'):
                if x[side]:
                    k, o = x[side]
                    d = side == 'chiude'
                    ends[side] = dict(seg=segs[k][0], html=o + d, testo=piano(segs[k][1], o) + d)
            ka = (x['apre'] or x['chiude'])[0]
            kb = (x['chiude'] or x['apre'])[0]
            rec = dict(id=x['id'], part=part, source=src, start=ends.get('apre'), end=ends.get('chiude'),
                       parent=None if x['padre'] is None else base + rank[x['padre']],
                       segments=[segs[k][0] for k in range(ka, kb + 1)])
            if x['sbilanciata']:
                rec['unbalanced'] = motivo(segs, q, x, part)
            else:
                (a, oa), (b, ob) = x['apre'], x['chiude']
                inner = [testo_piano(segs[k][1][oa + 1 if k == a else 0:ob if k == b else len(segs[k][1])])
                         for k in range(a, b + 1)]
                rec['text'] = ' '.join(t.strip() for t in inner if t.strip())
            out.append(rec)
    return out


def controlla(Q, data, pt):
    """The checks of stage 2e: every end inside its segment, at its guillemet, in the HTML and in the plain
    text of the graph; a parent is an earlier quotation of the same scope that holds it; the unbalanced
    guillemets of the verse text are exactly those of Sir 16,22 and Am 7,17 (as printed: README)."""
    errors = []
    testi = {k: (h, t) for _, _, segs in scopi(data, pt) for k, h, t in segs}
    for n, x in enumerate(Q):
        for side, c in (('start', APRE), ('end', CHIUDE)):
            e = x[side]
            if e is None:
                continue
            h, t = testi[e['seg']]
            o, to = e['html'] - (side == 'end'), e['testo'] - (side == 'end')
            if not (0 <= o < len(h)) or h[o] != c:
                errors.append('%s: %s not at a %s in the HTML' % (x['id'], side, c))
            if not (0 <= to < len(t)) or t[to] != c:
                errors.append('%s: %s not at a %s in the plain text' % (x['id'], side, c))
        p = x['parent']
        if p is not None:
            P = Q[p]
            if not (p < n and P['source'] == x['source'] and P['start'] and P['end']):
                errors.append('%s: parent %r not an earlier balanced quotation of the scope' % (x['id'], p))
        if not x['start'] and not x['end']:
            errors.append('%s: no end at all' % x['id'])
        if x['start'] and x['end'] and x['start']['seg'] == x['end']['seg'] and x['start']['html'] >= x['end']['html']:
            errors.append('%s: ends before it starts' % x['id'])
    sb = sorted(x['segments'][0] for x in Q if x.get('unbalanced') and x['part'] == 'testo')
    if sb != ['Amos.7.17', 'Sir.16.22']:
        errors.append('unbalanced guillemets in the text: %s (expected Am 7,17 and Sir 16,22)' % sb)
    return errors


def main(a):
    quiet = '-q' in a
    data = json.load(open(os.path.join(BUILD, 'bibbia.json'), encoding='utf-8'))
    pt = json.load(open(os.path.join(BUILD, 'paratesto.json'), encoding='utf-8'))
    Q = discorsi(data, pt)
    errors = controlla(Q, data, pt)
    from collections import Counter
    st = Counter()
    for x in Q:
        st[(x['part'], 'unbalanced' if x.get('unbalanced') else 'nested' if x['parent'] is not None else
            'outermost')] += 1
    meta = dict(generated_by='tools/ontologia/virgolette.py', rules='see the docstring of virgolette.py',
                counts={'%s %s' % k: v for k, v in sorted(st.items())},
                ids='<segment where it starts (verse, note, paragraph, entry id)>.<n>')
    sys.path.insert(0, HERE)
    from estrai import dump
    dump(dict(meta=meta, discorsi=Q), OUT)
    if not quiet or errors:
        for k, v in sorted(st.items()):
            print('  %-14s %-11s %6d' % (k[0], k[1], v))
    for e in errors:
        print('ERROR', e)
    print('virgolette: %d quotations -> %s' % (len(Q), os.path.relpath(OUT, C)))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
