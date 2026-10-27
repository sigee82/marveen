#!/usr/bin/env python3
"""InnoSocial post package -> 21napalatt posts in PENDING_REVIEW with customer approval links (Nessa's own tool).

WHY (Zsolt, 2026-10-10, TG 19151): in a week Nessa sent Nova 33 messages only to get posts into InnoSocial.
Same uploader and flow Nova used (scripts/innosocial/innosocial-posztok.php, Bit's: draft -> upload in order -> read back
md5 -> set_status pending_review -> review link). NOTHING IS PUBLISHED: the script never sets 'approved' and never
calls publish_now; a post goes out only after Eszter approves it on the /r/<token> page.

Package = a folder under agents/nessa/ with posztok.json + the media files next to it:
  {"client_id": 55, "meta_account_id": 8, "status": "pending_review", "source": "<honnan>",
   "posts": [{"platform": "instagram"|"facebook"|"both",
              "post_type": "single_image"|"carousel"|"text_only"|"reel"|"video"|"story",
              "scheduled_at_local": "YYYY-MM-DD HH:MM:SS" (Budapest), "text": "<szo szerint>",
              "images": ["kep1.png", ...], "video": "x.mp4"|"x.mov", "cover": "borito.png" (reelnel, opcionalis),
              "link_url": "https://..." (FB), "first_comment": "..." (IG), "hashtag_set_id": <id>,
              "post_type_facebook" + "post_type_instagram" (both, halozatonkent mas tipus, pl. video + reel)}]}
  Amit az InnoSocial enged (a feltolto ugyanezt ellenorzi, es megall, ha nem): text_only es video (feed-video) csak
  Facebook; reel csak Instagram; story barhova (both = ugyanaz a story mindket helyre); kulon lab-tipus csak both-nal.

IG STORY (Nova 20325/20331): ALAPBOL NINCS. Egy Instagram kep-/lapozos posztnal vagy Reelnel "ig_story": true -> a feltolto
mellé tesz egy story-posztot ugyanarra az idopontra, sajat pending_review-val es SAJAT jovahagyo linkkel (Eszter azt is
kulon hagyja jova). Kepnel a feed-kep 9:16-ra kiterjesztve (vagas nelkul, elmosott hatteren), Reelnel ugyanaz a video
(max 60 mp). A csomag szintjen "ig_story": true = minden IG posztja. Kulon story is lehet (pl. mar fent levo poszthoz):
post_type "story", egy "images" kep vagy egy "video", ugyanarra az idopontra is.

YOUTUBE SHORTS (Eszter TG 5519 Nessan at, Nova 24176: minden FB/IG video menjen YouTube-ra is). Egy videos poszt (reel,
Facebook feed-video, vagy platform "none" = CSAK YouTube, ahogy a 904/906/909 keszult) kaphat
  "youtube": {"title": "<legfeljebb 100 karakter, < es > nelkul>",
              "description": "<opcionalis, alapbol a poszt szovege>",
              "contains_synthetic_media": true|false   KOTELEZO (generalt tartalom nyilatkozat),
              "privacy_status": "public"|"unlisted"|"private"   opcionalis -- ha nincs, ESZTER valasztja,
              "made_for_kids": true|false              opcionalis -- ha nincs, ESZTER jeloli}
A YouTube-lab UGYANARRA a posztra kerul, egy jovahagyo linkkel (Eszter egyszerre hagyja jova a Reelt/FB-videot es a
YouTube-ot). "Video + YouTube" egy hivasbol: a Reel / FB-video posztba ird bele a "youtube" kulcsot. Csak YouTube:
platform "none", post_type "video", a video es a "youtube" kulcs. A Short allo vagy negyzetes, legfeljebb 180 mp:
itt merem ffprobe-bal (a szerveren nincs). "tiktok": ugyanezen a mintan, de KI van kapcsolva, amig a production review
at nem megy es a ws 8-hoz nincs TikTok-fiok -- ha a csomag keri, megallok.

PINTEREST (Zsolt TG 24093/24097, Nova 24319: minden 21napalatt video Pinterestre is, plusz kepes pinek). Az InnoSocial
KEP-pint is tud (a poszt elso kepe) es video-pint is (a video, a borito a poszt elso kepe). Kepes poszt (single_image,
carousel: csak az ELSO kep), Reel, Facebook-video, vagy platform "none" = CSAK Pinterest (post_type "single_image" egy
keppel, vagy "video", opcionalis "cover" kep a pin boritojanak) kaphat
  "pinterest": {"board_id": "<a tabla szam-azonositoja, szovegkent>"   KOTELEZO (agents/nova-atadas/pinterest-tablak-ws8.tsv),
                "title": "<legfeljebb 100>"                          KOTELEZO,
                "description": "<legfeljebb 800, alapbol a poszt szovege>",
                "link": "https://..."                                KOTELEZO,
                "alt_text": "<legfeljebb 500>"                        opcionalis,
                "ai_modified": true|false                            opcionalis, alapbol false}
A tablat a szerver ELOBEN ellenorzi (a fiok mostani tablai), es a videot is (4 mp - 15 perc, 1:2 - 1,91:1).
MEGLEVO POSZTHOZ PIN: a posts listaban {"add_pinterest_to": <poszt id>, "pinterest": {...}}, media nelkul (a poszte).
  pending_review poszt: a pin UGYANARRA a posztra kerul, a sajat jovahagyo linkjen hagyja jova Eszter;
  approved poszt: NEM nyitom vissza, egy kiseropost megy (csak Pinterest, ugyanarra az idopontra, sajat link);
  mar kiment poszt: ugyanez, de "scheduled_at_local" kell hozza (az eredeti ido elmult);
  draft / rejected: megallok.
EGY VIDEO = EGY PIN: ha egy percben ket poszt ugyanarra a csatornara (YouTube, Pinterest) menne, megallok -- a 20:00-as
Reel, FB-video es YouTube-masolat ugyanaz a video, ezekbol EGYHEZ kerjen pint.

  innosocial-nessa.py <csomag-mappa> --proba    dry-run only (nothing written), shows what would happen
  innosocial-nessa.py <csomag-mappa>            dry-run, then the real run (pending_review), then status + links
"""
import base64
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

