<?php
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

$PAROK = array(
  array('elem_id' => 'ed700ab', 'ut' => 'editor', 'mai' => 'Regisztrálj most, a kihívás teljesen ingyenes.
Indulás: 2026. október 1.', 'uj' => '<p><strong>Regisztrálj most, a kihívás teljesen ingyenes.</strong> <br>Indulás: 2026. október 1.</p>'),
  array('elem_id' => '8c97ba3', 'ut' => 'editor', 'mai' => 'Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor ismételsz, akkor az szokássá válik. A megfelelő önfegyelemmel egy felnőtt embernek tizennégy és huszonegy nap közötti időre van szüksége ahhoz, hogy egy új szokást kialakítson. Ez idő alatt pedig rendszeresen kell ismételni az adott cselekvést. Az ingyenes kihívásban ehhez kapsz egy óriási lökést, és ha tetszik, folytasd tovább!
Nem az a cél, hogy egyik napról a másikra mindent megváltoztass, hanem az, hogy megtapasztald, működik-e neked ez a fajta reggeli, egyszerűbb-e így reggelente jól dönteni.
A 21napalatt VIP Klubban nem állunk meg 7 napnál, további 14 napig építjük együtt a reggeli-rendszeredet a zárt klubban. Ha kedvet kapsz, Téged is sok szeretettel várunk, csatlakozz hozzánk!', 'uj' => '<p>Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor ismételsz, akkor az szokássá válik. A megfelelő önfegyelemmel egy felnőtt embernek tizennégy és huszonegy nap közötti időre van szüksége ahhoz, hogy egy új szokást kialakítson. Ez idő alatt pedig rendszeresen kell ismételni az adott cselekvést. Az ingyenes kihívásban ehhez kapsz egy óriási lökést, és ha tetszik, folytasd tovább!</p><p>Nem az a cél, hogy egyik napról a másikra mindent megváltoztass, hanem az, hogy megtapasztald, működik-e neked ez a fajta reggeli, egyszerűbb-e így reggelente jól dönteni.</p><p>A 21napalatt VIP Klubban nem állunk meg 7 napnál, további 14 napig építjük együtt a reggeli-rendszeredet a zárt klubban. Ha kedvet kapsz, Téged is sok szeretettel várunk, csatlakozz hozzánk!</p>'),
  array('elem_id' => '6a0ce87', 'ut' => 'editor', 'mai' => 'Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan eheted és ihatod ugyanazokat, amiket korábban is, mindössze a reggelidet rakjuk össze együtt egy kicsit másképp.', 'uj' => '<p>Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan eheted és ihatod ugyanazokat, amiket korábban is, mindössze a reggelidet rakjuk össze együtt egy kicsit másképp.</p>'),
  array('elem_id' => '1cfd5a8', 'ut' => 'editor', 'mai' => 'Készíts fotót az elkészült reggelidről.
Posztold a kihívás Facebook csoportjában a @21napalatt_kihivas hashtaggel
Október 8-án a legalább 1 képet feltöltők között kisorsolunk egy szerencsés résztvevőt,
aki 1 hónapos 21napalatt VIP Klub előfizetést nyer.
A 21napalatt VIP Klubtagság teljes hozzáférést ad a klub minden tartalmához: 21 napos életmódprogramhoz, a hetente frissülő menütervekhez, 500+ tej-, cukor- és gluténmentes recepthez, 21 napos kihívásokhoz, tudásanyagokhoz, a zárt Facebook csoporthoz.', 'uj' => '<ul><li><strong>Készíts fotót az elkészült reggelidről.</strong></li><li><strong>Posztold a kihívás Facebook csoportjában a @21napalatt_kihivas hashtaggel</strong></li></ul><p>Október 8-án a legalább 1 képet feltöltők között kisorsolunk egy szerencsés résztvevőt,<br>aki 1 hónapos 21napalatt VIP Klub előfizetést nyer.</p><p>A 21napalatt VIP Klubtagság teljes hozzáférést ad a klub minden tartalmához: 21 napos életmódprogramhoz, a hetente frissülő menütervekhez, 500+ tej-, cukor- és gluténmentes recepthez, 21 napos kihívásokhoz, tudásanyagokhoz, a zárt Facebook csoporthoz.</p>')
);

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
