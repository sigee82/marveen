#!/usr/bin/env python3
"""Memoria mentese a dashboard API-ra, IDO-KAPUVAL.

A napi naplonak 2026-08-18 ota van szkriptje (`napi-naplo.py`), es az mukodik: Pixel
2026-08-25-i visszamerese szerint a javitas ota 245 fejlecbol 245 percre pontos, mikozben a
javitas ELOTT 1483-bol csak 306 volt az. A memoria-oldalra viszont csak egy SZABALY-SOR keszult,
szkript nem -- es ugyanaz a merés ott 14 kitalalt idopontot talalt.

EZ A SZKRIPT AZT A LEPEST TESZI GEPIVE, AMI A NAPLO-OLDALON BEVALT: az idot a szkript teszi be
a rendszerorabol, es a szovegben allo idopontokat MEGMERI, mielott kimennek.

HASZNALAT
    python3 scripts/memoria-mentes.py --agent nova --kategoria cold \\
        --kulcsszavak "a, b" --szoveg "..."
    ... --stdin                       # a szoveg a stdin-en
    ... --onteszt                     # POZITIV KONTROLL, nem ir sehova

A szovegben hasznalhato helykitoltok, amiket a szkript MERT ertekre cserel:
    {MOST}       -> 2026-08-25 09:14          (datum + ora, rendszerorabol)
    {MA}         -> 2026-08-25                (csak datum)
    {ORA}        -> 09:14
Ha ezeket hasznalod, egyaltalan nem tudsz elirni orat.

A KAPU HAROM SZABALYA (a 2026-08-25-i meres ket hibaosztalyabol):
 1. MAI DATUMHOZ HORGONYZOTT JOVOBELI ORA -> BLOKKOL. Pl. "merve 2026-08-25 09:40", ha most 09:14 van.
 2. TARTOMANY MINDKET VEGPONTJA szamit. A domino hiba a memoria-oldalon EPP EZ VOLT: "merve
    2026-08-22 08:05-08:20", mentve 08:10-kor -- a KEZDET helyes, csak a VEG jovobeli. Egy olyan
    kapu, ami csak az elso orat nezi, a 10 ilyenbol 10-et atengedne (Pixel tervezesi eszrevetele).
 3. HORGONY NELKULI CSUPASZ ORA -> CSAK FIGYELMEZTET, nem blokkol. Pixel merese szerint az ilyen
    talalatok TULNYOMO RESZE HAMIS: elozo napi legitim hivatkozas, ejfelt atlepo idezet, vagy maga
    a hiba LEIRASA. A tulriasztas leszoktat a figyelesrol, ezert itt nem allunk meg.
"""
import argparse, pathlib, json, os, re, sys, urllib.request
from datetime import datetime, timedelta

TOKEN_FAJL = "/Users/macmini/marveen/store/.dashboard-token"
VEGPONT = "http://localhost:3420/api/memories"
KATEGORIAK = ("hot", "warm", "cold", "shared")

# "2026-08-25 09:40" vagy "2026-08-25 09:40-10:05" (a masodik ora is szamit)
# AZ EV OPCIONALIS (2026-08-28, Pixel meresei nyoman). A meresi jelentesek tablazat-szeru
# felsorolasaiban szinte sosem all ki az evszam: "08-25 20:00", "08-22 22:00". A regi,
# evszamot KOVETELO alak ezeket NEM ismerte fel horgonynak, ezert a CSUPASZ ag kapta el
# oket, es horgony nelkuli jovobeli oraként figyelmeztetett -- EGY mentesnel 11-szer.
# A tulriasztas ara nem nulla: leszoktat a figyelmeztetesek olvasasarol, es akkor marad
# el az igazi (ugyanaz az osztaly, mint a keparany-eset).
# A valtoztatas KET IRANYBAN hat, es mindketto helyes:
#   - csendesebb: a MAS napra horgonyzott rovid alak tobbe nem figyelmeztet,
#   - SZIGORUBB: a MAI naphoz horgonyzott rovid alak jovobeli oraja mostantol BLOKKOL,
#     amit korabban csak egy figyelmeztetes jelzett.
# Ev nelkul a MOSTANI evet vesszuk; ha igy nem a mai nap jon ki, a kapu ugyanugy
# atengedi, mint barmely mas napi horgonyt.
HORGONYZOTT = re.compile(r"(?<![\d-])(?:(\d{4})-)?(\d{1,2})-(\d{2})[^\d\n]{0,12}?(\d{1,2}):(\d{2})(?:\s*[-–]\s*(\d{1,2}):(\d{2}))?")
CSUPASZ = re.compile(r"(?<![\d:-])(\d{1,2}):(\d{2})(?![\d:])")

