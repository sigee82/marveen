#!/usr/bin/env python3
"""ESZTER-TANULAS: a heti javitasaibol szabaly-JAVASLAT Copynak (Zsolt kerese: a szovegkapu "tanuljon Eszter javitasaibol";
Nova 20908). A tiltolistaba (config/szovegszabalyok.json) NEM ir: a dontes Copye.

BEMENET (egy heti mappa, Nova utemezett futasa tolti meg MCP-vel; lasd FUTTATAS a lap aljan):
  <het>/posztnaptar.xlsx                 a Content Plan tabla xlsx-exportja (mindket posztnaptar-ful)
  <het>/posztnaptar.reviziok.txt         (opcionalis) a tabla getRevisions-kimenete, ahogy jott
  <het>/docs/<id>.txt                    az ELMULT HETEN modosult 21napalatt doksik text/plain exportja
  <het>/docs/<id>.megjegyzesek.txt       a doksi listComments-kimenete, ahogy jott
  <het>/docs/<id>.reviziok.txt           a doksi getRevisions-kimenete, ahogy jott
  --elozo <mappa>                        az elozo heti mappa: a cella- es doksi-valtozas ehhez merve

MIT TALAL:
  1. Eszter kommentjei: a horgony (amit kifogasolt), a komment (miert), a valasz (mire csereltuk).
  2. Szoveg-valtozasok az elozo hethez kepest: posztnaptar-cellak es doksik, szoszintu diffel (mi ment ki, mi jott be).
     A tabla nem mondja meg, KI irta at a cellat; a revizio-lista csak azt, hogy Eszter dolgozott-e benne a heten.
  3. Mindkettore lefuttatja a szovegkapu szabalyait:
       a kivett szoveget a kapu NEM fogja      -> szabaly-JELOLT (a kapu nem ismeri ezt a mintat)
       Eszter SAJAT (bekerult) szoveget fogja  -> TUL SZIGORU szabaly gyanu
KIMENET: Markdown (stdout vagy --ki). Exit 0, ha lefutott (talalattol fuggetlenul); 2, ha a bemenet hianyos.
"""
import argparse, datetime, difflib, glob, io, os, re, sys, zipfile
import xml.etree.ElementTree as ET

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'scripts', 'hooks'))
import szovegkapu as K  # noqa: E402

ESZTER = ('Szigeti-Kovács Eszter', 'esyti5')
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
LAPOK = {  # ful -> (szoveg-oszlopok, allapot-oszlop)
    'Posztnaptár Facebook': (('G',), 'I'),
    'Posztnaptár Instagram': (('G', 'H'), 'D'),
}


# ---------------------------------------------------------------- beolvasas
def xlsx_lapok(ut):
    z = zipfile.ZipFile(ut)
    ss = []
    if 'xl/sharedStrings.xml' in z.namelist():
        ss = [''.join(t.text or '' for t in si.iter(M + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M + 'si')]
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rid = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
    ki = {}
    for sh in wb.find(M + 'sheets'):
        cel = rid[sh.get(RNS)].lstrip('/')
        cel = cel if cel.startswith('xl/') else 'xl/' + cel
        sorok = []
        for row in ET.fromstring(z.read(cel)).iter(M + 'row'):
            d = {}
            for c in row.findall(M + 'c'):
                col = re.match(r'[A-Z]+', c.get('r')).group(0)
                if c.get('t') == 'inlineStr':
                    d[col] = ''.join(x.text or '' for x in c.iter(M + 't'))
                    continue
                v = c.find(M + 'v')
                if v is not None:
                    d[col] = ss[int(v.text)] if c.get('t') == 's' else v.text
            sorok.append(d)
        ki[sh.get('name')] = sorok
    return ki


def datum(v):
    v = (v or '').strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', v):
        return v[:10]
    try:
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=float(v))).isoformat()
    except ValueError:
        return v or None


