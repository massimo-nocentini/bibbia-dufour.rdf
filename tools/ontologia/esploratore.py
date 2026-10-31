"""Build ontologia/esplora.html, one offline page to explore the verse graph.

usage: esploratore.py [-o ontologia/esplora.html] [-q]

Reads ontologia/build/bibbia.json (estrai.py), ontologia/build/collegamenti.json
(riferimenti.py) and ontologia/build/dufour.json (dufour.py), packs what the page needs
into one compact JSON (verses, notes, margin entries, typed links, pericopes, divisions,
introductions; the entries of the Dizionario di Teologia Biblica with their sections,
paragraphs and citations), gzips it and embeds it as base64 in the page together with
the stylesheet and the script of tools/ontologia/esploratore/ (modello.html, stile.css,
app.js). The page has no external resource: it works from file:// and decompresses its
data with the browser's DecompressionStream.

Verses are numbered by their canonical order (0-based index into V.id), and every
target is stored as runs of consecutive indices [a, b, a, b, ...]. A margin link is
[margin, relation, runs, flags, keynote, key notes, key margins, qualifier, alt, status,
reason, raw, sign, key-note verses, tied doublet]; a citation read in another book than
the printed one (riferimenti.py 'inferred') carries that reading as its reason. The citations of a
note or an introduction are wrapped in <a class="ci" data-c=k> (notes) or
<a class="ci" data-i=k> (introductions) at the offsets found by riferimenti.py.

The dictionary (payload key 'diz', see dizionario()): entry names in the case they have
in the prose ('Agnello di Dio', not 'AGNELLO DI DIO'), authors as 'Pierre Grelot', each
citation wrapped in <a class="cd" data-d="k [k2 ...]"> at the offsets of dufour.py (one
anchor for the citations printed as one group), each resolved *word turned into
<a class="vl" href="#voce/<slug>">. A citation's reason, in Italian, says why it is
unresolved, how its book was read ('inferred': an aside, the prose, by hand, a reference
recovered from the text) or how its numbers were read again ('conversion': Sirach 34-36,
Obadiah, an OCR misprint).

Checks (exit status 1 if any fails): every margin link and citation points at a known
margin, note or paragraph; every citation is wrapped (its HTML span holds no tag), the
dictionary's too; every dictionary citation targets known verses and sections, every
*word a known entry; the
printed chapters of each book are contiguous; the page is under 30 MB and holds no
"</script" inside its script. Output is deterministic (gzip without timestamp).
"""
import base64
import gzip
import json
import os
import re
import sys
from collections import Counter

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
    (r'^also (.+) in the paragraph$', r'nel paragrafo anche \1: libro incerto'),
]
LETTURE = [
    (r'^book (\S+) from the text$', r'letto nel libro \1, nominato nel testo (la sigla stampata non ha questo passo)'),
    (r'^verses of chapter (\d+)$', r'letto come versetti del capitolo \1'),
    (r'^book (\S+) of the paragraph \(the source inherited (\S+)\)$',
     r'letto in \1, citato nel paragrafo (\2, il libro sottinteso, non ha questo passo)'),
    (r'^book (\S+) in force before the aside (.+) \(the source inherited (\S+)\)$',
     r'letto in \1, il libro in uso prima dell’inciso «\2» (non in \3)'),
    (r'^book (\S+) named in the prose \(the source inherited (\S+)\)$', r'letto in \1, nominato nel testo (non in \2)'),
    (r'^book (\S+) of the paragraph, like the reference before it in the same parentheses \(the source inherited '
     r'(\S+)\)$', r'letto in \1, come il riferimento che lo precede tra le stesse parentesi (non in \2)'),
    (r'^book (\S+) cited most in the paragraph before it \(a reference the source did not link\)$',
     r'riferimento ritrovato nel testo, letto in \1, il libro più citato nel paragrafo precedente'),
    (r'^book (\S+) of the citation before it in the paragraph \(a reference the source did not link\)$',
     r'riferimento ritrovato nel testo, letto in \1 come la citazione che lo precede'),
    (r'^book (\S+) named in the prose \(a reference the source did not link\)$',
     r'riferimento ritrovato nel testo, letto in \1, nominato nel testo'),
    (r'^by hand: .*\(a reference the source did not link\)$', 'riferimento ritrovato nel testo, libro scelto a mano'),
    (r'^by hand: .*$', 'libro scelto a mano'),
]
# how a row of the dictionary was read again (dufour.py 'conversion'), in Italian; '' = not shown
CONVERSIONI = [
    (r'^(?:.*; )?Sir (\S+): older verse division, CEI (\S+)$', r'Sir \1 nella vecchia numerazione dei versetti = CEI \2'),
    (r"^'(.+)' is Obadiah \(Abd\).*$", r'«\1» è Abdia (Abd), un libro di un solo capitolo'),
    (r"^'(.+)' is the range (\S+) across chapters.*$", r'«\1» è il passo \2, a cavallo di due capitoli'),
    (r"^'(.+)' is the OCR of '(.+)'$", r'«\1» è un errore di stampa per «\2»'),
    (r"^'(\d+) - (\d+)' read as the verse (\S+) .*$", r'letto come il versetto \3'),
    (r'^by hand: .*$', 'corretto a mano'),
    (r'.*', ''),
]
STATI_DIZ = ['resolved', 'partial', 'unresolved']
# a section heading of the dictionary as printed: VT / NT, A / B, I, 1, a, «run-in», INTRODUZIONE
TESTAMENTI = {'VT': 'Antico Testamento', 'NT': 'Nuovo Testamento'}
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


