<?php

/**
 * AZ INNOWORX 302 POSZTJANAK FELMERESE A 2. UTEM ATVITELE ELOTT. READ-ONLY.
 *
 * A vezerelv, amibol minden kerdes kovetkezik: a `napalatt_innoworx_prod`-ban
 * VALODI posztok vannak -- idozitettek, mar kimentek, es piszkozatok, amiket a
 * kollega kesobb veglegesit. EGYIK SEM TORHET EL. Ez a szkript azt meri meg,
 * hogy a tervezett valtoztatasok kozul melyik ERINTENE egy MAR LETEZO sort.
 *
 * KIZAROLAG SELECT. Nem ir, nem torol, nem futtat migraciot. Titkot nem ir ki.
 *
 * ES EGY KIKOTES A SZAMOK OLVASASAHOZ: egy nulla itt KETFELE lehet. "Nincs ilyen
 * sor" es "rossz helyen kerestem" ugyanugy nezne ki -- ezert minden veszelyes
 * kerdes mellett ott all a NEVEZO is (hany sorbol valogattunk), es a vegen egy
 * pozitiv kontroll, ami bizonyitja, hogy a lekerdezes egyaltalan lat adatot.
 *
 * HASZNALAT a hoszton, az api/ konyvtarbol:
 *   php innoworx-302-felmeres.php
 */

set_exception_handler(function (Throwable $e) {
    fwrite(STDERR, 'ELSZALLT: ' . get_class($e) . ': ' . $e->getMessage() . "\n");
    exit(9);
});

require_once 'config.php';
$db = getDB();
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

function cim(string $s): void { echo "\n=== $s ===\n"; }
function sor(string $s): void { echo "  $s\n"; }

/* A CELPONT AZONOSSAGA A MERES RESZE. Ma este egy meres a rossz portra ment, es
 * "helyes" valaszt adott -- a MASIK rendszerbol. Ezert a DB neve elol all, es ha
 * nem az, amit varunk, a szkript MEGALL. */
$dbNev = (string) $db->query('SELECT DATABASE()')->fetchColumn();
echo "adatbazis: $dbNev\n";
/* A HAROM ELFOGADOTT NEV, es mindharom InnoWorx: a prod, a tavoli dev, es a
 * lokalis docker-peldany (`innoworx`). A kapu celja NEM az, hogy csak a prodot
 * engedje, hanem hogy a MASIK RENDSZERT (InnoSocial) kizarja -- ma este egy
 * meres a rossz portra ment, es "helyes" valaszt adott a masik rendszerbol. */
if (!in_array($dbNev, ['napalatt_innoworx_prod', 'napalatt_innoworx_dev', 'innoworx'], true)) {
    fwrite(STDERR, "!! ALLJ: nem InnoWorx adatbazis ($dbNev). Nem ezt akartuk merni.\n");
    exit(2);
}

$osszes = (int) $db->query('SELECT COUNT(*) FROM innosocial_posts')->fetchColumn();
sor("osszes poszt: $osszes   <- EZ A NEVEZO minden lenti szamhoz");
if ($osszes === 0) {
    sor('(ures tabla -- minden lenti nulla ERROL szol, nem a kockazat hianyarol)');
}

cim('1. ELOSZLAS: statusz x tipus x platform');
$q = $db->query(
    'SELECT status, post_type, platform, COUNT(*) db
       FROM innosocial_posts GROUP BY status, post_type, platform
      ORDER BY status, post_type, platform'
);
foreach ($q as $r) {
    sor(sprintf('%-14s %-14s %-11s %d', $r['status'], $r['post_type'], $r['platform'], $r['db']));
}

cim('2. MEDIA-ELLATOTTSAG (a ket forras KULON, mert a szuk tu mar megtevesztett)');
$q = $db->query(
    "SELECT
        SUM(CASE WHEN g.db > 0 AND m.db = 0 THEN 1 ELSE 0 END) csak_generalt,
        SUM(CASE WHEN g.db = 0 AND m.db > 0 THEN 1 ELSE 0 END) csak_feltoltott,
        SUM(CASE WHEN g.db > 0 AND m.db > 0 THEN 1 ELSE 0 END) mindketto,
        SUM(CASE WHEN g.db = 0 AND m.db = 0 THEN 1 ELSE 0 END) semmi
     FROM innosocial_posts p
     JOIN (SELECT p2.id, (SELECT COUNT(*) FROM innosocial_generated_images gi WHERE gi.post_id=p2.id AND gi.picked=1) db FROM innosocial_posts p2) g ON g.id=p.id
     JOIN (SELECT p3.id, (SELECT COUNT(*) FROM innosocial_post_media pm WHERE pm.post_id=p3.id AND pm.media_type IN ('image','video')) db FROM innosocial_posts p3) m ON m.id=p.id"
);
$r = $q->fetch(PDO::FETCH_ASSOC);
sor(sprintf('csak generalt kep: %d | csak feltoltott media: %d | mindketto: %d | SEMMI: %d',
    (int) $r['csak_generalt'], (int) $r['csak_feltoltott'], (int) $r['mindketto'], (int) $r['semmi']));

