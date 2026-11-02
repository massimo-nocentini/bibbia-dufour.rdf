# La Bibbia di Gerusalemme as a semantic-web base

A verse-centred RDF graph of «La Bibbia di Gerusalemme» (EDB: CEI 2008 Italian text with
the notes and marginal cross-references of the Bible de Jérusalem), built from the 14
proofread LaTeX volumes in `progetti/`. Every verse is linked to the notes called from
it, the notes commenting on it, the references printed in its margin, and every citation
of it in a note or an introduction. The entries of X. Léon-Dufour's *Dizionario di
Teologia Biblica* (1976) are in the same graph: every verse is also linked to the entries
(and their sections and paragraphs) that cite it. So is what the volume prints before the
Old Testament and after the Apocalypse: the edition, the presentation and prefaces, the
two lists of the canon, the abbreviations and codices, the woodcuts, the index of the most
important notes (each reference linked to the BJ note it points to), the index of
pastoral themes, the chronological table and the Hasmonean and Herodian dynasties, the calendar,
the measures and coins and the maps; and the acrostic letters of the alphabetic poems, beside the
line each one opens. The parts are linked to each other, not only through the verse: the indices
and the dictionary by reviewed SKOS mappings, the dynasty persons to the verses, index entries and
chronology rows that name them, the chronology to the books it dates, the notes to the versions and
codices they cite; and every correction or reading of the editor, from every table of the project,
is one annotation (`bj:Intervento`) with its rule, source row and evidence.

Both texts are copyrighted (EDB, Marietti): everything here is for local use only (see
*Licence* below for the dictionary). The IRIs live under
`https://massimo-nocentini.github.io/bibbia-gerusalemme/`, but nothing is published
there; they are names, not links to follow.

| File | What | Made by |
|---|---|---|
| `bj-ontologia.ttl` | OWL 2 vocabulary, prefix `bj:` (the dictionary, then the front matter and appendices, in its last sections) | hand-written |
| `bj-forme.ttl` | SHACL shapes for the data | hand-written |
| `query/*.rq` | 34 SPARQL examples (13–18 on the dictionary, 19–26 on the front matter, appendices and acrostics, 27–32 on the links between the parts, the corrections, the measures, 33–34 on the quotations) | hand-written |
| `bj-dati.ttl.gz` | the data graph, Turtle: the Bible, the dictionary, the front matter and appendices | `tools/ontologia/rdf.py` |
| `bj-dati.nt.gz` | the same triples, N-Triples (for bulk loaders) | `tools/ontologia/rdf.py` |
| `bj-contesto.jsonld` | JSON-LD context: `bj:` terms by local name, data prefixes (pages are `pag:`) | `tools/ontologia/rdf.py` |
| `bj-void.ttl` | VoID description of the data: title, rights, source, dumps, vocabularies, triples per class and per property, a subset each for the Bible, the dictionary, the front matter and appendices and the links between the parts, eight linksets | `tools/ontologia/rdf.py` |
| `build/bibbia.json`, `build/collegamenti.json` | intermediate JSON (stages 1 and 2) | `estrai.py`, `riferimenti.py` |
| `build/dufour.json` | the entries of the *Dizionario di Teologia Biblica* (Léon-Dufour, 1976; read from `../dufour/corpus`) and their 30,257 Bible citations resolved to verses | `dufour.py` |
| `build/paratesto.json` | the front matter and the appendices (`progetti/introduzione-generale`, `progetti/appendici`), their references resolved; `build/cronologia.tsv`, `indice-note.tsv`, `indice-temi.tsv` made again by `progetti/appendici/tsv.py` | `paratesto.py` |
| `build/discorsi.json` | the quotations between « and » (direct speech, quoted words) of the text, notes, introductions, front matter and appendices | `virgolette.py` |
| `build/integrazione.json` | the links between the parts, the calendar, measures and maps, every correction as an intervention, from the hand tables of `tools/ontologia/` (`allineamenti.tsv`, `persone.tsv`, `cronologia-libri.tsv`, `testimoni.tsv`, `calendario.tsv`, `misure.tsv`, `carte.tsv`) | `integrazione.py` |
| `build/query.md` | rows and timings of the example queries at the last build (copied into the table below by `statistiche.py`) | `interroga.py` |
| `esplora.html` | the offline explorer: one page, data embedded (the Bible and the dictionary), opens from disk | `tools/ontologia/esploratore.py` |

`build/` (about 92 MB) is listed in `.gitignore`, like `bj-dati.nt` unpacked for a triple
store (about 750 MB): `make ontologia` rebuilds them. With the dictionary `bj-dati.nt.gz`
is 28.6 MB (27.1 MB before the quotations, 25.6 MB before the front matter and appendices, 17.6 MB before the dictionary), over the 20 MB above which a regenerable file is not kept in
git, so it is listed in `.gitignore` too (an earlier commit tracks it: `git rm --cached
ontologia/bj-dati.nt.gz` stops that; `bj-dati.ttl.gz`, 15.6 MB, holds the same triples).
The other generated files are at most about 9 MB (the page 9.1 MB). The dumps and the page now also hold the
dictionary's text, which its own corpus calls private: see *Licence* before committing
them.

## Rebuild

```sh
make ontologia                                   # or:
vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

The script runs every stage in order and stops at the first failed check: `estrai.py`
(LaTeX to JSON), `riferimenti.py` (references to typed links), `test_riferimenti.py`, `dufour.py` and `test_dufour.py` (the citations of the Dizionario di Teologia Biblica), `paratesto.py` and `test_paratesto.py` (the front matter and the appendices),
`virgolette.py` and `test_virgolette.py` (the quotations between « and »),
`integrazione.py` and `test_integrazione.py` (the links between the parts and the corrections),
`rdf.py` (JSON to RDF and the VoID description), `verifica_rdf.py` (checks of the graph), `interroga.py` on
every query, `statistiche.py` (the *Size* tables and the query table of this README, from `bj-void.ttl`
and `build/query.md`) and `esploratore.py` (the explorer page). It takes about 16 minutes; every generated file comes out byte-identical on every
run (two rebuilds from an empty `ontologia/`, same md5), but for the query timings this README copies. The code is in `tools/ontologia/` (see its README).

## Explore

Open `esplora.html` in a browser (from disk; it makes no network request). It reads the
same three JSON files as the graph and shows the verse as the hub: the reader with note
calls and margin signs, a panel per verse with its notes, its margin references by
relation (‖ parallel, = doublet, ↗ quoted later, + key note, related) and everything
that points at it, a tree to explore the links of a verse (cards with the verse text and
its BJ notes in a hand-drawn contour), a whole-word search ignoring accents, and a book × book
matrix. The *Dizionario di Teologia Biblica* is in every view: the panel of a verse lists
the entries citing it (section, the sentence around the citation, a click opens the entry
at that paragraph), the reader marks with `◊` the verses an entry names on their own or in
a passage of at most 3 verses (and its heat can show them), `#voce/<slug>[/<paragraph>]`
shows an entry as printed with its citations as links, `#dizionario` lists the entries, the
search finds them, the tree hangs entry cards from a verse (and the passages an entry cites
from it), the overview counts them. The front matter and the appendices too: the panel
lists the entries of the index of notes and of the pastoral themes naming the verse (with
the BJ note the index points to) and the chronology entries citing it; `#indice-note`,
`#temi` (entry pages with every reference as a link and the notes to read in place),
`#cronologia` (the table by period, and the dynasties), `#introduzione-generale` (the
edition, the texts, the canon, the abbreviations and codices, the woodcuts); the reader
shows the acrostic letters in the margin; the search finds them. A sixth tab, *Appendici*, is the
hub of all this (`#appendici`) and of the pages added by the review of 2026-10-31: `#persona/<id>` (a
person of the dynasties with the verses, chronology rows and index sub-entries naming it),
`#calendario`, `#misure`, `#carte`; the entity pages carry an «Anche in» strip (the same concept in
the other index, in the dictionary, a person, a feast), the chronology rows the books they date, a
book page the rows dating it, the abbreviations the notes that cite each version or codex, and a
corrected link the editor's intervention in its preview. Direct speech and quoted words are in italic
everywhere, as in the Tufte edition (the guillemets, verse numbers and note calls upright): a «Discorsi»
switch above the chapter (key `q`) highlights them, the verse panel lists the quotations running through
the verse, and the search can look only in the words between guillemets («Discorsi»). The search also looks for the other
spellings of a name (`tools/ontologia/sinonimi.tsv`: Davide / David, Oreb / Horeb). Text and interface are set in Literata, embedded (SIL Open
Font License, `tools/ontologia/esploratore/font/`). The reference box reads the forms printed in the BJ (`Gen 2,4b`, `Mt 5,3ss`,
`Dt 7,9.12`, `Gen 1,1; 2,4`, `Sir prologo`). Ids in its addresses are those of the graph (`#John.3.16`), so a verse found
there is `verso:John.3.16` here. Details in `tools/ontologia/README.md`, stage 4.

## Design

### The verse is the hub

The user's unit is the verse (`bj:Versetto`): the margin references are printed beside
a line, the notes are called from a word of a verse, and both point at verses. So every
other resource hangs off verses:

```
Versetto ─dcterms:isPartOf→ Capitolo ─dcterms:isPartOf→ Libro ─dcterms:isPartOf→ Testamento ─→ Bibbia
Versetto ─inPericope→ Pericope ─inDivisione→ Divisione ─inDivisione→ Divisione
Versetto ─haNota→ Nota ─oa:hasBody→ oa:TextualBody (rdf:value = the note text)
Versetto ←commenta─ Nota ─oa:hasTarget→ Passaggio | Capitolo | Libro
Nota ←daNota─ Citazione ─aPassaggio→ Passaggio            (Paragrafo ←daParagrafo─ Citazione)
Versetto ←accantoA─ Margine ←nelMargine─ Rimando ─aPassaggio→ Passaggio
Versetto ←daVersetto─ Rimando ─relazione→ Relazione (SKOS: correlato, parallelo, doppione, citatoDopo …)
Passaggio ─inizio | fine | comprende→ Versetto
Versetto ─rimandaA | paralleloA | doppioneDi | citatoIn | rinviaANotaChiave→ Versetto   (shortcuts)
Nota | Introduzione ─citaVersetto→ Versetto                                             (shortcut)
```

