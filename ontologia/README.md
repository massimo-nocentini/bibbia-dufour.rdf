# La Bibbia di Gerusalemme as a semantic-web base

A verse-centred RDF graph of «La Bibbia di Gerusalemme» (EDB: CEI 2008 Italian text with
the notes and marginal cross-references of the Bible de Jérusalem), built from the 14
proofread LaTeX volumes in `progetti/`. Every verse is linked to the notes called from
it, the notes commenting on it, the references printed in its margin, and every citation
of it in a note or an introduction. The entries of X. Léon-Dufour's *Dizionario di
Teologia Biblica* (1976) are in the same graph: every verse is also linked to the entries
(and their sections and paragraphs) that cite it.

Both texts are copyrighted (EDB, Marietti): everything here is for local use only (see
*Licence* below for the dictionary). The IRIs live under
`https://massimo-nocentini.github.io/bibbia-gerusalemme/`, but nothing is published
there; they are names, not links to follow.

| File | What | Made by |
|---|---|---|
| `bj-ontologia.ttl` | OWL 2 vocabulary, prefix `bj:` (the dictionary in its last section) | hand-written |
| `bj-forme.ttl` | SHACL shapes for the data | hand-written |
| `query/*.rq` | 18 SPARQL examples (13–18 on the dictionary) | hand-written |
| `bj-dati.ttl.gz` | the data graph, Turtle: the Bible and the dictionary | `tools/ontologia/rdf.py` |
| `bj-dati.nt.gz` | the same triples, N-Triples (for bulk loaders) | `tools/ontologia/rdf.py` |
| `bj-contesto.jsonld` | JSON-LD context: `bj:` terms by local name, data prefixes (pages are `pag:`) | `tools/ontologia/rdf.py` |
| `bj-void.ttl` | VoID description of the data: title, rights, source, dumps, vocabularies, triples per class and per property, a subset for the Bible and one for the dictionary, two entry ↔ verse linksets | `tools/ontologia/rdf.py` |
| `build/bibbia.json`, `build/collegamenti.json` | intermediate JSON (stages 1 and 2) | `estrai.py`, `riferimenti.py` |
| `build/dufour.json` | the entries of the *Dizionario di Teologia Biblica* (Léon-Dufour, 1976; read from `../dufour/corpus`) and their 30,257 Bible citations resolved to verses | `dufour.py` |
| `build/query.md` | rows and timings of the example queries at the last build | `interroga.py` |
| `esplora.html` | the offline explorer: one page, data embedded (the Bible and the dictionary), opens from disk | `tools/ontologia/esploratore.py` |

`build/` (about 92 MB) is listed in `.gitignore`, like `bj-dati.nt` unpacked for a triple
store (about 750 MB): `make ontologia` rebuilds them. With the dictionary `bj-dati.nt.gz`
is 25.6 MB (17.6 MB before), over the 20 MB above which a regenerable file is not kept in
git, so it is listed in `.gitignore` too (an earlier commit tracks it: `git rm --cached
ontologia/bj-dati.nt.gz` stops that; `bj-dati.ttl.gz`, 13.9 MB, holds the same triples).
The other generated files are under 9 MB. The dumps and the page now also hold the
dictionary's text, which its own corpus calls private: see *Licence* before committing
them.

## Rebuild

```sh
make ontologia                                   # or:
vendor/venv/bin/python -I tools/ontologia/costruisci.py
```

