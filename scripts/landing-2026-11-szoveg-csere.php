<?php
/**
 * 2026-11 INGYENES-KIHIVAS LANDING: A SZOVEG BEVITELE.
 * GENERALT FAJL -- ne kezzel szerkeszd: scripts/landing-honap-generator.py.
 * FORRAS: 2026-11-ingyenes-kihivas-landing-szoveg.md  md5=4a6b5acea11005a8121418bbfa9fab24  mtime=2026-10-14 15:12:03
 * MERT ELO ALLAPOT: 2026-10-14T13:08:30.436Z
 *
 *   --site=dev --oldal=<ID>                       SZARAZ a deven (semmit nem ir)
 *   --site=dev --oldal=<ID> --apply               ELES a deven: csak a landing-dev-atvitel.php
 *                                                 altal jelolt oldalra ir
 *   --site=prod --oldal=<ID>                      SZARAZ a prodon
 *   --site=prod --oldal=<ID> --apply --yes-prod   ELES a prodon: CSAK a draft, ideiglenes slugu
 *                                                 masolatra (landing-rotacio.php --duplikal), es
 *                                                 csak Zsolt OK-ja utan
 *
 * MIT ELLENORIZ IRAS ELOTT, mezonkent: a VALTOZO mezo jelenlegi erteke a mert horgonnyal
 * kezdodik; a VALTOZATLAN (MARAD) mezok is a mert horgonnyal kezdodnek -- ezek a pozitiv
 * kontroll, hogy jo oldalon, jo allapotban vagyunk. Barmely elteres: SEMMIT nem irunk.
 * A mentes a $HOME-ba megy, NEM a webrootba (a 2026.10-es valtozat a webrootba irta).
 *
 * PROBAPAD: LANDING_CSERE_PROBAPAD=1 + --wp=<gyoker> -- CSAK a hoszt-ellenorzest kapcsolja ki.
 * A cel-orok (tiltott ID, dev-jelolo, prod draft+ideiglenes slug, --yes-prod) probapadon is
 * elnek: azokat pont ott kell tudni kiprobalni, ahol eles iras nem tortenhet.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
$HONAP = '2026-11';
$FORRAS_ID = 17544;
$TILTOTT = array(17544, 17153);
$PROD_IDEIGLENES = 'novemberi-kihivas-eloke';
$PAROK = array(
  array('elem_id' => '6b45d9c', 'ut' => 'title', 'horgony' => 'Indul a 7 napos egészséges reggeli kihívás', 'uj' => 'Indul a 7 napos pihentető alvás kihívás', 'cimke' => '1. szekció -- Hero / Heading'),
  array('elem_id' => 'b3e8629', 'ut' => 'editor', 'horgony' => 'Csatlakozz a kihíváshoz, és készíts velünk hét laktató reggelit egyszerű', 'uj' => '<p>Csatlakozz a kihíváshoz, és rakjuk össze együtt, lépésről lépésre a pihentető estéd rutinját! Minden napra egy apró lépéssel és egy könnyű vacsorával, hogy este könnyebben jöhessen az álom.</p><ul><li>7 apró lépés a pihentető estékért</li><li>6 könnyű vacsora és 1 esti ital</li><li>heti bevásárlólista</li><li>iOS és Android applikáció</li></ul>', 'cimke' => '1. szekció -- Hero / Text-editor (bevezető + felsorolás)'),
  array('elem_id' => 'ed700ab', 'ut' => 'editor', 'horgony' => 'Regisztrálj most, a kihívás teljesen ingyenes. Indulás: 2026. október 1.', 'uj' => '<p><strong>Regisztrálj most, a kihívás teljesen ingyenes.</strong> <br>Indulás: 2026. november 1.</p>', 'cimke' => '1. szekció -- Hero / Text-editor (a hero alatti sor)'),
  array('elem_id' => '6c78b0f2', 'ut' => 'title', 'horgony' => 'Reggelizz úgy, hogy délig kitartson', 'uj' => 'Készülj úgy az estére, hogy könnyebben jöjjön az álom', 'cimke' => '2. szekció -- Ígéret-cím + a jelenet / Heading'),
  array('elem_id' => '370bdfea', 'ut' => 'editor', 'horgony' => 'Reggel kapkodsz, és a végén marad a kávé meg valami gyors édesség. Ismerős?', 'uj' => '<p>Este fáradtan bebújsz az ágyba, aztán mégis csak forgolódsz. Ismerős? Vagy elalszol, de hajnalban felébredsz, és azon jár az eszed, mennyi időd van még a csörgésig. Reggel pedig úgy kelsz, mintha nem is aludtál volna, és az első kávéval próbálod összeszedni magad.</p><p>Pedig a pihentető éjszaka nem csak este dől el. Már reggel elkezdődik, amikor kilépsz a fényre, folytatódik délután, amikor az utolsó kávédat iszod, és este, amikor vacsorázol és lecsendesedsz.</p><p>A pihentető alvás kihívásban minden nap kapsz egy rövid leckét egy apró lépéssel, amit még aznap este kipróbálhatsz, és mellé egy könnyű vacsorareceptet. Így nem neked kell kitalálnod, hol kezdd: reggel elolvasod, este kipróbálod.</p><p>És nem kell felforgatnod az estéidet! Nincs szigorú szabály, és semmit nem kell tökéletesen csinálnod. Egy hét alatt, lépésről lépésre összeáll a saját esti rutinod, a Te ébredésedhez igazítva.</p>', 'cimke' => '2. szekció -- Ígéret-cím + a jelenet / Text-editor'),
  array('elem_id' => '8c97ba3', 'ut' => 'editor', 'horgony' => 'Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor', 'uj' => '<p>Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor ismételsz, akkor az szokássá válik. A megfelelő önfegyelemmel egy felnőtt embernek tizennégy és huszonegy nap közötti időre van szüksége ahhoz, hogy egy új szokást kialakítson. Ez idő alatt pedig rendszeresen kell ismételni az adott cselekvést. Az ingyenes kihívásban ehhez kapsz egy óriási lökést, és ha tetszik, folytasd tovább!</p><p>Nem az a cél, hogy egyik napról a másikra mindent megváltoztass, hanem az, hogy megtapasztald, milyen egy este, amikor nem kapkodva zuhansz az ágyba, hanem szépen, lépésről lépésre ráhangolódsz az alvásra.</p><p>A 21napalatt VIP Klubban nem állunk meg 7 napnál, további 14 napig folytatjuk együtt a pihentető esték építését a zárt klubban. Ha kedvet kapsz, Téged is sok szeretettel várunk, csatlakozz hozzánk!</p>', 'cimke' => '3. szekció -- Miért éppen 7 nap? [VÁLTOZ / Text-editor'),
  array('elem_id' => '17c1f49', 'ut' => 'editor', 'horgony' => 'Minden reggel ott vár egy recept, és hozzá a heti bevásárlólista, hogy ne a', 'uj' => '<p>Minden reggel ott vár az applikációban egy rövid lecke, és mellé egy könnyű vacsorarecept, a hétre szóló bevásárlólistával együtt. Megnézzük, miért reggel kezdődik a jó alvás, mikor érdemes meginni az utolsó kávét, mikor vacsorázz, mikor tompítsd a fényeket, és hogyan tudod este lecsendesíteni a napot. Az egyik estére pedig egy melengető, koffeinmentes esti italt készítünk.</p><p>A recepteket úgy válogattam össze, hogy könnyűek legyenek, és este ne terheljék meg a gyomrodat. A hozzávalókat a piacokon, boltok polcain könnyen megtalálod. Nem kell hozzájuk különleges konyhai tudás, és nem kell semmilyen speciális eszköz sem. Mindegyik gluténmentes, tejmentes, és nincs bennük hozzáadott cukor.</p><p>A kihívás teljesítésével egy csapásra két legyet is üthetsz: a 7. nap végén megveregetheted a válladat, hogy teljesítetted a tervet. De ami fontosabb, elindulhatsz az úton egy új, egészséges szokás kialakításához, amelyet csak folytatnod kell.</p><p>A hét végére összeáll a saját esti rutinod alapja. Ha megszereted, a 21napalatt VIP Klubban együtt haladunk tovább!</p>', 'cimke' => '4. szekció -- Mire számíthatsz? / Text-editor'),
  array('elem_id' => '9a135ee', 'ut' => 'title', 'horgony' => 'Mi változhat a reggeleidben?', 'uj' => 'Mi változhat az estéidben?', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Heading'),
  array('elem_id' => 'c927586', 'ut' => 'editor', 'horgony' => 'Ebben a hétben nem kell reggelente kapkodva döntened. Reggelre ott a terv,', 'uj' => '<p>Ezen a héten nem kell egyszerre mindent megváltoztatnod. Minden nap csak egy apró lépés jön, és a hét végére ezek szépen összeállnak.</p><p>A kihívás alatt megtapasztalhatod, hogy</p>', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Text-editor'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.0.text', 'horgony' => 'kitarthat a jóllakottság délig, és elmaradhat a délelőtti éhségroham', 'uj' => 'este könnyebben jöhet az álom', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Ikonos lista (4 elem) #1'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.1.text', 'horgony' => 'milyen egyszerű egészségesen indítani a napot', 'uj' => 'reggel kipihentebben ébredhetsz', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Ikonos lista (4 elem) #2'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.2.text', 'horgony' => 'negyedóra alatt is összeáll egy laktató reggeli', 'uj' => 'mennyit számít, mikor iszod az utolsó kávét, és mikor vacsorázol', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Ikonos lista (4 elem) #3'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.3.text', 'horgony' => 'mennyivel nyugodtabb egy reggel, ha nem akkor kell kitalálni, mit egyél', 'uj' => 'mennyivel nyugodtabb egy este, ha megvan a saját esti rutinod', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Ikonos lista (4 elem) #4'),
  array('elem_id' => '6a0ce87', 'ut' => 'editor', 'horgony' => 'Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt nem kell semmit sem', 'uj' => '<p>Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan eheted és ihatod ugyanazokat, amiket korábban is, mindössze az estéidet rakjuk össze együtt egy kicsit másképp.</p><p>A kihívás szokásokról és ételekről szól, nem orvosi kezelés. Ha tartósan nehezen alszol, kérd orvos segítségét.</p>', 'cimke' => '5. szekció -- Mi változhat az estéidben? / Text-editor (a kizárás)'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.0.text', 'horgony' => 'reggelente kapkodsz, és a végén marad a kávé meg valami gyors édesség,', 'uj' => 'este fáradtan bebújsz az ágyba, aztán mégis csak forgolódsz,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #1'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.1.text', 'horgony' => 'délelőtt tízkor már a keksz után nyúlsz, pedig reggeliztél,', 'uj' => 'hajnalban felébredsz, és nehezen jön vissza az álom,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #2'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.2.text', 'horgony' => 'unod a megszokott reggeliket, és nem jut eszedbe semmi új,', 'uj' => 'reggel úgy kelsz, mintha nem is aludtál volna,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #3'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.3.text', 'horgony' => 'szeretnél egészségesebben reggelizni, de kevés időd van reggelenként,', 'uj' => 'délután még jólesik egy kávé, és este nehezen csendesedsz le,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #4'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.4.text', 'horgony' => 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél,', 'uj' => 'lefekvés előtt még a telefont görgeted, mert nehéz letenni,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #5'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.5.text', 'horgony' => 'gluténmentesen vagy tejmentesen étkezel, és elfogytak az ötleteid,', 'uj' => 'munka és család mellett este végre a Tiéd az idő, és nehéz lefeküdni,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #6'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.6.text', 'horgony' => 'munka és család mellett jól jönne egy kis segítség a reggelekhez,', 'uj' => 'szeretnél könnyű vacsorákat, de este már nincs kedved kitalálni, mi kerüljön az asztalra,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #7'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.7.text', 'horgony' => 'vagy egyszerűen kíváncsi vagy, hogy mitől lesz laktató egy reggeli.', 'uj' => 'vagy egyszerűen kíváncsi vagy, hogy mi segíthet könnyebben elaludni.', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (8 elem) #8'),
  array('elem_id' => 'be0d9b5', 'ut' => 'editor', 'horgony' => 'Remélem, a hét végére Te is úgy nézel majd a reggeli asztalon álló tányérodra,', 'uj' => '<p>Remélem, a hét végére Te is úgy oltod le este az éjjeli lámpát, hogy közben arra gondolsz: ezt miért nem csináltam eddig?</p>', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Text-editor (záró vágykép)'),
  array('elem_id' => '1cfd5a8', 'ut' => 'editor', 'horgony' => 'Készíts fotót az elkészült reggelidről. Posztold a kihívás Facebook', 'uj' => '<ul><li><strong>Készíts fotót az elkészült vacsorádról vagy esti italodról.</strong></li><li><strong>Posztold a kihívás Facebook csoportjában a @21napalatt_kihivas hashtaggel.</strong></li></ul><p>November 8-án a legalább 1 képet feltöltők között kisorsolunk egy szerencsés résztvevőt, aki 1 hónapos 21napalatt VIP Klub előfizetést nyer.</p><p>A 21napalatt VIP Klubtagság teljes hozzáférést ad a klub minden tartalmához: 21 napos életmódprogramhoz, a hetente frissülő menütervekhez, 600+ tej-, cukor- és gluténmentes recepthez, 21 napos kihívásokhoz, tudásanyagokhoz, a zárt Facebook csoporthoz.</p>', 'cimke' => '11. szekció -- Nyereményjáték (platform: / Text-editor'),
  array('elem_id' => '3685e05', 'ut' => 'title', 'horgony' => 'Jelentkezem a 7 napos egészséges reggeli kihívásra', 'uj' => 'Jelentkezem a 7 napos pihentető alvás kihívásra', 'cimke' => '12. szekció -- Űrlap-cím / Heading')
);
$MARAD = array(
  array('elem_id' => '2aec29b', 'ut' => 'text', 'horgony' => 'Én is kipróbálom', 'cimke' => 'Gomb 1'),
  array('elem_id' => '4aa9c3b', 'ut' => 'title', 'horgony' => 'Miért éppen 7 nap?', 'cimke' => 'Heading'),
  array('elem_id' => 'c0f829f', 'ut' => 'text', 'horgony' => 'Már megyek is', 'cimke' => 'Gomb 2'),
  array('elem_id' => '64ff707', 'ut' => 'title', 'horgony' => 'Mire számíthatsz?', 'cimke' => 'Heading'),
  array('elem_id' => 'e2e10c5', 'ut' => 'text', 'horgony' => 'Vágjunk bele, csatlakozom', 'cimke' => 'Gomb 3'),
  array('elem_id' => '2053b90', 'ut' => 'text', 'horgony' => 'Wow, erre rámegyek', 'cimke' => 'Gomb 4'),
  array('elem_id' => '94b920d', 'ut' => 'title', 'horgony' => 'Imádni fogod a kihívást, ha', 'cimke' => 'Heading'),
  array('elem_id' => '4ac6aea', 'ut' => 'text', 'horgony' => 'Naná, regisztrálok is', 'cimke' => 'Gomb 5'),
  array('elem_id' => 'e2e740b', 'ut' => 'title', 'horgony' => 'A kihívás menete', 'cimke' => 'Heading'),
  array('elem_id' => 'fb7e110', 'ut' => 'title', 'horgony' => 'Regisztrálj a kihívásra', 'cimke' => '7. Heading'),
  array('elem_id' => 'eadbb3d', 'ut' => 'editor', 'horgony' => 'Utána máris be tudsz lépni a kihívás felületére.', 'cimke' => 'Text'),
  array('elem_id' => '1ed9313', 'ut' => 'title', 'horgony' => 'Töltsd le az applikációt', 'cimke' => '8. Heading'),
  array('elem_id' => 'c0ad3ec', 'ut' => 'editor', 'horgony' => 'iOS vagy Android készülékedre és lépj be!', 'cimke' => 'Text'),
  array('elem_id' => 'cd7ec3e', 'ut' => 'title', 'horgony' => 'Keresd a bevásárlólistát', 'cimke' => '9. Heading'),
  array('elem_id' => '84b9598', 'ut' => 'editor', 'horgony' => 'és szerezd be a hozzávalókat!', 'cimke' => 'Text'),
  array('elem_id' => '76c4bce', 'ut' => 'title', 'horgony' => 'Nyerj 1 hónap 21napalatt VIP Klub előfizetést Facebook nyereményjátékunkon', 'cimke' => 'Heading'),
  array('elem_id' => '5b4972b', 'ut' => 'text', 'horgony' => 'Itt a helyem, regisztrálok', 'cimke' => 'Gomb 6')
);

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$YESPROD = in_array('--yes-prod', $ARGV, true);
$SITE = ''; $OLDAL = 0; $WP = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--site=') === 0)  { $SITE = substr($a, 7); }
    if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); }
    if (strpos($a, '--wp=') === 0)    { $WP = rtrim(substr($a, 5), '/'); }
}
$PROBAPAD = getenv('LANDING_CSERE_PROBAPAD') === '1';
function ki($s){ echo '@@ '.$s."\n"; }
/* Probapadon a forras-ID ugyanugy felulirhato, mint a landing-dev-atvitel.php-ban (LANDING_FORRAS),
   kulonben a lokalis atvitel jeloloje (a fixture ID-ja) es ez a szkript kulon vilagban elne. */
