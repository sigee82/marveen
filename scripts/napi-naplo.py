#!/usr/bin/env python3
"""Napi naplo bejegyzes irasa ugy, hogy az idobelyeget a GEP teszi be, ne az agens.

Miert letezik (2026-08-11, Pixel): ket alkalommal irtam le olyan orat, ami nem a
rendszerorabol jott. Eloszor egy jelentesben ("ma 10:05-ig" 09:11-kor -- innen egy
kanban kartyara is atkerult), majd HAROM ORAVAL kesobb, mar a tanulsag ismereteben,
egy naplosorba ("## 11:55" 11:50-kor). Az elso utan az `ads-kartya-orjarat` SKILL.md-jebe
tettem `date` eloirast -- de annak a HATOKORE csak az orjarat volt, a masodik hiba mashol
jott elo. Ez a szkript az egesz naplo-irasra huzza a kaput: a HH:MM-et nem lehet elirni,
mert nem is en adom meg.

ES AMI A ROSSZ ORAT SULYOSABBA TESZI, MINT EGY ELIRT SZAM (Signal merese, 2026-08-11):
a becsult ora a naplo KRONOLOGIAJAT is hamissa teszi. Signal aznapi bejegyzeseit visszamerte a
sajat kimeno uzenetei `created_at` mezojehez: egy "## 09:15"-os sor valojaban 08:37:58-kor kelt
(37 perccel a jovobe), egy "## 08:45"-os 08:24:43-kor (20 perccel). Emiatt a naploban a "09:15"-os
sor a "08:55"-os UTAN all, holott 17 perccel ELOTTE keletkezett -- vagyis ket esemeny sorrendje
megfordult. A sorrendbol pedig OK-OKOZATOT szokas olvasni ("ezt azert tette, mert elotte az
tortent"), tehat egy fel evvel kesobbi elemzes rossz kovetkeztetest von le, es semmi nem jelzi,
hogy baj van. Egy becsult ora nem egy szamot ront el, hanem a tortenetet.

ES A MECHANIZMUS, AMI MIATT EZ NEM MARAD KIS HIBA (Signal, ugyanaznap): A BECSULT ORA VANDOROL
A TARTOSABB TAROLOK FELE. Nem ott marad, ahol keletkezett. Signalnal a naplobol atkerult egy WARM
MEMORIABA (a fizetnivalo-atadasi regiszterbe, amit hetente elovesznek) -- ugyanazzal a 37 perces
elteressel, es EPP AZ AZONOSSAG bizonyitja, hogy masolas tortent, nem ket fuggetlen becsles.
Pixelnel ugyanez jelentes -> kanban kartya iranyban. Vagyis nem ket hiba, hanem EGY hiba es annak
a vandorlasa, es az irany mindig a hitelesebb, tartosabb hely fele mutat: a naplo append-only es
egy nap mulva senki nem nezi, a warm memoriaban viszont fel evig ott ul es egyre hitelesebbnek
latszik. Ez az ellenkezoje annak, ahogy egy hibarol gondolkodni szoktunk (hogy idovel elhalvanyul).
A KAPU HATOKORE EZERT: ez a szkript a NAPLOT vedi, a memoriakat es az inter-agent uzeneteket NEM.
Ott tovabbra is szabaly kell -- Signal megfogalmazasaban: ha memoriaba idopontot irsz, merheto
horgonybol vedd (sajat uzenet `created_at`, level `date` fejlece, vagy egy `date` futtatas); ha
nincs ilyen horgony, akkor NE irj orat, csak datumot.

Hasznalat:
    python3 scripts/napi-naplo.py --agent pixel --cim "Tema" --szoveg "Mi tortent."
    echo "hosszabb szoveg" | python3 scripts/napi-naplo.py --agent pixel --cim "Tema" --stdin

>>> A `--szoveg` ARGUMENTUM A SHELLEN AT ERKEZIK: backtick es dollar-jel benne PARANCS-HELYETTESITES,
    es a shell CSENDBEN URES stringre csereli, amit nem tud lefuttatni. 2026-08-18-an igy tunt el egy
    szo (`planned`) egy bejegyzesbol -- a hibauzenet ("command not found: planned") a shelltol jott,
    NEM a naplobejegyzesre mutatott, es a sor hibatlannak latszott a kimeneten.
    EZERT: minden nem-trivialis szoveghez a `--stdin` + IDEZOJELES heredoc (<< 'XEOF') hasznalando --
    az nem ertelmezi a backticket es a dollart. A `--szoveg` csak rovid, jelnelkuli sorokhoz valo. <<<

A kimeneten megjelenik a tenylegesen beirt idopont, es a szkript VISSZAOLVASSA a sort az
sqlite-bol -- a POST {"ok":true} valasza a kerest nyugtazza, nem a sor tartos megletet.
"""
import argparse, json, pathlib, re, sqlite3, subprocess, sys, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from keparany_szuro import keparany_e

