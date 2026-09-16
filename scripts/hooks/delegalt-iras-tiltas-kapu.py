#!/usr/bin/env python3
"""
delegalt-iras-tiltas-kapu -- megfogja, ha egy inter-agent uzenetben olyan IRAST kerek
egy tarsagenstol, amit a sajat, ervenyben levo tiltasom NEKI megtilt.

MIERT VAN EZ (2026-09-16, HARMADIK elofordulas egy honapon belul):
  2026-09-14 (emlek 3974), 2026-09-15 (emlek 4060) es 2026-09-16 -- haromszor kertem
  Signaltol, hogy irjon a fizetnivalo-Sheetbe, holott a SAJAT 2026-08-16-i tiltasom
  (agent_msg 6437) szerint oda Signal NEM irhat, semmilyen oszlopba, semmilyen indokkal.
  Mindharomszor a CIMZETT fogta meg, nem en.

A SZERKEZET, amiert ez ismetlodik (emlek 4060 es [[kikotes-egyetlen-hordozoja-a-kotelezett]]):
  a tiltas a VEGREHAJTO oldalan van bejegyezve, az utasitast viszont a KERO adja ki.
  Akinek a fejeben a feladat CELJA van ("kerüljön be a sor"), annak nincs olyan artefaktuma,
  ami emlekeztetne arra, hogy KI IRHAT oda. Ket eset figyelmetlenseg; harom mar szerkezet,
  es a sajat `sajat-ismetlodo-hiba-kapuzasa` skillem szerint ilyenkor MECHANIKUS kapu jar,
  nem ujabb feljegyzes.

MIT CSINAL: nem tilt, hanem MEGALLIT es visszakerdez. A tiltas feloldhato -- de TUDATOSAN,
nem azert, mert elfelejtettem, hogy letezik.
"""
import json, re, sys

# (minta a celpontra, minta a muveletre, kinek tiltott, a tiltas forrasa es indoka)
SZABALYOK = [
    {
        "cel": r"fizetnivalo|fizetnivaló|Céges -- 2026|Ceges -- 2026|Magán -- 2026|1D1Tge6meLFqpBKEHVZ",
        "muvelet": r"\bird be\b|\bir be\b|\bird bele\b|\bvedd fel\b|\bvezesd\b|\begeszitsd\b|\bbeir\b|\bbeír|\bsort\b.*\b(fel|be)\b|\bwrite\b|\bappend\b",
        "tiltott_agensek": ["signal", "summa", "copy", "pixel", "bit", "lumen", "reel", "nessa"],
        "forras": "sajat tiltas, 2026-08-16, agent_msg 6437",
        "indok": ("a Sheetnek NINCS utkozes-detektalasa: ket iro eseten az egyik iras NEMAN "
                  "eltunik, es utana MINDKETTO 'visszaolvastuk'-ot jelent. Elesben 2026-08-16-an "
                  "allt elo a Generali H11-en. A kockazat MA IS elo, mert TE MAGAD irsz erre a "
                  "lapra rendszeresen."),
        "helyes_ut": ("kerd el a KESZ SZOVEGET es a CELLAT, es ird be TE. Beiras elott merd meg, "
                      "hogy a celzott sor tenyleg ures, es hogy a tetel nem szerepel mar a lapon; "
                      "utana OLVASD VISSZA."),
    },
]

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if payload.get("tool_name") != "Bash":
        sys.exit(0)
    cmd = (payload.get("tool_input") or {}).get("command", "") or ""

    # >>> CSAK A VALODI KULDES ERDEKEL, NEM A ROLA SZOLO SZOVEG. KET SAJAT HIBA, PERCEKKEL A
    # KAPU MEGEPITESE UTAN (2026-09-16): <<<
    #  (1) Az elso valtozat `"/api/messages" in cmd`-re ment, es megfogta a SAJAT EMLEK-MENTESEMET,
    #      mert annak a heredoc-szovege IDEZTE az utvonalat. Ez a `uj-kontroll-incidens-utan` skill
    #      dokumentalt buktatoja: a substring-matcher a sajat dokumentaciojara is illeszkedik.
    #  (2) A javito parancsomat is megfogta, mert a KONTROLL-TESZTEK szovege tartalmazta a
    #      `curl ... /api/messages` alakot -- vagyis onmagat zaro kapu lett belole, ami epp azt a
    #      lepest tiltja, amibol a feloldasa szuletne (`kapu-hatokore-kit-vedd-kitol`).
    # A javitas: a heredoc TORZSET levagjuk, es a payloadot is csak a parancs-fejbol vesszuk.
    parancs_fej = re.split(r"<<-?\s*['\"]?\w+['\"]?", cmd, maxsplit=1)[0]
    if not re.search(r"curl[^|;&]*?/api/messages", parancs_fej, re.S):
        sys.exit(0)

    # a payload lehet inline (-d) vagy fajlban (--data-binary @fajl) -- mindkettot nezzuk
    szoveg = parancs_fej
    for m in re.finditer(r"--data-binary\s+@([^\s]+)", cmd):
        p = m.group(1).strip('"\'')
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                szoveg += "\n" + f.read()
        except Exception:
            pass

    low = szoveg.lower()
    # kinek megy? a "to":"<agens>" mezobol
    cimzett = None
    mt = re.search(r'"to"\s*:\s*"([a-z0-9_-]+)"', low)
    if mt:
        cimzett = mt.group(1)

    for sz in SZABALYOK:
        if cimzett and cimzett not in sz["tiltott_agensek"]:
            continue
        if not re.search(sz["cel"], szoveg, re.I):
            continue
        if not re.search(sz["muvelet"], low, re.I):
            continue
        uzenet = (
            f"KAPU: olyan IRAST kersz {cimzett or 'egy tarsagenstol'}, amit a SAJAT, ERVENYBEN LEVO "
            f"TILTASOD tilt meg neki ({sz['forras']}).\n"
            f"AZ INDOK, amit te magad mertel meg: {sz['indok']}\n"
            f"A HELYES UT: {sz['helyes_ut']}\n"
            f"EZ A HARMADIK ELOFORDULAS egy honapon belul (2026-09-14 emlek 3974, 09-15 emlek 4060, "
            f"09-16) -- mindharomszor a CIMZETT fogta meg, nem te. Ezert all itt kapu.\n"
            f"HA TUDATOSAN FELOLDOD: ird bele az uzenetbe szo szerint, hogy "
            f"'a 2026-08-16-i tiltast erre az egy esetre tudatosan feloldom', es a kapu atenged."
        )
        if "tudatosan feloldom" in low:
            sys.exit(0)
        print(uzenet, file=sys.stderr)
        sys.exit(2)

    sys.exit(0)

if __name__ == "__main__":
    main()
