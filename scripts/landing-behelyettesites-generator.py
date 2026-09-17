#!/usr/bin/env python3
"""A parositas-JSON-bol onallo PHP szkriptet ir, ami a prodon futtathato.

MIERT GENERALT PHP ES NEM PARAMETER: a szkript SSH-n, csoveken megy at a prod PHP-nak,
tehat nem tud beolvasni egy itteni JSON-t. A parok BEEGNEK a fajlba -- igy Nova ELOTTE
soronkent atnezheti, mi fog tortenni, es a futtatas nem fugg semmilyen kulso allapottol.
"""
import json

PAROK = '/Users/macmini/marveen/scripts/landing-szoveg-parositas.json'
KI = '/Users/macmini/marveen/scripts/landing-szoveg-behelyettesites.php'
MERES = '/Users/macmini/marveen/tervek/landing-rotacio-meres-2026-09-17.txt'

FEJ = '''<?php
/**
 * AZ OKTOBERI LANDING SZOVEGENEK BEVITELE.  GENERALT FAJL -- ne kezzel szerkeszd,
 * hanem a scripts/landing-behelyettesites-generator.py-t futtasd ujra.
 *
 *   (alapertelmezes)      SZARAZ: semmit nem ir, csak megmutatja, mi tortenne
 *   --apply --oldal=<ID>  ELES: a MEGADOTT oldalra irja be a szoveget
 *
 * A CELPONT A DUPLIKATUM, NEM A FORRAS. Az `--oldal` KOTELEZO az eles menetben, es a
 * szkript MEGTAGADJA a 17153-at: a forras-oldal a REGI, elo landing, azon nincs dolgunk.
 *
 * MIERT MEZO-SZINTU A VISSZAMERES, ES NEM BYTE-AZONOSSAG: a `_elementor_data`-t ujra
 * kell kodolni, es a kodolas ALAKJA valtozhat (escape-bol nyers vagy forditva). Az
 * Elementornak ez mindegy -- dekodolva ugyanaz --, de a byte-osszevetes "az egesz oldal
 * megvaltozott"-at mutatna. Ezert MEZONKENT olvassuk vissza. A kodolas
 * JSON_UNESCAPED_UNICODE NELKUL megy, mert a prod igy tarolja (Nova 2026-09-17-i szaraz
 * menete mérte: a fejlec `\\uXXXX` alakban allt).
 *
 * A CSERE ELOTT MINDEN MEZOT ELLENORZUNK: ha a jelenlegi ertek NEM az, amit a parositas
 * rogzitett, az adott mezot KIHAGYJUK es jelentjuk. Egy elcsuszott oldal-allapot igy nem
 * ir felul valamit vaktaban.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\\n"; }

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$OLDAL = 0;
foreach ($ARGV as $a) { if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); } }
$FORRAS = 17153;
$MENTES_DIR = '/home/napalatt/vip.21napalatt.hu';
'''

