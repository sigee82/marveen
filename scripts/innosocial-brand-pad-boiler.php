<?php
/* MI TUNIK EL A SZURESBEN? A kozos sorokat KET ablakmerettel szamolja ki (4000 = regi sorrend,
   60000 = uj), es kiirja, amit CSAK az uj dob el. Read-only, modellt nem hiv. */
define('INNOSOCIAL_AUTOFILL_LIB_MODE', true);
$IS = $argv[1]; $url = $argv[2];
chdir($IS);
require_once $IS . '/innosocial_brand_autofill.php';

function norm(string $s): string { return trim(preg_replace('/\s+/u', ' ', mb_strtolower($s))); }
function kozos(array $texts, float $share, int $minPages): array {
    $seen = [];
    foreach ($texts as $t) {
        foreach (array_unique(array_map('norm', preg_split("/\n/", $t) ?: [])) as $n) {
            if ($n === '') continue; $seen[$n] = ($seen[$n] ?? 0) + 1;
        }
    }
    $th = max($minPages, (int) ceil(count($texts) * $share));
    return array_filter($seen, fn($c) => $c >= $th);
}

$disc = InnoSocialBrandSiteReader::discover($url);
$urls = array_slice($disc['urls'] ?? [], 0, 10);
$regi = []; $uj = [];
foreach ($urls as $u) {
    $a = InnoSocialBrandSiteReader::fetch($u, 4000);
    $b = InnoSocialBrandSiteReader::fetch($u, 60000);
    if (!empty($a['ok'])) $regi[] = $a['content'];
    if (!empty($b['ok'])) $uj[] = $b['content'];
}
$kr = kozos($regi, 0.6, 3); $ku = kozos($uj, 0.6, 3);
$csakUj = array_diff_key($ku, $kr);
arsort($csakUj);
echo "$url -- oldal: ", count($uj), " | kozos sor regi ablakkal: ", count($kr), " | ujjal: ", count($ku),
     " | CSAK az ujban: ", count($csakUj), "\n";
$i = 0;
foreach ($csakUj as $sor => $db) {
    printf("  [%2d oldalon] %s\n", $db, mb_substr($sor, 0, 100));
    if (++$i >= 25) break;
}
