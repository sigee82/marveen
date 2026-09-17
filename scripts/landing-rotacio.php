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
 *   ssh ... 'cd ~/vip.21napalatt.hu && php -- --proba-takarit --uj-id=<ID>' < scripts/landing-rotacio.php
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

/* PROBAPADI FELULIRAS -- KORNYEZETI VALTOZOBOL, NEM KAPCSOLOBOL, ES SZANDEKOSAN.
 *
 * Az iro agak kodja a szaraz futasban BELE SEM FUT, tehat egy zold `php -l` semmit nem mond
 * arrol, hogy a duplikalas vagy a takaritas mukodik-e. Hogy ezt eles iras nelkul ki lehessen
 * probalni egy lokalis WP-n, a wp-load utja es a forras-oldal ID-je felulirhato.
 *
 * MIERT KORNYEZETI VALTOZO ES NEM `--forras=<ID>`: egy kapcsolot el lehet gepelni egy eles
 * futasban, es a slug-csere fazis a FORRAST NEVEZI AT. Kornyezeti valtozot nem ir be veletlenul
 * senki. Es ha barmelyik feluliras aktiv, a szkript a SLUG-CSERET MEGTAGADJA: probapadon
 * sosem gyakoroljuk az eles atnevezest, mert annak a kockazata nem a kodban van. */
$WPLOAD    = getenv('LANDING_WPLOAD') ?: '/home/napalatt/vip.21napalatt.hu/wp-load.php';
$FELULIRVA = (bool) (getenv('LANDING_WPLOAD') || getenv('LANDING_FORRAS'));
if (!file_exists($WPLOAD)) { exit("Nincs wp-load itt: $WPLOAD\n"); }
require_once $WPLOAD;
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

/**
 * AZ ELES OLDAL UJJLENYOMATA.
 *
 * Nova atveteli feltetele a probahoz: "az ELES szeptemberi oldal VALTOZATLAN -- merd meg ELOTTE
 * es UTANA". Ez azert kulon lepes, mert a masolas SIKERE es az eles oldal SERTETLENSEGE ket
 * fuggetlen allitas: egy szep masolat mellett is elmozdulhat a forras, ha egy hook hozzanyul,
 * es a szep masolat latvanya pont elnyomna a kerdest. Ezert a szam megy a kepernyore, nem a verdikt.
 *
 * A `post_modified` a legerzekenyebb mezo: a WP minden `wp_update_post`-nal frissiti, tehat egy
 * veletlen erintes MEG AKKOR IS nyomot hagy, ha a tartalom valtozatlan maradt.
 */
function elesUjjlenyomat($id) {
    $p = get_post($id);
    if (!$p) { return array('letezik' => false); }
    return array(
        'letezik'   => true,
        'ID'        => (int) $p->ID,
        'slug'      => (string) $p->post_name,
        'statusz'   => (string) $p->post_status,
        'modositva' => (string) $p->post_modified_gmt,
        'adat_byte' => strlen((string) get_post_meta($id, '_elementor_data', true)),
    );
}

function ujjlenyomatKiir($cimke, $u) {
    if (empty($u['letezik'])) { ki($cimke.': !! NEM LETEZIK'); return; }
    ki(sprintf('%s: ID=%d  slug=%s  statusz=%s  modositva(GMT)=%s  _elementor_data=%d byte',
        $cimke, $u['ID'], $u['slug'], $u['statusz'], $u['modositva'], $u['adat_byte']));
}

/** Ket ujjlenyomat osszevetese. A MEZONKENTI elteres megy ki, nem egy "valtozott/nem valtozott". */
function ujjlenyomatOsszevet($elotte, $utana) {
    $eltert = array();
    foreach (array('ID','slug','statusz','modositva','adat_byte') as $k) {
        $a = isset($elotte[$k]) ? $elotte[$k] : null;
        $b = isset($utana[$k]) ? $utana[$k] : null;
        if ($a !== $b) { $eltert[] = sprintf('%s: "%s" -> "%s"', $k, $a, $b); }
    }
    if (!$eltert) { ki('AZ ELES OLDAL VALTOZATLAN (mind az ot mezo azonos).'); return true; }
    ki('!! AZ ELES OLDAL ELMOZDULT -- ez onmagaban lelet, fuggetlenul a masolat minosegetol:');
    foreach ($eltert as $e) { ki('   '.$e); }
    return false;
}