if ($PROBAPAD && getenv('LANDING_FORRAS')) { $FORRAS_ID = (int) getenv('LANDING_FORRAS'); }
$HOSTOK = array('dev' => 'dev.21napalatt.hu', 'prod' => 'vip.21napalatt.hu');
if (!isset($HOSTOK[$SITE])) { ki('!! KOTELEZO a --site=dev|prod.'); exit(2); }
if ($WP !== '' && !$PROBAPAD) { ki('!! A --wp csak probapadon (LANDING_CSERE_PROBAPAD=1) adhato meg.'); exit(2); }
if ($WP === '') { $WP = '/home/napalatt/'.$HOSTOK[$SITE]; }
if (!file_exists($WP.'/wp-load.php')) { ki('!! nincs wp-load.php: '.$WP); exit(2); }
require_once $WP.'/wp-load.php';
error_reporting(E_ERROR | E_PARSE);

$host = (string) parse_url(home_url(), PHP_URL_HOST);
ki('LANDING '.$HONAP.' SZOVEG-CSERE  '.gmdate('c').' UTC   site='.$SITE.'  home='.home_url().'  DB='.DB_NAME);
if ($PROBAPAD) { ki('*** PROBAPAD: a hoszt-ellenorzes KI van kapcsolva (a cel-orok elnek). ***'); }
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');
if (!$PROBAPAD && $host !== $HOSTOK[$SITE]) { ki('!! --site='.$SITE.', de ez a telepites: '.$host.'. ALLJ MEG.'); exit(2); }
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is. Nem talalgatok.'); exit(2); }
if (in_array($OLDAL, $TILTOTT, true) && $SITE === 'prod') {
    ki('!! A '.$OLDAL.' elo vagy korabbi landing -- NEM irunk ra.'); exit(2);
}
$p = get_post($OLDAL);
if (!$p) { ki('!! a '.$OLDAL.' nem letezik ezen a peldanyon.'); exit(2); }
ki('celpont: '.$OLDAL.'  slug='.$p->post_name.'  status='.$p->post_status.'  cim='.$p->post_title);
{
    if ($SITE === 'dev' && get_post_meta($OLDAL, '_landing_atvitel_forras', true) !== (string) $FORRAS_ID) {
        ki('!! A deven csak a landing-dev-atvitel.php altal atvitt oldalra irok (_landing_atvitel_forras='.$FORRAS_ID.').');
        exit(2);
    }
    if ($SITE === 'prod' && ($p->post_name !== $PROD_IDEIGLENES || $p->post_status !== 'draft')) {
        ki('!! A prodon csak a draft, "'.$PROD_IDEIGLENES.'" slugu masolatra irok. Ez nem az.'); exit(2);
    }
}
if ($APPLY && $SITE === 'prod' && !$YESPROD) { ki('!! Prod iras csak --yes-prod-dal (Zsolt OK utan).'); exit(2); }
ki('');

