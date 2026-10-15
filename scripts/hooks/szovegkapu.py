#!/usr/bin/env python3
"""SZOVEGKAPU: az AI-os, semmitmondo szoveg ("AI-slop") ne menjen ki, es ne csusszon vissza.

MIERT (Zsolt, 2026-10-15, TG 20497/20499/20505/20507; Nova 20734/20748): Eszter egy landing-korben 17 kommentben
dobta ki ugyanazokat a fordulatokat ("Nincs szigorú szabály", "Ha megszereted", "A hét végére összeáll", "És egy kis
extra:"). Egy szabaly-lista nem eleg: a kovetkezo szovegben visszajonnek. Ezert GEPI KAPU, ugynoktol fuggetlenul.

KET RETEG, EGY ADATFAJLBAN (config/szovegszabalyok.json, Copy generalja; az ugyfel-felismeres: config/szovegkapu-ugyfelek.json):
  global       minden ugyfelre
  21napalatt   csak a 21napalatt szovegeire (Eszter hangja), mufaj-cimkevel
Ugyfel: a hivo mondja meg (CLI/pipeline), vagy az ugynok (cwd), vagy a szoveg jele ("21napalatt", "VIP Klub").
Szint: stop = MEGALL, jelez = figyelmeztet. A Google-doksi az adatfajlbol generalodik (egy iranyban).

HAROM HASZNALAT:
  1. PreToolUse hook (stdin: hook-payload). Ugyfel fele meno es Eszterhez meno utak: Drive/Docs-iras, Claude Docs,
     level-MCP (kuldes, piszkozat, save_to_mailbox), curl az InnoMailer / MailerLite / Drive API fele -> STOP talalatnal
     exit 2, olvashatatlan szoveg vagy szabalyfajl eseten is (fail-closed). Telegram -> SOHA nem allit meg, csak jelez
     (Nova 20748: a gazdanak meno valaszt ne akassza meg).
  2. Pipeline (SSH-s utak, amiket a hook nem lat): `from szovegkapu import kapu` vagy CLI:
       szovegkapu.py ellenoriz --fajl <szoveg> [--ugyfel 21napalatt] [--mufaj poszt] [--json]   exit 0 tiszta, 1 stop, 2 vak
  3. SZANDEKOS IDEZES (pl. egy jelentes Eszter elutasitott mondatat idezi):
       szovegkapu.py idezet-engedely --mondat "<a mondat>" --indok "<miert idezed>"
       szovegkapu.py idezet-engedely --fajl <szoveg> --indok "<miert>"   (a fajl minden megallo mondatara, pl. a szabaly-doksi)
     egyszeri, 15 percig ervenyes, naplozott engedely a mondat hash-ere; a szovegbe nem kerul jelolo.

Napló: store/szovegkapu.log (csak dontesek es talalatok, szoveg nelkul, a mondatok elso 120 karakterevel).
"""
import hashlib
import html
import io
import json
import os
import re
import shlex
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SZABALY_UT = os.environ.get('SZOVEGKAPU_SZABALYOK') or os.path.join(REPO, 'config', 'szovegszabalyok.json')
# az ugyfel-felismeres KULON fajl: a szabalyfajlt Copy generalja (build_tiltolista.py), az felulirna
UGYFEL_UT = os.environ.get('SZOVEGKAPU_UGYFELEK') or os.path.join(REPO, 'config', 'szovegkapu-ugyfelek.json')
ENGEDELY_UT = os.environ.get('SZOVEGKAPU_ENGEDELYEK') or os.path.join(REPO, 'store', 'szovegkapu-engedelyek.json')
NAPLO_UT = os.environ.get('SZOVEGKAPU_NAPLO') or os.path.join(REPO, 'store', 'szovegkapu.log')
ENGEDELY_PERC = 15
SZINTEK = ('stop', 'jelez')


# ---------------------------------------------------------------- szabalyok
class SzabalyHiba(Exception):
    pass