/**
 * AZ ELEMENTOR GENERALT CSS-FAJLJA EGY OLDALHOZ: letezik-e, mekkora, mikor iródott.
 *
 * A "stilussal jon-e fel" kerdest szkriptbol nem lehet megnezni -- de a mogotte levo
 * KOCKAZAT merheto. Azert nem masoljuk a `_elementor_css` metat, mert az a FORRAS
 * poszt-ID-jere mutat; ha a masolat nem tudja felepiteni a SAJAT fajljat, csupasz
 * szovegkent jon fel. Tehat a fajl letezese, merete es KULONBOZOSEGE a bizonyitek.
 */
function elementorCssFajl($id) {
    $u = wp_upload_dir();
    $ut = trailingslashit($u['basedir']).'elementor/css/post-'.((int) $id).'.css';
    clearstatcache(true, $ut);
    return array(
        'ut'     => $ut,
        'letezik'=> file_exists($ut),
        'meret'  => file_exists($ut) ? filesize($ut) : 0,
        'mtime'  => file_exists($ut) ? filemtime($ut) : 0,
    );
}

function cssFajlKiir($cimke, $f) {
    ki(sprintf('%s: %s  %s  meret=%d byte  mtime=%s', $cimke,
        $f['ut'], $f['letezik'] ? 'LETEZIK' : 'NINCS', $f['meret'],
        $f['mtime'] ? gmdate('H:i:s', $f['mtime']) : '-'));
}

/** Az eles URL valodi HTTP-probaja a szerverrol: nem a DB-t kerdezzuk, hanem a webet. */
function elesUrlProba($slug, $vart_id) {
    $url = home_url('/'.$slug.'/');
    $v = wp_remote_get($url, array('timeout' => 20, 'redirection' => 5));
    if (is_wp_error($v)) { ki('!! '.$url.' -> HIBA: '.$v->get_error_message()); return false; }
    $kod = (int) wp_remote_retrieve_response_code($v);
    $p = get_page_by_path($slug);
    $ok = ($kod === 200 && $p && (int) $p->ID === (int) $vart_id);
    ki(sprintf('%s -> HTTP %d, a slug ID-je: %s (vart: %d)  %s', $url, $kod,
        $p ? $p->ID : 'NINCS', $vart_id, $ok ? '(jo)' : '!! NEM EZ VOLT A CEL'));
    return $ok;
}


$ARGV = $argv ?: array();
$DUPLIKAL  = in_array('--duplikal', $ARGV, true);
$SLUGCSERE = in_array('--slugcsere', $ARGV, true);
$TAKARIT   = in_array('--proba-takarit', $ARGV, true);
$UJ_ID = 0;
foreach ($ARGV as $a) { if (strpos($a, '--uj-id=') === 0) { $UJ_ID = (int) substr($a, 8); } }

$FORRAS       = (int) (getenv('LANDING_FORRAS') ?: 17153);   // a jelenlegi /ingyenes-kihivas/
$REGI_UJ_SLUG = 'meal-prep-kihivas';          // amit a REGI kap (merve: SZABAD)
$AKTIV_SLUG   = 'ingyenes-kihivas';
$IDEIGLENES   = 'oktoberi-kihivas-eloke';     // az uj oldal slugja a csere ELOTT

/* A generalt metak: ezeket NEM masoljuk. Minden mast IGEN. */
$NEM_MASOLANDO = array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache',
                       '_edit_lock', '_edit_last', '_wp_old_slug');

ki('LANDING-ROTACIO  '.gmdate('c').' UTC   DB='.DB_NAME.'  home='.home_url());
/* A DB NEVE ONMAGABAN NEM AZONOSIT: a lokalis peldany DB-je is `napalatt_vip21nap`.
 * A `home_url()` az, ami elvalasztja oket -- ezert megy ki mindketto. */