$d = get_post_meta($OLDAL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$OLDAL.'-on'); exit(2); }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit(2); }

function &km_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings' || !is_array($gy)) { continue; }
        $t =& km_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}
function km_ut_ertek($settings, $ut) {
    $p = $settings;
    foreach (explode('.', $ut) as $r) {
        if (is_array($p) && array_key_exists($r, $p)) { $p = $p[$r]; } else { return null; }
    }
    return is_string($p) ? $p : null;
}
function km_ut_ir(&$settings, $ut, $ertek) {
    $p =& $settings;
    foreach (explode('.', $ut) as $r) {
        if (!is_array($p) || !array_key_exists($r, $p)) { return false; }
        $p =& $p[$r];
    }
    $p = $ertek;
    return true;
}
function km_tiszta($s) {
    $s = preg_replace('#<(/p|/li|br\s*/?|/h[1-6])\s*>#i', ' ', $s);
    $s = html_entity_decode(wp_strip_all_tags($s), ENT_QUOTES | ENT_HTML5, 'UTF-8');   // &nbsp; &amp; is
    return trim(preg_replace('/\s+/u', ' ', str_replace("\xC2\xA0", ' ', $s)));
}
function km_kezdodik($most, $horgony) {
    $h = km_tiszta($horgony);
    return mb_substr(km_tiszta($most), 0, mb_strlen($h)) === $h;
}

