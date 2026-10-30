# La Bibbia di Gerusalemme as a semantic-web base

A verse-centred RDF graph of «La Bibbia di Gerusalemme» (EDB: CEI 2008 Italian text with
the notes and marginal cross-references of the Bible de Jérusalem), built from the 14
proofread LaTeX volumes in `progetti/`. Every verse is linked to the notes called from
it, the notes commenting on it, the references printed in its margin, and every citation
of it in a note or an introduction.

The text is copyrighted: everything here is for local use only. The IRIs live under
`https://massimo-nocentini.github.io/bibbia-gerusalemme/`, but nothing is published
there; they are names, not links to follow.

| File | What | Made by |
|---|---|---|
| `bj-ontologia.ttl` | OWL 2 vocabulary, prefix `bj:` | hand-written |
| `bj-forme.ttl` | SHACL shapes for the data | hand-written |
| `query/*.rq` | 12 SPARQL examples | hand-written |
| `bj-dati.ttl.gz` | the data graph, Turtle | `tools/ontologia/rdf.py` |
| `bj-dati.nt.gz` | the same triples, N-Triples (for bulk loaders) | `tools/ontologia/rdf.py` |
| `bj-contesto.jsonld` | JSON-LD context: `bj:` terms by local name, data prefixes (pages are `pag:`) | `tools/ontologia/rdf.py` |
| `bj-void.ttl` | VoID description of the data: title, rights, source, dumps, vocabularies, triples per class and per property | `tools/ontologia/rdf.py` |
| `build/bibbia.json`, `build/collegamenti.json` | intermediate JSON (stages 1 and 2) | `estrai.py`, `riferimenti.py` |
| `build/query.md` | rows and timings of the example queries at the last build | `interroga.py` |
| `esplora.html` | the offline explorer: one page, data embedded, opens from disk | `tools/ontologia/esploratore.py` |

`build/` (about 64 MB) is listed in `.gitignore`, like `bj-dati.nt` unpacked for a triple
store (about 500 MB): `make ontologia` rebuilds them. The other generated files are under
20 MB each (`bj-dati.nt.gz` 17.6 MB the largest) and can be tracked.

## Rebuild

