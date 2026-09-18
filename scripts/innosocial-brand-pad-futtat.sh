#!/bin/bash
# A 12-fiokos brand-autofill merőpad EGY futasa a prodon, ket fazisban.
# 1. fazis: InnoWorx (token ujratitkositas) -> /tmp/nova_export_bemenet.json
# 2. fazis: InnoSocial (szallitott fuggvenyek + modellhivas) -> /tmp/nova_export_kimenet/
# A kimenet visszajon ide: agents/bit/workspace/innosocial/atadott/pad-<datum>/
set -uo pipefail
cd /Users/macmini/marveen || exit 1
TS=$(date +%Y-%m-%d-%H%M)
OUTDIR="agents/bit/workspace/innosocial/atadott/pad-$TS"
LOG="scratchpad/pad-$TS.log"
mkdir -p "$OUTDIR"

KEY=$(mktemp /tmp/nova_pad_key.XXXXXX)
cleanup() { B=$(wc -c < "$KEY" 2>/dev/null || echo 0); dd if=/dev/zero of="$KEY" bs=1 count="$B" conv=notrunc 2>/dev/null; rm -f "$KEY"; }
trap cleanup EXIT
node -e "
import('/Users/macmini/marveen/dist/web/vault.js').then(({getSecret}) => {
  const fs = require('fs');
  const k = getSecret('ssh-key-dc8b036ee89b5473');
  fs.writeFileSync('$KEY', k.endsWith('\n') ? k : k + '\n', { mode: 0o600 });
});
" 2>/dev/null
chmod 600 "$KEY"
SSHOPT="-i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
HOST="napalatt@185.208.227.93"

{
  echo "=== PAD $TS ==="
  echo "--- szallitott kod a szerveren (HEAD) ---"
  ssh $SSHOPT "$HOST" "cd /home/napalatt/app.innosocial.hu/api && git log -1 --format='%h %ci %s' 2>/dev/null"
  echo "--- fajlok feltoltese ---"
  scp $SSHOPT scripts/innosocial-brand-pad-export1.php "$HOST:/tmp/nova_export1.php" >/dev/null && echo "export1 fent"
  scp $SSHOPT scripts/innosocial-brand-pad-export2.php "$HOST:/tmp/nova_export2.php" >/dev/null && echo "export2 fent"
  echo "--- regi kimenet torlese (nehogy osszekeveredjen) ---"
  ssh $SSHOPT "$HOST" "rm -rf /tmp/nova_export_kimenet /tmp/nova_export_bemenet.json && echo torolve"
  echo "--- 1. FAZIS (InnoWorx) ---"
  ssh $SSHOPT "$HOST" "php /tmp/nova_export1.php" 2>&1
  echo "--- 2. FAZIS (InnoSocial, modellhivassal) ---"
  ssh $SSHOPT "$HOST" "php /tmp/nova_export2.php" 2>&1
  echo "--- kimenet visszahozasa ---"
  scp $SSHOPT "$HOST:/tmp/nova_export_kimenet/*.json" "$OUTDIR/" 2>&1 | tail -2
  ls -1 "$OUTDIR" | wc -l | xargs echo "visszahozott fajl:"
  echo "=== VEGE $(date '+%H:%M:%S') ==="
} 2>&1 | tee "$LOG"
echo "LOG: $LOG"
echo "OUT: $OUTDIR"
