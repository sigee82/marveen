# InnoWorx per-network típus + GIF: végső átnézés, mérve

**Mérvadó futás:** ág `feat/iw-halozatonkenti-tipus-es-gif`, commit
**`d792c2f08833bf35019d501c984b9c75301fbc8a`**, nulla nem-commitolt változással.
Ezen a SHA-n futott a TELJES mátrix, a preservation-mag, a `tsc -b --force`, a build és a
PHPUnit suite. A korábbi jelentés `802de0de`-ra hivatkozott; az már nem a fa vége.

Külön, eldobható konténer szolgálta ki (8003-as port, `innoworx_api-uploads` kötettel), a
meglévő stackhez nem nyúltam, és a mérés végén leállt. A kiszolgált fa azonossága
fájl-hash-sel igazolva, nem feltételezve. A mérő azonosság-kapuja `DB_NAME = innoworx`-re áll.

> Ez a lokális InnoWorx stack, nem a prod. A 302 valódi poszt a `napalatt_innoworx_prod`-ban
> van; oda nincs utam. A fixture 14 sora a prod eloszlására van mintázva.

---

## 1. A 21 cellás mátrix — újramérve a mostani HEAD-en

### MENTÉS-réteg, mind a 18 pár (valódi HTTP, `save_post`)

| típus | facebook | instagram | both |
|---|---|---|---|
| text_only | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| single_image | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| carousel | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| video | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| reel | **ELUTASÍTVA** | ELFOGADVA | **ELUTASÍTVA** |
| story | ELFOGADVA | ELFOGADVA | ELFOGADVA |

A `text_only`-ban nincs „JELENLEG" (az Instagram korlátja), a `video`/`reel` soroknál van
(a miénk). A 18 sor a `6fc1c893` és a `d792c2f0` futásban **soronként azonos** (`diff`-fel
összevetve), és azonos a `802de0de`-n mérttel.

### MÉDIA-réteg (valódi HTTP, a csatolás pillanata)

| anyag | eredmény |
|---|---|
| PNG | **200** — csatolva |
| GIF | **202** — `gif_to_mp4` sorba téve, a mondattal |
| MP4 → `single_image` | **400** — elutasítva |

### A 18. cella — a 2. ütem átvételi feltétele

`save_post`: `platform=both`, `post_type=video`, `post_type_facebook=video`,
`post_type_instagram=reel` → **`success`**.
Visszaolvasva **az adatbázisból** (nem a válaszból): **`fb=video ig=reel split=1`**.

A lábankénti tiltás mindhárom tiltott lába külön mondattal:

- FB-láb `reel` → „A Facebook-lábon a Reel JELENLEG nem megy: válaszd a Videó típust a
  Facebookhoz, az Instagram maradhat Reel."
- IG-láb `video` → „Az Instagram-lábon a feed-videó JELENLEG nem megy: válaszd a Reel
  típust az Instagramhoz, a Facebook maradhat Videó."
- IG-láb `text_only` → „Az Instagram nem fogad kép vagy videó nélküli posztot, ezért az
  Instagram-láb nem lehet »Csak szöveg«…"

---

## 2. Fordítás és build

| lépés | eredmény |
|---|---|
| `npx tsc -b --force` | **exit 0, nulla kimeneti sor** |
| `npm run build` (canva-app + `tsc -b` + vite + PWA) | **exit 0** |
| `npm run test:checks` (szekciónév-kapu) | **zöld**, 7 idézett név, 0 bukott |

A `--noEmit` ebben a repóban hamis zöldet ad; végig `-b --force` futott.

---

## 3. Preservation-mag — mérve, nevezővel együtt

| invariáns | eredmény | nevező |
|---|---|---|
| backfill-eltérés a migráció szabályától | **0** | 14 ellenőrzött sor |
| média nélküli sztori **kimenő** státuszban | **0** | 5 sztoriból 2 kimenő |
| rés-detektor (mindkét láb NULL) | **0** | 14 sor |
| kikötés-sértő sor | **2**, ebből kimenő **0** | 9047, 9048 — mindkettő `reel`+facebook DRAFT |

A mérő fájlban áll: `scripts/iw-pernet-preservation.sql`. **A kontrollja megmérve**, nem
feltételezve: egy sor platformját NYERS SQL-lel átírva (a lábakhoz nem nyúl, mert a szinkront
csak az író-utak futtatják) az ELTÉRÉS 0-ról **1**-re ment, a sor törlése után vissza 0-ra.
Tehát nem olyan kapu, ami csak zöldet tud mutatni.

---

