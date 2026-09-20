#!/usr/bin/env python3
"""Kapu az `agent_msg NNNNN` hivatkozasokra: a sor AZONOSSAGAT meri, nem a letezeset.

MIERT LETEZIK
-------------
Signal HAROM alkalommal irt le rossz `agent_msg` azonositot -- 2026-09-16-an EGY
sessionben ketszer (12465 helyett 12467, majd 12478 helyett 12479), 2026-09-20-an
egyszer (13781 helyett 14155). Mindharomszor ugyanaz a mechanizmus: a jelentes
szoveget es a marker-riportot a KULDES ELOTT allitotta elo, mert addigra minden
szam keszen volt -- az azonosito viszont CSAK a POST valaszaban keletkezik.
Amit nem egy LEPES gyart, azt kitoltjuk. (Ugyanaz az alak, mint az idopontnal:
ott a napi-naplo.py MERT erteket tesz be a rendszerorabol.)

>>> ES A LENYEG: MINDHAROM ROSSZ ID LETEZETT. <<<
Nem hibat adtak vissza, hanem EGY MASIK IGAZ VALASZT -- egy idegen sort. Ezert egy
"letezik-e az ID" alaku kapu MIND A HARMAT atengedte volna, vagyis pont a valodi
hibaosztalyra lenne vak. A kapu feltetele ezert az AZONOSSAG: letezik, ES a sor
tenyleg a hivatkozo agens sajat, adott iranyu uzenete, ES az ablakban keletkezett.

A HATOKOR, KIMONDVA
-------------------
Ez a szkript EGY SZOVEGET kap, nem egy payloadot -- szandekosan. Az `agent_msg`
hivatkozas nem csak a marker PUT-jaba kerul: memoria-mentesbe, napi naploba es a
tarsagensnek kuldott jelentesbe is, es mind ugyanabbol a kuldes ELOTT eloallitott
szovegbol jon. Ha a kapu egy konkret hivashoz kotne magat, a tobbi ut fedetlen
maradna. Igy egy kesobbi PreToolUse hook ra tud ulni ugyanerre a fuggvenyre
(lasd `ellenoriz()`), es a fedes nem a hivo sorrendjetol fugg.

A GYOKER-JAVITAS NEM EZ A KAPU, HANEM A LEPES-SORREND: a hivatkozast az a lepes
gyartsa, amelyik az erteket eloallitja (eloszor kuldj, a valaszbol vedd az ID-t,
es a `<PENDING>` helykitoltot csak utana valtsd ki). A kapu a maradek kockazatot
fogja, nem a szokast valtja ki -- egy kapu, ami minden korben javit egy tippet,
elobb-utobb rutinna valik, es az elso nem fedett uton ujra atmegy a tipp.

HASZNALAT
---------
    python3 scripts/agens-msg-id-kapu.py --agens signal --fajl <szovegfajl>
    ... | python3 scripts/agens-msg-id-kapu.py --agens signal          # stdin
    python3 scripts/agens-msg-id-kapu.py --onteszt                     # pozitiv kontroll

EXIT-KODOK
----------
    0 = minden hivatkozas AZONOS a hivatkozo sajat uzenetevel (vagy nincs hivatkozas)
    1 = van GYANUS hivatkozas -- ez a RIASZTAS, nem hiba
    2 = a kapu maga nem tudott merni (nincs DB) -- ez LELET, nem "szabad"

A kimenet MINDIG kiirja a NEVEZOT (hany hivatkozast vizsgalt), mert egy le nem
futott kapu es egy tiszta kor kulonben egyforman nez ki.
"""
import argparse
import os
import re
import sqlite3
import sys
import time

DB = "/Users/macmini/marveen/store/claudeclaw.db"

# `agent_msg 14155`, `agent_msg: 14155`, `agent_msg #14155`, `agent_msgs 14155`.
# A csupasz "msg 1234" alakot SZANDEKOSAN nem nezi: a flotta ket szamozasi teret
# hasznal (agent_messages es Telegram message_id), azonos tartomanyban -- egy
# jeloletlen szam nem dontheto el, es a kapu nem talalgat. A csupasz alakot maga
# a szabaly tiltja (mindig ird ki, melyik ter).
#
# A `[felado->cimzett]` utotag OPCIONALIS, es ez a SZANDEKOS IDEGEN-HIVATKOZAS alakja:
#     agent_msg 8910 [nova->nova]
# Ilyenkor a kapu NEM varja el, hogy a sor a hivatkozoe -- DE a megadott iranyt
# VISSZAMERI. Vagyis nem kibuvo, hanem egy ALLITAS, amit a kapu ellenoriz: ha a
# valos irany mas, az ugyanugy GYANUS. Egy nema "skip" ujra vakka tenne a kaput.
MINTA = re.compile(
    r"\bagent_msgs?\b\s*[:#]?\s*(\d{2,7})\b"
    r"(?:\s*\[\s*([a-z0-9_-]+)\s*->\s*([a-z0-9_-]+)\s*\])?",
    re.IGNORECASE,
)

