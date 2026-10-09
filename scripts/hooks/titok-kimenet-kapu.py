#!/usr/bin/env python3
"""PostToolUse hook: a secret-shaped value in a tool's OUTPUT is masked and named.

WHY THIS EXISTS
---------------
The key reached the transcript four times (2026-09-23 twice, 2026-09-28 twice),
every time through a READ, not a write: a sed-based redaction that silently did
not match, a `docker inspect` env dump masked by a deny-list of NAMES
(PASS/SECRET/KEY) that missed PM_BRIDGE_TOKEN, and `sed -n 1,30p` on a PHP file
whose header held raw define() credentials. Four notes in memory did not stop
the fifth; a step has to.

WHAT IT CAN AND CANNOT DO
-------------------------
The command has already run when this hook fires, so it never blocks. Two
layers, as in browser-content-notice.py, and for the same measured reason:

  1. `updatedToolOutput` -- the tool response with every secret-shaped value
     replaced by `<prefix>…[MASKED len=N sha=XXXXXXXX]`, SHAPE-PRESERVING: a
     dict keeps its keys, a list its length, only string leaves change. For a
     built-in tool the harness drops a replacement whose shape does not match
     and keeps the original WITHOUT telling the model (measured on WebSearch,
     Claude Code 2.1.278). Whether Bash accepts it has to be measured where the
     hook is wired; see the README next to this file.
  2. `additionalContext` -- a label that cannot be shape-rejected. It names the
     pattern KINDS and COUNTS, never a value: this text is injected as trusted
     framing, and repeating the value there would put it back in the context
     this hook exists to keep it out of.

The log (store/secret-output.log, JSON lines) holds kind, length and an 8-char
sha256 prefix per hit -- enough to tell "the same key again" from "a new one"
and to decide on rotation, never the value.

WHAT COUNTS AS A SECRET
-----------------------
Shapes with a fixed, documented prefix (OpenAI, Anthropic, Google API key,
Google OAuth client secret and refresh token, GitHub, Slack, AWS, Stripe,
Telegram bot token, JWT, PEM private key), plus two NAME-driven forms that the
prefix list cannot see: an assignment `SOMETHING_TOKEN=value` and a PHP
`define('SOMETHING_KEY', 'value')`. Those two skip obvious placeholders
(changeme, your_..., ***, <...>, ${...}, $(...), xxxx) and values under 8
characters. A bare hex string (md5, sha, git id) is NOT a secret here: they are
everywhere in this fleet's output and would bury the real hits.

CONTRACT
--------
Exit 0 on every path. Silence when nothing matched. A crash here must never
turn into a tool failure.
"""

import hashlib
import json
import os
import re
import sys
import time

LOG = os.environ.get('TITOK_KIMENET_LOG', '/Users/macmini/marveen/store/secret-output.log')