def betolt(ut=None):
    ut = ut or SZABALY_UT
    try:
        d = json.load(io.open(ut, encoding='utf-8'))
    except Exception as e:
        raise SzabalyHiba(f'a szabalyfajl nem olvashato ({ut}): {e}')
    ki = []
    for s in d.get('szabalyok') or []:
        for k in ('id', 'reteg', 'mufaj', 'tipus', 'minta', 'szint', 'miert'):
            if k not in s:
                raise SzabalyHiba(f'szabaly hianyos mezo nelkul ({k}): {s.get("id", "?")}')
        if s['szint'] not in SZINTEK:
            raise SzabalyHiba(f'ismeretlen szint ({s["szint"]}): {s["id"]}')
        try:
            rx = re.compile(s['minta']) if s['tipus'] == 'regex' else re.compile(re.escape(s['minta']), re.I)
        except re.error as e:
            raise SzabalyHiba(f'hibas regex ({s["id"]}): {e}')
        ki.append(dict(s, _rx=rx))
    if not ki:
        raise SzabalyHiba(f'a szabalyfajlban nincs szabaly ({ut})')
    ugyfelek = d.get('ugyfelek') or {}
    try:
        ugyfelek = json.load(io.open(UGYFEL_UT, encoding='utf-8')).get('ugyfelek') or ugyfelek
    except Exception:
        pass   # ugyfel-fajl nelkul csak a globalis reteg es a hivo altal megnevezett ugyfel fut
    return ki, ugyfelek


# ---------------------------------------------------------------- szoveg
def tiszta(s):
    """HTML -> sima szoveg; a blokk-hatarok sortoresek, hogy a mondat-bontas ne ragasszon ossze ket bekezdest."""
    s = re.sub(r'(?i)<\s*(br|/p|/li|/h[1-6]|/div|/tr)\s*/?>', '\n', str(s))
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html.unescape(s)
    return re.sub(r'[ \t\xa0]+', ' ', s)


def mondatok(szoveg):
    for sor in tiszta(szoveg).split('\n'):
        sor = sor.strip()
        if not sor:
            continue
        for m in re.split(r'(?<=[.!?])\s+(?=[A-ZÁÉÍÓÖŐÚÜŰ„"(])', sor):
            if m.strip():
                yield m.strip()


def mondat_hash(m):
    return hashlib.sha256(re.sub(r'\s+', ' ', m.strip()).encode('utf-8')).hexdigest()


def ugyfel_ugynok(ugynok):
    """The client an agent talks to on its own channel (config/szovegkapu-ugyfelek.json `ugynokok`), or None.
    Nessa's Telegram bot writes to Eszter (Nova 20786): that Telegram is a client path, STOP and fail-closed."""
    if not ugynok:
        return None
    try:
        for nev, u in (json.load(io.open(UGYFEL_UT, encoding='utf-8')).get('ugyfelek') or {}).items():
            if ugynok in (u.get('ugynokok') or []):
                return nev
    except Exception:
        return None
    return None


def fajl_cimke(ti):
    """A config/szovegkapu-ugyfelek.json `fajlok` resze: egy ISMERT fajl (pl. a 21napalatt posztnaptar) iras-hivasa a fajl
    sajat ugyfelevel es mufajaval fut. Copy 20922: ismeretlen mufajnal ('*') minden mufaj-szabaly fut, igy egy landingre
    szolo STOP posztra is elsult. -> {'ugyfel', 'mufaj', 'nev'} vagy None, ha a hivas nem ismert fajlra megy."""
    try:
        fajlok = json.load(io.open(UGYFEL_UT, encoding='utf-8')).get('fajlok') or {}
    except Exception:
        return None
    for k in ('spreadsheetId', 'documentId', 'fileId', 'id', 'presentationId'):
        v = ti.get(k)
        if isinstance(v, str) and v in fajlok:
            return fajlok[v]
    return None


