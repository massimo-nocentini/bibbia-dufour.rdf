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
| `test_riferimenti.py` | stage 2 tests: 112 cases on strings of the corpus and 44 links read in the sense of the sentence (run by `costruisci.py`) |
| `dufour.py` | stage 2b: the Dizionario di Teologia Biblica (`../dufour/corpus`, read only) → `ontologia/build/dufour.json` |
| `test_dufour.py` | stage 2b tests: 98 citations of real rows, text, entries, links, numbering evidence, verse index (run by `costruisci.py`) |
| `paratesto.py` | stage 2c: the front matter and the appendices (`progetti/introduzione-generale`, `progetti/appendici`, read only) → `ontologia/build/paratesto.json` |
| `test_paratesto.py` | stage 2c tests: index references, misprints, dates of the chronology, woodcuts, canon, abbreviations, dynasties, acrostic letters (run by `costruisci.py`) |
| `rdf.py` | stage 3: the four JSON files (Bible, links, dictionary, front matter and appendices) → `ontologia/bj-dati.ttl.gz`, `bj-dati.nt.gz`, `bj-contesto.jsonld`, `bj-void.ttl` |
| `grafo.py` | loads `bj-dati.nt.gz` (and the ontology) into rdflib, fast |
| `verifica_rdf.py` | stage 3 checks: parsers, OWL sanity, SPARQL integrity, SHACL, JSON-LD |
| `interroga.py` | runs SPARQL queries (`ontologia/query/*.rq` or `-e`) and prints tables |
| `esploratore.py` | stage 4: the four JSON files + `esploratore/` → `ontologia/esplora.html` |
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
| `verses` | `id`, `book`, `chapter`, `verse`, `suffix`, `label` (as printed), `text` (plain, `\n` at poetry line ends), `html` (`<em>`, `<br>`), `poetry`, `page`, `pericope`, `order` (canonical, 1-based); optional `omitted`, `bracketed`, `printed_in_chapter`, `superscription` (psalm title), `acrostic` (Hebrew letters as printed), `acrostic_lines` (the line of the verse each opens, from 1) |
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
begins on their line, above). Acrostic letters (`\acrostico{Bet}`; `\acrostico{(Mem)}` when
printed in parentheses) are taken out of the text into `acrostic` of the verse they head (the
name without parentheses), with the line they open in `acrostic_lines` (1 when printed before
the verse; Na 1,3 Bet opens line 3) and, on a verse with a bracketed letter,
`acrostic_brackets` (true for each bracketed one: the five of Ps 10,3.4.6.10 and 25,18):
339 letters, in Psalms (174), Pr 31 (22), Lamentations (132) and Na 1 (11).

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

**The sense of the sentence.** After all the links are made, `context_links()` reads the
citations of the notes and introductions again where the sentence gives another book or
chapter than the grammar (rules first written for the Tufte edition in `tools/tufte/contesto.py`,
which now only maps their fields to its own names): `catena` (a chain the grammar broke goes on
in the book of the reference before: «Dt 24 passim; 26,12», «Ger 23,5 = 33,15», «Ez 38–39, in
particolare (cf. 38,22)»), `puntatore` («v N» right after a reference of another chapter: «Ger
39,1–10 (con un’aggiunta nel v 3)» is Ger 39,3), `capitolo` («v N» in a note on several
chapters: the chapter named last in the sentence, the next chapters of the label, or the next
chapter), `elenco` («vv 4,7,15»), the table `CORREZIONI` (48 rows read in the notes, each with
its reason: a «Giovanni» or «Marco» before the parentheses is a person, the symbolic acts of
Ezekiel listed in a note on Ger 18, …; a row that matches no reference stops the stage),
`ester` (also margins: a «+» to Esther goes to the text that has the key note) and `inizio`
(also margins: a range with a misprinted end is linked to its first verse, status `partial`,
the misprint kept as printed). It then adds two kinds of links: `introduzione` (the
siglum-less references of the introductions to several books, in the book of their sentence
or section), `nudo` (a bare «c,v» after a preposition in a note, «come in 11,7, o») and
`aggiunta` (the table `AGGIUNTE`: references the grammar does not read at all, each read on the
page image: «Nm 11,17 (Mosè); 25–26» is Nm 11,25–26, «ai cc 11, 27 e 31 del Deuteronomio» Dt 27
and Dt 31, «Dt 5, soprattutto vv 4 e 22» Dt 5,22). Each such
link has `corrected` (the rule), `corrected_from` (the former first verse) and `why`; they go
to the graph as `bj:interpretazione` («rule: why»). Current volumes: 87 links corrected
(manuale 48, inizio 16, catena 9, capitolo 8, puntatore 3, ester 2, elenco 1) and 821 added
(introduzione 747, nudo 70, aggiunta 4). The Tufte edition gets exactly the same links as before the port:
`genera.py` run on a scratch output wrote 95 byte-identical files and `test_genera.py` passes
10/10.

**Results** (current volumes): 18,455 margins → 28,669 links: 27,801 references, 99.95%
resolved (related 25,098, parallel 1,533, quoted-later 659, doublet 511), 866 numbering,
2 comments; 4,661 of them carry `+` (7,712 with the `+` of note and introduction citations). Notes: 10,762 label links and 25,437 citations in 6,485 notes,
99.71% resolved (before the sense of the sentence: 25,363 in 6,467 notes, 99.66%); introductions: 2,689 citations,
99.70% resolved (before: 1,942, 99.59%). The margins are unchanged in number and share
(6 of them now read again: 5 `partial`, 1 in the other Esther text). What stays unresolved
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

## Stage 2b: `dufour.py`, the Dizionario di Teologia Biblica

```sh
vendor/venv/bin/python -I tools/ontologia/dufour.py [--dufour ../dufour/corpus] [-i bibbia.json] [-o dufour.json] [-q]
vendor/venv/bin/python -I tools/ontologia/test_dufour.py [-v]
```

Reads the research corpus of X. Léon-Dufour (ed.), *Dizionario di Teologia Biblica*
(Marietti, Italian edition 1976): a separate folder, by default `../dufour/corpus` next to
this repository (`--dufour` another one; a clear error when it is missing), whose
`data/` is only read (`entries.tsv`, `entries/<slug>.json`, `links.tsv`, `biblerefs.tsv`,
`authors.tsv`, `entry_authors.tsv`; see its README). It writes
`ontologia/build/dufour.json` (about 32 MB, one record per line, byte-identical between
runs). A "word" of the dictionary is an entry (`voce`).

