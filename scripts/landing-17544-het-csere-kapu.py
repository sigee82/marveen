#!/usr/bin/env python3
"""A HET csere ellenorzese a GENERALT PAROSITASON, nem Copy fajljan.

MIERT ITT, ha Copy fajljat Nova mar visszamerte: az o merese a FORRAST igazolja. Ez a
szkript a LANCOT igazolja -- azt, hogy a forrasbol a generator utan is ugyanaz jon ki,
es hogy amit a PHP be fog irni, az tenyleg a het cserét hordozza. Ket kulon allitas:
"Copy jol irta le" es "a szkript ezt fogja beirni".

ES EGY SZAM, AMI KET DOLGOT JELENT: a het CSERE OT elementor-MEZOBE esik (a hero-mondat
es a hero-bullet ugyanabba, a 2. szekcio ket valtoztatasa is ugyanabba). A generator
ezert 5 valtozo mezot jelent -- ez NEM ket elmaradt csere.
"""
import io, json, re, sys

PAROSITAS = '/Users/macmini/marveen/scripts/landing-17544-parositas.json'

# (nev, mezo-kulcs, aminek BENT kell lennie, aminek KINT kell lennie)
CSEREK = [
    ('1 hero-mondat', 'b3e8629|editor',
     'készíts velünk laktató reggeliket egyszerű alapanyagokból',
     'rakjuk össze együtt azt a reggelit'),
    ('2 hero-bullet 1. sora', 'b3e8629|editor',
     '7 laktató reggeli', '6 laktató reggeli és 1 reggeli ital'),
    ('3 ajanlo (Eszter)', '370bdfea|editor',
     'Az egészséges reggeli kihívás segít megismerni, mitől lesz egy reggeli igazán laktató',
     'hogy reggelente ne Neked kelljen ötletelni'),
    ('4 2. szekcio zarasa', '370bdfea|editor',
     'kipróbálunk hét laktató reggelit', 'hat laktató reggelit meg egy reggeli italt'),
    ('5 Mire szamithatsz 1. bek.', '17c1f49|editor',
     'Hét különböző reggeli, és mind a hét sós.',
     'Lesz köztük gyors serpenyős reggeli'),
    ('6 sebesseg-sor', '360da42|icon_list.2.text',
     'negyedóra alatt is összeáll egy laktató reggeli',
     'néhány perc is elég lehet'),
    ('7 "neked" kisbetus', '360da42|icon_list.3.text',
     'ha nem neked kell kitalálni', 'ha nem Neked kell kitalálni'),
]


def main():
    parok = {f"{p['elem_id']}|{p['ut']}": p for p in
             json.load(io.open(PAROSITAS, encoding='utf-8'))}
    hiba = 0
    for nev, kulcs, bent, kint in CSEREK:
        p = parok.get(kulcs)
        if p is None:
            print(f'  !! {nev}: NINCS ilyen mezo a parositasban ({kulcs})'); hiba += 1; continue
        uj = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', p['uj'])).strip()
        van_bent = bent in uj
        van_kint = kint in uj
        jel = 'OK  ' if (van_bent and not van_kint) else '!! '
        print(f'  {jel}{nev}  [{kulcs}]  uj-alak: {"BENT" if van_bent else "HIANYZIK"}, '
              f'regi-alak: {"MEG BENT !!" if van_kint else "kint"}')
        if not van_bent or van_kint:
            hiba += 1

    # A SAJAT KAPUNK LELETEI a generalt ertekeken -- ugyanaz a harom, amit a
    # szoveg-kapu az elo oldalon mer, csak itt MAR A BEVITEL ELOTT.
    egyben = re.sub(r'<[^>]+>', ' ', '\n'.join(p['uj'] for p in parok.values()))
    for nev, minta in [('nagykotojel', '[–—]'),
                       ('nagybetus "Neked"', r'\bNeked\b'),
                       ('elettani szokincs', 'vércukor|inzulin|anyagcsere|glikémiás'),
                       ("'allitottam ossze'", 'állítottam össze')]:
        n = len(re.findall(minta, egyben))
        print(f'  {"OK  " if n == 0 else "!! "}{nev}: {n}')
        if n:
            hiba += 1

    # POZITIV KONTROLL A DETEKTORRA: a mintaknak MUKODNIUK kell. Ha egy szandekosan
    # elrontott szovegen sem fognak, akkor a fenti nullak nem leletek, hanem vak meres.
    proba = 'ez egy – teszt, ahol Neked szol, es vércukor is van, meg állítottam össze'
    talalt = sum(1 for m in ['[–—]', r'\bNeked\b', 'vércukor', 'állítottam össze']
                 if re.search(m, proba))
    if talalt != 4:
        print(f'  !! POZITIV KONTROLL BUKOTT: a negy mintabol {talalt} fogott a probaszovegen.')
        print('     A fenti nullak ezert NEM leletek -- a meres romlott el.')
        return 2
    print(f'  (pozitiv kontroll: a negy minta mind a negy hibat megfogja a probaszovegen)')

    print()
    print(f'>>> {len(CSEREK)} csere, {len(set(k for _, k, _, _ in CSEREK))} elementor-mezoben. '
          f'{"MIND RENDBEN." if hiba == 0 else f"{hiba} HIBA."}')
    return 0 if hiba == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
