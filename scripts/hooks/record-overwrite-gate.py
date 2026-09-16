#!/usr/bin/env python3
"""PreToolUse gate: stop the "does this endpoint exist?" probe from landing on a LIVE record.

Why this exists. Five times between 2026-08-06 and 2026-08-24, four different
fleet agents destroyed a real stored record by answering a CAPABILITY question
with a WRITE: `PUT /api/memories/<id>` carrying a throwaway body ("x", "probe").
The endpoint exists, so the answer arrives as HTTP 200 -- and the 200 IS the
damage, because `content` is unconditionally overwritten.

The fifth case (2026-08-24) is the reason this file exists rather than another
note: it was committed by the agent who had already written the warning, already
documented the endpoint contract, and already taken the kanban card (ab986d26)
for building this gate. Knowledge, diagnosis and owner were all in place. The
missing piece was only ever the mechanical stop -- because "does PUT exist?"
FEELS like a read while being a write, and a warning does not stand in the way
at the moment the reflex fires.

The signal is narrow and concrete, which is why this gate is cheap: a probe body
is always a short literal. A real correction is never three characters. So:

    PUT /api/<store>/<id>  with a recoverable body whose `content` is short  -> BLOCK
    PUT /api/<store>/<id>  with no data payload at all                        -> BLOCK
    everything else                                                           -> ALLOW

Deliberately NOT fail-closed on an unreadable body. The legitimate repair path
(read the row, merge, PUT the full text back) is normally built with python or a
heredoc, which this hook cannot resolve -- blocking that would train the operator
to route around the gate, which is worse than the gate not firing. Every one of
the five incidents used a short inline literal, so precision beats coverage here.

Contract: PreToolUse. Hook payload on stdin, exit 0 = allow, exit 2 = block
(stderr is returned to the model).
"""
import json
import os
import re
import sys

# Stores whose PUT overwrites content unconditionally. Keep this list explicit:
# a gate that guesses which endpoints are destructive would fire on read paths.
STORES = ("memories", "kanban", "schedules", "agents")

# A real correction is longer than this. The five recorded probes were 1-5 chars.
MIN_CONTENT = 80

METHOD_RE = re.compile(r"(?:-X|--request)\s+(?:'|\")?(PUT|PATCH)(?:'|\")?", re.I)
POST_RE = re.compile(r"(?:-X|--request)\s+(?:'|\")?POST(?:'|\")?", re.I)
# The COLLECTION endpoint (no /<id> after it) -- creation, not update.
KANBAN_CREATE_RE = re.compile(r"/api/kanban(?![A-Za-z0-9_/-])")
URL_RE = re.compile(
    r"/api/(" + "|".join(STORES) + r")/([A-Za-z0-9_-]+)"
)
# Only inline literal payloads are recoverable here; $VAR / $(...) / heredocs are not.
DATA_RE = re.compile(r"(?:-d|--data(?:-raw|-binary)?)\s+'([^']*)'|(?:-d|--data(?:-raw|-binary)?)\s+\"([^\"]*)\"")
# `curl --data-binary @/path/body.json` -- the body IS there, it is just not on the
# command line. Measured 2026-09-08: without this the gate read a legitimate,
# file-carried PUT as "ADAT NELKUL" and blocked it, twice in a row, while telling
# the caller the exact opposite of what was true. That is the worse failure of the
# two the gate can have: "you sent nothing" is a claim, not a shrug, and it sends
# the caller looking for a missing payload that was never missing.
FILE_DATA_RE = re.compile(r"(?:-d|--data(?:-raw|-binary)?)\s+@([^\s'\"]+)")
MAX_BODY_BYTES = 1_000_000


def payload_of(cmd):
    """Return (found, text) for a -d payload. found=False means unrecoverable.

    THREE outcomes, not two, and the third is why this function exists: a body
    can be absent, inspectable, or PRESENT BUT OUT OF REACH. Collapsing the third
    into the first makes the gate lie.
    """
    m = DATA_RE.search(cmd)
    if m:
        raw = m.group(1) if m.group(1) is not None else m.group(2)
        if "$" in raw or "`" in raw:      # shell would expand it; we are not reading the real bytes
            return False, ""
        return True, raw
    f = FILE_DATA_RE.search(cmd)
    if f:
        path = f.group(1)
        if "$" in path or "`" in path:
            return False, ""
        try:
            if os.path.getsize(path) > MAX_BODY_BYTES:
                return False, ""
            with open(path, encoding="utf-8") as fh:
                return True, fh.read()
        except Exception:
            # The file is named but unreadable. NOT the same as no data: say so in
            # the caller's own terms rather than asserting an empty body.
            return False, ""
    return False, ""


