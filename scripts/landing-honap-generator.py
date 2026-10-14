#!/usr/bin/env python3
"""HAVI INGYENES-KIHIVAS LANDING: Copy leadott szovegebol a szoveg-csere PHP elkeszitese.

A 2026.10-es lanc (landing-17544-generator.py) egy konkret honapra irodott: bedrotozott
elem-azonositok, Copy JAVITOTT fajljanak (a)-(f) szerkezete, es a 17153 mint tiltott cel.
Ez a valtozat HONAPFUGGETLEN: a honapra szolo ertekek a HONAP blokkban allnak, a tobbit
a MERESBOL es Copy fajljabol veszi.

>>> A PAROSITAS NEM KEZI TABLA, HANEM SORREND + TIPUS + POZITIV KONTROLL. <<<
Copy fajlja megjelenesi sorrendben sorolja a mezoket ("**Heading:**", "**Text-editor:**",
"**Gomb N:**", "**Ikonos lista (N elem):**"), es mindegyiken jeloli, hogy [MARAD] vagy [CSERE].
Az elo oldal mert allapota (`ELO`) ugyanebben a sorrendben adja a widgeteket. A ketto
sorban parosodik, es a TIPUSNAK minden paron egyeznie kell. A pozitiv kontroll a [MARAD]
mezo: annak a szovege BETURE egyezik az elo oldallal -- ha a parositas egy hellyel
elcsuszna, a MARAD mezok nem egyeznenek, es a generator megall. Igy a hat gomb, a harom
allando cim es a 7-10. szekcio maga bizonyitja, hogy a CSERE mezok jo helyre mennek.

>>> A FORMAZAS A MERT HTML VAZABOL JON, NEM KITALALVA. <<<
2026-09-17-en egy sima szoveges iras leszedte a tageket (felsorolas, felkover), es csak a
bongeszoben latszott. Ezert a text-editor uj erteke az elo mezo vazat koveti: ugyanazok a
blokkok (p / li), ugyanazok a burkolok (strong / span), ugyanaz a <br>. Ha Copy sorainak
szama nem illeszkedik a vazhoz, es a vaz NEM csupa sima <p>, a generator megall -- nem
talalgat formazast.

FUTTATAS:  python3 scripts/landing-honap-generator.py [--regi-meres-ok]
Kimenet:   a HONAP blokkban megadott parositas-JSON es szoveg-csere PHP.
"""
import argparse, datetime, hashlib, io, json, os, re, subprocess, sys, tempfile

# ------------------------------------------------------------------ HONAP
HONAP = '2026-11'
COPY_MD = '/Users/macmini/marveen/agents/copy/munka/2026-11-ingyenes-kihivas-landing-szoveg.md'
ELO = '/Users/macmini/marveen/scripts/landing-17544-teljes-allapot.json'
FORRAS_ID = 17544                    # az oldal, amibol a masolat keszul (az elo /ingyenes-kihivas/)
TILTOTT_IDK = [17544, 17153]         # elo es korabbi landingek: ezekre a csere SOSEM ir
PROD_IDEIGLENES = 'novemberi-kihivas-eloke'   # landing-rotacio.php $IDEIGLENES -- egyezzen!
KIZART_WIDGETEK = {'8ce0efc'}        # lablec: nem a landing szovege
# Az oldal CIME (bongeszo-ful, keresok). A korpusz mintaja: "7 napos ingyenes kihivas - <Tema> <EEEE.HH>"
# (elo 17544: "7 napos ingyenes kihívás - Egészséges reggeli 2026.10"; a " - "-bol a wptexturize rajzol "–"-t).
# 2026-10-14-en a dev-elonezeten derult ki, hogy a csere ezt nem vitte: a ful a regi temat irta, a prodon
# pedig a --duplikal belso cime ("... (elokeszites)") maradt volna kint.
UJ_CIM = '7 napos ingyenes kihívás - Pihentető alvás 2026.11'
KI_JSON = f'/Users/macmini/marveen/scripts/landing-{HONAP}-parositas.json'
KI_PHP = f'/Users/macmini/marveen/scripts/landing-{HONAP}-szoveg-csere.php'
SZOVEG_KAPU = '/Users/macmini/marveen/scripts/kihivas-landing-szoveg-kapu.py'
# ------------------------------------------------------------------

