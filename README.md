# bj-ontology

The verse ontology of «La Bibbia di Gerusalemme» (EDB: CEI 2008 text with the notes and marginal
cross-references of the Bible de Jérusalem): an RDF graph centred on the verse, its vocabulary and SHACL
shapes, the checks, example SPARQL queries, the time line of every dated event and an offline explorer
(one HTML page). It is built from the proofread LaTeX transcription of the volume, which is a repository of
its own, and from the research corpus of X. Léon-Dufour's *Dizionario di Teologia Biblica*.

| Path | Content |
|---|---|
| `ontologia/` | what is built: the vocabulary `bj-ontologia.ttl`, the shapes `bj-forme.ttl`, the data `bj-dati.ttl.gz` (and `bj-dati.nt.gz`, not tracked), `bj-void.ttl`, `bj-contesto.jsonld`, the queries `query/*.rq`, the explorer `esplora.html`; the model and how to query it in `ontologia/README.md` |
| `tools/ontologia/` | the code of every stage, its tests and hand tables, the explorer's sources; every stage in `tools/ontologia/README.md` |

## Where the sources are

The build only reads them:

- the LaTeX transcription (`progetti/<volume>/*.tex`, `data/manifest.json`, `tools/progetti/`,
  `progetti/appendici/tsv.py`, the images of the maps): the folder `corpus` next to this repository
  (`overleaf/corpus` beside `overleaf/bj-ontology`), or `BJ_CORPUS=<its folder>`
  (`tools/ontologia/percorsi.py`);
- the *Dizionario di Teologia Biblica*: `../dufour/corpus` (`tools/ontologia/dufour.py`).

The transcription's Tufte edition reads this repository in turn (its parsers `estrai.py`, `riferimenti.py`,
`virgolette.py`, `paratesto.py`, `canone.py`, and `ontologia/build/bibbia.json`, `collegamenti.json`): it
looks for it next to itself, as `../bj-ontology`, or at `BJ_ONTOLOGY=<its folder>`.

## Build

```sh
make venv          # once: vendor/venv with requirements.txt
make ontologia     # about 18 minutes; every check must pass
```

The browser test of the explorer needs playwright-core (see `tools/ontologia/README.md`, stage 4):
`make prova PW=<folder where it is installed>`.

## Licence

The text of the BJ (EDB) and of the dictionary (Marietti) is copyrighted: the data and the page hold it, so
this repository is for personal study and stays private.
