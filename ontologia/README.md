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
pastoral themes, the chronological table and the Hasmonean and Herodian dynasties; and the
acrostic letters of the alphabetic poems, beside the line each one opens.

Both texts are copyrighted (EDB, Marietti): everything here is for local use only (see
*Licence* below for the dictionary). The IRIs live under
`https://massimo-nocentini.github.io/bibbia-gerusalemme/`, but nothing is published
there; they are names, not links to follow.

| File | What | Made by |
|---|---|---|
| `bj-ontologia.ttl` | OWL 2 vocabulary, prefix `bj:` (the dictionary, then the front matter and appendices, in its last sections) | hand-written |
| `bj-forme.ttl` | SHACL shapes for the data | hand-written |
| `query/*.rq` | 26 SPARQL examples (13–18 on the dictionary, 19–26 on the front matter, appendices and acrostics) | hand-written |
| `bj-dati.ttl.gz` | the data graph, Turtle: the Bible, the dictionary, the front matter and appendices | `tools/ontologia/rdf.py` |
| `bj-dati.nt.gz` | the same triples, N-Triples (for bulk loaders) | `tools/ontologia/rdf.py` |
| `bj-contesto.jsonld` | JSON-LD context: `bj:` terms by local name, data prefixes (pages are `pag:`) | `tools/ontologia/rdf.py` |
| `bj-void.ttl` | VoID description of the data: title, rights, source, dumps, vocabularies, triples per class and per property, a subset each for the Bible, the dictionary and the front matter and appendices, four entry ↔ verse linksets | `tools/ontologia/rdf.py` |
| `build/bibbia.json`, `build/collegamenti.json` | intermediate JSON (stages 1 and 2) | `estrai.py`, `riferimenti.py` |
| `build/dufour.json` | the entries of the *Dizionario di Teologia Biblica* (Léon-Dufour, 1976; read from `../dufour/corpus`) and their 30,257 Bible citations resolved to verses | `dufour.py` |
| `build/paratesto.json` | the front matter and the appendices (`progetti/introduzione-generale`, `progetti/appendici`), their references resolved; `build/cronologia.tsv`, `indice-note.tsv`, `indice-temi.tsv` made again by `progetti/appendici/tsv.py` | `paratesto.py` |
| `build/query.md` | rows and timings of the example queries at the last build | `interroga.py` |
| `esplora.html` | the offline explorer: one page, data embedded (the Bible and the dictionary), opens from disk | `tools/ontologia/esploratore.py` |

`build/` (about 92 MB) is listed in `.gitignore`, like `bj-dati.nt` unpacked for a triple
store (about 750 MB): `make ontologia` rebuilds them. With the dictionary `bj-dati.nt.gz`
is 26.7 MB (25.6 MB before the front matter and appendices, 17.6 MB before the dictionary), over the 20 MB above which a regenerable file is not kept in
git, so it is listed in `.gitignore` too (an earlier commit tracks it: `git rm --cached
ontologia/bj-dati.nt.gz` stops that; `bj-dati.ttl.gz`, 14.5 MB, holds the same triples).
The other generated files are under 9 MB. The dumps and the page now also hold the
dictionary's text, which its own corpus calls private: see *Licence* before committing
them.

## Rebuild