(Terms without a prefix are `bj:`.)

A verse carries its text (`bj:testo`, `@it`, `\n` at poetry line ends; `bj:testoHtml`
only when the markup differs), its printed label (`bj:etichetta`: `8a`, `25,19`), number
and suffix, chapter number, canonical order (`bj:ordine`, 1…35,762), printed page
(`bj:pagina`, and `prov:wasDerivedFrom` the `bj:Pagina`, whose `bj:paginaPdf` is page + 33),
poetry flag, `dcterms:isPartOf` its chapter, `bj:inLibro`, `bj:inPericope`, and
`bj:precede` / `bj:segue` (next and previous verse in the printed order, across books).
Psalm titles (`bj:titoloSalmo`), acrostic letters (`bj:acrostico`), omitted verses
(`bj:omesso`, Mt 17,21 …), bracketed ones (`bj:traParentesi`) and the displaced Nm 25,19
(`bj:stampatoNelCapitolo 26`) keep what stage 1 found.

### Passages

Every reference names one or more stretches of consecutive verses: `bj:Passaggio`, with
`bj:inizio`, `bj:fine` and every verse in between (`bj:comprende`, numeric order, as
stage 2 expanded it). A passage is identified by its two ends
(`id/passaggio/Gen.2.4-Gen.2.25`, or `id/passaggio/Gen.2.4` for one verse) and shared by
all the references and notes that name it: 30,789 passages serve 58,185 `bj:aPassaggio` links.
A reference joining verses with "." (`Dt 7,9.12`) points to two passages. It is an
`oa:SpecificResource` whose `oa:hasSource` is the book. Verse parts (`2,4b`) are kept
in the printed text of the reference; the passage takes the whole verse.

### Notes are Web Annotations

A BJ note is an annotation in the W3C sense: a body (the note text) about a target (the
verses of its label), with a motivation (commenting). So `bj:Nota rdfs:subClassOf
oa:Annotation`:

- `oa:hasBody` an `oa:TextualBody` with `rdf:value` (plain text), `dc:format "text/plain"`,
  `dc:language "it"` (the HTML with `<em>` is `bj:testoHtml` on the note);
- `oa:hasTarget` the passage(s) of a verse label (`1,1–2,4a`), the chapter(s) of a
  chapter label (`c 4`, `cc 8–10`, a psalm number), the book of a «Nota introduttiva»;
  `bj:ambito` says which;
- `oa:motivatedBy oa:commenting`;
- `bj:richiamataDa` the verse whose text carries the call (`bj:haNota` is the inverse),
  with the call's offset in the verse text and HTML (`bj:posizioneTesto`, `bj:posizioneHtml`)
  and the word before it;
- `bj:commenta`, a shortcut to every verse the target covers (subproperty of
  `oa:hasTarget`): the verse-level query is `?n bj:commenta verso:Gen.1.1`.

So the notes use the standard annotation model (body, target, motivation) and tools that
know it can read them; the anchor and the offsets add what an annotation alone does not
say, where the call is printed.

### Margin references are reified, and also direct links

A margin entry (one `\mref`, `bj:Margine`, beside a verse: `bj:accantoA`) holds one or
more references separated by ";". Each reference becomes a `bj:Rimando`, because it has
more to say than "verse A refers to verse B":

| Property | |
|---|---|
| `bj:daVersetto` | the verse it is printed beside (`cito:hasCitingEntity`) |
| `bj:aPassaggio` | the passage(s) it names (`cito:hasCitedEntity`) |
| `bj:testo` | the reference as printed (`‖2Cr 2,10–11`, `Sal 89,8 (LXX)`) |
| `bj:relazione` | the margin sign, a SKOS concept (table below) |
| `bj:notaChiave` | true if it carries `+`; `bj:mandaANota` / `bj:mandaAMargine` say where to |
| `bj:conParalleli` | true if it carries `p` (and its parallels) |
| `bj:estensione` | `s` or `ss` (already expanded in the passage) |
| `bj:qualificatore`, `bj:numeroAlternativo` | `LXX`, `volg.`, `TM`…; another numbering printed with it |
| `bj:stato`, `bj:motivo` | resolved, partial, unresolved (with the reason), not a reference |
| `bj:nelMargine`, `bj:posizione` | the margin entry and the position in it |
| `bj:doppioneDelRimando` | for a `=` tied to the previous reference (`‖2Cr 1,14=9,25`, `‖Lc 8,16; =11,33`): that reference, whose doublet this one is; the verse relates to it as to the previous one |
| `bj:interpretazione` | how a siglum-less reference was read when the inherited book has no such verse |

A margin entry is beside the verse whose text holds the first word of its printed line
(`bj:accantoA`); when that line opens with the last one or two words of a verse and goes
on with the next one, the entry is the next verse's, and `bj:stampatoNelVersetto` keeps
the verse its call stands in (1,250 entries; tools README, stage 1).

Both `bj:Rimando` and `bj:Citazione` are `cito:Citation`s. The reified form answers
every question about the printed page (which sign, which misprint, which `+`). For graph
queries the links are also **materialised as direct verse-to-verse properties**:

| Sign | Meaning (BJ front matter) | Concept | Shortcut | Links |
|---|---|---|---|---:|
| none | a passage usefully compared | `bj:correlato` | `bj:rimandaA` | 25,098 |
| ‖ | literary parallel in another book | `bj:parallelo` | `bj:paralleloA` (symmetric) | 1,533 |
| = | doublet in the same book | `bj:doppione` | `bj:doppioneDi` (symmetric) | 511 |
| ↗ (typed `/`) | quoted or used in a later book (mostly NT) | `bj:citatoDopo` | `bj:citatoIn` | 659 |
| `+` after a reference | a key note, or a group of references, is there | (`bj:notaChiave true`) | `bj:rinviaANotaChiave` | 4,661 |
| `s`, `ss` | and the next verse, and following | (`bj:estensione`) | | 833 |
| `p` | and its parallels | (`bj:conParalleli true`) | | 203 |
| `(LXX)`, `(volg.)`, `(TM)` | Greek, Vulgate, Hebrew text or numbering | (`bj:qualificatore`) | | 141 |
| a bare number of another tradition | not a reference | `bj:numerazione` | | 866 |
| `(aramaico)` … | a remark | `bj:commento` | | 2 |

"Links" counts the printed margin references (28,669 in 18,455 margin entries). The
same marks inside notes and introductions are on their `bj:Citazione`s: over margins,
notes and introductions together there are 7,707 `+` (4,661 + 2,999 + 47), 1,877 `s`,
27 `ss`, 430 `p` and 157 qualifiers (`summary` in `build/collegamenti.json`).
`bj:paralleloA`, `bj:doppioneDi`, `bj:citatoIn`
and `bj:rinviaANotaChiave` are subproperties of `bj:rimandaA`, and the data holds that
closure: every verse-to-verse edge of a subproperty is also a `bj:rimandaA` edge, and
parallels and doublets are present in both directions (they are symmetric). A range is
expanded verse by verse (`Gen 1,1 → 2,4–25` gives 22 edges); self-links are left out.
So `bj:rimandaA` (83,952 edges) answers "which verses are connected", while counting
`bj:Rimando` resources answers "how many references are printed". Numbering entries,
comments and unresolved references have no shortcut. Each relation concept says which
shortcut it feeds (`bj:proprietaDiretta`).

### Citations in notes and introductions

Every reference cited in the text of a note or of an introduction paragraph is a
`bj:Citazione` (`bj:daNota` or `bj:daParagrafo`, the printed text, its offsets in the
plain text and the HTML, `bj:conCf` when "cf." precedes it, the same status, passages
and `+` as a margin reference). The shortcut `bj:citaVersetto` (subproperty of
`cito:cites`) links the note or the introduction directly to every verse cited:
130,079 edges.

### Identifiers

| Resource | IRI (under `https://massimo-nocentini.github.io/bibbia-gerusalemme/id/`) |
|---|---|
| Bible, testaments | `bibbia`, `testamento/AT`, `testamento/NT` |
| book | `libro/<OSIS>`: `libro/Gen`, `libro/Ps`, `libro/John`, `libro/EsthGr` |
| chapter | `capitolo/Gen.1`, `capitolo/Sir.Prol` |
| verse | `verso/<OSIS>.<chapter>.<label>`: `verso/John.3.16`, `verso/Isa.7.8a`, `verso/Sir.Prol.3` |
| division, pericope | `divisione/Gen.1` (n-th `\parte` of the book), `pericope/<first verse>` |
| note and its body | `nota/<anchor verse>[_n]`, `corpo/<same>` |
| margin entry, reference | `margine/<anchor>_<position>`, `rimando/<anchor>_<position>-<n>` |
| citation | `citazione/<note>-c<n>`, `citazione/intro-<intro>.<paragraph>-c<n>` |
| introduction, paragraph | `introduzione/pentateuco`, `paragrafo/pentateuco.3` |
| passage, page | `passaggio/<first>-<last>`, `pagina/<printed page>` |

