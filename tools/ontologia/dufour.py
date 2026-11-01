"""Read the Dizionario di Teologia Biblica (X. Léon-Dufour) and link its references to the verses.

usage: dufour.py [--dufour ../dufour/corpus] [-i ontologia/build/bibbia.json] [-o ontologia/build/dufour.json] [-q]

Stage 2b of the verse ontology. Reads the research corpus of X. Léon-Dufour (ed.),
«Dizionario di Teologia Biblica» (Marietti, Italian edition 1976), a separate folder
(default ../dufour/corpus next to this repository, never written to), and writes one
JSON file with:
  voci       the 849 entries ("voci"): headword, kind (full / redirect), letter, printed
             pages, authors, redirect and see-also targets; for full entries the section
             tree (path in the book's notation: 'VT I 2', 'B NT III 2', '0', 'introd.')
             and the paragraphs (plain text without the '*' marks, HTML with <em> for
             the italics and every resolved '*word' as <a class="voce" data-voce=slug>)
  links      entry -> entry links of links.tsv: star ('*word'), seealso, redirect, with
             the target section when the printed path names one; see-also and redirect
             targets without a voce read again (ripara_links: misprinted names, pieces
             of a path)
  citations  one per row of biblerefs.tsv (<slug>#<n>), then the bare references the
             source did not link (<slug>#r<n>, recuperate): entry, section, paragraph,
             raw text with its offsets in the paragraph's (or section title's) plain text
             and HTML, the verses it names in this Bible (riferimenti.resolve_as_printed:
             CEI sigla, ranges, 's' and the next verse, 'ss' to the end of the pericope or
             the next verse printed in its group, 'par.' a flag), status resolved /
             partial / unresolved with the reason
  verses     the per-verse index: for each verse cited, the citations and entries
The numbering of the dictionary is checked against the verse texts (meta.numbering):
quotations followed by their reference are compared with the verses each numbering
would name. Psalms, Joel, Malachi, Esther, Daniel and Kings follow the numbering of this
Bible (Hebrew psalms, CEI chapters); Sirach 34-36 the older verse division, converted
(SIRACIDE). The book of a bare reference is the source's, except after an aside
('(14, 16; cfr. Mt 28, 20)': libri_letti), when a book is named in the prose, and in the
rows and paragraphs read by hand (CORREZIONI, PARAGRAFI). Rows the source's parser got
wrong are read again and said in 'conversion' (Greek Esther letters, a glued 's', Obadiah
printed 'Ab', '26 - 52' a verse, ranges across chapters split in two rows, '1 s' for 'Is').

Checks (exit status 1): counts equal the TSV files, every citation's offsets point at
its raw text in the plain text and the HTML, every target is a verse id, resolved and
partial citations have targets, unresolved ones a reason, every link target is a voce.
"""
import csv
import html as H
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import riferimenti as R  # noqa: E402
from estrai import dump  # noqa: E402

DUFOUR = os.path.join(os.path.dirname(C), 'dufour', 'corpus')
IN = R.IN
OUT = os.path.join(C, 'ontologia', 'build', 'dufour.json')
PAGINA = 20                                     # printed page = PDF index - 20 (dictionary)
QUALI = re.compile(r'ss|s|par\.?|\.\.\.|…|-\s*\d+')
# books named in the prose right before a bare '(c, v)' (CEI sigla); not the names that are
# also common words or persons cited by chapter of another book (Sapienza, Ebrei, Pietro)
NOMI_PROSA = {
    'Genesi': 'Gen', 'Esodo': 'Es', 'Levitico': 'Lv', 'Numeri': 'Nm', 'Deuteronomio': 'Dt', 'Giosuè': 'Gs',
    'Giudici': 'Gdc', 'Neemia': 'Ne', 'Tobia': 'Tb', 'Giuditta': 'Gdt', 'Giobbe': 'Gb', 'Proverbi': 'Pr',
    'Qohelet': 'Qo', 'Ecclesiaste': 'Qo', 'Siracide': 'Sir', 'Ecclesiastico': 'Sir', 'Isaia': 'Is', 'Geremia': 'Ger',
    'Lamentazioni': 'Lam', 'Baruch': 'Bar', 'Ezechiele': 'Ez', 'Osea': 'Os', 'Gioele': 'Gl', 'Amos': 'Am',
    'Abdia': 'Abd', 'Michea': 'Mi', 'Sofonia': 'Sof', 'Aggeo': 'Ag', 'Malachia': 'Ml', 'Matteo': 'Mt',
    'Marco': 'Mc', 'Luca': 'Lc', 'Romani': 'Rm', 'Galati': 'Gal', 'Efesini': 'Ef', 'Filippesi': 'Fil',
    'Colossesi': 'Col', 'Apocalisse': 'Ap', 'lettera agli Ebrei': 'Eb', 'prima lettera di Pietro': '1Pt',
    'seconda lettera di Pietro': '2Pt', 'prima lettera ai Corinzi': '1Cor', 'seconda lettera ai Corinzi': '2Cor',
    'prima lettera di Giovanni': '1Gv', 'lettera di Giacomo': 'Gc', 'lettera di Giuda': 'Gd'}
PROSA = re.compile(r'\b(%s)\s*$' % '|'.join(sorted(map(re.escape, NOMI_PROSA), key=len, reverse=True)))
# Sirach 34-36 in the older verse division the dictionary cites (the Bible de Jérusalem of
# its French original, the division of the NAB 1970), against the CEI 2008 (Ziegler):
# old verse -> (first, last) CEI verse. Anchored on the passages the entries paraphrase
# or quote (34,6 dreams sent by the Most High; 34,18 the unjust sacrifice = 34,21; 35,2
# alms = 35,3-4; 35,14 s the widow = 35,17-19; 35,16 s the prayer that reaches the clouds
# = 35,20-21; 35,22 'secondo il suo modo di agire' = 35,24; 36,4 = 36,5; 36,5 'rinnova i
# segni' = 36,6-7; 36,10 'raduna le tribù' = 36,13; 36,11 = 36,14; 36,1-17 the prayer =
# 36,1-19; 36,20 the perverse heart = 36,22; 36,23 'bontà e dolcezza' = 36,25; 36,24 the
# wife, a helper and a pillar = 36,26); between them, the verses the CEI splits or joins.
def _siracide():
    """{chapter: {older verse: (first, last) CEI verse}} from the rows of the scheme "dizionario" of
    tools/ontologia/numerazioni.tsv (the numberings of the whole project, shared with riferimenti.py)."""
    out = {}
    for r in R.numerazioni('dizionario'):
        c, v = map(int, r['stampato'].split(','))
        m = re.fullmatch(r'(\d+),(\d+)(?:–(\d+))?', r['cei'])
        if r['libro'] != 'Sir' or not m or int(m.group(1)) != c:
            raise ValueError('numerazioni.tsv: %r' % r)
        a = int(m.group(2))
        out.setdefault(c, {})[v] = (a, int(m.group(3) or a))
    return out