/* ================== A KET PRESERVATION-KOCKAZAT ================== */

cim('3. KOCKAZAT (story-media gate): MAR KIMENO allapotu, MEDIA NELKULI sztorik');
sor('Ezeket a gate NEM dobhatja vissza: mar jovahagyottak vagy utban vannak.');
$q = $db->query(
    "SELECT p.id, p.status, p.platform, p.scheduled_at,
            LENGTH(TRIM(p.text_content)) szoveg
       FROM innosocial_posts p
      WHERE p.post_type = 'story'
        AND p.status IN ('pending_review','approved','publishing','published')
        AND (SELECT COUNT(*) FROM innosocial_generated_images g WHERE g.post_id=p.id AND g.picked=1)
          + (SELECT COUNT(*) FROM innosocial_post_media m WHERE m.post_id=p.id AND m.media_type IN ('image','video')) = 0
      ORDER BY p.scheduled_at"
);
$n = 0;
foreach ($q as $r) {
    $n++;
    sor(sprintf('id=%-6s %-14s %-11s %s  szoveg=%d', $r['id'], $r['status'], $r['platform'], $r['scheduled_at'], $r['szoveg']));
}
$osszesStory = (int) $db->query("SELECT COUNT(*) FROM innosocial_posts WHERE post_type='story'")->fetchColumn();
sor(">>> ERINTETT: $n   (az osszes story: $osszesStory)");
sor($n > 0
    ? '>>> GRANDFATHER KELL: a gate csak UJ kimeno atmenetre allhat, ezekre nem.'
    : '>>> nincs erintett sor -- a gate visszamenoleg nem nyul semmihez.');

cim('4. KOCKAZAT (platform x tipus kikotes): MEGLEVO sorok, amiket az UJ kikotes elutasitana');
sor('A kikotes az UJ mentesre/atmenetre all -- de tudnunk kell, hany meglevo sort erintene.');
$q = $db->query(
    "SELECT id, status, post_type, platform, scheduled_at
       FROM innosocial_posts
      WHERE (post_type='reel'      AND platform <> 'instagram')
         OR (post_type='video'     AND platform <> 'facebook')
         OR (post_type='text_only' AND platform <> 'facebook')
      ORDER BY status, id"
);
$n2 = 0; $kimeno = 0;
foreach ($q as $r) {
    $n2++;
    if (in_array($r['status'], ['pending_review','approved','publishing','published'], true)) { $kimeno++; }
    sor(sprintf('id=%-6s %-14s %-11s %-11s %s', $r['id'], $r['status'], $r['post_type'], $r['platform'], $r['scheduled_at']));
}
sor(">>> ERINTETT: $n2   ebbol MAR KIMENO allapotu: $kimeno");
sor($kimeno > 0
    ? '>>> ALLJ: kimeno allapotu sor is erintett. A kikotes NEM allhat visszamenoleg -- Zsolt dontese.'
    : '>>> kimeno allapotu erintett sor NINCS; a tobbi piszkozat, azokat a kikotes a KOVETKEZO mentesnel erintene.');

cim('5. JOVOBELI, MAR BEUTEMEZETT SOROK -- ezek a legerzekenyebbek');
$q = $db->query(
    "SELECT COUNT(*) db, MIN(scheduled_at) elso, MAX(scheduled_at) utolso
       FROM innosocial_posts
      WHERE status IN ('pending_review','approved','publishing') AND scheduled_at > NOW()"
);
$r = $q->fetch(PDO::FETCH_ASSOC);
sor(sprintf('jovobeli kimeno sor: %d   (%s ... %s)', (int) $r['db'], $r['elso'] ?? '-', $r['utolso'] ?? '-'));

cim('6. POZITIV KONTROLL -- lat-e egyaltalan adatot a lekerdezes?');
$r = $db->query("SELECT COUNT(*) FROM innosocial_posts WHERE status='published'")->fetchColumn();
sor("mar publikalt poszt: $r   (ha ez is 0 egy 302 soros tablan, a szuroim rosszak, nem a vilag)");

cim('7. A SEMA MAI ALLAPOTA (mi hianyzik meg a 2. utemhez)');
foreach ([
    'post_type_facebook', 'post_type_instagram', 'post_type_split',
] as $oszlop) {
    $van = (int) $db->query(
        "SELECT COUNT(*) FROM information_schema.COLUMNS
          WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='innosocial_posts' AND COLUMN_NAME='$oszlop'"
    )->fetchColumn();
    sor(sprintf('%-22s %s', $oszlop, $van ? 'MAR LETEZIK' : 'hianyzik (a migracio hozza)'));
}
$tabla = (int) $db->query(
    "SELECT COUNT(*) FROM information_schema.TABLES
      WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='innosocial_media_jobs'"
)->fetchColumn();
sor(sprintf('%-22s %s', 'innosocial_media_jobs', $tabla ? 'MAR LETEZIK' : 'hianyzik (a migracio hozza)'));

echo "\nA FELMERES VEGE. Egyetlen sort sem irtunk.\n";
