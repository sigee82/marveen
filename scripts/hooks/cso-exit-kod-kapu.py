#!/usr/bin/env python3
"""PreToolUse gate on Bash: `$?` a cso VEGEN allo parancsot meri, nem a mertet.

MIERT LETEZIK
-------------
A `valami 2>&1 | tail -5; echo "exit=$?"` alakban a `$?` a `tail` kilepesi kodja,
ami majdnem mindig 0 -- a mert parancs bukasa NEM latszik. A szam kimegy egy
jelentesbe "exit=0"-kent, es HAMIS ZOLDET ad.

Ez nem elmeleti. 2026-09-22-en HAROM agens futott bele egy napon (Signal ketszer,
Nova egyszer, en egyszer), es nalam mar KET emlek tiltotta (4170 a 09-16-i esetrol,
4375). Ha N emlek tiltja ugyanazt es megis megtortenik, a hiba nem tudasbeli, hanem
viselkedesi -- es egy N+1-edik feljegyzes annyit er, mint az elozo N.

A KENYELMI KENYSZER, ami odatol (es amire a kapu valaszt ad)
------------------------------------------------------------
A csovezes nem hanyagsag: a kimenetet KELL rovidre fogni, kulonben elarasztja a
kontextust. Tehat a "ne csovezz" tiltas egy masik, helyes szabaly ellen dolgozna.
Ezert a kapu uzenete a MEGENGEDETT ALAKOT is megadja: fajlba iranyits, a kodot
kozvetlenul merd, a rovid kivonatot utana vedd ki a fajlbol.

A SZUKITO, ES HONNAN JON
------------------------
Nem "van cso es van $?" -- az a valodi korpuszon 17 talalatot adott, es a felük
HELYES parancs volt (`cmd > /tmp/x 2>&1; echo $?`, ahol a cso egy KESOBBI
utasitasban all). A szukito a hibas esetek kozos vonasa: a `$?` olvasasat
KOZVETLENUL MEGELOZO utasitas csovezett-e.

Merve a `tool_call_log` OSSZES rogzitett Bash-hivasan (2026-09-22):
    csak "$?"                                     104
    + cso barhol, pipestatus/pipefail nelkul       17   <- ebbol ~7 hamis riasztas
    + a $?-t KOZVETLENUL megelozo utasitas csovez  10   <- mind a 10 valodi hiba
Tuzelesi arany: 0.31%. Egy alaptalanul tuzelo kapu a leggyorsabb ut ahhoz, hogy
leszokjunk rola, ezert a szukito a szigorubb.

A NEVEZO, mert elso korben ELRONTOTTAM: "a sajat 3163 hivasomat" irtam ide, es az
nem az enyem volt, hanem a TELJES log het agenstol. A bontas (2026-09-22 12:5x):
    nova 1525 | bit 961 | nessa 391 | signal 242 | copy 51 | pixel 34 | summa 12
    osszesen 3216, ebbol blokkolva 10 (0.31%); csak a bit soraira 961/3 (0.31%)
Ez a kapu javara szol -- het kulonbozo ember-szokasra ugyanaz az arany --, de a
szam akkor is mas kerdesre valaszolt, mint amit a mondat allitott. **Aki egy masik
agens "sajat" korpuszan akarja fuggetlenul ellenorizni, elobb nezze meg, hogy a
sorai nincsenek-e MAR BENNE ebben a tablaban: ugyanabbol a tablabol venni egy
szeletet nem fuggetlen ismetles.**

AMIT A KAPU NEM FOG (kimondva, hogy ne latsszon tobbnek)
--------------------------------------------------------
- `set -o pipefail` vagy `${PIPESTATUS[0]}` eseten ATENGED: ott a szandek
  egyertelmu, es a nyelv megadja a helyes erteket.
- Tobbsoros szkriptet, ahol a `$?` egy fuggvenyben all, es a hivo oldalon dol el,
  mi elozi meg. Az mar parse-olas, nem mintaillesztes.
- Azt NEM allitja, hogy a nem-csovezett `$?` helyes. Csak azt, hogy a csovezett
  biztosan nem azt meri, amit a szerzo hisz.

Contract: PreToolUse. A hook payload stdin-en jon, exit 0 = engedd,
exit 2 = blokkolj (a stderr megy vissza a modellhez).
"""

import json
import os
import re
import sys

HATAROLOK = (';', '&&', '||', '\n', '(', '{')