SIRACIDE = _siracide()
# rows read by hand: citation id -> (raw as printed, fields of the row as read, why)
CORREZIONI = {
    'forza#23': ('Ab 3', dict(book='Abd', chapter='1', verse='3'),
                 "Obadiah 3, the refuge perched on inaccessible mountains, not Habakkuk 3"),
    'babele-babilonia#49': ('Deut 2 - 4', dict(book='Dn'),
                            'Nebuchadnezzar, the proud tyrant, is Daniel 2-4 (Deut printed for Dan)'),
    'altare#43': ('1 Cor 9, 26-30', dict(book='1Cr'), 'the Chronicler: 1 Cron 9,26-30 (1 Cor printed for 1 Cron)'),
    'latte#23': ('4, 11', dict(book='Ct'), "'nel Cantico (4, 11; 5, 1)'"),
    'latte#24': ('5, 1', dict(book='Ct'), "'nel Cantico (4, 11; 5, 1)'"),
    'mediatore#42': ('33, 1-9', dict(book='Ez'), "Ezechiele, the sentinel (Ez 33,1-9; 3,17-21)"),
    'mediatore#43': ('3, 17-21', dict(book='Ez'), "Ezechiele, the sentinel (Ez 33,1-9; 3,17-21)"),
    'miracolo#134': ('4, 2-7', dict(book='Mt'), 'the temptation and the signs refused: Mt 4; 12; 16'),
    'miracolo#135': ('12, 38 ss', dict(book='Mt'), 'the temptation and the signs refused: Mt 4; 12; 16'),
    'miracolo#136': ('16, 1-4', dict(book='Mt'), 'the temptation and the signs refused: Mt 4; 12; 16'),
    'tempio#13': ('Es 33, 7-l l', dict(verse_to='11'), "'7-l l' is 7-11 (OCR), the tent of meeting"),
    'paraclito#50': ('5, 19-47', dict(book='Gv'), "'in Giovanni è il difensore di Gesù'"),
    'paraclito#51': ('16, 8-11', dict(book='Gv'), "'in Giovanni è il difensore di Gesù'"),
    'paraclito#52': ('16, 33', dict(book='Gv'), "'in Giovanni è il difensore di Gesù'"),
}
# paragraphs whose bare references are read in one book by hand: those the source read in
# an aside's book, and those it did not link (recuperate) whose book is not the one cited
# most in the paragraph before; paragraph id -> (siglum, why), None: not Bible references
PARAGRAFI = {
    'pastore-e-gregge.11': ('Gv', 'John 10, the good shepherd, as in the paragraphs before (the source '
                                  'inherited the aside cfr. Num 27, 17)'),
    'anticristo.8': ('2Ts', "2 Thess 2: the paragraph opens with 'In Tess 2, 3-12'"),
    'sacerdozio.26': ('Eb', "the letter to the Hebrews, named where the paragraph opens ('La lettera agli "
                             "Ebrei, sola, ...'; the source inherited Sal 110, 4)"),
    'sacerdozio.27': ('Eb', 'the letter to the Hebrews, as in the paragraph before'),
    'terra.4': ('Gen', 'Genesis 1-2: man made from the earth, the garden'),
    'solitudine.7': ('Gv', "John 17,16: 'in un mondo al quale non appartiene'"),
    'verita.10': (None, 'Qumran texts (1QS), not Bible references'),
}
# see-also / redirect targets printed wrong: form -> voce
FORME = {'regalità': 're', 'espansione': 'espiazione', 'trasformazione': 'trasfigurazione'}
# one bare reference in parentheses: chapter, verses ('5, 24', '10, 15. 17 s', '2, 8-10', '20, 8. 25-29')
VOCE_NUDA = re.compile(r'(\d+)\s*,\s*(\d+(?:\s*-\s*\d+)?(?:\s*ss?(?![\w]))?'
                       r'(?:\s*\.\s*\d+(?:\s*-\s*\d+)?(?:\s*ss?(?![\w]))?)*)(?=\s*[;),])')
FRAMMENTO = re.compile(r'(?:\d+|o|NT|VT|[a-z] I1 [a-z]\.)$')   # a piece of the previous target's path
APARTE = re.compile(r'(?:cfr\.|=)\s*$')        # an aside: 'cfr. Mt 28, 20', '= Es 3, 14'

# Greek (LXX / Vulgate) psalm number -> Hebrew (CEI) psalm number, for the evidence only
def salmo_greco(g):
    if g <= 8 or g >= 148:
        return g
    if g == 9:
        return 9
    if g <= 112:
        return g + 1
    if g == 113:
        return 114
    if g in (114, 115):
        return 116
    if g <= 145:
        return g + 1
    return 147


# ---------------------------------------------------------------- reading the corpus

def cartella(a):
    """The data folder of the Dufour corpus (--dufour, default ../dufour/corpus)."""
    radice = os.path.abspath(a[a.index('--dufour') + 1]) if '--dufour' in a else DUFOUR
    dati = os.path.join(radice, 'data')
    if not os.path.isfile(os.path.join(dati, 'entries.tsv')):
        sys.exit('dufour.py: no Dufour corpus at %s (expected data/entries.tsv there); '
                 'pass --dufour <folder of the corpus>' % radice)
    return dati


def tsv(dati, nome):
    with open(os.path.join(dati, nome), encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE))


def carica(dati):
    """The TSV tables and the entry files, in the order of entries.tsv."""
    t = {n: tsv(dati, n + '.tsv') for n in ('entries', 'sections', 'paragraphs', 'links', 'biblerefs', 'authors',
                                            'entry_authors')}
    t['json'] = {e['slug']: json.load(open(os.path.join(dati, 'entries', e['slug'] + '.json'), encoding='utf-8'))
                 for e in t['entries']}
    t['links_tsv'] = len(t['links'])
    t['links'], t['links_read_again'] = ripara_links(t)
    return t


# ---------------------------------------------------------------- text and HTML

def stella(testo, s):
    """(drop, word start, word end, replacement) of a '*word' at offset s: '*' goes, and
    the spaces after it when it follows a space or an opening sign ('* obbedendo',
    '(* lebbra'); glued inside a word it is an apostrophe ('dell*uragano'), except in
    'onni*potente', where it only marks the link. After a compound's hyphen ('pietra- *memoriale',
    'Cristo- *agnello', 'diogmòs- *persecuzione') the space before it goes too: 'pietra-memoriale'."""
    n = s + 1
    prima = s - 1 if s >= 3 and testo[s - 1] == ' ' and testo[s - 2] == '-' and testo[s - 3].isalpha() else s
    if s == 0 or testo[s - 1] in ' («“"':
        while n < len(testo) and testo[n] == ' ':
            n += 1
    rimpiazzo = ''
    if s > 0 and testo[s - 1].isalpha() and n < len(testo) and testo[n].isalpha() and \
            not testo[:s].endswith('onni'):
        rimpiazzo = "'"
    return set(range(prima, n)), n, rimpiazzo


def componi(testo, ricco, stelle):
    """Plain text, HTML and offset maps of a paragraph (or a title, ricco = testo).

    stelle: [(offset of '*', length, slug or None)]. Returns (plain, html, pmap, hmap,
    hend): pmap[i] is where source character i lands in plain (or would land, if
    dropped), hmap[i] where its escaped text starts in html, hend[i] the end of html
    after the characters before i (so html[hmap[a]:hend[b]] is source a..b)."""
    tag_prima = defaultdict(list)               # source offset -> tags of rich before it
    i = 0
    for m in re.finditer(r'<[^>]*>|[^<]', ricco):
        if m.group(0).startswith('<'):
            tag_prima[i].append({'<i>': '<em>', '</i>': '</em>'}[m.group(0)])
        else:
            assert m.group(0) == testo[i], 'rich text differs from the text'
            i += 1
    tolti, rimpiazzi, apre, chiude = set(), {}, {}, {}
    for s, lung, slug in stelle:
        drop, w, rimpiazzo = stella(testo, s)
        tolti |= drop
        if rimpiazzo:
            rimpiazzi[s] = rimpiazzo
        if slug:
            apre[w] = slug
            chiude[s + lung] = True
    plain, out = [], []
    pmap, hmap, hend = [], [], []
    plen = hlen = 0
    for i in range(len(testo) + 1):
        hend.append(hlen)
        if i in chiude:
            out.append('</a>')
            hlen += 4
        for t in tag_prima.get(i, []):
            out.append(t)
            hlen += len(t)
        if i in apre:
            a = '<a class="voce" data-voce="%s">' % apre[i]
            out.append(a)
            hlen += len(a)
        pmap.append(plen)
        hmap.append(hlen)
        if i == len(testo):
            break
        ch = rimpiazzi.get(i, '' if i in tolti else testo[i])
        plain.append(ch)
        plen += len(ch)
        e = H.escape(ch, quote=False)
        out.append(e)
        hlen += len(e)
    return ''.join(plain), ''.join(out), pmap, hmap, hend


def pagina(pdf):
    return str(int(pdf) - PAGINA) if str(pdf).strip() else None


# ---------------------------------------------------------------- the entries

def autori(t):
    nomi = {a['id']: a for a in t['authors']}
    per_voce = defaultdict(list)
    for x in t['entry_authors']:
        per_voce[x['slug']].append(dict(id=x['author'], name=nomi[x['author']]['name'],
                                        signature=x['signature'], part=x['after_sec'] or None))
    return per_voce


def bersagli(links):
    """Redirect / see-also targets of one entry: [{voce, form, path, sec}] in print order."""
    return [dict(voce=x['target'] or None, form=x['form'], path=x['path'] or None, sec=x['target_sec'] or None)
            for x in links]


