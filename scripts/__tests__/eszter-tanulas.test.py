#!/usr/bin/env python3
"""ESZTER-TANULAS (scripts/eszter-tanulas.py): a heti diff es a kommentek feldolgozasa, szintetikus ket hettel.

  python3 scripts/__tests__/eszter-tanulas.test.py

Az elozo het posztnaptaraban egy FB-cella es egy doksi-mondat Eszter-stilusu javitas ELOTTI alakban all:
  - FB 2. sor: "Nem kell, hogy tökéletes legyen a fotó" -> a heten mar nincs benne (a kapu NEM fogja ezt az alakot: jelolt)
  - FB 3. sor: "egy rövid séta a ház körül" -> "pár perc séta a ház körül" (a kapu NEM fogja: szabaly-jelolt)
  - doksi: "Ha megszereted, ..." mondat kivéve (a kapu fogja), es ket uj, Eszter-sajat mondat: "A jó hír, ..." (JELEZ) es
    egy magaban allo "nem X, hanem Y" (a kuszob, 3, alatt: NEM jelez -- v15.6)
Elvart: a valtozasok megjelennek, a fogott/nem fogott jeloles helyes, a sorszam-elcsuszas (sorbeszuras) nem zavarja a parositast.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ITT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(ITT))
SZKRIPT = os.path.join(REPO, 'scripts', 'eszter-tanulas.py')
TMP = tempfile.mkdtemp(prefix='eszter-tanulas-teszt-')
ok = bad = 0


def check(nev, cond, reszlet=''):
    global ok, bad
    if cond:
        ok += 1
        print('ok    - ' + nev)
    else:
        bad += 1
        print('BUKIK - ' + nev + (f' :: {reszlet}' if reszlet else ''))


def xlsx(ut, fb_sorok, ig_sorok):
    """Minimalis ket-fulu xlsx inline stringekkel (a valodi exportban sharedStrings van; a beolvaso mindkettot olvassa)."""
    def lap(sorok, osz):
        x = ['<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
        for n, sor in enumerate(sorok, start=1):
            x.append(f'<row r="{n}">')
            for col, v in sor.items():
                v = v.replace('&', '&amp;').replace('<', '&lt;')
                x.append(f'<c r="{col}{n}" t="inlineStr"><is><t xml:space="preserve">{v}</t></is></c>')
            x.append('</row>')
        return ''.join(x) + '</sheetData></worksheet>'
    with zipfile.ZipFile(ut, 'w') as z:
        z.writestr('xl/workbook.xml', '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Posztnaptár Facebook" sheetId="1" r:id="rId1"/><sheet name="Posztnaptár Instagram" sheetId="2" r:id="rId2"/>'
                   '</sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Target="worksheets/sheet2.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', lap(fb_sorok, 'G'))
        z.writestr('xl/worksheets/sheet2.xml', lap(ig_sorok, 'G'))


FEJ_FB = {'A': 'Dátum', 'G': 'Poszt szövege', 'I': 'Állapot'}
FEJ_IG = {'A': 'Dátum', 'D': 'Állapot', 'G': 'Diák / kép szövege', 'H': 'Képaláírás'}
P1_REGI = 'Megérkezett a hét 5 receptje! Nem kell, hogy tökéletes legyen a fotó, a lényeg, hogy együtt főzünk.'
P1_UJ = 'Megérkezett a hét 5 receptje! Oszd meg velünk a fotódat, a lényeg, hogy együtt főzünk.'
P2_REGI = 'Ehhez nem kell edzőterem, elég egy rövid séta a ház körül. Te szoktál sétálni?'
P2_UJ = 'Ehhez nem kell edzőterem, elég pár perc séta a ház körül. Te szoktál sétálni?'

for het, sorok in (('W41', [FEJ_FB, {'A': '2026-09-28', 'G': P1_REGI, 'I': 'jóváhagyásra vár'}, {'A': '2026-09-29', 'G': P2_REGI, 'I': 'jóváhagyásra vár'}]),
                   # a heten egy uj sor kerult a ket regi ELE (sorbeszuras): a sorszamok elcsusznak, a parositas datum szerint megy
                   ('W42', [FEJ_FB, {'A': '2026-09-27', 'G': 'Egy teljesen új poszt a hét elejére.', 'I': 'tervezet'},
                            {'A': '2026-09-28', 'G': P1_UJ, 'I': 'időzítve'}, {'A': '2026-09-29', 'G': P2_UJ, 'I': 'időzítve'}])):
    d = os.path.join(TMP, het)
    os.makedirs(os.path.join(d, 'docs'))
    xlsx(os.path.join(d, 'posztnaptar.xlsx'), sorok, [FEJ_IG])
DOC_REGI = 'Indul a kihívás.\nHa megszereted, a 21napalatt VIP Klubban együtt haladunk tovább!\nVárunk szeretettel.'
DOC_UJ = 'Indul a kihívás.\nA jó hír, hogy ma este pihenhetsz.\nNem a tökéletes este a cél, hanem a pihentető alvás.\nVárunk szeretettel.'
io.open(os.path.join(TMP, 'W41', 'docs', 'abc.txt'), 'w', encoding='utf-8').write(DOC_REGI)
io.open(os.path.join(TMP, 'W42', 'docs', 'abc.txt'), 'w', encoding='utf-8').write(DOC_UJ)
io.open(os.path.join(TMP, 'W42', 'docs', 'abc.megjegyzesek.txt'), 'w', encoding='utf-8').write(
    'Found 2 comments:\n\n1. Szigeti-Kovács Eszter (10/15/2026)\n   Anchored to: "p&#246;r&#246;gj&#246;n a fejed,"\n'
    '   Comment: mivaaaaaan? ez mi?\n   └─ Inno Nova (10/15/2026): Javítva: „hogy ne a napi teendőkön járjon az eszed”.\n   Comment ID: X1\n\n'
    '2. Inno Nova (10/15/2026)\n   Anchored to: "valami"\n   Comment: ez Nova sajat kommentje, nem Eszteré\n   Comment ID: X2\n')
io.open(os.path.join(TMP, 'W42', 'posztnaptar.reviziok.txt'), 'w', encoding='utf-8').write('- 900: 2026-10-14T10:00:00Z by esyti5\n')

r = subprocess.run([sys.executable, '-I', SZKRIPT, '--het', os.path.join(TMP, 'W42'), '--elozo', os.path.join(TMP, 'W41')],
                   capture_output=True, text=True)
ki = r.stdout
check('a szkript lefut (exit 0)', r.returncode == 0, r.stderr[-400:])
check('Eszter kommentje bent van, a kapu fogja (G-porog-a-fej)', re.search(r'pörögjön a fejed.*G-porog-a-fej', ki) is not None)
check('Nova sajat kommentje NEM kerul a listaba', 'ez Nova sajat kommentje' not in ki)
check('a posztnaptar: Eszter-revizio a heten = igen', 'Eszter-revízió a héten: igen' in ki)
# a kapu a "nem kell tökéletesen/tökéletesnek" alakot fogja, a "Nem kell, hogy tökéletes legyen" valtozatot NEM
# (merve 2026-10-15; a 09-28-i jovahagyott FB-poszt pont ezt tartalmazza) -> a szkriptnek ezt jeloltkent kell adnia
check('FB 09-28: a "Nem kell, hogy tökéletes legyen" kivetel latszik, a kapu NEM fogja -> szabaly-jelolt',
      re.search(r'Facebook \d+\. sor, 2026-09-28.*\| Nem kell, hogy tökéletes legyen(?: <br>.*?)? \| Oszd meg velünk \| \*\*NEM\*\*', ki) is not None
      and re.search(r'^- \(1x\) „Nem kell, hogy tökéletes legyen”', ki, re.M) is not None,
      '\n'.join(l for l in ki.splitlines() if '09-28' in l))
check('FB 09-29: "egy rövid" -> "pár perc" csere latszik, a kapu NEM fogja', re.search(r'2026-09-29.*\| egy rövid(?: <br>.*?)? \| pár perc \| \*\*NEM\*\*', ki) is not None,
      '\n'.join(l for l in ki.splitlines() if '09-29' in l))
check('a sorbeszuras (uj 09-27-es poszt) nem jelenik meg javitaskent', '2026-09-27' not in ki)
check('a sorszam a HETI tablabol jon (FB 3. sor = 09-28)', 'Facebook 3. sor, 2026-09-28' in ki)
check('doksi: a "Ha megszereted" mondat kivetele latszik, a kapu fogja', re.search(r'doksi: abc.*Ha megszereted.*G-ha-megszereted', ki) is not None,
      '\n'.join(l for l in ki.splitlines() if 'doksi' in l))
check('szabaly-jelolt: "egy rövid" (2 szo, nem fogott) a javaslat-listaban', re.search(r'^- \(1x\) „egy rövid”', ki, re.M) is not None)
# a ket uj mondat EGY valtozas-darabba kerul, tehat egy tulszigoru-sor all rola; a sor VEGEN a jelzo szabalyok listaja
szig = [l for l in ki.splitlines() if l.startswith('- „A jó hír, hogy ma este')]
szab = szig[0].rsplit(' -- ', 1)[-1] if len(szig) == 1 else ''
check('Eszter sajat (bekerult) "A jó hír" mondatat a kapu JELEZI -> a tulszigoru-gyanu listaban', 'G-jo-hir' in szab, szig)
check('a magaban allo "nem X, hanem Y" NEM jelez ugyanabban a darabban (kuszob 3, egyszer all)',
      len(szig) == 1 and 'tökéletes este' in szig[0] and 'G-nem-x-hanem-y' not in szab, szig)
# --- teljes horgony getComment-fajlbol, es a mar kezelt komment (Copy 20939)
# W43: egy csonka horgonyu komment (a teljes horgony a getComment-fajlban, abban "Nincs szigorú szabály" -> a kapu fogja),
# egy csonka horgony getComment-fajl nelkul (figyelmeztetes), es egy komment, aminek az ID-je mar a tiltolistaban all.
w43 = os.path.join(TMP, 'W43', 'docs')
os.makedirs(w43)
io.open(os.path.join(w43, 'def.txt'), 'w', encoding='utf-8').write('x')
io.open(os.path.join(w43, 'def.megjegyzesek.txt'), 'w', encoding='utf-8').write(
    'Found 3 comments:\n\n1. Szigeti-Kovács Eszter (10/20/2026)\n   Anchored to: "Ez egy hossz&#250; mondat, amit a lista lev&#225;g..."\n'
    '   Comment: ai-os\n   Comment ID: TELJES1\n\n'
    '2. Szigeti-Kovács Eszter (10/20/2026)\n   Anchored to: "Egy m&#225;sik lev&#225;gott mondat, getComment n&#233;lk&#252;l..."\n   Comment: unalmas\n   Comment ID: CSONKA2\n\n'
    '3. Szigeti-Kovács Eszter (10/20/2026)\n   Anchored to: "juk a saj&#225;t esti rutinodat, a Te &#233;bred&#233;sedhez"\n'
    '   Comment: az emberek nem akarnak még több feladatot\n   Comment ID: AAACIy0GnL0\n')
io.open(os.path.join(w43, 'def.komment-TELJES1.txt'), 'w', encoding='utf-8').write(
    'Szigeti-Kovács Eszter (10/20/2026)\nAnchored to: "Ez egy hossz&#250; mondat, amit a lista lev&#225;g, de a v&#233;g&#233;n:\nNincs szigor&#250; szab&#225;ly, &#233;s ennyi."\nai-os\n')
r3 = subprocess.run([sys.executable, '-I', SZKRIPT, '--het', os.path.join(TMP, 'W43')], capture_output=True, text=True)
k3 = r3.stdout
check('teljes horgony: a getComment-fajlbol jon, es a teljes szovegen a kapu fogja (G-nincs-szigoru-szabaly)',
      re.search(r'Nincs szigorú szabály.*G-nincs-szigoru-szabaly', k3) is not None, '\n'.join(l for l in k3.splitlines() if 'hosszú' in l))
check('csonka horgony getComment nelkul: jelolve, es a figyelmeztetes kiirja (1 csonka)', '(csonka)' in k3 and '1 horgony csonka' in k3, k3[-600:])
check('mar kezelt komment-ID (AAACIy0GnL0, a tiltolistaban): "már kezelve", nem jelolt',
      'már kezelve' in k3 and 'AAACIy0GnL0' in k3 and not re.search(r'^- \(1x\) „juk a saját esti', k3, re.M), k3[-800:])
r2 = subprocess.run([sys.executable, '-I', SZKRIPT, '--het', os.path.join(TMP, 'nincs')], capture_output=True, text=True)
check('nem letezo heti mappa -> exit 2', r2.returncode == 2, str(r2.returncode))
shutil.rmtree(TMP, ignore_errors=True)
print(f'\n{ok} sikeres, {bad} bukott')
sys.exit(1 if bad else 0)