Every resource also has `dcterms:identifier` = its id in `build/bibbia.json` and
`build/collegamenti.json` (`Gen.1.1`, `note:Gen.1.1_2`, `mref:Gen.1.1_2#5`), so the
graph joins with the JSON; the front matter and appendices, the pages and the integration have
theirs too (`cronologia.133`, `acr:Nah.1.3.1`, `abbreviazione.92`, `xilografia.Gen`, `pagina.35`,
`pagapp.3`, `allineamenti.tsv#7`, `riferimenti.CORREZIONI#7`); only a textual body (`corpo:`, an
intervention's `…/motivo`) is named after its annotation. A SHACL shape and a SPARQL check enforce it.
There are no blank nodes.

**Language tags.** Natural-language text and labels are `@it` (verse and paragraph texts,
titles, the labels of entries, sub-entries, abbreviations, acrostic letters, the colophon, the
meaning of an abbreviation); codes, references and sigla as printed are plain strings (`Gen 1,1`,
`skos:notation`, `bj:testo` of a reference); the reasons and rules the code writes are `@en` where
they are English; a measure's original name is `@he-Latn`, `@grc-Latn` or `@la`.

| Integration resource | IRI (under `id/`) |
|---|---|
| alignment, intervention | `allineamento/<row>`, `intervento/<table>/<row or link>` (its reason `…/motivo`) |
| version, numbering scheme | `versione/lxx`, `numerazione/volgata` |
| month, feast, unit, map | `calendario/mese/I`, `calendario/festa/pasqua`, `misura/cubito`, `carta/esodo`; the schemes `id:calendario`, `id:misure` |
| chronology dating | `cronologia/datazione/96-1` (entry and row), `…/163-c` (from its references) |

**Esther** is printed twice: the Greek text with its lettered additions is
`EsthGr` (not a standard OSIS code; `verso/EsthGr.1.1a` … `verso/EsthGr.4.17z`), the
Hebrew text `Esth`. Both have the CEI siglum `Est`; labels say `Est gr.` and `Est ebr.`.
A reference «Est …» points to the Hebrew text unless it names a lettered verse or a verse
only the Greek text has. **Psalms** keep the Hebrew numbering of the CEI; the titles are
verses, as printed (and also `bj:titoloSalmo`); `(LXX)` is kept as a qualifier
(`bj:qualificatore`): most psalm references so marked are in the Hebrew numbering (`Sal 2,9`,
`110,1`), and where the print uses the Greek numbering a table maps the reference to the CEI verse
(`tools/ontologia/numerazioni.tsv`: `Sal 103,12 (LXX)` is Ps 104,12, `54,20 (LXX)` Ps 55,21,
`68,35 (LXX)` Ps 68,36, `Sal 9–10,32+` Ps 10,11), said in `bj:interpretazione` («numerazione: …»).
The same table holds the other numberings the BJ prints (the Vulgate's: Es 22, 2Mac 12,46, At 19,41,
Gdt 13–14; the BJ's own Sir 36) and the older division of Sirach 34–36 that the dictionary cites. **Sirach**'s translator's prologue is chapter 0, `verso/Sir.Prol.1` …
`Sir.Prol.35`. **Daniel** keeps the Greek parts (3,24–90; 13; 14) in the CEI numbering,
**Baruch** 6 is the Letter of Jeremiah.

### The Dizionario di Teologia Biblica

The 849 entries of X. Léon-Dufour (ed.), *Dizionario di Teologia Biblica* (Marietti, 5th
Italian edition 1976; `build/dufour.json`, stage 2b) are in the same graph and the same
dumps, so a verse leads to the entries that cite it and an entry to the BJ notes and
margins on the verses it cites. The vocabulary is a section of `bj-ontologia.ttl`, not a
separate module: its terms share the `bj:` namespace, reuse `bj:Citazione`,
`bj:Passaggio`, `bj:stato` and the offsets, and every tool (the checks of `rdf.py`, the
JSON-LD context, `grafo.py`, the store-loading commands below) reads one ontology file.

```
Dizionario (skos:ConceptScheme) ─skos:hasTopConcept→ Voce (skos:Concept)          ─bj:curatore | bj:traduttore→ foaf:Person
Voce ─dcterms:creator→ foaf:Person            Voce ─prov:wasDerivedFrom→ PaginaDizionario ─dcterms:isPartOf→ Dizionario
ParagrafoVoce ─dcterms:isPartOf→ SezioneVoce ─dcterms:isPartOf→ SezioneVoce … ─dcterms:isPartOf→ Voce     (bj:nellaVoce: shortcut)
ParagrafoVoce | SezioneVoce ←daParagrafo | daSezione─ Citazione ─aPassaggio→ Passaggio ─comprende→ Versetto
Voce ─voceCitaVersetto→ Versetto ─citatoNellaVoce→ Voce                                 (shortcuts, both stored)
Voce ←daVoce─ CollegamentoVoce ─aVoce→ Voce, ─aSezione→ SezioneVoce, ─tipoCollegamento→ TipoCollegamento (SKOS)
Voce ─richiamaVoce | vediAncheVoce | rinviaAVoce→ Voce   (⊑ skos:related, stored both ways)
```

**Why entries are SKOS concepts.** A dictionary of biblical theology is a controlled
vocabulary: each headword names a concept (ALLEANZA, SANGUE), the entries are connected
by "see" and "see also" references, and the redirect entries are the non-preferred terms
of a thesaurus. SKOS says exactly that: `bj:Voce rdfs:subClassOf skos:Concept`, the
dictionary is the `skos:ConceptScheme` (`skos:inScheme`, `skos:topConceptOf`: the scheme
is flat), the headword is the `skos:prefLabel` (`@it`, as printed, in capitals), and the
links are `skos:related` (symmetric, so stored in both directions, self-links left out),
each through a directed subproperty that keeps its kind: `bj:richiamaVoce` (a `*word` in
the text, 8,242 pairs), `bj:vediAncheVoce` (the closing `→` list, 4,646),
`bj:rinviaAVoce` (a redirect entry, 2,142). A SKOS tool sees a thesaurus; a query that
cares about the kind uses the subproperty. The same resource is also the article written
about the concept (authors, pages, sections, paragraphs): splitting concept and article
would double 849 resources for no query that needs them apart.

Redirect entries (`bj:VoceRinvio`, 519) stay concepts of their own, because 459 of them
send to several entries (ABBA → adorazione II 3, cuore II 2 b, Dio NT IV, …: not a
synonym of any). The 60 that send to one entry only are the USE references of a
thesaurus: their headword is also an `skos:altLabel` of that entry (so the label is both
the prefLabel of the redirect concept and an altLabel of its target, which qSKOS would
flag as an overlapping label; no SKOS integrity condition forbids it). MONARCHIA,
whose only target the corpus did not find (`regalità`), is read as RE (stage 2b).

**Links between entries are reified** (`bj:CollegamentoVoce`, a `cito:Citation`, 18,207,
like the margin references): `bj:tipoCollegamento` (`bj:collegamentoAsterisco`,
`bj:collegamentoVediAnche`, `bj:collegamentoRinvio`, a SKOS scheme whose concepts say
their shortcut with `bj:proprietaDiretta`), `bj:daVoce`, `bj:aVoce`, the word as printed
(`bj:forma`: `*sofferente` for SOFFERENZA), the paragraph or section title a `*word`
stands in (`bj:daParagrafo`, `bj:daSezione`) and how the corpus matched it (`bj:metodo`),
the path printed in a `→` item (`bj:percorso` `VT I 2`) and the section it names
(`bj:aSezione`; `IV 0`, the opening of section IV, is section IV), `bj:stato`
`bj:risolto` or `bj:irrisolto` (9 links whose target was not found have no `bj:aVoce`;
stage 2b read again 13 see-also and redirect targets the corpus left without one).

**Sections and paragraphs.** `bj:SezioneVoce` (3,022) keeps the book's own path
(`bj:percorso` `B NT III 2`, `introd.`, `VT «Segno di benedizione»`), label, title
(`dcterms:title`, `bj:testoHtml` when it has a `*word`), kind (`part`, `testament`,
`roman`, `num`, `alpha`, `runin`, `caps`), depth (`bj:livello` 1–4), order and page.
`bj:ParagrafoVoce` (4,149) has the plain text (`bj:testo`, the `*` removed) and the HTML
(`<em>` italics, `<a class="voce" data-voce="slug">` around each resolved `*word`),
number and page; the 350 paragraphs printed before the first heading are parts of the
entry itself. Both have `bj:nellaVoce`, the shortcut to the entry (like `bj:inLibro`).

**Citations reuse the pattern of the notes.** Each of the 30,111 rows of `biblerefs.tsv`,
and each of the 146 bare references stage 2b recovered from the text, is a `bj:Citazione` from its paragraph (`bj:daParagrafo`, whose range is now
`bj:Paragrafo ∪ bj:ParagrafoVoce`) or, for the 27 printed in a section title,
`bj:daSezione`, to the `bj:Passaggio`s of its ranges: the passages are shared with the
BJ, so `passaggio:Gen.4.4-Gen.4.5` is one resource whether a BJ margin or the entry
ABELE names it (6,142 passages are named only by the dictionary). It carries what a note
citation carries (printed text, status and reason, `s`/`ss` in `bj:estensione`, `par.` in
`bj:conParalleli`, offsets in the plain text and the HTML for highlighting, `bj:conCf`
when `cfr.` precedes it, `bj:interpretazione` when its book was read elsewhere) and what
only the dictionary has: `bj:eAltrove` (`...`), `bj:libroImplicito` (1 inherited, 2 named
in the prose, 3 recovered), `bj:conversione` (a row read again), `bj:tipoMotivo` and `bj:statoFonte`.
`bj:notaChiave` is always false (the dictionary has no `+`). The shortcuts:

- `bj:voceCitaVersetto` (Voce → Versetto, ⊑ `cito:cites`): the entry cites, in a
  paragraph or title, a passage including the verse; 119,506 (entry, verse) pairs, from
  30,164 resolved or partial citations (130,806 verse hits);
- `bj:citatoNellaVoce` (Versetto → Voce, ⊑ `cito:isCitedBy`), its inverse, also stored,
  so the verse-centred question is one triple pattern: `verso:John.1.14
  bj:citatoNellaVoce ?voce` (35 entries); 28,997 verses are cited.

The paragraph of a citation is one hop further: `?p bj:comprende verso:John.1.14 . ?c
bj:aPassaggio ?p ; bj:daParagrafo ?par` (query 13).

**Authors and the work.** `id:dizionario` is a `bj:Dizionario` and the concept scheme,
with the title page's data: `dcterms:title`, `dcterms:alternative` (*Vocabulaire de
Théologie Biblique*@fr, the original), publisher Marietti, `dcterms:issued` 1976
(`xsd:gYear`), `bj:edizione` (5th edition, revised; reprint 2002; recast on the 2nd
French edition), `dcterms:bibliographicCitation`, `bj:curatore` the six directors
(Léon-Dufour, Duplacy, George, Grelot, Guillet, Lacan) and `bj:traduttore` the editors of
the Italian edition (G. Viola, A. Milanoli). The 70 collaborators are `foaf:Person`
(`foaf:name`, `givenName`, `familyName` as printed, `bj:ordineReligioso` `O.P`,
`bj:sede`), `dcterms:creator` of the entries they signed; `bj:firma` keeps the signature
as printed (`R. FEUILLET e A. VIARD`). NOME is signed part by part, so its VT and NT
sections also have their own `dcterms:creator`. Pages are `bj:PaginaDizionario` (⊑
`bj:Pagina`, 778, `bj:paginaPdf` = page + 21, a viewer's page number), so a section, a
paragraph or an entry is `prov:wasDerivedFrom` its page like a verse (an entry from all
its pages, `bj:pagina` the first, `bj:paginaFinale` the last).

**Numbering.** Stage 2b measured, quotation by quotation, that the dictionary uses this
Bible's numbering (Psalms in the Hebrew numbering with the titles as verses, 151
quotations against 1; `1–2 Re` are 1–2 Kings; Joel in 4 chapters, Malachi in 3; Daniel as
in the CEI; `Eccli` is Sirach, `Eccle` Qoelet), except Sirach 34–36, cited in the older
verse division of the Bible de Jérusalem (`Eccli 36, 5` «Rinnova i prodigi» is CEI 36,6):
those 24 citations are converted by a table and say so in `bj:conversione`. It read Greek
Esther's lettered verses from the text (`Est 4, 17 g`; a bare `Est 4, 17` is the prayers
4,17a–z), Obadiah printed `Ab` (`Ab 18`), and the book of a bare reference after a
`cfr.` aside (`(14, 16; cfr. Mt 28, 20)`: John, not Matthew) or named in the prose. The evidence is in `meta.summary.numbering` of `dufour.json` and in
`tools/ontologia/README.md`, stage 2b; the passages of a dictionary citation are verses
of this graph, and a check proves it (below).