def voce(e, j, firme, links_di, stelle_di):
    """One entry: header, targets and, for a full entry, sections and paragraphs."""
    v = dict(id=e['slug'], headword=e['headword'], kind=e['kind'], letter=e['letter'],
             pages=[e['printed_first'], e['printed_last']], authors=firme.get(e['slug'], []))
    if e['kind'] == 'redirect':
        v.update(redirect=j['redirect'], targets=bersagli(links_di[(e['slug'], 'redirect')]))
        return v, {}
    testi = {}
    sezioni = []
    for s in j['sections']:
        plain, html, pmap, hmap, hend = componi(s['title'], s['title'], stelle_di[(e['slug'], '', s['id'])])
        testi[('', s['id'])] = (s['title'], plain, html, pmap, hmap, hend)
        sezioni.append(dict(path=s['id'], parent=s['parent_id'], kind=s['kind'], label=s['label'],
                            title=plain, title_html=html, depth=s['depth'], page=pagina(s['page'])))
    paragrafi = []
    for p in j['paragraphs']:
        plain, html, pmap, hmap, hend = componi(p['text'], p['rich'], stelle_di[(e['slug'], p['no'], p['sec'])])
        testi[(p['no'], p['sec'])] = (p['text'], plain, html, pmap, hmap, hend)
        rec = dict(id='%s.%d' % (e['slug'], p['no']), n=p['no'], sec=p['sec'], page=p['printed'],
                   text=plain, html=html)
        if p['page_last'] != p['page']:
            rec['page_last'] = pagina(p['page_last'])
        paragrafi.append(rec)
    v.update(words=int(e['words'] or 0), seealso=j.get('seealso') or None,
             targets=bersagli(links_di[(e['slug'], 'seealso')]), sections=sezioni, paragraphs=paragrafi)
    return v, testi


def ripara_links(t):
    """links.tsv with the see-also and redirect targets the source left without a voce
    read again: a misprinted name (FORME: MONARCHIA -> 'regalità' is RE), a 'NT' / 'VT'
    that continues the previous target's path ('tradizione VT II 2: NT I 1' in ANZIANI,
    'santo VT II; NT IV' in CULTO) becomes a second link to that voce, and the other
    fragments of a path ('uragano 1-3' -> '3', 're o' -> 'o', 'Gesù Cristo – d I1 d.')
    are dropped: the previous link already names their voce. Returns (rows, how many
    were read again)."""
    sezioni = {slug: {s['id'] for s in j.get('sections', [])} for slug, j in t['json'].items()}
    out, n = [], 0
    for x in t['links']:
        f = x['form'].strip()
        if x['type'] == 'star' or x['target']:
            out.append(x)
            continue
        prima = out[-1] if out and (out[-1]['source'], out[-1]['type']) == (x['source'], x['type']) else None
        if f in FORME:
            slug = FORME[f]
            sec = x['path'] if x['path'] in sezioni[slug] else ''
            out.append(dict(x, target=slug, target_kind='full', target_headword=t['json'][slug]['headword'],
                            method='by hand', target_sec=sec, path_status='exact' if sec else x['path_status']))
        elif FRAMMENTO.match(f) and prima and prima['target']:
            if f in ('NT', 'VT'):
                path = ('%s %s' % (f, x['path'])).strip()
                sec = path if path in sezioni[prima['target']] else ''
                out.append(dict(prima, path=path, target_sec=sec, method='continuation',
                                path_status='exact' if sec else 'none'))
        else:
            out.append(x)
            continue
        n += 1
    return out, n


def collegamenti(t):
    """links.tsv as records, and the same grouped for the entries."""
    out = []
    per = defaultdict(list)
    for x in t['links']:
        rec = dict(source=x['source'], type=x['type'], target=x['target'] or None, form=x['form'])
        if x['type'] == 'star':
            rec.update(sec=x['sec'], para='%s.%s' % (x['source'], x['para']) if x['para'] else None,
                       method=x['method'])
        else:
            rec.update(path=x['path'] or None, sec=x['target_sec'] or None, path_status=x['path_status'] or None)
        out.append(rec)
        per[(x['source'], x['type'])].append(x)
    return out, per


def stelle(t):
    """(slug, para or '', sec) -> [(offset, length, slug)] of the '*' links (entry files)."""
    out = defaultdict(list)
    for slug, j in t['json'].items():
        for x in j['links']:
            if x['type'] == 'star':
                out[(slug, x['para'], x['sec'])].append((x['offset'], x['length'], x['slug']))
    return out


# ---------------------------------------------------------------- citations

def span_di(r, B, dopo=''):
    """(siglum, spans for riferimenti, flags, conversion) of one row of biblerefs.tsv.

    dopo: the text right after the raw reference. The source's parser reads 'l' as '1'
    (right in '5, 3l' = 31, wrong in Esther '8, 12l', a lettered verse of the Greek
    text) and drops a letter glued to a verse ('Est 3, 13f', 'Es 3, 7s') or printed
    after a space ('Est 4, 17 g LXX'): they are read again from the text. Esther 4,17
    without a letter is the prayers of Mordecai and Esther, 4,17a-z of the Greek text:
    the dictionary cites it for them (PREGHIERA, POTENZA), and the Hebrew 4,17 only
    says that Mordecai went away. 'Ab' past chapter 3 is Obadiah, a book of one chapter
    cited by verse ('Ab 18', 'Ab 10, 14' = vv. 10 and 14), which the dictionary also
    abbreviates 'Ab'. 'Mt 26 - 52' with no chapter 52 is the verse 26,52. Sirach 34-36
    are converted from the older verse division (SIRACIDE)."""
    c = int(r['chapter'])
    v = int(r['verse']) if r['verse'] else None
    ct = int(r['chapter_to']) if r['chapter_to'] else None
    vt = int(r['verse_to']) if r['verse_to'] else None
    sp = dict(c1=c, v1=v, t1='', c2=ct or c, v2=vt if v is not None and vt else v, t2='', plus=False)
    flags, conversione = [], None
    for q in QUALI.findall(r['qual']):
        if q in ('s', 'ss'):
            sp['t2'] = q
        elif q.startswith('par'):
            flags.append('p')
        elif q in ('...', '…'):
            flags.append('...')
        else:                                   # 'Filem 14-21': the end read as a qualifier
            sp['v2'] = int(q.lstrip('- '))
    siglum = r['book']
    osis = (R.SIGLA.get(siglum) or [None])[0]
    if siglum == 'Ab' and c > len(B.chapters('Hab')):
        spans = [dict(sp, c1=1, v1=n, c2=1, v2=n, t2='') for n in [c] + ([v] if v is not None else [])]
        spans[-1]['t2'] = sp['t2']
        return 'Abd', spans, flags, "'Ab %s' is Obadiah (Abd), a book of one chapter cited by verse" % (
            c if v is None else '%d, %d' % (c, v))
    if v is None and ct and osis in B.books and (ct not in B.chapters(osis) or ct < c) and \
            B.by_num.get((osis, c, ct)):
        sp.update(c2=c, v1=ct, v2=ct)
        conversione = "'%d - %d' read as the verse %d,%d (%s)" % (
            c, ct, c, ct, 'no chapter %d' % ct if ct not in B.chapters(osis) else 'not a range backwards')
        v = ct
    if v is not None and siglum == 'Sir' and c in SIRACIDE and sp['c2'] == c:
        conv = SIRACIDE[c]
        if v in conv and (sp['v2'] in conv or sp['t2'] == 's' and v + 1 in conv):
            fine = v + 1 if sp['t2'] == 's' else sp['v2']
            if sp['t2'] == 's':
                flags.append('s')
                sp['t2'] = ''
            sp.update(v1=conv[v][0], v2=conv[fine][-1])
            if (sp['v1'], sp['v2']) != (v, fine):
                conversione = (conversione + '; ' if conversione else '') + 'Sir %d,%s: older verse division, CEI %d,%s' % (
                    c, v if fine == v else '%d-%d' % (v, fine), c,
                    sp['v1'] if sp['v1'] == sp['v2'] else '%d-%d' % (sp['v1'], sp['v2']))
    if v is not None and siglum == 'Est':
        lettere = {x['suffix'] for x in B.by_num.get(('EsthGr', c, v), [])}
        m = re.search(r'(?<!\d)%d([a-z])\b' % v, r['raw']) or re.match(r' ?([a-z])\b', dopo)
        corto = re.search(r'(?<!\d)(\d+)l\b', r['raw'])
        if m and m.group(1) in lettere:
            sp.update(t1=m.group(1), t2=m.group(1))
            conversione = 'letter %s of Greek Esther read from the text' % m.group(1)
        elif corto and str(v) == corto.group(1) + '1' and 'l' in {
                x['suffix'] for x in B.by_num.get(('EsthGr', c, int(corto.group(1))), [])}:
            sp.update(v1=int(corto.group(1)), v2=int(corto.group(1)), t1='l', t2='l')
            conversione = '%d,%s1 read as %d,%sl (Greek Esther)' % (c, corto.group(1), c, corto.group(1))
        elif (c, v, vt, r['qual']) == (4, 17, None, ''):
            sp.update(t1='a', t2='z')
            conversione = 'Est 4,17 without a letter: the prayers of the Greek text, 4,17a-z'
    elif v is not None and not r['qual'] and re.search(r'(?<!\d)%d(ss?)(?![a-z])' % v, r['raw']):
        sp['t2'] = re.search(r'(?<!\d)%d(ss?)(?![a-z])' % v, r['raw']).group(1)
        conversione = "'%s' glued to the verse read as the qualifier" % sp['t2']
    return siglum, [sp], flags, conversione


