<?php
/**
 * AZ AKTUALIS LANDING ATVITELE A DEV WP-RE, HOGY A HAVI SZOVEG-CSERE ELOSZOR OTT FUSSON.
 *
 * MIERT KELL (merve 2026-10-14, Bit): a dev.21napalatt.hu-n sem a 17544, sem a 17153 nem letezik
 * (mindketto 404), a /ingyenes-kihivas/ ott a /ingyenes-kihivasok/-ra (9532) dob. A landing
 * tartalma a WP ADATBAZISABAN el (`_elementor_data`), nem a 21napalattvip repoban, tehat a
 * "Deploy to Dev" nem viszi at. Az "elobb dev, aztan prod" szabalyhoz ezert az oldalt magat
 * kell atvinni. Ugyanaz a szerver, ket kulon WP-telepites es ket kulon DB: az atvitel egy
 * fajlon at megy, amit a prod-oldali export ir es a dev-oldali import olvas.
 *
 *   --export --wp=/home/napalatt/vip.21napalatt.hu
 *        PROD, CSAK OLVAS a DB-bol. A forras-oldalt (post-mezok + minden NEM generalt meta) egy
 *        JSON-fajlba irja (alapertelmezes: ~/landing-atvitel-<FORRAS>.json), es kiirja a sha256
 *        elejet. Az eles oldalt nem erinti: elotte-utana ujjlenyomatot mer, es osszeveti.
 *
 *   --wp=/home/napalatt/dev.21napalatt.hu                 (import, SZARAZ: semmit nem ir)
 *   --wp=/home/napalatt/dev.21napalatt.hu --apply         (import, ELES a deven)
 *        A dev-en letrehozza az oldalt PUBLIKUSAN a /ingyenes-kihivas/ uton (Eszter bejelentkezes
 *        nelkul nezi), es jelolo-metat tesz ra (`_landing_atvitel_forras`). A szoveg-csere szkript
 *        deven CSAK jelolt oldalra hajlando irni.
 *
 *   --wp=/home/napalatt/dev.21napalatt.hu --visszaallit --apply
 *        A MAR ATVITT dev-oldal `_elementor_data`-jat visszaallitja a fajlbol (a forras allapotara).
 *        Erre akkor van szukseg, ha a szoveg ujabb kort kap: a csere-szkript horgonyai a FORRAS
 *        szoveget varjak, egy mar atirt mezot kihagy. Masodik oldal NEM keszul.
 *
 * AMI NEM MEGY AT, ES KI KELL MONDANI:
 *  - A KEPEK: az Elementor-adat abszolut URL-lel hivatkozik a prod feltolteseire, tehat a deven
 *    is a prod kepei latszanak. Az attachment-ID-k a deven mas posztra mutathatnak; a szkript
 *    megszamolja, hany egyezik.
 *  - A KINEZET: a globalis szinek/betuk a WP Kitbol jonnek. Ha a dev Kitjebol hianyzik egy
 *    hivatkozott globalis ID, ott az Elementor alapertelmezest rajzol. A szkript ezt LISTAZZA;
 *    a vizualis egyezest nem tudja bizonyitani -- azt a dev-elonezetnel jelolni kell.
 *  - Az URLAP a dev telepites sajat beallitasaval fut (dev-regisztracio, nem prod).
 *
 * PROBAPAD: a LANDING_ATVITEL_PROBAPAD=1 kornyezeti valtozo a hoszt-ellenorzest kapcsolja ki
 * (lokalis WP-n az export es az import ugyanaz a telepites). Kapcsolo helyett env, mert eles
 * futasban senki nem irja be veletlenul -- es ha be van allitva, a kimenet elso sora mondja.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);

$ARGV = $argv ?: array();
$EXPORT    = in_array('--export', $ARGV, true);
$APPLY     = in_array('--apply', $ARGV, true);
$VISSZA    = in_array('--visszaallit', $ARGV, true);
$WP = ''; $FAJL = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--wp=') === 0)   { $WP = rtrim(substr($a, 5), '/'); }
    if (strpos($a, '--fajl=') === 0) { $FAJL = substr($a, 7); }
}
$FORRAS   = (int) (getenv('LANDING_FORRAS') ?: 17544);
$PROBAPAD = getenv('LANDING_ATVITEL_PROBAPAD') === '1';
$PROD_HOST = 'vip.21napalatt.hu';
$DEV_HOST  = 'dev.21napalatt.hu';
$DEV_SLUG  = 'ingyenes-kihivas';
$JELOLO    = '_landing_atvitel_forras';
$NEM_MASOLANDO = array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache',
                       '_edit_lock', '_edit_last', '_wp_old_slug', '_proba_forras_ujjlenyomat',
                       '_proba_eldobhato');

function ki($s) { echo '@@ '.$s."\n"; }
if ($WP === '') { ki('!! KOTELEZO a --wp=<a WP gyokere>. Nem talalgatok, melyik telepites.'); exit(2); }
if (!file_exists($WP.'/wp-load.php')) { ki('!! Nincs wp-load.php itt: '.$WP); exit(2); }
if ($FAJL === '') {
    $home = getenv('HOME') ?: dirname($WP);
    $FAJL = rtrim($home, '/').'/landing-atvitel-'.$FORRAS.'.json';
}
require_once $WP.'/wp-load.php';
error_reporting(E_ERROR | E_PARSE);

$host = (string) parse_url(home_url(), PHP_URL_HOST);
ki('LANDING-ATVITEL  '.gmdate('c').' UTC   home='.home_url().'  DB='.DB_NAME);
if ($PROBAPAD) { ki('*** PROBAPAD: a hoszt-ellenorzes KI van kapcsolva (LANDING_ATVITEL_PROBAPAD=1). ***'); }

function elementorInfo() {
    $kit = (int) get_option('elementor_active_kit');
    $ps  = $kit ? get_post_meta($kit, '_elementor_page_settings', true) : array();
    $ids = array();
    if (is_array($ps)) {
        foreach (array('system_colors', 'custom_colors', 'system_typography', 'custom_typography') as $k) {
            if (!empty($ps[$k]) && is_array($ps[$k])) {
                foreach ($ps[$k] as $e) { if (!empty($e['_id'])) { $ids[] = (string) $e['_id']; } }
            }
        }
    }
    return array(
        'elementor'     => defined('ELEMENTOR_VERSION') ? ELEMENTOR_VERSION : null,
        'elementor_pro' => defined('ELEMENTOR_PRO_VERSION') ? ELEMENTOR_PRO_VERSION : null,
        'kit_id'        => $kit,
        'kit_global_ids'=> array_values(array_unique($ids)),
    );
}

/** Az Elementor-adatbol a globalis hivatkozasok, a kep-ID-k es a prod-hoszt URL-ek. */
function adatHivatkozasok($adat, $prodHost) {
    /* A tarolt JSON a perjelet `\/` alakban is hordozhatja (wp_json_encode) -- mindkettot nezzuk. */
    preg_match_all('#globals\\\\?/(?:colors|typography)\?id=([A-Za-z0-9_-]+)#', $adat, $g);
    $fa = json_decode($adat, true);
    $kepek = array();
    $jar = function ($n) use (&$jar, &$kepek) {
        if (!is_array($n)) { return; }
        if (isset($n['url'], $n['id']) && is_string($n['url']) && is_numeric($n['id'])
            && preg_match('#/wp-content/uploads/#', $n['url'])) {
            $kepek[(int) $n['id']] = $n['url'];
        }
        foreach ($n as $v) { $jar($v); }
    };
    $jar($fa);
    return array(
        'globalis_idk' => array_values(array_unique($g[1])),
        'kepek'        => $kepek,
        'prod_url_db'  => substr_count(str_replace('\\/', '/', $adat), '//'.$prodHost.'/'),
    );
}