The script runs every stage in order and stops at the first failed check: `estrai.py`
(LaTeX to JSON), `riferimenti.py` (references to typed links), `test_riferimenti.py`, `dufour.py` and `test_dufour.py` (the citations of the Dizionario di Teologia Biblica),
`rdf.py` (JSON to RDF and the VoID description), `verifica_rdf.py` (checks of the graph), `interroga.py` on
every query and `esploratore.py` (the explorer page). It takes about 11½ minutes; every generated file comes out byte-identical on every
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
from it), the overview counts them. The text is set in Literata and the interface in Inter, both embedded (SIL Open
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
for the work; `cito:isCitedBy` above `bj:citatoNellaVoce`. schema.org adds nothing here
that these do not say, so it is not used.
The ontology carries `vann:preferredNamespacePrefix "bj"`; the dataset is described in
VoID (`bj-void.ttl`: `void:Dataset` with title, rights, source, dumps, vocabularies,
`void:exampleResource`, and one class and property partition each, with counts).
Every `bj:` term has `rdfs:label` and `rdfs:comment` in Italian and English.

## Checks

`rdf.py` checks while building: every `bj:` term used is declared, object properties
have IRIs and datatype properties literals of their range, no IRI is dangling, the
counts equal the JSON (the dictionary's against `dufour.json`: 849 entries, 519
redirects, 3,022 sections, 4,149 paragraphs, 18,207 links, 30,257 citations, 72 people),
the passages of each link and citation hold exactly its targets; it writes
`bj-void.ttl` and parses it back (`void:triples` equal to the graph, and to the sum of the
two subsets).
`verifica_rdf.py` then checks the written files:

- rdflib's N-Triples and Turtle parsers and the fast reader of `grafo.py` give the same
  3,527,956 triples;
- OWL sanity: each `bj:` term is declared with one kind; all 2.6 million triples with a
  `bj:` property have subject and object of its `rdfs:domain` and `rdfs:range`;
- 43 SPARQL integrity queries on the whole graph, about 3 minutes (counts against the JSON, exactly one
  text and chapter per verse, `bj:precede` goes to order + 1, inverses and symmetric and
  subproperty closures complete, every shortcut edge backed by a printed reference or
  citation, resolved references have passages); 20 of them on the dictionary: its counts
  equal stage 2b (entries, redirects, sections, paragraphs, links and the 9 unresolved,
  citations by status 30,162 / 2 / 93, the 28,997 verses of its verse index), every verse
  a dictionary citation's passages include is a declared `bj:Versetto`, every link target is
  an entry and every target section belongs to it, sections and paragraphs lie in their
  entry, `bj:voceCitaVersetto` holds exactly the 119,506 (entry, verse) pairs of the JSON,
  each backed by a citation, `bj:citatoNellaVoce` is its exact inverse, the entry shortcuts
  are backed by a printed link and `skos:related` is symmetric;
- SHACL (`bj-forme.ttl`, pyshacl) on the **whole graph**: 25 node shapes (8 for the
  dictionary: work, people, pages, entries, redirects, sections, paragraphs, links; the
  citation shape also takes a dictionary paragraph or section title as citing entity),
  234,807 typed resources, about 4.5 minutes; it conforms;
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
| `09-matrice-libri.rq` | book × book matrix of margin references | 2372 | 3.66 |
| `10-pericope.rq` | the verses of the pericope holding Lc 15,11, with their note counts | 22 | 0.02 |
| `11-salmi-nel-nt.rq` | Psalms quoted in the NT, by NT book | 16 | 0.14 |
| `12-irrisolti.rq` | unresolved references with their reason (BJ 101, dictionary 93) | 194 | 0.17 |
| `13-voci-che-citano.rq` | the dictionary entries citing Gv 1,14, with section, paragraph, citation as printed, page (a paragraph before the first heading has no section) | 39 | 0.03 |
| `14-piu-citati-dal-dizionario.rq` | the 25 verses most cited by the dictionary (citations, entries; Is 53,12 first) | 25 | 17.34 |
| `15-voci-con-versetti-comuni.rq` | the entries sharing the most cited verses with AGNELLO DI DIO, and whether they are linked (the all-pairs form is in the file: about 2 minutes in rdflib) | 25 | 0.14 |
| `16-voce-e-note-bj.rq` | for the entry ABELE: its verses, the BJ notes commenting on them and those citing them | 16 | 1.58 |
| `17-dizionario-e-margini.rq` | pairs of verses a paragraph of AGNELLO DI DIO cites together that the BJ margins also link, with the margin references | 57 | 0.49 |
| `18-autori-e-libri.rq` | the 70 authors: citations in the entries they signed, books cited, the most cited book (Grelot: Salmi, 483) | 70 | 3.53 |

## Size

`bj-dati.ttl.gz` 13.9 MB, `bj-dati.nt.gz` 25.6 MB (3,527,956 triples about 234,807
resources; uncompressed N-Triples 747 MB); `bj-ontologia.ttl` 1,392 triples, 149 `bj:`
terms; `bj-forme.ttl` 25 node shapes. The dictionary added 1,121,849 triples (the VoID
subset `vp:dizionario`); the Bible's 2,406,107 are unchanged, triple for triple.

| Resources | | Triples by property (largest) | |
|---|---:|---|---:|
| `bj:Citazione` (BJ, dictionary) | 57,562 (27,305, 30,257) | `rdf:type` | 236,465 |
| `bj:Passaggio` | 36,931 | `rdfs:label` | 224,347 |
| `bj:Versetto` | 35,762 | `dcterms:identifier` | 220,331 |
| `bj:Rimando` | 28,669 | `bj:comprende` | 183,000 |
| `bj:Margine` | 18,455 | `bj:testo` | 145,144 |
| `bj:CollegamentoVoce` | 18,207 | `bj:citaVersetto` | 130,079 |
| `bj:Nota`, `oa:TextualBody` | 10,762 each | `bj:voceCitaVersetto`, `bj:citatoNellaVoce` | 119,506 each |
| `bj:ParagrafoVoce` | 4,149 | `bj:stato` | 104,438 |
| `bj:Pericope` | 3,455 | `bj:aPassaggio` | 88,350 |
| `bj:SezioneVoce` | 3,022 | `bj:rimandaA` | 83,952 |
| `bj:Pagina` | 2,935 | `prov:wasDerivedFrom`, `bj:pagina` | 78,180, 77,453 |
| `bj:Capitolo` | 1,339 | `bj:nellaVoce` | 55,635 |
| `bj:Voce` (`skos:Concept`), of which `bj:VoceRinvio` | 849, 519 | `bj:commenta` | 38,939 |
| `bj:PaginaDizionario` | 778 | `skos:related` | 19,222 |
| `bj:Paragrafo` | 547 | `bj:paralleloA` | 14,926 |
| `bj:Divisione` | 452 | `bj:haNota`, `bj:richiamataDa` | 10,762 each |
| `bj:Libro` | 74 | `bj:richiamaVoce`, `bj:vediAncheVoce`, `bj:rinviaAVoce` | 8,242, 4,646, 2,142 |
| `foaf:Person` | 72 | `bj:rinviaANotaChiave` | 4,663 |
| `bj:Introduzione` | 21 | `bj:doppioneDi`, `bj:citatoIn` | 1,848, 1,370 |
| `bj:Testamento`, `bj:Bibbia`, `bj:Dizionario` | 2, 1, 1 | `skos:altLabel` | 60 |

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
- Unresolved references (101 in the BJ, 93 in the dictionary, `query/12-irrisolti.rq`)
  are kept with their reason and no passage; misprints are never corrected in the BJ
  (in the dictionary a few are, by hand and with their reason in `bj:conversione`).
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
