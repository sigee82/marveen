<?php
/**
 * 2026-11 INGYENES-KIHIVAS LANDING: A SZOVEG BEVITELE.
 * GENERALT FAJL -- ne kezzel szerkeszd: scripts/landing-honap-generator.py.
 * FORRAS: landing-doksi-rev734.md  md5=d970a85d57fdea6058b51af8da2af08a  mtime=2026-10-15 11:00:15
 * MERT ELO ALLAPOT: 2026-10-14T13:08:30.436Z
 *
 *   --site=dev --oldal=<ID>|jelolt                SZARAZ a deven (semmit nem ir)
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
 * HORGONY: a CSERE-mezok horgonya a mar lefutott korok szovege: elozo-parositas-20261014-1602.json -> landing-2026-11-parositas.json
 * $TOROL: ha a doksi listaja rovidebb, mint az oldale, a felesleges elemek a lista VEGEROL torlodnek --
 * csak ha a lista a mert elemszamu, a torlendo szovege a horgony, es minden elem ikonja egyforma.
 *
 * PROBAPAD: LANDING_CSERE_PROBAPAD=1 + --wp=<gyoker> -- CSAK a hoszt-ellenorzest kapcsolja ki.
 * A cel-orok (tiltott ID, dev-jelolo, prod draft+ideiglenes slug, --yes-prod) probapadon is
 * elnek: azokat pont ott kell tudni kiprobalni, ahol eles iras nem tortenhet.
 */
