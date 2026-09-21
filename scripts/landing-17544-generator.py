#!/usr/bin/env python3
"""17544 (/ingyenes-kihivas/, Egeszseges reggeli 2026.10): a JAVITOTT szoveg bevitele.

MIT CSINAL: Copy leadott markdownjabol KIOLVASSA az uj szovegeket (nem en gepelem ujra),
osszeparositja oket a 17544 Elementor-elem-azonositoival, kiirja a parositast JSON-be, es
generalja a prodon futtathato PHP-t.

>>> A HORGONYOK NEM ALLNAK EBBEN A FAJLBAN, HANEM MERESBOL JONNEK:
>>> `landing-17544-elo-allapot.json`, az ELO oldal renderelt DOM-jabol, data-id szerint.
>>>
>>> MIERT NEM KEZI TABLA, PEDIG ELOSZOR AZ VOLT (Nova fogta meg, 2026-09-21 delben):
>>> a tabla ertekeit a 09:27-es deploy ELOTT vettem fel, a deploy meg atirta a mezoket --
>>> vagyis a horgonyok a SAJAT MUNKANKTOL avultak el, par ora alatt. Egy kezzel felvett
>>> horgony pontosan addig ervenyes, amig senki nem ir az oldalra, tehat egy DEPLOY-
>>> szkriptben a legrosszabb helyen all: az elso sikeres futasa teszi ervenytelenne a
>>> sajat kovetkezo futasat. Es a bukas nem hangos: a PHP oldal "elcsuszott"-nak
>>> minositi az erintett mezoket es NEM ir, a kimenet pedig alacsonyabb darabszamot
>>> mutat -- amit konnyu "csak ennyi valtozott"-kent olvasni.

>>> ES EZERT ROVID A HORGONY: a WordPress `wptexturize` a MEGJELENITESKOR alakit at
>>> karaktereket -- a tarolt " - " az elo oldalon " – " (nagykotojel), a ' pedig ’.
>>> A renderelt szoveg tehat NEM egyezik a tarolttal, es a PHP-oldali osszevetes a
>>> TAROLTAT nezi. Ezert a horgony a mert ertek olyan prefixe, amit a texturize nem
>>> erinthetett: a `horgony()` levagja az elso kockazatos karakter elott. Ha ettol 25
>>> karakternel rovidebb maradna, a generator MEGALL -- egy tul rovid horgony nem
>>> azonosit, csak atengedne barmit.

FUTTATAS:
  python3 scripts/landing-17544-generator.py
"""
import argparse, html, io, json, os, re, subprocess

COPY_MD = ('/Users/macmini/marveen/agents/copy/workspace/landing/'
           'ingyenes-kihivas-2026-10-reggeli/landing-2026-10-reggeli-JAVITOTT.md')
KI_JSON = '/Users/macmini/marveen/scripts/landing-17544-parositas.json'
KI_PHP = '/Users/macmini/marveen/scripts/landing-17544-szoveg-csere.php'

ELO_ALLAPOT = '/Users/macmini/marveen/scripts/landing-17544-elo-allapot.json'

# Amit a wptexturize a MEGJELENITESKOR eloallithat. A horgony ezek ELSO elofordulasa
# elott ervenyet ver -- azon tul a renderelt es a tarolt szoveg elterhet.
KOCKAZATOS = '\u2013\u2014\u2018\u2019\u201c\u201d\u201e\u2026'
HORGONY_MAX = 80
HORGONY_MIN = 25