def ugyfel_felismer(szoveg, ugyfelek, ugynok=''):
    for nev, u in ugyfelek.items():
        if ugynok and ugynok in (u.get('ugynokok') or []):
            return nev
        for j in u.get('jelek') or []:
            if j.lower() in szoveg.lower():
                return nev
    return 'global'


# ---------------------------------------------------------------- engedelyek (szandekos idezes)
def _engedelyek_olvas():
    try:
        d = json.load(io.open(ENGEDELY_UT, encoding='utf-8'))
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _engedelyek_ir(lista):
    os.makedirs(os.path.dirname(ENGEDELY_UT), exist_ok=True)
    tmp = ENGEDELY_UT + '.tmp'
    io.open(tmp, 'w', encoding='utf-8').write(json.dumps(lista, ensure_ascii=False, indent=1))
    os.replace(tmp, ENGEDELY_UT)


def engedely_ad(mondat, indok):
    most = time.time()
    lista = [e for e in _engedelyek_olvas() if e.get('lejar', 0) > most]
    e = {'hash': mondat_hash(mondat), 'mondat': mondat[:200], 'indok': indok, 'adva': most, 'lejar': most + ENGEDELY_PERC * 60}
    lista.append(e)
    _engedelyek_ir(lista)
    naplo('ENGEDELY', [{'szabaly': '-', 'mondat': mondat, 'indok': indok}])
    return e


def _engedely_felhasznal(hashek):
    """Az ervenyes engedelyekbol azokat, amelyek hash-e itt van, felhasznalja (egyszeri). Visszaadja a felhasznalt hash-eket."""
    most = time.time()
    lista = [e for e in _engedelyek_olvas() if e.get('lejar', 0) > most]
    hasznalt, marad = set(), []
    for e in lista:
        if e['hash'] in hashek and e['hash'] not in hasznalt:
            hasznalt.add(e['hash'])
        else:
            marad.append(e)
    if hasznalt:
        _engedelyek_ir(marad)
    return hasznalt


# ---------------------------------------------------------------- az ellenorzes
def ellenoriz(szoveg, szabalyok, ugyfel='global', mufaj='*'):
    """Talalatok listaja: {szabaly, szint, miert, jo_pelda, mondat, talalat}. Ismeretlen mufaj ('*') = minden mufaj-szabaly fut."""
    ki = []
    ms = list(mondatok(szoveg))
    for sz in szabalyok:
        if sz['reteg'] not in ('global', ugyfel):
            continue
        if mufaj != '*' and '*' not in sz['mufaj'] and mufaj not in sz['mufaj']:
            continue
        for m in ms:
            t = sz['_rx'].search(m)
            if t:
                ki.append({'szabaly': sz['id'], 'szint': sz['szint'], 'miert': sz['miert'], 'jo_pelda': sz.get('jo_pelda', ''),
                           'mondat': m, 'talalat': t.group(0)})
    return ki


def kapu(szoveg, ugyfel=None, mufaj='*', ugynok='', szabaly_ut=None):
    """Pipeline-belepo: (stop_talalatok, jelzo_talalatok). Szabalyhiba -> SzabalyHiba (a hivo alljon meg)."""
    szabalyok, ugyfelek = betolt(szabaly_ut)
    if not ugyfel:
        ugyfel = ugyfel_felismer(szoveg, ugyfelek, ugynok)
    t = ellenoriz(szoveg, szabalyok, ugyfel, mufaj)
    stop = [x for x in t if x['szint'] == 'stop']
    if stop:
        hasznalt = _engedely_felhasznal({mondat_hash(x['mondat']) for x in stop})
        if hasznalt:
            naplo('IDEZET-ATENGEDVE', [x for x in stop if mondat_hash(x['mondat']) in hasznalt])
        stop = [x for x in stop if mondat_hash(x['mondat']) not in hasznalt]
    return stop, [x for x in t if x['szint'] == 'jelez']


