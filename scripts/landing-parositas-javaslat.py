#!/usr/bin/env python3
"""Parositas-JAVASLAT: a doksi 42 sora es a prod 42 mezoje egymas melle.

A sorrend mindket oldalon a megjelenes sorrendje, tehat a javaslat sorban parositja
oket -- DE a tipust ELLENORZI (heading<->Heading, editor<->Text-editor, button<->Gomb,
icon_list.N.text<->N. tetel). Ahol a tipus nem stimmel, ott KIIRJA, es nem hallgatja el:
egy elcsuszott par a rossz helyre teszi a szoveget, es az csak bongeszobol latszik.

A vegso szot COPY mondja ki. Ez JAVASLAT, nem dontes.
"""
import json
import re
import sys

MERES = '/Users/macmini/marveen/tervek/landing-rotacio-meres-2026-09-17.txt'
SABLON = '/Users/macmini/marveen/scripts/landing-szoveg-parositas.json'
KI = '/Users/macmini/marveen/tervek/landing-parositas-javaslat.txt'

SOR = re.compile(r'^@@\s+\[([0-9a-f]+)\s*\]\s+(\S+)\s+(\S+)\s+(.*)$')


def prod_mezok():
    mezok, benne = [], False
    for sor in open(MERES, encoding='utf-8'):
        if '=== 2.' in sor:
            benne = True
            continue
        if benne and 'OSSZESEN' in sor:
            break
        if benne:
            m = SOR.match(sor.rstrip('\n'))
            if m:
                mezok.append({'elem_id': m.group(1), 'widget': m.group(2),
                              'ut': m.group(3), 'jelenlegi': m.group(4).strip()})
    return mezok


def vart_tipus(cimke):
    """A doksi cimkejebol melyik prod-mezo-utat varjuk."""
    c = (cimke or '').lower()
    if 'ikonos lista' in c:
        return 'icon_list'
    if c.startswith('heading') or 'heading' in c:
        return 'title'
    if c.startswith('gomb'):
        return 'text'
    if 'text-editor' in c or c.startswith('text'):
        return 'editor'
    return '?'


def main():
    prod = prod_mezok()
    doksi = json.load(open(SABLON, encoding='utf-8'))
    print(f'@@ prod mezo: {len(prod)}   doksi sor: {len(doksi)}')
    if len(prod) != len(doksi):
        print('@@ !! A KET SZAM NEM EGYEZIK. A parositas ELOTT tisztazni kell, melyik oldal '
              'rejt el valamit -- ez ma mar ketszer elofordult, mindket oldalon.')
        sys.exit(1)

    sorok, eltero = [], 0
    for d, p in zip(doksi, prod):
        vart = vart_tipus(d['mezo_cimke'])
        tenyleges = 'icon_list' if p['ut'].startswith('icon_list') else p['ut']
        ok = (vart == tenyleges)
        if not ok:
            eltero += 1
        d['elem_id'] = p['elem_id']
        d['elem_mezo'] = p['ut']
        sorok.append((d, p, ok))

    with open(KI, 'w', encoding='utf-8') as f:
        def ir(s=''):
            print(s)
            f.write(s + '\n')
        ir('PAROSITAS-JAVASLAT -- a vegso szot COPY mondja ki.')
        ir(f'A doksi {len(doksi)} sora es a prod {len(prod)} mezoje, megjelenesi sorrendben.')
        ir(f'Tipus-elteres: {eltero} (0 a jo).')
        ir('A "MARAD" sorokat a doksi jeloli [VALTOZATLAN]-kent -- azokat NEM irjuk felul.')
        ir('')
        for d, p, ok in sorok:
            jel = '   ' if ok else '!! '
            allapot = 'CSERE ' if d['cserelendo'] else 'MARAD '
            ir(f'{jel}{allapot}[{p["elem_id"]:8s}] {p["ut"]:18s} ({p["widget"]})')
            ir(f'        MOST: {p["jelenlegi"][:88]}')
            if d['cserelendo']:
                ir(f'        UJ  : {d["uj_szoveg"][:88]}')
            ir(f'        doksi: {d["blokk"][:60]} | {d["mezo_cimke"]}')
            ir('')
    json.dump(doksi, open(SABLON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'@@ kiirva: {KI}')
    print(f'@@ a sablon kitoltve elem_id/elem_mezo ertekekkel: {SABLON}')


if __name__ == '__main__':
    main()
