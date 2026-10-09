#!/usr/bin/env python3
"""PreToolUse(Bash) gate: no `launchctl load|bootstrap` of a plist whose job has no PATH setup.

launchd starts jobs with PATH=/usr/bin:/bin:/usr/sbin:/sbin -- no Homebrew. A script that
shells out to node/tmux/gh works from an interactive shell and fails (or silently sees
nothing) under launchd. This happened twice despite a skill that documents it
(2026-08-22 login-watchdog, 2026-10-09 szamlak-napi), so it is a step now, not a note.

Passes when the plist sets EnvironmentVariables.PATH, or the script it runs assigns PATH=.
Deliberate exception (a script that only uses absolute binary paths): put the marker
`# launchd-path-ok` in the command.
"""
import json
import os
import plistlib
import re
import shlex
import sys

SCRIPT_EXT = ('.sh', '.bash', '.py', '.mjs', '.js', '.zsh')


def problems(plist_path):
    try:
        with open(plist_path, 'rb') as f:
            pl = plistlib.load(f)
    except Exception:
        return None  # unreadable / not a plist: not our call
    if (pl.get('EnvironmentVariables') or {}).get('PATH'):
        return None
    args = pl.get('ProgramArguments') or ([pl['Program']] if pl.get('Program') else [])
    scripts = [a for a in args if isinstance(a, str) and a.endswith(SCRIPT_EXT)]
    for s in scripts:
        try:
            if re.search(r'(^|[\s;])(export\s+)?PATH=', open(s, encoding='utf-8', errors='replace').read(), re.M):
                return None
            if 'os.environ["PATH"]' in open(s, encoding='utf-8', errors='replace').read():
                return None
        except OSError:
            pass
    return scripts or args[:1]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get('tool_input') or {}).get('command') or ''
    if not re.search(r'\blaunchctl\s+(load|bootstrap)\b', cmd) or '# launchd-path-ok' in cmd:
        return 0
    try:
        tokens = shlex.split(cmd, comments=False)
    except ValueError:
        tokens = cmd.split()
    bad = []
    for t in tokens:
        if t.endswith('.plist'):
            p = os.path.expanduser(os.path.expandvars(t))
            r = problems(p)
            if r is not None:
                bad.append((p, r))
    if not bad:
        return 0
    lines = ['launchagent-path-kapu: a launchd MINIMALIS PATH-tal indit (nincs /opt/homebrew/bin).']
    for p, r in bad:
        lines.append(f'  {p}: se EnvironmentVariables.PATH, se PATH= a futtatott scriptben ({", ".join(r)})')
    lines.append('Javitas: a wrapperbe `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"`, vagy PATH a plistbe.')
    lines.append('Utana a betoltes, es ELES csak egy `launchctl kickstart gui/501/<label>` futas utan.')
    lines.append('Ha a script csak abszolut binaris-utakat hasznal: `# launchd-path-ok` a parancsba.')
    print('\n'.join(lines), file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
