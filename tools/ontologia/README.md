# Ontologia dei versetti

A verse-centred semantic-web base built from the 14 proofread volumes in `progetti/` of the LaTeX
transcription (CEI 2008 text, Bible de Jérusalem notes and marginal cross-references). The transcription is a
repository of its own: the folder `corpus` next to this one, or `BJ_CORPUS` (`percorsi.py`, which every stage
uses for the paths it reads there: `progetti/`, `data/manifest.json`, `tools/progetti/`,
`progetti/appendici/tsv.py`, the images of the maps); the paths `progetti/…` below are in it. The verse is
the central node: each one is linked to the notes called from it, the notes that
comment on it, and the verses its margin references point to. Code lives here,
generated files in `ontologia/` (intermediate files in `ontologia/build/`); the design of
the RDF graph, the identifiers and how to query it are in `ontologia/README.md`.

Rebuild everything:

```sh
make ontologia          # the same: vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

(`make venv` first makes `vendor/venv` from `requirements.txt`.)

| Module | Role |
|---|---|
| `canone.py` | the 74 book sections: corpus id, OSIS code, CEI siglum, canonical order, verse ids |
| `estrai.py` | stage 1: LaTeX volumes → `ontologia/build/bibbia.json` |
| `riferimenti.py` | stage 2: reference parser and resolver → `ontologia/build/collegamenti.json` |
| `test_riferimenti.py` | stage 2 tests: 116 cases on strings of the corpus and 70 links read in the sense of the sentence, another numbering or a misprint (run by `costruisci.py`) |
| `numerazioni.tsv` | the numberings other than the CEI (Vulgate, LXX, the BJ's own, the older division of Sirach 34–36 of the dictionary) and how a reference printed in one reads in the CEI: read by `riferimenti.py` (16 references of the BJ) and `dufour.py` (the scheme `dizionario`) |
| `dufour.py` | stage 2b: the Dizionario di Teologia Biblica (`../dufour/corpus`, read only) → `ontologia/build/dufour.json` |
| `test_dufour.py` | stage 2b tests: 98 citations of real rows, text, entries, links, numbering evidence, verse index (run by `costruisci.py`) |
| `paratesto.py` | stage 2c: the front matter and the appendices (`progetti/introduzione-generale`, `progetti/appendici`, read only) → `ontologia/build/paratesto.json` |
| `test_paratesto.py` | stage 2c tests: index references, misprints, dates of the chronology, woodcuts, canon, abbreviations, dynasties, acrostic letters (run by `costruisci.py`) |
| `virgolette.py` | stage 2e: the quotations between « and » (direct speech, quoted words) of the text, the notes, the introductions, the front matter and the appendices → `ontologia/build/discorsi.json`; the one detector of the ontology, the explorer and the Tufte edition (`tools/tufte/discorsi.py`) |
| `test_virgolette.py` | stage 2e tests: the rules on strings, real quotations (Gen 1,3, Dt 5,1–26,19 and its nested ones, Sir 16,22 and Am 7,17, a poem, a note, an index headword, the edition), the counts (run by `costruisci.py`) |
| `integrazione.py` | stage 2d: the links between the parts, the calendar, measures and maps, every correction as an intervention (hand tables below) → `ontologia/build/integrazione.json` |
| `test_integrazione.py` | stage 2d tests: reviewed alignments and rejected ones, persons and their exceptions, datings, codices (D by book), measures and the prose misprints, the rows of every correction table (run by `costruisci.py`) |
| `allineamenti.tsv`, `persone.tsv`, `cronologia-libri.tsv`, `testimoni.tsv`, `calendario.tsv`, `misure.tsv`, `carte.tsv` | the hand tables of stage 2d, each with its header comment (what a row says, who reviewed it) |
| `eventi.py` | stage 2f: every dated event (the chronological table, the dynasties, the datings of the books, the maps, the dates written in the notes, introductions, front matter and Dizionario) on one time line → `ontologia/build/eventi.json` |
| `test_eventi.py` | stage 2f tests: 106 string cases (dated, never a candidate, refused), the sentence of a date, no reference ever a year, 38 real dates, the 585 entries, counts and order (run by `costruisci.py`) |
| `eventi-correzioni.tsv` | the dates of free text read by hand (era or not a date), stage 2f |
| `sinonimi.tsv` | the spellings that differ between the dictionary and the CEI text (David / Davide): the explorer's search |
| `rdf.py` | stage 3: the JSON files of stages 1–2f (Bible, links, dictionary, front matter and appendices, quotations, integration, time line) → `ontologia/bj-dati.ttl.gz`, `bj-dati.nt.gz`, `bj-contesto.jsonld`, `bj-void.ttl` |
| `grafo.py` | loads `bj-dati.nt.gz` (and the ontology) into rdflib, fast |
| `verifica_rdf.py` | stage 3 checks: parsers, OWL sanity, SPARQL integrity, SHACL, JSON-LD |
| `interroga.py` | runs SPARQL queries (`ontologia/query/*.rq` or `-e`) and prints tables |
| `statistiche.py` | writes the *Size* tables and the query table of `ontologia/README.md` from `bj-void.ttl` and `build/query.md` (`--controlla`: only check) |
| `esploratore.py` | stage 4: the five JSON files + `esploratore/` → `ontologia/esplora.html` |
| `esploratore/` | the page: `modello.html`, `font.css`, the two styles `stile-tufte.css` and `stile-giardino.css`, `app.js` (inlined by `esploratore.py`) |
| `prova_esploratore.mjs` | stage 4 test: the page in headless Chromium (not run by `costruisci.py`) |
| `costruisci.py` | runs every stage in order, stops at the first failed check |
| `percorsi.py` | where the LaTeX transcription is (`TEX`: `BJ_CORPUS`, else `../corpus`) |

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

**Psalms.** The CEI (Hebrew) numbering is used; `(LXX)` is kept as a qualifier, since the BJ
uses it mostly for the Greek text with Hebrew numbers (`Sal 89,8 (LXX)` in 2Ts 1,10, 10 of the 14
psalm references so marked); where the print uses the Greek numbering, `numerazioni.tsv` maps the
reference to the CEI verse (`Sal 103,12 (LXX)` in Mt 13,32 is Sal 104,12, `54,20 (LXX)` in Mt 26,23
Sal 55,21, `68,35 (LXX)` in 2Ts 1,10 Sal 68,36, `Sal 9–10,32+` in Ez 9,9 Sal 10,11).

**Other numberings** (`numerazioni.tsv`, rule `numerazione`). A reference the BJ prints in the
Vulgate's numbering (Es 22 in the note on Es 20,22, `2Mac 12,43–46` three times, `At 19,23–41`), in
the BJ's own (`36,27–31` in the introduction to Siracide) or in the Greek psalter is linked to the CEI
verse the table gives, its text as printed (`bj:interpretazione` «numerazione: …»). A row whose `cei`
is `=` makes the reference a numbering entry of its own verse (`13,27–28` beside Gdt 14,5, `per BJ:
36,29` in the note on Sir 36,26); `—` leaves it unresolved with the reason (`i vv 20–21 della volg.`,
`Sal 151`). A row that matches no reference stops the stage.

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
Extra-canonical books (`3 Esdra`, `Enoc`, `Giubilei`, `Didachè`, `1QS`, …) are kept as unresolved
with that reason, and the references that follow them in the chain inherit them. Misprinted sigla
(`MISPRINT`: `Zac` for Zc in the note on Am 7,7, `2Mc` for 2Mac in the note on At 26,7) are read as
the CEI siglum, the link marked `corrected` `refuso`; so are a misprinted reference of the margins
(`REFUSI_RIFERIMENTI`: `Sal 23,31 (LXX)` beside Ef 5,17 is Pr 23,31) and the two chains of the note on
Gen 6,5 the grammar cannot read (`REFUSI`: `7,1–2.3b–5.7.–10.12…` read 7–10, `…18–21.–24` read 24).
`gr.` glued to a verse is a qualifier (`1Sam 14,23gr.31` is 1Sam 14,23, Greek text, and 14,31).

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
elsewhere: that is a misprint or another numbering, and it stays unresolved (unless
`numerazioni.tsv` has it). Readings after an extra-canonical book or a misprinted siglum are not tried.

**Checks** (exit status 1 if any fails): every margin and note has a link; link ids are
unique; every target is a verse id; resolved links have targets, unresolved ones a
reason; every citation's offsets point at its raw text in the plain text and the HTML.
`test_riferimenti.py` runs 116 cases. Margin cases go through `printed(raw, verse)`,
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
chapter), `elenco` («vv 4,7,15»), the table `CORREZIONI` (62 rows read in the notes and introductions, each with
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
to the graph as `bj:interpretazione` («rule: why»). Current volumes: 117 links corrected
(manuale 62, numerazione 16, inizio 10, catena 9, capitolo 8, refuso 6, puntatore 3, ester 2,
elenco 1) and 821 added
(introduzione 747, nudo 70, aggiunta 4). The Tufte edition gets exactly the same links as before the port:
`genera.py` run on a scratch output wrote 95 byte-identical files and `test_genera.py` passes
10/10.

**Results** (current volumes): 18,455 margins → 28,669 links: 27,800 references, 99.97%
resolved, 867 numbering, 2 comments; 7,713 links carry `+` (margins, notes and introductions).
Notes: 10,762 label links and 25,437 citations in 6,485 notes, 99.76% resolved (before the sense of
the sentence: 25,363 in 6,467 notes, 99.66%); introductions: 2,689 citations, 99.81% resolved (before:
1,942, 99.59%). All links: 66,611 resolved, 869 numbering, 63 unresolved, 12 partial, 2 comments
(revisione 2026-10-31: 66,594, 867, 73, 21, 2 before it). The margins are unchanged in number and share
(6 of them now read again: 5 `partial`, 1 in the other Esther text). What stays unresolved
(`unresolved` in the file, about 130 strings) is genuinely odd: misprints (`Fil 1,21–32`,
`Col 5,2`, `Mt 4,18–29`, `Lc 20,45–57`, `Sal 23,31 (LXX)` for Pr 23,31, `‖Lc 23,2–5,13–25`,
`1Re 4,38` for 2Re 4,38, `Est 10,31` probably for 10,3l), verse numbers of other editions not in
`numerazioni.tsv` (`Sir 41,22–23`, partial), extra-canonical books (`Sal 151`, the Vulgate's `vv
20–21` of Gdt 13), and siglum-less references whose book is only named in the prose around them
(`dai Salmi (soprattutto 78,20…)`).

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
| `cronologia` | `intro` (the paragraph before the table), `sections` (`n`, `title`, `roman`; `text` and `html` of the line printed across the table under the title, `\testolargo`, when there is one: only VIII), `columns`, `turn` (the row where section IX turns to d.C.), entries [{`n`, `section`, `row`, `margin`, `page`, `column`, `order`, `text`, `html`, `smallcaps`, `caps`, `date`, `start`, `end`, `circa`}] |
| `dinastie` | the 34 persons of `dinastie.tsv`: number, name, italics, dates, father, mother, spouses, note |
| `links` | the citations of the texts (`front-cites`) and of the chronology (`chrono-cites`), records of `riferimenti.record` with text and HTML offsets |

**The tables of the appendices** come from `progetti/appendici/tsv.py`, imported and run
with its output redirected to `ontologia/build/` (`cronologia.tsv`, `indice-note.tsv`,
`indice-temi.tsv`); the files of the volume are only compared (a difference is a warning:
they are stale). A shim in front of `riferimenti.py` keeps every reference `tsv.py`
resolves, so each row of the index gets the full typed link (flags, key notes, reason) and
its `nota` column (what the BJ has at the first verse: `nota` a note is called or starts
there, `copre` inside a note's label, `capitolo`, `rimandi`, `nessuna`) and `note`.
Misprints stay as printed; `CORREZIONI_INDICI` (20 rows, each with the evidence of
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

## Stage 2f: `eventi.py`, every dated event on one time line

```sh
vendor/venv/bin/python -I tools/ontologia/eventi.py [-q] [--rivedi review.tsv]
vendor/venv/bin/python -I tools/ontologia/test_eventi.py [-v]
```

Run after `test_integrazione.py`. Reads `bibbia.json`, `collegamenti.json`, `dufour.json`,
`paratesto.json`, `integrazione.json` and the hand table `eventi-correzioni.tsv`, and writes
`build/eventi.json`: one list of every dated event of the material, in chronological order, for the
time line of the graph (`rdf.py`, stage 10 below) and of the explorer. Nothing is deduplicated: a note and a chronology entry on the same event
are two events, linked when that is certain (below). `--rivedi` writes a TSV of every date read in
free text and every candidate refused, for the review by hand.

| Key | Content |
|---|---|
| `meta` | `summary` (counts by source, precision, rule of the era, period, the placement of the chronology entries, the reasons of `non_datati`), `precisioni`, `fonti`, `ordine` |
| `periodi` | the 9 periods of the chronological table: `n`, `romano`, `titolo`, `inizio`, `fine` (the span that gives a date its period, below) |
| `eventi` | the events in order (fields below) |
| `non_datati` | every candidate the rules refused: `fonte`, `sorgente`, `apri`, `data` (as printed), `offset`, `motivo`, `frase` |

| Event field | Content |
|---|---|
| `id`, `n` | `ev:cronologia.<n>`, `ev:dinastie.<person>`, `ev:datazione.<dating>`, `ev:carta.<map>`, `ev:<source>@<offset>` (a date in free text); `n`: the position on the line, from 1 |
| `fonte`, `sorgente` | `cronologia` (entry `cronologia.<n>`), `dinastie` (person `P05`), `datazione` (row of `datazioni` of `integrazione.json`), `carta` (map id), `nota` (note id), `introduzione` (`intro-….<paragraph>`), `testo` (front matter `<text>.<paragraph>`), `dizionario` (paragraph `<entry>.<n>`), `sezione` (the line under the title of a period of the table, `cronologia.sezione.<n>`: read as free text, the era of the table, first among the table's events of the same years) |
| `apri` | where the explorer opens it: `#cronologia/<period>?v=<n>`, `#persona/<id>`, `#carte?c=<map>`, `#<anchor verse>` for a note, `#intro/<id>.<n>`, `#introduzione-generale/<id>.<n>`, `#voce/<entry>/<n>` |
| `data`, `offset` | the date as printed and where it starts in the plain text of its source (`text` of the note, paragraph or entry; none for rows, persons, datings and maps) |
| `inizio`, `fine` | first and last year, integers, negative = B.C. (no year 0) |
| `precisione` | `anno`, `intervallo`, `circa` (verso, intorno, ca.), `secolo`, `millennio`, `riga` (a chronology entry placed by its row), `periodo` (by its period only; none now) |
| `circa`, `limite`, `incerto`, `alternativa`, `parte` | approximate; `ante` (prima del, entro, fino al, anteriore al) or `post` (dopo il, a partire dal, sin dal, posteriore al, «Dalla fine del II sec.»; a negation turns it: «non potrebbe essere anteriore agli anni 80» is `post`; not the date of an origin, «che data dal II sec.»); a `?`; the other year, an integer signed like the years: «114 (o 78) a.C.» -78, «59 o 60» 60, «dal 52 al 59 o 60» 59; `inizio`, `metà`, `fine`… of a century |
| `era`, `era_da` | `a.C.`, `d.C.`, `a.C.–d.C.`; the rule that decided it (below) |
| `periodo` | the period (1–9) of the table: its section for an entry, else the period of `inizio`; null after 135 d.C. |
| `etichetta`, `frase`, `html` | a short plain label (the sentence, or a window of it around the date), the whole sentence (the entry's text), its HTML (the slice of the source's HTML, tags reopened and closed) |
| `verso`, `versetti`, `riferimenti` | the note's anchor verse; the verses the sentence (entry, map) cites as runs of verse indices of `bibbia.json` `[a, b, a, b, …]`; the references `[as printed, link id]` (stage 2, 2b, 2c, 2d links) |
| `cronologia` | entries: `voce`, `sezione`, `riga`, `colonna`, `margine` (the year printed in the margin of the row); and `data_da`: `tavola` (the date of stage 2c), `testo` (read in its text), `riga: anno a margine`, `riga: date delle altre voci`, `riga: tra le voci della colonna`, `riga: tra le righe vicine`, `periodo`, `colonna: intestazione` (the heading of a column) |
| `persona`, `tipo`, `libri`, `voce` | dynasties: the person, `morte` or `regno`; datings: the books (OSIS), `composizione`/`ministero`/`evento`, the entry |
| `stesso_evento`, `stesso_perche` | the events that are the same event (both ways: an entry lists its datings too), and why |

**The sources.**
- *The chronological table*: all 585 entries, each one event with its period, column, row and link. The
  388 dates of stage 2c are kept; an entry without one takes the first date its text gives under the
  rules below, with the era of the table (B.C. up to its turn, row 122 of section IX, A.D. after; a bound,
  «fino al 200», and a birth, «TIRAKA, … nato verso il 710; verso il 690 è coreggente», do not place an
  entry), and in the table also a year opening the entry («841 Salmanassar III…»), a hypothesis in
  parentheses («(428: missione di Esdra, se …)», `incerto`), a span after a name and a colon («GIOVANNI
  IRCANO (I): 134–104»), spans of reigns «N/M–K» («(305/4–281)», «(359/8–338/7)» is 359–337) and «N–M/K»
  («(404–359/358)» is 404–358), spans in parentheses of one or two digits («(9–6)», «(6–41)»), a span set
  off by a comma («(= Amenofi IV, 1374–1347)») and the first of two spans («Demetrio II (145–140 e
  129–125)»): 68 entries; a bound refused before the date is its other hypothesis («prima del 70? o verso
  l’80?»: 80, `alternativa` 70). Else its row: the year printed in its
  margin («1300; 1250» is 1300–1250), else the dates of the other entries of the row, narrowed in both
  cases by its column, since a column reads in order down the rows (`riga: tra le voci della colonna`, 39):
  it comes after the dated entry above it in its column (in its row; in a row without a margin year also in
  the rows above, when that entry starts within the row's years: «Ministero di Isaia» under «EZECHIA
  (716–687)», «Rivolta del sacerdote Mattatia» under «167–164: la grande persecuzione», not at the 171 of a
  Parthian king in the next column), and, starting with it, it ends no earlier («ALESSANDRO MAGNO (336–323) /
  Ha come precettore Aristotele» is 336–323, not 336–333, which sorted it first; so, in 2 rows, it leaves
  the margin year for the years of the entry above it: «Edom si rende indipendente» under «Ioram (848–841)»,
  margin 850; «Sotto Serse e Artaserse, Malachia …», printed under «445–443: prima missione di NEEMIA»,
  margin 450, with its 2 datings), and no later than the
  dated entry under it in its row («Pasqua 70 … / Presa delle terze e delle seconde mura … / Inizio di
  agosto: cessano i sacrifici … / 29 agosto 70» puts the two undated entries at 70, not at the 69–79 of
  the row, which sorted them before «Pasqua 70»; «Fine marzo – inizio aprile: morte di Erode» between two
  entries of 4 B.C. is 4 B.C., not 6–4); not where the column is out of order; margin 30, other entries
  48), else the rows
  around it (9, across the sections: from the latest start of the row before to the earliest of the row
  after, or, where the table is not in order there, from the latest start before to the latest after: «Una
  parte dei Sicari …» comes after «73: Flavio Silva …» and «Masada (Pasqua 74)» printed above it), else
  its period (none). An entry so placed always follows the entry printed above it in its column, except
  where the print itself is out of date order (6: the margins 950, 450 and 200 of «Rezon», «Ad Atene:
  Pericle» and «Scopas … si arrende», «Cazaèl … vinto» under the stele of Mesa «verso l’840», «Rabbi Giovanni
  ben-Zakkai» above «Tra 70 e 80 (?)», «Vangelo di Giovanni» above «La Didaché (fine del I sec.?)»). The 3
  headings of a column («ISRAELE», «GIUDA», «EGITTO»: one word in italic
  capitals naming its column, `intestazione()`) are not events: they open their column at the first year
  of the entry under them, however that one is placed (`colonna: intestazione`: «ISRAELE» and «GIUDA» at 931
  B.C., with Geroboamo and Roboamo, not at the 945–925 of Sisak's row; «EGITTO» at 716, with «24ª dinastia»,
  not at the 715 of BOCCORIS further down). The text dates refused are listed in `non_datati` («(la voce resta nella linea…)».
- *The dynasties*: the 6 persons with a date, «† 166» a death, «134–104» the years of a reign (as the
  chronology prints them). The era: «a.C.» is printed on Herod (37–4 a.C.); the Hasmoneans before him are
  B.C., his descendants (Agrippa I † 44, Agrippa II 48–95) A.D. (`ERE_DINASTIE`).
- *The datings of the books*: the 40 rows of `cronologia-libri.tsv` (`composizione`, `ministero`,
  `evento`), dated by their own words when they give a date other than the entry's (`data_da` `testo`, 3:
  «750 ca.: Amos e poco dopo Osea» in the row of GEROBOAMO II (783–743), «nel 50, le lettere ai
  Tessalonicesi», «Dal 53, lettere ai Filippesi e a Filèmone», a bound), «Del tempo di Alessandro: Zc 9-14» by
  the entry of ALESSANDRO MAGNO (336–323, `DATAZIONE_VOCE`), else by their entry (with its other hypothesis:
  «prima del 70? o verso l’80?»); the 120 `citato` rows are not datings of a book and are left out.
- *The maps*: the 8 maps with a period in `carte.tsv` («XIII sec. a.C.», «II-I millennio a.C.»), read
  by the same rules, with the verses of their passages; the two maps of the endpapers have none
  (`non_datati`).
- *Free text*: the 10,762 notes, the 21 introductions, the 7 front-matter texts and the 4,149 paragraphs of
  the Dizionario. One event per date expression, with its sentence (the sentence ends of stage 2; after
  «a.C.», «d.C.», «ca.», «sec.» or an initial only before a word that opens a sentence, `APRE`: «nel 19 a.C.
  Ciò situa la scena», «… 14 d.C. L’anno quindicesimo», not «nel 63 a.C. Pompeo», «All’inizio del II sec.
  a.C. Gesù Ben Sira»; never inside
  «a. C.» nor after «J. Ziegler», «F.M. Abel», «F.Ch. Baur», «per es.», «Ant. Giud.», «Ann.», «gr.»; a dash
  ends a sentence only after a full stop, the lemmas of a note, not inside one: «del tempio — dal 538 al
  520 — alla negligenza»; a sentence that opens with its date starts there, «… Ez 27,21). Nel 715, Sargon
  …»; the dash of a note's lemma that opens it is left out), the references of that sentence and their verses.

**The rules on strings** (`espressioni()`, then `data()`; `leggi(text, context)` runs both on a string).
The references are masked first: the citations of stage 2 (notes, introductions), 2b (dictionary), 2c
(front matter, chronology), with their offsets, and the tokens of a reference in words (`v 5`, `vv 3–5`,
`cap. 10`, `c 2`, `p. 123`, `nota 3`, `salmo 110`). A candidate is then:
- a number after a cue. Strong cues take two digits or more: `nel`, `nell’`, `verso il`, `intorno al`,
  `attorno al`, `circa il`, `prima del`, `dopo il`, `a partire dal`, `sin dal`, `fin dal`, `entro il`,
  `cioè il`, `nell’anno`, `dall’anno`, `l’anno`, `†`, a month or season before the year («giugno-luglio
  587», «Pentecoste 163», three digits; two digits are a weak cue read in the New Testament only: «febbraio
  44», «nell’inverno 54–55»), `gli anni`, `negli anni`, `degli anni`, `verso gli anni` («negli anni 61–63»,
  «negli anni 8–6»; «gli anni 80» alone is the decade 80–89), a colon or comma after «anno …» or «date …»
  (three digits: «Nel quarto anno di Ioiakìm: 605», «anno centosettantaquattro: 139–138», «Le date … sono
  quindi: 598, 587 e 582», «(quinto anno dell’esilio di Ioiachin, 593–592)»). Weak cues (`dal`, `al`, `del`, `fino al`, `anno`, `cioè`,
  `ossia`) take three digits or more, or an era suffix; «il 587» is read only with a suffix; a month
  before a weak cue makes it strong («16 marzo del 597»);
- `dal N al M`, `tra il N e il M`, `fra il N e il M` (one range; two digits need a suffix after `dal`); a
  range with a month, a season or the part of a year at its ends (`TRA_MESI`, `TRATTINO_MESI`: «fra dicembre
  del 589 e gennaio del 588», «tra la fine del 486 e l’inizio del 485», «tra l’ottobre del 141 e il settembre
  del 140», «dal 19 agosto del 28 al 18 agosto del 29», «dal settembre-ottobre del 27 al …», «dall’autunno del
  49 alla primavera del 50», «dalla primavera del 50 alla fine dell’estate del 51», «dal 626 circa al luglio
  del 587», «Dicembre 589 – gennaio 588»; two digits as after a month, in the New Testament only: «tra
  l’autunno 48 e l’estate 49»);
- a number before an era suffix: `a.C.`, `a. C.`, `d.C.`, `avanti Cristo`, `dopo Cristo`, `della nostra
  èra`, `prima della nostra èra`, `dell’èra cristiana`; a suffix after the last of a list or a range
  applies to all («dal 445 al 433 a.C.»), two suffixes make a range across the eras («dal 4 a.C. al 39
  d.C.», «(20 a.C. – 54 d.C.)»);
- a number of three or four digits (or with a suffix) right after «(» and followed by «)», «;» or «,»
  («Ramses II (1290–1224)», «Acazia (841)», «(598; cf. 2Re 24,14s)»; two years of four digits, «(1955 e
  1973)», «(1971; 1974)»), or of one or two digits after a title or «anni» («procuratore Cuspio Fado
  (44–46)», «regno di Claudio (41–54)», «due anni (52–54)», «sotto Nerone (64 o 67?)»; not «in Cristo
  (9–11)», chapters; a single year of two digits after «regno di», «dal regno di Erode (37)»; two
  descending spans, «(145–140 e 129–125)»), a number followed by `ca.` (also after «dal … al …»: «dal 1720
  al 1552 ca.»);
- set off by commas: a descending span of three or four digits after a word or «)» («Cofra (Aprie),
  589–570, presso cui», «(= Amenofi IV, 1374–1347)»; not «Ant. Giud. XIII, 171–173», ascending), a year
  after an event and its name («battaglia di Gaza, 312,», «morte di Pietro, 64 o 67,»: `EVENTO_VIRGOLA`);
- «il N e il M» with a suffix on the second («il 30 e il 33 d.C.»: both);
- the next years of a list after one of these («nel 597, 587, 582»: three digits; «gli anni 50–52 e 53–58»);
- a century: `IV secolo`, `sec. VIII`, `XIII sec.`, `nei sec. VIII–IX`, `dal IV al III sec.`, `dal sec.
  VIII al sec. IV`, `secoli XIII e XII`, `primo secolo`, with `inizio`, `prima metà`, `metà`, `seconda
  metà`, `fine` (the first 25, 50, the middle 50, the last 50, 25 years); a millennium: `II millennio`,
  `secondo millennio`, `II-I millennio`. The Roman numerals are upper case only («i secoli» is not I sec.);
- the turn of the era: «all’inizio (dal principio) della nostra èra», «sull’inizio dell’èra cristiana» is
  1–25 d.C., «alla vigilia della nostra èra» 25–1 a.C., «intorno (vicino, in prossimità) all’èra cristiana»
  25 a.C. – 25 d.C., all `circa`; «prima della nostra èra» is the bound `ante` of 25–1 a.C., «posteriore
  all’èra cristiana» the bound `post` of 1–25 d.C. (`NOSTRA_ERA`; not «il 753 come inizio della nostra èra»,
  nor a year before its suffix, «nel 63 prima della nostra èra»).
- the words just before an expression may make it approximate («va fatto risalire pressappoco al 605»,
  «risalire circa fino all’VIII secolo»: `CIRCA_PRIMA`) or a bound («in ogni caso prima della fine del
  febbraio 44»: `ante`, `LIMITE_FINE`; «a partire dal regno di Erode (37)», «a partire dal sinodo romano del
  382»: `post`, `LIMITE_DA`, singular only: «computato a partire dalla primavera (del 311)», «a partire dalle
  due precedenti edizioni (1955 e 1973)» are not bounds); the part of a decade is read as of a century
  («all’inizio degli anni 40»: 40–42).

A range `N–M`, `N/M` (`589/8` is 589–588: the short form only after a slash; `143-37` is 143–37; a longer
second year only when it is larger, «(64–135 d.C.)»), `N/M–K` («(455/454–403 ca.)»), `N–M/K`
(«(404–359/358)»), `N o M`, `N oppure M`, `nel N o nel M` («nel 735 o nel 732», «nel 64 o nel 67»), `dal N al
M o K` («dal 52 al 59 o 60»: 52–60) is one event. Refused (with the reason in `non_datati`): an ordinal («15°»), a count («40
anni», «400 m»: a unit after the number), a day («14 nisan», «il 14 del mese» and, after a weak cue, a
number up to 31 in a sentence that names a month), a regnal year («nell’anno 15 di Tiberio»), a year of
another era («169 seleucidico», «782 di Roma»), a sum («10+7»), one digit without a suffix, a weak cue
with fewer than three digits, a number in parentheses right after a reference («di 12,11 (1290)»: the
number of the verse), a psalm number in parentheses in the Psalms («un inno regale (144)»). Never a
candidate: a number glued to letters (`2Re`, `4QSam`), followed by `,5` or `.000`, or a book ordinal
(«nel 1 Sam»).

**The era** (`era_da`): the suffix (180); else a row of `eventi-correzioni.tsv` (31); else the order of a
range (descending is B.C., ascending A.D.: «(736–716)», «dal 59 al 67»; an ascending one in a text of the
Old Testament is refused, «Hallel (113–118)»: 164); else the source: notes and introductions of the Old
Testament B.C. (418; a year of four digits from 1500 or a century from XV without a suffix is refused
there: «nel 1947», «alla fine del XIX secolo», modern, go through the table), of the New Testament A.D.
(105: Paul, the war of 66–70, the Fathers, the canon, the manuscripts; their B.C. dates carry the suffix,
the exceptions «nel 168» (Antiochus) and «III sec.» (Cleanthes) are in the table; there a weak cue takes
two digits too, «dal 52 al 59», «febbraio 44», «tra l’autunno 48 e l’estate 49»: the 20 so read were
checked, all years), the front matter A.D. (22), a paragraph
of the Dizionario by its section (`VT` B.C., `NT` A.D. up to 135 and B.C. above: `sezione NT`), else by the
testament of the references of its sentence, else of its paragraph (`riferimenti AT`, `riferimenti NT, ≤
135`: 27; they were labelled `fonte AT` and `sezione NT` before the review of the feature), else B.C. above
135 and refused below («dopo il 70»). The chronology, datings and maps: the table (552 entries: `tavola` 164,
`tavola (stage 2c)` 388; and the 40 datings, `la voce della tavola`), the dynasties as above. `era_da` is the
key of the rule, sometimes with a qualifier after it («correzione: <reason>», «…; due cifre dopo «del» in un
testo del NT»): 53 distinct strings, matched by their start.

**`eventi-correzioni.tsv`** (34 rows, each read in its sentence; a row that matches nothing stops the
stage): `fonte`, `espressione` (as `data` prints it), `n` (the occurrence, 0 = all), `decisione`
(`a.C.`, `d.C.`, `scarta`), `motivo`. The A.D. years of Old Testament texts (the Arab chronicler of
1267 in the note on Gs 3,16, the Genizah and Masada of Siracide, Qumran 1947, Graf and Wellhausen, the
synod of 382 and the Trullo of 692, the Vaticanus, Cyprian, the editions of 1965–1986 and the CEI
translations of 1971 and 1974 in the notes on Est and Sir), the two B.C.
dates of New Testament notes, «dall’anno 2000» (B.C., 2Sam 5,9), the Dizionario's «dopo il 70», «sec. VI»
(Greece), «sec. II» (the Church), «sec. I» (the Jews of Jesus' time), and 3 numbers that are not dates
(Rev 11,13 «(1000)», the verses of Euripides' Medea in the note on Rm 7,15, a vague «verso il primo
secolo»).

**Periods.** Each period starts at the years of its title (IV 1200, V 931, VI 721, VII 538, VIII 333, IX
63 a.C.) or, for I–III, at the year in the margin of its first row (2000000, 3000, 1500), and ends the
year before the next starts; IX ends at 135 d.C. A date takes the period its start falls in; after 135
d.C. none (80 events: the Fathers, the manuscripts, the modern editions).

**The same event** (`stesso_evento`, both ways, 75 links): a date of free text, not a bound, with exactly
the years of a chronology entry dated by stage 2c or by its text, sharing a cited verse (15), the note's own
verse cited by the entry in a passage of up to 12 verses (14: «probabilmente nel 740» on Is 6,1 and «740
Vocazione di Isaia (Is 6,1)»; not in a whole chapter, «Marzo 160: Nicànore … (1Mac 7 …)» is not the note on
1Mac 7,1 «Verrà riconosciuto da Roma nel 160»), or a name the entry prints in small capitals or capitals
(42; four letters or more, generic words out: «Ramses», «Geroboamo», «Nabucodònosor»); a person of the
dynasties and an entry that names them (`persone.tsv`) with the same years, a death only to an entry that
tells a death («Erode Agrippa I † 44» is «44: morte di Agrippa I», not «Pasqua 44: … Agrippa I fa decapitare
Giacomo»: 4); a dating and its entry when it has the entry's years (36 of 40: not «750 ca.: Amos e poco dopo
Osea» and the reign of GEROBOAMO II). Links are made only when certain: a reader finds more (about 70 by the
review of the feature, with names not printed in capitals) and one doubtful one stays («Nel 58 viene
arrestato a Gerusalemme (At 21,27–23,22)» and «58 ca.: Felice … disperde la folla … del falso profeta
egiziano (cf. At 21,38)», a verse in common).

**Order**: by `inizio`, then `fine`, then the source (chronology, dynasties, datings, maps, notes in
canonical order, introductions, front matter, dictionary) and the position in it.

**Checks** (exit 1): the 585 entries on the line; integer years, start ≤ end, a precision and a source;
ordered; distinct ids; every row of the table used; every offset at its date as printed in its source;
every HTML well nested. `test_eventi.py` (12 tests): 156 string cases (99 dated, 19 never a candidate, 17
refused with their reasons, 2 never dated, 19 bounds), the sentence of a date (a dash inside it does not
end it; one that opens with its date starts there; after «a.C.» or an initial a sentence ends before a word
that opens one, not before a name; the references of the sentence before are not the date's), the bounds
(«anteriore al 735», «non … anteriore agli anni 80», «che data dal II sec.»), no reference of a sentence ever a year (strings parsed by
`riferimenti.scan_prose`, and every date of the file against the citation spans of its source), 38 real
dates read in their note, introduction, paragraph or entry (`nel 587` in the note on 2Re 25,8, `(736–716)`
in Gs 15,45, `nel 70 d.C.` and its reference Lc 21,20 in 2Sam 5,9, `Dal IV secolo d.C.` in Es 19,2, the
list of ESILIO, the rows of the table, the dates added by the adversarial review: «(41–54)», «verso gli anni
80», «negli anni 8–6», «febbraio 44», «(305/4–281)», «(6–41)», «(428: …)», TIRAKA; round 2: «(404–359/358)»,
AKNATON, Demetrio II, «Cofra (Aprie), 589–570», «battaglia di Gaza, 312», «morte di Pietro, 64 o 67», «regno
di Erode (37)», «dal 52 al 59 o 60», «verso l’inizio della nostra èra», «dal sec. VIII al sec. IV»; the
review of the feature: the spans with months, «nel 735 o nel 732», the datings by their words, the èra
cristiana, `riferimenti AT/NT`: 59), the entries placed by their row after the entry printed above them (15
pairs) and the headings before the entry under them, the same-event links (P29 to its death only, none
from a bound, by the note's verse, not by a chapter), «prima del 70? o verso l’80?», bounds and circa said
before, no sentence opening with a lemma's dash; all 585 entries with the dates of stage 2c unchanged, the
counts, the order, the periods by their numbers (not by `periodo_di`: the start year of each period is in
it, the year before in the one before) with `taglia_html` and `bilanciato` on strings, `non_datati`, the
table, the HTML.

**Results**: 1,547 events: chronology 585 (388 dated by stage 2c, 68 by their text, 129 by their row),
notes 546 (in 395 notes), introductions 267, Dizionario 68, front matter 26, datings 40, maps 8, dynasties
6, the line under the title of VIII 1; precision: year 680, range 378, circa 147, century 190, millennium 10, row 141. From 2,000,000 B.C.
(the first row of the table) to the third millennium of the preface; 1,107 B.C., 426 A.D., 13 across; 93
bounds.
`non_datati` 43: psalm numbers 11, days of a month 5, years of another era 5 (4 Seleucid, «782 di Roma»),
weak cues 4, bounds of an entry 3, ordinals 3, numbers of a verse 3, maps without a period 2, single digits
2, a birth, a sum, three rows of the table. `build/eventi.json`: 1.37 MB.

**Review** (round 1, adversarial): every one of the 934 dates read in free text and in the entries of the
table was read in its source; no date read in free text had a wrong year or era; the errors were 11 entries
of the table placed by a birth, by a later date of their text or by their row instead of their own span
(«(305/4–281)» and 5 more «N/M–K», «(6–41)», 3 hypotheses «(428: …)», TIRAKA; 5 entries of the same rows and
4 datings moved with them), 2 «ca.» lost after «dal … al», 2 lower bounds lost («dall’anno 200») and 7
sentences cut at a dash inside them; an independent scan of every number not read added 31 dates (the rules above
marked with «anni», a title, a month in the NT, a colon after «anno», «(1955 e 1973)», «il 30 e il 33
d.C.»). Still not read: «Cofra (Aprie), 589–570,», «battaglia di Gaza, 312,», «morte di Pietro, 64 o 67,»
(a bare apposition), «in tutto il 1900» (the century), bibliographic years («EDB 1992», «La Sacra Bibbia,
2008»).

**Review** (round 2, adversarial): the 908 dates of free text and the 65 entries dated by their text were
read again in their source, and mechanically: the sentence contains the date and is a slice of the source,
its HTML text is the sentence, the label holds the date, the references are the stage 2/2b/2c links whose
offset lies in the sentence, the verses their targets, the anchor the note's. No year, era, century or
circa was wrong. The errors were sentences (80 changed, 24 with other verses): 55 ran across a sentence end
after «a.C.», «d.C.», «sec.» into the next sentence or from the one before («… nel XIII sec. a.C. A Meneijeh
…», «… dell’anno 14 d.C. L’anno quindicesimo …», with its references), 18 began one sentence too early because the date opened its sentence (the
look-ahead of the sentence end was cut at the date: «… Ez 27,21). Nel 715, Sargon …», with the references
of the sentence before), 7 were cut at an abbreviation («J. Ziegler», «per es. Codex», «F.Ch. Baur», «(Gr.
II)», «Ant. Giud.», «ad es. Qumrân», «Ann. XV», «F.M. Abel»); 36 bounds were not marked («anteriore al 735», «a partire dal IV
secolo», «non … prima del III sec.»); «alternativa» was `true` for «N o M» and is now the other year; «dal
sec. VIII al sec. IV» was two events. Three entries of the table were placed by their row although their
text gives their span: «Artaserse II Mnemone (404–359/358)» (at 401), «AKNATON (= Amenofi IV, 1374–1347)» (at
the margin 1400), «Demetrio II (145–140 e 129–125)» (145–116). An independent scan of every number and era
word not read added 9 dates: «Cofra (Aprie), 589–570», «battaglia di Gaza, 312», «morte di Pietro, 64 o
67», «regno di Erode (37)», the turn of the era (5: «all’inizio della nostra èra», «alla vigilia …»),
and «dal 52 al 59 o 60» now ends at 60. 20 random entries checked on the scanned pages (46, 68, 125, 164,
191, 198, 205, 208, 332, 387, 415, 418, 425, 454, 479, 529, 560, 573, 579, 581): all match. Still not read:
«dal 626 circa al luglio del 587» (two events, 626 and 587: read since the review of the feature, below), «tra la fine del 486 e l’inizio del 485»
(two events: read since), «nel secondo quarto del II sec. a.C.» (the whole century), «prima della nostra
èra» (no year: read since, a bound).

**Review of the feature** (2026-11-03, adversarial, 37 findings): the entries placed by their row were
sorted before the entry printed above them in their column (240 before «ALESSANDRO MAGNO (336–323)», 273,
300, 384, 462, 482, 551, 552, 579, 126, 82, 219, 15 in all) and «EGITTO» after the entry under it: the column
rule above, now 6 left where the print itself is out of order. The same event: P29 (Agrippa I † 44) was
linked to «Pasqua 44 … fa decapitare Giacomo», a bound («i brani anteriori al 605») to Carchemish; +14 links
by the note's verse. Ranges with months at their ends were two events, and «dal 626 circa» a bound (12
ranges); «nel N o nel M» two events (3); 3 datings took the date of their entry instead of their own words;
the èra cristiana (6 events added), 2 approximations and 3 bounds said by the words before, the part of a
decade; the era rule of 27 dictionary dates named a section the paragraph does not have; «782 di Roma» was
refused as a regnal year; 55 sentences began with the dash of a lemma. The ids of the joined ranges are at
the start of the span now, the second year's event is gone: `@44`/`@62` of note:Jer.39.1_2 → `@31`, Ezek.24.1,
Ezek.29.1 `@9`/`@23` → `@0`, Ezek.33.21 `@9`/`@27` → `@0`, Ezra.4.6 `@170`/`@189` → `@158`, 1Macc.14.1
`@37`/`@60` → `@23`, Luke.3.1 `@265`/`@285` → `@251` and `@387`/`@415` → `@365`, intro-paolo.24
`@163`/`@177` → `@149`, intro-paolo.11 `@159`/`@181` → `@146`, intro-paolo.14 `@151`/`@180` → `@135`, and
Isa.5.26 `@130`, Matt.26.17 `@1254`, Acts.28.30_2 `@358`, Jer.1.2 `@69` merged into the event before. The
line «I diadochi si contendono l’impero di Alessandro (319–287)», printed across the table under the title
of period VIII (`\testolargo`), was in no build file: it is read since (stage 14), as the event
`ev:cronologia.sezione.8@49`. Not read yet: «in tutto il 1900» and «verso la metà del secolo scorso» (a century of the time of writing).

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

The time line is the key `tempo` (`tempo()`, from `build/eventi.json` of stage 2f; its docstring
lists the columns): the sources, the precisions, the 9 periods, the rules of the era, and the 1,547
events in the order of the line, each with its source and where it is read (an entry, a person, a
dating, a map, a note, a paragraph of an introduction, of a front-matter text or of an entry of the
Dizionario), its years (negative = B.C.), precision, the flags circa / uncertain / bound, the date as
printed, the period, the verses cited (runs), the anchor verse, the same-event links (both ways, as in
`eventi.json`), the column of the table, how a row was placed, the other year of «N o M» (signed, as in
`eventi.json`), the rule of the era and the part of a century or millennium as `eventi.py` read it («inizio
del II millennio»: the page printed «II mill.» before, deriving it with the thresholds of a century). A date
read in free text
carries its sentence as HTML cut from the payload's own HTML of its source, so its citations are the
`<a class="ci">` / `<a class="cd">` already there (the same targets, previews and reasons) and the date
is wrapped in `<mark class="tm-data">` (every one: a date that cannot be marked is an error now, not 10%
of them); `eventi.py` leaves a lemma's dash out of the sentence (it was dropped here). The other events
take their text from the payload at run time (the chronology entry, the person, the map with its
references). Checks: every event is in, every sentence is found in its source and its HTML has its
text, the wrapped citations of each sentence are as many as its references in `eventi.json`, every
date is marked (908 of 908 since the line of VIII, 907 after the review of the feature, 916 before). 353 KB of JSON, 94 KB gzipped; the page grows by 0.13 MB.

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

Fonts: ET Book (MIT License, `esploratore/font/LICENSE-ET-Book.txt`), the four faces of Tufte CSS
(roman with lining figures, italic with old-style figures, bold, roman with old-style figures for
the verse numbers), converted from its woff files to woff2 by `caratteri.py et-book <tufte-css>/et-book`
(about 145 KB). ET Book covers Latin-1 only, so Literata 3.103 (SIL Open Font License,
`esploratore/font/OFL-Literata.txt`) follows it in the stack for transliterations, Greek and the
other signs (about 60 characters, 9,264 occurrences in the payload); ET Book draws ‹ › as the ffi and
ffl ligatures, so its faces leave U+2039–203A to Literata. The six Literata woff2 files (Latin,
Latin Extended, Greek; upright and italic) are cut by `caratteri.py` from the upstream variable
fonts (googlefonts/literata, `fonts/variable/`), keeping both axes and the small capitals and
old-style figures. `caratteri.py` needs fontTools and brotli and is run by hand only when the fonts
change; `esploratore.py` embeds the files through `esploratore/font.css` as `data:` URLs, so the
page still makes no network request.

Styles: two complete stylesheets for the same markup, in the manner of the CSS Zen Garden, both
embedded (`STILI` in `esploratore.py`); a combo at the right of the bar («Tufte», «Giardino»)
switches them by disabling one `<style>`, the choice is kept (`localStorage`, `esplora.stile`) and a
small script in the `<head>` applies it before the first paint; after a switch the graph is laid
out again and the overview matrix repainted. On the phone the combo shares the second row of the bar
with the search field.

«Tufte» (`stile-tufte.css`, the default): the style of Tufte CSS (https://github.com/edwardtufte/tufte-css, MIT License,
`esploratore/LICENSE-tufte-css.txt`) adapted to an application, with the markup of `modello.html` and
`app.js` unchanged: ET Book on `#fffff8` paper in `#111` ink (`#ddd` on `#151515` in the dark theme),
titles at 3.2rem in regular weight, headings and labels in italic (ET Book has no small capitals; the
headings printed in capitals are set in synthesised small capitals, as the `newthought` of Tufte CSS),
the reading text at 1.4rem/2rem, side texts (notes, panel) near 1.1rem, links in the ink with a thin
underline, hairlines (`#ccc`) instead of boxes, cards and pills, no accent colour (`--errore` marks
only what is wrong) and shadows only on what floats (preview, help, tooltips). The relation colours
of the chips, the graph and the overview are kept, since they carry data. Light and dark themes
share the tokens at the top of the file. The page does not use the article layout of Tufte CSS
(a 55% column and side notes floated into the right margin), but borrows its margin: the reading
column moves left and leaves the right margin to the margin references as printed, beside their
verse (the column narrows first when the verse panel opens; below 52rem of page the margin hides,
by a container query on `main`). Tables are set as booktabs (a heavy rule above and below, a light
one under the head, the row rules on the rows, figures right-aligned); the first line of a chapter
and of each pericope is in small capitals, as the `newthought` of Tufte CSS; long titles printed in
capitals (the periods of the chronology) in small capitals at 2.2rem.

«Giardino» (`stile-giardino.css`): the quieter style that preceded it. Literata alone for text and
interface, black ink and one red (`--rubrica`) for verse numbers, rubrics and the current view;
hairlines instead of boxes; labels in true small capitals (`--spazio`); old-style figures in the
reading text; a warm, low-glare dark theme.


| View | Route | What |
|---|---|---|
| books | `#` | the books by testament and BJ volume, totals; four cards to the front matter, the two indices and the chronology |
| book | `#Gen` | chapters, divisions and pericopes, introductions |
| reader | `#Gen.1`, `#John.3.16`, `#Ps.23.1-4`, `#Deut.7.9?e=Deut.7.12` | the chapter as printed: headings, poetry lines, verse numbers, note calls (letters, buttons), margin signs (‖ ↗ = + •), page numbers; in the Tufte style the margin references as printed in the right margin beside their verse (`margineVerso`, each reference a link with its preview; `disponiMargine` moves one down when it would touch the one above, again whenever the text changes size; hidden where the page is narrower than 52rem); a plum `◊` beside the margin signs on the verses a dictionary citation names on their own or in a passage of at most 3 verses (12,175 verses; the tooltip and the verse's label give the entries and citations); heat (the flame) by in-degree or by the citations of at most 3 verses of the dictionary: the switch «Evidenzia: Rimandi BJ | Dizionario» above the text turns it on with that source (the pressed one turns it off), `d` switches the source; `e=` the other references of a list, highlighted and linked; the Hebrew letters of the alphabetic poems (Psalms, Pr 31, Lamentations, Na 1) in the left margin beyond the margin signs, beside the line each one opens, with the Hebrew character (inline at the line start under 1240 px) |
| verse panel | (with a verse) | the notes called here and those whose label covers the verse; the margin references by relation, unresolved ones grey with the reason; incoming margin references, note and introduction citations; «Nel Dizionario di Teologia Biblica»: every entry citing the verse (all citations whose passage includes it, the most specific entry first), each citation with the section path and title, the passage when wider, the flags (`s`, `ss`, `par.`, `…`) and the sentence around it with the citation marked; a click opens the entry at that paragraph; the number of entries also in the header; previews on hover (tap on touch screens); «Nell’indice delle note» and «Temi pastorali»: the (sub-)entries whose references name the verse (a corrected misprint by its corrected passage), most precise first, each reference as a chip with the BJ note it points to; «Nella tavola cronologica»: the entries citing it (most precise first) with their date, column and period, linked to the table; the woodcut that illustrates it, if any |
| graph | `#grafo/John.3.16[?p=2&f=parallel,doublet,diz]` | a tree to explore, left to right: the verse is the root, its links hang from it grouped by relation and direction (`‖ Paralleli`, `Affini →`, `← Affini`, `§ Le sue note citano`, ..., `◊ Nel Dizionario`; `f`: the relations shown, `diz` the dictionary); an entry of the dictionary is a card on lavender paper (its name, the section, the sentence around the citation) whose `▸` grows the passages it cites (those of the same paragraph first, `◊ La voce cita`) and whose name opens the entry; the most specific first, 8 per group at the root and 4 further on (`+10 di N` shows more); every card holds the reference, the passage text and the BJ notes it calls as yellow slips (`continua` opens one whole), inside an SVG contour drawn twice by hand, each time in one stroke with rounded corners of uneven radius and sides that bow or bend in a soft S, running on a little past its start, over a sheet with rounded corners (seeded by the verse, so it is stable); `−` in a card's heading reduces it to that heading (its branches stay), `+` shows it whole; the branches are drawn by hand too (an S through a midpoint off the smooth path, the solid relations gone over twice, seeded by the path from the root); `Esplorazioni salvate` keeps the tree as it is (its open and reduced cards, how many of each group are shown, the notes opened whole, the relations, the view) by name in this browser's localStorage (`esplora.esplorazioni`), lists the saved ones (a click brings one back, × deletes it; the same name replaces it); `Esporta in PDF` opens the print dialog on the whole tree as it is (open, reduced, filtered cards, the current style and theme) on one page of its own size, with real text («Salva come PDF»; a tree over 200 inches is scaled to fit); `▸` grows a card's own links in place (a passage already on the path from the root is left out, so there are no cycles), `Apri un livello` grows every leaf (up to about 260 cards), `p=2` opens the first level at once; the reference of a card makes it the root; drag to pan, the wheel scrolls, Ctrl + wheel, a two-finger pinch on a touch screen (the point between the fingers stays under them; a link or button a pinching finger landed on is not followed) or +/− zoom, ⌂ fits the whole tree; "nessun collegamento" on the root when there is none |
| search | `#cerca?q=…&in=versetti\|note\|dizionario\|apparati&t=AT\|NT&b=Gen` | verse texts, notes and the dictionary, accents and case ignored, whole words (`ira` is not in «apparirà»; `ira*` for the start of a word), all words required (or a "phrase"), grouped by book, highlighted; the dictionary is a group of its own on top (entry names as chips, then paragraphs, more in pages of 50; left out by the testament and book filters); Back returns to the rows shown and the scroll position; «Appendici» (`in=apparati`, also in «Tutto»): a group with the index entries and themes matching (headwords and sub-entries, as chips), the chronology entries and the paragraphs of the front matter |
| overview | `#panoramica[/Gen/Matt]` | totals, margin references by relation (grouped as in the panel: they add up to the references), book by book (small multiples after Tufte, `libroPerLibro`: a row per book, three word-sized lines across its chapters, the notes by calling verse, the margin references by verse printed at, the quotations by first verse, each on its own scale with a dot at its highest chapter and the total after it; over a line the chapter and its count, a click opens it), book × book matrix (click a cell: its references below, scrolled into view), the 50 most referenced verses; the dictionary: entries, citations, % recognised, verses cited, and the 20 verses it cites most, counting every citation or only those of at most 3 verses (the two rankings of `dufour.json`); four tiles of the appendices: entries of the index of notes, references to BJ notes with the share at a note's first line, themes, chronology entries |
| introduction | `#intro/intro-pentateuco[.3]` | an introduction with its citations as links |
| dictionary | `#dizionario[?q=spirito]` | the 849 entries by letter (letter buttons, disabled when the filter leaves the letter empty; a filter, kept in the address, and the scroll position, so Back returns to them): full entries with their number of citations, the 519 redirects in italics with the number of distinct entries they send to |
| entry | `#voce/abele`, `#voce/abele/2`, `#voce/abele/1?v=Gen.4.5` | an entry as printed: name, authors, pages, the sections with their headings (`VT`, `I.`, `1.`, `a)`, «…»), the paragraphs with italics, page numbers and the signatures, `*words` linking the other entries, the citations as links to the passage with the preview of the chips (unresolved ones grey, reachable with `Tab`, their reason in the preview on hover, tap or focus); section headings as headings for screen readers; a section index beside the text (a link clicked again scrolls again); see-also list and the entries pointing here (the path `0` shown as `introd.`; a target that is itself a redirect shows where it leads); a redirect lists its entries (at the section printed) and counts the distinct ones; `/n` scrolls to paragraph n (with its headings) and highlights it, or says the entry has no such paragraph, `v=` also marks the citations naming that verse, outlined inside the highlighted paragraph; the slug is normalised (`#voce/AGNELLO-DI-DIO`, `#voce/agnello di dio`) |
| front matter | `#introduzione-generale[/presentazione[.3]]`, `#introduzione-generale/abbreviazioni` | the edition (publisher, ISBN, printings, the colophon), the texts with their author, signature and position, printed in italics where the print is (the words in roman inside them upright), their citations as links; the two divisions of the canon with the list as printed and the books or chapters of this Bible each item is (an apocryphal one says it is not here); the Avvertenze and the 73 woodcuts as chips; the abbreviations and codices grouped as printed, book sigla linked, Gregory-Aland numbers |
| index of notes, themes | `#indice-note[?q=]`, `#temi`, `#indice-note/91[.2]` | the entries by letter with a filter kept in the address (as `#dizionario`); an entry: headword as printed (small caps, italics), its sub-entries, each printed reference as a chip (preview, unresolved grey with the reason; a misprint struck through with the corrected chip «→ Gs 14,6» beside it), in the index of notes the BJ note each points to («nota 14,6», a link opening the verse with that note) and the notes themselves below, closed, to read in place; «v.» to other entries, page numbers to the introductions; `.k` highlights a sub-entry |
| time line | `#tempo[?f=nota,introduzione&c=giuda&v=1&q=ciro&a=-587&e=<event>&p=6]` | «Linea del tempo»: every event of `eventi.json` by period of the table (its title as printed as the section head, the span and the count) and, inside, in the order of the line, one group per span of years with the years in a left gutter (`587 a.C.`, `171–138 a.C.`, `4 a.C. – 39 d.C.`, `fine II sec. a.C.`, `II mill. a.C.`, as the first event of the group dated by itself prints them, not an entry placed by its row; «c.» when every event of the group is approximate; sticky while its events scroll; on top on phones); each row: the sentence (the date marked, its tooltip the rule of the era) or the entry, person, map, with the references as links and previews; then the source as a link (the entry at `#cronologia/<period>?v=`, the note opened in the reader on that note, the paragraph of the introduction, of the front matter or of the entry, the person, the map at `#carte?c=`; a dating's books in its text), the column of the table, «≈ dalla riga» for a row placed by its row (the tooltip says how), «ipotesi», «non dopo» / «non prima» for a bound (the same marks beside the years in the verse panel and on a book
page, `qualificaT`), «o N» and «= …» links to the same event. Above it one row of filters (the 8 sources as switches with their counts, the line under the title of VIII with «Tavola», the column of the table with its counts, «solo con versetti citati», words as in the search, «Vai all’anno» with a.C./d.C.); every count follows the other filters. Under them the strip, sticky: one segment per period (the same width each, the years in proportion inside it, period I on a logarithmic scale; «dopo» half as wide), bars counting the events shown, a band over the rows on screen, a hairline and a tooltip over a bar (count, years, period), click or drag to move (touch too), a slider for the keyboard (arrows a span of years, PageUp/PageDown a period, Home/End; its value says the years and the period, «nessun evento» when none is shown; Tab goes on to the first row on screen, as after «Vai»). The address: `f` the sources (`f=` none), `c` the column, `v=1`, `q`, kept as you filter (a filter is a step of the history, the words replace it; Back sets the words of the field too), `a` the year and `r` the row at the top, written as you scroll, with that row's offset in the history entry (`history.state.tm`), so Back and Forward return to that row and not to the first of its year (a year can hold dozens), and a copied address to the row of `r` (else to the first row of `a` in the period that holds the year; a year that is not a number is the top), `e` an event highlighted and focused (Back and Forward to it restore the place kept in the history entry; a copied address goes to the event itself; «nascosto dai filtri» only when it is, gone when a filter shows it), `p` a period; a jump lands a group with its rule under the head's (no sliver of the group before); a filter change keeps the first row on screen. The fonts may load after the first render: the place is sought again when they have. Links into it: the verse panel («Nel tempo»: the events anchored at the verse or citing it, in order, with their years), a book page (its datings), a period of the chronology and its highlighted entry, the index of the chronology, a person, a map, the Appendici hub, the overview (a tile), the first page; the tab «Tempo» only where the bar has room (wider than 1280 px; `largo ampio`), else the hub. All rows are rendered at once (about 200 ms for 1,547). The tooltip of a bar gives the first and last year it holds, widened to the years of the events counted there |
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


## Stage 7: the fixes of the review of 2026-10-31 (session F1)

- `riferimenti.py`: `numerazioni.tsv` (rule `numerazione`, 16 references: the Greek psalter, the
  Vulgate's Es 22, 2Mac 12, At 19, Gdt 13–14, the BJ's Sir 36, Sal 151); `MISPRINT` sigla read as the
  CEI siglum and `REFUSI_RIFERIMENTI`, `REFUSI` (rule `refuso`, 6 links: Zac ×2, 2Mc, Sal 23,31 (LXX) →
  Pr 23,31, the two chains of Gen 6,5); `gr.` as a qualifier; 14 more rows of `CORREZIONI` (Ef 3,18;
  2Mac 13,23 and 15,20 → 1Mac; the nine 1Gv references of the introduction to Giovanni). Links:
  resolved 66,594 → 66,611, unresolved 73 → 63, partial 21 → 12, numbering 867 → 869. The wrong link
  of `Sal 103,12 (LXX)` (Ps 103,12) now goes to Ps 104,12.
- `dufour.py`: the table of Sirach 34–36 is read from `numerazioni.tsv` (scheme `dizionario`, equal to
  the former dict); `pietra- *memoriale` → `pietra-memoriale` (3 paragraphs).
- `paratesto.py`: `CORREZIONI_INDICI` 16 → 20 (Os 9,15, Eb 7,4, At 7,58, 1Ts 5,27, read on PDF 3032–3039).
- `progetti/appendici/tsv.py`: comments dropped as TeX does; a word split by `\pag{n}` is one word
  (the 4 sub-themes of R1 F1).
- `rdf.py`: no trailing space in a truncated label. `verifica_rdf.py`: the content of 460,452 literals
  (line-end hyphens, LaTeX residue, spaces; «» () [] balanced in labels and titles) and the report of the
  index references with no BJ note and no correction (18).
- Queries 22 (overlap, order) and 25 (the first verse of the Bet stanza).
- `make ontologia` green (13 min): 3,718,720 triples (+95), SHACL conforms; browser test 171/171.

## Stage 8: the links between the parts and the explorer (review of 2026-10-31, session F2)

- **Stage 2d, `integrazione.py`** (after `test_paratesto.py`): reads the hand tables of this folder
  and the four JSON files, writes `build/integrazione.json`; its checks fail on a row naming an
  unknown resource, a head-word alignment with no shared verse and no reviewer's reason, a verse
  given one by one in `persone.tsv` that does not name the person, a reference of the calendar,
  measures or maps that does not resolve, a row of a correction table with no intervention (or two),
  a corrected or read link with none. `test_integrazione.py`: 6 tests on real rows.
  - `allineamenti.tsv` (466): seeded by a script from R2's reviewed table (`revisione/R2/allineamenti-candidati.tsv`,
    the `si` rows), F2's review of the 7 `rivedere` (3 accepted, each with its reason) and of Magi / MAGIA
    (rejected), the direction of the head-word matches (an index entry broader than its dictionary
    entry is `narrowMatch`), 6 hand rows (Amicizia, Ascolto, Esortazione, Imitazione, Santità, Regalità),
    the 60 theme ↔ index-of-notes pairs and the 5 pairs of R2-10.
  - `persone.tsv`: verses by name within the chapters listed (exceptions written out), index
    sub-entries and references, chronology entries. `cronologia-libri.tsv`: 46 datings.
  - `testimoni.tsv` and the codices: a list of at least two sigla (or a papyrus) within 60 characters of
    a cue (`con`, `hanno`, `leggono`, `omette`, `var.`, `mss`, `ecc.`, …); D by book (05 Gospels and
    Acts, 06 Paul), E only in Acts, a codex only in the books its abbreviation row names.
  - `calendario.tsv`, `misure.tsv`, `carte.tsv`: the tables by hand, the references read by
    `riferimenti.scan_prose`, the prose misprints of `paratesto.CORREZIONI_PROSA` read corrected.
  - The interventions: one per row of `riferimenti.CORREZIONI` (matched by note and text),
    `CORREZIONI_VERSO`, `AGGIUNTE` (by note, in text order), `REFUSI`, `REFUSI_RIFERIMENTI`, `MISPRINT`,
    `numerazioni.tsv` (the dictionary's rows target the CEI passage they map), `paratesto.CORREZIONI_INDICI`,
    `CORREZIONI_PROSA`, `tsv.RIMANDI`, `PAGINE_ESTRANEE`, `dufour.CORREZIONI`, `PARAGRAFI`, `FORME`, the notes
    of `dinastie.tsv`, and one per link read by a rule of stage 2, 2b or 2c (1,433).
- **`paratesto.py`**: a month before a reign's span is read («NABUCODÒNOSOR (sett. 605–562)»): 388 of
  585 entries dated; query 22 now lists Nabucodònosor (R2-23's remaining gap).
- **`rdf.py`**: the fourth part (`integrazione()`, VoID subset `vp:integrazione` and four linksets);
  `dcterms:identifier` on the pages, the Bible, the front matter and appendices (R2-02), the
  woodcut's page (its book's first) and the acrostic letter's page and `bj:inVersetto` (R2-11),
  `bj:categoriaMotivo` on every reference with a reason, `bj:secondoVersione` from the qualifier,
  `@it` on the labels and meanings of the abbreviations, the acrostic labels and the colophon (R2-07),
  «Headword: label» sub-entry labels (R2-08), the VoID description of the whole dataset and `dc:` among
  its vocabularies (R2-01). Literals: `xsd:decimal` and the language tags `he-Latn`, `grc-Latn`, `la`.
- **Vocabulary** (`bj-ontologia.ttl`, version 1.3): 94 terms (230 → 324): 63 classes and properties, the concept schemes `bj:regole` (21
  rules) and `bj:motivi` (7 kinds) and the motivation `bj:interpretando`; **shapes** (`bj-forme.ttl`): 11 more (identifiers, alignments,
  datings, versions, witnesses, months, feasts, units, maps, interventions, persons named);
  **checks** (`verifica_rdf.py`): 22 SPARQL queries on the integration (counts against the JSON,
  shortcuts backed and closed, every reading or correction literal with its intervention, every typed
  resource with an identifier); **queries** 27–32; **README** numbers by `statistiche.py`.
- **Explorer** (R3): the reference box reads `1Cor 13,4` (E1), `Gv 3 16`, `Giov`, `Ecclesiaste`,
  `Eccli`, «Lettera di Geremia» (Bar 6) and says «Gn» is Giona (E7); counts in the singular (E3);
  not-found pages with their title and a message per view (E4); the *Appendici* tab and hub, the
  appendices above the books on the first page, the Panoramica tab only in the hub on the phone (E5);
  the search finds the other spellings (`sinonimi.tsv`) and says so (E2), in «Tutto» the verses come
  with the dictionary and appendix groups as closed boxes, the paragraphs of a matching entry first
  then by hits (E6); the filters wrap on the phone (E8); the graph's controls are a closed sheet on the
  phone and the first view fits the root and its first level (E9); Back to a chapter keeps its scroll
  (E11); titles name the verse and the period (E12); «Introduzione generale» and «riferimenti»
  everywhere (E13); no «0» on the index cards (E14); a note named once in the index summary (E15);
  E19: «Anche in» on the index entries, themes and dictionary entries, person pages (`#persona/<id>`)
  linked from the dynasties and the verse panel, books and persons at the end of the chronology entries,
  «Nella tavola cronologica» on a book page, «citato in N note» for versions and codices,
  `#calendario`, `#misure`, `#carte`, the editor's intervention in the preview of a corrected link.
  `prova_esploratore.mjs`: 50 more checks (221).

## Stage 9: quotations, direct speech and quoted words (session F4, 2026-11-01)

The user asked for direct speech and quoted sentences in italic (done in the Tufte edition by F3), «then
adjust the interfaces and the ontology in turn».

- **One detector, `virgolette.py`** (stage 2e, after `test_paratesto.py`). The language rules that F3
  wrote in `tools/tufte/discorsi.py` moved here, the way `contesto.py` became an adapter over
  `riferimenti.py`: a scope is matched on its own (a book's verses in order, the headings apart; a note;
  an introduction; a front-matter text; a canon item, the edition, an abbreviation, a chronology entry,
  an index entry or sub-entry); `«` opens and `»` closes the last one open (`accoppia`, stack
  matching), only the outermost pairs set the italic and a pair inside another is nested (its parent the
  innermost pair around it); a `«` left open and a `»` with none open are unbalanced, kept as printed,
  and the pairs after them are matched as if they were not there; guillemets already in italic (`\emph`,
  `\detto` in the LaTeX, `<em>` in the HTML) are skipped; a run only in italic already is not set again
  (`solo_corsivo`). `discorsi.py` keeps only the walk of the LaTeX and the wrapping: regenerating
  `progetti/bibbia-tufte/libri/` gave the 136 files byte-identical (md5), and `test_genera.py`
  `test_lettori` compares the two readers book by book: the same 5,948 outermost, 7 nested and 2
  unbalanced quotations, and the same 341,138 words in italic, word for word (the HTML runs are cut
  where a note or a margin reference is called, `tagli`, but never inside an `<em>`, as the runs of the
  LaTeX are; the page checks that the runs and the note calls stay well nested, `bilanciato`).
  In the HTML of stage 1 a `\detto` of the notes and introductions is `«…»`: a quotation like the typed
  ones (the volumes print both in italic in guillemets). Writes `build/discorsi.json`: per quotation its
  id (`<segment where it starts>.<n>`), part, source, the ends (segment, HTML and plain offsets of the
  `«` and after the `»`), parent, the segments spanned, its words or the reason it is unbalanced.
  Checks: every end at its guillemet in the HTML and in the plain text of the graph, parents earlier
  balanced quotations of the same scope, the unbalanced ones of the text exactly Sir 16,22 and Am 7,17.
- **Counts**: text of the books 5,957 (5,948 outermost, 7 nested in Dt 20–22 inside Moses' discourse
  Dt 5,1–26,19, 2 unbalanced), notes 10,279 (4 nested), introductions 529, front matter 59 (as the Tufte
  edition), appendices 25 (the chronology 13, the index of notes 12: its headwords and sub-entries; the
  Tufte edition has 41 there, since the calendar, the measures and the comments between the references
  of the index are text of the volume but not of the graph). 16,849 in all; the text spans 16,478
  verses (Dt 5,1–26,19: 532 verses, 77,654 characters).
- **The two unbalanced ones**, checked on the page images (`revisione/F4/crops/`), are printed so, not
  transcription errors: Sir 16,22 (p. 1584) opens `«Chi annuncerà…` and closes `…alla fine».` inside the
  third stich, printed in italics (an addition of Gr. II and lat., note 16,22c), so the closing
  guillemet is skipped; Am 7,14 (p. 2201) closes Amos' answer `…sicomòro».`, and 7,17 (p. 2202) closes
  again `…dalla sua terra”».` (the CEI 2008 runs the answer to 7,17: a misprint of the volume, kept).
  The reasons say so (`« closed only by a » inside italic text (Sir.16.22)`, `» with no « open: the
  quotation before it closed in Amos.7.14`).
- **RDF** (`rdf.py`): each quotation a `bj:Discorso` (a `oa:SpecificResource` of the resource it is read
  in, `oa:hasSource`: the book, the note, the introduction, the text, the entry) at
  `id/discorso/<verse id>.<n>` (else `id/discorso/<kind>/<local>.<n>`), with `bj:parte`, `bj:iniziaIn` /
  `bj:inizioCarattere` (the `«`) and `bj:finisceIn` / `bj:fineCarattere` (after the `»`) in the plain text of
  the verse, the note's body, the paragraph or the entry, `bj:dentroDi` the quotation around it,
  `bj:attraversa` every verse it spans, `bj:lunghezza` (characters of its words), `bj:sbilanciato` and
  `bj:motivo`. The words as `bj:testo` only up to 200 characters (`TESTO_DISCORSO`): 15,087 of 16,847;
  all of them would add 2.1 MB of literals, the text of the books 1.9 MB of it (43% of the verse text
  again, Moses' discourse alone 78 KB), recovered from the verses with the offsets; the short ones
  (a saying, a word, the first answer of a dialogue) are what a query looks for by text. No speaker is
  inferred. 200,064 triples (3,776,873 → 3,976,937, +5.3%), counted in the subset of the resource
  (16,765 in `vp:bibbia`, 84 in `vp:paratesto`).
- **Vocabulary** `bj:Discorso` and 8 properties (`bj:parte`, `bj:iniziaIn`, `bj:finisceIn`,
  `bj:inizioCarattere`, `bj:fineCarattere`, `bj:dentroDi`, `bj:attraversa`, `bj:sbilanciato`), `bj:lunghezza`
  and `bj:motivo` open to it, `bj:testo` says when; **shape** `bjf:Discorso` (55 node shapes); **checks**
  16 SPARQL queries (counts by part equal to the detector's, nested and unbalanced ones, both ends when
  balanced and one when not, the ends of the text verses in order, the verses spanned between the ends
  and their number, the offsets inside the text at a `«` and just after a `»`, the end after the start,
  nesting acyclic in one resource and inside a longer balanced quotation, the words when short);
  **queries** 33 (the quotations touching Gen 3) and 34 (the 25 longest).
- **Explorer**: the words of a quotation in italic, the guillemets, verse numbers and note calls upright,
  an `<em>` inside upright (`.ds`), in the reader (prose, poetry line by line, across verses), the
  verse panel, the notes (with their `\detto`), the introductions, the front-matter texts, the edition,
  the canon, the abbreviations, the chronology, the index headwords and the graph cards (verses and
  note slips, also when cut short: `htmlTagliato` cuts the HTML at a word and closes its tags). The verse runs are in the payload
  (`V.q`, HTML offsets, merged with the note calls at render); the other texts are wrapped at build time
  (`virgolette.corsivo`, after the citations). A «Discorsi N» switch above the chapter (key `q`)
  highlights them; the panel lists the quotations through the verse (where they run, their first words,
  verses and characters, «dentro il discorso di …», the reason of an unbalanced one); the search has a
  «Discorsi» filter (only the words between guillemets of the verses). Checks of `esploratore.py`: the
  detector run again on the packed HTML finds as many quotations per part as `discorsi.json`, every
  outermost one has italic unless its words are italic already. `prova_esploratore.mjs`: 19 more checks (240)
  (Gen 1,3, Dt 5,2–4 across verses, Dt 20,3 nested, Sir 16,22 and Am 7,17, Sal 2,3, a note call inside a
  quotation, notes, introductions, the Presentazione, an index headword, the colophon, the switch and
  its key, the search, the phone). The page grows 8.84 → 9.09 MB; first render about 600 ms as before.


## Stage 10: the time line in the graph (2026-11-02)

The user asked for a time line of every event in the explorer; stage 2f (`eventi.py`) built it as
`build/eventi.json`, and this stage brings it into the graph, extending the model the chronological table
already had (integer years `bj:annoInizio` / `bj:annoFine`, `bj:circa`, `bj:datazione`; no OWL-Time, no
`xsd:gYear`: see `ontologia/README.md`, *The front matter and the appendices*) instead of a parallel one.

- **RDF** (`rdf.py`, `eventi()` after `discorsi()`, `FONTI_TESTO`, `FONTI_RISORSE`, `risorsa_evento`):
  every event of `eventi.json` on one resource. The chronology entries, the dated persons of the dynasties,
  the datings of the books and the maps with a period are already resources: they take on themselves
  `bj:posizioneLinea` (the place on the line, 1–1,555), the years (`G.link`, so the 388 years of stage 2c
  are not added twice: `checks_eventi` asks for exactly one value, the JSON's), `bj:circa`,
  `bj:precisione`, `bj:regolaEra` (`era_da`), `bj:datataDa` (`data_da`, entries and datings),
  `bj:limite`, `bj:incerto`, `bj:annoAlternativo`, `bj:nelPeriodo` (the section of the period) and
  `bj:stessoEvento`; an entry dated by its text gets that date as `bj:datazione`, a person
  `bj:tipoDatazione` `morte` or `regno`. A date read in free text is a new `bj:EventoDatato` at
  `evento:<source with / for :>/<offset>` (`evento:nota/2Kgs.25.8/66`, `evento:paragrafo/storici.16/2202`,
  `evento:paragrafo/prefazione-verdon.2/517`, `evento:voce/gerusalemme/paragrafo/2/95`) with
  `dcterms:identifier` (the id of `eventi.json` without `ev:`), `rdfs:label` (`etichetta`), `bj:parte`
  (`nota`, `introduzione`, `preliminari`, `dizionario`), `oa:hasSource` (the note, the paragraph of the
  introduction or front-matter text, the paragraph of the entry), `bj:datazione` (`data`),
  `bj:posizioneTesto` (`offset`), `bj:testo` (`frase`) and `bj:testoHtml` (`html`, when it differs),
  `bj:versettoAncora` (a note's anchor), `bj:citazioneNellaFrase` (the `bj:Citazione` of each reference:
  `citazione()` for the BJ, `citazione_voce()` for the dictionary) and `bj:citaVersetto` (the verse runs).
  It counts in the VoID subset of its source (`vp:bibbia` for notes and introductions, `vp:paratesto` for
  the front matter, `vp:dizionario`); the triples added to the entries and persons count in
  `vp:paratesto`, to the datings and maps in `vp:integrazione`. `bj:annoAlternativo` is `alternativa`,
  signed like the years («del 587 (o 586?) a.C.»: -586), and `bj:stessoEvento` is stored both ways
  (symmetric), as `eventi.json` lists it (both were mended here until the review of stage 12 fixed them in
  `eventi.py`). `checks_eventi()`: one resource per event, its years and
  position the JSON's, a free-text date at its offset in the text of its source as the graph holds it, the
  sentence in that text, the verses equal to the targets of the sentence's resolved and partial citations,
  `bj:EventoDatato` count, `bj:stessoEvento` both ways. The VoID description names the time line.
- **Vocabulary** (`bj-ontologia.ttl`, version 1.4): the class `bj:EventoDatato` (`schema:Event`,
  `oa:SpecificResource`) and 11 properties (`bj:posizioneLinea`, `bj:precisione`, `bj:regolaEra`,
  `bj:datataDa`, `bj:limite`, `bj:incerto`, `bj:annoAlternativo`, `bj:nelPeriodo`, `bj:stessoEvento`
  (symmetric), `bj:versettoAncora`, `bj:citazioneNellaFrase`); `bj:annoInizio`, `bj:annoFine`, `bj:circa`
  open to the five classes of the line, `bj:datazione` and `bj:citaVersetto` to `bj:EventoDatato`,
  `bj:tipoDatazione` to `bj:PersonaStorica`, `bj:parte` to `bj:EventoDatato`, the comments say so.
- **Shapes** (`bj-forme.ttl`): `bjf:LineaDelTempo` (every subject of `bj:posizioneLinea`: one of the five
  classes, one position, start and end with start ≤ end, `bj:circa`, a precision of the list, an era rule,
  `bj:datataDa`, `bj:limite`, `bj:incerto` from their lists, a period a section, `bj:stessoEvento` to the
  line) and `bjf:EventoDatato` (label, part, a source of its kind, the expression, the offset, the
  sentence, citations and verses, the anchor exactly for the notes); `bjf:EventoCronologia` now asks
  every entry for its place and `bj:datataDa`, and a `bj:datazione` exactly when dated by the table or its
  text (the old rule, years only with a printed date, is gone); `bjf:PersonaStorica` takes
  `bj:tipoDatazione`. 57 node shapes.
- **Checks** (`verifica_rdf.py`, `integrita_eventi()`): 31 SPARQL queries (147 in all, 115 before): one position per event and
  1–N distinct, the counts by source against `eventi.json`, a start and an end with start ≤ end, the sums
  of the start and end years equal the JSON's, in order (each next position starts no earlier), precision
  and era rule everywhere, the periods (their count, an entry's its section), `bj:stessoEvento` symmetric,
  as many as the JSON's links both ways, between equal years; for the dates of free text the source of its
  part, the date at its offset in the source's text, the sentence holding the date and in that text, a
  note's date anchored at the verse calling the note, anchors only there, the (date, verse) pairs of the
  JSON, every anchor and cited verse a declared verse, every cited verse backed by a citation of the
  sentence, those citations citations of the source, their number. Changed: «entries with a year range»
  is now all 585, a new query counts the 388 dated by stage 2c (`bj:datataDa` «tavola» with
  `bj:datazione`), the `bj:citaVersetto` count of the notes, introductions, texts and entries leaves the
  dates out.
- **Queries**: `35-eventi-di-un-secolo.rq` (the 6th century B.C. on the line: every object starting in it,
  of every kind, with the date as printed, years, precision, where it is read and the verses cited) and
  `36-date-nelle-note-dei-re.rq` (the dates of the notes on 1–2 Kings in order, with the anchor verse, the
  era rule and the chronology entry that is the same event).
- **Numbers**: 916 `bj:EventoDatato` (notes 557, introductions 268, front matter 25, dictionary 66) and
  639 resources already there on the line (585 entries, 6 persons, 40 datings, 8 maps); 26,225 triples
  (3,976,937 → 4,003,162; `vp:bibbia` +19,484, `vp:dizionario` +2,156, `vp:paratesto` +4,207,
  `vp:integrazione` +378: the 80 triples of the 40 same-event links between a dating and its entry count in
  `vp:paratesto` since `eventi.json` lists them on the entry too, stage 12); 345 `bj:` terms (333 before). `make ontologia`: green (147 of 147 SPARQL
  queries, SHACL with 57 node shapes on 267,149 typed resources conforms, parsers and JSON-LD equal, the 36
  queries return rows: 35 has 215, 36 has 33, 22 now 35 instead of 34 since «Labashimarduk (556)», dated by its text, has a
  `bj:datazione`); `prova_esploratore.mjs` 247/247 (the explorer does not read the graph).

## Stage 11: the time line in the explorer (2026-11-02)

The user asked for «a timeline with *all* the events ordered chronologically, to the web interface, so that I can
explore content also from there». `esploratore.py` reads `build/eventi.json` (stage 2f) into the key `tempo` and
`app.js` shows it at `#tempo` (stage 4: the payload paragraph and the row «time line» of the table).

- **Form.** The list is the table view of the line: every event can be read, filtered and opened from it. The
  strip above it is a histogram, one series in the muted ink (no legend: the caption names it), thin bars with a
  2 px gap, hairline separators and baseline, a hover tooltip per bar with the count first, the hit target the
  whole column of a bar; the part on screen is a band (the ink in Tufte, the red in Giardino). The span from
  2,000,000 B.C. to 2008 A.D. has no honest linear scale: each period of the table gets the same width, the years
  are in proportion inside it, period I (2,000,000–3001 B.C.) is logarithmic, the 80 events after 135 A.D. a
  half-width segment; the caption under the strip says so. An event placed by its period (`periodo`) sits in its
  segment even when its first year falls in another one: 14 entries of the table, in the section that prints
  them (12, 20–21, 51, 54, 113, 199–201, 241–245: cronologia.12 at 3100 B.C. in II, 54 at 945 B.C. in V, 113 at
  721 B.C. in V, 199 at 525 B.C. in VI, 241–245 at 333–323 B.C. in VII, …; corrected by the review of the
  feature, which counted them); inside a period the order is the line's.
- **Order.** By period (the section of the table for an entry, else the period of the first year; after 135 A.D.
  last), then the order of `eventi.json`: inside each period the years never go back. Groups of rows share a
  span of years (720 groups).
- **Styles.** Both stylesheets, light and dark: Tufte (ET Book, the years in its old-style figures, a heavy rule
  over each period as booktabs, hairlines between the years, the date of a sentence on a paper tint, no accent);
  Giardino (Literata with old-style figures, the years, the dates and the titles of the periods in the red of the
  rubrics, the labels in small capitals). On a phone the years go above their rows, the filters wrap, the strip
  keeps its width and a short caption, the tab is hidden (the hub and the Appendici tab lead there).
- **Also changed.** `#carte?c=<map>` highlights a map; the tooltip of the overview's small multiples is hidden
  on a route change (it stayed on screen after a click).
- **Checks.** `esploratore.py`: the events and their sentences (above). `prova_esploratore.mjs`: 18 more (265):
  all 1,555 rows in the expected order with years never going back inside a period; the counts per source
  against `eventi.json`; the first render under 300 ms (about 180–210 ms); every reference a link with its
  target; the gutter of an entry, a person, a map, a note; the preview of a reference; the source filter in the
  address and Back; words and «solo con versetti citati» with the counts of the buttons; the strip (tooltip, a
  click on VI, a drag to IX, the band, the year in the address); the slider keys; «Vai all’anno» 30 d.C.; the
  panel of 2Re 25,8 («Nel tempo», as many as `eventi.json` has) and its link landing on the note's date,
  highlighted, in view and focused; the note opened from the row and Back to the row; the links from Sir, the
  period VI, the hub and the overview; both styles in light and dark; on the phone no horizontal scrolling, the
  filters inside the screen, the tabs on one line, a short sticky head, the event in view, a tap on the strip.
  Screenshots `T1`–`T11` with `--foto`.

## Stage 12: review of the time line (2026-11-02)

An end-to-end adversarial review of stages 2f, 10 and 11: 40 random events of every source read in their
source (all right), 10 more entries of the table on the scanned pages (pp. 4, 16, 18, 20: all right; with
them every entry of p. 4 and the rows of pp. 16, 20–21 around the found defect), the order at the origins,
the turn of the era, the centuries and 135 A.D., the graph (`verifica_rdf.py`, the example queries, and a
scan of `bj-dati.nt.gz` for orphan or duplicated resources of the line: none), the explorer used as a reader
(the tab, the hub, the verse panel, a chronology entry, a book, a map, a person, the filters, the strip,
Back and Forward, the previews, the keys, both styles, dark, 390 px), and these READMEs against the code.

- **Entries placed by their row sorted out of the order the table prints them.** An undated entry took the
  whole span of its row, so «Presa delle terze e delle seconde mura», «Inizio di agosto: cessano i sacrifici»
  and «Davanti al tempio, si sacrifica alle insegne romane» (row 153 of IX, 69–79) came before «Pasqua 70»
  on the line, and «Fine marzo – inizio aprile: morte di Erode» (6–4 B.C.) before «4: in marzo». Fixed in
  `eventi.py` (`riga: tra le voci della colonna`, stage 2f): 36 entries and 2 datings narrowed (`test_reali`
  checks 402, 404, 539, 33 and the order of 537–542). A row across the eras (-4…39) said `a.C.`; now
  `a.C.–d.C.` (2 entries).
- **Three headings of a column on the line as events.** «ISRAELE», «GIUDA» (row 23 of V) and «EGITTO» (row 40
  of VI) are the italic headings of the columns that open there, transcribed as entries by stage 2c; they
  sat on the line as rows «≈ dalla riga» at the span of their row. They stay entries (the 585 are all on
  the line), placed at the first year of the dated entry they head (`colonna: intestazione`) and marked
  «intestazione» in the explorer.
- **`eventi.json` half-done.** `alternativa` was unsigned and a dating's same-event link one way, mended
  downstream twice (`rdf.py`, `esploratore.py`): both now in `eventi.py` (the graph is unchanged: the same
  `bj:annoAlternativo` values, the same 206 `bj:stessoEvento` triples, 80 of them now counted in
  `vp:paratesto`). A map's `apri` was `#carte`, now `#carte?c=<map>`; «Composizione: Abdia (Abdia)» lost its
  repeated parenthesis.
- **Back to a highlighted event showed «L’evento è nascosto dai filtri»** and left the row off screen
  (`posiziona_` printed the notice whenever `e` and `a` were both in the address). **Back returned to the
  first row of the year**, not to the row the reader had left (a year holds up to some dozens of rows), and
  `memoTempo` did not record a scroll inside one year at all. Now the row and its offset are kept in the
  history entry (`history.state.tm`, `ripristinaTempo`).
- **A jump to a year left a 7 px gap** under the sticky head where the sticky year of the group before
  peeked out (a red or black sliver over the rule); a group now lands with its rule under the head's.
- **The gutter of a group** took the years of its first row even when that row was an entry placed by its
  row («1800–1601 a.C.» for «Sec. XVIII e XVII»): now the first row dated by itself prints them.
- **On a 390 px phone in Giardino «dopo»**, the label of the last segment of the strip, was cut to «do»; it
  now keeps the right edge, grows to the left, and Giardino sets those labels without letter spacing on a
  phone so it clears the «IX». The page said «a sinistra gli anni», wrong on a phone: «ogni gruppo porta i
  suoi anni».
- **Docs.** Stage 11 claimed 10 events set in a period their year is not in, «the -539 of a note in VI» among
  them (539 B.C. is in VI): it is 14 entries of the table, in the section that prints them (16 here before the
  review of the feature). Stage 10 and
  `ontologia/README.md` still described the mended fields and the VoID subsets before the fix.
- **Left as they are.** At 721–1100 px the top bar is too narrow (the search field shrinks to a letter at
  1024 px): older than the time line, as stage 11 says. Literata italic sets narrow word spaces («≈ dalla
  riga»), as everywhere in Giardino. «44–66: Cuspio Fado procuratore» is a misprint of the book (44–46), kept as
  printed. The entries of a column narrowed by their neighbours rest on the table reading in order inside a
  cell; where it does not (the start after the end), the row's span stays.
- **Checks.** `test_eventi.py` 11 tests (129 string cases, 48 real dates) with the new placements, the order
  of the siege of 70, the era of a row across the eras, links both ways, `alternativa` signed, a map's link;
  `prova_esploratore.mjs` 267 (2 new: a jump to 70 A.D. with no sliver and the siege in order; Back to a
  highlighted event in view with no notice and Back to the same row inside a year of many rows; the phone
  check of the strip now also asks for an unclipped «dopo» clear of «IX» in both styles).

## Stage 13: the fixes of the review of the feature (2026-11-03)

A second adversarial review of stages 2f and 10–12 (the data against the 21 scanned pages of the table and
every source, the graph by mutation, the explorer used as a reader and by mutation of `app.js`) confirmed 37
findings; 36 are fixed here, each with a check that fails on the code before (the new `test_eventi.py` cases
against the old `eventi.py` and `eventi.json`; the new `prova_esploratore.mjs` checks against a page built
from the old `app.js` and stylesheets: 12 of 12 fail there; the new graph checks against mutated graphs).

- **Data** (`eventi.py`, stage 2f, where the rules are described): the column rule of the entries placed by
  their row (15 entries had sorted before the entry printed above them; 6 left, where the print is out of
  date order), the headings at the first entry under them, the same-event links (one wrong, one from a
  bound, +14 by the note's verse), ranges with months and «nel N o nel M» as one event, the datings by their
  own words, the èra cristiana, bounds and approximations said before the date, the part of a decade,
  `riferimenti AT/NT` for the era rule of the Dizionario, «782 di Roma», the lemma's dash out of the
  sentence. 1,555 → 1,546 events; the ids of the 12 joined ranges moved to the start of the span (listed in
  stage 2f). `test_eventi.py`: 12 tests (156 string cases, 59 real dates; `test_periodi` asks for the
  periods by their numbers and cuts HTML on strings, so a mutation of `periodo_di`, `bilanciato` or
  `taglia_html` now fails).
- **Graph** (`rdf.py`, stage 10): `checks_eventi` compares every field of every event with the graph (the
  precision, circa, era rule, placement, bound, uncertain, the other year, the period, the date as printed,
  the label and sentence of a dated text, the exact set of same-event links): 12 mutations of the graph
  (another period, circa flipped, precision, rule, label, a cut sentence, a stage-2c date, a bound or
  `bj:incerto` removed, the sign of the other year, the placement of an entry, a same-event link moved to an
  entry of the same years) are each reported, none was before. A `bj:stessoEvento` triple counts in the VoID
  subset of its subject (all 206 were in `vp:paratesto`). A dating dated by its own words carries them as
  `bj:datazione` (3); it is the same event as its entry only with the entry's years (36 of 40; the check «the
  same event, the same years» stopped the build otherwise). `bj-forme.ttl`: the part of a `bj:EventoDatato` fixes the class of its source (a note,
  a paragraph, a paragraph of an entry: a dictionary event with a note as source conformed before); a person
  with a date is on the line with `bj:tipoDatazione`, one without is not; a dating of a book (not `citato`)
  is on the line (6 negative mutations on the subgraph of the line fire, the subgraph conforms).
  `bj-ontologia.ttl`: `bj:regolaEra` lists its keys and their qualifiers, compared with `STRSTARTS` (53
  strings, not a closed list); `bj:stessoEvento` names the capitals, the note's verse and no bounds;
  `bj:datataDa` and `bj:datazione` the datings by their words. `31-libri-nella-cronologia.rq` shows how
  the years of an entry were found (`?datata`: «riga: …» beside a year that is not printed, 27 rows).
  `verifica_rdf.py`: the names of the count checks say they count.
- **Explorer** (`app.js`, `esploratore.py`, stage 11): a copied address with `e=` opens on the event (the
  row was off screen for 312 of 1,555 events), `r=` keeps the row at the top for a copied address and a year
  alone is sought in its period; `f=` is no source; Back sets the words of the field; Tab from the strip goes
  to the rows on screen (it went back to period I), as does «Vai»; the tooltip of a bar says its own years
  (84 of 153 were off by one at an end), widened to the events counted there; «≈ dalla riga», «non dopo»,
  «non prima», «ipotesi» also in «Nel tempo» and on a book page (Gen 1,1 said «2.000.000 a.C.» bare); no
  highlight left by an event no longer in the address, focus on it after Back; `a=abc` is the top; the
  labels «IX» and «dopo» clear at 320–360 px in Giardino; the slider says «nessun evento», one tab active
  after a resize; the part of a millennium as read («inizio II mill.», was «II mill.»); the era of an
  ascending span «intervallo crescente: d.C.»; the timer of the words cleared on a route change (a
  `TypeError`, and Back rewritten); `#carte?c=x[` no longer stops the page; the notice of a hidden event goes
  when a filter shows it. `esploratore.py` fails on any date not marked (it allowed 10%); dead code out
  (`tm-riga`, the ids and `data-j` of the groups, `chiaveTempo`, the payload's `segnate`; `NOTA_KIND = [`).
- **Checks.** `prova_esploratore.mjs` 279 (12 new: the part of a millennium, the era of both orders and of
  the cited passages, «non dopo» and «non prima»; the column filter against `eventi.json`; «Vai all’anno»
  587 in both eras and the focus; words with «&» and Back with words; the last source off; the timer, `a=abc`
  and the notice; no stale highlight, PageUp, Tab from the strip; every bar's years; «≈ dalla riga» in the
  panel and on a book page; the tabs after a resize; copied addresses in fresh pages and `#carte?c=x[`; 320
  px in both styles). The final check of the fixes reverted each one alone in a copy: each made a check
  fail (the two guards of the words' timer only together, as each covers the other) except the focus put
  back on the row by Back to a highlighted event, which has its own check now (280).
- **Numbers.** 1,546 events (907 `bj:EventoDatato`: notes 546, introductions 267, front matter 26, Dizionario
  68), 75 same-event links (222 `bj:stessoEvento` triples: `vp:bibbia` 70, `vp:dizionario` 1, `vp:paratesto`
  115, `vp:integrazione` 36); 4,002,986 triples (4,003,162 before). `make ontologia`: green (147 of 147 SPARQL
  queries; SHACL with 57 node shapes on 267,140 typed resources conforms; query 35 has 210 rows, 215 before,
  query 31 still 74); `prova_esploratore.mjs` 280/280.
- **Not fixed.** The line «I diadochi si contendono l’impero di Alessandro (319–287)», printed across the
  table under the title of period VIII, is in no data: stage 2c reads only the cells of the table, and the
  line is neither an entry nor a text of the four parts of the graph, so placing it needs a decision (a new
  kind of source in `eventi.json` and in the graph, or a 586th entry, which would move the numbers of the
  table). The doubtful link «Nel 58 viene arrestato a Gerusalemme (At 21,27–23,22)» ↔ «58 ca.: Felice …
  (cf. At 21,38)» stays: it rests on a verse in common inside a long range, as do sound links (the schism of
  931 in 1Re 12, Giacomo in At 12), and a rule that drops it drops those.

## Stage 14: the line under the title of period VIII (2026-11-03)

The table prints one line across all its columns, under the title of period VIII: «I diadochi si
contendono l’impero di Alessandro (319–287).» (`\testolargo` in `cronologia.tex`). It is not a cell, so
stage 2c read no entry from it and it was in no data. Now:

- `paratesto.py` reads every `\testolargo` into the section it follows (`sections[n].text`, `html`); a line
  in no section or one with a reference is an error (references there would need links of their own).
  `test_paratesto.py` pins the one line.
- `eventi.py` reads it as free text of a new source, `sezione` (`cronologia.sezione.8`, opening
  `#cronologia/8`), with the era of the table (B.C. up to the turn of IX), first among the table's events
  of the same years: `ev:cronologia.sezione.8@49`, 319–287 B.C., `intervallo`, era by `ordine`, period VIII.
  The 585 entries keep their numbers. 1,547 events.
- `rdf.py` gives the section `cronologia:sezione/8` its `bj:testo` and `bj:testoHtml` (the source text the
  offset counts in) and the date a `bj:EventoDatato` with `oa:hasSource` the section and `bj:parte "tavola"`
  (908 `bj:EventoDatato`). SHACL: `bjf:SezioneCronologia` allows one text; `bjf:EventoDatato` takes
  `"tavola"` with a `bj:SezioneCronologia` as source (a fifth branch of its `sh:xone`). `verifica_rdf.py`
  counts the part `tavola` and checks its source class.
- The explorer: the event is a row of the time line («Tavola cronologica, VIII, sotto il titolo»); the
  source has no button of its own, it is filtered with «Tavola» (`GRUPPO_T`, the buttons are `T.filtri`);
  the page of period VIII prints the line under the title with a link to its row. `prova_esploratore.mjs`
  283: the line on `#cronologia/8` and its link, the row in VIII with its years and source, the «Tavola»
  filter keeping it, the counts of the buttons.
- **Numbers.** 1,547 events (908 `bj:EventoDatato`); 4,003,002 triples (4,002,986 before: 16 for the date
  and the text of its section, all in the front matter and appendices, 166,860). `make ontologia`: green
  (148 of 148 SPARQL queries; SHACL with 57 node shapes on 267,141 typed resources conforms; 18 m 31 s).
