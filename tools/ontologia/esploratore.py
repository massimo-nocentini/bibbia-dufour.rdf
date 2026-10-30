"""Build ontologia/esplora.html, one offline page to explore the verse graph.

usage: esploratore.py [-o ontologia/esplora.html] [-q]

Reads ontologia/build/bibbia.json (estrai.py) and ontologia/build/collegamenti.json
(riferimenti.py), packs what the page needs into one compact JSON (verses, notes,
margin entries, typed links, pericopes, divisions, introductions), gzips it and embeds
it as base64 in the page together with the stylesheet and the script of
tools/ontologia/esploratore/ (modello.html, stile.css, app.js). The page has no
external resource: it works from file:// and decompresses its data with the browser's
DecompressionStream.

Verses are numbered by their canonical order (0-based index into V.id), and every
target is stored as runs of consecutive indices [a, b, a, b, ...]. A margin link is
[margin, relation, runs, flags, keynote, key notes, key margins, qualifier, alt, status,
reason, raw, sign, key-note verses, tied doublet]; a citation read in another book than
the printed one (riferimenti.py 'inferred') carries that reading as its reason. The citations of a
note or an introduction are wrapped in <a class="ci" data-c=k> (notes) or
<a class="ci" data-i=k> (introductions) at the offsets found by riferimenti.py.

Checks (exit status 1 if any fails): every margin link and citation points at a known
margin, note or paragraph; every citation is wrapped (its HTML span holds no tag); the
printed chapters of each book are contiguous; the page is under 30 MB and holds no
"</script" inside its script. Output is deterministic (gzip without timestamp).
"""
import base64
import gzip
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(C, 'tools', 'progetti'))
from progetti import PROGETTI  # noqa: E402

BUILD = os.path.join(C, 'ontologia', 'build')
OUT = os.path.join(C, 'ontologia', 'esplora.html')
MODELLO = os.path.join(HERE, 'esploratore')
LIMITE = 30 * 1024 * 1024

RELAZIONI = ['related', 'parallel', 'doublet', 'quoted-later', 'numbering', 'comment']
STATI = ['resolved', 'partial', 'unresolved', 'numbering', 'comment']
SCOPI = ['verses', 'chapter', 'book']

# colour groups of the graph view, by BJ volume
GRUPPI = [
    ('Pentateuco', ['pentateuco']),
    ('Libri storici', ['libri-storici', 'cronache-esdra-neemia', 'tobia-giuditta-ester', 'maccabei']),
    ('Sapienziali', ['libri-sapienziali']),
    ('Profeti', ['profeti']),
    ('Vangeli', ['vangeli-sinottici', 'vangelo-giovanni']),
    ('Atti', ['atti-degli-apostoli']),
    ('Lettere', ['lettere-paolo', 'lettera-agli-ebrei', 'lettere-cattoliche']),
    ('Apocalisse', ['apocalisse']),
]

MOTIVI = [
    (r'^no verse (.+) \(chapter has (\d+)\)$', r'versetto inesistente: \1 (il capitolo ne ha \2)'),
    (r'^no chapter (.+) \((\S+) has (\d+)\)$', r'capitolo inesistente: \1 (\2 ne ha \3)'),
    (r'^extra-canonical book (.+)$', r'libro non canonico: \1'),
    (r'^unknown siglum (\S+) \((\S+)\?\)$', r'sigla sconosciuta: \1 (forse \2)'),
    (r'^unknown siglum (.+)$', r'sigla sconosciuta: \1'),
    (r'^reversed range (.+)$', r'intervallo rovesciato: \1'),
    (r"^odd suffix '(.+)' in (.+)$", r'suffisso anomalo «\1» in \2'),
    (r'^not understood$', 'riferimento non compreso'),
]
LETTURE = [
    (r'^book (\S+) from the text$', r'letto nel libro \1, nominato nel testo (la sigla stampata non ha questo passo)'),
    (r'^verses of chapter (\d+)$', r'letto come versetti del capitolo \1'),
]
ORDINALI = {'Primo': '1', 'Prima': '1', 'Secondo': '2', 'Seconda': '2', 'Terza': '3'}


def motivo(reason):
    """The reason of an unresolved link, in Italian, without repeated parts."""
    if not reason:
        return ''
    parti = []
    for p in reason.split('; '):
        for pat, rep in MOTIVI:
            if re.match(pat, p):
                p = re.sub(pat, rep, p)
                break
        if p not in parti:
            parti.append(p)
    return '; '.join(parti)


def lettura(inferred):
    """How a citation without siglum was read (riferimenti.py, 'inferred'), in Italian."""
    for pat, rep in LETTURE:
        if inferred and re.match(pat, inferred):
            return re.sub(pat, rep, inferred)
    return inferred or ''


