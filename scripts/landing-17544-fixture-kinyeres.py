#!/usr/bin/env python3
"""A 17544 MAI TAROLT ertekeit allitja elo fixture-kent, KET FUGGETLEN FORRASBOL.

A tarolt ertek (HTML-lel egyutt) kivulrol nem olvashato: a renderelt oldal texturizalt es
a tagok az innerText-bol eltunnek. Ket forrasunk van ra, es EGYIKET SEM HISSZUK EL MAGABAN:

  1. A 2026-09-21 09:27-es deploy parositasa a git-bol (`git show <ref>:...parositas.json`).
     Azok a `uj` ertekek mentek be, es a PHP mezonkent vissza is olvasta oket (17/17).
  2. Az ELO oldal ma mert renderelt szovege (`landing-17544-elo-allapot.json`).

A KETTOT OSSZEVETJUK: az 1-es ertekbol tagokat szedve, whitespace-t osszevonva PONTOSAN a
2-es szoveget kell kapni. Ha nem, akkor vagy az oldal mozdult el azota, vagy a git-ref
rossz -- mindket esetben LELET, es nem szabad fixture-t epiteni ra.
(A texturize itt nem zavar: a mert ertekekben nincs olyan karakter, amit atalakitana. Ha
egyszer lesz, ez az osszevetes fog elhasalni, es az a helyes viselkedes -- nem a csend.)

FUTTATAS:  python3 scripts/landing-17544-fixture-kinyeres.py [git-ref]
"""
import io, json, re, subprocess, sys

ELO = '/Users/macmini/marveen/scripts/landing-17544-elo-allapot.json'
KI = '/Users/macmini/marveen/scripts/landing-17544-fixture.json'
ALAP_REF = 'd1362da'   # a 2026-09-21 12:0x-es deployt hordozo parositas
UT = 'scripts/landing-17544-parositas.json'


def tiszta(s):
    s = re.sub(r'<(/p|/li|br\s*/?|/h[1-6])\s*>', ' ', s, flags=re.I)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()


def main():
    ref = sys.argv[1] if len(sys.argv) > 1 else ALAP_REF
    r = subprocess.run(['git', 'show', f'{ref}:{UT}'], capture_output=True, text=True,
                       cwd='/Users/macmini/marveen')
    if r.returncode != 0:
        raise SystemExit(f'HIBA: a {ref}:{UT} nem olvashato ki.\n  {r.stderr.strip()}')
    deploy = {f"{p['elem_id']}|{p['ut']}": p['uj'] for p in json.loads(r.stdout)}
    elo = json.load(io.open(ELO, encoding='utf-8'))['mezok']

    hiba = []
    for kulcs, mert in elo.items():
        if kulcs not in deploy:
            hiba.append(f'{kulcs}: nincs a {ref} parositasaban'); continue
        a, b = tiszta(deploy[kulcs]), mert['szoveg'].strip()
        if a != b:
            hiba.append(f'{kulcs}:\n      deploy: {a[:110]}\n      elo:    {b[:110]}')
    tobblet = sorted(set(deploy) - set(elo))
    if tobblet:
        hiba.append(f'a {ref} parositasaban van, az elo meresben nincs: {", ".join(tobblet)}')
    if hiba:
        raise SystemExit('HIBA -- a ket forras NEM egyezik, fixture-t nem epitek:\n  - '
                         + '\n  - '.join(hiba))

    json.dump(deploy, io.open(KI, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'@@ {len(deploy)} mezo tarolt erteke -> {KI}')
    print(f'@@ ket fuggetlen forras EGYEZIK: git {ref} parositas  ==  az elo oldal mai meresе')
    tagos = sum(1 for k, v in deploy.items() if k.endswith('|editor') and re.search(r'<[^>]+>', v))
    print(f'@@ az ot editor-mezobol {tagos} hordoz HTML-taget (a markup a helyen van).')


if __name__ == '__main__':
    sys.exit(main())