## 4. A migráció a VALÓDI futtatón keresztül — ez eddig nem volt megmérve

A négy blokk a lokális DB-be **kézzel** került be: a `migration_history`-ban 541-544
**nincs benne** (44 sor, a leghosszabb id 3 karakter). Tehát az `api/migrate.php`
ezt a négy blokkot **soha nem futtatta le** egyetlen rendszeren sem.

Mérőpad: a lokális `innoworx` dump másolata, a három oszlop és a `innosocial_media_jobs`
eldobva, a `migration_history` a másik 503 ID-vel feltöltve (ahogy a prod áll).

```
ELSŐ FUTÁS:    Executing [541_…] DONE  [542_…] DONE  [543_…] DONE  [544_…] DONE
               Executed: 4   Skipped: 503   Total: 507
MÁSODIK FUTÁS: Executed: 0   Skipped: 507   Total: 507
```

A **futtató által** előállított backfill azonos a kézivel: eltérés **0** / 14 sor,
rés **0**, a `media_jobs` tábla létrejött, kikötés-sértő **2 / kimenő 0**.

### >>> KÉT DOLOG ÁLLHAT A MIGRATE-FIRST ÉS A 541-ES BLOKK KÖZÉ <<<

Egyik sem ennek az ágnak a hibája, de mindkettő PONT ma este számít.

