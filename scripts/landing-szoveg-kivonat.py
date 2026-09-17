#!/usr/bin/env python3
"""A Copy-doksibol kivonja a KIMENO szoveget mezokre bontva, es parositas-sablont ir.

MIERT KULON LEPES: a behelyettesito szkriptnek elem-ID -> szoveg parokra van szuksege.
A doksi 9 BLOKKBAN, 18 MEZO-CIMKEVEL adja a szoveget ("## N. szekcio" + "**Heading:**" stb.),
a prod oldalon viszont 30 szoveges mezo all. A kulonbseg NEM hiba: a sablon allando reszeit
(CTA-gombok, "Miert eppen 7 nap?", VIP Klub leiras) a skill szerint NEM irjuk ujra.
Ezert a parositas EMBER dontese, es ez a szkript csak a SABLONT allitja elo hozza.

A hatart a ket EGYEDI jelolo adja, NEM sorszam: a doksi jegyzet-resze naponta tobbszor valtozik,
es egy sorszam-horgony NEMAN vagna le egy bekezdest vagy huzna be egy jegyzetet.
"""
import json
import re
import sys

DOKSI = '/Users/macmini/marveen/agents/copy/munka/2026-10-ingyenes-kihivas-landing-szoveg.md'
NYITO = '=== BEMENO-SZOVEG-KEZDETE ==='
ZARO = '=== BEMENO-SZOVEG-VEGE ==='
VART_HOSSZ = 6380  # Copy merte es a doksi fejleceben is all; a NYERS szakasz hossza


def kimeno_szakasz(szoveg):
    """A ket jelolo kozotti resz. Mindkettonek PONTOSAN egyszer kell szerepelnie."""
    for jelolo in (NYITO, ZARO):
        db = szoveg.count(jelolo)
        if db != 1:
            sys.exit(f'HIBA: a(z) "{jelolo}" jelolo {db}-szer szerepel, pontosan 1-et vartam. '
                     'Ne talalgassunk a hatarral -- szolj Copynak.')
    return szoveg[szoveg.index(NYITO) + len(NYITO):szoveg.index(ZARO)]


# A doksi KETFELE alakban irja a mezoket, es ez nem stilus-kerdes:
#   (A) a cimke ONALLO sorban all, a szoveg alatta  -- "**Heading:**\n Indul a ..."
#   (B) a cimke ES a szoveg EGY sorban             -- "**Heading:** A kihivas menete"
# Az elso valtozat csak az (A) alakot ismerte, es a (B)-t NEMAN eldobta: a 7-10. blokk
# HET mezoje egyszeruen hianyzott a kimenetbol, a darabszam meg 18-at mondott. Hogy a blokk
# [VALTOZATLAN], az szerencse volt, nem vedelem -- ha egy CSERELENDO mezo irodik igy, eltunik.
MEZO_MINTA = re.compile(r'^\*\*(.+?):\*\*[ \t]*(.*)$', re.M)


def mezokre_bont(szakasz):
    """[(blokk_cim, mezo_cimke, szoveg, alak)] a "## ..." blokkok es a mezo-cimkek menten."""
    blokkok = []
    hatarok = [m.start() for m in re.finditer(r'^## ', szakasz, re.M)] + [len(szakasz)]
    for i in range(len(hatarok) - 1):
        resz = szakasz[hatarok[i]:hatarok[i + 1]]
        cim = resz.splitlines()[0].lstrip('# ').strip()
        talalatok = list(MEZO_MINTA.finditer(resz))
        for j, m in enumerate(talalatok):
            cimke = m.group(1)
            soron_belul = m.group(2).strip()
            veg = talalatok[j + 1].start() if j + 1 < len(talalatok) else len(resz)
            if soron_belul:
                torzs, alak = soron_belul, 'egy-soros'
            else:
                torzs = resz[m.end():veg].strip().rstrip('-').strip()
                alak = 'cimke-alatt'
            if torzs:
                blokkok.append((cim, cimke, torzs, alak))
    return blokkok