```sh
make ontologia                                   # or:
vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

The script runs every stage in order and stops at the first failed check: `estrai.py`
(LaTeX to JSON), `riferimenti.py` (references to typed links), `test_riferimenti.py`, `dufour.py` and `test_dufour.py` (the citations of the Dizionario di Teologia Biblica), `paratesto.py` and `test_paratesto.py` (the front matter and the appendices),
`rdf.py` (JSON to RDF and the VoID description), `verifica_rdf.py` (checks of the graph), `interroga.py` on
every query and `esploratore.py` (the explorer page). It takes about 13 minutes; every generated file comes out byte-identical on every
run (two rebuilds from an empty `ontologia/`, same md5). The code is in `tools/ontologia/` (see its README).

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
shows the acrostic letters in the margin; the search finds them. The text is set in Literata and the interface in Inter, both embedded (SIL Open
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
`schema:spouse` for the dynasties.
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
  3,718,625 triples;
- OWL sanity: each `bj:` term is declared with one kind; all 2.7 million triples with a
  `bj:` property have subject and object of its `rdfs:domain` and `rdfs:range`;
- 77 SPARQL integrity queries on the whole graph, about 3 minutes (counts against the JSON, exactly one
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
  `schema:parent`;
- SHACL (`bj-forme.ttl`, pyshacl) on the **whole graph**: 43 node shapes (8 for the
  dictionary: work, people, pages, entries, redirects, sections, paragraphs, links; 18 for
  the front matter and appendices: edition, printings, pages, texts, canon, groups, items,
  abbreviations, manuscripts, woodcuts, indices, entries, the chronological table, its
  sections and entries, the genealogical chart, its persons, acrostic letters; the citation
  shape also takes a dictionary paragraph or section title, an index entry or a chronology
  entry as citing entity), 245,638 typed resources, about 6 minutes; it conforms;
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

| Query | Question | Rows | Seconds |
|---|---|---:|---:|
| `01-versetto.rq` | a verse (Gv 3,16) with its notes and margin references | 5 | 0.13 |
| `02-entranti.rq` | incoming references to Is 7,14 (margins and note citations) | 27 | 1.12 |
| `03-at-citato-nel-nt.rq` | OT verses quoted later in the NT (↗) | 618 | 0.19 |
| `04-samuele-re-cronache.rq` | parallels (‖) between Samuel-Kings and Chronicles, both ways | 275 | 0.24 |
| `05-piu-rimandati.rq` | the 25 verses most often named by a margin reference | 25 | 8.30 |
| `06-note-che-citano.rq` | notes and introductions citing Gen 15,6 | 7 | 0.04 |
| `07-note-chiave.rq` | key-note hubs: notes most often sent to by «+» | 25 | 0.59 |
| `08-due-passi.rq` | two-hop paths Gen 22,2 → ? → Rm 8,32 along `bj:rimandaA` | 1 | 0.02 |
| `09-matrice-libri.rq` | book × book matrix of margin references | 2373 | 3.58 |
| `10-pericope.rq` | the verses of the pericope holding Lc 15,11, with their note counts | 22 | 0.02 |
| `11-salmi-nel-nt.rq` | Psalms quoted in the NT, by NT book | 16 | 0.14 |
| `12-irrisolti.rq` | unresolved references with their reason (BJ 95, dictionary 93) | 188 | 0.16 |
| `13-voci-che-citano.rq` | the dictionary entries citing Gv 1,14, with section, paragraph, citation as printed, page (a paragraph before the first heading has no section) | 39 | 0.03 |
| `14-piu-citati-dal-dizionario.rq` | the 25 verses most cited by the dictionary (citations, entries; Is 53,12 first) | 25 | 17.34 |
| `15-voci-con-versetti-comuni.rq` | the entries sharing the most cited verses with AGNELLO DI DIO, and whether they are linked (the all-pairs form is in the file: about 2 minutes in rdflib) | 25 | 0.14 |
| `16-voce-e-note-bj.rq` | for the entry ABELE: its verses, the BJ notes commenting on them and those citing them | 16 | 1.58 |
| `17-dizionario-e-margini.rq` | pairs of verses a paragraph of AGNELLO DI DIO cites together that the BJ margins also link, with the margin references | 57 | 0.49 |
| `18-autori-e-libri.rq` | the 70 authors: citations in the entries they signed, books cited, the most cited book (Grelot: Salmi, 483) | 70 | 3.51 |
| `19-indice-note-di-un-versetto.rq` | the entries of the index of notes pointing to Gv 1,14, the note they send to and how it matches | 5 | 0.02 |
| `20-voce-indice-e-note.rq` | the entry ALLEANZA of the index of notes: sub-entries, references, the start of the notes they send to | 21 | 4.28 |
| `21-temi-pastorali-di-un-libro.rq` | the pastoral themes pointing to most verses of Tobia, with their sub-themes | 4 | 2.59 |
| `22-cronologia-esilio.rq` | the chronological table between 600 and 530 BC: printed date, years, column, text, references | 22 | 0.27 |
| `23-figli-di-erode.rq` | the children of Herod the Great with their mothers and spouses (`schema:`) | 5 | 0.02 |
| `24-refusi-degli-indici.rq` | the misprints of the indices with the corrected reference, why, and the note it sends to | 17 | 0.05 |
| `25-acrostici.rq` | the alphabetic poems by chapter: letters, the line where the Bet stanza begins, letters missing in the Hebrew text | 15 | 0.44 |
| `26-canone-greco.rq` | the deuterocanonical books of the Greek list and the books or chapters of this Bible they are | 9 | 0.01 |

## Size

`bj-dati.ttl.gz` 14.5 MB, `bj-dati.nt.gz` 26.7 MB (3,718,625 triples about 245,638
resources); `bj-ontologia.ttl` 2,046 triples, 230 `bj:` terms; `bj-forme.ttl` 43 node shapes.
Three VoID subsets: the Bible 2,439,195 triples (2,406,107 before this stage: +32,962), the
dictionary 1,120,756 (−1,093: passages now described first by the Bible's new links), the
front matter and appendices 158,674. Compared with the previous build, triple by triple
(both dumps sorted as rdflib N-Triples), 847 triples are gone, all from the 87 citations
the sense of the sentence reads again (their former passages, statuses, reasons and the
`bj:citaVersetto` of the wrong verses: 301 of a note, 1 of an introduction; 26 passages no
longer named; 6 margin references now partial or in the other Esther text), and 191,287 are
new: the 817 added citations and the corrected ones (84,395 triples about citations, with
their passages), the front matter and appendices, `bj:nellIndice` on 16,449 verse–entry
pairs, 187 acrostic letters and 339 `bj:LetteraAcrostica`.

The fixes of stage 6b (the audit of the front matter and the appendices) changed 271 triples of
that build: 250 new, 21 gone (the two dumps compared sorted). Gone: the bracketed acrostic names
(«(Mem)» … now «Mem», 10 literals), the «v.» of Šekina to «Presentazione (gesto di)» and of
Peccato to «Confessioni di Geremia» (6), the temi citation of «12,7» to Os 12,7 (3), the date of
chronology entry 423 («14–37»). New: the four citations of the table `AGGIUNTE` with their
passages and verses (Nm 11,25–26, Dt 27, Dt 31, Dt 5,22: 58 `bj:citaVersetto`), 25 chronology
dates read from the leading day-month forms (`bj:datazione`, `bj:annoInizio`, `bj:annoFine`,
`bj:circa`), the three «v.» of the table `RIMANDI` (`bj:vediVoce` and `skos:related` both ways),
Mt 12,7 in the index of the themes, the names without parentheses.

| Resources | | Triples by property (largest) | |
|---|---:|---|---:|
| `bj:Citazione` (BJ, dictionary, front matter and appendices) | 63,561 (28,122, 30,257, 5,182) | `rdf:type` | 247,038 |
| `bj:Passaggio` | 37,759 | `rdfs:label` | 234,875 |
| `bj:Versetto` | 35,762 | `dcterms:identifier` | 229,799 |
| `bj:Rimando` | 28,669 | `bj:comprende` | 196,221 |
| `bj:Margine` | 18,455 | `bj:testo` | 152,279 |
| `bj:CollegamentoVoce` | 18,207 | `bj:citaVersetto` | 140,121 |
| `bj:Nota`, `oa:TextualBody` | 10,762 each | `bj:voceCitaVersetto`, `bj:citatoNellaVoce` | 119,506 each |
| `bj:ParagrafoVoce` | 4,149 | `bj:stato` | 110,437 |
| `bj:Pericope` | 3,455 | `bj:aPassaggio` | 94,760 |
| `bj:SezioneVoce` | 3,022 | `prov:wasDerivedFrom`, `bj:pagina` | 86,478, 85,751 |
| `bj:Pagina` (+ 24 front-matter, 52 appendix pages) | 2,935 | `bj:rimandaA` | 83,956 |
| `bj:VoceIndice` (628 + 550 notes, 96 + 1,238 themes) | 2,512 | `bj:nellaVoce` | 55,635 |
| `bj:Capitolo` | 1,339 | `bj:commenta` | 38,939 |
| `bj:Voce` (`skos:Concept`), of which `bj:VoceRinvio` | 849, 519 | `bj:indicaVersetto`, `bj:nellIndice` | 16,449 each |
| `bj:PaginaDizionario` | 778 | `bj:paralleloA` | 14,926 |
| `bj:Paragrafo` (547 introductions, 78 front matter) | 625 | `bj:haNota`, `bj:richiamataDa` | 10,762 each |
| `bj:EventoCronologia` | 585 | `bj:daVoceIndice` | 4,957 |
| `bj:Divisione` | 452 | `bj:rinviaANotaChiave` | 4,663 |
| `bj:LetteraAcrostica` | 339 | `bj:indicaNota` | 3,646 |
| `bj:Abbreviazione`, `bj:Manoscritto` | 147, 56 | `bj:annoInizio`, `bj:annoFine` | 387 each |
| `foaf:Person` (70 + 2 of the dictionary, 5 of the edition) | 77 | `bj:vediVoce` | 247 |
| `bj:Libro`, `bj:Xilografia`, `bj:VoceCanone` | 74, 73, 59 | `bj:acrostico` | 339 |
| `bj:PersonaStorica` (`schema:Person`) | 34 | `schema:parent` (and `schema:children`), `schema:spouse` | 32, 24 |
| `bj:Introduzione`, `bj:SezioneCronologia`, `bj:TestoPreliminare`, `bj:GruppoCanone` | 21, 9, 7, 7 | `bj:doppioneDi`, `bj:citatoIn` | 1,848, 1,370 |
| `bj:Stampa`, `bj:Testamento`, `bj:Canone`, `bj:Indice` | 5, 2, 2, 2 | `bj:testoCorretto`, `bj:aPassaggioCorretto` | 16 each |
| `bj:Bibbia`, `bj:Dizionario`, `bj:Edizione`, `bj:TavolaCronologica`, `bj:TavolaGenealogica` | 1 each | `skos:altLabel` | 60 |

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
- Unresolved references (95 in the BJ, 93 in the dictionary, `query/12-irrisolti.rq`)
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
- Chronology: years only where the date is unambiguous (387 of 585 entries); the margin
  years are a scale of the print, kept as printed, not a date of the entry; names in small
  caps or capitals are strings, not persons; the dynasties are not linked to the index or
  the chronology. The calendar, the feasts, the measures and coins and the maps of the
  appendices are not in the graph.
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
