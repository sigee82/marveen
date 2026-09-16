#!/usr/bin/env python3
"""SessionStart: szol, ha a fajl-alapu memoria-index a csonkolasi hatar kozeleben all.

MIERT LETEZIK (2026-09-08): a `MEMORY.md` 23 564 bajtnal allt a ~24 KB-os hatar alatt
436 bajttal, es ezt csak azert vettem eszre, mert eppen egy fajlt toroltem belole es
ranezett a szemem a meretre. Ugyanezt a karbantartast 09-06-an mar egyszer kezzel
elvegeztem. Ket kezi javitas ugyanarra a hibara azt jelenti, hogy a hiba VISELKEDESI,
nem tudasbeli -- oda mechanikus kapu kell, nem ujabb feljegyzes.

A CSONKOLAS NEM HIBAUZENET. A limit folott a lista VEGEROL nemán levagott sorok
egyszeruen nincsenek ott, es a hianyzo emlek pontosan ugy nez ki, mint a nem letezo
emlek. 2026-09-02-n ez 235 bejegyzest tett evekre lathatatlanna.

ES AMIERT EPP A SessionStart A HELYE: ez az egyetlen pillanat, amikor az index
betoltodik -- tehat ez az egyetlen pillanat, amikor a figyelmeztetes olyan valakihez
er, aki tud is vele kezdeni valamit. Egy naplosor, amit senki nem olvas, nem jelzes.

HATOKOR -- ES EZT KETSZER IRTAM ROSSZUL EGY ORA ALATT, EZERT ALL ITT RESZLETESEN.

Bit elsore azt mondta, ez a FLOTTA kozos budzseje es masok emlekei tunnek el. Erre en
azt mertem, hogy a flotta-agensek sajat cwd-vel futnak, a slugjukhoz tartozo memory-dir
URES, tehat "ez csak Nova fajlja". MINDKETTO TULLOTT.

Amit tenyleg tudunk (2026-09-08):
- A tanulsagok TULNYOMO resze a SQLite flotta-tarba megy (/api/memories): nova 1563,
  bit 545, pixel 545, signal 231, summa 192. Ott NINCS index-plafon. Ennyiben igazam volt.
- DE Bit sessionje ezt a fajl-vaultot tolti be es irja: a rendszer-promptja szo szerint
  ezt az utat adja meg, menet kozben valtozas-ertesitest kap ra, es az ide irt sorai
  landolnak. Ez harom fuggetlen nyom A SAJAT kontextusabol -- erosebb, mint az en kulso
  kovetkeztetesem. Az o mai harom sora ebbol a budzsebol ment el, es o LATTA is.
- A masik OT agensre (pixel, summa, signal, copy, lumen, reel) EGYIKUNKNEK SINCS MERESE.
  Az inditasi parancsban nincs projekt- vagy memoria-kapcsolo, tehat a futtatokornyezet
  donti el, es azt kivulrol nem olvastam ki.
=> A helyes hatokor: LEGALABB KET session olvassa es irja, a tobbi meretlen. Nem "csak
   Nova", es nem is bizonyitottan "az egesz flotta".

ES A MODSZERTANI HIBA, ami ide vezetett: az URES slug-dir MINDKET hipotezisbol kovetkezik
-- abbol is, hogy Bit a kozos utat tolti be, es abbol is, hogy egyaltalan nem hasznal
fajl-memoriat. Egy nem-megkulonbozteto jelbol vontam le kovetkeztetest. Ami MEGKULONBOZTET:
Bit ma LETREHOZOTT ide egy fajlt. Az csak az elso hipotezissel fer ossze.
"""
import json
import os
import sys

# Az UT PARAMETER, nem bedrotozott konstans -- kulonben a kapu nem probalhato ki
# anelkul, hogy a valodi indexet felduzzasztanank. Ma tanultam meg ujra (a
# branchOnRemote-nal): ha egy dontes minden bemenete nem injektalhato, a dontest
# nem lehet megmerni, csak hinni benne.
M = os.environ.get("MEMORY_INDEX") or os.path.expanduser(
    "~/.claude/projects/-Users-macmini-marveen/memory/MEMORY.md")
