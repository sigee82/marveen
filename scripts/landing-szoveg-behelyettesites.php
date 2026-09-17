<?php
/**
 * AZ OKTOBERI LANDING SZOVEGENEK BEVITELE.  GENERALT FAJL -- ne kezzel szerkeszd,
 * hanem a scripts/landing-behelyettesites-generator.py-t futtasd ujra.
 *
 *   (alapertelmezes)      SZARAZ: semmit nem ir, csak megmutatja, mi tortenne
 *   --apply --oldal=<ID>  ELES: a MEGADOTT oldalra irja be a szoveget
 *
 * A CELPONT A DUPLIKATUM, NEM A FORRAS. Az `--oldal` KOTELEZO az eles menetben, es a
 * szkript MEGTAGADJA a 17153-at: a forras-oldal a REGI, elo landing, azon nincs dolgunk.
 *
 * MIERT MEZO-SZINTU A VISSZAMERES, ES NEM BYTE-AZONOSSAG: a `_elementor_data`-t ujra
 * kell kodolni, es a kodolas ALAKJA valtozhat (escape-bol nyers vagy forditva). Az
 * Elementornak ez mindegy -- dekodolva ugyanaz --, de a byte-osszevetes "az egesz oldal
 * megvaltozott"-at mutatna. Ezert MEZONKENT olvassuk vissza. A kodolas
 * JSON_UNESCAPED_UNICODE NELKUL megy, mert a prod igy tarolja (Nova 2026-09-17-i szaraz
 * menete mérte: a fejlec `\uXXXX` alakban allt).
 *
 * A CSERE ELOTT MINDEN MEZOT ELLENORZUNK: ha a jelenlegi ertek NEM az, amit a parositas
 * rogzitett, az adott mezot KIHAGYJUK es jelentjuk. Egy elcsuszott oldal-allapot igy nem
 * ir felul valamit vaktaban.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
require_once '/home/napalatt/vip.21napalatt.hu/wp-load.php';
error_reporting(E_ERROR | E_PARSE);
function ki($s){ echo '@@ '.$s."\n"; }

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$OLDAL = 0;
foreach ($ARGV as $a) { if (strpos($a, '--oldal=') === 0) { $OLDAL = (int) substr($a, 8); } }
$FORRAS = 17153;
$MENTES_DIR = '/home/napalatt/vip.21napalatt.hu';

$MARAD_DB = 13;
$PAROK = array(
  array('elem_id' => '6b45d9c', 'ut' => 'title', 'jelenlegi' => 'Indul a 7 napos meal prep kihívás', 'uj' => 'Indul a 7 napos egészséges reggeli kihívás', 'csere' => true),
  array('elem_id' => 'b3e8629', 'ut' => 'editor', 'jelenlegi' => 'Csatlakozz a kihíváshoz, és próbáld ki, hogy milyen finom, v', 'uj' => 'Csatlakozz a kihíváshoz, és rakjuk össze együtt azt a reggelit, ami nem tíz perc alatt elszáll, hanem kitart délig.

minden napra egy recept, 7 napon át
heti bevásárlólista
gluténmentes, tejmentes, hozzáadott cukor nélkül
iOS és Android applikáció', 'csere' => true),
  array('elem_id' => 'ed700ab', 'ut' => 'editor', 'jelenlegi' => 'Regisztrálj most, a kihívás teljesen ingyenes. Indulás: 2026', 'uj' => 'Regisztrálj most, a kihívás teljesen ingyenes.
Indulás: 2026. október 1.', 'csere' => true),
  array('elem_id' => '6c78b0f2', 'ut' => 'title', 'jelenlegi' => 'Főzz kevesebbet, egyél változatosabban', 'uj' => 'Reggelizz úgy, hogy délig kitartson', 'csere' => true),
  array('elem_id' => '370bdfea', 'ut' => 'editor', 'jelenlegi' => 'Mit együnk ma? - ismerős a kérdés? Sokszor nem egy jó recept', 'uj' => 'Reggel kapkodsz, és a végén marad a kávé meg valami gyors édesség - ismerős? Aztán tíz óra körül hirtelen megjön az éhség, és már a keksz után nyúlsz. Nem az akaraterővel van baj: az édesen indított reggeli után a vércukor felszalad, majd leesik, és ez a hullámvasút csinálja a délelőtti éhségrohamot.
 
A 7 napos egészséges reggeli kihívás 7 napon át minden nap hoz egy kész receptet és a hozzá tartozó bevásárlólistát, hogy reggelente ne neked kelljen kitalálni, mi legyen.
 
Nem kell felforgatnod a reggeleidet. Elég egy hét, hogy kipróbálj hat laktató reggelit meg egy reggeli italt, és kiderüljön, melyik az a kettő-három, ami beleférne a Te hétköznapodba is.', 'csere' => true),
  array('elem_id' => '4aa9c3b', 'ut' => 'title', 'jelenlegi' => 'Miért éppen 7 nap?', 'uj' => 'Miért éppen 7 nap?', 'csere' => true),
  array('elem_id' => '8c97ba3', 'ut' => 'editor', 'jelenlegi' => 'Bryan Tracy gyakorlás törvénye kimondja, hogy ha egy tevéken', 'uj' => 'Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor ismételsz, akkor az szokássá válik. A megfelelő önfegyelemmel egy felnőtt embernek tizennégy és huszonegy nap közötti időre van szüksége ahhoz, hogy egy új szokást kialakítson. Ez idő alatt pedig rendszeresen kell ismételni az adott cselekvést. Az ingyenes kihívásban ehhez kapsz egy óriási lökést, és ha tetszik, folytasd tovább!
Nem az a cél, hogy egyik napról a másikra mindent megváltoztass, hanem az, hogy megtapasztald, működik-e neked ez a fajta reggeli, egyszerűbb-e így reggelente jól dönteni.
A 21napalatt VIP Klubban nem állunk meg 7 napnál, további 14 napig építjük együtt a reggeli-rendszeredet a zárt klubban. Ha kedvet kapsz, Téged is sok szeretettel várunk, csatlakozz hozzánk!', 'csere' => true),
  array('elem_id' => '64ff707', 'ut' => 'title', 'jelenlegi' => 'Mire számíthatsz?', 'uj' => 'Mire számíthatsz?', 'csere' => true),
  array('elem_id' => '17c1f49', 'ut' => 'editor', 'jelenlegi' => 'A 7 napos meal prep kihívás alatt 7 változatos főétkezést ké', 'uj' => 'A 7 napos egészséges reggeli kihívás alatt minden nap kapsz egy receptet, és hozzá a heti bevásárlólistát. Lesz köztük gyors serpenyős reggeli, tálban összerakható, kásás, és azt is megnézzük, mit érdemes inni a reggeli mellé.
A recepteket úgy állítottam össze, hogy táplálóak, változatosak és reggel is reálisan elkészíthetőek legyenek. A hozzávalókat a piacokon, boltok polcain könnyen megtalálod. Nem kell hozzájuk különleges konyhai tudás, és nem kell semmilyen speciális eszköz sem. Mindegyik gluténmentes, tejmentes, és nincs bennük hozzáadott cukor.
A kihívás teljesítésével egy csapásra két legyet is üthetsz: a 7. nap végén megveregetheted a válladat, hogy teljesítetted a tervet. De ami fontosabb, elindulhatsz az úton egy új, egészséges szokás kialakításához, amelyet csak folytatnod kell.
A kihívás végére lesz 7 új recepted, amit később bármikor elővehetsz, amikor reggel nem jut eszedbe semmi.', 'csere' => true),
  array('elem_id' => '9a135ee', 'ut' => 'title', 'jelenlegi' => 'Mit kapsz még?', 'uj' => 'Mit kapsz még?', 'csere' => true),
  array('elem_id' => 'c927586', 'ut' => 'editor', 'jelenlegi' => 'A Meal Prep kihívás abban segít, hogy ne kelljen minden egye', 'uj' => 'Az egészséges reggeli abban segít, hogy ne a nap legrosszabb döntésével indítsd a napot, és ne délelőtt tízkor kelljen helyrehozni.
A kihívás alatt megtapasztalhatod, hogy', 'csere' => true),
  array('elem_id' => '360da42', 'ut' => 'icon_list.0.text', 'jelenlegi' => 'sokkal kevesebb idő is elég lehet a hétköznapi főzéshez', 'uj' => 'kitarthat a jóllakottság délig, és elmaradhat a délelőtti éhségroham', 'csere' => true),
  array('elem_id' => '360da42', 'ut' => 'icon_list.1.text', 'jelenlegi' => 'milyen egyszerű többféle zöldséget enni', 'uj' => 'milyen egyszerű sósan indítani a napot', 'csere' => true),
  array('elem_id' => '360da42', 'ut' => 'icon_list.2.text', 'jelenlegi' => 'milyen könnyű változatosan étkezni', 'uj' => 'néhány perc is elég lehet egy laktató reggelihez', 'csere' => true),
  array('elem_id' => '360da42', 'ut' => 'icon_list.3.text', 'jelenlegi' => 'mennyivel könnyebb fenntartani az egészséges étkezést, ha va', 'uj' => 'mennyivel nyugodtabb egy reggel, ha nem kell kitalálni, mi legyen', 'csere' => true),
  array('elem_id' => '6a0ce87', 'ut' => 'editor', 'jelenlegi' => 'Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt ne', 'uj' => 'Ez nem egy méregtelenítő- vagy fogyókúra. A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan eheted és ihatod ugyanazokat, amiket korábban is, mindössze a reggelidet rakjuk össze együtt egy kicsit másképp.', 'csere' => true),
  array('elem_id' => '94b920d', 'ut' => 'title', 'jelenlegi' => 'Imádni fogod a kihívást, ha', 'uj' => 'Imádni fogod a kihívást, ha', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.0.text', 'jelenlegi' => 'szeretnél egészségesebben enni, de nincs időd minden nap főz', 'uj' => 'reggelente kapkodsz, és a végén marad a kávé meg valami gyors édesség', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.1.text', 'jelenlegi' => 'gyakran délután jut eszedbe, hogy jaj, még vacsora is kellen', 'uj' => 'délelőtt tízkor már a keksz után nyúlsz, pedig reggeliztél', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.2.text', 'jelenlegi' => 'kevés időd van, de szeretnél egészségesebb döntéseket hozni,', 'uj' => 'unod a megszokott reggeliket, és nem jut eszedbe semmi új', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.3.text', 'jelenlegi' => 'szeretnél több zöldséget és hüvelyest enni,', 'uj' => 'szeretnél egészségesebben reggelizni, de reggel nincs időd főzni', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.4.text', 'jelenlegi' => 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél,', 'uj' => 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.5.text', 'jelenlegi' => 'kipróbáltad már az előre főzést, de nem akarsz napokig ugyan', 'uj' => 'gluténmentesen vagy tejmentesen étkezel, és elfogytak az ötleteid', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.6.text', 'jelenlegi' => 'munka és család mellett jól jönne egy kis segítség a menüter', 'uj' => 'munka és család mellett jól jönne egy kis segítség a reggelekhez', 'csere' => true),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.7.text', 'jelenlegi' => 'vagy egyszerűen kíváncsi vagy, hogy könnyebb-e meal preppel', 'uj' => 'vagy egyszerűen kíváncsi vagy, mitől lesz laktató egy reggeli.', 'csere' => true),
  array('elem_id' => 'be0d9b5', 'ut' => 'editor', 'jelenlegi' => 'Remélem, a hét végére Te is úgy nézel majd a hűtődben sorako', 'uj' => 'Remélem, a hét végére Te is úgy nézel majd erre a hétre, hogy volt közte legalább két olyan reggeli, amit tényleg meg akarsz tartani - és közben arra gondolsz, hogy ezt miért nem kezdtem el hamarabb?', 'csere' => true),
  array('elem_id' => '76c4bce', 'ut' => 'title', 'jelenlegi' => 'Nyerj 1 hónap 21napalatt VIP Klub előfizetést Facebook nyere', 'uj' => 'Nyerj 1 hónap 21napalatt VIP Klub előfizetést Facebook nyereményjátékunkon', 'csere' => true),
  array('elem_id' => '1cfd5a8', 'ut' => 'editor', 'jelenlegi' => 'Készíts fotót az elkészült meal prep ételedről.Posztold a ki', 'uj' => 'Készíts fotót az elkészült reggelidről.
Posztold a kihívás Facebook csoportjában a @21napalatt_kihivas hashtaggel
Október 8-án a legalább 1 képet feltöltők között kisorsolunk egy szerencsés résztvevőt,
aki 1 hónapos 21napalatt VIP Klub előfizetést nyer.
A 21napalatt VIP Klubtagság teljes hozzáférést ad a klub minden tartalmához: 21 napos életmódprogramhoz, a hetente frissülő menütervekhez, 500+ tej-, cukor- és gluténmentes recepthez, 21 napos kihívásokhoz, tudásanyagokhoz, a zárt Facebook csoporthoz.', 'csere' => true),
  array('elem_id' => '3685e05', 'ut' => 'title', 'jelenlegi' => 'Jelentkezem a 7 napos meal prep kihívásra', 'uj' => 'Jelentkezem a 7 napos egészséges reggeli kihívásra', 'csere' => true)
);

ki('LANDING-SZOVEG BEHELYETTESITES  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');

if ($OLDAL === $FORRAS) {
    ki('!! A megadott oldal a FORRAS ('.$FORRAS.') -- az a REGI, elo landing. NEM irunk ra.');
    exit;
}
if ($APPLY && $OLDAL <= 0) { ki('!! Eles menethez KOTELEZO a --oldal=<ID>. Nem talalgatok.'); exit; }
$CEL = $OLDAL > 0 ? $OLDAL : $FORRAS;   // szarazon a forrason mutatjuk meg, mi tortenne
ki('celpont: '.$CEL.($OLDAL > 0 ? '' : '  (szaraz menet, a forrason mutatva)'));
ki('');

$d = get_post_meta($CEL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$CEL.'-on'); exit; }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit; }

/** Egy elem megkeresese ID szerint, REFERENCIAVAL (hogy irni is tudjunk). */
function &km_elem(&$node, $id) {
    $nincs = null;
    if (!is_array($node)) { return $nincs; }
    if (isset($node['elType']) && isset($node['id']) && $node['id'] === $id) { return $node; }
    foreach ($node as $k => &$gy) {
        if ($k === 'settings') { continue; }
        if (!is_array($gy)) { continue; }
        $t =& km_elem($gy, $id);
        if ($t !== null) { return $t; }
    }
    return $nincs;
}
/** Ertek kiolvasasa/irasa a `icon_list.0.text` alaku uton belul a settings-ben. */
function km_ut_ertek($settings, $ut) {
    $reszek = explode('.', $ut);
    $p = $settings;
    foreach ($reszek as $r) {
        if (is_array($p) && array_key_exists($r, $p)) { $p = $p[$r]; }
        else { return null; }
    }
    return is_string($p) ? $p : null;
}
function km_ut_ir(&$settings, $ut, $ertek) {
    $reszek = explode('.', $ut);
    $p =& $settings;
    foreach ($reszek as $r) {
        if (!is_array($p) || !array_key_exists($r, $p)) { return false; }
        $p =& $p[$r];
    }
    $p = $ertek;
    return true;
}

