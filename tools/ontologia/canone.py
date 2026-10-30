"""The books of the Bibbia di Gerusalemme: corpus ids, OSIS codes and CEI sigla.

LIBRI lists the 74 book sections of the volume in canonical (printed) order as
(corpus id, OSIS code, CEI siglum). The corpus ids are those of
tools/progetti/progetti.py; the CEI siglum is the one used in the margins and
in the notes. Esther is printed twice: the Greek text with its lettered
additions (Est-gr, OSIS EsthGr) and the Hebrew text (Est-ebr, OSIS Esth); both
answer to the siglum "Est". Psalms keep the Hebrew numbering of the CEI, Baruch
includes the Letter of Jeremiah as chapter 6, Daniel includes the Greek parts
(3,24-90; 13; 14) and Sirach has a translator's prologue (chapter "Prol").
"""

LIBRI = [
    ('Gen', 'Gen', 'Gen'), ('Es', 'Exod', 'Es'), ('Lv', 'Lev', 'Lv'), ('Nm', 'Num', 'Nm'),
    ('Dt', 'Deut', 'Dt'), ('Gs', 'Josh', 'Gs'), ('Gdc', 'Judg', 'Gdc'), ('Rt', 'Ruth', 'Rt'),
    ('1Sam', '1Sam', '1Sam'), ('2Sam', '2Sam', '2Sam'), ('1Re', '1Kgs', '1Re'),
    ('2Re', '2Kgs', '2Re'), ('1Cr', '1Chr', '1Cr'), ('2Cr', '2Chr', '2Cr'),
    ('Esd', 'Ezra', 'Esd'), ('Ne', 'Neh', 'Ne'), ('Tb', 'Tob', 'Tb'), ('Gdt', 'Jdt', 'Gdt'),
    ('Est-gr', 'EsthGr', 'Est'), ('Est-ebr', 'Esth', 'Est'),
    ('1Mac', '1Macc', '1Mac'), ('2Mac', '2Macc', '2Mac'), ('Gb', 'Job', 'Gb'),
    ('Sal', 'Ps', 'Sal'), ('Pr', 'Prov', 'Pr'), ('Qo', 'Eccl', 'Qo'), ('Ct', 'Song', 'Ct'),
    ('Sap', 'Wis', 'Sap'), ('Sir', 'Sir', 'Sir'), ('Is', 'Isa', 'Is'), ('Ger', 'Jer', 'Ger'),
    ('Lam', 'Lam', 'Lam'), ('Bar', 'Bar', 'Bar'), ('Ez', 'Ezek', 'Ez'), ('Dn', 'Dan', 'Dn'),
    ('Os', 'Hos', 'Os'), ('Gl', 'Joel', 'Gl'), ('Am', 'Amos', 'Am'), ('Abd', 'Obad', 'Abd'),
    ('Gn', 'Jonah', 'Gn'), ('Mi', 'Mic', 'Mi'), ('Na', 'Nah', 'Na'), ('Ab', 'Hab', 'Ab'),
    ('Sof', 'Zeph', 'Sof'), ('Ag', 'Hag', 'Ag'), ('Zc', 'Zech', 'Zc'), ('Ml', 'Mal', 'Ml'),
    ('Mt', 'Matt', 'Mt'), ('Mc', 'Mark', 'Mc'), ('Lc', 'Luke', 'Lc'), ('Gv', 'John', 'Gv'),
    ('At', 'Acts', 'At'), ('Rm', 'Rom', 'Rm'), ('1Cor', '1Cor', '1Cor'), ('2Cor', '2Cor', '2Cor'),
    ('Gal', 'Gal', 'Gal'), ('Ef', 'Eph', 'Ef'), ('Fil', 'Phil', 'Fil'), ('Col', 'Col', 'Col'),
    ('1Ts', '1Thess', '1Ts'), ('2Ts', '2Thess', '2Ts'), ('1Tm', '1Tim', '1Tm'),
    ('2Tm', '2Tim', '2Tm'), ('Tt', 'Titus', 'Tt'), ('Fm', 'Phlm', 'Fm'), ('Eb', 'Heb', 'Eb'),
    ('Gc', 'Jas', 'Gc'), ('1Pt', '1Pet', '1Pt'), ('2Pt', '2Pet', '2Pt'), ('1Gv', '1John', '1Gv'),
    ('2Gv', '2John', '2Gv'), ('3Gv', '3John', '3Gv'), ('Gd', 'Jude', 'Gd'), ('Ap', 'Rev', 'Ap'),
]

PRIMO_NT = 'Mt'

OSIS = {sid: osis for sid, osis, _ in LIBRI}
SIGLA = {sid: sigla for sid, _, sigla in LIBRI}
ORDINE = {sid: i + 1 for i, (sid, _, _) in enumerate(LIBRI)}

# chapter label of Sirach's prologue in verse ids (Sir.Prol.1); its chapter number is 0
PROLOGO = 'Prol'


def testamento(sid):
    return 'NT' if ORDINE[sid] >= ORDINE[PRIMO_NT] else 'AT'


def verse_id(osis, cap, label):
    """Gen.1.1, EsthGr.1.1a, Sir.Prol.3 (cap 0 = Sirach's prologue)."""
    return '%s.%s.%s' % (osis, PROLOGO if cap == 0 else cap, label)


def numeric_order(group):
    """The verses sharing one chapter and number (dicts with 'suffix'), given in print
    order, in numeric order: the lettered ones by letter (Isa 10,18b is printed before
    18a, Sir 28,24a-25b and Isa 7,8a-9b are interleaved), the unlettered one where it is
    printed with respect to them (Greek Esther 1,1a-r come before 1,1, 4,17a-z after
    4,17)."""
    lettered = sorted((v for v in group if v['suffix']), key=lambda v: v['suffix'])
    bare = [v for v in group if not v['suffix']]
    if not bare or not lettered:
        return bare + lettered
    first_letter = min(group.index(v) for v in lettered)
    return bare + lettered if group.index(bare[0]) < first_letter else lettered + bare