def pipeline(darabok, ugyfel, mufaj, ut_cimke):
    """Pipeline-belepo a csomag-szkripteknek (InnoSocial, InnoPlan, landing): darabok = [(cimke, szoveg), ...].
    Vissza: (stop_uzenet vagy None, jelzes_uzenet vagy None). Barmilyen hiba kivetelt dob: a hivo alljon meg (fail-closed)."""
    stop_sor, jelez_sor = [], []
    for cimke, szoveg in darabok:
        if not (szoveg or '').strip():
            continue
        stop, jelez = kapu(szoveg, ugyfel, mufaj)
        if stop:
            naplo('STOP', stop, ut_cimke)
            stop_sor.append(szoveges(stop, f'{cimke}:'))
        if jelez:
            naplo('JELEZ', jelez, ut_cimke)
            jelez_sor.append(szoveges(jelez, f'{cimke}:'))
    stop_txt = None
    if stop_sor:
        stop_txt = ('SZOVEGKAPU: megalltam, tiltott fordulat (' + ut_cimke + '):\n' + '\n'.join(stop_sor) +
                    '\nJavitsd a mondatot. Ha SZANDEKOSAN idezed: python3 ' + os.path.join(REPO, 'scripts/hooks/szovegkapu.py') +
                    ' idezet-engedely --mondat "<a mondat>" --indok "<miert>"')
    return stop_txt, (('SZOVEGKAPU jelzes (' + ut_cimke + ', nem allitott meg):\n' + '\n'.join(jelez_sor)) if jelez_sor else None)


def szoveges(talalatok, cim):
    sorok = [cim]
    for x in talalatok:
        sorok.append(f'  [{x["szabaly"]}] „{x["mondat"][:160]}” -- {x["miert"]}' + (f' Jó példa: „{x["jo_pelda"]}”' if x.get('jo_pelda') else ''))
    return '\n'.join(sorok)


def naplo(dontes, talalatok, ut_cimke=''):
    try:
        os.makedirs(os.path.dirname(NAPLO_UT), exist_ok=True)
        with io.open(NAPLO_UT, 'a', encoding='utf-8') as f:
            for x in talalatok or [{}]:
                f.write(json.dumps({'ido': time.strftime('%Y-%m-%dT%H:%M:%S'), 'dontes': dontes, 'ut': ut_cimke,
                                    'szabaly': x.get('szabaly', ''), 'mondat': (x.get('mondat') or '')[:120],
                                    'indok': x.get('indok', '')}, ensure_ascii=False) + '\n')
    except Exception:
        pass


# ---------------------------------------------------------------- hook: mi a kimeno szoveg
TELEGRAM_RX = re.compile(r'telegram.*(reply|edit_message)', re.I)
DOCS_RX = re.compile(r'^mcp__google-drive__(createGoogleDoc|updateGoogleDoc|insertText|createDocFromHTML|findAndReplaceInDoc|'
                     r'addComment|replyToComment|createTextFile|updateTextFile|createGoogleSlidesTextBox|setElementText|'
                     r'replaceAllTextInSlides|updateGoogleSlides|addDocumentTab)$|'
                     r'^mcp__claude_ai_Google_Drive__(create_file|update_file)$|'
                     r'^mcp__claude_ai_Claude_Docs__(batch|update|create)$')
# Sheets-iras: CSAK a `fajlok`-ban felsorolt tablakra fut (a posztnaptar). Minden mas tablazat-iras kivul marad, mert a
# globalis reteg (pl. a gondolatjel) egy "Budapest - Szeged" cellan is megallna -- az nem ugyfelszoveg.
SHEETS_RX = re.compile(r'^mcp__google-drive__(updateGoogleSheet|updateGoogleSheetIfUnchanged|batchUpdateGoogleSheetValues|'
                       r'appendSpreadsheetRows)$')
