#!/bin/bash
# CAPI fbc-jelzes figyelo. READ-ONLY a prodon.
#
# MIERT LETEZIK (2026-09-15, Pixel keresere): a jelzes 17:06-kor elesedett, de VALODI vasarlason
# meg nem futott le. A lanc utolso szeme -- eles vasarlas -> sor a naplofajlban, helyes alakkal --
# igazolatlan. Ha ott romlik el, HETEKNYI adat vesz el ugy, hogy minden zoldnek latszik: a
# "nincs sor" ugyanugy nez ki, mint a "nem volt vasarlas".
#
# ES A MASODIK OK, ami tartosan fontosabb: a naplo a PRODON van, Pixelnek oda NINCS utja.
# Ha a kigyujtes azon mulik, hogy eszembe jut-e, akkor egy kimarado het nem hianynak latszik,
# hanem "nem volt lelet"-nek. Ezert szkript, nem szokas.
#
# KIMENET: ha van UJ sor a legutobbi futas ota, kiirja oket. Ha nincs, NEMA (exit 0).
# A "nulla allapot" kontrollja (Pixel): a naplosorok szama egyezzen a tranzakciok szamaval.
set -u
cd /Users/macmini/marveen || exit 1
STATE=store/capi-fbc-figyelo-state.txt
KEY=$(mktemp /tmp/nova_fbcfig.XXXXXX)
cleanup() { B=$(wc -c < "$KEY" 2>/dev/null || echo 0); dd if=/dev/zero of="$KEY" bs=1 count="$B" conv=notrunc 2>/dev/null; rm -f "$KEY"; }
trap cleanup EXIT
node -e "
import('/Users/macmini/marveen/dist/web/vault.js').then(({getSecret}) => {
  const fs=require('fs'); const k=getSecret('ssh-key-dc8b036ee89b5473');
  fs.writeFileSync('$KEY', k.endsWith('\n')?k:k+'\n',{mode:0o600});
});
" 2>/dev/null
chmod 600 "$KEY"

# A prodrol: az utolso 3 nap CAPI-sorai + a tranzakcio-szam ugyanarra a napra.
OUT=$(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=25 \
  napalatt@185.208.227.93 'L=~/vip.21napalatt.hu/wp-content/plugins/salesform_helper/logs
for i in 2 1 0; do
  D=$(date -d "-$i day" +%d-%b-%Y 2>/dev/null || date -v-${i}d +%d-%b-%Y)
  if [ -f "$L/capi_$D.log" ] && grep -qaE "fbc-megvan|FBC-HIANYZIK|FBC-ROSSZ" "$L/capi_$D.log"; then
    grep -aE "fbc-megvan|FBC-HIANYZIK|FBC-ROSSZ" "$L/capi_$D.log" | sed "s|^|SOR |"
    # PIXEL KERESE (2026-09-15): a nyers CAPI-sor melle a TRANZAKCIO-oldali adat is menjen at.
    # Az alak-ellenorzes egy ELGEPELT user_id-t NEM fogna meg -- csak az mondja meg, hogy a sor
    # a JO vasarlashoz tartozik-e. Ezert az adott nap connector-sorait is atadjuk, ido+user+tipus.
    [ -f "$L/log_$D.log" ] && grep -aE "created and LearnDash group|already registered to wrodpress|\[DUP\]" "$L/log_$D.log" \
      | sed -E "s/\(([A-Za-z0-9._%+-]+)@/(***@/; s/(prev_|new_)?(trid|token)=[a-f0-9]+/\\1\\2=<...>/g" | sed "s|^|TRANZ |"
  fi
  # A NULLA-ALLAPOT KONTROLLJA: hany tranzakcio volt aznap, es hany CAPI-sor keletkezett.
  if [ -f "$L/log_$D.log" ]; then
    TR=$(( $(grep -ac "created and LearnDash group" "$L/log_$D.log") + $(grep -ac "already registered to wrodpress" "$L/log_$D.log") ))
    CS=$(grep -acE "fbc-megvan|FBC-HIANYZIK|FBC-ROSSZ" "$L/capi_$D.log" 2>/dev/null || echo 0)
    echo "KONTROLL $D tranzakcio=$TR capi_fbc_sor=$CS"
  fi
done' 2>/dev/null)

[ -z "$OUT" ] && exit 0
UJ=$(echo "$OUT" | grep '^SOR ' | grep -vxFf "$STATE" 2>/dev/null || echo "$OUT" | grep '^SOR ')
if [ -n "$UJ" ]; then
  echo "=== UJ CAPI fbc-SOROK ==="
  echo "$UJ"
  echo
  echo "$OUT" | grep '^TRANZ '
  echo
  echo "$OUT" | grep '^KONTROLL '
  echo "$OUT" | grep '^SOR ' >> "$STATE"
  sort -u "$STATE" -o "$STATE"
fi
exit 0
