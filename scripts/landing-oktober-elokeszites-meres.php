<?php
/**
 * OKTOBERI INGYENES-KIHIVAS LANDING -- ELOKESZITO PROD MERES (read-only).
 *
 * MIERT KELL, ha a korpuszt mar elolvastam: a korpusz OT oldalt tartalmaz, a skill viszont
 * HET elo landinget sorol. Az "ot landing" a MERES hatokore volt, nem az elo oldalak szama.
 * Ez a szkript nem listabol dolgozik: a `_elementor_data`-ban KERESI meg, mely oldalak
 * hordozzak a javitando szoveget -- igy a lefedettseg nem az en feltevesem lesz.
 *
 * Tovabba megmeri azt a harom dolgot, amit a duplikalas elott NEM szabad feltetelezni:
 * a 17153 TELJES postameta-kulcskeszletet (nem csak a negy Elementor-kulcsot, amit fejbol
 * felsoroltam), a slug-utkozeseket, es az Elementor CSS-cache alakjat.
 *
 * FUTTATAS (kapuzott SSH-menetben):
 *   ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes napalatt@185.208.227.93 \
 *     'cd ~/vip.21napalatt.hu && php' < scripts/landing-oktober-elokeszites-meres.php \
 *     | grep -a '^@@' > tervek/landing-oktober-elokeszites-$(date +%Y-%m-%d-%H%M).txt
 *
 * SEMMIT NEM IR. Se posztot, se metat, se opciot, se cache-t. Titkot nem ir ki.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

global $wpdb;
$FORRAS = 17153; // az aktualis /ingyenes-kihivas/ landing, ebbol duplikalunk

ki('MERES '.gmdate('c').' UTC   DB='.DB_NAME.'   site='.get_option('siteurl'));
ki('');

ki('=== 1. A FORRAS-OLDAL ALLAPOTA (duplikalas alapja) ===');
$p = get_post($FORRAS);
$forrasVan = (bool)$p;
if (!$forrasVan) {
    ki('  !! '.$FORRAS.' NEM LETEZIK ezen a peldanyon -- a duplikalas alapja hianyzik.');
    ki('  A 2-3. pont kimarad, a tobbi meres FUT (azok nem fuggnek a forrastol).');
} else {
ki(sprintf('  ID=%d  slug=%s  statusz=%s  tipus=%s  modositva=%s',
    $p->ID, $p->post_name, $p->post_status, $p->post_type, $p->post_modified));
ki(sprintf('  cim: %s', $p->post_title));
ki(sprintf('  post_content hossz=%d  (Elementornal ez lenyegtelen, csak kontrollnak)', strlen($p->post_content)));
}

ki('');
ki('=== 2. A FORRAS TELJES POSTAMETA-KULCSKESZLETE ===');
ki('  (NEM feltetelezunk negy kulcsot. Ami itt all, azt MIND vinni kell a masolatba,');
ki('   kiveve amit a 3. pont kihagyandonak jelol.)');
if ($forrasVan) {
$metak = $wpdb->get_results($wpdb->prepare(
    "SELECT meta_key, COUNT(*) db, SUM(LENGTH(meta_value)) hossz
       FROM {$wpdb->postmeta} WHERE post_id=%d GROUP BY meta_key ORDER BY meta_key", $FORRAS));
foreach ($metak as $m) {
    ki(sprintf('  %-46s db=%-3d hossz=%d', $m->meta_key, (int)$m->db, (int)$m->hossz));
}
ki(sprintf('  OSSZESEN %d kulonbozo meta-kulcs', count($metak)));
} else { ki('  -- kimarad, nincs forras-oldal --'); }

ki('');
ki('=== 3. CSAK-FORRAS (generalt) METAK -- ezeket NE masold, ujra kell generalni ===');
if ($forrasVan) {
foreach (array('_elementor_css','_elementor_element_cache','_elementor_page_assets','_edit_lock','_edit_last','_wp_old_slug') as $k) {
    $v = $wpdb->get_var($wpdb->prepare("SELECT COUNT(*) FROM {$wpdb->postmeta} WHERE post_id=%d AND meta_key=%s", $FORRAS, $k));
    ki(sprintf('  %-28s van a forrason: %s', $k, ((int)$v ? 'IGEN ('.$v.')' : 'nem')));
}
} else { ki('  -- kimarad, nincs forras-oldal --'); }
ki('  Elementor verzio: '.(defined('ELEMENTOR_VERSION') ? ELEMENTOR_VERSION : 'NINCS DEFINIALVA'));
ki('  Elementor Pro   : '.(defined('ELEMENTOR_PRO_VERSION') ? ELEMENTOR_PRO_VERSION : 'nincs'));

ki('');
ki('=== 4. "Bryan Tracy" ELOFORDULAS -- KERESESSEL, NEM LISTABOL ===');
ki('  Minden poszt, amelynek barmely postametajaban szerepel a "Tracy" nev:');
$sor = $wpdb->get_results(
    "SELECT pm.post_id, pm.meta_key, p.post_name, p.post_status, p.post_type, p.post_title,
            (LENGTH(pm.meta_value)-LENGTH(REPLACE(pm.meta_value,'Bryan Tracy','')))/LENGTH('Bryan Tracy') AS hibas,
            (LENGTH(pm.meta_value)-LENGTH(REPLACE(pm.meta_value,'Brian Tracy','')))/LENGTH('Brian Tracy') AS helyes
       FROM {$wpdb->postmeta} pm JOIN {$wpdb->posts} p ON p.ID=pm.post_id
      WHERE pm.meta_value LIKE '%Tracy%'
      ORDER BY pm.post_id");
$osszHibas = 0; $oldalak = array(); $helyesOldalak = array();
foreach ($sor as $s) {
    $osszHibas += (int)$s->hibas;
    if ((int)$s->hibas > 0) { $oldalak[(int)$s->post_id] = $s->post_name; }
    if ((int)$s->hibas === 0 && (int)$s->helyes > 0) { $helyesOldalak[(int)$s->post_id] = $s->post_name; }
    ki(sprintf('  ID=%-6d %-12s %-9s %-28s meta=%-20s Bryan=%d Brian=%d',
        $s->post_id, $s->post_type, $s->post_status, substr($s->post_name,0,28),
        substr($s->meta_key,0,20), (int)$s->hibas, (int)$s->helyes));
    ki(sprintf('        cim: %s', $s->post_title));
}
ki(sprintf('  >>> JAVITANDO "Bryan Tracy" ELOFORDULAS OSSZESEN: %d   (postameta-sor: %d)', $osszHibas, count($sor)));
ki(sprintf('  >>> ERINTETT OLDALAK SZAMA: %d   ID-k: %s', count($oldalak),
    (count($oldalak) ? implode(', ', array_keys($oldalak)) : '-')));
foreach ($oldalak as $id=>$slug) { ki(sprintf('        javitando: ID=%d  %s', $id, $slug)); }
ki(sprintf('  >>> MAR HELYESEN all a nev %d oldalon: %s', count($helyesOldalak),
    (count($helyesOldalak) ? implode(', ', array_keys($helyesOldalak)) : '-')));
ki('  >>> Ha az erintett oldalak szama tobb mint 5, a korpusz alulmert, es a javitas-lista bovul.');
ki('  (OLDAL es SOR nem ugyanaz: ha egy oldalon ket kulonbozo meta-kulcsban all a nev,');
ki('   az ket sor de egy oldal. Nova a HANY OLDALON kerdesre var valaszt.)');
ki('  (Kontroll: a post_content-ben is megnezzuk, hatha nem csak Elementor-adatban all)');
$pcHibas = $wpdb->get_results(
    "SELECT ID, post_name, post_status FROM {$wpdb->posts} WHERE post_content LIKE '%Bryan Tracy%'");
ki(sprintf('  post_content-ben: %d poszt', count($pcHibas)));
foreach ($pcHibas as $s) { ki(sprintf('        ID=%d %s (%s)', $s->ID, $s->post_name, $s->post_status)); }

ki('');
ki('=== 5. A 16884 NYEREMENYJATEK-ELLENTMONDAS (fejlec kontra torzs) ===');
foreach (array(17153,16884,16355,16313,15135,13835,13716) as $id) {
    $d = get_post_meta($id, '_elementor_data', true);
    if (!is_string($d) || $d === '') { ki(sprintf('  ID=%-6d nincs _elementor_data (nem Elementor-oldal?)', $id)); continue; }
    $pp = get_post($id);
    ki(sprintf('  ID=%-6d slug=%-34s statusz=%-8s IG=%d FB=%d  Bryan=%d',
        $id, ($pp ? $pp->post_name : '?'), ($pp ? $pp->post_status : '?'),
        substr_count($d,'Instagram'), substr_count($d,'Facebook'), substr_count($d,'Bryan Tracy')));
    foreach (array('Instagram nyerem','Facebook nyerem') as $t) {
        if (strpos($d, $t) !== false) { ki(sprintf('        fejlec-talalat: "%s..."', $t)); }
    }
}

ki('');
ki('=== 6. SLUG-UTKOZES a tervezett atnevezesekhez ===');
foreach (array('meal-prep-kihivas','ingyenes-kihivas','egeszseges-reggeli-kihivas') as $slug) {
    $t = $wpdb->get_results($wpdb->prepare(
        "SELECT ID, post_status, post_type, post_title FROM {$wpdb->posts}
          WHERE post_name=%s AND post_status NOT IN ('inherit','auto-draft','trash')", $slug));
    if (!$t) { ki(sprintf('  %-30s SZABAD', $slug)); continue; }
    foreach ($t as $x) { ki(sprintf('  %-30s FOGLALT: ID=%d %s %s -- %s', $slug, $x->ID, $x->post_type, $x->post_status, $x->post_title)); }
}
ki('  (Ha a cel-slug foglalt, a WP NEMAN "-2"-t ragaszt, es a csere latszolag sikerul.)');

ki('');
ki('=== 7. MI ALL MOST az /ingyenes-kihivas/ uton ===');
$pg = get_page_by_path('ingyenes-kihivas');
ki($pg ? sprintf('  ID=%d  %s  (%s)', $pg->ID, $pg->post_title, $pg->post_status)
       : '  !! get_page_by_path("ingyenes-kihivas") NEM ad oldalt');
ki('');
ki('MERES VEGE. Semmit nem irtunk.');