def _hatar_vissza(parancs: str, poz: int):
    """A `poz` elotti legkozelebbi hatarolo (index, hossz) parja, vagy (-1, 0).

    A HOSSZ NEM ELHAGYHATO. A `||` ket karakter: ha egy karakterrel lepunk tovabb,
    a masodik `|` BENNMARAD a szakaszban, es a kapu csonek olvassa. Igy tuzelt a
    `npm test || echo baj; echo "$?"` alakra, ami teljesen helyes parancs -- a
    mutans-letra fogta meg, a valodi korpusz nem (nincs benne ilyen).
    """
    legjobb, hossz = -1, 0
    for h in HATAROLOK:
        i = parancs.rfind(h, 0, poz)
        if i > legjobb:
            legjobb, hossz = i, len(h)
    return legjobb, hossz


def megelozo_utasitas(parancs: str, poz: int) -> str:
    """A `$?` olvasasat kozvetlenul megelozo utasitas szovege.

    Ket hatart keresunk visszafele: az elsot (ez zarja a megelozo utasitast) es a
    masodikat (ez nyitja). Ami kozottuk all, az az, aminek a kodjat a szerzo MERNI
    akarta.
    """
    veg, _ = _hatar_vissza(parancs, poz)
    if veg < 0:
        return ''
    eleje, eleje_hossz = _hatar_vissza(parancs, veg)
    return parancs[eleje + eleje_hossz:veg] if eleje >= 0 else parancs[:veg]


def idezett_heredoc_nelkul(parancs: str) -> str:
    """Az IDEZETT heredoc-ok torzsenek kiejtese -- az ADAT, nem parancs.

    MIERT KELL. A kapu a sajat jelentesemen sult el: az uzenet szovegeben
    IDEZTEM egy hibas parancsot ("... | head -20; echo \"EXIT=$?\""), es az
    egesz uzenet egy `<<\'PY\'` heredoc torzseben allt. A shell egy IDEZETT
    hataroloju heredoc torzseben SEMMIT nem ertelmez -- ott definicio szerint
    adat van. Egy kapu, ami a rola szolo dokumentaciora tuzel, pont arra szoktat
    ra, hogy megkeruljuk.
    A NEM idezett heredoc (`<<EOF`) torzse viszont behelyettesitodik, tehat az
    marad a vizsgalt szovegben.
    """
    def csere(m):
        tag = m.group('tag')
        # a torzs a hataroloig tart (sor eleji tag, esetleg tabokkal `<<-` eseten)
        vege = re.search(r'^[ \t]*' + re.escape(tag) + r'[ \t]*$',
                         parancs[m.end():], re.MULTILINE)
        return m.end() + (vege.end() if vege else len(parancs) - m.end())

    ki, poz = [], 0
    for m in re.finditer(r"<<-?\s*(?:'(?P<tag>[^']+)'|\"(?P<tag2>[^\"]+)\")", parancs):
        if m.start() < poz:
            continue
        tag = m.group('tag') or m.group('tag2')
        maradek = parancs[m.end():]
        vege = re.search(r'^[ \t]*' + re.escape(tag) + r'[ \t]*$', maradek, re.MULTILINE)
        torzs_vege = m.end() + (vege.end() if vege else len(maradek))
        ki.append(parancs[poz:m.end()])
        poz = torzs_vege
    ki.append(parancs[poz:])
    return ''.join(ki)


def csovezett(szakasz: str) -> bool:
    """Van-e benne VALODI cso? A `||` nem cso, es a cso ne idezojelen belul legyen."""
    # `||` kiejtese, hogy ne szamitson csonek
    tiszta = re.sub(r'\|\|', ' ', szakasz)
    # idezojeles szakaszok kiejtese: egy `|` egy szovegben nem csovezes
    tiszta = re.sub(r'"[^"]*"', ' ', tiszta)
    tiszta = re.sub(r"'[^']*'", ' ', tiszta)
    return '|' in tiszta


