<?php
/**
 * CSOMAG A -- KET TENYBELI JAVITAS AZ ELO LANDINGEKEN.
 *
 *   a) "Bryan Tracy" -> "Brian Tracy" HAT elo oldal `_elementor_data`-jaban.
 *   b) A 16884 nyeremenyjatek-FEJLECE: "Instagram nyeremenyjatekunkon" -> "Facebook ...".
 *      (A 13716-hoz es a 15135-hoz NEM nyulunk: olvasassal igazoltan belsoleg konzisztensek.)
 *
 * ALAPERTELMEZESBEN SZARAZON FUT ES SEMMIT NEM IR. Az irashoz `--apply` kell:
 *   ssh ... 'cd ~/vip.21napalatt.hu && php' < scripts/landing-tenybeli-javitas.php          # szaraz
 *   ssh ... 'cd ~/vip.21napalatt.hu && php -- --apply' < scripts/landing-tenybeli-javitas.php
 *
 * MIERT IGY, ES MI A HAROM VESZELY, AMIRE EPUL:
 *
 * 1. A NULLA TALALAT NEM SIKER. A `_elementor_data` JSON, es az ekezetes betuk BENNE LEHETNEK
 *    `\uXXXX` alakban -- akkor a "nyeremenyjatekunkon" szo szerinti keresese NULLAT ad, es az
 *    ugy nez ki, mintha mar javitva lenne. Ezert a szkript MINDKET alakot probalja, kiirja
 *    MELYIK talalt, es ha a talalatok szama nem a VART, NEM IR, hanem megall.
 * 2. A REVIZIOK NEM TARTALOM. Csak a felsorolt szulo-posztok metajat irjuk; a `wp_posts`
 *    revizio-sorait nem.
 * 3. A JAVITAS LATHATATLAN MARAD CSS-CACHE NELKUL. Elementor a generalt CSS-t a `_elementor_css`
 *    metaban tartja; iras utan oldalankent eldobjuk, hogy ujraepuljon.
 *
 * MENTES: iras ELOTT oldalankent kiirja az EREDETI `_elementor_data`-t
 * `~/vip.21napalatt.hu/landing-mentes-<ID>-<idobelyeg>.txt` fajlba. Ez a visszaut.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$APPLY = in_array('--apply', $argv ?: array(), true);
$BELYEG = gmdate('Ymd-His');
$MENTES_DIR = '/home/napalatt/vip.21napalatt.hu';

ki('LANDING TENYBELI JAVITAS  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir (az irashoz: php -- --apply)');
ki('');

/* A javitando oldalak. A Tracy-lista Nova prod-meresebol jon (6 erintett oldal);
   a 13835 SZANDEKOSAN nincs benne, mert azon Bryan=0. */
$TRACY_OLDALAK = array(13716, 15135, 16313, 16355, 16884, 17153);
$FEJLEC_OLDAL  = 16884;

/* A ket alak, amiben az ekezetes szoveg allhat a JSON-ben. */
function km_valtozatok($szoveg) {
    $ki = array('nyers' => $szoveg);
    $json = json_encode($szoveg, JSON_UNESCAPED_SLASHES);           // "..." idezojelekkel
    $esc  = substr($json, 1, -1);                                    // a \uXXXX-es belso alak
    if ($esc !== $szoveg) { $ki['unicode-escape'] = $esc; }
    return $ki;
}

$hiba = false;

ki('=== a) "Bryan Tracy" -> "Brian Tracy" ===');
foreach ($TRACY_OLDALAK as $id) {
    $p = get_post($id);
    if (!$p) { ki(sprintf('  ID=%-6d !! NEM LETEZIK -- kihagyva, es ez LELET', $id)); $hiba = true; continue; }
    $d = get_post_meta($id, '_elementor_data', true);
    if (!is_string($d) || $d === '') { ki(sprintf('  ID=%-6d !! nincs _elementor_data -- LELET', $id)); $hiba = true; continue; }

    $db = substr_count($d, 'Bryan Tracy');
    $mar = substr_count($d, 'Brian Tracy');
    ki(sprintf('  ID=%-6d %-34s Bryan=%d  Brian=%d', $id, $p->post_name, $db, $mar));
    if ($db === 0) {
        ki('        !! NULLA TALALAT. Ez NEM siker: vagy mar javitva van (akkor Brian>0 all mellette),');
        ki('           vagy mas alakban all a nev. NEM IRUNK ezen az oldalon.');
        if ($mar === 0) { $hiba = true; ki('           Brian=0 IS -- tehat a nev egyaltalan nincs itt. Nezd meg kezzel.'); }
        continue;
    }
    if (!$APPLY) { ki(sprintf('        [szaraz] %d csere tortenne', $db)); continue; }

    $mentes = $MENTES_DIR.'/landing-mentes-'.$id.'-'.$BELYEG.'.txt';
    if (file_put_contents($mentes, $d) === false) {
        ki('        !! A MENTES NEM SIKERULT -- NEM IRUNK. '.$mentes); $hiba = true; continue;
    }
    ki('        mentes: '.$mentes.' ('.strlen($d).' byte)');

    $uj = str_replace('Bryan Tracy', 'Brian Tracy', $d);
    update_post_meta($id, '_elementor_data', wp_slash($uj));
    delete_post_meta($id, '_elementor_css');          // a generalt CSS ujraepuljen
    delete_post_meta($id, '_elementor_page_assets');

    $vissza = get_post_meta($id, '_elementor_data', true);
    ki(sprintf('        VISSZAOLVASVA: Bryan=%d (vart: 0)  Brian=%d (vart: %d)  hossz=%d (elotte %d)',
        substr_count($vissza, 'Bryan Tracy'), substr_count($vissza, 'Brian Tracy'), $db + $mar,
        strlen($vissza), strlen($d)));
    if (substr_count($vissza, 'Bryan Tracy') !== 0) { ki('        !! MEG MINDIG VAN BRYAN -- NEZD MEG'); $hiba = true; }
}