# KEPARANY-KIVETEL: a "9:16" ora-alaku, tehat a CSUPASZ elkapja es jovobeli oranak
# minositi. A szabaly a KOZOS modulban all, mert ugyanez a hamis pozitiv a
# napi-naplo.py-ban is elojon -- ket masolat eseten a kovetkezo javitas elmaradna.
# A reszletes indoklas, a mert szamok es a tudatosan hagyott res: scripts/keparany_szuro.py
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from keparany_szuro import keparany_e as _keparany_e


def keparany_e(szoveg: str, m) -> bool:
    return _keparany_e(szoveg, m.group(0), m.start(), m.end())


def kapu(szoveg: str, most: datetime):
    """(blokkolo lista, figyelmezteto lista)"""
    blokk, figyelem = [], []
    ma = most.date()
    horgonyzott_helyek = set()
    for m in HORGONYZOTT.finditer(szoveg):
        ev = int(m.group(1)) if m.group(1) else most.year
        ho, nap = int(m.group(2)), int(m.group(3))
        try:
            d = datetime(ev, ho, nap).date()
        except ValueError:
            continue
        horgonyzott_helyek.add(m.span())
        if d != ma:
            continue  # mas nap: a mult ideju hivatkozas legitim, a jovobeli datum nem ennek a kapunak a dolga
        for oi, pi in ((4, 5), (6, 7)):
            if m.group(oi) is None:
                continue
            o, p = int(m.group(oi)), int(m.group(pi))
            if o > 23 or p > 59:
                continue
            t = most.replace(hour=o, minute=p, second=0, microsecond=0)
            # TURES: 2 perc. A 0-2 perces "jovo" ora-kerekites, nem kitalalas -- a meres
            # tenyleg futott, csak a masodpercek estek at a percen. Az ELES visszamereskor
            # (159 memoria, 2026-08-25) turés nelkul 16 talalat jott, es abbol 5 pontosan
            # ilyen 0-2 perces zaj volt. A tulriasztas leszoktat a figyelesrol (Pixel
            # eszrevetele) -- ezert a zajt kivesszuk, a valodit meghagyjuk.
            if t > most + timedelta(minutes=2):
                perc = int((t - most).total_seconds() // 60)
                melyik = "a tartomany VEGE" if oi == 6 else "az idopont"
                blokk.append(f"{m.group(0)!r}: {melyik} ({o:02d}:{p:02d}) {perc} perccel a MOSTANI "
                             f"{most:%H:%M} UTAN van -- ez meg nem tortent meg")
    for m in CSUPASZ.finditer(szoveg):
        if any(a <= m.start() < b for a, b in horgonyzott_helyek):
            continue
        o, p = int(m.group(1)), int(m.group(2))
        if o > 23 or p > 59:
            continue
        if keparany_e(szoveg, m):
            continue
        t = most.replace(hour=o, minute=p, second=0, microsecond=0)
        if t > most + timedelta(minutes=2):
            figyelem.append(f"{m.group(0)}: horgony nelkuli ora a mostani {most:%H:%M} UTAN. "
                            f"Ha ez elozo napi hivatkozas, ird ki a datumot is.")
    return blokk, figyelem


def helykitolto(szoveg: str, most: datetime) -> str:
    return (szoveg.replace("{MOST}", most.strftime("%Y-%m-%d %H:%M"))
                  .replace("{MA}", most.strftime("%Y-%m-%d"))
                  .replace("{ORA}", most.strftime("%H:%M")))


ONTESZT = [
    ("merve {ma} 09:40, es a kovetkeztetes ez", 60, True,  "mai horgony, jovobeli ora"),
    ("merve {ma} 08:05-09:40 kozott", 60, True,  "TARTOMANY vege jovobeli, a kezdete nem"),
    ("merve {ma} 08:05-08:20 kozott", 60, False, "tartomany, mindketto mult -> atmegy"),
    ("a {tegnap} 23:05-os korben tortent", 60, False, "MAS napi horgony -> nem ennek a kapunak a dolga"),
    ("{ma} 09:00-kor merve", 60, False, "mai horgony, mult ido -> atmegy"),
    ("a 23:05-os kor eredmenye", 60, False, "horgony nelkuli ora -> csak figyelmeztet, NEM blokkol"),
    ("a vagat 9:16 aranyban keszul", 60, False, "KEPARANY keparany-kontextussal -> ne is figyelmeztessen"),
    ("a 9:16-os kreativ a Reels helyekre megy", 60, False, "KEPARANY, masik kontextus-szo"),
    # FIGYELEM a teszteset valasztasara: a "9:16" a rogzitett 09:14-es teszt-orahoz kepest
    # ket percen belul van, es a kapunak 2 perc turelme van -- azon a szovegen tehat a
    # kivetel NELKUL sem riasztana, vagyis semmit nem bizonyitana. A 16:10 tavolabb esik.
    ("16:10-kor merve, es ez a lelet", 60, False, "ora keparany-szo NELKUL -> figyelmeztet (nem blokkol)"),
    # A MASIK_ARANY szabaly tamado esetei (Pixel visszamerese nyoman, 2026-08-28).
    # Ezek mind blokkolas-mentesek; a lenyeg a FIGYELMEZTETES megléte, amit az
    # ontesztbol nem lehet allitani -- ezert all mellettuk, mit kell latni.
    ("a 4:5-os vagat 11:40-kor keszult el", 60, False, "valodi ora, NEM arany-alaku -> a whitelist megvedi, RIASZT"),
    # A VEZETO NULLAS eset ("09:16") EBBEN A HARNESSBEN NEM TESZTELHETO, es ezert nincs
    # itt teszteset ra: a rogzitett teszt-ora 09:14, a 09:16 pedig a kapu 2 PERCES
    # TURELMI IDEJEBE esik, tehat a kivetel nelkul SEM riasztana -- egy zold pipa ott
    # semmit nem bizonyitana. (Ugyanaz a csapda, amibe a 9:16-os tesztesettel mar
    # egyszer beleléptem ugyanezen a napon.) KULON MEGMERVE 06:00-s orarol:
    #   "a 4:5-os vagat 09:16-kor keszult el" -> RIASZT (helyes)
    #   "a 4:5-os vagat 16:10-kor keszult el" -> ATENGEDI (ez a tudatosan hagyott res)
    # Ha valaki ezt teszteset ala akarja vinni, a harness rogzitett orajat kell mozgatni.
    ("9:16 es 4:5 kozott kell valasztani", 60, False, "ket arany egymas mellett -> helyesen ATENGEDI"),
    # EV NELKULI (MM-DD) HORGONY -- Pixel merese, 2026-08-28. Az 5. elem a VART
    # figyelmeztetes-szam; e nelkul ezek a sorok semmit nem bizonyitananak, mert
    # mindharom eset figyelmeztetes-szintu, nem blokkolo.
    ("a 08-22 22:00-as korben mertem", 60, False, "MAS napi ROVID horgony -> se blokk, se figyelmeztetes", 0),
    ("08-25 09:00-kor merve, ez a lelet", 60, False, "MAI rovid horgony, MULT ora -> atmegy, nema", 0),
    ("08-25 09:40-kor merve, ez a lelet", 60, True,  "MAI rovid horgony, JOVOBELI ora -> mostantol BLOKKOL", 0),
    ("a 08-26 15:17-es es a 08-27 21:03-as bejegyzes", 60, False, "ket rovid horgony egy sorban -> nema", 0),
]


# Cirill/gorog betu, ami latin betuvel EGY SZOBAN all. Ez a homoglifa ujjlenyomata:
# egy TELJESEN cirill szo legitim (idezet, nev), de egy cirill betu EGY LATIN SZO
# KOZEPEN mindig elgepeles. A kar tartos es nema: a grep sosem talalja meg, es a
# hianyzo talalat NULLANAK latszik, nem hibanak.
#
# MIERT KAPU ES NEM SZABALY: 2026-09-20-an egy delelott haromszor csuszott be a sajat
# szovegembe -- egy memoria-fajlba, egy kanban-kommentbe es a napi naploba --, mindig
# egy magyar szo vegen, ahol az ekezetes betu helyere hasonlo alaku cirill kerult.
# Mind a harmat utolag talaltam meg, kulon keresessel. A figyelem nem hianyzott.
IDEGEN_BETU_RX = re.compile(r"[\u0400-\u04FF\u0370-\u03FF]")
SZO_RX = re.compile(r"[^\W\d_]+", re.UNICODE)


def homoglifak(szoveg: str) -> list:
    """A vegyes irasrendszeru szavakat adja: (szo, betu, kodpont, pozicio)."""
    ki = []
    for m in SZO_RX.finditer(szoveg):
        szo = m.group()
        idegen = [c for c in szo if IDEGEN_BETU_RX.match(c)]
        if not idegen or len(idegen) == len(szo):
            continue
        for c in idegen:
            ki.append((szo, c, f"U+{ord(c):04X}", m.start() + szo.index(c)))
    return ki


def onteszt() -> int:
    most = datetime(2026, 8, 25, 9, 14)
    ma, tegnap = "2026-08-25", "2026-08-24"
    hiba = 0
    print(f"POZITIV KONTROLL (a 'most' fixen {most:%Y-%m-%d %H:%M}):")
    for eset in ONTESZT:
        sablon, _, kell_blokk, mit = eset[0], eset[1], eset[2], eset[3]
        # Az 5. elem OPCIONALIS: a VART FIGYELMEZTETES-szam. Nelkule a teszteset csak a
        # blokkolasrol allit -- es epp ez volt a vak folt: a keparany- es a rovid-datum
        # eset MINDKETTO figyelmeztetes-szintu, tehat a blokkolas-alapu pipa rajtuk
        # semmit nem bizonyitott. (2026-08-28)
        kell_fig = eset[4] if len(eset) > 4 else None
        sz = sablon.format(ma=ma, tegnap=tegnap)
        b, f = kapu(sz, most)
        van = bool(b)
        ok = (van == kell_blokk) and (kell_fig is None or len(f) == kell_fig)
        if not ok:
            hiba += 1
        allapot = "OK  " if ok else "HIBA"
        fig_info = "" if kell_fig is None else f", figyelmeztetes={len(f)} (kell: {kell_fig})"
        print(f"  [{allapot}] blokkol={van} (kell: {kell_blokk}){fig_info}  {mit}")
        for x in b:
            print(f"          -> {x}")
        for x in f:
            print(f"          ~  {x}")
    # A HOMOGLIFA-DETEKTOR SAJAT KONTROLLJAI. Pozitiv kontroll a VALODI esetbol
    # (2026-09-20, cirill `e` egy magyar szo vegen), negativ kontroll arra, hogy a
    # tiszta magyar es a teljesen cirill szoveg NE akadjon fenn.
    hgl_hiba = 0
    for mit, be, kell in [
        ("pozitiv: cirill `e` magyar szo vegen", "a meropad mer\u0435se", True),
        ("negativ: tiszta magyar, ekezettel", "arvizturo tukorfurogep, merese", False),
        ("negativ: teljesen cirill szo (idezet)", "a szo \u043f\u0440\u0438\u0432\u0435\u0442 volt", False),
        ("negativ: szamok", "a 42 es a 3,14", False),
    ]:
        van = bool(homoglifak(be))
        allapot = "OK " if van == kell else "HIBA"
        if van != kell:
            hiba += 1
            hgl_hiba += 1
        print(f"  [{allapot}] homoglifa={van} (kell: {kell})  {mit}")

    print(f"\nonteszt: {hiba} hiba")
    return 1 if hiba else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent")
    ap.add_argument("--kategoria", choices=KATEGORIAK)
    ap.add_argument("--kulcsszavak", default="")
    ap.add_argument("--szoveg")
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--onteszt", action="store_true")
    ap.add_argument("--megis", action="store_true",
                    help="a blokkolo kapu megkerulese -- CSAK ha a kapu tenyleg tevedett, es ird meg a naploba")
    a = ap.parse_args()

    if a.onteszt:
        return onteszt()
    if not a.agent or not a.kategoria:
        print("--agent es --kategoria kotelezo", file=sys.stderr)
        return 2
    szoveg = sys.stdin.read() if a.stdin else (a.szoveg or "")
    if not szoveg.strip():
        print("ures szoveg", file=sys.stderr)
        return 2

    most = datetime.now()
    szoveg = helykitolto(szoveg, most)

    # A HOMOGLIFA-KAPU A HELYKITOLTO UTAN FUT, mert a behelyettesitett idopont maga is
    # szoveg -- es a kulcsszavakra IS rafut, mert epp azokon a legdragabb: egy homoglifas
    # kulcsszo szerint kesobb SOSEM lesz talalat, es az emlek csendben elerhetetlen lesz.
    hgl = homoglifak(szoveg + "\n" + (a.kulcsszavak or ""))
    if hgl and not a.megis:
        print(f"KAPU -- {len(hgl)} vegyes irasrendszeru szo. A memoria NEM ment el.", file=sys.stderr)
        for szo, betu, kod, poz in hgl:
            print(f"  {szo!r}  <- {betu!r} ({kod}) a {poz}. karakteren", file=sys.stderr)
        print("  Latin betunek LATSZANAK, de nem azok: a keresesed sosem fogja megtalalni oket.",
              file=sys.stderr)
        print("  Javitsd a betut. Ha tenyleg szandekos (idezet), --megis.", file=sys.stderr)
        return 3

    blokk, figyelem = kapu(szoveg, most)

    for x in figyelem:
        print(f"FIGYELMEZTETES: {x}", file=sys.stderr)
    if blokk and not a.megis:
        print(f"KAPU -- a memoria NEM ment el (rendszerora: {most:%Y-%m-%d %H:%M}):", file=sys.stderr)
        for x in blokk:
            print(f"  {x}", file=sys.stderr)
        print("  Javitas: hasznald a {MOST} / {ORA} helykitoltot, vagy ird at a mert ertekre.",
              file=sys.stderr)
        print("  Ha a kapu tevedett, --megis, es ird meg a naploba, miert.", file=sys.stderr)
        return 3

    tok = open(TOKEN_FAJL).read().strip()
    adat = json.dumps({"agent_id": a.agent, "content": szoveg,
                       "category": a.kategoria, "keywords": a.kulcsszavak}).encode()
    r = urllib.request.Request(VEGPONT, data=adat,
                               headers={"Content-Type": "application/json",
                                        "Authorization": "Bearer " + tok})
    v = json.loads(urllib.request.urlopen(r).read().decode())
    print(f"OK: memories id={v.get('id')} | {a.kategoria} | rendszerora {most:%Y-%m-%d %H:%M}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
