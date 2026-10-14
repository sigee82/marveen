<?php
/**
 * 2026-11 (pihento alvas) INGYENES-KIHIVAS LANDING: A HAROM LANDING-KEP CSEREJE.
 * A 2026.10-es landing-17544-kep-csere.php novemberi, dev-first valtozata.
 *
 * MIT CSERELUNK: a harom landing-specifikus kep-slotot (hero, "Mire szamithatsz?", "Mit kapsz
 * meg?"). Az elo 17544 ma (merve 2026-10-14, Playwright, data-id + wp-image-N + data-src):
 *   043088b -> #17548 honlapkep_egeszseges_reggeli_1.png
 *   18e743f -> #17549 honlapkep_egeszseges_reggeli_2.png
 *   62377a6 -> #17550 honlapkep_egeszseges_reggeli_3.png
 * A deven a landing-dev-atvitel.php byte-azonosan viszi at az adatot, tehat ott is EZEK az
 * ID-k allnak az adatban (a dev media-konyvtarban mas poszt is lehet ezen az ID-n -- nem baj,
 * az ellenorzes az ADATOT nezi, a csere uj, sajat feltoltest tesz be).
 * Az ikonokhoz, az emblemahoz es a 3 lepes ikonjaihoz NEM nyulunk.
 *
 *   --site=dev|prod --oldal=<ID>|jelolt --kepek=<mappa> [--ikon]     SZARAZ (kiirja a sha256-okat)
 *   ... --apply --sha=<s1>,<s2>,<s3>                                  ELES a deven
 *   ... --apply --sha=<s1>,<s2>,<s3> --yes-prod                       ELES a prodon (draft masolat)
 *
 * >>> MIERT KOTELEZO A --sha AZ ELES MENETBEN (2026-10-14): ugyanazon a napon a v1 kepeket
 * Eszter elutasitotta, a v2 UGYANAZON a fajlneven es UGYANAZON a Drive-ID-n jott. A fajlnev
 * tehat NEM azonositja a jovahagyott valtozatot. A sha-t a jovahagyott fajlokbol kell venni
 * (a szaraz menet kiirja), es a szkript csak azt tolti fel, ami bitre az. <<<
 *
 * --ikon: a "Mire szamithatsz?" cim feletti IKONT is csereli (3eacd38, ma #13794 2025/12/mire-szamithatsz,
 * a turmixgep-rajz) Lumen holdsarlos ikonjara (mire-szamithatsz-alvas.png, 200x200 -- a sablon eredetijenek
 * merete; a 150x150-es valtozatot a WP maga kesziti). Kulon kapcsolo, mert kulon jovahagyas: ha Eszter a
 * fotokat igen, az ikont nem hagyja jova, a harom foto nelkule is mehet. Ilyenkor a --sha NEGY erteket var.
 * Az eredeti ikont a regi landingek is hasznaljak: NEM irjuk felul, uj mediaelem megy fel (Lumen 20510).
 *
 * A REGI KEPEKET NEM TOROLJUK. A mentes a $HOME-ba megy (nem a webrootba).
 * PROBAPAD: LANDING_CSERE_PROBAPAD=1 + --wp=<gyoker>: CSAK a hoszt-ellenorzest kapcsolja ki.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);

$FORRAS_ID = 17544;
$TILTOTT = array(17544, 17153);
$PROD_IDEIGLENES = 'novemberi-kihivas-eloke';
$KEPEK_TERV = array(
    array('elem' => '043088b', 'slot' => 'HERO',              'vart_id' => 17548, 'vart_nev' => 'honlapkep_egeszseges_reggeli_1', 'fajl' => 'honlapkep_pihentato_alvas_1.png', 'meret' => 900),
    array('elem' => '18e743f', 'slot' => 'Mire szamithatsz?', 'vart_id' => 17549, 'vart_nev' => 'honlapkep_egeszseges_reggeli_2', 'fajl' => 'honlapkep_pihentato_alvas_2.png', 'meret' => 900),
    array('elem' => '62377a6', 'slot' => 'Mit kapsz meg?',    'vart_id' => 17550, 'vart_nev' => 'honlapkep_egeszseges_reggeli_3', 'fajl' => 'honlapkep_pihentato_alvas_3.png', 'meret' => 900),
);
/* Merve 2026-10-14 (Playwright, wp-image-N): a "Mire szamithatsz?" cim feletti ikon a 3eacd38, #13794. */
$IKON_TERV = array('elem' => '3eacd38', 'slot' => 'IKON "Mire szamithatsz?"', 'vart_id' => 13794, 'vart_nev' => 'mire-szamithatsz', 'fajl' => 'mire-szamithatsz-alvas.png', 'meret' => 200);

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$YESPROD = in_array('--yes-prod', $ARGV, true);
if (in_array('--ikon', $ARGV, true)) { $KEPEK_TERV[] = $IKON_TERV; }
$DB = count($KEPEK_TERV);
$SITE = ''; $OLDAL = 0; $WP = ''; $KEPEK = ''; $SHA = array();
foreach ($ARGV as $a) {
    if (strpos($a, '--site=') === 0)  { $SITE = substr($a, 7); }
    if (strpos($a, '--oldal=') === 0) { $OLDAL = substr($a, 8) === 'jelolt' ? -1 : (int) substr($a, 8); }
    if (strpos($a, '--wp=') === 0)    { $WP = rtrim(substr($a, 5), '/'); }
    if (strpos($a, '--kepek=') === 0) { $KEPEK = rtrim(substr($a, 8), '/'); }
    if (strpos($a, '--sha=') === 0)   { $SHA = array_map('strtolower', array_map('trim', explode(',', substr($a, 6)))); }
}
$PROBAPAD = getenv('LANDING_CSERE_PROBAPAD') === '1';
if ($PROBAPAD && getenv('LANDING_FORRAS')) { $FORRAS_ID = (int) getenv('LANDING_FORRAS'); }
function ki($s){ echo '@@ '.$s."\n"; }
$HOSTOK = array('dev' => 'dev.21napalatt.hu', 'prod' => 'vip.21napalatt.hu');
if (!isset($HOSTOK[$SITE])) { ki('!! KOTELEZO a --site=dev|prod.'); exit(2); }
if ($WP !== '' && !$PROBAPAD) { ki('!! A --wp csak probapadon (LANDING_CSERE_PROBAPAD=1) adhato meg.'); exit(2); }
if ($WP === '') { $WP = '/home/napalatt/'.$HOSTOK[$SITE]; }
if (!file_exists($WP.'/wp-load.php')) { ki('!! nincs wp-load.php: '.$WP); exit(2); }
require_once $WP.'/wp-load.php';
require_once ABSPATH . 'wp-admin/includes/file.php';
require_once ABSPATH . 'wp-admin/includes/media.php';
require_once ABSPATH . 'wp-admin/includes/image.php';
error_reporting(E_ERROR | E_PARSE);