if ($FELULIRVA) {
    ki('*** PROBAPAD: feluliras aktiv (wp-load es/vagy forras-ID). Ez NEM az eles menet. ***');
    ki('    forras-ID='.$FORRAS);
}
ki($DUPLIKAL ? '*** DUPLIKALO MENET: IRNI FOG ***'
   : ($SLUGCSERE ? '*** SLUG-CSERE MENET: IRNI FOG ***'
   : ($TAKARIT ? '*** TAKARITO MENET: VEGLEGESEN TOROL EGY PROBAOLDALT ***' : 'MERES: semmit nem ir')));
ki('');

$forras = get_post($FORRAS);
if (!$forras) { ki('!! A forras-oldal ('.$FORRAS.') NEM LETEZIK. Allj meg.'); exit; }
ki(sprintf('FORRAS: ID=%d  slug=%s  statusz=%s  modositva=%s', $forras->ID, $forras->post_name,
    $forras->post_status, $forras->post_modified));
ki(sprintf('        cim: %s', $forras->post_title));

/* ---------------------------------------------------------------- MERES */
/* MINDEN IRO FAZIST FEL KELL SOROLNI ITT. A `--proba-takarit` hozzaadasakor ez a sor
 * kimaradt, es a kapcsolo NEMAN a meresbe futott volna, majd kilep -- a `php -l` zold,
 * a fazis meg elerhetetlen. Uj kapcsolo eseten IDE IS be kell irni. */
