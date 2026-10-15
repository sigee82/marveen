#!/usr/bin/env python3
"""Narrow InnoPlan tool for Nessa: create / update / read tasks for ESZTER (user 11), in her own projects only.

SCOPE (Zsolt, 2026-10-10 TG 19146/19148): Nessa may create AND modify tasks for anyone, in any project (she acts when
Eszter asks). Default assignee: Eszter (11). Every call is still logged; no separate daily review (Zsolt: overhead).
WHY (Zsolt, 2026-10-10, TG 19142/19144): in a week Nessa sent Nova 66 messages only to have an InnoPlan task created.
Nova's credential is not handed over (fleet rule: no shared credentials); instead this tool uses it with a fixed scope:
  - assignee is always Eszter (11), project must be one of ALLOWED_PROJECTS,
  - update/read only touch a task that is ALREADY Eszter's AND sits in one of those projects (checked on the host),
  - inputs travel base64-encoded into a fixed PHP template (no free code, no free URL),
  - every call is logged to scripts/state/innoplan-eszter.log (who/what/result).
Same transport as scripts/szamlak/eszter_havi.py: one SSH session, JWT minted on the host, read back with md5.

  innoplan-eszter.py uj --cim "<cim>" --leiras-fajl <agents/nessa/...html> --hatarido YYYY-MM-DD --projekt <id> [--felelos <user id>] [--szekcio <id>]
  innoplan-eszter.py modosit --id <task id> [--cim ..] [--leiras-fajl ..] [--hatarido ..] [--allapot todo|in_progress|done] [--szekcio <id>]
  innoplan-eszter.py olvas --id <task id>
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

def szovegkapu(darabok):
    """The AI-slop text gate (scripts/hooks/szovegkapu.py) on what Eszter reads. The SSH payload is invisible to the
    PreToolUse hook, so the call is here. Any failure stops the write (fail-closed)."""
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'hooks'))
        import szovegkapu as sk
        stop, jelez = sk.pipeline(darabok, '21napalatt', '*', 'innoplan')
    except Exception as e:
        sys.exit(f'HIBA: a szovegkapu nem futott ({type(e).__name__}: {e}); ugyfel fele meno uton megallok')
    if jelez:
        print(jelez)
    if stop:
        sys.exit(stop)


ALLOWED_PROJECTS = {58: '21napalatt (Eszter)', 68: 'RECEPTEK', 53: 'OTTHONI TEENDOK'}
ASSIGNEE = 11
STATUSES = ('todo', 'in_progress', 'done')
NESSA_DIR = '/Users/macmini/marveen/agents/nessa/'
SSH_KEY_ID = 'ssh-key-dc8b036ee89b5473'
HOST = 'napalatt@185.208.227.93'
API_DIR = '/home/napalatt/app.innoworx.hu/api'
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state', 'innoplan-eszter.log')

PHP = r"""<?php
require_once 'config.php'; require_once 'jwt_helper.php';
$db = getDB(); $db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
set_exception_handler(function($e) { echo 'HIBA ', $e->getMessage(), "\n"; exit(1); });
$in = json_decode(base64_decode('__IN__'), true);
$ALLOWED = __ALLOWED__; $ASSIGNEE = __ASSIGNEE__; $OWN = __OWN__;
$jwt = JWT::encode(['sub' => 18, 'email' => 'nova@innogroup.hu', 'role' => 'member']);
function api($method, $url, $body) { global $jwt;
  $ch = curl_init('https://app.innoworx.hu/api/tasks.php' . $url);
  curl_setopt_array($ch, [CURLOPT_CUSTOMREQUEST => $method, CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 30,
    CURLOPT_HTTPHEADER => ['Content-Type: application/json', 'Authorization: Bearer ' . $jwt]]);
  if ($body !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($body));
  $r = curl_exec($ch); return [curl_getinfo($ch, CURLINFO_HTTP_CODE), $r]; }
function row($id) { global $db;
  $r = $db->prepare('SELECT t.id, t.title, t.status, t.due_date, t.assignee_id, md5(t.description) m, tp.project_id p, tp.section_id s FROM tasks t LEFT JOIN task_projects tp ON tp.task_id = t.id WHERE t.id = ?');
  $r->execute([$id]); return $r->fetch(PDO::FETCH_ASSOC); }
function guard($x) { global $ALLOWED, $ASSIGNEE, $OWN;
  if (!$x) { echo "HIBA nincs ilyen task\n"; exit(1); }
  /* Zsolt 2026-10-10 TG 19148: Nessa may modify ANY task (she does it when Eszter asks); no owner check */ }
if ($in['op'] === 'olvas') { $x = row($in['id']); guard($x); echo 'TASK ', json_encode($x, JSON_UNESCAPED_UNICODE), "\n"; exit(0); }
if ($in['op'] === 'uj') {
  $st = $db->prepare('SELECT id FROM tasks WHERE title = ? AND due_date = ? AND assignee_id = ?');
  $st->execute([$in['title'], $in['due_date'], $in['assignee_id']]);
  if ($id = $st->fetchColumn()) { echo "MAR_LETEZIK $id\n"; exit(0); }
  [$code, $res] = api('POST', '', ['title' => $in['title'], 'description' => $in['description'], 'assignee_id' => $in['assignee_id'],
                                   'project_id' => $in['project_id'], 'due_date' => $in['due_date']]);
  $st->execute([$in['title'], $in['due_date'], $in['assignee_id']]); $id = $st->fetchColumn();
  if (!$id) { echo "HIBA nincs task a POST utan, http $code: " . substr($res, 0, 300) . "\n"; exit(1); }
} else {
  $id = $in['id']; guard(row($id));
  $body = array_intersect_key($in, array_flip(['title', 'description', 'due_date', 'status']));
  if ($body) { [$code, $res] = api('PUT', '?id=' . $id, $body);
    if (strpos($res, 'success') === false) { [$code, $res] = api('PUT', '?id=' . $id, $body); } }
}
if (!empty($in['section_id'])) {
  [$c2, $r2] = api('PUT', '?id=' . $id . '&action=set_project_section', ['project_id' => (int)(row($id)['p']), 'section_id' => (int)$in['section_id']]);
  if (strpos($r2, 'success') === false) echo "FIGYELEM szekcio-allitas valasza: " . substr($r2, 0, 200) . "\n"; }