$host = (string) parse_url(home_url(), PHP_URL_HOST);
ki('LANDING 2026-11 KEP-CSERE  '.gmdate('c').' UTC   site='.$SITE.'  home='.home_url().'  DB='.DB_NAME);
if ($PROBAPAD) { ki('*** PROBAPAD: a hoszt-ellenorzes KI van kapcsolva (a cel-orok elnek). ***'); }
ki($APPLY ? '*** ELES MENET: IRNI ES FELTOLTENI FOG ***' : 'SZARAZ MENET: semmit nem ir, semmit nem tolt fel');
if (!$PROBAPAD && $host !== $HOSTOK[$SITE]) { ki('!! --site='.$SITE.', de ez a telepites: '.$host.'. ALLJ MEG.'); exit(2); }
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
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is.'); exit(2); }
if (in_array($OLDAL, $TILTOTT, true) && $SITE === 'prod') { ki('!! A '.$OLDAL.' elo vagy korabbi landing -- NEM irunk ra.'); exit(2); }
if ($KEPEK === '' || !is_dir($KEPEK)) { ki('!! KOTELEZO a --kepek=<letezo mappa> (a szerveren).'); exit(2); }
$p = get_post($OLDAL);
if (!$p) { ki('!! a '.$OLDAL.' nem letezik.'); exit(2); }
ki('celpont: '.$OLDAL.'  slug='.$p->post_name.'  status='.$p->post_status.'  cim='.$p->post_title);
if ($SITE === 'dev' && get_post_meta($OLDAL, '_landing_atvitel_forras', true) !== (string) $FORRAS_ID) {
    ki('!! A deven csak a landing-dev-atvitel.php altal atvitt oldalra irok.'); exit(2);
}
if ($SITE === 'prod' && ($p->post_name !== $PROD_IDEIGLENES || $p->post_status !== 'draft')) {
    ki('!! A prodon csak a draft, "'.$PROD_IDEIGLENES.'" slugu masolatra irok. Ez nem az.'); exit(2);
}
if ($APPLY && $SITE === 'prod' && !$YESPROD) { ki('!! Prod iras csak --yes-prod-dal (Zsolt OK utan).'); exit(2); }
if ($APPLY && count($SHA) !== $DB) {
    ki('!! Az eles menethez KOTELEZO a --sha= '.$DB.' ertekkel, a fenti sorrendben (a JOVAHAGYOTT fajlok sha256-janak eleje,');
    ki('   legalabb 8 jegy). A fajlnev nem azonositja a valtozatot: 2026-10-14-en a v1 es a v2 ugyanazon a neven jott.');
    exit(2);
}
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
        if ($k === 'settings' || !is_array($gy)) { continue; }
        $t =& kk_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}

