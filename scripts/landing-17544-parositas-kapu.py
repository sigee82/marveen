#!/usr/bin/env python3
"""A GENERALT PAROSITAS ellenorzese Copy forras-fajlja ellen.

MIERT LETEZIK: "Copy jol irta le" es "a szkript ezt fogja beirni" KET KULON ALLITAS.
Az elsot a szoveg gazdaja meri a forrason; ezt a masodikat senki mas nem meri.

>>> MIERT NEM LISTAZZA TOBBE A VART ALAKOKAT (2026-09-21, Nova fogta meg): <<<
Az elso valtozat egy kezzel felvett `CSEREK` tablat hordozott a het reggeli csere vart
mondataival. Delutan Eszter hang-kifogasa nyoman Copy atirt ot blokkot -- es a kapu
HAROM HIBAT jelentett azokra a mezokre, amiket epp jol irtak at. A kapu a DELELOTTI
vilagot varta.
Ez ugyanaz az alak, amit reggel a generatorbol mar kivettunk: egy kezi tabla, amit a
sajat sikeres deployunk avit el. Egy kapu, ami a vart alakot BEIRVA hordozza, pontosan
addig ervenyes, amig a szoveg nem valtozik -- vagyis addig, amig nincs ra szukseg.
Ezert a vart alak mostantol a FORRASBOL jon, es a kapu nem SZAMOKAT allit, hanem
LEFEDETTSEGET: minden forras-sor pontosan egyszer, minden parositas-ertek maradek nelkul.

AMIT MER:
  1. LEFEDETTSEG ODA: minden tartalmi sor Copy fajljabol megjelenik a parositasban.
  2. LEFEDETTSEG VISSZA: minden parositas-ertek maradek nelkul felbomlik forras-sorokra
     (nincs kitalalt szoveg, nincs duplikalas).
  3. ALLANDO SZABALYOK (ezek nem korfuggok): nagykotojel 0, nagybetus "Neked" 0,
     elettani szokincs 0, "allitottam ossze" 0.
  4. MI VALTOZIK: nem beirt lista, hanem a mert elo allapottal osszevetve SZAMOLVA.

A 2. pont a lenyeg, es szandekosan NEM a generator fuggvenyeivel bomlik: ha ugyanazzal a
parserrel ellenorizne, tautologia lenne. Sajat, buta sor-illesztes fut.

FUTTATAS:  python3 scripts/landing-17544-parositas-kapu.py
Kilepesi kod: 0 = rendben, 1 = lelet, 2 = a meres maga nem futott le.
"""
import io, json, os, re, sys

PAROSITAS = '/Users/macmini/marveen/scripts/landing-17544-parositas.json'
ELO = '/Users/macmini/marveen/scripts/landing-17544-elo-allapot.json'

# Elettani/orvosi mechanizmus-szokincs, SZOTOKENT. A korpusz ot landingjen MIND NULLA
# (ujramerve 2026-09-21: a lenti tizenketto egyike sem fordul elo benne).
#
# MIERT SZOTO ES NEM TELJES SZO (2026-09-21, az elo lap fogta meg a kaput, nem forditva):
# a lap "vércukrodat"-ot ir, es a magyar ragozas KIEJTI a tovegi o-t -- a "vércukor" tehat
# NEM reszsztringje. Mind a nyolc regi minta NULLAT adott egy olyan szovegen, amiben ket
# elettani fordulat all ("vércukrodat", "IR-barátok"). A nulla nem lelet volt, hanem vaksag.
ORVOSI = ['vércuk', 'inzulin', 'hormon', 'anyagcser', 'glikém', 'ketóz', 'gyullad',
          'immunrendszer', 'IR-barát', 'rezisztenc', 'glükóz', 'ketogén']


def norm(s):
    return re.sub(r'\s+', ' ', s.replace(' ', ' ')).strip()


def tagtalan(s):
    s = re.sub(r'<(/p|/li|br\s*/?|/h[1-6])\s*>', ' ', s, flags=re.I)
    return norm(re.sub(r'<[^>]+>', '', s))


def forras_sorok(ut):
    """Copy fajljanak TARTALMI sorai. A '#' kommentek es a '##'/'###' fejlecek nem azok."""
    ki = []
    for sor in io.open(ut, encoding='utf-8'):
        t = sor.strip()
        if not t or t.startswith('#'):
            continue
        ki.append(norm(t))
    return ki


def bomlik(ertek, keszlet):
    """Az erteket balrol jobbra forras-sorokra bontja. Visszaadja a felhasznalt sorokat
    es a maradekot. Nem regexpel: a leghosszabb illeszkedo sort veszi elore, hogy egy
    rovid sor ne harapjon bele egy hosszabba."""
    maradek, hasznalt = ertek, []
    while maradek:
        jelolt = [s for s in keszlet if maradek.startswith(s)]
        if not jelolt:
            return hasznalt, maradek
        leghosszabb = max(jelolt, key=len)
        hasznalt.append(leghosszabb)
        maradek = maradek[len(leghosszabb):].strip()
    return hasznalt, ''


