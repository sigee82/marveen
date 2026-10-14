#!/usr/bin/env python3
"""Eszter JOVAHAGYASI DOKSIJABOL (Google Doc, markdown-exportkent) a havi landing-generator bemenete.

MIERT (2026-10-14, Nessa 20531 / Nova 20532): a jovahagyott szoveg NEM Copy fajljaban el, hanem Eszter
doksijaban -- a ket valtozat 15:12 utan szetvalt (a doksiban mar "konnyebben elaludj", a fajlban meg
"jojjon az alom"). A generator Copy jelolt formatumat ([MARAD]/[CSERE], BEMENO-jelolok) varja; ez a
szkript a doksibol allitja elo UGYANAZT a formatumot, es a doksi 4. pontjabol a kurzus-leiras fajlt.

A JELOLES NEM A DOKSIBOL JON (abban nincs), hanem RÖGZITETT SZABALYBOL, mert a sablon allando:
  MARAD = a hat gomb, az allando cimek (3. "Miert eppen 7 nap?", 4. "Mire szamithatsz?", 6. "Imadni fogod...",
          11. nyeremeny-cim) es a teljes 7-10. szekcio;  minden mas CSERE.
Igy a generator pozitiv kontrollja (a MARAD mezok betura egyeznek az elo oldallal) a doksi-forrasnal is el:
ha a doksi szerkezete elcsuszik, a generator megall.

FUTTATAS:
  python3 scripts/landing-doksi-atalakito.py <doksi.md> <landing-ki.md> <leiras-ki.md>
A doksit a Drive-bol markdownkent kell letolteni (Docs export text/markdown), es a revizio-ID-t megjegyezni.
"""
import hashlib, io, re, sys

MARAD_CIMEK = {'3', '4', '6', '11'}          # ezekben a szekciokban a Heading allando


def unesc(s):
    """A Docs markdown-export escape-jei (\\. \\! \\- \\+ \\_ https\\:) es a felkover ** jelek a cimkeken kivul."""
    return re.sub(r'\\([\\`*_{}\[\]()#+\-.!:|>~])', r'\1', s)


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    nyers = io.open(sys.argv[1], encoding='utf-8').read()
    sorok = [unesc(s.rstrip()) for s in nyers.split('\n')]

    # --- a landing-resz: az "1. szekcio" fejlectol a "2. Hirlevel" fejlecig
    def fejlec(s):
        return re.sub(r'\*\*', '', s).strip()
    eleje = next(i for i, s in enumerate(sorok) if s.startswith('## ') and '1. szekció' in fejlec(s))
    vege = next(i for i, s in enumerate(sorok) if s.startswith('# ') and 'Hírlevél' in fejlec(s))
    ki, szekcio = [], ''
    for s in sorok[eleje:vege]:
        if s.startswith('## '):
            szekcio = fejlec(s[3:])
            m = re.match(r'(\d+)(-\d+)?\.', szekcio)
            szam = m.group(1) if m else ''
            valtozatlan = szam == '7'
            ki.append('')
            ki.append('## ' + szekcio + (' [VÁLTOZATLAN]' if valtozatlan else ''))
            continue
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', s)
        if m:
            cimke, maradek = m.group(1).strip(), m.group(2).strip()
            if valtozatlan:
                ki.append(f'**{cimke}:** {maradek}'.rstrip())          # a VALTOZATLAN szekcio jeloletlen = MARAD
                continue
            marad = cimke.startswith('Gomb ') or (cimke == 'Heading' and szam in MARAD_CIMEK)
            ki.append(f'**{cimke}:** [{"MARAD" if marad else "CSERE"}]')
            if maradek:
                ki.append(maradek)
            continue
        ki.append(s.strip())
    landing = ('# 2026/11 landing -- ESZTER DOKSIJABOL generalva (landing-doksi-atalakito.py)\n'
               f'# forras: {sys.argv[1]}  sha256={hashlib.sha256(nyers.encode()).hexdigest()[:8]}\n\n'
               '=== BEMENO-SZOVEG-KEZDETE ===\n' + '\n'.join(ki).strip('\n') + '\n\n=== BEMENO-SZOVEG-VEGE ===\n')
    io.open(sys.argv[2], 'w', encoding='utf-8').write(landing)

    # --- a 4. pont: kurzuskartya-mondat + hosszabb leiras, ingyenes es VIP
    k4 = next(i for i, s in enumerate(sorok) if re.match(r'^4\. Kurzusleírások', fejlec(s)))
    resz = [s.strip() for s in sorok[k4:]]
    kartya = {}
    for s in resz:
        m = re.match(r'^(Ingyenes|VIP):\s*(.+)$', s)
        if m:
            kartya[m.group(1)] = m.group(2)
    blokk = {}
    for nev, minta in (('Ingyenes', r'^Ingyenes kurzus:'), ('VIP', r'^VIP kurzus:')):
        i = next(j for j, s in enumerate(resz) if re.match(minta, s))
        cim = resz[i].split(':', 1)[1].strip()
        torzs = [s for s in resz[i + 1:i + 4] if s][:2]
        if len(torzs) != 2 or not torzs[1].startswith('Kezdés:'):
            raise SystemExit(f'HIBA: a(z) {nev} kurzusleiras nem "leiras + Kezdés:" alaku: {torzs}')
        blokk[nev] = (cim, torzs)
    if set(kartya) != {'Ingyenes', 'VIP'}:
        raise SystemExit(f'HIBA: a kurzuskartya-mondat hianyzik: {sorted(kartya)}')
    leiras = '# Kurzusleirasok -- ESZTER DOKSIJABOL (4. pont), landing-doksi-atalakito.py\n\n'
    for n, (nev, kod) in enumerate((('Ingyenes', 'Ingyenes kurzus'), ('VIP', 'VIP kurzus')), 1):
        cim, torzs = blokk[nev]
        leiras += f'## {n}. {kod}: {cim}\n\n{torzs[0]}\n\n{torzs[1]}\n\nKártya: {kartya[nev]}\n\n---\n\n'
    io.open(sys.argv[3], 'w', encoding='utf-8').write(leiras)
    print(f'landing -> {sys.argv[2]} ({len(ki)} sor)')
    print(f'leiras  -> {sys.argv[3]}')


if __name__ == '__main__':
    main()
