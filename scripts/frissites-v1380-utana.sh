#!/bin/bash
# Post-restart verification for the v1.38.0 upgrade -- the deterministic half.
#
# WHY A SCRIPT: the same reason frissites-verify.sh exists. If the before and after
# checks are typed twice by hand, the difference in how they were typed manufactures
# a diff of its own. One script means the only thing that can differ is the answer.
#
# The embedding probe is deliberately NOT in here: its positive control is
# asynchronous (the vector lands a few seconds after the POST, fire-and-forget), so
# it has to be a WAIT, not a single read. Measured 2026-09-16: read immediately
# after the POST it is still NULL, and running the edit at that point would make the
# "IS NULL" afterwards prove nothing. That step is run interactively, in order.
#
# The two helpers it calls live in scripts/, NOT in a scratchpad. They started in
# /tmp, which would have made this whole verification depend on one machine's temp
# directory -- the exact shape we spent today removing (an untracked
# frissites-verify.sh, an orphan dist module, a fix living only on an unmerged
# branch). A measuring tool has to be at least as durable as what it measures.
#
#   bash scripts/frissites-v1380-utana.sh
set -uo pipefail
ROOT=/Users/macmini/marveen
cd "$ROOT" || exit 1
TOK=$(cat store/.dashboard-token)
FAIL=0

say() { printf '%-52s %s\n' "$1" "$2"; }
check() { # label expected actual
  if [ "$2" = "$3" ]; then say "$1" "OK ($3)"; else say "$1" ">>> ELTER: vart=$2 kapott=$3"; FAIL=1; fi
}

echo "=== 1) MELYIK KOD FUT ==="
PID=$(pgrep -f "node .*$ROOT/dist/index.js" | head -1)
say "dashboard pid" "${PID:-NINCS}"
[ -n "$PID" ] && say "indulas" "$(ps -o lstart= -p "$PID")"
[ -n "$PID" ] || FAIL=1

echo
echo "=== 2) A DIFFERENCIALO HORGONY (a BETOLTOTT kod allitja elo, nem mi) ==="
# Baseline measured before the restart: this trigger did NOT exist, while the other
# kanban triggers did -- so the counter was not running on an empty set.
T=$(sqlite3 store/claudeclaw.db "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='kanban_cards_fields_bump_updated_at';")
check "kanban_cards_fields_bump_updated_at letezik" "1" "$T"
ALL=$(sqlite3 store/claudeclaw.db "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name LIKE 'kanban%';")
say "osszes kanban-trigger (elotte 7 volt)" "$ALL"

echo
echo "=== 3) SZOLGALTATAS ==="
check "GET /api/agents tokennel" "200" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -H "Authorization: Bearer $TOK" http://localhost:3420/api/agents)"
check "GET /api/agents token NELKUL" "401" "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 http://localhost:3420/api/agents)"

echo
echo "=== 4) VERZIO ES EREDET ==="
check "package.json verzio" "1.38.0" "$(node -e 'console.log(require("./package.json").version)')"
check "dist/.built-commit == HEAD" "0" "$(node scripts/built-commit-check.mjs >/dev/null 2>&1; echo $?)"
say "HEAD" "$(git rev-parse --short HEAD) $(git log -1 --format=%s | cut -c1-48)"

echo
echo "=== 5) KAPU-KONTROLL (ugyanaz a fixture-keszlet, mint az FF elott/utan) ==="
bash "$ROOT/scripts/frissites-kapu-fixture.sh"

echo
echo "=== 6) HOOK-BEKOTES: egy szkript sem tuzel ketszer ==="
python3 "$ROOT/scripts/hook-bekotes-duplikatum.py" | head -4

echo
if [ "$FAIL" -ne 0 ]; then
  echo "############ VAN ELTERES -- NE OLVASD ZOLDNEK ############"
  exit 1
fi
echo "A determinisztikus fele rendben. HATRA: a ketagu embedding-proba a futo peldanyon."
exit 0
