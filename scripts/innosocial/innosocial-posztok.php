<?php
/**
 * InnoSocial (InnoWorx prod) posts from a package, each left in pending_review
 * with ONE customer review link. Generalises 21na-fb-posztok.php (2026-09-26):
 * platform and post_type are per post, and a post carries an ordered image list
 * (a carousel) or a single image.
 *
 * Nothing goes out on its own: the script never sets 'approved' and never calls
 * publish_now. A post goes out only after the customer approves it on the
 * /r/<token> page, and then the regular cron publishes it at scheduled_at.
 *
 * It drives the app's OWN HTTP endpoints, not raw INSERTs:
 *   1. innosocial_calendar.php?action=check_conflicts   (read)
 *   2. innosocial_calendar.php?action=save_post          status=draft
 *   3. innosocial_image.php?action=upload                once per image, IN ORDER -- the
 *                                                        composer's upload, which appends
 *                                                        (display_order = MAX + 1)
 *   4. innosocial_calendar.php?action=set_status         draft -> pending_review
 *   5. innosocial_calendar.php?action=create_review_link
 *
 * THE CAROUSEL IMAGE COUNT IS CHECKED HERE, NOT BY THE APP'S GATE. Measured on
 * prod code 89013737: set_status runs innosocialNemKeszAtmenetre(), which asks a
 * story for media and every other type for text -- it does not count carousel
 * images. The only "at least 2" check is in Publisher.php, at publish time,
 * after the customer already approved. So between upload and set_status the
 * script reads the images back through PostImages::forPost() -- the very list
 * the publisher sends -- and requires the same count, the same order and the
 * same bytes (md5) as the package. Carousel: 2..10 images (the Meta adapter's
 * limit is 10).
 *
 * ONE POST PER PLATFORM, on purpose: a 'both' post has ONE caption and ONE image
 * list for both legs (Publisher: captionFb = captionIg = body; the split legs
 * only separate post_type), so a different text and a 1:1 vs 4:5 image set
 * cannot live in one post.
 *
 * An Instagram post uses the SAME meta account row: the publisher reads
 * instagram_business_account_id from it. The script requires that column to
 * equal --expect-ig and stops otherwise.
 *
 * AUTH / RBAC: as in 21na-fb-posztok.php -- a 10-minute token minted for --user
 * with the login payload (never printed); a missing innosocial_user_account_access
 * row stops the run unless --temp-grant, which inserts it through the app's
 * grantAccountAccess(), says so, and deletes it at the end (also on a stop) --
 * only if this run inserted it. permissions.innosocial is never touched.
 *
 * IDEMPOTENCY: before ANY write, every post is checked. The key is
 * (account, scheduled_at, platform) with the app's own overlap rule: an existing
 * 'both' post overlaps facebook and instagram alike. Any match, or any
 * check_conflicts hit, stops the run and nothing is written. The two posts of
 * this package share a minute on different platforms and do not stop each other.
 *
 *   cd /home/napalatt/app.innoworx.hu/api
 *   php /path/innosocial-posztok.php --json=/path/posztok.json \
 *       --expect-page=292200250940748 --expect-ig=17841400449301622 --dry-run
 *   php ... (same, without --dry-run) [--temp-grant]
 *   php ... (same) --status                             # read-only readback, any time
 *
 * Package: { client_id, meta_account_id, status: "pending_review",
 *            posts: [ { platform, post_type, scheduled_at_local, text,
 *                       images: [...] | image: "...", video: "x.mp4|x.mov", cover: "...",
 *                       link_url, first_comment, hashtag_set_id,
 *                       post_type_facebook + post_type_instagram, ig_story } ] }
 *
 * EVERYTHING THE APP SCHEDULES (Zsolt TG 19832 via Nova 20338), with the app's own rules, read from
 * innosocial_calendar.php / PostTypePerNetwork.php / Publisher.php on dev 0539a986:
 *   single_image, carousel   facebook | instagram | both
 *   text_only                facebook only (Instagram takes nothing without media); no picture -- the
 *                            publisher would post one with it
 *   video (feed video)       facebook only; mp4 or mov; no picture (the Page video edge takes none)
 *   reel                     instagram only; <= 90 s; one optional cover picture
 *   story                    facebook | instagram | both (both: the same picture/video on both); one
 *                            picture (made 9:16 unless it is) or one video <= 60 s; no caption
 *   leg types                platform both with post_type_facebook (single_image, carousel, text_only,
 *                            video, story) + post_type_instagram (single_image, carousel, reel, story),
 *                            e.g. facebook video + instagram reel from ONE video; the post shares one
 *                            picture list and one video between the legs
 *   link_url                 a Facebook leg's link (picture / carousel / text); first_comment: an Instagram
 *                            feed leg's first comment; hashtag_set_id: one of the client's sets
 * Unknown keys stop the run (a typo must not be dropped); "sor", "source", "note" and "_..." are the
 * packer's own. The saved row (platform, type, legs, link, comment, hashtag set) is read back before
 * any media goes up.
 * scheduled_at_local is Europe/Budapest wall time and is sent as-is.
 *
 * INSTAGRAM STORIES (Nova 20325/20331, Eszter TG 3285/3288). InnoSocial has no
 * feed->story share and Meta's API has none either: a story is its own post,
 * post_type 'story'. A story is made only where it is ASKED FOR (off by
 * default, Eszter wants one for the chosen posts): an Instagram feed post or
 * Reel (platform instagram or both; single_image, carousel, reel) with
 * "ig_story": true gets a companion story: platform instagram, the SAME
 * scheduled_at, its own pending_review and its own review link -- it goes out
 * only if it is approved too. "ig_story": true on the package turns it on for
 * every such post of it.
 *   - Reel: the same MP4. The composer refuses a story over 60 s
 *     (innosocial_video.php); a reel measured over 60 s stops the run, the
 *     package then says "story": false for it.
 *   - Picture: the feed picture (the first one of a carousel) extended to
 *     1080x1920: scaled to the full width, centred, NEVER cropped, on a blurred
 *     and darkened copy of itself. Made here with GD, JPEG.
 *   - The story's text is an internal note (Meta publishes no story caption).
 * --no-story turns every companion story off. A package may also list a
 * story itself (e.g. for a post already scheduled): post_type "story",
 * one "image" (made 9:16 the same way unless it already is) or one "video".
 * A story and a feed post at the same minute do not stop each other (the
 * autopilot keeps the two surfaces apart the same way); story vs story and
 * feed vs feed still do. --story-preview=<dir> copies the made 9:16 pictures
 * there (also in --dry-run) so they can be looked at before anything is written.
 *
 * YOUTUBE SHORTS (Eszter TG 5519 via Nessa / Nova 24176: every FB/IG video goes to YouTube too). A video post
 * (a reel, a Facebook feed video, or platform "none": YouTube only, as posts 904 / 906 / 909 were made) may carry
 *   "youtube": {"title": "...",                       required, <= 100, no < or >
 *               "description": "...",                 optional, the post's text when left out, <= 5000
 *               "contains_synthetic_media": true|false   REQUIRED, the "generated content" disclosure, no default
 *               "privacy_status": "public"|"unlisted"|"private",   optional: left out, ESZTER chooses it
 *               "made_for_kids": true|false}          optional: left out, Eszter answers it
 * The leg is saved on the SAME post with the composer's own endpoint (innosocial_video_platforms.php save_legs),
 * so ONE review link approves every network; VideoTargets checks it again at approval (privacy and made-for-kids
 * must be answered there, YouTube's own rule) and before sending. The channel is the workspace's one active YouTube
 * account (innosocial_platform_accounts), never a guess: none or two stop the run. A Short is vertical or square and
 * <= 180 s; the server has no ffprobe, the wrapper measures it. The saved leg is read back before the review link.
 * Platform "none" (YouTube only): post_type video, the video, a "youtube" leg, no picture; the app never counts it
 * against a Meta page (no check_conflicts), two "none" posts at one minute still stop each other here.
 * "tiktok": the same pattern, OFF until the TikTok production review is through and the workspace has a TikTok
 * account (TIKTOK_ENABLED); a package that asks for it stops.
 *
 * PINTEREST (Zsolt TG 24093/24097 via Nova 24319: every 21napalatt video goes to Pinterest too, plus picture pins).
 * The app pins pictures AND videos (VideoTargets::save: "Pinterest takes both"; VideoLegPublisher::sendPinterest: no
 * video -> an image Pin of the post's first picture, a video -> a video Pin, the post's first picture its cover). A post
 * with a picture or a video (single_image, carousel: its FIRST picture only, reel, Facebook video; or platform "none":
 * Pinterest only, post_type single_image or video, a video may carry one "cover") may carry
 *   "pinterest": {"board_id": "<numeric id>",             required, one of the account's boards
 *                 "title": "...",                         required, <= 100
 *                 "description": "...",                   optional, the post's text when left out, <= 800
 *                 "link": "https://...",                  required (Eszter: every pin goes somewhere), <= 2048
 *                 "alt_text": "...",                      optional, <= 500
 *                 "ai_modified": true|false}              optional, false when left out (Pinterest's AI label)
 * = VideoTargets::normalise('pinterest') and validatePinterest(). The board is checked LIVE, with the app's own rules:
 * after save_legs the composer's post_legs endpoint lists the account's boards now and runs validatePinterest (board,
 * lengths, the video measured by the server's ffmpeg: 4 s..15 min, 1:2..1.91:1); any problem stops, the post stays
 * DRAFT. Boards are never stored (Pinterest's developer guidelines).
 * A PIN FOR A POST THAT IS ALREADY THERE: a package item {"add_pinterest_to": <post id>, "pinterest": {...}} with no
 * media of its own; the picture or video is the post's.
 *   - pending_review: the leg goes on THAT post (save_legs, its other legs sent back unchanged and read back), so its
 *     own review link approves it; the link is printed (a new one only if it has no live one).
 *   - approved: the post is NOT reopened (that would undo Eszter's approval). A companion post: platform none, the
 *     SAME scheduled_at, the same video / picture bytes (md5), the Pinterest leg, its own pending_review and link.
 *   - published (failed, partial, publishing): the same companion, at "scheduled_at_local", which is then required.
 *   - draft or rejected: stops (not finished / refused by Eszter).
 * ONE PIN PER MINUTE: two posts at one minute that share a video or pin channel (YouTube, Pinterest) are a duplicate
 * and stop the run, whatever their Meta platform -- a reel, its Facebook video and its YouTube copy at 20:00 are one
 * video, and it gets one pin. Pick one of them.
 */