if (PHP_SAPI !== 'cli') { exit("Csak CLI-bol.\n"); }
define('WP_USE_THEMES', false);
$HONAP = '2026-11';
$FORRAS_ID = 17544;
$UJ_CIM = '7 napos ingyenes kihívás - Pihentető alvás 2026.11';
$TILTOTT = array(17544, 17153);
$PROD_IDEIGLENES = 'novemberi-kihivas-eloke';
$PAROK = array(
  array('elem_id' => '6c78b0f2', 'ut' => 'title', 'horgony' => 'Készülj úgy az estére, hogy könnyebben elaludj', 'uj' => 'Készülj tudatosan az estére a pihentető alvásért', 'cimke' => '2. szekció -- Ígéret-cím + a jelenet / Heading'),
  array('elem_id' => '370bdfea', 'ut' => 'editor', 'horgony' => 'Este fáradtan esel ágyba, de csak forgolódsz és nem tudsz aludni? Vagy elalszol', 'uj' => '<p>Este fáradtan esel ágyba, de csak forgolódsz és nem tudsz aludni? Vagy elalszol ugyan, de hajnalban felébredsz, és órákig nem tudsz visszaaludni és csak számolod a perceket az ébresztő csörgéséig? Reggel gyakran ébredsz úgy, mintha egész éjjel nem is aludtál volna.</p><p>Képzeld el, milyen jó lenne, ha este nem forgolódnál órákig, hanem egyszer csak elnyomna az álom, és reggel kipihenten, jókedvvel kelnél fel!</p><p>A pihentető alvás kihívásban egy héten át minden reggel kapsz egy rövid leckét egy egyszerű tippel, és mellé egy könnyű vacsorareceptet, így az sem stresszel esténként, hogy mi legyen a vacsora.</p><p>Nem kell felforgatnod az életed, és nem kerül több feladat a listádra. Olyan bevált életmódtippeket mutatunk, amelyek könnyen beleférnek a napodba, és talán már az első estéken érzed, mennyivel nyugodtabban hajtod le a fejed a párnára.</p>', 'cimke' => '2. szekció -- Ígéret-cím + a jelenet / Text-editor'),
  array('elem_id' => '8c97ba3', 'ut' => 'editor', 'horgony' => 'Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor', 'uj' => '<p>Brian Tracy gyakorlás törvénye kimondja, hogy ha egy tevékenységet elég sokszor ismételsz, akkor az szokássá válik. A megfelelő önfegyelemmel egy felnőtt embernek tizennégy és huszonegy nap közötti időre van szüksége ahhoz, hogy egy új szokást kialakítson. Ez idő alatt pedig rendszeresen kell ismételni az adott cselekvést. Az ingyenes kihívásban ehhez kapsz egy óriási lökést, és ha tetszik, folytasd tovább!</p><p>Nem az a cél, hogy egyik napról a másikra mindent megváltoztass, hanem az, hogy megtapasztald, milyen egy este, amikor nem kimerülve zuhansz az ágyba, hanem szépen, lépésről lépésre hangolódsz az alvásra.</p><p>A 21napalatt VIP Klubban nem állunk meg 7 napnál, további 14 napig folytatjuk együtt a pihentető esték építését. Ha kedvet kapsz, Téged is sok szeretettel várunk, csatlakozz hozzánk!</p>', 'cimke' => '3. szekció -- Miért éppen 7 nap? / Text-editor'),
  array('elem_id' => '17c1f49', 'ut' => 'editor', 'horgony' => 'Minden reggel ott vár az applikációban egy rövid lecke, és mellé egy könnyű', 'uj' => '<p>Minden reggel ott vár az applikációban egy rövid lecke, és mellé egy könnyű vacsorarecept, a hétre szóló bevásárlólistával együtt. Az egyik estére pedig egy melengető, koffeinmentes esti italt készítünk.</p><p>A recepteket úgy válogattuk össze, hogy könnyűek legyenek, és este ne terheljék meg a gyomrodat. A hozzávalókat a piacokon, boltok polcain könnyen megtalálod. Nem kell hozzájuk különleges konyhai tudás, és nem kell semmilyen speciális eszköz sem. Mindegyik gluténmentes, tejmentes, és 30 perc alatt elkészíthető.</p><p>A kihívás teljesítésével egy csapásra két legyet is üthetsz: a 7. nap végén megveregetheted a válladat, hogy teljesítetted a tervet. De ami fontosabb, elindulhatsz az úton egy új, egészséges szokás kialakításához, amelyet csak folytatnod kell.</p>', 'cimke' => '4. szekció -- Mire számíthatsz? / Text-editor'),
  array('elem_id' => '9a135ee', 'ut' => 'title', 'horgony' => 'Pihentetőbb éjszakák, kipihentebb reggelek', 'uj' => 'Pihentetőbb éjszakák, energikus reggelek', 'cimke' => '5. szekció -- Pihentetőbb éjszakák, ener / Heading'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.1.text', 'horgony' => 'reggel kipihentebben ébredhetsz', 'uj' => 'reggel kipihentebben, energikusan ébredhetsz', 'cimke' => '5. szekció -- Pihentetőbb éjszakák, ener / Ikonos lista (4 elem) #2'),
  array('elem_id' => '6a0ce87', 'ut' => 'editor', 'horgony' => 'A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan', 'uj' => '<p>A kihívás alatt nem kell semmit sem kihagynod a táplálkozásodból, nyugodtan eheted és ihatod ugyanazokat, amiket korábban is. Hasznos tippekkel gazdagodsz, mit tehetsz napközben a pihentető éjszakáért.</p><p>A kihívás életmódtippeket és recepteket tartalmaz, nem orvosi kezelés. Ha tartósan nehezen alszol, kérd orvos segítségét.</p>', 'cimke' => '5. szekció -- Pihentetőbb éjszakák, ener / Text-editor (a kizárás)'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.0.text', 'horgony' => 'este fáradtan bebújsz az ágyba, de sokszor nehezen tudsz elaludni,', 'uj' => 'este fáradtan bújsz az ágyba, de sokszor nehezen tudsz elaludni,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (7 elem) #1'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.4.text', 'horgony' => 'munka és család mellett este végre a Tiéd az idő, és nehéz lefeküdni,', 'uj' => 'munka, háztartás és család mellett nehezen jut idő önmagadra,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (7 elem) #5'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.5.text', 'horgony' => 'szeretnél könnyű vacsorákat, de este már nincs kedved kitalálni, mi kerüljön az', 'uj' => 'szeretnél könnyű, egészséges vacsorákat enni, de este már nincs kedved kitalálni, mi kerüljön az asztalra,', 'cimke' => '6. szekció -- Imádni fogod a kihívást, h / Ikonos lista (7 elem) #6'),
  array('elem_id' => '1cfd5a8', 'ut' => 'editor', 'horgony' => 'Készíts fotót az elkészült vacsorádról vagy esti italodról. Posztold a kihívás', 'uj' => '<ul><li><strong>Készíts fotót az elkészült vacsorádról vagy esti italodról és oszd meg velünk a kihívás Facebook csoportjában.</strong></li></ul><p>November 8-án a legalább 1 képet feltöltők között kisorsolunk egy szerencsés résztvevőt, aki 1 hónapos 21napalatt VIP Klub előfizetést nyer.</p><p>A 21napalatt VIP Klubtagság teljes hozzáférést ad a VIP Klub minden tartalmához: 21 napos életmódprogramhoz, a hetente frissülő menütervekhez, 600+ tej-, cukor- és gluténmentes recepthez, 21 napos kihívásokhoz, tudásanyagokhoz, a zárt Facebook csoporthoz.</p>', 'cimke' => '11. szekció -- Nyereményjáték (platform: / Text-editor')
);
$MARAD = array(
  array('elem_id' => '6b45d9c', 'ut' => 'title', 'horgony' => 'Indul a 7 napos pihentető alvás kihívás', 'cimke' => 'Heading'),
  array('elem_id' => 'b3e8629', 'ut' => 'editor', 'horgony' => 'Csatlakozz a kihíváshoz, és megmutatjuk, hogyan segíthetsz a szervezetednek', 'cimke' => 'Text-editor (bevezető + felsorolás)'),
  array('elem_id' => 'ed700ab', 'ut' => 'editor', 'horgony' => 'Regisztrálj most, a kihívás teljesen ingyenes. Indulás: 2026. november 1.', 'cimke' => 'Text-editor (a hero alatti sor)'),
  array('elem_id' => '2aec29b', 'ut' => 'text', 'horgony' => 'Én is kipróbálom', 'cimke' => 'Gomb 1'),
  array('elem_id' => '4aa9c3b', 'ut' => 'title', 'horgony' => 'Miért éppen 7 nap?', 'cimke' => 'Heading'),
  array('elem_id' => 'c0f829f', 'ut' => 'text', 'horgony' => 'Már megyek is', 'cimke' => 'Gomb 2'),
  array('elem_id' => '64ff707', 'ut' => 'title', 'horgony' => 'Mire számíthatsz?', 'cimke' => 'Heading'),
  array('elem_id' => 'e2e10c5', 'ut' => 'text', 'horgony' => 'Vágjunk bele, csatlakozom', 'cimke' => 'Gomb 3'),
  array('elem_id' => 'c927586', 'ut' => 'editor', 'horgony' => 'A kihívás alatt megtapasztalhatod, hogy', 'cimke' => 'Text-editor'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.0.text', 'horgony' => 'este könnyebben elalhatsz', 'cimke' => 'Ikonos lista (4 elem) #1'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.2.text', 'horgony' => 'mennyit számít, mikor és mit vacsorázol', 'cimke' => 'Ikonos lista (4 elem) #3'),
  array('elem_id' => '360da42', 'ut' => 'icon_list.3.text', 'horgony' => 'mennyivel nyugodtabb egy este, ha megvan a saját esti rutinod', 'cimke' => 'Ikonos lista (4 elem) #4'),
  array('elem_id' => '2053b90', 'ut' => 'text', 'horgony' => 'Wow, erre rámegyek', 'cimke' => 'Gomb 4'),
  array('elem_id' => '94b920d', 'ut' => 'title', 'horgony' => 'Imádni fogod a kihívást, ha', 'cimke' => 'Heading'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.1.text', 'horgony' => 'hajnalban felébredsz, és nehezen alszol vissza,', 'cimke' => 'Ikonos lista (7 elem) #2'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.2.text', 'horgony' => 'reggel úgy kelsz, mintha nem is aludtál volna,', 'cimke' => 'Ikonos lista (7 elem) #3'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.3.text', 'horgony' => 'lefekvés előtt még a telefont görgeted, amíg várod, hogy elálmosodj,', 'cimke' => 'Ikonos lista (7 elem) #4'),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.6.text', 'horgony' => 'vagy egyszerűen kíváncsi vagy, hogy mi segíthet könnyebben elaludni.', 'cimke' => 'Ikonos lista (7 elem) #7'),
  array('elem_id' => 'be0d9b5', 'ut' => 'editor', 'horgony' => 'Remélem, a hét végére Te is úgy oltod le este az éjjeli lámpát, hogy közben', 'cimke' => 'Text-editor (záró vágykép)'),
  array('elem_id' => '4ac6aea', 'ut' => 'text', 'horgony' => 'Naná, regisztrálok is', 'cimke' => 'Gomb 5'),
  array('elem_id' => 'e2e740b', 'ut' => 'title', 'horgony' => 'A kihívás menete', 'cimke' => 'Heading'),
  array('elem_id' => 'fb7e110', 'ut' => 'title', 'horgony' => 'Regisztrálj a kihívásra', 'cimke' => '7. Heading'),
  array('elem_id' => 'eadbb3d', 'ut' => 'editor', 'horgony' => 'Utána máris be tudsz lépni a kihívás felületére.', 'cimke' => 'Text'),
  array('elem_id' => '1ed9313', 'ut' => 'title', 'horgony' => 'Töltsd le az applikációt', 'cimke' => '8. Heading'),
  array('elem_id' => 'c0ad3ec', 'ut' => 'editor', 'horgony' => 'iOS vagy Android készülékedre és lépj be!', 'cimke' => 'Text'),
  array('elem_id' => 'cd7ec3e', 'ut' => 'title', 'horgony' => 'Keresd a bevásárlólistát', 'cimke' => '9. Heading'),
  array('elem_id' => '84b9598', 'ut' => 'editor', 'horgony' => 'és szerezd be a hozzávalókat!', 'cimke' => 'Text'),
  array('elem_id' => '76c4bce', 'ut' => 'title', 'horgony' => 'Nyerj 1 hónap 21napalatt VIP Klub előfizetést Facebook nyereményjátékunkon', 'cimke' => 'Heading'),
  array('elem_id' => '5b4972b', 'ut' => 'text', 'horgony' => 'Itt a helyem, regisztrálok', 'cimke' => 'Gomb 6'),
  array('elem_id' => '3685e05', 'ut' => 'title', 'horgony' => 'Jelentkezem a 7 napos pihentető alvás kihívásra', 'cimke' => 'Heading')
);
$TOROL = array(

);

$ARGV = $argv ?: array();
$APPLY = in_array('--apply', $ARGV, true);
$YESPROD = in_array('--yes-prod', $ARGV, true);
$SITE = ''; $OLDAL = 0; $WP = '';
foreach ($ARGV as $a) {
    if (strpos($a, '--site=') === 0)  { $SITE = substr($a, 7); }
    if (strpos($a, '--oldal=') === 0) { $OLDAL = substr($a, 8) === 'jelolt' ? -1 : (int) substr($a, 8); }
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
/* --oldal=jelolt: CSAK a deven, es csak ha PONTOSAN EGY atvitt (jelolt) oldal van. Igy a teljes
   dev-menet (export, import, csere) egy SSH-korben futhat, az uj ID elore ismerete nelkul. */
if ($OLDAL === -1) {
    if ($SITE !== 'dev') { ki('!! Az --oldal=jelolt csak a deven ervenyes.'); exit(2); }
    global $wpdb;
    $j = $wpdb->get_col($wpdb->prepare("SELECT p.ID FROM {$wpdb->posts} p JOIN {$wpdb->postmeta} m ON m.post_id=p.ID
        WHERE m.meta_key='_landing_atvitel_forras' AND m.meta_value=%s AND p.post_status NOT IN ('trash','inherit','auto-draft')",
        (string) $FORRAS_ID));
    if (count($j) !== 1) { ki('!! '.count($j).' jelolt oldal van, pontosan egyet vartam. Add meg az ID-t.'); exit(2); }
    $OLDAL = (int) $j[0];
    ki('--oldal=jelolt -> '.$OLDAL);
}
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
/* TORLES A LISTA VEGEROL (a doksi rovidebb listat ad, mint az oldal). Iras elott, szarazon is: a lista
   pontosan a mert elemszamu; a torlendo elem szovege a horgonnyal kezdodik; es a lista MINDEN eleme
   ugyanazt az ikont viseli -- kulonben a vegerol torles egy masik elem ikonjat vinne el. Barmely
   elteres: semmit nem irunk. */
ki('TORLES a lista vegerol ('.count($TOROL).' elem):');
$torolLe = $TOROL;
usort($torolLe, function ($x, $y) { return (int) $y['index'] - (int) $x['index']; });
foreach ($TOROL as $t) {
    $elem =& km_elem($fa, $t['elem_id']);
    $lista = ($elem !== null && isset($elem['settings'][$t['lista']]) && is_array($elem['settings'][$t['lista']])) ? $elem['settings'][$t['lista']] : null;
    unset($elem);
    if ($lista === null) { ki(sprintf('  !! [%s] nincs %s lista', $t['elem_id'], $t['lista'])); $hiba++; continue; }
    if (count($lista) !== (int) $t['vart_db']) { ki(sprintf('  !! [%s] a lista %d elemu, %d-et vartam', $t['elem_id'], count($lista), (int) $t['vart_db'])); $hiba++; continue; }
    $sz = isset($lista[(int) $t['index']]['text']) && is_string($lista[(int) $t['index']]['text']) ? $lista[(int) $t['index']]['text'] : null;
    if ($sz === null || !km_kezdodik($sz, $t['horgony'])) {
        ki(sprintf('  !! [%s] %s.%d: nem a horgony -- most: %s', $t['elem_id'], $t['lista'], (int) $t['index'], $sz === null ? 'NINCS' : mb_substr(km_tiszta($sz), 0, 70)));
        $hiba++; continue;
    }
    $ikon = function ($it) { return wp_json_encode(array(isset($it['selected_icon']) ? $it['selected_icon'] : null, isset($it['icon']) ? $it['icon'] : null)); };
    $elter = 0;
    foreach ($lista as $it) { if ($ikon($it) !== $ikon($lista[0])) { $elter++; } }
    if ($elter > 0) { ki(sprintf('  !! [%s] %d listaelem ikonja elter az elsotol -- a vegerol torles mas ikont vinne el. KIHAGYVA.', $t['elem_id'], $elter)); $hiba++; continue; }
    ki(sprintf('  [%s] %s.%d  -- %s', $t['elem_id'], $t['lista'], (int) $t['index'], $t['cimke']));
    ki('        torlendo: '.mb_substr(km_tiszta($sz), 0, 90).'   (a lista '.count($lista).' elemu, egyforma ikonnal)');
}
if ($APPLY && $hiba === 0) {
    foreach ($torolLe as $t) {
        $elem =& km_elem($fa, $t['elem_id']);
        array_splice($elem['settings'][$t['lista']], (int) $t['index'], 1);
        unset($elem);
    }
}
ki('');
$cimValtozik = ($p->post_title !== $UJ_CIM);
ki('OLDAL CIME: "'.$p->post_title.'"'.($cimValtozik ? '  ->  "'.$UJ_CIM.'"' : '  (mar ez)'));
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

if ($cimValtozik) {
    $r = wp_update_post(array('ID' => $OLDAL, 'post_title' => $UJ_CIM), true);
    ki(is_wp_error($r) ? '!! a cim irasa elbukott: '.$r->get_error_message() : 'cim irva.');
    clean_post_cache($OLDAL);
}
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
$vartDb = array();
foreach ($TOROL as $t) { $k = $t['elem_id'].'|'.$t['lista']; $vartDb[$k] = (isset($vartDb[$k]) ? $vartDb[$k] : (int) $t['vart_db']) - 1; }
foreach ($vartDb as $k => $db) {
    list($eid, $lst) = explode('|', $k);
    $e =& km_elem($faV, $eid);
    $most = ($e !== null && isset($e['settings'][$lst]) && is_array($e['settings'][$lst])) ? count($e['settings'][$lst]) : -1;
    unset($e);
    if ($most === $db) { ki(sprintf('  [%s] %s: %d elem (jo)', $eid, $lst, $most)); } else { $rossz++; ki(sprintf('  !! [%s] %s: %d elem, %d-et vartam', $eid, $lst, $most, $db)); }
}
$cimMost = get_post($OLDAL)->post_title;
if ($cimMost !== $UJ_CIM) { $rossz++; ki('  !! a cim: "'.$cimMost.'"'); } else { ki('  cim: "'.$cimMost.'" (jo)'); }
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($OLDAL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.' : '!! ELES MENET VEGE, DE VOLT ELTERES.');
exit($rossz === 0 ? 0 : 1);
