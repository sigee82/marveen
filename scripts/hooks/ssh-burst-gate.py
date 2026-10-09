#!/usr/bin/env python3
"""
PreToolUse gate: do not open a burst of SSH connections to the shared cPanel host.

Why: the host behind 21napalatt / InnoWorx / InnoSocial (185.208.227.93, user napalatt)
runs an IP firewall. Twice it banned the whole fleet's IP after a burst of SSH
connections from this machine:
  - 2026-09-24: ~8 connections in 25 minutes -> graylist, SSH timeout, HTTP splash.
  - 2026-09-26 16:0x: one file per `ssh ... 'cat > f' < f` in a loop (~16 connections
    in a few minutes, ~10 more earlier that day) -> hard ban: port 22 timeout, every
    domain on the host 403 "Unauthorized Access", for over an hour. It took down the
    InnoPlan bridge, the AI quota watcher and Lumen's image generator with it, because
    the whole fleet shares one IP.
The rule "one task = one connection" was already written in the landing-deploy-cpanel-ssh
skill after the first ban and was broken anyway. So this is a gate, not another note.

What it blocks (Bash commands that reach the host by ssh/scp/sftp/rsync):
  1. an ssh/scp call inside a shell loop (for/while) -- the number of connections is
     unknowable up front, and this is exactly the shape of the 09-26 ban;
  2. a command that would push the rolling count over LIMIT connections in WINDOW seconds.
What it does NOT cover: connections made by a script the command runs (e.g. a python
script that shells out to ssh), and other hosts. Deliberately narrow.

The allowed way: tar the files locally (plus MD5SUMS) and send them in ONE call:
  ssh <target> 'set -e; D=<dir>; mkdir -p $D; tar -xzf - -C $D; cd $D; md5sum -c --quiet MD5SUMS; <run>' < pkg.tgz

Contract: PreToolUse. Payload on stdin; exit 0 = allow, exit 2 = block (message on stderr).
Any internal error -> exit 0 (a broken gate must not stop the session).
State: a small timestamp log in the scratch dir below; losing it only makes the gate
forget recent connections.
"""
import json
import os
import re
import sys
import time

LIMIT = 6            # connections allowed per window
WINDOW = 15 * 60     # seconds
STATE = os.path.join(os.environ.get("TMPDIR", "/tmp"), "nova-ssh-burst-gate.log")

TARGET = re.compile(r"\b(ssh|scp|sftp|rsync)\b[^\n;|&]*?(185\.208\.227\.93|napalatt@)")
HOST = re.compile(r"185\.208\.227\.93|napalatt@")
SSHCALL = re.compile(r"\b(ssh|scp|sftp|rsync)\b")
LOOP = re.compile(r"\b(for|while|until)\b[\s\S]*?\bdo\b[\s\S]*?\b(ssh|scp|sftp|rsync)\b[\s\S]*?\bdone\b")

HOWTO = (
    "A helyes ut: csomagold egybe (tar czf + MD5SUMS), es EGY hivassal vidd fel es futtasd:\n"
    "  ssh <cel> 'set -e; D=<mappa>; mkdir -p $D; tar -xzf - -C $D; cd $D; "
    "md5sum -c --quiet MD5SUMS; <futtatas>' < csomag.tgz\n"
    "Ha tobb parancs kell egymas utan: -o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h "
    "-o ControlPersist=120 (egy kapcsolat, tobb parancs).\n"
    "Kapcsolodo skill: landing-deploy-cpanel-ssh (0/b pont)."
)


def recent(now):
    try:
        with open(STATE) as f:
            return [float(x) for x in f.read().split() if now - float(x) < WINDOW]
    except Exception:
        return []


def record(now, n, past):
    try:
        with open(STATE, "w") as f:
            f.write("\n".join(str(t) for t in past + [now] * n))
    except Exception:
        pass


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    # The host may sit in a variable (H=napalatt@...; ssh ... $H ...) -- the real 09-26
    # loop looked exactly like that, so presence anywhere + an ssh-family call counts.
    if not (HOST.search(cmd) and SSHCALL.search(cmd)):
        return 0
    hits = max(1, len(TARGET.findall(cmd)))

    if LOOP.search(cmd):
        sys.stderr.write(
            "KAPU (ssh-burst): ssh/scp hivas ciklusban a 185.208.227.93 hosztra. Ez pontosan az az alak, "
            "amitol a hoszt tuzfala 2026-09-26-an kitiltotta a flotta IP-jet (fajlonkent egy kapcsolat).\n"
            + HOWTO + "\n"
        )
        return 2

    now = time.time()
    past = recent(now)
    if len(past) + hits > LIMIT:
        sys.stderr.write(
            "KAPU (ssh-burst): az utobbi {w} percben mar {p} kapcsolat ment a 185.208.227.93 hosztra, "
            "ez a parancs +{h}-t nyitna (hatar: {l}). A tuzfal ennel kevesebbtol is tiltott mar (09-24: ~8/25 perc).\n"
            "Kerdes, mielott ujra probalod: osszevonhato-e egyetlen hivasba, amit most csinalsz?\n".format(
                w=WINDOW // 60, p=len(past), h=hits, l=LIMIT)
            + HOWTO + "\n"
        )
        return 2

    record(now, hits, past)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
