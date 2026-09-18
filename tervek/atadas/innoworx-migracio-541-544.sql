-- INNOWORX 541-544 -- A NEGY UJ MIGRACIOS BLOKK, KIEMELVE.
--
-- FORRAS: /Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet/api/migrations.sql
--         (HEAD d792c2f08833bf35019d501c984b9c75301fbc8a), 5298-5386. sor.
--
-- >>> EZ A FAJL OLVASASRA VAN, NEM FUTTATASRA. <<<
-- A futtato (api/migrate.php) FIX UTAT olvas: __DIR__ . '/migrations.sql'. Mas fajlt
-- nem vesz at. A prodra tehat a TELJES api/migrations.sql megy fel, es az api/migrate.php
-- futtatja -- ez a negy blokk az egyetlen, ami meg nincs a migration_history-ban.
--
-- A blokk-ID-k (a migration_history.id VARCHAR(50), ezert a hosszuk szamit):
--   541_innosocial_post_type_per_network            36 karakter
--   542_innosocial_post_type_per_network_backfill   45 karakter
--   543_innosocial_post_type_split                  30 karakter
--   544_innosocial_media_jobs                       25 karakter
-- Mind a negy befer. A 23 TULHOSSZU ID a fajl korabbi reszeben van, nem itt.

-- ID: 541_innosocial_post_type_per_network
-- Per-network post type: the two columns, added next to `post_type`.
--
-- STEP 1 AND 2 OF FIVE, AND THE SPLIT IS THE POINT. `innosocial_cron_publish.php`
-- keeps running while this ships, and this database holds 302 real posts --
-- scheduled, published, and drafts a colleague will finish later. Nothing here may
-- break. So the new columns arrive NEXT TO the old one, nullable, and the old
-- column keeps working untouched.
--
-- NULL is not "unknown": it MEANS "this network does not get this post". That is
-- why neither column is NOT NULL and neither has a default -- a default would give
-- every future row a type on a network nobody chose.
ALTER TABLE innosocial_posts
  ADD COLUMN post_type_facebook
    ENUM('single_image','carousel','video','text_only','reel','story') NULL DEFAULT NULL
    COMMENT 'Type on the Facebook leg; NULL = this post does not go to Facebook',
  ADD COLUMN post_type_instagram
    ENUM('single_image','carousel','video','text_only','reel','story') NULL DEFAULT NULL
    COMMENT 'Type on the Instagram leg; NULL = this post does not go to Instagram';

-- ID: 542_innosocial_post_type_per_network_backfill
-- THE BACKFILL COPIES, IT DOES NOT DECIDE.
--
-- facebook -> (fb = post_type, ig = NULL) - instagram -> (fb = NULL, ig = post_type)
-- both -> (fb = post_type, ig = post_type)
--
-- The tempting move is to be clever: a `video` on `both` is the case this whole
-- change exists for, and writing ig = 'reel' here would look like a fix. It would
-- be the migration choosing content for people on rows they cannot see changing --
-- on 302 posts that are somebody's real work. `story` stays one value for the same
-- reason: the word already means two operations, and the attached media decides
-- which one at publish time.
--
-- Measured on this database before writing (Nova, prod): exactly two rows carry a
-- combination the new constraint would refuse, both `reel`+facebook DRAFTS, and no
-- outgoing post is affected at all. They are copied faithfully and listed, not
-- repaired here.
--
-- The WHERE guard makes it re-runnable: it touches only rows nobody has legs for.
UPDATE innosocial_posts
   SET post_type_facebook  = CASE WHEN platform IN ('facebook','both')  THEN post_type ELSE NULL END,
       post_type_instagram = CASE WHEN platform IN ('instagram','both') THEN post_type ELSE NULL END
 WHERE post_type_facebook IS NULL
   AND post_type_instagram IS NULL;

-- ID: 543_innosocial_post_type_split
-- The marker for a DELIBERATE split.
--
-- The legs can differ for two reasons: the operator set them apart, or the
-- derivation happens to produce that. The two are indistinguishable in the data,
-- and the difference decides whether a later save may overwrite them.
--
-- Measured on the split instance before porting: a post saved with
-- fb=single_image and ig=carousel, then saved again WITHOUT leg types, came back
-- `success` with ig silently reverted. The operator's choice disappeared with no
-- signal. Guessing does not help either: if the sync only overwrote matching legs,
-- the legitimate case would break instead - someone changes the platform and the
-- legs must follow.
ALTER TABLE innosocial_posts
  ADD COLUMN post_type_split TINYINT(1) NOT NULL DEFAULT 0
    COMMENT '1 = the legs were set deliberately and the sync must not derive over them';

-- ID: 544_innosocial_media_jobs
-- The GIF -> MP4 conversion queue.
--
-- Shaped like the job tables that already exist here, and drained the same way --
-- the worker is started at request time through JobDispatch, not by cron. Nothing
-- in this codebase drains a job table from cron.
CREATE TABLE IF NOT EXISTS innosocial_media_jobs (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id INT NOT NULL,
  client_id INT NOT NULL,
  post_id INT NULL DEFAULT NULL
    COMMENT 'The post the result attaches to; NULL when the upload is not yet tied to one',
  kind ENUM('gif_to_mp4') NOT NULL DEFAULT 'gif_to_mp4',
  source_ref VARCHAR(500) NOT NULL,
  result_ref VARCHAR(500) NULL DEFAULT NULL,
  status ENUM('pending','running','done','error') NOT NULL DEFAULT 'pending',
  error_message TEXT NULL,
  -- A run that dies mid-way leaves the row in 'running' forever, and nothing can
  -- tell a working job from a dead one. These two make a stuck job recognisable.
  attempts TINYINT UNSIGNED NOT NULL DEFAULT 0,
  created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
  started_at TIMESTAMP NULL DEFAULT NULL,
  finished_at TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_status_created (status, created_at),
  KEY idx_post (post_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