# Alapertelmezett ablak: ennyi napra visszamenoleg fogadjuk el sajat hivatkozasnak.
# Nem szigor kedveert van: egy honapokkal korabbi sajat uzenetre hivatkozni legitim,
# csak akkor a `--ablak 0` kapcsolja ki az ido-agat. Az ablakon KIVULI sajat sor
# GYANUS, nem HIBAS -- a kimenet ezt kulon mondja.
ALAP_ABLAK_NAP = 30


def _sorok(db_ut, idk):
    """A hivatkozott id-k MERT allapota az agent_messages-bol. {id: row|None}"""
    ki = {}
    with sqlite3.connect(f"file:{db_ut}?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        for i in idk:
            cur = con.execute(
                "SELECT id, from_agent, to_agent, created_at FROM agent_messages WHERE id = ?",
                (i,),
            )
            ki[i] = cur.fetchone()
    return ki


def ellenoriz(szoveg, agens, db_ut=DB, ablak_nap=ALAP_ABLAK_NAP, most=None):
    """Egy szoveget vizsgal. Visszaad: (egyedi_talalatok, gyanus_lista).

    Ez a fuggveny a szerzodes: egy PreToolUse hook ezt hivja, nem a main()-t.
    """
    most = most if most is not None else int(time.time())
    # id -> a nala megadott, szandekos irany-allitas (vagy None). Ha ugyanaz az id
    # tobbszor szerepel es legalabb egyszer JELOLVE, a jelolest vesszuk: a jeloles
    # szandekot fejez ki, a jeloletlen elofordulas lehet puszta roviditesi.
    jeloles = {}
    for m in MINTA.finditer(szoveg):
        i = int(m.group(1))
        if m.group(2) and m.group(3):
            jeloles[i] = (m.group(2).lower(), m.group(3).lower())
        else:
            jeloles.setdefault(i, None)
    egyedi = sorted(jeloles)
    if not egyedi:
        return [], []

    sorok = _sorok(db_ut, egyedi)
    gyanus = []
    for i in egyedi:
        r = sorok.get(i)
        if r is None:
            gyanus.append((i, "NEM LETEZIK", "ilyen sor nincs az agent_messages-ben"))
            continue
        allitott = jeloles.get(i)
        if allitott is not None:
            # SZANDEKOS IDEGEN-HIVATKOZAS. Nem kibuvo: a megadott iranyt visszamerjuk.
            valos = (r["from_agent"], r["to_agent"])
            if valos != allitott:
                gyanus.append(
                    (i, "JELOLES NEM EGYEZIK",
                     f"a szoveg [{allitott[0]}->{allitott[1]}]-t allit, a sor valojaban "
                     f"{valos[0]} -> {valos[1]}")
                )
            continue
        # AZ AZONOSSAG-AG: ez a lenyeg. A sor letezik, de rola szol-e a mondat?
        if r["from_agent"] != agens and r["to_agent"] != agens:
            gyanus.append(
                (i, "IDEGEN SOR",
                 f"{r['from_agent']} -> {r['to_agent']}, a hivatkozo ({agens}) egyik vegen sincs. "
                 f"HA SZANDEKOS, jelold: `agent_msg {i} [{r['from_agent']}->{r['to_agent']}]`")
            )
            continue
        if ablak_nap > 0 and r["created_at"] and (most - int(r["created_at"])) > ablak_nap * 86400:
            napja = (most - int(r["created_at"])) // 86400
            gyanus.append(
                (i, "ABLAKON KIVUL",
                 f"sajat sor ({r['from_agent']} -> {r['to_agent']}), de {napja} napja -- "
                 f"legitim lehet, `--ablak 0` kikapcsolja ezt az agat")
            )
    return egyedi, gyanus


def _onteszt():
    """POZITIV KONTROLL, harom eset. A 2-es a lenyeg: egy 'letezik-e' kapu MIND A
    HARMAT atengedne, mert mindharom ID letezik."""
    import tempfile

    db_ut = os.path.join(tempfile.mkdtemp(), "onteszt.db")
    most = 1_789_900_000
    with sqlite3.connect(db_ut) as con:
        con.execute(
            "CREATE TABLE agent_messages (id INTEGER PRIMARY KEY, from_agent TEXT, "
            "to_agent TEXT, content TEXT, status TEXT, created_at INTEGER)"
        )
        con.executemany(
            "INSERT INTO agent_messages (id, from_agent, to_agent, content, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            [
                (14155, "signal", "nova", "a valodi jelentes", "delivered", most - 600),
                (13781, "nova", "bit", "IDEGEN: letezik, de masrol szol", "delivered", most - 90000),
            ],
        )

    esetek = [
        ("1. LETEZO, signal->nova sor", "Jelentes: agent_msg 14155.", False),
        ("2. LETEZO, de IDEGEN sor", "Jelentes: agent_msg 13781.", True),
        ("3. NEM LETEZO ID", "Jelentes: agent_msg 9999999.", True),
        ("4. JELOLT idegen sor, HELYES iranyt allit",
         "A context-guard sora: agent_msg 13781 [nova->bit].", False),
        ("5. JELOLT idegen sor, HAMIS iranyt allit",
         "A context-guard sora: agent_msg 13781 [nova->signal].", True),
    ]
    print("POZITIV KONTROLL -- 5 eset, agens='signal', ablak=30 nap\n")
    bukott = 0
    naiv_atengedne = 0
    for cim, szoveg, megall_e in esetek:
        talalat, gyanus = ellenoriz(szoveg, "signal", db_ut=db_ut, most=most)
        tenyleg = bool(gyanus)
        ok = tenyleg == megall_e
        bukott += 0 if ok else 1
        # Mit adna egy puszta "letezik-e" kapu? Csak a NEM LETEZIK agat nezne.
        if not any(f == "NEM LETEZIK" for _, f, _ in gyanus):
            naiv_atengedne += 1
        print(f"  [{'OK ' if ok else 'BUKO'}] {cim}")
        print(f"         vizsgalt: {len(talalat)} | verdikt: "
              f"{'MEGALL' if tenyleg else 'atmegy'} (vart: {'MEGALL' if megall_e else 'atmegy'})")
        for i, fajta, indok in gyanus:
            print(f"         -> agent_msg {i}: {fajta} -- {indok}")
    print()
    print(f"  KONTRASZT: egy puszta 'letezik-e' kapu {naiv_atengedne}/{len(esetek)} esetet engedne at,")
    print( "  koztuk a 2-est -- es PONT AZ a valodi hibaosztaly (mind a negy eles eset ilyen volt:")
    print( "  12465 bit->nova, 12478 nova->bit, 13781 nova->bit, 12222 bit->nova).")
    print(f"\n  {'MIND A(Z) ' + str(len(esetek)) + ' ESET RENDBEN.' if not bukott else str(bukott) + ' ESET BUKOTT.'}")
    return 0 if not bukott else 1


