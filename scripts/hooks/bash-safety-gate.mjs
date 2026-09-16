#!/usr/bin/env node
// PreToolUse Bash safety gate for restricted (web-reading) fleet agents.
//
// PROBLEM this solves (2026-07-20): the "marketer" security profile locked Bash
// to a tiny prefix allowlist (ls/cat/...). Background fleet agents build COMPOUND
// commands routinely -- `cd /path && F=... python3 ...`, pipes, heredocs. A
// prefix allowlist matches the FIRST word (`cd`, a `VAR=` assignment), so every
// such command fell through to an interactive permission PROMPT. For a background
// agent driven over Telegram that means the operator gets spammed with endless
// "Permission: Bash / Allowed" cards -- useless friction, and it blocks the agent
// waiting on a human.
//
// FIX: auto-APPROVE Bash (permissionDecision: 'allow' -> no prompt) EXCEPT for a
// focused denylist of genuinely dangerous commands, which are hard-DENIED here.
// The gate is self-contained: it does NOT rely on the settings deny-list surviving
// a hook 'allow', because a hook 'allow' can bypass the normal permission system.
// So every dangerous pattern must be denied by THIS gate.
//
// Money safety (ad spend) is unaffected: it lives at the MCP tool-approval layer,
// not in Bash. Self-pace safety is unaffected: self-pace-gate.mjs runs alongside
// and its 'deny' still wins (deny beats allow across PreToolUse hooks).
//
// Wired into the agent's .claude/settings.json PreToolUse "Bash" matcher.

import { readFileSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

// Split a compound command into simple segments so a dangerous token in one part
// is caught even when the command STARTS with something innocent (cd/VAR=). Same
// approach as self-pace-gate.mjs: collapse line-continuations first, then split on
// real separators. Not quote-aware (accepted: a dangerous binary inside a quoted
// string is rare and the worst case is a false-deny, which fails safe).
export function splitSegments(command) {
  const base = dropDataHeredocBodies(String(command ?? '').replace(/\\\r?\n/g, ' '))
    .split(/&&|\|\||[;&|]|\r?\n/)
    .map((s) => s.trim())
  return [...base, ...expandCodeWrappers(base)]
}

// The MISSING HALF of the heredoc rule, and the reason the denylist could be
// walked straight past. A body handed to a named data sink is data; a command
// handed to a SHELL is code -- and code has to go back through the denylist.
// Only the first half existed, so measured live on 2026-08-08: `sh -c 'rm -rf
// ...'` was ALLOWED and ran. The whole family went with it -- bash/zsh -c, eval,
// ssh <host> '<cmd>', xargs sh -c, find -exec/-delete -- including the secret
// read `sh -c 'cat ~/.ssh/id_rsa'`. Control: without the wrapper every one of
// them was already denied, so the wrapper was doing the bypassing.
//
// Why extract rather than widen the command boundary: adding the quote characters
// to BOUNDARY would be one character class, and it would deny every quoted
// MENTION of a denylisted word -- `echo "rm is dangerous"` and every commit
// message and inter-agent report with it. Measured on 10 889 real commands, that
// class of false positive is already the biggest one this gate produces. So the
// quoted text is read as code ONLY where a wrapper will actually execute it.
const CODE_WRAPPERS = [
  // <shell> -c '<code>' -- any flags may sit between, and the arg may be quoted
  // either way or bare. `\S+` last so an unquoted one-word command still lands.
  // `-[A-Za-z]*c` because bash takes BUNDLED short flags: `sh -lc '...'` and
  // `sh -ec '...'` run their argument exactly like `sh -c` does.
  /(?:^|[\s(`])(?:\S*\/)?(?:(?:ba|z|d|k|tc|c)?sh|fish)\s+(?:-[^\s-]\S*\s+)*-[A-Za-z]*c\s+('[^']*'|"(?:[^"\\]|\\.)*"|\S+)/gi,
  // eval takes its code as ordinary arguments, no -c
  /(?:^|[\s(`])eval\s+('[^']*'|"(?:[^"\\]|\\.)*"|\S+)/gi,
  // ssh [opts] <host> '<remote command>' -- the quoted tail is run on the far end,
  // which is still a destructive act we should not wave through.
  /(?:^|[\s(`])ssh\s+\S+(?:\s+\S+)*?\s+('[^']*'|"(?:[^"\\]|\\.)*")/gi,
  // find ... -exec/-execdir/-ok <command> ... ; -- everything up to the terminator
  /-(?:exec|execdir|ok|okdir)\s+([\s\S]*?)(?:\s+['"]?[;+]['"]?(?:\s|$)|$)/gi,
]

function unquote(arg) {
  const s = String(arg ?? '').trim()
  if ((s.startsWith("'") && s.endsWith("'")) || (s.startsWith('"') && s.endsWith('"'))) {
    return s.slice(1, -1).replace(/\\(["'\\$`])/g, '$1')
  }
  return s
}

// Pull the code out of every wrapper found in `segs` and return it as further
// segments, following nesting (`sh -c "sh -c 'rm -rf /'"`) to a small depth. The
// depth cap is a runaway guard, not a security boundary: three levels is already
// far past anything a real command does.
function expandCodeWrappers(segs, depth = 0) {
  if (depth >= 3) return []
  const found = []
  for (const seg of segs) {
    for (const re of CODE_WRAPPERS) {
      re.lastIndex = 0
      for (const m of seg.matchAll(re)) {
        const code = unquote(m[1])
        if (!code) continue
        for (const part of code.split(/&&|\|\||[;&|]|\r?\n/)) {
          const t = part.trim()
          if (t) found.push(t)
        }
      }
    }
  }
  return found.length ? [...found, ...expandCodeWrappers(found, depth + 1)] : []
}

// A heredoc body is DATA the named program reads, not a list of commands -- but
// only when we can NAME that program. Measured 2026-08-06: `rm = 0` on its own
// line inside `python3 <<'PY' ... PY` denied the whole call, because the split
// above cuts on newlines and every body line became a segment whose first word
// went against the denylist. A python variable name is not a deletion.
//
// The recognition is an ALLOWLIST, and that IS the safety property: a heredoc fed
// to anything not named here keeps today's behaviour exactly -- every body line is
// still scanned. A shell anywhere on the opener line vetoes the whole judgement,
// so `bash <<EOF ... EOF` and `cat <<EOF | sh` keep being read as code, which is
// what they are: hiding `rm -rf /` in a body bash executes is an attack, not a
// false positive. The veto also covers the case the allowlist alone would get
// wrong -- `sudo bash -c 'cat x' <<'EOF'` mentions `cat`, but a shell runs it.
const HEREDOC_DATA_CONSUMER = () =>
  at('python3?|node|jq|cat|sqlite3|mysql|psql|tee|awk|sed|grep|wc|sort|uniq|head|tail|mail')
const HEREDOC_CODE_CONSUMER = () =>
  at('sh|bash|zsh|dash|ksh|csh|tcsh|fish|eval|source|xargs|ssh')

// `git` is deliberately NOT in the allowlist above: most of git is not a data
// sink, and naming the binary alone would be far too wide. It qualifies in
// exactly one shape -- a message read from STDIN -- because there the body is
// prose git stores verbatim and never executes. Narrowed to this form on Nova's
// call (2026-08-08), after the gate refused THIS FILE's own commit message: the
// text quoted a denylisted word while explaining the fix, and the quote landed at
// a line start. The shell veto still sits above it, so `bash -c 'git commit -F -'`
// is read as code like any other shell line.
const GIT_STDIN_MESSAGE = /(?:^|\s)(?:-F\s*-|--file\s*=\s*-)(?=\s|$)/

// `<<WORD`, `<<-WORD`, `<<'WORD'`, `<<"WORD"`. Never `<<<WORD` (herestring), and
// the word must start like an identifier so `$((1<<2))` is not read as an opener.
//
// BOTH guards on the `<<<` case are load-bearing, and the lookBEHIND is the one
// that is easy to miss: with only the lookahead, `<<< "y"` still matched starting
// at the SECOND `<` (`<<` + ` "y"`), so a herestring opened a heredoc named `y`,
// swallowed every following line as body, and a real command after it went
// unscanned. Caught by the swallowing test, not by reading the regex.
const HEREDOC_OPEN = /(?<!<)<<(?!<)(-?)\s*(['"]?)([A-Za-z_]\w*)\2/g

// The consumer is the LAST command BEFORE the `<<`, never "any command on the
// line". The first version asked whether the line mentioned a data sink anywhere,
// and that was a hole I put in myself: `weirdtool <<'EOF' | tail -2` named `tail`
// downstream, so the body fed to weirdtool was dropped unscanned. Found by running
// the counter-test as a real command rather than trusting the unit tests, which
// had no pipeline case. self-pace-gate's stripDataHeredocs already took the owning
// command for the same reason (Pixel, 2026-08-02); this now matches it.
// The two halves of the question have DIFFERENT scopes, and getting that backwards
// is what made the first version wrong in both directions:
//
//   VETO -- whole line. A shell ANYWHERE on the line means the body may reach it:
//   `cat <<EOF | sh` hands cat's output straight to sh, so the body is executed
//   even though cat owns the heredoc. A line-wide veto only ever ADDS denials.
//
//   POSITIVE -- owning command only. The heredoc is fed to the command before the
//   `<<`, so a data sink DOWNSTREAM proves nothing: `weirdtool <<'EOF' | tail -2`
//   named tail and dropped a body fed to weirdtool. That was a hole I introduced
//   by asking the line-wide question here too, and it surfaced only when I ran the
//   counter-test as a real command -- the unit tests had no pipeline case.
//   self-pace-gate's stripDataHeredocs already took the owning command (Pixel,
//   2026-08-02); this now agrees with it.
function heredocBodyIsData(openerLine, heredocIndex) {
  const parts = openerLine.split(/&&|\|\||[;&|]/)
  if (parts.some((p) => HEREDOC_CODE_CONSUMER().test(p.trim()))) return false
  const owning = (openerLine.slice(0, heredocIndex).split(/&&|\|\||[;&|]/).pop() ?? '').trim()
  if (at('git').test(owning) && GIT_STDIN_MESSAGE.test(owning)) return true
  return HEREDOC_DATA_CONSUMER().test(owning)
}

// Remove the body lines of every heredoc whose consumer we recognise as a data
// sink. Command lines, and the bodies of every unrecognised consumer, come back
// untouched. Terminator matching follows bash: exact line, with `<<-` stripping
// leading TABS. An unterminated heredoc swallows the rest -- which is also what
// bash does with it, so nothing "escapes" that would have run as a command.
function dropDataHeredocBodies(text) {
  const lines = text.split(/\r?\n/)
  const kept = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i++]
    kept.push(line)
    const opens = [...line.matchAll(HEREDOC_OPEN)]
    if (!opens.length) continue
    for (const m of opens) {
      const [, dash, , delim] = m
      const bodyIsData = heredocBodyIsData(line, m.index)
      while (i < lines.length) {
        const cur = lines[i++]
        if ((dash === '-' ? cur.replace(/^\t+/, '') : cur) === delim) break
        if (!bodyIsData) kept.push(cur)
      }
    }
  }
  return kept.join('\n')
}

// A leading wrapper before the real binary: env-assignments, sudo/env/command/
// exec/nice/time/builtin, and an absolute/relative path prefix. Mirrors
// self-pace-gate's SCHED_PREFIX so `sudo rm`, `/bin/rm`, `PATH=/x rm` all anchor.
const PREFIX = String.raw`(?:(?:[A-Za-z_]\w*=\S*|sudo|env|command|exec|nice|builtin|time|\\)\s+)*(?:\S*/)?`
// Command boundary inside a segment: start, or right after a substitution opener.
const BOUNDARY = '[(`]'
const at = (bin) => new RegExp(String.raw`(^|${BOUNDARY}\s*)${PREFIX}(?:${bin})\b`, 'i')

// Destructive / privilege / system-state commands, checked PER SEGMENT (anchored
// at command position, wrapper-tolerant). `rm` in any form (an agent has its Write
// scoped to its own dir; deletion via shell is not a routine need and is the
// classic injection payload). cp/mv are intentionally NOT here: they are routine
// and blocking them would break normal work; the real destructive verbs are.
const DANGEROUS_SEG = [
  at('rm|rmdir'),                       // deletion
  at('sudo|su|doas'),                   // privilege escalation
  at('chmod|chown|chgrp|chflags'),      // permission tampering
  at('kill|killall|pkill'),             // process killing
  at('dd|mkfs|fdisk|parted|newfs'),     // disk destruction
  at('shutdown|reboot|halt|poweroff'),  // host state
  at('diskutil|hdiutil'),               // macOS disk tooling
  at('osascript'),                      // AppleScript: can drive the whole Mac
  // find's own deletion, which needs no wrapper to extract: `-delete` IS the verb.
  // Its `-exec`/`-ok` sibling goes through CODE_WRAPPERS instead, because there the
  // dangerous part is a command find runs, not a flag find understands.
  /\bfind\b[\s\S]*\s-delete\b/i,
]

// Patterns that span a pipe/substitution and so must be tested on the WHOLE
// command (splitSegments would cut the `|` and hide them).
const DANGEROUS_WHOLE = [
  // fork bomb
  /:\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:/,
  // pipe a network fetch straight into a shell (remote code execution)
  /\b(?:curl|wget|fetch)\b[\s\S]*\|\s*(?:sudo\s+)?(?:ba|z|d|k)?sh\b/i,
  // pipe ANYTHING into a bare interactive shell reading stdin (`... | sh`)
  /\|\s*(?:sudo\s+)?(?:ba|z|d|k)?sh\s*(?:$|[;&|])/i,
  // eval of fetched content
  /\beval\b[\s\S]*\$\(\s*(?:curl|wget|fetch)\b/i,
]

// Reading secret material: SSH/AWS/GPG keys, any .env, keychain dumps. This stops
// the casual/injected `cat ~/.ssh/id_rsa` exfil path, which is the realistic
// vector. It is a speed bump, not containment, and the SIZE of the gap is measured
// rather than estimated:
//
//   2026-09-16, 25 command shapes put to this gate (the gate is a pure function of
//   the command text, so no file was ever opened to measure it):
//     before widening the list: 11 trivially available alternatives passed
//     after:                     4  -- python3 -c, node -e, tar, ditto
//   sed, awk, grep, base64, cut, tr and perl moved from pass to deny in that round.
//
// KEEP THIS NUMBER HONEST WHEN THE LIST GROWS. An enumeration gets to look more
// complete with every name added while the CLASS stays open: an interpreter
// one-liner cannot be enumerated away, and closing it needs a different mechanism
// (match on the path a command OPENS, not on the command name). Without the number
// written down, the rule's best property -- that it admits what it does not cover
// -- is what erodes first.
//
// KNOWN FALSE POSITIVE, measured in the same round: `.env` matches env TEMPLATES
// too, so `grep PORT .env.example` and `sed -n 1p .env.sample` are refused. Harmless
// files, and annoying to hit. It is left as-is deliberately: `.env.example` and
// `.env.production` are lexically the same shape, so any suffix-based narrowing
// that frees the template also frees a real secret file.
const SECRET_READ = [
  /(^|[(`\s])(?:\S*\/)?(?:cat|less|more|head|tail|bat|nl|xxd|od|strings|cp|scp|rsync|sed|awk|grep|base64|cut|tr|perl)\b[\s\S]*(?:\/\.ssh\/|\/\.aws\/|\/\.gnupg\/|\.env\b|id_rsa|id_ed25519|\.pem\b)/i,
  /\bsecurity\b\s+(?:find-generic-password|find-internet-password|dump-keychain|export)\b/i,
]

// --- store/ is write-protected from an agent shell (2026-07-22) ----------------
//
// WHY: store/ holds the dashboard token, the vault, the sqlite DB and -- as of
// today -- the ads-write GRANT that decides whether an agent may spend money. The
// Write/Edit tools were already denied here by edit-safety-gate, but the shell was
// not, so `echo ... > store/ads-write-grant.json` would have let an agent widen its
// own permissions. A permission file that the permissioned party can rewrite is not
// a permission file.
//
// No agent needs to write here from a shell: the services that own these files
// (dashboard, bridge adapter) write them as PROCESSES, which this hook never sees.
// READING is deliberately untouched -- agents read the dashboard token here by design.
//
// HONEST LIMIT: a python3/node one-liner walks straight past this, exactly as the
// SECRET_READ comment above admits about its own rule. This raises the effort and
// makes a casual or injected attempt fail loudly; it is not containment.
const STORE_REF = /(?:\/marveen\/store\/|(?:\.\.\/)+store\/)/i

// Writing, moving, linking or re-permissioning. If a segment touches store/ with one
// of these it is refused -- including `cp store/.dashboard-token /tmp/`, a copy OUT,
// which is as much a leak as a write in.
const STORE_WRITE_CMD = at('tee|cp|mv|install|rsync|truncate|ln|touch|mkdir')
// `sed -i` edits in place; `dd of=` names a write target.
const STORE_WRITE_EXTRA = [/(^|\s)sed\b[^|;]*\s-i\b/i, /\bof=/i]
// A redirect whose TARGET is under store/. Deliberately narrow: `cat store/x > /tmp/y`
// reads from store and writes elsewhere, and must NOT be caught by this rule.
const STORE_REDIRECT = /(?:^|[^0-9>])>>?\s*["']?[^\s"';|&]*(?:\/marveen\/store\/|(?:\.\.\/)+store\/)/i

export function writesToStore(segment) {
  const s = String(segment ?? '')
  if (STORE_REDIRECT.test(s)) return true
  if (!STORE_REF.test(s)) return false
  if (STORE_WRITE_CMD.test(s)) return true
  return STORE_WRITE_EXTRA.some((re) => re.test(s))
}

// Pure decision. Returns { deny, reason } -- deny:true -> block; deny:false ->
// auto-approve (no prompt). Only Bash is gated; anything else -> allow (defer).
export function gateDecision(toolName, toolInput) {
  if (String(toolName ?? '') !== 'Bash') return { deny: false }
  const command = String(toolInput?.command ?? '')
  for (const re of DANGEROUS_WHOLE) {
    if (re.test(command)) return { deny: true, reason: DANGER_MSG }
  }
  for (const seg of splitSegments(command)) {
    for (const re of DANGEROUS_SEG) {
      if (re.test(seg)) return { deny: true, reason: DANGER_MSG }
    }
    for (const re of SECRET_READ) {
      if (re.test(seg)) return { deny: true, reason: SECRET_MSG }
    }
    if (writesToStore(seg)) return { deny: true, reason: STORE_WRITE_MSG }
  }
  return { deny: false }
}

// Loud AND useful: say what was refused, why, and what the legitimate route is --
// otherwise a well-meaning agent goes looking for a way around it.
const STORE_WRITE_MSG =
  'Iras a store/ ala TILTOTT agens-shellbol. Ott van a dashboard-token, a vault, az ' +
  'SQLite DB es a jogosultsagi grant-fajl -- ezeket a szolgaltatasok irjak sajat ' +
  'folyamatkent, nem shellbol. OLVASNI szabad, ez a tiltas csak az irasra/masolasra/ ' +
  'athelyezesre vonatkozik. LEGITIM UT, ha tenyleg kell oda irni: a fo-agens (Nova) ' +
  'teszi le a fajlt, vagy szolj Novanak inter-agent uzenettel es o intezi. NE keress ' +
  'kerulout -- ha megis kell egy kivetel, az egy beszelgetes, nem egy megkerules.'

const DANGER_MSG =
  'Ez a Bash-parancs a biztonsagi denylistre esik (destruktiv / rendszer-szintu / ' +
  'privilege / remote-code-exec). Ezt a profil tiltja. Ha tenyleg szukseges, kerd ' +
  'Zsolt jovahagyasat a Nova Fonokon keresztul, ne futtasd magadtol.'
const SECRET_MSG =
  'Titok-anyag olvasasa (SSH/AWS/GPG kulcs, .env, keychain) TILTOTT. Ha hitelesito ' +
  'adatra van szukseged, kerd a Nova Fonoktol a biztonsagos tarolas modjat.'
function dangerReason(_seg) { return DANGER_MSG }

function allow() {
  // Explicit allow -> skip the interactive prompt for safe commands.
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'allow',
      permissionDecisionReason: 'safe (bash-safety-gate)',
    },
  }))
  process.exit(0)
}

function deny(reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }))
  process.exit(0)
}

function isInvokedDirectly() {
  try {
    const self = realpathSync(fileURLToPath(import.meta.url))
    const entry = process.argv[1] ? realpathSync(process.argv[1]) : ''
    return self === entry
  } catch {
    return false
  }
}
if (isInvokedDirectly()) {
  let payload
  try {
    payload = JSON.parse(readFileSync(0, 'utf-8'))
  } catch {
    process.exit(0) // malformed/empty input: defer to normal flow, never crash
  }
  // Only opine on Bash. For any other tool, exit 0 with no output (no opinion).
  if (String(payload?.tool_name ?? '') !== 'Bash') process.exit(0)
  const { deny: shouldDeny, reason } = gateDecision(payload?.tool_name, payload?.tool_input)
  if (shouldDeny) deny(reason)
  allow()
}