def kanban_create_block(cmd):
    """POST /api/kanban carrying `agent_id`: the card is created with a NULL owner.

    kanban_cards has no `agent_id` column (it is `assignee`), and the endpoint
    neither rejects nor warns -- it answers {"ok":true} and drops the field. The
    damage surfaces hours later in the four-hourly audit, where the card counts
    as undelegated; if it is also under active watch it looks simultaneously
    ownerless and stuck, while neither is true.

    Documented since 2026-08-17 and walked into four more times since (9764b33b,
    cf7a6f1d, f8fc090a on 08-24; 2dc55bf0 on 09-02). `scripts/kanban-uj.sh`
    already exists to prevent exactly this, and reads the row back. Its problem
    is that using it requires remembering it, and card creation always happens
    in the middle of some other task -- which is when the read-back step drops
    out. So the note is not the missing piece; the stop is.

    Narrow on purpose, same reasoning as the PUT branch above: only an inline
    literal body is inspected. Every recorded case used one.
    """
    if not POST_RE.search(cmd) or not KANBAN_CREATE_RE.search(cmd):
        return False
    found, raw = payload_of(cmd)
    if not found:
        return False
    try:
        body = json.loads(raw)
    except Exception:
        return False
    if not isinstance(body, dict) or "agent_id" not in body:
        return False
    sys.stderr.write(
        "KAPU: POST /api/kanban `agent_id` mezovel. A kanban_cards tablaban NINCS ilyen oszlop "
        "(a helyes nev `assignee`), a vegpont megis {\"ok\":true}-t ad, es a kartya GAZDATLANUL "
        "jon letre. Se hibauzenet, se figyelmeztetes.\n"
        "2026-08-17 ota dokumentalt, es azota megis negyszer megtortent (9764b33b, cf7a6f1d, "
        "f8fc090a, 2dc55bf0) -- mindannyiszor egy masik feladat kozben, amikor a visszaolvasas "
        "lepese kiesik.\n"
        "\n"
        "HASZNALD EHELYETT (a helyes mezonevvel postol, visszaolvassa a sort, es nem-nulla "
        "kilepesi koddal all meg, ha az assignee ures maradt):\n"
        "  scripts/kanban-uj.sh \"<cim>\" \"<leiras>\" <status> <assignee> [prioritas]\n"
        "Ha tenyleg kezzel akarsz postolni, ird at a mezot `assignee`-re -- akkor ez a kapu "
        "nem all utadba.\n"
    )
    return True


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0                          # unparseable hook input must not block the session

    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if "/api/" not in cmd:
        return 0

    if kanban_create_block(cmd):
        return 2

    meth = METHOD_RE.search(cmd)
    url = URL_RE.search(cmd)
    if not meth or not url:
        return 0

    store, rec_id = url.group(1), url.group(2)
    found, raw = payload_of(cmd)

    if not found and not DATA_RE.search(cmd) and not FILE_DATA_RE.search(cmd):
        sys.stderr.write(
            "KAPU: {m} /api/{s}/{i} ADAT NELKUL. Ez a hivas nem javit, csak megserti a "
            "rekordot (a content mindig felulirodik). Ha a vegpont letezeset akarod "
            "kideriteni, csinald eldobhato rekordon.\n".format(m=meth.group(1).upper(), s=store, i=rec_id)
        )
        return 2

    if not found:
        return 0                          # body built by shell/python -- see module docstring

    try:
        body = json.loads(raw)
    except Exception:
        return 0

    content = body.get("content")
    if not isinstance(content, str) or len(content.strip()) >= MIN_CONTENT:
        return 0

    sys.stderr.write(
        "KAPU: {m} /api/{s}/{i} egy {n} karakteres content-tel. Ez proba-alaku iras egy ELO "
        "rekordra, es a 200-as valasz MAR a kar -- a content feltetel nelkul felulirodik.\n"
        "Ot ilyen eset volt 2026-08-06 es 08-24 kozott, negy agensnel, ugyanezzel az alakkal.\n"
        "\n"
        "Ha a KERDES az, hogy letezik-e a vegpont: a valasz mar le van irva "
        "(~/.claude/projects/-Users-macmini-marveen/memory/ne-probald-a-vegpontot-eles-irassal.md), "
        "vagy derits ki eldobhato rekordon, vagy `grep -rn \"api/{s}\" dist/ src/`.\n"
        "Ha a SZANDEK valodi javitas: olvasd ki a TELJES sort, fuzd ossze a javitassal, es a "
        "teljes szoveggel PUT-olj -- akkor ez a kapu nem fog megallitani.\n".format(
            m=meth.group(1).upper(), s=store, i=rec_id, n=len(content.strip())
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