```sh
make ontologia                                   # or:
vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

The script runs every stage in order and stops at the first failed check: `estrai.py`
(LaTeX to JSON), `riferimenti.py` (references to typed links), `test_riferimenti.py`,
`rdf.py` (JSON to RDF and the VoID description), `verifica_rdf.py` (checks of the graph), `interroga.py` on
every query and `esploratore.py` (the explorer page). It takes about 6½ minutes; every generated file comes out byte-identical on every
run (two rebuilds from an empty `ontologia/`, same md5). The code is in `tools/ontologia/` (see its README).

## Explore

Open `esplora.html` in a browser (from disk; it makes no network request). It reads the
same two JSON files as the graph and shows the verse as the hub: the reader with note
calls and margin signs, a panel per verse with its notes, its margin references by
relation (‖ parallel, = doublet, ↗ quoted later, + key note, related) and everything
that points at it, an ego-network view, a whole-word search ignoring accents, and a book × book
matrix. The reference box reads the forms printed in the BJ (`Gen 2,4b`, `Mt 5,3ss`,
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
graph joins with the JSON. There are no blank nodes.

**Esther** is printed twice: the Greek text with its lettered additions is
`EsthGr` (not a standard OSIS code; `verso/EsthGr.1.1a` … `verso/EsthGr.4.17z`), the
Hebrew text `Esth`. Both have the CEI siglum `Est`; labels say `Est gr.` and `Est ebr.`.
A reference «Est …» points to the Hebrew text unless it names a lettered verse or a verse
only the Greek text has. **Psalms** keep the Hebrew numbering of the CEI; the titles are
verses, as printed (and also `bj:titoloSalmo`); `(LXX)` is a qualifier, never a
renumbering. **Sirach**'s translator's prologue is chapter 0, `verso/Sir.Prol.1` …
`Sir.Prol.35`. **Daniel** keeps the Greek parts (3,24–90; 13; 14) in the CEI numbering,
**Baruch** 6 is the Letter of Jeremiah.

### Alignments

Only where the meaning matches: `dcterms:isPartOf`, `dcterms:title`, `dcterms:identifier`;
W3C Web Annotation (`oa:Annotation`, `oa:TextualBody`, `oa:SpecificResource`,
`oa:hasTarget`, `oa:hasSource`, `oa:commenting`); CiTO (`cito:Citation`,
`cito:hasCitingEntity`, `cito:hasCitedEntity`, `cito:cites`); PROV
(`prov:wasDerivedFrom` the printed page); SKOS for the relations, statuses and note
scopes. schema.org adds nothing here that these do not say, so it is not used.
The ontology carries `vann:preferredNamespacePrefix "bj"`; the dataset is described in
VoID (`bj-void.ttl`: `void:Dataset` with title, rights, source, dumps, vocabularies,
`void:exampleResource`, and one class and property partition each, with counts).
Every `bj:` term has `rdfs:label` and `rdfs:comment` in Italian and English.

## Checks

`rdf.py` checks while building: every `bj:` term used is declared, object properties
have IRIs and datatype properties literals of their range, no IRI is dangling, the
counts equal the JSON, the passages of each link hold exactly its targets; it writes
`bj-void.ttl` and parses it back (`void:triples` equal to the graph).
`verifica_rdf.py` then checks the written files:

- rdflib's N-Triples and Turtle parsers and the fast reader of `grafo.py` give the same
  2,406,107 triples;
- OWL sanity: each `bj:` term is declared with one kind; all 1.7 million triples with a
  `bj:` property have subject and object of its `rdfs:domain` and `rdfs:range`;
- 23 SPARQL integrity queries on the whole graph, about 90 s (counts against the JSON, exactly one
  text and chapter per verse, `bj:precede` goes to order + 1, inverses and symmetric and
  subproperty closures complete, every shortcut edge backed by a printed reference or
  citation, resolved references have passages);
- SHACL (`bj-forme.ttl`, pyshacl) on the **whole graph**: 17 node shapes, every typed
  resource, about 2.5 minutes; it conforms;
- the JSON-LD context: John 3,16 with its notes, margins and passages, serialised with
  `bj-contesto.jsonld` (compact terms and prefixes) and parsed back, gives the same triples.

## Querying

With rdflib (the venv of the repository):

```sh
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/01-versetto.rq
vendor/venv/bin/python -I tools/ontologia/interroga.py ontologia/query/*.rq --limite 10
vendor/venv/bin/python -I tools/ontologia/interroga.py -e 'SELECT ?n ?t WHERE {
    verso:Gen.1.1 bj:haNota ?n . ?n oa:hasBody/rdf:value ?t }' --largo
```

Loading takes about 20 s (a reader specialised for `bj-dati.nt.gz`; rdflib's own
parser needs about 65 s, and a pickled store is no faster, so there is no cache). In
Python: `sys.path.insert(0, 'tools/ontologia'); import grafo; g = grafo.carica()`.

rdflib evaluates SPARQL as written: keep one selective constant per basic graph pattern
and turn the others into `FILTER (?x = libro:Ps)`, avoid `VALUES` in front of
`UNION`s, and order on group keys from an outer query (see the examples).

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

| Query | Question | Rows | Seconds |
|---|---|---:|---:|
| `01-versetto.rq` | a verse (Gv 3,16) with its notes and margin references | 5 | 0.13 |
| `02-entranti.rq` | incoming references to Is 7,14 (margins and note citations) | 27 | 0.75 |
| `03-at-citato-nel-nt.rq` | OT verses quoted later in the NT (↗) | 618 | 0.18 |
| `04-samuele-re-cronache.rq` | parallels (‖) between Samuel-Kings and Chronicles, both ways | 275 | 0.24 |
| `05-piu-rimandati.rq` | the 25 verses most often named by a margin reference | 25 | 8.16 |
| `06-note-che-citano.rq` | notes and introductions citing Gen 15,6 | 7 | 0.04 |
| `07-note-chiave.rq` | key-note hubs: notes most often sent to by «+» | 25 | 0.57 |
| `08-due-passi.rq` | two-hop paths Gen 22,2 → ? → Rm 8,32 along `bj:rimandaA` | 1 | 0.02 |
| `09-matrice-libri.rq` | book × book matrix of margin references | 2372 | 3.60 |
| `10-pericope.rq` | the verses of the pericope holding Lc 15,11, with their note counts | 22 | 0.02 |
| `11-salmi-nel-nt.rq` | Psalms quoted in the NT, by NT book | 16 | 0.13 |
| `12-irrisolti.rq` | unresolved references with their reason | 101 | 0.10 |

## Size

`bj-dati.ttl.gz` 9.4 MB, `bj-dati.nt.gz` 17.6 MB (2,406,107 triples about
171,330 resources; uncompressed N-Triples 499 MB); `bj-ontologia.ttl` 993
triples, 106 `bj:` terms; `bj-forme.ttl` 17 node shapes.

| Resources | | Triples by property (largest) | |
|---|---:|---|---:|
| `bj:Versetto` | 35,762 | `rdf:type` | 171,330 |
| `bj:Passaggio` | 30,789 | `rdfs:label` | 160,570 |
| `bj:Rimando` | 28,669 | `dcterms:identifier` | 157,632 |
| `bj:Citazione` | 27,305 | `bj:comprende` | 135,718 |
| `bj:Margine` | 18,455 | `bj:citaVersetto` | 130,079 |
| `bj:Nota`, `oa:TextualBody` | 10,762 each | `bj:testo` | 110,738 |
| `bj:Pericope` | 3,455 | `bj:rimandaA` | 83,952 |
| `bj:Pagina` | 2,935 | `bj:pagina`, `prov:wasDerivedFrom` | 69,433 each |
| `bj:Capitolo` | 1,339 | `bj:aPassaggio` | 58,185 |
| `bj:Paragrafo` | 547 | `bj:commenta` | 38,939 |
| `bj:Divisione` | 452 | `bj:paralleloA` | 14,926 |
| `bj:Libro` | 74 | `bj:haNota`, `bj:richiamataDa` | 10,762 each |
| `bj:Introduzione` | 21 | `bj:rinviaANotaChiave` | 4,663 |
| `bj:Testamento`, `bj:Bibbia` | 2, 1 | `bj:doppioneDi`, `bj:citatoIn` | 1,848, 1,370 |

## Known limits

- A passage takes whole verses: `2,4b` is Gen 2,4 (the part is kept in `bj:testo`).
- `p` (and its parallels) is a flag; the parallels are not expanded.
- `ss` stops at the end of the pericope (stage 2), `(LXX)` psalm numbers are not
  converted (`Sal 103,12 (LXX)` resolves to Ps 103,12), and a siglum-less reference in a
  note means the book in force unless that book has no such verse (then the current book,
  the last book named, or verses of the previous chapter are tried, `bj:interpretazione`);
  see `tools/ontologia/README.md`, stage 2.
- A margin reference is tied to the verse of its printed line; one pushed down a crowded
  margin column stays with the line it is printed beside.
- Unresolved references (101, `query/12-irrisolti.rq`) are kept with their reason and no
  passage; misprints are never corrected.
- `bj:rimandaA` expands ranges verse by verse, so wide references (`Gb 38–39`) weigh as
  much as many narrow ones in path and degree queries; count `bj:Rimando` resources for
  printed references.
- Division levels come from the numbering style of the headings (stage 1).
