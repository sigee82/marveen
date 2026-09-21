#!/usr/bin/env python3
"""17544: a FORMAZAS helyreallitasa azokon a mezokon, ahol a SZO mar helyes.

A LELET (Bit, 2026-09-21, bongeszoben merve): a 17544 tizenharom text-editor widgetjebol
KILENC nulla HTML-taget hordoz. Pont az a kilenc, amit a 2026-09-17-i szoveg-csere
irt -- a negy erintetlen (eadbb3d, c0ad3ec, 84b9598, 8ce0efc) megtartotta a tagjait.
Az ok: a text-editor widget a tarolt erteket NYERSEN adja ki, a szkript pedig sima
szoveget irt bele. Az ujsorok a HTML-ben szokozze olvadnak, tehat minden bekezdes-hatar
es minden felsorolas ELTUNT -- a heroban a bevezeto es az elso listatetel OSSZE IS RAGADT
("...kitart delig.minden napra egy recept"), szokoz nelkul.
Ugyanez a rotacio elotti 2026.08-as landingen (16884, UGYANEZEK az elem-azonositok):
`<p>bevezeto</p><ul><li>...</li></ul>` -- vagyis a markup megvolt, es a csere vitte el.

EZ A SZKRIPT azokat a mezoket kezeli, ahol a SZOVEG MAR HELYES, es csak a markup hianyzik
(Nova 2026-09-21-i briefje ezeket "ellenorizve, helyes"-kent kerítette el -- a SZAVAK
tenyleg helyesek, a FORMAZAS nem). A hat cserelendo szekciot NEM ez kezeli: azokat a
landing-17544-generator.py mar HTML-ként irja.

A KAPU KETTOS, es ezert allithato, hogy egyetlen szo sem valtozik:
  1. a mai ertek legyen TAG-MENTES (csak oda nyulunk, ahol a markup tenyleg hianyzik);
  2. a beirando HTML tagoktol megtisztitva es szokozre normalizalva legyen BYTE-RA
     azonos a mai ertekkel.
Ha barmelyik nem all, az a mezo kimarad, es akkor SEMMIT nem irunk.
"""
import importlib.util, io, re

KI = '/Users/macmini/marveen/scripts/landing-17544-formazas-helyreallitas.php'
_spec = importlib.util.spec_from_file_location(
    'fk', '/Users/macmini/marveen/scripts/landing-17544-fixture-kinyeres.py')
_fk = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_fk)