| Key | Records |
|---|---|
| `meta` | source, ids, flags glossary, the 70 authors, `summary` (counts, top verses, numbering decisions with their evidence, reasons) |
| `voci` | `id` (slug), `headword`, `kind` (`full`/`redirect`), `letter`, `pages` (printed, first and last), `authors` (id, name as in `authors.tsv`, signature, the part they signed), `targets` (redirect or see-also: `voce`, `form`, `path` as printed, `sec` the section it matched); full entries: `words`, `seealso`, `sections` (`path` as printed: `VT I 2`, `B NT III 2`, `0` before the first heading; `parent`, `kind`, `label`, `title`, `title_html`, `depth`, `page`) and `paragraphs` (`id` `<slug>.<n>`, `n`, `sec`, `page`, `text`, `html`) |
| `links` | `links.tsv` (18,215 rows) read again where the source left a see-also or redirect without a voce (below): `source`, `type` (`star`, `seealso`, `redirect`), `target` (null for the 9 still unresolved), `form`; star links their `sec`, `para`, `method`; the others `path`, `sec` (the target section), `path_status` |
| `citations` | one per row of `biblerefs.tsv` (`id` `<slug>#<n>`, the n-th row of the entry), then the references the source did not link (`<slug>#r<n>`, `source_status` `recovered`): `voce`, `sec`, `para` (null in a section title, `where` says which), `raw`, `abbr`, `siglum` (CEI, as read), `book` (OSIS), the numbers as read, `qual`, `flags` (`s`, `ss`, `p` for `par.`, `...`), `implicit` (0 printed, 1 inherited, 2 named in the prose, 3 the book of the paragraph before), `source_status`, `offset`/`length` in the plain text and `html_offset`/`html_end` in the HTML, `targets`, `ranges`, `status`, `reason`, `reason_kind`, and `conversion` / `inferred` when the row was read again |
| `verses` | the per-verse index, canonical order: `id`, `n` (citations whose targets include it), `narrow` (those naming at most 3 verses), `voci`, `citations` |

**Text.** The plain text drops the `*` of the cross-references (and the space after a
`*` printed apart, `* obbedendo`); a `*` glued inside a word is an apostrophe
(`dell*uragano`), except in `onni*potente`. The HTML has `<em>` for the italics and
`<a class="voce" data-voce="<slug>">` around each resolved `*word` (the 7 unresolved stay
plain text). Pages are the printed ones (PDF index − 20).

**Resolution.** Each row becomes one span for `riferimenti.resolve_as_printed`, so the
conventions are those of the BJ notes: CEI sigla (the source already maps the 1976
abbreviations, `Eccli` = Sir, `Eccle` = Qo, `1 Re` = 1Kgs), ranges across chapters,
chapter ranges, `s` the next verse (or chapter), `ss` to the end of the pericope within
the chapter, `par.` a flag (parallels not expanded), `...` (= and elsewhere) a flag;
Esther: the Hebrew text unless the verse is a lettered one of the Greek text. Rows read
again from the text: a letter of Greek Esther glued to the verse or printed after a space
(`Est 3, 13f`, `Est 4, 17 g LXX`), `8, 12l` (the source read `121`), a bare `Est 4, 17`
(cited for the prayers: `4,17a–z` of the Greek text, the Hebrew 4,17 says only that
Mordecai went away), an `s` glued to the verse (`Es 3, 7s`, 12 rows), `Ab` past chapter 3
(Obadiah, which the dictionary also prints `Ab`: `Ab 18`, `Ab 10, 14` = vv. 10 and 14), a
chapter range whose end is no chapter but a verse (`Mt 26 - 52` = Mt 26,52, `Mt 24-22`), a
range across chapters the source split at its full stop (`47, 13-48. 29` = Ez 47,13–48,29,
`Ebr 8, 1-10. 18`), the OCR `1 s 65, 2` (= `Is 65, 2`), and Sirach 34–36 (Numbering).
`ss` stops before the next verse the same printed group names (`Giob 38, 4 ss. 16 ss` =
38,4–15 and 38,16–41; `9, 15 ss. 30-33`), otherwise at the end of the pericope.

*Implicit books.* The source gives a bare reference the book of the last explicit one
before it in the paragraph. When that one is an aside, `cfr. X` or `= X` printed after
another reference inside the same parentheses (`(14, 16; cfr. Mt 28, 20)` in PARACLITO,
`(12, 44; 14, 1; cfr. 8, 24 = Es 3, 14)` in FEDE), the bare references after the
parentheses close go on with the book in force when they opened (Gv), until the next
explicit reference; an aside run goes on over the explicit references after it in the same
parentheses (`(1 Piet 1, 18 s; cfr. Es 12, 5; Is 52, 3)`), and the change is made only
when at least as many of those references exist in the restored book as in the aside's.
An aside that opens its parentheses (`(cfr. Sal 18, 28)` in POVERI) is not one: what
follows may continue it. 99 rows are read this way (PARACLITO, PREDICARE, PROCESSO,
FEDE, ESODO, SACERDOZIO, CROCE ...). A book named in the prose right before the
parentheses (`prima lettera di Pietro (5, 12)`) is read too. A row that does not exist in
its book is read in the other books cited in its paragraph when exactly one of them has
it (`(1, 46-55)` in MARIA is Lc 1,46–55), and then the other bare references of the same
parentheses that inherited the same book (`(12, 26 s; 13, 8 ss)` in PASQUA: Es, not Nm);
with two or more it stays unresolved (`reason_kind` `ambiguous-book`). A few rows and
paragraphs are read by hand (`CORREZIONI`, `PARAGRAFI` in `dufour.py`, each with its
reason: misprints such as `Deut 2 - 4` for Dan 2–4 and `1 Cor 9, 26-30` for 1 Cron, and
paragraphs whose book is named only in the prose, `nel Cantico (4, 11; 5, 1)`). A range
whose start exists but whose end does not is `partial`, cut at the last verse that exists
(`Sap 7, 8-41` → Sap 7,8–30); a start that does not exist is never read elsewhere.
Extra-canonical books (Enoch, Didachè, 4 Esd, Damasco) are unresolved with that reason.

*References the source did not link.* The source links a bare `(c, v)` only when a book
was printed earlier in the same paragraph, so a paragraph that continues the book of the
one before it has none (FEDE after a paragraph on John: `(5, 24)`, `(3, 16; 6, 47)`).
They are recovered (`<slug>#r<n>`, `implicit` 3, `source_status` `recovered`) in the book
named in the prose right before them, else the book of the citation before them in the
paragraph, else the book cited most in the paragraph before; only those that exist in
that book are kept (146). Four paragraphs where that book is wrong are set by hand
(ANTICRISTO `In Tess 2, 3-12`, SACERDOZIO ¶ 27, TERRA, SOLITUDINE; SACERDOZIO ¶ 26, on Hebrews, is set by hand for the rows of the source too), and VERITÀ ¶ 10 is left
out (Qumran texts).

