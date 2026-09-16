"""After the cleanup: does every hook script fire EXACTLY ONCE per event?

Counts across BOTH registration surfaces at once -- the user-global and the repo
settings.json -- because the whole point of this round is that the two add up.

COUNTS (event, script, MATCHER) TRIPLES, not (event, script) pairs. The first
version counted pairs and reported two "duplicates" that were nothing of the sort:
email-approval-gate.py x3 and outgoing-copy-gate.py x4 are one entry per tool
matcher (Bash, send_email, manage_email, telegram reply/edit), and a given tool
call matches at most one of them. A checker that cries wolf on correct wiring
teaches exactly one reflex -- override it -- so the detector has to know the
difference between the same hook wired to several tools and the same hook wired
twice to the same tool.
"""
import json
import os
import re
import collections

USER = os.path.expanduser('~/.claude/settings.json')
REPO = "/Users/macmini/marveen/.claude/settings.json"


def script(cmd):
    m = re.findall(r'(?:hooks|scripts)/([A-Za-z0-9._-]+\.(?:py|mjs|sh|js))', cmd or '')
    return m[-1] if m else ''


count = collections.Counter()
where = collections.defaultdict(list)
pairs = set()
for label, path in (('user', USER), ('repo', REPO)):
    d = json.load(open(path))
    for ev, arr in (d.get('hooks') or {}).items():
        for e in arr:
            for h in e.get('hooks', []):
                n = script(h.get('command', ''))
                if n:
                    key = (ev, n, str(e.get('matcher')))
                    count[key] += 1
                    where[key].append(label)
                    pairs.add((ev, n))

dupes = {k: v for k, v in count.items() if v > 1}
print(f'osszes (esemeny, szkript, matcher) harmas: {len(count)}   -- ebbol {len(pairs)} kulonbozo (esemeny, szkript)')
print(f'UGYANARRA A MATCHERRE ketszer bekotve: {len(dupes)}')
for (ev, n, m), v in sorted(dupes.items()):
    print(f'    !! [{ev}] {n} matcher={m} x{v} ({", ".join(where[(ev, n, m)])})')
if not dupes:
    print('    -- egy sem: nincs olyan hook, ami ugyanarra a tool-hivasra ketszer futna')

print()
print('ellenorzes, hogy a szamlalo nem ures halmazon futott:')
for ev in sorted({e for e, _, _ in count}):
    names = sorted({n for e, n, _ in count if e == ev})
    print(f'  {ev} ({len(names)}): {names}')