$hiba = 0;
ki('KONTROLL: a valtozatlan mezok ('.count($MARAD).') a mert allapotot hordozzak-e');
$jo = 0;
foreach ($MARAD as $m) {
    $e =& km_elem($fa, $m['elem_id']);
    $most = ($e === null) ? null : km_ut_ertek($e['settings'], $m['ut']);
    if ($most === null || !km_kezdodik($most, $m['horgony'])) {
        $hiba++;
        ki(sprintf('  !! [%s] %s (%s): %s', $m['elem_id'], $m['ut'], $m['cimke'],
            $most === null ? 'NINCS ilyen elem/mezo' : 'mas: '.mb_substr(km_tiszta($most), 0, 70)));
    } else { $jo++; }
    unset($e);
}
ki(sprintf('  %d/%d rendben', $jo, count($MARAD)));
ki('');
ki('CSERE ('.count($PAROK).' mezo):');
foreach ($PAROK as $par) {
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) { ki(sprintf('  !! [%s] NINCS ILYEN ELEM', $par['elem_id'])); $hiba++; unset($elem); continue; }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) { ki(sprintf('  !! [%s] nincs ilyen mezo: %s', $par['elem_id'], $par['ut'])); $hiba++; unset($elem); continue; }
    if (!km_kezdodik($most, $par['horgony'])) {
        ki(sprintf('  !! [%s] %s: a jelenlegi ertek NEM a mert horgonnyal kezdodik -- KIHAGYVA', $par['elem_id'], $par['ut']));
        ki('        most:    '.mb_substr(km_tiszta($most), 0, 90));
        ki('        horgony: '.mb_substr(km_tiszta($par['horgony']), 0, 90));
        $hiba++; unset($elem); continue;
    }
    ki(sprintf('  [%s] %s  -- %s', $par['elem_id'], $par['ut'], $par['cimke']));
    ki('        regi: '.mb_substr(km_tiszta($most), 0, 90));
    ki('        uj:   '.mb_substr(km_tiszta($par['uj']), 0, 90));
    if ($APPLY && !km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++;
    }
    unset($elem);
}
ki('');
ki(sprintf('OSSZESEN: %d hiba/kihagyas', $hiba));
if (!$APPLY) { ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit($hiba > 0 ? 1 : 0); }
if ($hiba > 0) { ki('!! VOLT HIBA -- NEM IRUNK AZ OLDALRA. Reszleges szoveg rosszabb, mint a regi.'); exit(1); }