if (!$DUPLIKAL && !$SLUGCSERE && !$TAKARIT) {
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
                /* A settings-et REKURZIVAN jarjuk be, nem egy fix mezolistaval.
                   AZ ELSO VALTOZAT OT KULCSOT NEZETT (title/editor/text/...), es ezzel
                   NEMAN KIHAGYTA az ISMETLODO (repeater) mezoket -- az ikonos listak
                   teteleit, amik `settings.icon_list[].text` alatt ulnek. A Copy-doksi
                   KET ikonos listat tartalmaz (4 + 8 tetel), tehat 12 cserelendo szoveg
                   egyszeruen nem jelent volna meg a listaban, es a behelyettesites
                   nyomtalanul kihagyta volna oket. */
                $mezok = array();
                $bejar = function ($ertek, $ut) use (&$bejar, &$mezok) {
                    if (is_string($ertek)) {
                        $sz = trim(preg_replace('/\s+/', ' ', wp_strip_all_tags($ertek)));
                        /* Csak az EMBERI szoveg erdekel: a szin-kodok, ikon-nevek, URL-ek,
                           meret-ertekek nem. Ezeket az ut UTOLSO kulcsa alapjan szurjuk. */
                        if ($sz === '' || mb_strlen($sz) < 2) { return; }
                        if (preg_match('/^(#|https?:|fa[srb]? |eicon-|\d+$)/', $sz)) { return; }
                        $mezok[$ut] = $sz;
                        return;
                    }
                    if (is_array($ertek)) {
                        foreach ($ertek as $k => $v) {
                            if (in_array($k, array('elements','__globals__','__dynamic__'), true)) { continue; }
                            $bejar($v, $ut === '' ? (string) $k : $ut . '.' . $k);
                        }
                    }
                };
                $ERDEKES = '/(^|\.)(title|editor|text|heading_text|button_text|description_text|item_title|tab_title|tab_content)$/';
                if (!empty($node['settings']) && is_array($node['settings'])) {
                    $bejar($node['settings'], '');
                }
                foreach ($mezok as $ut => $sz) {
                    if (!preg_match($ERDEKES, $ut)) { continue; }
                    $n++;
                    ki(sprintf('  [%-8s] %-16s %-26s %s', $id, $tipus, $ut, mb_substr($sz, 0, 60)));
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
    /* Az eles oldal allapota MIELOTT hozzakezdunk. Ez a proba atveteli feltetele, nem dekoracio:
     * a masolat szepsege es a forras sertetlensege ket fuggetlen allitas. */
    $eles_elotte = elesUjjlenyomat($FORRAS);
    ujjlenyomatKiir('ELES ELOTTE ', $eles_elotte);
    $cssForras_elotte = elementorCssFajl($FORRAS);
    cssFajlKiir('FORRAS CSS ELOTTE', $cssForras_elotte);
    ki('');
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

    /* "STILUSSAL JON-E FEL?" -- a draftot kivulrol nem lehet megnezni, es a szerkeszto-elonezet
     * bejelentkezest kiván. Amit a szkript MEG TUD merni: hogy az Elementor a MASOLAT sajat
     * CSS-et fel tudja-e epiteni. Pont ez a kockazat, amiert a `_elementor_css`-t nem masoljuk --
     * ha az ujraepites nem megy, az oldal csupasz szovegkent jon fel.
     * FIGYELEM: ez KOZVETETT bizonyitek. A vizualis atvetel (Nova, bejelentkezett elonezet)
     * ettol fuggetlenul kell -- lasd a jelentes "amit ez nem bizonyit" sorat. */
    if (class_exists('\\Elementor\\Core\\Files\\CSS\\Post')) {
        try {
            $css = new \Elementor\Core\Files\CSS\Post($uj);
            $css->update();
            $cssUj = elementorCssFajl($uj);
            cssFajlKiir('  MASOLAT CSS  ', $cssUj);
            /* Harom allitas, kulon-kulon, mert kulon is tudnak bukni. */
            if (!$cssUj['letezik']) {
                ki('  !! A masolat CSS-fajlja NEM JOTT LETRE -- csupasz szovegkent jonne fel.');
            } elseif ($cssUj['meret'] <= 0) {
                ki('  !! A masolat CSS-fajlja URES -- csupasz szovegkent jonne fel.');
            } elseif ($cssUj['ut'] === $cssForras_elotte['ut']) {
                ki('  !! A masolat a FORRAS fajljara mutat -- pontosan ezt akartuk elkerulni.');
            } else {
                ki('  a masolat SAJAT, nem ures CSS-fajlt kapott (jo).');
            }
        } catch (Throwable $e) {
            ki('  !! A CSS-ujraepites HIBAT dobott: '.$e->getMessage());
        }
    } else {
        ki('  !! Az Elementor CSS-osztaly nem elerheto -- a stilus-epites NEM merheto innen.');
    }

    /* A NEGATIV KONTROLL, ami nelkul a fenti zold szam csak egy szam: a FORRAS sajat
     * CSS-fajlja valtozatlan. Ha a generalas hozzanyulna, a masolat szepsege pont
     * elfedne, hogy kozben az eles oldal fajlja alatta mozdult el. */
    $cssForras_utana = elementorCssFajl($FORRAS);
    cssFajlKiir('  FORRAS CSS UTANA', $cssForras_utana);
    if ($cssForras_elotte['meret'] === $cssForras_utana['meret']
        && $cssForras_elotte['mtime'] === $cssForras_utana['mtime']) {
        ki('  a forras CSS-fajlja VALTOZATLAN (meret es mtime azonos).');
    } else {
        ki('  !! A FORRAS CSS-FAJLJA ELMOZDULT: meret '.$cssForras_elotte['meret'].' -> '.$cssForras_utana['meret']
           .', mtime '.$cssForras_elotte['mtime'].' -> '.$cssForras_utana['mtime'].'. ALLJ MEG, NE TAKARITS.');
    }

    ki('');
    $eles_utana = elesUjjlenyomat($FORRAS);
    ujjlenyomatKiir('ELES UTANA  ', $eles_utana);
    ujjlenyomatOsszevet($eles_elotte, $eles_utana);
    elesUrlProba($AKTIV_SLUG, $FORRAS);

    /* AZ ALAPVONAL A PROBAOLDALRA KERUL, ES NEM AZ UZENETBE.
     *
     * A menetrend azt mondja: "ha az eles ujjlenyomat barmelyik mezoje elmozdult, ALLJ MEG,
     * NE TAKARITS". Amig ez csak egy mondat egy uzenetben es a futtato fejeben, a betartasa es
     * a mulasztasa kivulrol egyforma -- es a takaritas pont a NYOMOT vinne el. Ezert az itt mert
     * allapot a probaoldal sajat metajaba kerul: a takarito fazis EBBOL dolgozik, es megtagadja
     * a torlest, ha a forras kozben elmozdult. A meta a probaoldallal egyutt szunik meg. */
    update_post_meta($uj, '_proba_forras_ujjlenyomat', wp_slash(json_encode($eles_utana)));
    ki('  alapvonal rogzitve a probaoldalon (_proba_forras_ujjlenyomat) -- a takaritas ebbol dolgozik.');

    ki('');
    ki('KOVETKEZO LEPES: a szoveg es a kepek bevitele az Elementorban (ember), MAJD:');
    ki('  php -- --slugcsere --uj-id='.$uj);
    ki('PROBAFUTASNAL viszont NEM a slugcsere jon, hanem a takaritas:');
    ki('  php -- --proba-takarit --uj-id='.$uj);
    exit;
}

/* ------------------------------------------------------------ SLUG-CSERE */
if ($SLUGCSERE) {
    if ($FELULIRVA) {
        ki('!! PROBAPADON A SLUG-CSERE TILOS. Ez a fazis a FORRAST nevezi at, es az eles');
        ki('   atnevezes kockazata nem a kodban van, hanem a sorrendben es az URL-ben.');
        exit;
    }
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

/* ------------------------------------------------------------ PROBA-TAKARITAS */
/**
 * A PROBAFUTAS UTOLSO LEPESE: a HASZNALT probaoldal VEGLEGES torlese.
 *
 * Ez az egyetlen fazis, ami visszafordithatatlan, ezert ot kapun megy at, es MINDEGYIK
 * megall, nem "javit". A torles maga a konnyebbik fele; a nehezebb az, hogy a torles
 * UTAN is igazoljuk: az eles oldal es az eles URL valtozatlan. Egy sikeres torles, ami
 * kozben elmozditotta az elest, rosszabb, mint ha ott maradt volna a piszkozat.
 */
if ($TAKARIT) {
    if ($UJ_ID <= 0) { ki('!! Hianyzik a --uj-id=<ID>. Nem talalgatok, es itt kulonosen nem.'); exit; }
    if ($UJ_ID === $FORRAS) { ki('!! A megadott ID maga a FORRAS ('.$FORRAS.'). ALLJ MEG.'); exit; }
    $cel = get_post($UJ_ID);
    if (!$cel) { ki('!! A megadott oldal ('.$UJ_ID.') nem letezik. Talan mar torolve van.'); exit; }

    ki(sprintf('A TOROLNI KIVANT OLDAL: ID=%d  slug=%s  statusz=%s  cim=%s',
        $cel->ID, $cel->post_name, $cel->post_status, $cel->post_title));

    /* Kapu 1: publikus oldalt sosem torlunk ezzel a szkripttel. */
    if ($cel->post_status === 'publish') {
        ki('!! Ez az oldal PUBLIKUS. A probaoldal draft. NEM TOROLOK publikus oldalt.'); exit;
    }
    /* Kapu 2: csak a sajat, nevesitett ideiglenes slugot. Igy egy elgepelt ID sem visz el mast. */
    if ($cel->post_name !== $IDEIGLENES) {
        ki('!! A slug "'.$cel->post_name.'", nem "'.$IDEIGLENES.'". Ez nem a probaoldal. NEM TOROLOK.'); exit;
    }
    /* Kapu 3: az aktiv slug soha. */
    if ($cel->post_name === $AKTIV_SLUG) { ki('!! Ez az AKTIV slug. ALLJ MEG.'); exit; }

    $eles_elotte = elesUjjlenyomat($FORRAS);
    ujjlenyomatKiir('ELES ELOTTE ', $eles_elotte);

    /* KAPU 6: A DUPLIKALASKORI ALAPVONAL. Ez az egyetlen kapu, ami nem a torles CELPONTJAT
     * nezi, hanem az ELES oldalt -- es a legfontosabb, mert a takaritas a nyomot is elvinne. */
    $alap = get_post_meta($UJ_ID, '_proba_forras_ujjlenyomat', true);
    if ($alap === '' || $alap === null) {
        ki('!! Ezen a probaoldalon NINCS rogzitett alapvonal (_proba_forras_ujjlenyomat).');
        ki('   Enelkul NEM tudom bizonyitani, hogy az eles oldal erintetlen, a torles viszont');
        ki('   elvinne a nyomot. NEM TOROLOK. Nezd meg kezzel, es ha tiszta, torold a WP-bol.');
        exit;
    }
    $alap = json_decode($alap, true);
    ujjlenyomatKiir('ALAPVONAL   ', is_array($alap) ? $alap : array());
    if (!ujjlenyomatOsszevet($alap, $eles_elotte)) {
        ki('');
        ki('!! AZ ELES OLDAL ELMOZDULT A DUPLIKALAS OTA. NEM TOROLOK, mert a probaoldal es a');
        ki('   rajta levo alapvonal MAGA A BIZONYITEK. Szolj, es csak utana takaritsunk.');
        exit;
    }
    ki('');

    /* A PROBA SAJAT SZEMETE IS A PROBAE. A duplikalas generalt egy `post-<ID>.css`-t az
     * uploads ala; ha csak a posztot toroljuk, az a fajl ott marad, es a kovetkezo ember
     * egy nem letezo oldal CSS-et talalja. A forras fajljat viszont SOHA nem bantjuk --
     * ezert megy a torles a MASOLAT ID-jere epitett uton, es ezert merjuk vissza a forrast. */
    $cssForras_elotte = elementorCssFajl($FORRAS);
    $cssProba = elementorCssFajl($UJ_ID);
    cssFajlKiir('  A PROBA CSS-FAJLJA', $cssProba);

    $torolt = wp_delete_post($UJ_ID, true);   // true = veglegesen, nem a kukaba
    ki($torolt ? 'TOROLVE (veglegesen): ID='.$UJ_ID : '!! A TORLES NEM SIKERULT.');

    $cssProba_utana = elementorCssFajl($UJ_ID);
    if ($cssProba_utana['letezik']) {
        /* Az Elementor sajat takaritasa nem mindig fut le a poszt torlesenel. Ha maradt,
         * elvisszuk -- de KIZAROLAG a masolat sajat, ID-re epitett fajljat. */
        if ($cssProba_utana['ut'] === $cssForras_elotte['ut']) {
            ki('  !! A proba CSS-utja AZONOS a forraseval. NEM NYULOK HOZZA.');
        } else {
            @unlink($cssProba_utana['ut']);
            clearstatcache(true, $cssProba_utana['ut']);
            ki('  a maradek CSS-fajl: '.(file_exists($cssProba_utana['ut']) ? '!! MEG MINDIG OTT VAN' : 'elvive (jo)'));
        }
    } else {
        ki('  a proba CSS-fajlja a torlessel elment (jo).');
    }
    $cssForras_utana = elementorCssFajl($FORRAS);
    if ($cssForras_elotte['meret'] === $cssForras_utana['meret']
        && $cssForras_elotte['mtime'] === $cssForras_utana['mtime']) {
        ki('  a FORRAS CSS-fajlja valtozatlan (meret es mtime azonos).');
    } else {
        ki('  !! A FORRAS CSS-FAJLJA ELMOZDULT a takaritas alatt. Ez lelet, szolj.');
    }

    /* Kapu 4-5: a torles UTANI allapot. Ez a resze az, amiert egyaltalan erdemes szkriptbol csinalni. */
    ki('  visszaolvasva: '.(get_post($UJ_ID) ? '!! MEG MINDIG LETEZIK' : 'nincs ilyen poszt (jo)'));
    $maradt = get_page_by_path($IDEIGLENES);
    ki('  /'.$IDEIGLENES.'/ -> '.($maradt ? '!! MEG MINDIG VAN ott oldal (ID='.$maradt->ID.')' : 'nincs (jo)'));

    ki('');
    $eles_utana = elesUjjlenyomat($FORRAS);
    ujjlenyomatKiir('ELES UTANA  ', $eles_utana);
    ujjlenyomatOsszevet($eles_elotte, $eles_utana);
    elesUrlProba($AKTIV_SLUG, $FORRAS);
    ki('');
    ki('A PROBA ITT ER VEGET. Amit ez NEM bizonyit: hogy a masolat a BONGESZOBEN is szep volt --');
    ki('azt a bejelentkezett elonezetben kell megnezni, a torles ELOTT.');
    exit;
}
