#!/usr/bin/env python3
"""PreToolUse gate on Bash: a MAI datumhoz horgonyzott JOVOBELI ora nem mehet ki.

MIERT LETEZIK
-------------
A flotta becsult idopontokat irt ki mert ertek helyett. 2026-08-18-an harom agens
merte vissza a sajat aznapi naplo-fejleceit: Nova csucson 7 ora 39 perccel, Pixel
26 bejegyzesbol 25-ben atlag 31 perccel irt rossz orat, es a naplo kronologiaja ket
helyen megfordult. A becsult ora nem zajos, hanem EGY IRANYBA torzit (elore) es
felhalmozodik -- a mas agensek helyes belyegeihez kepest felcsereli a sorrendet,
amibol ok-okozatot szoktunk olvasni.

2026-08-25-en 159 memorian visszamerve ez a kapu 13-at fogott volna meg, koztuk
NYOLC olyan tartomanyt, ahol a KEZDET helyes volt es csak a VEG jovobeli -- egy
csak-az-elso-orat-nezo kapu mindet atengedte volna.

MIT CSINAL, HAROM AGON
----------------------
1. HORGONYZOTT ora (datum all mellette) es a horgony a MAI nap, es az ora
   JOVOBELI  ->  BLOKKOL (exit 2). Ez a lelet: mert ertek nem lehet a jovoben.
2. HORGONYZOTT ora, de a horgony NEM a mai nap  ->  ATENGEDI. Egy tegnapi vagy
   jovo heti idopont legitim hivatkozas.
3. HORGONY NELKULI csupasz ora  ->  ATENGEDI, de figyelmeztet. Azok tulnyomo
   resze legitim elozo napi hivatkozas, es egy blokkolas itt tobbet artana.

FONTOS: a tartomany MINDKET veget nezi (a "14:00-15:30" alakban a 15:30-at is),
mert a 2026-08-25-i visszameres szerint ott bujik meg a talalatok tobbsege.

Contract: PreToolUse. A hook payload stdin-en jon, exit 0 = engedd,
exit 2 = blokkolj (a stderr megy vissza a modellhez).

FAIL-OPEN, SZANDEKOSAN. Ez a kapu egy MINOSEGI szabalyt orzi, nem biztonsagit:
ha a vizsgalat maga elszall, a parancs MENJEN AT. A masik irany 2026-09-10-en
elsult: a fajl eltunt, a settings.json nyers `python3 <ut>` alakja a python sajat
"No such file" hibajat adta vissza a harnessnek, es ettol HAT agens Bash-e allt
meg -- egy minosegi kapu miatt. Egy elszallo minosegi kapu ne benitson eszkozt.
"""
import json
import os
import re
import sys
from datetime import datetime

# KEPARANY-KIVETEL. A "9:16" ora-alaku, tehat a lenti ORA-minta elkapja es jovobeli
# oranak minositi -- Reel es Lumen minden vagas-parancsaban ott van. A szabaly a
# KOZOS modulban all (scripts/keparany_szuro.py), mert ugyanez a hamis pozitiv a
# memoria-mentes.py-ban es a napi-naplo.py-ban is elojon; harom masolat eseten a
# kovetkezo javitas ket helyen elmaradna.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    from keparany_szuro import keparany_e as _keparany_e
except Exception:  # noqa: BLE001 -- a kapu a modul nelkul is mukodjon
    def _keparany_e(szoveg, token, start, end):
        return False

# Egy ora: 9:05, 14:03, 23:59. A masodperc opcionalis.
ORA = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?\b")

# Datum-horgony az ora KORNYEZETEBEN. Harom alak, mert mind a harmat hasznaljuk:
#   2026-09-10 / 2026.09.10 / 2026. szept. 10
HORGONY = re.compile(
    r"(\d{4})[-.]\s?(\d{1,2})[-.]\s?(\d{1,2})"
    r"|(\d{4})\.\s*(jan|feb|mar|ápr|apr|máj|maj|jun|jún|jul|júl|aug|sze|okt|nov|dec)[a-zíáéóöúüű]*\.?\s*(\d{1,2})"
)
HONAP = {"jan": 1, "feb": 2, "mar": 3, "ápr": 4, "apr": 4, "máj": 5, "maj": 5,
         "jun": 6, "jún": 6, "jul": 7, "júl": 7, "aug": 8, "sze": 9,
         "okt": 10, "nov": 11, "dec": 12}

