#!/usr/bin/env python3
"""17544 (/ingyenes-kihivas/, Egeszseges reggeli 2026.10): a JAVITOTT szoveg bevitele.

MIT CSINAL: Copy leadott markdownjabol KIOLVASSA az uj szovegeket (nem en gepelem ujra),
osszeparositja oket a 17544 Elementor-elem-azonositoival, kiirja a parositast JSON-be, es
generalja a prodon futtathato PHP-t.

>>> A `jelenlegi` HORGONYOK MERVE VANNAK, NEM FELTETELEZVE (Bit, 2026-09-21): az elo
>>> oldal DOM-jabol olvastam ki mind a 17 mezo aktualis erteket (playwright, data-id
>>> szerint). Ezert a horgony nem a korabbi generalt szkript `uj` oszlopa -- az csak azt
>>> mondana meg, mit AKARTUNK odairni, nem azt, mi ALL ott ma.

>>> ES EZERT ROVID A HORGONY: a WordPress `wptexturize` a MEGJELENITESKOR alakit at
>>> karaktereket -- a tarolt " - " az elo oldalon " – " (nagykotojel). Ha a teljes
>>> rendereltszoveget hasznalnam horgonynak, a PHP-oldali osszevetes (ami a TAROLT
>>> erteket nezi) minden ilyen mezot "elcsuszott"-nak minositene, es a szkript nem irna.
>>> A horgony ezert texturizalatlan reszlet: nincs benne kotojel, idezojel, harompont.

FUTTATAS:
  python3 scripts/landing-17544-generator.py
"""
import io, json, os, re

COPY_MD = ('/Users/macmini/marveen/agents/copy/workspace/landing/'
           'ingyenes-kihivas-2026-10-reggeli/landing-2026-10-reggeli-JAVITOTT.md')
KI_JSON = '/Users/macmini/marveen/scripts/landing-17544-parositas.json'
KI_PHP = '/Users/macmini/marveen/scripts/landing-17544-szoveg-csere.php'

# elem_id -> (ut, horgony)  A horgony a 2026-09-21-en az ELO oldalrol mert ertek prefixe.
HORGONY = {
    ('b3e8629', 'editor'): 'Csatlakozz a kihíváshoz, és rakjuk össze együtt azt a reggelit',
    ('370bdfea', 'editor'): 'Reggel kapkodsz, és a végén marad a kávé meg valami gyors édesség',
    ('17c1f49', 'editor'): 'A 7 napos egészséges reggeli kihívás alatt minden nap kapsz egy receptet',
    ('c927586', 'editor'): 'Az egészséges reggeli abban segít, hogy ne a nap legrosszabb döntésével',
    ('be0d9b5', 'editor'): 'Remélem, a hét végére Te is úgy nézel majd erre a hétre',
    ('360da42', 'icon_list.0.text'): 'kitarthat a jóllakottság délig, és elmaradhat a délelőtti éhségroham',
    ('360da42', 'icon_list.1.text'): 'milyen egyszerű sósan indítani a napot',
    ('360da42', 'icon_list.2.text'): 'néhány perc is elég lehet egy laktató reggelihez',
    ('360da42', 'icon_list.3.text'): 'mennyivel nyugodtabb egy reggel, ha nem kell kitalálni, mi legyen',
    ('bb2a697', 'icon_list.0.text'): 'reggelente kapkodsz, és a végén marad a kávé meg valami gyors édesség',
    ('bb2a697', 'icon_list.1.text'): 'délelőtt tízkor már a keksz után nyúlsz, pedig reggeliztél',
    ('bb2a697', 'icon_list.2.text'): 'unod a megszokott reggeliket, és nem jut eszedbe semmi új',
    ('bb2a697', 'icon_list.3.text'): 'szeretnél egészségesebben reggelizni, de reggel nincs időd főzni',
    ('bb2a697', 'icon_list.4.text'): 'kezdő életmódváltó vagy, és valami egyszerűvel kezdenél',
    ('bb2a697', 'icon_list.5.text'): 'gluténmentesen vagy tejmentesen étkezel, és elfogytak az ötleteid',
    ('bb2a697', 'icon_list.6.text'): 'munka és család mellett jól jönne egy kis segítség a reggelekhez',
    ('bb2a697', 'icon_list.7.text'): 'vagy egyszerűen kíváncsi vagy, mitől lesz laktató egy reggeli.',
}