def conversione(c):
    """How a citation was read again (dufour.py 'conversion'), in Italian, or ''."""
    for pat, rep in CONVERSIONI:
        if c and re.match(pat, c):
            return re.sub(pat, rep, c)
    return ''


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


# ---------------------------------------------------------------- the dictionary (dufour.json)

def nomi_voci(dz):
    """Display names of the entries: the headword (printed in capitals) in the case it has
    in the prose. A see-also or redirect printed with the same words gives it whole
    ('Spirito di Dio', 'padri e Padre'); otherwise each word takes the case it has most
    often inside those forms ('Dio' in 'AGNELLO DI DIO'), else lower case."""
    norm = lambda s: ' '.join(s.split()).lower()
    forme, parole = {}, {}
    for x in dz['links']:
        f = x.get('form') or ''
        if x['target']:
            forme.setdefault((x['target'], norm(f)), Counter())[f] += 1
        for w in f.split():                        # the see-also lists print common nouns in lower case
            parole.setdefault(w.lower(), Counter())[w] += 1
    out = {}
    for v in dz['voci']:
        h = ' '.join(v['headword'].split())
        c = forme.get((v['id'], norm(h)))
        if c:
            nome = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        else:
            nome = ' '.join(sorted(parole[w.lower()].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
                            if w.lower() in parole else w.lower() for w in h.split())
        out[v['id']] = nome[:1].upper() + nome[1:]
    return out


def nome_autore(n):
    """'PIERRE GRELOT' -> 'Pierre Grelot', 'JULES DE VAULX' -> 'Jules de Vaulx'."""
    piccole = {'DE', 'DI', 'DU', 'LA', 'LE', 'VAN', 'VON', 'DER', 'DES'}
    cap = lambda p: "'".join(x.capitalize() for x in p.split("'"))      # D'ARAGON -> D'Aragon
    return ' '.join(w.lower() if w in piccole and k else '-'.join(cap(p) for p in w.split('-'))
                    for k, w in enumerate(n.split()))


def avvolgi_diz(html, spans, errors, where):
    """Wrap the citations of a paragraph (or a section title) in <a class="cd" data-d="k k2">.

    Spans printed once for several citations ('Mi 25, 21. 23', 'Apoc 16, 6; 18, 24' read
    as one group) give one anchor carrying all of them. A span crossing a tag (a book in
    italics, '<em>Mi</em> 5, 11') is narrowed to its text after the last tag."""
    gruppi = {}
    for a, b, k in spans:
        gruppi.setdefault((a, b), []).append(k)
    for (a, b), ks in sorted(gruppi.items(), reverse=True):
        if '>' in html[a:b]:                  # '<em>Mi</em> 5, 11', 'Col 2<em>,</em> 18': after the tag
            a += html[a:b].rindex('>') + 1
            a += len(html[a:b]) - len(html[a:b].lstrip())
        if '<' in html[a:b] or not html[a:b].strip():
            errors.append('%s: citation %s spans a tag: %r' % (where, ks, html[a:b]))
            continue
        html = '%s<a class="cd" data-d="%s">%s</a>%s' % (html[:a], ' '.join(map(str, sorted(ks))), html[a:b], html[b:])
    return html


def collega_voci(html, ids, errors, where):
    """<a class="voce" data-voce="slug"> (a resolved *word) -> <a class="vl" href="#voce/slug">."""
    def rep(m):
        if m.group(1) not in ids:
            errors.append('%s: link to an unknown entry %s' % (where, m.group(1)))
        return '<a class="vl" href="#voce/%s">' % m.group(1)
    return re.sub(r'<a class="voce" data-voce="([^"]+)">', rep, html)


def primo_paragrafo(v, sec):
    """n of the first paragraph of section sec or of its subsections (0: none)."""
    for p in v.get('paragraphs', []):
        if sec is None or p['sec'] == sec or p['sec'].startswith(sec + ' '):
            return p['n']
    return 0


def dizionario(dz, vix, errors):
    """The dictionary in the payload.

    voci: [slug, name, kind 0 full / 1 redirect, letter, pages, authors [[k, signed part]],
    signatures [[text, paragraph index it follows]], targets [[entry (-1: unresolved), printed
    path, paragraph n, form]], sections [[path, label, title HTML, depth, kind]], paragraphs [[n, section,
    page, HTML]]]; cit: [entry, paragraph index (-1: a section title), section index (-1:
    before the first heading), runs, status, flags, printed text, reason in Italian].
    """
    ids = {v['id']: k for k, v in enumerate(dz['voci'])}
    nomi = nomi_voci(dz)
    autori = [a['id'] for a in dz['meta']['authors']]
    sezk = {}                                # (slug, path) -> section index
    park = {}                                # paragraph id -> (slug, index)
    for v in dz['voci']:
        for j, s in enumerate(v.get('sections', [])):
            sezk[(v['id'], s['path'])] = j
        for j, p in enumerate(v.get('paragraphs', [])):
            park[p['id']] = j
    cit, spans, tspans = [], {}, {}
    for c in dz['citations']:
        k = len(cit)
        try:
            r = runs(vix[t] for t in c['targets'])
        except KeyError as e:
            errors.append('%s: unknown verse %s' % (c['id'], e))
            r = []
        sec = sezk.get((c['voce'], c['sec']), -1)
        if c['sec'] != '0' and sec < 0:
            errors.append('%s: unknown section %s' % (c['id'], c['sec']))
        par = park[c['para']] if c['para'] else -1
        motivo_ = motivo(c['reason']) if c['status'] != 'resolved' else ''
        if c.get('inferred'):
            motivo_ = lettura(c['inferred'])
        if not motivo_:
            motivo_ = conversione(c.get('conversion'))
        cit.append([ids[c['voce']], par, sec, r, STATI_DIZ.index(c['status']), ''.join(
            {'s': 's', 'ss': 'ss', 'p': 'p', '...': '…'}[f] + ' ' for f in c['flags']).strip(), c['raw'], motivo_])
        dove = (c['voce'], par) if par >= 0 else (c['voce'], sec)
        (spans if par >= 0 else tspans).setdefault(dove, []).append((c['html_offset'], c['html_end'], k))

    voci = []
    for v in dz['voci']:
        slug = v['id']
        firme = []
        for a in v['authors']:
            if any(f[0] == a['signature'] for f in firme):
                continue
            ultimo = -1
            for j, p in enumerate(v.get('paragraphs', [])):
                if a['part'] in (None, '') or p['sec'] == a['part'] or p['sec'].startswith(a['part'] + ' '):
                    ultimo = j
            firme.append([a['signature'], ultimo if ultimo >= 0 else len(v.get('paragraphs', [])) - 1])
        bersagli = []
        for t in v.get('targets', []):
            if t['voce'] is None:                 # one of the 22 unresolved links: its form, as text
                bersagli.append([-1, t['path'] or '', 0, t['form']])
                continue
            dest = dz['voci'][ids[t['voce']]]
            bersagli.append([ids[t['voce']], t['path'] or '', primo_paragrafo(dest, t['sec']) if t['sec'] else 0,
                             t['form']])
        sezioni = []
        for j, s in enumerate(v.get('sections', [])):
            t = avvolgi_diz(s['title_html'], tspans.get((slug, j), []), errors, '%s %s' % (slug, s['path']))
            t = collega_voci(t, ids, errors, slug)
            if s['kind'] == 'testament' and not s['title']:
                t = TESTAMENTI.get(s['label'], s['label'])
            sezioni.append([s['path'], s['label'], t, s['depth'], s['kind']])
        paragrafi = []
        for j, p in enumerate(v.get('paragraphs', [])):
            h = avvolgi_diz(p['html'], spans.get((slug, j), []), errors, p['id'])
            paragrafi.append([p['n'], sezk.get((slug, p['sec']), -1), p['page'], collega_voci(h, ids, errors, p['id'])])
        pag = v['pages'][0] if v['pages'][0] == v['pages'][1] else '%s–%s' % tuple(v['pages'])
        voci.append([slug, nomi[slug], 0 if v['kind'] == 'full' else 1, v['letter'], pag,
                     [[autori.index(a['id']), a['part'] or ''] for a in v['authors']], firme, bersagli,
                     sezioni, paragrafi])

    avvolte = sum(len(x.split()) for v in voci for h in [s[2] for s in v[8]] + [p[3] for p in v[9]]
                  for x in re.findall(r'data-d="([^"]+)"', h))
    if avvolte != len(cit):
        errors.append('dictionary: wrapped citations %d != %d' % (avvolte, len(cit)))
    s = dz['meta']['summary']
    meta = dict(voci=s['voci'], piene=s['full'], rinvii=s['redirects'], sezioni=s['sections'],
                paragrafi=s['paragraphs'], collegamenti=len(dz['links']), citazioni=s['citations'],
                stati=[s['status'].get(x, 0) for x in STATI_DIZ], pct=s['pct_resolved'],
                versetti=s['verses_cited'], colpi=s['verse_hits'], libri=s['books'],
                top=[[vix[x['id']], x['n'], x['voci']] for x in s['top_verses']],
                top_stretti=[[vix[x['id']], x['narrow'], x['n']] for x in s['top_verses_narrow']])
    aut = [nome_autore(a['name']) for a in dz['meta']['authors']]
    return dict(meta=meta, aut=aut, voci=voci, cit=cit)


def fonts():
    """font.css with every @@FONT:file@@ replaced by that woff2 file of font/ as a data: URL."""
    css = open(os.path.join(MODELLO, 'font.css'), encoding='utf-8').read()

    def data_url(m):
        raw = open(os.path.join(MODELLO, 'font', m.group(1)), 'rb').read()
        return 'data:font/woff2;base64,' + base64.b64encode(raw).decode('ascii')
    return re.sub(r'@@FONT:([\w.-]+)@@', data_url, css)


def pagina(P):
    js = open(os.path.join(MODELLO, 'app.js'), encoding='utf-8').read()
    css = fonts() + open(os.path.join(MODELLO, 'stile.css'), encoding='utf-8').read()
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
    dz = json.load(open(os.path.join(BUILD, 'dufour.json'), encoding='utf-8'))
    P, errors = payload(data, coll['links'], coll['meta']['summary'])
    P['diz'] = dizionario(dz, {v['id']: i for i, v in enumerate(data['verses'])}, errors)
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
        Z = P['diz']
        print('dictionary: entries %d, sections %d, paragraphs %d, citations %d'
              % (len(Z['voci']), sum(len(v[8]) for v in Z['voci']), sum(len(v[9]) for v in Z['voci']), len(Z['cit'])))
        print('data: JSON %.1f MB, gzip %.1f MB; page %s %.1f MB'
              % (nraw / 1e6, ngz / 1e6, os.path.relpath(out, C), len(page.encode('utf-8')) / 1e6))
    for e in errors[:20]:
        print('ERROR ' + e)
    print('esploratore: %s' % ('FAILED (%d errors)' % len(errors) if errors else 'all checks pass'))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