NYITO, ZARO = '=== BEMENO-SZOVEG-KEZDETE ===', '=== BEMENO-SZOVEG-VEGE ==='
KOCKAZATOS = '–—‘’“”„…'
HORGONY_MAX, HORGONY_MIN = 80, 25
SZOVEGES = {'heading', 'text-editor', 'icon-list', 'button'}


def hiba(s):
    raise SystemExit('HIBA: ' + s)


def norm(s):
    return re.sub(r'\s+', ' ', s.replace(' ', ' ')).strip()


def h(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def tagtalan(s):
    s = re.sub(r'<(/p|/li|br\s*/?|/h[1-6])\s*>', ' ', s, flags=re.I)
    return norm(re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ').replace('&amp;', '&'))


def horgony(ertek):
    """A mert ertek texturize-biztos prefixe (a 2026.10-es generator szabalya)."""
    vag = len(ertek)
    for ch in KOCKAZATOS:
        i = ertek.find(ch)
        if i != -1:
            vag = min(vag, i)
    hh = ertek[:min(vag, HORGONY_MAX)]
    if len(hh) == HORGONY_MAX and ' ' in hh:
        hh = hh[:hh.rfind(' ')]
    hh = hh.strip()
    if hh == ertek.strip():
        return hh
    if len(hh) < HORGONY_MIN:
        hiba(f'a horgony {len(hh)} karakterre rovidult ("{hh}"). Kezi dontes kell.')
    return hh


# ------------------------------------------------------------------ Copy fajlja
def copy_mezok(szoveg):
    for j in (NYITO, ZARO):
        if szoveg.count(j) != 1:
            hiba(f'a "{j}" jelolo {szoveg.count(j)}-szer szerepel, pontosan 1-et vartam.')
    torzs = szoveg[szoveg.index(NYITO) + len(NYITO):szoveg.index(ZARO)]
    mezok, szekcio, valtozatlan, akt = [], '', False, None

    def lezar():
        if akt is not None:
            while akt['sorok'] and not akt['sorok'][-1].strip():
                akt['sorok'].pop()
            mezok.append(akt)

    for sor in torzs.split('\n'):
        if sor.startswith('## '):
            lezar(); akt = None
            szekcio = sor[3:].strip()
            valtozatlan = '[VÁLTOZATLAN]' in szekcio
            continue
        if sor.strip() == '---':
            lezar(); akt = None
            continue
        m = re.match(r'^\*\*(.+?):\*\*\s*(.*)$', sor.strip())
        if m:
            lezar()
            cimke, maradek = m.group(1).strip(), m.group(2).strip()
            tag = None
            t = re.match(r'^\[([^\]]*)\]\s*(.*)$', maradek)
            if t:
                tag, maradek = t.group(1).strip(), t.group(2).strip()
            if tag is None:
                if not valtozatlan:
                    hiba(f'jeloles nelkuli mezo nem-VALTOZATLAN szekcioban: "{szekcio}" / {cimke}')
                statusz = 'MARAD'
            elif tag.startswith('MARAD'):
                statusz = 'MARAD'
            elif tag.startswith('CSERE'):
                statusz = 'CSERE'
            else:
                hiba(f'ismeretlen jeloles: [{tag}] ({szekcio} / {cimke})')
            if re.match(r'^(\d+\.\s+)?Heading$', cimke):
                tipus, db = 'heading', 1
            elif re.match(r'^(Text-editor|Text)\b', cimke):
                tipus, db = 'text-editor', 1
            elif re.match(r'^Gomb \d+$', cimke):
                tipus, db = 'button', 1
            else:
                mm = re.match(r'^Ikonos lista \((\d+) elem\)$', cimke)
                if not mm:
                    hiba(f'ismeretlen mezo-cimke: "{cimke}" ({szekcio})')
                tipus, db = 'icon-list', int(mm.group(1))
            akt = {'szekcio': szekcio, 'cimke': cimke, 'tipus': tipus, 'db': db,
                   'statusz': statusz, 'sorok': [maradek] if maradek else []}
            continue
        if akt is not None:
            if akt['sorok'] or sor.strip():
                akt['sorok'].append(sor.rstrip())
    lezar()
    # az ikonos listak tetelenkent kulon mezo
    ki = []
    for f in mezok:
        sorok = [s.strip() for s in f['sorok'] if s.strip()]
        if f['tipus'] == 'icon-list':
            if len(sorok) != f['db']:
                hiba(f'{f["szekcio"]} / {f["cimke"]}: {len(sorok)} sor, {f["db"]}-et vartam.')
            for i, s in enumerate(sorok):
                ki.append({**f, 'cimke': f'{f["cimke"]} #{i + 1}', 'egysegek': [s], 'blokkok': [s]})
        else:
            if not sorok:
                hiba(f'ures mezo: {f["szekcio"]} / {f["cimke"]}')
            if f['tipus'] in ('heading', 'button') and len(sorok) != 1:
                hiba(f'{f["szekcio"]} / {f["cimke"]}: {len(sorok)} soros, egyet vartam.')
            blokkok = [norm(b) for b in re.split(r'\n\s*\n', '\n'.join(f['sorok'])) if b.strip()]
            ki.append({**f, 'egysegek': sorok, 'blokkok': blokkok})
    return ki


# ------------------------------------------------------------------ HTML-vaz
def vaz(html_):
    """A mert text-editor HTML blokkjai: [{'tag': p|li, 'szegmensek': [(burkolo, szoveg)]}]."""
    blokkok = []
    for m in re.finditer(r'<(p|li)>(.*?)</\1>', html_, re.S):
        szegm = []
        for sz in re.split(r'\s*<br\s*/?>\s*', m.group(2)):
            sz = sz.strip()
            if not sz:
                continue
            b = re.fullmatch(r'<(strong|b|em|span)((?:\s[^>]*)?)>(.*)</\1>', sz, re.S)
            if b and '<' not in b.group(3):
                szegm.append(('<' + b.group(1) + b.group(2) + '>', b.group(3)))
            elif '<' in sz:
                return None   # osszetettebb belso szerkezet: nem talalgatunk
            else:
                szegm.append(('', sz))
        blokkok.append({'tag': m.group(1), 'szegmensek': szegm})
    return blokkok


def burkol(burkolo, szoveg):
    if not burkolo:
        return h(szoveg)
    nev = re.match(r'<(\w+)', burkolo).group(1)
    return f'{burkolo}{h(szoveg)}</{nev}>'


def osszerak(blokkok):
    ki, ulben = '', False
    for b in blokkok:
        if b['tag'] == 'li' and not ulben:
            ki += '<ul>'; ulben = True
        if b['tag'] != 'li' and ulben:
            ki += '</ul>'; ulben = False
        ki += f"<{b['tag']}>" + ' <br>'.join(burkol(w, s) for w, s in b['szegmensek']) + f"</{b['tag']}>"
    return ki + ('</ul>' if ulben else '')


def editor_html(mert_html, egysegek, blokk_egysegek, cimke):
    """Copy sorai a mert vazba. Visszaad: (html, megjegyzes)."""
    v = vaz(mert_html)
    if v is None or not v:
        hiba(f'{cimke}: a mert HTML vaza nem ertelmezheto: {mert_html[:120]}')
    if tagtalan(osszerak(v)) != tagtalan(mert_html):
        hiba(f'{cimke}: a vazbol visszarakott szoveg nem egyezik a merttel -- a vaz-olvaso hibas.')
    szegm_db = sum(len(b['szegmensek']) for b in v)
    # 1. szegmens-szint: minden <br>-rel elvalasztott resz egy Copy-sor
    if szegm_db == len(egysegek):
        it = iter(egysegek)
        uj = [{'tag': b['tag'], 'szegmensek': [(w, next(it)) for w, _ in b['szegmensek']]} for b in v]
        return osszerak(uj), ''
    # 2. blokk-szint: minden p/li egy Copy-sor; a blokkon beluli <br> elmarad
    if len(v) == len(egysegek):
        uj, megj = [], []
        for b, s in zip(v, egysegek):
            burk = {w for w, _ in b['szegmensek']}
            w = burk.pop() if len(burk) == 1 else ''
            if len(b['szegmensek']) > 1:
                megj.append(f'a "{s[:30]}..." blokkon beluli <br> sortores elmarad')
            uj.append({'tag': b['tag'], 'szegmensek': [(w, s)]})
        return osszerak(uj), '; '.join(megj)
    # 3. csupa sima <p>: nincs formazas, amit elveszithetnenk -> bekezdesenkent <p>
    if all(b['tag'] == 'p' and all(w == '' for w, _ in b['szegmensek']) for b in v):
        uj = [{'tag': 'p', 'szegmensek': [('', s)]} for s in egysegek]
        megj = '' if len(egysegek) == len(v) else f'bekezdes-szam {len(v)} -> {len(egysegek)}'
        return osszerak(uj), megj
    hiba(f'{cimke}: Copy {len(egysegek)} sort ad, a mert vaz {len(v)} blokk / {szegm_db} szegmens, '
         f'es van benne formazas ({mert_html[:120]}). Nem talalgatok: kezi dontes kell.')


# ------------------------------------------------------------------ fo menet
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--regi-meres-ok', action='store_true',
                    help='24 oranal regebbi meres elfogadasa (a PHP futaskor ugyis horgonyt ellenoriz)')
    ap.add_argument('--forras', default=None,
                    help='a szoveg-forras (alapertelmezes: Copy fajlja). 2026-10-14 ota a JOVAHAGYOTT szoveg Eszter '
                         'doksija: landing-doksi-atalakito.py kimenete adhato meg itt.')
    a = ap.parse_args()
    global COPY_MD
    if a.forras:
        COPY_MD = a.forras

    for f in (COPY_MD, ELO, SZOVEG_KAPU):
        if not os.path.exists(f):
            hiba(f'nincs meg: {f}')
    copy_nyers = io.open(COPY_MD, 'rb').read()
    copy = copy_mezok(copy_nyers.decode('utf-8'))
    meres = json.load(io.open(ELO, encoding='utf-8'))
    if str(meres.get('oldal_id')) != str(FORRAS_ID):
        hiba(f'a meres a {meres.get("oldal_id")} oldalrol szol, a forras {FORRAS_ID}.')
    kor = (datetime.datetime.now(datetime.timezone.utc)
           - datetime.datetime.fromisoformat(meres['mikor_utc'].replace('Z', '+00:00'))).total_seconds() / 3600
    if kor > 24 and not a.regi_meres_ok:
        hiba(f'a meres {kor:.0f} oras ({meres["mikor_utc"]}). Merd ujra az elo oldalt, vagy --regi-meres-ok.')
    widgetek = [m for m in meres['mezok'] if m['tipus'] in SZOVEGES and m['id'] not in KIZART_WIDGETEK]

    if len(copy) != len(widgetek):
        for i in range(max(len(copy), len(widgetek))):
            c = copy[i] if i < len(copy) else None
            w = widgetek[i] if i < len(widgetek) else None
            print(f"  {i:2} {c['tipus'] if c else '-':12} {c['cimke'] if c else '':32} | "
                  f"{w['tipus'] if w else '-':12} {w['id'] if w else ''} {(w['szoveg'][:40] if w else '')}")
        hiba(f'Copy {len(copy)} mezot ad, az oldalon {len(widgetek)} szoveges mezo van.')

    parok, marad, bajok, megjegyzesek = [], [], [], []
    for i, (c, w) in enumerate(zip(copy, widgetek)):
        hol = f'#{i} {c["szekcio"][:28]} / {c["cimke"]} <-> {w["id"]} {w["ut"]}'
        if c['tipus'] != w['tipus']:
            bajok.append(f'TIPUS-ELTERES {hol}: Copy {c["tipus"]}, oldal {w["tipus"]}')
            continue
        mert = norm(w['szoveg'])
        if c['tipus'] == 'text-editor':
            copy_sz = norm(' '.join(c['egysegek']))
        else:
            copy_sz = c['egysegek'][0]
        if c['statusz'] == 'MARAD':
            if copy_sz != mert:
                bajok.append(f'MARAD-ELTERES {hol}:\n      Copy:  {copy_sz[:110]}\n      oldal: {mert[:110]}')
            else:
                marad.append({'elem_id': w['id'], 'ut': w['ut'], 'horgony': horgony(mert), 'cimke': c['cimke']})
            continue
        if c['tipus'] == 'text-editor':
            uj, megj = editor_html(w['html'], c['egysegek'], c['blokkok'], hol)
            if megj:
                megjegyzesek.append(f'{w["id"]} ({c["cimke"]}): {megj}')
        else:
            uj = copy_sz
        if tagtalan(uj) == mert:
            marad.append({'elem_id': w['id'], 'ut': w['ut'], 'horgony': horgony(mert), 'cimke': c['cimke']})
            continue
        parok.append({'elem_id': w['id'], 'ut': w['ut'], 'horgony': horgony(mert), 'uj': uj,
                      'cimke': f'{c["szekcio"][:40]} / {c["cimke"]}'})
    if bajok:
        hiba('a parositas nem all meg:\n  - ' + '\n  - '.join(bajok))

    # Az OLDAL vegso szovege, megjelenesi sorrendben: ezen fut a szoveg-kapu.
    vegso = []
    uj_by = {(p['elem_id'], p['ut']): p['uj'] for p in parok}
    for w in widgetek:
        u = uj_by.get((w['id'], w['ut']))
        if u is None:
            vegso.append(norm(w['szoveg']))
        elif w['tipus'] == 'text-editor':
            vegso.extend(tagtalan(x) for x in re.split(r'</p>|</li>|<br>', u) if tagtalan(x))
        else:
            vegso.append(u)
    with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as t:
        t.write('\n'.join(vegso) + '\n')
        oldal_txt = t.name
    r = subprocess.run([sys.executable, SZOVEG_KAPU, '--fajl', oldal_txt], capture_output=True, text=True)
    print('@@ SZOVEG-KAPU az oldal VEGSO szovegen (exit %d):' % r.returncode)
    for s in r.stdout.strip().split('\n'):
        print('@@   ' + s)
    os.unlink(oldal_txt)
    if r.returncode != 0:
        hiba('a szoveg-kapu nem 0-val tert vissza; a generalt PHP NEM keszult el.')

    md5 = hashlib.md5(copy_nyers).hexdigest()
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(COPY_MD)).strftime('%Y-%m-%d %H:%M:%S')
    json.dump({'honap': HONAP, 'forras': {'ut': COPY_MD, 'md5': md5, 'mtime': mtime},
               'meres': {'ut': ELO, 'mikor_utc': meres['mikor_utc']},
               'keszult': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
               'parok': parok, 'marad': marad, 'megjegyzesek': megjegyzesek},
              io.open(KI_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    fej = FEJ.replace('__HONAP__', HONAP).replace('__FORRAS_MD__', os.path.basename(COPY_MD)) \
             .replace('__MD5__', md5).replace('__MTIME__', mtime).replace('__MERES__', meres['mikor_utc'])
    if not UJ_CIM.strip() or "'" in UJ_CIM or '\\' in UJ_CIM:
        hiba('az UJ_CIM ures, vagy aposztrofot/backslasht tartalmaz.')
    konf = (f"$HONAP = '{HONAP}';\n$FORRAS_ID = {FORRAS_ID};\n$UJ_CIM = '{UJ_CIM}';\n"
            f"$TILTOTT = array({', '.join(str(x) for x in TILTOTT_IDK)});\n"
            f"$PROD_IDEIGLENES = '{PROD_IDEIGLENES}';\n")
    io.open(KI_PHP, 'w', encoding='utf-8').write(
        fej + konf + '$PAROK = ' + php_tomb(parok) + ';\n$MARAD = ' + php_tomb(marad) + ';\n' + TORZS)

    print(f'@@ FORRAS: {os.path.basename(COPY_MD)}  md5={md5}  mtime={mtime}')
    print(f'@@ meres: {meres["mikor_utc"]} ({kor:.1f} oras)')
    print(f'@@ {len(copy)} Copy-mezo = {len(widgetek)} oldal-mezo; {len(parok)} VALTOZIK, '
          f'{len(marad)} valtozatlan (a MARAD mezok betura egyeznek -- a parositas nem csuszott el)')
    for p in parok:
        print(f"@@   CSERE {p['elem_id']:9} {p['ut']:18} {p['cimke'][:60]}")
    for m in megjegyzesek:
        print(f'@@ FIGYELEM: {m}')
    print(f'@@ -> {KI_PHP}')
    print(f'@@ -> {KI_JSON}')


def php_tomb(sorok):
    def q(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"
    return 'array(\n' + ',\n'.join(
        '  array(' + ', '.join(f'{q(k)} => {q(v)}' for k, v in s.items()) + ')' for s in sorok) + '\n)'


FEJ = r'''<?php
/**
 * __HONAP__ INGYENES-KIHIVAS LANDING: A SZOVEG BEVITELE.
 * GENERALT FAJL -- ne kezzel szerkeszd: scripts/landing-honap-generator.py.
 * FORRAS: __FORRAS_MD__  md5=__MD5__  mtime=__MTIME__
 * MERT ELO ALLAPOT: __MERES__
 *
 *   --site=dev --oldal=<ID>|jelolt                SZARAZ a deven (semmit nem ir)
 *   --site=dev --oldal=<ID> --apply               ELES a deven: csak a landing-dev-atvitel.php
 *                                                 altal jelolt oldalra ir
 *   --site=prod --oldal=<ID>                      SZARAZ a prodon
 *   --site=prod --oldal=<ID> --apply --yes-prod   ELES a prodon: CSAK a draft, ideiglenes slugu
 *                                                 masolatra (landing-rotacio.php --duplikal), es
 *                                                 csak Zsolt OK-ja utan
 *
 * MIT ELLENORIZ IRAS ELOTT, mezonkent: a VALTOZO mezo jelenlegi erteke a mert horgonnyal
 * kezdodik; a VALTOZATLAN (MARAD) mezok is a mert horgonnyal kezdodnek -- ezek a pozitiv
 * kontroll, hogy jo oldalon, jo allapotban vagyunk. Barmely elteres: SEMMIT nem irunk.
 * A mentes a $HOME-ba megy, NEM a webrootba (a 2026.10-es valtozat a webrootba irta).
 *
 * PROBAPAD: LANDING_CSERE_PROBAPAD=1 + --wp=<gyoker> -- CSAK a hoszt-ellenorzest kapcsolja ki.
 * A cel-orok (tiltott ID, dev-jelolo, prod draft+ideiglenes slug, --yes-prod) probapadon is
 * elnek: azokat pont ott kell tudni kiprobalni, ahol eles iras nem tortenhet.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
'''

TORZS = r'''
$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$YESPROD = in_array('--yes-prod', $ARGV, true);
$SITE = ''; $OLDAL = 0; $WP = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--site=') === 0)  { $SITE = substr($a, 7); }
    if (strpos($a, '--oldal=') === 0) { $OLDAL = substr($a, 8) === 'jelolt' ? -1 : (int) substr($a, 8); }
    if (strpos($a, '--wp=') === 0)    { $WP = rtrim(substr($a, 5), '/'); }
}
$PROBAPAD = getenv('LANDING_CSERE_PROBAPAD') === '1';
function ki($s){ echo '@@ '.$s."\n"; }
/* Probapadon a forras-ID ugyanugy felulirhato, mint a landing-dev-atvitel.php-ban (LANDING_FORRAS),
   kulonben a lokalis atvitel jeloloje (a fixture ID-ja) es ez a szkript kulon vilagban elne. */
if ($PROBAPAD && getenv('LANDING_FORRAS')) { $FORRAS_ID = (int) getenv('LANDING_FORRAS'); }
$HOSTOK = array('dev' => 'dev.21napalatt.hu', 'prod' => 'vip.21napalatt.hu');
if (!isset($HOSTOK[$SITE])) { ki('!! KOTELEZO a --site=dev|prod.'); exit(2); }
if ($WP !== '' && !$PROBAPAD) { ki('!! A --wp csak probapadon (LANDING_CSERE_PROBAPAD=1) adhato meg.'); exit(2); }
if ($WP === '') { $WP = '/home/napalatt/'.$HOSTOK[$SITE]; }
if (!file_exists($WP.'/wp-load.php')) { ki('!! nincs wp-load.php: '.$WP); exit(2); }
require_once $WP.'/wp-load.php';
error_reporting(E_ERROR | E_PARSE);

$host = (string) parse_url(home_url(), PHP_URL_HOST);
ki('LANDING '.$HONAP.' SZOVEG-CSERE  '.gmdate('c').' UTC   site='.$SITE.'  home='.home_url().'  DB='.DB_NAME);
if ($PROBAPAD) { ki('*** PROBAPAD: a hoszt-ellenorzes KI van kapcsolva (a cel-orok elnek). ***'); }
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');
if (!$PROBAPAD && $host !== $HOSTOK[$SITE]) { ki('!! --site='.$SITE.', de ez a telepites: '.$host.'. ALLJ MEG.'); exit(2); }
/* --oldal=jelolt: CSAK a deven, es csak ha PONTOSAN EGY atvitt (jelolt) oldal van. Igy a teljes
   dev-menet (export, import, csere) egy SSH-korben futhat, az uj ID elore ismerete nelkul. */
if ($OLDAL === -1) {
    if ($SITE !== 'dev') { ki('!! Az --oldal=jelolt csak a deven ervenyes.'); exit(2); }
    global $wpdb;
    $j = $wpdb->get_col($wpdb->prepare("SELECT p.ID FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID
        WHERE m.meta_key='_landing_atvitel_forras' AND m.meta_value=%s AND p.post_status NOT IN ('trash','inherit','auto-draft')",
        (string) $FORRAS_ID));
    if (count($j) !== 1) { ki('!! '.count($j).' jelolt oldal van, pontosan egyet vartam. Add meg az ID-t.'); exit(2); }
    $OLDAL = (int) $j[0];
    ki('--oldal=jelolt -> '.$OLDAL);
}
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is. Nem talalgatok.'); exit(2); }
if (in_array($OLDAL, $TILTOTT, true) && $SITE === 'prod') {
    ki('!! A '.$OLDAL.' elo vagy korabbi landing -- NEM irunk ra.'); exit(2);
}
$p = get_post($OLDAL);
if (!$p) { ki('!! a '.$OLDAL.' nem letezik ezen a peldanyon.'); exit(2); }
ki('celpont: '.$OLDAL.'  slug='.$p->post_name.'  status='.$p->post_status.'  cim='.$p->post_title);
{
    if ($SITE === 'dev' && get_post_meta($OLDAL, '_landing_atvitel_forras', true) !== (string) $FORRAS_ID) {
        ki('!! A deven csak a landing-dev-atvitel.php altal atvitt oldalra irok (_landing_atvitel_forras='.$FORRAS_ID.').');
        exit(2);
    }
    if ($SITE === 'prod' && ($p->post_name !== $PROD_IDEIGLENES || $p->post_status !== 'draft')) {
        ki('!! A prodon csak a draft, "'.$PROD_IDEIGLENES.'" slugu masolatra irok. Ez nem az.'); exit(2);
    }
}
if ($APPLY && $SITE === 'prod' && !$YESPROD) { ki('!! Prod iras csak --yes-prod-dal (Zsolt OK utan).'); exit(2); }
ki('');

$d = get_post_meta($OLDAL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$OLDAL.'-on'); exit(2); }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit(2); }

function &km_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings' || !is_array($gy)) { continue; }
        $t =& km_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}
function km_ut_ertek($settings, $ut) {
    $p = $settings;
    foreach (explode('.', $ut) as $r) {
        if (is_array($p) && array_key_exists($r, $p)) { $p = $p[$r]; } else { return null; }
    }
    return is_string($p) ? $p : null;
}
function km_ut_ir(&$settings, $ut, $ertek) {
    $p =& $settings;
    foreach (explode('.', $ut) as $r) {
        if (!is_array($p) || !array_key_exists($r, $p)) { return false; }
        $p =& $p[$r];
    }
    $p = $ertek;
    return true;
}
function km_tiszta($s) {
    $s = preg_replace('#<(/p|/li|br\s*/?|/h[1-6])\s*>#i', ' ', $s);
    $s = html_entity_decode(wp_strip_all_tags($s), ENT_QUOTES | ENT_HTML5, 'UTF-8');   // &nbsp; &amp; is
    return trim(preg_replace('/\s+/u', ' ', str_replace("\xC2\xA0", ' ', $s)));
}
function km_kezdodik($most, $horgony) {
    $h = km_tiszta($horgony);
    return mb_substr(km_tiszta($most), 0, mb_strlen($h)) === $h;
}

$hiba = 0;
ki('KONTROLL: a valtozatlan mezok ('.count($MARAD).') a mert allapotot hordozzak-e');
$jo = 0;
foreach ($MARAD as $m) {
    $e =& km_elem($fa, $m['elem_id']);
    $most = ($e === null) ? null : km_ut_ertek($e['settings'], $m['ut']);
    if ($most === null || !km_kezdodik($most, $m['horgony'])) {
        $hiba++;
        ki(sprintf('  !! [%s] %s (%s): %s', $m['elem_id'], $m['ut'], $m['cimke'],
            $most === null ? 'NINCS ilyen elem/mezo' : 'mas: '.mb_substr(km_tiszta($most), 0, 70)));
    } else { $jo++; }
    unset($e);
}
ki(sprintf('  %d/%d rendben', $jo, count($MARAD)));
ki('');
ki('CSERE ('.count($PAROK).' mezo):');
foreach ($PAROK as $par) {
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) { ki(sprintf('  !! [%s] NINCS ILYEN ELEM', $par['elem_id'])); $hiba++; unset($elem); continue; }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) { ki(sprintf('  !! [%s] nincs ilyen mezo: %s', $par['elem_id'], $par['ut'])); $hiba++; unset($elem); continue; }
    if (!km_kezdodik($most, $par['horgony'])) {
        ki(sprintf('  !! [%s] %s: a jelenlegi ertek NEM a mert horgonnyal kezdodik -- KIHAGYVA', $par['elem_id'], $par['ut']));
        ki('        most:    '.mb_substr(km_tiszta($most), 0, 90));
        ki('        horgony: '.mb_substr(km_tiszta($par['horgony']), 0, 90));
        $hiba++; unset($elem); continue;
    }
    ki(sprintf('  [%s] %s  -- %s', $par['elem_id'], $par['ut'], $par['cimke']));
    ki('        regi: '.mb_substr(km_tiszta($most), 0, 90));
    ki('        uj:   '.mb_substr(km_tiszta($par['uj']), 0, 90));
    if ($APPLY && !km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++;
    }
    unset($elem);
}
ki('');
$cimValtozik = ($p->post_title !== $UJ_CIM);
ki('OLDAL CIME: "'.$p->post_title.'"'.($cimValtozik ? '  ->  "'.$UJ_CIM.'"' : '  (mar ez)'));
ki('');
ki(sprintf('OSSZESEN: %d hiba/kihagyas', $hiba));
if (!$APPLY) { ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit($hiba > 0 ? 1 : 0); }
if ($hiba > 0) { ki('!! VOLT HIBA -- NEM IRUNK AZ OLDALRA. Reszleges szoveg rosszabb, mint a regi.'); exit(1); }

$home = getenv('HOME') ?: dirname($WP);
$mentes = rtrim($home, '/').'/landing-szoveg-mentes-'.$SITE.'-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($OLDAL, '_elementor_data', wp_slash($uj));
/* A negy cache-reteg (2026-09-21 ota): css, page_assets, element_cache, post cache + LiteSpeed. */
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) { delete_post_meta($OLDAL, $mk); }
clean_post_cache($OLDAL);
if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $OLDAL); ki('litespeed_purge_post: kiadva'); }
else { ki('litespeed_purge_post: NINCS ilyen action'); }
if (has_action('litespeed_purge_all')) { do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva'); }
else { ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.'); }

if ($cimValtozik) {
    $r = wp_update_post(array('ID' => $OLDAL, 'post_title' => $UJ_CIM), true);
    ki(is_wp_error($r) ? '!! a cim irasa elbukott: '.$r->get_error_message() : 'cim irva.');
    clean_post_cache($OLDAL);
}
ki('');
ki('VISSZAMERES -- mezonkent:');
$faV = json_decode(get_post_meta($OLDAL, '_elementor_data', true), true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    $e =& km_elem($faV, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; } else { $rossz++; ki(sprintf('  !! [%s] %s NEM az uj erteket adja', $par['elem_id'], $par['ut'])); }
    unset($e);
}
$mOk = 0;
foreach ($MARAD as $m) {
    $e =& km_elem($faV, $m['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $m['ut']);
    if ($ert !== null && km_kezdodik($ert, $m['horgony'])) { $mOk++; } else { $rossz++; ki(sprintf('  !! [%s] %s (valtozatlan) ELMOZDULT', $m['elem_id'], $m['ut'])); }
    unset($e);
}
ki(sprintf('  %d/%d uj mezo a vart erteket adja; %d/%d valtozatlan mezo valtozatlan.', $ok, count($PAROK), $mOk, count($MARAD)));
$cimMost = get_post($OLDAL)->post_title;
if ($cimMost !== $UJ_CIM) { $rossz++; ki('  !! a cim: "'.$cimMost.'"'); } else { ki('  cim: "'.$cimMost.'" (jo)'); }
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($OLDAL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.' : '!! ELES MENET VEGE, DE VOLT ELTERES.');
exit($rossz === 0 ? 0 : 1);
'''

if __name__ == '__main__':
    main()