EMAIL_RX = re.compile(r'(^mcp__email__(send_email|save_to_mailbox)$)|(send_email|create_draft|draft_email|update_draft)$|'
                      r'gmail__(reply|reply_all|send_message|forward)$', re.I)
# a mezok, amelyek NEM szoveg (azonositok, utak, cimzettek) -- ezeket nem vizsgaljuk
NEM_SZOVEG = re.compile(r'(?i)(^|_)(id|ids|url|uri|path|file_path|mime.*|mimetype|to|cc|bcc|from|recipient.*|account|email|'
                        r'folder.*|parent.*|drive.*|range|index|format|font.*|color|style|type|kind|engine|ref|object|'
                        r'container|version|opid|answering|verbose|role|chat_id|reply_to|message_id|files|emoji)$')
CURL_CELOK = (('innomailer.hu', 'hirlevel'), ('connect.mailerlite.com', 'hirlevel'), ('googleapis.com/upload/drive', '*'))
CURL_SZOVEG_KULCS = re.compile(r'(?i)^(subject|name|title|content|html|plain|plain_text|text|body|preheader|description|message)$')


def stringek(o, kulcs=''):
    if isinstance(o, str):
        if kulcs and NEM_SZOVEG.search(kulcs):
            return []
        return [o]
    if isinstance(o, dict):
        ki = []
        for k, v in o.items():
            ki += stringek(v, str(k))
        return ki
    if isinstance(o, list):
        ki = []
        for v in o:
            ki += stringek(v, kulcs)
        return ki
    return []


def _heredoc(cmd):
    m = re.search(r"<<-?\s*'?(\w+)'?[^\n]*\n(.*?)\n\1(\s|$)", cmd, re.S)
    return m.group(2) if m else None