def nome_breve(title):
    """'Prima lettera ai Corinzi' -> '1 Corinzi', 'Vangelo secondo Matteo' -> 'Matteo'."""
    m = re.match(r'(Primo|Prima|Secondo|Seconda|Terza) (?:libro|lettera) (?:di|dei|delle|ai|agli|a) (.+)$', title)
    if m:
        return '%s %s' % (ORDINALI[m.group(1)], m.group(2))
    m = re.match(r'(?:Vangelo secondo|Lettera (?:di|ai|agli|a)) (.+)$', title)
    if m:
        return m.group(1)
    m = re.match(r'Ester \(testo (\w+)\)$', title)
    if m:
        return 'Ester %s' % m.group(1)
    return {'Atti degli Apostoli': 'Atti', 'Cantico dei Cantici': 'Cantico'}.get(title, title)


def runs(indices):
    """Sorted runs of consecutive verse indices, flattened: [a, b, a, b, ...]."""
    out = []
    for i in sorted(set(indices)):
        if out and out[-1] == i - 1:
            out[-1] = i
        else:
            out += [i, i]
    return out


def avvolgi(html, spans, attr, errors, where):
    """Wrap each (start, end, k) span of html in <a class="ci" attr=k>.

    A span crossing a tag ("<em>3 Esdra</em> 2,6", a book named in italics) is
    narrowed to the text after its last tag.
    """
    for a, b, k in sorted(spans, reverse=True):
        if '>' in html[a:b]:
            a += html[a:b].rindex('>') + 1
        if '<' in html[a:b] or not html[a:b].strip():
            errors.append('%s: citation %d spans a tag: %r' % (where, k, html[a:b]))
            continue
        html = '%s<a class="ci" %s="%d">%s</a>%s' % (html[:a], attr, k, html[a:b], html[b:])
    return html


# ---------------------------------------------------------------- the payload

def volumi():
    gruppo = {v: g for g, (_, vs) in enumerate(GRUPPI) for v in vs}
    return [[p['nome'], p['titolo'], gruppo[p['nome']]] for p in PROGETTI if not p.get('prova')]


def libri(data, errors):
    """Books with their printed chapters as [label, first verse index, last verse index]."""
    nomi = [v[0] for v in volumi()]
    caps = {b['osis']: [] for b in data['books']}
    for i, v in enumerate(data['verses']):
        pc = v.get('printed_in_chapter', v['chapter'])     # Nm 25,19 is printed in chapter 26
        c = caps[v['book']]
        if c and c[-1][0] == pc:
            c[-1][2] = i
        else:
            c.append([pc, i, i])
    out = []
    for b in data['books']:
        label = {c['n']: c['label'] for c in b['chapters']}
        c = caps[b['osis']]
        if len({x[0] for x in c}) != len(c) or any(x[2] - x[1] + 1 != sum(
                1 for k in range(x[1], x[2] + 1) if data['verses'][k]['book'] == b['osis']) for x in c):
            errors.append('%s: printed chapters not contiguous' % b['osis'])
        sigla = 'Est gr' if b['osis'] == 'EsthGr' else b['siglum']
        out.append(dict(o=b['osis'], s=sigla, t=b['title'], tl=b['title_long'], n=nome_breve(b['title']),
                        T=b['testament'],
                        v=nomi.index(b['volume']), c=[[label[x[0]], x[1], x[2]] for x in c]))
    return out


def versetti(data):
    V = data['verses']
    flags = [(1 if v['poetry'] else 0) | (2 if v.get('omitted') else 0) | (4 if v.get('bracketed') else 0)
             for v in V]
    return dict(id=[v['id'] for v in V], l=[v['label'] for v in V], h=[v['html'] for v in V],
                f=flags, pg=[v['page'] for v in V],
                ac={str(i): ' '.join(v['acrostic']) for i, v in enumerate(V) if v.get('acrostic')})