*Links.* The see-also and redirect targets the source left without a voce are read
again (13): misprinted names (`regalità` = RE in MONARCHIA, `espansione` = ESPIAZIONE,
`trasformazione` = TRASFIGURAZIONE), a `NT` / `VT` that continues the previous target's
path (`tradizione VT II 2: NT I 1`) becomes a second link to that voce, and the other
pieces of a path (`re o`, `uragano 1-3`, `Gesù Cristo – d I1 d.`) are dropped; `carcere
III` (AMORE, PERDIZIONE) names no voce and stays unresolved.

**Numbering.** The dictionary uses the numbering of this Bible, so nothing is renumbered.
The evidence is measured at each build (`meta.summary.numbering`): the content words of
each quotation printed right before its reference (`«…» (Sal 23, 1)`) are compared with
the verse each numbering names. Psalms: Hebrew numbers, 151 quotations fit them and 1 the
Greek / Vulgate number (Sal 22 for 23); titles are verses (21 against 5 for the verse
before); `Sal 23, 1` «il mio pastore», the Miserere is `Sal 51`. 1–2 Re are 1–2 Kings
(15 and 7 quotations, none fitting 1–2 Samuel, the Vulgate 1–2 Re). Joel has 4 chapters
(`Gioe 3, 1-5` the outpouring of the spirit, 18 citations of chapter 3, 14 of chapter 4,
none of a Vulgate 2,28–32); Malachi 3 chapters (10 citations of 3,19–24, none of a
chapter 4); Esther no Vulgate chapter 11–16; Daniel 3,24–90 and 13–14 as in the CEI.
The one exception is **Sirach 34–36**: there the dictionary uses the older verse division
of its French original (that of the Bible de Jérusalem and the NAB 1970), while the CEI
2008 follows Ziegler, so its numbers land 1 to 4 verses early (`Eccli 36, 5` «Rinnova i
prodigi» is CEI 36,6; `34, 18` the unjust sacrifice is 34,21; `36, 10` «Raduna le tribù»
is 36,13; the prayer `36, 1-17` is 36,1–19). The table `SIRACIDE` converts each old verse
to its CEI verses, anchored on the passages the entries quote or paraphrase; 24 citations
are converted (`conversion`), and the build measures the words of the clause before each
one against the converted and the printed verses (10 fit the converted ones better, 3
the printed ones, 4 equally, 6 neither). Outside 34–36 Sirach quotations fit the cited
verse (35 against 1).

**Results** (current corpus): 849 entries (330 full, 519 redirects), 3,022 sections,
4,149 paragraphs, 18,207 links (10,061 star, 5,682 see-also, 2,464 redirect; 9 without a
voce); 30,257 citations (the 30,111 rows of `biblerefs.tsv` and 146 recovered):
99.69% resolved (99.73% of the canonical ones), 2 partial, 93 unresolved (`reason_kind`:
76 no such chapter or verse, misprints such as `Mt 31, 38 s`; 14 extra-canonical; 2
reversed ranges such as `Deut 18, 14-9`; 1 ambiguous book); 28,997 distinct verses cited
(130,806 verse hits) in 74 books, by all 330 full entries. Most cited, all citations:
Is 53,12 (58 in 41 entries), 53,11, 53,10, Gen 3,19; citations of at most 3 verses:
Gv 1,14 (35), Ez 36,27, Is 53,12, Ez 36,26.

**Checks** (exit status 1): counts equal `entries.tsv`, `sections.tsv`, `paragraphs.tsv`,
`biblerefs.tsv` (without the recovered citations) and the resolved star links of `links.tsv`; `biblerefs.tsv` and the
entry files agree row by row; every citation's offsets point at its raw text in the
plain text and the HTML; every target is a verse id; resolved and partial citations have
targets, unresolved ones a reason; every link target is an entry.

## Stage 2c: `paratesto.py`, the front matter and the appendices

```sh
vendor/venv/bin/python -I tools/ontologia/paratesto.py [-q]
vendor/venv/bin/python -I tools/ontologia/test_paratesto.py [-v]
```

Reads the two volumes of what the BJ prints before the Old Testament and after the
Apocalypse (never written here) and `bibbia.json`, and writes `build/paratesto.json`:

| Key | Content |
|---|---|
| `edizione` | imprint data (p. ii–iv): the 5 printings (`month` `2009-01` …), ISBN, publisher, sources, imprimatur, rights, printer, the colophon lines; the hand-made fields are checked against the printed text |
| `testi` | the Presentazione, the three prefaces, the two divisions of the canon, the Avvertenze: `title`, `subtitle`, `page` (Roman), `author`, `signature` and `qualifica` as printed, `italic`, `paragraphs` [{`n`, `page`, `titoletto`, `text`, `html`}] (the `\textsc` of the volume as `<span class="sc">`) |
| `canoni` | the Hebrew list (24 items in 3 parts) and the Greek one (Rahlfs): groups, items with the OSIS `books` (or `chapters`, `Dan.13`) they are in this Bible (`CANONE_EBRAICO`, `CANONE_GRECO`), `deuterocanonical` (printed in italics), `apocryphal` (in brackets) |
| `abbreviazioni` | the 147 rows of `abbreviazioni.tsv`: form, meaning, kind, page, `books` through the sigla of `canone.py`, `gregory` (Gregory-Aland number of a codex or papyrus) |
| `xilografie` | the 73 woodcuts of the Avvertenze: book, the passage(s) each illustrates |
| `indici` | the two indices: entries [{`n`, `lemma`, `html`, `style`, `page`, `sub` [{`k`, `label` as printed, `name`}], `items` [{`kind` rif/libro/vedi/pagina, `sv`, `raw`, `page`, `cf`, `seguito`, `link` (a typed link, kind `index-cites`, with `nota`/`notes`, `implicit`, `correction`), `to` (entries of a «v.»), `intros`}]}] |
| `cronologia` | `intro` (the paragraph before the table), `sections`, `columns`, `turn` (the row where section IX turns to d.C.), entries [{`n`, `section`, `row`, `margin`, `page`, `column`, `order`, `text`, `html`, `smallcaps`, `caps`, `date`, `start`, `end`, `circa`}] |
| `dinastie` | the 34 persons of `dinastie.tsv`: number, name, italics, dates, father, mother, spouses, note |
| `links` | the citations of the texts (`front-cites`) and of the chronology (`chrono-cites`), records of `riferimenti.record` with text and HTML offsets |

