#!/usr/bin/env python3
"""scheduled-task-register-warn.py -- warns about a hand edit of a scheduled task before the scheduler refuses it.

WHY (Nova 32038, 2026-11-26): the schedule runner only starts a task whose files match the hash in the task registry
(src/web/schedule-registry.ts). A hand edit of ~/.claude/scheduled-tasks/<name>/SKILL.md or task-config.json without
`schedule-registry-cli.js register <name>` afterwards makes the NEXT start fail with a hash mismatch. That happens hours
later, and nobody tells the person who made the edit. Since 11-05 the main agent did this at least 11 times. The latest
was summa-adat-frissites, at the 05:30 start of 11-26 (system 32037). Ten cold memories about it did not stop it: an
agent reads a rule, but it does a step. This hook is the step.

WHY A WARNING AND NOT AN AUTOMATIC REGISTER: the registry is the gate against an edit nobody meant, an injected one
included. Registering automatically after the agent's own tool call would make every write by that agent legitimate,
which is the one thing the gate exists to stop. The warning costs no extra turn: right after the edit the model gets the
task name, the verdict and the exact command. Registering stays a deliberate step.

HOW: PostToolUse / PostToolUseFailure on Edit, MultiEdit, Write and Bash.
  - The candidate tasks:
    - Edit/MultiEdit/Write: the task whose folder holds file_path, if it lies under the scheduled-tasks directory;
    - Bash: every `scheduled-tasks/<name>` that the command text NAMES. Arbitrary interpreter code cannot be judged
      statically, so this is the same "the command names it" scope as memory-frontmatter-bash-gate.py.
  - For those names, the verdict comes from the registry's own CLI (`verify <name>`), so the hash rule lives in ONE place.
  - `hash-mismatch` or `unregistered` -> exit 2, with the names and the command on stderr. `ok` and `not-found` -> nothing.
  - What exit 2 does here: in PostToolUse it hands the stderr text to the model as a hook_blocking_error. It does NOT undo
    anything; the file stays as written. Measured on Claude Code 2.1.284 (memory-frontmatter-bash-gate.py, 2026-09-29).
FAIL-OPEN: an error in the hook itself (stdin, node missing, a timeout) never blocks. The hook exits 0 and writes one line
to store/hook-errors.log via hook_errlog.
MARVEEN_DISABLED_HOOKS=scheduled-task-register-warn switches it off.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

HOOK = 'scheduled-task-register-warn'
TOOLS = ('Edit', 'MultiEdit', 'Write', 'Bash')
# The registry's own directory (src/web/scheduled-tasks-io.ts: SCHEDULED_TASKS_DIR = ~/.claude/scheduled-tasks).
TASKS_DIR = os.environ.get('SCHEDULED_TASKS_DIR_OVERRIDE') or os.path.join(os.path.expanduser('~'), '.claude', 'scheduled-tasks')
CLI = os.environ.get('SCHEDULE_REGISTRY_CLI_OVERRIDE') or os.path.join(ROOT, 'dist', 'web', 'schedule-registry-cli.js')
NAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,99}$')
VERIFY_TIMEOUT_S = 8


def _log(message, exc=None):
    try:
        import hook_errlog
        hook_errlog.report(HOOK, message, exc)
    except Exception:
        pass


def _disabled():
    try:
        import hook_switches
        return hook_switches.is_disabled(HOOK)
    except Exception:
        # A base without hook_switches.py: the same switch, read here (comma, semicolon or space separated names).
        raw = os.environ.get('MARVEEN_DISABLED_HOOKS', '') or ''
        names = {p.strip().lower().removesuffix('.py') for p in re.split(r'[,; ]+', raw) if p.strip()}
        return HOOK in names


def _real(p):
    try:
        return os.path.realpath(os.path.expanduser(p))
    except Exception:
        return p


def name_from_path(path, tasks_dir=None):
    """The task name if `path` lies in <tasks_dir>/<name>/..., else None (symlinks resolved on both sides)."""
    if not path:
        return None
    base = _real(tasks_dir or TASKS_DIR)
    p = _real(path)
    if not p.startswith(base + os.sep):
        return None
    name = p[len(base) + 1:].split(os.sep, 1)[0]
    return name if NAME_RE.match(name) else None


def names_from_command(cmd):
    """Every task the command names as scheduled-tasks/<name>, in order, once each."""
    out = []
    for m in re.finditer(r'scheduled-tasks/([A-Za-z0-9][A-Za-z0-9_-]{0,99})(?=[/\s\'"]|$)', cmd or ''):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def candidates(payload, tasks_dir=None):
    tool = payload.get('tool_name')
    ti = payload.get('tool_input') or {}
    if not isinstance(ti, dict):
        return []
    if tool in ('Edit', 'MultiEdit', 'Write'):
        n = name_from_path(str(ti.get('file_path') or ''), tasks_dir)
        return [n] if n else []
    if tool == 'Bash':
        return names_from_command(str(ti.get('command') or ''))
    return []


def verify(names):
    """[(verdict, name)] from the registry CLI's own `verify`; verdict: ok | hash-mismatch | unregistered | not-found | ..."""
    r = subprocess.run(['node', CLI, 'verify'] + list(names), capture_output=True, text=True, timeout=VERIFY_TIMEOUT_S, cwd=ROOT)
    out = []
    for line in r.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out.append((parts[0], parts[1]))
    return out


def message(bad):
    names = ' '.join(n for _, n in bad)
    lines = ['%s: a scheduled task was changed by hand and is not registered, so the scheduler will REFUSE its next start.' % HOOK]
    for v, n in bad:
        lines.append('  - %s: %s' % (n, v))
    lines.append('If this is the change you meant, register it now (from the install root):')
    lines.append('  node dist/web/schedule-registry-cli.js register --source hand-edit %s' % names)
    lines.append('If you did not mean it, put the files back first. This hook undid nothing.')
    return '\n'.join(lines) + '\n'


def run(payload, tasks_dir=None, verifier=None):
    """The decision: (exit code, stderr text). Pure apart from the verifier."""
    if not isinstance(payload, dict) or payload.get('tool_name') not in TOOLS:
        return 0, ''
    if payload.get('hook_event_name') not in ('PostToolUse', 'PostToolUseFailure'):
        return 0, ''
    names = candidates(payload, tasks_dir)
    if not names:
        return 0, ''
    bad = [(v, n) for v, n in (verifier or verify)(names) if v in ('hash-mismatch', 'unregistered')]
    return (2, message(bad)) if bad else (0, '')


def main():
    if _disabled():
        sys.exit(0)
    try:
        payload = json.loads(sys.stdin.read())
    except Exception as ex:
        _log('unreadable stdin, let through', ex)
        sys.exit(0)
    try:
        code, text = run(payload)
    except Exception as ex:  # an error in the hook itself never blocks
        _log('internal error, let through', ex)
        code, text = 0, ''
    if text:
        sys.stderr.write(text)
    sys.exit(code)


if __name__ == '__main__':
    main()