def szekciok(szoveg):
    """A '## (x) ...' fejlecek szerint darabol. Ertek: a fejlec alatti nyers torzs."""
    ki, akt, buf = {}, None, []
    for sor in szoveg.split('\n'):
        m = re.match(r'^##\s+\(([a-f])\)', sor)
        if m:
            if akt:
                ki[akt] = '\n'.join(buf).strip('\n')
            akt, buf = m.group(1), []
            continue
        if akt is not None:
            buf.append(sor)
    if akt:
        ki[akt] = '\n'.join(buf).strip('\n')
    return ki


def alszekcio(torzs, cim):
    """Egy '### <cim>' alatti blokk, a kovetkezo '###'-ig."""
    m = re.search(r'^###\s+' + re.escape(cim) + r'\s*$(.*?)(?=^###\s|\Z)',
                  torzs, re.M | re.S)
    return None if not m else m.group(1).strip('\n')


def bekezdes_lista(blokk):
    return [b.strip() for b in re.split(r'\n\s*\n', blokk) if b.strip()]


def html_bekezdesek(blokk):
    """Bekezdesenkent <p>. A text-editor widget a tarolt erteket NYERSEN adja ki: ami
    nincs tagbe teve, az egyetlen folyo szovegge olvad ossze."""
    return ''.join('<p>' + h(b) + '</p>' for b in bekezdes_lista(blokk))


def html_hero(blokk):
    """Hero: elso bekezdes <p>, a maradek sorok <ul><li>. A 2026.08-as landing (16884)
    pontosan ezt az alakot hordozza ugyanezen az elem-azonositon."""
    r = bekezdes_lista(blokk)
    if len(r) != 2:
        raise SystemExit(f'HIBA: a hero {len(r)} blokkos, 2-t vartam (bevezeto + lista).')
    tetelek = [s.strip() for s in r[1].split('\n') if s.strip()]
    if len(tetelek) != 4:
        raise SystemExit(f'HIBA: a hero listaja {len(tetelek)} soros, nem 4.')
    return ('<p>' + h(r[0]) + '</p><ul>'
            + ''.join('<li>' + h(t) + '</li>' for t in tetelek) + '</ul>')


def h(s):
    """Csak a szerkezeti karaktereket entitasozzuk -- ekezetet, irasjelet nem."""
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def sorok(blokk):
    return [s.strip() for s in blokk.split('\n') if s.strip()]