**The tables of the appendices** come from `progetti/appendici/tsv.py`, imported and run
with its output redirected to `ontologia/build/` (`cronologia.tsv`, `indice-note.tsv`,
`indice-temi.tsv`); the files of the volume are only compared (a difference is a warning:
they are stale). A shim in front of `riferimenti.py` keeps every reference `tsv.py`
resolves, so each row of the index gets the full typed link (flags, key notes, reason) and
its `nota` column (what the BJ has at the first verse: `nota` a note is called or starts
there, `copre` inside a note's label, `capitolo`, `rimandi`, `nessuna`) and `note`.
Misprints stay as printed; `CORREZIONI_INDICI` (16 rows, each with the evidence of
`progetti/appendici/checklist-ocr.md`, in Italian) adds a `correction` (raw, targets, the
notes there, why) where that log states the corrected reference: Caleb `Gb 14,6` → Gs 14,6,
`Lc 22,60` → 66, `Gv 13,24` → 34, `Mt 5,11` → 17, `Is 7,10` → 14 in the index of notes;
`Cr 28,9` → 1Cr, `Na 8,7–9` → Ne, `Sap 24,22` → Sir, `Gn 17,8` → Gen, `10.23` → Eb 10,23,
`12,47` → Gv, three Isaiah and two Psalm references printed after another siglum in the
themes. Each row must match one reference and resolve.

**Dates of the chronology**: the date as printed is the start of the entry before «:»
(«165», «Nov. 164», «164 inizio», «Estate o autunno 63», «Fra il 34 e il 45», «Primavera
50-estate 51», «Dall’1/2 al 4 d.C.,», «19 agosto 14», «Verso il 738», «589/8» = 589–588,
«Giugno-luglio 587 o 586», «141, giugno», «37 (o 38) ca.», «Tra 70 e 80 (?)») or, without it, the one span in parentheses («ASSARADDON
(680–669)»; two different spans: no date). Years: sections I–VIII before Christ; section IX
before Christ up to the first row whose entry starts with a «d.C.» date (row 122), after
it; a printed «a.C.» / «d.C.» wins; a range whose ends do not follow the era's order is
left without years. 387 of the 585 entries have a date, all with years (362 before stage 6b,
which read the leading day-month dates: «19 agosto 14: morte di Augusto. TIBERIO imperatore
(14–37)» is 14, not the reign 14–37). The conjectural dates printed in parentheses
(«(458: missione di Esdra, se …»)) stay without years.

**The woodcuts** are read from the two run-in paragraphs of the Avvertenze («Genesi (1,27);
… 1 Samuele (9,27–10,1); … Salmi (51, 3–4)»): each book named in full (`XILO_NOMI`, the names
of `riferimenti.LIBRI_NOMI` and a few more), its numbers read in that book.

**Checks** (exit 1): the regenerated tables equal the volume's (else a warning); every
index reference has a link, every target a verse id, every note id exists; every
correction used once and resolved; every «v.» target an entry (a target is matched on the
whole headword, then on its first words, «Presenza» → «Presenza di Dio», then by stem; the 3
printed cross-references that match no headword, `v. Festa`, `v. Tentazione`, `v. Sorte`, go
to `Feste d’Israele`, `Tentare`, `Sorti (tirare le)` by the table `RIMANDI` of tsv.py, with
`why`; the two page numbers that are not pages of this edition, «cf. pp. 1032, 1376», have no
introduction and a `why`, table `PAGINE_ESTRANEE`; a reference without siglum inside
parentheses takes the book named last in them, «Os 6,6 (citato in Mt 9,13 e 12,7)»: Mt 12,7);
the Hebrew canon has the 39 books of the Hebrew text once each and the Greek list every Old
Testament book of this Bible; the book sigla of the abbreviations are those of `canone.py`;
the parents and spouses of the dynasties exist and spouses are linked both ways; every
citation's offsets point at its raw text in the text and the HTML (a reference printed in
italics ends before the `</em>`). `test_paratesto.py`: 36 index, cross-reference and date cases, the texts,
woodcuts, canon, abbreviations, edition, dynasties and acrostic letters (5 tests).

**Results**: 7 texts (78 paragraphs, 51 Bible citations), 147 abbreviations (56 codices and
papyri, 49 with a Gregory-Aland number), 73 woodcuts; index of notes 628 entries, 550
sub-entries, 1,663 references (all resolved; 1,590 at a note's first verse, 48 inside a note,
17 margin references only, 8 nothing), 247 «v.», 20 pages; themes 96, 1,238 sub-themes (one
label printed twice in one theme), 3,285 references (3,259 resolved), 9 whole books;
chronology 585 entries, 174 citations; 34 persons; 16 corrections.

## Stage 3: `rdf.py`, `verifica_rdf.py`, `interroga.py`

```sh
vendor/venv/bin/python -I tools/ontologia/rdf.py [-q]
vendor/venv/bin/python -I tools/ontologia/verifica_rdf.py [-q]
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/*.rq [--limite N] [--largo] [--tsv]
vendor/venv/bin/python -I tools/ontologia/interroga.py -e 'SELECT ...'
```

`rdf.py` turns `bibbia.json`, `collegamenti.json` and `dufour.json` into RDF in the
vocabulary of `ontologia/bj-ontologia.ttl` (hand-written, like `bj-forme.ttl` and
`ontologia/query/`). One function per kind of resource (`struttura`,
`divisioni_e_pericopi`, `versetti`, `introduzioni`, `note`, `margini`, `rimandi`,
`citazioni`; for the dictionary `opera`, `pagine_dizionario`, `voci`,
`sezioni_e_paragrafi`, `autori`, `collegamenti_voci`, `citazioni_voci`, run by
`dizionario`); `Passaggi` describes each
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

**The dictionary** (`dizionario`, after the BJ, design in `ontologia/README.md`): the
work `id:dizionario` (`bj:Dizionario` and `skos:ConceptScheme`, title-page data in
`DIZIONARIO`), the 70 collaborators and 2 translators (`foaf:Person`, `persona:<id>`), the
778 printed pages (`bj:PaginaDizionario`, `pagdiz:<n>`), each entry (`bj:Voce`,
`skos:Concept`, `voce:<slug>`; redirects also `bj:VoceRinvio`; a redirect to one entry
only adds its headword as `skos:altLabel` there, 60), its sections
(`voce:<slug>/sezione/<path>`, the path folded to ASCII and `-` by `tratto`) and
paragraphs (`.../paragrafo/<n>`), every link of `links.tsv` reified
(`.../collegamento/<n>`, `bj:CollegamentoVoce`; the shortcut of its kind and
`skos:related` both ways, self-links left out; a `→` path `IV 0` names section IV), and
every citation (`.../citazione/<n>`, a `bj:Citazione` built by the same `riferimento` as
the BJ citations, from `bj:daParagrafo` or, in a section title, `bj:daSezione`; `bj:conCf`
when `cfr.` precedes it; the shortcuts `bj:voceCitaVersetto` and `bj:citatoNellaVoce` for
resolved and partial ones). Passages are shared with the BJ (`Passaggi`): 6,142 are new.
`Grafo` counts each triple in the part being built (`parte`: `bibbia`, then `dizionario`)
and gives each subject the part that described it first; `void()` writes them as two
`void:Dataset` subsets with their own class and property partitions (2,406,107 and
1,121,849 triples) and two `void:Linkset`s for the entry ↔ verse shortcuts, and checks
that the subsets add up to the graph. Literals gain `('y', '1976')` (`xsd:gYear`) and
`fr`. The output is still deterministic, and the Bible's triples are those of the build
before the dictionary, one for one (sorted N-Triples compared at stage 2: 0 removed; the
Bible subset still has 2,406,107 triples after the second audit).