# (kind, regex, group holding the secret, visible prefix length)
PATTERNS = [
    ('openai-project', re.compile(r'sk-proj-[A-Za-z0-9_-]{20,}'), 0, 8),
    ('anthropic', re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'), 0, 7),
    ('openai-classic', re.compile(r'(?<![A-Za-z0-9_-])sk-[A-Za-z0-9]{32,}'), 0, 3),
    ('google-api-key', re.compile(r'AIza[0-9A-Za-z_-]{35}'), 0, 4),
    ('google-oauth-client-secret', re.compile(r'GOCSPX-[A-Za-z0-9_-]{20,}'), 0, 7),
    ('google-refresh-token', re.compile(r'(?<![A-Za-z0-9/])1//0[0-9A-Za-z_-]{30,}'), 0, 4),
    ('github-token', re.compile(r'\b(?:ghp|gho|ghs|ghu|ghr)_[A-Za-z0-9]{30,}'), 0, 4),
    ('github-pat', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{30,}'), 0, 11),
    ('slack-token', re.compile(r'\bxox[abprs]-[A-Za-z0-9-]{10,}'), 0, 5),
    ('aws-access-key', re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'), 0, 4),
    ('stripe-live-key', re.compile(r'\b(?:sk|rk)_live_[0-9A-Za-z]{20,}'), 0, 8),
    ('telegram-bot-token', re.compile(r'\b\d{8,10}:AA[A-Za-z0-9_-]{33}\b'), 0, 0),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'), 0, 3),
    ('pem-private-key', re.compile(
        r'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----'), 0, 0),
    # name-driven: the value after SOMETHING_TOKEN= / : (env dumps, .env, yaml)
    ('named-assignment', re.compile(
        r'\b[A-Za-z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|APIKEY|PRIVATE_KEY|ACCESS_KEY|CLIENT_SECRET)[A-Za-z0-9_]*'
        r'\s*[=:]\s*["\']?([^\s"\',;]{8,})', re.I), 1, 0),
    # name-driven: PHP define('SOMETHING_KEY', 'value')
    ('php-define', re.compile(
        r'define\(\s*["\'][A-Z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD)[A-Z0-9_]*["\']\s*,\s*["\']([^"\']{8,})["\']', re.I), 1, 0),
]

PLACEHOLDER = re.compile(
    r'^(?:\*+|x{4,}|X{4,}|<[^>]*>|\$\{[^}]*\}|\$\([^)]*\)|\$[A-Za-z_][A-Za-z0-9_]*|'
    r'.*(?:changeme|change_me|change-me|your[_-]|example|placeholder|dummy|redacted|masked|\[MASKED).*|'
    # code, not a value: `$userToken = get_user_meta($id, ...)` matched on 2026-09-28
    r'.*\(.*)$', re.I)


def _mask(value: str, keep: int) -> str:
    sha = hashlib.sha256(value.encode('utf-8', 'surrogatepass')).hexdigest()[:8]
    return f'{value[:keep]}…[MASKED len={len(value)} sha={sha}]'


def scan_text(text: str, hits: list) -> str:
    """Return text with every secret masked; append (kind, len, sha8) to hits."""
    if not text or len(text) < 8:
        return text
    for kind, rx, group, keep in PATTERNS:
        def repl(m, kind=kind, group=group, keep=keep):
            whole = m.group(0)
            secret = m.group(group)
            if '[MASKED' in whole:                    # already masked by an earlier pattern
                return whole
            if group and PLACEHOLDER.match(secret):
                return whole
            hits.append((kind, len(secret), hashlib.sha256(secret.encode('utf-8', 'surrogatepass')).hexdigest()[:8]))
            masked = _mask(secret, keep)
            if group == 0:
                return masked
            start, end = m.start(group) - m.start(0), m.end(group) - m.start(0)
            return whole[:start] + masked + whole[end:]
        text = rx.sub(repl, text)
    return text


def scan_value(value, hits: list):
    """Shape-preserving walk: only string leaves change."""
    if isinstance(value, str):
        return scan_text(value, hits)
    if isinstance(value, list):
        return [scan_value(v, hits) for v in value]
    if isinstance(value, dict):
        return {k: scan_value(v, hits) for k, v in value.items()}
    return value


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    response = payload.get('tool_response')
    if response is None:
        return
    hits: list = []
    masked = scan_value(response, hits)
    if not hits:
        return

    tool = str(payload.get('tool_name', '?'))
    kinds: dict = {}
    for kind, _, _ in hits:
        kinds[kind] = kinds.get(kind, 0) + 1
    summary = ', '.join(f'{k} x{n}' for k, n in sorted(kinds.items()))

    try:
        cmd_hits: list = []
        command = scan_text(str((payload.get('tool_input') or {}).get('command', ''))[:300], cmd_hits)
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({
                'ts': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                'session_id': payload.get('session_id'),
                'cwd': payload.get('cwd'),
                'tool': tool,
                'command': command,
                'hits': [{'kind': k, 'len': n, 'sha8': s} for k, n, s in hits],
            }, ensure_ascii=False) + '\n')
    except Exception:
        pass

    label = (
        f'[TITOK-KIMENET] A(z) {tool} kimenetében {len(hits)} titok-alakú érték volt ({summary}). '
        'A kimenetet maszkolva kellett kapnod; ha mégis a nyers értéket látod, a csere nem ment át. '
        'Az értéket NE ismételd meg, ne írd fájlba, üzenetbe vagy memóriába, és jelezd a futtatónak, '
        'melyik parancs írta ki (a csere-döntés a tulajdonosé). Napló érték nélkül: store/secret-output.log.'
    )
    print(json.dumps({
        'hookSpecificOutput': {
            'hookEventName': 'PostToolUse',
            'additionalContext': label,
            'updatedToolOutput': masked,
        }
    }, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
