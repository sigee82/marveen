# InnoWorx: a 21 cellás átvételi mátrix — mérve

**Mérvadó futás:** `feat/iw-halozatonkenti-tipus-es-gif`, commit **`802de0de`**, nulla nem-commitolt
változással. Külön, eldobható konténer szolgálta ki ezt a fát (8003-as port), a meglévő stackhez
nem nyúltam, és a mérés végén leállt. A mérő **azonosság-kapuval** indul: megáll, ha a
`DB_NAME` nem `innoworx`.

> **Ez a lokális InnoWorx stack, nem a prod.** A 302 valódi poszt a `napalatt_innoworx_prod`-ban
> van; oda nincs utam. A fixture 14 sora a **prod eloszlására** van mintázva (Nova mérése), és a
> két preservation-invariánst pontosan tükrözi: média nélküli sztori kimenő státuszban **0**, és
> kikötés-sértő sor **2, ebből kimenő 0**.

## MENTÉS-réteg — mind a 18 pár (valódi HTTP)

| típus | facebook | instagram | both |
|---|---|---|---|
| text_only | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| single_image | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| carousel | ELFOGADVA | ELFOGADVA | ELFOGADVA |
| video | ELFOGADVA | **ELUTASÍTVA** | **ELUTASÍTVA** |
| reel | **ELUTASÍTVA** | ELFOGADVA | **ELUTASÍTVA** |
| story | ELFOGADVA | ELFOGADVA | ELFOGADVA |

Az öt elutasítás saját mondattal; a `text_only`-ban **nincs** „JELENLEG", mert az Instagram
korlátja, nem a miénk. **Azonos a kiváltott eredményével.**

## MÉDIA-réteg (valódi HTTP)

| anyag | eredmény |
|---|---|
| PNG | **200** — csatolva |
| GIF | **202** — átalakítás sorba téve, a mondattal |
| MP4 → `single_image` | **400** — elutasítva |

## A 18. cella — a 2. ütem átvételi feltétele

| kérdés | eredmény |
|---|---|
| (a) a felület engedi-e | **igen** — `both`-nál két választó; az FB-láb listájából a `reel` kimarad |
| (b) ha tilt, kimondja-e | **igen** — „A Facebook-lábon a Reel JELENLEG nem megy…" |
| (c) a `save_post` | **igen** — `fb=video` + `ig=reel` → `success` |
| **visszaolvasó mérő** | **`fb=video ig=reel split=1`** — a kért érték áll, nem a szinkron alapértelmezése |
| (d) a publikáló lábanként | **levezetve** (valódi Meta-hívás nem történt) |
| (e) a tiltás látszik-e | **igen**, két szinten |

**És a Nova jelezte él, ami itt valódi adaton áll:** a 2 `reel`+facebook piszkozat a válaszban
`fb=reel`-lel jön vissza, és a per-láb választó **megjelölve** mutatja („Reel — ezen a hálózaton
nem megy") ahelyett, hogy kiszűrné. Kiszűrve a böngésző az első opciót mutatná, és a következő
mentés **némán átírná** a kolléga típusát.

## Preservation — a „semmi nem törhet el" mérései

- média nélküli sztori **kimenő** státuszban: **0** — a kapu az **átmenetre** áll, nem az
  állapotra, tehát egy már `approved` poszt nem is megy át rajta
- kikötés-sértő sor: **2, ebből kimenő 0**; a változatlan mentés **elutasításra kerül**, de
  **a sor megmarad** — mérve
- rés-detektor (mindkét láb NULL): **0**
- a backfill leképezése: **0 eltérés / 14 ellenőrzött sorból**

## NEM MÉRTEM — tételesen

1. **A publikálás kimenetele egyetlen cellában sem mért** — valódi Meta-hívás lenne.
2. **A GIF-konverzió maga**: az InnoWorx konténerben **nincs ffmpeg**. A sor, a dispatch, a
   hibaágak és a csatolás mérve; a konverziót a kiváltotton mértem, **azonos kóddal**.
3. **A 302 valódi soron semmi**: a prod-mérés Nováé, a rés-detektor ott a végső kapu.
4. **Böngészős végigkattintás** nem történt: a mérés HTTP-szintű.

## Eltérés a kiváltotthoz képest, amit felírtam és NEM javítottam

A videó-elutasítás üzenete az InnoWorxon **angolul** szól: *„Video upload only valid for reel /
story / video post types"* — a kiváltotton magyarul. Nem ennek a munkának a tárgya, de a kezelő
magyar felületen kap angol mondatot.

## Takarítás

A mérés-posztok törölve, a teszt-fájlok elvíve, a **fixture 14 sora érintetlen**, az eldobható
konténer leállt, a megosztott checkout tiszta.
