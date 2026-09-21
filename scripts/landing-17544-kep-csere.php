<?php
/**
 * 17544 -- /ingyenes-kihivas/ (Egeszseges reggeli 2026.10): A HAROM KEP CSEREJE.
 *
 * MIT CSERELUNK ES MIERT: az oldal ma a `honlapkep_meal_prep_1/2/3.png` fajlokat hordozza
 * (2026/08-as feltoltes) -- vagyis egy REGGELI landingen elokeszitett EBEDEK latszanak.
 * A harom uj kep Lumentol van, mind 900x900 PNG, ugyanaz a meret, mint a regieke, tehat
 * a szarmaztatott meretek (550, 768, 150) es a srcset alakja valtozatlan marad.
 *
 * AMIHEZ NEM NYULUNK: az ikonok, az emblema es a 3 lepes ikonjai (2025/12-es allando
 * elemek, minden landingen ugyanazok). Ezert NEM fajlnev-csere megy az egesz oldalon,
 * hanem HAROM NEVESITETT ELEM harom nevesitett mezoje.
 *
 *   (alapertelmezes)  SZARAZ: semmit nem ir, csak megmutatja, mi tortenne
 *   --apply           ELES
 *   --oldal=17544     KOTELEZO
 *   --kepek=<dir>     KOTELEZO -- a szerveren levo mappa a harom PNG-vel
 *
 * A REGI KEPEKET NEM TOROLJUK. A media-konyvtarban maradnak: ha valami elcsuszik, a
 * visszaallas egy mentesbol visszaolvasott `_elementor_data`, nem egy ujrafeltoltes.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once getenv('WP_LOAD') ?: '/home/napalatt/vip.21napalatt.hu/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$OLDAL = 0; $KEPEK = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); }
    if (strpos($a, '--kepek=') === 0) { $KEPEK = rtrim(substr($a, 8), '/'); }
}
$TILTOTT = 17153;
$MENTES_DIR = getenv('MENTES_DIR') ?: '/home/napalatt/vip.21napalatt.hu';

/* elem_id => [ a VART mai allapot, az uj fajl ].  A vart allapot 2026-09-21-en az elo
   oldal DOM-jabol merve (data-id szerint), nem feltetelezve. */
$KEPEK_TERV = array(
    array('elem' => '043088b', 'slot' => 'HERO',
          'vart_id' => 17163, 'vart_nev' => 'honlapkep_meal_prep_1',
          'fajl' => 'honlapkep_egeszseges_reggeli_1.png'),
    array('elem' => '18e743f', 'slot' => 'Mire szamithatsz?',
          'vart_id' => 17164, 'vart_nev' => 'honlapkep_meal_prep_2',
          'fajl' => 'honlapkep_egeszseges_reggeli_2.png'),
    array('elem' => '62377a6', 'slot' => 'Mit kapsz meg?',
          'vart_id' => 17165, 'vart_nev' => 'honlapkep_meal_prep_3',
          'fajl' => 'honlapkep_egeszseges_reggeli_3.png'),
);

ki('LANDING 17544 KEP-CSERE  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');
if ($OLDAL === $TILTOTT) { ki('!! a REGI meal-prep landing ('.$TILTOTT.') -- NEM irunk ra.'); exit(2); }
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is.'); exit(2); }
if ($KEPEK === '' || !is_dir($KEPEK)) { ki('!! KOTELEZO a --kepek=<letezo mappa>.'); exit(2); }
$p = get_post($OLDAL);
if (!$p) { ki('!! a '.$OLDAL.' nem letezik.'); exit(2); }
ki('celpont: '.$OLDAL.'  slug='.$p->post_name.'  status='.$p->post_status);
ki('kepek:   '.$KEPEK);
ki('');

$d = get_post_meta($OLDAL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data'); exit(2); }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit(2); }

function &kk_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings') { continue; }
        if (!is_array($gy)) { continue; }
        $t =& kk_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}

/* 1. MENET: ELLENORZES. Egyetlen kep sem toltodik fel, amig MIND A HAROM elem a vart
   allapotban nincs. Reszleges kep-csere rosszabb, mint a regi harom: az oldal fele
   reggeli, fele ebed lenne, es ez nem latszik meg semmilyen szamon. */
