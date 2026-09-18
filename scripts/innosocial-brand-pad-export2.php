<?php
/* 2. FAZIS -- az InnoSocial telepitesen fut, mert a SZALLITOTT kod es a modell-kulcs ott van.
 * A SZALLITOTT fuggvenyeket hivja (gather / prompt / parse / buildProposal). A modell-hivast
 * maga vegzi: `callProvider` + `estimateCostUsd`, ugyanazok a fuggvenyek, amiket a vegpont is hiv.
 * Nem ir semmilyen adatbazisba; a kimenet fajl. */
define('INNOSOCIAL_AUTOFILL_LIB_MODE', true);
$IS = '/home/napalatt/app.innosocial.hu/api';
chdir($IS);
require_once $IS . '/innosocial_brand_autofill.php';

$OUT = '/tmp/nova_export_kimenet';
@mkdir($OUT, 0700, true);
$BE = '/tmp/nova_export_bemenet.json';
if (!is_file($BE)) { fwrite(STDERR, "NINCS BEMENET: $BE -- futtasd eloszor a nova_export1.php-t\n"); exit(4); }
$in = json_decode(file_get_contents($BE), true);
if (!is_array($in) || !$in) { fwrite(STDERR, "URES vagy ROMLOTT BEMENET: $BE\n"); exit(5); }
$only = isset($argv[1]) ? (int) $argv[1] : 0;

$modelId = 'gpt-5.6-sol';
$modelEntry = findModel($modelId);
if (!$modelEntry) { fwrite(STDERR, "ismeretlen modell: $modelId\n"); exit(2); }
$apiKey = innosocialAiResolveApiKey($modelEntry['env']);
if (!$apiKey) { fwrite(STDERR, "nincs kulcs: {$modelEntry['env']}\n"); exit(3); }

$osszKoltseg = 0.0;
foreach ($in as $item) {
    $account = $item['account']; $row = $item['row'];
    $id = (int) $account['id'];
    if ($only && $id !== $only) continue;
    $t0 = microtime(true);
    try {
        ['site' => $site, 'meta' => $siteMeta, 'homeHtml' => $homeHtml, 'posts' => $posts]
            = autofillGatherSources($row, $account);
        $siteUrl = trim((string) ($row['brand_website_url'] ?? ''));
        if (empty($site['pages']) && (int) $posts['chars'] === 0) {
            printf("#%-4s %-30s NINCS FORRAS (honlap ures ES nulla poszt-karakter)\n", $id, mb_substr($account['page_name'],0,30));
            continue;
        }
        $p = autofillBuildPrompt($account, $siteUrl, $site, $siteMeta, $posts);
        /* UJRAPROBA: a szallitott CURLOPT_TIMEOUT 120 masodperc, es a valos valaszido a korlat
         * kornyeken szor. Egy timeout nem a marka tulajdonsaga, hanem a pade -- ha nem probaljuk
         * ujra, a hianyzo sor ugy nez ki, mintha a fiokkal lenne baj. */
        $result = null; $utolsoHiba = null;
        for ($kiserlet = 1; $kiserlet <= 3; $kiserlet++) {
            try { $result = callProvider($modelEntry, $apiKey, $p['system'], $p['user']); break; }
            catch (Throwable $e) {
                $utolsoHiba = $e;
                if ($kiserlet < 3) { printf("#%-4s %-30s ujraproba %d/3 (%s)\n", $id, mb_substr($account['page_name'],0,30), $kiserlet, mb_substr($e->getMessage(), 0, 40)); sleep(5); }
            }
        }
        if ($result === null) throw $utolsoHiba;
        $cost = estimateCostUsd($modelEntry, $result['usage']);
        $osszKoltseg += (float) $cost;
        $parsed = InnoSocialBrandAutofill::parse($result['text'], (int) $posts['chars'], !empty($site['pages']));
        if (empty($parsed['ok'])) {
            printf("#%-4s %-30s PARSE-HIBA: %s\n", $id, mb_substr($account['page_name'],0,30), mb_substr((string)($parsed['error'] ?? '?'),0,60));
            continue;
        }
        $proposal = autofillBuildProposal($parsed, $homeHtml, $account, $site, $siteMeta, $posts, $modelId, $cost);
        $proposal['_meta'] = ['account_id' => $id, 'page_name' => $account['page_name'],
                              'website' => $siteUrl, 'seconds' => round(microtime(true)-$t0, 1)];
        file_put_contents("$OUT/fiok-$id.json", json_encode($proposal, JSON_UNESCAPED_UNICODE));
        printf("#%-4s %-30s OK  oldal:%-2s poszt:%-3s tema:%-2s tag:%-3s dropped:%-3s usd:%.4f  %ss\n",
            $id, mb_substr($account['page_name'],0,30),
            count($site['pages'] ?? []), $posts['chars'] > 0 ? count($posts['facebook'] ?? []) + count($posts['instagram'] ?? []) : 0,
            count($proposal['themes'] ?? []),
            array_sum(array_map(fn($t) => count($t['tags'] ?? []), $proposal['themes'] ?? [])),
            count($parsed['dropped'] ?? []), $cost, round(microtime(true)-$t0,1));
    } catch (Throwable $e) {
        printf("#%-4s %-30s KIVETEL: %s\n", $id, mb_substr($account['page_name'],0,30), mb_substr($e->getMessage(),0,70));
    }
}
printf("\nOSSZ KOLTSEG: %.4f USD\n", $osszKoltseg);