ROOT = pathlib.Path(__file__).resolve().parent.parent
DB = ROOT / 'store' / 'claudeclaw.db'
TOKEN = (ROOT / 'store' / '.dashboard-token').read_text().strip()


def most() -> str:
    """A fali ora a rendszertol, nem az agens fejebol. Europe/Budapest az install zonaja."""
    return subprocess.run(['date', '+%H:%M'], capture_output=True, text=True, check=True).stdout.strip()


def jovobeli_orak(szoveg: str, most_hhmm: str) -> list:
    """A szovegben talalt HH:MM alakok kozul azokat adja vissza, amelyek a MAI oranal kesobbiek.

    MIERT CSAK A JOVOBELI (Nova kikotese, 2026-08-18): egy naplo tele van LEGITIM mult idejű
    orahivatkozassal ("a 08-15-i kikuldes 15:43-kor indult") -- azokra jelezni hamis pozitivot
    gyartana, es a zajos kapu korul megint kialakulna egy kenyelmesebb kerulout. A jovobeli ora
    viszont az, amit NEM lehet legitim modon MERNI: ha 10:31-kor 18:10 all a szovegben, az becsles.
    MIERT FIGYELMEZTETES ES NEM TILTAS: van legitim jovobeli ora is ("a kovetkezo kor 14:00-kor
    fut"), tehat a tiltas hamis pozitivot csinalna -- es pont azt a kenyelmesebb utat nyitna meg,
    amit 2026-08-18-an lezartunk.

    >>> A LEGGYAKORIBB TALALAT-FAJTA A JAVITO BEJEGYZES, ES AZ HELYES. NE HANGOLD RA A SZUROT. <<<
    2026-08-18: Bit megirta a 23 hibas fejlecehez tartozo megfeleltetes-tablat, es ez az ellenorzes
    13 TALALATTAL jelzett ra -- mert egy javito bejegyzes SZUKSEGKEPPEN idezi a rossz orakat. Ha
    tiltana, epp azt a bejegyzes-fajtat allitotta volna meg, amelyik a hibat dokumentalja. Aki kesobb
    "hamis-pozitiv-csokkentest" akar itt, ezeket fogja peldanak venni, es ha rajuk hangolja a szurot,
    a dokumentalt javitasokat neitja el. A sok talalat ITT nem a szuro hibaja, hanem a bejegyzes
    termeszete.

    ISMERT KORLAT (hamis NEGATIV, ejfel korul): a HH:MM-et a MAI naphoz merjuk, tehat 23:50-kor irt
    "00:10" MULTBELINEK latszik (00:10 < 23:50), holott 20 perccel a jovoben van -- ilyenkor NEM
    jelez. Fordítva is all: a napot atlepo fejlec nem csak a sorrendet, hanem a NAPOT is elrontja
    (Bit utolso ot fejlece atlepte az ejfelt, es a naploban ejszakai munka latszik delelott fel 11
    helyett).

    >>> A NAPON ATIVELO ESETRE NE PROBALD MEGJAVITANI EZT A SZUROT -- MAR VAN RA ESZKOZ. <<<
    Elvileg sem megy: a szovegben allo ora mellett NINCS datum, es azt a szovegbol nem lehet
    megbizhatoan kiolvasni, tehat EGY bejegyzesbol az atlepes nem eldontheto. Minden heurisztika,
    amit vegiggondoltunk, rosszabb a mostaninal ("a mosthoz legkozelebbi ertelmezes" a leggyakoribb
    legitim alakot, a mult idejű hivatkozast rontana el; "ha az elteres > 12 ora, forditsd meg" a
    legitim 16:00/20:00-as utemezesekre tevedne). A mostani szuro hamis pozitivja NULLA (10/10 teszt)
    -- egy mukodo detektort aldoznank fel egy olyan esetert, amire mar van masik.
    AMI LEFEDI: Bit sorozat-detektora (msg 6760). Az ejfel-atlepes NEM egy bejegyzesbol lathato,
    a SOROZATBOL igen: a created_at szerinti sorrendben a kezzel irt fejlecnek monoton nonie kell,
    es az atlepes CSOKKENESKENT jelenik meg. A mai adaton mar bizonyitott (bit 23:55 -> 00:35).
    A KET DETEKTOR HATOKORE (es MIKOR hat):
      ez a szuro          -- egy bejegyzes, a JELENHEZ merve, IRAS ELOTT  -> MEGELOZ, de ejfel korul vak
      Bit sorozat-tesztje -- tobb bejegyzes monotonitasa, UTOLAG          -> FELDERIT, atlepest is
    Nem helyettesitik egymast: az egyik meg megallithat egy rossz orat, a masik mar csak megtalalja.
    """
    h, m = (int(x) for x in most_hhmm.split(':'))
    most_perc = h * 60 + m
    talalt = []
    for mo in re.finditer(r'(?<!\d)([01]?\d|2[0-3]):([0-5]\d)(?!\d)', szoveg):
        # KEPARANY, NEM ORA (Reel jelezte 2026-08-28): minden videos bejegyzeseben
        # szerepel 9:16 / 4:5 / 16:9, es a kapu allandoan riasztott ra. A szabaly a
        # kozos modulban all (scripts/keparany_szuro.py) -- ugyanez a memoria-mentes.py-ban
        # is elojott. NEM mond ellent a fenti "javito bejegyzes" figyelmeztetesnek:
        # az idezett VALODI orakat a whitelist nem engedi at, a keparany pedig nem ora.
        if keparany_e(szoveg, mo.group(0), mo.start(), mo.end()):
            continue
        # ha a HH:MM elott 30 karakteren belul DATUM all, az masik naprol szol -> kihagyjuk
        elozmeny = szoveg[max(0, mo.start() - 30):mo.start()]
        if re.search(r'\d{4}-\d{2}-\d{2}|\d{2}-\d{2}', elozmeny):
            continue
        perc = int(mo.group(1)) * 60 + int(mo.group(2))
        if perc > most_perc:
            talalt.append((mo.group(0), perc - most_perc))
    return talalt