**The front matter and the appendices** (`paratesto`, after the dictionary, design in
`ontologia/README.md`, *The front matter and the appendices*): `edizione_bj`,
`testi_preliminari`, `canoni`, `abbreviazioni`, `xilografie`, `citazioni_par`, `indici`,
`cronologia`, `dinastie`, counted as the part `paratesto` (a third VoID subset, with two
linksets for `bj:indicaVersetto` / `bj:nellIndice`). `PaginePar` describes the printed pages
once (`pagprel:<roman>`, `pagapp:<n>`); the citations of the texts, of the chronology and of
the indices go through `riferimento`, like every other citation, and share the passages
(`Passaggi`). New data namespaces: `testopre:` (id/testo/), `canone:`, `abbreviazione:`,
`manoscritto:`, `xilografia:`, `indice:`, `cronologia:`, `dinastia:`, `acr:` (the acrostic
letters, id/acrostico/; `testo` and `acrostico` are `bj:` terms, so they cannot be prefixes of
the JSON-LD context), `pagprel:`, `pagapp:`, and `schema:`. A citation read in the sense of the
sentence (stage 2, `corrected`) gets `bj:interpretazione` «rule: why». The acrostic letters of
`bibbia.json` (`acrostic`, `acrostic_lines`) become `bj:LetteraAcrostica` resources of the
Bible part. The counts of the checks include the new classes (`paratesto.json` against the
graph), the passages of the corrected index references too.

`grafo.carica()` loads the N-Triples with a reader that knows what `rdf.py` writes
(about 30–45 s for 3.5 million triples into a `SimpleMemory` store; rdflib's parser takes
about 2 minutes and a pickled store is no faster, so there is no cache). `verifica_rdf.py` loads the graph into a
`Memory` store (pyshacl needs a context-aware one) while two worker processes parse both
files with rdflib's own parsers; the three must give the same triples. Then: OWL sanity
(every `bj:` term used is declared with one kind, every `bj:` triple respects
`rdfs:domain` / `rdfs:range`, unions included), 43 SPARQL integrity queries on the whole
graph (20 for the dictionary: counts equal `dufour.json`, citations by status, every
citation target a declared verse, every link target an entry and its section in that
entry, parts inside their entry, `bj:voceCitaVersetto` equal to the JSON's (entry, verse)
pairs and backed by citations, `bj:citatoNellaVoce` its exact inverse, the 28,997 verses
of the verse index, entry shortcuts backed by printed links, `skos:related` symmetric),
the JSON-LD round trip (John 3,16 and the entry ABELE), and pyshacl with `bj-forme.ttl`
on the whole graph (25 node shapes; pyshacl's `focus_nodes` option is quadratic, about
36 ms a node, so a sample would be slower than everything: the whole graph takes about
4.5 minutes). About 9 minutes in all.

`interroga.py` loads the graph once, runs each query, prints the table and the timing,
and a summary for several queries (`--riepilogo F` writes it as Markdown; `costruisci.py`
writes `ontologia/build/query.md`); it exits 1 when a query returns nothing.

`verifica_rdf.py` adds 34 integrity queries for the front matter and the appendices
(`integrita_paratesto`: texts and paragraphs, the 39 books of the Hebrew canon, abbreviations
naming books, manuscripts, one woodcut per book, entries and sub-entries of each index,
references by status, every sub-entry under a top entry of its scheme, `skos:narrower` the
inverse of `skos:broader`, the «v.» links of the JSON, `bj:indicaVersetto` equal to the JSON's
(entry, verse) pairs and backed by a citation of that entry, `bj:nellIndice` its inverse, an
entry's `bj:indicaNota` backed by a citation, the note a citation points to at a verse of its
passage (2 exceptions, Esther: `Est 3,7` and `9,18` resolve to the Hebrew text, the BJ notes are
on the Greek one), the corrections, the chronology's entries, years in order, citations and
`bj:citaVersetto`, the persons and their links, the acrostic letters); with the rest, 76
queries, about 3 minutes; the citation counts and `bj:citaVersetto` pairs include the new
citations, `skos:related` is checked for the indices too. SHACL: 43 node shapes (18 new: the
edition, printings, pages, texts, canon, groups and items, abbreviations, manuscripts,
woodcuts, indices and entries, the chronological table, sections and entries, the
genealogical chart and its persons, acrostic letters); the citation shape takes an index
entry or a chronology entry as citing entity, and asks for text offsets only outside the
indices; a paragraph may be part of a front-matter text; a verse has up to 3 acrostic letters.

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

`esploratore.py` packs what the page needs from `bibbia.json`, `collegamenti.json` and
`dufour.json` into one compact JSON (20.3 MB, of which 6.5 MB the dictionary), gzips it
(5.9 MB, no timestamp) and embeds it as base64 in `ontologia/esplora.html` (8.5 MB; 5.9 MB
before the dictionary) with the stylesheet and the script of `esploratore/`.
The page loads nothing from the network: open it from disk (`file://`); the browser
decompresses the data with `DecompressionStream` (Chrome 80, Firefox 113, Safari 16.4).
The output is byte-identical between runs.

**Payload.** Verses are numbered by canonical order (`V.id[i]`, columns `l` label, `h`
HTML, `f` flags poetry/omitted/bracketed, `pg` page, `ac` acrostic letters with the line each
opens); every target
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

The front matter and the appendices are the key `par` (`paratesto()`, its docstring lists
the columns): the edition, the texts with their citations wrapped in `<a class="ci"
data-p="k">`, the canon lists, abbreviations, woodcuts, the two indices (entries, sub-entries,
items with runs, status, reason, the notes pointed to, the correction), the chronology
(entries with their citations as `<a class="ci" data-t="k">`, sections, columns), the
dynasties and the Hebrew letters. The citations of notes and introductions now carry the
reading of the sense of the sentence as their reason («letto nel libro del riferimento
precedente: la catena continua», …).

