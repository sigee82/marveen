#!/usr/bin/env python3
"""INGYENES-KIHIVAS LANDING: SZOVEG-KAPU a mert korpusz ellen.

MIERT LETEZIK (2026-09-21, Zsolt: "ebbol majd legyen valami tanulsag es szabaly ...
mert ez elegge felrement"):
Az `ingyenes-kihivas-landing-havi` skillben 2026-09-15 ota ott all a HANG-PROFIL es az
OT LANDING teljes korpusza -- es a 2026.10-es egeszseges reggeli landing szovege MEGIS
elteret a hangtol. A referencia LETEZETT, csak semmi nem MERT hozza.

>>> A SZERKEZETI OK, es ezert nem eleg egy ujabb feljegyzes: a skill eljarasa azt felteszi,
>>> hogy a landing A MI LANCUNKON keszul (nova -> copy -> bit). A 2026.10-es oldalt a
>>> TULAJDONOS rakta ki maga, tehat a "copy megkapja a ket referencia-fajlt" lepes SOSEM
>>> FUTOTT LE -- es a 9. pont visszamerese csak a MECHANIKAT nezte (slug, urlap, mobil,
>>> platform), a SZOVEGET nem. A hiany tehat nem tudas-hiany volt, hanem egy hianyzo LEPES. <<<

AMIT EZ A KAPU MER, ES AMIT NEM:
  MER (szamokat ad, nem velemenyt): nagykotojel-darabszam; elettani/orvosi szokincs;
  a szerzo sajat szava; a hero bullet-minta; az "Imadni fogod" lista kozpontozasa;
  az allando blokkok megletet (CTA-k, "Miert eppen 7 nap?", VIP Klub leiras);
  a nyeremenyjatek-platform fejlec/torzs egyezeset.
  NEM MERI, es ezt ki kell mondani: hogy a szoveg JO-E. Egy mondat lehet hibatlanul
  korpusz-konform es kozben gyenge. A kapu a MERHETO elterest fogja meg, hogy az
  emberi/agensi figyelem a tobbire maradjon.

FUTTATAS:
  python3 scripts/kihivas-landing-szoveg-kapu.py                      # az elo /ingyenes-kihivas/
  python3 scripts/kihivas-landing-szoveg-kapu.py --url <URL>
  python3 scripts/kihivas-landing-szoveg-kapu.py --fajl <szoveg.txt>  # meg nem publikalt draft
Kilepesi kod: 0 = nincs mert elteres, 1 = van, 2 = a meres maga nem futott le (vak).
"""
import argparse, html, io, os, re, subprocess, sys

KORPUSZ = os.path.expanduser(
    "~/.claude/skills/ingyenes-kihivas-landing-havi/references/landing-korpusz.md")
ELO_URL = "https://vip.21napalatt.hu/ingyenes-kihivas/"

# Mind a hat CTA, szo szerint, a mert sorrendben. Ezek ALLANDOK.
CTA = ["Én is kipróbálom", "Már megyek is", "Vágjunk bele, csatlakozom",
       "Wow, erre rámegyek", "Naná, regisztrálok is", "Itt a helyem, regisztrálok"]
# Elettani/orvosi mechanizmus-szokincs, SZOTOKENT. A korpusz ot landingjen MIND NULLA
# (ujramerve 2026-09-21: a lenti tizenketto egyike sem fordul elo benne).
#
# MIERT SZOTO ES NEM TELJES SZO (2026-09-21, az elo lap fogta meg a kaput, nem forditva):
# a lap "vércukrodat"-ot ir, es a magyar ragozas KIEJTI a tovegi o-t -- a "vércukor" tehat
# NEM reszsztringje. Mind a nyolc regi minta NULLAT adott egy olyan szovegen, amiben ket
# elettani fordulat all ("vércukrodat", "IR-barátok"). A nulla nem lelet volt, hanem vaksag.
ORVOSI = ['vércuk', 'inzulin', 'hormon', 'anyagcser', 'glikém', 'ketóz', 'gyullad',
          'immunrendszer', 'IR-barát', 'rezisztenc', 'glükóz', 'ketogén']
ALLANDO = {
    "Miert eppen 7 nap blokk": "gyakorlás törvénye kimondja",
    "VIP Klub leiras": "teljes hozzáférést ad a klub minden tartalmához",
    "nem meregtelenito kizaras": "Ez nem egy méregtelenítő",
    "hero ingyenes-sor": "a kihívás teljesen ingyenes",
}


