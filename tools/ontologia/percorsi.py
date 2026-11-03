"""Where the two repositories are: this one (the ontology, C) and the LaTeX transcription it reads (TEX).

TEX is $BJ_CORPUS, else the folder `corpus` next to this repository (overleaf/corpus beside
overleaf/bibbia-dufour.rdf). Read only: the proofread volumes progetti/<volume>/*.tex, data/manifest.json,
tools/progetti/progetti.py and verifica.py (the sections of each volume), progetti/appendici/tsv.py (the
tables of the appendices) and the images of the maps. The Dizionario di Teologia Biblica is ../dufour/corpus
next to both (dufour.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.abspath(os.environ.get('BJ_CORPUS') or os.path.join(os.path.dirname(C), 'corpus'))
if not os.path.isdir(os.path.join(TEX, 'progetti')):
    sys.exit('the LaTeX transcription is not at %s: set BJ_CORPUS to the folder of its repository' % TEX)