/* ================================================================ EXPORT (prod, csak olvas) */
if ($EXPORT) {
    if (!$PROBAPAD && $host !== $PROD_HOST) {
        ki('!! Az export a PROD-rol megy ('.$PROD_HOST.'), ez a telepites: '.$host.'. ALLJ MEG.'); exit(2);
    }
    if ($APPLY || $VISSZA) { ki('!! Az --export mellett nincs --apply/--visszaallit: az export nem ir a DB-be.'); exit(2); }
    $p = get_post($FORRAS);
    if (!$p) { ki('!! A forras ('.$FORRAS.') nem letezik.'); exit(2); }
    ki(sprintf('FORRAS: ID=%d  slug=%s  statusz=%s  modositva(GMT)=%s  cim=%s',
        $p->ID, $p->post_name, $p->post_status, $p->post_modified_gmt, $p->post_title));
    $elotte = array($p->post_modified_gmt, strlen((string) get_post_meta($FORRAS, '_elementor_data', true)));

    global $wpdb;
    $sorok = $wpdb->get_results($wpdb->prepare(
        "SELECT meta_key, meta_value FROM {$wpdb->postmeta} WHERE post_id=%d ORDER BY meta_id", $FORRAS));
    $metak = array(); $kihagy = array();
    foreach ($sorok as $s) {
        if (in_array($s->meta_key, $NEM_MASOLANDO, true)) { $kihagy[] = $s->meta_key; continue; }
        $metak[] = array('k' => $s->meta_key, 'v' => $s->meta_value);   // NYERS DB-ertek (szerializalt marad)
    }
    $adat = (string) get_post_meta($FORRAS, '_elementor_data', true);
    if ($adat === '' || !is_array(json_decode($adat, true))) { ki('!! A forras _elementor_data ures vagy nem dekodolhato.'); exit(2); }
    $csomag = array(
        'forras_id'   => $FORRAS,
        'forras_host' => $host,
        'mikor_utc'   => gmdate('c'),
        'post'        => array(
            'post_type' => $p->post_type, 'post_title' => $p->post_title, 'post_name' => $p->post_name,
            'post_content' => $p->post_content, 'post_excerpt' => $p->post_excerpt,
            'comment_status' => $p->comment_status, 'ping_status' => $p->ping_status,
            'menu_order' => (int) $p->menu_order, 'post_modified_gmt' => $p->post_modified_gmt,
        ),
        'metak'       => $metak,
        'elementor'   => elementorInfo(),
        'hivatkozas'  => adatHivatkozasok($adat, $PROD_HOST),
        'adat_sha256' => hash('sha256', $adat),
        'adat_byte'   => strlen($adat),
    );
    $json = json_encode($csomag, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if (!is_string($json)) { ki('!! A csomag JSON-kodolasa elbukott: '.json_last_error_msg()); exit(2); }
    $tmp = $FAJL.'.tmp';
    if (file_put_contents($tmp, $json) === false || !rename($tmp, $FAJL)) { ki('!! Nem tudtam irni: '.$FAJL); exit(2); }
    ki(sprintf('IRVA: %s  (%d byte, sha256=%s)', $FAJL, strlen($json), substr(hash('sha256', $json), 0, 8)));
    ki(sprintf('  meta: %d kulcs viszunk, kihagyva (generalt): %s', count($metak),
        $kihagy ? implode(', ', array_unique($kihagy)) : '(egy sem volt)'));
    ki(sprintf('  _elementor_data: %d byte, sha256=%s', $csomag['adat_byte'], substr($csomag['adat_sha256'], 0, 8)));
    $e = $csomag['elementor']; $h = $csomag['hivatkozas'];
    ki(sprintf('  Elementor %s / Pro %s, Kit ID=%d (%d globalis ID)', $e['elementor'] ?: 'NINCS',
        $e['elementor_pro'] ?: 'NINCS', $e['kit_id'], count($e['kit_global_ids'])));
    ki(sprintf('  hivatkozasok: %d globalis ID, %d kep-attachment, %d prod-hoszt URL',
        count($h['globalis_idk']), count($h['kepek']), $h['prod_url_db']));
    clean_post_cache($FORRAS);
    $p2 = get_post($FORRAS);
    $utana = array($p2->post_modified_gmt, strlen((string) get_post_meta($FORRAS, '_elementor_data', true)));
    ki($elotte === $utana ? 'AZ ELES OLDAL VALTOZATLAN (modositva + adat-meret azonos).'
                          : '!! AZ ELES OLDAL ELMOZDULT AZ EXPORT ALATT: '.json_encode($elotte).' -> '.json_encode($utana));
    ki('EXPORT VEGE. A DB-be semmit nem irtunk.');
    exit(0);
}

/* ================================================================ IMPORT (dev) */
if (!$PROBAPAD && $host !== $DEV_HOST) {
    ki('!! Az import CSAK a devre megy ('.$DEV_HOST.'), ez a telepites: '.$host.'. NEM IROK.'); exit(2);
}
ki($APPLY ? ($VISSZA ? '*** VISSZAALLITO MENET: IRNI FOG ***' : '*** IMPORT: IRNI FOG ***') : 'SZARAZ MENET: semmit nem ir');
if (!file_exists($FAJL)) { ki('!! Nincs meg az export-fajl: '.$FAJL.' -- elobb a prodon: --export'); exit(2); }
$nyers = file_get_contents($FAJL);
$cs = json_decode($nyers, true);
if (!is_array($cs) || empty($cs['metak'])) { ki('!! Az export-fajl nem ertelmezheto.'); exit(2); }
ki(sprintf('FAJL: %s  (%d byte, sha256=%s)  exportalva: %s  forras: %s ID=%d',
    $FAJL, strlen($nyers), substr(hash('sha256', $nyers), 0, 8), $cs['mikor_utc'], $cs['forras_host'], $cs['forras_id']));
$adat = null;
foreach ($cs['metak'] as $m) { if ($m['k'] === '_elementor_data') { $adat = $m['v']; } }
if (!is_string($adat) || hash('sha256', $adat) !== $cs['adat_sha256']) {
    ki('!! A fajlban levo _elementor_data nem egyezik az export sajat sha256-javal. NEM IROK.'); exit(2);
}

/* --- kornyezet: Elementor, Kit, kepek --- */
ki('');
ki('=== A DEV KORNYEZETE a forrashoz kepest ===');
$de = elementorInfo(); $pe = $cs['elementor'];
ki(sprintf('  Elementor:     prod %s  dev %s  %s', $pe['elementor'] ?: 'NINCS', $de['elementor'] ?: 'NINCS',
    $de['elementor'] ? ($de['elementor'] === $pe['elementor'] ? '(azonos)' : '(ELTER)') : '!! A DEVEN NINCS ELEMENTOR'));
ki(sprintf('  Elementor Pro: prod %s  dev %s  %s', $pe['elementor_pro'] ?: 'NINCS', $de['elementor_pro'] ?: 'NINCS',
    $de['elementor_pro'] === $pe['elementor_pro'] ? '(azonos)' : '(ELTER)'));
if (!$de['elementor']) { ki('!! Elementor nelkul az oldal nem renderelheto. NEM IROK.'); exit(2); }
$hianyzoGlob = array_values(array_diff($cs['hivatkozas']['globalis_idk'], $de['kit_global_ids']));
ki(sprintf('  globalis szin/betu: %d hivatkozott, ebbol a dev Kitjeben (ID=%d) HIANYZIK: %d %s',
    count($cs['hivatkozas']['globalis_idk']), $de['kit_id'], count($hianyzoGlob),
    $hianyzoGlob ? '('.implode(', ', $hianyzoGlob).') -> ott ALAPERTELMEZETT stilus rajzolodik' : ''));
$kepEgyezik = 0; $kepMas = array();
foreach ($cs['hivatkozas']['kepek'] as $kid => $url) {
    $f = get_attached_file((int) $kid);
    if ($f && basename($f) === basename(parse_url($url, PHP_URL_PATH))) { $kepEgyezik++; } else { $kepMas[] = $kid; }
}
ki(sprintf('  kepek: %d attachment-ID, ebbol a deven ugyanaz a fajl: %d; elter/hianyzik: %d. A megjelenites',
    count($cs['hivatkozas']['kepek']), $kepEgyezik, count($kepMas)));
ki(sprintf('         az URL-bol megy (%d prod-hoszt URL), tehat a prod kepei latszanak; a szerkesztoben elterhet.',
    $cs['hivatkozas']['prod_url_db']));

/* --- a cel: van-e mar atvitt oldal, szabad-e a slug --- */
ki('');
ki('=== A CEL ===');
global $wpdb;
$jelolt = $wpdb->get_col($wpdb->prepare(
    "SELECT p.ID FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID
      WHERE m.meta_key=%s AND m.meta_value=%s AND p.post_status NOT IN ('trash','inherit','auto-draft')",
    $JELOLO, (string) $cs['forras_id']));
$foglal = $wpdb->get_results($wpdb->prepare(
    "SELECT ID, post_status, post_type, post_title FROM {$wpdb->posts}
      WHERE post_name=%s AND post_status NOT IN ('inherit','auto-draft')", $DEV_SLUG));
foreach ($foglal as $x) {
    ki(sprintf('  /%s/ slugon: ID=%d (%s, %s) %s%s', $DEV_SLUG, $x->ID, $x->post_type, $x->post_status, $x->post_title,
        in_array((string) $x->ID, $jelolt, true) ? '  <- a MI atvitt oldalunk' : ''));
}
if (!$foglal) { ki('  /'.$DEV_SLUG.'/ slug: SZABAD'); }
if (count($jelolt) > 1) { ki('!! TOBB atvitt oldal is van ('.implode(',', $jelolt).'). Kezi rendrakas kell, NEM IROK.'); exit(2); }

function cacheEldob($id) {
    foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $k) { delete_post_meta($id, $k); }
    clean_post_cache($id);
    if (class_exists('\\Elementor\\Core\\Files\\CSS\\Post')) {
        try { $c = new \Elementor\Core\Files\CSS\Post($id); $c->update(); } catch (Throwable $e) { ki('  !! CSS-ujraepites: '.$e->getMessage()); }
    }
    if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $id); ki('  litespeed_purge_post: kiadva'); }
}
function httpProba($id, $marker) {
    $url = get_permalink($id);
    $v = wp_remote_get(add_query_arg('nocache', time(), $url), array('timeout' => 25, 'redirection' => 3));
    if (is_wp_error($v)) { ki('  HTTP '.$url.' -> HIBA: '.$v->get_error_message()); return false; }
    $kod = (int) wp_remote_retrieve_response_code($v); $b = (string) wp_remote_retrieve_body($v);
    $sajat = (strpos($b, 'page-id-'.$id) !== false);
    ki(sprintf('  HTTP %s -> %d  body page-id-%d: %s  "%s": %s', $url, $kod, $id, $sajat ? 'igen' : '!! NEM',
        $marker, strpos($b, $marker) !== false ? 'megvan' : '!! NINCS'));
    return $kod === 200 && $sajat;
}

