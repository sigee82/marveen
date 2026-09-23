#!/usr/bin/env python3
"""PreToolUse(Bash) kapu: HOMOGLIFA az inter-agent uzenet `content` mezojeben.

MIERT LETEZIK (Copy merese, 2026-09-21, msg 14489)
--------------------------------------------------
Copy EGY NAP alatt HAROM kimeno uzenetebe csusztatott cirill betut, mindet
ekezetes magyar szo kornyeken, es mind a harom AZ O SAJAT KIMENETE volt, nem
relay-hiba:
    U+0435 (e)  a "belefernе"    szoban  -> agent_messages 14429
    U+043A (k)  a "tetelenкenti" szoban  -> agent_messages 14477
    U+0456 (i)  a "kulonіras"    szoban  -> egy memoria-mentesben
A HARMADIKAT MEGFOGTA egy kapu (a memoria-mentes szkripte), az elso kettot
NEM fogta meg semmi -- mert az inter-agent uton NEM VOLT kapu. Nessa ugyanezt
merte a sajat oldalan: nala gepi diff fut a Sheet-iras utan, ezert nem futott
bele. Az o mondata: "a kulonbseg a kapuban van, nem a figyelemben."

MIERT KULON HOOK, ES NEM AZ `outgoing-copy-gate.py` BOVITESE
------------------------------------------------------------
Az a kapu a VEVO fele meno szovegre van hangolva: ekezet-arany, gondolatjel,
dupla kotojel, nev-szabaly. Az inter-agent uzenet SZANDEKOSAN ekezet nelkuli
es tele van technikai tokennel -- ha ra engednenk a teljes auditot, minden
uzenet elbukna, es par nap alatt kikapcsolnank. Ez a hook EGYETLEN dolgot mer.

MIERT EPP A HOMOGLIFA, ES MIERT NEM ELEG AZ ATOLVASAS
-----------------------------------------------------
A cirill betu KINEZETRE azonos a latinnal, tehat a szempar SZERKEZETILEG vak ra.
A grep viszont nem talalja meg -- es a hianyzo talalat NEM hibanak latszik,
hanem NULLANAK: "nincs ilyen sor, nincs mit javitani". Egy inter-agent uzenet
ráadásul tovabbmegy: kartya-kommentbe, skillbe, deploy-jegyzetbe, csere-mintaba.

A MERCE: nem-ASCII BETU, aminek a unicode-neve nem LATIN...-nal kezdodik.
A jel-jellegu karakterek (fok-jel, gondolatjel, tipografiai idezojel) NEM betuk
(`isalpha()` hamis), tehat nem adnak hamis pozitivot -- Nessa merese szerint az
o korpuszaban mind a 6 "gyanus" talalat legitim fok-jel volt (200 °C).

FAIL-OPEN, SZANDEKOSAN: ha a hook barmin elhasal, a kuldes MENJEN. Egy
elnemult inter-agent csatorna dragabb, mint egy atcsuszo homoglifa -- a
javitas a masodik esetben meg lehetseges, az elsoben a munka all meg.
"""
import json
import re
import sys
import unicodedata

# Csak a mi uzenetsorunkra: mas /api/ vegpontok (memoria, naplo, kanban) sajat
# kapuval birnak, vagy nem szoveget kuldenek.
VEGPONT = re.compile(r"/api/messages\b")

# FELULBIRALO (Copy kerese, 2026-09-21): van, amikor a homoglifa MAGA a mondanivalo
# -- epp egy ilyen hibat jelentunk. Egy kapu, ami ezt nem engedi, arra kenyszerit,
# hogy a hibarol ne lehessen pontosan beszelni; onnan mar csak egy lepes kikapcsolni
# az egeszet. A jelzes SZANDEKOSAN a szoveg resze marad (nem kapcsolo): igy a
# kesobbi olvaso a sorban latja, hogy a betu ott AKART lenni.
FELULBIRALO = "[HOMOGLIFA-SZANDEKOS]"


def homoglifak(t):
    ki = []
    for i, ch in enumerate(t):
        if not ch.isalpha() or ord(ch) < 128:
            continue
        nev = unicodedata.name(ch, "")
        if not nev.startswith("LATIN"):
            ki.append((ch, hex(ord(ch)), nev or "?", t[max(0, i - 30):i + 30]))
    return ki


