<?php
/**
 * 17544 VISSZAALLITAS a csere-szkriptek altal irt mentesbol.
 *
 * MIERT KELL KULON SZKRIPT: a mentes a `_elementor_data` NYERS tarolt erteke. Egy kezi
 * `wp post meta update` mashogy slashelne, es a visszaallitas csendben elrontana a JSON-t
 * -- az oldal pedig ures Elementor-tartalommal jonne vissza. Itt a beolvasas dekodolassal
 * ELLENORZOTT: ha a mentes nem ervenyes JSON, nem irunk.
 *
 *   php -- --oldal=17544 --mentes=<fajl>            SZARAZ
 *   php -- --apply --oldal=17544 --mentes=<fajl>    ELES
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once getenv('WP_LOAD') ?: '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$APPLY = in_array('--apply', $argv, true);
$OLDAL = 0; $MENTES = '';
foreach ($argv as $a) {
    if (strpos($a, '--oldal=')  === 0) { $OLDAL  = (int) substr($a, 8); }
    if (strpos($a, '--mentes=') === 0) { $MENTES = substr($a, 9); }
}
if ($OLDAL <= 0)                 { ki('!! KOTELEZO a --oldal=<ID>.'); exit(2); }
if ($MENTES === '' || !is_readable($MENTES)) { ki('!! KOTELEZO a --mentes=<letezo fajl>.'); exit(2); }

$tartalom = file_get_contents($MENTES);
$fa = json_decode($tartalom, true);
if (!is_array($fa) || $fa === array()) {
    ki('!! a mentes nem ervenyes, nem ures Elementor-JSON -- NEM IRUNK.'); exit(1);
}
$most = get_post_meta($OLDAL, '_elementor_data', true);
ki(sprintf('oldal %d: mostani %d byte  <-  mentes %d byte (%d gyoker-szekcio)',
    $OLDAL, strlen((string) $most), strlen($tartalom), count($fa)));
if (!$APPLY) { ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit(0); }

update_post_meta($OLDAL, '_elementor_data', wp_slash($tartalom));
delete_post_meta($OLDAL, '_elementor_css');
delete_post_meta($OLDAL, '_elementor_page_assets');
if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $OLDAL); ki('litespeed purge: kiadva'); }

$vissza = get_post_meta($OLDAL, '_elementor_data', true);
$egyezik = ($vissza === $tartalom);
ki('visszameres: a tarolt ertek '.($egyezik ? 'BYTE-RA egyezik a mentessel.' : '!! NEM egyezik a mentessel.'));
exit($egyezik ? 0 : 1);