if ($VISSZA) {
    if (count($jelolt) !== 1) { ki('!! Nincs atvitt oldal, nincs mit visszaallitani. (Elobb sima import.)'); exit(2); }
    $cel = (int) $jelolt[0];
    $most = (string) get_post_meta($cel, '_elementor_data', true);
    ki(sprintf('VISSZAALLITAS: ID=%d  jelenlegi adat %d byte (sha %s) -> a fajl adata %d byte (sha %s)',
        $cel, strlen($most), substr(hash('sha256', $most), 0, 8), strlen($adat), substr($cs['adat_sha256'], 0, 8)));
    if (!$APPLY) { ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit(0); }
    update_post_meta($cel, '_elementor_data', wp_slash($adat));
    cacheEldob($cel);
    $vissza = (string) get_post_meta($cel, '_elementor_data', true);
    ki('  visszaolvasva: '.(hash('sha256', $vissza) === $cs['adat_sha256'] ? 'AZONOS a fajlbelivel (jo)' : '!! ELTER'));
    httpProba($cel, 'Miért éppen 7 nap?');
    exit(hash('sha256', $vissza) === $cs['adat_sha256'] ? 0 : 1);
}

if ($jelolt) { ki('!! MAR VAN atvitt oldal: ID='.$jelolt[0].'. Masodikat nem csinalok; ujrakezdeshez: --visszaallit'); exit(2); }
foreach ($foglal as $x) {
    if ($x->post_status !== 'trash') { ki('!! A /'.$DEV_SLUG.'/ slug FOGLALT egy masik oldallal. NEM IROK (a WP nemán "-2"-t adna).'); exit(2); }
}
ki('');
ki(sprintf('TERV: uj %s "%s", PUBLIKUS, slug=%s, %d meta + jelolo (%s=%d)',
    $cs['post']['post_type'], $cs['post']['post_title'], $DEV_SLUG, count($cs['metak']), $JELOLO, $cs['forras_id']));
