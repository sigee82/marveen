<?php
/**
 * 2026-11 (pihento alvas) INGYENES KIHIVAS: KURZUS + REGISZTRACIOS URLAP + UR-FEED + LANDING-SHORTCODE.
 *
 * A MINTA (GF9-probe, prodon merve 2026-10-14 15:37, Nova futtatta, read-only): EGY URLAP / KIHIVAS.
 * Form 4..9 mindegyike sajat User Registration feeddel sajat ingyenes kurzusba + a 9513 "Ingyenes
 * felhasznalo" csoportba irat be (vip-ld-enroll.php: az elso AKTIV UR-feed gf_user_registration_ldcourses /
 * _ldgroups mezoje), es sajat Innomailer-listat kap (vip-gf-innomailer.php: lista URLAPONKENT, az elso
 * bekuldeskor jon letre). A 17544 a form 9-et agyazza be -> #17551 (oktoberi ingyenes kurzus) + 9513.
 * Novemberi kurzus MEG NINCS. A kihivas-manager NEM hoz letre kurzust (README: "a MINTA kurzust kezzel
 * duplikalod, az ID-t a kihivasok ful kurzus_id_ingyenes cellajaba irod").
 *
 *   --export --wp=/home/napalatt/vip.21napalatt.hu    PROD, CSAK OLVAS: form 9 + feedjei + kurzus 17551
 *                                                      -> ~/landing-urlap-export-2026-11.json
 *   --site=dev|prod [--oldal=<ID>|jelolt]             SZARAZ: megmutatja a tervet es a kockazatokat
 *   ... --apply                                        ELES a deven
 *   ... --apply --yes-prod                             ELES a prodon (Zsolt OK utan)
 *   --leiras=<md> --leiras-sha=<8+ hex>                a ket uj kurzus LEIRASA (post_content) Copy fajljabol
 *                                                      (## 1. Ingyenes ... / ## 2. VIP ...; mindketto: leiras-bekezdes +
 *                                                      "Kezdes: ..."). Csak a JOVAHAGYOTT fajlra (sha), es csak ures vagy
 *                                                      altalunk irt leirast ir felul -- kezzel szerkesztettet NEM (Nova 20528).
 *   --k4-nelkul                                        CSAK kurzusok + urlap + feed, a landinghez NEM nyul
 *                                                      (Zsolt OK, 2026-10-14: prod K1-K3+VIP 10-20-an, K4 a
 *                                                      10-22-i valtasnal). Ilyenkor --oldal nem kell, es a
 *                                                      visszameres azt is igazolja, hogy az ELO landing meg a
 *                                                      forras-urlapot mutatja, es az uj urlapot SEHOL nem agyazza be lap.
 *
 * MIT CSINAL (ebben a sorrendben, mindegyik visszaolvasva):
 *   K1  uj ingyenes kurzus a 17551 BEALLITASAIBOL -- leckek, lepesek, felhasznalok, csoport-kotes,
 *       kiemelt kep es a kihivas-manager kulcsai NELKUL; a leirast (post_content) URESEN hagyja.
 *   K2  uj Gravity Forms urlap a form 9-bol (mezok, visszaigazolas, ertesites), uj cimmel.
 *   K3  UR-feed a form 9 feedjebol: kurzus = K1, csoport = ugyanaz (9513).
 *   K4  a landing shortcode-ja (09fb214): [gravityform id="9" ...] -> az uj urlap ID-ja.
 * Ujrafuttatva K1-K3-at NEM ismetli (a celhelyen option-ben rogziti), csak a K4-et -- igy a dev
 * kep-kor visszaallitasa utan a shortcode egy futassal visszaall.
 *
 * AMIT NEM CSINAL, es kie: a 21 napos VIP kurzus (Nessa/importer-sor kurzus_id_vip), a kurzus-ID beirasa
 * a Sheet kihivasok fulere (Nessa), a leckek feltoltese (kihivas-manager importer), a kurzus leirasa (Copy).
 *
 * PROBAPAD: LANDING_CSERE_PROBAPAD=1 + --wp=<gyoker>: CSAK a hoszt-ellenorzest kapcsolja ki.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);

/* ------------------------------------------------------------------ HONAP */
$HONAP          = '2026-11';
$FORRAS_URLAP   = 9;
$FORRAS_KURZUS  = 17551;
$UJ_KURZUS_CIM  = '7 napos ingyenes pihentető alvás kihívás';
$UJ_URLAP_CIM   = '7 napos ingyenes pihentető alvás kihívás';
/* A 21 napos VIP kurzus (Nova 20514): ugyanaz a K1, a 17563 (oktoberi VIP) beallitasaibol. Urlap/feed nincs hozza. */
$VIP_FORRAS_KURZUS = 17563;
$UJ_VIP_CIM     = '21 napos pihentető alvás kihívás';
/* A KURZUS ZARODATUMA (ACF tanfolyam_lezaras). Ebbol szamol a tema (functions.php: lejart/grace badge), a
   kihivas-lista (aktiv/hamarosan) es a push-pro (FREE: kezdet = zaro - 6 nap). Az oktoberi ertek atmasolva a
   novemberi kurzust azonnal LEJARTNAK mutatna, es a push rossz napra szamolna. A kezdes Nessa adata
   (sheet kihivasok: kezdodatum / kezdodatum_ingyenes = 2026-11-01, napok_szama 21). */
$KEZDES         = '2026-11-01';
$NAPOK          = array('ingyenes' => 7, 'vip' => 21);
$REGI_TEMA      = array('reggeli', 'október', 'oktober');        // ha az atvitt szovegben marad: FIGYELMEZTETES
/* Az ertesito level(ek) uj szovege, ertesites-NEV szerint (a szaraz menet kiirja a neveket es a mai torzset).
   Uresen: a forras szovege megy at -- ha abban regi tema all, a szaraz menet "!!"-lel jelzi.
   A SZOVEG COPYE; ide csak a jovahagyott alak kerul. Pl.:
   'Felhasználó értesítése a regisztrációról' => array('subject' => '...', 'message' => '...'), */
$UJ_ERTESITES   = array();
$LANDING_FORRAS = 17544;                                         // a dev-atvitel jeloloje
$PROD_IDEIGLENES = 'novemberi-kihivas-eloke';
$SHORTCODE_ELEM = '09fb214';
$OPCIO          = 'landing_urlap_2026_11';                        // a celhelyen: {kurzus, urlap, feed}
/* Amit a kurzus-masolas NEM visz (prefix): leckek/lepesek, szerkesztozar, kihivas-manager, kiemelt kep (az
   oktoberi temaja). A felhasznaloi hozzaferes a user-metaban el, de a kurzus-beallitasban is lehet lista -- azt
   kulon nullazzuk.
   A CSOPORT-KOTEST (learndash_group_enrolled_<gid>) VISSZUK, a forras szerint. Az elso valtozat kihagyta, es a
   dev-futas (2026-10-14 15:46) mutatta meg, hogy a 17551 a 9513 "Ingyenes felhasznalo" csoporthoz van kotve --
   ezen at kap hozzaferest a csoport. A VIP kurzusnal ugyanez a VIP-csoportok kotese: nelkule a VIP-tagok nem
   latnak bele. A masolat tehat a forras hozzaferesi modelljet tukrozi, nem egy szukebbet. */