def payload(data, links, summary):
    errors = []
    V = data['verses']
    vix = {v['id']: i for i, v in enumerate(V)}
    bix = {b['osis']: k for k, b in enumerate(data['books'])}
    nix = {n['id']: k for k, n in enumerate(data['notes'])}
    mix = {m['id']: k for k, m in enumerate(data['mrefs'])}
    iix = {x['id']: k for k, x in enumerate(data['intros'])}
    books = libri(data, errors)

    def tgt(link):
        return runs(vix[t] for t in link['targets'])

    mlinks, ncites, icites = [], [], []
    nspans = {k: [] for k in range(len(data['notes']))}
    ispans = {}
    for x in links:
        if x['kind'] == 'mref':
            if x['source'] not in mix:
                errors.append('%s: unknown margin' % x['id'])
                continue
            mlinks.append([mix[x['source']], RELAZIONI.index(x['relation']), tgt(x), ''.join(x['flags']),
                           1 if x['keynote'] else 0, [nix[n] for n in x['keynote_notes']],
                           [mix[m] for m in x['keynote_mrefs']], x['qualifier'] or '',
                           '' if x['alt'] is None else str(x['alt']), STATI.index(x['status']),
                           motivo(x['reason']), x['raw'], x['sign'] or '',
                           [vix[t] for t in x.get('keynote_verses', [])], 1 if x.get('doublet_of') else 0])
        elif x['kind'] == 'note-cites':
            if x['source'] not in nix:
                errors.append('%s: unknown note' % x['id'])
                continue
            k = len(ncites)
            ncites.append([nix[x['source']], tgt(x), STATI.index(x['status']),
                           motivo(x['reason']) or lettura(x.get('inferred')), x['raw']])
            nspans[nix[x['source']]].append((x['html_offset'], x['html_end'], k))
        elif x['kind'] == 'intro-cites':
            intro, par = x['source'].rsplit('.', 1)
            if intro not in iix:
                errors.append('%s: unknown introduction' % x['id'])
                continue
            k = len(icites)
            icites.append([iix[intro], int(par), tgt(x), STATI.index(x['status']),
                           motivo(x['reason']) or lettura(x.get('inferred')), x['raw']])
            ispans.setdefault((intro, int(par)), []).append((x['html_offset'], x['html_end'], k))

    notes = []
    for k, n in enumerate(data['notes']):
        r = runs(vix[t] for t in n['targets'])
        if not r and n['target_book']:
            c = books[bix[n['target_book']]]['c']
            r = [c[0][1], c[-1][2]]
        html = avvolgi(n['html'], nspans[k], 'data-c', errors, n['id'])
        notes.append([vix[n['anchor']], n['html_offset'], n['label'] or '', n['sign'] or '',
                      SCOPI.index(n['scope']), html, r, n['page']])

    intros = []
    for x in data['intros']:
        pars = [[p['n'], p['page'], avvolgi(p['html'], ispans.get((x['id'], p['n']), []), 'data-i', errors,
                                             '%s.%d' % (x['id'], p['n']))] for p in x['paragraphs']]
        intros.append([x['id'], x['title'], x['heading'], [v[0] for v in volumi()].index(x['volume']),
                       [bix[o] for o in x['books']], pars])

    peri = [[vix[p['first']], vix[p['last']], p['title_html'], 1 if p['mid_verse'] else 0]
            for p in data['pericopes']]
    divs = [[vix[d['first']], vix[d['last']], d['level'], d['title_html']] for d in data['divisions']]
    mrefs = [[vix[m['anchor']], m['html_offset'], m['raw'], m['page']] for m in data['mrefs']]
    wrapped = sum(n[5].count('<a class="ci"') for n in notes) + \
        sum(p[2].count('<a class="ci"') for x in intros for p in x[5])
    if wrapped != len(ncites) + len(icites):
        errors.append('wrapped citations %d != %d' % (wrapped, len(ncites) + len(icites)))
    meta = dict(totali=data['meta']['totals'], riepilogo=summary,
                relazioni=RELAZIONI, stati=STATI, scopi=SCOPI, gruppi=[g for g, _ in GRUPPI])
    P = dict(meta=meta, vol=volumi(), libri=books, V=versetti(data), peri=peri, div=divs,
             note=notes, mref=mrefs, ml=mlinks, nc=ncites, ic=icites, intro=intros)
    return P, errors



def pagina(P):
    js = open(os.path.join(MODELLO, 'app.js'), encoding='utf-8').read()
    css = open(os.path.join(MODELLO, 'stile.css'), encoding='utf-8').read()
    html = open(os.path.join(MODELLO, 'modello.html'), encoding='utf-8').read()
    raw = json.dumps(P, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    gz = gzip.compress(raw, compresslevel=9, mtime=0)
    b64 = base64.b64encode(gz).decode('ascii')
    page = html.replace('/*@@CSS@@*/', css).replace('/*@@JS@@*/', js).replace('@@DATI@@', b64)
    return page, len(raw), len(gz), js


def main(a):
    out = a[a.index('-o') + 1] if '-o' in a else OUT
    quiet = '-q' in a
    data = json.load(open(os.path.join(BUILD, 'bibbia.json'), encoding='utf-8'))
    coll = json.load(open(os.path.join(BUILD, 'collegamenti.json'), encoding='utf-8'))
    P, errors = payload(data, coll['links'], coll['meta']['summary'])
    page, nraw, ngz, js = pagina(P)
    if '</script' in js.lower():
        errors.append('app.js contains "</script"')
    if len(page.encode('utf-8')) > LIMITE:
        errors.append('page is %d bytes, over the limit' % len(page.encode('utf-8')))
    with open(out, 'w', encoding='utf-8') as f:
        f.write(page)
    if not quiet:
        print('verses %d, notes %d, margins %d, margin links %d, note citations %d, intro citations %d'
              % (len(P['V']['id']), len(P['note']), len(P['mref']), len(P['ml']), len(P['nc']), len(P['ic'])))
        print('data: JSON %.1f MB, gzip %.1f MB; page %s %.1f MB'
              % (nraw / 1e6, ngz / 1e6, os.path.relpath(out, C), len(page.encode('utf-8')) / 1e6))
    for e in errors[:20]:
        print('ERROR ' + e)
    print('esploratore: %s' % ('FAILED (%d errors)' % len(errors) if errors else 'all checks pass'))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