**Licence.** The dictionary is copyrighted (Marietti), like the BJ (EDB): its research
corpus `../dufour/corpus` calls itself private, for personal study, and is not pushed to
Overleaf (it is a git repository of its own; its README still says its `.gitignore` is
`*`, which its current `.gitignore` no longer is). The dumps now hold the full text of its
paragraphs: keep `bj-dati.ttl.gz`, `bj-dati.nt.gz` (and anything built from them) local,
and decide before committing them to a repository with a remote whether that repository
may hold the dictionary's text. The same holds for `esplora.html`, tracked like the
dumps: it now embeds the dictionary's paragraphs (gzipped) to show the entries.

**Identifiers** (under `id/`): the work `dizionario`; an entry `voce/<slug>` (the slug of
the corpus: `voce/abele`, `voce/figlio-di-dio`); its sections `voce/<slug>/sezione/<path>`
(the path in ASCII joined by `-`: `voce/adorazione/sezione/II-1`,
`voce/nome/sezione/VT`), paragraphs `voce/<slug>/paragrafo/<n>`, citations
`voce/<slug>/citazione/<n>` (the n-th row of the entry in `biblerefs.tsv`; `r<n>` for the
n-th bare reference the source did not link, recovered from the text), links
`voce/<slug>/collegamento/<n>` (the n-th link printed in the entry); people
`persona/<id>`; pages `dizionario/pagina/<n>`. `dcterms:identifier` is the id of
`dufour.json` (`abele`, `abele.3`, `abele#2`) or, for sections and links, the IRI's local
part. These IRIs hold `/` after the prefix, so the Turtle writes them in full.

### The front matter and the appendices

What the volume prints before the Old Testament (`progetti/introduzione-generale`) and
after the Apocalypse (`progetti/appendici`) is the third part of the graph (VoID subset
`vp:paratesto`), read by `tools/ontologia/paratesto.py` into `build/paratesto.json`. Its
pages have their own numbering: `bj:PaginaPreliminare` (`pagprel:xxii`, Roman, PDF = n + 5)
and `bj:PaginaAppendice` (`pagapp:3`, PDF = n + 3001), both `bj:Pagina`; every resource has
`bj:pagina` and `prov:wasDerivedFrom` its page, as the Bible's.

```
id:edizione (bj:Edizione) ─bj:edizioneDi→ id:bibbia        ←bj:stampaDi─ bj:Stampa (5 printings)
testopre:presentazione (bj:TestoPreliminare) ─dcterms:creator→ persona:gianfranco-ravasi
    ←dcterms:isPartOf─ paragrafo:presentazione.1 (bj:Paragrafo) ←bj:daParagrafo─ bj:Citazione ─bj:aPassaggio→ …
canone:ebraico (bj:Canone) ←isPartOf─ canone:ebraico/gruppo/3 ←isPartOf─ canone:ebraico/voce/8 ─bj:comprendeLibro→ libro:1Sam, libro:2Sam
abbreviazione:9 (bj:Abbreviazione, skos:notation "1 2 Cor") ─bj:abbreviaLibro→ libro:1Cor, libro:2Cor
abbreviazione:92 ─bj:abbreviaManoscritto→ manoscritto:01 (bj:Manoscritto, bj:numeroGregoryAland "01")
xilografia:Gen (bj:Xilografia) ─bj:apreLibro→ libro:Gen ; ─bj:illustra→ passaggio:Gen.1.27 ; ─bj:illustraVersetto→ verso:Gen.1.27
```

- **The edition**: imprint data as printed (publisher, place, ISBN, the three sources of
  text, notes and woodcuts as `dcterms:source`, the two imprimatur, three rights, the
  printer, the colophon as `bj:testo`), the editorial direction (`bj:direzioneEditoriale`)
  and the editor (`bj:curatore`), five printings with the printed date and the month
  (`dcterms:date`, `xsd:gYearMonth`).
- **Texts**: the Presentazione, the three prefaces (author as `foaf:Person`, `bj:firma`
  and `bj:qualifica` as printed, `bj:corsivo` when the text is printed in italics), the
  two divisions of the canon and the Avvertenze, with their paragraphs as `bj:Paragrafo`
  and their Bible references as `bj:Citazione` (read like those of an introduction, no
  current book) and the shortcut `bj:citaVersetto`.
- **The canon**: the two lists as printed (`bj:Canone` → `bj:GruppoCanone` → `bj:VoceCanone`),
  each item with the books (`bj:comprendeLibro`) or chapters (`bj:comprendeCapitolo`:
  Susanna = Dn 13) of this Bible; the Greek list says `bj:deuterocanonico` (printed in
  italics) and `bj:apocrifo` (in brackets: no book here).
- **Abbreviations and codices**: each row of the lists (`skos:notation`, `bj:significato`,
  `bj:tipoAbbreviazione`); a book siglum names its books through the CEI sigla of
  `canone.py` («Est» both texts of Esther), a codex or papyrus row a `bj:Manoscritto` with
  its Gregory-Aland number when it has one (`01`, `P46`, `066`; not the vetus latina).
- **Woodcuts**: the Avvertenze list the passage the woodcut opening each book illustrates.

```
indice:note (bj:Indice, skos:ConceptScheme) ─skos:hasTopConcept→ indice:note/voce/91 (bj:VoceIndice «Caleb»)
indice:note/voce/5/1 (sub-entry «Abitazione di Dio») ─skos:broader→ indice:note/voce/5
citazione:indice-note.91-c1 (bj:Citazione «Gb 14,6») ─bj:daVoceIndice→ indice:note/voce/91
    ─bj:aPassaggio→ passaggio:Job.14.6 (as printed) ; ─bj:aPassaggioCorretto→ passaggio:Josh.14.6 ;
    ─bj:indicaNota→ nota:Josh.14.6 ; bj:testoCorretto "Gs 14,6" ; bj:correzione "…" ; bj:corrispondenzaNota
indice:note/voce/91 ─bj:indicaVersetto→ verso:Josh.14.6 ─bj:nellIndice→ indice:note/voce/91 ; ─bj:indicaNota→ nota:Josh.14.6
indice:note/voce/2 ─bj:vediVoce, skos:related→ indice:note/voce/186 («v. Ebiatàr») ; ─bj:rinviaAIntroduzione→ introduzione:…
```

- **The two indices** are SKOS concept schemes. Entries are top concepts (`skos:prefLabel`
  as printed, `bj:stile` maiuscoletto / corsivo / tondo / grassetto); sub-entries are
  `skos:broader` the entry (`skos:narrower` back), labelled with the dash replaced by the
  headword («Abitazione di Dio») and `bj:etichetta` as printed («- di Dio»). «v.» is
  `bj:vediVoce` (the printed direction) under `skos:related` (both directions); page numbers
  of the edition are `bj:rinviaAIntroduzione` (the introduction printed there).