def tipo_motivo(reason, status_fonte):
    """extra-canonical, ambiguous-book (an implicit reference that fits several books of
    its paragraph), out-of-range (no such chapter or verse), other."""
    if status_fonte == 'noncanonical':
        return 'extra-canonical'
    if reason and reason.endswith('in the paragraph'):
        return 'ambiguous-book'
    if reason and (reason.startswith('no chapter') or reason.startswith('no verse')):
        return 'out-of-range'
    return 'other'


def tronca(B, osis, sp):
    """The span with its end moved to the last verse that exists (a partial reading), or
    None: only when its start exists ('Sal 10, 9-30' in a psalm of 18 verses)."""
    if osis not in B.books or not R.starts_in(B, osis, sp):
        return None
    capitoli = B.chapters(osis)
    if sp['c2'] in capitoli and (sp['v2'] is None or B.by_num.get((osis, sp['c2'], sp['v2']))):
        return None                             # the end exists: the problem is another one
    c2 = sp['c2'] if sp['c2'] in capitoli else max(capitoli)
    if c2 < sp['c1']:
        return None
    if sp['v1'] is None:
        return dict(sp, c2=c2, t2='')
    return dict(sp, c2=c2, v2=B.by_chapter[(osis, c2)][-1]['verse'], t2='')


def risolvi(r, B, altri=(), dopo='', limite=None):
    """Resolve one row with the resolver of stage 2 (same conventions as the BJ notes).

    altri: for a row whose book is inherited (implicit), the sigla of the explicit
    references of its paragraph. As in riferimenti.resolve, when the inherited book has
    no such chapter or verse, the other books are tried; the reading is kept, and said
    in 'inferred', only when exactly one of them resolves ('(1, 46-55)' after 'Sal' in
    MARIA, with Lc and 1Sam cited around it, is Lc 1,46-55: 1Sam 1 has 28 verses); with
    two or more readings it stays unresolved (CROCE '(19, 30)' could be Gv or At). A
    reference whose start exists is never read elsewhere. limite: the next verse the
    same printed group names in the chapter, where an 'ss' stops ('9, 15 ss. 30-33')."""
    siglum, spans, flags, conversione = span_di(r, B, dopo)
    ref = dict(siglum=siglum, current=False, spans=spans, qualifier=None, raw=r['raw'])
    if r['status'] == 'noncanonical' or not siglum:
        ref.update(book=None, targets=[], ranges=[], flags=[], status='unresolved',
                   reason='extra-canonical book %s' % r['abbr'])
    else:
        R.resolve_as_printed(ref, B, {})
        if ref['status'] != 'resolved' and r['implicit'] != '0' and not (
                ref['book'] and R.starts_in(B, ref['book'], spans[0])):
            prove = [(alt, R.resolve_as_printed(dict(ref, siglum=alt), B, {})) for alt in altri]
            buone = [(alt, p) for alt, p in prove if p['status'] == 'resolved']
            if len(buone) == 1:
                alt, prova = buone[0]
                ref.update({k: prova[k] for k in ('book', 'targets', 'ranges', 'flags', 'status', 'reason')})
                ref['inferred'] = 'book %s of the paragraph (the source inherited %s)' % (alt, siglum)
            elif buone:
                ref['reason'] += '; also %s in the paragraph' % ', '.join(alt for alt, _ in buone)
        if ref['status'] != 'resolved' and ref['book'] and len(spans) == 1:
            corto = tronca(B, ref['book'], spans[0])
            if corto:
                alt = R.resolve_as_printed(dict(ref, spans=[corto]), B, {})
                if alt['status'] == 'resolved':
                    reason = ref['reason']
                    ref.update({k: alt[k] for k in ('book', 'targets', 'ranges', 'flags')})
                    ref.update(status='partial', reason=reason)
    if limite and spans[-1]['t2'] == 'ss' and len(ref['ranges']) == 1:
        primo = B.verses[ref['targets'][0]]
        resta = [t for t in ref['targets'] if B.verses[t]['chapter'] != primo['chapter'] or
                 B.verses[t]['verse'] < limite]
        if resta and len(resta) < len(ref['targets']):
            ref.update(targets=resta, ranges=[[resta[0], resta[-1]]])
    ref['flags'] = sorted(set(ref.get('flags', [])) | set(flags))
    ref['conversion'] = conversione
    return ref


def vicini(righe, i, libro):
    """Sigla of the explicit references in the paragraph of row i, nearest first (those
    before it, then those after it), without libro, the siglum the row is read in."""
    r = righe[i]
    stesso = [(abs(k - i), k > i, x['book']) for k, x in enumerate(righe)
              if (x['para'], x['sec']) == (r['para'], r['sec']) and x['implicit'] == '0' and x['status'] == 'ok']
    out = []
    for _, _, sig in sorted(stesso):
        if sig != libro and sig not in out:
            out.append(sig)
    return out


def parentesi(testo, pos):
    """(start, end) of the innermost parentheses around offset pos, or None."""
    aperte = 0
    for i in range(pos - 1, -1, -1):
        if testo[i] == ')':
            aperte += 1
        elif testo[i] == '(':
            if not aperte:
                fine = testo.find(')', pos)
                return (i, fine) if fine >= 0 else None
            aperte -= 1
    return None


def libri_letti(righe, js, testi, B):
    """{row index: (siglum, why)} for the rows of one entry read in another book than the
    source's: the bare references after an aside.

    The source gives a bare reference ('(14, 17)') the book of the last explicit one
    before it. When that one is an aside, 'cfr. Mt 28, 20' or '= Es 3, 14' printed after
    another reference inside the same parentheses ('(14, 16; cfr. Mt 28, 20)'), the bare
    references after the parentheses close go on with the book in force when they opened
    (Gv in PARACLITO), until the next explicit reference. Only those that inherited the
    aside's book change, and only when at least as many of them exist in the restored book
    as in the aside's (MIRACOLO '(12, 33; cfr. 3, 14 = Num 21, 8)' then '(20, 30 s)': Gv).
    An aside that opens its parentheses ('(cfr. Sal 18, 28)') is not one: what follows may
    continue it (POVERI: Sal 9, 14-19)."""
    per_par = defaultdict(list)
    for k, j in enumerate(js):
        per_par[(j['para'], j['sec'])].append(k)
    out = {}

    def chiudi(z, letto):
        entra = sum(1 for k in z['righe'] if esiste(B, z['libro'], righe[k]))
        resta = sum(1 for k in z['righe'] if esiste(B, z['aparte'], righe[k]))
        if z['righe'] and entra >= resta:
            for k in z['righe']:
                letto[k] = z['libro']
                out[k] = (z['libro'], 'book %s in force before the aside %s (the source inherited %s)' % (
                    z['libro'], z['raw'], z['aparte']))

    for chiave, ks in per_par.items():
        testo = testi[chiave][0]
        letto, attesa, zona = {}, None, None
        for k in ks:
            r, j = righe[k], js[k]
            if attesa and j['start'] > attesa['fine']:
                zona, attesa = attesa, None
            if r['implicit'] != '0':
                nome = nominato(testo, j['start'], ks, js, k)
                if nome and nome != r['book'] and r['implicit'] == '1' and esiste(B, nome, r):
                    out[k] = (nome, 'book %s named in the prose (the source inherited %s)' % (nome, r['book']))
                    letto[k] = nome
                    if zona:                    # a book named anew ends the zone
                        chiudi(zona, letto)
                        zona = None
                    continue
                if zona and r['implicit'] == '2':     # a book named in the prose ends the zone
                    chiudi(zona, letto)
                    zona = None
                if zona and r['implicit'] == '1' and r['book'] == zona['aparte']:
                    zona['righe'].append(k)
                letto[k] = r['book']
                continue
            if zona:                            # the next explicit reference ends the zone
                chiudi(zona, letto)
                zona = None
            letto[k] = r['book']
            if attesa:                          # 'cfr. Es 12, 5; Is 52, 3': the aside goes on
                attesa.update(aparte=r['book'])
                continue
            g = parentesi(testo, j['start'])
            prima = [x for x in ks if x < k and g and js[x]['start'] > g[0]]
            if g and prima and APARTE.search(testo[:j['start']]) and \
                    letto[prima[0]] != r['book'] and r['status'] == 'ok':
                attesa = dict(fine=g[1], libro=letto[prima[0]], aparte=r['book'], raw=r['raw'], righe=[])
        if zona:
            chiudi(zona, letto)
    return out