def curl_szoveg(cmd, cwd):
    """(mufaj, szoveg) ha a parancs egy figyelt cel fele kuld curl-lel; (None, None) ha nem ilyen; (mufaj, None) ha igen, de
    a torzs nem olvashato (a hivo ilyenkor megall)."""
    if 'curl' not in cmd:
        return None, None
    test = re.sub(r"<<-?\s*'?(\w+)'?[^\n]*\n.*?\n\1(\s|$)", ' ', cmd, flags=re.S)
    try:
        # punctuation_chars: a `'{...}';` alakban a `;` kulon token lesz, kulonben a JSON-hoz tapad, es a torzs nyersen megy at
        lex = shlex.shlex(test, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        tok = list(lex)
    except ValueError:
        tok = test.split()
    mufaj = None
    for t in tok:
        for cel, mf in CURL_CELOK:
            if cel in t and not t.startswith('{'):
                mufaj = mf
    if mufaj is None:
        return None, None
    darabok = []
    for i, t in enumerate(tok):
        if t in ('-d', '--data', '--data-raw', '--data-binary', '--data-urlencode', '-F', '--form') and i + 1 < len(tok):
            v = tok[i + 1]
            if v == '@-':
                h = _heredoc(cmd)
                if h is None:
                    return mufaj, None
                darabok.append(h)
            elif v.startswith('@'):
                p = v[1:]
                p = p if os.path.isabs(p) else os.path.join(cwd or '.', p)
                try:
                    darabok.append(io.open(p, encoding='utf-8').read())
                except Exception:
                    return mufaj, None
            else:
                darabok.append(v)
    if not darabok:
        return mufaj, ''
    szoveg = []
    for d in darabok:
        try:
            o = json.loads(d)
            szoveg += [v for k, v in _kulcsos(o) if CURL_SZOVEG_KULCS.match(k)]
        except Exception:
            szoveg.append(d)
    return mufaj, '\n'.join(szoveg)


def _kulcsos(o, k=''):
    if isinstance(o, dict):
        for kk, v in o.items():
            yield from _kulcsos(v, str(kk))
    elif isinstance(o, list):
        for v in o:
            yield from _kulcsos(v, k)
    elif isinstance(o, str):
        yield k, o


def ugynok_cwd(cwd):
    m = re.search(r'/agents/([^/]+)', cwd or '')
    return m.group(1) if m else ''


def hook():
    try:
        p = json.load(sys.stdin)
    except Exception:
        return 0
    tool = p.get('tool_name') or ''
    ti = p.get('tool_input') or {}
    cwd = p.get('cwd') or ''
    ugynok = ugynok_cwd(cwd)
    if TELEGRAM_RX.search(tool):
        szoveg, mufaj = '\n'.join(str(ti.get(k) or '') for k in ('text', 'caption', 'message')), '*'
        # an agent whose own bot writes to a client (Nessa -> Eszter): a client path like the others, not the internal Telegram
        ut = 'telegram-ugyfel' if ugyfel_ugynok(ugynok) else 'telegram'
    elif DOCS_RX.search(tool) or SHEETS_RX.search(tool):
        f = fajl_cimke(ti)
        if SHEETS_RX.search(tool) and not f:
            return 0
        ut, mufaj, szoveg = ('sheet' if SHEETS_RX.search(tool) else 'docs'), (f or {}).get('mufaj') or '*', '\n'.join(stringek(ti))
        if f:
            ut += ':' + (f.get('nev') or 'ismert fajl')
    elif EMAIL_RX.search(tool):
        ut, mufaj, szoveg = 'level', '*', '\n'.join(stringek(ti))
    elif tool == 'Bash':
        mufaj, szoveg = curl_szoveg(str(ti.get('command') or ''), cwd)
        if mufaj is None:
            return 0
        ut = 'curl'
    else:
        return 0
    if ut != 'telegram' and szoveg is None:
        print('SZOVEGKAPU: a kimeno szoveg nem olvashato ki (pl. @fajl relativ uttal, vagy hianyzo fajl), ezert megallok. '
              'Add at a torzset olvashato alakban (abszolut @fajl, vagy -d / heredoc).', file=sys.stderr)
        naplo('VAK-STOP', [], ut)
        return 2
    if not (szoveg or '').strip():
        return 0
    try:
        f = fajl_cimke(ti) if ut.startswith(('docs', 'sheet')) else None
        stop, jelez = kapu(szoveg, (f or {}).get('ugyfel'), mufaj, ugynok)
    except SzabalyHiba as e:
        if ut == 'telegram':
            print(json.dumps({'systemMessage': f'SZOVEGKAPU nem futott (Telegram, atengedve): {e}'}, ensure_ascii=False))
            return 0
        print(f'SZOVEGKAPU: {e} -- ugyfel fele meno uton ilyenkor megallok (fail-closed).', file=sys.stderr)
        naplo('SZABALYHIBA-STOP', [], ut)
        return 2
    if stop and ut != 'telegram':
        naplo('STOP', stop, ut)
        print(szoveges(stop, f'SZOVEGKAPU: megalltam, {len(stop)} tiltott fordulat ({ut}):') +
              '\nJavitsd a mondatot. Ha SZANDEKOSAN idezed (pl. egy jelentesben): '
              'python3 ' + os.path.join(REPO, 'scripts/hooks/szovegkapu.py') + ' idezet-engedely --mondat "<a mondat>" --indok "<miert>"'
              + (('\n' + szoveges(jelez, 'Emellett jelzes:')) if jelez else ''), file=sys.stderr)
        return 2
    jelzes = (stop if ut == 'telegram' else []) + jelez
    if jelzes:
        naplo('JELEZ', jelzes, ut)
        print(json.dumps({'systemMessage': szoveges(jelzes, f'SZOVEGKAPU jelzes ({ut}, nem allitott meg):')}, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------- CLI
def cli(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd')
    e = sub.add_parser('ellenoriz')
    e.add_argument('--fajl', required=True)
    e.add_argument('--ugyfel', default=None)
    e.add_argument('--mufaj', default='*')
    e.add_argument('--json', action='store_true')
    g = sub.add_parser('idezet-engedely')
    g.add_argument('--mondat', default=None)
    g.add_argument('--fajl', default=None, help='a fajl MINDEN megallo mondata kap egyszeri engedelyt (pl. a szabaly-doksi rossz peldai)')
    g.add_argument('--ugyfel', default=None)
    g.add_argument('--indok', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'idezet-engedely':
        if len(a.indok.strip()) < 5:
            print('az --indok kotelezo (miert idezed)'); return 2
        if bool(a.mondat) == bool(a.fajl):
            print('pontosan egy kell: --mondat vagy --fajl'); return 2
        if a.mondat:
            x = engedely_ad(a.mondat, a.indok)
            print(f'engedely: egyszeri, {ENGEDELY_PERC} percig, hash {x["hash"][:12]}'); return 0
        try:
            szabalyok, ugyfelek = betolt()
            t = io.open(a.fajl, encoding='utf-8').read()
        except (OSError, SzabalyHiba) as ex:
            print(f'VAK: {ex}'); return 2
        ugyfel = a.ugyfel or ugyfel_felismer(t, ugyfelek)
        ms = sorted({x['mondat'] for x in ellenoriz(t, szabalyok, ugyfel, '*') if x['szint'] == 'stop'})
        for m in ms:
            engedely_ad(m, a.indok + f' (fajl: {a.fajl})')
        print(f'engedely: {len(ms)} mondat, egyszeri, {ENGEDELY_PERC} percig (fajl: {a.fajl})'); return 0
    if a.cmd == 'ellenoriz':
        try:
            t = io.open(a.fajl, encoding='utf-8').read()
            stop, jelez = kapu(t, a.ugyfel, a.mufaj)
        except (OSError, SzabalyHiba) as ex:
            print(f'VAK: {ex}'); return 2
        if a.json:
            print(json.dumps({'stop': stop, 'jelez': jelez}, ensure_ascii=False, indent=1))
        else:
            if stop:
                print(szoveges(stop, f'STOP ({len(stop)}):'))
            if jelez:
                print(szoveges(jelez, f'JELEZ ({len(jelez)}):'))
            if not stop and not jelez:
                print('tiszta')
        return 1 if stop else 0
    ap.print_help(); return 2


def hook_vedett():
    """Egy varatlan kivetel exit 1 lenne, amit a Claude Code NEM blokkolonak vesz: az ugyfel fele meno uton ez nema
    atengedes volna. Ezert a hook hibaja exit 2, kiveve a Telegramot (ott fail-open, Nova 20748 b)."""
    nyers = sys.stdin.read()
    try:
        sys.stdin = io.StringIO(nyers)
        return hook()
    except Exception as e:
        try:
            bemenet = json.loads(nyers)
            tool = bemenet.get('tool_name') or ''
            cmd = str((bemenet.get('tool_input') or {}).get('command') or '')
        except Exception:
            tool, cmd, bemenet = '', '', {}
        if tool == 'Bash' and not any(cel in cmd for cel, _ in CURL_CELOK):
            return 0   # a Bash-hivasok tulnyomo resze nem ugyfel fele megy: ott a kapu hibaja ne allitsa meg a flottat
        if TELEGRAM_RX.search(tool) and not ugyfel_ugynok(ugynok_cwd(bemenet.get('cwd') if isinstance(bemenet, dict) else '')):
            print(json.dumps({'systemMessage': f'SZOVEGKAPU hiba (Telegram, atengedve): {type(e).__name__}: {e}'}, ensure_ascii=False))
            return 0
        naplo('HIBA-STOP', [], tool)
        print(f'SZOVEGKAPU: belso hiba ({type(e).__name__}: {e}) -- ugyfel fele meno uton megallok (fail-closed).', file=sys.stderr)
        return 2


if __name__ == '__main__':
    if len(sys.argv) > 1:
        sys.exit(cli(sys.argv[1:]))
    sys.exit(hook_vedett())