def fajl_payloadok(cmd):
    """A `--data-binary @UT` / `-d @UT` / `--data @UT` alakban hivatkozott FAJLOK tartalma.

    >>> EZ A RESZ COPY MERESEBOL SZULETETT, 2026-09-21, ES EGY VALODI VAK FOLTOT ZART BE. <<<
    Az elso valtozat CSAK a parancs szoveget nezte, es a nyolc kontrollom MIND inline alakot
    hasznalt (heredoc, -d '{...}'). Copy lefuttatott egy pozitiv kontrollt A SAJAT PRODUKCIOS
    UTJAN -- fajlba irt payload + `--data-binary @fajl` --, es AZ ATMENT: a cirill betu
    sertetlenul bekerult az uzenetsorba (id 14495). A kapu tehat pontosan azt a ket alakot
    fogta, amit o NEM hasznal, es azt az egyet nem, amit igen.
    ES A FAJLOS ALAK NEM KIVETEL, HANEM AZ ELOIRT: a CLAUDE.md tiltja a `-d "{...}"` dupla
    idezojeles alakot (a shell behelyettesit benne), ezert allunk at fajlra.

    A TANULSAG, amit Copy fogalmazott meg: a kontrollok SZAMA nem szamit, ha mind ugyanabbol
    a keszletbol jon, amit a kapu iroja elkepzelt. A pozitiv kontrollt a VALODI hivo VALODI
    utjan kell futtatni.

    MEGMARADO KORLAT, KIMONDVA: egy hook a PARANCSOT latja, tehat mindig egy lepessel a
    hivasi alakok mogott jar. A teljes fedes a VEGPONTON van (a szerver a payloadot kapja,
    nem a parancsot) -- az a tartos javitas, ez a mai res betomese.
    """
    ki = []
    for m in re.finditer(r"(?:--data-binary|--data|-d)\s+@([^\s'\"]+)", cmd):
        ut = m.group(1)
        if ut == '-':          # stdin/heredoc: azt a parancs-szoveg mar hordozza
            continue
        try:
            with open(ut, encoding='utf-8', errors='replace') as f:
                ki.append(f.read())
        except Exception:
            continue           # fail-open: nem olvashato fajl nem allit meg kuldest
    return ki


def content_mezok(cmd):
    """A `content` mezok kiszedese, barmilyen alakban is megy a payload.

    Harom utat kell fednie, mert mindharmat hasznaljuk: idezett heredoc
    (--data-binary @- <<'JSON'), fajlbol kuldes (--data-binary @/ut), es a
    python -c json.dumps alak. A heredoc torzse magaban a parancs-stringben
    all, tehat a nyers szovegbol is kell keresni -- ezert a JSON-parse UTAN
    egy regex-es halo is fut.
    """
    ki = []
    for m in re.finditer(r'\{.*?"content"\s*:\s*".*?\}', cmd, flags=re.S):
        try:
            d = json.loads(m.group(0))
        except Exception:
            continue
        if isinstance(d, dict) and isinstance(d.get("content"), str):
            ki.append(d["content"])
    if not ki:
        for m in re.finditer(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', cmd, flags=re.S):
            try:
                ki.append(json.loads('"' + m.group(1) + '"'))
            except Exception:
                ki.append(m.group(1))
    return ki


def main():
    payload = json.load(sys.stdin)
    if str(payload.get("tool_name") or "") != "Bash":
        sys.exit(0)
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    if not VEGPONT.search(cmd):
        sys.exit(0)

    forrasok = list(content_mezok(cmd))
    for payload in fajl_payloadok(cmd):
        forrasok.extend(content_mezok(payload))

    talalatok = []
    for szoveg in forrasok:
        if FELULBIRALO in szoveg:
            continue
        talalatok.extend(homoglifak(szoveg))
    if not talalatok:
        sys.exit(0)

    sorok = [
        f"  - {ch!r} ({kod}, {nev}) itt: ...{kor.strip()}..."
        for ch, kod, nev, kor in talalatok[:6]
    ]
    tobb = f"\n  (+{len(talalatok) - 6} tovabbi)" if len(talalatok) > 6 else ""
    sys.stderr.write(
        "INTER-AGENT HOMOGLIFA KAPU: TILTVA, az uzenet nem mehet ki igy.\n\n"
        f"{len(talalatok)} nem-latin betu all latin szo kozepen:\n"
        + "\n".join(sorok) + tobb + "\n\n"
        "Olvasva lathatatlan, a grepnek viszont mas szo -- es egy inter-agent uzenet\n"
        "tovabbmegy kartya-kommentbe, skillbe, csere-mintaba. Ott a hianyzo talalat\n"
        "nem hibanak latszik, hanem nullanak.\n"
        "JAVITAS, EBBEN A SORRENDBEN (Copy merese, 2026-09-21):\n"
        "  1. HA A HIBAROL BESZELSZ: NE idezd a hibas szot -- NEVEZD MEG a betut es a kodpontot\n"
        "     (pl. 'CIRILL kis ie betu, U+0435'). Ez a jobbik alak, mert egy homoglifat TARTALMAZO\n"
        "     uzenet maga sem grepelheto, es a betu tovabbmasolodik mindenkivel, aki idezi.\n"
        "  2. HA CSAK ELGEPELTED: ird ujra az erintett szot (ne masold vissza ugyanonnan).\n"
        "  3. HA TENYLEG IDEZNED KELL a hibas alakot: tedd bele a szovegbe a\n"
        f"     {FELULBIRALO!r} jelzest -- akkor a kapu atengedi, es a jelzes a sorban is latszik,\n"
        "     tehat a kesobbi olvaso tudja, hogy a betu SZANDEKOS.\n"
    )
    sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        # FAIL-OPEN, de SOHA nem nemán: egy csendben kiesett kapu ugyanaz,
        # mintha ott sem lenne.
        print(json.dumps({"systemMessage":
            f"interagent-homoglifa-kapu: NEM FUTOTT LE ({exc.__class__.__name__}: {exc}). "
            "Az uzenet a homoglifa-ellenorzes NELKUL ment ki."}))
        sys.exit(0)