/* 1. ELLENORZES: semmi nem toltodik fel, amig mind a harom elem es fajl rendben nincs. */
$hiba = 0;
foreach ($KEPEK_TERV as $i => $t) {
    $ut = $KEPEK.'/'.$t['fajl'];
    if (!is_readable($ut)) { ki(sprintf('  !! [%s] nincs meg a fajl: %s', $t['elem'], $ut)); $hiba++; continue; }
    $meret = @getimagesize($ut);
    if (!$meret || $meret[2] !== IMAGETYPE_PNG) { ki(sprintf('  !! [%s] nem PNG: %s', $t['elem'], $ut)); $hiba++; continue; }
    if ($meret[0] !== $t['meret'] || $meret[1] !== $t['meret']) {
        ki(sprintf('  !! [%s] %dx%d, nem %dx%d', $t['elem'], $meret[0], $meret[1], $t['meret'], $t['meret'])); $hiba++; continue;
    }
    $sha = hash_file('sha256', $ut);
    if ($SHA) {
        $vart = isset($SHA[$i]) ? $SHA[$i] : '';
        if (strlen($vart) < 8 || strpos($sha, $vart) !== 0) {
            ki(sprintf('  !! [%s] %s sha256=%s, a megadott: %s -- NEM a jovahagyott valtozat', $t['elem'], $t['fajl'], substr($sha, 0, 12), $vart));
            $hiba++; continue;
        }
    }
    $e =& kk_elem($fa, $t['elem']);
    if ($e === null) { ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon', $t['elem'])); $hiba++; unset($e); continue; }
    $kep = isset($e['settings']['image']) ? $e['settings']['image'] : null;
    unset($e);
    if (!is_array($kep) || !isset($kep['id']) || !isset($kep['url'])) { ki(sprintf('  !! [%s] nincs settings.image.id/url', $t['elem'])); $hiba++; continue; }
    if ((int) $kep['id'] !== $t['vart_id'] || strpos($kep['url'], $t['vart_nev']) === false) {
        ki(sprintf('  !! [%s] a mai kep #%d %s, a vart #%d %s -- az oldal elmozdult, KIHAGYVA',
            $t['elem'], (int) $kep['id'], basename($kep['url']), $t['vart_id'], $t['vart_nev'])); $hiba++; continue;
    }
    ki(sprintf('  [%s] %s', $t['elem'], $t['slot']));
    ki(sprintf('        regi: #%d %s', (int) $kep['id'], basename($kep['url'])));
    ki(sprintf('        uj:   %s (%dx%d, %d byte, sha256=%s)', $t['fajl'], $meret[0], $meret[1], filesize($ut), substr($sha, 0, 8)));
}
if ($hiba > 0) { ki(''); ki(sprintf('!! %d ELLENORZES BUKOTT -- semmit nem toltunk fel es nem irunk.', $hiba)); exit(1); }
if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Az eleshez a fenti sha256-okat add at --sha=...-ként (ebben a sorrendben), ha EZEK a jovahagyott kepek.'); exit(0); }

/* 2. FELTOLTES (a sideload elviszi a forrast, ezert masolatot kap). */
$ujak = array();
foreach ($KEPEK_TERV as $t) {
    $temp = wp_tempnam($t['fajl']);
    if (!$temp || !copy($KEPEK.'/'.$t['fajl'], $temp)) { ki('!! a temp masolat elbukott: '.$t['fajl']); exit(1); }
    $id = media_handle_sideload(array('name' => $t['fajl'], 'type' => 'image/png', 'tmp_name' => $temp), 0);
    if (is_wp_error($id)) {
        @unlink($temp);
        ki('!! a feltoltes elbukott ('.$t['fajl'].'): '.$id->get_error_message().' -- az oldalhoz MEG NEM nyultunk.');
        exit(1);
    }
    update_post_meta($id, '_wp_attachment_image_alt', '');
    $ujak[$t['elem']] = array('id' => (int) $id, 'url' => wp_get_attachment_url($id));
    ki(sprintf('  feltoltve: %s -> #%d %s', $t['fajl'], $id, $ujak[$t['elem']]['url']));
}

/* 3. AZ OLDAL. Mentes eloszor, a $HOME-ba. */
$home = getenv('HOME') ?: dirname($WP);
$mentes = rtrim($home, '/').'/landing-kep-mentes-'.$SITE.'-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');
foreach ($KEPEK_TERV as $t) {
    $e =& kk_elem($fa, $t['elem']);
    $e['settings']['image']['id'] = $ujak[$t['elem']]['id'];
    $e['settings']['image']['url'] = $ujak[$t['elem']]['url'];
    unset($e);
}
$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($OLDAL, '_elementor_data', wp_slash($uj));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) { delete_post_meta($OLDAL, $mk); }
clean_post_cache($OLDAL);
if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $OLDAL); ki('litespeed_purge_post: kiadva'); }
else { ki('litespeed_purge_post: NINCS ilyen action'); }
if (has_action('litespeed_purge_all')) { do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva'); }
else { ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.'); }

ki('');
ki('VISSZAMERES:');
$faV = json_decode(get_post_meta($OLDAL, '_elementor_data', true), true);
$ok = 0;
foreach ($KEPEK_TERV as $t) {
    $e =& kk_elem($faV, $t['elem']);
    $kep = ($e === null) ? null : $e['settings']['image'];
    unset($e);
    $vart = $ujak[$t['elem']];
    if (is_array($kep) && (int) $kep['id'] === $vart['id'] && $kep['url'] === $vart['url']) {
        $ok++; ki(sprintf('  [%s] #%d %s', $t['elem'], $vart['id'], basename($vart['url'])));
    } else { ki(sprintf('  !! [%s] NEM az uj kepet adja vissza', $t['elem'])); }
}
ki(sprintf('  %d/%d kep-mezo a vart uj erteket adja.', $ok, $DB));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($OLDAL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki($ok === $DB ? 'ELES MENET VEGE. Mind a(z) '.$DB.' kep a helyen.' : '!! ELES MENET VEGE, DE VOLT ELTERES.');
exit($ok === $DB ? 0 : 1);