$cserelt = 0; $kihagyott = 0; $hiba = 0;
foreach ($PAROK as $par) {
    if (empty($par['csere'])) { continue; }
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) {
        ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon -- kihagyva', $par['elem_id'])); $hiba++; continue;
    }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) {
        ki(sprintf('  !! [%s] nincs ilyen mezo: %s -- kihagyva', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $mostTiszta = trim(preg_replace('/\s+/', ' ', wp_strip_all_tags($most)));
    $vartTiszta = trim(preg_replace('/\s+/', ' ', $par['jelenlegi']));
    /* A meres 60 karakternel vagott, ezert a VART erteket prefixkent vetjuk ossze --
       es ezt ki is mondjuk, hogy senki ne olvassa teljes egyezesnek. */
    if (mb_substr($mostTiszta, 0, mb_strlen($vartTiszta)) !== $vartTiszta) {
        ki(sprintf('  !! [%s] %s: a JELENLEGI ertek nem az, amit a parositas rogzitett -- KIHAGYVA',
            $par['elem_id'], $par['ut']));
        ki(sprintf('        most: %s', mb_substr($mostTiszta, 0, 70)));
        ki(sprintf('        vart: %s', mb_substr($vartTiszta, 0, 70)));
        $hiba++; continue;
    }
    if (!$APPLY) {
        ki(sprintf('  [szaraz] [%s] %s', $par['elem_id'], $par['ut']));
        ki(sprintf('        -> %s', mb_substr(preg_replace('/\s+/', ' ', $par['uj']), 0, 70)));
        $cserelt++; continue;
    }
    if (!km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $cserelt++;
}

ki('');
ki(sprintf('CSERE: %d   HIBA/KIHAGYVA: %d   (a MARAD mezokhez nem nyultunk: %d)',
    $cserelt, $hiba, $MARAD_DB));

if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit; }
if ($hiba > 0) {
    ki('');
    ki('!! VOLT LEGALABB EGY KIHAGYOTT MEZO -- NEM IRUNK AZ OLDALRA.');
    ki('   Reszleges szoveg rosszabb, mint a regi: a kesz oldal fele-fele lenne, es az');
    ki('   nem latszik meg a szamokon. Nezd meg a fenti sorokat, es futtasd ujra.');
    exit;
}

$mentes = $MENTES_DIR.'/landing-szoveg-mentes-'.$CEL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit; }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

/* A prod alakja szerint kodolunk: JSON_UNESCAPED_UNICODE NELKUL. */
$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit; }
update_post_meta($CEL, '_elementor_data', wp_slash($uj));
delete_post_meta($CEL, '_elementor_css');
delete_post_meta($CEL, '_elementor_page_assets');

ki('');
ki('VISSZAMERES -- MEZONKENT, nem byte-azonossagra:');
$vissza = get_post_meta($CEL, '_elementor_data', true);
$faVissza = json_decode($vissza, true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    if (empty($par['csere'])) { continue; }
    $e =& km_elem($faVissza, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; }
    else {
        $rossz++;
        ki(sprintf('  !! [%s] %s NEM az uj erteket adja vissza', $par['elem_id'], $par['ut']));
    }
}
ki(sprintf('  %d/%d mezo a VART uj erteket adja vissza.', $ok, $ok + $rossz));
ki('  _elementor_css eldobva: '.(get_post_meta($CEL,'_elementor_css',true) === '' ? 'igen' : '!! MEGVAN'));
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