if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit(0); }

$uj = wp_insert_post(array(
    'post_type' => $cs['post']['post_type'], 'post_status' => 'publish',
    'post_title' => $cs['post']['post_title'], 'post_name' => $DEV_SLUG,
    'post_content' => $cs['post']['post_content'], 'post_excerpt' => $cs['post']['post_excerpt'],
    'comment_status' => $cs['post']['comment_status'], 'ping_status' => $cs['post']['ping_status'],
    'menu_order' => $cs['post']['menu_order'],
), true);
if (is_wp_error($uj)) { ki('!! A letrehozas elbukott: '.$uj->get_error_message()); exit(1); }
ki('UJ DEV-OLDAL: ID='.$uj);
foreach ($cs['metak'] as $m) { add_post_meta($uj, $m['k'], wp_slash(maybe_unserialize($m['v']))); }
update_post_meta($uj, $JELOLO, (string) $cs['forras_id']);
update_post_meta($uj, '_landing_atvitel_sha', substr($cs['adat_sha256'], 0, 16));
cacheEldob($uj);

ki('');
ki('VISSZAMERES');
$p = get_post($uj);
ki('  slug: '.$p->post_name.($p->post_name === $DEV_SLUG ? '  (jo)' : '  !! NEM "'.$DEV_SLUG.'"'));
$vissza = (string) get_post_meta($uj, '_elementor_data', true);
$adatOk = hash('sha256', $vissza) === $cs['adat_sha256'];
ki('  _elementor_data: '.($adatOk ? 'byte-azonos a prod forrassal (jo)' : '!! ELTER a forrastol'));
ki('  _elementor_edit_mode: '.(get_post_meta($uj, '_elementor_edit_mode', true) ?: '!! HIANYZIK'));
$css = wp_upload_dir()['basedir'].'/elementor/css/post-'.$uj.'.css';
ki('  sajat CSS-fajl: '.(file_exists($css) && filesize($css) > 0 ? 'van ('.filesize($css).' byte)' : '!! NINCS (lehet, hogy a "belso CSS" mod van beallitva)'));
$httpOk = httpProba($uj, 'Miért éppen 7 nap?');
ki('');
ki('KOVETKEZO: a szoveg-csere a deven:  --site=dev --oldal='.$uj);
ki('A KINEZET egyezeset ez NEM bizonyitja: a dev-elonezetnel a fenti Kit-/kep-sorokkal egyutt jelold.');
exit($p->post_name === $DEV_SLUG && $adatOk && $httpOk ? 0 : 1);