$KURZUS_NEM = array('ld_course_steps', '_ld_course_steps', 'ld_course_', '_edit_', '_km_',
                    '_thumbnail_id', 'course_', '_wp_old_slug', '_wp_old_date', '_elementor_', '_landing_urlap_');

$ARGV = $argv ?: array();
$EXPORT = in_array('--export', $ARGV, true);
$APPLY = in_array('--apply', $ARGV, true);
$YESPROD = in_array('--yes-prod', $ARGV, true);
$K4NELKUL = in_array('--k4-nelkul', $ARGV, true);
$LEIRAS_FAJL = ''; $LEIRAS_SHA = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--leiras=') === 0)     { $LEIRAS_FAJL = substr($a, 9); }
    if (strpos($a, '--leiras-sha=') === 0) { $LEIRAS_SHA = strtolower(substr($a, 13)); }
}
$SITE = ''; $OLDAL = 0; $WP = ''; $FAJL = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--site=') === 0)  { $SITE = substr($a, 7); }
    if (strpos($a, '--oldal=') === 0) { $OLDAL = substr($a, 8) === 'jelolt' ? -1 : (int) substr($a, 8); }
    if (strpos($a, '--wp=') === 0)    { $WP = rtrim(substr($a, 5), '/'); }
    if (strpos($a, '--fajl=') === 0)  { $FAJL = substr($a, 7); }
}
$PROBAPAD = getenv('LANDING_CSERE_PROBAPAD') === '1';
if ($PROBAPAD && getenv('LANDING_FORRAS')) { $LANDING_FORRAS = (int) getenv('LANDING_FORRAS'); }
if ($PROBAPAD && getenv('LANDING_URLAP_FORRAS'))  { $FORRAS_URLAP  = (int) getenv('LANDING_URLAP_FORRAS'); }
if ($PROBAPAD && getenv('LANDING_KURZUS_FORRAS')) { $FORRAS_KURZUS = (int) getenv('LANDING_KURZUS_FORRAS'); }
if ($PROBAPAD && getenv('LANDING_VIP_FORRAS'))    { $VIP_FORRAS_KURZUS = (int) getenv('LANDING_VIP_FORRAS'); }
function ki($s){ echo '@@ '.$s."\n"; }
$HOSTOK = array('dev' => 'dev.21napalatt.hu', 'prod' => 'vip.21napalatt.hu');
if ($EXPORT) { $SITE = 'prod'; }
if (!isset($HOSTOK[$SITE])) { ki('!! KOTELEZO a --site=dev|prod (vagy --export).'); exit(2); }
if ($WP !== '' && !$PROBAPAD && !$EXPORT) { ki('!! A --wp csak probapadon vagy --export mellett adhato meg.'); exit(2); }
if ($WP === '') { $WP = '/home/napalatt/'.$HOSTOK[$SITE]; }
if (!file_exists($WP.'/wp-load.php')) { ki('!! nincs wp-load.php: '.$WP); exit(2); }
if ($FAJL === '') { $FAJL = rtrim(getenv('HOME') ?: dirname($WP), '/').'/landing-urlap-export-'.$HONAP.'.json'; }
require_once $WP.'/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
global $wpdb;

$host = (string) parse_url(home_url(), PHP_URL_HOST);
ki('LANDING '.$HONAP.' URLAP  '.gmdate('c').' UTC  site='.$SITE.'  home='.home_url().'  DB='.DB_NAME);
if ($PROBAPAD) { ki('*** PROBAPAD: a hoszt-ellenorzes KI van kapcsolva (a cel-orok elnek). ***'); }
if (!$PROBAPAD && $host !== $HOSTOK[$SITE]) { ki('!! site='.$SITE.', de ez a telepites: '.$host.'. ALLJ MEG.'); exit(2); }
if (!class_exists('GFAPI')) { ki('!! Gravity Forms nincs betoltve.'); exit(2); }
function rov($s, $n = 140) { $s = trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags((string) $s))); return mb_strlen($s) > $n ? mb_substr($s, 0, $n).'...' : $s; }

