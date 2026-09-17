-- AZ ELSO ELES POSZT ELLENORZESE a hashtag-kapcsolo utan (READ-ONLY).
--
-- >>> MIT BIZONYIT MELYIK FORRAS -- ezt eloszor olvasd el, mert az elso valtozat ebben tevedett: <<<
--   a `innosocial_publishing_log` a "KIMENT-E" kerdesre valaszol (melyik posztbol melyik platformra,
--   sikerrel, mikor). A "MI MENT KI" kerdesre NEM: a tablanak NINCS caption/message/payload mezoje,
--   es a Meta publikalasi valasza (amibol a `raw_response` keszul) CSAK AZONOSITOKAT ad vissza --
--   `id` es `post_id` --, a kikuldott szoveget nem (MetaAdapter::publishToPage, 202-215. sor).
--   A CAPTIONT tehat a KINT LEVO POSZT bizonyitja: a `platform_post_url` permalinkjet kell megnyitni.
--   A VART erteket a 2. lekerdezes adja; a MEGFIGYELT erteket a szemed a permalinken. A ketto
--   osszevetese a bizonyitek -- egyik onmagaban sem az.
--
-- Futtatas a prod DB-n, miutan a kollega kikuldott egy posztot.
-- (Az idobelyeg-oszlop neve `attempted_at`, NEM `created_at`. Az elso valtozat ezen hibara futott
--  volna -- pont a donto lekerdezesen, es pont akkor, amikor a legjobban kellene.)

-- 1) A KAPCSOLOK ALLASA fiokonkent. Ez a VART viselkedes forrasa.
SELECT s.meta_account_id, a.page_name,
       s.hashtags_enabled_facebook  AS fb_kapcsolo,
       s.hashtags_enabled_instagram AS ig_kapcsolo
  FROM innosocial_account_settings s
  JOIN innosocial_meta_accounts a ON a.id = s.meta_account_id
 ORDER BY s.meta_account_id;

-- 2) A VART CAPTION a deploy ota kiment posztokra, platformonkent kibontva.
--    A szett tagjai CSAK oda kerulnek, ahol a kapcsolo 1 -- ugyanaz a szabaly, amit a Publisher
--    alkalmaz. A szovegbeli (`#`) tagek mindket halozatra kimennek: azokat semmilyen kapcsolo
--    nem veszi le, es ez SZANDEKOS.
SELECT p.id, p.platform, p.published_at, h.set_name,
       JSON_LENGTH(h.hashtags) AS szett_tag_db,
       (LENGTH(p.text_content) - LENGTH(REPLACE(p.text_content, '#', ''))) AS szovegbeli_tag,
       s.hashtags_enabled_facebook  AS fb_kapcsolo,
       s.hashtags_enabled_instagram AS ig_kapcsolo,
       CASE WHEN p.post_type = 'story' THEN 'STORY: nincs caption, semmi nem megy ki'
            WHEN p.hashtag_set_id IS NULL THEN 'nincs szett: csak a szovegbeli tagek'
            ELSE CONCAT('FB: ', IF(s.hashtags_enabled_facebook, 'szett-tagek IGEN', 'szett-tagek NEM'),
                        ' | IG: ', IF(s.hashtags_enabled_instagram, 'szett-tagek IGEN', 'szett-tagek NEM'))
       END AS vart_viselkedes,
       LEFT(p.text_content, 70) AS szoveg_eleje
  FROM innosocial_posts p
  LEFT JOIN innosocial_hashtag_sets h ON h.id = p.hashtag_set_id
  LEFT JOIN innosocial_account_settings s ON s.meta_account_id = p.meta_account_id
 WHERE p.published_at >= '2026-09-17 12:04:00'
 ORDER BY p.published_at DESC
 LIMIT 20;

-- 3) A KIKULDES NYOMA, es a CIM, ahol a caption megnezheto.
--    Platformonkent kulon sor -- egy `both` posztnal tehat KET permalink jon, es a kettot KULON
--    kell megnezni: eppen az a kerdes, hogy elternek-e.
SELECT l.post_id, l.platform, l.success, l.attempt_number, l.attempted_at,
       l.platform_post_url AS ITT_NEZD_MEG_A_CAPTIONT,
       l.error_code, LEFT(COALESCE(l.error_message, ''), 60) AS hiba
  FROM innosocial_publishing_log l
 WHERE l.attempted_at >= '2026-09-17 12:04:00'
 ORDER BY l.attempted_at DESC, l.post_id, l.platform
 LIMIT 40;

-- 4) KONTROLL A KONTROLLHOZ: ha a 2. es a 3. URES, az NEM azt jelenti, hogy jol mukodik --
--    hanem hogy MEG NEM MENT KI SEMMI, tehat nincs mit ellenorizni.
SELECT (SELECT COUNT(*) FROM innosocial_posts WHERE published_at >= '2026-09-17 12:04:00') AS uj_posztok,
       (SELECT COUNT(*) FROM innosocial_publishing_log WHERE attempted_at >= '2026-09-17 12:04:00') AS naplo_sorok;
