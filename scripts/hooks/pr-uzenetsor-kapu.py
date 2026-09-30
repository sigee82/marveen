#!/usr/bin/env python3
"""PreToolUse gate on Bash: no `gh pr create` / `gh pr merge` while a message to this agent waits unread.

WHY IT EXISTS
-------------
An agent's inter-agent messages are delivered into its session only when the session is IDLE. While
it works, a newer instruction -- "stop", "not like that", "not now" -- sits in agent_messages as
`pending`, and nothing in the session shows it. The agent finishes, opens the PR or merges, and the
instruction it never saw is already overtaken.

Measured on Bit, FIVE times in three days, with a memory note against it the whole time
(pr-elott-uzenetsor-ellenorzes): 2026-09-28 twice (a merge after a stop, a PR after "survey only"),
2026-09-29 twice (the queue read in the SAME command as the merge), 2026-09-30 once (InnoWorx #369:
the stop 17241 arrived 08:09Z, the PR went out 08:14Z). Five notes' worth of knowing did not stop the
sixth; a step does. Hence a gate, not a sixth note.

WHAT IT DOES
------------
On a command that opens or merges a PR (`gh pr create`, `gh pr merge`, or a `gh api ... pulls/N/merge`)
it asks agent_messages for rows TO this agent that are still `pending` (not yet shown in the session).
None -> the command runs. Some -> it stops, and says which ids and how to read them.

READING THEM COUNTS, AND THE COMMAND SAYS SO: a pending row stays pending until the session is idle,
even after the agent has read it from the database -- so the gate could never let a busy session
through. The agent therefore states, IN the command, the newest id it has read in full:
    gh pr merge 369 ... # sor-olvasva:17248
Only pending rows ABOVE that id stop it. The number is the agent's own claim; the gate checks the queue
against it, so a message that arrived after the reading still stops the command.

WHAT IT DOES NOT CATCH (said, so it does not look like more)
------------------------------------------------------------
- a merge through the GitHub web UI, or any tool other than `gh` (a raw `curl` to the API);
- a message that was delivered (shown) but not acted on: that is in the session, not in the queue;
- whether the agent really READ what it claims with sor-olvasva: the gate holds the queue, not the eyes.

FAIL-CLOSED: if the queue cannot be read, the PR command is stopped and the message says why -- a gate
that turns green when its source is gone is the silence it exists to catch.

Contract: PreToolUse. The payload comes on stdin; exit 0 = allow, exit 2 = block (stderr goes back).
Usage in settings: python3 pr-uzenetsor-kapu.py --agent bit [--db PATH]
"""

import argparse
import json
import os
import re
import sqlite3
import sys

DEFAULT_DB = "/Users/macmini/marveen/store/claudeclaw.db"
# `gh` in COMMAND position (line start, after ; & | ( or $( ) -- "echo gh pr merge" is text, not a merge
_START = r"(?:^|[;&|(\n]|\$\()\s*"
PR_CMD = re.compile(_START + r"gh\s+pr\s+(?:create|merge)(?=\s|$)|" + _START + r"gh\s+api\b[^\n]*\bpulls/\d+/merge\b")
MARKER = re.compile(r"sor-olvasva:(\d+)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", required=True)
    ap.add_argument("--db", default=os.environ.get("PR_KAPU_DB", DEFAULT_DB))
    args = ap.parse_args()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    cmd = str((payload.get("tool_input") or {}).get("command") or "")
    if not PR_CMD.search(cmd):
        return 0
    marks = [int(m) for m in MARKER.findall(cmd)]
    seen = max(marks) if marks else 0
    try:
        con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True, timeout=5)
        rows = con.execute(
            "SELECT id, from_agent, substr(replace(content, char(10), ' '), 1, 140) FROM agent_messages "
            "WHERE to_agent = ? AND status = 'pending' AND id > ? ORDER BY id",
            (args.agent, seen),
        ).fetchall()
        con.close()
    except Exception as e:
        print(f"pr-uzenetsor-kapu: the message queue could not be read ({args.db}: {e}). A PR or merge "
              f"command is stopped while it cannot be read: a gate that goes green without its source is "
              f"exactly the silence it exists to catch. Fix the path/permissions, or read the queue by hand "
              f"and have the owner decide.", file=sys.stderr)
        return 2
    if not rows:
        return 0
    ids = ", ".join(str(r[0]) for r in rows)
    lines = "\n".join(f"  {r[0]} from {r[1]}: {r[2]}" for r in rows)
    print(
        f"pr-uzenetsor-kapu: {len(rows)} message(s) to {args.agent} are waiting UNREAD in the queue (pending, not "
        f"yet shown in this session), newer than {seen or 'anything you marked'}:\n{lines}\n"
        f"Read each one IN FULL first, e.g.\n"
        f"  sqlite3 {args.db} \"select content from agent_messages where id = {rows[-1][0]}\"\n"
        f"If it still stands, run the command again with `# sor-olvasva:{rows[-1][0]}` at its end. "
        f"(ids: {ids})",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