def nominato(testo, pos, ks, js, k):
    """The siglum of a book named in the prose right before the parentheses of the
    reference at pos, when it opens them or follows only bare references there: 'ma Amos
    (1, 15), Isaia (8, 11)', 'della prima lettera di Pietro (5, 12)'; else None."""
    g = parentesi(testo, pos)
    if not g or any(js[x]['start'] > g[0] and js[x]['start'] < pos and js[x].get('implicit') == 0
                    for x in ks if x < k):
        return None
    m = PROSA.search(testo[max(0, g[0] - 40):g[0]])
    return NOMI_PROSA[m.group(1)] if m else None


def esiste(B, sig, r):
    """Row r names a passage of book sig (as printed, without reading other books)."""
    sig, spans, _, _ = span_di(dict(r, book=sig), B)
    ref = dict(siglum=sig, current=False, spans=spans, qualifier=None, raw=r['raw'])
    return R.resolve_as_printed(ref, B, {})['status'] == 'resolved'


def ritocchi(righe, js, testi, B):
    """{row index: (row as read, note, field of the note)}: the rows read otherwise than
    the source parsed them, before resolving.

    CORREZIONI by hand; '1 s 65, 2', the OCR of 'Is 65, 2' (the source took '1 s' for
    chapter 1 and the next); a range across chapters printed with a full stop that the
    source split in two rows, '47, 13-48. 29' = Ez 47,13-48,29 and 'Ebr 8, 1-10. 18' =
    Eb 8,1-10,18 (only when the second row has no such verse in its chapter but has one
    in the chapter the first row ends with)."""
    out = {}
    for k, (r, j) in enumerate(zip(righe, js)):
        cid = '%s#%d' % (r['slug'], k + 1)
        if cid in CORREZIONI:
            raw, campi, perche = CORREZIONI[cid]
            if r['raw'] == raw:                 # else controlli() reports it
                out[k] = (dict(r, **campi), 'by hand: %s' % perche,
                          'inferred' if r['implicit'] != '0' and set(campi) == {'book'} else 'conversion')
            continue
        pid = '%s.%s' % (r['slug'], r['para'])
        if pid in PARAGRAFI and PARAGRAFI[pid][0] and r['implicit'] == '1':
            out[k] = (dict(r, book=PARAGRAFI[pid][0]), 'by hand: %s' % PARAGRAFI[pid][1], 'inferred')
            continue
        dopo = testi[(j['para'], j['sec'])][0][j['end']:]
        m = re.match(r'\s+(\d+),\s*(\d+)(?![\d,])', dopo)
        if re.fullmatch(r'[1l] s', r['raw']) and m:
            out[k] = (dict(r, book='Is', abbr='ls', chapter=m.group(1), verse=m.group(2), chapter_to='',
                           verse_to='', qual='', implicit='0', raw=r['raw'] + m.group(0), status='ok'),
                      "'%s%s' is the OCR of 'Is %s, %s'" % (r['raw'], m.group(0), m.group(1), m.group(2)),
                      'conversion')
            continue
        if k + 1 < len(righe) and r['verse'] and r['verse_to'] and r['chapter_to'] == r['chapter']:
            q = righe[k + 1]
            osis = (R.SIGLA.get(r['book']) or [None])[0]
            c, n, v = int(r['chapter']), int(r['verse_to']), int(q['verse'] or 0)
            if js[k + 1]['start'] == j['start'] and q['raw'] == r['raw'] and q['chapter'] == r['chapter'] and \
                    v and not q['verse_to'] and osis in B.books and n > c and n in B.chapters(osis) and \
                    not B.by_num.get((osis, c, v)) and B.by_num.get((osis, n, v)):
                nota = "'%s' is the range %d,%s-%d,%d across chapters (the source split it at '%d. %d')" % (
                    r['raw'], c, r['verse'], n, v, n, v)
                out[k] = (dict(r, verse_to=str(v), chapter_to=str(n)), nota, 'conversion')
                out[k + 1] = (dict(q, chapter=str(n)), nota, 'conversion')
    return out


def limiti(righe, js):
    """{row index: verse}: the next verse of the same chapter printed in the same group,
    where an 'ss' stops ('Giob 38, 4 ss. 16 ss': 38,4-15 then 38,16 and following)."""
    out = {}
    for k, (r, j) in enumerate(zip(righe, js)):
        if not r['verse'] or 'ss' not in r['qual'].split():
            continue
        for q, i in zip(righe[k + 1:], js[k + 1:]):
            if i['start'] != j['start'] or q['raw'] != r['raw'] or q['chapter'] != r['chapter']:
                break
            if q['verse'] and int(q['verse']) > int(r['verse']):
                out[k] = int(q['verse'])
                break
    return out


def rileggi_gruppi(recs, righe, js, testi, B):
    """In the parentheses where one bare reference was read in another book of its
    paragraph (PASQUA '(12, 26 s; 13, 8 ss)': Es, the source inherited Nm), the others that
    inherited the same book go to that one too, when it has them."""
    gruppi = defaultdict(list)
    for k, j in enumerate(js):
        g = parentesi(testi[(j['para'], j['sec'])][0], j['start'])
        if g:
            gruppi[(j['para'], j['sec'], g)].append(k)
    for ks in gruppi.values():
        letti = [re.match(r'book (\S+) of the paragraph', recs[k].get('inferred') or '') for k in ks]
        nuovi = {(righe[k]['book'], m.group(1)) for k, m in zip(ks, letti) if m}
        if len(nuovi) != 1:
            continue
        vecchio, nuovo = nuovi.pop()
        for k, m in zip(ks, letti):
            r = righe[k]
            if m or r['implicit'] != '1' or r['book'] != vecchio or recs[k].get('inferred') or \
                    recs[k]['status'] != 'resolved' or not esiste(B, nuovo, r):
                continue
            ref = risolvi(dict(r, book=nuovo), B)
            recs[k].update({x: ref[x] for x in ('book', 'targets', 'ranges', 'flags', 'status', 'reason')})
            recs[k]['inferred'] = 'book %s of the paragraph, like the reference before it in the same ' \
                                  'parentheses (the source inherited %s)' % (nuovo, vecchio)


def citazioni(t, testi, B):
    """One citation per row of biblerefs.tsv, joined to the entry files for the offsets."""
    righe = defaultdict(list)
    for r in t['biblerefs']:
        righe[r['slug']].append(r)
    out, errori = [], []
    for e in t['entries']:
        slug = e['slug']
        js = t['json'][slug]['biblerefs']
        if len(js) != len(righe[slug]) or any(a['raw'] != b['raw'] for a, b in zip(js, righe[slug])):
            errori.append('%s: biblerefs.tsv and the entry file differ' % slug)
            continue
        rs = [dict(r, slug=slug) for r in righe[slug]]
        letti = libri_letti(rs, js, testi[slug], B)
        rivisti = ritocchi(rs, js, testi[slug], B)
        fermi = limiti(rs, js)
        recs = []
        for k, (r, j) in enumerate(zip(rs, js)):
            sorgente, plain, html, pmap, hmap, hend = testi[slug][(j['para'], j['sec'])]
            letta, nota, campo = rivisti.get(k, (r, None, None))
            libro, perche = letti.get(k, (letta['book'], None))
            ref = risolvi(dict(letta, book=libro), B,
                          vicini(rs, k, libro) if letta['implicit'] != '0' and campo != 'inferred' else (),
                          sorgente[j['end']:j['end'] + 4], fermi.get(k))
            if perche and not ref.get('inferred'):
                ref['inferred'] = perche
            if nota:
                ref[campo] = nota if campo == 'inferred' or not ref.get(campo) else '%s; %s' % (nota, ref[campo])
            s = j['start'] + len(sorgente[j['start']:j['end']]) - len(sorgente[j['start']:j['end']].lstrip())
            fine = j['start'] + len(letta['raw']) if letta['raw'] != r['raw'] else j['end']
            rec = dict(id='%s#%d' % (slug, k + 1), voce=slug, sec=r['sec'],
                       para='%s.%s' % (slug, r['para']) if r['para'] else None,
                       where='paragraph' if r['para'] else 'title', raw=letta['raw'], abbr=letta['abbr'],
                       siglum=letta['book'] or None, book=ref['book'], chapter=int(letta['chapter']),
                       verse=int(letta['verse']) if letta['verse'] else None,
                       chapter_to=int(letta['chapter_to']) if letta['chapter_to'] else None,
                       verse_to=int(letta['verse_to']) if letta['verse_to'] else None,
                       qual=letta['qual'] or None, flags=ref['flags'], implicit=int(letta['implicit']),
                       source_status=r['status'], offset=pmap[s], length=pmap[fine] - pmap[s],
                       html_offset=hmap[s], html_end=hend[fine], targets=ref['targets'], ranges=ref['ranges'],
                       status=ref['status'], reason=ref.get('reason'))
            for x in ('conversion', 'inferred'):
                if ref.get(x):
                    rec[x] = ref[x]
            recs.append(rec)
        rileggi_gruppi(recs, rs, js, testi[slug], B)
        for rec in recs:
            if rec['status'] != 'resolved':
                rec['reason_kind'] = tipo_motivo(rec['reason'], rec['source_status'])
        out += recs
    return out, errori