def h(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def mai_ertekek():
    php = io.open(_fk.REGI_PHP, encoding='utf-8').read()
    blk = re.search(r'\$PAROK = array\((.*?)\n\);', php, re.S).group(1)
    ki = {}
    for darab in re.findall(r'array\((.*?)\)(?=,\n|\n\))', blk, re.S):
        s = _fk.php_stringek(darab)
        d = {s[i]: s[i + 1] for i in range(0, len(s) - 1, 2)}
        if d.get('ut') == 'editor':
            ki[d['elem_id']] = d['uj']
    return ki


def p_soronkent(ertek):
    return ''.join('<p>' + h(s.strip()) + '</p>' for s in ertek.split('\n') if s.strip())


def regisztralj(ertek):
    """<strong> az elso mondatra, <br> a masodik sor ele -- a 16884 alakja."""
    sorok = [s.strip() for s in ertek.split('\n') if s.strip()]
    if len(sorok) != 2:
        raise SystemExit(f'HIBA: ed700ab {len(sorok)} soros, 2-t vartam.')
    return f'<p><strong>{h(sorok[0])}</strong> <br>{h(sorok[1])}</p>'


def nyeremenyjatek(ertek):
    """Ket felszolito lepes <ul><li><strong>, aztan a sorsolas es a VIP Klub leiras."""
    sorok = [s.strip() for s in ertek.split('\n') if s.strip()]
    if len(sorok) != 5:
        raise SystemExit(f'HIBA: 1cfd5a8 {len(sorok)} soros, 5-ot vartam.')
    return ('<ul>' + ''.join(f'<li><strong>{h(x)}</strong></li>' for x in sorok[:2]) + '</ul>'
            + f'<p>{h(sorok[2])}<br>{h(sorok[3])}</p>'
            + f'<p>{h(sorok[4])}</p>')


SZABALY = {
    'ed700ab': regisztralj,      # "Regisztralj most ... / Indulas: 2026. oktober 1."
    '8c97ba3': p_soronkent,      # "Miert eppen 7 nap?" -- harom bekezdes
    '6a0ce87': p_soronkent,      # "Ez nem egy meregtelenito..." -- egy bekezdes
    '1cfd5a8': nyeremenyjatek,   # nyeremenyjatek: ket lepes + sorsolas + VIP Klub
}


def tiszta(s):
    s = re.sub(r'<(/p|/li|br\s*/?|/h[1-6])\s*>', ' ', s, flags=re.I)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def main():
    mai = mai_ertekek()
    sorok = []
    for eid, fn in SZABALY.items():
        if eid not in mai:
            raise SystemExit(f'HIBA: {eid} nincs a korabbi generalt szkriptben.')
        uj = fn(mai[eid])
        # ONELLENORZES: a szo nem valtozhat. Ugyanaz a kapu, amit a PHP is futtat --
        # itt azert is, hogy egy rossz szabaly ne is jusson el a szerverig.
        if tiszta(uj) != tiszta(mai[eid]):
            raise SystemExit(f'HIBA: {eid} -- a formazas MEGVALTOZTATNA a szoveget.\n'
                             f'  mai: {tiszta(mai[eid])[:120]}\n  uj:  {tiszta(uj)[:120]}')
        if re.search(r'<[^>]+>', mai[eid]):
            raise SystemExit(f'HIBA: {eid} MAR hordoz tagot -- nem ide tartozik.')
        sorok.append({'elem_id': eid, 'ut': 'editor', 'mai': mai[eid], 'uj': uj})
    io.open(KI, 'w', encoding='utf-8').write(FEJ + '\n$PAROK = ' + _php_tomb(sorok) + ';\n' + TORZS)
    print(f'@@ {len(sorok)} mezo formazasa -> {KI}')
    for s in sorok:
        print(f"@@   {s['elem_id']}: {s['uj'][:90]}")


def _php_tomb(sorok):
    def q(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"
    return 'array(\n' + ',\n'.join(
        '  array(' + ', '.join(f'{q(k)} => {q(v)}' for k, v in s.items()) + ')'
        for s in sorok) + '\n)'


FEJ = r'''<?php
/**
 * 17544 -- A FORMAZAS HELYREALLITASA. GENERALT FAJL -- a
 * scripts/landing-17544-formazas-generator.py irja, ne kezzel szerkeszd.
 *
 * EGYETLEN SZO SEM VALTOZIK. Csak <p>, <ul><li>, <strong> es <br> kerul be azokra a
 * mezokre, ahonnan a 2026-09-17-i sima-szoveges iras elvitte oket.
 *
 *   php -- --oldal=17544            SZARAZ
 *   php -- --apply --oldal=17544    ELES
 *
 * A KAPU KETTOS, mezonkent:
 *   1. a mai ertek TAG-MENTES (ahol mar van markup, oda nem nyulunk);
 *   2. a beirando HTML tagoktol megtisztitva BYTE-RA azonos a mai ertekkel.
 * Ha barmelyik mezon barmelyik nem all, EGYETLEN mezot sem irunk.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once getenv('WP_LOAD') ?: '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }
$APPLY = in_array('--apply', $argv, true);
$OLDAL = 0;
foreach ($argv as $a) { if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); } }
$MENTES_DIR = getenv('MENTES_DIR') ?: '/home/napalatt/vip.21napalatt.hu';
'''

TORZS = r'''
ki('LANDING 17544 FORMAZAS-HELYREALLITAS  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');
if ($OLDAL === 17153) { ki('!! a REGI meal-prep landing -- NEM irunk ra.'); exit(2); }
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>.'); exit(2); }
$post = get_post($OLDAL);
if (!$post) { ki('!! a '.$OLDAL.' nem letezik.'); exit(2); }
ki('celpont: '.$OLDAL.'  slug='.$post->post_name);
ki('');

$d = get_post_meta($OLDAL, '_elementor_data', true);
$fa = is_string($d) ? json_decode($d, true) : null;
if (!is_array($fa)) { ki('!! nincs dekodolhato _elementor_data'); exit(2); }

function &fh_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings') { continue; }
        if (!is_array($gy)) { continue; }
        $t =& fh_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}
function fh_tiszta($s) {
    $s = preg_replace('#<(/p|/li|br\s*/?|/h[1-6])\s*>#i', ' ', $s);
    return trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags($s)));
}

$hiba = 0;
foreach ($PAROK as $par) {
    $e =& fh_elem($fa, $par['elem_id']);
    if ($e === null) { ki('  !! ['.$par['elem_id'].'] nincs ilyen elem'); $hiba++; continue; }
    $most = isset($e['settings'][$par['ut']]) ? $e['settings'][$par['ut']] : null;
    if (!is_string($most)) { ki('  !! ['.$par['elem_id'].'] nincs '.$par['ut'].' mezo'); $hiba++; continue; }
    if (preg_match('/<[^>]+>/', $most)) {
        ki('  !! ['.$par['elem_id'].'] MAR hordoz HTML-taget -- nem nyulunk hozza.');
        ki('     most: '.mb_substr($most, 0, 90));
        $hiba++; continue;
    }
    if (fh_tiszta($par['uj']) !== fh_tiszta($most)) {
        ki('  !! ['.$par['elem_id'].'] a formazas MEGVALTOZTATNA a szoveget -- KIHAGYVA');
        ki('     most: '.mb_substr(fh_tiszta($most), 0, 90));
        ki('     uj:   '.mb_substr(fh_tiszta($par['uj']), 0, 90));
        $hiba++; continue;
    }
    ki('  ['.$par['elem_id'].'] '.mb_substr($par['uj'], 0, 100));
    if ($APPLY) { $e['settings'][$par['ut']] = $par['uj']; }
}

if ($hiba > 0) { ki(''); ki('!! '.$hiba.' MEZO BUKOTT -- semmit nem irunk.'); exit(1); }
if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit(0); }

$mentes = $MENTES_DIR.'/landing-formazas-mentes-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');
$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($OLDAL, '_elementor_data', wp_slash($uj));
delete_post_meta($OLDAL, '_elementor_css');
delete_post_meta($OLDAL, '_elementor_page_assets');
/* A NEGYEDIK RETEG, es Nova merte meg 2026-09-21-en: a szkript visszameresé ZOLD volt, a
   `litespeed_purge_post` KIADVA, es a lap MEGIS a regit adta -- cache-kerulo query-vel is.
   A tarolt `_elementor_data` ekozben mar az ujat hordozta, tehat NEM az iras bukott, hanem a
   KISZOLGALAS. A hianyzo meta az `_elementor_element_cache`: ez a RENDERELT HTML cache-e.
   Ujragenralodik, a torlese biztonsagos.
   ES EZ A LEGROSSZABB ALAKBAN JELENTKEZIK: minden nyugta zold, es a lap valtozatlan --
   vagyis pont ugy nez ki, mint egy elbukott iras, es oda kuldi a keresest, ahol nincs semmi. */
delete_post_meta($OLDAL, '_elementor_element_cache');
clean_post_cache($OLDAL);
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
    do_action('litespeed_purge_post', $OLDAL); ki('litespeed_purge_post: kiadva');
} else {
    ki('litespeed_purge_post: NINCS ilyen action.');
}
if (has_action('litespeed_purge_all')) {
    do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva');
} else {
    ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.');
}

ki('');
ki('VISSZAMERES:');
$faV = json_decode(get_post_meta($OLDAL, '_elementor_data', true), true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    $e =& fh_elem($faV, $par['elem_id']);
    $ert = ($e === null) ? null : $e['settings'][$par['ut']];
    if ($ert === $par['uj']) { $ok++; }
    else { $rossz++; ki('  !! ['.$par['elem_id'].'] nem az uj erteket adja vissza'); }
}
ki(sprintf('  %d/%d mezo a vart HTML-t adja vissza.', $ok, $ok + $rossz));
ki($rossz === 0 ? 'ELES MENET VEGE. A szoveg valtozatlan, a formazas helyreallt.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES.');
exit($rossz === 0 ? 0 : 1);
'''


if __name__ == '__main__':
    main()
