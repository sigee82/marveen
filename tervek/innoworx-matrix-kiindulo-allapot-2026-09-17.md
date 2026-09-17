# InnoWorx — a 21 cellás mátrix KIINDULÓ állapota

**Mérve 2026-09-17-én, `origin/dev` = `4f5a9ac4` (a #194 merge-e).**
Ez NEM a kiváltott példány eredménye: ott más a szerkezet, ezért nulláról mértem.

## Hogyan mértem, és mi micsoda

Két forrás, és külön jelölöm, melyik állítás melyikből jön:

- **EMPIRIKUS** — a futó dev-stacken, valódi HTTP-hívással (`save_post`, `set_status`,
  `client_id=900`, JWT a konténerből mintázva). 18 poszt jött létre, mindet visszamértem a
  DB-ből, és mind a 18-at töröltem utána (`maradt: 0`).
- **KÓDBÓL** — a publikáló ágaiból levezetve. A publikálás valódi Meta-hívás lenne, azt nem
  futtattam.

**EGY KIKÖTÉS A MÉRÉS ÉRVÉNYESSÉGÉRE.** A konténer nem a `dev` naptárfájlját szolgálja ki:
egyetlen hunk tér el (692. sor), pontosan a #194 story-szöveg kivétele. Megmértem, hogy ez az
EGYETLEN eltérés (`diff` → 1 hunk), tehát a platform × típus tengelyen a konténer bájtra a dev.
A szöveg-tengelyen viszont a konténer a #194 ELŐTTI állapot, ezért ott a dev viselkedése a
kódból áll, nem a mérésből.

## A mentés (save_post) — EMPIRIKUS

| post_type | facebook | instagram | both |
|---|---|---|---|
| single_image | elfogadva | elfogadva | elfogadva |
| carousel | elfogadva | elfogadva | elfogadva |
| video | elfogadva | **elfogadva** | **elfogadva** |
| text_only | elfogadva | **elfogadva** | **elfogadva** |
| reel | **elfogadva** | elfogadva | elfogadva |
| story | elfogadva | elfogadva | elfogadva |

**Mind a 18 pár átmegy.** Az InnoWorxon NINCS platform × típus kikötés a mentésben — nincs
`innosocialPlatformKikotes()` megfelelő. A vastagon szedettek azok, amiket a kiváltott példány
ma már a mentésnél elutasít, saját mondattal.

## A kimenő átmenet (set_status → approved) — EMPIRIKUS

Média NÉLKÜL, szöveggel, mind a hat próbált pár **átment** `approved`-ba:

    video/instagram      {"status":"success","data":{"updated":1}}
    text_only/instagram  {"status":"success","data":{"updated":1}}
    reel/facebook        {"status":"success","data":{"updated":1}}
    story/facebook       {"status":"success","data":{"updated":1}}
    story/instagram      {"status":"success","data":{"updated":1}}
    story/both           {"status":"success","data":{"updated":1}}

**A média nélküli sztori kimenő állapotba kerül mind a három platformon.** Ez a lyuk, amit a
#283 zár be a kiváltott példányon. Az InnoWorxon ma nyitva van — és itt vannak a valódi
felhasználók.

## A 21 cella

A mátrix három réteget kérdez, és a média a mentésnek láthatatlan. Ezért cellánként azt írom,
melyik réteg dönt, és MELYIK forrásból tudom.

| # | Platform | Anyag | InnoWorx MA | forrás |
|---|---|---|---|---|
| 1 | csak FB | szöveg | megy | kód |
| 2 | csak FB | egy kép | megy | kód |
| 3 | csak FB | 2-10 kép | megy; <2 képnél a publikáló utasít el, saját mondattal | kód |
| 4 | csak FB | MP4 | megy | kód |
| 5 | csak FB | GIF | **nincs konverzió sehol** | kód |
| 6 | csak FB | kép + Story | megy (`publishPhotoStoryToPage`) | kód |
| 7 | csak FB | MP4 + Story | publikálónál elutasít, saját mondattal (270. sor) | kód |
| 8 | csak IG | szöveg | mentés ÁTENGEDI; publikálónál "Instagram publikáláshoz kép kötelező" — **nem mint típus akad el, hanem mint "nincs kép"** | empirikus + kód |
| 9 | csak IG | egy kép | megy | kód |
| 10 | csak IG | 2-10 kép | megy | kód |
| 11 | csak IG | MP4 | Reel típussal megy | kód |
| 12 | csak IG | GIF | **nincs konverzió** | kód |
| 13 | csak IG | kép + Story | megy | kód |
| 14 | csak IG | MP4 + Story | megy | kód |
| 15 | mindkettő | szöveg | mentés átengedi; IG-lábon a 8. korlát | empirikus + kód |
| 16 | mindkettő | egy kép | megy | kód |
| 17 | mindkettő | 2-10 kép | megy | kód |
| 18 | mindkettő | MP4 | **a publikáló a `video` típust `platform !== 'facebook'`-nál elutasítja (163. sor)** — a 2. ütem átvételi feltétele | kód |
| 19 | mindkettő | GIF | **nincs konverzió** | kód |
| 20 | mindkettő | kép + Story | megy mindkét lábon | kód |
| 21 | mindkettő | MP4 + Story | **az egész poszt bukik**: az FB-láb dob (270.), az IG-láb el sem indul | kód |

## TÉTELES ELTÉRÉSEK a kiváltott példányhoz képest

Nova kérte, hogy ne egyesítve. Hat tétel:

**1. Nincs `PostReadiness.php`.** A #194 inline oldotta meg, a `save_post`-ban, EGY feltétellel,
a MENTÉS tengelyén. A kiváltotton a szabály az ÁLLAPOT tengelyén áll és három úton hat.

**2. Öt író út van, nem négy.** A többlet a `innosocial_cron_translate.php:494`, ami `pending_review`-ba
emel posztot. **Ez a kiváltotton nem létezik.** Ott az "operátor-mondat" fogalma nem értelmes,
mert nincs operátor a huzalon — Nova külön dönt róla, én nem nyúlok hozzá.

**3. Nincs platform × típus kikötés a mentésben.** Mind a 18 pár átmegy (empirikus). A kiváltotton
a `video`+nem-FB, a `reel`+nem-IG és a `text_only`+IG saját mondattal elakad a mentésnél.

**4. HÉT elavult `"Vizuál" szekció` hivatkozás, miközben a szekció neve „Kreatív".**
`Publisher.php` 218, 224, 230, 242, 270, 433 — és `PostBriefDialog.tsx:1878`. A composer szekció
neve a `PostBriefDialog.tsx:1954` szerint „Kreatív"; két hely (1942, 2591) már helyesen mondja.
A felületen „Vizuál*" csak a Brand-modulban van („Vizuális kit"), az MÁS hely — a mondat pedig
azt mondja, hogy „csatold a poszthoz". **Az InnoWorxon nincs szekciónév-ellenőrző.**