def main():
    if not os.path.exists(COPY_MD):
        raise SystemExit(f'HIBA: nincs meg Copy fajlja: {COPY_MD}')
    sz = szekciok(io.open(COPY_MD, encoding='utf-8').read())
    hianyzo = [k for k in 'abcdef' if k not in sz]
    if hianyzo:
        raise SystemExit(f'HIBA: Copy fajljabol hianyzik: {", ".join(hianyzo)}')

    parok = []

    def fel(elem_id, ut, uj):
        hg = HORGONY.get((elem_id, ut))
        if hg is None:
            raise SystemExit(f'HIBA: nincs mert horgony ehhez: {elem_id} {ut}')
        if not uj or not uj.strip():
            raise SystemExit(f'HIBA: ures uj ertek: {elem_id} {ut}')
        parok.append({'elem_id': elem_id, 'ut': ut, 'horgony': hg, 'uj': uj,
                      'valtozik': re.sub(r'<[^>]+>', ' ', uj).strip() != hg.strip()})

    # (b) hero: bevezeto + negysoros lista, egyben
    fel('b3e8629', 'editor', html_hero(sz['b']))
    # (a) 2. szekcio torzse  (a CIM valtozatlan, ezert nincs benne a parositasban)
    fel('370bdfea', 'editor', html_bekezdesek(alszekcio(sz['a'], 'Törzs')))
    # (c) "Mire szamithatsz?" torzse
    fel('17c1f49', 'editor', html_bekezdesek(sz['c']))
    # (d) "Mit kapsz meg?" bevezeto + negy ikonos pont
    fel('c927586', 'editor', html_bekezdesek(alszekcio(sz['d'], 'Bevezető')))
    negy = sorok(alszekcio(sz['d'], 'A négy pont'))
    if len(negy) != 4:
        raise SystemExit(f'HIBA: a "negy pont" {len(negy)} soros, nem 4.')
    for i, s in enumerate(negy):
        fel('360da42', f'icon_list.{i}.text', s)
    # (e) "Imadni fogod" nyolc pontja
    nyolc = sorok(sz['e'])
    if len(nyolc) != 8:
        raise SystemExit(f'HIBA: az "Imadni fogod" {len(nyolc)} pontos, nem 8.')
    for i, s in enumerate(nyolc):
        fel('bb2a697', f'icon_list.{i}.text', s)
    # (f) zaro vagykep
    fel('be0d9b5', 'editor', html_bekezdesek(sz['f']))

    if len(parok) != len(HORGONY):
        raise SystemExit(f'HIBA: {len(parok)} par keszult, {len(HORGONY)} horgonyhoz.')

    # ONELLENORZES, ami a kapu sajat leleteire nez: a bevitt szoveg ne hozza vissza
    # azt, amit epp javitunk. Nem velemeny, hanem szamlalas.
    egyben = re.sub(r'<[^>]+>', ' ', '\n'.join(p['uj'] for p in parok))
    bajok = []
    if '–' in egyben or '—' in egyben:
        bajok.append('nagykotojel van az UJ szovegben')
    for szo in ['vércukor', 'inzulin', 'hormon', 'anyagcsere', 'glikémiás',
                'ketózis', 'gyulladás', 'immunrendszer']:
        if szo in egyben:
            bajok.append(f'elettani szokincs az UJ szovegben: {szo}')
    if 'állítottam össze' in egyben:
        bajok.append("'allitottam ossze' az UJ szovegben")
    imadni = [p['uj'] for p in parok if p['elem_id'] == 'bb2a697']  # ezek tag nelkuliek
    vesszos = sum(1 for x in imadni if x.endswith(','))
    if vesszos < 7:
        bajok.append(f'az "Imadni fogod" 8 pontjabol csak {vesszos} vesszos')
    if bajok:
        raise SystemExit('HIBA -- a bevitel a sajat kapunk leleteit hozna vissza:\n  - '
                         + '\n  - '.join(bajok))

    json.dump(parok, io.open(KI_JSON, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    io.open(KI_PHP, 'w', encoding='utf-8').write(FEJ + '\n$PAROK = ' + php_tomb(parok) + ';\n' + TORZS)
    valtozik = sum(1 for p in parok if p['valtozik'])
    print(f'@@ {len(parok)} mezo ({valtozik} valtozik, {len(parok)-valtozik} valtozatlan) -> {KI_PHP}')
    print(f'@@ parositas: {KI_JSON}')


FEJ = r'''<?php
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
'''

TORZS = r'''
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

/* LITESPEED-URITES. Enelkul a kovetkezo lekeres a REGI oldalt adja vissza, es a
   visszameres a valtozas HIANYAT merne -- ami pont ugy nez ki, mint egy elbukott iras. */
if (has_action('litespeed_purge_post')) {
    do_action('litespeed_purge_post', $CEL); ki('litespeed_purge_post: kiadva');
} else {
    ki('litespeed_purge_post: NINCS ilyen action -- a lap-cache-t kezzel kell uriteni.');
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
ki('  _elementor_css eldobva: '.(get_post_meta($CEL,'_elementor_css',true) === '' ? 'igen' : '!! MEGVAN'));
ki('');
ki($rossz === 0 ? 'ELES MENET VEGE. Minden mezo a vart erteket adja.'
                : '!! ELES MENET VEGE, DE VOLT ELTERES -- olvasd vissza a fentit.');
exit($rossz === 0 ? 0 : 1);
'''


def php_tomb(sorok):
    def q(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"
    reszek = []
    for s in sorok:
        reszek.append('  array(' + ', '.join(
            f'{q(k)} => ' + (('true' if v else 'false') if isinstance(v, bool) else q(v))
            for k, v in s.items()) + ')')
    return 'array(\n' + ',\n'.join(reszek) + '\n)'


if __name__ == '__main__':
    main()