if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }

$api = getcwd();
foreach (['config.php', 'jwt_helper.php', 'innosocial_lib/AccessControl.php', 'innosocial_lib/PostReadiness.php', 'innosocial_lib/PostImages.php'] as $f) {
    if (!is_file("$api/$f")) {
        fwrite(STDERR, "STOP: run this from the InnoWorx api directory ($f not found in $api)\n");
        exit(1);
    }
}
require_once "$api/config.php";
require_once "$api/jwt_helper.php";
require_once "$api/innosocial_lib/AccessControl.php";
require_once "$api/innosocial_lib/PostReadiness.php";
require_once "$api/innosocial_lib/PostImages.php";

$opt = getopt('', ['json:', 'img-dir::', 'user::', 'base-url::', 'expect-page:', 'expect-ig::', 'expiry-days::', 'dry-run', 'temp-grant', 'status', 'no-story', 'story-preview::']);
if (empty($opt['json']) || empty($opt['expect-page'])) {
    fwrite(STDERR, "usage: php innosocial-posztok.php --json=<posztok.json> --expect-page=<facebook_page_id> [--expect-ig=<ig_business_id>] [--dry-run|--status] [--temp-grant] [--img-dir=] [--user=18] [--base-url=https://app.innoworx.hu] [--expiry-days=]\n");
    exit(2);
}
$dryRun = isset($opt['dry-run']);
$statusOnly = isset($opt['status']);
$tempGrant = isset($opt['temp-grant']);
$userId = (int) ($opt['user'] ?? 18);
$baseUrl = rtrim((string) ($opt['base-url'] ?? 'https://app.innoworx.hu'), '/');
$imgDir = rtrim((string) ($opt['img-dir'] ?? dirname((string) $opt['json'])), '/');
$expectPage = (string) $opt['expect-page'];
$expectIg = (string) ($opt['expect-ig'] ?? '');

const PLATFORMS = ['facebook', 'instagram', 'both', 'none'];   // none = no Meta leg: the post's video channels only
const YOUTUBE_KEYS = ['title', 'description', 'contains_synthetic_media', 'privacy_status', 'made_for_kids'];
const YOUTUBE_PRIVACY = ['public', 'unlisted', 'private'];   // = VideoTargets::YOUTUBE_PRIVACY
const TIKTOK_ENABLED = false;                                  // Nova 24176: off until the production review and a ws account
const TYPES = ['single_image', 'carousel', 'text_only', 'reel', 'story', 'video'];   // = ALLOWED_POST_TYPES (innosocial_calendar.php)
const LEG_TYPES = ['facebook' => ['single_image', 'carousel', 'text_only', 'video', 'story'],   // = innosocialLabKikotes
                   'instagram' => ['single_image', 'carousel', 'reel', 'story']];
const VIDEO_MIMES = ['video/mp4', 'video/quicktime'];   // = VIDEO_ALLOWED_MIMES (innosocial_video.php)
const POST_KEYS = ['platform', 'post_type', 'post_type_facebook', 'post_type_instagram', 'scheduled_at_local', 'text', 'image', 'images',
                   'video', 'cover', 'link_url', 'first_comment', 'hashtag_set_id', 'ig_story', 'youtube', 'tiktok', 'pinterest'];
const ADD_KEYS = ['add_pinterest_to', 'pinterest', 'scheduled_at_local'];
const PINTEREST_KEYS = ['board_id', 'title', 'description', 'link', 'alt_text', 'ai_modified'];
const PINTEREST_MAX = ['title' => 100, 'description' => 800, 'link' => 2048, 'alt_text' => 500];   // = VideoTargets::PINTEREST_*_MAX
const PIN_TYPES = ['single_image', 'carousel', 'reel', 'video'];   // a leg with a picture or a video
const VIDEO_MAX_BYTES = 300 * 1024 * 1024;           // = api/innosocial_video.php
const REEL_MAX_SECONDS = 90;                         // the composer refuses a longer Reel (the server does not measure)
const STORY_MAX_SECONDS = 60;                        // ... and a longer Story (innosocial_video.php header)
const STORY_W = 1080, STORY_H = 1920;                // 9:16
const CAROUSEL_MAX = 10;                      // MetaAdapter: "maximum 10 kép"

function out(string $s = ''): void { echo $s, "\n"; }
function stop(string $s): void { fwrite(STDERR, "STOP: $s\n"); exit(1); }
// = _platformsOverlap, for two posts that both have a Meta leg
function overlaps(string $a, string $b): bool { return $a === 'both' || $b === 'both' || $a === $b; }
function surface(string $type): string { return $type === 'story' ? 'story' : 'feed'; }
// Two posts at one minute duplicate each other when they share a video or pin channel (a second YouTube upload, a second
// Pin), or, both with a Meta leg, on one surface with overlapping platforms. A 'none' post crowds no Meta page (the app's
// rule). Each side: ['platform' => ..., 'surface' => ..., 'providers' => [...]].
function duplicates(array $a, array $b): bool
{
    if (array_intersect($a['providers'], $b['providers'])) return true;
    return $a['platform'] !== 'none' && $b['platform'] !== 'none' && $a['surface'] === $b['surface'] && overlaps($a['platform'], $b['platform']);
}
function sameSettings(array $a, array $b): bool { ksort($a); ksort($b); return $a === $b; }

/** The Pinterest leg as VideoTargets::normalise('pinterest') stores it, with the app's limits; the board is checked live later. */
function pinterestLeg($pin, string $n, string $text, PDO $db, int $accountId): array
{
    if (!is_array($pin)) stop("post $n: \"pinterest\" is an object");
    foreach (array_keys($pin) as $k) if (!in_array($k, PINTEREST_KEYS, true)) stop("post $n pinterest: unknown key \"$k\" (known: " . implode(', ', PINTEREST_KEYS) . ')');
    $s = ['board_id' => trim((string) ($pin['board_id'] ?? '')), 'title' => trim((string) ($pin['title'] ?? '')),
          'description' => array_key_exists('description', $pin) ? (string) $pin['description'] : $text,
          'link' => trim((string) ($pin['link'] ?? '')), 'alt_text' => trim((string) ($pin['alt_text'] ?? '')), 'ai_modified' => $pin['ai_modified'] ?? false];
    if (!preg_match('/^\d{6,30}$/', $s['board_id'])) stop("post $n pinterest: board_id is the board's numeric id, as a string");
    if ($s['title'] === '') stop("post $n pinterest: the title is required");
    foreach (PINTEREST_MAX as $k => $max) {
        if (mb_strlen($s[$k]) > $max) stop("post $n pinterest: $k is at most $max characters (" . mb_strlen($s[$k]) . ')' . ($k === 'description' && !array_key_exists('description', $pin) ? ' -- it is the post\'s text; give "description"' : ''));
    }
    if (!preg_match('#^https://\S+$#i', $s['link'])) stop("post $n pinterest: link is required, an https address (every pin goes somewhere, Eszter's rule)");
    if (!is_bool($s['ai_modified'])) stop("post $n pinterest: ai_modified is true or false (or leave it out: false)");
    $pa = $db->prepare("SELECT id, display_name FROM innosocial_platform_accounts WHERE meta_account_id = ? AND provider = 'pinterest' AND active = 1");
    $pa->execute([$accountId]);
    $rows = $pa->fetchAll(PDO::FETCH_ASSOC);
    if (count($rows) !== 1) stop("post $n pinterest: workspace $accountId has " . count($rows) . ' active Pinterest account(s); exactly one is needed (which one is not this script\'s guess)');
    return ['platform_account_id' => (int) $rows[0]['id'], 'settings' => $s, 'account' => (string) $rows[0]['display_name']];
}

/**
 * The 9:16 story picture from a feed picture: the whole picture at the full 1080 width (or the full 1920 height when
 * it is taller than 9:16), centred, on a blurred, darkened copy of itself that covers the canvas. Nothing is cropped
 * from the picture itself: the returned 'fit' is where it sits, and the caller checks it lies inside the canvas.
 */
function storyCanvas(string $src, string $dir): array
{
    if (!function_exists('imagecreatetruecolor') || !function_exists('imagejpeg')) stop('the story picture needs PHP GD with JPEG support on this host; or leave "ig_story" off');
    $im = @imagecreatefromstring((string) file_get_contents($src));
    if (!$im) stop('story: GD cannot read ' . basename($src));
    $w = imagesx($im); $h = imagesy($im);
    // background: cover the canvas, blurred in stages (a single tiny->full upscale shows blocks), then darkened
    $cover = max(STORY_W / $w, STORY_H / $h);
    $cw = STORY_W / $cover; $chh = STORY_H / $cover;
    $small = imagecreatetruecolor(54, 96);
    imagecopyresampled($small, $im, 0, 0, (int) round(($w - $cw) / 2), (int) round(($h - $chh) / 2), 54, 96, (int) round($cw), (int) round($chh));
    for ($i = 0; $i < 6; $i++) imagefilter($small, IMG_FILTER_GAUSSIAN_BLUR);
    $mid = imagescale($small, 270, 480, IMG_BICUBIC);
    for ($i = 0; $i < 12; $i++) imagefilter($mid, IMG_FILTER_GAUSSIAN_BLUR);
    $canvas = imagescale($mid, STORY_W, STORY_H, IMG_BILINEAR_FIXED);
    for ($i = 0; $i < 4; $i++) imagefilter($canvas, IMG_FILTER_GAUSSIAN_BLUR);
    imagefilter($canvas, IMG_FILTER_BRIGHTNESS, -30);
    // foreground: contain, never crop
    $fit = min(STORY_W / $w, STORY_H / $h);
    $fw = (int) round($w * $fit); $fh = (int) round($h * $fit);
    $fx = (int) floor((STORY_W - $fw) / 2); $fy = (int) floor((STORY_H - $fh) / 2);
    imagecopyresampled($canvas, $im, $fx, $fy, 0, 0, $fw, $fh, $w, $h);
    $out = $dir . '/story-' . pathinfo($src, PATHINFO_FILENAME) . '.jpg';
    if (!imagejpeg($canvas, $out, 92)) stop("story: could not write $out");
    imagedestroy($im); imagedestroy($small); imagedestroy($mid); imagedestroy($canvas);
    $info = getimagesize($out);
    return ['path' => $out, 'w' => $info[0], 'h' => $info[1], 'bytes' => filesize($out), 'md5' => md5_file($out),
            'from' => basename($src) . " {$w}x{$h}", 'fit' => [$fx, $fy, $fw, $fh]];
}