- **Each printed reference** is a `bj:Citazione` from its (sub-)entry, made by the same
  resolver (`bj:libroImplicito` 1 when its book is inherited from the chain, 2 when only the
  text names it, `bj:seguito` «e par», «ecc.»). In the index of the notes it also points to
  the BJ note at its first verse (`bj:indicaNota`), with `bj:corrispondenzaNota`: `nota` (a
  note is called or starts there), `copre` (the verse is inside a note's label),
  `capitolo`, `rimandi` (margin references only), `nessuna`: the index exists to point to
  notes. The shortcuts `bj:indicaVersetto` / `bj:nellIndice` and `bj:indicaNota` hang from the
  most specific (sub-)entry.
- **Misprints** stay as printed (`bj:testo`, `bj:aPassaggio` the verse printed, or no passage
  when it does not exist). Where the volume's log of doubts (`progetti/appendici/checklist-ocr.md`)
  states the correction and its evidence (5 in the index of notes: Caleb `Gb 14,6` → Gs 14,6,
  Lc 22,60 → 66, Gv 13,24 → 34, Mt 5,11 → 17, Is 7,10 → 14; 11 in the themes: `Cr 28,9` → 1Cr,
  `Na 8,7–9` → Ne, the Isaiah and Psalm references printed after another siglum, …) the
  citation adds `bj:aPassaggioCorretto`, `bj:testoCorretto`, `bj:correzione`, the note there,
  and the shortcuts use the corrected passage only. Misprints the log does not correct
  (`Gv 2,38`, `Rm 11–7`, Ester `4,18ss`, …) keep only their reason.

```
cronologia:tavola (bj:TavolaCronologica) ←isPartOf─ cronologia:sezione/6 ←isPartOf─ cronologia:voce/133 (bj:EventoCronologia)
cronologia:voce/133 bj:testo "ASSARADDON (680–669). …" ; bj:datazione "680–669" ; bj:annoInizio -680 ; bj:annoFine -669 ;
    bj:colonna bj:colonnaUniversale ; bj:riga 44 ; bj:ordine 1 ; bj:nomeMaiuscolo "ASSARADDON" ; bj:citaVersetto …
dinastia:P15 (bj:PersonaStorica, schema:Person «11. Erode il Grande») ─schema:spouse→ dinastia:P16 ; ─schema:children→ …
verso:Nah.1.3 ─bj:haLetteraAcrostica→ acr:Nah.1.3.1 (bj:LetteraAcrostica «Bet», "ב", bj:posizioneAlfabeto 2, bj:rigo 3)
```

- **The chronological table**: 9 sections, its 585 entries as `bj:EventoCronologia` (a
  `schema:Event`) with the text as printed (`bj:testoHtml` keeps italics and small caps), the
  column (a SKOS concept of `bj:colonneCronologia`: world history, Palestinian and biblical
  history, the kingdoms of Israel and Judah, Egypt, Lagids, Seleucids), the row of the print
  and the order in its cell, the years of the margin scale as printed (`bj:anniMargine`), the
  date as printed (`bj:datazione`: at the start of the entry, «Nov. 164», «Fra il 34 e il
  45», or the one span in parentheses, «(51–30)») and, when it is unambiguous, the years
  `bj:annoInizio` / `bj:annoFine` (integers, negative before Christ, no year zero; sections
  I–VIII are before Christ, section IX turns at the first row dated «d.C.»; `bj:circa` for
  «ca.», «verso»), the names in small caps and capitals, and its Bible references as
  `bj:Citazione` (`bj:daEvento`, offsets in the entry text) with `bj:citaVersetto`.
  Integers and not `xsd:gYear`: XSD 1.0 and 1.1 disagree on the year before 1, and the
  print counts years, it does not give dates.
- **The dynasties** (Hasmonean and Herodian): the 34 persons of `dinastie.tsv` as
  `bj:PersonaStorica` (also `schema:Person`) in `dinastia:tavola`, with the order number,
  the dates and the italics as printed, and the family links as **schema.org**
  `schema:parent`, `schema:children` (its inverse, materialised) and `schema:spouse` (both
  directions). schema.org is used because these three properties say exactly what the chart
  draws and nothing more; FOAF has no kinship, and BIO models a family through birth and
  marriage events the chart does not print. The persons are not `foaf:Person` (whose shape
  asks for a family name: these are historical persons, not authors).
- **Acrostic letters**: besides the `bj:acrostico` literals (now up to three on a verse:
  Sal 111,9), each letter is a `bj:LetteraAcrostica` with the name as printed but without the
  parentheses (`bj:testo` «Mem», as `bj:acrostico`; SHACL: a name, no brackets), the Hebrew
  character, its place in the alphabet, the line of the verse it opens (`bj:rigo`: Na 1,3 Bet
  is on the third line, where the stanza begins) and `bj:mancanteNelTesto` true for the five
  printed in parentheses, «(Mem)» (Sal 10,3.4.6.10; 25,18). All the letters are
  `\acrostico{…}` in the volumes since stage 6b (`\acrostico{(Mem)}` for the bracketed ones).
  Stage 1 records the line (`acrostic_lines`); 339 letters in Psalms, Pr 31, Lamentations
  (132, added in stage 3 of this work) and Na 1 (11).

### The links between the parts, and the corrections (review of 2026-10-31, session F2)

Stage 2d (`tools/ontologia/integrazione.py`) reads hand tables, each reviewed row by row (precision
over recall), and writes `build/integrazione.json`; `rdf.py` makes of it the fourth VoID subset
(`vp:integrazione`).

```
indice:note/voce/7 ─skos:closeMatch→ voce:abramo        (and back; broadMatch ↔ narrowMatch)
allineamento:12 (bj:Allineamento) ─bj:allineamentoDa→ indice:note/voce/7 ; ─bj:allineamentoA→ voce:abramo ;
    bj:proprietaMapping skos:closeMatch ; bj:metodoAllineamento "label" ; bj:revisore "R2" ; bj:versettiComuni 10
verso:Mark.6.14 ─bj:nominaPersona (⊑ schema:mentions)→ dinastia:P23 ─bj:nominatoIn→ verso:Mark.6.14
cronologia:voce/430 ─bj:riguardaPersona→ dinastia:P23 ;  indice:note/voce/204/1 ─bj:indicaPersona→ dinastia:P29
cronologia:datazione/96-1 (bj:Datazione) ─bj:datazioneDi→ cronologia:voce/96 ; ─bj:datazioneLibro→ libro:Amos ; bj:tipoDatazione "ministero"
cronologia:voce/96 ─bj:riguardaLibro→ libro:Amos ─bj:nellaCronologia→ cronologia:voce/96   (libro:Amos ←bj:introduce─ its introduction)
nota:Luke.8.26 ─bj:citaTestimone→ manoscritto:03 ;  a reference qualified «LXX» ─bj:secondoVersione→ versione:lxx
calendario:festa/encenie (bj:Festa) ─bj:nelMese→ calendario:mese/IX ; ─bj:citaVersetto→ verso:John.10.22 ; ─skos:relatedMatch→ indice:note/voce/156
misura:cubito (bj:Unita) bj:valore 45.0 ; bj:unitaQudt unit:CentiM ; bj:rapporto "1" ;  verso:… ─bj:nominaMisura→ misura:cubito
carta:tribu (bj:Carta ⊑ schema:Map) ─bj:raffiguraLibro→ libro:Josh ; ─bj:raffiguraPassaggio→ passaggio:Josh.13.1-Josh.21.45
intervento:riferimenti.CORREZIONI/7 (bj:Intervento ⊑ oa:Annotation) oa:motivatedBy bj:interpretando ; bj:regola bj:regolaManuale ;
    oa:hasTarget citazione:John.13.2-c2 ; oa:hasBody …/motivo ; bj:tabellaFonte "riferimenti.CORREZIONI" ; bj:rigaFonte "7" ;
    bj:testoStampato "cf. 13,29" ; prov:wasDerivedFrom pagina:2554 ; prov:wasAttributedTo persona:massimo-nocentini
```

- **Concept alignments** (`allineamenti.tsv`, 466 rows): the index of notes and the pastoral themes
  with the dictionary (the 393 pairs session R2 accepted of 413 candidates; 3 of its 7 «rivedere»
  accepted with a reason, Magi / MAGIA rejected, the direction of the head-word matches set:
  «Agnello» `skos:narrowMatch` AGNELLO DI DIO, «Croce di Gesù» `skos:broadMatch` CROCE; 6 hand rows),
  the themes with the index of notes (60, by label or head word) and the 5 pairs the index of notes
  prints twice without a «v.» (Caifa / Anna e Caifa, Kyrios / Signore (Gesù), …: `skos:closeMatch`,
  not `bj:vediVoce`, so the print stays distinguishable). Each is reified (`bj:Allineamento`: method,
  reviewer, table row, the verses both sides point to, recomputed at every build); a head-word match
  with no shared verse needs a reviewer's reason. `skos:exactMatch` is not used.
- **Persons** (`persone.tsv`): the verses that name a dynasty person, by book or chapter and name
  with the exceptions written out (291 verses: Erode in Mt 2 is P15, in Mt 14, Mc 6, Lc 23 P23, in At 12
  P29; not «il pretorio di Erode» of At 23,35 nor Cesarèa di Filippo), the index sub-entries «Erode
  Agrippa I» / «II» and three references printed under «Erode» (the entry itself is merged with no
  person), and 112 (entry, person) pairs of chronology sections VIII–IX read one by one.
- **Chronology and books** (`cronologia-libri.tsv`, 46 rows): the entries that date a book's
  composition, a prophet's ministry or the end of a narrative («750 ca.: Amos e poco dopo Osea»,
  «Malachia e forse: Giobbe, Proverbi, …»), and every entry with references dating the books it
  cites (kind `citato`); the book reaches its introduction through `bj:introduce`.
- **Versions and codices** (`testimoni.tsv`): eleven versions (`bj:Versione`; with `bj:Manoscritto`
  under `bj:Testimone`) and the 2,899 notes naming them; the codices and papyri named in a list of
  witnesses of a note («con S, B, ecc.»; D is Dᵉ in the Gospels and Acts, Dᵖ in Paul; a codex only in
  the books its row of the abbreviations says it holds): 149 notes, 459 mentions. The qualifier of a
  reference that names a version is linked to it (`bj:secondoVersione`).
- **Calendar, measures and coins, maps** (`calendario.tsv`, `misure.tsv`, `carte.tsv`, by hand from
  the appendices): 12 months (`bj:Mese`: notation, Babylonian, old and Macedonian names) and 8 feasts
  (`bj:Festa`: month, day, references as `bj:Citazione` with `bj:daVoceTavola`, the same concept in the
  indices and the dictionary as `skos:relatedMatch`); 61 units (`bj:Unita`: value as `xsd:decimal`, the
  QUDT unit IRI as data, the ratio as printed and as a number, its base, equivalences, approximate);
  the verses naming an unambiguous unit or month; 10 maps (`bj:Carta`: title, PDF page, image file,
  period, books and passages). The misprints of their prose (`paratesto.CORREZIONI_PROSA`: Zac for Zc,
  Esd 6,69 for 2,69) are now corrections in the graph.