def gruppi_nudi(testo):
    """The bare references printed in parentheses: [(start, end, chapter, verse, verse_to,
    qualifier, raw)], one per verse ('(14, 17. 25)': two, with the same raw), for
    '(14, 17)', '(cfr. 3, 14 s; 6, 40)', '(10, 15. 17 s)', '(2, 8-10)'."""
    out = []
    for g in re.finditer(r'\((?:cfr\.\s*)?(?=\d+\s*,\s*\d)', testo):
        pos = g.end()
        while True:
            m = VOCE_NUDA.match(testo, pos)
            if not m:
                break
            raw = m.group(0).rstrip()
            for v in re.finditer(r'(\d+)(?:\s*-\s*(\d+))?(\s*ss?(?![\w]))?', m.group(2)):
                out.append((m.start(), m.start() + len(raw), int(m.group(1)), int(v.group(1)),
                            int(v.group(2)) if v.group(2) else None, (v.group(3) or '').strip(), raw))
            sep = re.match(r'\s*;\s*(?:cfr\.\s*)?(?=\d+\s*,\s*\d)', testo[m.end():])
            if not sep:
                break
            pos = m.end() + sep.end()
    return out


def recuperate(t, testi, cit, B):
    """Citations the source did not link: bare references in parentheses ('(5, 24)',
    '(3, 16; 6, 47)') in a paragraph where no book is printed before them (FEDE, after a
    paragraph on John). Each is read in the book named in the prose right before it, else
    in the book of the citation before it in the paragraph, else in the book of the last
    citation of the paragraphs before it in the entry; it is kept only when that book has
    the passage, with ids <slug>#r<n>, implicit 3 and source_status 'recovered'."""
    per_voce = defaultdict(list)
    for c in cit:
        per_voce[c['voce']].append(c)
    out = []
    for e in t['entries']:
        slug = e['slug']
        j = t['json'][slug]
        if 'paragraphs' not in j:
            continue
        vigore, n = None, 0
        for p in j['paragraphs']:
            sorgente, plain, html, pmap, hmap, hend = testi[slug][(p['no'], p['sec'])]
            pid = '%s.%d' % (slug, p['no'])
            presenti = sorted((c['offset'], c['offset'] + c['length'], c['book']) for c in per_voce[slug]
                              if c['para'] == pid)
            for a, b, cap, v, vt, q, raw in gruppi_nudi(sorgente):
                if any(x < pmap[b] and pmap[a] < y for x, y, _ in presenti):
                    continue
                prima = [o for x, y, o in presenti if y <= pmap[a] and o]
                nome = PROSA.search(sorgente[max(0, a - 42):a].rstrip('( ').rstrip('cfr.').rstrip())
                osis, come = (R.SIGLA[PARAGRAFI[pid][0]][0] if PARAGRAFI[pid][0] else None,
                              'by hand: %s' % PARAGRAFI[pid][1]) if pid in PARAGRAFI else \
                    (R.SIGLA[NOMI_PROSA[nome.group(1)]][0], 'named in the prose') if nome else \
                    (prima[-1], 'of the citation before it in the paragraph') if prima else \
                    (vigore, 'cited most in the paragraph before it')
                if not osis:
                    continue
                sig = R.OSIS2SIGLA[osis]
                riga = dict(slug=slug, raw=raw, abbr='', book=sig, chapter=str(cap), verse=str(v),
                            chapter_to=str(cap) if vt else '', verse_to=str(vt or ''), qual=q, implicit='3',
                            status='ok')
                ref = risolvi(riga, B)
                if ref['status'] != 'resolved':
                    continue
                n += 1
                out.append(dict(id='%s#r%d' % (slug, n), voce=slug, sec=p['sec'], para=pid, where='paragraph',
                                raw=raw, abbr=None, siglum=sig, book=ref['book'], chapter=cap, verse=v,
                                chapter_to=cap if vt else None, verse_to=vt, qual=q or None, flags=ref['flags'],
                                implicit=3, source_status='recovered', offset=pmap[a], length=pmap[b] - pmap[a],
                                html_offset=hmap[a], html_end=hend[b], targets=ref['targets'],
                                ranges=ref['ranges'], status='resolved', reason=None,
                                inferred='book %s %s (a reference the source did not link)' % (sig, come)
                                if not come.startswith('by hand') else '%s (a reference the source did not '
                                                                       'link)' % come))
            libri = [c['book'] for c in sorted(per_voce[slug] + [x for x in out if x['para'] == pid],
                                               key=lambda c: c['offset']) if c['para'] == pid and c['book']]
            if libri:                           # the book cited most in the paragraph, the last on a tie
                conto = Counter(libri)
                vigore = max(reversed(libri), key=lambda o: conto[o])
    return out


def indice(cit, B):
    """verse id -> citations and entries; in canonical order."""
    per = defaultdict(list)
    for c in cit:
        for vid in c['targets']:
            per[vid].append(c)
    ordine = {v: B.verses[v]['order'] for v in per}
    out = []
    for vid in sorted(per, key=ordine.get):
        cs = per[vid]
        out.append(dict(id=vid, n=len(cs), voci=sorted({c['voce'] for c in cs}),
                        narrow=sum(1 for c in cs if len(c['targets']) <= 3),
                        citations=[c['id'] for c in cs]))
    return out


# ---------------------------------------------------------------- numbering evidence

VUOTE = set('alla allo alle agli dalla dalle dagli della delle degli dello nella nelle negli nello sulla sulle '
            'sugli come anche sono essi esse egli ella questo questa questi queste quello quella quelli quelle '
            'perche quando dove ogni tutto tutti tutta tutte loro suoi sue tuoi tue miei mie nostro vostro '
            'nostra vostra cosi poiche mentre fino verso sopra sotto dopo prima ancora anzi senza contro '
            'presso cioe ecco stato stata hanno aveva avete avere essere sara saranno siano'.split())


def parole(s):
    s = unicodedata.normalize('NFD', s.lower().replace('jahvè', 'signore').replace('jahve', 'signore'))
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return {w[:6] for w in re.findall(r'[a-z]{4,}', s) if w not in VUOTE}


def testo_versi(B, osis, c, v1, v2):
    vs = [x for n in range(v1, min(v2, v1 + 5) + 2) for x in B.by_num.get((osis, c, n), [])]
    return ' '.join(x['text'] for x in vs)


def quotate(t, B):
    """(row, words of the quotation) for each reference printed right after a quotation:
    «...» (Sal 23, 1)."""
    testi = {(p['slug'], p['para']): p['text'] for p in t['paragraphs']}
    out = []
    for r in t['biblerefs']:
        if not r['para'] or not r['verse'] or r['implicit'] != '0' or r['status'] != 'ok':
            continue
        txt = testi[(r['slug'], r['para'])]
        i = txt.find(r['raw'])
        m = re.search(r'«([^»]{10,400})»[\s,.;:]*\(\s*(?:cfr\.\s*)?$', txt[:i]) if i > 0 else None
        if m:
            out.append((r, parole(m.group(1))))
    return out


def punteggio(B, q, osis, c, v1, v2):
    w = parole(testo_versi(B, osis, c, v1, v2))
    return len(q & w)


def confronta(B, righe, siglum, osis, alternativa):
    """Quotations whose words fit the cited numbering better, worse, equally, not at all,
    against another numbering (alternativa: row -> (osis, c, v1, v2) or None)."""
    conto, esempi = Counter(), []
    for r, q in righe:
        if r['book'] != siglum:
            continue
        c, v1 = int(r['chapter']), int(r['verse'])
        v2 = int(r['verse_to']) if r['verse_to'] and r['chapter_to'] == r['chapter'] else v1
        alt = alternativa(c, v1, v2)
        if alt is None:
            continue
        a, b = punteggio(B, q, osis, c, v1, v2), punteggio(B, q, *alt)
        esito = 'none' if not a and not b else 'cited' if a > b else 'other' if b > a else 'tie'
        conto[esito] += 1
        if esito == 'cited' and len(esempi) < 3:
            esempi.append(r['raw'])
    return dict(conto), esempi


