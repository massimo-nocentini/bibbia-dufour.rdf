# Ontologia dei versetti

A verse-centred semantic-web base built from the 14 proofread volumes in `progetti/`
(CEI 2008 text, Bible de Jérusalem notes and marginal cross-references). The verse is
the central node: each one is linked to the notes called from it, the notes that
comment on it, and the verses its margin references point to. Code lives here,
generated files in `ontologia/` (intermediate files in `ontologia/build/`); the design of
the RDF graph, the identifiers and how to query it are in `ontologia/README.md`.

Rebuild everything:

```sh
make ontologia          # the same: vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

| Module | Role |
|---|---|
| `canone.py` | the 74 book sections: corpus id, OSIS code, CEI siglum, canonical order, verse ids |
| `estrai.py` | stage 1: LaTeX volumes → `ontologia/build/bibbia.json` |
| `riferimenti.py` | stage 2: reference parser and resolver → `ontologia/build/collegamenti.json` |
| `test_riferimenti.py` | stage 2 tests: 112 cases on strings of the corpus (run by `costruisci.py`) |
| `rdf.py` | stage 3: both JSON files → `ontologia/bj-dati.ttl.gz`, `bj-dati.nt.gz`, `bj-contesto.jsonld`, `bj-void.ttl` |
| `grafo.py` | loads `bj-dati.nt.gz` (and the ontology) into rdflib, fast |
| `verifica_rdf.py` | stage 3 checks: parsers, OWL sanity, SPARQL integrity, SHACL, JSON-LD |
| `interroga.py` | runs SPARQL queries (`ontologia/query/*.rq` or `-e`) and prints tables |
| `esploratore.py` | stage 4: both JSON files + `esploratore/` → `ontologia/esplora.html` |
| `esploratore/` | the page: `modello.html`, `stile.css`, `app.js` (inlined by `esploratore.py`) |
| `prova_esploratore.mjs` | stage 4 test: the page in headless Chromium (not run by `costruisci.py`) |
| `costruisci.py` | runs every stage in order, stops at the first failed check |

## Stage 1: `estrai.py`

```sh
vendor/venv/bin/python -I tools/ontologia/estrai.py [-o file.json] [-q]
```

Reads the book and introduction files of each volume (the sections of
`tools/progetti/progetti.py`, `prova-paolo` and `main.tex` excluded) and writes one
JSON file with one record per line. Top-level keys:

| Key | Records |
|---|---|
| `meta` | source, id scheme, totals |
| `books` | `osis`, `id` (corpus id), `siglum` (CEI), `title` (`\libro`), `title_long`, `volume`, `order`, `testament` (AT/NT), `file`, `chapters` [{`n`, `label`, `verses` [ids in numeric order]}] |
| `divisions` | `\parte`: `id` (`div:Gen.1`), `book`, `title`, `title_html`, `short`, `level` (1 = I., 2 = 1., 3 = A.), `parent`, `first`, `last`, `page` |
| `pericopes` | `\sezione`: `id` (`peri:<first verse>`), `book`, `title`, `title_html`, `short`, `opens_chapter`, `first`, `last`, `mid_verse`, `page` |
| `verses` | `id`, `book`, `chapter`, `verse`, `suffix`, `label` (as printed), `text` (plain, `\n` at poetry line ends), `html` (`<em>`, `<br>`), `poetry`, `page`, `pericope`, `order` (canonical, 1-based); optional `omitted`, `bracketed`, `printed_in_chapter`, `superscription` (psalm title), `acrostic` (Hebrew letters) |
| `notes` | `id`, `label` (as printed), `sign` (`•`), `anchor`, `offset`/`html_offset` (call position in the anchor's `text`/`html`), `word` (word before the call), `page`, `scope` (`verses`/`chapter`/`book`), `targets` (verse ids), `target_chapters`, `target_book`, `unresolved`, `text`, `html`, `latex` |
| `mrefs` | `id` (`mref:<anchor>_<position>`), `anchor`, `position`, `raw` (as printed, whitespace collapsed), `offset`, `html_offset`, `word`, `page`; `printed_in_verse` when the call stands in the text of the previous verse (below) |
| `intros` | `id` (`intro-…`), `volume`, `title`, `heading`, `books` (OSIS of the books it introduces), `file`, `paragraphs` [{`n`, `page`, `titoletto`, `text`, `html`}] |
| `anomalies` | `kind`, `where`, `detail`: every oddity handled (below) |

Pages are printed page numbers (PDF page = page + 33).

**Ids.** Verses are `<OSIS>.<chapter>.<label>`: `Gen.1.1`, `Ps.23.1` (Hebrew numbering
of the CEI, titles are verses), `Isa.7.8a` (verse parts printed as separate verses),
`Sir.Prol.1` … `Sir.Prol.35` (the translator's prologue, `chapter` 0). Esther is printed
twice: the Greek text with its lettered additions is `EsthGr` (`EsthGr.1.1a`,
`EsthGr.4.17z`), the Hebrew text is `Esth`; both have the CEI siglum `Est`. Baruch 6 is
the Letter of Jeremiah (`Bar.6.x`); Daniel keeps the Greek parts (3,24–90; 13; 14) in
the CEI numbering. Notes are `note:<anchor>` and `note:<anchor>_2`, … when several are
called from one verse.

**Anchors.** A note or margin reference belongs to the verse whose text contains its
call (it stands after the first word of a printed line). Calls printed between
`\capitolo` and the chapter's first verse (chapter notes, psalm notes) belong to that
first verse, at offset 0.

A margin reference followed by at most two words of its verse before the next
`\vs` (with no poetry line break and no heading in between) belongs to that next
verse, at offset 0: its printed line opens with the last word(s) of one verse and
goes on with the next one, and the reference is about the next one (`loro
schiere.\mref{Es 20,8+; …} \vs{2}` is the sabbath of Gen 2,2; `\mref{‖Mt 5,46}`
before Lc 6,32 is «se amate quelli che vi amano»). The rule was measured, not
guessed: counting the content words that the targets of a reference share with each
of the two verses, the next verse wins 272 to 79 for references with nothing after
them, 135 to 54 with one word, 190 to 78 with two, and only 155 to 109 with three;
with a poetry line break in between the previous verse wins (65 to 14), and for
references in mid-verse the verse they stand in wins 1,644 to 472. 1,250 references
are moved; each keeps `printed_in_verse` and an anomaly `mref-before-verse` saying
after which words it was printed.

**Lettered verses** of one number are listed in letter order, the unlettered one
where it is printed with respect to them (Greek Esther `1,1a–r` before `1,1`, `4,17a–z`
after `4,17`): Isa 10,18b is printed before 18a and Sir 28,24a–25b, Isa 7,8a–9b are
interleaved, but ranges and `chapters[].verses` follow the numbers
(`canone.numeric_order`, used by stages 1 and 2).

**Note labels.** `1,2` and `1,2–5`, ranges across chapters (`1,1–2,4a`), `9,44.46`;
a letter is a verse part (`1,2b` → verse 2) unless such a lettered verse exists
(`EsthGr` `4,17a–z`, `8,12s`, `Job.31.40a`); `s` adds the next verse; `ss` runs to the
end of the pericope (within the chapter); `v 6`, `vv 3–5` are verses of the current
chapter; `c 2`, `cc 8–10` are whole chapters; a bare number is a chapter when the
note stands before the first verse of a chapter (psalms) and a verse otherwise
(one-chapter books); `Nota introduttiva` is the whole book (`scope` `book`). Ranges
are expanded to the verses that exist, in numeric order, so a displaced verse
(Nm 25,19, printed at the top of chapter 26) falls in chapter 25. A label that
cannot be resolved keeps `unresolved` (none in the current volumes).

**Checks** (printed; exit status 1 if any fails): verses per chapter equal the
counts of `tools/progetti/verifica.py`; chapters per book equal `data/manifest.json`;
`\footnote` and `\mref` counts equal a plain grep of the files; every call has an
anchor and offsets whose plain and HTML prefixes agree; ids are unique; no
backslash, brace or call marker is left in any plain text. The per-book table also
shows the counts of the raw OCR tables (`data/notes.tsv`, `data/xrefs.tsv`) for
comparison only.

**Anomalies handled** (kinds in `anomalies`): `verse-omitted` (number printed, text
omitted by the CEI: Mt 17,21 …, `[44]` in brackets), `verse-bracketed` (EsthGr 4,6;
9,5), `verse-displaced` (Nm 25,19), `pericope-mid-verse` (a heading inside a verse,
e.g. Gen 2,4b), `note-without-label` (Sirach's prologue note: a note on the whole
prologue), `chapter-note-anchor` (Nm cc 26–30, anchored to 25,19, the first verse
printed in chapter 26), `mref-before-verse` (1,250 margins anchored to the verse that
begins on their line, above). Acrostic letters (Psalms, Pr 31) are taken out of the text
into `acrostic` of the verse they head.

## Stage 2: `riferimenti.py`

```sh
vendor/venv/bin/python -I tools/ontologia/riferimenti.py [-i bibbia.json] [-o collegamenti.json] [-q]
vendor/venv/bin/python -I tools/ontologia/test_riferimenti.py [-v]
```

Parses every margin reference, every note label and every reference cited in the
text of a note or an introduction, resolves it to the verse ids of `bibbia.json` and
writes one **typed link** per reference. `collegamenti.json` has `meta` (id scheme,
relation and flag glossary, `summary` with the counts below), `links` and
`unresolved` (each odd string with its reason and count). The API used by the tests:
`parse(text, ctx)` → references with their spans, `resolve(ref, Bibbia(data), ctx)` →
targets and status, `scan_prose(text, ctx)` → the references a text cites.

| Link field | Content |
|---|---|
| `id` | `<mref id>#<n>` (n-th reference of the margin), `<note id>#label`, `<note id>#c<n>`, `<intro id>.<paragraph>#c<n>` |
| `kind` | `mref`, `note-label`, `note-cites`, `intro-cites` |
| `source`, `source_verse` | the margin / note / intro paragraph, and the verse it stands beside (none for introductions) |
| `relation` | margins: `related` (no sign), `parallel` (‖, literary parallel in another book), `doublet` (=, same book or same text), `quoted-later` (/, printed ↗), `numbering`, `comment`; notes: `comments-on` (label), `cites` |
| `raw`, `sign` | the reference as printed (one item of a ";" list), its leading sign |
| `book`, `targets`, `ranges`, `target_book` | OSIS book, verse ids (ranges expanded), `[[first, last], …]` stretches, whole book (`Gs (passim)`) |
| `flags`, `keynote`, `keynote_verses`, `keynote_notes`, `keynote_mrefs` | `s` and the next verse, `ss` and following, `p` and parallels; `+`: the verse of each span carrying it (`17,8.23+` → 17,23 only), the notes it sends to (narrowest first) or, with no note there, the margin group beside that verse |
| `doublet_of` | margins: the reference a `=` is tied to (`‖2Cr 1,14=9,25`, `‖Lc 8,16; =11,33`): this one is its doublet, and the verse relates to it with that reference's relation |
| `inferred` | citations without siglum resolved in another reading than the inherited book (below) |
| `qualifier`, `alt` | `LXX`, `volg.`, `TM`, `TM var.`, `Tg`; another numbering printed with it (`3,96(29)`), or the number of a `numbering` link |
| `status`, `reason` | `resolved`, `partial`, `unresolved` (with the reason), `numbering`, `comment` |
| (note labels) | `raw` is `''` for the one unlabelled note (Sirach's prologue), never null |
| `offset`, `length`, `html_offset`, `html_end`, `cf` | citations only: where the reference stands in the note/paragraph `text` and `html`, and whether "cf." precedes it |

**Grammar.** CEI sigla (`1 Cor` with a space too); `c,v`; `.` joins verses of the same
chapter (`Dt 7,9.12`, `Gs 4,6s.21s`, `15,1+.19s.28s`); `–` (or `-`) ranges, also across
chapters (`Ag 1,14–2,9`) and books (`1Re 17–2Re 1`); `;` separates references (in margins
also a missing `;` before a siglum, `Dt 34,9 Gs 22,2`, and a sign glued to the previous
one, `2Cr 1,14=9,25`). A reference inherits the book of the previous one; the first one
without a book is the current book. A number without a comma is a chapter (`Sal 8; 104`,
`Gdc 13–16`), a verse in one-chapter books (`Abd 18`, `Gd 11`) and after `v`/`vv`
(`vv 3–5; 8`); `c`/`cc` are chapters; `.` never joins chapters (a margin `9.11` is
verses 9 and 11). A range from a chapter to a verse starts at the head of that chapter
(`Gen 1–2,4a` = Gen 1,1–2,4; `Sal 9–10,32` is unresolved, Ps 10 has 18 verses). A
misprinted item (`‖Lc 23,2–5,13–25`, a comma for a dot) stays one unresolved
reference. Letters: a lettered verse where one exists (Greek Esther `4,17u–y`,
`4,17de` = d–e, `4,17rs` = r–s, `Est 4,17(b)`), else a part of the verse (`2,4b`,
`12ab`); suffixes `s`, `ss` (to the end of the pericope, within the chapter, as for the
note labels), `p`, `sp`, `+`; qualifiers `(LXX)`, `(volg.)`, `(TM)`, `(TM var.)`, `Tg`,
`(passim)`; `Sir prol.`, `prologo 7–14` (Sirach's prologue).

**Esther.** `Est` is the Hebrew text (`Esth`) unless a letter after a verse names a
lettered verse of the Greek text (`4,17a`, `4,17rs`, `3,8.13de`, in any segment, at
either end of a range; `s`, `ss`, `p` alone stay "and the next" etc.) or only the Greek
text has the verse; a siglum-less reference in either Esther looks in that one first.

**Doublets.** `=` marks a doublet in the same book: a `=` without siglum after a
reference to another book is in the current book (`Is 25,8; =21,4` beside Ap 7,17 is
Ap 21,4), unless it is glued to the previous reference (`‖2Cr 1,14=9,25`,
`2Re 19,3=Is 37,3`) or follows a `‖` one (`‖Lc 8,16; =11,33` beside Mc 4,21): then it is
the doublet *of that reference* (`doublet_of`), and the verse relates to it as to the
previous one (parallel, or related). A `=` with another book written out (`=Es 34,6+`
beside Sal 86,15, 6 cases) is kept as printed.

**Psalms.** The CEI (Hebrew) numbering is used; `(LXX)` is kept as a qualifier only, since
the BJ uses it both for the Greek text with Hebrew numbers (`Sal 89,8 (LXX)` in 2Ts 1,9)
and for Greek numbers (`Sal 54,20 (LXX)` in Mt 26,22, left unresolved).

**Bare numbers in the margins.** Most margins holding only a number (`\mref{23}`,
`\mref{4 5 6}`) print the verse number of another tradition (the Vulgate in Gen 31–32,
Lv 5–7, Tb, Gdt, Greek Esther…, the TM in Dn 3, the LXX in Sir and Jer): they become
`numbering` links (no targets) when their chapter has an explicit one (`32,1 (volg.)`,
`24 (TM)`; not a chapter heading such as `LXX: 36`, which says nothing of the verse
numbers: Jer 29,17 `24` is Jer 24, the figs), three or more bare numbers, or two close
ones; dot-joined ones too (`9.11` in Gdt 14). A margin of Esther
pointing at 10,4–16,24 is the Vulgate number of an addition (`11,2`). An isolated bare
number is a chapter of the current book (`Gen 25,9` → Gen 23; `Dn 7,1` → Dn 2), which is
what the margins mean wherever it could be checked. A siglum-less reference with
`(volg.)`, `(LXX)`, `(TM)` is also a `numbering`; `(aramaico)`, `(ebraico)` (Dn) are
`comment`s.

**Citations in notes and introductions.** A chain of references starts at an explicit
siglum, at a book named in full right before `(3,1`, `: 3,1` or `(c 52` (`Isaia`,
`Geremia`, `Luca`… — not names that are also persons or words, like Giuda, Ebrei,
Sapienza), and, when there is a current book, at `cf. 3,1`, `(3,1`, a bare `3,1`, `v 6`,
`vv 3–5`, `c 2`, `cc 8–10`. Inside a chain `;`, `, `/` e ` before a reference, `(` and `[`
continue it (`Ger 1,11–12 (cf. 31,28; 44,27)` stays in Ger). Never a start: dates
(`36-25 a.C.`, `(44–46)`), manuscript sigla (P46, 1QpAb), measures (`22,5 cm`, `4,50
litri`), other numberings (`neovolg. (2,21)`, `la volg. (v 23)`, `TM 1,1`). The current
book is the note's book, the current chapter that of its first target; introductions
have a current book only when they introduce one book, and no current chapter.
Extra-canonical books (`3 Esdra`, `Enoc`, `Giubilei`, `Didachè`, `1QS`, …) and misprinted
sigla (`Zac`, `2Mc`) are kept as unresolved with that reason, and the references that
follow them in the chain inherit them.

**Key notes.** `+` sends to the narrowest note whose label starts at that verse, else one
called from it, else the narrowest (≤ 20 verses) commenting on it; with no note there, to
the margin references printed beside it (the "group of references" of the front matter).
The verse is the first of the span that carries the `+` (`keynote_verses`): in
`17,8.23+` only 17,23, in `/Mt 21,18–19+.33–44+` 21,18 and 21,33.

**Other readings of a citation without siglum.** When a citation that inherits its
book (from the chain, or the current book) names a chapter or verse that does not exist
there, these readings are tried in order and the first that resolves is kept, said in
`inferred`: the current book (`Sal 110 (cf. 22,41s)` in a note on Mt is Mt 22,41s); the
last book named in the text, by siglum or by name (`Gen 12,1 … In 12,1` in Ct 2,10 is Gen
12,1; `Ezechiele … (cc 16 e 23)` in Os 1,2 is Ez 16; a `(= Sal 82,6)` aside does not
count, so `Gv 10,34 (= Sal 82,6); 14,20` stays in Gv); verses of the previous chapter
(`Mt 27,56; 61` is Mt 27,61, `Lv 25,23–25; 47–49` Lv 25,47–49). In prose, `e`, `o`,
`e forse`, `e anche` continue a chain (`Mt 15,26 e forse 7,6`), and after a `= 2Re 19,4`
aside the chain goes back to its book (`Is 37,4 = 2Re 19,4; 37,31–32`). A reference whose
first verse exists but whose end does not (`2Mac 12,43–46`, `Gb 12,23–35`) is never read
elsewhere: that is a misprint or another numbering, and it stays unresolved. Readings
after an extra-canonical book or a misprinted siglum are not tried.

**Checks** (exit status 1 if any fails): every margin and note has a link; link ids are
unique; every target is a verse id; resolved links have targets, unresolved ones a
reason; every citation's offsets point at its raw text in the plain text and the HTML.
`test_riferimenti.py` runs 112 cases. Margin cases go through `printed(raw, verse)`,
which takes the real `\mref` printed beside that verse, so a case cannot test a string
the corpus does not have (five grammar probes that are not printed use `margin()` and
say so); note cases use real note texts. The cases marked F1–F12 are the regressions
of the stage 5 audit (margins before a verse, `Est 4,17rs`, `Is 25,8; =21,4`, `‖Lc 8,16;
=11,33`, `Sal 9–10,32+`, `9.11`, Jer 29,17 `24`, `17,8.23+`, `‖Lc 23,2–5,13–25`, the letter
order of Isa 10,18, siglum-less citations); `test_collegamenti_file` checks the written
file (no null `raw`, targets in numeric order).

**Results** (current volumes): 18,455 margins → 28,669 links: 27,801 references, 99.95%
resolved (related 25,098, parallel 1,533, quoted-later 659, doublet 511), 866 numbering,
2 comments; 4,661 of them carry `+` (7,707 with the `+` of note and introduction citations). Notes: 10,762 label links and 25,363 citations in 6,467 notes,
99.66% resolved (24 citations resolved through another reading, `inferred`); introductions: 1,942 citations,
99.59% resolved. What stays unresolved
(`unresolved` in the file, about 130 strings) is genuinely odd: misprints (`Fil 1,21–32`,
`Col 5,2`, `Mt 4,18–29`, `Lc 20,45–57`, `Sal 23,31 (LXX)` for Pr 23,31, `‖Lc 23,2–5,13–25`,
`1Re 4,38` for 2Re 4,38, `Est 10,31` probably for 10,3l), verse numbers of other editions
(`2Mac 12,46`, `Gdt 13,27`), extra-canonical books, and siglum-less references whose book
is only named in the prose around them (`dai Salmi (soprattutto 78,20…)`).

**Known limits.** A siglum-less `3,1` or `v 6` means the book in force: when a note
talks about another book without its siglum, the reference resolves wrongly if that
verse also exists in the book in force (only the ones that do not exist are read
elsewhere, above). `ss` is capped at the end of the pericope. A margin's line is known
only through its first word, so a reference pushed down the margin by a crowded column
(Lc 24,47 `Mt 3,2+` printed beside the line of 24,48) stays with the verse of its line.

## Stage 3: `rdf.py`, `verifica_rdf.py`, `interroga.py`

```sh
vendor/venv/bin/python -I tools/ontologia/rdf.py [-q]
vendor/venv/bin/python -I tools/ontologia/verifica_rdf.py [-q]
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/*.rq [--limite N] [--largo] [--tsv]
vendor/venv/bin/python -I tools/ontologia/interroga.py -e 'SELECT ...'
```

`rdf.py` turns `bibbia.json` and `collegamenti.json` into RDF in the vocabulary of
`ontologia/bj-ontologia.ttl` (hand-written, like `bj-forme.ttl` and `ontologia/query/`).
One function per kind of resource (`struttura`, `divisioni_e_pericopi`, `versetti`,
`introduzioni`, `note`, `margini`, `rimandi`, `citazioni`); `Passaggi` describes each
passage (first and last verse) once, expanding it with `riferimenti.Bibbia.between`, the
expansion stage 2 used. Triples are kept grouped by subject in the order they are made
and written by hand (Turtle with prefixed names and `,` lists; N-Triples), gzipped
without a timestamp: two runs give identical files. No blank nodes. The JSON-LD context
is generated from the ontology (object properties `@id`, integers and booleans typed,
`rdf:langString` ranges `@it`; `testoIt` is `bj:testo` with `@it`, for verse texts; a
term is never also a prefix, so pages are `pag:` there, `pagina` being `bj:pagina`).
Checks: declared terms with Italian and English labels and comments, object vs datatype
properties and ranges, no dangling IRI, counts equal to the JSON, passages equal to the
link targets, no duplicate triples. `void()` writes `ontologia/bj-void.ttl`, the VoID
description (title, rights, source, dumps, vocabularies, triples, entities, one partition
per class and per property, all with IRIs under `void#`), and parses it back to check
`void:triples`.

`grafo.carica()` loads the N-Triples with a reader that knows what `rdf.py` writes
(about 20 s into a `SimpleMemory` store; rdflib's parser takes about 65 s and a pickled
store about 47 s, so there is no cache). `verifica_rdf.py` loads the graph into a
`Memory` store (pyshacl needs a context-aware one) while two worker processes parse both
files with rdflib's own parsers; the three must give the same triples. Then: OWL sanity
(every `bj:` term used is declared with one kind, every `bj:` triple respects
`rdfs:domain` / `rdfs:range`, unions included), 23 SPARQL integrity queries on the whole
graph, the JSON-LD round trip, and pyshacl with `bj-forme.ttl` on the whole graph
(pyshacl's `focus_nodes` option is quadratic, about 36 ms a node, so a sample would be
slower than everything: the whole graph takes about 2.5 minutes). About 5 minutes in all.

`interroga.py` loads the graph once, runs each query, prints the table and the timing,
and a summary for several queries (`--riepilogo F` writes it as Markdown; `costruisci.py`
writes `ontologia/build/query.md`); it exits 1 when a query returns nothing.

**Choices** (details in `ontologia/README.md`): the verse is the hub; notes are
`oa:Annotation`s (`oa:hasTarget` the passage, chapter or book of the label, `oa:hasBody`
a `oa:TextualBody`, `bj:richiamataDa` the anchor verse); each margin reference is a
reified `bj:Rimando` (sign as a SKOS concept, `+`, `p`, qualifier, status) inside its
`bj:Margine`; citations in notes and introductions are `bj:Citazione`s; shortcuts
`bj:haNota`, `bj:commenta`, `bj:citaVersetto`, `bj:rimandaA` with `bj:paralleloA`,
`bj:doppioneDi` (both symmetric, both directions stored), `bj:citatoIn`,
`bj:rinviaANotaChiave` are materialised, closure included. A verse's label `25,19`
(Nm 25,19 printed in Nm 26) is the printed one. `bj:rinviaANotaChiave` goes only to the
verse of each span carrying `+` (`keynote_verses`), not to every target of the
reference. Three terms record the stage 5 decisions: `bj:stampatoNelVersetto` (a
`bj:Margine` anchored to the verse that begins on its line keeps the verse its call is
printed in), `bj:doppioneDelRimando` (a `=` tied to the previous reference of its
margin, `‖2Cr 1,14=9,25`: Rimando → Rimando) and `bj:interpretazione` (how a citation
without siglum was read when the inherited book has no such verse).

## Stage 4: `esploratore.py`, the offline explorer

```sh
vendor/venv/bin/python -I tools/ontologia/esploratore.py [-o ontologia/esplora.html] [-q]
node tools/ontologia/prova_esploratore.mjs --pw <folder with node_modules/playwright-core> [--foto <dir>]
```

`esploratore.py` packs what the page needs from `bibbia.json` and `collegamenti.json` into
one compact JSON (13.8 MB), gzips it (4.0 MB, no timestamp) and embeds it as base64 in
`ontologia/esplora.html` (5.4 MB) with the stylesheet and the script of `esploratore/`.
The page loads nothing from the network: open it from disk (`file://`); the browser
decompresses the data with `DecompressionStream` (Chrome 80, Firefox 113, Safari 16.4).
The output is byte-identical between runs.

**Payload.** Verses are numbered by canonical order (`V.id[i]`, columns `l` label, `h`
HTML, `f` flags poetry/omitted/bracketed, `pg` page, `ac` acrostic letters); every target
is a list of runs of consecutive indices `[a, b, a, b, …]`. `libri` has the printed
chapters of each book as `[label, first, last]` (so Nm 25,19 sits at the top of Nm 26,
where it is printed); `peri` and `div` the headings; `note` the notes (anchor, call
offset in the verse HTML, label, sign, scope, HTML, targets, page); `mref` the margins;
`ml`, `nc`, `ic` the typed links of the margins, the note citations and the introduction
citations (relation, `+`, the notes a `+` sends to and the verses carrying it, flags,
qualifier, status and reason in Italian, printed text, whether a `=` is tied to the
previous reference; a citation read in another book says how). Books carry a short
name (`n`: `1 Corinzi`, `Matteo`, `Ester greco`) for the index and the reference box. The citations of notes and introductions are wrapped at the
offsets found by stage 2 in `<a class="ci" data-c|data-i>`; a citation printed across a
tag (`<em>3 Esdra</em> 2,6`) is narrowed to its part after the tag.

**The page** (Italian, `app.js`, plain JavaScript, no library):

| View | Route | What |
|---|---|---|
| books | `#` | the books by testament and BJ volume, totals |
| book | `#Gen` | chapters, divisions and pericopes, introductions |
| reader | `#Gen.1`, `#John.3.16`, `#Ps.23.1-4`, `#Deut.7.9?e=Deut.7.12` | the chapter as printed: headings, poetry lines, verse numbers, note calls (letters, buttons), margin signs (‖ ↗ = + •), page numbers; heat by in-degree (toggle); `e=` the other references of a list, highlighted and linked |
| verse panel | (with a verse) | the notes called here and those whose label covers the verse; the margin references by relation, unresolved ones grey with the reason; incoming margin references, note and introduction citations; previews on hover (tap on touch screens) |
| graph | `#grafo/John.3.16[?p=2&f=parallel,doublet]` | ego network, depth 1 or 2 (at most 150 nodes, the most specific links first), force layout on canvas, edges by relation (`f`: the ones shown), nodes by testament, zoom and pan, click (or the list of nodes) to recentre; the labels of the centre's own margin references first, none under the title; "nessun collegamento" when there is none |
| search | `#cerca?q=…&in=versetti\|note&t=AT\|NT&b=Gen` | verse texts and notes, accents and case ignored, whole words (`ira` is not in «apparirà»; `ira*` for the start of a word), all words required (or a "phrase"), grouped by book, highlighted |
| overview | `#panoramica[/Gen/Matt]` | totals, margin references by relation (grouped as in the panel: they add up to the references), book × book matrix (click a cell: its references below, scrolled into view), the 50 most referenced verses |
| introduction | `#intro/intro-pentateuco[.3]` | an introduction with its citations as links |

The reference box takes CEI sigla (`Gv 3,16`, `Sal 23,1-4`, `Gen 1`, `1 Cor 13`, `Gd 3`,
`Est 4,17a` → Greek Esther, `Sir prol 3`, `Sir prologo`), the forms printed in the BJ
(`Gen 2,4b`, `Gen 1,1-2,4a`, `Mt 5,3s`, `Mt 5,3ss` to the end of the pericope, `Mt 5,3p`,
`Dt 7,9.12`, `Gen 1,1; 2,4`: the first opens, the others are highlighted and linked), book
titles and short names (`Cantico dei Cantici 2`, `Prima Corinzi 13`, `I Cor 13`) and the
page's own ids; a known book with a chapter or verse it does not have gets a message
(«Gv 3,99: versetto inesistente (il capitolo ne ha 36)») with a link to search the words
instead; anything else is searched. Keys: `/` the box, `j`/`k` next/previous verse, `n`/`p` chapter, `g`
graph, `h` heat, `t` theme, `?` help, `Esc` closes; `Tab` reaches the verses and the note
calls, `Enter` opens them and moves the focus to the panel. The help is a modal dialog
(focus inside, `Tab` kept in, `Esc` gives the focus back); route changes are announced
to screen readers; the theme button has `aria-pressed`. Muted text has a contrast of at
least 4.5:1 in both themes. On phones the panel is a bottom sheet whose handle makes it
tall or short, and the reader adds room under the text only while it is open. In-degree (heat, top 50, matrix) counts
the resolved margin references, other numberings excluded, naming a passage that includes
the verse (like `ontologia/query/05-piu-rimandati.rq`).

**Checks** (`esploratore.py`, exit status 1): every margin link and citation points at a
known margin, note or paragraph; every citation is wrapped; the printed chapters of each
book are contiguous; the page is under 30 MB and the script holds no `</script`.

**Browser test.** `prova_esploratore.mjs` opens the page from `file://` in headless
Chromium (desktop 1366×900, then a 390×844 touch phone) and runs 89 checks: load time,
no console error and no network request, the reference box (24 forms, and the messages
for `Gv 3,99`, `Ap 22,22`, `Sal 9,22`, `Gen 51`), Gv 3,16 → its note → a margin reference
(hover preview) → back, a `‖` parallel and back, a `+` reference opening the key note
(and Gv 2,20 `Mt 12,6+.38–40+` opening Mt 12,38), a whole-chapter chip opening the whole
chapter, `j`/`k`/`Esc`/`/`, the heat toggle, the search (accents, whole words `ira` vs
`ira*`, `Elìa` not finding `Eliàb`, `pane & vino` typed and reloaded, `#cerca?q=100%25`),
the testament filter, the graph (depth 1 and 2, click to recentre, the Grafo tab writing
the verse in the address, `#grafo/Xyz`, filters in the address, a verse with no links),
the matrix click (the list in view at the first click; the bars adding up to the
references), the introduction, the book page, no title cut in the index, the contrast of
muted text in both themes, `Tab`/`Enter` on a verse and the focus in the panel, the
help dialog, an unresolved reference with its reason, the dark theme, and on the phone
the bottom sheet and its handle, tap previews, the 24 px note-call target, compact top-50
rows, the pair list inside the gutter, no blank page under a chapter and no horizontal
scrolling. `--foto` saves the screenshots. playwright-core is not a
dependency of the repository: install it anywhere (`npm install playwright-core@1.64.0`
drives the cached `chromium_headless_shell-1248`); where the system lacks Chromium's
libraries (libatk, libgbm, libXcomposite…), unpack their Ubuntu packages
(`apt-get download`, `dpkg-deb -x`) into a folder and point `LD_LIBRARY_PATH` at it.
Last run: 89/89, the page ready in about 0.45 s (data decoded in 0.2 s). The page was
also opened in headless Firefox 157 (playwright's `firefox-1555`, with the GTK 3
libraries unpacked the same way): reader, search, graph and overview, no console error.

## Stage 5: the audit

Two audits of stages 1–4 (data and page) found 27 problems; each was reproduced, fixed
where it arose and given a regression test (`test_riferimenti.py`, cases F1–F12, and
`prova_esploratore.mjs`). On the data: margins printed before a verse number moved to
that verse (stage 1, *Anchors*), Esther's two-letter tails (`4,17rs`), the `=` rules
(*Doublets*), chapter-to-verse ranges, dot-joined bare numbers, the `LXX: N` headings,
`+` only at the verse carrying it, one item per misprint, letter order of lettered
verses, no null `raw`, and other readings of siglum-less citations (stage 2). On the
page: the overview bars, the address decoded once, the reference box forms and
messages, whole-word search, the matrix click, the book names, the `+` chips, the
contrast, keyboard and screen-reader access, the phone tables and bottom sheet, the
graph's address, filters and labels, one wording for margin entries and references,
whole-passage chips and word-aligned snippets (stage 4).

## Stage 6: completeness pass

`ontologia/` was emptied of everything generated (only `bj-ontologia.ttl`, `bj-forme.ttl`,
`query/` and the README kept) and rebuilt twice, by `costruisci.py` and by
`make ontologia` (the new Makefile target): every check passed and `bibbia.json`,
`collegamenti.json`, `bj-dati.ttl.gz`, `bj-dati.nt.gz`, `bj-contesto.jsonld` and
`esplora.html` were byte-identical to the previous build and between the two runs.
Added: `bj-void.ttl` (VoID description of the data, written by `rdf.py`), the `vann:`
namespace prefix of the ontology, `/ontologia/build/` and `/ontologia/bj-dati.nt` in
`.gitignore` (regenerable and over 20 MB; the other generated files are under 20 MB).
The READMEs' counts were checked against the build (margin-only counts for `+`, `s`,
`p` and qualifiers in the sign table; triples per property).
