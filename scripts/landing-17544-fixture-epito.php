<?php
/**
 * LOKALIS PROBAPAD a 17544 szoveg-csere szkripthez. CSAK a lokalis dockeres WordPressen fut.
 *
 * MIERT KELL: a prod SSH nem az en kezemben van (dev-agens), tehat a szkript ELSO
 * futasa elesben lenne -- kontroll nelkul. Ez a pad eloallit egy oldalt, aminek a
 * `_elementor_data`-ja a 17544 MAI tarolt ertekeit hordozza, ugyanabban a beagyazasban
 * (section > column > widget), es igy a szkript teljes gepezete (elem-kereses, az
 * `icon_list.N.text` uton valo iras, ujrakodolas, visszameres) merheto eles iras nelkul.
 *
 * HASZNALAT:  php fixture-epito.php --json=<fixture.json> [--rontsd=<elem_id>|<ut>]
 * Kiirja a letrehozott oldal ID-jet `@@ OLDAL=<id>` alakban.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once getenv('WP_LOAD') ?: '/var/www/html/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$JSON = ''; $RONTSD = '';
foreach ($argv as $a) {
    if (strpos($a, '--json=') === 0)   { $JSON = substr($a, 7); }
    if (strpos($a, '--rontsd=') === 0) { $RONTSD = substr($a, 9); }
}
if (!$JSON || !is_readable($JSON)) { ki('!! nincs --json=<fajl>'); exit(2); }
$mezok = json_decode(file_get_contents($JSON), true);
if (!is_array($mezok)) { ki('!! a fixture JSON nem dekodolhato'); exit(2); }

/* A mezoket elem_id szerint csoportositjuk, es widget-szerkezetet epitunk beloluk.
   Az `icon_list.N.text` utakbol valodi icon_list tomb lesz, a tobbibol sima settings-kulcs. */
$widgetek = array();
foreach ($mezok as $kulcs => $ertek) {
    list($eid, $ut) = explode('|', $kulcs, 2);
    if (!isset($widgetek[$eid])) { $widgetek[$eid] = array('settings' => array(), 'tipus' => 'text-editor'); }
    if (preg_match('/^icon_list\.(\d+)\.text$/', $ut, $m)) {
        $widgetek[$eid]['tipus'] = 'icon-list';
        $widgetek[$eid]['settings']['icon_list'][(int) $m[1]] = array(
            '_id' => substr(md5($eid . $m[1]), 0, 7), 'text' => $ertek);
    } else {
        $widgetek[$eid]['settings'][$ut] = $ertek;
    }
}
if ($RONTSD !== '') {
    list($reid, $rut) = explode('|', $RONTSD, 2);
    if (!isset($widgetek[$reid])) { ki('!! a --rontsd elem nincs a fixture-ben: '.$reid); exit(2); }
    if (preg_match('/^icon_list\.(\d+)\.text$/', $rut, $m)) {
        $widgetek[$reid]['settings']['icon_list'][(int) $m[1]]['text'] = 'KEZZEL ATIRT SZOVEG (proba)';
    } else {
        $widgetek[$reid]['settings'][$rut] = 'KEZZEL ATIRT SZOVEG (proba)';
    }
    ki('rontas: '.$RONTSD.' -> "KEZZEL ATIRT SZOVEG (proba)"');
}

/* Beagyazas: section > column > widget, plusz EGY erintetlen szomszed widget, hogy a
   szkript szelektivitasa is latsszon (amihez nem nyul, az byte-ra maradjon). */
$elemek = array();
$i = 0;
foreach ($widgetek as $eid => $w) {
    $i++;
    $elemek[] = array(
        'id' => substr(md5('sec' . $eid), 0, 7), 'elType' => 'section', 'settings' => array(),
        'elements' => array(array(
            'id' => substr(md5('col' . $eid), 0, 7), 'elType' => 'column', 'settings' => array(),
            'elements' => array(
                array('id' => $eid, 'elType' => 'widget', 'widgetType' => $w['tipus'],
                      'settings' => $w['settings'], 'elements' => array()),
                array('id' => substr(md5('szomszed' . $i), 0, 7), 'elType' => 'widget',
                      'widgetType' => 'heading',
                      'settings' => array('title' => 'ERINTETLEN SZOMSZED '.$i), 'elements' => array()),
            ),
        )),
    );
}

$cim = 'PROBA landing 17544 fixture';
$meglevo = get_page_by_title($cim, OBJECT, 'page');
$id = $meglevo ? $meglevo->ID : wp_insert_post(array(
    'post_title' => $cim, 'post_type' => 'page', 'post_status' => 'draft'));
if (!$id || is_wp_error($id)) { ki('!! az oldal letrehozasa elbukott'); exit(2); }
update_post_meta($id, '_elementor_data', wp_slash(wp_json_encode($elemek, JSON_UNESCAPED_SLASHES)));
update_post_meta($id, '_elementor_css', 'proba-cache-ertek');
update_post_meta($id, '_elementor_page_assets', 'proba-assets-ertek');

ki(sprintf('fixture: %d widget, %d mezo, %d erintetlen szomszed', count($widgetek), count($mezok), $i));
ki('OLDAL='.$id);