LIMIT = 24576
# 85%: nem a hataron szol, hanem amig az archivalas meg nyugodt munka, es nem egy
# mar levagott lista helyreallitasa.
#
# AZ ELORETARTAST NE BEJEGYZES-SZAMBAN ADD MEG (Bit lelete, 10959, es igaza volt).
# Az elso valtozat "kb. 2300 bajt / 15-18 bejegyzes"-t irt ide. A bajt-resz is rossz
# volt (85%-tol a plafonig 3686 B), a bejegyzes-szam meg BECSULT sorhosszbol jott, nem
# mertbol. A valodi meres 2026-09-08-an: 115 index-sor / 19 141 B = 166 B ATLAGOS
# sorhossz, tehat a kuszobig 7-8 bejegyzes fert, nem 15-18. Kb. a fele.
#
# MIERT SZAMIT EGY KOMMENTBEN ALLO SZAM: ebbol TERVEZ a kovetkezo olvaso. Aki azt hiszi,
# ket hete van, nem archival ma -- es a mai delutanon NEGY agens irt ebbe az indexbe.
# A sorhossz ezenfelul agensenkent es korszakonkent valtozik: a ma irt het sor atlaga
# 172 B, a teljes korpusze 166 -- vagyis epp a friss stilus a surubb.
#
# A HELYES ALAK, ha valaki ujraszamolja:
#     meg befer =~ (KUSZOB - jelenlegi meret) / MERT atlagos sorhossz
# Merd meg a sorhosszt, ne becsuld:
#     grep '^- \[' MEMORY.md | wc -c   ->  osztva a sorok szamaval
KUSZOB = int(LIMIT * 0.85)

try:
    b = os.path.getsize(M)
except OSError:
    sys.exit(0)          # nincs index: nem a mi dolgunk, es semmikepp nem hiba

if b > KUSZOB:
    # STDOUT + hookSpecificOutput.additionalContext, NEM stderr (Bit lelete, 10950).
    # Az elso valtozat a stderr-re irt rc=0-val, es ezzel a figyelmeztetes a transcript-
    # nezetbe ment, NEM a modell kontextusaba: a kapu tuzelt, es senki nem latta. Pontosan
    # az az alak, amit ez a kapu megelozni hivatott -- es amirol a fenti docstringben magam
    # irtam, hogy "egy naplosor, amit senki nem olvas, nem jelzes".
    #
    # A TANULSAG NEM A CSATORNA, HANEM HOGY MEG SEM NEZTEM: ugyanebben a mappaban KET mukodo
    # SessionStart hook all (taskstate-replay.py 108-113, ledger-replay.py 176-178, 248), es
    # mindketto igy ad at. Volt ket peldam a helyes kezbesitesre, es egyiket sem olvastam el.
    uzenet = (
        f"[memoria-index] FIGYELEM: MEMORY.md {b} B / {LIMIT} B ({round(b / LIMIT * 100)}%). "
        f"A hatar folott a lista VEGE nemán levagodik, es a levagott emlek ugy nez ki, "
        f"mint a nem letezo. TEENDO: a `## Legfrissebb bejegyzesek` lista LEGREGIBB ~30 sora "
        f"a MEMORY-korabbi.md vegere. A KAPU A HALMAZ-DIFF, nem a darabszam: "
        f"`cat MEMORY.md MEMORY-korabbi.md | grep '^- \\[' | sort` a ket allapotra, aztan diff -- "
        f"a darabszam akkor is stimmel, ha egy sor elveszett es egy masik duplikalodott."
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": uzenet,
        }
    }, ensure_ascii=False))
    sys.stdout.flush()
sys.exit(0)