def numerazione(t, B, cit):
    """The numbering decisions, each with the evidence measured on this build."""
    q = quotate(t, B)
    per = defaultdict(list)
    for c in cit:
        if c['siglum']:
            per[c['siglum']].append(c)

    def citati(sig, cond):
        return sum(1 for c in per[sig] if cond(c))
    out = []
    conto, esempi = confronta(B, q, 'Sal', 'Ps', lambda c, v1, v2: ('Ps', salmo_greco(c), v1, v2)
                              if salmo_greco(c) != c else None)
    out.append(dict(book='Sal', decision='Hebrew numbering of the CEI, titles counted as verses: no conversion',
                    evidence=dict(quotations=conto, examples=esempi + ['Sal 23, 1 «il mio pastore»',
                                                                       'il Miserere (Sal 51)'],
                                  against='the Greek / Vulgate number of the same psalm (Sal 22 for 23)')))
    titoli, _ = confronta(B, q, 'Sal', 'Ps', lambda c, v1, v2: ('Ps', c, v1 - 1, v2 - 1) if v1 > 1 else None)
    out[-1]['evidence']['titles'] = dict(quotations=titoli, against='the verse before (titles not counted)')
    for sig, osis, altro in (('1Re', '1Kgs', '1Sam'), ('2Re', '2Kgs', '2Sam')):
        conto, esempi = confronta(B, q, sig, osis, lambda c, v1, v2, a=altro: (a, c, v1, v2)
                                  if B.by_num.get((a, c, v1)) else None)
        out.append(dict(book=sig, decision='%s = %s of the CEI (the edition prints "Volg. 3 4 Re" beside it), '
                        'not the Vulgate %s = %s' % (sig, osis, sig.replace('Re', ' Re'), altro),
                        evidence=dict(quotations=conto, examples=esempi)))
    conto, esempi = confronta(B, q, 'Gl', 'Joel', lambda c, v1, v2: ('Joel', 4, v1, v2) if c == 3 else None)
    out.append(dict(book='Gl', decision='Joel in 4 chapters (Hebrew, CEI): 3,1-5 is the outpouring of the spirit',
                    evidence=dict(quotations=conto, examples=esempi,
                                  cited_3=citati('Gl', lambda c: c['chapter'] == 3),
                                  cited_4=citati('Gl', lambda c: c['chapter'] == 4),
                                  cited_2_28_32=citati('Gl', lambda c: c['chapter'] == 2 and (c['verse'] or 0) >= 28))))
    out.append(dict(book='Ml', decision='Malachi in 3 chapters (CEI): 3,19-24 is the Vulgate 4,1-6',
                    evidence=dict(cited_3_19_24=citati('Ml', lambda c: c['chapter'] == 3 and (c['verse'] or 0) >= 19),
                                  cited_4=citati('Ml', lambda c: c['chapter'] == 4))))
    out.append(dict(book='Est', decision='Esther as in the BJ: the Greek additions are lettered verses of EsthGr '
                    '(3,13f; 4,17g; 4,17z; 8,12l; 10,3f) and a bare 4,17 is the prayers 4,17a-z; any other verse '
                    'the Hebrew text first (riferimenti)',
                    evidence=dict(read_again=citati('Est', lambda c: bool(c.get('conversion'))),
                                  vulgate_chapters_11_16=citati('Est', lambda c: c['chapter'] > 10),
                                  greek=citati('Est', lambda c: c['book'] == 'EsthGr'),
                                  hebrew=citati('Est', lambda c: c['book'] == 'Esth'))))
    out.append(dict(book='Dn', decision='Daniel 3 with the Greek parts as in the CEI (3,24-90; 13; 14)',
                    evidence=dict(cited_3_24_90=citati('Dn', lambda c: c['chapter'] == 3 and 24 <= (c['verse'] or 0)
                                                       <= 90),
                                  cited_13_14=citati('Dn', lambda c: c['chapter'] in (13, 14)),
                                  unresolved=citati('Dn', lambda c: c['status'] == 'unresolved'))))
    for sig, osis in (('Sir', 'Sir'), ('Qo', 'Eccl')):
        fuori = [x for x in q if not (sig == 'Sir' and int(x[0]['chapter']) in SIRACIDE)]
        conto, esempi = confronta(B, fuori, sig, osis, lambda c, v1, v2, o=osis: (o, c, v1 + 1, v2 + 1))
        out.append(dict(book=sig, decision='%s = %s (Eccli = Siracide, Eccle = Qoelet); numbering of the CEI'
                        % (sig, osis), evidence=dict(quotations=conto, examples=esempi,
                                                     against='the next verse',
                                                     unresolved=citati(sig, lambda c: c['status'] != 'resolved'))))
    out[-2].update(decision=out[-2]['decision'] + ', except chapters 34-36: the older verse division of the '
                   'Bible de Jérusalem (as the NAB 1970), converted with a table (SIRACIDE)')
    out[-2]['evidence']['chapters_34_36'] = siracide(t, B, cit)
    return out


def siracide(t, B, cit):
    """Evidence for the Sirach 34-36 table: the words of the clause before each converted
    citation fit the CEI verses it is converted to better, worse or as well as the verses
    its printed numbers name in the CEI."""
    testi = {(p['slug'], p['para']): p['text'] for p in t['paragraphs']}
    conto, esempi = Counter(), []
    for c in cit:
        if 'older verse division' not in (c.get('conversion') or '') or not c['para'] or not c['verse']:
            continue
        txt = testi[(c['voce'], c['para'].rsplit('.', 1)[1])]
        i = txt.find(c['raw'])
        prima = parole(re.sub(r'\([^()]*$', '', txt[max(0, i - 200):i]))
        stampato = parole(' '.join(x['text'] for n in range(c['verse'], (c['verse_to'] or c['verse']) + 1)
                                   for x in B.by_num.get(('Sir', c['chapter'], n), [])))
        letto = parole(' '.join(B.verses[x]['text'] for x in c['targets'][:6]))
        a, b = len(prima & letto), len(prima & stampato)
        esito = 'none' if not a and not b else 'converted' if a > b else 'printed' if b > a else 'tie'
        conto[esito] += 1
        if esito == 'converted' and len(esempi) < 4:
            esempi.append('%s %s -> %s' % (c['id'], c['raw'], c['ranges'][0][0]))
    return dict(citations=dict(conto), examples=esempi, against='the CEI verses of the printed numbers')


# ---------------------------------------------------------------- checks and report

def controlli(t, voci, links, cit, B, errori):
    errori = list(errori)
    if len(voci) != len(t['entries']):
        errori.append('%d voci for %d rows of entries.tsv' % (len(voci), len(t['entries'])))
    n_sez = sum(len(v.get('sections', [])) for v in voci)
    n_par = sum(len(v.get('paragraphs', [])) for v in voci)
    if n_sez != len(t['sections']):
        errori.append('%d sections for %d rows of sections.tsv' % (n_sez, len(t['sections'])))
    if n_par != len(t['paragraphs']):
        errori.append('%d paragraphs for %d rows of paragraphs.tsv' % (n_par, len(t['paragraphs'])))
    fonte = [c for c in cit if c['source_status'] != 'recovered']
    if len(fonte) != len(t['biblerefs']):
        errori.append('%d citations for %d rows of biblerefs.tsv' % (len(fonte), len(t['biblerefs'])))
    per_id = {c['id']: c for c in cit}
    errori += ['CORREZIONI %s: no citation printed %r' % (cid, x[0]) for cid, x in CORREZIONI.items()
               if per_id.get(cid, {}).get('raw') != x[0]]
    paragrafi = {p['id'] for v in voci for p in v.get('paragraphs', [])}
    errori += ['PARAGRAFI %s: no such paragraph' % pid for pid in PARAGRAFI if pid not in paragrafi]
    ids = {v['id'] for v in voci}
    errori += ['link %s -> %s: no such voce' % (x['source'], x['target']) for x in links
               if x['target'] and x['target'] not in ids]
    stelle_html = sum(len(re.findall(r'<a class="voce"', p['html'])) for v in voci for p in v.get('paragraphs', []))
    stelle_html += sum(len(re.findall(r'<a class="voce"', s['title_html'])) for v in voci
                       for s in v.get('sections', []))
    risolte = sum(1 for x in links if x['type'] == 'star' and x['target'])
    if stelle_html != risolte:
        errori.append('%d * links in the HTML, %d resolved in links.tsv' % (stelle_html, risolte))
    testi = {}
    for v in voci:
        for p in v.get('paragraphs', []):
            testi[(v['id'], p['id'])] = (p['text'], p['html'])
        for s in v.get('sections', []):
            testi[(v['id'], s['path'])] = (s['title'], s['title_html'])
    for c in cit:
        plain, html = testi[(c['voce'], c['para'] or c['sec'])]
        atteso = re.sub(r'(?<=\w)\*(?=\w)', "'", c['raw']).replace('* ', '').replace('*', '')
        if plain[c['offset']:c['offset'] + c['length']] != atteso:
            errori.append('%s: offset does not point at %r' % (c['id'], c['raw']))
        pezzo = html[c['html_offset']:c['html_end']]
        if H.unescape(re.sub(r'<[^>]*>', '', pezzo)) != atteso:
            errori.append('%s: html offsets do not point at %r' % (c['id'], c['raw']))
        if any(x not in B.verses for x in c['targets']):
            errori.append('%s: unknown target' % c['id'])
        if c['status'] in ('resolved', 'partial') and not c['targets']:
            errori.append('%s: %s without targets' % (c['id'], c['status']))
        if c['status'] == 'unresolved' and not c['reason']:
            errori.append('%s: unresolved without a reason' % c['id'])
    return errori