# Cirill es gorog betuk, amelyek latin betuvel EGY SZOBAN allnak. Ez a homoglifa
# ujjlenyomata: onmagaban egy cirill szo legitim (idezet, nev), de egy cirill betu
# EGY LATIN SZO KOZEPEN mindig elgepeles -- es a grep vak ra, mert a keresett
# mintat nem talalja meg, es a hianyzo talalat nullanak latszik, nem hibanak.
#
# MIERT KAPU ES NEM SZABALY: 2026-09-20-an egy delelott HAROMSZOR csuszott be a sajat
# szovegembe (egy memoria-fajlba, egy kanban-kommentbe es ebbe a naploba), mindig egy
# magyar szo VEGEN, ahol az ekezetes betu helyere hasonlo alaku cirill kerult. Mind a
# harmat utolag talaltam meg, kulon keresessel. A figyelem nem hianyzott; a LEPES hianyzott.
IDEGEN_BETU_RX = re.compile(r'[\u0400-\u04FF\u0370-\u03FF]')
SZO_RX = re.compile(r'[^\W\d_]+', re.UNICODE)


def homoglifak(szoveg: str) -> list:
    """A vegyes irasrendszeru SZAVAKAT adja vissza: (szo, betu, kodpont, pozicio)."""
    talalatok = []
    for m in SZO_RX.finditer(szoveg):
        szo = m.group()
        idegen = [c for c in szo if IDEGEN_BETU_RX.match(c)]
        if not idegen:
            continue
        # Egy TELJESEN idegen irasrendszeru szo legitim (orosz idezet, gorog jeloles).
        # Csak a KEVEREK gyanus.
        if len(idegen) == len(szo):
            continue
        for c in idegen:
            talalatok.append((szo, c, f'U+{ord(c):04X}', m.start() + szo.index(c)))
    return talalatok