- **The corrections** (R2-20): every row of every correction table (`riferimenti.CORREZIONI`,
  `CORREZIONI_VERSO`, `AGGIUNTE`, `REFUSI`, `REFUSI_RIFERIMENTI`, `MISPRINT`, `numerazioni.tsv`,
  `paratesto.CORREZIONI_INDICI`, `CORREZIONI_PROSA`, `tsv.RIMANDI`, `PAGINE_ESTRANEE`, `dufour.CORREZIONI`,
  `PARAGRAFI`, `FORME`, the editorial notes of `dinastie.tsv`) and every rule or reading of stages 2,
  2b and 2c (the sense of the sentence, the readings of the dictionary and the indices, the dictionary's
  conversions) is one `bj:Intervento` (1,433): `oa:motivatedBy` `oa:editing` (a misprint),
  `bj:interpretando` (a reading), `oa:linking` (a link added) or `oa:describing` (a note); the rule
  (`bj:regola`, a concept of `bj:regole`), the source table and row, the printed and the read text, the
  page that is the evidence. Today's literals (`bj:interpretazione`, `bj:correzione`, `bj:conversione`,
  `bj:aPassaggioCorretto`) stay as shortcuts, and the corrected reference also carries `bj:regola`.
  The items of the volumes' checklists are not imported (they are prose; the tables cite them).
- **Numbering schemes** (R2-21): `bj:SchemaNumerazione` resources for the CEI and the four schemes of
  `numerazioni.tsv`; each of its rows names its scheme on its intervention.
- **Kinds of reason** (R2-11): every unresolved or partial reference has `bj:categoriaMotivo`, a
  concept of `bj:motivi` (extra-canonical, out of range, misprinted range, not understood, other
  numbering, ambiguous book, other); the text stays in `bj:motivo`.
- **Index sub-entries** (R2-08): `skos:prefLabel` is «Headword: label» with the printed dash replaced by
  the headword where it stands for it («Abramo: seno di Abramo», «Amicizia: tra Davide e Giònata»);
  today's expansion is `skos:altLabel`, `bj:etichetta` keeps the print.

### Quotations: direct speech and quoted words (session F4)

The text between « and » is a `bj:Discorso` (an `oa:SpecificResource` of the resource it is read in),
found by `tools/ontologia/virgolette.py`, the detector the Tufte edition shares (its italic): in the
text of the books (5,957, across verses too), the notes (10,279: the volumes' `\detto` is a quotation in
guillemets, typed or not), the introductions (529), the front matter (59) and the appendices (25). Who
speaks is not inferred.

```
discorso:Deut.5.1.1 (bj:Discorso) ─oa:hasSource→ libro:Deut ; bj:parte "testo"
    ─bj:iniziaIn→ verso:Deut.5.1 ; bj:inizioCarattere 41        (the «, in its bj:testo)
    ─bj:finisceIn→ verso:Deut.26.19 ; bj:fineCarattere 163      (just after the »)
    ─bj:attraversa→ verso:Deut.5.1 … verso:Deut.26.19 (532) ; bj:lunghezza 77654
discorso:Deut.20.3.1 ─bj:dentroDi→ discorso:Deut.5.1.1 ; bj:testo "Ascolta, Israele! …" (≤ 200 characters)
discorso:Sir.16.22.1 bj:sbilanciato true ; bj:motivo "« closed only by a » inside italic text (Sir.16.22), …"
discorso:nota/Sir.16.22.1 ─oa:hasSource→ nota:Sir.16.22 ; ─bj:iniziaIn→ nota:Sir.16.22 (offsets in the rdf:value of its body)
```

- **The rules** (`virgolette.py`): each book's verses, each note, introduction, front-matter text or
  entry is a scope; `«` opens, `»` closes the last one open, the outermost pairs are the italic ones and
  a pair inside another has `bj:dentroDi` (the 7 of Dt 20–22 inside Moses' discourse, 4 in notes); a
  guillemet with no partner is `bj:sbilanciato` with its reason, and only two are in the text of the
  books, both printed so (Sir 16,22, Am 7,17: `tools/ontologia/README.md`, stage 9); guillemets already in
  italic are skipped. The same rules make the italic of the Tufte edition, and its 5,948 + 7 + 2
  quotations of the books are these, book by book (`tools/tufte/test_genera.py`, `test_lettori`).
- **Ends**: `bj:iniziaIn` / `bj:finisceIn` the verse (note, paragraph, entry) whose plain text holds the
  `«` / the `»`, with the offsets: `bj:inizioCarattere` at the `«`, `bj:fineCarattere` just after the `»`,
  so the words are the characters between them (verses joined by a space). One end only when unbalanced.
- **The words** (`bj:testo`) only when at most 200 characters (15,087 of 16,847 balanced): all of them
  would repeat 2.1 million characters, 1.9 of them the verse text (43% of it again); a long discourse is
  read in its verses (`bj:attraversa`, the offsets). `bj:lunghezza` is always there (query 34).
- **Parts** (`bj:parte`): `testo`, `nota`, `introduzione`, `preliminari`, `appendici`. In the appendices
  only what the graph holds as text: the chronology entries and the index headwords and sub-entries (the
  calendar, the measures and the comments between the references of the index are not text here).

### Alignments

Only where the meaning matches: `dcterms:isPartOf`, `dcterms:title`, `dcterms:identifier`;
W3C Web Annotation (`oa:Annotation`, `oa:TextualBody`, `oa:SpecificResource`,
`oa:hasTarget`, `oa:hasSource`, `oa:commenting`); CiTO (`cito:Citation`,
`cito:hasCitingEntity`, `cito:hasCitedEntity`, `cito:cites`); PROV
(`prov:wasDerivedFrom` the printed page); SKOS for the relations, statuses and note
scopes, and for the dictionary's entries (`skos:Concept`, `skos:ConceptScheme`,
`skos:prefLabel`, `skos:altLabel`, `skos:related`); FOAF for its authors (`foaf:Person`,
`foaf:name`); `dcterms:creator`, `dcterms:contributor` (super-property of `bj:curatore`,
`bj:traduttore`), `dcterms:issued`, `dcterms:alternative`, `dcterms:bibliographicCitation`
for the work; `cito:isCitedBy` above `bj:citatoNellaVoce` and `bj:nellIndice`; SKOS
`skos:broader`, `skos:narrower`, `skos:notation` for the indices and the abbreviations;
schema.org only for what nothing above says: `schema:Event` (superclass of
`bj:EventoCronologia`), `schema:Person` with `schema:parent`, `schema:children`,
`schema:spouse` for the dynasties, `schema:mentions` (above `bj:nominaPersona`, `bj:riguardaPersona`,
`bj:nominaMese`, `bj:nominaMisura`) and `schema:Map` (above `bj:Carta`); SKOS mapping properties
(`skos:closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`) between the indices and the
dictionary; `dcterms:subject` above `bj:riguardaLibro`, `dcterms:temporal` for the period of a map;
PROV `prov:wasAttributedTo` for the interventions; QUDT unit IRIs (`unit:CentiM`, `unit:L`, …) as
data, never dereferenced.
The ontology carries `vann:preferredNamespacePrefix "bj"`; the dataset is described in
VoID (`bj-void.ttl`: `void:Dataset` with title, rights, source, dumps, vocabularies,
`void:exampleResource`, and one class and property partition each, with counts).
Every `bj:` term has `rdfs:label` and `rdfs:comment` in Italian and English.

## Checks

`rdf.py` checks while building: every `bj:` term used is declared, object properties
have IRIs and datatype properties literals of their range, no IRI is dangling, the
counts equal the JSON (the dictionary's against `dufour.json`: 849 entries, 519
redirects, 3,022 sections, 4,149 paragraphs, 18,207 links, 30,257 citations, 72 people),
the passages of each link and citation hold exactly its targets (the corrected passages of
the indices too), the front matter and appendices against `paratesto.json`; it writes
`bj-void.ttl` and parses it back (`void:triples` equal to the graph, and to the sum of the
three subsets).
`verifica_rdf.py` then checks the written files:

- rdflib's N-Triples and Turtle parsers and the fast reader of `grafo.py` give the same
  3,976,937 triples;
- OWL sanity: each `bj:` term is declared with one kind; all 2.7 million triples with a
  `bj:` property have subject and object of its `rdfs:domain` and `rdfs:range`;
- 115 SPARQL integrity queries on the whole graph, about 5 minutes (counts against the JSON, exactly one
  text and chapter per verse, `bj:precede` goes to order + 1, inverses and symmetric and
  subproperty closures complete, every shortcut edge backed by a printed reference or
  citation, resolved references have passages); 20 of them on the dictionary: its counts
  equal stage 2b (entries, redirects, sections, paragraphs, links and the 9 unresolved,
  citations by status 30,162 / 2 / 93, the 28,997 verses of its verse index), every verse
  a dictionary citation's passages include is a declared `bj:Versetto`, every link target is
  an entry and every target section belongs to it, sections and paragraphs lie in their
  entry, `bj:voceCitaVersetto` holds exactly the 119,506 (entry, verse) pairs of the JSON,
  each backed by a citation, `bj:citatoNellaVoce` is its exact inverse, the entry shortcuts
  are backed by a printed link and `skos:related` is symmetric; 33 on the front matter and
  appendices: counts against `paratesto.json` (texts, paragraphs, manuscripts, woodcuts,
  entries and sub-entries of each index, references by status, chronology entries, years and
  citations, persons, acrostic letters), the 39 books of the Hebrew canon, every sub-entry
  under a top entry of its scheme and `skos:narrower` the inverse of `skos:broader`,
  `bj:indicaVersetto` equal to the (entry, verse) pairs of the JSON and backed by a citation of
  the entry, `bj:nellIndice` its inverse, the notes an entry points to backed by its citations
  and lying at a verse of the citation's passage (two exceptions, both in Esther, counted),
  the corrections, `schema:spouse` symmetric and `schema:children` the inverse of
  `schema:parent`; 22 on the links between the parts: alignments one per row, each with its
  SKOS shortcut, the mapping closures, the shared verses really shared, persons, datings backed and
  closed, a cited book a book the entry cites, witnesses, calendar and measures, interventions one per
  row, each with a target, a rule and a source, every reading, correction and conversion literal with
  its intervention, the rule shortcut backed, every typed resource (bodies aside) with an identifier;
  16 on the quotations (`bj:Discorso`): counts by part equal to `virgolette.py`'s, nested and
  unbalanced ones, both ends when balanced, the ends of the text verses in order, the verses spanned
  between the ends (16,478), the offsets inside the text at a `«` and just after a `»`, nesting acyclic
  in one resource and inside a longer balanced quotation, the words when at most 200 characters;
