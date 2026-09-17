# A 21 cellás átvételi mátrix — a kiváltott InnoSocial, mérve

**Mérve 2026-09-17 este, a kiváltott példány LOKÁLIS docker-stackjén** (`DB=innosocial`,
API a 8001-es porton, client 900, meta account 900), a ma esti kóddal: per-hálózat oszlopok,
olvasás-váltás, GIF-konverzió.

> **EZ NEM A `dev.innosocial.hu`.** A távoli dev másik környezet, és ott jelenleg egyetlen
> meta fiók van (acc 22, csak Facebook, IG nincs bekötve). A különbség a **mentés**-réteget nem
> érinti: megmérve, a `save_post` nem nézi, van-e IG bekötve a fiókhoz — az `instagram` és a
> `both` párokat a platform-kikötés alapján fogadja el vagy utasítja el. A **publikálás**-réteget
> viszont érinti, azt viszont egyik környezetben sem mértem.

Zsolt kikötése: *„atomjaira tesztelve minden opcióra — csak Facebookkal, csak Instával,
mindkettővel együtt, mindenfajta verzióban, képpel, videóval, GIF-fel."*

## A 18. CELLA MEGVAN — újramérve `6ff6b8d0`-n

**A második ütem átvételi feltétele teljesül:** egy poszt, két különböző láb-típus.

| kérdés | eredmény |
|---|---|
| (a) a felület engedi-e | **igen** — `both`-nál „Külön típus hálózatonként", két választóval; a Facebook-láb listájából a `reel` **ki sem látszik** |
| (b) ha tilt, kimondja-e | **igen** — „A Facebook-lábon a Reel JELENLEG nem megy: válaszd a Videó típust a Facebookhoz, az Instagram maradhat Reel." |
| (c) a `save_post` ugyanazt mondja-e | **igen** — `fb=video` + `ig=reel` → `success` |
| **visszaolvasó mérő** | **a DB-ben pontosan a kért érték áll**: `fb=video ig=reel split=1` — nem a szinkron alapértelmezése |
| (d) a publikáló lábanként kezelné-e | **levezetve** (valódi Meta-hívás nem történt): az FB-ág `$fbTipus`-ból, az IG-ág `$igTipus`-ból dolgozik |
| (e) a tiltás látszik-e | **igen**, két szinten: a választó fel sem kínálja, és a szerver saját mondattal utasít el |

**A néma vesztés, amit a mérés talált és ami javítva lett:** egy `fb=single_image, ig=carousel`
poszt egy **sikeres**, láb-típus nélküli mentés után `ig=single_image`-re állt vissza — a válasz
`success` volt. A javítás a `post_type_split` jelölő: a szándékos szétválasztás **állapot**, és
állapotnak hordozó kell. Visszamérve mindkét irányban: szétválasztottnál a láb túléli a második
mentést, nem szétválasztottnál a platform-váltás továbbra is továbbterjed a lábakra.

**Egy sor, amit Nova kért külön:** ha egy régi kliens láb nélkül ment egy szétválasztott posztra és
a pár-szintű kikötés tiltja a párt, a mentés **elutasításra kerül** — nem némán ír felül. A váltás
nem hagy hátsó ajtót a régi felületnek.

## Az előző futás (`2b5d01f0`) — a definiált állapot bevezetése

**A mérvadó futás:** `feat/halozatonkenti-tipus-es-gif`, commit **`2b5d01f0`**, nulla
nem-commitolt változással. Külön, eldobható konténer szolgálta ki ezt a fát (8002-es port),
a meglévő stackhez nem nyúltam, és a mérés végén leállt.

### A két futás különbsége — mit rejtett el a kevert fa

**Egy valódi regressziót, az enyémet.** A kevert fán minden újonnan létrehozott poszt rendes
id-t adott vissza; a definiált fán **`id: 0`**. Ok: a dual-write `innosocialLabakSzinkron()`
egy UPDATE-et futtat, és MySQL-ben egy UPDATE után a `lastInsertId()` **nullát** ad — a hívás
egy sorral a kiolvasás elé került. A poszt létrejött, a mentés `success`-t adott, csak az
**azonosítója veszett el a válaszban** — vagyis a composer nem tudott média-t csatolni egy friss
poszthoz. Pontosan az a hibaosztály, amiről ez az egész munka szól.

A kevert fa azért nem mutatta, mert abban nem volt benne ez a változás. **Nem csak pontatlan
volt: elrejtett egy hibát.** Javítva (`2b5d01f0`), visszamérve: a mentés `id: 108`-at ad, és a
poszt `fb=single_image, ig=-` — a lábak is megvannak.

