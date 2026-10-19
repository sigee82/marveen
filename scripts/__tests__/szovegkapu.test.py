#!/usr/bin/env python3
"""SZOVEGKAPU (scripts/hooks/szovegkapu.py) -- pozitiv es negativ kontroll minden uton (Nova 20734/20748).

  python3 scripts/__tests__/szovegkapu.test.py

POZITIV: Eszter 2026-10-15-en elutasitott mondatai (fixtures/szovegkapu/eszter-elutasitott-2026-10-15.json) MIND akadjanak.
NEGATIV: Eszter jovahagyott alvas-landing szovege (rev 734) NE akadjon (jelzes lehet: 'nem X, hanem Y').
Minden ut kulon: Drive/Docs MCP, Claude Docs, level-MCP (save_to_mailbox is), curl InnoMailer/MailerLite, Telegram (fail-open),
pipeline (kapu()), CLI; plusz a szandekos idezes es a fail-closed szabalyhiba.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

ITT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(ITT))
KAPU = os.path.join(REPO, 'scripts', 'hooks', 'szovegkapu.py')
FIX = os.path.join(ITT, 'fixtures', 'szovegkapu')
TMP = tempfile.mkdtemp(prefix='szovegkapu-teszt-')
ENV = dict(os.environ, SZOVEGKAPU_ENGEDELYEK=os.path.join(TMP, 'eng.json'), SZOVEGKAPU_NAPLO=os.path.join(TMP, 'naplo.log'))

poz = json.load(io.open(os.path.join(FIX, 'eszter-elutasitott-2026-10-15.json'), encoding='utf-8'))
# a jovahagyott szoveg a doksi-vaz NELKUL (Copy kontroll.py approved_texts(): szekciocimek, '->' linkek, mezocimkek kivagva)
NEG = {m: io.open(os.path.join(FIX, f'alvas-rev734-{m}-jovahagyott.txt'), encoding='utf-8').read() for m in ('landing', 'hirlevel')}
neg = NEG['landing'] + '\n' + NEG['hirlevel']

ok = bad = 0
def check(nev, cond, reszlet=''):
    global ok, bad
    if cond:
        ok += 1; print('ok    -', nev)
    else:
        bad += 1; print('BUKIK -', nev, ('::' + str(reszlet)[:300]) if reszlet else '')

def hook(payload, env=None):
    r = subprocess.run([sys.executable, KAPU], input=json.dumps(payload), capture_output=True, text=True, env=env or ENV)
    return r.returncode, r.stdout, r.stderr

NESSA = '/Users/macmini/marveen/agents/nessa'
UTAK = {
    'Drive (google-drive MCP createGoogleDoc)': lambda t: {'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'title': 'Landing', 'content': t, 'parentFolderId': 'x'}, 'cwd': NESSA},
    'Drive (claude.ai update_file)': lambda t: {'tool_name': 'mcp__claude_ai_Google_Drive__update_file', 'tool_input': {'fileId': 'abc', 'content': t}, 'cwd': NESSA},
    'Claude Docs (batch)': lambda t: {'tool_name': 'mcp__claude_ai_Claude_Docs__batch', 'tool_input': {'container': {'kind': 'project', 'id': 'p1'}, 'batch': [{'markdown': t}]}, 'cwd': NESSA},
    'levelpiszkozat (mcp__email__save_to_mailbox)': lambda t: {'tool_name': 'mcp__email__save_to_mailbox', 'tool_input': {'to': ['x@y.hu'], 'subject': 'Alvás', 'body': t}, 'cwd': NESSA},
    'InnoMailer (curl -d JSON)': lambda t: {'tool_name': 'Bash', 'tool_input': {'command': "curl -s -X POST https://innomailer.hu/api/inno/v1/campaigns -H 'Content-Type: application/json' -d " + json.dumps(json.dumps({'name': 'Alvás', 'subject': 'Indul', 'html': '<p>' + t.replace('\n', '</p><p>') + '</p>'}, ensure_ascii=False))}, 'cwd': NESSA},
    'MailerLite (curl --data-binary @- heredoc)': lambda t: {'tool_name': 'Bash', 'tool_input': {'command': "curl -s https://connect.mailerlite.com/api/campaigns --data-binary @- <<'JSON'\n" + json.dumps({'name': 'x', 'emails': [{'subject': 'Alvás', 'content': t}]}, ensure_ascii=False) + "\nJSON"}, 'cwd': NESSA},
}

# --- minden ugyfel-ut: pozitiv akad, negativ nem
for nev, mk in UTAK.items():
    akadt = 0
    for p in poz:
        rc, out, err = hook(mk(p['mondat']))
        akadt += (rc == 2)
    check(f'{nev}: POZITIV -- mind a {len(poz)} elutasitott mondat megall', akadt == len(poz), f'{akadt}/{len(poz)}')
    rc, out, err = hook(mk(neg))
    check(f'{nev}: NEGATIV -- a jovahagyott rev 734 nem all meg (jelzes lehet)', rc == 0, err)

# --- a megallas a mondatot es a szabalyt nevezi meg
rc, out, err = hook(UTAK['Drive (google-drive MCP createGoogleDoc)']('Ez nagyon jó. Ha megszereted, maradj velünk a VIP Klubban!'))
check('a megallas szovege: a mondat, a szabaly-id es a kijelolt idezes-ut', rc == 2 and 'G-ha-megszereted' in err and 'Ha megszereted, maradj' in err and 'idezet-engedely' in err, err)

# --- jelzo szint: a 'nem X, hanem Y' nem allit meg, de jelez
rc, out, err = hook(UTAK['Drive (google-drive MCP createGoogleDoc)']('Nem az a cél, hogy rohanj, hanem az, hogy pihenj.'))
check("'nem X, hanem Y' = JELZO: atmegy, systemMessage-ben jelez", rc == 0 and 'G-nem-x-hanem-y' in out, (rc, out, err))

# --- ugyfel-reteg: a 21napalatt szabaly csak 21napalatt szovegen (vagy Nessa cwd-jen) fut
klub = 'A klubban minden héten új recept vár.'
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': klub}, 'cwd': '/Users/macmini/marveen/agents/pixel'})
check('21napalatt-reteg: masik ugyfel szovegen (pixel cwd, jel nelkul) a "klub" szo nem all meg', rc == 0, err)
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': klub}, 'cwd': NESSA})
check('21napalatt-reteg: Nessa cwd-jen a csupasz "klub" megall (mindig VIP Klub)', rc == 2 and 'E-vip-klub' in err, err)
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': 'A 21napalatt ' + klub}, 'cwd': '/Users/macmini/marveen/agents/pixel'})
check('21napalatt-reteg: a szoveg jele ("21napalatt") barhonnan bekapcsolja', rc == 2, err)

# --- belso Telegram (Nova, a tobbi agens): SOHA nem allit meg, csak jelez (Nova 20748)
NOVA = '/Users/macmini/marveen'
rc, out, err = hook({'tool_name': 'mcp__plugin_telegram_telegram__reply', 'tool_input': {'chat_id': '1', 'text': 'Eszter kivette: Nincs szigorú szabály, és semmit nem kell tökéletesen csinálnod.'}, 'cwd': NOVA})
check('belso Telegram: tiltott fordulat -> atmegy (exit 0), systemMessage-ben jelez', rc == 0 and 'G-nincs-szigoru-szabaly' in out, (rc, out, err))
# --- Nessa Telegramja Eszterhez megy (ugyfel): STOP, mint a tobbi ugyfel-ut (Nova 20786)
rc, out, err = hook({'tool_name': 'mcp__plugin_telegram_telegram__reply', 'tool_input': {'chat_id': '1', 'text': 'Nincs szigorú szabály, és semmit nem kell tökéletesen csinálnod.'}, 'cwd': NESSA})
check('Nessa Telegram (Eszterhez): tiltott fordulat -> MEGALL', rc == 2 and 'G-nincs-szigoru-szabaly' in err, (rc, out, err))
for nev in ('landing', 'hirlevel'):
    rc, out, err = hook({'tool_name': 'mcp__plugin_telegram_telegram__edit_message', 'tool_input': {'chat_id': '1', 'message_id': '2', 'text': NEG[nev]}, 'cwd': NESSA})
    check(f'Nessa Telegram: a jovahagyott rev 734 ({nev}) nem akad', rc == 0, err)

# --- nem figyelt eszkoz / parancs: nem nez bele
rc, out, err = hook({'tool_name': 'Bash', 'tool_input': {'command': 'echo "Ha megszereted" > /tmp/x.txt'}, 'cwd': NESSA})
check('nem figyelt Bash (nem kuld sehova): atmegy', rc == 0, err)
rc, out, err = hook({'tool_name': 'Read', 'tool_input': {'file_path': '/x'}, 'cwd': NESSA})
check('nem figyelt eszkoz (Read): atmegy', rc == 0)

# --- curl, olvashatatlan torzs -> megall (fail-closed)
rc, out, err = hook({'tool_name': 'Bash', 'tool_input': {'command': 'curl -s https://innomailer.hu/api/inno/v1/campaigns --data-binary @nincs-ilyen.json'}, 'cwd': NESSA})
check('curl InnoMailer, olvashatatlan @fajl: MEGALL (fail-closed)', rc == 2 and 'nem olvashato' in err, err)

# --- curl '{...}'; echo -- a `;` nem tapadhat a JSON-hoz (2026-10-15, elo kontroll: a torzs nyersen ment at)
rc, out, err = hook({'tool_name': 'Bash', 'tool_input': {'command': "curl -s https://innomailer.hu/x --data-binary '" + json.dumps(
    {'subject': 'A', 'content': 'Ezen a héten nem kell egyszerre mindent megváltoztatnod.'}, ensure_ascii=False) + "'; echo x"}, 'cwd': NESSA})
check("curl '{json}'; echo: megall, es a JSON-kulcsok nem a mondatban", rc == 2 and '"subject"' not in err, err)

# --- szabalyfajl hiba: ugyfel-uton megall, Telegramon atmegy
rossz = dict(ENV, SZOVEGKAPU_SZABALYOK=os.path.join(TMP, 'nincs.json'))
rc, out, err = hook(UTAK['Claude Docs (batch)']('Szép napot.'), rossz)
check('hianyzo szabalyfajl, ugyfel-ut: MEGALL (fail-closed)', rc == 2 and 'fail-closed' in err, err)
rc, out, err = hook({'tool_name': 'mcp__plugin_telegram_telegram__reply', 'tool_input': {'text': 'Szép napot.'}}, rossz)
check('hianyzo szabalyfajl, Telegram: atmegy, jelez', rc == 0 and 'nem futott' in out, (rc, out, err))
rc, out, err = hook({'tool_name': 'mcp__plugin_telegram_telegram__reply', 'tool_input': {'text': 'Szép napot.'}, 'cwd': NESSA}, rossz)
check('hianyzo szabalyfajl, Nessa Telegram (ugyfel): MEGALL (fail-closed)', rc == 2 and 'fail-closed' in err, (rc, out, err))

# --- szandekos idezes: egyszeri engedely
mondat = 'Ha megszereted, a 21napalatt VIP Klubban együtt haladunk tovább!'
r = subprocess.run([sys.executable, KAPU, 'idezet-engedely', '--mondat', mondat, '--indok', 'jelentes Nessanak, Eszter elutasitotta'], capture_output=True, text=True, env=ENV)
check('idezet-engedely kiadva', r.returncode == 0 and 'egyszeri' in r.stdout, r.stdout + r.stderr)
rc, out, err = hook(UTAK['levelpiszkozat (mcp__email__save_to_mailbox)'](mondat))
check('az engedelyezett mondat EGYSZER atmegy', rc == 0, err)
rc, out, err = hook(UTAK['levelpiszkozat (mcp__email__save_to_mailbox)'](mondat))
check('masodszor mar megall (egyszeri engedely)', rc == 2, err)

# --- szandekos idezes egy egesz fajlra (a szabaly-doksi rossz peldai)
doksi = os.path.join(TMP, 'szabalydoksi.txt')
io.open(doksi, 'w', encoding='utf-8').write('\n'.join(p['mondat'] for p in poz))
r = subprocess.run([sys.executable, KAPU, 'idezet-engedely', '--fajl', doksi, '--ugyfel', '21napalatt', '--indok', 'Szovegszabalyok doksi, rossz peldak'], capture_output=True, text=True, env=ENV)
check('idezet-engedely --fajl: minden megallo mondat engedelyt kap', r.returncode == 0 and 'mondat' in r.stdout, r.stdout + r.stderr)
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': io.open(doksi, encoding='utf-8').read()}, 'cwd': NESSA})
check('...a szabaly-doksi egyszer kimehet', rc == 0, err)
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': io.open(doksi, encoding='utf-8').read()}, 'cwd': NESSA})
check('...masodszor mar megall', rc == 2, err)

# --- pipeline (kapu()) es CLI
sys.path.insert(0, os.path.join(REPO, 'scripts', 'hooks'))
os.environ.update(SZOVEGKAPU_ENGEDELYEK=ENV['SZOVEGKAPU_ENGEDELYEK'], SZOVEGKAPU_NAPLO=ENV['SZOVEGKAPU_NAPLO'])
import importlib
sk = importlib.import_module('szovegkapu')
sk.ENGEDELY_UT, sk.NAPLO_UT = ENV['SZOVEGKAPU_ENGEDELYEK'], ENV['SZOVEGKAPU_NAPLO']
stop_db = sum(1 for p in poz if sk.kapu(p['mondat'], '21napalatt', 'poszt')[0])
check(f'pipeline kapu(): pozitiv {len(poz)}/{len(poz)} stop (21napalatt, poszt)', stop_db == len(poz), stop_db)
for m, txt in NEG.items():
    st, je = sk.kapu(txt, '21napalatt', m)
    check(f'pipeline kapu(): negativ rev 734 ({m}) -> 0 stop', not st, st)
f = os.path.join(TMP, 'poszt.txt'); io.open(f, 'w', encoding='utf-8').write(poz[0]['mondat'])
r = subprocess.run([sys.executable, KAPU, 'ellenoriz', '--fajl', f, '--ugyfel', '21napalatt', '--mufaj', 'poszt'], capture_output=True, text=True, env=ENV)
check('CLI ellenoriz: tiltott -> exit 1, kiirja a szabalyt', r.returncode == 1 and 'STOP' in r.stdout, r.stdout)
io.open(f, 'w', encoding='utf-8').write(neg)
r = subprocess.run([sys.executable, KAPU, 'ellenoriz', '--fajl', f, '--ugyfel', '21napalatt', '--mufaj', 'landing'], capture_output=True, text=True, env=ENV)
check('CLI ellenoriz: rev 734 -> exit 0', r.returncode == 0, r.stdout)

# --- ismert fajl (config/szovegkapu-ugyfelek.json `fajlok`): a posztnaptar irasa 'poszt' mufajjal fut (Copy 20922)
POSZTNAPTAR = '1uJr8SWueMRRB3WaeIRXzjE_YphMvWIO_Nf5fDpVjD-E'
def sheet(t, sid=POSZTNAPTAR, tool='mcp__google-drive__updateGoogleSheet', cwd='/Users/macmini/marveen'):
    return {'tool_name': tool, 'tool_input': {'spreadsheetId': sid, 'range': 'Posztnaptár Facebook!G40', 'data': [[t]]}, 'cwd': cwd}
apro = 'Akár minden napot végigcsináltál, akár csak egy receptet próbáltál ki, minden apró lépés számít.'
# v15.5 (Copy 22073): in a post only the task-intro form flags; the encouraging form is Eszter's own voice
feladat = 'A mai apró lépésed: este egy órával lefekvés előtt tedd le a telefont.'
rc, out, err = hook(sheet(feladat))
check("posztnaptar Sheets-iras: 'mai apró lépésed:' posztban csak JELEZ (E-apro-lepes-poszt), nem STOP", rc == 0 and 'E-apro-lepes-poszt' in out, (rc, out, err))
rc, out, err = hook(sheet(apro))
check("posztnaptar Sheets-iras: batorito 'minden apró lépés számít' posztban atmegy, jelzes nelkul", rc == 0 and 'E-apro-lepes-poszt' not in out, (rc, out, err))
rc, out, err = hook({'tool_name': 'mcp__google-drive__createGoogleDoc', 'tool_input': {'content': 'A 21napalatt kihívásban ' + apro}, 'cwd': NESSA})
check("ugyanez ismeretlen mufaju Docs-iraskor: a landing-szabaly (E-apro-lepes) STOP-ol -- a cimke a kulonbseg", rc == 2 and 'E-apro-lepes' in err, err)
rc, out, err = hook(sheet('A receptet megtalálod a Klub recepttárában.'))
check('posztnaptar Sheets-iras: csupasz "Klub" -> STOP (a fajl ugyfele 21napalatt, jel nelkul is)', rc == 2 and 'E-vip-klub' in err, err)
rc, out, err = hook(sheet('A receptet megtalálod a Klub recepttárában.', tool='mcp__google-drive__appendSpreadsheetRows'))
check('posztnaptar appendSpreadsheetRows: ugyanaz a kapu', rc == 2 and 'E-vip-klub' in err, err)
rc, out, err = hook(sheet('Budapest - Szeged, a Klub tagjai', sid='masik-tablazat-id'))
check('MAS tablazat Sheets-irasa: kivul marad (exit 0, nincs uzenet)', rc == 0 and not out.strip() and not err.strip(), (rc, out, err))
rc, out, err = hook(sheet('Ez nem egy méregtelenítő- vagy fogyókúra.'))
check('posztnaptar: a landing-mufaju E-meregtelenito posztban is fut (minden mufaj listajaban benne van a poszt)', rc == 2 and 'E-meregtelenito' in err, err)

# --- csere-ut (Copy 20941): a findAndReplaceInDoc KERESETT (torlendo) szovege nem kimeno, a replaceText igen
cs = lambda find, repl: {'tool_name': 'mcp__google-drive__findAndReplaceInDoc', 'tool_input': {'documentId': 'doc1', 'findText': find, 'replaceText': repl, 'matchCase': True}, 'cwd': NESSA}
rc, out, err = hook(cs('ha soha nem leszel klubtag', 'ha soha nem lépsz be a VIP Klubba'))
check('csere: a tiltott alakot KIVEVO csere atmegy (findText nem kimeno)', rc == 0, (rc, out, err))
rc, out, err = hook(cs('ha soha nem lépsz be a VIP Klubba', 'ha soha nem leszel klubtag'))
check('csere: a tiltott alakot BEHOZO csere megall (replaceText vizsgalt)', rc == 2 and 'E-vip-klub' in err, err)

print(f'\n{ok} sikeres, {bad} bukott')
sys.exit(1 if bad else 0)
