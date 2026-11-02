#!/usr/bin/env python3
"""PreToolUse gate for Copy: no ad copy goes out unless this session loaded the ad skills and read the references.

WHY IT EXISTS
-------------
Zsolt rejected two rounds of VIP ad copy on 2026-11-02 as "AI-os fos" (TG 25257/25258). Copy then built a
reference set of real Hungarian ads and Zsolt's own yardsticks into the ad-copy skill (Nova 25412). A
reference that is not read does nothing, and "remember to read it" is a note, not a step. So the step is
a gate (Nova 25414, Zsolt TG 25273).

WHAT COUNTS AS HANDING IN AD COPY
---------------------------------
- Bash: an inter-agent message (a POST or PUT to /api/messages: a new message, or closing one with a
  result) whose text is about an ad. The text is read from the command itself or from an
  `--data-binary @file` / `-d @file` it sends.
- Write / Edit / MultiEdit: a file under agents/copy/{workspace,atadas,munka}/ whose path has "meta" or
  "hirdet" in a folder or file name (e.g. workspace/vip-meta-20261102/...). Copy's own skill folder is
  not included, so editing the references is never blocked.
- A Google Drive / Docs write tool whose input is about an ad.
"About an ad" is the AD pattern below (hirdetés, Meta-szöveg/-kampány, primary text, elsődleges szöveg,
kreatív-szöveg).

WHAT IT REQUIRES, FROM THIS SESSION'S TRANSCRIPT
------------------------------------------------
(a) the copywriter-core and ad-copy skills loaded: a Skill tool call, a typed /command, or a Read of the
    skill's SKILL.md;
(b) every *.md directly in ad-copy/references/magyar-mintak/ (listed when the gate runs) and
    ad-copy/references/zsolt-hirdetes-mercek.md read: a Read tool call on the file, or a Bash
    cat/head/tail/sed/less naming it.
If anything is missing, the call is blocked, and the message names each missing step.

WHAT IT DOES NOT CATCH (said, so it does not look like more)
------------------------------------------------------------
- whether the reading was ATTENTIVE, or covered a whole long file (a Read with a small limit counts);
- ad copy handed in some other way: a Telegram reply, a curl to another service, a file outside the paths
  above;
- an ad-related message that is not ad copy (e.g. "stop, the brief changed"), which is blocked too: the
  cost is loading the skills once per session.

FAIL-CLOSED: an unreadable transcript or a missing reference folder blocks, and the message says why.

Contract: PreToolUse; payload on stdin; exit 0 = allow, exit 2 = block (stderr goes back to the agent).
Usage in settings: python3 hirdetes-elokeszites-kapu.py [--skills-dir DIR]
"""

import argparse
import glob
import json
import os
import re
import shlex
import sys

DEFAULT_SKILLS = "/Users/macmini/marveen/agents/copy/.claude/skills"
REQUIRED_SKILLS = ("copywriter-core", "ad-copy")
AD = re.compile(
    r"hirdet[eé]s|hirdet[eé]si|meta[- ]?(?:sz[oö]veg|kamp[aá]ny|hirdet)|primary[- ]text|"
    r"els[oő]dleges[- ]sz[oö]veg|kreat[ií]v[- ]sz[oö]veg",
    re.I,
)
MSG_API = re.compile(r"/api/messages\b")
SENDS = re.compile(r"-X\s*['\"]?(?:POST|PUT)\b|--data(?:-binary|-raw)?\b|(?:^|\s)-d\s")
DATA_FILE = re.compile(r"(?:--data-binary|--data|-d)\s+@(\"[^\"]+\"|'[^']+'|\S+)")
COPY_OUT = re.compile(r"/agents/copy/(?:workspace|atadas|munka)/(.+)$")
DOC_TOOL = re.compile(r"^mcp__(?:google-drive__|claude_ai_Google_Drive__|claude_ai_Claude_Docs__)"
                      r".*(?:create|update|insert|append|replace|batch|write|edit)", re.I)
READ_VERB = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(cat|head|tail|sed|less|more|bat)\b([^;&|\n]*)")


