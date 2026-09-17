<?php

/**
 * MIT TUD A WEB SAPI? -- olvaso proba, semmit nem ir, semmit nem indit el.
 *
 * MIERT KELL EGYALTALAN. A GIF -> MP4 konverzio korlatait CLI SAPI-bol mertuk:
 * `/home/napalatt/bin/ffmpeg` (7.0.2-static), `proc_open`/`shell_exec`/`popen`
 * elerheto, `exec`/`system`/`passthru` tiltott. A cPanelen a WEB SAPI-nak sajat
 * `disable_functions`-je es sajat PATH-ja lehet -- a ketto rendszeresen elter, es
 * eppen ez az, amit nem szabad feltetelezni. Ugyanez a csapda fogott meg minket a
 * feltoltesi korlatnal is: `ini_get` a webben mast adott, mint CLI-ben.
 *
 * ES AMI FONTOS AZ EREDMENY OLVASASAKOR: ha a web SAPI-bol az ffmpeg NEM erheto el,
 * az NEM kudarc es NEM akadaly. Az a HATTER-UT IGAZOLASA: pontosan ezert nem a
 * feltoltes keresében konvertalunk, hanem DETACHALT folyamatban. Ha viszont
 * elerheto, az sem ok arra, hogy inline konvertaljunk -- egy 100 MB-os video a
 * keresben akkor is rossz alak. A proba a TENYT adja meg, nem a dontest.
 *
 * (Ez a bekezdes eredetileg "cronbol"-t irt. Az a MI tervunk volt, nem a rendszere:
 * ebben a repoban NINCS cron, ami job-tablat uritene -- a `JobDispatch` keres-idoben
 * detachal. Javitva, mert egy fajl, ami ellentmond onmaganak, a sajat also felet is
 * gyanussa teszi.)
 *
 * ================== MIRE VALASZOL, ES MIKOR KELL ==================
 *
 * 2026-09-17: EZT A PROBAT NEM FUTTATTUK LE, ES MA NINCS IS RA SZUKSEG.
 *
 * A kerdes idokozben eldolt OLVASASSAL: a web handler es a CLI ugyanaz a csomag
 * (`ea-php82`), a `disable_functions` a MESTER ini-bol jon, es PHP_INI_SYSTEM --
 * tehat `.user.ini`-bol vagy `.htaccess`-bol nem irhato felul. Ebbol kovetkezik,
 * hogy a web SAPI ugyanazt latja, mint a CLI: `proc_open`/`shell_exec`/`popen`
 * elerheto, `exec`/`system`/`passthru` tiltott.
 * Es a GIF-konverter vegul NEM a webbol konvertal: a `JobDispatch` detachalt
 * folyamatot indit, es az ffmpeg-et ABSZOLUT uton hivja, tehat a PATH-kerdes fel
 * sem merul.
 *
 * AKKOR KELL ELOVENNI, HA:
 *   - valaha INLINE konverzio kerul szoba (a `JobDispatch` harmadik fokozata a
 *     webfolyamatban fut -- ott mar szamit, mit tud a web SAPI); vagy
 *   - a konverter a bevezetes utan azzal bukik, hogy nem talalja vagy nem tudja
 *     inditani az ffmpeg-et, es a naplosor nem mond eleget; vagy
 *   - a hoszt PHP-verziot vagy csomagot valt -- akkor a fenti levezetes ujra
 *     merendo, mert a KONFIGURACIO valtozott alatta.
 *
 * ES AMIERT NEM TETTUK KI "csak biztosra": egy fajl a webgyokerben akar egy
 * percre is NYILVANOSAN elerheto, es kornyezeti reszleteket ir ki. A kockazat
 * kicsi, de nem nulla -- es kiderult, hogy nincs is ra szukseg.
 * ==================================================================
 *
 * HASZNALAT: tedd a webgyokerbe ideiglenesen, hivd meg bongeszobol vagy curl-lel,
 * majd VEDD LE. Titkot nem ir ki: sem jelszot, sem tokent, sem kornyezeti valtozot
 * a PATH-on kivul.
 */

header('Content-Type: text/plain; charset=utf-8');

$ffmpeg = '/home/napalatt/bin/ffmpeg';

echo "sapi: " . PHP_SAPI . "\n";
echo "php:  " . PHP_VERSION . "\n";
echo "disable_functions: [" . ini_get('disable_functions') . "]\n";
echo "PATH: " . (getenv('PATH') ?: '(nincs)') . "\n";
echo "max_execution_time: " . ini_get('max_execution_time') . "\n";
echo "memory_limit: " . ini_get('memory_limit') . "\n\n";

foreach (['proc_open', 'shell_exec', 'popen', 'exec', 'system', 'passthru'] as $f) {
    printf("  %-10s %s\n", $f, function_exists($f) ? 'van' : 'NINCS');
}

echo "\nffmpeg a varhato uton ($ffmpeg):\n";
echo "  letezik:     " . (file_exists($ffmpeg) ? 'igen' : 'NEM') . "\n";
echo "  futtathato:  " . (is_executable($ffmpeg) ? 'igen' : 'NEM') . "\n";

/* A verzio-lekerdezes a legolcsobb valodi proba: elindul-e egyaltalan a binaris a
 * web SAPI alol. `proc_open`-nel maradunk, mert az `exec`-csalad CLI-ben mar
 * tiltott volt, es nem akarunk a tiltott agon merni. */
if (function_exists('proc_open') && is_executable($ffmpeg)) {
    $leiro = [1 => ['pipe', 'w'], 2 => ['pipe', 'w']];
    $p = @proc_open([$ffmpeg, '-version'], $leiro, $cso);
    if (is_resource($p)) {
        $ki = stream_get_contents($cso[1]);
        fclose($cso[1]);
        fclose($cso[2]);
        $kod = proc_close($p);
        $elsoSor = strtok($ki, "\n");
        echo "  -version:    kilepes=$kod  |  " . ($elsoSor !== false ? $elsoSor : '(ures kimenet)') . "\n";
    } else {
        echo "  -version:    a proc_open NEM indult el\n";
    }
} else {
    echo "  -version:    nem probaltam (nincs proc_open vagy nem futtathato)\n";
}

echo "\nEZ A PROBA SEMMIT NEM IRT ES SEMMIT NEM INDITOTT EL A VERZIO-LEKERDEZESEN KIVUL.\n";