def vizsgal(parancs: str):
    """(talalat, a mert utasitas) vagy (False, '')."""
    # Kis-nagybetu-fuggetlenul: zsh-ban `${pipestatus[1]}`, bashban `${PIPESTATUS[0]}`.
    parancs = idezett_heredoc_nelkul(parancs)
    also = parancs.lower()
    if 'pipestatus' in also or 'pipefail' in also:
        # A KIUT, AMIT A KAPU MEGALD, DE NEM MUKODIK ITT.
        #
        # Pixel kerdese (2026-09-22): ha a kijelolt kiut elakad, a kapu
        # zsakutcaba zar. Egy fokkal rosszabb eset is van, es ez az: a kiut NEM
        # akad el, hanem NEMAN rossz. A `${PIPESTATUS[0]}` bash-alak, zsh alatt
        # ures sztringet ad -- Nova buko csovon merte (`false | tail -2`), tehat
        # nem csak elter a ket alak, hanem a bash-alak EPP A HIBAT nyeli el.
        # A kapu eddig ezt atengedte, uzenet nelkul: megaldotta a sajat rossz
        # kiutjat. Most atengedi (nem a mi dolgunk eldonteni, milyen shellben
        # fut), de KIMONDJA.
        if 'PIPESTATUS' in parancs and 'zsh' in os.environ.get('SHELL', ''):
            sys.stderr.write(
                'cso-exit-kod-kapu (FIGYELMEZTETES, nem blokkolas): a `${PIPESTATUS[...]}` '
                'BASH-alak, a te shelled viszont zsh -- itt URES sztringet ad, tehat az '
                '"exit=" sor ures marad es a bukas ugyanugy nem latszik. zsh-ban: '
                '`${pipestatus[1]}`, vagy `set -o pipefail` (mindket shellben jo).\n'
            )
        return False, ''
    for m in re.finditer(r'\$\?', parancs):
        szakasz = megelozo_utasitas(parancs, m.start())
        if csovezett(szakasz):
            return True, szakasz.strip()
    return False, ''


UZENET = """cso-exit-kod-kapu: a `$?` itt a CSO VEGEN allo parancsot meri, nem azt, amit merni akarsz.

  a `$?` elott ez az utasitas all:
    {szakasz}

  A `| tail`/`| head`/`| grep` majdnem mindig 0-val ter vissza, tehat a mert parancs
  BUKASA NEM LATSZIK, es a szam "exit=0"-kent megy ki egy jelentesbe. Hamis zold.

  MEGENGEDETT ALAK -- a kimenet ugyanugy rovid marad:
    <parancs> > /tmp/ki.txt 2>&1; echo "exit=$?"; tail -5 /tmp/ki.txt
  vagy ha tenyleg csovezni kell:
    set -o pipefail; <parancs> | tail -5; echo "exit=$?"      <- ez mindket shellben jo
    <parancs> | tail -5; echo "exit=${{pipestatus[1]}}"       <- zsh (itt EZ a shell)

  FIGYELEM: a `${{PIPESTATUS[0]}}` BASH-alak, es zsh alatt URES sztringet ad --
  megmerve 2026-09-22, zsh 5.9: `false | true` utan a zsh-alak 1-et adott, a
  bash-alak semmit. Egy ures "exit=" pont olyan nema, mint a rossz kod.

  (Ha a `$?` tenyleg a cso egeszere vonatkozik es ez szandekos, hasznald a
   pipefail/pipestatus alakot -- a kapu azt atengedi.)
"""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception as exc:
        # Fail-open, DE NEM NEMAN. Egy olvashatatlan payload nem a szerzo hibaja,
        # es nem is ok a munka megallitasara -- de ha a hook-szerzodes egyszer
        # megvaltozik (mas mezonev, mas burkolas), a kapu ettol a perctol NEM VED,
        # es semmi nem mondja meg. Pont az a hibaosztaly, ami ellen keszult:
        # egy vedelem, ami jel nelkul szunik meg. Ezert a stderr-re kiirja magat.
        sys.stderr.write(
            'cso-exit-kod-kapu: a payload nem olvashato (%r), a kapu ATENGED -- '
            'ha ez ismetlodik, a hook-szerzodes valtozott meg, nem a parancs.\n' % (exc,)
        )
        return 0

    if payload.get('tool_name') != 'Bash':
        return 0
    parancs = (payload.get('tool_input') or {}).get('command') or ''
    if not parancs:
        return 0

    talalat, szakasz = vizsgal(parancs)
    if not talalat:
        return 0

    sys.stderr.write(UZENET.format(szakasz=szakasz[:160]))
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:  # egy guard-hiba soha ne akassza meg a munkat
        sys.stderr.write('cso-exit-kod-kapu: belso hiba (%r), a kapu ATENGED.\n' % (exc,))
        sys.exit(0)