The dictionary is the key `diz`: `voci` (slug, name, full or redirect, letter, pages,
authors and the part they signed, signatures and the paragraph they follow, targets of a
redirect or a see-also list with the printed section path and the paragraph it starts at,
sections as printed, paragraphs with page and HTML), `cit` (entry, paragraph or section
title, section, runs of verse indices, status, flags `s` `ss` `p` `…`, printed text, reason
in Italian), `aut` (the 70 authors) and `meta` (counts, both top-20 rankings of
`dufour.json`). An entry is named in the case it has in the prose, taken from the see-also
and redirect forms that print it (`Spirito di Dio`, `padri e Padre`) or word by word from
them (`Agnello di Dio`), not in the capitals of the headword. Each citation is wrapped in
`<a class="cd" data-d="k">` at the offsets of `dufour.py`; a group printed once
(`Mi 25, 21. 23`: 2,932 citations in 1,373 such groups) is one anchor carrying
all its citations; a span crossing a tag (`<em>Mi</em> 5, 11`) is narrowed after it.
Resolved `*words` become `<a class="vl" href="#voce/<slug>">`.

**The page** (Italian, `app.js`, plain JavaScript, no library):

Fonts: Literata for the text and Inter for the interface, the variable woff2 files of
`@fontsource-variable` (Latin, Latin Extended, Greek for Literata), under the SIL Open
Font License (`esploratore/font/OFL-*.txt`); `esploratore.py` embeds them through
`esploratore/font.css` as `data:` URLs, so the page still makes no network request.