**Minden más cella azonos eredményt adott a két futáson**: ugyanaz az 5 elutasítás ugyanazokkal
a mondatokkal, ugyanaz a 13 elfogadás, és a média-réteg (PNG 200 / GIF 202 / MP4 400 a
`single_image`-re) is változatlan.

### Az eredeti, kevert futás korlátja (megtartva, mert a különbség ettől olvasható)

Nova mérte vissza, és igaza van. A konténer, amelyen a **mentés-réteg** futott, nem `origin/dev`
és nem is egy megnevezett commit: HEAD `ecb86939` (a #277), **hat committal elmaradva** dev-től,
plusz egy részleges kézi overlay (7 fájl, +7/−254). A **média-réteghez** viszont én magam
másoltam be a ma esti fájljaimat. Vagyis a mérés **kevert fán** futott.

**Ami ettől függetlenül érvényes:** a platform-kikötés függvénye (`innosocialPlatformKikotes`)
a két fán tartalmilag azonos — megmérve —, tehát az öt elutasítás és a tizenhárom elfogadás
a függvény viselkedéséről igaz. Ez viszont **nem** ugyanaz, mint „a kimenő rendszer zöld".

**A helyes rendszer-a-teszt-alatt** nem a tiszta `origin/dev` (abban a ma esti képességek nincsenek
benne, a GIF-cellák mind elutasításra futnának), hanem **`origin/dev` + a ma esti commitok** =
a `feat/halozatonkenti-tipus-es-gif` ág. **A mérés ezen még nem futott le.** Amíg nem fut le,
ez a dokumentum a fenti korláttal olvasandó, és a jelentésbe a commit-sha kerül, nem az, hogy „dev".

## Amit ez a mérés ér, és amit nem

**Három réteg, és cellánként megnevezem, melyik válaszolt.** A média a mentésnek **láthatatlan**
— külön végponton jön, a mentés után —, ezért egy „a mentés átengedte" nem jelenti, hogy a poszt
kiküldhető.

- **MENTÉS** — valódi HTTP `save_post`. Mind a 18 típus×platform pár lemérve.
- **MÉDIA** — valódi HTTP, a csatolás pillanata: PNG, MP4, GIF.
- **PUBLIKÁL** — **NEM FUTTATTAM**: valódi Meta-hívás lenne. A publikáló ágaiból vezetve le,
  és minden ilyen cella ezt ki is mondja.

**Egy hiba, ami majdnem elrontotta az egészet, és ezért itt áll:** az első futás a **8000-es**
portra ment, ami az **InnoWorx**, nem a kiváltott. Mind a 18 pár „elfogadva"-t adott — helyesen,
csak a másik rendszerben, ahol nincs platform-kikötés. 19 próba-poszt keletkezett az InnoWorxban,
mire kiderült; kitöröltem őket. A mérő azóta **indulásnál ellenőrzi a `DB_NAME`-et**, és megáll,
ha nem a kiváltottat méri.

## MENTÉS-réteg — mind a 18 pár (valódi HTTP)

| típus | facebook | instagram | both |
|---|---|---|---|
| text_only | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| single_image | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| carousel | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| video | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| reel | **ELUTASÍTVA** | ELFOGADVA | **ELUTASÍTVA** |
| story | ELFOGADVA | ELFOGADVA | ELFOGADVA |

Az öt elutasítás **saját mondattal**, szó szerint:
- `text_only` + IG/both: „Az Instagram nem fogad kép vagy videó nélküli posztot. Tegyél fel egy
  képet, vagy állítsd a platformot Facebookra." — **nincs benne „JELENLEG"**, mert ez az Instagram
  korlátja, nem a miénk.
- `video` + IG/both: „A videós poszt JELENLEG csak a Facebookra publikálható…"
- `reel` + FB/both: „Reel posztot JELENLEG csak az Instagramra tudunk kiküldeni…"

## MÉDIA-réteg — a csatolás pillanata (valódi HTTP)

| anyag | eredmény |
|---|---|
| PNG kép | **HTTP 200** — csatolva, `picked=1` |
| GIF | **HTTP 202** — átalakítás sorba téve: „A GIF átalakítása videóvá elindult. Amint kész, videóként jelenik meg a poszton." |
| MP4 → `story` (FB) | **HTTP 200** — csatolva videóként |
| MP4 → `reel` (IG) | **HTTP 200** |
| MP4 → `video` (FB) | **HTTP 200** |
| MP4 → `single_image` | **HTTP 400** — „Videót csak Reel, Story vagy videó poszthoz lehet feltölteni." |

A GIF végig is ment: külön mérve egy 63×41-es GIF → h264 **62×40**, videóként csatolva.

## A 21 cella

Az (e) kérdés — **ha tilt, a tiltás LÁTSZIK-e** — azért van külön, mert a néma tiltás
(letiltott gomb, el nem küldött kérés) kívülről ugyanúgy néz ki, mint a működés.

| # | Platform | Anyag | Mérés | Melyik réteg felelt |
|---|---|---|---|---|
| 1 | csak FB | szöveg | mentés ELFOGADVA | MENTÉS (mért) |
| 2 | csak FB | egy kép | mentés + kép csatolás 200 | MENTÉS + MÉDIA (mért) |
| 3 | csak FB | 2-10 kép | mentés ELFOGADVA; <2 képnél a publikáló utasít el saját mondattal | MENTÉS mért, publikáló **levezetve** |
| 4 | csak FB | MP4 | mentés + MP4 csatolás 200 | MENTÉS + MÉDIA (mért) |
| 5 | csak FB | GIF | **202, átalakítás indul**, majd videóként csatolva | MÉDIA (mért) |
| 6 | csak FB | kép + Story | mentés ELFOGADVA, kép csatolható | MENTÉS + MÉDIA (mért) |
| 7 | csak FB | MP4 + Story | mentés ELFOGADVA, MP4 csatolás **200**; a publikáló kép-storyt vár és saját mondattal utasít el | MENTÉS + MÉDIA mért, publikáló **levezetve** |
| 8 | csak IG | szöveg | **mentés ELUTASÍTVA**, saját mondattal | MENTÉS (mért) |
| 9 | csak IG | egy kép | mentés + csatolás 200 | MENTÉS + MÉDIA (mért) |
| 10 | csak IG | 2-10 kép | mentés ELFOGADVA | MENTÉS (mért) |
| 11 | csak IG | MP4 | `reel`-ként: mentés + MP4 200 | MENTÉS + MÉDIA (mért) |
| 12 | csak IG | GIF | **202**, majd videóként csatolva | MÉDIA (mért) |
| 13 | csak IG | kép + Story | mentés + csatolás 200 | MENTÉS + MÉDIA (mért) |
| 14 | csak IG | MP4 + Story | mentés + MP4 200 | MENTÉS + MÉDIA (mért) |
| 15 | mindkettő | szöveg | **mentés ELUTASÍTVA** (a 8. korlát) | MENTÉS (mért) |
| 16 | mindkettő | egy kép | mentés + csatolás 200 | MENTÉS + MÉDIA (mért) |
| 17 | mindkettő | 2-10 kép | mentés ELFOGADVA | MENTÉS (mért) |
| 18 | mindkettő | MP4 | **mentés ELUTASÍTVA** `video`+both-ra; `reel`+both szintén | MENTÉS (mért) |
| 19 | mindkettő | GIF | **202** (a konverzió platform-független) | MÉDIA (mért) |
| 20 | mindkettő | kép + Story | mentés + csatolás 200 | MENTÉS + MÉDIA (mért) |
| 21 | mindkettő | MP4 + Story | mentés ELFOGADVA, MP4 200; a publikálónál az FB-láb dob, és az IG-láb el sem indul | MENTÉS + MÉDIA mért, publikáló **levezetve** |

## NEM MÉRTEM — tételesen

Nova kikötése: ahol nem tudom megmérni, ott ez álljon, ne üres rubrika.

1. **A publikálás kimenetele egyetlen cellában sem mért.** Valódi Meta-hívás lenne. A 3., 7., 18.
   és 21. cella publikáló-része a kódból van levezetve.
2. **A 18. cella (FB feed-videó + IG Reel EGY posztból) ma nem érhető el**: a mentés a
   `video`+both és a `reel`+both párt egyaránt elutasítja. A per-hálózat oszlopok már megvannak és
   a publikáló már azokból olvas, de a **composer még nem tud külön láb-típust beállítani** — ez a
   2. ütem hátralévő fele. A cella tehát: **nem mértem, mert a képesség még nincs kint.**
3. **A 21. cella viselkedése** (az egész poszt bukik-e, vagy `partial` lesz) publikálás nélkül nem
   dönthető el.
4. **Böngészős végigkattintás** nem történt: a mérés HTTP-szintű.

## Takarítás

17 mérés-poszt létrehozva és mind törölve (`meres-posztok utana: 0`), a teszt-fájlok elvíve,
a 21 soros fixture **érintetlen** (21). A megosztott checkout két érintett fájlja sha-azonosan
visszaállítva.