def onteszt() -> int:
    """POST NELKUL vegigfuttatja a szkript sajat utjait.

    MIERT (Signal javaslata, Nova kerese, 2026-08-18): egy szintaktikailag helyes valtoztatas is
    eltorhet FUTASIDOBEN -- ezt a szkriptet epp egy hianyzo `import re` buktatta meg, es az CSAK
    hivaskor derult volna ki, azaz az elso valos naplozason. Amiota ez az EGYETLEN kijelolt
    naplozasi ut, a torese az egesz flottat allitja meg: a szelesebb ut lezarasaval kotelezettseget
    vallaltunk a maradek karbantartasara, es ez annak az olcso resze.
    """
    hibak = []

    def probal(nev, fn):
        try:
            fn()
            print(f'  OK   {nev}')
        except Exception as e:
            print(f'  HIBA {nev}: {e.__class__.__name__}: {e}', file=sys.stderr)
            hibak.append(nev)

    print('napi-naplo.py onteszt (POST nelkul)')

    def t_ora():
        ido = most()
        assert re.fullmatch(r'\d{2}:\d{2}', ido), f'a `date` kimenete nem HH:MM: {ido!r}'
    probal('rendszerora (`date +%H:%M`)', t_ora)

    def t_pozitiv():
        # POZITIV KONTROLL: enelkul a tiszta futas nem bizonyitja, hogy talalni is tudna
        tal = jovobeli_orak('A kor 23:59-kor zarult.', '00:01')
        assert tal, 'a jovobeli orat NEM ismerte fel'
    probal('jovobeli ora felismerese (pozitiv kontroll)', t_pozitiv)

    def t_negativ():
        assert not jovobeli_orak('A kikuldes 00:02-kor indult.', '23:58'), 'multbeli orara jelzett'
        assert not jovobeli_orak('A 2026-08-15-i futas 23:59-kor.', '00:01'), 'datummal elozott orara jelzett'
        assert not jovobeli_orak('A CTR 2,60% es az arany 1:5.', '00:01'), 'nem-ora mintara jelzett'
    probal('hamis pozitiv szures (negativ kontroll)', t_negativ)

    def t_homoglifa_pozitiv():
        # POZITIV KONTROLL A DETEKTORRA, a valodi esetbol: a 2026-09-20-i naplo-cimbol
        # vett szo, cirill `e`-vel a vegen.
        tal = homoglifak('a meropad mer\u0435se rendben')
        assert tal, 'a vegyes irasrendszeru szot NEM ismerte fel'
        assert tal[0][2] == 'U+0435', f'rossz kodpontot jelentett: {tal[0]}'
    probal('homoglifa felismerese (pozitiv kontroll)', t_homoglifa_pozitiv)

    def t_homoglifa_negativ():
        assert not homoglifak('teljesen tiszta magyar szoveg ekezettel: arvizturo'), 'tiszta szovegre jelzett'
        assert not homoglifak('arvizturo tukorfurogep, arjegyzek, elohivas'), 'ekezetes magyarra jelzett'
        # Egy TELJESEN cirill szo nem homoglifa, hanem idezet:
        assert not homoglifak('a forras szerint \u043f\u0440\u0438\u0432\u0435\u0442 volt a szo'), 'tiszta cirill szora jelzett'
        assert not homoglifak('a 42 es a 3,14 nem szo'), 'szamra jelzett'
    probal('homoglifa hamis pozitiv szures (negativ kontroll)', t_homoglifa_negativ)

    def t_token():
        assert TOKEN, 'ures dashboard-token'
    probal('dashboard-token olvashato', t_token)

    def t_db():
        con = sqlite3.connect(DB)
        try:
            con.execute('SELECT COALESCE(MAX(id), 0) FROM daily_logs WHERE agent_id=?', ('__onteszt__',)).fetchone()
        finally:
            con.close()
    probal(f'sqlite olvasas ({DB.name}, daily_logs)', t_db)

    if hibak:
        print(f'ONTESZT BUKOTT: {len(hibak)} lepes ({", ".join(hibak)})', file=sys.stderr)
        return 1
    print('ONTESZT RENDBEN: 7/7 lepes. Iras NEM tortent.')
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--agent')
    ap.add_argument('--cim', help='A bejegyzes temaja (a "## HH:MM -- " utan jon)')
    ap.add_argument('--onteszt', action='store_true',
                    help='POST nelkul vegigfuttatja a sajat utjait, majd kilep')
    ap.add_argument('--szoveg', default=None)
    ap.add_argument('--stdin', action='store_true', help='A torzs a stdin-rol jon')
    ap.add_argument('--engedd-a-homoglifat', action='store_true',
                    dest='engedd_a_homoglifat',
                    help='Atengedi a vegyes irasrendszeru szavakat (szandekos idezetnel)')
    a = ap.parse_args()

    if a.onteszt:
        return onteszt()
    if not a.agent or not a.cim:
        print('HIBA: --agent es --cim kotelezo (kiveve --onteszt eseten)', file=sys.stderr)
        return 2

    torzs = sys.stdin.read().strip() if a.stdin else (a.szoveg or '').strip()
    if not torzs:
        print('HIBA: ures torzs (--szoveg vagy --stdin kell)', file=sys.stderr)
        return 2

    ido = most()

    # TORZS-ELLENORZES: a fejlecet a szkript teszi be, de a SZOVEGBEN is lehet becsult ora.
    # Csak figyelmeztet -- a dontes az agense.
    gyanus = jovobeli_orak(a.cim + '\n' + torzs, ido)
    if gyanus:
        print(f'FIGYELEM: a szovegben {len(gyanus)} olyan ora van, ami a mostani {ido}-nal KESOBBI:',
              file=sys.stderr)
        for ora, delta in gyanus:
            print(f'  {ora}  (+{delta} perc a jelenhez kepest)', file=sys.stderr)
        print('  Ha ez becsult ora, javitsd. Ha legitim jovobeli hivatkozas (utemezes, hatarido),'
              ' hagyd -- a bejegyzes ettol fuggetlenul elment.', file=sys.stderr)

    # HOMOGLIFA-KAPU. Ez MEGALLIT, nem figyelmeztet -- ellentetben a fenti ora-jelzessel,
    # aminel a dontes jogosan az agense (egy jovobeli ora lehet legitim hatarido).
    # Itt nincs legitim eset: egy cirill betu EGY LATIN SZO KOZEPEN mindig elgepeles, a
    # javitas egy karakter, es a kar (nema vak folt minden kesobbi keresesben) tartos.
    # Egy figyelmeztetes pont az az alak, amin at szoktam siklani -- ezert kapu.
    hgl = homoglifak(a.cim + '\n' + torzs)
    if hgl and not a.engedd_a_homoglifat:
        print(f'KAPU: {len(hgl)} vegyes irasrendszeru szo a szovegben. A bejegyzes NEM ment el.',
              file=sys.stderr)
        for szo, betu, kod, poz in hgl:
            print(f'  {szo!r}  <- {betu!r} ({kod}) a {poz}. karakteren', file=sys.stderr)
        print('  Ezek latin betunek LATSZANAK, de nem azok: a grep sosem fogja megtalalni oket,'
              ' es a hianyzo talalat nullanak latszik, nem hibanak.', file=sys.stderr)
        print('  Javitsd a betut, vagy ha tenyleg igy akarod: --engedd-a-homoglifat', file=sys.stderr)
        return 3

    content = f'## {ido} -- {a.cim}\n{torzs}'

    # A POST ELOTTI legnagyobb id: enelkul egy ugyanabban a percben, ugyanazzal a cimmel
    # futott KORABBI hivas sora igazolna vissza a mostani (sikertelen) irast -- vagyis pont
    # az ujraprobalkozas eseten adna hamis OK-t, amikor a kapu a legfontosabb.
    con = sqlite3.connect(DB)
    elotte = con.execute('SELECT COALESCE(MAX(id), 0) FROM daily_logs WHERE agent_id=?',
                         (a.agent,)).fetchone()[0]
    con.close()

    req = urllib.request.Request(
        'http://localhost:3420/api/daily-log',
        data=json.dumps({'agent_id': a.agent, 'content': content}).encode(),
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {TOKEN}'},
        method='POST')
    urllib.request.urlopen(req).read()

    # visszaolvasas sqlite-bol, nem az API valaszabol
    con = sqlite3.connect(DB)
    row = con.execute(
        'SELECT id, content FROM daily_logs WHERE agent_id=? ORDER BY id DESC LIMIT 1',
        (a.agent,)).fetchone()
    con.close()

    if not row or row[0] <= elotte or not row[1].startswith(f'## {ido} -- {a.cim}'):
        print(f'HIBA: a sor nem olvashato vissza (idopont {ido}, utolso id elotte {elotte})',
              file=sys.stderr)
        return 1

    print(f'OK: daily_logs id={row[0]}, beirt idopont {ido} (rendszerorabol)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
