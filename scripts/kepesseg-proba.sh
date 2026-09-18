#!/bin/bash
# KEPESSEG-PROBA -- feladat ELVALLALASAKOR futtatandó, a tervezes ELOTT.
#
# MIERT SZKRIPT ES NEM SZABALY. 2026-09-18-an harom kulon feladatot vallaltam el ugy, hogy nem
# mertem meg, meg tudom-e tenni: a landing prod-probat (ssh tiltva), a fixture-padot (a vegpont
# nem hivhato + a teszt-konteneribol nincs DB), es a valodi-adatos padot (a fiokok a prodon
# vannak + nincs modell-kulcs). Mindharomnal a falba MUNKA KOZBEN futottam bele, es a kivulrol
# nezo (Nova) siettetett, mert a "nem tudom megtenni" es a "meg nem kezdtem el" kivulrol azonos.
#
# Delelott felirtam magamnak SZABALYKENT. Delutan megegyszer belefutottam. Ugyanaz az alak, mint
# a naplo-idobelyegeknel: nem a figyelem hianyzott, hanem a LEPES. Ezert lett szkript.
#
# HASZNALAT (a sajat munkakonyvtaradbol):
#   scripts/kepesseg-proba.sh ssh
#   scripts/kepesseg-proba.sh ssh kulcs docker
#   scripts/kepesseg-proba.sh push:https://github.com/sigee82/InnoSocial.git
#   scripts/kepesseg-proba.sh db:innosocial-api:innosocial_meta_accounts
#
# Minden proba MERT bizonyitekot ir ki, nem velemenyt. A kimenet ket oszlop: VAN / NINCS + a
# meres, amibol kijott. Ha NINCS, az az ELSO valaszodba valo, ne harom kor mulva.
set -u
AGENS="${AGENS:-bit}"
CFG="/Users/macmini/marveen/agents/$AGENS/.claude/settings.json"
HIBA=0

sor() { printf "  %-8s %-46s %s\n" "$1" "$2" "$3"; }

proba_ssh() {
    if [ ! -f "$CFG" ]; then sor "?" "ssh" "nincs meg a profil: $CFG"; return; fi
    if grep -q '"Bash(ssh:\*)"' "$CFG"; then
        sor "NINCS" "ssh (tavoli futtatas)" "deny-lista: $CFG"
        HIBA=1
    else
        sor "VAN" "ssh (tavoli futtatas)" "nincs a deny-listan"
    fi
}

proba_kulcs() {
    local env_talalat=0
    for v in OPENAI_API_KEY ANTHROPIC_API_KEY GOOGLE_API_KEY; do
        [ -n "${!v:-}" ] && env_talalat=1
    done
    local db_sorok
    db_sorok=$(docker exec innosocial-api php -r '
        require "/var/www/html/api/config.php";
        try { echo (int) getDB()->query("SELECT COUNT(*) FROM innosocial_secrets")->fetchColumn(); }
        catch (Throwable $e) { echo "?"; }' 2>/dev/null)
    # Csak a DARABSZAM megy ki. A kulcsok ERTEKET soha nem olvassuk es nem irjuk ki.
    if [ "$env_talalat" = "1" ] || { [ -n "$db_sorok" ] && [ "$db_sorok" != "0" ] && [ "$db_sorok" != "?" ]; }; then
        sor "VAN" "modell-kulcs" "env=$env_talalat, secrets sorok=$db_sorok"
    else
        sor "NINCS" "modell-kulcs" "env=nincs, secrets sorok=${db_sorok:-?}"
        HIBA=1
    fi
}

proba_docker() {
    if docker ps >/dev/null 2>&1; then
        sor "VAN" "docker" "$(docker ps -q | wc -l | tr -d ' ') futo konteneri"
    else
        sor "NINCS" "docker" "a docker ps nem valaszol"; HIBA=1
    fi
}

proba_push() {   # push:<remote-url vagy remote-nev>
    local cel="${1#push:}"
    local ki
    ki=$(git ls-remote "$cel" 2>&1 | head -1)
    if [ -n "$ki" ] && ! printf '%s' "$ki" | grep -qi "denied\|fatal\|could not"; then
        sor "VAN" "olvasas: $cel" "ls-remote valaszolt"
    else
        sor "NINCS" "olvasas: $cel" "$(printf '%s' "$ki" | cut -c1-40)"; HIBA=1
    fi
    # Az IRAS-jogot nem probaljuk ki iras nelkul -- azt a push maga mondja meg.
    sor "?" "iras: $cel" "csak egy valodi push donti el"
}

proba_db() {     # db:<konteneri>:<tabla>
    local x="${1#db:}"
    local kont="${x%%:*}"
    local tabla="${x##*:}"
    local n
    n=$(docker exec "$kont" php -r "
        require '/var/www/html/api/config.php';
        try { echo (int) getDB()->query('SELECT COUNT(*) FROM $tabla')->fetchColumn(); }
        catch (Throwable \$e) { echo '?'; }" 2>/dev/null)
    if [ -n "$n" ] && [ "$n" != "?" ]; then
        sor "VAN" "$tabla ($kont)" "$n sor -- ELLENORIZD, hogy ez az ELES adat-e"
    else
        sor "NINCS" "$tabla ($kont)" "a lekerdezes nem ment at"; HIBA=1
    fi
}

echo "KEPESSEG-PROBA ($AGENS) -- $(date '+%Y-%m-%d %H:%M')"
[ $# -eq 0 ] && set -- ssh kulcs docker
for p in "$@"; do
    case "$p" in
        ssh)      proba_ssh ;;
        kulcs)    proba_kulcs ;;
        docker)   proba_docker ;;
        push:*)   proba_push "$p" ;;
        db:*)     proba_db "$p" ;;
        *)        sor "?" "$p" "ismeretlen proba" ;;
    esac
done

if [ "$HIBA" = "1" ]; then
    echo
    echo "  >>> VAN 'NINCS' A LISTAN. Ez az ELSO valaszodba valo, a terv ELE."
    echo "  >>> Es a helyes atadas nem 'nem tudom megcsinalni', hanem: (1) a kesz parancs annak,"
    echo "  >>> aki meg tudja, es (2) a munka atszabasa ugy, hogy a hozzaferes a masik oldalon maradjon."
fi
exit 0