| View | Route | What |
|---|---|---|
| books | `#` | the books by testament and BJ volume, totals; four cards to the front matter, the two indices and the chronology |
| book | `#Gen` | chapters, divisions and pericopes, introductions |
| reader | `#Gen.1`, `#John.3.16`, `#Ps.23.1-4`, `#Deut.7.9?e=Deut.7.12` | the chapter as printed: headings, poetry lines, verse numbers, note calls (letters, buttons), margin signs (‖ ↗ = + •), page numbers; a plum `◊` beside the margin signs on the verses a dictionary citation names on their own or in a passage of at most 3 verses (12,175 verses; the tooltip and the verse's label give the entries and citations); heat (the flame) by in-degree or by the citations of at most 3 verses of the dictionary: the switch «Evidenzia: Rimandi BJ | Dizionario» above the text turns it on with that source (the pressed one turns it off), `d` switches the source; `e=` the other references of a list, highlighted and linked; the Hebrew letters of the alphabetic poems (Psalms, Pr 31, Lamentations, Na 1) in the left margin beyond the margin signs, beside the line each one opens, with the Hebrew character (inline at the line start under 1240 px) |
| verse panel | (with a verse) | the notes called here and those whose label covers the verse; the margin references by relation, unresolved ones grey with the reason; incoming margin references, note and introduction citations; «Nel Dizionario di Teologia Biblica»: every entry citing the verse (all citations whose passage includes it, the most specific entry first), each citation with the section path and title, the passage when wider, the flags (`s`, `ss`, `par.`, `…`) and the sentence around it with the citation marked; a click opens the entry at that paragraph; the number of entries also in the header; previews on hover (tap on touch screens); «Nell’indice delle note» and «Temi pastorali»: the (sub-)entries whose references name the verse (a corrected misprint by its corrected passage), most precise first, each reference as a chip with the BJ note it points to; «Nella tavola cronologica»: the entries citing it (most precise first) with their date, column and period, linked to the table; the woodcut that illustrates it, if any |
| graph | `#grafo/John.3.16[?p=2&f=parallel,doublet,diz]` | a tree to explore, left to right: the verse is the root, its links hang from it grouped by relation and direction (`‖ Paralleli`, `Affini →`, `← Affini`, `§ Le sue note citano`, ..., `◊ Nel Dizionario`; `f`: the relations shown, `diz` the dictionary); an entry of the dictionary is a card on lavender paper (its name, the section, the sentence around the citation) whose `▸` grows the passages it cites (those of the same paragraph first, `◊ La voce cita`) and whose name opens the entry; the most specific first, 8 per group at the root and 4 further on (`+10 di N` shows more); every card holds the reference, the passage text and the BJ notes it calls as yellow slips (`continua` opens one whole), inside an SVG contour drawn twice with a wobbly hand (seeded by the verse, so it is stable); `▸` grows a card's own links in place (a passage already on the path from the root is left out, so there are no cycles), `Apri un livello` grows every leaf (up to about 260 cards), `p=2` opens the first level at once; the reference of a card makes it the root; drag to pan, the wheel scrolls, Ctrl + wheel or +/− zoom, ⌂ fits the whole tree; "nessun collegamento" on the root when there is none |
| search | `#cerca?q=…&in=versetti\|note\|dizionario\|apparati&t=AT\|NT&b=Gen` | verse texts, notes and the dictionary, accents and case ignored, whole words (`ira` is not in «apparirà»; `ira*` for the start of a word), all words required (or a "phrase"), grouped by book, highlighted; the dictionary is a group of its own on top (entry names as chips, then paragraphs, more in pages of 50; left out by the testament and book filters); Back returns to the rows shown and the scroll position; «Appendici» (`in=apparati`, also in «Tutto»): a group with the index entries and themes matching (headwords and sub-entries, as chips), the chronology entries and the paragraphs of the front matter |
| overview | `#panoramica[/Gen/Matt]` | totals, margin references by relation (grouped as in the panel: they add up to the references), book × book matrix (click a cell: its references below, scrolled into view), the 50 most referenced verses; the dictionary: entries, citations, % recognised, verses cited, and the 20 verses it cites most, counting every citation or only those of at most 3 verses (the two rankings of `dufour.json`); four tiles of the appendices: entries of the index of notes, references to BJ notes with the share at a note's first line, themes, chronology entries |
| introduction | `#intro/intro-pentateuco[.3]` | an introduction with its citations as links |
| dictionary | `#dizionario[?q=spirito]` | the 849 entries by letter (letter buttons, disabled when the filter leaves the letter empty; a filter, kept in the address, and the scroll position, so Back returns to them): full entries with their number of citations, the 519 redirects in italics with the number of distinct entries they send to |
| entry | `#voce/abele`, `#voce/abele/2`, `#voce/abele/1?v=Gen.4.5` | an entry as printed: name, authors, pages, the sections with their headings (`VT`, `I.`, `1.`, `a)`, «…»), the paragraphs with italics, page numbers and the signatures, `*words` linking the other entries, the citations as links to the passage with the preview of the chips (unresolved ones grey, reachable with `Tab`, their reason in the preview on hover, tap or focus); section headings as headings for screen readers; a section index beside the text (a link clicked again scrolls again); see-also list and the entries pointing here (the path `0` shown as `introd.`; a target that is itself a redirect shows where it leads); a redirect lists its entries (at the section printed) and counts the distinct ones; `/n` scrolls to paragraph n (with its headings) and highlights it, or says the entry has no such paragraph, `v=` also marks the citations naming that verse, outlined inside the highlighted paragraph; the slug is normalised (`#voce/AGNELLO-DI-DIO`, `#voce/agnello di dio`) |
| front matter | `#introduzione-generale[/presentazione[.3]]`, `#introduzione-generale/abbreviazioni` | the edition (publisher, ISBN, printings, the colophon), the texts with their author, signature and position, printed in italics where the print is (the words in roman inside them upright), their citations as links; the two divisions of the canon with the list as printed and the books or chapters of this Bible each item is (an apocryphal one says it is not here); the Avvertenze and the 73 woodcuts as chips; the abbreviations and codices grouped as printed, book sigla linked, Gregory-Aland numbers |
| index of notes, themes | `#indice-note[?q=]`, `#temi`, `#indice-note/91[.2]` | the entries by letter with a filter kept in the address (as `#dizionario`); an entry: headword as printed (small caps, italics), its sub-entries, each printed reference as a chip (preview, unresolved grey with the reason; a misprint struck through with the corrected chip «→ Gs 14,6» beside it), in the index of notes the BJ note each points to («nota 14,6», a link opening the verse with that note) and the notes themselves below, closed, to read in place; «v.» to other entries, page numbers to the introductions; `.k` highlights a sub-entry |
| chronology | `#cronologia`, `#cronologia/6[?v=133]`, `#cronologia/dinastie` | the introduction of the table and its 9 periods (with the span of their years); a period as a table: the margin years and printed pages at the left, one column per column of the print (in print order), the entries with their italics and small caps, the citations as links, the date and years in the tooltip; `v=` highlights an entry; on phones the cells stack with the column name; the dynasties as a tree (children under the father, «da Mariamne I» when the wives are several, ∞ for marriages, numbers, italics and dates as printed) |

The reference box takes CEI sigla (`Gv 3,16`, `Sal 23,1-4`, `Gen 1`, `1 Cor 13`, `Gd 3`,
`Est 4,17a` → Greek Esther, `Sir prol 3`, `Sir prologo`), the forms printed in the BJ
(`Gen 2,4b`, `Gen 1,1-2,4a`, `Mt 5,3s`, `Mt 5,3ss` to the end of the pericope, `Mt 5,3p`,
`Dt 7,9.12`, `Gen 1,1; 2,4`: the first opens, the others are highlighted and linked), book
titles and short names (`Cantico dei Cantici 2`, `Prima Corinzi 13`, `I Cor 13`) and the
page's own ids; a known book with a chapter or verse it does not have gets a message
(«Gv 3,99: versetto inesistente (il capitolo ne ha 36)») with a link to search the words
instead; anything else is searched. Keys: `/` the box, `j`/`k` next/previous verse, `n`/`p` chapter, `g`
graph, `h` heat, `d` heat of the dictionary (and back), `t` theme, `?` help, `Esc` closes; `Tab` reaches the verses and the note
calls, `Enter` opens them and moves the focus to the panel. The help is a modal dialog
(focus inside, `Tab` kept in, `Esc` gives the focus back); route changes are announced
to screen readers; the theme button has `aria-pressed`. Muted text has a contrast of at
least 4.5:1 in both themes. On phones the panel is a bottom sheet whose handle makes it
tall or short, and the reader adds room under the text only while it is open. In-degree (heat, top 50, matrix) counts
the resolved margin references, other numberings excluded, naming a passage that includes
the verse (like `ontologia/query/05-piu-rimandati.rq`); for the dictionary, the citations
naming a passage that includes the verse (like `ontologia/query/14-piu-citati-dal-dizionario.rq`),
all of them or those of at most 3 verses. On phones the five tabs fit one line.

**Checks** (`esploratore.py`, exit status 1): every margin link and citation points at a
known margin, note or paragraph; every citation is wrapped; the printed chapters of each
book are contiguous; the page is under 30 MB and the script holds no `</script`.

**Browser test.** `prova_esploratore.mjs` opens the page from `file://` in headless
Chromium (desktop 1366×900, then a 390×844 touch phone) and runs 135 checks: first render
under 1 s,
no console error and no network request, the reference box (24 forms, and the messages
for `Gv 3,99`, `Ap 22,22`, `Sal 9,22`, `Gen 51`), Gv 3,16 → its note → a margin reference
(hover preview) → back, a `‖` parallel and back, a `+` reference opening the key note
(and Gv 2,20 `Mt 12,6+.38–40+` opening Mt 12,38), a whole-chapter chip opening the whole
chapter, `j`/`k`/`Esc`/`/`, the heat toggle, the search (accents, whole words `ira` vs
`ira*`, `Elìa` not finding `Eliàb`, `pane & vino` typed and reloaded, `#cerca?q=100%25`),
the testament filter, the graph (the root card with text, note slips and hand-drawn contour, groups and branches, ▸ growing a card, a slip opened whole, Apri un livello, a reference recentring, the Grafo tab writing
the verse in the address, `#grafo/Xyz`, filters in the address, a verse with no links),
the matrix click (the list in view at the first click; the bars adding up to the
references), the introduction, the book page, no title cut in the index, the contrast of
muted text in both themes, `Tab`/`Enter` on a verse and the focus in the panel, the
help dialog, an unresolved reference with its reason, the dark theme, and on the phone
the bottom sheet and its handle, tap previews, the 24 px note-call target, compact top-50
rows, the pair list inside the gutter, no blank page under a chapter and no horizontal
scrolling. On the dictionary: the panel of Is 53,12 (41 entries, 58 citations, as in
`dufour.json`), ABELE's `Gen 4, 4 s` with its flag opening `#voce/abele/1?v=Gen.4.5`
(paragraph highlighted and in view, the citation marked), previews, `*words`, signature
and see-also of an entry, a redirect, `#voce/xyz`, the section index, `#dizionario` (849
entries, 519 redirects, the filter), the search (`Jahvè` = `jahve`, the entries as a group),
the `◊` marker with its tooltip and label, the dictionary heat and `d`, the tree (the
`◊ Nel Dizionario` group of 8 entry cards on their tint, `▸` growing at most 4 passages,
`f=diz`, an entry's name opening it), the overview (tiles, both top-20 rankings equal to
`dufour.json`), the contrast of the plum in both themes, and on the phone the tabs on one
line, an entry, the index and the marker in the margin. The second audit of the
dictionary added 17: the data seen in the panel (FEDE cites Gv 10,30 and not Es 14,10
after `= Es 3, 14`; Gv 3,16 lists FEDE, a recovered citation; `Eccli 36, 5` on Sir 36,6),
every search row highlighted, pages of 50 and Back keeping them and the scroll, «1
voce», an unresolved citation reached with `Tab` and its reason in the preview, distinct
entries of a redirect, no phantom targets, MONARCHIA → Re, the citation outlined in the
highlighted paragraph, headings for screen readers, a normalised slug, a missing
paragraph, the index filter in the address and Back, the heat switch shown without the
flame. `--foto` saves the screenshots. playwright-core is not a
dependency of the repository: install it anywhere (`npm install playwright-core@1.64.0`
drives the cached `chromium_headless_shell-1248`); where the system lacks Chromium's
libraries (libatk, libgbm, libXcomposite…), unpack their Ubuntu packages
(`apt-get download`, `dpkg-deb -x`) into a folder and point `LD_LIBRARY_PATH` at it.
The front matter and the appendices added 35 checks: the four cards of the index, the
22 letters of Lam 1 in the margin left of the margin signs and Bet on the third line of Na 1,3,
the panel of Gs 14,6 (Caleb, «Gb 14,6» struck through, «→ Gs 14,6», the note), of Gv 1,14 (both
indices, as many entries as the data) and its «nota» opening the note in the panel, of Gen 4,22
(the chronology, the most precise entry first, opening highlighted), `#indice-note` (628 entries,
the filter in the address), an entry, a «v.», `#temi` (96) and an entry with an unresolved
reference and its reason, `#cronologia` (9 periods and the dynasties), a period (its columns,
entries and linked citations equal to the data), the dynasties (Herod's children with their
mothers), `#introduzione-generale`, the Presentazione (signature, italics, Sal 119,105 linked),
the Hebrew canon (24 items, Samuele = 1Sam and 2Sam), the abbreviations (63 book sigla,
Gregory-Aland), the 73 woodcuts, three searches (an index entry, the chronology, a phrase of the
Presentazione), the overview tiles against the data, `Tab`/`Enter` on a theme, the contrast in
the dark theme; on the phone six of the new pages without horizontal scrolling, an acrostic
letter inside the screen and the panel section.
Last run: 171/171 (stage 6b added Ps 10: 11 letters, «(Mem)» in parentheses with the
Hebrew letter and «mancante nel testo ebraico»), the page ready in about 0.63 s (data decoded in 0.33 s; 8.8 MB, before the
front matter and appendices 8.5 MB; before the dictionary 0.45 s and 0.2 s). The page was
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

Then two audits of the dictionary (stages 2b–4 above); every finding was reproduced
and fixed where it arose, with regression cases in `test_dufour.py` (98 citation
cases, links, numbering) and `prova_esploratore.mjs`. On the data: the bare references
after a `cfr.` / `=` aside (99 rows), a book named in the prose, the bare references of
the same parentheses, Sirach 34–36 in the older verse division, Obadiah printed `Ab`,
chapter ranges that are a verse, ranges across chapters the source split, `ss` stopping
at the next verse printed in its group, the OCR `1 s` for `Is`, misprints by hand, 146
bare references the source did not link, the see-also and redirect targets without a
voce, and query 13 (paragraphs before the first heading). On the page: search rows
without highlight (a stale `lastIndex` of a shared global regex), the reasons of
unresolved citations by keyboard and touch, distinct entries of a redirect, `introd.`
for the path `0`, the citation inside the highlighted paragraph, plural forms and pages
of 50, the index filter in the address, headings, slug and missing paragraph, the heat
switch. Not changed: the tree forgets a card grown with `▸` after Back (the tree is
rebuilt from its address, which records the root, depth and filters, not single cards).

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

With the dictionary (stages 2b–4) the same pass was repeated: `ontologia/` emptied of
everything generated and rebuilt by `make ontologia` (11 min 14 s, every check passed);
the three JSON files, both dumps, `bj-contesto.jsonld`, `bj-void.ttl` and `esplora.html`
came out byte-identical to the build before (`build/query.md` differs only in timings).
The browser test passed 135/135, and a check of completeness compared the page with
`dufour.json`: for every one of the 28,997 cited verses the entries and the number of
citations the page derives from its data, and the `◊` counts (12,175 verses), equal the
verse index; the panel of 66 verses, the `◊ Nel Dizionario` group of the tree for 25 and
the citation links of 43 entries (resolved ones linked, unresolved ones grey) agree with
it too. `bj-dati.nt.gz` (25.6 MB) joined `.gitignore` as a regenerable file over 20 MB;
an earlier commit still tracks it.

## Stage 7: the front matter and the appendices

The two volumes transcribed after the 14 (`progetti/introduzione-generale`,
`progetti/appendici`) and the acrostic letters added to Lamentations, Nahum and Ps 111–112
went into the ontology: the corrections of `tools/tufte/contesto.py` moved into
`riferimenti.py` (stage 2, *The sense of the sentence*: 87 corrected and 817 added links;
note citations 25,433, 99.71% resolved, introductions 2,689, 99.70%; the Tufte edition
regenerated byte-identical, `test_genera.py` 10/10), the new stage 2c (`paratesto.py`,
`test_paratesto.py`), the third part of the graph (vocabulary, 18 shapes, VoID subset, 33
integrity queries, 8 example queries), the explorer (panel sections, `#indice-note`,
`#temi`, `#cronologia`, `#introduzione-generale`, the letters in the margin, the search,
the overview; 35 browser checks). `make ontologia`: 13 minutes, every check green; 3,718,396
triples (3,527,956 before). Compared triple by triple with the previous build, the Bible part
lost 847 triples, all of the 87 citations read again (their former passages and statuses, the
`bj:citaVersetto` to the wrong verses), and gained the corrected and added citations, the
acrostic letters and the verse → index shortcuts.

## Stage 6b: fixes after the audit of the front matter and the appendices

- `riferimenti.py`: the table `AGGIUNTE` (rule `aggiunta`, 4 links the grammar does not read, each
  read on the page image: Nm 11,25–26 in the note on Is 11,2, Dt 27 and Dt 31 in the note on Gs
  8,30, Dt 5,22 in the note on Es 20,1); `test_riferimenti.py` 48 context cases. Links 67,553 →
  67,557; note citations 25,433 → 25,437. The Tufte edition already linked the last three (its
  own reading of the chain); only the note on Is 11,2 changed there.
- `progetti/appendici/tsv.py`: «v.» matched on whole words before the stem (Šekina → «Presenza
  di Dio», Peccato → «Confessione dei peccati»; the other 245 unchanged), the table `RIMANDI`
  (Festa, Tentazione, Sorte), `PAGINE_ESTRANEE` («cf. pp. 1032, 1376»), the class `Libro` (a bare
  reference in parentheses takes the book named last in them: Mt 12,7; no other reference of
  the indices or the chronology changed its book).
- `paratesto.py`: the leading dates of the chronology (387 dated, was 362; entry 423 is 14, not
  14–37), `why` on the «v.» and page items, `CORREZIONI_PROSA` for the Tufte edition.
- Acrostics: all `\acrostico{…}` (`estrai.py` reads only that macro), the name without
  parentheses and `acrostic_brackets` (5 letters) → `bj:mancanteNelTesto`; SHACL patterns on
  `bj:testo` and `bj:acrostico`; one more integrity query (77). `make ontologia` green
  (13 min); 3,718,625 triples (+229).