# --- ELETTANI FORDULAT: JELZES, NEM TILTAS (2026-09-21, Nova/Eszter dontese) ---------------
# Eszter 13:10-kor KERTE az IR-pozicionalast ("sokkal fontosabb, hogy IR barat es a cel a
# vercukor egyensuly megtartasa"), tehat a keret SZANDEKOS. A mintak MEGIS bennmaradnak:
# ha kivennenk oket, a kapu a MECHANIZMUS-magyarazatra is vakka valna, az pedig tovabbra is
# tiltott. A hatar HAROM AGU, es a kozepso ketto nem dontes kerdese:
#   POZICIONALAS   IGEN  -- "IR-barát", "segítsen egyensúlyban tartani a vércukrodat"
#   MECHANIZMUS    NEM   -- "a vércukor felszalad, majd leesik" (reggel epp kivettuk)
#   IGERT EREDMENY NEM   -- felteteles alak kell ("segítsen", nem "le fog menni")
# A ketto gepileg nem valaszthato szet megbizhatoan (ugyanazokat a szotoveket hasznaljak),
# az ember viszont ranezesre eldonti. Ezert a kimenet a MONDATOKAT adja at, nem verdiktet:
# "amit a kapu kikenyszerit, az csak olyan allitas lehet, ami nem dontes kerdese".
# A `\w+` ELOL KOTELEZO: igy a "hetente"/"hetven" nem illeszkedik (azok "het"-tel KEZDODNEK),
# az "elkeszithetoek" viszont igen. A `\w*` HATUL azert kell, mert a kepzo utan meg jon szoveg.
# ES NEM NYERS STRINGBEN, EKEZETTEL: az elso valtozat r'' -ben irt \u00ed-t hasznalt, ami NEM
# karakter, hanem hat betu -- a 'segit' ag ezert SOSEM illeszkedett volna. Megmerve alul.
FELTETELES = re.compile('\\w+(hat|het)\\w*|\\b(segít\\w*|lehet\\w*|támogat\\w*|hozzájárul\\w*)\\b', re.I)


# A FELTETELES-DETEKTOR SAJAT KONTROLL-KESZLETE. Minden futasnal lefut, mert egy regex,
# ami SEMMIT nem fog, pontosan ugy nez ki, mint egy szoveg, amiben nincs felteteles alak.
# (Az elso valtozatom r'' -ben irt `\u00ed`-t, ami hat betu es nem karakter -- a "segit" ag
# SOSEM illeszkedett volna, es ez a kimeneten sehol nem latszott volna.)
FELTETELES_KONTROLL = [
    ('segítsen egyensúlyban tartani a vércukrodat', True),
    ('hogy IR-barátok, táplálóak és reggel is reálisan elkészíthetőek legyenek', True),
    ('a vércukor felszalad, majd leesik, és ez a hullámvasút csinálja', False),
    ('a vércukrod le fog menni és megszűnik az éhségroham', False),
    ('hetente kapsz egy hetven perces videót', False),
]


def felteteles_kontroll_ok():
    """(rendben?, hibas esetek). A pozitiv ES a negativ ag is szerepel benne."""
    rossz = [sz for sz, vart in FELTETELES_KONTROLL
             if bool(FELTETELES.search(sz)) != vart]
    return not rossz, rossz


def elettani_mondatok(szoveg):
    """A szotoveket tartalmazo MONDATOK, jelzesekkel egyutt. Nem minosit, atad."""
    ki = []
    for mondat in re.split(r'(?<=[.!?])\s+', szoveg):
        talalt = [k for k in ORVOSI if re.search(re.escape(k), mondat, re.I)]
        if talalt:
            ki.append({'mondat': mondat.strip(), 'szotovek': talalt,
                       'felteteles': bool(FELTETELES.search(mondat))})
    return ki


