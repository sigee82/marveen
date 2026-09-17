<?php
/**
 * CSOMAG B -- A HAVI LANDING-ROTACIO.  HAROM KULON FAZIS, MINDEGYIK SAJAT KAPCSOLOVAL.
 *
 *   (alapertelmezes)  MERES: semmit nem ir. Kiirja a forras-oldal szerkezetet, a szoveg-elemeit
 *                     (elem-ID + a jelenlegi szoveg eleje) es a TELJES postameta-kulcslistat.
 *                     EZ KELL AHHOZ, hogy a szoveg-behelyettesitest VALODI adatra lehessen irni.
 *   --duplikal        Letrehozza az UJ oldalt a 17153 masolatakent, DRAFT statuszban, IDEIGLENES
 *                     slugon. A generalt metakat NEM masolja, a CSS-cache-t nem viszi at.
 *   --slugcsere       A KET atnevezes, a KOTELEZO sorrendben. Kulon fazis, mert ez a nap, amikor
 *                     az URL atall -- es ezt nem akarjuk a duplikalassal egy mozdulatban.
 *
 * FUTTATAS:
 *   ssh ... 'cd ~/vip.21napalatt.hu && php' < scripts/landing-rotacio.php
 *   ssh ... 'cd ~/vip.21napalatt.hu && php -- --duplikal' < scripts/landing-rotacio.php
 *   ssh ... 'cd ~/vip.21napalatt.hu && php -- --slugcsere --uj-id=<ID>' < scripts/landing-rotacio.php
 *
 * MIERT HAROM FAZIS, ES MIERT EZ A SORREND:
 *
 * 1. A SLUG-CSERE SORRENDJE NEM IZLES KERDESE. Ha az UJ oldal kapja meg eloszor az
 *    `ingyenes-kihivas` slugot, a WP NEM HIBAZIK, hanem NEMAN `ingyenes-kihivas-2`-t ad neki,
 *    es az eles URL tovabbra is a REGIRE mutat. Ezert eloszor a REGI kap tema-slugot.
 *    A szkript ezt ki is kenyszeriti: a masodik atnevezes utan VISSZAOLVAS, es ha a kapott slug
 *    nem pontosan `ingyenes-kihivas`, HIBAKENT jelenti.
 * 2. AZ ELEMENTOR TARTALMA A `_elementor_data` POSTMETABAN VAN, nem a `post_content`-ben.
 *    Aki a post_content-et masolja, ures oldalt kap, es a hianyt a cache-re fogja.
 * 3. A GENERALT METAKAT NEM MASOLJUK. A `_elementor_css` a FORRAS poszt-ID-jere mutat; atmasolva
 *    az uj oldal a regi CSS-ere hivatkozna. Ugyanez all a `_elementor_page_assets`-re es a
 *    szerkeszto-zarakra. Ezert a masolas ENGEDELYEZO-LISTA helyett TILTO-listaval megy: MINDENT
 *    viszunk, KIVEVE a generaltakat -- igy egy uj Elementor-meta nem marad le nemán.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$ARGV = $argv ?: array();
$DUPLIKAL  = in_array('--duplikal', $ARGV, true);
$SLUGCSERE = in_array('--slugcsere', $ARGV, true);
$UJ_ID = 0;
foreach ($ARGV as $a) { if (strpos($a, '--uj-id=') === 0) { $UJ_ID = (int) substr($a, 8); } }

$FORRAS       = 17153;                        // a jelenlegi /ingyenes-kihivas/
$REGI_UJ_SLUG = 'meal-prep-kihivas';          // amit a REGI kap (merve: SZABAD)
$AKTIV_SLUG   = 'ingyenes-kihivas';
$IDEIGLENES   = 'oktoberi-kihivas-eloke';     // az uj oldal slugja a csere ELOTT

/* A generalt metak: ezeket NEM masoljuk. Minden mast IGEN. */
$NEM_MASOLANDO = array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache',
                       '_edit_lock', '_edit_last', '_wp_old_slug');

