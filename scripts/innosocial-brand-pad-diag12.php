<?php
/* A TIZENKET HONLAP KINYERES-MERESE -- a VALODI olvasoval. Read-only, nem hiv modellt.
   Hasznalat: php nova_diag12.php <api-konyvtar>   (pl. /home/napalatt/dev.innosocial.hu/api) */
define('INNOSOCIAL_AUTOFILL_LIB_MODE', true);
$IS = $argv[1] ?? '/home/napalatt/app.innosocial.hu/api';
if (!is_dir($IS)) { fwrite(STDERR, "nincs ilyen konyvtar: $IS\n"); exit(2); }
chdir($IS);
require_once $IS . '/innosocial_brand_autofill.php';

$urls = [
  8  => 'https://vip.21napalatt.hu/csatlakozz/',
  14 => 'https://hillside-godollo.hu/',
  22 => 'https://szamelkutyahaz.hu/',
  23 => 'https://www.naturalskin.hu/',
  26 => 'https://www.panoptika.hu/',
  27 => 'https://psiboudyoto.cz/',
  28 => 'https://psiebudy.sk/',
  29 => 'https://hillsidesopron.at/',
  30 => 'https://lakeresort.hu/hu',
  31 => 'https://www.festekbazis.hu/hu/',
  32 => 'https://www.westpannonshop.hu/',
  33 => 'https://perjesioptika.hu/hu/',
  0  => 'https://innogroup.hu/',   // negativ kontroll: NEM mozdulhat el
];
printf("%-4s %-34s %5s %8s %9s  %s\n", 'id', 'url', 'oldal', 'karakter', 'boilerpl', 'bukott okok');
foreach ($urls as $id => $url) {
    try {
        $disc = InnoSocialBrandSiteReader::discover($url);
        $site = InnoSocialBrandSiteReader::readPages($disc['urls'] ?? []);
        $okok = [];
        foreach (($site['failed'] ?? []) as $f) {
            $k = ($f['code'] ?? 'unknown');
            $okok[$k] = ($okok[$k] ?? 0) + 1;
        }
        $okszoveg = '';
        foreach ($okok as $k => $n) $okszoveg .= "$k:$n ";
        printf("%-4s %-34s %5d %8d %9d  %s\n", $id, mb_substr($url, 0, 34),
            count($site['pages'] ?? []), (int) ($site['chars'] ?? 0),
            (int) ($site['boilerplate_lines_removed'] ?? -1), trim($okszoveg));
    } catch (Throwable $e) {
        printf("%-4s %-34s KIVETEL: %s\n", $id, mb_substr($url, 0, 34), mb_substr($e->getMessage(), 0, 70));
    }
}
