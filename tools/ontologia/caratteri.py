"""Rebuild the woff2 files of esploratore/font/ from the upstream Literata variable fonts.

The @fontsource subsets the explorer used before lack the small capitals (smcp, c2sc) and
the optical-size axis; this keeps them. Upstream (SIL Open Font License, release 3.103):
https://github.com/googlefonts/literata/tree/main/fonts/variable
  Literata[opsz,wght].ttf, Literata-Italic[opsz,wght].ttf

  python caratteri.py <dir with the two ttf files>

Needs fontTools and brotli (not in the project venv: pip install --target <dir> brotli and
put <dir> on PYTHONPATH). Each file of font.css gets exactly the unicode-range written there.
"""
import os
import re
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

QUI = os.path.dirname(os.path.abspath(__file__))
MODELLO = os.path.join(QUI, 'esploratore')
SORGENTI = {'normal': 'Literata[opsz,wght].ttf', 'italic': 'Literata-Italic[opsz,wght].ttf'}
# the features the page uses, and those the shaping needs
FUNZIONI = ['kern', 'mark', 'mkmk', 'ccmp', 'locl', 'rvrn', 'liga', 'case', 'smcp', 'c2sc',
            'onum', 'lnum', 'tnum', 'pnum', 'frac', 'sups', 'ordn']


def intervalli(testo):
    """'U+0000-00FF, U+0131' -> the code points."""
    cp = set()
    for parte in testo.split(','):
        a, _, b = parte.strip()[2:].partition('-')
        cp.update(range(int(a, 16), int(b or a, 16) + 1))
    return cp


def main(a):
    origine = a[0]
    css = open(os.path.join(MODELLO, 'font.css'), encoding='utf-8').read()
    facce = re.findall(r'font-family: "Literata"; font-style: (\w+);.*?@@FONT:([\w.-]+)@@.*?unicode-range: ([^;]+);', css, re.S)
    for stile, nome, gamma in facce:
        f = TTFont(os.path.join(origine, SORGENTI[stile]))
        o = subset.Options()
        o.flavor = 'woff2'
        o.layout_features = FUNZIONI
        o.name_IDs = ['*']
        o.notdef_outline = True
        s = subset.Subsetter(o)
        s.populate(unicodes=intervalli(gamma))
        s.subset(f)
        f.flavor = 'woff2'
        f.save(os.path.join(MODELLO, 'font', nome))
        print('%-40s %7d bytes' % (nome, os.path.getsize(os.path.join(MODELLO, 'font', nome))))


if __name__ == '__main__':
    main(sys.argv[1:])
