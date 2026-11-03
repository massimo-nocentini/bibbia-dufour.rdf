# The verse ontology of «La Bibbia di Gerusalemme», its RDF data and its offline explorer.
#
#   make                  the same as `make ontologia`
#   make ontologia        rebuild everything -> ontologia/ (about 18 minutes; stops at the first failed check)
#   make venv             the Python environment of requirements.txt -> vendor/venv
#   make prova PW=<dir>   the explorer in headless Chromium (playwright-core installed in <dir>; not part of
#                         `make ontologia`, see tools/ontologia/README.md, stage 4)
#
# The ontology is built from the LaTeX transcription, a repository of its own: the folder `corpus` next to
# this one (overleaf/corpus beside overleaf/bibbia-dufour.rdf), or BJ_CORPUS=<its folder>; the Dizionario di
# Teologia Biblica is ../dufour/corpus. Both are only read.

PYTHON ?= vendor/venv/bin/python

.DEFAULT_GOAL := ontologia
.PHONY: ontologia venv prova

ontologia:
	@$(PYTHON) -I tools/ontologia/costruisci.py

venv:
	python3 -m venv vendor/venv
	vendor/venv/bin/pip install -r requirements.txt

prova:
	@test -n "$(PW)" || { echo 'make prova PW=<folder where playwright-core is installed>'; exit 1; }
	node tools/ontologia/prova_esploratore.mjs --pw $(PW)
