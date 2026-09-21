#!/usr/bin/env python3
"""Stale-watcher detector.

A csak-hibat-jelento figyelok csendje ketertelmu: ugyanugy hangzik a "lefutott, nincs
lelet" es a "sosem futott le". Aki a sajat markeret olvassa, a SZAGGATOTT kiesest megfogja,
a TARTOSAT nem -- ha a feladatot kikapcsoljak vagy torlik, a marker olvasoja is elhallgat.
(Bit lelete, 2026-09-21.)

Ezert ezt a szkriptet egy MASIK, megbizhatoan futo jarat hivja (ma: reggeli-napindito),
es a figyelt feladatoktol FUGGETLENUL meri oket:
  (a) letezik-e meg az utemezes, es enabled-e,
  (b) letezik-e a marker-fajl,
  (c) friss-e.
Ures kimenet = mind a harom rendben. Barmely sor = lelet.
"""
import datetime
import json
import os
import re
import subprocess
import sys

TASKS = os.path.expanduser("~/.claude/scheduled-tasks")
TOKEN = "/Users/macmini/marveen/store/.dashboard-token"
ALAP_KUSZOB_NAP = 2


def varhato_nap(cron):
    """Ket futas kozotti varhato nap a cron alakjabol.

    Miert szamoljuk, es nem tablazatbol vesszuk (Bit lelete, 2026-09-21): egy kezi
    kuszob-tabla olyan erteket kovet, amit a lekert utemezes-lista MAR hordoz. A 83 sorbol
    csak 33 napi vagy surubb, 10 heti-ish, 40 ritkabb -- vagyis amint egy HETI figyelo
    markert kap (pont az az osztaly, ami miatt ez keszult), egy fix 2 napos kuszob HETENTE
    tuzelne, orokre. Egy kapu, ami mindig mond valamit, ugyanannyit er, mint amelyik sosem.

    A felbontas szandekosan NAP: a marker napra kerekitett datumot tarol, ennel finomabbat
    nem tud merni. Ezert a `*/30 * * * *` is 1 napot ad, nem fel orat -- jobb kimondani,
    mint pontosabbnak latszani.
    """
    r = (cron or "").split()
    if len(r) != 5:
        return None
    _perc, _ora, nap, honap, hetnap = r
    if honap != "*":
        if honap.startswith("*/"):
            try:
                lepes = int(honap[2:])
            except ValueError:
                lepes = 1
            return 365.0 / max(1, 12 // max(1, lepes))
        return 365.0 / max(1, len([x for x in honap.split(",") if x]))
    if nap.startswith("*/"):
        # Minden N. nap. Enelkul az ag atesne a heti/napi vizsgalatra es 1 napot adna,
        # amitol a kuszob 2 lenne -- egy `*/3` sor 3 naponta fut, tehat HETENTE tobbszor
        # hamisan tuzelne. Sajat meres 2026-09-21: `0 9 */3 * *` -> 1.0 nap volt.
        try:
            return float(int(nap[2:]))
        except ValueError:
            return 1.0
    if nap != "*":
        return 30.0
    if hetnap != "*":
        if "-" in hetnap:
            a, b = hetnap.split("-")[0], hetnap.split("-")[-1]
            try:
                n = int(b) - int(a) + 1
            except ValueError:
                n = 1
        else:
            n = len([x for x in hetnap.split(",") if x != ""])
        return 7.0 / max(1, n)
    return 1.0


def kuszob_nap(cron):
    v = varhato_nap(cron)
    if v is None:
        return ALAP_KUSZOB_NAP
    return max(ALAP_KUSZOB_NAP, round(2 * v))


def utemezesek():
    try:
        with open(TOKEN) as f:
            t = f.read().strip()
        ki = subprocess.run(
            ["curl", "-s", "-H", f"Authorization: Bearer {t}",
             "http://localhost:3420/api/schedules"],
            capture_output=True, text=True, timeout=20).stdout
        return {r["name"]: r for r in json.loads(ki)}
    except Exception as e:
        print(f"LELET: az utemezes-lista nem olvashato ({e}) -- a marker-kor NEM futott le")
        sys.exit(0)


def main():
    ma = datetime.date.today()
    sched = utemezesek()
    leletek = []

    # Minden feladat, ami a promptjaban markert deklaral
    for nev, r in sched.items():
        prompt = r.get("prompt") or ""
        m = re.search(r"(~/\.claude/scheduled-tasks/[\w.-]+/\.[\w.-]+)", prompt)
        if not m:
            continue
        ut = os.path.expanduser(m.group(1))
        kuszob = kuszob_nap(r.get("schedule"))

        if not r.get("enabled"):
            leletek.append(f"LELET: `{nev}` KI VAN KAPCSOLVA, de markert deklaral -- a csendje nem jelent semmit")
            continue
        if not os.path.exists(ut):
            # TURELMI IDO: egy frissen letrehozott sornal a hianyzo marker nem lelet, hanem
            # "meg nem esedekes" -- a ketto ugyanugy nez ki. 36 ora alatt egy napi cronnak
            # legalabb egyszer tuzelnie kellett, tehat utana a hiany MAR lelet.
            kor_ora = (datetime.datetime.now().timestamp() - os.stat(os.path.dirname(ut)).st_birthtime) / 3600 \
                if os.path.isdir(os.path.dirname(ut)) else 1e9
            if kor_ora < 36:
                continue
            leletek.append(f"LELET: `{nev}` {kor_ora/24:.1f} napja letezik es engedelyezve van, "
                           f"de a markere MEG SOSEM keletkezett ({ut})")
            continue
        try:
            elso = open(ut).read().split()[0]
            d = datetime.datetime.strptime(elso, "%Y-%m-%d").date()
        except Exception as e:
            leletek.append(f"LELET: `{nev}` markere olvashatatlan ({e})")
            continue
        kor = (ma - d).days
        if kor > kuszob:
            leletek.append(f"LELET: `{nev}` {kor} napja nem futott (marker: {elso}, kuszob: {kuszob} nap)")

    # Gazdatlan marker: letezik a fajl, de nincs hozza utemezes
    if os.path.isdir(TASKS):
        for mappa in sorted(os.listdir(TASKS)):
            p = os.path.join(TASKS, mappa)
            if not os.path.isdir(p):
                continue
            markerek = [f for f in os.listdir(p) if f.startswith(".utolso")]
            if markerek and mappa not in sched:
                leletek.append(f"LELET: `{mappa}` markere ott all, de ilyen nevu UTEMEZES MAR NINCS")

    for s in leletek:
        print(s)


if __name__ == "__main__":
    main()