/* ================================================================ EXPORT (prod, csak olvas) */
if ($EXPORT) {
    if ($APPLY) { ki('!! az --export nem ir; --apply nelkul futtasd.'); exit(2); }
    $form = GFAPI::get_form($FORRAS_URLAP);
    if (!$form) { ki('!! nincs '.$FORRAS_URLAP.'-es urlap'); exit(2); }
    $feeds = $wpdb->get_results($wpdb->prepare("SELECT id, addon_slug, is_active, meta FROM {$wpdb->prefix}gf_addon_feed WHERE form_id=%d ORDER BY feed_order, id", $FORRAS_URLAP), ARRAY_A);
    $kurzusExport = function ($id) use ($wpdb) {
        $k = get_post($id);
        if (!$k || $k->post_type !== 'sfwd-courses') { ki('!! a '.$id.' nem kurzus'); exit(2); }
        $km = $wpdb->get_results($wpdb->prepare("SELECT meta_key k, meta_value v FROM {$wpdb->postmeta} WHERE post_id=%d ORDER BY meta_id", $id), ARRAY_A);
        $terms = array();
        foreach (array('ld_course_category', 'ld_course_tag', 'category') as $tx) {
            $t = wp_get_post_terms($id, $tx, array('fields' => 'slugs'));
            if (!is_wp_error($t) && $t) { $terms[$tx] = $t; }
        }
        return array('id' => (int) $id, 'post' => array('post_title' => $k->post_title, 'post_status' => $k->post_status,
                     'post_content_byte' => strlen($k->post_content), 'post_excerpt' => $k->post_excerpt,
                     'comment_status' => $k->comment_status, 'menu_order' => (int) $k->menu_order),
                     'metak' => $km, 'terms' => $terms);
    };
    $cs = array('honap' => $HONAP, 'mikor_utc' => gmdate('c'), 'forras_host' => $host,
        'urlap' => $form, 'feedek' => $feeds,
        'kurzus' => $kurzusExport($FORRAS_KURZUS), 'vip_kurzus' => $kurzusExport($VIP_FORRAS_KURZUS));
    $k = get_post($FORRAS_KURZUS); $km = $cs['kurzus']['metak']; $terms = $cs['kurzus']['terms'];
    $json = json_encode($cs, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    if (!is_string($json) || file_put_contents($FAJL.'.tmp', $json) === false || !rename($FAJL.'.tmp', $FAJL)) { ki('!! nem tudtam irni: '.$FAJL); exit(2); }
    ki(sprintf('IRVA: %s (%d byte, sha256=%s)', $FAJL, strlen($json), substr(hash('sha256', $json), 0, 8)));
    ki(sprintf('  urlap %d "%s": %d mezo, %d feed; kurzus %d "%s": %d meta, cimkek: %s', $FORRAS_URLAP, $form['title'],
        count($form['fields']), count($feeds), $FORRAS_KURZUS, $k->post_title, count($km), json_encode($terms, JSON_UNESCAPED_UNICODE)));
    ki(sprintf('  VIP kurzus %d "%s": %d meta', $VIP_FORRAS_KURZUS, $cs['vip_kurzus']['post']['post_title'], count($cs['vip_kurzus']['metak'])));
    ki('EXPORT VEGE. A DB-be semmit nem irtunk.');
    exit(0);
}

/* ================================================================ CEL (dev / prod) */
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');
if ($APPLY && $SITE === 'prod' && !$YESPROD) { ki('!! Prod iras csak --yes-prod-dal (Zsolt OK utan).'); exit(2); }
/* --- a kurzus-leirasok (opcionalis) --- */
$LEIRAS = null; $KARTYA = array();
if ($LEIRAS_FAJL !== '') {
    if (!is_readable($LEIRAS_FAJL)) { ki('!! nincs meg a leiras-fajl: '.$LEIRAS_FAJL); exit(2); }
    $lny = file_get_contents($LEIRAS_FAJL);
    $lsha = hash('sha256', $lny);
    ki('LEIRAS-FAJL: '.$LEIRAS_FAJL.' ('.strlen($lny).' byte, sha256='.substr($lsha, 0, 8).')');
    if ($APPLY && (strlen($LEIRAS_SHA) < 8 || strpos($lsha, $LEIRAS_SHA) !== 0)) {
        ki('!! az eleshez a --leiras-sha= a JOVAHAGYOTT fajl sha256-janak eleje kell (legalabb 8 jegy); ez a fajl '.substr($lsha, 0, 8).'. NEM IROK.');
        exit(2);
    }
    $LEIRAS = array(); $KARTYA = array();
    foreach (array('ingyenes' => '/^##\s+1\./m', 'vip' => '/^##\s+2\./m') as $szerep => $minta) {
        if (!preg_match($minta, $lny, $mm, PREG_OFFSET_CAPTURE)) { ki('!! a leiras-fajlban nincs "## '.($szerep === 'ingyenes' ? '1' : '2').'." szakasz.'); exit(2); }
        $tor = substr($lny, $mm[0][1]);
        $tor = substr($tor, strpos($tor, "\n") + 1);
        $veg = preg_match('/^(---|##\s)/m', $tor, $vv, PREG_OFFSET_CAPTURE) ? $vv[0][1] : strlen($tor);
        $bek = array_values(array_filter(array_map('trim', preg_split('/\n\s*\n/', substr($tor, 0, $veg))), 'strlen'));
        /* opcionalis 3. bekezdes: "Kártya: <egy mondat>" -- a kurzuskartya rovid leirasa (Eszter doksija, 4. pont) */
        $kartya = null;
        if (count($bek) === 3 && strpos($bek[2], 'Kártya:') === 0) { $kartya = trim(substr($bek[2], strlen('Kártya:'))); array_pop($bek); }
        if (count($bek) !== 2 || strpos($bek[1], 'Kezdés:') !== 0) {
            ki('!! a(z) '.$szerep.' leiras '.count($bek).' bekezdes, 2-t vartam (leiras + "Kezdés: ...", opcionalisan + "Kártya: ..."). NEM talalgatok.'); exit(2);
        }
        if ($kartya !== null) {
            foreach ($REGI_TEMA as $w) { if (mb_stripos($kartya, $w) !== false) { ki('!! a(z) '.$szerep.' kartya-mondatban REGI TEMA all. NEM IROK.'); exit(2); } }
            $KARTYA[$szerep] = $kartya;
            ki('  kartya ('.$szerep.'): "'.$kartya.'"');
        }
        foreach ($REGI_TEMA as $w) { if (mb_stripos($bek[0].' '.$bek[1], $w) !== false) { ki('!! a(z) '.$szerep.' leirasban REGI TEMA all ('.$w.'). NEM IROK.'); exit(2); } }
        $html = '';
        foreach ($bek as $b) {
            $html .= ($html === '' ? '' : "\n\n")."<!-- wp:paragraph -->\n<p>".htmlspecialchars(preg_replace('/\s+/u', ' ', $b), ENT_NOQUOTES, 'UTF-8')."</p>\n<!-- /wp:paragraph -->";
        }
        $LEIRAS[$szerep] = $html;
        ki(sprintf('  leiras (%s): %d byte; "%s" | "%s"', $szerep, strlen($html), rov($bek[0], 70), $bek[1]));
    }
}
if (!file_exists($FAJL)) { ki('!! nincs export-fajl: '.$FAJL.' -- elobb a prodon: --export'); exit(2); }
$nyers = file_get_contents($FAJL); $cs = json_decode($nyers, true);
if (!is_array($cs) || ($cs['honap'] ?? '') !== $HONAP) { ki('!! az export-fajl nem ertelmezheto vagy masik honape.'); exit(2); }
ki(sprintf('FAJL: %s (sha256=%s, exportalva %s, %s)', $FAJL, substr(hash('sha256', $nyers), 0, 8), $cs['mikor_utc'], $cs['forras_host']));

/* a landing-celpont (K4) -- ugyanazok az orok, mint a szoveg-/kep-csere szkriptekben */
/* Az ELO /ingyenes-kihivas/ lap shortcode-ja (csak olvas). --k4-nelkul eseten ez a kontroll: a landing
   NEM mozdulhat, es az uj urlapot egyetlen lap sem agyazhatja be. */
function eles_landing_shortcode($elem) {
    $p = get_page_by_path('ingyenes-kihivas');
    if (!$p) { return array(null, null); }
    $fa = json_decode((string) get_post_meta($p->ID, '_elementor_data', true), true);
    $talal = null;
    $jar = function ($n) use (&$jar, &$talal, $elem) {
        if (!is_array($n) || $talal !== null) { return; }
        if (isset($n['id']) && $n['id'] === $elem && isset($n['settings']['shortcode'])) { $talal = (string) $n['settings']['shortcode']; return; }
        foreach ($n as $k => $v) { if ($k !== 'settings') { $jar($v); } }
    };
    $jar($fa);
    return array((int) $p->ID, $talal);
}
function urlapot_beagyazo_lapok($urlapId) {
    global $wpdb;
    if (!$urlapId) { return array(); }
    $sorok = $wpdb->get_results("SELECT p.ID, p.post_content, m.meta_value AS el FROM {$wpdb->posts} p
        LEFT JOIN {$wpdb->postmeta} m ON m.post_id=p.ID AND m.meta_key='_elementor_data'
        WHERE p.post_status IN ('publish','draft','private') AND p.post_type NOT IN ('revision')
          AND (p.post_content LIKE '%gravityform%' OR m.meta_value LIKE '%gravityform%')");
    $ki = array();
    foreach ($sorok as $r) {
        $t = $r->post_content.' '.str_replace('\\"', '"', (string) $r->el);
        if (preg_match('/\[gravityforms?\b[^\]]*\bid=["\']?'.(int) $urlapId.'["\']?(?![0-9])/i', $t)) { $ki[] = (int) $r->ID; }
    }
    return array_values(array_unique($ki));
}
$regiMintaK = '/\[gravityforms?\b[^\]]*\bid=["\']?'.$FORRAS_URLAP.'["\']?(?![0-9])/i';
if ($K4NELKUL) {
    list($elId, $elSc) = eles_landing_shortcode($SHORTCODE_ELEM);
    ki('K4 KIHAGYVA (--k4-nelkul). Az elo /ingyenes-kihivas/ (#'.($elId ?: '-').') shortcode-ja: '.($elSc ?? '-'));
    $OLDAL = 0;
} elseif ($OLDAL === -1) {
    if ($SITE !== 'dev') { ki('!! Az --oldal=jelolt csak a deven ervenyes.'); exit(2); }
    $j = $wpdb->get_col($wpdb->prepare("SELECT p.ID FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID
        WHERE m.meta_key='_landing_atvitel_forras' AND m.meta_value=%s AND p.post_status NOT IN ('trash','inherit','auto-draft')", (string) $LANDING_FORRAS));
    if (count($j) !== 1) { ki('!! '.count($j).' jelolt oldal van, pontosan egyet vartam.'); exit(2); }
    $OLDAL = (int) $j[0];
}
if (!$K4NELKUL) {
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>|jelolt (a K4 shortcode-csere celja), vagy --k4-nelkul.'); exit(2); }
$lap = get_post($OLDAL);
if (!$lap) { ki('!! a '.$OLDAL.' nem letezik.'); exit(2); }
if ($SITE === 'dev' && get_post_meta($OLDAL, '_landing_atvitel_forras', true) !== (string) $LANDING_FORRAS) { ki('!! A deven csak az atvitt (jelolt) landingre irok.'); exit(2); }
if ($SITE === 'prod' && (in_array($OLDAL, array(17544, 17153), true) || $lap->post_name !== $PROD_IDEIGLENES || $lap->post_status !== 'draft')) {
    ki('!! A prodon csak a draft, "'.$PROD_IDEIGLENES.'" slugu masolatra irok. Ez nem az.'); exit(2);
}
ki('landing: '.$OLDAL.'  slug='.$lap->post_name.'  status='.$lap->post_status);
}

/* --- kockazat-sorok --- */
ki('');
ki('=== KORNYEZET ===');
$csoportok = array();
$urFeed = null;
foreach ($cs['feedek'] as $fd) {
    if ($fd['addon_slug'] !== 'gravityformsuserregistration' || !$fd['is_active']) { continue; }
    $urFeed = json_decode($fd['meta'], true); break;
}
if (!$urFeed) { ki('!! a forras-urlapnak nincs aktiv UR-feedje az exportban.'); exit(2); }
foreach ((array) ($urFeed['gf_user_registration_ldgroups'] ?? array()) as $gid => $flag) { if ((int) $flag === 1) { $csoportok[] = (int) $gid; } }
foreach ($csoportok as $gid) {
    $g = get_post($gid);
    ki(sprintf('  csoport %d: %s', $gid, $g && $g->post_type === 'groups' ? '"'.$g->post_title.'" megvan (jo)' : '!! NINCS ilyen LearnDash-csoport ezen a peldanyon'));
    if (!$g || $g->post_type !== 'groups') { $hianyCsoport = true; }
}
$inno = function_exists('vip_innomailer_token') ? (vip_innomailer_token() !== null) : null;
ki('  Innomailer token beallitva: '.($inno === null ? 'a plugin nincs betoltve' : ($inno ? 'IGEN -- egy TESZT-bekuldes VALODI hirlevel-listat hozna letre!' : 'nem (teszt-bekuldes nem hoz letre listat)')));
ki('  LearnDash: '.(function_exists('ld_update_course_access') ? 'betoltve' : '!! NINCS'));
if (!empty($hianyCsoport)) { ki('!! A beirato csoport hianyzik -- NEM IROK.'); exit(2); }

/* --- forras-szovegek, amik a masolattal mennenek: regi tema? --- */
ki('');
ki('=== AMI A MASOLATTAL MENNE (regi-tema ellenorzes: '.implode(', ', $REGI_TEMA).') ===');
$figy = 0;
$szovegek = array('urlap-cim' => $cs['urlap']['title'], 'urlap-leiras' => $cs['urlap']['description'] ?? '');
foreach ((array) ($cs['urlap']['confirmations'] ?? array()) as $c) {
    $szovegek['visszaigazolas "'.($c['name'] ?? '?').'" ('.($c['type'] ?? '?').')'] = ($c['type'] ?? '') === 'redirect' ? ($c['url'] ?? '') : ($c['message'] ?? '');
}
foreach ((array) ($cs['urlap']['notifications'] ?? array()) as $n) {
    $szovegek['ertesites "'.($n['name'] ?? '?').'" targy'] = $n['subject'] ?? '';
    $szovegek['ertesites "'.($n['name'] ?? '?').'" torzs'] = $n['message'] ?? '';
}
foreach ($cs['urlap']['fields'] as $f) { $szovegek['mezo '.$f['id'].' ('.$f['type'].')'] = ($f['label'] ?? '').' '.($f['description'] ?? '').' '.($f['content'] ?? ''); }
foreach ($szovegek as $nev => $sz) {
    $talal = array();
    foreach ($REGI_TEMA as $w) { if (mb_stripos((string) $sz, $w) !== false) { $talal[] = $w; } }
    if ($nev === 'urlap-cim') { continue; }   // a cim ugyis csere
    $uj = (strpos($nev, 'ertesites "') === 0 && preg_match('/^ertesites "(.*)" (targy|torzs)$/', $nev, $mm) && isset($UJ_ERTESITES[$mm[1]][$mm[2] === 'targy' ? 'subject' : 'message']));
    if ($uj) { ki('  '.$nev.': (Copy uj szovege megy helyette)'); continue; }
    if ($talal) { $figy++; }
    ki(sprintf('  %s%s: %s', $talal ? '!! ' : '', $nev, rov($sz, 160)).($talal ? '   <- REGI TEMA ('.implode(',', $talal).')' : ''));
}
ki('  kurzus-forras: "'.$cs['kurzus']['post']['post_title'].'"  leiras '.$cs['kurzus']['post']['post_content_byte'].' byte (NEM visszuk at, ures lesz)');
if ($figy) { ki('  >>> '.$figy.' helyen regi tema maradna. Ez nem allitja meg a futast, de a szoveget Copynak kell atadni.'); }

/* --- kurzus-masolas: terv (meta-lista regi-tema jelolessel) es letrehozas --- */
if (empty($cs['vip_kurzus'])) { ki('!! az export-fajlban nincs VIP kurzus (regi export) -- futtasd ujra az --export-ot.'); exit(2); }
function kurzus_meta_terv($exp, $NEM, $REGI_TEMA, $cimke) {
    $visz = array(); $kihagy = array();
    foreach ($exp['metak'] as $m) {
        $nem = false;
        foreach ($NEM as $px) { if (strpos($m['k'], $px) === 0) { $nem = true; break; } }
        if ($nem) { $kihagy[] = $m['k']; continue; }
        /* Egyszeru (nem szerializalt) meta, ami a REGI temat hordozza (SEO-cim, -leiras): NEM visszuk, mert
           a keresoben/fulon az oktoberi tema latszana. A szerializalt beallitast (_sfwd-courses) visszuk, csak jelezzuk. */
        $regi = false;
        if (!is_serialized($m['v'])) { foreach ($REGI_TEMA as $w) { if (mb_stripos((string) $m['v'], $w) !== false) { $regi = true; } } }
        if ($regi) { $kihagy[] = $m['k'].' (regi tema: '.rov($m['v'], 50).')'; continue; }
        $visz[] = $m;
    }
    ki(sprintf('  %s: forras #%d "%s", %d meta visz, kihagyva: %s', $cimke, $exp['id'], $exp['post']['post_title'], count($visz),
        $kihagy ? implode(', ', array_unique($kihagy)) : '-'));
    foreach ($visz as $m) {
        $v = (string) $m['v']; $talal = array();
        foreach ($REGI_TEMA as $w) { if (mb_stripos($v, $w) !== false) { $talal[] = $w; } }
        $csop = (strpos($m['k'], 'learndash_group_enrolled_') === 0);
        ki(sprintf('     %s%-40s %6d byte%s%s', $talal ? '!! ' : '   ', $m['k'], strlen($v),
            $csop ? '  <- CSOPORT-KOTES: '.(get_post((int) substr($m['k'], 25)) ? '"'.get_the_title((int) substr($m['k'], 25)).'"' : '!! a csoport ezen a peldanyon NINCS') : '',
            $talal ? '  <- REGI TEMA ('.implode(',', $talal).'): '.rov($v, 80) : ''));
    }
    foreach ($visz as $m) {
        if ($m['k'] !== '_sfwd-courses') { continue; }
        $arr = maybe_unserialize($m['v']);
        if (!is_array($arr)) { continue; }
        foreach (sfwd_regi_kulcsok($arr, $REGI_TEMA) as $kk) { ki('       _sfwd-courses['.$kk.'] REGI TEMAT hordoz -> URESEN megy (Copy tolti): '.rov($arr[$kk], 70)); }
        ki('       hozzaferes-tipus (sfwd-courses_course_price_type): '.($arr['sfwd-courses_course_price_type'] ?? '?'));
    }
    ki('     cimkek: '.json_encode($exp['terms'], JSON_UNESCAPED_UNICODE).'  leiras: '.$exp['post']['post_content_byte'].' byte (NEM visszuk, ures lesz)');
    return $visz;
}
function sfwd_regi_kulcsok($arr, $REGI_TEMA) {
    $ki = array();
    foreach ($arr as $k => $v) {
        if (!is_string($v)) { continue; }
        foreach ($REGI_TEMA as $w) { if (mb_stripos($v, $w) !== false) { $ki[] = $k; break; } }
    }
    return $ki;
}
/* az uj zarodatum a forras FORMATUMABAN (Ymd vagy Y-m-d) */
function uj_lezaras($forras, $kezdes, $napok) {
    $d = new DateTime($kezdes, new DateTimeZone('Europe/Budapest'));
    $d->modify('+'.($napok - 1).' days');
    return preg_match('/^\d{8}$/', (string) $forras) ? $d->format('Ymd') : $d->format('Y-m-d');
}
function lezaras_forras($exp) {
    foreach ($exp['metak'] as $m) { if ($m['k'] === 'tanfolyam_lezaras') { return (string) $m['v']; } }
    return null;
}
function kurzus_letrehoz($exp, $visz, $cim, $honap, $szerep, $lezaras, $REGI_TEMA) {
    $kp = $exp['post'];
    $id = wp_insert_post(array('post_type' => 'sfwd-courses', 'post_status' => $kp['post_status'], 'post_title' => $cim,
        'post_content' => '', 'post_excerpt' => '', 'comment_status' => $kp['comment_status'], 'menu_order' => $kp['menu_order']), true);
    if (is_wp_error($id)) { ki('!! kurzus ('.$szerep.'): '.$id->get_error_message()); exit(1); }
    foreach ($visz as $m) {
        $v = maybe_unserialize($m['v']);
        if ($m['k'] === '_sfwd-courses' && is_array($v)) {
            foreach (array('sfwd-courses_course_access_list', 'course_access_list') as $al) { if (isset($v[$al])) { $v[$al] = ''; } }
            foreach (sfwd_regi_kulcsok($v, $REGI_TEMA) as $kk) { $v[$kk] = ''; }
        }
        if ($m['k'] === 'tanfolyam_lezaras') { $v = $lezaras; }
        add_post_meta($id, $m['k'], wp_slash($v));
    }
    foreach ($exp['terms'] as $tx => $slugs) { if (taxonomy_exists($tx)) { wp_set_object_terms($id, $slugs, $tx); } }
    update_post_meta($id, '_landing_urlap_honap', $honap.':'.$szerep);
    ki('kurzus ('.$szerep.'): #'.$id.' "'.get_the_title($id).'" ('.get_post_status($id).')');
    return (int) $id;
}
/* a forras csoport-koteseibol ami a celkurzuson MEG NINCS (a 2026-10-14 15:46-os dev-futas meg nem vitte) */
function csoport_hiany($exp, $celId) {
    $h = array();
    foreach ($exp['metak'] as $m) {
        if (strpos($m['k'], 'learndash_group_enrolled_') !== 0) { continue; }
        if ($celId && get_post_meta($celId, $m['k'], true) === '') { $h[] = $m; }
    }
    return $h;
}

$kesz = get_option($OPCIO);
$kesz = is_array($kesz) ? $kesz : array();
ki('');
ki('=== TERV ===');
$viszIngy = kurzus_meta_terv($cs['kurzus'], $KURZUS_NEM, $REGI_TEMA, 'INGYENES kurzus "'.$UJ_KURZUS_CIM.'"');
$viszVip  = kurzus_meta_terv($cs['vip_kurzus'], $KURZUS_NEM, $REGI_TEMA, 'VIP kurzus "'.$UJ_VIP_CIM.'"');
$lezIngy = uj_lezaras(lezaras_forras($cs['kurzus']), $KEZDES, $NAPOK['ingyenes']);
$lezVip  = uj_lezaras(lezaras_forras($cs['vip_kurzus']), $KEZDES, $NAPOK['vip']);
ki(sprintf('  ZARODATUM (tanfolyam_lezaras): ingyenes %s -> %s (%s + %d nap - 1);  VIP %s -> %s (%s + %d nap - 1)',
    lezaras_forras($cs['kurzus']) ?? 'NINCS', $lezIngy, $KEZDES, $NAPOK['ingyenes'],
    lezaras_forras($cs['vip_kurzus']) ?? 'NINCS', $lezVip, $KEZDES, $NAPOK['vip']));
$ujKurzus = (int) ($kesz['kurzus'] ?? 0); $ujUrlap = (int) ($kesz['urlap'] ?? 0); $ujVip = (int) ($kesz['vip_kurzus'] ?? 0);
if ($ujUrlap) {
    ki('  K1-K3 MAR KESZ ezen a peldanyon: kurzus #'.$ujKurzus.', urlap '.$ujUrlap.', feed '.$kesz['feed'].' -- nem ismetlem');
    $potol = csoport_hiany($cs['kurzus'], $ujKurzus);
    ki('  K1b csoport-kotes potlasa a #'.$ujKurzus.'-en: '.($potol ? implode(', ', array_map(function ($m) { return $m['k']; }, $potol)) : 'nincs mit (megvan)'));
} else {
    ki(sprintf('  K2 urlap "%s" a form %d-bol (%d mezo, %d visszaigazolas, %d ertesites)', $UJ_URLAP_CIM, $FORRAS_URLAP,
        count($cs['urlap']['fields']), count((array) ($cs['urlap']['confirmations'] ?? array())), count((array) ($cs['urlap']['notifications'] ?? array()))));
    ki('  K3 UR-feed "'.($urFeed['feedName'] ?? '').'": kurzus = K1, csoport = '.implode(',', $csoportok));
}
ki('  KV VIP kurzus: '.($ujVip ? 'MAR KESZ (#'.$ujVip.')' : 'letrehozando'));
/* K1c: egy KORABBI futas altal letrehozott kurzuson a zarodatum es a regi-temas beallitas-szoveg javitasa
   (a 2026-10-14-i dev-kurzusok 16708/16709 meg az oktoberi zarodatummal es leirassal keszultek). */
function kurzus_javitas($cel, $vartLez, $REGI_TEMA, $apply) {
    if (!$cel || !get_post($cel)) { return array(); }
    $teendo = array();
    $most = (string) get_post_meta($cel, 'tanfolyam_lezaras', true);
    if ($most !== '' && $most !== $vartLez) { $teendo[] = 'zarodatum '.$most.' -> '.$vartLez; if ($apply) { update_post_meta($cel, 'tanfolyam_lezaras', $vartLez); } }
    $sf = get_post_meta($cel, '_sfwd-courses', true);
    if (is_array($sf)) {
        $kk = sfwd_regi_kulcsok($sf, $REGI_TEMA);
        if ($kk) { $teendo[] = '_sfwd-courses['.implode(',', $kk).'] uritve'; if ($apply) { foreach ($kk as $k) { $sf[$k] = ''; } update_post_meta($cel, '_sfwd-courses', $sf); } }
    }
    foreach (array('_learndash_course_grid_short_description') as $mk) {
        $v = (string) get_post_meta($cel, $mk, true);
        foreach ($REGI_TEMA as $w) { if ($v !== '' && mb_stripos($v, $w) !== false) { $teendo[] = $mk.' uritve'; if ($apply) { delete_post_meta($cel, $mk); } break; } }
    }
    return $teendo;
}
foreach (array(array($ujKurzus, $lezIngy, 'ingyenes'), array($ujVip, $lezVip, 'VIP')) as $par) {
    if (!$par[0]) { continue; }
    $t = kurzus_javitas($par[0], $par[1], $REGI_TEMA, false);
    ki('  K1c '.$par[2].' #'.$par[0].' javitas: '.($t ? implode('; ', $t) : 'nincs mit'));
}
function &ku_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) { if ($k === 'settings' || !is_array($gy)) { continue; } $t =& ku_elem($gy, $id); if ($t !== null) { return $t; } }
    return $nincs;
}
$k4kell = false;
if (!$K4NELKUL) {
ki('  K4 shortcode a '.$SHORTCODE_ELEM.' elemben: id="'.$FORRAS_URLAP.'" -> az uj urlap ID-ja');

$d = get_post_meta($OLDAL, '_elementor_data', true);
$fa = json_decode((string) $d, true);
if (!is_array($fa)) { ki('!! a landing _elementor_data nem dekodolhato.'); exit(2); }
$e =& ku_elem($fa, $SHORTCODE_ELEM);
$sc = ($e !== null && isset($e['settings']['shortcode'])) ? (string) $e['settings']['shortcode'] : null;
unset($e);
ki('     jelenleg: '.($sc === null ? '!! NINCS shortcode-mezo' : $sc));
$regiMinta = '/(\[gravityforms?\b[^\]]*\bid=["\']?)'.$FORRAS_URLAP.'(["\']?)/i';
$k4kell = ($sc !== null && preg_match($regiMinta, $sc));
if ($sc === null) { ki('!! a shortcode-elem hianyzik -- NEM IROK.'); exit(1); }
if (!$k4kell && !($ujUrlap && preg_match('/\bid=["\']?'.$ujUrlap.'["\']?/', $sc))) {
    ki('!! a shortcode sem a forras ('.$FORRAS_URLAP.'), sem az uj urlapra nem mutat -- a lap elmozdult, NEM IROK.'); exit(1);
}
}
if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit(0); }

/* ================================================================ ELES */
ki('');
if ($ujUrlap) {
    foreach (csoport_hiany($cs['kurzus'], $ujKurzus) as $m) { add_post_meta($ujKurzus, $m['k'], $m['v'], true); ki('K1b csoport-kotes potolva: '.$m['k']); }
}
foreach (array(array($ujKurzus, $lezIngy, 'ingyenes'), array($ujVip, $lezVip, 'VIP')) as $par) {
    if (!$par[0]) { continue; }
    $t = kurzus_javitas($par[0], $par[1], $REGI_TEMA, true);
    if ($t) { ki('K1c '.$par[2].' #'.$par[0].' javitva: '.implode('; ', $t)); }
}
if (!$ujVip) {
    $ujVip = kurzus_letrehoz($cs['vip_kurzus'], $viszVip, $UJ_VIP_CIM, $HONAP, 'vip', $lezVip, $REGI_TEMA);
    $kesz['vip_kurzus'] = $ujVip; update_option($OPCIO, $kesz, false);
}
if (!$ujUrlap) {
    /* K1 */
    $ujKurzus = kurzus_letrehoz($cs['kurzus'], $viszIngy, $UJ_KURZUS_CIM, $HONAP, 'ingyenes', $lezIngy, $REGI_TEMA);

    /* K2 */
    $uf = $cs['urlap'];
    unset($uf['id']);
    $uf['title'] = $UJ_URLAP_CIM;
    $uf['is_active'] = 1;
    foreach ((array) ($uf['notifications'] ?? array()) as $nid => $n) {
        if (isset($UJ_ERTESITES[$n['name'] ?? ''])) {
            foreach (array('subject', 'message') as $mk) {
                if (isset($UJ_ERTESITES[$n['name']][$mk])) { $uf['notifications'][$nid][$mk] = $UJ_ERTESITES[$n['name']][$mk]; }
            }
            ki('K2 ertesites "'.$n['name'].'": uj szoveg (Copy)');
        }
    }
    $ujUrlap = GFAPI::add_form($uf);
    if (is_wp_error($ujUrlap)) { ki('!! K2 urlap: '.$ujUrlap->get_error_message().' -- a K1 kurzus #'.$ujKurzus.' MAR LETEZIK.'); exit(1); }
    ki('K2 urlap: '.$ujUrlap.' "'.$UJ_URLAP_CIM.'"');

    /* K3 */
    $fm = $urFeed;
    $fm['gf_user_registration_ldcourses'] = array((string) $ujKurzus => '1');
    $ujFeed = GFAPI::add_feed($ujUrlap, $fm, 'gravityformsuserregistration');
    if (is_wp_error($ujFeed)) { ki('!! K3 feed: '.$ujFeed->get_error_message().' -- K1 #'.$ujKurzus.' es K2 '.$ujUrlap.' MAR LETEZIK.'); exit(1); }
    ki('K3 feed: #'.$ujFeed);
    $kesz = array_merge($kesz, array('kurzus' => (int) $ujKurzus, 'urlap' => (int) $ujUrlap, 'feed' => (int) $ujFeed, 'mikor' => gmdate('c')));
    update_option($OPCIO, $kesz, false);
}

/* KL: a kurzus-leirasok */
if ($LEIRAS !== null) {
    foreach (array('ingyenes' => $ujKurzus, 'vip' => $ujVip) as $szerep => $cel) {
        $p = get_post($cel);
        if (!$p) { ki('!! KL '.$szerep.': nincs kurzus'); exit(1); }
        if ($p->post_content === $LEIRAS[$szerep]) { ki('KL '.$szerep.' #'.$cel.': a leiras mar ez.'); continue; }
        if ($p->post_content !== '' && get_post_meta($cel, '_landing_leiras_sha', true) === '') {
            ki('!! KL '.$szerep.' #'.$cel.': a leiras NEM ures es nem mi irtuk ('.strlen($p->post_content).' byte) -- kezzel szerkesztettek, NEM irom felul.');
            continue;
        }
        $r = wp_update_post(array('ID' => $cel, 'post_content' => wp_slash($LEIRAS[$szerep])), true);
        if (is_wp_error($r)) { ki('!! KL '.$szerep.': '.$r->get_error_message()); exit(1); }
        update_post_meta($cel, '_landing_leiras_sha', substr(hash('sha256', $LEIRAS[$szerep]), 0, 16));
        ki('KL '.$szerep.' #'.$cel.': leiras irva ('.strlen($LEIRAS[$szerep]).' byte).');
    }
    /* a kurzuskartya rovid leirasa: ket helyen el (a forrasban mindketto a "Probald ki..." mondat volt) */
    foreach ($KARTYA as $szerep => $mondat) {
        $cel = $szerep === 'vip' ? $ujVip : $ujKurzus;
        $sf = get_post_meta($cel, '_sfwd-courses', true);
        $most = is_array($sf) ? (string) ($sf['sfwd-courses_course_short_description'] ?? '') : '';
        if ($most !== '' && $most !== $mondat) { ki('!! KL kartya '.$szerep.' #'.$cel.': nem ures es mas ("'.rov($most, 50).'") -- NEM irom felul.'); continue; }
        if (is_array($sf)) { $sf['sfwd-courses_course_short_description'] = $mondat; update_post_meta($cel, '_sfwd-courses', $sf); }
        update_post_meta($cel, '_learndash_course_grid_short_description', $mondat);
        ki('KL kartya '.$szerep.' #'.$cel.': irva.');
    }
}

/* K4 */
if ($K4NELKUL) {
    ki('K4: kihagyva (--k4-nelkul).');
} elseif ($k4kell) {
    $mentes = rtrim(getenv('HOME') ?: dirname($WP), '/').'/landing-urlap-mentes-'.$SITE.'-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
    if (file_put_contents($mentes, $d) === false) { ki('!! a mentes nem sikerult -- a K4-et NEM irom.'); exit(1); }
    $e =& ku_elem($fa, $SHORTCODE_ELEM);
    $e['settings']['shortcode'] = preg_replace($regiMinta, '${1}'.$ujUrlap.'${2}', $sc, 1);
    unset($e);
    update_post_meta($OLDAL, '_elementor_data', wp_slash(wp_json_encode($fa, JSON_UNESCAPED_SLASHES)));
    foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) { delete_post_meta($OLDAL, $mk); }
    clean_post_cache($OLDAL);
    if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $OLDAL); }
    ki('K4 mentes: '.$mentes);
} else {
    ki('K4: a shortcode mar az uj urlapra mutat.');
}