$db = getDB();
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
out('db: ' . $db->query('SELECT DATABASE()')->fetchColumn() . ' | mode: ' . ($statusOnly ? 'STATUS (read-only)' : ($dryRun ? 'DRY-RUN (writes nothing)' : 'REAL')));

// ---------------------------------------------------------------- the package
$pkg = json_decode((string) @file_get_contents((string) $opt['json']), true);
if (!is_array($pkg) || empty($pkg['posts']) || !is_array($pkg['posts'])) stop('json unreadable or has no posts');
$sums = dirname((string) $opt['json']) . '/MD5SUMS';
if (is_file($sums)) {   // the package's own checksums: a file that changed on the way stops the run
    foreach (file($sums, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $line) {
        [$want, $f] = preg_split('/\s+/', trim($line), 2);
        $f = ltrim($f, '*');
        $fp = dirname((string) $opt['json']) . '/' . basename($f);
        if (!is_file($fp) || md5_file($fp) !== $want) stop("MD5SUMS: $f does not match the package (" . (is_file($fp) ? md5_file($fp) : 'missing') . " vs $want)");
    }
    out('MD5SUMS: every file of the package matches');
}
$clientId = (int) ($pkg['client_id'] ?? 0);
$accountId = (int) ($pkg['meta_account_id'] ?? 0);
if ($clientId <= 0 || $accountId <= 0) stop('client_id / meta_account_id missing in json');
if (($pkg['status'] ?? '') !== 'pending_review') stop('this script only leaves posts in pending_review; json says status=' . var_export($pkg['status'] ?? null, true));

$readback = function () use ($db, $accountId, $pkg): array {
    // the package's minutes, and the minutes of the posts it adds a pin to (a companion sits at its post's minute)
    $times = array_map(fn($p) => (string) ($p['scheduled_at_local'] ?? ''), $pkg['posts']);
    $ids = array_values(array_filter(array_map(fn($p) => is_int($p['add_pinterest_to'] ?? null) ? $p['add_pinterest_to'] : 0, $pkg['posts'])));
    if ($ids) {
        $q = $db->prepare('SELECT scheduled_at FROM innosocial_posts WHERE id IN (' . implode(',', array_fill(0, count($ids), '?')) . ')');
        $q->execute($ids);
        $times = array_merge($times, $q->fetchAll(PDO::FETCH_COLUMN));
    }
    $times = array_values(array_unique(array_filter($times)));
    if (!$times) return [];
    $in = implode(',', array_fill(0, count($times), '?'));
    $st = $db->prepare("
        SELECT p.id, p.status, p.scheduled_at, p.platform, p.post_type, p.client_id, p.meta_account_id,
               p.created_by, p.approved_at, LEFT(p.text_content, 50) AS text_start,
               (SELECT COUNT(*) FROM innosocial_generated_images g WHERE g.post_id = p.id AND g.picked = 1) AS picked_count,
               (SELECT GROUP_CONCAT(CONCAT(g.display_order, ':', g.file_ref) ORDER BY g.display_order, g.id SEPARATOR ' ')
                  FROM innosocial_generated_images g WHERE g.post_id = p.id AND g.picked = 1) AS picked_images,
               (SELECT COUNT(*) FROM innosocial_post_media m WHERE m.post_id = p.id) AS media_rows,
               (SELECT GROUP_CONCAT(CONCAT(t.provider, ':', t.leg_status) SEPARATOR ' ') FROM innosocial_post_targets t WHERE t.post_id = p.id) AS legs,
               (SELECT GROUP_CONCAT(CONCAT(r.token, ' exp=', r.expires_at, ' UTC',
                                           IF(r.approved_at IS NULL, '', CONCAT(' approved=', r.approved_at)),
                                           IF(r.rejected_at IS NULL, '', CONCAT(' rejected=', r.rejected_at)))
                                    SEPARATOR ' | ')
                  FROM innosocial_review_links r WHERE r.post_id = p.id) AS review_links
          FROM innosocial_posts p
         WHERE p.meta_account_id = ? AND p.scheduled_at IN ($in)
         ORDER BY p.scheduled_at, p.platform, p.id");
    $st->execute(array_merge([$accountId], $times));
    return $st->fetchAll(PDO::FETCH_ASSOC);
};

if ($statusOnly) {
    out(json_encode($readback(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
    exit(0);
}

// ---------------------------------------------------------------- preflight (read-only)
$acc = $db->prepare('SELECT id, client_id, facebook_page_id, instagram_business_account_id, page_name, active FROM innosocial_meta_accounts WHERE id = ?');
$acc->execute([$accountId]);
$accRow = $acc->fetch(PDO::FETCH_ASSOC);
if (!$accRow) stop("meta account $accountId not found");
out("account $accountId: page_name=" . $accRow['page_name'] . ' facebook_page_id=' . $accRow['facebook_page_id']
    . ' instagram_business_account_id=' . ($accRow['instagram_business_account_id'] ?: '-') . ' client_id=' . $accRow['client_id'] . ' active=' . $accRow['active']);
if ((int) $accRow['client_id'] !== $clientId) stop("account $accountId belongs to client {$accRow['client_id']}, not $clientId");
if ((string) $accRow['facebook_page_id'] !== $expectPage) stop("account $accountId is page {$accRow['facebook_page_id']}, expected $expectPage");
if ((int) $accRow['active'] !== 1) stop("account $accountId is not active");

$u = $db->prepare('SELECT id, email, role, permissions FROM users WHERE id = ?');
$u->execute([$userId]);
$userRow = $u->fetch(PDO::FETCH_ASSOC);
if (!$userRow) stop("user $userId not found");
$perms = is_string($userRow['permissions']) ? json_decode($userRow['permissions'], true) : $userRow['permissions'];
$isAdmin = $userRow['role'] === 'admin';
if (!$isAdmin && (($perms['innosocial'] ?? false) !== true)) stop("user $userId has no innosocial permission; not changing that");
$hasAccess = InnoSocialAccessControl::userHasAccountAccess($userId, $accountId);
out("user $userId: role={$userRow['role']} innosocial=" . (($perms['innosocial'] ?? false) === true ? 'yes' : 'no') . ' account_access=' . ($hasAccess ? 'yes' : 'NO'));
if (!$hasAccess && !$tempGrant && !$dryRun) stop("user $userId has no access to account $accountId. Re-run with --temp-grant to add it for this run only (RBAC bypass, removed at the end).");

$storyOn = !isset($opt['no-story']);   // a companion story is made only where "ig_story": true asks for it
$storyDir = null;   // the made 9:16 pictures live here for the run (removed at the end), copied to --story-preview
$storyPreview = isset($opt['story-preview']) ? rtrim((string) $opt['story-preview'], '/') : '';
if ($storyPreview !== '' && !is_dir($storyPreview)) stop("--story-preview: $storyPreview is not a directory");
$madeStory = function (string $src) use (&$storyDir, $storyPreview): array {
    if ($storyDir === null) {
        $storyDir = sys_get_temp_dir() . '/innosocial-story-' . getmypid() . '-' . bin2hex(random_bytes(4));
        if (!mkdir($storyDir, 0700)) stop("story: cannot make $storyDir");
        register_shutdown_function(function () use ($storyDir): void {
            foreach (glob("$storyDir/*") ?: [] as $f) @unlink($f);
            @rmdir($storyDir);
        });
    }
    $s = storyCanvas($src, $storyDir);
    [$fx, $fy, $fw, $fh] = $s['fit'];
    if ($s['w'] !== STORY_W || $s['h'] !== STORY_H) stop('story: made ' . "{$s['w']}x{$s['h']}" . ', not ' . STORY_W . 'x' . STORY_H);
    if ($fx < 0 || $fy < 0 || $fx + $fw > STORY_W || $fy + $fh > STORY_H) stop('story: the picture would be cropped (' . implode(',', $s['fit']) . ')');
    if ($storyPreview !== '') copy($s['path'], $storyPreview . '/' . basename($s['path']));
    return $s;
};
$checkVideo = function (array $p, string $n, ?int $maxSeconds, string $why) use ($imgDir): array {
    $vp = $imgDir . '/' . basename((string) ($p['video'] ?? ''));
    if (empty($p['video']) || !is_file($vp)) stop("post $n: video not found: $vp");
    $vmime = mime_content_type($vp) ?: '';
    if (!in_array($vmime, VIDEO_MIMES, true)) stop("post $n: the video is '$vmime', the app takes " . implode(' / ', VIDEO_MIMES));
    if (filesize($vp) > VIDEO_MAX_BYTES) stop("post $n: the video is over 300 MB");
    $dur = null;
    if (trim((string) @shell_exec('command -v ffprobe')) !== '') $dur = (float) trim((string) shell_exec('ffprobe -v error -show_entries format=duration -of csv=p=0 ' . escapeshellarg($vp)));
    if ($dur !== null && $maxSeconds !== null && $dur > $maxSeconds) stop("post $n: the video is {$dur} s, over $maxSeconds ($why)");
    return ['path' => $vp, 'mime' => $vmime, 'bytes' => filesize($vp), 'md5' => md5_file($vp), 'seconds' => $dur];
};
$posts = [];
$seenKeys = [];
// the package must not hold two duplicate posts at one minute (duplicates()), and the account must not have one
// already, any status. A pin added to a post that is there counts only its new channel, and that post is not its own
// duplicate.
$register = function (array $e) use (&$seenKeys, $db, $accountId): void {
    [$n, $when] = [$e['n'], $e['when']];
    $me = ['platform' => $e['kind'] === 'add' ? 'none' : $e['platform'], 'surface' => surface($e['type']), 'providers' => array_keys($e['video_legs'])];
    foreach ($seenKeys as [$w2, $other, $n2]) {
        if ($w2 === $when && duplicates($me, $other)) stop("post $n and post $n2 at $when are duplicates (" . (array_intersect($me['providers'], $other['providers'])
            ? 'both go to ' . implode(', ', array_intersect($me['providers'], $other['providers'])) . ': one video gets one pin / one upload, pick one'
            : "{$me['surface']} posts on overlapping platforms ({$me['platform']} / {$other['platform']})") . ')');
    }
    $seenKeys[] = [$when, $me, $n];
    $dup = $db->prepare('SELECT id, status, platform, post_type FROM innosocial_posts WHERE meta_account_id = ? AND scheduled_at = ? AND id <> ?');
    $dup->execute([$accountId, $when, (int) ($e['id'] ?? 0)]);
    $prov = $db->prepare('SELECT provider FROM innosocial_post_targets WHERE post_id = ?');
    $dupRows = array_values(array_filter($dup->fetchAll(PDO::FETCH_ASSOC), function ($r) use ($me, $prov) {
        $prov->execute([(int) $r['id']]);
        return duplicates($me, ['platform' => (string) $r['platform'], 'surface' => surface((string) $r['post_type']), 'providers' => $prov->fetchAll(PDO::FETCH_COLUMN)]);
    }));
    if ($dupRows) stop("post $n: account $accountId already has a post at $when that this one duplicates (an overlapping {$me['surface']} post, or the same channel: "
        . implode(', ', $me['providers'] ?: ['-']) . '): ' . json_encode($dupRows) . ' -- nothing written');
};
$webRoot = dirname($api); // file_ref is "/api/uploads/..." under the site root
$futureCheck = function (string $when, string $n): void {
    $ts = strtotime($when);
    if ($ts === false || date('Y-m-d H:i:s', $ts) !== $when) stop("post $n: scheduled_at_local must be 'Y-m-d H:i:s' local time, got '$when'");
    if ($ts < time() + 15 * 60) stop("post $n: $when is not at least 15 minutes in the future");
};
// {"add_pinterest_to": <post id>, "pinterest": {...}}: a pin for a post that is already there (see the header)
$addPinterest = function (array $p, string $n) use ($db, $accountId, $clientId, $webRoot, $futureCheck): array {
    foreach (array_keys($p) as $k) if (!in_array($k, ADD_KEYS, true) && !in_array($k, ['sor', 'source', 'note'], true) && !str_starts_with((string) $k, '_')) stop("post $n: unknown key \"$k\" next to add_pinterest_to (known: " . implode(', ', ADD_KEYS) . ')');
    $srcId = $p['add_pinterest_to'];
    if (!is_int($srcId) || $srcId <= 0) stop("post $n: add_pinterest_to is a post id (a number)");
    if (!isset($p['pinterest'])) stop("post $n: add_pinterest_to needs a \"pinterest\" leg");
    $q = $db->prepare('SELECT id, client_id, meta_account_id, status, platform, post_type, post_type_facebook, post_type_instagram, scheduled_at, text_content FROM innosocial_posts WHERE id = ?');
    $q->execute([$srcId]);
    $src = $q->fetch(PDO::FETCH_ASSOC);
    if (!$src || (int) $src['meta_account_id'] !== $accountId || (int) $src['client_id'] !== $clientId) stop("post $n: post $srcId is not one of workspace $accountId / client $clientId's posts");
    $lt = $db->prepare('SELECT provider, platform_account_id, settings, leg_status FROM innosocial_post_targets WHERE post_id = ? ORDER BY provider');
    $lt->execute([$srcId]);
    $srcLegs = [];
    foreach ($lt->fetchAll(PDO::FETCH_ASSOC) as $r) $srcLegs[$r['provider']] = $r;
    if (isset($srcLegs['pinterest'])) stop("post $n: post $srcId already has a Pinterest leg ({$srcLegs['pinterest']['leg_status']}) -- nothing written");
    $types = array_values(array_filter([$src['post_type'], $src['post_type_facebook'], $src['post_type_instagram']]));
    if (!array_intersect($types, PIN_TYPES) && $src['platform'] !== 'none') stop("post $n: post $srcId is a " . implode('/', $types) . ' post; a pin is made from a picture or video post');
    // the media the publisher resolves: the first video (Publisher::resolveFirstVideoUrl), the pictures (PostImages)
    $v = $db->prepare("SELECT file_ref FROM innosocial_post_media WHERE post_id = ? AND media_type = 'video' ORDER BY media_order ASC, id ASC LIMIT 1");
    $v->execute([$srcId]);
    $videoRef = (string) $v->fetchColumn();
    $imgRefs = array_map(fn($g) => (string) $g['file_ref'], PostImages::forPost($db, $srcId));
    if ($videoRef === '' && !$imgRefs) stop("post $n: post $srcId has no picture or video");
    $text = (string) $src['text_content'];
    $leg = pinterestLeg($p['pinterest'], $n, $text, $db, $accountId);
    $status = (string) $src['status'];
    $e = ['n' => $n, 'video_legs' => ['pinterest' => $leg], 'extra' => [], 'legs' => null, 'story_of' => null, 'source_id' => $srcId,
          'source' => "#$srcId $status {$src['platform']} {$src['post_type']} {$src['scheduled_at']}"];
    if ($status === 'pending_review') {
        // the leg goes on the post itself; its other legs are sent back as they are (save_legs replaces the set)
        if (isset($p['scheduled_at_local']) && $p['scheduled_at_local'] !== $src['scheduled_at']) stop("post $n: post $srcId is in review; the pin goes on it, at its own time {$src['scheduled_at']} -- leave scheduled_at_local out");
        foreach ($srcLegs as $prov => $r) if ($r['leg_status'] !== 'pending') stop("post $n: post $srcId's $prov leg is {$r['leg_status']}, not pending; not touching it");
        $futureCheck((string) $src['scheduled_at'], $n);
        $keep = [];
        foreach ($srcLegs as $prov => $r) $keep[$prov] = ['platform_account_id' => (int) $r['platform_account_id'], 'settings' => json_decode((string) $r['settings'], true) ?: []];
        return $e + ['kind' => 'add', 'id' => $srcId, 'platform' => (string) $src['platform'], 'type' => (string) $src['post_type'], 'when' => (string) $src['scheduled_at'],
                     'text' => $text, 'expiry' => max(14, (int) ceil((strtotime((string) $src['scheduled_at']) - time()) / 86400) + 1), 'imgs' => [], 'video' => null, 'keep_legs' => $keep, 'media_note' => ($videoRef !== '' ? 'its video' : 'its first picture') . ' (' . ($videoRef ?: $imgRefs[0]) . ')'];
    }
    if (in_array($status, ['draft', 'rejected'], true)) stop("post $n: post $srcId is $status (" . ($status === 'draft' ? 'not finished' : 'Eszter refused it') . '); no pin from it');
    if ($status === 'approved') {
        $when = (string) ($p['scheduled_at_local'] ?? $src['scheduled_at']);
    } else {
        if (!isset($p['scheduled_at_local'])) stop("post $n: post $srcId is $status (its time has passed); the pin needs its own \"scheduled_at_local\"");
        $when = (string) $p['scheduled_at_local'];
    }
    $futureCheck($when, $n);
    if (trim($text) === '') stop("post $n: post $srcId has no text for the companion post");
    // a companion: platform none, Pinterest only, the source's bytes; the approved post itself is not touched
    $file = function (string $ref) use ($webRoot, $n, $srcId): string {
        $path = $webRoot . $ref;
        if (!str_starts_with($ref, '/api/') || !is_file($path)) stop("post $n: post $srcId's file $ref is not a local file under $webRoot");
        return $path;
    };
    $video = null;
    if ($videoRef !== '') {
        $vp = $file($videoRef);
        $video = ['path' => $vp, 'mime' => mime_content_type($vp) ?: 'video/mp4', 'bytes' => filesize($vp), 'md5' => md5_file($vp), 'seconds' => null];
    }
    $imgs = [];
    if ($imgRefs) {   // the first picture: the pin itself, or the video pin's cover (the reel's)
        $ip = $file($imgRefs[0]);
        $info = @getimagesize($ip);
        if (!is_array($info)) stop("post $n: post $srcId's picture $imgRefs[0] is not readable");
        $imgs[] = ['path' => $ip, 'w' => $info[0], 'h' => $info[1], 'bytes' => filesize($ip), 'md5' => md5_file($ip)];
    }
    return $e + ['kind' => 'new', 'platform' => 'none', 'type' => $video ? 'video' : 'single_image', 'when' => $when, 'text' => $text,
                 'imgs' => $imgs, 'video' => $video, 'expiry' => max(14, (int) ceil((strtotime($when) - time()) / 86400) + 1),
                 'media_note' => 'a companion of #' . $srcId . ($video ? ': its video' . ($imgs ? ' + its cover' : '') : ': its first picture') . (count($imgRefs) > 1 ? ' (it has ' . count($imgRefs) . ' pictures; a pin takes the first)' : '')];
};
foreach ($pkg['posts'] as $i => $p) {
    $n = (string) ($i + 1);
    if (array_key_exists('add_pinterest_to', $p)) {
        $e = $addPinterest($p, $n);
        if (isset($opt['expiry-days'])) $e['expiry'] = max(1, min(90, (int) $opt['expiry-days']));
        $register($e);
        $posts[] = $e;
        continue;
    }
    $platform = (string) ($p['platform'] ?? $pkg['platform'] ?? '');
    $postType = (string) ($p['post_type'] ?? $pkg['post_type'] ?? '');
    if (!in_array($platform, PLATFORMS, true)) stop("post $n: platform '$platform' is not facebook/instagram/both/none");
    if (!in_array($postType, TYPES, true)) stop("post $n: post_type '$postType' -- the app takes " . implode(', ', TYPES));
    if (isset($p['story'])) stop("post $n: the key is \"ig_story\" (true/false), not \"story\"");
    // a typo must not be dropped silently; bookkeeping keys ("sor", "source", "note", "_...") are the packer's own
    foreach (array_keys($p) as $k) if (!in_array($k, POST_KEYS, true) && !in_array($k, ['sor', 'source', 'note'], true) && !str_starts_with((string) $k, '_')) stop("post $n: unknown key \"$k\" (known: " . implode(', ', POST_KEYS) . ')');

    // the legs: what each network publishes. Unsplit: the post's type on every network of the platform, with the app's
    // pair rule (innosocialPlatformKikotes). Split ("post_type_facebook" + "post_type_instagram", platform both): each
    // leg its own type, with the app's leg rule (innosocialLabKikotes) -- the composer's "külön típus hálózatonként".
    $split = array_key_exists('post_type_facebook', $p) || array_key_exists('post_type_instagram', $p);
    if ($platform === 'none') {
        // YouTube / Pinterest only (posts 904 / 906 / 909): no Meta leg; a video, or a picture for a pin
        if ($split) stop("post $n: platform none has no Meta legs");
        if (!isset($p['youtube']) && !isset($p['tiktok']) && !isset($p['pinterest'])) stop("post $n: platform none goes to its video and pin channels only, and this one names none (\"youtube\", \"pinterest\")");
        if ($postType !== 'video' && !($postType === 'single_image' && isset($p['pinterest']))) stop("post $n: platform none is post_type video (YouTube, Pinterest), or single_image for a picture pin");
        $fbLeg = $igLeg = '';
    } elseif ($split) {
        if ($platform !== 'both') stop("post $n: leg types (post_type_facebook / post_type_instagram) need platform both");
        $fbLeg = (string) ($p['post_type_facebook'] ?? ''); $igLeg = (string) ($p['post_type_instagram'] ?? '');
        if (!in_array($fbLeg, LEG_TYPES['facebook'], true)) stop("post $n: post_type_facebook '$fbLeg' -- the Facebook leg takes " . implode(', ', LEG_TYPES['facebook']));
        if (!in_array($igLeg, LEG_TYPES['instagram'], true)) stop("post $n: post_type_instagram '$igLeg' -- the Instagram leg takes " . implode(', ', LEG_TYPES['instagram']));
        if ($fbLeg === $igLeg) stop("post $n: both legs are '$fbLeg' -- that is a plain post_type '$fbLeg', leave the leg types out");
        // the post_type column decides which upload the app takes (a video only on reel/story/video): the leg with the video
        $postType = in_array($igLeg, ['reel', 'story'], true) && !empty($p['video']) ? $igLeg : (in_array($fbLeg, ['video', 'story'], true) && !empty($p['video']) ? $fbLeg : $fbLeg);
    } else {
        if ($postType === 'video' && $platform !== 'facebook') stop("post $n: a feed video goes to Facebook only (the app's rule); for Instagram it is a reel, for both use leg types");
        if ($postType === 'reel' && $platform !== 'instagram') stop("post $n: a reel goes to Instagram only (the app's rule); for both use leg types (facebook video + instagram reel)");
        if ($postType === 'text_only' && $platform !== 'facebook') stop("post $n: Instagram takes no post without a picture or video (text_only is Facebook only)");
        $fbLeg = $platform !== 'instagram' ? $postType : '';
        $igLeg = $platform !== 'facebook' ? $postType : '';
    }
    $legs = array_values(array_filter([$fbLeg, $igLeg]));
    if ($platform === 'none') $legs = [$postType];   // what the media rules below need: one video (a pin may add a cover), or one picture

    // the video channels' legs, saved on this same post (save_legs) and approved on its one review link
    if (isset($p['tiktok']) && !TIKTOK_ENABLED) stop("post $n: TikTok is off (Nova 24176: until the production review is through and the workspace has a TikTok account)");
    $videoLegs = [];
    if (isset($p['youtube'])) {
        $yt = $p['youtube'];
        if (!is_array($yt)) stop("post $n: \"youtube\" is an object");
        foreach (array_keys($yt) as $k) if (!in_array($k, YOUTUBE_KEYS, true)) stop("post $n youtube: unknown key \"$k\" (known: " . implode(', ', YOUTUBE_KEYS) . ')');
        if ($platform === 'none' ? $postType !== 'video' : (!in_array($fbLeg, ['video'], true) && !in_array($igLeg, ['reel'], true))) stop("post $n: a YouTube leg needs a video post (a reel, a Facebook feed video, or platform none with post_type video)");
        $title = trim((string) ($yt['title'] ?? ''));
        $desc = array_key_exists('description', $yt) ? (string) $yt['description'] : (string) ($p['text'] ?? '');
        if ($title === '' || mb_strlen($title) > 100) stop("post $n youtube: the title is required, at most 100 characters (" . mb_strlen($title) . ')');
        if (mb_strlen($desc) > 5000) stop("post $n youtube: the description is at most 5000 characters");
        if (preg_match('/[<>]/', $title . $desc)) stop("post $n youtube: no < or > in the title or the description (YouTube's rule)");
        if (!is_bool($yt['contains_synthetic_media'] ?? null)) stop("post $n youtube: contains_synthetic_media (the generated-content disclosure) must be given, true or false");
        if (isset($yt['privacy_status']) && !in_array($yt['privacy_status'], YOUTUBE_PRIVACY, true)) stop("post $n youtube: privacy_status is " . implode('/', YOUTUBE_PRIVACY) . ' (or leave it out: Eszter chooses)');
        if (array_key_exists('made_for_kids', $yt) && !is_bool($yt['made_for_kids'])) stop("post $n youtube: made_for_kids is true or false (or leave it out: Eszter answers)");
        $ya = $db->prepare("SELECT id, display_name FROM innosocial_platform_accounts WHERE meta_account_id = ? AND provider = 'youtube' AND active = 1");
        $ya->execute([$accountId]);
        $yaRows = $ya->fetchAll(PDO::FETCH_ASSOC);
        if (count($yaRows) !== 1) stop("post $n youtube: workspace $accountId has " . count($yaRows) . ' active YouTube account(s); exactly one is needed (which one is not this script\'s guess)');
        $settings = ['title' => $title, 'description' => $desc, 'contains_synthetic_media' => $yt['contains_synthetic_media']]
            + (isset($yt['privacy_status']) ? ['privacy_status' => $yt['privacy_status']] : [])
            + (array_key_exists('made_for_kids', $yt) ? ['made_for_kids' => $yt['made_for_kids']] : []);
        $videoLegs['youtube'] = ['platform_account_id' => (int) $yaRows[0]['id'], 'settings' => $settings, 'account' => (string) $yaRows[0]['display_name']];
    }
    $wantsStory = $storyOn && in_array($igLeg, ['single_image', 'carousel', 'reel'], true) && ($p['ig_story'] ?? $pkg['ig_story'] ?? false) === true;
    if (($p['ig_story'] ?? null) === true && !in_array($igLeg, ['single_image', 'carousel', 'reel'], true)) stop("post $n: \"ig_story\" is for an Instagram picture, carousel or reel post, this one's Instagram leg is '" . ($igLeg ?: 'none') . "'");
    if ($igLeg !== '') {
        $ig = (string) ($accRow['instagram_business_account_id'] ?? '');
        if ($ig === '') stop("post $n ($platform): account $accountId has no instagram_business_account_id; an Instagram post needs a meta account that carries one -- which one is not this script's guess");
        if ($expectIg === '') stop("post $n ($platform): pass --expect-ig=<instagram_business_account_id> so the IG target is checked, not assumed");
        if ($ig !== $expectIg) stop("post $n ($platform): account $accountId carries IG $ig, expected $expectIg");
    }

    $when = (string) ($p['scheduled_at_local'] ?? '');
    $futureCheck($when, $n);
    $ts = strtotime($when);
    $text = (string) ($p['text'] ?? '');
    $onlyStory = $legs === array_fill(0, count($legs), 'story');
    if (trim($text) === '' && !$onlyStory) stop("post $n: empty text");
    if (isset($p['pinterest'])) {   // a picture or a video to pin; the app pins a carousel's first picture
        if (!array_intersect($legs, PIN_TYPES)) stop("post $n: a Pinterest pin needs a picture or a video post, not '" . implode('/', $legs) . "'");
        $videoLegs['pinterest'] = pinterestLeg($p['pinterest'], $n, $text, $db, $accountId);
    }
    $pinCover = $platform === 'none' && $postType === 'video' && isset($p['pinterest']);   // a Pinterest-only video may carry its cover

    // extras the composer sends, with its own rules: a link is Facebook's, a first comment Instagram's
    $extra = [];
    if (isset($p['link_url'])) {
        if ($fbLeg === '' || in_array($fbLeg, ['story', 'video'], true)) stop("post $n: link_url goes with a Facebook picture / carousel / text post only (the Facebook leg here is '" . ($fbLeg ?: 'none') . "')");
        if (!preg_match('~^https?://[^\s]+$~', (string) $p['link_url'])) stop("post $n: link_url is not a URL");
        $extra['link_url'] = (string) $p['link_url'];
    }
    if (isset($p['first_comment'])) {
        if ($igLeg === '' || $igLeg === 'story') stop("post $n: first_comment is published on Instagram feed posts only (the Instagram leg here is '" . ($igLeg ?: 'none') . "')");
        if (trim((string) $p['first_comment']) === '') stop("post $n: empty first_comment");
        $extra['first_comment'] = (string) $p['first_comment'];
    }
    if (isset($p['hashtag_set_id'])) {
        $hs = $db->prepare('SELECT client_id, set_name FROM innosocial_hashtag_sets WHERE id = ?');
        $hs->execute([(int) $p['hashtag_set_id']]);
        $hsRow = $hs->fetch(PDO::FETCH_ASSOC);
        if (!$hsRow || (int) $hsRow['client_id'] !== $clientId) stop("post $n: hashtag set {$p['hashtag_set_id']} is not one of client $clientId's");
        $extra['hashtag_set_id'] = (int) $p['hashtag_set_id'];
    }

    // media: what the legs need, from the one image list and the one video the post carries (the app keeps one of each)
    $video = null;
    $needVideo = (bool) array_intersect($legs, ['reel', 'video']);
    if (!empty($p['video'])) {
        if (!$needVideo && !in_array('story', $legs, true)) stop("post $n: a video only goes with a reel, a feed video or a story, not with '" . implode('/', $legs) . "'");
        $limit = in_array('story', $legs, true) || $wantsStory ? [STORY_MAX_SECONDS, 'a story takes at most ' . STORY_MAX_SECONDS . ' s'] : (in_array('reel', $legs, true) ? [REEL_MAX_SECONDS, 'a reel takes at most ' . REEL_MAX_SECONDS . ' s'] : [null, '']);
        $video = $checkVideo($p, $n, $limit[0], $limit[1]);
        if ($video['seconds'] === null && $limit[0] !== null) out("post $n: the video's length is not measured on this host (no ffprobe); it needs <= {$limit[0]} s");
    } elseif ($needVideo) {
        stop("post $n: '" . implode('/', $legs) . "' needs a video");
    }
    $names = isset($p['images']) ? (array) $p['images'] : (isset($p['image']) ? [$p['image']] : []);
    if (isset($p['cover'])) {
        // a reel's cover; packages written for the earlier wrapper also list it under "images" (it shipped only those)
        if (!in_array('reel', $legs, true) && !$pinCover) stop("post $n: \"cover\" is a reel's cover (or a Pinterest-only video's)");
        if ($names && array_map('basename', $names) !== [basename((string) $p['cover'])]) stop("post $n: \"cover\" and \"images\" name different pictures; a reel post carries one picture");
        $names = [$p['cover']];
    }
    if ($legs === ['video'] && $names && !($pinCover && isset($p['cover']))) stop("post $n: a feed video publishes no picture; leave the picture out" . ($pinCover ? ' (a pin\'s cover goes in "cover")' : ''));
    $picLegs = array_intersect($legs, ['single_image', 'carousel']);
    if (in_array('carousel', $picLegs, true)) {
        if (count($names) < 2 || count($names) > CAROUSEL_MAX) stop("post $n: a carousel needs 2.." . CAROUSEL_MAX . ' images, got ' . count($names));
    } elseif ($picLegs) {
        if (count($names) !== 1) stop("post $n: a picture post needs exactly 1 image, got " . count($names));
    } elseif (in_array('text_only', $legs, true)) {
        if ($names || $video) stop("post $n: text_only carries no picture or video (the publisher would post the picture with it)");
    } elseif ($onlyStory) {
        if (count($names) + ($video ? 1 : 0) !== 1) stop("post $n: a story needs one image or one video, got " . count($names) . ' image(s)' . ($video ? ' and a video' : ''));
    } elseif (count($names) > 1) {
        stop("post $n: '" . implode('/', $legs) . "' takes at most one picture (a cover), got " . count($names));
    }
    if (in_array('text_only', $legs, true) && ($names || $video)) stop("post $n: the Facebook leg is text_only, but the post carries media -- the publisher would post it on Facebook too");
    if (in_array('story', $legs, true) && !$onlyStory && !$names && !$video) stop("post $n: the story leg needs the post's picture or video");
    if (count(array_unique(array_map('basename', $names))) !== count($names)) stop("post $n: the same image is listed twice");
    $imgs = [];
    foreach ($names as $k => $name) {
        $img = $imgDir . '/' . basename((string) $name);
        if (!is_file($img)) stop("post $n image " . ($k + 1) . ": not found: $img");
        $info = @getimagesize($img);
        if (!is_array($info) || !in_array($info[2], [IMAGETYPE_PNG, IMAGETYPE_JPEG, IMAGETYPE_WEBP], true)) stop("post $n image " . ($k + 1) . ": not a PNG/JPEG/WebP: $img");
        if (filesize($img) > 10 * 1024 * 1024) stop("post $n image " . ($k + 1) . ": over 10 MB: $img");
        $imgs[] = ['path' => $img, 'w' => $info[0], 'h' => $info[1], 'bytes' => filesize($img), 'md5' => md5_file($img)];
    }
    $ratios = array_unique(array_map(fn($x) => round($x['w'] / $x['h'], 3), $imgs));
    if (count($ratios) > 1) stop("post $n: the images do not share one aspect ratio (" . implode(', ', $ratios) . ')');
    // a story-only post's picture that is not 9:16 yet is extended the same way as a companion story's
    if ($onlyStory && $imgs && abs($imgs[0]['w'] / $imgs[0]['h'] - STORY_W / STORY_H) > 0.01) $imgs = [$madeStory($imgs[0]['path'])];

    $days = (int) ceil(($ts - time()) / 86400) + 1;
    $expiry = isset($opt['expiry-days']) ? (int) $opt['expiry-days'] : max(14, $days);
    $expiry = max(1, min(90, $expiry));

    $e = ['n' => $n, 'kind' => 'new', 'platform' => $platform, 'type' => $postType, 'legs' => $split ? ['facebook' => $fbLeg, 'instagram' => $igLeg] : null,
          'when' => $when, 'text' => $text, 'extra' => $extra, 'imgs' => $imgs, 'video' => $video, 'expiry' => $expiry, 'story_of' => null,
          'video_legs' => $videoLegs];
    if ($onlyStory && trim($text) === '') $e['text'] = "Story ($when). A sztorinak nincs képaláírása, ez belső megjegyzés.";
    $register($e);
    $posts[] = $e;

    if ($wantsStory) {
        // the companion story: same minute, Instagram, the reel's video or the feed picture made 9:16
        $s = ['n' => "$n-story", 'kind' => 'new', 'platform' => 'instagram', 'type' => 'story', 'legs' => null, 'when' => $when, 'extra' => [],
              'text' => "Story a(z) $when Instagram " . ($igLeg === 'reel' ? 'Reel' : 'poszt') . ' mellé (feed poszt: #FEED). A sztorinak nincs képaláírása, ez belső megjegyzés.',
              'imgs' => $igLeg === 'reel' ? [] : [$madeStory($imgs[0]['path'])], 'video' => $igLeg === 'reel' ? $video : null,
              'expiry' => $expiry, 'story_of' => $n, 'video_legs' => []];
        $register($s);
        $posts[] = $s;
    }
}

// ---------------------------------------------------------------- HTTP against the app's endpoints
$token = null;
$mint = function () use ($userRow, $perms, &$token, $baseUrl): void {
    $local = in_array((string) parse_url($baseUrl, PHP_URL_HOST), ['localhost', '127.0.0.1'], true);   // a local test pad only
    if (JWT_SECRET === 'YOUR_SECRET_KEY_HERE_CHANGE_ME' && !$local) stop('JWT_SECRET is the placeholder in CLI; the web server gets it elsewhere. Not guessing.');
    $token = JWT::encodeWithTtl(['sub' => (int) $userRow['id'], 'email' => $userRow['email'], 'role' => $userRow['role'], 'permissions' => $perms], 600);
};
$http = function (string $method, string $script, array $query, ?array $json = null, ?array $multipart = null) use ($baseUrl, &$token): array {
    $ch = curl_init("$baseUrl/api/$script?" . http_build_query($query));
    $headers = ['Authorization: Bearer ' . $token, 'Accept: application/json'];
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 90, CURLOPT_USERAGENT => 'innosocial-posztok-cli']);
    if ($method === 'POST') {
        curl_setopt($ch, CURLOPT_POST, true);
        if ($json !== null) {
            $headers[] = 'Content-Type: application/json';
            curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($json, JSON_UNESCAPED_UNICODE));
        } else {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $multipart ?? []);
        }
    }
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    $raw = curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err = curl_error($ch);
    curl_close($ch);
    if ($raw === false) return [0, ['error' => "curl: $err"]];
    $dec = json_decode((string) $raw, true);
    return [$code, is_array($dec) ? $dec : ['raw' => mb_substr((string) $raw, 0, 300)]];
};
// the app's check_conflicts does not know the surface; its hits are kept only when they are on this post's surface
// (story / feed), read from the posts table -- the autopilot keeps a 10:00 story and a 10:00 feed post apart the same way
$conflicts = function (string $when, string $platform, string $type) use ($http, $clientId, $accountId, $db): array {
    [$c, $r] = $http('GET', 'innosocial_calendar.php', ['action' => 'check_conflicts', 'client_id' => $clientId,
        'meta_account_id' => $accountId, 'platform' => $platform, 'scheduled_at' => $when]);
    if ($c === 401) stop('the endpoint refused the CLI-minted token (401): the web server and the CLI see different JWT_SECRETs, or the user is gone. Nothing written.');
    if ($c !== 200 || ($r['status'] ?? '') !== 'success') stop("check_conflicts $when $platform -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE));
    $hits = $r['data']['conflicts'] ?? [];
    if (!$hits) return [];
    $st = $db->prepare('SELECT post_type FROM innosocial_posts WHERE id = ?');
    return array_values(array_filter($hits, function ($h) use ($st, $type) {
        $st->execute([(int) $h['id']]);
        return surface((string) $st->fetchColumn()) === surface($type);
    }));
};

$granted = false;
$revoke = function () use (&$granted, $db, $userId, $accountId): void {
    if (!$granted) return;
    $d = $db->prepare('DELETE FROM innosocial_user_account_access WHERE user_id = ? AND meta_account_id = ?');
    $d->execute([$userId, $accountId]);
    out("RBAC: temporary access row for user $userId / account $accountId REMOVED (" . $d->rowCount() . ' row)');
    $granted = false;
};
register_shutdown_function($revoke); // also on stop()/exit/fatal

$describe = function (array $p): void {
    if ($p['kind'] === 'add') {
        out("post {$p['n']}: a Pinterest leg ADDED to post {$p['source']} (pending_review): the pin is {$p['media_note']}; its other legs ("
            . (implode(', ', array_keys($p['keep_legs'])) ?: 'none') . ') are sent back unchanged; its own review link approves the pin');
    } else {
        out("post {$p['n']}: {$p['platform']} {$p['type']}" . ($p['legs'] ? " (legs: facebook {$p['legs']['facebook']}, instagram {$p['legs']['instagram']})" : '') . " at $p[when] (Europe/Budapest), review link $p[expiry] days"
            . (isset($p['source_id']) ? " -- {$p['media_note']} ({$p['source']}, which is not touched)" : ''));
    }
    foreach ($p['extra'] as $k => $v) out("  $k: $v");
    if ($p['video']) out('  video: ' . basename($p['video']['path']) . ' ' . round($p['video']['bytes'] / 1048576, 1) . ' MB md5 ' . $p['video']['md5'] . ' duration ' . ($p['video']['seconds'] === null ? '(not measured: no ffprobe on this host)' : $p['video']['seconds'] . ' s'));
    foreach ($p['imgs'] as $k => $im) {
        out('  image ' . ($k + 1) . ': ' . basename($im['path']) . " {$im['w']}x{$im['h']} " . round($im['bytes'] / 1024) . ' KB'
            . (isset($im['fit']) ? " -- made from {$im['from']}: the picture at x={$im['fit'][0]} y={$im['fit'][1]} {$im['fit'][2]}x{$im['fit'][3]}, not cropped, md5 {$im['md5']}" : ''));
    }
    if ($p['story_of'] !== null) out("  companion story of post {$p['story_of']}: own pending_review, own review link");
    foreach ($p['video_legs'] as $prov => $l) {
        $st = $l['settings'];
        if ($prov === 'pinterest') {
            out("  pinterest leg -> {$l['account']} (account {$l['platform_account_id']}): board {$st['board_id']} (checked live after save_legs), title '{$st['title']}' (" . mb_strlen($st['title'])
                . '/100), description ' . mb_strlen($st['description']) . '/800 chars, link ' . $st['link'] . ', alt ' . mb_strlen($st['alt_text']) . '/500, AI label: ' . ($st['ai_modified'] ? 'yes' : 'no')
                . ($p['type'] === 'carousel' ? ' -- a carousel: the pin is its FIRST picture' : ''));
            continue;
        }
        out("  $prov leg -> {$l['account']} (account {$l['platform_account_id']}): title '{$st['title']}' (" . mb_strlen($st['title']) . '/100), description ' . mb_strlen($st['description'])
            . ' chars, generated content: ' . ($st['contains_synthetic_media'] ? 'yes' : 'no') . ', privacy: ' . ($st['privacy_status'] ?? 'ESZTER CHOOSES') . ', made for kids: '
            . (array_key_exists('made_for_kids', $st) ? ($st['made_for_kids'] ? 'yes' : 'no') : 'ESZTER ANSWERS'));
    }
    out('  text: ' . mb_strlen($p['text']) . ' chars | ' . str_replace("\n", ' / ', mb_substr($p['text'], 0, 90)) . '...');
};

// ---------------------------------------------------------------- dry run
if ($dryRun) {
    if ($hasAccess) $mint();
    foreach ($posts as $p) {
        out();
        $describe($p);
        out('  same account + minute: no duplicate (overlapping Meta post on this surface, or the same video / pin channel)');
        if ($p['kind'] === 'add') {
            out('  would: save_legs (' . implode(', ', array_keys($p['keep_legs'] + $p['video_legs'])) . ') -> read back every leg -> post_legs (the app\'s live board and media check) -> the post\'s review link');
            continue;
        }
        if ($p['platform'] === 'none') {
            out('  check_conflicts: not asked (a post with no Meta leg crowds no Meta page, the app\'s rule)');
        } elseif ($hasAccess) {
            $cf = $conflicts($p['when'], $p['platform'], $p['type']);
            out('  check_conflicts (app endpoint): ' . ($cf ? 'CONFLICT ' . json_encode($cf, JSON_UNESCAPED_UNICODE) : 'none'));
        } else {
            out('  check_conflicts: not called (user has no account access yet; the real run needs --temp-grant)');
        }
        out('  would: save_post(draft) -> ' . ($p['video'] ? 'upload the video (innosocial_video.php) -> ' : '') . 'upload ' . count($p['imgs']) . ' image(s) in order -> read back (count, order, md5' . ($p['video'] ? ', the video the publisher resolves' : '') . ') -> '
            . ($p['video_legs'] ? 'save_legs (' . implode(', ', array_keys($p['video_legs'])) . ') -> read back the leg -> ' : '')
            . (isset($p['video_legs']['pinterest']) ? 'post_legs (the app\'s live board and media check) -> ' : '') . 'set_status(pending_review) -> create_review_link');
    }
    out();
    out($hasAccess ? 'DRY-RUN OK: nothing written.' : "DRY-RUN OK: nothing written. The real run needs --temp-grant (user $userId has no row for account $accountId).");
    exit(0);
}

// ---------------------------------------------------------------- real run
if (!$hasAccess) {
    InnoSocialAccessControl::grantAccountAccess($userId, $accountId, $userId);
    $granted = true;
    out("RBAC BYPASS: temporary access row inserted for user $userId / account $accountId; it is removed at the end of this run");
}
$mint();

foreach ($posts as $p) {   // every conflict check BEFORE the first write
    if ($p['platform'] === 'none' || $p['kind'] === 'add') continue;   // no new Meta leg: the app's check takes no 'none' and counts it against no page
    $cf = $conflicts($p['when'], $p['platform'], $p['type']);
    if ($cf) stop("post {$p['n']} $p[when] {$p['platform']}: check_conflicts found " . json_encode($cf, JSON_UNESCAPED_UNICODE) . ' -- nothing written');
}

// the app's own check of a saved Pinterest leg: the composer's post_legs lists the account's boards NOW and runs
// VideoTargets::validate (board, lengths, the video as the server's ffmpeg measures it). [error or '', board name]
$pinCheck = function (int $postId) use ($http, $accountId): array {
    [$c, $r] = $http('GET', 'innosocial_video_platforms.php', ['action' => 'post_legs', 'meta_account_id' => $accountId, 'post_id' => $postId]);
    if ($c !== 200 || ($r['status'] ?? '') !== 'success') return ["post_legs -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE), ''];
    foreach ((array) ($r['data']['legs'] ?? []) as $l) {
        if (($l['provider'] ?? '') !== 'pinterest') continue;
        if (!empty($l['problems'])) return ['the app refuses the Pinterest leg: ' . implode(' ', (array) $l['problems']) . (!empty($l['creator_error']) ? " ({$l['creator_error']})" : ''), ''];
        $board = array_values(array_filter((array) ($l['creator_info']['boards'] ?? []), fn($b) => (string) ($b['id'] ?? '') === (string) ($l['settings']['board_id'] ?? '')));
        if (!$board) return ['the board is not among the account\'s boards, listed now', ''];
        return ['', (string) ($board[0]['name'] ?? '')];
    }
    return ['post_legs shows no Pinterest leg', ''];
};
$liveLink = function (int $postId) use ($db, $baseUrl): string {
    $q = $db->prepare('SELECT token FROM innosocial_review_links WHERE post_id = ? AND approved_at IS NULL AND rejected_at IS NULL AND expires_at > ? ORDER BY id DESC LIMIT 1');
    $q->execute([$postId, gmdate('Y-m-d H:i:s')]);
    $t = (string) $q->fetchColumn();
    return $t === '' ? '' : "$baseUrl/r/$t";
};
$readLegs = function (int $postId) use ($db): array {
    $lt = $db->prepare('SELECT provider, platform_account_id, settings FROM innosocial_post_targets WHERE post_id = ? ORDER BY provider');
    $lt->execute([$postId]);
    $saved = [];
    foreach ($lt->fetchAll(PDO::FETCH_ASSOC) as $row) $saved[$row['provider']] = ['platform_account_id' => (int) $row['platform_account_id'], 'settings' => json_decode((string) $row['settings'], true) ?: []];
    return $saved;
};

$done = [];
$idOf = [];   // package post number -> post id, for the companion story's note
foreach ($posts as $p) {
    $n = $p['n'];
    out();
    if ($p['kind'] === 'add') {
        // a pin on a post in review: its legs + Pinterest, with the composer's endpoint; the app refuses it once approved (409)
        $postId = $p['id'];
        out("post $n (Pinterest added to #$postId {$p['platform']} {$p['type']} $p[when]):");
        $before = $readLegs($postId);
        foreach ($p['keep_legs'] as $prov => $l) {
            if (!isset($before[$prov]) || $before[$prov]['platform_account_id'] !== $l['platform_account_id'] || !sameSettings($before[$prov]['settings'], $l['settings'])) stop("post $n: post $postId's $prov leg changed since the check -- nothing written for it");
        }
        if (array_diff_key($before, $p['keep_legs'])) stop("post $n: post $postId got a new leg since the check (" . implode(', ', array_keys(array_diff_key($before, $p['keep_legs']))) . ') -- nothing written for it');
        $legsBody = $p['keep_legs'] + array_map(fn($l) => ['platform_account_id' => $l['platform_account_id'], 'settings' => $l['settings']], $p['video_legs']);
        ksort($legsBody);
        $restore = function (string $why) use ($http, $accountId, $postId, $p, $readLegs, $n): void {
            [$c, $r] = $http('POST', 'innosocial_video_platforms.php', ['action' => 'save_legs'], ['meta_account_id' => $accountId, 'post_id' => $postId, 'legs' => (object) $p['keep_legs']]);
            $back = $readLegs($postId);
            $ok = $c === 200 && array_keys($back) == array_keys($p['keep_legs']);
            stop("post $n: $why | the Pinterest leg was " . ($ok ? 'taken off again; post ' . $postId . ' has its legs as before' : 'NOT taken off (HTTP ' . $c . '): post ' . $postId . ' needs a look'));
        };
        [$c, $r] = $http('POST', 'innosocial_video_platforms.php', ['action' => 'save_legs'], ['meta_account_id' => $accountId, 'post_id' => $postId, 'legs' => $legsBody]);
        if ($c !== 200 || ($r['status'] ?? '') !== 'success') stop("post $n save_legs on #$postId -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . ' (409: Eszter approved it meanwhile; a companion is the way then) | nothing changed');
        $saved = $readLegs($postId);
        if (array_keys($saved) != array_keys($legsBody)) $restore('the saved legs are ' . json_encode(array_keys($saved)) . ', expected ' . json_encode(array_keys($legsBody)));
        foreach ($legsBody as $prov => $l) {
            if ($saved[$prov]['platform_account_id'] !== $l['platform_account_id'] || !sameSettings($saved[$prov]['settings'], $l['settings'])) $restore("the $prov leg reads back " . json_encode($saved[$prov], JSON_UNESCAPED_UNICODE) . ', not as sent');
        }
        out('  save_legs: ' . implode(', ', array_keys($legsBody)) . ' -- read back: every leg as sent, the old ones unchanged');
        [$err, $boardName] = $pinCheck($postId);
        if ($err !== '') $restore($err);
        out("  post_legs: the app accepts the pin (board \"$boardName\", listed now)");
        $url = $liveLink($postId);
        if ($url === '') {
            [$c, $r] = $http('POST', 'innosocial_calendar.php', ['action' => 'create_review_link'], ['post_id' => $postId, 'client_id' => $clientId, 'expiry_days' => $p['expiry']]);
            $path = (string) ($r['data']['public_path'] ?? '');
            if ($c !== 200 || $path === '') stop("post $n create_review_link -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId has the pin, in review, WITHOUT a live link");
            $url = $baseUrl . $path;
            out("  review link (it had no live one): $url");
        } else {
            out("  review link (its own, unchanged): $url");
        }
        $done[] = ['n' => $n, 'id' => $postId, 'platform' => $p['platform'], 'post_type' => '+pinterest', 'legs' => null, 'status' => 'pending_review',
                   'scheduled_at' => $p['when'], 'story_of' => null, 'video_ref' => null, 'file_refs' => [], 'review_url' => $url];
        continue;
    }
    out("post $n ({$p['platform']} {$p['type']} $p[when]):");
    if ($p['story_of'] !== null) $p['text'] = str_replace('#FEED', '#' . $idOf[$p['story_of']], $p['text']);

    [$c, $r] = $http('POST', 'innosocial_calendar.php', ['action' => 'save_post'], [
        'client_id' => $clientId, 'meta_account_id' => $accountId, 'platform' => $p['platform'],
        'post_type' => $p['type'], 'text_content' => $p['text'], 'scheduled_at' => $p['when'], 'status' => 'draft',
    ] + $p['extra'] + ($p['legs'] ? ['post_type_facebook' => $p['legs']['facebook'], 'post_type_instagram' => $p['legs']['instagram']] : []));
    $postId = (int) ($r['data']['id'] ?? 0);
    if ($c !== 200 || $postId <= 0) stop("post $n save_post -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . ' | created so far: ' . json_encode($done, JSON_UNESCAPED_SLASHES));
    out("  save_post: id=$postId status=draft");
    $idOf[$n] = $postId;
    // the row as the publisher will read it: platform, type, legs, extras
    $row = $db->prepare('SELECT platform, post_type, post_type_split, post_type_facebook, post_type_instagram, link_url, first_comment, hashtag_set_id FROM innosocial_posts WHERE id = ?');
    $row->execute([$postId]);
    $r0 = $row->fetch(PDO::FETCH_ASSOC);
    $wantRow = ['platform' => $p['platform'], 'post_type' => $p['type'], 'post_type_split' => $p['legs'] ? 1 : 0,
                'post_type_facebook' => $p['legs']['facebook'] ?? null, 'post_type_instagram' => $p['legs']['instagram'] ?? null,
                'link_url' => $p['extra']['link_url'] ?? null, 'first_comment' => $p['extra']['first_comment'] ?? null,
                'hashtag_set_id' => $p['extra']['hashtag_set_id'] ?? null];
    if ($p['legs'] && $p['legs']['facebook'] === $p['legs']['instagram']) $wantRow['post_type'] = $p['legs']['facebook'];
    foreach ($wantRow as $k => $v) {
        $got = $r0[$k] ?? null;
        if ($k === 'post_type_split') $got = (int) $got;
        if ($k === 'hashtag_set_id' && $got !== null) $got = (int) $got;
        if (!$p['legs'] && in_array($k, ['post_type_facebook', 'post_type_instagram'], true)) continue;   // derived by the app on an unsplit row
        if ($got !== $v) stop("post $n: the saved row has $k=" . var_export($got, true) . ', expected ' . var_export($v, true) . " | post $postId stays DRAFT");
    }
    out('  read back: platform, type' . ($p['legs'] ? ', legs fb=' . $p['legs']['facebook'] . ' ig=' . $p['legs']['instagram'] : '') . ($p['extra'] ? ', ' . implode(', ', array_keys($p['extra'])) : '') . ' as sent');

    $videoRef = null;
    if ($p['video']) {
        [$c, $r] = $http('POST', 'innosocial_video.php', ['action' => 'upload'], null, [
            'client_id' => (string) $clientId, 'post_id' => (string) $postId,
            'file' => new CURLFile($p['video']['path'], $p['video']['mime'], basename($p['video']['path'])),
        ]);
        $videoRef = (string) ($r['data']['file_ref'] ?? '');
        if ($c !== 200 || $videoRef === '') stop("post $n video upload -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId stays DRAFT without a video (cannot go out)");
        out("  video upload: $videoRef");
        // the video the publisher will send: its own query (Publisher::resolveFirstVideoUrl), and the bytes on disk
        $v = $db->prepare("SELECT file_ref FROM innosocial_post_media WHERE post_id = ? AND media_type = 'video' ORDER BY media_order ASC, id ASC LIMIT 1");
        $v->execute([$postId]);
        $first = (string) $v->fetchColumn();
        if ($first !== $videoRef) stop("post $n: the publisher's first video is '$first', not the uploaded $videoRef | post $postId stays DRAFT");
        if (!is_file($webRoot . $videoRef) || md5_file($webRoot . $videoRef) !== $p['video']['md5']) stop("post $n: the stored video's bytes differ from the package (md5) | post $postId stays DRAFT");
        out('  read back: the publisher resolves this video, bytes match the package (md5)');
    }
    foreach ($p['imgs'] as $k => $im) {   // sequential: the endpoint appends, so the order is the upload order
        [$c, $r] = $http('POST', 'innosocial_image.php', ['action' => 'upload'], null, [
            'client_id' => (string) $clientId, 'post_id' => (string) $postId,
            'file' => new CURLFile($im['path'], mime_content_type($im['path']) ?: 'image/png', basename($im['path'])),
        ]);
        $ref = (string) ($r['data']['image']['file_ref'] ?? '');
        if ($c !== 200 || $ref === '') stop("post $n upload of image " . ($k + 1) . " -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId stays DRAFT with $k image(s) (cannot go out)");
        out('  upload ' . ($k + 1) . ": $ref");
    }

    // what the publisher will send, read through the publisher's own source
    $got = PostImages::forPost($db, $postId);
    if (count($got) !== count($p['imgs'])) stop("post $n: PostImages::forPost returns " . count($got) . ' image(s), expected ' . count($p['imgs']) . " | post $postId stays DRAFT");
    $refs = [];
    foreach ($got as $k => $g) {
        $ref = (string) $g['file_ref'];
        $disk = $webRoot . $ref;
        if (!str_starts_with($ref, '/api/') || !is_file($disk)) stop("post $n: image " . ($k + 1) . " ($ref) is not a local file under $webRoot | post $postId stays DRAFT");
        if (md5_file($disk) !== $p['imgs'][$k]['md5']) stop("post $n: image slot " . ($k + 1) . ' holds ' . basename($ref) . ', not ' . basename($p['imgs'][$k]['path']) . " (md5) -- order or content differs | post $postId stays DRAFT");
        $refs[] = $ref;
    }
    out('  read back: ' . count($refs) . ' image(s), order and bytes match the package');

    // the video channels' legs, with the composer's own endpoint, on this post; read back before it goes to review
    if ($p['video_legs']) {
        $legsBody = array_map(fn($l) => ['platform_account_id' => $l['platform_account_id'], 'settings' => $l['settings']], $p['video_legs']);
        ksort($legsBody);   // the read-back below is ORDER BY provider
        [$c, $r] = $http('POST', 'innosocial_video_platforms.php', ['action' => 'save_legs'], ['meta_account_id' => $accountId, 'post_id' => $postId, 'legs' => $legsBody]);
        if ($c !== 200 || ($r['status'] ?? '') !== 'success') stop("post $n save_legs -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId stays DRAFT");
        $lt = $db->prepare('SELECT provider, platform_account_id, settings FROM innosocial_post_targets WHERE post_id = ? ORDER BY provider');
        $lt->execute([$postId]);
        $saved = [];
        foreach ($lt->fetchAll(PDO::FETCH_ASSOC) as $row) $saved[$row['provider']] = ['platform_account_id' => (int) $row['platform_account_id'], 'settings' => json_decode((string) $row['settings'], true) ?: []];
        if (array_keys($saved) != array_keys($legsBody)) stop("post $n: the saved legs are " . json_encode(array_keys($saved)) . ', expected ' . json_encode(array_keys($legsBody)) . " | post $postId stays DRAFT");
        foreach ($legsBody as $prov => $l) {
            if ($saved[$prov]['platform_account_id'] !== $l['platform_account_id']) stop("post $n: the $prov leg went to account {$saved[$prov]['platform_account_id']}, not {$l['platform_account_id']} | post $postId stays DRAFT");
            foreach ($l['settings'] as $k => $v) if (($saved[$prov]['settings'][$k] ?? null) !== $v) stop("post $n: the $prov leg's $k reads back " . json_encode($saved[$prov]['settings'][$k] ?? null, JSON_UNESCAPED_UNICODE) . ', expected ' . json_encode($v, JSON_UNESCAPED_UNICODE) . " | post $postId stays DRAFT");
        }
        out('  save_legs: ' . implode(', ', array_keys($legsBody)) . ' -- read back: account and every setting as sent');
        if (isset($legsBody['pinterest'])) {
            [$err, $boardName] = $pinCheck($postId);
            if ($err !== '') stop("post $n: $err | post $postId stays DRAFT");
            out("  post_legs: the app accepts the pin (board \"$boardName\", listed now)");
        }
    }

    [$c, $r] = $http('POST', 'innosocial_calendar.php', ['action' => 'set_status'], ['id' => $postId, 'client_id' => $clientId, 'status' => 'pending_review']);
    if ($c !== 200 || (int) ($r['data']['updated'] ?? 0) !== 1) stop("post $n set_status -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId stays DRAFT");
    out('  set_status: pending_review');

    [$c, $r] = $http('POST', 'innosocial_calendar.php', ['action' => 'create_review_link'], ['post_id' => $postId, 'client_id' => $clientId, 'expiry_days' => $p['expiry']]);
    $path = (string) ($r['data']['public_path'] ?? '');
    if ($c !== 200 || $path === '') stop("post $n create_review_link -> HTTP $c " . json_encode($r, JSON_UNESCAPED_UNICODE) . " | post $postId is pending_review WITHOUT a link");
    $url = $baseUrl . $path;
    out("  review link: $url ($p[expiry] days)");

    $done[] = ['n' => $n, 'id' => $postId, 'platform' => $p['platform'], 'post_type' => $p['type'], 'legs' => $p['legs'], 'status' => 'pending_review',
               'scheduled_at' => $p['when'], 'story_of' => $p['story_of'] === null ? null : $idOf[$p['story_of']],
               'video_ref' => $videoRef, 'file_refs' => $refs, 'review_url' => $url];
}

$revoke();

out();
out('REVIEW LINKS (a companion story is approved on its own link):');
foreach ($done as $d) out("  post {$d['n']} #{$d['id']} {$d['platform']} " . ($d['legs'] ? "fb:{$d['legs']['facebook']}+ig:{$d['legs']['instagram']}" : $d['post_type']) . " {$d['scheduled_at']}: {$d['review_url']}");
out();
out('RESULT:');
out(json_encode($done, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
out();
out('READBACK (SELECT on innosocial_posts / generated_images / post_media / review_links):');
out(json_encode($readback(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
