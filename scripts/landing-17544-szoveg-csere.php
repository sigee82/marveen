<?php
/**
 * 17544 -- /ingyenes-kihivas/ (Egeszseges reggeli 2026.10): A JAVITOTT SZOVEG BEVITELE.
 * GENERALT FAJL -- ne kezzel szerkeszd, hanem a scripts/landing-17544-generator.py-t
 * futtasd ujra. A szoveg forrasa Copy leadott markdownja, a szkript olvassa ki belole.
 *
 *   (alapertelmezes)          SZARAZ: semmit nem ir, csak megmutatja, mi tortenne
 *   --apply --oldal=17544     ELES: a MEGADOTT oldalra irja be a szoveget
 *
 * A 17153 (a REGI, elo meal-prep landing) MEG VAN TAGADVA. Az `--oldal` az eles menetben
 * kotelezo: ezen a peldanyon tobb landing is ugyanezeket az elem-azonositokat hordozza
 * (duplikalt oldalak), tehat egy elfelejtett `--oldal` NEM ures futast adna, hanem a
 * ROSSZ oldalt irna at.
 *
 * MIERT PREFIX-EGYEZES ES NEM TELJES: a horgony a tarolt ertek eleje, szandekosan olyan
 * reszlet, amit a `wptexturize` nem alakit at (nincs benne kotojel, idezojel, harompont).
 * A teljes rendereltszoveghez hasonlitani hibas lenne: a tarolt " - " az elo oldalon
 * " – " alakban jelenik meg, es minden ilyen mezo "elcsuszott"-nak latszana.
 *
 * MIERT MEZO-SZINTU A VISSZAMERES: a `_elementor_data`-t ujra kell kodolni, es a kodolas
 * ALAKJA valtozhat. Az Elementornak ez mindegy (dekodolva ugyanaz), de egy byte-osszevetes
 * "az egesz oldal megvaltozott"-at mutatna. A kodolas JSON_UNESCAPED_UNICODE NELKUL megy,
 * mert a prod igy tarolja.
 *
 * FORRAS: landing-2026-10-reggeli-JAVITOTT.md  md5=968e3f099cc5d7ffba6ce4c3d2f89466  mtime=2026-09-21 13:16:25
 * MERT ELO ALLAPOT: 2026-09-21T11:27:22Z
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
$TILTOTT = 17153;
$MENTES_DIR = '/home/napalatt/vip.21napalatt.hu';

$PAROK = array(
  array('elem_id' => 'b3e8629', 'ut' => 'editor', 'horgony' => 'Csatlakozz a kihíváshoz, és készíts velünk hét laktató reggelit egyszerű', 'uj' => '<p>Csatlakozz a kihíváshoz, és készíts velünk hét laktató reggelit egyszerű alapanyagokból! Olyanokat, amik délig is kitarthatnak.</p><ul><li>7 laktató reggeli</li><li>heti bevásárlólista</li><li>könnyen elkészíthető receptek</li><li>iOS és Android applikáció</li></ul>', 'valtozik' => false),
  array('elem_id' => '6c78b0f2', 'ut' => 'title', 'horgony' => 'Reggelizz úgy, hogy délig kitartson', 'uj' => 'Reggelizz úgy, hogy délig kitartson', 'valtozik' => false),
  array('elem_id' => '370bdfea', 'ut' => 'editor', 'horgony' => 'Reggel kapkodsz, és a végén marad a kávé meg valami gyors édesség. Ismerős?', 'uj' => '<p>Reggel kapkodsz, és a végén marad a kávé meg valami gyors édesség. Ismerős? Aztán tíz óra körül megjön az éhség, és már a keksz után nyúlsz, pedig reggeliztél.</p><p>Nem a jó recept hiányzik. Reggel van a legkevesebb időd, és pont olyankor a legnehezebb kitalálni, mi kerüljön az asztalra.</p><p>Az egészséges reggeli kihívás segít megismerni, mitől lesz egy reggeli igazán laktató, és hogyan kerülheted el, hogy tíz óra körül újra rád törjön az éhség. A kihívásban 7 különböző receptet készítünk el, és pontos bevásárlólistát is kapsz, így nem neked kell kitalálni, mit egyél reggel, egyszerűen csak készítsd el és élvezd.</p><p>És nem kell felforgatnod a reggeleidet! Nem az a cél, hogy holnaptól mindent másképp csinálj, hanem hogy egy hét alatt kipróbálj hét reggelit, és kiderüljön, melyik az a kettő-három, ami tényleg belefér a Te hétköznapodba.</p>', 'valtozik' => false),
  array('elem_id' => '17c1f49', 'ut' => 'editor', 'horgony' => 'Minden reggel ott vár egy recept, és hozzá a heti bevásárlólista, hogy ne a', 'uj' => '<p>Minden reggel ott vár egy recept, és hozzá a heti bevásárlólista, hogy ne a hűtő előtt állva kelljen döntened. Hét reggelit próbálunk ki egy hét alatt, és mindet úgy raktuk össze, hogy segítsen egyensúlyban tartani a vércukrodat.</p><p>A recepteket úgy válogattam össze, hogy IR-barátok, táplálóak és reggel is reálisan elkészíthetőek legyenek. A hozzávalókat a piacokon, boltok polcain könnyen megtalálod. Nem kell hozzájuk különleges konyhai tudás, és nem kell semmilyen speciális eszköz sem. Mindegyik sós, gluténmentes, tejmentes, és nincs bennük hozzáadott cukor.</p><p>A kihívás teljesítésével egy csapásra két legyet is üthetsz: a 7. nap végén megveregetheted a válladat, hogy teljesítetted a tervet. De ami fontosabb, elindulhatsz az úton egy új, egészséges szokás kialakításához, amelyet csak folytatnod kell.</p><p>A kihívás végére lesz 7 új recepted, amit később bármikor elővehetsz, amikor reggel nem jut eszedbe semmi.</p>', 'valtozik' => false),
  array('elem_id' => '9a135ee', 'ut' => 'title', 'horgony' => 'Mi változhat a reggeleidben?', 'uj' => 'Mi változhat a reggeleidben?', 'valtozik' => false),
  array('elem_id' => 'c927586', 'ut' => 'editor', 'horgony' => 'Ebben a hétben nem kell reggelente kapkodva döntened. Reggelre ott a terv,', 'uj' => '<p>Ebben a hétben nem kell reggelente kapkodva döntened. Reggelre ott a terv, neked már csak elő kell venned.</p><p>A kihívás alatt megtapasztalhatod, hogy</p>', 'valtozik' => false),
  array('elem_id' => '360da42', 'ut' => 'icon_list.0.text', 'horgony' => 'kitarthat a jóllakottság délig, és elmaradhat a délelőtti éhségroham', 'uj' => 'kitarthat a jóllakottság délig, és elmaradhat a délelőtti éhségroham', 'valtozik' => false),
  array('elem_id' => '360da42', 'ut' => 'icon_list.1.text', 'horgony' => 'milyen egyszerű sósan indítani a napot', 'uj' => 'milyen egyszerű sósan indítani a napot', 'valtozik' => false),
  array('elem_id' => '360da42', 'ut' => 'icon_list.2.text', 'horgony' => 'negyedóra alatt is összeáll egy laktató reggeli', 'uj' => 'negyedóra alatt is összeáll egy laktató reggeli', 'valtozik' => false),
  array('elem_id' => '360da42', 'ut' => 'icon_list.3.text', 'horgony' => 'mennyivel nyugodtabb egy reggel, ha már kész a terv', 'uj' => 'mennyivel nyugodtabb egy reggel, ha már kész a terv', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.0.text', 'horgony' => 'reggelente kapkodsz, és a végén marad a kávé meg valami gyors édesség,', 'uj' => 'reggelente kapkodsz, és a végén marad a kávé meg valami gyors édesség,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.1.text', 'horgony' => 'délelőtt tízkor már a keksz után nyúlsz, pedig reggeliztél,', 'uj' => 'délelőtt tízkor már a keksz után nyúlsz, pedig reggeliztél,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.2.text', 'horgony' => 'unod a megszokott reggeliket, és nem jut eszedbe semmi új,', 'uj' => 'unod a megszokott reggeliket, és nem jut eszedbe semmi új,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.3.text', 'horgony' => 'szeretnél egészségesebben reggelizni, de reggel nincs időd főzni,', 'uj' => 'szeretnél egészségesebben reggelizni, de reggel nincs időd főzni,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.4.text', 'horgony' => 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél,', 'uj' => 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.5.text', 'horgony' => 'gluténmentesen vagy tejmentesen étkezel, és elfogytak az ötleteid,', 'uj' => 'gluténmentesen vagy tejmentesen étkezel, és elfogytak az ötleteid,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.6.text', 'horgony' => 'munka és család mellett jól jönne egy kis segítség a reggelekhez,', 'uj' => 'munka és család mellett jól jönne egy kis segítség a reggelekhez,', 'valtozik' => false),
  array('elem_id' => 'bb2a697', 'ut' => 'icon_list.7.text', 'horgony' => 'vagy egyszerűen kíváncsi vagy, hogy mitől lesz laktató egy reggeli.', 'uj' => 'vagy egyszerűen kíváncsi vagy, hogy mitől lesz laktató egy reggeli.', 'valtozik' => false),
  array('elem_id' => 'be0d9b5', 'ut' => 'editor', 'horgony' => 'Remélem, a hét végére Te is úgy nézel majd a reggeli asztalon álló tányérodra,', 'uj' => '<p>Remélem, a hét végére Te is úgy nézel majd a reggeli asztalon álló tányérodra, hogy ezt miért nem csináltam eddig?</p>', 'valtozik' => false)
);

ki('LANDING 17544 SZOVEG-CSERE  '.gmdate('c').' UTC   DB='.DB_NAME);
ki($APPLY ? '*** ELES MENET: IRNI FOG ***' : 'SZARAZ MENET: semmit nem ir');

if ($OLDAL === $TILTOTT) {
    ki('!! A megadott oldal a REGI meal-prep landing ('.$TILTOTT.') -- NEM irunk ra.');
    exit(2);
}
if ($OLDAL <= 0) { ki('!! KOTELEZO a --oldal=<ID>, szarazon is. Nem talalgatok.'); exit(2); }
$CEL = $OLDAL;
$p = get_post($CEL);
if (!$p) { ki('!! a '.$CEL.' nem letezik ezen a peldanyon.'); exit(2); }
ki('celpont: '.$CEL.'  slug='.$p->post_name.'  status='.$p->post_status);
ki('');

$d = get_post_meta($CEL, '_elementor_data', true);
if (!is_string($d) || $d === '') { ki('!! nincs _elementor_data a '.$CEL.'-on'); exit(2); }
$fa = json_decode($d, true);
if (!is_array($fa)) { ki('!! a JSON nem dekodolhato: '.json_last_error_msg()); exit(2); }

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
    /* A blokk-tagek HATART jelentenek: nelkuluk a "</p><p>" hatarbol "…vegeEleje…" lesz,
       es a jelentes olvashatatlan. A horgony-osszevetest ez nem billenti el: a MAI ertekek
       tag-mentesek (2026-09-21-en megmerve: a 13 text-editor widgetbol 9 nulla tagot hordoz). */
    $s = preg_replace('#<(/p|/li|br\s*/?|/h[1-6])\s*>#i', ' ', $s);
    return trim(preg_replace('/\s+/u', ' ', wp_strip_all_tags($s)));
}