/* VISSZAMERES */
ki('');
ki('VISSZAMERES');
$rossz = 0;
$kk = get_post($ujKurzus);
$ok = $kk && $kk->post_type === 'sfwd-courses';
ki('  kurzus #'.$ujKurzus.': '.($ok ? '"'.$kk->post_title.'" '.$kk->post_status.', leckek: '.(is_array($st = get_post_meta($ujKurzus, 'ld_course_steps', true)) ? 'VAN lepes-adat (!!)' : '0 (helyes: az importer tolti fel)') : '!! NINCS')); if (!$ok) { $rossz++; }
foreach (array(array($cs['kurzus'], $ujKurzus, 'ingyenes'), array($cs['vip_kurzus'], $ujVip, 'VIP')) as $par) {
    list($exp, $cel, $nev) = $par;
    $hiany = csoport_hiany($exp, $cel);
    $db = 0; foreach ($exp['metak'] as $m) { if (strpos($m['k'], 'learndash_group_enrolled_') === 0) { $db++; } }
    ki(sprintf('  %s kurzus #%d csoport-kotes: %d/%d a forras szerint%s', $nev, $cel, $db - count($hiany), $db, $hiany ? '  !! hianyzik' : '  (jo)'));
    if ($hiany || !get_post($cel)) { $rossz++; }
}
foreach (array(array($ujKurzus, $lezIngy, 'ingyenes'), array($ujVip, $lezVip, 'VIP')) as $par) {
    list($cel, $vart, $nev) = $par;
    $most = (string) get_post_meta($cel, 'tanfolyam_lezaras', true);
    $sf = get_post_meta($cel, '_sfwd-courses', true);
    $regiK = is_array($sf) ? sfwd_regi_kulcsok($sf, $REGI_TEMA) : array();
    ki(sprintf('  %s #%d: zarodatum %s%s; hozzaferes-tipus %s; regi tema a beallitasban: %s', $nev, $cel, $most,
        $most === $vart ? ' (jo)' : ' !! vart: '.$vart, is_array($sf) ? ($sf['sfwd-courses_course_price_type'] ?? '?') : '?', $regiK ? '!! '.implode(',', $regiK) : 'nincs'));
    if ($most !== $vart || $regiK) { $rossz++; }
}
if ($LEIRAS !== null) {
    foreach (array('ingyenes' => $ujKurzus, 'vip' => $ujVip) as $szerep => $cel) {
        $most = get_post($cel) ? get_post($cel)->post_content : null;
        $ok = ($most === $LEIRAS[$szerep]);
        ki('  leiras '.$szerep.' #'.$cel.': '.($ok ? 'a jovahagyott szoveg (jo)' : '!! NEM a vart ('.strlen((string) $most).' byte)'));
        if (!$ok) { $rossz++; }
        if (isset($KARTYA[$szerep])) {
            $sf = get_post_meta($cel, '_sfwd-courses', true);
            $k1 = is_array($sf) ? ($sf['sfwd-courses_course_short_description'] ?? '') : '';
            $k2 = (string) get_post_meta($cel, '_learndash_course_grid_short_description', true);
            $kok = ($k1 === $KARTYA[$szerep] && $k2 === $KARTYA[$szerep]);
            ki('  kartya '.$szerep.' #'.$cel.': '.($kok ? 'mindket helyen a jovahagyott mondat (jo)' : '!! elter'));
            if (!$kok) { $rossz++; }
        }
    }
} else {
    ki('  leiras: nem kertuk (--leiras nelkul) -- a ket kurzus leirasa '.strlen((string) get_post($ujKurzus)->post_content).' / '.strlen((string) get_post($ujVip)->post_content).' byte');
}
$vk = get_post($ujVip);
ki('  VIP kurzus #'.$ujVip.': '.($vk ? '"'.$vk->post_title.'" '.$vk->post_status : '!! NINCS'));
$fo = GFAPI::get_form($ujUrlap);
ki('  urlap '.$ujUrlap.': '.($fo ? '"'.$fo['title'].'" aktiv='.(!empty($fo['is_active']) ? 'igen' : 'NEM').', '.count($fo['fields']).' mezo' : '!! NINCS')); if (!$fo) { $rossz++; }
if (function_exists('vip_ld_from_ur_feed')) {
    $r = vip_ld_from_ur_feed($ujUrlap);
    $jo = ($r['courses'] === array((int) $ujKurzus)) && ($r['groups'] == $csoportok);
    ki('  vip_ld_from_ur_feed('.$ujUrlap.'): kurzus='.implode(',', $r['courses']).' csoport='.implode(',', $r['groups']).($jo ? '  (jo)' : '  !! NEM a vart'));
    if (!$jo) { $rossz++; }
} else { ki('  vip_ld_from_ur_feed nem letezik ezen a peldanyon -- a feed-metat olvasom vissza:');
    $fb = GFAPI::get_feeds(null, $ujUrlap, 'gravityformsuserregistration');
    $c = is_wp_error($fb) || !$fb ? array() : array_keys(array_filter((array) ($fb[0]['meta']['gf_user_registration_ldcourses'] ?? array())));
    ki('     kurzus a feedben: '.implode(',', $c).($c == array($ujKurzus) ? '  (jo)' : '  !! NEM a vart')); if ($c != array($ujKurzus)) { $rossz++; }
}
if ($K4NELKUL) {
    list($elId, $elSc) = eles_landing_shortcode($SHORTCODE_ELEM);
    $elOk = ($elSc !== null && preg_match($regiMintaK, $elSc));
    ki('  elo landing #'.($elId ?: '-').' shortcode: '.($elSc ?? '-').($elOk ? '  (meg a '.$FORRAS_URLAP.'-es urlap -- jo, a landing nem mozdult)' : '  !! NEM a forras-urlap'));
    if (!$elOk) { $rossz++; }
    $lapok = urlapot_beagyazo_lapok($ujUrlap);
    ki('  az uj urlapot ('.$ujUrlap.') beagyazo lap: '.($lapok ? '!! '.implode(',', $lapok) : 'egy sincs (jo, latogato nem eri el)'));
    if ($lapok) { $rossz++; }
} else {
$faV = json_decode(get_post_meta($OLDAL, '_elementor_data', true), true);
$e =& ku_elem($faV, $SHORTCODE_ELEM);
$scV = $e === null ? '' : (string) ($e['settings']['shortcode'] ?? '');
unset($e);
$scOk = (bool) preg_match('/\bid=["\']?'.$ujUrlap.'["\']?/', $scV);
ki('  shortcode: '.$scV.($scOk ? '  (jo)' : '  !! NEM az uj urlap')); if (!$scOk) { $rossz++; }
}
ki('');
ki('KOVETKEZO (nem ez a szkript): Nessa a Sheet kihivasok fulre: kurzus_id_ingyenes = '.$ujKurzus.', kurzus_id_vip = '.$ujVip.' (a '.$SITE.'-hoz tartozo ID-k!),');
ki('  utana az importer feltolti a leckeket. A kurzus leirasat Copy adja.');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden visszamerve.' : '!! ELES MENET VEGE, DE '.$rossz.' ELTERES.');
exit($rossz === 0 ? 0 : 1);