TIKTOK_ENABLED = False   # Nova 24176: a production review es egy ws-8 TikTok-fiok utan
YT_KEYS = {'title', 'description', 'contains_synthetic_media', 'privacy_status', 'made_for_kids'}
SHORTS_MAX_SEC = 180
PIN_KEYS = {'board_id', 'title', 'description', 'link', 'alt_text', 'ai_modified'}
PIN_MAX = {'title': 100, 'description': 800, 'link': 2048, 'alt_text': 500}   # = VideoTargets::PINTEREST_*_MAX
PIN_VIDEO_SEC = (4, 900)                                                      # = PINTEREST_VIDEO_MIN_SEC / MAX_SEC
BOARDS_TSV = '/Users/macmini/marveen/agents/nova-atadas/pinterest-tablak-ws8.tsv'

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOADER = os.path.join(HERE, 'innosocial', 'innosocial-posztok.php')
NESSA_DIR = '/Users/macmini/marveen/agents/nessa/'
CLIENT, ACCOUNT, PAGE, IG = 55, 8, '292200250940748', '17841400449301622'   # 21napalatt
SSH_KEY_ID = 'ssh-key-dc8b036ee89b5473'
HOST = 'napalatt@185.208.227.93'
LOG = os.path.join(HERE, 'state', 'innosocial-nessa.log')