TORZS = r'''
ki('LANDING-SZOVEG BEHELYETTESITES  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');

if ($OLDAL === $FORRAS) {
    ki('!! A megadott oldal a FORRAS ('.$FORRAS.') -- az a REGI, elo landing. NEM irunk ra.');
    exit;
}
if ($APPLY && $OLDAL <= 0) { ki('!! Eles menethez KOTELEZO a --oldal=<ID>. Nem talalgatok.'); exit; }
$CEL = $OLDAL > 0 ? $OLDAL : $FORRAS;   // szarazon a forrason mutatjuk meg, mi tortenne
ki('celpont: '.$CEL.($OLDAL > 0 ? '' : '  (szaraz menet, a forrason mutatva)'));
ki('');

$d = get_post_meta($CEL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$CEL.'-on'); exit; }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit; }

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
/** Ertek kiolvasasa/irasa a `icon_list.0.text` alaku uton belul a settings-ben. */
function km_ut_ertek($settings, $ut) {
    $reszek = explode('.', $ut);
    $p = $settings;
    foreach ($reszek as $r) {
        if (is_array($p) && array_key_exists($r, $p)) { $p = $p[$r]; }
        else { return null; }
    }
    return is_string($p) ? $p : null;
}
function km_ut_ir(&$settings, $ut, $ertek) {
    $reszek = explode('.', $ut);
    $p =& $settings;
    foreach ($reszek as $r) {
        if (!is_array($p) || !array_key_exists($r, $p)) { return false; }
        $p =& $p[$r];
    }
    $p = $ertek;
    return true;
}

$cserelt = 0; $kihagyott = 0; $hiba = 0;
foreach ($PAROK as $par) {
    if (empty($par['csere'])) { continue; }
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) {
        ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon -- kihagyva', $par['elem_id'])); $hiba++; continue;
    }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) {
        ki(sprintf('  !! [%s] nincs ilyen mezo: %s -- kihagyva', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $mostTiszta = trim(preg_replace('/\s+/', ' ', wp_strip_all_tags($most)));
    $vartTiszta = trim(preg_replace('/\s+/', ' ', $par['jelenlegi']));
    /* A meres 60 karakternel vagott, ezert a VART erteket prefixkent vetjuk ossze --
       es ezt ki is mondjuk, hogy senki ne olvassa teljes egyezesnek. */
    if (mb_substr($mostTiszta, 0, mb_strlen($vartTiszta)) !== $vartTiszta) {
        ki(sprintf('  !! [%s] %s: a JELENLEGI ertek nem az, amit a parositas rogzitett -- KIHAGYVA',
            $par['elem_id'], $par['ut']));
        ki(sprintf('        most: %s', mb_substr($mostTiszta, 0, 70)));
        ki(sprintf('        vart: %s', mb_substr($vartTiszta, 0, 70)));
        $hiba++; continue;
    }
    if (!$APPLY) {
        ki(sprintf('  [szaraz] [%s] %s', $par['elem_id'], $par['ut']));
        ki(sprintf('        -> %s', mb_substr(preg_replace('/\s+/', ' ', $par['uj']), 0, 70)));
        $cserelt++; continue;
    }
    if (!km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $cserelt++;
}

ki('');
ki(sprintf('CSERE: %d   HIBA/KIHAGYVA: %d   (a MARAD mezokhez nem nyultunk: %d)',
    $cserelt, $hiba, $MARAD_DB));

if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit; }
if ($hiba > 0) {
    ki('');
    ki('!! VOLT LEGALABB EGY KIHAGYOTT MEZO -- NEM IRUNK AZ OLDALRA.');
    ki('   Reszleges szoveg rosszabb, mint a regi: a kesz oldal fele-fele lenne, es az');
    ki('   nem latszik meg a szamokon. Nezd meg a fenti sorokat, es futtasd ujra.');
    exit;
}

$mentes = $MENTES_DIR.'/landing-szoveg-mentes-'.$CEL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit; }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

/* A prod alakja szerint kodolunk: JSON_UNESCAPED_UNICODE NELKUL. */
$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit; }
update_post_meta($CEL, '_elementor_data', wp_slash($uj));
delete_post_meta($CEL, '_elementor_css');
delete_post_meta($CEL, '_elementor_page_assets');

ki('');
ki('VISSZAMERES -- MEZONKENT, nem byte-azonossagra:');
$vissza = get_post_meta($CEL, '_elementor_data', true);
$faVissza = json_decode($vissza, true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    if (empty($par['csere'])) { continue; }
    $e =& km_elem($faVissza, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; }
    else {
        $rossz++;
        ki(sprintf('  !! [%s] %s NEM az uj erteket adja vissza', $par['elem_id'], $par['ut']));
    }
}
ki(sprintf('  %d/%d mezo a VART uj erteket adja vissza.', $ok, $ok + $rossz));
ki('  _elementor_css eldobva: '.(get_post_meta($CEL,'_elementor_css',true) === '' ? 'igen' : '!! MEGVAN'));
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
'''


def main():
    parok = json.load(open(PAROK, encoding='utf-8'))
    meres = open(MERES, encoding='utf-8').read()
    import re

    def jelenlegi(eid, ut):
        m = re.search(r'^@@\s+\[' + re.escape(eid) + r'\s*\]\s+\S+\s+' + re.escape(ut) + r'\s+(.*)$',
                      meres, re.M)
        return m.group(1).strip() if m else ''

    sorok = []
    marad = 0
    for r in parok:
        if not r['cserelendo']:
            marad += 1
            continue
        sorok.append({'elem_id': r['elem_id'], 'ut': r['elem_mezo'],
                      'jelenlegi': jelenlegi(r['elem_id'], r['elem_mezo']),
                      'uj': r['uj_szoveg'], 'csere': True})
    hianyzo = [s for s in sorok if not s['jelenlegi']]
    if hianyzo:
        raise SystemExit(f'HIBA: {len(hianyzo)} parhoz nincs jelenlegi ertek a meresben.')

    php = FEJ + '\n$MARAD_DB = ' + str(marad) + ';\n$PAROK = ' + php_tomb(sorok) + ';\n' + TORZS
    open(KI, 'w', encoding='utf-8').write(php)
    print(f'@@ {len(sorok)} csere-par + {marad} erintetlen mezo -> {KI}')


def php_tomb(sorok):
    def q(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"
    reszek = []
    for s in sorok:
        reszek.append('  array(' + ', '.join(
            f'{q(k)} => ' + (q(v) if not isinstance(v, bool) else ('true' if v else 'false'))
            for k, v in s.items()) + ')')
    return 'array(\n' + ',\n'.join(reszek) + '\n)'


if __name__ == '__main__':
    main()
