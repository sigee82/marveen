#!/bin/bash
# Fixture set for the two wired gates that go live at FF time.
# Same fixtures before and after, so the only thing that can differ is behaviour.
cd /Users/macmini/marveen || exit 1

dec() {
  python3 -c '
import sys, json
s = sys.stdin.read().strip()
if not s:
    print("allow"); raise SystemExit
try:
    print(json.loads(s).get("hookSpecificOutput", {}).get("permissionDecision", "allow"))
except Exception:
    print("allow")
'
}

echo "--- egress-gate.mjs (fo agens: TILTANIA kell az ismeretlent)"
for U in https://valami-random-domain-9x.example https://evil-example-zz.test; do
  D=$(printf '{"tool_name":"WebFetch","tool_input":{"url":"%s"},"agent_type":""}' "$U" | node scripts/hooks/egress-gate.mjs 2>/dev/null | dec)
  printf "  fo agens  %-45s -> %s\n" "$U" "$D"
done
echo "--- egress-gate.mjs (karanten-olvaso: ENGEDNIE kell)"
D=$(printf '{"tool_name":"WebFetch","tool_input":{"url":"https://valami-random-domain-9x.example"},"agent_type":"quarantine-reader"}' | node scripts/hooks/egress-gate.mjs 2>/dev/null | dec)
printf "  karanten  %-45s -> %s\n" "(barmely domain)" "$D"

echo "--- outgoing-copy-gate.py"
python3 - <<'PY'
import importlib.util
spec = importlib.util.spec_from_file_location("o", "scripts/hooks/outgoing-copy-gate.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
hit = bool(m.audit("koszonom szepen a valaszt es a segitseget"))
print(f"  ekezethianyos mondat        -> {'TALALAT' if hit else 'atengedte'}")
miss = bool(m.audit("a 429-es kod"))
print(f"  szamtoldalek (429-es)       -> {'TALALAT' if miss else 'atmegy'}")
PY
