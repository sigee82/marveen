-- AZ ELSO ELES POSZT ELLENORZESE a hashtag-kapcsolo utan (READ-ONLY).
--
-- MIERT KELL KULON: a deploy zoldje es a "cron fut, nem hibazik" csak annyit mond, hogy a fajl
-- betoltheto. A caption-ag -- vagyis a ket uj kapcsolo TENYLEGES hatasa -- csak akkor fut le,
-- amikor egy poszt valoban kimegy. A deploy utan `attempted=0` volt: a bizonyitek meg nem letezik.
--
-- Futtatas a prod DB-n, miutan a kollega kikuldott egy posztot.

-- 1) A KAPCSOLOK ALLASA fiokonkent. Ez a VART viselkedes forrasa.
SELECT s.meta_account_id, a.page_name,
       s.hashtags_enabled_facebook  AS fb_kapcsolo,
       s.hashtags_enabled_instagram AS ig_kapcsolo
  FROM innosocial_account_settings s
  JOIN innosocial_meta_accounts a ON a.id = s.meta_account_id
 ORDER BY s.meta_account_id;

-- 2) A DEPLOY OTA KIMENT POSZTOK, a szettjukkel egyutt.
--    A `hashtag_set_id` mondja meg, MI JOHETNE a szettbol; a kapcsolo, hogy melyik halozatra jut el.
SELECT p.id, p.platform, p.status, p.published_at,
       p.hashtag_set_id,
       h.set_name,
       JSON_LENGTH(h.hashtags) AS szett_tag_db,
       (LENGTH(p.text_content) - LENGTH(REPLACE(p.text_content, '#', ''))) AS szovegbeli_kettoskereszt,
       LEFT(p.text_content, 80) AS szoveg_eleje
  FROM innosocial_posts p
  LEFT JOIN innosocial_hashtag_sets h ON h.id = p.hashtag_set_id
 WHERE p.published_at >= '2026-09-17 12:04:00'
 ORDER BY p.published_at DESC
 LIMIT 20;

-- 3) A DONTO SOR: a publikalasi naplo. Itt all, ami TENYLEGESEN kiment.
--    Platformonkent kulon sor -- vagyis egy `both` posztnal LATSZIK, ha a ket caption elter.
SELECT l.post_id, l.platform, l.success, l.attempt_number, l.created_at,
       l.platform_post_url
  FROM innosocial_publishing_log l
 WHERE l.created_at >= '2026-09-17 12:04:00'
 ORDER BY l.created_at DESC, l.post_id, l.platform
 LIMIT 40;

-- 4) KONTROLL A KONTROLLHOZ: ha a 2. es a 3. lekerdezes URES, az NEM azt jelenti, hogy jol
--    mukodik -- hanem hogy MEG NEM MENT KI SEMMI, tehat nincs mit ellenorizni.
SELECT (SELECT COUNT(*) FROM innosocial_posts WHERE published_at >= '2026-09-17 12:04:00') AS uj_posztok,
       (SELECT COUNT(*) FROM innosocial_publishing_log WHERE created_at >= '2026-09-17 12:04:00') AS naplo_sorok;
