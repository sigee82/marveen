#!/usr/bin/env python3
"""Generate the input for the Sheet-vs-register comparison the email round owes.

WHY THIS EXISTS (2026-08-28): the skill mandates this comparison every morning
round, and on 2026-08-28 I skipped it and still reported the round as complete.
The miss surfaced a second overdue utility bill (Magyar Telekom, no bank charge
since 2026-07-20) half a day late.

WHAT IT DOES: parses the handed-over items out of the register (memories 1501)
and prints them ranked BY PAYMENT MODE, not by date -- because that is what the
same day taught: of the ten items with no Sheet row, nine were harmless (already
paid, card/automatic) and the one that mattered was the single one whose mode
carried a `?`. Exits non-zero while any `?`-mode item is open, so it cannot pass
silently.

WHAT IT DOES NOT DO: read the Sheet. That needs the Drive MCP, which a script
cannot call. This produces the LIST you check the Sheet against -- so the input
is generated, not typed from memory (the FoxPost row was lost in 2026-08-12
exactly that way).
"""
import argparse, re, sqlite3, sys
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "store" / "claudeclaw.db"
REGISTER_ID = 1501


def load(db_path, mem_id):
    row = sqlite3.connect(db_path).execute(
        "SELECT content FROM memories WHERE id=?", (mem_id,)).fetchone()
    if row is None:
        sys.exit(f"HIBA: a {mem_id} memoria nem letezik ({db_path}).")
    return row[0]


# Harom vodor, a VALODI kockazati tengely menten -- nem datum, hanem az, hogy
# a tetel MAGATOL lemegy-e. Ezt a 2026-08-28-i meres tanitotta: a tiz Sheet-sor
# nelkuli tetelbol kilenc mert kartyas volt (koltsegmentes), es az egyetlen,
# ami szamitott, a `?`-es modu Telekom.
UNSURE = re.compile(r"\(\?\)")                       # a mod maga bizonytalan
MANUAL = re.compile(r"KEZI lepest igenyel|KÉZI lépést igényel|nem megy le magatol"
                    r"|nem megy le magától|NYITOTT|ÁTUTALÁS|ATUTALAS|UTÁNVÉT|UTANVET", re.I)
SETTLED = re.compile(r"KIFIZETVE|MÁR TERHELVE|MAR TERHELVE|automata|LEZÁRVA|LEZARVA"
                     r"|MEGMÉRVE|MEGMERVE|IGAZOLT|levonva", re.I)

BUCKET = {
    "?":      ("!!", "a MOD bizonytalan -- KELL Sheet-sor"),
    "KEZI":   ("! ", "nem megy le magatol -- KELL Sheet-sor"),
    "MERT":   ("  ", "mert kartyas/automata -- a hianyzo sor koltsegmentes"),
}


def parse(text):
    """One item per '- **<azonosito>** | ...' line. A line it cannot classify is
    reported, never silently dropped -- a lost row is the expensive direction."""
    items, seen = [], set()
    for line in text.split("\n"):
        # HAROM alak all a regiszterben, es 2026-09-14-ig CSAK AZ ELSOT mertem:
        #   (a) "- **<id>** | ..."      felsorolas-elem (a 2026-08-as alak)
        #   (b) "| **<id>** (X) | ..."  TABLAZAT-sor (a 2026-09-es alak)
        #   (c) "`<id> | ...`"          backtick-es atadas-blokk
        # A (b) es (c) 2026-09-14-i meresig LATHATATLAN volt: 1253 sorbol 31-et
        # latott a mero, es a HAT nyitott szeptemberi tetelbol NULLAT. A sheet-
        # osszevetes bemenete igy szerkezetileg hianyos volt -- pont az a
        # hibaosztaly, ami ellen a script keszult.
        m = (re.match(r"\s*[-|]\s*\*\*(.+?)\*\*[^|]*\|(.*)$", line)
             or re.match(r"\s*`([A-Za-z0-9][^|`]{3,60}?)\s*\|(.*)$", line))
        if not m:
            continue
        ident, rest = m.group(1).strip(), m.group(2)
        # A DEDUP-KULCS A NEV **ES AZ OSSZEG**, NEM CSAK A NEV.
        # 2026-09-15: a csak-nev kulcs a B014 (16 500) es a B015 (27 500) sort
        # EGYNEK vette -- azonos szallitonev, ket KULON albetet, ket KULON tetel --,
        # es a masodikat NEMAN eldobta. Pont az a hibaosztaly, ami ellen a script
        # keszult. Az osszeget hozzaveve a koronkent ismetlodo UGYANAZ a tetel
        # tovabbra is osszeolvad; ket azonos nevu, KULONBOZO osszegu tetel nem.
        # Vallalt mellekhatas: ha egy tetel osszege kesobb javul, ketszer jon elo --
        # felesleges sort ki lehet venni, kimaradt tetelt nem lehet megtalalni.
        amt = re.search(r"(\d[\d\s\u00a0.,]{2,})\s*(?:Ft|EUR|USD)", rest)
        amt = re.sub(r"[^0-9]", "", amt.group(1)) if amt else ""
        key = re.sub(r"[^a-z0-9]", "", ident.lower()) + "#" + amt
        if key in seen:
            continue
        seen.add(key)
        if ident.upper().startswith("[LEZ"):
            continue
        if UNSURE.search(rest):
            bucket = "?"
        elif SETTLED.search(rest):
            bucket = "MERT"          # a kimondott fizetettseg eros jel
        elif MANUAL.search(rest):
            bucket = "KEZI"
        else:
            bucket = "?"             # osztalyozhatatlan -> a dragabb irany
        items.append((bucket, ident, rest.strip()[:130]))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--id", type=int, default=REGISTER_ID)
    a = ap.parse_args()

    items = parse(load(a.db, a.id))
    order = {"?": 0, "KEZI": 1, "MERT": 2}
    items.sort(key=lambda x: (order[x[0]], x[1]))

    risky = [i for i in items if i[0] != "MERT"]
    print(f"{len(items)} atadott tetel a regiszterben (memories {a.id}).")
    print(f"Ebbol {len(risky)} NEM megy le magatol -- CSAK EZEKNEK kell Sheet-sor.\n")
    print("Vesd ossze a Sheet KET lapjaval (Ceges + Magan), es a jelentesbe")
    print("MINDKET oldal elemszama menjen -- kulonben a '0 elteres' es a")
    print("'0 vizsgalt tetel' egyforman nez ki.\n")
    for bucket, ident, rest in items:
        flag, _ = BUCKET[bucket]
        print(f"{flag} [{bucket:4}] {ident} | {rest}")

    if risky:
        print(f"\n{'':2}--")
        for bucket in ("?", "KEZI"):
            n = sum(1 for i in items if i[0] == bucket)
            if n:
                print(f"{BUCKET[bucket][0]} {n} db [{bucket}]: {BUCKET[bucket][1]}")
        print("   Mindegyiknek legyen Sheet-sora, VAGY egy kimondott indok, miert nincs.")
        return 1
    print("\nMinden atadott tetel mert kartyas/automata -- nincs kockazatos hiany.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