$rendben = 0; $hiba = 0; $valtozik = 0;
foreach ($PAROK as $par) {
    $elem =& km_elem($fa, $par['elem_id']);
    if ($elem === null) {
        ki(sprintf('  !! [%s] NINCS ILYEN ELEM az oldalon', $par['elem_id'])); $hiba++; continue;
    }
    $most = km_ut_ertek($elem['settings'], $par['ut']);
    if ($most === null) {
        ki(sprintf('  !! [%s] nincs ilyen mezo: %s', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $mostT = km_tiszta($most);
    $horgony = km_tiszta($par['horgony']);
    if (mb_substr($mostT, 0, mb_strlen($horgony)) !== $horgony) {
        ki(sprintf('  !! [%s] %s: a JELENLEGI ertek nem a mert horgonnyal kezdodik -- KIHAGYVA',
            $par['elem_id'], $par['ut']));
        ki(sprintf('        most:    %s', mb_substr($mostT, 0, 90)));
        ki(sprintf('        horgony: %s', mb_substr($horgony, 0, 90)));
        $hiba++; continue;
    }
    $azonos = (km_tiszta($par['uj']) === $mostT);
    if (!$azonos) { $valtozik++; }
    ki(sprintf('  [%s] %s %s', $par['elem_id'], $par['ut'], $azonos ? '(valtozatlan)' : ''));
    if (!$azonos) {
        ki(sprintf('        regi: %s', mb_substr($mostT, 0, 90)));
        ki(sprintf('        uj:   %s', mb_substr(km_tiszta($par['uj']), 0, 90)));
    }
    if ($APPLY && !km_ut_ir($elem['settings'], $par['ut'], $par['uj'])) {
        ki(sprintf('  !! [%s] %s: az iras nem sikerult', $par['elem_id'], $par['ut'])); $hiba++; continue;
    }
    $rendben++;
}

ki('');
ki(sprintf('MEZO: %d rendben, %d hiba/kihagyva  (ebbol %d valtozik, %d mar most is egyezik)',
    $rendben, $hiba, $valtozik, $rendben - $valtozik));

if (!$APPLY) { ki(''); ki('SZARAZ MENET VEGE. Semmit nem irtunk.'); exit($hiba > 0 ? 1 : 0); }
if ($hiba > 0) {
    ki('');
    ki('!! VOLT LEGALABB EGY KIHAGYOTT MEZO -- NEM IRUNK AZ OLDALRA.');
    ki('   Reszleges szoveg rosszabb, mint a regi: a kesz oldal fele-fele lenne, es az');
    ki('   nem latszik meg a szamokon. Nezd meg a fenti sorokat, es futtasd ujra.');
    exit(1);
}

$mentes = $MENTES_DIR.'/landing-szoveg-mentes-'.$CEL.'-'.gmdate('Ymd-His').'.txt';
if (file_put_contents($mentes, $d) === false) { ki('!! A MENTES NEM SIKERULT -- NEM IRUNK.'); exit(1); }
ki('mentes: '.$mentes.' ('.strlen($d).' byte)');

$uj = wp_json_encode($fa, JSON_UNESCAPED_SLASHES);
if (!is_string($uj)) { ki('!! a JSON ujrakodolasa elbukott -- NEM IRUNK.'); exit(1); }
update_post_meta($CEL, '_elementor_data', wp_slash($uj));
delete_post_meta($CEL, '_elementor_css');
delete_post_meta($CEL, '_elementor_page_assets');
/* A NEGYEDIK RETEG, es Nova merte meg 2026-09-21-en: a szkript visszameresé ZOLD volt, a
   `litespeed_purge_post` KIADVA, es a lap MEGIS a regit adta -- cache-kerulo query-vel is.
   A tarolt `_elementor_data` ekozben mar az ujat hordozta, tehat NEM az iras bukott, hanem a
   KISZOLGALAS. A hianyzo meta az `_elementor_element_cache`: ez a RENDERELT HTML cache-e.
   Ujragenralodik, a torlese biztonsagos.
   ES EZ A LEGROSSZABB ALAKBAN JELENTKEZIK: minden nyugta zold, es a lap valtozatlan --
   vagyis pont ugy nez ki, mint egy elbukott iras, es oda kuldi a keresest, ahol nincs semmi. */
delete_post_meta($CEL, '_elementor_element_cache');
clean_post_cache($CEL);
/* MIERT MEGY A PURGE_ALL IS, pedig durvabb: Nova a retegeket EGYSZERRE uritette, tehat hogy
   melyik oldotta meg, az NINCS izolalva. Egy szukebb reszhalmaz ezert tipp lenne; ez a sor
   azt csinalja, amirol MERES van. A szkript evente parszor fut: egy ujraepulo cache olcsobb,
   mint egy landing, ami az inditas napjan valtozatlannak latszik.
   ES A HOROG LETEZIK, nem remeny: a kihelyezett LiteSpeed 7.5.0.1 `src/api.cls.php` `init()`-je
   a 110. es 111. soran regisztralja a `litespeed_purge_all`-t ES a `litespeed_purge_post`-ot,
   egymas mellett, feltétel nelkul. A `purge_post` agat 2026-09-21-en HAROM eles futas kiirta
   ("kiadva"), ami csak a has_action IGAZ againal tortenhet -- tehat az `init()` lefutott, es
   vele a szomszedos sor is. (A plugint a `prod` agrol olvastam, nem a futo fajlbol.) */
if (has_action('litespeed_purge_post')) {
    do_action('litespeed_purge_post', $CEL); ki('litespeed_purge_post: kiadva');
} else {
    ki('litespeed_purge_post: NINCS ilyen action.');
}
if (has_action('litespeed_purge_all')) {
    do_action('litespeed_purge_all'); ki('litespeed_purge_all: kiadva');
} else {
    ki('litespeed_purge_all: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.');
}

ki('');
ki('VISSZAMERES -- MEZONKENT, nem byte-azonossagra:');
$faVissza = json_decode(get_post_meta($CEL, '_elementor_data', true), true);
$ok = 0; $rossz = 0;
foreach ($PAROK as $par) {
    $e =& km_elem($faVissza, $par['elem_id']);
    $ert = ($e === null) ? null : km_ut_ertek($e['settings'], $par['ut']);
    if ($ert === $par['uj']) { $ok++; }
    else { $rossz++; ki(sprintf('  !! [%s] %s NEM az uj erteket adja vissza', $par['elem_id'], $par['ut'])); }
}
ki(sprintf('  %d/%d mezo a VART uj erteket adja vissza.', $ok, $ok + $rossz));
foreach (array('_elementor_css', '_elementor_page_assets', '_elementor_element_cache') as $mk) {
    ki('  '.$mk.' eldobva: '.(get_post_meta($CEL, $mk, true) === '' ? 'igen' : '!! MEGVAN'));
}
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
exit($rossz === 0 ? 0 : 1);