$hiba = 0;
foreach ($KEPEK_TERV as $t) {
    $ut = $KEPEK.'/'.$t['fajl'];
    if (!is_readable($ut)) { ki(sprintf('  !! [%s] nincs meg a fajl: %s', $t['elem'], $ut)); $hiba++; continue; }
    $meret = @getimagesize($ut);
    if (!$meret || $meret[2] !== IMAGETYPE_PNG) { ki(sprintf('  !! [%s] nem PNG: %s', $t['elem'], $ut)); $hiba++; continue; }
    if ($meret[0] !== 900 || $meret[1] !== 900) {
        ki(sprintf('  !! [%s] %dx%d, nem 900x900 -- a regiek 900x900-ak, a srcset elcsuszna',
            $t['elem'], $meret[0], $meret[1])); $hiba++; continue;
    }
    $e =& kk_elem($fa, $t['elem']);
    if ($e === null) { ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon', $t['elem'])); $hiba++; continue; }
    $kep = isset($e['settings']['image']) ? $e['settings']['image'] : null;
    if (!is_array($kep) || !isset($kep['id']) || !isset($kep['url'])) {
        ki(sprintf('  !! [%s] nincs settings.image.id/url', $t['elem'])); $hiba++; continue;
    }
    if ((int) $kep['id'] !== $t['vart_id']) {
        ki(sprintf('  !! [%s] a mai attachment %d, a vart %d -- az oldal elmozdult, KIHAGYVA',
            $t['elem'], (int) $kep['id'], $t['vart_id'])); $hiba++; continue;
    }
    if (strpos($kep['url'], $t['vart_nev']) === false) {
        ki(sprintf('  !! [%s] a mai url nem %s-t hordoz: %s', $t['elem'], $t['vart_nev'], $kep['url']));
        $hiba++; continue;
    }
    ki(sprintf('  [%s] %s', $t['elem'], $t['slot']));
    ki(sprintf('        regi: #%d %s', (int) $kep['id'], basename($kep['url'])));
    ki(sprintf('        uj:   %s (%dx%d, %d byte)', $t['fajl'], $meret[0], $meret[1], filesize($ut)));
}

if ($hiba > 0) {
    ki('');
    ki(sprintf('!! %d ELLENORZES BUKOTT -- semmit nem toltunk fel es nem irunk.', $hiba));
    exit(1);
}
if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk, semmit nem toltottunk fel.'); exit(0); }

/* 2. MENET: FELTOLTES. A media_handle_sideload ELVISZI a forrasfajlt, ezert masolatot
   adunk neki -- az eredeti a mappaban marad, ujrafuttathatoan. */
$ujak = array();
foreach ($KEPEK_TERV as $t) {
    $forras = $KEPEK.'/'.$t['fajl'];
    $temp = wp_tempnam($t['fajl']);
    if (!$temp || !copy($forras, $temp)) { ki('!! a temp masolat elbukott: '.$t['fajl']); exit(1); }
    $id = media_handle_sideload(
        array('name' => $t['fajl'], 'type' => 'image/png', 'tmp_name' => $temp), 0);
    if (is_wp_error($id)) {
        @unlink($temp);
        ki('!! a feltoltes elbukott ('.$t['fajl'].'): '.$id->get_error_message());
        ki('   A korabban mar feltoltott kepek a media-konyvtarban maradtak, de az');
        ki('   oldalhoz MEG NEM nyultunk -- az oldal valtozatlan.');
        exit(1);
    }
    update_post_meta($id, '_wp_attachment_image_alt', '');
    $ujak[$t['elem']] = array('id' => (int) $id, 'url' => wp_get_attachment_url($id));
    ki(sprintf('  feltoltve: %s -> #%d %s', $t['fajl'], $id, $ujak[$t['elem']]['url']));
}

/* 3. MENET: AZ OLDAL. Mentes eloszor. */
$mentes = $MENTES_DIR.'/landing-kep-mentes-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

foreach ($KEPEK_TERV as $t) {
    $e =& kk_elem($fa, $t['elem']);
    $e['settings']['image']['id'] = $ujak[$t['elem']]['id'];
    $e['settings']['image']['url'] = $ujak[$t['elem']]['url'];
}
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
   mint egy landing, ami az inditas napjan valtozatlannak latszik. */
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
foreach ($KEPEK_TERV as $t) {
    $e =& kk_elem($faV, $t['elem']);
    $kep = ($e === null) ? null : $e['settings']['image'];
    $vart = $ujak[$t['elem']];
    if (is_array($kep) && (int) $kep['id'] === $vart['id'] && $kep['url'] === $vart['url']) {
        $ok++;
        ki(sprintf('  [%s] #%d %s', $t['elem'], $vart['id'], basename($vart['url'])));
    } else {
        $rossz++;
        ki(sprintf('  !! [%s] NEM az uj kepet adja vissza', $t['elem']));
    }
}
ki(sprintf('  %d/3 kep-mezo a vart uj erteket adja.', $ok));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($OLDAL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Mind a harom kep a helyen.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
exit($rossz === 0 ? 0 : 1);
