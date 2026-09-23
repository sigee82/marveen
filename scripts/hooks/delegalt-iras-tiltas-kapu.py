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
        # >>> A CEL-LISTAT KETSZER KELL MERNI, KET IRANYBA -- ES MA MINDKET HIBAT MEGKAPTUK.
        # (2026-09-21, Signal merte meg mindkettot, oran belul.)
        #
        # REGGEL A SZUKITESE engedett at egy VALODI kerest: a `cel` a vedett lapot a NEVEROL
        # ismerte fel (`fizetnivalo`, `Ceges -- 2026`, sheet-id), a keresem viszont a
        # FUNKCIOJAVAL hivatkozott ra ("a Billingo SHEET-SORA ... vedd fel"). Exit 0.
        #
        # DELELOTT A TAGITASA fogott meg egy ENGEDELYEZETT kerest: a puszta `táblá` agtol a
        # "Vedd fel a kanban táblára ezt a feladatot" is blokkolt -- holott a kanban-felvetel a
        # sajat napi rutinom, a CLAUDE.md szo szerint eloirja. Es rosszabb: az EKEZET dontott el,
        # ellentetes iranyba ("tablara" atment, "táblára" blokkolt), mert a `táblá` bekerult, a
        # `tabla` nem. Ugyanarra a keresre ketfele valasz, es egyik sem a CELROL szol.
        #
        # A MEGOLDAS: a tag szavak ONMAGUKBAN NEM celok. Csak akkor szamitanak, ha ugyanabban az
        # uzenetben ott a vedett lap egy HORGONYA (fizet/utal/Ceges--/Magan--), ES nem egy MASIK,
        # engedelyezett tabla a targy (kanban, kartya, InnoPlan). Igy a mai reggeli alakom
        # blokkolna (benne van a "kifizetve"), a kanban-rutin viszont atmegy.
        # Es mindket helyesiras EGYUTT megy be, kulonben az ekezet dont a cel helyett.
        "cel": r"fizetnivalo|fizetnivaló|Céges -- 2026|Ceges -- 2026|Magán -- 2026|Magan -- 2026|1D1Tge6meLFqpBKEHVZ",
        # tag alak: CSAK horgonnyal egyutt, es kizaro nelkul
        "cel_tag": r"sheet|táblá|tábla|tabla|tablazat|táblázat",
        # A HORGONY-FELTETEL 2026-09-21 08:2x-kor MEGSZUNT, es ez nem lazitas, hanem CSERE.
        # Signal megmerte, hogy horgony nelkul is lehet egyertelmuen a vedett lap egy soranak
        # felvetelet kerni ("Vedd fel a Billingo sheet-sorat a 21. sorba, a 14. es 15. minta
        # szerint" -- exit 0 volt, pedig szo szerint a tiltott keres). A horgony tehat NEM fedte
        # le a keresek egy reszet. A mondat-hatokor (lasd lent) pontosabban vegzi ugyanazt:
        # a kizaro szo ugyanabban a tagmondatban kell alljon, mint a keres.
        "cel_horgony": None,
        # A KIZARO LISTA CSAK EGYERTELMU TABLA-NEVEKET TARTALMAZHAT. Az elso valtozatban benne
        # allt a puszta `kartya|kártya` is -- es azzal a SAJAT MAI, TILTOTT keresem ATMENT volna,
        # mert abban a "kartya" BANKKARTYAT jelentett ("7 607 Ft, kartya, mar kifizetve"), nem
        # kanban-kartyat. Merve: POZ2 exit 0 lett, holott 2-t kell adnia. Egy kizaro szo, aminek
        # ket jelentese van, a vedelmet kapcsolja ki a rosszabbik jelentesnel.
        "cel_kizaro": r"kanban|InnoPlan|kanban_cards",
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
    nyers_payload = ""
    for m in re.finditer(r"--data-binary\s+@([^\s]+)", cmd):
        p = m.group(1).strip('"\'')
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                nyers_payload += "\n" + f.read()
        except Exception:
            pass
    szoveg += nyers_payload

    # >>> A JSON-BUROK MINDENT IDEZOJELBE TESZ, ES EZ MEGBUKTATTA AZ IDEZET-MASZKOLAST.
    # (2026-09-21, sajat hiba, a kontroll fogta meg: a maszkolas bevezetese utan MIND A HET
    # pozitiv eset exit 0 lett.) Az ok: a payload egy JSON fajl, amiben a TELJES uzenet-szoveg
    # egyetlen `"..."` ertek -- a maszkolo tehat az EGESZ tartalmat kivagta, es a kapu semmit
    # nem latott. Ugyanaz az alak, mint a heredoc-eset: a BUROK szerkezetet nezetem szovegnek.
    # A javitas: ha a payload JSON, a `content` mezot DEKODOLVA vizsgaljuk -- ott az idezojel mar
    # a szerzo sajat idezojele, nem a formatume. Ha nem parsolhato, marad a nyers szoveg.
    uzenet_szoveg = szoveg
    try:
        adat = json.loads(nyers_payload.strip())
        if isinstance(adat, dict) and isinstance(adat.get("content"), str):
            uzenet_szoveg = adat["content"]
    except Exception:
        pass

    low = szoveg.lower()
    # kinek megy? a "to":"<agens>" mezobol
    cimzett = None
    mt = re.search(r'"to"\s*:\s*"([a-z0-9_-]+)"', low)
    if mt:
        cimzett = mt.group(1)

    # >>> IDEZET-MASZKOLAS: A SAJAT KAPUROL SZOLO BESZAMOLOT A SAJAT KAPU ALLITOTTA MEG.
    # (2026-09-21, Signal merte meg a NAP VALODI FORGALMAN: negy nova->signal uzenetbol KETTO
    # tevedett -- a 14329 es a 14337, mindketto a kapu javitasarol szolo beszamolo. 49 illetve
    # 71 tagmondat, 12 illetve 15 tuzelo ablak, ES MIND IDEZET VOLT, egyik sem keres.)
    #
    # UGYANAZ AZ OSZTALY, MINT A 2026-09-16-I HEREDOC-ESET FENT, csak egy reteggel feljebb:
    # ott az utvonal-matcher illeszkedett a sajat dokumentaciojara, itt a cel/muvelet-minta
    # illeszkedik az IDEZETT kontroll-esetekre. A megoldas alakja is ugyanonnan jon: ami IDEZET,
    # az ne legyen vizsgalt szoveg.
    #
    # DE NEM TOROLJUK AZ IDEZETEKET A VIZSGALATBOL, MERT AZ UJ REST NYITNA: idezojelbe teve egy
    # VALODI tiltott keres atmenne ("Kerlek: 'vedd fel a sheet-sort'"). Ezert KET SCAN fut:
    #   - a MASZKOLT szovegen (idezetek es `-> exit N` sorok kivagva): ha ez tuzel, VALODI keres
    #     -> exit 2, blokkolas.
    #   - ha csak a NYERS szovegen tuzel: minden tuzelo ablak idezetben van -> FIGYELMEZTETES
    #     (stderr) es exit 0. A jel megmarad, de nem all az utba.
    # AZ ARA, KIMONDVA: egy idezetbe rejtett valodi keres igy FIGYELMEZTETESSEL atmegy. Ezt
    # vallaljuk, mert a jel nem tunik el -- szemben a torlessel, ahol nyom nelkul atmenne.
    def maszkol(t):
        t = re.sub(r"^.*->\s*exit\s*\d.*$", " ", t, flags=re.M)   # kontroll-eset sorok
        for minta in (r'"[^"\n]{0,400}"', r"'[^'\n]{0,400}'", r"`[^`\n]{0,400}`"):
            t = re.sub(minta, " ", t)
        return t

    def tuzel_e(sz, t):
        """Van-e olyan LEGFELJEBB HAROM SZOMSZEDOS tagmondatbol allo ablak, amiben a cel ES a
        muvelet egyutt all, es amiben NINCS kizaro szo."""
        darabok = [d for d in re.split(
            r"[;!?\n]|(?<=\.)\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ])| ES | es kerlek| es kérlek| plusz | kulon | külön ",
            t) if d and d.strip()]
        for i in range(len(darabok)):
            for j in range(i, min(i + 3, len(darabok))):
                ablak = " ".join(darabok[i:j + 1])
                if not re.search(sz["muvelet"], ablak.lower(), re.I):
                    continue
                if not (re.search(sz["cel"], ablak, re.I)
                        or (sz.get("cel_tag") and re.search(sz["cel_tag"], ablak, re.I))):
                    continue
                if re.search(sz["cel_kizaro"], ablak, re.I):
                    continue
                return ablak
        return None

    szoveg_maszkolt = maszkol(uzenet_szoveg)

    for sz in SZABALYOK:
        if cimzett and cimzett not in sz["tiltott_agensek"]:
            continue
        # KET SCAN: eloszor a MASZKOLT szovegen (ott csak VALODI keres tuzelhet), aztan a
        # nyerson -- az utobbi csak figyelmeztetesre jo.
        valodi = tuzel_e(sz, szoveg_maszkolt)
        if not valodi:
            idezett = tuzel_e(sz, uzenet_szoveg)
            if idezett:
                print(f"[delegalt-iras-tiltas-kapu] FIGYELMEZTETES: a szovegben van olyan reszlet, "
                      f"ami iras-keresnek LATSZIK, de IDEZETBEN all, ezert nem blokkolok. "
                      f"Ha ez megis valodi keres, fogalmazd at idezojel nelkul. "
                      f"A talalat: {idezett.strip()[:160]}", file=sys.stderr)
            continue
        # A kapu NEVEZZE MEG MAGAT. Ok (2026-09-16, mert eset): Bit ket kulonbozo kaputol kapott
        # blokkolast ugyanazon a napon, es MINDKETTOT a self-pace-gate-nek tulajdonitotta -- mert
        # tobb kapunk uzenete is a "KAPU:" szoval kezdodik, tehat a prefix nem kulonbozteti meg oket.
        # Ebbol egy nem reprodukalhato diagnozis lett, es majdnem egy rossz kapu lazitasa.
        uzenet = (
            f"[delegalt-iras-tiltas-kapu] "
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