def elo_szoveg():
    """Az ELO lap olvashato szovege. Ugyanaz a fetch-ut, amit a szoveg-kapu hasznal."""
    r = subprocess.run(['curl', '-sL', 'https://vip.21napalatt.hu/ingyenes-kihivas/'],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        return None
    t = re.sub(r'(?is)<(script|style|noscript)[^>]*>.*?</\1>', ' ', r.stdout)
    t = html.unescape(re.sub(r'(?s)<[^>]+>', ' ', t))
    return re.sub(r'\s+', ' ', t.replace('\u00a0', ' ')).strip()


def frissesseg_kapu(parok, meta):
    """A MERES FRISSESSEGE, mert a mert allapot ugyanugy elavul, mint a kezi tabla volt.

    A snapshot egy PILLANATOT rogzit, es a sajat deployunk irja felul. Ha valaki kesobb
    ujragenéral anelkul, hogy ujramerne, pontosan az a hiba jon vissza, amit a kezi tabla
    kivetelevel megszuntettunk -- csak eggyel feljebb. Ezert a generator megnezi, hogy a
    horgonyok MA is ott allnak-e az elo lapon.

    Nem a teljes erteket veti ossze, hanem a HORGONYT: az a resz, amit a PHP-oldali kapu
    tenylegesen hasznal. Ami a horgony UTAN valtozott, az nem is erdekli a kaput.
    """
    t = elo_szoveg()
    if t is None:
        raise SystemExit('HIBA: az elo lap nem toltodott le, a frissesseg nem merheto.\n'
                         '  A --meres-nelkul kapcsoloval atlephetsz rajta, de akkor a\n'
                         '  horgonyok korarol NINCS allitasunk.')
    hianyzo = [f"{p['elem_id']}|{p['ut']}" for p in parok
               if re.sub(r'\s+', ' ', p['horgony']).strip() not in t]
    if hianyzo:
        raise SystemExit(
            'HIBA -- A MERT ALLAPOT ELAVULT. {} horgony nincs meg az elo lapon:\n  - {}\n\n'
            '  A meres ideje: {}\n'
            '  Azota irt valaki az oldalra (tipikusan MI, egy korabbi deployjal).\n'
            '  TEENDO: merd ujra az elo oldalt es frissitsd a {} fajlt.\n'
            '  NE a horgonyt igazitsd a szkripthez -- a horgony a VILAG allapota.'
            .format(len(hianyzo), '\n  - '.join(hianyzo), meta['mikor_utc'], ELO_ALLAPOT))
    print(f'@@ frissesseg-kapu: mind a {len(parok)} horgony megvan az elo lapon.')


def elo_allapot():
    """A ma MERT elo ertekek. A fajl fejlece mondja meg, mikor es hogyan keszult."""
    if not os.path.exists(ELO_ALLAPOT):
        raise SystemExit(f'HIBA: nincs meg a mert elo allapot: {ELO_ALLAPOT}\n'
                         f'  Ez NEM potolhato a korabbi generalt szkriptbol: az azt mondja meg,\n'
                         f'  mit AKARTUNK odairni, nem azt, mi ALL ott most.')
    d = json.load(io.open(ELO_ALLAPOT, encoding='utf-8'))
    return d['mezok'], d


def horgony(ertek):
    """A mert ertek texturize-biztos prefixe."""
    vag = len(ertek)
    for ch in KOCKAZATOS:
        i = ertek.find(ch)
        if i != -1:
            vag = min(vag, i)
    h = ertek[:min(vag, HORGONY_MAX)]
    if len(h) == HORGONY_MAX and ' ' in h:
        h = h[:h.rfind(' ')]
    h = h.strip()
    if len(h) < HORGONY_MIN:
        raise SystemExit(f'HIBA: a horgony {len(h)} karakterre rovidult ("{h}").\n'
                         f'  A mert ertek eleje kockazatos karaktert tartalmaz, tehat innen\n'
                         f'  nem lehet texturize-biztos horgonyt vagni. Kezi dontes kell.')
    return h


def szekciok(szoveg):
    """A '## (x) ...' fejlecek szerint darabol. Ertek: a fejlec alatti nyers torzs."""
    ki, akt, buf = {}, None, []
    for sor in szoveg.split('\n'):
        m = re.match(r'^##\s+\(([a-f])\)', sor)
        if m:
            if akt:
                ki[akt] = '\n'.join(buf).strip('\n')
            akt, buf = m.group(1), []
            continue
        if akt is not None:
            buf.append(sor)
    if akt:
        ki[akt] = '\n'.join(buf).strip('\n')
    return ki


def alszekcio(torzs, cim):
    """Egy '### <cim>' alatti blokk, a kovetkezo '###'-ig."""
    m = re.search(r'^###\s+' + re.escape(cim) + r'\s*$(.*?)(?=^###\s|\Z)',
                  torzs, re.M | re.S)
    return None if not m else m.group(1).strip('\n')


def bekezdes_lista(blokk):
    return [b.strip() for b in re.split(r'\n\s*\n', blokk) if b.strip()]


def html_bekezdesek(blokk):
    """Bekezdesenkent <p>. A text-editor widget a tarolt erteket NYERSEN adja ki: ami
    nincs tagbe teve, az egyetlen folyo szovegge olvad ossze."""
    return ''.join('<p>' + h(b) + '</p>' for b in bekezdes_lista(blokk))


def html_hero(blokk):
    """Hero: elso bekezdes <p>, a maradek sorok <ul><li>. A 2026.08-as landing (16884)
    pontosan ezt az alakot hordozza ugyanezen az elem-azonositon."""
    r = bekezdes_lista(blokk)
    if len(r) != 2:
        raise SystemExit(f'HIBA: a hero {len(r)} blokkos, 2-t vartam (bevezeto + lista).')
    tetelek = [s.strip() for s in r[1].split('\n') if s.strip()]
    if len(tetelek) != 4:
        raise SystemExit(f'HIBA: a hero listaja {len(tetelek)} soros, nem 4.')
    return ('<p>' + h(r[0]) + '</p><ul>'
            + ''.join('<li>' + h(t) + '</li>' for t in tetelek) + '</ul>')


def h(s):
    """Csak a szerkezeti karaktereket entitasozzuk -- ekezetet, irasjelet nem."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def sorok(blokk):
    return [s.strip() for s in blokk.split('\n') if s.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--meres-nelkul', action='store_true',
                    help='a frissesseg-kapu kihagyasa (halozat nelkul)')
    a = ap.parse_args()
    if not os.path.exists(COPY_MD):
        raise SystemExit(f'HIBA: nincs meg Copy fajlja: {COPY_MD}')
    sz = szekciok(io.open(COPY_MD, encoding='utf-8').read())
    hianyzo = [k for k in 'abcdef' if k not in sz]
    if hianyzo:
        raise SystemExit(f'HIBA: Copy fajljabol hianyzik: {", ".join(hianyzo)}')

    mert, meta = elo_allapot()
    parok = []
    tagtalan = []

    def fel(elem_id, ut, uj):
        kulcs = f'{elem_id}|{ut}'
        m = mert.get(kulcs)
        if m is None:
            raise SystemExit(f'HIBA: a {kulcs} mezorol NINCS mert elo ertek.\n'
                             f'  Ne talald ki: merd ujra az elo oldalt, es frissitsd a\n'
                             f'  {ELO_ALLAPOT} fajlt.')
        if not uj or not uj.strip():
            raise SystemExit(f'HIBA: ures uj ertek: {kulcs}')
        # A MARKUP-REGRESSZIO ORSZEME: a 09-17-i eset ota tudjuk, hogy egy sima szoveges
        # iras nemán leszedi a tageket az editor-mezokrol. Ha a MERT elo ertek ma nulla
        # taget hordoz egy editor-mezon, azt ki kell mondani -- nem allitjuk meg a
        # generalast (ez a szkript epp javitani fogja), de ne csendben mulion el.
        if ut == 'editor' and m.get('tag_db', 0) == 0:
            tagtalan.append(kulcs)
        tiszta_uj = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', uj)).strip()
        parok.append({'elem_id': elem_id, 'ut': ut,
                      'horgony': horgony(m['szoveg']), 'uj': uj,
                      'valtozik': tiszta_uj != m['szoveg'].strip()})

    # (b) hero: bevezeto + negysoros lista, egyben
    fel('b3e8629', 'editor', html_hero(sz['b']))
    # (a) 2. szekcio torzse  (a CIM valtozatlan, ezert nincs benne a parositasban)
    fel('370bdfea', 'editor', html_bekezdesek(alszekcio(sz['a'], 'Törzs')))
    # (c) "Mire szamithatsz?" torzse
    fel('17c1f49', 'editor', html_bekezdesek(sz['c']))
    # (d) "Mit kapsz meg?" bevezeto + negy ikonos pont
    fel('c927586', 'editor', html_bekezdesek(alszekcio(sz['d'], 'Bevezető')))
    negy = sorok(alszekcio(sz['d'], 'A négy pont'))
    if len(negy) != 4:
        raise SystemExit(f'HIBA: a "negy pont" {len(negy)} soros, nem 4.')
    for i, s in enumerate(negy):
        fel('360da42', f'icon_list.{i}.text', s)
    # (e) "Imadni fogod" nyolc pontja
    nyolc = sorok(sz['e'])
    if len(nyolc) != 8:
        raise SystemExit(f'HIBA: az "Imadni fogod" {len(nyolc)} pontos, nem 8.')
    for i, s in enumerate(nyolc):
        fel('bb2a697', f'icon_list.{i}.text', s)
    # (f) zaro vagykep
    fel('be0d9b5', 'editor', html_bekezdesek(sz['f']))

    if len(parok) != len(mert):
        hiany = sorted(set(mert) - {f"{p['elem_id']}|{p['ut']}" for p in parok})
        raise SystemExit(f'HIBA: {len(parok)} par keszult, {len(mert)} mert mezohoz.\n'
                         f'  Parositatlan: {", ".join(hiany) or "(nincs)"}')

    if a.meres_nelkul:
        print('@@ FIGYELEM: a frissesseg-kapu KIHAGYVA (--meres-nelkul).')
        print(f"@@   A horgonyok a {meta['mikor_utc']}-i meresbol valok, es azota barmi tortenhetett.")
    else:
        frissesseg_kapu(parok, meta)

    # ONELLENORZES, ami a kapu sajat leleteire nez: a bevitt szoveg ne hozza vissza
    # azt, amit epp javitunk. Nem velemeny, hanem szamlalas.
    egyben = re.sub(r'<[^>]+>', ' ', '\n'.join(p['uj'] for p in parok))
    bajok = []
    if '–' in egyben or '—' in egyben:
        bajok.append('nagykotojel van az UJ szovegben')
    for szo in ['vércukor', 'inzulin', 'hormon', 'anyagcsere', 'glikémiás',
                'ketózis', 'gyulladás', 'immunrendszer']:
        if szo in egyben:
            bajok.append(f'elettani szokincs az UJ szovegben: {szo}')
    if 'állítottam össze' in egyben:
        bajok.append("'allitottam ossze' az UJ szovegben")
    imadni = [p['uj'] for p in parok if p['elem_id'] == 'bb2a697']  # ezek tag nelkuliek
    vesszos = sum(1 for x in imadni if x.endswith(','))
    if vesszos < 7:
        bajok.append(f'az "Imadni fogod" 8 pontjabol csak {vesszos} vesszos')
    if bajok:
        raise SystemExit('HIBA -- a bevitel a sajat kapunk leleteit hozna vissza:\n  - '
                         + '\n  - '.join(bajok))

    json.dump(parok, io.open(KI_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    io.open(KI_PHP, 'w', encoding='utf-8').write(FEJ + '\n$PAROK = ' + php_tomb(parok) + ';\n' + TORZS)
    valtozik = [p for p in parok if p['valtozik']]
    print(f"@@ mert elo allapot: {meta['mikor_utc']}  ({meta['forras']})")
    print(f'@@ {len(parok)} mezo ({len(valtozik)} valtozik, {len(parok)-len(valtozik)} valtozatlan)'
          f' -> {KI_PHP}')
    for p in valtozik:
        print(f"@@   CSERE {p['elem_id']} {p['ut']}")
    if tagtalan:
        print(f'@@ FIGYELEM: {len(tagtalan)} editor-mezo MA nulla HTML-taget hordoz '
              f'({", ".join(tagtalan)}).')
        print('@@   Ez a markup-veszteses hibaosztaly nyoma. Ez a szkript HTML-t ir vissza,')
        print('@@   tehat javitja -- de ha ez UJ, valami megint sima szoveget irt a mezobe.')
    print(f'@@ parositas: {KI_JSON}')


FEJ = r'''<?php
/**
 * 17544 -- /ingyenes-kihivas/ (Egeszseges reggeli 2026.10): A JAVITOTT SZOVEG BEVITELE.
 * GENERALT FAJL -- ne kezzel szerkeszd, hanem a scripts/landing-17544-generator.py-t
 * futtasd ujra. A szoveg forrasa Copy leadott markdownja, a szkript olvassa ki belole.
 *
 *   (alapertelmezes)          SZARAZ: semmit nem ir, csak megmutatja, mi tortenne
 *   --apply --oldal=17544     ELES: a MEGADOTT oldalra irja be a szoveget
 *
 * A 17153 (a REGI, elo meal-prep landing) MEG VAN TAGADVA. Az `--oldal` az eles menetben
 * kotelezo: ezen a peldanyon tobb landing is ugyanezeket az elem-azonositokat hordozza
 * (duplikalt oldalak), tehat egy elfelejtett `--oldal` NEM ures futast adna, hanem a
 * ROSSZ oldalt irna at.
 *
 * MIERT PREFIX-EGYEZES ES NEM TELJES: a horgony a tarolt ertek eleje, szandekosan olyan
 * reszlet, amit a `wptexturize` nem alakit at (nincs benne kotojel, idezojel, harompont).
 * A teljes rendereltszoveghez hasonlitani hibas lenne: a tarolt " - " az elo oldalon
 * " – " alakban jelenik meg, es minden ilyen mezo "elcsuszott"-nak latszana.
 *
 * MIERT MEZO-SZINTU A VISSZAMERES: a `_elementor_data`-t ujra kell kodolni, es a kodolas
 * ALAKJA valtozhat. Az Elementornak ez mindegy (dekodolva ugyanaz), de egy byte-osszevetes
 * "az egesz oldal megvaltozott"-at mutatna. A kodolas JSON_UNESCAPED_UNICODE NELKUL megy,
 * mert a prod igy tarolja.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$OLDAL = 0;
foreach ($ARGV as $a) { if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); } }
$TILTOTT = 17153;
$MENTES_DIR = '/home/napalatt/vip.21napalatt.hu';
'''

TORZS = r'''
ki('LANDING 17544 SZOVEG-CSERE  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');

if ($OLDAL === $TILTOTT) {
    ki('!! A megadott oldal a REGI meal-prep landing ('.$TILTOTT.') -- NEM irunk ra.');
    exit(2);
}
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is. Nem talalgatok.'); exit(2); }
$CEL = $OLDAL;
$p = get_post($CEL);
if (!$p) { ki('!! a '.$CEL.' nem letezik ezen a peldanyon.'); exit(2); }
ki('celpont: '.$CEL.'  slug='.$p->post_name.'  status='.$p->post_status);
ki('');

$d = get_post_meta($CEL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$CEL.'-on'); exit(2); }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit(2); }

/** Egy elem megkeresese ID szerint, REFERENCIAVAL (hogy irni is tudjunk). */
function &km_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings') { continue; }
        if (!is_array($gy)) { continue; }
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
    /* A blokk-tagek HATART jelentenek: nelkuluk a "</p><p>" hatarbol "…vegeEleje…" lesz,
       es a jelentes olvashatatlan. A horgony-osszevetest ez nem billenti el: a MAI ertekek
       tag-mentesek (2026-09-21-en megmerve: a 13 text-editor widgetbol 9 nulla tagot hordoz). */
    $s = preg_replace('#<(/p|/li|br\s*/?|/h[1-6])\s*>#i', ' ', $s);
    return trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags($s)));
}

$rendben = 0; $hiba = 0; $valtozik = 0;
foreach ($PAROK as $par) {
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) {
        ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon', $par['elem_id'])); $hiba++; continue;
    }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) {
        ki(sprintf('  !! [%s] nincs ilyen mezo: %s', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $mostT = km_tiszta($most);
    $horgony = km_tiszta($par['horgony']);
    if (mb_substr($mostT, 0, mb_strlen($horgony)) !== $horgony) {
        ki(sprintf('  !! [%s] %s: a JELENLEGI ertek nem a mert horgonnyal kezdodik -- KIHAGYVA',
            $par['elem_id'], $par['ut']));
        ki(sprintf('        most:    %s', mb_substr($mostT, 0, 90)));
        ki(sprintf('        horgony: %s', mb_substr($horgony, 0, 90)));
        $hiba++; continue;
    }
    $azonos = (km_tiszta($par['uj']) === $mostT);
    if (!$azonos) { $valtozik++; }
    ki(sprintf('  [%s] %s %s', $par['elem_id'], $par['ut'], $azonos ? '(valtozatlan)' : ''));
    if (!$azonos) {
        ki(sprintf('        regi: %s', mb_substr($mostT, 0, 90)));
        ki(sprintf('        uj:   %s', mb_substr(km_tiszta($par['uj']), 0, 90)));
    }
    if ($APPLY && !km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $rendben++;
}

ki('');
ki(sprintf('MEZO: %d rendben, %d hiba/kihagyva  (ebbol %d valtozik, %d mar most is egyezik)',
    $rendben, $hiba, $valtozik, $rendben - $valtozik));

if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit($hiba > 0 ? 1 : 0); }
if ($hiba > 0) {
    ki('');
    ki('!! VOLT LEGALABB EGY KIHAGYOTT MEZO -- NEM IRUNK AZ OLDALRA.');
    ki('   Reszleges szoveg rosszabb, mint a regi: a kesz oldal fele-fele lenne, es az');
    ki('   nem latszik meg a szamokon. Nezd meg a fenti sorokat, es futtasd ujra.');
    exit(1);
}

$mentes = $MENTES_DIR.'/landing-szoveg-mentes-'.$CEL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($CEL, '_elementor_data', wp_slash($uj));
delete_post_meta($CEL, '_elementor_css');
delete_post_meta($CEL, '_elementor_page_assets');
/* A NEGYEDIK RETEG, es Nova merte meg 2026-09-21-en: a szkript visszameresé ZOLD volt, a
   `litespeed_purge_post` KIADVA, es a lap MEGIS a regit adta -- cache-kerulo query-vel is.
   A tarolt `_elementor_data` ekozben mar az ujat hordozta, tehat NEM az iras bukott, hanem a
   KISZOLGALAS. A hianyzo meta az `_elementor_element_cache`: ez a RENDERELT HTML cache-e.
   Ujragenralodik, a torlese biztonsagos.
   ES EZ A LEGROSSZABB ALAKBAN JELENTKEZIK: minden nyugta zold, es a lap valtozatlan --
   vagyis pont ugy nez ki, mint egy elbukott iras, es oda kuldi a keresest, ahol nincs semmi. */
delete_post_meta($CEL, '_elementor_element_cache');
clean_post_cache($CEL);
/* MIERT MEGY A PURGE_ALL IS, pedig durvabb: Nova a retegeket EGYSZERRE uritette, tehat hogy
   melyik oldotta meg, az NINCS izolalva. Egy szukebb reszhalmaz ezert tipp lenne; ez a sor
   azt csinalja, amirol MERES van. A szkript evente parszor fut: egy ujraepulo cache olcsobb,
   mint egy landing, ami az inditas napjan valtozatlannak latszik.
   ES A HOROG LETEZIK, nem remeny: a kihelyezett LiteSpeed 7.5.0.1 `src/api.cls.php` `init()`-je
   a 110. es 111. soran regisztralja a `litespeed_purge_all`-t ES a `litespeed_purge_post`-ot,
   egymas mellett, feltétel nelkul. A `purge_post` agat 2026-09-21-en HAROM eles futas kiirta
   ("kiadva"), ami csak a has_action IGAZ againal tortenhet -- tehat az `init()` lefutott, es
   vele a szomszedos sor is. (A plugint a `prod` agrol olvastam, nem a futo fajlbol.) */
if (has_action('litespeed_purge_post')) {
    do_action('litespeed_purge_post', $CEL); ki('litespeed_purge_post: kiadva');
} else {
    ki('litespeed_purge_post: NINCS ilyen action.');
}
if (has_action('litespeed_purge_all')) {
    do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva');
} else {
    ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.');
}

ki('');
ki('VISSZAMERES -- MEZONKENT, nem byte-azonossagra:');
$faVissza = json_decode(get_post_meta($CEL, '_elementor_data', true), true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    $e =& km_elem($faVissza, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; }
    else { $rossz++; ki(sprintf('  !! [%s] %s NEM az uj erteket adja vissza', $par['elem_id'], $par['ut'])); }
}
ki(sprintf('  %d/%d mezo a VART uj erteket adja vissza.', $ok, $ok + $rossz));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($CEL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
exit($rossz === 0 ? 0 : 1);
'''


def php_tomb(sorok):
    def q(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"
    reszek = []
    for s in sorok:
        reszek.append('  array(' + ', '.join(
            f'{q(k)} => ' + (('true' if v else 'false') if isinstance(v, bool) else q(v))
            for k, v in s.items()) + ')')
    return 'array(\n' + ',\n'.join(reszek) + '\n)'


if __name__ == '__main__':
    main()