def delivery(tool, inp, cwd):
    """The reason this call hands in ad copy, or None."""
    if tool == "Bash":
        cmd = str(inp.get("command") or "")
        if not MSG_API.search(cmd) or not SENDS.search(cmd):
            return None  # a GET (reading a message) hands nothing in
        text = cmd
        for m in DATA_FILE.finditer(cmd):
            p = m.group(1).strip("\"'")
            p = p if os.path.isabs(p) else os.path.join(cwd or "", p)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    text += "\n" + fh.read(200000)
            except OSError:
                pass
        return "an inter-agent message about an ad" if AD.search(text) else None
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        m = COPY_OUT.search(path.replace("\\", "/"))
        if m and re.search(r"meta|hirdet", m.group(1), re.I):
            return f"a file in an ad folder ({path})"
        return None
    if DOC_TOOL.search(tool or "") and AD.search(json.dumps(inp, ensure_ascii=False)):
        return f"a Drive/Docs write about an ad ({tool})"
    return None


def session_events(transcript):
    """Skill names loaded, Read paths, and Bash commands of this session."""
    skills, reads, bash = set(), set(), []
    with open(transcript, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                j = json.loads(line)
            except ValueError:
                continue
            msg = j.get("message") if isinstance(j, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            if not isinstance(content, list):
                continue
            for x in content:
                if not isinstance(x, dict):
                    continue
                if x.get("type") == "text" and j.get("type") == "user":
                    for name in re.findall(r"<command-name>/?([\w:.-]+)</command-name>", x.get("text") or ""):
                        skills.add(name.split(":")[-1])
                if x.get("type") != "tool_use":
                    continue
                inp = x.get("input") or {}
                if x.get("name") == "Skill":
                    skills.add(str(inp.get("skill") or "").split(":")[-1])
                elif x.get("name") == "Read":
                    reads.add(os.path.realpath(str(inp.get("file_path") or "")))
                elif x.get("name") == "Bash":
                    bash.append(str(inp.get("command") or ""))
    return skills, reads, bash


def was_read(path, reads, bash):
    if os.path.realpath(path) in reads:
        return True
    name = os.path.basename(path)
    for cmd in bash:
        if "ad-copy" not in cmd and path not in cmd:
            continue
        for m in READ_VERB.finditer(cmd):
            try:
                args = shlex.split(m.group(2))
            except ValueError:
                args = m.group(2).split()
            if m.group(1) == "sed" and any(a.startswith("-i") for a in args):
                continue  # sed -i writes
            if any(a == path or a.endswith("/" + name) or a == name for a in args):
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default=os.environ.get("HIRDETES_KAPU_SKILLS", DEFAULT_SKILLS))
    args = ap.parse_args()
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool = str(payload.get("tool_name") or "")
    why = delivery(tool, payload.get("tool_input") or {}, payload.get("cwd"))
    if not why:
        return 0
    head = f"hirdetes-elokeszites-kapu: this call hands in ad copy ({why}), and"
    refs_dir = os.path.join(args.skills_dir, "ad-copy", "references")
    files = sorted(glob.glob(os.path.join(refs_dir, "magyar-mintak", "*.md"))) + [os.path.join(refs_dir, "zsolt-hirdetes-mercek.md")]
    missing_files = [f for f in files if not os.path.isfile(f)]
    if missing_files or not os.path.isdir(os.path.join(refs_dir, "magyar-mintak")):
        print(f"{head} the reference set it must be checked against is missing ({', '.join(missing_files) or refs_dir + '/magyar-mintak'}). "
              f"Blocked until it is back: the gate does not go green without its source.", file=sys.stderr)
        return 2
    transcript = str(payload.get("transcript_path") or "")
    try:
        skills, reads, bash = session_events(transcript)
    except OSError as e:
        print(f"{head} this session's transcript could not be read ({transcript or 'no transcript_path'}: {e}). "
              f"Blocked: without it the gate cannot see whether the skills were loaded.", file=sys.stderr)
        return 2
    for s in REQUIRED_SKILLS:
        if os.path.realpath(os.path.join(args.skills_dir, s, "SKILL.md")) in reads:
            skills.add(s)
    lacking = [f"load the {s} skill (Skill tool: {s})" for s in REQUIRED_SKILLS if s not in skills]
    lacking += [f"read {f}" for f in files if not was_read(f, reads, bash)]
    if not lacking:
        return 0
    steps = "\n".join(f"  - {x}" for x in lacking)
    print(f"{head} in this session these steps are missing:\n{steps}\n"
          f"Do them (Read tool for the files), check the copy against them, then hand it in again.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
