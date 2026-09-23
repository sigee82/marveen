#!/usr/bin/env node
// PreToolUse Write/Edit/NotebookEdit safety gate for sandboxed dev fleet agents
// (e.g. Bit).
//
// PROBLEM (2026-07-20): after the Bash + MCP gates silenced those surfaces, a
// dev agent that edits files constantly (Write/Edit) still fired a "Permission:
// Edit / Allowed" card to the owner's Telegram for every single edit -- because
// an allow-LIST allow still surfaces a permission card, only a hook 'allow' is
// silent. For a background dev agent that means endless edit-permission spam.
//
// FIX: auto-APPROVE Write/Edit/NotebookEdit whose target path is INSIDE the
// agent's own sandbox roots (silent, no card); DEFER (normal prompt) for any
// path outside the sandbox; and DENY edits to secret material. Same output
// contract as bash-safety-gate.mjs. Governance gates run alongside and a 'deny'
// from any of them still wins.
//
// Wired into the agent's .claude/settings.json PreToolUse "Write|Edit|NotebookEdit".

import { readFileSync, realpathSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { normalize } from 'node:path'

const EDIT_TOOLS = new Set(['Write', 'Edit', 'NotebookEdit'])
// Sandbox roots any fleet agent may edit silently: the whole agents/ tree (each
// agent's own workdir, incl. workspace clones + nova-adapter) plus scratch temp.
// Cross-agent edit risk is low (all one owner's fleet) and the SECRET_PATH below
// still hard-denies credential material anywhere.
const ALLOWED_ROOTS = [
  '/Users/macmini/marveen/', // whole project (parity with read-gate): agents edit
  '/tmp/',                    // their own dirs AND legit project files (e.g. the dev
  '/private/tmp/',            // agent patching src/ under Nova's explicit approval).
  '/Users/macmini/.claude/skills/', // self-improvement: agents auto-generate/patch
]                            // SKILL.md files here (core fleet behavior) -> silent.
// The denylists below still hard-gate creds anywhere.
// Never silently write to secret/credential material even inside the sandbox.
const CRED_PATH = /(?:\/\.ssh\/|\/\.aws\/|\/\.gnupg\/|id_rsa|id_ed25519|\.pem$|\/\.secrets\/|\/marveen\/store\/|\.dashboard-token|\.vault-key|\/vault\.json)/i

// .env is its own case, and the previous rule got it WRONG IN BOTH DIRECTIONS
// (measured 2026-09-23, owner-authorised model switch):
//
//   * The comment above this line used to promise ".env files -> defer
//     (prompt), never silent overwrite", but .env sat in the same regex as the
//     SSH keys, so the code DENIED. Contract and implementation disagreed, and
//     the refusal text ("SSH/AWS/GPG kulcs, .pem") never even named .env, so
//     the message did not describe the rule that fired.
//   * A blanket defer is no better: under bypass-permissions there IS no
//     prompt, so "defer" degrades to a SILENT whole-file overwrite -- exactly
//     what the comment set out to prevent.
//
// So .env is split by the SHAPE of the write, not by trust:
//   Write/NotebookEdit -> replaces the whole file -> still DENY.
//   Edit               -> replaces one named string -> allowed to defer, UNLESS
//                         either side of the replacement mentions a credential
//                         key, which keeps token/key lines untouchable.
// Reading .env stays blocked by bash-safety-gate/read-safety-gate, so an agent
// cannot learn a secret's current value to put in old_string in the first place.
const ENV_PATH = /(?:^|\/)\.env(?:\.|$)/i
const CRED_KEY = /(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD|CREDENTIAL|_PW\b)/i

// Pure decision. Returns { decision: 'allow'|'deny'|'defer', reason? }.
// allow -> silent approve; deny -> block; defer -> no opinion (normal prompt).
export function gateDecision(toolName, toolInput) {
  if (!EDIT_TOOLS.has(String(toolName ?? ''))) return { decision: 'defer' }
  const p = toolInput?.file_path ?? toolInput?.notebook_path ?? toolInput?.path
  if (typeof p !== 'string' || !p) return { decision: 'defer' }
  const norm = normalize(p)
  if (CRED_PATH.test(norm)) return { decision: 'deny', reason: SECRET_MSG }
  if (ENV_PATH.test(norm)) {
    if (String(toolName) !== 'Edit') return { decision: 'deny', reason: ENV_WRITE_MSG }
    const touched = `${toolInput?.old_string ?? ''}\n${toolInput?.new_string ?? ''}`
    if (CRED_KEY.test(touched)) return { decision: 'deny', reason: ENV_CRED_MSG }
    return { decision: 'defer' }
  }
  if (norm.startsWith('/')) {
    if (ALLOWED_ROOTS.some((r) => norm.startsWith(r))) return { decision: 'allow' }
    return { decision: 'defer' } // absolute path outside sandbox -> normal prompt
  }
  // Relative path: resolved against the agent's own workdir cwd -> safe unless it
  // climbs out with a leading '..'.
  if (!norm.startsWith('..')) return { decision: 'allow' }
  return { decision: 'defer' }
}

const SECRET_MSG =
  'Titok-anyagba iras (SSH/AWS/GPG kulcs, .pem) TILTOTT. Ha hitelesito adatot kell ' +
  'tarolni, kerd a Nova Fonoktol a biztonsagos tarolas modjat.'

const ENV_WRITE_MSG =
  'Egy .env EGESZENEK feluliras (Write/NotebookEdit) TILTOTT: az a fajl hitelesito ' +
  'adatot is hordoz, es egy teljes visszairas a tobbi sort NYOMTALANUL eldobja. ' +
  'LEGITIM UT: celzott Edit egyetlen kulcsra (old_string/new_string). Ha tenyleg a ' +
  'teljes fajl kell, az a gazda dontese, ne kerulout.'

const ENV_CRED_MSG =
  'Ez az Edit egy .env HITELESITO kulcsat erinti (TOKEN/KEY/SECRET/PASSWORD/' +
  'CREDENTIAL szerepel a cserelt szovegben). Ez TILTOTT agens-oldalrol. Nem-titok ' +
  'konfigkulcs (pl. MAIN_AGENT_MODEL) celzott Edittel szabadon allithato.'

function emitAllow() {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'allow',
      permissionDecisionReason: 'safe in-sandbox edit (edit-safety-gate)',
    },
  }))
  process.exit(0)
}

function emitDeny(reason) {
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
    process.exit(0) // malformed/empty input: defer, never crash
  }
  if (!EDIT_TOOLS.has(String(payload?.tool_name ?? ''))) process.exit(0)
  const { decision, reason } = gateDecision(payload?.tool_name, payload?.tool_input)
  if (decision === 'deny') emitDeny(reason)
  if (decision === 'allow') emitAllow()
  process.exit(0) // defer
}