def posztok(xlsx):
    """[(ful, sorszam, datum, allapot, szoveg)] a ket posztnaptar-fulrol."""
    lapok = xlsx_lapok(xlsx)
    ki = []
    for ful, (osz, all_osz) in LAPOK.items():
        if ful not in lapok:
            raise SystemExit(f'HIBA: a {ful!r} ful hianyzik a tablabol ({xlsx}) -- atneveztek? (exit 2)')
        for i, r in enumerate(lapok[ful][1:], start=2):
            sz = '\n'.join((r.get(o) or '') for o in osz).strip()
            if sz:
                ki.append((ful, i, datum(r.get('A')), (r.get(all_osz) or '').strip(), sz))
    return ki


def megjegyzesek(ut):
    """A listComments szoveges kimenete -> [{szerzo, datum, horgony, komment, valaszok:[(szerzo, szoveg)], id}]."""
    t = io.open(ut, encoding='utf-8').read()
    ki = []
    for blokk in re.split(r'(?m)^\s*\d+\.\s+(?=\S.*\(\d{1,2}/\d{1,2}/\d{4}\)\s*$)', t)[1:]:
        fej = blokk.split('\n', 1)[0]
        m = re.match(r'(.*?)\s*\((\d{1,2}/\d{1,2}/\d{4})\)', fej)
        horgony = re.search(r'Anchored to:\s*"(.*?)"\s*$', blokk, re.M)
        komment = re.search(r'Comment:\s*(.*?)(?=\n\s*(?:└─|Comment ID:)|\Z)', blokk, re.S)
        valaszok = re.findall(r'└─\s*(.*?)\s*\(\d{1,2}/\d{1,2}/\d{4}\):\s*(.*?)(?=\n\s*(?:└─|Comment ID:)|\Z)', blokk, re.S)
        cid = re.search(r'Comment ID:\s*(\S+)', blokk)
        ki.append({'szerzo': m.group(1).strip() if m else '?', 'datum': m.group(2) if m else '',
                   'horgony': K.html.unescape(horgony.group(1)) if horgony else '',
                   'komment': ' '.join((komment.group(1) if komment else '').split()),
                   'valaszok': [(a.strip(), ' '.join(b.split())) for a, b in valaszok],
                   'id': cid.group(1) if cid else ''})
    return ki


def eszter_dolgozott(ut):
    """A getRevisions-kimenetbol: van-e Eszter-revizio (es mikor)."""
    if not ut or not os.path.exists(ut):
        return None
    return [s.strip() for s in io.open(ut, encoding='utf-8') if any(n in s for n in ESZTER)]


# ---------------------------------------------------------------- diff
SZO = re.compile(r'\S+')


def szo_diff(regi, uj, kornyezet=2):
    """[(kivett, bekerult, kornyezet)] szoszintu cserek/torlesek/beszurasok."""
    a, b = SZO.findall(regi), SZO.findall(uj)
    ki = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        ki.append((' '.join(a[i1:i2]), ' '.join(b[j1:j2]), ' '.join(a[max(0, i1 - kornyezet):i1])))
    return ki


def valtozasok(regi, uj):
    """[(kivett, bekerult, regi_mondat, uj_mondat)] MONDATSZINTEN: a torolt vagy uj mondat egeszben; egy atirt mondatnal
    (1:1 csere, hasonlosag >= 0.5) a kicserelt szavak, a mondattal egyutt (a kapu mondatonkent mer, Copy mondatot olvas)."""
    a, b = list(K.mondatok(regi)), list(K.mondatok(uj))
    ki = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        ra, rb = a[i1:i2], b[j1:j2]
        if op == 'replace' and len(ra) == len(rb):
            for x, y in zip(ra, rb):
                if difflib.SequenceMatcher(None, x, y).ratio() >= 0.5:
                    for kivett, bekerult, _k in szo_diff(x, y):
                        ki.append((kivett, bekerult, x, y))
                else:
                    ki.append((x, y, x, y))
            continue
        ki.append((' '.join(ra), ' '.join(rb), ' '.join(ra), ' '.join(rb)))
    return ki