def main():
    if not os.path.exists(PAROSITAS):
        print(f'VAK MERES: nincs parositas: {PAROSITAS}'); return 2
    d = json.load(io.open(PAROSITAS, encoding='utf-8'))
    if 'parok' not in d or 'forras' not in d:
        print('VAK MERES: a parositas regi alaku (nincs `forras` ujjlenyomata). '
              'Futtasd ujra a generatort.'); return 2
    parok, forras = d['parok'], d['forras']
    if not os.path.exists(forras['ut']):
        print(f"VAK MERES: nincs meg a forras: {forras['ut']}"); return 2

    import hashlib
    mai = hashlib.md5(io.open(forras['ut'], 'rb').read()).hexdigest()
    print(f"FORRAS : {os.path.basename(forras['ut'])}")
    print(f"  a parositas ezzel keszult: md5={forras['md5']}  ({forras['mtime']})")
    print(f"  a fajl MOST:               md5={mai}")
    if mai != forras['md5']:
        print()
        print('>>> A FORRAS AZOTA MEGVALTOZOTT, hogy ez a parositas keszult.')
        print('    A kapu tovabbmegy, de a MOSTANI forrashoz mer -- vagyis a lenti')
        print('    leletek egy resze nem hiba, hanem egy ujabb kor, ami meg nincs')
        print('    generalva. ELOSZOR FUTTASD UJRA A GENERATORT.')
        return 2
    print()

    sorok = forras_sorok(forras['ut'])
    keszlet = set(sorok)
    leletek = []
    felhasznalt = []

    for p in parok:
        kulcs = f"{p['elem_id']}|{p['ut']}"
        ertek = tagtalan(p['uj'])
        hasznalt, maradek = bomlik(ertek, keszlet)
        if maradek:
            leletek.append(f'NEM FORRASBOL VALO SZOVEG [{kulcs}]: a bontas megallt itt -> '
                           f'"{maradek[:90]}"')
        felhasznalt.extend(hasznalt)

    tobbszor = sorted({s for s in felhasznalt if felhasznalt.count(s) > 1})
    for s in tobbszor:
        leletek.append(f'TOBBSZOR FELHASZNALT FORRAS-SOR ({felhasznalt.count(s)}x): "{s[:80]}"')
    kimaradt = [s for s in sorok if s not in felhasznalt]
    for s in kimaradt:
        leletek.append(f'FORRAS-SOR, AMI SEHOL NEM JELENIK MEG: "{s[:90]}"')

    # 3. allando szabalyok
    egyben = '\n'.join(tagtalan(p['uj']) for p in parok)
    szabalyok = [('nagykotojel', r'[–—]'),
                 ('nagybetus "Neked"', r'\bNeked\b'),
                 ('elettani szokincs', '|'.join(ORVOSI)),
                 ("'allitottam ossze'", 'állítottam össze')]
    for nev, minta in szabalyok:
        n = len(re.findall(minta, egyben))
        print(f'  {"OK  " if n == 0 else "!!  "}{nev}: {n}')
        if n:
            leletek.append(f'ALLANDO SZABALY SERUL: {nev} ({n} talalat)')

    # POZITIV KONTROLL A DETEKTOROKRA: negy nulla ugyanugy nez ki, mint negy vak minta.
    # A PROBASZOVEG RAGOZOTT alakot hasznal: a regi, teljes szavas lista EZEN BUKOTT
    # meg 2026-09-21-en az elo lapon.
    proba = 'ez egy – teszt, ahol Neked szol, es a vércukrodat is emliti, meg állítottam össze'
    fog = sum(1 for _, m in szabalyok if re.search(m, proba))
    if fog != len(szabalyok):
        print(f'  !! POZITIV KONTROLL BUKOTT: {len(szabalyok)}-bol {fog} minta fogott.')
        print('     A fenti nullak ezert NEM leletek, hanem romlott meres.')
        return 2
    print(f'  (pozitiv kontroll: mind a {len(szabalyok)} minta fog a probaszovegen)')
    print()

    # 4. mi valtozik -- SZAMOLVA, nem beirva
    elo = json.load(io.open(ELO, encoding='utf-8'))['mezok']
    valtozik = []
    for p in parok:
        kulcs = f"{p['elem_id']}|{p['ut']}"
        m = elo.get(kulcs)
        if m is None:
            leletek.append(f'NINCS MERT ELO ERTEK: {kulcs}')
            continue
        if tagtalan(p['uj']) != norm(m['szoveg']):
            valtozik.append(kulcs)
    print(f'VALTOZIK ({len(valtozik)}/{len(parok)} mezo), az elo allapothoz merve:')
    for k in valtozik:
        print(f'  - {k}')
    print()

    print(f'LEFEDETTSEG: {len(sorok)} forras-sor, {len(parok)} parositas-mezo, '
          f'{len(kimaradt)} kimaradt sor, {len(tobbszor)} tobbszor hasznalt.')
    if not leletek:
        print()
        print('>>> NINCS LELET. A parositas pontosan a forrast hordozza.')
        print('>>> ES AMIT EZ NEM MOND: hogy a SZOVEG jo. Azt a szoveg gazdaja donti el.')
        return 0
    print()
    print(f'>>> {len(leletek)} LELET:')
    for x in leletek:
        print(f'  - {x}')
    return 1


if __name__ == '__main__':
    sys.exit(main())