- SHACL (`bj-forme.ttl`, pyshacl) on the **whole graph**: 55 node shapes (8 for the
  dictionary: work, people, pages, entries, redirects, sections, paragraphs, links; 18 for
  the front matter and appendices: edition, printings, pages, texts, canon, groups, items,
  abbreviations, manuscripts, woodcuts, indices, entries, the chronological table, its
  sections and entries, the genealogical chart, its persons, acrostic letters; the citation
  shape also takes a dictionary paragraph or section title, an index entry or a chronology
  entry as citing entity, or an item of the calendar, measures and maps; 11 for the integration:
  identifiers of every typed resource, alignments, persons named, datings, versions, witnesses,
  months, feasts, units, maps, interventions; 1 for the quotations), 266,233 typed resources, about 8
  minutes; it conforms;
- the JSON-LD context: John 3,16 with its notes, margins and passages, and the entry ABELE
  with its sections, paragraphs, citations and links, serialised with
  `bj-contesto.jsonld` (compact terms and prefixes) and parsed back, gives the same triples.

## Querying

With rdflib (the venv of the repository):

```sh
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/01-versetto.rq
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/*.rq --limite 10
vendor/venv/bin/python -I tools/ontologia/interroga.py -e 'SELECT ?n ?t WHERE {
    verso:Gen.1.1 bj:haNota ?n . ?n oa:hasBody/rdf:value ?t }' --largo
```

Loading takes about 30–45 s (a reader specialised for `bj-dati.nt.gz`; rdflib's own
parser needs about 2 minutes, and a pickled store is no faster, so there is no cache). In
Python: `sys.path.insert(0, 'tools/ontologia'); import grafo; g = grafo.carica()`.

rdflib evaluates SPARQL as written: keep one selective constant per basic graph pattern
and turn the others into `FILTER (?x = libro:Ps)`, avoid `VALUES` in front of
`UNION`s, and order on group keys from an outer query (see the examples). It also puts
`?x a bj:Classe` patterns first and evaluates a join of two subqueries row by row, so on
the 30,000 dictionary citations prefer one grouped subquery (`18-autori-e-libri.rq`
takes the arg-max as the largest "count name" string), and `OPTIONAL { … BIND }` does not
bind (a count over it stays 0).

For speed load `bj-dati.nt.gz` and `bj-ontologia.ttl` into a triple store, all of them
local:

```sh
gunzip -k bj-dati.nt.gz
oxigraph load --location bj.db --file bj-dati.nt --file bj-ontologia.ttl --file bj-void.ttl
oxigraph serve --location bj.db          # SPARQL endpoint on localhost:7878
tdb2.tdbloader --loc bj.tdb bj-dati.nt.gz bj-ontologia.ttl && fuseki-server --loc bj.tdb /bj
```

GraphDB imports the `.ttl.gz` or `.nt.gz` directly. With RDFS reasoning a store also
derives what the data leaves to the vocabulary: `dcterms:isPartOf` for `bj:inPericope`,
`bj:inDivisione` and `bj:nelMargine`, `oa:hasTarget` for `bj:commenta`, `cito:cites` for
`bj:citaVersetto`, and the superclasses `oa:Annotation`, `cito:Citation`,
`oa:SpecificResource`.

### The examples (`query/`)

Rows and rdflib timings at the last build (`build/query.md`); the graph loads once.

<!-- generato da tools/ontologia/statistiche.py: query -->
| Query | Question | Rows | Seconds |
|---|---|---:|---:|
| `01-versetto.rq` | a verse (Gv 3,16) with its notes and margin references | 5 | 0.12 |
| `02-entranti.rq` | incoming references to Is 7,14 (margins and note citations) | 27 | 1.20 |
| `03-at-citato-nel-nt.rq` | OT verses quoted later in the NT (↗) | 618 | 0.19 |
| `04-samuele-re-cronache.rq` | parallels (‖) between Samuel-Kings and Chronicles, both ways | 275 | 0.25 |
| `05-piu-rimandati.rq` | the 25 verses most often named by a margin reference | 25 | 8.22 |
| `06-note-che-citano.rq` | notes and introductions citing Gen 15,6 | 7 | 0.05 |
| `07-note-chiave.rq` | key-note hubs: notes most often sent to by «+» | 25 | 0.58 |
| `08-due-passi.rq` | two-hop paths Gen 22,2 → ? → Rm 8,32 along `bj:rimandaA` | 1 | 0.02 |
| `09-matrice-libri.rq` | book × book matrix of margin references | 2373 | 3.59 |
| `10-pericope.rq` | the verses of the pericope holding Lc 15,11, with their note counts | 22 | 0.02 |
| `11-salmi-nel-nt.rq` | Psalms quoted in the NT, by NT book | 16 | 0.14 |
| `12-irrisolti.rq` | unresolved references with their reason (BJ 85, dictionary 93) | 178 | 0.16 |
| `13-voci-che-citano.rq` | the dictionary entries citing Gv 1,14, with section, paragraph, citation as printed, page (a paragraph before the first heading has no section) | 39 | 0.03 |
| `14-piu-citati-dal-dizionario.rq` | the 25 verses most cited by the dictionary (citations, entries; Is 53,12 first) | 25 | 20.82 |
| `15-voci-con-versetti-comuni.rq` | the entries sharing the most cited verses with AGNELLO DI DIO, and whether they are linked (the all-pairs form is in the file: about 2 minutes in rdflib) | 25 | 0.29 |
| `16-voce-e-note-bj.rq` | for the entry ABELE: its verses, the BJ notes commenting on them and those citing them | 16 | 1.56 |
| `17-dizionario-e-margini.rq` | pairs of verses a paragraph of AGNELLO DI DIO cites together that the BJ margins also link, with the margin references | 57 | 0.49 |
| `18-autori-e-libri.rq` | the 70 authors: citations in the entries they signed, books cited, the most cited book (Grelot: Salmi, 483) | 70 | 3.53 |
| `19-indice-note-di-un-versetto.rq` | the entries of the index of notes pointing to Gv 1,14, the note they send to and how it matches | 5 | 0.02 |
| `20-voce-indice-e-note.rq` | the entry ALLEANZA of the index of notes: sub-entries, references, the start of the notes they send to | 21 | 4.24 |
| `21-temi-pastorali-di-un-libro.rq` | the pastoral themes pointing to most verses of Tobia, with their sub-themes | 4 | 2.62 |
| `22-cronologia-esilio.rq` | the chronological table between 600 and 530 BC (the entries whose years overlap it, reigns across it included; by year, column, position): printed date, years, column, text, references | 34 | 0.30 |
| `23-figli-di-erode.rq` | the children of Herod the Great with their mothers and spouses (`schema:`) | 5 | 0.02 |
| `24-refusi-degli-indici.rq` | the misprints of the indices with the corrected reference, why, and the note it sends to | 21 | 0.05 |
| `25-acrostici.rq` | the alphabetic poems by chapter: letters, the line where the Bet stanza begins (its first verse: Lam 3,4), letters missing in the Hebrew text | 15 | 0.54 |
| `26-canone-greco.rq` | the deuterocanonical books of the Greek list and the books or chapters of this Bible they are | 9 | 0.01 |
| `27-indice-e-dizionario.rq` | the alignments of the entries of the index of notes and of the themes with the dictionary: the SKOS property, the method, the reviewer and the shared verses; here for the entries holding «Amore» | 7 | 0.10 |
| `28-erode-antipa.rq` | e le voci della tavola cronologica che lo riguardano. Herod Antipas: the verses naming him, by book, and the chronology entries about him | 5 | 0.02 |
| `29-note-e-testimoni.rq` | e le versioni (TM, LXX, Volgata, ...). The codices and papyri named by the notes, with how many notes name them, and the versions | 38 | 0.40 |
| `30-interventi.rq` | e regola, quanti interventi, con la motivazione e un esempio con il suo motivo. The editor's corrections and readings in one model: by table and rule, how many, the motivation, an example | 27 | 0.55 |
| `31-libri-nella-cronologia.rq` | la voce, i suoi anni e il tipo (composizione, ministero, evento); dal libro si arriva alla sua introduzione. The books in the chronological table: for each book dated by hand, the entry, its years and the kind | 74 | 0.07 |
| `32-misure-e-monete.rq` | rapporto stampato all'unità di base, e quanti versetti le nominano. The measures and coins: value (with the QUDT unit kept as data), printed ratio to the base, verses naming them | 61 | 0.09 |
| `33-discorsi-di-un-capitolo.rq` | the quotations between guillemets that touch Gen 3 (bj:Discorso, in the text): where they start and end, their words (when short), how many characters, the quotation holding them | 13 | 1.10 |
| `34-discorsi-piu-lunghi.rq` | the 25 longest quotations of the text: where they start and end, how many verses and characters | 25 | 1.14 |
<!-- fine del blocco generato -->

## Size

Written by `tools/ontologia/statistiche.py` from `bj-void.ttl` at every build (the numbers of the
VoID description; R2-01). `bj-dati.ttl.gz` and `bj-dati.nt.gz` are about 15.6 and 28.6 MB;
`bj-ontologia.ttl` declares 333 `bj:` terms; `bj-forme.ttl` has 55 node shapes.

<!-- generato da tools/ontologia/statistiche.py: dimensioni -->
3,976,937 triples about 266,233 subjects (266,233 typed resources), 58 classes, 259 properties. Four VoID subsets:
- the Bible: 2,642,959 triples (`vp:bibbia`);
- the dictionary: 1,121,613 triples (`vp:dizionario`);
- the front matter and appendices: 162,712 triples (`vp:paratesto`);
- the links between the parts, the calendar, measures and maps, the corrections: 49,653 triples (`vp:integrazione`).

Linksets: `bj:riguardaLibro` 215, `skos:mappingRelation` 401, `bj:indicaVersetto` 16,449, `bj:citaTestimone` 4,870, `bj:nellIndice` 16,449, `bj:nominaPersona` 291, `bj:citatoNellaVoce` 119,506, `bj:voceCitaVersetto` 119,506.