def szoveg_urlbol(url):
    """(olvashato szoveg, NYERS html) -- a nyerset a nagykotojel-szetvalasztas hasznalja.

    MIERT KELL A NYERS IS: a `wptexturize` ENTITASKENT irja ki a maga nagykotojelet
    (`&#8211;`), a beirt/tarolt nagykotojel viszont NYERS UTF-8 karakterkent all. A
    `html.unescape` a kettot egyforma betuve teszi -- vagyis pont azt az informaciot
    dobja el, amitol a lelet eldontheto lenne.
    """
    r = subprocess.run(["curl", "-sL", url], capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        return None, None
    nyers = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", r.stdout)
    s = html.unescape(re.sub(r"(?s)<[^>]+>", "\n", nyers))
    return "\n".join(x.strip() for x in s.split("\n") if x.strip()), nyers


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=None)
    ap.add_argument("--fajl", default=None)
    a = ap.parse_args()

    if not os.path.exists(KORPUSZ):
        print(f"VAK MERES: nincs korpusz itt: {KORPUSZ}"); return 2
    korp = io.open(KORPUSZ, encoding="utf-8").read()

    if a.fajl:
        if not os.path.exists(a.fajl):
            print(f"VAK MERES: nincs ilyen fajl: {a.fajl}"); return 2
        t = io.open(a.fajl, encoding="utf-8").read(); forras = a.fajl; nyers = None
    else:
        forras = a.url or ELO_URL
        t, nyers = szoveg_urlbol(forras)
        if not t:
            print(f"VAK MERES: a(z) {forras} nem toltodott le."); return 2

    # POZITIV KONTROLL: a mero lat-e egyaltalan. Ha a korpuszban NEM talalja a sajat
    # horgonyait, akkor a lenti nullak nem leletek, hanem romlott meres.
    if korp.count("gyakorlás törvénye kimondja") < 3 or korp.count("Én is kipróbálom") < 3:
        print("VAK MERES: a korpusz nem hordozza a sajat horgonyait -- a mero romlott el.")
        return 2

    ok, rossz = felteteles_kontroll_ok()
    if not ok:
        print('VAK MERES: a felteteles-detektor kontroll-keszlete elbukott ezeken:')
        for x in rossz:
            print(f'  - {x}')
        print('  A lenti elettani jelzes ezert nem megbizhato.')
        return 2

    print(f"FORRAS: {forras}   ({len(t)} karakter)")
    print(f"KORPUSZ: {KORPUSZ}")
    print()
    leletek = []

    # 1. nagykotojel -- KET KULON FORRASBOL, ES CSAK AZ EGYIK LELET
    #
    # 2026-09-21-en megmerve (Bit), es ezert nem egy szam all itt, hanem ketto:
    # a `wptexturize` MINDEN szokozok kozotti kotojelbol nagykotojelet csinal a
    # MEGJELENITESKOR, `&#8211;` ENTITASKENT. A szokoz nelkulihez ("meregtelenito-",
    # "ketto-harom") nem nyul. Vagyis az elo oldalon allo nagykotojelek tulnyomo resze
    # NEM a szovegben keletkezett: az iras sima kotojelet tarol, a WordPress rajzolja at.
    # Az elso valtozat ezeket EGYBEN szamolta, es igy a kapu SOHA nem tudott nullara menni:
    # a cim-elvalaszto es a lablec allandoan hozott harmat, barmilyen tiszta a copy.
    # A ket forrast az ALAK valasztja szet: entitas = a render csinalta, nyers UTF-8 = tarolt.
    em = t.count("—")
    ken, kem = korp.count("–"), korp.count("—")
    if nyers is not None:
        tarolt = nyers.count("–")
        renderelt = len(re.findall(r"&(?:#8211|#x2013|ndash);", nyers))
        print(f"NAGYKOTOJEL-BONTAS: {tarolt} tarolt (nyers UTF-8) + {renderelt} renderelt "
              f"(&#8211;, a wptexturize csinalta szokozok kozotti kotojelbol).")
        print()
        if tarolt or em:
            leletek.append(f"NAGYKOTOJEL A TAROLT SZOVEGBEN: {tarolt} db '–' es {em} db '—'. "
                           f"A korpusz ot landingjen: {ken} es {kem}. A korpusz ugyanezt a "
                           f"fordulatot SIMA KOTOJELLEL hozza "
                           f"('Mit együnk ma? - ismerős a kérdés?').")
            for sor in t.split("\n"):
                if ("–" in sor or "—" in sor) and len(sor) > 40:
                    leletek.append(f"    -> {sor[:130]}")
        if renderelt:
            print(f">>> ES AMI NEM LELET: a {renderelt} renderelt nagykotojel a WordPress "
                  f"kimeneti szurojenek a muve, nem a szovege. Szoveg-csereval NEM tunik el "
                  f"-- a tarolt ertek mar most is sima kotojel. Aki ezeket 'javitja', olyan "
                  f"cserét futtat, ami nem valtoztat semmit, es sikernek latszik.")
            print()
    else:
        # FAJL-MOD: itt nincs render, tehat a szetvalasztas nem elvegezheto. Ami MERHETO:
        # a szokozok kozotti kotojelbol a kihelyezes utan nagykotojel LESZ.
        en = t.count("–")
        if en or em:
            leletek.append(f"NAGYKOTOJEL: {en} db '–' es {em} db '—' a szovegben. "
                           f"A korpusz ot landingjen: {ken} es {kem}.")
            for sor in t.split("\n"):
                if ("–" in sor or "—" in sor) and len(sor) > 40:
                    leletek.append(f"    -> {sor[:130]}")
        lesz = len(re.findall(r"(?<=\s)-(?=\s)", t))
        if lesz:
            print(f"ELORETEKINTES: {lesz} db szokozok kozotti kotojel van a draftban. "
                  f"Mindegyikbol NAGYKOTOJEL lesz, amint az oldal kimegy (wptexturize). "
                  f"Ez nem lelet itt, de az elo oldalon annyival tobb '–' fog latszani.")
            print()

    # 2. elettani szokincs -- JELZES, NEM LELET (lasd a FELTETELES melletti szakaszt)
    mondatok = elettani_mondatok(t)
    if mondatok:
        print(f">>> DONTENDO, NEM HIBA: {len(mondatok)} elettani fordulat all a lapon.")
        print("    Eszter 2026-09-21-en KERTE az IR-pozicionalast, tehat a keret szandekos.")
        print("    A hatar: POZICIONALAS igen | MECHANIZMUS-magyarazat nem | IGERT EREDMENY nem")
        print("    (az utobbi kettohoz felteteles alak kell). Nezd at, melyik agon all:")
        for m in mondatok:
            print(f"      [{'felteteles' if m['felteteles'] else 'NEM FELTETELES'}] "
                  f"({', '.join(k + '*' for k in m['szotovek'])})")
            print(f"        {m['mondat'][:150]}")
        print("    A 'NEM FELTETELES' jelzes NEM verdikt: a minta szuk (-hat/-het, segit,")
        print("    lehet, tamogat, hozzajarul), tehat mas felteteles alakot nem ismer fel.")
        print()

    # 2/b. HOMOGLIFA -- 2026-09-21-en adtam hozza (Nova), Copy leletebol.
    #
    # MIERT ITT, ES MIERT NEM "ELEG ODAFIGYELNI": a landing szovege HOSSZU LANCON
    # utazik, mielott kikerul (Eszter hangja -> Nessa briefje -> Copy fajlja ->
    # inter-agent uzenet -> Bit csere-szkriptje -> _elementor_data). 2026-09-21-en
    # Copy sajat maga vette eszre, hogy az INTER-AGENT UZENETE torzseben a
    # "belefernе" szo vegere CIRILL 'е' (U+0435) kerult, mikozben a LEADOTT FAJLJA
    # tiszta volt. A hiba tehat nem a szovegben keletkezett, hanem az ATADASBAN --
    # es aki az uzenetbol masol, azt viszi ki az elo lapra.
    #
    # ES AMIERT EZ ROSSZABB EGY ELGEPELESNEL: a cirill betu KINEZETRE azonos, tehat
    # az atolvasas nem fogja meg; a grep viszont NEM TALALJA MEG, vagyis utana sem a
    # kapu, sem egy kesobbi csere-szkript nem lat ra ra. A hianyzo talalat pedig NEM
    # hibanak latszik, hanem NULLANAK -- "nincs ilyen sor, nincs mit javitani".
    #
    # A KAPU TEHAT NEM A SZOVEGET VEDI, HANEM AZ ATADAST. Ha ez tuzel, a javitas
    # SOSEM az, hogy atirjuk a szot: a kihelyezes forrasa a FAJL legyen, amin ez a
    # kapu lefutott, soha nem az uzenet, amiben emlitettuk.
    import unicodedata as _ud
    homo = []
    for _i, _ch in enumerate(t):
        if _ch.isalpha() and ord(_ch) > 127 and not _ud.name(_ch, "?").startswith("LATIN"):
            homo.append((_ch, hex(ord(_ch)), _ud.name(_ch, "?"), t[max(0, _i - 30):_i + 30]))
    if homo:
        reszlet = "; ".join(f"{c} ({k}, {n}) itt: ...{sz.strip()}..." for c, k, n, sz in homo[:5])
        leletek.append(f"HOMOGLIFA ({len(homo)} nem-latin betu latin szo kozepen): {reszlet}. "
                       "NE a szoveget javitsd: a kihelyezes forrasa a FAJL legyen, ne az uzenet.")

    # 3. a szerzo sajat szava
    if "állítottam össze" in t and "válogattam össze" not in t:
        leletek.append("SZERZO SAJAT SZAVA: 'allitottam ossze' all a szovegben. A korpuszban "
                       f"'valogattam ossze' {korp.count('válogattam össze')}x, "
                       f"'allitottam ossze' {korp.count('állítottam össze')}x.")

    # 4. allando blokkok
    for nev, horgony in ALLANDO.items():
        if horgony not in t:
            leletek.append(f"HIANYZO ALLANDO BLOKK: {nev} (horgony: '{horgony}').")

    # 5. CTA-gombok
    hianyzo = [c for c in CTA if c not in t]
    if hianyzo:
        leletek.append(f"HIANYZO CTA-GOMB ({len(hianyzo)}/6): {', '.join(hianyzo)}. "
                       f"Ezek szo szerint allandok mind az ot landingen.")

    # 6. "Imadni fogod" lista kozpontozasa
    sorok = t.split("\n")
    ix = [i for i, x in enumerate(sorok) if "Imádni fogod a kihívást" in x]
    if ix:
        pontok = [x for x in sorok[ix[0] + 1:ix[0] + 9] if x]
        vesszos = sum(1 for x in pontok if x.endswith(","))
        if pontok and vesszos < len(pontok) - 1:
            leletek.append(f"LISTA-KOZPONTOZAS: az 'Imadni fogod, ha' {len(pontok)} pontjabol "
                           f"{vesszos} zarul vesszovel. A korpuszban mind a nyolc vesszos, "
                           f"az utolso 'vagy egyszeruen kivancsi vagy...' alakkal.")

    # 7. nyeremenyjatek platform: fejlec kontra torzs
    fej = "Instagram" if re.search(r"Nyerj .{0,80}Instagram nyereményjáték", t) else (
        "Facebook" if re.search(r"Nyerj .{0,80}Facebook nyereményjáték", t) else None)
    torzs = "Instagram" if "Instagram" in t.split("Posztold")[-1][:200] else (
        "Facebook" if "Facebook" in t.split("Posztold")[-1][:200] else None)
    if fej and torzs and fej != torzs:
        leletek.append(f"NYEREMENYJATEK-PLATFORM SZETCSUSZAS: a fejlec {fej}-t ir, a torzs "
                       f"{torzs}-ot. Elo oldalon mar elofordult (2026.08). A resztvevo ket "
                       f"kulon helyre kap utasitast, es a sorsolas alapja vitathato lesz.")
    elif not fej:
        leletek.append("NYEREMENYJATEK-PLATFORM: a fejlecbol nem olvashato ki a platform.")

    if not leletek:
        print("NINCS MERT ELTERES a korpuszhoz kepest.")
        print()
        print(">>> ES AMIT EZ NEM MOND: hogy a szoveg JO. A kapu a MERHETO elterest fogja meg "
              "(kozpontozas, szokincs, allando blokkok, minta) -- azt nem tudja megmondani, hogy "
              "egy mondat meggyozo-e, vagy hogy a zaro vagykep KONKRET jelenetet mutat-e. "
              "Az tovabbra is olvasas kerdese, a korpusz mellett.")
        return 0

    # A DARABSZAM CSAK A VALODI LELETEKET SZAMOLJA, a `->` reszlet-sorokat NEM. Az elso
    # valtozat "7 MERT ELTERES"-t irt NEGY lelethez, mert a harom idezett sort is beleszamolta --
    # vagyis a szam tobbet allitott, mint a lista. Pont az a hibaosztaly, ami ellen a kapu keszult.
    valodi = [x for x in leletek if not x.startswith("    ->")]
    print(f">>> {len(valodi)} MERT ELTERES:")
    for x in leletek:
        print(("  " if x.startswith("    ->") else "  - ") + x)
    print()
    print("A korpusz es a hang-profil: ~/.claude/skills/ingyenes-kihivas-landing-havi/references/")
    return 1


if __name__ == "__main__":
    sys.exit(main())