ki('LANDING-ROTACIO  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($DUPLIKAL ? '*** DUPLIKALO MENET: IRNI FOG ***'
   : ($SLUGCSERE ? '*** SLUG-CSERE MENET: IRNI FOG ***' : 'MERES: semmit nem ir'));
ki('');

$forras = get_post($FORRAS);
if (!$forras) { ki('!! A forras-oldal ('.$FORRAS.') NEM LETEZIK. Allj meg.'); exit; }
ki(sprintf('FORRAS: ID=%d  slug=%s  statusz=%s  modositva=%s', $forras->ID, $forras->post_name,
    $forras->post_status, $forras->post_modified));
ki(sprintf('        cim: %s', $forras->post_title));

/* ---------------------------------------------------------------- MERES */
if (!$DUPLIKAL && !$SLUGCSERE) {
    ki('');
    ki('=== 1. A FORRAS POSTAMETAI (amit a masolasnak vinnie kell) ===');
    global $wpdb;
    $metak = $wpdb->get_results($wpdb->prepare(
        "SELECT meta_key, COUNT(*) db, SUM(LENGTH(meta_value)) hossz FROM {$wpdb->postmeta}
          WHERE post_id=%d GROUP BY meta_key ORDER BY meta_key", $FORRAS));
    $visz = 0; $kihagy = 0;
    foreach ($metak as $m) {
        $skip = in_array($m->meta_key, $NEM_MASOLANDO, true);
        $skip ? $kihagy++ : $visz++;
        ki(sprintf('  %-46s db=%-3d hossz=%-8d %s', $m->meta_key, (int)$m->db, (int)$m->hossz,
            $skip ? '<- NEM masoljuk (generalt)' : ''));
    }
    ki(sprintf('  OSSZESEN %d kulcs: %d masolando, %d generalt', count($metak), $visz, $kihagy));

    ki('');
    ki('=== 2. A SZOVEG-ELEMEK (ehhez kell majd a behelyettesitest irni) ===');
    ki('  Elem-ID + a jelenlegi szoveg eleje. A Copy-doksi 12 szekciojat EZEKRE kell rakotni,');
    ki('  es a parositast EMBER dontse el -- a szkript nem talalgat.');
    $d = get_post_meta($FORRAS, '_elementor_data', true);
    $fa = json_decode((string) $d, true);
    if (!is_array($fa)) { ki('  !! a _elementor_data nem dekodolhato: '.json_last_error_msg()); }
    else {
        $n = 0;
        $jaro = function ($node, $ut) use (&$jaro, &$n) {
            if (!is_array($node)) { return; }
            if (isset($node['elType'])) {
                $id = isset($node['id']) ? $node['id'] : '?';
                $tipus = isset($node['widgetType']) ? $node['widgetType'] : $node['elType'];
                foreach (array('title','editor','text','heading_text','button_text') as $mezo) {
                    if (!empty($node['settings'][$mezo]) && is_string($node['settings'][$mezo])) {
                        $sz = trim(preg_replace('/\s+/', ' ', wp_strip_all_tags($node['settings'][$mezo])));
                        if ($sz === '') { continue; }
                        $n++;
                        ki(sprintf('  [%-7s] %-18s %-14s %s', $id, $tipus, $mezo, mb_substr($sz, 0, 70)));
                    }
                }
            }
            /* Egy elem gyerekei CSAK az `elements` alatt vannak. A lista-csomopontok
               (a fa gyokere es az `elements` tombok) viszont sima tombok.
               AZ ELSO VALTOZAT MINDKET UTON BEJARTA A GYEREKEKET, es ezert MINDEN
               elemet KETSZER szamolt -- 3 mezobol 6 lett. Lokalis teszt fogta meg;
               egy 12 szekcios oldalon ez 24-et irt volna, es a parositas azon bukik. */
            if (isset($node['elType'])) {
                if (!empty($node['elements']) && is_array($node['elements'])) {
                    foreach ($node['elements'] as $gy) { $jaro($gy, $ut); }
                }
            } else {
                foreach ($node as $gy) { $jaro($gy, $ut); }
            }
        };
        $jaro($fa, '');
        ki(sprintf('  OSSZESEN %d szoveges mezo. (Ha ez 0, a bejaro rossz -- ne olvasd ures oldalnak.)', $n));
    }

    ki('');
    ki('=== 3. SLUG-ALLAS a tervezett atnevezeshez ===');
    foreach (array($REGI_UJ_SLUG, $AKTIV_SLUG, $IDEIGLENES) as $slug) {
        $t = $wpdb->get_results($wpdb->prepare(
            "SELECT ID, post_status, post_title FROM {$wpdb->posts}
              WHERE post_name=%s AND post_status NOT IN ('inherit','auto-draft','trash')", $slug));
        if (!$t) { ki(sprintf('  %-30s SZABAD', $slug)); }
        else { foreach ($t as $x) { ki(sprintf('  %-30s FOGLALT: ID=%d (%s) %s', $slug, $x->ID, $x->post_status, $x->post_title)); } }
    }
    ki('');
    ki('MERES VEGE. Semmit nem irtunk.');
    exit;
}

/* ------------------------------------------------------------ DUPLIKALAS */
if ($DUPLIKAL) {
    global $wpdb;
    $letezo = get_page_by_path($IDEIGLENES);
    if ($letezo) {
        ki('!! MAR LETEZIK oldal a(z) "'.$IDEIGLENES.'" slugon (ID='.$letezo->ID.').');
        ki('   NEM duplikalok masodszor -- ket felig kesz masolat rosszabb, mint egy.');
        exit;
    }
    $uj = wp_insert_post(array(
        'post_type'    => $forras->post_type,
        'post_status'  => 'draft',                       // draftban szuletik, nem publikusan
        'post_title'   => 'INGYENES KIHIVAS -- oktober (elokeszites)',
        'post_name'    => $IDEIGLENES,
        'post_content' => $forras->post_content,
        'post_excerpt' => $forras->post_excerpt,
        'post_parent'  => $forras->post_parent,
        'menu_order'   => $forras->menu_order,
        'comment_status' => $forras->comment_status,
        'ping_status'  => $forras->ping_status,
    ), true);
    if (is_wp_error($uj)) { ki('!! A letrehozas ELBUKOTT: '.$uj->get_error_message()); exit; }
    ki('UJ OLDAL: ID='.$uj.'  slug='.$IDEIGLENES.'  statusz=draft');

    $sorok = $wpdb->get_results($wpdb->prepare(
        "SELECT meta_key, meta_value FROM {$wpdb->postmeta} WHERE post_id=%d", $FORRAS));
    $vitt = 0; $kihagyott = array();
    foreach ($sorok as $s) {
        if (in_array($s->meta_key, $NEM_MASOLANDO, true)) { $kihagyott[] = $s->meta_key; continue; }
        add_post_meta($uj, $s->meta_key, wp_slash(maybe_unserialize($s->meta_value)));
        $vitt++;
    }
    ki('  postameta atmasolva: '.$vitt.' sor');
    ki('  szandekosan kihagyva: '.($kihagyott ? implode(', ', array_unique($kihagyott)) : '(egy sem volt)'));

    /* A masolat ellenorzese: a TARTALOM tenyleg atment-e. */
    $f = get_post_meta($FORRAS, '_elementor_data', true);
    $u = get_post_meta($uj, '_elementor_data', true);
    ki(sprintf('  _elementor_data: forras=%d byte  masolat=%d byte  %s',
        strlen((string)$f), strlen((string)$u),
        ((string)$f === (string)$u ? 'AZONOS (jo)' : '!! ELTER -- NEZD MEG')));
    $mod = get_post_meta($uj, '_elementor_edit_mode', true);
    ki('  _elementor_edit_mode a masolaton: '.($mod === '' ? '!! HIANYZIK' : $mod));
    ki('  _elementor_css a masolaton: '.(get_post_meta($uj,'_elementor_css',true) === '' ? 'nincs (helyes, ujraepul)' : '!! ATMASOLODOTT'));
    ki('');
    ki('KOVETKEZO LEPES: a szoveg es a kepek bevitele az Elementorban (ember), MAJD:');
    ki('  php -- --slugcsere --uj-id='.$uj);
    exit;
}

/* ------------------------------------------------------------ SLUG-CSERE */
if ($SLUGCSERE) {
    if ($UJ_ID <= 0) { ki('!! Hianyzik a --uj-id=<ID>. Nem talalgatok.'); exit; }
    $uj = get_post($UJ_ID);
    if (!$uj) { ki('!! A megadott uj oldal ('.$UJ_ID.') NEM LETEZIK.'); exit; }
    if ($uj->ID === $FORRAS) { ki('!! A megadott ID a FORRAS. Allj meg.'); exit; }
    ki('UJ OLDAL: ID='.$uj->ID.'  slug='.$uj->post_name.'  statusz='.$uj->post_status);
    if ($uj->post_status !== 'publish') {
        ki('!! Az uj oldal NEM publikus ('.$uj->post_status.'). Eloszor publikald, aztan cserelj slugot --');
        ki('   kulonben az `ingyenes-kihivas` URL egy draftra mutatna. NEM CSERELEK.');
        exit;
    }

    ki('');
    ki('1. LEPES: a REGI ('.$FORRAS.') megkapja a tema-slugot: '.$REGI_UJ_SLUG);
    wp_update_post(array('ID' => $FORRAS, 'post_name' => $REGI_UJ_SLUG));
    clean_post_cache($FORRAS);
    $regi_most = get_post($FORRAS)->post_name;
    ki('   visszaolvasva: '.$regi_most.($regi_most === $REGI_UJ_SLUG ? '  (jo)' : '  !! NEM EZ VOLT A CEL'));
    if ($regi_most !== $REGI_UJ_SLUG) {
        ki('   !! AZ ELSO ATNEVEZES NEM SIKERULT -- a masodikat NEM csinalom meg.');
        ki('      (Ha most adnank az ujnak az `ingyenes-kihivas`-t, a WP "-2"-t ragasztana ra.)');
        exit;
    }

    ki('');
    ki('2. LEPES: az UJ ('.$uj->ID.') megkapja: '.$AKTIV_SLUG);
    wp_update_post(array('ID' => $uj->ID, 'post_name' => $AKTIV_SLUG));
    clean_post_cache($uj->ID);
    $uj_most = get_post($uj->ID)->post_name;
    ki('   visszaolvasva: '.$uj_most);
    if ($uj_most !== $AKTIV_SLUG) {
        ki('   !! NEM "'.$AKTIV_SLUG.'" lett, hanem "'.$uj_most.'".');
        ki('      Ez PONTOSAN az a nema hiba, amit el akartunk kerulni: az URL a REGIRE mutat tovabb.');
    }

    ki('');
    ki('3. VISSZAMERES');
    $utvegen = get_page_by_path($AKTIV_SLUG);
    ki('   /'.$AKTIV_SLUG.'/ -> ID='.($utvegen ? $utvegen->ID : 'NINCS')
       .($utvegen && $utvegen->ID === $uj->ID ? '  (az UJ oldal -- jo)' : '  !! NEM az uj oldal'));
    $regi_ut = get_page_by_path($REGI_UJ_SLUG);
    ki('   /'.$REGI_UJ_SLUG.'/ -> ID='.($regi_ut ? $regi_ut->ID : 'NINCS')
       .($regi_ut && $regi_ut->ID === $FORRAS ? '  (a REGI, publikusan -- jo)' : '  !! nem a regi'));
    ki('   a REGI statusza: '.get_post($FORRAS)->post_status.'  (publish kell, NEM draft)');
    ki('');
    ki('A bongeszos visszameres (mobil-nezet, urlap, nyeremenyjatek-platform) tovabbra is Nova dolga.');
}