**(a) Egy fantom migráció — JAVÍTVA ezen az ágon (`6fc1c893`).**
A futtató a fájlt a `-- ID: ` szöveg MINDEN előfordulásán felvágja, prózában is. Egy
kommentmondat (fdaee671, #35 óta a dev-en) tartalmazta, így a futtató
`block (migrate.php runs a single query() per block).` azonosítóval futtatott egy blokkot.
A futtatás ártalmatlan (a törzse csupa komment), **az ID nem**: 53 karakter, a
`migration_history.id` VARCHAR(50) → „Data too long", ami **nincs** a futtató lenyelt hibái
között, tehát **MEGÁLLÍTJA a futást** — az ~525. blokknál, a 541 ELŐTT. Megmérve: javítás
előtt megállt, javítás után `Executed: 4`.

**(b) 23 túlhosszú blokk-ID — NINCS javítva, tudatosan.**
507 blokkból 23-nak az ID-je 50 karakternél hosszabb; az első a
`367_innosocial_publishing_log_instagram_comment_enum` (52). Ugyanaz a megállás vár rájuk,
**ha a cél adatbázis még nem rögzítette őket**. Az első 50 karakterük mind különböző, tehát
csonkolás nem tud egy blokkot egy másikkal elnyeletni. Az oszlop szélesítése külön döntés,
itt nem hoztam meg.

**A prod-futás előtti egy lekérdezés, ami eldönti, elér-e a futás a 541-ig:**

```sql
SELECT COUNT(*) AS hianyzo FROM migration_history
 WHERE id IN ('367_innosocial_publishing_log_instagram_comment_enum',
              'block (migrate.php runs a single query() per block).');
SELECT CHARACTER_MAXIMUM_LENGTH FROM information_schema.COLUMNS
 WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME='migration_history' AND COLUMN_NAME='id';
```

Ha a `migration_history` sorainak száma 500 körül van és a 367-es bent van, a futás elér a
541-ig. Ha nincs bent, a migrate-first lépés **megáll**, mielőtt bármit csinálna — nem ront
el semmit, de nem is halad.

---

## 5. Amit ez az átnézés talált és JAVÍTOTT

1. **A mérő nem tudta előállítani a saját média-rétegét** (`b8b5ccd4`). A konténerben hívta
   az ffmpeg-et, ami abban a képben nincs → 127, a `2>/dev/null` elnyelte, a `set -e` a
   próba-poszt kiírása UTÁN, némán megállt. A MENTÉS 18 sora kijött, a MÉDIA 3 sora meg sem
   jelent — és egy meg nem jelent sor később nem „hibának", hanem „nem volt ott"-nak
   olvasódik. A fájlok most a hoszton készülnek és `docker cp`-vel mennek be; a futás kiírja,
   melyik fájl érkezett meg. Az ffmpeg **szándékosan** marad a konténeren kívül: bent a
   GIF-konverzió épp attól működne, hogy a MÉRŐNEK kellett.
2. **Két mérés-feltöltés be volt commitolva** (`b8b5ccd4`). A 8003-as konténer a munkafa
   `api/`-ját csatolta uploads-kötet nélkül, így a média-réteg PNG-je és GIF-je a munkafába
   esett és bement `950e8c63`-mal. A prod deploy kizárja az `uploads/**`-ot, tehát
   észrevétlen maradt volna. Kivéve, és a `_generated/*/` mostantól ignorálva.
3. **Egy komment nem létező őrre hivatkozott** (`b8b5ccd4`). A `PostTypePerNetwork.php`
   fejléce azt írta, hogy `PostTypePerNetworkTest` összeveti a dual-write SQL-t egy
   `api/migrations/20260917_…sql` fájllal. **Egyik sem létezik ebben a repóban** — a mondat
   a kiválttal együtt jött át. Egy komment, ami az „le van fedve?" kérdésre igennel válaszol,
   rosszabb, mint a semmi. **Az őr most valódi**: a `PerNetworkLegRuleMatchesTheMigrationTest`
   kiolvassa az 542-es blokkot a `migrations.sql`-ből és összeveti az
   `INNOSOCIAL_LABAK_SQL`-lel, plusz negatív kontroll az üres összevetésre.
   **Három állapotban megmérve**: zöld; **piros**, amikor a konstans egyik ága NULL helyett
   `'single_image'`-et írna (a bukás kiírja mindkét szöveget); és újra zöld a visszaállítás után.
4. **Egy prózamondat migrációként futott** (`6fc1c893`) — lásd a 4. szakasz (a) pontját.
5. **A preservation-mérő fájlba került** (`d792c2f0`). Amit nem lehet újra levezetni, az
   állítás. Menet közben derült ki, hogy a repo `*.sql`-t globálisan ignorál, ezért az első
   commit-kísérlet NÉMÁN nem csinált semmit („working tree clean") — a `scripts/` alatti
   mérők most kivételek.

---

## 6. NEM MÉRTEM — tételesen

1. **A publikálás kimenetele egyetlen cellában sem mért** — valódi Meta-hívás lenne.
2. **A GIF→MP4 konverzió maga**: az InnoWorx konténerben nincs ffmpeg. A sor, a dispatch, a
   hibaágak és a csatolás mérve; a konverziót a kiváltotton mérték, azonos kóddal.
3. **A 302 valódi soron semmi** — a prod-mérés a tiéd.
4. **Böngészős végigkattintás nem történt**: a mérés HTTP- és DB-szintű.
5. **A prod `migration_history` állapota** — a 4. szakasz lekérdezése a tiéd.
6. **`/home/napalatt/bin/ffmpeg` léte a prodon.** A worker abszolút úton hívja
   (`INNOSOCIAL_FFMPEG` env felülírja), és ha nincs ott, a job `error` lesz világos üzenettel
   — nem törik el tőle semmi más. Egy soros ellenőrzés: `ls -l /home/napalatt/bin/ffmpeg`.

---

## 7. NYITOTT, NEM BLOKKOLÓ — amit én magam nem tartok késznek

Kérdésedre az őszinte válasz: **három tétel**, egyik sem áll a GO útjában, de egyik sem
„kész" abban az értelemben, hogy rá lehetne hagyatkozni.

1. **Két függvény, nulla hívási hellyel.** Az `innosocialLabakUtolero()` és az
   `innosocialLabAnomaliak()` az `api/innosocial_lib/PostTypePerNetwork.php`-ban **definíció,
   semmi több** — az egész repóban egyetlen hívásuk sincs (grepelve). Az utolérő pont arra az
   ablakra való, amit a lépcsős terv maga nyit: a backfill EGYSZER fut, tehát minden sor, ami
   a migráció és a kód-deploy KÖZÖTT születik, NULL lábakkal marad, és semmi nem tölti ki.
   Ma ezt **kézzel** kell lefuttatni a deploy után — vagy a rés-detektort megnézni.
   A migrate-first sorrendnél ez az ablak valós.
2. **A 4. lépés (olvasás-váltás) előtt a két `reel`+facebook piszkozatot le kell zárni**, és a
   lezárás MÓDJA számít. Megmérve mindkét út:
   - **API/felület** (`save_post`, platform=instagram): `fb=NULL ig=reel` — a lábak követik. ✔
   - **Nyers SQL** `UPDATE … SET platform='instagram'`: a lábak **`fb=reel ig=NULL`** maradnak,
     vagyis az igazság ELLENKEZŐJÉT mondják, és az eltérés-számláló 0-ról 1-re megy.
     A 4. lépés után egy ilyen sor a Facebook-lábon próbálna Reelt kiküldeni.

   **Tehát: a két piszkozatot a felületen/API-n át állítsd át, ne SQL-ből.** Ha mégis SQL-ből
   megy, utána a `scripts/iw-pernet-preservation.sql` 1. szakaszának **0**-t kell adnia —
   ha 1-et vagy 2-t ad, a lábakat is át kell vezetni.
3. **A `save_post` lábak nélküli újramentése egy split poszton elutasít.** Megmérve: a
   `fb=video ig=reel split=1` posztot lábak nélkül újramentve a pár-szintű kikötés lép be, és
   azt tanácsolja, állítsd a platformot Facebookra — ami ezen a soron rossz tanács. A sor nem
   sérül (a `split=1` védi), és a szerkesztő MINDIG visszaküldi a lábakat (a dialógus két
   választóval nyitja a szétválasztott posztot), tehát a felületről nem érhető el. Bármely
   MÁS hívó (script, jövőbeli integráció) viszont beleszalad.

**Ideiglenes flag, kikapcsolt ág, nyitott TODO nincs**: a `git diff origin/dev...HEAD`
változott fájljaiban nulla `TODO`/`FIXME`/`HACK`, és nulla feature-flag.

Egy nyitott ág **van, és a kódban ki van mondva**, nem jegyzetben: az
`innosocial_gif_worker.php` fejléce megnevezi az inline fokozatot (megszakadt futás
`running`-ban marad örökre; a felület nem mutatja a konverzió állapotát), és megmondja, mi
határolja (16M `upload_max_filesize`, a `popen` fokozat elérhető). Ezt tudatosan hagytuk így.

---

## 8. A PHPUnit suite — a számot ismerd, mielőtt ránézel

| fa | teszt | hiba | bukás |
|---|---|---|---|
| `origin/dev` (4f5a9ac4) | 700 | 10 | 19 |
| ez az ág (d792c2f0) | 703 | 10 | 19 |

A bukó halmaz **elemre azonos**: 29 bejegyzés, mind a kettőn ugyanaz (`comm`-mal összevetve,
mindkét irányban üres a különbség). **Ez az ág nulla új bukást hoz.** De a suite a dev-en
MÁR piros, tehát „a tesztek zöldek" itt nem használható kapuként — a különbséget kell nézni.

---

## 9. Amit átadok — abszolút úttal

| mi | út |
|---|---|
| a munkafa (HEAD `d792c2f0`, tiszta) | `/Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet` |
| **a prodra felmenő `migrations.sql`** | `/Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet/api/migrations.sql` |
| a 541-544 blokk kiemelve (OLVASÁSRA) | `/Users/macmini/marveen/tervek/atadas/innoworx-migracio-541-544.sql` |
| ez a jelentés | `/Users/macmini/marveen/tervek/innoworx-matrix-vegso-atnezes-2026-09-18.md` |
| a mátrix-mérő | `/Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet/scripts/iw-matrix-meres.sh` |
| a preservation-mérő | `/Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet/scripts/iw-pernet-preservation.sql` |
| a bontás/rés-kontroll | `/Users/macmini/marveen/agents/bit/workspace/wt-iw-pernet/scripts/iw-pernet-kontroll.sh` |

**A migrációt NEM lehet a kiemelt fájlból futtatni.** Az `api/migrate.php` fix utat olvas
(`__DIR__ . '/migrations.sql'`), más fájlt nem vesz át. A prodra a **teljes**
`api/migrations.sql` megy fel, és az `api/migrate.php` futtatja; a 541-544 az egyetlen négy
blokk, ami még nincs a `migration_history`-ban. A deploy workflow **nem** hívja a
`migrate.php`-t, tehát a sorrend tényleg a tiéd.

A 541-544 blokk a fájl **5298-5386.** sorában áll (a fájl 5386 soros).

## 10. A 2 reel+Facebook piszkozatról

A (b) út — ti állítjátok át őket Instagramra — a kódból nézve **rendben van**, egy kikötéssel,
ami a 7/2. pontban áll: **az átállítás menjen a felületen/API-n át, ne nyers SQL-ből**, mert a
láb-szinkront csak az író-utak futtatják. Utána a preservation-mérő 1. szakaszának 0-t kell
adnia. Ezen kívül **nincs a kódban semmi, ami emiatt másképp viselkedne**: a lábakat ma még
senki nem olvassa (a 4. lépés nincs ezen az ágon), a publikáló továbbra is a `post_type`-ból
dolgozik.

**Nem pusholtam és nem mergeltem.** Ez az átnézés HÁROM új commitot tett az ágra, mind lokális:
`b8b5ccd4`, `6fc1c893`, `d792c2f0`. Az ág így 10 committal áll az `origin/dev` előtt.