$home = getenv('HOME') ?: dirname($WP);
$mentes = rtrim($home, '/').'/landing-szoveg-mentes-'.$SITE.'-'.$OLDAL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($OLDAL, '_elementor_data', wp_slash($uj));
/* A negy cache-reteg (2026-09-21 ota): css, page_assets, element_cache, post cache + LiteSpeed. */
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) { delete_post_meta($OLDAL, $mk); }
clean_post_cache($OLDAL);
if (has_action('litespeed_purge_post')) { do_action('litespeed_purge_post', $OLDAL); ki('litespeed_purge_post: kiadva'); }
else { ki('litespeed_purge_post: NINCS ilyen action'); }
if (has_action('litespeed_purge_all')) { do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva'); }
else { ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.'); }

ki('');
ki('VISSZAMERES -- mezonkent:');
$faV = json_decode(get_post_meta($OLDAL, '_elementor_data', true), true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    $e =& km_elem($faV, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; } else { $rossz++; ki(sprintf('  !! [%s] %s NEM az uj erteket adja', $par['elem_id'], $par['ut'])); }
    unset($e);
}
$mOk = 0;
foreach ($MARAD as $m) {
    $e =& km_elem($faV, $m['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $m['ut']);
    if ($ert !== null && km_kezdodik($ert, $m['horgony'])) { $mOk++; } else { $rossz++; ki(sprintf('  !! [%s] %s (valtozatlan) ELMOZDULT', $m['elem_id'], $m['ut'])); }
    unset($e);
}
ki(sprintf('  %d/%d uj mezo a vart erteket adja; %d/%d valtozatlan mezo valtozatlan.', $ok, count($PAROK), $mOk, count($MARAD)));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($OLDAL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.' : '!! ELES MENET VEGE, DE VOLT ELTERES.');
exit($rossz === 0 ? 0 : 1);