**5. A `reel` + facebook némán rossz kimenetet ad.** Az `isReel` a publikálóban csak két helyen
szerepel (221: kell videó; 436: IG-láb). **Az FB-lábon nincs reel-ág**, tehát a Facebookra
közönséges poszt megy ki, hibaüzenet nélkül. A típusválasztó `facebook`-ról instagramra billenti
a platformot Reel választásakor — de **némán**, és a platform-kapcsolóban (`togglePlatform`, 80-88.
sor) **nincs semmilyen típus-őr**, tehát a `reel` + `both` kombináció visszaépíthető.

**6. Egy komment olyat állít, ami itt nem igaz.** A `ComposerHeaderBar.tsx` a `video` típusnál azt
írja: *"the server refuses this type on instagram/both"*. Az InnoWorxon a szerver a MENTÉSNÉL nem
utasítja el (empirikus: elfogadva), csak a publikálónál. A mondat a kiváltott példány állapotát
írja le.

## Amit ez a mérés NEM mond meg

- A publikáló ágai KÓDBÓL vannak levezetve; valódi Meta-hívást nem futtattam.
- A szöveg-tengelyen a dev viselkedése kódból áll, mert a konténer a #194 előtti naptárt szolgálja.
- A GIF-sor (5., 12., 19.) mindkét rendszeren ugyanaz a hiány; ez a 2. ütem tárgya.