ki('');
ki('=== b) A 16884 nyeremenyjatek-FEJLECE ===');
$d = get_post_meta($FEJLEC_OLDAL, '_elementor_data', true);
if (!is_string($d) || $d === '') {
    ki('  !! nincs _elementor_data a '.$FEJLEC_OLDAL.'-on'); $hiba = true;
} else {
    /* A fejlec-mondat vegzodese. CSAK ezt cserejuk, hogy a TORZS
       ("Posztold a kihivas Facebook csoportjaban") erintetlen maradjon. */
    $regi_valt = km_valtozatok('Instagram nyereményjátékunkon');
    $uj_valt   = km_valtozatok('Facebook nyereményjátékunkon');

    $talalt_alak = null; $talalt_db = 0;
    foreach ($regi_valt as $nev => $minta) {
        $n = substr_count($d, $minta);
        ki(sprintf('  alak "%s": %d talalat', $nev, $n));
        if ($n > 0) { $talalt_alak = $nev; $talalt_db = $n; }
    }
    if ($talalt_alak === null) {
        ki('  !! EGYIK ALAKBAN SEM TALALOM. NEM IRUNK. Lehet, hogy mar javitva van:');
        foreach (km_valtozatok('Facebook nyereményjátékunkon') as $nev => $m) {
            ki(sprintf('     "Facebook nyeremenyjatekunkon" (%s): %d', $nev, substr_count($d, $m)));
        }
        $hiba = true;
    } elseif ($talalt_db !== 1) {
        ki(sprintf('  !! %d TALALAT, de PONTOSAN EGYET vartam (egy fejlec). NEM IRUNK -- nezd meg kezzel.', $talalt_db));
        $hiba = true;
    } elseif (!$APPLY) {
        ki('  [szaraz] 1 csere tortenne a "'.$talalt_alak.'" alakon');
    } else {
        $mentes = $MENTES_DIR.'/landing-mentes-'.$FEJLEC_OLDAL.'-fejlec-'.$BELYEG.'.txt';
        if (file_put_contents($mentes, $d) === false) {
            ki('  !! A MENTES NEM SIKERULT -- NEM IRUNK.'); $hiba = true;
        } else {
            ki('  mentes: '.$mentes);
            $uj = str_replace($regi_valt[$talalt_alak], $uj_valt[$talalt_alak], $d);
            update_post_meta($FEJLEC_OLDAL, '_elementor_data', wp_slash($uj));
            delete_post_meta($FEJLEC_OLDAL, '_elementor_css');
            delete_post_meta($FEJLEC_OLDAL, '_elementor_page_assets');

            $vissza = get_post_meta($FEJLEC_OLDAL, '_elementor_data', true);
            $maradt = 0; foreach ($regi_valt as $m) { $maradt += substr_count($vissza, $m); }
            $lett   = 0; foreach ($uj_valt as $m)   { $lett   += substr_count($vissza, $m); }
            ki(sprintf('  VISSZAOLVASVA: "Instagram nyerem..."=%d (vart: 0)   "Facebook nyerem..."=%d (vart: 1)',
                $maradt, $lett));
            if ($maradt !== 0 || $lett < 1) { ki('  !! A CSERE NEM AZ, AMIT VARTAM'); $hiba = true; }
            /* A TORZS erintetlensege: a Facebook-csoportos mondatnak maradnia kell. */
            $torzs = 0; foreach (km_valtozatok('Facebook csoportjában') as $m) { $torzs += substr_count($vissza, $m); }
            ki(sprintf('  a TORZS ("...Facebook csoportjaban") tovabbra is megvan: %d elofordulas', $torzs));
        }
    }
}

ki('');
if (!$APPLY) {
    ki('SZARAZ MENET VEGE. Semmit nem irtunk. Ha a fenti szamok jok, ugyanez `php -- --apply`-jal.');
} else {
    ki($hiba ? 'ELES MENET VEGE -- DE VOLT LEGALABB EGY FIGYELMEZTETES, OLVASD VISSZA A FENTIT.'
             : 'ELES MENET VEGE. Minden visszaolvasas a vart erteket adta.');
    ki('A mentesek a '.$MENTES_DIR.' mappaban, `landing-mentes-*-'.$BELYEG.'.txt` nevvel.');
}
