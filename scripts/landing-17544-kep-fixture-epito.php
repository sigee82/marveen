<?php
/**
 * LOKALIS PROBAPAD a 17544 kep-csere szkripthez (csak a dockeres WordPressen).
 * Eloallit egy oldalt harom image-widgettel, a 17544 MAI kep-allapotaval, plusz
 * KET allando ikonnal, amikhez a szkriptnek NEM szabad hozzanyulnia.
 *   --rontsd=<elem_id>   az adott elem attachment-id-jet elallitja (negativ kontroll)
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once getenv('WP_LOAD') ?: '/var/www/html/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }
$RONTSD = '';
foreach ($argv as $a) { if (strpos($a, '--rontsd=') === 0) { $RONTSD = substr($a, 9); } }

$B = 'https://vip.21napalatt.hu/wp-content/uploads/';
$kepek = array(
    array('043088b', 17163, $B.'2026/08/honlapkep_meal_prep_1.png'),
    array('18e743f', 17164, $B.'2026/08/honlapkep_meal_prep_2.png'),
    array('62377a6', 17165, $B.'2026/08/honlapkep_meal_prep_3.png'),
    // ALLANDO ELEMEK -- ezekhez a szkriptnek nem szabad hozzanyulnia:
    array('41adc9f', 13723, $B.'2025/12/kihivas-ikon.png'),
    array('3eacd38', 13794, $B.'2025/12/lepes-1.png'),
);
$elemek = array();
foreach ($kepek as $k) {
    list($eid, $aid, $url) = $k;
    if ($RONTSD === $eid) { $aid = 99999; ki('rontas: '.$eid.' attachment-id -> 99999'); }
    $elemek[] = array('id' => substr(md5('s'.$eid),0,7), 'elType' => 'section', 'settings' => array(),
      'elements' => array(array('id' => substr(md5('c'.$eid),0,7), 'elType' => 'column',
        'settings' => array(), 'elements' => array(
          array('id' => $eid, 'elType' => 'widget', 'widgetType' => 'image', 'elements' => array(),
                'settings' => array('image' => array('id' => $aid, 'url' => $url),
                                    'image_size' => 'large'))))));
}
$cim = 'PROBA landing 17544 kep-fixture';
$meg = get_page_by_title($cim, OBJECT, 'page');
$id = $meg ? $meg->ID : wp_insert_post(array('post_title'=>$cim,'post_type'=>'page','post_status'=>'draft'));
update_post_meta($id, '_elementor_data', wp_slash(wp_json_encode($elemek, JSON_UNESCAPED_SLASHES)));
update_post_meta($id, '_elementor_css', 'proba-cache-ertek');
ki('OLDAL='.$id);