def main():
    szoveg = open(DOKSI, encoding='utf-8').read()
    szakasz = kimeno_szakasz(szoveg)
    print(f'@@ kimeno szakasz: {len(szakasz)} karakter (vart: {VART_HOSSZ})')
    if len(szakasz) != VART_HOSSZ:
        print('@@ FIGYELEM: a hossz ELTER a vart ertektol. Copy valtoztatott -- '
              'ellenorizd, mielott barmit kikuldesz.')
    mezok = mezokre_bont(szakasz)
    alakok = {}
    for _, _, _, alak in mezok:
        alakok[alak] = alakok.get(alak, 0) + 1
    print(f'@@ blokk: {len(set(b for b, _, _, _ in mezok))}   mezo: {len(mezok)}'
          f'   (alak szerint: {alakok})')
    print('@@ (a prod oldalon 42 elem van: 30 kozonseges + 12 ikonlista-tetel -- Copy merese '
          'mind az ot landingen)')
    print('@@')
    # Az IKONOS LISTA a doksiban EGY mezo, a prod oldalon viszont ANNYI elem, ahany
    # tetele van (`icon_list.0.text`, `icon_list.1.text`, ...). Ha egyben hagynank, a
    # nyolc sor EGY parba menne, es a masik het tetel a REGI (meal prep) szoveget tartana
    # meg az uj landingen -- ezt Copy merte vissza mind az ot landingen: az "osszes elem
    # minusz icon-list tetel" MINDENHOL pontosan 30, tehat a rejtozes rendszeres.
    # Ezert tetelekre bontjuk, hogy a parositas 1:1 legyen.
    bontott = []
    for blokk, cimke, torzs, alak in mezok:
        if cimke and 'konos lista' in cimke:
            tetelek = [t.strip().rstrip(',') for t in torzs.split('\n') if t.strip()]
            for i, tetel in enumerate(tetelek):
                bontott.append((blokk, f'{cimke} / {i + 1}. tetel', tetel, alak))
        else:
            bontott.append((blokk, cimke, torzs, alak))
    print(f'@@ lista-bontas utan: {len(bontott)} sor  (a doksi {len(mezok)} mezojebol; '
          f'a ket ikonos lista 2 mezobol {len(bontott) - len(mezok) + 2} tetelre bomlott)')
    print('@@ EZ A SZAM ALL SZEMBEN a prod 42 elemevel -- ha nem egyezik, a parositas elott '
          'tisztazni kell, melyik oldal rejt el valamit.')
    mezok = bontott

    sablon = []
    for idx, (blokk, cimke, torzs, alak) in enumerate(mezok, 1):
        elso = torzs.splitlines()[0]
        print(f'@@ [{idx:2d}] {blokk[:44]:44s} | {str(cimke)[:26]:26s} | {elso[:48]}')
        # A doksi HAROM helyen jeloli, mi marad, es az elso valtozat csak az elsot ismerte:
        #  (a) a mezo ERTEKE maga "[VALTOZATLAN]"            -- ezt ismerte
        #  (b) a BLOKK cimeben all "[VALTOZATLAN]"           -- az egesz blokk marad
        #  (c) a jeloles egy VALODI mondat VEGEN all         -- Copy megjegyzese, NEM tartalom
        # A (c) volt a sulyos: a jeloles BENNE MARADT a cserelendo szovegben, tehat a
        # "[VALTOZATLAN]" szo SZO SZERINT kikerult volna az elo landingre, a VIP Klub
        # mondat vegere. A (b) pedig a "kihivas menete" blokk het mezojet tette volna
        # cserelendove, pedig Copy az EGESZ blokkot valtozatlannak jelolte.
        # KIVETEL a (b)-nel: ha a jeloles utan MEG VAN valami ("[VALTOZATLAN, egy temaszo
        # cserelve...]"), akkor a blokk NEM valtozatlan -- eppen azt mondja, mi valtozott.
        # A SORREND SZAMIT, ES EZT MEGJARTAM: eloszor a jelolest LEVAGTAM, es csak UTANA
        # kerdeztem meg, hogy "valtozatlan-e". Egy gomb erteke PONTOSAN "[VALTOZATLAN]",
        # tehat a vagas utan URES lett, az ures nem kezdodik a jelolessel -> mind a HAT
        # CTA-gomb CSERELENDOVE valt, URES uj szoveggel. Az elo landingen ez hat URES
        # gombot jelentett volna. Eloszor dontunk, aztan vagunk.
        blokk_valtozatlan = bool(re.search(r'\[VÁLTOZATLAN\]\s*$', blokk))
        csak_jeloles = torzs.strip().upper().startswith('[VÁLTOZATLAN')
        valtozatlan = blokk_valtozatlan or csak_jeloles
        if not csak_jeloles:
            # Copy megjegyzese egy VALODI mondat vegen -- ez sosem tartalom.
            torzs = re.sub(r'\s*\[VÁLTOZATLAN\]\s*$', '', torzs).strip()
        sablon.append({
            'cserelendo': not valtozatlan,
            'sorszam': idx,
            'blokk': blokk,
            'mezo_cimke': cimke,
            'doksi_alak': alak,
            'elem_id': '',      # <- EZT KELL KITOLTENI a prod meres elem-ID-ibol
            'elem_mezo': '',    # <- title | editor | text
            'uj_szoveg': torzs,
        })
    ki = '/Users/macmini/marveen/scripts/landing-szoveg-parositas.json'
    with open(ki, 'w', encoding='utf-8') as f:
        json.dump(sablon, f, ensure_ascii=False, indent=1)
    print(f'@@\n@@ parositas-sablon kiirva: {ki}')
    cserelendo = sum(1 for x in sablon if x['cserelendo'])
    print(f'@@ ebbol CSERELENDO: {cserelendo}   valtozatlannak jelolt: {len(sablon) - cserelendo}')
    print('@@ A kitoltendo mezok: elem_id, elem_mezo. Ures elem_id = NEM cserelunk.')


if __name__ == '__main__':
    main()