# Mennyi szoveget nezunk az ora ELOTT horgonyt keresve. 40 karakter eleg a
# "2026-09-09 14:03:05" es a "2026. szept. 10. 14:03" alakhoz is.
HORGONY_ABLAK = 40


def horgony_datuma(elotte: str):
    """A legkozelebbi datum-horgony az ora elott, vagy None."""
    talalat = None
    for m in HORGONY.finditer(elotte):
        talalat = m  # az UTOLSO (legkozelebbi) szamit
    if not talalat:
        return None
    g = talalat.groups()
    try:
        if g[0]:
            return datetime(int(g[0]), int(g[1]), int(g[2])).date()
        kulcs = (g[4] or "")[:3].lower()
        return datetime(int(g[3]), HONAP.get(kulcs, 0) or 1, int(g[5])).date()
    except (ValueError, TypeError):
        return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)  # olvashatatlan payload: nem a mi dolgunk blokkolni

    parancs = ""
    ti = payload.get("tool_input")
    if isinstance(ti, dict):
        parancs = str(ti.get("command") or "")
    if not parancs:
        sys.exit(0)

    most = datetime.now()
    ma = most.date()
    jovobeli = []
    horgonytalan = []

    for m in ORA.finditer(parancs):
        if _keparany_e(parancs, m.group(0), m.start(), m.end()):
            continue  # 9:16, 16:10 stb. keparany-kontextusban: nem ora
        ora, perc = int(m.group(1)), int(m.group(2))
        elotte = parancs[max(0, m.start() - HORGONY_ABLAK):m.start()]
        d = horgony_datuma(elotte)
        perc_kulonbseg = (ora * 60 + perc) - (most.hour * 60 + most.minute)
        if d is None:
            if perc_kulonbseg > 0:
                horgonytalan.append(m.group(0))
            continue
        if d != ma:
            continue  # nem mai horgony: legitim hivatkozas
        if perc_kulonbseg > 0:
            jovobeli.append("%s (+%d perc)" % (m.group(0), perc_kulonbseg))

    if jovobeli:
        sys.stderr.write(
            "KAPU: a kimeno szovegben JOVOBELI ora all, ami nem lehet mert ertek: "
            + ", ".join(jovobeli)
            + ".\nA rendszerora most %s. A parancs NEM futott le.\n\n" % most.strftime("%H:%M")
            + "OK: a becsult idopont EGY IRANYBA torzit (elore) es felhalmozodik. "
              "A mas agensek helyes belyegeihez kepest felcsereli a sorrendet, "
              "amibol ok-okozatot szoktunk olvasni -- es a kanban-komment nem is szerkesztheto.\n\n"
            + "JAVITAS, ket lehetoseg:\n"
              "  1. Ha az idopontot MERNED kellett volna: futtass egy `date`-et, es AZT "
              "az erteket ird le. Tartomanyt csak akkor irj, ha MINDKET vegpontja mert.\n"
              "  2. Ha az ora legitim jovobeli hivatkozas (utemezes, hatarido, kovetkezo kor) "
              "vagy egy MAS napi mert ertek: ird ele a DATUMOT (pl. \"2026-09-04 16:00\"). "
              "A datummal horgonyzott ora atmegy -- es amugy is az a helyes alak, mert "
              "horgony nelkul egy ora ket het mulva ertelmezhetetlen.\n"
        )
        sys.exit(2)

    if horgonytalan:
        sys.stderr.write(
            "FIGYELEM (nem blokkol): horgony nelkuli, jovobelinek latszo ora a szovegben: "
            + ", ".join(horgonytalan[:5])
            + ". Ha mert ertek, ird ele a datumot.\n"
        )
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        # FAIL-OPEN. Lasd a modul-docstring vegen: egy elszallo MINOSEGI kapu
        # ne benitson eszkozt. A 2026-09-10-i incidens pont ez volt.
        sys.stderr.write("idobelyeg-gate: belso hiba (%r), a kapu ATENGED.\n" % (exc,))
        sys.exit(0)
