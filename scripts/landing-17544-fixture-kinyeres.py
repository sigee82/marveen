#!/usr/bin/env python3
"""A 17544 MAI tarolt ertekeit allitja elo fixture-kent a lokalis probahoz.

FORRAS ES MIERT AZ: a tarolt (`_elementor_data`-beli) alakot NEM lehet az elo oldalrol
kiolvasni -- a WordPress `wptexturize` a megjeleniteskor atalakit (a tarolt " - "-bol
" – " lesz). A ma ervenyes tarolt ertek az elozo generalt szkript `uj` oszlopa: azt irta
be a 2026-09-17-i eles menet, es az elo DOM (ma megmerve, data-id szerint) mind a 17
mezoben ezzel egyezik, a texturizalt karaktereket leszamitva.
"""
import io, json, re, sys

REGI_PHP = '/Users/macmini/marveen/scripts/landing-szoveg-behelyettesites.php'
PAROSITAS = '/Users/macmini/marveen/scripts/landing-17544-parositas.json'
KI = '/Users/macmini/marveen/scripts/landing-17544-fixture.json'


def php_stringek(sor):
    """A generalt PHP sajat idezesenek inverze: \\' -> ' , \\\\ -> \\ ."""
    ki, i, akt, benn = [], 0, [], False
    while i < len(sor):
        c = sor[i]
        if not benn:
            if c == "'":
                benn, akt = True, []
            i += 1
            continue
        if c == '\\' and i + 1 < len(sor):
            akt.append(sor[i + 1]); i += 2; continue
        if c == "'":
            ki.append(''.join(akt)); benn = False; i += 1; continue
        akt.append(c); i += 1
    return ki


def main():
    php = io.open(REGI_PHP, encoding='utf-8').read()
    m = re.search(r'\$PAROK = array\((.*?)\n\);', php, re.S)
    if not m:
        raise SystemExit('HIBA: nem talalom a $PAROK tombot a regi generalt PHP-ban.')
    regi = {}
    for darab in re.findall(r'array\((.*?)\)(?=,\n|\n\))', m.group(1), re.S):
        s = php_stringek(darab)
        # sorrend: elem_id, <ertek>, ut, <ertek>, jelenlegi, <ertek>, uj, <ertek>
        d = {s[i]: s[i + 1] for i in range(0, len(s) - 1, 2)}
        if 'elem_id' in d and 'ut' in d and 'uj' in d:
            regi[(d['elem_id'], d['ut'])] = d['uj']

    parok = json.load(io.open(PAROSITAS, encoding='utf-8'))
    fixture, hianyzo = {}, []
    for p in parok:
        k = (p['elem_id'], p['ut'])
        if k not in regi:
            hianyzo.append(f"{k[0]} {k[1]}")
            continue
        fixture[f"{k[0]}|{k[1]}"] = regi[k]
    if hianyzo:
        raise SystemExit('HIBA: a regi generalt PHP nem hordozza: ' + ', '.join(hianyzo))

    # POZITIV KONTROLL: a kinyert ertek kezdodjon a MERT horgonnyal. Ha nem, akkor vagy a
    # parsolas romlott el, vagy az oldal azota elmozdult -- mindketto lelet, nem nulla.
    rossz = []
    for p in parok:
        v = fixture[f"{p['elem_id']}|{p['ut']}"]
        tiszta = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', v)).strip()
        if not tiszta.startswith(re.sub(r'\s+', ' ', p['horgony']).strip()):
            rossz.append(f"{p['elem_id']} {p['ut']}: '{tiszta[:60]}'")
    if rossz:
        raise SystemExit('HIBA -- a kinyert ertek nem a mert horgonnyal kezdodik:\n  - '
                         + '\n  - '.join(rossz))

    json.dump(fixture, io.open(KI, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'@@ {len(fixture)} mezo mai tarolt erteke -> {KI}')
    print('@@ mind a 17 a mert horgonnyal kezdodik (pozitiv kontroll rendben).')


if __name__ == '__main__':
    sys.exit(main())
