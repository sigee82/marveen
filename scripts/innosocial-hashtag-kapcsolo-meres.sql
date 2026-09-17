-- INNOSOCIAL HASHTAG-SZETT: A POZITIV KONTROLL LEKERDEZESEI (READ-ONLY)
--
-- MIERT KELL: a kod-olvasas megmondta, MI TORTENHET. Azt nem, hogy a kollega
-- valodi posztjain MELYIK ut tuzelt. Ez a fajl az a negy kerdes, amit Nova
-- 4. pontja ker -- mind SELECT, egyik sem ir.
--
-- Bit, 2026-09-17. A lokalis dev DB-ben NINCSENEK innosocial_* tablak,
-- ezert a kontrollt ott NEM lehetett elvegezni.

-- 1) A TUNET MAGA: szett NINCS kivalasztva, megis all hashtag a szovegben.
--    Ez a "beegett" ut (az AI-valtozat elfogadasakor a tagek a text_content-be
--    kerulnek, a kapcsolotol fuggetlenul).
SELECT p.id, p.client_id, p.meta_account_id, p.platform, p.status,
       p.created_at, LEFT(p.text_content, 60) AS szoveg_eleje,
       (LENGTH(p.text_content) - LENGTH(REPLACE(p.text_content, '#', ''))) AS kettoskereszt_db
  FROM innosocial_posts p
 WHERE p.hashtag_set_id IS NULL
   AND p.text_content LIKE '%#%'
 ORDER BY p.created_at DESC
 LIMIT 50;

-- 2) A DUPLA UT: a szovegben MAR van hashtag ES szett is van valasztva.
--    Ezeken publikalaskor a Publisher MEG egyszer hozzafuzi a szett tagjeit.
SELECT p.id, p.client_id, p.platform, p.status, h.set_name,
       (LENGTH(p.text_content) - LENGTH(REPLACE(p.text_content, '#', ''))) AS kettoskereszt_a_szovegben,
       JSON_LENGTH(h.hashtags) AS szett_meret
  FROM innosocial_posts p
  JOIN innosocial_hashtag_sets h ON h.id = p.hashtag_set_id
 WHERE p.text_content LIKE '%#%'
 ORDER BY p.created_at DESC
 LIMIT 50;

-- 3) A LAPPANGO UT: inaktiv szettre mutato poszt. A Publisher az `active`
--    mezot NEM nezi, a felulet viszont csak az aktivakat listazza.
--    (A feluleten a torles HARD DELETE, tehat ez valoszinuleg 0 sor lesz --
--     ha megsem, az onallo lelet.)
SELECT p.id, p.client_id, p.status, h.id AS set_id, h.set_name, h.active
  FROM innosocial_posts p
  JOIN innosocial_hashtag_sets h ON h.id = p.hashtag_set_id
 WHERE h.active = 0
 LIMIT 50;

-- 4) A HATOKOR: hany szett van ugyfelenkent/fiokonkent, es van-e egyaltalan
--    alapertelmezett. Ahol NINCS is_default, ott a felulet az ELSO szettet
--    valasztja ki magatol (`?? hashtagSets[0]`) -- ott a "sosem kapcsol ki"
--    tunet erosebb.
SELECT h.client_id, h.meta_account_id, COUNT(*) AS szettek,
       SUM(h.is_default = 1) AS alapertelmezett_db,
       SUM(h.active = 1) AS aktiv_db
  FROM innosocial_hashtag_sets h
 GROUP BY h.client_id, h.meta_account_id
 ORDER BY szettek DESC;

-- 5) KONTROLL A KONTROLLHOZ: van-e egyaltalan poszt es szett a vizsgalt
--    peldanyon. Ha ezek nullak, a fenti negy ures halmaza SEMMIT nem jelent.
SELECT (SELECT COUNT(*) FROM innosocial_posts)        AS posztok,
       (SELECT COUNT(*) FROM innosocial_hashtag_sets) AS szettek,
       (SELECT COUNT(*) FROM innosocial_posts WHERE status = 'published') AS publikalt;