| Class | Resources | Property (largest) | Triples |
|---|---:|---|---:|
| `bj:Citazione` | 63,635 | `rdf:type` | 267,640 |
| `bj:Passaggio` | 37,822 | `rdfs:label` | 254,042 |
| `bj:Versetto` | 35,762 | `dcterms:identifier` | 254,038 |
| `bj:Rimando` | 28,669 | `bj:comprende` | 196,516 |
| `bj:Margine` | 18,455 | `bj:testo` | 167,440 |
| `bj:CollegamentoVoce` | 18,207 | `bj:citaVersetto` | 141,289 |
| `bj:Discorso` | 16,849 | `bj:voceCitaVersetto` | 119,506 |
| `oa:TextualBody` | 12,195 | `bj:citatoNellaVoce` | 119,506 |
| `bj:Nota` | 10,762 | `bj:stato` | 110,511 |
| `bj:ParagrafoVoce` | 4,149 | `bj:aPassaggio` | 94,851 |
| `bj:Pericope` | 3,455 | `bj:notaChiave` | 92,304 |
| `bj:SezioneVoce` | 3,022 | `bj:conParalleli` | 92,304 |
| `bj:Pagina` | 2,935 | `prov:wasDerivedFrom` | 88,042 |
| `bj:VoceIndice` | 2,512 | `bj:posizioneTesto` | 87,895 |
| `bj:Intervento` | 1,433 | `bj:posizioneHtml` | 87,825 |
| `bj:Capitolo` | 1,339 | `bj:pagina` | 86,310 |
| `skos:Concept` | 849 | `bj:rimandaA` | 83,959 |
| `bj:Voce` | 849 | `bj:lunghezza` | 75,525 |
| `bj:PaginaDizionario` | 778 | `bj:conCf` | 63,635 |
| `bj:Paragrafo` | 625 | `bj:fineHtml` | 58,608 |
| `bj:EventoCronologia` | 585 | `bj:nellaVoce` | 55,635 |
| `bj:VoceRinvio` | 519 | `oa:hasSource` | 54,671 |
| `bj:Allineamento` | 466 | `bj:etichetta` | 52,690 |
| `bj:Divisione` | 452 | `bj:ordine` | 48,341 |
| `bj:LetteraAcrostica` | 339 | `bj:posizione` | 47,124 |
| `bj:Datazione` | 160 | `dcterms:isPartOf` | 46,558 |
| `bj:Abbreviazione` | 147 | `bj:numero` | 45,735 |
| `foaf:Person` | 78 | `bj:daParagrafo` | 42,978 |
| `bj:Libro` | 74 | `bj:inizio` | 41,729 |
| `bj:Xilografia` | 73 | `bj:fine` | 41,729 |
| `bj:PaginaAppendice` | 64 | `bj:inLibro` | 41,008 |
| `bj:Unita` | 61 | `bj:commenta` | 38,939 |
| `bj:VoceCanone` | 59 | `bj:poesia` | 35,762 |
| `bj:Manoscritto` | 56 | `bj:numeroCapitolo` | 35,762 |
| `schema:Person` | 34 | `bj:segue` | 35,761 |
| `bj:PersonaStorica` | 34 | `bj:precede` | 35,761 |
| `bj:PaginaPreliminare` | 24 | `bj:inPericope` | 35,259 |
| `bj:Introduzione` | 21 | `bj:relazione` | 28,669 |
| `bj:Mese` | 12 | `bj:nelMargine` | 28,669 |
| `bj:Versione` | 11 | `bj:daVersetto` | 28,669 |
| `bj:Carta` | 10 | `bj:parolaPrecedente` | 27,597 |
| `bj:SezioneCronologia` | 9 | `bj:daNota` | 25,437 |
| `bj:Festa` | 8 | `bj:testoHtml` | 21,702 |
| `bj:TestoPreliminare` | 7 | `skos:related` | 19,704 |
| `bj:GruppoCanone` | 7 | `bj:accantoA` | 18,455 |
| `skos:ConceptScheme` | 5 | `bj:tipoCollegamento` | 18,207 |
| `bj:Stampa` | 5 | `bj:forma` | 18,207 |
| `bj:SchemaNumerazione` | 5 | `bj:daVoce` | 18,207 |
| `bj:Testamento` | 2 | `bj:aVoce` | 18,198 |
| `bj:Indice` | 2 | `bj:parte` | 16,849 |
| `bj:Canone` | 2 | `bj:inizioCarattere` | 16,848 |
| `bj:TavolaMisure` | 1 | `bj:iniziaIn` | 16,848 |
| `bj:TavolaGenealogica` | 1 | `bj:finisceIn` | 16,848 |
| `bj:TavolaCronologica` | 1 | `bj:fineCarattere` | 16,848 |
| `bj:Edizione` | 1 | `bj:attraversa` | 16,478 |
| `bj:Dizionario` | 1 | `bj:nellIndice` | 16,449 |
| `bj:Calendario` | 1 | `bj:indicaVersetto` | 16,449 |
| `bj:Bibbia` | 1 | `bj:paralleloA` | 14,926 |
<!-- fine del blocco generato -->

Session F4 (2026-11-01) added 200,064 triples (3,776,873 → 3,976,937): the 16,849 quotations
(`bj:Discorso`, 16,765 in the Bible subset, 84 in the front matter and appendices) with their ends,
parts, sources, 16,478 verses spanned, lengths, the words of the 15,087 of at most 200 characters, 11
parents and the 2 unbalanced ones.

The review of 2026-10-31 (sessions F1 and F2) added 58,248 triples to the 3,718,625 of the build
before it: F1 95 (the references read again, the literal checks' fixes), F2 58,153: the fourth subset
(49,653 triples: 466 alignments with their shortcuts and shared verses, 408 person links, 160 datings,
the versions and 4,870 (note, witness) pairs, the calendar, measures and maps with 70 references and
the verses naming them, 1,433 interventions with their bodies) and, in the three others, the
identifiers of the pages and of the front matter (R2-02), the kinds of reason, the rule shortcuts, the
`skos:altLabel` of the sub-entries, the pages of the woodcuts and of the acrostic letters and
`bj:inVersetto`.

## Known limits

- A passage takes whole verses: `2,4b` is Gen 2,4 (the part is kept in `bj:testo`).
- `p` (and its parallels) is a flag; the parallels are not expanded.
- `ss` stops at the end of the pericope (stage 2), other numberings are converted only where
  `tools/ontologia/numerazioni.tsv` has the reference (16 references), and a siglum-less reference in a
  note means the book in force unless that book has no such verse (then the current book,
  the last book named, or verses of the previous chapter are tried, `bj:interpretazione`);
  see `tools/ontologia/README.md`, stage 2.
- A margin reference is tied to the verse of its printed line; one pushed down a crowded
  margin column stays with the line it is printed beside.
- Unresolved references (85 in the BJ, 93 in the dictionary, `query/12-irrisolti.rq`)
  are kept with their reason and no passage; misprints are never corrected in the BJ
  (a range with a misprinted end is linked to its first verse, `bj:parziale`; in the
  dictionary a few are corrected by hand, with their reason in `bj:conversione`; in the
  indices 16, where the volume's log of doubts states the correction, as
  `bj:aPassaggioCorretto` beside the printed passage).
- The sense of the sentence (stage 2) reads again 87 citations and adds 817 by rules and a
  table of 48 rows written after an audit of the Tufte edition; other citations whose book
  is given only by the prose may still be read in the book in force.
- Indices: a reference names the passage printed; the note it «points to» is the one at the
  first verse (or covering it), as `tsv.py` decides: two Esther references resolve in the
  Hebrew text while their BJ note is on the Greek one; 3 «v.» match no headword
  (`v. Festa`, `v. Tentazione`, `v. Sorte`): they point to the obvious entries (`Feste
  d’Israele`, `Tentare`, `Sorti (tirare le)`) by a table of `tsv.py`, with the reason in the
  item (`why`); «cf. pp. 1032, 1376» (Sapienza) are not pages of this edition and point to no
  introduction; a sub-entry printed twice in one theme is two sub-entries.
- Chronology: years only where the date is unambiguous (388 of 585 entries); the margin
  years are a scale of the print, kept as printed, not a date of the entry; names in small
  caps or capitals are strings (the persons of the dynasties are linked by a reviewed list,
  `persone.tsv`, not by name). The calendar, the measures and the maps are in the graph from hand
  tables checked against the appendices (`calendario.tsv`, `misure.tsv`, `carte.tsv`), not parsed.
- Front matter: the Bible references of the texts are read without a current book, so
  «Esodo (2,2–3)» in a running text is a reference only where the book is named in a form
  the resolver knows (the woodcut list is read on its own, all 73 resolved).
- `bj:rimandaA` expands ranges verse by verse, so wide references (`Gb 38–39`) weigh as
  much as many narrow ones in path and degree queries; count `bj:Rimando` resources for
  printed references.
- Division levels come from the numbering style of the headings (stage 1).
- Dictionary: `par.` is a flag (`bj:conParalleli`), `ss` stops at the end of the pericope
  or before the next verse printed in its group; a citation counts every verse of its
  range, so whole chapters and long `ss` weigh like many verses (`query/14` says how to
  keep only citations of at most three verses). The book of a siglum-less reference
  follows rules (the source's inheritance, `cfr.` asides, books named in the prose) and a
  few choices by hand: a sample of 40 such rows read right, but some may still be read in
  the wrong book; one stays unresolved as ambiguous (PASQUA `13`). Bare references printed
  in forms the corpus did not parse (`la 63, 19` for Is, `Is I, 11-20`) are not linked: stage 2b.
  A `→` item has no `bj:aSezione` when it prints no path (2,190, `bj:esitoPercorso` `none`)
  or when the corpus did not find its path in the target entry (58 `unresolved`, as `2 e` in
  PARADISO); `carcere III` (AMORE, PERDIZIONE) has no target entry at all.
- Headwords are kept as printed (capitals) in `skos:prefLabel`; authors' names likewise
  in `foaf:name`.
- Quotations (`bj:Discorso`): the text between « and » as printed, nothing more: no speaker, no
  quotation marked only by a verb of saying, the inner “…” of a quotation not a resource; a guillemet
  inside italic text is skipped (Sir 16,22's » in its italic stich: the quotation is unbalanced, as the
  Tufte edition leaves it upright); the words only up to 200 characters (`bj:testo`); in the appendices
  only the chronology and the index headwords (the calendar and the measures are not text of the graph).
