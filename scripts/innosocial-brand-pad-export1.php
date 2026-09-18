<?php
/* 1. FAZIS -- az InnoWorx oldalan fut, mert a tokenek AZ O JWT_SECRET-jevel vannak titkositva.
 * Kiolvassa a 12 teszt-fiokot, es a tokent UJRATITKOSITJA az InnoSocial kulcsaval, hogy a
 * 2. fazis a SZALLITOTT `autofillGatherSources()`-t hivhassa valtoztatas nelkul.
 * A token sehova nem kerul ki: vegig a szerveren marad, es sosem irodik ki nyersen. */
$IW = '/home/napalatt/app.innoworx.hu/api';
chdir($IW);
require_once $IW . '/config.php';
require_once $IW . '/integrations/shared/EncryptionHelper.php';
use InnoWorx\Integrations\Shared\EncryptionHelper;

// a masik telepites kulcsa, CSAK ujratitkositashoz -- sosem irjuk ki
$isEnv = file_get_contents('/home/napalatt/app.innosocial.hu/api/.env');
if (!preg_match('/^JWT_SECRET\s*=\s*"?([^"\r\n]+)"?/m', $isEnv, $m)) { fwrite(STDERR, "nincs JWT_SECRET az InnoSocial .env-ben\n"); exit(2); }
$isSecret = trim($m[1]);

$db = getDB();
$q = $db->query("SELECT a.id, a.client_id, a.page_name, a.page_username, a.profile_picture_url,
        a.facebook_page_id, a.instagram_business_account_id, a.access_token_encrypted, a.active,
        s.*
   FROM innosocial_meta_accounts a
   JOIN innosocial_account_brand_settings s ON s.meta_account_id = a.id
  WHERE a.active = 1 AND s.brand_website_url IS NOT NULL AND s.brand_website_url <> ''
  ORDER BY a.id");
$out = [];
foreach ($q as $r) {
    try { $plain = EncryptionHelper::decrypt($r['access_token_encrypted'], JWT_SECRET); }
    catch (Throwable $e) { fwrite(STDERR, "#{$r['id']} token nem fejtheto: " . $e->getMessage() . "\n"); continue; }
    $account = [
        'id' => (int) $r['id'], 'client_id' => (int) $r['client_id'],
        'page_name' => $r['page_name'], 'page_username' => $r['page_username'],
        'profile_picture_url' => $r['profile_picture_url'],
        'facebook_page_id' => $r['facebook_page_id'],
        'instagram_business_account_id' => $r['instagram_business_account_id'],
        'access_token_encrypted' => EncryptionHelper::encrypt($plain, $isSecret),
        'active' => 1,
    ];
    $row = [];
    foreach ($r as $k => $v) { if (!is_int($k)) $row[$k] = $v; }
    $out[] = ['account' => $account, 'row' => $row];
}
file_put_contents('/tmp/nova_export_bemenet.json', json_encode($out, JSON_UNESCAPED_UNICODE));
printf("fiok: %d, fajl: /tmp/nova_export_bemenet.json (%d byte)\n", count($out), filesize('/tmp/nova_export_bemenet.json'));
foreach ($out as $o) printf("  #%-4s %-32s %s\n", $o['account']['id'], mb_substr($o['account']['page_name'],0,32), mb_substr((string)$o['row']['brand_website_url'],0,38));