HEAD = """#!/bin/bash
set -euo pipefail
cd /home/napalatt/app.innoworx.hu/api || { echo "NO PROD API DIR"; exit 1; }
T="$(mktemp -d "$HOME/nessa-is.XXXXXX")"
cleanup() { for f in "$T"/*; do [ -f "$f" ] && rm -f "$f"; done; rmdir "$T" 2>/dev/null || true; }
trap cleanup EXIT
"""
TAIL = """echo "== files ok (sha256): $(ls "$T" | wc -l) files"
A="--json=$T/posztok.json --img-dir=$T --expect-page=%s --expect-ig=%s"
echo "######## DRY RUN"
php "$T/innosocial-posztok.php" $A --dry-run </dev/null
""" % (PAGE, IG)
REAL = """echo "######## REAL RUN (pending_review, nothing published)"
php "$T/innosocial-posztok.php" $A --temp-grant </dev/null
echo "######## STATUS"
php "$T/innosocial-posztok.php" $A --status </dev/null
"""


def fail(msg):
    sys.exit('HIBA: ' + msg)


def szovegkapu(darabok, mufaj, ut):
    """The AI-slop text gate (scripts/hooks/szovegkapu.py) on what goes to Eszter. The SSH payload is invisible to the
    PreToolUse hook, so the call is here. Any failure stops the upload (fail-closed)."""
    try:
        sys.path.insert(0, os.path.join(HERE, 'hooks'))
        import szovegkapu as sk
        stop, jelez = sk.pipeline(darabok, '21napalatt', mufaj, ut)
    except Exception as e:
        fail(f'a szovegkapu nem futott ({type(e).__name__}: {e}); ugyfel fele meno uton megallok')
    if jelez:
        print(jelez)
    if stop:
        fail(stop)


def ffprobe_video(path):
    """(duration s, width, height) of the first video stream, or None when ffprobe is not here."""
    if not shutil.which('ffprobe'):
        return None
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height:stream_side_data=rotation:format=duration',
                        '-of', 'json', path], capture_output=True, text=True)
    j = json.loads(r.stdout or '{}')
    st = (j.get('streams') or [{}])[0]
    w, h = int(st.get('width') or 0), int(st.get('height') or 0)
    rot = next((abs(int(sd.get('rotation', 0))) for sd in st.get('side_data_list') or [] if 'rotation' in sd), 0)
    if rot in (90, 270):
        w, h = h, w
    return float((j.get('format') or {}).get('duration') or 0), w, h


def youtube_leg(i, p, d):
    """The YouTube leg's own checks, before anything is sent (the uploader checks them again on the server)."""
    yt = p['youtube']
    if not isinstance(yt, dict):
        fail(f'{i}. poszt: a "youtube" egy objektum')
    if set(yt) - YT_KEYS:
        fail(f'{i}. poszt youtube: ismeretlen kulcs: {sorted(set(yt) - YT_KEYS)}')
    title = (yt.get('title') or '').strip()
    if not title or len(title) > 100:
        fail(f'{i}. poszt youtube: a cim kotelezo, legfeljebb 100 karakter (most {len(title)})')
    if not isinstance(yt.get('contains_synthetic_media'), bool):
        fail(f'{i}. poszt youtube: a "contains_synthetic_media" (generalt tartalom nyilatkozat) kotelezo, true vagy false')
    if 'privacy_status' in yt and yt['privacy_status'] not in ('public', 'unlisted', 'private'):
        fail(f'{i}. poszt youtube: privacy_status public/unlisted/private, vagy hagyd ki (Eszter valasztja)')
    if 'made_for_kids' in yt and not isinstance(yt['made_for_kids'], bool):
        fail(f'{i}. poszt youtube: made_for_kids true vagy false, vagy hagyd ki (Eszter jeloli)')
    legs = {p.get('post_type_facebook'), p.get('post_type_instagram'), p.get('post_type')}
    if p.get('platform') != 'none' and not ({'video', 'reel'} & legs):
        fail(f'{i}. poszt: YouTube-lab csak videos poszthoz (reel, Facebook video, vagy platform none)')
    if not p.get('video'):
        fail(f'{i}. poszt: a YouTube-labhoz video kell')
    m = ffprobe_video(os.path.join(d, p['video']))
    if m is None:
        fail(f'{i}. poszt: nincs ffprobe ezen a gepen, a Short hossza/aranya nem merheto -- igy nem kuldom')
    sec, w, h = m
    if sec > SHORTS_MAX_SEC:
        fail(f'{i}. poszt: a video {sec:.1f} mp, a YouTube Short legfeljebb {SHORTS_MAX_SEC} mp')
    if w > h:
        fail(f'{i}. poszt: a video fekvo ({w}x{h}); a YouTube Short allo vagy negyzetes')
    return [(f'{i}. poszt youtube cim', title), (f'{i}. poszt youtube leiras', yt.get('description') or '')]