def sommario(t, voci, links, cit, versi, B, decisioni):
    stato = Counter(c['status'] for c in cit)
    canoniche = [c for c in cit if c['source_status'] != 'noncanonical']
    piu = sorted(versi, key=lambda x: (-x['n'], B.verses[x['id']]['order']))[:20]
    stretti = sorted(versi, key=lambda x: (-x['narrow'], B.verses[x['id']]['order']))[:20]
    return dict(
        voci=len(voci), full=sum(1 for v in voci if v['kind'] == 'full'),
        redirects=sum(1 for v in voci if v['kind'] == 'redirect'),
        sections=sum(len(v.get('sections', [])) for v in voci),
        paragraphs=sum(len(v.get('paragraphs', [])) for v in voci),
        links=dict(Counter(x['type'] for x in links)),
        links_unresolved=sum(1 for x in links if not x['target']),
        links_tsv=t['links_tsv'], links_read_again=t['links_read_again'],
        citations=len(cit), recovered=sum(1 for c in cit if c['source_status'] == 'recovered'), status=dict(stato),
        pct_resolved=round(R.pct(stato['resolved'], len(cit)), 2),
        pct_resolved_canonical=round(R.pct(stato['resolved'], len(canoniche)), 2),
        in_titles=sum(1 for c in cit if c['where'] == 'title'),
        implicit=dict(Counter(str(c['implicit']) for c in cit)),
        flags=dict(Counter(f for c in cit for f in c['flags'])),
        conversions=dict(Counter(re.sub(r'(?<=letter )[a-z]|\d+', 'N', c['conversion'])
                                 for c in cit if c.get('conversion'))),
        inferred=dict(Counter(lettura_tipo(c['inferred']) for c in cit if c.get('inferred'))),
        books=len({c['book'] for c in cit if c['book']}),
        verses_cited=len(versi), verse_hits=sum(x['n'] for x in versi),
        voci_citing=len({c['voce'] for c in cit if c['targets']}),
        top_verses=[dict(id=x['id'], n=x['n'], voci=len(x['voci'])) for x in piu],
        top_verses_narrow=[dict(id=x['id'], narrow=x['narrow'], n=x['n']) for x in stretti],
        unresolved_kinds=dict(Counter(c.get('reason_kind') for c in cit if c['status'] != 'resolved')),
        numbering=decisioni)


def lettura_tipo(inferred):
    """The kind of an 'inferred' note: aside, prose, paragraph, group, by hand, recovered."""
    for chiave, tipo in (('a reference the source did not link', 'recovered'), ('by hand', 'by hand'),
                         ('before the aside', 'aside'), ('named in the prose', 'prose'),
                         ('in the same parentheses', 'parentheses'), ('of the paragraph', 'paragraph')):
        if chiave in inferred:
            return tipo
    return 'other'


def riferimento(B, vid):
    v = B.verses[vid]
    return R.label(v['book'], v['chapter'], v['label'] if v['chapter'] else v['verse'])


def stampa(s, cit, B):
    print('voci: %d (%d full, %d redirects); sections %d, paragraphs %d' % (
        s['voci'], s['full'], s['redirects'], s['sections'], s['paragraphs']))
    print('links: %s; %d without a target (%d rows of links.tsv, %d read again)' % (
        ', '.join('%s %d' % kv for kv in sorted(s['links'].items())), s['links_unresolved'], s['links_tsv'],
        s['links_read_again']))
    print('citations: %d (%d in section titles, %d recovered from the text); %s; %.2f%% resolved (%.2f%% of the '
          'canonical ones)' % (s['citations'], s['in_titles'], s['recovered'], ', '.join('%s %d' % kv for kv in Counter(s['status']).most_common()),
        s['pct_resolved'], s['pct_resolved_canonical']))
    print('flags: %s; implicit book: %s; read in another book: %s; conversions: %s' % (
        s['flags'], s['implicit'], s['inferred'], s['conversions']))
    print('distinct verses cited: %d (%d verse hits) in %d books, by %d voci' % (
        s['verses_cited'], s['verse_hits'], s['books'], s['voci_citing']))
    print('top 20 verses (all citations naming them | citations of at most 3 verses):')
    for a, b in zip(s['top_verses'], s['top_verses_narrow']):
        print('  %-14s %4d in %3d voci     %-14s %4d' % (riferimento(B, a['id']), a['n'], a['voci'],
                                                        riferimento(B, b['id']), b['narrow']))
    print('numbering:')
    for d in s['numbering']:
        print('  %-4s %s\n       %s' % (d['book'], d['decision'], json.dumps(d['evidence'], ensure_ascii=False)))
    print('not resolved: %s' % s['unresolved_kinds'])
    for (raw, reason), n in Counter((c['voce'] + ' ' + c['raw'], c['reason']) for c in cit
                                    if c['status'] != 'resolved').most_common(80):
        print('  %-36s %s' % (raw, reason))


def prepara(dati, inp):
    """Everything dufour.json holds, and the errors of the checks (nothing written)."""
    t = carica(dati)
    B = R.Bibbia(json.load(open(inp, encoding='utf-8')))
    links, links_di = collegamenti(t)
    firme = autori(t)
    stelle_di = stelle(t)
    voci, testi = [], {}
    for e in t['entries']:
        v, ts = voce(e, t['json'][e['slug']], firme, links_di, stelle_di)
        voci.append(v)
        testi[e['slug']] = ts
    cit, errori = citazioni(t, testi, B)
    nuove = recuperate(t, testi, cit, B)
    ordine = {e['slug']: k for k, e in enumerate(t['entries'])}
    cit = sorted(cit + nuove, key=lambda c: (ordine[c['voce']], c['source_status'] == 'recovered'))
    versi = indice(cit, B)
    decisioni = numerazione(t, B, cit)
    errori = controlli(t, voci, links, cit, B, errori)
    s = sommario(t, voci, links, cit, versi, B, decisioni)
    return dict(t=t, B=B, voci=voci, links=links, citations=cit, verses=versi, summary=s, errors=errori)


def costruisci(dati, inp, out):
    """Build and write dufour.json; returns what prepara() returns."""
    p = prepara(dati, inp)
    meta = dict(
        source='%s (X. Léon-Dufour, Dizionario di Teologia Biblica, Marietti 1976)' % os.path.relpath(
            os.path.dirname(dati), os.path.dirname(C)),
        generated_by='tools/ontologia/dufour.py',
        ids=dict(voce='<slug> (entries.tsv)', paragraph='<slug>.<n>', citation='<slug>#<n> (n-th row of the '
                 'entry in biblerefs.tsv)', section='the path within its voce, as printed (VT I 2, 0 = before the '
                 'first heading)'),
        page='printed page of the dictionary (PDF index - 20)',
        html='<em> italics, <a class="voce" data-voce="<slug>"> a resolved *word',
        offsets='offset/length in the plain text (paragraph, or section title when para is null), '
                'html_offset/html_end in its HTML',
        flags=dict(s='and the next verse', ss='and following (to the end of the pericope, within the chapter)',
                   p='par.: and its parallels (not expanded)', **{'...': 'printed "...": and elsewhere'}),
        authors=[dict(id=a['id'], name=a['name'], given=a['given'], surname=a['surname'], order=a['order'],
                      place=a['place']) for a in p['t']['authors']],
        summary=p['summary'])
    dump(dict(meta=meta, voci=p['voci'], links=p['links'], citations=p['citations'], verses=p['verses']), out)
    return p


def main(a):
    inp = a[a.index('-i') + 1] if '-i' in a else IN
    out = a[a.index('-o') + 1] if '-o' in a else OUT
    quiet = '-q' in a
    dati = cartella(a)
    p = costruisci(dati, inp, out)
    s, errori = p['summary'], p['errors']
    if not quiet:
        stampa(s, p['citations'], p['B'])
    else:
        print('voci %d, sections %d, paragraphs %d, citations %d, %.2f%% resolved, %d verses cited' % (
            s['voci'], s['sections'], s['paragraphs'], s['citations'], s['pct_resolved'], s['verses_cited']))
    for e in errori[:30]:
        print('ERROR  ' + e)
    print('checks: %s; wrote %s' % ('ok' if not errori else '%d errors' % len(errori), os.path.relpath(out, C)))
    return 1 if errori else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