def parosit(regi, uj):
    """Posztnaptar: az uj cellat a regi tabla UGYANAZON fulenek, UGYANAZON datumu cellajaval parositja, a leghasonlobbal.
    A sorszam elcsuszhat (sorbeszuras), a datum es a ful nem."""
    index = {}
    for ful, i, d, _all, sz in regi:
        index.setdefault((ful, d), []).append(sz)
    for ful, i, d, all_, sz in uj:
        jeloltek = index.get((ful, d)) or []
        if not jeloltek or sz in jeloltek:
            continue
        legjobb = max(jeloltek, key=lambda r: difflib.SequenceMatcher(None, r, sz).ratio())
        if difflib.SequenceMatcher(None, legjobb, sz).ratio() >= 0.4:   # alatta mas poszt kerult a helyere, nem javitas
            yield (f'{ful.split()[-1]} {i}. sor, {d} ({all_})', legjobb, sz)


# ---------------------------------------------------------------- kapu
def kapu_fog(szabalyok, szoveg, mufaj):
    return sorted({x['szabaly'] for x in K.ellenoriz(szoveg, szabalyok, '21napalatt', mufaj)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--het', required=True)
    ap.add_argument('--elozo', default=None)
    ap.add_argument('--ki', default=None)
    a = ap.parse_args()
    if not os.path.isdir(a.het):
        print(f'HIBA: nincs ilyen heti mappa: {a.het}', file=sys.stderr)
        return 2
    szabalyok, _ = K.betolt()
    sorok = [f'# Eszter javításai -- szabály-javaslat Copynak ({os.path.basename(a.het.rstrip("/"))}, készült {datetime.datetime.now():%Y-%m-%d %H:%M})', '',
             'A tiltólistához ez a lista nem nyúl. A „kapu fogja?” oszlop a mai `config/szovegszabalyok.json` szerint mér.', '']
    jeloltek, szigoru = [], []

    # 1. kommentek
    kom_sorok = []
    for ut in sorted(glob.glob(os.path.join(a.het, 'docs', '*.megjegyzesek.txt'))):
        doc = os.path.basename(ut).split('.')[0]
        for k in megjegyzesek(ut):
            if not any(n in k['szerzo'] for n in ESZTER):
                continue
            fog = kapu_fog(szabalyok, k['horgony'], '*') if k['horgony'] else []
            csere = next((v for s, v in k['valaszok']), '')
            kom_sorok.append(f'| `{doc[:10]}…` | „{k["horgony"][:110]}” | {k["komment"][:160]} | {csere[:160]} | {", ".join(fog) or "**NEM**"} |')
            if k['horgony'] and not fog:
                jeloltek.append(('komment', k['horgony'], k['komment'], doc))
    sorok += ['## 1. Eszter kommentjei a doksikban', '',
              '| doksi | amit kifogásolt (horgony) | a komment | mire cseréltük (válasz) | kapu fogja? |', '|---|---|---|---|---|']
    sorok += kom_sorok or ['| – | nincs Eszter-komment a héten | | | |']

    # 2. valtozasok az elozo hethez kepest
    valt = []
    if a.elozo:
        uj_x, regi_x = os.path.join(a.het, 'posztnaptar.xlsx'), os.path.join(a.elozo, 'posztnaptar.xlsx')
        if os.path.exists(uj_x) and os.path.exists(regi_x):
            for cimke, regi, uj in parosit(posztok(regi_x), posztok(uj_x)):
                valt.append(('posztnaptár', cimke, 'poszt', regi, uj))
        for ut in sorted(glob.glob(os.path.join(a.het, 'docs', '*.txt'))):
            if ut.endswith(('.megjegyzesek.txt', '.reviziok.txt')):
                continue
            elozo = os.path.join(a.elozo, 'docs', os.path.basename(ut))
            if os.path.exists(elozo):
                valt.append(('doksi', os.path.basename(ut)[:-4], '*', io.open(elozo, encoding='utf-8').read(), io.open(ut, encoding='utf-8').read()))
    tabla_eszter = eszter_dolgozott(os.path.join(a.het, 'posztnaptar.reviziok.txt'))
    sorok += ['', '## 2. Szöveg-változások az előző héthez képest', '']
    if not a.elozo:
        sorok.append('Nincs előző heti mappa (`--elozo`), ezért ezen a héten csak a kommentekből tanul; ez a mappa lesz a jövő heti alapvonal.')
    else:
        sorok.append('Posztnaptár: a táblában Eszter-revízió a héten: ' + ('igen' if tabla_eszter else ('nem' if tabla_eszter is not None else 'nincs revízió-lista')) + '. A cella szerzőjét a tábla nem mondja meg.')
        sorok += ['', '| hol | kivett | bekerült | kapu fogja a kivettet? | kapu fogja a bekerültet? |', '|---|---|---|---|---|']
        n = 0
        for hol, cimke, mufaj, regi, uj in valt:
            for kivett, bekerult, rm, um in valtozasok(regi, uj):
                if not re.search(r'\w', kivett + bekerult):
                    continue
                n += 1
                fk = kapu_fog(szabalyok, rm, mufaj) if kivett else []
                fb = kapu_fog(szabalyok, um, mufaj) if bekerult else []
                mondat = f' <br><sub>a mondat: „{rm[:160]}”</sub>' if kivett and rm != kivett else ''
                sorok.append(f'| {hol}: {cimke} | {kivett[:110] or "–"}{mondat} | {bekerult[:110] or "–"} | {", ".join(fk) or ("**NEM**" if kivett else "–")} | {", ".join(fb) or "–"} |')
                if kivett and not fk and len(kivett.split()) >= 2:
                    jeloltek.append(('csere', kivett, f'helyette: {bekerult[:80]}' if bekerult else 'törölve', cimke))
                if bekerult and fb:
                    szigoru.append((um, fb, cimke))
        if not n:
            sorok.append('| – | nincs szöveg-változás | | | |')

    # 3. javaslat
    sorok += ['', '## 3. Javaslat-lista Copynak', '',
              '**a) Szabály-jelöltek** (Eszter kivette vagy kifogásolta, a mai kapu NEM fogja). Ismétlődő minta = erős jelölt:', '']
    gyak = {}
    for _t, szoveg, _ok, _hol in jeloltek:
        kulcs = ' '.join(szoveg.lower().split()[:4])
        gyak.setdefault(kulcs, []).append((_t, szoveg, _ok, _hol))
    for kulcs, L in sorted(gyak.items(), key=lambda x: -len(x[1])):
        t, szoveg, ok, hol = L[0]
        sorok.append(f'- ({len(L)}x) „{szoveg[:140]}” -- {ok[:160]} [{hol}]')
    if not gyak:
        sorok.append('- nincs: minden kivett/kifogásolt szöveget fog a mai kapu')
    sorok += ['', '**b) Túl szigorú gyanú** (Eszter SAJÁT szövegét a kapu megfogná):', '']
    sorok += [f'- „{b[:140]}” -- {", ".join(f)} [{h}]' for b, f, h in szigoru] or ['- nincs']
    sorok += ['', f'Számok: {len(kom_sorok)} Eszter-komment, {len(valt)} változott szöveg, {len(gyak)} szabály-jelölt, {len(szigoru)} túl-szigorú gyanú.']
    ki = '\n'.join(sorok) + '\n'
    if a.ki:
        io.open(a.ki, 'w', encoding='utf-8').write(ki)
        print(a.ki)
    else:
        sys.stdout.write(ki)
    return 0


if __name__ == '__main__':
    sys.exit(main())