def boards():
    """The ws-8 boards as Nova listed them (id -> name). The server lists them again, live, before anything is saved."""
    try:
        rows = [l.rstrip('\n').split('\t') for l in open(BOARDS_TSV, encoding='utf-8') if l.strip()]
    except OSError as e:
        fail(f'a tablalista ({BOARDS_TSV}) nem olvashato: {e}')
    return {r[0].strip(): r[1].strip() for r in rows if len(r) >= 2}


def pinterest_leg(i, p, d, text):
    """The Pinterest leg's own checks, before anything is sent (the uploader and the app check them again)."""
    pin = p['pinterest']
    if not isinstance(pin, dict):
        fail(f'{i}. poszt: a "pinterest" egy objektum')
    if set(pin) - PIN_KEYS:
        fail(f'{i}. poszt pinterest: ismeretlen kulcs: {sorted(set(pin) - PIN_KEYS)}')
    bid = pin.get('board_id')
    if not isinstance(bid, str) or not bid.isdigit():
        fail(f'{i}. poszt pinterest: a board_id a tabla szam-azonositoja, SZOVEGKENT ("371124...")')
    tablak = boards()
    if bid not in tablak:
        fail(f'{i}. poszt pinterest: a {bid} tabla nincs a ws-8 tablalistan ({BOARDS_TSV}); ha uj tabla, Nova frissitse a listat')
    if not (pin.get('title') or '').strip():
        fail(f'{i}. poszt pinterest: a cim kotelezo')
    desc = pin['description'] if 'description' in pin else text
    for k, mx in PIN_MAX.items():
        v = desc if k == 'description' else (pin.get(k) or '')
        if len(v) > mx:
            fail(f'{i}. poszt pinterest: {k} legfeljebb {mx} karakter (most {len(v)})'
                 + (' -- ez a poszt szovege, adj meg "description"-t' if k == 'description' and 'description' not in pin else ''))
    if not re.match(r'^https://\S+$', pin.get('link') or '', re.I):
        fail(f'{i}. poszt pinterest: a link kotelezo, https-sel kezdodo cim')
    if 'ai_modified' in pin and not isinstance(pin['ai_modified'], bool):
        fail(f'{i}. poszt pinterest: ai_modified true vagy false (vagy hagyd ki: false)')
    if p.get('video') and d:
        m = ffprobe_video(os.path.join(d, p['video']))
        if m is None:
            fail(f'{i}. poszt: nincs ffprobe ezen a gepen, a pin-video hossza/aranya nem merheto -- igy nem kuldom')
        sec, w, h = m
        if not PIN_VIDEO_SEC[0] <= sec <= PIN_VIDEO_SEC[1]:
            fail(f'{i}. poszt: a video {sec:.1f} mp, a Pinterest 4 mp es 15 perc kozott veszi at')
        if h and not 0.5 < w / h <= 1.91:
            fail(f'{i}. poszt: a video {w}x{h}, a Pinterest 1:2 es 1,91:1 kozotti aranyt vesz at')
    print(f'{i}. poszt pinterest: tabla "{tablak[bid]}"')
    return [(f'{i}. poszt pinterest cim', pin.get('title') or ''), (f'{i}. poszt pinterest leiras', pin.get('description') or ''),
            (f'{i}. poszt pinterest alt', pin.get('alt_text') or '')]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    proba = '--proba' in sys.argv
    if len(args) != 1:
        sys.exit(__doc__)
    d = os.path.realpath(args[0])
    if not d.startswith(NESSA_DIR):
        fail(f'a csomag-mappa csak {NESSA_DIR} alatt lehet')
    pj = os.path.join(d, 'posztok.json')
    pkg = json.load(open(pj, encoding='utf-8'))
    if (pkg.get('client_id'), pkg.get('meta_account_id'), pkg.get('status')) != (CLIENT, ACCOUNT, 'pending_review'):
        fail(f'a posztok.json client_id={CLIENT}, meta_account_id={ACCOUNT}, status=pending_review kell legyen')
    files = []
    now = datetime.datetime.now()
    pin_texts = []
    for i, p in enumerate(pkg.get('posts') or [], 1):
        if 'add_pinterest_to' in p:
            # a pin for a post that is already there: no media of its own (the uploader reads the post's)
            if not isinstance(p['add_pinterest_to'], int) or isinstance(p['add_pinterest_to'], bool) or p['add_pinterest_to'] <= 0:
                fail(f'{i}. poszt: az add_pinterest_to egy poszt id (szam)')
            if 'pinterest' not in p:
                fail(f'{i}. poszt: az add_pinterest_to melle "pinterest" lab kell')
            extra = set(p) - {'add_pinterest_to', 'pinterest', 'scheduled_at_local', 'sor', 'source', 'note'}
            if {k for k in extra if not k.startswith('_')}:
                fail(f'{i}. poszt: az add_pinterest_to mellett csak pinterest es scheduled_at_local lehet, ez is van: {sorted(extra)}')
            if 'scheduled_at_local' in p:
                when = datetime.datetime.strptime(p['scheduled_at_local'], '%Y-%m-%d %H:%M:%S')
                if when < now + datetime.timedelta(minutes=30):
                    fail(f'{i}. poszt: az idopont ({when}) kevesebb mint 30 perc mulva van -- Eszternek jovahagyni sem marad ido')
            pin_texts += pinterest_leg(i, p, None, '')
            continue
        if p.get('platform') not in ('instagram', 'facebook', 'both', 'none'):
            fail(f'{i}. poszt: platform instagram, facebook, both vagy none (none = csak YouTube / Pinterest)')
        if 'tiktok' in p and not TIKTOK_ENABLED:
            fail(f'{i}. poszt: a TikTok meg ki van kapcsolva (production review + ws-8 TikTok-fiok kell hozza)')
        if p.get('platform') == 'none' and not (('youtube' in p or 'pinterest' in p) and (p.get('post_type') == 'video'
                                                or (p.get('post_type') == 'single_image' and 'pinterest' in p and 'youtube' not in p))):
            fail(f'{i}. poszt: platform none = csak YouTube / Pinterest: post_type "video" es "youtube" vagy "pinterest" kulcs, '
                 'vagy post_type "single_image" es "pinterest" (kep-pin)')
        when = datetime.datetime.strptime(p.get('scheduled_at_local', ''), '%Y-%m-%d %H:%M:%S')
        if when < now + datetime.timedelta(minutes=30):
            fail(f'{i}. poszt: az idopont ({when}) kevesebb mint 30 perc mulva van -- Eszternek jovahagyni sem marad ido')
        if 'pinterest' in p:
            pin_texts += pinterest_leg(i, p, d, p.get('text') or '')
        legs = [t for t in (p.get('post_type_facebook'), p.get('post_type_instagram')) if t] or [p.get('post_type')]
        if not (p.get('text') or '').strip() and set(legs) != {'story'}:
            fail(f'{i}. poszt: ures szoveg')
        media = list(p.get('images') or []) + ([p['image']] if p.get('image') else []) \
            + ([p['video']] if p.get('video') else []) + ([p['cover']] if p.get('cover') else [])
        if not media and legs != ['text_only']:
            fail(f'{i}. poszt: nincs kep/video')
        for m in media:
            if os.path.basename(m) != m or not os.path.isfile(os.path.join(d, m)):
                fail(f'{i}. poszt: a mediafajl ({m}) nincs a csomag-mappaban (csak fajlnev, mappa nelkul)')
            files.append(m)
        # the app's length limits (story 60 s, reel 90 s); the server has no ffprobe, so the length is measured here
        story = 'story' in legs or (p.get('ig_story', pkg.get('ig_story')) is True and 'reel' in legs)
        limit = 60 if story else (90 if 'reel' in legs else None)
        if limit and p.get('video') and shutil.which('ffprobe'):
            sec = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                        os.path.join(d, p['video'])], capture_output=True, text=True).stdout.strip() or 0)
            if sec > limit:
                fail(f'{i}. poszt: a video {sec:.1f} mp, ' + ('a story legfeljebb 60 mp -- hagyd ki az "ig_story"-t, vagy rovidebb video'
                                                             if story else 'a Reel legfeljebb 90 mp'))
    if not pkg.get('posts'):
        fail('nincs poszt a csomagban')
    yt_texts = [t for i, p in enumerate(pkg['posts'], 1) if 'youtube' in p for t in youtube_leg(i, p, d)]
    szovegkapu([(f'{i}. poszt {k}', p.get(k) or '') for i, p in enumerate(pkg['posts'], 1) for k in ('text', 'first_comment')] + yt_texts + pin_texts,
               'poszt', 'innosocial')
    files = list(dict.fromkeys(files)) + ['posztok.json']
    with tempfile.TemporaryDirectory() as t:
        sh = os.path.join(t, 'run.sh')
        with open(sh, 'w') as out:
            out.write(HEAD)
            for name, path in [('innosocial-posztok.php', UPLOADER)] + [(f, os.path.join(d, f)) for f in files]:
                b = open(path, 'rb').read()
                out.write(f"base64 -d > \"$T/{name}\" <<'B64'\n" + base64.encodebytes(b).decode() + "B64\n")
                out.write(f"echo \"{hashlib.sha256(b).hexdigest()}  $T/{name}\" | sha256sum -c --quiet - || "
                          f"{{ echo \"FAIL: {name} damaged in transit\"; exit 1; }}\n")
            out.write(TAIL + ('' if proba else REAL))
        key = os.path.join(t, 'k')
        subprocess.run(['node', '--input-type=module', '-e',
                        "import { getSecret } from '/Users/macmini/marveen/dist/web/vault.js';import { writeFileSync } from 'fs';"
                        f"const k=getSecret('{SSH_KEY_ID}');writeFileSync(process.argv[1],k.endsWith('\\n')?k:k+'\\n',{{mode:0o600}})",
                        key], check=True)
        try:
            with open(sh) as f:
                p = subprocess.run(['ssh', '-i', key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
                                    HOST, 'bash -s'], stdin=f, capture_output=True, text=True, timeout=900)
        finally:
            open(key, 'w').close()
    out = '\n'.join(l for l in (p.stdout + p.stderr).splitlines() if not re.match(r'^(perl|\s*L[A-Z_]* =)|are supported|locale', l))
    print(out)
    links = sorted(set(re.findall(r'https://app\.innoworx\.hu/r/[A-Za-z0-9_-]+', out)))
    # the uploader's own list, in package order, with the story next to its post
    pairs = re.findall(r'^  post (\S+) #(\d+) (\S+) (\S+) (\S+ \S+): (https://\S+)$', out, re.M)
    ok = p.returncode == 0 and ('DRY-RUN OK' in out) and (proba or bool(links))
    print('\nEREDMENY:', 'OK' if ok else 'HIBA (a fenti kimenet mondja meg, mi allt meg)')
    if pairs:
        print('JOVAHAGYO LINKEK (Eszternek; a story kulon link):')
        for n, pid, plat, typ, when, url in pairs:
            print(f'  {when} {plat} {"STORY" if typ == "story" else typ} (#{pid}): {url}')
    elif links:
        print('JOVAHAGYO LINKEK (Eszternek):\n' + '\n'.join(links))
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:
        f.write(json.dumps({'at': now.isoformat(timespec='seconds'), 'csomag': d, 'proba': proba, 'posztok': len(pkg['posts']),
                            'rc': p.returncode, 'ok': ok, 'linkek': links, 'out_vege': out[-400:]}, ensure_ascii=False) + '\n')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