$x = row($id);
$ok = isset($in['description']) ? ($x['m'] === md5($in['description']) ? 'leiras OK' : 'LEIRAS ELTER') : 'leiras valtozatlan';
echo strtoupper($in['op']) . " $id | $ok | " . json_encode($x, JSON_UNESCAPED_UNICODE) . "\n";
"""


def own_ids():
    """Task ids this tool created (from the log) -- the only non-Eszter tasks it may modify."""
    ids = []
    if os.path.exists(LOG):
        for line in open(LOG):
            m = re.search(r'"out": "UJ (\d+)', line)
            if m:
                ids.append(int(m.group(1)))
    return sorted(set(ids)) or [0]


def iso(v):
    datetime.date.fromisoformat(v)
    return v


def run_remote(php):
    with tempfile.TemporaryDirectory() as d:
        key, src = os.path.join(d, 'k'), os.path.join(d, 'x.php')
        open(src, 'w').write(php)
        subprocess.run(['node', '--input-type=module', '-e',
                        "import { getSecret } from '/Users/macmini/marveen/dist/web/vault.js';import { writeFileSync } from 'fs';"
                        f"const k=getSecret('{SSH_KEY_ID}');writeFileSync(process.argv[1],k.endsWith('\\n')?k:k+'\\n',{{mode:0o600}})",
                        key], check=True)
        try:
            with open(src) as f:
                p = subprocess.run(['ssh', '-i', key, '-o', 'IdentitiesOnly=yes', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20',
                                    HOST, f'cd {API_DIR} && php'], stdin=f, capture_output=True, text=True, timeout=120)
        finally:
            open(key, 'w').close()
    out = '\n'.join(l for l in (p.stdout + p.stderr).splitlines() if not re.match(r'^(perl|\s*L[A-Z_]* =)|are supported|locale', l))
    return p.returncode, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('op', choices=['uj', 'modosit', 'olvas'])
    ap.add_argument('--id', type=int)
    ap.add_argument('--cim')
    ap.add_argument('--leiras-fajl')
    ap.add_argument('--hatarido', type=iso)
    ap.add_argument('--projekt', type=int)
    ap.add_argument('--felelos', type=int, default=ASSIGNEE, help='InnoPlan user id (alapertelmezes: Eszter, 11)')
    ap.add_argument('--szekcio', type=int)
    ap.add_argument('--allapot', choices=STATUSES)
    a = ap.parse_args()
    inp = {'op': a.op}
    if a.op == 'uj':
        if not (a.cim and a.leiras_fajl and a.hatarido and a.projekt):
            sys.exit('uj: --cim, --leiras-fajl, --hatarido es --projekt kotelezo')
        inp.update(project_id=a.projekt, assignee_id=a.felelos)
    else:
        if not a.id:
            sys.exit('--id kotelezo')
        inp['id'] = a.id
    if a.cim:
        inp['title'] = a.cim.strip()
    if a.hatarido:
        inp['due_date'] = a.hatarido
    if a.allapot:
        inp['status'] = a.allapot
    if a.szekcio:
        inp['section_id'] = a.szekcio
    if a.leiras_fajl:
        p = os.path.realpath(a.leiras_fajl)
        if not p.startswith(NESSA_DIR):
            sys.exit(f'TILTVA: a leiras-fajl csak {NESSA_DIR} alatt lehet')
        desc = open(p, encoding='utf-8').read()
        if '<p>' not in desc:
            sys.exit('A leiras HTML legyen (TipTap: <p>, <strong>, <ul><li><p>..</p></li></ul>, <a href>) -- skill innoplan-feladat-irasa')
        inp['description'] = desc
    szovegkapu([('cim', inp.get('title') or ''), ('leiras', inp.get('description') or '')])
    php = (PHP.replace('__IN__', base64.b64encode(json.dumps(inp, ensure_ascii=False).encode()).decode())
              .replace('__ALLOWED__', '[' + ','.join(map(str, sorted(ALLOWED_PROJECTS))) + ']')
              .replace('__ASSIGNEE__', str(ASSIGNEE))
              .replace('__OWN__', '[' + ','.join(map(str, own_ids())) + ']'))
    rc, out = run_remote(php)
    print(out)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, 'a') as f:
        f.write(json.dumps({'at': datetime.datetime.now().isoformat(timespec='seconds'), 'op': a.op, 'id': a.id,
                            'cim': a.cim, 'projekt': a.projekt, 'rc': rc, 'out': out[-300:],
                            'leiras_md5': hashlib.md5(inp.get('description', '').encode()).hexdigest() if 'description' in inp else None},
                           ensure_ascii=False) + '\n')
    return 0 if rc == 0 and not out.startswith(('HIBA', 'TILTVA')) else 1


if __name__ == '__main__':
    sys.exit(main())