def main():
    p = argparse.ArgumentParser(description="agent_msg hivatkozas-kapu (azonossag, nem letezes)")
    p.add_argument("--agens", help="a hivatkozo agens id-je, pl. signal")
    p.add_argument("--fajl", help="a vizsgalando szoveg fajlja (alapertelmezes: stdin)")
    p.add_argument("--ablak", type=int, default=ALAP_ABLAK_NAP,
                   help=f"hany napra visszamenoleg fogadjuk el sajat hivatkozasnak "
                        f"(0 = ki; alap {ALAP_ABLAK_NAP})")
    p.add_argument("--db", default=DB)
    p.add_argument("--onteszt", action="store_true", help="pozitiv kontroll, harom eset")
    a = p.parse_args()

    if a.onteszt:
        return _onteszt()
    if not a.agens:
        p.error("--agens kotelezo (vagy hasznald az --onteszt kapcsolot)")

    if not os.path.exists(a.db):
        print(f"KAPU-HIBA: az adatbazis nem talalhato ({a.db}).", file=sys.stderr)
        print("EZ LELET, NEM 'SZABAD': meres nelkul a hivatkozasokrol semmit nem allitunk.",
              file=sys.stderr)
        return 2

    szoveg = open(a.fajl, encoding="utf-8").read() if a.fajl else sys.stdin.read()
    talalat, gyanus = ellenoriz(szoveg, a.agens, db_ut=a.db, ablak_nap=a.ablak)

    # A NEVEZO MINDIG MENJEN KI: egy le nem futott kapu es egy tiszta kor kulonben
    # egyforman nez ki (ugyanaz a hibaosztaly, mint minden negativ leletnel).
    print(f"agent_msg hivatkozas: {len(talalat)} egyedi vizsgalva | agens: {a.agens} | "
          f"ablak: {'ki' if a.ablak == 0 else str(a.ablak) + ' nap'}")
    if talalat:
        print(f"  id-k: {', '.join(str(i) for i in talalat)}")
    if not gyanus:
        print("MINDEN HIVATKOZAS AZONOS a hivatkozo sajat uzenetevel." if talalat
              else "NINCS agent_msg hivatkozas a szovegben -- a kapu lefutott, nem volt mit merni.")
        return 0

    print(f"\n!! GYANUS: {len(gyanus)} a {len(talalat)}-bol", file=sys.stderr)
    for i, fajta, indok in gyanus:
        print(f"   agent_msg {i}: {fajta} -- {indok}", file=sys.stderr)
    print("\n   A LEPES: NE talald ki a helyes ID-t. Kuldd el az uzenetet, es a POST",
          file=sys.stderr)
    print("   VALASZABOL vedd az azonositot -- a `<PENDING>` helykitolto ezt varja.",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
